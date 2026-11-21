def ensure_initial_promotion():
    from apps.catalogo.models import Producto
    from .models import Promocion
    duo = Producto.objects.filter(legacy_id="duo-tradicion").first()
    if duo:
        return Promocion.objects.get_or_create(clave="duo-tradicion", defaults={
            "titulo": "La tradición sabe mejor de a dos", "descripcion": "Queso Ranchero de 400 g y Queso Panela de 400 g para tus recetas favoritas.",
            "producto": duo, "imagen_alt": "Tabla de quesos y acompañamientos para compartir", "texto_boton": "Conocer el dúo", "orden": 0,
        })
    return None, False
