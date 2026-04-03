<script setup lang="ts">
import { onMounted, onUnmounted, computed, ref } from 'vue'
import { formatElapsed } from '@/utils/dateUtils'
import { useAuthStore } from '../stores/auth'
import { usePedidosStore } from '../stores/pedidos'
import { useRouter } from 'vue-router'
import { 
  Clock, 
  Utensils, 
  Package, 
  Car, 
  CheckCircle, 
  Flame, 
  Circle,
  AlertCircle
} from 'lucide-vue-next'

const auth = useAuthStore()
const router = useRouter()
const pedidosStore = usePedidosStore()

// Estado para forzar actualización del temporizador
const timerTick = ref(0)

const todasLasComandas = computed(() => {
  // Filtrar pedidos pendientes y preparando + pedidos que volvieron a pendiente con artículos nuevos
  return pedidosStore.pedidosKDS
    .filter(p => ['pendiente', 'preparando'].includes(p.estado))
    .map(p => {
      // Filtrar artículos: ocultar entregado y ocultar Bebidas
      const articulosVisibles = (p.articulos_pedido || []).filter(a => 
        ['pendiente', 'preparando', 'listo'].includes(a.estado_item) &&
        a.platillo?.categoria !== 'Bebidas'
      )
      
      return {
        ...p,
        articulos_pedido: articulosVisibles
      }
    })
    // Filtrar pedidos que NO tienen artículos visibles
    .filter(p => p.articulos_pedido.length > 0)
    .sort((a, b) => new Date(a.fecha_creacion).getTime() - new Date(b.fecha_creacion).getTime())
})

const totalPedidosPendientes = computed(() => {
  return todasLasComandas.value.length
})

// Sistema de Densidad Dinámica
const densityMode = computed(() => {
  const count = todasLasComandas.value.length
  if (count <= 2) return 'comfy'
  if (count <= 6) return 'normal'
  return 'compact'
})

const gridClasses = computed(() => {
  const count = todasLasComandas.value.length
  if (count <= 1) return 'grid-cols-1 max-w-5xl mx-auto'
  if (count === 2) return 'grid-cols-1 xl:grid-cols-2'
  if (count === 3) return 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3'
  if (count === 4) return 'grid-cols-1 md:grid-cols-2 xl:grid-cols-4'
  if (count <= 6) return 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3'
  if (count <= 8) return 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4'
  return 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 grid-cols-3xl-6'
})

// Acciones interactivas
async function toggleArticuloEstado(articulo: any) {
  let nuevoEstado = 'pendiente'
  if (articulo.estado_item === 'pendiente') nuevoEstado = 'preparando'
  else if (articulo.estado_item === 'preparando') nuevoEstado = 'listo'
  else return // Ya está listo

  await pedidosStore.updateArticuloEstado(articulo.id, nuevoEstado)
}

async function marcarPedidoCompleto(pedido: any) {
  // Marcar todos los artículos como listos
  const promesas = pedido.articulos_pedido
    .filter((a: any) => a.estado_item !== 'listo')
    .map((a: any) => pedidosStore.updateArticuloEstado(a.id, 'listo'))
  
  await Promise.all(promesas)
  
  // Forzar actualización del pedido a listo
  await pedidosStore.updatePedidoEstado(pedido.id, 'listo')
}

function getEstadoColor(estado: string, fechaCreacion: string) {
  const ahora = new Date()
  const fechaPedido = new Date(fechaCreacion)
  const diferenciaMin = Math.floor((ahora.getTime() - fechaPedido.getTime()) / (1000 * 60))

  if (diferenciaMin >= 15) return 'border-rose-500 shadow-[0_0_25px_rgba(244,63,94,0.2)]'
  if (diferenciaMin >= 10) return 'border-orange-500 shadow-[0_0_20px_rgba(249,115,22,0.15)]'
  
  if (estado === 'preparando') return 'border-amber-400 shadow-[0_0_20px_rgba(251,191,36,0.1)]'
  return 'border-white/10 shadow-xl'
}

function getEstadoHeaderClass(estado: string, fechaCreacion: string) {
  const ahora = new Date()
  const fechaPedido = new Date(fechaCreacion)
  const diferenciaMin = Math.floor((ahora.getTime() - fechaPedido.getTime()) / (1000 * 60))

  if (diferenciaMin >= 15) return 'bg-rose-500 text-white'
  if (diferenciaMin >= 10) return 'bg-orange-500 text-white'
  if (estado === 'preparando') return 'bg-amber-400 text-black'
  return 'bg-slate-800 text-slate-300'
}

function getTipoOrdenIcon(tipo: string) {
  const icons: Record<string, any> = {
    'aqui': Utensils,
    'llevar': Package,
    'uber_eats': Car
  }
  return icons[tipo] || Utensils
}

function calcularTiempoTranscurrido(fechaCreacion: string) {
  timerTick.value
  return formatElapsed(fechaCreacion)
}

function getTiempoBadgeClass(fechaCreacion: string) {
  const ahora = new Date()
  const fechaPedido = new Date(fechaCreacion)
  const minutos = Math.floor((ahora.getTime() - fechaPedido.getTime()) / (1000 * 60))
  
  if (minutos < 5) return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
  if (minutos < 10) return 'bg-amber-500/10 text-amber-400 border-amber-500/20'
  if (minutos < 15) return 'bg-orange-500/10 text-orange-400 border-orange-500/20'
  return 'bg-rose-500/20 text-rose-400 border-rose-500/30 animate-pulse'
}

function getArticuloItemStyles(estado_item: string) {
  switch (estado_item) {
    case 'pendiente':
      return 'bg-slate-800/40 border-white/5 hover:bg-slate-800/60 cursor-pointer'
    case 'preparando':
      return 'bg-amber-500/10 border-amber-500/30 ring-1 ring-amber-500/20 cursor-pointer'
    case 'listo':
      return 'bg-emerald-500/10 border-emerald-500/30 opacity-60'
    default:
      return 'bg-slate-800/40 border-white/5'
  }
}

function getArticuloIcon(estado_item: string) {
  switch (estado_item) {
    case 'pendiente': return Circle
    case 'preparando': return Flame
    case 'listo': return CheckCircle
    default: return Circle
  }
}

function getArticuloIconColor(estado_item: string) {
  switch (estado_item) {
    case 'pendiente': return 'text-slate-600'
    case 'preparando': return 'text-amber-400 animate-pulse'
    case 'listo': return 'text-emerald-400'
    default: return 'text-slate-600'
  }
}

function ordenarArticulosPorEstado(articulos: any[]) {
  if (!articulos || articulos.length === 0) return []
  return [...articulos].sort((a, b) => {
    const prioridad = { 'preparando': 1, 'pendiente': 2, 'listo': 3 }
    return (prioridad[a.estado_item] || 99) - (prioridad[b.estado_item] || 99)
  })
}

onMounted(async () => {
  if (!auth.isAuthenticated) { router.replace({ name: 'login' }); return }
  if (!['cocina', 'administrador'].includes(auth.user?.rol || '')) { router.replace({ name: 'login' }); return }

  try {
    await pedidosStore.loadInitialData()
    const wsConnected = await pedidosStore.initWebSocket('kds')
    
    if (!wsConnected) {
      timer = window.setInterval(() => { pedidosStore.refreshPedidos() }, 5000)
    }

    timerInterval = window.setInterval(() => { timerTick.value++ }, 1000)
  } catch (error) {
    console.error('❌ KDS View: Error en inicialización:', error)
  }
})

let timer: number | undefined
let timerInterval: number | undefined

onUnmounted(() => {
  if (timer) clearInterval(timer)
  if (timerInterval) clearInterval(timerInterval)
})
</script>

<template>
  <div class="min-h-screen bg-[#070b14] text-slate-200 p-4 md:p-6 lg:p-8 relative overflow-x-hidden font-sans selection:bg-[#FDB700] selection:text-[#00126D]">
    <!-- Fondo Decorativo Premium -->
    <div class="fixed inset-0 pointer-events-none overflow-hidden">
      <div class="absolute -top-[10%] -right-[10%] w-[50%] h-[50%] bg-[#00126D]/15 blur-[120px] rounded-full"></div>
      <div class="absolute -bottom-[10%] -left-[10%] w-[40%] h-[40%] bg-[#FDB700]/5 blur-[100px] rounded-full"></div>
    </div>

    <!-- Layout Container -->
    <div class="relative z-10 max-w-[1920px] mx-auto h-full flex flex-col">
      
      <!-- Header Modernizado -->
      <header class="flex flex-col md:flex-row items-center justify-between gap-6 mb-8 bg-slate-900/40 backdrop-blur-2xl px-6 md:px-10 py-5 rounded-[2.5rem] border border-white/5 shadow-2xl transition-all duration-300">
        <div class="flex items-center gap-6 group">
          <div class="relative">
            <div class="absolute inset-0 bg-[#FDB700] blur-xl opacity-20 group-hover:opacity-40 transition-opacity"></div>
            <div class="relative p-4 bg-gradient-to-br from-[#FDB700] to-[#FFD700] rounded-2xl shadow-lg transform group-hover:scale-105 transition-transform duration-500">
              <Utensils class="w-8 md:w-10 h-8 md:h-10 text-[#00126D]" />
            </div>
          </div>
          <div>
            <h1 class="text-3xl md:text-4xl font-black text-white tracking-tighter uppercase leading-none mb-1">
              Kitchen <span class="text-[#FDB700]">Display</span>
            </h1>
            <div class="flex items-center gap-3">
              <div class="flex items-center gap-2 px-2 py-0.5 bg-emerald-500/10 rounded-full border border-emerald-500/20">
                <span class="flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
                <span class="text-[10px] font-black text-emerald-400 uppercase tracking-widest leading-none">Live Console</span>
              </div>
              <p class="text-slate-500 font-bold uppercase text-[10px] tracking-widest">Sucursal #{{ auth.user?.sucursal_id || '---' }}</p>
            </div>
          </div>
        </div>

        <!-- Metrics & Clock -->
        <div class="flex items-center gap-4 md:gap-8 bg-black/20 p-2 rounded-3xl border border-white/5">
          <div class="flex items-center gap-6 px-6 border-r border-white/10">
            <div class="text-center">
              <p class="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1">Activos</p>
              <p class="text-2xl font-black text-white leading-none">{{ todasLasComandas.length }}</p>
            </div>
            <div class="text-center">
              <p class="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1">En Cola</p>
              <p class="text-2xl font-black text-rose-500 leading-none">{{ pedidosStore.pedidosKDS.length - todasLasComandas.length }}</p>
            </div>
          </div>

          <div class="flex flex-col items-center px-6 min-w-[120px]">
            <div class="text-3xl font-black text-white leading-none tabular-nums tracking-tighter">
              {{ new Date().toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) }}
            </div>
            <div class="text-[#FDB700] font-black text-[9px] tracking-widest mt-1 opacity-70 uppercase text-center">Sync del Servidor</div>
          </div>
        </div>
      </header>

      <!-- Grid de Comandas -->
      <div class="flex-1 overflow-y-auto custom-scrollbar pb-8 px-2">
        <transition-group 
          tag="div" 
          name="list" 
          class="grid gap-6 auto-rows-min transition-all duration-500" 
          :class="[gridClasses, `density-${densityMode}`]"
        >
          <div v-for="p in todasLasComandas" :key="p.id" 
               class="flex flex-col bg-slate-900/60 backdrop-blur-xl rounded-[2.5rem] border-2 transition-all duration-500 overflow-hidden relative group/card"
               :class="[getEstadoColor(p.estado, p.fecha_creacion)]">
            
            <!-- Banner de Tiempo Máximo / Alerta -->
            <div v-if="Math.floor((new Date().getTime() - new Date(p.fecha_creacion).getTime()) / (1000 * 60)) >= 15" 
                 class="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-rose-600 via-rose-400 to-rose-600 animate-shimmer z-20"></div>

            <!-- Header de la Card -->
            <div class="px-5 py-4 flex items-center justify-between border-b border-white/5 bg-white/2">
              <div class="flex items-center gap-3">
                <div class="px-3 py-1 bg-white/5 rounded-full border border-white/10">
                  <span class="text-[10px] font-black text-slate-400 uppercase tracking-widest">ORD-{{ p.numero_display }}</span>
                </div>
                <div :class="[getTiempoBadgeClass(p.fecha_creacion)]" class="flex items-center gap-2 px-3 py-1 rounded-full border font-black text-sm tabular-nums transition-all duration-300">
                  <Clock class="w-3.5 h-3.5" />
                  {{ calcularTiempoTranscurrido(p.fecha_creacion) }}
                </div>
              </div>
              <div class="flex items-center gap-2">
                <div v-if="p.articulos_pedido.every(a => a.estado_item === 'listo')" class="text-emerald-400 flex items-center gap-1 bg-emerald-400/10 px-2 py-0.5 rounded-md border border-emerald-400/20">
                  <CheckCircle class="w-3 h-3" />
                  <span class="text-[9px] font-black uppercase">Ready</span>
                </div>
                <div class="bg-white/5 p-2 rounded-xl border border-white/10 text-white/50">
                  <component :is="getTipoOrdenIcon(p.tipo_orden)" class="w-5 h-5" />
                </div>
              </div>
            </div>

            <!-- Identificador de Mesa/Cliente -->
            <div class="px-6 py-8 transition-all duration-500 group-hover/card:bg-white/5" :class="[getEstadoHeaderClass(p.estado, p.fecha_creacion)]">
              <div class="text-center">
                <p class="text-[10px] font-black uppercase tracking-[0.3em] opacity-60 mb-1">
                  {{ p.mesa ? 'Mesa / Estación' : 'Cliente / Pedido' }}
                </p>
                <h2 class="font-black tracking-tighter truncate px-2 transition-all duration-500"
                    :class="[
                      densityMode === 'comfy' ? 'text-6xl md:text-7xl' : 
                      densityMode === 'normal' ? 'text-4xl md:text-5xl' : 'text-3xl md:text-4xl'
                    ]">
                  {{ p.mesa || p.nombre_cliente || 'SIN ID' }}
                </h2>
              </div>
            </div>

            <!-- Lista de Artículos -->
            <div class="flex-1 p-5 space-y-3 overflow-y-auto custom-scrollbar-thin transition-all duration-500"
                 :class="[densityMode === 'compact' ? 'max-h-[350px]' : 'max-h-[500px]']">
              <div v-for="a in ordenarArticulosPorEstado(p.articulos_pedido)" :key="a.id" 
                   @click="toggleArticuloEstado(a)"
                   class="group/item relative rounded-2xl border-2 transition-all duration-300 active:scale-[0.98] card-item-shadow"
                   :class="[
                     getArticuloItemStyles(a.estado_item),
                     densityMode === 'compact' ? 'p-3' : 'p-4'
                   ]">
                
                <div class="flex items-start gap-4">
                  <!-- Cantidad -->
                  <div class="flex flex-col items-center justify-center bg-[#FDB700] rounded-xl shadow-lg border-b-4 border-[#00126D]/20 transform -rotate-2 transition-all duration-300"
                       :class="[densityMode === 'compact' ? 'min-w-[32px] h-[32px]' : 'min-w-[42px] h-[42px]']">
                    <span class="font-black text-[#00126D]" :class="[densityMode === 'compact' ? 'text-lg' : 'text-xl']">{{ a.cantidad }}</span>
                  </div>

                  <!-- Detalles -->
                  <div class="flex-1 min-w-0 pt-0.5">
                    <p class="font-black text-white leading-tight uppercase tracking-tight transition-all duration-300" 
                       :class="[
                         a.estado_item === 'listo' ? 'line-through opacity-40' : '',
                         densityMode === 'compact' ? 'text-lg' : 'text-xl md:text-2xl'
                       ]">
                      {{ a.platillo?.kds_name || a.platillo?.nombre }}
                    </p>
                    
                    <!-- Modificaciones -->
                    <div v-if="a.modificaciones" class="mt-2 font-black text-[#FDB700] bg-black/40 px-3 py-1.5 rounded-lg border-l-4 border-[#FDB700] uppercase italic transition-all duration-300"
                        :class="[densityMode === 'compact' ? 'text-[10px]' : 'text-xs']">
                      {{ a.modificaciones }}
                    </div>
                  </div>

                  <!-- Status Icon -->
                  <div class="flex-shrink-0 pt-1">
                    <component :is="getArticuloIcon(a.estado_item)" 
                               class="transition-all duration-300"
                               :class="[
                                 getArticuloIconColor(a.estado_item),
                                 densityMode === 'compact' ? 'w-6 h-6' : 'w-8 h-8'
                               ]" />
                  </div>
                </div>
              </div>
            </div>

            <!-- Footer: Actions -->
            <div class="p-4 bg-black/20 border-t border-white/5">
              <button 
                @click="marcarPedidoCompleto(p)"
                class="w-full bg-emerald-500/10 hover:bg-emerald-500/20 border-2 border-emerald-500/20 hover:border-emerald-500/40 rounded-2xl transition-all duration-300 group/btn flex items-center justify-center gap-3 overflow-hidden relative"
                :class="[densityMode === 'compact' ? 'py-3' : 'py-4']"
              >
                <div class="absolute inset-0 bg-emerald-500/10 translate-y-full group-hover/btn:translate-y-0 transition-transform duration-500"></div>
                <div class="relative flex items-center gap-3">
                  <CheckCircle class="w-6 h-6 text-emerald-400 group-hover/btn:scale-110 transition-transform" />
                  <span class="font-black text-emerald-400 uppercase tracking-widest"
                        :class="[densityMode === 'compact' ? 'text-base' : 'text-lg']">
                    Completar Orden
                  </span>
                </div>
              </button>
            </div>
          </div>
        </transition-group>
      </div>

      <!-- Estados Vacíos y Loading -->
      <div v-if="pedidosStore.loading" class="fixed inset-0 z-50 flex items-center justify-center bg-[#070b14]/80 backdrop-blur-md">
        <div class="text-center group">
          <div class="relative w-24 h-24 mx-auto mb-6">
            <div class="absolute inset-0 border-4 border-white/5 rounded-full"></div>
            <div class="absolute inset-0 border-4 border-t-[#FDB700] rounded-full animate-spin"></div>
            <div class="absolute inset-0 flex items-center justify-center">
              <Utensils class="w-8 h-8 text-[#FDB700] animate-pulse" />
            </div>
          </div>
          <p class="text-xl font-black text-white uppercase tracking-[0.3em] animate-pulse">Sincronizando...</p>
        </div>
      </div>

      <div v-else-if="todasLasComandas.length === 0" class="flex-1 flex flex-col items-center justify-center py-20 px-6">
        <div class="relative transform transition-all duration-700 hover:scale-105">
          <div class="absolute inset-0 bg-emerald-500/10 blur-[80px] rounded-full animate-pulse"></div>
          <div class="relative p-12 bg-slate-900/50 rounded-full border border-white/5 shadow-2xl">
            <CheckCircle class="w-48 h-48 text-emerald-500/40" />
          </div>
        </div>
        <div class="text-center mt-12 relative">
          <h2 class="text-6xl md:text-8xl font-black text-white uppercase tracking-tighter mb-4 opacity-90">
            Estación <span class="text-[#FDB700]">Limpia</span>
          </h2>
          <div class="flex items-center justify-center gap-4 text-emerald-400/60 font-black text-xl uppercase tracking-[0.4em]">
            <span class="h-px w-12 bg-emerald-400/20"></span>
            Todo Producción al Día
            <span class="h-px w-12 bg-emerald-400/20"></span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 6px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { 
  background: rgba(255, 255, 255, 0.05); 
  border-radius: 10px; 
}
.custom-scrollbar-thin::-webkit-scrollbar { width: 4px; }
.custom-scrollbar-thin::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.03); border-radius: 10px; }

@keyframes shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}
.animate-shimmer {
  animation: shimmer 2.5s infinite linear;
}

/* Transitions for dynamic list */
.list-move,
.list-enter-active,
.list-leave-active {
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}
.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateY(30px) scale(0.9);
}
.list-leave-active {
  position: absolute;
  width: 100%;
}

.card-item-shadow {
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

/* Extra large screens support */
@media (min-width: 2000px) {
  .grid-cols-3xl-6 { grid-template-columns: repeat(6, minmax(0, 1fr)); }
}
</style>
