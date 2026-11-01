import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { api } from '@/api/client'
import { useAuthStore } from './auth'

export interface ProveedorGasto { id: number; nombre: string }
export interface CategoriaGasto { id: number; nombre: string }
export interface ArticuloGasto { id: number; nombre: string; unidad: string; costo_estandar: number; categoria_id?: number | null }
export interface EmpleadoGasto { id: number; nombre: string }
export interface ConceptoGasto {
  id: number; nombre: string; monto_tipico: number | null
  frecuencia: 'semanal' | 'mensual' | 'bimestral' | 'anual' | 'cada_n_dias' | 'eventual'
  dia_vencimiento: number | null; intervalo_dias: number | null; activo: boolean
}
export interface ConceptoPendiente {
  concepto: ConceptoGasto; ultimo_gasto: string | null
  estado: 'al_corriente' | 'pendiente' | 'vencido'
}

export const useCatalogosGastosStore = defineStore('catalogos-gastos', () => {
  const auth = useAuthStore()
  const scope = computed(() => `${auth.user?.id ?? ''}:${auth.user?.sucursal_id ?? ''}`)
  const proveedores = ref<ProveedorGasto[]>([])
  const articulos = ref<ArticuloGasto[]>([])
  const categorias = ref<CategoriaGasto[]>([])
  const empleados = ref<EmpleadoGasto[]>([])
  const conceptos = ref<ConceptoPendiente[]>([])
  const loading = ref(false)
  const error = ref('')
  let loaded = false
  let generation = 0
  let pending: Promise<void> | undefined
  function invalidar() { loaded = false; generation++; pending = undefined }
  watch(scope, () => {
    invalidar(); loading.value = false; error.value = ''; proveedores.value = []; articulos.value = []; categorias.value = []; empleados.value = []; conceptos.value = []
  }, { flush: 'sync' })
  async function cargar(force = false): Promise<void> {
    if (force) invalidar()
    if (loaded) return
    if (pending) return pending
    const current = scope.value
    const version = generation
    loading.value = true; error.value = ''
    pending = (async () => {
      try {
        const [p, a, c, e, k] = await Promise.all([
          api.get('/gastos/proveedores'), api.get('/gastos/articulos'),
          api.get('/gastos/categorias-articulo'), api.get('/gastos/empleados'), api.get('/gastos/conceptos/pendientes'),
        ])
        if (current !== scope.value || version !== generation) return
        proveedores.value = p.data; articulos.value = a.data; categorias.value = c.data; empleados.value = e.data; conceptos.value = k.data
        loaded = true
      } catch (exc) {
        if (current === scope.value && version === generation) error.value = 'No se pudieron cargar los catálogos'
        throw exc
      } finally {
        if (version === generation) { loading.value = false; pending = undefined }
      }
    })()
    return pending
  }
  window.addEventListener('catalogos-gastos-cambiados', () => {
    invalidar()
    if (auth.isAuthenticated) void cargar().catch(() => {})
  })
  return { proveedores, articulos, categorias, empleados, conceptos, loading, error, cargar, invalidar }
})
