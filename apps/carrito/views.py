import json
from django.http import JsonResponse
from django.shortcuts import render,redirect
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST
from .services import summarize,change,items,KEY,MAX_QUANTITY
from apps.catalogo.models import Producto

def detail(request):
    return render(request,"carrito/carrito.html",{"cart":summarize(request.session)})
def payload(cart):
    return {"ok":True,"count":cart["count"],"subtotal":str(cart["subtotal"]),"total":str(cart["total"]),"academico":str(cart["academico"])}
@require_POST
def mutate(request):
    ajax=request.content_type=="application/json"
    try:
        data=json.loads(request.body) if ajax else request.POST
        if not isinstance(data,dict) and ajax: raise ValueError()
        if ajax and set(data)-{"producto","cantidad","operacion"}: raise ValidationError("La solicitud contiene campos no permitidos.")
        operation=data.get("operacion","set")
        if operation not in {"add","set","clear"}: raise ValidationError("Operación no válida.")
        if operation=="clear":
            request.session[KEY]={};cart=summarize(request.session)
        else:
            raw=data.get("cantidad",1)
            if type(raw) is bool or ajax and type(raw) is not int: raise ValueError()
            quantity=int(raw)
            if ajax and type(data.get("producto")) is not int: raise ValueError()
            product_id=int(data.get("producto"))
            if product_id<=0: raise ValueError()
            cart=change(request.session,product_id,quantity,operation)
        if ajax: return JsonResponse(payload(cart))
        messages.success(request,"Carrito actualizado.")
    except (ValidationError,ValueError,TypeError,json.JSONDecodeError) as error:
        message=" ".join(error.messages) if isinstance(error,ValidationError) else "Solicitud de carrito no válida."
        if ajax: return JsonResponse({"ok":False,"message":message},status=400)
        messages.error(request,message)
    return redirect("carrito:detalle")
@require_POST
def import_legacy(request):
    if request.session.get("carranco_legacy_imported"):
        return JsonResponse({**payload(summarize(request.session)),"warnings":[]})
    try:
        data=json.loads(request.body)
        if not isinstance(data,list) or len(data)>30: raise ValueError()
        merged={}
        for row in data:
            if not isinstance(row,dict) or set(row)-{"id","quantity"} or type(row.get("quantity")) is not int or not isinstance(row.get("id"),str) or not 1<=row["quantity"]<=20: raise ValueError()
            merged[row["id"]]=min(20,merged.get(row["id"],0)+row["quantity"])
        cart=items(request.session);warnings=[]
        for product in Producto.objects.filter(legacy_id__in=merged,activo=True):
            requested=merged.pop(product.legacy_id)
            qty=min(requested,MAX_QUANTITY,product.stock_disponible)
            if qty: cart[str(product.pk)]=min(MAX_QUANTITY,product.stock_disponible,max(cart.get(str(product.pk),0),qty))
            if not qty: warnings.append(product.nombre+" está agotado.")
            elif qty<requested: warnings.append(product.nombre+": cantidad ajustada al inventario disponible.")
        if merged: warnings.append("Algunos productos anteriores ya no están disponibles.")
        request.session[KEY]=cart;request.session["carranco_legacy_imported"]=True
        return JsonResponse({**payload(summarize(request.session)),"warnings":warnings})
    except (ValueError,TypeError,json.JSONDecodeError):
        return JsonResponse({"ok":False,"message":"El carrito anterior contiene datos no válidos."},status=400)
