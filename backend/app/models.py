from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.types import DECIMAL
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base

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
    rol = Column(String(20), nullable=False)  # 'cajero', 'cocina', 'administrador', 'compras'
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
    estado = Column(String(20), default='disponible')  # 'disponible', 'no_disponible'
    
    # Relaciones
    articulos_pedido = relationship("ArticuloPedido", back_populates="platillo")

class Pedido(Base):
    __tablename__ = "pedidos"
    
    id = Column(Integer, primary_key=True, index=True)
    numero_display = Column(String(10), nullable=False, unique=True)  # Ej: "101", "102"
    nombre_cliente = Column(String(100))
    total = Column(DECIMAL(8, 2), nullable=False)
    estado = Column(String(20), default='pendiente')  # 'pendiente', 'preparando', 'listo', 'completado'
    metodo_pago = Column(String(20))  # 'efectivo', 'tarjeta', 'transferencia'
    tipo_orden = Column(String(20), default='aqui')  # 'aqui', 'llevar', 'uber_eats'
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
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
    
    # Relaciones
    pedido = relationship("Pedido", back_populates="articulos_pedido")
    platillo = relationship("Platillo", back_populates="articulos_pedido")

class Gasto(Base):
    __tablename__ = "gastos"
    
    id = Column(Integer, primary_key=True, index=True)
    descripcion = Column(String(255), nullable=False)
    monto = Column(DECIMAL(8, 2), nullable=False)
    categoria = Column(String(50), nullable=False)
    fecha_gasto = Column(DateTime, default=datetime.utcnow)
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"))
    
    # Relaciones
    sucursal = relationship("Sucursal", back_populates="gastos")
