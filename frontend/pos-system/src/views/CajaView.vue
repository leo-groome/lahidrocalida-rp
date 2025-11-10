<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { api } from '../api/client'
import type { PedidoResponse } from '../types'

const router = useRouter()
const auth = useAuthStore()

// Referencias reactivas
const activeTab = ref<'overview' | 'pendientes'>('pendientes')
const todosLosPedidos = ref<PedidoResponse[]>([])
const pedidosPendientes = ref<PedidoResponse[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const successMessage = ref<string | null>(null)
const showNotification = ref(false)
const selectedPedido = ref<PedidoResponse | null>(null)
const processingPayment = ref(false)

let timer: number | undefined

// Validar que el usuario tenga permisos
onMounted(async () => {
  if (!auth.isAuthenticated || !['cajero', 'administrador'].includes(auth.user?.rol || '')) {
    router.replace({ name: 'login' })
    return
  }
  await loadData()
  // Auto-refresh cada 5 segundos
  timer = window.setInterval(loadData, 5000)
})

onUnmounted(() => {
  if (timer) window.clearInterval(timer)
})

// Cargar todos los datos
const loadData = async () => {
  if (processingPayment.value) return // No actualizar durante procesamiento de pago
  
  // Solo mostrar loading si no hay datos previos
  const isInitialLoad = todosLosPedidos.value.length === 0 && pedidosPendientes.value.length === 0
  
  if (isInitialLoad) {
    loading.value = true
  }
  
  try {
    await Promise.all([
      loadTodosLosPedidos(),
      loadPedidosPendientes()
    ])
  } catch (e: any) {
    showErrorNotification(e?.message || 'Error al cargar datos')
  } finally {
    if (isInitialLoad) {
      loading.value = false
    }
  }
}

// Cargar todos los pedidos (overview)
const loadTodosLosPedidos = async () => {
  try {
    const { data } = await api.get<PedidoResponse[]>('/pedidos')
    todosLosPedidos.value = data
  } catch (e: any) {
    throw new Error(e?.response?.data?.detail || 'Error al cargar pedidos')
  }
}

// Cargar pedidos pendientes de pago
const loadPedidosPendientes = async () => {
  try {
    const { data } = await api.get<PedidoResponse[]>('/pedidos/pendientes-pago/lista')
    pedidosPendientes.value = data
  } catch (e: any) {
    throw new Error(e?.response?.data?.detail || 'Error al cargar pedidos pendientes')
  }
}

// Computadas para estadísticas
const totalPendientesPago = computed(() => {
  return pedidosPendientes.value.reduce((sum, pedido) => sum + Number(pedido.total), 0)
})

const estadisticasOverview = computed(() => {
  const stats = {
    pendiente: 0,
    preparando: 0,
    listo: 0,
    entregado: 0,
    cuenta_solicitada: 0,
    pagado: 0,
    cancelado: 0
  }
  
  todosLosPedidos.value.forEach(pedido => {
    if (stats.hasOwnProperty(pedido.estado)) {
      stats[pedido.estado as keyof typeof stats]++
    }
  })
  
  return stats
})

const pedidosActivos = computed(() => {
  return todosLosPedidos.value.filter(p => !['pagado', 'cancelado'].includes(p.estado))
})

// Obtener emoji por tipo de orden
const getTipoOrdenEmoji = (tipo: string) => {
  const emojis: Record<string, string> = {
    'aqui': '🍽️',
    'llevar': '📦', 
    'uber_eats': '🚗'
  }
  return emojis[tipo] || '📋'
}

// Obtener color por estado
const getEstadoColor = (estado: string) => {
  const colors: Record<string, string> = {
    'pendiente': 'bg-yellow-500',
    'preparando': 'bg-orange-500', 
    'listo': 'bg-green-500',
    'entregado': 'bg-blue-500',
    'cuenta_solicitada': 'bg-purple-500',
    'pagado': 'bg-gray-500',
    'cancelado': 'bg-red-500'
  }
  return colors[estado] || 'bg-gray-400'
}

// Obtener texto del estado
const getEstadoTexto = (estado: string) => {
  const textos: Record<string, string> = {
    'pendiente': 'PENDIENTE',
    'preparando': 'PREPARANDO', 
    'listo': 'LISTO',
    'entregado': 'ENTREGADO',
    'cuenta_solicitada': 'CUENTA SOLICITADA',
    'pagado': 'PAGADO',
    'cancelado': 'CANCELADO'
  }
  return textos[estado] || estado.toUpperCase()
}

// Obtener detalles del pedido completo
const getPedidoCompleto = async (pedidoId: number) => {
  try {
    const { data } = await api.get<PedidoResponse>(`/pedidos/${pedidoId}`)
    return data
  } catch (e: any) {
    showErrorNotification(e?.response?.data?.detail || 'Error al obtener detalles del pedido')
    return null
  }
}

// Procesar pago
const procesarPago = async (pedido: PedidoResponse, metodoPago: 'efectivo' | 'tarjeta' | 'transferencia') => {
  processingPayment.value = true
  try {
    // Actualizar método de pago y estado
    await api.put(`/pedidos/${pedido.id}`, { 
      estado: 'pagado',
      metodo_pago: metodoPago 
    })
    
    const tipoTexto = pedido.mesa ? `Mesa ${pedido.mesa}` : pedido.nombre_cliente || 'Cliente'
    showSuccessNotification(`Pago procesado: ${tipoTexto} - $${Number(pedido.total).toFixed(2)} (${metodoPago})`)
    
    selectedPedido.value = null
    await loadData()
  } catch (e: any) {
    showErrorNotification(e?.response?.data?.detail || 'Error al procesar pago')
  } finally {
    processingPayment.value = false
  }
}

// Funciones de notificación
const showErrorNotification = (message: string) => {
  error.value = message
  successMessage.value = null
  showNotification.value = true
  setTimeout(() => {
    showNotification.value = false
  }, 5000)
}

const showSuccessNotification = (message: string) => {
  successMessage.value = message
  error.value = null
  showNotification.value = true
  setTimeout(() => {
    showNotification.value = false
  }, 3000)
}

// Seleccionar pedido para mostrar detalles
const selectPedido = async (pedido: PedidoResponse) => {
  if (selectedPedido.value?.id === pedido.id) {
    selectedPedido.value = null
    return
  }
  
  // Cargar detalles completos del pedido
  const pedidoCompleto = await getPedidoCompleto(pedido.id)
  if (pedidoCompleto) {
    selectedPedido.value = pedidoCompleto
  }
}

// Cerrar modal
const closeModal = () => {
  selectedPedido.value = null
}
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
          <h1 class="text-2xl font-bold text-white">Sistema de Caja</h1>
          <p class="text-xs text-blue-100">La Hidrocálida</p>
        </div>
      </div>
      <div class="flex items-center gap-4 text-sm">
        <div class="bg-white bg-opacity-10 px-4 py-2 rounded-lg backdrop-blur">
          <p class="text-white text-xs">Total Pendiente Pago</p>
          <p class="text-[#FDB700] font-bold text-lg">$ {{ totalPendientesPago.toFixed(2) }}</p>
        </div>
        <div class="bg-white bg-opacity-10 px-4 py-2 rounded-lg backdrop-blur">
          <p class="text-white text-xs">Usuario</p>
          <p class="text-blue-200 font-semibold">{{ auth.user?.nombre }}</p>
        </div>
        <button 
          @click="auth.logout()" 
          class="px-4 py-2 rounded-lg bg-red-500 text-white font-semibold hover:bg-red-600 transition shadow-md hover:shadow-lg"
        >
          🚪 Salir
        </button>
      </div>
    </header>

    <!-- Navigation Tabs -->
    <div class="bg-gray-50 border-b border-gray-200">
      <div class="px-6 py-4">
        <div class="flex gap-1 bg-white rounded-lg p-1 shadow-sm border">
          <button
            @click="activeTab = 'overview'"
            :class="[
              'flex-1 px-4 py-2 rounded-md font-medium transition-all text-sm',
              activeTab === 'overview' 
                ? 'bg-[#00126D] text-white shadow-md' 
                : 'text-gray-600 hover:text-gray-800 hover:bg-gray-50'
            ]"
          >
            📊 Overview General
          </button>
          <button
            @click="activeTab = 'pendientes'"
            :class="[
              'flex-1 px-4 py-2 rounded-md font-medium transition-all text-sm flex items-center justify-center gap-2',
              activeTab === 'pendientes' 
                ? 'bg-[#00126D] text-white shadow-md' 
                : 'text-gray-600 hover:text-gray-800 hover:bg-gray-50'
            ]"
          >
            <span>💳 Pendientes de Pago</span>
            <span v-if="pedidosPendientes.length > 0" :class="[
              'px-2 py-1 rounded-full text-xs font-bold',
              activeTab === 'pendientes' ? 'bg-white text-[#00126D]' : 'bg-red-500 text-white'
            ]">
              {{ pedidosPendientes.length }}
            </span>
          </button>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <main class="flex-1 p-6 pt-0">
      <div v-if="loading" class="text-center py-8 text-gray-600 font-medium">
        Cargando datos...
      </div>

      <!-- Tab Overview General -->
      <div v-else-if="activeTab === 'overview'" class="space-y-6">
        <!-- Estadísticas -->
        <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
          <div class="bg-yellow-100 border border-yellow-300 rounded-lg p-4 text-center">
            <div class="text-2xl font-bold text-yellow-700">{{ estadisticasOverview.pendiente }}</div>
            <div class="text-xs text-yellow-600 font-medium">PENDIENTE</div>
          </div>
          <div class="bg-orange-100 border border-orange-300 rounded-lg p-4 text-center">
            <div class="text-2xl font-bold text-orange-700">{{ estadisticasOverview.preparando }}</div>
            <div class="text-xs text-orange-600 font-medium">PREPARANDO</div>
          </div>
          <div class="bg-green-100 border border-green-300 rounded-lg p-4 text-center">
            <div class="text-2xl font-bold text-green-700">{{ estadisticasOverview.listo }}</div>
            <div class="text-xs text-green-600 font-medium">LISTO</div>
          </div>
          <div class="bg-blue-100 border border-blue-300 rounded-lg p-4 text-center">
            <div class="text-2xl font-bold text-blue-700">{{ estadisticasOverview.entregado }}</div>
            <div class="text-xs text-blue-600 font-medium">ENTREGADO</div>
          </div>
          <div class="bg-purple-100 border border-purple-300 rounded-lg p-4 text-center">
            <div class="text-2xl font-bold text-purple-700">{{ estadisticasOverview.cuenta_solicitada }}</div>
            <div class="text-xs text-purple-600 font-medium">CUENTA SOLICITADA</div>
          </div>
          <div class="bg-gray-100 border border-gray-300 rounded-lg p-4 text-center">
            <div class="text-2xl font-bold text-gray-700">{{ estadisticasOverview.pagado }}</div>
            <div class="text-xs text-gray-600 font-medium">PAGADO</div>
          </div>
          <div class="bg-red-100 border border-red-300 rounded-lg p-4 text-center">
            <div class="text-2xl font-bold text-red-700">{{ estadisticasOverview.cancelado }}</div>
            <div class="text-xs text-red-600 font-medium">CANCELADO</div>
          </div>
        </div>

        <!-- Lista de pedidos activos -->
        <div>
          <h3 class="text-lg font-bold text-gray-700 mb-4">Pedidos Activos ({{ pedidosActivos.length }})</h3>
          <div v-if="pedidosActivos.length === 0" class="text-center py-8">
            <div class="text-4xl mb-2">🎉</div>
            <p class="text-gray-600">No hay pedidos activos</p>
          </div>
          <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            <div 
              v-for="pedido in pedidosActivos" 
              :key="pedido.id"
              class="bg-white border border-gray-200 rounded-lg p-4 shadow-sm"
            >
              <div class="flex items-center justify-between mb-3">
                <div class="flex items-center gap-2">
                  <span class="text-xl">{{ getTipoOrdenEmoji(pedido.tipo_orden) }}</span>
                  <span class="text-lg font-bold text-[#00126D]">{{ pedido.numero_display }}</span>
                </div>
                <div :class="[getEstadoColor(pedido.estado), 'text-white px-2 py-1 rounded text-xs font-bold']">
                  {{ getEstadoTexto(pedido.estado) }}
                </div>
              </div>
              <div class="text-sm">
                <div v-if="pedido.mesa" class="text-blue-600 font-medium">🪑 Mesa {{ pedido.mesa }}</div>
                <div v-if="pedido.nombre_cliente" class="text-green-600 font-medium">👤 {{ pedido.nombre_cliente }}</div>
                <div class="text-[#FDB700] font-bold mt-1">$ {{ Number(pedido.total).toFixed(2) }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Tab Pendientes de Pago -->
      <div v-else-if="activeTab === 'pendientes'">
        <div v-if="pedidosPendientes.length === 0" class="text-center py-12">
          <div class="text-6xl mb-4">💳</div>
          <h2 class="text-2xl font-bold text-gray-600 mb-2">Sin pedidos pendientes de pago</h2>
          <p class="text-gray-500">Todos los pedidos están pagados</p>
        </div>

        <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          <div 
            v-for="pedido in pedidosPendientes" 
            :key="pedido.id"
            @click="selectPedido(pedido)"
            class="bg-white border-2 border-gray-200 rounded-2xl p-6 hover:shadow-xl hover:border-[#FDB700] cursor-pointer transition-all hover:scale-105 group"
          >
            <!-- Header del pedido -->
            <div class="flex items-center justify-between mb-4">
              <div class="flex items-center gap-3">
                <div class="text-3xl">{{ getTipoOrdenEmoji(pedido.tipo_orden) }}</div>
                <div class="text-2xl font-black text-[#00126D]">{{ pedido.numero_display }}</div>
              </div>
              <div class="bg-purple-500 text-white px-3 py-1 rounded-full text-xs font-bold">
                CUENTA SOLICITADA
              </div>
            </div>

            <!-- Información de mesa/cliente -->
            <div class="mb-4">
              <div v-if="pedido.mesa" class="bg-blue-500 text-white px-3 py-1 rounded-full text-sm font-bold text-center mb-2">
                🪑 MESA {{ pedido.mesa }}
              </div>
              <div v-if="pedido.nombre_cliente && pedido.tipo_orden === 'llevar'" class="bg-green-500 text-white px-3 py-1 rounded-full text-sm font-bold text-center">
                📦 {{ pedido.nombre_cliente }}
              </div>
            </div>

            <!-- Total -->
            <div class="border-t pt-4">
              <div class="text-center">
                <div class="text-sm text-gray-600 mb-1">Total a cobrar</div>
                <div class="text-3xl font-black text-[#FDB700]">$ {{ Number(pedido.total).toFixed(2) }}</div>
              </div>
            </div>

            <!-- Indicador de hover -->
            <div class="mt-4 text-center text-xs text-gray-500 group-hover:text-[#00126D] transition">
              👆 Clic para procesar pago
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- Modal de procesamiento de pago - Minimalista -->
    <div 
      v-if="selectedPedido" 
      class="fixed inset-0 flex items-center justify-center z-50 p-4"
      @click.self="closeModal"
    >
      <div class="bg-white rounded-lg max-w-md w-full shadow-lg border border-gray-200">
        <!-- Header simple -->
        <div class="px-6 py-4 border-b border-gray-200">
          <div class="flex items-center justify-between">
            <h2 class="text-lg font-semibold text-gray-800">
              Procesar Pago - Pedido #{{ selectedPedido.numero_display }}
            </h2>
            <button 
              @click="closeModal" 
              class="text-gray-400 hover:text-gray-600 text-xl"
            >
              ×
            </button>
          </div>
        </div>

        <!-- Contenido del modal -->
        <div class="p-6">
          <!-- Info básica -->
          <div class="mb-4">
            <div v-if="selectedPedido.mesa" class="text-center bg-blue-100 text-blue-800 px-3 py-2 rounded-lg mb-3 font-medium">
              🪑 Mesa {{ selectedPedido.mesa }}
            </div>
            <div v-if="selectedPedido.nombre_cliente && selectedPedido.tipo_orden === 'llevar'" class="text-center bg-green-100 text-green-800 px-3 py-2 rounded-lg mb-3 font-medium">
              📦 {{ selectedPedido.nombre_cliente }}
            </div>
          </div>
            
          <!-- Lista de artículos simple -->
          <div v-if="selectedPedido.articulos_pedido && selectedPedido.articulos_pedido.length > 0" class="mb-4">
            <h4 class="text-sm font-medium text-gray-700 mb-2">Artículos:</h4>
            <div class="bg-gray-50 rounded-lg p-3 max-h-40 overflow-y-auto">
              <div 
                v-for="articulo in selectedPedido.articulos_pedido" 
                :key="articulo.id"
                class="flex justify-between items-start py-1 text-sm"
              >
                <div class="flex-1">
                  <div class="font-medium">{{ articulo.platillo?.nombre || 'Producto' }}</div>
                  <div v-if="articulo.modificaciones" class="text-gray-500 text-xs">
                    {{ articulo.modificaciones }}
                  </div>
                </div>
                <div class="text-center px-2">
                  <span class="text-gray-600">x{{ articulo.cantidad }}</span>
                </div>
                <div class="text-right text-orange-600 font-medium">
                  ${{ Number(articulo.precio_cobrado).toFixed(2) }}
                </div>
              </div>
            </div>
          </div>
            
          <!-- Total -->
          <div class="text-center bg-orange-100 text-orange-800 px-4 py-3 rounded-lg mb-6">
            <div class="text-sm">Total a cobrar</div>
            <div class="text-2xl font-bold">$ {{ Number(selectedPedido.total).toFixed(2) }}</div>
          </div>

          <!-- Botones de pago simples -->
          <div class="space-y-2">
            <button
              @click="procesarPago(selectedPedido, 'efectivo')"
              :disabled="processingPayment"
              class="w-full py-3 bg-green-600 hover:bg-green-700 text-white font-medium rounded-lg transition-all disabled:opacity-50"
            >
              {{ processingPayment ? 'Procesando...' : '💵 Efectivo' }}
            </button>
            <button
              @click="procesarPago(selectedPedido, 'tarjeta')"
              :disabled="processingPayment"
              class="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-all disabled:opacity-50"
            >
              {{ processingPayment ? 'Procesando...' : '💳 Tarjeta' }}
            </button>
            <button
              @click="procesarPago(selectedPedido, 'transferencia')"
              :disabled="processingPayment"
              class="w-full py-3 bg-purple-600 hover:bg-purple-700 text-white font-medium rounded-lg transition-all disabled:opacity-50"
            >
              {{ processingPayment ? 'Procesando...' : '📱 Transferencia' }}
            </button>
          </div>

          <!-- Botón cancelar simple -->
          <button
            @click="closeModal"
            :disabled="processingPayment"
            class="w-full mt-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 font-medium rounded-lg transition-all disabled:opacity-50"
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>

    <!-- Notification Toast -->
    <div v-if="showNotification" class="fixed inset-0 flex items-center justify-center z-50 pointer-events-none">
      <!-- Error Notification -->
      <div v-if="error" class="bg-red-50 border-l-4 border-red-500 rounded-xl p-6 max-w-md w-full mx-4 shadow-2xl pointer-events-auto animate-in fade-in slide-in-from-top-5">
        <div class="flex items-start gap-4">
          <div class="text-3xl">❌</div>
          <div>
            <h3 class="font-bold text-red-700 text-lg mb-1">Error</h3>
            <p class="text-red-600">{{ error }}</p>
          </div>
          <button @click="showNotification = false" class="text-red-400 hover:text-red-600 text-2xl leading-none ml-auto">×</button>
        </div>
      </div>

      <!-- Success Notification -->
      <div v-if="successMessage" class="bg-green-50 border-l-4 border-green-500 rounded-xl p-6 max-w-md w-full mx-4 shadow-2xl pointer-events-auto animate-in fade-in slide-in-from-top-5">
        <div class="flex items-start gap-4">
          <div class="text-3xl">✅</div>
          <div>
            <h3 class="font-bold text-green-700 text-lg mb-1">¡Pago Procesado!</h3>
            <p class="text-green-600">{{ successMessage }}</p>
          </div>
          <button @click="showNotification = false" class="text-green-400 hover:text-green-600 text-2xl leading-none ml-auto">×</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@keyframes slideInFromTop {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-in {
  animation: slideInFromTop 0.3s ease-out;
}

.fade-in {
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.slide-in-from-top-5 {
  animation: slideInFromTop 0.3s ease-out;
}

/* Custom scrollbar for modal */
.custom-scrollbar {
  scrollbar-width: thin;
  scrollbar-color: #cbd5e1 #f1f5f9;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 3px;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

/* Animación de spin para loading */
@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.animate-spin {
  animation: spin 1s linear infinite;
}

/* Efectos de hover mejorados */
.group:hover .group-hover\:scale-105 {
  transform: scale(1.05);
}

/* Transiciones suaves para todos los elementos */
* {
  transition-property: color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter;
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
  transition-duration: 150ms;
}

/* Mejoras para el backdrop del modal */
.backdrop-blur-sm {
  backdrop-filter: blur(4px);
}

/* Sombras personalizadas */
.shadow-2xl {
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
}

.hover\:shadow-xl:hover {
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
}
</style>