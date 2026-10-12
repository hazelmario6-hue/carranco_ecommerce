import json
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from apps.pedidos.views import owned
from .services import mercadopago,openpay
from .services.gateway import start,configured
from .services.confirmation import confirm
from .models import VerificacionOpenpay
@login_required
@require_POST
def pay(request,numero):
    order=owned(request,numero)
    try: url=start(order.pk,request.user,request.META.get("REMOTE_ADDR",""))
    except ValidationError as error:
        messages.error(request," ".join(error.messages));return redirect("pedidos:detalle",numero=order.numero)
    return redirect(url)
@csrf_exempt
@require_POST
def webhook_mp(request):
    if not configured("mercadopago") or not mercadopago.verify_signature(request): return JsonResponse({"ok":False},status=401)
    try:
        payload=json.loads(request.body)
        payment_id=request.GET.get("data.id","")
        if payload.get("type")!="payment": return JsonResponse({"ok":True})
        if str(payload.get("data",{}).get("id"))!=payment_id: return JsonResponse({"ok":False},status=400)
        data=mercadopago.fetch(payment_id)
        confirm("mercadopago",data)
        return JsonResponse({"ok":True})
    except (ValueError,TypeError,AttributeError,KeyError): return JsonResponse({"ok":False},status=400)
    except ValidationError: return JsonResponse({"ok":False},status=503)
@csrf_exempt
@require_POST
def webhook_openpay(request):
    if not openpay.verify_basic(request): return JsonResponse({"ok":False},status=401)
    try:
        payload=json.loads(request.body)
        if payload.get("type")=="verification":
            code=payload.get("verification_code")
            if not isinstance(code,str) or not 1<=len(code)<=150: return JsonResponse({"ok":False},status=400)
            VerificacionOpenpay.objects.create(codigo=code)
            return JsonResponse({"ok":True})
        if payload.get("type") not in {"charge.succeeded","charge.failed","charge.cancelled","charge.refunded"}: return JsonResponse({"ok":True})
        if not configured("openpay"): return JsonResponse({"ok":False},status=503)
        data=openpay.fetch(payload["transaction"]["id"])
        confirm("openpay",data)
        return JsonResponse({"ok":True})
    except (ValueError,TypeError,AttributeError,KeyError): return JsonResponse({"ok":False},status=400)
    except ValidationError: return JsonResponse({"ok":False},status=503)
