<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { usePedidosStore } from '../stores/pedidos'
import type { PedidoResponse } from '../types'
import AppHeader from '@/components/AppHeader.vue'
import api from '@/api/client'
import printService from '@/services/printService'

const router = useRouter()
const auth = useAuthStore()
const pedidosStore = usePedidosStore()

// Referencias reactivas
const activeTab = ref<'overview' | 'pendientes' | 'propinas'>('overview')
const selectedPedido = ref<PedidoResponse | null>(null)
const processingPayment = ref(false)
const successMessage = ref<string | null>(null)
const showNotification = ref(false)
const error = ref<string | null>(null)

// Estados para calculadora de efectivo
const showEfectivoCalculator = ref(false)
const efectivoRecibido = ref<string>('')
const cambioCalculado = ref<number>(0)

// Estados para propinas
const propinaEfectivo = ref<string>('')
const propinaTarjeta = ref<string>('')

// Estados para modal de propina tarjeta/transferencia
const showPropinaTarjetaModal = ref(false)
const metodoPagoSeleccionado = ref<'tarjeta' | 'transferencia' | null>(null)

// Estados para reporte de propinas
const reportePropinas = ref<any>(null)
const detallePropinas = ref<any[]>([])
const loadingPropinas = ref(false)

// Estados para búsqueda y mapa de mesas
const searchQuery = ref<string>('')
const showMesaMap = ref(false)

let timer: number | undefined

// Validar que el usuario tenga permisos
onMounted(async () => {
  if (!auth.isAuthenticated || !['cajero', 'administrador'].includes(auth.user?.rol || '')) {
    router.replace({ name: 'login' })
    return
  }

  console.log('💰 Caja View: Iniciando...')

  try {
    // Cargar datos iniciales
    await pedidosStore.loadInitialData()
    
    // Inicializar WebSocket para caja
    const wsConnected = await pedidosStore.initWebSocket('caja')
    
    if (wsConnected) {
      console.log('✅ Caja View: WebSocket conectado, datos en tiempo real activos')
    } else {
      console.warn('⚠️ Caja View: WebSocket falló, usando polling como fallback')
      // Fallback: polling cada 5 segundos si WebSocket falla
      timer = window.setInterval(() => {
        pedidosStore.refreshPedidos()
      }, 5000)
    }
  } catch (error) {
    console.error('❌ Caja View: Error en inicialización:', error)
  }
})

onUnmounted(() => {
  console.log('👋 Caja View: Cleanup...')
  if (timer) {
    clearInterval(timer)
  }
  // No desconectamos el WebSocket aquí porque puede ser usado por otras vistas
})


// Funciones para reporte de propinas
const cargarReportePropinas = async (fecha?: string) => {
  loadingPropinas.value = true
  try {
    const params = fecha ? { fecha } : {}
    const [reporteRes, detalleRes] = await Promise.all([
      api.get('/propinas/reporte', { params }),
      api.get('/propinas/detalle', { params })
    ])
    reportePropinas.value = reporteRes.data
    detallePropinas.value = detalleRes.data
  } catch (error) {
    console.error('Error cargando reporte de propinas:', error)
    showErrorNotification('Error al cargar reporte de propinas')
  } finally {
    loadingPropinas.value = false
  }
}

// Watch para cargar reporte cuando se activa la pestaña
watch(activeTab, (newTab) => {
  if (newTab === 'propinas') {
    cargarReportePropinas()
  }
})

// Computadas para estadísticas
const totalPendientesPago = computed(() => {
  return pedidosStore.pedidosPendientesPago.reduce((sum, pedido) => sum + Number(pedido.total), 0)
})

const estadisticasOverview = computed(() => {
  return pedidosStore.estadisticasPedidos
})

// Computadas para propinas
const propinaEfectivoNum = computed(() => parseFloat(propinaEfectivo.value) || 0)
const propinaTarjetaNum = computed(() => parseFloat(propinaTarjeta.value) || 0)
const propinaTotal = computed(() => propinaEfectivoNum.value + propinaTarjetaNum.value)
const totalConPropina = computed(() => {
  if (!selectedPedido.value) return 0
  return Number(selectedPedido.value.total) + propinaTotal.value
})

const pedidosActivos = computed(() => {
  let pedidos = [...pedidosStore.pedidosCaja]
  
  // Filtrar por búsqueda (mesa o cliente)
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase().trim()
    pedidos = pedidos.filter(pedido => 
      (pedido.mesa && pedido.mesa.includes(query)) ||
      (pedido.nombre_cliente && pedido.nombre_cliente.toLowerCase().includes(query)) ||
      pedido.numero_display.includes(query)
    )
  }
  
  return pedidos
})

// Computed para pedidos pendientes de pago con filtro y ordenamiento
const pedidosPendientes = computed(() => {
  let pedidos = [...pedidosStore.pedidosPendientesPago]
  
  // Filtrar por búsqueda (mesa o cliente)
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase().trim()
    pedidos = pedidos.filter(pedido => 
      (pedido.mesa && pedido.mesa.includes(query)) ||
      (pedido.nombre_cliente && pedido.nombre_cliente.toLowerCase().includes(query)) ||
      pedido.numero_display.includes(query)
    )
  }
  
  // Ordenar por fecha de creación (más viejos primero)
  return pedidos.sort((a, b) => 
    new Date(a.fecha_creacion).getTime() - new Date(b.fecha_creacion).getTime()
  )
})

// Layout de mesas para el mapa (igual que en mesero)
const mesasLayout = [
  ['11', '21', '31'],
  ['12', '22', '32'],
  ['13', '23', '33'],
  ['14', '24', '34'],
  ['15', '25', '35']
]

// Computed para estado de mesas
const mesasOcupadas = computed(() => {
  const ocupadas = new Set<string>()
  
  // Mesas con pedidos activos (no pagados ni cancelados)
  pedidosStore.pedidos.forEach(pedido => {
    if (pedido.mesa && !['pagado', 'cancelado'].includes(pedido.estado)) {
      ocupadas.add(pedido.mesa)
    }
  })
  
  return ocupadas
})

// Obtener estado de una mesa específica
const getMesaEstado = (numeroMesa: string) => {
  if (!mesasOcupadas.value.has(numeroMesa)) return 'libre'
  
  // Buscar el pedido más reciente de esta mesa
  const pedidosMesa = pedidosStore.pedidos.filter(p => p.mesa === numeroMesa && !['pagado', 'cancelado'].includes(p.estado))
  if (pedidosMesa.length === 0) return 'libre'
  
  // Obtener el estado más avanzado
  const ultimoPedido = pedidosMesa.sort((a, b) => 
    new Date(b.fecha_creacion).getTime() - new Date(a.fecha_creacion).getTime()
  )[0]
  
  return ultimoPedido.estado
}

// Obtener clase CSS para el estado de la mesa (colores iguales a las estadísticas)
const getMesaClase = (numeroMesa: string) => {
  const estado = getMesaEstado(numeroMesa)
  
  const clases = {
    'libre': 'bg-gray-100 border-gray-200 text-gray-600 hover:bg-gray-200',
    'pendiente': 'bg-yellow-100 border-yellow-200 text-yellow-700',
    'preparando': 'bg-orange-100 border-orange-200 text-orange-700', 
    'listo': 'bg-green-100 border-green-200 text-green-700',
    'entregado': 'bg-blue-100 border-blue-200 text-blue-700',
    'cuenta_solicitada': 'bg-purple-100 border-purple-200 text-purple-700 animate-pulse'
  }
  
  return clases[estado as keyof typeof clases] || clases.libre
}

// Buscar mesa específica
const buscarMesa = (numeroMesa: string) => {
  searchQuery.value = numeroMesa
  if (activeTab.value !== 'pendientes') {
    activeTab.value = 'pendientes'
  }
}


// Manejar click en mesa según su estado
const handleMesaClick = (numeroMesa: string) => {
  const estadoMesa = getMesaEstado(numeroMesa)
  
  // Mesa libre - no hacer nada
  if (estadoMesa === 'libre') {
    return
  }
  
  // Buscar el pedido más reciente de esta mesa
  const pedidosMesa = pedidosStore.pedidos.filter(p => 
    p.mesa === numeroMesa && !['pagado', 'cancelado'].includes(p.estado)
  )
  
  if (pedidosMesa.length === 0) return
  
  const ultimoPedido = pedidosMesa.sort((a, b) => 
    new Date(b.fecha_creacion).getTime() - new Date(a.fecha_creacion).getTime()
  )[0]
  
  // Si es cuenta solicitada - ir directo a cobrar
  if (ultimoPedido.estado === 'cuenta_solicitada') {
    activeTab.value = 'pendientes'
    searchQuery.value = numeroMesa
    // Pequeño delay para asegurar que se filtre antes de abrir modal
    nextTick(() => {
      selectedPedido.value = ultimoPedido
    })
    return
  }
  
  // Para cualquier otro estado - mostrar detalles del pedido
  showPedidoDetails(ultimoPedido)
}

// Estado reactivo para modal de detalles
const showDetailsModal = ref(false)
const selectedPedidoDetails = ref<PedidoResponse | null>(null)

// Estado para modal de confirmación de cancelación
const showCancelConfirmModal = ref(false)
const pedidoACancelar = ref<PedidoResponse | null>(null)

// Mostrar detalles del pedido
const showPedidoDetails = (pedido: PedidoResponse) => {
  selectedPedidoDetails.value = pedido
  showDetailsModal.value = true
}

// Cerrar modal de detalles
const closeDetailsModal = () => {
  showDetailsModal.value = false
  selectedPedidoDetails.value = null
}

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

// Obtener detalles del pedido completo desde el store
const getPedidoCompleto = async (pedidoId: number) => {
  // Los pedidos ya están cargados en el store con todos sus detalles
  const pedido = pedidosStore.pedidos.find(p => p.id === pedidoId)
  if (pedido) {
    return pedido
  } else {
    showErrorNotification('Pedido no encontrado')
    return null
  }
}

// Procesar pago
const procesarPago = async (pedido: PedidoResponse, metodoPago: 'efectivo' | 'tarjeta' | 'transferencia') => {
  if (metodoPago === 'efectivo') {
    // Mostrar calculadora de efectivo
    showEfectivoCalculator.value = true
    efectivoRecibido.value = ''
    cambioCalculado.value = 0
    // Resetear propina tarjeta ya que no aplica para efectivo
    propinaTarjeta.value = ''
    return
  }
  
  // Para tarjeta y transferencia, mostrar modal de propina primero
  metodoPagoSeleccionado.value = metodoPago
  propinaTarjeta.value = '' // Resetear propina anterior
  showPropinaTarjetaModal.value = true
}

// Finalizar pago (usado por todos los métodos)
const finalizarPago = async (
  pedido: PedidoResponse, 
  metodoPago: 'efectivo' | 'tarjeta' | 'transferencia',
  propinaEfectivoVal: number = 0,
  propinaTarjetaVal: number = 0
) => {
  processingPayment.value = true
  try {
    // Usar el store para actualizar el pedido
    const success = await pedidosStore.updatePedidoEstado(
      pedido.id, 
      'pagado', 
      metodoPago, 
      propinaEfectivoVal, 
      propinaTarjetaVal
    )
    
    if (success) {
      const tipoTexto = pedido.mesa ? `Mesa ${pedido.mesa}` : pedido.nombre_cliente || 'Cliente'
      const totalConPropina = Number(pedido.total) + propinaEfectivoVal + propinaTarjetaVal
      let mensaje = `Pago procesado: ${tipoTexto} - $${totalConPropina.toFixed(2)} (${metodoPago})`
      
      if (propinaEfectivoVal > 0 || propinaTarjetaVal > 0) {
        mensaje += ` (Propina: $${(propinaEfectivoVal + propinaTarjetaVal).toFixed(2)})`
      }
      
      if (metodoPago === 'efectivo' && parseFloat(efectivoRecibido.value) > totalConPropina) {
        mensaje += ` - Cambio: $${cambioCalculado.value.toFixed(2)}`
      }
      
      showSuccessNotification(mensaje)
      
      // Resetear estados
      selectedPedido.value = null
      showEfectivoCalculator.value = false
      efectivoRecibido.value = ''
      cambioCalculado.value = 0
      propinaEfectivo.value = ''
      propinaTarjeta.value = ''
      
      // Limpiar filtro después de acción completada
      searchQuery.value = ''
    } else {
      showErrorNotification(pedidosStore.error || 'Error al procesar pago')
    }
  } catch (e: any) {
    showErrorNotification('Error inesperado al procesar pago')
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
  }, 3000) // 3 segundos para errores - tiempo suficiente para leer
}

const showSuccessNotification = (message: string) => {
  successMessage.value = message
  error.value = null
  showNotification.value = true
  setTimeout(() => {
    showNotification.value = false
  }, 1000) // 1 segundo para éxito - súper rápido
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
  showEfectivoCalculator.value = false
  showPropinaTarjetaModal.value = false
  metodoPagoSeleccionado.value = null
  efectivoRecibido.value = ''
  cambioCalculado.value = 0
  propinaEfectivo.value = ''
  propinaTarjeta.value = ''
}

// Funciones para calculadora de efectivo
const calcularCambio = () => {
  if (!selectedPedido.value) return
  
  const recibido = parseFloat(efectivoRecibido.value) || 0
  const total = Number(selectedPedido.value.total) + propinaEfectivoNum.value
  
  cambioCalculado.value = recibido - total
}

const confirmarPagoEfectivo = async () => {
  if (!selectedPedido.value) return
  
  const recibido = parseFloat(efectivoRecibido.value) || 0
  const total = Number(selectedPedido.value.total) + propinaEfectivoNum.value
  
  if (recibido < total) {
    showErrorNotification(`Efectivo insuficiente. Falta: $${(total - recibido).toFixed(2)}`)
    return
  }
  
  await finalizarPago(selectedPedido.value, 'efectivo', propinaEfectivoNum.value, 0)
}

const cerrarCalculadoraEfectivo = () => {
  showEfectivoCalculator.value = false
  efectivoRecibido.value = ''
  cambioCalculado.value = 0
  propinaEfectivo.value = ''
}

// Función para imprimir ticket (impresora térmica + fallbacks)
const imprimirTicket = async (pedido: PedidoResponse) => {
  try {
    console.log('🖨️ Iniciando proceso de impresión de ticket...')
    
    // Asegurar que tenemos los artículos del pedido
    const pedidoCompleto = await getPedidoCompleto(pedido.id)
    if (!pedidoCompleto) throw new Error('Pedido no encontrado para impresión')

    // Usar el servicio de impresión con fallbacks automáticos
    const result = await printService.printTicket(pedidoCompleto)
    
    if (result.success) {
      console.log(`✅ Ticket impreso exitosamente usando: ${result.method}`)
      
      // Mostrar notificación al usuario sobre el método usado
      if (result.method === 'Impresora térmica ESC/POS') {
        // No mostrar notificación para impresora térmica, es el flujo esperado
      } else {
        // Para fallbacks, mostrar breve notificación informativa
        showSuccessNotification(`Ticket generado (${result.method})`)
      }
    } else {
      throw new Error(result.error || 'Error desconocido en impresión')
    }
    
  } catch (e: any) {
    console.error('❌ Error en proceso de impresión:', e.message)
    
    // En caso de error total, mostrar mensaje pero no fallar el flujo
    showErrorNotification('Error en impresión, verifique la impresora')
    
    // No lanzar error para no interrumpir el flujo de solicitar cuenta
  }
}

// Imprimir ticket por separado (para pedidos ya en cuenta_solicitada)
const imprimirTicketSeparado = async (pedido: PedidoResponse) => {
  try {
    console.log('🖨️ Imprimiendo ticket separado para pedido:', pedido.id)
    
    // Solo imprimir ticket sin cambiar estado
    await imprimirTicket(pedido)
    
    const tipoTexto = pedido.mesa ? `Mesa ${pedido.mesa}` : pedido.nombre_cliente || 'Cliente'
    showSuccessNotification(`Ticket reimpreso: ${tipoTexto} - $${Number(pedido.total).toFixed(2)}`)
    
  } catch (e: any) {
    showErrorNotification('Error al reimprimir ticket')
  }
}

// Mostrar modal de confirmación de cancelación (primera confirmación)
const mostrarConfirmacionCancelacion = (pedido: PedidoResponse) => {
  pedidoACancelar.value = pedido
  showCancelConfirmModal.value = true
}

// Cerrar modal de confirmación
const cerrarConfirmacionCancelacion = () => {
  showCancelConfirmModal.value = false
  pedidoACancelar.value = null
}

// Cancelar pedido (segunda confirmación - ejecutar cancelación)
const confirmarCancelacion = async () => {
  if (!pedidoACancelar.value) return
  
  const pedido = pedidoACancelar.value
  
  try {
    // Cambiar estado a cancelado
    const success = await pedidosStore.updatePedidoEstado(pedido.id, 'cancelado')
    
    if (success) {
      const tipoTexto = pedido.mesa ? `Mesa ${pedido.mesa}` : pedido.nombre_cliente || 'Cliente'
      showSuccessNotification(`Pedido cancelado: ${tipoTexto} - $${Number(pedido.total).toFixed(2)}`)
      
      // Limpiar filtro después de acción completada
      searchQuery.value = ''
      
      // Cerrar todos los modales
      cerrarConfirmacionCancelacion()
      if (showDetailsModal.value) {
        closeDetailsModal()
      }
    } else {
      showErrorNotification(pedidosStore.error || 'Error al cancelar pedido')
    }
  } catch (e: any) {
    showErrorNotification('Error inesperado al cancelar pedido')
  }
}

// Solicitar cuenta para pedido entregado
const solicitarCuenta = async (pedido: PedidoResponse) => {
  try {
    // Primero imprimimos el ticket
    await imprimirTicket(pedido)
    
    // Luego cambiamos el estado
    const success = await pedidosStore.updatePedidoEstado(pedido.id, 'cuenta_solicitada')
    
    if (success) {
      const tipoTexto = pedido.mesa ? `Mesa ${pedido.mesa}` : pedido.nombre_cliente || 'Cliente'
      showSuccessNotification(`Ticket impreso y cuenta solicitada: ${tipoTexto} - $${Number(pedido.total).toFixed(2)}`)
      
      // Limpiar filtro después de acción completada
      searchQuery.value = ''
    } else {
      showErrorNotification(pedidosStore.error || 'Error al solicitar cuenta')
    }
  } catch (e: any) {
    showErrorNotification('Error inesperado al solicitar cuenta')
  }
}

// Funciones para modal de propina tarjeta/transferencia
const aplicarPropinaPorcentaje = (porcentaje: number) => {
  if (!selectedPedido.value) return
  const subtotal = Number(selectedPedido.value.total)
  const propina = (subtotal * porcentaje) / 100
  propinaTarjeta.value = propina.toFixed(2)
}

const actualizarTotalConPropina = () => {
  // Esta función se llama automáticamente cuando el input de propina cambia
  // No necesita lógica adicional porque propinaTarjetaNum ya se actualiza
}

const cerrarModalPropina = () => {
  showPropinaTarjetaModal.value = false
  metodoPagoSeleccionado.value = null
  propinaTarjeta.value = ''
}

const confirmarPagoConPropina = async () => {
  if (!selectedPedido.value || !metodoPagoSeleccionado.value) return
  
  const tipAmount = propinaTarjetaNum.value
  await finalizarPago(
    selectedPedido.value,
    metodoPagoSeleccionado.value,
    0, // propina efectivo
    tipAmount // propina tarjeta
  )
  cerrarModalPropina()
}

const confirmarPagoSinPropina = async () => {
  if (!selectedPedido.value || !metodoPagoSeleccionado.value) return
  
  await finalizarPago(
    selectedPedido.value,
    metodoPagoSeleccionado.value,
    0, // propina efectivo
    0  // propina tarjeta
  )
  cerrarModalPropina()
}
</script>

<template>
  <div class="min-h-screen flex flex-col bg-gradient-to-br from-[#F8FAFC] to-[#EEF2F5]">
    <!-- Header -->
    <AppHeader title="Caja" />

    <!-- Navigation Tabs -->
    <div class="bg-gray-50 border-b border-gray-200">
      <div class="px-6 py-4 space-y-4">
        <!-- Tabs principales -->
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
          <button
            @click="activeTab = 'propinas'"
            :class="[
              'flex-1 px-4 py-2 rounded-md font-medium transition-all text-sm',
              activeTab === 'propinas' 
                ? 'bg-[#00126D] text-white shadow-md' 
                : 'text-gray-600 hover:text-gray-800 hover:bg-gray-50'
            ]"
          >
            💰 Reporte de Propinas
          </button>
        </div>

        <!-- Búsqueda -->
        <div class="flex items-center">
          <div class="flex-1">
            <div class="relative">
              <input
                v-model="searchQuery"
                type="text"
                placeholder="🔍 Buscar por mesa, cliente o pedido..."
                class="w-full pl-4 pr-10 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#00126D] focus:border-transparent text-sm"
              />
              <button 
                v-if="searchQuery"
                @click="searchQuery = ''"
                class="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                ✕
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <main class="flex-1 p-6 pt-0">
      <div class="flex gap-6">
        <!-- Contenido principal -->
        <div class="flex-1">
          <div v-if="pedidosStore.loading" class="text-center py-8 text-gray-600 font-medium">
            <div class="text-4xl mb-4">⏳</div>
            <p class="text-lg">Cargando datos...</p>
            <p class="text-sm text-gray-500 mt-2">
              WebSocket: {{ pedidosStore.wsConnected ? '🟢 Conectado' : '🔴 Desconectado' }}
            </p>
          </div>

      <!-- Tab Overview General -->
      <div v-else-if="activeTab === 'overview'" class="space-y-6">
        <!-- Debug info -->
        <div v-if="pedidosStore.wsConnected" class="bg-green-50 border border-green-200 rounded-lg p-3 mb-4">
          <div class="flex items-center gap-2 text-sm text-green-700">
            <span>🟢</span>
            <span>Tiempo real activo - Última actualización: {{ pedidosStore.lastUpdate ? new Date(pedidosStore.lastUpdate).toLocaleTimeString() : 'N/A' }}</span>
          </div>
        </div>
        <div v-else class="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4">
          <div class="flex items-center gap-2 text-sm text-yellow-700">
            <span>🟡</span>
            <span>Modo polling - Actualizando cada 5 segundos</span>
          </div>
        </div>
        <!-- Estadísticas compactas -->
        <div class="flex flex-wrap gap-3 justify-center lg:justify-start">
          <div class="bg-yellow-100 border border-yellow-200 rounded-lg px-4 py-2 min-w-[80px] text-center">
            <div class="text-xl font-bold text-yellow-700">{{ estadisticasOverview.pendiente }}</div>
            <div class="text-xs text-yellow-600 font-medium">PENDIENTE</div>
          </div>
          <div class="bg-orange-100 border border-orange-200 rounded-lg px-4 py-2 min-w-[80px] text-center">
            <div class="text-xl font-bold text-orange-700">{{ estadisticasOverview.preparando }}</div>
            <div class="text-xs text-orange-600 font-medium">PREPARANDO</div>
          </div>
          <div class="bg-green-100 border border-green-200 rounded-lg px-4 py-2 min-w-[80px] text-center">
            <div class="text-xl font-bold text-green-700">{{ estadisticasOverview.listo }}</div>
            <div class="text-xs text-green-600 font-medium">LISTO</div>
          </div>
          <div class="bg-blue-100 border border-blue-200 rounded-lg px-4 py-2 min-w-[80px] text-center">
            <div class="text-xl font-bold text-blue-700">{{ estadisticasOverview.entregado }}</div>
            <div class="text-xs text-blue-600 font-medium">ENTREGADO</div>
          </div>
          <div class="bg-purple-100 border border-purple-200 rounded-lg px-4 py-2 min-w-[90px] text-center">
            <div class="text-xl font-bold text-purple-700">{{ estadisticasOverview.cuenta_solicitada }}</div>
            <div class="text-xs text-purple-600 font-medium">CUENTA SOL.</div>
          </div>
          <div class="bg-gray-100 border border-gray-200 rounded-lg px-4 py-2 min-w-[80px] text-center">
            <div class="text-xl font-bold text-gray-700">{{ estadisticasOverview.pagado }}</div>
            <div class="text-xs text-gray-600 font-medium">PAGADO</div>
          </div>
          <div class="bg-red-100 border border-red-200 rounded-lg px-4 py-2 min-w-[80px] text-center">
            <div class="text-xl font-bold text-red-700">{{ estadisticasOverview.cancelado }}</div>
            <div class="text-xs text-red-600 font-medium">CANCELADO</div>
          </div>
        </div>

        <!-- Lista de pedidos activos -->
        <div>
          <!-- Header con información de filtros -->
          <div class="mb-4 flex items-center justify-between">
            <h3 class="text-lg font-bold text-gray-700">
              Pedidos Activos
              <span v-if="searchQuery" class="text-sm font-normal text-gray-500">
                (filtrado por: "{{ searchQuery }}")
              </span>
            </h3>
            <div class="text-sm text-gray-500">
              {{ pedidosActivos.length }} de {{ pedidosStore.pedidosCaja.length }} pedidos
            </div>
          </div>
          
          <div v-if="pedidosActivos.length === 0" class="text-center py-8">
            <div class="text-4xl mb-2">🎉</div>
            <p class="text-gray-600">
              {{ searchQuery ? 'No se encontraron resultados' : 'No hay pedidos activos' }}
            </p>
            <button 
              v-if="searchQuery"
              @click="searchQuery = ''"
              class="mt-4 px-4 py-2 bg-[#00126D] text-white rounded-lg hover:bg-blue-900 transition-all"
            >
              Limpiar filtro
            </button>
          </div>
          <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            <div 
              v-for="pedido in pedidosActivos" 
              :key="pedido.id"
              @click="showPedidoDetails(pedido)"
              class="bg-white border border-gray-200 rounded-lg p-4 shadow-sm hover:shadow-md transition-all cursor-pointer hover:border-[#FDB700] hover:scale-105"
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

              <!-- Indicador de clickeable y botones de acción -->
              <div class="mt-3 pt-3 border-t border-gray-200 space-y-2">
                <!-- Botón solicitar cuenta si está entregado -->
                <button
                  v-if="pedido.estado === 'entregado'"
                  @click.stop="solicitarCuenta(pedido)"
                  class="w-full px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm font-semibold rounded-lg transition-all hover:scale-105 shadow-sm hover:shadow-md"
                >
                  💳 Solicitar Cuenta
                </button>
                
                <!-- Indicador de acción -->
                <div class="text-center text-xs text-gray-500 font-medium">
                  👆 Clic para ver detalles del pedido
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Tab Pendientes de Pago -->
      <div v-else-if="activeTab === 'pendientes'">
        <!-- Header con información de filtros -->
        <div class="mb-4 flex items-center justify-between">
          <div class="flex items-center gap-4">
            <h3 class="text-lg font-bold text-gray-700">
              Cuentas Pendientes 
              <span v-if="searchQuery" class="text-sm font-normal text-gray-500">
                (filtrado por: "{{ searchQuery }}")
              </span>
            </h3>
          </div>
          <div class="text-sm text-gray-500">
            {{ pedidosPendientes.length }} de {{ pedidosStore.pedidosPendientesPago.length }} cuentas
          </div>
        </div>

        <div v-if="pedidosPendientes.length === 0" class="text-center py-12">
          <div class="text-6xl mb-4">💳</div>
          <h2 class="text-2xl font-bold text-gray-600 mb-2">
            {{ searchQuery ? 'No se encontraron resultados' : 'Sin pedidos pendientes de pago' }}
          </h2>
          <p class="text-gray-500">
            {{ searchQuery ? 'Intenta con otro término de búsqueda' : 'Todos los pedidos están pagados' }}
          </p>
          <button 
            v-if="searchQuery"
            @click="searchQuery = ''"
            class="mt-4 px-4 py-2 bg-[#00126D] text-white rounded-lg hover:bg-blue-900 transition-all"
          >
            Limpiar filtro
          </button>
        </div>

        <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-6">
          <div 
            v-for="pedido in pedidosPendientes" 
            :key="pedido.id"
            @click="selectPedido(pedido)"
            class="bg-white border-2 border-gray-200 rounded-2xl p-6 hover:shadow-xl hover:border-[#FDB700] cursor-pointer transition-all hover:scale-105 group"
          >
            <!-- Header del pedido - PRIORIZADA MESA/CLIENTE -->
            <div class="flex items-center justify-center mb-4">
              <div class="flex items-center gap-3">
                <div class="text-3xl">{{ getTipoOrdenEmoji(pedido.tipo_orden) }}</div>
                <!-- Mesa o Cliente como prioridad principal -->
                <div v-if="pedido.mesa" class="text-2xl font-black text-blue-600">MESA {{ pedido.mesa }}</div>
                <div v-else-if="pedido.nombre_cliente" class="text-2xl font-black text-green-600">{{ pedido.nombre_cliente }}</div>
                <div v-else class="text-2xl font-black text-[#00126D]">{{ pedido.numero_display }}</div>
              </div>
            </div>

            <!-- Número de pedido secundario -->
            <div class="mb-4 text-center">
              <div class="text-sm text-gray-500 font-medium">
                Pedido #{{ pedido.numero_display }}
              </div>
            </div>

            <!-- Total -->
            <div class="border-t pt-4">
              <div class="text-center">
                <div class="text-sm text-gray-600 mb-1">Total a cobrar</div>
                <div class="text-3xl font-black text-[#FDB700]">$ {{ Number(pedido.total).toFixed(2) }}</div>
              </div>
            </div>

            <!-- Botones de acción -->
            <div class="mt-3 pt-3 border-t border-gray-200 space-y-2">
              <button
                @click.stop="imprimirTicketSeparado(pedido)"
                class="w-full px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg transition-all hover:scale-105 shadow-sm hover:shadow-md flex items-center justify-center gap-2"
              >
                🖨️ Imprimir Ticket
              </button>
              
              <button
                @click.stop="selectPedido(pedido)"
                class="w-full px-3 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-semibold rounded-lg transition-all hover:scale-105 shadow-sm hover:shadow-md flex items-center justify-center gap-2"
              >
                💰 Cobrar
              </button>
            </div>

            <!-- Información adicional de tiempo -->
            <div class="mt-3 text-center text-xs text-gray-500 space-y-1">
              <div>
                ⏰ {{ new Date(pedido.fecha_creacion).toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' }) }}
                ({{ Math.floor((Date.now() - new Date(pedido.fecha_creacion).getTime()) / (1000 * 60)) }} min)
              </div>
              <div class="group-hover:text-[#00126D] transition font-medium">
                👆 Clic para procesar pago
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Tab Reporte de Propinas -->
      <div v-else-if="activeTab === 'propinas'" class="space-y-6">
        <div v-if="loadingPropinas" class="text-center py-8 text-gray-600 font-medium">
          <div class="text-4xl mb-4">⏳</div>
          <p class="text-lg">Cargando reporte de propinas...</p>
        </div>
        
        <div v-else>
          <!-- Resumen diario -->
          <div class="bg-white rounded-lg border border-gray-200 p-6 mb-6">
            <h3 class="text-lg font-bold text-gray-700 mb-4">📊 Resumen de Propinas del Día</h3>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div class="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
                <div class="text-2xl font-bold text-green-700">${{ reportePropinas?.total_efectivo?.toFixed(2) || '0.00' }}</div>
                <div class="text-sm text-green-600 font-medium">Propina Efectivo</div>
              </div>
              <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 text-center">
                <div class="text-2xl font-bold text-blue-700">${{ reportePropinas?.total_tarjeta?.toFixed(2) || '0.00' }}</div>
                <div class="text-sm text-blue-600 font-medium">Propina Tarjeta</div>
              </div>
              <div class="bg-purple-50 border border-purple-200 rounded-lg p-4 text-center">
                <div class="text-2xl font-bold text-purple-700">${{ reportePropinas?.total_general?.toFixed(2) || '0.00' }}</div>
                <div class="text-sm text-purple-600 font-medium">Propina Total</div>
              </div>
            </div>
          </div>

          <!-- Detalle por mesero -->
          <div class="bg-white rounded-lg border border-gray-200 p-6">
            <h3 class="text-lg font-bold text-gray-700 mb-4">👥 Propinas por Mesero</h3>
            <div v-if="reportePropinas?.por_mesero?.length === 0" class="text-center py-4 text-gray-500">
              No hay propinas registradas hoy
            </div>
            <div v-else class="overflow-x-auto">
              <table class="min-w-full divide-y divide-gray-200">
                <thead>
                  <tr class="bg-gray-50">
                    <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Mesero</th>
                    <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Propina Efectivo</th>
                    <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Propina Tarjeta</th>
                    <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Total</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-200">
                  <tr v-for="item in reportePropinas?.por_mesero || []" :key="item.mesero_id" class="hover:bg-gray-50">
                    <td class="px-4 py-3 text-sm font-medium text-gray-900">{{ item.nombre || `Mesero ${item.mesero_id}` }}</td>
                    <td class="px-4 py-3 text-sm text-green-600 font-bold">${{ item.propina_efectivo?.toFixed(2) || '0.00' }}</td>
                    <td class="px-4 py-3 text-sm text-blue-600 font-bold">${{ item.propina_tarjeta?.toFixed(2) || '0.00' }}</td>
                    <td class="px-4 py-3 text-sm text-purple-600 font-bold">${{ item.propina_total?.toFixed(2) || '0.00' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
        </div>

        <!-- Panel lateral de mesas -->
        <div class="w-64 bg-white rounded-lg border border-gray-200 p-4 h-fit sticky top-6">
          <div class="mb-3">
            <h3 class="text-sm font-bold text-[#00126D] flex items-center gap-2">
              🗺️ Estado de Mesas
            </h3>
            <p class="text-xs text-gray-500 mt-1">Clic en mesa para buscar</p>
          </div>
          
          <!-- Layout de mesas -->
          <div class="space-y-3">
            <div class="grid grid-cols-3 gap-2">
              <div v-for="(fila, index) in mesasLayout" :key="index" class="contents">
                <button
                  v-for="numeroMesa in fila"
                  :key="numeroMesa"
                  @click="handleMesaClick(numeroMesa)"
                  :disabled="getMesaEstado(numeroMesa) === 'libre'"
                  :class="[
                    'w-12 h-10 rounded border text-sm font-bold transition-all',
                    getMesaEstado(numeroMesa) === 'libre' 
                      ? 'cursor-not-allowed opacity-60' 
                      : 'hover:scale-105 cursor-pointer',
                    getMesaClase(numeroMesa)
                  ]"
                  :title="`Mesa ${numeroMesa} - ${getMesaEstado(numeroMesa).toUpperCase()}${getMesaEstado(numeroMesa) === 'libre' ? ' (Sin pedidos)' : ' (Clic para ver)'}`"
                >
                  {{ numeroMesa }}
                </button>
              </div>
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
          <div class="text-center bg-orange-100 text-orange-800 px-4 py-3 rounded-lg mb-4">
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

    <!-- Modal Calculadora de Efectivo Profesional -->
    <div 
      v-if="showEfectivoCalculator && selectedPedido" 
      class="fixed inset-0 flex items-center justify-center z-[60] p-4"
      @click.self="cerrarCalculadoraEfectivo"
    >
      <div class="bg-white rounded-2xl max-w-lg w-full shadow-2xl border-2 border-gray-300">
        <!-- Header profesional -->
        <div class="bg-gradient-to-r from-green-600 to-green-700 px-6 py-4 rounded-t-2xl">
          <div class="flex items-center justify-between text-white">
            <h2 class="text-xl font-bold flex items-center gap-2">
              💵 Pago en Efectivo
            </h2>
            <button 
              @click="cerrarCalculadoraEfectivo" 
              class="text-white hover:text-gray-200 text-2xl font-bold"
            >
              ×
            </button>
          </div>
        </div>

        <!-- Contenido de la calculadora -->
        <div class="p-6">
          <!-- Info del pedido -->
          <div class="bg-gray-50 rounded-lg p-4 mb-6 text-center">
            <div class="text-sm text-gray-600 mb-1">Pedido #{{ selectedPedido.numero_display }}</div>
            <div v-if="selectedPedido.mesa" class="text-blue-600 font-medium mb-2">
              🪑 Mesa {{ selectedPedido.mesa }}
            </div>
            <div class="text-3xl font-black text-[#FDB700] mb-2">
              ${{ Number(selectedPedido.total).toFixed(2) }}
            </div>
            <div class="text-sm text-gray-500">Subtotal</div>
            <div class="mt-2 pt-2 border-t border-gray-200">
              <div class="text-lg font-bold text-green-600">
                Total con propina: ${{ totalConPropina.toFixed(2) }}
              </div>
            </div>
          </div>

          <!-- Campo de efectivo recibido -->
          <div class="mb-6">
            <label class="block text-sm font-bold text-gray-700 mb-2">
              💰 Efectivo recibido
            </label>
            <div class="relative">
              <span class="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500 text-lg font-bold">$</span>
              <input
                v-model="efectivoRecibido"
                @input="calcularCambio"
                type="number"
                step="0.01"
                min="0"
                class="w-full pl-8 pr-4 py-4 text-2xl font-bold border-2 border-gray-300 rounded-lg focus:border-green-500 focus:ring-2 focus:ring-green-200 text-center"
                placeholder="0.00"
                autofocus
              />
            </div>
          </div>

          <!-- Propina en efectivo -->
          <div class="mb-4">
            <label class="block text-sm font-bold text-gray-700 mb-2">
              💰 Propina en efectivo (opcional)
            </label>
            <div class="relative">
              <span class="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500 text-lg font-bold">$</span>
              <input
                v-model="propinaEfectivo"
                @input="calcularCambio"
                type="number"
                step="0.01"
                min="0"
                class="w-full pl-8 pr-4 py-3 text-lg font-medium border-2 border-gray-300 rounded-lg focus:border-green-500 focus:ring-2 focus:ring-green-200 text-center"
                placeholder="0.00"
              />
            </div>
            <div class="text-xs text-gray-500 mt-1 text-center">
              Total con propina: <span class="font-bold">${{ totalConPropina.toFixed(2) }}</span>
            </div>
          </div>

          <!-- Resultado del cambio -->
          <div class="mb-6 p-4 rounded-lg" :class="{
            'bg-green-50 border-2 border-green-200': cambioCalculado >= 0,
            'bg-red-50 border-2 border-red-200': cambioCalculado < 0
          }">
            <div class="text-center">
              <div class="text-sm font-medium mb-1" :class="{
                'text-green-700': cambioCalculado >= 0,
                'text-red-700': cambioCalculado < 0
              }">
                {{ cambioCalculado >= 0 ? 'Cambio a entregar' : 'Falta por pagar' }}
              </div>
              <div class="text-3xl font-black" :class="{
                'text-green-600': cambioCalculado >= 0,
                'text-red-600': cambioCalculado < 0
              }">
                ${{ Math.abs(cambioCalculado).toFixed(2) }}
              </div>
            </div>
          </div>

          <!-- Botones de acción -->
          <div class="space-y-3">
            <button
              @click="confirmarPagoEfectivo"
              :disabled="processingPayment || cambioCalculado < 0 || !efectivoRecibido"
              class="w-full py-4 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white font-bold text-lg rounded-lg transition-all disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {{ processingPayment ? '⏳ Procesando...' : '✅ Confirmar Pago' }}
            </button>
            
            <div class="grid grid-cols-3 gap-2">
              <button
                @click="efectivoRecibido = (Number(selectedPedido.total) + propinaEfectivoNum.value).toString(); calcularCambio()"
                class="py-2 bg-blue-100 hover:bg-blue-200 text-blue-700 font-medium text-sm rounded transition-all"
              >
                Exacto
              </button>
              <button
                @click="efectivoRecibido = (Math.ceil((Number(selectedPedido.total) + propinaEfectivoNum.value) / 50) * 50).toString(); calcularCambio()"
                class="py-2 bg-purple-100 hover:bg-purple-200 text-purple-700 font-medium text-sm rounded transition-all"
              >
                + $50
              </button>
              <button
                @click="efectivoRecibido = (Math.ceil((Number(selectedPedido.total) + propinaEfectivoNum.value) / 100) * 100).toString(); calcularCambio()"
                class="py-2 bg-orange-100 hover:bg-orange-200 text-orange-700 font-medium text-sm rounded transition-all"
              >
                + $100
              </button>
            </div>
            
            <button
              @click="cerrarCalculadoraEfectivo"
              :disabled="processingPayment"
              class="w-full py-3 bg-gray-200 hover:bg-gray-300 text-gray-700 font-medium rounded-lg transition-all disabled:opacity-50"
            >
              Cancelar
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal de Propina para Tarjeta/Transferencia -->
    <div 
      v-if="showPropinaTarjetaModal && selectedPedido && metodoPagoSeleccionado" 
      class="fixed inset-0 flex items-center justify-center z-[65] p-4"
      @click.self="cerrarModalPropina"
    >
      <div class="bg-white rounded-2xl max-w-lg w-full shadow-2xl border-2 border-blue-300">
        <!-- Header profesional -->
        <div class="bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-4 rounded-t-2xl">
          <div class="flex items-center justify-between text-white">
            <h2 class="text-xl font-bold flex items-center gap-2">
              💳 Propina - Pago con {{ metodoPagoSeleccionado === 'tarjeta' ? 'Tarjeta' : 'Transferencia' }}
            </h2>
            <button 
              @click="cerrarModalPropina" 
              class="text-white hover:text-gray-200 text-2xl font-bold"
            >
              ×
            </button>
          </div>
        </div>

        <!-- Contenido del modal -->
        <div class="p-6">
          <!-- Info del pedido -->
          <div class="bg-gray-50 rounded-lg p-4 mb-6 text-center">
            <div class="text-sm text-gray-600 mb-1">Pedido #{{ selectedPedido.numero_display }}</div>
            <div v-if="selectedPedido.mesa" class="text-blue-600 font-medium mb-2">
              🪑 Mesa {{ selectedPedido.mesa }}
            </div>
            <div class="text-3xl font-black text-[#FDB700] mb-2">
              ${{ Number(selectedPedido.total).toFixed(2) }}
            </div>
            <div class="text-sm text-gray-500">Subtotal</div>
          </div>

          <!-- Opciones de porcentaje -->
          <div class="mb-6">
            <label class="block text-sm font-bold text-gray-700 mb-3">
              🎯 Selecciona porcentaje de propina
            </label>
            <div class="grid grid-cols-3 gap-3">
              <button
                @click="aplicarPropinaPorcentaje(10)"
                class="py-3 bg-blue-100 hover:bg-blue-200 text-blue-700 font-bold rounded-lg transition-all hover:scale-105"
              >
                10%
              </button>
              <button
                @click="aplicarPropinaPorcentaje(15)"
                class="py-3 bg-blue-200 hover:bg-blue-300 text-blue-800 font-bold rounded-lg transition-all hover:scale-105"
              >
                15%
              </button>
              <button
                @click="aplicarPropinaPorcentaje(20)"
                class="py-3 bg-blue-300 hover:bg-blue-400 text-blue-900 font-bold rounded-lg transition-all hover:scale-105"
              >
                20%
              </button>
            </div>
          </div>

          <!-- Monto específico -->
          <div class="mb-6">
            <label class="block text-sm font-bold text-gray-700 mb-2">
              💰 O especifica monto de propina
            </label>
            <div class="relative">
              <span class="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500 text-lg font-bold">$</span>
              <input
                v-model="propinaTarjeta"
                type="number"
                step="0.01"
                min="0"
                class="w-full pl-8 pr-4 py-3 text-lg font-medium border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:ring-2 focus:ring-blue-200 text-center"
                placeholder="0.00"
                @input="actualizarTotalConPropina"
              />
            </div>
          </div>

          <!-- Total con propina -->
          <div class="bg-blue-50 border-2 border-blue-200 rounded-lg p-4 mb-6 text-center">
            <div class="text-sm font-medium text-blue-700 mb-1">Total a pagar</div>
            <div class="text-3xl font-black text-blue-600">
              ${{ (Number(selectedPedido.total) + propinaTarjetaNum).toFixed(2) }}
            </div>
            <div class="text-xs text-blue-600 mt-1">
              Subtotal: ${{ Number(selectedPedido.total).toFixed(2) }} + Propina: ${{ propinaTarjetaNum.toFixed(2) }}
            </div>
          </div>

          <!-- Botones de acción -->
          <div class="space-y-3">
            <button
              @click="confirmarPagoConPropina"
              :disabled="processingPayment"
              class="w-full py-4 bg-blue-600 hover:bg-blue-700 text-white font-bold text-lg rounded-lg transition-all disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {{ processingPayment ? '⏳ Procesando...' : '✅ Confirmar con Propina' }}
            </button>
            
            <button
              @click="confirmarPagoSinPropina"
              :disabled="processingPayment"
              class="w-full py-3 bg-gray-200 hover:bg-gray-300 text-gray-700 font-medium rounded-lg transition-all disabled:opacity-50"
            >
              💳 Pagar sin propina
            </button>
            
            <button
              @click="cerrarModalPropina"
              :disabled="processingPayment"
              class="w-full py-3 bg-red-100 hover:bg-red-200 text-red-700 font-medium rounded-lg transition-all disabled:opacity-50"
            >
              Cancelar
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal de detalles del pedido -->
    <div 
      v-if="showDetailsModal && selectedPedidoDetails" 
      class="fixed inset-0 flex items-center justify-center z-50 p-4"
      @click.self="closeDetailsModal"
    >
      <div class="bg-white rounded-lg max-w-md w-full shadow-xl border border-gray-200">
        <!-- Header -->
        <div class="px-6 py-4 border-b border-gray-200 bg-[#00126D] rounded-t-lg">
          <div class="flex items-center justify-between text-white">
            <h2 class="text-lg font-semibold flex items-center gap-2">
              🍽️ Mesa {{ selectedPedidoDetails.mesa }} - Pedido #{{ selectedPedidoDetails.numero_display }}
            </h2>
            <button 
              @click="closeDetailsModal" 
              class="text-white hover:text-gray-200 text-xl"
            >
              ×
            </button>
          </div>
        </div>

        <!-- Contenido -->
        <div class="p-6">
          <!-- Estado y información básica -->
          <div class="mb-4">
            <div class="flex items-center justify-between mb-3">
              <div :class="[getEstadoColor(selectedPedidoDetails.estado), 'text-white px-3 py-1 rounded-full text-sm font-bold']">
                {{ getEstadoTexto(selectedPedidoDetails.estado) }}
              </div>
              <div class="text-sm text-gray-500">
                {{ new Date(selectedPedidoDetails.fecha_creacion).toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' }) }}
              </div>
            </div>
            
            <div v-if="selectedPedidoDetails.nombre_cliente" class="bg-green-100 text-green-800 px-3 py-2 rounded-lg mb-3 text-center font-medium">
              👤 {{ selectedPedidoDetails.nombre_cliente }}
            </div>
          </div>
            
          <!-- Lista de artículos -->
          <div v-if="selectedPedidoDetails.articulos_pedido && selectedPedidoDetails.articulos_pedido.length > 0" class="mb-4">
            <h4 class="text-sm font-bold text-gray-700 mb-3">📋 Artículos del pedido:</h4>
            <div class="bg-gray-50 rounded-lg p-3 max-h-60 overflow-y-auto">
              <div 
                v-for="articulo in selectedPedidoDetails.articulos_pedido" 
                :key="articulo.id"
                class="flex justify-between items-start py-2 border-b border-gray-200 last:border-b-0"
              >
                <div class="flex-1">
                  <div class="font-medium text-gray-800">{{ articulo.platillo?.nombre || 'Producto' }}</div>
                  <div v-if="articulo.modificaciones" class="text-gray-500 text-xs mt-1">
                    💬 {{ articulo.modificaciones }}
                  </div>
                  <div class="text-xs text-gray-400 mt-1">
                    Estado: <span :class="articulo.estado_item === 'listo' ? 'text-green-600' : 'text-orange-600'">
                      {{ articulo.estado_item === 'listo' ? '✅ Listo' : '⏳ Preparando' }}
                    </span>
                  </div>
                </div>
                <div class="text-center px-3">
                  <span class="text-gray-600 font-medium">x{{ articulo.cantidad }}</span>
                </div>
                <div class="text-right text-[#FDB700] font-bold">
                  ${{ Number(articulo.precio_cobrado).toFixed(2) }}
                </div>
              </div>
            </div>
          </div>
            
          <!-- Total -->
          <div class="text-center bg-[#FDB700] text-white px-4 py-3 rounded-lg mb-6">
            <div class="text-sm">Total del pedido</div>
            <div class="text-2xl font-bold">$ {{ Number(selectedPedidoDetails.total).toFixed(2) }}</div>
          </div>

          <!-- Botones de acción según el estado -->
          <div class="space-y-2">
            <!-- Si está listo para entregar -->
            <button
              v-if="selectedPedidoDetails.estado === 'entregado'"
              @click="solicitarCuenta(selectedPedidoDetails); closeDetailsModal()"
              class="w-full py-3 bg-purple-600 hover:bg-purple-700 text-white font-medium rounded-lg transition-all"
            >
              💳 Solicitar Cuenta
            </button>
            
            <!-- Si es cuenta solicitada -->
            <button
              v-if="selectedPedidoDetails.estado === 'cuenta_solicitada'"
              @click="selectedPedido = selectedPedidoDetails; closeDetailsModal()"
              class="w-full py-3 bg-green-600 hover:bg-green-700 text-white font-medium rounded-lg transition-all"
            >
              💰 Cobrar Ahora
            </button>
            
            <!-- Botón cancelar discreto (más pequeño) -->
            <button
              v-if="!['pagado', 'cancelado'].includes(selectedPedidoDetails.estado)"
              @click="mostrarConfirmacionCancelacion(selectedPedidoDetails)"
              class="w-full py-2 bg-red-500 hover:bg-red-600 text-white text-sm font-medium rounded-md transition-all opacity-80 hover:opacity-100"
            >
              🗑️ Cancelar Pedido
            </button>
            
            <!-- Botón cerrar -->
            <button
              @click="closeDetailsModal"
              class="w-full py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 font-medium rounded-lg transition-all"
            >
              Cerrar
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal de Confirmación de Cancelación -->
    <div 
      v-if="showCancelConfirmModal && pedidoACancelar" 
      class="fixed inset-0 flex items-center justify-center z-[70] p-4"
      @click.self="cerrarConfirmacionCancelacion"
    >
      <div class="bg-white rounded-xl max-w-md w-full shadow-2xl border-2 border-red-200">
        <!-- Header de advertencia -->
        <div class="bg-gradient-to-r from-red-600 to-red-700 px-6 py-4 rounded-t-xl">
          <div class="flex items-center justify-between text-white">
            <h2 class="text-lg font-bold flex items-center gap-2">
              ⚠️ Confirmar Cancelación
            </h2>
            <button 
              @click="cerrarConfirmacionCancelacion" 
              class="text-white hover:text-gray-200 text-xl font-bold"
            >
              ×
            </button>
          </div>
        </div>

        <!-- Contenido de confirmación -->
        <div class="p-6">
          <!-- Información del pedido a cancelar -->
          <div class="bg-gray-50 rounded-lg p-4 mb-6 text-center">
            <div class="text-sm text-gray-600 mb-2">Se cancelará este pedido:</div>
            
            <div v-if="pedidoACancelar.mesa" class="text-blue-600 font-bold text-lg mb-1">
              🪑 Mesa {{ pedidoACancelar.mesa }}
            </div>
            <div v-else-if="pedidoACancelar.nombre_cliente" class="text-green-600 font-bold text-lg mb-1">
              👤 {{ pedidoACancelar.nombre_cliente }}
            </div>
            
            <div class="text-lg font-medium text-gray-700 mb-2">
              Pedido #{{ pedidoACancelar.numero_display }}
            </div>
            
            <div class="text-2xl font-black text-[#FDB700] mb-2">
              ${{ Number(pedidoACancelar.total).toFixed(2) }}
            </div>
            
            <div class="text-xs text-gray-500">
              {{ new Date(pedidoACancelar.fecha_creacion).toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' }) }}
            </div>
          </div>

          <!-- Advertencia final -->
          <div class="bg-red-50 border-2 border-red-200 rounded-lg p-4 mb-6">
            <div class="flex items-center gap-2 text-red-700 font-medium mb-2">
              ⚠️ Esta acción NO se puede deshacer
            </div>
            <div class="text-red-600 text-sm">
              El pedido se marcará como cancelado y desaparecerá de todas las vistas activas.
            </div>
          </div>

          <!-- Botones de confirmación final -->
          <div class="space-y-3">
            <button
              @click="confirmarCancelacion"
              class="w-full py-3 bg-red-600 hover:bg-red-700 text-white font-bold rounded-lg transition-all hover:scale-105 flex items-center justify-center gap-2"
            >
              🗑️ SÍ, Cancelar Pedido
            </button>
            
            <button
              @click="cerrarConfirmacionCancelacion"
              class="w-full py-3 bg-gray-200 hover:bg-gray-300 text-gray-700 font-medium rounded-lg transition-all"
            >
              ← No, Mantener Pedido
            </button>
          </div>
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
            <h3 class="font-bold text-green-700 text-lg mb-1">¡Éxito!</h3>
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