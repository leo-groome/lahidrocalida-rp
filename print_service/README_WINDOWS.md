# 🖨️ Sistema de Impresión La Hidrocálida - Windows

> **Para computadora de caja Windows** - Guía rápida de instalación y uso

---

## 🚀 INSTALACIÓN RÁPIDA (5 minutos)

### 1. Preparar Todo
```batch
install.bat
```
**¡Esto configura TODO automáticamente!**

### 2. Iniciar Servicio
```batch
inicio_rapido.bat
```
**Seleccionar Opción 1** - Iniciar servicio

### 3. Probar Funcionamiento
**En el mismo menú** - **Opción 2** - Probar impresión

### 4. ¡Listo!
**Ahora el sistema de caja imprime automáticamente** ✅

---

## 📋 ARCHIVOS IMPORTANTES

| Archivo | Función | Cuándo usar |
|---------|---------|-------------|
| `install.bat` | 📦 Instala todo | Solo la primera vez |
| `inicio_rapido.bat` | 🎯 Menú principal | **Uso diario** |
| `start_print_service.bat` | 🚀 Inicia servicio | Inicio directo |
| `test_connection.bat` | 🧪 Prueba sistema | Verificar funcionamiento |
| `stop_print_service.bat` | 🛑 Detiene servicio | Si hay problemas |

---

## 🎯 USO DIARIO

### Cada Mañana
1. **Conectar impresora térmica** USB
2. **Doble click** en `inicio_rapido.bat`
3. **Opción 1** - Iniciar servicio
4. **¡Listo!** - Funciona automáticamente

### Durante el Día
- **Los tickets se imprimen solos** cuando se procesa pago
- **Si no imprime** → Verifica que la ventana del servicio esté abierta
- **Si hay problemas** → `inicio_rapido.bat` → Opción 4

### Al Cerrar
- **Dejar el servicio ejecutándose** (opcional)
- **O cerrar** la ventana del servidor

---

## ⚡ SISTEMA DE IMPRESIÓN INTELIGENTE

### 🔥 PRIORIDAD 1: Impresora Térmica
- ✅ **Automática** - Sin intervención
- ✅ **Profesional** - Formato de restaurante
- ✅ **Rápida** - Impresión instantánea

### 💻 PRIORIDAD 2: Impresora del Sistema
- ✅ **Fallback automático** si térmica no funciona
- ✅ **Usa impresora normal** de Windows
- ✅ **Formato optimizado** para papel A4

### 🖥️ PRIORIDAD 3: Consola del Navegador
- ✅ **Nunca falla** - Siempre funciona
- ✅ **Visible en F12** del navegador
- ✅ **Formato completo** para copiar/pegar

---

## 🛠️ SOLUCIONES RÁPIDAS

### ❌ "Servicio no disponible"
**Solución**: `inicio_rapido.bat` → Opción 1

### ❌ "Python no encontrado"
**Solución**: Instalar Python desde https://python.org → Marcar "Add to PATH"

### ❌ "Impresora no funciona"
**Solución**: ¡Tranquilo! El sistema usa fallback automático

### ⚠️ "Puerto 3001 ocupado"
**Solución**: `stop_print_service.bat` → `start_print_service.bat`

---

## 🔧 CONFIGURACIÓN AVANZADA

### Inicio Automático con Windows
1. **Windows + R** → `shell:startup`
2. **Copiar** `inicio_rapido.bat` a esa carpeta
3. **Reiniciar** - Se abre automáticamente

### Acceso Directo en Escritorio
1. **Click derecho** en `inicio_rapido.bat`
2. **Enviar a → Escritorio**
3. **Renombrar** a "🖨️ La Hidrocálida"

---

## 🎉 RESULTADO FINAL

### ✅ LO QUE FUNCIONA:
- **Impresión automática** de tickets al procesar pagos
- **3 métodos de respaldo** - nunca falla
- **Formato profesional** para restaurante
- **Fácil de usar** - solo doble click diario
- **Sin configuración compleja** - todo automático

### 🔄 FLUJO COMPLETO:
1. **Mesero** solicita cuenta
2. **Caja** procesa pago
3. **Ticket se imprime automáticamente** 🖨️
4. **Cliente recibe su comprobante** ✅

---

## 📞 AYUDA RÁPIDA

### Verificar que Todo Funciona
```batch
test_connection.bat
```

### Ver Estado del Sistema
```batch
inicio_rapido.bat
```
→ **Opción 4**

### Controlar Servicio
- **Iniciar**: Opción 1
- **Probar**: Opción 2  
- **Detener**: Opción 3
- **Estado**: Opción 4

---

## 📋 INFORMACIÓN TÉCNICA

- **Puerto del servicio**: 3001
- **URL de verificación**: http://localhost:3001/health
- **Formato de impresión**: ESC/POS (térmicas 80mm/58mm)
- **Compatibilidad**: Windows 7/8/10/11
- **Respaldos**: Tickets fallidos en `failed_tickets\`

---

**🏪 Sistema POS La Hidrocálida**  
**📅 Versión Windows - Enero 2025**  
**🖨️ Impresión automática garantizada**