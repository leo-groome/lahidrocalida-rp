# Traspaso a Claude — compras, Uber, Admin móvil y R2

Fecha: 2026-10-13. Rama: `feat/compras-uber-mobile`. Base del trabajo de Claude:
`f8c3de6`. Las correcciones descritas aquí se prepararon después de esa base.
**Estado: implementación y validación local avanzadas; no aprobado para merge.**

Commits de implementación: `1840f38` (backend) y `760d98c` (frontend).
PR en borrador: [#10 — tickets de gastos en R2, canal Uber separado y Admin móvil](https://github.com/leo-groome/lahidrocalida-rp/pull/10).

Leer primero este archivo, después [la auditoría](AUDITORIA_compras-uber-mobile.md)
y [el plan de correcciones](PLAN_CORRECCIONES_compras-uber-mobile.md). Los hallazgos
originales de la auditoría describen el estado anterior, no el código corregido.
También siguen aplicando AGENTS.md y los documentos de contexto del proyecto.
No comenzar S4 ni asumir que esto ya está en producción.

## 1. Primera tarea al retomar

**Corregir CORS en el rechazo temprano de uploads.** Se comprobó al cerrar esta sesión:
un POST a `/gastos/1/adjuntos` con un `Origin` permitido y `Content-Length: 10485760`
devuelve **413 sin `Access-Control-Allow-Origin`**. La conexión con R2 funciona;
este fallo está en la respuesta de error de la API.

`app/main.py` registra `AdjuntoBodyLimitMiddleware` después de `CORSMiddleware`,
dejando el limitador por fuera del procesamiento CORS. Revisar el orden y agregar
una regresión HTTP con Origin permitido que exija 413 **y** sus cabeceras CORS.
Mantener el límite real antes del parser multipart; no regresar a validar solo
Content-Length. Probar también Origin no permitido y barra final de la ruta.
Este pendiente está documentado, **no corregido** en este checkpoint.

Después, revisar el diff completo, completar las verificaciones pendientes de
§5 y comprobar el CI del PR antes de plantear el merge.

## 2. Cambios implementados

### Pedidos Uber y artículos

- `routers/pedidos.py`: la edición de estado de un artículo bloquea primero el
  pedido y después el artículo. Exige misma sucursal, incluso para administrador,
  y rechaza pedidos terminales antes de mutar. Agregar/actualizar artículos también
  bloquean el pedido para serializarse con la entrega terminal.
- La entrega Uber usa **el turno abierto al entregar**, aunque la creación haya
  ocurrido en T1 y la entrega en T2. Sin turno abierto devuelve 409 sin confirmar
  cambios. El turno se bloquea para serializar entrega y cierre.
- `routers/turnos.py`: el cierre bloquea el turno antes de sumar y congelar;
  el resumen de un turno cerrado usa las cifras Uber persistidas.
- `models.py`: el índice parcial de turno abierto tiene también `sqlite_where`
  para representar la misma regla en tests SQLite.
- Se endurecieron tests Uber para exigir rechazos de negocio con payloads válidos;
  se añadieron terminalidad, sucursal ajena, T1/T2 y ausencia de turno.
- **Corrección al plan:** `services/jornada.py` actualmente reconcilia asistencias;
  los turnos no se cierran automáticamente por jornada. Se conservó ese comportamiento.

### Idempotencia de gastos

- `GastoCreate.client_request_id` es UUID opcional por compatibilidad.
- `OperacionGasto` conserva sucursal, actor, UUID, hash del payload y referencia
  al gasto. Unicidad por `(sucursal_id, client_request_id)` en BD.
- Operación y gasto se crean en la misma transacción. La carrera se resuelve con
  unicidad, rollback y lectura del resultado confirmado.
- Mismo UUID/contenido/actor devuelve el mismo gasto; contenido diferente devuelve
  409; actor diferente, 403. Al borrar el gasto queda una operación sin referencia:
  un replay devuelve 410 y no recrea el gasto.
- El frontend guarda un snapshot estable de payload, UUID y fecha. El único POST
  de creación de gastos del frontend está en `stores/gastos-pendientes.ts`.
- Compra rápida, compra con líneas y nómina tienen regresiones de replay.

### Fotos, WebP y limpieza de storage

- `services/imagenes.py`: Pillow + pillow-heif decodifican JPEG/PNG/WebP/HEIC reales,
  aplican orientación, limitan a 40 millones de píxeles de entrada y 1600 px de lado
  de salida, eliminan metadata y guardan **WebP**. Se rechazan imágenes corruptas.
- La compresión en el navegador es una optimización; el backend garantiza el
  formato de nuevas fotos. No hay conversión masiva de adjuntos históricos.
- Uploads llevan UUID de foto estable en `client_request_id` como query param;
  hash del contenido detecta reutilización con otros bytes. La cuota de cinco
  se comprueba bajo lock del gasto; un replay no consume otra plaza.
- `StorageBorrado` es una cola durable independiente del gasto. Borrar adjunto o
  gasto registra limpieza en la misma transacción que borra sus filas. El borrado
  repetido de un adjunto bajo un gasto autorizado devuelve 204.
- Antes de escribir un objeto se confirma una tarea de posible huérfano con demora
  de una hora. Un commit exitoso de adjunto elimina esa tarea; un fallo o caída
  conserva su referencia para limpieza. El put tiene timeout de 60 s.
- `storage_cleanup.py`: consumidor desde lifespan, lotes de diez cada 30 s,
  `FOR UPDATE SKIP LOCKED`, backoff hasta una hora y recuperación por rollback.
  Se probó fallo de storage, reintento y fallo de commit después del put.
- `AdjuntoBodyLimitMiddleware` limita bytes reales antes del parser, con o sin
  Content-Length y con barra final. Su respuesta CORS queda pendiente según §1.

### Cola recuperable y formularios

- `gasto-queue-db.ts`: IndexedDB conserva payload y archivos antes de limpiar la
  captura; si falla esa escritura, el formulario conserva lo capturado.
- `gastos-pendientes.ts`: Pinia conserva ejecución fuera de la vista, separa creación
  del gasto y subida de fotos, persiste `gastoId` antes de subir y reintenta solo
  fotos cuando el gasto ya existe. No ejecuta bajo otra identidad/sucursal.
- Se usan Web Locks cuando están disponibles; sin ellos la unicidad del backend
  sigue evitando duplicados entre pestañas. El reintento tras recarga es manual.
- `GastosPendientesLink` permite volver a pendientes desde las cabeceras operativas
  y Admin. Descartar un pendiente local no borra un gasto confirmado.
- `useCrearGasto.ts` ahora exporta `useGastoSubmission`; se retiraron helpers antiguos
  sin consumidores. Rechazos definitivos 400/422 permiten corregir captura; errores
  ambiguos conservan el snapshot original.
- La captura de fotos expone su estado de preparación y bloquea guardar mientras
  se convierte la selección. HEIC no decodificable muestra aviso en vez de preview roto.
- `gasto-error.ts` convierte errores de red/validación en mensajes legibles.

### Catálogos, precio sugerido y móvil

- `catalogos-gastos.ts`: carga compartida, deduplicación, errores visibles e
  invalidación tras CRUD. Respuestas de identidad anterior no pisan datos actuales.
  Formularios, historial, resolver y vistas de catálogos consumen este store.
  Artículos/categorías siguen siendo catálogos globales en el backend existente;
  no se añadió sucursal a sus modelos.
- Precio sugerido desde `costo_estandar`, preservando importes y ediciones manuales.
- Eliminados `GastoForm.vue` y `GastosAnalytics.vue` después de comprobar referencias.
- Padding de safe area en Admin, Registro rápido y botones de modales.
- Barrido del navegador a 375 px: Dashboard, Usuarios, Turnos con datos, Recursos
  Humanos con datos y Anomalías, Gastos, modal de Gasto y modal de Usuario.
  Sin desborde del contenedor principal en las mediciones realizadas. Dashboard
  comprobado también a 768 y 1280 px. Esto **no sustituye** un celular físico.

### Docker y CI

- Docker instala con `uv sync --frozen --no-dev --no-install-project` desde
  `pyproject.toml` y `uv.lock`; uv fijado a 0.12.10. Copia `/opt/venv` al runtime
  y conserva usuario no root y arranque con Alembic.
- Pillow/pillow-heif están en el proyecto y el lock; también se actualizaron las
  dependencias del archivo legado `requirements.txt`.
- CI frontend ahora ejecuta Vitest. CI backend añade migraciones y pruebas de
  concurrencia contra su PostgreSQL desechable. La suite general declara SQLite
  explícitamente en lugar de variables de DB que conftest no consumía.
- El lockfile raíz ya contiene Vitest; el lockfile anidado de frontend es legado.
  No asumir que la nota anterior de «sin Vitest en lock» describe el workspace actual.
- Estos cambios de CI se verificaron localmente; confirmar sus resultados en GitHub.

## 3. Migraciones nuevas

Cadena: `d7a2e4b91c13` → `e8b3c5d90142` → `f9c4d6e01253`.

- `e8b3c5d90142_operaciones_gasto.py`: registro durable de idempotencia.
- `f9c4d6e01253_storage_lifecycle.py`: UUID/hash en adjuntos y cola de limpieza.

Probados en PostgreSQL aislado: baseline completo → head, downgrade al head previo
y upgrade con un gasto/catálogos ficticios existentes. No se migró producción.
En rollout, actualizar backend y sus migraciones antes de habilitar el frontend nuevo;
un backend anterior no protege los UUID enviados por el cliente.

## 4. Evidencia de validación

| Verificación | Resultado / límite |
|---|---|
| Suite backend final, SQLite | **182 passed, 7 skipped**, 58 warnings de deprecación |
| Tres carreras en PostgreSQL | Pasan: creación concurrente, cuota de fotos, cierre vs entrega Uber |
| Subset PostgreSQL de gastos/adjuntos/Uber | **43 passed**; anterior a los últimos tres casos añadidos |
| Últimos casos de gastos/adjuntos | **31 passed** en SQLite; incluyen commit interrumpido, replay con cuota llena y nómina/líneas |
| Ruff check + format | Pasan, 76 archivos comprobados |
| Frontend Vitest | **21 tests**, cinco archivos, pasan |
| `pnpm exec vue-tsc --noEmit` | Pasa |
| Build final frontend | Pasa; warning existente de import estático/dinámico de auth |
| Docker | Build con uv pasa; HEIC sintético → WebP probado dentro de la imagen |
| Navegador: persistencia | POST bloqueado → navegar a Admin → recargar Registro rápido → reintentar; exactamente un gasto ficticio |
| Navegador: HEIC | Selección de HEIC sintético desde galería; un adjunto guardado. No cámara física |
| R2 directo | Subida, lectura exacta y borrado de imagen sintética pasan |
| API + R2 real | Crear gasto, convertir foto, replay sin duplicado, leer y borrar vía outbox pasan, usando DB aislada |
| Dominio R2 | `https://assets.lahidrocalida.com` devuelve **404** para el objeto temporal; no prueba CORS ni certifica privacidad |
| Rechazo temprano con Origin permitido | **413 sin cabecera CORS**: pendiente confirmado |

Las tres carreras se omiten intencionalmente en SQLite y sí se ejecutaron aparte en
PostgreSQL. No atribuir una ejecución completa de la suite a PostgreSQL. Los tests
de cola usan persistencia simulada; la recuperación IndexedDB real se ejercitó en
el navegador. Los tests de fotos ahora usan imágenes decodificables, no solo cabeceras.

Capturas con datos ficticios:
[Dashboard](evidencias/compras-uber-mobile/dashboard-375.png),
[Usuario](evidencias/compras-uber-mobile/usuario-modal-375.png),
[Gasto](evidencias/compras-uber-mobile/gasto-modal-375.png),
[Turnos](evidencias/compras-uber-mobile/turnos-375.png),
[Recursos Humanos](evidencias/compras-uber-mobile/recursos-humanos-375.png).

## 5. Pendientes concretos antes de merge

1. Corregir y probar el CORS de respuestas 413 según §1.
2. Revisar el diff completo y el CI del PR; repetir los tres casos añadidos también
   en PostgreSQL. Revisar multiworker/reinicio del consumidor de limpieza: hay
   exclusión por lock y persistencia probadas, no un ensayo completo de kill/restart.
3. Celular físico: cámara, galería con HEIC real, orientación, legibilidad, teclado,
   safe area, red intermitente y recuperación de fotos parciales. El usuario dijo
   tener celular disponible; no se registró todavía sistema/navegador ni resultados.
   Usar un entorno de prueba HTTPS: `crypto.randomUUID` requiere contexto seguro;
   localhost es válido para escritorio, una IP HTTP en el celular puede no serlo.
4. Privacidad R2: revisar custom domain, bucket asociado, Cloudflare Access si aplica
   y estado de `r2.dev`. El usuario confirmó dominio habilitado. Su 404 puede indicar
   asociación/ruta/acceso diferente; no deducir «bucket privado» de ese resultado.
   La app no necesita un dominio público para servir tickets.
5. Repetir flujos operativos completos en UI: pedidos normales/bebidas, división,
   cobro/propinas/corte, nómina y eventos WS. La suite automatizada pasó; no afirmar
   que hubo un barrido manual completo de Caja/KDS/Mesero en esta sesión.
6. Confirmar variables R2 en Railway antes del rollout. Solo se verificó `.env`
   local y R2 remoto; no se inspeccionó configuración de Railway ni se desplegó.

Referencia de privacidad: [Cloudflare R2 public buckets](https://developers.cloudflare.com/r2/buckets/public-buckets/).
CORS no reemplaza autorización. No cambiar a bucket público para arreglar uploads.

## 6. Configuración local y entorno de prueba

El usuario agregó credenciales a `apps/backend/.env`. Se comprobó acceso real, pero
el selector seguía en local; Codex cambió **solo `STORAGE_BACKEND=r2`**, conservando
las credenciales. `.env` está ignorado y no debe entrar al PR. No copiar valores a
documentación, issues, logs ni fixtures. Reiniciar procesos para que lean el cambio.

Se creó el contenedor aislado `hidro-audit-postgres` (PostgreSQL 16), puerto local
**55438**, usuario `audit`, contraseña **de prueba** `audit-local-only`.

- DB `audit`: desechable para pytest. **conftest hace drop/create de tablas** cuando
  se usa `TEST_DATABASE_URL` PostgreSQL. Nunca apuntar a Neon, producción ni audit_ui.
- DB `audit_ui`: migrada al nuevo head, con datos ficticios y pruebas de navegador.
- Backend de prueba: puerto **8015**, storage local forzado a `/tmp/hidro-audit-uploads`.
- Frontend de prueba: puerto **5175**, API `http://127.0.0.1:8015`.
- Sesión de navegador: `hidro-audit-mobile` (agent-browser), aislada del navegador del usuario.
- Imagen Docker construida: `hidro-audit-backend`.

Los procesos pueden seguir activos tras el traspaso. Inspeccionarlos antes de iniciar
otros; reiniciar el backend de prueba para cargar el código final, porque se inició
sin reload. Los adjuntos de audit_ui creados en UI son locales: no mezclar esa DB con
R2 sin recrear los datos ficticios. Los objetos sintéticos de las pruebas R2 se borraron.
Scripts de semillas y prueba API usados en `/tmp` son temporales y no se versionan.

Comandos principales, desde `apps/backend`:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .

# Solo la base desechable audit; este test setup elimina tablas.
TEST_DATABASE_URL=postgresql://audit:audit-local-only@127.0.0.1:55438/audit \
  uv run pytest tests/test_compras_concurrencia.py tests/test_gastos_idempotencia.py \
  tests/test_gasto_adjuntos.py tests/test_uber_eats.py -q

# No toca la DB: crea y borra únicamente su imagen sintética en R2.
uv run python -m scripts.verify_r2_storage
R2_AUDIT_PUBLIC_URLS=https://assets.lahidrocalida.com \
  uv run python -m scripts.verify_r2_storage
```

Desde `apps/frontend`: `pnpm test`, `pnpm exec vue-tsc --noEmit`, `pnpm run build`.
No hubo merge, despliegue ni migración de producción. El PR se deja en borrador
para que Claude revise y cierre los pendientes, no para omitirlos.
