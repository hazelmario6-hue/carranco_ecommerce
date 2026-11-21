# Actualización Carranco — 20 de noviembre de 2026

## Qué cambia

- Mercado Pago es la única pasarela para pedidos nuevos. Openpay no aparece en checkout, ayuda ni diagnóstico y no puede reactivarse solo agregando credenciales.
- El navegador normal recupera la interfaz web. El APK usa el modo app por su User-Agent; `?modo=app` solo previsualiza la página solicitada. Se elimina la cookie antigua que dejaba la vista app pegada al navegador.
- Las pantallas usan altura flexible y espacio para la navegación y las zonas seguras. Se ajustó el viewport del APK 1.2.
- El carrito actualiza cantidades, importes y contador sin recargar; agrupa clics durante 300 ms, limita al stock y espera la respuesta del servidor. Los pedidos siguen comprobando y reservando stock en el servidor.
- Las promociones se administran desde `/dashboard/promociones/` y se muestran desde una misma fuente en web y app, con fechas y orden.
- Las cuentas activas con `is_staff=True` entran al dashboard con diseño web. Dentro del APK permanece el mismo WebView para conservar la sesión; al salir vuelve la presentación de cliente.
- Redes sociales y WhatsApp usan las siete direcciones proporcionadas, con nombres accesibles y enlaces externos. Se presentan como redes del proyecto.
- Las imágenes tienen descripciones concretas. Los textos genéricos antiguos de las galerías se normalizan al mostrarse; se conservan los textos específicos que se hubieran editado.

El registro con PIN, los recibos y el cobro del total de catálogo más envío continúan con su configuración existente. Esta actualización no realiza compras ni envía correos al instalarse.

## Archivos del paquete completo

- `carranco_ecommerce-main/`: proyecto Django actualizado.
- `carranco-android/`: fuente Android 1.2, versionCode 3.
- `Carranco-1.2.apk`: APK de depuración compilado y con firma verificada.
- `APLICAR_ACTUALIZACION.ps1`: actualización controlada de los dos repositorios locales.
- `cambios.json`: archivos modificados y sus hashes antes/después.
- `LEEME_PRIMERO.md`: comandos para Windows y pasos de despliegue.

## Subir a GitHub

Usa el script de la raíz del paquete. Comprueba la rama `main`, los cambios preparados y las versiones de los archivos antes de copiar; conserva un respaldo de los archivos que reemplaza. Solo prepara para el commit los archivos incluidos en el manifiesto. No copia `.env`, `.git`, bases de datos, credenciales, archivos subidos ni carpetas de compilación.

Si hay modificaciones diferentes de la base o de esta actualización, se detiene antes de copiar. No uses `git reset --hard` ni `push --force` para resolverlo: compara el archivo indicado. Con `-Publicar`, además comprueba si hay commits nuevos en GitHub, crea los commits y hace un push normal. Si un push falla por autenticación, los cambios y el commit quedan en tu carpeta; vuelve a autenticar y realiza el push.

## Railway: migraciones y configuración

Antes de activar esta versión, confirma que el servicio Django ejecuta `python manage.py migrate --noinput` como comando de predespliegue. Ahora se necesitan `core.0003_promocion` y `core.0004_promocion_inicial`. La segunda crea la promoción del dúo si ese producto ya existe, sin cambiar sus precios ni existencias. Las migraciones se incluyen en el paquete: no ejecutes `makemigrations` en producción.

Conserva el paso `python manage.py collectstatic --noinput` que ya utiliza tu despliegue. Los recursos de esta actualización llevan una nueva versión para renovar la caché.

En Variables de Railway:

- Conserva `PAYMENTS_LIVE=True`, `DEBUG=False`, tus variables de Mercado Pago y la URL HTTPS.
- Conserva `MAIL_PROVIDER=resend`, `RESEND_API_KEY` y el remitente de tu dominio verificado **servicioslnformaticos.it.com** (la letra después de “servicios” es una ele minúscula).
- Elimina o deja vacíos `OPENPAY_MERCHANT_ID`, `OPENPAY_PRIVATE_KEY`, `OPENPAY_WEBHOOK_USER` y `OPENPAY_WEBHOOK_PASSWORD`; elimina `OPENPAY_PRODUCTION` o déjalo en `False`. Estas variables no se modificaron desde este paquete.
- No pegues el archivo `.env.example` sobre las variables reales: sus valores son ejemplos para desarrollo.

Para revisar el despliegue, abre PowerShell en el repositorio Django y entra al servicio:

```powershell
railway.cmd ssh
```

Cuando el prompt cambie a `root@…:/app#`, ejecuta **dentro de Railway**, no en PowerShell local:

```bash
/app/.venv/bin/python /app/manage.py migrate --noinput
/app/.venv/bin/python /app/manage.py seed_promotions
/app/.venv/bin/python /app/manage.py check_integrations --remote
exit
```

`seed_promotions` no duplica la promoción ni sobrescribe ediciones del administrador. El diagnóstico consulta la API de Mercado Pago por GET; no cobra ni manda correo. Revisa en Railway que el despliegue activo corresponda al commit que acabas de subir.

## Publicar una promoción

1. Entra como administrador a `/dashboard/promociones/` y pulsa **Nueva promoción**.
2. Completa título, descripción y descripción accesible de la imagen.
3. Vincula un producto para usar su foto, precio actual y destino. También puedes indicar una URL HTTPS de imagen y un enlace propio.
4. Define inicio y fin en hora de Ciudad de México, o déjalos vacíos para no limitar ese extremo. El fin debe ser posterior al inicio.
5. Activa la promoción, asigna el orden y guarda. Las vencidas, futuras, inactivas o asociadas a productos no disponibles se ocultan automáticamente.

Los superusuarios ya tienen acceso. Para personal con permisos limitados, agrega desde Django Admin los permisos `core.view_promocion`, `core.add_promocion` y `core.change_promocion` al usuario o grupo que administra promociones; no es necesario darle permisos de superusuario. Reejecutar `create_carranco_groups` también actualiza los grupos predeterminados, pero vuelve a asignar su conjunto estándar de permisos.

Una promoción muestra el precio vigente del producto; editar el banner no crea un descuento independiente ni cambia el importe a cobrar. Para cambiar ese precio, usa la edición de productos.

## Android y redes sociales

Sube los cambios de `carranco-android/` al segundo repositorio. En GitHub: **Actions → Generar APK Carranco → Run workflow**, rama `main`. Al finalizar, descarga el artefacto **Quesos-Carranco-Android**. También puedes probar el `Carranco-1.2.apk` incluido, después de desplegar Django.

El APK incluido es para instalación y pruebas, con una firma de depuración de esta compilación. Si Android informa que entra en conflicto con la aplicación instalada, la firma anterior es diferente: usa una compilación firmada con la misma clave anterior para actualizarla. Si decides desinstalar la copia antigua para instalar esta, perderás la sesión y los datos locales de esa app, aunque la cuenta y los pedidos seguirán en el servidor. No es un paquete firmado para publicar en Play Store.

Los enlaces externos se entregan a Android para abrir la aplicación correspondiente o el navegador. WhatsApp no envía mensajes automáticamente. Falta confirmar la apertura con las apps instaladas en un teléfono físico; la compilación no sustituye esa prueba.

## Prueba final en tu despliegue

1. Abre la URL normal en navegador: deben aparecer encabezado y pie web, sin barra inferior app.
2. Abre `/?modo=app` y luego la URL normal: la segunda debe volver a web. En el APK, navega entre varias páginas: deben permanecer en modo app.
3. Comprueba inicio, cuenta, carrito y checkout en un teléfono estrecho, uno largo y en horizontal; abre el teclado y desplázate hasta el último botón.
4. Con stock conocido, pulsa rápidamente `+` en el carrito: debe detenerse en el máximo, actualizar una vez tras la pausa y conservar subtotales y envío correctos.
5. Publica una promoción y comprueba ambos inicios; desactívala y verifica que desaparezca. Inicia sesión como administrador desde el APK y luego cierra sesión para comprobar ambos roles.
6. Abre cada red y WhatsApp. Verifica también las fotografías externas desde tu red.
7. Comprueba que checkout solo muestra Mercado Pago. Para revisar el registro y el recibo, usa tu cuenta y el flujo existente; cualquier pago completado con `PAYMENTS_LIVE=True` cobra el importe real mostrado.

Resultado de pruebas locales y límites: `docs/VERIFICACION_2026-11-20.md`.
