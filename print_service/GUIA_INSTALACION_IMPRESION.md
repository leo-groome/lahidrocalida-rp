# 🖨️ Guía de Instalación - Sistema de Impresión La Hidrocálida

## 📋 Resumen

El sistema de impresión funciona con **3 niveles de fallback automático**:
1. **🔥 Impresora térmica ESC/POS** (puerto 3001) ← **PRIORIDAD 1**
2. **💻 Impresora del sistema** (window.print) ← **FALLBACK 1**
3. **🖥️ Consola del navegador** (F12 para ver) ← **FALLBACK 2**

---

## 🚀 Instalación Rápida (Windows)

### 1. Preparar el Entorno

```batch
cd print_service
install.bat
```
**¡Esto instala TODO automáticamente!**

### 2. Iniciar el Servicio

**OPCIÓN A - Menú Interactivo (Recomendado):**
```batch
inicio_rapido.bat
```

**OPCIÓN B - Inicio Directo:**
```batch
start_print_service.bat
```

### 3. Verificar Funcionamiento

```batch
test_connection.bat
```

### 4. Uso Diario

**Para cada día de trabajo:**
1. Doble clic en `inicio_rapido.bat`
2. Seleccionar **Opción 1** - Iniciar servicio
3. ¡Listo! El sistema funciona automáticamente

---

## 🔧 Configuración de Impresora Térmica

### Requisitos de Hardware

- **Impresora térmica 80mm** (58mm también compatible)
- **Conexión USB** o puerto serie
- **Drivers instalados** en el sistema operativo

### Configuración para Windows (Computadora de Caja)

#### 🪟 Configuración Automática
1. **Conectar impresora térmica USB** al puerto USB
2. **Ejecutar `install.bat`** - Configura todo automáticamente
3. **Windows detectará la impresora** - Instalar drivers si se solicita
4. **Listo** - El sistema manejará todo lo demás

#### 🔧 Configuración Manual (si es necesario)
1. **Panel de Control → Dispositivos e Impresoras**
2. **Verificar que aparece la impresora térmica**
3. **Click derecho → Propiedades → Imprimir página de prueba**
4. **Si funciona** → Configuración completa

#### 📋 Puertos Comunes en Windows
- **USB**: Automático (recomendado)
- **Puerto Serie**: COM1, COM2, COM3...
- **Puerto Paralelo**: LPT1 (impresoras antiguas)

> **💡 Tip**: La mayoría de impresoras térmicas USB funcionan automáticamente sin configuración especial

---

## 🧪 Pruebas del Sistema

### Test Automático Completo (Recomendado)
```batch
test_connection.bat
```
**¡Prueba TODA la funcionalidad automáticamente!**

### Test desde Menú Interactivo
```batch
inicio_rapido.bat
```
→ Seleccionar **Opción 2** - Probar conexión y impresión

### Test Manual (Avanzado)
1. **Abrir navegador** → `http://localhost:3001/health`
2. **Si aparece un JSON** → Servidor funcionando ✅
3. **Si no carga** → Ejecutar `start_print_service.bat`

### Test desde el Sistema de Caja
1. **Ir a Vista de Caja** en el navegador
2. **Procesar cualquier pedido** en estado "Cuenta Solicitada"
3. **Verificar impresión automática** (térmica/sistema/consola)

---

## 🎯 Flujo Operativo Completo (Windows)

### 1. Configuración Inicial (Una sola vez)
```batch
cd print_service
install.bat                     REM Instalar TODO automáticamente
test_connection.bat             REM Verificar funcionamiento
```

### 2. Uso Diario
```batch
inicio_rapido.bat               REM Menú interactivo
```
→ **Opción 1** - Iniciar servicio  
→ **Listo** - No requiere más intervención

### 3. Proceso de Impresión Automático
1. **Mesero** solicita cuenta → Se genera ticket
2. **Caja** procesa pago → **Se imprime automáticamente**
3. **Sistema** intenta en orden:
   - ✅ **Impresora térmica** (puerto 3001) ← **PREFERIDO**
   - ✅ **Impresora del sistema** (window.print) ← **FALLBACK 1**
   - ✅ **Consola del navegador** (F12) ← **FALLBACK 2**

### 4. Control del Servicio
- **Iniciar**: `start_print_service.bat`
- **Detener**: `stop_print_service.bat`
- **Probar**: `test_connection.bat`
- **Estado**: `inicio_rapido.bat` → Opción 4

---

## 🛠️ Solución de Problemas (Windows)

### ❌ Error: "Servicio no disponible"

**Causa**: El servidor en puerto 3001 no está ejecutándose

**Solución Rápida**:
```batch
inicio_rapido.bat
```
→ **Opción 1** - Iniciar servicio

**Solución Manual**:
```batch
start_print_service.bat
REM Esperar a ver: "Running on http://localhost:3001"
```

### ❌ Error: "Impresora no encontrada"

**Causa**: La impresora térmica no está conectada o configurada

**Solución**:
1. **Verificar cable USB** conectado firmemente
2. **Windows detecta automáticamente** la mayoría de impresoras USB
3. **Panel de Control → Dispositivos** → Verificar que aparece
4. **¡El sistema usa fallback automático!** - Sigue funcionando

### ❌ Error: "Python no encontrado"

**Causa**: Python no está instalado en Windows

**Solución**:
1. **Descargar Python** desde https://python.org/downloads/
2. **Durante instalación**: ✅ Marcar "Add to PATH"
3. **Reiniciar** la computadora
4. **Ejecutar** `install.bat` nuevamente

### ❌ Error: "ModuleNotFoundError: flask"

**Causa**: Dependencias no instaladas

**Solución Automática**:
```batch
install.bat
```

**Solución Manual**:
```batch
pip install flask flask-cors
```

### ⚠️ Warning: "Fallback to system printer"

**Causa**: Impresora térmica no disponible, usando impresora del sistema

**Impacto**: **Normal** - el ticket se imprime correctamente en impresora alternativa

### 🟡 Info: "Fallback to console"

**Causa**: Ni impresora térmica ni del sistema disponibles

**Impacto**: **Aceptable** - ticket visible en consola del navegador (F12)

---

## 📊 Estados del Sistema

| Estado | Significado | Acción Requerida |
|--------|-------------|------------------|
| 🟢 **Impresora Térmica OK** | Sistema completo funcionando | Ninguna |
| 🟡 **System Printer Fallback** | Térmica no disponible, usando sistema | Verificar impresora térmica |
| 🟠 **Console Fallback** | Solo impresión en navegador | Verificar impresoras |
| 🔴 **Service Unavailable** | Servidor no ejecutándose | Iniciar servicio de impresión |

---

## 🔄 Automatización Windows

### Inicio Automático con Windows (Recomendado)

#### Método 1: Carpeta de Inicio (Más fácil)
1. **Presiona** `Windows + R`
2. **Escribe** `shell:startup` y Enter
3. **Copia** el archivo `inicio_rapido.bat` a esa carpeta
4. **Reinicia** la computadora
5. **Se abrirá automáticamente** al iniciar Windows

#### Método 2: Programador de Tareas (Avanzado)
1. **Buscar** "Programador de tareas" en Windows
2. **Crear tarea básica...**
   - Nombre: "La Hidrocálida - Servicio de Impresión"
   - Desencadenador: "Al iniciar el sistema"
   - Acción: "Iniciar un programa"
   - Programa: `C:\ruta\completa\print_service\start_print_service.bat`
3. **Finalizar**

#### Método 3: Acceso Directo en Escritorio
1. **Click derecho** en `inicio_rapido.bat`
2. **Enviar a → Escritorio (crear acceso directo)**
3. **Renombrar** a "🖨️ Sistema de Impresión"
4. **Doble click diario** para iniciar

---

## 📝 Logs y Monitoreo (Windows)

### Verificar Estado del Servicio
```batch
REM Usando el menú interactivo
inicio_rapido.bat
REM → Opción 4 - Ver estado del servicio

REM O verificar manualmente en navegador:
REM http://localhost:3001/health
```

### Ver Logs del Servidor
- **Los logs aparecen** en la ventana donde se ejecutó `start_print_service.bat`
- **Mantén esa ventana abierta** para ver la actividad en tiempo real
- **Cada impresión** aparece registrada con timestamp

### Tickets Fallidos (Respaldo Automático)
Los tickets que no se pueden imprimir se guardan automáticamente en:
```
print_service\failed_tickets\
```
- **Se guardan como archivos JSON** con timestamp
- **Se pueden reimprimir** manualmente más tarde
- **No se pierde información** aunque falle la impresora

---

## 🎉 Resultado Final

### ✅ **LO QUE FUNCIONA AHORA:**

1. **Sistema robusto de 3 niveles** - Nunca falla completamente
2. **Impresión térmica automática** - Cuando esté disponible
3. **Fallbacks inteligentes** - Sin intervención manual
4. **Tickets profesionales** - Formato completo para restaurante
5. **Integración transparente** - Funciona desde el sistema de caja
6. **Logs detallados** - Para debugging y monitoreo
7. **Auto-recovery** - El sistema se recupera automáticamente

### 🔮 **FLUJO DE USUARIO:**

1. El usuario procesa un pago en caja
2. Se imprime **automáticamente** el mejor método disponible:
   - 🔥 **Impresora térmica** (silencioso, profesional)
   - 💻 **Impresora del sistema** (con notificación discreta)
   - 🖥️ **Consola del navegador** (con instrucciones claras)
3. **El usuario siempre obtiene su ticket** - sin errores

---

## 📞 Soporte

### Auto-diagnóstico
```bash
cd print_service/
python test_connection.py
```

### Información del Sistema
- **Puerto del servicio**: 3001
- **Endpoints disponibles**: `/health`, `/print`, `/test`
- **Formato de impresión**: ESC/POS para térmicas 80mm
- **Fallbacks**: Sistema + Consola
- **Compatibilidad**: Windows, Linux, macOS

---

**Creado por**: Sistema POS La Hidrocálida  
**Versión**: 1.0  
**Última actualización**: Enero 2025