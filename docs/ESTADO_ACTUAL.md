# La Hidrocálida POS — Estado actual del sistema

**Última revisión:** 2026-08-25 · rama `v2/sprint-3-jornada` · **Sprint 1 "Fundaciones" (🟢), Sprint 2 "Fiabilidad de pedidos" (🟢) y Sprint 3 "Jornada y sesiones" (🟢) completos** (ver detalle y notas de cierre en [SPRINTS.md](./SPRINTS.md)). Deuda pendiente para triage: `ACCESS_TOKEN_EXPIRE_MINUTES=1440` sin refresh token; JWT en `localStorage` del frontend (expuesto a XSS); CI de backend corre sobre SQLite in-memory, no Postgres (env vars muertas); comentario desactualizado en `models.py:95` y falta `CheckConstraint` en `pedidos.estado`; `pedidos.py` mezcla endpoints `async def` con queries síncronas de SQLAlchemy (migración a AsyncSession/asyncpg, fuera de alcance de S2).

Este documento describe **cómo funciona el sistema hoy**, con sus defectos incluidos. Lo que se va
a construir está en [PLAN_V2.md](./PLAN_V2.md), y el avance por sprints en
[SPRINTS.md](./SPRINTS.md).

---

## 1. Qué es

POS para pozolería en producción. Flujo: **mesero toma orden → cocina prepara → cajero cobra**.
Cinco roles con interfaces dedicadas, tiempo real por WebSocket, PWA instalable en tablets y
pantallas de cocina, e impresión térmica desde un servicio local.

- Frontend: https://lahidrocalida.vercel.app (Vercel, CI/CD por push a GitHub)
- Backend: Docker → Railway (migrado de Koyeb el 2026-08-24, S0)
- DB: PostgreSQL en Neon Cloud, instancia nueva en AWS us-east-2 (la de Azure, deprecada, está apagada)

---

## 2. Stack

| Capa | Tecnología | Versión |
|---|---|---|
| Frontend | Vue 3 + TypeScript | 3.5.21 / 5.8.3 |
| CSS | Tailwind CSS | 4.1.13 |
| Estado | Pinia | 3.0.3 |
| Router | Vue Router | 4.6.3 |
| HTTP | Axios | 1.12.2 |
| Charts | Chart.js + vue-chartjs | 4.5.1 / 5.3.3 |
| Build | Vite | 7.1.7 |
| PWA | vite-plugin-pwa | 1.2.0 |
| Backend | FastAPI | 0.117.1 |
| ORM | SQLAlchemy (**síncrono**, psycopg2) | 2.0.43 |
| Migraciones | Alembic | 1.13.2 |
| Auth | JWT HS256 (python-jose) + Argon2 | — |
| WebSocket | websockets | 11.0.3 |
| Paquetes | pnpm (front) · uv (back) | — |

> El backend usa SQLAlchemy **síncrono** dentro de endpoints `async def`. Es una desviación
> consciente del estándar del equipo (async end-to-end) y hoy es la causa de los timeouts de
> WebSocket. Se corrige en el Bloque 1 del plan v2.

---

## 3. Estructura del repo

```
lahidrocalida-rp/
├── README.md
├── AGENTS.md                   # Guía de contribución
├── package.json                # Root monorepo (pnpm workspace)
├── pnpm-workspace.yaml         # Apunta a apps/frontend
├── docker-compose.yml          # app + Postgres, dev local reproducible
├── .github/
│   └── workflows/
│       ├── backend-ci.yml      # uv sync + ruff + pytest en cada push a apps/backend/**
│       ├── frontend-ci.yml     # pnpm + vue-tsc + build en cada push a apps/frontend/**
│       └── security-sast.yml   # Gitleaks cada lunes + push a main; alerta Telegram
├── docs/
│   ├── ESTADO_ACTUAL.md        # Este archivo
│   ├── PLAN_V2.md              # Plan de la siguiente versión
│   └── SPRINTS.md              # Tablero de avance por sprint
└── apps/
    ├── backend/
    │   ├── app/
    │   │   ├── main.py             # App init, CORS, /health
    │   │   ├── models.py           # 14 modelos ORM (332 lín)
    │   │   ├── schemas.py          # Pydantic (449 lín)
    │   │   ├── auth.py             # JWT + hashing (121 lín)
    │   │   ├── websocket_manager.py / websocket_routes.py
    │   │   ├── core/{config.py, cache.py}
    │   │   ├── db/session.py
    │   │   ├── utils/timezone.py
    │   │   └── routers/            # 10 routers, 5 313 líneas
    │   ├── alembic/versions/       # 1 migración baseline (colapsada de 6, S0)
    │   ├── alembic.ini
    │   ├── tests/                  # pytest — solo test_network_optimizations.py
    │   ├── pyproject.toml          # uv project + ruff config + pytest config
    │   ├── uv.lock
    │   ├── .env.example
    │   └── Dockerfile              # multi-stage, usuario no-root, healthcheck
    ├── frontend/
    │   └── src/
    │       ├── views/              # 9 vistas (8 712 líneas)
    │       ├── components/         # ~30 componentes
    │       └── stores/ services/ api/ router/ utils/ types.ts
    └── print-service/              # Servicio impresora térmica (Windows → rewrite Go pendiente)
```

Tamaño de los routers: `pedidos.py` 1 464 · `turnos.py` 965 · `admin.py` 880 · `gastos.py` 752 ·
`reportes.py` 325 · `products.py` 210 · `auth.py` 198 · `propinas.py` 197 · `asistencia.py` 180 ·
`users.py` 141.

---

## 4. Modelo de datos

14 tablas en `backend/app/models.py`:

| Tabla | Propósito | Notas |
|---|---|---|
| `sucursales` | Sucursal | Clave de aislamiento (`sucursal_id`) |
| `usuarios` | Staff | `pin` con Argon2; soft delete vía `activo` |
| `platillos` | Menú | `kds_name`, `estado` (disponible/no_disponible) |
| `pedidos` | Órdenes | `numero_display`, `total`, `estado`, `metodo_pago`, propinas, `tipo_orden`, `turno_id`, `client_request_id`, `parent_pedido_id` |
| `articulos_pedido` | Líneas de orden | `estado_item`; **sin timestamps propios** |
| `proveedores` | Proveedores | |
| `categorias_articulo` | Categorías de gasto | |
| `articulos` | Insumos | `unidad`, `costo_estandar`; **sin stock** |
| `gastos` | Cabecera de compra | `tipo_gasto`, `metodo_pago`, `turno_id` |
| `gasto_detalles` | Líneas de compra | |
| `nomina_detalles` | Pago de nómina por empleado | Gasto tipo `nomina`, sin proveedor |
| `turnos` | Turno de caja | Índice único parcial: 1 turno `abierto` por sucursal |
| `turno_denominaciones` | Conteo de efectivo | Tipo inicial/final |
| `registros_asistencia` | Check-in/out | **Sin `sucursal_id`, `turno_id` ni snapshot de rol** |

**Relaciones clave:** `Turno → Pedido` y `Turno → Gasto` (el turno es la unidad contable, no la
fecha); `Pedido → ArticuloPedido` y `Gasto → GastoDetalle` con cascade delete.

**Lo que no existe:** stock ni movimientos de inventario, relación platillo→insumo (BOM), campos
fiscales (`subtotal`/`iva`/`rfc`), bitácora de eventos de pedido, tabla de aprobaciones.

---

## 5. Endpoints

### `/auth`
| Método | Ruta | Auth |
|---|---|---|
| POST | `/auth/login-simple` — login staff (`user_id` + `pin`) | — |
| POST | `/auth/login-admin` — admin (payload legado `email`/`password`) | — |
| POST | `/auth/asistencia` — check-in/out público con PIN | — |
| POST | `/auth/login` — OAuth2 form | — |
| GET | `/auth/me` | Bearer |
| GET | `/auth/users` — lista para el selector de login | **sin auth** |

### `/pedidos` (núcleo, 1 464 líneas)
`POST /` · `GET /` · `GET /{id}` · `PUT /{id}` (estado) · `PUT /{id}/agregar-articulos` ·
`PUT /{id}/actualizar-articulos` · `PUT /articulos/{id}` (estado de ítem) · `POST /{id}/dividir` ·
`POST /{id}/dividir_por_montos` · `POST /{id}/imprimir`.

**Estados:** `pendiente → preparando → listo → entregado → cuenta_solicitada → pagado`, más
`cancelado` y `dividido`.

**Transiciones por rol** (hoy es una whitelist rol→destino; **no valida el estado de origen**):
mesero `entregado`/`cuenta_solicitada` · cocina `preparando`/`listo` · cajero `pagado`/`cancelado` ·
admin cualquiera.

### Resto
- `/usuarios` — CRUD (el `GET` no valida rol)
- `/platillos` — CRUD + `PATCH /{id}/disponibilidad` + `/ordenados-popularidad`
- `/turnos` — `iniciar`, `activo`, `{id}/resumen`, `{id}/cerrar`, `historial`
- `/gastos` — CRUD de gastos, proveedores, categorías, artículos; nómina por tanda
- `/propinas` — `/reporte`, `/detalle`
- `/reportes` — `/dia/tickets`, `/dia/analytics`
- `/asistencia` — `/`, `/usuario/{id}`, `/resumen` (solo admin)
- `/admin` — `/analytics` por rango
- WS `/ws/{client_type}?token={JWT}` (**el JWT completo queda en los logs de acceso, ver §12**) ·
  `GET /ws/stats` (**sin auth**)
- `/health`, `/health/database`

---

## 6. Roles

| Rol | Frontend | Backend |
|---|---|---|
| `mesero` | `/mesero` | Crear pedidos, agregar ítems, marcar entregado |
| `cajero` | `/caja` | Cobrar, propinas, reportes del día, turnos |
| `cocina` | `/kds-view`, `/kds-manager` | Marcar preparando/listo, toggle disponibilidad |
| `administrador` | Todo | Lo anterior + usuarios, analytics, dividir cuenta |
| `compras` | `/compras` | Gestión de gastos y compras |

Los checks de rol están **inline en cada endpoint** (~30 repeticiones) con cuatro helpers
duplicados: `_ensure_admin_access` (admin), `_ensure_admin` (asistencia), `_validar_permisos_turnos`
(turnos), `_ensure_can_manage_gastos` (gastos). Ya divergen entre sí.

---

## 7. Flujo operativo de una orden

```
1. Mesero → MeseroView, arma el carrito (modal de variantes para Pozole)
2. POST /pedidos/ → estado "pendiente"
   └── backend valida turno activo → inyecta turno_id (sin turno: 400)
   └── WebSocket → KDS y Caja
3. Cocina ve la orden en KDSView (pantalla grande, solo lectura)
4. KDSManager (tablet): Preparando → Listo por ítem
   └── WebSocket → Mesero y Caja
5. Mesero marca "entregado" (bebidas se marcan aparte, no se auto-entregan)
6. Mesero solicita cuenta → "cuenta_solicitada"
   └── auto-imprime ticket (print_service:3001)
7. Cajero cobra: método de pago, propina, cambio en efectivo
   └── admin puede dividir cuenta (por artículos o por montos)
8. Orden → "pagado" → WebSocket a todos → entra en analytics del día
```

---

## 8. Tiempo real (WebSocket)

`src/services/websocket.ts` — reconexión con backoff exponencial (3 s → 30 s máx), integrado con
`visibilitychange` y `online`, heartbeat cada 30 s.

**Eventos:** `pedido_created`, `pedido_estado_changed`, `articulo_estado_changed`,
`connection_established`.

**Backend** (`websocket_manager.py`): broadcast por tipo de cliente + sucursal, **estado en memoria
del proceso** (no escala a más de un worker), limpieza de zombies a los 120 s sin ping.

**Red de seguridad:** las cuatro vistas operativas (`CajaView`, `KDSView`, `KDSManager`,
`MeseroView`) hacen polling cada 5 s cuando el WS está caído, y un refresh preventivo si no hubo
tráfico en 45 s. Es lo que hoy salva los eventos perdidos.

---

## 9. Impresión

`print_service/` — servicio Python + Flask + ESC/POS en Windows, puerto 3001, impresora Easytime
SP-POS891ED (80 mm). El backend hace POST automático al marcar `cuenta_solicitada`; falla en
silencio para no bloquear el cobro. Cola con reintentos (máx. 5).

---

## 10. Autenticación

- JWT HS256, **expiración 24 h** (`ACCESS_TOKEN_EXPIRE_MINUTES = 1440`), payload `sub` + `exp`.
- Sin `jti`, sin refresh, sin blacklist → **no hay forma de invalidar una sesión**.
- PIN con Argon2, retrocompatible con bcrypt.
- `verify_password` acepta texto plano si el hash no empieza con `$` (fallback legado).
- Sin rate limiting en ningún endpoint de login.
- Aislamiento por `sucursal_id`.

---

## 11. Infraestructura

| Servicio | Plataforma | Estado |
|---|---|---|
| Frontend | Vercel | Activo |
| Backend | Docker → Railway | Activo, Dockerfile multi-stage, no-root, healthcheck |
| DB | Neon Cloud (AWS us-east-2) | Activo — instancia nueva, migrada de Azure el 2026-08-24 (S0) |
| Redis | Railway | En uso desde S2 — fan-out de eventos WS entre workers y backend del rate limiter de login |
| Migraciones | Alembic (1 baseline colapsado, head `1af66464b276`) en `apps/backend/alembic/` | Completas |
| Tests | pytest — 108 tests (backend), sin suite de tests en frontend todavía | `apps/backend/tests/` |
| CI/CD backend | GitHub Actions `backend-ci.yml` | ✅ Activo — ruff + pytest en cada push a `apps/backend/**` |
| CI/CD frontend | GitHub Actions `frontend-ci.yml` | ✅ Activo — vue-tsc + build en cada push a `apps/frontend/**` |
| Seguridad | GitHub Actions `security-sast.yml` | ✅ Activo — Gitleaks cada lunes, alerta Telegram |
| docker-compose | `docker-compose.yml` (raíz) | `docker compose up` levanta app + Postgres; context `./apps/backend` |

**Ramas:** solo `main` (producción y desarrollo). `flujo-mesero` fue promovida a `main` el 2026-08-24.

**Estructura:** monorepo bajo `apps/` — `apps/backend/`, `apps/frontend/`, `apps/print-service/`.

**Detalle de la migración de infraestructura (S0)** en
[SPRINTS.md](./SPRINTS.md#s0--migración-de-infraestructura): por qué el baseline se generó por
espejo de `pg_dump` y no por `autogenerate` desde `models.py`, las 6 divergencias que ese diff
reveló (`models.py` desincronizado del schema real — entrada directa para S1), y los hallazgos de
seguridad nuevos (secreto de Neon en `alembic.ini`, shim que eclipsaba `pydantic-settings`, JWT en
query string de los WS).

---

## 12. Deuda técnica conocida

| Issue | Severidad | Dónde |
|---|---|---|
| Endpoints `async def` con sesión síncrona → bloqueo del event loop | Alta | `routers/*.py` (deliberadamente fuera de alcance de S2, ver notas de cierre en SPRINTS.md) |
| ~~WS manager en memoria; no soporta >1 worker~~ | — | Resuelto en S2 2.2: fan-out por Redis pub/sub, degrada a memoria sin Redis |
| ~~Sin máquina de estados (whitelist rol→destino)~~ | — | Resuelto en S2 2.4: `domain/estados.py::transicion_permitida`, valida origen y destino |
| ~~Carrera en `update_articulo_estado` (check-then-act, 2 commits)~~ | — | Resuelto en S2 2.5: `with_for_update()` + un solo commit |
| Sin rate limiting en logins | Alta | `routers/auth.py` |
| Fallback de password en texto plano | Alta | `auth.py:35-38` |
| JWT de sesión completo en el query string de los `/ws/*` → queda en texto plano en logs de acceso de Railway | Alta | `websocket_routes.py` (hallazgo del 2026-08-24, ver SPRINTS.md) |
| ~~`models.py` desincronizado del schema real (turnos.diferencia)~~ | — | Resuelto en S3 3.8: `turnos.diferencia` mapeada en ORM y persistida en `cerrar_turno` |
| Secreto de Neon (la instancia vieja, ya apagada) trackeado en el historial de `alembic.ini` | Media | recuperable con `git log -p -- alembic.ini`; sin efecto práctico ya que la credencial está muerta, pero sigue en el historial |
| Cobertura de tests casi nula | Alta | Todo el proyecto (mitigado: 108 tests en backend) |
| ~~Check-in por NIP ignora la fecha del registro abierto~~ | — | Resuelto en S3 3.5: check-in explícito con lock `with_for_update()` e índice único parcial |
| ~~Turno sin cerrar bloquea el siguiente y sigue capturando pedidos~~ | — | Resuelto en S3 3.4/3.8: `reconciliar_jornada` perezosa + cierre automático |
| Fechas naive comparadas contra `TIMESTAMPTZ` | Media | `asistencia.py:42-50,127-128` |
| N+1 en `resumen_asistencia` | Media | `asistencia.py:142-151` |
| `CajaView.vue` 4 093 líneas · `MeseroView.vue` 2 580 | Media | `views/` |
| `print()` como logging | Baja | Routers |

El plan v2 ataca todos los de severidad alta. Detalle y orden en [PLAN_V2.md](./PLAN_V2.md).

---

## 13. Fuera de alcance hoy

Descuentos y promociones · mapa visual de mesas · perfil o historial de clientes · cambio de
sucursal desde la UI · precios dinámicos · sistema genérico de variantes (solo Pozole) · emisión de
CFDI · inventario y stock (llega en el plan v2).

---

## 14. Referencia rápida

**Numeración de mesas:** piso 1 → 11-15 · piso 2 → 21-25 · piso 3 → 31-35.

**Colores corporativos:** `#00126D` (azul) · `#FDB700` (amarillo).

**Puertos:** backend 8000 · frontend 5173 · print service 3001.
