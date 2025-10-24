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

export interface PedidoResponse {
  id: number
  numero_display: string
  nombre_cliente: string | null
  total: string | number
  estado: 'pendiente' | 'preparando' | 'listo' | 'completado' | 'cancelado'
  metodo_pago: 'efectivo' | 'tarjeta' | 'transferencia'
  tipo_orden: 'aqui' | 'llevar' | 'uber_eats'
  sucursal_id: number
  usuario_id: number
  fecha_creacion: string
}
