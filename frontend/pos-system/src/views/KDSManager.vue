<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed } from 'vue'
import { api } from '../api/client'
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'

interface Articulo {
  id: number
  cantidad: number
  precio_cobrado: string | number
  modificaciones?: string | null
  estado_item: string
  platillo?: { nombre: string; kds_name?: string | null }
}

interface Pedido {
  id: number
  numero_display: string
  nombre_cliente: string | null
  mesa: string | null
  tipo_orden: 'aqui' | 'llevar' | 'uber_eats'
  estado: 'pendiente' | 'preparando' | 'listo' | 'entregado' | 'cuenta_solicitada' | 'pagado' | 'cancelado'
  articulos_pedido?: Articulo[]
}

const auth = useAuthStore()
const router = useRouter()

const pedidos = ref<Pedido[]>([])
const error = ref<string | null>(null)
const selectedPedidoId = ref<number | null>(null)
let timer: number | undefined

const pedidosActivos = computed(() => {
  return pedidos.value.filter(p => !['entregado', 'cuenta_solicitada', 'pagado', 'cancelado'].includes(p.estado))
})

const selectedPedido = computed(() => {
  return pedidosActivos.value.find(p => p.id === selectedPedidoId.value)
})

function getTipoOrdenEmoji(tipo: string) {
  const emojis: Record<string, string> = {
    'aqui': '🍽️',
    'llevar': '📦',
    'uber_eats': '🚗'
  }
  return emojis[tipo] || '📋'
}

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

async function fetchPedidos() {
  try {
    const { data } = await api.get<Pedido[]>('/pedidos')
    pedidos.value = data
  } catch (e: any) {
    error.value = e?.response?.data?.detail || 'Error cargando pedidos'
  }
}

async function updateEstadoPedido(pedidoId: number, nuevoEstado: string) {
  try {
    await api.put(`/pedidos/${pedidoId}`, { estado: nuevoEstado })
    await fetchPedidos()
  } catch (e: any) {
    error.value = e?.response?.data?.detail || 'Error actualizando pedido'
  }
}

async function updateEstadoArticulo(articuloId: number, nuevoEstado: string) {
  try {
    const response = await api.put(`/pedidos/articulos/${articuloId}`, { estado_item: nuevoEstado })
    await fetchPedidos()
    return response.data
  } catch (e: any) {
    error.value = e?.response?.data?.detail || 'Error actualizando artículo'
  }
}

function selectPedido(pedidoId: number) {
  selectedPedidoId.value = selectedPedidoId.value === pedidoId ? null : pedidoId
}

function toggleArticuloEstado(articulo: Articulo) {
  if (!selectedPedido.value || selectedPedido.value.estado === 'pendiente') {
    error.value = 'Debes empezar a preparar el pedido primero'
    return
  }
  const nuevoEstado = articulo.estado_item === 'pendiente' ? 'listo' : 'pendiente'
  updateEstadoArticulo(articulo.id, nuevoEstado)
}

function swipeToPreparando(pedido: Pedido) {
  if (pedido.estado === 'pendiente') {
    updateEstadoPedido(pedido.id, 'preparando')
  }
}

onMounted(async () => {
  if (!auth.isAuthenticated) {
    router.replace({ name: 'login' })
    return
  }
  await fetchPedidos()
  timer = window.setInterval(fetchPedidos, 3000)
})

onUnmounted(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<template>
  <div class="min-h-screen flex flex-col bg-gradient-to-br from-[#F8FAFC] to-[#EEF2F5]">
    <!-- Header -->
    <header class="flex items-center justify-between px-6 py-4 bg-gradient-to-r from-[#00126D] to-[#001a4d] shadow-lg">
      <div class="flex items-center gap-4">
        <div class="bg-white rounded-lg p-2 drop-shadow-lg">
          <img src="/src/assets/Logo.png" alt="Logo" class="h-8" />
        </div>
        <div>
          <h1 class="text-2xl font-bold text-white">Cocina - Manager</h1>
          <p class="text-xs text-blue-100">La Hidrocálida</p>
        </div>
      </div>
      <div class="flex items-center gap-4 text-sm">
        <div class="bg-white bg-opacity-10 px-4 py-2 rounded-lg backdrop-blur">
          <p class="text-[#00126D] text-xs">Usuario</p>
          <p class="text-blue-500 font-semibold">{{ auth.user?.nombre }}</p>
        </div>
      </div>
    </header>

    <main class="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-6 p-6 overflow-hidden">
      <!-- Lista de Pedidos -->
      <div class="lg:col-span-1 bg-white rounded-2xl shadow-lg border-2 border-gray-200 overflow-hidden flex flex-col">
        <div class="bg-gradient-to-r from-[#00126D] to-[#001a4d] px-6 py-4 text-white font-bold">
          📋 Pedidos Activos ({{ pedidosActivos.length }})
        </div>
        <div class="flex-1 overflow-auto space-y-2 p-4">
          <div v-if="pedidosActivos.length === 0" class="text-center text-gray-500 py-8">
            Sin pedidos activos
          </div>
          <div
            v-for="p in pedidosActivos"
            :key="p.id"
            @click="selectPedido(p.id)"
            :class="[
              'p-4 rounded-lg border-2 cursor-pointer transition-all hover:shadow-md',
              selectedPedidoId === p.id
                ? 'bg-blue-50 border-[#FDB700] shadow-md'
                : 'bg-gray-50 border-gray-200 hover:border-gray-300'
            ]"
          >
            <div class="flex items-center justify-between mb-2">
              <div class="text-2xl font-black text-[#00126D]">{{ p.numero_display }}</div>
              <div :class="['text-xs font-bold px-2 py-1 rounded text-white', getEstadoColor(p.estado)]">
                {{ p.estado.toUpperCase() }}
              </div>
            </div>
            <div class="text-sm text-gray-600">{{ getTipoOrdenEmoji(p.tipo_orden) }} {{ p.tipo_orden }}</div>
            
            <!-- Mesa y Cliente con mejor diseño -->
            <div v-if="p.mesa" class="mt-2">
              <div class="bg-blue-500 text-white px-2 py-1 rounded-full text-xs font-bold text-center">
                🪑 MESA {{ p.mesa }}
              </div>
            </div>
            <div v-if="p.nombre_cliente && p.tipo_orden === 'llevar'" class="mt-2">
              <div class="bg-green-500 text-white px-2 py-1 rounded-full text-xs font-bold text-center">
                📦 {{ p.nombre_cliente }}
              </div>
            </div>
            
            <div class="text-xs text-gray-500 mt-2">{{ p.articulos_pedido?.length || 0 }} items</div>
          </div>
        </div>
      </div>

      <!-- Detalle del Pedido Seleccionado -->
      <div class="lg:col-span-2 bg-white rounded-2xl shadow-lg border-2 border-gray-200 overflow-hidden flex flex-col">
        <div v-if="!selectedPedido" class="flex-1 flex items-center justify-center text-gray-400">
          <div class="text-center">
            <p class="text-4xl mb-4">👈</p>
            <p class="text-lg font-semibold">Selecciona un pedido</p>
          </div>
        </div>

        <template v-else>
          <!-- Header del Pedido -->
          <div class="bg-gradient-to-r from-[#00126D] to-[#001a4d] px-6 py-4 text-white">
            <div class="flex items-center justify-between mb-3">
              <div class="flex items-center gap-3">
                <div class="text-4xl">{{ getTipoOrdenEmoji(selectedPedido.tipo_orden) }}</div>
                <div>
                  <div class="text-3xl font-black">Pedido #{{ selectedPedido.numero_display }}</div>
                  <div class="text-sm text-blue-100">{{ selectedPedido.tipo_orden }}</div>
                </div>
              </div>
              <div :class="['text-sm font-bold px-3 py-2 rounded-lg', getEstadoColor(selectedPedido.estado)]">
                {{ selectedPedido.estado.toUpperCase() }}
              </div>
            </div>

            <!-- Botones de Acción -->
            <div class="flex gap-2 mt-4">
              <button
                v-if="selectedPedido.estado === 'pendiente'"
                @click="swipeToPreparando(selectedPedido)"
                class="flex-1 py-2 px-4 bg-yellow-500 hover:bg-yellow-600 text-white font-bold rounded-lg transition-all active:scale-95"
              >
                👉 Empezar a preparar
              </button>
              <button
                v-if="selectedPedido.estado === 'preparando'"
                @click="updateEstadoPedido(selectedPedido.id, 'listo')"
                class="flex-1 py-2 px-4 bg-green-500 hover:bg-green-600 text-white font-bold rounded-lg transition-all active:scale-95"
              >
                ✓ Marcar como listo
              </button>
              <button
                v-if="selectedPedido.estado === 'listo'"
                @click="updateEstadoPedido(selectedPedido.id, 'entregado')"
                class="flex-1 py-2 px-4 bg-blue-500 hover:bg-blue-600 text-white font-bold rounded-lg transition-all active:scale-95"
              >
                🍽️ Entregado
              </button>
            </div>
          </div>

          <!-- Lista de Artículos -->
          <div class="flex-1 overflow-auto p-6 space-y-3">
            <div
              v-for="a in selectedPedido.articulos_pedido || []"
              :key="a.id"
              @click="toggleArticuloEstado(a)"
              :class="[
                'p-4 rounded-lg border-2 transition-all',
                selectedPedido.estado === 'pendiente'
                  ? 'cursor-not-allowed opacity-50 bg-gray-50 border-gray-200'
                  : 'cursor-pointer hover:shadow-md',
                a.estado_item === 'listo'
                  ? 'bg-green-50 border-green-500 shadow-md'
                  : 'bg-gray-50 border-gray-200 hover:border-gray-300'
              ]"
            >
              <div class="flex items-start justify-between">
                <div class="flex-1">
                  <div class="flex items-center gap-2 mb-1">
                    <div class="text-2xl font-black text-[#FDB700]">{{ a.cantidad }}x</div>
                    <div class="font-bold text-[#00126D]">{{ a.platillo?.kds_name || a.platillo?.nombre || 'Platillo' }}</div>
                  </div>
                  <div v-if="a.modificaciones" class="text-sm text-gray-600 ml-8">📝 {{ a.modificaciones }}</div>
                </div>
                <div :class="['text-2xl font-bold px-3 py-1 rounded', a.estado_item === 'listo' ? 'text-green-600' : 'text-gray-400']">
                  {{ a.estado_item === 'listo' ? '✓' : '○' }}
                </div>
              </div>
            </div>
          </div>

          <!-- Footer con Progreso -->
          <div class="bg-gray-50 px-6 py-4 border-t-2 border-gray-200">
            <div class="flex items-center justify-between mb-2">
              <span class="text-sm font-bold text-gray-700">Progreso</span>
              <span class="text-sm font-bold text-[#FDB700]">
                {{ (selectedPedido.articulos_pedido || []).filter(a => a.estado_item === 'listo').length }} / {{ selectedPedido.articulos_pedido?.length || 0 }}
              </span>
            </div>
            <div class="w-full bg-gray-300 rounded-full h-2 overflow-hidden">
              <div
                :style="{ width: `${((selectedPedido.articulos_pedido || []).filter(a => a.estado_item === 'listo').length / (selectedPedido.articulos_pedido?.length || 1)) * 100}%` }"
                class="bg-green-500 h-full transition-all"
              ></div>
            </div>
          </div>
        </template>
      </div>
    </main>
  </div>
</template>

<style scoped>
</style>
