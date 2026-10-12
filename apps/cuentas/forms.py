import hashlib
from datetime import timedelta
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm,AuthenticationForm
from django.db import transaction
from django.utils import timezone
from .models import Direccion,PerfilCliente,IntentoLogin
User=get_user_model()
class RegistroForm(UserCreationForm):
    email=forms.EmailField(label="Correo electrónico",max_length=150)
    first_name=forms.CharField(label="Nombre",max_length=100)
    last_name=forms.CharField(label="Apellidos",max_length=150)
    telefono=forms.CharField(label="Teléfono",max_length=25)
    class Meta:
        model=User
        fields=["first_name","last_name","email","telefono","password1","password2"]
    def clean_email(self):
        email=self.cleaned_data["email"].strip().lower()
        if User.objects.filter(username=email).exists() or User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Este correo ya tiene una cuenta.")
        return email
    def clean_telefono(self):
        field=PerfilCliente._meta.get_field("telefono")
        return field.clean(self.cleaned_data["telefono"],None)
    @transaction.atomic
    def save(self,commit=True):
        user=super().save(commit=False)
        user.username=self.cleaned_data["email"]
        user.email=user.username
        user.is_staff=False
        user.is_superuser=False
        user.save()
        PerfilCliente.objects.create(usuario=user,telefono=self.cleaned_data["telefono"])
        return user
class AccesoForm(AuthenticationForm):
    username=forms.CharField(label="Usuario o correo",max_length=150)
    def clean(self):
        self.cleaned_data["username"]=self.cleaned_data.get("username","").strip().lower()
        ip=self.request.META.get("REMOTE_ADDR","")
        self.key=hashlib.sha256((self.cleaned_data["username"]+":"+ip).encode()).hexdigest()
        with transaction.atomic():
            attempt,_=IntentoLogin.objects.select_for_update().get_or_create(clave=self.key)
            if attempt.bloqueado_hasta and attempt.bloqueado_hasta>timezone.now():
                raise forms.ValidationError("Demasiados intentos. Espera 15 minutos antes de volver a intentarlo.")
        try:
            cleaned=super().clean()
        except forms.ValidationError:
            with transaction.atomic():
                attempt=IntentoLogin.objects.select_for_update().get(clave=self.key)
                if attempt.bloqueado_hasta and attempt.bloqueado_hasta<=timezone.now():
                    attempt.fallos=0;attempt.bloqueado_hasta=None
                attempt.fallos+=1
                if attempt.fallos>=5: attempt.bloqueado_hasta=timezone.now()+timedelta(minutes=15)
                attempt.save()
            raise forms.ValidationError("Usuario o contraseña incorrectos.")
        IntentoLogin.objects.filter(clave=self.key).update(fallos=0,bloqueado_hasta=None)
        return cleaned
class PerfilForm(forms.ModelForm):
    telefono=forms.CharField(label="Teléfono",max_length=25)
    class Meta:
        model=User
        fields=["first_name","last_name"]
        labels={"first_name":"Nombre","last_name":"Apellidos"}
    def clean_telefono(self):
        return PerfilCliente._meta.get_field("telefono").clean(self.cleaned_data["telefono"],None)
class DireccionForm(forms.ModelForm):
    class Meta:
        model=Direccion
        exclude=["usuario","created_at","updated_at"]
        labels={"numero_exterior":"Número exterior","numero_interior":"Número interior","codigo_postal":"Código postal","predeterminada":"Dirección predeterminada"}
