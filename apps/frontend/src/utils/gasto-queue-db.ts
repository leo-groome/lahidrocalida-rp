import type { GastoPayload } from './gasto-payload'

export interface FotoPendiente { id: string; file: File }
export interface GastoPendiente {
  id: string
  usuarioId: number
  sucursalId: number
  total: number
  resumen: string
  estado: 'pendiente' | 'enviando' | 'ok' | 'parcial' | 'error'
  error: string
  fotosFallidas: number
  payload: GastoPayload
  fotos: FotoPendiente[]
  rechazado?: boolean
  gastoId?: number
}

function open(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open('gastos-pendientes-v1', 1)
    req.onupgradeneeded = () => req.result.createObjectStore('operaciones', { keyPath: 'id' })
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
    req.onblocked = () => reject(new Error('Cierra otras pestañas para recuperar los pendientes'))
  })
}

async function transaction<T>(mode: IDBTransactionMode, action: (store: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  const db = await open()
  return new Promise((resolve, reject) => {
    const tx = db.transaction('operaciones', mode)
    const req = action(tx.objectStore('operaciones'))
    tx.oncomplete = () => { db.close(); resolve(req.result) }
    tx.onerror = tx.onabort = () => { db.close(); reject(tx.error ?? req.error) }
  })
}

export const leerPendientes = () => transaction('readonly', s => s.getAll()) as Promise<GastoPendiente[]>
// Construir copia plana: IndexedDB no acepta los proxies de Vue.
export const guardarPendiente = (p: GastoPendiente) => transaction('readwrite', s => s.put({
  ...p, payload: JSON.parse(JSON.stringify(p.payload)), fotos: p.fotos.map(f => ({ id: f.id, file: f.file })),
}))
export const borrarPendiente = (id: string) => transaction('readwrite', s => s.delete(id))
