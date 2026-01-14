export type Rol = 'mesero' | 'cajero' | 'cocina' | 'administrador' | 'compras'

export interface Platillo {
  id: number
  nombre: string
  descripcion?: string
  precio: string | number
  categoria: string
  estado: 'disponible' | 'no_disponible'
  kds_name?: string
}

export interface ArticuloPedidoCreate {
  platillo_id: number
  cantidad: number
  modificaciones?: string | null
}

export interface ArticuloPedidoResponse {
  id: number
  pedido_id: number
  platillo_id: number
  cantidad: number
  precio_cobrado: string | number
  modificaciones?: string | null
  estado_item: 'pendiente' | 'listo'
  platillo?: Platillo
}

export interface PlatilloResponse {
  id: number
  nombre: string
  descripcion?: string
  precio: number
  categoria: string
  estado: 'disponible' | 'no_disponible'
  kds_name?: string
}

export interface PedidoCreate {
  nombre_cliente: string
  mesa?: string
  tipo_orden: 'aqui' | 'llevar' | 'uber_eats'
  metodo_pago?: string // Agregar metodo_pago opcional
  articulos: Array<{
    platillo_id: number
    cantidad: number
    modificaciones?: string
  }>
}

export interface PedidoResponse {
  id: number
  numero_display: string
  nombre_cliente: string | null
  mesa: string | null
  total: string | number
  estado: 'pendiente' | 'preparando' | 'listo' | 'entregado' | 'cuenta_solicitada' | 'pagado' | 'cancelado'
  metodo_pago: 'efectivo' | 'tarjeta' | 'transferencia' | null
  propina_efectivo: number
  propina_tarjeta: number
  propina_total: number
  tipo_orden: 'aqui' | 'llevar' | 'uber_eats'
  sucursal_id: number
  usuario_id: number
  fecha_creacion: string
  created_at?: string // Alias para fecha_creacion
  articulos_pedido?: ArticuloPedidoResponse[]
}
