"""Durable outbox: store before send; mail failure never rolls back a payment."""
import logging
from datetime import timedelta
import requests
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from .models import CorreoPendiente
logger=logging.getLogger(__name__)

class MailDeliveryError(Exception):
    pass

def configured():
    if settings.MAIL_PROVIDER=="resend":
        return bool(settings.RESEND_API_KEY and settings.DEFAULT_FROM_EMAIL and "example.com" not in settings.DEFAULT_FROM_EMAIL)
    return settings.DEBUG and settings.MAIL_PROVIDER=="console"

def queue_email(key,to,subject,text,html,expires=None):
    mail,_=CorreoPendiente.objects.get_or_create(clave=key,defaults={
        "destinatario":to,"remitente":settings.DEFAULT_FROM_EMAIL,"responder_a":settings.EMAIL_REPLY_TO,
        "asunto":subject,"texto":text,"html":html,"vence_at":expires})
    transaction.on_commit(lambda pk=mail.pk: deliver_email(pk), robust=True)
    return mail

def send_email(mail):
    if settings.MAIL_PROVIDER=="resend":
        if not configured(): raise MailDeliveryError("Falta configurar el proveedor o el remitente.")
        payload={"from":mail.remitente,"to":[mail.destinatario],"subject":mail.asunto,"text":mail.texto,"html":mail.html}
        if mail.responder_a: payload["reply_to"]=mail.responder_a
        try:
            response=requests.post("https://api.resend.com/emails",headers={
                "Authorization":"Bearer "+settings.RESEND_API_KEY,
                "Idempotency-Key":"carranco/"+mail.clave},json=payload,timeout=(3,8),allow_redirects=False)
            if not 200<=response.status_code<300:
                raise MailDeliveryError("El proveedor de correo respondió HTTP "+str(response.status_code)+".")
            data=response.json()
            if not isinstance(data,dict) or not isinstance(data.get("id"),str):
                raise MailDeliveryError("Respuesta de correo no válida.")
            return data["id"][:150]
        except (requests.RequestException,ValueError):
            raise MailDeliveryError("No fue posible confirmar el envío con el proveedor.")
    if settings.MAIL_PROVIDER=="console" and settings.DEBUG:
        message=EmailMultiAlternatives(mail.asunto,mail.texto,mail.remitente,[mail.destinatario],
            reply_to=[mail.responder_a] if mail.responder_a else [])
        message.attach_alternative(mail.html,"text/html")
        if message.send()!=1: raise MailDeliveryError("El backend local no aceptó el mensaje.")
        return "local-development"
    raise MailDeliveryError("Proveedor de correo no habilitado.")

def deliver_email(pk):
    now=timezone.now()
    with transaction.atomic():
        mail=CorreoPendiente.objects.select_for_update().get(pk=pk)
        if mail.estado in {"enviado","fallido","cancelado"}: return False
        if mail.estado=="enviando" and mail.bloqueo_hasta and mail.bloqueo_hasta>now: return False
        if mail.proximo_intento>now: return False
        if mail.vence_at and mail.vence_at<=now:
            mail.estado="cancelado";mail.texto="";mail.html="";mail.save();return False
        # Resend retains idempotency keys for 24 h. Never auto-retry an ambiguous send beyond that window.
        if not configured():
            mail.ultimo_error="Falta configurar el proveedor o el remitente."
            mail.estado="pendiente";mail.proximo_intento=now+timedelta(minutes=5);mail.bloqueo_hasta=None;mail.save();return False
        if mail.intentos and mail.primer_intento_at and now-mail.primer_intento_at>timedelta(hours=23):
            mail.estado="fallido";mail.ultimo_error="Revisar entrega en proveedor antes de reenviar (ventana de idempotencia).";mail.save();return False
        if mail.intentos>=6:
            mail.estado="fallido";mail.save();return False
        if not mail.intentos:
            mail.primer_intento_at=now
            mail.remitente=settings.DEFAULT_FROM_EMAIL;mail.responder_a=settings.EMAIL_REPLY_TO
        mail.estado="enviando";mail.intentos+=1;mail.bloqueo_hasta=now+timedelta(minutes=2);mail.save()
    try:
        identifier=send_email(mail)
    except MailDeliveryError as error:
        CorreoPendiente.objects.filter(pk=pk,estado="enviando").update(
            estado="fallido" if mail.intentos>=6 else "pendiente",ultimo_error=str(error),bloqueo_hasta=None,
            proximo_intento=timezone.now()+timedelta(seconds=min(3600,60*2**mail.intentos)))
        logger.warning("Correo %s pendiente: %s",pk,error) # No API key, token, recipient or body in logs.
        return False
    CorreoPendiente.objects.filter(pk=pk,estado="enviando").update(
        estado="enviado",enviado_at=timezone.now(),id_proveedor=identifier,ultimo_error="",bloqueo_hasta=None)
    return True

def due_ids(limit=50):
    now=timezone.now()
    return list(CorreoPendiente.objects.filter(Q(estado="pendiente")|Q(estado="enviando",bloqueo_hasta__lte=now),
        proximo_intento__lte=now).order_by("created_at").values_list("pk",flat=True)[:limit])
