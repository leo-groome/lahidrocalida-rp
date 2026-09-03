<script setup lang="ts">
import { 
  ref, 
  onMounted, 
  onUnmounted, 
  computed, 
  watch, 
  nextTick 
} from 'vue'
import { useRouter } from 'vue-router'
import { formatTime } from '@/utils/dateUtils'
import { useAuthStore } from '../stores/auth'
import { usePedidosStore } from '../stores/pedidos'
import { api } from '../api/client'
import { enviarOEncolar, pendingCount as pedidosSinConfirmar } from '@/services/offlineQueue'
import type { PlatilloResponse, PedidoCreate, ArticuloPedidoCreate } from '../types'
import PozoleVariantModal from '../components/PozoleVariantModal.vue'
import AppHeader from '@/components/AppHeader.vue'
import { 
  Search, 
  ShoppingBag, 
  User, 
  ChevronRight, 
  X, 
  Plus, 
  Minus, 
  Check, 
  Clock, 
  Trash2,
  ChevronDown,
  Info,
  CreditCard,
  ChefHat,
  ArrowLeft,
  Filter,
  MoreVertical,
  LayoutGrid,
  Package,
  Truck,
  ListOrdered,
  XCircle,
  PlusSquare,
  Eye,
  Save,
  CheckCircle,
  WifiOff,
  ArrowRight,
  Edit3,
  Map,
  Receipt,
  Utensils,
  Coffee,
  AlertCircle
} from 'lucide-vue-next'

const router = useRouter()
const auth = useAuthStore()
const pedidosStore = usePedidosStore()

// Búsqueda y filtrado
const searchQuery = ref('')
const activeCategory = ref<string | null>(null)

// Referencias reactivas
  const platillos = ref<PlatilloResponse[]>([])
  const carrito = ref<Array<{ platillo: PlatilloResponse; cantidad: number; modificaciones: string; comboKey?: string; proteina?: string; tamano?: string; tipo_pozole?: string }>>([])
// Clave de idempotencia del carrito actual: se genera en el primer intento de envío
// y se conserva entre reintentos para que un re-tap de "Enviar" no duplique el pedido
const currentRequestId = ref<string | null>(null)

// La clave representa el contenido exacto del carrito: si cambia, clave nueva
// (si no, un reintento con carrito modificado replayería el pedido viejo sin los cambios)
watch(carrito, () => { currentRequestId.value = null }, { deep: true })
const loading = ref(false)
const error = ref<string | null>(null)
const successMessage = ref<string | null>(null)
const showNotification = ref(false)
const nombreCliente = ref('')
const mesa = ref('')
const tipoOrden = ref<'aqui' | 'llevar' | 'uber_eats'>('aqui')
const showPozoleModal = ref(false)
const selectedPozoleColor = ref<'Verde' | 'Blanco' | 'Rojo' | null>(null)

// Control del carrito móvil
const showMobileCart = ref(false)
const isMobile = ref(false)

// Control de categorías colapsables
const categoriasAbiertas = ref<Set<string>>(new Set())

// Control del modal de mesas
const showMesaModal = ref(false)
const showMesaOcupadaModal = ref(false)

// Guard de carga: true cuando los pedidos iniciales ya han cargado
const pedidosInicialmenteListos = ref(false)
// true si el usuario intentó abrir el modal de mesas antes de que cargaran los pedidos
const esperandoCargaMesas = ref(false)

// Control del modal inicial de tipo de orden
const showTipoOrdenModal = ref(true)
const pedidoConfigurado = ref(false)

// Control del modo "agregar artículos"
const modoAgregarArticulos = ref(false)
const pedidoExistenteId = ref<number | null>(null)

// Control del modal "ver pedido actual"
const showVerPedidoModal = ref(false)
const pedidoActual = ref<any>(null)
const articulosEditables = ref<any[]>([])

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

const esBebida = (articulo: any) => {
  return ['Bebidas', 'Aguas', 'Refrescos'].includes(articulo?.platillo?.categoria || '')
}

const marcarBebidaEntregada = async (articuloId: number) => {
  const rol = auth.user?.rol
  if (rol !== 'mesero' && rol !== 'administrador') return

  const ok = await pedidosStore.updateArticuloEstado(articuloId, 'entregado')
  if (ok) {
    showSuccessNotification('Bebida marcada como entregada')
    actualizarModalPedido()
  }
}


// Control del modal "pedidos actuales"
const showPedidosActualesModal = ref(false)
const monitorMobileTab = ref<'mesas' | 'llevar'>('mesas')

// Control del modal de nombre de cliente
const showNombreClienteModal = ref(false)

// Control del modal de especificaciones
const showEspecificacionesModal = ref(false)
const platilloSeleccionado = ref<PlatilloResponse | null>(null)
const especificacionesTemp = ref('')
const proteinaSeleccionada = ref('')
const cantidadTemp = ref(1)

// Constante de estados activos (excluye 'pagado', 'cancelado', 'dividido')
const ESTADOS_ACTIVOS = ['pendiente', 'preparando', 'listo', 'entregado', 'cuenta_solicitada']

// Computed reactivo para mesas ocupadas basado en el store - DATOS EN TIEMPO REAL
const mesasOcupadasReactivo = computed(() => {
  const pedidosActivos = pedidosStore.pedidos.filter((pedido: any) => 
    pedido.tipo_orden === 'aqui' && 
    ESTADOS_ACTIVOS.includes(pedido.estado) &&
    pedido.mesa
  )
  
  return new Set(pedidosActivos.map((pedido: any) => pedido.mesa))
})

let timer: number | undefined

// Detectar si es móvil
const checkIfMobile = () => {
  isMobile.value = window.innerWidth < 1024 // lg breakpoint
}

// Validar que el usuario tenga permisos
onMounted(async () => {
  if (!auth.isAuthenticated || !['mesero', 'administrador'].includes(auth.user?.rol || '')) {
    router.replace({ name: 'login' })
    return
  }

  console.log('👨‍🍳 Mesero View: Iniciando...')
  
  // Detectar tamaño de pantalla
  checkIfMobile()
  window.addEventListener('resize', checkIfMobile)
  
  try {
    // Cargar datos iniciales del store PRIMERO - esto incluye pedidos para mesas
    await pedidosStore.loadInitialData()
    
    // Marcar pedidos como listos ANTES de cargar platillos para que el watcher
    // pueda abrir el modal si alguien lo intentó mientras cargaban
    pedidosInicialmenteListos.value = true
    
    // Luego cargar platillos en paralelo - mesas ya están en el store
    await loadPlatillos()
    
    console.log('✅ Mesero View: Datos iniciales cargados, mesas disponibles desde el store')
    
    // Inicializar WebSocket para mantener todo actualizado
    const wsConnected = await pedidosStore.initWebSocket('mesero')
    
    if (wsConnected) {
      console.log('✅ Mesero View: WebSocket conectado, mesas actualizadas en tiempo real')
    } else {
      console.warn('⚠️ Mesero View: WebSocket falló, datos sin tiempo real')
    }

    // Polling de respaldo permanente: si el WS está caído refresca cada 5s;
    // si está vivo, red de seguridad solo cuando no ha llegado tráfico en 45s
    timer = window.setInterval(() => {
      const staleMs = Date.now() - (pedidosStore.lastUpdate?.getTime() ?? 0)
      if (!pedidosStore.wsConnected || staleMs > 45_000) {
        pedidosStore.refreshPedidos()
      }
    }, 5000)
  } catch (error) {
    console.error('❌ Mesero View: Error en inicialización:', error)
    // Aunque falle, permitir abrir el modal (los pedidos pueden estar parcialmente cargados)
    pedidosInicialmenteListos.value = true
  }
})

// Cuando los pedidos iniciales terminen de cargar y alguien estaba esperando, abrir el modal
watch(pedidosInicialmenteListos, (listos) => {
  if (listos && esperandoCargaMesas.value) {
    esperandoCargaMesas.value = false
    showMesaModal.value = true
    console.log('✅ Pedidos cargados – abriendo modal de mesas (estaba en espera)')
  }
})

// Watcher para actualizar modal cuando cambien los pedidos por WebSocket
watch(() => pedidosStore.pedidos, (newPedidos, oldPedidos) => {
  console.log('🔍 Pedidos store updated in MeseroView:', newPedidos?.length || 0, 'pedidos')
  actualizarModalPedido()
}, { deep: true })

// Watcher adicional específico para cuando el modal esté abierto
watch(() => showVerPedidoModal.value, (isOpen) => {
  if (isOpen) {
    console.log('👁️ Modal "Ver Pedido" abierto - refrescando datos desde el store guardado por WebSocket')
    if (pedidoActual.value) {
      const pedidoFresca = pedidosStore.pedidos.find(p => p.id === pedidoActual.value.id)
      if (pedidoFresca) {
        pedidoActual.value = { ...pedidoActual.value, ...pedidoFresca }
        // Forzar recarga de los artículos de la vista al abrir si el backend dice que hay nuevos
        articulosEditables.value = pedidoFresca.articulos_pedido.map((articulo: any) => ({
          ...articulo,
          cantidad_original: articulo.cantidad,
          modificaciones_original: articulo.modificaciones || '',
          eliminado: false
        }))
      }
    }
  } else {
    console.log('👁️ Modal "Ver Pedido" cerrado')
  }
})

onUnmounted(() => {
  console.log('👋 Mesero View: Cleanup...')
  if (timer) {
    clearInterval(timer)
  }
  window.removeEventListener('resize', checkIfMobile)
  // No desconectamos el WebSocket aquí porque puede ser usado por otras vistas
})

// Control del carrito móvil
const toggleMobileCart = () => {
  showMobileCart.value = !showMobileCart.value
}

const closeMobileCart = () => {
  // Añadir animación de cierre
  const carritoElement = document.querySelector('.carrito-mobile')
  if (carritoElement) {
    carritoElement.classList.add('translate-y-full')
    setTimeout(() => {
      showMobileCart.value = false
    }, 300) // Duración de la animación
  } else {
    showMobileCart.value = false
  }
}

// Cargar platillos disponibles
const loadPlatillos = async () => {
  loading.value = true
  error.value = ''
  try {
    const { data } = await api.get<PlatilloResponse[]>('/platillos')
    platillos.value = data.filter(p => p.estado === 'disponible')
  } catch (e: any) {
    error.value = e?.response?.data?.detail || 'Error al cargar platillos'
  } finally {
    loading.value = false
  }
}


// Categorías únicas de platillos (excluyendo Pozoles) - Ordenadas según la preferencia del usuario
const categorias = computed(() => {
  const cats = [...new Set(platillos.value
    .filter(p => p.categoria !== 'Pozole' && p.estado === 'disponible')
    .map(p => p.categoria))]
  
  const categoryOrder = [
    'enchiladas',
    'sopes',
    'flautas',
    'tacos',
    'tostadas',
    'tamales',
    'extras',
    'postres',
    'bebidas',
    'aguas',
    'refrescos'
  ]

  const sortedCats = cats.sort((a, b) => {
    const indexA = categoryOrder.indexOf(a.toLowerCase())
    const indexB = categoryOrder.indexOf(b.toLowerCase())
    
    if (indexA !== -1 && indexB !== -1) {
      return indexA - indexB
    }
    if (indexA !== -1) return -1
    if (indexB !== -1) return 1
    return a.localeCompare(b)
  })

  return sortedCats
})

// Platillos filtrados por búsqueda y categoría
const filteredPlatillos = computed(() => {
  return platillos.value.filter(p => {
    const matchesSearch = !searchQuery.value || 
      p.nombre.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      (p.kds_name && p.kds_name.toLowerCase().includes(searchQuery.value.toLowerCase()))
    
    const matchesCategory = activeCategory.value && p.categoria === activeCategory.value
    
    return p.estado === 'disponible' && matchesSearch && matchesCategory
  })
})

// Agrupar por categoría para el scroll (opcional para la nueva vista)
const platillosPorCategoria = computed(() => {
  return categorias.value.reduce((acc, cat) => {
    acc[cat] = filteredPlatillos.value.filter(p => p.categoria === cat)
    return acc
  }, {} as Record<string, PlatilloResponse[]>)
})

// Verificar si hay pozoles disponibles
const hasAnyPozole = computed(() => {
  return platillos.value.some(p => p.categoria === 'Pozole' && p.estado === 'disponible')
})

// Pozoles organizados por color
const pozolesByColor = computed(() => {
  const map: Record<'Verde' | 'Blanco' | 'Rojo', PlatilloResponse[]> = {
    'Verde': [],
    'Blanco': [],
    'Rojo': []
  }
  
  for (const p of platillos.value) {
    if (p.categoria !== 'Pozole' || p.estado !== 'disponible') continue
    
    // Extraer el color del nombre (ej: "Pozole de Verde")
    const parts = p.nombre.split(' ')
    const color = parts[2] as 'Verde' | 'Blanco' | 'Rojo' // "Verde", "Blanco", "Rojo"
    if (map[color]) {
      map[color].push(p)
    }
  }
  return map
})

// Proteínas disponibles para pozoles (se pasan al modal)
const proteinasPozole = ['Cerdo', 'Pollo', 'Surtida', 'Mixta']

// Enchilladas 1/2 - proteínas disponibles (MVP)
const enchiladasProteins = ['Puerco', 'Pollo', 'Queso con cebolla', 'Queso y Cebolla']
const selectedEnchiladasProtein = ref<string | null>(null)

// Especificaciones rápidas por categoría - ESPECIFICACIONES REALES
const especificacionesComunes = computed(() => {
  const categoria = platilloSeleccionado.value?.categoria || ''
  
  const especificacionesPorCategoria: Record<string, string[]> = {
    'Pozole': ['Sin lechuga', 'Poco grano', 'Muy caliente'],
    'Enchiladas': ['Sin crema', 'Sin lechuga', 'Sin queso', 'Sin cueritos', 'Sin papa y zanahoria', 'Con jalapeño'],
    'Flautas': ['Sin crema', 'Sin lechuga', 'Sin queso'],
    'Sopes': ['Sin crema', 'Sin lechuga', 'Sin queso', 'Sin frijoles'],
    'Tacos': ['Sin crema', 'Sin lechuga', 'Sin queso'],
    'Tostadas': ['Sin crema', 'Sin lechuga', 'Sin queso', 'Sin frijoles'],
    'Postres': ['Sin chocolate']
  }
  
  return especificacionesPorCategoria[categoria] || []
})

// Total del carrito
const totalCarrito = computed(() => {
  return carrito.value.reduce((sum, item) => sum + (item.platillo.precio * item.cantidad), 0)
})

// Etiqueta del pedido actual
const currentOrderLabel = computed(() => {
  if (!pedidoConfigurado.value) return 'Nuevo Pedido'
  if (tipoOrden.value === 'aqui') return `Mesa ${mesa.value}`
  if (tipoOrden.value === 'llevar') return `📦 ${nombreCliente.value || 'Para Llevar'}`
  if (tipoOrden.value === 'uber_eats') return `🚗 ${nombreCliente.value || 'Uber Eats'}`
  return 'Pedido'
})

const currentOrderItemsCount = computed(() => {
  return carrito.value.reduce((sum, item) => sum + item.cantidad, 0)
})

// Colores por categoría (mismo esquema que POS)
const getCategoryColor = (category: string) => {
  const colors: Record<string, string> = {
    'Pozole': 'bg-red-500 hover:bg-red-600',
    'Pozoles': 'bg-red-500 hover:bg-red-600',
    'Bebidas': 'bg-blue-500 hover:bg-blue-600',
    'Aguas': 'bg-blue-500 hover:bg-blue-600',
    'Refrescos': 'bg-cyan-500 hover:bg-cyan-600',
    'Antojitos': 'bg-green-500 hover:bg-green-600',
    'Postres': 'bg-yellow-500 hover:bg-yellow-600',
    'Extras': 'bg-purple-500 hover:bg-purple-600'
  }
  return colors[category] || 'bg-gray-500 hover:bg-gray-600'
}

// Mapeo de iconos por categoría
const getCategoryIcon = (categoria: string) => {
  const map: Record<string, string> = {
    'Pozole': '🍲',
    'Bebidas': '🥤',
    'Aguas': '🥤',
    'Refrescos': '🥤',
    'Antojitos': '🌮',
    'Postres': '🍰',
    'Extras': '🍽️',
    'Enchiladas': '🥘',
    'Flautas': '🌯',
    'Sopes': '🫓',
    'Tacos': '🌮',
    'Tostadas': '🥪',
    'Especialidades': '✨',
    'Guarniciones': '🥗',
    'Entradas': '🥗'
  }
  return map[categoria] || '🍴'
}



// Abrir modal de variantes de pozole
const abrirPozoleModal = () => {
  showPozoleModal.value = true
}

// Cerrar modal de pozole
const closePozoleModal = () => {
  showPozoleModal.value = false
}

// Seleccionar variante de pozole desde el modal
const selectPozoleVariant = ({ platillo, cantidad, proteina, tamano, tipo_pozole }: { platillo: PlatilloResponse; cantidad: number; proteina: string; tamano: string; tipo_pozole: string }) => {
  const key = `${platillo.id}|${proteina}|${tamano}|${tipo_pozole}`
  const existente = carrito.value.find(item => item.comboKey === key)
  if (existente) {
    existente.cantidad += cantidad
  } else {
    carrito.value.push({
      platillo,
      cantidad,
      modificaciones: '',
      comboKey: key,
      proteina,
      tamano,
      tipo_pozole
    })
  }
  closePozoleModal()
}

// Eliminar del carrito
const eliminarDelCarrito = (index: number) => {
  carrito.value.splice(index, 1)
}

// Ajustar cantidad
const ajustarCantidad = (index: number, cambio: number) => {
  const item = carrito.value[index]
  item.cantidad += cambio
  if (item.cantidad <= 0) {
    eliminarDelCarrito(index)
  }
}

// Lista de números de mesa disponibles
const mesasDisponibles = [
  '11', '12', '13', '14', '15',
  '21', '22', '23', '24', '25', 
  '31', '32', '33', '34', '35'
]

// Validaciones según tipo de orden
const validarFormulario = (): boolean => {
  if (carrito.value.length === 0) {
    error.value = 'Agrega productos al carrito'
    return false
  }

  if (tipoOrden.value === 'aqui' && !mesa.value) {
    error.value = 'Selecciona una mesa'
    return false
  }

  if ((tipoOrden.value === 'llevar' || tipoOrden.value === 'uber_eats') && !nombreCliente.value.trim()) {
    error.value = 'Ingresa el nombre del cliente'
    return false
  }

  return true
}

// Enviar pedido (sin pago - flujo mesero) o agregar artículos a pedido existente
const enviarPedido = async () => {
  if (!validarFormulario()) {
    return
  }

  loading.value = true
  error.value = ''

  try {
    const articulos: ArticuloPedidoCreate[] = carrito.value.map(item => ({
      platillo_id: item.platillo.id,
      cantidad: item.cantidad,
      modificaciones: item.modificaciones || '',
      proteina: (item as any).proteina
    }))

    if (modoAgregarArticulos.value && pedidoExistenteId.value) {
      if (!currentRequestId.value) {
        currentRequestId.value = crypto.randomUUID()
      }

      // Modo agregar artículos - usar endpoint PUT. Sin conexión, se encola y
      // se reintenta solo (mismo client_request_id, el backend es idempotente).
      const resultado = await enviarOEncolar(
        'put',
        `/pedidos/${pedidoExistenteId.value}/agregar-articulos`,
        {
          articulos,
          mesero_id: auth.user?.id,
          client_request_id: currentRequestId.value
        },
        currentRequestId.value
      )

      if (resultado.estado === 'ok') {
        showSuccessNotification(`Artículos agregados a Mesa ${mesa.value}`)
        limpiarModoAgregar()
      } else if (resultado.estado === 'encolado') {
        showSuccessNotification(`Sin conexión: se agregarán a Mesa ${mesa.value} en cuanto vuelva la señal`)
        limpiarModoAgregar()
      } else {
        showErrorNotification(resultado.error?.response?.data?.detail || 'Error al agregar artículos')
      }

  } else {
    // Modo nuevo pedido - usar endpoint POST
      // Reusar la clave si es un reintento del mismo carrito: el backend
      // devuelve el pedido original si el intento anterior sí llegó
      if (!currentRequestId.value) {
        currentRequestId.value = crypto.randomUUID()
      }

      const pedidoData: PedidoCreate = {
        nombre_cliente: (tipoOrden.value === 'llevar' || tipoOrden.value === 'uber_eats') ? nombreCliente.value : null,
        mesa: tipoOrden.value === 'aqui' ? mesa.value : null,
        tipo_orden: tipoOrden.value,
        articulos,
        client_request_id: currentRequestId.value
      }

      const resultado = await pedidosStore.createPedido(pedidoData)

      if (resultado && 'pedido' in resultado) {
        // Limpiar formulario y reiniciar flujo
        limpiarFormulario()

        const mensajeExito = tipoOrden.value === 'aqui'
          ? `Pedido #${resultado.pedido.numero_display} enviado a cocina para Mesa ${mesa.value}`
          : `Pedido #${resultado.pedido.numero_display} ${tipoOrden.value === 'uber_eats' ? 'Uber Eats' : 'para llevar'} enviado a cocina (${nombreCliente.value})`

        showSuccessNotification(mensajeExito)
      } else if (resultado && 'queued' in resultado) {
        limpiarFormulario()
        showSuccessNotification('Sin conexión: el pedido se enviará automáticamente en cuanto vuelva la señal')
      } else {
        showErrorNotification(pedidosStore.error || 'No se pudo enviar. Revisa tu conexión y vuelve a intentar — el pedido no se duplicará.')
      }
    }
    
    // Cerrar carrito móvil si está abierto
    if (isMobile.value && showMobileCart.value) {
      closeMobileCart()
    }
    
  } catch (e: any) {
    showErrorNotification(e?.response?.data?.detail || 'Error al procesar pedido')
  } finally {
    loading.value = false
  }
}

// Cambiar tipo de orden
const setTipoOrden = (tipo: 'aqui' | 'llevar') => {
  tipoOrden.value = tipo
  // Limpiar campos cuando cambie el tipo
  nombreCliente.value = ''
  mesa.value = ''
}

// Funciones del modal inicial de tipo de orden
const configurarTipoOrden = (tipo: 'aqui' | 'llevar' | 'uber_eats') => {
  tipoOrden.value = tipo

  // FIX: Limpiar siempre el estado de sesiones anteriores para evitar mezcla de pedidos.
  // Si modoAgregarArticulos quedó activo de una sesión previa, el envío iría al pedido
  // equivocado (PUT en lugar de POST). Resetear previene ese bug.
  modoAgregarArticulos.value = false
  pedidoExistenteId.value = null
  pedidoActual.value = null
  carrito.value = []
  currentRequestId.value = null

  if (tipo === 'aqui') {
    // Si es "aquí", abrir modal de mesas
    showTipoOrdenModal.value = false
    openMesaModal()
  } else {
    // Si es "llevar" o "uber_eats", pedir nombre de cliente
    showTipoOrdenModal.value = false
    showNombreClienteModal.value = true
  }
}

// Función para mostrar pedidos actuales
const mostrarPedidosActuales = () => {
  showTipoOrdenModal.value = false
  showPedidosActualesModal.value = true
  // Los datos ya están disponibles en pedidosStore.pedidos con tiempo real
}


// Helpers de estado y etiquetas
const getEstadoBadgeColor = (estado: string) => {
  const colors: Record<string, string> = {
    pendiente: 'bg-amber-500',
    preparando: 'bg-orange-500',
    listo: 'bg-emerald-500',
    entregado: 'bg-blue-500',
    cuenta_solicitada: 'bg-purple-600',
    pagado: 'bg-emerald-600',
    cancelado: 'bg-rose-500'
  }
  return colors[estado] || 'bg-slate-400'
}

const getEstadoBadgeClass = (estado: string) => {
  const classes: Record<string, string> = {
    pendiente: 'bg-amber-50 text-amber-700 border-amber-200/80',
    preparando: 'bg-orange-50 text-orange-700 border-orange-200/80',
    listo: 'bg-emerald-50 text-emerald-700 border-emerald-200/80',
    entregado: 'bg-blue-50 text-blue-700 border-blue-200/80',
    cuenta_solicitada: 'bg-purple-50 text-purple-700 border-purple-300 font-black animate-pulse',
    pagado: 'bg-emerald-50 text-emerald-700 border-emerald-200/80',
    cancelado: 'bg-rose-50 text-rose-700 border-rose-200/80'
  }
  return classes[estado] || 'bg-slate-50 text-slate-700 border-slate-200'
}

const getEstadoTexto = (estado: string) => {
  const texts: Record<string, string> = {
    pendiente: 'Pendiente',
    preparando: 'En Cocina',
    listo: 'Listo p/ Servir',
    entregado: 'En Mesa',
    cuenta_solicitada: 'Cuenta Pedida'
  }
  return texts[estado] || estado
}

// Función para ver/modificar pedido desde lista o mapa
const verPedidoDesdeActuales = (pedido: any) => {
  showPedidosActualesModal.value = false
  pedidoActual.value = pedido
  pedidoExistenteId.value = pedido.id
  modoAgregarArticulos.value = true
  
  // Configurar datos para reutilizar el modal existente
  if (pedido.tipo_orden === 'aqui') {
    mesa.value = pedido.mesa
    tipoOrden.value = 'aqui'
  } else {
    nombreCliente.value = pedido.nombre_cliente
    tipoOrden.value = pedido.tipo_orden
  }
  
  // Abrir modal de ver pedido actual
  verPedidoActual()
}

// Cerrar modal de pedidos actuales
const cerrarPedidosActualesModal = () => {
  showPedidosActualesModal.value = false
  showTipoOrdenModal.value = true
}

// Computed para pedidos actuales (tiempo real desde store - excluye divididos, cancelados y pagados)
const pedidosActualesReactivo = computed(() => {
  return pedidosStore.pedidos
    .filter(pedido => ESTADOS_ACTIVOS.includes(pedido.estado))
    .sort((a, b) => new Date(b.fecha_creacion).getTime() - new Date(a.fecha_creacion).getTime())
})

// Computed para separar pedidos por tipo
const pedidosParaAqui = computed(() => {
  return pedidosActualesReactivo.value.filter(pedido => pedido.tipo_orden === 'aqui')
})

const pedidosParaLlevar = computed(() => {
  return pedidosActualesReactivo.value.filter(pedido => pedido.tipo_orden === 'llevar' || pedido.tipo_orden === 'uber_eats')
})

// Obtener el pedido activo más reciente de una mesa
const getMesaPedido = (numeroMesa: string) => {
  const pedidosMesa = pedidosStore.pedidos.filter((p: any) => 
    p.mesa === numeroMesa && 
    p.tipo_orden === 'aqui' && 
    ESTADOS_ACTIVOS.includes(p.estado)
  )
  if (pedidosMesa.length === 0) return null
  return pedidosMesa.sort((a: any, b: any) => 
    new Date(b.fecha_creacion).getTime() - new Date(a.fecha_creacion).getTime()
  )[0]
}

// Obtener el estado actual de la mesa
const getMesaEstado = (numeroMesa: string) => {
  const p = getMesaPedido(numeroMesa)
  return p ? p.estado : 'libre'
}

// Clases de estilo para las tarjetas de mesa en el mapa interactivo
const getMesaCardClass = (numeroMesa: string) => {
  const estado = getMesaEstado(numeroMesa)
  const clases: Record<string, string> = {
    libre: 'bg-slate-50/60 border-slate-200/70 text-slate-400 opacity-50 cursor-not-allowed',
    pendiente: 'bg-amber-50/90 border-amber-300 text-amber-900 shadow-md shadow-amber-500/10 hover:border-amber-400 hover:scale-[1.04] cursor-pointer ring-2 ring-amber-200/60',
    preparando: 'bg-orange-50/90 border-orange-300 text-orange-900 shadow-md shadow-orange-500/10 hover:border-orange-400 hover:scale-[1.04] cursor-pointer ring-2 ring-orange-200/60',
    listo: 'bg-emerald-50/90 border-emerald-300 text-emerald-900 shadow-md shadow-emerald-500/10 hover:border-emerald-400 hover:scale-[1.04] cursor-pointer ring-2 ring-emerald-200/60',
    entregado: 'bg-blue-50/90 border-blue-300 text-blue-900 shadow-md shadow-blue-500/10 hover:border-blue-400 hover:scale-[1.04] cursor-pointer ring-2 ring-blue-200/60',
    cuenta_solicitada: 'bg-purple-50/90 border-purple-400 text-purple-900 shadow-lg shadow-purple-500/20 hover:border-purple-500 hover:scale-[1.04] cursor-pointer ring-2 ring-purple-300 animate-pulse'
  }
  return clases[estado] || clases.libre
}

// Estadísticas de estados para el monitor
const estadisticasMonitor = computed(() => {
  const counts: Record<string, number> = {
    pendiente: 0,
    preparando: 0,
    listo: 0,
    entregado: 0,
    cuenta_solicitada: 0
  }
  pedidosActualesReactivo.value.forEach(p => {
    if (counts[p.estado] !== undefined) {
      counts[p.estado]++
    }
  })
  return counts
})

// Clic en el monitor de mesas
const onMesaClickEnMonitor = (numeroMesa: string) => {
  const pedido = getMesaPedido(numeroMesa)
  if (pedido) {
    verPedidoDesdeActuales(pedido)
  }
}

// Función ya no necesaria - se elimina el botón "Continuar"

// Funciones del modal de nombre de cliente
const confirmarNombreCliente = () => {
  if (nombreCliente.value.trim()) {
    showNombreClienteModal.value = false
    pedidoConfigurado.value = true
  }
}

const cerrarNombreClienteModal = () => {
  showNombreClienteModal.value = false
  // Regresar al modal inicial
  showTipoOrdenModal.value = true
}

// Función para agregar platillo con especificaciones
const abrirEspecificaciones = (platillo: PlatilloResponse) => {
  platilloSeleccionado.value = platillo
  especificacionesTemp.value = ''
  proteinaSeleccionada.value = ''
  cantidadTemp.value = 1
  showEspecificacionesModal.value = true
}

const confirmarEspecificaciones = () => {
  if (platilloSeleccionado.value && cantidadTemp.value > 0) {
    // Si es enchiladas 1/2, requiere proteína seleccionada
    let proteinaParaAgregar: string | undefined = proteinaSeleccionada.value
    if (platilloSeleccionado.value.nombre.toLowerCase().includes('enchiladas') && platilloSeleccionado.value.nombre.includes('1/2')) {
      if (!selectedEnchiladasProtein.value) {
        showErrorNotification('Selecciona una proteína para enchiladas 1/2')
        return
      }
      proteinaParaAgregar = selectedEnchiladasProtein.value
    }

    const existente = carrito.value.find(item => 
      item.platillo.id === platilloSeleccionado.value!.id && 
      item.modificaciones === especificacionesTemp.value &&
      item.proteina === proteinaParaAgregar
    )
    
    if (existente) {
      existente.cantidad += cantidadTemp.value
    } else {
      carrito.value.push({
        platillo: platilloSeleccionado.value,
        cantidad: cantidadTemp.value,
        modificaciones: especificacionesTemp.value,
        proteina: proteinaParaAgregar
      })
    }
    
    // Cerrar todas las categorías después de agregar artículo
    categoriasAbiertas.value.clear()
  }
  cerrarEspecificaciones()
}

const cerrarEspecificaciones = () => {
  showEspecificacionesModal.value = false
  platilloSeleccionado.value = null
  especificacionesTemp.value = ''
  proteinaSeleccionada.value = ''
  cantidadTemp.value = 1
}

// Función para agregar especificación rápida
const agregarEspecificacion = (especificacion: string) => {
  if (especificacionesTemp.value) {
    // Si ya hay texto, agregar con coma
    especificacionesTemp.value += ', ' + especificacion
  } else {
    // Si está vacío, agregar directamente
    especificacionesTemp.value = especificacion
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

// Limpiar carrito y reiniciar flujo
const limpiarCarrito = () => {
  carrito.value = []
  nombreCliente.value = ''
  mesa.value = ''
  pedidoConfigurado.value = false
  showTipoOrdenModal.value = true
  showNombreClienteModal.value = false
}

// Limpiar formulario completo (nuevo pedido)
const limpiarFormulario = () => {
  carrito.value = []
  currentRequestId.value = null
  nombreCliente.value = ''
  mesa.value = ''
  pedidoConfigurado.value = false
  showTipoOrdenModal.value = true
  showNombreClienteModal.value = false
  modoAgregarArticulos.value = false
  pedidoExistenteId.value = null
}

// Limpiar modo agregar artículos (mantiene mesa)
const limpiarModoAgregar = () => {
  carrito.value = []
  currentRequestId.value = null
  pedidoConfigurado.value = false
  showTipoOrdenModal.value = true
  modoAgregarArticulos.value = false
  pedidoExistenteId.value = null
  mesa.value = ''
}

// Cancelar pedido desde desktop (no cierra modal)
const cancelarPedidoDesktop = () => {
  limpiarCarrito()
}

// Cancelar pedido desde móvil (cierra modal)
const cancelarPedidoMovil = () => {
  limpiarCarrito()
  showMobileCart.value = false
}

// Funciones de colapso de categorías
const toggleCategoria = (categoria: string) => {
  const nuevasAbiertas = new Set(categoriasAbiertas.value)
  if (nuevasAbiertas.has(categoria)) {
    nuevasAbiertas.delete(categoria)
  } else {
    nuevasAbiertas.add(categoria)
  }
  categoriasAbiertas.value = nuevasAbiertas
}

const isCategoriaAbierta = (categoria: string) => {
  return categoriasAbiertas.value.has(categoria)
}

// Funciones para verificar estado del carrito
const platilloEnCarrito = (platilloId: number): boolean => {
  return carrito.value.some(item => item.platillo.id === platilloId)
}

const getCantidadEnCarrito = (platilloId: number): number => {
  return carrito.value
    .filter(item => item.platillo.id === platilloId)
    .reduce((total, item) => total + item.cantidad, 0)
}

// Funciones del modal de mesas
const openMesaModal = () => {
  // FIX: Si los pedidos todavía no han cargado, encolar la apertura del modal.
  // Esto evita que el usuario vea todas las mesas como "libres" cuando en realidad
  // los pedidos activos aún no llegaron desde el backend.
  if (!pedidosInicialmenteListos.value) {
    console.log('⏳ Pedidos aún cargando, esperando antes de abrir modal de mesas...')
    esperandoCargaMesas.value = true
    return
  }
  showMesaModal.value = true
}

const closeMesaModal = () => {
  showMesaModal.value = false
  // Regresar al modal inicial de tipo de orden
  pedidoConfigurado.value = false
  showTipoOrdenModal.value = true
}

const seleccionarMesa = (numeroMesa: string) => {
  // Verificar si la mesa está ocupada usando el computed reactivo
  if (mesasOcupadasReactivo.value.has(numeroMesa)) {
    // Mesa ocupada - redirigir a Pedidos Actuales
    showMesaModal.value = false
    showErrorNotification('Mesa ocupada. Ve a "Pedidos Actuales" para modificar el pedido existente.')
    showTipoOrdenModal.value = true
    return
  }
  
  // Mesa libre - continuar normal
  mesa.value = numeroMesa
  pedidoConfigurado.value = true
  showMesaModal.value = false
}

// Layout de mesas organizado por pisos y posición
const mesasLayout = [
  ['11', '21', '31'],
  ['12', '22', '32'],
  ['13', '23', '33'],
  ['14', '24', '34'],
  ['15', '25', '35']
]

// Funciones del modal de mesa ocupada
const cerrarMesaOcupadaModal = () => {
  showMesaOcupadaModal.value = false
  mesa.value = ''
  // Regresar al modal de selección de mesas
  showMesaModal.value = true
}

const agregarArticulosMesa = () => {
  // Buscar el pedido existente de esta mesa
  const pedidoExistente = pedidosStore.pedidos.find(pedido => 
    pedido.mesa === mesa.value && 
    pedido.tipo_orden === 'aqui' &&
    ['pendiente', 'preparando', 'listo', 'entregado', 'cuenta_solicitada'].includes(pedido.estado)
  )
  
  if (pedidoExistente) {
    // Configurar modo agregar artículos
    modoAgregarArticulos.value = true
    pedidoExistenteId.value = pedidoExistente.id
    tipoOrden.value = 'aqui'
    
    // Cerrar modal y continuar al flujo de menú
    showMesaOcupadaModal.value = false
    pedidoConfigurado.value = true
    
    console.log(`✅ Modo agregar artículos activado para pedido #${pedidoExistente.numero_display} (ID: ${pedidoExistente.id})`)
  } else {
    showErrorNotification('No se encontró pedido activo para esta mesa')
    cerrarMesaOcupadaModal()
  }
}

const verPedidoActual = async () => {
  // Si ya hay un pedidoActual.value (desde Pedidos Actuales), usar ese
  let pedidoExistente = pedidoActual.value
  
  // Si no hay pedidoActual, buscar por mesa (flujo original)
  if (!pedidoExistente) {
    pedidoExistente = pedidosStore.pedidos.find(pedido => 
      pedido.mesa === mesa.value && 
      pedido.tipo_orden === 'aqui' &&
      ['pendiente', 'preparando', 'listo', 'entregado', 'cuenta_solicitada'].includes(pedido.estado)
    )
  }
  
  if (pedidoExistente) {
    pedidoActual.value = pedidoExistente
    // Crear copia editable de los artículos para no modificar el store directamente
    articulosEditables.value = pedidoExistente.articulos_pedido.map((articulo: any) => ({
      ...articulo,
      cantidad_original: articulo.cantidad, // Para detectar cambios de cantidad
      modificaciones_original: articulo.modificaciones || '', // Para detectar cambios de modificaciones
      eliminado: false // Flag para tracking de eliminación
    }))
    
    showMesaOcupadaModal.value = false
    showVerPedidoModal.value = true
    
    console.log(`✅ Ver pedido actual #${pedidoExistente.numero_display} - Estado: ${pedidoExistente.estado}`)
    console.log(`📊 Artículos cargados:`, articulosEditables.value.length)
  } else {
    showErrorNotification('No se encontró pedido activo para esta mesa')
    cerrarMesaOcupadaModal()
  }
}

// Solicitar cuenta para pedido entregado (NUEVA FUNCIONALIDAD EN MESERO)
const solicitarCuenta = async (pedido: any) => {
  try {
    // Cambiar estado a cuenta_solicitada
    const success = await pedidosStore.updatePedidoEstado(pedido.id, 'cuenta_solicitada')
    
    if (success) {
      const tipoTexto = pedido.mesa ? `Mesa ${pedido.mesa}` : pedido.nombre_cliente || 'Cliente'
      showSuccessNotification(`Cuenta solicitada: ${tipoTexto} - $${Number(pedido.total).toFixed(2)}`)
      
      // Cerrar modal si está abierto
      if (showVerPedidoModal.value) {
        showVerPedidoModal.value = false
      }
      
      // REINICIAR FLUJO COMPLETO AL MODAL INICIAL
      limpiarFormulario()
      
      // Actualizar datos del modal si es necesario
      actualizarModalPedido()
    } else {
      showErrorNotification(pedidosStore.error || 'Error al solicitar cuenta')
    }
  } catch (e: any) {
    showErrorNotification('Error inesperado al solicitar cuenta')
  }
}

// Función para actualizar el modal cuando cambien los datos por WebSocket
const actualizarModalPedido = () => {
  // Si no hay pedido actual, no hay nada que actualizar
  if (!pedidoActual.value) return
  
  // Buscar versión actualizada del pedido en el store
  const pedidoActualizado = pedidosStore.pedidos.find(p => p.id === pedidoActual.value.id)
  
  if (pedidoActualizado) {
    console.log('🔄 WebSocket update detected for pedido:', pedidoActualizado.id, 'modal open:', showVerPedidoModal.value)
    
    // Actualizar siempre la información básica del pedido (estado, total, etc.)
    pedidoActual.value = {
      ...pedidoActual.value,
      estado: pedidoActualizado.estado,
      total: pedidoActualizado.total,
      numero_display: pedidoActualizado.numero_display,
      articulos_pedido: pedidoActualizado.articulos_pedido
    }
    
    // Solo actualizar artículos editables si no hay cambios locales pendientes Y el modal está abierto
    if (showVerPedidoModal.value) {
      if (!hayCantidadesCambiadas.value) {
        // Si no hay cambios locales, es seguro sobrescribir todo
        articulosEditables.value = pedidoActualizado.articulos_pedido.map((articulo: any) => ({
          ...articulo,
          cantidad_original: articulo.cantidad,
          modificaciones_original: articulo.modificaciones || '',
          eliminado: false
        }))
        console.log('📱 Modal artículos actualizados por WebSocket (sin cambios locales)')
      } else {
        // Hay cambios locales: Fusión inteligente
        // 1. Mantener los artículos que ya estaban y conservar sus cambios locales (cantidades modificadas, eliminaciones)
        // 2. Agregar cualquier artículo NUEVO que venga en la actualización de WebSocket (agregado en otra pantalla)
        
        console.log('⚠️ Modal tiene cambios locales. Aplicando fusión inteligente...')
        const idsArticulosExistentes = new Set(articulosEditables.value.map(a => a.id))
        
        pedidoActualizado.articulos_pedido.forEach((articuloWs: any) => {
          if (!idsArticulosExistentes.has(articuloWs.id)) {
            // Es un artículo totalmente nuevo (agregado por otro cliente/Cajero/KDS/etc)
            articulosEditables.value.push({
              ...articuloWs,
              cantidad_original: articuloWs.cantidad,
              modificaciones_original: articuloWs.modificaciones || '',
              eliminado: false
            })
            console.log(`➕ Artículo nuevo inyectado en modal:`, articuloWs.platillo?.nombre)
          } else {
             // Actualizar solo info que no afecte el trabajo actual (como el estado)
             const articuloLocal = articulosEditables.value.find(a => a.id === articuloWs.id)
             if (articuloLocal) {
               articuloLocal.estado_item = articuloWs.estado_item
             }
          }
        })
      }
    } else {
      console.log('📱 Modal cerrado, info básica actualizada para próxima apertura')
    }
  } else if (pedidoActual.value) {
    // El pedido ya no existe en el store, probablemente fue eliminado/cancelado
    console.log('❌ Pedido no encontrado en store, cerrando modal')
    if (showVerPedidoModal.value) {
      cerrarVerPedidoModal()
    }
  }
}

// Funciones del modal ver pedido
const cerrarVerPedidoModal = () => {
  showVerPedidoModal.value = false
  pedidoActual.value = null
  articulosEditables.value = []
  // Regresar al modal de pedidos actuales
  showPedidosActualesModal.value = true
}

const esPedidoPendiente = computed(() => {
  return pedidoActual.value?.estado === 'pendiente'
})

// Separar artículos de bebidas (servicio mesero) vs comida (cocina)
const articulosBebidas = computed(() => {
  return articulosEditables.value.filter(a => !a.eliminado && esBebida(a))
})

const articulosComida = computed(() => {
  return articulosEditables.value.filter(a => !a.eliminado && !esBebida(a))
})

const hayCantidadesCambiadas = computed(() => {
  if (!pedidoActual.value) return false
  
  // Verificar si se eliminaron artículos (artículos marcados como eliminado)
  const articulosEliminados = articulosEditables.value.some(articulo => articulo.eliminado)
  if (articulosEliminados) {
    return true
  }
  
  // Verificar si hay cambios de cantidad O modificaciones
  return articulosEditables.value.some(articulo => 
    articulo.cantidad !== articulo.cantidad_original ||
    (articulo.modificaciones || '') !== (articulo.modificaciones_original || '')
  )
})

// Computed para el total dinámico basado en artículos editables (excluyendo eliminados)
const totalDinamicoModal = computed(() => {
  if (!articulosEditables.value.length) return 0
  
  return articulosEditables.value.reduce((total, articulo) => {
    if (articulo.cantidad > 0 && articulo.platillo && !articulo.eliminado) {
      return total + (Number(articulo.platillo.precio) * articulo.cantidad)
    }
    return total
  }, 0)
})

// Indicador de si el total mostrado está desactualizado
const totalDesactualizado = computed(() => {
  if (!pedidoActual.value || !esPedidoPendiente.value) return false
  return hayCantidadesCambiadas.value && Math.abs(totalDinamicoModal.value - Number(pedidoActual.value.total)) > 0.01
})

const ajustarCantidadPedido = (index: number, cambio: number) => {
  if (!esPedidoPendiente.value) return
  
  const articulo = articulosEditables.value[index]
  const nuevaCantidad = articulo.cantidad + cambio
  
  if (nuevaCantidad > 0) {
    articulo.cantidad = nuevaCantidad
  }
}

const eliminarArticuloPedido = (index: number) => {
  if (!esPedidoPendiente.value) {
    console.log('❌ No se puede eliminar: pedido no está pendiente')
    return
  }
  
  const articulo = articulosEditables.value[index]
  console.log(`🗑️ Marcando artículo ${index} para eliminación:`, articulo)
  
  // IMPORTANTE: No usar splice() - marcar como eliminado para enviar cantidad = 0 al backend
  articulo.cantidad = 0
  articulo.eliminado = true
  
  console.log('✅ Artículo marcado para eliminación (cantidad = 0)')
}

const irAAgregarMasArticulos = () => {
  // Cerrar modal actual y activar modo agregar
  showVerPedidoModal.value = false
  modoAgregarArticulos.value = true
  pedidoExistenteId.value = pedidoActual.value.id
  pedidoConfigurado.value = true
}

// Borrar un artículo solo se permite con el pedido en estado 'pendiente'
// (gateado por esPedidoPendiente arriba) — sin PIN: es la tablet del propio
// mesero, no la caja compartida. El PIN de administrador para borrar
// artículos vive en CajaView (editar mesa desde caja), no aquí.
const guardarCambiosPedido = async () => {
  if (!esPedidoPendiente.value || !pedidoActual.value) return

  loading.value = true
  error.value = ''

  try {
    // Mapear TODOS los artículos editables - INCLUIR eliminados con cantidad 0
    const articulosActualizados = articulosEditables.value
      .map(articulo => ({
        id: articulo.id,
        cantidad: articulo.cantidad, // Puede ser 0 para eliminar
        modificaciones: articulo.modificaciones?.trim() || '' // Limpiar espacios
      }))

    console.log('📡 Enviando artículos al backend:', articulosActualizados)

    // Llamar al endpoint para actualizar el pedido
    const response = await api.put(`/pedidos/${pedidoActual.value.id}/actualizar-articulos`, {
      articulos: articulosActualizados
    })

    if (response.status === 200) {
      showSuccessNotification(`Pedido #${pedidoActual.value.numero_display} actualizado`)
      
      // Actualizar los valores originales para reflejar el nuevo estado guardado
      // Y ELIMINAR artículos marcados como eliminados del array
      articulosEditables.value = articulosEditables.value.filter(articulo => {
        if (articulo.eliminado) {
          console.log(`🗑️ Artículo eliminado permanentemente del modal:`, articulo)
          return false // Quitar del array
        }
        // Actualizar valores originales para artículos que quedan
        articulo.cantidad_original = articulo.cantidad
        articulo.modificaciones_original = articulo.modificaciones || ''
        return true // Mantener en el array
      })
      
      console.log('✅ Pedido actualizado exitosamente, valores originales actualizados, artículos eliminados removidos')
      
      // NO cerrar el modal automáticamente, permitir que el usuario vea el resultado
      // y decida si quiere hacer más cambios o cerrar manualmente
    } else {
      showErrorNotification('Error al guardar cambios')
    }
    
  } catch (e: any) {
    showErrorNotification(e?.response?.data?.detail || 'Error al guardar cambios del pedido')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex flex-col bg-slate-50/50 selection:bg-blue-100 italic-shadows">
    <!-- Header -->
    <AppHeader title="Mesero" />

    <!-- Cola offline: pedidos/artículos guardados localmente esperando reconexión -->
    <div v-if="pedidosSinConfirmar > 0"
         class="fixed top-20 right-4 z-40 bg-amber-500 text-white px-4 py-2.5 rounded-2xl shadow-2xl flex items-center gap-2.5 border border-amber-300 animate-pulse">
      <WifiOff class="w-5 h-5 flex-shrink-0" />
      <span class="text-xs font-black uppercase tracking-wide">
        {{ pedidosSinConfirmar }} sin confirmar — reintentando…
      </span>
    </div>

    <main class="flex-1 p-4 lg:p-8 max-w-[1600px] mx-auto w-full relative">
      <!-- Background Decorative Elements -->
      <div class="fixed top-20 right-0 w-96 h-96 bg-blue-100/30 blur-[120px] rounded-full -z-10 pointer-events-none"></div>
      <div class="fixed bottom-0 left-0 w-80 h-80 bg-yellow-100/20 blur-[100px] rounded-full -z-10 pointer-events-none"></div>

      <!-- Layout responsive: móvil = solo menú, desktop = grid -->
      <div class="lg:grid lg:grid-cols-12 lg:gap-8 items-start">
        
        <!-- Menu Section -->
        <section class="lg:col-span-8 xl:col-span-9 space-y-8">
          <!-- Solo mostrar el menú después de configurar el pedido -->
          <div v-if="!pedidoConfigurado" class="flex flex-col items-center justify-center min-h-[60vh] text-center p-12 bg-white/40 backdrop-blur-md rounded-[2.5rem] border border-white/60 shadow-sm">
            <div class="w-24 h-24 bg-blue-50 rounded-3xl flex items-center justify-center mb-6 shadow-inner ring-1 ring-blue-100/50">
              <ChefHat class="w-12 h-12 text-blue-600 opacity-80" />
            </div>
            <h2 class="text-3xl font-black text-slate-800 mb-3 tracking-tight">Creación de Pedido</h2>
            <p class="text-slate-500 max-w-sm mx-auto font-medium leading-relaxed italic">Inicia una nueva experiencia gastronómica configurando el tipo de orden.</p>
          </div>

          <div v-else-if="loading" class="flex flex-col items-center justify-center min-h-[40vh] gap-4">
            <div class="w-12 h-12 border-4 border-blue-600/20 border-t-blue-600 rounded-full animate-spin"></div>
            <p class="text-slate-400 font-black text-[10px] uppercase tracking-widest">Preparando Menú...</p>
          </div>

          <div v-else-if="pedidoConfigurado" class="animate-in fade-in slide-in-from-bottom-4 duration-700">
            <!-- Order Context Bar (Mobile only, Desktop has Sidebar) -->
            <div v-if="isMobile" class="flex items-center justify-between mb-6 px-2">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-200">
                  <User v-if="tipoOrden === 'aqui'" class="w-5 h-5 text-white" />
                  <Truck v-else class="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 class="font-black text-slate-800 leading-none mb-1">{{ currentOrderLabel }}</h3>
                  <p class="text-[9px] font-bold text-blue-500 uppercase tracking-widest">{{ tipoOrden.replace('_', ' ') }}</p>
                </div>
              </div>
              <button @click="showTipoOrdenModal = true" class="p-2 rounded-xl bg-slate-100 text-slate-400 hover:bg-slate-200 transition-colors">
                <Edit3 class="w-5 h-5" />
              </button>
            </div>

            <!-- Pozoles Section (Premium Hero Card) -->
            <div class="mb-10 px-1" v-if="hasAnyPozole">
              <div class="relative overflow-hidden group">
                <button
                  @click="abrirPozoleModal"
                  class="w-full relative z-10 bg-slate-900 border border-slate-800 rounded-[2rem] p-8 text-left transition-all duration-500 hover:scale-[1.01] hover:shadow-2xl hover:shadow-blue-900/20 active:scale-95 group overflow-hidden"
                >
                  <!-- Decorative circle backdrop -->
                  <div class="absolute -right-20 -top-20 w-80 h-80 bg-blue-600/20 blur-[80px] group-hover:bg-blue-500/30 transition-colors duration-700 rounded-full"></div>
                  
                  <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-6">
                    <div class="flex items-center gap-6">
                      <div class="w-16 h-16 bg-white/10 backdrop-blur-xl rounded-2xl flex items-center justify-center border border-white/10 group-hover:rotate-6 transition-transform duration-500 transform-gpu">
                        <span class="text-3xl">🍲</span>
                      </div>
                      <div>
                        <h2 class="text-2xl font-black text-white tracking-tight mb-1">Pozoles</h2>
                        <p class="text-blue-200/60 font-medium text-sm">Personaliza cada ingrediente al gusto</p>
                      </div>
                    </div>
                    
                    <div class="flex items-center gap-4">
                      <div class="flex -space-x-2">
                        <div v-for="c in ['Verde', 'Blanco', 'Rojo']" :key="c" :class="`w-8 h-8 rounded-full border-2 border-slate-900 ${c === 'Verde' ? 'bg-emerald-500' : c === 'Blanco' ? 'bg-slate-100' : 'bg-red-500'}`"></div>
                      </div>
                      <div class="bg-blue-600 text-white p-3 rounded-full flex items-center justify-center group-hover:translate-x-2 transition-transform duration-500">
                        <ArrowRight class="w-5 h-5" />
                      </div>
                    </div>
                  </div>
                </button>
              </div>
            </div>

            <!-- Filters & Navigation -->
            <div class="mb-10 px-1">
              <!-- Botón de Volver cuando hay una categoría seleccionada -->
              <div v-if="activeCategory" class="animate-in fade-in slide-in-from-top-3 duration-200">
                <button 
                  @click="activeCategory = null" 
                  class="group flex items-center gap-2 px-5 py-3 rounded-2xl border border-slate-200/60 bg-white text-slate-500 hover:text-blue-600 hover:border-blue-200 shadow-sm transition-all hover:scale-[1.02] active:scale-[0.98] font-bold text-xs uppercase tracking-wider"
                >
                  <ArrowLeft class="w-4 h-4 text-slate-400 group-hover:text-blue-600 transition-colors" />
                  <span>Volver a Categorías</span>
                </button>
              </div>

              <!-- Grid completo de categorías cuando no hay selección -->
              <div v-else class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3 animate-in fade-in zoom-in-95 duration-200">
                <button 
                  v-for="cat in categorias" 
                  :key="cat"
                  @click="activeCategory = cat"
                  :class="[
                    'flex items-center gap-3 p-4 rounded-2xl border text-left transition-all duration-300 transform-gpu hover:scale-[1.02] active:scale-[0.98]',
                    activeCategory === cat 
                      ? 'bg-gradient-to-r from-blue-600 to-blue-500 border-blue-600 text-white shadow-lg shadow-blue-500/20' 
                      : 'bg-slate-50/70 border-slate-200/50 text-slate-700 hover:bg-slate-100 hover:border-slate-300 shadow-sm'
                  ]"
                >
                  <div 
                    :class="[
                      'w-10 h-10 rounded-xl flex items-center justify-center text-xl shadow-sm transition-colors duration-300 flex-shrink-0',
                      activeCategory === cat ? 'bg-blue-700/40 text-white' : 'bg-white text-slate-800'
                    ]"
                  >
                    {{ getCategoryIcon(cat) }}
                  </div>
                  <span class="font-bold text-sm tracking-wide uppercase truncate leading-none">
                    {{ cat }}
                  </span>
                </button>
              </div>
            </div>

            <!-- Menú por categorías -->
            <div class="space-y-12">
              <template v-if="activeCategory">
                <div v-for="categoria in [activeCategory]" :key="categoria">
                  <div class="flex items-center gap-4 mb-6 px-2">
                    <div class="w-10 h-10 bg-slate-100 rounded-xl flex items-center justify-center">
                      <span class="text-xl opacity-80">{{ getCategoryIcon(categoria) }}</span>
                    </div>
                    <h3 class="text-xl font-black text-slate-800 tracking-tight">{{ categoria }}</h3>
                    <div class="h-px flex-1 bg-gradient-to-r from-slate-200/60 to-transparent"></div>
                    <span class="text-[10px] font-black text-slate-300 uppercase tracking-widest">{{ platillosPorCategoria[categoria]?.length || 0 }} items</span>
                  </div>

                <div class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4 sm:gap-6">
                  <button
                    v-for="platillo in platillosPorCategoria[categoria]"
                    :key="platillo.id"
                    @click="abrirEspecificaciones(platillo)"
                    :class="[
                      'group relative flex flex-col bg-white rounded-3xl p-5 text-left transition-all duration-300 border hover:scale-[1.02] transform-gpu',
                      platilloEnCarrito(platillo.id) 
                        ? 'border-blue-600/40 bg-blue-50/20 shadow-xl shadow-blue-600/5 ring-1 ring-blue-600/10' 
                        : 'border-slate-100 shadow-sm hover:shadow-xl hover:shadow-slate-200/60 hover:border-blue-200'
                    ]"
                  >
                    <!-- Quantity Badge -->
                    <div 
                      v-if="platilloEnCarrito(platillo.id)"
                      class="absolute -top-3 -right-3 bg-blue-600 text-white text-[10px] font-black w-8 h-8 rounded-xl flex items-center justify-center shadow-lg shadow-blue-200 ring-2 ring-white animate-in zoom-in-50 duration-300"
                    >
                      {{ getCantidadEnCarrito(platillo.id) }}
                    </div>
                    
                    <div class="flex-1 space-y-4">
                      <div class="flex justify-between items-start">
                        <div class="w-12 h-12 bg-slate-50 rounded-2xl flex items-center justify-center group-hover:bg-blue-50 group-hover:scale-110 transition-all duration-500">
                          <span class="text-2xl group-hover:rotate-12 transition-transform duration-500">{{ getCategoryIcon(platillo.categoria) }}</span>
                        </div>
                        <div class="text-sm font-black text-blue-600">$ {{ Number(platillo.precio).toFixed(0) }}<span class="text-[10px] opacity-60">.00</span></div>
                      </div>
                      
                      <div>
                        <h4 class="font-black text-slate-800 text-sm leading-tight mb-1 group-hover:text-blue-600 transition-colors uppercase tracking-tight">{{ platillo.kds_name || platillo.nombre }}</h4>
                        <!-- Porción context -->
                        <div v-if="platillo.defaultPortion === 2 || platillo.defaultPortion === 4" class="text-[9px] font-bold text-slate-400 uppercase tracking-widest bg-slate-50 px-2 py-0.5 rounded-full inline-block">
                          Orden de {{ platillo.defaultPortion }}
                        </div>
                      </div>
                    </div>

                    <div class="mt-4 pt-4 border-t border-slate-50 flex items-center justify-between">
                      <span class="text-[10px] font-black text-slate-300 uppercase tracking-widest group-hover:text-blue-400">Personalizar</span>
                      <Plus class="w-4 h-4 text-slate-300 group-hover:text-blue-600 transition-colors" />
                    </div>
                  </button>
                </div>
              </div>
            </template>
            <template v-else>
              <div class="flex flex-col items-center justify-center py-20 px-4 text-center bg-slate-50/50 rounded-[2rem] border border-dashed border-slate-200/80 animate-in fade-in duration-500">
                <div class="w-16 h-16 bg-blue-50 text-blue-600 rounded-2xl flex items-center justify-center mb-4 shadow-sm">
                  <span class="text-2xl">🍽️</span>
                </div>
                <h4 class="text-base font-black text-slate-700 mb-1">Selecciona una Categoría</h4>
                <p class="text-xs text-slate-400 max-w-xs leading-relaxed">Presiona cualquiera de los botones de arriba para ver los platillos disponibles.</p>
              </div>
            </template>
          </div>
          </div>
        </section>

        <!-- Dynamic Cart Sidebar - Desktop -->
        <aside class="hidden lg:block lg:col-span-4 xl:col-span-3 sticky top-24 max-h-[calc(100vh-8rem)]">
          <div class="bg-white rounded-[2.5rem] border border-slate-200/60 shadow-2xl flex flex-col overflow-hidden h-full">
            <!-- Sidebar Header -->
            <div class="p-8 border-b border-slate-50">
              <div class="flex items-center justify-between mb-4">
                <div class="flex items-center gap-3">
                  <div class="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-200">
                    <ShoppingBag class="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h2 class="font-black text-slate-800 tracking-tight leading-none mb-1">Pedido Actual</h2>
                    <p class="text-[9px] font-bold text-blue-500 uppercase tracking-widest">{{ currentOrderLabel }}</p>
                  </div>
                </div>
                <div v-if="carrito.length > 0" class="w-6 h-6 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center text-[10px] font-black">
                  {{ currentOrderItemsCount }}
                </div>
              </div>
            </div>

            <!-- Sidebar Items -->
            <div class="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin">
              <div v-if="carrito.length === 0" class="flex flex-col items-center justify-center h-full text-center p-8 opacity-40 italic">
                <Package class="w-12 h-12 mb-3 text-slate-300" />
                <p class="text-sm font-medium text-slate-400">El lienzo está en blanco.<br>Comienza a agregar platillos.</p>
              </div>

              <div v-for="(item, index) in carrito" :key="index" class="group bg-slate-50 hover:bg-blue-50/50 rounded-2xl p-4 border border-transparent hover:border-blue-100 transition-all duration-300">
                <div class="flex items-start justify-between gap-3 mb-3">
                  <div class="flex-1 min-w-0">
                    <h5 class="font-black text-slate-800 text-[13px] leading-tight truncate uppercase tracking-tight">{{ item.platillo.kds_name || item.platillo.nombre }}</h5>
                    <div v-if="item.proteina || item.tamano" class="text-[9px] font-bold text-blue-500 uppercase tracking-widest mt-1">
                      {{ item.proteina }} • {{ item.tamano }}
                    </div>
                  </div>
                  <div class="text-sm font-black text-slate-400">$ {{ (Number(item.platillo.precio) * item.cantidad).toFixed(0) }}</div>
                </div>

                <div class="flex items-center justify-between gap-4">
                  <!-- Counter Component (Refined) -->
                  <div class="flex items-center gap-1 bg-white p-1 rounded-xl shadow-sm border border-slate-100">
                    <button @click="ajustarCantidad(index, -1)" class="w-7 h-7 rounded-lg flex items-center justify-center text-slate-400 hover:bg-slate-100 hover:text-red-500 transition-colors">
                      <Minus class="w-3 h-3" />
                    </button>
                    <span class="w-6 text-center text-xs font-black text-slate-700">{{ item.cantidad }}</span>
                    <button @click="ajustarCantidad(index, 1)" class="w-7 h-7 rounded-lg flex items-center justify-center text-slate-400 hover:bg-slate-100 hover:text-blue-600 transition-colors">
                      <Plus class="w-3 h-3" />
                    </button>
                  </div>
                  
                  <button @click="eliminarDelCarrito(index)" class="p-2 rounded-xl text-slate-300 hover:text-red-500 hover:bg-red-50 transition-all opacity-0 group-hover:opacity-100">
                    <Trash2 class="w-4 h-4" />
                  </button>
                </div>
                
                <div class="mt-3 relative group/note">
                  <Edit3 class="absolute left-2.5 top-2.5 w-3 h-3 text-slate-300 group-focus-within/note:text-blue-500 transition-colors" />
                  <input 
                    v-model="item.modificaciones" 
                    placeholder="Notas especiales..." 
                    class="w-full pl-8 pr-3 py-2 bg-white/50 border border-slate-100 rounded-xl text-[10px] font-bold text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-100 focus:bg-white transition-all placeholder:text-slate-300 italic"
                  />
                </div>
              </div>
            </div>

            <!-- Sidebar Footer -->
            <div class="p-8 bg-slate-900 text-white mt-auto">
              <!-- Total -->
              <div class="flex items-center justify-between mb-8">
                <span class="text-[10px] font-black uppercase tracking-[0.3em] text-blue-400">Total Inversión</span>
                <div class="text-3xl font-black tracking-tighter">
                  <span class="text-blue-400 text-sm font-black mr-1">$</span>{{ totalCarrito.toFixed(0) }}<span class="text-sm opacity-40">.{{ totalCarrito.toFixed(2).split('.')[1] }}</span>
                </div>
              </div>

              <!-- Actions -->
              <div class="space-y-4">
                <button 
                  @click="enviarPedido" 
                  :disabled="loading || carrito.length === 0" 
                  class="w-full py-5 rounded-2xl bg-blue-600 hover:bg-blue-500 disabled:opacity-30 disabled:grayscale transition-all duration-500 shadow-xl shadow-blue-900/40 relative group overflow-hidden"
                >
                  <div class="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-1000"></div>
                  <div class="flex items-center justify-center gap-3">
                    <span v-if="loading" class="w-5 h-5 border-2 border-white/20 border-t-white rounded-full animate-spin"></span>
                    <ChefHat v-else class="w-5 h-5" />
                    <span class="font-black text-xs uppercase tracking-widest">{{ modoAgregarArticulos ? `Fusionar con Mesa ${mesa}` : 'Enviar a Cocina' }}</span>
                  </div>
                </button>

                <button @click="cancelarPedidoDesktop" class="w-full py-2 text-[10px] font-black uppercase tracking-widest text-slate-400 hover:text-red-400 transition-colors flex items-center justify-center gap-2">
                   <span>Limpiar Mesa</span>
                </button>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </main>

    <!-- Botón flotante móvil (Premium Fab) -->
    <div v-if="isMobile" class="fixed bottom-6 right-6 z-[110]">
      <button
        @click="toggleMobileCart"
        class="relative w-24 h-24 bg-slate-900 text-white rounded-[2.5rem] shadow-2xl shadow-slate-950/40 flex items-center justify-center active:scale-95 transition-all duration-300 group"
      >
        <!-- Inner Glow Container (to keep glow contained if needed, or let it bleed for atmosphere) -->
        <div v-if="carrito.length > 0" class="absolute inset-0 bg-blue-600/20 blur-2xl animate-pulse rounded-[2.5rem]"></div>
        
        <div class="relative flex flex-col items-center gap-1">
          <ShoppingBag class="w-8 h-8 group-hover:scale-110 transition-transform text-white" />
          <div v-if="carrito.length > 0 && mesa" class="flex flex-col items-center">
             <span class="text-[10px] font-black uppercase tracking-[0.2em] text-blue-400">Mesa</span>
             <span class="text-xl font-black text-white leading-none">{{ mesa }}</span>
          </div>
        </div>
        
        <!-- Counter Badge: Now correctly floating outside -->
        <div 
          v-if="carrito.length > 0" 
          class="absolute -top-1 -right-1 w-10 h-10 bg-blue-600 rounded-2xl flex items-center justify-center border-4 border-white shadow-xl animate-in zoom-in-50 duration-500 z-20"
        >
          <span class="text-xs font-black text-white italic">{{ carrito.reduce((acc, item) => acc + item.cantidad, 0) }}</span>
        </div>
      </button>
    </div>

    <!-- Carrito Móvil (Full Screen Drawer) -->
    <div
      v-if="isMobile && showMobileCart"
      class="fixed inset-0 z-[100] flex flex-col"
    >
      <!-- Backdrop -->
      <div @click="closeMobileCart" class="absolute inset-0 bg-slate-900/60 backdrop-blur-sm transition-opacity duration-300"></div>
      
      <!-- Carrito Panel -->
      <div class="carrito-mobile relative mt-auto w-full max-h-[92vh] bg-white rounded-t-[3rem] shadow-2xl flex flex-col overflow-hidden transform transition-transform duration-500 ease-out translate-y-0">
        <!-- Handle for drawer feel -->
        <div class="flex justify-center pt-4 pb-2">
          <div class="w-12 h-1.5 bg-slate-100 rounded-full"></div>
        </div>

        <!-- Header del carrito móvil -->
        <div class="flex items-center justify-between p-8 pt-4">
          <div class="flex items-center gap-4">
            <div class="w-12 h-12 bg-blue-50 rounded-2xl flex items-center justify-center border border-blue-100/50">
              <ShoppingBag class="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <h2 class="text-xl font-black text-slate-800 leading-none mb-1">Mi Carrito</h2>
              <p class="text-[10px] font-bold text-blue-500 uppercase tracking-widest">{{ currentOrderLabel }}</p>
            </div>
          </div>
          <button @click="closeMobileCart" class="w-10 h-10 rounded-full bg-slate-50 flex items-center justify-center text-slate-400">
            <X class="w-5 h-5" />
          </button>
        </div>

        <!-- Contenido del carrito móvil -->
        <div class="flex flex-col flex-1 overflow-hidden font-bold">
          <div class="flex-1 overflow-y-auto px-8 py-2 space-y-4">
            <div v-if="carrito.length === 0" class="flex flex-col items-center justify-center py-20 text-center opacity-40">
              <Package class="w-16 h-16 text-slate-300 mb-4" />
              <p class="text-slate-500 italic">El carrito está vacío</p>
            </div>

            <div v-for="(item, index) in carrito" :key="index" class="bg-slate-50 rounded-3xl p-5 border border-transparent shadow-sm">
                <div class="flex items-center justify-between gap-4 mb-4">
                  <div class="flex-1">
                    <h4 class="font-black text-slate-800 text-sm uppercase tracking-tight">{{ item.platillo.kds_name || item.platillo.nombre }}</h4>
                    <div class="text-[10px] font-black text-blue-500 mt-1">$ {{ Number(item.platillo.precio).toFixed(0) }} c/u</div>
                  </div>
                  
                  <div class="flex items-center gap-2 bg-white p-1 rounded-2xl shadow-inner ring-1 ring-slate-100">
                    <button @click="ajustarCantidad(index, -1)" class="w-9 h-9 rounded-xl flex items-center justify-center text-slate-400 bg-slate-50 active:bg-slate-100 transition-colors">
                      <Minus class="w-4 h-4" />
                    </button>
                    <span class="w-8 text-center text-sm font-black text-slate-800">{{ item.cantidad }}</span>
                    <button @click="ajustarCantidad(index, 1)" class="w-9 h-9 rounded-xl flex items-center justify-center text-white bg-blue-600 active:bg-blue-700 transition-colors shadow-lg shadow-blue-100">
                      <Plus class="w-4 h-4" />
                    </button>
                  </div>
                </div>

                <div class="flex items-center gap-4">
                  <div class="flex-1 relative group">
                    <Edit3 class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-300 pointer-events-none" />
                    <input 
                      v-model="item.modificaciones" 
                      placeholder="Instrucciones especiales..." 
                      class="w-full pl-10 pr-4 py-3 bg-white border border-slate-100 rounded-2xl text-[11px] placeholder:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-100 transition-all font-medium"
                    />
                  </div>
                  <button @click="eliminarDelCarrito(index)" class="w-12 h-12 rounded-2xl bg-red-50 text-red-500 flex items-center justify-center active:scale-95 transition-all">
                    <Trash2 class="w-5 h-5" />
                  </button>
                </div>
            </div>
          </div>
          
          <!-- Bottom Action Area -->
          <div class="p-8 pb-12 bg-white border-t border-slate-100 space-y-6">
            <div class="flex items-center justify-between">
              <span class="text-[11px] font-black text-slate-400 uppercase tracking-[0.2em]">Total del pedido</span>
              <div class="text-3xl font-black text-slate-800 tracking-tighter">
                <span class="text-blue-600 text-sm align-super mr-1">$</span>{{ totalCarrito.toFixed(0) }}<span class="text-sm opacity-40">.{{ totalCarrito.toFixed(2).split('.')[1] }}</span>
              </div>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <button 
                @click="cancelarPedidoMovil" 
                class="py-5 rounded-2xl bg-slate-100 text-slate-500 text-xs font-black uppercase tracking-widest active:bg-red-50 active:text-red-500 transition-all"
              >
                Limpiar
              </button>
              <button 
                @click="enviarPedido" 
                :disabled="loading || carrito.length === 0" 
                class="py-5 rounded-2xl bg-blue-600 text-white shadow-xl shadow-blue-100 active:scale-95 transition-all flex items-center justify-center gap-2"
              >
                <ChefHat v-if="!loading" class="w-5 h-5" />
                <div v-else class="w-5 h-5 border-2 border-white/20 border-t-white rounded-full animate-spin"></div>
                <span class="text-xs font-black uppercase tracking-widest">{{ loading ? 'Enviando...' : 'Pedir Ahora' }}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal Inicial - Full Screen Mobile / Modal Desktop -->
    <div
      v-if="showTipoOrdenModal"
      class="fixed inset-0 z-[150] flex items-center justify-center sm:p-6"
    >
      <!-- Backdrop (Only visible on desktop) -->
      <div class="absolute inset-0 bg-slate-900/80 backdrop-blur-md animate-in fade-in duration-500 hidden sm:block"></div>
      
      <!-- Modal Content: Full screen on mobile, rounded modal on sm+ -->
      <div class="relative bg-white sm:rounded-[3rem] w-full h-full sm:h-auto sm:max-h-[90vh] sm:max-w-xl shadow-2xl overflow-hidden animate-in sm:zoom-in-95 slide-in-from-bottom-10 duration-700 flex flex-col">
        
        <!-- Header: More compact to save space -->
        <div class="px-6 py-4 sm:p-10 text-center border-b border-slate-50 flex-shrink-0 bg-white">
          <h3 class="text-xl sm:text-3xl font-black text-slate-800 tracking-tight leading-none uppercase mb-1">Nueva Comanda</h3>
          <p class="text-[9px] sm:text-xs font-black text-blue-500 uppercase tracking-widest opacity-80">Seleccionar Modalidad</p>
        </div>
        
        <!-- Content Area: Buttons fill 75% of screen -->
        <div class="p-4 sm:p-10 flex-1 flex flex-col gap-4 overflow-y-auto">
          
          <!-- Pedidos Actuales (Approx 20% height) -->
          <button
            @click="mostrarPedidosActuales"
            class="w-full group relative p-6 bg-slate-900 text-white rounded-[2rem] overflow-hidden shadow-xl hover:shadow-blue-900/20 transition-all duration-500 active:scale-95 flex-1 min-h-[120px] flex items-center"
          >
            <div class="absolute -right-6 -bottom-6 w-32 h-32 bg-blue-600 blur-[60px] opacity-40 group-hover:opacity-60 transition-opacity"></div>
            <div class="flex items-center gap-6 relative z-10 text-left w-full">
              <div class="w-14 h-14 sm:w-16 sm:h-16 bg-white/10 backdrop-blur-xl rounded-2xl border border-white/10 flex items-center justify-center group-hover:rotate-6 transition-transform flex-shrink-0">
                <ListOrdered class="w-8 h-8 text-blue-400" />
              </div>
              <div>
                <div class="text-xl sm:text-2xl font-black tracking-tight mb-0.5 leading-none">Ver Mesas Activas</div>
                <div class="text-[9px] font-black text-slate-400 uppercase tracking-widest opacity-80 italic">Comandas en Curso</div>
              </div>
            </div>
          </button>

          <!-- Middle Options Grid (Approx 40% height) -->
          <div class="grid grid-cols-2 gap-4 flex-[2.5] min-h-[280px]">
            <!-- Servicio Mesa -->
            <button
              @click="configurarTipoOrden('aqui')"
              class="group p-8 bg-white border-2 border-slate-100 rounded-[2.5rem] hover:border-blue-600/30 hover:bg-blue-50/50 transition-all duration-300 active:scale-95 text-left relative overflow-hidden flex flex-col justify-between"
            >
              <div class="w-14 h-14 sm:w-16 sm:h-16 bg-blue-50 rounded-2xl flex items-center justify-center group-hover:bg-blue-600 transition-colors">
                <Search class="w-8 h-8 text-blue-600 group-hover:text-white" />
              </div>
              <div>
                <h4 class="text-xl sm:text-2xl font-black text-slate-800 tracking-tight leading-tight uppercase">Comer<br>Aquí</h4>
                <div class="w-10 h-1.5 bg-blue-600 mt-3 rounded-full"></div>
              </div>
            </button>
            
            <!-- Para Llevar -->
            <button
              @click="configurarTipoOrden('llevar')"
              class="group p-8 bg-white border-2 border-slate-100 rounded-[2.5rem] hover:border-blue-600/30 hover:bg-blue-50/50 transition-all duration-300 active:scale-95 text-left relative overflow-hidden flex flex-col justify-between"
            >
              <div class="w-14 h-14 sm:w-16 sm:h-16 bg-blue-50 rounded-2xl flex items-center justify-center group-hover:bg-blue-600 transition-colors">
                <Truck class="w-8 h-8 text-blue-600 group-hover:text-white" />
              </div>
              <div>
                <h4 class="text-xl sm:text-2xl font-black text-slate-800 tracking-tight leading-tight uppercase">Para<br>Llevar</h4>
                <div class="w-10 h-1.5 bg-blue-600 mt-3 rounded-full"></div>
              </div>
            </button>
          </div>
          
          <!-- Food Delivery (Approx 15% height) -->
          <button
            @click="configurarTipoOrden('uber_eats')"
            class="w-full group p-6 bg-slate-50 border-2 border-slate-100 rounded-[2rem] hover:border-blue-600/30 hover:bg-blue-50 transition-all duration-300 active:scale-95 flex items-center justify-between flex-1 min-h-[100px]"
          >
            <div class="flex items-center gap-6 text-left">
              <div class="w-14 h-14 bg-white rounded-2xl flex items-center justify-center border border-slate-100 group-hover:rotate-6 transition-transform shadow-sm flex-shrink-0">
                <CheckCircle class="w-8 h-8 text-emerald-500" />
              </div>
              <div>
                <div class="text-lg sm:text-xl font-black text-slate-800 tracking-tight leading-none mb-1 uppercase">Food Delivery</div>
                <div class="text-[10px] font-black text-slate-400 uppercase tracking-widest opacity-80">Uber Eats / APP</div>
              </div>
            </div>
            <div class="w-10 h-10 bg-white rounded-full flex items-center justify-center border border-slate-100 text-slate-300 group-hover:text-blue-600 group-hover:border-blue-200 transition-all">
              <Plus class="w-5 h-5" />
            </div>
          </button>
        </div>
      </div>
    </div>

    <!-- Modal de Nombre de Cliente (Elevated Design) -->
    <div
      v-if="showNombreClienteModal"
      class="fixed inset-0 z-[120] flex items-center justify-center p-4 lg:p-8"
    >
      <!-- Backdrop -->
      <div class="absolute inset-0 bg-slate-900/80 backdrop-blur-md"></div>
      
      <!-- Modal Content -->
      <div class="relative bg-white rounded-[3rem] p-12 max-w-xl w-full mx-auto shadow-2xl overflow-hidden animate-in zoom-in-95 duration-500">
        <!-- Accent Decoration -->
        <div class="absolute top-0 right-0 w-48 h-48 bg-blue-50 blur-[80px] -z-10 rounded-full"></div>

        <!-- Header -->
        <div class="text-center mb-10">
          <div class="w-20 h-20 bg-blue-50 rounded-3xl flex items-center justify-center mx-auto mb-6 border border-blue-100 shadow-sm">
            <span class="text-4xl text-blue-600">{{ tipoOrden === 'uber_eats' ? '🚗' : '📦' }}</span>
          </div>
          <h3 class="text-3xl font-black text-slate-800 tracking-tight mb-2 uppercase">Identificador</h3>
          <p class="text-slate-400 font-medium text-sm">¿A nombre de quién registramos el pedido?</p>
        </div>
        
        <!-- Campo de nombre (Refined Input) -->
        <div class="mb-10 group">
          <label class="block text-[10px] font-black text-blue-600 mb-3 uppercase tracking-widest px-1">
             Nombre del Cliente
          </label>
          <div class="relative">
            <User class="absolute left-6 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-300 group-focus-within:text-blue-500 transition-colors" />
            <input
              v-model="nombreCliente"
              type="text"
              placeholder="Ej. Juan Pérez"
              class="w-full pl-16 pr-6 py-5 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-4 focus:ring-blue-100 focus:bg-white focus:border-blue-200 transition-all text-xl font-bold text-slate-800 placeholder:text-slate-300"
              @keyup.enter="confirmarNombreCliente"
              autofocus
            />
          </div>
        </div>
        
        <!-- Botones (Premium Palette) -->
        <div class="flex gap-4">
          <button
            @click="cerrarNombreClienteModal"
            class="flex-[0.4] py-5 bg-slate-100 hover:bg-slate-200 text-slate-500 font-black uppercase tracking-widest text-[10px] rounded-2xl transition-all active:scale-95 flex items-center justify-center gap-2"
          >
            Atrás
          </button>
          <button
            @click="confirmarNombreCliente"
            :disabled="!nombreCliente.trim()"
            class="flex-1 py-5 bg-blue-600 hover:bg-blue-500 disabled:opacity-30 disabled:grayscale text-white font-black uppercase tracking-widest text-[10px] rounded-2xl transition-all active:scale-95 shadow-xl shadow-blue-100 flex items-center justify-center gap-2"
          >
            Continuar  <ChevronRight class="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>

    <!-- Modal de Pedidos Actuales (Monitor de Mesas Activas con Minimapa Responsive) -->
    <div
      v-if="showPedidosActualesModal"
      class="fixed inset-0 z-[130] flex items-center justify-center p-0 sm:p-6"
    >
      <!-- Backdrop -->
      <div class="absolute inset-0 bg-slate-900/80 backdrop-blur-md hidden sm:block" @click="cerrarPedidosActualesModal"></div>
      
      <!-- Modal Content (Full Screen en móvil, Centrado en tablet/desktop) -->
      <div class="relative bg-white rounded-none sm:rounded-[3.5rem] w-full max-w-6xl shadow-2xl flex flex-col overflow-hidden h-full sm:h-[88vh] animate-in zoom-in-95 duration-500">
        
        <!-- Header -->
        <div class="px-5 py-4 sm:p-8 border-b border-slate-100 flex items-center justify-between bg-slate-50/70 flex-shrink-0">
          <div class="flex items-center gap-3 sm:gap-6">
            <div class="w-10 h-10 sm:w-16 sm:h-16 bg-blue-600 rounded-xl sm:rounded-[1.5rem] flex items-center justify-center shadow-lg shadow-blue-500/20 flex-shrink-0 text-white">
               <Map class="w-5 h-5 sm:w-8 sm:h-8" />
            </div>
            <div>
              <div class="flex items-center gap-2 sm:gap-3 mb-0.5">
                <h3 class="text-lg sm:text-3xl font-black text-slate-800 tracking-tight uppercase leading-none">Monitor Mesas</h3>
                <div class="flex items-center gap-1.5 px-2.5 py-0.5 bg-emerald-50 rounded-full border border-emerald-100">
                   <div class="w-1.5 h-1.5 sm:w-2 sm:h-2 bg-emerald-500 rounded-full animate-pulse"></div>
                   <span class="text-[8px] sm:text-[9px] font-black text-emerald-600 uppercase tracking-widest">En Vivo</span>
                </div>
              </div>
              <p class="text-[9px] sm:text-xs font-bold text-slate-400 uppercase tracking-widest">
                {{ pedidosParaAqui.length }} en mesa • {{ pedidosParaLlevar.length }} para llevar
              </p>
            </div>
          </div>
          <button 
            @click="cerrarPedidosActualesModal" 
            class="w-10 h-10 sm:w-12 sm:h-12 rounded-xl sm:rounded-2xl bg-white border border-slate-200/80 text-slate-400 hover:text-slate-800 hover:bg-slate-100 transition-all active:scale-90 flex items-center justify-center shadow-sm"
          >
            <X class="w-5 h-5 sm:w-6 sm:h-6" />
          </button>
        </div>

        <!-- Selector de Tabs Móvil (Solo visible en pantallas pequeñas) -->
        <div class="lg:hidden p-3 bg-slate-50 border-b border-slate-100 flex-shrink-0">
          <div class="flex p-1 bg-slate-200/70 rounded-2xl">
            <button 
              @click="monitorMobileTab = 'mesas'" 
              :class="[
                'flex-1 py-2.5 rounded-xl font-black text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition-all',
                monitorMobileTab === 'mesas' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-600'
              ]"
            >
              <span>🪑 Mesas ({{ pedidosParaAqui.length }})</span>
            </button>
            <button 
              @click="monitorMobileTab = 'llevar'" 
              :class="[
                'flex-1 py-2.5 rounded-xl font-black text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition-all',
                monitorMobileTab === 'llevar' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-600'
              ]"
            >
              <span>🥡 Para Llevar ({{ pedidosParaLlevar.length }})</span>
            </button>
          </div>
        </div>

        <!-- Contenido: Layout Split en Desktop / Tabs en Móvil -->
        <div class="flex-1 overflow-y-auto p-4 sm:p-8">
          <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            
            <!-- Columna Izquierda / Central: Croquis de Mesas -->
            <div 
              :class="[
                'lg:col-span-7 xl:col-span-8 flex flex-col space-y-4 sm:space-y-6',
                monitorMobileTab === 'mesas' ? 'block' : 'hidden lg:flex'
              ]"
            >
              <!-- Barra de Título del Mapa -->
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                  <div class="w-8 h-8 sm:w-9 sm:h-9 rounded-xl bg-blue-50 flex items-center justify-center border border-blue-100">
                    <LayoutGrid class="w-4 h-4 text-blue-600" />
                  </div>
                  <div>
                    <h4 class="text-xs sm:text-sm font-black text-slate-800 uppercase tracking-wider">Croquis del Restaurante</h4>
                    <p class="text-[9px] sm:text-[10px] text-slate-400 font-medium">Toca una mesa en servicio para abrir comanda</p>
                  </div>
                </div>
              </div>

              <!-- Cuadrícula 3x5 de Mesas del Minimapa -->
              <div class="grid grid-cols-3 gap-2.5 sm:gap-4">
                <div v-for="(fila, fIndex) in mesasLayout" :key="fIndex" class="contents">
                  <div
                    v-for="numeroMesa in fila"
                    :key="numeroMesa"
                    @click="onMesaClickEnMonitor(numeroMesa)"
                    :class="[
                      'relative aspect-[1/0.9] sm:aspect-[1/0.85] rounded-2xl sm:rounded-3xl p-2.5 sm:p-4 flex flex-col justify-between transition-all duration-300 border-2 select-none min-h-[80px]',
                      getMesaCardClass(numeroMesa)
                    ]"
                  >
                    <!-- Header de la Mesa: Número + Badge Estado -->
                    <div class="flex items-start justify-between">
                      <span class="text-xl sm:text-3xl font-black tracking-tighter leading-none">
                        {{ numeroMesa }}
                      </span>
                      <div v-if="getMesaEstado(numeroMesa) !== 'libre'" class="flex items-center gap-1">
                        <span 
                          :class="[
                            'px-1.5 sm:px-2 py-0.5 rounded-full text-[7px] sm:text-[9px] font-black uppercase tracking-wider border shadow-xs',
                            getEstadoBadgeClass(getMesaEstado(numeroMesa))
                          ]"
                        >
                          {{ getEstadoTexto(getMesaEstado(numeroMesa)) }}
                        </span>
                      </div>
                      <span v-else class="text-[8px] sm:text-[9px] font-bold text-slate-300 uppercase tracking-widest">
                        Libre
                      </span>
                    </div>

                    <!-- Footer de la Mesa: Folio y Total -->
                    <div v-if="getMesaPedido(numeroMesa)" class="flex items-end justify-between pt-1.5 sm:pt-2 border-t border-black/5">
                      <div>
                        <div class="text-[7px] sm:text-[8px] font-black uppercase tracking-wider opacity-60">Folio</div>
                        <div class="text-[11px] sm:text-sm font-black leading-none">#{{ getMesaPedido(numeroMesa)?.numero_display }}</div>
                      </div>
                      <div class="text-right">
                        <div class="text-[7px] sm:text-[8px] font-black uppercase tracking-wider opacity-60">Total</div>
                        <div class="text-[11px] sm:text-sm font-black leading-none">
                          ${{ Number(getMesaPedido(numeroMesa)?.total || 0).toFixed(0) }}
                        </div>
                      </div>
                    </div>

                    <div v-else class="text-[8px] sm:text-[9px] font-medium text-slate-300 italic">
                      Disponible
                    </div>
                  </div>
                </div>
              </div>

              <!-- Barra de Resumen de Estados del Monitor -->
              <div class="pt-3 sm:pt-4 border-t border-slate-100">
                <div class="grid grid-cols-2 sm:grid-cols-5 gap-2">
                  <div 
                    v-for="estado in ['pendiente', 'preparando', 'listo', 'entregado', 'cuenta_solicitada']" 
                    :key="estado"
                    class="flex items-center justify-between p-2 sm:p-2.5 rounded-xl bg-slate-50 border border-slate-100"
                  >
                    <div class="flex items-center gap-1.5">
                      <div :class="[getEstadoBadgeColor(estado), 'w-2 h-2 sm:w-2.5 sm:h-2.5 rounded-full']"></div>
                      <span class="text-[9px] sm:text-[10px] font-black text-slate-600 uppercase tracking-tight truncate">{{ getEstadoTexto(estado) }}</span>
                    </div>
                    <span class="text-[11px] sm:text-xs font-black text-slate-800 bg-white px-2 py-0.5 rounded-md border border-slate-200/60 shadow-2xs">
                      {{ estadisticasMonitor[estado] || 0 }}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Columna Derecha: Pedidos Para Llevar / Uber Eats -->
            <div 
              :class="[
                'lg:col-span-5 xl:col-span-4 bg-slate-50/70 border border-slate-100 rounded-2xl sm:rounded-3xl p-4 sm:p-6 flex flex-col space-y-4',
                monitorMobileTab === 'llevar' ? 'block' : 'hidden lg:flex'
              ]"
            >
              <!-- Header Para Llevar -->
              <div class="flex items-center justify-between pb-3 border-b border-slate-200/60">
                <div class="flex items-center gap-3">
                  <div class="w-8 h-8 sm:w-9 sm:h-9 rounded-xl bg-amber-50 flex items-center justify-center border border-amber-200">
                    <Truck class="w-4 h-4 text-amber-700" />
                  </div>
                  <div>
                    <h4 class="text-xs sm:text-sm font-black text-slate-800 uppercase tracking-wider">Para Llevar & Apps</h4>
                    <p class="text-[9px] sm:text-[10px] text-slate-400 font-medium">Pedidos externos en curso</p>
                  </div>
                </div>
                <span class="px-2.5 py-1 rounded-xl bg-white border border-slate-200 text-slate-700 text-xs font-black shadow-2xs">
                  {{ pedidosParaLlevar.length }}
                </span>
              </div>

              <!-- Lista de Pedidos Para Llevar -->
              <div class="space-y-3 max-h-[500px] overflow-y-auto pr-1">
                <div v-if="pedidosParaLlevar.length === 0" class="py-12 text-center opacity-50">
                  <Package class="w-12 h-12 text-slate-300 mx-auto mb-2" />
                  <p class="text-xs font-black text-slate-500 uppercase tracking-wider">Sin pedidos para llevar</p>
                  <p class="text-[10px] text-slate-400 mt-0.5">Todas las órdenes externas han sido entregadas</p>
                </div>

                <div
                  v-for="pedido in pedidosParaLlevar"
                  :key="pedido.id"
                  @click="verPedidoDesdeActuales(pedido)"
                  class="group bg-white border border-slate-200/80 hover:border-blue-500 rounded-2xl p-4 shadow-sm hover:shadow-md transition-all duration-300 cursor-pointer text-left active:scale-98"
                >
                  <div class="flex items-start justify-between gap-2 mb-2">
                    <div class="flex-1 min-w-0">
                      <div class="flex items-center gap-1.5 mb-1">
                        <span class="text-xs">{{ pedido.tipo_orden === 'uber_eats' ? '🚗' : '📦' }}</span>
                        <span class="text-[9px] font-black text-blue-600 uppercase tracking-widest">
                          {{ pedido.tipo_orden === 'uber_eats' ? 'Uber Eats' : 'Para Llevar' }}
                        </span>
                      </div>
                      <h5 class="text-xs sm:text-sm font-black text-slate-800 uppercase tracking-tight truncate">
                        {{ pedido.nombre_cliente || 'Cliente sin nombre' }}
                      </h5>
                    </div>
                    <div class="text-right">
                      <div class="text-xs sm:text-sm font-black text-slate-900">
                        ${{ Number(pedido.total || 0).toFixed(0) }}
                      </div>
                      <div class="text-[9px] font-bold text-slate-400">
                        #{{ pedido.numero_display }}
                      </div>
                    </div>
                  </div>

                  <div class="flex items-center justify-between pt-2 border-t border-slate-100">
                    <span 
                      :class="[
                        'px-2.5 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider border',
                        getEstadoBadgeClass(pedido.estado)
                      ]"
                    >
                      {{ getEstadoTexto(pedido.estado) }}
                    </span>
                    <div class="flex items-center gap-1 text-[10px] font-black text-blue-600 group-hover:translate-x-0.5 transition-transform">
                      <span>Ver Comanda</span>
                      <ChevronRight class="w-3.5 h-3.5" />
                    </div>
                  </div>
                </div>
              </div>
            </div>

          </div>
        </div>
      </div>
    </div>

    <!-- Modal de Espera: Cargando pedidos antes de mostrar mesas -->
    <div
      v-if="esperandoCargaMesas"
      class="fixed inset-0 z-50 flex items-center justify-center"
    >
      <!-- Backdrop -->
      <div class="absolute inset-0 bg-black bg-opacity-60"></div>
      <!-- Card -->
      <div class="relative bg-white rounded-2xl p-8 max-w-xs w-full mx-4 shadow-2xl flex flex-col items-center gap-4">
        <!-- Spinner -->
        <div class="w-14 h-14 rounded-full border-4 border-[#FDB700] border-t-transparent animate-spin"></div>
        <h3 class="text-lg font-bold text-[#00126D]">Cargando mesas...</h3>
        <p class="text-sm text-gray-500 text-center">Verificando disponibilidad de mesas,<br>un momento por favor.</p>
      </div>
    </div>

    <!-- Modal de Selección de Mesas (Grid Map Responsive) -->
    <div
      v-if="showMesaModal"
      class="fixed inset-0 z-[150] flex items-center justify-center p-4 lg:p-12"
      @click.self="closeMesaModal"
    >
      <!-- Backdrop -->
      <div class="absolute inset-0 bg-slate-900/80 backdrop-blur-md"></div>
      
      <!-- Modal Content -->
      <div class="relative bg-white rounded-[3.5rem] w-full max-w-xl shadow-2xl flex flex-col overflow-hidden animate-in zoom-in-95 duration-500 max-h-[85vh]">
        
        <!-- Header -->
        <div class="p-8 sm:p-10 pb-6 flex items-center justify-between border-b border-slate-50">
          <div class="flex items-center gap-4">
            <div class="w-12 h-12 bg-blue-50 rounded-2xl flex items-center justify-center border border-blue-100/50 flex-shrink-0">
               <span class="text-2xl">🪑</span>
            </div>
            <div>
              <h3 class="text-2xl font-black text-slate-800 tracking-tight uppercase leading-none mb-1">Mesa</h3>
              <p class="text-[9px] font-black text-blue-500 uppercase tracking-widest">Seleccionar Ubicación</p>
            </div>
          </div>
          <button @click="closeMesaModal" class="p-3 rounded-2xl bg-slate-50 text-slate-400 hover:text-slate-800 transition-all active:scale-95">
            <X class="w-5 h-5" />
          </button>
        </div>
        
        <!-- Layout de Mesas -->
        <div class="flex-1 overflow-y-auto p-8 sm:p-10">
          <div class="grid grid-cols-3 gap-3 sm:gap-4 lg:gap-5">
            <div v-for="(fila, index) in mesasLayout" :key="index" class="contents">
              <button
                v-for="numeroMesa in fila"
                :key="numeroMesa"
                @click="seleccionarMesa(numeroMesa)"
                :class="[
                  'group relative aspect-square rounded-3xl flex flex-col items-center justify-center transition-all duration-300 border-2',
                  mesasOcupadasReactivo.has(numeroMesa)
                    ? 'bg-blue-50 border-blue-200 text-blue-600 shadow-md'
                    : 'bg-white border-slate-100 text-slate-800 hover:border-blue-600 hover:scale-[1.05] hover:shadow-xl hover:shadow-blue-900/10'
                ]"
              >
                <span class="text-xl sm:text-2xl font-black tracking-tighter relative z-10">{{ numeroMesa }}</span>
                <div v-if="mesasOcupadasReactivo.has(numeroMesa)" class="absolute top-2 right-2 flex items-center gap-1">
                   <div class="w-1.5 h-1.5 bg-blue-600 rounded-full animate-pulse"></div>
                </div>
              </button>
            </div>
          </div>
          
          <!-- Modernized Legend -->
          <div class="mt-8 flex justify-center gap-6 pt-6 border-t border-slate-50">
            <div class="flex items-center gap-2">
              <div class="w-3 h-3 bg-white border border-slate-100 rounded-md"></div>
              <span class="text-[9px] font-black text-slate-400 uppercase tracking-widest leading-none">Libre</span>
            </div>
            <div class="flex items-center gap-2">
              <div class="w-3 h-3 bg-blue-600 rounded-md shadow-sm shadow-blue-200"></div>
              <span class="text-[9px] font-black text-blue-600 uppercase tracking-widest leading-none italic">En Servicio</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal de Mesa Ocupada -->
    <div
      v-if="showMesaOcupadaModal"
      class="fixed inset-0 z-50 flex items-center justify-center"
      @click.self="cerrarMesaOcupadaModal"
    >
      <!-- Backdrop -->
      <div class="absolute inset-0 bg-black bg-opacity-75"></div>
      
      <!-- Modal Content -->
      <div class="relative bg-white rounded-2xl p-8 max-w-md w-full mx-4 shadow-2xl">
        <!-- Header -->
        <div class="text-center mb-8">
          <div class="text-6xl mb-4">🍽️</div>
          <h3 class="text-2xl font-bold text-[#00126D] mb-2">Mesa {{ mesa }} Ocupada</h3>
          <p class="text-gray-600">¿Qué quieres hacer?</p>
        </div>
        
        <!-- Opciones -->
        <div class="space-y-4">
          <button
            @click="agregarArticulosMesa"
            class="w-full p-6 bg-white border-2 border-gray-200 rounded-xl hover:border-[#FDB700] hover:bg-yellow-50 transition-all group text-left"
          >
            <div class="flex items-center gap-4">
              <div class="text-4xl">➕</div>
              <div>
                <div class="text-lg font-bold text-[#00126D] group-hover:text-[#FDB700]">Agregar artículos</div>
                <div class="text-sm text-gray-600">Añadir más platillos al pedido existente</div>
              </div>
            </div>
          </button>
          
          <button
            @click="verPedidoActual"
            class="w-full p-6 bg-white border-2 border-gray-200 rounded-xl hover:border-blue-300 hover:bg-blue-50 transition-all group text-left"
          >
            <div class="flex items-center gap-4">
              <div class="text-4xl">👁️</div>
              <div>
                <div class="text-lg font-bold text-[#00126D] group-hover:text-blue-600">Ver pedido actual</div>
                <div class="text-sm text-gray-600">Revisar lo que ya pidieron</div>
              </div>
            </div>
          </button>
          
          <button
            @click="cerrarMesaOcupadaModal"
            class="w-full p-4 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-xl transition-all text-center"
          >
            ← Cancelar
          </button>
        </div>
      </div>
    </div>

    <!-- Modal Ver Pedido Actual (Rediseño Moderno con Gestión de Bebidas y Acciones Rápidas) -->
    <div
      v-if="showVerPedidoModal"
      class="fixed inset-0 z-[140] flex items-center justify-center p-0 sm:p-6"
    >
      <!-- Backdrop -->
      <div class="absolute inset-0 bg-slate-900/80 backdrop-blur-md hidden sm:block" @click="cerrarVerPedidoModal"></div>
      
      <!-- Modal Content (Full Screen en móvil con footer sticky) -->
      <div class="relative bg-white rounded-none sm:rounded-[3rem] w-full max-w-2xl shadow-2xl flex flex-col overflow-hidden h-full sm:h-auto sm:max-h-[88vh] animate-in zoom-in-95 duration-300 border-0 sm:border sm:border-slate-100">
        
        <!-- Header -->
        <div class="px-6 py-5 sm:p-8 border-b border-slate-100 flex items-center justify-between bg-slate-50/60 flex-shrink-0">
          <div class="flex items-center gap-4">
            <div class="w-12 h-12 sm:w-14 sm:h-14 bg-blue-600 text-white rounded-2xl flex items-center justify-center shadow-lg shadow-blue-500/20 text-2xl flex-shrink-0">
              <span v-if="pedidoActual?.tipo_orden === 'aqui'">🪑</span>
              <span v-else-if="pedidoActual?.tipo_orden === 'uber_eats'">🚗</span>
              <span v-else>📦</span>
            </div>
            <div>
              <div class="flex items-center gap-2 mb-1">
                <h3 class="text-xl sm:text-2xl font-black text-slate-800 tracking-tight uppercase leading-none">
                  {{ pedidoActual?.tipo_orden === 'aqui' ? `Mesa ${pedidoActual.mesa}` : (pedidoActual?.nombre_cliente || 'Comanda') }}
                </h3>
                <span 
                  :class="[
                    'px-2.5 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider border shadow-2xs',
                    getEstadoBadgeClass(pedidoActual?.estado || '')
                  ]"
                >
                  {{ getEstadoTexto(pedidoActual?.estado || '') }}
                </span>
              </div>
              <p class="text-[10px] sm:text-xs font-bold text-slate-400 uppercase tracking-widest">
                Comanda #{{ pedidoActual?.numero_display }} • {{ formatTime(pedidoActual?.fecha_creacion || '') }}
              </p>
            </div>
          </div>

          <button 
            @click="cerrarVerPedidoModal" 
            class="w-10 h-10 rounded-2xl bg-white border border-slate-200 text-slate-400 hover:text-slate-800 hover:bg-slate-100 transition-all active:scale-90 flex items-center justify-center shadow-2xs"
          >
            <X class="w-5 h-5" />
          </button>
        </div>
        
        <!-- Cuerpo scrolleable del Pedido -->
        <div class="flex-1 overflow-y-auto p-4 sm:p-8 space-y-6">
          
          <!-- Empty State si no hay artículos -->
          <div v-if="articulosEditables.length === 0" class="py-12 text-center opacity-40">
            <Package class="w-12 h-12 text-slate-300 mx-auto mb-2" />
            <p class="text-sm font-black text-slate-400 uppercase tracking-wider">Sin artículos registrados</p>
          </div>

          <!-- SECCIÓN 1: BEBIDAS (Servicio Directo de Mesero) -->
          <div v-if="articulosBebidas.length > 0" class="bg-blue-50/50 border border-blue-100 rounded-3xl p-4 sm:p-6 space-y-4">
            <div class="flex items-center justify-between pb-3 border-b border-blue-100/80">
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-xl bg-blue-600 text-white flex items-center justify-center shadow-sm text-sm">
                  🥤
                </div>
                <div>
                  <h4 class="text-xs sm:text-sm font-black text-slate-800 uppercase tracking-wider">Bebidas y Refrescos</h4>
                  <p class="text-[9px] text-blue-600 font-bold uppercase tracking-wider">Servicio directo de mesero</p>
                </div>
              </div>
              <span class="px-2.5 py-1 rounded-xl bg-white border border-blue-200 text-blue-700 text-xs font-black">
                {{ articulosBebidas.length }} items
              </span>
            </div>

            <!-- Lista de Bebidas -->
            <div class="space-y-3">
              <div 
                v-for="articulo in articulosBebidas" 
                :key="articulo.id"
                class="bg-white rounded-2xl p-4 border border-blue-100 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3"
              >
                <div class="flex items-center gap-3 flex-1 min-w-0">
                  <div class="w-9 h-9 rounded-xl bg-slate-50 flex items-center justify-center text-lg flex-shrink-0">
                    🥤
                  </div>
                  <div class="min-w-0 flex-1">
                    <div class="flex items-center gap-2">
                      <span class="text-xs font-black text-blue-600 bg-blue-50 px-2 py-0.5 rounded-md">
                        {{ articulo.cantidad }}x
                      </span>
                      <h5 class="text-xs sm:text-sm font-black text-slate-800 uppercase tracking-tight truncate">
                        {{ articulo.platillo?.kds_name || articulo.platillo?.nombre }}
                      </h5>
                    </div>
                    <div class="text-[10px] font-bold text-slate-400 mt-0.5">
                      ${{ Number(articulo.platillo?.precio || 0).toFixed(0) }} c/u • Subtotal: ${{ (Number(articulo.platillo?.precio || 0) * articulo.cantidad).toFixed(0) }}
                    </div>
                  </div>
                </div>

                <!-- Estado y Acción Rápida de Entrega de Bebida -->
                <div class="flex items-center justify-between sm:justify-end gap-3 pt-2 sm:pt-0 border-t sm:border-t-0 border-slate-50">
                  <span 
                    v-if="articulo.estado_item === 'entregado'"
                    class="px-3 py-1.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-700 text-[10px] font-black uppercase tracking-wider flex items-center gap-1.5"
                  >
                    <CheckCircle class="w-3.5 h-3.5 text-emerald-600" />
                    <span>Entregada</span>
                  </span>
                  
                  <button
                    v-else
                    @click="marcarBebidaEntregada(articulo.id)"
                    class="w-full sm:w-auto px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl text-[11px] font-black uppercase tracking-wider shadow-md shadow-blue-500/20 active:scale-95 transition-all flex items-center justify-center gap-1.5"
                  >
                    <Check class="w-3.5 h-3.5" />
                    <span>Marcar Entregada</span>
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- SECCIÓN 2: ALIMENTOS Y PLATILLOS DE COCINA -->
          <div v-if="articulosComida.length > 0" class="space-y-4">
            <div class="flex items-center justify-between pb-2 border-b border-slate-100">
              <div class="flex items-center gap-2">
                <span class="text-base">🍲</span>
                <h4 class="text-xs sm:text-sm font-black text-slate-800 uppercase tracking-wider">Alimentos de Cocina</h4>
              </div>
              <span class="text-[10px] font-black text-slate-400 uppercase tracking-widest">
                {{ articulosComida.length }} items
              </span>
            </div>

            <!-- Lista de Alimentos -->
            <div class="space-y-3">
              <div 
                v-for="articulo in articulosComida" 
                :key="articulo.id"
                class="bg-slate-50/80 rounded-2xl p-4 border border-slate-200/60 shadow-2xs space-y-3"
              >
                <div class="flex items-start justify-between gap-3">
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2 mb-1">
                      <span v-if="!esPedidoPendiente" class="text-xs font-black text-slate-700 bg-white px-2 py-0.5 rounded-md border border-slate-200/80">
                        {{ articulo.cantidad }}x
                      </span>
                      <h5 class="text-xs sm:text-sm font-black text-slate-800 uppercase tracking-tight truncate">
                        {{ articulo.platillo?.kds_name || articulo.platillo?.nombre }}
                      </h5>
                    </div>
                    <div v-if="articulo.proteina || articulo.tamano" class="text-[9px] font-bold text-blue-600 uppercase tracking-widest">
                      {{ articulo.proteina }} {{ articulo.tamano ? `• ${articulo.tamano}` : '' }}
                    </div>
                    <div class="text-[10px] font-bold text-slate-400 mt-0.5">
                      ${{ Number(articulo.platillo?.precio || 0).toFixed(0) }} c/u • Subtotal: ${{ (Number(articulo.platillo?.precio || 0) * articulo.cantidad).toFixed(0) }}
                    </div>
                  </div>

                  <!-- Controles de Cantidad en Modo Pendiente -->
                  <div v-if="esPedidoPendiente" class="flex items-center gap-2 flex-shrink-0">
                    <div class="flex items-center gap-1 bg-white p-1 rounded-xl border border-slate-200 shadow-2xs">
                      <button 
                        @click="ajustarCantidadPedido(articulosEditables.indexOf(articulo), -1)"
                        class="w-7 h-7 rounded-lg bg-slate-50 hover:bg-slate-100 flex items-center justify-center text-slate-600 font-bold transition-all active:scale-90"
                        :disabled="articulo.cantidad <= 0"
                      >
                        <Minus class="w-3 h-3" />
                      </button>
                      <span class="w-6 text-center font-black text-xs text-slate-800">{{ articulo.cantidad }}</span>
                      <button 
                        @click="ajustarCantidadPedido(articulosEditables.indexOf(articulo), 1)"
                        class="w-7 h-7 rounded-lg bg-blue-50 hover:bg-blue-100 flex items-center justify-center text-blue-600 font-bold transition-all active:scale-90"
                      >
                        <Plus class="w-3 h-3" />
                      </button>
                    </div>
                    <button 
                      @click="eliminarArticuloPedido(articulosEditables.indexOf(articulo))"
                      class="w-8 h-8 rounded-xl bg-red-50 hover:bg-red-100 text-red-500 border border-red-200 flex items-center justify-center transition-all active:scale-90"
                      :disabled="articulo.cantidad === 0"
                    >
                      <Trash2 class="w-3.5 h-3.5" />
                    </button>
                  </div>

                  <!-- Estado en Cocina (KDS) cuando no es editable -->
                  <div v-else class="text-right flex-shrink-0">
                    <span 
                      :class="[
                        'px-2.5 py-1 rounded-xl text-[9px] font-black uppercase tracking-wider border',
                        getEstadoBadgeClass(articulo.estado_item)
                      ]"
                    >
                      {{ getArticuloEstadoLabel(articulo.estado_item) }}
                    </span>
                  </div>
                </div>

                <!-- Modificaciones / Notas -->
                <div v-if="esPedidoPendiente">
                  <input 
                    v-model="articulo.modificaciones" 
                    placeholder="Notas o modificaciones (ej: sin cebolla)..." 
                    class="w-full px-3 py-2 bg-white border border-slate-200 rounded-xl text-[11px] font-medium text-slate-700 placeholder:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-100"
                  />
                </div>
                <div v-else-if="articulo.modificaciones" class="text-[11px] text-amber-800 bg-amber-50 px-3 py-1.5 rounded-xl border border-amber-200/60 font-medium">
                  📝 {{ articulo.modificaciones }}
                </div>
              </div>
            </div>
          </div>

          <!-- Resumen de Total -->
          <div class="bg-slate-900 text-white rounded-3xl p-5 sm:p-6 shadow-xl">
            <div class="flex items-center justify-between">
              <div>
                <span class="text-[9px] font-black uppercase tracking-[0.2em] text-blue-400">Total Acumulado</span>
                <div class="text-2xl sm:text-3xl font-black tracking-tight">
                  <span class="text-blue-400 text-lg mr-0.5">$</span>
                  <span v-if="esPedidoPendiente && hayCantidadesCambiadas">{{ totalDinamicoModal.toFixed(0) }}</span>
                  <span v-else>{{ Number(pedidoActual?.total || 0).toFixed(0) }}</span>
                  <span class="text-sm opacity-50">.00</span>
                </div>
              </div>

              <div v-if="totalDesactualizado" class="text-right">
                <span class="text-[9px] font-black uppercase tracking-widest text-amber-400 block">Cambios Sin Guardar</span>
                <span class="text-xs font-bold text-slate-400">Original: ${{ Number(pedidoActual?.total || 0).toFixed(0) }}</span>
              </div>
            </div>
          </div>

        </div>

        <!-- Barra de Acciones Fijas (Footer) -->
        <div class="p-4 sm:p-6 border-t border-slate-100 bg-slate-50/80 space-y-3 flex-shrink-0">
          
          <!-- Botón Guardar Cambios (si está pendiente y se modificaron artículos) -->
          <button 
            v-if="esPedidoPendiente && hayCantidadesCambiadas"
            @click="guardarCambiosPedido"
            :disabled="loading"
            class="w-full py-3.5 bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-slate-900 font-black rounded-2xl transition-all text-xs uppercase tracking-wider shadow-lg shadow-amber-500/20 flex items-center justify-center gap-2 active:scale-98"
          >
            <Save class="w-4 h-4" />
            <span>{{ loading ? 'Guardando Cambios...' : 'Guardar Modificaciones' }}</span>
          </button>

          <!-- Fila de Acciones Principales -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            
            <!-- Botón AGREGAR MÁS ARTÍCULOS -->
            <button
              @click="irAAgregarMasArticulos"
              class="w-full py-4 bg-emerald-600 hover:bg-emerald-500 active:scale-98 text-white font-black rounded-2xl transition-all text-xs uppercase tracking-wider shadow-lg shadow-emerald-600/20 flex items-center justify-center gap-2"
            >
              <Plus class="w-4 h-4" />
              <span>Agregar Más Artículos</span>
            </button>

            <!-- Botón SOLICITAR CUENTA (prominente y clickeable) -->
            <button
              v-if="pedidoActual?.estado === 'cuenta_solicitada'"
              disabled
              class="w-full py-4 bg-purple-100 border border-purple-300 text-purple-800 font-black rounded-2xl text-xs uppercase tracking-wider flex items-center justify-center gap-2 cursor-not-allowed"
            >
              <CheckCircle class="w-4 h-4 text-purple-600 animate-pulse" />
              <span>Cuenta Ya Solicitada (Caja)</span>
            </button>

            <button
              v-else
              @click="solicitarCuenta(pedidoActual)"
              class="w-full py-4 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 active:scale-98 text-white font-black rounded-2xl transition-all text-xs uppercase tracking-wider shadow-xl shadow-purple-600/25 flex items-center justify-center gap-2"
            >
              <CreditCard class="w-4 h-4" />
              <span>Solicitar Cuenta a Caja</span>
            </button>

          </div>

          <!-- Botón Cerrar / Volver -->
          <button
            @click="cerrarVerPedidoModal"
            class="w-full py-2.5 text-center text-slate-400 hover:text-slate-700 font-bold text-xs uppercase tracking-wider transition-colors"
          >
            Volver al Monitor de Mesas
          </button>
        </div>

      </div>
    </div>

    <!-- Modal de Especificaciones -->
    <div
      v-if="showEspecificacionesModal"
      class="fixed inset-0 z-50 flex items-center justify-center"
      @click.self="cerrarEspecificaciones"
    >
      <!-- Backdrop -->
      <div class="absolute inset-0 bg-black bg-opacity-50"></div>
      
      <!-- Modal Content -->
      <div class="relative bg-white rounded-2xl p-6 max-w-md w-full mx-4 shadow-2xl">
        <!-- Header -->
        <div class="flex items-center justify-between mb-6">
          <h3 class="text-xl font-bold text-[#00126D] flex items-center gap-2">
            ✏️ Especificaciones
          </h3>
          <button @click="cerrarEspecificaciones" class="text-gray-400 hover:text-gray-600 text-xl">
            ←
          </button>
        </div>
        
        <!-- Información del platillo -->
        <div v-if="platilloSeleccionado" class="mb-6 p-4 bg-gray-50 rounded-lg">
          <div class="font-bold text-[#00126D] mb-1">{{ platilloSeleccionado.kds_name || platilloSeleccionado.nombre }}</div>
          <div class="text-sm text-[#FDB700] font-semibold">$ {{ Number(platilloSeleccionado.precio).toFixed(2) }}</div>
          <div class="text-xs text-gray-600 mt-1">{{ platilloSeleccionado.descripcion }}</div>
        </div>

        <!-- Proteínas para Enchiladas 1/2 (MVP) -->
        <div v-if="platilloSeleccionado?.nombre?.toLowerCase().includes('enchiladas') && platilloSeleccionado?.nombre.includes('1/2')" class="mb-4 p-4 bg-white rounded-lg border border-gray-200">
          <div class="font-semibold text-[#00126D] mb-2">Proteína</div>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="p in enchiladasProteins"
              :key="p"
              @click="selectedEnchiladasProtein = p"
              :class="[
                'px-4 py-2 rounded border font-bold text-sm',
                selectedEnchiladasProtein === p ? 'bg-[#FDB700] text-[#00126D] border-[#FDB700]' : 'bg-white border-gray-200'
              ]"
            >
              {{ p }}
            </button>
          </div>
        </div>

        <!-- Proteínas para Enchiladas 1/2 (MVP) -->
        <div v-if="platilloSeleccionado?.nombre?.toLowerCase().includes('enchiladas') && platilloSeleccionado?.nombre.includes('1/2')" class="mb-6 p-4 bg-white rounded-lg border border-gray-200">
          <div class="font-semibold text-[#00126D] mb-2">Proteína</div>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="p in enchiladasProteins"
              :key="p"
              @click="selectedEnchiladasProtein = p"
              :class="[
                'px-4 py-2 rounded border font-bold text-sm',
                selectedEnchiladasProtein === p ? 'bg-[#FDB700] text-[#00126D] border-[#FDB700]' : 'bg-white border-gray-200'
              ]"
            >
              {{ p }}
            </button>
          </div>
        </div>
        

        <!-- Selector de cantidad discreto -->
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Cantidad
          </label>
          <div class="flex items-center gap-2">
            <button 
              @click="cantidadTemp = Math.max(1, cantidadTemp - 1)"
              class="w-8 h-8 bg-gray-100 hover:bg-gray-200 rounded-lg font-bold text-sm transition active:scale-95"
            >
              −
            </button>
            <div class="w-12 h-8 bg-gray-50 border-2 border-gray-200 rounded-lg flex items-center justify-center font-bold text-sm">
              {{ cantidadTemp }}
            </div>
            <button 
              @click="cantidadTemp = Math.min(99, cantidadTemp + 1)"
              class="w-8 h-8 bg-gray-100 hover:bg-gray-200 rounded-lg font-bold text-sm transition active:scale-95"
            >
              +
            </button>
          </div>
        </div>

        <!-- Especificaciones rápidas -->
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Especificaciones rápidas
          </label>
          <div class="grid grid-cols-2 gap-2 mb-3">
            <button
              v-for="esp in especificacionesComunes"
              :key="esp"
              @click="agregarEspecificacion(esp)"
              class="px-3 py-2 bg-gray-100 hover:bg-[#FDB700] hover:text-[#00126D] text-gray-700 text-sm rounded-lg transition-all active:scale-95 font-medium"
            >
              {{ esp }}
            </button>
          </div>
        </div>

        <!-- Campo de especificaciones -->
        <div class="mb-6">
          <label class="block text-sm font-bold text-[#00126D] mb-2">
            📝 Especificaciones personalizadas
          </label>
          <textarea
            v-model="especificacionesTemp"
            placeholder="Ej: Sin crema, sin zanahoria, extra lechuga..."
            class="w-full p-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-[#FDB700] focus:border-[#FDB700] transition bg-white resize-none"
            rows="2"
          ></textarea>
          <div class="text-xs text-gray-500 mt-1">
            💡 Usa los botones de arriba o escribe aquí
          </div>
        </div>
        
        <!-- Botones -->
        <div class="flex gap-3">
          <button
            @click="cerrarEspecificaciones"
            class="flex-1 px-4 py-3 bg-gray-100 hover:bg-gray-200 text-[#00126D] rounded-lg transition-all"
          >
            Cancelar
          </button>
          <button
            @click="confirmarEspecificaciones"
            class="flex-1 px-4 py-3 bg-[#FDB700] hover:bg-yellow-400 text-[#00126D] font-bold rounded-lg transition-all"
          >
            Agregar al Carrito
          </button>
        </div>
      </div>
    </div>

    <!-- Pozole Variant Modal -->
    <PozoleVariantModal
      v-if="showPozoleModal"
      :platillos="platillos.filter(p => p.categoria === 'Pozole')"
      :isOpen="showPozoleModal"
      @close="closePozoleModal"
      @select="selectPozoleVariant"
    />

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
/* Animaciones para carrito móvil */
.carrito-mobile {
  animation: slideUpIn 0.3s ease-out;
}

@keyframes slideUpIn {
  from {
    transform: translateY(100%);
  }
  to {
    transform: translateY(0);
  }
}

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

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px) scaleY(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scaleY(1);
  }
}


/* Digital Design System */
.bg-glass {
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.bg-glass-dark {
  background: rgba(15, 23, 42, 0.85);
  backdrop-filter: blur(30px);
  -webkit-backdrop-filter: blur(30px);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.shadow-premium {
  box-shadow: 
    0 10px 40px -10px rgba(0, 18, 109, 0.08),
    0 20px 60px -15px rgba(0, 0, 0, 0.04);
}

.text-gradient {
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

/* Custom Scrollbar for a cleaner look */
::-webkit-scrollbar {
  width: 6px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.05);
  border-radius: 10px;
}
::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.1);
}

/* Animations */
@keyframes slideDownFade {
  from { opacity: 0; transform: translateY(-20px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes slideUpFade {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes zoomFade {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}

.animate-slide-down { animation: slideDownFade 0.6s cubic-bezier(0.2, 0.8, 0.2, 1); }
.animate-slide-up { animation: slideUpFade 0.6s cubic-bezier(0.2, 0.8, 0.2, 1); }
.animate-zoom { animation: zoomFade 0.5s cubic-bezier(0.2, 0.8, 0.2, 1); }

.animate-in {
  animation: slideUpFade 0.4s ease-out;
}

.fade-in {
  animation: fadeIn 0.3s ease-out;
}

/* Lucide Transiciones */
.rotate-180 {
  transform: rotate(180deg);
  transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Pozole tile height adjustment */
.pozole-tile { height: calc(15rem - 5px); }

/* Touch Optimization */
@media (mousedown: false) {
  .btn-touch-active:active {
    transform: scale(0.96);
    opacity: 0.9;
  }
}
</style>
