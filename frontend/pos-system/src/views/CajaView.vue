<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { usePedidosStore } from '../stores/pedidos'
import { websocketService } from '@/services/websocket'
import type { PedidoResponse, ReporteDiaAnalytics, ReporteDiaTicket, Turno } from '../types'
import AppHeader from '@/components/AppHeader.vue'
import TurnoModal from '@/components/TurnoModal.vue'
import GastoFormModal from '@/components/gastos/GastoFormModal.vue'
import api from '@/api/client'
import printService from '@/services/printService'
import { formatTime, formatDateTime, getMinutesElapsed } from '@/utils/dateUtils'

const router = useRouter()
const auth = useAuthStore()
const pedidosStore = usePedidosStore()

// Referencias reactivas
const activeTab = ref<'overview' | 'pendientes' | 'propinas'>('overview')
const selectedPedido = ref<PedidoResponse | null>(null)
const processingPayment = ref(false)

// Cambio manual de estado (admin-only) desde cards
const showEstadoMenuPedidoId = ref<number | null>(null)
const estadoMenuTarget = ref<HTMLElement | null>(null)
const estadoMenuPos = ref<{ top: number; left: number } | null>(null)
const estadoMenuLoading = ref(false)

const estadoOptions: Array<{ value: PedidoResponse['estado']; label: string }> = [
  { value: 'pendiente', label: 'Pendiente' },
  { value: 'preparando', label: 'Preparando' },
  { value: 'listo', label: 'Listo' },
  { value: 'entregado', label: 'Entregado' },
  { value: 'cuenta_solicitada', label: 'Cuenta solicitada' },
  { value: 'pagado', label: 'Pagado' },
  { value: 'cancelado', label: 'Cancelado' },
  { value: 'dividido', label: 'Dividido' }
]

const canManualChangeEstado = computed(() => auth.user?.rol === 'administrador')

const getArticuloEstadoLabel = (estadoItem: string) => {
  const labels: Record<string, string> = {
    pendiente: '🕒 Pendiente',
    preparando: '⏳ Preparando',
    listo: '✅ Listo',
    entregado: '📦 Entregado'
  }
  return labels[estadoItem] || estadoItem
}

const getArticuloEstadoClass = (estadoItem: string) => {
  const classes: Record<string, string> = {
    pendiente: 'text-gray-600',
    preparando: 'text-orange-600',
    listo: 'text-green-700',
    entregado: 'text-blue-700'
  }
  return classes[estadoItem] || 'text-gray-600'
}


// Estados para dividir cuenta
const showSplitModal = ref(false)
const splitPedido = ref<PedidoResponse | null>(null)
const splitNumCuentas = ref<number>(2)
const splitAsignaciones = ref<Record<number, number[]>>({})
const splitProcessing = ref(false)
const splitPrintPaused = ref(false)
const splitPrintError = ref<string | null>(null)
const splitPendingPrints = ref<PedidoResponse[]>([])
const splitCurrentPrintIndex = ref<number>(0)

const MAX_SPLIT_CUENTAS = 5

const canSplitSelectedPedido = computed(() => {
  if (auth.user?.rol !== 'administrador') return false
  if (!selectedPedido.value) return false
  return ['entregado', 'cuenta_solicitada'].includes(selectedPedido.value.estado)
})

const canSplitDetailsPedido = computed(() => {
  if (auth.user?.rol !== 'administrador') return false
  if (!selectedPedidoDetails.value) return false
  return ['entregado', 'cuenta_solicitada'].includes(selectedPedidoDetails.value.estado)
})
const successMessage = ref<string | null>(null)
const showNotification = ref(false)
const error = ref<string | null>(null)

// Estados para gestion de turnos
const turnoActivo = ref<Turno | null>(null)
const showTurnoModal = ref(false)
const modalTipo = ref<'inicio' | 'cierre'>('inicio')
const loadingTurno = ref(false)
const reporteTurno = ref<any>(null)
const shiftSummary = ref<any>(null)
const showGastoModal = ref(false)


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

// Subtabs dentro de "Reporte del dia"
const subTabReporteDia = ref<'reporte' | 'tickets'>('reporte')

// Tickets del dia (pagados + cancelados)
const ticketsDelDia = ref<ReporteDiaTicket[]>([])
const loadingTicketsDelDia = ref(false)

// Analiticas del dia (estilo dashboard)
const analyticsDia = ref<ReporteDiaAnalytics | null>(null)
const loadingAnalyticsDia = ref(false)

let analyticsDiaTimer: number | undefined

let ticketsDelDiaTimer: number | undefined

const printingTicketId = ref<number | null>(null)

// Modal: editar propina (solo pagados)
const showEditarPropinaModal = ref(false)
const ticketParaPropina = ref<ReporteDiaTicket | null>(null)
const propinaMontoManual = ref<string>('')
const propinaTipoManual = ref<'efectivo' | 'tarjeta'>('tarjeta')
const savingPropinaManual = ref(false)

// Estados para búsqueda y mapa de mesas
const searchQuery = ref<string>('')
const showMesaMap = ref(false)

// Estados para tabla de pedidos del día en analíticas
const selectedPaymentMethod = ref<'todos' | 'efectivo' | 'tarjeta' | 'transferencia'>('todos')
const sortDescending = ref(true)

const filteredPedidosDelDia = computed(() => {
  if (!ticketsDelDia.value) return []
  
  let result = [...ticketsDelDia.value]

  // Filtrar por método de pago
  if (selectedPaymentMethod.value !== 'todos') {
    result = result.filter(p => p.metodo_pago === selectedPaymentMethod.value)
  }

  // Ordenar por hora (fecha_evento o fecha_creacion)
  result.sort((a, b) => {
    // Usar fecha_evento o fecha_creacion si no hay evento
    const dateA = new Date(a.fecha_evento || a.fecha_creacion || 0).getTime()
    const dateB = new Date(b.fecha_evento || b.fecha_creacion || 0).getTime()
    return sortDescending.value ? dateB - dateA : dateA - dateB
  })

  return result
})

const filteredSummary = computed(() => {
  const pedidos = filteredPedidosDelDia.value
  const count = pedidos.length
  if (count === 0) return null

  const total = pedidos.reduce((sum, p) => sum + Number(p.total), 0)
  const propina_total = pedidos.reduce((sum, p) => sum + Number(p.propina_total || 0), 0)
  
  return {
    count,
    total,
    propina_total,
    promedio_ticket: total / count
  }
})

// Helpers para tabla
const getMesaClienteDisplay = (pedido: ReporteDiaTicket) => {
  if (pedido.mesa) return `Mesa ${pedido.mesa}`
  if (pedido.nombre_cliente) return pedido.nombre_cliente
  return 'Cliente'
}

const getPaymentMethodIcon = (metodo: string | null) => {
  if (!metodo) return '❓'
  const icons: Record<string, string> = {
    efectivo: '💵',
    tarjeta: '💳',
    transferencia: '📱'
  }
  return icons[metodo] || '❓'
}

const getPaymentMethodColor = (metodo: string | null) => {
  if (!metodo) return 'bg-gray-100 text-gray-800'
  const colors: Record<string, string> = {
    efectivo: 'bg-green-100 text-green-800',
    tarjeta: 'bg-blue-100 text-blue-800',
    transferencia: 'bg-purple-100 text-purple-800'
  }
  return colors[metodo] || 'bg-gray-100 text-gray-800'
}

const formatTipDisplay = (pedido: ReporteDiaTicket) => {
  const total = Number(pedido.propina_total || 0)
  if (total === 0) return 'Sin propina'
  return `$${total.toFixed(2)}`
}

// WebSocket Event Handler
const handlePedidoEvent = () => {
    if (activeTab.value === 'propinas') {
        cargarAnalyticsDia()
        cargarTicketsDelDia()
        cargarReportePropinas()
    }
}

let timer: number | undefined
let timerTurno: number | undefined

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

    // Cargar turno activo
    await cargarTurnoActivo()

    // Inicializar WebSocket para caja
    const wsConnected = await pedidosStore.initWebSocket('caja')

    if (wsConnected) {
      console.log('✅ Caja View: WebSocket conectado, datos en tiempo real activos')
      
      // Suscribirse a eventos para actualizar analíticas
      websocketService.on('pedido_created', handlePedidoEvent)
      websocketService.on('pedido_estado_changed', handlePedidoEvent)
      websocketService.on('articulo_estado_changed', handlePedidoEvent)
      websocketService.on('pedido_pagado', handlePedidoEvent)
    } else {
      console.warn('⚠️ Caja View: WebSocket falló, usando polling como fallback')
      // Fallback: polling cada 5 segundos si WebSocket falla
      timer = window.setInterval(() => {
        pedidosStore.refreshPedidos()
      }, 5000)
    }

    // No se necesita polling del turno: se carga al iniciar y el WebSocket maneja cambios en tiempo real
  } catch (error) {
    console.error('❌ Caja View: Error en inicialización:', error)
  }
})

const closeEstadoMenu = () => {
  showEstadoMenuPedidoId.value = null
  estadoMenuTarget.value = null
  estadoMenuPos.value = null
  estadoMenuLoading.value = false
}

const toggleEstadoMenu = async (pedido: PedidoResponse, ev: MouseEvent) => {
  if (!canManualChangeEstado.value) return

  if (showEstadoMenuPedidoId.value === pedido.id) {
    closeEstadoMenu()
    return
  }

  showEstadoMenuPedidoId.value = pedido.id
  estadoMenuTarget.value = ev.currentTarget as HTMLElement

  await nextTick()
  const rect = estadoMenuTarget.value?.getBoundingClientRect()
  if (rect) {
    // Posicionar el menu alineado a la derecha del badge
    estadoMenuPos.value = {
      top: rect.bottom + 8,
      left: Math.max(8, rect.right - 240)
    }
  }
}

const applyManualEstado = async (pedido: PedidoResponse | null | undefined, nuevoEstado: PedidoResponse['estado']) => {
  if (!canManualChangeEstado.value) return
  if (estadoMenuLoading.value) return
  if (!pedido) return
  if (pedido.estado === nuevoEstado) {
    closeEstadoMenu()
    return
  }

  estadoMenuLoading.value = true
  try {
    const ok = await pedidosStore.updatePedidoEstado(pedido.id, nuevoEstado)
    if (ok) {
      showSuccessNotification(`Estado actualizado: #${pedido.numero_display} → ${getEstadoTexto(nuevoEstado)}`)
      closeEstadoMenu()
    }
  } finally {
    estadoMenuLoading.value = false
  }
}

const onGlobalClick = (ev: MouseEvent) => {
  if (!showEstadoMenuPedidoId.value) return

  const target = ev.target as Node
  if (estadoMenuTarget.value && estadoMenuTarget.value.contains(target)) return

  // si el click ocurre dentro del menu, no cerrar
  const menuEl = document.getElementById('estado-menu-popover')
  if (menuEl && menuEl.contains(target)) return

  closeEstadoMenu()
}

onMounted(() => {
  document.addEventListener('click', onGlobalClick)
})

onUnmounted(() => {
  console.log('👋 Caja View: Cleanup...')
  document.removeEventListener('click', onGlobalClick)
  if (timer) {
    clearInterval(timer)
  }
  if (timerTurno) {
    clearInterval(timerTurno)
  }
  
  // Limpiar listeners WebSocket
  websocketService.off('pedido_created', handlePedidoEvent)
  websocketService.off('pedido_estado_changed', handlePedidoEvent)
  websocketService.off('articulo_estado_changed', handlePedidoEvent)
  websocketService.off('pedido_pagado', handlePedidoEvent)

  stopTicketsDelDiaAutoRefresh()
  stopAnalyticsDiaAutoRefresh()
  pedidosStore.disconnectWebSocket()
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

const cargarAnalyticsDia = async () => {
  loadingAnalyticsDia.value = true
  try {
    const res = await api.get('/reportes/dia/analytics')
    analyticsDia.value = res.data
  } catch (error) {
    console.error('Error cargando analiticas del dia:', error)
    showErrorNotification('Error al cargar analiticas del dia')
  } finally {
    loadingAnalyticsDia.value = false
  }
}

const startAnalyticsDiaAutoRefresh = () => {
  // Deprecated: WebSocket handles updates
  cargarAnalyticsDia()
  cargarTicketsDelDia()
}

const stopAnalyticsDiaAutoRefresh = () => {
  // Deprecated
  if (analyticsDiaTimer) {
    clearInterval(analyticsDiaTimer)
    analyticsDiaTimer = undefined
  }
}

const estadoEnVivoAnalytics = [
  'pendiente',
  'preparando',
  'listo',
  'entregado',
  'cuenta_solicitada',
  'dividido'
]

const getAnalyticsDataHora = (hora: number) => {
  if (!analyticsDia.value) return { cantidad: 0, total: 0 }
  const data = analyticsDia.value.ventas_por_hora.find(d => d.hora === hora)
  return data || { cantidad: 0, total: 0 }
}

const getAnalyticsPorcentajeHora = (hora: number) => {
  if (!analyticsDia.value) return 0
  const maxVentas = Math.max(...analyticsDia.value.ventas_por_hora.map(d => d.total), 1)
  const data = getAnalyticsDataHora(hora)
  return (data.total / maxVentas) * 100
}

const getAnalyticsCantidadEstado = (estado: string) => {
  if (!analyticsDia.value) return 0
  const data = analyticsDia.value.estado_actual.find(d => d.estado === estado)
  return data ? data.cantidad : 0
}

// Computadas para métricas del turno actual (dinámicas)
const turnoMetrics = computed(() => {
  if (!turnoActivo.value) {
    return null
  }

  const inicioTurno = new Date(turnoActivo.value.fecha_apertura).getTime()
  
  // Filtrar tickets pagados DESPUÉS del inicio del turno
  const ticketsDelTurno = ticketsDelDia.value.filter(t => {
    if (!t.fecha_pago) return false
    const fechaPago = new Date(t.fecha_pago).getTime()
    return fechaPago >= inicioTurno
  })

  // Calcular totales
  const ventasEfectivo = ticketsDelTurno
    .filter(t => t.metodo_pago === 'efectivo')
    .reduce((sum, t) => sum + Number(t.total), 0)

  const ventasTarjeta = ticketsDelTurno
    .filter(t => t.metodo_pago === 'tarjeta' || t.metodo_pago === 'transferencia')
    .reduce((sum, t) => sum + Number(t.total), 0)

  const propinasEfectivo = ticketsDelTurno
    .reduce((sum, t) => sum + Number(t.propina_efectivo || 0), 0)

  const propinasTarjeta = ticketsDelTurno
    .reduce((sum, t) => sum + Number(t.propina_tarjeta || 0), 0)

  // Gastos del turno (desde el resumen del backend)
  const gastosTurno = shiftSummary.value?.gastos_turno || 0

  // Efectivo esperado en caja = Fondo Inicial + Ventas Efectivo + Propinas Efectivo - Gastos
  const efectivoEsperado = Number(turnoActivo.value.total_inicial) + ventasEfectivo + propinasEfectivo - gastosTurno

  return {
    ticketsCount: ticketsDelTurno.length,
    ventasEfectivo,
    ventasTarjeta,
    propinasEfectivo,
    propinasTarjeta,
    gastosTurno,
    efectivoEsperado,
    fondoInicial: Number(turnoActivo.value.total_inicial)
  }
})

// Watch para cargar reporte cuando se activa la pestaña
watch(activeTab, (newTab) => {
  if (newTab === 'propinas') {
    subTabReporteDia.value = 'reporte'
    cargarReportePropinas()
    cargarAnalyticsDia()
    cargarTicketsDelDia()
    return
  }
})

watch(subTabReporteDia, (newSubTab) => {
  if (activeTab.value === 'propinas') {
    cargarAnalyticsDia()
    cargarTicketsDelDia()
  }
})

const startTicketsDelDiaAutoRefresh = () => {
  // Deprecated: WebSocket handles updates
  cargarTicketsDelDia()
}

const stopTicketsDelDiaAutoRefresh = () => {
  // Deprecated
  if (ticketsDelDiaTimer) {
    clearInterval(ticketsDelDiaTimer)
    ticketsDelDiaTimer = undefined
  }
}

const cargarTicketsDelDia = async () => {
  loadingTicketsDelDia.value = true
  try {
    const res = await api.get('/reportes/dia/tickets')
    ticketsDelDia.value = res.data
  } catch (error) {
    console.error('Error cargando tickets del dia:', error)
    showErrorNotification('Error al cargar tickets del dia')
  } finally {
    loadingTicketsDelDia.value = false
  }
}

const reimprimirTicketDesdeHistorial = async (t: ReporteDiaTicket) => {
  if (t.estado !== 'pagado') return
  if (printingTicketId.value) return

  printingTicketId.value = t.id
  try {
    const pedidoRes = await api.get(`/pedidos/${t.id}`)
    const pedidoCompleto = pedidoRes.data as PedidoResponse

    const result = await printService.printTicket(pedidoCompleto)
    if (!result.success) {
      throw new Error(result.error || 'Error desconocido en impresión')
    }

    showSuccessNotification(`Ticket reimpreso (#${t.numero_display})`)
  } catch (e: any) {
    console.error('Error reimprimiendo ticket:', e)
    showErrorNotification('Error al reimprimir ticket')
  } finally {
    printingTicketId.value = null
  }
}

const abrirEditarPropina = (t: ReporteDiaTicket) => {
  if (t.estado !== 'pagado') return

  ticketParaPropina.value = t
  propinaTipoManual.value = t.metodo_pago === 'efectivo' ? 'efectivo' : 'tarjeta'

  const montoInicial =
    propinaTipoManual.value === 'efectivo'
      ? Number(t.propina_efectivo || 0)
      : Number(t.propina_tarjeta || 0)
  propinaMontoManual.value = montoInicial ? montoInicial.toFixed(2) : ''

  showEditarPropinaModal.value = true
}

const cerrarEditarPropina = () => {
  showEditarPropinaModal.value = false
  ticketParaPropina.value = null
  propinaMontoManual.value = ''
  propinaTipoManual.value = 'tarjeta'
  savingPropinaManual.value = false
}

const guardarPropinaManual = async () => {
  if (!ticketParaPropina.value) return
  if (savingPropinaManual.value) return

  const monto = parseFloat(propinaMontoManual.value) || 0
  if (monto < 0) {
    showErrorNotification('La propina no puede ser negativa')
    return
  }

  savingPropinaManual.value = true
  try {
    const payload = {
      estado: 'pagado',
      propina_efectivo: propinaTipoManual.value === 'efectivo' ? monto : 0,
      propina_tarjeta: propinaTipoManual.value === 'tarjeta' ? monto : 0
    }

    await api.put(`/pedidos/${ticketParaPropina.value.id}`, payload)
    showSuccessNotification('Propina actualizada')

    cerrarEditarPropina()
    await Promise.all([cargarTicketsDelDia(), cargarReportePropinas(), cargarAnalyticsDia()])
  } catch (e: any) {
    console.error('Error actualizando propina:', e)
    showErrorNotification('Error al actualizar propina')
  } finally {
    savingPropinaManual.value = false
  }
}

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

// Computed para gestión de turnos
const tieneTurnoActivo = computed(() => turnoActivo.value !== null)
const botonTurnoTexto = computed(() =>
  tieneTurnoActivo.value ? 'Cerrar Turno' : 'Iniciar Turno'
)

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
    if (pedido.mesa && !['pagado', 'cancelado', 'dividido'].includes(pedido.estado)) {
      ocupadas.add(pedido.mesa)
    }
  })

  return ocupadas
})

// Obtener estado de una mesa específica
const getMesaEstado = (numeroMesa: string) => {
  if (!mesasOcupadas.value.has(numeroMesa)) return 'libre'

  // Buscar el pedido más reciente de esta mesa
  const pedidosMesa = pedidosStore.pedidos.filter(p => p.mesa === numeroMesa && !['pagado', 'cancelado', 'dividido'].includes(p.estado))
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
     p.mesa === numeroMesa && !['pagado', 'cancelado', 'dividido'].includes(p.estado)
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

// Estado para edición de pedido
const showEditPedidoModal = ref(false)
const orderItemsToEdit = ref<any[]>([])
const editingOrderId = ref<number | null>(null)
const isSavingEdits = ref(false)

// Abrir modal de edición
const openEditPedido = (pedido: PedidoResponse) => {
  editingOrderId.value = pedido.id
  // Clonar los artículos para edición local
  orderItemsToEdit.value = (pedido.articulos_pedido || []).map(a => ({
    id: a.id,
    cantidad: a.cantidad,
    modificaciones: a.modificaciones,
    nombre: a.platillo?.nombre || 'Producto',
    precio_unitario: Number(a.precio_cobrado) / a.cantidad
  }))
  showEditPedidoModal.value = true
}

// Actualizar cantidad en edición
const updateEditQuantity = (index: number, delta: number) => {
  const item = orderItemsToEdit.value[index]
  const nuevaCantidad = Math.max(1, item.cantidad + delta)
  item.cantidad = nuevaCantidad
}

// Eliminar artículo en edición
const removeEditItem = (index: number) => {
  orderItemsToEdit.value.splice(index, 1)
}

// Guardar ediciones del pedido
const saveOrderEdits = async () => {
  if (!editingOrderId.value || orderItemsToEdit.value.length === 0) return

  isSavingEdits.value = true
  try {
    // Primero obtener el pedido actual para saber qué artículos quedan y cuáles eliminar
    const pedidoResp = await api.get(`/pedidos/${editingOrderId.value}`)
    const pedidoCompleto = pedidoResp.data
    const existentes = pedidoCompleto.articulos_pedido || []
    const idsEditados = new Set(orderItemsToEdit.value.map(i => i.id))

    const finalArticulos = orderItemsToEdit.value.map(a => ({
      id: a.id,
      cantidad: a.cantidad,
      modificaciones: a.modificaciones
    }))

    // Agregar entradas para eliminar los que ya no están en edicion
    existentes.forEach((a: any) => {
      if (!idsEditados.has(a.id)) {
        finalArticulos.push({ id: a.id, cantidad: 0, modificaciones: '' })
      }
    })

    const payload = { articulos: finalArticulos }

    await api.put(`/pedidos/${editingOrderId.value}/actualizar-articulos`, payload)

    // Recargar el pedido completo para actualizar UI sin cambiar estado
    const res = await api.get(`/pedidos/${editingOrderId.value}`)
    const updatedPedido = res.data

    // Actualizar en el store/lista local
    const idx = pedidosStore.pedidosCaja.findIndex(p => p.id === editingOrderId.value)
    if (idx !== -1) {
      pedidosStore.pedidosCaja[idx] = updatedPedido
    }
    
    // Si el modal de detalles estaba abierto con este pedido, actualizarlo
    if (selectedPedidoDetails.value?.id === editingOrderId.value) {
      selectedPedidoDetails.value = updatedPedido
    }
    
    showSuccessNotification('Pedido actualizado correctamente')
    showEditPedidoModal.value = false
  } catch (error: any) {
    console.error('Error al guardar cambios:', error)
    showErrorNotification(error.response?.data?.detail || 'Error al guardar cambios')
  } finally {
    isSavingEdits.value = false
  }
}

// Imprimir ticket adelantado
const isPrintingTicket = ref(false)
const imprimirPedidoAdelantado = async (pedido: PedidoResponse) => {
  if (!pedido.articulos_pedido || pedido.articulos_pedido.length === 0) {
    showErrorNotification('El pedido no tiene artículos')
    return
  }
  
  isPrintingTicket.value = true
  try {
    await api.post(`/pedidos/${pedido.id}/imprimir`)
    showSuccessNotification('Ticket enviado a impresión')
  } catch (error: any) {
    console.error('Error al imprimir:', error)
    showErrorNotification(error.response?.data?.detail || 'Error al imprimir ticket')
  } finally {
    isPrintingTicket.value = false
  }
}

// Total calculado localmente para el modal de edición
const totalEditado = computed(() => {
  return orderItemsToEdit.value.reduce((acc, item) => {
    return acc + (item.cantidad * item.precio_unitario)
  }, 0)
})

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
    'cancelado': 'bg-red-500',
    'dividido': 'bg-slate-500'
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
    'cancelado': 'CANCELADO',
    'dividido': 'DIVIDIDO'
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

const openSplitModalForPedido = async (pedido: PedidoResponse) => {
  const pedidoCompleto = await getPedidoCompleto(pedido.id)
  if (!pedidoCompleto) return

  splitPedido.value = pedidoCompleto
  splitNumCuentas.value = 2
  splitAsignaciones.value = {}

  // Inicializar asignaciones por articulo: [c1, c2, ...]
  for (const articulo of pedidoCompleto.articulos_pedido || []) {
    const arr = new Array(MAX_SPLIT_CUENTAS).fill(0)
    arr[0] = articulo.cantidad
    splitAsignaciones.value[articulo.id] = arr
  }

  showSplitModal.value = true
}

const closeSplitModal = () => {
  showSplitModal.value = false
  splitPedido.value = null
  splitAsignaciones.value = {}
  splitProcessing.value = false
  splitPrintPaused.value = false
  splitPrintError.value = null
  splitPendingPrints.value = []
  splitCurrentPrintIndex.value = 0
}

const splitCuentasVisibles = computed(() => {
  const n = Math.min(Math.max(splitNumCuentas.value, 2), MAX_SPLIT_CUENTAS)
  return Array.from({ length: n }, (_, idx) => idx)
})

const splitTotalesPorCuenta = computed(() => {
  const pedido = splitPedido.value
  if (!pedido?.articulos_pedido) return []

  const n = Math.min(Math.max(splitNumCuentas.value, 2), MAX_SPLIT_CUENTAS)
  const totales = new Array(n).fill(0)

  for (const articulo of pedido.articulos_pedido) {
    const asign = splitAsignaciones.value[articulo.id] || []
    const precioUnit = Number(articulo.precio_cobrado) / Math.max(articulo.cantidad, 1)

    for (let i = 0; i < n; i++) {
      const cant = Number(asign[i] || 0)
      totales[i] += cant * precioUnit
    }
  }

  return totales
})

const splitIsValid = computed(() => {
  const pedido = splitPedido.value
  if (!pedido?.articulos_pedido) return false

  const n = Math.min(Math.max(splitNumCuentas.value, 2), MAX_SPLIT_CUENTAS)

  for (const articulo of pedido.articulos_pedido) {
    const asign = splitAsignaciones.value[articulo.id] || []
    let sum = 0
    for (let i = 0; i < n; i++) {
      const cant = Number(asign[i] || 0)
      if (cant < 0) return false
      sum += cant
    }
    if (sum !== articulo.cantidad) return false
  }

  // Evitar cuentas en 0
  const totales = splitTotalesPorCuenta.value
  if (totales.some(t => t <= 0)) return false

  return true
})

const setSplitCantidad = (articuloId: number, cuentaIndex: number, value: number) => {
  const arr = splitAsignaciones.value[articuloId] || new Array(MAX_SPLIT_CUENTAS).fill(0)
  const safe = Number.isFinite(value) ? Math.max(0, Math.floor(value)) : 0
  arr[cuentaIndex] = safe
  splitAsignaciones.value[articuloId] = arr
}

const buildCuentaText = (i: number, total: number) => `Cuenta ${i}/${total}`

const dividirCuentaConfirmar = async () => {
  if (!splitPedido.value) return
  if (!splitIsValid.value) {
    showErrorNotification('Revisa la division: cada articulo debe repartirse completo y ninguna cuenta debe quedar en $0')
    return
  }

  splitProcessing.value = true
  splitPrintPaused.value = false
  splitPrintError.value = null

  const pedido = splitPedido.value
  const n = Math.min(Math.max(splitNumCuentas.value, 2), MAX_SPLIT_CUENTAS)

  const payload = {
    cuentas: Array.from({ length: n }, (_, idx) => ({
      items: (pedido.articulos_pedido || [])
        .map(a => ({ articulo_id: a.id, cantidad: Number((splitAsignaciones.value[a.id] || [])[idx] || 0) }))
        .filter(x => x.cantidad > 0)
    }))
  }

  try {
    const res = await api.post(`/pedidos/${pedido.id}/dividir`, payload)
    const cuentas: PedidoResponse[] = res.data?.cuentas || []

    if (!cuentas.length) {
      throw new Error('No se recibieron cuentas nuevas')
    }

    // Preparar cola de impresion
    splitPendingPrints.value = cuentas
    splitCurrentPrintIndex.value = 0

    // Imprimir en orden; si falla se pausa
    await processSplitPrintQueue()

    if (!splitPrintPaused.value) {
      showSuccessNotification(`Cuenta dividida en ${cuentas.length} partes e impresa`)
      closeSplitModal()

      // Refrescar pedidos por si WS tarda
      await pedidosStore.refreshPedidos()
    }

  } catch (e: any) {
    console.error('Error dividiendo cuenta:', e)
    showErrorNotification(e?.response?.data?.detail || 'Error al dividir cuenta')
  } finally {
    splitProcessing.value = false
  }
}

const processSplitPrintQueue = async () => {
  while (splitCurrentPrintIndex.value < splitPendingPrints.value.length) {
    const pedidoCuenta = splitPendingPrints.value[splitCurrentPrintIndex.value]

    const ok = await imprimirTicket(pedidoCuenta)
    if (!ok) {
      const mesa = pedidoCuenta.mesa ? `Mesa ${pedidoCuenta.mesa}` : ''
      const cliente = pedidoCuenta.nombre_cliente || ''
      splitPrintError.value = `Fallo la impresion: ${mesa} ${cliente}`.trim()
      splitPrintPaused.value = true
      return
    }

    splitCurrentPrintIndex.value++
  }

  splitPrintPaused.value = false
  splitPrintError.value = null
}

const reintentarImpresionSplit = async () => {
  if (!splitPrintPaused.value) return

  splitPrintPaused.value = false
  splitProcessing.value = true

  await processSplitPrintQueue()

  if (!splitPrintPaused.value) {
    showSuccessNotification(`Tickets impresos (${splitPendingPrints.value.length})`)
    closeSplitModal()
    await pedidosStore.refreshPedidos()
  }

  splitProcessing.value = false
}

const cancelarImpresionesRestantes = () => {
  splitPrintPaused.value = false
  splitPrintError.value = null
  showErrorNotification('Impresion detenida. Puedes reimprimir desde Caja.')
  closeSplitModal()
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
const imprimirTicket = async (pedido: PedidoResponse): Promise<boolean> => {
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

      return true
    }

    throw new Error(result.error || 'Error desconocido en impresión')

  } catch (e: any) {
    console.error('❌ Error en proceso de impresión:', e.message)

    showErrorNotification('Error en impresión, verifique la impresora')
    return false
  }
}

// Imprimir ticket por separado (para pedidos ya en cuenta_solicitada)
const imprimirTicketSeparado = async (pedido: PedidoResponse) => {
  try {
    console.log('🖨️ Imprimiendo ticket separado para pedido:', pedido.id)

    // Solo imprimir ticket sin cambiar estado
    const printed = await imprimirTicket(pedido)
    if (!printed) {
      return
    }

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
    const printed = await imprimirTicket(pedido)
    if (!printed) {
      return
    }
 
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

// ===== FUNCIONES PARA GESTIÓN DE TURNOS =====

const cargarTurnoActivo = async () => {
  loadingTurno.value = true
  try {
    const response = await api.get('/turnos/activo')
    turnoActivo.value = response.data
  } catch (error: any) {
    // 404 significa que no hay turno activo, lo cual es normal
    if (error.response?.status === 404) {
      turnoActivo.value = null
      shiftSummary.value = null
    } else {
      console.error('Error cargando turno activo:', error)
      showErrorNotification('Error al cargar turno activo')
    }
    return
  } finally {
    loadingTurno.value = false
  }

  // Cargar resumen del turno para métricas de gastos (silencioso si falla)
  if (turnoActivo.value) {
    try {
      const summaryRes = await api.get(`/turnos/${turnoActivo.value.id}/resumen`)
      shiftSummary.value = summaryRes.data
    } catch (summaryErr: any) {
      // El resumen es opcional: solo registrar en consola, no mostrar error al usuario
      console.warn('No se pudo cargar resumen del turno:', summaryErr?.message)
      shiftSummary.value = null
    }
  } else {
    shiftSummary.value = null
  }
}

const manejarClickTurno = async () => {
  if (tieneTurnoActivo.value) {
    modalTipo.value = 'cierre'
    reporteTurno.value = await obtenerReporteTurno()
  } else {
    modalTipo.value = 'inicio'
    reporteTurno.value = null
  }
  showTurnoModal.value = true
}

const iniciarTurno = async (conteoInicial: any) => {
  loadingTurno.value = true
  try {
    const response = await api.post('/turnos/iniciar', {
      conteo_inicial: {
        denominaciones: conteoInicial.denominaciones
      },
      observaciones: conteoInicial.observaciones
    })

    showSuccessNotification(`Turno #${response.data.id} iniciado con $${conteoInicial.total.toFixed(2)}`)
    await cargarTurnoActivo()
    showTurnoModal.value = false
  } catch (error: any) {
    console.error('Error iniciando turno:', error)
    showErrorNotification(error.response?.data?.detail || 'Error al iniciar turno')
  } finally {
    loadingTurno.value = false
  }
}

const cerrarTurno = async (conteoFinal: any) => {
  loadingTurno.value = true
  try {
    if (!turnoActivo.value) {
      throw new Error('No hay turno activo para cerrar')
    }

    const response = await api.post(`/turnos/${turnoActivo.value.id}/cerrar`, {
      conteo_final: {
        denominaciones: conteoFinal.denominaciones
      },
      observaciones: conteoFinal.observaciones
    })

    showSuccessNotification(`Turno #${response.data.id} cerrado exitosamente`)

    await cargarTurnoActivo()
    showTurnoModal.value = false
  } catch (error: any) {
    console.error('Error cerrando turno:', error)
    showErrorNotification(error.response?.data?.detail || 'Error al cerrar turno')
  } finally {
    loadingTurno.value = false
  }
}

const obtenerReporteTurno = async () => {
  if (!turnoActivo.value) return null
  try {
    const res = await api.get(`/turnos/${turnoActivo.value.id}/resumen`)
    return res.data
  } catch (e: any) {
    console.error('Error obteniendo reporte de turno:', e)
    return null
  }
}

const handleGastoSaved = async () => {
  showGastoModal.value = false
  showSuccessNotification('Gasto registrado y descontado de caja')
  await cargarTurnoActivo()
}
</script>

<template>
  <div class="min-h-screen flex flex-col bg-gradient-to-br from-[#F8FAFC] to-[#EEF2F5]">
    <!-- Header -->
    <AppHeader title="Caja" />

    <!-- Navigation Tabs -->
    <div class="bg-gray-50 border-b border-gray-200">
      <div class="px-6 py-4">
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
            📅 Reporte del dia
          </button>
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
        <!-- Header unificado Blanco -->
        <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4 flex items-center justify-between">
          <div class="flex items-center gap-6">
            <h3 class="text-xl font-bold text-[#00126D]">Pedidos Activos</h3>
            
            <!-- Métrica de 1/4 (Resumen rápido) -->
            <div class="hidden lg:flex items-center gap-3 px-4 py-2 bg-yellow-50 rounded-xl border border-yellow-100">
              <span class="text-xs font-black text-yellow-600 uppercase tracking-wider">Por Cobrar:</span>
              <span class="text-lg font-black text-yellow-700">${{ totalPendientesPago.toFixed(2) }}</span>
            </div>
          </div>

          <div class="flex items-center gap-4">
            <!-- Indicador Tiempo Real -->
            <div v-if="pedidosStore.wsConnected" class="flex items-center gap-2 px-3 py-1.5 bg-green-50 text-green-700 rounded-full border border-green-200 text-xs font-bold shadow-sm">
              <span class="relative flex h-2 w-2">
                <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                <span class="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
              </span>
              TIEMPO REAL ACTIVO
            </div>
            <div v-else class="flex items-center gap-2 px-3 py-1.5 bg-yellow-50 text-yellow-700 rounded-full border border-yellow-200 text-xs font-bold shadow-sm">
              <span class="animate-pulse">🟡</span>
              ACTUALIZACIÓN CADA 5S
            </div>
          </div>
        </div>

        <!-- Lista de pedidos activos (Restaurada) -->
        <div>
          <div v-if="pedidosActivos.length === 0" class="text-center py-12 bg-white rounded-xl border border-dashed border-gray-300">
            <div class="text-4xl mb-4">🎉</div>
            <p class="text-gray-500 font-medium">No hay pedidos activos en este momento</p>
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
                  <span v-if="pedido.mesa" class="text-lg font-bold text-[#00126D]">Mesa {{ pedido.mesa }}</span>
                  <span v-else-if="pedido.nombre_cliente" class="text-lg font-bold text-[#00126D] truncate max-w-[120px]" :title="pedido.nombre_cliente">
                    {{ pedido.nombre_cliente }}
                  </span>
                  <span v-else class="text-lg font-bold text-[#00126D]">#{{ pedido.numero_display }}</span>
                </div>
                <!-- Botón de estado con menú desplegable -->
                <button
                  v-if="canManualChangeEstado"
                  @click.stop="toggleEstadoMenu(pedido, $event)"
                  :disabled="estadoMenuLoading && showEstadoMenuPedidoId === pedido.id"
                  :class="[
                    getEstadoColor(pedido.estado),
                    'text-white px-2 py-1 rounded-xl text-[10px] font-bold shadow-sm uppercase flex items-center gap-1 hover:opacity-90 transition-all disabled:opacity-60'
                  ]"
                >
                  {{ getEstadoTexto(pedido.estado) }}
                  <span class="text-[10px]">▼</span>
                </button>
                <div 
                  v-else
                  :class="[getEstadoColor(pedido.estado), 'text-white px-2 py-1 rounded-xl text-[10px] font-bold shadow-sm uppercase']"
                >
                  {{ getEstadoTexto(pedido.estado) }}
                </div>
              </div>

              <div class="text-sm">
                <div class="text-blue-700 font-semibold mb-1">📄 Pedido #{{ pedido.numero_display }}</div>
                <div class="text-[#FDB700] font-black text-xl">$ {{ Number(pedido.total).toFixed(2) }}</div>
              </div>

              <div class="mt-3 pt-3 border-t border-gray-100 flex justify-between items-center">
                <div class="text-[10px] text-gray-400 font-bold flex items-center gap-1">
                  ⏰ {{ formatTime(pedido.fecha_creacion) }}
                </div>
                <button
                  v-if="pedido.estado === 'entregado'"
                  @click.stop="solicitarCuenta(pedido)"
                  class="text-[10px] font-black text-purple-600 hover:text-purple-800 uppercase tracking-tighter bg-purple-50 px-2 py-1 rounded border border-purple-100 transition-colors"
                >
                  Solicitar Cuenta →
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Tab Pendientes de Pago -->
      <div v-else-if="activeTab === 'pendientes'" class="space-y-6">
        <!-- Header con información -->
        <div class="mb-4 flex items-center justify-between bg-white p-4 rounded-xl shadow-sm border border-gray-200">
          <h3 class="text-lg font-bold text-gray-700">Cuentas Pendientes</h3>
          <div class="text-sm text-gray-500 font-medium">
            {{ pedidosPendientes.length }} cuentas esperando pago
          </div>
        </div>

        <div v-if="pedidosPendientes.length === 0" class="text-center py-16 bg-white rounded-xl border border-dashed border-gray-300">
          <div class="text-6xl mb-4">💳</div>
          <h2 class="text-2xl font-bold text-gray-600 mb-2">Sin pedidos pendientes</h2>
          <p class="text-gray-500">Todos los pedidos están pagados en este momento</p>
        </div>

        <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-6">
          <div
            v-for="pedido in pedidosPendientes"
            :key="pedido.id"
            @click="selectPedido(pedido)"
            class="bg-white border-2 border-gray-200 rounded-2xl p-6 hover:shadow-xl hover:border-[#FDB700] cursor-pointer transition-all hover:scale-105 group"
          >
             <!-- Header del pedido: Mesa/Cliente arriba, Pedido abajo -->
             <div class="flex items-center justify-center mb-4">
               <div class="flex items-center gap-3">
                 <div class="text-3xl">{{ getTipoOrdenEmoji(pedido.tipo_orden) }}</div>
                 <div class="text-2xl font-black text-[#00126D]">
                   <span v-if="pedido.mesa">Mesa {{ pedido.mesa }}</span>
                   <span v-else-if="pedido.nombre_cliente" class="truncate max-w-[220px]" :title="pedido.nombre_cliente">{{ pedido.nombre_cliente }}</span>
                   <span v-else>Pedido #{{ pedido.numero_display }}</span>
                 </div>
               </div>
             </div>

             <div class="mb-4 text-center">
               <div class="text-sm text-blue-700 font-semibold">📄 Pedido #{{ pedido.numero_display }}</div>
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
                ⏰ {{ formatTime(pedido.fecha_creacion) }}
                ({{ getMinutesElapsed(pedido.fecha_creacion) }} min)
              </div>
              <div class="group-hover:text-[#00126D] transition font-medium">
                👆 Clic para procesar pago
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Tab Reporte del Dia (Renovado) -->
      <div v-else-if="activeTab === 'propinas'" class="space-y-6">
        
        <!-- Sección de Control de Turno -->
        <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div class="p-6">
            <div class="flex items-center justify-between mb-6">
              <div>
                <h2 class="text-xl font-bold text-gray-800 flex items-center gap-2">
                  🛡️ Control de Turno
                  <span v-if="turnoActivo" class="text-sm font-normal text-green-600 bg-green-50 px-2 py-1 rounded-full border border-green-200">
                    Activo desde {{ formatTime(turnoActivo.fecha_apertura) }}
                  </span>
                  <span v-else class="text-sm font-normal text-red-600 bg-red-50 px-2 py-1 rounded-full border border-red-200">
                    🔴 Turno Cerrado
                  </span>
                </h2>
                <p class="text-sm text-gray-500 mt-1">Cálculos en tiempo real basados en los tickets cobrados durante este turno.</p>
              </div>
              
              <!-- Botón de Acción de Turno -->
              <div class="flex items-center gap-3">
                <button
                  v-if="tieneTurnoActivo"
                  @click="showGastoModal = true"
                  class="px-4 py-2.5 bg-amber-500 text-white rounded-lg font-bold shadow-sm hover:bg-amber-600 transition-all flex items-center gap-2"
                >
                  <span>💸</span>
                  Registrar Gasto
                </button>

                <button
                  @click="manejarClickTurno"
                  :class="[
                    'px-6 py-2.5 rounded-lg font-bold shadow-sm transition-all flex items-center gap-2',
                    tieneTurnoActivo 
                      ? 'bg-white border-2 border-red-500 text-red-600 hover:bg-red-50' 
                      : 'bg-[#00126D] text-white hover:bg-blue-900 hover:shadow-md transform hover:-translate-y-0.5'
                  ]"
                >
                  <span class="text-xl">{{ tieneTurnoActivo ? '🔒' : '🔓' }}</span>
                  {{ botonTurnoTexto }}
                </button>
              </div>
            </div>

            <!-- Si NO hay turno activo -->
            <div v-if="!turnoActivo" class="py-12 text-center bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
              <div class="text-6xl mb-4 opacity-50">🔐</div>
              <h3 class="text-xl font-bold text-gray-700 mb-2">Turno Cerrado</h3>
              <p class="text-gray-500 max-w-md mx-auto mb-6">
                Para comenzar a cobrar y registrar movimientos de caja, debes iniciar un nuevo turno contando el fondo inicial.
              </p>
              <button
                @click="manejarClickTurno"
                class="px-8 py-3 bg-[#00126D] text-white rounded-xl font-bold shadow-lg hover:bg-blue-900 transition-all text-lg"
              >
                Iniciar Turno Ahora
              </button>
            </div>

            <!-- Si HAY turno activo: Dashboard de Métricas -->
            <div v-else-if="turnoMetrics" class="grid grid-cols-1 lg:grid-cols-3 gap-6">
              
              <!-- Tarjeta Principal: Arqueo Esperado -->
              <div class="lg:col-span-1 bg-gradient-to-br from-[#00126D] to-[#001E96] rounded-xl p-6 text-white shadow-lg relative overflow-hidden group">
                <div class="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                  <span class="text-8xl">💵</span>
                </div>
                
                <h3 class="text-blue-100 font-medium mb-1 uppercase tracking-wider text-sm">Efectivo Esperado en Caja</h3>
                <div class="text-4xl font-bold mb-4 tracking-tight">
                  ${{ turnoMetrics.efectivoEsperado.toFixed(2) }}
                </div>

                <div class="space-y-2 text-sm border-t border-blue-800/50 pt-3">
                  <div class="flex justify-between text-blue-200">
                    <span>Fondo Inicial:</span>
                    <span class="font-mono font-medium">+${{ turnoMetrics.fondoInicial.toFixed(2) }}</span>
                  </div>
                  <div class="flex justify-between text-blue-200">
                    <span>Ventas Efectivo:</span>
                    <span class="font-mono font-medium">+${{ turnoMetrics.ventasEfectivo.toFixed(2) }}</span>
                  </div>
                  <div class="flex justify-between text-blue-200">
                    <span>Propinas Efectivo:</span>
                    <span class="font-mono font-medium">+${{ turnoMetrics.propinasEfectivo.toFixed(2) }}</span>
                  </div>
                  <div class="flex justify-between text-red-200 font-bold bg-red-900/20 px-1 rounded">
                    <span>Gastos en Efectivo:</span>
                    <span class="font-mono font-medium">-${{ turnoMetrics.gastosTurno.toFixed(2) }}</span>
                  </div>
                </div>
              </div>

              <!-- Tarjetas Secundarias: Desglose -->
              <div class="lg:col-span-2 grid grid-cols-2 sm:grid-cols-4 gap-4">
                
                <!-- Venta Efectivo -->
                <div class="bg-green-50 border border-green-100 rounded-xl p-4 flex flex-col justify-between">
                  <div class="text-green-600 mb-1 font-medium text-xs uppercase">Venta Efectivo</div>
                  <div class="text-2xl font-bold text-green-800">${{ turnoMetrics.ventasEfectivo.toFixed(2) }}</div>
                </div>

                <!-- Venta Tarjeta -->
                <div class="bg-blue-50 border border-blue-100 rounded-xl p-4 flex flex-col justify-between">
                  <div class="text-blue-600 mb-1 font-medium text-xs uppercase">Venta Tarjeta</div>
                  <div class="text-2xl font-bold text-blue-800">${{ turnoMetrics.ventasTarjeta.toFixed(2) }}</div>
                </div>

                <!-- Propinas Efectivo -->
                <div class="bg-yellow-50 border border-yellow-100 rounded-xl p-4 flex flex-col justify-between">
                  <div class="text-yellow-600 mb-1 font-medium text-xs uppercase">Propina Efectivo</div>
                  <div class="text-2xl font-bold text-yellow-800">${{ turnoMetrics.propinasEfectivo.toFixed(2) }}</div>
                </div>

                <!-- Propinas Tarjeta -->
                <div class="bg-purple-50 border border-purple-100 rounded-xl p-4 flex flex-col justify-between">
                  <div class="text-purple-600 mb-1 font-medium text-xs uppercase">Propina Tarjeta</div>
                  <div class="text-2xl font-bold text-purple-800">${{ turnoMetrics.propinasTarjeta.toFixed(2) }}</div>
                </div>

                <!-- Gastos Efectivo -->
                <div class="bg-red-50 border border-red-100 rounded-xl p-4 flex flex-col justify-between">
                  <div class="text-red-600 mb-1 font-medium text-xs uppercase">Gastos Caja (Efe)</div>
                  <div class="text-2xl font-bold text-red-800">${{ turnoMetrics.gastosTurno.toFixed(2) }}</div>
                </div>

              </div>
            </div>
          </div>
        </div>

        <!-- Tabla de Tickets del Día (Histórico Auditable) -->
        <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div class="px-6 py-4 border-b border-gray-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <h3 class="font-bold text-gray-800">
              🧾 Comandas del Día
              <span class="text-sm font-normal text-gray-500 ml-2">({{ filteredSummary?.count || 0 }} tickets)</span>
            </h3>
            
            <div class="flex items-center gap-2 bg-gray-100 p-1 rounded-lg">
              <button 
                v-for="method in ['todos', 'efectivo', 'tarjeta']" 
                :key="method"
                @click="selectedPaymentMethod = method as any"
                :class="[
                  'px-3 py-1 text-xs font-medium rounded-md transition-all capitalize',
                  selectedPaymentMethod === method ? 'bg-white shadow text-gray-800' : 'text-gray-500 hover:text-gray-700'
                ]"
              >
                {{ method }}
              </button>
            </div>
          </div>

          <div class="overflow-x-auto">
            <table class="w-full text-sm text-left">
              <thead class="bg-gray-50 text-gray-500 font-medium border-b border-gray-200">
                <tr>
                  <th class="px-6 py-3">Hora</th>
                  <th class="px-6 py-3">Ticket</th>
                  <th class="px-6 py-3">Mesa/Cliente</th>
                  <th class="px-6 py-3">Mesero</th>
                  <th class="px-6 py-3 text-center">Método</th>
                  <th class="px-6 py-3 text-right">Total</th>
                  <th class="px-6 py-3 text-right">Propina</th>
                  <th class="px-6 py-3 text-center">Acciones</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-100">
                <tr v-if="loadingTicketsDelDia" class="animate-pulse">
                  <td colspan="8" class="px-6 py-8 text-center text-gray-400">Cargando tickets...</td>
                </tr>
                <tr v-else-if="filteredPedidosDelDia.length === 0">
                  <td colspan="8" class="px-6 py-8 text-center text-gray-400">No hay tickets registrados hoy con este filtro.</td>
                </tr>
                <tr 
                  v-for="pedido in filteredPedidosDelDia" 
                  :key="pedido.id"
                  class="hover:bg-gray-50 transition-colors"
                >
                  <td class="px-6 py-3 text-gray-500 font-mono text-xs">
                    {{ pedido.fecha_pago ? formatTime(pedido.fecha_pago) : '--:--' }}
                  </td>
                  <td class="px-6 py-3 font-medium text-gray-900">#{{ pedido.numero_display }}</td>
                  <td class="px-6 py-3 text-gray-600 truncate max-w-[150px]" :title="getMesaClienteDisplay(pedido)">
                    {{ getMesaClienteDisplay(pedido) }}
                  </td>
                  <td class="px-6 py-3 text-gray-500">{{ pedido.mesero_nombre || '-' }}</td>
                  <td class="px-6 py-3 text-center">
                    <span :class="['inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium', getPaymentMethodColor(pedido.metodo_pago)]">
                      <span class="mr-1">{{ getPaymentMethodIcon(pedido.metodo_pago) }}</span>
                      {{ pedido.metodo_pago || 'Sin pago' }}
                    </span>
                  </td>
                  <td class="px-6 py-3 text-right font-medium text-gray-900">
                    ${{ Number(pedido.total).toFixed(2) }}
                  </td>
                  <td class="px-6 py-3 text-right text-gray-500">
                     <span v-if="Number(pedido.propina_total) > 0" class="text-green-600 font-medium">
                       +${{ Number(pedido.propina_total).toFixed(2) }}
                     </span>
                     <span v-else class="text-gray-300">-</span>
                  </td>
                  <td class="px-6 py-3 text-center flex justify-center gap-2">
                    <button 
                      @click="reimprimirTicketDesdeHistorial(pedido)"
                      class="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                      title="Reimprimir Ticket"
                    >
                      🖨️
                    </button>
                    <button 
                      @click="abrirEditarPropina(pedido)"
                      class="p-1.5 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded transition-colors"
                      title="Editar Propina"
                    >
                      💰
                    </button>
                  </td>
                </tr>
              </tbody>
              <!-- Footer de Totales de la Tabla -->
              <tfoot v-if="filteredSummary" class="bg-gray-50 font-medium text-gray-800 border-t border-gray-200">
                <tr>
                  <td colspan="5" class="px-6 py-3 text-right">Total Filtro:</td>
                  <td class="px-6 py-3 text-right">${{ filteredSummary.total.toFixed(2) }}</td>
                  <td class="px-6 py-3 text-right text-green-700">+${{ filteredSummary.propina_total.toFixed(2) }}</td>
                  <td></td>
                </tr>
              </tfoot>
            </table>
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

          <!-- Resumen de Estados (Lista Estética) - Movido a la derecha -->
          <div class="mt-8 pt-6 border-t border-gray-100">
            <h4 class="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2">
              <span class="w-1.5 h-1.5 bg-[#00126D] rounded-full"></span>
              Resumen de Estados
            </h4>
            <div class="space-y-1.5">
              <div 
                v-for="estado in ['pendiente', 'preparando', 'listo', 'entregado', 'cuenta_solicitada']" 
                :key="estado"
                class="flex items-center justify-between p-2 rounded-lg hover:bg-gray-50 transition-colors group border border-transparent hover:border-gray-100"
              >
                <div class="flex items-center gap-2.5">
                  <div :class="[getEstadoColor(estado), 'w-2.5 h-2.5 rounded-full shadow-sm group-hover:scale-125 transition-transform']"></div>
                  <span class="text-xs font-bold text-gray-600 group-hover:text-gray-900 transition-colors">{{ getEstadoTexto(estado) }}</span>
                </div>
                <div class="bg-gray-100 px-2 py-0.5 rounded text-[10px] font-black text-gray-500 group-hover:bg-[#00126D] group-hover:text-white transition-all">
                  {{ estadisticasOverview[estado as keyof typeof estadisticasOverview] }}
                </div>
              </div>
            </div>
          </div>
        </div>
    </div>
  </main>

    <!-- Modal: Editar propina (solo pagados) -->
    <div
      v-if="showEditarPropinaModal && ticketParaPropina"
      class="fixed inset-0 flex items-center justify-center z-50 p-4"
      @click.self="cerrarEditarPropina"
    >
      <div class="bg-white rounded-lg max-w-md w-full shadow-lg border border-gray-200">
        <div class="px-6 py-4 border-b border-gray-200">
          <div class="flex items-center justify-between">
            <h2 class="text-lg font-semibold text-gray-800">
              Editar Propina - Ticket #{{ ticketParaPropina.numero_display }}
            </h2>
            <button
              @click="cerrarEditarPropina"
              class="text-gray-400 hover:text-gray-600 text-xl"
              :disabled="savingPropinaManual"
            >
              ×
            </button>
          </div>
          <div class="mt-2 text-sm text-gray-600">
            <span v-if="ticketParaPropina.mesa">Mesa {{ ticketParaPropina.mesa }}</span>
            <span v-else-if="ticketParaPropina.nombre_cliente">{{ ticketParaPropina.nombre_cliente }}</span>
            <span v-else>-</span>
            <span class="mx-2">•</span>
            <span class="capitalize">{{ ticketParaPropina.metodo_pago || '-' }}</span>
          </div>
        </div>

        <div class="p-6 space-y-4">
          <div>
            <div class="text-sm font-medium text-gray-700 mb-2">Tipo de propina</div>
            <div class="flex gap-3">
              <label class="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                <input v-model="propinaTipoManual" type="radio" value="efectivo" />
                Efectivo
              </label>
              <label class="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                <input v-model="propinaTipoManual" type="radio" value="tarjeta" />
                Tarjeta/Transferencia
              </label>
            </div>
          </div>

          <div>
            <label class="text-sm font-medium text-gray-700">Monto</label>
            <div class="mt-1 flex items-center gap-2">
              <span class="text-gray-600 font-semibold">$</span>
              <input
                v-model="propinaMontoManual"
                type="number"
                min="0"
                step="0.01"
                inputmode="decimal"
                class="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#00126D] focus:border-transparent"
                placeholder="0.00"
              />
            </div>
            <div class="mt-2 text-xs text-gray-500">
              Se sobrescribe la propina actual.
            </div>
          </div>
        </div>

        <div class="px-6 py-4 border-t border-gray-200 flex gap-3 justify-end">
          <button
            @click="cerrarEditarPropina"
            class="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-all"
            :disabled="savingPropinaManual"
          >
            Cancelar
          </button>
          <button
            @click="guardarPropinaManual"
            class="px-4 py-2 bg-[#00126D] text-white rounded-lg hover:bg-blue-900 transition-all disabled:opacity-50"
            :disabled="savingPropinaManual"
          >
            {{ savingPropinaManual ? 'Guardando...' : 'Guardar' }}
          </button>
        </div>
      </div>
    </div>

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



           <!-- Boton dividir cuenta (solo admin) -->
           <button
             v-if="canSplitSelectedPedido"
             @click="openSplitModalForPedido(selectedPedido)"
             :disabled="processingPayment"
             class="w-full mb-3 py-2 bg-amber-100 hover:bg-amber-200 text-amber-900 font-semibold rounded-lg transition-all disabled:opacity-50"
           >
             ✂️ Dividir cuenta
           </button>

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
               Pedido #{{ selectedPedidoDetails.numero_display }}
             </h2>
            <div class="flex items-center gap-2">
              <button
                @click="openEditPedido(selectedPedidoDetails)"
                class="bg-white/10 hover:bg-white/20 text-white px-3 py-1 rounded-lg border border-white/30 transition-all flex items-center gap-2 text-sm font-bold"
              >
                <span>✏️</span>
                Editar
              </button>
              <button
                @click="closeDetailsModal"
                class="text-white hover:text-gray-200 text-xl"
              >
                ×
              </button>
            </div>
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
                {{ formatTime(selectedPedidoDetails.fecha_creacion) }}
              </div>
            </div>

            <div v-if="selectedPedidoDetails.mesa" class="bg-blue-100 text-blue-800 px-3 py-2 rounded-lg mb-3 text-center font-medium">
              🪑 Mesa {{ selectedPedidoDetails.mesa }}
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
                     Estado:
                     <span :class="getArticuloEstadoClass(articulo.estado_item)">
                       {{ getArticuloEstadoLabel(articulo.estado_item) }}
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

            <!-- Boton dividir cuenta (solo admin) -->
          <button
            v-if="canSplitDetailsPedido"
            @click="openSplitModalForPedido(selectedPedidoDetails); closeDetailsModal()"
            class="w-full py-3 bg-amber-100 hover:bg-amber-200 text-amber-900 font-semibold rounded-lg transition-all"
          >
            ✂️ Dividir cuenta
          </button>

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

            <!-- Botón imprimir ticket adelantado -->
            <button
              v-if="!['pagado', 'cancelado', 'dividido'].includes(selectedPedidoDetails.estado)"
              @click="imprimirPedidoAdelantado(selectedPedidoDetails)"
              :disabled="isPrintingTicket"
              class="w-full py-3 bg-green-500 hover:bg-green-600 text-white font-bold rounded-lg transition-all flex items-center justify-center gap-2 shadow-sm"
            >
              <span>🖨️</span>
              {{ isPrintingTicket ? 'Imprimiendo...' : 'Imprimir Ticket' }}
            </button>

            <!-- Botón cancelar discreto (más pequeño) -->
             <button
               v-if="!['pagado', 'cancelado', 'dividido'].includes(selectedPedidoDetails.estado)"
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

    <!-- Modal dividir cuenta -->
    <div
      v-if="showSplitModal && splitPedido"
      class="fixed inset-0 z-[80] flex items-center justify-center p-4"
      @click.self="closeSplitModal"
    >
      <div class="absolute inset-0 bg-black bg-opacity-60"></div>

      <div class="relative bg-white rounded-2xl max-w-4xl w-full mx-4 shadow-2xl border border-gray-200 overflow-hidden">
        <div class="px-6 py-4 bg-gradient-to-r from-amber-500 to-amber-600 text-white flex items-center justify-between">
          <div>
            <div class="text-sm opacity-90">Dividir cuenta</div>
            <div class="text-lg font-bold">Pedido #{{ splitPedido.numero_display }}</div>
          </div>
          <button
            @click="closeSplitModal"
            class="text-white hover:text-gray-100 text-2xl font-bold"
          >
            ×
          </button>
        </div>

        <div class="p-6">
          <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-5">
            <div class="text-sm text-gray-700">
              <div v-if="splitPedido.mesa" class="font-semibold text-blue-700">🪑 Mesa {{ splitPedido.mesa }}</div>
              <div v-else-if="splitPedido.nombre_cliente" class="font-semibold text-green-700">👤 {{ splitPedido.nombre_cliente }}</div>
              <div class="text-xs text-gray-500 mt-1">Maximo {{ MAX_SPLIT_CUENTAS }} cuentas</div>
            </div>

            <div class="flex items-center gap-3">
              <label class="text-sm font-semibold text-gray-700">Cuentas:</label>
              <select
                v-model.number="splitNumCuentas"
                class="border border-gray-300 rounded-lg px-3 py-2 text-sm"
                :disabled="splitProcessing || splitPrintPaused"
              >
                <option :value="2">2</option>
                <option :value="3">3</option>
                <option :value="4">4</option>
                <option :value="5">5</option>
              </select>
            </div>
          </div>

          <div class="overflow-auto border border-gray-200 rounded-xl">
            <table class="min-w-full">
              <thead class="bg-gray-50">
                <tr>
                  <th class="text-left text-xs font-bold text-gray-600 px-3 py-3">Articulo</th>
                  <th class="text-center text-xs font-bold text-gray-600 px-3 py-3">Total</th>
                  <th
                    v-for="idx in splitCuentasVisibles"
                    :key="idx"
                    class="text-center text-xs font-bold text-gray-600 px-3 py-3"
                  >
                    {{ buildCuentaText(idx + 1, splitCuentasVisibles.length) }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="articulo in (splitPedido.articulos_pedido || [])"
                  :key="articulo.id"
                  class="border-t"
                >
                  <td class="px-3 py-3">
                    <div class="text-sm font-semibold text-gray-800">{{ articulo.platillo?.nombre || 'Producto' }}</div>
                    <div v-if="articulo.modificaciones" class="text-xs text-gray-500">{{ articulo.modificaciones }}</div>
                  </td>
                  <td class="px-3 py-3 text-center text-sm font-bold text-gray-700">{{ articulo.cantidad }}</td>
                  <td
                    v-for="idx in splitCuentasVisibles"
                    :key="idx"
                    class="px-3 py-2 text-center"
                  >
                    <input
                      type="number"
                      min="0"
                      step="1"
                      class="w-20 border border-gray-300 rounded-lg px-2 py-1 text-center text-sm"
                      :disabled="splitProcessing || splitPrintPaused"
                      :value="(splitAsignaciones[articulo.id] || [])[idx] || 0"
                      @input="setSplitCantidad(articulo.id, idx, Number(($event.target as HTMLInputElement).value))"
                    />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="mt-5 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="bg-gray-50 border border-gray-200 rounded-xl p-4">
              <div class="text-sm font-bold text-gray-700 mb-3">Totales por cuenta</div>
              <div class="grid grid-cols-2 gap-2">
                <div
                  v-for="(total, idx) in splitTotalesPorCuenta"
                  :key="idx"
                  class="bg-white border border-gray-200 rounded-lg p-3"
                >
                  <div class="text-xs text-gray-500">{{ buildCuentaText(idx + 1, splitTotalesPorCuenta.length) }}</div>
                  <div class="text-lg font-black text-amber-700">$ {{ total.toFixed(2) }}</div>
                </div>
              </div>
            </div>

            <div class="bg-white border border-gray-200 rounded-xl p-4">
              <div v-if="splitPrintPaused" class="bg-red-50 border border-red-200 rounded-lg p-3 mb-3">
                <div class="text-sm font-bold text-red-700">Impresion detenida</div>
                <div class="text-xs text-red-700 mt-1">{{ splitPrintError }}</div>
              </div>

              <div class="text-xs text-gray-500 mb-2">
                Se imprimiran {{ splitCuentasVisibles.length }} tickets (uno por cuenta) al confirmar.
              </div>

              <button
                v-if="!splitPrintPaused"
                @click="dividirCuentaConfirmar"
                :disabled="splitProcessing || !splitIsValid"
                class="w-full py-3 bg-amber-600 hover:bg-amber-700 disabled:bg-gray-300 text-white font-bold rounded-lg transition-all disabled:cursor-not-allowed"
              >
                {{ splitProcessing ? 'Procesando...' : '✅ Confirmar y imprimir' }}
              </button>

              <div v-else class="grid grid-cols-2 gap-3">
                <button
                  @click="reintentarImpresionSplit"
                  :disabled="splitProcessing"
                  class="py-3 bg-green-600 hover:bg-green-700 text-white font-bold rounded-lg"
                >
                  Reintentar
                </button>
                <button
                  @click="cancelarImpresionesRestantes"
                  :disabled="splitProcessing"
                  class="py-3 bg-gray-200 hover:bg-gray-300 text-gray-800 font-bold rounded-lg"
                >
                  Cancelar
                </button>
              </div>

              <button
                @click="closeSplitModal"
                :disabled="splitProcessing"
                class="w-full mt-3 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold rounded-lg"
              >
                Cerrar
              </button>

              <div v-if="!splitIsValid" class="text-xs text-gray-500 mt-2">
                Tip: cada articulo debe sumar exactamente su total entre cuentas.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Popover: cambio manual de estado (admin-only) -->
    <div
      v-if="showEstadoMenuPedidoId && estadoMenuPos"
      id="estado-menu-popover"
      class="fixed z-[90]"
      :style="{ top: `${estadoMenuPos.top}px`, left: `${estadoMenuPos.left}px` }"
    >
      <div class="w-60 bg-white border border-gray-200 rounded-2xl shadow-2xl overflow-hidden">
        <div class="px-3 py-2 bg-gray-50 border-b border-gray-200">
          <div class="text-xs font-bold text-gray-700">Cambiar estado</div>
          <div class="text-[11px] text-gray-500">Solo administrador (casos especiales)</div>
        </div>

        <div class="p-2 max-h-60 overflow-y-auto scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-transparent">
          <button
            v-for="opt in estadoOptions"
            :key="opt.value"
            @click.stop="applyManualEstado(pedidosActivos.find(p => p.id === showEstadoMenuPedidoId), opt.value)"
            :disabled="estadoMenuLoading || pedidosActivos.find(p => p.id === showEstadoMenuPedidoId)?.estado === opt.value"
            class="w-full text-left px-3 py-2 rounded-xl text-sm transition-all"
            :class="[
              pedidosActivos.find(p => p.id === showEstadoMenuPedidoId)?.estado === opt.value
                ? 'bg-gray-100 text-gray-500'
                : 'hover:bg-gray-50 text-gray-800'
            ]"
          >
            {{ opt.label }}
          </button>
        </div>

        <div class="px-3 py-2 bg-white border-t border-gray-200">
          <button
            @click.stop="closeEstadoMenu"
            class="w-full px-3 py-2 text-sm font-semibold bg-gray-100 hover:bg-gray-200 text-gray-800 rounded-xl"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>

    <!-- Modal: Edición de Pedido -->
    <div
      v-if="showEditPedidoModal"
      class="fixed inset-0 flex items-center justify-center z-[100] p-4 bg-black/60 backdrop-blur-sm"
      @click.self="showEditPedidoModal = false"
    >
      <div class="bg-white rounded-3xl max-w-lg w-full shadow-2xl border border-gray-200 flex flex-col max-h-[90vh] md:max-h-[85vh]">
        <!-- Header -->
        <div class="px-6 py-5 border-b border-gray-100 flex items-center justify-between">
          <div>
            <h2 class="text-xl font-black text-[#00126D] flex items-center gap-2">
              <span>✏️</span>
              Editar Artículos
            </h2>
            <p class="text-xs text-gray-400 font-bold uppercase tracking-wider mt-1">Pedido #{{ editingOrderId }}</p>
          </div>
          <button
            @click="showEditPedidoModal = false"
            class="w-10 h-10 flex items-center justify-center rounded-full hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-all text-2xl"
          >
            ×
          </button>
        </div>

        <!-- Lista de artículos editables -->
        <div :class="['flex-1', orderItemsToEdit.length > 3 ? 'overflow-y-auto max-h-[420px] p-6 space-y-4 custom-scrollbar' : 'p-6 space-y-4']">
          <div v-if="orderItemsToEdit.length === 0" class="text-center py-12">
            <div class="text-4xl mb-4">⚠️</div>
            <p class="text-gray-500 font-bold">No hay artículos en el pedido</p>
          </div>
          
          <div
            v-for="(item, index) in orderItemsToEdit"
            :key="item.id"
            class="bg-gray-50 rounded-2xl p-4 border border-gray-100 flex items-center justify-between gap-4 group hover:border-[#FDB700] transition-all"
          >
            <div class="flex-1 min-w-0">
              <div class="font-bold text-gray-800 truncate" :title="item.nombre">{{ item.nombre }}</div>
              <div v-if="item.modificaciones" class="text-[10px] text-gray-400 font-medium truncate italic mt-0.5">
                "{{ item.modificaciones }}"
              </div>
              <div class="text-xs font-black text-[#FDB700] mt-1">
                ${{ Number(item.precio_unitario * item.cantidad).toFixed(2) }}
              </div>
            </div>

            <div class="flex items-center gap-3">
              <!-- Controles de cantidad -->
              <div class="flex items-center bg-white rounded-xl border border-gray-200 p-1 shadow-sm">
                <button
                  @click="updateEditQuantity(index, -1)"
                  class="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-50 text-gray-600 font-bold transition-all active:scale-90"
                >
                  -
                </button>
                <span class="w-10 text-center font-black text-[#00126D] text-sm">{{ item.cantidad }}</span>
                <button
                  @click="updateEditQuantity(index, 1)"
                  class="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-50 text-gray-600 font-bold transition-all active:scale-90"
                >
                  +
                </button>
              </div>

              <!-- Botón eliminar -->
              <button
                @click="removeEditItem(index)"
                class="w-10 h-10 flex items-center justify-center rounded-xl bg-red-50 text-red-500 hover:bg-red-100 hover:text-red-600 transition-all active:scale-95"
                title="Eliminar artículo"
              >
                🗑️
              </button>
            </div>
          </div>
        </div>

        <!-- Footer del Modal -->
        <div class="p-6 border-t border-gray-100 bg-gray-50 rounded-b-3xl">
          <div class="flex items-center justify-between mb-6">
            <div class="flex flex-col">
              <span class="text-[10px] font-black text-gray-400 uppercase tracking-widest">Total Estimado</span>
              <span class="text-2xl font-black text-[#00126D]">$ {{ totalEditado.toFixed(2) }}</span>
            </div>
            <div class="text-right">
              <span class="text-[10px] font-black text-gray-400 uppercase tracking-widest">Artículos</span>
              <span class="block text-lg font-bold text-gray-700">{{ orderItemsToEdit.length }}</span>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <button
              @click="showEditPedidoModal = false"
              class="py-3.5 px-6 rounded-2xl font-bold text-gray-500 bg-white border border-gray-200 hover:bg-gray-100 transition-all active:scale-95"
            >
              Cancelar
            </button>
            <button
              @click="saveOrderEdits"
              :disabled="isSavingEdits || orderItemsToEdit.length === 0"
              class="py-3.5 px-6 rounded-2xl font-bold text-white bg-[#00126D] hover:bg-blue-900 shadow-lg shadow-blue-900/20 transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              <span v-if="isSavingEdits" class="animate-spin text-lg">⏳</span>
              {{ isSavingEdits ? 'Guardando...' : '💾 Guardar Cambios' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal de Turno -->
    <TurnoModal
      v-if="showTurnoModal"
      :tipo="modalTipo"
      :reporte-turno="modalTipo === 'cierre' ? reporteTurno : undefined"
      :denominaciones-iniciales="modalTipo === 'cierre' && turnoActivo ? turnoActivo.denominaciones_iniciales : undefined"
      :fondo-anterior="turnoActivo?.fondo_anterior"
      @cancelar="showTurnoModal = false"
      @confirmar="modalTipo === 'inicio' ? iniciarTurno($event) : cerrarTurno($event)"
    />

    <GastoFormModal
      v-if="showGastoModal"
      :turno-id="turnoActivo?.id"
      @close="showGastoModal = false"
      @save="handleGastoSaved"
    />

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
              {{ formatTime(pedidoACancelar.fecha_creacion) }}
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
