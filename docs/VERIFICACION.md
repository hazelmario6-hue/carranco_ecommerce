# Verificación de la entrega Django

PROYECTO ACADÉMICO · SITIO NO OFICIAL

## Resultado comprobado

El proyecto se probó con Python 3.12.14, Django 5.2.18, mysqlclient 2.3.0 y un servidor MySQL 8.0.46 real. Se aplicaron las migraciones, se cargaron los nueve SKU y se crearon los grupos de permisos. `manage.py check` no detectó problemas.

La suite contiene 64 pruebas y terminó sin fallos. Incluye registro, contraseñas, login correcto e incorrecto, bloqueo, logout POST, persistencia del carrito al entrar, perfil, direcciones, catálogo, búsqueda y categorías, transferencia del carrito previo, límites de stock, cálculo Decimal, consentimiento y resumen firmado, idempotencia de pedidos, pertenencia de pedidos/direcciones, CSRF, productos, ajustes auditados, transiciones, clientes, reportes, CSV y pagos.

Se verificó que dos solicitudes concurrentes de distintos compradores sobre la última unidad crean un solo pedido y una sola reserva. Una edición simultánea de nombre/precio no borra una reserva de inventario. La suite también verifica notificaciones duplicadas de Mercado Pago y Openpay, importes/monedas incorrectos, pagos tardíos y segundos pagos para un pedido ya confirmado.

Los proveedores se controlaron con mocks, sin contactar una cuenta real. La firma HMAC, HTTP Basic y las llamadas de consulta pasan por las rutas y servicios de la aplicación. Esto comprueba la lógica, no equivale a un pago aprobado por una cuenta sandbox/productiva.

Los tres CSS generales se compararon mediante SHA-256 con los de la entrega 3 y son idénticos. Los templates públicos y administrativos renderizaron correctamente y los cinco JavaScript pasaron `node --check`.

## Lo que falta verificar en la instalación del usuario

- Instalar con MySQL local y completar `.env`.
- Revisar visualmente móvil, tablet y escritorio a 320, 390, 768, 1280 y 1440 px. No se dispuso de QA visual de navegador en el entorno de construcción.
- Probar menú móvil, filtros dinámicos, galería, cantidades, toast y transferencia desde localStorage en un navegador real.
- Probar carga de una foto desde Inventario/Productos y verificar su servido desde media.
- Configurar credenciales de prueba, HTTPS, cuentas comprador/vendedor y webhook de Mercado Pago. Comprobar aprobado, pendiente y rechazado externos.
- Tras esa prueba, configurar Openpay y verificar su webhook/formulario alojado con la cuenta habilitada.
- Si se desean cobros reales, hacerlos únicamente tras la prueba externa y el consentimiento explícito del importe reducido con DEBUG=False, HTTPS y PAYMENTS_LIVE=True.

## Prueba manual recomendada

1. Abre `/productos/`, busca Panela y filtra Frescos.
2. Abre Ranchero y cambia miniatura/cantidad. Agrega y comprueba contador.
3. En `/carrito/`, aumenta/disminuye, elimina y vacía. Intenta superar stock.
4. Regístrate, guarda dirección y vuelve al checkout. Comprueba que el carrito se mantuvo.
5. Revisa total comercial y monto académico. Sin aceptar, no debe crearse el pedido.
6. Acepta y crea el pedido. Verifica el historial; con credenciales vacías permanece pendiente.
7. Intenta abrir un pedido de otra cuenta: debe devolver 404. Como cliente, `/dashboard/` debe devolver 403.
8. Entra al dashboard como administrador, crea/edita/desactiva un producto, ajusta stock con motivo, busca cliente y exporta CSV.
9. Una vez habilitada la pasarela, paga desde su formulario alojado y espera la confirmación del servidor. Llegar a confirmación con `status=approved` no debe aprobar un pedido.
10. Reenvía una notificación del proveedor: debe permanecer un movimiento de venta por SKU/pedido.
11. Avanza pagado → preparando → en_camino → entregado; rechaza retrocesos.

Apple Pay permanece oculto: faltan confirmar soporte de la cuenta/pasarela, Merchant ID, certificados y dominio verificado. No se presenta como habilitado.
