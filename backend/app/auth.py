from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional as _Optional
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import Usuario
from app.core.config import settings

# Configuración para hash de contraseñas
# Usamos argon2 como esquema principal (sin límite de 72 bytes),
# con compatibilidad para bcrypt_sha256/bcrypt ya almacenados
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt_sha256", "bcrypt"],
    deprecated="auto",
)

# Configuración para JWT
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

# Esquema de autenticación
security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)  # Para endpoints públicos opcionales (KDS)

def verify_password(plain_password: str, stored_password: str) -> bool:
    """Verifica contraseña hash (bcrypt_sha256/bcrypt) o texto plano legado."""
    try:
        # Passlib detecta el esquema según el prefijo del hash
        if stored_password.startswith("$"):
            return pwd_context.verify(plain_password, stored_password)
        # Compatibilidad temporal con texto plano
        return plain_password == stored_password
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    """Genera el hash de una contraseña usando argon2 por defecto"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Crea un token JWT"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def authenticate_user(db: Session, user_id: str, password: str) -> Optional[Usuario]:
    """Autentica un usuario verificando ID y contraseña"""
    try:
        # Convertir el ID de string a int
        user_id_int = int(user_id)
    except ValueError:
        return None
    
    user = db.query(Usuario).filter(Usuario.id == user_id_int).first()
    if not user:
        return None
    if not verify_password(password, user.pin):
        return None
    return user

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Usuario:
    """Obtiene el usuario actual basado en el token JWT"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario_id: int = payload.get("sub")
        if usuario_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if user is None:
        raise credentials_exception
    
    return user

def get_optional_current_user(
    credentials: _Optional[HTTPAuthorizationCredentials] = Depends(security_optional),
    db: Session = Depends(get_db)
) -> _Optional[Usuario]:
    """Retorna el usuario autenticado o None si no hay token (para endpoints públicos como KDS)."""
    if credentials is None:
        return None
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario_id: int = payload.get("sub")
        if usuario_id is None:
            return None
        user = db.query(Usuario).filter(Usuario.id == usuario_id).first()
        return user if user and user.activo else None
    except JWTError:
        return None


def get_current_active_user(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    """Obtiene el usuario actual activo"""
    if not current_user.activo:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    return current_user
