import re
import hmac
import hashlib
import time
from decimal import Decimal
from django.conf import settings
from django.urls import reverse
from django.core.exceptions import ValidationError
from .http import api,checkout_url,money,external_id
BASE="https://api.mercadopago.com"
def headers():
    return {"Authorization":"Bearer "+settings.MP_ACCESS_TOKEN}

def account():
    data=api("GET",BASE+"/users/me",headers=headers())
    if not settings.PAYMENTS_LIVE and not settings.MP_ACCESS_TOKEN.startswith("TEST-") and "test_user" not in data.get("tags",[]):
        raise ValidationError("Las credenciales requieren revisar el modo de prueba. No se inició el cobro.")
    return data

def create(order,ip=""):
    account()
    back=settings.APP_URL+reverse("pedidos:confirmacion",kwargs={"numero":order.numero})
    data={"items":[{"id":order.numero,"title":"Pago Quesos Carranco · "+order.numero,"quantity":1,"currency_id":"MXN","unit_price":order.total_academico}],"payer":{"name":order.usuario.first_name,"surname":order.usuario.last_name,"email":order.usuario.email},"external_reference":str(order.referencia),"back_urls":{"success":back,"pending":back,"failure":back},"notification_url":settings.APP_URL+reverse("pagos:webhook_mp"),"expires":True,"expiration_date_to":order.reserva_expira_at.isoformat(),"payment_methods":{"excluded_payment_types":[{"id":"ticket"},{"id":"atm"}],"installments":1}}
    if settings.APP_URL.startswith("https://"): data["auto_return"]="approved"
    result=api("POST",BASE+"/checkout/preferences",headers={**headers(),"X-Idempotency-Key":str(order.referencia)},payload=data)
    url=result.get("init_point") if settings.PAYMENTS_LIVE else result.get("sandbox_init_point") or result.get("init_point")
    return external_id(result.get("id")),checkout_url(url,["mercadopago.com","mercadopago.com.mx"])

def verify_signature(request):
    if not settings.MP_WEBHOOK_SECRET: return False
    payment_id=request.GET.get("data.id","")
    request_id=request.headers.get("x-request-id","")
    parts={}
    for part in request.headers.get("x-signature","").split(","):
        key,separator,value=part.strip().partition("=")
        if separator: parts[key]=value
    timestamp=parts.get("ts","")
    if not re.fullmatch(r"[0-9]{1,30}",payment_id) or not request_id or len(request_id)>150 or not timestamp.isdigit(): return False
    seconds=int(timestamp)/1000 if len(timestamp)>10 else int(timestamp)
    if abs(time.time()-seconds)>900: return False
    message=f"id:{payment_id};request-id:{request_id};ts:{timestamp};"
    expected=hmac.new(settings.MP_WEBHOOK_SECRET.encode(),message.encode(),hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected,parts.get("v1",""))

def fetch(payment_id):
    if not re.fullmatch(r"[0-9]{1,30}",str(payment_id)): raise ValidationError("Identificador de pago no válido.")
    data=api("GET",BASE+"/v1/payments/"+str(payment_id),headers=headers())
    if str(data.get("id"))!=str(payment_id) or data.get("live_mode") is not settings.PAYMENTS_LIVE: raise ValidationError("La operación no corresponde al entorno configurado.")
    status={"approved":"aprobado","pending":"pendiente","in_process":"pendiente","authorized":"pendiente","rejected":"rechazado","cancelled":"cancelado","refunded":"reembolsado","charged_back":"revision"}.get(data.get("status"),"revision")
    return {"id":str(data["id"]),"reference":data.get("external_reference"),"amount":money(data.get("transaction_amount",0)),"currency":data.get("currency_id"),"status":status,"method":str(data.get("payment_type_id",""))[:50]}
