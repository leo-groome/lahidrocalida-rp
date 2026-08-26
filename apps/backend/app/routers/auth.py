from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import (
    authenticate_user,
    create_access_token,
    get_current_active_user,
    verificar_pin_admin,
    verify_password,
)
from app.core.rate_limit import (
    clear_login_failures,
    enforce_login_rate_limit,
    register_login_failure,
)
from app.db.session import get_db
from app.domain.estados import MAX_HORAS_JORNADA
from app.models import AutorizacionPin, RegistroAsistencia, Usuario
from app.schemas import (
    AdminLogin,
    AsistenciaPinRequest,
    PinVerifyRequest,
    RegistroAsistenciaResponse,
    Token,
    UsuarioLogin,
    UsuarioResponse,
)
from app.services.jornada import reconciliar_jornada
from app.utils.timezone import get_mexico_now, jornada_de

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
    rl_keys = await enforce_login_rate_limit(request, form_data.username)
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        await register_login_failure(rl_keys)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ID de usuario o NIP incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    await clear_login_failures(rl_keys)
    if user.sucursal_id is not None:
        reconciliar_jornada(db, user.sucursal_id)
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login-simple", response_model=Token)
async def login_simple(request: Request, user_data: UsuarioLogin, db: Session = Depends(get_db)):
    """Login por NIP táctil para staff (mesero, cajero, cocina). No permite admins."""
    rl_keys = await enforce_login_rate_limit(request, user_data.user_id)

    try:
        user_id_int = int(user_data.user_id)
    except ValueError:
        await register_login_failure(rl_keys)
        raise HTTPException(status_code=400, detail="user_id inválido")

    user = db.query(Usuario).filter(Usuario.id == user_id_int, Usuario.activo == True).first()

    if not user or user.rol in ROLES_ADMIN:
        await register_login_failure(rl_keys)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o no autorizado para login NIP",
        )

    if not verify_password(user_data.pin, user.pin):
        await register_login_failure(rl_keys)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="NIP incorrecto",
        )

    await clear_login_failures(rl_keys)
    if user.sucursal_id is not None:
        reconciliar_jornada(db, user.sucursal_id)
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login-admin", response_model=Token)
async def login_admin(request: Request, user_data: AdminLogin, db: Session = Depends(get_db)):
    """Login para administradores con email + password. Solo accesible desde /admin-login."""
    rl_keys = await enforce_login_rate_limit(request, user_data.email)
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
        await register_login_failure(rl_keys)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    await clear_login_failures(rl_keys)
    if user.sucursal_id is not None:
        reconciliar_jornada(db, user.sucursal_id)
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
    rl_keys = await enforce_login_rate_limit(request, str(data.usuario_id))
    user = db.query(Usuario).filter(Usuario.id == data.usuario_id, Usuario.activo == True).first()

    if not user:
        await register_login_failure(rl_keys)
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if user.rol in ROLES_ADMIN:
        raise HTTPException(
            status_code=403, detail="Administradores no tienen registro de asistencia"
        )

    if not verify_password(data.pin, user.pin):
        await register_login_failure(rl_keys)
        raise HTTPException(status_code=401, detail="NIP incorrecto")

    await clear_login_failures(rl_keys)

    ahora = get_mexico_now()
    jornada_actual = jornada_de(ahora)

    # Registro realmente abierto de HOY: excluye tanto los ya cerrados como
    # los huérfanos de una jornada anterior que reconciliar_jornada marcó con
    # cierre_automatico=True (fecha_salida sigue NULL a propósito ahí — no se
    # inventa la hora real — pero ya no cuentan como "abierto" para este
    # toggle: eso es lo que respeta el índice único parcial de la migración).
    # `with_for_update()` cierra la carrera de dos clock-out simultáneos.
    registro_abierto = (
        db.query(RegistroAsistencia)
        .filter(
            RegistroAsistencia.usuario_id == data.usuario_id,
            RegistroAsistencia.fecha_salida.is_(None),
            RegistroAsistencia.cierre_automatico.is_(False),
        )
        .with_for_update()
        .first()
    )

    if registro_abierto and jornada_de(registro_abierto.fecha_entrada) == jornada_actual:
        # Clock-Out
        registro_abierto.fecha_salida = ahora
        if data.notas:
            registro_abierto.notas = data.notas
        db.commit()
        db.refresh(registro_abierto)
        registro = registro_abierto
    else:
        # Clock-In. Si `registro_abierto` existe pero es de otra jornada, se
        # ignora para este toggle (nunca se lee como salida de hoy).
        registro = RegistroAsistencia(
            usuario_id=data.usuario_id,
            fecha_entrada=ahora,
            notas=data.notas,
        )
        db.add(registro)
        try:
            db.commit()
        except IntegrityError:
            # Carrera: otro request ganó la inserción del check-in de hoy
            # (índice único parcial de la migración). Se resuelve al estado
            # actual en vez de fallar la request.
            db.rollback()
            registro = (
                db.query(RegistroAsistencia)
                .filter(
                    RegistroAsistencia.usuario_id == data.usuario_id,
                    RegistroAsistencia.fecha_salida.is_(None),
                    RegistroAsistencia.cierre_automatico.is_(False),
                )
                .order_by(RegistroAsistencia.fecha_entrada.desc())
                .first()
            )
            if registro is None:
                raise
        else:
            db.refresh(registro)

    # Calcular horas trabajadas si hay salida, con tope defensivo de MAX_HORAS_JORNADA
    horas = None
    if registro.fecha_salida:
        delta = registro.fecha_salida - registro.fecha_entrada
        horas = round(min(delta.total_seconds() / 3600, MAX_HORAS_JORNADA), 2)

    return RegistroAsistenciaResponse(
        id=registro.id,
        usuario_id=registro.usuario_id,
        fecha_entrada=registro.fecha_entrada,
        fecha_salida=registro.fecha_salida,
        notas=registro.notas,
        usuario_nombre=user.nombre,
        horas_trabajadas=horas,
    )


@router.post("/verify-admin-pin")
async def verify_admin_pin(
    request: Request,
    data: PinVerifyRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    """Autoriza puntualmente con PIN de un administrador activo (cualquiera).

    Gate previo a mostrar las analíticas del turno (venta/propinas del día) —
    no hay cajero fijo, así que el rol de la sesión activa no basta.
    """
    admin = await verificar_pin_admin(db, data.pin, request, current_user)
    db.add(
        AutorizacionPin(
            accion="ver_analiticas",
            ejecutado_por_id=current_user.id,
            autorizado_por_id=admin.id,
        )
    )
    db.commit()
    return {"ok": True}


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
            RegistroAsistencia.usuario_id == usuario_id,
            RegistroAsistencia.fecha_salida.is_(None),
            RegistroAsistencia.cierre_automatico.is_(False),
        )
        .first()
    )

    return {
        "tiene_turno_activo": registro_abierto is not None,
        "fecha_entrada": registro_abierto.fecha_entrada if registro_abierto else None,
    }
