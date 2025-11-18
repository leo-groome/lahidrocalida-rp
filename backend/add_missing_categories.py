#!/usr/bin/env python3
"""
Script para agregar las categorías faltantes de platillos en la base de datos.
Ejecutar desde el directorio backend/
"""

from app.db.session import SessionLocal
from app.models import Platillo

def update_categories():
    db = SessionLocal()
    try:
        # Mapeo de categorías viejas a nuevas
        category_mapping = {
            'pozole': 'pozoles',
            'antojitos': 'flautas'  # Cambiar antojitos por flautas como ejemplo
        }
        
        # Actualizar categorías existentes
        for old_cat, new_cat in category_mapping.items():
            platillos = db.query(Platillo).filter(Platillo.categoria == old_cat).all()
            for platillo in platillos:
                platillo.categoria = new_cat
                print(f"Actualizado: {platillo.nombre} - {old_cat} -> {new_cat}")
        
        # Ejemplos de platillos para las nuevas categorías
        nuevos_platillos = [
            # Postres
            {"nombre": "Flan Napolitano", "categoria": "postres", "precio": 45.00, "descripcion": "Flan casero con caramelo"},
            {"nombre": "Gelatina de Leche", "categoria": "postres", "precio": 35.00, "descripcion": "Gelatina cremosa de leche"},
            
            # Bebidas
            {"nombre": "Agua de Horchata", "categoria": "bebidas", "precio": 25.00, "descripcion": "Agua fresca de horchata"},
            {"nombre": "Refresco", "categoria": "bebidas", "precio": 30.00, "descripcion": "Refresco de 355ml"},
            {"nombre": "Agua Natural", "categoria": "bebidas", "precio": 20.00, "descripcion": "Agua natural 500ml"},
            
            # Extras
            {"nombre": "Tostadas Extra", "categoria": "extras", "precio": 15.00, "descripcion": "Porción extra de tostadas"},
            {"nombre": "Salsa Verde", "categoria": "extras", "precio": 10.00, "descripcion": "Porción extra de salsa verde"},
            {"nombre": "Crema", "categoria": "extras", "precio": 12.00, "descripcion": "Porción extra de crema"},
        ]
        
        # Verificar si ya existen antes de crear
        for platillo_data in nuevos_platillos:
            existing = db.query(Platillo).filter(Platillo.nombre == platillo_data["nombre"]).first()
            if not existing:
                nuevo_platillo = Platillo(
                    nombre=platillo_data["nombre"],
                    categoria=platillo_data["categoria"],
                    precio=platillo_data["precio"],
                    descripcion=platillo_data["descripcion"],
                    kds_name=platillo_data["nombre"][:15],  # Nombre corto para KDS
                    estado="disponible"
                )
                db.add(nuevo_platillo)
                print(f"Agregado: {platillo_data['nombre']} - {platillo_data['categoria']}")
            else:
                print(f"Ya existe: {platillo_data['nombre']}")
        
        db.commit()
        print("\n✅ Categorías actualizadas exitosamente!")
        
        # Mostrar resumen
        categorias = db.query(Platillo.categoria).distinct().all()
        print("\n📋 Categorías disponibles:")
        for cat in categorias:
            count = db.query(Platillo).filter(Platillo.categoria == cat[0]).count()
            print(f"  - {cat[0]}: {count} platillos")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Actualizando categorías de platillos...")
    update_categories()