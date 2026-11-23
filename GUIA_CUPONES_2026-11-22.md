# Cupones Carranco — parche del 22 de noviembre de 2026

## Decisión recomendada

Los cupones se controlan por **vigencia, usos totales y usos por cuenta**. No se utiliza el número consecutivo del cliente: ese número no describe quién llegó primero de forma confiable y permitiría comportamientos difíciles de explicar.

Para una campaña limitada a los primeros clientes configura, por ejemplo:

- Código: `CARRANCO10`
- Tipo: porcentaje
- Valor: `10`
- Compra mínima: `$300`
- Inicio y fin: una semana
- Usos totales máximos: `50`
- Usos máximos por cliente: `1`

Eso representa los primeros 50 pedidos que reserven válidamente el código. Si un pedido pendiente se cancela o vence sin pago, su uso se libera. Los pagos aprobados conservan el registro para auditoría.

## Funcionamiento

- El descuento se aplica al subtotal de productos. El envío conserva la regla existente.
- Admite porcentaje o importe fijo. El descuento fijo nunca supera el subtotal de productos.
- El cliente aplica o retira el código en checkout y ve subtotal, envío, ahorro y total antes de crear el pedido.
- El código queda incluido en el resumen firmado. Si se cambia después, el servidor rechaza el resumen anterior.
- Al crear el pedido se bloquean la cuenta, el inventario y el cupón dentro de la transacción. Se verifican otra vez fechas, compra mínima, límite global y límite por cliente.
- Mercado Pago recibe el total final con descuento. El pedido, detalle, recibo web y recibo por correo conservan el código y el ahorro.
- Web y modo app utilizan el mismo checkout.

No se permite un cupón que produzca un total de pago igual a cero. Para regalos o muestras crea un flujo administrativo diferente; no envíes un pago de cero a Mercado Pago.

## Administración

Después de desplegar y migrar, entra como superusuario en:

```text
/dashboard/cupones/
```

Pulsa **Nuevo cupón** y completa:

1. Código sin espacios. Se guarda en mayúsculas.
2. Tipo: porcentaje o importe fijo.
3. Valor y subtotal mínimo de productos.
4. Fechas en hora de Ciudad de México; los extremos vacíos no limitan la vigencia.
5. Usos totales máximos; vacío significa sin límite global.
6. Usos máximos por cliente; se recomienda `1`.
7. Estado activo.

Los administradores del grupo Carranco Administradores reciben los permisos al ejecutar nuevamente `create_carranco_groups`. Los superusuarios ya tienen acceso. El dashboard no elimina cupones usados; desactívalos para conservar el historial.

## Railway

El parche incluye `pedidos.0003`. Conserva en **Settings → Deploy → Pre-Deploy Command**:

```bash
python manage.py migrate --noinput && python manage.py seed_promotions
```

El seed de promociones no crea cupones. Los códigos se crean desde el dashboard para evitar publicar un código conocido dentro del repositorio.

Conserva también la ejecución periódica que libera reservas vencidas:

```bash
python manage.py expire_reservations
```

Aunque el checkout deja de contar automáticamente una reserva expirada, el comando limpia el inventario reservado y el registro provisional del uso.

## Prueba rápida

1. Crea `PRUEBA10`, 10%, mínimo $0, diez usos totales y uno por cliente.
2. Con una cuenta de cliente agrega productos y entra a checkout.
3. Escribe `PRUEBA10`; revisa que aparezca el descuento y cambie el botón de creación.
4. Crea el pedido y confirma que el detalle conserve código, ahorro y total.
5. Cancela el pedido pendiente y aplica el código otra vez; debe quedar disponible.
6. Completa una compra de prueba o real solo si aceptas el cargo mostrado. Mercado Pago debe recibir exactamente el total descontado.

## Verificación realizada

- 133 pruebas Django: 131 aprobadas y 2 omitidas por requerir MySQL.
- Migraciones sincronizadas y recopilación de recursos estáticos correcta.
- Prueba en Chromium a 393×852: código aplicado en web y modo app, descuento de $6.00 y total de $133.00 sin desbordamiento horizontal.
- No se modificó Railway, no se creó ningún cupón productivo y no se realizó un cargo real.
