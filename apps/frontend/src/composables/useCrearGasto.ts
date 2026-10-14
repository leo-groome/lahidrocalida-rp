import { useGastosPendientesStore } from '@/stores/gastos-pendientes'
import type { GastoPendiente } from '@/utils/gasto-queue-db'
import type { GastoPayload } from '@/utils/gasto-payload'

/** Conserva el snapshot hasta obtener una respuesta definitiva del servidor. */
export function useGastoSubmission() {
  const cola = useGastosPendientesStore()
  let operation: GastoPendiente | undefined
  async function enviar(input: GastoPayload, fotos: File[] = []) {
    if (!operation) {
      const total = input.total_manual ?? (
        input.tipo_gasto === 'nomina'
          ? (input.nomina_detalles ?? []).reduce((sum, d) => sum + Number(d.monto), 0)
          : (input.detalles ?? []).reduce((sum, d) => sum + Number(d.subtotal_linea), 0)
      )
      operation = await cola.agregar(input, fotos, total,
        input.tipo_gasto === 'nomina' ? 'nómina' : 'gasto')
    }
    await cola.enviar(operation)
    if (!operation.gastoId) {
      const message = operation.error || 'Pendiente guardado. Reintenta desde Registro rápido.'
      // Un rechazo de validación garantiza que no se creó el gasto y permite corregir captura.
      if (operation.rechazado) {
        await cola.descartar(operation.id)
        operation = undefined
      }
      throw new Error(message)
    }
    const result = { id: operation.gastoId, fotosFallidas: operation.fotosFallidas }
    operation = undefined
    return result
  }
  return { enviar }
}
