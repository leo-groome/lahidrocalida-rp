# Walkthrough de auditoría — `feat/compras-uber-mobile`

**Estado posterior a las correcciones de Codex (2026-10-13):**
[traspaso a Claude](HANDOFF_CLAUDE_compras-uber-mobile.md). Este walkthrough y la
segunda revisión conservan el diagnóstico previo; no tomar sus pendientes históricos
como una descripción del código actual. El traspaso detalla implementación, pruebas,
R2 real, pendientes restantes y el nuevo hallazgo CORS en respuestas 413.

13 commits, 47 archivos, +2646/−183 sobre `main`. Suite backend: 157 passed, 4 skipped. Build frontend limpio.
Orden de ejecución: **B (Uber Eats) → A (Gastos + foto) → C (Admin móvil)**, elegido por ROI: Uber toca dinero y corte de caja, así que va primero.

Cómo auditar: cada sección dice **qué se pidió → qué se hizo → por qué → cómo verificarlo → qué NO está cubierto**.

---

## 0. Decisiones transversales

| Decisión | Alternativa descartada | Razón |
|---|---|---|
| Storage de fotos en **Cloudflare R2** (S3-compatible, bucket privado) | Disco local / volumen Railway | El disco de Railway es efímero: cada deploy borraría las fotos. Elegido por el usuario. |
| Uber = **estado terminal nuevo `entregado_repartidor`** | Flag booleano en `pagado`, o `metodo_pago='uber'` | Un pedido que nunca llega a `pagado` queda fuera de **todas** las sumas existentes (`estado == 'pagado'`) por construcción, sin tocar decenas de queries. Elegido por el usuario. |
| Corte de turno = **bloque aparte** con columnas nuevas en `Turno` | Calcularlo al vuelo | El corte cerrado debe ser inmutable: los números se congelan al cerrar. |
| Fotos servidas **solo por endpoint autenticado**; el front las baja como blob | URLs firmadas / bucket público | Los tickets son datos del negocio; así el control de sucursal vive en un solo punto. |
| Conversión a WebP **en el navegador** | Pillow en backend | Evita una dependencia nueva y baja el peso antes de subir por red móvil. |

Reglas del usuario aplicadas: `uv`/`pnpm`, Docker, aislamiento por sucursal en cada query, validación por magic bytes, sin secretos en código.

---

## B. Uber Eats como canal aparte

**Pedido:** no se cobra en terminal; se marca entregado cuando llega el repartidor; fuera de las sumas normales; dinero entra por depósito a tarjeta. Luego: solo aparecer como segmento propio en el corte y en la auditoría de turno, discreto y bajo las propinas.

**Backend**
- `app/domain/estados.py`: `ENTREGADO_REPARTIDOR` en el enum y en `terminales()`. `transicion_permitida(origen, destino, rol, tipo_orden)`:
  - `entregado_repartidor` solo para `tipo_orden == "uber_eats"`.
  - Un Uber no puede ir a `cuenta_solicitada`, `pagado` ni `dividido`.
  - Roles: mesero, cajero, administrador.
- `routers/pedidos.py` (`update_pedido`): al entregar fija `fecha_pago` (hora de entrega, para ubicarlo en turno/día) y `turno_id`, marca artículos entregados, **ignora** `metodo_pago`/propinas y no dispara impresión ni WS de pago. `dividir` y `dividir_por_montos` devuelven 400 para Uber.
- `routers/turnos.py`: `_calcular_uber()`; `cerrar_turno` guarda `pedidos_uber`/`ventas_uber`; el resumen devuelve `uber_eats`. **No entra** a `total_esperado` ni `diferencia`.
- `routers/reportes.py`: `/dia/analytics` devuelve `uber_eats{pedidos,total}`; `/dia/tickets` incluye Uber (por `fecha_pago`) para que aparezca en la auditoría del turno.
- Migración `c3f1a9d27e50` (`turnos.pedidos_uber` int, `ventas_uber` numeric(10,2), default 0). `pedidos.estado` es varchar sin CHECK: sin cambio de esquema.

**Frontend:** `MeseroView` (botón "Entregado a Repartidor", sin solicitar cuenta), `CajaView` (sección Uber, tarjeta gris tenue bajo propinas en el corte, badge/filtro/subtotal en auditoría, excluido de "Total Filtro" y del mix de cobro), `TurnoModal`, store (`pedidosUber`; `pedidosCaja` y pendientes de pago lo excluyen; KDS lo oculta). Bonus: labels del Dashboard corregidos (`aqui`/`llevar`/`uber_eats`).

**Seguridad (commit `dd9079d`, hallazgos de revisión automática, verificados):**
1. `update_pedido` solo validaba sucursal para cajero → ahora todo rol no administrador.
2. `agregar-articulos`/`actualizar-articulos` permitían editar un Uber ya entregado (alteraba el total reportado) → bloqueado.
3. Se registra en log quién marca la entrega, para conciliar con Uber.
Revisión posterior con `security-review`: sin hallazgos ≥8 de confianza.

**Verificar:** `tests/test_uber_eats.py` (transiciones, corte separado, analytics, tickets, aislamiento de sucursal, no edición post-entrega), `tests/test_estados_pedido.py`.
**No cubierto / deuda:** pedidos Uber históricos ya cobrados como "llevar" no se migran. Sin PIN de admin para marcar entrega ni actor persistido (solo log). Cualquiera con rol permitido puede crear pedidos `uber_eats`. No hay conciliación del depósito contra banco.

---

## A. Gastos: foto del ticket y registro simple

**Pedido:** subir foto del ticket al comprar; registrar cualquier gasto de forma muy sencilla. Luego: todo en WebP, cámara directa, UI optimista en `/rapido`.

**Backend**
- `services/storage.py`: protocolo `Storage` (`guardar/leer/borrar`), `LocalStorage` (guarda contra path traversal con `is_relative_to`) y `R2Storage` (aioboto3, import perezoso). `get_storage()` exige las 4 vars `R2_*` con backend r2 y **lanza error si `ENVIRONMENT=production` con backend local** (evita perder fotos en silencio). `detectar_tipo()` por magic bytes: JPEG/PNG/WebP/HEIC; nada de SVG/HTML. Llaves generadas por el servidor (uuid, prefijo por sucursal). Tope 8 MB leído en chunks.
- `routers/gasto_adjuntos.py`: POST/GET/GET archivo/DELETE bajo `/gastos/{id}/adjuntos`. Roles administrador/compras/cajero. Máx. 5 fotos por gasto. 404 (no 403) para gastos de otra sucursal, **incluso administrador**. Headers: `nosniff`, `Content-Disposition: inline`, `Cache-Control: private`. El `content_type` guardado sale de lo detectado, nunca del cliente.
- Modelo `GastoAdjunto` + migración `d7a2e4b91c13` (índice por `gasto_id`, `storage_key` único).
- `routers/gastos.py`: proveedor opcional en directo/indirecto; detalles opcionales si hay `total_manual` ("compra rápida": monto + foto).
- Dependencias: `aioboto3` y `python-multipart` fijadas en `requirements.txt` **y** `pyproject.toml` (el Dockerfile instala con pip desde `requirements.txt`).

**Frontend**
- `composables/useAdjuntosGasto.ts`: `prepararFoto` convierte a WebP (1600 px, calidad 0.8) **al elegir** la foto; cae a JPEG o al original (HEIC). Subida después de crear el gasto, timeout 60 s.
- Subir **después** del POST: el gasto nunca falla por la foto; si falla la foto se avisa y el gasto queda guardado.
- `FotoTicketInput`: botón de cámara (`capture="environment"`) y botón de galería.
- `RegistroRapidoView`: monto + foto en una pantalla; **UI optimista**: limpia el formulario al instante, envía en segundo plano con lista de pendientes (enviando / ok / parcial / error+reintentar), aviso al cerrar con envíos en curso. `enviarGasto` extraído para envíos en paralelo.
- Historial: clip con contador y visor de fotos; "Compra rápida" para gastos sin proveedor.

**Seguridad (auditoría con `security-auditor`, commit `9375e57`):**
1. Multipart parseado **antes** de autenticar y sin tope → middleware 413 por `Content-Length` (>9 MB) en `POST */adjuntos`.
2. `python-multipart` 0.0.9 con CVE-2024-53981 → 0.0.32.
3. get/update/delete/list de gastos aislaban por sucursal solo para `compras` → ahora todo rol no administrador (404). El administrador conserva el filtro opcional `sucursal_id`, como en pedidos.
4. Al borrar un gasto, las fotos quedaban en R2 → se borran tras el commit (si el storage falla, se loguea y queda huérfano; preferible a una fila apuntando a nada).

**Verificar:** `tests/test_gasto_adjuntos.py` (formatos válidos, HTML renombrado a .jpg → 415, vacío, >límite, máx. 5, otra sucursal, rol sin permiso, borrado de archivo, guard de producción, credenciales R2, body gigante → 413, cajero ajeno → 404).
**No cubierto / deuda:**
- **R2 real nunca se probó** (sin credenciales); solo hay tests de configuración. Probado con storage local en Docker.
- Cámara en celular real, no probada (solo subida de archivo).
- EXIF/GPS: una foto que el navegador no pueda recomprimir se sube tal cual con su metadata.
- El tope de 5 fotos no es atómico bajo concurrencia (impacto: cuota).
- `/gastos` no tiene idempotencia: "Reintentar" tras respuesta perdida puede duplicar.
- Sin migrar del plan: store compartido de catálogos, precio sugerido, unificar payload de `GastoCheckout`/`GastoRapidoModal`, borrar `GastoForm.vue`/`GastosAnalytics.vue`.

---

## C. Admin en móvil

**Pedido:** que el admin funcione bien en móvil; que haya forma de moverse a otras áreas (botón al hub).

- `AdminSidebar`: bajo `lg` es un **drawer** (hamburguesa en `AdminTopbar`, backdrop, botón X); etiquetas y logout siempre visibles; sin dependencia de hover. En escritorio conserva el comportamiento de hover. Nuevo botón **Áreas** → `admin-hub` (antes no había forma de volver al hub desde el admin). Targets ≥44 px.
- `AdminView`: `h-dvh`, `viewport-fit=cover` en `index.html`; `window.location.reload()` reemplazado por remontado de la sección (`refreshKey`).
- Modales (`ProveedorFormModal`, `ArticuloFormModal`, `GastoFormModal`, `AdminModals`): pantalla completa en móvil, tarjeta desde `sm`.
- Tablas de Usuarios y Dashboard con `overflow-x-auto`; `GastosSection` y `GastosDashboard` sin desbordes.

**Por qué drawer y no barra inferior:** el menú tiene 8 entradas; una barra inferior no cabe.
**Verificar:** a 375 px solo se validó visualmente Gastos (analíticas) y el drawer.
**No cubierto:** Dashboard, Usuarios, Turnos, Recursos Humanos y los modales de Gasto/Usuario a 375 px no se abrieron en navegador. Falta `safe-area-inset` en padding inferior.

---

## Actualización posterior a la auditoría de Codex (2026-10-14)

Este documento describe el estado al commit `f8c3de6`. Las correcciones de Codex
(PR #10) están en [HANDOFF](HANDOFF_CLAUDE_compras-uber-mobile.md) y
[PLAN_CORRECCIONES](PLAN_CORRECCIONES_compras-uber-mobile.md); donde difieran, mandan esos.
Cambios hechos después, con su razón:

| Commit | Cambio | Por qué |
|---|---|---|
| `b8a4719` | Tarjeta **Compras** en `AdminHub` → `/rapido` | El administrador no tenía acceso directo al registro rápido; el router ya permitía su rol. |
| `2fbeec1` | `GET …/adjuntos/{id}/archivo` responde **404** si el archivo no está en el storage (`ObjetoNoEncontrado`) | Filas creadas con storage local antes de pasar a R2 daban 500 sin cabeceras CORS; el navegador lo mostraba como "CORS blocked". |
| (este push) | `AdjuntoBodyLimitMiddleware` se registra **antes** de `CORSMiddleware` | El 413 salía sin `Access-Control-Allow-Origin` (pendiente §1 del handoff). Test de regresión con `Origin` permitido; verificado que falla sin el cambio. |

Verificación local con **R2 real** (bucket del `.env`, no certifica producción):
subida de imagen pequeña y de JPEG de 3.8 MB desde `/rapido` → `POST …/adjuntos` 201,
objeto legible por `GET` (200 `image/webp`); llave inexistente → 404.
Lección operativa: un contenedor backend sin recrear (`docker compose up -d --build backend`)
corre código y variables viejos; síntoma: `POST …/adjuntos` sin respuesta.

Estados que cambiaron respecto a las secciones de arriba (resueltos por Codex, ver handoff):
R2 probado localmente; WebP garantizado por el backend (Pillow, sin EXIF); límite de 5 fotos
bajo lock; idempotencia de gastos y de adjuntos; limpieza durable de storage.
Siguen abiertos: cámara/HEIC en dispositivo físico, barrido a 375 px de las secciones del
admin no revisadas, y el plan de Gastos (store de catálogos, precio sugerido, borrar
`GastoForm.vue`/`GastosAnalytics.vue`).

---

## Pendientes antes de merge
1. Credenciales R2 (bucket privado + `STORAGE_BACKEND=r2` + 4 `R2_*` en Railway) y una prueba real de subida/lectura/borrado.
2. Probar cámara y HEIC en un celular.
3. Barrido visual del admin a 375 px en las secciones no vistas.
4. Decidir idempotencia de `/gastos`.
5. Deuda previa fuera de alcance: lockfile de pnpm sin vitest; warning de `CheckCircle` en `CajaView`; no hay servicio de frontend en el compose del repo.

---

## Segunda revisión independiente — Codex, 2026-10-13

Plan de ejecución: [PLAN_CORRECCIONES_compras-uber-mobile.md](PLAN_CORRECCIONES_compras-uber-mobile.md).

**Dictamen: no listo para merge.** Revisión del diff contra `main` hasta `f8c3de6`.
Se verificó el código y se ejecutaron `uv run pytest -q` (157 passed, 4 skipped),
`pnpm run build` y `pnpm exec vue-tsc --noEmit` (ambos pasan).
El script `build` solo ejecuta Vite: no sustituye la comprobación explícita de TypeScript.
No se ejecutó R2 real, celular físico ni barrido visual del admin; esas pruebas siguen abiertas.
Esta revisión no implementa correcciones ni certifica migraciones contra PostgreSQL.

### Hallazgos antes de continuar

1. **P1 — Reintentar puede duplicar dinero registrado.**
   `RegistroRapidoView.vue:314` vuelve a llamar a `enviarGasto`, que hace un POST nuevo
   sin identificador estable. Si el servidor hizo commit pero se perdió la respuesta,
   el segundo intento crea otro gasto. No basta deshabilitar el botón durante el envío.
   Corregir con clave estable por operación, unicidad en BD y recuperación del resultado
   anterior; probar respuesta perdida y solicitudes concurrentes. Esto debe resolverse
   antes de publicar la UI optimista con reintentos.

2. **P1 — La terminalidad de Uber no protege la edición de estado de sus artículos.**
   `pedidos.py:1128-1172`, `PUT /pedidos/articulos/{id}`, permite cambiar `estado_item`
   sin comprobar el estado terminal del pedido ni su sucursal. Un mesero/cocina/admin
   puede pasar un artículo de un Uber ya entregado a `pendiente`; también puede hacerlo
   desde otra sucursal si conoce el ID. El endpoint existía previamente, pero la nueva
   protección post-entrega no lo cubre. No cambia el total, sí permite alterar artículos
   que se documentan como inmutables. Validar sucursal y terminalidad antes de mutar;
   probar petición válida, terminal y sucursal ajena con artículos reales.

3. **P1 — Uber puede incorporarse a un turno que ya fue cerrado.**
   Crear un pedido asigna `turno_id` (`pedidos.py:257`); entregar solo busca otro turno
   si ese campo es nulo (`pedidos.py:1000`). Escenario: crear Uber en T1, cerrar T1,
   abrir T2 y entregar. El pedido conserva T1: el corte congelado de T1 no lo incluyó
   y T2 tampoco lo incluye. `obtener_resumen_turno` calcula Uber desde pedidos vivos,
   por lo que además puede diferir de las columnas congeladas del turno cerrado.
   Definir la regla para pedidos pendientes entre turnos, protegerla contra cierre
   concurrente y probar este escenario. Es una brecha del nuevo canal aunque el
   patrón de asignación ya exista en el cobro normal.

4. **P2 — La cola optimista desaparece con navegación interna y no conserva errores.**
   `RegistroRapidoView.vue:293-294` protege únicamente `beforeunload`; `volver()` usa
   Vue Router sin guard. Al salir se pierde la lista local aunque las promesas puedan
   seguir ejecutándose. Si fallan, no hay UI para recuperar el gasto/fotos. Recargar
   también pierde pendientes en error/parcial, porque el aviso solo considera
   `enviando`. Mantener las operaciones fuera de la vista o impedir salida mientras
   haya trabajo sin resolver, con recuperación explícita. Probar volver durante envío,
   error posterior al desmontaje y fotos parcialmente fallidas.

5. **P2 — Borrar un adjunto puede devolver error después de haberlo eliminado de BD.**
   `gasto_adjuntos.py:168-169` confirma la eliminación antes de borrar en storage y no
   captura el fallo. Si R2 falla, queda archivo huérfano, se devuelve 500 y reintentar
   devuelve 404: se perdió la referencia necesaria para limpiar. El borrado de gasto
   completo captura el error, pero solo registra un warning; tampoco tiene limpieza
   posterior durable. Registrar tareas de limpieza reintentables y probar storage caído.

### Correcciones al alcance declarado

- **“Todo en WebP” no está garantizado.** `useAdjuntosGasto.ts:30` conserva el original
  si la conversión pesa más, incluso cuando sí pudo decodificarlo. También conserva
  originales ante fallo de decodificación. HEIC aceptado por el backend no implica
  HEIC visible en el visor, que solo usa `<img>` con un blob. Los tests HEIC usan
  cabeceras sintéticas, no una foto decodificable. Validar con archivos reales y
  definir conversión o mensaje de incompatibilidad antes de dar este requisito por cerrado.
- Algunos tests Uber aceptan **400 o 422** (`test_uber_eats.py:91,165,167`). Un 422
  puede ocurrir antes de entrar a la regla de negocio; esos asserts no demuestran
  necesariamente el bloqueo descrito. Usar payloads válidos y exigir el rechazo
  específico de dividir/editar Uber.
- El store compartido, precio sugerido y unificación del payload siguen sin hacerse:
  hay POST directos en Checkout, Rápido y FormModal además del composable.
  `GastoForm.vue` y `GastosAnalytics.vue` siguen presentes. Es deuda de alcance pendiente,
  no una validación completada por este PR.

### Puertas de salida

Primero corregir P1 y añadir pruebas de regresión; después P2 y la captura/visualización
de fotos. Completar el barrido de Dashboard, Usuarios, Turnos, Recursos Humanos y
modales a 375 px. Mantener R2 real y cámara/HEIC como **no verificados** hasta disponer
de credenciales de prueba y un dispositivo físico. La suite local usa SQLite por
defecto y no certifica locks ni migraciones de PostgreSQL. El plan de Gastos requiere
implementación o una decisión explícita de separarlo del alcance del merge.
