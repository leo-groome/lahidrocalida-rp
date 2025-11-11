from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, extract
from typing import List, Dict, Any
from datetime import datetime, date, timedelta
from decimal import Decimal

from app.db.session import get_db
from app.models import Usuario, Pedido, ArticuloPedido, Platillo, Gasto
from app.auth import get_current_active_user

router = APIRouter(prefix="/admin", tags=["administracion"])


def _ensure_admin_access(user: Usuario) -> None:
    """Verificar que el usuario sea administrador"""
    if user.rol != "administrador":
        raise HTTPException(status_code=403, detail="Acceso solo para administradores")


def _get_week_range(date_input: date = None) -> tuple[date, date]:
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
    
    return {
        "fecha": today.isoformat(),
        "total_pedidos": total_pedidos,
        "ingresos": {
            "efectivo": float(efectivo_total),
            "tarjeta": float(tarjeta_total),
            "transferencia": float(transferencia_total),
            "total": float(efectivo_total + tarjeta_total + transferencia_total)
        },
        "productos_mas_vendidos": [
            {"nombre": nombre, "cantidad": int(cantidad)}
            for nombre, cantidad in productos_vendidos
        ]
    }


@router.get("/reportes/semanal")
def get_weekly_report(
    fecha: str = None,  # Formato YYYY-MM-DD, cualquier día de la semana deseada
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
    gastos_total = db.query(func.sum(Gasto.monto)).filter(
        and_(
            func.date(Gasto.fecha_gasto) >= tuesday,
            func.date(Gasto.fecha_gasto) <= sunday,
            Gasto.sucursal_id == current_user.sucursal_id
        )
    ).scalar() or Decimal('0.00')
    
    total_ingresos = efectivo_total + tarjeta_total + transferencia_total
    utilidad_bruta = total_ingresos - gastos_total
    
    return {
        "periodo": {
            "inicio": tuesday.isoformat(),
            "fin": sunday.isoformat(),
            "descripcion": f"Semana del {tuesday.strftime('%d/%m/%Y')} al {sunday.strftime('%d/%m/%Y')}"
        },
        "total_pedidos": total_pedidos,
        "ingresos": {
            "efectivo": float(efectivo_total),
            "tarjeta": float(tarjeta_total),
            "transferencia": float(transferencia_total),
            "total": float(total_ingresos)
        },
        "gastos": {
            "total": float(gastos_total)
        },
        "utilidad_bruta": float(utilidad_bruta),
        "productos_mas_vendidos": [
            {"nombre": nombre, "cantidad": int(cantidad)}
            for nombre, cantidad in productos_vendidos
        ],
        "ventas_por_dia": [
            {
                "fecha": fecha.isoformat(),
                "total": float(total),
                "pedidos": int(pedidos)
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
    
    # Resumen por categoría
    gastos_por_categoria = db.query(
        Gasto.categoria,
        func.sum(Gasto.monto).label('total'),
        func.count(Gasto.id).label('cantidad')
    ).filter(
        and_(
            func.date(Gasto.fecha_gasto) >= inicio,
            func.date(Gasto.fecha_gasto) <= fin,
            Gasto.sucursal_id == current_user.sucursal_id
        )
    ).group_by(
        Gasto.categoria
    ).all()
    
    total_gastos = sum(float(total) for _, total, _ in gastos_por_categoria)
    
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
            for categoria, total, cantidad in gastos_por_categoria
        ]
    }