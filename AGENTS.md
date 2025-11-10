# AGENTS.md - Contexto del Proyecto para AI Agents

## 📋 Resumen Ejecutivo

**La Hidrocálida - Sistema de Gestión para Pozolería**

Sistema completo de gestión de pedidos con **flujo post-pago** desarrollado específicamente para pozolería. Incluye gestión de meseros, cocina digital (KDS) y procesamiento de pagos. El proyecto está **COMPLETADO** y listo para producción.

**Estado Actual: PRODUCCIÓN READY - 100% completado**

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
│   │   ├── views/             # Vistas principales del sistema
│   │   ├── router/            # Configuración rutas
│   │   └── types.ts           # Tipos TypeScript
│   └── package.json           # Dependencias Node.js
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
- Gestión de pedidos pendientes de pago
- Vista overview con estadísticas por estado
- Modal de procesamiento con 3 métodos de pago
- Auto-refresh cada 5 segundos
- Total de pedidos pendientes en tiempo real

**4. KDS View (/kds-view)**
- **Rol:** cocina, administrador
- Vista de solo lectura para pantallas de cocina
- Muestra números de mesa y nombres de cliente
- Estados visuales expandidos con colores distintivos
- Auto-refresh cada 3 segundos
- Indicadores por tipo de orden (emojis)

**5. KDS Manager (/kds-manager)**
- **Rol:** cocina, administrador
- Gestión activa de pedidos de cocina
- Cambio de estados con permisos por rol
- Control individual de artículos
- Información de mesa/cliente contextual
- Filtrado por estados

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

### ✅ Completado (100%) - SISTEMA EN PRODUCCIÓN

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

**Frontend Completo:**
- ✅ Sistema de meseros para toma de pedidos
- ✅ Vista de caja para procesar pagos
- ✅ KDS completo (lectura y gestión)
- ✅ Autenticación y autorización por roles
- ✅ Estado global con persistencia
- ✅ Diseño responsivo y UI/UX optimizada
- ✅ Navegación intuitiva entre vistas
- ✅ Auto-refresh en vistas críticas
- ✅ Notificaciones y feedback al usuario

**Flujo Operativo 100% Funcional:**
- ✅ Mesero toma pedidos con mesa
- ✅ Cocina gestiona preparación
- ✅ Mesero entrega y solicita cuenta
- ✅ Caja procesa pago final

### 🚀 Funcionalidades Opcionales para Futuro

**Reportes y Analytics:**
- 📊 Dashboard de ventas por período
- 📈 Análisis de productos más vendidos
- 💰 Reportes de ingresos por mesero/cajero
- 📅 Estadísticas por mesa y horarios

**Optimizaciones Técnicas:**
- ⚡ Paginación en listados largos
- 🗄️ Cache de consultas frecuentes
- 🔍 Optimización de queries DB
- 🧪 Tests automatizados
- 🚀 CI/CD pipeline
- 📊 Monitoreo y alertas
- 🔧 Configuración avanzada

**Mejoras UX Avanzadas:**
- ⌨️ Shortcuts de teclado
- 🔊 Notificaciones sonoras
- 🌙 Modo oscuro
- ♿ Accesibilidad (WCAG)
- 📱 PWA (offline support)
- 🖨️ Impresión de tickets
- 💳 Integración TPV externa

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
     - **Cajero**: `cuenta_solicitada`, `pagado`
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
4. **alembic/versions/**: Migraciones aplicadas de BD

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

### Archivos críticos:
- `app/models.py` - Modelos con campo mesa y estados
- `app/routers/pedidos.py` - Lógica de flujo post-pago
- `src/views/MeseroView.vue` - Interface de meseros
- `src/views/CajaView.vue` - Interface de caja
- `src/router/index.ts` - Rutas y permisos

---

**Última actualización: Enero 2025**
**Estado del proyecto: SISTEMA COMPLETO EN PRODUCCIÓN**
**Flujo: Post-pago para pozolería**
**Mantenido por: AI Agents & Development Team**