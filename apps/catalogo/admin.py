from django.contrib import admin
from apps.dashboard.forms import ProductoForm
from apps.core.models import Auditoria
from .models import Categoria,Producto
@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display=["nombre","slug"]
    prepopulated_fields={"slug":["nombre"]}
@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    form=ProductoForm
    list_display=["sku","nombre","categoria","precio_catalogo","precio_de_cobro","stock","stock_reservado","activo"]
    search_fields=["sku","nombre"]
    list_filter=["activo","categoria","destacado"]
    readonly_fields=["stock","stock_reservado","created_at","updated_at"]
    @admin.display(description="Precio de cobro",ordering="precio_academico")
    def precio_de_cobro(self,obj):
        return obj.precio_academico
    def has_delete_permission(self,request,obj=None):
        return False
    def save_model(self,request,obj,form,change):
        if change:
            obj.save(update_fields=[*form.Meta.fields,"updated_at"])
        else:
            obj.save()
        Auditoria.objects.create(usuario=request.user,evento="editar_producto_admin" if change else "crear_producto_admin",objeto=str(obj.pk))
