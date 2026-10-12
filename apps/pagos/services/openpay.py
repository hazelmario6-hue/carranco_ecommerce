import base64
import hmac
import re
from decimal import Decimal
from django.conf import settings
from django.urls import reverse
from django.core.exceptions import ValidationError
from .http import api,checkout_url,money,external_id

def endpoint():
    host="https://api.openpay.mx" if settings.OPENPAY_PRODUCTION else "https://sandbox-api.openpay.mx"
    if not re.fullmatch(r"[a-zA-Z0-9]{10,40}",settings.OPENPAY_MERCHANT_ID): raise ValidationError("La segunda pasarela no está configurada.")
    return host+"/v1/"+settings.OPENPAY_MERCHANT_ID

def create(order,ip=""):
    user=order.usuario
    phone=getattr(getattr(user,"perfil_cliente",None),"telefono","")
    data={"method":"card","amount":order.total_academico,"currency":"MXN","description":"Pago Quesos Carranco "+order.numero,"order_id":str(order.referencia),"customer":{"name":user.first_name,"last_name":user.last_name,"email":user.email,"phone_number":phone},"confirm":False,"send_email":False,"redirect_url":settings.APP_URL+reverse("pedidos:confirmacion",kwargs={"numero":order.numero})}
    result=api("POST",endpoint()+"/charges",headers={"X-Forwarded-For":ip},payload=data,auth=(settings.OPENPAY_PRIVATE_KEY,""))
    return external_id(result.get("id")),checkout_url(result.get("payment_method",{}).get("url"),["openpay.mx"])

def verify_basic(request):
    if not settings.OPENPAY_WEBHOOK_USER or not settings.OPENPAY_WEBHOOK_PASSWORD: return False
    kind,separator,encoded=request.headers.get("Authorization","").partition(" ")
    if kind.lower()!="basic" or not separator: return False
    try: value=base64.b64decode(encoded,validate=True).decode()
    except (ValueError,UnicodeError): return False
    expected=settings.OPENPAY_WEBHOOK_USER+":"+settings.OPENPAY_WEBHOOK_PASSWORD
    return hmac.compare_digest(value.encode(),expected.encode())

def fetch(payment_id):
    if not re.fullmatch(r"[a-zA-Z0-9]{1,150}",str(payment_id)): raise ValidationError("Identificador de pago no válido.")
    data=api("GET",endpoint()+"/charges/"+str(payment_id),auth=(settings.OPENPAY_PRIVATE_KEY,""))
    if str(data.get("id"))!=str(payment_id) or data.get("transaction_type")!="charge": raise ValidationError("Operación no válida.")
    status={"completed":"aprobado","in_progress":"pendiente","charge_pending":"pendiente","failed":"rechazado","cancelled":"cancelado","refunded":"reembolsado"}.get(data.get("status"),"revision")
    return {"id":str(data["id"]),"reference":data.get("order_id"),"amount":money(data.get("amount",0)),"currency":data.get("currency"),"status":status,"method":str(data.get("method","card"))[:50]}
