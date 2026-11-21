from django.shortcuts import render,redirect
from django.contrib import messages
from apps.catalogo.models import Producto
from .forms import ContactoForm
from .models import Promocion

def index(request):
    return render(request,"core/app_inicio.html" if getattr(request,"app_mode",False) else "core/index.html",{"destacados":Producto.objects.filter(activo=True,destacado=True).select_related("categoria"),"promociones":Promocion.objects.vigentes(),"nav_active":"inicio"})
def nosotros(request):
    return render(request,"core/nosotros.html",{"nav_active":"nosotros"})
def contacto(request):
    form=ContactoForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        form.save();messages.success(request,"Tu mensaje quedó registrado para el equipo de atención.");return redirect("core:contacto")
    return render(request,"core/contacto.html",{"form":form,"nav_active":"contacto"})
def ayuda(request):
    return render(request,"core/ayuda.html")

def acerca_app(request):
    return render(request, "core/acerca_app.html")
