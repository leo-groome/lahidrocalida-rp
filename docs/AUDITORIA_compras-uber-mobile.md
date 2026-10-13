# Walkthrough de auditoría — `feat/compras-uber-mobile`

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

## Pendientes antes de merge
1. Credenciales R2 (bucket privado + `STORAGE_BACKEND=r2` + 4 `R2_*` en Railway) y una prueba real de subida/lectura/borrado.
2. Probar cámara y HEIC en un celular.
3. Barrido visual del admin a 375 px en las secciones no vistas.
4. Decidir idempotencia de `/gastos`.
5. Deuda previa fuera de alcance: lockfile de pnpm sin vitest; warning de `CheckCircle` en `CajaView`; no hay servicio de frontend en el compose del repo.
