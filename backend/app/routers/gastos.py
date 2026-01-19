from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, func

from app.auth import get_current_active_user
from app.db.session import get_db
from app.models import (
    Articulo,
    CategoriaArticulo,
    Gasto,
    GastoDetalle,
    Proveedor,
    Usuario,
)
from app.schemas import (
    ArticuloCreate,
    ArticuloResponse,
    CategoriaArticuloCreate,
    CategoriaArticuloResponse,
    GastoCreate,
    GastoResponse,
    ProveedorCreate,
    ProveedorResponse,
)

router = APIRouter(prefix="/gastos", tags=["gastos"])

TIPOS_GASTO = {"directo", "indirecto", "nomina"}
METODOS_PAGO = {"efectivo", "tarjeta"}
UNIDADES_PERMITIDAS = {"kg", "g", "lt", "ml", "pza", "caja", "paq"}


def _ensure_can_manage_gastos(user: Usuario) -> None:
    if user.rol not in ["administrador", "compras"]:
        raise HTTPException(status_code=403, detail="No autorizado para gestionar gastos")


def _normalize_decimal(value: Decimal) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _parse_date(value: Optional[str], label: str) -> Optional[date]:
    if value is None or value == "":
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Formato de {label} inválido. Use YYYY-MM-DD")


def _validate_gasto_inputs(data: GastoCreate) -> None:
    if data.tipo_gasto not in TIPOS_GASTO:
        raise HTTPException(status_code=400, detail="Tipo de gasto inválido")
    if data.metodo_pago not in METODOS_PAGO:
        raise HTTPException(status_code=400, detail="Método de pago inválido")


@router.get("/proveedores", response_model=List[ProveedorResponse])
def list_proveedores(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    query = db.query(Proveedor)
    if current_user.sucursal_id is not None:
        query = query.filter(Proveedor.sucursal_id == current_user.sucursal_id)
    return query.order_by(func.lower(Proveedor.nombre).asc()).all()


@router.post("/proveedores", response_model=ProveedorResponse, status_code=status.HTTP_201_CREATED)
def create_proveedor(
    data: ProveedorCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    _ensure_can_manage_gastos(current_user)
    proveedor = Proveedor(
        nombre=data.nombre,
        telefono=data.telefono,
        direccion=data.direccion,
        notas=data.notas,
        sucursal_id=current_user.sucursal_id,
    )
    db.add(proveedor)
    db.commit()
    db.refresh(proveedor)
    return proveedor


@router.put("/proveedores/{proveedor_id}", response_model=ProveedorResponse)
def update_proveedor(
    proveedor_id: int,
    data: ProveedorCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    _ensure_can_manage_gastos(current_user)
    proveedor = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    if current_user.sucursal_id is not None and proveedor.sucursal_id != current_user.sucursal_id:
        raise HTTPException(status_code=403, detail="No autorizado para editar este proveedor")
    proveedor.nombre = data.nombre
    proveedor.telefono = data.telefono
    proveedor.direccion = data.direccion
    proveedor.notas = data.notas
    db.commit()
    db.refresh(proveedor)
    return proveedor


@router.get("/categorias-articulo", response_model=List[CategoriaArticuloResponse])
def list_categorias_articulo(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    return db.query(CategoriaArticulo).order_by(func.lower(CategoriaArticulo.nombre).asc()).all()


@router.post("/categorias-articulo", response_model=CategoriaArticuloResponse, status_code=status.HTTP_201_CREATED)
def create_categoria_articulo(
    data: CategoriaArticuloCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    _ensure_can_manage_gastos(current_user)
    existing = db.query(CategoriaArticulo).filter(CategoriaArticulo.nombre == data.nombre).first()
    if existing:
        raise HTTPException(status_code=400, detail="La categoría ya existe")
    categoria = CategoriaArticulo(nombre=data.nombre)
    db.add(categoria)
    db.commit()
    db.refresh(categoria)
    return categoria


@router.put("/categorias-articulo/{categoria_id}", response_model=CategoriaArticuloResponse)
def update_categoria_articulo(
    categoria_id: int,
    data: CategoriaArticuloCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    _ensure_can_manage_gastos(current_user)
    categoria = db.query(CategoriaArticulo).filter(CategoriaArticulo.id == categoria_id).first()
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    categoria.nombre = data.nombre
    db.commit()
    db.refresh(categoria)
    return categoria


@router.get("/articulos", response_model=List[ArticuloResponse])
def list_articulos(
    categoria_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    query = db.query(Articulo).options(joinedload(Articulo.categoria))
    if categoria_id is not None:
        query = query.filter(Articulo.categoria_id == categoria_id)
    return query.order_by(func.lower(Articulo.nombre).asc()).all()


@router.post("/articulos", response_model=ArticuloResponse, status_code=status.HTTP_201_CREATED)
def create_articulo(
    data: ArticuloCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    _ensure_can_manage_gastos(current_user)
    if data.unidad not in UNIDADES_PERMITIDAS:
        raise HTTPException(status_code=400, detail="Unidad inválida")
    categoria = db.query(CategoriaArticulo).filter(CategoriaArticulo.id == data.categoria_id).first()
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    articulo = Articulo(
        nombre=data.nombre,
        unidad=data.unidad,
        costo_estandar=_normalize_decimal(data.costo_estandar),
        categoria_id=data.categoria_id,
    )
    db.add(articulo)
    db.commit()
    db.refresh(articulo)
    return articulo


@router.put("/articulos/{articulo_id}", response_model=ArticuloResponse)
def update_articulo(
    articulo_id: int,
    data: ArticuloCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    _ensure_can_manage_gastos(current_user)
    if data.unidad not in UNIDADES_PERMITIDAS:
        raise HTTPException(status_code=400, detail="Unidad inválida")
    articulo = db.query(Articulo).filter(Articulo.id == articulo_id).first()
    if not articulo:
        raise HTTPException(status_code=404, detail="Artículo no encontrado")
    categoria = db.query(CategoriaArticulo).filter(CategoriaArticulo.id == data.categoria_id).first()
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    articulo.nombre = data.nombre
    articulo.unidad = data.unidad
    articulo.costo_estandar = _normalize_decimal(data.costo_estandar)
    articulo.categoria_id = data.categoria_id
    db.commit()
    db.refresh(articulo)
    return articulo


def _build_gasto_detalles(
    detalles_data: List,
    db: Session,
) -> tuple[list[GastoDetalle], Decimal]:
    if not detalles_data:
        return [], Decimal("0.00")
    articulo_ids = [detalle.articulo_id for detalle in detalles_data]
    articulos = db.query(Articulo).filter(Articulo.id.in_(articulo_ids)).all()
    if len(articulos) != len(set(articulo_ids)):
        raise HTTPException(status_code=400, detail="Hay artículos inválidos en el detalle")
    detalles = []
    subtotal = Decimal("0.00")
    for detalle in detalles_data:
        cantidad = _normalize_decimal(detalle.cantidad)
        precio_unitario = _normalize_decimal(detalle.precio_unitario)
        subtotal_linea = _normalize_decimal(cantidad * precio_unitario)
        subtotal += subtotal_linea
        detalles.append(
            GastoDetalle(
                articulo_id=detalle.articulo_id,
                cantidad=cantidad,
                precio_unitario=precio_unitario,
                subtotal_linea=subtotal_linea,
            )
        )
    subtotal = _normalize_decimal(subtotal)
    return detalles, subtotal


@router.post("/", response_model=GastoResponse, status_code=status.HTTP_201_CREATED)
def create_gasto(
    data: GastoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    _ensure_can_manage_gastos(current_user)
    _validate_gasto_inputs(data)

    proveedor = db.query(Proveedor).filter(Proveedor.id == data.proveedor_id).first()
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    if proveedor.sucursal_id != current_user.sucursal_id:
        raise HTTPException(status_code=403, detail="Proveedor no pertenece a tu sucursal")

    if data.tipo_gasto == "nomina":
        if data.detalles:
            raise HTTPException(status_code=400, detail="Nómina no lleva detalles de artículos")
        if data.total_manual is None:
            raise HTTPException(status_code=400, detail="Total manual requerido para nómina")
        subtotal = _normalize_decimal(data.total_manual)
        total = subtotal
        detalles = []
    else:
        if not data.detalles:
            raise HTTPException(status_code=400, detail="Se requiere al menos un artículo")
        detalles, subtotal = _build_gasto_detalles(data.detalles, db)
        total = _normalize_decimal(data.total_manual) if data.total_manual is not None else subtotal

    gasto = Gasto(
        proveedor_id=data.proveedor_id,
        tipo_gasto=data.tipo_gasto,
        metodo_pago=data.metodo_pago,
        descripcion=data.descripcion,
        folio=data.folio,
        subtotal=subtotal,
        total=total,
        total_manual=_normalize_decimal(data.total_manual) if data.total_manual is not None else None,
        notas=data.notas,
        sucursal_id=current_user.sucursal_id,
        detalles=detalles,
    )
    db.add(gasto)
    db.commit()
    db.refresh(gasto)
    return gasto


@router.get("/", response_model=List[GastoResponse])
def list_gastos(
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    proveedor_id: Optional[int] = None,
    tipo_gasto: Optional[str] = None,
    metodo_pago: Optional[str] = None,
    categoria_id: Optional[int] = None,
    sucursal_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    fecha_inicio_date = _parse_date(fecha_inicio, "fecha_inicio")
    fecha_fin_date = _parse_date(fecha_fin, "fecha_fin")

    query = (
        db.query(Gasto)
        .options(
            joinedload(Gasto.proveedor),
            joinedload(Gasto.detalles)
            .joinedload(GastoDetalle.articulo)
            .joinedload(Articulo.categoria),
        )
    )

    if current_user.rol == "compras":
        query = query.filter(Gasto.sucursal_id == current_user.sucursal_id)
    elif sucursal_id is not None:
        query = query.filter(Gasto.sucursal_id == sucursal_id)

    if proveedor_id is not None:
        query = query.filter(Gasto.proveedor_id == proveedor_id)
    if tipo_gasto is not None:
        query = query.filter(Gasto.tipo_gasto == tipo_gasto)
    if metodo_pago is not None:
        query = query.filter(Gasto.metodo_pago == metodo_pago)
    if fecha_inicio_date is not None:
        query = query.filter(Gasto.fecha_gasto >= fecha_inicio_date)
    if fecha_fin_date is not None:
        query = query.filter(Gasto.fecha_gasto <= fecha_fin_date)
    if categoria_id is not None:
        query = (
            query.join(Gasto.detalles)
            .join(GastoDetalle.articulo)
            .filter(Articulo.categoria_id == categoria_id)
            .distinct()
        )

    return query.order_by(Gasto.fecha_gasto.desc()).all()


@router.get("/{gasto_id}", response_model=GastoResponse)
def get_gasto(
    gasto_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    gasto = (
        db.query(Gasto)
        .options(
            joinedload(Gasto.proveedor),
            joinedload(Gasto.detalles)
            .joinedload(GastoDetalle.articulo)
            .joinedload(Articulo.categoria),
        )
        .filter(Gasto.id == gasto_id)
        .first()
    )
    if not gasto:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")

    if current_user.rol == "compras" and gasto.sucursal_id != current_user.sucursal_id:
        raise HTTPException(status_code=403, detail="No autorizado para ver este gasto")
    return gasto


@router.put("/{gasto_id}", response_model=GastoResponse)
def update_gasto(
    gasto_id: int,
    data: GastoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    _ensure_can_manage_gastos(current_user)
    _validate_gasto_inputs(data)

    gasto = db.query(Gasto).filter(Gasto.id == gasto_id).first()
    if not gasto:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")

    if current_user.rol == "compras" and gasto.sucursal_id != current_user.sucursal_id:
        raise HTTPException(status_code=403, detail="No autorizado para editar este gasto")

    proveedor = db.query(Proveedor).filter(Proveedor.id == data.proveedor_id).first()
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    if proveedor.sucursal_id != current_user.sucursal_id:
        raise HTTPException(status_code=403, detail="Proveedor no pertenece a tu sucursal")

    if data.tipo_gasto == "nomina":
        if data.detalles:
            raise HTTPException(status_code=400, detail="Nómina no lleva detalles de artículos")
        if data.total_manual is None:
            raise HTTPException(status_code=400, detail="Total manual requerido para nómina")
        subtotal = _normalize_decimal(data.total_manual)
        total = subtotal
        detalles = []
    else:
        if not data.detalles:
            raise HTTPException(status_code=400, detail="Se requiere al menos un artículo")
        detalles, subtotal = _build_gasto_detalles(data.detalles, db)
        total = _normalize_decimal(data.total_manual) if data.total_manual is not None else subtotal

    gasto.proveedor_id = data.proveedor_id
    gasto.tipo_gasto = data.tipo_gasto
    gasto.metodo_pago = data.metodo_pago
    gasto.descripcion = data.descripcion
    gasto.folio = data.folio
    gasto.subtotal = subtotal
    gasto.total = total
    gasto.total_manual = _normalize_decimal(data.total_manual) if data.total_manual is not None else None
    gasto.notas = data.notas

    gasto.detalles.clear()
    for detalle in detalles:
        gasto.detalles.append(detalle)

    db.commit()
    db.refresh(gasto)
    return gasto


@router.delete("/{gasto_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_gasto(
    gasto_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    _ensure_can_manage_gastos(current_user)
    gasto = db.query(Gasto).filter(Gasto.id == gasto_id).first()
    if not gasto:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")

    if current_user.rol == "compras" and gasto.sucursal_id != current_user.sucursal_id:
        raise HTTPException(status_code=403, detail="No autorizado para eliminar este gasto")

    db.delete(gasto)
    db.commit()
    return None
