# Carranco: interfaz para el APK

> Esta guía describe la actualización de diseño anterior. El paquete actual también incorpora correos y pagos: sigue primero `README_CORREOS_Y_PAGOS.md`, que requiere cuatro migraciones nuevas y variables de correo/pasarelas.

## Qué cambia

El APK se identifica con `CarrancoApp/2` en su User-Agent. Django activa `request.app_mode` para esa petición: inicio compacto, encabezado corto, navegación inferior Inicio/Productos/Carrito/Cuenta y estilos para celular. El aviso académico y la ayuda se encuentran en el botón de tres puntos → Acerca de. La versión del navegador conserva su encabezado y footer, incluso si se abre desde un teléfono.

Es una aplicación híbrida con WebView y una pantalla inicial nativa. Este cambio no convierte la tienda en una aplicación de comercio completamente nativa. El indicador de modo app es solo de presentación y no concede permisos.

## Cómo desplegar

1. Extrae este ZIP. Abre la carpeta `carranco_ecommerce-main`.
2. En el repositorio Django `carranco_ecommerce`, actualiza los archivos enumerados abajo, conservando su ruta. No subas la carpeta contenedora dentro de otra carpeta. No reemplaces las variables de Railway ni subas un `.env`.
3. Guarda los cambios en la rama que despliega Railway y espera a que termine el despliegue.
4. Conserva el build command `python manage.py collectstatic --noinput` y el comando Gunicorn que ya funcionaba. El cambio de diseño por sí solo no requería variables ni migraciones; la actualización posterior de correos y pagos sí las requiere, como indica su guía.
5. Para previsualizar en un navegador, abre `https://carrancoecommerce-production.up.railway.app/?modo=app`. La preferencia de vista dura un día. Para regresar al sitio normal abre `https://carrancoecommerce-production.up.railway.app/?modo=web`.
6. Instala el nuevo APK. La app activa su diseño automáticamente; no requiere añadir parámetros a sus enlaces.

Archivos nuevos o modificados:

- config/settings.py (incorpora AppModeMiddleware)
- apps/core/middleware.py
- apps/core/views.py
- apps/core/urls.py
- apps/core/test_app_mode.py
- templates/base.html
- templates/catalogo/tarjeta.html
- templates/includes/disclosure.html
- templates/includes/app_nav.html
- templates/core/app_inicio.html
- templates/core/acerca_app.html
- static/css/app.css
- static/js/app.js
- README_MODO_APP.md

El cambio original de diseño no alteró modelos, precios, inventario, autenticación, lógica del carrito ni pasarelas. La actualización de correos y pagos tiene su propia lista de cambios. No ejecutes comandos de vaciado, importación o reinicio de base de datos para instalar este diseño.

## Prueba de aceptación

- Navegador normal: muestra el sitio con footer; no aparece la navegación inferior.
- APK con internet: muestra el inicio compacto y los cuatro accesos inferiores.
- Agrega un producto; verifica contador, cantidades y total en carrito.
- Inicia y cierra sesión; el modo app se conserva. Comprueba el formulario y el teclado.
- Abre los tres puntos: aviso académico, preguntas frecuentes, contacto y pedidos accesibles.
- Antes de abrir la app, activa modo avión y ciérrala por completo. Al abrirla debe aparecer la pantalla local con marca y aviso de falta de conexión, no un error técnico de WebView.
- Restablece internet y pulsa Volver a intentar. Debe abrirse el inicio. El botón no repite un POST ni una compra anterior.
- Prueba un flujo de pago en el ambiente de prueba habitual; las pasarelas externas continúan abriéndose fuera del WebView.

## Validación realizada

Siete pruebas de Django pasaron en una base SQLite temporal aislada: separación web/app, rutas públicas, divulgación académica, previsualización, autorización, carrito/cuenta y CSRF. No se conectaron ni modificaron bases de datos de Railway. Se revisaron inicio, catálogo, detalle, carrito vacío, login y acerca de a 390 px, sin desbordamiento horizontal ni errores JavaScript. Para esa revisión visual se bloquearon recursos externos: se verificó también la presentación de imagen no disponible.

Pendiente: prueba en teléfono real, teclado de Android, interrupciones de red reales y pasarelas. Las pruebas de esta entrega no sustituyen la suite original de transacciones concurrentes en MySQL.
