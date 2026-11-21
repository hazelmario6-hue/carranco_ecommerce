"""Regression checks for the November storefront and checkout update."""
import io
import json
import uuid
from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, Client, override_settings
from django.utils import timezone
from apps.catalogo.models import Producto, Categoria
from apps.carrito.services import KEY, summarize
from apps.core.models import Promocion, Auditoria
from apps.core.context_processors import SOCIAL_LINKS
from apps.cuentas.models import Direccion, VerificacionCorreo
from apps.dashboard.forms import PromocionForm
from apps.pagos.services.gateway import configured, start
from apps.pedidos.models import Pedido
from apps.pedidos.services import create_order, make_quote

class PendingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cat = Categoria.objects.create(nombre="Mantequilla", slug="mantequilla")
        cls.product = Producto.objects.create(sku="BUTTER", legacy_id="butter-test", nombre="Mantequilla Carranco", slug="butter-test", categoria=cat,
            descripcion="Mantequilla sin sal", presentacion="90 g", precio_catalogo="60.00", precio_academico="60.00", stock=18,
            imagen_url="https://example.test/mantequilla.jpg")
        cls.user = get_user_model().objects.create_user("cliente", email="cliente@example.test", password="test-password-2026")
        cls.admin = get_user_model().objects.create_superuser("admin", email="admin@example.test", password="test-password-2026")
        cls.operator = get_user_model().objects.create_user("operador", password="test-password-2026", is_staff=True)
        VerificacionCorreo.objects.create(usuario=cls.user, email=cls.user.email, verificado_at=timezone.now())
        cls.address = Direccion.objects.create(usuario=cls.user, calle="Calle", numero_exterior="1", colonia="Centro", codigo_postal="78000", ciudad="SLP", estado="SLP")

    def cart(self, quantity=1):
        session = self.client.session
        session[KEY] = {str(self.product.pk): quantity}
        session.save()

    def mutation(self, **data):
        return self.client.post('/carrito/actualizar/', data=json.dumps(data), content_type='application/json')

    def promo(self, **kwargs):
        values = dict(titulo="Selección de mantequilla", descripcion="Para preparar tus recetas.", imagen_alt="Mantequilla Carranco de 90 g", producto=self.product)
        values.update(kwargs)
        return Promocion.objects.create(**values)

    def form_data(self):
        return dict(titulo="Promoción de fin de semana", descripcion="Selección para compartir", producto=self.product.pk,
            imagen_url="", imagen_alt="Mantequilla Carranco de 90 g", enlace="", texto_boton="Ver producto", inicio="", fin="", activa="on", orden="2")

    def test_cart_cap_is_stock_not_twenty(self):
        self.cart(18)
        self.assertContains(self.client.get('/carrito/'), 'max="18"')
        response = self.mutation(producto=self.product.pk, cantidad=20, operacion="set")
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['items'][0]['cantidad'], 18)
        self.assertEqual(data['items'][0]['maximo'], 18)
        self.assertEqual(self.client.session[KEY][str(self.product.pk)], 18)

    def test_cart_json_totals_shipping_and_count(self):
        self.cart()
        data = self.mutation(producto=self.product.pk, cantidad=9, operacion="set").json()
        self.assertEqual((data['subtotal'], data['envio'], data['total'], data['count']), ('540.00', '0.00', '540.00', 9))
        data = self.mutation(producto=self.product.pk, cantidad=1, operacion="set").json()
        self.assertEqual((data['subtotal'], data['envio'], data['total']), ('60.00', '79.00', '139.00'))

    def test_stock_changed_returns_authoritative_cart(self):
        self.cart(18)
        Producto.objects.filter(pk=self.product.pk).update(stock_reservado=12)
        response = self.mutation(producto=self.product.pk, cantidad=17, operacion="set")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['items'][0]['cantidad'], 6)
        self.assertEqual(response.json()['items'][0]['maximo'], 6)
        self.assertEqual(self.client.session[KEY][str(self.product.pk)], 6)

    def test_page_reconciles_stock_and_unavailable_products(self):
        self.cart(20)
        self.client.get('/carrito/')
        self.assertEqual(self.client.session[KEY][str(self.product.pk)], 18)
        Producto.objects.filter(pk=self.product.pk).update(activo=False)
        response = self.client.get('/carrito/estado/')
        self.assertEqual(response.json()['items'], [])
        self.assertEqual(response.json()['count'], 0)
        self.assertIn('no-store', response['Cache-Control'])

    def test_clear_and_remove_return_empty_state(self):
        for action in [dict(producto=self.product.pk, cantidad=0, operacion='set'), dict(operacion='clear')]:
            self.cart()
            data = self.mutation(**action).json()
            self.assertEqual(data['items'], [])
            self.assertEqual(data['total'], '0.00')

    def test_manual_checkout_still_rejects_overstock(self):
        session = {KEY: {str(self.product.pk): 20}}
        with self.assertRaises(ValidationError):
            create_order(self.user, session, self.address.pk, 'mercadopago', uuid.uuid4(), make_quote(self.user, summarize(session)))
        self.assertEqual(Pedido.objects.count(), 0)

    @override_settings(MP_ACCESS_TOKEN="test", MP_WEBHOOK_SECRET="test", APP_URL="https://example.test",
        OPENPAY_MERCHANT_ID="merchant", OPENPAY_PRIVATE_KEY="key", OPENPAY_WEBHOOK_USER="u", OPENPAY_WEBHOOK_PASSWORD="p", OPENPAY_PRODUCTION=False)
    def test_openpay_stays_disabled_even_with_credentials(self):
        self.assertFalse(configured('openpay'))
        self.client.force_login(self.user); self.cart()
        response = self.client.get('/checkout/')
        self.assertEqual([x[0] for x in response.context['form'].fields['proveedor'].choices], ['mercadopago'])
        self.assertNotContains(response, 'Openpay')
        data = {**response.context['form'].initial, 'direccion': self.address.pk, 'proveedor': 'openpay'}
        self.assertEqual(self.client.post('/checkout/', data).status_code, 200)
        self.assertFalse(Pedido.objects.exists())
        with self.assertRaises(ValidationError):
            create_order(self.user, self.client.session, self.address.pk, 'openpay', uuid.uuid4(), data['resumen'])
        output = io.StringIO(); call_command('check_integrations', stdout=output)
        self.assertNotIn('openpay', output.getvalue().lower())

    def test_staff_app_login_redirects_even_with_customer_next(self):
        client = Client(HTTP_USER_AGENT="CarrancoApp/2")
        response = client.post('/cuenta/login/?modo=app&next=/carrito/', {'username': 'admin', 'password': 'test-password-2026'})
        self.assertRedirects(response, '/dashboard/')
        self.assertNotContains(client.get('/dashboard/'), 'app-bottom-nav')
        self.assertNotContains(client.get('/productos/?modo=app'), 'css/app.css')
        self.assertRedirects(client.get('/'), '/dashboard/')
        client.post('/cuenta/logout/')
        self.assertContains(client.get('/'), 'class="app-bottom-nav"')

    def test_client_never_gets_admin_permissions_from_app_flag(self):
        self.client.force_login(self.user)
        for url in ['/dashboard/', '/dashboard/promociones/', '/dashboard/promociones/nueva/']:
            self.assertEqual(self.client.get(url+'?modo=app').status_code, 403)

    def test_promotions_share_source_and_hide_expired_future_inactive(self):
        now = timezone.now()
        good = self.promo(titulo='PROMO ACTIVA', inicio=now-timedelta(days=1), fin=now+timedelta(days=1))
        self.promo(titulo='VENCIDA', fin=now-timedelta(seconds=1))
        self.promo(titulo='FUTURA', inicio=now+timedelta(days=1))
        self.promo(titulo='INACTIVA', activa=False)
        for url in ['/', '/?modo=app']:
            response = self.client.get(url)
            self.assertContains(response, good.titulo)
            for title in ['VENCIDA', 'FUTURA', 'INACTIVA']: self.assertNotContains(response, title)
        Producto.objects.filter(pk=self.product.pk).update(stock=0)
        self.assertNotContains(self.client.get('/?modo=app'), good.titulo)

    def test_promotions_order_and_live_product_price(self):
        last = self.promo(titulo='LAST', orden=10)
        first = self.promo(titulo='FIRST', orden=0)
        self.assertEqual(list(Promocion.objects.vigentes()), [first, last])
        Producto.objects.filter(pk=self.product.pk).update(precio_catalogo='65.50')
        self.assertContains(self.client.get('/'), '$65.50')

    def test_create_edit_disable_promotion_from_dashboard(self):
        self.client.force_login(self.admin)
        data = self.form_data()
        self.assertRedirects(self.client.post('/dashboard/promociones/nueva/', data), '/dashboard/promociones/')
        promo = Promocion.objects.get()
        self.assertContains(Client().get('/?modo=app'), promo.titulo)
        data.pop('activa'); data['titulo'] = 'Desactivada'
        self.assertRedirects(self.client.post(f'/dashboard/promociones/{promo.pk}/', data), '/dashboard/promociones/')
        self.assertFalse(Promocion.objects.vigentes().exists())
        self.assertEqual(Auditoria.objects.filter(evento__in=['crear_promocion','editar_promocion']).count(), 2)
        self.product.refresh_from_db(); self.assertEqual(self.product.stock, 18)

    def test_promotion_permissions_and_csrf(self):
        self.client.force_login(self.operator)
        self.assertEqual(self.client.get('/dashboard/promociones/').status_code, 403)
        self.operator.user_permissions.add(Permission.objects.get(codename='view_promocion'))
        self.assertEqual(self.client.get('/dashboard/promociones/').status_code, 200)
        self.assertEqual(self.client.post('/dashboard/promociones/nueva/', self.form_data()).status_code, 403)
        client = Client(enforce_csrf_checks=True); client.force_login(self.admin)
        self.assertEqual(client.post('/dashboard/promociones/nueva/', self.form_data()).status_code, 403)

    def test_promotion_dates_and_link_validation(self):
        data = self.form_data()
        data.update(inicio='2026-11-22T10:00', fin='2026-11-21T10:00')
        self.assertIn('fin', PromocionForm(data).errors)
        for link in ['javascript:alert(1)', '//example.test', '/\\example.test', 'http://example.test']:
            values = {**self.form_data(), 'enlace': link}
            self.assertIn('enlace', PromocionForm(values).errors)
        for link in ['/productos/?categoria=mantequilla', 'https://example.test/promocion']:
            form = PromocionForm({**self.form_data(), 'enlace': link})
            self.assertTrue(form.is_valid(), form.errors)

    def test_seed_is_idempotent_and_preserves_edits(self):
        self.product.legacy_id='duo-tradicion';self.product.save()
        for _ in range(2): call_command('seed_promotions', stdout=io.StringIO())
        promo=Promocion.objects.get(clave='duo-tradicion');promo.activa=False;promo.titulo='Cambio del admin';promo.save()
        call_command('seed_promotions', stdout=io.StringIO())
        promo.refresh_from_db();self.assertFalse(promo.activa);self.assertEqual(promo.titulo,'Cambio del admin')
        self.assertEqual(Promocion.objects.count(),1)

    def test_social_urls_exact_and_no_placeholder_buttons(self):
        from html import unescape
        for url in ['/', '/?modo=app', '/contacto/']:
            body = unescape(self.client.get(url).content.decode())
            for social in SOCIAL_LINKS:
                if url != '/contacto/' or social['icono']=='whatsapp': self.assertIn(social['url'], body)
            self.assertNotIn('data-social=', body)
            self.assertNotIn('data-whatsapp', body)

    def test_known_gallery_images_have_specific_honest_descriptions(self):
        call_command('seed_carranco', stdout=io.StringIO())
        for product in Producto.objects.exclude(pk=self.product.pk):
            for photo in product.galeria_descriptiva:
                self.assertNotIn('ilustrativ', photo['alt'].lower())
                self.assertNotIn('ilustrativ', photo['caption'].lower())
                self.assertTrue(photo['alt'])
        ranchero=Producto.objects.get(legacy_id='ranchero')
        self.assertIn('300 g', ranchero.descripcion_imagen)
