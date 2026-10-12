from django.conf import settings
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from . import mercadopago,openpay
from apps.pedidos.models import Pedido
from apps.pagos.models import IntentoPago

def configured(provider):
    if provider=="mercadopago": return bool(settings.MP_ACCESS_TOKEN and settings.MP_WEBHOOK_SECRET and settings.APP_URL.startswith("https://"))
    if provider=="openpay": return bool(settings.OPENPAY_MERCHANT_ID and settings.OPENPAY_PRIVATE_KEY and settings.OPENPAY_WEBHOOK_USER and settings.OPENPAY_WEBHOOK_PASSWORD and settings.OPENPAY_PRODUCTION==settings.PAYMENTS_LIVE and settings.APP_URL.startswith("https://"))
    return False
@transaction.atomic
def start(order_id,user,ip=""):
    order=Pedido.objects.select_for_update().select_related("usuario").get(pk=order_id,usuario=user)
    if not configured(order.metodo_pago): raise ValidationError("El pago no está disponible. Tu pedido permanece pendiente.")
    if order.estado!="pendiente_pago" or order.inventario_descontado_at or not order.reserva_activa or order.reserva_expira_at<=timezone.now(): raise ValidationError("Este pedido ya no admite iniciar un pago. Revisa su estado.")
    attempt,_=IntentoPago.objects.get_or_create(pedido=order,defaults={"proveedor":order.metodo_pago})
    if attempt.url: return attempt.url
    module=mercadopago if order.metodo_pago=="mercadopago" else openpay
    identifier,url=module.create(order,ip)
    attempt.identificador=identifier;attempt.url=url;attempt.save()
    return url
