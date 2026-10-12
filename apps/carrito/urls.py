from django.urls import path
from . import views
app_name="carrito"
urlpatterns=[path("",views.detail,name="detalle"),path("actualizar/",views.mutate,name="actualizar"),path("importar/",views.import_legacy,name="importar")]
