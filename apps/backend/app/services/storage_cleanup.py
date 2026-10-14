"""Outbox de borrados, con recuperación por rollback y exclusión entre workers."""

import asyncio
import logging
from datetime import timedelta

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import StorageBorrado
from app.services.storage import Storage, get_storage
from app.utils.timezone import get_mexico_now

logger = logging.getLogger(__name__)


def programar_borrado(db: Session, llave: str, *, demora: int = 0) -> StorageBorrado:
    """Registra limpieza en la transacción del llamador."""
    task = StorageBorrado(
        storage_key=llave, proximo_intento=get_mexico_now() + timedelta(seconds=demora)
    )
    db.add(task)
    return task


async def procesar_borrados(db: Session, storage: Storage) -> int:
    """Procesa un lote acotado; cada fila se bloquea hasta confirmar su resultado."""
    count = 0
    for _ in range(10):
        task = (
            db.query(StorageBorrado)
            .filter(StorageBorrado.proximo_intento <= get_mexico_now())
            .order_by(StorageBorrado.id)
            .with_for_update(skip_locked=True)
            .first()
        )
        if task is None:
            db.rollback()
            break
        try:
            await storage.borrar(task.storage_key)
        except Exception as exc:
            task.intentos += 1
            task.ultimo_error = type(exc).__name__
            task.proximo_intento = get_mexico_now() + timedelta(
                seconds=min(3600, 30 * 2 ** min(task.intentos, 7))
            )
            logger.warning(
                "Limpieza de storage pendiente: tarea=%s intento=%s", task.id, task.intentos
            )
        else:
            db.delete(task)
            count += 1
        db.commit()
    return count


async def cleanup_consumer(stop: asyncio.Event) -> None:
    """Reintenta sin depender de una petición HTTP ni perder tareas al reiniciar."""
    while not stop.is_set():
        try:
            with SessionLocal() as db:
                # No inicializar R2/local hasta que exista trabajo pendiente.
                if db.query(StorageBorrado.id).first() is not None:
                    await procesar_borrados(db, get_storage())
        except Exception:
            logger.exception("No se pudo procesar la limpieza de storage")
        try:
            await asyncio.wait_for(stop.wait(), timeout=30)
        except asyncio.TimeoutError:
            pass
