from fastapi import FastAPI, Depends
from sqlalchemy import text
from app.db.session import get_db
from sqlalchemy.orm import Session

app = FastAPI(title="La Hidrocálida POS API")

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
            "result": test_value[0] if test_value else None
        }
    except Exception as e:
        return {
            "status": "error",
            "message": "Error al conectar con la base de datos",
            "error": str(e)
        }