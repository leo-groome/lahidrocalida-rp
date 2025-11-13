# 🖨️ **Instalación de Impresión Térmica - La Hidrocálida**

## 📋 **Instrucciones para el Local (PC de Caja)**

### ⚡ **Instalación Rápida (5 minutos)**

1. **📁 Copia la carpeta `print_service`** a la PC de caja
2. **🔌 Conecta la impresora térmica** vía USB
3. **⚙️ Ejecuta instalación:**
   - **Windows:** Doble clic en `install.bat`
   - **Linux/Mac:** `chmod +x install.sh && ./install.sh`
4. **🚀 Inicia el servicio:**
   - **Windows:** Doble clic en `start_print_service.bat`
   - **Linux/Mac:** `./start_print_service.sh`
5. **✅ Abre el navegador** con el sistema y ¡listo!

---

## 🎯 **Flujo Automático de Impresión**

### **Funcionamiento:**
1. **Mesero** toma pedido → Envía a cocina
2. **Cocina** prepara → Marca como "listo" 
3. **Mesero** entrega → Marca como "entregado"
4. **Caja** procesa pago → **¡Imprime automáticamente!**

### **Estrategia de Impresión (3 niveles):**
```
🥇 PRIORIDAD 1: Impresora térmica ESC/POS
    ↓ (si falla)
🥈 PRIORIDAD 2: Impresora del sistema (Ctrl+P)
    ↓ (si falla)  
🥉 PRIORIDAD 3: Consola del navegador (F12)
```

---

## 🔧 **Verificación de Funcionamiento**

### **1. Probar Servicio:**
- Abrir navegador: `http://localhost:3001/health`
- Debe mostrar: `{"status": "ok", "service": "La Hidrocálida Print Service"}`

### **2. Prueba de Impresión:**
- Ejecutar: `python test_ticket.py`
- Debe imprimir un ticket de prueba

### **3. Indicadores en el Sistema:**
- **🟢 Verde:** Impresora térmica conectada
- **🟡 Amarillo:** Usando impresora del sistema
- **🔴 Rojo:** Solo consola (problema con impresión)

---

## 🐛 **Solución de Problemas**

### **"Servicio no se inicia"**
```bash
# Verificar Python
python --version
# Debe mostrar Python 3.x

# Instalar dependencias manualmente
pip install flask flask-cors
```

### **"No encuentra la impresora"**
1. **Verificar conexión USB** - Cable conectado firmemente
2. **Instalar drivers** - Descargar del fabricante
3. **Verificar dispositivo:**
   - Windows: Debe aparecer en "Dispositivos e impresoras"
   - Linux: `lsusb` debe mostrar la impresora

### **"Error de permisos"**
```bash
# Linux: Dar permisos al dispositivo USB
sudo chmod 666 /dev/usb/lp0
# O agregar usuario al grupo lp
sudo usermod -a -G lp $USER
```

### **"Papel atorado"**
1. Apagar impresora
2. Abrir tapa y quitar papel atorado
3. Cerrar tapa y encender
4. Reiniciar servicio de impresión

---

## ⚙️ **Configuración Avanzada**

### **Cambiar Puerto del Servicio:**
Editar `print_server.py` línea final:
```python
app.run(host='0.0.0.0', port=3001, debug=False)
#                       ↑ cambiar aquí
```

### **Impresoras Soportadas:**
- **Epson:** TM-T20, TM-T88, TM-U220
- **Star:** TSP100, TSP143, TSP650
- **Bixolon:** SRP-350, SRP-275
- **Citizen:** CT-S310, CT-E351
- **Cualquier impresora** compatible con ESC/POS

### **Conexiones:**
- **USB:** `/dev/usb/lp0` (Linux), `PRN` (Windows)
- **Serie:** `/dev/ttyUSB0` (Linux), `COM1` (Windows)
- **Ethernet:** Modificar código para IP específica

---

## 📱 **Uso Diario**

### **Al Abrir el Local:**
1. **Encender PC de caja**
2. **Conectar impresora** (si no está siempre conectada)
3. **Ejecutar:** `start_print_service.bat` (o `.sh`)
4. **Abrir navegador** con el sistema
5. **Verificar** indicador verde 🟢 en vista de caja

### **Al Cerrar:**
- El servicio puede quedarse corriendo
- O cerrar con `Ctrl+C` en la ventana del servicio

### **Mantenimiento:**
- **Papel:** Cambiar cuando se agote
- **Limpieza:** Limpiar cabezal ocasionalmente
- **Actualización:** Reiniciar servicio si hay problemas

---

## 📞 **Soporte Técnico**

### **Información del Sistema:**
- **Servicio:** Puerto 3001
- **Logs:** Se muestran en ventana del servicio
- **Configuración:** Archivos en carpeta `print_service`

### **Contactos:**
- **Documentación técnica:** Ver `print_service/README.md`
- **Pruebas:** Ejecutar `test_ticket.py`
- **Problemas:** Revisar logs en ventana del servicio

---

**🎯 ¡El sistema está preparado para funcionar inmediatamente al llegar al local!**

**Desarrollado para Pozolería "La Hidrocálida"**  
**Sistema de impresión térmica - Enero 2025**