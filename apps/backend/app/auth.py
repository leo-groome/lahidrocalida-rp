from datetime import datetime, timedelta
from typing import Optional
from typing import Optional as _Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models import Usuario
from app.services.jornada import reconciliar_jornada
from app.utils.timezone import get_mexico_now, jornada_de, to_mexico_aware

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
    """Verifica una contraseña contra un hash (argon2 / bcrypt_sha256 / bcrypt).

    Solo se acepta un hash reconocible por passlib (prefijo `$`). Cualquier otro
    valor almacenado — texto plano legado, cadena vacía, NULL — devuelve False:
    nunca se compara en claro. Verificado contra la DB de producción: 0 filas con
    PIN sin hashear, así que remover el fallback no bloquea a ningún usuario.
    """
    if not stored_password or not stored_password.startswith("$"):
        return False
    try:
        # Passlib detecta el esquema según el prefijo del hash
        return pwd_context.verify(plain_password, stored_password)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Genera el hash de una contraseña usando argon2 por defecto"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Crea un token JWT.

    Lleva `jornada` (día de jornada operativa al momento del login, ISO date)
    e `iat` — ambos usados en `_decode_token` para cortar la sesión en el
    corte de jornada (S3.2) y para revocación selectiva (S3.3), sin cron ni
    blacklist: se comparan contra el estado actual en cada request.
    """
    to_encode = data.copy()
    now = datetime.utcnow()
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update(
        {
            "exp": expire,
            "iat": now,
            "jornada": jornada_de(get_mexico_now()).isoformat(),
        }
    )
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


def _resolve_user_from_token(token: str, db: Session) -> Optional[Usuario]:
    """Decodifica el JWT y resuelve el `Usuario`, o `None` si el token no es
    válido por cualquier motivo: firma/formato, usuario inexistente, jornada
    del token distinta de la jornada actual (S3.2 — sin cron ni blacklist,
    solo comparación en vivo), o sesión revocada selectivamente vía
    `sesiones_validas_desde` (S3.3).

    Un token SIN claim `jornada` (emitido antes de S3) se trata como válido
    en cuanto a jornada — no se fuerza re-login masivo al desplegar.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

    usuario_id = payload.get("sub")
    if usuario_id is None:
        return None

    user = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if user is None:
        return None

    jornada_token = payload.get("jornada")
    if jornada_token is not None and jornada_token != jornada_de(get_mexico_now()).isoformat():
        return None

    iat = payload.get("iat")
    if user.sesiones_validas_desde is not None and iat is not None:
        if iat < to_mexico_aware(user.sesiones_validas_desde).timestamp():
            return None

    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)
) -> Usuario:
    """Obtiene el usuario actual basado en el token JWT"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user = _resolve_user_from_token(credentials.credentials, db)
    if user is None:
        raise credentials_exception

    if user.sucursal_id is not None:
        reconciliar_jornada(db, user.sucursal_id)

    return user


def get_optional_current_user(
    credentials: _Optional[HTTPAuthorizationCredentials] = Depends(security_optional),
    db: Session = Depends(get_db),
) -> _Optional[Usuario]:
    """Retorna el usuario autenticado o None si no hay token (para endpoints públicos como KDS)."""
    if credentials is None:
        return None
    user = _resolve_user_from_token(credentials.credentials, db)
    return user if user and user.activo else None


def get_current_active_user(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    """Obtiene el usuario actual activo"""
    if not current_user.activo:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    return current_user
