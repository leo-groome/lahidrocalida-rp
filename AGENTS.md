# AGENTS.md - Contexto del Proyecto para AI Agents

## 📋 Resumen Ejecutivo

**La Hidrocálida - Sistema de Gestión para Pozolería**

Sistema de gestión de pedidos con **flujo post-pago** desarrollado específicamente para pozolería. Incluye gestión de meseros, cocina digital (KDS) y procesamiento de pagos. El **flujo operativo está completo** con WebSockets en tiempo real, pero faltan funcionalidades adicionales para producción completa.

**Estado Actual: SISTEMA COMPLETO - Panel Admin + WebSockets + Reportes + KDS Optimizado para TV/Tablet**

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

**🖨️ Sistema de Impresión:**
- **Print Server Python** - Servidor independiente para impresoras térmicas
- **ESC/POS Commands** - Formato profesional de tickets
- **Multi-plataforma** - Windows y Linux soportados
- **Integración automática** - Impresión desde CajaView

### Estructura de Directorios

```
proyecto/
├── backend/                    # API FastAPI + WebSockets
│   ├── .venv/                 # Entorno virtual Python (USAR SIEMPRE)
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
│   ├── add_missing_categories.py # Script de utilidad para categorías
│   └── requirements.txt       # Dependencias Python
├── frontend/pos-system/       # Aplicación Vue.js + WebSockets
│   ├── src/
│   │   ├── api/               # Cliente HTTP (Axios)
│   │   ├── components/        # Componentes reutilizables
│   │   ├── services/          # WebSocket + Print services
│   │   ├── stores/            # Estado Pinia (auth, pedidos)
│   │   ├── views/             # Vistas principales del sistema
│   │   ├── router/            # Configuración rutas
│   │   └── types.ts           # Tipos TypeScript
│   ├── package.json           # Dependencias Node.js
│   ├── pnpm-lock.yaml         # Lock file pnpm (USAR PNPM)
│   └── PERFORMANCE_OPTIMIZATIONS.md # Optimizaciones implementadas
├── print_service/             # Sistema de Impresión Física
│   ├── print_server.py        # Servidor de impresión independiente
│   ├── requirements.txt       # Dependencias del print server
│   ├── install.sh/.bat        # Scripts de instalación multi-plataforma
│   ├── inicio_rapido.bat      # Script de inicio rápido Windows
│   └── README.md              # Documentación de impresión
├── README.md                  # Documentación del proyecto
├── MEJORAS_PROYECTO.md        # Plan detallado de mejoras futuras
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

### Cambios de Base de Datos Aplicados
- **Campo kds_name**: Agregado a platillos para nombres cortos en KDS
- **Campo estado_item**: Agregado a artículos_pedido para control granular
- **Campo mesa**: Agregado a pedidos para gestión de mesas
- **Constraint único**: numero_display único por día/sucursal
- **Nota**: Las migraciones se aplican directamente en models.py (no se usa Alembic)

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

**2. MeseroView (/mesero) - ULTRA-OPTIMIZADO + AGREGAR A PEDIDO EXISTENTE**
- **Rol:** mesero, administrador
- **Modal inicial obligatorio** - Configuración de tipo de orden al inicio
- **Flujo optimizado**: Tipo orden → Mesa/Nombre → Menú → Especificaciones → Carrito
- **Mesas ocupadas TIEMPO REAL** - WebSocket sincronización automática entre meseros
- **FUNCIONALIDAD "AGREGAR A PEDIDO EXISTENTE"** - Sistema completo implementado:
  * **Modal mesa ocupada** - Opciones: [➕ Agregar artículos] [👁️ Ver pedido actual] [← Cancelar]
  * **Agregar artículos**: Cualquier estado antes de `cuenta_solicitada`
  * **Modificar pedidos**: Solo estado `pendiente` (cambiar cantidades, eliminar artículos)
  * **Ver pedido actual**: Modal con artículos actuales, editable si pendiente
  * **Lógica diferenciada por estado**:
    - Pendiente: Actualiza pedido completo, re-envía a KDS
    - Preparando/listo/entregado: Solo artículos nuevos aparecen como "#001-A" en KDS
  * **Endpoints backend**: `PUT /pedidos/{id}/agregar-articulos`, `PUT /pedidos/{id}/actualizar-articulos`
  * **WebSocket tiempo real**: Notificaciones automáticas según contexto
- **Carrito full-screen móvil** - Scroll funcional con botón "Enviar a Cocina" siempre visible
- **Especificaciones inmediatas** - Modal al seleccionar cualquier platillo
- **Especificaciones rápidas** - Botones por categoría para máxima velocidad:
  * Pozole: Sin lechuga, Poco grano, Muy caliente
  * Enchiladas: Sin crema, Sin lechuga, Sin queso, Sin cueritos, Sin papa y zanahoria, Con jalapeño
  * Flautas: Sin crema, Sin lechuga, Sin queso
  * Sopes: Sin crema, Sin lechuga, Sin queso, Sin frijoles
  * Tacos: Sin crema, Sin lechuga, Sin queso
  * Tostadas: Sin crema, Sin lechuga, Sin queso, Sin frijoles
- **Selector cantidad discreto** - En modal de especificaciones sin distraer
- **Botón eliminar separado** - En carrito para evitar toques accidentales
- **Categorías auto-cerradas** - Se cierran después de agregar artículo
- **Orden estandarizado** - Especificaciones consistentes entre categorías
- **Pozoles completos** - 36 variaciones con 4 proteínas (Puerco/Pollo/Surtida/Mixta)
- **Cancelar pedido** - Opción para reiniciar en cualquier momento
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

**4. KDS View (/kds-view) - OPTIMIZADO TV 8 METROS**
- **Rol:** cocina, administrador
- **Vista TV optimizada** para pantallas de cocina a 8 metros de distancia
- **Mesa/Nombre como punto focal** - Texto gigante (text-4xl) para máxima visibilidad
- **Máximo 4 pedidos** en pantalla para evitar saturación
- **Indicador de urgencia** - Badge rojo con pedidos no visibles (+X más pendientes)
- **Artículos con texto GIGANTE** - text-4xl/3xl/2xl escalado por cantidad
- **Modificaciones destacadas** - Fondo amarillo, texto XL para legibilidad
- **Sin tachado** en artículos listos - Completamente legibles
- **Temporizadores prominentes** - Tiempo transcurrido en tiempo real
- **Emojis grandes** - text-5xl/4xl/3xl para tipo de orden
- **WebSocket tiempo real** - Updates instantáneos sin polling
- **Fallback polling** - 3 segundos si WebSocket falla

**5. KDS Manager (/kds-manager) - OPTIMIZADO TABLET/MÓVIL**
- **Rol:** cocina, administrador
- **Gestión táctil** optimizada para tablet y dispositivos móviles
- **Mesa/Nombre prominentes** - text-2xl/xl desktop, text-xl/lg móvil
- **Artículos ULTRA-legibles** - text-lg/xl/2xl para uso en tablet
- **Modificaciones grandes** - text-base/lg/xl con fondo destacado
- **Sin tachado** en artículos listos - Texto completamente visible
- **Botones táctiles** grandes para cambio de estados
- **Íconos grandes** - text-3xl/4xl para estados de artículos
- **Filtrado rápido** por estados con contadores en tiempo real
- **Layout responsivo** - Optimizado para móvil y tablet
- **WebSocket tiempo real** - Actualizaciones instantáneas
- **Control granular** de artículos individuales

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

## ✅ **Completado - SISTEMA COMPLETO + PANEL ADMIN + KDS OPTIMIZADO + UX MEJORADA + IMPRESIÓN FÍSICA**

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
- ✅ **Auto-marcar artículos** - Al marcar pedido como listo, todos los artículos se marcan automáticamente
- ✅ **Auto-marcar artículos entregados** - Al marcar pedido como entregado, todos los artículos se marcan como entregado
- ✅ **Pedidos entregados reactivados** - Agregar artículos a pedido entregado lo vuelve a estado pendiente
- ✅ **Filtrado KDS por artículos** - KDS muestra solo artículos no entregados para comandas reactivadas
- ✅ **Temporizador reiniciado** - Pedidos reactivados van al final de la cola con nueva fecha de creación
- ✅ **WebSocket MeseroView mejorado** - Modal "Ver Pedido" se actualiza correctamente en tiempo real
- ✅ **Configuración avanzada** - Timezone, versioning, debug mode
- ✅ **Scripts de utilidades** - Gestión de categorías automática

**Frontend Completo:**
- ✅ Sistema de meseros para toma de pedidos
- ✅ Vista de caja para procesar pagos + **solicitar cuenta**
- ✅ **KDS View ULTRA-OPTIMIZADO** - Vista TV para 8 metros con texto gigante y máximo 4 pedidos
- ✅ **KDS Manager ULTRA-OPTIMIZADO** - Tablet/móvil con artículos legibles y sin tachado
- ✅ **Panel de Administración** - Dashboard completo con reportes
- ✅ **Vista Dashboard** - Métricas del día en tiempo real
- ✅ **Reportes Semanales** - Analytics por período configurable
- ✅ **Gestión de Gastos** - CRUD con categorización
- ✅ **Top 10 Productos** - Analytics de ventas por producto
- ✅ **Métricas financieras** - Ingresos, gastos, utilidad bruta
- ✅ **Mapa de mesas inteligente** - Vista visual del estado de mesas en tiempo real
- ✅ **Búsqueda y filtrado** - Por mesa, cliente o número de pedido con auto-limpieza
- ✅ **Interacción contextual de mesas** - Clic directo para ver detalles o cobrar según estado
- ✅ **UX optimizada** - Notificaciones consistentes y flujo simplificado
- ✅ Autenticación y autorización por roles
- ✅ Estado global con persistencia
- ✅ Diseño responsivo y UI/UX optimizada
- ✅ Navegación intuitiva entre vistas
- ✅ **WebSockets tiempo real** - Actualizaciones instantáneas
- ✅ **Fallback automático** - Polling si WebSocket falla
- ✅ **Notificaciones tiempo real** - Estados de pedidos
- ✅ **Debug indicators** - Estado de conexión WebSocket
- ✅ **Temporizadores KDS** - Tiempo transcurrido por pedido en tiempo real
- ✅ **Updates optimísticos** - Performance mejorado sin loading innecesario
- ✅ **Sistema de impresión integrado** - Impresión automática de tickets desde CajaView
- ✅ **Performance optimizado** - Bundle size reducido 99% (logo), chunks separados
- ✅ **Build analysis tools** - Herramientas de análisis de bundle implementadas
- ✅ Notificaciones y feedback al usuario

**🖨️ Sistema de Impresión Física Completo:**
- ✅ **Print Server independiente** - Servidor Python para impresoras térmicas
- ✅ **Formato ESC/POS** - Tickets profesionales con formato estándar
- ✅ **Auto-impresión** - Tickets se imprimen automáticamente al procesar pago
- ✅ **Multi-plataforma** - Scripts de instalación para Windows y Linux
- ✅ **Notificaciones de impresión** - Feedback de éxito/error en CajaView
- ✅ **Configuración flexible** - Servidor configurable por puerto/IP
- ✅ **Fallback a consola** - Si no hay impresora, imprime en consola del navegador

**Flujo Operativo Completo + Tiempo Real + Administración + UX Ultra-Optimizada:**
- ✅ **Mesero: Modal inicial** → **Tipo orden → Mesa/Nombre → Menú instantáneo**
- ✅ **Mesero: AGREGAR A PEDIDO EXISTENTE** → **Mesa ocupada → [Agregar artículos] [Ver pedido] [Cancelar]**
- ✅ **Mesero: Modificar pedidos pendientes** → **Ver pedido actual permite editar cantidades y eliminar artículos**
- ✅ **Mesero: Lógica diferenciada por estado** → **Pendiente: actualiza completo, otros: solo nuevos "#001-A"**
- ✅ **Mesero: WebSocket tiempo real** → **Notificaciones automáticas según contexto de modificación**
- ✅ **Mesero: Especificaciones ULTRA-RÁPIDAS** → **Botones por categoría + cantidad en modal**
- ✅ **Mesero: Mesas TIEMPO REAL** → **WebSocket sincronización automática entre meseros**
- ✅ **Mesero: Carrito optimizado** → **Scroll funcional + botón siempre visible + eliminar separado**
- ✅ **Mesero: Categorías auto-cerradas** → **Se cierran después de agregar para mayor velocidad**
- ✅ **Pozoles completos** → **36 variaciones con 4 proteínas (Surtida/Mixta nuevas)**
- ✅ Cocina recibe pedido → **Aparece instantáneamente en KDS**
- ✅ **Cocina ve temporizadores** → **Tiempo transcurrido por pedido en tiempo real**
- ✅ **KDS View ULTRA-optimizado** → **Vista TV legible desde 8 metros con máximo 4 pedidos**
- ✅ **KDS Manager ULTRA-optimizado** → **Tablet/móvil con texto gigante sin tachado**
- ✅ **Indicador de urgencia** → **Badge rojo mostrando pedidos no visibles (+X más)**
- ✅ **Auto-marcar artículos** → **Al marcar pedido listo, todos los artículos se marcan**
- ✅ Mesero entrega → **Todos los artículos se marcan como entregados automáticamente**
- ✅ **Agregar a pedido entregado** → **Pedido vuelve a estado pendiente, aparece en KDS solo con artículos nuevos**
- ✅ **Temporizador reiniciado** → **Pedidos reactivados van al FINAL de la cola con nueva fecha de creación**
- ✅ **Filtrado inteligente KDS** → **Solo muestra artículos no entregados, indicador visual para comandas reactivadas**
- ✅ **Caja ve mapa de mesas** → **Estado visual en tiempo real**
- ✅ **Caja hace clic en mesa** → **Ve detalles del pedido o va directo a cobrar**
- ✅ **Caja solicita cuenta** → **Botón en overview + auto-limpieza de filtros**
- ✅ Caja procesa pago final → **Estadísticas actualizadas + filtros limpios automáticamente**
- ✅ **Panel de administración** → **Dashboard + reportes implementados**
- ✅ **Reportes semanales** → **Analytics completos con métricas**
- ✅ **Gestión de gastos** → **CRUD completo con categorías**
- ✅ **Impresión física automática** → **Tickets se imprimen en impresora térmica + fallback consola**

### **🚧 Funcionalidades Pendientes para Producción Completa**

**Críticas para Producción:**
- 📅 **Estadísticas operativas** - Rendimiento por mesero, tiempos promedio
- 📊 **Reportes mensuales** - Analytics extendidos por mes/año
- 🔍 **Búsqueda avanzada en caja** - Herramientas para encontrar pedidos rápidamente
- 🔧 **Configuración de impresora UI** - Interface para configurar impresoras desde admin
- ⌨️ **Shortcuts de teclado** - Navegación rápida para cajeros
- 🔊 **Notificaciones sonoras** - Alertas para nueva orden en cocina
- 🌙 **Modo oscuro** - Para uso en horarios nocturnos

**🆕 NUEVO - Sistema de Bebidas y Postres Implementado:**
- ✅ **Bebidas automáticamente entregadas** - Se marcan como "entregado" al crear pedido
- ✅ **Filtrado inteligente KDS** - Bebidas nunca aparecen en pantallas de cocina
- ✅ **Auto-promoción mejorada** - Pedidos pasan a "listo" considerando bebidas entregadas
- ✅ **Orden de categorías optimizado** - Comida → Postres → Bebidas
- ✅ **Especificaciones rápidas Postres** - "Sin chocolate" agregado
- ✅ **KDS limpio** - Eliminado indicador de "agregados" que interfería

**Optimizaciones Necesarias:**
- ⚡ **Performance avanzado** - Paginación, cache, optimización de queries
- 🔧 **Configuración UI** - Interface para ajustar horarios, precios desde admin
- 📱 **Responsividad móvil** - Optimización para tablets/móviles
- 🧪 **Testing** - Tests automatizados para estabilidad
- 📊 **Monitoreo** - Logs, alertas, health checks avanzados

**Mejoras UX Importantes:**
- ⌨️ **Shortcuts de teclado** - Navegación rápida para cajeros
- 🔊 **Notificaciones sonoras** - Alertas para nueva orden en cocina
- 🌙 **Modo oscuro** - Para uso en horarios nocturnos
- ♿ **Accesibilidad** - Cumplimiento WCAG para inclusividad
- 📱 **PWA** - Funcionalidad offline y app móvil
- 💳 **Integración TPV** - Conexión con terminales de pago
- 🎯 **Configuración de impresora UI** - Panel admin para gestionar impresoras

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
- `VITE_API_URL`: Backend API base URL (usa .env.example como plantilla)
- Fallback por defecto: `http://localhost:8000`

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
cp .env.example .env  # Configurar API URL
# Editar .env con la IP/URL correcta del backend
pnpm install          # NO usar npm
pnpm run dev          # NO usar npm run dev
pnpm run build        # NO usar npm run build
pnpm run build:analyze # Análisis de bundle size
pnpm run bundle-size  # Ver tamaños de archivos

# Print Service (Sistema de impresión)
cd print_service
python print_server.py --port 3001  # Puerto configurable
# Windows: inicio_rapido.bat
# Linux: ./start_print_service.sh

# Utilidades
cd backend
python add_missing_categories.py  # Agregar categorías faltantes

# Base de datos
psql $DATABASE_URL

# WebSockets test
# Backend debe estar corriendo en :8000
# Frontend debe estar corriendo en :5173
# Print Service corriendo en :3001
# WebSocket endpoint: ws://localhost:8000/ws/{tipo_usuario}
```

### ⚠️ **IMPORTANTE - Configuración de este entorno:**

- **Backend**: SIEMPRE usar `.venv/` - No instalar globalmente
- **Frontend**: SIEMPRE usar `pnpm` - No usar npm/yarn
- **WebSockets**: Puerto 8000 backend, 5173 frontend
- **Base de datos**: PostgreSQL en Neon Cloud (ver env vars)
- **API URL**: Configurar en un solo lugar usando `.env.example` como plantilla

### 🔧 **Configuración de IP/URL centralizada:**

Para evitar cambiar la IP en múltiples lugares:

1. **Copia el template**: `cp frontend/pos-system/.env.example frontend/pos-system/.env`
2. **Edita una sola vez**: Cambia `VITE_API_URL` en `.env` según tu entorno
3. **Ejemplos comunes**:
   - Desarrollo: `VITE_API_URL=http://localhost:8000`
   - Red local: `VITE_API_URL=http://192.168.1.100:8000`
   - Testing: `VITE_API_URL=http://172.24.13.255:8000`

### Archivos críticos:
- `app/models.py` - Modelos con campo mesa y estados
- `app/routers/pedidos.py` - **Lógica de flujo post-pago + AGREGAR A PEDIDO EXISTENTE**
  * `PUT /pedidos/{id}/agregar-articulos` - Endpoint para agregar artículos a pedidos existentes
  * `PUT /pedidos/{id}/actualizar-articulos` - Endpoint para modificar pedidos pendientes
- `app/core/config.py` - **Configuración con timezone y versioning**
- `app/websocket_manager.py` - **Gestor WebSockets tiempo real + notificaciones a meseros**
- `app/websocket_routes.py` - **Rutas WebSocket por tipo usuario**
- `add_missing_categories.py` - **Script utilidades para categorías**
- `src/api/client.ts` - **Cliente HTTP con fallback localhost**
- `src/services/websocket.ts` - **Cliente WebSocket frontend**
- `src/services/printService.ts` - **Servicio de impresión integrado**
- `src/stores/pedidos.ts` - **Estado global con WebSockets**
- `src/views/MeseroView.vue` - **Interface de meseros + AGREGAR A PEDIDO EXISTENTE**
  * Modal mesa ocupada con opciones
  * Modal "Ver pedido actual" con edición de cantidades
  * Funciones: `verPedidoActual()`, `agregarArticulosMesa()`, `guardarCambiosPedido()`
- `src/views/CajaView.vue` - **Interface de caja + impresión automática**
- `src/views/KDSView.vue` - **Vista cocina tiempo real**
- `src/views/KDSManager.vue` - **Gestión cocina tiempo real**
- `src/router/index.ts` - Rutas y permisos
- `frontend/pos-system/.env.example` - **Template de configuración**
- `print_service/print_server.py` - **Servidor de impresión independiente**
- `PERFORMANCE_OPTIMIZATIONS.md` - **Optimizaciones implementadas**

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
**Estado del proyecto: SISTEMA COMPLETO + Panel Admin + KDS ULTRA-OPTIMIZADO + BEBIDAS Y POSTRES + WebSockets + IMPRESIÓN FÍSICA**
**Flujo: Post-pago + Dashboard + Reportes + KDS TV 8 metros + KDS Tablet táctil + Sistema Bebidas Inteligente + Impresión automática**
**Pendiente: Reportes mensuales, configuración UI impresora, testing automatizado**
**Últimos cambios - SISTEMA BEBIDAS Y POSTRES COMPLETO:**
- ✅ **BEBIDAS AUTOMÁTICAS**: Se marcan como "entregado" al crear pedido, nunca aparecen en KDS
- ✅ **FILTRADO INTELIGENTE KDS**: Bebidas invisibles para cocina, solo ven comida a preparar
- ✅ **AUTO-PROMOCIÓN MEJORADA**: Pedidos pasan a "listo" considerando bebidas+comida completados
- ✅ **ORDEN CATEGORÍAS OPTIMIZADO**: Comida → Postres (penúltimo) → Bebidas (último)
- ✅ **ESPECIFICACIONES POSTRES**: Agregado "Sin chocolate" para opciones rápidas
- ✅ **KDS LIMPIO**: Eliminado indicador "agregados" que interfería con el flujo
- ✅ **LÓGICA BACKEND INTELIGENTE**: Bebidas se crean como entregadas en creación y modificación
- ✅ **FLUJO SIMPLIFICADO COCINA**: Interface limpia sin distracciones innecesarias
- ✅ **ESTADOS COHERENTES**: Considera "listo" + "entregado" como artículos completados
- ✅ **MESERO OPTIMIZADO COMPLETO**: Sistema completo con agregar a pedido existente
- ✅ **KDS View TV optimizado**: Legibilidad desde 8 metros, máximo 4 pedidos, texto gigante
- ✅ **KDS Manager tablet**: Artículos táctiles grandes sin elementos que interfieren
- ✅ **WebSocket tiempo real perfecto**: Funciona sin problemas con el nuevo sistema
**Funcionalidades nuevas:** 
- **Mapa de mesas lateral** en vista caja con estados visuales en tiempo real
- **Interacción contextual** - Clic en mesa libre (deshabilitado), ocupada (detalles), cuenta solicitada (cobro directo)
- **Auto-limpieza de filtros** después de cada acción completada
- **Búsqueda optimizada** por mesa, cliente o pedido con limpieza automática
- **Notificaciones consistentes** siguiendo patrón de MeseroView (1s éxito, 3s errores)
- **UI simplificada** sin elementos redundantes en pendientes de pago
- **Temporizadores en tiempo real** en KDS View para monitoreo de urgencia
- **KDS Manager ultra-optimizado** para tablet con updates instantáneos sin loading
- **Auto-marcar artículos** cuando se marca pedido como listo
- **Performance mejorado** eliminando refrescos innecesarios
- **🖨️ Sistema de impresión física completo** - Print server + integración frontend
- **📦 Bundle optimization** - Size reducido 99% con chunks inteligentes
- **🔧 Scripts de utilidades** - Gestión automática de categorías
- **⚙️ Configuración avanzada** - Timezone, versioning, debug mode
**Mantenido por: AI Agents & Development Team**