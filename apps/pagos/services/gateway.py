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

def start(order_id,user,ip=""):
    from apps.cuentas.verificacion import is_verified
    if settings.EMAIL_REQUIRE_VERIFICATION and not is_verified(user):
        raise ValidationError("Verifica tu correo antes de pagar.")
    error=None
    with transaction.atomic():
        order=Pedido.objects.select_for_update().select_related("usuario").get(pk=order_id,usuario=user)
        if not configured(order.metodo_pago): raise ValidationError("El pago no está disponible. Tu pedido permanece pendiente.")
        if order.total_academico!=order.total_catalogo:
            raise ValidationError("Este pedido conserva un importe anterior. Crea uno nuevo con el precio completo.")
        if order.estado!="pendiente_pago" or order.estado_pago=="revision" or order.inventario_descontado_at or not order.reserva_activa or order.reserva_expira_at<=timezone.now():
            raise ValidationError("Este pedido ya no admite iniciar un pago. Revisa su estado.")
        attempt,_=IntentoPago.objects.get_or_create(pedido=order,defaults={"proveedor":order.metodo_pago,"en_vivo":settings.PAYMENTS_LIVE})
        if attempt.en_vivo is not None and attempt.en_vivo!=settings.PAYMENTS_LIVE:
            raise ValidationError("El intento pertenece a otro entorno de pago. Solicita revisión.")
        if attempt.url: return attempt.url
        if attempt.estado=="revision":
            raise ValidationError("No se pudo confirmar la creación del pago. Consulta su estado o contacta al equipo; no generaremos otro cargo automáticamente.")
        module=mercadopago if order.metodo_pago=="mercadopago" else openpay
        try:
            identifier,url=module.create(order,ip)
        except ValidationError as exc:
            # Commit uncertainty before raising; rolling back would permit blind duplicate POSTs.
            attempt.estado="revision";attempt.en_vivo=settings.PAYMENTS_LIVE;attempt.save()
            error=exc
        else:
            attempt.identificador=identifier;attempt.url=url;attempt.estado="listo";attempt.en_vivo=settings.PAYMENTS_LIVE;attempt.save()
    if error: raise error
    return url

def synchronize(order_id,user):
    from datetime import timedelta
    from .confirmation import confirm
    with transaction.atomic():
        order=Pedido.objects.select_for_update().get(pk=order_id,usuario=user)
        if not configured(order.metodo_pago): raise ValidationError("La pasarela no está configurada.")
        attempt=IntentoPago.objects.select_for_update().filter(pedido=order).first()
        if not attempt: raise ValidationError("Todavía no has iniciado el pago de este pedido.")
        if attempt.en_vivo is not None and attempt.en_vivo!=settings.PAYMENTS_LIVE:
            raise ValidationError("El intento pertenece a otro entorno de pago.")
        now=timezone.now()
        if attempt.ultima_consulta_at and now-attempt.ultima_consulta_at<timedelta(seconds=20):
            raise ValidationError("Espera 20 segundos antes de consultar otra vez.")
        attempt.ultima_consulta_at=now;attempt.save(update_fields=["ultima_consulta_at"])
    module=mercadopago if order.metodo_pago=="mercadopago" else openpay
    results=module.search(order)
    for data in results:
        if str(data.get("reference"))!=str(order.referencia): raise ValidationError("La referencia recibida no coincide.")
        confirm(order.metodo_pago,data)
    order.refresh_from_db()
    return order
