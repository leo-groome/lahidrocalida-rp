<script setup lang="ts">
import { onMounted, onUnmounted, computed, ref } from 'vue'
import { parseSafeDate } from '@/utils/dateUtils'
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
} from 'lucide-vue-next'

const auth = useAuthStore()
const router = useRouter()
const pedidosStore = usePedidosStore()

// Ref que actualiza cada segundo — todo cálculo de tiempo lo usa directamente
const ahora = ref(new Date())

const todasLasComandas = computed(() => {
  return pedidosStore.pedidosKDS
    .filter(p => ['pendiente', 'preparando'].includes(p.estado))
    .map(p => {
      const articulosVisibles = (p.articulos_pedido || []).filter(a =>
        ['pendiente', 'preparando', 'listo'].includes(a.estado_item) &&
        !['Bebidas', 'Aguas', 'Refrescos'].includes(a.platillo?.categoria || '')
      )
      return { ...p, articulos_pedido: articulosVisibles }
    })
    .filter(p => p.articulos_pedido.length > 0)
    .sort((a, b) => new Date(a.fecha_creacion).getTime() - new Date(b.fecha_creacion).getTime())
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

const densityMode = computed(() => {
  const count = todasLasComandas.value.length
  if (count <= 2) return 'comfy'
  if (count <= 6) return 'normal'
  return 'compact'
})


function getMinutosTranscurridos(fechaCreacion: string): number {
  const fecha = parseSafeDate(fechaCreacion)
  if (!fecha) return 0
  return Math.floor((ahora.value.getTime() - fecha.getTime()) / (1000 * 60))
}

function calcularTiempoTranscurrido(fechaCreacion: string): string {
  const fecha = parseSafeDate(fechaCreacion)
  if (!fecha) return '0s'
  const totalSeconds = Math.floor((ahora.value.getTime() - fecha.getTime()) / 1000)
  if (totalSeconds < 0) return '0s'
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60
  if (hours > 0) return `${hours}h ${minutes}m`
  if (minutes > 0) return `${minutes}m ${seconds}s`
  return `${seconds}s`
}

function getEstadoColor(estado: string, fechaCreacion: string) {
  const min = getMinutosTranscurridos(fechaCreacion)
  if (min >= 15) return 'border-red-500 shadow-[0_0_30px_rgba(239,68,68,0.5)]'
  if (min >= 10) return 'border-orange-500 shadow-[0_0_25px_rgba(249,115,22,0.4)]'
  if (min >= 5)  return 'border-yellow-400 shadow-[0_0_20px_rgba(250,204,21,0.3)]'
  if (estado === 'preparando') return 'border-amber-400 shadow-[0_0_15px_rgba(251,191,36,0.2)]'
  return 'border-zinc-600 shadow-lg'
}

function getEstadoHeaderClass(estado: string, fechaCreacion: string) {
  const min = getMinutosTranscurridos(fechaCreacion)
  if (min >= 15) return 'bg-red-600 text-white'
  if (min >= 10) return 'bg-orange-500 text-white'
  if (estado === 'preparando') return 'bg-amber-500 text-black'
  return 'bg-zinc-800 text-white'
}

function getTiempoBadgeClass(fechaCreacion: string) {
  const min = getMinutosTranscurridos(fechaCreacion)
  if (min < 5)  return 'bg-emerald-600 text-white'
  if (min < 10) return 'bg-yellow-500 text-black'
  if (min < 15) return 'bg-orange-600 text-white'
  return 'bg-red-600 text-white animate-pulse'
}

function getTipoOrdenIcon(tipo: string) {
  const icons: Record<string, any> = {
    'aqui': Utensils,
    'llevar': Package,
    'uber_eats': Car
  }
  return icons[tipo] || Utensils
}

function getArticuloItemStyles(estado_item: string) {
  switch (estado_item) {
    case 'pendiente':  return 'bg-zinc-800 border-zinc-600'
    case 'preparando': return 'bg-orange-500 border-orange-400'
    case 'listo':      return 'bg-green-700 border-green-500'
    default:           return 'bg-zinc-800 border-zinc-600'
  }
}

function getArticuloTextClass(estado_item: string) {
  switch (estado_item) {
    case 'preparando': return 'text-white'
    case 'listo': return 'text-white line-through opacity-70'
    default: return 'text-white'
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
    case 'pendiente': return 'text-zinc-400'
    case 'preparando': return 'text-white'
    case 'listo': return 'text-white'
    default: return 'text-zinc-400'
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
  try {
    await pedidosStore.loadInitialData()
    const wsConnected = await pedidosStore.initWebSocket('kds')
    if (!wsConnected) {
      timer = window.setInterval(() => { pedidosStore.refreshPedidos() }, 5000)
    }
    timerInterval = window.setInterval(() => { ahora.value = new Date() }, 1000)
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
  <div class="min-h-screen bg-[#070b14] text-white p-2 overflow-x-hidden font-sans">

    <!-- Grid de Comandas -->
    <div class="h-screen overflow-y-auto custom-scrollbar pb-2">
      <transition-group
        tag="div"
        name="list"
        class="grid gap-3 auto-rows-min transition-all duration-500 h-full"
        :class="[gridClasses]"
      >
        <div v-for="p in todasLasComandas" :key="p.id"
             class="flex flex-col bg-zinc-900 rounded-2xl border-2 transition-all duration-500 overflow-hidden"
             :class="[getEstadoColor(p.estado, p.fecha_creacion)]">

          <!-- Banner alerta 15+ min -->
          <div v-if="getMinutosTranscurridos(p.fecha_creacion) >= 15"
               class="h-1.5 bg-red-500 animate-pulse"></div>

          <!-- Header de la Card: número de orden + tipo -->
          <div class="px-4 py-2 flex items-center justify-between border-b border-white/10 bg-black/30">
            <span class="text-xs font-black text-zinc-400 uppercase tracking-widest">ORD-{{ p.numero_display }}</span>
            <div class="flex items-center gap-2">
              <div v-if="p.articulos_pedido.every(a => a.estado_item === 'listo')" class="flex items-center gap-1 bg-green-600 px-2 py-0.5 rounded text-white text-xs font-black uppercase">
                <CheckCircle class="w-3 h-3" />
                LISTA
              </div>
              <component :is="getTipoOrdenIcon(p.tipo_orden)" class="w-4 h-4 text-zinc-500" />
            </div>
          </div>

          <!-- Mesa / Número grande + tiempo -->
          <div class="px-4 py-4 text-center transition-all duration-300"
               :class="[getEstadoHeaderClass(p.estado, p.fecha_creacion)]">
            <h2 class="font-black tracking-tighter leading-none"
                :class="[
                  densityMode === 'comfy' ? 'text-8xl md:text-9xl' :
                  densityMode === 'normal' ? 'text-6xl md:text-7xl' : 'text-5xl md:text-6xl'
                ]">
              {{ p.mesa || p.nombre_cliente || '?' }}
            </h2>
            <div class="mt-2 inline-flex items-center gap-1.5 px-3 py-1 rounded-full font-black text-sm"
                 :class="[getTiempoBadgeClass(p.fecha_creacion)]">
              <Clock class="w-3.5 h-3.5" />
              {{ calcularTiempoTranscurrido(p.fecha_creacion) }}
            </div>
          </div>

          <!-- Lista de Artículos -->
          <div class="flex-1 p-3 space-y-2 overflow-y-auto custom-scrollbar-thin">
            <div v-for="a in ordenarArticulosPorEstado(p.articulos_pedido)" :key="a.id"
                 class="rounded-xl border-2 transition-all duration-300"
                 :class="[
                   getArticuloItemStyles(a.estado_item),
                   densityMode === 'compact' ? 'p-2.5' : 'p-3'
                 ]">

              <div class="flex items-center gap-3">
                <!-- Cantidad -->
                <div class="flex items-center justify-center bg-black/30 rounded-lg font-black text-white shrink-0"
                     :class="[densityMode === 'compact' ? 'w-8 h-8 text-lg' : 'w-10 h-10 text-xl']">
                  {{ a.cantidad }}
                </div>

                <!-- Nombre + modificaciones -->
                <div class="flex-1 min-w-0">
                  <p class="font-black leading-tight uppercase"
                     :class="[
                       getArticuloTextClass(a.estado_item),
                       densityMode === 'compact' ? 'text-base' : 'text-lg md:text-xl'
                     ]">
                    {{ a.platillo?.kds_name || a.platillo?.nombre }}
                  </p>
                  <div v-if="a.modificaciones"
                       class="mt-1 font-bold text-xs uppercase italic px-2 py-0.5 rounded border-l-4"
                       :class="[
                         a.estado_item === 'preparando'
                           ? 'text-black border-black/40 bg-black/20'
                           : 'text-yellow-400 border-yellow-400 bg-black/30'
                       ]">
                    {{ a.modificaciones }}
                  </div>
                </div>

                <!-- Status Icon -->
                <component :is="getArticuloIcon(a.estado_item)"
                           class="shrink-0 transition-all duration-200"
                           :class="[
                             getArticuloIconColor(a.estado_item),
                             densityMode === 'compact' ? 'w-6 h-6' : 'w-7 h-7'
                           ]" />
              </div>
            </div>
          </div>

        </div>
      </transition-group>
    </div>

    <!-- Loading -->
    <div v-if="pedidosStore.loading" class="fixed inset-0 z-50 flex items-center justify-center bg-[#070b14]/90 backdrop-blur-md">
      <div class="text-center">
        <div class="relative w-20 h-20 mx-auto mb-4">
          <div class="absolute inset-0 border-4 border-white/10 rounded-full"></div>
          <div class="absolute inset-0 border-4 border-t-amber-400 rounded-full animate-spin"></div>
        </div>
        <p class="text-xl font-black text-white uppercase tracking-widest animate-pulse">Sincronizando...</p>
      </div>
    </div>

    <!-- Estado vacío -->
    <div v-else-if="todasLasComandas.length === 0" class="fixed inset-0 flex flex-col items-center justify-center">
      <CheckCircle class="w-40 h-40 text-green-600/50" />
      <h2 class="text-7xl font-black text-white uppercase tracking-tighter mt-8">
        Estación <span class="text-green-500">Limpia</span>
      </h2>
      <p class="text-zinc-500 font-bold uppercase tracking-widest mt-4">Todo al día</p>
    </div>
  </div>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 10px; }
.custom-scrollbar-thin::-webkit-scrollbar { width: 3px; }
.custom-scrollbar-thin::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.05); border-radius: 10px; }

.list-move,
.list-enter-active,
.list-leave-active {
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}
.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateY(20px) scale(0.95);
}
.list-leave-active {
  position: absolute;
  width: 100%;
}

@media (min-width: 2000px) {
  .grid-cols-3xl-6 { grid-template-columns: repeat(6, minmax(0, 1fr)); }
}
</style>
