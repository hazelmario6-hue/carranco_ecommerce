from django.conf import settings
from django.db import models
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
