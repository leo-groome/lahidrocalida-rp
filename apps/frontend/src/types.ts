import type { EstadoArticuloPedido, EstadoPedido, EstadoTurno } from "./constants/estados";

export type Rol = "mesero" | "cajero" | "cocina" | "administrador" | "compras";

export interface Platillo {
  id: number;
  nombre: string;
  descripcion?: string;
  precio: string | number;
  categoria: string;
  estado: "disponible" | "no_disponible";
  kds_name?: string;
}

export interface ArticuloPedidoCreate {
  platillo_id: number;
  cantidad: number;
  modificaciones?: string | null;
  proteina?: string;
}

export interface ArticuloPedidoResponse {
  id: number;
  pedido_id: number;
  platillo_id: number;
  cantidad: number;
  precio_cobrado: string | number;
  modificaciones?: string | null;
  estado_item: EstadoArticuloPedido;
  platillo?: Platillo;
}

export interface PlatilloResponse {
  id: number;
  nombre: string;
  descripcion?: string;
  precio: number;
  categoria: string;
  estado: "disponible" | "no_disponible";
  kds_name?: string;
  defaultPortion?: number;
}

export interface PedidoCreate {
  nombre_cliente: string | null;
  mesa: string | null;
  tipo_orden: "aqui" | "llevar" | "uber_eats";
  metodo_pago?: string;
  articulos: Array<{
    platillo_id: number;
    cantidad: number;
    modificaciones?: string;
    proteina?: string;
  }>;
  // Clave de idempotencia: reintentar el envío con la misma clave no duplica el pedido
  client_request_id?: string;
}

export interface PedidoResponse {
  id: number;
  numero_display: string;
  nombre_cliente: string | null;
  mesa: string | null;
  total: string | number;
  usuario_nombre?: string | null;
  fecha_pago?: string | null;
  estado: EstadoPedido;
  metodo_pago: "efectivo" | "tarjeta" | "transferencia" | null;
  propina_efectivo: number;
  propina_tarjeta: number;
  propina_total: number;
  tipo_orden: "aqui" | "llevar" | "uber_eats";
  sucursal_id: number;
  usuario_id: number;
  fecha_creacion: string;
  created_at?: string;
  articulos_pedido?: ArticuloPedidoResponse[];
}

export interface Denominacion {
  denominacion: number;
  cantidad: number;
  subtotal?: number;
}

export interface Turno {
  id: number;
  sucursal_id: number;
  usuario_id: number;
  fecha_apertura: string;
  fecha_cierre: string | null;
  estado: EstadoTurno;
  total_inicial: number;
  total_final: number | null;
  ventas_efectivo: number | null;
  propinas_efectivo: number | null;
  diferencia: number | null;
  observaciones: string | null;
  denominaciones_iniciales: Denominacion[];
  denominaciones_finales: Denominacion[] | null;
  usuario_nombre: string | null;
  sucursal_nombre: string | null;
}

export interface ReporteDiaTicket {
  id: number;
  numero_display: string;
  mesa: string | null;
  nombre_cliente: string | null;
  estado: "pagado" | "cancelado" | string;
  metodo_pago: "efectivo" | "tarjeta" | "transferencia" | null;
  total: number;
  propina_efectivo: number;
  propina_tarjeta: number;
  propina_total: number;
  fecha_pago: string | null;
  fecha_creacion: string | null;
  fecha_evento: string | null;
  mesero_nombre: string | null;
  tipo_orden?: "aqui" | "llevar" | "uber_eats";
}

export interface ReporteDiaAnalytics {
  fecha: string;
  total_pedidos: number;
  promedio_ticket: number;
  cancelaciones: number;
  ingresos: {
    efectivo: number;
    tarjeta: number;
    transferencia: number;
    total: number;
  };
  propinas: {
    efectivo: number;
    tarjeta: number;
    total: number;
  };
  ventas_por_hora: Array<{
    hora: number;
    cantidad: number;
    total: number;
  }>;
  tipos_orden: Array<{
    tipo: string;
    cantidad: number;
  }>;
  estado_actual: Array<{
    estado: string;
    cantidad: number;
  }>;
  productos_mas_vendidos: Array<{
    nombre: string;
    cantidad: number;
  }>;
}
