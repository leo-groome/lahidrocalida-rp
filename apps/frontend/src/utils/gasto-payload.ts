export interface GastoPayload {
  proveedor_id?: number | null
  tipo_gasto: string
  metodo_pago: string
  fecha_gasto?: string | null
  total_manual?: number | null
  turno_id?: number | null
  descripcion?: string | null
  notas?: string | null
  folio?: string | null
  detalles?: Array<{ articulo_id: number | null; cantidad: number | null; precio_unitario: number; subtotal_linea: number }>
  nomina_detalles?: Array<{ usuario_id: number; monto: number; notas?: string | null }>
  client_request_id?: string
}

/** Snapshot estable para que un reintento no cambie fecha, contenido ni UUID. */
export function prepararPayloadGasto(input: GastoPayload): GastoPayload {
  return {
    proveedor_id: input.proveedor_id ?? null,
    tipo_gasto: input.tipo_gasto,
    metodo_pago: input.metodo_pago,
    fecha_gasto: input.fecha_gasto || new Date().toISOString(),
    total_manual: input.total_manual ?? null,
    turno_id: input.turno_id ?? null,
    descripcion: input.descripcion ?? input.notas ?? null,
    notas: input.notas ?? null,
    folio: input.folio ?? null,
    detalles: (input.detalles ?? []).map(d => ({
      articulo_id: d.articulo_id, cantidad: d.cantidad,
      precio_unitario: d.precio_unitario, subtotal_linea: d.subtotal_linea,
    })),
    nomina_detalles: (input.nomina_detalles ?? []).map(d => ({ ...d })),
    client_request_id: input.client_request_id ?? crypto.randomUUID(),
  }
}
