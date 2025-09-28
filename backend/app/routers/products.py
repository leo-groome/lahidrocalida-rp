from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models import Platillo, Usuario
from app.schemas import PlatilloCreate, PlatilloResponse
from app.auth import get_current_active_user

router = APIRouter(prefix="/platillos", tags=["platillos"])


@router.get("/", response_model=List[PlatilloResponse])
def list_platillos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    return db.query(Platillo).all()


@router.post("/", response_model=PlatilloResponse, status_code=status.HTTP_201_CREATED)
def create_platillo(
    data: PlatilloCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    # Solo admin puede crear platillos inicialmente
    if current_user.rol != "administrador":
        raise HTTPException(status_code=403, detail="No autorizado para crear platillos")

    platillo = Platillo(
        nombre=data.nombre,
        descripcion=data.descripcion,
        precio=data.precio,
        categoria=data.categoria,
        estado=data.estado,
    )
    db.add(platillo)
    db.commit()
    db.refresh(platillo)
    return platillo


