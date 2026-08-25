from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models import RegistroAsistencia, Usuario
from app.schemas import AsistenciaResumenItem, AsistenciaResumenResponse, RegistroAsistenciaResponse

router = APIRouter(prefix="/asistencia", tags=["asistencia"])


@router.get("/", response_model=List[RegistroAsistenciaResponse])
def list_registros(
    usuario_id: Optional[int] = None,
    fecha_inicio: Optional[str] = None,  # YYYY-MM-DD
    fecha_fin: Optional[str] = None,  # YYYY-MM-DD
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("administrador")),
):
    """Listar registros de asistencia. Solo admin."""

    query = db.query(RegistroAsistencia)

    if usuario_id:
        query = query.filter(RegistroAsistencia.usuario_id == usuario_id)

    if fecha_inicio:
        try:
            dt_inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d")
            query = query.filter(RegistroAsistencia.fecha_entrada >= dt_inicio)
        except ValueError:
            raise HTTPException(
                status_code=400, detail="fecha_inicio inválida. Formato: YYYY-MM-DD"
            )

    if fecha_fin:
        try:
            dt_fin = datetime.strptime(fecha_fin, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.filter(RegistroAsistencia.fecha_entrada <= dt_fin)
        except ValueError:
            raise HTTPException(status_code=400, detail="fecha_fin inválida. Formato: YYYY-MM-DD")

    registros = query.order_by(RegistroAsistencia.fecha_entrada.desc()).all()

    result = []
    for r in registros:
        horas = None
        if r.fecha_salida:
            delta = r.fecha_salida - r.fecha_entrada
            horas = round(delta.total_seconds() / 3600, 2)
        result.append(
            RegistroAsistenciaResponse(
                id=r.id,
                usuario_id=r.usuario_id,
                fecha_entrada=r.fecha_entrada,
                fecha_salida=r.fecha_salida,
                notas=r.notas,
                usuario_nombre=r.usuario.nombre if r.usuario else None,
                horas_trabajadas=horas,
            )
        )

    return result


@router.get("/usuario/{usuario_id}", response_model=List[RegistroAsistenciaResponse])
def historial_usuario(
    usuario_id: int,
    limit: int = 30,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("administrador")),
):
    """Historial de asistencia de un empleado específico. Solo admin."""

    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    registros = (
        db.query(RegistroAsistencia)
        .filter(RegistroAsistencia.usuario_id == usuario_id)
        .order_by(RegistroAsistencia.fecha_entrada.desc())
        .limit(limit)
        .all()
    )

    result = []
    for r in registros:
        horas = None
        if r.fecha_salida:
            delta = r.fecha_salida - r.fecha_entrada
            horas = round(delta.total_seconds() / 3600, 2)
        result.append(
            RegistroAsistenciaResponse(
                id=r.id,
                usuario_id=r.usuario_id,
                fecha_entrada=r.fecha_entrada,
                fecha_salida=r.fecha_salida,
                notas=r.notas,
                usuario_nombre=usuario.nombre,
                horas_trabajadas=horas,
            )
        )

    return result


@router.get("/resumen", response_model=AsistenciaResumenResponse)
def resumen_asistencia(
    fecha_inicio: str,  # YYYY-MM-DD
    fecha_fin: str,  # YYYY-MM-DD
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("administrador")),
):
    """Resumen de horas trabajadas por empleado en un rango de fechas. Solo admin."""

    try:
        dt_inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d")
        dt_fin = datetime.strptime(fecha_fin, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Usar YYYY-MM-DD")

    if dt_inicio > dt_fin:
        raise HTTPException(status_code=400, detail="fecha_inicio debe ser anterior a fecha_fin")

    # Usuarios no-admin activos
    usuarios = (
        db.query(Usuario)
        .filter(Usuario.activo == True, Usuario.rol.notin_(["administrador"]))
        .all()
    )

    empleados_resumen = []
    for usuario in usuarios:
        registros = (
            db.query(RegistroAsistencia)
            .filter(
                RegistroAsistencia.usuario_id == usuario.id,
                RegistroAsistencia.fecha_entrada >= dt_inicio,
                RegistroAsistencia.fecha_entrada <= dt_fin,
            )
            .all()
        )

        horas_totales = 0.0
        ultima_entrada = None
        ultima_salida = None

        for r in registros:
            if r.fecha_salida:
                delta = r.fecha_salida - r.fecha_entrada
                horas_totales += delta.total_seconds() / 3600
            if ultima_entrada is None or r.fecha_entrada > ultima_entrada:
                ultima_entrada = r.fecha_entrada
            if r.fecha_salida and (ultima_salida is None or r.fecha_salida > ultima_salida):
                ultima_salida = r.fecha_salida

        empleados_resumen.append(
            AsistenciaResumenItem(
                usuario_id=usuario.id,
                usuario_nombre=usuario.nombre,
                rol=usuario.rol,
                total_registros=len(registros),
                horas_totales=round(horas_totales, 2),
                ultima_entrada=ultima_entrada,
                ultima_salida=ultima_salida,
            )
        )

    return AsistenciaResumenResponse(
        fecha_inicio=dt_inicio,
        fecha_fin=dt_fin,
        empleados=empleados_resumen,
    )
