from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.views import LoginView,LogoutView
from django.contrib.auth.decorators import login_required
from django.db import transaction,IntegrityError
from django.shortcuts import render,redirect,get_object_or_404
from django.views.decorators.http import require_POST,require_http_methods
from .forms import RegistroForm,AccesoForm,PerfilForm,DireccionForm,ReenviarCorreoForm
from .models import PerfilCliente,Direccion,VerificacionCorreo
from .verificacion import request_verification,link_valid,consume_verification,is_verified
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
        try:
            with transaction.atomic():
                user=form.save()
                request_verification(user)
        except IntegrityError:
            form.add_error("email","Este correo ya tiene una cuenta.")
        else:
            messages.success(request,"Cuenta creada. Revisa tu correo para activarla. Si el envío tarda, puedes solicitar un nuevo enlace.")
            return redirect("cuentas:reenviar_correo")
    return render(request,"cuentas/registro.html",{"form":form})
@login_required
def perfil(request):
    profile,_=PerfilCliente.objects.get_or_create(usuario=request.user)
    form=PerfilForm(request.POST or None,instance=request.user,initial={"telefono":profile.telefono})
    if request.method=="POST" and form.is_valid():
        with transaction.atomic():
            form.save();profile.telefono=form.cleaned_data["telefono"];profile.save()
        messages.success(request,"Perfil actualizado.");return redirect("cuentas:perfil")
    return render(request,"cuentas/perfil.html",{"form":form,"correo_verificado":is_verified(request.user)})
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


@require_http_methods(["GET","POST"])
def reenviar_correo(request):
    form=ReenviarCorreoForm(request.POST or None,initial={"email":request.user.email if request.user.is_authenticated else ""})
    if request.user.is_authenticated:
        form.fields["email"].disabled=True
    if request.method=="POST" and form.is_valid():
        if request.user.is_authenticated:
            user=request.user # Never let an authenticated form verify somebody else's address.
        else:
            record=VerificacionCorreo.objects.select_related("usuario").filter(
                email__iexact=form.cleaned_data["email"],activar_al_verificar=True,usuario__is_active=False).first()
            user=record.usuario if record else None
        if user: request_verification(user)
        messages.info(request,"Si la cuenta necesita verificación, enviaremos un enlace. Revisa spam y espera al menos un minuto antes de solicitar otro; máximo cinco por hora.")
        return redirect("cuentas:reenviar_correo")
    return render(request,"cuentas/reenviar_correo.html",{"form":form})


@require_http_methods(["GET","POST"])
def verificar_correo(request,uid,token):
    # GET only displays a confirmation; email security scanners must not consume links.
    valid=link_valid(uid,token)
    if request.method=="POST" and valid:
        if consume_verification(uid,token):
            messages.success(request,"Correo verificado. Ya puedes iniciar sesión y continuar tu compra.")
            response=redirect("cuentas:perfil" if request.user.is_authenticated else "cuentas:login")
            response["Referrer-Policy"]="no-referrer"
            return response
        valid=False
    response=render(request,"cuentas/verificar_correo.html",{"enlace_valido":valid},status=200 if valid else 400)
    response["Referrer-Policy"]="no-referrer"
    return response
