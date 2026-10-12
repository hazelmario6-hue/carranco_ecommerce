import json
from pathlib import Path
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.catalogo.models import Categoria,Producto
class Command(BaseCommand):
    help="Carga categorías y nueve SKU sin sobrescribir precios, stock ni productos existentes."
    @transaction.atomic
    def handle(self,*args,**options):
        categorias={}
        for slug,nombre in [("frescos","Quesos frescos"),("fundir","Para fundir"),("madurados","Madurados"),("mantequilla","Mantequilla"),("ofertas","Ofertas")]:
            categorias[slug],_=Categoria.objects.get_or_create(slug=slug,defaults={"nombre":nombre})
        rows=json.loads((Path(__file__).resolve().parents[2]/"data/productos.json").read_text())
        creados=0
        for data in rows:
            data.pop("id")
            sku=data.pop("sku")
            data["categoria"]=categorias[data["categoria"]]
            data["precio_catalogo"]=Decimal(str(data["precio_catalogo"]))
            data["precio_academico"]=Decimal(str(data["precio_academico"]))
            _,nuevo=Producto.objects.get_or_create(sku=sku,defaults=data)
            creados+=int(nuevo)
        self.stdout.write(self.style.SUCCESS(f"{creados} SKU nuevos; los productos anteriores se conservan."))
