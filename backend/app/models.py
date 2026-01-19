from datetime import datetime

import pytz
from app.core.config import settings
from app.db.session import Base
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    Enum,
    Numeric,
)
from sqlalchemy.orm import relationship
from sqlalchemy.types import DECIMAL


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
    proveedores = relationship("Proveedor", back_populates="sucursal")


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    rol = Column(
        String(20), nullable=False
    )  # 'cajero', 'cocina', 'administrador', 'compras', 'mesero'
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
    estado = Column(String(20), default="disponible")  # 'disponible', 'no_disponible'

    # Relaciones
    articulos_pedido = relationship("ArticuloPedido", back_populates="platillo")


class Pedido(Base):
    __tablename__ = "pedidos"
    __table_args__ = (
        UniqueConstraint(
            "numero_display",
            "sucursal_id",
            "fecha_creacion",
            name="uq_numero_display_sucursal_fecha",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    numero_display = Column(
        String(10), nullable=False
    )  # Ej: "001", "002" (único por día y sucursal)
    nombre_cliente = Column(String(100))
    mesa = Column(
        String(10), nullable=True
    )  # Número de mesa para tipo_orden 'aqui' (11,12,13,14,15,21,22,23,24,25,31,32,33,34,35)
    total = Column(DECIMAL(8, 2), nullable=False)
    estado = Column(
        String(20), default="pendiente"
    )  # 'pendiente', 'preparando', 'listo', 'entregado', 'cuenta_solicitada', 'pagado'
    metodo_pago = Column(String(20))  # 'efectivo', 'tarjeta', 'transferencia'
    propina_efectivo = Column(DECIMAL(8, 2), default=0)
    propina_tarjeta = Column(DECIMAL(8, 2), default=0)
    tipo_orden = Column(String(20), default="aqui")  # 'aqui', 'llevar', 'uber_eats'
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
    estado_item = Column(
        String(20), default="pendiente"
    )  # 'pendiente', 'preparando', 'listo', 'entregado'

    # Relaciones
    pedido = relationship("Pedido", back_populates="articulos_pedido")
    platillo = relationship("Platillo", back_populates="articulos_pedido")


class Proveedor(Base):
    __tablename__ = "proveedores"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), nullable=False)
    telefono = Column(String(50))
    direccion = Column(Text)
    notas = Column(Text)
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"))

    # Relaciones
    sucursal = relationship("Sucursal", back_populates="proveedores")
    gastos = relationship("Gasto", back_populates="proveedor")


class CategoriaArticulo(Base):
    __tablename__ = "categorias_articulo"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(80), nullable=False, unique=True)

    # Relaciones
    articulos = relationship("Articulo", back_populates="categoria")


class Articulo(Base):
    __tablename__ = "articulos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), nullable=False)
    unidad = Column(String(20), nullable=False)
    costo_estandar = Column(DECIMAL(10, 2), nullable=False)
    categoria_id = Column(Integer, ForeignKey("categorias_articulo.id"), nullable=False)

    # Relaciones
    categoria = relationship("CategoriaArticulo", back_populates="articulos")
    detalles_gasto = relationship("GastoDetalle", back_populates="articulo")


class Gasto(Base):
    __tablename__ = "gastos"

    id = Column(Integer, primary_key=True, index=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=False)
    tipo_gasto = Column(
        Enum("directo", "indirecto", "nomina", name="tipo_gasto_enum"),
        nullable=False,
    )
    metodo_pago = Column(
        Enum("efectivo", "tarjeta", name="metodo_pago_gasto_enum"),
        nullable=False,
    )
    descripcion = Column(String(255))
    folio = Column(String(100))
    subtotal = Column(DECIMAL(10, 2), nullable=False)
    total = Column(DECIMAL(10, 2), nullable=False)
    total_manual = Column(DECIMAL(10, 2))
    fecha_gasto = Column(DateTime, default=get_local_datetime)
    notas = Column(Text)
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"))

    # Relaciones
    sucursal = relationship("Sucursal", back_populates="gastos")
    proveedor = relationship("Proveedor", back_populates="gastos")
    detalles = relationship(
        "GastoDetalle", back_populates="gasto", cascade="all, delete-orphan"
    )


class GastoDetalle(Base):
    __tablename__ = "gasto_detalles"

    id = Column(Integer, primary_key=True, index=True)
    gasto_id = Column(Integer, ForeignKey("gastos.id", ondelete="CASCADE"))
    articulo_id = Column(Integer, ForeignKey("articulos.id"), nullable=False)
    cantidad = Column(Numeric(10, 2), nullable=False)
    precio_unitario = Column(DECIMAL(10, 2), nullable=False)
    subtotal_linea = Column(DECIMAL(10, 2), nullable=False)

    # Relaciones
    gasto = relationship("Gasto", back_populates="detalles")
    articulo = relationship("Articulo", back_populates="detalles_gasto")


class Turno(Base):
    __tablename__ = "turnos"

    id = Column(Integer, primary_key=True, index=True)
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    fecha_apertura = Column(DateTime, default=get_local_datetime)
    fecha_cierre = Column(DateTime)
    estado = Column(
        String(10), default="abierto", nullable=False
    )  # 'abierto', 'cerrado'
    total_inicial = Column(DECIMAL(10, 2), nullable=False)
    total_final = Column(DECIMAL(10, 2))
    ventas_efectivo = Column(DECIMAL(10, 2))
    propinas_efectivo = Column(DECIMAL(10, 2))
    diferencia = Column(DECIMAL(10, 2))
    observaciones = Column(Text)

    # Relaciones
    sucursal = relationship("Sucursal")
    usuario = relationship("Usuario")
    denominaciones = relationship(
        "TurnoDenominacion", back_populates="turno", cascade="all, delete-orphan"
    )

    # Índices y constraints
    __table_args__ = (
        Index(
            "idx_turno_activo_sucursal",
            sucursal_id,
            unique=True,
            postgresql_where=estado == "abierto",
        ),
        CheckConstraint("estado IN ('abierto', 'cerrado')", name="chk_turno_estado"),
    )


class TurnoDenominacion(Base):
    __tablename__ = "turno_denominaciones"

    id = Column(Integer, primary_key=True, index=True)
    turno_id = Column(
        Integer, ForeignKey("turnos.id", ondelete="CASCADE"), nullable=False
    )
    tipo = Column(String(10), nullable=False)  # 'inicial', 'final'
    denominacion = Column(
        Integer, nullable=False
    )  # 1000, 500, 200, 100, 50, 20, 10, 5, 2, 1
    cantidad = Column(Integer, nullable=False, default=0)
    subtotal = Column(DECIMAL(10, 2), nullable=False)

    # Relaciones
    turno = relationship("Turno", back_populates="denominaciones")

    # Índices y constraints
    __table_args__ = (
        UniqueConstraint(
            "turno_id", "tipo", "denominacion", name="uq_turno_tipo_denominacion"
        ),
        CheckConstraint(
            "tipo IN ('inicial', 'final')", name="chk_turno_denominacion_tipo"
        ),
        CheckConstraint(
            "denominacion IN (1000, 500, 200, 100, 50, 20, 10, 5, 2, 1)",
            name="chk_turno_denominacion_valor",
        ),
        CheckConstraint("cantidad >= 0", name="chk_turno_denominacion_cantidad"),
        CheckConstraint("subtotal >= 0", name="chk_turno_denominacion_subtotal"),
    )
