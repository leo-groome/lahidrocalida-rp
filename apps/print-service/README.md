# 🖨️ Sistema de Impresión - La Hidrocálida

> **Sistema de impresión automática para tickets de caja** - Optimizado para impresora Easytime SP-POS891ED

---

## 📋 Descripción

Este sistema proporciona impresión automática de tickets cuando se solicita la cuenta en el sistema POS de La Hidrocálida. Está específicamente diseñado para trabajar con la impresora térmica Easytime SP-POS891ED (80mm) y se integra automáticamente con el backend FastAPI existente.

### ✨ Características Principales

- 🚀 **Impresión automática** al solicitar cuenta
- 📄 **Formato de ticket idéntico** al sistema actual
- 🖨️ **Soporte nativo** para Easytime SP-POS891ED
- 🔄 **Sistema de cola** con reintentos automáticos
- 🌐 **Integración WebSocket** con el backend
- 📊 **Logs detallados** y monitoreo

---

## 🛠️ Requisitos del Sistema

### Hardware
- **Computadora**: Windows 10/11
- **Impresora**: Easytime SP-POS891ED (80mm térmica USB)
- **Backend**: Sistema POS La Hidrocálida ejecutándose

### Software
- **Python**: 3.8 o superior (viene preinstalado en Windows)
- **Conexión**: Internet para instalación inicial

---

## 📦 Instalación

### Paso 1: Preparar el Entorno
```batch
# Navegar al directorio del servicio de impresión
cd print_service
```

### Paso 2: Instalar Dependencias
```batch
# Ejecutar instalación automática
install.bat
```
**Este comando instala automáticamente:**
- Todas las dependencias de Python
- Librerías necesarias para impresión
- Configuración de directorios

### Paso 3: Verificar Instalación
```batch
# Ejecutar pruebas del sistema
scripts\test_full_system.bat
```

Si todas las pruebas pasan, el sistema está listo ✅

---

## ⚙️ Configuración

### Configuración Básica
Por defecto, el sistema usa:
- **Puerto**: 3001
- **Impresora**: "Generic / Text Only"
- **Backend**: `http://localhost:8000`

### Configuración Avanzada (.env)
Para configurar el servicio sin modificar el código fuente, cree un archivo `.env` en la raíz de `print_service/` (basado en `.env.example`):

```env
# URL base de tu backend (local o de producción en Railway)
BACKEND_URL=https://tu-backend-railway.up.railway.app

# URL del WebSocket de caja para eventos en tiempo real
WEBSOCKET_URL=wss://tu-backend-railway.up.railway.app/ws/caja

# Token de acceso JWT de un usuario con rol 'cajero' o 'administrador'
BACKEND_TOKEN=tu_token_de_acceso_aqui

# Nombre exacto de tu impresora térmica en Windows
PRINTER_NAME=Generic / Text Only
```

---

## 🎯 Uso Diario

### Inicio del Servicio
```batch
# Iniciar servicio de impresión
start_service.bat
```

El servicio se ejecuta en segundo plano y:
- ✅ Se conecta automáticamente al backend
- ✅ Espera eventos de impresión
- ✅ Maneja la cola de tickets

### Verificación de Estado
Abra en navegador: `http://localhost:3001/health`

### Funcionamiento Automático
1. **Mesero solicita cuenta** en el sistema POS
2. **Pedido cambia** a estado `cuenta_solicitada`
3. **Sistema imprime** automáticamente el ticket
4. **Cliente recibe** el comprobante ✅

### Detención del Servicio
```batch
# Detener servicio
stop_service.bat
```

---

## 🧪 Pruebas y Verificación

### Prueba de Impresora
```batch
# Probar conexión con impresora
test_printer.bat
```

### Prueba de Formato
```batch
# Ver formato de ticket de ejemplo
python -c "
from core.ticket_formatter import TicketFormatter
f = TicketFormatter()
print(f.format_ticket({
    'numero_display': '001',
    'mesa': '5',
    'nombre_cliente': 'Juan Perez',
    'articulos': [{'cantidad': 1, 'nombre': 'Pozole Rojo', 'precio': 120.0}],
    'total': 120.0
}))
"
```

### Verificar Logs
```batch
# Ver logs en tiempo real
type logs\print_service.log

# Ver cola de impresión
type logs\print_queue.json

# Ver tickets fallidos
dir logs\failed_tickets\
```

---

## 🔧 Solución de Problemas

### ❌ "Servicio no disponible"
```batch
# Reiniciar servicio
stop_service.bat
start_service.bat
```

### ❌ "Impresora no funciona"
1. Verificar que esté conectada por USB
2. Comprobar nombre en `config/settings.py`
3. Probar con `test_printer.bat`
4. Revisar logs: `logs/print_service.log`

### ❌ "Tickets no se imprimen"
1. Verificar que el backend esté ejecutándose
2. Comprobar estado: `http://localhost:3001/health`
3. Revisar logs del backend
4. Verificar cola: `logs/print_queue.json`

### ❌ "Error de dependencias"
```batch
# Reinstalar dependencias
pip install -r requirements.txt --force-reinstall
```

---

## 📁 Estructura del Proyecto

```
print_service/
├── config/
│   ├── settings.py          # Configuración general
│   └── printer_config.py    # Config. Easytime SP-POS891ED
├── core/
│   ├── printer_manager.py   # Gestión de impresora
│   ├── ticket_formatter.py  # Formato ESC/POS
│   └── print_queue.py       # Sistema de cola
├── server/
│   ├── api_server.py       # API REST
│   └── websocket_bridge.py  # Puente WebSocket
├── scripts/
│   ├── install.bat          # Instalación
│   ├── start_service.bat    # Inicio
│   ├── stop_service.bat     # Detención
│   ├── test_printer.bat     # Prueba impresora
│   └── test_full_system.bat # Prueba completa
├── logs/                    # Logs y cola
├── requirements.txt         # Dependencias
├── printer_service.py       # Punto de entrada
└── README.md               # Esta documentación
```

---

## 📊 Monitoreo y Logs

### Archivos de Log
- **`logs/print_service.log`**: Logs detallados del servicio
- **`logs/print_queue.json`**: Estado de la cola de impresión
- **`logs/failed_tickets/`**: Tickets que fallaron al imprimir

### Métricas Importantes
- **Tiempo de respuesta**: < 1 segundo por ticket
- **Tasa de éxito**: > 95% con reintentos
- **Formato**: 48 caracteres por línea (80mm térmica)

---

## 🔌 Integración Técnica

### Conexión con Backend
- **WebSocket**: `ws://localhost:8000/ws/orders` (escucha eventos)
- **HTTP**: `http://localhost:8000` (API del backend)
- **Evento**: Cambio de estado a `cuenta_solicitada`

### Formato de Comunicación
```json
{
  "numero_display": "042",
  "mesa": "23",
  "nombre_cliente": "Juan Pérez",
  "articulos": [...],
  "total": 360.00
}
```

### Puerto del Servicio
- **API**: `http://localhost:3001`
- **Health Check**: `http://localhost:3001/health`
- **Impresión**: `POST http://localhost:3001/print`

---

## 🆘 Soporte

### Verificación Rápida
```batch
# Estado completo del sistema
scripts\test_full_system.bat

# Estado de salud
curl http://localhost:3001/health
```

### Información de Debug
Si hay problemas, proporcione:
1. Contenido de `logs/print_service.log`
2. Resultado de `scripts\test_full_system.bat`
3. Configuración en `config/settings.py`

---

## 📋 Información Técnica

- **Versión**: 1.0
- **Python**: 3.8+
- **Framework**: Flask + python-escpos
- **SO**: Windows 10/11
- **Impresora**: Easytime SP-POS891ED (80mm térmica)
- **Protocolo**: ESC/POS
- **Ancho**: 48 caracteres por línea

---

## 🎉 ¡Listo para Usar!

Después de seguir estos pasos, el sistema estará completamente funcional y listo para imprimir tickets automáticamente cuando se solicite la cuenta.

**🏪 Sistema POS La Hidrocálida**  
**🖨️ Impresión Automática - Enero 2025**</content>
<parameter name="filePath">C:\Desktop\Vanta Solutions\lahidrocalida-rp\print_service\README.md