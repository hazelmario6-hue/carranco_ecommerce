# Carranco: verificación por correo, recibos y pasarelas

Actualización del 10 de noviembre de 2026. Conserva el diseño web, el modo del APK, la navegación inferior y el contador del carrito. Los cambios se ejecutan en Django: para estas funciones no necesitas volver a compilar el APK.

## Qué queda implementado

- **Registro:** crea una cuenta pendiente de activación, envía un enlace de un solo uso y exige confirmarlo antes de iniciar sesión. Vence a las 24 horas. Abrir el enlace muestra una pantalla; el botón Confirmar completa la activación para que un escáner de correo no consuma el enlace.
- **Usuarios existentes:** conservan su acceso. En Mi cuenta pueden verificar su correo; se exige antes de crear un pedido o iniciar un pago. No se activan automáticamente usuarios deshabilitados previamente por administración.
- **Reenvío:** espera de un minuto y máximo cinco solicitudes por cuenta cada hora. Solicitar otro enlace invalida el anterior. El formulario anónimo responde de forma genérica.
- **Recibo por correo:** se prepara al confirmar un pago aprobado con la API del proveedor y completar el pedido. Incluye productos, cantidades, precios de catálogo, importe confirmado, referencia, fecha y enlace privado al recibo. Los pagos de prueba se identifican como tales. Un pago pendiente, rechazado o un regreso del navegador no genera un recibo de compra.
- **Cola de envío:** un fallo del proveedor de correo deja el mensaje pendiente. El pago conserva su estado confirmado; el comando programado reintenta los mensajes. Una notificación de pago repetida no crea otro recibo ni descuenta stock otra vez.
- **Mercado Pago y Openpay:** conserva e integra los adaptadores existentes de checkout alojado y webhooks. Añade consulta del estado por pedido, separación de intentos de prueba/producción, selección únicamente de pasarelas configuradas y comprobación de correo verificado.

El recibo **no es una factura fiscal CFDI**. No incluye timbrado, XML ni integración con un PAC. No se agregó emisión fiscal. Los pedidos anteriores a esta actualización no reciben correos retrospectivos: no tienen la nueva copia del correo verificado del cliente.

**Estado de validación:** los flujos locales están probados con respuestas controladas de las APIs. No se recibieron credenciales del usuario, no se enviaron mensajes reales, no se registraron webhooks en sus cuentas y no se realizaron cobros. La activación externa termina con los pasos siguientes y la prueba de aceptación.

## 1. Actualizar el repositorio y Railway

1. Conserva una copia de la base de datos actual antes del despliegue.
2. Extrae el ZIP. Actualiza en `carranco_ecommerce` el contenido de `carranco_ecommerce-main/`, manteniendo las rutas. Sube los archivos extraídos, no el ZIP, y evita crear otra carpeta contenedora dentro del repositorio. No subas un `.env` real.
3. Conserva las variables de base de datos que ya funcionan en Railway. No cambies `DB_HOST` a localhost.
4. En el servicio Django conserva el Build Command:

   ```sh
   python manage.py collectstatic --noinput
   ```

5. Configura como Pre-deploy Command:

   ```sh
   python manage.py migrate --noinput
   ```

6. Conserva el Start Command:

   ```sh
   gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
   ```

7. Despliega la rama actualizada. Se añaden cuatro migraciones: `core/0002`, `cuentas/0002`, `pagos/0002` y `pedidos/0002`. Crean tablas de verificación y correos, y añaden campos a pedidos/pagos. No vacían productos ni usuarios.

Configura el correo antes de abrir el nuevo registro a otras personas. Mientras falte la configuración, las cuentas nuevas quedarán pendientes y sus mensajes esperarán en la cola.

## 2. Correo por HTTPS con Resend

Se usa la API HTTPS de Resend para funcionar también en Railway Trial/Free/Hobby, donde SMTP no está habilitado. En producción el backend de consola no envía mensajes.

1. Crea o abre tu cuenta en [Resend](https://resend.com/).
2. En Domains agrega un dominio que controles. Copia los registros DNS indicados por Resend en tu proveedor de dominio y espera a que aparezca verificado. El subdominio `up.railway.app` asignado a tu servicio no es un dominio cuyo DNS controles para configurar este remitente.
3. Crea una API key con permiso para enviar desde ese dominio. Guárdala en Railway → servicio `carranco_ecommerce` → Variables.
4. Usa como remitente una dirección de ese dominio verificado. `EMAIL_REPLY_TO` es opcional y debe ser una dirección atendida por ti.

| Variable en Django/Railway | Valor |
| --- | --- |
| `MAIL_PROVIDER` | `resend` |
| `RESEND_API_KEY` | Tu API key de Resend, pegada solo en Railway |
| `DEFAULT_FROM_EMAIL` | `Carranco <avisos@TU_DOMINIO_VERIFICADO>` |
| `EMAIL_REPLY_TO` | Tu dirección de contacto; opcional |
| `APP_URL` | `https://carrancoecommerce-production.up.railway.app` |
| `ALLOWED_HOSTS` | `carrancoecommerce-production.up.railway.app` |
| `CSRF_TRUSTED_ORIGINS` | `https://carrancoecommerce-production.up.railway.app` |
| `DEBUG` | `False` |
| `TRUST_PROXY_HTTPS` | Conserva `True` si ya funciona así detrás del proxy de Railway |

Sustituye el dominio si cambiaste la dirección pública. `ALLOWED_HOSTS` no lleva `https://`. Conserva `SECRET_KEY`; cambiarla puede invalidar sesiones y otros tokens de Django.

**Si aún no tienes dominio:** Resend permite probar con `Carranco <onboarding@resend.dev>`, pero ese remitente solo puede enviar al correo del propietario de la cuenta de Resend. Sirve para una prueba personal, no para verificar cuentas de varios compañeros. Para enviarles necesitas el dominio verificado.

Entra al contenedor del servicio Django por SSH y ejecuta, sustituyendo el destinatario por tu dirección:

```sh
/app/.venv/bin/python /app/manage.py check_integrations
/app/.venv/bin/python /app/manage.py send_test_email --to TU_CORREO
```

Estos comandos se ejecutan **dentro de Railway**, donde están las variables y la base correctas. En tu PowerShell primero entra con `railway.cmd ssh`. Si `python` no se encuentra dentro del contenedor, usa las rutas completas anteriores. Para salir usa `exit`.

El estado `enviado` significa que el proveedor aceptó el mensaje, no que haya llegado a la bandeja. Comprueba el correo, spam y el registro de Resend. El comando `send_test_email` sí envía un mensaje al destinatario que indiques.

Para desarrollo local puedes usar `MAIL_PROVIDER=console` con `DEBUG=True`: el enlace se imprime en la terminal y no sale ningún correo externo.

## 3. Reintentos de correo

El primer envío se intenta al guardar la cuenta o confirmar el pedido. Programa un servicio cron en el mismo proyecto/entorno de Railway, con este repositorio y las mismas variables de base de datos, URL y correo. No crees otra base para este servicio.

Start Command del servicio cron:

```sh
python manage.py send_pending_emails
```

Frecuencia: `*/5 * * * *` (cada cinco minutos). Este servicio ejecuta el comando y termina; no debe ejecutar Gunicorn. Conserva también la tarea existente `expire_reservations` para liberar reservas vencidas. Puedes ejecutar ambas tareas periódicas en un mismo servicio con:

```sh
sh -c 'python manage.py send_pending_emails && python manage.py expire_reservations'
```

El servicio cron necesita estar conectado a la misma base del servicio web y tener las variables resueltas en ese entorno. Las migraciones se aplican en el despliegue web antes de ejecutar la tarea.

Como superusuario, en `/admin/core/correopendiente/` (cola de correos) puedes consultar destinatario, estado, intentos y error resumido. Tras seis fallos, o una respuesta ambigua que supera la ventana segura de reintento del proveedor, el correo queda `fallido`: comprueba primero su entrega en Resend antes de reenviarlo manualmente. Los enlaces vencidos se cancelan. La falta de configuración deja el mensaje pendiente sin consumir intentos.

## 4. Mercado Pago: primero pruebas

Se utiliza Checkout Pro / API de Preferences, con captura de tarjeta en la pantalla de Mercado Pago. La cuenta del vendedor de prueba debe ser diferente de la del comprador de prueba.

1. Abre la aplicación correspondiente en [Mercado Pago Developers](https://www.mercadopago.com.mx/developers/).
2. Sigue la [guía oficial de compras de prueba](https://www.mercadopago.com.mx/developers/es/docs/checkout-pro-preferences/integration-test/test-purchases) para obtener vendedor, comprador y tarjetas de prueba. Usa las credenciales que esa guía indique para el vendedor de prueba de Checkout Pro; el prefijo del token por sí solo no identifica todos los casos.
3. Guarda en Railway `MP_ACCESS_TOKEN` del vendedor de prueba. Si usas un token `APP_USR` de una cuenta de prueba, el código comprueba que la API identifique a la cuenta como `test_user`.
4. En la configuración de Webhooks de esa aplicación/entorno registra el evento de pagos (`payment`) y esta URL:

   ```text
   https://carrancoecommerce-production.up.railway.app/pagos/webhook/mercadopago/
   ```

5. Guarda la clave secreta de firma del webhook en `MP_WEBHOOK_SECRET`. Es distinta del Access Token.
6. Si la compra de prueba necesita el correo del comprador de prueba, configura `MP_TEST_BUYER_EMAIL`. Tu cuenta de Carranco debe tener tu correo real verificado para recibir activación y recibos; el ajuste solo cambia el correo enviado al checkout de prueba de Mercado Pago.

| Variable | Para probar |
| --- | --- |
| `PAYMENTS_LIVE` | `False` |
| `ACADEMIC_MODE` | `True` |
| `MP_ACCESS_TOKEN` | Credencial del vendedor de prueba |
| `MP_WEBHOOK_SECRET` | Clave de firma del webhook de esa aplicación |
| `MP_TEST_BUYER_EMAIL` | Correo del comprador de prueba, si corresponde |
| `ACADEMIC_CHARGE_AMOUNT` | Vacío para usar precios académicos por producto, o un importe fijo explícito admitido por tu cuenta y dentro del límite |
| `ACADEMIC_MAX_CHARGE` | Conserva `100.00` |

Consulta desde el contenedor, después de configurar las variables:

```sh
/app/.venv/bin/python /app/manage.py check_integrations --remote
```

`--remote` hace consultas GET autenticadas; no crea pagos ni envía correos. Un resultado OK confirma acceso a la API, no la recepción del webhook ni una compra completa.

Realiza la compra de prueba desde una cuenta de Carranco verificada. En el pedido pulsa **Pagar con mercadopago**, completa el checkout con los datos de prueba del proveedor y regresa al pedido. Si la notificación tarda, pulsa **Consultar pago con la pasarela**. Se consulta la API y se verifican referencia, importe, moneda y entorno; los parámetros de regreso del navegador no aprueban el pago.

## 5. Openpay México: sandbox

Openpay es una integración independiente: necesita su propia cuenta y credenciales. La cuenta debe tener habilitado el checkout alojado/redirección.

| Variable | Para probar |
| --- | --- |
| `OPENPAY_MERCHANT_ID` | ID del comercio sandbox |
| `OPENPAY_PRIVATE_KEY` | Llave privada sandbox |
| `OPENPAY_PRODUCTION` | `False` |
| `OPENPAY_WEBHOOK_USER` | Usuario que defines para autenticar notificaciones |
| `OPENPAY_WEBHOOK_PASSWORD` | Contraseña larga y exclusiva definida por ti |
| `PAYMENTS_LIVE` | `False`, debe coincidir con el entorno de Openpay |

No se necesita llave pública: los datos de tarjeta se introducen en el checkout alojado. El código crea el cargo con `confirm=false` y utiliza la URL devuelta por Openpay.

1. Configura esas variables en el servicio Django y despliega.
2. En Openpay configura un webhook hacia:

   ```text
   https://carrancoecommerce-production.up.railway.app/pagos/webhook/openpay/
   ```

3. Configura su autenticación HTTP Basic con el mismo usuario y contraseña de las variables. No incrustes la contraseña en la URL.
4. Openpay enviará un evento de verificación. Entra como superusuario a `/admin/pagos/verificacionopenpay/` y copia el código recibido para completar la verificación en Openpay.
5. Habilita las notificaciones de cargos correspondientes. El receptor procesa `charge.succeeded`, `charge.failed`, `charge.cancelled` y `charge.refunded`, y consulta el cargo con la API antes de actualizar el pedido.
6. Ejecuta `check_integrations --remote` y una compra sandbox con los datos de prueba de la [documentación oficial](https://documents.openpay.mx/docs/api/index.html). Prueba también un rechazo.

Carranco envía el recibo cuando confirma el pedido. Se deja `send_email=false` en la creación del cargo de Openpay para que no haya un segundo envío desde ese flujo de Openpay.

## 6. Prueba de aceptación antes de presentar la app

1. Registra una cuenta con una dirección que recibas. Antes de confirmar no debe permitir iniciar sesión.
2. Abre el correo. Solo abrir el enlace no activa la cuenta: pulsa **Confirmar mi correo**. El mismo enlace no debe volver a funcionar.
3. Regresa al APK e inicia sesión allí. El navegador que abrió el correo y el WebView pueden tener sesiones distintas; la cuenta verificada sí es la misma.
4. Completa perfil y dirección. Agrega productos: comprueba el contador del carrito y las cantidades.
5. Elige una pasarela configurada, acepta el resumen e importe, crea el pedido pendiente y pulsa Pagar. Prueba una pasarela por vez.
6. Comprueba un pago aprobado y otro rechazado. Solo el aprobado debe completar el pedido, descontar stock una vez y generar un recibo.
7. Verifica que el importe confirmado del recibo coincide con el de la pasarela. El total de catálogo puede ser distinto porque se conserva el modo académico de importes reducidos.
8. Reenvía la notificación desde el proveedor o vuelve a consultar: el pedido no debe descontar stock ni enviar un segundo recibo.
9. Comprueba que el recibo solo se puede abrir con la cuenta propietaria y que una cuenta distinta recibe 404.
10. Confirma la entrega del correo de recibo en la bandeja o en spam y revisa su estado en Resend.

En caso de timeout al iniciar el pago, el intento se conserva para revisión y se evita repetir a ciegas la creación del cargo. Consulta su estado y revisa el panel de la pasarela antes de crear otro pedido. Los pagos tardíos de reservas liberadas o pedidos cancelados quedan en revisión y no producen un recibo de compra completada automáticamente.

## 7. Cobros reales, cuando ambas pruebas hayan terminado

Esta entrega conserva el alcance académico y el límite de importe ya existentes. No cambia a ventas por el precio completo del catálogo.

Para activar dinero real, usa credenciales productivas del vendedor, firma webhook del entorno correspondiente, `PAYMENTS_LIVE=True`, `DEBUG=False`, HTTPS y `ACADEMIC_MODE=True`. Para Openpay usa también `OPENPAY_PRODUCTION=True` y sus credenciales productivas. Conserva un importe académico explícito, visible y dentro de `ACADEMIC_MAX_CHARGE`.

`PAYMENTS_LIVE` afecta a las dos pasarelas: no mezcles Mercado Pago productivo con Openpay sandbox en ese despliegue. Deshabilita la pasarela cuyas variables no estén listas. No reutilices pedidos/intentos de prueba para producción; utiliza pedidos nuevos. Deja vacío `MP_TEST_BUYER_EMAIL` en producción. No elimines la validación de entorno o importe para hacer pasar un pago.

## Archivos y comprobación local

Se añaden cuatro migraciones, servicios de verificación/cola/recibos, plantillas de cuenta y correo, página de recibo, consulta de pago y tres comandos: `check_integrations`, `send_test_email` y `send_pending_emails`. `.env.example` incluye los nombres nuevos sin credenciales.

La validación de esta entrega usa Python 3.12, Django 5.2.18 y una base SQLite temporal independiente. Pasaron 97 pruebas: 28 nuevas de correo/pagos, 7 de modo app y 62 de regresión del comercio. `check` y `makemigrations --check --dry-run` no reportaron problemas. Se probaron migraciones nuevas sobre la base temporal. Las plantillas nuevas renderizaron en esas pruebas. La comprobación visual en Chromium no pudo completarse porque este entorno bloqueó el inicio del navegador; revisa las pantallas nuevas en tu teléfono después del despliegue.

No se ejecutaron en esta entrega los dos casos específicos de MySQL (motor y concurrencia sobre la última unidad). Tampoco se probaron cuentas reales, entrega real de mensajes, recepción de webhooks desde internet ni teléfonos físicos. La suite original de MySQL sigue disponible en `apps/core/tests.py`; ejecútala contra una base de pruebas separada, nunca contra la base productiva.

## Referencias

- [Railway: conexiones salientes y SMTP](https://docs.railway.com/networking/outbound-networking)
- [Resend: enviar correo por API](https://resend.com/docs/api-reference/emails/send-email)
- [Resend: restricción del dominio de prueba](https://resend.com/docs/knowledge-base/403-error-resend-dev-domain)
- [Mercado Pago: pruebas de Checkout Pro](https://www.mercadopago.com.mx/developers/es/docs/checkout-pro-preferences/integration-test/test-purchases)
- [Mercado Pago: Webhooks](https://www.mercadopago.com.mx/developers/es/docs/your-integrations/notifications/webhooks)
- [Openpay México: API](https://documents.openpay.mx/docs/api/index.html)
