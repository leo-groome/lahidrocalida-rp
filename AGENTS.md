# AGENTS.md - Development Guidelines for AI Agents

## 🚀 Build, Lint & Test Commands

### Backend (FastAPI/Python)

**Environment Setup:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

**Development Server:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Database Health Check:**
```bash
curl http://localhost:8000/health/database
```

**API Documentation:**
- Auto-generated docs: `http://localhost:8000/docs`
- Alternative docs: `http://localhost:8000/redoc`

**Run Single Test File:**
```bash
# No automated test framework configured
# Run individual test files manually:
python print_service/scripts/test_printer.bat
python print_service/scripts/test_full_system.bat
```

### Frontend (Vue.js/TypeScript)

**Environment Setup:**
```bash
cd frontend/pos-system
# Preferred: pnpm (project standard)
# If pnpm is not available on the machine:
# corepack enable
# corepack prepare pnpm@latest --activate
pnpm install  # Always use pnpm, never npm
cp .env.example .env
# Edit .env with correct VITE_API_URL
```

**Development Server:**
```bash
pnpm run dev  # Port 5173
```

**Build Commands:**
```bash
pnpm run build              # Production build
pnpm run build:analyze      # Bundle analysis with visualizer
pnpm run bundle-size        # Show bundle sizes
pnpm run preview           # Preview production build
```

**Type Checking:**
```bash
# No dedicated type check script
# Types checked during build
pnpm run build  # Includes TypeScript compilation
```

## 📝 Code Style Guidelines

### Python (Backend)

**Imports:** Standard library first, third‑party second, local imports grouped by module.

**Function Signatures:** Use type hints and docstrings for public functions.

**Error Handling:** Use try/except with specific exceptions; return user‑friendly error messages.

**Naming Conventions:**
- Functions: `snake_case`
- Classes: `PascalCase`
- Variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`

**Database Queries:** Use SQLAlchemy ORM methods; for complex queries use `func` and proper joins.

### TypeScript/Vue (Frontend)

**File Structure:** Follow Vue 3 `<script setup>` composition API.

**Component Structure:** Use reactive state (`ref`, `reactive`), computed properties, and lifecycle hooks.

**Type Definitions:** Use TypeScript interfaces with union types for enums; mark nullable fields optional.

**API Calls:** Centralized Axios client with request/response interceptors.

**State Management:** Pinia stores with Composition API syntax.

**Naming Conventions:**
- Components: `PascalCase`
- Files: `PascalCase` for components, `kebab‑case` for others
- Variables/Functions: `camelCase`
- Types: `PascalCase`
- Constants: `camelCase` or `UPPER_SNAKE_CASE`

**Error Handling:** Wrap async operations in try/catch; display user‑friendly error messages.

## 🔧 Development Workflow

### Adding New Features
**Backend:** Update schemas → add router endpoint → include auth → implement DB operations → test.
**Frontend:** Define types → create component → add reactive state → implement error handling → add to router.

### Database Changes
**Modifying models:** Update SQLAlchemy model and Pydantic schemas; test endpoints.
**New entities:** Create model, schemas, router, frontend types, and test CRUD cycle.

### Code Quality Checks
1. Run backend server and test endpoints manually.
2. Build frontend to verify TypeScript compilation.
3. Test critical user flows.
4. Verify database health endpoint.

## 📋 Environment Configuration

**Backend (.env):**
```env
DATABASE_URL=postgresql://user:pass@host:port/db
SECRET_KEY=your-super-secret-jwt-key
ACCESS_TOKEN_EXPIRE_MINUTES=30
TIMEZONE=America/Mexico_City
```

**Frontend (.env):**
```env
VITE_API_URL=http://localhost:8000
```

## 🧪 Testing Strategy

- No automated test framework configured.
- Manual testing via API endpoints and UI.
- Utility test scripts in `print_service/scripts/` (run individually).
- Frontend UI Guidelines:
- - Pozole button: ensure desktop grid alignment; color green; increased padding and height adjustments as implemented.
- - Ensure consistency across responsive breakpoints; mobile keeps the existing modal behavior.
- Print service includes comprehensive verification scripts.
- Nueva guía de pruebas para Caja (Edición de pedidos):
- Edición de articulos en Pedido Actual mediante un modal accesible desde cada tarjeta en Pedidos Activos.
- El modal permite eliminar artículos (con delete) y modificar cantidades; no se pueden añadir artículos nuevos.
- El borrado de artículos se aplica al guardar enviando PUT /pedidos/{id}/actualizar-articulos con un payload que incluye artículos existentes con cantidad actualizada y artículos eliminados con cantidad 0.
- Tras guardar, se recarga el pedido completo con GET /pedidos/{id} para reflejar los cambios, sin modificar el estado del pedido.
- Se añadió la opción de imprimir adelantadamente el ticket desde la tarjeta (POST /pedidos/{id}/imprimir).
- En la UI, la zona de edición de artículos es scrollable cuando hay más de 3 artículos para evitar desplazar el resto de la tarjeta.
- Recommended future setup: pytest (backend), Vitest/Playwright (frontend).

## 🖨️ Sistema de Impresión Automática

**Nuevo sistema completo para impresión automática de tickets de caja**

### Arquitectura del Sistema
- **Tecnología**: Python + ESC/POS + Flask API
- **Impresora compatible**: Easytime SP-POS891ED (80mm térmica)
- **Integración**: WebSocket + HTTP con backend FastAPI
- **Sistema operativo**: Windows 10/11

### Inicio Rápido
```batch
# 1. Instalar
cd print_service
install.bat

# 2. Iniciar servicio
start_service.bat

# 3. ¡Listo! Los tickets se imprimen automáticamente
```

### Scripts de Control
```batch
install.bat          # Instalación automática
start_service.bat    # Iniciar servicio
stop_service.bat     # Detener servicio
test_printer.bat     # Probar impresora
scripts/test_full_system.bat    # Pruebas completas
scripts/verify_system.bat      # Verificación final
scripts/status.bat             # Estado del sistema
```

### Estructura del Sistema
```
print_service/
├── config/           # Configuración específica
├── core/             # Lógica principal
│   ├── printer_manager.py     # Gestión impresora
│   ├── ticket_formatter.py    # Formato ESC/POS
│   └── print_queue.py         # Cola con reintentos
├── server/           # API y WebSocket
├── scripts/          # Control y verificación
├── logs/             # Logs y cola persistente
└── README.md         # Documentación completa
```

### Integración con Backend
**Archivo modificado**: `backend/app/routers/pedidos.py`
- Nueva función: `print_ticket_automatic()`
- Trigger automático: Estado `cuenta_solicitada`
- Comunicación: HTTP POST a `http://localhost:3001/print`

### Características Técnicas
- **Impresión automática** al solicitar cuenta
- **Formato idéntico** al sistema actual (48 chars/línea)
- **Sistema de cola robusto** con reintentos (máx. 5)
- **Logs detallados** en `logs/print_service.log`
- **API REST** en puerto 3001 para integración
- **Puente WebSocket** para eventos en tiempo real

### Verificación del Sistema
```batch
# Estado completo
scripts\status.bat

# Verificación final
scripts\verify_system.bat

# Health check
curl http://localhost:3001/health
```

### Configuración
- **Impresora**: Configurable en `config/settings.py`
- **Backend URL**: Configurable en `config/settings.py`
- **Puerto**: 3001 (configurable)
- **Reintentos**: 5 (configurable)
- **Intervalo**: 30 segundos (configurable)

## 🚨 Critical Patterns to Follow

1. **Always use virtual environment** for Python development.
2. **Always use pnpm** instead of npm for frontend dependencies.
3. **Validate user permissions** on all protected endpoints.
4. **Use proper TypeScript typing** throughout the frontend.
5. **Handle errors gracefully** with user‑friendly messages.
6. **Follow existing naming conventions** for consistency.
7. **Test WebSocket functionality** when modifying real‑time features.
8. **Document API changes** in the FastAPI automatic documentation.
9. **Implement tip modal flow correctly**: Show tip modal only after selecting card/transfer payment method with quick percentage buttons (10%/15%/20%) and specific amount field. For cash payments, display cash received field before optional tip.
10. **Implement split-bill flow correctly** (admin-only): allow dividir cuenta (2-5) for `entregado` or `cuenta_solicitada`, mark original order as `dividido`, and create new orders in `cuenta_solicitada` with `Cuenta i/n` label; print one ticket per cuenta.
11. **Manual status override (admin-only)**: from Caja "Pedidos Activos" allow admin to change `estado` via a dropdown on the status badge (no payment/propina changes); use this only for exceptional cases.
12. **Manual beverage delivery (mesero/admin)**: bebidas (Platillo.categoria == `Bebidas`) are NOT auto-delivered; mesero/admin can mark beverage items as `entregado` from Mesero "Ver pedido actual". Caja shows item status read-only.
13. **Ticket math and metadata**: ticket line items must use unit price (precio_cobrado / cantidad) to avoid inflated totals; include `Mesero`, `Hora llegada` (fecha_creacion), and `Hora salida` (fecha_pago, set when order becomes `pagado`).
14. **KDS beverage filter**: cocina/KDS must hide Bebidas; if a pedido has only Bebidas it should not appear in KDS.


## 💸 Gestión de Gastos

**Modelo y flujo:**
- `Gasto` es cabecera de compra con proveedor, tipo de gasto, método de pago, subtotal/total y `total_manual` opcional.
- `GastoDetalle` son líneas con artículo, cantidad y precio unitario.
- `nomina` no lleva artículos; se captura con `total_manual` + `notas` (nombre/periodo).

**Catálogos:**
- `Proveedor`: nombre, teléfono, dirección, notas.
- `CategoriaArticulo`: catálogo editable.
- `Articulo`: nombre, unidad, categoría, costo estándar.

**Enums y valores fijos:**
- Tipos de gasto: `directo`, `indirecto`, `nomina`.
- Métodos de pago: `efectivo`, `tarjeta`.
- Unidades válidas: `kg`, `g`, `lt`, `ml`, `pza`, `caja`, `paq`.

**API:**
- `/gastos` (CRUD con filtros por fecha, proveedor, tipo, método, categoría).
- `/gastos/proveedores`, `/gastos/categorias-articulo`, `/gastos/articulos`.

**UI (Admin):**
- Tab Gestión de Gastos con subtabs: Gastos, Proveedores, Artículos, Categorías.

## 🏦 Gestión de Turnos y Cierre de Caja

**Nueva funcionalidad para control de efectivo y turnos de cajero:**

### Backend - Endpoints Principales (`/turnos`)
- `POST /turnos/iniciar` - Iniciar turno con conteo inicial
- `POST /turnos/{id}/cerrar` - Cerrar turno con conteo final y resumen automático
- `GET /turnos/activo` - Obtener turno activo actual
- `GET /turnos` - Listar turnos (filtros: fecha, estado, cajero)
- `GET /turnos/{id}` - Detalle completo de turno
- `PUT /turnos/{id}` - Editar turno (solo si está abierto)
- `GET /turnos/{id}/resumen` - Resumen detallado para modal de cierre (incluye comandas cobradas efectivo, gastos del turno y total esperado en caja)


**Modelos de Base de Datos:**
- `Turno`: sucursal, cajero, fechas, totales, estado (abierto/cerrado)
- `TurnoDenominacion`: tipo (inicial/final), denominación (1000-1), cantidad, subtotal

**Frontend - Componentes:**
- `TurnoModal.vue`: Modal reutilizable para inicio/cierre con 10 denominaciones
- `CajaView.vue`: Botón dinámico "Iniciar/Cerrar Turno" en barra superior

**Flujo de Usuario:**
1. Cajero hace clic en botón "Iniciar Turno" (verde)
2. Ingresa cantidades de billetes/monedas (1000, 500, 200, 100, 50, 20, 10, 5, 2, 1)
3. Sistema calcula total en tiempo real
4. Al cerrar turno, sistema calcula automáticamente:
   - Ventas en efectivo durante el turno
   - Propinas en efectivo
   - Diferencia entre conteo final y esperado
5. Botón cambia a "Cerrar Turno" (rojo) durante el turno activo

**Ejemplo Request Iniciar Turno:**
```json
{
  "conteo_inicial": {
    "denominaciones": [
      {"denominacion": 1000, "cantidad": 5},
      {"denominacion": 500, "cantidad": 10},
      {"denominacion": 100, "cantidad": 20}
    ]
  },
  "observaciones": "Fondo inicial del día"
}
```

**Validaciones:**
- Solo un turno activo por sucursal
- Solo cajeros/administradores pueden gestionar turnos
- Cajeros solo pueden editar sus propios turnos
- Denominaciones válidas: 1000, 500, 200, 100, 50, 20, 10, 5, 2, 1
- Cálculos automáticos de ventas y diferencias


**🛠️ Correcciones y Mejoras Implementadas:**

**Bug Fix Backend:**
- Corregido `NameError: name 'Opt' is not defined` en `app/routers/turnos.py`
- Reemplazado alias `Opt` por `Optional` en parámetros de función `listar_turnos`
- Servidor ahora inicia sin errores de importación

**Mejoras UI - Modal Compacto:**
- Modal redimensionado: `max-w-4xl` → `max-w-2xl` (más estrecho)
- Altura máxima reducida: `max-h-[90vh]` → `max-h-[85vh]`
- Header más compacto con menos padding
- Tabla de denominaciones con fuentes y elementos más pequeños
- Botones +/- reducidos (`w-8 h-8` → `w-6 h-6`)
- Inputs numéricos más estrechos (`w-20` → `w-14`)
- Scroll vertical solo en contenido, no en todo el modal
- Espacios entre secciones optimizados

**Mejoras en Reporte del Día - CajaView:**
- Eliminada la caja inicial con 3 recuadros (propina efectivo, tarjeta, total) en la sección "Reporte del dia".
- Agregada tabla completa "Pedidos del Día" desde AdminView.vue a la sección de analíticas, incluyendo filtros por método de pago, ordenamiento por fecha, y resumen estadístico.
- Conectadas las analíticas al WebSocket para actualizaciones en tiempo real, eliminando el polling automático de 60 segundos.
- Actualizado endpoint backend `/reportes/dia/tickets` para incluir campo `tipo_orden` en la respuesta.
- Actualizadas interfaces TypeScript para incluir `tipo_orden` opcional en `ReporteDiaTicket`.

---

## 📚 Key Files Reference

**Backend:**
- `app/main.py` – FastAPI app setup and CORS
- `app/models.py` – SQLAlchemy database models (incluye `Turno`, `TurnoDenominacion`)
- `app/schemas.py` – Pydantic request/response models (incluye schemas para turnos)
- `app/routers/` – API endpoint definitions (incluye `turnos.py` para gestión de turnos y `pedidos.py` con integración de impresión automática)

**Frontend:**
- `src/types.ts` – TypeScript type definitions (incluye `Turno`, `Denominacion`)
- `src/api/client.ts` – Axios HTTP client configuration
- `src/stores/` – Pinia state management stores
- `src/views/` – Main application views/pages
- `src/components/TurnoModal.vue` – Modal para inicio/cierre de turno con conteo rápido

**Sistema de Impresión:**
- `print_service/printer_service.py` – Servicio principal de impresión
- `print_service/core/printer_manager.py` – Gestión de impresora Easytime SP-POS891ED
- `print_service/core/ticket_formatter.py` – Formateo ESC/POS de tickets
- `print_service/core/print_queue.py` – Sistema de cola con reintentos
- `print_service/server/api_server.py` – API REST para integración
- `print_service/server/websocket_bridge.py` – Puente WebSocket con backend
- `print_service/config/settings.py` – Configuración del sistema de impresión
- `print_service/config/printer_config.py` – Configuración específica SP-POS891ED

---

**🖨️ Actualización Enero 2025:** Sistema de impresión automática implementado con soporte completo para impresora térmica Easytime SP-POS891ED. Ver sección "Sistema de Impresión Automática" para detalles completos.

*No Cursor rules (`/.cursor/rules/`) or Copilot instructions (`/.github/copilot‑instructions.md`) are present in this repository.*
