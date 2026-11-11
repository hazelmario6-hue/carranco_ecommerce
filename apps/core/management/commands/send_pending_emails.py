from django.core.management.base import BaseCommand
from apps.core.correos import due_ids,deliver_email
class Command(BaseCommand):
    help="Envía correos pendientes; ejecutar cada 5 minutos en un servicio cron con las mismas variables/BD."
    def add_arguments(self,parser): parser.add_argument("--limit",type=int,default=50)
    def handle(self,*args,**options):
        ids=due_ids(max(1,min(options["limit"],500)))
        sent=sum(deliver_email(pk) for pk in ids)
        self.stdout.write(f"{sent} aceptados por el proveedor de {len(ids)} pendientes.")
