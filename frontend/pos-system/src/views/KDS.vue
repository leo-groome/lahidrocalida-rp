<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed } from 'vue'
import { api } from '../api/client'
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'

// Tipo mínimo para mostrar tarjetas en KDS
interface PedidoKDS {
  id: number
  numero_display: string
  nombre_cliente: string | null
  tipo_orden: 'aqui' | 'llevar' | 'uber_eats'
  estado: 'pendiente' | 'preparando' | 'listo' | 'completado' | 'cancelado'
  fecha_creacion: string
  articulos_pedido?: Array<{
    id: number
    cantidad: number
    precio_cobrado: string | number
    modificaciones?: string | null
    platillo?: { nombre: string }
  }>
}

const auth = useAuthStore()
const router = useRouter()

const pedidos = ref<PedidoKDS[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
let timer: number | undefined

const todasLasComandas = computed(() => {
  return pedidos.value.filter(p => p.estado !== 'completado' && p.estado !== 'cancelado').slice(0, 60)
})

function getEstadoColor(estado: string) {
  const colors: Record<string, string> = {
    'pendiente': 'bg-red-500 text-white',
    'preparando': 'bg-yellow-500 text-white',
    'listo': 'bg-green-500 text-white'
  }
  return colors[estado] || 'bg-gray-500 text-white'
}

function getEstadoLabel(estado: string) {
  const labels: Record<string, string> = {
    'pendiente': 'PENDIENTE',
    'preparando': 'PREPARANDO',
    'listo': 'LISTO'
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

async function fetchPedidos() {
  loading.value = true
  error.value = null
  try {
    // Trae todos y filtramos por estado en cliente; backend ya ordena por fecha
    const { data } = await api.get<PedidoKDS[]>('/pedidos')
    pedidos.value = data
  } catch (e: any) {
    error.value = e?.response?.data?.detail || 'Error cargando pedidos'
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  if (!auth.isAuthenticated) {
    router.replace({ name: 'login' })
    return
  }
  await fetchPedidos()
  timer = window.setInterval(fetchPedidos, 10000)
})

onUnmounted(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<template>
  <div class="min-h-screen flex flex-col bg-[#0a0e27]">
    <main class="flex-1 p-2 overflow-hidden">
      <!-- Grid compacto de comandas -->
      <div class="grid gap-2" style="grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); grid-auto-rows: max-content;">
        <div v-for="p in todasLasComandas" :key="p.id" :class="['rounded-lg p-3 border-2 transition-all', getEstadoColor(p.estado)]" style="border-color: currentColor; opacity: 0.95;">
          <!-- Estado y número -->
          <div class="flex items-center justify-between mb-2">
            <div class="text-2xl font-black">{{ p.numero_display }}</div>
            <div class="text-xs font-bold px-2 py-1 bg-black bg-opacity-30 rounded">{{ getEstadoLabel(p.estado) }}</div>
          </div>

          <!-- Tipo de orden -->
          <div class="text-sm font-semibold mb-2">{{ getTipoOrdenEmoji(p.tipo_orden) }} {{ p.nombre_cliente || 'Cliente' }}</div>

          <!-- Items compactos -->
          <div class="text-xs space-y-0.5 bg-black bg-opacity-20 rounded p-2">
            <div v-for="a in p.articulos_pedido || []" :key="a.id" class="truncate">
              <span class="font-bold">{{ a.cantidad }}x</span> {{ a.platillo?.nombre || 'Platillo' }}
              <div v-if="a.modificaciones" class="text-xs opacity-90">{{ a.modificaciones }}</div>
            </div>
          </div>
        </div>

        <!-- Empty state -->
        <div v-if="todasLasComandas.length === 0" class="col-span-full text-center py-20 text-gray-400">
          <p class="text-4xl mb-4">✨</p>
          <p class="text-xl font-semibold">Sin comandas activas</p>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
</style>
