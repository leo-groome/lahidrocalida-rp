# **La Hidrocálida - Sistema de Gestión para Pozolería**

**Estado: SISTEMA COMPLETO EN PRODUCCIÓN**  
Fecha: Enero 2025

## 📋 Resumen del Proyecto

**Sistema completo de gestión de pedidos con flujo post-pago** desarrollado específicamente para pozolería. Implementa un workflow completo desde la toma de pedidos por meseros hasta el procesamiento final de pagos en caja.

### 🎯 Características Principales

- **✅ Flujo Post-Pago Completo**: Mesero → Cocina → Entrega → Solicitar Cuenta → Pago en Caja
- **✅ Gestión de Mesas**: Sistema de numeración por pisos (11-15, 21-25, 31-35)
- **✅ Roles Granulares**: Mesero, Cajero, Cocina, Administrador con permisos específicos
- **✅ KDS (Kitchen Display System)**: Pantallas digitales para cocina con estados visuales
- **✅ Estados Expandidos**: 7 estados del pedido para control completo del flujo
- **✅ Auto-refresh**: Actualizaciones en tiempo real en todas las vistas críticas
- **✅ UI/UX Optimizada**: Diseño responsivo con colores corporativos y navegación intuitiva

### 🚀 Estado Actual

**SISTEMA 100% FUNCIONAL Y LISTO PARA PRODUCCIÓN**

Todas las funcionalidades core están implementadas y probadas. El sistema maneja completamente el flujo operativo de una pozolería desde la toma de pedidos hasta el cobro final.

## 🏗️ Arquitectura del Sistema

### Stack Tecnológico

**Backend:**
- **FastAPI 0.117.1** - API REST de alto rendimiento
- **SQLAlchemy 2.0.43** - ORM con soporte async
- **PostgreSQL** (Neon Cloud) - Base de datos principal
- **Alembic 1.13.2** - Migraciones de esquema
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
│   ├── app/
│   │   ├── routers/         # Endpoints organizados
│   │   ├── models.py        # Modelos de BD
│   │   ├── schemas.py       # Validaciones Pydantic
│   │   └── auth.py          # Autenticación JWT
│   └── alembic/             # Migraciones aplicadas
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

### 2. Vista de Mesero (/mesero)
- **Toma de pedidos sin pago inicial**
- Selección obligatoria de mesa
- Grid de productos por categorías
- Carrito de compras con modificaciones
- Modal para variantes de pozole
- Tipos de orden: Mesa, Llevar, UberEats
- Envío directo a cocina

### 3. Kitchen Display System (KDS)
- **Vista de solo lectura** (/kds-view) para pantallas
- **Vista de gestión** (/kds-manager) para staff
- Muestra números de mesa y nombres de cliente
- Estados visuales con colores distintivos:
  - 🟡 Pendiente
  - 🟠 Preparando
  - 🟢 Listo
  - 🔵 Entregado
  - 🟣 Cuenta Solicitada
- Auto-refresh cada 3 segundos
- Control individual de artículos

### 4. Vista de Caja (/caja)
- **Gestión de pedidos pendientes de pago**
- Dashboard con estadísticas por estado
- Grid de pedidos en "cuenta solicitada"
- Modal de procesamiento con 3 métodos:
  - 💵 Efectivo
  - 💳 Tarjeta
  - 📱 Transferencia
- Auto-refresh cada 5 segundos
- Total pendiente en tiempo real

## 📊 Flujo Operativo

### Flujo Principal (Post-Pago)

```mermaid
graph LR
    A[Mesero toma pedido] --> B[Selecciona mesa]
    B --> C[Envía a cocina: PENDIENTE]
    C --> D[Cocina: PREPARANDO]
    D --> E[Cocina: LISTO]
    E --> F[Mesero: ENTREGADO]
    F --> G[Cliente solicita: CUENTA_SOLICITADA]
    G --> H[Caja procesa: PAGADO]
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
- **Migraciones**: Sistema completo con Alembic
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

# Aplicar migraciones
alembic upgrade head

# Ejecutar servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
cd frontend/pos-system
npm install

# Configurar variables de entorno
echo "VITE_API_URL=http://localhost:8000" > .env

# Ejecutar en desarrollo
npm run dev

# Build para producción
npm run build
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
# Crear nueva migración
alembic revision --autogenerate -m "descripcion"

# Aplicar migraciones
alembic upgrade head

# Ver estado de migraciones
alembic current

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

## 📈 Próximas Funcionalidades (Opcionales)

### Reportes y Analytics
- Dashboard de ventas por período
- Análisis de productos más vendidos
- Estadísticas por mesero/cajero
- Reportes de ocupación de mesas

### Integraciones
- Impresión de tickets
- Notificaciones push/WebSocket
- TPV para pagos con tarjeta
- Sistema de inventory management

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
**Sistema completo y funcional - Enero 2025**  
**Flujo post-pago optimizado para restaurantes**