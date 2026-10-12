import uuid
from django.conf import settings
from django.db import models
from apps.core.models import TimeStamped
class Pedido(TimeStamped):
    ESTADOS=[(x,x.replace("_"," ").capitalize()) for x in ["pendiente_pago","pagado","preparando","en_camino","entregado","cancelado"]]
    PAGOS=[(x,x.capitalize()) for x in ["pendiente","aprobado","rechazado","cancelado","reembolsado","revision"]]
    usuario=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="pedidos")
    direccion=models.ForeignKey("cuentas.Direccion",on_delete=models.PROTECT)
    direccion_snapshot=models.JSONField()
    clave_idempotencia=models.UUIDField(default=uuid.uuid4)
    referencia=models.UUIDField(default=uuid.uuid4,unique=True,editable=False)
    subtotal_catalogo=models.DecimalField(max_digits=12,decimal_places=2)
    envio=models.DecimalField(max_digits=12,decimal_places=2,default=0)
    total_catalogo=models.DecimalField(max_digits=12,decimal_places=2)
    total_academico=models.DecimalField(max_digits=12,decimal_places=2)
    total_cobrado=models.DecimalField(max_digits=12,decimal_places=2,default=0)
    estado=models.CharField(max_length=25,choices=ESTADOS,default="pendiente_pago")
    estado_pago=models.CharField(max_length=20,choices=PAGOS,default="pendiente")
    metodo_pago=models.CharField(max_length=25)
    reserva_activa=models.BooleanField(default=True)
    reserva_expira_at=models.DateTimeField()
    inventario_descontado_at=models.DateTimeField(null=True,blank=True)
    aviso_academico_aceptado_at=models.DateTimeField()
    class Meta:
        db_table="cc_pedidos"
        ordering=["-created_at"]
        constraints=[models.UniqueConstraint(fields=["usuario","clave_idempotencia"],name="cc_pedido_idempotente"),models.CheckConstraint(condition=models.Q(total_academico__gt=0,subtotal_catalogo__gte=0,envio__gte=0,total_catalogo=models.F("subtotal_catalogo")+models.F("envio"),total_cobrado__gte=0),name="cc_pedido_importes")]
    @property
    def numero(self):
        return f"CARR-{self.pk:06d}"
    @property
    def progreso(self):
        estados=["pagado","preparando","en_camino","entregado"]
        actual=estados.index(self.estado) if self.estado in estados else -1
        return [(label,i<=actual) for i,label in enumerate(["Pago confirmado","Preparando","En camino","Entregado"])]
    def __str__(self):
        return self.numero
class PedidoItem(models.Model):
    pedido=models.ForeignKey(Pedido,on_delete=models.PROTECT,related_name="items")
    producto=models.ForeignKey("catalogo.Producto",on_delete=models.PROTECT)
    sku=models.CharField(max_length=64)
    nombre_producto=models.CharField(max_length=150)
    presentacion=models.CharField(max_length=100)
    precio_unitario=models.DecimalField(max_digits=10,decimal_places=2)
    precio_academico_unitario=models.DecimalField(max_digits=10,decimal_places=2)
    cantidad=models.PositiveSmallIntegerField()
    subtotal=models.DecimalField(max_digits=12,decimal_places=2)
    class Meta:
        db_table="cc_pedido_items"
        constraints=[models.UniqueConstraint(fields=["pedido","producto"],name="cc_item_unico"),models.CheckConstraint(condition=models.Q(cantidad__gte=1,cantidad__lte=20,subtotal=models.F("precio_unitario")*models.F("cantidad")),name="cc_item_importes")]
class HistorialPedido(models.Model):
    pedido=models.ForeignKey(Pedido,on_delete=models.PROTECT,related_name="historial")
    estado_anterior=models.CharField(max_length=25)
    estado_nuevo=models.CharField(max_length=25)
    usuario=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True,blank=True)
    comentario=models.CharField(max_length=250)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table="cc_historial_pedido"
        ordering=["created_at"]
class MovimientoInventario(models.Model):
    producto=models.ForeignKey("catalogo.Producto",on_delete=models.PROTECT,related_name="movimientos")
    tipo=models.CharField(max_length=20,choices=[("venta","Venta"),("ajuste","Ajuste")])
    cantidad=models.IntegerField()
    stock_anterior=models.PositiveIntegerField()
    stock_nuevo=models.PositiveIntegerField()
    pedido=models.ForeignKey(Pedido,on_delete=models.PROTECT,null=True,blank=True)
    usuario_admin=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True,blank=True)
    motivo=models.CharField(max_length=250)
    fecha=models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table="cc_movimientos_inventario"
        constraints=[models.UniqueConstraint(fields=["producto","pedido","tipo"],name="cc_movimiento_unico"),models.CheckConstraint(condition=~models.Q(cantidad=0),name="cc_movimiento_no_cero")]
