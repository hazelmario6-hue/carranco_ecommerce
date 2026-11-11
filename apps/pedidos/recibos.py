from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse
from apps.core.correos import queue_email

def receipt_context(order,payment):
    return {"logo_url":settings.APP_URL+"/static/img/carranco-logo.png","pedido":order,"pago":payment,"items":list(order.items.all()),
        "url":settings.APP_URL+reverse("pedidos:recibo",kwargs={"numero":order.numero}),
        "es_prueba":payment.en_vivo is False}

def queue_receipt(order,payment):
    if not order.correo_cliente: return # Legacy orders have no verified recipient snapshot.
    context=receipt_context(order,payment)
    queue_email(f"recibo:{order.pk}",order.correo_cliente,"Recibo "+order.numero+" · Carranco",
        render_to_string("emails/recibo.txt",context),render_to_string("emails/recibo.html",context))
