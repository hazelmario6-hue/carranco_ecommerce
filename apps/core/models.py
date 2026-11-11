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
