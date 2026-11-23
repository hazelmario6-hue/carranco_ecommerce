from django import forms
from django.utils.text import slugify
from apps.catalogo.models import Producto
from apps.pedidos.models import Cupon
from apps.core.templatetags.storefront import storefront_text

class StorefrontCopyMixin:
    """Display legacy copy cleanly and preserve an untouched stored value."""
    def format_value(self,value):
        if value==self.original_copy:
            value=storefront_text(value)
        return super().format_value(value)
    def value_from_datadict(self,data,files,name):
        value=super().value_from_datadict(data,files,name)
        return self.original_copy if value==storefront_text(self.original_copy) else value

class StorefrontTextarea(StorefrontCopyMixin,forms.Textarea):
    pass

class StorefrontTextInput(StorefrontCopyMixin,forms.TextInput):
    pass

class ProductoForm(forms.ModelForm):
    class Meta:
        model=Producto
        fields=["sku","nombre","slug","legacy_id","categoria","descripcion","presentacion","precio_catalogo","imagen","imagen_url","activo","destacado","en_catalogo","etiqueta","uso_recomendado","conservacion"]
        labels={"precio_catalogo":"Precio de venta"}
        widgets={"descripcion":forms.Textarea(attrs={"rows":4}),"uso_recomendado":forms.Textarea(attrs={"rows":3}),"conservacion":forms.Textarea(attrs={"rows":3})}
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        for name in ["descripcion","etiqueta","uso_recomendado","conservacion"]:
            original=self.initial.get(name,"")
            if storefront_text(original)!=original:
                field=self.fields[name]
                widget_class=StorefrontTextarea if isinstance(field.widget,forms.Textarea) else StorefrontTextInput
                widget=widget_class(attrs=field.widget.attrs)
                widget.original_copy=original
                field.widget=widget
    def save(self,commit=True):
        product=super().save(commit=False)
        # Campo heredado: se conserva en BD, pero los nuevos pedidos usan precio_catalogo.
        product.precio_academico=product.precio_catalogo
        if commit:
            if product.pk:
                product.save(update_fields=[*self.Meta.fields,"precio_academico","updated_at"])
            else:
                product.save()
            self.save_m2m()
        return product
    def clean_precio_catalogo(self):
        price=self.cleaned_data["precio_catalogo"]
        if price<=0: raise forms.ValidationError("El precio de venta debe ser mayor que cero.")
        return price
    def clean_imagen(self):
        image=self.cleaned_data.get("imagen")
        if image and hasattr(image,"size") and image.size>2*1024*1024: raise forms.ValidationError("La imagen no debe superar 2 MB.")
        if image and hasattr(image,"image") and (image.image.format not in {"JPEG","PNG","WEBP"} or image.image.width*image.image.height>20000000): raise forms.ValidationError("Utiliza JPG, PNG o WebP de hasta 20 megapíxeles.")
        return image
    def clean_imagen_url(self):
        value=self.cleaned_data.get("imagen_url","")
        if value and not value.startswith("https://"): raise forms.ValidationError("La URL de imagen debe usar HTTPS.")
        return value
class AjusteForm(forms.Form):
    cantidad=forms.IntegerField(min_value=-10000,max_value=10000,label="Ajuste de unidades (+ / −)")
    motivo=forms.CharField(min_length=5,max_length=250,label="Motivo")
    def clean_cantidad(self):
        value=self.cleaned_data["cantidad"]
        if value==0: raise forms.ValidationError("El ajuste debe ser distinto de cero.")
        return value
class EstadoForm(forms.Form):
    estado=forms.ChoiceField(choices=[("preparando","Preparando"),("en_camino","En camino"),("entregado","Entregado"),("cancelado","Cancelar pendiente")])
    comentario=forms.CharField(min_length=5,max_length=250,label="Comentario")


from apps.core.models import Promocion

class PromocionForm(forms.ModelForm):
    class Meta:
        model = Promocion
        fields = ["titulo", "descripcion", "producto", "imagen_url", "imagen_alt", "enlace", "texto_boton", "inicio", "fin", "activa", "orden"]
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 3}),
            "inicio": forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}),
            "fin": forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}),
        }
        help_texts = {"inicio": "Hora de Ciudad de México. Vacío: disponible desde ahora.", "fin": "Hora de Ciudad de México. Vacío: sin fecha de término."}

class CuponForm(forms.ModelForm):
    class Meta:
        model=Cupon
        fields=["codigo","tipo","valor","compra_minima","inicio","fin","max_usos","max_usos_cliente","activo"]
        widgets={
            "inicio":forms.DateTimeInput(format="%Y-%m-%dT%H:%M",attrs={"type":"datetime-local"}),
            "fin":forms.DateTimeInput(format="%Y-%m-%dT%H:%M",attrs={"type":"datetime-local"}),
        }
        help_texts={
            "codigo":"Letras, números, guion o guion bajo. Se guardará en mayúsculas.",
            "valor":"Porcentaje (hasta 100) o importe en MXN según el tipo.",
            "compra_minima":"Subtotal mínimo de productos; el envío no cuenta.",
            "max_usos":"Vacío significa sin límite global.",
            "max_usos_cliente":"Recomendado: 1 uso por cuenta.",
            "inicio":"Hora de Ciudad de México. Vacío: disponible ahora.",
            "fin":"Hora de Ciudad de México. Vacío: sin vencimiento.",
        }
    def clean_codigo(self): return self.cleaned_data["codigo"].strip().upper()
