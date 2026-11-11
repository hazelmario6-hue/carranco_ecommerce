from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.views import LoginView,LogoutView
from django.contrib.auth.decorators import login_required
from django.db import transaction,IntegrityError
from django.shortcuts import render,redirect,get_object_or_404
from django.views.decorators.http import require_POST,require_http_methods
from .forms import RegistroForm,AccesoForm,PerfilForm,DireccionForm
from .models import PerfilCliente,Direccion,VerificacionCorreo
from .verificacion import link_valid,consume_verification,is_verified
from apps.core.models import Auditoria
from .pin import issue_pin, verify_pin
from django import forms
from django.utils import timezone
from django.conf import settings
class Acceso(LoginView):
    template_name="cuentas/login.html"
    authentication_form=AccesoForm
    def form_valid(self,form):
        if getattr(form,"pending_verification",False):
            self.request.session.cycle_key()
            self.request.session["registro_pendiente"]=form.get_user().pk
            issue_pin(form.get_user())
            return redirect("cuentas:registro")
        response=super().form_valid(form)
        Auditoria.objects.create(usuario=self.request.user,evento="login",objeto="cuenta")
        return response
class Salir(LogoutView):
    def post(self,request,*args,**kwargs):
        cart=request.session.get("carranco_cart",{})
        response=super().post(request,*args,**kwargs)
        request.session["carranco_cart"]=cart
        return response

@require_http_methods(["GET","POST"])
def registro(request):
    if request.user.is_authenticated and is_verified(request.user): return redirect("cuentas:perfil")
    pending=request.user if request.user.is_authenticated else get_user_model().objects.filter(
        pk=request.session.get("registro_pendiente"),is_active=False,
        verificacion_correo__activar_al_verificar=True,verificacion_correo__verificado_at__isnull=True).first()
    form=RegistroForm(request.POST or None) if not pending else RegistroForm()
    error=""
    if pending:
        if request.method=="POST":
            action=request.POST.get("action", "verify")
            if action=="verify":
                ok,error=verify_pin(pending,request.POST.get("codigo", "").strip())
                if ok:
                    pending.refresh_from_db()
                    login(request,pending,backend="django.contrib.auth.backends.ModelBackend")
                    request.session.pop("registro_pendiente",None)
                    messages.success(request,"¡Bienvenido! Tu correo quedó verificado.")
                    return redirect("cuentas:perfil")
            elif action=="resend":
                if not issue_pin(pending): error="Espera 60 segundos entre envíos. Puedes solicitar hasta cinco códigos por hora."
                else: return redirect("cuentas:registro")
            elif action=="change" and not request.user.is_authenticated:
                try:
                    email=forms.EmailField(max_length=150).clean(request.POST.get("email", "")).lower()
                    with transaction.atomic():
                        locked=get_user_model().objects.select_for_update().get(pk=pending.pk)
                        if locked.is_active: raise forms.ValidationError("Esta cuenta ya está activa.")
                        if get_user_model().objects.exclude(pk=locked.pk).filter(email__iexact=email).exists():
                            raise forms.ValidationError("Este correo ya tiene una cuenta.")
                        if get_user_model().objects.exclude(pk=locked.pk).filter(username__iexact=email).exists():
                            raise forms.ValidationError("Este correo ya tiene una cuenta.")
                        locked.email=email;locked.save(update_fields=["email"])
                        VerificacionCorreo.objects.filter(usuario=locked).update(pin_hash="",token_hash="",pin_envio_ok=False)
                        # Keep the cooldown and hourly budget even when the email changes.
                        issue_pin(locked)
                    return redirect("cuentas:registro")
                except forms.ValidationError as exc: error=" ".join(exc.messages)
        record=VerificacionCorreo.objects.filter(usuario=pending).first()
        wait=max(0,int(settings.EMAIL_VERIFY_RESEND_SECONDS-(timezone.now()-record.ultimo_envio).total_seconds())+1) if record and record.ultimo_envio else 0
        local,_,domain=pending.email.partition("@")
        context={"pin_step":True,"masked_email":local[:2]+"•••@"+domain,"resend_wait":wait,
                 "pin_error":error,"pin_sent":bool(record and record.pin_envio_ok),
                 "can_change_email":not request.user.is_authenticated,"form":form}
    else:
        if request.method=="POST" and form.is_valid():
            try:
                with transaction.atomic():
                    user=form.save()
                    issue_pin(user)
            except IntegrityError:
                form.add_error(None,"El usuario o correo ya están registrados.")
            else:
                request.session.cycle_key()
                request.session["registro_pendiente"]=user.pk
                return redirect("cuentas:registro")
        context={"form":form}
    response=render(request,"cuentas/registro.html",context)
    response["Cache-Control"]="private, no-store"
    return response

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
    # Keep old bookmarks and checkout redirects; all new verification lives in registration.
    if request.user.is_authenticated and request.method=="POST": issue_pin(request.user)
    return redirect("cuentas:registro" if request.user.is_authenticated or request.session.get("registro_pendiente") else "cuentas:login")


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
