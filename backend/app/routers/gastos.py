from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.models import Gasto, Usuario
from app.schemas import GastoCreate, GastoResponse
from app.auth import get_current_active_user

router = APIRouter(prefix="/gastos", tags=["gastos"])


def _ensure_can_manage_gastos(user: Usuario) -> None:
    if user.rol not in ["administrador", "compras"]:
        raise HTTPException(status_code=403, detail="No autorizado para gestionar gastos")


@router.post("/", response_model=GastoResponse, status_code=status.HTTP_201_CREATED)
def create_gasto(
    data: GastoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    _ensure_can_manage_gastos(current_user)

    gasto = Gasto(
        descripcion=data.descripcion,
        monto=data.monto,
        categoria=data.categoria,
        sucursal_id=data.sucursal_id,
    )
    db.add(gasto)
    db.commit()
    db.refresh(gasto)
    return gasto


@router.get("/", response_model=List[GastoResponse])
def list_gastos(
    sucursal_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    # Compras ve solo su sucursal; admin puede ver todos y filtrar
    query = db.query(Gasto)
    if current_user.rol == "compras":
        query = query.filter(Gasto.sucursal_id == current_user.sucursal_id)
    if current_user.rol == "administrador" and sucursal_id is not None:
        query = query.filter(Gasto.sucursal_id == sucursal_id)
    return query.order_by(Gasto.fecha_gasto.desc()).all()


@router.get("/{gasto_id}", response_model=GastoResponse)
def get_gasto(
    gasto_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    gasto = db.query(Gasto).filter(Gasto.id == gasto_id).first()
    if not gasto:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")

    if current_user.rol == "compras" and gasto.sucursal_id != current_user.sucursal_id:
        raise HTTPException(status_code=403, detail="No autorizado para ver este gasto")
    return gasto


@router.put("/{gasto_id}", response_model=GastoResponse)
def update_gasto(
    gasto_id: int,
    data: GastoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    _ensure_can_manage_gastos(current_user)
    gasto = db.query(Gasto).filter(Gasto.id == gasto_id).first()
    if not gasto:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")

    # Si es rol compras, asegurar que edita su sucursal
    if current_user.rol == "compras" and gasto.sucursal_id != current_user.sucursal_id:
        raise HTTPException(status_code=403, detail="No autorizado para editar este gasto")

    gasto.descripcion = data.descripcion
    gasto.monto = data.monto
    gasto.categoria = data.categoria
    gasto.sucursal_id = data.sucursal_id
    db.commit()
    db.refresh(gasto)
    return gasto


@router.delete("/{gasto_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_gasto(
    gasto_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    _ensure_can_manage_gastos(current_user)
    gasto = db.query(Gasto).filter(Gasto.id == gasto_id).first()
    if not gasto:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")

    if current_user.rol == "compras" and gasto.sucursal_id != current_user.sucursal_id:
        raise HTTPException(status_code=403, detail="No autorizado para eliminar este gasto")

    db.delete(gasto)
    db.commit()
    return None


