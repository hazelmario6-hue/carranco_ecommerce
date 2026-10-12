from django.urls import path
from . import views
app_name="dashboard"
urlpatterns=[path("",views.dashboard,name="inicio"),path("productos/",views.products,name="productos"),path("productos/nuevo/",views.product_edit,name="producto_nuevo"),path("productos/<int:pk>/",views.product_edit,name="producto_editar"),path("inventario/",views.inventory,name="inventario"),path("inventario/<int:pk>/ajuste/",views.stock_adjust,name="ajuste"),path("pedidos/",views.orders,name="pedidos"),path("pedidos/<int:pk>/",views.order_detail,name="pedido_detalle"),path("clientes/",views.customers,name="clientes"),path("clientes/<int:pk>/",views.customer,name="cliente_detalle"),path("reportes/",views.reports,name="reportes"),path("exportar/pedidos.csv",views.export,name="csv")]
