# La Hidrocálida v2 — Tablero de sprints

**Rama base:** `flujo-mesero` · **Última actualización:** 2026-08-24 (S0 cerrado)

Documento vivo. El alcance y el *por qué* de cada bloque están en [PLAN_V2.md](./PLAN_V2.md); la
foto del sistema tal como funciona hoy está en [ESTADO_ACTUAL.md](./ESTADO_ACTUAL.md). Este archivo
es el **avance**: qué se hizo, qué falta, qué se descubrió por el camino.

**Al abrir una sesión de trabajo:** leer el resumen → identificar el sprint 🔵 en curso → tomar la
primera tarea en ⚪. No hace falta reconstruir contexto de otra forma.

**Al cerrar una tarea:** marcar su fila. **Al cerrar un sprint:** llenar *Notas de cierre*,
actualizar `ESTADO_ACTUAL.md`, y añadir las decisiones nuevas al registro del final.

Estados: ⚪ pendiente · 🔵 en curso · 🟢 cerrado · 🔴 bloqueado · ⏭️ pospuesto

---

## Resumen

| Sprint | Alcance | Bloques | Tamaño | Estado | Rama | Cerrado |
|---|---|---|---|---|---|---|
| **S0** | Migración de infraestructura (Koyeb→Railway, Neon nueva instancia) | — | M | 🟢 cerrado | — | 2026-08-24 |
| **S1** | Fundaciones: Alembic, `deps.py`, `estados.py`, seguridad crítica | 0 + críticos 6 | M | ⚪ **siguiente** | `v2/sprint-1-fundaciones` | — |
| **S2** | Fiabilidad de pedidos | 1 | L | ⚪ | `v2/sprint-2-pedidos` | — |
| **S3** | Jornada: sesiones y corte unificado | 8 + 9 | L | ⚪ | `v2/sprint-3-jornada` | — |
| **S4** | Tiempos y métricas de cocina | 2 | M | ⚪ | `v2/sprint-4-tiempos` | — |
| **S5** | Aprobaciones, visibilidad de métricas, IVA | 4 + 5 + 7 | L | ⚪ | `v2/sprint-5-control` | — |
| **S6** | Inventario | 3 | XL | ⚪ | `v2/sprint-6-inventario` | — |
| **S7** | Endurecimiento para producción | resto de 6 | M | ⚪ | `v2/sprint-7-produccion` | — |

**Grafo de dependencias:**

```
S0 ──▶ S1 ──┬──▶ S2 ──┬──▶ S4 ──▶ S5 ──▶ S6
            │         │
            └──▶ S3 ──┘
                      └──▶ S7
```

S2 y S3 son independientes entre sí y se pueden desarrollar en paralelo, pero **ambos tocan
`auth.py`**: sus merges se serializan.

---

## S0 — Migración de infraestructura

**Estado:** 🟢 cerrado (2026-08-24) · **Depende de:** nada · **Ejecuta:** Leo (yo entrego el runbook y valido)

**Objetivo:** mover el backend de Koyeb a Railway y la base a una instancia nueva de Neon (la actual
en Azure está siendo depreciada), aprovechando la migración para validar el baseline de Alembic sin
tocar producción.

**Por qué va primero:** el plan original exigía `alembic stamp` sobre la Neon de producción — el
paso más frágil de todo el Bloque 0. Construyendo la instancia nueva desde las migraciones ese paso
desaparece: si el baseline está mal, se descubre en una base vacía que a nadie le importa. De paso,
la instancia nueva nace con credenciales nuevas, lo que neutraliza el secreto filtrado sin
reescribir el historial de git.

### Pasos (el orden importa)

| # | Paso | Quién | Estado |
|---|---|---|---|
| 0.1 | Generar el baseline de Alembic y verificarlo contra Postgres local vacío | Claude | 🟢 |
| 0.2 | `pg_dump --schema-only` de Neon actual vs. DDL del baseline local → diff revisado a mano | Claude | 🟢 |
| 0.3 | Crear la instancia nueva de Neon (fuera de Azure) — hecho vía Import Data Assistant de Neon (schema+datos en un solo flujo, DB de 12 MB, bajo el límite de 10 GB) | Leo | 🟢 |
| 0.4 | Construir el esquema con `alembic upgrade head` — **nunca** con `create_all` — no aplicó tal cual: el Import Data Assistant ya trajo el schema+datos, así que en vez de construir se **estampó** (`alembic stamp --purge 1af66464b276`) para alinear `alembic_version` con el baseline colapsado; `alembic upgrade head` corrido después confirma no-op | Claude | 🟢 |
| 0.5 | `pg_dump --data-only` de la vieja → restore en la nueva; verificar conteos por tabla — cubierto por el Import Data Assistant; conteos verificados iguales en las 14 tablas entre vieja y nueva | Leo + Claude | 🟢 |
| 0.6 | Migrar el backend a Railway, `DATABASE_URL` a la instancia nueva, `alembic upgrade head` como release command (integrado al `CMD` del Dockerfile, corre en cada arranque, idempotente) | Leo | 🟢 |
| 0.7 | Provisionar Redis en Railway (no se usa hasta S2, pero tenerlo evita bloquear ese sprint) | Leo | 🟢 |
| 0.8 | Apagar la instancia vieja → la credencial filtrada queda muerta | Leo | 🟢 |

Los pasos 0.1 y 0.2 son también la tarea 1.1 del Sprint 1: se hacen una sola vez.

### Hallazgos de 0.1/0.2 (2026-08-24)

La cadena de 6 migraciones **no reconstruye el schema desde cero**: la primera (`8967024cbc4c`)
hace `ALTER TABLE pedidos ADD COLUMN` sobre una tabla que nunca crea — el schema base nació de
`create_all()` en prod y Alembic solo trackeó cambios incrementales desde ahí. Confirmado corriendo
la cadena contra Postgres vacío: falla en la primera migración.

El baseline nuevo (`alembic/versions/1af66464b276_baseline_schema.py`) se generó a partir de
`pg_dump --schema-only` de la Neon actual (espejo exacto, no desde `models.py` — ver por qué abajo),
reemplaza las 6 migraciones viejas, y quedó verificado byte-a-byte contra prod (las únicas 2
diferencias residuales son un `COMMENT ON SCHEMA` que pone Postgres local por defecto y el
formato interno de dos `CHECK` constraints — ambos artefactos de versión de Postgres, sin efecto
semántico).

**Por qué espejo de prod y no autogenerate desde `models.py`:** el diff mostró que `models.py` está
desincronizado del schema real. Autogenerar desde el ORM habría *dropeado* columnas con datos al
construir la instancia nueva. Divergencias encontradas, sin tocar (son bugs de S1, no de S0):

- `turnos.diferencia` — el ORM no la mapea; `turnos.py:768` le asigna valor pero **nunca se
  persiste** (atributo transitorio de Python, no columna mapeada). Bug real, silencioso.
- `turnos.monto_retirado` / `monto_restante_en_caja` — el frontend (`TurnoModal.vue`) las manda,
  el backend las ignora (comentario explícito en `turnos.py:320`).
- `usuarios.permiso_registros/reportes/configuracion/escritura_*` (5 columnas) — sin ninguna
  referencia en el código. Parecen muertas.
- `usuarios.pin` tiene un hash bcrypt como `DEFAULT` de columna — cruft, no debería estar ahí.
- `platillos.kds_name`: prod es `varchar(32)`, el modelo declara `String(50)` — el ORM permite más
  de lo que la columna acepta.
- Nombres de índices/FK divergentes entre prod y lo que generaría el modelo
  (`uq_pedidos_client_request_id` parcial vs. `ix_pedidos_client_request_id` no-parcial).
- Función `show_db_tree()` en prod — helper de introspección manual sin relación con las tablas de
  la app. Se preservó en el baseline por fidelidad; candidata a borrar en S1 si nadie la usa.

Estas 6 divergencias deben resolverse en S1 (o antes) actualizando `models.py` para que refleje la
realidad — decidir por cada una si se sincroniza el modelo a la columna o se hace la migración
inversa. `turnos.diferencia` es la más urgente: es un bug de negocio activo, no solo deuda técnica.

**Nota operativa:** al correr el diff contra prod se ejecutó por accidente un `alembic upgrade head`
contra la Neon de producción (el `alembic.ini` tiene la URL hardcodeada y `env.py` no lee
`DATABASE_URL` de entorno). Fue inofensivo porque prod ya estaba en `head` (no-op), pero confirmó
que ese archivo es peligroso mientras el secreto siga ahí. Se resolvió parcialmente en el mismo
día: `alembic/env.py` ahora prioriza `DATABASE_URL` de entorno sobre `alembic.ini` (era condición
necesaria para que el `CMD` del Dockerfile no migrara contra la URL vieja). Falta borrar el literal
de `alembic.ini:63` — eso es 1.2, y con la instancia vieja ya apagada (0.8) la credencial filtrada
quedó muerta de todas formas, así que 1.2 es limpieza, ya no es urgente.

### Hallazgos de 0.3-0.6 (2026-08-24)

**Import Data Assistant de Neon reemplazó 0.3+0.5 en un solo paso.** La DB pesaba 12-13 MB, muy
por debajo del límite de 10 GB del flujo guiado — copió schema + datos de un tiro en vez del
`pg_dump`/`restore` manual planeado. Cambia el orden pero no el resultado: como el baseline ya
estaba verificado byte-a-byte contra prod (0.1/0.2), no hacía falta que la instancia nueva
construyera su schema *desde* las migraciones para confiar en el resultado — sólo hacía falta que
`alembic_version` quedara consistente con el baseline colapsado. Se resolvió con
`alembic stamp --purge 1af66464b276` contra la URL nueva. **Lección para la próxima migración de
infra:** si el import trae su propio `alembic_version`, siempre hay que re-estampar antes del
primer deploy — si no, el `alembic upgrade head` del arranque falla con
`Can't locate revision`.

**La `DATABASE_URL` se corrompió al copiarla a Railway.** Perdió `/neondb?sslmode=require&channel_binding=require`
al pegarla en la UI de variables de Railway (y lo mismo pasó en `backend/.env` local al
reconstruirlo desde `.env.example`). Sin `dbname` en la URL, psycopg2/libpq usa el username como
nombre de base (error confuso: `database "neondb_owner" does not exist`), y sin `sslmode=require`
Neon rechaza la conexión directamente. **Lección:** al pegar connection strings de Neon en un env var
de Railway (o cualquier UI), verificar el string completo después de pegar — el `&` de la query
string es un punto de corte fácil.

**El JWT de sesión viaja como query param en el WebSocket (`/ws/kds?token=...`).** Confirmado en
logs de Railway: el token completo queda en texto plano en los logs de acceso. Va contra la regla
de "nunca loguear tokens" del proyecto. No se tocó — es cambio de `auth.py` +
`websocket_routes.py` + frontend, entra en el bloque de seguridad de S1 (ver hallazgo nuevo abajo).

### Definition of Done
- [x] `alembic upgrade head` sobre base vacía reconstruye el esquema completo
- [x] El diff contra el dump de producción está revisado y cada diferencia explicada
- [x] Conteos por tabla cuadran entre instancia vieja y nueva
- [x] El backend responde en Railway contra la instancia nueva
- [x] La instancia vieja está apagada

### Bloqueantes
Ninguno — cerrado. S1 puede arrancar.

### Notas de cierre

**Qué quedó funcionando:** Neon en AWS us-east-2 (fuera de Azure, credencial vieja muerta), Railway
sirviendo el backend con `alembic upgrade head` integrado al arranque del contenedor (release
command implícito, idempotente), Redis provisionado, Docker local reproducible
(`docker compose up` levanta app + Postgres desde cero y pasa el DoD de 1.1/1.8 por adelantado).

**Qué se adelantó de S1 sin querer, porque tocar Docker/env lo exigía:** 1.1 completo (baseline
colapsado, `create_all` fuera, `/health`), 1.8 completo (`docker-compose.yml`), y partes de 1.2/1.3/1.7
(ver sus filas en la tabla de S1 — quedaron marcadas 🔵 parcial con el detalle de qué falta).
**Al abrir la sesión de S1, no repetir ese trabajo — leer primero qué quedó parcial antes de asignar
las tareas a los agentes.**

**Las 6 divergencias `models.py` vs. schema real** (sección "Hallazgos de 0.1/0.2" arriba) siguen
sin resolver y son ahora la entrada más concreta para arrancar S1 — en particular
`turnos.diferencia`, que es un bug de negocio activo (se calcula, nunca se guarda).

---

## S1 — Fundaciones

**Estado:** ⚪ pendiente · **Rama:** `v2/sprint-1-fundaciones` · **Depende de:** S0 pasos 0.1-0.2

**Objetivo:** que a partir de aquí toda migración sea reproducible, todo check de rol venga de un
solo sitio, exista un enum de estados único, y los agujeros explotables desde la LAN estén cerrados.

### Tareas

| # | Tarea | Archivos | Agente | Estado |
|---|---|---|---|---|
| 1.1 | Baseline de Alembic (colapsar las 6 migraciones), quitar `create_all` de `main.py:29`, añadir `/health` simple | `alembic/versions/*`, `backend/app/main.py` | backend-architect | 🟢 |
| 1.2 | Purgar el secreto de `alembic.ini:63`; la URL sale solo de env vía `env.py` | `alembic.ini`, `alembic/env.py` | security-auditor | 🔵 parcial — `env.py` ya prioriza `DATABASE_URL` de entorno sobre el `.ini` (necesario para que Docker no migre contra la URL vieja hardcodeada); falta borrar el literal de `alembic.ini:63` y rotar si aplica |
| 1.3 | Borrar `pydantic_settings.py` (shim que eclipsa al paquete real) y `add_propinas_columns.py`; crear `backend/.env.example` | `backend/` raíz | task-executor | 🔵 parcial — shim borrado, `.env.example` creado; falta borrar `add_propinas_columns.py` (script de migración ad-hoc ya cubierto por el baseline) |
| 1.4 | `app/deps.py` con `require_roles` + consolidar `get_turno_activo` (hoy 4 copias) | `backend/app/deps.py` (nuevo) | backend-architect | ⚪ |
| 1.5A | Migrar checks de rol — `pedidos.py`, `turnos.py` | 2 routers | task-executor | ⚪ |
| 1.5B | Migrar checks de rol — `gastos.py`, `asistencia.py`, `admin.py` | 3 routers | task-executor | ⚪ |
| 1.5C | Migrar checks de rol — `users.py`, `reportes.py`, `propinas.py`, `products.py` | 4 routers | task-executor | ⚪ |
| 1.6 | `domain/estados.py` + `constants/estados.ts` como fuente única (sin tabla de transiciones todavía) | backend + 4 consumidores front | backend-architect + vue-ui-architect | ⚪ |
| 1.7 | Seguridad crítica: quitar fallback texto plano, rate limiting en logins, gates en `/usuarios/` y `/ws/stats`, `/health/database` sin host, CORS desde env, JWT de sesión fuera del query string de los `/ws/*` (hallazgo nuevo, confirmado en logs de Railway) | `auth.py`, `config.py`, `main.py`, `users.py`, `websocket_routes.py` | security-auditor + task-executor | 🔵 parcial — `CORS_ORIGINS` ahora viene de env (`CORS_ORIGINS` obligatoria, sin default, sin IP de LAN hardcodeada) y `/health/database` ya no expone host; falta fallback texto plano, rate limiting, gates de `/usuarios/` y `/ws/stats`, y el token en query string de los WS |
| 1.8 | `docker-compose.yml` (app + Postgres; Redis llega en S2) | raíz | backend-architect | 🟢 |
| 1.9 | Arreglar `conftest.py` para que los tests nuevos corran | `backend/tests/conftest.py` | backend-architect | ⚪ |

### Reglas de ejecución

**La tarea 1.5 es estrictamente 1:1.** El conjunto de roles después debe ser idéntico al del `if`
que reemplaza. Hay divergencias conocidas (`agregar_articulos` bloquea `cuenta_solicitada` y
`actualizar_articulos` no) que **no se corrigen aquí** — eso es lógica de negocio y va al S2 con sus
propios tests. Criterio: el diff de roles permitidos por endpoint debe ser vacío.

**`require_roles` se cuelga de `get_current_active_user`, no de `get_current_user`.** Hoy
`get_current_user` (`auth.py:72-96`) no comprueba `usuario.activo`: un usuario desactivado pasa por
cualquier endpoint que no use explícitamente la variante `active`.

**`/auth/users` no se toca.** Es el selector de login de la tablet; ponerle auth rompe el arranque
del dispositivo. Y contra lo que dice PLAN_V2.md, ya filtra admins (`auth.py:174`).

**`ACCESS_TOKEN_EXPIRE_MINUTES` se queda en 1440.** Bajarlo sin el mecanismo de jornada del S3
deslogueua al personal a media operación.

### Lotes de ejecución paralela

Ningún par de agentes toca el mismo archivo a la vez. Archivos calientes: `main.py`, `config.py`,
`auth.py`, `conftest.py`, `pedidos.py`.

| Lote | En paralelo | Agentes |
|---|---|---|
| 0 | 1.2 · 1.3 · 1.6-backend · query de PINs contra la base | 3 + 1 verificación |
| 1 | 1.1 · 1.4 | 2 |
| 2 | 1.5A · 1.5B · 1.5C · 1.7 · 1.6-frontend | 5 |
| 3 | 1.8 · 1.9 (secuencial, necesitan la rama consolidada) | 1-2 |
| 4 | Verificación completa + security-auditor sobre el diff acumulado | 1 |

El lote 2 es el cuello de botella: 1.7 toca `main.py` y `config.py`, que el lote 1 ya modificó.

### Verificación

```bash
docker compose up -d db
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/hidrocalida alembic upgrade head

# La prueba del Bloque 0
pg_dump --schema-only "$NEON_URL_ACTUAL" > /tmp/prod_schema.sql
pg_dump --schema-only postgresql://postgres:postgres@localhost:5432/hidrocalida > /tmp/local_schema.sql
diff /tmp/prod_schema.sql /tmp/local_schema.sql

cd backend && uv run pytest -q
docker compose up --build
curl localhost:8000/health                          # {"status":"ok"}
curl localhost:8000/health/database                 # sin host ni credenciales
curl localhost:8000/ws/stats                        # 401
curl -H "Authorization: Bearer $TOKEN_MESERO" localhost:8000/usuarios/   # 403
curl -H "Authorization: Bearer $TOKEN_ADMIN"  localhost:8000/usuarios/   # 200
for i in $(seq 1 20); do curl -s -o /dev/null -w "%{http_code}\n" \
  -X POST localhost:8000/auth/login-simple -d '{"usuario_id":1,"pin":"0000"}' \
  -H 'Content-Type: application/json'; done         # debe aparecer 429
cd frontend/pos-system && pnpm build
```

**Tests nuevos** (`backend/tests/`, happy path + caso de error cada uno):

- `test_deps.py` — 403 con rol prohibido, 200 con permitido, 403 con `activo=False`
- `test_auth_hardening.py` — `verify_password` rechaza texto plano, acepta argon2
- `test_rate_limit.py` — intento N+1 dentro de la ventana da 429; la ventana expira
- `test_health.py` — el body no contiene host ni contraseña
- `test_ws_stats_auth.py` — sin token 401, no-admin 403, admin 200
- `test_app_importable.py` — canario de import (detecta regresiones del efecto secundario de `websocket_manager`)
- `test_config.py` — `Settings` sin `SECRET_KEY` levanta `ValidationError` (prueba de que el shim murió)

### Definition of Done
- [ ] `docker compose up` levanta app + Postgres desde cero
- [ ] `alembic upgrade head` sobre base vacía reconstruye el esquema; diff contra prod revisado
- [ ] `pytest` verde con los 7 archivos nuevos
- [ ] `pnpm build` compila
- [ ] `grep -rn "current_user.rol" backend/app/routers/` no devuelve nada
- [ ] `grep -n "create_all" backend/app/main.py` no devuelve nada
- [ ] `git grep -i "npg_\|postgres://.*:.*@"` limpio
- [ ] Revisión de security-auditor sobre el diff acumulado, sin hallazgos altos
- [ ] `PLAN_V2.md` y `ESTADO_ACTUAL.md` actualizados con las correcciones de la sección de abajo

### Bloqueantes

| Qué | Quién | Bloquea |
|---|---|---|
| `SELECT id, nombre FROM usuarios WHERE pin NOT LIKE '$%';` — si devuelve filas, hay que rehashear esos PINs antes de mergear o esos usuarios quedan fuera | Leo (o Claude con `DATABASE_URL` de solo lectura) | merge de 1.7 |
| Lista definitiva de orígenes CORS de producción (hoy: `lahidrocalida.vercel.app` + una IP de LAN quemada) | Leo | merge de 1.7 |

### Notas de cierre
*(pendiente)*

---

## S2 — Fiabilidad de pedidos

**Estado:** ⚪ pendiente · **Rama:** `v2/sprint-2-pedidos` · **Depende de:** S1, S0 completo

**Objetivo:** que deje de perderse un pedido. Cubre el Bloque 1 completo.

| # | Tarea | Bloque | Estado |
|---|---|---|---|
| 2.1 | Desbloquear el event loop: `app/events.py` con cola + consumidor en `lifespan`; los endpoints dejan de hacer `await notify_*` | 1.1 | ⚪ |
| 2.2 | Redis entra de verdad: `core/redis.py`, fan-out de WS por pub/sub, degradación a fan-out local, `/health` reporta Redis aparte | 1.2 | ⚪ |
| 2.3 | Migrar el rate limiter de S1 de memoria a Redis (misma firma, solo cambia el backend) | 6 | ⚪ |
| 2.4 | Máquina de estados real: tabla `(origen, destino) → roles` en `domain/estados.py`; `update_pedido` valida origen **y** destino | 1.3 | ⚪ |
| 2.5 | Cerrar la carrera de cocina: `with_for_update()` + un solo commit en `update_articulo_estado` | 1.4 | ⚪ |
| 2.6 | Atomicidad de la división de cuenta: sacar los commits del bucle + `client_request_id` | 1.5 | ⚪ |
| 2.7 | `UniqueConstraint(pedido_id, client_request_id)` en `articulos_pedido` + captura de `IntegrityError` | 1.6 | ⚪ |
| 2.8 | Cola offline en el mesero: `localStorage` + reintento con backoff reusando `client_request_id`; badge de "N sin confirmar" | 1.7 | ⚪ |
| 2.9 | Acuse del KDS por WS + alerta en KDSManager si un pedido lleva >60 s sin acuse | 1.8 | ⚪ |
| 2.10 | Interceptor 401 en `api/client.ts` (hoy solo hay interceptor de request) | 1.9 | ⚪ |

**Nota de arranque:** aquí se introduce el `lifespan` en `main.py`, que hoy no existe. Eso permite
eliminar el efecto secundario de import de `websocket_manager.py:297` y, con él, el monkeypatch de
`asyncio.create_task` en `conftest.py:15-26`.

### Notas de cierre
*(pendiente)*

---

## S3 — Jornada: sesiones y corte unificado

**Estado:** ⚪ pendiente · **Rama:** `v2/sprint-3-jornada` · **Depende de:** S1

**Objetivo:** que las sesiones mueran en el corte de jornada y que nada quede abierto
indefinidamente. Cubre los Bloques 8 y 9. **Es lo que hoy corrompe la nómina cada semana.**

| # | Tarea | Bloque | Estado |
|---|---|---|---|
| 3.1 | `jornada_de(ts)` en `utils/timezone.py`; jornada 05:00→05:00, corte a la 1:00 AM | 8.1 | ⚪ |
| 3.2 | JWT lleva `jornada`; `get_current_user` la compara contra la actual → 401. Sin cron, sin blacklist | 8.2 | ⚪ |
| 3.3 | `Usuario.sesiones_validas_desde` para revocación selectiva | 8.4 | ⚪ |
| 3.4 | `reconciliar_jornada(db, sucursal_id)` idempotente, disparo perezoso desde la dependencia de auth y puntos de entrada | 9.1 | ⚪ |
| 3.5 | Check-in explícito, no interruptor: un registro abierto de jornada anterior nunca se lee como salida | 9.2 | ⚪ |
| 3.6 | `MAX_HORAS_JORNADA` (16 h) como tope duro | 9.2 | ⚪ |
| 3.7 | No inventar horas: `cierre_automatico`, `requiere_revision`, `fecha_salida_estimada`; fuera de nómina hasta que un admin fije la hora | 9.3 | ⚪ |
| 3.8 | Turno de caja `cerrado_automatico` con `total_final`/`diferencia` en NULL | 9.4 | ⚪ |
| 3.9 | `GET /asistencia/anomalias` + marcar los registros basura existentes en la migración (no borrarlos) | 9.5 | ⚪ |
| 3.10 | Cola de revisión en `RecursosHumanosSection.vue`; aviso al abrir turno; cerrar asistencias al cerrar turno | 9.2/9.3 | ⚪ |

**Detalle a no perder:** `POST /auth/asistencia` (`routers/auth.py:114-118`) tampoco tiene lock —
dos requests simultáneos con el mismo `usuario_id` pueden crear dos entradas abiertas. Se arregla
junto con 3.5.

### Notas de cierre
*(pendiente)*

---

## S4 — Tiempos y métricas de cocina

**Estado:** ⚪ pendiente · **Rama:** `v2/sprint-4-tiempos` · **Depende de:** S2, S3

Bloque 2 completo: `PedidoEvento` append-only, columnas denormalizadas de fechas, backfill sin
inventar datos, atribución a la cocinera que marcó el platillo, arreglo del módulo de asistencia
(`rol_snapshot`, `sucursal_id`, `turno_id`, fechas tz, N+1 de `asistencia.py:141-174`) y
`GET /metricas/cocina`.

**Depende de S3 de forma dura:** sin asistencia limpia, los tiempos por cocinera no significan nada.

### Notas de cierre
*(pendiente)*

---

## S5 — Aprobaciones, visibilidad e IVA

**Estado:** ⚪ pendiente · **Rama:** `v2/sprint-5-control` · **Depende de:** S2, S4

Bloques 4, 5 y 7: token de aprobación de un solo uso (consumo atómico con `SET NX EX` en Redis),
bitácora `Aprobacion`, recorte de métricas al cajero, blur real (valores en `null`, no CSS),
`GET /metricas/operacion` y `/metricas/propinas`, y el modelo fiscal (`subtotal`, `iva`, `tasa_iva`,
datos de RFC) con su propagación a cuentas divididas, cortes de caja y ticket impreso.

Buen momento para extraer los paneles de métricas de `CajaView.vue` (4 093 líneas, hoy solo tiene
`TurnoModal` extraído).

### Notas de cierre
*(pendiente)*

---

## S6 — Inventario

**Estado:** ⚪ pendiente · **Rama:** `v2/sprint-6-inventario` · **Depende de:** S5

Bloque 3 completo: `MovimientoInventario` como verdad append-only, `stock_actual` como caché
derivado, `RecetaDetalle` solo de insumos clave, enganche de entrada en `POST /gastos/` y de salida
al pasar el pedido a `pagado`, endpoints de existencias/reorden/conteo/merma/kardex, y la UI de
conteo físico para tablet.

El sprint más grande. Candidato a partirse en dos (modelo + enganches / endpoints + UI) cuando se
llegue.

### Notas de cierre
*(pendiente)*

---

## S7 — Endurecimiento para producción

**Estado:** ⚪ pendiente · **Rama:** `v2/sprint-7-produccion` · **Depende de:** S2

Resto del Bloque 6: Dockerfile multi-stage con `uv` y usuario no-root, `HEALTHCHECK`,
`--workers $WEB_CONCURRENCY` (solo seguro una vez que el fan-out por Redis de S2 esté probado en
producción), handler global de excepciones con contrato `{"error": {"code", "message"}}`, migración
de `requirements.txt` a `pyproject.toml` + `uv.lock`, CI/CD del backend, y ampliación de la suite de
tests.

### Notas de cierre
*(pendiente)*

---

## Correcciones pendientes a la documentación

Se aplican al cerrar el S1. Verificadas contra el código en la auditoría del 2026-08-24.

| Documento | Afirmación | Realidad |
|---|---|---|
| PLAN_V2 (tabla de hallazgos), ESTADO_ACTUAL §5 | «`GET /auth/users` expone la nómina completa con roles» | `auth.py:174` ya filtra admins con `rol.notin_(ROLES_ADMIN)`. Sigue siendo público, y debe seguirlo siendo: es el selector de login. Lo que queda es recortar campos |
| PLAN_V2 (tabla de hallazgos) | «endpoints `async def` con `Session` síncrona — 16 en total» | Los tres GET de `pedidos.py` (332, 390, 417) ya son `def`. Los `async def` son POST/PUT, y lo son porque hacen `await notify_*`. Esa dependencia es lo que hay que romper |
| PLAN_V2 §0.2 | «~30 checks inline» | 37 sitios con `current_user.rol`. Además hay 4 reimplementaciones de "turno activo por sucursal" (`pedidos.py:40`, `turnos.py:42`, `reportes.py:49`, `reportes.py:150`) que el plan no menciona |
| PLAN_V2 §Bloque 6, AGENTS.md | «tests con `httpx.AsyncClient`» | `conftest.py` usa `fastapi.testclient.TestClient` |
| AGENTS.md, README.md | `uv sync`, `cp .env.example .env` | No existen `pyproject.toml`, `uv.lock` ni `backend/.env.example`. El proyecto corre con `requirements.txt` y `pip`. S1 crea el `.env.example`; la migración a `uv` va en S7 |
| PLAN_V2 (tabla de hallazgos) | — | Falta el hallazgo del secreto de Neon en `alembic.ini` (ver registro de decisiones) |

---

## Hallazgos nuevos de la auditoría del 2026-08-24

No estaban en PLAN_V2.md ni en ESTADO_ACTUAL.md.

**1. Credencial de producción de Neon commiteada en el historial de git — crítico.**
`alembic.ini:63` lleva la URL completa con la contraseña del rol `neondb_owner`, trackeada desde el
commit `f4743ee`. Borrar la línea no mitiga nada: es recuperable con `git log -p -- alembic.ini`.
La mitigación real es rotar la credencial, y **la migración a la instancia nueva de Neon (S0) lo
hace de forma natural**. Por eso S0 va primero.

**2. `backend/pydantic_settings.py` eclipsa al paquete real.**
Es un shim casero con una clase `BaseSettings` propia. Como `backend/` es el CWD,
`from pydantic_settings import BaseSettings` en `core/config.py:1` resuelve a ese archivo, no al
paquete instalado (verificado: `import pydantic_settings` → `/backend/pydantic_settings.py`).
Consecuencia: hoy `Settings` **no tiene validación Pydantic de ninguna clase**, pese a que
`pydantic-settings==2.11.0` está en `requirements.txt`. Trackeado, y entra en la imagen Docker.
Se borra en 1.3.

**3. `backend/add_propinas_columns.py` — DDL manual pre-Alembic.**
Script trackeado que altera la tabla `pedidos` con SQL directo. Exactamente el antipatrón que el
Bloque 0 viene a eliminar. Se borra en 1.3.

**4. El JWT de sesión viaja como query param en los WebSocket (`/ws/kds`, y presumiblemente los
demás `/ws/*`) y queda en texto plano en los logs de acceso de Railway.** Confirmado en producción
el 2026-08-24. `websocket_routes.py` usa `token: str = Query(...)` porque el handshake de WS del
browser no permite headers custom — el patrón en sí es común, pero usar el JWT de sesión completo
(no uno de un solo uso, corta vida) significa que cualquiera con acceso a esos logs puede reusarlo
hasta que expire (`ACCESS_TOKEN_EXPIRE_MINUTES=1440`, o sea todo el turno). Entra en el alcance de
seguridad de 1.7 — no estaba en la lista original de esa tarea, hay que agregarlo.

---

## Registro de decisiones

| Fecha | Decisión | Motivo |
|---|---|---|
| 2026-08-24 | La Fase A se parte en 3 sprints (S1/S2/S3) en vez de uno | Un merge que toca 15 archivos del backend, el esquema y 4 vistas no se puede validar en piso ni revertir con precisión |
| 2026-08-24 | Rama por sprint desde `flujo-mesero` + PR al final | Revisión antes de merge; el sprint entero es revertible como unidad |
| 2026-08-24 | La migración de infraestructura (S0) va antes que todo | Elimina el `alembic stamp` sobre producción, valida el baseline en una base desechable, y rota la credencial filtrada sin reescribir historial de git |
| 2026-08-24 | Redis no entra en S1; el rate limiter arranca en memoria | Hoy corre un solo worker, así que en memoria es correcto, no un parche. La firma se diseña para que S2 cambie el backend sin tocar los call sites |
| 2026-08-24 | La cadena de 6 migraciones se colapsa en un único baseline | Ninguna representa algo aplicado de forma controlada en ningún entorno: Neon vive de `create_all` |
| 2026-08-24 | La migración de checks de rol (1.5) es estrictamente 1:1 | Las divergencias existentes son lógica de negocio; "arreglarlas" en una migración mecánica puede bloquear un flujo que hoy funciona en producción |
| 2026-08-24 | `ACCESS_TOKEN_EXPIRE_MINUTES` se queda en 1440 hasta el S3 | Bajarlo sin el mecanismo de jornada desloguea al personal a media operación |
| 2026-08-24 | `/auth/users` no recibe gate de auth | Es el selector de login de la tablet; ponerle auth rompe el arranque del dispositivo |
| 2026-08-24 | El baseline de Alembic se genera por espejo de `pg_dump --schema-only` de prod, no por `autogenerate` desde `models.py` | El diff mostró que el ORM está desincronizado del schema real (`turnos.diferencia` y otras 5 columnas); autogenerar desde el modelo habría dropeado columnas con datos al construir la instancia nueva |
| 2026-08-24 | Se usó el Import Data Assistant de Neon (copia schema+datos en un solo flujo) en vez del `pg_dump`/`restore` manual de 0.3+0.5 | DB de 12-13 MB, muy por debajo del límite de 10 GB del flujo guiado; el riesgo que 0.4 mitigaba (baseline malo) ya estaba cubierto por la verificación byte-a-byte de 0.1/0.2, así que no hacía falta que la instancia nueva construyera su schema desde las migraciones |
| 2026-08-24 | `alembic/env.py` prioriza `DATABASE_URL` de entorno sobre `alembic.ini` | Necesario para que el `CMD` del Dockerfile (`alembic upgrade head` en cada arranque) no migre por accidente contra la URL vieja hardcodeada en el `.ini`; purga completa del secreto sigue pendiente en 1.2, pero ya no es urgente porque la instancia vieja se apagó (0.8) |
| 2026-08-24 | `CORS_ORIGINS` pasa a variable de entorno obligatoria, sin default | Los orígenes ya no viven hardcodeados en `main.py` (incluían una IP de LAN quemada); si falta la variable, la app no arranca en vez de arrancar con CORS abierto o mal configurado |
