"""
Servidor API para el servicio de impresión
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import threading
from datetime import datetime
from core.printer_manager import printer_manager
from core.print_queue import print_queue

app = Flask(__name__)
CORS(app)

@app.route('/health', methods=['GET'])
def health_check():
    """Verifica el estado del servicio de impresión"""
    return jsonify({
        "status": "ok",
        "service": "La Hidrocálida Print Service",
        "timestamp": datetime.now().isoformat(),
        "printer_status": "connected" if printer_manager.printer else "disconnected"
    })

@app.route('/print', methods=['POST'])
def print_ticket():
    """Endpoint para imprimir tickets"""
    try:
        # Obtener datos del ticket
        ticket_data = request.get_json()
        
        if not ticket_data:
            return jsonify({"error": "No se recibieron datos del ticket"}), 400
        
        # Agregar ticket a la cola de impresión
        print_queue.add_to_queue(ticket_data)
        
        # Procesar cola inmediatamente
        print_queue.process_queue(printer_manager)
        
        return jsonify({
            "status": "success",
            "message": "Ticket agregado a la cola de impresión",
            "ticket_id": ticket_data.get('numero_display', 'N/A')
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error al procesar ticket: {str(e)}"
        }), 500

@app.route('/printers', methods=['GET'])
def get_printers():
    """Obtiene la lista de impresoras disponibles"""
    try:
        printers = printer_manager.get_available_printers()
        return jsonify({
            "status": "success",
            "printers": list(printers.keys()) if printers else []
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error al obtener impresoras: {str(e)}"
        }), 500

@app.route('/test', methods=['POST'])
def test_print():
    """Endpoint para prueba de impresión"""
    try:
        # Datos de prueba
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
                }
            ],
            "total": 150.00
        }
        
        # Intentar imprimir ticket de prueba
        success = printer_manager.print_ticket(test_data)
        
        if success:
            return jsonify({
                "status": "success",
                "message": "Prueba de impresión exitosa"
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Prueba de impresión fallida"
            }), 500
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error en prueba de impresión: {str(e)}"
        }), 500

if __name__ == '__main__':
    print("🚀 Iniciando servicio de impresión La Hidrocálida...")
    print("📡 Servicio disponible en: http://localhost:3001")
    print("🔍 Health check: http://localhost:3001/health")
    print("[PRINT] Impresion: POST http://localhost:3001/print")
    print("[STOP] Presiona Ctrl+C para detener")
    
    app.run(host='localhost', port=3001, debug=False)