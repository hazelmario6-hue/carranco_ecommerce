"""Single-use email PIN. Only a salted hash is persisted; message exists in memory."""
import logging
import secrets
import uuid
from datetime import timedelta
from types import SimpleNamespace
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password, check_password
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
from apps.core.correos import send_email, MailDeliveryError
from apps.core.models import CorreoPendiente
from .models import VerificacionCorreo
logger=logging.getLogger(__name__)

@transaction.atomic
def issue_pin(user):
    user=get_user_model().objects.select_for_update().get(pk=user.pk)
    record,_=VerificacionCorreo.objects.select_for_update().get_or_create(usuario=user, defaults={"email":user.email})
    now=timezone.now()
    if not user.email or (not user.is_active and not record.activar_al_verificar): return False
    if record.verificado_at and record.email.lower()==user.email.lower(): return False
    if record.ultimo_envio and (now-record.ultimo_envio).total_seconds()<settings.EMAIL_VERIFY_RESEND_SECONDS: return False
    if record.ventana_envio and now-record.ventana_envio<timedelta(hours=1):
        if record.envios_en_ventana>=5: return False
    else:
        record.ventana_envio=now;record.envios_en_ventana=0
    code=f"{secrets.randbelow(1000000):06d}"
    record.pin_hash=make_password(code)
    record.pin_intentos=0;record.pin_envio_ok=False;record.token_hash=""
    record.email=user.email.lower();record.verificado_at=None
    record.vence_at=now+timedelta(seconds=settings.EMAIL_PIN_TTL_SECONDS)
    record.ultimo_envio=now;record.envios_en_ventana+=1;record.save()
    CorreoPendiente.objects.filter(clave__startswith=f"verificar:{user.pk}:",estado="pendiente").update(estado="cancelado",texto="",html="")
    context={"nombre":user.first_name,"codigo":code,"minutos":settings.EMAIL_PIN_TTL_SECONDS//60,"logo_url":settings.APP_URL+"/static/img/carranco-logo.png"}
    msg=SimpleNamespace(remitente=settings.DEFAULT_FROM_EMAIL,responder_a=settings.EMAIL_REPLY_TO,
        destinatario=user.email,asunto="Tu código de verificación · Carranco",clave="pin:"+str(uuid.uuid4()),
        texto=render_to_string("emails/pin.txt",context),html=render_to_string("emails/pin.html",context))
    def deliver():
        try:
            send_email(msg)
        except MailDeliveryError:
            logger.warning("No se pudo enviar el PIN. Se puede solicitar uno nuevo desde el registro.")
        else:
            VerificacionCorreo.objects.filter(pk=record.pk,pin_hash=record.pin_hash).update(pin_envio_ok=True)
    transaction.on_commit(deliver,robust=True)
    return True

@transaction.atomic
def verify_pin(user,code):
    user=get_user_model().objects.select_for_update().get(pk=user.pk)
    record=VerificacionCorreo.objects.select_for_update().filter(usuario=user).first()
    if not record or not record.pin_hash or record.verificado_at: return False,"Solicita un nuevo código."
    if not user.is_active and not record.activar_al_verificar: return False,"La cuenta no está disponible."
    if not record.vence_at or record.vence_at<=timezone.now(): return False,"El código caducó. Solicita uno nuevo."
    if record.pin_intentos>=settings.EMAIL_PIN_MAX_ATTEMPTS: return False,"Alcanzaste los cinco intentos. Solicita otro código cuando esté disponible."
    if record.email.lower()!=user.email.lower(): return False,"El correo cambió. Solicita otro código."
    record.pin_intentos+=1
    valid=len(code)==6 and code.isascii() and code.isdigit() and check_password(code,record.pin_hash)
    if not valid:
        record.save(update_fields=["pin_intentos"])
        left=settings.EMAIL_PIN_MAX_ATTEMPTS-record.pin_intentos
        return False,f"Código incorrecto. Quedan {left} intentos."
    if record.activar_al_verificar:
        user.is_active=True;user.save(update_fields=["is_active"])
    record.activar_al_verificar=False;record.verificado_at=timezone.now();record.pin_hash="";record.token_hash="";record.save()
    return True,"Correo verificado."
