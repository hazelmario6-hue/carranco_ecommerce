from django.core.management.base import BaseCommand,CommandError
from django.core.exceptions import ValidationError
from apps.pagos.services import mercadopago,openpay
from apps.pagos.services.confirmation import confirm
from apps.pagos.services.gateway import configured
class Command(BaseCommand):
    help="Consulta un pago en la pasarela y aplica la misma confirmación idempotente; nunca inicia cobros."
    def add_arguments(self,parser):
        parser.add_argument("provider",choices=["mercadopago","openpay"])
        parser.add_argument("payment_id")
    def handle(self,*args,**options):
        provider=options["provider"]
        if not configured(provider): raise CommandError("Configura la pasarela antes de consultar.")
        module=mercadopago if provider=="mercadopago" else openpay
        try: order=confirm(provider,module.fetch(options["payment_id"]))
        except ValidationError as error: raise CommandError(" ".join(error.messages))
        self.stdout.write(f"{order.numero}: {order.estado_pago}")
