"""Dependencias transversales de FastAPI.

Centraliza lo que hoy está duplicado en los routers:
- autorización por rol (`require_roles`), que hasta ahora se hace con checks
  inline de `current_user.rol` en cada endpoint;
- lookup del turno abierto de la sucursal, que existe en 4 copias
  (`pedidos._get_turno_activo`, `turnos._obtener_turno_activo_sucursal` y dos
  queries inline en `admin.py` y `reportes.py`).

Los routers todavía NO consumen este módulo: la migración es tarea 1.5.
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_active_user
from app.db.session import get_db
from app.models import Turno, Usuario

# Estado de un turno abierto. Único lugar donde vive el literal.
TURNO_ESTADO_ABIERTO = "abierto"


def require_roles(*roles: str):
    """Dependency factory: exige que el rol del usuario esté en `roles`.

    Cuelga de `get_current_active_user` (no de `get_current_user`) porque solo
    aquella verifica `usuario.activo`. Un usuario inactivo por lo tanto nunca
    llega al chequeo de rol.

    Uso:
        @router.get("/x", dependencies=[Depends(require_roles("administrador"))])
        # o, si el endpoint necesita el usuario:
        current_user: Usuario = Depends(require_roles("administrador", "cajero"))

    Devuelve el `Usuario` para poder usarse como parámetro, no solo en
    `dependencies=[...]`.

    Errores:
        401 si no hay token válido (de `get_current_user`).
        400 si el usuario está inactivo (de `get_current_active_user`).
        403 si el rol no está permitido.
    """
    if not roles:
        raise ValueError("require_roles necesita al menos un rol")

    roles_permitidos = frozenset(roles)

    def _check_roles(current_user: Usuario = Depends(get_current_active_user)) -> Usuario:
        if current_user.rol not in roles_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requiere rol: {', '.join(sorted(roles_permitidos))}",
            )
        return current_user

    return _check_roles


def obtener_turno_activo(db: Session, sucursal_id: int) -> Optional[Turno]:
    """Turno abierto de una sucursal, o None si no hay.

    Helper plano (no dependency) para los call sites que necesitan el turno de
    una sucursal distinta a la del usuario — p. ej. `pedidos.py` al reasignar
    el turno de un pedido usando `pedido.sucursal_id`.

    Apoyado por el índice parcial `idx_turno_activo_sucursal`
    (sucursal_id, estado='abierto') definido en `models.Turno`.
    """
    return (
        db.query(Turno)
        .filter(Turno.sucursal_id == sucursal_id, Turno.estado == TURNO_ESTADO_ABIERTO)
        .first()
    )


def get_turno_activo(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
) -> Optional[Turno]:
    """Turno abierto de la sucursal DEL USUARIO AUTENTICADO, o None.

    La sucursal sale de `current_user.sucursal_id` — nunca de body ni query
    param, para no permitir que un cliente lea el turno de otra sucursal.

    Devuelve None en lugar de lanzar 404: cada endpoint decide si la ausencia
    de turno es un error (crear pedido) o solo un fallback (reportes caen al
    filtro por fecha del día). Ese es el comportamiento de las 4 copias
    actuales y se preserva tal cual.
    """
    return obtener_turno_activo(db, current_user.sucursal_id)
