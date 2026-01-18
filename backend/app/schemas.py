from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, EmailStr


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


# ===== SCHEMAS PARA SUCURSALES =====
class SucursalBase(BaseModel):
    nombre: str
    direccion: Optional[str] = None


class SucursalCreate(SucursalBase):
    pass


class SucursalResponse(SucursalBase):
    id: int

    class Config:
        from_attributes = True


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
class GastoBase(BaseModel):
    descripcion: str
    monto: Decimal
    categoria: str
    sucursal_id: int


class GastoCreate(GastoBase):
    pass


class GastoResponse(GastoBase):
    id: int
    fecha_gasto: datetime

    class Config:
        from_attributes = True


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
    observaciones: Optional[str] = None


class TurnoUpdate(BaseModel):
    conteo_inicial: Optional[ConteoRequest] = None
    conteo_final: Optional[ConteoRequest] = None
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
    diferencia: Optional[float] = None
    observaciones: Optional[str] = None
    denominaciones_iniciales: List[DenominacionBase]
    denominaciones_finales: Optional[List[DenominacionBase]] = None
    usuario_nombre: Optional[str] = None
    sucursal_nombre: Optional[str] = None

    class Config:
        from_attributes = True
