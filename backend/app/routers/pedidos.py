from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, cast
from sqlalchemy import Integer as SAInteger
from typing import List, Optional
from sqlalchemy.exc import IntegrityError
from datetime import datetime, date, timedelta
import pytz

from app.db.session import get_db
from app.models import Pedido, ArticuloPedido, Platillo, Usuario
from app.schemas import PedidoCreate, PedidoResponse, PedidoUpdate, ArticuloPedidoUpdate
from app.auth import get_current_active_user
from app.websocket_manager import websocket_manager
from app.core.config import settings

router = APIRouter(prefix="/pedidos", tags=["pedidos"])


def generate_numero_display(db: Session, sucursal_id: int) -> str:
    """
    Genera el número de display secuencial por día y sucursal.
    Formato: 001, 002, 003, etc.
    Se reinicia automáticamente cada día en zona horaria local.
    """
    # Usar zona horaria local del restaurante directamente
    tz = pytz.timezone(settings.TIMEZONE)
    now_local = datetime.now(tz)
    today_local = now_local.date()
    
    # Usar fechas locales directamente (BD ya está en zona local)
    start_dt = tz.localize(datetime.combine(today_local, datetime.min.time())).replace(tzinfo=None)
    end_dt = tz.localize(datetime.combine(today_local + timedelta(days=1), datetime.min.time())).replace(tzinfo=None)

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
async def create_pedido(
    data: PedidoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    Crear un nuevo pedido.
    Solo cajeros y administradores pueden crear pedidos.
    """
    # Validar permisos
    if current_user.rol not in ["cajero", "administrador", "mesero"]:
        raise HTTPException(
            status_code=403, 
            detail="Solo cajeros, meseros y administradores pueden crear pedidos"
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
                mesa=data.mesa,
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
            
            # Notificar creación del pedido via WebSocket
            try:
                pedido_data = {
                    "id": pedido.id,
                    "numero_display": pedido.numero_display,
                    "nombre_cliente": pedido.nombre_cliente,
                    "mesa": pedido.mesa,
                    "total": float(pedido.total),
                    "estado": pedido.estado,
                    "tipo_orden": pedido.tipo_orden,
                    "sucursal_id": pedido.sucursal_id,
                    "fecha_creacion": pedido.fecha_creacion.isoformat(),
                    "articulos_pedido": [
                        {
                            "id": a.id,
                            "cantidad": a.cantidad,
                            "precio_cobrado": float(a.precio_cobrado),
                            "modificaciones": a.modificaciones,
                            "estado_item": a.estado_item,
                            "platillo": {
                                "nombre": a.platillo.nombre,
                                "kds_name": a.platillo.kds_name
                            } if a.platillo else None
                        } for a in pedido.articulos_pedido
                    ]
                }
                await websocket_manager.notify_pedido_created(pedido_data)
            except Exception as e:
                # Log del error pero no fallar la creación del pedido
                print(f"Error notifying pedido creation via WebSocket: {e}")
            
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
    Listar pedidos del día actual según zona horaria del restaurante.
    Cajeros ven solo pedidos de su sucursal.
    Administradores ven todos los pedidos.
    """
    # Usar zona horaria local del restaurante para filtrar pedidos del día
    tz = pytz.timezone(settings.TIMEZONE)
    now_local = datetime.now(tz)
    today_local = now_local.date()
    
    # Usar fechas locales directamente (BD ya está en zona local)
    start_dt = tz.localize(datetime.combine(today_local, datetime.min.time())).replace(tzinfo=None)
    end_dt = tz.localize(datetime.combine(today_local + timedelta(days=1), datetime.min.time())).replace(tzinfo=None)
    
    query = db.query(Pedido).filter(
        Pedido.fecha_creacion >= start_dt,
        Pedido.fecha_creacion < end_dt
    )
    
    # Filtro por sucursal según el rol
    if current_user.rol == "cajero":
        query = query.filter(Pedido.sucursal_id == current_user.sucursal_id)
    # Los administradores ven todos los pedidos (sin filtro de sucursal)
    
    # Filtro por estado si se especifica
    if estado:
        if estado not in ["pendiente", "preparando", "listo", "entregado", "cuenta_solicitada", "pagado", "cancelado"]:
            raise HTTPException(
                status_code=400,
                detail="Estado inválido. Valores permitidos: pendiente, preparando, listo, entregado, cuenta_solicitada, pagado, cancelado"
            )
        query = query.filter(Pedido.estado == estado)
    
    # Ordenar por fecha de creación descendente
    query = query.order_by(Pedido.fecha_creacion.desc())
    
    return query.all()


@router.get("/pendientes-pago/lista", response_model=List[PedidoResponse])
def get_pedidos_pendientes_pago(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    Obtener pedidos que están esperando pago (estado: cuenta_solicitada).
    Para cajeros: solo pedidos de su sucursal.
    Para administradores: todos los pedidos.
    """
    # Solo cajeros y administradores pueden ver esto
    if current_user.rol not in ["cajero", "administrador"]:
        raise HTTPException(
            status_code=403,
            detail="Solo cajeros y administradores pueden ver pedidos pendientes de pago"
        )
    
    query = db.query(Pedido).filter(Pedido.estado == "cuenta_solicitada")
    
    # Filtro por sucursal para cajeros
    if current_user.rol == "cajero":
        query = query.filter(Pedido.sucursal_id == current_user.sucursal_id)
    
    # Ordenar por fecha de creación
    return query.order_by(Pedido.fecha_creacion.asc()).all()


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
# Nota: la impresión automática puede activarse bajo condiciones, pero por ahora la impresión se invoca desde el frontend antes del cambio de estado.
async def update_pedido(
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
    
    # Validar permisos para cambiar estado según rol
    allowed_transitions = {
        "mesero": ["pendiente", "entregado", "cuenta_solicitada"],
        "cajero": ["entregado", "cuenta_solicitada", "pagado"],  # Cajero puede cambiar de entregado a cuenta_solicitada
        "cocina": ["pendiente", "preparando", "listo"],
        "administrador": ["pendiente", "preparando", "listo", "entregado", "cuenta_solicitada", "pagado", "cancelado"]
    }
    
    if current_user.rol not in allowed_transitions:
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para cambiar el estado de pedidos"
        )
    
    if data.estado not in allowed_transitions[current_user.rol]:
        raise HTTPException(
            status_code=403,
            detail=f"Tu rol ({current_user.rol}) no puede cambiar a estado '{data.estado}'"
        )
    
    # Validar estado
    if data.estado not in ["pendiente", "preparando", "listo", "entregado", "cuenta_solicitada", "pagado", "cancelado"]:
        raise HTTPException(
            status_code=400,
            detail="Estado inválido. Valores permitidos: pendiente, preparando, listo, entregado, cuenta_solicitada, pagado, cancelado"
        )
    
    # Actualizar estado
    old_estado = pedido.estado
    pedido.estado = data.estado
    
    # Actualizar método de pago si se proporciona
    if data.metodo_pago is not None:
        pedido.metodo_pago = data.metodo_pago
    
    db.commit()
    db.refresh(pedido)
    
    # Notificar cambio de estado via WebSocket (solo si cambió)
    if old_estado != data.estado:
        try:
            pedido_data = {
                "id": pedido.id,
                "numero_display": pedido.numero_display,
                "nombre_cliente": pedido.nombre_cliente,
                "mesa": pedido.mesa,
                "total": float(pedido.total),
                "estado": pedido.estado,
                "tipo_orden": pedido.tipo_orden,
                "sucursal_id": pedido.sucursal_id,
                "fecha_creacion": pedido.fecha_creacion.isoformat(),
                "metodo_pago": pedido.metodo_pago,
                "articulos_pedido": [
                    {
                        "id": a.id,
                        "cantidad": a.cantidad,
                        "precio_cobrado": float(a.precio_cobrado),
                        "modificaciones": a.modificaciones,
                        "estado_item": a.estado_item,
                        "platillo": {
                            "nombre": a.platillo.nombre,
                            "kds_name": a.platillo.kds_name
                        } if a.platillo else None
                    } for a in pedido.articulos_pedido
                ]
            }
            await websocket_manager.notify_pedido_estado_changed(
                pedido_id=pedido.id,
                nuevo_estado=data.estado,
                pedido_data=pedido_data
            )
        except Exception as e:
            # Log del error pero no fallar la actualización del pedido
            print(f"Error notifying pedido estado change via WebSocket: {e}")
    
    return pedido


@router.put("/articulos/{articulo_id}", response_model=dict)
async def update_articulo_estado(
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
    if current_user.rol not in ["mesero", "cocina", "administrador"]:
        raise HTTPException(
            status_code=403,
            detail="Solo meseros, cocina y administradores pueden actualizar items"
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
    old_estado = articulo.estado_item
    articulo.estado_item = data.estado_item
    db.commit()
    
    # Obtener el pedido asociado
    pedido = articulo.pedido
    
    # Verificar si todos los artículos están listos
    todos_listos = all(a.estado_item == "listo" for a in pedido.articulos_pedido)
    
    # Si todos están listos y el pedido está en 'preparando', cambiar a 'listo'
    pedido_estado_changed = False
    if todos_listos and pedido.estado == "preparando":
        pedido.estado = "listo"
        pedido_estado_changed = True
        db.commit()
    
    db.refresh(articulo)
    db.refresh(pedido)
    
    # Notificar cambio de artículo via WebSocket (solo si cambió)
    if old_estado != data.estado_item:
        try:
            pedido_data = {
                "id": pedido.id,
                "numero_display": pedido.numero_display,
                "nombre_cliente": pedido.nombre_cliente,
                "mesa": pedido.mesa,
                "total": float(pedido.total),
                "estado": pedido.estado,
                "tipo_orden": pedido.tipo_orden,
                "sucursal_id": pedido.sucursal_id,
                "fecha_creacion": pedido.fecha_creacion.isoformat(),
                "articulos_pedido": [
                    {
                        "id": a.id,
                        "cantidad": a.cantidad,
                        "precio_cobrado": float(a.precio_cobrado),
                        "modificaciones": a.modificaciones,
                        "estado_item": a.estado_item,
                        "platillo": {
                            "nombre": a.platillo.nombre,
                            "kds_name": a.platillo.kds_name
                        } if a.platillo else None
                    } for a in pedido.articulos_pedido
                ]
            }
            
            # Notificar cambio de artículo
            await websocket_manager.notify_articulo_estado_changed(
                pedido_id=pedido.id,
                articulo_id=articulo.id,
                nuevo_estado=data.estado_item,
                pedido_data=pedido_data
            )
            
            # Si el pedido también cambió de estado, notificar eso también
            if pedido_estado_changed:
                await websocket_manager.notify_pedido_estado_changed(
                    pedido_id=pedido.id,
                    nuevo_estado="listo",
                    pedido_data=pedido_data
                )
                
        except Exception as e:
            # Log del error pero no fallar la actualización del artículo
            print(f"Error notifying articulo estado change via WebSocket: {e}")
    
    return {
        "articulo_id": articulo.id,
        "estado_item": articulo.estado_item,
        "pedido_id": pedido.id,
        "pedido_estado": pedido.estado
    }
