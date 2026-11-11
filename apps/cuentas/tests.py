import re
from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase,Client,override_settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.core import mail
from django.utils import timezone
from .models import VerificacionCorreo
from .pin import issue_pin,verify_pin
from .verificacion import request_verification,link_valid,consume_verification
from apps.core.correos import MailDeliveryError
from apps.core.models import CorreoPendiente
User=get_user_model()

@override_settings(DEBUG=True,MAIL_PROVIDER='console',EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',SECURE_SSL_REDIRECT=False)
class PinTests(TestCase):
    def signup(self,client=None):
        client=client or self.client
        with self.captureOnCommitCallbacks(execute=True):
            r=client.post('/cuenta/registro/',{'first_name':'Hazel','username':'hazel','email':'hazel@example.test','password1':'Otra-clave-larga-2026!','password2':'Otra-clave-larga-2026!','is_staff':'1'})
        return r,User.objects.get(username='hazel')
    def code(self):return re.search(r'es: (\d{6})',mail.outbox[-1].body).group(1)
    def test_shared_registration_web_and_app_same_url(self):
        for ua in ['Desktop','CarrancoApp/2']:
            with self.subTest(ua=ua):
                self.assertContains(Client(HTTP_USER_AGENT=ua).get('/cuenta/registro/'),'Crear cuenta')
        r,u=self.signup();self.assertRedirects(r,'/cuenta/registro/')
        self.assertFalse(u.is_active);self.assertFalse(u.is_staff)
        self.assertNotIn('_auth_user_id',self.client.session)
        response=self.client.get('/cuenta/registro/');self.assertContains(response,'ha•••@example.test');self.assertContains(response,'Verificar y entrar')
        record=VerificacionCorreo.objects.get();self.assertTrue(check_password(self.code(),record.pin_hash))
        self.assertNotEqual(record.pin_hash,self.code());self.assertFalse(CorreoPendiente.objects.exists())
        self.assertEqual(self.client.get('/cuenta/login/').status_code,200)
        self.assertNotContains(self.client.get('/cuenta/login/'),'reenviar enlace')
    def test_success_activates_logs_in_and_preserves_cart(self):
        r,u=self.signup();session=self.client.session;session['carranco_cart']={'1':2};session.save()
        code=self.code();r=self.client.post('/cuenta/registro/',{'codigo':code})
        self.assertRedirects(r,'/cuenta/');u.refresh_from_db();self.assertTrue(u.is_active)
        self.assertEqual(str(u.pk),self.client.session['_auth_user_id'])
        self.assertEqual(self.client.session['carranco_cart'],{'1':2})
        self.assertEqual(VerificacionCorreo.objects.get().pin_hash,'')
        self.assertFalse(verify_pin(u,code)[0])
    def test_five_attempts_lock_even_correct_pin(self):
        _,u=self.signup();code=self.code();wrong='000000' if code!='000000' else '111111'
        for _ in range(5):self.assertFalse(verify_pin(u,wrong)[0])
        self.assertFalse(verify_pin(u,code)[0]);self.assertFalse(User.objects.get(pk=u.pk).is_active)
        self.assertEqual(VerificacionCorreo.objects.get().pin_intentos,5)
    def test_expired_wrong_user_and_tamper(self):
        _,u=self.signup();code=self.code()
        self.assertEqual(Client().post('/cuenta/registro/',{'codigo':code,'usuario':u.pk}).status_code,200)
        self.assertFalse(User.objects.get(pk=u.pk).is_active)
        VerificacionCorreo.objects.filter(usuario=u).update(vence_at=timezone.now()-timedelta(seconds=1))
        self.assertFalse(verify_pin(u,code)[0])
    def test_resend_cooldown_hour_budget_and_old_pin_invalid(self):
        _,u=self.signup();old=self.code();self.assertFalse(issue_pin(u))
        VerificacionCorreo.objects.filter(usuario=u).update(ultimo_envio=timezone.now()-timedelta(seconds=61))
        with patch('apps.cuentas.pin.secrets.randbelow',return_value=(int(old)+1)%1000000):
            with self.captureOnCommitCallbacks(execute=True):self.assertTrue(issue_pin(u))
        self.assertFalse(verify_pin(u,old)[0]);self.assertTrue(verify_pin(u,self.code())[0])
    def test_hourly_limit(self):
        _,u=self.signup();VerificacionCorreo.objects.filter(usuario=u).update(ultimo_envio=timezone.now()-timedelta(seconds=61),envios_en_ventana=5)
        self.assertFalse(issue_pin(u))
    def test_change_email_invalidates_code_and_keeps_budget(self):
        _,u=self.signup();old=self.code()
        self.client.post('/cuenta/registro/',{'action':'change','email':'correct@example.test'})
        u.refresh_from_db();self.assertEqual(u.email,'correct@example.test')
        self.assertFalse(verify_pin(u,old)[0]);self.assertFalse(issue_pin(u))
        VerificacionCorreo.objects.filter(usuario=u).update(ultimo_envio=timezone.now()-timedelta(seconds=61))
        with self.captureOnCommitCallbacks(execute=True):issue_pin(u)
        self.assertEqual(mail.outbox[-1].to,['correct@example.test']);self.assertTrue(verify_pin(u,self.code())[0])
    def test_change_to_used_email_rejected(self):
        _,u=self.signup();User.objects.create_user('other',email='used@example.test')
        self.assertContains(self.client.post('/cuenta/registro/',{'action':'change','email':'used@example.test'}),'ya tiene una cuenta')
        u.refresh_from_db();self.assertEqual(u.email,'hazel@example.test')
    def test_pending_login_resumes_only_with_password(self):
        _,u=self.signup();client=Client()
        client.post('/cuenta/login/',{'username':u.email,'password':'wrong'})
        self.assertNotIn('registro_pendiente',client.session)
        r=client.post('/cuenta/login/',{'username':u.email,'password':'Otra-clave-larga-2026!'})
        self.assertRedirects(r,'/cuenta/registro/');self.assertNotIn('_auth_user_id',client.session)
        self.assertEqual(client.session['registro_pendiente'],u.pk)
        self.assertRedirects(client.post('/cuenta/registro/',{'codigo':self.code()}),'/cuenta/')
    def test_disabled_verified_user_cannot_resume(self):
        _,u=self.signup();verify_pin(u,self.code());u.is_active=False;u.save()
        c=Client();c.post('/cuenta/login/',{'username':u.email,'password':'Otra-clave-larga-2026!'})
        self.assertNotIn('registro_pendiente',c.session);self.assertNotIn('_auth_user_id',c.session)
    def test_existing_active_account_uses_same_screen(self):
        u=User.objects.create_user('legacy',email='legacy@example.test',password='Legacy-password-2026!');self.client.force_login(u)
        self.assertRedirects(self.client.get('/cuenta/verificar/'),'/cuenta/registro/')
        with self.captureOnCommitCallbacks(execute=True):self.client.post('/cuenta/registro/',{'action':'resend','email':'attacker@example.test'})
        self.assertEqual(mail.outbox[-1].to,[u.email])
        self.assertRedirects(self.client.post('/cuenta/registro/',{'codigo':self.code()}),'/cuenta/')
    def test_csrf_and_nostore(self):
        self.signup();client=Client(enforce_csrf_checks=True);client.cookies=self.client.cookies
        self.assertEqual(client.post('/cuenta/registro/',{'codigo':self.code()}).status_code,403)
        self.assertIn('no-store',self.client.get('/cuenta/registro/')['Cache-Control'])
    def test_delivery_failure_and_retry(self):
        with patch('apps.cuentas.pin.send_email',side_effect=MailDeliveryError('offline')):_,u=self.signup()
        self.assertFalse(VerificacionCorreo.objects.get().pin_envio_ok)
        self.assertContains(self.client.get('/cuenta/registro/'),'aún no tiene envío confirmado')
        VerificacionCorreo.objects.filter(usuario=u).update(ultimo_envio=timezone.now()-timedelta(seconds=61))
        with self.captureOnCommitCallbacks(execute=True):issue_pin(u)
        self.assertTrue(VerificacionCorreo.objects.get().pin_envio_ok)
    def test_legacy_link_remains_single_use(self):
        u=User.objects.create_user('legacy',email='legacy@example.test')
        request_verification(u)
        body=CorreoPendiente.objects.get().texto
        uid,token=re.search(r'/verificar/([^/]+)/([^/]+)/',body).groups()
        self.assertTrue(link_valid(uid,token));self.assertTrue(consume_verification(uid,token));self.assertFalse(consume_verification(uid,token))
