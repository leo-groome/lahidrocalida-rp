from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.auth import authenticate_user, create_access_token, get_current_active_user
from app.models import Usuario
from app.schemas import Token, UsuarioResponse, UsuarioLogin

router = APIRouter(prefix="/auth", tags=["autenticación"])

@router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Endpoint para iniciar sesión y obtener token JWT (usar ID como username)"""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ID de usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login-simple", response_model=Token)
async def login_simple(
    user_data: UsuarioLogin,
    db: Session = Depends(get_db)
):
    """Endpoint para login con ID y contraseña"""
    user = authenticate_user(db, user_data.user_id, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ID de usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UsuarioResponse)
async def read_users_me(current_user: Usuario = Depends(get_current_active_user)):
    """Obtiene información del usuario actual"""
    return current_user
