from django.urls import path
from . import views
app_name="pedidos"
urlpatterns=[path("checkout/",views.checkout,name="checkout"),path("mis-pedidos/",views.history,name="historial"),path("mis-pedidos/<str:numero>/",views.detail,name="detalle"),path("mis-pedidos/<str:numero>/confirmacion/",views.confirmation,name="confirmacion"),path("mis-pedidos/<str:numero>/cancelar/",views.cancel,name="cancelar")]
