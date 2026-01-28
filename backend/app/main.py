from app import websocket_routes
from app.db.session import engine, get_db
from app.models import Base
from app.routers import (
    admin,
    auth,
    gastos,
    pedidos,
    products,
    propinas,
    reportes,
    turnos,
    users,
)
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

# Crear todas las tablas
Base.metadata.create_all(bind=engine)

app = FastAPI(title="La Hidrocálida POS API")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Para servidor de desarrollo Vite local
        "http://192.168.0.10:5173",  # URL del frontend actual
        "https://lahidrocalida.vercel.app",
        # Agregar URLs de producción más tarde, ej. "https://yourapp.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(products.router)
app.include_router(pedidos.router)
app.include_router(gastos.router)
app.include_router(admin.router)
app.include_router(propinas.router)
app.include_router(reportes.router)
app.include_router(turnos.router)
app.include_router(websocket_routes.router)


@app.get("/")
def root():
    return {"message": "La Hidrocálida POS API"}


@app.get("/health/database")
def check_database_connection(db: Session = Depends(get_db)):
    """
    Endpoint para verificar la conexión a la base de datos.
    Ejecuta una consulta simple para confirmar que todo funciona.
    """
    try:
        # Ejecutar una consulta simple
        result = db.execute(text("SELECT 5 as test"))
        test_value = result.fetchone()

        return {
            "status": "success",
            "message": "Conexión a la base de datos exitosa",
            "database": "PostgreSQL (Neon)",
            "test_query": "SELECT 5",
            "result": test_value[0] if test_value else None,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": "Error al conectar con la base de datos",
            "error": str(e),
        }
