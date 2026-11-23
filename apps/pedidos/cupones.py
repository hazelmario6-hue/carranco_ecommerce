from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone
from .models import Cupon, UsoCupon

SESSION_KEY="checkout_coupon"

def normalize(code):
    return (code or "").strip().upper()[:32]

def price_with_coupon(user,cart,code="",lock=False):
    """Return the payable total. A locked call serializes global coupon usage."""
    code=normalize(code)
    result={"cupon":None,"codigo":"","descuento":Decimal("0.00"),"total":cart["total"]}
    if not code:return result
    query=Cupon.objects.select_for_update() if lock else Cupon.objects.all()
    coupon=query.filter(codigo=code).first()
    if coupon is None:raise ValidationError("El código promocional no existe.")
    now=timezone.now()
    if not coupon.activo:raise ValidationError("El código promocional está desactivado.")
    if coupon.inicio and coupon.inicio>now:raise ValidationError("El código promocional todavía no está vigente.")
    if coupon.fin and coupon.fin<=now:raise ValidationError("El código promocional venció.")
    if cart["subtotal"]<coupon.compra_minima:
        raise ValidationError(f"Este código requiere una compra mínima de ${coupon.compra_minima:.2f} MXN en productos.")
    # An expired unpaid reservation must not block the coupon while the cleanup job catches up.
    uses=UsoCupon.objects.filter(cupon=coupon).filter(
        Q(pedido__estado_pago__in=["aprobado","revision"])|
        Q(pedido__reserva_activa=True,pedido__reserva_expira_at__gt=now)
    )
    if coupon.max_usos and uses.count()>=coupon.max_usos:raise ValidationError("El código promocional agotó sus usos disponibles.")
    if uses.filter(usuario=user).count()>=coupon.max_usos_cliente:raise ValidationError("Ya utilizaste este código el máximo de veces permitido.")
    discount=coupon.descuento_para(cart["subtotal"])
    total=cart["subtotal"]+cart["envio"]-discount
    if discount<=0 or total<=0:raise ValidationError("Este código no produce un total válido para el pago.")
    return {"cupon":coupon,"codigo":coupon.codigo,"descuento":discount,"total":total}
