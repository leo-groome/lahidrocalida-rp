# AGENTS.md - Contexto del Proyecto para AI Agents

## 📋 Resumen Ejecutivo

**La Hidrocálida - Sistema de Gestión para Pozolería**

Sistema de gestión de pedidos con **flujo post-pago** desarrollado específicamente para pozolería. Incluye gestión de meseros, cocina digital (KDS) y procesamiento de pagos. El **flujo operativo está completo** con WebSockets en tiempo real, pero faltan funcionalidades adicionales para producción completa.

**Estado Actual: SISTEMA COMPLETO - Panel Admin + WebSockets + Reportes implementados**

---

## 🏗️ Arquitectura del Sistema

### Stack Tecnológico

**Backend (Python/FastAPI):**
- **FastAPI 0.117.1** - Framework API REST + WebSockets
- **SQLAlchemy 2.0.43** - ORM para base de datos
- **PostgreSQL** (Neon Cloud) - Base de datos principal
- **JWT (python-jose)** - Autenticación y autorización
- **Passlib** - Hash de contraseñas (Argon2/bcrypt)
- **Pydantic 2.11.9** - Validación y serialización
- **WebSockets** - Actualizaciones en tiempo real

**Frontend (Vue.js/TypeScript):**
- **Vue 3.5.21** - Framework frontend reactivo
- **TypeScript 5.8.3** - Tipado estático
- **Vue Router 4.6.3** - Enrutamiento SPA
- **Pinia 3.0.3** - Estado global
- **Tailwind CSS 4.1.13** - Framework CSS utilitario
- **Axios 1.12.2** - Cliente HTTP
- **Vite 7.1.7** - Bundler y dev server
- **WebSockets** - Conexión tiempo real con fallback polling
- **pnpm** - Gestor de paquetes (usar en este entorno)

### Estructura de Directorios

```
proyecto/
├── backend/                    # API FastAPI + WebSockets
│   ├── .venv/                 # Entorno virtual Python (USAR SIEMPRE)
│   │   └── versions/          # Archivos de migración
│   ├── app/
│   │   ├── core/              # Configuración
│   │   ├── db/                # Sesión de base de datos
│   │   ├── routers/           # Endpoints API REST
│   │   ├── auth.py            # Autenticación JWT
│   │   ├── main.py            # Aplicación principal
│   │   ├── models.py          # Modelos SQLAlchemy
│   │   ├── schemas.py         # Schemas Pydantic
│   │   ├── websocket_manager.py  # Gestor WebSockets
│   │   └── websocket_routes.py   # Rutas WebSockets
│   └── requirements.txt       # Dependencias Python
├── frontend/pos-system/       # Aplicación Vue.js + WebSockets
│   ├── src/
│   │   ├── api/               # Cliente HTTP (Axios)
│   │   ├── components/        # Componentes reutilizables
│   │   ├── services/          # WebSocket service
│   │   ├── stores/            # Estado Pinia (auth, pedidos)
│   │   ├── views/             # Vistas principales del sistema
│   │   ├── router/            # Configuración rutas
│   │   └── types.ts           # Tipos TypeScript
│   ├── package.json           # Dependencias Node.js
│   └── pnpm-lock.yaml         # Lock file pnpm (USAR PNPM)
├── README.md                  # Documentación del proyecto
└── AGENTS.md                  # Este documento - Contexto para AI
```

---

## 🗄️ Modelo de Datos

### Entidades Principales

**1. Sucursal**
- `id`, `nombre`, `direccion`
- Relación: Usuarios, Pedidos, Gastos

**2. Usuario**
- `id`, `nombre`, `rol`, `password`, `activo`, `sucursal_id`
- Roles: `cajero`, `cocina`, `administrador`, `compras`
- Autenticación por ID numérico + contraseña

**3. Platillo**
- `id`, `nombre`, `descripcion`, `precio`, `categoria`, `estado`
- `kds_name` - Nombre corto para pantalla de cocina
- Estados: `disponible`, `no_disponible`

**4. Pedido**
- `id`, `numero_display`, `nombre_cliente`, `total`, `estado`, `mesa`
- `metodo_pago`, `tipo_orden`, `fecha_creacion`
- `sucursal_id`, `usuario_id`
- Estados: `pendiente`, `preparando`, `listo`, `entregado`, `cuenta_solicitada`, `pagado`, `cancelado`
- Tipos: `aqui`, `llevar`, `uber_eats`
- Numeración secuencial por día y sucursal (001, 002, ...)
- Campo `mesa` para pedidos en local (11,12,13,14,15,21,22,23,24,25,31,32,33,34,35)

**5. ArticuloPedido**
- `id`, `pedido_id`, `platillo_id`, `cantidad`, `precio_cobrado`
- `modificaciones`, `estado_item`
- Estados item: `pendiente`, `listo`

**6. Gasto**
- `id`, `descripcion`, `monto`, `categoria`, `fecha_gasto`
- `sucursal_id`

### Migraciones Aplicadas
- **001_add_kds_name**: Agregó campo `kds_name` a platillos
- **002_add_estado_item**: Agregó campo `estado_item` a artículos_pedido
- **003_add_mesa_field**: Agregó campo `mesa` a pedidos
- **fix_numero_display_unique_constraint**: Constraint único por día/sucursal

---

## 🚀 Funcionalidades Implementadas

### ✅ Backend API Completa

**Autenticación (/auth)**
- `POST /auth/login` - OAuth2 estándar
- `POST /auth/login-simple` - Login con ID+password
- `GET /auth/me` - Información usuario actual
- JWT con expiración configurable (30 min default)

**Usuarios (/users)**
- CRUD completo con autorización por roles
- Hash seguro de contraseñas (Argon2/bcrypt)

**Platillos (/platillos)**
- `GET /platillos` - Listar todos (autenticado)
- `POST /platillos` - Crear (solo admin)
- Soporte para nombres cortos KDS

**Pedidos (/pedidos)**
- `POST /pedidos` - Crear pedido con artículos (soporte para campo mesa)
- `GET /pedidos` - Listar pedidos (filtros por estado)
- `GET /pedidos/pendientes-pago/lista` - Pedidos en estado cuenta_solicitada
- `PUT /pedidos/{id}` - Actualizar estado pedido (soporte para método de pago)
- `PUT /pedidos/{id}/articulos/{articulo_id}` - Estado individual items
- Numeración automática secuencial por día
- Validaciones de stock y precios
- Permisos granulares por rol para cambio de estados

**Gastos (/gastos)**
- CRUD completo para registro de gastos
- Categorización y filtrado por sucursal

**Utilidades**
- `GET /health/database` - Health check de PostgreSQL
- Middleware CORS configurado
- Logs SQL para debugging

### ✅ Frontend - Sistema de Gestión

**1. Login (/login)**
- Autenticación por ID numérico + contraseña
- Redirección automática basada en rol
- Manejo de errores y validaciones

**2. MeseroView (/mesero)**
- **Rol:** mesero, administrador
- Toma de pedidos con selección obligatoria de mesa
- Grid de categorías de platillos con colores
- Carrito de compras con modificaciones
- Modal para variantes de pozole
- **Sin método de pago** - envío directo a cocina
- Tipos de orden (aquí/llevar/UberEats)

**3. CajaView (/caja)**
- **Rol:** cajero, administrador
- **Overview completo** - Todos los pedidos del día en tiempo real
- **Solicitar cuenta** - Botón en pedidos "entregado" → "cuenta_solicitada"
- Gestión de pedidos pendientes de pago
- Vista overview con estadísticas por estado
- Modal de procesamiento con 3 métodos de pago
- **WebSocket tiempo real** - Sin polling manual necesario
- **Debug indicators** - Estado conexión WebSocket (🟢/🟡)
- Total de pedidos pendientes en tiempo real

**4. KDS View (/kds-view)**
- **Rol:** cocina, administrador
- Vista de solo lectura para pantallas de cocina
- Muestra números de mesa y nombres de cliente
- Estados visuales expandidos con colores distintivos
- **WebSocket tiempo real** - Updates instantáneos
- **Fallback polling** - 3 segundos si WebSocket falla
- Indicadores por tipo de orden (emojis)

**5. KDS Manager (/kds-manager)**
- **Rol:** cocina, administrador
- Gestión activa de pedidos de cocina
- Cambio de estados con permisos por rol
- Control individual de artículos
- Información de mesa/cliente contextual
- Filtrado por estados
- **WebSocket tiempo real** - Actualizaciones instantáneas
- **Notificaciones automáticas** - Nuevos pedidos y cambios

### ✅ Características Técnicas

**Autenticación y Autorización:**
- JWT Bearer tokens
- Guard de rutas por rol
- Interceptor automático de tokens
- Logout automático en expiración

**Estado Global (Pinia):**
- Store de autenticación centralizado
- Persistencia en localStorage
- Tipado TypeScript completo

**UX/UI:**
- Diseño responsivo con Tailwind
- Colores corporativos (#00126D, #FDB700, #FFFFFF)
- Estados visuales claros
- Loading states y error handling

**API Client:**
- Instancia Axios configurada
- Base URL configurable (env: VITE_API_URL)
- Interceptores de autenticación automáticos

---

## 🔧 Estado de Desarrollo

### ✅ Completado - SISTEMA COMPLETO + PANEL ADMIN

**Backend Completo:**
- ✅ Modelos de datos con flujo post-pago
- ✅ Autenticación JWT con roles granulares
- ✅ CRUD completo para todas las entidades
- ✅ Lógica de negocio para flujo mesero
- ✅ Estados expandidos del pedido
- ✅ Permisos por rol para cada endpoint
- ✅ Campo mesa para gestión de mesas
- ✅ Numeración automática de pedidos
- ✅ Migraciones de base de datos aplicadas
- ✅ Validaciones y manejo de errores
- ✅ Health checks y logging
- ✅ **WebSockets completos** - Tiempo real para todas las vistas
- ✅ **WebSocket Manager** - Gestión de conexiones por tipo de usuario
- ✅ **Notificaciones automáticas** - Updates por cambios de estado
- ✅ **API de Administración** - Dashboard y reportes completos
- ✅ **Reportes semanales** - Métricas detalladas por período
- ✅ **Analytics de productos** - Top 10 más vendidos
- ✅ **Gestión de gastos** - CRUD completo con categorías

**Frontend Completo:**
- ✅ Sistema de meseros para toma de pedidos
- ✅ Vista de caja para procesar pagos + **solicitar cuenta**
- ✅ KDS completo (lectura y gestión)
- ✅ **Panel de Administración** - Dashboard completo con reportes
- ✅ **Vista Dashboard** - Métricas del día en tiempo real
- ✅ **Reportes Semanales** - Analytics por período configurable
- ✅ **Gestión de Gastos** - CRUD con categorización
- ✅ **Top 10 Productos** - Analytics de ventas por producto
- ✅ **Métricas financieras** - Ingresos, gastos, utilidad bruta
- ✅ Autenticación y autorización por roles
- ✅ Estado global con persistencia
- ✅ Diseño responsivo y UI/UX optimizada
- ✅ Navegación intuitiva entre vistas
- ✅ **WebSockets tiempo real** - Actualizaciones instantáneas
- ✅ **Fallback automático** - Polling si WebSocket falla
- ✅ **Notificaciones tiempo real** - Estados de pedidos
- ✅ **Debug indicators** - Estado de conexión WebSocket
- ✅ Notificaciones y feedback al usuario

**Flujo Operativo Completo + Tiempo Real + Administración:**
- ✅ Mesero toma pedidos con mesa → **Aparece instantáneamente en KDS**
- ✅ Cocina gestiona preparación → **Updates en tiempo real**
- ✅ Mesero entrega → **Notificación automática**
- ✅ **Caja solicita cuenta** → **Botón en overview**
- ✅ Caja procesa pago final → **Estadísticas actualizadas en tiempo real**
- ✅ **Panel de administración** → **Dashboard + reportes implementados**
- ✅ **Reportes semanales** → **Analytics completos con métricas**
- ✅ **Gestión de gastos** → **CRUD completo con categorías**
- ✅ **Impresión en consola** → **Tickets se imprimen en consola del navegador**

### 🚧 Funcionalidades Pendientes para Producción Completa

**Críticas para Producción:**
- 📅 **Estadísticas operativas** - Rendimiento por mesero, tiempos promedio
- 📊 **Reportes mensuales** - Analytics extendidos por mes/año
- 🖨️ **Impresión física** - Integración con impresora térmica (opcional)

**Optimizaciones Necesarias:**
- ⚡ **Performance** - Paginación, cache, optimización de queries
- 🔍 **Búsqueda avanzada** - Filtros por fecha, cliente, productos
- 🔧 **Configuración** - Ajustes de impresora, horarios, precios
- 📱 **Responsividad móvil** - Optimización para tablets/móviles
- 🧪 **Testing** - Tests automatizados para estabilidad
- 📊 **Monitoreo** - Logs, alertas, health checks

**Mejoras UX Importantes:**
- ⌨️ **Shortcuts de teclado** - Navegación rápida para cajeros
- 🔊 **Notificaciones sonoras** - Alertas para nueva orden en cocina
- 🌙 **Modo oscuro** - Para uso en horarios nocturnos
- ♿ **Accesibilidad** - Cumplimiento WCAG para inclusividad
- 📱 **PWA** - Funcionalidad offline y app móvil
- 💳 **Integración TPV** - Conexión con terminales de pago

---

## 🔑 Contexto Clave para AI Agents

### Reglas de Negocio Críticas

1. **Numeración de Pedidos:**
   - Secuencial por día Y sucursal (001, 002, 003...)
   - Se reinicia cada día automáticamente
   - Constraint único en BD para evitar duplicados

2. **Estados de Pedido (Flujo Post-Pago):**
   - Flujo: `pendiente` → `preparando` → `listo` → `entregado` → `cuenta_solicitada` → `pagado`
   - Estado `cancelado` disponible en cualquier momento (solo admin)
   - Items individuales pueden marcarse `listo` independientemente
   - **Permisos por Rol:**
     - **Mesero**: `pendiente`, `entregado`, `cuenta_solicitada`
     - **Cajero**: `entregado`, `cuenta_solicitada`, `pagado` ← **ACTUALIZADO**
     - **Cocina**: `pendiente`, `preparando`, `listo`
     - **Administrador**: Todos los estados + `cancelado`

3. **Gestión de Mesas:**
   - Campo `mesa` obligatorio para pedidos tipo `aqui`
   - Numeración: 11,12,13,14,15 (piso 1), 21,22,23,24,25 (piso 2), 31,32,33,34,35 (piso 3)
   - Se muestra en KDS y vista de caja para identificación

4. **Autenticación:**
   - Login por ID numérico (no username)
   - 4 roles: `mesero`, `cajero`, `cocina`, `administrador`
   - Token JWT con expiración configurable

5. **Tipos de Orden:**
   - `aqui`: Consumo en local (requiere mesa)
   - `llevar`: Para llevar (requiere nombre cliente)
   - `uber_eats`: Delivery externo

6. **Métodos de Pago:**
   - Se asignan al final del flujo en vista de caja
   - Opciones: `efectivo`, `tarjeta`, `transferencia`
   - Solo se guarda cuando el pedido se marca como `pagado`

### Patrones de Código Importantes

**Backend Patterns:**
```python
# Dependency injection para DB y auth
def endpoint(db: Session = Depends(get_db), 
           current_user: Usuario = Depends(get_current_active_user)):

# Validación por rol
if current_user.rol not in ["administrador", "cajero"]:
    raise HTTPException(status_code=403, detail="No autorizado")

# Generación de número de pedido
numero_display = generate_numero_display(db, sucursal_id)
```

**Frontend Patterns:**
```typescript
// Store de autenticación
const auth = useAuthStore()
if (!auth.isAuthenticated) router.replace({name: 'login'})

// API calls con manejo de errores
try {
  const {data} = await api.get<PedidoResponse[]>('/pedidos')
} catch (e: any) {
  error.value = e?.response?.data?.detail || 'Error genérico'
}
```

### Configuración Crítica

**Variables de Entorno Backend:**
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: JWT signing key  
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Token expiration

**Variables de Entorno Frontend:**
- `VITE_API_URL`: Backend API base URL

### Puntos de Integración

**Base de Datos:**
- PostgreSQL en Neon Cloud
- Connection pooling configurado

**API:**
- CORS habilitado para desarrollo
- FastAPI auto-docs en `/docs`
- Prefijos consistentes (`/auth`, `/pedidos`, etc.)

---

## 🎯 Casos de Uso Comunes

### Para Desarrollo de Nuevas Features

1. **Agregar nuevo endpoint:**
   - Crear schema en `schemas.py`
   - Agregar ruta en router correspondiente
   - Validar autenticación/autorización
   - Actualizar tipos TypeScript

2. **Nueva vista frontend:**
   - Crear componente en `src/views/`
   - Agregar ruta en `router/index.ts`
   - Configurar guards por rol
   - Integrar con stores Pinia

3. **Modificar modelo de datos:**
   - Actualizar modelo en `models.py`
   - Actualizar schemas y tipos

### Para Debugging

**Backend Debug:**
- Logs SQL habilitados (`echo=True`)
- Health check: `GET /health/database`
- FastAPI docs: `http://localhost:8000/docs`

**Frontend Debug:**
- Vue DevTools
- Network tab para API calls
- localStorage para token inspection

### Para Deployment

**Checklist Producción:**
- [ ] Variables de entorno configuradas
- [ ] CORS restringido a dominio específico
- [ ] Logs SQL deshabilitados
- [ ] Migraciones aplicadas
- [ ] Build de frontend optimizado

---

### 🎯 Estado Actual vs Funcionalidades Faltantes

**✅ LO QUE FUNCIONA:**
- Flujo operativo completo (mesero → cocina → caja)
- WebSockets tiempo real en todas las vistas
- Gestión de pedidos con estados granulares
- Autenticación y autorización por roles
- Solicitar cuenta desde caja
- Vista KDS para cocina
- Gestión de mesas y tipos de orden
- **Panel de administración completo**
- **Dashboard con métricas diarias**
- **Reportes semanales detallados**
- **Analytics de productos más vendidos**
- **Gestión completa de gastos**
- **Métricas financieras (ingresos, gastos, utilidad)**

**❌ LO QUE FALTA PARA PRODUCCIÓN:**
- **Reportes mensuales/anuales** extendidos
- **Optimización de código** y performance
- **Testing automatizado** y control de calidad
- **Configuración avanzada** (horarios, etc.)
- **Analytics de meseros** (rendimiento individual)
- **Impresión física** (opcional - actualmente solo en consola)

## 🎯 Casos de Uso del Sistema

### Flujo Operativo Diario

**1. Mesero (MeseroView):**
- Selecciona mesa disponible
- Toma pedido del cliente
- Envía a cocina (estado: `pendiente`)
- Recibe notificación cuando está `listo`
- Entrega comida (cambia a `entregado`)
- Cliente solicita cuenta (cambia a `cuenta_solicitada`)

**2. Cocina (KDS):**
- Ve pedidos `pendiente` con mesa y detalles
- Cambia a `preparando` al iniciar
- Marca `listo` cuando termina
- Ve información de mesa para entrega

**3. Caja (CajaView):**
- Ve pedidos en `cuenta_solicitada`
- Selecciona pedido y método de pago
- Procesa pago (cambia a `pagado`)
- Ve estadísticas generales del día

### Casos Especiales

**Pedidos para Llevar:**
- Mesero ingresa nombre del cliente
- No requiere mesa
- Flujo igual pero se identifica por nombre

**Cancelaciones:**
- Solo administrador puede cancelar
- Disponible desde cualquier estado
- Se registra el cambio

## 📚 Documentos de Referencia

1. **README.md**: Documentación general del proyecto
2. **backend/requirements.txt**: Dependencias Python exactas
3. **frontend/package.json**: Dependencias Node.js exactas
---

## 🤖 Instrucciones para AI Agents

### Al trabajar en este proyecto:

1. **SIEMPRE revisar** este documento antes de hacer cambios
2. **Mantener consistencia** con el flujo post-pago establecido
3. **Validar permisos por rol** en nuevos endpoints
4. **Actualizar migraciones** para cambios de BD
5. **Preservar** reglas de negocio del flujo mesero
6. **Testear** en todos los roles (mesero, cajero, cocina, admin)
7. **Documentar** cambios significativos
8. **PRIORIZAR** funcionalidades pendientes para producción
9. **OPTIMIZAR** código existente cuando sea posible
10. **CONSIDERAR** escalabilidad y performance

### 🚀 Comandos para este entorno específico:

```bash
# Backend (USAR .venv/ obligatorio)
cd backend
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (USAR pnpm obligatorio)
cd frontend/pos-system
pnpm install          # NO usar npm
pnpm run dev          # NO usar npm run dev
pnpm run build        # NO usar npm run build

# Base de datos
psql $DATABASE_URL

# WebSockets test
# Backend debe estar corriendo en :8000
# Frontend debe estar corriendo en :5173
# WebSocket endpoint: ws://localhost:8000/ws/{tipo_usuario}
```

### ⚠️ **IMPORTANTE - Configuración de este entorno:**

- **Backend**: SIEMPRE usar `.venv/` - No instalar globalmente
- **Frontend**: SIEMPRE usar `pnpm` - No usar npm/yarn
- **WebSockets**: Puerto 8000 backend, 5173 frontend
- **Base de datos**: PostgreSQL en Neon Cloud (ver env vars)

### Archivos críticos:
- `app/models.py` - Modelos con campo mesa y estados
- `app/routers/pedidos.py` - Lógica de flujo post-pago
- `app/websocket_manager.py` - **Gestor WebSockets tiempo real**
- `app/websocket_routes.py` - **Rutas WebSocket por tipo usuario**
- `src/services/websocket.ts` - **Cliente WebSocket frontend**
- `src/stores/pedidos.ts` - **Estado global con WebSockets**
- `src/views/MeseroView.vue` - Interface de meseros
- `src/views/CajaView.vue` - **Interface de caja + solicitar cuenta**
- `src/views/KDSView.vue` - **Vista cocina tiempo real**
- `src/views/KDSManager.vue` - **Gestión cocina tiempo real**
- `src/router/index.ts` - Rutas y permisos

---

## 📡 **WebSockets - Implementación Completa**

### **Arquitectura Tiempo Real:**
- **Backend**: FastAPI WebSockets con gestión por tipo de usuario
- **Frontend**: Cliente WebSocket con fallback automático a polling
- **Tipos de conexión**: `kds`, `mesero`, `caja`, `admin`
- **Notificaciones**: Automáticas por cambios de estado/artículos
- **Fallback**: Polling inteligente si WebSocket falla

### **Cobertura por Vista:**
- **KDSView**: ✅ Updates de pedidos activos
- **KDSManager**: ✅ Notificaciones de nuevos pedidos y cambios
- **MeseroView**: ✅ Notificaciones de pedidos listos y cambios relevantes
- **CajaView**: ✅ **TODOS** los cambios para overview completo

### **Estados Soportados:**
- `pedido_created` - Nuevo pedido creado
- `pedido_estado_changed` - Cambio de estado general
- `articulo_estado_changed` - Progreso de artículos individuales

---

**Última actualización: Enero 2025**
**Estado del proyecto: SISTEMA COMPLETO + Panel Admin + WebSockets tiempo real**
**Flujo: Post-pago + Dashboard + Reportes + Administración + Impresión en consola**
**Pendiente: Reportes mensuales, optimizaciones, impresión física opcional**
**Funcionalidad nueva: Impresión de tickets en consola del navegador**
**Mantenido por: AI Agents & Development Team**