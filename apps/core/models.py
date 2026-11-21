from django.conf import settings
from django.db import models
from django.utils import timezone
class TimeStamped(models.Model):
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta:
        abstract=True
class Contacto(TimeStamped):
    nombre=models.CharField(max_length=100)
    email=models.EmailField()
    telefono=models.CharField(max_length=25,blank=True)
    asunto=models.CharField(max_length=150)
    mensaje=models.TextField(max_length=3000)
    class Meta:
        db_table="cc_contactos"
    def __str__(self):
        return self.asunto
class Auditoria(models.Model):
    usuario=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True)
    evento=models.CharField(max_length=80)
    objeto=models.CharField(max_length=100)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table="cc_auditoria"
        ordering=["-created_at"]

class CorreoPendiente(TimeStamped):
    clave=models.CharField(max_length=160,unique=True)
    destinatario=models.EmailField()
    remitente=models.CharField(max_length=254)
    responder_a=models.EmailField(blank=True)
    asunto=models.CharField(max_length=200)
    texto=models.TextField()
    html=models.TextField()
    estado=models.CharField(max_length=15,default="pendiente",choices=[(x,x.capitalize()) for x in ["pendiente","enviando","enviado","fallido","cancelado"]])
    intentos=models.PositiveSmallIntegerField(default=0)
    primer_intento_at=models.DateTimeField(null=True,blank=True)
    proximo_intento=models.DateTimeField(default=timezone.now)
    bloqueo_hasta=models.DateTimeField(null=True,blank=True)
    vence_at=models.DateTimeField(null=True,blank=True)
    enviado_at=models.DateTimeField(null=True,blank=True)
    id_proveedor=models.CharField(max_length=150,blank=True)
    ultimo_error=models.CharField(max_length=200,blank=True)
    class Meta:
        db_table="cc_correos"
        indexes=[models.Index(fields=["estado","proximo_intento"],name="cc_correo_pendiente")]


class PromocionQuerySet(models.QuerySet):
    def vigentes(self):
        now = timezone.now()
        return self.filter(activa=True).filter(
            models.Q(inicio__isnull=True) | models.Q(inicio__lte=now)
        ).filter(models.Q(fin__isnull=True) | models.Q(fin__gt=now)).filter(
            models.Q(producto__isnull=True) | models.Q(producto__activo=True, producto__stock__gt=models.F("producto__stock_reservado"))
        ).select_related("producto")


class Promocion(TimeStamped):
    titulo = models.CharField(max_length=120)
    descripcion = models.TextField(max_length=600)
    imagen_url = models.URLField("URL de imagen (HTTPS)", max_length=1000, blank=True,
        help_text="Si la dejas vacía, se usa la foto del producto vinculado.")
    imagen_alt = models.CharField("Descripción de la imagen", max_length=200,
        help_text="Describe qué aparece; por ejemplo: Quesos Ranchero y Panela Carranco.")
    producto = models.ForeignKey("catalogo.Producto", on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Se mostrará su precio actual; la promoción no cambia el precio del catálogo.")
    enlace = models.CharField(max_length=1000, blank=True,
        help_text="Ruta del sitio (/productos/...) o URL HTTPS. Vacío: abre el producto vinculado.")
    texto_boton = models.CharField(max_length=50, default="Ver promoción")
    inicio = models.DateTimeField("Inicio", null=True, blank=True)
    fin = models.DateTimeField("Fin", null=True, blank=True)
    activa = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)
    clave = models.SlugField(max_length=80, unique=True, null=True, blank=True, editable=False)
    objects = PromocionQuerySet.as_manager()

    class Meta:
        db_table = "cc_promociones"
        verbose_name = "promoción"
        verbose_name_plural = "promociones"
        ordering = ["orden", "pk"]
        constraints = [models.CheckConstraint(condition=models.Q(inicio__isnull=True) | models.Q(fin__isnull=True) | models.Q(fin__gt=models.F("inicio")), name="cc_promocion_fechas")]

    def __str__(self):
        return self.titulo

    @property
    def foto(self):
        return self.imagen_url or (self.producto.foto if self.producto else "")

    @property
    def destino(self):
        return self.enlace or (self.producto.get_absolute_url() if self.producto else "/productos/")

    @property
    def externa(self):
        return self.destino.startswith("https://")

    @property
    def estado_publicacion(self):
        now = timezone.now()
        if not self.activa: return "Inactiva"
        if self.inicio and self.inicio > now: return "Programada"
        if self.fin and self.fin <= now: return "Vencida"
        if self.producto and (not self.producto.activo or not self.producto.stock_disponible): return "Producto no disponible"
        return "Publicada"

    def clean(self):
        from django.core.exceptions import ValidationError
        from django.core.validators import URLValidator
        errors = {}
        if self.inicio and self.fin and self.fin <= self.inicio:
            errors["fin"] = "El fin debe ser posterior al inicio."
        if self.imagen_url and not self.imagen_url.startswith("https://"):
            errors["imagen_url"] = "La imagen debe usar HTTPS."
        if not self.imagen_url and not (self.producto and self.producto.foto):
            errors["imagen_url"] = "Agrega una URL de imagen o vincula un producto con foto."
        if not self.enlace and not self.producto:
            errors["enlace"] = "Indica un enlace o vincula un producto."
        if self.enlace:
            local = self.enlace.startswith("/") and not self.enlace.startswith("//") and "\\" not in self.enlace
            if not local:
                try: URLValidator(schemes=["https"])(self.enlace)
                except ValidationError: errors["enlace"] = "Usa una ruta del sitio o una URL HTTPS válida."
        if any(c in self.enlace for c in ("\r", "\n")):
            errors["enlace"] = "El enlace contiene caracteres no válidos."
        if self.imagen_alt.strip().lower() in {"imagen ilustrativa", "imagen de producto", "imagen del producto", "foto", "imagen"}:
            errors["imagen_alt"] = "Describe el contenido concreto de la imagen."
        if errors: raise ValidationError(errors)
