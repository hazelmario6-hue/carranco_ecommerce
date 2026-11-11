"""Presentation isolation and cart/auth integration for APK mode."""
from django.test import TestCase, Client
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model
from apps.catalogo.models import Categoria, Producto
from apps.carrito.services import KEY

class AppModeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        category = Categoria.objects.create(nombre='Frescos', slug='frescos')
        cls.product = Producto.objects.create(sku='APP-TEST', nombre='Queso de prueba',
            slug='queso-prueba', legacy_id='app-test', categoria=category, descripcion='Prueba',
            presentacion='400 g', precio_catalogo=100, precio_academico=2, stock=10, destacado=True)
        cls.user = get_user_model().objects.create_user(username='app-user', password='test-only-password')

    def app_client(self):
        return Client(HTTP_USER_AGENT='Android WebView CarrancoApp/2')

    def test_normal_and_mobile_browsers_keep_web(self):
        for ua in ['Desktop', 'Mozilla/5.0 Android Mobile']:
            response = self.client.get('/', HTTP_USER_AGENT=ua)
            self.assertContains(response, 'class="site-footer"')
            self.assertNotContains(response, 'class="app-bottom-nav"')
            self.assertNotContains(response, 'css/app.css')

    def test_app_pages_render_with_local_navigation(self):
        client = self.app_client()
        for path in ['/', '/productos/', '/productos/queso-prueba/', '/carrito/', '/cuenta/login/', '/cuenta/registro/', '/nosotros/', '/contacto/', '/ayuda/']:
            with self.subTest(path=path):
                response = client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'class="app-bottom-nav"')
                self.assertNotContains(response, 'class="site-footer"')
                self.assertIn('User-Agent', response['Vary'])
                self.assertIn('Cookie', response['Vary'])

    def test_disclosure_is_available_in_about(self):
        response = self.app_client().get('/app/acerca/')
        self.assertContains(response, 'Proyecto académico universitario')
        self.assertContains(response, 'No representa ni sustituye')
        self.assertNotContains(self.app_client().get('/'), 'footer-disclosure')
        self.assertIn('Proyecto académico universitario', render_to_string('base.html', {'footer_only': True}))

    def test_preview_persists_and_can_be_reset(self):
        response = self.client.get('/?modo=app')
        self.assertTrue(response.cookies['carranco_app_preview']['httponly'])
        self.assertContains(self.client.get('/productos/'), 'class="app-bottom-nav"')
        self.client.get('/?modo=web')
        self.assertNotContains(self.client.get('/'), 'class="app-bottom-nav"')

    def test_app_marker_does_not_grant_dashboard_access(self):
        response = self.app_client().get('/dashboard/')
        self.assertIn(response.status_code, [302, 403])
        response = self.app_client().get('/admin/login/')
        self.assertNotContains(response, 'class="app-bottom-nav"')

    def test_cart_login_and_logout_keep_app_mode(self):
        client = self.app_client()
        response = client.post('/carrito/actualizar/', {'producto': self.product.pk, 'cantidad': 1, 'operacion': 'add'})
        self.assertIn(response.status_code, [200, 302])
        self.assertEqual(client.session[KEY][str(self.product.pk)], 1)
        client.force_login(self.user)
        self.assertContains(client.get('/cuenta/'), 'class="app-bottom-nav"')
        self.assertIn('no-store', client.get('/carrito/')['Cache-Control'])
        client.post('/cuenta/logout/')
        self.assertContains(client.get('/'), 'class="app-bottom-nav"')

    def test_app_does_not_bypass_csrf(self):
        client = Client(enforce_csrf_checks=True, HTTP_USER_AGENT='CarrancoApp/2')
        response = client.post('/carrito/actualizar/', {'producto': self.product.pk, 'cantidad': 1, 'operacion': 'add'})
        self.assertEqual(response.status_code, 403)
