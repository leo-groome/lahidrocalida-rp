import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { reactive } from 'vue'
const state = vi.hoisted(() => ({
  auth: { isAuthenticated: true, user: { id: 1, sucursal_id: 1 } }, get: vi.fn(),
}))
vi.mock('./auth', async () => {
  const { reactive } = await import('vue')
  return { useAuthStore: () => reactive(state.auth) }
})
vi.mock('@/api/client', () => ({ api: { get: state.get } }))
import { useCatalogosGastosStore } from './catalogos-gastos'

beforeEach(() => {
  setActivePinia(createPinia()); state.get.mockReset()
  state.auth = { isAuthenticated: true, user: { id: 1, sucursal_id: 1 } }
  vi.stubGlobal('window', new EventTarget())
})

describe('catálogos compartidos', () => {
  it('coalesce cargas y refresca tras CRUD', async () => {
    state.get.mockResolvedValue({ data: [{ id: 1, nombre: 'Original' }] })
    const store = useCatalogosGastosStore()
    await Promise.all([store.cargar(), store.cargar(), store.cargar()])
    expect(state.get).toHaveBeenCalledTimes(4)
    expect(store.proveedores[0]!.nombre).toBe('Original')
    state.get.mockResolvedValue({ data: [{ id: 1, nombre: 'Editado' }] })
    window.dispatchEvent(new Event('catalogos-gastos-cambiados'))
    await store.cargar()
    expect(store.proveedores[0]!.nombre).toBe('Editado')
  })
  it('ignora respuesta de una identidad anterior', async () => {
    const resolvers: Array<(value: any) => void> = []
    state.get.mockImplementation(() => new Promise(resolve => resolvers.push(resolve)))
    const store = useCatalogosGastosStore()
    const pending = store.cargar()
    reactive(state.auth).user = { id: 2, sucursal_id: 2 }
    for (const resolve of resolvers) resolve({ data: [{ id: 1, nombre: 'Ajeno' }] })
    await pending
    expect(store.proveedores).toHaveLength(0)
    expect(store.articulos).toHaveLength(0)
  })
  it('expone fallo de carga para recuperación', async () => {
    state.get.mockRejectedValue(new Error('offline'))
    const store = useCatalogosGastosStore()
    await expect(store.cargar()).rejects.toThrow('offline')
    expect(store.error).toBeTruthy()
    expect(store.loading).toBe(false)
    state.get.mockResolvedValue({ data: [] })
    await store.cargar()
    expect(store.error).toBe('')
  })
})
