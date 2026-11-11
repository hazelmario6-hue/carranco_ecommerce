import re
import uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch, Mock
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import TestCase, Client, override_settings
from django.db import transaction
from django.utils import timezone
from apps.core.models import CorreoPendiente
from apps.core.correos import queue_email, deliver_email, MailDeliveryError
from apps.cuentas.models import VerificacionCorreo, Direccion
from apps.cuentas.verificacion import request_verification, is_verified
from apps.catalogo.models import Categoria, Producto
from apps.carrito.services import KEY, summarize
from apps.pedidos.models import Pedido, MovimientoInventario
from apps.pedidos.services import create_order, make_quote
from apps.pagos.models import IntentoPago
from apps.pagos.services.confirmation import confirm
from apps.pagos.services.gateway import start, synchronize
from apps.pagos.services import mercadopago, openpay
User=get_user_model()

@override_settings(DEBUG=True,MAIL_PROVIDER='console',EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',APP_URL='https://carranco.example.test',SECURE_SSL_REDIRECT=False)
class VerificationTests(TestCase):
    def signup(self):
        with self.captureOnCommitCallbacks(execute=True):
            response=self.client.post('/cuenta/registro/',{'first_name':'Hazel','last_name':'Prueba','email':'nuevo@example.test','telefono':'4441234567','password1':'Mi-Clave-larga-2026!','password2':'Mi-Clave-larga-2026!','is_staff':'on'})
        return response,User.objects.get(username='nuevo@example.test')
    def link(self):
        body=CorreoPendiente.objects.filter(clave__startswith='verificar:').latest('pk').texto
        return re.search(r'https://carranco.example.test(/cuenta/verificar/\S+)',body).group(1)
    def test_signup_requires_email_before_login(self):
        response,user=self.signup()
        self.assertRedirects(response,'/cuenta/verificar/')
        self.assertFalse(user.is_active);self.assertFalse(user.is_staff)
        self.assertNotIn('_auth_user_id',self.client.session)
        self.assertEqual(len(mail.outbox),1)
        self.assertEqual(mail.outbox[0].to,[user.email])
        self.assertIn('verificar',mail.outbox[0].body)
        self.client.post('/cuenta/login/',{'username':user.username,'password':'Mi-Clave-larga-2026!'})
        self.assertNotIn('_auth_user_id',self.client.session)
    def test_get_scanner_does_not_activate_and_post_single_use(self):
        _,user=self.signup();link=self.link()
        self.assertEqual(self.client.get(link).status_code,200)
        user.refresh_from_db();self.assertFalse(user.is_active)
        self.assertRedirects(self.client.post(link),'/cuenta/login/')
        user.refresh_from_db();self.assertTrue(user.is_active);self.assertTrue(is_verified(user))
        self.assertEqual(self.client.post(link).status_code,400)
        self.assertNotIn('_auth_user_id',self.client.session)
        self.client.post('/cuenta/login/',{'username':user.username,'password':'Mi-Clave-larga-2026!'})
        self.assertIn('_auth_user_id',self.client.session)
    def test_token_expiry_tampering_and_email_change(self):
        _,user=self.signup();link=self.link()
        self.assertEqual(self.client.post(link[:-2]+'x/').status_code,400)
        VerificacionCorreo.objects.filter(usuario=user).update(vence_at=timezone.now()-timedelta(seconds=1))
        self.assertEqual(self.client.post(link).status_code,400)
        VerificacionCorreo.objects.filter(usuario=user).update(vence_at=timezone.now()+timedelta(hours=1))
        user.email='otro@example.test';user.save()
        self.assertEqual(self.client.post(link).status_code,400)
    def test_resend_throttle_and_latest_link_only(self):
        _,user=self.signup();old=self.link()
        self.assertFalse(request_verification(user))
        VerificacionCorreo.objects.filter(usuario=user).update(ultimo_envio=timezone.now()-timedelta(minutes=2))
        with self.captureOnCommitCallbacks(execute=True):self.assertTrue(request_verification(user))
        self.assertEqual(self.client.post(old).status_code,400)
        self.assertEqual(self.client.get(self.link()).status_code,200)
        VerificacionCorreo.objects.filter(usuario=user).update(ultimo_envio=timezone.now()-timedelta(minutes=2),envios_en_ventana=5)
        self.assertFalse(request_verification(user))
    def test_unknown_resend_generic_and_disabled_user_not_activated(self):
        response=self.client.post('/cuenta/verificar/',{'email':'inexistente@example.test'})
        self.assertEqual(response.status_code,302);self.assertEqual(CorreoPendiente.objects.count(),0)
        user=User.objects.create_user('blocked',email='blocked@example.test',is_active=False)
        self.assertFalse(request_verification(user))
    def test_existing_account_keeps_login_but_checkout_requires_verification(self):
        user=User.objects.create_user('legacy',email='legacy@example.test',password='legacy-test-password')
        self.client.force_login(user)
        self.assertContains(self.client.get('/cuenta/'),'Verifica tu correo')
        self.assertRedirects(self.client.get('/checkout/'),'/cuenta/verificar/')
        with self.captureOnCommitCallbacks(execute=True):self.client.post('/cuenta/verificar/',{'email':'attacker@example.test'})
        self.assertEqual(CorreoPendiente.objects.get().destinatario,user.email)
        user.refresh_from_db();self.assertTrue(user.is_active)
        self.client.post(self.link());self.assertTrue(is_verified(user))
    def test_post_verification_csrf_and_no_referrer(self):
        self.signup();link=self.link();client=Client(enforce_csrf_checks=True)
        response=client.get(link)
        self.assertEqual(response['Referrer-Policy'],'no-referrer')
        self.assertIn('no-store',response['Cache-Control'])
        self.assertNotContains(response,'fonts.googleapis.com')
        self.assertEqual(client.post(link).status_code,403)
    def test_registration_survives_mail_failure(self):
        with patch('apps.core.correos.send_email',side_effect=MailDeliveryError('Proveedor temporalmente no disponible.')):
            response,user=self.signup()
        self.assertEqual(response.status_code,302);self.assertFalse(user.is_active)
        self.assertEqual(CorreoPendiente.objects.get().estado,'pendiente')

@override_settings(DEBUG=True,MAIL_PROVIDER='console',EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',APP_URL='https://carranco.example.test',SECURE_SSL_REDIRECT=False,PAYMENTS_LIVE=False,MP_ACCESS_TOKEN='TEST-local',MP_WEBHOOK_SECRET='local-only',OPENPAY_PRODUCTION=False)
class PaymentEmailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user=User.objects.create_user('customer',email='customer@example.test',password='test-password-2026',first_name='Hazel')
        VerificacionCorreo.objects.create(usuario=cls.user,email=cls.user.email,verificado_at=timezone.now())
        cat=Categoria.objects.create(nombre='Quesos',slug='quesos')
        cls.product=Producto.objects.create(sku='Q1',legacy_id='q1',nombre='Queso',slug='queso',categoria=cat,precio_catalogo=95,precio_academico=2,stock=10)
        cls.address=Direccion.objects.create(usuario=cls.user,calle='Calle',numero_exterior='1',colonia='Centro',codigo_postal='78000',ciudad='SLP',estado='SLP')
    def order(self,provider='mercadopago'):
        session={KEY:{str(self.product.pk):2}}
        return create_order(self.user,session,self.address.pk,provider,uuid.uuid4(),make_quote(self.user,summarize(session)))
    def data(self,order,status='aprobado'):
        return {'id':'123456','reference':str(order.referencia),'amount':Decimal('4.00'),'currency':'MXN','status':status,'method':'credit_card'}
    def test_approved_payment_queues_one_receipt_only(self):
        order=self.order()
        with self.captureOnCommitCallbacks(execute=True):
            for _ in range(2):confirm('mercadopago',self.data(order))
        self.assertEqual(CorreoPendiente.objects.filter(clave=f'recibo:{order.pk}').count(),1)
        self.assertEqual(len(mail.outbox),1);self.assertIn('4.00',mail.outbox[0].body)
        self.assertIn('OPERACIÓN DE PRUEBA',mail.outbox[0].body)
        self.assertIn('no es una factura fiscal',mail.outbox[0].body)
        self.assertEqual(MovimientoInventario.objects.count(),1)
        self.assertEqual(CorreoPendiente.objects.get().estado,'enviado')
    def test_pending_failed_or_forged_payments_never_send_receipt(self):
        order=self.order()
        for status in ['pendiente','rechazado']:
            confirm('mercadopago',self.data(order,status))
        bad=self.data(order);bad['amount']=Decimal('1.00')
        with self.assertRaises(ValidationError):confirm('mercadopago',bad)
        self.assertFalse(CorreoPendiente.objects.exists())
        self.client.force_login(self.user)
        self.client.get(f'/mis-pedidos/{order.numero}/confirmacion/?status=approved&payment_id=123456')
        order.refresh_from_db();self.assertEqual(order.estado,'pendiente_pago')
    def test_receipt_owner_only_and_email_snapshot(self):
        order=self.order();self.user.email='changed@example.test';self.user.save()
        confirm('mercadopago',self.data(order))
        self.assertEqual(CorreoPendiente.objects.get().destinatario,'customer@example.test')
        self.client.force_login(self.user)
        self.assertContains(self.client.get(f'/mis-pedidos/{order.numero}/recibo/'),'Recibo de compra')
        other=User.objects.create_user('another',email='other@example.test');self.client.force_login(other)
        self.assertEqual(self.client.get(f'/mis-pedidos/{order.numero}/recibo/').status_code,404)
    def test_mail_failure_does_not_undo_payment(self):
        order=self.order()
        with patch('apps.core.correos.send_email',side_effect=MailDeliveryError('Timeout')):
            with self.captureOnCommitCallbacks(execute=True):confirm('mercadopago',self.data(order))
        order.refresh_from_db();self.assertEqual(order.estado_pago,'aprobado')
        row=CorreoPendiente.objects.get();self.assertEqual(row.estado,'pendiente')
        CorreoPendiente.objects.filter(pk=row.pk).update(proximo_intento=timezone.now())
        self.assertTrue(deliver_email(row.pk));self.assertFalse(deliver_email(row.pk))
        self.assertEqual(len(mail.outbox),1)
    def test_payment_rollback_never_sends_receipt(self):
        order=self.order()
        with self.captureOnCommitCallbacks(execute=True):
            try:
                with transaction.atomic():
                    confirm('mercadopago',self.data(order))
                    raise RuntimeError('Simulated database rollback')
            except RuntimeError:
                pass
        order.refresh_from_db()
        self.assertEqual(order.estado_pago,'pendiente')
        self.assertFalse(CorreoPendiente.objects.exists())
        self.assertFalse(mail.outbox)
    def test_disabled_gateways_cannot_be_selected(self):
        self.client.force_login(self.user);session=self.client.session;session[KEY]={str(self.product.pk):1};session.save()
        with override_settings(MP_ACCESS_TOKEN='',OPENPAY_PRIVATE_KEY=''):
            response=self.client.get('/checkout/')
            self.assertEqual(response.context['form'].fields['proveedor'].choices,[])
            initial=response.context['form'].initial
            response=self.client.post('/checkout/',{'direccion':self.address.pk,'proveedor':'mercadopago','aceptar':'on',**initial})
            self.assertEqual(response.status_code,200);self.assertEqual(Pedido.objects.count(),0)
    def test_unverified_cannot_create_or_start_payment(self):
        order=self.order();VerificacionCorreo.objects.all().delete()
        with self.assertRaises(ValidationError):self.order()
        with self.assertRaises(ValidationError):start(order.pk,self.user)
    def test_uncertain_gateway_creation_is_not_posted_twice(self):
        order=self.order()
        with patch('apps.pagos.services.mercadopago.create',side_effect=ValidationError('Timeout')) as create:
            with self.assertRaises(ValidationError):start(order.pk,self.user)
            with self.assertRaises(ValidationError):start(order.pk,self.user)
            self.assertEqual(create.call_count,1)
        self.assertEqual(IntentoPago.objects.get().estado,'revision')
    def test_query_uses_provider_data_and_is_rate_limited(self):
        order=self.order();IntentoPago.objects.create(pedido=order,proveedor='mercadopago',en_vivo=False)
        with patch('apps.pagos.services.mercadopago.search',return_value=[self.data(order)]) as search:
            self.assertEqual(synchronize(order.pk,self.user).estado_pago,'aprobado')
            with self.assertRaises(ValidationError):synchronize(order.pk,self.user)
            self.assertEqual(search.call_count,1)
    def test_query_other_reference_rejected(self):
        order=self.order();IntentoPago.objects.create(pedido=order,proveedor='mercadopago')
        data=self.data(order);data['reference']=str(uuid.uuid4())
        with patch('apps.pagos.services.mercadopago.search',return_value=[data]):
            with self.assertRaises(ValidationError):synchronize(order.pk,self.user)
        self.assertEqual(CorreoPendiente.objects.count(),0)
    def test_mp_search_fetches_only_our_payment_and_validates_environment(self):
        order=self.order()
        results={'results':[{'id':123456,'external_reference':str(order.referencia)},
                            {'id':999999,'external_reference':str(uuid.uuid4())}]}
        payment={'id':123456,'external_reference':str(order.referencia),'live_mode':False,
                 'transaction_amount':4,'currency_id':'MXN','status':'approved','payment_type_id':'credit_card'}
        with patch('apps.pagos.services.mercadopago.api',side_effect=[results,payment]) as api:
            self.assertEqual(mercadopago.search(order)[0]['status'],'aprobado')
        self.assertEqual(api.call_count,2)
        self.assertIn('external_reference='+str(order.referencia),api.call_args_list[0].args[1])
        payment['live_mode']=True
        with patch('apps.pagos.services.mercadopago.api',side_effect=[results,payment]):
            with self.assertRaises(ValidationError):mercadopago.search(order)
    @override_settings(OPENPAY_MERCHANT_ID='m12345678901234567890',OPENPAY_PRIVATE_KEY='test-private')
    def test_openpay_search_fetches_charge_from_same_order(self):
        order=self.order(provider='openpay')
        payment={'id':'ch123','order_id':str(order.referencia),'transaction_type':'charge',
                 'amount':4,'currency':'MXN','status':'completed','method':'card'}
        with patch('apps.pagos.services.openpay.api',side_effect=[[payment],payment]) as api:
            data=openpay.search(order)
        self.assertEqual(data[0]['reference'],str(order.referencia))
        self.assertEqual(data[0]['amount'],Decimal('4'))
        self.assertEqual(api.call_count,2)
        self.assertTrue(api.call_args_list[0].kwargs['expect_list'])
    @override_settings(MP_TEST_BUYER_EMAIL='buyer@testuser.com')
    def test_mp_sandbox_buyer_is_not_receipt_recipient(self):
        order=self.order()
        with patch('apps.pagos.services.mercadopago.account'),patch('apps.pagos.services.mercadopago.api',return_value={'id':'pref1','sandbox_init_point':'https://sandbox.mercadopago.com.mx/checkout/1'}) as api:
            mercadopago.create(order)
        self.assertEqual(api.call_args.kwargs['payload']['payer']['email'],'buyer@testuser.com')
        self.assertEqual(order.correo_cliente,'customer@example.test')
    @override_settings(PAYMENTS_LIVE=True)
    def test_production_rejects_test_credentials(self):
        with patch('apps.pagos.services.mercadopago.api',return_value={'tags':['test_user']}):
            with self.assertRaises(ValidationError):mercadopago.account()
    def test_environment_change_rejects_old_attempt(self):
        order=self.order();IntentoPago.objects.create(pedido=order,proveedor='mercadopago',en_vivo=True)
        with self.assertRaises(ValidationError):confirm('mercadopago',self.data(order))
        self.assertFalse(CorreoPendiente.objects.exists())

@override_settings(DEBUG=False,MAIL_PROVIDER='resend',RESEND_API_KEY='test-key-not-real',DEFAULT_FROM_EMAIL='Carranco <mail@example.test>')
class OutboxTransportTests(TestCase):
    def queue(self):
        return queue_email('test-event', 'recipient@example.test','Prueba','Texto','<p>Texto</p>')
    def test_resend_payload_and_idempotency(self):
        row=self.queue();response=Mock(status_code=200);response.json.return_value={'id':'email-123'}
        with patch('apps.core.correos.requests.post',return_value=response) as post:
            self.assertTrue(deliver_email(row.pk));self.assertFalse(deliver_email(row.pk))
        self.assertEqual(post.call_count,1)
        self.assertEqual(post.call_args.kwargs['headers']['Idempotency-Key'],'carranco/test-event')
        self.assertEqual(post.call_args.kwargs['json']['to'],['recipient@example.test'])
    def test_provider_error_not_leaked(self):
        row=self.queue();response=Mock(status_code=403,text='PRIVATE API KEY')
        with patch('apps.core.correos.requests.post',return_value=response):self.assertFalse(deliver_email(row.pk))
        row.refresh_from_db();self.assertNotIn('PRIVATE',row.ultimo_error);self.assertIn('403',row.ultimo_error)
    def test_expired_link_not_sent(self):
        row=self.queue();row.vence_at=timezone.now()-timedelta(seconds=1);row.save()
        with patch('apps.core.correos.requests.post') as post:self.assertFalse(deliver_email(row.pk))
        post.assert_not_called();row.refresh_from_db();self.assertEqual(row.estado,'cancelado')
    def test_missing_config_does_not_exhaust_retry_attempts(self):
        row=self.queue()
        with override_settings(RESEND_API_KEY=''):
            self.assertFalse(deliver_email(row.pk))
        row.refresh_from_db();self.assertEqual(row.intentos,0);self.assertEqual(row.estado,'pendiente')
    def test_inflight_lease_and_idempotency_window(self):
        row=self.queue();row.estado='enviando';row.bloqueo_hasta=timezone.now()+timedelta(minutes=1);row.save()
        with patch('apps.core.correos.requests.post') as post:self.assertFalse(deliver_email(row.pk))
        post.assert_not_called()
        row.estado='pendiente';row.intentos=1;row.primer_intento_at=timezone.now()-timedelta(hours=24);row.save()
        with patch('apps.core.correos.requests.post') as post:self.assertFalse(deliver_email(row.pk))
        post.assert_not_called();row.refresh_from_db();self.assertEqual(row.estado,'fallido')
