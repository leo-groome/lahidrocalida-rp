import { ref } from 'vue'
import { api } from '@/api/client'

// Contrato de POST /gastos/ para gastos NO nómina (insumos / servicios).
// Extraído de GastoCheckout.vue submit() para no duplicar la forma del payload.
export interface CrearGastoArgs {
  proveedorId: number | null
  tipoGasto: 'directo' | 'indirecto'
  metodoPago: 'efectivo' | 'tarjeta'
  detalles: Array<{
    articulo_id: number | null
    cantidad: number | null
    precio_unitario: number
    subtotal_linea: number
  }>
  notas?: string | null
  folio?: string | null
  /** datetime-local ("YYYY-MM-DDTHH:mm") o ISO; por defecto: ahora. */
  fechaGasto?: string | null
  totalManual?: number | null
  turnoId?: number | null
}

export function useCrearGasto() {
  const submitting = ref(false)
  const error = ref<string | null>(null)

  async function crearGasto(args: CrearGastoArgs) {
    submitting.value = true
    error.value = null
    try {
      const payload = {
        proveedor_id: args.proveedorId,
        tipo_gasto: args.tipoGasto,
        metodo_pago: args.metodoPago,
        folio: args.folio || null,
        notas: args.notas || null,
        descripcion: args.notas || null,
        fecha_gasto: args.fechaGasto
          ? new Date(args.fechaGasto).toISOString()
          : new Date().toISOString(),
        turno_id: args.turnoId ?? null,
        total_manual: args.totalManual ?? null,
        detalles: args.detalles.map((d) => ({
          articulo_id: d.articulo_id,
          cantidad: d.cantidad,
          precio_unitario: d.precio_unitario,
          subtotal_linea: d.subtotal_linea,
        })),
        nomina_detalles: [],
      }
      const { data } = await api.post('/gastos/', payload)
      return data
    } catch (e: any) {
      error.value = e?.response?.data?.detail || 'Error al guardar el gasto'
      throw e
    } finally {
      submitting.value = false
    }
  }

  return { crearGasto, submitting, error }
}
