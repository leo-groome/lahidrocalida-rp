
import os
from sqlalchemy import create_engine, func, and_
from sqlalchemy.orm import sessionmaker
from datetime import datetime, date
import dotenv

# Load environment variables
dotenv.load_dotenv("backend/.env")
DATABASE_URL = os.getenv("DATABASE_URL")

# Import models
import sys
sys.path.append(os.path.join(os.getcwd(), "backend"))
from app.models import Pedido, Usuario

def debug_query():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    start_date = date(2026, 2, 1)
    end_date = date(2026, 2, 28)
    sucursal_id = 1
    
    ventas_filters = [
        func.date(Pedido.fecha_creacion) >= start_date,
        func.date(Pedido.fecha_creacion) <= end_date,
        Pedido.estado == "pagado",
        Pedido.sucursal_id == sucursal_id
    ]
    
    query = db.query(
        func.date(Pedido.fecha_creacion).label('fecha'),
        func.sum(Pedido.total).label('total_ventas'),
        func.count(Pedido.id).label('cantidad_pedidos')
    ).filter(and_(*ventas_filters)).group_by(func.date(Pedido.fecha_creacion))
    
    print(f"SQL GENERATED:\n{query}")
    
    results = query.all()
    print(f"Number of days with records: {len(results)}")
    
    total_sales = sum(r.total_ventas for r in results)
    print(f"Total Sales: {total_sales}")
    
    if results:
        print(f"Sample result: {results[0]}")
    
    # Check if any orders exist at all for that sucursal and date range but different state
    all_count = db.query(func.count(Pedido.id)).filter(
        and_(
            func.date(Pedido.fecha_creacion) >= start_date,
            func.date(Pedido.fecha_creacion) <= end_date,
            Pedido.sucursal_id == sucursal_id
        )
    ).scalar()
    print(f"Total count (any state): {all_count}")
    
    # Check states
    states = db.query(Pedido.estado, func.count(Pedido.id)).filter(
        and_(
            func.date(Pedido.fecha_creacion) >= start_date,
            func.date(Pedido.fecha_creacion) <= end_date,
            Pedido.sucursal_id == sucursal_id
        )
    ).group_by(Pedido.estado).all()
    print(f"States found: {states}")

if __name__ == "__main__":
    debug_query()
