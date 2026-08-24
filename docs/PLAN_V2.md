# La Hidrocálida v2 — Inventario, Control y Métricas

**Estado:** plan aprobado, **nada implementado**.
**Base:** rama `flujo-mesero`, commit `09bb815`.
**Estado actual del sistema:** [ESTADO_ACTUAL.md](./ESTADO_ACTUAL.md).
**Avance de la ejecución:** [SPRINTS.md](./SPRINTS.md) — este plan es el *qué* y el *por qué*;
SPRINTS.md es el *cuándo* y el *cómo va*. Incluye correcciones verificadas a este documento.

---

## Cómo retomar esto

**Siguiente paso concreto:** Fase A → Bloque 0.1 (baseline de Alembic). Sin eso ninguna
migración de este plan es reproducible.

**No quedan preguntas abiertas.** Las dos que había están resueltas:

- **IVA:** los precios de `Platillo` son **sin IVA**. Con factura, `total = suma_artículos × 1.16`.
  El cliente que factura paga 16 % más. Decisión tomada (Bloque 7).
- **Escalado:** **entra Redis en esta versión**. El fan-out de WebSocket va por pub/sub, no se fija
  `--workers 1` (Bloque 1.2). Redis además sostiene el rate limiting y el consumo de tokens de
  aprobación de un solo uso (Bloques 4 y 6).

---

## Context

El POS está en producción y cubre el flujo operativo (mesero → cocina → caja), pero se construyó
optimizando velocidad de entrega, no control. La auditoría de este repo confirma tres huecos
estructurales que hoy cuestan dinero:

1. **No hay control de insumos.** `Articulo` existe solo como línea de gasto. No hay stock, ni
   movimientos, ni relación platillo→insumo. Se compra a ciegas y se descubre el faltante cuando
   ya no hay.
2. **No hay control de autoridad.** Ninguna acción sensible (cancelar pedido, editar propina de un
   ticket pagado, cerrar caja con faltante) exige más que el rol ya logueado. El cajero ve las
   ventas del día, el ticket promedio y las propinas del local — información que el personal no
   debería tener.
3. **No hay memoria de tiempos.** `Pedido` solo guarda `fecha_creacion` y `fecha_pago`;
   `ArticuloPedido` no guarda ninguna fecha. Es imposible reconstruir cuánto tardó un platillo o
   dónde se atoró un pedido. Sin eso no hay decisión informada sobre cuánto preparar.
4. **No se puede cobrar con factura.** No existe `subtotal`, `iva` ni `rfc` en ningún modelo; el
   `total` es una suma plana de precios.
5. **No se puede cerrar una sesión.** El JWT lleva `sub` y `exp` y nada más — sin `jti` ni
   blacklist, un token vive 24 h pase lo que pase, en tablets que rota todo el personal.
6. **Nada se cierra solo.** Un turno de caja o un check-in que nadie cerró queda abierto
   indefinidamente: la nómina registra jornadas de 100 horas y el corte de caja acumula tres días
   de ventas contra el fondo de anteayer. Está pasando cada semana.

Y hay un séptimo problema, operativo: **se pierden pedidos**. La auditoría encontró la causa raíz
(Bloque 1) — no es un misterio, son cuatro defectos concretos y todos son arreglables.

Resultado esperado: saber qué hay en almacén y cuándo re-pedir; que ninguna acción sensible ocurra
sin autorización trazable; que el personal opere sin ver el dinero del día; tener tiempos reales
por platillo —y por cocinera— para decidir cuánto producir; poder cobrar con IVA cuando el cliente
pide factura; y que las sesiones mueran en el corte de jornada, no cuando al token se le acaba el
reloj.

---

## Estado actual — hallazgos que condicionan el diseño

| Hallazgo | Ubicación | Consecuencia |
|---|---|---|
| Endpoints `async def` con `Session` **síncrona** | `pedidos.py:136,449,670,813,969,1085,1267` (16 en total) | Cada query bloquea el event loop; los pings WS no se procesan a tiempo |
| WebSocket manager 100% en memoria del proceso | `websocket_manager.py:23-40` | Con >1 worker/réplica, el KDS conectado al worker B nunca recibe el pedido creado en el worker A |
| Sin máquina de estados: solo whitelist rol→destino | `pedidos.py:839-844` | Un admin puede pasar `pagado → pendiente`; un cajero puede pagar sin pasar por cocina |
| Enum de estados duplicado en 4 lugares, ya divergente | `models.py:98-100` (le faltan `cancelado`/`dividido`), `pedidos.py:343,859`, `stores/pedidos.ts:23` | Divergencia silenciosa |
| Check-then-act sin lock + 2 commits separados | `pedidos.py:1005` y `1018` | Dos tablets de cocina en paralelo dejan el pedido atascado en `preparando` con todo listo |
| `dividir_cuenta` commitea dentro del bucle | `pedidos.py:578,751` | División a medias queda persistida, sin deshacer |
| Idempotencia de agregar-artículos sin constraint en BD | migración `e8f7d6c5b4a3` (índice **no** único) | Ventana de carrera → artículos duplicados |
| Sin cola offline en el mesero | `MeseroView.vue`, `stores/pedidos.ts:326` | Sin red, el pedido se evapora; solo reintento manual |
| Sin `SELECT FOR UPDATE` ni versión optimista en todo el backend | — | Último que escribe gana |
| `verify_password` acepta **texto plano** si el hash no empieza con `$` | `auth.py:35-38` | Si queda un PIN legado sin hashear, entra sin criptografía |
| Sin rate limiting en ningún login | `routers/auth.py:34,66,89` | NIP de 4 dígitos = 10 000 intentos, fuerza bruta trivial |
| `GET /usuarios/` sin check de rol | `users.py:37-43` | Cualquier mesero lista a los administradores |
| `GET /auth/users` y `GET /ws/stats` públicos | `auth.py:162`, `websocket_routes.py:123` | Nómina del personal y topología de conexiones sin auth |
| `create_all()` en el arranque + Alembic | `main.py:29` | Solo 2 de 6 migraciones crean tablas; las 10 tablas núcleo **no tienen migración**. `alembic upgrade head` sobre DB vacía no reconstruye el esquema |
| Sin `require_role` reusable | ~30 checks inline repetidos | Ya diverge: `agregar_articulos` bloquea `cuenta_solicitada`, `actualizar_articulos` no |
| Cero facturación: no hay `subtotal`, `iva`, `rfc` en ningún modelo | `models.py:97` (`total` es suma plana) | No se puede cobrar con IVA ni separar la venta facturada |
| JWT sin `jti` ni `iat` utilizable, sin blacklist | `auth.py:45-55` | **Imposible invalidar una sesión**, ni una ni todas |
| `RegistroAsistencia` sin `sucursal_id`, `turno_id` ni snapshot de rol | `models.py:322-333` | El rol se lee en vivo; si una cocinera cambia de rol se reescribe el pasado |
| `update_articulo_estado` no guarda **quién** marcó listo | `pedidos.py:968-1081` | No hay a quién atribuir los tiempos de cocina |
| El NIP de asistencia es un interruptor que ignora la fecha del registro abierto | `routers/auth.py:114-128` | Quien olvidó salir el martes, al volver el domingo **marca salida en vez de entrada**: jornadas de 100 h y check-in perdido |
| Turno de caja sin cerrar bloquea el siguiente y sigue capturando pedidos | `turnos.py:179-184`, `models.py:278-283`, `pedidos.py:165-176` | `400` al abrir el día siguiente, y tres días de ventas caen en el turno de anteayer |
| Fechas naive comparadas contra `TIMESTAMPTZ` | `asistencia.py:42-50,127-128` | Filtros de asistencia mal en los bordes del día |

Lo que **sí** está bien y hay que reusar, no reescribir:

- Idempotencia de creación de pedido (`pedidos.py:154-163` + unique parcial + retry sobre
  `IntegrityError`). Es el patrón correcto; replicarlo.
- Polling de respaldo cada 5 s con resync completo en las 4 vistas (`KDSView.vue:161`,
  `KDSManager.vue:257`, `CajaView.vue:374`, `MeseroView.vue:210`) — es la red que hoy salva los
  eventos WS perdidos. **No quitarlo.**
- Reconexión WS con backoff + `visibilitychange` + `online` (`services/websocket.ts:356-418`).
- Turno como unidad contable (`turno_id` en `Pedido` y `Gasto`, unique parcial de turno abierto).
  Todo lo nuevo cuelga de ahí, no de fechas.
- `TTLCache` (`core/cache.py`) y eager loading (`_query_pedidos_eager`, `pedidos.py:30`) — el
  trabajo de egress de Neon ya hecho.
- `Gasto` + `GastoDetalle` como captura de compra; el inventario se engancha ahí, no la reemplaza.

---

## Decisiones tomadas

- **Inventario:** kardex de movimientos + receta **solo de insumos clave** (maíz, carnes,
  refrescos, cerveza). El resto se cuadra con conteo físico y merma manual.
- **Aprobaciones:** PIN de administrador en el momento, sin cerrar la sesión del cajero, con
  bitácora.
- **Métricas:** el rol `cajero` pierde el acceso a analytics del día. Las métricas del turno se
  difuminan hasta que un admin las confirma con su PIN.
- **Propinas:** es un **indicador**, no un reparto. Medir `propinas ÷ venta` por mesero y agregado
  del turno, contra un benchmark configurable (hoy 10 %).
- **IVA:** los precios del menú son **sin IVA**. Si el cliente pide factura, la cuenta se multiplica
  por 1.16; si no, paga lo mismo que hoy. Se decide **en caja al cobrar**, no al crear el pedido.
- **Redis entra en esta versión:** fan-out de WebSocket por pub/sub (adiós al candado de un solo
  worker), rate limiting compartido y consumo atómico de tokens de aprobación. Nunca en el camino
  crítico de un pedido: si se cae, el sistema degrada a fan-out local + polling.
- **Sesiones:** la sesión sobrevive los cierres de turno intermedios (mismo hardware, mismo
  personal) y muere en el corte de jornada de la 1:00 AM.
- **Tiempos de cocina:** se atribuyen a la cocinera que marcó el platillo, cruzados con quién
  estaba checada ese día.
- **Corte de la 1:00 AM:** el mismo corte de jornada cierra sesiones, turnos de caja y registros de
  asistencia. Disparo perezoso, no cron. Nunca inventa una hora de salida.

---

## Bloque 0 — Fundaciones

Habilitan todo lo demás. Sin esto, cada bloque siguiente repite el mismo error.

**0.1 Baseline de Alembic.** Generar `initial_baseline` con `--autogenerate` contra una DB vacía,
`alembic stamp` en producción, y **eliminar `Base.metadata.create_all()`** de `main.py:29`. Añadir
`alembic upgrade head` como release command del deploy. Sin esto, ninguna migración de este plan es
reproducible.

**0.2 `backend/app/deps.py`** — `require_roles("cajero", "administrador")` como dependencia
FastAPI. Migrar los ~30 checks inline. Reemplaza `_ensure_admin_access` (`admin.py:27`),
`_ensure_admin` (`asistencia.py:19`), `_validar_permisos_turnos` (`turnos.py:28`) y
`_ensure_can_manage_gastos` (`gastos.py:48`), que hoy hacen lo mismo cuatro veces.

**0.3 `backend/app/domain/estados.py`** — `EstadoPedido` y `EstadoItem` como `StrEnum`, más la
tabla de transiciones válidas. Fuente única; importar desde modelo, router y regenerar el tipo TS
del frontend a partir de ahí.

---

## Bloque 1 — Fiabilidad de pedidos

Las cuatro causas de que un pedido se pierda, en orden de impacto.

**1.1 Desbloquear el event loop.** Los endpoints con `Session` síncrona pasan de `async def` a
`def` — FastAPI los ejecuta en threadpool y dejan de bloquear el loop. Como consecuencia ya no
pueden hacer `await websocket_manager.notify_*()` directamente: introducir `app/events.py` con una
`asyncio.Queue` y un consumidor arrancado en el `lifespan` de la app; los endpoints encolan con
`asyncio.run_coroutine_threadsafe(...)` sobre el loop principal. Esto además desacopla el broadcast
del request: un WS lento deja de retrasar la respuesta HTTP al mesero.

*Por qué importa:* hoy, bajo carga, el loop bloqueado impide procesar los pings; a los 120 s el
limpiador de zombies (`websocket_manager.py:65-76`) cierra conexiones que están perfectamente vivas
y el KDS se queda mudo hasta que el polling lo rescata.

**1.2 Fan-out de WebSocket por Redis pub/sub.** Hoy el manager vive en memoria del proceso: con más
de un worker, el KDS conectado al worker B nunca ve el pedido creado en el worker A. Se resuelve
con Redis, que entra como dependencia de infraestructura en esta versión.

- `backend/app/core/redis.py` — cliente `redis.asyncio` único, arrancado y cerrado en el `lifespan`
  de la app, con `REDIS_URL` desde env.
- `websocket_manager.py` conserva su registro **local** de conexiones (quién está conectado a
  *este* proceso), pero deja de ser la fuente del broadcast. El consumidor de `app/events.py` (1.1)
  publica en un canal por sucursal (`ws:sucursal:{id}`); cada worker está suscrito y reparte el
  mensaje a sus conexiones locales.
- Un mensaje se publica **una vez** y lo entregan todos los workers. El payload lleva
  `evento_id` para que el acuse del KDS (1.8) y la deduplicación en el cliente funcionen igual.
- **Degradación explícita:** si Redis no responde, el fan-out cae al modo local (el worker sirve a
  sus propias conexiones) y se loguea. No se cae la operación: el polling de respaldo de 5 s en las
  cuatro vistas sigue siendo la red final. Redis nunca es camino crítico de un pedido.
- `redis` no guarda estado durable. Si se reinicia, no se pierde nada que no esté en Postgres.

*Lo que Redis habilita más allá del WS,* y por lo que vale la pena traerlo ahora en vez de después:
rate limiting compartido entre workers (Bloque 6 crítico) y consumo atómico de los tokens de
aprobación de un solo uso (Bloque 4.1). Sin estado compartido, ambos son incorrectos en cuanto hay
más de un proceso — un token "de un solo uso" se podría canjear una vez por worker.

**Riesgo aceptado:** Redis es una pieza más que puede caerse. Se mitiga con la degradación de
arriba y con el `HEALTHCHECK` reportando su estado por separado en `/health`. Nada del flujo
mesero → cocina → caja depende de que Redis esté vivo.

**1.3 Máquina de estados real.** En `domain/estados.py`, tabla `(origen, destino) → roles
permitidos`. `update_pedido` (`pedidos.py:811`) valida origen **y** destino; los estados terminales
(`pagado`, `cancelado`, `dividido`) solo salen con token de aprobación (Bloque 4). Aplicar lo mismo
a `estado_item` en `update_articulo_estado` (`pedidos.py:968`).

**1.4 Cerrar la carrera de cocina.** En `update_articulo_estado`, tomar el `Pedido` con
`with_for_update()` antes de leer sus artículos, y hacer **un solo `commit`** que cubra el cambio
del artículo y la posible promoción del pedido a `listo`. Elimina de golpe el pedido atascado y la
doble escritura de `pedidos.py:1005`/`1018`.

**1.5 Atomicidad de la división de cuenta.** Sacar los `commit` del bucle en `dividir_cuenta`
(`pedidos.py:578`) y `dividir_por_montos` (`pedidos.py:751`): un solo commit al final. Añadir
`client_request_id` a `DividirCuentaRequest` y `DividirPorMontoRequest` para que el reintento sea
idempotente de verdad y no dependa de inspeccionar `estado == "dividido"`.

**1.6 Idempotencia de agregar-artículos con red de seguridad.** Migración:
`UniqueConstraint(pedido_id, client_request_id)` en `articulos_pedido`, y capturar `IntegrityError`
como replay — el mismo patrón que ya funciona en `create_pedido`. Hoy la deduplicación depende solo
de un `SELECT` previo sin constraint detrás.

**1.7 Cola offline en el mesero.** Persistir el pedido pendiente en `localStorage` antes del POST y
reintentar automáticamente con backoff reusando el mismo `client_request_id` (la lógica de reuso ya
existe en `MeseroView.vue:555-580`). Badge visible de "N pedidos sin confirmar". Es el único caso
hoy en que un pedido desaparece sin dejar rastro.

**1.8 Acuse del KDS.** El KDS confirma recepción por WS (`pedido_id` + `evento_id`); el backend lo
registra en `PedidoEvento` (Bloque 2). Alerta en KDSManager si un pedido lleva >60 s creado sin
acuse. Convierte "a veces se pierden" en un número medible.

**1.9 Interceptor 401 en el frontend.** `api/client.ts` no tiene interceptor de respuesta: un token
expirado produce fallos silenciosos en lugar de mandar al login.

---

## Bloque 2 — Tiempos (prerequisito de las métricas)

**2.1 `PedidoEvento`** — tabla append-only: `pedido_id`, `articulo_id` (nullable),
`estado_anterior`, `estado_nuevo`, `usuario_id`, `origen` (`app`/`sistema`/`aprobacion`), `ts`. Es
a la vez la fuente de los tiempos y la bitácora de auditoría del ciclo de vida. Se escribe dentro
de la misma transacción del cambio de estado.

**2.2 Columnas denormalizadas** para no recalcular en cada consulta:
`Pedido.fecha_preparando/listo/entregado/cuenta_solicitada`;
`ArticuloPedido.fecha_preparando/listo/entregado`. Se llenan desde el mismo punto que escribe el
evento.

**2.3 Backfill** desde `fecha_creacion`/`fecha_pago` para lo histórico, marcando el resto como
desconocido — no inventar datos que no existen.

**2.4 Atribuir los tiempos a la cocinera.** Hoy `update_articulo_estado` (`pedidos.py:968`) no
registra quién marcó el platillo — el dato simplemente no existe. `PedidoEvento.usuario_id` lo
resuelve de raíz. Requisito operativo: **marcar desde `KDSManager`** (tiene JWT y por tanto
identidad), no desde `KDSView`, que es una ruta pública de solo lectura (`router/index.ts:20`). Si
se quiere marcar desde la pantalla grande, hay que darle identidad primero.

**2.5 Arreglar el módulo de asistencia** — hoy no soporta el cruce que se pide:

- `RegistroAsistencia` += `sucursal_id`, `rol_snapshot` (el rol **al momento del check-in**; hoy se
  lee en vivo de `Usuario.rol`, así que un cambio de rol reescribe el pasado), `turno_id`
  (nullable, el turno de caja abierto al momento).
- Corregir la comparación de fechas naive contra columnas `TIMESTAMPTZ` en `asistencia.py:42-50` y
  `127-128` — hoy los filtros fallan en los bordes del día.
- Eliminar el N+1 de `resumen_asistencia` (`asistencia.py:142-151`: una query por empleado dentro
  del bucle).
- Los registros sin salida y los auto-cerrados (Bloque 9) se excluyen de los tiempos de cocina: un
  turno de 100 horas contamina cualquier promedio.

**2.6 `GET /metricas/cocina`** (admin) — el cruce pedido:

- tiempos p50/p90 por platillo y por día;
- **quién estaba checado en cocina cada día** (vía `rol_snapshot`) y qué platillos marcó cada quien;
- tiempo promedio por cocinera, comparado contra el promedio del turno;
- correlación entre la dotación de cocina de ese día (cuántas cocineras, quiénes) y los tiempos
  resultantes.

Advertencia honesta sobre este cruce: la atribución es a **quien marcó el platillo listo**, que no
siempre es quien lo cocinó. Con una sola tablet de KDS, el dato dice "quién operaba la tablet", no
"quién cocinó". Para atribución individual real haría falta una tablet por estación o login por
platillo — decisión aparte. Lo que **sí** es sólido desde el día uno es el cruce a nivel día:
*estas cocineras trabajaron este día, y este día los tiempos fueron estos*. Eso ya responde la
pregunta de negocio.

Métricas que esto habilita: tiempo de cocina por platillo (`pendiente → listo`), tiempo de entrega
(`listo → entregado`), ciclo completo, **dónde** se atora cada pedido, y rendimiento de cocina por
día y por dotación.

---

## Bloque 3 — Inventario

**3.1 Modelo.**

- `Articulo` += `stock_actual` (Numeric 12,3), `punto_reorden`, `stock_maximo`, `activo`.
  `stock_actual` es **caché derivado**, no la verdad.
- `MovimientoInventario` (append-only, la verdad): `articulo_id`, `tipo`
  (`compra`|`venta`|`ajuste`|`merma`|`devolucion`), `cantidad` con signo, `costo_unitario`,
  `referencia_tipo`+`referencia_id` (gasto / pedido / conteo), `motivo`, `usuario_id`, `turno_id`,
  `sucursal_id`, `fecha`.
- `RecetaDetalle`: `platillo_id`, `articulo_id`, `cantidad_por_unidad`. Solo insumos clave; un
  platillo sin receta simplemente no descuenta.
- Constraint: `unidad` de `Articulo` pasa de texto libre a CHECK con el set que hoy solo valida el
  router (`gastos.py:46`).

**3.2 Enganches.**

- **Entrada:** en `POST /gastos/` (`gastos.py:351`), cada `GastoDetalle` de un gasto `directo`
  genera un movimiento `compra`. Reusar la transacción existente. Actualizar `costo_estandar` del
  artículo como promedio móvil.
- **Salida:** al pasar el pedido a **`pagado`**, no al crearlo — así los cancelados no descuentan.
  Explota la receta de cada `ArticuloPedido` y genera movimientos `venta`. Si el pedido pagado se
  cancela después, se generan movimientos `devolucion`.
- **Stock negativo no bloquea la venta.** Se registra y se alerta. Un POS que impide cobrar porque
  el inventario está mal capturado es un POS que se apaga.

**3.3 Endpoints** (`routers/inventario.py`, siguiendo la estructura de `gastos.py`):

- `GET /inventario/existencias` — stock actual, punto de reorden, días de cobertura estimados según
  consumo de las últimas 4 semanas.
- `GET /inventario/reorden` — lista de compra sugerida. **Esta es la salida pedida: saber cuándo
  volver a pedir.**
- `POST /inventario/conteo` — conteo físico → movimientos `ajuste` por diferencia.
- `POST /inventario/merma` — requiere aprobación admin por encima de un umbral configurable.
- `GET /inventario/kardex/{articulo_id}` — movimientos con saldo corrido.

**3.4 Frontend.** Sección de inventario en `AdminView` reusando el patrón de `components/gastos/`.
Vista de conteo físico optimizada para tablet.

---

## Bloque 4 — Aprobaciones con PIN de admin

**4.1 `POST /aprobaciones/verificar`** — recibe `{accion, recurso_tipo, recurso_id, pin}`, valida
contra administradores activos de la sucursal, y devuelve un **token de aprobación de un solo
uso**: JWT de 60 s con `jti` y `scope` = acción + recurso concretos. El endpoint destino lo exige
en el header `X-Approval-Token` y lo consume. El consumo es un `SET NX EX 60` sobre el `jti` en
Redis (1.2): atómico y compartido entre workers, así que un token no se puede canjear una vez por
proceso. Sin ese estado compartido, "un solo uso" sería mentira en cuanto hay más de un worker.

*Por qué token y no "el PIN viajando con la acción":* el PIN no se reenvía en cada request, el
alcance queda acotado a un recurso específico, y expira solo.

**4.2 `Aprobacion`** — bitácora: `accion`, `recurso_tipo`, `recurso_id`, `payload` (JSON del estado
previo), `solicitante_id`, `autorizador_id`, `fecha`, `sucursal_id`. Nunca se borra.

**4.3 Acciones protegidas:** cancelar pedido pagado, editar propina de un ticket ya pagado, dividir
cuenta, cerrar turno con diferencia sobre el umbral, merma/ajuste de inventario sobre el umbral,
eliminar gasto (`gastos.py:736`), y revelar métricas (Bloque 5).

**4.4 Rate limiting obligatorio** en `/aprobaciones/verificar` — si no, se convierte en un oráculo
para adivinar el PIN del administrador.

**4.5 Frontend:** componente `ApprovalGate.vue` reusando `NipKeypad.vue` (ya existe, 152 líneas).
Envuelve el botón de la acción; no cierra la sesión del cajero.

---

## Bloque 5 — Visibilidad de métricas

**5.1 Recortar al cajero.** Quitar `cajero` de `/reportes/dia/analytics` (`reportes.py:144`),
`/propinas/reporte` y `/propinas/detalle` (`propinas.py:31,121`). Conserva `/reportes/dia/tickets`
para reimprimir, **sin los agregados del día**.

**5.2 Blur real, no cosmético.** `GET /turnos/{id}/resumen` (`turnos.py:824`) y el panel de caja
devuelven `{revelado: false, ...}` con los valores monetarios **nulos** hasta que se presenta un
`X-Approval-Token` de acción `revelar_metricas`. Ocultar solo con CSS no sirve: hoy el dato viaja
en la respuesta y basta abrir DevTools en la tablet.

**5.3 `GET /metricas/operacion`** (admin) — el endpoint para decidir cuánto llevar:

- demanda por platillo y por franja horaria, segmentada por día de la semana;
- proyección de la siguiente jornada a partir de las últimas N semanas del mismo día;
- tiempos de cocina p50/p90 por platillo (viene del Bloque 2);
- tasa de cancelación, ticket promedio, y mermas del período (viene del Bloque 3).

**5.4 `GET /metricas/propinas`** (admin) — **% de propina sobre venta**:

- por mesero: `SUM(propina_efectivo + propina_tarjeta) / SUM(total)` de sus pedidos;
- agregado del turno y del rango: el % que sacó el equipo completo;
- comparación contra un benchmark configurable (hoy 10 %) con marca de quién queda fuera de rango.

El agrupamiento por `Pedido.usuario_id` ya existe en `propinas.py:55-62`; se reusa y se le añade el
denominador de venta.

---

## Bloque 7 — IVA y facturación

**7.1 Modelo.** `Pedido` += `requiere_factura` (bool, default `false`), `subtotal`, `iva`,
`tasa_iva` (Numeric, default 0.16 — congelada por pedido para que un cambio futuro de tasa no
reescriba el histórico). El `total` sigue siendo lo que se cobra: `subtotal + iva`. Las **propinas
quedan fuera de la base gravable** — se suman al cobro, nunca al subtotal.

**7.2 Dónde se aplica.** En caja, al cobrar (`PUT /pedidos/{id}` con `estado=pagado`,
`pedidos.py:811`) o en un paso previo dedicado. **No** al crear el pedido: el cliente pide factura
al final, no al sentarse. El backend recalcula siempre desde los artículos — nunca acepta el total
del cliente.

**7.3 Base de cálculo — confirmado.** Los precios de `Platillo` son **sin IVA**. Por lo tanto:

```
subtotal = Σ (precio_cobrado)          # lo que ya se cobra hoy
iva      = subtotal × tasa_iva         # 0 si requiere_factura = false
total    = subtotal + iva
```

Sin factura, `iva = 0` y `total = subtotal` — idéntico a hoy, cero cambio para el cliente que no
factura. Con factura, el cliente paga 16 % más que el de la mesa de al lado por el mismo pozole:
**es la decisión de negocio tomada, no un efecto secundario**. La UI de caja debe mostrar el
recargo antes de confirmar, para que el cajero pueda decírselo al cliente y no haya sorpresa al
imprimir el ticket.

Redondeo a 2 decimales con `ROUND_HALF_UP` sobre `Decimal`, aplicado al `iva` una sola vez sobre el
subtotal completo — nunca partida por partida, porque la suma de redondeos por línea no cuadra con
el total.

**7.4 Datos fiscales.** Campos opcionales en el pedido: `rfc`, `razon_social`, `uso_cfdi`,
`email_factura`. El sistema **no emite CFDI** (no hay PAC integrado ni está en alcance): captura
los datos y desglosa el ticket para que el contador facture. Decirlo explícitamente evita que
alguien en piso prometa una factura que el sistema no emite.

**7.5 Propagación.**

- **Cuentas divididas** (`pedidos.py:448,669`): cada cuenta hija lleva su propio flag y su propio
  desglose — uno pide factura y otro no.
- **Reportes y corte de caja:** separar venta facturada de no facturada, y subtotal de IVA. Si el
  IVA se cuenta como venta, todos los márgenes salen inflados. Toca `reportes.py:129`,
  `turnos.py:824`, `admin.py:52`, y `_calcular_movimientos_efectivo` (`turnos.py:98`).
- **Ticket impreso** (`print_service/`, `services/printService.ts`): desglose subtotal / IVA /
  propina / total.
- **Métrica de propina (5.4):** el denominador es el **subtotal sin IVA**, no el total. Si no, los
  pedidos facturados aparecen artificialmente con peor porcentaje de propina.

**7.6 Cambiar el flag después de pagado** requiere aprobación de admin (Bloque 4) — altera el monto
cobrado de un ticket cerrado.

---

## Bloque 8 — Sesiones por jornada

El problema real: `create_access_token` (`auth.py:45-55`) emite un JWT con `sub` y `exp` y nada
más. Sin `jti`, sin blacklist, **no existe forma de invalidar una sesión**. Un token vive sus 24 h
pase lo que pase, en una tablet compartida por todo el personal.

**8.1 Jornada operativa, no día natural.** Cierran pasada la medianoche, así que el día natural es
el corte equivocado. Definir la jornada de **05:00 a 05:00** con corte de sesiones a la **1:00 AM**
(`HORA_CORTE_JORNADA` configurable). `jornada_de(ts)` vive en `utils/timezone.py`, junto a
`get_mexico_now()`.

**8.2 Invalidación sin cron ni tabla de blacklist.** El JWT lleva `jornada` (la fecha de la jornada
en que se emitió) además de `sub` y `exp`. `get_current_user` (`auth.py:72`) compara la `jornada`
del token contra la jornada actual: si no coinciden, `401`. Ningún token sobrevive el corte de la
1:00 AM.

*Por qué así:* no requiere scheduler (no hay ninguno en el backend hoy, y añadir APScheduler para
esto sería sobreingeniería), no requiere tabla ni Redis, no tiene ventana de fallo si el proceso
está caído a la 1:00, y es una sola comparación en la dependencia que ya se ejecuta en cada
request. Además baja `ACCESS_TOKEN_EXPIRE_MINUTES` a un valor sano sin romper la operación, porque
el corte real ya no depende del `exp`.

**8.3 Cerrar turno NO desloguea.** Mismo hardware, mismo personal, varios turnos por jornada. La
sesión sobrevive los cierres intermedios. Lo que sí ocurre al cerrar turno: se cierran los
`RegistroAsistencia` abiertos de ese turno (2.5) y se bloquea la creación de pedidos hasta que se
abra el siguiente (ya funciona así, `pedidos.py:165-170`).

**8.4 Revocación selectiva** para cuando alguien renuncia a media jornada:
`Usuario.sesiones_validas_desde` (timestamp). Un token emitido antes de esa marca se rechaza. Se
actualiza al desactivar al usuario, al cambiarle el PIN o desde un botón de "cerrar sesión en todos
los dispositivos". Cubre el caso que la jornada no cubre.

**8.5 Frontend.** Interceptor 401 en `api/client.ts` (1.9) → limpia `localStorage` y manda al login
preservando el `device_role` de la tablet, para que el reingreso sea solo el NIP en la cuadrícula
de la sucursal, no una reconfiguración del dispositivo.

**8.6 Reautenticación al abrir turno.** Al arrancar la jornada, `POST /turnos/iniciar` exige un
token de la jornada vigente — quien quedó logueado de ayer es rechazado por 8.2 y tiene que meter
su NIP. Sale gratis del mismo mecanismo.

---

## Bloque 9 — Corte de jornada: turnos y asistencia sin cerrar

El más urgente de los bloques nuevos, porque hoy **corrompe la nómina y el corte de caja a la vez**,
y ya está pasando.

### El bug de fondo (peor que "se les olvida")

`POST /auth/asistencia` (`routers/auth.py:114-128`) usa el mismo NIP como interruptor: si hay un
registro abierto, marca **salida**; si no, marca **entrada**. No mira la fecha de ese registro
abierto.

Consecuencia real para el mesero que trabaja martes y domingos: el martes entra y olvida salir. El
**domingo llega y marca su NIP creyendo que entra** — y el sistema le da *salida del martes*, con 5
días de duración. Tiene que marcar una segunda vez para entrar de verdad. No es solo que se les
olvide cerrar: es que **el sistema convierte el olvido en un dato falso y además les roba el
check-in**. Por eso aparecen las 100 horas.

### Y el turno de caja sin cerrar bloquea la operación

El índice único parcial `idx_turno_activo_sucursal` (`models.py:278-283`) permite un solo turno
abierto por sucursal. Si nadie cierra:

- `POST /turnos/iniciar` responde `400 "Ya hay un turno activo"` (`turnos.py:179-184`) — no se
  puede abrir el día siguiente.
- Peor: el turno viejo **sigue activo**, así que los pedidos de los días siguientes se siguen
  aceptando y caen todos con el `turno_id` de anteayer (`pedidos.py:165-176`).
- `_calcular_movimientos_efectivo` filtra por `turno_id` (`turnos.py:131`), así que ese corte
  acumula tres días de ventas contra un fondo inicial de hace tres días. El arqueo resultante no
  significa nada.

### 9.1 Corte unificado de jornada

Una sola función `reconciliar_jornada(db, sucursal_id)`, **idempotente**, que ejecuta el corte de
la 1:00 AM `America/Mexico_City` (la zona ya configurada en `config.py:22` y usada por
`get_mexico_now()`). Cierra las tres cosas que quedan colgando: sesiones (Bloque 8), turnos de
caja, y registros de asistencia. Reusa `jornada_de()` del Bloque 8 — mismo concepto de corte, un
solo lugar donde vive la regla.

**Disparo perezoso, no cron.** Se invoca desde la dependencia de auth (barata: una comparación, y
solo entra a trabajar si la última reconciliación de esa sucursal es de una jornada anterior), y en
los puntos de entrada relevantes: `POST /turnos/iniciar`, `POST /auth/asistencia`, `POST /pedidos/`.
Más `POST /admin/reconciliar-jornada` manual.

*Por qué perezoso:* no hay scheduler en el backend y añadir APScheduler solo para esto es
infraestructura que puede caerse en silencio justo la noche que importa. El disparo perezoso no
puede "no correr": si nadie toca el sistema en tres días, corre en cuanto alguien entra, y **cierra
con la hora de corte que correspondía, no con la hora en que se descubrió**. Ese detalle es lo que
evita que el registro del martes se cierre el domingo. Si más adelante se quiere un cron de Railway
que pegue al endpoint manual, se suma sin cambiar nada — la función ya es idempotente.

### 9.2 Prevención (más importante que el auto-cierre)

Cerrar automáticamente repara el síntoma. Esto ataca la causa:

- **Check-in/check-out explícito, no interruptor.** Si el registro abierto es de una jornada
  anterior, **nunca** interpretarlo como salida: se cierra por corte y se registra una **entrada
  nueva**. La respuesta dice qué pasó (`"entrada"` / `"salida"`), y la UI de `ClockInView.vue` lo
  confirma en grande antes de aceptar. Elimina el doble daño de hoy.
- **Tope duro:** ningún registro puede exceder `MAX_HORAS_JORNADA` (16 h, configurable). Es la red
  por si el corte falla.
- **Quién sigue checado, visible:** en `ClockInView` (ya muestra indicadores de turno activo,
  commit `85c1caa`) y en el panel de caja.
- **Al cerrar turno de caja**, listar los registros de asistencia abiertos de ese turno y ofrecer
  cerrarlos en el mismo paso. Es el momento natural: el cajero ya está haciendo el cierre del día.
- **Aviso al abrir turno** si el anterior se cerró automáticamente: hay algo que conciliar antes de
  seguir.

### 9.3 No inventar horas

Cuando el corte cierra un registro, la hora de salida real **no se conoce**. No se adivina.

- `RegistroAsistencia` += `cierre_automatico` (bool), `requiere_revision` (bool),
  `fecha_salida_estimada`.
- Se cierra con la hora de corte, marcado `requiere_revision=true`.
- **Esas horas quedan fuera del cálculo de nómina** hasta que un admin fije la hora real. Pagar
  sobre una salida inventada es exactamente el problema que se está tratando de resolver, con otro
  disfraz.
- Cola de revisión en la sección de RRHH (`RecursosHumanosSection.vue` ya existe): "3 registros
  necesitan hora de salida", con el ajuste registrado en la bitácora de aprobaciones (Bloque 4).

### 9.4 Turno de caja auto-cerrado

- Nuevo estado `cerrado_automatico` (ampliar el `CheckConstraint chk_turno_estado`,
  `models.py:284`).
- Sin conteo final: `total_final` y `diferencia` quedan en `NULL`. **No hubo arqueo, así que no se
  fabrica un cuadre.** `ventas_efectivo` y `propinas_efectivo` sí se calculan, que son datos reales.
- Libera el índice único → el día siguiente abre normal.
- Aparece en el panel de admin como pendiente de conciliar, y el cierre manual posterior (con el
  efectivo que se haya contado) requiere aprobación (Bloque 4).

### 9.5 Limpiar lo que ya está en la base

Ya hay registros de 100 horas en producción contaminando la nómina y cualquier métrica que se
construya encima. Antes de confiar en los números:

- `GET /asistencia/anomalias` — registros abiertos, o con duración sobre el tope, o que cruzan una
  jornada.
- Marcarlos `requiere_revision` en la migración. **No borrarlos ni auto-corregirlos**: son
  registros de nómina, los corrige un humano.
- Reporte para que el admin los ajuste en lote antes de cerrar el siguiente periodo de pago.

---

## Bloque 6 — Endurecer para producción

**Crítico (va en la primera fase, no se negocia):**

- Quitar el fallback de contraseña en texto plano (`auth.py:35-38`) tras verificar en la DB que
  ningún `pin` carece de prefijo `$`.
- Rate limiting + lockout en `/auth/login-simple`, `/auth/login-admin`, `/auth/asistencia` y
  `/aprobaciones/verificar`, **con contador en Redis** (1.2) para que el límite sea real con varios
  workers. Un NIP de 4 dígitos sin límite de intentos es una puerta abierta.
- `require_roles` en `GET /usuarios/` (`users.py:37`) y auth en `GET /ws/stats`
  (`websocket_routes.py:123`).
- `GET /auth/users`: devolver solo `id` y `nombre` de la sucursal del dispositivo, no la nómina
  completa con roles.
- `/health/database`: dejar de exponer el host de la DB (`main.py:79-86`).

**Importante:**

- CORS desde env, no con la IP de LAN quemada en `main.py:38`.
- Handler global de excepciones → contrato uniforme `{"error": {"code", "message"}}`, sin filtrar
  internals.
- JWT: bajar `ACCESS_TOKEN_EXPIRE_MINUTES` (hoy 1440). La revocación la resuelve el Bloque 8.
- `DEBUG` en `config.py:10` está en `True` por defecto y no se usa en ningún lado: conectarlo o
  borrarlo.
- Dockerfile: multi-stage con `uv`, usuario no-root, `HEALTHCHECK`. Los workers pasan a `--workers
  $WEB_CONCURRENCY` (default 2), ya viable gracias al fan-out por Redis (1.2).
- `docker-compose.yml` para levantar app + Postgres + Redis con un comando.
- `/health` reporta Postgres y Redis por separado, sin exponer hosts.
- `REDIS_URL` en `Settings` (`core/config.py`), desde env como todo lo demás.

**Tests** (hoy solo existe `test_network_optimizations.py`). Mínimo, con `httpx.AsyncClient`:

- máquina de estados: transición válida + transición prohibida rechazada;
- idempotencia: POST duplicado de pedido y de agregar-artículos;
- aprobaciones: acción sin token rechazada, con token válido aceptada, token reusado rechazado;
- inventario: compra suma, venta con receta resta, cancelación devuelve;
- roles: cajero recibe 403 en analytics.

---

## Orden de ejecución

| Fase | Contenido | Por qué en este orden |
|---|---|---|
| **A** | Bloque 0 + Bloque 1 + Bloque 8 (sesiones) + **Bloque 9 (corte de jornada)** + los críticos del Bloque 6 | Deja de perder pedidos y cierra los agujeros de seguridad. Bloques 8 y 9 comparten el mismo corte de jornada, se hacen juntos. El 9 va aquí porque **hoy está corrompiendo nómina y cortes de caja cada semana** |
| **B** | Bloque 2 (tiempos + asistencia + cocina) | Sin timestamps no hay métricas que valgan; empieza a acumular datos cuanto antes. Depende del 9: sin asistencia limpia, los tiempos por cocinera no significan nada |
| **C** | Bloque 4 (aprobaciones) + Bloque 5 (visibilidad) + Bloque 7 (IVA) | El control de autoridad debe existir antes de que el inventario dependa de él. El IVA va aquí porque cambiar el flag ya cerrado exige aprobación |
| **D** | Bloque 3 (inventario) | El más grande; se apoya en aprobaciones (mermas) y en el modelo de eventos |
| **E** | Resto del Bloque 6 | Docker, tests, CORS por env |

Cada fase es desplegable por sí sola. El sistema sigue operando durante todas.

---

## Archivos críticos

**Nuevos:** `backend/app/deps.py`, `backend/app/domain/estados.py`, `backend/app/domain/jornada.py`
(corte, `reconciliar_jornada`), `backend/app/events.py`, `backend/app/core/redis.py` (cliente
`redis.asyncio`, pub/sub, rate limiting, consumo de tokens), `backend/app/routers/inventario.py`,
`backend/app/routers/aprobaciones.py`, `backend/app/routers/metricas.py`,
`frontend/pos-system/src/components/ApprovalGate.vue`, `docker-compose.yml`.

**Modificados a fondo:** `backend/app/websocket_manager.py` (registro local + suscripción al canal
de Redis), `backend/app/core/config.py` (`REDIS_URL`), `backend/app/models.py`,
`backend/app/schemas.py`,
`backend/app/routers/pedidos.py` (núcleo del Bloque 1 + IVA), `backend/app/routers/gastos.py`
(enganche de inventario), `backend/app/routers/turnos.py` (blur + venta facturada),
`backend/app/routers/asistencia.py` (rol snapshot, fechas tz, N+1), `backend/app/auth.py` (jornada
en el token), `backend/app/utils/timezone.py` (`jornada_de`), `backend/app/main.py` (lifespan,
CORS, handlers, quitar `create_all`), `backend/Dockerfile`.

**Frontend:** `views/CajaView.vue` (blur + aprobaciones + captura de factura — 4 093 líneas, buen
momento para extraer los paneles de métricas a componentes), `views/MeseroView.vue` (cola offline),
`views/KDSManager.vue` (acuse), `stores/pedidos.ts`, `api/client.ts` (interceptor 401),
`services/printService.ts` y `print_service/` (desglose de IVA en el ticket).

**Migraciones:** una de baseline + una por bloque (eventos + asistencia, inventario, aprobaciones,
IVA), respetando la cadena lineal existente desde `c4d5e6f7a8b9`.

---

## Verificación

**Por fase, antes de desplegar:**

1. `docker compose up` levanta app + Postgres + Redis; `alembic upgrade head` corre limpio **sobre
   una base vacía** y sobre un dump de producción.
2. `pytest` verde, incluidos los casos nuevos de cada bloque.

**Fase A — pedidos que no se pierden:**

- Con dos tablets de cocina, marcar artículos del mismo pedido en paralelo; el pedido debe terminar
  en `listo`, nunca atascado en `preparando`.
- Cortar la red del mesero, capturar un pedido, restaurar la red: el pedido debe llegar solo, una
  vez, sin duplicado.
- Reenviar el mismo POST con el mismo `client_request_id` 10 veces: un solo pedido.
- Intentar `pagado → pendiente` como admin sin token de aprobación: 403.
- Con la app bajo carga, confirmar que las conexiones WS del KDS ya no se cierran por timeout de
  ping.
- **Redis (1.2):** levantar con `WEB_CONCURRENCY=2`, conectar el KDS a un worker y crear el pedido
  contra el otro (forzando la ruta con dos conexiones distintas): el KDS debe recibirlo. Cada
  mensaje llega **una sola vez**, no duplicado por worker. Tumbar Redis con la app arriba: el flujo
  mesero → cocina → caja sigue funcionando (fan-out local + polling), `/health` marca Redis caído,
  y al volver Redis el fan-out entre workers se restablece sin reiniciar.
- **Token de aprobación con 2 workers:** canjear el mismo `X-Approval-Token` contra ambos en
  paralelo → exactamente uno debe pasar.

**Fase A — sesiones (Bloque 8):** con el reloj del contenedor movido a las 00:59 y luego a las
01:01, el mismo token pasa de `200` a `401`. Cerrar y reabrir turno **sin** que la sesión muera.
Desactivar a un usuario → su token deja de servir de inmediato.

**Fase A — corte de jornada (Bloque 9)** — reproducir el caso exacto del mesero de martes y
domingos:

- Check-in el martes, sin salida. Avanzar el reloj al domingo. Marcar NIP → debe registrar
  **entrada**, no salida; el registro del martes debe aparecer cerrado a la 1:00 AM del
  **miércoles** (la hora de corte que correspondía), no con la hora del domingo, y marcado
  `requiere_revision`.
- Ese registro no debe sumar horas a la nómina hasta que un admin fije la hora de salida.
- Turno de caja abierto durante 3 días: al reconciliar queda `cerrado_automatico` con `total_final`
  y `diferencia` en `NULL`, y `POST /turnos/iniciar` vuelve a funcionar.
- Llamar `reconciliar_jornada` dos veces seguidas no debe producir ningún cambio la segunda vez
  (idempotencia).
- `GET /asistencia/anomalias` debe listar los registros basura que ya existen en producción.

**Fase B — tiempos y cocina:** crear un pedido, recorrer todo el ciclo, y verificar que
`PedidoEvento` tiene la traza completa y que los tiempos por platillo cuadran con el reloj. Con dos
cocineras checadas y marcando desde KDSManager, `GET /metricas/cocina` debe atribuir cada platillo a
quien lo marcó y listar la dotación de cocina de ese día. Un check-in sin check-out debe cerrarse
solo en el corte de la 1:00 AM, no sumar 20 horas.

**Fase C — control e IVA:** cajero recibe 403 en analytics; el resumen del turno llega con los
montos en `null` hasta presentar el token; un token de aprobación reusado es rechazado; cada acción
aprobada deja registro con autorizador. Cobrar un pedido de $1 000 con factura → total $1 160, con
`subtotal` 1 000 e `iva` 160; la propina se suma aparte y **no** entra en la base gravable. El
**mismo** pedido sin factura → total $1 000, `iva` 0: el cliente que no factura paga exactamente lo
de hoy. Dividir esa cuenta con una mitad facturada y otra no. Verificar que el corte de caja
reporta la venta facturada separada y que el margen no se infla con el IVA.

**Fase D — inventario:** registrar una compra de 10 kg de maíz → stock +10. Vender y cobrar 20
pozoles con receta de 0.18 kg → stock 6.4. Cancelar uno de esos pedidos pagados → el stock se
devuelve. Conteo físico con diferencia → movimiento de ajuste con el motivo capturado.
`GET /inventario/reorden` lista lo que está bajo el punto de reorden.

**Validación en piso:** un servicio completo real con la fase desplegada, contrastando el corte de
caja del sistema contra el conteo manual antes de dar por buena cada fase.
