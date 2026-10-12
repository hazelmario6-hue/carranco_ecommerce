import io
import json
import uuid
import time
import hmac
import hashlib
import base64
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
from django.test import TestCase,Client,override_settings,RequestFactory
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group,Permission
from django.core.management import call_command
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import IntegrityError,transaction,connection
from django.db.models.deletion import ProtectedError
from apps.catalogo.models import Producto,Categoria
from apps.cuentas.models import Direccion,PerfilCliente
from apps.carrito.services import summarize,change,KEY
from apps.pedidos.models import Pedido,HistorialPedido,MovimientoInventario
from apps.pedidos.services import create_order,make_quote,adjust_stock,transition,cancel_pending
from apps.pagos.models import Pago,IntentoPago
from apps.pagos.services.confirmation import confirm
from apps.pagos.services import mercadopago,openpay
from apps.pagos.services.gateway import start
from apps.dashboard.views import csv_safe
User=get_user_model()
class CommerceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_carranco",stdout=io.StringIO())
        call_command("create_carranco_groups",stdout=io.StringIO())
        cls.user=User.objects.create_user(username="cliente@example.test",email="cliente@example.test",password="Clave-universitaria-2026",first_name="Mario",last_name="Ávalos")
        cls.other=User.objects.create_user(username="otro@example.test",email="otro@example.test",password="Otra-clave-valida-2026")
        PerfilCliente.objects.create(usuario=cls.user,telefono="4441234567")
        cls.staff=User.objects.create_superuser(username="admin",email="admin@example.test",password="Clave-administrador-2026")
        cls.address=Direccion.objects.create(usuario=cls.user,calle="Universidad",numero_exterior="100",colonia="Centro",codigo_postal="78000",ciudad="San Luis Potosí",estado="SLP")
        cls.foreign_address=Direccion.objects.create(usuario=cls.other,calle="Otra",numero_exterior="2",colonia="Centro",codigo_postal="78000",ciudad="SLP",estado="SLP")
    def setUp(self):
        self.product=Producto.objects.get(legacy_id="ranchero")
    def order(self,qty=2,provider="mercadopago",session=None,key=None,quote=None):
        session=session if session is not None else {KEY:{str(self.product.pk):qty}}
        return create_order(self.user,session,self.address.pk,provider,key or uuid.uuid4(),quote or make_quote(self.user,summarize(session)))
    def verified(self,order,status="aprobado",identifier="99001"):
        return {"id":identifier,"reference":str(order.referencia),"amount":order.total_academico,"currency":"MXN","status":status,"method":"credit_card"}
    def login(self):
        self.client.force_login(self.user)
    def test_01_mysql_is_real(self):
        self.assertEqual(connection.vendor,"mysql")
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            self.assertTrue(cursor.fetchone()[0].startswith("8."))
    def test_02_seed_preserves_data(self):
        self.product.stock=14;self.product.precio_catalogo=Decimal("112.00");self.product.save()
        call_command("seed_carranco",stdout=io.StringIO())
        self.product.refresh_from_db();self.assertEqual(self.product.stock,14);self.assertEqual(self.product.precio_catalogo,Decimal("112.00"));self.assertEqual(Producto.objects.count(),9)
    def test_03_public_templates_render(self):
        for path in ["/","/productos/","/productos/queso-ranchero/","/nosotros/","/contacto/","/ayuda/","/carrito/","/cuenta/login/","/cuenta/registro/"]:
            with self.subTest(path=path):
                response=self.client.get(path);self.assertEqual(response.status_code,200);self.assertContains(response,"Proyecto académico universitario")
    def test_04_catalog_orm_filter(self):
        response=self.client.get("/productos/",{"q":"Panela","categoria":"frescos"})
        self.assertEqual(len(response.context["coincidencias"]),1)
        self.assertContains(response,"/productos/queso-panela/")
    def test_05_catalog_empty(self):
        response=self.client.get("/productos/",{"q":"inexistente"})
        self.assertEqual(len(response.context["coincidencias"]),0);self.assertContains(response,"No encontramos productos")
    def test_06_legacy_navigation(self):
        response=self.client.get("/producto.html?id=ranchero")
        self.assertRedirects(response,"/productos/queso-ranchero/")
    def test_07_registration(self):
        response=self.client.post("/cuenta/registro/",{"first_name":"Hazel","last_name":"Ávalos","email":"NUEVO@example.test","telefono":"4441234567","password1":"Mi-clave-larga-2026","password2":"Mi-clave-larga-2026","is_staff":"1","is_superuser":"1"})
        self.assertRedirects(response,"/cuenta/")
        user=User.objects.get(username="nuevo@example.test");self.assertFalse(user.is_staff);self.assertFalse(user.is_superuser);self.assertTrue(user.check_password("Mi-clave-larga-2026"))
    def test_08_weak_password_rejected(self):
        response=self.client.post("/cuenta/registro/",{"first_name":"A","last_name":"B","email":"weak@example.test","telefono":"4441234567","password1":"123","password2":"123"})
        self.assertEqual(response.status_code,200);self.assertFalse(User.objects.filter(email="weak@example.test").exists())
    def test_09_login_correct_wrong(self):
        response=self.client.post("/cuenta/login/",{"username":self.user.username,"password":"incorrecta"})
        self.assertContains(response,"Usuario o contraseña incorrectos")
        response=self.client.post("/cuenta/login/",{"username":self.user.username,"password":"Clave-universitaria-2026"})
        self.assertRedirects(response,"/cuenta/")
    def test_10_login_blocked(self):
        for _ in range(5): self.client.post("/cuenta/login/",{"username":self.user.username,"password":"incorrecta"})
        response=self.client.post("/cuenta/login/",{"username":self.user.username,"password":"Clave-universitaria-2026"})
        self.assertContains(response,"Demasiados intentos")
    def test_11_login_keeps_cart(self):
        self.client.post("/carrito/actualizar/",{"producto":self.product.pk,"cantidad":1,"operacion":"add"})
        self.client.post("/cuenta/login/",{"username":self.user.username,"password":"Clave-universitaria-2026"})
        self.assertEqual(self.client.session[KEY][str(self.product.pk)],1)
    def test_12_logout_requires_post(self):
        self.login();self.assertEqual(self.client.get("/cuenta/logout/").status_code,405)
        response=self.client.post("/cuenta/logout/");self.assertEqual(response.status_code,302);self.assertNotIn("_auth_user_id",self.client.session)
    def test_13_profile(self):
        self.login();self.client.post("/cuenta/",{"first_name":"Hazel Mario","last_name":"Ávalos","telefono":"4447654321"})
        self.user.refresh_from_db();self.assertEqual(self.user.first_name,"Hazel Mario")
    def test_14_address_ownership(self):
        self.login();response=self.client.get(f"/cuenta/direcciones/{self.foreign_address.pk}/")
        self.assertEqual(response.status_code,404)
    def test_15_address_validation(self):
        self.login();response=self.client.post("/cuenta/direcciones/",{"calle":"Calle","numero_exterior":"5","colonia":"Centro","codigo_postal":"abc","ciudad":"SLP","estado":"SLP"})
        self.assertEqual(response.status_code,200);self.assertEqual(self.user.direcciones.count(),1)
    def test_16_cart_mutations(self):
        session=self.client.session
        change(session,self.product.pk,2,"add");change(session,self.product.pk,1,"add")
        self.assertEqual(summarize(session)["count"],3)
        change(session,self.product.pk,1);self.assertEqual(summarize(session)["count"],1)
        change(session,self.product.pk,0);self.assertEqual(summarize(session)["count"],0)
    def test_17_cart_rejects_stock(self):
        self.product.stock=1;self.product.save()
        with self.assertRaises(ValidationError): change(self.client.session,self.product.pk,2,"add")
    def test_18_cart_rejects_price_in_json(self):
        response=self.client.post("/carrito/actualizar/",data=json.dumps({"producto":self.product.pk,"cantidad":1,"precio":1}),content_type="application/json")
        self.assertEqual(response.status_code,400)
    def test_19_legacy_import_idempotent(self):
        body=json.dumps([{"id":"ranchero","quantity":2}])
        for _ in range(2):
            response=self.client.post("/carrito/importar/",data=body,content_type="application/json");self.assertEqual(response.status_code,200)
        self.assertEqual(self.client.session[KEY][str(self.product.pk)],2)
        self.assertEqual(response.json()["warnings"],[])
    def test_20_checkout_server_totals(self):
        order=self.order(2)
        self.assertEqual(order.subtotal_catalogo,Decimal("190.00"));self.assertEqual(order.total_catalogo,Decimal("269.00"));self.assertEqual(order.total_academico,Decimal("4.00"))
        self.product.refresh_from_db();self.assertEqual(self.product.stock,20);self.assertEqual(self.product.stock_reservado,2)
    def test_21_checkout_idempotency(self):
        key=uuid.uuid4();a=self.order(key=key);b=self.order(key=key)
        self.assertEqual(a.pk,b.pk);self.product.refresh_from_db();self.assertEqual(self.product.stock_reservado,2)
    def test_22_checkout_other_address_rejected(self):
        session={KEY:{str(self.product.pk):1}}
        with self.assertRaises(ValidationError):create_order(self.user,session,self.foreign_address.pk,"mercadopago",uuid.uuid4(),make_quote(self.user,summarize(session)))
    def test_23_price_change_requires_new_consent(self):
        session={KEY:{str(self.product.pk):1}};quote=make_quote(self.user,summarize(session));self.product.precio_academico=Decimal("3.00");self.product.save()
        with self.assertRaises(ValidationError):self.order(qty=1,session=session,quote=quote)
    def test_24_checkout_form_and_consent(self):
        self.login();session=self.client.session;session[KEY]={str(self.product.pk):2};session.save()
        response=self.client.get("/checkout/");initial=response.context["form"].initial
        data={"direccion":self.address.pk,"proveedor":"mercadopago","clave":initial["clave"],"resumen":initial["resumen"],"total":0,"precio":0}
        self.client.post("/checkout/",data);self.assertEqual(Pedido.objects.count(),0)
        data["aceptar"]="on";response=self.client.post("/checkout/",data)
        order=Pedido.objects.get();self.assertEqual(order.total_academico,Decimal("4.00"));self.assertEqual(response.status_code,302)
    def test_25_confirmation_browser_cannot_approve(self):
        order=self.order();self.login();response=self.client.get(f"/mis-pedidos/{order.numero}/confirmacion/?status=approved&payment_id=123")
        self.assertContains(response,"Todavía no hay un pago aprobado");order.refresh_from_db();self.assertEqual(order.estado_pago,"pendiente")
    def test_26_foreign_history_denied(self):
        order=self.order();self.client.force_login(self.other);self.assertEqual(self.client.get(f"/mis-pedidos/{order.numero}/").status_code,404)
    def test_27_approved_payment_once(self):
        order=self.order();data=self.verified(order)
        confirm("mercadopago",data);confirm("mercadopago",data)
        self.product.refresh_from_db();order.refresh_from_db();self.assertEqual(self.product.stock,18);self.assertEqual(self.product.stock_reservado,0);self.assertEqual(MovimientoInventario.objects.count(),1);self.assertEqual(Pago.objects.count(),1);self.assertEqual(order.estado,"pagado")
    def test_28_pending_rejected_approved(self):
        order=self.order()
        confirm("mercadopago",self.verified(order,"pendiente"));confirm("mercadopago",self.verified(order,"rechazado"))
        self.product.refresh_from_db();self.assertEqual(self.product.stock,20)
        confirm("mercadopago",self.verified(order));self.product.refresh_from_db();self.assertEqual(self.product.stock,18)
    def test_29_payment_amount_currency_ref(self):
        order=self.order()
        for field,value in [("amount",Decimal("0.01")),("currency","USD"),("reference",str(uuid.uuid4()))]:
            data=self.verified(order);data[field]=value
            with self.assertRaises(ValidationError):confirm("mercadopago",data)
        self.assertEqual(Pago.objects.count(),0)
    def test_30_approved_not_regressed(self):
        order=self.order();confirm("mercadopago",self.verified(order));confirm("mercadopago",self.verified(order,"pendiente"));order.refresh_from_db();self.assertEqual(order.estado_pago,"aprobado")
    def test_31_cancel_release_and_late_payment(self):
        order=self.order();cancel_pending(order.pk,self.user);confirm("mercadopago",self.verified(order))
        self.product.refresh_from_db();order.refresh_from_db();self.assertEqual(self.product.stock,20);self.assertEqual(self.product.stock_reservado,0);self.assertEqual(order.estado_pago,"revision")
    def test_32_expired_reservation(self):
        order=self.order();order.reserva_expira_at=timezone.now()-timedelta(minutes=1);order.save()
        call_command("expire_reservations",stdout=io.StringIO());self.product.refresh_from_db();self.assertEqual(self.product.stock_reservado,0)
    def test_33_no_paid_cancel_or_auto_refund(self):
        order=self.order();confirm("mercadopago",self.verified(order))
        with self.assertRaises(ValidationError):cancel_pending(order.pk,self.user)
        self.product.refresh_from_db();self.assertEqual(self.product.stock,18)
    def test_34_staff_protection(self):
        self.assertEqual(self.client.get("/dashboard/").status_code,302)
        self.login();self.assertEqual(self.client.get("/dashboard/").status_code,403);self.assertEqual(self.client.get("/dashboard/productos/nuevo/").status_code,403)
    def test_35_staff_dashboard_pages(self):
        self.client.force_login(self.staff)
        for path in ["/dashboard/","/dashboard/productos/","/dashboard/inventario/","/dashboard/pedidos/","/dashboard/clientes/","/dashboard/reportes/","/admin/"]:
            with self.subTest(path=path):self.assertEqual(self.client.get(path).status_code,200)
    def test_36_inventory_audit(self):
        adjust_stock(self.product.pk,10,self.staff,"Carga académica adicional")
        self.product.refresh_from_db();self.assertEqual(self.product.stock,30);movement=MovimientoInventario.objects.get();self.assertEqual(movement.usuario_admin,self.staff);self.assertEqual(movement.cantidad,10)
    def test_37_inventory_reserves_protected(self):
        self.order()
        with self.assertRaises(ValidationError):adjust_stock(self.product.pk,-19,self.staff,"No debería dejar menos de la reserva")
    def test_38_order_transitions(self):
        order=self.order();confirm("mercadopago",self.verified(order))
        for state in ["preparando","en_camino","entregado"]:transition(order.pk,state,self.staff,"Cambio académico autorizado")
        with self.assertRaises(ValidationError):transition(order.pk,"preparando",self.staff,"Retroceso no permitido")
        order.refresh_from_db();self.assertEqual(order.estado,"entregado")
    def test_39_no_delete_historical_product(self):
        self.order()
        with self.assertRaises(ProtectedError):self.product.delete()
    def test_40_csrf_required(self):
        client=Client(enforce_csrf_checks=True)
        self.assertEqual(client.post("/carrito/actualizar/",{"producto":self.product.pk,"cantidad":1,"operacion":"add"}).status_code,403)
        self.assertEqual(client.post("/cuenta/login/",{"username":"admin","password":"anything"}).status_code,403)
    def test_41_csv_and_formula_guard(self):
        self.order();self.client.force_login(self.staff);response=self.client.get("/dashboard/exportar/pedidos.csv")
        self.assertEqual(response.status_code,200);self.assertIn("CARR-000",response.content.decode());self.assertNotIn("password",response.content.decode().lower());self.assertTrue(csv_safe("=cmd").startswith("'"))
    def test_42_contact(self):
        response=self.client.post("/contacto/",{"nombre":"Equipo","email":"equipo@example.test","asunto":"Prueba","mensaje":"Mensaje académico válido"})
        self.assertRedirects(response,"/contacto/")
    @override_settings(MP_WEBHOOK_SECRET="secreto-exclusivo-de-pruebas")
    def test_43_mp_signature(self):
        ts=str(int(time.time()));manifest=f"id:991;request-id:request-test;ts:{ts};";signature=hmac.new(b"secreto-exclusivo-de-pruebas",manifest.encode(),hashlib.sha256).hexdigest()
        request=RequestFactory().post("/pagos/webhook/mercadopago/?data.id=991",data="{}",content_type="application/json",HTTP_X_REQUEST_ID="request-test",HTTP_X_SIGNATURE=f"ts={ts},v1={signature}")
        self.assertTrue(mercadopago.verify_signature(request))
        invalid=RequestFactory().post("/pagos/webhook/mercadopago/?data.id=991",data="{}",content_type="application/json",HTTP_X_REQUEST_ID="request-test",HTTP_X_SIGNATURE=f"ts={ts},v1=incorrecta")
        self.assertFalse(mercadopago.verify_signature(invalid))
    @override_settings(MP_ACCESS_TOKEN="TEST-only-local-fixture",MP_WEBHOOK_SECRET="secreto-exclusivo-de-pruebas",APP_URL="https://carranco.example.test")
    def test_44_webhook_real_lookup_mocked(self):
        order=self.order();ts=str(int(time.time()));manifest=f"id:991;request-id:request-test;ts:{ts};";signature=hmac.new(b"secreto-exclusivo-de-pruebas",manifest.encode(),hashlib.sha256).hexdigest()
        with patch("apps.pagos.views.mercadopago.fetch",return_value=self.verified(order,identifier="991")) as fetch:
            for _ in range(2):
                response=self.client.post("/pagos/webhook/mercadopago/?data.id=991",data=json.dumps({"type":"payment","data":{"id":"991"}}),content_type="application/json",HTTP_X_REQUEST_ID="request-test",HTTP_X_SIGNATURE=f"ts={ts},v1={signature}")
                self.assertEqual(response.status_code,200)
            self.assertEqual(fetch.call_count,2)
        self.assertEqual(MovimientoInventario.objects.count(),1)
    def test_45_unsigned_webhook_rejected(self):
        self.assertEqual(self.client.post("/pagos/webhook/mercadopago/?data.id=99",data="{}",content_type="application/json").status_code,401)
    @override_settings(MP_ACCESS_TOKEN="TEST-only-local-fixture",MP_WEBHOOK_SECRET="signature",APP_URL="https://carranco.example.test")
    def test_46_payment_start_reuses_attempt(self):
        order=self.order()
        with patch("apps.pagos.services.gateway.mercadopago.create",return_value=("pref-test","https://www.mercadopago.com.mx/checkout/test")) as creator:
            a=start(order.pk,self.user);b=start(order.pk,self.user);self.assertEqual(a,b);self.assertEqual(creator.call_count,1)
    @override_settings(MP_ACCESS_TOKEN="TEST-only-local-fixture",MP_WEBHOOK_SECRET="signature",APP_URL="https://carranco.example.test")
    def test_47_provider_payload_uses_decimal(self):
        order=self.order()
        with patch("apps.pagos.services.mercadopago.api",side_effect=[{"id":123,"tags":["test_user"]},{"id":"pref","sandbox_init_point":"https://www.mercadopago.com.mx/checkout/test"}]) as api:
            mercadopago.create(order)
            payload=api.call_args.kwargs["payload"];self.assertEqual(payload["items"][0]["unit_price"],Decimal("4.00"));self.assertNotIn("card",payload)
    @override_settings(OPENPAY_MERCHANT_ID="m12345678901234567890",OPENPAY_PRIVATE_KEY="test-private",OPENPAY_WEBHOOK_USER="webhook",OPENPAY_WEBHOOK_PASSWORD="unique-test-password",APP_URL="https://carranco.example.test")
    def test_48_openpay_confirmation_once(self):
        order=self.order(provider="openpay");confirm("openpay",self.verified(order,identifier="charge123"));confirm("openpay",self.verified(order,identifier="charge123"));self.product.refresh_from_db();self.assertEqual(self.product.stock,18)
    @override_settings(OPENPAY_WEBHOOK_USER="webhook",OPENPAY_WEBHOOK_PASSWORD="unique-test-password")
    def test_49_openpay_basic_verification(self):
        basic=base64.b64encode(b"webhook:unique-test-password").decode()
        response=self.client.post("/pagos/webhook/openpay/",data=json.dumps({"type":"verification","verification_code":"code-test"}),content_type="application/json",HTTP_AUTHORIZATION="Basic "+basic)
        self.assertEqual(response.status_code,200);self.assertEqual(self.client.post("/pagos/webhook/openpay/",data="{}",content_type="application/json").status_code,401)
    def test_50_secrets_not_in_frontend(self):
        self.login();order=self.order()
        for path in ["/","/checkout/",f"/mis-pedidos/{order.numero}/"]:
            response=self.client.get(path);body=response.content.decode();self.assertNotIn("SECRET_KEY=",body);self.assertNotIn(self.user.password,body);self.assertNotIn("MP_ACCESS_TOKEN",body)
    def test_51_stock_constraint(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():Producto.objects.filter(pk=self.product.pk).update(stock_reservado=21)
    def test_52_operator_read_only(self):
        operator=User.objects.create_user("operador",password="Mi-clave-operador-2026",is_staff=True);operator.groups.add(Group.objects.get(name="Carranco Operadores"));self.client.force_login(operator)
        self.assertEqual(self.client.get("/dashboard/productos/").status_code,200);self.assertEqual(self.client.get(f"/dashboard/productos/{self.product.pk}/").status_code,403)
    def test_53_product_create_edit_deactivate(self):
        self.client.force_login(self.staff)
        data={"sku":"CARR-NUEVO","nombre":"Queso de prueba","slug":"queso-prueba","legacy_id":"prueba","categoria":self.product.categoria_id,"descripcion":"Producto para validar el CRUD","presentacion":"400 g","precio_catalogo":"80.00","precio_academico":"2.00","activo":"on","en_catalogo":"on"}
        response=self.client.post("/dashboard/productos/nuevo/",data)
        self.assertRedirects(response,"/dashboard/productos/")
        product=Producto.objects.get(sku="CARR-NUEVO");self.assertEqual(product.stock,0)
        data["precio_catalogo"]="95.50";data.pop("activo");response=self.client.post(f"/dashboard/productos/{product.pk}/",data)
        self.assertRedirects(response,"/dashboard/productos/");product.refresh_from_db();self.assertEqual(product.precio_catalogo,Decimal("95.50"));self.assertFalse(product.activo)
    def test_54_remove_inactive_cart_item(self):
        session=self.client.session;change(session,self.product.pk,1,"add")
        self.product.activo=False;self.product.save()
        change(session,self.product.pk,0);self.assertEqual(summarize(session)["count"],0)
    def test_55_product_form_does_not_overwrite_concurrent_stock(self):
        from apps.dashboard.forms import ProductoForm
        data={field:getattr(self.product,field) for field in ProductoForm.Meta.fields if field not in {"imagen","categoria"}}
        data["categoria"]=self.product.categoria_id;data["nombre"]="Nombre actualizado"
        form=ProductoForm(data,instance=self.product);self.assertTrue(form.is_valid(),form.errors)
        Producto.objects.filter(pk=self.product.pk).update(stock_reservado=2)
        form.save();self.product.refresh_from_db();self.assertEqual(self.product.stock_reservado,2)
    def test_56_duplicate_payment_never_double_stock(self):
        order=self.order();confirm("mercadopago",self.verified(order,identifier="991"));confirm("mercadopago",self.verified(order,identifier="992"))
        self.product.refresh_from_db();self.assertEqual(self.product.stock,18);self.assertEqual(MovimientoInventario.objects.count(),1);self.assertEqual(Pago.objects.get(payment_id_externo="992").estado,"revision")
    @override_settings(OPENPAY_MERCHANT_ID="m12345678901234567890",OPENPAY_PRIVATE_KEY="test-private",APP_URL="https://carranco.example.test")
    def test_57_openpay_payload_no_card_data(self):
        order=self.order(provider="openpay")
        with patch("apps.pagos.services.openpay.api",return_value={"id":"charge-test","payment_method":{"url":"https://sandbox-api.openpay.mx/checkout/test"}}) as api:
            openpay.create(order,"127.0.0.1");data=api.call_args.kwargs["payload"]
            self.assertIs(data["confirm"],False);self.assertEqual(data["amount"],Decimal("4.00"));self.assertNotIn("card",data);self.assertNotIn("cvv",data)
    def test_58_bad_csrf_logout(self):
        client=Client(enforce_csrf_checks=True);client.force_login(self.user)
        self.assertEqual(client.post("/cuenta/logout/").status_code,403)

    @override_settings(OPENPAY_MERCHANT_ID="m12345678901234567890",OPENPAY_PRIVATE_KEY="test-private",OPENPAY_WEBHOOK_USER="webhook",OPENPAY_WEBHOOK_PASSWORD="unique-test-password",APP_URL="https://carranco.example.test")
    def test_60_openpay_webhook_lookup_duplicate(self):
        order=self.order(provider="openpay");basic=base64.b64encode(b"webhook:unique-test-password").decode()
        with patch("apps.pagos.views.openpay.fetch",return_value=self.verified(order,identifier="charge-test")) as lookup:
            for _ in range(2):
                response=self.client.post("/pagos/webhook/openpay/",data=json.dumps({"type":"charge.succeeded","transaction":{"id":"charge-test"}}),content_type="application/json",HTTP_AUTHORIZATION="Basic "+basic)
                self.assertEqual(response.status_code,200)
            self.assertEqual(lookup.call_count,2)
        self.assertEqual(MovimientoInventario.objects.count(),1)
    def test_61_legacy_import_warns_stock_cap(self):
        self.product.stock=1;self.product.save()
        response=self.client.post("/carrito/importar/",data=json.dumps([{"id":"ranchero","quantity":2}]),content_type="application/json")
        self.assertEqual(response.json()["count"],1);self.assertIn("ajustada",response.json()["warnings"][0])
    def test_62_provider_money_validation(self):
        from apps.pagos.services.http import money
        for value in ["NaN","Infinity","0","-2","1.005","invalid"]:
            with self.assertRaises(ValidationError):money(value)
        self.assertEqual(money("2.00"),Decimal("2.00"))
        from apps.pagos.services.http import external_id
        for value in [None,True,"", "http://invalid", "x"*151]:
            with self.assertRaises(ValidationError):external_id(value)

    def test_63_product_image_upload(self):
        import tempfile
        from pathlib import Path
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        image=io.BytesIO();Image.new("RGB",(2,2),(255,255,255)).save(image,format="PNG")
        self.client.force_login(self.staff)
        data={"sku":"CARR-IMAGEN","nombre":"Producto con imagen","slug":"producto-imagen","legacy_id":"imagen","categoria":self.product.categoria_id,"descripcion":"Imagen de prueba","presentacion":"400 g","precio_catalogo":"80.00","precio_academico":"2.00","activo":"on","en_catalogo":"on","imagen":SimpleUploadedFile("producto.png",image.getvalue(),content_type="image/png")}
        with tempfile.TemporaryDirectory() as folder,override_settings(MEDIA_ROOT=folder):
            response=self.client.post("/dashboard/productos/nuevo/",data)
            self.assertRedirects(response,"/dashboard/productos/")
            product=Producto.objects.get(sku="CARR-IMAGEN");self.assertTrue((Path(folder)/product.imagen.name).is_file());self.assertTrue(product.foto.startswith("/media/productos/"))
    def test_64_private_pages_no_cache(self):
        self.login();response=self.client.get("/cuenta/");self.assertIn("no-store",response["Cache-Control"])

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.test import TransactionTestCase
from django.db import close_old_connections
class ConcurrencyTests(TransactionTestCase):
    reset_sequences=True
    def test_two_orders_last_unit(self):
        category=Categoria.objects.create(nombre="Frescos",slug="frescos")
        product=Producto.objects.create(sku="CARR-CONCURRENCIA",nombre="Última unidad",slug="ultima-unidad",legacy_id="ultima",categoria=category,descripcion="Prueba",presentacion="400 g",precio_catalogo=Decimal("80"),precio_academico=Decimal("2"),stock=1)
        users=[User.objects.create_user(username=f"concurrent-{n}",email=f"{n}@example.test",password="Clave-larga-prueba-2026") for n in range(2)]
        addresses=[Direccion.objects.create(usuario=user,calle="Calle",numero_exterior="1",colonia="Centro",codigo_postal="78000",ciudad="SLP",estado="SLP") for user in users]
        barrier=Barrier(2)
        def worker(index):
            close_old_connections()
            try:
                user=User.objects.get(pk=users[index].pk)
                session={KEY:{str(product.pk):1}}
                quote=make_quote(user,summarize(session));barrier.wait(timeout=10)
                try:create_order(user,session,addresses[index].pk,"mercadopago",uuid.uuid4(),quote);return "created"
                except ValidationError:return "rejected"
            finally:close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes=list(pool.map(worker,range(2)))
        self.assertCountEqual(outcomes,["created","rejected"])
        product.refresh_from_db();self.assertEqual(product.stock_reservado,1);self.assertEqual(Pedido.objects.count(),1)
