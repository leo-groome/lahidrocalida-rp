import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
const state = vi.hoisted(() => ({
  auth: { isAuthenticated: true, user: { id: 1, sucursal_id: 1 } as { id: number; sucursal_id: number } | null },
  disk: new Map<string, any>(), post: vi.fn(), failSave: false,
}))
vi.mock('./auth', () => ({ useAuthStore: () => state.auth }))
vi.mock('@/api/client', () => ({ api: { post: state.post } }))
vi.mock('@/utils/gasto-queue-db', () => ({
  leerPendientes: async () => [...state.disk.values()].map(p => structuredClone(p)),
  guardarPendiente: async (p: any) => {
    if (state.failSave) throw new Error('quota')
    state.disk.set(p.id, { ...p, payload: JSON.parse(JSON.stringify(p.payload)), fotos: p.fotos.map((f: any) => ({ ...f })) })
  },
  borrarPendiente: async (id: string) => { state.disk.delete(id) },
}))
import { useGastosPendientesStore } from './gastos-pendientes'

beforeEach(() => {
  setActivePinia(createPinia()); state.disk.clear(); state.post.mockReset(); state.failSave = false
  state.auth.user = { id: 1, sucursal_id: 1 }; state.auth.isAuthenticated = true
  vi.stubGlobal('navigator', {})
})
const payload = { tipo_gasto: 'directo', metodo_pago: 'efectivo', total_manual: 100 }

describe('recuperación de operaciones', () => {
  it('no limpia captura si no puede persistir', async () => {
    state.failSave = true
    const store = useGastosPendientesStore()
    await expect(store.agregar(payload, [], 100, 'compra')).rejects.toThrow('quota')
    expect(store.pendientes).toHaveLength(0)
    expect(state.post).not.toHaveBeenCalled()
  })
  it('recupera respuesta perdida con mismo UUID y snapshot', async () => {
    const store = useGastosPendientesStore()
    const p = await store.agregar(payload, [], 100, 'compra')
    state.post.mockRejectedValueOnce(new Error('respuesta perdida')).mockResolvedValueOnce({ data: { id: 9 } })
    await store.enviar(p)
    expect(p.estado).toBe('error')
    await store.enviar(p)
    expect(p.estado).toBe('ok')
    expect(state.post.mock.calls[0]![1]).toEqual(state.post.mock.calls[1]![1])
  })
  it('reintenta solo fotos tras gasto confirmado', async () => {
    const store = useGastosPendientesStore()
    const file = new File(['photo'], 'ticket.webp', { type: 'image/webp' })
    const p = await store.agregar(payload, [file], 100, 'compra')
    state.post.mockResolvedValueOnce({ data: { id: 9 } }).mockRejectedValueOnce(new Error('foto offline')).mockResolvedValueOnce({ data: { id: 1 } })
    await store.enviar(p)
    expect(p.estado).toBe('parcial')
    await store.enviar(p)
    expect(p.estado).toBe('ok')
    expect(state.post.mock.calls.filter(c => c[0] === '/gastos/')).toHaveLength(1)
    expect(state.post.mock.calls[1]![2]).toEqual(state.post.mock.calls[2]![2])
  })
  it('recupera operación interrumpida al reiniciar store', async () => {
    const first = useGastosPendientesStore()
    const p = await first.agregar(payload, [], 100, 'compra')
    state.disk.get(p.id).estado = 'enviando'
    setActivePinia(createPinia())
    const second = useGastosPendientesStore()
    await second.cargar()
    expect(second.pendientes[0]!.estado).toBe('pendiente')
    expect(second.pendientes[0]!.payload.client_request_id).toBe(p.id)
  })
  it('no envía bajo otra identidad y oculta sus pendientes', async () => {
    const store = useGastosPendientesStore()
    const p = await store.agregar(payload, [], 100, 'compra')
    state.auth.user = { id: 2, sucursal_id: 1 }
    await expect(store.enviar(p)).rejects.toThrow('usuario')
    expect(state.post).not.toHaveBeenCalled()
  })
})
