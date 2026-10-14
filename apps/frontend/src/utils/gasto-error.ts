import { isAxiosError } from 'axios'

export function mensajeErrorGasto(error: unknown): string {
  if (isAxiosError(error)) {
    const detail: unknown = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return 'Revisa los datos del gasto antes de guardar'
    if (!error.response) return 'No se pudo conectar. Reintenta cuando vuelva la conexión'
    return 'No se pudo guardar el gasto'
  }
  return error instanceof Error ? error.message : 'No se pudo guardar el gasto'
}
