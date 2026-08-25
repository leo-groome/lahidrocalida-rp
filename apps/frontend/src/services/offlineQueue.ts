import { ref, computed } from 'vue'
import { api } from '@/api/client'

/**
 * Cola offline para mutaciones del mesero (crear pedido, agregar artículos).
 *
 * Si el POST/PUT falla por un error DE RED (sin conexión, timeout — no llegó
 * respuesta del server), se persiste en localStorage y se reintenta con
 * backoff exponencial, igual que la reconexión de websocket.ts. Reutiliza el
 * client_request_id que el propio caller ya genera para idempotencia: el
 * backend ya sabe devolver el resultado existente si el mismo request llega
 * dos veces (por retry o por reconstrucción de la cola tras un reload).
 *
 * Un error de servidor real (400/403/…) NO se reintenta — reintentar el
 * mismo payload inválido para siempre trabaría la cola.
 */

interface QueuedRequest {
  id: string // = client_request_id
  method: 'post' | 'put'
  url: string
  payload: unknown
  createdAt: number
  attempts: number
}

const STORAGE_KEY = 'mesero_cola_offline_v1'
const BASE_DELAY_MS = 3000
const MAX_DELAY_MS = 30000

function cargarDeStorage(): QueuedRequest[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function guardarEnStorage(items: QueuedRequest[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
  } catch {
    // localStorage lleno o deshabilitado (modo privado): la cola sigue viva
    // en memoria para esta sesión, solo se pierde la persistencia entre reloads.
  }
}

const queue = ref<QueuedRequest[]>(cargarDeStorage())
export const pendingCount = computed(() => queue.value.length)

let flushTimer: number | null = null
let flushing = false

function esErrorDeRed(e: any): boolean {
  // axios: sin `response` significa que el request nunca llegó a completarse
  // contra el server (offline, DNS, timeout, CORS) — a diferencia de un 4xx/5xx
  // real, que sí llegó y respondió.
  return !e?.response
}

function backoffDelay(attempts: number): number {
  return Math.min(BASE_DELAY_MS * 2 ** attempts, MAX_DELAY_MS)
}

function scheduleFlush(delay: number): void {
  if (flushTimer) {
    clearTimeout(flushTimer)
  }
  flushTimer = window.setTimeout(() => {
    flush()
  }, delay)
}

async function flush(): Promise<void> {
  if (flushing) return
  flushing = true
  try {
    while (queue.value.length > 0) {
      const item = queue.value[0]
      try {
        await api[item.method](item.url, item.payload)
        queue.value = queue.value.slice(1)
        guardarEnStorage(queue.value)
      } catch (e: any) {
        if (esErrorDeRed(e)) {
          item.attempts++
          guardarEnStorage(queue.value)
          break // seguir sin red: reintentar más tarde, no trabar en loop
        }
        // Error real del servidor: descartar para no bloquear la cola con un
        // payload que nunca va a pasar validación.
        console.error('offlineQueue: request descartado por error del servidor', item, e)
        queue.value = queue.value.slice(1)
        guardarEnStorage(queue.value)
      }
    }
  } finally {
    flushing = false
  }
  if (queue.value.length > 0) {
    scheduleFlush(backoffDelay(queue.value[0].attempts))
  }
}

window.addEventListener('online', () => scheduleFlush(0))
// Reintentar lo que haya quedado pendiente de una sesión anterior (reload de
// página con la cola todavía persistida en localStorage).
scheduleFlush(0)

export type ResultadoEnvio<T> =
  | { estado: 'ok'; data: T }
  | { estado: 'encolado' }
  | { estado: 'error'; error: any }

/**
 * Intenta el request inmediatamente; si falla por conectividad lo encola
 * (con el client_request_id del caller) para reintentar solo, y resuelve
 * como "encolado" en vez de propagar el error — desde la perspectiva del
 * mesero, la acción ya quedó registrada y se sincronizará sola.
 */
export async function enviarOEncolar<T = any>(
  method: 'post' | 'put',
  url: string,
  payload: unknown,
  clientRequestId: string
): Promise<ResultadoEnvio<T>> {
  try {
    const { data } = await api[method]<T>(url, payload)
    return { estado: 'ok', data }
  } catch (e: any) {
    if (esErrorDeRed(e)) {
      if (!queue.value.some((q) => q.id === clientRequestId)) {
        queue.value = [
          ...queue.value,
          { id: clientRequestId, method, url, payload, createdAt: Date.now(), attempts: 0 },
        ]
        guardarEnStorage(queue.value)
      }
      scheduleFlush(0)
      return { estado: 'encolado' }
    }
    return { estado: 'error', error: e }
  }
}
