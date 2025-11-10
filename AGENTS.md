# AGENTS.md - Contexto del Proyecto para AI Agents

## 📋 Resumen Ejecutivo

**La Hidrocálida - Sistema POS para Pozolería**

Este es un sistema de punto de venta (POS) completo desarrollado para una pozolería, que incluye gestión de pedidos, cocina digital (KDS), pantalla de cliente y administración. El proyecto está en **desarrollo activo** con funcionalidades core implementadas y listo para extensiones.

**Estado Actual: MVPP (Producto Mínimo Viable Plus) - 80% completado**

---

## 🏗️ Arquitectura del Sistema

### Stack Tecnológico

**Backend (Python/FastAPI):**
- **FastAPI 0.117.1** - Framework API REST
- **SQLAlchemy 2.0.43** - ORM para base de datos
- **PostgreSQL** (Neon Cloud) - Base de datos principal
- **Alembic 1.13.2** - Migraciones de base de datos
- **JWT (python-jose)** - Autenticación y autorización
- **Passlib** - Hash de contraseñas (Argon2/bcrypt)
- **Pydantic 2.11.9** - Validación y serialización

**Frontend (Vue.js/TypeScript):**
- **Vue 3.5.21** - Framework frontend reactivo
- **TypeScript 5.8.3** - Tipado estático
- **Vue Router 4.6.3** - Enrutamiento SPA
- **Pinia 3.0.3** - Estado global
- **Tailwind CSS 4.1.13** - Framework CSS utilitario
- **Axios 1.12.2** - Cliente HTTP
- **Vite 7.1.7** - Bundler y dev server

### Estructura de Directorios

```
proyecto/
├── backend/                    # API FastAPI
│   ├── alembic/               # Migraciones DB
│   │   └── versions/          # Archivos de migración
│   ├── app/
│   │   ├── core/              # Configuración
│   │   ├── db/                # Sesión de base de datos
│   │   ├── routers/           # Endpoints API
│   │   ├── auth.py            # Autenticación JWT
│   │   ├── main.py            # Aplicación principal
│   │   ├── models.py          # Modelos SQLAlchemy
│   │   └── schemas.py         # Schemas Pydantic
│   └── requirements.txt       # Dependencias Python
├── frontend/pos-system/       # Aplicación Vue.js
│   ├── src/
│   │   ├── api/               # Cliente HTTP
│   │   ├── components/        # Componentes reutilizables
│   │   ├── stores/            # Estado Pinia
│   │   ├── views/             # Páginas principales
│   │   ├── router/            # Configuración rutas
│   │   └── types.ts           # Tipos TypeScript
│   └── package.json           # Dependencias Node.js
├── DatabaseSquema.json        # Esquema completo de DB
├── README.md                  # Plan de desarrollo
├── Scoped.md                  # Guía de implementación
└── AGENTS.md                  # Este documento
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
- `id`, `numero_display`, `nombre_cliente`, `total`, `estado`
- `metodo_pago`, `tipo_orden`, `fecha_creacion`
- `sucursal_id`, `usuario_id`
- Estados: `pendiente`, `preparando`, `listo`, `completado`, `cancelado`
- Tipos: `aqui`, `llevar`, `uber_eats`
- Numeración secuencial por día y sucursal (001, 002, ...)

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
- `POST /pedidos` - Crear pedido con artículos
- `GET /pedidos` - Listar pedidos (filtros por estado)
- `PUT /pedidos/{id}` - Actualizar estado pedido
- `PUT /pedidos/{id}/articulos/{articulo_id}` - Estado individual items
- Numeración automática secuencial por día
- Validaciones de stock y precios

**Gastos (/gastos)**
- CRUD completo para registro de gastos
- Categorización y filtrado por sucursal

**Utilidades**
- `GET /health/database` - Health check de PostgreSQL
- Middleware CORS configurado
- Logs SQL para debugging

### ✅ Frontend Multi-Vista

**1. Login (/login)**
- Autenticación por ID numérico + contraseña
- Redirección basada en rol
- Manejo de errores

**2. POS (/pos)**
- **Rol:** cajero, administrador
- Grid de categorías de platillos con colores
- Carrito de compras con modificaciones
- Finalización de pedidos (efectivo/tarjeta/transferencia)
- Tipos de orden (aquí/llevar/UberEats)
- Modal para variantes de pozole

**3. KDS View (/kds-view)**
- **Rol:** cocina, administrador
- Vista de solo lectura para pantallas de cocina
- Grid compacto con estados visuales
- Auto-refresh cada 3 segundos
- Indicadores por tipo de orden (emojis)

**4. KDS Manager (/kds-manager)**
- **Rol:** cocina, administrador
- Gestión activa de pedidos
- Cambio de estados (pendiente→preparando→listo)
- Control individual de artículos
- Filtrado por estados

**5. Cliente Display (/cliente-display)**
- **Acceso:** público
- Pantalla para clientes
- Muestra pedidos listos (estado: listo)
- Grid responsive hasta 4 pedidos simultáneos
- Auto-refresh cada 3 segundos

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

### ✅ Completado (80%)

**Backend:**
- ✅ Modelos de datos completos
- ✅ Autenticación JWT implementada
- ✅ CRUD completo para todas las entidades
- ✅ Lógica de negocio para pedidos
- ✅ Numeración automática de pedidos
- ✅ Migraciones de base de datos
- ✅ Validaciones y manejo de errores
- ✅ Health checks

**Frontend:**
- ✅ Todas las vistas principales
- ✅ Autenticación y autorización
- ✅ POS funcional completo
- ✅ KDS (lectura y gestión)
- ✅ Pantalla de cliente
- ✅ Estado global y persistencia
- ✅ Diseño responsivo

### 🚧 Pendiente/En Progreso (20%)

**Funcionalidades Faltantes:**
- 🔲 Reportes y análisis de ventas
- 🔲 Gestión de inventario/stock
- 🔲 Configuración de sucursales
- 🔲 Backup y restauración
- 🔲 Notificaciones push/websockets
- 🔲 Impresión de tickets
- 🔲 Integración con métodos de pago
- 🔲 Dashboard administrativo completo

**Optimizaciones Técnicas:**
- 🔲 Paginación en listados largos
- 🔲 Cache de consultas frecuentes
- 🔲 Optimización de queries DB
- 🔲 Tests automatizados
- 🔲 CI/CD pipeline
- 🔲 Monitoreo y logging
- 🔲 Configuración de producción

**UX Mejoras:**
- 🔲 Shortcuts de teclado en POS
- 🔲 Sonidos de notificación
- 🔲 Modo oscuro
- 🔲 Accesibilidad (WCAG)
- 🔲 PWA (offline support)

---

## 🔑 Contexto Clave para AI Agents

### Reglas de Negocio Críticas

1. **Numeración de Pedidos:**
   - Secuencial por día Y sucursal (001, 002, 003...)
   - Se reinicia cada día automáticamente
   - Constraint único en BD para evitar duplicados

2. **Estados de Pedido:**
   - Flujo: `pendiente` → `preparando` → `listo` → `completado`
   - Estado `cancelado` disponible en cualquier momento
   - Items individuales pueden marcarse `listo` independientemente

3. **Autenticación:**
   - Login por ID numérico (no username)
   - 4 roles con permisos específicos
   - Token JWT con expiración

4. **Tipos de Orden:**
   - `aqui`: Consumo en local
   - `llevar`: Para llevar
   - `uber_eats`: Delivery externo

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
- Alembic para migraciones
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
   - Generar migración: `alembic revision --autogenerate`
   - Aplicar: `alembic upgrade head`
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

## 📚 Documentos de Referencia

1. **README.md**: Plan de desarrollo completo y fases
2. **Scoped.md**: Guía de implementación detallada por pasos
3. **DatabaseSquema.json**: Esquema completo de base de datos
4. **backend/requirements.txt**: Dependencias Python exactas
5. **frontend/package.json**: Dependencias Node.js exactas

---

## 🤖 Instrucciones para AI Agents

### Al trabajar en este proyecto:

1. **SIEMPRE revisar** este documento antes de hacer cambios
2. **Mantener consistencia** con patrones existentes
3. **Validar autenticación** en nuevos endpoints
4. **Actualizar migraciones** para cambios de BD
5. **Preservar** reglas de negocio críticas
6. **Testear** funcionalidad cross-browser/device
7. **Documentar** cambios significativos

### Comandos útiles:

```bash
# Backend
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
alembic upgrade head
alembic revision --autogenerate -m "descripcion"

# Frontend  
cd frontend/pos-system
npm run dev
npm run build

# Base de datos
psql $DATABASE_URL
```

### Archivos que nunca tocar sin coordinación:
- `alembic/versions/*` - Migraciones aplicadas
- `app/models.py` - Cambios requieren migración
- `app/core/config.py` - Configuración crítica
- `src/types.ts` - Tipos compartidos

---

**Última actualización: Enero 2025**
**Estado del proyecto: MVP+ Ready for Extensions**
**Mantenido por: AI Agents & Development Team**