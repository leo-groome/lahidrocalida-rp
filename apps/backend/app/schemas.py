from datetime import date, datetime, time
from decimal import Decimal
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


# ===== SCHEMAS PARA USUARIOS =====
class UsuarioBase(BaseModel):
    nombre: str
    rol: str
    activo: bool = True
    sucursal_id: int


class UsuarioCreate(UsuarioBase):
    pin: str


class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = None
    rol: Optional[str] = None
    activo: Optional[bool] = None
    sucursal_id: Optional[int] = None
    pin: Optional[str] = None  # PIN opcional para updates


class UsuarioResponse(UsuarioBase):
    id: int

    class Config:
        from_attributes = True


class UsuarioLogin(BaseModel):
    user_id: str  # ID del usuario (ej: "1", "2", "3")
    pin: str


class AdminLogin(BaseModel):
    email: str
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


class GastoPorProveedor(BaseModel):
    id: int
    nombre: str
    total: float
    compras: int


class GastoPorArticulo(BaseModel):
    id: int
    nombre: str
    unidad: str
    categoria: Optional[str] = None
    cantidad: float
    total: float


class GastoPorConcepto(BaseModel):
    id: int
    nombre: str
    total: float
    pagos: int


class GastosResumenResponse(BaseModel):
    total_gastado: float
    gasto_promedio_diario: float
    por_categoria: List[GastoPorCategoria]
    top_proveedor: Optional[GastoTopProveedor] = None
    por_proveedor: List[GastoPorProveedor] = []
    por_articulo: List[GastoPorArticulo] = []
    por_concepto: List[GastoPorConcepto] = []
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
    client_request_id: Optional[str] = None

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
    turno_id: Optional[int] = None


class PedidoCreate(BaseModel):
    nombre_cliente: Optional[str] = None
    mesa: Optional[str] = None
    tipo_orden: str = "aqui"
    metodo_pago: Optional[str] = None
    articulos: List[ArticuloPedidoCreate]
    client_request_id: Optional[str] = Field(default=None, max_length=36)


class PedidoUpdate(BaseModel):
    estado: str
    metodo_pago: Optional[str] = None
    propina_efectivo: Optional[Decimal] = None
    propina_tarjeta: Optional[Decimal] = None
    pin_autorizacion: Optional[str] = None
    # Override manual de estatus desde Caja (cualquier rol): exige PIN de admin.
    cambio_manual: bool = False


class PinVerifyRequest(BaseModel):
    pin: str


class AgregarArticulosRequest(BaseModel):
    articulos: List[ArticuloPedidoCreate]
    mesero_id: Optional[int] = None
    client_request_id: Optional[str] = None


class PedidoResponse(PedidoBase):
    id: int
    fecha_creacion: datetime
    fecha_pago: Optional[datetime] = None
    usuario_nombre: Optional[str] = None
    articulos_pedido: List[ArticuloPedidoResponse]
    parent_pedido_id: Optional[int] = None
    client_request_id: Optional[str] = None

    class Config:
        from_attributes = True


class DividirCuentaItem(BaseModel):
    articulo_id: int
    cantidad: int


class DividirCuentaCuenta(BaseModel):
    items: List[DividirCuentaItem]


class DividirCuentaRequest(BaseModel):
    cuentas: List[DividirCuentaCuenta]
    client_request_id: Optional[str] = Field(default=None, max_length=36)
    pin_autorizacion: Optional[str] = None


class DividirCuentaResponse(BaseModel):
    pedido_original_id: int
    cuentas: List[PedidoResponse]


class DividirPorMontoCuenta(BaseModel):
    monto: Decimal


class DividirPorMontoRequest(BaseModel):
    cuentas: List[DividirPorMontoCuenta]
    client_request_id: Optional[str] = Field(default=None, max_length=36)
    pin_autorizacion: Optional[str] = None


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


class NominaEmpleado(BaseModel):
    id: int
    nombre: str
    rol: str

    class Config:
        from_attributes = True


class NominaDetalleBase(BaseModel):
    usuario_id: int
    monto: Decimal = Field(..., ge=0)
    notas: Optional[str] = None


class NominaDetalleCreate(NominaDetalleBase):
    pass


class NominaDetalleResponse(NominaDetalleBase):
    id: int
    usuario: NominaEmpleado

    class Config:
        from_attributes = True


FRECUENCIAS_CONCEPTO = Literal[
    "semanal", "mensual", "bimestral", "anual", "cada_n_dias", "eventual"
]


class ConceptoGastoCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    monto_tipico: Optional[Decimal] = Field(None, gt=0, max_digits=10, decimal_places=2)
    frecuencia: FRECUENCIAS_CONCEPTO = "mensual"
    dia_vencimiento: Optional[int] = Field(None, ge=1, le=31)
    intervalo_dias: Optional[int] = Field(None, ge=1, le=365)
    activo: bool = True

    @model_validator(mode="after")
    def _validar_intervalo(self):
        if self.frecuencia == "cada_n_dias" and self.intervalo_dias is None:
            raise ValueError("Indica cada cuántos días se paga")
        if self.frecuencia != "cada_n_dias":
            self.intervalo_dias = None
        return self


class ConceptoGastoResponse(ConceptoGastoCreate):
    id: int

    class Config:
        from_attributes = True


class ConceptoPendiente(BaseModel):
    concepto: ConceptoGastoResponse
    ultimo_gasto: Optional[datetime] = None
    estado: Literal["al_corriente", "pendiente", "vencido"]


class GastoBase(BaseModel):
    # Opcional: la nómina no lleva proveedor.
    proveedor_id: Optional[int] = None
    tipo_gasto: str
    metodo_pago: str
    descripcion: Optional[str] = None
    folio: Optional[str] = None
    total_manual: Optional[Decimal] = Field(None, ge=0)
    notas: Optional[str] = None
    turno_id: Optional[int] = None
    # Solo para tipo indirecto: concepto del catálogo (luz, gas, renta...).
    concepto_id: Optional[int] = None


class GastoCreate(GastoBase):
    client_request_id: Optional[UUID] = None
    detalles: List[GastoDetalleCreate] = []
    nomina_detalles: List[NominaDetalleCreate] = []
    fecha_gasto: Optional[datetime] = None


class AdjuntoResponse(BaseModel):
    id: int
    content_type: str
    size: int
    created_at: datetime

    class Config:
        from_attributes = True


class GastoResponse(GastoBase):
    id: int
    num_adjuntos: int = 0
    adjuntos: List[AdjuntoResponse] = []
    subtotal: Decimal
    total: Decimal
    fecha_gasto: datetime
    proveedor: Optional[ProveedorResponse] = None
    concepto: Optional[ConceptoGastoResponse] = None
    detalles: List[GastoDetalleResponse]
    nomina_detalles: List[NominaDetalleResponse] = []

    class Config:
        from_attributes = True


class PaginatedGastosResponse(BaseModel):
    items: List[GastoResponse]
    total: int
    suma_total: float = 0.0
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
    fondo_anterior: Optional[float] = None
    pedidos_uber: int = 0
    ventas_uber: float = 0.0
    observaciones: Optional[str] = None
    denominaciones_iniciales: List[DenominacionBase]
    denominaciones_finales: Optional[List[DenominacionBase]] = None
    usuario_nombre: Optional[str] = None
    sucursal_nombre: Optional[str] = None
    cerrado_automatico: bool = False

    class Config:
        from_attributes = True


# ===== SCHEMAS PARA ASISTENCIA =====
class RegistroAsistenciaCreate(BaseModel):
    usuario_id: int
    notas: Optional[str] = None


class AsistenciaPinRequest(BaseModel):
    usuario_id: int
    pin: str
    notas: Optional[str] = None


class ConfirmarSalidaRequest(BaseModel):
    fecha_salida: datetime


class RegistroAsistenciaResponse(BaseModel):
    id: int
    usuario_id: int
    fecha_entrada: datetime
    fecha_salida: Optional[datetime] = None
    notas: Optional[str] = None
    usuario_nombre: Optional[str] = None
    horas_trabajadas: Optional[float] = None
    cierre_automatico: bool = False
    requiere_revision: bool = False
    fecha_salida_estimada: Optional[datetime] = None

    class Config:
        from_attributes = True


class AsistenciaResumenItem(BaseModel):
    usuario_id: int
    usuario_nombre: str
    rol: str
    total_registros: int
    horas_totales: float
    ultima_entrada: Optional[datetime] = None
    ultima_salida: Optional[datetime] = None


class AsistenciaResumenResponse(BaseModel):
    fecha_inicio: datetime
    fecha_fin: datetime
    empleados: List[AsistenciaResumenItem]


class AsistenciaAnomaliasResumen(BaseModel):
    """Resumen ligero para el aviso al cajero al abrir turno — sin detalle
    (nombres/horas) que solo debe ver un admin."""

    sucursal_id: int
    pendientes: int


# ===== SCHEMAS PARA PAGO Y HORARIOS DE EMPLEADOS =====
class EmpleadoPagoUpdate(BaseModel):
    tarifa_hora: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    tarifa_hora_extra: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    # Horas por día a partir de las cuales cada hora se paga como extra.
    horas_jornada: Decimal = Field(
        default=Decimal("8"), gt=0, le=16, max_digits=4, decimal_places=2
    )


class EmpleadoPagoResponse(EmpleadoPagoUpdate):
    class Config:
        from_attributes = True


class HorarioDia(BaseModel):
    dia_semana: int = Field(ge=0, le=6)
    hora_entrada: time
    hora_salida: time

    @model_validator(mode="after")
    def _validar_horas(self):
        if self.hora_entrada == self.hora_salida:
            raise ValueError("La entrada y la salida no pueden ser iguales")
        return self

    class Config:
        from_attributes = True


class HorarioUpdate(BaseModel):
    dias: List[HorarioDia] = Field(max_length=7)

    @model_validator(mode="after")
    def _sin_dias_repetidos(self):
        if len({d.dia_semana for d in self.dias}) != len(self.dias):
            raise ValueError("Día de la semana repetido")
        return self


class EmpleadoNominaResponse(BaseModel):
    usuario_id: int
    nombre: str
    rol: str
    pago: Optional[EmpleadoPagoResponse] = None
    horario: List[HorarioDia] = []


# ===== SCHEMAS PARA NÓMINA SEMANAL =====
class PeriodoNominaCreate(BaseModel):
    # Cualquier fecha de la semana: el servidor la normaliza al martes que inicia el periodo.
    fecha_inicio: date


class LineaNominaUpdate(BaseModel):
    horas_trabajadas: Optional[Decimal] = Field(None, ge=0, le=200, max_digits=6, decimal_places=2)
    horas_extra: Optional[Decimal] = Field(None, ge=0, le=60, max_digits=5, decimal_places=2)
    bonos: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    descuentos: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    metodo_pago: Optional[Literal["efectivo", "tarjeta"]] = None
    sale_de_caja: Optional[bool] = None
    notas: Optional[str] = Field(None, max_length=255)


class PagarNominaRequest(BaseModel):
    pin_autorizacion: str = Field(min_length=1, max_length=64)
    # Empleados a pagar; vacío = todos los que ya se pueden pagar.
    usuario_ids: Optional[List[int]] = Field(None, max_length=200)


class DiaNomina(BaseModel):
    """Una checada de la semana, para ver qué días y cuántas horas se están pagando."""

    fecha: date  # jornada operativa
    entrada: datetime
    salida: Optional[datetime] = None
    horas: Decimal
    automatica: bool = False
    abierta: bool = False
    # Solo en la entrada abierta de hoy: horas si trabaja hasta las 23:59 (no se paga así).
    horas_proyectadas: Optional[Decimal] = None


class LineaNominaResponse(BaseModel):
    usuario_id: int
    nombre: str
    dias_esperados: int
    dias_trabajados: int
    faltas: int
    horas_trabajadas: Decimal
    horas_extra: Decimal
    base: Decimal
    extra_monto: Decimal
    bonos: Decimal
    descuentos: Decimal
    total: Decimal
    metodo_pago: str
    sale_de_caja: bool
    notas: Optional[str] = None
    pagada: bool = False
    # Último día de la semana que le toca trabajar (se le paga ese día o después).
    ultimo_dia: date
    dias: List[DiaNomina] = []
    # None = se puede pagar ya; si no, por qué todavía no.
    bloqueo: Optional[str] = None
    # Registros que el sistema cerró solo a las 00:30: el empleado no checó salida y
    # sus horas (y extras) pueden estar infladas. Conviene revisarlos antes de pagar.
    salidas_automaticas: int = 0
    # Con la entrada abierta de hoy proyectada hasta las 23:59; None si no hay ninguna.
    horas_proyectadas: Optional[Decimal] = None
    total_proyectado: Optional[Decimal] = None


class PeriodoNominaResponse(BaseModel):
    id: int
    fecha_inicio: date
    fecha_fin: date
    estado: str
    pagado_en: Optional[datetime] = None
    total: Decimal
    # Registros de asistencia sin salida dentro del periodo (cada uno bloquea el pago de su dueño).
    pendientes_asistencia: int
    # Empleados activos sin reglas de pago: no entran al cálculo.
    sin_configurar: List[str]
    lineas: List[LineaNominaResponse]
