# 🖨️ Sistema de Impresión La Hidrocálida - Windows

> **Sistema completo de impresión automática para tickets** - Optimizado para Easytime SP-POS891ED

---

## 🚀 INSTALACIÓN RÁPIDA (5 minutos)

### 1. Preparar Todo
```batch
install.bat
```
**¡Esto configura TODO automáticamente!**

### 2. Configurar Impresora
- Asegúrese de que la impresora Easytime SP-POS891ED esté conectada por USB
- Si no es la impresora por defecto, modifique `config/settings.py`

### 3. Iniciar Servicio
```batch
start_service.bat
```
**El servicio se conecta automáticamente al backend**

### 4. ¡Listo!
**Ahora los tickets se imprimen automáticamente al solicitar cuenta** ✅

---

## 📋 ARCHIVOS IMPORTANTES

| Archivo | Función | Cuándo usar |
|---------|---------|-------------|
| `install.bat` | 📦 Instala todo | Solo la primera vez |
| `start_service.bat` | 🚀 Inicia servicio | **Uso diario** |
| `test_printer.bat` | 🧪 Prueba impresora | Verificar funcionamiento |
| `stop_service.bat` | 🛑 Detiene servicio | Si hay problemas |
| `config/settings.py` | ⚙️ Configuración | Personalizar impresora |
| `logs/print_service.log` | 📊 Logs detallados | Revisar problemas |

---

## 🎯 USO DIARIO

### Cada Mañana
1. **Conectar impresora térmica** Easytime SP-POS891ED por USB
2. **Doble click** en `start_service.bat`
3. **Verificar** que aparezca "🚀 Puente WebSocket iniciado"
4. **¡Listo!** - Funciona automáticamente

### Durante el Día
- **Los tickets se imprimen solos** cuando se solicita cuenta
- **Si no imprime** → Verificar que el servicio esté ejecutándose
- **Si hay problemas** → Revisar logs en `logs/print_service.log`

### Al Cerrar
- **Dejar el servicio ejecutándose** (opcional)
- **O cerrar** la ventana del servicio

---

## ⚡ SISTEMA DE IMPRESIÓN INTELIGENTE

### 🔥 PRIORIDAD 1: Impresora Térmica Easytime
- ✅ **Automática** - Sin intervención
- ✅ **Profesional** - Formato perfecto para 80mm
- ✅ **Rápida** - Impresión instantánea
- ✅ **Robusta** - Sistema de cola con reintentos

### 💻 PRIORIDAD 2: Cola de Impresión
- ✅ **Reintentos automáticos** cada 30 segundos
- ✅ **Máximo 5 reintentos** por ticket
- ✅ **Tickets fallidos guardados** para revisión
- ✅ **Notificaciones** de fallos críticos

---

## 🛠️ CONFIGURACIÓN AVANZADA

### Cambiar Impresora
Edite `config/settings.py`:
```python
PRINTER_NAME = "Nombre de su impresora"
```

### Configurar Backend
Edite `config/settings.py`:
```python
BACKEND_URL = "http://localhost:8000"
WEBSOCKET_URL = "ws://localhost:8000/ws/orders"
```

### Ver Logs
Los logs se guardan en `logs/print_service.log`:
```batch
type logs\print_service.log
```

---

## 🔧 SOLUCIONES RÁPIDAS

### ❌ "Servicio no disponible"
**Solución**: `start_service.bat` → Verificar "🚀 Puente WebSocket iniciado"

### ❌ "Python no encontrado"
**Solución**: Instalar Python desde https://python.org → Marcar "Add to PATH"

### ❌ "Impresora no funciona"
**Solución**:
1. Verificar conexión USB
2. Probar con `test_printer.bat`
3. Revisar nombre en `config/settings.py`

### ⚠️ "Tickets no se imprimen"
**Solución**:
1. Verificar que el backend esté ejecutándose
2. Revisar logs del servicio
3. Probar conexión manual con `test_printer.bat`

---

## 📊 MONITOREO Y DASHBOARD

### Verificar Estado
```batch
curl http://localhost:3001/health
```

### Ver Cola de Impresión
```batch
type logs\print_queue.json
```

### Ver Tickets Fallidos
```batch
dir logs\failed_tickets\
```

---

## 🎉 RESULTADO FINAL

### ✅ LO QUE FUNCIONA:
- **Impresión automática** al solicitar cuenta (estado `cuenta_solicitada`)
- **Formato de ticket idéntico** al actual
- **Soporte nativo** para Easytime SP-POS891ED (80mm térmica)
- **Sistema de cola robusto** con reintentos automáticos
- **Integración completa** con el backend vía WebSocket
- **Logs detallados** para troubleshooting
- **Fácil de usar** - solo doble click diario

### 🔄 FLUJO COMPLETO:
1. **Mesero** solicita cuenta en el sistema
2. **Backend** cambia estado a `cuenta_solicitada`
3. **WebSocket** notifica al servicio de impresión
4. **Servicio** genera ticket ESC/POS automáticamente
5. **Easytime SP-POS891ED** imprime el ticket
6. **Cliente recibe** su comprobante ✅

---

## 📞 AYUDA RÁPIDA

### Verificar que Todo Funciona
```batch
# 1. Instalar
install.bat

# 2. Configurar impresora (opcional)
# Editar config/settings.py si es necesario

# 3. Iniciar
start_service.bat

# 4. Probar
test_printer.bat

# 5. Verificar logs
type logs\print_service.log
```

### Ver Estado del Sistema
```batch
# Health check
curl http://localhost:3001/health

# Cola de impresión
type logs\print_queue.json

# Logs del servicio
type logs\print_service.log
```

### Controlar Servicio
- **Iniciar**: `start_service.bat`
- **Detener**: `stop_service.bat`
- **Probar**: `test_printer.bat`
- **Estado**: `curl http://localhost:3001/health`

---

## 📋 INFORMACIÓN TÉCNICA

- **Puerto del servicio**: 3001
- **URL de verificación**: http://localhost:3001/health
- **Formato de impresión**: ESC/POS (térmica 80mm)
- **Impresora compatible**: Easytime SP-POS891ED
- **Compatibilidad**: Windows 10/11
- **Tickets fallidos**: `logs/failed_tickets/`
- **Cola persistente**: `logs/print_queue.json`

---

**🏪 Sistema POS La Hidrocálida**  
**📅 Versión Nueva - Enero 2025**  
**🖨️ Impresión automática garantizada**