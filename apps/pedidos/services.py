from decimal import Decimal
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from apps.catalogo.models import Producto
from apps.cuentas.models import Direccion
from apps.carrito.services import summarize,items
from apps.core.models import Auditoria
from .models import Pedido,PedidoItem,MovimientoInventario,HistorialPedido

def fingerprint(cart):
    return {"items":[[line["producto"].pk,line["cantidad"],str(line["producto"].precio_catalogo),str(line["producto"].precio_academico)] for line in cart["items"]],"academic":str(cart["academico"]),"shipping":str(cart["envio"])}
def make_quote(user,cart):
    return signing.dumps({"user":user.pk,**fingerprint(cart)},salt="carranco.checkout")
@transaction.atomic
def create_order(user,session,address_id,provider,key,quote):
    get_user_model().objects.select_for_update().get(pk=user.pk)
    previous=Pedido.objects.filter(usuario=user,clave_idempotencia=key).first()
    if previous: return previous
    address=Direccion.objects.filter(pk=address_id,usuario=user).first()
    if address is None: raise ValidationError("Selecciona una dirección de tu cuenta.")
    if provider not in {"mercadopago","openpay"}: raise ValidationError("Método de pago no válido.")
    raw=items(session)
    products=list(Producto.objects.select_for_update().filter(pk__in=raw).order_by("pk"))
    cart=summarize(session)
    if not cart["valido"]: raise ValidationError("Revisa tu carrito: algún producto está agotado, inactivo o supera el stock.")
    try: quoted=signing.loads(quote,salt="carranco.checkout",max_age=900)
    except signing.BadSignature: raise ValidationError("El resumen venció. Actualiza el checkout y acepta el importe actual.")
    if quoted!={"user":user.pk,**fingerprint(cart)}: raise ValidationError("Cambió tu selección o su precio. Revisa y acepta el nuevo resumen.")
    amount=cart["academico"].quantize(Decimal("0.01"))
    if amount<=0 or amount>settings.ACADEMIC_MAX_CHARGE: raise ValidationError("El importe a pagar supera el límite permitido. Reduce la selección.")
    snapshot={field:getattr(address,field) for field in ["calle","numero_exterior","numero_interior","colonia","codigo_postal","ciudad","estado","referencias"]}
    order=Pedido.objects.create(usuario=user,direccion=address,direccion_snapshot=snapshot,clave_idempotencia=key,subtotal_catalogo=cart["subtotal"],envio=cart["envio"],total_catalogo=cart["total"],total_academico=amount,metodo_pago=provider,reserva_expira_at=timezone.now()+timedelta(minutes=settings.RESERVATION_MINUTES),aviso_academico_aceptado_at=timezone.now())
    for product in products:
        qty=raw[str(product.pk)]
        if not product.activo or product.stock_disponible<qty: raise ValidationError("Las existencias cambiaron. Revisa tu selección.")
        product.stock_reservado+=qty;product.save(update_fields=["stock_reservado","updated_at"])
        PedidoItem.objects.create(pedido=order,producto=product,sku=product.sku,nombre_producto=product.nombre,presentacion=product.presentacion,precio_unitario=product.precio_catalogo,precio_academico_unitario=product.precio_academico,cantidad=qty,subtotal=product.precio_catalogo*qty)
    HistorialPedido.objects.create(pedido=order,estado_anterior="",estado_nuevo="pendiente_pago",usuario=user,comentario="Pedido creado; total a pagar aceptado.")
    return order

def release_locked(order,comment,user=None):
    if order.inventario_descontado_at: raise ValidationError("Un pedido pagado requiere revisión de pago antes de cancelar; no hay reembolsos automáticos.")
    if order.reserva_activa:
        quantities={line.producto_id:line.cantidad for line in order.items.all()}
        for product in Producto.objects.select_for_update().filter(pk__in=quantities).order_by("pk"):
            if product.stock_reservado<quantities[product.pk]: raise ValidationError("La reserva requiere revisión administrativa.")
            product.stock_reservado-=quantities[product.pk];product.save(update_fields=["stock_reservado","updated_at"])
    before=order.estado;order.reserva_activa=False;order.estado="cancelado";order.save()
    HistorialPedido.objects.create(pedido=order,estado_anterior=before,estado_nuevo="cancelado",comentario=comment,usuario=user)
@transaction.atomic
def cancel_pending(order_id,user):
    order=Pedido.objects.select_for_update().get(pk=order_id,usuario=user)
    if order.estado=="cancelado": return
    if order.estado!="pendiente_pago": raise ValidationError("Solo puedes cancelar un pedido pendiente de pago.")
    release_locked(order,"Cancelado por el cliente sin pago confirmado.",user)
@transaction.atomic
def transition(order_id,new_state,user,comment):
    order=Pedido.objects.select_for_update().get(pk=order_id)
    allowed={"pagado":"preparando","preparando":"en_camino","en_camino":"entregado"}
    if new_state=="cancelado" and order.estado=="pendiente_pago":
        release_locked(order,comment,user)
    elif allowed.get(order.estado)==new_state and order.estado_pago=="aprobado":
        previous=order.estado;order.estado=new_state;order.save(update_fields=["estado","updated_at"])
        HistorialPedido.objects.create(pedido=order,estado_anterior=previous,estado_nuevo=new_state,usuario=user,comentario=comment)
    else: raise ValidationError("La transición solicitada no está permitida.")
    Auditoria.objects.create(usuario=user,evento="estado_pedido",objeto=order.numero)
@transaction.atomic
def adjust_stock(product_id,delta,user,reason):
    product=Producto.objects.select_for_update().get(pk=product_id)
    if type(delta) is not int or delta==0 or abs(delta)>10000: raise ValidationError("El ajuste debe ser un entero distinto de cero entre -10000 y 10000.")
    before=product.stock;after=before+delta
    if after<product.stock_reservado: raise ValidationError("El ajuste no puede dejar el stock por debajo de las reservas.")
    product.stock=after;product.save(update_fields=["stock","updated_at"])
    MovimientoInventario.objects.create(producto=product,tipo="ajuste",cantidad=delta,stock_anterior=before,stock_nuevo=after,usuario_admin=user,motivo=reason)
    Auditoria.objects.create(usuario=user,evento="ajuste_inventario",objeto=str(product.pk))
