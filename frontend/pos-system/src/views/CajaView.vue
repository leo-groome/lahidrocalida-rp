<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { usePedidosStore } from '../stores/pedidos'
import { websocketService } from '@/services/websocket'
import type { PedidoResponse, ReporteDiaAnalytics, ReporteDiaTicket, Turno } from '../types'
import AppHeader from '@/components/AppHeader.vue'
import TurnoModal from '@/components/TurnoModal.vue'
import GastoRapidoModal from '@/components/gastos/GastoRapidoModal.vue'
import api from '@/api/client'
import printService from '@/services/printService'
import { formatTime, formatDateTime, getMinutesElapsed } from '@/utils/dateUtils'
import { 
  Users, 
  CreditCard, 
  Receipt, 
  History, 
  Plus, 
  Search, 
  CheckCircle2, 
  Clock, 
  DollarSign, 
  ChefHat, 
  Check, 
  Printer, 
  ArrowRight,
  TrendingUp,
  AlertCircle,
  LayoutDashboard,
  Lock,
  Unlock,
  PieChart,
  ScrollText,
  ShoppingBag,
  TrendingDown,
  RefreshCcw,
  ShieldCheck,
  Map,
  CircleDollarSign,
  Contact2,
  Banknote,
  SearchIcon,
  ChevronDown,
  ArrowBigRightDash,
  MonitorCheck,
  Edit3,
  X,
  UtensilsCrossed,
  User,
  ReceiptText,
  Scissors,
  Wallet,
  Trash2,
  ChevronRight,
  Smartphone
} from 'lucide-vue-next'


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
const splitModo = ref<'articulo' | 'equitativo' | 'montos'>('articulo')
const splitNumCuentas = ref<number>(2)
const splitAsignaciones = ref<Record<number, number[]>>({})
const splitProcessing = ref(false)
const splitPrintPaused = ref(false)
const splitPrintError = ref<string | null>(null)
const splitPendingPrints = ref<PedidoResponse[]>([])
const splitCurrentPrintIndex = ref<number>(0)

// Modo equitativo
const splitEquitativoN = ref<number>(2)

// Modo por montos
const splitMontos = ref<{ monto: number }[]>([])
const splitMontoInput = ref<string>('')

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

const totalVentasDia = computed(() => {
  return pedidosStore.analytics?.total_ventas || 0
})

const getEstadoAccentColor = (estado: string) => {
  const colors: Record<string, string> = {
    pendiente: 'bg-slate-200',
    preparando: 'bg-amber-400',
    listo: 'bg-green-400',
    entregado: 'bg-blue-400',
    cuenta_solicitada: 'bg-purple-400',
    pagado: 'bg-emerald-500',
    cancelado: 'bg-rose-500'
  }
  return colors[estado] || 'bg-slate-200'
}

const getEstadoBadgeColor = (estado: string) => {
  const colors: Record<string, string> = {
    pendiente: 'bg-slate-400',
    preparando: 'bg-amber-500',
    listo: 'bg-green-500',
    entregado: 'bg-blue-500',
    cuenta_solicitada: 'bg-purple-500',
    pagado: 'bg-emerald-500',
    cancelado: 'bg-rose-500'
  }
  return colors[estado] || 'bg-slate-400'
}

const getEstadoButtonColor = (estado: string) => {
  const colors: Record<string, string> = {
    pendiente: 'bg-slate-50 border-slate-200 text-slate-600',
    preparando: 'bg-amber-50 border-amber-200 text-amber-700',
    listo: 'bg-green-50 border-green-200 text-green-700',
    entregado: 'bg-blue-50 border-blue-200 text-blue-700',
    cuenta_solicitada: 'bg-purple-50 border-purple-200 text-purple-700',
    pagado: 'bg-emerald-50 border-emerald-200 text-emerald-700',
    cancelado: 'bg-rose-50 border-rose-200 text-rose-700'
  }
  return colors[estado] || 'bg-slate-50 border-slate-200 text-slate-600'
}

const getEstadoBadgeClasses = (estado: string) => {
  return `px-3 py-1 rounded-xl text-[10px] font-black uppercase tracking-wider border ${getEstadoButtonColor(estado)}`
}

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
const efectivoInput = ref<HTMLInputElement | null>(null)

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
const tipTypeOptions = ['efectivo', 'tarjeta'] as const
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
    const params: Record<string, any> = {}
    if (turnoActivo.value?.id) params.turno_id = turnoActivo.value.id
    const res = await api.get('/reportes/dia/analytics', { params })
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

// Focus automático para calculadora de efectivo
watch(showEfectivoCalculator, async (val) => {
  if (val) {
    await nextTick()
    setTimeout(() => {
      efectivoInput.value?.focus()
      // Seleccionar el texto para que sea fácil borrarlo
      efectivoInput.value?.select()
    }, 100)
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
  splitModo.value = 'articulo'
  splitAsignaciones.value = {}
  splitProcessing.value = false
  splitPrintPaused.value = false
  splitPrintError.value = null
  splitPendingPrints.value = []
  splitCurrentPrintIndex.value = 0
  splitEquitativoN.value = 2
  splitMontos.value = []
  splitMontoInput.value = ''
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

const splitRestantePorArticulo = computed(() => {
  const pedido = splitPedido.value
  if (!pedido?.articulos_pedido) return {}

  const restante: Record<number, number> = {}
  const n = Math.min(Math.max(splitNumCuentas.value, 2), MAX_SPLIT_CUENTAS)

  for (const articulo of pedido.articulos_pedido) {
    const asign = splitAsignaciones.value[articulo.id] || []
    let sum = 0
    for (let i = 0; i < n; i++) {
      sum += Number(asign[i] || 0)
    }
    restante[articulo.id] = articulo.cantidad - sum
  }
  return restante
})

const setSplitCantidad = (articuloId: number, cuentaIndex: number, value: number) => {
  const arr = splitAsignaciones.value[articuloId] || new Array(MAX_SPLIT_CUENTAS).fill(0)
  const safe = Number.isFinite(value) ? Math.max(0, Math.floor(value)) : 0
  arr[cuentaIndex] = safe
  splitAsignaciones.value[articuloId] = [...arr]
}

const incrementarSplitArticulo = (articuloId: number, cuentaIndex: number) => {
  const restante = splitRestantePorArticulo.value[articuloId] || 0
  if (restante > 0) {
    const asign = splitAsignaciones.value[articuloId] || new Array(MAX_SPLIT_CUENTAS).fill(0)
    setSplitCantidad(articuloId, cuentaIndex, Number(asign[cuentaIndex] || 0) + 1)
  }
}

const decrementarSplitArticulo = (articuloId: number, cuentaIndex: number) => {
  const asign = splitAsignaciones.value[articuloId] || new Array(MAX_SPLIT_CUENTAS).fill(0)
  const actual = Number(asign[cuentaIndex] || 0)
  if (actual > 0) {
    setSplitCantidad(articuloId, cuentaIndex, actual - 1)
  }
}

const buildCuentaText = (i: number, total: number) => `Cuenta ${i}/${total}`

// ── Computeds modo equitativo ──────────────────────────────────────────────
const totalPedidoNum = computed(() => Number(splitPedido.value?.total ?? 0))

const montoEquitativo = computed(() => {
  const n = Math.max(splitEquitativoN.value, 1)
  return totalPedidoNum.value / n
})

const equitativoValido = computed(() =>
  splitEquitativoN.value >= 2 && totalPedidoNum.value > 0
)

// ── Computeds modo por montos ──────────────────────────────────────────────
const totalMontosCobrados = computed(() =>
  splitMontos.value.reduce((s, m) => s + m.monto, 0)
)

const montoRestante = computed(() =>
  totalPedidoNum.value - totalMontosCobrados.value
)

const montosValidos = computed(() =>
  Math.abs(montoRestante.value) < 0.05 && splitMontos.value.length >= 2
)

const agregarMontoPago = () => {
  const val = parseFloat(splitMontoInput.value)
  if (!Number.isFinite(val) || val <= 0) return
  splitMontos.value.push({ monto: val })
  splitMontoInput.value = ''
}

const eliminarMontoPago = (idx: number) => {
  splitMontos.value.splice(idx, 1)
}

// ── Helper compartido para llamar al endpoint de montos ────────────────────
const dividirPorMontosAPI = async (cuentas: { monto: number }[]) => {
  if (!splitPedido.value) return
  splitProcessing.value = true
  splitPrintPaused.value = false
  splitPrintError.value = null

  try {
    const res = await api.post(`/pedidos/${splitPedido.value.id}/dividir_por_montos`, { cuentas })
    const nuevasCuentas: PedidoResponse[] = res.data?.cuentas || []

    if (!nuevasCuentas.length) throw new Error('No se recibieron cuentas nuevas')

    splitPendingPrints.value = nuevasCuentas
    splitCurrentPrintIndex.value = 0
    await processSplitPrintQueue()

    if (!splitPrintPaused.value) {
      showSuccessNotification(`Cuenta dividida en ${nuevasCuentas.length} partes`)
      closeSplitModal()
      await pedidosStore.refreshPedidos()
    }
  } catch (e: any) {
    console.error('Error dividiendo cuenta por montos:', e)
    showErrorNotification(e?.response?.data?.detail || 'Error al dividir cuenta')
  } finally {
    splitProcessing.value = false
  }
}

const dividirCuentaEquitativoConfirmar = async () => {
  if (!equitativoValido.value) return
  const n = splitEquitativoN.value
  const base = parseFloat(montoEquitativo.value.toFixed(2))
  // El último absorbe el centavo residual
  const ultimo = parseFloat((totalPedidoNum.value - base * (n - 1)).toFixed(2))
  const cuentas = Array.from({ length: n }, (_, i) => ({ monto: i < n - 1 ? base : ultimo }))
  await dividirPorMontosAPI(cuentas)
}

const dividirCuentaMontosConfirmar = async () => {
  if (!montosValidos.value) return
  const cuentas = splitMontos.value.map(m => ({ monto: m.monto }))
  await dividirPorMontosAPI(cuentas)
}

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
  if (isPrintingTicket.value) return
  isPrintingTicket.value = true
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
  } finally {
    isPrintingTicket.value = false
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
  <div class="min-h-screen bg-[#F8FAFC] font-sans selection:bg-blue-100 selection:text-blue-900">
    <!-- Header -->
    <AppHeader title="Caja" />

    <!-- Modern Sidebar-like Navigation Tabs (Segmented Control) -->
    <div class="sticky top-[64px] z-20 bg-white/80 backdrop-blur-md border-b border-slate-200/60 px-6 py-4">
      <div class="max-w-[1400px] mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div class="flex p-1 bg-slate-100 rounded-2xl w-full md:w-auto self-start">
          <button
            @click="activeTab = 'overview'"
            :class="[
              'flex items-center gap-2 px-6 py-2.5 rounded-xl font-bold text-sm transition-all duration-300',
              activeTab === 'overview'
                ? 'bg-white text-blue-700 shadow-sm ring-1 ring-black/5'
                : 'text-slate-500 hover:text-slate-700 hover:bg-white/50'
            ]"
          >
            <LayoutDashboard class="w-4 h-4" />
            <span>Overview</span>
          </button>
          <button
            @click="activeTab = 'pendientes'"
            :class="[
              'flex items-center gap-2 px-6 py-2.5 rounded-xl font-bold text-sm transition-all duration-300 relative',
              activeTab === 'pendientes'
                ? 'bg-white text-blue-700 shadow-sm ring-1 ring-black/5'
                : 'text-slate-500 hover:text-slate-700 hover:bg-white/50'
            ]"
          >
            <CreditCard class="w-4 h-4" />
            <span>Cuentas</span>
            <span v-if="pedidosPendientes.length > 0" 
              class="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-[10px] text-white font-black ring-2 ring-white">
              {{ pedidosPendientes.length }}
            </span>
          </button>
          <button
            @click="activeTab = 'propinas'"
            :class="[
              'flex items-center gap-2 px-6 py-2.5 rounded-xl font-bold text-sm transition-all duration-300',
              activeTab === 'propinas'
                ? 'bg-white text-blue-700 shadow-sm ring-1 ring-black/5'
                : 'text-slate-500 hover:text-slate-700 hover:bg-white/50'
            ]"
          >
            <History class="w-4 h-4" />
            <span>Historial</span>
          </button>
        </div>

        <!-- Quick Stats / Actions -->
        <div class="flex items-center gap-3">
          <div class="hidden sm:flex items-center gap-4 mr-2 py-1 px-4 bg-blue-50 border border-blue-100 rounded-2xl">
            <div class="flex flex-col">
              <span class="text-[10px] font-black text-blue-400 uppercase tracking-widest">Pendiente</span>
              <span class="text-sm font-black text-blue-700">${{ totalPendientesPago.toFixed(2) }}</span>
            </div>
            <div class="w-px h-6 bg-blue-200"></div>
            <div class="flex flex-col text-right">
              <span class="text-[10px] font-black text-blue-400 uppercase tracking-widest">Hoy</span>
              <span class="text-sm font-black text-blue-700">${{ totalVentasDia.toFixed(2) }}</span>
            </div>
          </div>
          
          <button 
            @click="manejarClickTurno"
            :class="[
              'px-4 py-2.5 rounded-xl text-sm font-black transition-all shadow-lg flex items-center gap-2',
              tieneTurnoActivo 
                ? 'bg-red-50 text-red-600 hover:bg-red-100 shadow-red-200/50 border border-red-200' 
                : 'bg-green-600 text-white hover:bg-green-700 shadow-green-900/40'
            ]"
          >
            <Clock class="w-4 h-4" />
            {{ tieneTurnoActivo ? 'Cerrar Turno' : 'Abrir Turno' }}
          </button>
        </div>
      </div>
    </div>


    <!-- Main Content -->
    <main class="flex-1 p-6 pt-0">
      <!-- Banner: sin turno activo -->
      <div v-if="!tieneTurnoActivo" class="mb-4 flex items-center gap-4 p-4 bg-amber-50 border border-amber-200 rounded-2xl shadow-sm">
        <AlertCircle class="w-6 h-6 text-amber-500 flex-shrink-0" />
        <div class="flex-1 min-w-0">
          <p class="font-bold text-amber-800 text-sm">No hay turno activo</p>
          <p class="text-xs text-amber-600 mt-0.5">Las métricas son del día completo. Inicia un turno para ver datos del turno actual.</p>
        </div>
        <button
          @click="manejarClickTurno"
          class="px-4 py-2 bg-amber-500 text-white rounded-xl text-sm font-bold whitespace-nowrap hover:bg-amber-600 active:scale-95 transition-all flex-shrink-0"
        >
          Iniciar Turno
        </button>
      </div>

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
      <div v-else-if="activeTab === 'overview'" class="space-y-8 mt-6">
        <!-- Header Unificado -->
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-4">
            <div class="p-3 bg-blue-600 rounded-2xl shadow-lg shadow-blue-200">
              <LayoutDashboard class="w-6 h-6 text-white" />
            </div>
            <div>
              <h3 class="text-2xl font-black text-slate-800 tracking-tight">Pedidos Activos</h3>
              <p class="text-xs font-bold text-slate-400 uppercase tracking-widest">En preparación y servicio</p>
            </div>
          </div>

          <div class="flex items-center gap-3">
            <div v-if="pedidosStore.wsConnected" class="flex items-center gap-2 px-4 py-2 bg-green-50 text-green-600 rounded-2xl border border-green-100 text-[10px] font-black uppercase tracking-widest shadow-sm">
              <span class="relative flex h-2 w-2">
                <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                <span class="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
              </span>
              Sincronizado
            </div>
            <div v-else class="flex items-center gap-2 px-4 py-2 bg-amber-50 text-amber-600 rounded-2xl border border-amber-100 text-[10px] font-black uppercase tracking-widest shadow-sm">
              <AlertCircle class="w-3 h-3 animate-pulse" />
              Reconectando...
            </div>
          </div>
        </div>

        <!-- Lista de pedidos activos -->
        <div v-if="pedidosActivos.length === 0" class="flex flex-col items-center justify-center py-20 bg-white rounded-[2.5rem] border-2 border-dashed border-slate-200 shadow-sm">
          <div class="w-20 h-20 bg-slate-50 rounded-full flex items-center justify-center mb-6">
            <ChefHat class="w-10 h-10 text-slate-300" />
          </div>
          <h4 class="text-xl font-black text-slate-400">Cocina Despejada</h4>
          <p class="text-slate-400 text-sm font-medium">No hay pedidos activos en este momento</p>
        </div>

        <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-6">
          <div
            v-for="pedido in pedidosActivos"
            :key="pedido.id"
            @click="showPedidoDetails(pedido)"
            class="group bg-white rounded-[2rem] p-5 shadow-xl shadow-slate-200/40 border border-slate-100 hover:border-blue-400 transition-all duration-500 cursor-pointer flex flex-col relative overflow-hidden"
          >
            <!-- Decorative Accent -->
            <div :class="['absolute top-0 left-0 w-full h-1.5', getEstadoAccentColor(pedido.estado)]"></div>

            <div class="flex items-start justify-between mb-4">
              <div class="flex items-center gap-3">
                <div class="w-12 h-12 bg-slate-50 rounded-2xl flex items-center justify-center shadow-inner group-hover:bg-blue-50 transition-colors">
                  <span class="text-2xl">{{ getTipoOrdenEmoji(pedido.tipo_orden) }}</span>
                </div>
                <div>
                  <h4 class="text-lg font-black text-slate-800 leading-tight">
                    <span v-if="pedido.mesa">Mesa {{ pedido.mesa }}</span>
                    <span v-else-if="pedido.nombre_cliente" class="truncate block max-w-[120px]">{{ pedido.nombre_cliente }}</span>
                    <span v-else>#{{ pedido.numero_display }}</span>
                  </h4>
                  <span class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Pedido #{{ pedido.numero_display }}</span>
                </div>
              </div>

              <!-- Status Dropdown Trigger -->
              <button
                v-if="canManualChangeEstado"
                @click.stop="toggleEstadoMenu(pedido, $event)"
                :disabled="estadoMenuLoading && showEstadoMenuPedidoId === pedido.id"
                :class="[
                  getEstadoButtonColor(pedido.estado),
                  'p-2 rounded-xl border transition-all duration-300 hover:scale-110 flex items-center justify-center'
                ]"
              >
                <div :class="['w-2 h-2 rounded-full mr-2', getEstadoBadgeColor(pedido.estado)]"></div>
                <span class="text-[10px] font-black uppercase tracking-tighter">{{ getEstadoTexto(pedido.estado) }}</span>
              </button>
              <div v-else :class="[getEstadoBadgeClasses(pedido.estado)]">
                {{ getEstadoTexto(pedido.estado) }}
              </div>
            </div>

            <div class="flex-1 flex flex-col justify-center">
              <div class="flex items-baseline gap-1">
                <span class="text-sm font-black text-slate-400">$</span>
                <span class="text-3xl font-black text-slate-800 tracking-tighter">{{ Number(pedido.total).toFixed(2) }}</span>
              </div>
            </div>

            <div class="mt-5 pt-4 border-t border-slate-50 flex items-center justify-between">
              <div class="flex items-center gap-1.5 text-slate-400">
                <Clock class="w-3.5 h-3.5" />
                <span class="text-[10px] font-bold uppercase tracking-wider">{{ formatTime(pedido.fecha_creacion) }}</span>
              </div>
              
              <button
                v-if="pedido.estado === 'entregado'"
                @click.stop="solicitarCuenta(pedido)"
                class="flex items-center gap-1 bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-xl text-[10px] font-black uppercase transition-all shadow-md shadow-blue-200"
              >
                Cobrar
                <ArrowRight class="w-3 h-3" />
              </button>
            </div>
          </div>
        </div>
      </div>


      <!-- Tab Pendientes de Pago (Modernized Premium) -->
      <div v-else-if="activeTab === 'pendientes'" class="space-y-8 mt-6">
        <!-- Header con información -->
        <div class="flex items-center justify-between mb-2">
          <div class="flex items-center gap-4">
            <div class="p-3 bg-blue-600 rounded-2xl shadow-lg shadow-blue-200">
              <CreditCard class="w-6 h-6 text-white" />
            </div>
            <div>
              <h3 class="text-2xl font-black text-slate-800 tracking-tight">Cuentas Pendientes</h3>
              <p class="text-xs font-bold text-slate-400 uppercase tracking-widest">{{ pedidosPendientes.length }} cuentas esperando pago</p>
            </div>
          </div>
        </div>

        <div v-if="pedidosPendientes.length === 0" class="flex flex-col items-center justify-center py-20 bg-white rounded-[2.5rem] border-2 border-dashed border-slate-200 shadow-sm">
          <div class="w-20 h-20 bg-green-50 rounded-full flex items-center justify-center mb-6">
            <CheckCircle class="w-10 h-10 text-green-400" />
          </div>
          <h4 class="text-xl font-black text-slate-400">Todo Pagado</h4>
          <p class="text-slate-400 text-sm font-medium">No hay cuentas pendientes en este momento</p>
        </div>

        <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-6">
          <div
            v-for="pedido in pedidosPendientes"
            :key="pedido.id"
            @click="selectPedido(pedido)"
            class="group bg-white rounded-[2.2rem] p-6 shadow-xl shadow-slate-200/40 border border-slate-100 hover:border-blue-400 transition-all duration-500 cursor-pointer flex flex-col relative overflow-hidden"
          >
            <!-- Decorative Accent -->
            <div class="absolute top-0 left-0 w-full h-1.5 bg-amber-400"></div>

            <div class="flex items-start justify-between mb-6">
              <div class="flex items-center gap-4">
                <div class="w-14 h-14 bg-slate-50 rounded-2xl flex items-center justify-center shadow-inner group-hover:bg-blue-50 transition-colors">
                  <span class="text-2xl">{{ getTipoOrdenEmoji(pedido.tipo_orden) }}</span>
                </div>
                <div>
                  <h4 class="text-xl font-black text-[#00126D] tracking-tight leading-tight">
                    <span v-if="pedido.mesa">Mesa {{ pedido.mesa }}</span>
                    <span v-else-if="pedido.nombre_cliente" class="truncate block max-w-[150px]">{{ pedido.nombre_cliente }}</span>
                    <span v-else>Pedido #{{ pedido.numero_display }}</span>
                  </h4>
                  <span class="text-[10px] font-black text-slate-400 uppercase tracking-widest">PEDIDO #{{ pedido.numero_display }}</span>
                </div>
              </div>
            </div>

            <div class="flex-1 flex flex-col justify-center mb-6">
              <div class="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Total a cobrar</div>
              <div class="flex items-baseline gap-1">
                <span class="text-lg font-black text-amber-500">$</span>
                <span class="text-4xl font-black text-slate-800 tracking-tighter">{{ Number(pedido.total).toFixed(2) }}</span>
              </div>
            </div>

            <div class="space-y-2">
              <button
                @click.stop="imprimirTicketSeparado(pedido)"
                class="w-full flex items-center justify-center gap-2 bg-[#00126D] hover:bg-blue-900 text-white px-4 py-3 rounded-2xl text-xs font-black uppercase transition-all shadow-lg shadow-blue-200"
              >
                <Printer class="w-4 h-4" />
                Imprimir Ticket
              </button>

              <button
                @click.stop="selectPedido(pedido)"
                class="w-full flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-3 rounded-2xl text-xs font-black uppercase transition-all shadow-lg shadow-emerald-100"
              >
                <Banknote class="w-4 h-4" />
                Cobrar Cuenta
              </button>
            </div>

            <div class="mt-5 pt-4 border-t border-slate-50 flex items-center justify-center">
              <div class="flex items-center gap-1.5 text-slate-400">
                <Clock class="w-3.5 h-3.5" />
                <span class="text-[10px] font-bold uppercase tracking-wider">
                  {{ formatTime(pedido.fecha_creacion) }}
                  ({{ getMinutesElapsed(pedido.fecha_creacion) }} min)
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Tab Reporte del Dia (Modernized Premium) -->
      <div v-else-if="activeTab === 'propinas'" class="space-y-8 mt-6">
        
        <!-- SUB-TABS (Segmented Control) -->
        <div class="flex p-1 bg-slate-100 rounded-2xl w-fit mb-4">
          <button
            @click="subTabReporteDia = 'reporte'"
            :class="[
              'flex items-center gap-2 px-6 py-2.5 rounded-xl font-black text-[10px] uppercase tracking-widest transition-all duration-500',
              subTabReporteDia === 'reporte'
                ? 'bg-[#00126D] text-white shadow-lg shadow-blue-900/20'
                : 'text-slate-500 hover:text-slate-700 hover:bg-white/50'
            ]"
          >
            <PieChart class="w-3.5 h-3.5" />
            <span>Resumen del Día</span>
          </button>
          <button
            @click="subTabReporteDia = 'tickets'"
            :class="[
              'flex items-center gap-2 px-6 py-2.5 rounded-xl font-black text-[10px] uppercase tracking-widest transition-all duration-500',
              subTabReporteDia === 'tickets'
                ? 'bg-[#00126D] text-white shadow-lg shadow-blue-900/20'
                : 'text-slate-500 hover:text-slate-700 hover:bg-white/50'
            ]"
          >
            <Receipt class="w-3.5 h-3.5" />
            <span>Auditoría & Turno</span>
          </button>
        </div>

        <!-- Vista 1: Dashboard de Analíticas -->
        <div v-if="subTabReporteDia === 'reporte'" class="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
          
          <!-- Header del Dashboard -->
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-4">
              <div class="p-3 bg-[#00126D] rounded-2xl shadow-xl shadow-blue-200">
                <TrendingUp class="w-6 h-6 text-white" />
              </div>
              <div>
                <h3 class="text-2xl font-black text-slate-800 tracking-tight">Analíticas de Venta</h3>
                <p class="text-xs font-bold text-slate-400 uppercase tracking-widest">Resumen total acumulado hoy</p>
              </div>
            </div>
            <button 
              @click="cargarAnalyticsDia" 
              class="p-3 bg-white text-slate-400 hover:text-[#00126D] hover:rotate-180 transition-all duration-500 rounded-2xl shadow-sm border border-slate-100"
              :class="{ 'animate-spin': loadingAnalyticsDia }"
            >
              <RefreshCcw class="w-5 h-5" />
            </button>
          </div>

          <!-- Loading State -->
          <div v-if="!analyticsDia && loadingAnalyticsDia" class="py-24 text-center bg-white rounded-[2.5rem] border border-slate-100 shadow-sm">
            <div class="w-16 h-16 border-4 border-slate-100 border-t-[#00126D] rounded-full animate-spin mx-auto mb-6"></div>
            <h4 class="text-xl font-black text-slate-300">Generando Reporte...</h4>
            <p class="text-slate-400 text-sm font-medium">Calculando métricas y ventas por hora</p>
          </div>

          <div v-else-if="analyticsDia" class="space-y-8">
            <!-- Grid de Métricas Principales -->
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <!-- Ventas Totales -->
              <div class="bg-white p-7 rounded-[2.5rem] border border-slate-100 shadow-xl shadow-slate-200/40 relative overflow-hidden group">
                <div class="absolute -right-4 -top-4 w-20 h-20 bg-emerald-50 rounded-full blur-2xl group-hover:bg-emerald-100 transition-colors"></div>
                <div class="flex items-center gap-3 mb-6 relative z-10">
                  <div class="p-2.5 bg-emerald-50 rounded-2xl text-emerald-600 shadow-inner">
                    <DollarSign class="w-5 h-5" />
                  </div>
                  <span class="text-[11px] font-black text-slate-400 uppercase tracking-widest leading-none">{{ tieneTurnoActivo ? 'Ventas del Turno' : 'Ingresos del Día' }}</span>
                </div>
                <div class="text-4xl font-black text-slate-800 tracking-tighter mb-2 relative z-10">
                  <span class="text-emerald-500 text-xl mr-1 font-black">$</span>{{ Number(analyticsDia.ingresos.total).toFixed(2) }}
                </div>
                <div class="flex items-center gap-2 text-[10px] font-black text-emerald-600 uppercase tracking-tight bg-emerald-50 w-fit px-3 py-1 rounded-full">
                  <TrendingUp class="w-3 h-3" />
                  Sincronizado
                </div>
              </div>

              <!-- Ticket Promedio -->
              <div class="bg-white p-7 rounded-[2.5rem] border border-slate-100 shadow-xl shadow-slate-200/40 relative overflow-hidden group">
                <div class="absolute -right-4 -top-4 w-20 h-20 bg-blue-50 rounded-full blur-2xl group-hover:bg-blue-100 transition-colors"></div>
                <div class="flex items-center gap-3 mb-6 relative z-10">
                  <div class="p-2.5 bg-blue-50 rounded-2xl text-blue-600 shadow-inner">
                    <History class="w-5 h-5" />
                  </div>
                  <span class="text-[11px] font-black text-slate-400 uppercase tracking-widest leading-none">Ticket Promedio</span>
                </div>
                <div class="text-4xl font-black text-slate-800 tracking-tighter mb-2 relative z-10">
                  <span class="text-blue-500 text-xl mr-1 font-black">$</span>{{ Number(analyticsDia.promedio_ticket).toFixed(2) }}
                </div>
                <div class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Basado en {{ analyticsDia.total_pedidos }} pedidos</div>
              </div>

              <!-- Propinas -->
              <div class="bg-white p-7 rounded-[2.5rem] border border-slate-100 shadow-xl shadow-slate-200/40 relative overflow-hidden group">
                <div class="absolute -right-4 -top-4 w-20 h-20 bg-amber-50 rounded-full blur-2xl group-hover:bg-amber-100 transition-colors"></div>
                <div class="flex items-center gap-3 mb-6 relative z-10">
                  <div class="p-2.5 bg-amber-50 rounded-2xl text-amber-600 shadow-inner">
                    <CircleDollarSign class="w-5 h-5" />
                  </div>
                  <span class="text-[11px] font-black text-slate-400 uppercase tracking-widest leading-none">Propinas Acum.</span>
                </div>
                <div class="text-4xl font-black text-slate-800 tracking-tighter mb-2 relative z-10">
                  <span class="text-amber-500 text-xl mr-1 font-black">$</span>{{ Number(analyticsDia.propinas.total).toFixed(2) }}
                </div>
                <div class="flex gap-4">
                  <div class="flex flex-col">
                    <span class="text-[8px] font-black text-slate-400 uppercase">Efec</span>
                    <span class="text-[10px] font-black text-slate-700">${{ analyticsDia.propinas.efectivo }}</span>
                  </div>
                  <div class="flex flex-col border-l border-slate-100 pl-4">
                    <span class="text-[8px] font-black text-slate-400 uppercase">Tarj</span>
                    <span class="text-[10px] font-black text-slate-700">${{ analyticsDia.propinas.tarjeta }}</span>
                  </div>
                </div>
              </div>

              <!-- Mix de Pagos -->
              <div class="bg-white p-7 rounded-[2.5rem] border border-slate-100 shadow-xl shadow-slate-200/40 relative overflow-hidden group">
                <div class="absolute -right-4 -top-4 w-20 h-20 bg-purple-50 rounded-full blur-2xl group-hover:bg-purple-100 transition-colors"></div>
                <div class="flex items-center gap-3 mb-4 relative z-10">
                  <div class="p-2.5 bg-purple-50 rounded-2xl text-purple-600 shadow-inner">
                    <CreditCard class="w-5 h-5" />
                  </div>
                  <span class="text-[11px] font-black text-slate-400 uppercase tracking-widest leading-none">Mix de Cobro</span>
                </div>
                <div class="space-y-2 relative z-10">
                  <div v-for="(monto, m) in { efec: analyticsDia.ingresos.efectivo, tarj: analyticsDia.ingresos.tarjeta, transf: analyticsDia.ingresos.transferencia }" :key="m" class="flex justify-between items-center group/row">
                    <span class="text-[10px] font-black text-slate-400 uppercase tracking-tighter group-hover/row:text-slate-600 transition-colors">{{ m }}</span>
                    <span class="text-xs font-black text-slate-800">${{ Number(monto).toFixed(2) }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Gráficos y Listas -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
              
              <!-- Más Vendidos -->
              <div class="bg-white rounded-[2.5rem] border border-slate-100 shadow-xl shadow-slate-200/40 p-8 flex flex-col">
                <div class="flex items-center justify-between mb-8">
                  <div class="flex items-center gap-4">
                    <div class="p-3 bg-blue-50 rounded-2xl text-blue-600">
                      <ShoppingBag class="w-6 h-6" />
                    </div>
                    <div>
                      <h4 class="text-xl font-black text-slate-800 tracking-tight">Productos Top</h4>
                      <p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Lo más pedido hoy</p>
                    </div>
                  </div>
                </div>

                <div class="flex-1 space-y-4">
                  <div v-if="analyticsDia.productos_mas_vendidos.length === 0" class="py-12 text-center text-slate-300 font-bold italic">
                    Sin datos de venta suficientes
                  </div>
                  <div 
                    v-for="(prod, idx) in analyticsDia.productos_mas_vendidos.slice(0, 6)" 
                    :key="prod.nombre"
                    class="group flex items-center justify-between p-4 rounded-2xl bg-slate-50/50 border border-slate-100 hover:bg-white hover:shadow-lg hover:border-blue-100 transition-all duration-500"
                  >
                    <div class="flex items-center gap-4">
                      <div class="w-8 h-8 rounded-xl bg-white border border-slate-100 flex items-center justify-center text-xs font-black text-slate-400 group-hover:bg-[#00126D] group-hover:text-white transition-all shadow-sm">
                        {{ idx + 1 }}
                      </div>
                      <span class="font-bold text-slate-700 tracking-tight group-hover:translate-x-1 transition-transform">{{ prod.nombre }}</span>
                    </div>
                    <div class="flex items-center gap-3">
                      <span class="text-[10px] font-black text-slate-400 uppercase">Vendidos:</span>
                      <span class="px-4 py-1 bg-white border border-slate-100 rounded-xl text-xs font-black text-[#00126D] shadow-sm transform group-hover:scale-110 transition-transform">
                        {{ prod.cantidad }} pzas
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Gráfico de Ventas por Hora -->
              <div class="bg-white rounded-[2.5rem] border border-slate-100 shadow-xl shadow-slate-200/40 p-8 flex flex-col">
                <div class="flex items-center justify-between mb-8">
                  <div class="flex items-center gap-4">
                    <div class="p-3 bg-indigo-50 rounded-2xl text-indigo-600">
                      <Clock class="w-6 h-6" />
                    </div>
                    <div>
                      <h4 class="text-xl font-black text-slate-800 tracking-tight">Flujo de Ventas</h4>
                      <p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Actividad horaria acumulada</p>
                    </div>
                  </div>
                </div>

                <div class="flex-1 flex flex-col justify-end">
                  <div class="h-64 flex items-end justify-between gap-2 pb-2">
                    <div 
                      v-for="hora in [12,13,14,15,16,17,18,19,20,21,22]" 
                      :key="hora"
                      class="flex-1 flex flex-col justify-end items-center gap-3 group relative"
                    >
                      <!-- Tooltip -->
                      <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 bg-[#00126D] text-white text-[10px] font-black px-3 py-1.5 rounded-xl opacity-0 group-hover:opacity-100 transition-all pointer-events-none shadow-xl z-20 whitespace-nowrap">
                        <div class="flex flex-col items-center">
                          <span>{{ getAnalyticsDataHora(hora).cantidad }} pedidos</span>
                          <span class="text-blue-200 font-bold">${{ Number(getAnalyticsDataHora(hora).total).toFixed(0) }}</span>
                        </div>
                        <!-- Arrow -->
                        <div class="absolute top-full left-1/2 -translate-x-1/2 border-8 border-transparent border-t-[#00126D]"></div>
                      </div>

                      <!-- Bar -->
                      <div 
                        class="w-full bg-slate-100 rounded-t-xl group-hover:bg-[#00126D] transition-all duration-700 overflow-hidden relative"
                        :style="{ height: `${Math.max(getAnalyticsPorcentajeHora(hora) * 1.5, 4)}px` }"
                      >
                        <div class="absolute inset-0 bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                      </div>

                      <!-- Label -->
                      <span class="text-[9px] font-black text-slate-400 tracking-tighter transition-colors group-hover:text-slate-800">
                        {{ hora }}:00
                      </span>
                    </div>
                  </div>
                </div>
              </div>

            </div>

          </div>
        </div>

        <!-- Vista 2: Auditoría y Control de Turno -->
        <div v-else-if="subTabReporteDia === 'tickets'" class="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
          
          <!-- Sección de Control de Turno -->
          <div class="bg-white rounded-[2.5rem] shadow-xl shadow-slate-200/50 border border-slate-100 overflow-hidden">
            <div class="p-8">
              <div class="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
                <div class="flex items-center gap-4">
                  <div class="p-3 bg-slate-100 rounded-2xl text-slate-600">
                    <ShieldCheck class="w-6 h-6" />
                  </div>
                  <div>
                    <h2 class="text-xl font-black text-slate-800 flex items-center gap-2">
                      Control de Turno
                      <span v-if="turnoActivo" class="text-[10px] font-black text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-lg border border-emerald-100 uppercase tracking-widest">
                        Activo desde {{ formatTime(turnoActivo.fecha_apertura) }}
                      </span>
                      <span v-else class="text-[10px] font-black text-rose-600 bg-rose-50 px-2 py-0.5 rounded-lg border border-rose-100 uppercase tracking-widest">
                        Turno Cerrado
                      </span>
                    </h2>
                    <p class="text-xs font-bold text-slate-400 uppercase tracking-widest mt-1">Sincronización de caja en tiempo real</p>
                  </div>
                </div>
                
                <!-- Botones de Acción de Turno -->
                <div class="flex items-center gap-3">
                  <button
                    v-if="tieneTurnoActivo"
                    @click="showGastoModal = true"
                    class="px-5 py-3 bg-slate-100 text-slate-700 rounded-2xl font-black text-xs uppercase tracking-widest hover:bg-slate-200 transition-all flex items-center gap-2 shadow-sm"
                  >
                    <TrendingDown class="w-4 h-4 text-rose-500" />
                    Registrar Gasto
                  </button>

                  <button
                    @click="manejarClickTurno"
                    :class="[
                      'px-6 py-3 rounded-2xl font-black text-xs uppercase tracking-widest shadow-lg transition-all flex items-center gap-2',
                      tieneTurnoActivo 
                        ? 'bg-rose-50 text-rose-600 hover:bg-rose-100 border border-rose-200 shadow-rose-100' 
                        : 'bg-emerald-600 text-white hover:bg-emerald-700 shadow-emerald-200'
                    ]"
                  >
                    <component :is="tieneTurnoActivo ? Lock : Unlock" class="w-4 h-4" />
                    {{ botonTurnoTexto }}
                  </button>
                </div>
              </div>

              <!-- Si NO hay turno activo -->
              <div v-if="!turnoActivo" class="py-16 text-center bg-slate-50 rounded-[2rem] border-2 border-dashed border-slate-200">
                <div class="w-20 h-20 bg-white rounded-full shadow-inner flex items-center justify-center mx-auto mb-6 text-slate-300">
                  <Lock class="w-10 h-10" />
                </div>
                <h3 class="text-2xl font-black text-slate-400 mb-2 tracking-tight">Turno Cerrado</h3>
                <p class="text-slate-400 text-sm font-medium max-w-md mx-auto mb-8">
                  Para comenzar a cobrar y registrar movimientos de caja, debes iniciar un nuevo turno contando el fondo inicial.
                </p>
                <button
                  @click="manejarClickTurno"
                  class="px-10 py-4 bg-[#00126D] text-white rounded-[1.5rem] font-black text-sm uppercase tracking-widest shadow-xl shadow-blue-200 hover:bg-blue-900 transition-all hover:-translate-y-1"
                >
                  Abrir Turno
                </button>
              </div>

              <!-- Si HAY turno activo: Dashboard de Métricas -->
              <div v-else-if="turnoMetrics" class="grid grid-cols-1 lg:grid-cols-12 gap-8">
                
                <!-- Tarjeta Principal: Arqueo Esperado -->
                <div class="lg:col-span-4 bg-[#00126D] rounded-[2rem] p-8 text-white shadow-2xl shadow-blue-900/20 relative overflow-hidden group border border-white/5">
                  <!-- Decorative Elements -->
                  <div class="absolute top-0 right-0 w-32 h-32 bg-white/5 rounded-full -translate-y-1/2 translate-x-1/2 blur-2xl"></div>
                  <div class="absolute bottom-0 left-0 w-24 h-24 bg-blue-400/10 rounded-full translate-y-1/2 -translate-x-1/2 blur-xl"></div>
                  
                  <div class="relative z-10">
                    <div class="flex items-center gap-2 text-blue-200/80 mb-2">
                      <Banknote class="w-4 h-4" />
                      <span class="text-[10px] font-black uppercase tracking-widest">Efectivo Esperado</span>
                    </div>
                    <div class="text-5xl font-black mb-8 tracking-tighter">
                      <span class="text-blue-300/40 font-black text-2xl mr-1">$</span>{{ turnoMetrics.efectivoEsperado.toFixed(2) }}
                    </div>

                    <div class="space-y-4 text-xs pt-6 border-t border-white/10">
                      <div class="flex justify-between items-center text-blue-100/60 font-bold uppercase tracking-wider">
                        <span>Fondo Inicial:</span>
                        <span class="text-white">+${{ turnoMetrics.fondoInicial.toFixed(2) }}</span>
                      </div>
                      <div class="flex justify-between items-center text-blue-100/60 font-bold uppercase tracking-wider">
                        <span>Ventas Efectivo:</span>
                        <span class="text-white">+${{ turnoMetrics.ventasEfectivo.toFixed(2) }}</span>
                      </div>
                      <div class="flex justify-between items-center text-blue-100/60 font-bold uppercase tracking-wider">
                        <span>Propinas Efectivo:</span>
                        <span class="text-white">+${{ turnoMetrics.propinasEfectivo.toFixed(2) }}</span>
                      </div>
                      <div class="flex justify-between items-center bg-rose-500/20 p-3 rounded-2xl text-rose-200 font-black uppercase tracking-widest border border-rose-500/10">
                        <span>Gastos Turno:</span>
                        <span>-${{ turnoMetrics.gastosTurno.toFixed(2) }}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Tarjetas Secundarias: Desglose -->
                <div class="lg:col-span-8 grid grid-cols-2 sm:grid-cols-2 gap-4">
                  <!-- Venta Efectivo -->
                  <div class="bg-emerald-50 border border-emerald-100 rounded-[2rem] p-6 flex flex-col justify-between group hover:bg-emerald-100 transition-colors">
                    <div class="flex items-center gap-2 text-emerald-400 mb-2">
                      <Banknote class="w-4 h-4" />
                      <span class="text-[10px] font-black uppercase tracking-widest">Venta Efectivo</span>
                    </div>
                    <div class="text-3xl font-black text-emerald-800 tracking-tighter">${{ turnoMetrics.ventasEfectivo.toFixed(2) }}</div>
                  </div>

                  <!-- Venta Tarjeta -->
                  <div class="bg-blue-50 border border-blue-100 rounded-[2rem] p-6 flex flex-col justify-between group hover:bg-blue-100 transition-colors">
                    <div class="flex items-center gap-2 text-blue-400 mb-2">
                      <CreditCard class="w-4 h-4" />
                      <span class="text-[10px] font-black uppercase tracking-widest">Venta Tarjeta</span>
                    </div>
                    <div class="text-3xl font-black text-blue-800 tracking-tighter">${{ turnoMetrics.ventasTarjeta.toFixed(2) }}</div>
                  </div>

                  <!-- Propinas Efectivo -->
                  <div class="bg-amber-50 border border-amber-100 rounded-[2rem] p-6 flex flex-col justify-between group hover:bg-amber-100 transition-colors">
                    <div class="flex items-center gap-2 text-amber-500 mb-2">
                      <CircleDollarSign class="w-4 h-4" />
                      <span class="text-[10px] font-black uppercase tracking-widest">Propina Efectivo</span>
                    </div>
                    <div class="text-3xl font-black text-amber-700 tracking-tighter">${{ turnoMetrics.propinasEfectivo.toFixed(2) }}</div>
                  </div>

                  <!-- Propinas Tarjeta -->
                  <div class="bg-indigo-50 border border-indigo-100 rounded-[2rem] p-6 flex flex-col justify-between group hover:bg-indigo-100 transition-colors">
                    <div class="flex items-center gap-2 text-indigo-400 mb-2">
                      <Contact2 class="w-4 h-4" />
                      <span class="text-[10px] font-black uppercase tracking-widest">Propina Tarjeta</span>
                    </div>
                    <div class="text-3xl font-black text-indigo-800 tracking-tighter">${{ turnoMetrics.propinasTarjeta.toFixed(2) }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Tabla de Tickets del Día (Modernized) -->
          <div class="bg-white rounded-[2.5rem] shadow-xl shadow-slate-200/50 border border-slate-100 overflow-hidden">
            <div class="px-8 py-6 border-b border-slate-50 flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-50/50">
              <h3 class="text-xl font-black text-slate-800 flex items-center gap-3">
                <ScrollText class="w-6 h-6 text-[#00126D]" />
                Auditoría de Comandas
                <span class="text-[10px] font-black text-slate-400 border border-slate-200 px-2 py-0.5 rounded uppercase tracking-widest ml-2">{{ filteredSummary?.count || 0 }} tickets</span>
              </h3>
              
              <!-- Filtros de la tabla -->
              <div class="flex items-center gap-2">
                <select 
                  v-model="selectedPaymentMethod" 
                  class="bg-white border border-slate-200 rounded-xl px-3 py-2 text-[10px] font-black uppercase tracking-wider outline-none focus:ring-2 focus:ring-blue-100 transition-all"
                >
                  <option value="todos">Todos los pagos</option>
                  <option value="efectivo">Efectivo</option>
                  <option value="tarjeta">Tarjeta</option>
                  <option value="transferencia">Transferencia</option>
                </select>
                <button 
                  @click="sortDescending = !sortDescending"
                  class="p-2 bg-white border border-slate-200 rounded-xl text-slate-400 hover:text-[#00126D] transition-colors"
                >
                  <TrendingUp v-if="!sortDescending" class="w-4 h-4" />
                  <TrendingDown v-else class="w-4 h-4" />
                </button>
              </div>
            </div>
            
            <div class="overflow-x-auto">
              <table class="w-full text-left border-collapse">
                <thead>
                  <tr class="bg-white text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] border-b border-slate-100">
                    <th class="px-8 py-5">Ticket</th>
                    <th class="px-8 py-5">Referencia / Usuario</th>
                    <th class="px-8 py-5">Hora Pago</th>
                    <th class="px-8 py-5 text-center">Método</th>
                    <th class="px-8 py-5 text-right">Monto</th>
                    <th class="px-8 py-5 text-right">Propina</th>
                    <th class="px-8 py-5 text-center">Acciones</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-50">
                  <tr 
                    v-for="pedido in filteredPedidosDelDia" 
                    :key="pedido.id"
                    class="group hover:bg-slate-50/80 transition-all duration-300"
                  >
                    <td class="px-8 py-5">
                      <div class="font-black text-slate-800 tracking-tight">#{{ pedido.numero_display }}</div>
                    </td>
                    <td class="px-8 py-5">
                      <div class="flex flex-col">
                        <div class="flex items-center gap-2">
                          <span class="text-base">{{ getTipoOrdenEmoji(pedido.tipo_orden) }}</span>
                          <span class="font-bold text-slate-700">
                            {{ pedido.mesa ? 'Mesa ' + pedido.mesa : (pedido.nombre_cliente || 'Sin Nombre') }}
                          </span>
                        </div>
                        <div class="flex items-center gap-1.5 mt-1">
                          <Users class="w-3 h-3 text-slate-300" />
                          <span class="text-[9px] font-black text-slate-400 uppercase tracking-widest">{{ pedido.mesero_nombre || 'S/N' }}</span>
                        </div>
                      </div>
                    </td>
                    <td class="px-8 py-5">
                      <div class="text-xs font-bold text-slate-400 uppercase">{{ formatTime(pedido.fecha_pago || pedido.fecha_modificacion) }}</div>
                    </td>
                    <td class="px-8 py-5 text-center">
                      <span :class="['inline-flex items-center px-3 py-1 rounded-xl text-[10px] font-black uppercase tracking-widest border', getPaymentMethodColor(pedido.metodo_pago)]">
                        {{ getPaymentMethodIcon(pedido.metodo_pago) }}
                        <span class="ml-1.5">{{ pedido.metodo_pago || '---' }}</span>
                      </span>
                    </td>
                    <td class="px-8 py-5 text-right">
                      <div class="font-black text-slate-800 tracking-tight">${{ Number(pedido.total).toFixed(2) }}</div>
                    </td>
                    <td class="px-8 py-5 text-right">
                       <div v-if="Number(pedido.propina_total) > 0" class="font-black text-emerald-600">
                         +${{ Number(pedido.propina_total).toFixed(2) }}
                       </div>
                       <div v-else class="text-slate-200">---</div>
                    </td>
                    <td class="px-8 py-5 text-center">
                      <div class="flex justify-center gap-2">
                        <button 
                          @click="reimprimirTicketDesdeHistorial(pedido)"
                          class="p-2.5 text-slate-400 hover:text-[#00126D] hover:bg-white hover:shadow-sm border border-transparent hover:border-slate-200 rounded-xl transition-all"
                          title="Reimprimir Ticket"
                        >
                          <Printer class="w-4 h-4" />
                        </button>
                        <button 
                          @click="abrirEditarPropina(pedido)"
                          class="p-2.5 text-slate-400 hover:text-emerald-600 hover:bg-white hover:shadow-sm border border-transparent hover:border-slate-200 rounded-xl transition-all"
                          title="Editar Propina"
                        >
                          <CircleDollarSign class="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                </tbody>
                <tfoot v-if="filteredSummary" class="bg-slate-50/30 font-black text-slate-800 border-t border-slate-100">
                  <tr class="text-xs uppercase tracking-widest">
                    <td colspan="4" class="px-8 py-6 text-right text-slate-400">Total Filtro</td>
                    <td class="px-8 py-6 text-right text-lg tracking-tighter">${{ filteredSummary.total.toFixed(2) }}</td>
                    <td class="px-8 py-6 text-right text-emerald-600 text-lg tracking-tighter">+${{ filteredSummary.propina_total.toFixed(2) }}</td>
                    <td></td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>

        </div>
      </div>
        </div>

        <!-- Panel lateral de mesas (Modernized Premium) -->
        <div class="w-80 bg-white rounded-[2.5rem] shadow-xl shadow-slate-200/50 border border-slate-100 p-8 h-fit sticky top-[152px]">
          <div class="mb-8">
            <div class="flex items-center gap-3 mb-2">
              <div class="p-2 bg-blue-50 rounded-xl">
                <Map class="w-5 h-5 text-[#00126D]" />
              </div>
              <h3 class="text-xl font-black text-slate-800 tracking-tight">Estado de Mesas</h3>
            </div>
            <p class="text-[10px] font-black text-slate-400 uppercase tracking-widest leading-none">Clic en mesa ocupada para buscar</p>
          </div>

          <!-- Layout de mesas -->
          <div class="space-y-4">
            <div class="grid grid-cols-3 gap-3">
              <div v-for="(fila, index) in mesasLayout" :key="index" class="contents">
                <button
                  v-for="numeroMesa in fila"
                  :key="numeroMesa"
                  @click="handleMesaClick(numeroMesa)"
                  :disabled="getMesaEstado(numeroMesa) === 'libre'"
                  :class="[
                    'w-full aspect-[1/0.8] rounded-2xl flex items-center justify-center text-sm font-black transition-all duration-300 relative group overflow-hidden',
                    getMesaEstado(numeroMesa) === 'libre'
                      ? 'bg-slate-50 text-slate-300 border-2 border-slate-100'
                      : 'hover:scale-110 shadow-lg shadow-slate-200/50 cursor-pointer border-2 ring-4 ring-transparent hover:ring-blue-50',
                    getMesaClase(numeroMesa)
                  ]"
                >
                  <!-- Status Indicator -->
                  <div v-if="getMesaEstado(numeroMesa) !== 'libre'" class="absolute top-1.5 right-1.5 w-2 h-2 rounded-full border border-white shadow-sm" :class="getEstadoBadgeColor(getMesaEstado(numeroMesa))"></div>
                  
                  <span class="z-10">{{ numeroMesa }}</span>
                  
                  <!-- Hover Overlay -->
                  <div class="absolute inset-0 bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                </button>
              </div>
            </div>
          </div>

          <!-- Resumen de Estados Premium -->
          <div class="mt-10 pt-8 border-t border-slate-50">
            <h4 class="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] mb-6 flex items-center gap-3">
              <span class="w-2 h-2 bg-[#00126D] rounded-full"></span>
              Distribución actual
            </h4>
            <div class="space-y-3">
              <div 
                v-for="estado in ['pendiente', 'preparando', 'listo', 'entregado', 'cuenta_solicitada']" 
                :key="estado"
                class="flex items-center justify-between px-4 py-3 rounded-2xl hover:bg-slate-50 transition-all duration-300 group border border-transparent hover:border-slate-100"
              >
                <div class="flex items-center gap-3">
                  <div :class="[getEstadoBadgeColor(estado), 'w-3 h-3 rounded-full shadow-lg ring-4 ring-white']"></div>
                  <span class="text-xs font-black text-slate-600 group-hover:text-[#00126D] transition-colors uppercase tracking-widest">{{ getEstadoTexto(estado) }}</span>
                </div>
                <div class="bg-slate-100 px-3 py-1 rounded-xl text-[10px] font-black text-slate-500 group-hover:bg-[#00126D] group-hover:text-white transition-all shadow-inner">
                  {{ estadisticasOverview[estado as keyof typeof estadisticasOverview] || 0 }}
                </div>
              </div>
            </div>
          </div>
        </div>
        </div>
      </main>

    <!-- Modal: Editar propina (solo pagados) (Renovado Premium) -->
    <div
      v-if="showEditarPropinaModal && ticketParaPropina"
      class="fixed inset-0 flex items-center justify-center z-[150] p-4 backdrop-blur-sm bg-black/30"
      @click.self="cerrarEditarPropina"
    >
      <div class="bg-white rounded-2xl max-w-md w-full shadow-2xl border border-gray-200 overflow-hidden transform transition-all">
        <!-- Header con gradiente -->
        <div class="bg-gradient-to-r from-[#00126D] to-[#001E96] px-6 py-5 text-white">
          <div class="flex items-center justify-between">
            <h2 class="text-xl font-black flex items-center gap-2">
              <span>💰</span> Editar Propina
            </h2>
            <button
              @click="cerrarEditarPropina"
              class="text-white/70 hover:text-white transition-colors text-2xl font-bold leading-none"
              :disabled="savingPropinaManual"
            >
              ×
            </button>
          </div>
          <div class="mt-2 flex items-center gap-2 text-blue-100/80 text-sm font-medium">
            <span class="bg-blue-800/40 px-2 py-0.5 rounded">Ticket #{{ ticketParaPropina.numero_display }}</span>
            <span class="opacity-40">•</span>
            <span>{{ ticketParaPropina.mesa ? 'Mesa ' + ticketParaPropina.mesa : ticketParaPropina.nombre_cliente }}</span>
          </div>
        </div>

        <div class="p-6 space-y-6">
          <!-- Tipo de propina (Segmented Control) -->
          <div>
            <label class="block text-xs font-black text-gray-400 uppercase tracking-widest mb-3">
              Tipo de propina
            </label>
            <div class="flex p-1 bg-gray-100 rounded-xl">
              <button 
                v-for="tipo in tipTypeOptions" 
                :key="tipo"
                @click="propinaTipoManual = tipo"
                :class="[
                  'flex-1 py-2.5 text-sm font-bold rounded-lg transition-all capitalize flex items-center justify-center gap-2',
                  propinaTipoManual === tipo 
                    ? 'bg-white shadow-sm text-[#00126D] scale-[1.02]' 
                    : 'text-gray-500 hover:text-gray-700'
                ]"
              >
                <span>{{ tipo === 'efectivo' ? '💵' : '💳' }}</span>
                {{ tipo === 'tarjeta' ? 'Tarjeta' : tipo }}
              </button>
            </div>
          </div>

          <!-- Monto Input -->
          <div>
            <label class="block text-xs font-black text-gray-400 uppercase tracking-widest mb-3">
              Monto de la propina
            </label>
            <div class="relative group">
              <div class="absolute left-4 top-1/2 -translate-y-1/2 text-2xl font-bold text-gray-400 group-focus-within:text-[#00126D] transition-colors">$</div>
              <input
                v-model="propinaMontoManual"
                type="number"
                min="0"
                step="0.01"
                inputmode="decimal"
                class="w-full pl-10 pr-4 py-4 bg-gray-50 border-2 border-transparent rounded-2xl text-2xl font-black text-[#00126D] focus:bg-white focus:border-[#FDB700] focus:ring-4 focus:ring-[#FDB700]/10 transition-all outline-none"
                placeholder="0.00"
              />
            </div>
            
            <!-- Banner de información -->
            <div class="mt-4 flex items-start gap-3 p-3 bg-amber-50 rounded-xl border border-amber-100">
              <span class="text-amber-500">⚠️</span>
              <p class="text-[11px] font-medium text-amber-800 leading-tight">
                Al guardar, se sobrescribirá cualquier registro previo de propina para este ticket.
              </p>
            </div>
          </div>
        </div>

        <!-- Footer con botones de acción -->
        <div class="px-6 py-5 bg-gray-50 border-t border-gray-100 flex gap-3">
          <button
            @click="cerrarEditarPropina"
            class="flex-1 py-3 border-2 border-gray-200 rounded-xl text-gray-600 font-bold hover:bg-white hover:border-gray-300 transition-all active:scale-95"
            :disabled="savingPropinaManual"
          >
            Cancelar
          </button>
          <button
            @click="guardarPropinaManual"
            class="flex-[1.5] py-3 bg-[#00126D] text-white rounded-xl font-bold shadow-lg shadow-blue-900/20 hover:bg-blue-900 hover:-translate-y-0.5 transition-all active:scale-95 disabled:opacity-50 disabled:translate-y-0"
            :disabled="savingPropinaManual"
          >
            <span v-if="savingPropinaManual" class="flex items-center justify-center gap-2">
              <svg class="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
              Guardando...
            </span>
            <span v-else>Confirmar Cambios</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Modal de procesamiento de pago - Premium -->
    <div
      v-if="selectedPedido"
      class="fixed inset-0 flex items-center justify-center z-[150] p-4 bg-slate-900/40 backdrop-blur-sm"
      @click.self="closeModal"
    >
      <div class="bg-white rounded-2xl max-w-xl w-full shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh] animate-in fade-in zoom-in duration-300">
        <!-- Header Premium -->
        <div class="px-6 py-4 border-b border-slate-100 bg-[#00126D]">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-xl bg-white/10 flex items-center justify-center text-white">
                <CreditCard class="w-4 h-4" />
              </div>
              <div>
                <h2 class="text-lg font-bold text-white leading-tight">
                  Procesar Pago
                </h2>
                <p class="text-xs text-blue-100/70">Pedido #{{ selectedPedido.numero_display }}</p>
              </div>
            </div>
            <button
              @click="closeModal"
              class="w-8 h-8 flex items-center justify-center rounded-lg text-white/70 hover:text-white hover:bg-white/10 transition-colors"
            >
              <X class="w-5 h-5" />
            </button>
          </div>
        </div>

        <!-- Contenido del modal -->
        <div class="p-4 md:p-6 overflow-y-auto flex-1 min-h-0 custom-scrollbar">
          <!-- Info básica con badges modernos -->
          <div class="flex flex-wrap gap-2 mb-4">
            <div v-if="selectedPedido.mesa" class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-blue-50 text-blue-700 text-xs font-bold ring-1 ring-inset ring-blue-700/10">
              <span class="text-sm">🪑</span> Mesa {{ selectedPedido.mesa }}
            </div>
            <div v-if="selectedPedido.nombre_cliente && selectedPedido.tipo_orden === 'llevar'" class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-50 text-emerald-700 text-xs font-bold ring-1 ring-inset ring-emerald-700/10">
              <span class="text-sm">📦</span> {{ selectedPedido.nombre_cliente }}
            </div>
            <div class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-slate-100 text-slate-600 text-xs font-bold">
              <Clock class="w-3.5 h-3.5" /> {{ formatTime(selectedPedido.fecha_creacion) }}
            </div>
          </div>

          <!-- Lista de artículos refinada -->
          <div v-if="selectedPedido.articulos_pedido && selectedPedido.articulos_pedido.length > 0" class="mb-4">
            <div class="flex items-center justify-between mb-2">
              <h4 class="text-xs font-bold text-slate-400 uppercase tracking-widest">Resumen de Cuenta</h4>
              <span class="text-xs text-slate-400">{{ selectedPedido.articulos_pedido.length }} ítems</span>
            </div>
            <div class="bg-slate-50/50 rounded-xl p-3 max-h-32 overflow-y-auto border border-slate-100 custom-scrollbar">
              <div
                v-for="articulo in selectedPedido.articulos_pedido"
                :key="articulo.id"
                class="flex justify-between items-center py-2.5 group first:pt-0 last:pb-0 border-b border-slate-100 last:border-0"
              >
                <div class="flex-1 min-w-0 pr-4">
                  <div class="flex items-baseline gap-2">
                    <span class="text-xs font-bold text-slate-400">x{{ articulo.cantidad }}</span>
                    <h5 class="text-sm font-semibold text-slate-800 truncate">{{ articulo.platillo?.nombre || 'Producto' }}</h5>
                  </div>
                  <p v-if="articulo.modificaciones" class="text-[10px] text-slate-500 mt-0.5 italic">
                    {{ articulo.modificaciones }}
                  </p>
                </div>
                <div class="text-sm font-bold text-slate-900 tabular-nums">
                  ${{ Number(articulo.precio_cobrado).toFixed(2) }}
                </div>
              </div>
            </div>
          </div>

          <!-- Total Impactante -->
          <div class="relative overflow-hidden bg-slate-900 rounded-2xl p-4 mb-4 text-white shadow-lg shadow-slate-200">
            <!-- Círculos decorativos -->
            <div class="absolute -right-4 -top-4 w-20 h-20 bg-white/5 rounded-full blur-2xl"></div>
            <div class="absolute -left-4 -bottom-4 w-16 h-16 bg-blue-500/10 rounded-full blur-xl"></div>
            
            <div class="relative flex items-center justify-between">
              <div>
                <p class="text-[10px] uppercase tracking-widest text-slate-400 font-bold mb-1">Total Final</p>
                <div class="flex items-baseline gap-1">
                  <span class="text-lg font-medium text-slate-400">$</span>
                  <span class="text-4xl font-black text-white tracking-tight tabular-nums">
                    {{ Number(selectedPedido.total).toFixed(2) }}
                  </span>
                </div>
              </div>
              <div class="p-3 bg-white/10 rounded-xl border border-white/10">
                <Receipt class="w-6 h-6 text-blue-400" />
              </div>
            </div>
          </div>

          <!-- Botón dividir cuenta (Elegante) -->
          <button
            v-if="canSplitSelectedPedido"
            @click="openSplitModalForPedido(selectedPedido)"
            :disabled="processingPayment"
            class="w-full mb-4 py-2.5 px-4 flex items-center justify-center gap-2 bg-amber-50 hover:bg-amber-100 text-amber-700 text-sm font-bold rounded-xl border border-amber-200/50 transition-all active:scale-[0.98] disabled:opacity-50"
          >
            <Scissors class="w-4 h-4" />
            Dividir Cuenta
          </button>

          <!-- Métodos de Pago Premium -->
          <div class="grid grid-cols-1 gap-3">
            <button
              @click="procesarPago(selectedPedido, 'efectivo')"
              :disabled="processingPayment"
              class="group relative flex items-center justify-between p-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl transition-all shadow-md shadow-emerald-200 active:scale-[0.98] disabled:opacity-50 overflow-hidden"
            >
              <div class="flex items-center gap-3 z-10">
                <div class="w-10 h-10 rounded-lg bg-white/20 flex items-center justify-center group-hover:scale-110 transition-transform">
                  <Banknote class="w-6 h-6" />
                </div>
                <span class="font-bold tracking-wide">EFECTIVO</span>
              </div>
              <ChevronRight class="w-5 h-5 opacity-50 z-10" />
              <div class="absolute right-0 bottom-0 w-24 h-24 bg-white/10 rounded-full translate-x-12 translate-y-12 blur-3xl"></div>
            </button>

            <div class="grid grid-cols-2 gap-3">
              <button
                @click="procesarPago(selectedPedido, 'tarjeta')"
                :disabled="processingPayment"
                class="group flex flex-col items-center justify-center gap-2 p-4 bg-[#00126D] hover:bg-[#000E5A] text-white rounded-xl transition-all shadow-md shadow-blue-200 active:scale-[0.98] disabled:opacity-50"
              >
                <CreditCard class="w-6 h-6 group-hover:scale-110 transition-transform" />
                <span class="text-xs font-bold tracking-widest">TARJETA</span>
              </button>
              
              <button
                @click="procesarPago(selectedPedido, 'transferencia')"
                :disabled="processingPayment"
                class="group flex flex-col items-center justify-center gap-2 p-4 bg-purple-600 hover:bg-purple-700 text-white rounded-xl transition-all shadow-md shadow-purple-200 active:scale-[0.98] disabled:opacity-50"
              >
                <Smartphone class="w-6 h-6 group-hover:scale-110 transition-transform" />
                <span class="text-xs font-bold tracking-widest">TRANSFER</span>
              </button>
            </div>
          </div>

          <!-- Botón cerrar refinado -->
          <button
            @click="closeModal"
            :disabled="processingPayment"
            class="w-full mt-8 py-3 text-slate-400 hover:text-slate-600 text-sm font-bold transition-colors"
          >
            Volver a la caja
          </button>
        </div>
      </div>
    </div>

    <!-- Modal Calculadora de Efectivo Profesional -->
    <div
      v-if="showEfectivoCalculator && selectedPedido"
      class="fixed inset-0 flex items-center justify-center z-[160] p-4 bg-slate-900/40 backdrop-blur-sm"
      @click.self="cerrarCalculadoraEfectivo"
    >
      <div class="bg-white rounded-2xl max-w-lg w-full shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh] animate-in fade-in slide-in-from-bottom-8 duration-300">
        <!-- Header profesional -->
        <div class="bg-gradient-to-r from-green-600 to-green-700 px-6 py-4">
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
                ref="efectivoInput"
                v-model="efectivoRecibido"
                @input="calcularCambio"
                type="number"
                step="0.01"
                min="0"
                class="w-full pl-8 pr-4 py-4 text-2xl font-bold border-2 border-gray-300 rounded-lg focus:border-green-500 focus:ring-2 focus:ring-green-200 text-center"
                placeholder="0.00"
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
      class="fixed inset-0 flex items-center justify-center z-[165] p-4 bg-slate-900/40 backdrop-blur-sm"
      @click.self="cerrarModalPropina"
    >
      <div class="bg-white rounded-2xl max-w-lg w-full shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh] animate-in fade-in slide-in-from-bottom-8 duration-300">
        <!-- Header profesional -->
        <div class="bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-4">
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
                @click="aplicarPropinaPorcentaje(5)"
                class="py-3 bg-blue-100 hover:bg-blue-200 text-blue-700 font-bold rounded-lg transition-all hover:scale-105"
              >
                5%
              </button>
              <button
                @click="aplicarPropinaPorcentaje(10)"
                class="py-3 bg-blue-200 hover:bg-blue-300 text-blue-800 font-bold rounded-lg transition-all hover:scale-105"
              >
                10%
              </button>
              <button
                @click="aplicarPropinaPorcentaje(15)"
                class="py-3 bg-blue-300 hover:bg-blue-400 text-blue-900 font-bold rounded-lg transition-all hover:scale-105"
              >
                15%
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
    <!-- Modal de Detalles del Pedido - Premium Refined -->
    <div
      v-if="showDetailsModal && selectedPedidoDetails"
      class="fixed inset-0 flex items-center justify-center z-[150] p-4 bg-slate-900/40 backdrop-blur-sm"
      @click.self="closeDetailsModal"
    >
      <div class="bg-white rounded-2xl max-w-xl w-full shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh] animate-in fade-in slide-in-from-bottom-8 duration-300">
        <!-- Header - Mesa/Cliente como título principal -->
        <div class="px-6 py-4 border-b border-white/10 bg-[#00126D]">
          <div class="flex items-start justify-between">
            <div class="flex items-center gap-3 min-w-0 flex-1">
              <div class="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center text-white flex-shrink-0">
                <span v-if="selectedPedidoDetails.mesa" class="text-lg font-black">{{ selectedPedidoDetails.mesa }}</span>
                <User v-else class="w-5 h-5" />
              </div>
              <div class="min-w-0 flex-1">
                <!-- Título principal: Mesa o Cliente -->
                <h2 class="text-2xl font-black text-white tracking-tight leading-tight truncate">
                  <span v-if="selectedPedidoDetails.mesa">Mesa {{ selectedPedidoDetails.mesa }}</span>
                  <span v-else-if="selectedPedidoDetails.nombre_cliente">{{ selectedPedidoDetails.nombre_cliente }}</span>
                  <span v-else>Pedido #{{ selectedPedidoDetails.numero_display }}</span>
                </h2>
                <!-- Subtítulo: número de pedido + estado -->
                <div class="flex items-center gap-2 mt-1 flex-wrap">
                  <span class="text-[10px] text-blue-200/70 font-bold uppercase tracking-widest">
                    #{{ selectedPedidoDetails.numero_display }}
                  </span>
                  <span class="text-blue-200/40">·</span>
                  <span :class="[getEstadoColor(selectedPedidoDetails.estado), 'px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider text-white']">{{ getEstadoTexto(selectedPedidoDetails.estado) }}</span>
                  <span class="text-blue-200/40">·</span>
                  <span class="flex items-center gap-1 text-[10px] text-blue-200/70 font-bold">
                    <Clock class="w-3 h-3" />
                    {{ formatTime(selectedPedidoDetails.fecha_creacion) }}
                  </span>
                </div>
              </div>
            </div>
            <div class="flex items-center gap-2 flex-shrink-0 ml-2">
              <button
                @click="openEditPedido(selectedPedidoDetails)"
                class="w-9 h-9 flex items-center justify-center rounded-xl bg-white/10 hover:bg-white/20 text-white transition-all active:scale-90"
                title="Editar pedido"
              >
                <Edit3 class="w-4 h-4" />
              </button>
              <button
                @click="closeDetailsModal"
                class="w-9 h-9 flex items-center justify-center rounded-xl text-white/50 hover:text-white hover:bg-white/10 transition-colors"
              >
                <X class="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>

        <!-- Contenido scrollable -->
        <div class="p-4 md:p-6 overflow-y-auto flex-1 min-h-0 custom-scrollbar">
          <!-- Items List Refined -->
          <div v-if="selectedPedidoDetails.articulos_pedido && selectedPedidoDetails.articulos_pedido.length > 0" class="mb-4">
            <div class="flex items-center justify-between mb-2">
              <h4 class="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">Composición del Pedido</h4>
              <span class="px-2 py-0.5 rounded-md bg-slate-100 text-slate-500 text-[10px] font-bold">{{ selectedPedidoDetails.articulos_pedido.length }} platillos</span>
            </div>
            <div class="bg-slate-50/50 rounded-2xl p-2 border border-slate-100 max-h-40 overflow-y-auto custom-scrollbar">
              <div
                v-for="articulo in selectedPedidoDetails.articulos_pedido"
                :key="articulo.id"
                class="flex justify-between items-center p-3 hover:bg-white rounded-xl transition-all border border-transparent hover:border-slate-100 hover:shadow-sm mb-1 last:mb-0 group"
              >
                <div class="flex-1 min-w-0 pr-4">
                  <div class="flex items-center gap-2">
                    <span class="w-6 h-6 flex items-center justify-center rounded-md bg-slate-200/50 text-[10px] font-black text-slate-600">
                      {{ articulo.cantidad }}
                    </span>
                    <h5 class="text-sm font-bold text-slate-800 truncate group-hover:text-[#00126D] transition-colors">{{ articulo.platillo?.nombre || 'Producto' }}</h5>
                  </div>
                  <div class="flex items-center gap-3 mt-1.5 ml-8">
                    <span :class="[getArticuloEstadoClass(articulo.estado_item), 'text-[9px] font-black uppercase tracking-tighter px-2 py-0.5 rounded-md']">
                      {{ getArticuloEstadoLabel(articulo.estado_item) }}
                    </span>
                    <span v-if="articulo.modificaciones" class="text-[10px] text-slate-400 italic font-medium truncate">
                      "{{ articulo.modificaciones }}"
                    </span>
                  </div>
                </div>
                <div class="text-sm font-black text-slate-900 tabular-nums">
                  ${{ Number(articulo.precio_cobrado).toFixed(2) }}
                </div>
              </div>
            </div>
          </div>

          <!-- Total Footer -->
          <div class="relative overflow-hidden bg-[#FDB700] p-4 rounded-xl mb-4 group">
            <div class="absolute -right-4 -bottom-4 w-24 h-24 bg-white/10 rounded-full group-hover:scale-125 transition-transform duration-700"></div>
            <div class="relative flex items-center justify-between text-white">
              <div class="flex flex-col">
                <span class="text-[10px] font-black uppercase tracking-[0.2em] opacity-80">Subtotal del Pedido</span>
                <span class="text-3xl font-black tabular-nums tracking-tighter">
                  ${{ Number(selectedPedidoDetails.total).toFixed(2) }}
                </span>
              </div>
              <div class="w-14 h-14 bg-white/20 rounded-xl flex items-center justify-center backdrop-blur-md border border-white/30">
                <ReceiptText class="w-7 h-7" />
              </div>
            </div>
          </div>

          <!-- Quick Actions Grid -->
          <div class="grid grid-cols-1 gap-3">
            <div class="grid grid-cols-2 gap-3">
              <button
                v-if="canSplitDetailsPedido"
                @click="openSplitModalForPedido(selectedPedidoDetails); closeDetailsModal()"
                class="flex flex-col items-center justify-center p-4 bg-slate-50 hover:bg-slate-100 text-slate-700 rounded-2xl border border-slate-200 transition-all active:scale-95 group"
              >
                <Scissors class="w-5 h-5 mb-1 group-hover:rotate-12 transition-transform" />
                <span class="text-[10px] font-black uppercase tracking-widest">Dividir</span>
              </button>

              <button
                v-if="!['pagado', 'cancelado', 'dividido'].includes(selectedPedidoDetails.estado)"
                @click="imprimirTicketSeparado(selectedPedidoDetails)"
                :disabled="isPrintingTicket"
                class="flex flex-col items-center justify-center p-4 bg-slate-900 hover:bg-black text-white rounded-2xl transition-all active:scale-95 group disabled:opacity-50"
              >
                <Printer class="w-5 h-5 mb-1 group-hover:scale-110 transition-transform" />
                <span class="text-[10px] font-black uppercase tracking-widest">
                  {{ isPrintingTicket ? 'Espere...' : 'Imprimir' }}
                </span>
              </button>
            </div>

            <!-- Primary Action Call -->
            <button
              v-if="selectedPedidoDetails.estado === 'entregado'"
              @click="solicitarCuenta(selectedPedidoDetails); closeDetailsModal()"
              class="w-full py-3 bg-[#00126D] hover:bg-[#000E5A] text-white font-black uppercase tracking-widest rounded-xl shadow-lg shadow-blue-200 flex items-center justify-center gap-3 transition-all active:scale-[0.98]"
            >
              <CreditCard class="w-5 h-5" />
              SOLICITAR CUENTA
            </button>

            <button
              v-if="selectedPedidoDetails.estado === 'cuenta_solicitada'"
              @click="selectedPedido = selectedPedidoDetails; closeDetailsModal()"
              class="w-full py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-black uppercase tracking-widest rounded-xl shadow-lg shadow-emerald-200 flex items-center justify-center gap-3 transition-all active:scale-[0.98]"
            >
              <Wallet class="w-5 h-5" />
              COBRAR AHORA
            </button>

            <!-- Dangerous Action -->
            <button
              v-if="!['pagado', 'cancelado', 'dividido'].includes(selectedPedidoDetails.estado)"
              @click="mostrarConfirmacionCancelacion(selectedPedidoDetails)"
              class="group flex items-center justify-center gap-2 py-3 text-red-400 hover:text-red-500 font-bold text-xs transition-colors"
            >
              <Trash2 class="w-3.5 h-3.5 group-hover:rotate-12 transition-transform" />
              CANCELAR PEDIDO
            </button>
          </div>

          <button
            @click="closeDetailsModal"
            class="w-full mt-6 py-2 text-slate-400 hover:text-slate-600 text-xs font-bold transition-colors"
          >
            Regresar
          </button>
        </div>
      </div>
    </div>

    <!-- Modal dividir cuenta -->
    <div
      v-if="showSplitModal && splitPedido"
      class="fixed inset-0 z-[180] flex items-center justify-center p-4 sm:p-6"
      @click.self="closeSplitModal"
    >
      <div class="absolute inset-0 bg-slate-900/40 backdrop-blur-sm transition-opacity"></div>

      <div class="relative bg-white rounded-3xl max-w-5xl w-full mx-auto shadow-2xl overflow-hidden flex flex-col max-h-full">
        <div class="px-6 py-5 bg-gradient-to-r from-amber-500 to-amber-600 text-white flex items-center justify-between flex-shrink-0">
          <div>
            <div class="text-sm font-semibold opacity-90 uppercase tracking-widest">Dividir cuenta</div>
            <div class="text-2xl font-black">Pedido #{{ splitPedido.numero_display }}</div>
          </div>
          <button
            @click="closeSplitModal"
            class="text-white/80 hover:text-white bg-white/10 hover:bg-white/20 w-10 h-10 rounded-full flex items-center justify-center transition-colors"
          >
            <X class="w-6 h-6" />
          </button>
        </div>

        <div class="p-6 overflow-y-auto flex-grow scrollbar-thin scrollbar-thumb-gray-200">
          <!-- Info del pedido -->
          <div class="flex items-center justify-between mb-4">
            <div class="text-sm text-gray-700">
              <div v-if="splitPedido.mesa" class="font-semibold text-blue-700">🪑 Mesa {{ splitPedido.mesa }}</div>
              <div v-else-if="splitPedido.nombre_cliente" class="font-semibold text-green-700">👤 {{ splitPedido.nombre_cliente }}</div>
              <div class="text-xs text-gray-500 mt-0.5">Total: <span class="font-bold text-gray-800">${{ Number(splitPedido.total).toFixed(2) }}</span></div>
            </div>
          </div>

          <!-- Tabs de modo -->
          <div class="flex gap-2 mb-5 border-b border-gray-200 pb-3">
            <button
              @click="splitModo = 'articulo'"
              :disabled="splitProcessing || splitPrintPaused"
              :class="splitModo === 'articulo'
                ? 'bg-amber-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
              class="px-4 py-2 rounded-lg text-sm font-semibold transition-all disabled:opacity-50"
            >
              Por artículo
            </button>
            <button
              @click="splitModo = 'equitativo'"
              :disabled="splitProcessing || splitPrintPaused"
              :class="splitModo === 'equitativo'
                ? 'bg-amber-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
              class="px-4 py-2 rounded-lg text-sm font-semibold transition-all disabled:opacity-50"
            >
              Equitativo
            </button>
            <button
              @click="splitModo = 'montos'"
              :disabled="splitProcessing || splitPrintPaused"
              :class="splitModo === 'montos'
                ? 'bg-amber-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
              class="px-4 py-2 rounded-lg text-sm font-semibold transition-all disabled:opacity-50"
            >
              Por montos
            </button>
          </div>

          <!-- ── MODO POR ARTÍCULO ─────────────────────────────────────────── -->
          <template v-if="splitModo === 'articulo'">
            <div class="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 mb-4">
              <div class="text-sm text-gray-500">
                <span class="font-semibold text-amber-600">Tip:</span> Asigna las cantidades a cada cuenta usando los controles. Los artículos sin asignar se mostrarán en rojo.
              </div>
              <div class="flex flex-col sm:flex-row sm:items-center gap-3">
                <label class="text-sm font-semibold text-gray-700">Cuentas:</label>
                <select
                  v-model.number="splitNumCuentas"
                  class="border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white font-bold text-amber-700 w-full sm:w-auto"
                  :disabled="splitProcessing || splitPrintPaused"
                >
                  <option :value="2">2 Cuentas</option>
                  <option :value="3">3 Cuentas</option>
                  <option :value="4">4 Cuentas</option>
                  <option :value="5">5 Cuentas</option>
                </select>
              </div>
            </div>

            <div class="bg-gray-50 border border-gray-200 rounded-xl p-3 sm:p-4 mb-5 max-h-[50vh] overflow-y-auto w-full">
              <div class="space-y-3 sm:space-y-4">
                <div v-for="articulo in (splitPedido.articulos_pedido || [])" :key="articulo.id" class="bg-white border border-gray-200 rounded-xl p-3 sm:p-4 shadow-sm flex flex-col gap-3">
                  
                  <!-- Info del artículo -->
                  <div class="w-full flex justify-between items-start gap-2">
                    <div>
                      <div class="font-bold text-gray-800 text-sm sm:text-base">{{ articulo.platillo?.nombre || 'Producto' }}</div>
                      <div v-if="articulo.modificaciones" class="text-xs text-gray-500 line-clamp-2 mt-0.5">{{ articulo.modificaciones }}</div>
                    </div>
                    
                    <div class="flex-shrink-0 flex items-center justify-between bg-amber-50 rounded-lg px-2 sm:px-3 py-1 sm:py-1.5 border"
                         :class="{'border-red-200 bg-red-50': splitRestantePorArticulo[articulo.id] > 0, 'border-green-200 bg-green-50': splitRestantePorArticulo[articulo.id] === 0}">
                      <span class="font-black text-sm sm:text-base" :class="{'text-red-600': splitRestantePorArticulo[articulo.id] > 0, 'text-green-700': splitRestantePorArticulo[articulo.id] === 0}">
                        Faltan: {{ splitRestantePorArticulo[articulo.id] }}
                      </span>
                    </div>
                  </div>

                  <!-- Controles por cuenta -->
                  <div class="grid grid-cols-2 md:grid-cols-4 lg:flex gap-2 w-full mt-2">
                    <div v-for="idx in splitCuentasVisibles" :key="idx" class="flex-1 min-w-0 bg-gray-50 border border-gray-200 rounded-lg p-2 flex flex-col items-center">
                      <div class="text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-2">Cuenta {{ idx + 1 }}</div>
                      <div class="flex items-center gap-1 sm:gap-2">
                        <button 
                          @click="decrementarSplitArticulo(articulo.id, idx)"
                          :disabled="splitProcessing || splitPrintPaused || (splitAsignaciones[articulo.id] || [])[idx] === 0"
                          class="w-6 h-6 sm:w-8 sm:h-8 rounded-full flex items-center justify-center bg-white border border-gray-300 text-gray-600 hover:bg-red-50 hover:text-red-600 hover:border-red-300 disabled:opacity-30 transition-colors shadow-sm font-bold text-lg leading-none"
                        >−</button>
                        <span class="font-black text-sm sm:text-lg text-gray-800 min-w-[1.5rem] sm:min-w-[2rem] text-center">
                          {{ (splitAsignaciones[articulo.id] || [])[idx] || 0 }}
                        </span>
                        <button 
                          @click="incrementarSplitArticulo(articulo.id, idx)"
                          :disabled="splitProcessing || splitPrintPaused || splitRestantePorArticulo[articulo.id] === 0"
                          class="w-6 h-6 sm:w-8 sm:h-8 rounded-full flex items-center justify-center bg-white border border-gray-300 text-gray-600 hover:bg-green-50 hover:text-green-600 hover:border-green-300 disabled:opacity-30 transition-colors shadow-sm font-bold text-lg leading-none"
                        >+</button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
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
                  <button @click="reintentarImpresionSplit" :disabled="splitProcessing" class="py-3 bg-green-600 hover:bg-green-700 text-white font-bold rounded-lg">Reintentar</button>
                  <button @click="cancelarImpresionesRestantes" :disabled="splitProcessing" class="py-3 bg-gray-200 hover:bg-gray-300 text-gray-800 font-bold rounded-lg">Cancelar</button>
                </div>
                <button @click="closeSplitModal" :disabled="splitProcessing" class="w-full mt-3 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold rounded-lg">Cerrar</button>
                <div v-if="!splitIsValid" class="text-xs text-gray-500 mt-2">Tip: cada articulo debe sumar exactamente su total entre cuentas.</div>
              </div>
            </div>
          </template>

          <!-- ── MODO EQUITATIVO ──────────────────────────────────────────── -->
          <template v-else-if="splitModo === 'equitativo'">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <!-- Panel izquierdo: configuración -->
              <div class="bg-gray-50 border border-gray-200 rounded-xl p-5 flex flex-col">
                <div class="text-sm font-bold text-gray-700 mb-4">Dividir en partes iguales</div>
                <div class="flex items-center justify-between bg-white border border-gray-200 rounded-xl p-2 mb-5">
                  <button @click="splitEquitativoN = Math.max(2, splitEquitativoN - 1)" :disabled="splitProcessing || splitPrintPaused || splitEquitativoN <= 2" class="w-10 h-10 flex items-center justify-center bg-gray-100 hover:bg-red-50 text-gray-600 rounded-lg disabled:opacity-50 font-bold text-xl transition-colors">-</button>
                  <div class="text-center">
                    <span class="block text-2xl font-black text-gray-800">{{ splitEquitativoN }}</span>
                    <span class="block text-[10px] text-gray-500 uppercase tracking-widest -mt-1 font-bold">Personas</span>
                  </div>
                  <button @click="splitEquitativoN++" :disabled="splitProcessing || splitPrintPaused" class="w-10 h-10 flex items-center justify-center bg-gray-100 hover:bg-green-50 text-gray-600 rounded-lg disabled:opacity-50 font-bold text-xl transition-colors">+</button>
                </div>
                
                <div class="bg-amber-50 border border-amber-200 rounded-xl p-4 text-center mt-auto shadow-inner">
                  <div class="text-xs font-bold uppercase tracking-wider text-amber-600 mb-1">Cada persona paga</div>
                  <div class="text-4xl font-black text-amber-700 tracking-tight">${{ montoEquitativo.toFixed(2) }}</div>
                  <div class="text-xs text-amber-600/70 mt-1 font-semibold">Total a dividir: ${{ totalPedidoNum.toFixed(2) }}</div>
                </div>

                <!-- Visual tickets -->
                <div class="mt-4 flex flex-wrap gap-2 justify-center max-h-32 overflow-y-auto w-full">
                  <div v-for="i in Math.min(splitEquitativoN, 10)" :key="i" class="w-16 h-20 bg-white border border-gray-200 border-x-dashed border-x-2 rounded-sm shadow-sm flex flex-col items-center justify-center text-center">
                    <span class="text-[9px] text-gray-400 font-bold mb-1 border-b border-gray-100 w-full pb-1">T-{{i}}</span>
                    <span class="text-xs font-black text-gray-800">${{ montoEquitativo.toFixed(0) }}</span>
                  </div>
                  <div v-if="splitEquitativoN > 10" class="w-16 h-20 flex items-center justify-center text-gray-400 font-bold text-sm bg-gray-100 rounded-lg">
                    +{{ splitEquitativoN - 10 }}
                  </div>
                </div>
              </div>

              <!-- Panel derecho: acciones -->
              <div class="bg-white border border-gray-200 rounded-xl p-5">
                <div v-if="splitPrintPaused" class="bg-red-50 border border-red-200 rounded-lg p-3 mb-3">
                  <div class="text-sm font-bold text-red-700">Impresion detenida</div>
                  <div class="text-xs text-red-700 mt-1">{{ splitPrintError }}</div>
                </div>
                <div class="text-xs text-gray-500 mb-3">
                  Se crearán {{ splitEquitativoN }} sub-pedidos de ${{ montoEquitativo.toFixed(2) }} c/u. Cada uno se cobra por separado con su propio método de pago.
                </div>
                <button
                  v-if="!splitPrintPaused"
                  @click="dividirCuentaEquitativoConfirmar"
                  :disabled="splitProcessing || !equitativoValido"
                  class="w-full py-3 bg-amber-600 hover:bg-amber-700 disabled:bg-gray-300 text-white font-bold rounded-lg transition-all disabled:cursor-not-allowed"
                >
                  {{ splitProcessing ? 'Procesando...' : '✅ Dividir y generar tickets' }}
                </button>
                <div v-else class="grid grid-cols-2 gap-3">
                  <button @click="reintentarImpresionSplit" :disabled="splitProcessing" class="py-3 bg-green-600 hover:bg-green-700 text-white font-bold rounded-lg">Reintentar</button>
                  <button @click="cancelarImpresionesRestantes" :disabled="splitProcessing" class="py-3 bg-gray-200 hover:bg-gray-300 text-gray-800 font-bold rounded-lg">Cancelar</button>
                </div>
                <button @click="closeSplitModal" :disabled="splitProcessing" class="w-full mt-3 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold rounded-lg">Cerrar</button>
              </div>
            </div>
          </template>

          <!-- ── MODO POR MONTOS ──────────────────────────────────────────── -->
          <template v-else-if="splitModo === 'montos'">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <!-- Panel izquierdo: ingresar pagos -->
              <div class="bg-gray-50 border border-gray-200 rounded-xl p-5">
                <div class="text-sm font-bold text-gray-700 mb-3">Registrar pagos</div>

                <!-- Input agregar monto -->
                <div class="flex flex-col gap-2 mb-4">
                  <div class="flex gap-2">
                    <div class="relative flex-1">
                      <span class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 font-bold">$</span>
                      <input
                        type="number"
                        min="0.01"
                        step="0.01"
                        placeholder="0.00"
                        v-model="splitMontoInput"
                        :disabled="splitProcessing || splitPrintPaused"
                        @keydown.enter="agregarMontoPago"
                        class="w-full border border-gray-300 rounded-lg pl-7 pr-3 py-2 text-sm focus:ring-amber-500 focus:border-amber-500"
                      />
                    </div>
                    <button
                      @click="agregarMontoPago"
                      :disabled="splitProcessing || splitPrintPaused || !splitMontoInput || parseFloat(splitMontoInput) <= 0"
                      class="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white font-bold rounded-lg text-sm disabled:opacity-50 transition-colors"
                    >
                      + Agregar
                    </button>
                  </div>
                  <button 
                    v-if="montoRestante > 0.05"
                    @click="splitMontoInput = montoRestante.toFixed(2)"
                    class="text-xs text-amber-700 bg-amber-50 border border-amber-200 py-1.5 px-3 rounded-md hover:bg-amber-100 self-start font-semibold transition-colors"
                  >
                    Sugerir monto restante: ${{ montoRestante.toFixed(2) }}
                  </button>
                </div>

                <!-- Lista de pagos -->
                <div class="space-y-2 max-h-52 overflow-y-auto">
                  <div
                    v-for="(pago, idx) in splitMontos"
                    :key="idx"
                    class="flex items-center justify-between bg-white border border-gray-200 rounded-lg px-3 py-2"
                  >
                    <span class="text-xs text-gray-500">Persona {{ idx + 1 }}</span>
                    <span class="font-bold text-gray-800">${{ pago.monto.toFixed(2) }}</span>
                    <button
                      @click="eliminarMontoPago(idx)"
                      :disabled="splitProcessing || splitPrintPaused"
                      class="text-red-400 hover:text-red-600 font-bold text-lg leading-none disabled:opacity-40"
                    >×</button>
                  </div>
                  <div v-if="!splitMontos.length" class="text-center text-xs text-gray-400 py-4">
                    Agrega el monto de cada persona
                  </div>
                </div>
              </div>

              <!-- Panel derecho: resumen y confirmación -->
              <div class="bg-white border border-gray-200 rounded-xl p-5">
                <!-- Barra de progreso -->
                <div class="mb-4">
                  <div class="flex justify-between text-xs font-semibold mb-1">
                    <span class="text-gray-600">Cobrado</span>
                    <span :class="montosValidos ? 'text-green-600' : 'text-gray-700'">${{ totalMontosCobrados.toFixed(2) }} / ${{ totalPedidoNum.toFixed(2) }}</span>
                  </div>
                  <div class="w-full bg-gray-200 rounded-full h-2">
                    <div
                      class="h-2 rounded-full transition-all"
                      :class="montosValidos ? 'bg-green-500' : 'bg-amber-500'"
                      :style="{ width: `${Math.min((totalMontosCobrados / totalPedidoNum) * 100, 100)}%` }"
                    ></div>
                  </div>
                </div>

                <!-- Restante / cambio -->
                <div class="rounded-lg p-3 mb-4 text-center" :class="montoRestante > 0.05 ? 'bg-red-50 border border-red-200' : 'bg-green-50 border border-green-200'">
                  <div v-if="montoRestante > 0.05">
                    <div class="text-xs text-red-600 font-semibold">Falta por cobrar</div>
                    <div class="text-2xl font-black text-red-700">${{ montoRestante.toFixed(2) }}</div>
                  </div>
                  <div v-else-if="montoRestante < -0.05">
                    <div class="text-xs text-green-700 font-semibold">Cambio a regresar</div>
                    <div class="text-2xl font-black text-green-700">${{ Math.abs(montoRestante).toFixed(2) }}</div>
                  </div>
                  <div v-else>
                    <div class="text-xs text-green-700 font-semibold">Total cubierto</div>
                    <div class="text-2xl font-black text-green-700">✓</div>
                  </div>
                </div>

                <div v-if="splitPrintPaused" class="bg-red-50 border border-red-200 rounded-lg p-3 mb-3">
                  <div class="text-sm font-bold text-red-700">Impresion detenida</div>
                  <div class="text-xs text-red-700 mt-1">{{ splitPrintError }}</div>
                </div>

                <div class="text-xs text-gray-500 mb-3">
                  Se creará un sub-pedido por cada monto. Cada uno se cobra por separado con su propio método de pago.
                </div>

                <button
                  v-if="!splitPrintPaused"
                  @click="dividirCuentaMontosConfirmar"
                  :disabled="splitProcessing || !montosValidos"
                  class="w-full py-3 bg-amber-600 hover:bg-amber-700 disabled:bg-gray-300 text-white font-bold rounded-lg transition-all disabled:cursor-not-allowed"
                >
                  {{ splitProcessing ? 'Procesando...' : '✅ Dividir y generar tickets' }}
                </button>
                <div v-else class="grid grid-cols-2 gap-3">
                  <button @click="reintentarImpresionSplit" :disabled="splitProcessing" class="py-3 bg-green-600 hover:bg-green-700 text-white font-bold rounded-lg">Reintentar</button>
                  <button @click="cancelarImpresionesRestantes" :disabled="splitProcessing" class="py-3 bg-gray-200 hover:bg-gray-300 text-gray-800 font-bold rounded-lg">Cancelar</button>
                </div>
                <button @click="closeSplitModal" :disabled="splitProcessing" class="w-full mt-3 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold rounded-lg">Cerrar</button>

                <div v-if="splitMontos.length < 2 && splitMontos.length > 0" class="text-xs text-gray-500 mt-2">
                  Agrega al menos 2 pagos para poder dividir.
                </div>
              </div>
            </div>
          </template>

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
      class="fixed inset-0 flex items-center justify-center z-[200] p-4 bg-black/60 backdrop-blur-sm"
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

    <GastoRapidoModal
      v-if="showGastoModal"
      :turno-id="turnoActivo?.id"
      @save="handleGastoSaved"
      @cancel="showGastoModal = false"
    />

    <!-- Modal de Confirmación de Cancelación -->
    <div
      v-if="showCancelConfirmModal && pedidoACancelar"
      class="fixed inset-0 flex items-center justify-center z-[170] p-4"
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
