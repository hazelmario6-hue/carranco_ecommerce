from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from django.urls import reverse
from django.conf import settings
from apps.core.models import TimeStamped
class Categoria(models.Model):
    nombre=models.CharField(max_length=80)
    slug=models.SlugField(unique=True)
    class Meta:
        db_table="cc_categorias"
        ordering=["id"]
    def __str__(self):
        return self.nombre
class Producto(TimeStamped):
    sku=models.CharField(max_length=64,unique=True)
    nombre=models.CharField(max_length=150)
    slug=models.SlugField(max_length=100,unique=True)
    legacy_id=models.SlugField(max_length=80,unique=True)
    categoria=models.ForeignKey(Categoria,on_delete=models.PROTECT,related_name="productos")
    descripcion=models.TextField()
    presentacion=models.CharField(max_length=100)
    precio_catalogo=models.DecimalField(max_digits=10,decimal_places=2,validators=[MinValueValidator(Decimal("0"))])
    precio_academico=models.DecimalField(max_digits=10,decimal_places=2,validators=[MinValueValidator(Decimal("0.01"))])
    stock=models.PositiveIntegerField(default=0)
    stock_reservado=models.PositiveIntegerField(default=0)
    imagen=models.ImageField(upload_to="productos/%Y/%m/",blank=True)
    imagen_url=models.URLField(max_length=1000,blank=True)
    galeria=models.JSONField(default=list,blank=True)
    etiqueta=models.CharField(max_length=50,blank=True)
    activo=models.BooleanField(default=True)
    destacado=models.BooleanField(default=False)
    en_catalogo=models.BooleanField(default=True)
    uso_recomendado=models.TextField(blank=True)
    conservacion=models.TextField(blank=True)
    fuente=models.URLField(max_length=1000,blank=True)
    class Meta:
        db_table="cc_productos"
        ordering=["id"]
        constraints=[models.CheckConstraint(condition=models.Q(stock__gte=models.F("stock_reservado")),name="cc_stock_reserva"),models.CheckConstraint(condition=models.Q(precio_catalogo__gte=0,precio_academico__gt=0),name="cc_precios_validos")]
    @property
    def stock_disponible(self):
        return self.stock-self.stock_reservado
    @property
    def disponibilidad(self):
        return "Agotado" if self.stock_disponible==0 else "Últimas unidades" if self.stock_disponible<=settings.STOCK_LOW_THRESHOLD else "Disponible"
    @property
    def foto(self):
        return self.imagen.url if self.imagen else self.imagen_url
    def get_absolute_url(self):
        return reverse("catalogo:detalle",kwargs={"slug":self.slug})
    def __str__(self):
        return self.nombre
