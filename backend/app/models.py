from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, UniqueConstraint, func
from sqlalchemy.types import DECIMAL
from sqlalchemy.orm import relationship
from datetime import datetime
import pytz
from app.db.session import Base
from app.core.config import settings

def get_local_datetime():
    """Obtener datetime en zona horaria local del restaurante"""
    tz = pytz.timezone(settings.TIMEZONE)
    return datetime.now(tz).replace(tzinfo=None)

class Sucursal(Base):
    __tablename__ = "sucursales"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    direccion = Column(Text)
    
    # Relaciones
    usuarios = relationship("Usuario", back_populates="sucursal")
    pedidos = relationship("Pedido", back_populates="sucursal")
    gastos = relationship("Gasto", back_populates="sucursal")

class Usuario(Base):
    __tablename__ = "usuarios"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    rol = Column(String(20), nullable=False)  # 'cajero', 'cocina', 'administrador', 'compras', 'mesero'
    password = Column(String(255), nullable=False)  # Cambiado de 'pin' a 'password'
    activo = Column(Boolean, default=True)
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"))
    
    # Relaciones
    sucursal = relationship("Sucursal", back_populates="usuarios")
    pedidos = relationship("Pedido", back_populates="usuario")

class Platillo(Base):
    __tablename__ = "platillos"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text)
    precio = Column(DECIMAL(8, 2), nullable=False)
    categoria = Column(String(50), nullable=False)
    kds_name = Column(String(50), nullable=True)  # Nombre corto para KDS
    estado = Column(String(20), default='disponible')  # 'disponible', 'no_disponible'
    
    # Relaciones
    articulos_pedido = relationship("ArticuloPedido", back_populates="platillo")

class Pedido(Base):
    __tablename__ = "pedidos"
    __table_args__ = (
        UniqueConstraint('numero_display', 'sucursal_id', 'fecha_creacion', name='uq_numero_display_sucursal_fecha'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    numero_display = Column(String(10), nullable=False)  # Ej: "001", "002" (único por día y sucursal)
    nombre_cliente = Column(String(100))
    mesa = Column(String(10), nullable=True)  # Número de mesa para tipo_orden 'aqui' (11,12,13,14,15,21,22,23,24,25,31,32,33,34,35)
    total = Column(DECIMAL(8, 2), nullable=False)
    estado = Column(String(20), default='pendiente')  # 'pendiente', 'preparando', 'listo', 'entregado', 'cuenta_solicitada', 'pagado'
    metodo_pago = Column(String(20))  # 'efectivo', 'tarjeta', 'transferencia'
    tipo_orden = Column(String(20), default='aqui')  # 'aqui', 'llevar', 'uber_eats'
    fecha_creacion = Column(DateTime, default=get_local_datetime)
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"))
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    
    # Relaciones
    sucursal = relationship("Sucursal", back_populates="pedidos")
    usuario = relationship("Usuario", back_populates="pedidos")
    articulos_pedido = relationship("ArticuloPedido", back_populates="pedido")

class ArticuloPedido(Base):
    __tablename__ = "articulos_pedido"
    
    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), nullable=False)
    platillo_id = Column(Integer, ForeignKey("platillos.id"), nullable=False)
    cantidad = Column(Integer, nullable=False)
    precio_cobrado = Column(DECIMAL(8, 2), nullable=False)
    modificaciones = Column(Text)
    estado_item = Column(String(20), default='pendiente')  # 'pendiente', 'preparando', 'listo', 'entregado'
    
    # Relaciones
    pedido = relationship("Pedido", back_populates="articulos_pedido")
    platillo = relationship("Platillo", back_populates="articulos_pedido")

class Gasto(Base):
    __tablename__ = "gastos"
    
    id = Column(Integer, primary_key=True, index=True)
    descripcion = Column(String(255), nullable=False)
    monto = Column(DECIMAL(8, 2), nullable=False)
    categoria = Column(String(50), nullable=False)
    fecha_gasto = Column(DateTime, default=get_local_datetime)
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"))
    
    # Relaciones
    sucursal = relationship("Sucursal", back_populates="gastos")
