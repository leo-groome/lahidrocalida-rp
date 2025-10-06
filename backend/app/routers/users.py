from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models import Usuario, Sucursal
from app.schemas import UsuarioCreate, UsuarioResponse
from app.auth import get_current_active_user, get_password_hash

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.post("/", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def create_usuario(
    data: UsuarioCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Crear un usuario (requiere usuario autenticado)."""
    # Validar rol del creador (solo administrador puede crear)
    if current_user.rol != "administrador":
        raise HTTPException(status_code=403, detail="No autorizado para crear usuarios")

    usuario = Usuario(
        nombre=data.nombre,
        rol=data.rol,
        # Guardar contraseña hasheada
        password=get_password_hash(data.password),
        activo=data.activo,
        sucursal_id=data.sucursal_id,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.get("/", response_model=List[UsuarioResponse])
def list_usuarios(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Listar usuarios (requiere usuario autenticado)."""
    return db.query(Usuario).all()


@router.get("/me", response_model=UsuarioResponse)
def get_me(current_user: Usuario = Depends(get_current_active_user)):
    return current_user


