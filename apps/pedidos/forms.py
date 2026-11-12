from django import forms
from apps.cuentas.models import Direccion

class CheckoutForm(forms.Form):
    direccion=forms.ModelChoiceField(queryset=Direccion.objects.none(),label="Dirección de entrega")
    proveedor=forms.ChoiceField(label="¿Cómo deseas pagar?",choices=[])
    clave=forms.UUIDField(widget=forms.HiddenInput)
    resumen=forms.CharField(widget=forms.HiddenInput)

    def __init__(self,*args,user,openpay=False,mercadopago=False,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields["direccion"].queryset=Direccion.objects.filter(usuario=user)
        choices=[]
        if mercadopago:
            choices.append(("mercadopago","Mercado Pago · tarjeta y métodos disponibles"))
        if openpay:
            choices.append(("openpay","Openpay · tarjeta"))
        self.fields["proveedor"].choices=choices
        if len(choices)==1:
            self.fields["proveedor"].initial=choices[0][0]
