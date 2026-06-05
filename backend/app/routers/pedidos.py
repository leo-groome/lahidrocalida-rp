from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, cast
from sqlalchemy import Integer as SAInteger
from typing import List, Optional
from sqlalchemy.exc import IntegrityError
from datetime import datetime, date, timedelta
from decimal import Decimal
import requests

from app.db.session import get_db
from app.models import Pedido, ArticuloPedido, Platillo, Usuario, Turno
from app.utils.timezone import get_mexico_now, MEXICO_TZ
from app.schemas import (
    PedidoCreate,
    PedidoResponse,
    PedidoUpdate,
    ArticuloPedidoUpdate,
    AgregarArticulosRequest,
    DividirCuentaRequest,
    DividirCuentaResponse,
    DividirPorMontoRequest,
)
from app.auth import get_current_active_user, get_optional_current_user
from app.websocket_manager import websocket_manager
from app.core.config import settings


def _get_turno_activo(db: Session, sucursal_id: int) -> Optional[Turno]:
    """Obtener el turno activo de una sucursal."""
    return db.query(Turno).filter(
        Turno.sucursal_id == sucursal_id,
        Turno.estado == "abierto"
    ).first()

router = APIRouter(prefix="/pedidos", tags=["pedidos"])

async def print_ticket_automatic(pedido_data):
    """
    Envía ticket al servicio de impresión automática
    """
    try:
        print_service_url = "http://localhost:3001/print"

        # Preparar datos del ticket para impresión
        ticket_data = {
            "numero_display": pedido_data.get("numero_display", "N/A"),
            "mesa": pedido_data.get("mesa"),
            "nombre_cliente": pedido_data.get("nombre_cliente"),
            "mesero_nombre": None,  # Se puede agregar si se tiene la información
            "fecha_llegada": pedido_data.get("fecha_creacion"),
            "fecha_salida": pedido_data.get("fecha_salida"),
            "articulos": [
                {
                    "cantidad": articulo.get("cantidad", 1),
                    "nombre": articulo.get("platillo", {}).get("nombre", "Producto"),
                    "precio": articulo.get("precio_cobrado", 0),
                    "modificaciones": articulo.get("modificaciones")
                }
                for articulo in pedido_data.get("articulos_pedido", [])
            ],
            "total": pedido_data.get("total", 0)
        }

        # Enviar al servicio de impresión
        response = requests.post(
            print_service_url,
            json=ticket_data,
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Ticket #{pedido_data.get('numero_display', 'N/A')} enviado a impresión automática: {result}")
        else:
            print(f"⚠️  Error en impresión automática: {response.status_code} - {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión con servicio de impresión: {e}")
        # No fallar la transacción principal por error de impresión
    except Exception as e:
        print(f"❌ Error en impresión automática: {e}")
        # No fallar la transacción principal por error de impresión


def generate_numero_display(db: Session, sucursal_id: int) -> str:
    """
    Genera el número de display secuencial por día y sucursal.
    Formato: 001, 002, 003, etc.
    Se reinicia automáticamente cada día en zona horaria local.
    """
    now_local = get_mexico_now()
    today_local = now_local.date()
    
    # Rango del día actual en zona horaria de México
    start_dt = datetime.combine(today_local, datetime.min.time(), tzinfo=MEXICO_TZ)
    end_dt = datetime.combine(today_local + timedelta(days=1), datetime.min.time(), tzinfo=MEXICO_TZ)

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

    # Verificar que hay turno activo — sin turno no se acepta ningún pedido
    turno_activo = _get_turno_activo(db, current_user.sucursal_id)
    if not turno_activo:
        raise HTTPException(
            status_code=400,
            detail="No hay turno activo en esta sucursal. El cajero debe abrir turno antes de tomar pedidos."
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
                usuario_id=current_user.id,
                turno_id=turno_activo.id,
            )

            db.add(pedido)
            db.flush()  # Para obtener el ID del pedido

            # Crear los artículos del pedido
            for articulo_data in articulos_calculados:
                # Obtener el platillo para verificar si es bebida
                platillo = db.query(Platillo).filter(Platillo.id == articulo_data['platillo_id']).first()
                
                # Todos los items inician en pendiente; bebidas se marcan manualmente por mesero si aplica
                estado_inicial = "pendiente"

                articulo = ArticuloPedido(
                    pedido_id=pedido.id,
                    platillo_id=articulo_data['platillo_id'],
                    cantidad=articulo_data['cantidad'],
                    precio_cobrado=articulo_data['precio_cobrado'],
                    modificaciones=articulo_data['modificaciones'],
                    estado_item=estado_inicial
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
            "metodo_pago": pedido.metodo_pago,
            "propina_efectivo": float(pedido.propina_efectivo),
            "propina_tarjeta": float(pedido.propina_tarjeta),
            "propina_total": float(pedido.propina_efectivo + pedido.propina_tarjeta),
            "articulos_pedido": [
                        {
                            "id": a.id,
                            "cantidad": a.cantidad,
                            "precio_cobrado": float(a.precio_cobrado),
                            "modificaciones": a.modificaciones,
                            "estado_item": a.estado_item,
                            "platillo": {
                                "nombre": a.platillo.nombre,
                                "kds_name": a.platillo.kds_name,
                                "categoria": a.platillo.categoria
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


@router.get("", response_model=List[PedidoResponse])
def list_pedidos(
    estado: Optional[str] = None,
    turno_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Optional[Usuario] = Depends(get_optional_current_user)
):
    """
    Listar pedidos.
    - Sin auth (KDS): devuelve pedidos activos (no pagados/cancelados) sin filtro de fecha.
    - Con auth: filtra por turno activo o turno_id explícito.
    """
    ESTADOS_VALIDOS = ["pendiente", "preparando", "listo", "entregado", "cuenta_solicitada", "pagado", "cancelado", "dividido"]

    if estado and estado not in ESTADOS_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Estado inválido. Valores permitidos: {', '.join(ESTADOS_VALIDOS)}"
        )

    if current_user is None:
        # Modo KDS público — pedidos activos sin filtro de fecha ni sucursal
        estados_kds = ["pendiente", "preparando", "listo", "entregado", "cuenta_solicitada"]
        query = db.query(Pedido)
        if estado and estado in estados_kds:
            query = query.filter(Pedido.estado == estado)
        else:
            query = query.filter(Pedido.estado.in_(estados_kds))
        return query.order_by(Pedido.fecha_creacion.asc()).all()

    # Con autenticación — filtro por turno
    if turno_id:
        query = db.query(Pedido).filter(Pedido.turno_id == turno_id)
    else:
        turno_activo = _get_turno_activo(db, current_user.sucursal_id)
        if turno_activo:
            query = db.query(Pedido).filter(Pedido.turno_id == turno_activo.id)
        else:
            # Sin turno activo: fallback a pedidos del día actual
            now_local = get_mexico_now()
            today_local = now_local.date()
            start_dt = datetime.combine(today_local, datetime.min.time(), tzinfo=MEXICO_TZ)
            end_dt = datetime.combine(today_local + timedelta(days=1), datetime.min.time(), tzinfo=MEXICO_TZ)
            query = db.query(Pedido).filter(
                Pedido.fecha_creacion >= start_dt,
                Pedido.fecha_creacion < end_dt
            )

    # Filtro por sucursal según rol
    if current_user.rol == "cajero":
        query = query.filter(Pedido.sucursal_id == current_user.sucursal_id)

    if estado:
        query = query.filter(Pedido.estado == estado)

    return query.order_by(Pedido.fecha_creacion.desc()).all()


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
    current_user: Optional[Usuario] = Depends(get_optional_current_user)
):
    """
    Obtener un pedido específico por ID.
    Público para KDS (sin auth). Con auth: cajeros solo ven su sucursal.
    """
    pedido = (
        db.query(Pedido)
        .options(joinedload(Pedido.articulos_pedido).joinedload(ArticuloPedido.platillo))
        .filter(Pedido.id == pedido_id)
        .first()
    )
    
    if not pedido:
        raise HTTPException(
            status_code=404,
            detail="Pedido no encontrado"
        )
    
    # Con auth: cajeros solo ven su sucursal
    if current_user and current_user.rol == "cajero" and pedido.sucursal_id != current_user.sucursal_id:
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para ver este pedido"
        )

    return pedido


@router.post("/{pedido_id}/dividir", response_model=DividirCuentaResponse)
async def dividir_cuenta(
    pedido_id: int,
    data: DividirCuentaRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    """Dividir una cuenta por articulos (solo administrador)."""

    if current_user.rol != "administrador":
        raise HTTPException(status_code=403, detail="Solo administradores pueden dividir cuentas")

    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    if pedido.estado not in ["entregado", "cuenta_solicitada"]:
        raise HTTPException(
            status_code=400,
            detail="Solo se puede dividir un pedido en estado 'entregado' o 'cuenta_solicitada'",
        )

    if not data.cuentas or len(data.cuentas) < 2:
        raise HTTPException(status_code=400, detail="Debe especificar al menos 2 cuentas")

    if len(data.cuentas) > 5:
        raise HTTPException(status_code=400, detail="Maximo 5 cuentas")

    articulos_originales = db.query(ArticuloPedido).filter(ArticuloPedido.pedido_id == pedido.id).all()
    if not articulos_originales:
        raise HTTPException(status_code=400, detail="El pedido no tiene articulos")

    articulos_por_id = {a.id: a for a in articulos_originales}

    # Validar reparto exacto por articulo
    asignado_por_articulo: dict[int, int] = {a.id: 0 for a in articulos_originales}

    for cuenta in data.cuentas:
        if not cuenta.items:
            raise HTTPException(status_code=400, detail="Cada cuenta debe tener items")
        for item in cuenta.items:
            if item.articulo_id not in articulos_por_id:
                raise HTTPException(status_code=400, detail=f"Articulo {item.articulo_id} no pertenece a este pedido")
            if item.cantidad <= 0:
                raise HTTPException(status_code=400, detail="La cantidad debe ser mayor a 0")
            asignado_por_articulo[item.articulo_id] += item.cantidad

    for articulo_id, articulo in articulos_por_id.items():
        if asignado_por_articulo.get(articulo_id, 0) != int(articulo.cantidad):
            raise HTTPException(
                status_code=400,
                detail=f"El articulo {articulo_id} no fue repartido correctamente",
            )

    # Marcar pedido original como dividido
    old_estado = pedido.estado
    pedido.estado = "dividido"
    db.commit()
    db.refresh(pedido)

    cuentas_creadas: List[Pedido] = []

    # Helper para construir nombre_cliente con Cuenta i/n
    def build_nombre_cliente(nombre_base: Optional[str], i: int, total: int) -> str:
        base = (nombre_base or "").strip()
        label = f"Cuenta {i}/{total}"
        if base:
            return f"{base} {label}"
        return label

    total_cuentas = len(data.cuentas)

    for i, cuenta in enumerate(data.cuentas, start=1):
        numero_display = generate_numero_display(db, pedido.sucursal_id)

        nombre_cliente_nuevo = build_nombre_cliente(pedido.nombre_cliente, i, total_cuentas)

        nuevo_pedido = Pedido(
            numero_display=numero_display,
            nombre_cliente=nombre_cliente_nuevo,
            mesa=pedido.mesa,
            total=Decimal("0"),
            estado="cuenta_solicitada",
            metodo_pago=None,
            tipo_orden=pedido.tipo_orden,
            sucursal_id=pedido.sucursal_id,
            usuario_id=pedido.usuario_id,
        )

        db.add(nuevo_pedido)
        db.flush()

        total_cuenta = Decimal("0")

        for item in cuenta.items:
            articulo_original = articulos_por_id[item.articulo_id]

            precio_unitario = Decimal(str(articulo_original.precio_cobrado)) / Decimal(str(articulo_original.cantidad))
            precio_cobrado = precio_unitario * Decimal(str(item.cantidad))
            total_cuenta += precio_cobrado

            estado_item = articulo_original.estado_item

            articulo_nuevo = ArticuloPedido(
                pedido_id=nuevo_pedido.id,
                platillo_id=articulo_original.platillo_id,
                cantidad=item.cantidad,
                precio_cobrado=float(precio_cobrado),
                modificaciones=articulo_original.modificaciones,
                estado_item=estado_item,
            )
            db.add(articulo_nuevo)

        nuevo_pedido.total = total_cuenta
        db.commit()
        db.refresh(nuevo_pedido)
        cuentas_creadas.append(nuevo_pedido)

    # Notificar por WebSocket
    try:
        pedido_original_data = {
            "id": pedido.id,
            "numero_display": pedido.numero_display,
            "nombre_cliente": pedido.nombre_cliente,
            "mesa": pedido.mesa,
            "total": float(pedido.total),
            "estado": pedido.estado,
            "tipo_orden": pedido.tipo_orden,
            "sucursal_id": pedido.sucursal_id,
            "fecha_creacion": pedido.fecha_creacion.isoformat(),
            "fecha_pago": pedido.fecha_pago.isoformat() if pedido.fecha_pago else None,
            "usuario_nombre": pedido.usuario.nombre if pedido.usuario else None,
            "metodo_pago": pedido.metodo_pago,
            "propina_efectivo": float(pedido.propina_efectivo),
            "propina_tarjeta": float(pedido.propina_tarjeta),
            "propina_total": float(pedido.propina_efectivo + pedido.propina_tarjeta),
            "articulos_pedido": [
                {
                    "id": a.id,
                    "cantidad": a.cantidad,
                    "precio_cobrado": float(a.precio_cobrado),
                    "modificaciones": a.modificaciones,
                    "estado_item": a.estado_item,
                    "platillo": {
                        "nombre": a.platillo.nombre,
                        "kds_name": a.platillo.kds_name,
                        "categoria": a.platillo.categoria,
                    }
                    if a.platillo
                    else None,
                }
                for a in pedido.articulos_pedido
            ],
        }

        if old_estado != pedido.estado:
            await websocket_manager.notify_pedido_estado_changed(
                pedido_id=pedido.id,
                nuevo_estado=pedido.estado,
                pedido_data=pedido_original_data,
            )

        for cuenta_pedido in cuentas_creadas:
            cuenta_data = {
                "id": cuenta_pedido.id,
                "numero_display": cuenta_pedido.numero_display,
                "nombre_cliente": cuenta_pedido.nombre_cliente,
                "mesa": cuenta_pedido.mesa,
                "total": float(cuenta_pedido.total),
                "estado": cuenta_pedido.estado,
                "tipo_orden": cuenta_pedido.tipo_orden,
                "sucursal_id": cuenta_pedido.sucursal_id,
                "fecha_creacion": cuenta_pedido.fecha_creacion.isoformat(),
                "metodo_pago": cuenta_pedido.metodo_pago,
                "propina_efectivo": float(cuenta_pedido.propina_efectivo),
                "propina_tarjeta": float(cuenta_pedido.propina_tarjeta),
                "propina_total": float(cuenta_pedido.propina_efectivo + cuenta_pedido.propina_tarjeta),
                "articulos_pedido": [
                    {
                        "id": a.id,
                        "cantidad": a.cantidad,
                        "precio_cobrado": float(a.precio_cobrado),
                        "modificaciones": a.modificaciones,
                        "estado_item": a.estado_item,
                        "platillo": {
                            "nombre": a.platillo.nombre,
                            "kds_name": a.platillo.kds_name,
                        }
                        if a.platillo
                        else None,
                    }
                    for a in cuenta_pedido.articulos_pedido
                ],
            }
            await websocket_manager.notify_pedido_created(cuenta_data)

    except Exception as e:
        print(f"Error notifying dividir cuenta via WebSocket: {e}")

    return {
        "pedido_original_id": pedido.id,
        "cuentas": cuentas_creadas,
    }


@router.post("/{pedido_id}/dividir_por_montos", response_model=DividirCuentaResponse)
async def dividir_por_montos(
    pedido_id: int,
    data: DividirPorMontoRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    """Dividir una cuenta por montos arbitrarios sin asignar articulos (solo administrador)."""

    if current_user.rol != "administrador":
        raise HTTPException(status_code=403, detail="Solo administradores pueden dividir cuentas")

    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    if pedido.estado not in ["entregado", "cuenta_solicitada"]:
        raise HTTPException(
            status_code=400,
            detail="Solo se puede dividir un pedido en estado 'entregado' o 'cuenta_solicitada'",
        )

    if not data.cuentas or len(data.cuentas) < 2:
        raise HTTPException(status_code=400, detail="Debe especificar al menos 2 cuentas")

    for cuenta in data.cuentas:
        if cuenta.monto <= 0:
            raise HTTPException(status_code=400, detail="Cada monto debe ser mayor a 0")

    suma_montos = sum(c.monto for c in data.cuentas)
    if abs(suma_montos - pedido.total) > Decimal("0.05"):
        raise HTTPException(
            status_code=400,
            detail=f"La suma de los montos ({suma_montos}) no coincide con el total del pedido ({pedido.total})",
        )

    def build_nombre_cliente(nombre_base, i, total):
        base = (nombre_base or "").strip()
        label = f"Cuenta {i}/{total}"
        return f"{base} {label}" if base else label

    old_estado = pedido.estado
    pedido.estado = "dividido"
    db.commit()
    db.refresh(pedido)

    cuentas_creadas: List[Pedido] = []
    total_cuentas = len(data.cuentas)

    for i, cuenta in enumerate(data.cuentas, start=1):
        numero_display = generate_numero_display(db, pedido.sucursal_id)
        nombre_cliente_nuevo = build_nombre_cliente(pedido.nombre_cliente, i, total_cuentas)

        nuevo_pedido = Pedido(
            numero_display=numero_display,
            nombre_cliente=nombre_cliente_nuevo,
            mesa=pedido.mesa,
            total=cuenta.monto,
            estado="cuenta_solicitada",
            metodo_pago=None,
            tipo_orden=pedido.tipo_orden,
            sucursal_id=pedido.sucursal_id,
            usuario_id=pedido.usuario_id,
        )

        db.add(nuevo_pedido)
        db.commit()
        db.refresh(nuevo_pedido)
        cuentas_creadas.append(nuevo_pedido)

    # Notificar por WebSocket
    try:
        pedido_original_data = {
            "id": pedido.id,
            "numero_display": pedido.numero_display,
            "nombre_cliente": pedido.nombre_cliente,
            "mesa": pedido.mesa,
            "total": float(pedido.total),
            "estado": pedido.estado,
            "tipo_orden": pedido.tipo_orden,
            "sucursal_id": pedido.sucursal_id,
            "fecha_creacion": pedido.fecha_creacion.isoformat(),
            "fecha_pago": pedido.fecha_pago.isoformat() if pedido.fecha_pago else None,
            "usuario_nombre": pedido.usuario.nombre if pedido.usuario else None,
            "metodo_pago": pedido.metodo_pago,
            "propina_efectivo": float(pedido.propina_efectivo),
            "propina_tarjeta": float(pedido.propina_tarjeta),
            "propina_total": float(pedido.propina_efectivo + pedido.propina_tarjeta),
            "articulos_pedido": [],
        }

        if old_estado != pedido.estado:
            await websocket_manager.notify_pedido_estado_changed(
                pedido_id=pedido.id,
                nuevo_estado=pedido.estado,
                pedido_data=pedido_original_data,
            )

        for cuenta_pedido in cuentas_creadas:
            cuenta_data = {
                "id": cuenta_pedido.id,
                "numero_display": cuenta_pedido.numero_display,
                "nombre_cliente": cuenta_pedido.nombre_cliente,
                "mesa": cuenta_pedido.mesa,
                "total": float(cuenta_pedido.total),
                "estado": cuenta_pedido.estado,
                "tipo_orden": cuenta_pedido.tipo_orden,
                "sucursal_id": cuenta_pedido.sucursal_id,
                "fecha_creacion": cuenta_pedido.fecha_creacion.isoformat(),
                "metodo_pago": cuenta_pedido.metodo_pago,
                "propina_efectivo": float(cuenta_pedido.propina_efectivo),
                "propina_tarjeta": float(cuenta_pedido.propina_tarjeta),
                "propina_total": float(cuenta_pedido.propina_efectivo + cuenta_pedido.propina_tarjeta),
                "articulos_pedido": [],
            }
            await websocket_manager.notify_pedido_created(cuenta_data)

    except Exception as e:
        print(f"Error notifying dividir_por_montos via WebSocket: {e}")

    return {
        "pedido_original_id": pedido.id,
        "cuentas": cuentas_creadas,
    }


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
        "administrador": ["pendiente", "preparando", "listo", "entregado", "cuenta_solicitada", "pagado", "cancelado", "dividido"]
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
    if data.estado not in ["pendiente", "preparando", "listo", "entregado", "cuenta_solicitada", "pagado", "cancelado", "dividido"]:
        raise HTTPException(
            status_code=400,
            detail="Estado inválido. Valores permitidos: pendiente, preparando, listo, entregado, cuenta_solicitada, pagado, cancelado, dividido"
        )
    
    # Validar propinas (no negativas)
    if data.propina_efectivo is not None and data.propina_efectivo < 0:
        raise HTTPException(
            status_code=400,
            detail="La propina en efectivo no puede ser negativa"
        )
    if data.propina_tarjeta is not None and data.propina_tarjeta < 0:
        raise HTTPException(
            status_code=400,
            detail="La propina en tarjeta no puede ser negativa"
        )
    
    # Actualizar estado
    old_estado = pedido.estado
    pedido.estado = data.estado

    # Registrar fecha de pago cuando se marca como pagado
    if data.estado == "pagado" and pedido.fecha_pago is None:
        pedido.fecha_pago = get_mexico_now()
    
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
    
    # Actualizar propinas si se proporcionan
    if data.propina_efectivo is not None:
        pedido.propina_efectivo = data.propina_efectivo
    if data.propina_tarjeta is not None:
        pedido.propina_tarjeta = data.propina_tarjeta
    
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
                "propina_efectivo": float(pedido.propina_efectivo),
                "propina_tarjeta": float(pedido.propina_tarjeta),
                "propina_total": float(pedido.propina_efectivo + pedido.propina_tarjeta),
                "articulos_pedido": [
                    {
                        "id": a.id,
                        "cantidad": a.cantidad,
                        "precio_cobrado": float(a.precio_cobrado),
                        "modificaciones": a.modificaciones,
                        "estado_item": a.estado_item,
                    "platillo": {
                        "nombre": a.platillo.nombre,
                        "kds_name": a.platillo.kds_name,
                        "categoria": a.platillo.categoria
                    } if a.platillo else None
                    } for a in pedido.articulos_pedido
                ]
            }
            await websocket_manager.notify_pedido_estado_changed(
                pedido_id=pedido.id,
                nuevo_estado=data.estado,
                pedido_data=pedido_data
            )

            # Integración automática con servicio de impresión
            if data.estado == "cuenta_solicitada":
                try:
                    await print_ticket_automatic(pedido_data)
                except Exception as e:
                    print(f"Error en impresión automática: {e}")
                    # No fallar la actualización del pedido por error de impresión

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
    if data.estado_item not in ["pendiente", "preparando", "listo", "entregado"]:
        raise HTTPException(
            status_code=400,
            detail="Estado inválido. Valores permitidos: pendiente, preparando, listo, entregado"
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
                "metodo_pago": pedido.metodo_pago,
                "propina_efectivo": float(pedido.propina_efectivo),
                "propina_tarjeta": float(pedido.propina_tarjeta),
                "propina_total": float(pedido.propina_efectivo + pedido.propina_tarjeta),
                "articulos_pedido": [
                    {
                        "id": a.id,
                        "cantidad": a.cantidad,
                        "precio_cobrado": float(a.precio_cobrado),
                        "modificaciones": a.modificaciones,
                        "estado_item": a.estado_item,
                    "platillo": {
                        "nombre": a.platillo.nombre,
                        "kds_name": a.platillo.kds_name,
                        "categoria": a.platillo.categoria
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
        
        # Todos los items inician en pendiente; bebidas se marcan manualmente por mesero si aplica
        estado_inicial = "pendiente"

        articulo = ArticuloPedido(
            pedido_id=pedido.id,
            platillo_id=articulo_data["platillo_id"],
            cantidad=articulo_data["cantidad"],
            precio_cobrado=articulo_data["precio_cobrado"],
            modificaciones=articulo_data["modificaciones"],
            estado_item=estado_inicial
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
        
        # Siempre enviar actualización del pedido completo
        # Esto agrupa los artículos nuevos con los existentes visualmente en lugar de crear un "-A" temporal
        await websocket_manager.notify_pedido_estado_changed(
            pedido_id=pedido.id,
            nuevo_estado=pedido.estado,
            pedido_data=pedido_data
        )
        
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
    Permitido para pedidos en cualquier estado excepto finales.
    """
    # Validar permisos
    if current_user.rol not in ["mesero", "administrador", "cajero"]:
        raise HTTPException(
            status_code=403,
            detail="Solo meseros, cajeros y administradores pueden modificar pedidos"
        )
    
    # Buscar el pedido
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(
            status_code=404,
            detail="Pedido no encontrado"
        )
    
    # Validar que el pedido no esté en estados finales
    if pedido.estado in ["pagado", "cancelado", "dividido"]:
        raise HTTPException(
            status_code=400,
            detail=f"No se pueden modificar pedidos en estado '{pedido.estado}'"
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


@router.post("/{pedido_id}/imprimir", response_model=dict)
async def imprimir_ticket_pedido(
    pedido_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    Imprimir el ticket de un pedido manualmente.
    Disponible para meseros, cajeros y administradores.
    """
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    
    # Validar que el pedido tiene artículos
    if not pedido.articulos_pedido:
        raise HTTPException(status_code=400, detail="El pedido no tiene artículos para imprimir")

    # Validar permisos de acceso por sucursal
    if current_user.rol != "administrador" and pedido.sucursal_id != current_user.sucursal_id:
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para imprimir este pedido"
        )

    # Preparar datos para impresión
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
        "fecha_salida": pedido.fecha_pago.isoformat() if pedido.fecha_pago else None,
        "articulos_pedido": [
            {
                "cantidad": a.cantidad,
                "precio_cobrado": float(a.precio_cobrado),
                "modificaciones": a.modificaciones,
                "platillo": {
                    "nombre": a.platillo.nombre
                } if a.platillo else None
            } for a in pedido.articulos_pedido
        ]
    }

    # Programar impresión en segundo plano; no bloquea la respuesta
    try:
        background_tasks.add_task(print_ticket_automatic, pedido_data)
        return {"status": "ok", "message": "Ticket en cola de impresión"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al imprimir: {str(e)}")
