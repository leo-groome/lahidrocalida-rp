# Plan de correcciones — compras, Uber y Admin móvil

Fecha: 2026-10-13. Estado: **implementado en rama; validación de cierre pendiente**.
Base: `feat/compras-uber-mobile`, auditoría hasta `f8c3de6`.
Referencia: [auditoría independiente](AUDITORIA_compras-uber-mobile.md#segunda-revisión-independiente--codex-2026-10-13).

**Checkpoint actual y siguiente tarea:** [traspaso a Claude](HANDOFF_CLAUDE_compras-uber-mobile.md).
Los bloques 1–5 tienen implementación y pruebas; el bloque 6 tiene R2 real y barrido
de navegador, pero no cámara física ni privacidad certificada. El bloque 7 tiene
checks locales y cambios de CI; falta revisión del PR. Se confirmó además que los
rechazos 413 del middleware no llevan cabeceras CORS: corregirlo primero al retomar.
El texto de abajo conserva el plan original; consultar el traspaso para el estado real.

Objetivo: cerrar los hallazgos de la auditoría y los pendientes declarados por Claude
antes del merge. Este plan no inicia S4 ni modifica el roadmap de PLAN_V2.
Los cambios se entregan en commits pequeños dentro de la rama actual, con pruebas
por bloque. No desplegar ni usar datos de producción para las pruebas.

## Orden de ejecución

| Bloque | Prioridad | Resultado | Dependencia |
|---|---|---|---|
| 1 | P1 | Artículos protegidos y Uber conciliado con el turno correcto | Ninguna |
| 2 | P1 | Creación de gastos idempotente y payload centralizado | Ninguna |
| 3 | P2 | Fotos consistentes, adjuntos reintentables y limpieza durable | Contrato idempotente del bloque 2 |
| 4 | P2 | Cola recuperable al navegar, recargar o perder conexión | Bloques 2 y 3 |
| 5 | Alcance pendiente | Catálogos compartidos, precio sugerido y retirada de componentes antiguos | Bloque 2 |
| 6 | Validación | Admin usable a 375 px y pruebas reales de fotos/R2 | Bloques anteriores |
| 7 | Cierre | Migraciones, regresión y evidencias para merge | Todos |

## 1. Integridad de pedidos y cortes Uber

Archivos principales: `routers/pedidos.py`, `routers/turnos.py`,
`tests/test_uber_eats.py` y pruebas de estados/artículos existentes.

- En `update_articulo_estado`, consultar y validar el pedido antes de mutar el
  artículo. Aplicar aislamiento estricto por sucursal en este endpoint y rechazar
  modificaciones cuando el pedido esté pagado, cancelado, dividido o entregado
  al repartidor. Conservar el flujo de bebidas y las transiciones legítimas de cocina.
- Revisar el orden de locks de pedido/artículos para que todas las operaciones
  involucradas usen un orden consistente; evitar introducir deadlocks.
- Regla propuesta para Uber: **el turno contable es el abierto al entregar al
  repartidor**, aunque el pedido se haya creado en otro turno. Si no hay turno
  abierto válido, rechazar la entrega con un error recuperable y no mutar nada.
  Aplicar las reglas de jornada existentes antes de elegir el turno.
- Serializar entrega y cierre mediante lock del turno y revalidación de su estado.
  El cierre debe usar el mismo protocolo de lock antes de sumar y congelar cifras.
  Revisar el cierre automático de jornada para que respete este protocolo y
  congele Uber; no ampliar aquí la reasignación del cobro normal.
- Para turnos cerrados, devolver las cifras Uber persistidas, sin recalcular el
  bloque congelado desde pedidos. Para abiertos, calcular los valores actuales.
- Reemplazar asserts `400 o 422` por payloads válidos y rechazo concreto de la
  regla de negocio. Usar artículos reales en las pruebas de edición.

Aceptación: T1 creado → T1 cerrado → T2 abierto → entrega Uber se contabiliza una
sola vez en T2; T1 permanece inmutable. Sin turno no hay entrega. Una carrera entre
cierre y entrega incluye la operación en un corte válido o la rechaza sin escritura
parcial. Probar aislamiento, terminalidad, bebidas y happy path. Las pruebas de
concurrencia se ejecutan en PostgreSQL, no se dan por cubiertas con SQLite.

## 2. Idempotencia de gastos y contrato único

Archivos principales: `models.py`, `schemas.py`, `routers/gastos.py`, migración
Alembic nueva, `useCrearGasto.ts`, Checkout, Rápido, FormModal y Registro rápido.

- Añadir `client_request_id` UUID opcional por compatibilidad con clientes previos.
  Usar unicidad por sucursal y un registro durable de operación con hash del
  payload normalizado, actor y gasto resultante. Conservar el registro si se borra
  el gasto para que un reintento tardío no lo recree.
- Crear la operación y el gasto en la misma transacción. Resolver colisiones de
  unicidad con rollback y lectura del resultado confirmado; no usar únicamente
  check-then-insert ni un lock en memoria.
- Misma clave y mismo contenido: devolver el mismo gasto. Misma clave con otro
  contenido: 409. Operación cuyo gasto fue eliminado: respuesta explícita sin
  recrearlo. Validar autorización y sucursal también en el camino de replay.
- Generar el UUID una sola vez al confirmar; conservar UUID, fecha y payload en
  todos los reintentos. No generar otro ID dentro de la función de envío.
- Unificar construcción y envío del payload. Cubrir también nómina sin perder
  su contrato distinto; todos los formularios deben usar el camino común.
- Separar el resultado de creación del resultado de fotos: persistir `gastoId`
  en cuanto se recibe, antes de iniciar las subidas. Reintentar fotos no debe
  volver a crear el gasto.

Aceptación: dos solicitudes concurrentes crean un solo gasto; respuesta perdida y
reintento devuelven el mismo ID; otra sucursal no recupera el resultado ajeno;
cambiar el contenido con la misma clave devuelve 409. Probar gasto rápido, gasto
con líneas y nómina, incluyendo validación fallida sin efectos parciales.

## 3. Fotos y ciclo de vida de adjuntos

Archivos principales: `services/storage.py`, `routers/gasto_adjuntos.py`,
`routers/gastos.py`, modelos/migraciones, composables y componentes de fotos.

- Garantizar WebP para **nuevas fotos guardadas**. Mantener compresión en el
  navegador como optimización y añadir normalización de imagen en backend para
  originales y HEIC; incorporar dependencias con `uv` y mantener coherencia con
  el archivo que instala Docker. Verificar soporte HEIC en la imagen de Docker.
- Decodificar imágenes reales; límites de bytes, dimensiones y píxeles; aplicar
  orientación y eliminar EXIF/GPS al producir WebP. Una cabecera válida sola no
  basta. Rechazar archivos corruptos con error legible. No conservar silenciosamente
  el original porque el WebP pese más.
- Evitar vista previa rota en navegadores sin HEIC: mostrar un estado explícito
  mientras el servidor convierte, o un mensaje comprensible si el archivo falla.
  Los adjuntos históricos conservan su MIME; mostrar incompatibilidad en el visor
  cuando corresponda, sin migración masiva implícita.
- Dar a cada foto un UUID estable y replay idempotente por gasto, con detección de
  contenido diferente. El límite de cinco debe comprobarse bajo lock del gasto;
  un replay no consume otra plaza. Proteger además subida contra borrado concurrente.
- Registrar tareas de borrado de storage en BD en la misma transacción que elimina
  adjunto/gasto. La tarea debe sobrevivir al cascade del gasto.
- Implementar un procesador con reintentos, backoff, exclusión entre workers y
  recuperación tras reinicio. Un fallo R2 deja la tarea pendiente, sin convertir
  una eliminación ya confirmada en un 500 ambiguo. Registrar intento, error y estado.
- Cubrir también limpieza de una subida cuyo commit falla; documentar la ventana
  de caída entre escritura del objeto y registro en BD y cómo reconciliar huérfanos.
- Revisar el middleware de tamaño: probar ruta con barra final y límite efectivo
  de lectura, además de `Content-Length`; no certificarlo solo por ese header.

Aceptación: JPEG, PNG y HEIC reales producen WebP visible y sin GPS; archivo corrupto
o excesivo se rechaza. Reintentar una foto no duplica adjuntos. Seis subidas concurrentes
no superan cinco. R2 caído al borrar mantiene limpieza pendiente; al recuperarse se
elimina el objeto. Probar reinicio del procesador y borrado repetido autorizado.

## 4. Recuperación de la cola optimista

Archivos principales: store nuevo de operaciones de gastos, persistencia IndexedDB,
`RegistroRapidoView.vue`, `useCrearGasto.ts` y entrada de navegación correspondiente.

- Mover cola y ejecución fuera de la vista a un store. Guardar operaciones y blobs
  en IndexedDB por usuario/sucursal; no almacenar fotos como cadenas en localStorage.
- Persistir la operación **antes** de limpiar el formulario. Si falla la persistencia,
  conservar captura y mostrar error. Guardar UUID, payload, `gastoId`, UUID de cada foto
  y progreso; distinguir creación pendiente, fotos pendientes, completo y error.
- Al recargar, convertir estados interrumpidos en pendientes recuperables. Reintentar
  con las mismas claves; no enviar bajo otra identidad ni tras logout sin validar sesión.
- Mantener acceso visible a pendientes al volver; proteger el cierre mientras haya
  escritura local sin confirmar. Gestionar cierre de sesión y descarte explícito sin
  confundir descartar la operación local con borrar un gasto confirmado.
- Mostrar “Reintentar fotos” para éxito parcial, conservando solo las fotos pendientes.
  Permitir una sola ejecución por operación, incluso ante doble tap o dos pestañas.

Aceptación: volver, cambiar de sección y recargar no pierde operaciones; respuesta
perdida no duplica; fotos parciales se recuperan sin crear otro gasto. Probar desconexión,
almacenamiento local fallido, cambio de usuario, doble reintento y reinicio de navegador.

## 5. Completar el plan de Gastos

- Crear store compartido de proveedores, artículos y categorías con estados de carga,
  error e invalidación tras CRUD; evitar respuestas obsoletas al cambiar identidad/sucursal.
- Sugerir `costo_estandar` al elegir artículo, sin sobrescribir precio capturado o una
  línea existente al editar. Permitir siempre precio manual.
- Completar la centralización del bloque 2 y eliminar llamadas duplicadas.
- Buscar referencias y sustituir usos antes de retirar `GastoForm.vue` y
  `GastosAnalytics.vue`. Confirmar que no se pierden funciones activas.

Aceptación: un CRUD de catálogo se refleja en todos los formularios; seleccionar
artículo ofrece precio editable; edición conserva el precio original; registro normal,
rápido y nómina siguen funcionando. Tests de lógica compartida y comprobación de tipos.

## 6. Validación móvil y R2 real

Barrido de navegador a 375 px: Dashboard, Usuarios, Turnos, Recursos Humanos, Gastos,
drawer y modales de Gasto/Usuario/Proveedor/Artículo. Revisar scroll, teclado, botones
de guardar/cancelar, navegación, errores y `safe-area-inset`. Repetir comprobaciones
de escritorio y un ancho de tablet después de corregir desbordes.

Probar en celular físico cámara trasera, galería, rotación/orientación, foto HEIC real,
cancelación del selector, red intermitente, carga parcial y visualización posterior.
Registrar dispositivo, sistema, navegador y resultados; la emulación no reemplaza esto.

R2: usar bucket privado de prueba y credenciales por variables de entorno; subir,
leer autenticado, borrar y verificar desaparición del objeto, además del flujo de
limpieza tras fallo. Confirmar que acceso directo no autenticado al bucket no expone
archivos. No pegar credenciales en documentos, logs o commits.

Dependencias externas pendientes: credenciales R2 de prueba y acceso a un celular.
Se puede completar el código y las pruebas locales antes; esos dos resultados siguen
marcados **no verificados** hasta obtener evidencia real.

## 7. Cierre y criterio de merge

- Ejecutar suite backend con `uv run pytest`, lint configurado y pruebas específicas
  de concurrencia contra PostgreSQL desechable. Crear DB limpia mediante Alembic y
  probar actualización desde el head previo con datos representativos.
- Ejecutar `pnpm exec vue-tsc --noEmit`, build y tests frontend de contratos, cola y
  lógica compartida. Verificar primero la coherencia de Vitest con el lockfile.
- Repetir flujos de pedidos normales, bebidas, división, cobro/propinas, corte,
  nómina y eventos WebSocket afectados por entrega y edición de artículos.
- Actualizar la auditoría con evidencia por hallazgo: corregido, validado o pendiente,
  indicando comando o prueba manual. No convertir “implementado” en “probado”.
- Merge solo con P1/P2 cerrados, alcance de Gastos completado, migraciones verificadas
  y evidencia móvil/R2 real. Si se decide reducir el alcance, documentar expresamente
  qué se separa y por qué antes de considerar cerrado el trabajo.

Primera tarea al retomar: corregir CORS de los rechazos 413 y añadir su regresión;
después seguir los pendientes concretos del documento de traspaso.
