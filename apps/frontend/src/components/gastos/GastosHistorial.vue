<template>
  <div class="gastos-historial space-y-8 animate-in fade-in slide-in-from-bottom-5 duration-700">
    <!-- Header & Quick Stats -->
    <div class="flex flex-col lg:flex-row lg:items-end justify-between gap-6">
      <div class="space-y-1">
        <h2 class="text-xs font-black tracking-[0.3em] text-slate-400 uppercase">Administración</h2>
        <h1 class="text-5xl font-black tracking-tight text-slate-900 flex items-center gap-3">
          HISTORIAL <span class="text-indigo-600">GASTOS</span>
        </h1>
      </div>

      <div class="flex flex-wrap items-center gap-4">
        <!-- Quick Summary of current view -->
        <div class="bg-indigo-50 border border-indigo-100 rounded-[1.5rem] px-6 py-3 flex items-center gap-4">
          <div class="p-2 bg-indigo-600 rounded-xl text-white">
            <Calculator class="w-5 h-5" />
          </div>
          <div>
            <p class="text-[10px] font-black tracking-widest text-indigo-400 uppercase">Total en vista</p>
            <p class="text-xl font-black text-indigo-900 leading-tight">
              ${{ formatCurrency(calculateFilteredTotal) }}
            </p>
          </div>
        </div>

        <button 
          @click="$emit('new-gasto')" 
          class="h-[60px] px-8 bg-slate-900 text-white rounded-[1.5rem] hover:bg-slate-800 transition-all duration-300 flex items-center gap-3 group shadow-xl shadow-slate-200 active:scale-95"
        >
          <div class="w-8 h-8 bg-white/10 rounded-xl flex items-center justify-center group-hover:rotate-90 transition-transform duration-500">
            <Plus class="w-5 h-5 text-white" />
          </div>
          <span class="font-black tracking-widest text-sm uppercase">Nuevo Registro</span>
        </button>
      </div>
    </div>

    <!-- Filter Bar - Modern SaaS Style -->
    <div class="bg-white border-2 border-slate-100 rounded-[2.5rem] p-8 shadow-sm">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div class="space-y-2">
          <label class="text-[10px] font-black tracking-widest text-slate-400 uppercase ml-1 flex items-center gap-2">
            <CalendarIcon class="w-3 h-3" /> Desde
          </label>
          <div class="relative group">
            <input 
              type="date" 
              v-model="filters.fecha_inicio"
              class="w-full bg-slate-50 border-0 rounded-2xl px-5 py-3.5 text-sm font-bold text-slate-700 focus:ring-2 focus:ring-indigo-500 transition-all outline-none"
            >
          </div>
        </div>

        <div class="space-y-2">
          <label class="text-[10px] font-black tracking-widest text-slate-400 uppercase ml-1 flex items-center gap-2">
            <CalendarIcon class="w-3 h-3" /> Hasta
          </label>
          <div class="relative group">
            <input 
              type="date" 
              v-model="filters.fecha_fin"
              class="w-full bg-slate-50 border-0 rounded-2xl px-5 py-3.5 text-sm font-bold text-slate-700 focus:ring-2 focus:ring-indigo-500 transition-all outline-none"
            >
          </div>
        </div>

        <div class="space-y-2">
          <label class="text-[10px] font-black tracking-widest text-slate-400 uppercase ml-1 flex items-center gap-2">
            <Truck class="w-3 h-3" /> Proveedor
          </label>
          <select 
            v-model="filters.proveedor_id"
            class="w-full bg-slate-50 border-0 rounded-2xl px-5 py-3.5 text-sm font-bold text-slate-700 focus:ring-2 focus:ring-indigo-500 transition-all outline-none appearance-none cursor-pointer"
          >
            <option :value="null">Todos los proveedores</option>
            <option v-for="p in proveedores" :key="p.id" :value="p.id">{{ p.nombre }}</option>
          </select>
        </div>

        <div class="flex items-end gap-3">
          <button 
            @click="loadGastos" 
            class="flex-1 h-[52px] bg-indigo-600 text-white rounded-2xl text-xs font-black tracking-widest uppercase hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-100 flex items-center justify-center gap-2"
          >
            <Search class="w-4 h-4" /> Aplicar
          </button>
          <button 
            @click="clearFilters" 
            class="w-[52px] h-[52px] bg-slate-100 text-slate-500 rounded-2xl hover:bg-slate-200 transition-all flex items-center justify-center"
            title="Limpiar filtros"
          >
            <RotateCcw class="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>

    <!-- Main List Container -->
    <div class="relative min-h-[400px]">
      <!-- Loading Overlay -->
      <div v-if="loading" class="absolute inset-0 bg-white/60 backdrop-blur-[2px] z-20 flex items-center justify-center rounded-[3rem]">
        <div class="flex flex-col items-center gap-4">
          <div class="w-16 h-16 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
          <p class="text-xs font-black tracking-[0.2em] text-indigo-600 animate-pulse uppercase">Cargando registros...</p>
        </div>
      </div>

      <!-- Empty State -->
      <div v-if="!loading && gastos.length === 0" class="bg-white border-2 border-dashed border-slate-200 rounded-[3rem] py-24 flex flex-col items-center justify-center text-center px-6">
        <div class="w-24 h-24 bg-slate-50 rounded-full flex items-center justify-center mb-6">
          <FileText class="w-12 h-12 text-slate-300" />
        </div>
        <h3 class="text-2xl font-black text-slate-900 mb-2">No hay gastos</h3>
        <p class="text-slate-500 max-w-sm mb-8 leading-relaxed">No encontramos registros con los filtros seleccionados o para este periodo de tiempo.</p>
        <button @click="clearFilters" class="text-xs font-black tracking-widest text-indigo-600 uppercase hover:underline">Ver todo el historial</button>
      </div>

      <!-- Expense Cards List -->
      <div v-else class="space-y-4">
        <div 
          v-for="(gasto, index) in gastos" 
          :key="gasto.id" 
          class="bg-white border border-slate-100 rounded-[2rem] p-6 hover:shadow-2xl hover:shadow-slate-200/50 transition-all duration-500 group relative overflow-hidden"
          :style="{ animationDelay: `${index * 50}ms` }"
        >
          <!-- Subtle decoration -->
          <div class="absolute top-0 right-0 w-32 h-32 bg-slate-50 rounded-full -mr-16 -mt-16 group-hover:bg-indigo-50 transition-colors duration-500"></div>

          <div class="flex flex-col md:flex-row md:items-center gap-6 relative z-10">
            <!-- Date Badge -->
            <div class="flex flex-col items-center justify-center w-20 h-20 bg-slate-900 rounded-3xl text-white shadow-xl shadow-slate-200 group-hover:bg-indigo-600 transition-colors duration-500">
              <span class="text-xs font-black tracking-tighter opacity-70">{{ getDay(gasto.fecha_gasto) }}</span>
              <span class="text-2xl font-black">{{ getDayNum(gasto.fecha_gasto) }}</span>
              <span class="text-[10px] font-black uppercase opacity-70">{{ getMonth(gasto.fecha_gasto) }}</span>
            </div>

            <!-- Info Content -->
            <div class="flex-1 space-y-3">
              <div class="flex flex-wrap items-center gap-3">
                <h3 class="text-xl font-black text-slate-900 tracking-tight">
                  {{ gasto.tipo_gasto === 'nomina'
                    ? 'Pago de Nómina'
                    : (gasto.proveedor?.nombre || 'Proveedor Desconocido') }}
                </h3>
                <div class="flex gap-2">
                  <span :class="[
                    'px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest shadow-sm',
                    gasto.tipo_gasto === 'nomina' ? 'bg-purple-600 text-white' : 
                    gasto.tipo_gasto === 'indirecto' ? 'bg-amber-500 text-white' : 'bg-emerald-600 text-white'
                  ]">
                    {{ gasto.tipo_gasto }}
                  </span>
                  <span class="px-3 py-1 bg-slate-100 rounded-full text-[10px] font-black text-slate-500 uppercase tracking-widest flex items-center gap-1.5">
                    <component :is="gasto.metodo_pago === 'efectivo' ? Banknote : CreditCard" class="w-3 h-3" />
                    {{ gasto.metodo_pago }}
                  </span>
                </div>
              </div>

              <div class="flex flex-wrap items-center gap-x-6 gap-y-2">
                <div v-if="gasto.folio" class="flex items-center gap-2 text-xs font-bold text-slate-400">
                  <Hash class="w-3.5 h-3.5" />
                  <span>FOLIO: {{ gasto.folio }}</span>
                </div>
                <div v-if="gasto.descripcion" class="flex items-center gap-2 text-xs font-bold text-slate-500 italic max-w-md truncate">
                  <span class="text-slate-300">"</span>{{ gasto.descripcion }}<span class="text-slate-300">"</span>
                </div>
              </div>

              <!-- Empleados de la nómina -->
              <div v-if="gasto.nomina_detalles && gasto.nomina_detalles.length > 0" class="flex flex-wrap gap-2 pt-1">
                <div
                  v-for="nd in gasto.nomina_detalles.slice(0, 4)"
                  :key="nd.id"
                  class="bg-purple-50 border border-purple-100 px-3 py-1 rounded-xl flex items-center gap-2"
                >
                  <span class="text-[10px] font-bold text-purple-700">{{ nd.usuario?.nombre }}</span>
                  <span class="text-[10px] font-black text-purple-600">${{ formatCurrency(nd.monto) }}</span>
                </div>
                <div v-if="gasto.nomina_detalles.length > 4" class="px-2 py-1 flex items-center">
                  <span class="text-[10px] font-black text-slate-300">+{{ gasto.nomina_detalles.length - 4 }} más</span>
                </div>
              </div>

              <!-- Compact Item Badges / List -->
              <div v-if="gasto.detalles && gasto.detalles.length > 0" class="flex flex-wrap gap-2 pt-1">
                <div 
                  v-for="d in gasto.detalles.slice(0, 4)" 
                  :key="d.id"
                  class="bg-slate-50 border border-slate-100 px-3 py-1 rounded-xl flex items-center gap-2"
                >
                  <span class="text-[10px] font-black text-indigo-600">{{ d.cantidad }}</span>
                  <span class="text-[10px] font-bold text-slate-600">{{ d.articulo?.nombre }}</span>
                </div>
                <div v-if="gasto.detalles.length > 4" class="px-2 py-1 flex items-center">
                  <span class="text-[10px] font-black text-slate-300">+{{ gasto.detalles.length - 4 }} más</span>
                </div>
              </div>
            </div>

            <!-- Price & Actions -->
            <div class="flex flex-row md:flex-col items-center md:items-end justify-between md:justify-center gap-4 border-t md:border-t-0 md:border-l border-slate-100 pt-4 md:pt-0 md:pl-8">
              <div class="text-right">
                <p class="text-[10px] font-black tracking-widest text-slate-400 uppercase mb-1">Total Pagado</p>
                <div class="flex items-baseline gap-1">
                  <span class="text-sm font-black text-slate-400">$</span>
                  <span class="text-3xl font-black text-slate-900 tracking-tighter">
                    {{ formatCurrency(gasto.total) }}
                  </span>
                </div>
                <div v-if="gasto.total_manual" class="flex justify-end mt-1">
                  <span class="text-[10px] font-black text-amber-600 border border-amber-200 bg-amber-50 px-2 py-0.5 rounded-lg flex items-center gap-1">
                    <AlertCircle class="w-3 h-3" /> AJUSTE MANUAL
                  </span>
                </div>
              </div>
              
              <button 
                @click="$emit('edit-gasto', gasto)" 
                class="w-[44px] h-[44px] bg-slate-50 text-slate-400 rounded-2xl hover:bg-slate-900 hover:text-white transition-all flex items-center justify-center shadow-sm"
                title="Editar registro"
              >
                <ChevronRight class="w-6 h-6" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Pagination -->
      <div v-if="totalItems > 0" class="mt-12 flex flex-col sm:flex-row items-center justify-between gap-6 bg-slate-900 rounded-[2rem] p-6 shadow-2xl">
        <div class="text-xs font-black tracking-widest text-slate-400 uppercase">
          Mostrando <span class="text-white">{{ (page - 1) * pageSize + 1 }} - {{ Math.min(page * pageSize, totalItems) }}</span> 
          de <span class="text-white">{{ totalItems }}</span> registros
        </div>
        
        <div class="flex items-center gap-2">
          <button 
            @click="changePage(page - 1)" 
            :disabled="page === 1"
            class="w-12 h-12 flex items-center justify-center rounded-2xl bg-white/10 text-white disabled:opacity-30 hover:bg-white/20 transition-all"
          >
            <ChevronLeft class="w-6 h-6" />
          </button>
          
          <div class="flex items-center gap-1 px-4 text-white font-black text-sm">
            {{ page }} <span class="text-slate-500 mx-2">/</span> {{ Math.ceil(totalItems / pageSize) }}
          </div>

          <button 
            @click="changePage(page + 1)" 
            :disabled="page * pageSize >= totalItems"
            class="w-12 h-12 flex items-center justify-center rounded-2xl bg-white/10 text-white disabled:opacity-30 hover:bg-white/20 transition-all"
          >
            <ChevronRight class="w-6 h-6" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import api from '@/api/client'
import { parseSafeDate } from '@/utils/dateUtils'
import { 
  Plus, 
  Search, 
  RotateCcw, 
  Calendar as CalendarIcon, 
  Truck, 
  Banknote, 
  CreditCard, 
  FileText, 
  Calculator,
  ChevronRight,
  ChevronLeft,
  AlertCircle,
  Hash
} from 'lucide-vue-next'

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

const calculateFilteredTotal = computed(() => {
  return gastos.value.reduce((acc, g) => acc + (g.total || 0), 0)
})

const formatCurrency = (val: number) => val.toLocaleString('es-MX', { 
  minimumFractionDigits: 2, 
  maximumFractionDigits: 2 
})

// Date Formatting helpers for premium UI
const getDay = (dateStr: string) => {
  const d = parseSafeDate(dateStr)
  if (!d) return ''
  return d.toLocaleDateString('es-MX', { weekday: 'short' }).replace('.', '').toUpperCase()
}

const getDayNum = (dateStr: string) => {
  const d = parseSafeDate(dateStr)
  if (!d) return ''
  return d.getDate()
}

const getMonth = (dateStr: string) => {
  const d = parseSafeDate(dateStr)
  if (!d) return ''
  return d.toLocaleDateString('es-MX', { month: 'short' }).replace('.', '').toUpperCase()
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
    
    if (res.data.items && typeof res.data.total === 'number') {
      gastos.value = res.data.items
      totalItems.value = res.data.total
    } else if (Array.isArray(res.data)) {
      gastos.value = res.data
      totalItems.value = res.data.length
    }
    
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const changePage = (newPage: number) => {
  if (newPage < 1) return
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

// Watch filters to reset page, but don't auto-load to avoid excessive calls
watch(filters, () => {
  page.value = 1
}, { deep: true })

onMounted(() => {
  loadProveedores()
  loadGastos()
})

defineExpose({ loadGastos })
</script>

<style scoped>
.animate-in {
  animation: fadeIn 0.5s ease-out forwards;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

select {
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%23475569' stroke-width='2'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M19 9l-7 7-7-7'%3E%3C/path%3E%3C/svg%3E");
  background-position: right 1rem center;
  background-repeat: no-repeat;
  background-size: 1.5em;
  padding-right: 2.5rem;
}
</style>
