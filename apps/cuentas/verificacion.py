import hashlib
import secrets
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode,urlsafe_base64_decode
from apps.core.correos import queue_email
from apps.core.models import CorreoPendiente
from .models import VerificacionCorreo

def is_verified(user):
    return bool(user.is_authenticated and user.is_active and VerificacionCorreo.objects.filter(usuario=user,
        email__iexact=user.email,verificado_at__isnull=False).exists())

@transaction.atomic
def request_verification(user):
    user=get_user_model().objects.select_for_update().get(pk=user.pk)
    record,_=VerificacionCorreo.objects.select_for_update().get_or_create(usuario=user,defaults={"email":user.email})
    if not user.email or (not user.is_active and not record.activar_al_verificar): return False
    if record.verificado_at and record.email.lower()==user.email.lower(): return False
    now=timezone.now()
    if record.ultimo_envio and (now-record.ultimo_envio).total_seconds()<settings.EMAIL_VERIFY_RESEND_SECONDS: return False
    if record.ventana_envio and now-record.ventana_envio<timedelta(hours=1):
        if record.envios_en_ventana>=5: return False
    else:
        record.ventana_envio=now;record.envios_en_ventana=0
    token=secrets.token_urlsafe(32)
    record.email=user.email.lower();record.token_hash=hashlib.sha256(token.encode()).hexdigest()
    record.verificado_at=None;record.vence_at=now+timedelta(seconds=settings.EMAIL_VERIFY_TTL_SECONDS)
    record.ultimo_envio=now;record.envios_en_ventana+=1;record.save()
    # Discard queued older links; a completed mail may still contain an expired link.
    CorreoPendiente.objects.filter(clave__startswith=f"verificar:{user.pk}:",estado="pendiente").update(estado="cancelado",texto="",html="")
    url=settings.APP_URL+reverse("cuentas:verificar_correo",kwargs={"uid":urlsafe_base64_encode(force_bytes(user.pk)),"token":token})
    context={"nombre":user.first_name,"url":url,"horas":settings.EMAIL_VERIFY_TTL_SECONDS//3600}
    queue_email(f"verificar:{user.pk}:{record.token_hash}",user.email,"Verifica tu correo · Carranco",
        render_to_string("emails/verificacion.txt",context),render_to_string("emails/verificacion.html",context),record.vence_at)
    return True

def _user_id(uid):
    try:
        pk=int(urlsafe_base64_decode(uid).decode())
        return pk if 0<pk<9223372036854775808 else None
    except (ValueError,UnicodeError,OverflowError): return None

def valid_record(record,token):
    return bool(record and len(token)<=100 and record.token_hash and not record.verificado_at and record.vence_at
        and record.vence_at>timezone.now() and record.email.lower()==record.usuario.email.lower()
        and (record.usuario.is_active or record.activar_al_verificar)
        and constant_time_compare(record.token_hash,hashlib.sha256(token.encode()).hexdigest()))

def link_valid(uid,token):
    record=VerificacionCorreo.objects.select_related("usuario").filter(usuario_id=_user_id(uid)).first()
    return valid_record(record,token)

@transaction.atomic
def consume_verification(uid,token):
    user=get_user_model().objects.select_for_update().filter(pk=_user_id(uid)).first()
    if not user: return False
    record=VerificacionCorreo.objects.select_for_update().filter(usuario=user).first()
    if not valid_record(record,token): return False
    if record.activar_al_verificar:
        user.is_active=True;user.save(update_fields=["is_active"])
    record.activar_al_verificar=False;record.verificado_at=timezone.now();record.token_hash="";record.save()
    return True
