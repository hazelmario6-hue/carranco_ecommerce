from django.core.management.base import BaseCommand
from apps.core.promociones import ensure_initial_promotion

class Command(BaseCommand):
    help = "Crea la promoción del dúo si existe el SKU; no sobrescribe promociones, precios ni stock."
    def handle(self, *args, **options):
        promo, created = ensure_initial_promotion()
        self.stdout.write("Promoción creada." if created else "Promociones conservadas." if promo else "No existe el SKU duo-tradicion; crea las promociones desde el dashboard.")
