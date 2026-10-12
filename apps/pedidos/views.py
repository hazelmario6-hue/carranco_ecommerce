import uuid
from django.contrib.auth.decorators import login_required
from django.shortcuts import render,redirect,get_object_or_404
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST
from .models import Pedido
from .forms import CheckoutForm
from .services import create_order,make_quote,cancel_pending
from apps.carrito.services import summarize,KEY
from apps.pagos.services.gateway import configured
@login_required
def checkout(request):
    cart=summarize(request.session)
    if not cart["items"]:
        messages.info(request,"Agrega productos antes de continuar.");return redirect("carrito:detalle")
    initial={"clave":request.session.setdefault("checkout_key",str(uuid.uuid4())),"resumen":make_quote(request.user,cart)}
    form=CheckoutForm(request.POST or None,user=request.user,openpay=configured("openpay"),initial=initial)
    if request.method=="POST" and form.is_valid():
        try: order=create_order(request.user,request.session,form.cleaned_data["direccion"].pk,form.cleaned_data["proveedor"],form.cleaned_data["clave"],form.cleaned_data["resumen"])
        except ValidationError as error: form.add_error(None,error)
        else:
            request.session[KEY]={};request.session.pop("checkout_key",None)
            messages.success(request,"Pedido creado. El pago se confirma únicamente al verificar la pasarela.")
            return redirect("pedidos:detalle",numero=order.numero)
    return render(request,"pedidos/checkout.html",{"form":form,"cart":cart,"mp_enabled":configured("mercadopago"),"openpay_enabled":configured("openpay")})
@login_required
def history(request):
    return render(request,"pedidos/mis_pedidos.html",{"pedidos":request.user.pedidos.prefetch_related("items")})
def owned(request,numero):
    try: pk=int(numero.removeprefix("CARR-"))
    except ValueError: pk=0
    return get_object_or_404(Pedido.objects.select_related("usuario").prefetch_related("items","historial"),pk=pk,usuario=request.user)
@login_required
def detail(request,numero):
    order=owned(request,numero)
    return render(request,"pedidos/pedido_detalle.html",{"pedido":order,"pago_habilitado":configured(order.metodo_pago)})
@login_required
def confirmation(request,numero):
    order=owned(request,numero)
    return render(request,"pedidos/confirmacion.html",{"pedido":order})
@login_required
@require_POST
def cancel(request,numero):
    order=owned(request,numero)
    try: cancel_pending(order.pk,request.user)
    except ValidationError as error: messages.error(request," ".join(error.messages))
    else: messages.success(request,"Pedido pendiente cancelado; reserva liberada.")
    return redirect("pedidos:detalle",numero=order.numero)
