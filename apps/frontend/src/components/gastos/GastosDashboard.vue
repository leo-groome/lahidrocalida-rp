<template>
  <div class="gastos-dashboard space-y-10 animate-in fade-in slide-in-from-bottom-5 duration-700">
    <!-- Header & Date Controls -->
    <div class="flex flex-col lg:flex-row lg:items-end justify-between gap-8">
      <div class="space-y-1">
        <h2 class="text-xs font-black tracking-[0.3em] text-slate-400 uppercase">Analíticas</h2>
        <h1 class="text-5xl font-black tracking-tight text-slate-900 flex items-center gap-3">
          PANEL <span class="text-red-500">CONTROL</span>
        </h1>
      </div>

      <div class="flex flex-wrap items-center gap-3">
        <!-- Modern Date Picker Module -->
        <div class="bg-white border-2 border-slate-100 rounded-[1.75rem] p-1.5 flex items-center shadow-sm">
          <div class="flex items-center px-4 gap-3">
            <Calendar class="h-4 w-4 text-slate-400" />
            <div class="flex flex-col">
              <span class="text-[9px] font-black text-slate-400 uppercase tracking-tighter">Desde</span>
              <input 
                type="date" 
                v-model="dates.start"
                class="bg-transparent border-none p-0 text-xs font-black text-slate-700 focus:ring-0 w-24 uppercase"
              >
            </div>
          </div>
          <div class="w-px h-8 bg-slate-100 mx-1"></div>
          <div class="flex items-center px-4 gap-3">
            <div class="flex flex-col">
              <span class="text-[9px] font-black text-slate-400 uppercase tracking-tighter">Hasta</span>
              <input 
                type="date" 
                v-model="dates.end"
                class="bg-transparent border-none p-0 text-xs font-black text-slate-700 focus:ring-0 w-24 uppercase"
              >
            </div>
          </div>
          <button 
            @click="loadDashboard" 
            :disabled="loading"
            class="bg-slate-900 text-white h-[48px] px-6 rounded-2xl text-xs font-black uppercase tracking-widest hover:bg-slate-800 disabled:opacity-50 transition-all ml-2 shadow-lg shadow-slate-200"
          >
             <span v-if="!loading">Actualizar</span>
             <Loader2 v-else class="w-4 h-4 animate-spin" />
          </button>
        </div>
      </div>
    </div>

    <!-- Main Content States -->
    <div v-if="loading && !stats" class="h-[500px] flex flex-col items-center justify-center bg-white rounded-[3rem] border-2 border-slate-100 p-12">
      <div class="relative w-20 h-20 mb-6">
        <div class="absolute inset-0 border-8 border-slate-50 rounded-full"></div>
        <div class="absolute inset-0 border-8 border-indigo-600 rounded-full border-t-transparent animate-spin"></div>
      </div>
      <p class="text-slate-400 font-black text-xs uppercase tracking-[0.3em] animate-pulse">Procesando métricas financieras...</p>
    </div>

    <div v-else-if="!stats && !loading" class="h-[500px] flex flex-col items-center justify-center text-slate-400 bg-white rounded-[3rem] border-2 border-dashed border-slate-200 p-12">
      <div class="w-24 h-24 rounded-full bg-slate-50 flex items-center justify-center mb-6">
        <SearchX class="h-10 w-10 text-slate-300" />
      </div>
      <h3 class="text-xl font-black text-slate-900 mb-2">Sin datos de auditoría</h3>
      <p class="text-slate-500 max-w-sm text-center mb-8">No se encontraron movimientos financieros registrados en el periodo solicitado.</p>
      <button @click="loadDashboard" class="px-8 py-3 bg-indigo-600 text-white rounded-2xl text-xs font-black uppercase tracking-widest hover:bg-indigo-700 transition-all shadow-xl shadow-indigo-100">
        Intentar de nuevo
      </button>
    </div>

    <!-- Dashboard Grid -->
    <div v-else-if="stats" class="space-y-10 animate-in fade-in slide-in-from-bottom-6 duration-1000">
      <!-- High Impact KPIs -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <!-- KPI 1: Inversion Total -->
        <div class="group relative bg-white p-8 rounded-[2.5rem] border border-slate-100 shadow-sm hover:shadow-2xl hover:shadow-red-500/10 hover:-translate-y-1 transition-all duration-500 overflow-hidden">
          <div class="absolute top-0 right-0 w-32 h-32 bg-red-50/50 rounded-full -mr-16 -mt-16 group-hover:scale-110 transition-transform duration-700"></div>
          <div class="relative z-10 flex flex-col h-full justify-between gap-8">
            <div class="w-14 h-14 rounded-2xl bg-red-500 text-white flex items-center justify-center shadow-lg shadow-red-100 transform group-hover:rotate-6 transition-transform">
              <DollarSign class="h-7 w-7" />
            </div>
            <div class="space-y-1">
              <p class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Egresos Totales</p>
              <h3 class="text-4xl font-black text-slate-900 tracking-tighter leading-none">
                ${{ formatCurrency(stats.total_gastado) }}
              </h3>
            </div>
          </div>
        </div>

        <!-- KPI 2: Promedio -->
        <div class="group relative bg-white p-8 rounded-[2.5rem] border border-slate-100 shadow-sm hover:shadow-2xl hover:shadow-indigo-500/10 hover:-translate-y-1 transition-all duration-500 overflow-hidden">
          <div class="absolute top-0 right-0 w-32 h-32 bg-indigo-50/50 rounded-full -mr-16 -mt-16 group-hover:scale-110 transition-transform duration-700"></div>
          <div class="relative z-10 flex flex-col h-full justify-between gap-8">
            <div class="w-14 h-14 rounded-2xl bg-indigo-600 text-white flex items-center justify-center shadow-lg shadow-indigo-100 transform group-hover:rotate-6 transition-transform">
              <Clock class="h-7 w-7" />
            </div>
            <div class="space-y-1">
              <p class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Ritmo Diario</p>
              <h3 class="text-4xl font-black text-slate-900 tracking-tighter leading-none">
                ${{ formatCurrency(stats.gasto_promedio_diario) }}
              </h3>
            </div>
          </div>
        </div>

        <!-- KPI 3: Principal Socio -->
        <div class="group relative bg-white p-8 rounded-[2.5rem] border border-slate-100 shadow-sm hover:shadow-2xl hover:shadow-emerald-500/10 hover:-translate-y-1 transition-all duration-500 overflow-hidden">
          <div class="absolute top-0 right-0 w-32 h-32 bg-emerald-50/50 rounded-full -mr-16 -mt-16 group-hover:scale-110 transition-transform duration-700"></div>
          <div class="relative z-10 flex flex-col h-full justify-between gap-8">
            <div class="w-14 h-14 rounded-2xl bg-emerald-600 text-white flex items-center justify-center shadow-lg shadow-emerald-100 transform group-hover:rotate-6 transition-transform">
              <Trophy class="h-7 w-7" />
            </div>
            <div class="space-y-1 overflow-hidden">
              <p class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Socio Estratégico</p>
              <h3 class="text-xl font-black text-slate-900 tracking-tight truncate uppercase leading-tight" :title="stats.top_proveedor?.nombre">
                {{ stats.top_proveedor?.nombre || 'N/A' }}
              </h3>
              <p class="text-xs font-black text-emerald-600" v-if="stats.top_proveedor">
                Facturado: ${{ formatCurrency(stats.top_proveedor.total) }}
              </p>
            </div>
          </div>
        </div>

        <!-- KPI 4: Categoria Principal -->
        <div class="group relative bg-white p-8 rounded-[2.5rem] border border-slate-100 shadow-sm hover:shadow-2xl hover:shadow-amber-500/10 hover:-translate-y-1 transition-all duration-500 overflow-hidden">
          <div class="absolute top-0 right-0 w-32 h-32 bg-amber-50/50 rounded-full -mr-16 -mt-16 group-hover:scale-110 transition-transform duration-700"></div>
          <div class="relative z-10 flex flex-col h-full justify-between gap-8">
            <div class="w-14 h-14 rounded-2xl bg-amber-500 text-white flex items-center justify-center shadow-lg shadow-amber-100 transform group-hover:rotate-6 transition-transform">
              <Tag class="h-7 w-7" />
            </div>
            <div class="space-y-1 overflow-hidden">
              <p class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Fuga Principal</p>
              <h3 class="text-xl font-black text-slate-900 tracking-tight truncate uppercase leading-tight">
                {{ topCategory?.categoria || 'Sin Datos' }}
              </h3>
              <p class="text-xs font-black text-amber-600" v-if="topCategory">
                Concentración: ${{ formatCurrency(topCategory.total) }}
              </p>
            </div>
          </div>
        </div>
      </div>

      <!-- Detail Visualizations Layer -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <!-- Main Line Chart -->
        <div class="lg:col-span-8 bg-white p-10 rounded-[3rem] border border-slate-100 shadow-sm hover:shadow-xl transition-shadow duration-500 relative group overflow-hidden">
          <div class="flex items-center justify-between mb-10 relative z-10">
            <div class="space-y-1">
              <h3 class="text-2xl font-black text-slate-900 tracking-tight">Tendencia de Egresos</h3>
              <p class="text-xs font-black text-slate-400 uppercase tracking-tighter">Cronología detallada de gastos operativos</p>
            </div>
            <div class="flex items-center gap-2 px-4 py-2 bg-slate-50 rounded-2xl">
              <TrendingDown class="w-4 h-4 text-red-500" />
              <span class="text-[10px] font-black text-slate-600 uppercase tracking-widest">Análisis Temporal</span>
            </div>
          </div>
          
          <div class="h-[450px] w-full relative z-10">
            <Line :data="lineChartData" :options="lineChartOptions" />
          </div>
          
          <!-- Background accent -->
          <div class="absolute -bottom-24 -left-24 w-64 h-64 bg-slate-50 rounded-full opacity-50 group-hover:scale-110 transition-transform duration-1000"></div>
        </div>

        <!-- Distribution & Ranking -->
        <div class="lg:col-span-4 space-y-8">
          <!-- Circular Distribution -->
          <div class="bg-indigo-900 p-10 rounded-[3rem] text-white shadow-2xl relative overflow-hidden group h-[400px] flex flex-col">
            <div class="relative z-10 mb-6">
              <p class="text-[10px] font-black text-indigo-400 uppercase tracking-[0.2em] mb-1">Distribución</p>
              <h3 class="text-xl font-black tracking-tight">Mix por Categoría</h3>
            </div>
            
            <div class="flex-1 relative min-h-0 flex items-center justify-center">
              <Doughnut v-if="doughnutData" :data="doughnutData" :options="doughnutOptions" />
              <div v-else class="text-indigo-700 font-extrabold text-sm uppercase">Sin métricas</div>
            </div>

            <!-- Absolute decorative patterns -->
            <div class="absolute top-0 right-0 p-8">
              <PieChart class="w-24 h-24 text-indigo-800 rotate-12" />
            </div>
          </div>

          <!-- Top Spending List -->
          <div class="bg-white p-10 rounded-[3rem] border border-slate-100 shadow-sm flex-1 min-h-[300px]">
             <h3 class="text-sm font-black text-slate-900 uppercase tracking-widest mb-8 flex items-center gap-3">
               <ListStart class="w-4 h-4 text-indigo-600" /> Top Categorías
             </h3>
             
             <div v-if="stats?.por_categoria" class="space-y-6">
               <div 
                 v-for="(cat, idx) in sortedCategories.slice(0, 5)" 
                 :key="cat.categoria" 
                 class="flex items-center justify-between group cursor-default"
               >
                 <div class="flex items-center gap-4">
                   <div 
                     class="w-10 h-10 rounded-xl flex items-center justify-center text-xs font-black shadow-sm group-hover:scale-110 transition-transform"
                     :style="{ 
                       backgroundColor: getCategoryColor(idx) + '15', 
                       color: getCategoryColor(idx) 
                     }"
                   >
                     {{ idx + 1 }}
                   </div>
                   <div class="flex flex-col">
                     <span class="text-xs font-black text-slate-700 uppercase group-hover:text-indigo-600 transition-colors">{{ cat.categoria }}</span>
                     <span class="text-[10px] font-bold text-slate-400">{{ getPercentage(cat.total) }}% del total</span>
                   </div>
                 </div>
                 <span class="text-sm font-black text-slate-900">${{ formatCurrency(cat.total) }}</span>
               </div>
             </div>
             <div v-else class="h-40 flex items-center justify-center text-slate-300 font-black text-[10px] uppercase tracking-widest">
               No hay registros
             </div>
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
  TrendingDown, Calendar, SearchX, DollarSign, Clock, 
  Trophy, Tag, Loader2, PieChart, ListStart
} from 'lucide-vue-next'
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

// Interfaces for better type safety and preventing lint errors
interface GastoAnalytics {
  total_gastado: number;
  gasto_promedio_diario: number;
  top_proveedor: { nombre: string; total: number } | null;
  por_categoria: Array<{ categoria: string; total: number }>;
  timeline: Array<{ fecha: string; total: number }>;
}

const loading = ref(false)
const stats = ref<GastoAnalytics | null>(null)

// Fechas por defecto: mes actual
const now = new Date()
const firstDay = new Date(now.getFullYear(), now.getMonth(), 1)
const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0)

const dates = ref({
  start: firstDay.toISOString().split('T')[0],
  end: lastDay.toISOString().split('T')[0]
})

const formatCurrency = (val: number | string) => {
  const num = typeof val === 'string' ? parseFloat(val) : val
  if (isNaN(num)) return '0.00'
  return num.toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
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
  return [...stats.value.por_categoria].sort((a, b) => b.total - a.total)[0]
})

const sortedCategories = computed(() => {
  if (!stats.value?.por_categoria) return []
  return [...stats.value.por_categoria].sort((a, b) => b.total - a.total)
})

const getPercentage = (amount: number) => {
  if (!stats.value?.total_gastado) return 0
  return ((amount / stats.value.total_gastado) * 100).toFixed(1)
}

const getCategoryColor = (idx: number) => {
  const colors = ['#6366F1', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899']
  return colors[idx % colors.length]
}

// Line Chart Visualization
const lineChartData = computed(() => {
  if (!stats.value) return { labels: [], datasets: [] }
  const timeline = stats.value.timeline || []
  
  return {
    labels: timeline.map((t) => {
      const date = parseSafeDate(t.fecha)
      return date ? date.toLocaleDateString('es-MX', { timeZone: 'America/Mexico_City', day: 'numeric', month: 'short' }).toUpperCase() : ''
    }),
    datasets: [{
      label: 'Gasto Diario',
      data: timeline.map((t) => t.total),
      borderColor: '#f43f5e', // Rose 500
      backgroundColor: (context: any) => {
        const chart = context.chart
        const { ctx, chartArea } = chart
        if (!chartArea) return null
        const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom)
        gradient.addColorStop(0, 'rgba(244, 63, 94, 0.2)')
        gradient.addColorStop(1, 'rgba(244, 63, 94, 0.0)')
        return gradient
      },
      fill: true,
      tension: 0.45,
      borderWidth: 5,
      pointRadius: 0,
      pointHoverRadius: 8,
      pointHoverBackgroundColor: '#f43f5e',
      pointHoverBorderColor: '#fff',
      pointHoverBorderWidth: 4
    }]
  }
})

const lineChartOptions: any = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    intersect: false,
    mode: 'index',
  },
  plugins: { 
    legend: { display: false },
    tooltip: {
      backgroundColor: '#0f172a',
      padding: 20,
      titleFont: { size: 10, weight: '900', family: 'Inter', textTransform: 'uppercase' },
      bodyFont: { size: 16, weight: '900', family: 'Inter' },
      cornerRadius: 16,
      displayColors: false,
      callbacks: {
        label: (context: any) => `$${Number(context.parsed.y).toLocaleString()}`
      }
    }
  },
  scales: { 
    y: { 
      beginAtZero: true,
      grid: { color: 'rgba(0,0,0,0.03)', drawTicks: false },
      border: { display: false },
      ticks: { 
        padding: 15,
        font: { family: 'Inter', weight: '800', size: 11 },
        color: '#94a3b8',
        callback: (value: any) => '$' + Number(value).toLocaleString()
      }
    },
    x: {
      grid: { display: false },
      border: { display: false },
      ticks: { 
        padding: 15,
        font: { family: 'Inter', weight: '800', size: 10 },
        color: '#cbd5e1'
      }
    }
  }
}

// Doughnut Chart Visualization
const doughnutData = computed(() => {
  if (!stats.value?.por_categoria?.length) return null
  
  const cats = stats.value.por_categoria
  return {
    labels: cats.map((c: any) => c.categoria),
    datasets: [{
      data: cats.map((c: any) => c.total),
      backgroundColor: [
        '#818CF8', '#34D399', '#FB923C', '#F87171', '#A78BFA', '#F472B6', '#818CF8', '#94A3B8'
      ],
      hoverOffset: 15,
      borderWidth: 0,
      spacing: 8,
      borderRadius: 12
    }]
  }
})

const doughnutOptions: any = {
  responsive: true,
  maintainAspectRatio: false,
  cutout: '80%',
  plugins: { 
    legend: { display: false },
    tooltip: {
      backgroundColor: '#fff',
      titleColor: '#0f172a',
      bodyColor: '#0f172a',
      padding: 16,
      cornerRadius: 16,
      titleFont: { weight: '900' },
      bodyFont: { weight: '900' },
      borderWidth: 1,
      borderColor: '#e2e8f0',
      callbacks: {
        label: (context: any) => ` ${context.label}: $${Number(context.parsed).toLocaleString()}`
      }
    }
  }
}

onMounted(() => {
  loadDashboard()
})
</script>

<style scoped>
.animate-in {
  animation: slideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(30px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Hide scrollbar for top category list but keep functional */
.top-categories-list::-webkit-scrollbar {
  display: none;
}
</style>

