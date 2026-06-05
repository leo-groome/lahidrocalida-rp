# La Hidrocálida V3 — Roadmap de Ejecución

## Estado General
> **Sprint activo:** Fase 3 — Frontend  
> **Leyenda:** `[ ]` pendiente · `[~]` en progreso · `[x]` completado

---

## Contexto y Objetivos
Reestructurar el software para que sea el motor definitivo de operaciones:
- Eliminar falla conceptual del **corte a medianoche** (día → turno)
- Acelerar flujos de trabajo con **login por NIP táctil**
- Añadir observabilidad: **Turnos Históricos, RRHH, Asistencia**
- Separar login de **admins vs staff** para seguridad

---

## Decisiones de Arquitectura

| Decisión | Resolución |
|----------|-----------|
| Migración password → pin | Renombrar columna, reset todos a NIP `1111` |
| Admin login | URL separada `/admin-login` con usuario administrador + PIN |
| Staff login | `/login` — NIP grid, solo roles: mesero, cajero, cocina |
| Filtro por dispositivo | localStorage guarda rol por tablet (config única) |
| Sin turno activo | Backend rechaza creación de pedidos con 400 |
| KDSView | Sin auth (solo lectura) — backend GET público |
| KDSManager | Mantiene JWT obligatorio |
| RegistroAsistencia | Solo roles no-admin |
| ClockIn tablet | Ruta pública `/checkin`, muestra todos los no-admin |
| Comida de Personal | **Fuera de este sprint** |
| Brute force NIP | Sin protección en este sprint |

---

## FASE 1 — Base de Datos y Modelos
> **Archivos:** `backend/app/models.py`, `backend/app/schemas.py`, `alembic/versions/NEW.py`

- [x] **1.1** `models.py` — `Usuario.password` → renombrar a `pin`
- [x] **1.2** `models.py` — `Pedido`: añadir `turno_id` FK a `turnos.id` (nullable)
- [x] **1.3** `models.py` — `Turno`: añadir `pedidos = relationship("Pedido")`
- [x] **1.4** `models.py` — **[NUEVO]** modelo `RegistroAsistencia` (`id`, `usuario_id`, `fecha_entrada`, `fecha_salida`, `notas`)
- [x] **1.5** `schemas.py` — Actualizar `UserBase`: `pin` en lugar de `password`
- [x] **1.6** `schemas.py` — `PedidoCreate`: campo `turno_id` opcional
- [x] **1.7** `schemas.py` — **[NUEVO]** schemas `RegistroAsistenciaCreate`, `RegistroAsistenciaResponse`
- [x] **1.8** Alembic migration: `ALTER COLUMN password → pin` + `UPDATE pin = argon2(1111)` para todos
- [x] **1.9** Alembic migration: `ADD COLUMN turno_id` en tabla `pedidos`
- [x] **1.10** Alembic migration: `CREATE TABLE registros_asistencia`
- [x] **1.11** `UsuarioUpdate` — payload parcial; conserva campos no enviados y PIN si viene vacío/omitido

---

## FASE 2 — Lógica de Backend y API
> **Archivos:** `backend/app/routers/auth.py`, `pedidos.py`, `admin.py`, `reportes.py`, **nuevo** `asistencia.py`

- [x] **2.1** `auth.py` — Endpoint `POST /auth/login-simple`: acepta `{usuario_id, pin}` para staff (bloquea admins)
- [x] **2.2** `auth.py` — Endpoint `POST /auth/login-admin`: usuario administrador + PIN solo para administradores
- [x] **2.3** `auth.py` — **[NUEVO]** `POST /auth/asistencia`: clock-in/out con NIP sin generar JWT (público)
- [x] **2.4** `pedidos.py` — `POST /pedidos/`: inyecta `turno_id` activo; rechaza con 400 si no hay turno activo
- [x] **2.5** `pedidos.py` — `GET /pedidos` y `GET /pedidos/{id}`: auth opcional via `get_optional_current_user` (KDS público)
- [x] **2.6** `admin.py` — `GET /admin/dashboard`: usa turno activo; param `turno_id` opcional
- [x] **2.7** `reportes.py` — `/dia/analytics` y `/dia/tickets`: param `turno_id` opcional, fallback a fecha del día
- [x] **2.8** **[NUEVO]** `routers/asistencia.py`:
  - [x] `GET /asistencia/` — listar registros (admin only)
  - [x] `GET /asistencia/usuario/{id}` — historial por empleado
  - [x] `GET /asistencia/resumen` — horas trabajadas por rango de fechas

---

## FASE 3 — Frontend
> **Archivos:** `router/index.ts`, `Login.vue`, `CajaView.vue`, nuevos: `AdminLogin.vue`, `ClockInView.vue`, `TurnosSection.vue`, `RecursosHumanosSection.vue`

- [x] **3.1** `router/index.ts` — Rutas públicas: `/kds`, `/checkin`, `/admin-login`; `/login` sin guard pero sin admins
- [x] **3.2** **[NUEVO]** `AdminLogin.vue` — Ruta `/admin-login`, formulario usuario administrador + PIN, sin visibilidad hacia staff
- [x] **3.3** `Login.vue` — Destruir formulario email/password
- [x] **3.4** `Login.vue` — Primer arranque: selector de rol por dispositivo (guarda en localStorage)
- [x] **3.5** `Login.vue` — Grid de avatares filtrado por rol del dispositivo (excluye admins siempre)
- [x] **3.6** `Login.vue` — Overlay keypad numérico al seleccionar usuario → `POST /auth/login-simple`
- [x] **3.7** `Login.vue` — Botón secundario discreto → `/checkin`
- [ ] **3.8** `CajaView.vue` — Stat cards: "Ventas de Hoy" → "Ventas del Turno Activo"
- [ ] **3.9** `CajaView.vue` — Banner si sin turno activo: "Sin turno activo — Abrir turno para ver estadísticas"
- [ ] **3.10** **[NUEVO]** `ClockInView.vue` — Ruta pública `/checkin`, grid todos no-admin, keypad NIP → `POST /auth/asistencia`, feedback visual
- [ ] **3.11** **[NUEVO]** `TurnosSection.vue` — Panel admin: historial turnos con discrepancias, gastos, ventas por turno
- [ ] **3.12** **[NUEVO]** `RecursosHumanosSection.vue` — Panel admin: horas trabajadas por empleado con selector de fechas

---

## FASE 4 — Rediseño de Gastos
> **Archivos:** componentes existentes de Gastos

- [ ] **4.1** Identificar componentes actuales de gastos y mapear flujo existente
- [ ] **4.2** Rediseño: flujo 3 pasos (categoría con botones → monto + keypad → confirmación)
- [ ] **4.3** Auto-vinculación al turno activo en submit
- [ ] **4.4** Testing del flujo completo

---

## Plan de Verificación

| Prueba | Descripción |
|--------|-------------|
| Midnight test | Turno 10 PM → pedido 11:30 PM + pedido 12:15 AM → ambos en mismo turno en CajaView |
| NIP login | Todos los usuarios staff entran con NIP `1111` desde UI táctil |
| Admin login | Admin entra por `/admin-login` con usuario `Admin` + PIN `1111`; no aparece en grid staff |
| Editar usuario | `PUT /usuarios/{id}` con solo `{activo}` o solo `{pin}` preserva nombre, rol y sucursal |
| Bloqueo sin turno | Crear pedido sin turno activo → error visible en UI mesero |
| KDS público | `/kds` sin login → funciona; `/kds-manager` sin login → redirect |
| Clock-in/out | `/checkin` → usuario → NIP → entrada/salida → panel RRHH muestra horas |
| Device config | Tablet configurada como "mesero" solo muestra meseros en grid |
| Stats por turno | CajaView muestra datos del turno activo, no del día calendario |
