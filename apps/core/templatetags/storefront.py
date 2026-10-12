"""Presentation-only replacements for legacy catalogue and order copy."""
from django import template

register = template.Library()

@register.filter
def storefront_text(value):
    """Keep stored data unchanged while removing obsolete UI notices."""
    text = str(value or "")
    replacements = {
        " La presentación seleccionada pertenece al prototipo académico.": " Consulta la presentación seleccionada.",
        "presentación simulada": "presentación seleccionada",
        "distinto al simulado": "distinto al seleccionado",
        "Conjunto de demostración con un Ranchero y un Panela. La promoción y las presentaciones son ficticias y las fotografías son ilustrativas.": "Conjunto con un Ranchero y un Panela. Fotografías ilustrativas; consulta las presentaciones seleccionadas.",
        " El conjunto y su promoción son una simulación académica.": "",
        "Oferta simulada": "Oferta",
        "Pedido creado; aviso académico aceptado.": "Pedido creado; total a pagar aceptado.",
    }
    for original, replacement in replacements.items():
        text = text.replace(original, replacement)
    return text
