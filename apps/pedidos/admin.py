from django.contrib import admin
from apps.core.admin import ReadOnlyAdmin
from apps.core.templatetags.storefront import storefront_text
from .models import Pedido,PedidoItem,HistorialPedido,MovimientoInventario
@admin.register(Pedido)
class PedidoAdmin(ReadOnlyAdmin):
    list_display=["numero","usuario","estado","estado_pago","total_cobrado","created_at"]
    list_filter=["estado","estado_pago","metodo_pago"]
    search_fields=["usuario__email","referencia"]
    def get_readonly_fields(self,request,obj=None):
        return ["numero"]+super().get_readonly_fields(request,obj)+["total_a_pagar","importe_aceptado_at"]
    def get_fields(self,request,obj=None):
        labels={"total_academico":"total_a_pagar","aviso_academico_aceptado_at":"importe_aceptado_at"}
        return [labels.get(name,name) for name in super().get_fields(request,obj) if name not in labels.values()]
    @admin.display(description="Total a pagar")
    def total_a_pagar(self,obj): return obj.total_academico
    @admin.display(description="Importe aceptado el")
    def importe_aceptado_at(self,obj): return obj.aviso_academico_aceptado_at
@admin.register(PedidoItem)
class ItemAdmin(ReadOnlyAdmin):
    list_display=["pedido","nombre_producto","cantidad","subtotal"]
    def get_readonly_fields(self,request,obj=None):
        return super().get_readonly_fields(request,obj)+["precio_de_cobro_unitario"]
    def get_fields(self,request,obj=None):
        return ["precio_de_cobro_unitario" if name=="precio_academico_unitario" else name for name in super().get_fields(request,obj) if name!="precio_de_cobro_unitario"]
    @admin.display(description="Precio de cobro unitario")
    def precio_de_cobro_unitario(self,obj): return obj.precio_academico_unitario
@admin.register(HistorialPedido)
class HistorialAdmin(ReadOnlyAdmin):
    list_display=["pedido","estado_anterior","estado_nuevo","usuario","created_at"]
    def get_readonly_fields(self,request,obj=None):
        return super().get_readonly_fields(request,obj)+["comentario_visible"]
    def get_fields(self,request,obj=None):
        return ["comentario_visible" if name=="comentario" else name for name in super().get_fields(request,obj) if name!="comentario_visible"]
    @admin.display(description="Comentario")
    def comentario_visible(self,obj): return storefront_text(obj.comentario)
@admin.register(MovimientoInventario)
class MovimientoAdmin(ReadOnlyAdmin):
    list_display=["producto","tipo","cantidad","stock_anterior","stock_nuevo","usuario_admin","fecha"]
