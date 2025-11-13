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
  return pedidosStore.pedidosKDS
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
  <div class="min-h-screen bg-slate-900 p-2">
    <!-- Grid optimizado para TV - más comandas visibles -->
    <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-3">
      <div v-for="p in todasLasComandas" :key="p.id" 
           :class="['rounded-lg p-3 text-white shadow-lg', getEstadoColor(p.estado)]">
        
        <!-- Header compacto: emoji + número + temporizador -->
        <div class="flex items-center justify-between mb-2">
          <div class="flex items-center gap-2">
            <span class="text-2xl">{{ getTipoOrdenEmoji(p.tipo_orden) }}</span>
            <span class="text-2xl font-black">{{ p.numero_display }}</span>
          </div>
          <div :class="['px-2 py-1 rounded-full text-xs font-bold', getTiempoColor(p.fecha_creacion)]">
            {{ calcularTiempoTranscurrido(p.fecha_creacion) }}
          </div>
        </div>

        <!-- Mesa compacta -->
        <div v-if="p.mesa" class="text-center mb-2">
          <div class="text-lg font-bold">Mesa {{ p.mesa }}</div>
        </div>
        <div v-else-if="p.nombre_cliente" class="text-center mb-2">
          <div class="text-sm font-semibold truncate">{{ p.nombre_cliente }}</div>
        </div>

        <!-- Lista de platillos - fondo negro con texto blanco -->
        <div class="space-y-1">
          <div v-for="a in p.articulos_pedido || []" :key="a.id" 
               :class="['p-2 rounded text-white text-sm', 
                       a.estado_item === 'listo' 
                         ? 'bg-green-600 bg-opacity-40 line-through opacity-70' 
                         : 'bg-black bg-opacity-60']">
            <div class="font-medium">
              {{ a.cantidad }}x {{ a.platillo?.kds_name || a.platillo?.nombre || 'Platillo' }}
            </div>
            <div v-if="a.modificaciones" class="text-xs opacity-90 mt-0.5">
              {{ a.modificaciones }}
            </div>
          </div>
        </div>
      </div>

      <!-- Estados vacíos -->
      <div v-if="pedidosStore.loading" class="col-span-full text-center py-16 text-white">
        <p class="text-5xl mb-3">⏳</p>
        <p class="text-xl font-bold">Cargando...</p>
      </div>

      <div v-else-if="todasLasComandas.length === 0" class="col-span-full text-center py-16 text-white">
        <p class="text-5xl mb-3">✨</p>
        <p class="text-xl font-bold">¡Todo listo!</p>
        <p class="text-sm opacity-75 mt-1">Sin comandas pendientes</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
</style>
