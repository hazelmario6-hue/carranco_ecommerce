from django.db import migrations


def seed(apps, schema_editor):
    alias = schema_editor.connection.alias
    Producto = apps.get_model("catalogo", "Producto")
    Promocion = apps.get_model("core", "Promocion")
    duo = Producto.objects.using(alias).filter(legacy_id="duo-tradicion").first()
    if duo:
        Promocion.objects.using(alias).get_or_create(clave="duo-tradicion", defaults={
            "titulo": "La tradición sabe mejor de a dos", "descripcion": "Queso Ranchero de 400 g y Queso Panela de 400 g para tus recetas favoritas.",
            "producto_id": duo.pk, "imagen_alt": "Tabla de quesos y acompañamientos para compartir", "texto_boton": "Conocer el dúo", "orden": 0,
        })


class Migration(migrations.Migration):
    dependencies = [("core", "0003_promocion")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
