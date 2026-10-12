import requests
import simplejson
from urllib.parse import urlsplit
from decimal import Decimal,InvalidOperation
from django.core.exceptions import ValidationError

def api(method,url,*,headers=None,payload=None,auth=None):
    try:
        response=requests.request(method,url,headers={"Content-Type":"application/json",**(headers or {})},data=simplejson.dumps(payload,use_decimal=True) if payload is not None else None,auth=auth,timeout=(3,8),allow_redirects=False)
        if not 200<=response.status_code<300: raise ValidationError("La pasarela no pudo procesar la solicitud. Intenta más tarde.")
        data=simplejson.loads(response.text,use_decimal=True)
        if not isinstance(data,dict): raise ValidationError("Respuesta de pasarela no válida.")
        return data
    except (requests.RequestException,ValueError):
        raise ValidationError("No fue posible contactar a la pasarela. El pedido conserva su estado.")

def checkout_url(value,domains):
    url=urlsplit(str(value))
    if url.scheme!="https" or not url.hostname or url.username or url.password or not any(url.hostname==host or url.hostname.endswith("."+host) for host in domains):
        raise ValidationError("La pasarela devolvió una URL no válida.")
    return value

def money(value):
    try:
        amount=Decimal(str(value))
        if not amount.is_finite() or amount<=0 or amount!=amount.quantize(Decimal("0.01")):
            raise ValidationError("Importe de pasarela no válido.")
        return amount
    except (InvalidOperation,ValueError,TypeError):
        raise ValidationError("Importe de pasarela no válido.")

def external_id(value):
    import re
    if type(value) not in {str,int} or not re.fullmatch(r"[A-Za-z0-9_-]{1,150}",str(value)):
        raise ValidationError("Identificador de pasarela no válido.")
    return str(value)
