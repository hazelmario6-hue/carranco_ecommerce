from django.urls import path
from . import views
app_name="pagos"
urlpatterns=[path("consultar/<str:numero>/",views.consult,name="consultar"),path("iniciar/<str:numero>/",views.pay,name="iniciar"),path("webhook/mercadopago/",views.webhook_mp,name="webhook_mp")]
