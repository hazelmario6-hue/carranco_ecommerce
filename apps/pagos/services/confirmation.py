import uuid
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from apps.pedidos.models import Pedido,MovimientoInventario,HistorialPedido
from apps.catalogo.models import Producto
from apps.pagos.models import Pago
from apps.core.models import Auditoria
@transaction.atomic
def confirm(provider,data):
    try: reference=uuid.UUID(str(data["reference"]))
    except (ValueError,TypeError,KeyError): raise ValidationError("Referencia de pago no válida.")
    order=Pedido.objects.select_for_update().filter(referencia=reference).first()
    if order is None or order.metodo_pago!=provider: raise ValidationError("El pago no corresponde a un pedido de esta pasarela.")
    amount=data["amount"]
    if not amount.is_finite() or amount!=order.total_academico or data["currency"]!="MXN": raise ValidationError("El monto o la moneda no coinciden con el pedido.")
    payment,created=Pago.objects.get_or_create(proveedor=provider,payment_id_externo=data["id"],defaults={"pedido":order,"monto":amount,"moneda":"MXN","estado":data["status"],"metodo_pago":data["method"]})
    if payment.pedido_id!=order.pk: raise ValidationError("El identificador externo ya pertenece a otro pedido.")
    if order.inventario_descontado_at:
        if created and data["status"]=="aprobado":
            payment.estado="revision";payment.save(update_fields=["estado","updated_at"])
            Auditoria.objects.create(evento="posible_pago_duplicado",objeto=order.numero)
        elif data["status"] in {"reembolsado","revision"}:
            payment.estado=data["status"];payment.save()
            order.estado_pago=data["status"];order.save(update_fields=["estado_pago","updated_at"])
            Auditoria.objects.create(evento="revision_pago",objeto=order.numero)
        return order
    if payment.estado=="aprobado" and data["status"]!="aprobado": return order
    payment.estado=data["status"];payment.save(update_fields=["estado","updated_at"])
    if data["status"]!="aprobado":
        if order.estado_pago not in {"aprobado","revision"}:
            order.estado_pago=data["status"];order.save(update_fields=["estado_pago","updated_at"])
        return order
    if not order.reserva_activa or order.estado=="cancelado":
        order.estado_pago="revision";order.total_cobrado=amount;order.save(update_fields=["estado_pago","total_cobrado","updated_at"])
        payment.estado="revision";payment.save()
        Auditoria.objects.create(evento="pago_tardio_revision",objeto=order.numero)
        return order
    quantities={line.producto_id:line.cantidad for line in order.items.all()}
    products=list(Producto.objects.select_for_update().filter(pk__in=quantities).order_by("pk"))
    if any(p.stock<quantities[p.pk] or p.stock_reservado<quantities[p.pk] for p in products): raise ValidationError("El inventario requiere revisión antes de confirmar.")
    for product in products:
        qty=quantities[product.pk];before=product.stock
        product.stock-=qty;product.stock_reservado-=qty;product.save(update_fields=["stock","stock_reservado","updated_at"])
        MovimientoInventario.objects.create(producto=product,tipo="venta",cantidad=-qty,stock_anterior=before,stock_nuevo=product.stock,pedido=order,motivo="Pago verificado por "+provider)
    previous=order.estado;order.estado="pagado";order.estado_pago="aprobado";order.total_cobrado=amount;order.reserva_activa=False;order.inventario_descontado_at=timezone.now();order.save()
    HistorialPedido.objects.create(pedido=order,estado_anterior=previous,estado_nuevo="pagado",comentario="Confirmación verificada por "+provider)
    Auditoria.objects.create(evento="pago_confirmado",objeto=order.numero)
    return order
