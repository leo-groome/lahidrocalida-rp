<script setup lang="ts">
import { onMounted, onUnmounted, computed, ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { usePedidosStore } from '../stores/pedidos'
import { useRouter } from 'vue-router'

const auth = useAuthStore()
const router = useRouter()
const pedidosStore = usePedidosStore()

// Estado para forzar actualización del temporizador
const timerTick = ref(0)

const todasLasComandas = computed(() => {
  // Filtrar solo pedidos pendientes y preparando, limitados a 4, más antiguos primero
  return pedidosStore.pedidosKDS
    .filter(p => ['pendiente', 'preparando'].includes(p.estado))
    .sort((a, b) => new Date(a.fecha_creacion).getTime() - new Date(b.fecha_creacion).getTime())
    .slice(0, 4)
})

const totalPedidosPendientes = computed(() => {
  return pedidosStore.pedidosKDS
    .filter(p => ['pendiente', 'preparando'].includes(p.estado)).length
})

const pedidosNoVisibles = computed(() => {
  return Math.max(0, totalPedidosPendientes.value - 4)
})

function getEstadoColor(estado: string) {
  const colors: Record<string, string> = {
    'pendiente': 'bg-red-500',
    'preparando': 'bg-yellow-500', 
    'listo': 'bg-green-500',
    'entregado': 'bg-blue-500',
    'cuenta_solicitada': 'bg-purple-500'
  }
  return colors[estado] || 'bg-gray-500'
}

function getEstadoLabel(estado: string) {
  const labels: Record<string, string> = {
    'pendiente': 'PENDIENTE',
    'preparando': 'PREPARANDO',
    'listo': 'LISTO',
    'entregado': 'ENTREGADO',
    'cuenta_solicitada': 'CUENTA'
  }
  return labels[estado] || estado.toUpperCase()
}

function getTipoOrdenEmoji(tipo: string) {
  const emojis: Record<string, string> = {
    'aqui': '🍽️',
    'llevar': '📦',
    'uber_eats': '🚗'
  }
  return emojis[tipo] || '📋'
}

function calcularTiempoTranscurrido(fechaCreacion: string) {
  // Forzar re-renderizado con timerTick
  timerTick.value
  
  const ahora = new Date()
  const fechaPedido = new Date(fechaCreacion)
  const diferenciaMs = ahora.getTime() - fechaPedido.getTime()
  
  const minutos = Math.floor(diferenciaMs / (1000 * 60))
  const segundos = Math.floor((diferenciaMs % (1000 * 60)) / 1000)
  
  if (minutos >= 60) {
    const horas = Math.floor(minutos / 60)
    const minutosRestantes = minutos % 60
    return `${horas}h ${minutosRestantes}m`
  } else if (minutos > 0) {
    return `${minutos}m ${segundos}s`
  } else {
    return `${segundos}s`
  }
}

function getTiempoColor(fechaCreacion: string) {
  const ahora = new Date()
  const fechaPedido = new Date(fechaCreacion)
  const diferenciaMs = ahora.getTime() - fechaPedido.getTime()
  const minutos = Math.floor(diferenciaMs / (1000 * 60))
  
  // Colores para el temporizador como en la imagen
  if (minutos < 5) return 'bg-green-500 text-white'        // Verde sólido
  if (minutos < 10) return 'bg-yellow-500 text-white'      // Amarillo sólido
  if (minutos < 15) return 'bg-orange-500 text-white'      // Naranja sólido
  return 'bg-red-600 text-white'                           // Rojo sólido
}

function getArticuloItemStyles(estado_item: string) {
  switch (estado_item) {
    case 'pendiente':
      return 'bg-black bg-opacity-60'
    case 'preparando':
      return 'bg-yellow-600 bg-opacity-50 border-2 border-yellow-400'
    case 'listo':
      return 'bg-green-600 bg-opacity-60 border-2 border-green-300 shadow-lg'
    default:
      return 'bg-black bg-opacity-60'
  }
}

function getArticuloIcon(estado_item: string) {
  switch (estado_item) {
    case 'pendiente':
      return '⭕'
    case 'preparando':
      return '🔥'
    case 'listo':
      return '✅'
    default:
      return '⭕'
  }
}

function ordenarArticulosPorEstado(articulos: any[]) {
  if (!articulos || articulos.length === 0) return []
  
  // Ordenar artículos: pendiente → preparando → listo
  return [...articulos].sort((a, b) => {
    const prioridadEstado = {
      'pendiente': 1,   // Arriba - más urgentes
      'preparando': 2,  // Medio - en proceso
      'listo': 3        // Abajo - completados
    }
    
    const prioridadA = prioridadEstado[a.estado_item] || 999
    const prioridadB = prioridadEstado[b.estado_item] || 999
    
    return prioridadA - prioridadB
  })
}

onMounted(async () => {
  if (!auth.isAuthenticated) {
    router.replace({ name: 'login' })
    return
  }

  // Verificar que el rol tenga permisos para KDS
  if (!['cocina', 'administrador'].includes(auth.user?.rol || '')) {
    router.replace({ name: 'login' })
    return
  }

  console.log('🍽️ KDS View: Iniciando...')

  try {
    // Cargar datos iniciales
    await pedidosStore.loadInitialData()
    
    // Inicializar WebSocket para KDS
    const wsConnected = await pedidosStore.initWebSocket('kds')
    
    if (wsConnected) {
      console.log('✅ KDS View: WebSocket conectado, datos en tiempo real activos')
    } else {
      console.warn('⚠️ KDS View: WebSocket falló, usando polling como fallback')
      // Fallback: polling cada 5 segundos si WebSocket falla
      timer = window.setInterval(() => {
        pedidosStore.refreshPedidos()
      }, 5000)
    }

    // Inicializar temporizador para actualizar tiempo transcurrido cada segundo
    timerInterval = window.setInterval(() => {
      timerTick.value++
    }, 1000)

  } catch (error) {
    console.error('❌ KDS View: Error en inicialización:', error)
  }
})

let timer: number | undefined
let timerInterval: number | undefined

onUnmounted(() => {
  console.log('👋 KDS View: Cleanup...')
  if (timer) {
    clearInterval(timer)
  }
  if (timerInterval) {
    clearInterval(timerInterval)
  }
  // No desconectamos el WebSocket aquí porque puede ser usado por otras vistas
})
</script>

<template>
  <div class="min-h-screen bg-slate-900 p-4">
    <!-- Indicador de pedidos no visibles -->
    <div v-if="pedidosNoVisibles > 0" 
         class="fixed top-4 right-4 bg-red-600 text-white px-6 py-3 rounded-xl font-black text-2xl shadow-2xl border-4 border-white animate-pulse z-50">
      +{{ pedidosNoVisibles }} más pendientes
    </div>

    <!-- Grid adaptativo - máximo 4 pedidos, mejor legibilidad -->
    <div class="grid gap-6" :class="{
      'grid-cols-1': todasLasComandas.length <= 1,
      'grid-cols-2': todasLasComandas.length === 2,
      'grid-cols-3': todasLasComandas.length === 3,
      'grid-cols-2 lg:grid-cols-4': todasLasComandas.length === 4
    }">
      <div v-for="p in todasLasComandas" :key="p.id" 
           :class="['rounded-xl p-4 text-white shadow-2xl border-4 border-white border-opacity-30', getEstadoColor(p.estado)]">
        
        <!-- Header: temporizador + mesa + emoji centrado -->
        <div class="flex items-center justify-between mb-2">
          <!-- Temporizador (izquierda) -->
          <div :class="['px-3 py-2 rounded-full font-black shadow-lg border-2 border-white border-opacity-50', 
                       getTiempoColor(p.fecha_creacion), {
                         'text-xl': todasLasComandas.length <= 2,
                         'text-lg': todasLasComandas.length === 3,
                         'text-base': todasLasComandas.length >= 4
                       }]">
            {{ calcularTiempoTranscurrido(p.fecha_creacion) }}
          </div>

          <!-- Mesa/Nombre (centro - más grande) -->
          <div class="text-center flex-1 px-2">
            <div v-if="p.mesa" 
                 :class="['font-black text-white', {
                   'text-4xl': todasLasComandas.length <= 2,
                   'text-3xl': todasLasComandas.length === 3,
                   'text-2xl': todasLasComandas.length >= 4
                 }]">
              MESA {{ p.mesa }}
            </div>
            <div v-else-if="p.nombre_cliente" 
                 :class="['font-black text-white leading-tight', {
                   'text-3xl': todasLasComandas.length <= 2,
                   'text-2xl': todasLasComandas.length === 3,
                   'text-xl': todasLasComandas.length >= 4
                 }]">
              {{ p.nombre_cliente.toUpperCase() }}
            </div>
            <div v-else 
                 :class="['font-bold text-yellow-300', {
                   'text-2xl': todasLasComandas.length <= 2,
                   'text-xl': todasLasComandas.length === 3,
                   'text-lg': todasLasComandas.length >= 4
                 }]">
              PARA LLEVAR
            </div>
          </div>

          <!-- Solo emoji tipo de orden (derecha - centrado) -->
          <div class="flex justify-center">
            <span :class="{
              'text-5xl': todasLasComandas.length <= 2,
              'text-4xl': todasLasComandas.length === 3,
              'text-3xl': todasLasComandas.length >= 4
            }">{{ getTipoOrdenEmoji(p.tipo_orden) }}</span>
          </div>
        </div>

        <!-- Lista de artículos - FONT MÁXIMO PARA 8 METROS -->
        <div class="space-y-2">
          <div v-for="a in ordenarArticulosPorEstado(p.articulos_pedido || [])" :key="a.id" 
               :class="['p-3 rounded-lg text-white border-2 border-white border-opacity-30', 
                       getArticuloItemStyles(a.estado_item)]">
            <!-- Platillo principal - FONT GIGANTE -->
            <div class="font-black flex items-center justify-between"
                 :class="{
                   'text-4xl': todasLasComandas.length <= 2,
                   'text-3xl': todasLasComandas.length === 3,
                   'text-2xl': todasLasComandas.length >= 4
                 }">
              <span class="leading-tight">{{ a.cantidad }}x {{ a.platillo?.kds_name || a.platillo?.nombre || 'Platillo' }}</span>
              <span class="text-5xl ml-2 flex-shrink-0">{{ getArticuloIcon(a.estado_item) }}</span>
            </div>
            <!-- Modificaciones - FONT GRANDE -->
            <div v-if="a.modificaciones" 
                 class="mt-1 font-bold leading-snug bg-yellow-900 bg-opacity-60 p-2 rounded border-l-4 border-yellow-400"
                 :class="{
                   'text-2xl': todasLasComandas.length <= 2,
                   'text-xl': todasLasComandas.length === 3,
                   'text-lg': todasLasComandas.length >= 4
                 }">
              {{ a.modificaciones }}
            </div>
          </div>
        </div>
      </div>

      <!-- Estados vacíos -->
      <div v-if="pedidosStore.loading" class="col-span-full text-center py-20 text-white">
        <p class="text-8xl mb-6">⏳</p>
        <p class="text-4xl font-bold">Cargando comandas...</p>
      </div>

      <div v-else-if="todasLasComandas.length === 0" class="col-span-full text-center py-20 text-white">
        <p class="text-8xl mb-6">✨</p>
        <p class="text-4xl font-bold">¡Todo listo!</p>
        <p class="text-xl opacity-75 mt-3">Sin comandas pendientes o en preparación</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
</style>
