# Carranco · identidad móvil y correo con PIN

Esta actualización parte del commit `75c3e8a` de `hazelmario6-hue/carranco_ecommerce`.
Reemplaza las instrucciones anteriores sobre el registro mediante enlace por el flujo con PIN que se describe aquí. El dominio correcto tiene una **l minúscula** después de servicios: `servicioslnformaticos.it.com`.

## Qué cambia

- App: logo original local, azul marino `#0D1B2A`, crema `#F2E6CF`, dorado `#C9A24B` e ivory `#FBF7EF`, tomados de `static/css/styles.css`. Tipografías Montserrat y Cormorant Garamond.
- Inicio móvil con foto real de molletes con queso Carranco, logo, Comprar quesos, búsqueda, carrusel de destacados y bloque de historia.
- Menú lateral con nombre visible, cierre por botón/Escape, foco y enlaces de ayuda; cerrar sesión solo por POST.
- Catálogo en dos columnas; Ver detalles y botón de carrito; confirmación con el nombre del producto y contador actualizado.
- Barra inferior compacta con área segura; ajustes de títulos, formularios y espaciado.
- Web y app: registro en `/cuenta/registro/`, primero datos y después PIN en la misma dirección y tarjeta.
- Campos: nombre, usuario, correo y contraseña dos veces. Usuarios existentes conservan sus credenciales y pueden iniciar sesión por usuario o correo.
- PIN aleatorio de seis dígitos, 10 minutos, máximo cinco intentos por PIN, 60 segundos entre envíos y cinco envíos por hora por cuenta. Cambiar el correo no reinicia esos límites.
- Se guarda un hash con sal. El PIN y su correo se construyen en memoria; no se persisten en la cola de correos. Si el proveedor falla, se informa en pantalla y se puede solicitar otro código al terminar el contador.
- La cuenta nueva queda inactiva hasta verificar. Verificar inicia sesión conservando el carrito. Un usuario pendiente puede retomar desde Iniciar sesión con su contraseña correcta; una cuenta deshabilitada administrativamente no se activa por este flujo.
- Los enlaces antiguos ya enviados conservan su validación hasta caducar, salvo que se solicite un PIN nuevo. Los nuevos registros siempre usan PIN.
- Cuentas existentes sin correo verificado siguen accediendo al perfil y verifican en el mismo formulario antes de comprar.
- Recibo HTML y texto por correo al confirmar el pago desde la pasarela; importe real confirmado y distinción de prueba. Evita duplicados y conserva la cola de reintentos para recibos. El recibo no es una factura fiscal CFDI.

## Actualizar sin perder la base ni las variables

1. En la carpeta local del repositorio Django, ejecuta `git status` y guarda tus cambios antes de actualizar.
2. Sin cambios pendientes, ejecuta `git pull --ff-only origin main`. Si hay divergencia, no uses force: revisa los cambios antes de integrar.
3. Copia el contenido de `actualizacion/` del ZIP sobre esa carpeta. Son solo archivos modificados/nuevos. No incluye `.env`, `.git`, bases, catálogo ni credenciales. Se incluye también `fuente-completa/` como referencia, sin esos datos.
4. Revisa `git diff`. Si modificaste `config/settings.py` desde el commit base, conserva tus ajustes al integrar; nunca sustituyas variables de Railway por valores de localhost.
5. Ejecuta:

```powershell
git add .
git commit -m "Recuperar identidad Carranco y registro con PIN"
git push origin main
```

No hace falta modificar el repositorio Android ni generar otro APK: el APK actual identifica el modo app y carga el frontend de Railway.

## Variables de Railway: servicio Django

```env
MAIL_PROVIDER=resend
RESEND_API_KEY=TU_CLAVE_PRIVADA_DE_RESEND
DEFAULT_FROM_EMAIL=Quesos Carranco <no-reply@servicioslnformaticos.it.com>
APP_URL=https://carrancoecommerce-production.up.railway.app
TRUST_PROXY_HTTPS=True
DEBUG=False
```

Introduce el valor real de la clave únicamente en Railway. `EMAIL_REPLY_TO` es opcional y debe ser un correo que puedas recibir; Resend no crea una bandeja de entrada al verificar el dominio. Conserva tus valores actuales de `SECRET_KEY`, `DB_*`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` y pasarelas.

El valor de `DEFAULT_FROM_EMAIL` de Railway tiene prioridad sobre el predeterminado del código: corrígelo allí si todavía tiene el dominio anterior.

- Build: `python manage.py collectstatic --noinput`
- Pre-deploy: `python manage.py migrate --noinput`
- Start: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`

Se añade la migración `cuentas.0003`; no elimina tablas ni registros.
Confirma que Railway desplegó el nuevo commit (Deploy Latest Commit si el automático no se ejecutó).

## Probar el correo

En PowerShell, dentro del repositorio vinculado a Railway:

```powershell
railway.cmd ssh
```

Dentro del contenedor, utiliza el Python del entorno (el comando `python` puede no estar en el PATH):

```sh
/app/.venv/bin/python manage.py check_integrations
/app/.venv/bin/python manage.py send_test_email --to TU_CORREO_REAL
```

Sustituye `TU_CORREO_REAL`. Revisa Resend → Emails y tu bandeja/spam. “enviado” significa aceptado por el proveedor, no confirma llegada a la bandeja. Los errores muestran el código HTTP sin claves ni el cuerpo del correo.

Para reintentar recibos pendientes:

```sh
/app/.venv/bin/python manage.py send_pending_emails --limit 50
```

Para automatizar los reintentos, configura un servicio cron de Railway cada cinco minutos (`*/5 * * * *`) con el mismo código, variables y base de datos; su comando de inicio debe ejecutar `python manage.py send_pending_emails --limit 50` y terminar. No reemplace el inicio del servicio web por este comando.
Los PIN fallidos se reenvían desde el registro; no se almacenan para reintento automático.

## Prueba de aceptación en Railway

1. Web: abre `/?modo=web`; registra un usuario nuevo, recibe el PIN e introdúcelo sin abandonar el registro.
2. App: abre `/?modo=app` o el APK y repite con otro correo. Verifica el menú lateral, logo y colores.
3. Introduce un PIN incorrecto, uno vencido y un PIN anterior a un reenvío: deben fallar. Después de cinco errores ese código no se acepta.
4. Comprueba reenvío, cambiar correo, recargar el registro y retomar desde login. Comprueba que una cuenta existente sigue entrando por correo.
5. Agrega un producto y observa el aviso y contador. El carrito debe conservarse al verificar e iniciar sesión.
6. En sandbox, confirma un pago con las credenciales de prueba de tu pasarela. Revisa que llega un recibo y que una notificación duplicada no envía otro. Pagos pendientes/rechazados no generan recibo.
7. Revisa la cuenta: perfil, direcciones, pedidos y cerrar sesión. Acerca de contiene el aviso académico reducido.
8. En dispositivos reales prueba teclado, pegado/autocompletado del PIN, botón atrás, menú y barra inferior. Anchos objetivo: 360, 393 y 412 px.

No se modificaron credenciales ni se habilitaron cobros reales. Verificar Resend no configura Mercado Pago/Openpay: sus variables y webhooks se administran por separado.

## Validación local realizada

- Pruebas automatizadas Django en BD SQLite aislada: 105 pruebas, 103 aprobadas y 2 omitidas por requerir MySQL/bloqueos de filas.
- Comprobaciones Django, migraciones consistentes y collectstatic.
- Sintaxis JavaScript y diferencias Git sin errores de formato.
- Pruebas de Resend con transporte simulado y correos locales; sin enviar a terceros.
- La revisión visual en navegador y en dispositivos físicos sigue pendiente: el navegador de este entorno no pudo acceder al servidor local. No se ha publicado ni probado la entrega real desde Railway.

Para repetir la suite sin tocar MySQL de producción:

```sh
python manage.py test apps.cuentas apps.core --settings=config.test_settings
```

Las pruebas de concurrencia necesitan un MySQL de pruebas separado. No apuntar los tests a la base de producción.
