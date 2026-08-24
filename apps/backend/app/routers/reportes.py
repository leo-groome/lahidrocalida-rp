from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Optional, cast

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, case, extract, func, or_
from sqlalchemy.orm import Session

from app.auth import get_current_active_user
from app.core.config import settings
from app.db.session import get_db
from app.models import ArticuloPedido, Pedido, Platillo, Turno, Usuario
from app.utils.timezone import get_mexico_now, MEXICO_TZ

router = APIRouter(prefix="/reportes", tags=["reportes"])


@router.get("/dia/tickets")
def tickets_del_dia(
    turno_id: Optional[int] = None,
    # Default alto a propósito: CajaView calcula los totales del cierre de
    # caja sumando estos tickets sin paginar — truncar corrompe las cifras.
    # El limit es un cap defensivo, no paginación por default.
    limit: int = Query(1000, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    """Historial de tickets del turno actual (pagados y cancelados) para Caja.

    - Solo cajero/administrador.
    - Con turno_id: filtra por turno.
    - Sin turno_id: usa el turno activo; fallback a fecha del día.
    """

    user = cast(Any, current_user)

    if user.rol not in ["cajero", "administrador"]:
        raise HTTPException(status_code=403, detail="Solo cajeros y administradores")

    fecha_evento_expr = case(
        (Pedido.estado == "pagado", Pedido.fecha_pago),
        else_=Pedido.fecha_creacion,
    )

    # Determinar filtro: turno o fecha
    tid = turno_id
    if not tid:
        turno_activo = db.query(Turno).filter(
            Turno.sucursal_id == user.sucursal_id,
            Turno.estado == "abierto"
        ).first()
        tid = turno_activo.id if turno_activo else None

    # Proyección de columnas: evita traer el modelo completo y el N+1 de
    # usuario_nombre (property que lazy-loadea Pedido.usuario por fila)
    query = db.query(
        Pedido.id,
        Pedido.numero_display,
        Pedido.mesa,
        Pedido.nombre_cliente,
        Pedido.estado,
        Pedido.metodo_pago,
        Pedido.total,
        Pedido.propina_efectivo,
        Pedido.propina_tarjeta,
        Pedido.fecha_pago,
        Pedido.fecha_creacion,
        Pedido.tipo_orden,
        Usuario.nombre.label("mesero_nombre"),
    ).outerjoin(Usuario, Pedido.usuario_id == Usuario.id)

    if tid:
        query = query.filter(
            Pedido.turno_id == tid,
            Pedido.estado.in_(["pagado", "cancelado"]),
        )
    else:
        # Fallback: fecha del día
        now_local = get_mexico_now()
        today_local = now_local.date()
        start_dt = datetime.combine(today_local, datetime.min.time(), tzinfo=MEXICO_TZ)
        end_dt = datetime.combine(today_local + timedelta(days=1), datetime.min.time(), tzinfo=MEXICO_TZ)
        query = query.filter(
            or_(
                and_(
                    Pedido.estado == "pagado",
                    Pedido.fecha_pago.isnot(None),
                    Pedido.fecha_pago >= start_dt,
                    Pedido.fecha_pago < end_dt,
                ),
                and_(
                    Pedido.estado == "cancelado",
                    Pedido.fecha_creacion >= start_dt,
                    Pedido.fecha_creacion < end_dt,
                ),
            )
        )

    if user.rol == "cajero":
        query = query.filter(Pedido.sucursal_id == user.sucursal_id)

    rows = query.order_by(fecha_evento_expr.desc()).limit(limit).offset(offset).all()

    def _serialize_ticket(row: Any) -> dict[str, Any]:
        fecha_evento = row.fecha_pago if row.estado == "pagado" else row.fecha_creacion

        return {
            "id": row.id,
            "numero_display": row.numero_display,
            "mesa": row.mesa,
            "nombre_cliente": row.nombre_cliente,
            "estado": row.estado,
            "metodo_pago": row.metodo_pago,
            "total": float(row.total or 0),
            "propina_efectivo": float(row.propina_efectivo or 0),
            "propina_tarjeta": float(row.propina_tarjeta or 0),
            "propina_total": float((row.propina_efectivo or 0) + (row.propina_tarjeta or 0)),
            "fecha_pago": row.fecha_pago.isoformat() if row.fecha_pago is not None else None,
            "fecha_creacion": row.fecha_creacion.isoformat() if row.fecha_creacion is not None else None,
            "fecha_evento": fecha_evento.isoformat() if fecha_evento is not None else None,
            "mesero_nombre": row.mesero_nombre,
            "tipo_orden": row.tipo_orden,
        }

    return [_serialize_ticket(r) for r in rows]


@router.get("/dia/analytics")
def analytics_del_dia(
    turno_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    """Analíticas del turno actual para Caja.

    - Solo cajero/administrador.
    - Con turno_id: filtra por turno.
    - Sin turno_id: usa el turno activo; fallback a fecha del día.
    """

    user = cast(Any, current_user)

    if user.rol not in ["cajero", "administrador"]:
        raise HTTPException(status_code=403, detail="Solo cajeros y administradores")

    # Determinar filtro turno vs fecha
    tid = turno_id
    if not tid:
        turno_activo = db.query(Turno).filter(
            Turno.sucursal_id == user.sucursal_id,
            Turno.estado == "abierto"
        ).first()
        tid = turno_activo.id if turno_activo else None

    def _filtro_periodo(extra_filters=None):
        """Construye los filtros de periodo (turno o fecha) + estado pagado + sucursal."""
        filters = [Pedido.estado == "pagado", Pedido.sucursal_id == user.sucursal_id]
        if tid:
            filters.append(Pedido.turno_id == tid)
        else:
            now_local = get_mexico_now()
            today = now_local.date()
            start_dt = datetime.combine(today, datetime.min.time(), tzinfo=MEXICO_TZ)
            end_dt = datetime.combine(today + timedelta(days=1), datetime.min.time(), tzinfo=MEXICO_TZ)
            filters += [Pedido.fecha_creacion >= start_dt, Pedido.fecha_creacion < end_dt]
        if extra_filters:
            filters += extra_filters
        return and_(*filters)

    # Base query: pedidos pagados del turno/dia
    base_query = db.query(Pedido).filter(_filtro_periodo())

    total_pedidos = base_query.count()

    efectivo_total = (
        db.query(func.sum(Pedido.total))
        .filter(_filtro_periodo([Pedido.metodo_pago == "efectivo"]))
        .scalar() or Decimal("0.00")
    )

    tarjeta_total = (
        db.query(func.sum(Pedido.total))
        .filter(_filtro_periodo([Pedido.metodo_pago == "tarjeta"]))
        .scalar() or Decimal("0.00")
    )

    transferencia_total = (
        db.query(func.sum(Pedido.total))
        .filter(_filtro_periodo([Pedido.metodo_pago == "transferencia"]))
        .scalar() or Decimal("0.00")
    )

    # Propinas por metodo
    propina_efectivo_total = (
        db.query(func.sum(Pedido.propina_efectivo))
        .filter(_filtro_periodo([Pedido.metodo_pago == "efectivo"]))
        .scalar() or Decimal("0.00")
    )

    propina_tarjeta_total = (
        db.query(func.sum(Pedido.propina_tarjeta))
        .filter(_filtro_periodo([Pedido.metodo_pago.in_(["tarjeta", "transferencia"])]))
        .scalar() or Decimal("0.00")
    )

    propina_total = propina_efectivo_total + propina_tarjeta_total

    # Ticket promedio
    total_ingresos = efectivo_total + tarjeta_total + transferencia_total
    promedio_ticket = float(total_ingresos) / total_pedidos if total_pedidos > 0 else 0

    # Ventas por hora
    ventas_por_hora = (
        db.query(
            extract("hour", Pedido.fecha_creacion).label("hora"),
            func.count(Pedido.id).label("cantidad"),
            func.sum(Pedido.total).label("total"),
        )
        .filter(_filtro_periodo())
        .group_by(extract("hour", Pedido.fecha_creacion))
        .order_by(extract("hour", Pedido.fecha_creacion))
        .all()
    )

    # Tipos de orden
    tipos_orden_data = (
        db.query(Pedido.tipo_orden, func.count(Pedido.id).label("cantidad"))
        .filter(_filtro_periodo())
        .group_by(Pedido.tipo_orden)
        .all()
    )

    # Cancelaciones (no pagado, usa filtro de periodo sin estado=pagado)
    def _filtro_cancelaciones():
        filters = [Pedido.estado == "cancelado", Pedido.sucursal_id == user.sucursal_id]
        if tid:
            filters.append(Pedido.turno_id == tid)
        else:
            now_local = get_mexico_now()
            today = now_local.date()
            start_dt = datetime.combine(today, datetime.min.time(), tzinfo=MEXICO_TZ)
            end_dt = datetime.combine(today + timedelta(days=1), datetime.min.time(), tzinfo=MEXICO_TZ)
            filters += [Pedido.fecha_creacion >= start_dt, Pedido.fecha_creacion < end_dt]
        return and_(*filters)

    cancelaciones = (
        db.query(func.count(Pedido.id))
        .filter(_filtro_cancelaciones())
        .scalar() or 0
    )

    # Estado actual (operativo) — no filtra por estado=pagado
    estados_operativos = ["pendiente", "preparando", "listo", "entregado", "cuenta_solicitada", "dividido"]

    def _filtro_operativos():
        filters = [Pedido.estado.in_(estados_operativos), Pedido.sucursal_id == user.sucursal_id]
        if tid:
            filters.append(Pedido.turno_id == tid)
        else:
            now_local = get_mexico_now()
            today = now_local.date()
            start_dt = datetime.combine(today, datetime.min.time(), tzinfo=MEXICO_TZ)
            end_dt = datetime.combine(today + timedelta(days=1), datetime.min.time(), tzinfo=MEXICO_TZ)
            filters += [Pedido.fecha_creacion >= start_dt, Pedido.fecha_creacion < end_dt]
        return and_(*filters)

    estado_actual_data = (
        db.query(Pedido.estado, func.count(Pedido.id).label("cantidad"))
        .filter(_filtro_operativos())
        .group_by(Pedido.estado)
        .all()
    )

    # Productos mas vendidos (top 5)
    productos_vendidos = (
        db.query(
            Platillo.nombre,
            func.sum(ArticuloPedido.cantidad).label("total_vendido"),
        )
        .join(ArticuloPedido, Platillo.id == ArticuloPedido.platillo_id)
        .join(Pedido, ArticuloPedido.pedido_id == Pedido.id)
        .filter(_filtro_periodo())
        .group_by(Platillo.id, Platillo.nombre)
        .order_by(func.sum(ArticuloPedido.cantidad).desc())
        .limit(5)
        .all()
    )

    # Determinar etiqueta de fecha/turno para la respuesta
    periodo_label = f"turno_{tid}" if tid else get_mexico_now().date().isoformat()

    return {
        "fecha": periodo_label,
        "turno_id": tid,
        "total_pedidos": total_pedidos,
        "promedio_ticket": promedio_ticket,
        "cancelaciones": int(cancelaciones),
        "ingresos": {
            "efectivo": float(efectivo_total),
            "tarjeta": float(tarjeta_total),
            "transferencia": float(transferencia_total),
            "total": float(total_ingresos),
        },
        "propinas": {
            "efectivo": float(propina_efectivo_total),
            "tarjeta": float(propina_tarjeta_total),
            "total": float(propina_total),
        },
        "ventas_por_hora": [
            {"hora": int(hora), "cantidad": int(cantidad), "total": float(total or 0)}
            for hora, cantidad, total in ventas_por_hora
        ],
        "tipos_orden": [
            {"tipo": tipo, "cantidad": int(cantidad)} for tipo, cantidad in tipos_orden_data
        ],
        "estado_actual": [
            {"estado": estado, "cantidad": int(cantidad)}
            for estado, cantidad in estado_actual_data
        ],
        "productos_mas_vendidos": [
            {"nombre": nombre, "cantidad": int(cantidad)}
            for nombre, cantidad in productos_vendidos
        ],
    }
