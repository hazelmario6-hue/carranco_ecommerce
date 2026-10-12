from django.urls import path
from . import views
app_name="catalogo"
urlpatterns=[path("",views.catalog,name="productos"),path("<slug:slug>/",views.detail,name="detalle")]
