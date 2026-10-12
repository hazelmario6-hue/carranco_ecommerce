from django.conf import settings
from django.db import models
from django.core.validators import RegexValidator
from apps.core.models import TimeStamped
class PerfilCliente(TimeStamped):
    usuario=models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="perfil_cliente")
    telefono=models.CharField(max_length=25,blank=True,validators=[RegexValidator(r"^[+0-9 ()-]{7,25}$","Ingresa un teléfono válido.")])
    class Meta:
        db_table="cc_perfiles"
class Direccion(TimeStamped):
    usuario=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="direcciones")
    calle=models.CharField(max_length=150)
    numero_exterior=models.CharField(max_length=30)
    numero_interior=models.CharField(max_length=30,blank=True)
    colonia=models.CharField(max_length=150)
    codigo_postal=models.CharField(max_length=5,validators=[RegexValidator(r"^[0-9]{5}$","El código postal debe tener cinco dígitos.")])
    ciudad=models.CharField(max_length=100)
    estado=models.CharField(max_length=100)
    referencias=models.CharField(max_length=500,blank=True)
    predeterminada=models.BooleanField(default=False)
    class Meta:
        db_table="cc_direcciones"
        ordering=["-predeterminada","-id"]
    def __str__(self):
        return f"{self.calle} {self.numero_exterior}, {self.colonia}, {self.ciudad}"
class IntentoLogin(models.Model):
    clave=models.CharField(max_length=64,unique=True)
    fallos=models.PositiveIntegerField(default=0)
    bloqueado_hasta=models.DateTimeField(null=True,blank=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta:
        db_table="cc_intentos_login"
