<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed } from 'vue'
import { api } from '../api/client'
import { useAuthStore } from '../stores/auth'
import { usePedidosStore } from '../stores/pedidos'
import { useRouter } from 'vue-router'
import { formatElapsed } from '@/utils/dateUtils'
import AppHeader from '@/components/AppHeader.vue'

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
}

const auth = useAuthStore()
const pedidosStore = usePedidosStore()
const router = useRouter()

const error = ref<string | null>(null)
const selectedPedidoId = ref<number | null>(null)
let timer: number | undefined

const pedidosActivos = computed(() => {
  // Mostrar pedidos pendientes, preparando, listo y entregado (incluye los que volvieron a pendiente)
  return pedidosStore.pedidosKDS
    .filter(p => ['pendiente', 'preparando', 'listo', 'entregado'].includes(p.estado))
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
})

// Pedidos recién completados (últimos 20 minutos) para recuperar errores
const pedidosRecienCompletados = computed(() => {
  const hace20Minutos = Date.now() - (20 * 60 * 1000)
  
  return pedidosStore.pedidosKDS
    .filter(p => {
      // Solo pedidos marcados como "listo" en los últimos 20 minutos
      if (p.estado !== 'listo') return false
      
      const tiempoCreacion = new Date(p.fecha_creacion).getTime()
      return tiempoCreacion >= hace20Minutos
    })
    .sort((a, b) => new Date(b.fecha_creacion).getTime() - new Date(a.fecha_creacion).getTime()) // Más recientes primero
})

const selectedPedido = computed(() => {
  return pedidosActivos.value.find(p => p.id === selectedPedidoId.value)
})

// Vista actual: activos, completados o disponibilidad
const vistaActual = ref<'activos' | 'completados' | 'disponibilidad'>('activos')

// Estado para gestión de disponibilidad
const platillos = ref<any[]>([])
const searchPlatillo = ref('')
const loading_platillos = ref(false)

const pedidosMostrados = computed(() => {
  if (vistaActual.value === 'completados') {
    return pedidosRecienCompletados.value
  }
  
  const activos = pedidosActivos.value
  console.log('🔍 Debug pedidosFiltrados:', {
    totalPedidos: pedidosStore.pedidos.length,
    pedidosKDS: pedidosStore.pedidosKDS.length,
    pedidosActivos: activos.length,
    wsConnected: pedidosStore.wsConnected,
    loading: pedidosStore.loading
  })
  
  // Ordenamiento eficiente por prioridad para KDS Manager
  return activos.sort((a, b) => {
    // 1. Por urgencia de tiempo (más antiguos primero)
    const tiempoA = new Date(a.fecha_creacion).getTime()
    const tiempoB = new Date(b.fecha_creacion).getTime()
    const diffA = Date.now() - tiempoA
    const diffB = Date.now() - tiempoB
    
    // 2. Priorizar pedidos urgentes (>10 min) al top
    const urgentA = diffA > 10 * 60 * 1000 // más de 10 min
    const urgentB = diffB > 10 * 60 * 1000
    
    if (urgentA && !urgentB) return -1
    if (!urgentA && urgentB) return 1
    
    // 3. Después por tiempo de creación (más viejo primero)
    if (tiempoA !== tiempoB) return tiempoA - tiempoB
    
    // 4. Por número de pedido como tiebreaker
    return (a.numero_display || '').localeCompare(b.numero_display || '')
  })
})

const loading = computed(() => pedidosStore.loading)

// Función para volver un pedido de listo a preparando (recuperar error)
function recuperarPedido(pedido: any) {
  console.log('🔄 Recuperando pedido marcado por error:', pedido.id)
  updateEstadoPedidoOptimistic(pedido, 'preparando')
}

// Funciones para gestión de disponibilidad
async function cargarPlatillos() {
  if (loading_platillos.value) return
  
  loading_platillos.value = true
  try {
    const response = await api.get('/platillos')
    platillos.value = response.data
    console.log('✅ Platillos cargados:', platillos.value.length)
  } catch (e: any) {
    console.error('❌ Error cargando platillos:', e)
    error.value = 'Error al cargar platillos'
  } finally {
    loading_platillos.value = false
  }
}

// Cambiar disponibilidad de un platillo
async function toggleDisponibilidad(platillo: any) {
  const nuevoEstado = platillo.estado === 'disponible' ? 'no_disponible' : 'disponible'
  const estadoOriginal = platillo.estado
  
  // Optimistic update
  platillo.estado = nuevoEstado
  
  try {
    // Usar el nuevo endpoint específico para disponibilidad
    await api.patch(`/platillos/${platillo.id}/disponibilidad`, { estado: nuevoEstado })
    console.log(`✅ Platillo ${platillo.nombre} cambiado a ${nuevoEstado}`)
    
    // Aquí podríamos agregar notificación WebSocket a meseros
  } catch (e: any) {
    // Revertir cambio si falla
    platillo.estado = estadoOriginal
    console.error('❌ Error al cambiar disponibilidad:', e)
    
    // Mostrar error más específico
    const errorMsg = e?.response?.data?.detail || 'Error al cambiar disponibilidad del platillo'
    error.value = errorMsg
    
    // También mostrar en consola para debugging
    console.error('Error details:', {
      status: e?.response?.status,
      data: e?.response?.data,
      platillo: platillo.nombre,
      nuevoEstado,
      estadoOriginal
    })
  }
}

// Platillos filtrados por búsqueda y agrupados por categoría
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

// Contar disponibles por categoría
function getDisponiblesPorCategoria(categoria: string): { disponibles: number, total: number } {
  const platillosCategoria = platillosPorCategoria.value[categoria] || []
  const disponibles = platillosCategoria.filter(p => p.estado === 'disponible').length
  return { disponibles, total: platillosCategoria.length }
}

function getEstadoStyles(estado: string): string {
  const styles: Record<string, string> = {
    'pendiente': 'bg-red-500 text-white',
    'preparando': 'bg-yellow-500 text-white',
    'listo': 'bg-green-500 text-white',
    'entregado': 'bg-blue-500 text-white'
  }
  return styles[estado] || 'bg-gray-500 text-white'
}

// Funciones de temporizador (copiadas de KDS View)
const timerTick = ref(0)
let timerInterval: number | undefined

function calcularTiempoTranscurrido(fechaCreacion: string) {
  timerTick.value // Forzar re-renderizado
  return formatElapsed(fechaCreacion)
}

function getTiempoColor(fechaCreacion: string) {
  const ahora = new Date()
  const fechaPedido = new Date(fechaCreacion)
  const diferenciaMs = ahora.getTime() - fechaPedido.getTime()
  const minutos = Math.floor(diferenciaMs / (1000 * 60))
  
  if (minutos < 5) return 'bg-green-500 text-white'
  if (minutos < 10) return 'bg-yellow-500 text-white'
  if (minutos < 15) return 'bg-orange-500 text-white'
  return 'bg-red-600 text-white'
}

function getTipoOrdenEmoji(tipo: string) {
  const emojis: Record<string, string> = {
    'aqui': '🍽️',
    'llevar': '📦',
    'uber_eats': '🚗'
  }
  return emojis[tipo] || '📋'
}

function getArticuloStyles(estado: string) {
  switch (estado) {
    case 'pendiente':
      return 'bg-slate-700 text-white hover:bg-slate-600 active:scale-95'
    case 'preparando':
      return 'bg-yellow-600 bg-opacity-50 text-yellow-100 hover:bg-yellow-500 active:scale-95'
    case 'listo':
      return 'bg-green-600 bg-opacity-60 text-green-100 hover:bg-green-500 active:scale-95 border-2 border-green-300'
    default:
      return 'bg-slate-700 text-white hover:bg-slate-600 active:scale-95'
  }
}

function getArticuloIcon(estado: string) {
  switch (estado) {
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

async function updateEstadoPedido(pedidoId: number, nuevoEstado: string) {
  try {
    const success = await pedidosStore.updatePedidoEstado(pedidoId, nuevoEstado)
    if (!success) {
      error.value = pedidosStore.error || 'Error actualizando pedido'
    }
  } catch (e: any) {
    error.value = e?.response?.data?.detail || 'Error actualizando pedido'
  }
}

async function updateEstadoArticulo(articuloId: number, nuevoEstado: string) {
  try {
    const success = await pedidosStore.updateArticuloEstado(articuloId, nuevoEstado)
    if (!success) {
      error.value = pedidosStore.error || 'Error actualizando artículo'
    }
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
  
  // Ciclo: pendiente -> preparando -> listo -> preparando
  let nuevoEstado: string
  switch (articulo.estado_item) {
    case 'pendiente':
      nuevoEstado = 'preparando'
      break
    case 'preparando':
      nuevoEstado = 'listo'
      break
    case 'listo':
      nuevoEstado = 'preparando'
      break
    default:
      nuevoEstado = 'preparando'
  }
  
  updateEstadoArticulo(articulo.id, nuevoEstado)
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

function swipeToPreparando(pedido: Pedido) {
  if (pedido.estado === 'pendiente') {
    updateEstadoPedido(pedido.id, 'preparando')
  }
}

// Función sin updates optimísticos problemáticos - usar store directamente
async function updateEstadoPedidoOptimistic(pedido: any, nuevoEstado: string) {
  try {
    // Usar la función del store directamente sin modificar el objeto local
    const success = await pedidosStore.updatePedidoEstado(pedido.id, nuevoEstado)
    if (!success) {
      error.value = pedidosStore.error || 'Error actualizando pedido'
    }
  } catch (e: any) {
    error.value = e?.response?.data?.detail || 'Error actualizando pedido'
    console.error('❌ Error actualizando pedido:', e)
  }
}

// Función sin updates optimísticos problemáticos - usar store directamente
async function toggleArticuloEstadoOptimistic(articulo: any) {
  // Ciclo: pendiente -> preparando -> listo -> preparando
  let nuevoEstado: string
  switch (articulo.estado_item) {
    case 'pendiente':
      nuevoEstado = 'preparando'
      break
    case 'preparando':
      nuevoEstado = 'listo'
      break
    case 'listo':
      nuevoEstado = 'preparando'
      break
    default:
      nuevoEstado = 'preparando'
  }
  
  try {
    // Usar la función del store directamente sin modificar el objeto local
    const success = await pedidosStore.updateArticuloEstado(articulo.id, nuevoEstado)
    if (!success) {
      error.value = pedidosStore.error || 'Error actualizando artículo'
    }
  } catch (e: any) {
    error.value = e?.response?.data?.detail || 'Error actualizando artículo'
    console.error('❌ Error actualizando artículo:', e)
  }
}

onMounted(async () => {
  if (!auth.isAuthenticated || !['cocina', 'administrador'].includes(auth.user?.rol || '')) {
    router.replace({ name: 'login' })
    return
  }

  console.log('🍳 KDS Manager: Iniciando...')

  try {
    // Cargar datos iniciales
    await pedidosStore.loadInitialData()
    
    // Cargar platillos para gestión de disponibilidad
    await cargarPlatillos()
    
    // Inicializar WebSocket para KDS
    const wsConnected = await pedidosStore.initWebSocket('kds')
    
    if (wsConnected) {
      console.log('✅ KDS Manager: WebSocket conectado, datos en tiempo real activos')
    } else {
      console.warn('⚠️ KDS Manager: WebSocket falló, usando polling como fallback')
      // Fallback: polling cada 3 segundos si WebSocket falla
      timer = window.setInterval(() => {
        pedidosStore.refreshPedidos()
      }, 3000)
    }

    // Inicializar temporizador para actualizar tiempo transcurrido cada segundo
    timerInterval = window.setInterval(() => {
      timerTick.value++
    }, 1000)

  } catch (error) {
    console.error('❌ KDS Manager: Error en inicialización:', error)
  }
})

onUnmounted(() => {
  console.log('👋 KDS Manager: Cleanup...')
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
  <div class="min-h-screen bg-slate-900 text-white">
    <!-- Header con pestañas -->
    <div class="bg-slate-800 p-2 border-b border-slate-600">
      <div class="flex items-center justify-between">
        <h1 class="text-lg font-bold">🍳 Control Rápido</h1>
        <div class="flex items-center gap-3">
          <!-- Pestañas de vista -->
          <button
            @click="vistaActual = 'activos'"
            :class="[
              'px-4 py-2 rounded-lg text-sm font-bold transition-colors',
              vistaActual === 'activos' 
                ? 'bg-blue-600 text-white' 
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            ]"
          >
            🔥 Pedidos Activos ({{ pedidosActivos.length }})
          </button>
          
          <button
            @click="vistaActual = 'completados'"
            :class="[
              'px-4 py-2 rounded-lg text-sm font-bold transition-colors',
              vistaActual === 'completados' 
                ? 'bg-green-600 text-white' 
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            ]"
          >
            ✅ Recién Completados ({{ pedidosRecienCompletados.length }})
          </button>
          
          <button
            @click="vistaActual = 'disponibilidad'"
            :class="[
              'px-4 py-2 rounded-lg text-sm font-bold transition-colors',
              vistaActual === 'disponibilidad' 
                ? 'bg-purple-600 text-white' 
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            ]"
          >
            🍽️ Disponibilidad
          </button>
          
          <!-- Indicador conexión -->
          <div :class="pedidosStore.wsConnected ? 'text-green-400' : 'text-yellow-400'">
            {{ pedidosStore.wsConnected ? '🟢' : '🟡' }}
          </div>
        </div>
      </div>
    </div>

    <!-- Lista ultra-optimizada para tablet/móvil -->
    <div class="p-4">
      <div v-if="loading" class="text-center py-20">
        <div class="text-6xl mb-4">⏳</div>
        <div class="text-2xl font-bold">Cargando...</div>
      </div>
      
      <!-- Vista de Disponibilidad -->
      <div v-if="vistaActual === 'disponibilidad'" class="space-y-6">
        <!-- Header con búsqueda -->
        <div class="bg-slate-800 rounded-lg p-4">
          <div class="flex items-center gap-4">
            <h2 class="text-xl font-bold text-purple-400">🍽️ Gestión de Disponibilidad</h2>
            <div class="flex-1">
              <input
                v-model="searchPlatillo"
                type="text"
                placeholder="🔍 Buscar platillo..."
                class="w-full px-4 py-2 bg-slate-700 text-white rounded-lg border border-slate-600 focus:border-purple-400 focus:outline-none"
              />
            </div>
          </div>
        </div>

        <!-- Loading state para platillos -->
        <div v-if="loading_platillos" class="text-center py-20">
          <div class="text-6xl mb-4">⏳</div>
          <div class="text-2xl font-bold">Cargando platillos...</div>
        </div>

        <!-- Lista de platillos por categoría -->
        <div v-else-if="Object.keys(platillosPorCategoria).length === 0" class="text-center py-20">
          <div class="text-6xl mb-4">🍽️</div>
          <div class="text-2xl font-bold">No se encontraron platillos</div>
          <div class="text-gray-400 mt-2">Verifica tu búsqueda o contacta al administrador</div>
        </div>

        <div v-else class="space-y-4">
          <div
            v-for="(platillosCategoria, categoria) in platillosPorCategoria"
            :key="categoria"
            class="bg-slate-800 rounded-lg p-4"
          >
            <!-- Header de categoría -->
            <div class="flex items-center justify-between mb-4 pb-2 border-b border-slate-600">
              <h3 class="text-lg font-bold text-white">
                {{ categoria }}
              </h3>
              <div class="text-sm text-gray-400">
                {{ getDisponiblesPorCategoria(categoria).disponibles }}/{{ getDisponiblesPorCategoria(categoria).total }} disponibles
              </div>
            </div>

            <!-- Lista de platillos de la categoría -->
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              <div
                v-for="platillo in platillosCategoria"
                :key="platillo.id"
                :class="[
                  'p-4 rounded-lg border-2 transition-all',
                  platillo.estado === 'disponible'
                    ? 'bg-green-900 border-green-600 text-green-100'
                    : 'bg-red-900 border-red-600 text-red-100'
                ]"
              >
                <div class="flex items-center justify-between">
                  <div class="flex-1">
                    <div class="font-bold text-sm sm:text-base">
                      {{ platillo.nombre }}
                    </div>
                    <div class="text-xs text-gray-400 mt-1">
                      ${{ Number(platillo.precio).toFixed(2) }}
                    </div>
                  </div>
                  
                  <!-- Switch táctil grande -->
                  <button
                    @click="toggleDisponibilidad(platillo)"
                    :class="[
                      'relative w-16 h-8 rounded-full transition-colors',
                      platillo.estado === 'disponible' ? 'bg-green-600' : 'bg-red-600'
                    ]"
                  >
                    <div
                      :class="[
                        'absolute top-1 w-6 h-6 bg-white rounded-full transition-transform',
                        platillo.estado === 'disponible' ? 'translate-x-9' : 'translate-x-1'
                      ]"
                    />
                  </button>
                </div>
                
                <!-- Estado visual -->
                <div class="mt-2 text-center text-xs font-bold">
                  {{ platillo.estado === 'disponible' ? '🟢 DISPONIBLE' : '🔴 NO DISPONIBLE' }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Vista de pedidos (activos y completados) -->
      <div v-else-if="pedidosMostrados.length === 0" class="text-center py-20">
        <div class="text-6xl mb-4">{{ vistaActual === 'completados' ? '📋' : '✨' }}</div>
        <div class="text-2xl font-bold">
          {{ vistaActual === 'completados' ? 'No hay pedidos completados recientes' : '¡Todo listo!' }}
        </div>
        <div v-if="vistaActual === 'completados'" class="text-gray-400 mt-2">
          Los pedidos aparecen aquí durante 20 minutos después de marcarlos como listos
        </div>
      </div>
      
      <!-- Layout de lista vertical optimizado -->
      <div v-else class="space-y-4">
        <div
          v-for="p in pedidosMostrados"
          :key="p.id"
          :class="[
            'rounded-xl p-5 transition-all duration-200 shadow-lg border-4 border-white border-opacity-20',
            getEstadoStyles(p.estado)
          ]"
        >
          <!-- Header responsive - diferente layout para móvil -->
          <div class="space-y-3">
            <!-- Fila 1: Info básica optimizada -->
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-3">
                <!-- Emoji más grande -->
                <span class="text-4xl sm:text-5xl">{{ getTipoOrdenEmoji(p.tipo_orden) }}</span>
                <!-- Mesa/Nombre prominente en desktop -->
                <div class="hidden sm:block">
                  <span v-if="p.mesa" class="text-2xl font-black text-white">MESA {{ p.mesa }}</span>
                  <span v-else-if="p.nombre_cliente" class="text-xl font-black text-white">{{ p.nombre_cliente.toUpperCase() }}</span>
                  <span v-else class="text-lg font-bold text-yellow-300">PARA LLEVAR</span>
                </div>
                <!-- Número discreto -->
                <span class="text-sm font-medium opacity-75">#{{ p.numero_display }}</span>
              </div>
              
              <!-- Temporizador más prominente -->
              <span :class="['text-sm sm:text-lg font-black px-3 py-2 rounded-full border-2 border-white border-opacity-50', getTiempoColor(p.fecha_creacion)]">
                {{ calcularTiempoTranscurrido(p.fecha_creacion) }}
              </span>
            </div>
            
            <!-- Fila 2: Mesa/Cliente en móvil + Acción principal - Layout fijo -->
            <div class="flex items-center justify-between">
              <!-- Mesa/Nombre GRANDE en móvil -->
              <div class="min-w-0 flex-shrink-0 sm:hidden">
                <div v-if="p.mesa" class="text-xl font-black text-white">MESA {{ p.mesa }}</div>
                <div v-else-if="p.nombre_cliente" class="text-lg font-black text-white truncate max-w-32">{{ p.nombre_cliente.toUpperCase() }}</div>
                <div v-else class="text-base font-bold text-yellow-300">PARA LLEVAR</div>
              </div>
              
              <!-- Botones según la vista actual -->
              <div v-if="vistaActual === 'completados'">
                <!-- Vista de completados: botón para recuperar -->
                <button
                  @click="recuperarPedido(p)"
                  class="bg-orange-600 hover:bg-orange-700 text-white font-black py-2 px-4 sm:py-3 sm:px-6 rounded-lg text-sm sm:text-lg transition-colors w-full sm:w-auto sm:min-w-40"
                >
                  🔄 RECUPERAR
                </button>
              </div>
              
              <div v-else>
                <!-- Vista activos: botones normales -->
                <button
                  v-if="p.estado === 'pendiente'"
                  @click="updateEstadoPedidoOptimistic(p, 'preparando')"
                  class="bg-yellow-600 hover:bg-yellow-700 text-white font-black py-2 px-4 sm:py-3 sm:px-6 rounded-lg text-sm sm:text-lg transition-colors w-full sm:w-auto sm:min-w-32"
                >
                  🔥 INICIAR
                </button>
                
                <button
                  v-else-if="p.estado === 'preparando'"
                  @click="updateEstadoPedidoOptimistic(p, 'listo')"
                  class="bg-green-600 hover:bg-green-700 text-white font-black py-2 px-4 sm:py-3 sm:px-6 rounded-lg text-sm sm:text-lg transition-colors w-full sm:w-auto sm:min-w-32"
                >
                  ✅ LISTO
                </button>
                
                <button
                  v-else-if="p.estado === 'listo'"
                  @click="updateEstadoPedidoOptimistic(p, 'entregado')"
                  class="bg-blue-600 hover:bg-blue-700 text-white font-black py-2 px-4 sm:py-3 sm:px-6 rounded-lg text-sm sm:text-lg transition-colors w-full sm:w-auto sm:min-w-32"
                >
                  📤 ENTREGAR
                </button>
                
                <div v-else class="text-green-400 font-bold text-sm sm:text-lg py-2 px-4 sm:py-3 sm:px-6 text-center w-full sm:w-auto">
                  ✓ ENTREGADO
                </div>
              </div>
            </div>
          </div>

          <!-- Artículos táctiles para marcar individualmente - TEXTO GRANDE -->
          <div v-if="p.estado === 'preparando'" class="grid grid-cols-1 gap-3">
            <div
              v-for="articulo in ordenarArticulosPorEstado(p.articulos_pedido || [])"
              :key="articulo.id"
              :class="[
                'p-4 rounded-lg flex items-center justify-between transition-all cursor-pointer border-2 border-white border-opacity-20',
                getArticuloStyles(articulo.estado_item)
              ]"
              @click="toggleArticuloEstadoOptimistic(articulo)"
            >
              <div class="flex-1">
                <!-- Platillo principal - TEXTO MUY GRANDE para tablet -->
                <div class="font-black text-lg sm:text-xl lg:text-2xl leading-tight">
                  {{ articulo.cantidad }}x {{ articulo.platillo?.kds_name || articulo.platillo?.nombre || 'Platillo' }}
                </div>
                <!-- Modificaciones - TEXTO GRANDE y legible -->
                <div v-if="articulo.modificaciones" class="text-base sm:text-lg lg:text-xl font-bold mt-2 bg-yellow-900 bg-opacity-50 p-2 rounded border-l-4 border-yellow-400 leading-snug">
                  {{ articulo.modificaciones }}
                </div>
              </div>
              <!-- Ícono más grande -->
              <div class="text-3xl sm:text-4xl font-bold ml-3">
                {{ getArticuloIcon(articulo.estado_item) }}
              </div>
            </div>
          </div>
          
          <!-- Solo mostrar resumen para otros estados -->
          <div v-else class="text-sm opacity-75">
            {{ p.articulos_pedido?.length || 0 }} artículos
            <span v-if="p.estado === 'listo'">
              - {{ (p.articulos_pedido || []).filter(a => a.estado_item === 'listo').length }} listos
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
</style>
