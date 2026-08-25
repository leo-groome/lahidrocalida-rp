from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth import (
    authenticate_user,
    create_access_token,
    get_current_active_user,
    verify_password,
)
from app.core.rate_limit import (
    clear_login_failures,
    enforce_login_rate_limit,
    register_login_failure,
)
from app.db.session import get_db
from app.models import RegistroAsistencia, Usuario
from app.schemas import (
    AdminLogin,
    AsistenciaPinRequest,
    RegistroAsistenciaResponse,
    Token,
    UsuarioLogin,
    UsuarioResponse,
)
from app.utils.timezone import get_mexico_now

router = APIRouter(prefix="/auth", tags=["autenticación"])

ROLES_STAFF = ["cajero", "cocina", "mesero"]
ROLES_ADMIN = ["administrador"]


@router.post("/login", response_model=Token)
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Endpoint OAuth2 estándar — compatibilidad con Swagger UI (usa ID como username)"""
    rl_keys = enforce_login_rate_limit(request, form_data.username)
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        register_login_failure(rl_keys)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ID de usuario o NIP incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    clear_login_failures(rl_keys)
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login-simple", response_model=Token)
async def login_simple(request: Request, user_data: UsuarioLogin, db: Session = Depends(get_db)):
    """Login por NIP táctil para staff (mesero, cajero, cocina). No permite admins."""
    rl_keys = enforce_login_rate_limit(request, user_data.user_id)

    try:
        user_id_int = int(user_data.user_id)
    except ValueError:
        register_login_failure(rl_keys)
        raise HTTPException(status_code=400, detail="user_id inválido")

    user = db.query(Usuario).filter(Usuario.id == user_id_int, Usuario.activo == True).first()

    if not user or user.rol in ROLES_ADMIN:
        register_login_failure(rl_keys)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o no autorizado para login NIP",
        )

    if not verify_password(user_data.pin, user.pin):
        register_login_failure(rl_keys)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="NIP incorrecto",
        )

    clear_login_failures(rl_keys)
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login-admin", response_model=Token)
async def login_admin(request: Request, user_data: AdminLogin, db: Session = Depends(get_db)):
    """Login para administradores con email + password. Solo accesible desde /admin-login."""
    rl_keys = enforce_login_rate_limit(request, user_data.email)
    user = (
        db.query(Usuario)
        .filter(
            Usuario.nombre == user_data.email,  # Usamos 'nombre' como identificador admin
            Usuario.activo == True,
            Usuario.rol == "administrador",
        )
        .first()
    )

    if not user or not verify_password(user_data.password, user.pin):
        register_login_failure(rl_keys)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    clear_login_failures(rl_keys)
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/asistencia", response_model=RegistroAsistenciaResponse)
async def registrar_asistencia(
    request: Request, data: AsistenciaPinRequest, db: Session = Depends(get_db)
):
    """
    Clock-In / Clock-Out mediante NIP. No requiere JWT.
    - Sin registro abierto → Clock-In (nueva entrada)
    - Con registro abierto → Clock-Out (registra salida)
    Solo para roles no-admin.

    Rate-limitado igual que los logins: sin JWT y verificando el mismo NIP, es
    el mismo oráculo de fuerza-bruta que /auth/login-simple, y además escribe.
    """
    rl_keys = enforce_login_rate_limit(request, str(data.usuario_id))
    user = db.query(Usuario).filter(Usuario.id == data.usuario_id, Usuario.activo == True).first()

    if not user:
        register_login_failure(rl_keys)
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if user.rol in ROLES_ADMIN:
        raise HTTPException(
            status_code=403, detail="Administradores no tienen registro de asistencia"
        )

    if not verify_password(data.pin, user.pin):
        register_login_failure(rl_keys)
        raise HTTPException(status_code=401, detail="NIP incorrecto")

    clear_login_failures(rl_keys)

    # Buscar registro abierto (sin fecha_salida)
    registro_abierto = (
        db.query(RegistroAsistencia)
        .filter(
            RegistroAsistencia.usuario_id == data.usuario_id,
            RegistroAsistencia.fecha_salida == None,
        )
        .first()
    )

    if registro_abierto:
        # Clock-Out
        registro_abierto.fecha_salida = get_mexico_now()
        if data.notas:
            registro_abierto.notas = data.notas
        db.commit()
        db.refresh(registro_abierto)
        registro = registro_abierto
    else:
        # Clock-In
        registro = RegistroAsistencia(
            usuario_id=data.usuario_id,
            fecha_entrada=get_mexico_now(),
            notas=data.notas,
        )
        db.add(registro)
        db.commit()
        db.refresh(registro)

    # Calcular horas trabajadas si hay salida
    horas = None
    if registro.fecha_salida:
        delta = registro.fecha_salida - registro.fecha_entrada
        horas = round(delta.total_seconds() / 3600, 2)

    return RegistroAsistenciaResponse(
        id=registro.id,
        usuario_id=registro.usuario_id,
        fecha_entrada=registro.fecha_entrada,
        fecha_salida=registro.fecha_salida,
        notas=registro.notas,
        usuario_nombre=user.nombre,
        horas_trabajadas=horas,
    )


@router.get("/me", response_model=UsuarioResponse)
async def read_users_me(current_user: Usuario = Depends(get_current_active_user)):
    """Obtiene información del usuario actual"""
    return current_user


@router.get("/users", response_model=List[UsuarioResponse])
async def list_public_users(rol: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Lista usuarios activos NO-admin para el selector de login NIP.
    Opcional: filtrar por rol (ej. ?rol=mesero).
    Los administradores nunca aparecen en esta lista.
    """
    query = db.query(Usuario).filter(Usuario.activo == True, Usuario.rol.notin_(ROLES_ADMIN))
    if rol and rol in ROLES_STAFF:
        query = query.filter(Usuario.rol == rol)
    return query.order_by(Usuario.nombre).all()


@router.get("/asistencia/status/{usuario_id}")
async def check_asistencia_status(usuario_id: int, db: Session = Depends(get_db)):
    """
    Verifica si el usuario tiene un turno (registro de asistencia) activo (sin fecha_salida).
    """
    registro_abierto = (
        db.query(RegistroAsistencia)
        .filter(
            RegistroAsistencia.usuario_id == usuario_id, RegistroAsistencia.fecha_salida == None
        )
        .first()
    )

    return {
        "tiene_turno_activo": registro_abierto is not None,
        "fecha_entrada": registro_abierto.fecha_entrada if registro_abierto else None,
    }
