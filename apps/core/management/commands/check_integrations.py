from urllib.parse import urlsplit
from email.utils import parseaddr
from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from apps.core.correos import configured as mail_configured
from apps.pagos.services.gateway import configured
from apps.pagos.services import mercadopago,openpay
from apps.pagos.services.http import api

class Command(BaseCommand):
    help='Diagnóstico sin imprimir claves. --remote solo hace consultas GET; no cobra ni envía correos.'
    def add_arguments(self,parser): parser.add_argument('--remote',action='store_true')
    def handle(self,*args,**options):
        origin=urlsplit(settings.APP_URL)
        self.stdout.write('APP_URL HTTPS: '+str(origin.scheme=='https' and bool(origin.hostname)))
        self.stdout.write('Modo de pago: '+('REAL (importe académico)' if settings.PAYMENTS_LIVE else 'PRUEBAS, sin cobros reales'))
        sender=parseaddr(settings.DEFAULT_FROM_EMAIL)[1]
        self.stdout.write('Correo: '+settings.MAIL_PROVIDER+' · '+('variables presentes' if mail_configured() else 'FALTAN variables/remitente'))
        if sender.endswith('@resend.dev'):self.stdout.write('Remitente resend.dev: solo pruebas hacia el correo del propietario de la cuenta Resend.')
        for provider in ['mercadopago','openpay']:
            ready=configured(provider)
            self.stdout.write(provider+': '+('variables presentes' if ready else 'FALTAN variables o entorno incompatible'))
            if ready and options['remote']:
                try:
                    if provider=='mercadopago':mercadopago.account()
                    else:api('GET',openpay.endpoint()+'/charges?limit=1',auth=(settings.OPENPAY_PRIVATE_KEY,''),expect_list=True)
                except ValidationError as error:self.stdout.write('  Consulta API: '+ ' '.join(error.messages))
                else:self.stdout.write('  Consulta API autenticada: OK')
        self.stdout.write('Las variables presentes no prueban que el webhook esté registrado, que el remitente esté verificado ni que una compra funcione. Sigue la prueba de aceptación.')
