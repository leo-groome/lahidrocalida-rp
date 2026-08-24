from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_active_user
from app.db.session import get_db
from app.models import Gasto, Pedido, Turno, TurnoDenominacion, Usuario
from app.schemas import (
    DenominacionBase,
    TurnoCierreRequest,
    TurnoCreate,
    TurnoResponse,
    TurnoUpdate,
)
from app.utils.timezone import MEXICO_TZ, get_mexico_now

router = APIRouter(prefix="/turnos", tags=["turnos"])


# ===== FUNCIONES HELPER =====


def _validar_permisos_turnos(usuario: Usuario):
    """Validar que el usuario tenga permisos para gestionar turnos"""
    if usuario.rol not in ["cajero", "administrador"]:
        raise HTTPException(
            status_code=403,
            detail="Solo cajeros y administradores pueden gestionar turnos",
        )


def _get_turno_diferencia(turno: Turno) -> Optional[float]:
    diferencia = getattr(turno, "diferencia", None)
    return float(diferencia) if diferencia is not None else None


def _obtener_turno_activo_sucursal(db: Session, sucursal_id: int) -> Optional[Turno]:
    """Obtener el turno activo de una sucursal"""
    return (
        db.query(Turno).filter(Turno.sucursal_id == sucursal_id, Turno.estado == "abierto").first()
    )


def _validar_turno_existente(db: Session, turno_id: int) -> Turno:
    """Validar que un turno exista y devolverlo"""
    turno = db.query(Turno).filter(Turno.id == turno_id).first()
    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    return turno


def _validar_puede_editar_turno(usuario: Usuario, turno: Turno):
    """Validar que el usuario pueda editar/cerrar el turno"""
    # Administradores pueden editar cualquier turno
    if usuario.rol == "administrador":
        return

    # Cajeros solo pueden editar sus propios turnos
    if usuario.rol == "cajero" and turno.usuario_id != usuario.id:
        raise HTTPException(status_code=403, detail="Solo puedes gestionar tus propios turnos")


def _calcular_totales_denominaciones(denominaciones_data: List[dict]) -> Decimal:
    """Calcular total a partir de lista de denominaciones"""
    total = Decimal("0")
    for denom in denominaciones_data:
        subtotal = Decimal(denom["denominacion"]) * Decimal(denom["cantidad"])
        total += subtotal
    return total


def _guardar_denominaciones(db: Session, turno_id: int, tipo: str, denominaciones_data: List[dict]):
    """Guardar denominaciones para un turno"""
    for denom_data in denominaciones_data:
        denom = TurnoDenominacion(
            turno_id=turno_id,
            tipo=tipo,
            denominacion=denom_data["denominacion"],
            cantidad=denom_data["cantidad"],
            subtotal=Decimal(denom_data["denominacion"]) * Decimal(denom_data["cantidad"]),
        )
        db.add(denom)
    db.flush()


def _calcular_movimientos_efectivo(
    db: Session,
    sucursal_id: int,
    fecha_apertura: datetime,
    fecha_cierre: datetime,
    turno_id: Optional[int] = None,
) -> dict:
    """
    Calcular ventas, propinas y gastos en efectivo entre dos fechas
    Retorna: {"ventas_efectivo": Decimal, "propinas_efectivo": Decimal, "gastos": Decimal}
    """
    # Las fechas ya deberían ser aware si vienen de la DB o de get_mexico_now()
    apertura_local = (
        fecha_apertura.replace(tzinfo=MEXICO_TZ)
        if fecha_apertura.tzinfo is None
        else fecha_apertura
    )
    cierre_local = (
        fecha_cierre.replace(tzinfo=MEXICO_TZ) if fecha_cierre.tzinfo is None else fecha_cierre
    )

    # Consultar pedidos pagados en efectivo — por turno_id si está disponible
    ventas_query = db.query(
        func.sum(Pedido.total).label("total_ventas"),
        func.sum(Pedido.propina_efectivo).label("total_propinas"),
    ).filter(
        Pedido.sucursal_id == sucursal_id,
        Pedido.metodo_pago == "efectivo",
        Pedido.estado == "pagado",
    )

    if turno_id:
        ventas_query = ventas_query.filter(Pedido.turno_id == turno_id)
    else:
        ventas_query = ventas_query.filter(
            Pedido.fecha_pago >= apertura_local,
            Pedido.fecha_pago <= cierre_local,
        )

    ventas_res = ventas_query.first()

    # Consultar gastos pagados en efectivo vinculados a este turno
    gastos_query = db.query(func.sum(Gasto.total)).filter(
        Gasto.sucursal_id == sucursal_id,
        Gasto.metodo_pago == "efectivo",
    )

    if turno_id:
        gastos_query = gastos_query.filter(Gasto.turno_id == turno_id)
    else:
        gastos_query = gastos_query.filter(
            Gasto.fecha_gasto >= apertura_local, Gasto.fecha_gasto <= cierre_local
        )

    gastos_total = gastos_query.scalar() or Decimal("0")

    return {
        "ventas_efectivo": ventas_res.total_ventas or Decimal("0"),
        "propinas_efectivo": ventas_res.total_propinas or Decimal("0"),
        "gastos": gastos_total,
    }


# ===== ENDPOINTS =====


@router.post("/iniciar", response_model=TurnoResponse)
def iniciar_turno(
    turno_data: TurnoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    """
    Iniciar un nuevo turno para la sucursal del usuario.
    Solo puede haber un turno activo por sucursal.
    """
    _validar_permisos_turnos(current_user)

    # Verificar que no haya turno activo en la sucursal
    turno_activo = _obtener_turno_activo_sucursal(db, current_user.sucursal_id)
    if turno_activo:
        raise HTTPException(
            status_code=400,
            detail=f"Ya hay un turno activo en esta sucursal (Turno #{turno_activo.id})",
        )

    # Validar que todas las denominaciones sean válidas
    denominaciones_validas = {1000, 500, 200, 100, 50, 20, 10, 5, 2, 1}
    for denom in turno_data.conteo_inicial.denominaciones:
        if denom.denominacion not in denominaciones_validas:
            raise HTTPException(
                status_code=400,
                detail=f"Denominación inválida: {denom.denominacion}. "
                f"Válidas: {sorted(denominaciones_validas)}",
            )
        if denom.cantidad < 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cantidad no puede ser negativa para denominación {denom.denominacion}",
            )

    # Calcular total inicial
    total_inicial = _calcular_totales_denominaciones(
        [d.dict() for d in turno_data.conteo_inicial.denominaciones]
    )

    # Crear turno
    turno = Turno(
        sucursal_id=current_user.sucursal_id,
        usuario_id=current_user.id,
        total_inicial=total_inicial,
        observaciones=turno_data.observaciones,
        estado="abierto",
    )

    db.add(turno)
    db.flush()  # Para obtener el ID

    # Guardar denominaciones iniciales
    _guardar_denominaciones(
        db=db,
        turno_id=turno.id,
        tipo="inicial",
        denominaciones_data=[d.dict() for d in turno_data.conteo_inicial.denominaciones],
    )

    db.commit()

    # Cargar relaciones para respuesta
    db.refresh(turno)
    turno = (
        db.query(Turno)
        .options(
            selectinload(Turno.denominaciones),
            selectinload(Turno.usuario),
            selectinload(Turno.sucursal),
        )
        .filter(Turno.id == turno.id)
        .first()
    )

    # Formatear respuesta
    denominaciones_iniciales = [
        DenominacionBase(
            denominacion=d.denominacion, cantidad=d.cantidad, subtotal=float(d.subtotal)
        )
        for d in turno.denominaciones
        if d.tipo == "inicial"
    ]

    return TurnoResponse(
        id=turno.id,
        sucursal_id=turno.sucursal_id,
        usuario_id=turno.usuario_id,
        fecha_apertura=turno.fecha_apertura,
        estado=turno.estado,
        total_inicial=float(turno.total_inicial),
        observaciones=turno.observaciones,
        denominaciones_iniciales=denominaciones_iniciales,
        usuario_nombre=turno.usuario.nombre if turno.usuario else None,
        sucursal_nombre=turno.sucursal.nombre if turno.sucursal else None,
    )


@router.get("/activo", response_model=TurnoResponse)
def obtener_turno_activo(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    """
    Obtener el turno activo actual para la sucursal del usuario.
    """
    _validar_permisos_turnos(current_user)

    turno = _obtener_turno_activo_sucursal(db, current_user.sucursal_id)
    if not turno:
        raise HTTPException(status_code=404, detail="No hay turno activo en esta sucursal")

    # Cargar relaciones
    turno = (
        db.query(Turno)
        .options(
            selectinload(Turno.denominaciones),
            selectinload(Turno.usuario),
            selectinload(Turno.sucursal),
        )
        .filter(Turno.id == turno.id)
        .first()
    )

    # Separar denominaciones iniciales y finales
    denominaciones_iniciales = []
    denominaciones_finales = []

    for d in turno.denominaciones:
        denom = DenominacionBase(
            denominacion=d.denominacion, cantidad=d.cantidad, subtotal=float(d.subtotal)
        )
        if d.tipo == "inicial":
            denominaciones_iniciales.append(denom)
        else:
            denominaciones_finales.append(denom)

    # Buscar fondo anterior (monto_restante_en_caja del último turno cerrado)
    ultimo_turno_cerrado = (
        db.query(Turno)
        .filter(Turno.sucursal_id == current_user.sucursal_id, Turno.estado == "cerrado")
        .order_by(Turno.fecha_cierre.desc())
        .first()
    )
    ultimo_turno_cerrado = (
        db.query(Turno)
        .filter(Turno.sucursal_id == current_user.sucursal_id, Turno.estado == "cerrado")
        .order_by(Turno.fecha_cierre.desc())
        .first()
    )
    # Reverting to None for fondo anterior since we don't have monto_restante_en_caja
    fondo_anterior = None

    return TurnoResponse(
        id=turno.id,
        sucursal_id=turno.sucursal_id,
        usuario_id=turno.usuario_id,
        fecha_apertura=turno.fecha_apertura,
        fecha_cierre=turno.fecha_cierre,
        estado=turno.estado,
        total_inicial=float(turno.total_inicial),
        total_final=float(turno.total_final) if turno.total_final else None,
        ventas_efectivo=float(turno.ventas_efectivo) if turno.ventas_efectivo else None,
        propinas_efectivo=float(turno.propinas_efectivo) if turno.propinas_efectivo else None,
        fondo_anterior=fondo_anterior,
        observaciones=turno.observaciones,
        denominaciones_iniciales=denominaciones_iniciales,
        denominaciones_finales=denominaciones_finales if denominaciones_finales else None,
        usuario_nombre=turno.usuario.nombre if turno.usuario else None,
        sucursal_nombre=turno.sucursal.nombre if turno.sucursal else None,
    )


@router.post("/{turno_id}/cerrar", response_model=TurnoResponse)
def cerrar_turno(
    turno_id: int,
    cierre_data: TurnoCierreRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    """
    Cerrar un turno con conteo final.
    Calcula automáticamente ventas y propinas en efectivo.
    """
    _validar_permisos_turnos(current_user)

    # Obtener y validar turno
    turno = _validar_turno_existente(db, turno_id)
    _validar_puede_editar_turno(current_user, turno)

    if turno.estado == "cerrado":
        raise HTTPException(status_code=400, detail="El turno ya está cerrado")

    # Validar denominaciones finales
    denominaciones_validas = {1000, 500, 200, 100, 50, 20, 10, 5, 2, 1}
    for denom in cierre_data.conteo_final.denominaciones:
        if denom.denominacion not in denominaciones_validas:
            raise HTTPException(
                status_code=400, detail=f"Denominación inválida: {denom.denominacion}"
            )
        if denom.cantidad < 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cantidad no puede ser negativa para denominación {denom.denominacion}",
            )

    # Calcular total final
    total_final = _calcular_totales_denominaciones(
        [d.dict() for d in cierre_data.conteo_final.denominaciones]
    )

    # Calcular ventas y propinas en efectivo durante el turno
    fecha_cierre = get_mexico_now()
    movs_info = _calcular_movimientos_efectivo(
        db=db,
        sucursal_id=turno.sucursal_id,
        fecha_apertura=turno.fecha_apertura,
        fecha_cierre=fecha_cierre,
        turno_id=turno.id,
    )

    # Calcular diferencia
    diferencia = total_final - (
        turno.total_inicial
        + movs_info["ventas_efectivo"]
        + movs_info["propinas_efectivo"]
        - movs_info["gastos"]
    )

    # Actualizar turno
    turno.fecha_cierre = fecha_cierre
    turno.estado = "cerrado"
    turno.total_final = total_final
    turno.ventas_efectivo = movs_info["ventas_efectivo"]
    turno.propinas_efectivo = movs_info["propinas_efectivo"]

    if cierre_data.observaciones:
        turno.observaciones = (
            f"{turno.observaciones or ''}\n[CIERRE] {cierre_data.observaciones}"
        ).strip()

    # Guardar denominaciones finales
    _guardar_denominaciones(
        db=db,
        turno_id=turno.id,
        tipo="final",
        denominaciones_data=[d.dict() for d in cierre_data.conteo_final.denominaciones],
    )

    db.commit()

    # Cargar relaciones para respuesta
    db.refresh(turno)
    turno = (
        db.query(Turno)
        .options(
            selectinload(Turno.denominaciones),
            selectinload(Turno.usuario),
            selectinload(Turno.sucursal),
        )
        .filter(Turno.id == turno.id)
        .first()
    )

    # Separar denominaciones
    denominaciones_iniciales = []
    denominaciones_finales = []

    for d in turno.denominaciones:
        denom = DenominacionBase(
            denominacion=d.denominacion, cantidad=d.cantidad, subtotal=float(d.subtotal)
        )
        if d.tipo == "inicial":
            denominaciones_iniciales.append(denom)
        else:
            denominaciones_finales.append(denom)

    return TurnoResponse(
        id=turno.id,
        sucursal_id=turno.sucursal_id,
        usuario_id=turno.usuario_id,
        fecha_apertura=turno.fecha_apertura,
        fecha_cierre=turno.fecha_cierre,
        estado=turno.estado,
        total_inicial=float(turno.total_inicial),
        total_final=float(turno.total_final),
        ventas_efectivo=float(turno.ventas_efectivo),
        propinas_efectivo=float(turno.propinas_efectivo),
        diferencia=_get_turno_diferencia(turno),
        observaciones=turno.observaciones,
        denominaciones_iniciales=denominaciones_iniciales,
        denominaciones_finales=denominaciones_finales,
        usuario_nombre=turno.usuario.nombre if turno.usuario else None,
        sucursal_nombre=turno.sucursal.nombre if turno.sucursal else None,
    )


@router.get("/", response_model=List[TurnoResponse])
def listar_turnos(
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    sucursal_id: Optional[int] = None,
    usuario_id: Optional[int] = None,
    estado: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    """
    Listar turnos con filtros opcionales.
    Para cajeros: solo sus turnos en su sucursal.
    Para administradores: todos los turnos.
    """
    _validar_permisos_turnos(current_user)

    # Construir consulta base
    query = db.query(Turno).options(
        selectinload(Turno.denominaciones),
        selectinload(Turno.usuario),
        selectinload(Turno.sucursal),
    )

    # Filtros para cajeros
    if current_user.rol == "cajero":
        query = query.filter(Turno.sucursal_id == current_user.sucursal_id)
        if usuario_id and usuario_id != current_user.id:
            # Cajeros solo pueden ver sus propios turnos
            query = query.filter(Turno.usuario_id == current_user.id)
        else:
            query = query.filter(Turno.usuario_id == current_user.id)

    # Filtros opcionales para administradores o propios
    if current_user.rol == "administrador":
        if sucursal_id:
            query = query.filter(Turno.sucursal_id == sucursal_id)
        if usuario_id:
            query = query.filter(Turno.usuario_id == usuario_id)

    # Filtros de fecha
    if fecha_inicio:
        try:
            fecha_ini = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
            start_dt = datetime.combine(fecha_ini, datetime.min.time(), tzinfo=MEXICO_TZ)
            query = query.filter(Turno.fecha_apertura >= start_dt)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Formato de fecha_inicio inválido. Use YYYY-MM-DD",
            )

    if fecha_fin:
        try:
            fecha_fin_date = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
            end_dt = datetime.combine(
                fecha_fin_date + timedelta(days=1), datetime.min.time(), tzinfo=MEXICO_TZ
            )
            query = query.filter(Turno.fecha_apertura < end_dt)
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Formato de fecha_fin inválido. Use YYYY-MM-DD"
            )

    # Filtro por estado
    if estado:
        if estado not in ["abierto", "cerrado"]:
            raise HTTPException(
                status_code=400, detail="Estado inválido. Use 'abierto' o 'cerrado'"
            )
        query = query.filter(Turno.estado == estado)

    # Ordenar por fecha de apertura descendente
    query = query.order_by(Turno.fecha_apertura.desc())

    turnos = query.limit(200).all()

    # Formatear respuesta
    respuesta = []
    for turno in turnos:
        denominaciones_iniciales = []
        denominaciones_finales = []

        for d in turno.denominaciones:
            denom = DenominacionBase(
                denominacion=d.denominacion,
                cantidad=d.cantidad,
                subtotal=float(d.subtotal),
            )
            if d.tipo == "inicial":
                denominaciones_iniciales.append(denom)
            else:
                denominaciones_finales.append(denom)

        respuesta.append(
            TurnoResponse(
                id=turno.id,
                sucursal_id=turno.sucursal_id,
                usuario_id=turno.usuario_id,
                fecha_apertura=turno.fecha_apertura,
                fecha_cierre=turno.fecha_cierre,
                estado=turno.estado,
                total_inicial=float(turno.total_inicial),
                total_final=float(turno.total_final) if turno.total_final else None,
                ventas_efectivo=float(turno.ventas_efectivo) if turno.ventas_efectivo else None,
                propinas_efectivo=float(turno.propinas_efectivo)
                if turno.propinas_efectivo
                else None,
                diferencia=_get_turno_diferencia(turno),
                observaciones=turno.observaciones,
                denominaciones_iniciales=denominaciones_iniciales,
                denominaciones_finales=denominaciones_finales if denominaciones_finales else None,
                usuario_nombre=turno.usuario.nombre if turno.usuario else None,
                sucursal_nombre=turno.sucursal.nombre if turno.sucursal else None,
            )
        )

    return respuesta


@router.get("/{turno_id}", response_model=TurnoResponse)
def obtener_turno(
    turno_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    """
    Obtener detalle completo de un turno.
    """
    _validar_permisos_turnos(current_user)

    turno = _validar_turno_existente(db, turno_id)

    # Validar permisos para ver este turno
    if current_user.rol == "cajero":
        if turno.sucursal_id != current_user.sucursal_id or turno.usuario_id != current_user.id:
            raise HTTPException(status_code=403, detail="Solo puedes ver tus propios turnos")

    # Cargar relaciones
    turno = (
        db.query(Turno)
        .options(
            selectinload(Turno.denominaciones),
            selectinload(Turno.usuario),
            selectinload(Turno.sucursal),
        )
        .filter(Turno.id == turno_id)
        .first()
    )

    # Separar denominaciones
    denominaciones_iniciales = []
    denominaciones_finales = []

    for d in turno.denominaciones:
        denom = DenominacionBase(
            denominacion=d.denominacion, cantidad=d.cantidad, subtotal=float(d.subtotal)
        )
        if d.tipo == "inicial":
            denominaciones_iniciales.append(denom)
        else:
            denominaciones_finales.append(denom)

    return TurnoResponse(
        id=turno.id,
        sucursal_id=turno.sucursal_id,
        usuario_id=turno.usuario_id,
        fecha_apertura=turno.fecha_apertura,
        fecha_cierre=turno.fecha_cierre,
        estado=turno.estado,
        total_inicial=float(turno.total_inicial),
        total_final=float(turno.total_final) if turno.total_final else None,
        ventas_efectivo=float(turno.ventas_efectivo) if turno.ventas_efectivo else None,
        propinas_efectivo=float(turno.propinas_efectivo) if turno.propinas_efectivo else None,
        diferencia=_get_turno_diferencia(turno),
        observaciones=turno.observaciones,
        denominaciones_iniciales=denominaciones_iniciales,
        denominaciones_finales=denominaciones_finales if denominaciones_finales else None,
        usuario_nombre=turno.usuario.nombre if turno.usuario else None,
        sucursal_nombre=turno.sucursal.nombre if turno.sucursal else None,
    )


@router.put("/{turno_id}", response_model=TurnoResponse)
def editar_turno(
    turno_id: int,
    update_data: TurnoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    """
    Editar un turno (solo si está abierto).
    Solo puede editar el cajero que lo creó o un administrador.
    """
    _validar_permisos_turnos(current_user)

    turno = _validar_turno_existente(db, turno_id)
    _validar_puede_editar_turno(current_user, turno)

    if turno.estado == "cerrado":
        raise HTTPException(status_code=400, detail="No se puede editar un turno cerrado")

    # Actualizar observaciones si se proporcionan
    if update_data.observaciones is not None:
        turno.observaciones = update_data.observaciones

    # Actualizar conteo inicial si se proporciona
    if update_data.conteo_inicial:
        # Eliminar denominaciones iniciales existentes
        db.query(TurnoDenominacion).filter(
            TurnoDenominacion.turno_id == turno_id, TurnoDenominacion.tipo == "inicial"
        ).delete()

        # Validar nuevas denominaciones
        denominaciones_validas = {1000, 500, 200, 100, 50, 20, 10, 5, 2, 1}
        for denom in update_data.conteo_inicial.denominaciones:
            if denom.denominacion not in denominaciones_validas:
                raise HTTPException(
                    status_code=400,
                    detail=f"Denominación inválida: {denom.denominacion}",
                )
            if denom.cantidad < 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cantidad no puede ser negativa para denominación {denom.denominacion}",
                )

        # Calcular nuevo total inicial
        total_inicial = _calcular_totales_denominaciones(
            [d.dict() for d in update_data.conteo_inicial.denominaciones]
        )
        turno.total_inicial = total_inicial

        # Guardar nuevas denominaciones iniciales
        _guardar_denominaciones(
            db=db,
            turno_id=turno_id,
            tipo="inicial",
            denominaciones_data=[d.dict() for d in update_data.conteo_inicial.denominaciones],
        )

    # Actualizar conteo final si se proporciona (raro, pero posible)
    if update_data.conteo_final:
        # Eliminar denominaciones finales existentes
        db.query(TurnoDenominacion).filter(
            TurnoDenominacion.turno_id == turno_id, TurnoDenominacion.tipo == "final"
        ).delete()

        # Validar nuevas denominaciones
        denominaciones_validas = {1000, 500, 200, 100, 50, 20, 10, 5, 2, 1}
        for denom in update_data.conteo_final.denominaciones:
            if denom.denominacion not in denominaciones_validas:
                raise HTTPException(
                    status_code=400,
                    detail=f"Denominación inválida: {denom.denominacion}",
                )
            if denom.cantidad < 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cantidad no puede ser negativa para denominación {denom.denominacion}",
                )

        # Calcular nuevo total final
        total_final = _calcular_totales_denominaciones(
            [d.dict() for d in update_data.conteo_final.denominaciones]
        )
        turno.total_final = total_final

        # Guardar nuevas denominaciones finales
        _guardar_denominaciones(
            db=db,
            turno_id=turno_id,
            tipo="final",
            denominaciones_data=[d.dict() for d in update_data.conteo_final.denominaciones],
        )

        # Recalcular diferencia si ya hay ventas calculadas
        if turno.ventas_efectivo is not None and turno.propinas_efectivo is not None:
            turno.diferencia = total_final - (
                turno.total_inicial + turno.ventas_efectivo + turno.propinas_efectivo
            )

    db.commit()

    # Cargar relaciones actualizadas
    db.refresh(turno)
    turno = (
        db.query(Turno)
        .options(
            selectinload(Turno.denominaciones),
            selectinload(Turno.usuario),
            selectinload(Turno.sucursal),
        )
        .filter(Turno.id == turno_id)
        .first()
    )

    # Separar denominaciones
    denominaciones_iniciales = []
    denominaciones_finales = []

    for d in turno.denominaciones:
        denom = DenominacionBase(
            denominacion=d.denominacion, cantidad=d.cantidad, subtotal=float(d.subtotal)
        )
        if d.tipo == "inicial":
            denominaciones_iniciales.append(denom)
        else:
            denominaciones_finales.append(denom)

    return TurnoResponse(
        id=turno.id,
        sucursal_id=turno.sucursal_id,
        usuario_id=turno.usuario_id,
        fecha_apertura=turno.fecha_apertura,
        fecha_cierre=turno.fecha_cierre,
        estado=turno.estado,
        total_inicial=float(turno.total_inicial),
        total_final=float(turno.total_final) if turno.total_final else None,
        ventas_efectivo=float(turno.ventas_efectivo) if turno.ventas_efectivo else None,
        propinas_efectivo=float(turno.propinas_efectivo) if turno.propinas_efectivo else None,
        diferencia=_get_turno_diferencia(turno),
        observaciones=turno.observaciones,
        denominaciones_iniciales=denominaciones_iniciales,
        denominaciones_finales=denominaciones_finales if denominaciones_finales else None,
        usuario_nombre=turno.usuario.nombre if turno.usuario else None,
        sucursal_nombre=turno.sucursal.nombre if turno.sucursal else None,
    )


@router.get("/{turno_id}/resumen")
def obtener_resumen_turno(
    turno_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    """
    Obtener resumen detallado para mostrar en modal de cierre.
    Incluye cálculos detallados y desglose por denominación.
    """
    _validar_permisos_turnos(current_user)

    turno = _validar_turno_existente(db, turno_id)

    # Validar permisos para ver este turno
    if current_user.rol == "cajero":
        if turno.sucursal_id != current_user.sucursal_id or turno.usuario_id != current_user.id:
            raise HTTPException(status_code=403, detail="Solo puedes ver tus propios turnos")

    # Cargar relaciones
    turno = (
        db.query(Turno)
        .options(
            selectinload(Turno.denominaciones),
            selectinload(Turno.usuario),
            selectinload(Turno.sucursal),
        )
        .filter(Turno.id == turno_id)
        .first()
    )

    # Preparar desglose de denominaciones
    desglose_inicial = {}
    desglose_final = {}

    for d in turno.denominaciones:
        if d.tipo == "inicial":
            desglose_inicial[d.denominacion] = {
                "cantidad": d.cantidad,
                "subtotal": float(d.subtotal),
            }
        else:
            desglose_final[d.denominacion] = {
                "cantidad": d.cantidad,
                "subtotal": float(d.subtotal),
            }

    # Formatear respuesta de resumen
    resumen = {
        "turno_id": turno.id,
        "sucursal": turno.sucursal.nombre if turno.sucursal else "N/A",
        "cajero": turno.usuario.nombre if turno.usuario else "N/A",
        "fecha_apertura": turno.fecha_apertura.isoformat(),
        "fecha_cierre": turno.fecha_cierre.isoformat() if turno.fecha_cierre else None,
        "estado": turno.estado,
        "conteo_inicial": {
            "total": float(turno.total_inicial),
            "desglose": desglose_inicial,
        },
        "conteo_final": {
            "total": float(turno.total_final) if turno.total_final else None,
            "desglose": desglose_final if desglose_final else None,
        },
        "movimientos": {
            "ventas_efectivo": float(turno.ventas_efectivo) if turno.ventas_efectivo else None,
            "propinas_efectivo": float(turno.propinas_efectivo)
            if turno.propinas_efectivo
            else None,
        },
        "observaciones": turno.observaciones,
    }

    # Determinar rango para reporte
    fecha_inicio = turno.fecha_apertura
    fecha_fin = (
        get_mexico_now() if turno.estado == "abierto" else (turno.fecha_cierre or get_mexico_now())
    )

    # Movimientos en efectivo en el rango
    movs_info = _calcular_movimientos_efectivo(
        db=db,
        sucursal_id=turno.sucursal_id,
        fecha_apertura=fecha_inicio,
        fecha_cierre=fecha_fin,
        turno_id=turno.id,
    )

    # Comandas cobradas en efectivo durante el turno — filtradas por turno_id
    comandas = (
        db.query(Pedido)
        .options(selectinload(Pedido.usuario))
        .filter(
            Pedido.sucursal_id == turno.sucursal_id,
            Pedido.estado == "pagado",
            Pedido.metodo_pago == "efectivo",
            Pedido.fecha_pago.isnot(None),
            Pedido.turno_id == turno_id,
        )
        .order_by(Pedido.fecha_pago.asc())
        .all()
    )

    resumen["comandas_cobradas"] = [
        {
            "id": p.id,
            "numero_display": p.numero_display,
            "mesa": p.mesa,
            "nombre_cliente": p.nombre_cliente,
            "total": float(p.total),
            "propina_efectivo": float(p.propina_efectivo or 0),
            "fecha_pago": p.fecha_pago.isoformat() if p.fecha_pago else None,
            "usuario_nombre": p.usuario.nombre if p.usuario else None,
        }
        for p in comandas
    ]

    resumen["gastos_turno"] = float(movs_info["gastos"])

    total_esperado = (
        Decimal(str(turno.total_inicial))
        + movs_info["ventas_efectivo"]
        + movs_info["propinas_efectivo"]
        - movs_info["gastos"]
    )

    resumen["ventas_hasta_ahora"] = {
        "ventas_efectivo": float(movs_info["ventas_efectivo"]),
        "propinas_efectivo": float(movs_info["propinas_efectivo"]),
        "gastos": float(movs_info["gastos"]),
        "total_esperado": float(total_esperado),
    }

    return resumen
