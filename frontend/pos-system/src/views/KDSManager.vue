<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed } from 'vue'
import { api } from '../api/client'
import { useAuthStore } from '../stores/auth'
import { usePedidosStore } from '../stores/pedidos'
import { useRouter } from 'vue-router'
import { formatElapsed } from '@/utils/dateUtils'
import { 
  Flame, 
  CheckCircle, 
  PackageCheck, 
  RotateCcw, 
  Search, 
  AlertCircle,
  LayoutDashboard,
  Clock,
  Utensils,
  Package,
  Car,
  Circle,
  ShieldCheck
} from 'lucide-vue-next'

interface Articulo {
  id: number
  cantidad: number
  precio_cobrado: string | number
  modificaciones?: string | null
  estado_item: string
  platillo?: { nombre: string; kds_name?: string | null; categoria?: string | null }
}

interface Pedido {
  id: number
  numero_display: string
  nombre_cliente: string | null
  mesa: string | null
  tipo_orden: 'aqui' | 'llevar' | 'uber_eats'
  estado: 'pendiente' | 'preparando' | 'listo' | 'entregado' | 'cuenta_solicitada' | 'pagado' | 'cancelado'
  articulos_pedido?: Articulo[]
  fecha_creacion: string
}

const auth = useAuthStore()
const pedidosStore = usePedidosStore()
const router = useRouter()

const error = ref<string | null>(null)
const selectedPedidoId = ref<number | null>(null)
let timer: number | undefined

const pedidosActivos = computed(() => {
  return pedidosStore.pedidosKDS
    .filter(p => ['pendiente', 'preparando', 'listo', 'entregado'].includes(p.estado))
    .map(p => {
      const articulosVisibles = (p.articulos_pedido || []).filter(a => 
        ['pendiente', 'preparando', 'listo'].includes(a.estado_item) &&
        a.platillo?.categoria !== 'Bebidas'
      )
      
      return {
        ...p,
        articulos_pedido: articulosVisibles
      }
    })
    .filter(p => (p.articulos_pedido || []).length > 0)
})

const pedidosRecienCompletados = computed(() => {
  const hace20Minutos = Date.now() - (20 * 60 * 1000)
  
  return pedidosStore.pedidosKDS
    .filter(p => {
      if (p.estado !== 'listo') return false
      const tiempoCreacion = new Date(p.fecha_creacion).getTime()
      return tiempoCreacion >= hace20Minutos
    })
    .sort((a, b) => new Date(b.fecha_creacion).getTime() - new Date(a.fecha_creacion).getTime())
})

const selectedPedido = computed(() => {
  return pedidosActivos.value.find(p => p.id === selectedPedidoId.value)
})

const vistaActual = ref<'activos' | 'completados' | 'disponibilidad'>('activos')

const platillos = ref<any[]>([])
const searchPlatillo = ref('')
const loading_platillos = ref(false)

const pedidosMostrados = computed(() => {
  if (vistaActual.value === 'completados') {
    return pedidosRecienCompletados.value as Pedido[]
  }
  
  const activos = pedidosActivos.value as Pedido[]
  
  return activos.sort((a, b) => {
    const tiempoA = new Date(a.fecha_creacion).getTime()
    const tiempoB = new Date(b.fecha_creacion).getTime()
    const diffA = Date.now() - tiempoA
    const diffB = Date.now() - tiempoB
    
    const urgentA = diffA > 10 * 60 * 1000
    const urgentB = diffB > 10 * 60 * 1000
    
    if (urgentA && !urgentB) return -1
    if (!urgentA && urgentB) return 1
    if (tiempoA !== tiempoB) return tiempoA - tiempoB
    return (a.numero_display || '').localeCompare(b.numero_display || '')
  })
})

const loading = computed(() => pedidosStore.loading)

function recuperarPedido(pedido: any) {
  updateEstadoPedidoOptimistic(pedido, 'preparando')
}

async function cargarPlatillos() {
  if (loading_platillos.value) return
  loading_platillos.value = true
  try {
    const response = await api.get('/platillos')
    platillos.value = response.data
  } catch (e: any) {
    error.value = 'Error al cargar platillos'
  } finally {
    loading_platillos.value = false
  }
}

async function toggleDisponibilidad(platillo: any) {
  const nuevoEstado = platillo.estado === 'disponible' ? 'no_disponible' : 'disponible'
  const estadoOriginal = platillo.estado
  platillo.estado = nuevoEstado
  try {
    await api.patch(`/platillos/${platillo.id}/disponibilidad`, { estado: nuevoEstado })
  } catch (e: any) {
    platillo.estado = estadoOriginal
    error.value = e?.response?.data?.detail || 'Error al cambiar disponibilidad'
  }
}

const platillosPorCategoria = computed(() => {
  const filtrados = platillos.value.filter(p => 
    p.nombre.toLowerCase().includes(searchPlatillo.value.toLowerCase())
  )
  const categorias: Record<string, any[]> = {}
  filtrados.forEach(platillo => {
    if (!categorias[platillo.categoria]) {
      categorias[platillo.categoria] = []
    }
    categorias[platillo.categoria].push(platillo)
  })
  return categorias
})

function getDisponiblesPorCategoria(categoria: string) {
  const platillosCategoria = platillosPorCategoria.value[categoria] || []
  const disponibles = platillosCategoria.filter(p => p.estado === 'disponible').length
  return { disponibles, total: platillosCategoria.length }
}

function getEstadoStyles(estado: string): string {
  const styles: Record<string, string> = {
    'pendiente': 'bg-[#00126D]/30 border-rose-500/30',
    'preparando': 'bg-[#00126D]/50 border-amber-500/50 shadow-[0_0_20px_rgba(245,158,11,0.1)]',
    'listo': 'bg-[#00126D]/70 border-emerald-500/40 opacity-90',
    'entregado': 'bg-[#00126D]/20 border-blue-500/30'
  }
  return styles[estado] || 'bg-slate-800'
}

const timerTick = ref(0)
let timerInterval: number | undefined

function calcularTiempoTranscurrido(fechaCreacion: string) {
  timerTick.value
  return formatElapsed(fechaCreacion)
}

function getTiempoColor(fechaCreacion: string) {
  const ahora = new Date()
  const fechaPedido = new Date(fechaCreacion)
  const diferenciaMs = ahora.getTime() - fechaPedido.getTime()
  const minutos = Math.floor(diferenciaMs / (1000 * 60))
  if (minutos < 5) return 'text-emerald-400'
  if (minutos < 10) return 'text-amber-400'
  if (minutos < 15) return 'text-orange-400'
  return 'text-rose-400 animate-pulse'
}

function getTipoOrdenIcon(tipo: string) {
  const icons: Record<string, any> = {
    'aqui': Utensils,
    'llevar': Package,
    'uber_eats': Car
  }
  return icons[tipo] || Utensils
}

function getArticuloStyles(estado: string) {
  switch (estado) {
    case 'pendiente': return 'bg-white/5 text-slate-300'
    case 'preparando': return 'bg-amber-500/10 text-amber-100 border-amber-500/30'
    case 'listo': return 'bg-emerald-500/10 text-emerald-100 border-emerald-500/30 opacity-70'
    default: return 'bg-white/5'
  }
}

function getArticuloIcon(estado: string) {
  switch (estado) {
    case 'pendiente': return Circle
    case 'preparando': return Flame
    case 'listo': return CheckCircle
    default: return Circle
  }
}

async function updateEstadoPedidoOptimistic(pedido: any, nuevoEstado: string) {
  try {
    const success = await pedidosStore.updatePedidoEstado(pedido.id, nuevoEstado)
    if (!success) error.value = pedidosStore.error || 'Error actualizando pedido'
  } catch (e: any) {
    error.value = 'Error actualizando pedido'
  }
}

async function toggleArticuloEstadoOptimistic(articulo: any) {
  let nuevoEstado: string
  switch (articulo.estado_item) {
    case 'pendiente': nuevoEstado = 'preparando'; break
    case 'preparando': nuevoEstado = 'listo'; break
    case 'listo': nuevoEstado = 'preparando'; break
    default: nuevoEstado = 'preparando'
  }
  try {
    const success = await pedidosStore.updateArticuloEstado(articulo.id, nuevoEstado)
    if (!success) error.value = pedidosStore.error || 'Error actualizando artículo'
  } catch (e: any) {
    error.value = 'Error actualizando artículo'
  }
}

onMounted(async () => {
  if (!auth.isAuthenticated || !['cocina', 'administrador'].includes(auth.user?.rol || '')) {
    router.replace({ name: 'login' })
    return
  }
  try {
    await pedidosStore.loadInitialData()
    await cargarPlatillos()
    await pedidosStore.initWebSocket('kds')
    timerInterval = window.setInterval(() => timerTick.value++, 1000)
  } catch (error) {
    console.error('❌ KDS Manager error:', error)
  }
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  if (timerInterval) clearInterval(timerInterval)
})
</script>

<template>
  <div class="min-h-screen bg-[#000a20] text-white overflow-x-hidden font-sans pb-10">
    <!-- Background Accents -->
    <div class="fixed inset-0 pointer-events-none opacity-20 z-0">
      <div class="absolute top-0 right-0 w-[600px] h-[600px] bg-[#00126D] blur-[150px] rounded-full"></div>
      <div class="absolute bottom-0 left-0 w-[500px] h-[500px] bg-[#FDB700] blur-[200px] rounded-full opacity-5"></div>
    </div>

    <!-- Header Premium -->
    <div class="z-20 bg-[#00126D]/30 backdrop-blur-xl border-b border-white/5 sticky top-0 shadow-2xl">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 py-4">
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div class="flex items-center gap-4">
            <div class="p-4 bg-gradient-to-br from-[#FDB700] to-[#FFD700] rounded-2xl shadow-lg">
              <LayoutDashboard class="w-7 h-7 text-[#00126D]" />
            </div>
            <div>
              <h1 class="text-2xl font-black tracking-tighter uppercase leading-none">Console Control</h1>
              <div class="flex items-center gap-2 mt-1">
                <div :class="pedidosStore.wsConnected ? 'bg-emerald-500' : 'bg-amber-500'" class="w-1.5 h-1.5 rounded-full"></div>
                <p class="text-slate-400 text-[9px] font-black tracking-[0.2em] uppercase opacity-70">
                  Dispatcher {{ pedidosStore.wsConnected ? 'Live' : 'Buffered' }}
                </p>
              </div>
            </div>
          </div>

          <!-- Navigation Tabs -->
          <div class="flex bg-black/40 p-1 rounded-2xl border border-white/10 shadow-inner">
            <button
              @click="vistaActual = 'activos'"
              class="flex items-center gap-2 px-6 py-3 rounded-xl text-xs font-black transition-all duration-300 tracking-wider"
              :class="vistaActual === 'activos' ? 'bg-[#FDB700] text-[#00126D] shadow-lg' : 'text-slate-400 hover:text-white'"
            >
              <Flame class="w-4 h-4" />
              <span>ACTIVOS ({{ pedidosActivos.length }})</span>
            </button>
            <button
              @click="vistaActual = 'completados'"
              class="flex items-center gap-2 px-6 py-3 rounded-xl text-xs font-black transition-all duration-300 tracking-wider"
              :class="vistaActual === 'completados' ? 'bg-emerald-500 text-white shadow-lg' : 'text-slate-400 hover:text-white'"
            >
              <PackageCheck class="w-4 h-4" />
              <span>TERMINADOS</span>
            </button>
            <button
              @click="vistaActual = 'disponibilidad'"
              class="flex items-center gap-2 px-6 py-3 rounded-xl text-xs font-black transition-all duration-300 tracking-wider"
              :class="vistaActual === 'disponibilidad' ? 'bg-violet-600 text-white shadow-lg' : 'text-slate-400 hover:text-white'"
            >
              <Search class="w-4 h-4" />
              <span>INVENTARIO</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Main Content Area -->
    <div class="relative z-10 max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
      <!-- Error Toasts -->
      <transition enter-active-class="transform transition ease-out duration-300 translate-y-2 opacity-0" 
                  enter-to-class="translate-y-0 opacity-100" 
                  leave-active-class="transition ease-in duration-100 opacity-0">
        <div v-if="error" class="fixed bottom-10 right-10 z-50 bg-rose-600 text-white px-6 py-4 rounded-2xl shadow-2xl flex items-center gap-4 border border-rose-400">
          <AlertCircle class="w-6 h-6" />
          <span class="font-black tracking-tight">{{ error }}</span>
          <button @click="error = null" class="ml-4 opacity-50 hover:opacity-100">✕</button>
        </div>
      </transition>

      <!-- Vista de Disponibilidad -->
      <div v-if="vistaActual === 'disponibilidad'" class="space-y-8 animate-in active">
        <div class="bg-[#00126D]/10 backdrop-blur-xl rounded-[2.5rem] p-8 border border-white/5 shadow-2xl">
          <div class="flex flex-col sm:flex-row items-center gap-8">
            <div class="p-5 bg-violet-600/10 rounded-2xl border border-violet-500/20 shadow-inner">
              <Search class="w-10 h-10 text-violet-400" />
            </div>
            <div class="flex-1 w-full">
              <h2 class="text-3xl font-black tracking-tight mb-3 uppercase">Gestión de Stock Activo</h2>
              <div class="relative">
                <Search class="absolute left-5 top-1/2 -translate-y-1/2 w-6 h-6 text-slate-500" />
                <input
                  v-model="searchPlatillo"
                  type="text"
                  placeholder="NOMBRE O CATEGORÍA..."
                  class="w-full pl-14 pr-8 py-5 bg-black/40 border border-white/10 rounded-3xl focus:ring-4 focus:ring-violet-500/20 focus:border-violet-500 outline-none transition-all font-black tracking-wide text-xl"
                />
              </div>
            </div>
          </div>
        </div>

        <div v-if="loading_platillos" class="flex flex-col items-center py-24">
          <div class="w-20 h-20 border-4 border-violet-500/20 border-t-violet-500 rounded-full animate-spin"></div>
        </div>

        <div v-else class="space-y-8">
          <div v-for="(platillosCategoria, categoria) in platillosPorCategoria" :key="categoria" 
               class="bg-white/5 backdrop-blur-md rounded-[3rem] p-8 border border-white/5 shadow-xl">
            <div class="flex items-center justify-between mb-10 border-b border-white/10 pb-6">
              <h3 class="text-3xl font-black text-white uppercase tracking-tighter">{{ categoria }}</h3>
              <span class="px-6 py-2 bg-black/30 rounded-full text-xs font-black text-[#FDB700] tracking-[0.2em] border border-white/5">
                {{ getDisponiblesPorCategoria(categoria).disponibles }} / {{ getDisponiblesPorCategoria(categoria).total }} DISPONIBLES
              </span>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              <div v-for="platillo in platillosCategoria" :key="platillo.id"
                   class="group/item p-6 rounded-[2.2rem] border-2 transition-all duration-300 flex flex-col justify-between min-h-[160px]"
                   :class="platillo.estado === 'disponible' ? 'bg-[#00126D]/20 border-white/5' : 'bg-rose-900/10 border-rose-500/30'">
                
                <div class="flex justify-between items-start mb-4">
                  <div class="flex-1 pr-6">
                    <h4 class="font-black text-2xl uppercase tracking-tighter leading-[1.1] mb-2 group-hover/item:text-[#FDB700] transition-colors">
                      {{ platillo.nombre }}
                    </h4>
                    <p class="text-slate-500 font-bold text-xs tracking-widest">UNIT-PREC: ${{ Number(platillo.precio).toFixed(2) }}</p>
                  </div>
                  
                  <button @click="toggleDisponibilidad(platillo)" 
                          class="relative w-20 h-10 rounded-full transition-all flex-shrink-0 border-2"
                          :class="platillo.estado === 'disponible' ? 'bg-emerald-500/20 border-emerald-500 shadow-[0_0_20px_rgba(16,185,129,0.2)]' : 'bg-rose-600/20 border-rose-600'">
                    <div class="absolute top-1 w-6 h-6 rounded-full shadow-2xl transition-all duration-400"
                         :class="[platillo.estado === 'disponible' ? 'left-11 bg-emerald-400 shadow-emerald-500/50' : 'left-1.5 bg-rose-400 shadow-rose-500/50']"></div>
                  </button>
                </div>

                <div class="flex items-center gap-3 bg-black/20 p-3 rounded-2xl border border-white/5">
                  <div class="w-3 h-3 rounded-full animate-pulse" :class="platillo.estado === 'disponible' ? 'bg-emerald-400' : 'bg-rose-400'"></div>
                  <span class="text-xs font-black uppercase tracking-[0.2em]" :class="platillo.estado === 'disponible' ? 'text-emerald-400' : 'text-rose-400'">
                    {{ platillo.estado === 'disponible' ? 'En Stock' : 'Agotado' }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Pedidos View -->
      <div v-else class="animate-in active">
        <div v-if="pedidosMostrados.length === 0" class="flex flex-col items-center justify-center py-40 opacity-40">
          <div class="p-12 bg-white/5 rounded-full mb-8 border border-white/10 shadow-2xl">
            <ShieldCheck class="w-24 h-24 text-slate-600" />
          </div>
          <h2 class="text-5xl font-black uppercase tracking-tighter text-white">Console Clear</h2>
          <p class="text-[#FDB700] mt-3 font-bold tracking-[0.4em] text-sm uppercase">Stand-by active</p>
        </div>

        <div v-else class="space-y-6">
          <div v-for="p in pedidosMostrados" :key="p.id"
               class="relative group rounded-[3rem] border-2 p-8 transition-all duration-500"
               :class="[getEstadoStyles(p.estado)]">
            
            <div class="flex flex-col lg:flex-row lg:items-center gap-6 lg:gap-12">
              <!-- Ticket Meta -->
              <div class="flex items-center gap-6 min-w-[280px]">
                <div class="p-5 bg-black/30 rounded-3xl border border-white/10 shadow-inner">
                  <component :is="getTipoOrdenIcon(p.tipo_orden)" class="w-10 h-10 text-white" />
                </div>
                <div>
                  <span class="text-[11px] font-black text-[#FDB700]/80 uppercase tracking-[0.3em] mb-1 block">TKT-REF #{{ p.numero_display }}</span>
                  <p class="text-4xl font-black leading-none uppercase tracking-tighter text-white">
                    {{ p.mesa ? 'Mesa ' + p.mesa : (p.nombre_cliente || 'Carry Out') }}
                  </p>
                </div>
              </div>

              <!-- Status Flag & Time -->
              <div class="flex items-center gap-6 flex-1">
                <div class="px-6 py-4 bg-black/50 rounded-2xl border border-white/10 flex items-center gap-4 shadow-xl">
                  <Clock class="w-6 h-6 text-[#FDB700] opacity-80" />
                  <span class="text-2xl font-black tabular-nums tracking-tighter" :class="[getTiempoColor(p.fecha_creacion)]">
                    {{ calcularTiempoTranscurrido(p.fecha_creacion) }}
                  </span>
                </div>
                <!-- Indicador de acción (solo si preparando) -->
                <div v-if="p.estado === 'preparando'" class="flex gap-2">
                  <div v-for="i in 3" :key="i" class="w-2.5 h-2.5 rounded-full bg-amber-500 animate-pulse" :style="`animation-delay: ${i * 0.3}s`"></div>
                </div>
              </div>

              <!-- Main Actions -->
              <div class="flex gap-4">
                <template v-if="vistaActual === 'completados'">
                  <button @click="recuperarPedido(p)" 
                          class="flex items-center justify-center gap-4 bg-rose-600 hover:bg-rose-500 text-white font-black px-10 py-5 rounded-[2rem] transition-all shadow-2xl active:scale-95 group/btn border border-rose-400/50">
                    <RotateCcw class="w-7 h-7 group-hover/btn:rotate-180 transition-transform duration-500" />
                    <span class="text-lg uppercase tracking-widest font-black">Rollback</span>
                  </button>
                </template>
                <template v-else>
                  <button v-if="p.estado === 'pendiente'" @click="updateEstadoPedidoOptimistic(p, 'preparando')"
                          class="flex items-center justify-center gap-4 bg-amber-500 hover:bg-amber-400 text-[#00126D] font-black px-10 py-5 rounded-[2rem] transition-all shadow-2xl active:scale-95 border border-amber-300">
                    <Flame class="w-8 h-8" />
                    <span class="text-xl uppercase tracking-widest font-black">Fire!</span>
                  </button>
                  <button v-else-if="p.estado === 'preparando'" @click="updateEstadoPedidoOptimistic(p, 'listo')"
                          class="flex items-center justify-center gap-4 bg-emerald-500 hover:bg-emerald-400 text-white font-black px-10 py-5 rounded-[2rem] transition-all shadow-2xl active:scale-95 border border-emerald-400">
                    <CheckCircle class="w-8 h-8" />
                    <span class="text-xl uppercase tracking-widest font-black">Complete</span>
                  </button>
                  <button v-else-if="p.estado === 'listo'" @click="updateEstadoPedidoOptimistic(p, 'entregado')"
                          class="flex items-center justify-center gap-4 bg-blue-600 hover:bg-blue-500 text-white font-black px-10 py-5 rounded-[2rem] transition-all shadow-2xl active:scale-95 border border-blue-400">
                    <PackageCheck class="w-8 h-8" />
                    <span class="text-xl uppercase tracking-widest font-black">Dispatch</span>
                  </button>
                  <div v-else class="flex items-center gap-5 px-10 py-5 bg-black/40 rounded-[2rem] border border-white/10 opacity-70">
                    <ShieldCheck class="w-8 h-8 text-white opacity-40" />
                    <span class="text-white font-black uppercase tracking-widest text-lg opacity-40">Archived</span>
                  </div>
                </template>
              </div>
            </div>

            <!-- Items Detailed (Tactile Grid) -->
            <transition enter-active-class="animate-in active" leave-active-class="opacity-0 duration-200">
              <div v-if="p.estado === 'preparando'" class="mt-10 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 border-t-2 border-white/5 pt-10">
                <div v-for="item in (p.articulos_pedido || [])" :key="item.id"
                     @click="toggleArticuloEstadoOptimistic(item)"
                     class="group/item p-6 rounded-[2.5rem] border-2 transition-all duration-300 cursor-pointer flex items-center justify-between"
                     :class="[getArticuloStyles(item.estado_item)]">
                  <div class="flex-1 pr-6">
                    <div class="flex items-center gap-4 mb-2">
                      <div class="w-12 h-12 bg-[#FDB700]/10 rounded-2xl flex items-center justify-center border border-[#FDB700]/30 shadow-inner">
                        <span class="text-3xl font-black text-[#FDB700]">{{ item.cantidad }}</span>
                      </div>
                      <p class="text-xl font-black leading-tight uppercase truncate text-white">{{ item.platillo?.kds_name || item.platillo?.nombre }}</p>
                    </div>
                    <p v-if="item.modificaciones" class="text-sm font-bold text-[#FDB700] mt-3 bg-black/40 px-4 py-2 rounded-xl border border-[#FDB700]/20 leading-snug uppercase tracking-wide">
                      {{ item.modificaciones }}
                    </p>
                  </div>
                  <div class="flex-shrink-0 group-active/item:scale-90 transition-transform">
                    <component :is="getArticuloIcon(item.estado_item)" 
                               class="w-12 h-12 transition-all duration-500" 
                               :class="item.estado_item === 'listo' ? 'text-emerald-400 drop-shadow-[0_0_15px_rgba(52,211,153,0.3)]' : 'text-slate-600 opacity-40'" />
                  </div>
                </div>
              </div>
              <div v-else class="mt-8 flex items-center gap-6">
                <div class="flex -space-x-4">
                   <div v-for="i in Math.min(p.articulos_pedido?.length || 0, 5)" :key="i" class="w-10 h-10 rounded-full border-2 border-[#00126D] bg-white/5 overflow-hidden flex items-center justify-center">
                     <Utensils class="w-4 h-4 text-white opacity-30" />
                   </div>
                </div>
                <span class="text-base font-black uppercase tracking-[0.3em] text-white/30">{{ p.articulos_pedido?.length || 0 }} Culinary Tokens REQUIRED</span>
              </div>
            </transition>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.animate-in {
  opacity: 0;
  transform: translateY(20px);
}
.animate-in.active {
  opacity: 1;
  transform: translateY(0);
  transition: all 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes slide-up {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

::-webkit-scrollbar {
  width: 10px;
}
::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 20px;
}
::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 20px;
  border: 3px solid transparent;
  background-clip: padding-box;
}
::-webkit-scrollbar-thumb:hover {
  background: rgba(253, 183, 0, 0.2);
}

.group {
  transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}
.group:hover {
  background-color: rgba(0, 18, 109, 0.25);
  border-color: rgba(253, 183, 0, 0.15);
}
</style>
