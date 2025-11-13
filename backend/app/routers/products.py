from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from typing import List
from datetime import date, timedelta

from app.db.session import get_db
from app.models import Platillo, Usuario, Pedido, ArticuloPedido
from app.schemas import PlatilloCreate, PlatilloResponse
from app.auth import get_current_active_user

router = APIRouter(prefix="/platillos", tags=["platillos"])


@router.get("/", response_model=List[PlatilloResponse])
def list_platillos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    return db.query(Platillo).all()


@router.post("/", response_model=PlatilloResponse, status_code=status.HTTP_201_CREATED)
def create_platillo(
    data: PlatilloCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    # Solo admin puede crear platillos inicialmente
    if current_user.rol != "administrador":
        raise HTTPException(status_code=403, detail="No autorizado para crear platillos")

    platillo = Platillo(
        nombre=data.nombre,
        descripcion=data.descripcion,
        precio=data.precio,
        categoria=data.categoria,
        estado=data.estado,
    )
    db.add(platillo)
    db.commit()
    db.refresh(platillo)
    return platillo


@router.get("/ordenados-popularidad", response_model=List[PlatilloResponse])
def get_platillos_ordenados_popularidad(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
    dias: int = 30  # Últimos 30 días por defecto
):
    """
    Obtener platillos ordenados por popularidad (últimos N días)
    Usa datos de ventas reales para optimizar la experiencia del mesero
    """
    fecha_limite = date.today() - timedelta(days=dias)
    
    # Query para obtener platillos con su popularidad
    platillos_con_popularidad = db.query(
        Platillo,
        func.coalesce(func.sum(ArticuloPedido.cantidad), 0).label('total_vendido')
    ).outerjoin(
        ArticuloPedido, Platillo.id == ArticuloPedido.platillo_id
    ).outerjoin(
        Pedido, and_(
            ArticuloPedido.pedido_id == Pedido.id,
            Pedido.estado == "pagado",
            func.date(Pedido.fecha_creacion) >= fecha_limite,
            Pedido.sucursal_id == current_user.sucursal_id
        )
    ).filter(
        Platillo.estado == "disponible"
    ).group_by(
        Platillo.id
    ).order_by(
        desc('total_vendido'),  # Más vendidos primero
        Platillo.nombre         # Alfabético como fallback
    ).all()
    
    # Retornar solo los objetos Platillo
    return [platillo for platillo, _ in platillos_con_popularidad]


