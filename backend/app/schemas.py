from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

# ===== SCHEMAS PARA USUARIOS =====
class UsuarioBase(BaseModel):
    nombre: str
    rol: str
    activo: bool = True
    sucursal_id: int

class UsuarioCreate(UsuarioBase):
    password: str

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
    estado: str = 'disponible'

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

class ArticuloPedidoCreate(BaseModel):
    platillo_id: int
    cantidad: int
    modificaciones: Optional[str] = None

class ArticuloPedidoResponse(ArticuloPedidoBase):
    id: int
    platillo: PlatilloResponse
    
    class Config:
        from_attributes = True

class PedidoBase(BaseModel):
    numero_display: str
    nombre_cliente: Optional[str] = None
    total: Decimal
    estado: str = 'pendiente'
    metodo_pago: Optional[str] = None
    sucursal_id: int
    usuario_id: int

class PedidoCreate(BaseModel):
    nombre_cliente: str
    metodo_pago: str
    articulos: List[ArticuloPedidoCreate]

class PedidoUpdate(BaseModel):
    estado: str

class PedidoResponse(PedidoBase):
    id: int
    fecha_creacion: datetime
    articulos_pedido: List[ArticuloPedidoResponse]
    
    class Config:
        from_attributes = True

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
