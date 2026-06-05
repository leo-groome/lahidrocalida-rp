# LA HIDROCÁLIDA — SCOPE DEL SISTEMA POS

**Fecha:** 2026-06-04  
**Versión del sistema:** 1.1.0  
**Estado global:** ~88-92% feature-complete. Producción activa.

---

## 1. DESCRIPCIÓN DEL PROYECTO

Sistema POS (Point of Sale) completo para pozolería, diseñado para el flujo:
**Mesero toma orden → Cocina prepara → Cajero cobra**

Soporte para 4 roles de usuario con interfaces dedicadas, comunicación en tiempo real vía WebSocket, y PWA para instalación en tablets/pantallas de cocina.

**Repositorio:** https://github.com/leo-groome/lahidrocalida-rp  
**Frontend production:** https://lahidrocalida.vercel.app  
**DB:** PostgreSQL en Neon Cloud (Azure westus3)  
**Backend deploy:** Docker (Railway)

---

## 2. STACK TECNOLÓGICO CONFIRMADO

| Capa | Tecnología | Versión |
|------|-----------|---------|
| Frontend | Vue 3 + TypeScript | 3.5.21 / 5.8.3 |
| CSS | Tailwind CSS | 4.1.13 |
| State | Pinia | 3.0.3 |
| Router | Vue Router | 4.6.3 |
| HTTP | Axios | 1.12.2 |
| Charts | Chart.js + vue-chartjs | 4.5.1 / 5.3.3 |
| Build | Vite | 7.1.7 |
| PWA | vite-plugin-pwa | 1.2.0 |
| Backend | FastAPI | 0.117.1 |
| ORM | SQLAlchemy | 2.0.43 |
| DB | PostgreSQL (Neon) | — |
| Auth | JWT (python-jose) + Argon2 | — |
| Migrations | Alembic | 1.13.2 |
| WebSocket | websockets | 11.0.3 |
| Package mgr | pnpm (frontend), pip (backend) | — |
| Container | Docker | — |

---

## 3. ESTRUCTURA DEL MONOREPO

```
lahidrocalida-rp/
├── backend/                    # FastAPI REST API
│   ├── app/
│   │   ├── core/config.py      # Settings, env vars
│   │   ├── db/session.py       # SQLAlchemy engine
│   │   ├── models.py           # ORM models (291 líneas)
│   │   ├── schemas.py          # Pydantic schemas
│   │   ├── auth.py             # JWT + hashing
│   │   ├── main.py             # App init + CORS
│   │   ├── websocket_manager.py # Connection manager (282 lín)
│   │   ├── websocket_routes.py  # WS endpoints
│   │   └── routers/
│   │       ├── auth.py         # Login
│   │       ├── users.py        # CRUD usuarios
│   │       ├── products.py     # CRUD platillos
│   │       ├── pedidos.py      # Órdenes (1333 lín - core)
│   │       ├── gastos.py       # Gastos (23KB)
│   │       ├── propinas.py     # Tips
│   │       ├── reportes.py     # Reportes diarios
│   │       ├── turnos.py       # Turnos (32KB)
│   │       └── admin.py        # Admin analytics (34KB)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/pos-system/        # Vue 3 SPA
│   ├── src/
│   │   ├── views/              # 6 vistas principales
│   │   ├── components/         # 26 componentes
│   │   ├── stores/             # 2 Pinia stores
│   │   ├── services/           # WebSocket + Print
│   │   ├── router/             # Routes + guards
│   │   ├── api/                # Axios client
│   │   ├── utils/              # dateUtils
│   │   └── types.ts            # TypeScript interfaces
│   ├── vite.config.ts          # Build + PWA config
│   └── package.json
├── print_service/              # Servicio impresora térmica (Windows)
├── alembic/                    # Migraciones DB
├── AGENTS.md                   # Guidelines para AI agents
└── README.md                   # Docs generales
```

---

## 4. BASE DE DATOS — MODELOS

| Tabla | Propósito | Campos clave |
|-------|-----------|-------------|
| **Sucursal** | Sucursal del restaurante | id, nombre, direccion |
| **Usuario** | Cuentas de staff | id, nombre, rol, pin (argon2), activo, sucursal_id |
| **Platillo** | Menú | id, nombre, precio, categoria, kds_name, estado (disponible/no_disponible) |
| **Pedido** | Órdenes | id, numero_display, mesa, total, estado, metodo_pago, propina_efectivo, propina_tarjeta, tipo_orden, fecha_creacion, fecha_pago, **turno_id** |
| **ArticuloPedido** | Items en orden | id, pedido_id, platillo_id, cantidad, precio_cobrado, modificaciones, estado_item |
| **Proveedor** | Proveedores | id, nombre, telefono, notas, sucursal_id |
| **CategoriaArticulo** | Categorías de gasto | id, nombre |
| **Articulo** | Insumos/inventario | id, nombre, unidad, costo_estandar, categoria_id |
| **Gasto** | Registro de gastos | id, proveedor_id, tipo_gasto, metodo_pago, total, turno_id |
| **GastoDetalle** | Líneas de gasto | id, gasto_id, articulo_id, cantidad, precio_unitario |
| **Turno** | Turno de caja | id, sucursal_id, usuario_id, fecha_apertura, fecha_cierre, estado, total_inicial |
| **TurnoDenominacion** | Conteo de efectivo | id, turno_id, tipo, denominacion, cantidad, subtotal |

**Relaciones clave:**
- Sucursal → Usuario, Pedido, Gasto (1:many)
- Pedido → ArticuloPedido (1:many, cascade delete)
- Gasto → GastoDetalle (1:many, cascade delete)
- **Turno → Pedido (1:many)** — cada pedido lleva `turno_id`; se inyecta automáticamente en el backend al crear la orden; sin turno activo → 400
- **Turno → Gasto (1:many)** — gastos ligados al turno explícitamente

---

## 5. API ENDPOINTS — RESUMEN COMPLETO

### Auth `/auth`
| Método | Ruta | Función | Auth |
|--------|------|---------|------|
| POST | `/auth/login-simple` | Login staff JSON (`user_id` + `pin`) | — |
| POST | `/auth/login-admin` | Login admin con usuario administrador + PIN (payload legado: `email`, `password`) | — |
| POST | `/auth/asistencia` | Clock-in/out público con PIN | — |
| POST | `/auth/login` | Login OAuth2 form | — |
| GET | `/auth/me` | Usuario actual | Bearer |
| GET | `/auth/users` | Lista usuarios para selector login | — |

### Usuarios `/usuarios`
| Método | Ruta | Función | Rol |
|--------|------|---------|-----|
| POST | `/usuarios/` | Crear usuario | Admin |
| GET | `/usuarios/` | Listar todos | Auth |
| PUT | `/usuarios/{id}` | Actualizar parcial; conserva campos omitidos y PIN vacío | Admin |
| DELETE | `/usuarios/{id}` | Desactivar | Admin |

### Platillos `/platillos`
| Método | Ruta | Función | Rol |
|--------|------|---------|-----|
| GET | `/platillos` | Listar menú | Auth |
| POST | `/platillos/` | Crear platillo | Admin |
| PUT | `/platillos/{id}` | Editar | Admin |
| PATCH | `/platillos/{id}/disponibilidad` | Toggle disponible | Cocina/Admin |
| GET | `/platillos/ordenados-popularidad` | Top ventas | Auth |
| DELETE | `/platillos/{id}` | Eliminar | Admin |

### Pedidos `/pedidos` (CORE — 1333 líneas)
| Método | Ruta | Función | Rol |
|--------|------|---------|-----|
| POST | `/pedidos/` | Crear orden | Mesero/Cajero/Admin |
| GET | `/pedidos` | Listar activos del día | Auth |
| GET | `/pedidos/{id}` | Detalle orden | Auth |
| PUT | `/pedidos/{id}` | Actualizar estado | Role-based |
| PUT | `/pedidos/{id}/agregar-articulos` | Agregar items | Mesero/Admin |
| PUT | `/pedidos/{id}/actualizar-articulos` | Editar/eliminar items | Mesero/Cajero/Admin |
| PUT | `/pedidos/articulos/{id}` | Actualizar estado item | Cocina/Mesero/Admin |
| POST | `/pedidos/{id}/dividir` | Dividir cuenta por items | Admin |
| POST | `/pedidos/{id}/dividir_por_montos` | Dividir cuenta por montos | Admin |
| POST | `/pedidos/{id}/imprimir` | Imprimir ticket manual | Auth |

**Estados de orden:** `pendiente → preparando → listo → entregado → cuenta_solicitada → pagado` (o `cancelado`/`dividido`)

**Transiciones por rol:**
- Mesero: pendiente → entregado → cuenta_solicitada
- Cocina: pendiente → preparando → listo
- Cajero: entregado → pagado/cancelado
- Admin: cualquier transición

### Reportes `/reportes`
| Método | Ruta | Función | Rol |
|--------|------|---------|-----|
| GET | `/reportes/dia/tickets` | Tickets del día (pagados + cancelados) | Cajero/Admin |
| GET | `/reportes/dia/analytics` | Analytics diario | Cajero/Admin |

### Gastos `/gastos`
| Método | Ruta | Función | Rol |
|--------|------|---------|-----|
| GET/POST/PUT | `/gastos/proveedores` | CRUD proveedores | Admin/Compras/Cajero |
| GET/POST/PUT | `/gastos/categorias-articulo` | CRUD categorías | Admin/Compras/Cajero |
| (más endpoints) | `/gastos/*` | Registro y reporte de gastos | — |

### Propinas `/propinas`
| Método | Ruta | Función | Rol |
|--------|------|---------|-----|
| GET | `/propinas/reporte` | Reporte propinas por mesero/día | Cajero/Admin |
| GET | `/propinas/detalle` | Detalle propinas por orden | Cajero/Admin |

### Turnos `/turnos`
| Método | Ruta | Función | Rol |
|--------|------|---------|-----|
| POST | `/turnos/iniciar` | Abrir turno con denominaciones iniciales | Cajero/Admin |
| GET | `/turnos/activo` | Turno activo de la sucursal | Cajero/Admin |
| GET | `/turnos/{id}/resumen` | Resumen detallado (ventas, propinas, gastos, comandas) filtrado por turno_id | Cajero/Admin |
| POST | `/turnos/{id}/cerrar` | Cierre de turno con conteo final de denominaciones | Cajero/Admin |
| GET | `/turnos/historial` | Historial de turnos cerrados | Admin |

**Comportamiento clave:**
- Solo existe **un turno activo por sucursal** (índice unique parcial en DB)
- `turno_id` se auto-inyecta en cada `POST /pedidos/` desde el turno activo
- Resumen y cierre filtran pedidos por `turno_id`, no por rango de fecha — correcto ante cambios de día

### Admin `/admin`
| Método | Ruta | Función | Rol |
|--------|------|---------|-----|
| GET | `/admin/analytics` | Analytics por rango de fechas | Admin |

### WebSocket
| Protocolo | Ruta | Función | Auth |
|-----------|------|---------|------|
| WS | `/ws/{client_type}?token={JWT}` | Tiempo real (kds/caja/mesero) | Bearer |
| GET | `/ws/stats` | Conexiones activas | — |

---

## 6. ROLES Y PERMISOS

| Rol | Acceso Frontend | Permisos Backend |
|-----|----------------|-----------------|
| **mesero** | `/mesero` | Crear pedidos, agregar items, marcar entregado |
| **cajero** | `/caja` | Cobrar, propinas, reportes diarios, turnos |
| **cocina** | `/kds-view`, `/kds-manager` | Ver pedidos, marcar preparando/listo, toggle disponibilidad |
| **administrador** | Todos | Todo lo anterior + usuarios, analytics, dividir cuenta |
| **compras** | — (sin vista dedicada) | Gestión gastos |

---

## 7. VISTAS DEL FRONTEND — ESTADO ACTUAL

### Login.vue — COMPLETO 100%
- Selector de rol por dispositivo (`localStorage.device_role`)
- Grid de usuarios staff filtrado por rol; administradores excluidos
- Login con PIN mediante keypad numérico
- Redirect por rol al autenticar
- Links secundarios a `/admin-login` y `/checkin`

### MeseroView.vue (2,498 lín) — FUNCIONAL 95%
- Catálogo de platillos con búsqueda y filtro por categoría
- Carrito con cantidades y modificaciones
- Modal especial para variantes de Pozole (tamaño, proteína, color)
- Creación de orden (mesa, cliente, tipo: aquí/llevar/UberEats)
- Modal "Ver Pedido Actual" con estado por ítem
- Marcar bebidas como entregadas
- Modo agregar artículos a orden existente
- Modo edición de orden existente
- Vista de mesas ocupadas (reactivo desde store)
- **Pendiente:** Manejo de items eliminados en modo edición (`MeseroView.vue:~700`)

### CajaView.vue (4,074 lín) — FUNCIONAL 90%
- **Tab Pendientes:** Órdenes en `cuenta_solicitada`, selección método pago, propinas, cambio para efectivo
- **Tab Overview:** Estadísticas del día (ventas totales, por método, top platillos)
- **Tab Propinas:** Analytics de propinas por método + historial detallado
- Integración con servicio de impresión (puerto 3001, fallback browser)
- Gestión de turno (TurnoModal: apertura con denominaciones, cierre)
- Edición de propina en tickets ya pagados (solo admin)
- División de cuenta (admin only): por artículos y por montos
- **Issue:** Analytics no se actualiza en tiempo real (REST polling manual)
- **Issue:** Componente gigante (173KB) — candidato a decomposición

### KDSView.vue (324 lín) — COMPLETO 100%
- Grid dinámico (1-6 columnas según cantidad de órdenes)
- Filtra items de bebidas (solo muestra food)
- Temporizador por orden con urgencia por color:
  - Gris: < 5 min | Amarillo: 5-10 | Naranja: 10-15 | Rojo pulsante: > 15 min
- Actualización cada 1 segundo
- Optimizado para lectura a 8m de distancia (pantalla de cocina)

### KDSManager.vue (564 lín) — COMPLETO 100%
- Tab Activos: Ver y expandir órdenes, marcar items Preparando → Listo
- Tab Completados: Órdenes finalizadas en últimos 20 min
- Tab Disponibilidad: Toggle disponible/no_disponible por platillo con búsqueda

### AdminView.vue (250 lín) — FUNCIONAL 85%
- Navegación por tabs con URL param (`?tab=`)
- DashboardSection: KPIs y métricas con filtro por fecha
- GastosSection: CRUD gastos + proveedores + categorías + artículos
- PlatillosSection: CRUD menú
- UsuariosSection: CRUD usuarios; edición parcial con PIN opcional
- ConfiguracionSection: Ajustes del sistema

---

## 8. COMUNICACIÓN EN TIEMPO REAL (WebSocket)

**Servicio frontend:** `src/services/websocket.ts` (434 lín)

- Reconexión automática con backoff exponencial (3s inicial → max 30s)
- Integración con browser events: `visibilitychange` + `online`
- Heartbeat cada 30s (ping → pong)
- Suscripción por tipo: `on(eventType, cb)` | `on('*', cb)`
- Estado reactivo: `isConnected`, `connectionStatus`, `stats`

**Eventos:**
| Evento | Payload | Destino |
|--------|---------|---------|
| `pedido_created` | `{pedido}` | KDS, Caja, Mesero |
| `pedido_estado_changed` | `{pedido_id, nuevo_estado, pedido}` | KDS, Caja, Mesero |
| `articulo_estado_changed` | `{pedido_id, articulo_id, nuevo_estado, pedido}` | KDS, Caja, Mesero |
| `connection_established` | — | Cliente |

**Backend manager** (`websocket_manager.py`):
- Broadcast por tipo de cliente + sucursal
- Zombie cleanup: desconecta sin ping en 120s

---

## 9. PWA (Progressive Web App)

| Configuración | Valor |
|--------------|-------|
| Nombre | La Hidrocálida POS |
| Start URL | `/login` |
| Display | standalone |
| Theme color | #e11d48 (rose) |
| Background | #0f172a (slate-950) |
| Icons | 72px → 512px + maskable |
| Backend cache | NetworkOnly (sin cache) |
| WebSocket | Excluido de fallback |
| Auto-update | Sí |
| Install prompt | En Login.vue |
| Offline orders | No soportado |

---

## 10. SERVICIO DE IMPRESIÓN

- **Ubicación:** `/print_service/`
- **Plataforma:** Windows (específico)
- **Impresora:** Easytime SP-POS891ED (80mm USB)
- **Puerto:** localhost:3001
- **Trigger:** Backend POST automático al marcar `pagado`
- **Fallback:** Falla silenciosa (no bloquea el pago)
- **Manual:** Disponible desde frontend

---

## 11. AUTENTICACIÓN Y SEGURIDAD

- **JWT:** HS256, expiración 24h
- **Passwords:** Argon2 (default), retrocompatible con bcrypt
- **RBAC:** Validado endpoint por endpoint
- **CORS:** localhost:5173, :5174, lahidrocalida.vercel.app, 192.168.2.69
- **Multi-tenant:** `sucursal_id` aísla datos
- **Soft delete:** Usuarios se desactivan, no se borran

---

## 12. INFRAESTRUCTURA Y DEPLOY

| Servicio | Plataforma | Estado |
|---------|-----------|--------|
| Frontend | Vercel (CI/CD vía GitHub push) | Activo |
| Backend | Docker → Railway | Dockerfile listo |
| Base de datos | Neon Cloud (PostgreSQL) | Activo |
| Migraciones | Alembic | Configurado |
| Impresora | Servicio local Windows | En restaurante |
| CI/CD backend | GitHub Actions | No configurado |
| docker-compose | — | No existe |

**Branches:**
- `main` — producción
- `flujo-mesero` — desarrollo activo (rama actual)
- `feat/caja-ui-test` — experimentos UI caja

---

## 13. ESTADO POR MÓDULO

| Módulo | Estado | % |
|--------|--------|---|
| Autenticación | Completo | 100% |
| Mesero (toma de orden) | Funcional | 95% |
| Cocina KDS (pantalla) | Completo | 100% |
| Cocina Manager (tablet) | Completo | 100% |
| Caja (cobro y pagos) | Funcional | 90% |
| División de cuenta | Backend listo, UI parcial | 70% |
| Admin Dashboard | Funcional | 85% |
| Gestión de platillos | Completo | 100% |
| Gestión de usuarios | Completo | 100% |
| Gastos y proveedores | Parcial | 65% |
| Turnos de caja | Funcional | 85% |
| Reportes y analytics | Funcional | 85% |
| Propinas | Completo | 100% |
| WebSocket tiempo real | Completo | 100% |
| PWA / Offline | Configurado | 70% |
| Impresión térmica | Funcional | 90% |
| Variantes Pozole | Completo | 100% |
| Multi-sucursal | Modelo listo, UI no | 40% |

---

## 14. FUERA DE ALCANCE ACTUAL

- Sistema de descuentos / promociones
- Mapa visual de mesas (solo número de mesa en texto)
- Perfil o historial de clientes
- Cambio de sucursal desde UI
- Alertas de stock bajo
- Precios dinámicos / happy hour
- Sistema genérico de variantes de platillo (solo Pozole implementado)
- "Marcar todo como listo" en KDS
- Tests automatizados (ni frontend ni backend)
- CI/CD para backend (GitHub Actions)
- docker-compose para desarrollo local

---

## 15. DEUDA TÉCNICA

| Issue | Severidad | Ubicación |
|-------|-----------|-----------|
| CajaView.vue — 4,074 líneas | Media | `views/CajaView.vue` |
| MeseroView.vue — 2,498 líneas | Media | `views/MeseroView.vue` |
| Analytics no en tiempo real | Baja | `views/CajaView.vue` |
| 0% test coverage | Alta | Todo el proyecto |
| Sin CI/CD backend | Media | Infraestructura |
| Sin docker-compose | Baja | Infraestructura |
| `print()` como logging en backend | Baja | Routers |
| `create_all()` sin Alembic puro | Media | `backend/app/main.py:21` |
| TODO items eliminados en edición | Baja | `MeseroView.vue:~700` |

---

## 16. FLUJO COMPLETO DE UNA ORDEN

```
1. Mesero → MeseroView
2. Selecciona platillos del catálogo (filtrable)
   └── Si es Pozole: modal variantes (tamaño / proteína / color)
3. Llena datos de orden: mesa, cliente, tipo (aquí/llevar/UberEats)
4. POST /pedidos/ → estado "pendiente"
   └── Backend valida turno activo → inyecta turno_id (sin turno: 400)
   └── WebSocket → KDS y Caja notificados
5. Cocina ve orden en KDSView (pantalla grande)
6. KDS Manager (tablet): Preparando → Listo por ítem
   └── WebSocket → Mesero y Caja notificados
7. Mesero marca orden "entregado"
   └── Bebidas: marcadas directamente desde MeseroView
8. Mesero solicita cuenta → "cuenta_solicitada"
   └── Backend auto-imprime ticket (print_service:3001)
   └── WebSocket → Caja notificada
9. Cajero → Tab Pendientes en CajaView
   a. Selecciona método de pago (efectivo / tarjeta / transferencia)
   b. Ingresa propina (por método)
   c. Efectivo: calcula cambio automático
   d. Admin: puede dividir cuenta (por artículos o por montos)
10. Orden → "pagado"
    └── WebSocket notifica a todos
    └── Aparece en analytics del día
```

---

## 17. NUMERACIÓN DE MESAS

| Piso | Rango |
|------|-------|
| Piso 1 | 11 – 15 |
| Piso 2 | 21 – 25 |
| Piso 3 | 31 – 35 |

---

## 18. VARIABLES DE ENTORNO REQUERIDAS

**Backend (`backend/.env`):**
```env
DATABASE_URL=postgresql://...@neon.tech/neondb?sslmode=require&channel_binding=require
SECRET_KEY=<random-secret>
```

**Frontend (`frontend/pos-system/.env`):**
```env
VITE_API_URL=http://localhost:8000
```
