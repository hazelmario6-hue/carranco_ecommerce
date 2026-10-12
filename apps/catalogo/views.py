from django.db.models import Q
from django.shortcuts import render,get_object_or_404,redirect
from .models import Producto,Categoria

def catalog(request):
    products=Producto.objects.filter(activo=True,en_catalogo=True).select_related("categoria")
    query=request.GET.get("q","")[:150].strip()
    category=request.GET.get("categoria","")
    visible=products
    if query: visible=visible.filter(Q(nombre__icontains=query)|Q(descripcion__icontains=query)|Q(categoria__nombre__icontains=query))
    if category and category!="todos": visible=visible.filter(categoria__slug=category)
    return render(request,"catalogo/productos.html",{"productos":products,"coincidencias":set(visible.values_list("pk",flat=True)),"categorias":Categoria.objects.exclude(slug="ofertas"),"query":query,"categoria_actual":category or "todos","nav_active":"productos"})

def detail(request,slug):
    product=get_object_or_404(Producto.objects.select_related("categoria"),slug=slug,activo=True)
    others=Producto.objects.filter(activo=True,en_catalogo=True).exclude(pk=product.pk).select_related("categoria")
    related=list(others.filter(categoria=product.categoria)[:4])
    if len(related)<4: related+=list(others.exclude(categoria=product.categoria)[:4-len(related)])
    return render(request,"catalogo/producto_detalle.html",{"producto":product,"relacionados":related,"max_quantity":max(1,min(20,product.stock_disponible)),"nav_active":"productos"})

def legacy_detail(request):
    product=get_object_or_404(Producto,legacy_id=request.GET.get("id"),activo=True)
    return redirect(product.get_absolute_url())
