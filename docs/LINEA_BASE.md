# Línea base del repositorio

**Revisión inicial:** 2026-11-25. Esta es una revisión de archivos locales y referencias Git, no una auditoría completa ni una comprobación de producción. El checkout era `feat/nomina-cierre-al-pagar` en `0f52e4c`, con cambios locales previos. `origin/main` local apuntaba a `fd4ecba`, mientras la consulta al remoto devolvió `e1720b5`; por tanto, esta fotografía no asegura describir el último `main` ni el despliegue actual.

## Componentes comprobados

- Monorepo con backend FastAPI y SQLAlchemy en `apps/backend`, frontend Vue 3/TypeScript/Pinia en `apps/frontend` y servicio de impresión en `apps/print-service`.
- El backend registra routers de autenticación, usuarios, asistencia, platillos, pedidos, gastos, adjuntos, nómina, administración, propinas, reportes, turnos y WebSocket. Los modelos incluyen sucursales, pedidos y artículos, gastos, adjuntos, nómina, turnos y asistencia.
- La configuración admite Redis para eventos y limitación de acceso; sin URL degrada a operación local. Adjuntos admiten disco local o almacenamiento compatible con S3. No se ha comprobado la configuración activa de producción.
- El backend tiene migraciones Alembic y pruebas pytest; el frontend tiene pruebas Vitest. El workflow backend usa SQLite en la suite general y PostgreSQL para `alembic upgrade head` y la prueba de concurrencia de compras. El frontend ejecuta `vue-tsc`, Vitest y build por separado.
- El Dockerfile ejecuta migraciones al arrancar. El README histórico identifica Vercel, Railway y Neon, pero no se han inspeccionado sus configuraciones ni el despliegue actual.

## Producto y decisiones históricas

El flujo general documentado es mesero → cocina → caja, con pedidos en tiempo real, impresión, turnos, gastos y nómina. `SPRINTS.md` registra S0–S3 como terminados y `SPRINT_ADMIN.md` describe cambios posteriores; sus fechas, tareas y estados se conservan como historia, no como prueba de que estén en producción. `PLAN_V2.md` contiene propuestas y dependencias que necesitan reconciliarse con el código y la prioridad actual.

## Trabajo pendiente de conciliación

- Actualizar referencias y contrastar el código de `main` remoto, PR abiertos y CI con esta revisión de la rama local.
- Inventariar las tareas históricas y separar implementado, pendiente, descartado y sin verificar. Verificar en particular los pendientes de producción y el backfill de asistencia documentados en `SPRINT_ADMIN.md`; no ejecutarlos durante la revisión.
- Confirmar ajustes reales de Vercel/Railway, base y Redis, sin exponer secretos.
- Reconciliar las secciones antiguas de `ESTADO_ACTUAL.md`, `AGENTS.md` y documentación por módulo con el comportamiento actual. Las advertencias de vigencia identifican que aún hay trabajo por hacer.
- Confirmar el orden de producto con el responsable; los sprints históricos no fijan prioridad automáticamente.

Linear es el tablero operativo. La consulta del proyecto el 2026-11-25 no mostró tickets antes de crear [VAL-265](https://linear.app/valtaoperative/issue/VAL-265/adoptar-flujo-linear-y-documentacion-operativa) para esta adopción.

## Seguridad: hallazgo histórico

Gitleaks detectó una `SECRET_KEY` en un archivo histórico del repositorio público. El 2026-11-25 Leo confirmó que esa clave se rotó al migrar a Railway. El escaneo histórico sigue fallando; queda revisar el tratamiento del hallazgo y la posible reutilización en otros entornos. Seguimiento: [VAL-266](https://linear.app/valtaoperative/issue/VAL-266/investigar-y-revocar-secret-key-historica-expuesta).
