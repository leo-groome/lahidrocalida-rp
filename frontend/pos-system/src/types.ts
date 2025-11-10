export interface Platillo {
  id: number
  nombre: string
  descripcion?: string
  precio: string | number
  categoria: string
  estado: 'disponible' | 'no_disponible'
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

export interface PedidoResponse {
  id: number
  numero_display: string
  nombre_cliente: string | null
  mesa: string | null
  total: string | number
  estado: 'pendiente' | 'preparando' | 'listo' | 'entregado' | 'cuenta_solicitada' | 'pagado' | 'cancelado'
  metodo_pago: 'efectivo' | 'tarjeta' | 'transferencia' | null
  tipo_orden: 'aqui' | 'llevar' | 'uber_eats'
  sucursal_id: number
  usuario_id: number
  fecha_creacion: string
  articulos_pedido?: ArticuloPedidoResponse[]
}
