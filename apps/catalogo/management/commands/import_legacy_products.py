import json
import re
from django.core.management.base import BaseCommand,CommandError
from django.db import connection,transaction
from django.utils.text import slugify
from apps.catalogo.models import Categoria,Producto
class Command(BaseCommand):
    help="Copia productos de la base anterior sin modificarla; rechaza bases con pedidos para exigir revisión de su historial."
    def add_arguments(self,parser):
        parser.add_argument("--database",required=True)
    @transaction.atomic
    def handle(self,*args,**options):
        source=options["database"]
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}",source): raise CommandError("Nombre de base no válido.")
        if source==connection.settings_dict["NAME"]: raise CommandError("Utiliza una base Django separada para conservar la anterior.")
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM `{source}`.`pedidos`")
            if cursor.fetchone()[0]: raise CommandError("Hay pedidos anteriores: conserva la base y revisa el traslado de su historial antes de copiar existencias.")
            cursor.execute(f"SELECT * FROM `{source}`.`productos`")
            names=[col[0] for col in cursor.description]
            rows=[dict(zip(names,row)) for row in cursor.fetchall()]
        labels={"frescos":"Quesos frescos","fundir":"Para fundir","madurados":"Madurados","mantequilla":"Mantequilla","ofertas":"Ofertas"}
        created=0
        for row in rows:
            if row.get("stock_reservado",0): raise CommandError("Hay reservas anteriores. Revisa su origen antes de copiar existencias.")
            category,_=Categoria.objects.get_or_create(slug=row["categoria"],defaults={"nombre":labels.get(row["categoria"],row["categoria"])})
            legacy=row["slug"]
            data={key:row[key] for key in ["nombre","descripcion","presentacion","precio_catalogo","precio_academico","stock","etiqueta","activo","destacado","en_catalogo","uso_recomendado","conservacion","fuente"]}
            data.update(categoria=category,legacy_id=legacy,slug="queso-"+legacy if row["nombre"].startswith("Queso ") else legacy,imagen_url=row["imagen"],galeria=json.loads(row["galeria"]) if isinstance(row["galeria"],str) else row["galeria"])
            _,new=Producto.objects.get_or_create(sku=row["sku"],defaults=data);created+=int(new)
        self.stdout.write(self.style.SUCCESS(f"{created} productos copiados. La base anterior se conserva intacta; no se sobrescriben SKU existentes."))
