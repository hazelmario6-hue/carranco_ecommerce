import uuid
from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone
from apps.core.models import TimeStamped

class Cupon(TimeStamped):
    TIPOS=[("porcentaje","Porcentaje"),("fijo","Importe fijo")]
    codigo=models.CharField(max_length=32,unique=True,validators=[RegexValidator(r"^[A-Z0-9_-]+$","Usa letras, números, guion o guion bajo.")])
    tipo=models.CharField(max_length=15,choices=TIPOS)
    valor=models.DecimalField(max_digits=10,decimal_places=2)
    compra_minima=models.DecimalField(max_digits=12,decimal_places=2,default=0)
    inicio=models.DateTimeField(null=True,blank=True)
    fin=models.DateTimeField(null=True,blank=True)
    max_usos=models.PositiveIntegerField("Usos totales máximos",null=True,blank=True)
    max_usos_cliente=models.PositiveSmallIntegerField("Usos máximos por cliente",default=1)
    activo=models.BooleanField(default=True)
    class Meta:
        db_table="cc_cupones"
        ordering=["-created_at"]
        constraints=[
            models.CheckConstraint(condition=models.Q(valor__gt=0),name="cc_cupon_valor_positivo"),
            models.CheckConstraint(condition=models.Q(compra_minima__gte=0),name="cc_cupon_minimo_valido"),
            models.CheckConstraint(condition=models.Q(max_usos__isnull=True)|models.Q(max_usos__gt=0),name="cc_cupon_usos_validos"),
            models.CheckConstraint(condition=models.Q(max_usos_cliente__gt=0),name="cc_cupon_cliente_valido"),
            models.CheckConstraint(condition=models.Q(inicio__isnull=True)|models.Q(fin__isnull=True)|models.Q(fin__gt=models.F("inicio")),name="cc_cupon_fechas"),
        ]
    def clean(self):
        errors={}
        self.codigo=(self.codigo or "").strip().upper()
        if self.tipo=="porcentaje" and self.valor>Decimal("100.00"): errors["valor"]="El porcentaje no puede superar 100."
        if self.inicio and self.fin and self.fin<=self.inicio: errors["fin"]="El fin debe ser posterior al inicio."
        if errors: raise ValidationError(errors)
    def save(self,*args,**kwargs):
        self.codigo=(self.codigo or "").strip().upper()
        super().save(*args,**kwargs)
    def descuento_para(self,subtotal):
        amount=subtotal*self.valor/Decimal("100") if self.tipo=="porcentaje" else self.valor
        return min(subtotal,amount.quantize(Decimal("0.01"),rounding=ROUND_HALF_UP))
    def usos_vigentes(self):
        """Compras confirmadas o reservas que todavía pueden pagarse."""
        now=timezone.now()
        return self.usos.filter(
            models.Q(pedido__estado_pago__in=["aprobado","revision"])|
            models.Q(pedido__reserva_activa=True,pedido__reserva_expira_at__gt=now)
        ).count()
    @property
    def estado_publicacion(self):
        now=timezone.now()
        if not self.activo:return "Inactivo"
        if self.inicio and self.inicio>now:return "Programado"
        if self.fin and self.fin<=now:return "Vencido"
        if self.max_usos and self.usos_vigentes()>=self.max_usos:return "Agotado"
        return "Disponible"
    def __str__(self): return self.codigo

class Pedido(TimeStamped):
    ESTADOS=[(x,x.replace("_"," ").capitalize()) for x in ["pendiente_pago","pagado","preparando","en_camino","entregado","cancelado"]]
    PAGOS=[(x,x.capitalize()) for x in ["pendiente","aprobado","rechazado","cancelado","reembolsado","revision"]]
    usuario=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="pedidos")
    direccion=models.ForeignKey("cuentas.Direccion",on_delete=models.PROTECT)
    direccion_snapshot=models.JSONField()
    correo_cliente=models.EmailField(blank=True)
    clave_idempotencia=models.UUIDField(default=uuid.uuid4)
    referencia=models.UUIDField(default=uuid.uuid4,unique=True,editable=False)
    subtotal_catalogo=models.DecimalField(max_digits=12,decimal_places=2)
    envio=models.DecimalField(max_digits=12,decimal_places=2,default=0)
    descuento=models.DecimalField(max_digits=12,decimal_places=2,default=0)
    cupon=models.ForeignKey(Cupon,on_delete=models.SET_NULL,null=True,blank=True,related_name="pedidos")
    codigo_cupon=models.CharField(max_length=32,blank=True)
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
        constraints=[models.UniqueConstraint(fields=["usuario","clave_idempotencia"],name="cc_pedido_idempotente"),models.CheckConstraint(condition=models.Q(total_academico__gt=0,subtotal_catalogo__gte=0,envio__gte=0,descuento__gte=0,total_catalogo=models.F("subtotal_catalogo")+models.F("envio")-models.F("descuento"),total_cobrado__gte=0),name="cc_pedido_importes")]
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

class UsoCupon(models.Model):
    cupon=models.ForeignKey(Cupon,on_delete=models.PROTECT,related_name="usos")
    usuario=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="usos_cupon")
    pedido=models.OneToOneField(Pedido,on_delete=models.CASCADE,related_name="uso_cupon")
    descuento=models.DecimalField(max_digits=12,decimal_places=2)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table="cc_usos_cupon"
        indexes=[models.Index(fields=["cupon","usuario"],name="cc_cupon_usuario")]
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
