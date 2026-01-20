from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, cast

import pytz
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, case, extract, func, or_
from sqlalchemy.orm import Session

from app.auth import get_current_active_user
from app.core.config import settings
from app.db.session import get_db
from app.models import ArticuloPedido, Pedido, Platillo, Usuario

router = APIRouter(prefix="/reportes", tags=["reportes"])


@router.get("/dia/tickets")
def tickets_del_dia(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    """Historial de tickets del dia (pagados y cancelados) para Caja.

    - Solo cajero/administrador.
    - Pagados: filtra por fecha_pago del dia local.
    - Cancelados: filtra por fecha_creacion del dia local (no existe fecha_cancelacion).
    """

    user = cast(Any, current_user)

    if user.rol not in ["cajero", "administrador"]:
        raise HTTPException(status_code=403, detail="Solo cajeros y administradores")

    tz = pytz.timezone(settings.TIMEZONE)
    today_local = datetime.now(tz).date()
    start_dt = tz.localize(datetime.combine(today_local, datetime.min.time())).replace(tzinfo=None)
    end_dt = tz.localize(datetime.combine(today_local + timedelta(days=1), datetime.min.time())).replace(tzinfo=None)

    fecha_evento_expr = case(
        (Pedido.estado == "pagado", Pedido.fecha_pago),
        else_=Pedido.fecha_creacion,
    )

    query = db.query(Pedido).filter(
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

    pedidos = query.order_by(fecha_evento_expr.desc()).all()

    def _serialize_ticket(pedido: Pedido) -> dict[str, Any]:
        p = cast(Any, pedido)
        fecha_pago = cast(Any, p).fecha_pago
        fecha_creacion = cast(Any, p).fecha_creacion
        fecha_evento = fecha_pago if p.estado == "pagado" else fecha_creacion

        return {
            "id": p.id,
            "numero_display": p.numero_display,
            "mesa": p.mesa,
            "nombre_cliente": p.nombre_cliente,
            "estado": p.estado,
            "metodo_pago": p.metodo_pago,
            "total": float(getattr(p, "total", 0) or 0),
            "propina_efectivo": float(getattr(p, "propina_efectivo", 0) or 0),
            "propina_tarjeta": float(getattr(p, "propina_tarjeta", 0) or 0),
            "propina_total": float((getattr(p, "propina_efectivo", 0) or 0) + (getattr(p, "propina_tarjeta", 0) or 0)),
            "fecha_pago": fecha_pago.isoformat() if fecha_pago is not None else None,
            "fecha_creacion": fecha_creacion.isoformat() if fecha_creacion is not None else None,
            "fecha_evento": fecha_evento.isoformat() if fecha_evento is not None else None,
            "mesero_nombre": p.usuario_nombre,
        }

    return [_serialize_ticket(p) for p in pedidos]


@router.get("/dia/analytics")
def analytics_del_dia(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    """Analiticas del dia para Caja (mismo criterio que Admin dashboard).

    - Solo cajero/administrador.
    - Filtra por fecha_creacion (date) del dia.
    - Filtra por sucursal del usuario.
    """

    user = cast(Any, current_user)

    if user.rol not in ["cajero", "administrador"]:
        raise HTTPException(status_code=403, detail="Solo cajeros y administradores")

    today = date.today()

    # Base query: pedidos pagados del dia
    base_query = db.query(Pedido).filter(
        and_(
            func.date(Pedido.fecha_creacion) == today,
            Pedido.estado == "pagado",
            Pedido.sucursal_id == user.sucursal_id,
        )
    )

    total_pedidos = base_query.count()

    efectivo_total = (
        db.query(func.sum(Pedido.total))
        .filter(
            and_(
                func.date(Pedido.fecha_creacion) == today,
                Pedido.estado == "pagado",
                Pedido.metodo_pago == "efectivo",
                Pedido.sucursal_id == user.sucursal_id,
            )
        )
        .scalar()
        or Decimal("0.00")
    )

    tarjeta_total = (
        db.query(func.sum(Pedido.total))
        .filter(
            and_(
                func.date(Pedido.fecha_creacion) == today,
                Pedido.estado == "pagado",
                Pedido.metodo_pago == "tarjeta",
                Pedido.sucursal_id == user.sucursal_id,
            )
        )
        .scalar()
        or Decimal("0.00")
    )

    transferencia_total = (
        db.query(func.sum(Pedido.total))
        .filter(
            and_(
                func.date(Pedido.fecha_creacion) == today,
                Pedido.estado == "pagado",
                Pedido.metodo_pago == "transferencia",
                Pedido.sucursal_id == user.sucursal_id,
            )
        )
        .scalar()
        or Decimal("0.00")
    )

    # Propinas por metodo
    propina_efectivo_total = (
        db.query(func.sum(Pedido.propina_efectivo))
        .filter(
            and_(
                func.date(Pedido.fecha_creacion) == today,
                Pedido.estado == "pagado",
                Pedido.metodo_pago == "efectivo",
                Pedido.sucursal_id == user.sucursal_id,
            )
        )
        .scalar()
        or Decimal("0.00")
    )

    propina_tarjeta_total = (
        db.query(func.sum(Pedido.propina_tarjeta))
        .filter(
            and_(
                func.date(Pedido.fecha_creacion) == today,
                Pedido.estado == "pagado",
                Pedido.metodo_pago.in_(["tarjeta", "transferencia"]),
                Pedido.sucursal_id == user.sucursal_id,
            )
        )
        .scalar()
        or Decimal("0.00")
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
        .filter(
            and_(
                func.date(Pedido.fecha_creacion) == today,
                Pedido.estado == "pagado",
                Pedido.sucursal_id == user.sucursal_id,
            )
        )
        .group_by(extract("hour", Pedido.fecha_creacion))
        .order_by(extract("hour", Pedido.fecha_creacion))
        .all()
    )

    # Tipos de orden
    tipos_orden_data = (
        db.query(Pedido.tipo_orden, func.count(Pedido.id).label("cantidad"))
        .filter(
            and_(
                func.date(Pedido.fecha_creacion) == today,
                Pedido.estado == "pagado",
                Pedido.sucursal_id == user.sucursal_id,
            )
        )
        .group_by(Pedido.tipo_orden)
        .all()
    )

    # Cancelaciones
    cancelaciones = (
        db.query(func.count(Pedido.id))
        .filter(
            and_(
                func.date(Pedido.fecha_creacion) == today,
                Pedido.estado == "cancelado",
                Pedido.sucursal_id == user.sucursal_id,
            )
        )
        .scalar()
        or 0
    )

    # Estado actual (operativo)
    estados_operativos = [
        "pendiente",
        "preparando",
        "listo",
        "entregado",
        "cuenta_solicitada",
        "dividido",
    ]
    estado_actual_data = (
        db.query(Pedido.estado, func.count(Pedido.id).label("cantidad"))
        .filter(
            and_(
                func.date(Pedido.fecha_creacion) == today,
                Pedido.estado.in_(estados_operativos),
                Pedido.sucursal_id == user.sucursal_id,
            )
        )
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
        .filter(
            and_(
                func.date(Pedido.fecha_creacion) == today,
                Pedido.estado == "pagado",
                Pedido.sucursal_id == user.sucursal_id,
            )
        )
        .group_by(Platillo.id, Platillo.nombre)
        .order_by(func.sum(ArticuloPedido.cantidad).desc())
        .limit(5)
        .all()
    )

    return {
        "fecha": today.isoformat(),
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
