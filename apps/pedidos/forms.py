from django import forms
from apps.cuentas.models import Direccion
class CheckoutForm(forms.Form):
    direccion=forms.ModelChoiceField(queryset=Direccion.objects.none(),label="Dirección de entrega")
    proveedor=forms.ChoiceField(label="¿Cómo deseas pagar?",choices=[("mercadopago","Mercado Pago · tarjeta y métodos disponibles")])
    aceptar=forms.BooleanField(label="Acepto el total a pagar y autorizo continuar con el pago.",required=True)
    clave=forms.UUIDField(widget=forms.HiddenInput)
    resumen=forms.CharField(widget=forms.HiddenInput)
    def __init__(self,*args,user,openpay=False,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields["direccion"].queryset=Direccion.objects.filter(usuario=user)
        if openpay: self.fields["proveedor"].choices.append(("openpay","Openpay · tarjeta"))
