# type: ignore
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, extract, func
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.deps import require_roles
from app.models import (
    Articulo,
    ArticuloPedido,
    CategoriaArticulo,
    Gasto,
    GastoDetalle,
    Pedido,
    Platillo,
    Proveedor,
    Turno,
    Usuario,
)
from app.utils.timezone import (
    DIAS_ES,
    HORA_CORTE_JORNADA,
    jornada_actual,
    jornada_de,
    rango_jornadas,
    semana_hidrocalida,
    to_mexico_aware,
)

router = APIRouter(prefix="/admin", tags=["administracion"])

# Una venta se fecha cuando se cobra (fecha_pago); fecha_creacion es solo respaldo
# para pagados históricos sin fecha_pago. "Día" = jornada 05:00→05:00 hora México:
# se filtra por rango [inicio, fin) y se agrupa en Python con `jornada_de` — sin
# funciones SQL de zona horaria, para que SQLite (tests) y Postgres (prod) coincidan.
VENTA_TS = func.coalesce(Pedido.fecha_pago, Pedido.fecha_creacion)
MAX_DIAS_RANGO = 731
METODOS_GASTO = ("efectivo", "tarjeta")  # enum de Gasto.metodo_pago


def _get_week_range(date_input: Optional[date] = None) -> tuple[date, date]:
    """Semana operativa Martes→Domingo; por defecto la de la jornada en curso."""
    return semana_hidrocalida(date_input or jornada_actual())


def _parse_rango(fecha_inicio: str, fecha_fin: str) -> tuple[date, date]:
    try:
        inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
        fin = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Usar YYYY-MM-DD")
    if fin < inicio:
        raise HTTPException(
            status_code=422, detail="fecha_fin no puede ser anterior a fecha_inicio"
        )
    if (fin - inicio).days >= MAX_DIAS_RANGO:
        raise HTTPException(status_code=422, detail=f"El rango máximo es de {MAX_DIAS_RANGO} días")
    return inicio, fin


def _orden_hora_jornada(hora: int) -> int:
    """Ordena las horas dentro de la jornada: 05..23 y luego 00..04."""
    return hora if hora >= HORA_CORTE_JORNADA else hora + 24


@router.get("/analytics")
def get_analytics(
    fecha_inicio: str,  # YYYY-MM-DD
    fecha_fin: str,  # YYYY-MM-DD
    metodo_pago: Optional[str] = None,  # efectivo, tarjeta, transferencia
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("administrador")),
):
    """
    Analíticas unificadas (Ventas vs Gastos) para un rango de fechas.
    Permite zoom out (diario, semanal, mensual) según el rango proporcionado por el frontend.
    Incluye métricas avanzadas (top platillos, top meseros, ventas por categoría).
    """

    start_date, end_date = _parse_rango(fecha_inicio, fecha_fin)
    inicio_dt, fin_dt = rango_jornadas(start_date, end_date)

    # Filtros base
    ventas_filters = [
        VENTA_TS >= inicio_dt,
        VENTA_TS < fin_dt,
        Pedido.estado == "pagado",
        Pedido.sucursal_id == current_user.sucursal_id,
    ]

    gastos_filters = [
        Gasto.fecha_gasto >= inicio_dt,
        Gasto.fecha_gasto < fin_dt,
        Gasto.sucursal_id == current_user.sucursal_id,
    ]

    if metodo_pago and metodo_pago != "todos":
        ventas_filters.append(Pedido.metodo_pago == metodo_pago)
        # Gasto.metodo_pago es un enum (efectivo|tarjeta): filtrar por "transferencia"
        # rompería la query. Las ventas por transferencia se comparan contra todos los gastos.
        if metodo_pago in METODOS_GASTO:
            gastos_filters.append(Gasto.metodo_pago == metodo_pago)

    # 1. Ventas (pedidos pagados) — agrupadas por jornada en Python
    ventas_rows = (
        db.query(
            VENTA_TS.label("ts"),
            Pedido.total,
            Pedido.propina_efectivo + Pedido.propina_tarjeta,
        )
        .filter(and_(*ventas_filters))
        .all()
    )

    # 2. Gastos
    gastos_rows = db.query(Gasto.fecha_gasto, Gasto.total).filter(and_(*gastos_filters)).all()

    # 3. Métodos de pago del periodo
    metodos_pago_query = (
        db.query(Pedido.metodo_pago, func.sum(Pedido.total).label("total"))
        .filter(and_(*ventas_filters))
        .group_by(Pedido.metodo_pago)
        .all()
    )

    # 4. Procesar y Unificar Datos por Fecha
    data_by_date = {}
    current = start_date
    while current <= end_date:
        data_by_date[current.isoformat()] = {
            "fecha": current.isoformat(),
            "ventas": 0.0,
            "gastos": 0.0,
            "pedidos": 0,
            "utilidad": 0.0,
        }
        current += timedelta(days=1)

    total_ventas = 0.0
    total_gastos = 0.0
    total_pedidos = 0
    total_propinas = 0.0

    # Llenar Ventas
    for ts, total, propinas in ventas_rows:
        dia = data_by_date.get(jornada_de(ts).isoformat())
        if dia is None:
            continue
        val_ventas = float(total or 0)
        dia["ventas"] += val_ventas
        dia["pedidos"] += 1
        total_ventas += val_ventas
        total_pedidos += 1
        total_propinas += float(propinas or 0)

    # Llenar Gastos
    for ts, total in gastos_rows:
        dia = data_by_date.get(jornada_de(ts).isoformat())
        if dia is None:
            continue
        val_gastos = float(total or 0)
        dia["gastos"] += val_gastos
        total_gastos += val_gastos

    # Calcular Utilidad por día
    timeline = []
    for date_key in sorted(data_by_date.keys()):
        day_data = data_by_date[date_key]
        day_data["utilidad"] = day_data["ventas"] - day_data["gastos"]
        timeline.append(day_data)

    # Resumen Métodos de Pago
    metodos_pago_data = [
        {"metodo": m.metodo_pago, "total": float(m.total or 0)} for m in metodos_pago_query
    ]

    # === ANALÍTICAS AVANZADAS (Ahora en endpoint separado, pero mantenemos compatibilidad por si acaso) ===
    # Para optimizar, si el frontend llama al endpoint nuevo, este no devuelve 'avanzado'.
    # Si el frontend viejo llama a este, calculamos 'avanzado' para no romper, o lo quitamos y obligamos a actualizar frontend.
    # Decisión: Quitamos 'avanzado' de aquí para aligerar la carga principal.

    return {
        "resumen": {
            "total_ventas": total_ventas,
            "total_gastos": total_gastos,
            "utilidad_neta": total_ventas - total_gastos,
            "total_pedidos": total_pedidos,
            "ticket_promedio": (total_ventas / total_pedidos) if total_pedidos > 0 else 0,
            "total_propinas": total_propinas,
        },
        "timeline": timeline,
        "metodos_pago": metodos_pago_data,
        "avanzado": None,  # Deprecated here, use /analytics/advanced
    }


@router.get("/analytics/advanced")
def get_analytics_advanced(
    fecha_inicio: str,  # YYYY-MM-DD
    fecha_fin: str,  # YYYY-MM-DD
    metodo_pago: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("administrador")),
):
    """
    Analíticas avanzadas separadas para optimización de carga.
    Top platillos, ventas por categoría, top meseros.
    """

    start_date, end_date = _parse_rango(fecha_inicio, fecha_fin)
    inicio_dt, fin_dt = rango_jornadas(start_date, end_date)

    ventas_filters = [
        VENTA_TS >= inicio_dt,
        VENTA_TS < fin_dt,
        Pedido.estado == "pagado",
        Pedido.sucursal_id == current_user.sucursal_id,
    ]

    if metodo_pago and metodo_pago != "todos":
        ventas_filters.append(Pedido.metodo_pago == metodo_pago)

    # Top Platillos (Cantidad y Dinero)
    top_platillos = (
        db.query(
            Platillo.nombre,
            func.sum(ArticuloPedido.cantidad).label("cantidad"),
            func.sum(ArticuloPedido.precio_cobrado).label("total_dinero"),
        )
        .join(ArticuloPedido, Platillo.id == ArticuloPedido.platillo_id)
        .join(Pedido, ArticuloPedido.pedido_id == Pedido.id)
        .filter(and_(*ventas_filters))
        .group_by(Platillo.id, Platillo.nombre)
        .order_by(func.sum(ArticuloPedido.cantidad).desc())
        .limit(10)
        .all()
    )

    # Ventas por Categoría (Para gráfico circular)
    ventas_por_categoria = (
        db.query(
            Platillo.categoria,
            func.sum(ArticuloPedido.precio_cobrado).label("total"),
        )
        .join(ArticuloPedido, Platillo.id == ArticuloPedido.platillo_id)
        .join(Pedido, ArticuloPedido.pedido_id == Pedido.id)
        .filter(and_(*ventas_filters))
        .group_by(Platillo.categoria)
        .all()
    )

    # Top Meseros (Ventas generadas)
    top_meseros = (
        db.query(
            Usuario.nombre,
            func.count(Pedido.id).label("pedidos"),
            func.sum(Pedido.total).label("total_vendido"),
        )
        .join(Pedido, Usuario.id == Pedido.usuario_id)
        .filter(and_(*ventas_filters))
        .group_by(Usuario.id, Usuario.nombre)
        .order_by(func.sum(Pedido.total).desc())
        .all()
    )

    # 1. Ventas por hora local (México), ordenadas dentro de la jornada
    horas: Dict[int, Dict[str, float]] = {}
    for ts, total in db.query(VENTA_TS, Pedido.total).filter(and_(*ventas_filters)).all():
        h = horas.setdefault(to_mexico_aware(ts).hour, {"cantidad": 0, "total": 0.0})
        h["cantidad"] += 1
        h["total"] += float(total or 0)
    ventas_por_hora = sorted(horas.items(), key=lambda kv: _orden_hora_jornada(kv[0]))

    # 2. Distribución por Tipo de Orden (Canales)
    tipos_orden = (
        db.query(
            Pedido.tipo_orden,
            func.count(Pedido.id).label("cantidad"),
            func.sum(Pedido.total).label("total"),
        )
        .filter(and_(*ventas_filters))
        .group_by(Pedido.tipo_orden)
        .all()
    )

    # 3. Desglose de Métodos de Pago
    metodos_pago = (
        db.query(
            Pedido.metodo_pago,
            func.count(Pedido.id).label("cantidad"),
            func.sum(Pedido.total).label("total"),
        )
        .filter(and_(*ventas_filters))
        .group_by(Pedido.metodo_pago)
        .all()
    )

    # 4. Eficiencia Operativa (Promedio de tiempos)
    # Nota: Usamos fecha_pago - fecha_creacion como proxy de tiempo de servicio total
    eficiencia = (
        db.query(
            func.avg(extract("epoch", Pedido.fecha_pago - Pedido.fecha_creacion)).label(
                "avg_service_time"
            )
        )
        .filter(and_(*ventas_filters, Pedido.fecha_pago != None))
        .first()
    )

    # 5. Estructura de Gastos Detallada
    gastos_filters = [
        Gasto.fecha_gasto >= inicio_dt,
        Gasto.fecha_gasto < fin_dt,
        Gasto.sucursal_id == current_user.sucursal_id,
    ]

    gastos_por_tipo = (
        db.query(Gasto.tipo_gasto, func.sum(Gasto.total).label("total"))
        .filter(and_(*gastos_filters))
        .group_by(Gasto.tipo_gasto)
        .all()
    )

    # 6. Rendimiento de Personal Adicional (Venta por pedido promedio por mesero)
    # Ya tenemos top_meseros, pero podemos añadir métricas de eficiencia si fuera necesario.

    # 7. Tasa de Cancelaciones
    cancelados_filters = [
        Pedido.fecha_creacion >= inicio_dt,
        Pedido.fecha_creacion < fin_dt,
        Pedido.estado == "cancelado",
        Pedido.sucursal_id == current_user.sucursal_id,
    ]
    total_pedidos = (
        db.query(func.count(Pedido.id))
        .filter(
            Pedido.fecha_creacion >= inicio_dt,
            Pedido.fecha_creacion < fin_dt,
            Pedido.sucursal_id == current_user.sucursal_id,
        )
        .scalar()
        or 1
    )  # Evitar división por cero

    total_cancelados = (
        db.query(func.count(Pedido.id)).filter(and_(*cancelados_filters)).scalar() or 0
    )

    return {
        "top_platillos": [
            {"nombre": p.nombre, "cantidad": int(p.cantidad), "total": float(p.total_dinero or 0)}
            for p in top_platillos
        ],
        "ventas_categoria": [
            {"categoria": c.categoria, "total": float(c.total or 0)} for c in ventas_por_categoria
        ],
        "top_meseros": [
            {"nombre": m.nombre, "pedidos": m.pedidos, "total": float(m.total_vendido or 0)}
            for m in top_meseros
        ],
        "ventas_por_hora": [
            {"hora": hora, "cantidad": int(v["cantidad"]), "total": v["total"]}
            for hora, v in ventas_por_hora
        ],
        "tipos_orden": [
            {"tipo": t.tipo_orden, "cantidad": int(t.cantidad), "total": float(t.total or 0)}
            for t in tipos_orden
        ],
        "metodos_pago_detalle": [
            {"metodo": m.metodo_pago, "cantidad": int(m.cantidad), "total": float(m.total or 0)}
            for m in metodos_pago
        ],
        "eficiencia_operativa": {
            "avg_service_time_mins": round(float(eficiencia.avg_service_time or 0) / 60, 2)
        },
        "estructura_gastos": [
            {"tipo": g.tipo_gasto, "total": float(g.total or 0)} for g in gastos_por_tipo
        ],
        "metricas_cancelacion": {
            "total_cancelados": total_cancelados,
            "total_pedidos": total_pedidos,
            "tasa_cancelacion": round((total_cancelados / total_pedidos) * 100, 2),
        },
        "proyeccion_ia": _get_predictive_sales(current_user.sucursal_id, db),
    }


def _get_predictive_sales(sucursal_id: int, db: Session) -> Dict[str, Any]:
    """
    Proyección de ventas para la PRÓXIMA SEMANA HIDROCALIDA (Martes a Domingo, 6 días
    de operación) = promedio del mismo día de la semana en las últimas 4 semanas,
    por jornada (05:00→05:00 hora México).
    """
    hoy = jornada_actual()
    # weekday(): 0=Lun, 1=Mar, ..., 6=Dom
    days_until_tuesday = (1 - hoy.weekday() + 7) % 7 or 7
    proximo_martes = hoy + timedelta(days=days_until_tuesday)

    # Una sola query: desde 4 semanas antes del primer día proyectado hasta hoy.
    desde = proximo_martes - timedelta(weeks=4)
    inicio_dt, fin_dt = rango_jornadas(
        desde, proximo_martes + timedelta(days=5) - timedelta(weeks=1)
    )
    ventas_por_jornada: Dict[date, float] = {}
    for ts, total in (
        db.query(VENTA_TS, Pedido.total)
        .filter(
            VENTA_TS >= inicio_dt,
            VENTA_TS < fin_dt,
            Pedido.estado == "pagado",
            Pedido.sucursal_id == sucursal_id,
        )
        .all()
    ):
        j = jornada_de(ts)
        ventas_por_jornada[j] = ventas_por_jornada.get(j, 0.0) + float(total or 0)

    proyecciones = []
    for i in range(6):
        dia_proyectado = proximo_martes + timedelta(days=i)
        fechas_pasadas = [dia_proyectado - timedelta(weeks=w) for w in range(1, 5)]
        esperado = sum(ventas_por_jornada.get(f, 0.0) for f in fechas_pasadas) / 4
        proyecciones.append(
            {
                "fecha": dia_proyectado.isoformat(),
                "dia": DIAS_ES[dia_proyectado.weekday()],
                "esperado": esperado,
            }
        )

    total_proyectado = sum(p["esperado"] for p in proyecciones)

    return {
        "proximos_7_dias": proyecciones,  # clave histórica; son los 6 días Mar→Dom
        "total_semana_esperado": total_proyectado,
        "confianza": "Baja (Datos históricos limitados)"
        if any(p["esperado"] == 0 for p in proyecciones)
        else "Alta (Consistencia en 4 semanas)",
    }


@router.get("/dashboard")
def get_dashboard_metrics(
    turno_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("administrador")),
):
    """Dashboard principal — métricas del turno activo (o turno_id explícito)."""

    # Determinar turno_id efectivo
    tid = turno_id
    if not tid:
        turno_activo = (
            db.query(Turno)
            .filter(Turno.sucursal_id == current_user.sucursal_id, Turno.estado == "abierto")
            .first()
        )
        tid = turno_activo.id if turno_activo else None

    jornada_hoy = jornada_actual()
    hoy_ini, hoy_fin = rango_jornadas(jornada_hoy, jornada_hoy)

    def _fp(*extra):
        """Filtro periodo: turno_id o jornada en curso + pagado + sucursal."""
        f = [Pedido.estado == "pagado", Pedido.sucursal_id == current_user.sucursal_id]
        f += list(extra)
        if tid:
            f.append(Pedido.turno_id == tid)
        else:
            f += [VENTA_TS >= hoy_ini, VENTA_TS < hoy_fin]
        return and_(*f)

    def _fp_any_estado(*estados, extra=None):
        """Filtro periodo sin restricción de estado=pagado."""
        f = [Pedido.sucursal_id == current_user.sucursal_id, Pedido.estado.in_(list(estados))]
        if extra:
            f += list(extra)
        if tid:
            f.append(Pedido.turno_id == tid)
        else:
            f += [Pedido.fecha_creacion >= hoy_ini, Pedido.fecha_creacion < hoy_fin]
        return and_(*f)

    # Consulta base
    base_query = db.query(Pedido).filter(_fp())
    total_pedidos = base_query.count()

    # Totales por método de pago
    efectivo_total = db.query(func.sum(Pedido.total)).filter(
        _fp(Pedido.metodo_pago == "efectivo")
    ).scalar() or Decimal("0.00")
    tarjeta_total = db.query(func.sum(Pedido.total)).filter(
        _fp(Pedido.metodo_pago == "tarjeta")
    ).scalar() or Decimal("0.00")
    transferencia_total = db.query(func.sum(Pedido.total)).filter(
        _fp(Pedido.metodo_pago == "transferencia")
    ).scalar() or Decimal("0.00")

    # Propinas
    propina_efectivo_total = db.query(func.sum(Pedido.propina_efectivo)).filter(
        _fp(Pedido.metodo_pago == "efectivo")
    ).scalar() or Decimal("0.00")
    propina_tarjeta_total = db.query(func.sum(Pedido.propina_tarjeta)).filter(
        _fp(Pedido.metodo_pago.in_(["tarjeta", "transferencia"]))
    ).scalar() or Decimal("0.00")
    propina_total = propina_efectivo_total + propina_tarjeta_total

    # Productos más vendidos (top 5)
    productos_vendidos = (
        db.query(Platillo.nombre, func.sum(ArticuloPedido.cantidad).label("total_vendido"))
        .join(ArticuloPedido, Platillo.id == ArticuloPedido.platillo_id)
        .join(Pedido, ArticuloPedido.pedido_id == Pedido.id)
        .filter(_fp())
        .group_by(Platillo.id, Platillo.nombre)
        .order_by(func.sum(ArticuloPedido.cantidad).desc())
        .limit(5)
        .all()
    )

    # Pedidos del turno (para lista en dashboard). selectinload evita el
    # producto cartesiano del JOIN por el wire; limit 200 como cap defensivo —
    # el dashboard muestra la lista completa del turno y los agregados vienen
    # de las otras queries.
    pedidos_del_dia = (
        db.query(Pedido)
        .options(selectinload(Pedido.articulos_pedido).selectinload(ArticuloPedido.platillo))
        .filter(_fp())
        .order_by(Pedido.fecha_creacion.desc())
        .limit(200)
        .all()
    )

    # Ticket promedio
    total_ingresos = efectivo_total + tarjeta_total + transferencia_total
    promedio_ticket = float(total_ingresos) / total_pedidos if total_pedidos > 0 else 0

    # Ventas por hora local (México), en orden de jornada
    horas: Dict[int, list] = {}
    for ts, total in db.query(VENTA_TS, Pedido.total).filter(_fp()).all():
        h = horas.setdefault(to_mexico_aware(ts).hour, [0, 0.0])
        h[0] += 1
        h[1] += float(total or 0)
    ventas_por_hora = [
        (hora, cant, tot)
        for hora, (cant, tot) in sorted(horas.items(), key=lambda kv: _orden_hora_jornada(kv[0]))
    ]

    # Tipos de orden
    tipos_orden_data = (
        db.query(Pedido.tipo_orden, func.count(Pedido.id).label("cantidad"))
        .filter(_fp())
        .group_by(Pedido.tipo_orden)
        .all()
    )

    # Cancelaciones
    cancelaciones = (
        db.query(func.count(Pedido.id)).filter(_fp_any_estado("cancelado")).scalar() or 0
    )

    # Estado actual (pedidos activos)
    estado_actual_data = (
        db.query(Pedido.estado, func.count(Pedido.id).label("cantidad"))
        .filter(
            _fp_any_estado(
                "pendiente", "preparando", "listo", "entregado", "cuenta_solicitada", "dividido"
            )
        )
        .group_by(Pedido.estado)
        .all()
    )

    periodo_label = f"turno_{tid}" if tid else jornada_hoy.isoformat()

    return {
        "fecha": periodo_label,
        "turno_id": tid,
        "total_pedidos": total_pedidos,
        "promedio_ticket": promedio_ticket,
        "cancelaciones": cancelaciones,
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
            {"hora": int(hora), "cantidad": int(cantidad), "total": float(total)}
            for hora, cantidad, total in ventas_por_hora
        ],
        "tipos_orden": [
            {"tipo": tipo, "cantidad": int(cantidad)} for tipo, cantidad in tipos_orden_data
        ],
        "estado_actual": [
            {"estado": estado, "cantidad": int(cantidad)} for estado, cantidad in estado_actual_data
        ],
        "productos_mas_vendidos": [
            {"nombre": nombre, "cantidad": int(cantidad)} for nombre, cantidad in productos_vendidos
        ],
        "pedidos_del_dia": [
            {
                "id": pedido.id,
                "numero_display": pedido.numero_display,
                "mesa": pedido.mesa,
                "nombre_cliente": pedido.nombre_cliente,
                "tipo_orden": pedido.tipo_orden,
                "total": float(pedido.total),
                "metodo_pago": pedido.metodo_pago,
                "propina_efectivo": float(pedido.propina_efectivo),
                "propina_tarjeta": float(pedido.propina_tarjeta),
                "propina_total": float(pedido.propina_efectivo + pedido.propina_tarjeta),
                "fecha_creacion": pedido.fecha_creacion.isoformat(),
                "articulos_pedido": [
                    {
                        "platillo": articulo.platillo.nombre,
                        "cantidad": articulo.cantidad,
                        "precio_cobrado": float(articulo.precio_cobrado),
                        "modificaciones": articulo.modificaciones,
                    }
                    for articulo in pedido.articulos_pedido
                ],
            }
            for pedido in pedidos_del_dia
        ],
    }


@router.get("/reportes/semanal")
def get_weekly_report(
    fecha: Optional[str] = None,  # Formato YYYY-MM-DD, cualquier día de la semana deseada
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("administrador")),
):
    """Reporte semanal (Martes a Domingo)"""

    # Parsear fecha si se proporciona
    target_date = jornada_actual()
    if fecha:
        try:
            target_date = datetime.strptime(fecha, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Formato de fecha inválido. Usar YYYY-MM-DD"
            )

    # Obtener rango de la semana
    tuesday, sunday = _get_week_range(target_date)
    inicio_dt, fin_dt = rango_jornadas(tuesday, sunday)

    # Consulta base para pedidos de la semana con estado 'pagado'
    base_query = db.query(Pedido).filter(
        and_(
            VENTA_TS >= inicio_dt,
            VENTA_TS < fin_dt,
            Pedido.estado == "pagado",
            Pedido.sucursal_id == current_user.sucursal_id,
        )
    )

    # Total pedidos de la semana
    total_pedidos = base_query.count()

    # Totales por método de pago
    efectivo_total = db.query(func.sum(Pedido.total)).filter(
        and_(
            VENTA_TS >= inicio_dt,
            VENTA_TS < fin_dt,
            Pedido.estado == "pagado",
            Pedido.metodo_pago == "efectivo",
            Pedido.sucursal_id == current_user.sucursal_id,
        )
    ).scalar() or Decimal("0.00")

    tarjeta_total = db.query(func.sum(Pedido.total)).filter(
        and_(
            VENTA_TS >= inicio_dt,
            VENTA_TS < fin_dt,
            Pedido.estado == "pagado",
            Pedido.metodo_pago == "tarjeta",
            Pedido.sucursal_id == current_user.sucursal_id,
        )
    ).scalar() or Decimal("0.00")

    transferencia_total = db.query(func.sum(Pedido.total)).filter(
        and_(
            VENTA_TS >= inicio_dt,
            VENTA_TS < fin_dt,
            Pedido.estado == "pagado",
            Pedido.metodo_pago == "transferencia",
            Pedido.sucursal_id == current_user.sucursal_id,
        )
    ).scalar() or Decimal("0.00")

    # Productos más vendidos de la semana (top 10)
    productos_vendidos = (
        db.query(Platillo.nombre, func.sum(ArticuloPedido.cantidad).label("total_vendido"))
        .join(ArticuloPedido, Platillo.id == ArticuloPedido.platillo_id)
        .join(Pedido, ArticuloPedido.pedido_id == Pedido.id)
        .filter(
            and_(
                VENTA_TS >= inicio_dt,
                VENTA_TS < fin_dt,
                Pedido.estado == "pagado",
                Pedido.sucursal_id == current_user.sucursal_id,
            )
        )
        .group_by(Platillo.id, Platillo.nombre)
        .order_by(func.sum(ArticuloPedido.cantidad).desc())
        .limit(10)
        .all()
    )

    # Ventas por día de la semana
    por_dia: Dict[date, list] = {}
    for ts, total in (
        db.query(VENTA_TS, Pedido.total)
        .filter(
            VENTA_TS >= inicio_dt,
            VENTA_TS < fin_dt,
            Pedido.estado == "pagado",
            Pedido.sucursal_id == current_user.sucursal_id,
        )
        .all()
    ):
        d = por_dia.setdefault(jornada_de(ts), [0.0, 0])
        d[0] += float(total or 0)
        d[1] += 1
    ventas_por_dia = [(f, t, n) for f, (t, n) in sorted(por_dia.items())]

    # Total de gastos de la semana
    gastos_total = db.query(func.sum(Gasto.total)).filter(
        and_(
            Gasto.fecha_gasto >= inicio_dt,
            Gasto.fecha_gasto < fin_dt,
            Gasto.sucursal_id == current_user.sucursal_id,
        )
    ).scalar() or Decimal("0.00")

    # === NUEVAS MÉTRICAS DETALLADAS ===

    # Gastos por tipo
    gastos_por_tipo = (
        db.query(Gasto.tipo_gasto, func.sum(Gasto.total).label("total"))
        .filter(
            and_(
                Gasto.fecha_gasto >= inicio_dt,
                Gasto.fecha_gasto < fin_dt,
                Gasto.sucursal_id == current_user.sucursal_id,
            )
        )
        .group_by(Gasto.tipo_gasto)
        .all()
    )

    gastos_por_proveedor = (
        db.query(Proveedor.nombre, func.sum(Gasto.total).label("total"))
        .join(Proveedor, Proveedor.id == Gasto.proveedor_id)
        .filter(
            and_(
                Gasto.fecha_gasto >= inicio_dt,
                Gasto.fecha_gasto < fin_dt,
                Gasto.sucursal_id == current_user.sucursal_id,
            )
        )
        .group_by(Proveedor.nombre)
        .all()
    )

    gastos_por_categoria_articulo = (
        db.query(CategoriaArticulo.nombre, func.sum(GastoDetalle.subtotal_linea).label("total"))
        .join(Articulo, Articulo.categoria_id == CategoriaArticulo.id)
        .join(GastoDetalle, GastoDetalle.articulo_id == Articulo.id)
        .join(Gasto, Gasto.id == GastoDetalle.gasto_id)
        .filter(
            and_(
                Gasto.fecha_gasto >= inicio_dt,
                Gasto.fecha_gasto < fin_dt,
                Gasto.sucursal_id == current_user.sucursal_id,
            )
        )
        .group_by(CategoriaArticulo.nombre)
        .all()
    )

    # Análisis por tipo de orden
    tipos_orden = (
        db.query(
            Pedido.tipo_orden,
            func.count(Pedido.id).label("cantidad"),
            func.sum(Pedido.total).label("ingresos"),
        )
        .filter(
            and_(
                VENTA_TS >= inicio_dt,
                VENTA_TS < fin_dt,
                Pedido.estado == "pagado",
                Pedido.sucursal_id == current_user.sucursal_id,
            )
        )
        .group_by(Pedido.tipo_orden)
        .all()
    )

    # Análisis de cancelaciones (todos los pedidos de la semana)
    total_pedidos_creados = (
        db.query(Pedido)
        .filter(
            and_(
                VENTA_TS >= inicio_dt,
                VENTA_TS < fin_dt,
                Pedido.sucursal_id == current_user.sucursal_id,
            )
        )
        .count()
    )

    pedidos_cancelados = (
        db.query(Pedido)
        .filter(
            and_(
                VENTA_TS >= inicio_dt,
                VENTA_TS < fin_dt,
                Pedido.estado == "cancelado",
                Pedido.sucursal_id == current_user.sucursal_id,
            )
        )
        .count()
    )

    tasa_cancelacion = (
        (pedidos_cancelados / total_pedidos_creados * 100) if total_pedidos_creados > 0 else 0
    )

    total_ingresos = efectivo_total + tarjeta_total + transferencia_total
    utilidad_bruta = total_ingresos - gastos_total
    promedio_ticket = float(total_ingresos / total_pedidos) if total_pedidos > 0 else 0

    return {
        "periodo": {
            "inicio": tuesday.isoformat(),
            "fin": sunday.isoformat(),
            "descripcion": f"Semana del {tuesday.strftime('%d/%m/%Y')} al {sunday.strftime('%d/%m/%Y')}",
        },
        "resumen": {
            "total_pedidos": total_pedidos,
            "total_pedidos_creados": total_pedidos_creados,
            "pedidos_cancelados": pedidos_cancelados,
            "tasa_cancelacion": round(tasa_cancelacion, 2),
            "promedio_ticket": round(promedio_ticket, 2),
        },
        "ingresos": {
            "efectivo": float(efectivo_total),
            "tarjeta": float(tarjeta_total),
            "transferencia": float(transferencia_total),
            "total": float(total_ingresos),
        },
        "gastos": {
            "total": float(gastos_total),
            "por_categoria": [
                {
                    "categoria": categoria,
                    "total": float(total),
                    "porcentaje": round(float(total) / float(gastos_total) * 100, 2)
                    if gastos_total > 0
                    else 0,
                }
                for categoria, total in gastos_por_tipo
            ],
            "por_proveedor": [
                {"proveedor": proveedor, "total": float(total)}
                for proveedor, total in gastos_por_proveedor
            ],
            "por_categoria_articulo": [
                {"categoria": categoria, "total": float(total)}
                for categoria, total in gastos_por_categoria_articulo
            ],
        },
        "analisis_tipos_orden": [
            {
                "tipo": tipo,
                "cantidad": int(cantidad),
                "ingresos": float(ingresos),
                "porcentaje_pedidos": round(int(cantidad) / total_pedidos * 100, 2)
                if total_pedidos > 0
                else 0,
                "porcentaje_ingresos": round(float(ingresos) / float(total_ingresos) * 100, 2)
                if total_ingresos > 0
                else 0,
            }
            for tipo, cantidad, ingresos in tipos_orden
        ],
        "utilidad_bruta": float(utilidad_bruta),
        "productos_mas_vendidos": [
            {"nombre": nombre, "cantidad": int(cantidad)} for nombre, cantidad in productos_vendidos
        ],
        "ventas_por_dia": [
            {
                "fecha": fecha.isoformat(),
                "total": float(total),
                "pedidos": int(pedidos),
                "promedio_ticket_dia": round(float(total) / int(pedidos), 2) if pedidos > 0 else 0,
            }
            for fecha, total, pedidos in ventas_por_dia
        ],
    }


@router.get("/gastos/resumen")
def get_gastos_summary(
    fecha_inicio: str = None,  # YYYY-MM-DD
    fecha_fin: str = None,  # YYYY-MM-DD
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("administrador")),
):
    """Resumen de gastos por categoría en un período"""

    # Si no se especifican fechas, usar la semana actual
    if not fecha_inicio or not fecha_fin:
        tuesday, sunday = _get_week_range()
        fecha_inicio = tuesday.isoformat()
        fecha_fin = sunday.isoformat()

    try:
        inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
        fin = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Usar YYYY-MM-DD")

    inicio_dt, fin_dt = rango_jornadas(inicio, fin)

    # Resumen por tipo de gasto
    gastos_por_tipo = (
        db.query(
            Gasto.tipo_gasto,
            func.sum(Gasto.total).label("total"),
            func.count(Gasto.id).label("cantidad"),
        )
        .filter(
            and_(
                Gasto.fecha_gasto >= inicio_dt,
                Gasto.fecha_gasto < fin_dt,
                Gasto.sucursal_id == current_user.sucursal_id,
            )
        )
        .group_by(Gasto.tipo_gasto)
        .all()
    )

    total_gastos = sum(float(total) for _, total, _ in gastos_por_tipo)

    return {
        "periodo": {"inicio": fecha_inicio, "fin": fecha_fin},
        "total_gastos": total_gastos,
        "por_categoria": [
            {
                "categoria": categoria,
                "total": float(total),
                "cantidad": int(cantidad),
                "porcentaje": round((float(total) / total_gastos * 100), 2)
                if total_gastos > 0
                else 0,
            }
            for categoria, total, cantidad in gastos_por_tipo
        ],
    }
