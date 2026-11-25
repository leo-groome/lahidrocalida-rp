# Plan de adopción de Linear y flujo de trabajo

**Preparado:** 2026-11-25 · **Estado:** en implementación, [VAL-265](https://linear.app/valtaoperative/issue/VAL-265/adoptar-flujo-linear-y-documentacion-operativa); inventario inicial sujeto a verificación.

## Acuerdos

- Linear es el tablero operativo del proyecto LaHidrocalida (`.linear.yaml`). Se autoriza crear y actualizar tickets y estados como parte del trabajo. Buscar antes de crear y no cerrar trabajo ajeno sin confirmarlo. Se creó VAL-265 para esta adopción.
- Flujo previsto: rama de trabajo → PR a `develop` → PR de promoción a `main`. Una sola persona desarrolla; no habrá rama permanente `QA`.
- El proyecto es single tenant. Mantener los controles de permisos y de sucursal existentes según la operación real; no agregar infraestructura multitenant por adoptar este proceso.
- El trabajo de producto conserva su prioridad por definir; no convertir automáticamente todo el plan histórico en un compromiso vigente.

## Línea base inicial

- El 2026-11-25, `linear issues list --project 0e34ecbf-19fa-405b-8691-9e5a52633ca1 --limit 250 --output json` devolvió `[]`. Confirmar nuevamente antes de crear tickets.
- La referencia local `origin/main` apunta a `fd4ecba`; el checkout está en `feat/nomina-cierre-al-pagar`, con un commit adicional y un merge de `origin/main`. Las referencias locales remotas no muestran `develop`. Consulta directa posterior: `main` remoto avanzó a `e1720b5` y no existe `develop`; actualizar referencias antes de crearla.
- Hay trabajo local preexistente: cambios en `AGENTS.md` y `apps/backend/.python-version`, y archivos/directorios sin seguimiento `.linear.yaml`, `CLAUDE.md` y `.herdr-web-ui/`. No sobrescribir ni incluirlos inadvertidamente; revisar sus diffs antes de editarlos.
- Los workflows actuales se activan en `main`: backend ejecuta Ruff, pruebas generales en SQLite, migraciones PostgreSQL y una prueba de concurrencia PostgreSQL; frontend ejecuta vue-tsc, Vitest y build; seguridad ejecuta Gitleaks. No se ha verificado el resultado actual de CI ni la suite completa.
- `README.md` y `AGENTS.md` contienen rutas y afirmaciones históricas sobre tests o migraciones; `PLAN_V2.md` dice que nada está implementado, aunque `SPRINTS.md` registra S0–S3 como terminados. `SPRINT_ADMIN.md` documenta cambios y verificaciones pendientes posteriores. Es necesario contrastar cada afirmación con código, PR y pruebas; un documento histórico no prueba el estado de producción.
- El repositorio tiene pruebas backend y frontend; sus scripts actuales están en `apps/backend/pyproject.toml` y `apps/frontend/package.json`. El build de frontend no incluye por sí mismo `vue-tsc`; CI lo ejecuta por separado.

## Fases

### 1. Diagnóstico y conciliación

1. Revisar el estado remoto de ramas, PR abiertos, CI y configuración de despliegue disponible sin cambiarla. Separar hechos comprobados, históricos y pendientes de verificación en producción.
2. Contrastar módulos y pruebas con los documentos actuales. Priorizar reglas operativas de pedidos, caja, turnos, asistencia, impresión y nómina.
3. Inventariar pendientes de `SPRINTS.md`, `PLAN_V2.md`, `SPRINT_ADMIN.md` y auditorías, con evidencia, posibles duplicados, dependencias y estado propuesto. No afirmar que algo sigue pendiente solo porque un documento antiguo lo diga.
4. Identificar comprobaciones que requieran datos o acceso de producción; no ejecutar backfills ni cambios de datos como parte del diagnóstico.

**Entrega:** diagnóstico fechado e inventario revisable de candidatos a tickets, con incertidumbres explícitas.

### 2. Documentación y reglas de agentes

- Actualizar `AGENTS.md` sin perder reglas de negocio vigentes: propósito, lectura inicial, Linear, ramas, checks y límites de operación. Mover detalles extensos a documentos de dominio cuando se hayan verificado.
- Mantener `CLAUDE.md` como referencia breve a `AGENTS.md` y asegurar que ambos queden versionados.
- Actualizar `README.md` con rutas y comandos comprobados. Actualizar `ESTADO_ACTUAL.md` con fecha y alcance de la verificación.
- Señalar `PLAN_V2.md`, `SPRINTS.md` y `SPRINT_ADMIN.md` como estrategia o registro histórico según corresponda; Linear mantendrá el estado operativo. Conservar decisiones y evidencia existentes.
- Crear `docs/BRANCHING.md` con el flujo de este proyecto, requisitos de revisión, rollback y despliegue.

**Entrega:** documentos coherentes entre sí, sin presentar como confirmado lo que no se haya comprobado.

### 3. Linear

- Consultar nuevamente el proyecto y el detalle de cualquier ticket relacionado antes de crear uno.
- Crear tickets de adopción y de producto solo a partir del inventario conciliado. Cada ticket debe incluir contexto, alcance, criterios comprobables, dependencias y referencias pertinentes. Evitar duplicados y carga masiva sin priorización.
- Usar los estados reales del equipo: `Backlog`, `Todo`, `In Progress`, `In Review`, `Done`, previa verificación. Propuesta: `In Progress` al iniciar, `In Review` al abrir PR, mantenerlo en revisión tras merge a `develop`, y `Done` tras promoción a `main` y verificación acordada. Documentar excepciones y divergencias.
- Registrar PR y resultados en el ticket; actualizar docs afectadas en el mismo cambio. Sin credenciales en el repositorio.

**Entrega:** tickets trazables y reglas de actualización documentadas.

### 4. Ramas y despliegue

- Comprobar primero qué ramas despliegan Vercel y Railway, cómo se ejecutan las migraciones y cuál es el commit adecuado para iniciar `develop`; no asumir que el checkout actual representa producción.
- Preparar `develop` desde el `main` remoto confirmado. El desarrollo nuevo parte de `develop`; los cambios llegan por PR y CI verde. Promover `develop → main` mediante PR después de la revisión y pruebas aplicables.
- Documentar hotfixes por el mismo recorrido y una lista breve de verificación de producción. No promover ni desplegar como parte de la preparación.
- Considerar un guard que falle PR a `main` desde otra rama; verificar sus límites reales: un workflow no impide por sí mismo pushes directos.

**Entrega:** flujo documentado y configuración coherente, sin despliegue accidental.

### 5. Quality gates

- Adaptar los workflows existentes para PR a `develop` y `main` y los pushes pertinentes. Mantener filtros por rutas y comunicar qué controles ejecuta cada cambio.
- Revisar si conviene ampliar PostgreSQL y Redis en CI; registrar primero los fallos preexistentes sin ocultarlos ni desactivar verificaciones.
- Documentar checks locales reales y QA proporcional al cambio: pedidos, KDS, caja, turnos, asistencia, nómina e impresión según el alcance.
- Validar sintaxis y comportamiento de workflows y ejecutar los checks aplicables antes de usarlos como requisito.

**Entrega:** controles que reflejen lo que realmente se ejecuta y que acompañen el flujo nuevo.

### 6. Piloto

Escoger un ticket pequeño una vez definida la prioridad: ticket → rama → implementación y docs → pruebas → PR a `develop` → revisión → promoción separada a `main`. Ajustar el proceso con lo aprendido. La promoción a producción requiere la autorización correspondiente en el momento de ejecutarla.

## Pendientes de decisión

- Prioridad de producto: confirmar si se retoma el orden histórico S4–S7 o se atiende primero otra necesidad del restaurante.
- Determinar qué estado final en Linear representa una liberación verificada y quién realiza esa comprobación, especialmente para cambios sin despliegue.
- Confirmar configuración efectiva de despliegue y estado de verificaciones históricas en producción antes de adoptar conclusiones operativas.
