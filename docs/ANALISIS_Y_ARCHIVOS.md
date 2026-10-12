# Base revisada y archivos reutilizados

La base inspeccionada fue `carranco-ecommerce-entrega3-fase1.zip`, versión 3.0.0. Contiene 33 archivos de Node.js/Express y una tienda HTML/CSS/JavaScript. Inicio, catálogo, detalle, filtros, galería, relacionados, navbar, footer, WhatsApp de demostración y validación de stock estaban presentes. El carrito guardaba IDs y cantidades en `carranco.cart.v1`.

El SQL incluye nueve tablas: productos, clientes, direcciones, carritos, carrito_items, pedidos, pedido_items, pagos y movimientos_inventario. Había nueve SKU y ocho productos de catálogo. No había endpoints de registro, checkout, pedidos ni pasarelas implementadas. La entrega Django incorpora esas operaciones; no asume que ya existían.

## Transformaciones

| Origen | Resultado Django |
| --- | --- |
| public/index.html | templates/core/index.html y templates/base.html |
| Navbar, footer, head y diálogos repetidos | templates/base.html compartida |
| public/productos.html | templates/catalogo/productos.html y tarjeta.html |
| public/producto.html | templates/catalogo/producto_detalle.html |
| public/css/styles.css | static/css/styles.css, contenido idéntico |
| public/css/components.css | static/css/components.css, contenido idéntico |
| public/css/responsive.css | static/css/responsive.css, contenido idéntico |
| Menú, toast, diálogo, fallback de imágenes | static/js/main.js, mismos componentes |
| Carrito local de js/main.js | apps/carrito, sesiones Django, static/js/carrito.js |
| js/catalogo.js | static/js/productos.js, filtra tarjetas renderizadas por el ORM |
| js/producto-detalle.js | static/js/producto-detalle.js, galería y cantidad |
| database/seed.sql | apps/catalogo/data/productos.json y seed_carranco |
| API Express y conexión mysql2 | Views, Forms, ORM y configuración MySQL de Django |

Las URLs anteriores index.html, productos.html y producto.html?id=ranchero redirigen a las URLs nombradas nuevas. Las fotografías y los textos del inicio se reutilizan. Los datos de precios y stock del inicio, catálogo, carrito y checkout salen del ORM. La colección JSON es solo la carga inicial; no es una fuente de datos del frontend.

Se añade commerce.css para las pantallas nuevas sin alterar los tres CSS anteriores. Se añaden templates de cuentas, direcciones, carrito, checkout, pedidos, contacto, ayuda y administración. Todas las aplicaciones incluyen sus models/views/forms/urls/admin según corresponda y migraciones versionadas.

## Conservación de la base previa

Se recomienda `carranco_django` como base nueva. No ejecutar DROP ni importar el schema.sql anterior sobre Django. Las tablas propias usan el prefijo `cc_`; Django añade sus tablas de autenticación y sesión. La base anterior permanece disponible para consultas y respaldo.

`import_legacy_products --database carranco_ecommerce` copia los SKU sin sobrescribirlos y nunca escribe en la base origen. Se ejecuta antes de seed_carranco si se desean los precios y existencias previos. Rechaza pedidos o reservas anteriores: no se traslada automáticamente un historial financiero a un esquema distinto sin comprobar su correspondencia.

Si la instalación previa contiene clientes o pedidos reales que no aparecen en el ZIP, respáldala y conserva su historial en la base anterior. No reutilices hashes de un algoritmo desconocido ni inventes un acceso de cliente: cualquier traslado posterior necesita revisar el esquema y proporcionar un restablecimiento de contraseña. La base de código revisada no tenía esos flujos implementados.
