from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, cast
from sqlalchemy import Integer as SAInteger
from typing import List, Optional
from sqlalchemy.exc import IntegrityError
from datetime import datetime, date, timedelta
from decimal import Decimal
import pytz

from app.db.session import get_db
from app.models import Pedido, ArticuloPedido, Platillo, Usuario
from app.schemas import PedidoCreate, PedidoResponse, PedidoUpdate, ArticuloPedidoUpdate, AgregarArticulosRequest
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
                # Obtener el platillo para verificar si es bebida
                platillo = db.query(Platillo).filter(Platillo.id == articulo_data['platillo_id']).first()
                
                # Si es bebida, marcarla como "entregado" automáticamente
                estado_inicial = "entregado" if platillo and platillo.categoria == "Bebidas" else "pendiente"
                
                articulo = ArticuloPedido(
                    pedido_id=pedido.id,
                    platillo_id=articulo_data['platillo_id'],
                    cantidad=articulo_data['cantidad'],
                    precio_cobrado=articulo_data['precio_cobrado'],
                    modificaciones=articulo_data['modificaciones'],
                    estado_item=estado_inicial  # Bebidas = "entregado", resto = "pendiente"
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
        "cajero": ["entregado", "cuenta_solicitada", "pagado", "cancelado"],  # Cajero puede cancelar pedidos
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
    
    # Si el pedido se marca como "listo", marcar todos los artículos como "listo"
    # EXCEPTO aquellos que ya están "entregado" (bebidas)
    if data.estado == "listo":
        for articulo in pedido.articulos_pedido:
            if articulo.estado_item not in ["listo", "entregado"]:
                articulo.estado_item = "listo"
    
    # Si el pedido se marca como "entregado", marcar todos los artículos como "entregado"
    if data.estado == "entregado":
        for articulo in pedido.articulos_pedido:
            if articulo.estado_item != "entregado":
                articulo.estado_item = "entregado"
    
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
    if data.estado_item not in ["pendiente", "preparando", "listo"]:
        raise HTTPException(
            status_code=400,
            detail="Estado inválido. Valores permitidos: pendiente, preparando, listo"
        )
    
    # Actualizar estado del artículo
    old_estado = articulo.estado_item
    articulo.estado_item = data.estado_item
    db.commit()
    
    # Obtener el pedido asociado
    pedido = articulo.pedido
    
    # Verificar si todos los artículos están completados (listo o entregado)
    todos_completados = all(a.estado_item in ["listo", "entregado"] for a in pedido.articulos_pedido)
    
    # Si todos están completados y el pedido está en 'preparando', cambiar a 'listo'
    pedido_estado_changed = False
    if todos_completados and pedido.estado == "preparando":
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


@router.put("/{pedido_id}/agregar-articulos", response_model=PedidoResponse)
async def agregar_articulos_pedido(
    pedido_id: int,
    data: AgregarArticulosRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    Agregar artículos a un pedido existente.
    Comportamiento diferente según el estado del pedido:
    - pendiente: Agregar al pedido actual, re-enviar completo a KDS
    - preparando/listo/entregado: Agregar al pedido, enviar SOLO artículos nuevos a KDS
    """
    # Validar permisos
    if current_user.rol not in ["mesero", "administrador"]:
        raise HTTPException(
            status_code=403,
            detail="Solo meseros y administradores pueden agregar artículos"
        )
    
    # Validar que hay artículos
    if len(data.articulos) == 0:
        raise HTTPException(
            status_code=400,
            detail="Debe agregar al menos un artículo"
        )
    
    # Buscar el pedido
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(
            status_code=404,
            detail="Pedido no encontrado"
        )
    
    # Validar que el pedido no esté en estados finales
    if pedido.estado in ["cuenta_solicitada", "pagado", "cancelado"]:
        raise HTTPException(
            status_code=400,
            detail=f"No se pueden agregar artículos a pedidos en estado '{pedido.estado}'"
        )
    
    # Validar permisos de acceso por sucursal
    if current_user.rol != "administrador" and pedido.sucursal_id != current_user.sucursal_id:
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para modificar este pedido"
        )
    
    # Validar y procesar artículos
    articulos_calculados = []
    total_agregado = Decimal('0')
    
    for articulo_data in data.articulos:
        # Validar que el platillo existe
        platillo = db.query(Platillo).filter(Platillo.id == articulo_data.platillo_id).first()
        if not platillo:
            raise HTTPException(
                status_code=400,
                detail=f"Platillo con ID {articulo_data.platillo_id} no encontrado"
            )
        
        # Validar que el platillo esté disponible
        if platillo.estado != "disponible":
            raise HTTPException(
                status_code=400,
                detail=f"El platillo '{platillo.nombre}' no está disponible"
            )
        
        # Validar cantidad
        if articulo_data.cantidad <= 0:
            raise HTTPException(
                status_code=400,
                detail="La cantidad debe ser mayor a 0"
            )
        
        # Calcular precio
        precio_cobrado = platillo.precio * articulo_data.cantidad
        total_agregado += precio_cobrado
        
        # Crear artículo calculado
        articulo_calculado = {
            "platillo_id": articulo_data.platillo_id,
            "cantidad": articulo_data.cantidad,
            "precio_cobrado": float(precio_cobrado),  # Convertir a float para JSON
            "modificaciones": articulo_data.modificaciones or ""
        }
        articulos_calculados.append(articulo_calculado)
    
    # Crear los nuevos artículos
    nuevos_articulos = []
    for articulo_data in articulos_calculados:
        # Obtener el platillo para verificar si es bebida
        platillo = db.query(Platillo).filter(Platillo.id == articulo_data["platillo_id"]).first()
        
        # Si es bebida, marcarla como "entregado" automáticamente
        estado_inicial = "entregado" if platillo and platillo.categoria == "Bebidas" else "pendiente"
        
        articulo = ArticuloPedido(
            pedido_id=pedido.id,
            platillo_id=articulo_data["platillo_id"],
            cantidad=articulo_data["cantidad"],
            precio_cobrado=articulo_data["precio_cobrado"],
            modificaciones=articulo_data["modificaciones"],
            estado_item=estado_inicial  # Bebidas = "entregado", resto = "pendiente"
        )
        db.add(articulo)
        nuevos_articulos.append(articulo)
    
    # Actualizar total del pedido
    pedido.total += total_agregado
    
    # Si el pedido estaba en "pendiente", mantenerlo así para re-procesar todo
    # Si estaba en otros estados, los artículos nuevos van a cocina como "agregados"
    # Si el pedido estaba "entregado", volver a "pendiente" para que aparezca en KDS
    estado_original = pedido.estado
    if pedido.estado == "entregado":
        pedido.estado = "pendiente"
        # REINICIAR TEMPORIZADOR: Actualizar fecha de creación para que vaya al final de la cola
        pedido.fecha_creacion = datetime.now()
    
    db.commit()
    db.refresh(pedido)
    
    # Notificaciones WebSocket según el estado
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
        
        if estado_original == "pendiente" or estado_original == "entregado":
            # Re-enviar pedido completo actualizado
            # Si era "pendiente": mantener flujo normal
            # Si era "entregado": ahora es "pendiente" y debe aparecer en KDS con solo artículos no entregados
            await websocket_manager.notify_pedido_estado_changed(
                pedido_id=pedido.id,
                nuevo_estado=pedido.estado,
                pedido_data=pedido_data
            )
        else:
            # Para otros estados (preparando, listo): Enviar solo artículos nuevos como "agregados"
            articulos_agregados_data = {
                "id": f"{pedido.id}-agregado",  # ID especial para agregados
                "numero_display": f"{pedido.numero_display}-A",
                "nombre_cliente": pedido.nombre_cliente,
                "mesa": pedido.mesa,
                "total": float(total_agregado),
                "estado": "pendiente",  # Los agregados siempre empiezan como pendiente
                "tipo_orden": pedido.tipo_orden,
                "sucursal_id": pedido.sucursal_id,
                "fecha_creacion": datetime.now().isoformat(),
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
                    } for a in nuevos_articulos
                ]
            }
            await websocket_manager.notify_pedido_created(articulos_agregados_data)
        
    except Exception as e:
        # Log del error pero no fallar la operación
        print(f"Error notifying articulos agregados via WebSocket: {e}")
    
    return pedido


@router.put("/{pedido_id}/actualizar-articulos", response_model=PedidoResponse)
async def actualizar_articulos_pedido(
    pedido_id: int,
    data: dict,  # {"articulos": [{"id": int, "cantidad": int, "modificaciones": str}]}
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    Actualizar artículos de un pedido existente.
    Solo permitido para pedidos en estado 'pendiente'.
    """
    # Validar permisos
    if current_user.rol not in ["mesero", "administrador"]:
        raise HTTPException(
            status_code=403,
            detail="Solo meseros y administradores pueden modificar pedidos"
        )
    
    # Buscar el pedido
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(
            status_code=404,
            detail="Pedido no encontrado"
        )
    
    # Validar que el pedido esté en estado pendiente
    if pedido.estado != "pendiente":
        raise HTTPException(
            status_code=400,
            detail=f"Solo se pueden modificar pedidos en estado 'pendiente'. Estado actual: '{pedido.estado}'"
        )
    
    # Validar permisos de acceso por sucursal
    if current_user.rol != "administrador" and pedido.sucursal_id != current_user.sucursal_id:
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para modificar este pedido"
        )
    
    # Validar estructura de data
    if "articulos" not in data or not isinstance(data["articulos"], list):
        raise HTTPException(
            status_code=400,
            detail="Se requiere campo 'articulos' como lista"
        )
    
    # Obtener artículos actuales del pedido
    articulos_actuales = {a.id: a for a in pedido.articulos_pedido}
    nuevo_total = Decimal('0')
    
    # Procesar cada artículo actualizado
    for articulo_data in data["articulos"]:
        if "id" not in articulo_data or "cantidad" not in articulo_data:
            raise HTTPException(
                status_code=400,
                detail="Cada artículo debe tener 'id' y 'cantidad'"
            )
        
        articulo_id = articulo_data["id"]
        nueva_cantidad = articulo_data["cantidad"]
        nuevas_modificaciones = articulo_data.get("modificaciones", "")
        
        # Validar que el artículo pertenece a este pedido
        if articulo_id not in articulos_actuales:
            raise HTTPException(
                status_code=400,
                detail=f"Artículo con ID {articulo_id} no pertenece a este pedido"
            )
        
        articulo = articulos_actuales[articulo_id]
        
        # Validar cantidad
        if nueva_cantidad < 0:
            raise HTTPException(
                status_code=400,
                detail="La cantidad no puede ser negativa"
            )
        
        if nueva_cantidad == 0:
            # Eliminar artículo
            db.delete(articulo)
            continue
        
        # Actualizar artículo
        articulo.cantidad = nueva_cantidad
        articulo.modificaciones = nuevas_modificaciones
        
        # Recalcular precio basado en nueva cantidad
        articulo.precio_cobrado = articulo.platillo.precio * nueva_cantidad
        nuevo_total += articulo.precio_cobrado
    
    # Actualizar total del pedido
    pedido.total = nuevo_total
    
    # Commit cambios
    db.commit()
    db.refresh(pedido)
    
    # Notificar via WebSocket que el pedido se actualizó
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
        
        print(f"📡 SENDING WebSocket notification: pedido {pedido.id} actualizado")
        await websocket_manager.notify_pedido_estado_changed(
            pedido_id=pedido.id,
            nuevo_estado=pedido.estado,
            pedido_data=pedido_data
        )
        print(f"✅ WebSocket notification sent successfully for pedido {pedido.id}")
        
    except Exception as e:
        # Log del error pero no fallar la operación
        print(f"❌ Error notifying pedido actualizado via WebSocket: {e}")
        import traceback
        traceback.print_exc()
    
    return pedido
