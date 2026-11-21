# Verificación — 20 de noviembre de 2026

## Resultados reproducidos

- Suite Django: 124 pruebas ejecutadas, 122 aprobadas y 2 omitidas porque requieren MySQL. Configuración aislada SQLite: `python manage.py test --settings=config.test_settings --noinput`.
- `makemigrations --check --dry-run`: sin cambios pendientes de migración.
- `collectstatic --noinput`: 143 archivos recopilados.
- Sintaxis de `carrito.js` y `app.js`: correcta con `node --check`.
- Actualizador probado con PowerShell 7.4.6 y dos repositorios temporales: copia, commit y push a remotos locales, repetición sin cambios, archivos CRLF, preservación de `.env`, rechazo de cambios locales diferentes y detección de rebase pendiente. No se hizo push a los repositorios reales.
- Navegador Chromium: 60 comprobaciones locales aprobadas. No se usó el sitio productivo.
- Android: `gradle --no-daemon lintDebug assembleDebug` completado con Gradle 8.9, AGP 8.7.3 y SDK 35. Lint: 0 errores, 4 advertencias heredadas sobre reglas de respaldo y textos sin recursos de traducción.
- APK: `apksigner verify` correcto, firma v2. Paquete `mx.edu.carranco.tienda`, versión 1.2, versionCode 3, Android mínimo API 24.

## Pantallas revisadas

| Presentación | Tamaños CSS | Pantallas |
| --- | --- | --- |
| Web | 1440×1000, 393×852 | Inicio, catálogo, producto, carrito, login, registro, contacto |
| App | 360×800, 393×852, 412×1000, 852×393 | Las siete anteriores |
| App con cliente autenticado | Los cuatro tamaños app | Perfil, direcciones, checkout, carrito |

En esas comprobaciones no hubo desbordamiento horizontal. Las páginas cortas cubrieron el alto visible. En las pantallas autenticadas se comprobó que el final del contenido quedara accesible por encima de la navegación inferior al terminar de desplazarse. Web mostró su pie y no mostró barra app; app mostró su navegación y no el pie web.

## Comportamientos comprobados

- 25 pulsaciones rápidas en `+`, con 18 mantequillas disponibles: cantidad final 18, un POST con cantidad 18 y ninguna recarga.
- Subtotal de $1,080.00 con envío $0.00; al reducir a una unidad, subtotal $60.00, envío $79.00 y total $139.00. Contador actualizado y eliminación hasta carrito vacío.
- Stock reducido de 18 a 6 después de mostrar la página: el servidor rechaza la cantidad anterior y la interfaz adopta el máximo 6 y el mensaje actualizado.
- Servidor: rechazo de cantidades manipuladas, recalculo de importes y bloqueo de Openpay incluso con variables presentes.
- Roles: login de personal dirigido al dashboard, exclusión de estilos app y denegación de permisos a clientes; logout devuelve el modo cliente en el APK.
- Promociones: altas y ediciones con permisos y CSRF, orden, precio vigente, ventanas de fechas, desactivación, invisibilidad por falta de stock y seed idempotente.
- Presencia de las URLs exactas de las siete redes y sustitución de textos genéricos de galerías.
- Pruebas existentes de PIN, correo, pagos y webhooks usando proveedores simulados dentro de los tests.

## Límites de esta validación

- Las dos pruebas de MySQL (bloqueos/concurrencia y configuración del motor) no se ejecutaron en este entorno SQLite. La configuración productiva conserva MySQL y las transacciones existentes.
- No se cambiaron variables de Railway, no se desplegó a producción y no se realizaron cargos ni envíos reales de correo.
- No se ejecutó el APK en hardware Android ni se probó Safari/iOS real. Los tamaños móviles son ventanas de Chromium, no dispositivos físicos ni una simulación completa del teclado y las zonas seguras del sistema.
- Algunas imágenes y fuentes externas no se descargaron en este entorno; se revisó también el comportamiento de respaldo. Se requiere comprobar esos recursos y los saltos a las apps de redes/WhatsApp desde el teléfono.

Las comprobaciones de presentación y transacciones del servidor están automatizadas; el cierre final requiere instalar la versión, aplicar las migraciones y recorrer el flujo real descrito en `GUIA_ACTUALIZACION.md`.
