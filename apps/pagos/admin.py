from django.contrib import admin
from apps.core.admin import ReadOnlyAdmin
from .models import Pago,IntentoPago,VerificacionOpenpay
@admin.register(Pago)
class PagoAdmin(ReadOnlyAdmin):
    list_display=["pedido","proveedor","payment_id_externo","monto","estado","created_at"]
    list_filter=["proveedor","estado"]
@admin.register(IntentoPago)
class IntentoAdmin(ReadOnlyAdmin):
    list_display=["pedido","proveedor","identificador"]
@admin.register(VerificacionOpenpay)
class VerificationAdmin(ReadOnlyAdmin):
    list_display=["created_at"]
    def has_view_permission(self,request,obj=None): return request.user.is_superuser
    def has_change_permission(self,request,obj=None): return request.user.is_superuser
