# SA — Panel de administración útil

**Rama base:** `main` · **Abierto:** 2026-10-17 · **Estado:** 🔵 en curso

Documento vivo de un sprint que se trabaja en varias sesiones. Objetivo: que el panel de admin
responda preguntas de negocio reales — cuánto vendí **de qué** cada día, cuánto entró en
**efectivo vs tarjeta**, cuánto compré y a quién — con números correctos en hora de Aguascalientes.

**Al abrir una sesión:** leer *Decisiones* → ir al *TODO* → tomar la primera tarea ⚪ del PR
en curso → marcarla 🔵. **Al cerrar una tarea:** marcarla 🟢 con fecha y PR, y agregar una fila
a la *Bitácora*. **Al cerrar un PR:** verificar en producción con agent-browser contra la
sección *Auditoría* (la evidencia "antes" está ahí).

Estados: ⚪ pendiente · 🔵 en curso · 🟢 cerrado · 🔴 bloqueado · ⏭️ pospuesto

---

## 1. Auditoría (2026-10-17, producción + código)

Hecha con agent-browser sobre `lahidrocalida.vercel.app` (admin "Claudio") y lectura del código.
Hora local al auditar: sábado 2026-10-17 12:18 (America/Mexico_City, UTC-6).

### 1.1 Fechas y zona horaria — el desfase que se nota

| # | Hallazgo | Evidencia |
|---|---|---|
| F1 | `/admin/analytics` y `/admin/analytics/advanced` filtran y agrupan con `func.date(Pedido.fecha_creacion)` → **día UTC**. La sesión de Neon corre en UTC (no se fija `timezone` en `db/session.py` ni `TZ` en Docker). Todo lo vendido después de las 18:00 locales cae en el día siguiente. | `admin.py:68-110, 214-218, 317-343`. En prod, "Hoy" (17-oct a las 12:18, restaurante cerrado) mostraba **$5,802 / 18 pedidos**: eran las ventas de la noche del 16. |
| F2 | `ventas_por_hora` usa `extract("hour", fecha_creacion)` en UTC. | Respuesta real: horas 0-5 y 21-23. El restaurante opera ~14:00–00:30 local. |
| F3 | `/admin/dashboard`, `/admin/reportes/semanal`, `/admin/gastos/resumen`, timeline de `/gastos/analiticas/resumen` y `/platillos/ordenados-popularidad` también usan `func.date` / `date.today()`. | `admin.py:470-548, 644-664, 917`, `gastos.py:624-626, 662-665`, `products.py:61,74`. |
| F4 | Frontend arma fechas con `new Date().toISOString().split('T')[0]` (fecha **UTC**): después de las 18:00 "Hoy" manda mañana. | `DashboardSection.vue:384-385, 423-424`, `TurnosSection.vue:125-129`, `RecursosHumanosSection.vue:380-397`. |
| F5 | `GastoFormModal.vue:206` precarga `fecha_gasto` con hora UTC en un `datetime-local` → el gasto se guarda **6 h en el futuro**. | Editar sí aplica offset (L304-306). |
| F6 | Existe el helper de jornada (`jornada_de`, `rango_jornada`, corte 05:00) pero **ningún reporte lo usa**. `settings.TIMEZONE` nunca se lee. | `utils/timezone.py`, `core/config.py:30`. |
| F7 | Semana del dashboard = Lun–Dom; backend semanal/proyección = Mar–Dom. "Semana pasada" de RRHH = ventana móvil 13→7 días. | `DashboardSection.vue:411-414`, `RecursosHumanosSection.vue:401-403`. |

### 1.2 Dinero mal sumado

| # | Hallazgo | Evidencia |
|---|---|---|
| D1 | Top platillos y ventas por categoría calculan `cantidad * precio_cobrado`, pero `precio_cobrado` **ya es total de línea** (`precio * cantidad`). Ingreso por platillo inflado cuando cantidad > 1. | `admin.py:228, 243` vs `pedidos.py:226, 1364, 1591`. |
| D2 | Split por montos (`/dividir_por_montos`) crea hijos **sin artículos**; los artículos quedan en el padre `dividido` → esos platillos desaparecen de todo reporte por platillo. | `pedidos.py:797-813`. |
| D3 | Pedidos Uber terminan en `entregado_repartidor`, nunca `pagado` → no existen para `/admin/*`. | Solo Caja los muestra. |
| D4 | Agregar artículos a un pedido `entregado` resetea `fecha_creacion` → mueve la venta de hora/día y acorta "tiempo de servicio". | `pedidos.py:1407-1411`. |
| D5 | Propina en efectivo sobre pago con tarjeta no entra al efectivo esperado del turno (se condiciona por `metodo_pago`). `/propinas` suma sin condicionar → dos verdades. | `turnos.py:116-123`, `admin.py:500-505`, `reportes.py:203-209`. |
| D6 | Total del dashboard (efectivo+tarjeta+transferencia) vs conteo de pedidos (incluye método NULL/otro) → ticket promedio sesgado. `metodo_pago` es `String(20)` libre. | `admin.py`, `schemas.py:139,152,159`. |

### 1.3 Dashboard — rótulos que mienten

- `:trend="12"` hardcodeado: siempre "+12%" (`DashboardSection.vue:67`).
- "Incluye propinas e impuestos": falso, suma `Pedido.total` y propinas van aparte (`total_propinas` viene en la respuesta y nunca se muestra).
- No hay KPI de efectivo vs tarjeta; solo una dona escondida en la pestaña "Pago". Datos reales semana 12–18 oct: efectivo $10,106 (34) · tarjeta $13,136 (42).
- Top platillos limitado a 10. No se puede responder "¿cuántos pozoles verdes vendí?".
- Proyección "7 días" devuelve 6, con días en inglés ("Tuesday").
- Filtro de pago "Transferencia" también filtra `Gasto.metodo_pago` (enum sin ese valor) → probable 500 (`admin.py:81-89`).
- Escribir fechas a mano no apaga el toggle activo (`DashboardSection.vue:45-47`).
- Sin `onActivated`: con keep-alive las fechas quedan congeladas desde el primer montaje.

### 1.4 Gastos

| # | Hallazgo | Evidencia |
|---|---|---|
| G1 | **Filtro de Catálogo roto.** `<select>` emite string `"4"`, el filtro compara `a.categoria_id === "4"` contra número `4` → lista vacía. "Todas" emite el texto de la opción → también vacía. | Verificado en prod: 90 artículos → 0 al elegir "lacteos". `ArticulosView.vue:179-186`, `GastosSection.vue:156-157`. Mismo bug en `ComprasView.vue:77-82,138-139`. |
| G2 | **"TOTAL EN VISTA $0105.01191.97"**: suma con `+` sobre strings (Numeric serializa como string) → concatena. Además solo suma la página actual. | Verificado en prod. `GastosHistorial.vue:322-324`. |
| G3 | Tras guardar gasto/proveedor/artículo, Historial y Resumen no se recargan (keep-alive, `handleGastoSaved` solo cierra modal). | `AdminView.vue:224-227`, `GastosSection.vue:184-213`. |
| G4 | Historial no expone filtros que el backend ya acepta: `tipo_gasto`, `metodo_pago`, `categoria_id`. Fotos de tickets (adjuntos) no se ven en la lista. | `gastos.py:485-495`. |
| G5 | `ArticulosView.vue:200` hace `a.categoria.nombre` → crashea si un artículo no tiene categoría. | |
| G6 | **Problema de fondo — captura:** solo **10 gastos** registrados de junio a octubre; 2 en octubre ($296.98); **0 con foto**. Con ventas de ~$23k/semana, la "Utilidad neta $22,945" es ficción. Ninguna analítica de compras sirve hasta que se capture. | `GET /gastos/?fecha_inicio=2026-06-01…` |

### 1.5 Barra lateral / Compras

- "Compras" en el sidebar hace `router.push('/compras')` y **saca del layout de admin** (`AdminView.vue:125-128`). Sus pestañas Historial/Proveedores/Artículos/Categorías son los mismos componentes que Gastos; solo agrega "Registrar".
- La tarjeta "Compras" del Hub lleva a `/rapido`; el sidebar a `/compras` → dos entradas distintas para lo mismo.
- Código muerto: `components/gastos/GastosSection.vue` + `components/gastos/GastosView.vue` (solo se importan entre sí).

### 1.6 Turnos

- "Total ventas" del resumen = suma de `ventas_efectivo` solamente (`TurnosSection.vue:148-150`). Sin tarjeta, Uber ni propinas, aunque `GET /turnos/{id}/resumen` ya trae el desglose (solo lo usa Caja).
- Discrepancias grandes pasan desapercibidas: turno #225 cerró con total final = fondo ($1,273), discrepancia **−$3,697**. Total semana −$3,286.51.
- Pedido abierto en turno A y cobrado en turno B cuenta en A (ya cerrado) — `turno_id` solo se reasigna si es NULL (`pedidos.py:257, 987`).
- `editar_turno` recalcula `diferencia` sin restar gastos (`turnos.py:782-784`), distinto al cierre.
- `if turno.total_final` convierte 0 en `—` (`turnos.py` ~L595).
- Petición `/turnos/` duplicada y solo `estado=cerrado` (no se ve el turno abierto).
- **Flujo real confirmado (no es bug):** el cajero cierra ~00:04 y abre el siguiente ~00:05 para dejar contado el fondo (turnos #220–#226).

### 1.7 Recursos Humanos

- 15 anomalías abiertas. `reconciliar_jornada` deja `fecha_salida = NULL` + `fecha_salida_estimada` (05:00) + `requiere_revision` → esas horas cuentan **0** (`asistencia.py:146-153`).
- `/auth/asistencia` (sin JWT) no llama `reconciliar_jornada`; con un registro de ayer abierto, el índice único parcial dispara `IntegrityError` y el fallback devuelve el registro de ayer en vez de crear entrada (`routers/auth.py:198-214`).
- Comentarios/docs desactualizados: `turnos.py:190` y `ESTADO_ACTUAL.md:282` dicen que los turnos se auto-cierran (se quitó en `7a3bb52`).
- Filtro de rol solo Cocina/Meseros; cajeros y compras solo en "Todos".

### 1.8 Datos sucios

- Platillo `"Coca Regular\t"` (tab al final).

---

## 2. Decisiones

| Fecha | Decisión | Motivo |
|---|---|---|
| 2026-10-17 | **Turnos de caja NO se auto-cierran.** | El cajero cierra ~00:04 y abre el siguiente de inmediato para dejar el fondo contado; un auto-cierre mataría ese turno (por eso se quitó en `7a3bb52`). |
| 2026-10-17 | **Asistencia sí se auto-cierra:** todo empleado sin salida después de las **00:30** hora Ags recibe `fecha_salida = 00:30` de esa noche, marcado `cierre_automatico`. | Las anomalías hoy dejan horas en 0 y ensucian RRHH. 00:30 es la hora real de salida. |
| 2026-10-17 | **"Día" en toda analítica = jornada 05:00→05:00 hora Ags** (`jornada_de` / `rango_jornada`). | Una venta a las 00:20 pertenece a la noche anterior. No depende de que el cajero cierre bien el turno. |
| 2026-10-17 | La venta se fecha por **`fecha_pago`**, no `fecha_creacion`. | El dinero entra al cobrar; `fecha_creacion` además se resetea (D4). |
| 2026-10-17 | "Ventas" **no incluye propinas**; propinas se muestran aparte, desglosadas efectivo/tarjeta. | Las propinas no son ingreso del restaurante. |
| 2026-10-17 | Auto-cierre de asistencia es **perezoso** (sin cron). | Caja/KDS hacen polling cada 5 s; y el valor (00:30) es determinista aunque se aplique tarde. Menos infraestructura. |

---

## 3. TODO

Orden de PRs = orden de ejecución. Cada PR: rama `sa/prN-…`, test happy path + 1 error,
`pnpm run build` limpio, verificación en prod con agent-browser.

### PR1 — Fechas y dinero correctos · 🟢 código listo y verificado en local (2026-10-17) — falta verificar en prod tras deploy

| Estado | Tarea | Archivos |
|---|---|---|
| 🟢 | ~~Helper SQL `jornada_sql`~~ → **desviación:** se filtra por rango `[inicio, fin)` con `rango_jornadas` y se agrupa en Python con `jornada_de`. Sin funciones SQL de zona horaria, así la suite (SQLite) y prod (Postgres) dan lo mismo. Helpers nuevos: `jornada_actual`, `rango_jornadas`, `semana_hidrocalida`, `DIAS_ES`. | `utils/timezone.py` |
| 🟢 | Reemplazar `func.date`/`date.today()` en analytics, advanced, proyección, dashboard, semanal, gastos/resumen, timeline y categorías de `/gastos/analiticas/resumen`, y popularidad. Horas en hora local, ordenadas por jornada (05→23, 00→04). Rango de `/gastos/` y `/gastos/analiticas/resumen` ahora también por jornada. | `admin.py`, `gastos.py`, `products.py` |
| 🟢 | Ventas filtradas y agrupadas por `coalesce(fecha_pago, fecha_creacion)`. | `admin.py` (`VENTA_TS`) |
| 🟢 | Quitar `cantidad *` (D1). | `admin.py` |
| 🟢 | Filtro "transferencia" no se aplica a gastos. | `admin.py` |
| 🟢 | `utils/fecha.ts` (`hoyJornada`, `rangoSemana`, `rangoMes`, `rangoAnio`, `rangoUltimosDias`, `datetimeLocalAhora`) + 11 tests; reemplaza todo `toISOString().split('T')` en Dashboard, Turnos, RRHH, GastosDashboard y GastosHistorial; default de `GastoFormModal` en hora local. | `utils/fecha.ts`, secciones admin |
| 🟢 | Quitar "+12%" fijo, rótulo de ventas corregido, proyección con días en español, el toggle pasa a "custom" al editar fechas, `onActivated` recalcula, "Semana" = Mar→Dom. | `DashboardSection.vue`, `admin.py` |
| 🟢 | Tests: 23:50 y 00:20 en la misma jornada; "hoy" no incluye anoche; D1; horas locales; proyección en español; transferencia con gastos; rango inválido 422 / formato 400 / rango > 731 días 422; semana Mar→Dom. | `tests/test_admin_analytics.py` |
| ⚪ | Verificar en prod con agent-browser tras deploy (checklist de la sección 4). | — |

**Hallazgos durante PR1:**
- Bug heredado: `_get_week_range` hacía martes+**6** (= lunes) y la llamaba "Mar→Dom". Ahora martes+5. Semanal y `/gastos/resumen` por defecto cubrían un día de más.
- La proyección sigue siendo de 6 días (Mar→Dom, el lunes no opera); la clave `proximos_7_dias` se conserva por compatibilidad.
- El `Pedido.total` sigue sin incluir propinas; el rótulo ahora lo dice.
- Pendiente de PR3/PR5 (no tocado aquí): Uber no entra a analytics; el dashboard `/admin/dashboard` sigue condicionando propinas por método (D5).

### PR2 — Salida automática de asistencia a las 00:30 · 🟢 código listo y verificado en local (2026-10-17) — falta aplicar backfill en prod

| Estado | Tarea | Archivos |
|---|---|---|
| 🟢 | Regla nueva en `reconciliar_jornada`: registro abierto → `fecha_salida = 00:30` de la madrugada que cierra su jornada, `cierre_automatico=True`, sin `requiere_revision` (cuenta para horas). Función pura `salida_automatica(entrada)`; `ahora` inyectable. Determinista: da igual cuándo corra la reconciliación. Turnos de caja no se tocan. | `services/jornada.py` |
| 🟢 | Lo que la regla no cubre sigue siendo anomalía (sin inventar hora): entrada con >16 h de turno (p. ej. 06:00), <1 h antes del corte (p. ej. 00:06) o posterior al corte. | `services/jornada.py` |
| 🟢 | `/auth/asistencia` llama a `reconciliar_jornada` antes de decidir entrada/salida (cierra el `IntegrityError` que devolvía el registro de ayer). | `routers/auth.py` |
| 🟢 | **Guard extra (no estaba en el plan):** si entre 00:30 y 05:00 el empleado checa y ya tiene la salida automática de esa noche, se le devuelve esa salida en vez de abrir una entrada fantasma que luego sería anomalía. | `routers/auth.py` |
| 🟢 | Backfill de anomalías existentes: `scripts/backfill_salidas_0030.py` (dry-run por defecto, `--apply` escribe, idempotente). | `scripts/`, `services/jornada.py` |
| 🟢 | RRHH: etiqueta "Automática" en la salida, "Sin salida · revisar" (rojo) en vez de "En Turno" para anomalías, filtros Caja y Compras. ("Semana pasada" y fechas locales ya salieron en PR1.) | `RecursosHumanosSection.vue` |
| 🟢 | Comentarios/docs obsoletos corregidos (`turnos.py`, `ESTADO_ACTUAL.md`, `SPRINTS.md`). | |
| 🟢 | Tests: 10 nuevos (`test_asistencia_salida_automatica.py`) + 3 existentes fijados a 06:00 (dependían de la hora del reloj). | `tests/` |
| ⚪ | **En prod:** tras el deploy, correr `uv run python scripts/backfill_salidas_0030.py` con `DATABASE_URL` de prod, revisar el dry-run y luego `--apply`. Confirmar con Leo antes. | — |

**Hallazgos durante PR2:**
- La suite en Postgres tiene **11 fallos preexistentes en `main`** (dividir cuenta, PIN de admin, turno_diferencia, adjuntos): mismos con y sin estos cambios. En SQLite todo pasa. Ver *Limpieza*.
- En Postgres los datetimes vuelven con tz; en SQLite naive. Los tests deben usar `to_mexico_aware`, no `.replace(tzinfo=…)`.
- Entradas pegadas a medianoche (p. ej. Monica 00:06 del 4-oct) no se auto-cierran: se dejan a revisión humana por tener <1 h.

### PR3 — Ventas por producto y por día · ⚪

El pedido central: "cuántos pozoles verdes, cuántos tamales, por día y en rangos".

| Estado | Tarea | Archivos |
|---|---|---|
| ⚪ | `GET /admin/analytics/productos?fecha_inicio&fecha_fin&agrupar=dia\|total&categoria=` → por platillo: categoría, unidades, ingreso, precio promedio, y por jornada. Incluye `pagado` + Uber + hijos de split; excluye padres `dividido` salvo split por montos (sus artículos se atribuyen al padre, D2). Filtra por `sucursal_id` del usuario. | `admin.py` (o `routers/analytics.py`), `schemas.py` |
| ⚪ | Vista "Ventas por producto": tabla completa con buscador, filtro de categoría, totales por categoría, matriz producto × día, export CSV. | `components/admin/sections/` nuevo |
| ⚪ | KPIs de dinero arriba del dashboard: Ventas · Efectivo · Tarjeta · Transferencia · Uber · Propinas (ef./tarj.) · # tickets · ticket promedio, con comparación vs periodo anterior equivalente (reemplaza el +12%). | `DashboardSection.vue`, `admin.py` |
| ⚪ | Timeline diario apilado efectivo/tarjeta/transferencia. | `DashboardSection.vue` |
| ⚪ | Tests del endpoint (rango con split, Uber y cantidad > 1) + error de `agrupar` inválido. | `tests/` |

### PR4 — Gastos rediseñado + fuera Compras del sidebar · ⚪

| Estado | Tarea | Archivos |
|---|---|---|
| ⚪ | Quitar "Compras" del sidebar y del `selectTab`. Borrar `components/gastos/GastosSection.vue` y `GastosView.vue`. Unificar entrada del Hub. | `AdminSidebar.vue:34-43`, `AdminView.vue:125-128`, `AdminHub.vue:47` |
| ⚪ | Arreglar filtro de Catálogo (G1) con `v-model.number` / `Number(v) \|\| null`; guard de `a.categoria` (G5). Mismo fix en `ComprasView.vue`. | `ArticulosView.vue`, `GastosSection.vue`, `ComprasView.vue` |
| ⚪ | Historial: total del filtro calculado en servidor (`suma_total` en la respuesta paginada), no concatenado (G2). | `gastos.py:485`, `GastosHistorial.vue:322` |
| ⚪ | Historial como lista de tickets: miniatura del adjunto, proveedor, total, método, tipo; filtros fecha/proveedor/tipo/método/categoría y toggle Hoy/Semana/Mes. | `GastosHistorial.vue` |
| ⚪ | Refrescar Historial/Resumen al guardar (G3). | `AdminView.vue`, `GastosSection.vue` |
| ⚪ | Analítica de compras por jornada: por proveedor, categoría y artículo (cantidad y costo). | `gastos.py`, `GastosDashboard.vue` |
| ⚪ | Alerta "N días sin compras registradas" en dashboard (ataca G6). | `DashboardSection.vue` |
| ⚪ | Tests: total del filtro, filtro por categoría. | `tests/` |

### PR5 — Turnos útil · ⚪

| Estado | Tarea | Archivos |
|---|---|---|
| ⚪ | Tarjeta por turno con desglose de `/turnos/{id}/resumen`: efectivo, tarjeta, Uber, propinas, gastos, esperado vs contado; discrepancia en rojo si \|dif\| > $100. Mostrar también el turno abierto. | `TurnosSection.vue`, `schemas.py:411-431` |
| ⚪ | Resumen superior: total real (no solo efectivo), discrepancia acumulada. | `TurnosSection.vue:148` |
| ⚪ | Pedido cobrado en otro turno se atribuye al turno donde se cobró. | `pedidos.py:987` |
| ⚪ | `editar_turno` resta gastos igual que el cierre; `total_final = 0` no se convierte en `—`. | `turnos.py:782, ~595` |
| ⚪ | Propina en efectivo cuenta al efectivo esperado sin importar método de pago (D5). | `turnos.py:116-123`, `admin.py:500`, `reportes.py:203` |
| ⚪ | Tests de cierre con propina efectivo sobre tarjeta. | `tests/` |

### Limpieza · ⚪

| Estado | Tarea |
|---|---|
| ⚪ | Arreglar los 11 tests que fallan en Postgres desde antes del sprint (`test_dividir_cuenta`×3, `test_pedidos_transiciones`×3, `test_pin_autorizacion`×2, `test_turno_diferencia`×2, `test_gasto_adjuntos`×1) y correr la CI contra Postgres. |
| ⚪ | Migración de datos: `trim` de nombres de platillos (`"Coca Regular\t"`). |
| ⚪ | No resetear `fecha_creacion` al agregar artículos (D4) — evaluar si algo depende de ello (KDS). |
| ⚪ | Actualizar `ESTADO_ACTUAL.md` y fila SA en `SPRINTS.md` al cerrar. |

---

## 4. Verificación por PR

- Backend: `cd apps/backend && uv run pytest`.
- Frontend: `cd apps/frontend && pnpm run build`.
- Local: `docker compose up`.
- Producción (agent-browser, sesión propia, admin Claudio):
  - PR1: "Hoy" antes de las 14:00 no muestra la noche anterior; horas del gráfico entre 14 y 00; dinero de top platillos = suma de `precio_cobrado`.
  - PR2: después de las 00:30, anomalías ≈ 0 y horas > 0 para quien no marcó salida.
  - PR3: "Pozole Verde" de la semana coincide con un conteo manual por SQL.
  - PR4: elegir "lacteos" en Catálogo lista artículos; total del historial es un número válido; no hay "Compras" en el sidebar.
  - PR5: suma de turnos = ventas del rango en el dashboard.

---

## 5. Bitácora de sesiones

| Fecha | PR | Qué se hizo | Hallazgos nuevos |
|---|---|---|---|
| 2026-10-17 | — | Auditoría en prod + código; documento de sprint. | Ver sección 1. |
| 2026-10-17 | PR1 | Rama `sa/pr1-fechas-dinero`: jornada 05:00→05:00 en todos los reportes de admin, D1, helpers de fecha en frontend. Backend 196 tests, frontend 65 tests + build OK. | Semana Mar→Dom estaba mal por 1 día (ver PR1). |
| 2026-10-17 | PR2 | Rama `sa/pr2-asistencia-0030` (apilada sobre PR1): salida automática 00:30, guard anti-entrada-fantasma, backfill, RRHH. Backend 206 tests (SQLite) y sin regresiones en Postgres; verificado en local con Agent Browser. | 11 tests ya fallaban en Postgres en `main`. |

## Notas de cierre

_(llenar al cerrar el sprint)_
