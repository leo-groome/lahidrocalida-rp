from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models import Usuario, Sucursal
from app.schemas import UsuarioCreate, UsuarioUpdate, UsuarioResponse
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


@router.get("/{usuario_id}", response_model=UsuarioResponse)
def get_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    # Solo admin puede ver usuarios específicos
    if current_user.rol != "administrador":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    return usuario


@router.put("/{usuario_id}", response_model=UsuarioResponse)
def update_usuario(
    usuario_id: int,
    data: UsuarioUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    # Solo admin puede actualizar usuarios
    if current_user.rol != "administrador":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Verificar conflicto de nombre (excluyendo el usuario actual)
    existing_user = db.query(Usuario).filter(
        Usuario.nombre == data.nombre,
        Usuario.sucursal_id == data.sucursal_id,
        Usuario.id != usuario_id
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Ya existe otro usuario con ese nombre en esta sucursal"
        )
    
    # Actualizar campos
    usuario.nombre = data.nombre
    usuario.rol = data.rol
    usuario.activo = data.activo
    usuario.sucursal_id = data.sucursal_id
    
    # Actualizar contraseña solo si se proporciona una nueva
    if data.password:
        usuario.password = get_password_hash(data.password)
    
    db.commit()
    db.refresh(usuario)
    
    return usuario


@router.delete("/{usuario_id}")
def delete_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    # Solo admin puede eliminar usuarios
    if current_user.rol != "administrador":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    # No permitir que se elimine a sí mismo
    if usuario_id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propio usuario")
    
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # En lugar de eliminar, marcar como inactivo para preservar integridad
    usuario.activo = False
    db.commit()
    
    return {"message": "Usuario desactivado correctamente"}


