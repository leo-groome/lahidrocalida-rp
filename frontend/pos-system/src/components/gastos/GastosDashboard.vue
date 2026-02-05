<template>
  <div class="gastos-dashboard">
    <div class="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Dashboard de Gastos</h1>
        <p class="text-gray-600 mt-1">Resumen ejecutivo de gastos del negocio</p>
      </div>
      
      <div class="flex items-center gap-2">
         <button 
          @click="$emit('new-gasto')" 
          class="bg-green-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-green-700 font-medium shadow-sm flex items-center"
        >
          <span class="mr-1 text-lg">+</span> Nuevo Gasto
        </button>

         <!-- Controles de fecha -->
         <div class="flex items-center space-x-2 bg-white p-2 rounded-lg shadow-sm border border-gray-200">
            <input 
               type="date" 
               v-model="dates.start"
               class="border-gray-300 rounded-md text-sm focus:ring-blue-500 focus:border-blue-500 w-32"
            >
            <span class="text-gray-400">→</span>
            <input 
               type="date" 
               v-model="dates.end"
               class="border-gray-300 rounded-md text-sm focus:ring-blue-500 focus:border-blue-500 w-32"
            >
            <button 
               @click="loadDashboard" 
               :disabled="loading"
               class="bg-blue-600 text-white px-3 py-1.5 rounded-md text-sm hover:bg-blue-700 disabled:opacity-50"
            >
               {{ loading ? '...' : 'Filtrar' }}
            </button>
         </div>
      </div>
    </div>
    
    <div v-if="loading && !stats" class="h-64 flex items-center justify-center">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
    </div>

    <div v-else-if="!stats && !loading" class="h-64 flex flex-col items-center justify-center text-gray-500">
      <p class="mb-2">No hay datos disponibles para el rango seleccionado.</p>
      <button @click="loadDashboard" class="text-blue-600 hover:underline">Reintentar</button>
    </div>

    <div v-else-if="stats">
      <!-- KPIs principales -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <!-- Total Gastado -->
        <div class="bg-white rounded-lg shadow p-6 border-l-4 border-blue-500">
          <div class="flex items-center">
            <div class="flex-shrink-0 bg-blue-100 p-3 rounded-full">
              <span class="text-xl">💰</span>
            </div>
            <div class="ml-4">
              <div class="text-sm text-gray-500">Total Gastado</div>
              <div class="text-2xl font-bold text-gray-900">${{ formatCurrency(stats.total_gastado) }}</div>
            </div>
          </div>
        </div>
        
        <!-- Promedio Diario -->
        <div class="bg-white rounded-lg shadow p-6 border-l-4 border-purple-500">
          <div class="flex items-center">
            <div class="flex-shrink-0 bg-purple-100 p-3 rounded-full">
              <span class="text-xl">📅</span>
            </div>
            <div class="ml-4">
              <div class="text-sm text-gray-500">Promedio Diario</div>
              <div class="text-2xl font-bold text-gray-900">${{ formatCurrency(stats.gasto_promedio_diario) }}</div>
            </div>
          </div>
        </div>
        
        <!-- Top Proveedor -->
        <div class="bg-white rounded-lg shadow p-6 border-l-4 border-green-500">
          <div class="flex items-center">
            <div class="flex-shrink-0 bg-green-100 p-3 rounded-full">
              <span class="text-xl">🏆</span>
            </div>
            <div class="ml-4 overflow-hidden">
              <div class="text-sm text-gray-500">Top Proveedor</div>
              <div class="text-lg font-bold text-gray-900 truncate" :title="stats.top_proveedor?.nombre || 'N/A'">
                {{ stats.top_proveedor?.nombre || 'N/A' }}
              </div>
              <div class="text-xs text-green-700 font-medium" v-if="stats.top_proveedor">
                ${{ formatCurrency(stats.top_proveedor.total) }}
              </div>
            </div>
          </div>
        </div>
        
        <!-- Categoría Principal -->
        <div class="bg-white rounded-lg shadow p-6 border-l-4 border-yellow-500">
          <div class="flex items-center">
            <div class="flex-shrink-0 bg-yellow-100 p-3 rounded-full">
              <span class="text-xl">🏷️</span>
            </div>
            <div class="ml-4">
              <div class="text-sm text-gray-500">Categoría Principal</div>
              <div class="text-lg font-bold text-gray-900 truncate">
                 {{ topCategory?.categoria || 'N/A' }}
              </div>
              <div class="text-xs text-yellow-700 font-medium" v-if="topCategory">
                 ${{ formatCurrency(topCategory.total) }}
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Gráficos y visualizaciones -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <!-- Tendencia -->
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="text-lg font-medium text-gray-900 mb-4">Tendencia de Gastos</h3>
          <div class="h-80 w-full relative">
            <Line :data="lineChartData" :options="lineChartOptions" />
          </div>
        </div>
        
        <!-- Distribución -->
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="text-lg font-medium text-gray-900 mb-4">Distribución por Categoría</h3>
          <div class="h-80 w-full relative flex justify-center">
            <Doughnut v-if="doughnutData" :data="doughnutData" :options="doughnutOptions" />
            <div v-else class="text-gray-400 self-center">Sin datos para mostrar</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import api from '@/api/client'
import { parseSafeDate } from '@/utils/dateUtils'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  ArcElement
} from 'chart.js'
import { Line, Doughnut } from 'vue-chartjs'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  ArcElement
)

const loading = ref(false)
const stats = ref<any>(null)

// Fechas por defecto: mes actual
const now = new Date()
const firstDay = new Date(now.getFullYear(), now.getMonth(), 1)
const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0)

const dates = ref({
  start: firstDay.toISOString().split('T')[0],
  end: lastDay.toISOString().split('T')[0]
})

const formatCurrency = (val: number) => {
  return val.toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const loadDashboard = async () => {
  loading.value = true
  try {
    const { start, end } = dates.value
    const res = await api.get(`/gastos/analiticas/resumen?fecha_inicio=${start}&fecha_fin=${end}`)
    stats.value = res.data
  } catch (error) {
    console.error('Error loading dashboard', error)
  } finally {
    loading.value = false
  }
}

const topCategory = computed(() => {
  if (!stats.value?.por_categoria?.length) return null
  // Ordenar copia y tomar primero
  return [...stats.value.por_categoria].sort((a, b) => b.total - a.total)[0]
})

// Gráfico de Línea
const lineChartData = computed(() => {
  if (!stats.value) return { labels: [], datasets: [] }
  const timeline = stats.value.timeline || []
  
  return {
    labels: timeline.map((t: any) => {
      const date = parseSafeDate(t.fecha)
      return date ? date.toLocaleDateString(undefined, { day: 'numeric', month: 'short' }) : ''
    }),
    datasets: [{
      label: 'Gasto Diario',
      data: timeline.map((t: any) => t.total),
      borderColor: '#EF4444',
      backgroundColor: 'rgba(239, 68, 68, 0.1)',
      fill: true,
      tension: 0.3
    }]
  }
})

const lineChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: { y: { beginAtZero: true } }
}

// Gráfico Circular
const doughnutData = computed(() => {
  if (!stats.value?.por_categoria?.length) return null
  
  const cats = stats.value.por_categoria
  return {
    labels: cats.map((c: any) => c.categoria),
    datasets: [{
      data: cats.map((c: any) => c.total),
      backgroundColor: [
        '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#6366F1', '#64748B'
      ],
      borderWidth: 0
    }]
  }
})

const doughnutOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { position: 'right' as const } }
}

onMounted(() => {
  loadDashboard()
})
</script>
