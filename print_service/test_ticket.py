#!/usr/bin/env python3
"""
Script para probar la impresión manualmente
"""

import requests
import json

# Datos de prueba realistas para restaurante
test_ticket = {
    "numero_display": "047",
    "mesa": "15",
    "nombre_cliente": "Familia Rodríguez",
    "articulos": [
        {
            "cantidad": 2,
            "nombre": "Pozole Rojo Grande",
            "precio": 120.00,
            "modificaciones": "Extra picante, sin orégano, cebolla extra, limón aparte"
        },
        {
            "cantidad": 1,
            "nombre": "Pozole Blanco Mediano",
            "precio": 95.00,
            "modificaciones": "Sin chile piquín"
        },
        {
            "cantidad": 1,
            "nombre": "Pozole Verde Chico",
            "precio": 85.00,
            "modificaciones": None
        },
        {
            "cantidad": 4,
            "nombre": "Agua de Horchata",
            "precio": 30.00,
            "modificaciones": "Sin canela"
        },
        {
            "cantidad": 1,
            "nombre": "Orden de Tostadas",
            "precio": 45.00,
            "modificaciones": "Con queso extra y crema"
        }
    ],
    "total": 485.00
}

def test_service():
    """Probar el servicio de impresión"""
    try:
        # Verificar que el servicio esté corriendo
        response = requests.get("http://localhost:3001/health", timeout=5)
        if response.status_code == 200:
            print("✅ Servicio de impresión disponible")
            print(f"📡 Respuesta: {response.json()}")
        else:
            print("❌ Servicio no responde correctamente")
            return False
            
        # Probar impresión
        print("\n🖨️ Enviando ticket de prueba...")
        response = requests.post(
            "http://localhost:3001/print",
            json=test_ticket,
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ Ticket enviado exitosamente")
            print(f"📄 Respuesta: {response.json()}")
            return True
        else:
            print(f"❌ Error en impresión: {response.status_code}")
            print(f"📄 Error: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ No se puede conectar al servicio")
        print("🔧 Asegúrate de que el servicio esté ejecutándose:")
        print("   Windows: start_print_service.bat")
        print("   Linux/Mac: ./start_print_service.sh")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Probando servicio de impresión...")
    print("=" * 40)
    
    success = test_service()
    
    print("=" * 40)
    if success:
        print("✅ ¡Prueba completada exitosamente!")
    else:
        print("❌ Prueba fallida. Revisar configuración.")