from django.db import models
from apps.core.models import TimeStamped
class IntentoPago(TimeStamped):
    pedido=models.OneToOneField("pedidos.Pedido",on_delete=models.PROTECT,related_name="intento_pago")
    proveedor=models.CharField(max_length=25)
    identificador=models.CharField(max_length=150,blank=True)
    url=models.URLField(max_length=1500,blank=True)
    class Meta:
        db_table="cc_intentos_pago"
class Pago(TimeStamped):
    pedido=models.ForeignKey("pedidos.Pedido",on_delete=models.PROTECT,related_name="pagos")
    proveedor=models.CharField(max_length=25)
    payment_id_externo=models.CharField(max_length=150)
    monto=models.DecimalField(max_digits=12,decimal_places=2)
    moneda=models.CharField(max_length=3,default="MXN")
    estado=models.CharField(max_length=20)
    metodo_pago=models.CharField(max_length=50)
    class Meta:
        db_table="cc_pagos"
        constraints=[models.UniqueConstraint(fields=["proveedor","payment_id_externo"],name="cc_pago_externo_unico"),models.CheckConstraint(condition=models.Q(monto__gt=0,moneda="MXN"),name="cc_pago_monto")]
class VerificacionOpenpay(models.Model):
    codigo=models.CharField(max_length=150)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table="cc_verificacion_openpay"
