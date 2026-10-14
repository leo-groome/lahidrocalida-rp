/**
 * Fuente única de verdad para los estados de pedido, artículo de pedido y turno.
 *
 * Espejo del enum backend en `apps/backend/app/domain/estados.py`. Los valores
 * string son EXACTAMENTE los que se persisten en la DB y viajan por la API/WS —
 * no traducir, no inventar variantes. Si el backend agrega/renombra un estado,
 * este archivo se actualiza en el mismo PR.
 */

/** Estados de un pedido completo. */
export const EstadoPedido = {
  PENDIENTE: 'pendiente',
  PREPARANDO: 'preparando',
  LISTO: 'listo',
  ENTREGADO: 'entregado',
  CUENTA_SOLICITADA: 'cuenta_solicitada',
  PAGADO: 'pagado',
  CANCELADO: 'cancelado',
  DIVIDIDO: 'dividido',
  /** Solo Uber Eats: el repartidor ya recogió el pedido (no se cobra en Caja). */
  ENTREGADO_REPARTIDOR: 'entregado_repartidor',
} as const

export type EstadoPedido = (typeof EstadoPedido)[keyof typeof EstadoPedido]

/** Estados de un artículo dentro de un pedido (KDS). */
export const EstadoArticuloPedido = {
  PENDIENTE: 'pendiente',
  PREPARANDO: 'preparando',
  LISTO: 'listo',
  ENTREGADO: 'entregado',
} as const

export type EstadoArticuloPedido = (typeof EstadoArticuloPedido)[keyof typeof EstadoArticuloPedido]

/** Estados de un turno de caja. */
export const EstadoTurno = {
  ABIERTO: 'abierto',
  CERRADO: 'cerrado',
} as const

export type EstadoTurno = (typeof EstadoTurno)[keyof typeof EstadoTurno]

/** Pedidos que ya no están "en curso" para efectos de cobro/cierre. */
export const ESTADOS_PEDIDO_FINALES: readonly EstadoPedido[] = [
  EstadoPedido.PAGADO,
  EstadoPedido.CANCELADO,
  EstadoPedido.DIVIDIDO,
  EstadoPedido.ENTREGADO_REPARTIDOR,
]

/** Tipo de orden del canal Uber Eats (se cobra fuera de Caja). */
export const TIPO_ORDEN_UBER = 'uber_eats'
