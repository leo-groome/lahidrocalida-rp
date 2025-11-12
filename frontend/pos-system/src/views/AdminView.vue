<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <AppHeader title="Panel de Administración" />

    <!-- Navegación de pestañas -->
    <div class="bg-white border-b border-gray-200">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <nav class="flex space-x-8" aria-label="Tabs">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="activeTab = tab.id"
            :class="[
              activeTab === tab.id
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
              'whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm'
            ]"
          >
            {{ tab.name }}
          </button>
        </nav>
      </div>
    </div>

    <!-- Contenido principal -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Tab: Dashboard -->
      <div v-if="activeTab === 'dashboard'">
        <div class="mb-6">
          <div class="flex justify-between items-center">
            <h2 class="text-xl font-semibold text-gray-900">Dashboard - Hoy</h2>
            <button
              @click="refreshDashboard"
              :disabled="loadingDashboard"
              class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {{ loadingDashboard ? 'Actualizando...' : 'Actualizar' }}
            </button>
          </div>
        </div>

        <!-- Métricas del día -->
        <div v-if="dashboardData" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <!-- Total Pedidos -->
          <div class="bg-white overflow-hidden shadow rounded-lg">
            <div class="p-5">
              <div class="flex items-center">
                <div class="flex-shrink-0">
                  <div class="w-8 h-8 bg-blue-500 rounded-md flex items-center justify-center">
                    <span class="text-white text-sm font-bold">#</span>
                  </div>
                </div>
                <div class="ml-5 w-0 flex-1">
                  <dl>
                    <dt class="text-sm font-medium text-gray-500 truncate">Total Pedidos</dt>
                    <dd class="text-lg font-medium text-gray-900">{{ dashboardData.total_pedidos }}</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <!-- Total Efectivo -->
          <div class="bg-white overflow-hidden shadow rounded-lg">
            <div class="p-5">
              <div class="flex items-center">
                <div class="flex-shrink-0">
                  <div class="w-8 h-8 bg-green-500 rounded-md flex items-center justify-center">
                    <span class="text-white text-sm font-bold">$</span>
                  </div>
                </div>
                <div class="ml-5 w-0 flex-1">
                  <dl>
                    <dt class="text-sm font-medium text-gray-500 truncate">Efectivo</dt>
                    <dd class="text-lg font-medium text-gray-900">${{ dashboardData.ingresos.efectivo.toFixed(2) }}</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <!-- Total Tarjeta -->
          <div class="bg-white overflow-hidden shadow rounded-lg">
            <div class="p-5">
              <div class="flex items-center">
                <div class="flex-shrink-0">
                  <div class="w-8 h-8 bg-purple-500 rounded-md flex items-center justify-center">
                    <span class="text-white text-sm font-bold">💳</span>
                  </div>
                </div>
                <div class="ml-5 w-0 flex-1">
                  <dl>
                    <dt class="text-sm font-medium text-gray-500 truncate">Tarjeta</dt>
                    <dd class="text-lg font-medium text-gray-900">${{ dashboardData.ingresos.tarjeta.toFixed(2) }}</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <!-- Total General -->
          <div class="bg-white overflow-hidden shadow rounded-lg">
            <div class="p-5">
              <div class="flex items-center">
                <div class="flex-shrink-0">
                  <div class="w-8 h-8 bg-yellow-500 rounded-md flex items-center justify-center">
                    <span class="text-white text-sm font-bold">💰</span>
                  </div>
                </div>
                <div class="ml-5 w-0 flex-1">
                  <dl>
                    <dt class="text-sm font-medium text-gray-500 truncate">Total Ingresos</dt>
                    <dd class="text-lg font-medium text-gray-900">${{ dashboardData.ingresos.total.toFixed(2) }}</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Productos más vendidos -->
        <div v-if="dashboardData" class="bg-white shadow rounded-lg">
          <div class="px-4 py-5 sm:p-6">
            <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">Productos Más Vendidos (Hoy)</h3>
            <div v-if="dashboardData.productos_mas_vendidos.length > 0">
              <div class="space-y-3">
                <div 
                  v-for="(producto, index) in dashboardData.productos_mas_vendidos" 
                  :key="index"
                  class="flex justify-between items-center py-2 px-3 bg-gray-50 rounded-md"
                >
                  <span class="font-medium text-gray-900">{{ producto.nombre }}</span>
                  <span class="text-sm text-gray-600">{{ producto.cantidad }} unidades</span>
                </div>
              </div>
            </div>
            <div v-else class="text-gray-500 text-center py-4">
              No hay ventas registradas hoy
            </div>
          </div>
        </div>
      </div>

      <!-- Tab: Reportes Semanales -->
      <div v-if="activeTab === 'reportes'">
        <div class="mb-6">
          <div class="flex justify-between items-center">
            <h2 class="text-xl font-semibold text-gray-900">Reportes Semanales</h2>
            <div class="flex items-center space-x-4">
              <input
                v-model="selectedWeekDate"
                type="date"
                class="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
              <button
                @click="loadWeeklyReport"
                :disabled="loadingWeekly"
                class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {{ loadingWeekly ? 'Cargando...' : 'Cargar Semana' }}
              </button>
            </div>
          </div>
        </div>

        <div v-if="weeklyData">
          <!-- Información del período -->
          <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
            <h3 class="font-medium text-blue-900">{{ weeklyData.periodo.descripcion }}</h3>
            <p class="text-sm text-blue-700">
              Del {{ formatDate(weeklyData.periodo.inicio) }} al {{ formatDate(weeklyData.periodo.fin) }}
            </p>
          </div>

          <!-- Métricas semanales -->
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-8">
            <div class="bg-white overflow-hidden shadow rounded-lg">
              <div class="p-5">
                <div class="flex items-center">
                  <div class="flex-shrink-0">
                    <div class="w-8 h-8 bg-blue-500 rounded-md flex items-center justify-center">
                      <span class="text-white text-sm font-bold">#</span>
                    </div>
                  </div>
                  <div class="ml-5 w-0 flex-1">
                    <dl>
                      <dt class="text-sm font-medium text-gray-500 truncate">Pedidos</dt>
                      <dd class="text-lg font-medium text-gray-900">{{ weeklyData.total_pedidos }}</dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>

            <div class="bg-white overflow-hidden shadow rounded-lg">
              <div class="p-5">
                <div class="flex items-center">
                  <div class="flex-shrink-0">
                    <div class="w-8 h-8 bg-green-500 rounded-md flex items-center justify-center">
                      <span class="text-white text-sm font-bold">📈</span>
                    </div>
                  </div>
                  <div class="ml-5 w-0 flex-1">
                    <dl>
                      <dt class="text-sm font-medium text-gray-500 truncate">Ingresos</dt>
                      <dd class="text-lg font-medium text-gray-900">${{ weeklyData.ingresos.total.toFixed(2) }}</dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>

            <div class="bg-white overflow-hidden shadow rounded-lg">
              <div class="p-5">
                <div class="flex items-center">
                  <div class="flex-shrink-0">
                    <div class="w-8 h-8 bg-red-500 rounded-md flex items-center justify-center">
                      <span class="text-white text-sm font-bold">📉</span>
                    </div>
                  </div>
                  <div class="ml-5 w-0 flex-1">
                    <dl>
                      <dt class="text-sm font-medium text-gray-500 truncate">Gastos</dt>
                      <dd class="text-lg font-medium text-gray-900">${{ weeklyData.gastos.total.toFixed(2) }}</dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>

            <div class="bg-white overflow-hidden shadow rounded-lg">
              <div class="p-5">
                <div class="flex items-center">
                  <div class="flex-shrink-0">
                    <div class="w-8 h-8 bg-yellow-500 rounded-md flex items-center justify-center">
                      <span class="text-white text-sm font-bold">💰</span>
                    </div>
                  </div>
                  <div class="ml-5 w-0 flex-1">
                    <dl>
                      <dt class="text-sm font-medium text-gray-500 truncate">Utilidad</dt>
                      <dd class="text-lg font-medium text-gray-900">${{ weeklyData.utilidad_bruta.toFixed(2) }}</dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>

            <div class="bg-white overflow-hidden shadow rounded-lg">
              <div class="p-5">
                <div class="flex items-center">
                  <div class="flex-shrink-0">
                    <div class="w-8 h-8 bg-indigo-500 rounded-md flex items-center justify-center">
                      <span class="text-white text-sm font-bold">📊</span>
                    </div>
                  </div>
                  <div class="ml-5 w-0 flex-1">
                    <dl>
                      <dt class="text-sm font-medium text-gray-500 truncate">Promedio/Día</dt>
                      <dd class="text-lg font-medium text-gray-900">${{ (weeklyData.ingresos.total / 7).toFixed(2) }}</dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Ventas por día -->
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div class="bg-white shadow rounded-lg">
              <div class="px-4 py-5 sm:p-6">
                <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">Ventas por Día</h3>
                <div class="space-y-3">
                  <div 
                    v-for="dia in weeklyData.ventas_por_dia" 
                    :key="dia.fecha"
                    class="flex justify-between items-center py-2 px-3 bg-gray-50 rounded-md"
                  >
                    <span class="font-medium text-gray-900">{{ formatDate(dia.fecha) }}</span>
                    <div class="text-sm text-gray-600">
                      <span class="font-medium">${{ dia.total.toFixed(2) }}</span>
                      <span class="ml-2">({{ dia.pedidos }} pedidos)</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="bg-white shadow rounded-lg">
              <div class="px-4 py-5 sm:p-6">
                <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">Top 10 Productos</h3>
                <div class="space-y-3">
                  <div 
                    v-for="(producto, index) in weeklyData.productos_mas_vendidos" 
                    :key="index"
                    class="flex justify-between items-center py-2 px-3 bg-gray-50 rounded-md"
                  >
                    <span class="font-medium text-gray-900">{{ producto.nombre }}</span>
                    <span class="text-sm text-gray-600">{{ producto.cantidad }} unidades</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Tab: Gestión de Gastos -->
      <div v-if="activeTab === 'gastos'">
        <div class="mb-6">
          <div class="flex justify-between items-center">
            <h2 class="text-xl font-semibold text-gray-900">Gestión de Gastos</h2>
            <button
              @click="showAddGastoModal = true"
              class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
            >
              Agregar Gasto
            </button>
          </div>
        </div>

        <!-- Lista de gastos recientes -->
        <div class="bg-white shadow rounded-lg">
          <div class="px-4 py-5 sm:p-6">
            <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">Gastos Recientes</h3>
            <div v-if="gastosList.length > 0">
              <div class="space-y-3">
                <div 
                  v-for="gasto in gastosList" 
                  :key="gasto.id"
                  class="flex justify-between items-center py-3 px-4 border border-gray-200 rounded-md"
                >
                  <div>
                    <p class="font-medium text-gray-900">{{ gasto.descripcion }}</p>
                    <p class="text-sm text-gray-500">{{ gasto.categoria }} - {{ formatDateTime(gasto.fecha_gasto) }}</p>
                  </div>
                  <span class="font-medium text-red-600">${{ typeof gasto.monto === 'string' ? parseFloat(gasto.monto).toFixed(2) : gasto.monto.toFixed(2) }}</span>
                </div>
              </div>
            </div>
            <div v-else class="text-gray-500 text-center py-4">
              No hay gastos registrados
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal para agregar gasto -->
    <div v-if="showAddGastoModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg shadow-xl p-6 w-96">
        <h3 class="text-lg font-medium text-gray-900 mb-4">Agregar Nuevo Gasto</h3>
        
        <form @submit.prevent="addGasto">
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Descripción</label>
              <input
                v-model="newGasto.descripcion"
                type="text"
                required
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Ej: Compra de ingredientes"
              >
            </div>
            
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Monto</label>
              <input
                v-model="newGasto.monto"
                type="number"
                step="0.01"
                min="0"
                required
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="0.00"
              >
            </div>
            
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Categoría</label>
              <select
                v-model="newGasto.categoria"
                required
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Seleccionar categoría</option>
                <option value="directos">Gastos Directos</option>
                <option value="indirectos">Gastos Indirectos</option>
                <option value="nomina">Nómina</option>
              </select>
            </div>
          </div>
          
          <div class="flex justify-end space-x-3 mt-6">
            <button
              type="button"
              @click="showAddGastoModal = false"
              class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-200 hover:bg-gray-300 rounded-md"
            >
              Cancelar
            </button>
            <button
              type="submit"
              :disabled="addingGasto"
              class="px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded-md disabled:opacity-50"
            >
              {{ addingGasto ? 'Guardando...' : 'Guardar' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Loading overlay -->
    <div v-if="loadingDashboard && !dashboardData" class="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center z-40">
      <div class="bg-white rounded-lg p-6">
        <div class="flex items-center space-x-3">
          <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
          <span class="text-gray-700">Cargando dashboard...</span>
        </div>
      </div>
    </div>

    <!-- Error message -->
    <div v-if="error" class="fixed bottom-4 right-4 bg-red-500 text-white px-6 py-3 rounded-lg shadow-lg z-50">
      <div class="flex items-center justify-between">
        <span>{{ error }}</span>
        <button @click="error = ''" class="ml-3 text-white hover:text-gray-200">
          ✕
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import api from '@/api/client'
import AppHeader from '@/components/AppHeader.vue'

interface DashboardData {
  fecha: string
  total_pedidos: number
  ingresos: {
    efectivo: number
    tarjeta: number
    transferencia: number
    total: number
  }
  productos_mas_vendidos: Array<{
    nombre: string
    cantidad: number
  }>
}

interface WeeklyData {
  periodo: {
    inicio: string
    fin: string
    descripcion: string
  }
  total_pedidos: number
  ingresos: {
    efectivo: number
    tarjeta: number
    transferencia: number
    total: number
  }
  gastos: {
    total: number
  }
  utilidad_bruta: number
  productos_mas_vendidos: Array<{
    nombre: string
    cantidad: number
  }>
  ventas_por_dia: Array<{
    fecha: string
    total: number
    pedidos: number
  }>
}

interface Gasto {
  id: number
  descripcion: string
  monto: number
  categoria: string
  fecha_gasto: string
}

const router = useRouter()
const auth = useAuthStore()

// Estado
const activeTab = ref('dashboard')
const loadingDashboard = ref(false)
const loadingWeekly = ref(false)
const addingGasto = ref(false)
const error = ref('')

const dashboardData = ref<DashboardData | null>(null)
const weeklyData = ref<WeeklyData | null>(null)
const gastosList = ref<Gasto[]>([])

const selectedWeekDate = ref(new Date().toISOString().split('T')[0])
const showAddGastoModal = ref(false)

const newGasto = ref({
  descripcion: '',
  monto: 0,
  categoria: ''
})

// Configuración de tabs
const tabs = [
  { id: 'dashboard', name: 'Dashboard' },
  { id: 'reportes', name: 'Reportes Semanales' },
  { id: 'gastos', name: 'Gestión de Gastos' }
]

// Métodos
const handleLogout = () => {
  auth.logout()
  router.push({ name: 'login' })
}

const refreshDashboard = async () => {
  loadingDashboard.value = true
  error.value = ''
  
  try {
    const response = await api.get('/admin/dashboard')
    dashboardData.value = response.data
  } catch (err: any) {
    error.value = err?.response?.data?.detail || 'Error al cargar dashboard'
    console.error('Error cargando dashboard:', err)
  } finally {
    loadingDashboard.value = false
  }
}

const loadWeeklyReport = async () => {
  if (!selectedWeekDate.value) return
  
  loadingWeekly.value = true
  error.value = ''
  
  try {
    const response = await api.get(`/admin/reportes/semanal?fecha=${selectedWeekDate.value}`)
    weeklyData.value = response.data
  } catch (err: any) {
    error.value = err?.response?.data?.detail || 'Error al cargar reporte semanal'
    console.error('Error cargando reporte semanal:', err)
  } finally {
    loadingWeekly.value = false
  }
}

const loadGastosList = async () => {
  try {
    const response = await api.get('/gastos/')
    // Normalizar los datos para asegurar que monto sea number
    gastosList.value = response.data.slice(0, 10).map((gasto: any) => ({
      ...gasto,
      monto: typeof gasto.monto === 'string' ? parseFloat(gasto.monto) : gasto.monto
    }))
  } catch (err: any) {
    console.error('Error cargando gastos:', err)
    error.value = 'Error al cargar lista de gastos'
  }
}

const addGasto = async () => {
  if (!newGasto.value.descripcion || !newGasto.value.monto || !newGasto.value.categoria) {
    error.value = 'Por favor completa todos los campos'
    return
  }

  addingGasto.value = true
  error.value = ''

  try {
    const gastoData = {
      ...newGasto.value,
      sucursal_id: auth.user?.sucursal_id
    }

    await api.post('/gastos/', gastoData)
    
    // Limpiar formulario
    newGasto.value = { descripcion: '', monto: 0, categoria: '' }
    showAddGastoModal.value = false
    
    // Recargar lista de gastos
    await loadGastosList()
    
    error.value = ''
  } catch (err: any) {
    error.value = err?.response?.data?.detail || 'Error al guardar gasto'
    console.error('Error agregando gasto:', err)
  } finally {
    addingGasto.value = false
  }
}

// Utilidades de formateo
const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  return date.toLocaleDateString('es-ES', {
    weekday: 'short',
    day: 'numeric',
    month: 'short'
  })
}

const formatDateTime = (dateStr: string) => {
  const date = new Date(dateStr)
  return date.toLocaleDateString('es-ES', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// Cargar datos iniciales
onMounted(async () => {
  await Promise.all([
    refreshDashboard(),
    loadGastosList()
  ])
})
</script>