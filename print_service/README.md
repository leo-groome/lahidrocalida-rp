# 🖨️ Servicio de Impresión - La Hidrocálida

## 📋 Instrucciones de Instalación en la PC de Caja

### 🔧 **Instalación Automática**

**Windows:**
1. Copia la carpeta `print_service` a la PC de caja
2. Haz doble clic en `install.bat`
3. ¡Listo!

**Linux/Mac:**
1. Copia la carpeta `print_service` a la PC de caja
2. Abre terminal en la carpeta
3. Ejecuta: `chmod +x install.sh && ./install.sh`
4. ¡Listo!

### 🚀 **Uso Diario**

**Para iniciar el servicio cada día:**
- **Windows:** Doble clic en `start_print_service.bat`
- **Linux/Mac:** Ejecuta `./start_print_service.sh`

### 🔌 **Conexión de Impresora**

**Impresoras térmicas compatibles:**
- Epson TM-T20, TM-T88
- Bixolon SRP-350
- Star TSP100
- Cualquier impresora ESC/POS

**Conexiones soportadas:**
- USB (recomendado)
- Serie/COM
- Paralelo/LPT

### ✅ **Verificación de Funcionamiento**

1. **Iniciar servicio:** Ejecutar archivo de inicio
2. **Verificar estado:** Abrir `http://localhost:3001/health`
3. **Prueba de impresión:** Hacer POST a `http://localhost:3001/test`

### 🐛 **Resolución de Problemas**

**"No se puede conectar al servicio"**
- Verificar que el servicio esté ejecutándose
- Revisar puerto 3001 disponible

**"No se encuentra la impresora"**
- Verificar conexión USB/Serie
- Instalar drivers de la impresora
- Revisar permisos de acceso al dispositivo

**"Error de impresión"**
- Verificar papel en la impresora
- Revisar que no esté atorada
- Reiniciar impresora y servicio

### 🏗️ **Arquitectura**

```
[Frontend Browser] --HTTP--> [localhost:3001] --ESC/POS--> [Impresora Térmica]
```

**Flujo:**
1. Usuario procesa pago en navegador
2. Frontend detecta servicio local
3. Envía datos del ticket vía HTTP
4. Servicio genera comandos ESC/POS
5. Impresora térmica imprime ticket

### 📱 **Fallbacks Automáticos**

Si el servicio no está disponible:
1. **Fallback 1:** `window.print()` del navegador
2. **Fallback 2:** Impresión en consola (actual)

### 🔧 **Configuración Avanzada**

**Cambiar puerto del servicio:**
Editar `print_server.py` línea final:
```python
app.run(host='0.0.0.0', port=NUEVO_PUERTO, debug=False)
```

**Configurar dispositivo específico:**
Editar función `print_to_device()` con la ruta correcta de tu impresora.

---

**Desarrollado para Pozolería "La Hidrocálida"**
**Servicio de impresión local - Enero 2025**