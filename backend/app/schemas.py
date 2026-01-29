from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


# ===== SCHEMAS PARA USUARIOS =====
class UsuarioBase(BaseModel):
    nombre: str
    rol: str
    activo: bool = True
    sucursal_id: int


class UsuarioCreate(UsuarioBase):
    password: str


class UsuarioUpdate(UsuarioBase):
    password: Optional[str] = None  # Password opcional para updates


class UsuarioResponse(UsuarioBase):
    id: int

    class Config:
        from_attributes = True


class UsuarioLogin(BaseModel):
    user_id: str  # ID del usuario (ej: "1", "2", "3")
    password: str


# ===== SCHEMAS PARA ANALÍTICAS DE GASTOS =====
class GastoTimeline(BaseModel):
    fecha: str
    total: float

class GastoPorCategoria(BaseModel):
    categoria: str
    total: float

class GastoTopProveedor(BaseModel):
    id: int
    nombre: str
    total: float

class GastosResumenResponse(BaseModel):
    total_gastado: float
    gasto_promedio_diario: float
    por_categoria: List[GastoPorCategoria]
    top_proveedor: Optional[GastoTopProveedor] = None
    timeline: List[GastoTimeline]

class HistorialPrecioItem(BaseModel):
    fecha: datetime
    precio_unitario: float
    proveedor_nombre: str
    cantidad_comprada: float

class HistorialPreciosResponse(BaseModel):
    articulo_id: int
    articulo_nombre: str
    historial: List[HistorialPrecioItem]



# ===== SCHEMAS PARA PLATILLOS =====
class PlatilloBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    precio: Decimal
    categoria: str
    kds_name: Optional[str] = None
    estado: str = "disponible"


class PlatilloCreate(PlatilloBase):
    pass


class PlatilloResponse(PlatilloBase):
    id: int

    class Config:
        from_attributes = True


# ===== SCHEMAS PARA PEDIDOS =====
class ArticuloPedidoBase(BaseModel):
    platillo_id: int
    cantidad: int
    precio_cobrado: Decimal
    modificaciones: Optional[str] = None
    estado_item: str = "pendiente"


class ArticuloPedidoCreate(BaseModel):
    platillo_id: int
    cantidad: int
    modificaciones: Optional[str] = None


class ArticuloPedidoUpdate(BaseModel):
    estado_item: str


class ArticuloPedidoResponse(ArticuloPedidoBase):
    id: int
    platillo: PlatilloResponse

    class Config:
        from_attributes = True


class PedidoBase(BaseModel):
    numero_display: str
    nombre_cliente: Optional[str] = None
    mesa: Optional[str] = None
    total: Decimal
    estado: str = "pendiente"
    metodo_pago: Optional[str] = None
    propina_efectivo: Decimal = Decimal("0")
    propina_tarjeta: Decimal = Decimal("0")
    tipo_orden: str = "aqui"
    sucursal_id: int
    usuario_id: int


class PedidoCreate(BaseModel):
    nombre_cliente: Optional[str] = None
    mesa: Optional[str] = None
    metodo_pago: Optional[str] = None  # Opcional para flujo mesero
    tipo_orden: str = "aqui"
    articulos: List[ArticuloPedidoCreate]


class PedidoUpdate(BaseModel):
    estado: str
    metodo_pago: Optional[str] = None
    propina_efectivo: Optional[Decimal] = None
    propina_tarjeta: Optional[Decimal] = None


class AgregarArticulosRequest(BaseModel):
    articulos: List[ArticuloPedidoCreate]
    mesero_id: Optional[int] = None


class PedidoResponse(PedidoBase):
    id: int
    fecha_creacion: datetime
    fecha_pago: Optional[datetime] = None
    usuario_nombre: Optional[str] = None
    articulos_pedido: List[ArticuloPedidoResponse]

    class Config:
        from_attributes = True


class DividirCuentaItem(BaseModel):
    articulo_id: int
    cantidad: int


class DividirCuentaCuenta(BaseModel):
    items: List[DividirCuentaItem]


class DividirCuentaRequest(BaseModel):
    cuentas: List[DividirCuentaCuenta]


class DividirCuentaResponse(BaseModel):
    pedido_original_id: int
    cuentas: List[PedidoResponse]



# ===== SCHEMAS PARA GASTOS =====
class ProveedorBase(BaseModel):
    nombre: str
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    notas: Optional[str] = None
    sucursal_id: Optional[int] = None


class ProveedorCreate(ProveedorBase):
    pass


class ProveedorResponse(ProveedorBase):
    id: int

    class Config:
        from_attributes = True


class CategoriaArticuloBase(BaseModel):
    nombre: str


class CategoriaArticuloCreate(CategoriaArticuloBase):
    pass


class CategoriaArticuloResponse(CategoriaArticuloBase):
    id: int

    class Config:
        from_attributes = True


class ArticuloBase(BaseModel):
    nombre: str
    unidad: str
    costo_estandar: Decimal = Field(..., ge=0)
    categoria_id: int


class ArticuloCreate(ArticuloBase):
    pass


class ArticuloResponse(ArticuloBase):
    id: int
    categoria: CategoriaArticuloResponse

    class Config:
        from_attributes = True


class GastoDetalleBase(BaseModel):
    articulo_id: int
    cantidad: Decimal = Field(..., ge=0)
    precio_unitario: Decimal = Field(..., ge=0)
    subtotal_linea: Optional[Decimal] = None


class GastoDetalleCreate(GastoDetalleBase):
    pass


class GastoDetalleResponse(GastoDetalleBase):
    id: int
    articulo: ArticuloResponse

    class Config:
        from_attributes = True


class GastoBase(BaseModel):
    proveedor_id: int
    tipo_gasto: str
    metodo_pago: str
    descripcion: Optional[str] = None
    folio: Optional[str] = None
    total_manual: Optional[Decimal] = Field(None, ge=0)
    notas: Optional[str] = None
    turno_id: Optional[int] = None


class GastoCreate(GastoBase):
    detalles: List[GastoDetalleCreate] = []
    fecha_gasto: Optional[datetime] = None


class GastoResponse(GastoBase):
    id: int
    subtotal: Decimal
    total: Decimal
    fecha_gasto: datetime
    proveedor: ProveedorResponse
    detalles: List[GastoDetalleResponse]

    class Config:
        from_attributes = True


class PaginatedGastosResponse(BaseModel):
    items: List[GastoResponse]
    total: int
    page: int
    page_size: int


# ===== SCHEMAS PARA AUTENTICACIÓN =====
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    usuario_id: Optional[int] = None


# ===== SCHEMAS PARA TURNOS =====
class DenominacionBase(BaseModel):
    denominacion: int  # 1000, 500, 200, 100, 50, 20, 10, 5, 2, 1
    cantidad: int
    subtotal: Optional[float] = None


class ConteoRequest(BaseModel):
    denominaciones: List[DenominacionBase]


class TurnoBase(BaseModel):
    sucursal_id: int
    usuario_id: int
    total_inicial: Decimal
    observaciones: Optional[str] = None
    estado: str = "abierto"


class TurnoCreate(BaseModel):
    conteo_inicial: ConteoRequest
    observaciones: Optional[str] = None


class TurnoCierreRequest(BaseModel):
    conteo_final: ConteoRequest
    monto_retirado: Optional[Decimal] = None
    monto_restante_en_caja: Optional[Decimal] = None
    observaciones: Optional[str] = None


class TurnoUpdate(BaseModel):
    conteo_inicial: Optional[ConteoRequest] = None
    conteo_final: Optional[ConteoRequest] = None
    monto_retirado: Optional[Decimal] = None
    monto_restante_en_caja: Optional[Decimal] = None
    observaciones: Optional[str] = None


class TurnoResponse(BaseModel):
    id: int
    sucursal_id: int
    usuario_id: int
    fecha_apertura: datetime
    fecha_cierre: Optional[datetime] = None
    estado: str
    total_inicial: float
    total_final: Optional[float] = None
    ventas_efectivo: Optional[float] = None
    propinas_efectivo: Optional[float] = None
    monto_retirado: Optional[float] = None
    monto_restante_en_caja: Optional[float] = None
    fondo_anterior: Optional[float] = None
    diferencia: Optional[float] = None
    observaciones: Optional[str] = None
    denominaciones_iniciales: List[DenominacionBase]
    denominaciones_finales: Optional[List[DenominacionBase]] = None
    usuario_nombre: Optional[str] = None
    sucursal_nombre: Optional[str] = None

    class Config:
        from_attributes = True
