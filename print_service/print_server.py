#!/usr/bin/env python3
"""
Servicio de impresión local para La Hidrocálida
Escucha en puerto 3001 y maneja impresora térmica ESC/POS
"""

import json
import sys
import traceback
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Permitir requests desde el frontend

def generate_escpos_commands(ticket_data):
    """Genera comandos ESC/POS optimizados para impresora térmica 80mm (48 chars)"""
    
    # Comandos ESC/POS para impresora térmica
    ESC = '\x1b'
    GS = '\x1d'
    INIT = ESC + '@'  # Inicializar impresora
    BOLD_ON = ESC + 'E1'  # Negrita ON
    BOLD_OFF = ESC + 'E0'  # Negrita OFF
    CENTER = ESC + 'a1'  # Centrar texto
    LEFT = ESC + 'a0'  # Alinear izquierda
    RIGHT = ESC + 'a2'  # Alinear derecha
    DOUBLE_WIDTH = GS + '!01'  # Doble ancho
    DOUBLE_HEIGHT = GS + '!10'  # Doble altura
    DOUBLE_BOTH = GS + '!11'  # Doble ancho y altura
    NORMAL_SIZE = GS + '!00'  # Tamaño normal
    SMALL_FONT = ESC + 'M1'  # Fuente pequeña
    NORMAL_FONT = ESC + 'M0'  # Fuente normal
    CUT = GS + 'V1'  # Cortar papel
    LINE_FEED = '\n'
    
    # Líneas decorativas para 48 chars
    DOUBLE_LINE = '═' * 48
    SINGLE_LINE = '─' * 48
    DOT_LINE = '·' * 48
    STAR_LINE = '★' + '─' * 46 + '★'
    
    # Construir ticket para restaurante (48 chars width)
    commands = []
    commands.append(INIT)
    
    # ENCABEZADO DEL RESTAURANTE
    commands.append(LINE_FEED)
    commands.append(CENTER)
    commands.append(STAR_LINE + LINE_FEED)
    commands.append(LINE_FEED)
    commands.append(DOUBLE_BOTH + BOLD_ON + "LA HIDROCÁLIDA" + BOLD_OFF + NORMAL_SIZE + LINE_FEED)
    commands.append(LINE_FEED)
    commands.append(BOLD_ON + "☾ POZOLERÍA TRADICIONAL ☽" + BOLD_OFF + LINE_FEED)
    commands.append("Auténticos sabores mexicanos" + LINE_FEED)
    commands.append(LINE_FEED)
    commands.append(STAR_LINE + LINE_FEED)
    commands.append(LINE_FEED)
    
    # INFORMACIÓN DEL PEDIDO
    commands.append(LEFT)
    commands.append(BOLD_ON + "ORDEN #" + str(ticket_data.get('numero_display', 'N/A')).zfill(3) + BOLD_OFF)
    
    # Fecha en la misma línea
    fecha = datetime.now().strftime('%d/%m/%Y')
    hora = datetime.now().strftime('%H:%M')
    fecha_line = f"ORDEN #{str(ticket_data.get('numero_display', 'N/A')).zfill(3)}"
    fecha_right = f"{fecha} {hora}"
    spaces = 48 - len(fecha_line) - len(fecha_right)
    commands.append(LEFT)
    commands.append(BOLD_ON + fecha_line + BOLD_OFF + " " * spaces + fecha_right + LINE_FEED)
    
    commands.append(SINGLE_LINE + LINE_FEED)
    
    # Mesa y Cliente con mejor spacing
    if ticket_data.get('mesa'):
        mesa_line = f"Mesa: {ticket_data['mesa']}"
        commands.append(mesa_line + LINE_FEED)
    
    if ticket_data.get('nombre_cliente'):
        cliente_line = f"Cliente: {ticket_data['nombre_cliente']}"
        commands.append(cliente_line + LINE_FEED)
    
    commands.append(SINGLE_LINE + LINE_FEED)
    commands.append(LINE_FEED)
    
    # DETALLES DEL PEDIDO
    commands.append(CENTER + BOLD_ON + "~ DETALLES DEL PEDIDO ~" + BOLD_OFF + LINE_FEED)
    commands.append(LEFT)
    commands.append(DOT_LINE + LINE_FEED)
    commands.append(LINE_FEED)
    
    # Productos con formato mejorado
    for i, articulo in enumerate(ticket_data.get('articulos', []), 1):
        cantidad = articulo.get('cantidad', 1)
        nombre = articulo.get('nombre', 'Producto')
        precio_unitario = float(articulo.get('precio', 0))
        precio_total = cantidad * precio_unitario
        
        # Línea principal del producto
        commands.append(BOLD_ON + f"{i}. {nombre}" + BOLD_OFF + LINE_FEED)
        
        # Cantidad y precios
        cant_precio = f"   {cantidad} x ${precio_unitario:.2f}"
        total_str = f"${precio_total:.2f}"
        spaces = 48 - len(cant_precio) - len(total_str)
        commands.append(cant_precio + " " * spaces + total_str + LINE_FEED)
        
        # Modificaciones en línea separada
        if articulo.get('modificaciones'):
            mod_text = articulo['modificaciones']
            # Dividir modificaciones largas en líneas de 44 chars
            lines = []
            while len(mod_text) > 44:
                cut_pos = mod_text.rfind(' ', 0, 44)
                if cut_pos == -1:
                    cut_pos = 44
                lines.append(mod_text[:cut_pos])
                mod_text = mod_text[cut_pos:].strip()
            if mod_text:
                lines.append(mod_text)
            
            for line in lines:
                commands.append(f"   > {line}" + LINE_FEED)
        
        commands.append(LINE_FEED)  # Espacio entre productos
    
    # TOTALES
    commands.append(DOT_LINE + LINE_FEED)
    commands.append(LINE_FEED)
    
    total = float(ticket_data.get('total', 0))
    
    # Total destacado y centrado
    commands.append(CENTER)
    commands.append(DOUBLE_LINE + LINE_FEED)
    commands.append(DOUBLE_WIDTH + BOLD_ON + f"TOTAL: ${total:.2f}" + BOLD_OFF + NORMAL_SIZE + LINE_FEED)
    commands.append(DOUBLE_LINE + LINE_FEED)
    commands.append(LINE_FEED)
    
    # MENSAJE DE AGRADECIMIENTO
    commands.append("¡MUCHAS GRACIAS!" + LINE_FEED)
    commands.append("Por elegirnos para disfrutar" + LINE_FEED)
    commands.append("de nuestros auténticos pozoles" + LINE_FEED)
    commands.append(LINE_FEED)
    
    # INFORMACIÓN DEL RESTAURANTE
    commands.append(LEFT)
    commands.append(SMALL_FONT)
    commands.append("♨ Especialidades de la casa:" + LINE_FEED)
    commands.append("  • Pozole Rojo Tradicional" + LINE_FEED)
    commands.append("  • Pozole Blanco Casero" + LINE_FEED)
    commands.append("  • Tostadas y Garnachas" + LINE_FEED)
    commands.append(NORMAL_FONT)
    commands.append(LINE_FEED)
    
    # REDES SOCIALES Y CONTACTO
    commands.append(CENTER)
    commands.append("☆ Síguenos en redes sociales ☆" + LINE_FEED)
    commands.append("@lahidrocalida_oficial" + LINE_FEED)
    commands.append(LINE_FEED)
    commands.append("¿Te gustó nuestro servicio?" + LINE_FEED)
    commands.append("Déjanos tu reseña ⭐⭐⭐⭐⭐" + LINE_FEED)
    commands.append(LINE_FEED)
    
    # PIE DE PÁGINA
    commands.append(SMALL_FONT)
    commands.append("Sistema POS v1.0 - La Hidrocálida" + LINE_FEED)
    commands.append(f"Impreso: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}" + LINE_FEED)
    commands.append(NORMAL_FONT)
    commands.append(LINE_FEED)
    commands.append(DOT_LINE + LINE_FEED)
    commands.append(LINE_FEED)
    commands.append(LINE_FEED)
    commands.append(LINE_FEED)
    
    # Cortar papel
    commands.append(CUT)
    
    return ''.join(commands)

def print_to_device(data, device_path='/dev/usb/lp0'):
    """Envía datos a la impresora"""
    try:
        # En Windows, usar 'PRN' o el nombre del puerto
        # En Linux/Mac, usar /dev/usb/lp0 o similar
        
        # Detectar sistema operativo
        import platform
        system = platform.system().lower()
        
        if system == 'windows':
            # Windows - intentar diferentes puertos
            possible_ports = ['PRN', 'LPT1', 'COM1']
            for port in possible_ports:
                try:
                    with open(port, 'wb') as printer:
                        printer.write(data.encode('cp437', errors='replace'))
                    logger.info(f"✅ Impreso exitosamente en {port}")
                    return True
                except Exception as e:
                    logger.warning(f"❌ No se pudo imprimir en {port}: {e}")
                    continue
        else:
            # Linux/Mac - usar modo binario para comandos ESC/POS
            possible_devices = ['/dev/usb/lp0', '/dev/ttyUSB0', '/dev/ttyACM0', '/dev/lp0']
            for device in possible_devices:
                try:
                    with open(device, 'wb') as printer:
                        printer.write(data.encode('cp437', errors='replace'))
                    logger.info(f"✅ Impreso exitosamente en {device}")
                    return True
                except Exception as e:
                    logger.warning(f"❌ No se pudo imprimir en {device}: {e}")
                    continue
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Error general de impresión: {e}")
        return False

@app.route('/health', methods=['GET'])
def health_check():
    """Health check del servicio"""
    return jsonify({
        "status": "ok",
        "service": "La Hidrocálida Print Service",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/test-format', methods=['POST'])
def test_format():
    """Endpoint de test para verificar comandos ESC/POS"""
    try:
        logger.info("🧪 Ejecutando test de formato ESC/POS...")
        
        # Ticket de prueba simple
        test_data = {
            "numero_display": "TEST",
            "mesa": "99",
            "nombre_cliente": "Test Format",
            "articulos": [
                {
                    "cantidad": 1,
                    "nombre": "Pozole Test",
                    "precio": 50.00,
                    "modificaciones": "Sin cebolla, extra chile"
                }
            ],
            "total": 50.00
        }
        
        # Generar comandos
        escpos_data = generate_escpos_commands(test_data)
        
        # Log detallado
        logger.info(f"📏 Test - Longitud: {len(escpos_data)} chars")
        
        # Verificar comandos específicos
        commands_check = {
            "INIT \\x1b@": '\x1b@' in escpos_data,
            "BOLD_ON \\x1bE1": '\x1bE1' in escpos_data,
            "BOLD_OFF \\x1bE0": '\x1bE0' in escpos_data,
            "CENTER \\x1ba1": '\x1ba1' in escpos_data,
            "LEFT \\x1ba0": '\x1ba0' in escpos_data,
            "DOUBLE_BOTH \\x1d!11": '\x1d!11' in escpos_data,
            "NORMAL_SIZE \\x1d!00": '\x1d!00' in escpos_data,
            "CUT \\x1dV1": '\x1dV1' in escpos_data,
        }
        
        for cmd, found in commands_check.items():
            status = "✅" if found else "❌"
            logger.info(f"   {status} {cmd}: {'ENCONTRADO' if found else 'FALTANTE'}")
        
        # Intentar impresión de test
        success = print_to_device(escpos_data)
        
        return jsonify({
            "status": "success" if success else "error",
            "message": "Test de formato completado",
            "commands_found": sum(commands_check.values()),
            "commands_total": len(commands_check),
            "print_success": success,
            "data_length": len(escpos_data),
            "commands_detail": commands_check
        })
        
    except Exception as e:
        logger.error(f"❌ Error en test de formato: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error en test: {str(e)}"
        }), 500

@app.route('/print', methods=['POST'])
def print_ticket():
    """Endpoint principal para imprimir tickets"""
    try:
        # Obtener datos del ticket
        ticket_data = request.get_json()
        
        if not ticket_data:
            return jsonify({"error": "No se recibieron datos del ticket"}), 400
        
        # Validaciones básicas
        required_fields = ['numero_display', 'total']
        missing_fields = [field for field in required_fields if not ticket_data.get(field)]
        if missing_fields:
            return jsonify({
                "error": f"Campos requeridos faltantes: {', '.join(missing_fields)}"
            }), 400
        
        logger.info(f"📄 Procesando impresión del pedido #{ticket_data.get('numero_display', 'N/A')}")
        
        # Generar comandos ESC/POS
        escpos_data = generate_escpos_commands(ticket_data)
        
        # Log del ticket generado para debugging
        logger.info(f"📏 Longitud del ticket: {len(escpos_data)} caracteres")
        logger.info("🔍 Comandos ESC/POS detectados:")
        
        # Verificar comandos ESC/POS en el ticket
        escpos_commands_found = []
        if '\x1b@' in escpos_data:
            escpos_commands_found.append("INIT")
        if '\x1bE1' in escpos_data:
            escpos_commands_found.append("BOLD_ON")
        if '\x1bE0' in escpos_data:
            escpos_commands_found.append("BOLD_OFF")
        if '\x1ba1' in escpos_data:
            escpos_commands_found.append("CENTER")
        if '\x1ba0' in escpos_data:
            escpos_commands_found.append("LEFT")
        if '\x1d!11' in escpos_data:
            escpos_commands_found.append("DOUBLE_BOTH")
        if '\x1dV1' in escpos_data:
            escpos_commands_found.append("CUT")
            
        logger.info(f"   {', '.join(escpos_commands_found) if escpos_commands_found else 'NINGUNO DETECTADO'}")
        
        # Mostrar primeras líneas del ticket (solo texto visible)
        visible_lines = escpos_data.replace('\x1b', '[ESC]').replace('\x1d', '[GS]').split('\n')[:10]
        logger.info("📝 Primeras líneas del ticket:")
        for i, line in enumerate(visible_lines, 1):
            if line.strip():
                logger.info(f"   {i}: {line[:50]}")
        
        if app.debug:
            logger.debug("🔧 Ticket completo (con comandos de control):")
            logger.debug(repr(escpos_data))
        
        # Intentar imprimir
        success = print_to_device(escpos_data)
        
        if success:
            logger.info("🖨️ Ticket impreso exitosamente en impresora térmica")
            return jsonify({
                "status": "success",
                "message": "Ticket impreso exitosamente",
                "method": "thermal_printer",
                "pedido": ticket_data.get('numero_display', 'N/A'),
                "timestamp": datetime.now().isoformat()
            })
        else:
            # Si falla la impresión, log detallado pero respuesta simple
            logger.warning("⚠️ Impresora térmica no disponible - datos guardados para reintento")
            
            # Guardar ticket para reintento posterior (opcional)
            save_failed_ticket(ticket_data)
            
            return jsonify({
                "status": "error", 
                "message": "Impresora térmica no disponible",
                "fallback_required": True,
                "pedido": ticket_data.get('numero_display', 'N/A')
            }), 503  # Service Unavailable
            
    except Exception as e:
        logger.error(f"❌ Error en impresión: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return jsonify({
            "status": "error",
            "message": "Error interno del servidor de impresión",
            "fallback_required": True,
            "details": str(e) if app.debug else "Error interno"
        }), 500

def save_failed_ticket(ticket_data):
    """Guarda tickets fallidos para reintento posterior"""
    try:
        import os
        failed_dir = "failed_tickets"
        if not os.path.exists(failed_dir):
            os.makedirs(failed_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{failed_dir}/ticket_{ticket_data.get('numero_display', 'unknown')}_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(ticket_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 Ticket guardado para reintento: {filename}")
    except Exception as e:
        logger.warning(f"No se pudo guardar ticket fallido: {e}")

@app.route('/test', methods=['POST'])
def test_print():
    """Endpoint para imprimir un ticket de prueba"""
    test_data = {
        "numero_display": "999",
        "mesa": "TEST",
        "nombre_cliente": "Prueba del Sistema",
        "articulos": [
            {
                "cantidad": 1,
                "nombre": "Pozole Rojo Grande",
                "precio": 120.00,
                "modificaciones": "Prueba de impresión - Extra picante, sin orégano"
            },
            {
                "cantidad": 1,
                "nombre": "Agua de Horchata",
                "precio": 30.00,
                "modificaciones": "Sin canela"
            },
            {
                "cantidad": 1,
                "nombre": "Orden de Tostadas",
                "precio": 45.00,
                "modificaciones": None
            }
        ],
        "total": 195.00
    }
    
    # Reutilizar lógica de impresión
    request.json = test_data
    return print_ticket()

if __name__ == '__main__':
    print("🚀 Iniciando servicio de impresión La Hidrocálida...")
    print("📡 Servicio disponible en: http://localhost:3001")
    print("🔍 Health check: http://localhost:3001/health")
    print("🧪 Test de impresión: POST http://localhost:3001/test")
    print("🖨️ Impresión: POST http://localhost:3001/print")
    print("⏹️  Presiona Ctrl+C para detener")
    
    try:
        app.run(host='0.0.0.0', port=3001, debug=False)
    except KeyboardInterrupt:
        print("\n👋 Servicio de impresión detenido")
        sys.exit(0)