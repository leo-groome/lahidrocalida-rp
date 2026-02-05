<template>
  <div class="gastos-historial">
    <div class="bg-white rounded-lg shadow">
      <!-- Header y Filtros -->
      <div class="px-6 py-4 border-b border-gray-200">
        <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-4">
          <h2 class="text-lg font-medium text-gray-900">Historial de Gastos</h2>
          <div class="flex gap-2">
            <button 
              @click="$emit('new-gasto')" 
              class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm font-medium flex items-center"
            >
              <span class="mr-1">+</span> Nuevo Gasto
            </button>
          </div>
        </div>

        <!-- Filtros Avanzados -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 bg-gray-50 p-4 rounded-lg">
          <div>
            <label class="block text-xs font-medium text-gray-500 mb-1">Desde</label>
            <input 
              type="date" 
              v-model="filters.fecha_inicio"
              class="w-full border-gray-300 rounded-md shadow-sm text-sm focus:ring-blue-500 focus:border-blue-500"
            >
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-500 mb-1">Hasta</label>
            <input 
              type="date" 
              v-model="filters.fecha_fin"
              class="w-full border-gray-300 rounded-md shadow-sm text-sm focus:ring-blue-500 focus:border-blue-500"
            >
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-500 mb-1">Proveedor</label>
            <select 
              v-model="filters.proveedor_id"
              class="w-full border-gray-300 rounded-md shadow-sm text-sm focus:ring-blue-500 focus:border-blue-500"
            >
              <option :value="null">Todos</option>
              <option v-for="p in proveedores" :key="p.id" :value="p.id">{{ p.nombre }}</option>
            </select>
          </div>
          <div class="flex items-end gap-2">
            <button 
              @click="loadGastos" 
              class="flex-1 bg-blue-600 text-white py-2 rounded-md text-sm hover:bg-blue-700 font-medium"
            >
              Filtrar
            </button>
            <button 
              @click="clearFilters" 
              class="bg-gray-200 text-gray-700 py-2 px-3 rounded-md text-sm hover:bg-gray-300"
              title="Limpiar filtros"
            >
              x
            </button>
          </div>
        </div>
      </div>
      
      <!-- Lista de gastos -->
      <div v-if="loading" class="py-12 flex justify-center">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>

      <div v-else-if="gastos.length === 0" class="py-12 text-center text-gray-500">
        No se encontraron gastos con estos filtros.
      </div>

      <div v-else class="divide-y divide-gray-200">
        <div 
          v-for="gasto in gastos" 
          :key="gasto.id" 
          class="px-6 py-4 hover:bg-gray-50 transition-colors"
        >
          <div class="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
            <!-- Info Principal -->
            <div class="flex-1">
              <div class="flex items-center justify-between mb-1">
                <h3 class="font-semibold text-gray-900 text-base">{{ gasto.proveedor.nombre }}</h3>
                <span class="text-sm font-medium text-gray-500">{{ formatDate(gasto.fecha_gasto) }}</span>
              </div>
              
              <div class="flex flex-wrap items-center gap-2 text-sm text-gray-600 mb-2">
                <span :class="[
                  'px-2 py-0.5 rounded-full text-xs font-medium uppercase tracking-wide',
                  gasto.tipo_gasto === 'nomina' ? 'bg-purple-100 text-purple-800' : 
                  gasto.tipo_gasto === 'indirecto' ? 'bg-orange-100 text-orange-800' : 'bg-blue-100 text-blue-800'
                ]">
                  {{ gasto.tipo_gasto }}
                </span>
                <span class="flex items-center gap-1 text-xs bg-gray-100 px-2 py-0.5 rounded text-gray-700 capitalize">
                  {{ gasto.metodo_pago === 'efectivo' ? '💵' : '💳' }} {{ gasto.metodo_pago }}
                </span>
                <span v-if="gasto.folio" class="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                  #{{ gasto.folio }}
                </span>
              </div>

              <p v-if="gasto.descripcion" class="text-sm text-gray-500 italic mb-2">
                {{ gasto.descripcion }}
              </p>

              <!-- Detalles Expansibles (Preview simple) -->
              <div v-if="gasto.detalles.length > 0" class="mt-2 pl-3 border-l-2 border-gray-200">
                <p class="text-xs text-gray-400 mb-1">Artículos:</p>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1">
                  <div v-for="d in gasto.detalles" :key="d.id" class="text-xs flex justify-between text-gray-600">
                    <span>{{ d.articulo.nombre }} ({{ d.cantidad }})</span>
                    <span>${{ formatCurrency(d.subtotal_linea) }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Columna Derecha: Total y Acciones -->
            <div class="flex flex-row md:flex-col items-center md:items-end justify-between md:justify-start gap-4 min-w-[120px]">
              <div class="text-right">
                <div class="text-lg font-bold text-gray-900">${{ formatCurrency(gasto.total) }}</div>
                <div v-if="gasto.total_manual" class="text-xs text-orange-600" title="Total ajustado manualmente">
                  (Manual)
                </div>
              </div>
              
              <div class="flex gap-2">
                <button 
                  @click="$emit('edit-gasto', gasto)" 
                  class="text-blue-600 hover:text-blue-800 text-sm font-medium hover:underline"
                >
                  Editar
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Paginación -->
      <div v-if="totalItems > 0" class="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
        <div class="text-sm text-gray-500">
          Mostrando {{ (page - 1) * pageSize + 1 }} a {{ Math.min(page * pageSize, totalItems) }} de {{ totalItems }} resultados
        </div>
        <div class="flex gap-2">
          <button 
            @click="changePage(page - 1)" 
            :disabled="page === 1"
            class="px-3 py-1 border rounded text-sm disabled:opacity-50 hover:bg-gray-50"
          >
            Anterior
          </button>
          <button 
            @click="changePage(page + 1)" 
            :disabled="page * pageSize >= totalItems"
            class="px-3 py-1 border rounded text-sm disabled:opacity-50 hover:bg-gray-50"
          >
            Siguiente
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import api from '@/api/client'
import { parseSafeDate } from '@/utils/dateUtils'

const emit = defineEmits(['new-gasto', 'edit-gasto'])

const gastos = ref<any[]>([])
const proveedores = ref<any[]>([])
const loading = ref(false)

// Paginación
const page = ref(1)
const pageSize = ref(50)
const totalItems = ref(0)

// Fechas por defecto: mes actual
const now = new Date()
const firstDay = new Date(now.getFullYear(), now.getMonth(), 1)
const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0)

const filters = ref({
  fecha_inicio: firstDay.toISOString().split('T')[0],
  fecha_fin: lastDay.toISOString().split('T')[0],
  proveedor_id: null
})

const formatCurrency = (val: number) => val.toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const formatDate = (dateStr: string) => {
  const date = parseSafeDate(dateStr)
  if (!date) return ''
  return date.toLocaleDateString('es-MX', {
    day: '2-digit', month: 'short', year: 'numeric'
  })
}

const loadProveedores = async () => {
  try {
    const res = await api.get('/gastos/proveedores')
    proveedores.value = res.data
  } catch (e) {
    console.error(e)
  }
}

const loadGastos = async () => {
  loading.value = true
  try {
    const params: any = { 
      ...filters.value,
      page: page.value,
      page_size: pageSize.value
    }
    // Limpiar nulos
    Object.keys(params).forEach(key => params[key] === null && delete params[key])
    
    const res = await api.get('/gastos/', { params })
    
    // Soporte para respuesta paginada o lista simple (compatibilidad)
    if (res.data.items && typeof res.data.total === 'number') {
      gastos.value = res.data.items
      totalItems.value = res.data.total
    } else if (Array.isArray(res.data)) {
      gastos.value = res.data
      totalItems.value = res.data.length // Fallback
    }
    
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const changePage = (newPage: number) => {
  page.value = newPage
  loadGastos()
}

const clearFilters = () => {
  filters.value = {
    fecha_inicio: '',
    fecha_fin: '',
    proveedor_id: null
  }
  page.value = 1
  loadGastos()
}

// Recargar al cambiar filtros
watch(filters, () => {
  page.value = 1 // Resetear a página 1 al filtrar
  // Debounce opcional podría ir aquí, pero por ahora directo
}, { deep: true })

onMounted(() => {
  loadProveedores()
  loadGastos()
})

defineExpose({ loadGastos }) // Para recargar desde el padre
</script>
