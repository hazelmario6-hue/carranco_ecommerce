import uuid
from datetime import timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase,override_settings
from django.utils import timezone
from apps.carrito.services import KEY,summarize
from apps.catalogo.models import Categoria,Producto
from apps.cuentas.models import Direccion,VerificacionCorreo
from .cupones import SESSION_KEY,price_with_coupon
from .models import Cupon,UsoCupon
from .services import cancel_pending,create_order,make_quote

@override_settings(MP_ACCESS_TOKEN="test",MP_WEBHOOK_SECRET="secret",APP_URL="https://example.test")
class CouponTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        category=Categoria.objects.create(nombre="Quesos",slug="coupon-cheese")
        cls.product=Producto.objects.create(sku="COUPON-1",legacy_id="coupon-product",nombre="Queso para cupón",slug="coupon-product",categoria=category,descripcion="Queso",presentacion="400 g",precio_catalogo="100.00",precio_academico="100.00",stock=50,imagen_url="https://example.test/queso.jpg")
        cls.user=get_user_model().objects.create_user("coupon-client",email="coupon@example.test",password="test-password-2026")
        VerificacionCorreo.objects.create(usuario=cls.user,email=cls.user.email,verificado_at=timezone.now())
        cls.address=Direccion.objects.create(usuario=cls.user,calle="Calle",numero_exterior="1",colonia="Centro",codigo_postal="78000",ciudad="SLP",estado="SLP")
        cls.admin=get_user_model().objects.create_superuser("coupon-admin",email="admin@example.test",password="test-password-2026")

    def cart(self,quantity=5): return {KEY:{str(self.product.pk):quantity}}
    def coupon(self,**kwargs):
        values={"codigo":"CARRANCO10","tipo":"porcentaje","valor":Decimal("10.00"),"compra_minima":Decimal("300.00"),"max_usos":10,"max_usos_cliente":1,"activo":True}
        values.update(kwargs);return Cupon.objects.create(**values)
    def order(self,coupon,user=None,address=None,quantity=5):
        user=user or self.user;address=address or self.address
        session=self.cart(quantity);session[SESSION_KEY]=coupon.codigo
        cart=summarize(session);pricing=price_with_coupon(user,cart,coupon.codigo)
        return create_order(user,session,address.pk,"mercadopago",uuid.uuid4(),make_quote(user,cart,pricing))

    def test_percentage_coupon_changes_exact_gateway_total(self):
        coupon=self.coupon();order=self.order(coupon)
        self.assertEqual((order.subtotal_catalogo,order.envio,order.descuento,order.total_catalogo,order.total_academico),(Decimal("500.00"),Decimal("0.00"),Decimal("50.00"),Decimal("450.00"),Decimal("450.00")))
        self.assertEqual(order.codigo_cupon,"CARRANCO10");self.assertEqual(UsoCupon.objects.get().descuento,Decimal("50.00"))

    def test_fixed_coupon_keeps_shipping_and_is_capped_at_subtotal(self):
        coupon=self.coupon(codigo="MENOS200",tipo="fijo",valor=Decimal("200.00"),compra_minima=0)
        order=self.order(coupon,quantity=2)
        self.assertEqual((order.subtotal_catalogo,order.envio,order.descuento,order.total_catalogo),(Decimal("200.00"),Decimal("79.00"),Decimal("200.00"),Decimal("79.00")))

    def test_dates_minimum_and_invalid_total_are_rejected(self):
        cart=summarize(self.cart(2))
        for coupon,message in [
            (self.coupon(codigo="FUTURO",inicio=timezone.now()+timedelta(hours=1)),"todavía"),
            (self.coupon(codigo="VENCIDO",fin=timezone.now()-timedelta(seconds=1)),"venció"),
            (self.coupon(codigo="MINIMO",compra_minima=Decimal("300.00")),"mínima"),
        ]:
            with self.assertRaisesMessage(ValidationError,message):price_with_coupon(self.user,cart,coupon.codigo)
        full=self.coupon(codigo="GRATIS",valor=Decimal("100.00"),compra_minima=0)
        with self.assertRaisesMessage(ValidationError,"total válido"):price_with_coupon(self.user,summarize(self.cart(5)),full.codigo)

    def test_global_and_customer_limits(self):
        coupon=self.coupon(max_usos=1,max_usos_cliente=1);self.order(coupon)
        other=get_user_model().objects.create_user("coupon-other",email="other@example.test",password="test-password-2026")
        VerificacionCorreo.objects.create(usuario=other,email=other.email,verificado_at=timezone.now())
        address=Direccion.objects.create(usuario=other,calle="Otra",numero_exterior="2",colonia="Centro",codigo_postal="78000",ciudad="SLP",estado="SLP")
        with self.assertRaisesMessage(ValidationError,"agotó"):self.order(coupon,other,address)

    def test_expired_unpaid_reservation_does_not_hold_global_use(self):
        coupon=self.coupon(max_usos=1);order=self.order(coupon)
        self.assertEqual(coupon.estado_publicacion,"Agotado")
        type(order).objects.filter(pk=order.pk).update(reserva_expira_at=timezone.now()-timedelta(seconds=1))
        self.assertEqual(coupon.usos_vigentes(),0);self.assertEqual(coupon.estado_publicacion,"Disponible")
        other=get_user_model().objects.create_user("coupon-later",email="later@example.test",password="test-password-2026")
        VerificacionCorreo.objects.create(usuario=other,email=other.email,verificado_at=timezone.now())
        address=Direccion.objects.create(usuario=other,calle="Nueva",numero_exterior="3",colonia="Centro",codigo_postal="78000",ciudad="SLP",estado="SLP")
        self.assertIsNotNone(self.order(coupon,other,address))

    def test_cancelled_pending_order_releases_coupon_use(self):
        coupon=self.coupon();order=self.order(coupon)
        cancel_pending(order.pk,self.user)
        self.assertFalse(UsoCupon.objects.exists())
        self.assertIsNotNone(self.order(coupon))

    def test_signed_quote_rejects_coupon_changed_after_review(self):
        coupon=self.coupon();session=self.cart();cart=summarize(session);quote=make_quote(self.user,cart)
        session[SESSION_KEY]=coupon.codigo
        with self.assertRaisesMessage(ValidationError,"Cambió tu selección, cupón o precio"):
            create_order(self.user,session,self.address.pk,"mercadopago",uuid.uuid4(),quote)

    def test_checkout_apply_remove_and_app_view(self):
        coupon=self.coupon();self.client.force_login(self.user)
        session=self.client.session;session[KEY]={str(self.product.pk):5};session.save()
        self.assertRedirects(self.client.post("/checkout/cupon/",{"codigo":" carranco10 "}),"/checkout/")
        for url in ["/checkout/","/checkout/?modo=app"]:
            response=self.client.get(url);self.assertContains(response,"−$50.00");self.assertContains(response,"$450.00 MXN")
        self.assertRedirects(self.client.post("/checkout/cupon/",{"accion":"quitar"}),"/checkout/")
        self.assertNotContains(self.client.get("/checkout/"),"−$50.00")

    def test_dashboard_crud_validation_and_permissions(self):
        self.client.force_login(self.admin)
        data={"codigo":"bienvenida","tipo":"porcentaje","valor":"15.00","compra_minima":"300.00","inicio":"","fin":"","max_usos":"25","max_usos_cliente":"1","activo":"on"}
        self.assertRedirects(self.client.post("/dashboard/cupones/nuevo/",data),"/dashboard/cupones/")
        coupon=Cupon.objects.get();self.assertEqual(coupon.codigo,"BIENVENIDA")
        data["valor"]="101";data["codigo"]="EXCESIVO"
        response=self.client.post("/dashboard/cupones/nuevo/",data);self.assertContains(response,"no puede superar 100")
        self.client.force_login(self.user);self.assertEqual(self.client.get("/dashboard/cupones/").status_code,403)
