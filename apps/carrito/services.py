from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from apps.catalogo.models import Producto
KEY="carranco_cart"
MAX_QUANTITY=20

def items(session):
    raw=session.get(KEY,{})
    if not isinstance(raw,dict):
        return {}
    return {str(k):v for k,v in raw.items() if str(k).isdigit() and type(v) is int and 1<=v<=MAX_QUANTITY}

def summarize(session):
    cart=items(session)
    products=Producto.objects.select_related("categoria").filter(pk__in=cart)
    lines=[]
    subtotal=Decimal("0.00")
    academic=Decimal("0.00")
    for product in products:
        quantity=cart[str(product.pk)]
        line_total=product.precio_catalogo*quantity
        subtotal+=line_total
        academic+=product.precio_academico*quantity
        lines.append({"producto":product,"cantidad":quantity,"subtotal":line_total,"valido":product.activo and product.stock_disponible>=quantity})
    shipping=Decimal("0.00") if subtotal==0 or subtotal>=500 else Decimal("79.00")
    academic=settings.ACADEMIC_CHARGE_AMOUNT if settings.ACADEMIC_CHARGE_AMOUNT is not None and lines else academic
    return {"items":lines,"count":sum(cart.values()),"subtotal":subtotal,"envio":shipping,"total":subtotal+shipping,"academico":academic,"valido":bool(lines) and len(lines)==len(cart) and all(line["valido"] for line in lines)}

def change(session,product_id,quantity,operation="set"):
    if type(quantity) is not int or quantity<0 or quantity>MAX_QUANTITY:
        raise ValidationError("La cantidad debe ser un entero entre 1 y 20; usa 0 para eliminar.")
    if quantity==0 and operation=="set":
        cart=items(session);cart.pop(str(product_id),None);session[KEY]=cart;session.modified=True
        return summarize(session)
    product=Producto.objects.filter(pk=product_id,activo=True).first()
    if product is None:
        raise ValidationError("El producto no está disponible.")
    cart=items(session)
    selected=quantity+cart.get(str(product.pk),0) if operation=="add" else quantity
    if selected>MAX_QUANTITY or selected>product.stock_disponible:
        raise ValidationError(f"Solo puedes seleccionar hasta {min(MAX_QUANTITY,product.stock_disponible)} unidades de {product.nombre}.")
    if selected: cart[str(product.pk)]=selected
    else: cart.pop(str(product.pk),None)
    session[KEY]=cart
    session.modified=True
    return summarize(session)
