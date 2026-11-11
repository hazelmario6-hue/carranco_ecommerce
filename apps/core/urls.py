from django.urls import path
from . import views
app_name="core"
urlpatterns=[path("app/acerca/",views.acerca_app,name="acerca_app"),path("",views.index,name="index"),path("nosotros/",views.nosotros,name="nosotros"),path("contacto/",views.contacto,name="contacto"),path("ayuda/",views.ayuda,name="ayuda")]
