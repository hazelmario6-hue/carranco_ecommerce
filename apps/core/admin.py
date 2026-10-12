from django.contrib import admin
from .models import Contacto,Auditoria
class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self,request): return False
    def has_delete_permission(self,request,obj=None): return False
    def get_readonly_fields(self,request,obj=None): return [field.name for field in self.model._meta.fields]
@admin.register(Contacto)
class ContactoAdmin(ReadOnlyAdmin):
    list_display=["nombre","asunto","email","created_at"]
    search_fields=["nombre","email","asunto"]
@admin.register(Auditoria)
class AuditoriaAdmin(ReadOnlyAdmin):
    list_display=["evento","objeto","usuario","created_at"]
admin.site.site_header="Quesos Carranco"
admin.site.site_title="Carranco · Administración"
admin.site.index_title="Panel administrativo"
