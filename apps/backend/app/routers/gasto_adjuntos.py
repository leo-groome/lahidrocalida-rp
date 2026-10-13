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

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models import Gasto, GastoAdjunto, Usuario
from app.schemas import AdjuntoResponse
from app.services.storage import (
    MAX_ADJUNTO_BYTES,
    AdjuntoInvalido,
    Storage,
    detectar_tipo,
    generar_llave,
    get_storage,
)

router = APIRouter(prefix="/gastos", tags=["gastos"])

MAX_ADJUNTOS_POR_GASTO = 5
_CHUNK = 64 * 1024

_roles_gastos = require_roles("administrador", "compras", "cajero")


def _gasto_de_mi_sucursal(db: Session, gasto_id: int, user: Usuario) -> Gasto:
    gasto = db.query(Gasto).filter(Gasto.id == gasto_id).first()
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
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_roles_gastos),
    storage: Storage = Depends(get_storage),
):
    gasto = _gasto_de_mi_sucursal(db, gasto_id, current_user)

    if len(gasto.adjuntos) >= MAX_ADJUNTOS_POR_GASTO:
        raise HTTPException(
            status_code=400,
            detail=f"Máximo {MAX_ADJUNTOS_POR_GASTO} fotos por gasto",
        )

    datos = await _leer_limitado(archivo)
    if not datos:
        raise HTTPException(status_code=400, detail="Archivo vacío")
    try:
        content_type = detectar_tipo(datos[:16])
    except AdjuntoInvalido as e:
        raise HTTPException(status_code=415, detail=str(e))

    llave = generar_llave(f"gastos/{gasto.sucursal_id}", content_type)
    await storage.guardar(llave, datos, content_type)

    adjunto = GastoAdjunto(
        gasto_id=gasto.id,
        sucursal_id=gasto.sucursal_id,
        storage_key=llave,
        content_type=content_type,
        size=len(datos),
        subido_por_id=current_user.id,
    )
    db.add(adjunto)
    try:
        db.commit()
    except Exception:
        db.rollback()
        await storage.borrar(llave)  # no dejar archivos huérfanos
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
    datos = await storage.leer(adjunto.storage_key)
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
    adjunto = _adjunto_de_mi_sucursal(db, gasto_id, adjunto_id, current_user)
    llave = adjunto.storage_key
    db.delete(adjunto)
    db.commit()
    await storage.borrar(llave)
    return None
