from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from apps.pedidos.models import Pedido
from apps.pedidos.services import release_locked
class Command(BaseCommand):
    help="Libera reservas vencidas sin pago aprobado; no cancela ni reembolsa pagos confirmados."
    def handle(self,*args,**options):
        count=0
        ids=list(Pedido.objects.filter(reserva_activa=True,estado="pendiente_pago",reserva_expira_at__lt=timezone.now()).exclude(estado_pago="aprobado").values_list("pk",flat=True))
        for pk in ids:
            with transaction.atomic():
                order=Pedido.objects.select_for_update().get(pk=pk)
                if order.reserva_activa and order.estado=="pendiente_pago" and order.estado_pago not in {"aprobado","revision"}:
                    release_locked(order,"Reserva vencida sin pago confirmado.");count+=1
        self.stdout.write(f"{count} reservas liberadas.")
