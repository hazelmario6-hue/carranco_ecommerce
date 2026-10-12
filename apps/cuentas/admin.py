from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from .models import Direccion,PerfilCliente
from apps.core.admin import ReadOnlyAdmin
User=get_user_model()
admin.site.unregister(User)
@admin.register(User)
class CarrancoUserAdmin(UserAdmin):
    def get_fieldsets(self,request,obj=None):
        if obj is None: return super().get_fieldsets(request,obj)
        return [(title,{**options,"fields":tuple(field for field in options["fields"] if field!="password")}) for title,options in super().get_fieldsets(request,obj)]
@admin.register(PerfilCliente)
class PerfilAdmin(ReadOnlyAdmin):
    list_display=["usuario","telefono","created_at"]
@admin.register(Direccion)
class DireccionAdmin(ReadOnlyAdmin):
    list_display=["usuario","calle","ciudad","codigo_postal","predeterminada"]
