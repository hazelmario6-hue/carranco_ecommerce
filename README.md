# Quesos Carranco — e-commerce académico con Django y MySQL

**PROYECTO ACADÉMICO · SITIO NO OFICIAL**

Proyecto Django ejecutable con `python manage.py runserver`. Mantiene la interfaz de las tres entregas anteriores y completa cuentas, carrito, checkout, pedidos y administración. Las integraciones de Mercado Pago y Openpay están implementadas y requieren tus credenciales y un webhook HTTPS antes de efectuar operaciones externas. Apple Pay permanece oculto.

## Qué incluye

- Django 5.2.18 LTS, Django Authentication, Sessions, Forms, Messages y ORM.
- MySQL 8 con `mysqlclient`; no utiliza SQLite ni XAMPP.
- Inicio, catálogo, detalle, búsqueda dinámica, categorías, galería y relacionados.
- Los tres CSS anteriores idénticos: paleta, fuentes, navbar, footer y fotografías conservados.
- Registro de clientes con contraseña validada, login, bloqueo tras cinco fallos, logout POST, perfil y direcciones.
- Carrito en sesión Django, validación de stock, IDs/cantidades del carrito local anterior importados una sola vez.
- Checkout que recalcula los importes en el servidor y exige aceptar un resumen firmado. Si cambian los precios, se exige revisar el nuevo monto.
- Pedidos con número de backend CARR-000001, snapshots de productos y dirección, historial y seguimiento.
- Reservas transaccionales con bloqueo de filas; un pago aprobado descuenta inventario una sola vez.
- Mercado Pago Checkout Pro y Openpay con formulario alojado: la tarjeta se captura en la pasarela, nunca en Django.
- Webhooks separados, firma HMAC para Mercado Pago, HTTP Basic para Openpay y consulta a la API antes de confirmar.
- Django Admin y dashboard personalizado: productos, precios, imágenes, baja lógica, inventario auditado, pedidos, estados, clientes, reportes y CSV.
- Contacto persistido en MySQL, Nosotros, FAQ y asistente WhatsApp de demostración.

Las pantallas de cliente y dashboard extienden `templates/base.html`. Las páginas del dashboard utilizan `templates/dashboard/base.html`. Django Admin conserva su interfaz propia con los colores Carranco.

## Estructura

```text
carranco_ecommerce/
    manage.py
    requirements.txt
    .env.example
    README.md
    config/         settings.py, urls.py, asgi.py, wsgi.py
    apps/
        core/       contacto, auditoría y páginas generales
        catalogo/   categorías, productos, carga inicial y copia de productos previos
        carrito/    sesión, validaciones y transferencia del carrito anterior
        cuentas/    formularios de Django, perfil, direcciones e intentos de login
        pedidos/    checkout, pedidos, inventario, reservas e historial
        pagos/      modelos, webhooks y servicios separados de pasarela
        dashboard/  gestión, permisos, reportes y exportación
    templates/      base, core, catalogo, carrito, cuentas, pedidos, dashboard, admin
    static/         css, js y recursos del frontend
    media/          productos subidos; se crea al cargar imágenes
    docs/           análisis, mapa de archivos y verificación
```

Las migraciones iniciales ya vienen incluidas. No es necesario generarlas al instalar. `makemigrations` se utiliza solo si posteriormente cambias modelos.

## Instalación exacta en Windows

### 1. Abre la carpeta

Extrae el ZIP y abre PowerShell dentro de `carranco_ecommerce`, donde está `manage.py`. Necesitas Python 3.12 o 3.13 y MySQL 8 iniciado. La versión comprobada fue Python 3.12.14 con MySQL 8.0.46. Node.js no es necesario para ejecutar esta entrega.

```powershell
py --version
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Estos comandos usan directamente el Python del entorno y funcionan sin cambiar la política de ejecución de PowerShell. Opcionalmente puedes activar `.venv` con `.\.venv\Scripts\Activate.ps1` y después utilizar `python`.

Si `mysqlclient` intenta compilar, usa Python 3.12/3.13 de 64 bits y una versión de pip actualizada para obtener la rueda Windows. No sustituyas el motor por SQLite.

### 2. Crea una base separada

En MySQL Workbench, conectado con tu cuenta de configuración, ejecuta lo siguiente después de sustituir `TU_CLAVE_LOCAL`:

```sql
CREATE DATABASE IF NOT EXISTS carranco_django
CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

CREATE USER 'carranco_app'@'127.0.0.1'
IDENTIFIED BY 'TU_CLAVE_LOCAL';

GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES
ON carranco_django.* TO 'carranco_app'@'127.0.0.1';
```

Si el usuario ya existe, omite `CREATE USER` y conserva su contraseña. Si utilizas otro nombre de base o usuario, cámbialo en SQL y `.env`. Los permisos DDL son para instalar las migraciones; después pueden retirarse del usuario que atiende la web y utilizarse con una cuenta separada de despliegue.

La base `carranco_ecommerce` de las entregas anteriores no se elimina ni se altera. Las tablas de negocio de Django tienen el prefijo `cc_`. Consulta `docs/ANALISIS_Y_ARCHIVOS.md` antes de trasladar datos anteriores.

### 3. Crea `.env`

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

Completa:

```env
DEBUG=True
SECRET_KEY=
DB_NAME=carranco_django
DB_USER=carranco_app
DB_PASSWORD="TU_CLAVE_LOCAL"
DB_HOST=127.0.0.1
DB_PORT=3306
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
APP_URL=http://localhost:8000
ACADEMIC_MODE=True
ACADEMIC_CHARGE_AMOUNT=
ACADEMIC_MAX_CHARGE=100.00
PAYMENTS_LIVE=False
```

Genera tu SECRET_KEY:

```powershell
.\.venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copia el resultado entre comillas en `SECRET_KEY="..."`. Usa comillas para claves que contienen `#` o espacios. No hay secretos ni contraseñas compartidos en el proyecto.

### 4. Migra y carga el catálogo

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_carranco
.\.venv\Scripts\python.exe manage.py create_carranco_groups
```

El seed carga cinco categorías, ocho productos de catálogo y el dúo del inicio, con stock académico. Repetirlo no sobrescribe productos, precios ni stock existentes.

Para copiar los productos de tu base anterior, realiza la copia **antes del seed**. Concede SELECT sobre la base origen a la cuenta configurada y ejecuta:

```powershell
.\.venv\Scripts\python.exe manage.py import_legacy_products --database carranco_ecommerce
.\.venv\Scripts\python.exe manage.py seed_carranco
```

El comando no escribe en la base origen y rechaza pedidos o reservas previos que requieren revisar el historial. No reutiliza hashes de clientes de otro sistema ni afirma trasladar pedidos financieros que no fueron verificados.

### 5. Crea administrador e inicia

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py runserver
```

Introduce usuario, correo y una contraseña propia; no se entrega una cuenta predeterminada.

Abre:

- http://localhost:8000/ — inicio.
- http://localhost:8000/productos/ — catálogo.
- http://localhost:8000/productos/queso-ranchero/ — detalle.
- http://localhost:8000/carrito/ — carrito.
- http://localhost:8000/cuenta/registro/ — registro.
- http://localhost:8000/checkout/ — checkout, requiere cuenta y selección.
- http://localhost:8000/mis-pedidos/ — historial propio.
- http://localhost:8000/dashboard/ — panel personalizado.
- http://localhost:8000/admin/ — Django Admin.

Mantén la consola abierta. Ctrl+C detiene el servidor. En próximas ejecuciones basta con iniciar MySQL y ejecutar `manage.py runserver` con el Python del entorno.

## Probar sin credenciales de pago

1. Registra una cuenta de cliente.
2. Guarda una dirección desde Mi cuenta.
3. Agrega productos y prueba cantidades, eliminación y vaciado.
4. En checkout revisa los dos importes y acepta el aviso académico.
5. Crea un pedido pendiente. Su stock queda reservado, no vendido.
6. Consulta Mis pedidos y su seguimiento.
7. Cancela un pedido pendiente y comprueba que la reserva se libera.
8. Entra como superusuario al dashboard para revisar productos, inventario, clientes y pedidos.

Sin credenciales y webhook HTTPS, la web no muestra un botón que finja cobrar. La confirmación no cambia a aprobado por parámetros enviados desde el navegador. Los estados aprobados se prueban automáticamente con respuestas de proveedor controladas; no se incluyen rutas públicas de simulación ni un botón administrativo para marcar un pago aprobado.

## Precios y consentimiento

`precio_catalogo` se utiliza para el total comercial, con envío ilustrativo de $79.00, gratuito desde $500.00. Ese envío no se añade al cobro académico.

Con `ACADEMIC_CHARGE_AMOUNT` vacío, el cobro académico suma `precio_academico` por unidad. El seed conserva $2.00 por unidad de la entrega anterior. Puedes configurar un importe fijo con `ACADEMIC_CHARGE_AMOUNT`, por ejemplo `10.00`; el checkout lo muestra antes de aceptarlo. El límite `ACADEMIC_MAX_CHARGE` evita operaciones superiores al monto configurado. Comprueba los mínimos que admite tu cuenta de pasarela: el código nunca aumenta silenciosamente el importe para cumplirlos.

El resumen está firmado, dura 15 minutos y depende del usuario, SKU, cantidades y precios. La aceptación se registra en el pedido. No se toman precios ni totales del frontend.

## Mercado Pago

### Qué necesitas y dónde obtenerlo

| Dato | Dónde se obtiene | Variable |
| --- | --- | --- |
| Access Token del entorno elegido | Mercado Pago Developers → Tus integraciones → tu aplicación → Credenciales | MP_ACCESS_TOKEN |
| Firma secreta de notificaciones | Tu aplicación → Webhooks → Configurar notificaciones | MP_WEBHOOK_SECRET |
| URL pública HTTPS | Dominio del despliegue o túnel de desarrollo HTTPS | APP_URL |

Se usa Checkout Pro mediante la API REST oficial. No se necesita Public Key porque no hay SDK ni captura de tarjeta en el navegador. Los formularios alojados permiten los medios habilitados en tu cuenta, incluidos tarjetas. La aplicación excluye ticket/ATM para evitar medios diferidos con reservas cortas.

### Prueba externa

1. Obtén las credenciales y cuentas de prueba que indique tu integración de Checkout Pro. Utiliza tarjetas y compradores de prueba de la documentación oficial.
2. Configura un dominio o túnel HTTPS hacia el servidor local. No pegues secretos en el chat.
3. Define `APP_URL=https://TU_DOMINIO`, añade ese host a `ALLOWED_HOSTS` y añade su origen HTTPS a `CSRF_TRUSTED_ORIGINS`.
4. Mantén `PAYMENTS_LIVE=False` y completa `MP_ACCESS_TOKEN` y `MP_WEBHOOK_SECRET`.
5. En Mercado Pago configura el evento Payments (`payment`) y la URL `https://TU_DOMINIO/pagos/webhook/mercadopago/` en el entorno de esa cuenta.
6. Reinicia Django. Crea el pedido, revisa el monto y pulsa Pagar con Mercado Pago.
7. El navegador irá al checkout de Mercado Pago. Después de regresar, consulta el estado: solo cambia al verificar el pago desde la API.
8. Prueba aprobados, pendientes y rechazados; verifica en el dashboard pagos y movimientos. Reenvía una notificación desde el panel del proveedor y comprueba que no se descuenta stock dos veces.

El código consulta `/users/me` al crear la preferencia y evita utilizar credenciales de vendedor real mientras `PAYMENTS_LIVE=False`, salvo credenciales TEST del proveedor. Para las cuentas de prueba con Access Token APP_USR exige la etiqueta `test_user`. Al consultar un pago verifica que `live_mode` corresponda al entorno.

### Cobros reales reducidos

Cuando la integración externa haya pasado sus pruebas y tu cuenta admita el método, configura credenciales productivas, `PAYMENTS_LIVE=True`, `DEBUG=False` y HTTPS. Las cookies serán Secure y se exigirá HTTPS. Conserva `ACADEMIC_MODE=True`, el importe reducido, el límite de cobro y el consentimiento visible. El código rechaza cobros reales con DEBUG activado.

Si HTTPS termina en un proxy de confianza, configura `TRUST_PROXY_HTTPS=True` únicamente cuando ese proxy elimine o reescriba `X-Forwarded-Proto` y el backend no sea accesible directamente. De lo contrario usa False y HTTPS hasta la aplicación. Para un despliegue compartido utiliza un servidor WSGI/ASGI y configura static/media; `runserver` corresponde a desarrollo.

No se efectuó ningún cargo real durante la construcción del proyecto. La prueba con tus cuentas es un paso pendiente y no puede reemplazarse con los tests locales.

## Openpay México

El servicio separado usa el formulario alojado mediante `POST /v1/{merchant_id}/charges`, `method=card`, `confirm=false` y `redirect_url`. Recibe la URL del proveedor en `payment_method.url`. No se utiliza un SDK antiguo ni se envían datos de tarjeta desde la tienda.

| Dato | Dónde se obtiene | Variable |
| --- | --- | --- |
| ID de comercio | Dashboard Openpay México → datos de integración | OPENPAY_MERCHANT_ID |
| Llave privada | Dashboard Openpay México → credenciales/API | OPENPAY_PRIVATE_KEY |
| Entorno de API | Sandbox o cuenta productiva | OPENPAY_PRODUCTION |
| Usuario y contraseña del receptor webhook | Los defines tú y los configuras también en Openpay | OPENPAY_WEBHOOK_USER, OPENPAY_WEBHOOK_PASSWORD |

No se necesita llave pública porque se utiliza redirección a un formulario alojado. La opción Openpay aparece cuando están configurados los datos, HTTPS y el mismo entorno que `PAYMENTS_LIVE`.

Configura el webhook `https://TU_DOMINIO/pagos/webhook/openpay/` con HTTP Basic usando el usuario y contraseña anteriores. El evento verification guarda su código; un superusuario lo ve en el resumen del dashboard o en Django Admin para completar la verificación en Openpay. Las notificaciones de cargo se confirman consultando GET del cargo con la llave privada. Un evento recibido no se acepta como prueba de aprobación por sí solo.

Prueba Openpay después de Mercado Pago. La cuenta debe tener habilitado el formulario alojado y los métodos correspondientes. La operación externa no fue probada con una cuenta del usuario; los tests comprueban payloads, autenticación y confirmación con respuestas controladas.

## Apple Pay

**Apple Pay preparado para futura habilitación.** No se renderiza un botón Apple Pay.

Apple Pay existe en México, pero eso no demuestra que una cuenta concreta de Mercado Pago/Openpay pueda habilitarlo para este checkout. Faltan comprobar una vía oficialmente soportada por la pasarela de tu cuenta, Merchant ID, certificado de identidad/procesamiento cuando corresponda, dominio verificado, HTTPS y un dispositivo compatible. No se proporcionaron esa cuenta, dominio ni certificados. Una futura integración deberá usar la misma confirmación transaccional del backend; nunca considerar el callback del navegador como prueba de pago.

## Inventario, cancelaciones e idempotencia

- Al crear un pedido se reserva stock con `transaction.atomic()` y `select_for_update()`. El stock disponible es stock menos reservado.
- Al verificar un pago aprobado se descuentan stock y reserva una vez, se registra Pago, MovimientoInventario y HistorialPedido.
- Un identificador externo repetido no genera otra venta. Un segundo pago diferente para un pedido ya pagado queda señalado para revisión; no descuenta nuevamente.
- Un pago tardío de un pedido cancelado o con reserva liberada queda en revisión, conservando su importe confirmado. No se vende stock ya reservado para otra persona ni se reembolsa automáticamente.
- Cancelar un pendiente libera su reserva. Un pedido pagado no se cancela desde esta acción.
- Solo se permite pagado → preparando → en_camino → entregado. No se permiten retrocesos ni marcar manualmente un pago aprobado.
- Un reembolso/contracargo verificado cambia el estado del pago para revisión sin devolver stock automáticamente.

Ejecuta periódicamente, por ejemplo cada minuto con el programador del servidor:

```powershell
.\.venv\Scripts\python.exe manage.py expire_reservations
```

Las reservas duran `RESERVATION_MINUTES=30` por defecto. Hasta ejecutar la limpieza, una reserva vencida conserva las unidades; la web impide iniciar nuevos pagos de ese pedido. Una notificación que falló puede reconciliarse por consulta, sin crear cargos:

```powershell
.\.venv\Scripts\python.exe manage.py reconcile_payment mercadopago ID_DEL_PAGO
.\.venv\Scripts\python.exe manage.py reconcile_payment openpay ID_DEL_CARGO
```

Para limpieza de sesiones Django:

```powershell
.\.venv\Scripts\python.exe manage.py clearsessions
```

## Administración y permisos

- El superusuario tiene todos los permisos.
- Grupo Carranco Administradores: permisos sobre modelos de negocio, sin eliminación física. Requiere is_staff=True.
- Grupo Carranco Operadores: consulta. Requiere is_staff=True.
- Ser cliente o enviar un rol desde el navegador no permite entrar al dashboard.
- Las rutas de cada pantalla también comprueban permisos de modelo Django.
- Las existencias se ajustan con motivo y auditoría; editar una descripción/precio no sobrescribe una reserva concurrente.
- Django Admin muestra stock y pagos como solo lectura; las transiciones y ajustes se hacen en el dashboard.
- Productos se desactivan; los asociados a pedidos están protegidos frente a eliminación.
- CSV contiene número, nombre, fecha, estado, importe cobrado y pasarela. Escapa prefijos de fórmulas y no exporta contraseñas, hashes ni datos bancarios.

## Seguridad

Se utilizan CSRF, autenticación y sesiones Django, contraseñas nativas validadas, cookies HttpOnly, validación de formularios y consultas ORM. Solo los endpoints de webhook eximen CSRF, con autenticación propia de proveedor y consulta del estado real. No se guarda tarjeta, CVV, vencimiento, tokens de acceso ni payload bancario completo en la base o auditoría.

El receptor HTTP limita el tamaño del cuerpo. Las imágenes aceptan JPG/PNG/WebP de hasta 2 MB y 20 megapíxeles mediante ImageField/Pillow. Static y media están separados. `.env` no se sirve. En producción DEBUG=False, ALLOWED_HOSTS y orígenes CSRF deben corresponder al despliegue HTTPS. Ningún secreto se entrega en HTML o JavaScript.

El bloqueo de login se identifica por usuario/IP y se persiste en MySQL. Un despliegue compartido debe añadir límites en el proxy para registro, contacto, cargas y tráfico general según su capacidad. El prototipo está destinado al equipo y evaluadores, no a venta pública.

## Pruebas

```powershell
.\.venv\Scripts\python.exe manage.py test --noinput
```

Django crea una base de pruebas separada, `test_carranco_django` por defecto. La cuenta necesita permisos de creación/eliminación sobre esa base de pruebas; no los concedas al usuario de producción. Para pruebas locales puedes usar otra cuenta en una copia privada de `.env`. No asignes TEST_DB_NAME a una base con datos: Django elimina la base de pruebas al terminar.

Ejemplo de preparación con Workbench para pruebas locales:

```sql
GRANT ALL PRIVILEGES ON test_carranco_django.*
TO 'carranco_app'@'127.0.0.1';
```

Se comprobaron 64 pruebas con MySQL 8.0.46: registro, login, sesiones, direcciones, catálogo, carrito, precios, consentimiento, checkout, pedidos, ownership, CSRF, estados, inventario, CRUD, CSV, webhooks, idempotencia y concurrencia sobre la última unidad. Los proveedores externos se controlan en los tests; no se afirma una operación sandbox o productiva ejecutada con credenciales reales.

Los tres CSS generales se compararon byte a byte con la tercera entrega; son idénticos. Los templates renderizan correctamente y los JavaScript pasan la verificación de sintaxis. No se dispuso de una comprobación visual en navegador en este entorno; revisa en tu instalación anchos 320/390/768/1280/1440, galería, menú, filtros y toasts antes de presentar la demostración.

`docs/VERIFICACION.md` detalla el resultado y los pasos de aceptación con tu cuenta de pasarela.

## Problemas frecuentes

| Problema | Solución |
| --- | --- |
| SECRET_KEY ausente | Genera el secreto, escríbelo entre comillas en .env y reinicia |
| Access denied | Revisa DB_USER, DB_PASSWORD y el host exacto del usuario MySQL |
| Can't connect / ECONNREFUSED | Inicia MySQL y revisa host/puerto |
| Unknown database | Crea carranco_django en Workbench |
| Tabla inexistente | Ejecuta manage.py migrate |
| Login bloqueado | Espera 15 minutos tras los fallos |
| No aparece Pagar | Configura credenciales, webhook y APP_URL HTTPS |
| Firma webhook inválida | Revisa la clave de la aplicación y la URL con data.id; sincroniza el reloj |
| Redirección HTTPS repetida | Revisa el proxy y TRUST_PROXY_HTTPS; no lo habilites sin un proxy de confianza |
| Perfil/dirección incompletos | Edita Mi cuenta y guarda la dirección antes de checkout |
| Importe mínimo de pasarela | Configura explícitamente el importe académico y vuelve a aceptar el resumen |

## Referencias oficiales

- Django y versiones: https://www.djangoproject.com/download/
- Django/MySQL: https://docs.djangoproject.com/en/5.2/ref/databases/
- Transacciones: https://docs.djangoproject.com/en/5.2/topics/db/transactions/
- Checkout Pro Preferences: https://www.mercadopago.com.mx/developers/en/reference/online-payments/checkout-pro-preferences/overview
- Crear preferencia: https://www.mercadopago.com.mx/developers/en/reference/online-payments/checkout-pro-preferences/create-preference/post
- Webhooks: https://www.mercadopago.com.mx/developers/en/docs/your-integrations/notifications/webhooks
- Openpay México, redirección: https://documents.openpay.mx/docs/op-form-charge
- Openpay México, API: https://documents.openpay.mx/docs/api.html
- Openpay México, notificaciones: https://documents.openpay.mx/docs/webhooks.html
- Apple Pay México: https://www.apple.com/mx/apple-pay/
- Apple Pay web: https://developer.apple.com/help/account/configure-app-capabilities/configure-apple-pay-on-the-web/

Este sitio fue desarrollado únicamente con fines académicos como parte de un proyecto universitario de Comercio Electrónico. No representa ni sustituye los canales oficiales de Quesos Carranco.
