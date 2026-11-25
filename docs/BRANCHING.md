# Ramas y promoción

Flujo acordado: `feature/*`, `fix/*`, `docs/*` o `chore/*` → PR a `develop` → PR de promoción a `main`. `main` representa producción; no hay una rama permanente de QA.

## Activación pendiente

El 2026-11-25 no existía `develop` en el remoto. `main` remoto avanzó más allá de la referencia local y hay trabajo en curso en el checkout. Antes de activar el flujo, actualizar las referencias, revisar PR abiertos y confirmar qué ramas disparan Vercel y Railway. Crear `develop` desde el `main` remoto confirmado, sin mezclar trabajo no integrado. No promover cambios solo por crear la rama.

## Trabajo diario

1. Consulta Linear, el ticket y sus criterios; identifica dependencias. Si no existe, busca duplicados y crea uno en el proyecto indicado por `.linear.yaml`.
2. Actualiza referencias y crea una rama de trabajo desde `origin/develop`, sin cambiar de rama en un checkout ocupado. Usa worktree si hay trabajo simultáneo; no pierdas cambios locales.
3. Implementa, actualiza la documentación afectada y ejecuta los checks adecuados de `AGENTS.md`.
4. Abre PR a `develop` con el ticket, comportamiento, pruebas y limitaciones; actualiza Linear a `In Review`. No integres con CI fallido.
5. Revisa funcionalmente en un entorno adecuado. Promueve con PR `develop → main` cuando esté listo y autorizado para producción. Confirma despliegue y verificación aplicable antes de marcar `Done`.

Los arreglos urgentes siguen el mismo recorrido; se puede acortar la revisión según el riesgo. Registra incidencias y cómo revertir cuando el cambio lo requiera. No se hace push directo a ramas permanentes. Los workflows por sí solos no impiden pushes directos ni garantizan protección de ramas; comprobar los controles disponibles en GitHub.

## Verificación antes de producción

Revisar el diff de promoción completo, CI aplicable, migraciones y variables de entorno; probar los flujos afectados (pedidos, cocina, caja, turnos, nómina, asistencia o impresión). La imagen backend ejecuta `alembic upgrade head` al arrancar, por lo que una promoción puede cambiar el esquema. Preparar recuperación y validar con datos seguros cuando corresponda. No ejecutar migraciones o backfills en producción durante la preparación del PR.
