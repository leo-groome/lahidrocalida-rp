# type: ignore
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, extract
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
from decimal import Decimal

from app.db.session import get_db
from app.models import (
    Usuario,
    Pedido,
    ArticuloPedido,
    Platillo,
    Gasto,
    Proveedor,
    CategoriaArticulo,
    GastoDetalle,
    Articulo,
)
from app.auth import get_current_active_user

router = APIRouter(prefix="/admin", tags=["administracion"])


def _ensure_admin_access(user: Usuario) -> None:
    """Verificar que el usuario sea administrador"""
    if user.rol != "administrador":
        raise HTTPException(status_code=403, detail="Acceso solo para administradores")


def _get_week_range(date_input: Optional[date] = None) -> tuple[date, date]:
    """
    Obtener el rango de fechas de la semana (Martes a Domingo)
    Si no se proporciona fecha, usar la semana actual
    """
    if date_input is None:
        date_input = date.today()
    
    # Encontrar el martes de esta semana
    days_since_tuesday = (date_input.weekday() - 1) % 7
    tuesday = date_input - timedelta(days=days_since_tuesday)
    
    # El domingo es 6 días después del martes
    sunday = tuesday + timedelta(days=6)
    
    return tuesday, sunday



@router.get("/analytics")
def get_analytics(
    fecha_inicio: str,  # YYYY-MM-DD
    fecha_fin: str,     # YYYY-MM-DD
    metodo_pago: Optional[str] = None, # efectivo, tarjeta, transferencia
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    """
    Analíticas unificadas (Ventas vs Gastos) para un rango de fechas.
    Permite zoom out (diario, semanal, mensual) según el rango proporcionado por el frontend.
    Incluye métricas avanzadas (top platillos, top meseros, ventas por categoría).
    """
    _ensure_admin_access(current_user)

    try:
        start_date = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
        end_date = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Usar YYYY-MM-DD")

    # Filtros base
    ventas_filters = [
        func.date(Pedido.fecha_creacion) >= start_date,
        func.date(Pedido.fecha_creacion) <= end_date,
        Pedido.estado == "pagado",
        Pedido.sucursal_id == current_user.sucursal_id
    ]
    
    gastos_filters = [
        func.date(Gasto.fecha_gasto) >= start_date,
        func.date(Gasto.fecha_gasto) <= end_date,
        Gasto.sucursal_id == current_user.sucursal_id
    ]

    # Aplicar filtro de método de pago si existe
    if metodo_pago and metodo_pago != 'todos':
        if metodo_pago in ['tarjeta', 'transferencia']:
             # Para simplificar, a veces tarjeta y transferencia se agrupan, pero aquí seremos estrictos si el frontend lo manda separado
             # O si el frontend manda 'tarjeta' para ambos, ajustar. Asumimos valor exacto de la DB.
             ventas_filters.append(Pedido.metodo_pago == metodo_pago)
             gastos_filters.append(Gasto.metodo_pago == metodo_pago)
        else:
             ventas_filters.append(Pedido.metodo_pago == metodo_pago)
             gastos_filters.append(Gasto.metodo_pago == metodo_pago)

    # 1. Ventas (Pedidos Pagados)
    ventas_query = db.query(
        func.date(Pedido.fecha_creacion).label('fecha'),
        func.sum(Pedido.total).label('total_ventas'),
        func.count(Pedido.id).label('cantidad_pedidos'),
        func.sum(Pedido.propina_efectivo + Pedido.propina_tarjeta).label('total_propinas')
    ).filter(and_(*ventas_filters)).group_by(func.date(Pedido.fecha_creacion)).all()

    # 2. Gastos
    gastos_query = db.query(
        func.date(Gasto.fecha_gasto).label('fecha'),
        func.sum(Gasto.total).label('total_gastos')
    ).filter(and_(*gastos_filters)).group_by(func.date(Gasto.fecha_gasto)).all()

    # 3. Métodos de Pago (Resumen del periodo) - Ignora el filtro de metodo_pago para mostrar el panorama completo si no se filtra, 
    # o mostrar solo el seleccionado si se filtra (lo cual es redundante pero consistente).
    # Mejor: Mostrar siempre el desglose completo para contexto, a menos que sea confuso.
    # Decisión: Si el usuario filtra por "Efectivo", ver "Tarjeta: 0" es correcto.
    metodos_pago_query = db.query(
        Pedido.metodo_pago,
        func.sum(Pedido.total).label('total')
    ).filter(and_(*ventas_filters)).group_by(Pedido.metodo_pago).all()

    # 4. Procesar y Unificar Datos por Fecha
    data_by_date = {}
    current = start_date
    while current <= end_date:
        data_by_date[current.isoformat()] = {
            "fecha": current.isoformat(),
            "ventas": 0.0,
            "gastos": 0.0,
            "pedidos": 0,
            "utilidad": 0.0
        }
        current += timedelta(days=1)

    total_ventas = 0.0
    total_gastos = 0.0
    total_pedidos = 0
    total_propinas = 0.0

    # Llenar Ventas
    for v in ventas_query:
        f_str = v.fecha.isoformat()
        if f_str in data_by_date:
            val_ventas = float(v.total_ventas or 0)
            data_by_date[f_str]["ventas"] = val_ventas
            data_by_date[f_str]["pedidos"] = v.cantidad_pedidos
            total_ventas += val_ventas
            total_pedidos += v.cantidad_pedidos
            total_propinas += float(v.total_propinas or 0)

    # Llenar Gastos
    for g in gastos_query:
        f_str = g.fecha.isoformat()
        if f_str in data_by_date:
            val_gastos = float(g.total_gastos or 0)
            data_by_date[f_str]["gastos"] = val_gastos
            total_gastos += val_gastos

    # Calcular Utilidad por día
    timeline = []
    for date_key in sorted(data_by_date.keys()):
        day_data = data_by_date[date_key]
        day_data["utilidad"] = day_data["ventas"] - day_data["gastos"]
        timeline.append(day_data)

    # Resumen Métodos de Pago
    metodos_pago_data = [
        {"metodo": m.metodo_pago, "total": float(m.total or 0)} 
        for m in metodos_pago_query
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
            "total_propinas": total_propinas
        },
        "timeline": timeline,
        "metodos_pago": metodos_pago_data,
        "avanzado": None # Deprecated here, use /analytics/advanced
    }


@router.get("/analytics/advanced")
def get_analytics_advanced(
    fecha_inicio: str,  # YYYY-MM-DD
    fecha_fin: str,     # YYYY-MM-DD
    metodo_pago: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    """
    Analíticas avanzadas separadas para optimización de carga.
    Top platillos, ventas por categoría, top meseros.
    """
    _ensure_admin_access(current_user)

    try:
        start_date = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
        end_date = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Usar YYYY-MM-DD")

    ventas_filters = [
        func.date(Pedido.fecha_creacion) >= start_date,
        func.date(Pedido.fecha_creacion) <= end_date,
        Pedido.estado == "pagado",
        Pedido.sucursal_id == current_user.sucursal_id
    ]

    if metodo_pago and metodo_pago != 'todos':
        ventas_filters.append(Pedido.metodo_pago == metodo_pago)

    # Top Platillos (Cantidad y Dinero)
    top_platillos = db.query(
        Platillo.nombre,
        func.sum(ArticuloPedido.cantidad).label('cantidad'),
        func.sum(ArticuloPedido.cantidad * ArticuloPedido.precio_cobrado).label('total_dinero')
    ).join(ArticuloPedido, Platillo.id == ArticuloPedido.platillo_id)\
     .join(Pedido, ArticuloPedido.pedido_id == Pedido.id)\
     .filter(and_(*ventas_filters))\
     .group_by(Platillo.id, Platillo.nombre)\
     .order_by(func.sum(ArticuloPedido.cantidad).desc())\
     .limit(10).all()

    # Ventas por Categoría (Para gráfico circular)
    ventas_por_categoria = db.query(
        Platillo.categoria,
        func.sum(ArticuloPedido.cantidad * ArticuloPedido.precio_cobrado).label('total')
    ).join(ArticuloPedido, Platillo.id == ArticuloPedido.platillo_id)\
     .join(Pedido, ArticuloPedido.pedido_id == Pedido.id)\
     .filter(and_(*ventas_filters))\
     .group_by(Platillo.categoria).all()

    # Top Meseros (Ventas generadas)
    top_meseros = db.query(
        Usuario.nombre,
        func.count(Pedido.id).label('pedidos'),
        func.sum(Pedido.total).label('total_vendido')
    ).join(Pedido, Usuario.id == Pedido.usuario_id)\
     .filter(and_(*ventas_filters))\
     .group_by(Usuario.id, Usuario.nombre)\
     .order_by(func.sum(Pedido.total).desc()).all()

    return {
        "top_platillos": [
            {
                "nombre": p.nombre, 
                "cantidad": int(p.cantidad), 
                "total": float(p.total_dinero or 0)
            } for p in top_platillos
        ],
        "ventas_categoria": [
            {"categoria": c.categoria, "total": float(c.total or 0)}
            for c in ventas_por_categoria
        ],
        "top_meseros": [
            {"nombre": m.nombre, "pedidos": m.pedidos, "total": float(m.total_vendido or 0)}
            for m in top_meseros
        ]
    }


@router.get("/dashboard")
def get_dashboard_metrics(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    """Dashboard principal - métricas del día actual"""
    _ensure_admin_access(current_user)
    
    today = date.today()
    
    # Consulta base para pedidos del día actual con estado 'pagado'
    base_query = db.query(Pedido).filter(
        and_(
            func.date(Pedido.fecha_creacion) == today,
            Pedido.estado == "pagado",
            Pedido.sucursal_id == current_user.sucursal_id
        )
    )
    
    # Total pedidos del día
    total_pedidos = base_query.count()
    
    # Total por método de pago
    efectivo_total = db.query(func.sum(Pedido.total)).filter(
        and_(
            func.date(Pedido.fecha_creacion) == today,
            Pedido.estado == "pagado",
            Pedido.metodo_pago == "efectivo",
            Pedido.sucursal_id == current_user.sucursal_id
        )
    ).scalar() or Decimal('0.00')
    
    tarjeta_total = db.query(func.sum(Pedido.total)).filter(
        and_(
            func.date(Pedido.fecha_creacion) == today,
            Pedido.estado == "pagado",
            Pedido.metodo_pago == "tarjeta",
            Pedido.sucursal_id == current_user.sucursal_id
        )
    ).scalar() or Decimal('0.00')
    
    transferencia_total = db.query(func.sum(Pedido.total)).filter(
        and_(
            func.date(Pedido.fecha_creacion) == today,
            Pedido.estado == "pagado",
            Pedido.metodo_pago == "transferencia",
            Pedido.sucursal_id == current_user.sucursal_id
        )
    ).scalar() or Decimal('0.00')

    # Propinas por método de pago
    propina_efectivo_total = db.query(func.sum(Pedido.propina_efectivo)).filter(
        and_(
            func.date(Pedido.fecha_creacion) == today,
            Pedido.estado == "pagado",
            Pedido.metodo_pago == "efectivo",
            Pedido.sucursal_id == current_user.sucursal_id
        )
    ).scalar() or Decimal('0.00')
    
    propina_tarjeta_total = db.query(func.sum(Pedido.propina_tarjeta)).filter(
        and_(
            func.date(Pedido.fecha_creacion) == today,
            Pedido.estado == "pagado",
            Pedido.metodo_pago.in_(['tarjeta', 'transferencia']),
            Pedido.sucursal_id == current_user.sucursal_id
        )
    ).scalar() or Decimal('0.00')
    
    propina_total = propina_efectivo_total + propina_tarjeta_total

    # Productos más vendidos (top 5)
    productos_vendidos = db.query(
        Platillo.nombre,
        func.sum(ArticuloPedido.cantidad).label('total_vendido')
    ).join(
        ArticuloPedido, Platillo.id == ArticuloPedido.platillo_id
    ).join(
        Pedido, ArticuloPedido.pedido_id == Pedido.id
    ).filter(
        and_(
            func.date(Pedido.fecha_creacion) == today,
            Pedido.estado == "pagado",
            Pedido.sucursal_id == current_user.sucursal_id
        )
    ).group_by(
        Platillo.id, Platillo.nombre
    ).order_by(
        func.sum(ArticuloPedido.cantidad).desc()
    ).limit(5).all()

    # Pedidos del día (para la lista en dashboard)
    pedidos_del_dia = db.query(Pedido).options(
        joinedload(Pedido.articulos_pedido).joinedload(ArticuloPedido.platillo)
    ).filter(
        and_(
            func.date(Pedido.fecha_creacion) == today,
            Pedido.estado == "pagado",
            Pedido.sucursal_id == current_user.sucursal_id
        )
    ).order_by(Pedido.fecha_creacion.desc()).all()

     # Ticket promedio
    total_ingresos = efectivo_total + tarjeta_total + transferencia_total
    promedio_ticket = float(total_ingresos) / total_pedidos if total_pedidos > 0 else 0

    # Ventas por hora
    ventas_por_hora = db.query(
        extract('hour', Pedido.fecha_creacion).label('hora'),
        func.count(Pedido.id).label('cantidad'),
        func.sum(Pedido.total).label('total')
    ).filter(
        and_(
            func.date(Pedido.fecha_creacion) == today,
            Pedido.estado == "pagado",
            Pedido.sucursal_id == current_user.sucursal_id
        )
    ).group_by(extract('hour', Pedido.fecha_creacion)).order_by(extract('hour', Pedido.fecha_creacion)).all()

    # Tipos de orden
    tipos_orden_data = db.query(
        Pedido.tipo_orden,
        func.count(Pedido.id).label('cantidad')
    ).filter(
        and_(
            func.date(Pedido.fecha_creacion) == today,
            Pedido.estado == "pagado",
            Pedido.sucursal_id == current_user.sucursal_id
        )
    ).group_by(Pedido.tipo_orden).all()

    # Cancelaciones
    cancelaciones = db.query(func.count(Pedido.id)).filter(
        and_(
            func.date(Pedido.fecha_creacion) == today,
            Pedido.estado == "cancelado",
            Pedido.sucursal_id == current_user.sucursal_id
        )
    ).scalar() or 0

    # Estado actual (Pedidos activos)
    estado_actual_data = db.query(
        Pedido.estado,
        func.count(Pedido.id).label('cantidad')
    ).filter(
        and_(
            func.date(Pedido.fecha_creacion) == today,
            Pedido.estado.in_(['pendiente', 'preparando', 'listo', 'entregado', 'cuenta_solicitada', 'dividido']),
            Pedido.sucursal_id == current_user.sucursal_id
        )
    ).group_by(Pedido.estado).all()
    
    return {
        "fecha": today.isoformat(),
        "total_pedidos": total_pedidos,
        "promedio_ticket": promedio_ticket,
        "cancelaciones": cancelaciones,
        "ingresos": {
            "efectivo": float(efectivo_total),
            "tarjeta": float(tarjeta_total),
            "transferencia": float(transferencia_total),
            "total": float(total_ingresos)
        },
        "propinas": {
            "efectivo": float(propina_efectivo_total),
            "tarjeta": float(propina_tarjeta_total),
            "total": float(propina_total)
        },
        "ventas_por_hora": [
            {"hora": int(hora), "cantidad": int(cantidad), "total": float(total)}
            for hora, cantidad, total in ventas_por_hora
        ],
        "tipos_orden": [
            {"tipo": tipo, "cantidad": int(cantidad)}
            for tipo, cantidad in tipos_orden_data
        ],
        "estado_actual": [
            {"estado": estado, "cantidad": int(cantidad)}
            for estado, cantidad in estado_actual_data
        ],
        "productos_mas_vendidos": [
            {"nombre": nombre, "cantidad": int(cantidad)}
            for nombre, cantidad in productos_vendidos
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
                        "modificaciones": articulo.modificaciones
                    }
                    for articulo in pedido.articulos_pedido
                ]
            }
            for pedido in pedidos_del_dia
        ]
    }


@router.get("/reportes/semanal")
def get_weekly_report(
    fecha: Optional[str] = None,  # Formato YYYY-MM-DD, cualquier día de la semana deseada
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    """Reporte semanal (Martes a Domingo)"""
    _ensure_admin_access(current_user)
    
    # Parsear fecha si se proporciona
    target_date = date.today()
    if fecha:
        try:
            target_date = datetime.strptime(fecha, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha inválido. Usar YYYY-MM-DD")
    
    # Obtener rango de la semana
    tuesday, sunday = _get_week_range(target_date)
    
    # Consulta base para pedidos de la semana con estado 'pagado'
    base_query = db.query(Pedido).filter(
        and_(
            func.date(Pedido.fecha_creacion) >= tuesday,
            func.date(Pedido.fecha_creacion) <= sunday,
            Pedido.estado == "pagado",
            Pedido.sucursal_id == current_user.sucursal_id
        )
    )
    
    # Total pedidos de la semana
    total_pedidos = base_query.count()
    
    # Totales por método de pago
    efectivo_total = db.query(func.sum(Pedido.total)).filter(
        and_(
            func.date(Pedido.fecha_creacion) >= tuesday,
            func.date(Pedido.fecha_creacion) <= sunday,
            Pedido.estado == "pagado",
            Pedido.metodo_pago == "efectivo",
            Pedido.sucursal_id == current_user.sucursal_id
        )
    ).scalar() or Decimal('0.00')
    
    tarjeta_total = db.query(func.sum(Pedido.total)).filter(
        and_(
            func.date(Pedido.fecha_creacion) >= tuesday,
            func.date(Pedido.fecha_creacion) <= sunday,
            Pedido.estado == "pagado",
            Pedido.metodo_pago == "tarjeta",
            Pedido.sucursal_id == current_user.sucursal_id
        )
    ).scalar() or Decimal('0.00')
    
    transferencia_total = db.query(func.sum(Pedido.total)).filter(
        and_(
            func.date(Pedido.fecha_creacion) >= tuesday,
            func.date(Pedido.fecha_creacion) <= sunday,
            Pedido.estado == "pagado",
            Pedido.metodo_pago == "transferencia",
            Pedido.sucursal_id == current_user.sucursal_id
        )
    ).scalar() or Decimal('0.00')
    
    # Productos más vendidos de la semana (top 10)
    productos_vendidos = db.query(
        Platillo.nombre,
        func.sum(ArticuloPedido.cantidad).label('total_vendido')
    ).join(
        ArticuloPedido, Platillo.id == ArticuloPedido.platillo_id
    ).join(
        Pedido, ArticuloPedido.pedido_id == Pedido.id
    ).filter(
        and_(
            func.date(Pedido.fecha_creacion) >= tuesday,
            func.date(Pedido.fecha_creacion) <= sunday,
            Pedido.estado == "pagado",
            Pedido.sucursal_id == current_user.sucursal_id
        )
    ).group_by(
        Platillo.id, Platillo.nombre
    ).order_by(
        func.sum(ArticuloPedido.cantidad).desc()
    ).limit(10).all()
    
    # Ventas por día de la semana
    ventas_por_dia = db.query(
        func.date(Pedido.fecha_creacion).label('fecha'),
        func.sum(Pedido.total).label('total_dia'),
        func.count(Pedido.id).label('pedidos_dia')
    ).filter(
        and_(
            func.date(Pedido.fecha_creacion) >= tuesday,
            func.date(Pedido.fecha_creacion) <= sunday,
            Pedido.estado == "pagado",
            Pedido.sucursal_id == current_user.sucursal_id
        )
    ).group_by(
        func.date(Pedido.fecha_creacion)
    ).order_by(
        func.date(Pedido.fecha_creacion)
    ).all()
    
    # Total de gastos de la semana
    gastos_total = db.query(func.sum(Gasto.total)).filter(
        and_(
            func.date(Gasto.fecha_gasto) >= tuesday,
            func.date(Gasto.fecha_gasto) <= sunday,
            Gasto.sucursal_id == current_user.sucursal_id
        )
    ).scalar() or Decimal('0.00')
    
    # === NUEVAS MÉTRICAS DETALLADAS ===
    
    # Gastos por tipo
    gastos_por_tipo = db.query(
        Gasto.tipo_gasto,
        func.sum(Gasto.total).label('total')
    ).filter(
        and_(
            func.date(Gasto.fecha_gasto) >= tuesday,
            func.date(Gasto.fecha_gasto) <= sunday,
            Gasto.sucursal_id == current_user.sucursal_id
        )
    ).group_by(Gasto.tipo_gasto).all()
    
    gastos_por_proveedor = db.query(
        Proveedor.nombre,
        func.sum(Gasto.total).label('total')
    ).join(Proveedor, Proveedor.id == Gasto.proveedor_id).filter(
        and_(
            func.date(Gasto.fecha_gasto) >= tuesday,
            func.date(Gasto.fecha_gasto) <= sunday,
            Gasto.sucursal_id == current_user.sucursal_id
        )
    ).group_by(Proveedor.nombre).all()
    
    gastos_por_categoria_articulo = (
        db.query(
            CategoriaArticulo.nombre,
            func.sum(GastoDetalle.subtotal_linea).label('total')
        )
        .join(Articulo, Articulo.categoria_id == CategoriaArticulo.id)
        .join(GastoDetalle, GastoDetalle.articulo_id == Articulo.id)
        .join(Gasto, Gasto.id == GastoDetalle.gasto_id)
        .filter(
            and_(
                func.date(Gasto.fecha_gasto) >= tuesday,
                func.date(Gasto.fecha_gasto) <= sunday,
                Gasto.sucursal_id == current_user.sucursal_id
            )
        )
        .group_by(CategoriaArticulo.nombre)
        .all()
    )
    
    # Análisis por tipo de orden
    tipos_orden = db.query(
        Pedido.tipo_orden,
        func.count(Pedido.id).label('cantidad'),
        func.sum(Pedido.total).label('ingresos')
    ).filter(
        and_(
            func.date(Pedido.fecha_creacion) >= tuesday,
            func.date(Pedido.fecha_creacion) <= sunday,
            Pedido.estado == "pagado",
            Pedido.sucursal_id == current_user.sucursal_id
        )
    ).group_by(Pedido.tipo_orden).all()
    
    # Análisis de cancelaciones (todos los pedidos de la semana)
    total_pedidos_creados = db.query(Pedido).filter(
        and_(
            func.date(Pedido.fecha_creacion) >= tuesday,
            func.date(Pedido.fecha_creacion) <= sunday,
            Pedido.sucursal_id == current_user.sucursal_id
        )
    ).count()
    
    pedidos_cancelados = db.query(Pedido).filter(
        and_(
            func.date(Pedido.fecha_creacion) >= tuesday,
            func.date(Pedido.fecha_creacion) <= sunday,
            Pedido.estado == "cancelado",
            Pedido.sucursal_id == current_user.sucursal_id
        )
    ).count()
    
    tasa_cancelacion = (pedidos_cancelados / total_pedidos_creados * 100) if total_pedidos_creados > 0 else 0
    
    total_ingresos = efectivo_total + tarjeta_total + transferencia_total
    utilidad_bruta = total_ingresos - gastos_total
    promedio_ticket = float(total_ingresos / total_pedidos) if total_pedidos > 0 else 0
    
    return {
        "periodo": {
            "inicio": tuesday.isoformat(),
            "fin": sunday.isoformat(),
            "descripcion": f"Semana del {tuesday.strftime('%d/%m/%Y')} al {sunday.strftime('%d/%m/%Y')}"
        },
        "resumen": {
            "total_pedidos": total_pedidos,
            "total_pedidos_creados": total_pedidos_creados,
            "pedidos_cancelados": pedidos_cancelados,
            "tasa_cancelacion": round(tasa_cancelacion, 2),
            "promedio_ticket": round(promedio_ticket, 2)
        },
        "ingresos": {
            "efectivo": float(efectivo_total),
            "tarjeta": float(tarjeta_total),
            "transferencia": float(transferencia_total),
            "total": float(total_ingresos)
        },
        "gastos": {
            "total": float(gastos_total),
            "por_categoria": [
                {
                    "categoria": categoria,
                    "total": float(total),
                    "porcentaje": round(float(total) / float(gastos_total) * 100, 2) if gastos_total > 0 else 0
                }
                for categoria, total in gastos_por_tipo
            ],
            "por_proveedor": [
                {
                    "proveedor": proveedor,
                    "total": float(total)
                }
                for proveedor, total in gastos_por_proveedor
            ],
            "por_categoria_articulo": [
                {
                    "categoria": categoria,
                    "total": float(total)
                }
                for categoria, total in gastos_por_categoria_articulo
            ]
        },
        "analisis_tipos_orden": [
            {
                "tipo": tipo,
                "cantidad": int(cantidad),
                "ingresos": float(ingresos),
                "porcentaje_pedidos": round(int(cantidad) / total_pedidos * 100, 2) if total_pedidos > 0 else 0,
                "porcentaje_ingresos": round(float(ingresos) / float(total_ingresos) * 100, 2) if total_ingresos > 0 else 0
            }
            for tipo, cantidad, ingresos in tipos_orden
        ],
        "utilidad_bruta": float(utilidad_bruta),
        "productos_mas_vendidos": [
            {"nombre": nombre, "cantidad": int(cantidad)}
            for nombre, cantidad in productos_vendidos
        ],
        "ventas_por_dia": [
            {
                "fecha": fecha.isoformat(),
                "total": float(total),
                "pedidos": int(pedidos),
                "promedio_ticket_dia": round(float(total) / int(pedidos), 2) if pedidos > 0 else 0
            }
            for fecha, total, pedidos in ventas_por_dia
        ]
    }


@router.get("/gastos/resumen")
def get_gastos_summary(
    fecha_inicio: str = None,  # YYYY-MM-DD
    fecha_fin: str = None,     # YYYY-MM-DD
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    """Resumen de gastos por categoría en un período"""
    _ensure_admin_access(current_user)
    
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
    
    # Resumen por tipo de gasto
    gastos_por_tipo = db.query(
        Gasto.tipo_gasto,
        func.sum(Gasto.total).label('total'),
        func.count(Gasto.id).label('cantidad')
    ).filter(
        and_(
            func.date(Gasto.fecha_gasto) >= inicio,
            func.date(Gasto.fecha_gasto) <= fin,
            Gasto.sucursal_id == current_user.sucursal_id
        )
    ).group_by(
        Gasto.tipo_gasto
    ).all()
    
    total_gastos = sum(float(total) for _, total, _ in gastos_por_tipo)
    
    return {
        "periodo": {
            "inicio": fecha_inicio,
            "fin": fecha_fin
        },
        "total_gastos": total_gastos,
        "por_categoria": [
            {
                "categoria": categoria,
                "total": float(total),
                "cantidad": int(cantidad),
                "porcentaje": round((float(total) / total_gastos * 100), 2) if total_gastos > 0 else 0
            }
            for categoria, total, cantidad in gastos_por_tipo
        ]
    }
