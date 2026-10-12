from django.urls import path
from . import views
app_name="cuentas"
urlpatterns=[path("login/",views.Acceso.as_view(),name="login"),path("registro/",views.registro,name="registro"),path("logout/",views.Salir.as_view(),name="logout"),path("",views.perfil,name="perfil"),path("direcciones/",views.direcciones,name="direcciones"),path("direcciones/<int:pk>/",views.direcciones,name="editar_direccion"),path("direcciones/<int:pk>/eliminar/",views.borrar_direccion,name="borrar_direccion")]
