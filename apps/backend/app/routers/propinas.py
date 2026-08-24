from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_active_user
from app.db.session import get_db
from app.models import Pedido, Usuario
from app.utils.timezone import MEXICO_TZ, get_mexico_now

router = APIRouter(prefix="/propinas", tags=["propinas"])


@router.get("/reporte")
def get_reporte_propinas(
    fecha: Optional[str] = None,  # Formato YYYY-MM-DD, por defecto hoy
    mesero_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """
    Obtener reporte de propinas para una fecha específica.
    Solo cajeros y administradores pueden ver reportes.
    Para cajeros: solo pedidos de su sucursal.
    Para administradores: todos los pedidos.
    """
    # Validar permisos
    if current_user.rol not in ["cajero", "administrador"]:
        raise HTTPException(
            status_code=403, detail="Solo cajeros y administradores pueden ver reportes de propinas"
        )

    # Determinar fecha a usar
    if fecha:
        try:
            target_date = datetime.strptime(fecha, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use YYYY-MM-DD")
    else:
        # Usar hoy en zona horaria local
        target_date = get_mexico_now().date()

    # Calcular rangos de fecha en zona horaria local
    start_dt = datetime.combine(target_date, datetime.min.time(), tzinfo=MEXICO_TZ)
    end_dt = datetime.combine(
        target_date + timedelta(days=1), datetime.min.time(), tzinfo=MEXICO_TZ
    )

    # Construir consulta base
    query = (
        db.query(
            Pedido.usuario_id,
            Usuario.nombre.label("mesero_nombre"),
            func.sum(Pedido.propina_efectivo).label("total_efectivo"),
            func.sum(Pedido.propina_tarjeta).label("total_tarjeta"),
            func.sum(Pedido.propina_efectivo + Pedido.propina_tarjeta).label("total_general"),
        )
        .join(Usuario, Pedido.usuario_id == Usuario.id)
        .filter(
            Pedido.fecha_creacion >= start_dt,
            Pedido.fecha_creacion < end_dt,
            Pedido.estado == "pagado",  # Solo pedidos pagados tienen propinas registradas
        )
    )

    # Filtro por sucursal para cajeros
    if current_user.rol == "cajero":
        query = query.filter(Pedido.sucursal_id == current_user.sucursal_id)

    # Filtro por mesero si se especifica
    if mesero_id is not None:
        query = query.filter(Pedido.usuario_id == mesero_id)

    # Agrupar por mesero
    query = query.group_by(Pedido.usuario_id, Usuario.nombre)

    # Ejecutar consulta
    resultados = query.all()

    # Calcular totales generales
    total_efectivo_general = sum(r.total_efectivo or 0 for r in resultados)
    total_tarjeta_general = sum(r.total_tarjeta or 0 for r in resultados)
    total_general = total_efectivo_general + total_tarjeta_general

    # Construir respuesta
    reporte = {
        "fecha": target_date.isoformat(),
        "total_efectivo": float(total_efectivo_general),
        "total_tarjeta": float(total_tarjeta_general),
        "total_general": float(total_general),
        "por_mesero": [],
    }

    for resultado in resultados:
        reporte["por_mesero"].append(
            {
                "mesero_id": resultado.usuario_id,
                "nombre": resultado.mesero_nombre,
                "propina_efectivo": float(resultado.total_efectivo or 0),
                "propina_tarjeta": float(resultado.total_tarjeta or 0),
                "total": float((resultado.total_efectivo or 0) + (resultado.total_tarjeta or 0)),
            }
        )

    return reporte


@router.get("/detalle")
def get_detalle_propinas(
    fecha: Optional[str] = None,
    mesero_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """
    Obtener detalle de propinas por pedido para una fecha específica.
    Útil para verificar pedidos individuales.
    """
    # Validar permisos
    if current_user.rol not in ["cajero", "administrador"]:
        raise HTTPException(
            status_code=403, detail="Solo cajeros y administradores pueden ver detalle de propinas"
        )

    # Determinar fecha a usar (misma lógica que reporte)
    if fecha:
        try:
            target_date = datetime.strptime(fecha, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use YYYY-MM-DD")
    else:
        target_date = get_mexico_now().date()

    # Calcular rangos de fecha
    start_dt = datetime.combine(target_date, datetime.min.time(), tzinfo=MEXICO_TZ)
    end_dt = datetime.combine(
        target_date + timedelta(days=1), datetime.min.time(), tzinfo=MEXICO_TZ
    )

    # Proyección de columnas con join: evita traer el modelo completo y el
    # N+1 de pedido.usuario dentro del loop
    query = (
        db.query(
            Pedido.id,
            Pedido.numero_display,
            Pedido.mesa,
            Pedido.nombre_cliente,
            Pedido.usuario_id,
            Usuario.nombre.label("mesero_nombre"),
            Pedido.total,
            Pedido.propina_efectivo,
            Pedido.propina_tarjeta,
            Pedido.metodo_pago,
            Pedido.fecha_creacion,
        )
        .outerjoin(Usuario, Pedido.usuario_id == Usuario.id)
        .filter(
            Pedido.fecha_creacion >= start_dt,
            Pedido.fecha_creacion < end_dt,
            Pedido.estado == "pagado",
        )
    )

    # Filtro por sucursal para cajeros
    if current_user.rol == "cajero":
        query = query.filter(Pedido.sucursal_id == current_user.sucursal_id)

    # Filtro por mesero si se especifica
    if mesero_id is not None:
        query = query.filter(Pedido.usuario_id == mesero_id)

    # Ordenar por fecha
    query = query.order_by(Pedido.fecha_creacion.desc())

    rows = query.all()

    # Formatear respuesta
    detalle = []
    for row in rows:
        detalle.append(
            {
                "pedido_id": row.id,
                "numero_display": row.numero_display,
                "mesa": row.mesa,
                "nombre_cliente": row.nombre_cliente,
                "mesero_id": row.usuario_id,
                "mesero_nombre": row.mesero_nombre or "N/A",
                "total_pedido": float(row.total or 0),
                "propina_efectivo": float(row.propina_efectivo or 0),
                "propina_tarjeta": float(row.propina_tarjeta or 0),
                "propina_total": float((row.propina_efectivo or 0) + (row.propina_tarjeta or 0)),
                "metodo_pago": row.metodo_pago,
                "fecha_pago": row.fecha_creacion.isoformat(),
            }
        )

    return {"fecha": target_date.isoformat(), "total_pedidos": len(rows), "detalle": detalle}
