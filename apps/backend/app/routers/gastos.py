from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload, selectinload

from app.auth import get_current_active_user
from app.core.cache import catalogos_cache
from app.db.session import get_db
from app.deps import require_roles
from app.models import (
    Articulo,
    CategoriaArticulo,
    Gasto,
    GastoDetalle,
    NominaDetalle,
    Proveedor,
    Usuario,
    get_local_datetime,
)
from app.schemas import (
    ArticuloCreate,
    ArticuloResponse,
    CategoriaArticuloCreate,
    CategoriaArticuloResponse,
    GastoCreate,
    GastoPorCategoria,
    GastoResponse,
    GastosResumenResponse,
    GastoTimeline,
    GastoTopProveedor,
    HistorialPrecioItem,
    HistorialPreciosResponse,
    PaginatedGastosResponse,
    ProveedorCreate,
    ProveedorResponse,
    UsuarioResponse,
)
from app.utils.timezone import MEXICO_TZ

router = APIRouter(prefix="/gastos", tags=["gastos"])

TIPOS_GASTO = {"directo", "indirecto", "nomina"}
METODOS_PAGO = {"efectivo", "tarjeta"}
UNIDADES_PERMITIDAS = {"kg", "g", "lt", "ml", "pza", "caja", "paq"}


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
    if data.tipo_gasto == "nomina":
        if data.detalles:
            raise HTTPException(status_code=400, detail="Nómina no lleva detalles de artículos")
        if not data.nomina_detalles:
            raise HTTPException(
                status_code=400, detail="Se requiere al menos un empleado en la nómina"
            )
    else:
        if data.nomina_detalles:
            raise HTTPException(status_code=400, detail="Solo la nómina lleva empleados")
        if data.proveedor_id is None:
            raise HTTPException(status_code=400, detail="Proveedor requerido")
        if not data.detalles:
            raise HTTPException(status_code=400, detail="Se requiere al menos un artículo")


def _build_nomina_detalles(
    detalles_data: List,
    db: Session,
    sucursal_id: int,
) -> tuple[list[NominaDetalle], Decimal]:
    """Valida empleados (misma sucursal, activos) y arma las líneas de nómina."""
    usuario_ids = [d.usuario_id for d in detalles_data]
    if len(usuario_ids) != len(set(usuario_ids)):
        raise HTTPException(status_code=400, detail="Empleado repetido en la nómina")
    usuarios = (
        db.query(Usuario)
        .filter(
            Usuario.id.in_(usuario_ids),
            Usuario.sucursal_id == sucursal_id,
            Usuario.activo == True,  # noqa: E712
        )
        .all()
    )
    if len(usuarios) != len(set(usuario_ids)):
        raise HTTPException(
            status_code=400, detail="Hay empleados inválidos, inactivos o de otra sucursal"
        )
    detalles = []
    total = Decimal("0.00")
    for d in detalles_data:
        monto = _normalize_decimal(d.monto)
        if monto <= 0:
            raise HTTPException(
                status_code=400, detail="El monto de cada empleado debe ser mayor a 0"
            )
        total += monto
        detalles.append(NominaDetalle(usuario_id=d.usuario_id, monto=monto, notas=d.notas))
    total = _normalize_decimal(total)
    if total <= 0:
        raise HTTPException(status_code=400, detail="El total de la nómina debe ser mayor a 0")
    return detalles, total


@router.get("/proveedores", response_model=List[ProveedorResponse])
def list_proveedores(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    cache_key = f"proveedores:{current_user.sucursal_id}"
    cached = catalogos_cache.get(cache_key)
    if cached is not None:
        return cached
    query = db.query(Proveedor)
    if current_user.sucursal_id is not None:
        query = query.filter(Proveedor.sucursal_id == current_user.sucursal_id)
    result = [
        ProveedorResponse.model_validate(p)
        for p in query.order_by(func.lower(Proveedor.nombre).asc()).all()
    ]
    catalogos_cache.set(cache_key, result)
    return result


@router.post("/proveedores", response_model=ProveedorResponse, status_code=status.HTTP_201_CREATED)
def create_proveedor(
    data: ProveedorCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("administrador", "compras", "cajero")),
):
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
    catalogos_cache.invalidate_prefix("proveedores:")
    return proveedor


@router.put("/proveedores/{proveedor_id}", response_model=ProveedorResponse)
def update_proveedor(
    proveedor_id: int,
    data: ProveedorCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("administrador", "compras", "cajero")),
):
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
    catalogos_cache.invalidate_prefix("proveedores:")
    return proveedor


@router.get("/categorias-articulo", response_model=List[CategoriaArticuloResponse])
def list_categorias_articulo(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    cached = catalogos_cache.get("categorias_articulo")
    if cached is not None:
        return cached
    result = [
        CategoriaArticuloResponse.model_validate(c)
        for c in db.query(CategoriaArticulo)
        .order_by(func.lower(CategoriaArticulo.nombre).asc())
        .all()
    ]
    catalogos_cache.set("categorias_articulo", result)
    return result


@router.post(
    "/categorias-articulo",
    response_model=CategoriaArticuloResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_categoria_articulo(
    data: CategoriaArticuloCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("administrador", "compras", "cajero")),
):
    existing = db.query(CategoriaArticulo).filter(CategoriaArticulo.nombre == data.nombre).first()
    if existing:
        raise HTTPException(status_code=400, detail="La categoría ya existe")
    categoria = CategoriaArticulo(nombre=data.nombre)
    db.add(categoria)
    db.commit()
    db.refresh(categoria)
    catalogos_cache.invalidate("categorias_articulo")
    return categoria


@router.put("/categorias-articulo/{categoria_id}", response_model=CategoriaArticuloResponse)
def update_categoria_articulo(
    categoria_id: int,
    data: CategoriaArticuloCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("administrador", "compras", "cajero")),
):
    categoria = db.query(CategoriaArticulo).filter(CategoriaArticulo.id == categoria_id).first()
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    categoria.nombre = data.nombre
    db.commit()
    db.refresh(categoria)
    catalogos_cache.invalidate("categorias_articulo")
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
    current_user: Usuario = Depends(require_roles("administrador", "compras", "cajero")),
):
    if data.unidad not in UNIDADES_PERMITIDAS:
        raise HTTPException(status_code=400, detail="Unidad inválida")
    categoria = (
        db.query(CategoriaArticulo).filter(CategoriaArticulo.id == data.categoria_id).first()
    )
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
    current_user: Usuario = Depends(require_roles("administrador", "compras", "cajero")),
):
    if data.unidad not in UNIDADES_PERMITIDAS:
        raise HTTPException(status_code=400, detail="Unidad inválida")
    articulo = db.query(Articulo).filter(Articulo.id == articulo_id).first()
    if not articulo:
        raise HTTPException(status_code=404, detail="Artículo no encontrado")
    categoria = (
        db.query(CategoriaArticulo).filter(CategoriaArticulo.id == data.categoria_id).first()
    )
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
        # Respetar el total de línea si el cliente lo envía (permite ajustes
        # manuales "por si hay algún cambio"); si no, calcularlo.
        if getattr(detalle, "subtotal_linea", None) is not None:
            subtotal_linea = _normalize_decimal(detalle.subtotal_linea)
        else:
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


@router.get("/empleados", response_model=List[UsuarioResponse])
def list_empleados_nomina(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("administrador", "compras", "cajero")),
):
    """Empleados activos de la sucursal del usuario, para armar la nómina."""
    return (
        db.query(Usuario)
        .filter(
            Usuario.sucursal_id == current_user.sucursal_id,
            Usuario.activo == True,  # noqa: E712
        )
        .order_by(Usuario.nombre)
        .all()
    )


@router.post("/", response_model=GastoResponse, status_code=status.HTTP_201_CREATED)
def create_gasto(
    data: GastoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("administrador", "compras", "cajero")),
):
    _validate_gasto_inputs(data)

    detalles: list[GastoDetalle] = []
    nomina_detalles: list[NominaDetalle] = []
    proveedor_id = None

    if data.tipo_gasto == "nomina":
        nomina_detalles, subtotal = _build_nomina_detalles(
            data.nomina_detalles, db, current_user.sucursal_id
        )
        total = subtotal
    else:
        proveedor = db.query(Proveedor).filter(Proveedor.id == data.proveedor_id).first()
        if not proveedor:
            raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        if proveedor.sucursal_id != current_user.sucursal_id:
            raise HTTPException(status_code=403, detail="Proveedor no pertenece a tu sucursal")
        proveedor_id = proveedor.id
        detalles, subtotal = _build_gasto_detalles(data.detalles, db)
        total = _normalize_decimal(data.total_manual) if data.total_manual is not None else subtotal

    # Determinar fecha de gasto: si viene en el payload usarla, si no usar hora actual
    fecha_gasto = data.fecha_gasto if data.fecha_gasto else get_local_datetime()

    gasto = Gasto(
        proveedor_id=proveedor_id,
        tipo_gasto=data.tipo_gasto,
        metodo_pago=data.metodo_pago,
        descripcion=data.descripcion,
        folio=data.folio,
        subtotal=subtotal,
        total=total,
        total_manual=_normalize_decimal(data.total_manual)
        if data.total_manual is not None
        else None,
        fecha_gasto=fecha_gasto,
        notas=data.notas,
        sucursal_id=current_user.sucursal_id,
        turno_id=data.turno_id if data.tipo_gasto != "nomina" else None,
        detalles=detalles,
        nomina_detalles=nomina_detalles,
    )
    db.add(gasto)
    db.commit()
    db.refresh(gasto)
    return gasto


@router.get("/", response_model=PaginatedGastosResponse)
def list_gastos(
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    proveedor_id: Optional[int] = None,
    tipo_gasto: Optional[str] = None,
    metodo_pago: Optional[str] = None,
    categoria_id: Optional[int] = None,
    sucursal_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    fecha_inicio_date = _parse_date(fecha_inicio, "fecha_inicio")
    fecha_fin_date = _parse_date(fecha_fin, "fecha_fin")

    query = db.query(Gasto)

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
        start_dt = datetime.combine(fecha_inicio_date, datetime.min.time(), tzinfo=MEXICO_TZ)
        query = query.filter(Gasto.fecha_gasto >= start_dt)
    if fecha_fin_date is not None:
        end_dt = datetime.combine(
            fecha_fin_date + timedelta(days=1), datetime.min.time(), tzinfo=MEXICO_TZ
        )
        query = query.filter(Gasto.fecha_gasto < end_dt)

    # Filtro complejo por categoría (requiere join)
    if categoria_id is not None:
        query = (
            query.join(Gasto.detalles)
            .join(GastoDetalle.articulo)
            .filter(Articulo.categoria_id == categoria_id)
            .distinct()
        )

    # Contar total antes de paginar
    total = query.count()

    # Aplicar orden y paginación
    query = (
        query.options(
            joinedload(Gasto.proveedor),
            joinedload(Gasto.detalles)
            .joinedload(GastoDetalle.articulo)
            .joinedload(Articulo.categoria),
            selectinload(Gasto.nomina_detalles).joinedload(NominaDetalle.usuario),
        )
        .order_by(Gasto.fecha_gasto.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    items = query.all()

    return PaginatedGastosResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/analiticas/resumen", response_model=GastosResumenResponse)
def get_gastos_analiticas(
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    sucursal_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    fecha_inicio_date = _parse_date(fecha_inicio, "fecha_inicio")
    fecha_fin_date = _parse_date(fecha_fin, "fecha_fin")

    base_query = db.query(Gasto)

    if current_user.rol == "compras":
        base_query = base_query.filter(Gasto.sucursal_id == current_user.sucursal_id)
    elif sucursal_id is not None:
        base_query = base_query.filter(Gasto.sucursal_id == sucursal_id)

    if fecha_inicio_date:
        start_dt = datetime.combine(fecha_inicio_date, datetime.min.time(), tzinfo=MEXICO_TZ)
        base_query = base_query.filter(Gasto.fecha_gasto >= start_dt)
    if fecha_fin_date:
        end_dt = datetime.combine(
            fecha_fin_date + timedelta(days=1), datetime.min.time(), tzinfo=MEXICO_TZ
        )
        base_query = base_query.filter(Gasto.fecha_gasto < end_dt)

    # 1. Total Gastado

    total_gastado = base_query.with_entities(func.sum(Gasto.total)).scalar() or 0

    # 2. Promedio Diario
    if fecha_inicio_date and fecha_fin_date:
        dias = (fecha_fin_date - fecha_inicio_date).days + 1
        promedio_diario = float(total_gastado) / dias if dias > 0 else 0
    else:
        # Si no hay rango, calculamos sobre el rango de datos existente
        min_date = base_query.with_entities(func.min(Gasto.fecha_gasto)).scalar()
        max_date = base_query.with_entities(func.max(Gasto.fecha_gasto)).scalar()
        if min_date and max_date:
            dias = (max_date - min_date).days + 1
            promedio_diario = float(total_gastado) / dias if dias > 0 else 0
        else:
            promedio_diario = 0

    # 3. Por Categoría (más complejo porque 'nomina' no tiene articulos/categorias)
    # Estrategia: Consultar GastoDetalle -> Articulo -> Categoria para gastos normales
    # Y sumar gastos tipo 'nomina' o sin detalles como 'Otros'

    # A. Gastos con detalle
    gastos_con_detalle = (
        db.query(
            CategoriaArticulo.nombre.label("categoria"),
            func.sum(GastoDetalle.subtotal_linea).label("total"),
        )
        .join(Articulo, GastoDetalle.articulo_id == Articulo.id)
        .join(CategoriaArticulo, Articulo.categoria_id == CategoriaArticulo.id)
        .join(Gasto, GastoDetalle.gasto_id == Gasto.id)
    )

    # Aplicar mismos filtros a esta subquery
    if current_user.rol == "compras":
        gastos_con_detalle = gastos_con_detalle.filter(
            Gasto.sucursal_id == current_user.sucursal_id
        )
    elif sucursal_id:
        gastos_con_detalle = gastos_con_detalle.filter(Gasto.sucursal_id == sucursal_id)
    if fecha_inicio_date:
        gastos_con_detalle = gastos_con_detalle.filter(Gasto.fecha_gasto >= fecha_inicio_date)
    if fecha_fin_date:
        gastos_con_detalle = gastos_con_detalle.filter(Gasto.fecha_gasto <= fecha_fin_date)

    res_categorias = gastos_con_detalle.group_by(CategoriaArticulo.nombre).all()

    por_categoria = [
        GastoPorCategoria(categoria=r.categoria, total=float(r.total or 0)) for r in res_categorias
    ]

    # B. Agregar Nomina e Indirectos sin detalle
    # Nómina
    nomina_query = base_query.filter(Gasto.tipo_gasto == "nomina")
    total_nomina = nomina_query.with_entities(func.sum(Gasto.total)).scalar() or 0
    if total_nomina > 0:
        por_categoria.append(GastoPorCategoria(categoria="Nómina", total=float(total_nomina)))

    # 4. Top Proveedor
    top_prov = (
        base_query.with_entities(
            Proveedor.id, Proveedor.nombre, func.sum(Gasto.total).label("total")
        )
        .join(Proveedor, Gasto.proveedor_id == Proveedor.id)
        .group_by(Proveedor.id, Proveedor.nombre)
        .order_by(func.sum(Gasto.total).desc())
        .first()
    )

    top_proveedor_obj = None
    if top_prov:
        top_proveedor_obj = GastoTopProveedor(
            id=top_prov.id, nombre=top_prov.nombre, total=float(top_prov.total)
        )

    # 5. Timeline
    # Agrupar por fecha (día)
    timeline_res = (
        base_query.with_entities(
            func.date(Gasto.fecha_gasto).label("fecha"), func.sum(Gasto.total).label("total")
        )
        .group_by(func.date(Gasto.fecha_gasto))
        .order_by(func.date(Gasto.fecha_gasto))
        .all()
    )

    timeline = [GastoTimeline(fecha=str(r.fecha), total=float(r.total)) for r in timeline_res]

    return GastosResumenResponse(
        total_gastado=float(total_gastado),
        gasto_promedio_diario=promedio_diario,
        por_categoria=por_categoria,
        top_proveedor=top_proveedor_obj,
        timeline=timeline,
    )


@router.get("/analiticas/historial-precios/{articulo_id}", response_model=HistorialPreciosResponse)
def get_historial_precios(
    articulo_id: int,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    articulo = db.query(Articulo).filter(Articulo.id == articulo_id).first()
    if not articulo:
        raise HTTPException(status_code=404, detail="Artículo no encontrado")

    rows = (
        db.query(
            Gasto.fecha_gasto,
            GastoDetalle.precio_unitario,
            Proveedor.nombre.label("proveedor_nombre"),
            GastoDetalle.cantidad,
        )
        .select_from(GastoDetalle)
        .join(Gasto)
        .join(Proveedor)
        .filter(GastoDetalle.articulo_id == articulo_id)
        .order_by(Gasto.fecha_gasto.desc())
        .limit(limit)
        .all()
    )

    items = [
        HistorialPrecioItem(
            fecha=row.fecha_gasto,
            precio_unitario=float(row.precio_unitario),
            proveedor_nombre=row.proveedor_nombre,
            cantidad_comprada=float(row.cantidad),
        )
        for row in rows
    ]

    return HistorialPreciosResponse(
        articulo_id=articulo.id, articulo_nombre=articulo.nombre, historial=items
    )


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
            selectinload(Gasto.nomina_detalles).joinedload(NominaDetalle.usuario),
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
    current_user: Usuario = Depends(require_roles("administrador", "compras", "cajero")),
):
    _validate_gasto_inputs(data)

    gasto = db.query(Gasto).filter(Gasto.id == gasto_id).first()
    if not gasto:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")

    if current_user.rol == "compras" and gasto.sucursal_id != current_user.sucursal_id:
        raise HTTPException(status_code=403, detail="No autorizado para editar este gasto")

    detalles: list[GastoDetalle] = []
    nomina_detalles: list[NominaDetalle] = []
    proveedor_id = None

    if data.tipo_gasto == "nomina":
        nomina_detalles, subtotal = _build_nomina_detalles(
            data.nomina_detalles, db, current_user.sucursal_id
        )
        total = subtotal
    else:
        proveedor = db.query(Proveedor).filter(Proveedor.id == data.proveedor_id).first()
        if not proveedor:
            raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        if proveedor.sucursal_id != current_user.sucursal_id:
            raise HTTPException(status_code=403, detail="Proveedor no pertenece a tu sucursal")
        proveedor_id = proveedor.id
        detalles, subtotal = _build_gasto_detalles(data.detalles, db)
        total = _normalize_decimal(data.total_manual) if data.total_manual is not None else subtotal

    gasto.proveedor_id = proveedor_id
    gasto.tipo_gasto = data.tipo_gasto
    gasto.metodo_pago = data.metodo_pago
    gasto.descripcion = data.descripcion
    gasto.folio = data.folio
    gasto.subtotal = subtotal
    gasto.total = total
    gasto.total_manual = (
        _normalize_decimal(data.total_manual) if data.total_manual is not None else None
    )
    if data.fecha_gasto:
        gasto.fecha_gasto = data.fecha_gasto
    gasto.notas = data.notas
    gasto.turno_id = data.turno_id if data.tipo_gasto != "nomina" else None

    gasto.detalles.clear()
    for detalle in detalles:
        gasto.detalles.append(detalle)

    gasto.nomina_detalles.clear()
    for nd in nomina_detalles:
        gasto.nomina_detalles.append(nd)

    db.commit()
    db.refresh(gasto)
    return gasto


@router.delete("/{gasto_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_gasto(
    gasto_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("administrador", "compras", "cajero")),
):
    gasto = db.query(Gasto).filter(Gasto.id == gasto_id).first()
    if not gasto:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")

    if current_user.rol == "compras" and gasto.sucursal_id != current_user.sucursal_id:
        raise HTTPException(status_code=403, detail="No autorizado para eliminar este gasto")

    db.delete(gasto)
    db.commit()
    return None
