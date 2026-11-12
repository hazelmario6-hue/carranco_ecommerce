# Carranco · cobro del precio completo

Este cambio parte del commit `06fc0f8` ya desplegado. Los pedidos **nuevos** cobran el mismo total visible en carrito y checkout: suma de `precio_catalogo × cantidad` más envío. El envío es $79 MXN cuando el subtotal es menor de $500 MXN y gratis desde $500 MXN. Ejemplo: dos unidades de $95 → $190 + $79 = **$269 MXN** tanto en Mercado Pago como en Openpay.

El nombre de columna `total_academico` se conserva por compatibilidad con la base y los pedidos anteriores; para pedidos nuevos almacena el total completo. Los pedidos anteriores cuyo importe reducido difiere del total del catálogo no pueden iniciar otro pago: crea un pedido nuevo. Los registros históricos y sus recibos conservan el importe realmente cobrado. El campo legado `precio_academico` permanece en la base; el panel ya solo edita el precio de venta y sincroniza ambos valores al guardar. No se necesitan migraciones para esta actualización.

`ACADEMIC_CHARGE_AMOUNT` y `ACADEMIC_MAX_CHARGE` ya no se consultan. Puedes retirarlas de Railway después del despliegue. `ACADEMIC_MODE` solo conserva la identificación del proyecto académico; no reduce el cargo. El recibo de compra no equivale a una factura fiscal CFDI.

## Aplicar el parche

1. En el repositorio Django local, confirma `git status` limpio y `git pull --ff-only origin main`. La base esperada es `06fc0f8`.
2. Copia **el contenido** de `actualizacion/` del ZIP nuevo sobre el repositorio. No subas el ZIP como un archivo del proyecto, ni sustituyas `.env`, `datos_catalogo.json` o credenciales.
3. Revisa `git diff --check`, `git status`, confirma los archivos y haz `git add -A`, `git commit -m "Cobrar total de catalogo y envio"`, `git push origin main`.
4. Confirma el nuevo commit activo en Railway. La web y el APK usan el mismo backend; no es necesario generar otro APK por este cambio.

## Activar Mercado Pago con dinero real

1. En Mercado Pago Developers, activa las credenciales **productivas** de la aplicación de Checkout Pro/Preferences y configura Webhooks productivos para el evento **Payments (`payment`)** con `https://carrancoecommerce-production.up.railway.app/pagos/webhook/mercadopago/`. Copia el Access Token productivo y la clave de firma del webhook por separado; nunca a Git ni al chat.
2. En las variables del servicio Django de Railway configura `PAYMENTS_LIVE=True`, `DEBUG=False`, `APP_URL=https://carrancoecommerce-production.up.railway.app`, `TRUST_PROXY_HTTPS=True`, `MP_ACCESS_TOKEN` productivo, `MP_WEBHOOK_SECRET` productivo y deja vacío `MP_TEST_BUYER_EMAIL`. Conservar `ACADEMIC_MODE=True` no cambia el importe. Si Openpay todavía no tiene credenciales productivas, deja vacíos `OPENPAY_MERCHANT_ID`, `OPENPAY_PRIVATE_KEY`, `OPENPAY_WEBHOOK_USER` y `OPENPAY_WEBHOOK_PASSWORD`; `OPENPAY_PRODUCTION=False`.
3. **Despliega los cambios de variables** de Railway. Desde `railway.cmd ssh`, ejecuta `/app/.venv/bin/python /app/manage.py check_integrations --remote`. Debe indicar modo REAL, Mercado Pago variables presentes y consulta API autenticada OK. Esto no prueba la recepción del webhook.
4. Registra/usa una cuenta Carranco con correo verificado. Crea un **pedido nuevo** y revisa el total exacto en checkout, la pasarela y el recibo. Verifica en el panel de Mercado Pago un cargo real pequeño que estés dispuesto a pagar; comprueba que el webhook o la consulta manual confirme el pedido una sola vez. No reutilices pedidos del modo de pruebas.

Openpay requiere que la cuenta y las credenciales productivas hayan sido aprobadas por Openpay. Configura su webhook productivo con HTTP Basic y `OPENPAY_PRODUCTION=True` solo cuando también lo vayas a activar; `PAYMENTS_LIVE` es global para ambas pasarelas. La documentación original en `README_CORREOS_Y_PAGOS.md` describe el proceso de sandbox y otras funciones, pero su explicación del importe académico reducido fue sustituida por esta guía.

Esta entrega no activa variables por sí sola y no realizó transacciones reales. Revisa precios, inventario y condiciones de entrega antes de aceptar el primer cargo. El problema de que la web muestre la interfaz app se tratará por separado.
