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


@router.get("/{platillo_id}", response_model=PlatilloResponse)
def get_platillo(
    platillo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    platillo = db.query(Platillo).filter(Platillo.id == platillo_id).first()
    if not platillo:
        raise HTTPException(status_code=404, detail="Platillo no encontrado")
    return platillo


@router.put("/{platillo_id}", response_model=PlatilloResponse)
def update_platillo(
    platillo_id: int,
    data: PlatilloCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    # Solo admin puede actualizar platillos
    if current_user.rol != "administrador":
        raise HTTPException(status_code=403, detail="No autorizado para actualizar platillos")

    platillo = db.query(Platillo).filter(Platillo.id == platillo_id).first()
    if not platillo:
        raise HTTPException(status_code=404, detail="Platillo no encontrado")

    # Actualizar campos
    platillo.nombre = data.nombre
    platillo.descripcion = data.descripcion
    platillo.precio = data.precio
    platillo.categoria = data.categoria
    platillo.estado = data.estado
    
    # Generar kds_name si no se proporciona
    if hasattr(data, 'kds_name') and data.kds_name:
        platillo.kds_name = data.kds_name
    else:
        platillo.kds_name = data.nombre[:20]  # Truncar a 20 caracteres

    db.commit()
    db.refresh(platillo)
    return platillo


@router.patch("/{platillo_id}/disponibilidad", response_model=PlatilloResponse)
def toggle_disponibilidad_platillo(
    platillo_id: int,
    data: dict,  # {"estado": "disponible" | "no_disponible"}
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    Cambiar disponibilidad de un platillo.
    Permitido para cocina y administradores.
    """
    # Validar permisos - cocina y admin pueden cambiar disponibilidad
    if current_user.rol not in ["cocina", "administrador"]:
        raise HTTPException(
            status_code=403, 
            detail="Solo cocina y administradores pueden cambiar disponibilidad"
        )

    platillo = db.query(Platillo).filter(Platillo.id == platillo_id).first()
    if not platillo:
        raise HTTPException(status_code=404, detail="Platillo no encontrado")

    # Validar estado
    nuevo_estado = data.get("estado")
    if nuevo_estado not in ["disponible", "no_disponible"]:
        raise HTTPException(
            status_code=400, 
            detail="Estado inválido. Use 'disponible' o 'no_disponible'"
        )

    # Actualizar solo el estado
    estado_anterior = platillo.estado
    platillo.estado = nuevo_estado
    
    db.commit()
    db.refresh(platillo)
    
    print(f"✅ Platillo '{platillo.nombre}' cambiado de '{estado_anterior}' a '{nuevo_estado}' por {current_user.nombre}")
    
    return platillo


@router.delete("/{platillo_id}")
def delete_platillo(
    platillo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    # Solo admin puede eliminar platillos
    if current_user.rol != "administrador":
        raise HTTPException(status_code=403, detail="No autorizado para eliminar platillos")

    platillo = db.query(Platillo).filter(Platillo.id == platillo_id).first()
    if not platillo:
        raise HTTPException(status_code=404, detail="Platillo no encontrado")

    # Verificar si tiene pedidos asociados
    pedidos_count = db.query(ArticuloPedido).filter(ArticuloPedido.platillo_id == platillo_id).count()
    if pedidos_count > 0:
        # En lugar de eliminar, cambiar estado a no_disponible
        platillo.estado = "no_disponible"
        db.commit()
        return {"message": "Platillo marcado como no disponible (tiene pedidos asociados)"}
    
    # Si no tiene pedidos, eliminar completamente
    db.delete(platillo)
    db.commit()
    return {"message": "Platillo eliminado correctamente"}


