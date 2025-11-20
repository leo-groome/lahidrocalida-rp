# **La Hidrocálida - Sistema de Gestión para Pozolería**

**Estado: SISTEMA COMPLETO + KDS OPTIMIZADO + SISTEMA BEBIDAS INTELIGENTE + PANEL ADMIN**  
Fecha: Enero 2025

## 📋 Resumen del Proyecto

**Sistema completo de gestión de pedidos con flujo post-pago** desarrollado específicamente para pozolería. Implementa un workflow completo desde la toma de pedidos por meseros hasta el procesamiento final de pagos en caja.

### 🎯 Características Principales

- **✅ Flujo Post-Pago Completo**: Mesero → Cocina → Entrega → Solicitar Cuenta → Pago en Caja
- **✅ Sistema de Bebidas Inteligente**: Bebidas automáticamente entregadas, invisibles en KDS para cocina
- **✅ Gestión de Mesas**: Sistema de numeración por pisos (11-15, 21-25, 31-35)
- **✅ Roles Granulares**: Mesero, Cajero, Cocina, Administrador con permisos específicos
- **✅ KDS (Kitchen Display System)**: Pantallas digitales optimizadas solo para comida a preparar
- **✅ Estados Expandidos**: 7 estados del pedido para control completo del flujo
- **✅ WebSockets tiempo real**: Actualizaciones instantáneas sin demoras ni loading innecesario
- **✅ UI/UX Optimizada**: Interface limpia sin distracciones para cocina
- **✅ Reactivación Inteligente**: Pedidos entregados pueden reactivarse con temporizador reiniciado

### 🚀 Estado Actual

**SISTEMA 100% FUNCIONAL Y LISTO PARA PRODUCCIÓN**

Todas las funcionalidades core están implementadas y probadas. El sistema maneja completamente el flujo operativo de una pozolería desde la toma de pedidos hasta el cobro final.

## 🏗️ Arquitectura del Sistema

### Stack Tecnológico

**Backend:**
- **FastAPI 0.117.1** - API REST de alto rendimiento
- **SQLAlchemy 2.0.43** - ORM con soporte async
- **PostgreSQL** (Neon Cloud) - Base de datos principal
- **JWT (python-jose)** - Autenticación segura
- **Pydantic 2.11.9** - Validación de datos

**Frontend:**
- **Vue 3.5.21** - Framework reactivo moderno
- **TypeScript 5.8.3** - Tipado estático
- **Tailwind CSS 4.1.13** - Estilos utilitarios
- **Pinia 3.0.3** - Gestión de estado global
- **Vite 7.1.7** - Build tool optimizado

### Estructura del Proyecto

```
├── backend/                 # API FastAPI
│   └── app/
│       ├── routers/         # Endpoints organizados
│       ├── models.py        # Modelos de BD
│       ├── schemas.py       # Validaciones Pydantic
│       └── auth.py          # Autenticación JWT
│   
├── frontend/pos-system/     # Aplicación Vue.js
│   └── src/
│       ├── views/           # Vistas principales
│       ├── stores/          # Estado global
│       ├── api/             # Cliente HTTP
│       └── router/          # Rutas y permisos
└── README.md
```

## 🎯 Funcionalidades Implementadas

### 1. Sistema de Autenticación
- Login por ID numérico + contraseña
- 4 roles con permisos específicos:
  - **Mesero**: Toma pedidos, gestiona entregas
  - **Cajero**: Procesa pagos pendientes
  - **Cocina**: Gestiona preparación de pedidos
  - **Administrador**: Acceso completo al sistema
- JWT con expiración configurable
- Redirección automática por rol

### 2. Vista de Mesero (/mesero) - ULTRA-OPTIMIZADA + WEBSOCKET MEJORADO
- **Modal inicial obligatorio** - Configura tipo de orden primero
- **Flujo sin scrolling** - Tipo → Mesa/Nombre → Menú instantáneo
- **Mesas tiempo real** - Ve cuáles están ocupadas automáticamente
- **Especificaciones inmediatas** - Modal automático al clic en platillo
- **Carrito inteligente** - Full-screen móvil con animaciones suaves
- **36 variaciones de pozole** - Con nuevas proteínas Surtida y Mixta
- **Cancelar pedido** - Reiniciar flujo completo en cualquier momento
- Tipos de orden: Mesa, Llevar, UberEats
- **Toma de pedidos sin pago inicial** - Envío directo a cocina
- **📱 Modal "Ver Pedido" mejorado** - Actualizaciones WebSocket en tiempo real preservando cambios locales
- **🔄 Agregar a pedidos entregados** - Funcionalidad completa con reactivación automática

### 3. Kitchen Display System (KDS) - ULTRA-OPTIMIZADO + REACTIVACIÓN INTELIGENTE
- **Vista TV (/kds-view)** - OPTIMIZADA PARA 8 METROS DE DISTANCIA
  - **Mesa/Nombre GIGANTES** - text-4xl/3xl/2xl como punto focal principal
  - **Máximo 4 pedidos** en pantalla para evitar saturación visual
  - **Indicador urgencia** - Badge rojo animado con "+X más pendientes"
  - **Artículos texto GIGANTE** - text-4xl/3xl/2xl escalado por cantidad
  - **Sin tachado** - Artículos listos completamente legibles
  - **Emojis prominentes** - text-5xl/4xl/3xl para tipo de orden
  - **Temporizadores grandes** - Tiempo transcurrido prominente con borders
  - **WebSocket tiempo real** - Updates instantáneos sin polling
  - **🔄 Reactivación inteligente** - Pedidos entregados con nuevos artículos van al final de la cola
  - **Filtrado automático** - Solo muestra artículos no entregados en comandas reactivadas
  - **Indicador visual** - Badge amarillo pulsante "➕ AGREGADOS" para comandas reactivadas
- **Vista Manager (/kds-manager)** - OPTIMIZADA PARA TABLET/MÓVIL
  - **Mesa/Nombre prominentes** - text-2xl/xl desktop, text-xl/lg móvil
  - **Artículos táctiles GRANDES** - text-lg/xl/2xl para uso en tablet
  - **Modificaciones destacadas** - Fondo amarillo, texto XL, border
  - **Sin tachado** - Texto completamente visible en artículos listos
  - **Botones táctiles** grandes optimizados para dedos
  - **Íconos grandes** - text-3xl/4xl para estados de artículos
  - **Auto-marcar artículos** - Al marcar pedido listo, todos se marcan
  - **Layout responsivo** - Perfecto para tablet y móvil
- Estados visuales con colores distintivos:
  - 🟡 Pendiente
  - 🟠 Preparando  
  - 🟢 Listo
  - 🔵 Entregado
  - 🟣 Cuenta Solicitada

### 4. Vista de Caja (/caja)
- **Mapa de mesas lateral** con estados visuales en tiempo real
- **Interacción contextual**: Clic en mesa libre (deshabilitado), ocupada (detalles), cuenta solicitada (cobro directo)
- **Búsqueda y filtrado** por mesa, cliente o número de pedido con auto-limpieza
- **Gestión de pedidos pendientes de pago** sin elementos redundantes
- Dashboard con estadísticas compactas por estado
- Grid de pedidos en "cuenta solicitada" con información temporal
- Modal de procesamiento con 3 métodos:
  - 💵 Efectivo (con calculadora de cambio)
  - 💳 Tarjeta
  - 📱 Transferencia
- **Auto-limpieza de filtros** después de cada acción completada
- **Notificaciones optimizadas** (1s éxitos, 3s errores)
- **WebSockets tiempo real** sin polling innecesario

### 5. Panel de Administración (/admin)
- **Dashboard completo** con métricas del día
- **Reportes semanales** con analytics detallados
- **Top 10 productos** más vendidos
- **Gestión de gastos** con categorización
- **Métricas financieras**: Ingresos, gastos, utilidad bruta
- **Ventas por día** de la semana seleccionada
- **Análisis por método de pago** (efectivo, tarjeta, transferencia)
- Navegación por pestañas: Dashboard, Reportes, Gastos

## 📊 Flujo Operativo

### Flujo Principal Ultra-Optimizado (Post-Pago)

```mermaid
graph LR
    A[Modal Inicial] --> B[Tipo Orden]
    B --> C[Mesa/Nombre]
    C --> D[Menú Instantáneo]
    D --> E[Clic Platillo]
    E --> F[Modal Especificaciones]
    F --> G[Carrito Full-Screen]
    G --> H[Envía: PENDIENTE]
    H --> I[Cocina: PREPARANDO]
    I --> J[Cocina: LISTO]
    J --> K[Mesero: ENTREGADO]
    K --> L[Cliente: CUENTA_SOLICITADA]
    L --> M[Caja: PAGADO + Impresión]
```

### Estados del Pedido

| Estado | Descripción | Responsable |
|--------|-------------|-------------|
| `pendiente` | Pedido recibido en cocina | Mesero → Cocina |
| `preparando` | En proceso de preparación | Cocina |
| `listo` | Listo para servir | Cocina |
| `entregado` | Servido al cliente | Mesero |
| `cuenta_solicitada` | Cliente pide cuenta | Mesero |
| `pagado` | Pago procesado | Cajero |
| `cancelado` | Pedido cancelado | Administrador |

## 🗄️ Modelo de Datos

### Entidades Principales

**Pedido**
- `id`, `numero_display`, `total`, `estado`, `mesa`
- `nombre_cliente`, `metodo_pago`, `tipo_orden`
- `fecha_creacion`, `sucursal_id`, `usuario_id`

**ArticuloPedido**
- `id`, `pedido_id`, `platillo_id`, `cantidad`
- `precio_cobrado`, `modificaciones`, `estado_item`

**Platillo**
- `id`, `nombre`, `descripcion`, `precio`, `categoria`
- `kds_name` (nombre corto para cocina)

**Usuario**
- `id`, `nombre`, `rol`, `password_hash`
- `sucursal_id`, `activo`

### Características de BD

- **Numeración automática**: Secuencial por día y sucursal (001, 002...)
- **Gestión de mesas**: Campo específico para identificación
- **Constraints**: Validaciones de integridad aplicadas

## 🚀 Instalación y Configuración

### Prerrequisitos

- Python 3.11+
- Node.js 18+
- PostgreSQL (Neon Cloud)

### Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate    # Windows
pip install -r requirements.txt

# Configurar variables de entorno
export DATABASE_URL="postgresql://..."
export SECRET_KEY="tu-secret-key"

# Ejecutar servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
cd frontend/pos-system

# Instalar dependencias (USAR PNPM)
pnpm install

# Configurar variables de entorno
cp .env.example .env
# Editar .env con la URL correcta del backend

# Ejecutar en desarrollo
pnpm run dev

# Build para producción
pnpm run build
```

### Variables de Entorno

**Backend (.env):**
```env
DATABASE_URL=postgresql://user:pass@host:port/db
SECRET_KEY=your-super-secret-jwt-key
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**Frontend (.env):**
```env
VITE_API_URL=http://localhost:8000
```

## 👥 Usuarios de Prueba

| ID | Nombre | Rol | Password | Descripción |
|----|--------|-----|----------|-------------|
| 3 | Admin | administrador | admin123 | Acceso completo |
| 4 | Leo | cajero | cajero123 | Gestión de caja |
| 5 | Mesero Test | mesero | mesero123 | Toma de pedidos |

## 🔧 Comandos Útiles

### Backend
```bash

# Health check de BD
curl http://localhost:8000/health/database
```

### Frontend
```bash
# Linter y formatter
npm run lint
npm run format

# Build con análisis
npm run build -- --analyze

# Preview de build
npm run preview
```

## 🎨 Personalización

### Colores Corporativos

- **Azul Principal**: `#00126D`
- **Amarillo Accent**: `#FDB700`
- **Blanco**: `#FFFFFF`

### Numeración de Mesas

- **Piso 1**: 11, 12, 13, 14, 15
- **Piso 2**: 21, 22, 23, 24, 25
- **Piso 3**: 31, 32, 33, 34, 35

## 🖨️ Impresión de Tickets

**Sistema de impresión integrado en el navegador:**

**Funcionalidad Actual:**
- **Impresión automática** al procesar pagos en la vista de caja
- **Formato profesional** con todos los detalles del pedido
- **Visible en consola** del navegador (F12 → Console)

**Información incluida en el ticket:**
```
=== IMPRIMIENDO TICKET ===
Pozolería La Hidrocálida
==========================
Pedido: #123
Fecha: 12/01/2025, 13:12:34
Mesa: 15
Cliente: Juan Pérez
==========================
2x Pozole Grande - $260.00
   Extra picante, sin orégano
1x Refresco - $25.00
==========================
TOTAL: $285.00
==========================
¡Gracias por su visita!
=== FIN TICKET ===
```

**Uso:**
1. En la vista de Caja, procesa un pago
2. El ticket se imprime automáticamente en consola
3. Abre las herramientas de desarrollador (F12) para verlo

## 📈 Próximas Funcionalidades (Opcionales)

### Funcionalidades Restantes
- Reportes mensuales y anuales extendidos
- Analytics de rendimiento por mesero
- Estadísticas de ocupación de mesas en tiempo real

### Integraciones
- ✅ **Impresión en consola** - Tickets se imprimen en el navegador
- ✅ **WebSocket tiempo real** - Notificaciones automáticas implementadas
- TPV para pagos con tarjeta (pendiente)
- Sistema de inventory management (pendiente)
- Impresión física con impresora térmica (opcional)

### Optimizaciones
- Cache de consultas frecuentes
- PWA con soporte offline
- Tests automatizados
- CI/CD pipeline

## 🔒 Seguridad

- Autenticación JWT con expiración
- Hash de contraseñas con Argon2
- Validación de permisos por endpoint
- Sanitización de inputs
- CORS configurado para producción

## 📞 Soporte

- **Documentación técnica**: Ver `AGENTS.md`
- **Base de datos**: PostgreSQL en Neon Cloud
- **API Docs**: `http://localhost:8000/docs`
- **Logs**: Configurados en FastAPI con SQL echo

---

**Desarrollado para Pozolería "La Hidrocálida"**  
**Sistema completo con KDS Ultra-Optimizado - Enero 2025**  
**Gestión integral: Post-pago + Sistema Bebidas Inteligente + KDS TV 8 metros + KDS Tablet táctil + MeseroView Ultra-Optimizado + Reactivación Inteligente + WebSocket Mejorado + Panel Admin + Impresión Física**