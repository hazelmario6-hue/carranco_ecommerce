from django.contrib import messages
from django.contrib.auth import login,get_user_model
from django.contrib.auth.views import LoginView,LogoutView
from django.contrib.auth.decorators import login_required
from django.db import transaction,IntegrityError
from django.shortcuts import render,redirect,get_object_or_404
from django.views.decorators.http import require_POST
from .forms import RegistroForm,AccesoForm,PerfilForm,DireccionForm
from .models import PerfilCliente,Direccion
from apps.core.models import Auditoria
class Acceso(LoginView):
    template_name="cuentas/login.html"
    authentication_form=AccesoForm
    def form_valid(self,form):
        response=super().form_valid(form)
        Auditoria.objects.create(usuario=self.request.user,evento="login",objeto="cuenta")
        return response
class Salir(LogoutView):
    def post(self,request,*args,**kwargs):
        cart=request.session.get("carranco_cart",{})
        response=super().post(request,*args,**kwargs)
        request.session["carranco_cart"]=cart
        return response

def registro(request):
    if request.user.is_authenticated: return redirect("cuentas:perfil")
    form=RegistroForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        try: user=form.save()
        except IntegrityError:
            form.add_error("email","Este correo ya tiene una cuenta.")
        else:
            login(request,user);messages.success(request,"Tu cuenta está lista.")
            return redirect("cuentas:perfil")
    return render(request,"cuentas/registro.html",{"form":form})
@login_required
def perfil(request):
    profile,_=PerfilCliente.objects.get_or_create(usuario=request.user)
    form=PerfilForm(request.POST or None,instance=request.user,initial={"telefono":profile.telefono})
    if request.method=="POST" and form.is_valid():
        with transaction.atomic():
            form.save();profile.telefono=form.cleaned_data["telefono"];profile.save()
        messages.success(request,"Perfil actualizado.");return redirect("cuentas:perfil")
    return render(request,"cuentas/perfil.html",{"form":form})
@login_required
def direcciones(request,pk=None):
    address=get_object_or_404(Direccion,pk=pk,usuario=request.user) if pk else None
    form=DireccionForm(request.POST or None,instance=address)
    if request.method=="POST" and form.is_valid():
        with transaction.atomic():
            get_user_model().objects.select_for_update().get(pk=request.user.pk)
            instance=form.save(commit=False);instance.usuario=request.user
            if not request.user.direcciones.exists(): instance.predeterminada=True
            if instance.predeterminada: request.user.direcciones.update(predeterminada=False)
            instance.save()
        messages.success(request,"Dirección guardada.");return redirect("cuentas:direcciones")
    return render(request,"cuentas/direcciones.html",{"form":form,"direcciones":request.user.direcciones.all(),"editando":bool(pk)})
@login_required
@require_POST
def borrar_direccion(request,pk):
    from django.db.models.deletion import ProtectedError
    address=get_object_or_404(Direccion,pk=pk,usuario=request.user)
    try: address.delete()
    except ProtectedError: messages.error(request,"Esta dirección se conserva porque tiene pedidos asociados.")
    else: messages.success(request,"Dirección eliminada.")
    return redirect("cuentas:direcciones")
