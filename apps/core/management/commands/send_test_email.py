import uuid
from django.core.management.base import BaseCommand,CommandError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.utils.html import escape
from apps.core.correos import queue_email,configured
class Command(BaseCommand):
    help='Envía un correo de prueba al destinatario indicado explícitamente.'
    def add_arguments(self,parser):parser.add_argument('--to',required=True)
    def handle(self,*args,**options):
        try:validate_email(options['to'])
        except ValidationError:raise CommandError('Dirección de correo no válida.')
        if not configured():raise CommandError('Configura primero MAIL_PROVIDER, RESEND_API_KEY y DEFAULT_FROM_EMAIL.')
        text='Prueba de correo de Carranco. Este mensaje no registra una compra ni realiza un cobro.'
        row=queue_email('test:'+str(uuid.uuid4()),options['to'],'Prueba de correo · Carranco',text,'<p>'+escape(text)+'</p>')
        row.refresh_from_db()
        self.stdout.write(f'Correo {row.pk}: {row.estado}. Aceptado por el proveedor no significa entregado en la bandeja; revisa también spam.')
