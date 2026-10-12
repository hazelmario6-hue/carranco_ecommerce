import csv
from functools import wraps
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied,ValidationError
from django.db.models import Sum,Count,F,Q
from django.db.models.functions import Cast
from django.db.models import DateField
from django.db import transaction
from django.shortcuts import render,redirect,get_object_or_404
from django.http import HttpResponse
from django.urls import reverse
from django.contrib import messages
from django.conf import settings
from apps.catalogo.models import Producto
from apps.pedidos.models import Pedido,PedidoItem
from apps.pedidos.services import adjust_stock,transition
from apps.core.models import Auditoria
from apps.pagos.models import VerificacionOpenpay
from .forms import ProductoForm,AjusteForm,EstadoForm

def staff_required(permission=None):
    def decorate(view):
        @wraps(view)
        def wrapper(request,*args,**kwargs):
            if not request.user.is_authenticated: return redirect_to_login(request.get_full_path(),reverse("cuentas:login"))
            if not request.user.is_active or not request.user.is_staff or permission and not request.user.has_perm(permission): raise PermissionDenied
            return view(request,*args,**kwargs)
        return wrapper
    return decorate
@staff_required()
def dashboard(request):
    orders=Pedido.objects.all();products=Producto.objects.filter(activo=True)
    stats={"Pedidos totales":orders.count(),"Pendientes":orders.filter(estado="pendiente_pago").count(),"Pagados":orders.filter(estado_pago="aprobado").count(),"Entregados":orders.filter(estado="entregado").count(),"Clientes registrados":get_user_model().objects.filter(is_staff=False).count(),"Productos activos":products.count(),"Stock bajo":products.filter(stock__gt=F("stock_reservado"),stock__lte=F("stock_reservado")+settings.STOCK_LOW_THRESHOLD).count(),"Agotados":products.filter(stock=F("stock_reservado")).count(),"Ventas":orders.filter(estado_pago="aprobado").aggregate(total=Sum("total_cobrado"))["total"] or Decimal("0.00")}
    return render(request,"dashboard/dashboard.html",{"stats":stats,"ultimos":orders.select_related("usuario")[:6],"stock_bajo":products.annotate(disponible=F("stock")-F("stock_reservado")).filter(disponible__lte=settings.STOCK_LOW_THRESHOLD),"verificacion_openpay":VerificacionOpenpay.objects.order_by("-id").first() if request.user.is_superuser else None})
@staff_required("catalogo.view_producto")
def products(request):
    query=request.GET.get("q","")[:150]
    data=Producto.objects.select_related("categoria").filter(Q(nombre__icontains=query)|Q(sku__icontains=query))
    return render(request,"dashboard/productos.html",{"productos":data,"query":query})
@staff_required("catalogo.change_producto")
def product_edit(request,pk=None):
    if pk is None and not request.user.has_perm("catalogo.add_producto"): raise PermissionDenied
    product=get_object_or_404(Producto,pk=pk) if pk else None
    form=ProductoForm(request.POST or None,request.FILES or None,instance=product)
    if request.method=="POST" and form.is_valid():
        with transaction.atomic():
            saved=form.save();Auditoria.objects.create(usuario=request.user,evento="editar_producto" if pk else "crear_producto",objeto=str(saved.pk))
        messages.success(request,"Producto guardado. Ajusta sus existencias desde Inventario.");return redirect("dashboard:productos")
    return render(request,"dashboard/producto_form.html",{"form":form,"producto":product})
@staff_required("catalogo.view_producto")
def inventory(request):
    query=request.GET.get("q","")[:150]
    return render(request,"dashboard/inventario.html",{"productos":Producto.objects.filter(Q(nombre__icontains=query)|Q(sku__icontains=query)),"query":query})
@staff_required("catalogo.change_producto")
def stock_adjust(request,pk):
    product=get_object_or_404(Producto,pk=pk)
    form=AjusteForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        try: adjust_stock(pk,form.cleaned_data["cantidad"],request.user,form.cleaned_data["motivo"])
        except ValidationError as error: form.add_error(None,error)
        else: messages.success(request,"Ajuste registrado con su movimiento de inventario.");return redirect("dashboard:inventario")
    return render(request,"dashboard/ajuste.html",{"form":form,"producto":product})
@staff_required("pedidos.view_pedido")
def orders(request):
    query=request.GET.get("q","")[:150];state=request.GET.get("estado","")
    data=Pedido.objects.select_related("usuario").filter(usuario__email__icontains=query) if query else Pedido.objects.select_related("usuario")
    if query.startswith("CARR-") and query[5:].isdigit(): data=Pedido.objects.filter(pk=int(query[5:])).select_related("usuario")
    if state in dict(Pedido.ESTADOS): data=data.filter(estado=state)
    return render(request,"dashboard/pedidos.html",{"pedidos":data,"query":query,"estados":Pedido.ESTADOS,"estado_actual":state})
@staff_required("pedidos.view_pedido")
def order_detail(request,pk):
    order=get_object_or_404(Pedido.objects.select_related("usuario").prefetch_related("items","historial","pagos"),pk=pk)
    form=EstadoForm(request.POST or None)
    if request.method=="POST":
        if not request.user.has_perm("pedidos.change_pedido"): raise PermissionDenied
        if form.is_valid():
            try: transition(pk,form.cleaned_data["estado"],request.user,form.cleaned_data["comentario"])
            except ValidationError as error: form.add_error(None,error)
            else: messages.success(request,"Estado actualizado con historial.");return redirect("dashboard:pedido_detalle",pk=pk)
    return render(request,"dashboard/pedido_detalle.html",{"pedido":order,"form":form})
@staff_required("cuentas.view_perfilcliente")
def customers(request):
    query=request.GET.get("q","")[:150]
    data=get_user_model().objects.filter(is_staff=False).filter(Q(first_name__icontains=query)|Q(last_name__icontains=query)|Q(email__icontains=query)).select_related("perfil_cliente").annotate(num_pedidos=Count("pedidos"))
    return render(request,"dashboard/clientes.html",{"clientes":data,"query":query})
@staff_required("cuentas.view_perfilcliente")
def customer(request,pk):
    user=get_object_or_404(get_user_model(),pk=pk,is_staff=False)
    return render(request,"dashboard/cliente_detalle.html",{"cliente":user,"pedidos":user.pedidos.all()})
@staff_required("pedidos.view_pedido")
def reports(request):
    paid=Pedido.objects.filter(estado_pago="aprobado")
    top=PedidoItem.objects.filter(pedido__estado_pago="aprobado").values("nombre_producto").annotate(unidades=Sum("cantidad")).order_by("-unidades")[:10]
    dates=paid.annotate(dia=Cast("created_at",DateField())).values("dia").annotate(pedidos=Count("id"),cobrado=Sum("total_cobrado")).order_by("-dia")[:30]
    gateways=paid.values("metodo_pago").annotate(pedidos=Count("id"),cobrado=Sum("total_cobrado"))
    clients=get_user_model().objects.filter(is_staff=False).annotate(num_pedidos=Count("pedidos")).order_by("-num_pedidos")[:10]
    return render(request,"dashboard/reportes.html",{"por_fecha":dates,"mas_vendidos":top,"por_pasarela":gateways,"clientes":clients,"por_estado":Pedido.objects.values("estado").annotate(total=Count("id")),"ventas":paid.aggregate(total=Sum("total_cobrado"))["total"] or 0})
def csv_safe(value):
    value=str(value)
    return "'"+value if value.lstrip().startswith(("=","+","-","@")) else value
@staff_required("pedidos.view_pedido")
def export(request):
    response=HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"]='attachment; filename="pedidos-carranco.csv"'
    response["Cache-Control"]="no-store"
    response.write("\ufeff")
    writer=csv.writer(response)
    writer.writerow(["Número","Cliente","Fecha","Estado","Total cobrado MXN","Pasarela"])
    for order in Pedido.objects.select_related("usuario").iterator(chunk_size=200):
        writer.writerow([csv_safe(value) for value in [order.numero,order.usuario.get_full_name(),order.created_at.isoformat(),order.estado,format(order.total_cobrado,".2f"),order.metodo_pago]])
    return response
