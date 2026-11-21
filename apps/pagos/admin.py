from django.contrib import admin
from apps.core.admin import ReadOnlyAdmin
from .models import Pago,IntentoPago
@admin.register(Pago)
class PagoAdmin(ReadOnlyAdmin):
    list_display=["pedido","proveedor","payment_id_externo","monto","estado","created_at"]
    list_filter=["proveedor","estado"]
@admin.register(IntentoPago)
class IntentoAdmin(ReadOnlyAdmin):
    list_display=["pedido","proveedor","identificador"]
# Credentials and card data are never stored in admin records.
