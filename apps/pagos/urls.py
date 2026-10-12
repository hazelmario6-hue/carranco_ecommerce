from django.urls import path
from . import views
app_name="pagos"
urlpatterns=[path("iniciar/<str:numero>/",views.pay,name="iniciar"),path("webhook/mercadopago/",views.webhook_mp,name="webhook_mp"),path("webhook/openpay/",views.webhook_openpay,name="webhook_openpay")]
