from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime, date

from app.db.session import get_db
from app.models import Pedido, ArticuloPedido, Platillo, Usuario
from app.schemas import PedidoCreate, PedidoResponse, PedidoUpdate
from app.auth import get_current_active_user

router = APIRouter(prefix="/pedidos", tags=["pedidos"])


def generate_numero_display(db: Session, sucursal_id: int) -> str:
    """
    Genera el número de display secuencial por día y sucursal.
    Formato: 001, 002, 003, etc.
    Se reinicia automáticamente cada día.
    """
    today = date.today()
    
    # Buscar el último número del día actual para esta sucursal
    last_pedido = db.query(Pedido).filter(
        and_(
            Pedido.sucursal_id == sucursal_id,
            func.date(Pedido.fecha_creacion) == today
        )
    ).order_by(Pedido.numero_display.desc()).first()
    
    if last_pedido:
        # Incrementar el último número
        last_number = int(last_pedido.numero_display)
        next_number = last_number + 1
    else:
        # Primer pedido del día
        next_number = 1
    
    return f"{next_number:03d}"


@router.post("/", response_model=PedidoResponse, status_code=status.HTTP_201_CREATED)
def create_pedido(
    data: PedidoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    Crear un nuevo pedido.
    Solo cajeros y administradores pueden crear pedidos.
    """
    # Validar permisos
    if current_user.rol not in ["cajero", "administrador"]:
        raise HTTPException(
            status_code=403, 
            detail="Solo cajeros y administradores pueden crear pedidos"
        )
    
    # Validar que nombre_cliente no esté vacío
    if not data.nombre_cliente or data.nombre_cliente.strip() == "":
        raise HTTPException(
            status_code=400,
            detail="El nombre del cliente es obligatorio"
        )
    
    # Validar que hay artículos en el pedido
    if not data.articulos or len(data.articulos) == 0:
        raise HTTPException(
            status_code=400,
            detail="El pedido debe tener al menos un artículo"
        )
    
    # Validar y calcular artículos
    total_calculado = 0
    articulos_calculados = []
    
    for articulo in data.articulos:
        # Validar que el platillo existe
        platillo = db.query(Platillo).filter(Platillo.id == articulo.platillo_id).first()
        if not platillo:
            raise HTTPException(
                status_code=400,
                detail=f"Platillo con ID {articulo.platillo_id} no encontrado"
            )
        
        # Validar que el platillo esté disponible
        if platillo.estado != "disponible":
            raise HTTPException(
                status_code=400,
                detail=f"El platillo '{platillo.nombre}' no está disponible"
            )
        
        # Validar cantidad
        if articulo.cantidad <= 0:
            raise HTTPException(
                status_code=400,
                detail="La cantidad debe ser mayor a 0"
            )
        
        # Calcular precio_cobrado automáticamente
        precio_cobrado = float(platillo.precio) * articulo.cantidad
        total_calculado += precio_cobrado
        
        # Guardar artículo con precio calculado
        articulos_calculados.append({
            'platillo_id': articulo.platillo_id,
            'cantidad': articulo.cantidad,
            'precio_cobrado': precio_cobrado,
            'modificaciones': articulo.modificaciones
        })
    
    # Generar número de display
    numero_display = generate_numero_display(db, current_user.sucursal_id)
    
    # Crear el pedido
    pedido = Pedido(
        numero_display=numero_display,
        nombre_cliente=data.nombre_cliente.strip(),
        total=total_calculado,
        estado="pendiente",
        metodo_pago=data.metodo_pago,
        sucursal_id=current_user.sucursal_id,
        usuario_id=current_user.id
    )
    
    db.add(pedido)
    db.flush()  # Para obtener el ID del pedido
    
    # Crear los artículos del pedido
    for articulo_data in articulos_calculados:
        articulo = ArticuloPedido(
            pedido_id=pedido.id,
            platillo_id=articulo_data['platillo_id'],
            cantidad=articulo_data['cantidad'],
            precio_cobrado=articulo_data['precio_cobrado'],
            modificaciones=articulo_data['modificaciones']
        )
        db.add(articulo)
    
    db.commit()
    db.refresh(pedido)
    
    return pedido


@router.get("/", response_model=List[PedidoResponse])
def list_pedidos(
    estado: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    Listar pedidos con filtros.
    Cajeros ven solo pedidos de su sucursal.
    Administradores ven todos los pedidos.
    """
    query = db.query(Pedido)
    
    # Filtro por sucursal según el rol
    if current_user.rol == "cajero":
        query = query.filter(Pedido.sucursal_id == current_user.sucursal_id)
    # Los administradores ven todos los pedidos (sin filtro de sucursal)
    
    # Filtro por estado si se especifica
    if estado:
        if estado not in ["pendiente", "preparando", "listo", "completado", "cancelado"]:
            raise HTTPException(
                status_code=400,
                detail="Estado inválido. Valores permitidos: pendiente, preparando, listo, completado, cancelado"
            )
        query = query.filter(Pedido.estado == estado)
    
    # Ordenar por fecha de creación descendente
    query = query.order_by(Pedido.fecha_creacion.desc())
    
    return query.all()


@router.get("/{pedido_id}", response_model=PedidoResponse)
def get_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    Obtener un pedido específico por ID.
    Cajeros solo pueden ver pedidos de su sucursal.
    Administradores pueden ver cualquier pedido.
    """
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    
    if not pedido:
        raise HTTPException(
            status_code=404,
            detail="Pedido no encontrado"
        )
    
    # Validar permisos de acceso
    if current_user.rol == "cajero" and pedido.sucursal_id != current_user.sucursal_id:
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para ver este pedido"
        )
    
    return pedido


@router.put("/{pedido_id}", response_model=PedidoResponse)
def update_pedido(
    pedido_id: int,
    data: PedidoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    Actualizar el estado de un pedido.
    Solo cocina y administradores pueden cambiar estados.
    """
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    
    if not pedido:
        raise HTTPException(
            status_code=404,
            detail="Pedido no encontrado"
        )
    
    # Validar permisos de acceso
    if current_user.rol == "cajero" and pedido.sucursal_id != current_user.sucursal_id:
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para modificar este pedido"
        )
    
    # Validar permisos para cambiar estado
    if current_user.rol not in ["cocina", "administrador"]:
        raise HTTPException(
            status_code=403,
            detail="Solo cocina y administradores pueden cambiar el estado de pedidos"
        )
    
    # Validar estado
    if data.estado not in ["pendiente", "preparando", "listo", "completado", "cancelado"]:
        raise HTTPException(
            status_code=400,
            detail="Estado inválido. Valores permitidos: pendiente, preparando, listo, completado, cancelado"
        )
    
    # Actualizar estado
    pedido.estado = data.estado
    
    db.commit()
    db.refresh(pedido)
    
    return pedido
