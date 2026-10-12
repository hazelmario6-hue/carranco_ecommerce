from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group,Permission
class Command(BaseCommand):
    help="Crea grupos Django; no crea usuarios ni contraseñas. Asigna is_staff desde Django Admin."
    def handle(self,*args,**options):
        group,_=Group.objects.get_or_create(name="Carranco Administradores")
        group.permissions.set(Permission.objects.filter(content_type__app_label__in=["catalogo","cuentas","pedidos","pagos","core"]).exclude(codename__startswith="delete_"))
        operator,_=Group.objects.get_or_create(name="Carranco Operadores")
        operator.permissions.set(Permission.objects.filter(content_type__app_label__in=["catalogo","cuentas","pedidos","pagos"],codename__startswith="view_"))
        self.stdout.write("Grupos creados. Los operadores consultan; los administradores gestionan; ambos requieren is_staff.")
