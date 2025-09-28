from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import Usuario
from app.core.config import settings

# Configuración para hash de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configuración para JWT
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

# Esquema de autenticación
security = HTTPBearer()

def verify_password(plain_password: str, stored_password: str) -> bool:
    """Verifica contraseña permitiendo compatibilidad con texto plano temporalmente."""
    # Si parece un hash bcrypt ($2...), verificamos con bcrypt
    if stored_password.startswith("$2"):
        try:
            return pwd_context.verify(plain_password, stored_password)
        except Exception:
            return False
    # De lo contrario, comparamos como texto plano (modo simple temporal)
    return plain_password == stored_password

def get_password_hash(password: str) -> str:
    """Genera el hash de una contraseña"""
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
    if not verify_password(password, user.password):
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

def get_current_active_user(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    """Obtiene el usuario actual activo"""
    if not current_user.activo:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    return current_user
