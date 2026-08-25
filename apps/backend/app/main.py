import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import events, websocket_routes
from app.core.config import settings
from app.db.session import get_db
from app.routers import (
    admin,
    asistencia,
    auth,
    gastos,
    pedidos,
    products,
    propinas,
    reportes,
    turnos,
    users,
)
from app.websocket_manager import websocket_manager

# Sin esto, los logger.* de los módulos propios no salen en los logs del host
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # asyncio.create_task requiere un loop corriendo: por eso vive aquí y no en
    # el __init__ de WebSocketManager (ese side-effect de import truena en
    # tests, que importan app.main sin loop activo).
    stop_event = asyncio.Event()
    tasks = [
        asyncio.create_task(events.event_consumer(stop_event)),
        asyncio.create_task(websocket_manager._cleanup_zombies()),
    ]
    try:
        yield
    finally:
        stop_event.set()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


app = FastAPI(title="La Hidrocálida POS API", lifespan=lifespan)

# CORS: orígenes declarados en CORS_ORIGINS (env), nunca hardcodeados en el código.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(auth.router)
app.include_router(asistencia.router)
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


@app.get("/health")
def health():
    """Healthcheck simple, sin tocar la DB. Lo usan Docker y Railway."""
    return {"status": "ok"}


@app.get("/health/database")
def check_database_connection(db: Session = Depends(get_db)):
    """Verifica la conexión a la base de datos sin exponer host ni credenciales."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception:
        logging.getLogger(__name__).exception("Fallo de conexión a la base de datos")
        return {"status": "error"}
