from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# 1. CREAR EL ENGINE (Motor de base de datos)
# El engine es como el "conductor" que maneja la conexión a PostgreSQL
engine = create_engine(
    settings.DATABASE_URL,  # URL de tu base de datos Neon
    echo=False,  # No loguear SQL: expone datos de clientes y ensucia logs en Railway
    pool_pre_ping=True,  # Verifica que la conexión esté viva antes de usarla
    pool_recycle=300,  # Renueva conexiones cada 5 minutos
)

# 2. CREAR LA CLASE BASE PARA MODELOS
# Base es la clase padre que usarán todos tus modelos (tablas)
Base = declarative_base()

# 3. CREAR EL SESSIONMAKER
# SessionLocal es una "fábrica" que crea sesiones de base de datos
SessionLocal = sessionmaker(
    autocommit=False,  # No guarda automáticamente, necesitas hacer commit
    autoflush=False,  # No envía cambios automáticamente a la BD
    bind=engine,  # Conecta con nuestro engine
)


# 4. FUNCIÓN PARA OBTENER UNA SESIÓN
def get_db():
    """
    Esta función crea una nueva sesión de base de datos.
    Se usa como dependencia en FastAPI.
    """
    db = SessionLocal()
    try:
        yield db  # Entrega la sesión
    finally:
        db.close()  # Siempre cierra la conexión al terminar
