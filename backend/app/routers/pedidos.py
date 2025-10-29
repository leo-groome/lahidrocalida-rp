from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, cast
from sqlalchemy import Integer as SAInteger
from typing import List, Optional
from sqlalchemy.exc import IntegrityError
from datetime import datetime, date, timedelta

from app.db.session import get_db
from app.models import Pedido, ArticuloPedido, Platillo, Usuario
from app.schemas import PedidoCreate, PedidoResponse, PedidoUpdate, ArticuloPedidoUpdate
from app.auth import get_current_active_user

router = APIRouter(prefix="/pedidos", tags=["pedidos"])


def generate_numero_display(db: Session, sucursal_id: int) -> str:
    """
    Genera el número de display secuencial por día y sucursal.
    Formato: 001, 002, 003, etc.
    Se reinicia automáticamente cada día.
    """
    # Usar ventana del día en UTC para evitar problemas de zona horaria
    today_utc = datetime.utcnow().date()
    start_dt = datetime.combine(today_utc, datetime.min.time())
    end_dt = start_dt + timedelta(days=1)

    # Obtener el máximo numero_display como entero para la sucursal y día actuales
    max_number = (
        db.query(func.max(cast(Pedido.numero_display, SAInteger)))
        .filter(
            Pedido.sucursal_id == sucursal_id,
            Pedido.fecha_creacion >= start_dt,
            Pedido.fecha_creacion < end_dt,
        )
        .scalar()
    )

    next_number = (max_number or 0) + 1
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
    # Validar tipo_orden
    if data.tipo_orden not in ["aqui", "llevar", "uber_eats"]:
        raise HTTPException(
            status_code=400,
            detail="tipo_orden inválido. Valores permitidos: aqui, llevar, uber_eats"
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
    
    # Crear pedido con reintentos ante colisión de numero_display por concurrencia
    attempts = 0
    while attempts < 5:
        try:
            # Generar número de display basado en ventana del día
            numero_display = generate_numero_display(db, current_user.sucursal_id)

            # Crear el pedido
            pedido = Pedido(
                numero_display=numero_display,
                nombre_cliente=data.nombre_cliente.strip() if data.nombre_cliente else None,
                total=total_calculado,
                estado="pendiente",
                metodo_pago=data.metodo_pago,
                tipo_orden=data.tipo_orden,
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
        except IntegrityError:
            # Colisión de unique (otra transacción tomó el número). Reintentar.
            db.rollback()
            attempts += 1
    # Si no se pudo después de varios intentos, reportar error
    raise HTTPException(status_code=500, detail="No fue posible generar un numero_display único. Intenta de nuevo.")


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


@router.put("/articulos/{articulo_id}", response_model=dict)
def update_articulo_estado(
    articulo_id: int,
    data: ArticuloPedidoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    Actualizar el estado de un artículo del pedido.
    Solo cocina y administradores pueden actualizar.
    Si todos los artículos están listos, el pedido pasa a 'listo'.
    """
    # Validar permisos
    if current_user.rol not in ["cocina", "administrador"]:
        raise HTTPException(
            status_code=403,
            detail="Solo cocina y administradores pueden actualizar items"
        )
    
    # Obtener el artículo
    articulo = db.query(ArticuloPedido).filter(ArticuloPedido.id == articulo_id).first()
    if not articulo:
        raise HTTPException(
            status_code=404,
            detail="Artículo no encontrado"
        )
    
    # Validar estado
    if data.estado_item not in ["pendiente", "listo"]:
        raise HTTPException(
            status_code=400,
            detail="Estado inválido. Valores permitidos: pendiente, listo"
        )
    
    # Actualizar estado del artículo
    articulo.estado_item = data.estado_item
    db.commit()
    
    # Obtener el pedido asociado
    pedido = articulo.pedido
    
    # Verificar si todos los artículos están listos
    todos_listos = all(a.estado_item == "listo" for a in pedido.articulos_pedido)
    
    # Si todos están listos y el pedido está en 'preparando', cambiar a 'listo'
    if todos_listos and pedido.estado == "preparando":
        pedido.estado = "listo"
        db.commit()
    
    db.refresh(articulo)
    
    return {
        "articulo_id": articulo.id,
        "estado_item": articulo.estado_item,
        "pedido_id": pedido.id,
        "pedido_estado": pedido.estado
    }
