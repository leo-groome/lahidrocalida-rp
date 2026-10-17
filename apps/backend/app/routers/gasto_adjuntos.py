"""Fotos de tickets de gastos: subir, listar, ver y borrar.

Reglas de seguridad:
- El tipo se detecta por magic bytes, no por extensión ni Content-Type.
- Tope de tamaño, leído en chunks (no se carga un archivo gigante en memoria).
- Llave de storage generada por el servidor.
- Aislamiento por sucursal estricto para TODOS los roles: las fotos de tickets
  contienen datos del negocio, así que ni un administrador de otra sucursal
  accede.
- El archivo se sirve solo por este endpoint autenticado (bucket privado).
"""

import asyncio
import hashlib
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models import Gasto, GastoAdjunto, Usuario
from app.schemas import AdjuntoResponse
from app.services.imagenes import normalizar_imagen
from app.services.storage import (
    MAX_ADJUNTO_BYTES,
    AdjuntoInvalido,
    ObjetoNoEncontrado,
    Storage,
    detectar_tipo,
    generar_llave,
    get_storage,
)
from app.services.storage_cleanup import programar_borrado

router = APIRouter(prefix="/gastos", tags=["gastos"])

MAX_ADJUNTOS_POR_GASTO = 5
_CHUNK = 64 * 1024

_roles_gastos = require_roles("administrador", "compras", "cajero")


def _gasto_de_mi_sucursal(
    db: Session, gasto_id: int, user: Usuario, *, bloquear: bool = False
) -> Gasto:
    query = db.query(Gasto).filter(Gasto.id == gasto_id)
    if bloquear:
        query = query.with_for_update().populate_existing()
    gasto = query.first()
    # 404 (no 403) cuando es de otra sucursal: no revelar que el gasto existe.
    if gasto is None or gasto.sucursal_id != user.sucursal_id:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    return gasto


def _adjunto_de_mi_sucursal(db: Session, gasto_id: int, adjunto_id: int, user: Usuario):
    adjunto = (
        db.query(GastoAdjunto)
        .filter(
            GastoAdjunto.id == adjunto_id,
            GastoAdjunto.gasto_id == gasto_id,
            GastoAdjunto.sucursal_id == user.sucursal_id,
        )
        .first()
    )
    if adjunto is None:
        raise HTTPException(status_code=404, detail="Adjunto no encontrado")
    return adjunto


async def _leer_limitado(archivo: UploadFile) -> bytes:
    partes: list[bytes] = []
    total = 0
    while chunk := await archivo.read(_CHUNK):
        total += len(chunk)
        if total > MAX_ADJUNTO_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"La imagen supera {MAX_ADJUNTO_BYTES // (1024 * 1024)} MB",
            )
        partes.append(chunk)
    return b"".join(partes)


@router.post(
    "/{gasto_id}/adjuntos",
    response_model=AdjuntoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def subir_adjunto(
    gasto_id: int,
    archivo: UploadFile,
    client_request_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_roles_gastos),
    storage: Storage = Depends(get_storage),
):
    # Registrar el posible huérfano ANTES de escribir en storage. Una caída
    # entre put y commit deja una tarea durable para reconciliarlo.
    _gasto_de_mi_sucursal(db, gasto_id, current_user)
    datos = await _leer_limitado(archivo)
    if not datos:
        raise HTTPException(status_code=400, detail="Archivo vacío")
    fingerprint = hashlib.sha256(datos).hexdigest()
    try:
        detectar_tipo(datos[:16])
        datos = await asyncio.to_thread(normalizar_imagen, datos)
    except AdjuntoInvalido as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    content_type = "image/webp"
    llave = generar_llave(f"gastos/{current_user.sucursal_id}", content_type)
    cleanup = programar_borrado(db, llave, demora=3600)
    db.commit()
    gasto = _gasto_de_mi_sucursal(db, gasto_id, current_user, bloquear=True)
    request_id = str(client_request_id) if client_request_id else None
    if request_id:
        existing = (
            db.query(GastoAdjunto)
            .filter_by(gasto_id=gasto.id, client_request_id=request_id)
            .first()
        )
        if existing:
            db.delete(cleanup)
            db.commit()
            if existing.payload_hash != fingerprint:
                raise HTTPException(
                    status_code=409, detail="La foto ya se envió con otro contenido"
                )
            return existing
    if db.query(GastoAdjunto).filter_by(gasto_id=gasto.id).count() >= MAX_ADJUNTOS_POR_GASTO:
        db.delete(cleanup)
        db.commit()
        raise HTTPException(
            status_code=400, detail=f"Máximo {MAX_ADJUNTOS_POR_GASTO} fotos por gasto"
        )
    await asyncio.wait_for(storage.guardar(llave, datos, content_type), timeout=60)
    adjunto = GastoAdjunto(
        gasto_id=gasto.id,
        sucursal_id=gasto.sucursal_id,
        storage_key=llave,
        content_type=content_type,
        size=len(datos),
        subido_por_id=current_user.id,
        client_request_id=request_id,
        payload_hash=fingerprint,
    )
    db.add(adjunto)
    db.delete(cleanup)
    try:
        db.commit()
    except Exception:
        db.rollback()  # La tarea confirmada antes del put permanece pendiente.
        raise
    db.refresh(adjunto)
    return adjunto


@router.get("/{gasto_id}/adjuntos", response_model=List[AdjuntoResponse])
def listar_adjuntos(
    gasto_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_roles_gastos),
):
    gasto = _gasto_de_mi_sucursal(db, gasto_id, current_user)
    return gasto.adjuntos


@router.get("/{gasto_id}/adjuntos/{adjunto_id}/archivo")
async def ver_adjunto(
    gasto_id: int,
    adjunto_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_roles_gastos),
    storage: Storage = Depends(get_storage),
):
    adjunto = _adjunto_de_mi_sucursal(db, gasto_id, adjunto_id, current_user)
    try:
        datos = await storage.leer(adjunto.storage_key)
    except ObjetoNoEncontrado:
        # Fila sin archivo (p. ej. subida en otro backend de storage): 404, no 500.
        raise HTTPException(status_code=404, detail="Archivo no disponible")
    return Response(
        content=datos,
        media_type=adjunto.content_type,
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, max-age=300",
            "Content-Disposition": "inline",
        },
    )


@router.delete("/{gasto_id}/adjuntos/{adjunto_id}", status_code=status.HTTP_204_NO_CONTENT)
async def borrar_adjunto(
    gasto_id: int,
    adjunto_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_roles_gastos),
    storage: Storage = Depends(get_storage),
):
    _gasto_de_mi_sucursal(db, gasto_id, current_user, bloquear=True)
    adjunto = (
        db.query(GastoAdjunto)
        .filter_by(id=adjunto_id, gasto_id=gasto_id, sucursal_id=current_user.sucursal_id)
        .first()
    )
    if adjunto is None:
        return None  # Replay autorizado; la fila ya fue eliminada.
    programar_borrado(db, adjunto.storage_key)
    db.delete(adjunto)
    db.commit()
    return None
