from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path,include
from django.views.generic import RedirectView
from apps.catalogo.views import legacy_detail
urlpatterns=[path("admin/",admin.site.urls),path("dashboard/",include("apps.dashboard.urls")),path("productos/",include("apps.catalogo.urls")),path("carrito/",include("apps.carrito.urls")),path("cuenta/",include("apps.cuentas.urls")),path("pagos/",include("apps.pagos.urls")),path("",include("apps.pedidos.urls")),path("",include("apps.core.urls")),path("index.html",RedirectView.as_view(pattern_name="core:index",permanent=False)),path("productos.html",RedirectView.as_view(pattern_name="catalogo:productos",query_string=True,permanent=False)),path("producto.html",legacy_detail),path("carrito.html",RedirectView.as_view(pattern_name="carrito:detalle",permanent=False)),path("cuenta.html",RedirectView.as_view(pattern_name="cuentas:perfil",permanent=False)),path("checkout.html",RedirectView.as_view(pattern_name="pedidos:checkout",permanent=False))]
if settings.DEBUG: urlpatterns+=static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)
