<template>
  <div class="space-y-8 animate-in fade-in duration-500">
    <!-- Header with Filters -->
    <div class="flex flex-wrap items-end justify-between gap-6 bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
      <div class="space-y-1">
        <h2 class="text-2xl font-extrabold text-slate-900 tracking-tight">Visión General</h2>
        <p class="text-sm font-medium text-slate-500">Analiza el rendimiento del restaurante en tiempo real.</p>
      </div>
      
      <div class="flex flex-wrap items-center gap-4">
        <!-- Quick Range Select -->
        <div class="inline-flex p-1 bg-slate-100 rounded-xl border border-slate-200 shadow-inner">
          <button 
            v-for="range in dateRanges" 
            :key="range.id"
            @click="setAnalyticsRange(range.id)"
            :class="[
              'px-4 py-2 text-xs font-bold rounded-lg transition-all duration-200',
              selectedRangeId === range.id 
                ? 'bg-white text-blue-600 shadow-sm ring-1 ring-slate-200/50' 
                : 'text-slate-500 hover:text-slate-800'
            ]"
          >
            {{ range.label }}
          </button>
        </div>

        <!-- Payment Filter -->
        <div class="flex items-center space-x-3 bg-slate-50 border border-slate-200 rounded-xl px-4 py-2 hover:bg-white transition-colors">
          <label class="text-xs font-extrabold text-slate-400 uppercase tracking-widest">Pago:</label>
          <select 
            v-model="selectedPaymentMethodFilter" 
            @change="loadAnalytics" 
            class="bg-transparent text-sm font-semibold text-slate-700 focus:outline-none cursor-pointer"
          >
             <option value="todos">Todos los métodos</option>
             <option value="efectivo">Efectivo 💵</option>
             <option value="tarjeta">Tarjeta 💳</option>
             <option value="transferencia">Transferencia 📲</option>
          </select>
        </div>

        <!-- Manual Date inputs -->
        <div class="flex items-center space-x-2 bg-slate-50 border border-slate-200 rounded-xl p-1.5 transition-all focus-within:ring-2 focus-within:ring-blue-400/20 focus-within:bg-white">
          <input type="date" v-model="analyticsDates.start" class="bg-transparent text-xs font-bold text-slate-600 focus:outline-none p-1" />
          <ArrowRight class="h-3 w-3 text-slate-300" />
          <input type="date" v-model="analyticsDates.end" class="bg-transparent text-xs font-bold text-slate-600 focus:outline-none p-1" />
          <button 
            @click="loadAnalytics"
            :disabled="loadingAnalytics"
            class="ml-2 h-8 w-8 flex items-center justify-center bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-all disabled:opacity-50 hover:scale-105 active:scale-95 shadow-lg shadow-blue-600/20"
          >
            <RefreshCw class="h-4 w-4" :class="{ 'animate-spin': loadingAnalytics }" />
          </button>
        </div>
      </div>
    </div>

    <!-- Main KPIs Grid -->
    <div v-if="analyticsData" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
      <AdminStatCard 
        label="Ventas Totales"
        :value="'$' + formatCurrency(analyticsData.resumen.total_ventas)"
        :icon="TrendingUp"
        iconColor="text-emerald-600"
        iconBg="bg-emerald-50 border border-emerald-100"
        :trend="12" 
        subtext="Incluye propinas e impuestos"
      />
      <AdminStatCard 
        label="Gastos Totales"
        :value="'$' + formatCurrency(analyticsData.resumen.total_gastos)"
        :icon="TrendingDown"
        iconColor="text-red-600"
        iconBg="bg-red-50 border border-red-100"
        subtext="Mercancía y nómina"
      />
      <AdminStatCard 
        label="Utilidad Neta"
        :value="'$' + formatCurrency(analyticsData.resumen.utilidad_neta)"
        :icon="PieChart"
        :iconColor="analyticsData.resumen.utilidad_neta >= 0 ? 'text-blue-600' : 'text-orange-600'"
        :iconBg="analyticsData.resumen.utilidad_neta >= 0 ? 'bg-blue-50 border border-blue-100' : 'bg-orange-50 border border-orange-100'"
        subtext="Saldo después de gastos"
      />
      <AdminStatCard 
        label="Ticket Promedio"
        :value="'$' + formatCurrency(analyticsData.resumen.ticket_promedio)"
        :icon="CreditCard"
        iconColor="text-purple-600"
        iconBg="bg-purple-50 border border-purple-100"
        subtext="Por cada orden"
      />
    </div>

    <!-- Main Trend Chart -->
    <div v-if="analyticsData" class="bg-white p-8 rounded-3xl shadow-sm border border-slate-100 relative overflow-hidden group">
      <div class="absolute top-0 left-0 w-2 h-full bg-blue-600"></div>
      <div class="flex items-center justify-between mb-8">
        <div>
          <h3 class="text-xl font-extrabold text-slate-800 tracking-tight mb-1">Tendencia de Flujo</h3>
          <p class="text-sm font-medium text-slate-400">Ingresos vs Egresos del periodo seleccionado</p>
        </div>
        <div class="flex items-center space-x-1 lg:space-x-4 bg-slate-50/50 p-1 rounded-xl border border-slate-100">
          <div class="flex items-center px-4 py-1.5 rounded-lg bg-white shadow-sm border border-slate-100">
            <div class="h-2 w-2 rounded-full bg-blue-600 mr-2"></div>
            <span class="text-xs font-bold text-slate-600">Ventas</span>
          </div>
          <div class="flex items-center px-4 py-1.5">
            <div class="h-2 w-2 rounded-full bg-red-500 mr-2"></div>
            <span class="text-xs font-bold text-slate-500">Gastos</span>
          </div>
        </div>
      </div>
      <div class="h-[400px] w-full">
         <Line :data="chartData" :options="chartOptions" />
      </div>
    </div>

    <!-- Advanced Analytics Rows -->
    <div v-if="loadingAdvanced" class="py-12 flex flex-col items-center gap-4">
        <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 ring-8 ring-blue-50/50"></div>
        <p class="text-xs font-bold text-slate-400 animate-pulse tracking-widest uppercase">Consultando datos avanzados...</p>
    </div>
    
    <div v-else-if="advancedAnalyticsData" class="space-y-8">
      <!-- Row 1: Sales by Hour and Categories -->
      <div class="grid grid-cols-12 gap-8">
        <!-- Sales by Hour Bar Chart -->
        <div class="col-span-12 lg:col-span-8 bg-white p-8 rounded-3xl shadow-sm border border-slate-100">
          <div class="flex items-center justify-between mb-8">
            <div class="flex-1">
               <h3 class="text-xl font-extrabold text-slate-800 tracking-tight mb-1">📊 Ingresos por Franja Horaria</h3>
               <p class="text-sm font-medium text-slate-400">Total acumulado por cada hora en el periodo seleccionado.</p>
            </div>
          </div>
          <div class="h-[300px] w-full">
            <Bar v-if="hourChartData" :data="hourChartData" :options="barOptions" />
          </div>
        </div>

        <!-- Categorías Chart -->
        <div class="col-span-12 lg:col-span-4 bg-white p-8 rounded-3xl shadow-sm border border-slate-100">
          <h3 class="text-xl font-extrabold text-slate-800 tracking-tight mb-1 text-center">Categorías</h3>
          <p class="text-xs font-medium text-slate-400 text-center mb-8 italic">Distribución de ingresos</p>
          <div class="h-64 flex justify-center relative">
             <Doughnut v-if="categoryChartData" :data="categoryChartData" :options="doughnutOptions" />
             <div v-else class="flex flex-col items-center justify-center text-slate-400 bg-slate-50/50 rounded-full w-full">
               <Slash class="h-8 w-8 mb-2 opacity-20" />
               <span class="text-[10px] font-bold uppercase tracking-widest">Sin datos</span>
             </div>
          </div>
        </div>
      </div>

      <!-- Row 2: Top Platillos and Channels/Payments -->
      <div class="grid grid-cols-12 gap-8">
        <!-- Top Platillos -->
        <div class="col-span-12 lg:col-span-8 bg-white p-8 rounded-3xl shadow-sm border border-slate-100">
           <!-- (Keep Top Platillos table header/content same as before) -->
          <div class="flex items-center justify-between mb-6">
            <div>
              <h3 class="text-xl font-extrabold text-slate-800 tracking-tight mb-1">⭐ Top Platillos</h3>
              <p class="text-sm font-medium text-slate-400">Los 10 más vendidos por volumen</p>
            </div>
          </div>
          
          <div class="overflow-hidden">
            <table class="min-w-full">
              <thead>
                <tr class="border-b border-slate-100">
                  <th class="pb-4 text-left text-[10px] font-extrabold text-slate-400 uppercase tracking-widest">Platillo</th>
                  <th class="pb-4 text-center text-[10px] font-extrabold text-slate-400 uppercase tracking-widest">Cant.</th>
                  <th class="pb-4 text-right text-[10px] font-extrabold text-slate-400 uppercase tracking-widest">Total Generado</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-50">
                <tr 
                  v-for="(item, index) in advancedAnalyticsData.top_platillos" 
                  :key="index"
                  class="group hover:bg-slate-50/50 transition-all cursor-default"
                >
                  <td class="py-4">
                    <div class="flex items-center space-x-3">
                      <span class="h-6 w-6 flex items-center justify-center font-black" 
                        :class="Number(index) < 3 ? 'text-blue-600 bg-blue-50 rounded-lg text-xs ring-4 ring-blue-50/50' : 'text-slate-300 text-[10px]'">
                        {{ Number(index) + 1 }}
                      </span>
                      <span class="text-sm font-extrabold text-slate-700 tracking-tight group-hover:text-blue-600 transition-colors">{{ item.nombre }}</span>
                    </div>
                  </td>
                  <td class="py-4 text-center">
                     <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold bg-slate-100 text-slate-600">
                       {{ item.cantidad }}
                     </span>
                  </td>
                  <td class="py-4 text-right">
                    <span class="text-sm font-black text-slate-900 tracking-tighter">${{ formatCurrency(item.total) }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Channels and Payments side column -->
        <div class="col-span-12 lg:col-span-4 space-y-8">
          <!-- Multi-Data Doughnut (Channels or Payments) -->
          <div class="bg-white p-8 rounded-3xl shadow-sm border border-slate-100">
            <div class="flex items-center justify-between mb-6">
               <h3 class="text-lg font-extrabold text-slate-800 tracking-tight">Canales y Pagos</h3>
               <div class="flex gap-1 bg-slate-100 p-1 rounded-lg">
                 <button @click="sideChartTab = 'channels'" :class="sideChartTab === 'channels' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-400'" class="px-2 py-1 text-[10px] font-bold rounded-md transition-all">Canal</button>
                 <button @click="sideChartTab = 'payments'" :class="sideChartTab === 'payments' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-400'" class="px-2 py-1 text-[10px] font-bold rounded-md transition-all">Pago</button>
               </div>
            </div>
            <div class="h-56 flex justify-center relative">
               <Doughnut v-if="sideChartTab === 'channels' && orderTypeChartData" :data="orderTypeChartData" :options="doughnutOptionsSmall" />
               <Doughnut v-else-if="sideChartTab === 'payments' && paymentMethodChartData" :data="paymentMethodChartData" :options="doughnutOptionsSmall" />
            </div>
          </div>

          <!-- Top Meseros -->
          <div class="bg-white p-8 rounded-3xl shadow-sm border border-slate-100">
            <h3 class="text-lg font-extrabold text-slate-800 tracking-tight mb-8">Personal (Fuerza de Venta)</h3>
            <div class="space-y-6">
              <div v-for="(m, idx) in advancedAnalyticsData.top_meseros" :key="idx" class="flex items-center justify-between group">
                <div class="flex items-center space-x-4">
                  <div class="h-9 w-9 rounded-xl bg-slate-100 flex items-center justify-center font-bold text-slate-500 group-hover:bg-blue-600 group-hover:text-white transition-all">{{ m.nombre.charAt(0) }}</div>
                  <div>
                    <p class="text-sm font-bold text-slate-700">{{ m.nombre }}</p>
                    <p class="text-[10px] font-medium text-slate-400 uppercase tracking-wider">{{ m.pedidos }} servicios</p>
                  </div>
                </div>
                <div class="text-sm font-black text-slate-900 tracking-tighter">${{ formatCurrency(m.total) }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Row 3: Operational Efficiency & Cancellation & Expense Types -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
         <!-- Efficiency card -->
         <div class="bg-white p-8 rounded-3xl shadow-sm border border-slate-100 flex flex-col items-center text-center">
            <div class="h-12 w-12 rounded-2xl bg-blue-50 flex items-center justify-center text-blue-600 mb-4 ring-8 ring-blue-50/50">
               <Clock class="h-6 w-6" />
            </div>
            <h4 class="text-sm font-bold text-slate-400 uppercase tracking-widest mb-1">Eficiencia Operativa</h4>
            <div class="text-3xl font-black text-slate-900 mb-1">{{ advancedAnalyticsData.eficiencia_operativa.avg_service_time_mins }} min</div>
            <p class="text-xs font-medium text-slate-400">Tiempo promedio de servicio completo</p>
         </div>

         <!-- Cancellation card -->
         <div class="bg-white p-8 rounded-3xl shadow-sm border border-slate-100 flex flex-col items-center text-center">
            <div class="h-12 w-12 rounded-2xl bg-orange-50 flex items-center justify-center text-orange-600 mb-4 ring-8 ring-orange-50/50">
               <AlertCircle class="h-6 w-6" />
            </div>
            <h4 class="text-sm font-bold text-slate-400 uppercase tracking-widest mb-1">Tasa de Cancelación</h4>
            <div class="text-3xl font-black text-slate-900 mb-1">{{ advancedAnalyticsData.metricas_cancelacion.tasa_cancelacion }}%</div>
            <p class="text-xs font-bold text-red-500" v-if="advancedAnalyticsData.metricas_cancelacion.total_cancelados > 0">
              {{ advancedAnalyticsData.metricas_cancelacion.total_cancelados }} pedidos perdidos
            </p>
            <p class="text-xs font-bold text-emerald-500" v-else>Operación sin fugas</p>
         </div>

         <!-- Detailed Expenses card (Doughnut) -->
         <div class="bg-white p-6 rounded-3xl shadow-sm border border-slate-100">
            <h4 class="text-center text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-4">Estructura de Gastos</h4>
            <div class="h-40 flex justify-center relative">
               <Doughnut v-if="expenseStructureChartData" :data="expenseStructureChartData" :options="doughnutOptionsSmall" />
               <div v-else class="flex flex-col items-center justify-center text-slate-400 bg-slate-50/50 rounded-full w-full">
                 <div class="flex items-center space-x-1 opacity-20">
                    <span class="w-1 h-1 rounded-full bg-slate-400"></span>
                    <span class="w-1 h-3 rounded-full bg-slate-400"></span>
                    <span class="w-1 h-1 rounded-full bg-slate-400"></span>
                 </div>
                 <span class="mt-2 text-[8px] font-black uppercase tracking-widest opacity-40">No hay gastos en el periodo</span>
               </div>
            </div>
         </div>
      </div>

      <!-- Row 4: Predictive Analytics (Feature 7) -->
      <div v-if="advancedAnalyticsData.proyeccion_ia" class="bg-white p-8 rounded-3xl shadow-sm border border-slate-100 text-slate-900 relative overflow-hidden transition-all duration-300 hover:shadow-xl hover:shadow-blue-500/5">
         <div class="absolute top-0 right-0 p-8 opacity-5">
            <Sparkles class="h-32 w-32 text-blue-600" />
         </div>
         
         <div class="flex flex-col lg:flex-row gap-12 relative z-10 text-slate-900">
            <div class="lg:w-1/3 flex flex-col justify-between">
               <div>
                  <div class="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-blue-50 text-blue-600 text-[10px] font-black uppercase tracking-widest mb-6 border border-blue-100">
                     <Sparkles class="h-3 w-3" />
                     <span>Analítica Predictiva La Hidrocalida</span>
                  </div>
                  <h3 class="text-3xl font-black mb-2 leading-tight text-slate-800">Proyección Próxima Semana</h3>
                  <p class="text-slate-400 text-sm font-medium mb-8">Tendencias de comportamiento (Martes-Domingo).</p>
               </div>
               
               <div class="space-y-6">
                  <div>
                     <p class="text-slate-400 text-[10px] font-bold uppercase tracking-widest mb-1">Ingreso Estimado</p>
                     <p class="text-4xl font-black tracking-tighter text-blue-600">${{ formatCurrency(advancedAnalyticsData.proyeccion_ia.total_semana_esperado) }}</p>
                  </div>
                  
                  <div class="flex items-center space-x-3 p-4 rounded-2xl bg-blue-50/50 border border-blue-100">
                     <div :class="[
                        'h-3 w-3 rounded-full',
                        advancedAnalyticsData.proyeccion_ia.confianza.includes('Baja') ? 'bg-orange-500 shadow-lg shadow-orange-500/50' : 'bg-emerald-500 shadow-lg shadow-emerald-500/50'
                     ]"></div>
                     <div>
                        <p class="text-[10px] font-black uppercase tracking-widest text-slate-500">Nivel de Confianza</p>
                        <p class="text-xs font-bold">{{ advancedAnalyticsData.proyeccion_ia.confianza }}</p>
                     </div>
                  </div>
               </div>
            </div>
            
            <div class="lg:w-2/3 h-[300px]">
               <Line v-if="projectionChartData" :data="projectionChartData" :options="projectionOptions" />
            </div>
         </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import api from '@/api/client'
import { parseSafeDate } from '@/utils/dateUtils'
import AdminStatCard from '@/components/admin/AdminStatCard.vue'
import { 
  TrendingUp, 
  TrendingDown, 
  PieChart, 
  CreditCard, 
  ArrowRight, 
  RefreshCw,
  Clock,
  AlertCircle,
  TrendingUp as ArrowUp,
  TrendingDown as ArrowDown,
  Trash2 as Slash,
  Sparkles,
  Info
} from 'lucide-vue-next'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'
import { Line, Doughnut, Bar } from 'vue-chartjs'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

const loadingAnalytics = ref(false)
const loadingAdvanced = ref(false)
const analyticsData = ref<any>(null)
const advancedAnalyticsData = ref<any>(null)
const sideChartTab = ref('channels')

const analyticsDates = ref({
  start: new Date().toISOString().split('T')[0],
  end: new Date().toISOString().split('T')[0]
})
const selectedRangeId = ref('today')
const selectedPaymentMethodFilter = ref('todos')

const dateRanges = [
  { id: 'today', label: 'Hoy' },
  { id: 'week', label: 'Semana' },
  { id: 'month', label: 'Mes' },
  { id: 'year', label: 'Año' }
]

const formatCurrency = (val: any) => {
  const n = Number(val)
  return isNaN(n) ? '0.00' : n.toFixed(2)
}

const setAnalyticsRange = (rangeId: string) => {
  selectedRangeId.value = rangeId
  const today = new Date()
  let start = new Date()
  let end = new Date()

  if (rangeId === 'today') {
    // Current date
  } else if (rangeId === 'week') {
    const day = today.getDay()
    const diff = today.getDate() - day + (day === 0 ? -6 : 1)
    start = new Date(today.setDate(diff))
    end = new Date(today.setDate(start.getDate() + 6))
  } else if (rangeId === 'month') {
    start = new Date(today.getFullYear(), today.getMonth(), 1)
    end = new Date(today.getFullYear(), today.getMonth() + 1, 0)
  } else if (rangeId === 'year') {
    start = new Date(today.getFullYear(), 0, 1)
    end = new Date(today.getFullYear(), 11, 31)
  }

  analyticsDates.value.start = start.toISOString().split('T')[0]
  analyticsDates.value.end = end.toISOString().split('T')[0]
  loadAnalytics()
}

const loadAnalytics = async () => {
  loadingAnalytics.value = true
  loadingAdvanced.value = true
  analyticsData.value = null
  advancedAnalyticsData.value = null

  try {
    const { start, end } = analyticsDates.value
    let url = `/admin/analytics?fecha_inicio=${start}&fecha_fin=${end}`
    if (selectedPaymentMethodFilter.value !== 'todos') {
       url += `&metodo_pago=${selectedPaymentMethodFilter.value}`
    }
    
    const response = await api.get(url)
    analyticsData.value = response.data
    loadingAnalytics.value = false

    let advancedUrl = `/admin/analytics/advanced?fecha_inicio=${start}&fecha_fin=${end}`
    if (selectedPaymentMethodFilter.value !== 'todos') {
       advancedUrl += `&metodo_pago=${selectedPaymentMethodFilter.value}`
    }
    const advancedResponse = await api.get(advancedUrl)
    advancedAnalyticsData.value = advancedResponse.data

  } catch (err) {
    console.error('Error loading analytics', err)
  } finally {
    loadingAnalytics.value = false
    loadingAdvanced.value = false
  }
}

const chartData = computed(() => {
  if (!analyticsData.value) return { labels: [], datasets: [] }
  
  const timeline = analyticsData.value.timeline
  const labels = timeline.map((d: any) => {
    const date = parseSafeDate(d.fecha)
    return date ? date.toLocaleDateString('es-MX', { timeZone: 'America/Mexico_City', day: 'numeric', month: 'short' }) : ''
  })
  
  return {
    labels,
    datasets: [
      {
        label: 'Ventas',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        borderColor: '#3b82f6',
        borderWidth: 3,
        pointBackgroundColor: '#fff',
        pointBorderColor: '#3b82f6',
        pointBorderWidth: 2,
        pointRadius: 4,
        pointHoverRadius: 6,
        data: timeline.map((d: any) => d.ventas),
        fill: true,
        tension: 0.4
      },
      {
        label: 'Gastos',
        backgroundColor: 'rgba(239, 68, 68, 0.05)',
        borderColor: '#ef4444',
        borderWidth: 2,
        borderDash: [5, 5],
        pointBackgroundColor: '#fff',
        pointBorderColor: '#ef4444',
        pointRadius: 0,
        data: timeline.map((d: any) => d.gastos),
        fill: false,
        tension: 0.4
      }
    ]
  }
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: '#1e293b',
      titleFont: { size: 12, weight: 'bold' as any },
      bodyFont: { size: 12 },
      padding: 12,
      cornerRadius: 12,
      displayColors: true,
      callbacks: {
        label: (context: any) => ` ${context.dataset.label}: $${formatCurrency(context.parsed.y)}`
      }
    }
  },
  scales: {
    y: {
      grid: {
        color: '#f1f5f9',
        drawBorder: false
      },
      ticks: {
        font: { size: 10, weight: 'bold' as any },
        color: '#94a3b8',
        callback: (v: any) => '$' + v
      },
      beginAtZero: true
    },
    x: {
      grid: { display: false },
      ticks: {
        font: { size: 10, weight: 'bold' as any },
        color: '#94a3b8'
      }
    }
  }
}

const categoryChartData = computed(() => {
   if (!advancedAnalyticsData.value?.ventas_categoria?.length) return null
   const data = advancedAnalyticsData.value.ventas_categoria
   return {
      labels: data.map((d: any) => d.categoria),
      datasets: [{
         data: data.map((d: any) => d.total),
         backgroundColor: ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#6366F1'],
         borderWidth: 6,
         borderColor: '#ffffff',
         hoverOffset: 15
      }]
   }
})

const hourChartData = computed(() => {
  if (!advancedAnalyticsData.value?.ventas_por_hora?.length) return null
  const data = advancedAnalyticsData.value.ventas_por_hora
  // Fill 24 hours if needed or just use available
  const labels = data.map((d: any) => `${d.hora}:00`)
  return {
    labels,
    datasets: [{
      label: 'Ingresos',
      backgroundColor: '#3b82f6',
      borderRadius: 8,
      data: data.map((d: any) => d.total)
    }]
  }
})

const orderTypeChartData = computed(() => {
  if (!advancedAnalyticsData.value?.tipos_orden?.length) return null
  const data = advancedAnalyticsData.value.tipos_orden
  const labelsMap: any = { 'local': 'Aquí', 'llevar': 'Llevar', 'uber': 'Uber Eats', 'rappi': 'Rappi' }
  return {
    labels: data.map((d: any) => labelsMap[d.tipo] || d.tipo),
    datasets: [{
      data: data.map((d: any) => d.total),
      backgroundColor: ['#10B981', '#F59E0B', '#3B82F6', '#F43F5E'],
      borderWidth: 4,
      borderColor: '#ffffff'
    }]
  }
})

const paymentMethodChartData = computed(() => {
  if (!advancedAnalyticsData.value?.metodos_pago_detalle?.length) return null
  const data = advancedAnalyticsData.value.metodos_pago_detalle
  return {
    labels: data.map((d: any) => d.metodo.toUpperCase()),
    datasets: [{
      data: data.map((d: any) => d.total),
      backgroundColor: ['#6366F1', '#EC4899', '#8B5CF6'],
      borderWidth: 4,
      borderColor: '#ffffff'
    }]
  }
})

const expenseStructureChartData = computed(() => {
  if (!advancedAnalyticsData.value?.estructura_gastos?.length) return null
  const data = advancedAnalyticsData.value.estructura_gastos
  const labelsMap: any = { 'directo': 'Directo', 'indirecto': 'Indirecto', 'nomina': 'Nómina' }
  return {
    labels: data.map((d: any) => labelsMap[d.tipo] || d.tipo),
    datasets: [{
      data: data.map((d: any) => d.total),
      backgroundColor: ['#F59E0B', '#3B82F6', '#EF4444'],
      borderWidth: 4,
      borderColor: '#ffffff'
    }]
  }
})

const projectionChartData = computed(() => {
  if (!advancedAnalyticsData.value?.proyeccion_ia?.proximos_7_dias) return null
  const data = advancedAnalyticsData.value.proyeccion_ia.proximos_7_dias
  const labelsMap: any = { 'Monday': 'Lun', 'Tuesday': 'Mar', 'Wednesday': 'Mié', 'Thursday': 'Jue', 'Friday': 'Vie', 'Saturday': 'Sáb', 'Sunday': 'Dom' }
  
  return {
    labels: data.map((d: any) => labelsMap[d.dia] || d.dia),
    datasets: [{
      label: 'Esperado',
      data: data.map((d: any) => d.esperado),
      borderColor: '#2563eb',
      backgroundColor: 'rgba(37, 99, 235, 0.05)',
      borderWidth: 4,
      pointBackgroundColor: '#fff',
      pointBorderColor: '#2563eb',
      pointBorderWidth: 2,
      pointRadius: 6,
      pointHoverRadius: 8,
      tension: 0.4,
      fill: true
    }]
  }
})

const projectionOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: '#1e293b',
      titleFont: { size: 12, weight: 'bold' as any },
      bodyFont: { size: 12 },
      callbacks: {
        label: (ctx: any) => ` Estimado: $${formatCurrency(ctx.parsed.y)}`
      }
    }
  },
  scales: {
    y: {
      grid: { color: 'rgba(255,255,255,0.05)' },
      ticks: { color: '#64748b', font: { size: 10, weight: 'bold' as any }, callback: (v: any) => '$' + v },
      beginAtZero: true
    },
    x: {
      grid: { display: false },
      ticks: { color: '#64748b', font: { size: 10, weight: 'bold' as any } }
    }
  }
}

const barOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      padding: 12,
      cornerRadius: 12,
      callbacks: {
        label: (ctx: any) => ` Ingreso Total: $${formatCurrency(ctx.parsed.y)}`
      }
    }
  },
  scales: {
    y: { 
      beginAtZero: true,
      grid: { color: '#f1f5f9' },
      ticks: { 
        font: { size: 10 },
        callback: (v: any) => '$' + v 
      }
    },
    x: { grid: { display: false }, ticks: { font: { size: 10 } } }
  }
}

const doughnutOptions = {
   responsive: true,
   maintainAspectRatio: false,
   plugins: {
      legend: { 
        display: true, 
        position: 'bottom' as any,
        labels: {
          usePointStyle: true,
          padding: 20,
          font: { size: 11, weight: 'bold' as any }
        }
      },
      tooltip: {
        padding: 12,
        cornerRadius: 12,
        callbacks: {
           label: (ctx: any) => ` ${ctx.label}: $${formatCurrency(ctx.parsed)}`
        }
      }
   },
   cutout: '70%'
}

const doughnutOptionsSmall = {
   ...doughnutOptions,
   plugins: {
     ...doughnutOptions.plugins,
     legend: { display: false }
   },
   cutout: '65%'
}

onMounted(() => {
  setAnalyticsRange('today')
})
</script>
