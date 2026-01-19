<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { usePedidosStore } from '../stores/pedidos'
import { api } from '../api/client'
import type { PlatilloResponse, PedidoCreate, ArticuloPedidoCreate } from '../types'
import PozoleVariantModal from '../components/PozoleVariantModal.vue'
import AppHeader from '@/components/AppHeader.vue'

const router = useRouter()
const auth = useAuthStore()
const pedidosStore = usePedidosStore()

// Referencias reactivas
const platillos = ref<PlatilloResponse[]>([])
const carrito = ref<Array<{ platillo: PlatilloResponse; cantidad: number; modificaciones: string }>>([])
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
  return articulo?.platillo?.categoria === 'Bebidas'
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

// Control del modal de nombre de cliente
const showNombreClienteModal = ref(false)

// Control del modal de especificaciones
const showEspecificacionesModal = ref(false)
const platilloSeleccionado = ref<PlatilloResponse | null>(null)
const especificacionesTemp = ref('')
const proteinaSeleccionada = ref('')
const cantidadTemp = ref(1)

// Computed reactivo para mesas ocupadas basado en el store - DATOS EN TIEMPO REAL
const mesasOcupadasReactivo = computed(() => {
  const pedidosActivos = pedidosStore.pedidos.filter((pedido: any) => 
    pedido.tipo_orden === 'aqui' && 
    ['pendiente', 'preparando', 'listo', 'entregado', 'cuenta_solicitada'].includes(pedido.estado) &&
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
  } catch (error) {
    console.error('❌ Mesero View: Error en inicialización:', error)
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
    console.log('👁️ Modal "Ver Pedido" abierto - iniciando escucha de WebSocket')
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


// Categorías únicas de platillos (excluyendo Pozoles) - Postres penúltimo, Bebidas último
const categorias = computed(() => {
  const cats = [...new Set(platillos.value
    .filter(p => p.categoria !== 'Pozole' && p.estado === 'disponible')
    .map(p => p.categoria))]
  
  // Ordenamiento personalizado: Postres penúltimo, Bebidas último
  return cats.sort((a, b) => {
    // Si uno es Bebidas, va al final
    if (a === 'Bebidas') return 1
    if (b === 'Bebidas') return -1
    
    // Si uno es Postres, va después de todo excepto Bebidas
    if (a === 'Postres') return 1
    if (b === 'Postres') return -1
    
    // Resto en orden alfabético
    return a.localeCompare(b)
  })
})

// Platillos por categoría (excluyendo Pozoles)
const platillosPorCategoria = computed(() => {
  return categorias.value.reduce((acc, cat) => {
    acc[cat] = platillos.value.filter(p => p.categoria === cat && p.estado === 'disponible')
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

// Colores por categoría (mismo esquema que POS)
const getCategoryColor = (category: string) => {
  const colors: Record<string, string> = {
    'Pozoles': 'bg-red-500 hover:bg-red-600',
    'Bebidas': 'bg-blue-500 hover:bg-blue-600',
    'Antojitos': 'bg-green-500 hover:bg-green-600',
    'Postres': 'bg-yellow-500 hover:bg-yellow-600',
    'Extras': 'bg-purple-500 hover:bg-purple-600'
  }
  return colors[category] || 'bg-gray-500 hover:bg-gray-600'
}

// Agregar producto al carrito (para platillos normales - solo usado para pozoles)
const agregarAlCarrito = (platillo: any) => {
  const existente = carrito.value.find(item => 
    item.platillo.id === platillo.id && 
    item.modificaciones === ''
  )
  
  if (existente) {
    existente.cantidad++
  } else {
    carrito.value.push({
      platillo,
      cantidad: 1,
      modificaciones: ''
    })
  }
}

// Abrir modal de variantes de pozole
const openPozoleVariants = (color: 'Verde' | 'Blanco' | 'Rojo') => {
  selectedPozoleColor.value = color
  showPozoleModal.value = true
}

// Cerrar modal de pozole
const closePozoleModal = () => {
  showPozoleModal.value = false
  selectedPozoleColor.value = null
}

// Seleccionar variante de pozole desde el modal
const selectPozoleVariant = (platillo: PlatilloResponse) => {
  // NO agregar al carrito aquí, solo pasar al modal de especificaciones
  closePozoleModal()
  // Abrir especificaciones donde se agregará al carrito una sola vez
  abrirEspecificaciones(platillo)
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
      modificaciones: item.modificaciones || ''
    }))

    if (modoAgregarArticulos.value && pedidoExistenteId.value) {
      // Modo agregar artículos - usar endpoint PUT
      const response = await api.put(`/pedidos/${pedidoExistenteId.value}/agregar-articulos`, {
        articulos,
        mesero_id: auth.user?.id
      })
      
      if (response.status === 200) {
        const mensajeExito = `Artículos agregados a Mesa ${mesa.value}`
        showSuccessNotification(mensajeExito)
        
        // Limpiar y salir del modo agregar
        limpiarModoAgregar()
      } else {
        showErrorNotification('Error al agregar artículos')
      }
      
    } else {
      // Modo nuevo pedido - usar endpoint POST
      const pedidoData: PedidoCreate = {
        nombre_cliente: (tipoOrden.value === 'llevar' || tipoOrden.value === 'uber_eats') ? nombreCliente.value : null,
        mesa: tipoOrden.value === 'aqui' ? mesa.value : null,
        tipo_orden: tipoOrden.value,
        articulos
      }

      const nuevoPedido = await pedidosStore.createPedido(pedidoData)
      
      if (nuevoPedido) {
        // Limpiar formulario y reiniciar flujo
        limpiarFormulario()
        
        const mensajeExito = tipoOrden.value === 'aqui' 
          ? `Pedido #${nuevoPedido.numero_display} enviado a cocina para Mesa ${mesa.value}` 
          : `Pedido #${nuevoPedido.numero_display} ${tipoOrden.value === 'uber_eats' ? 'Uber Eats' : 'para llevar'} enviado a cocina (${nombreCliente.value})`
        
        showSuccessNotification(mensajeExito)
      } else {
        showErrorNotification(pedidosStore.error || 'Error al crear pedido')
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
  if (tipo === 'aqui') {
    // Si es "aquí", abrir modal de mesas inmediatamente
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


// Función para obtener color por estado
const getEstadoColor = (estado: string) => {
  switch (estado) {
    case 'pendiente': return 'bg-yellow-100 text-yellow-800'
    case 'preparando': return 'bg-blue-100 text-blue-800'
    case 'listo': return 'bg-green-100 text-green-800'
    case 'entregado': return 'bg-purple-100 text-purple-800'
    case 'cuenta_solicitada': return 'bg-orange-100 text-orange-800'
    default: return 'bg-gray-100 text-gray-800'
  }
}

// Función para ver/modificar pedido desde lista
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

// Computed para pedidos actuales (tiempo real desde store)
const pedidosActualesReactivo = computed(() => {
  return pedidosStore.pedidos
    .filter(pedido => pedido.estado !== 'pagado')
    .sort((a, b) => new Date(b.fecha_creacion).getTime() - new Date(a.fecha_creacion).getTime())
})

// Computed para separar pedidos por tipo
const pedidosParaAqui = computed(() => {
  return pedidosActualesReactivo.value.filter(pedido => pedido.tipo_orden === 'aqui')
})

const pedidosParaLlevar = computed(() => {
  return pedidosActualesReactivo.value.filter(pedido => pedido.tipo_orden === 'llevar' || pedido.tipo_orden === 'uber_eats')
})

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
    const existente = carrito.value.find(item => 
      item.platillo.id === platilloSeleccionado.value!.id && 
      item.modificaciones === especificacionesTemp.value
    )
    
    if (existente) {
      existente.cantidad += cantidadTemp.value
    } else {
      carrito.value.push({
        platillo: platilloSeleccionado.value,
        cantidad: cantidadTemp.value,
        modificaciones: especificacionesTemp.value
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
  // Abrir modal inmediatamente - los datos ya están en el store
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
    showNotificationMessage('Mesa ocupada. Ve a "Pedidos Actuales" para modificar el pedido existente.', 'info')
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
    if (showVerPedidoModal.value && !hayCantidadesCambiadas.value) {
      articulosEditables.value = pedidoActualizado.articulos_pedido.map((articulo: any) => ({
        ...articulo,
        cantidad_original: articulo.cantidad,
        modificaciones_original: articulo.modificaciones || '',
        eliminado: false
      }))
      console.log('📱 Modal artículos actualizados por WebSocket')
    } else if (showVerPedidoModal.value) {
      console.log('⚠️ Modal tiene cambios locales, solo actualizada info básica')
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
  <div class="min-h-screen flex flex-col bg-gradient-to-br from-[#F8FAFC] to-[#EEF2F5]">
    <!-- Header -->
    <AppHeader title="Mesero" />

    <main class="flex-1 p-6 pb-24 lg:pb-6">
      <!-- Layout responsive: móvil = solo menú, desktop = grid -->
      <div class="lg:grid lg:grid-cols-3 lg:gap-6">
        <!-- Menu -->
        <section class="lg:col-span-2 space-y-6">
        <!-- Solo mostrar el menú después de configurar el pedido -->
        <div v-if="!pedidoConfigurado" class="p-8 text-center text-gray-600 font-medium">
          <div class="text-6xl mb-4">🍽️</div>
          <h2 class="text-xl font-bold text-[#00126D] mb-2">Configurando pedido...</h2>
          <p>Selecciona el tipo de orden para continuar</p>
        </div>

        <div v-else-if="loading" class="p-4 text-center text-gray-600 font-medium">Cargando platillos...</div>

        <div v-else-if="pedidoConfigurado">
          <!-- Pozoles Section -->
          <div v-if="hasAnyPozole && pozolesByColor.Verde.length + pozolesByColor.Blanco.length + pozolesByColor.Rojo.length > 0" class="mb-6">
            <h2 class="text-xl font-bold text-[#00126D] mb-4 flex items-center gap-2">
              <span class="text-2xl">🍲</span> Pozoles Especiales
            </h2>
            <div class="grid grid-cols-3 gap-4">
              <button
                v-if="pozolesByColor.Verde.length > 0"
                @click="openPozoleVariants('Verde')"
                class="bg-gradient-to-br from-green-50 to-green-100 border-2 border-green-500 rounded-xl p-6 text-center hover:shadow-xl hover:scale-105 transition-all font-bold text-green-700 active:scale-95"
              >
                🟢<br>Verde
              </button>
              <button
                v-if="pozolesByColor.Blanco.length > 0"
                @click="openPozoleVariants('Blanco')"
                class="bg-gradient-to-br from-gray-50 to-gray-100 border-2 border-gray-400 rounded-xl p-6 text-center hover:shadow-xl hover:scale-105 transition-all font-bold text-gray-700 active:scale-95"
              >
                ⚪<br>Blanco
              </button>
              <button
                v-if="pozolesByColor.Rojo.length > 0"
                @click="openPozoleVariants('Rojo')"
                class="bg-gradient-to-br from-red-50 to-red-100 border-2 border-red-500 rounded-xl p-6 text-center hover:shadow-xl hover:scale-105 transition-all font-bold text-red-700 active:scale-95"
              >
                🔴<br>Rojo
              </button>
            </div>
          </div>

          <!-- Otras Categorías -->
          <div v-for="categoria in categorias" :key="categoria" class="mb-6">
            <!-- Header de categoría clickeable -->
            <button 
              @click="toggleCategoria(categoria)"
              class="w-full text-xl font-bold mb-4 px-4 py-3 rounded-lg border-2 text-white bg-gradient-to-r from-[#00126D] to-[#001a4d] hover:from-[#001a4d] hover:to-[#002866] transition-all duration-300 flex items-center justify-between group"
            >
              <span>{{ categoria }}</span>
              <span class="text-2xl transition-transform duration-300" :class="{ 'rotate-180': isCategoriaAbierta(categoria) }">
                ▼
              </span>
            </button>
            
            <!-- Contenido de la categoría (colapsable) -->
            <div 
              v-if="isCategoriaAbierta(categoria)"
              class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4 animate-in slide-in-from-top duration-300"
            >
              <button
                v-for="platillo in platillosPorCategoria[categoria]"
                :key="platillo.id"
                @click="abrirEspecificaciones(platillo)"
                :class="[
                  'relative bg-white border-2 rounded-xl p-4 text-left hover:shadow-lg hover:border-[#FDB700] hover:scale-105 group transition-all active:scale-95',
                  platilloEnCarrito(platillo.id) 
                    ? 'border-[#FDB700] shadow-lg bg-yellow-50' 
                    : 'border-gray-200'
                ]"
              >
                <!-- Badge de cantidad -->
                <div 
                  v-if="platilloEnCarrito(platillo.id)"
                  class="absolute -top-2 -right-2 bg-[#FDB700] text-[#00126D] text-xs font-bold rounded-full w-6 h-6 flex items-center justify-center shadow-md"
                >
                  {{ getCantidadEnCarrito(platillo.id) }}
                </div>
                
                <div class="text-sm font-semibold text-[#FDB700] mb-1">$ {{ Number(platillo.precio).toFixed(2) }}</div>
                <div class="font-bold text-[#00126D] group-hover:text-[#3AAD08] text-sm">{{ platillo.kds_name || platillo.nombre }}</div>
                <div class="text-xs text-gray-600 line-clamp-2 mt-1">{{ platillo.descripcion }}</div>
              </button>
            </div>
          </div>
        </div>
      </section>

        <!-- Carrito Desktop -->
        <aside class="hidden lg:block bg-gradient-to-b from-white to-blue-50 border-2 border-gray-200 rounded-2xl p-6 flex flex-col gap-5 h-screen sticky top-0 shadow-xl">
        <div class="text-center border-b pb-4">
          <h2 class="text-lg font-bold text-[#00126D] flex items-center justify-center gap-2">
            <span v-if="tipoOrden === 'aqui'">🪑 Mesa {{ mesa }}</span>
            <span v-else-if="tipoOrden === 'llevar'">📦 {{ nombreCliente }}</span>
            <span v-else-if="tipoOrden === 'uber_eats'">🚗 {{ nombreCliente }}</span>
          </h2>
        </div>

        <!-- Items del carrito -->
        <div class="flex-1 flex flex-col">
          <div class="text-xs font-semibold text-gray-600 mb-3">🛒 CARRITO ({{ carrito.length }} items)</div>
          <div class="space-y-2 flex-1 overflow-auto">
            <div v-if="carrito.length === 0" class="text-sm text-gray-500 text-center py-4">Sin artículos</div>
            <div v-for="(item, index) in carrito" :key="index" class="bg-white border-2 border-gray-100 rounded-lg p-3 hover:shadow-md transition">
              <div class="flex items-center justify-between mb-2">
                <div class="flex-1">
                  <div class="font-bold text-[#00126D] text-sm">{{ item.platillo.kds_name || item.platillo.nombre }}</div>
                  <div class="text-xs text-[#FDB700] font-semibold">$ {{ Number(item.platillo.precio).toFixed(2) }}</div>
                </div>
                <div class="flex items-center gap-3">
                  <!-- Controles de cantidad -->
                  <div class="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
                    <button class="px-2 py-1 rounded bg-white hover:bg-gray-200 transition font-bold text-sm" @click="ajustarCantidad(index, -1)">−</button>
                    <div class="w-6 text-center font-bold text-sm">{{ item.cantidad }}</div>
                    <button class="px-2 py-1 rounded bg-white hover:bg-gray-200 transition font-bold text-sm" @click="ajustarCantidad(index, 1)">+</button>
                  </div>
                  <!-- Botón eliminar separado -->
                  <button class="px-2 py-1 rounded bg-red-100 hover:bg-red-200 transition text-red-600 font-bold text-sm border border-red-200" @click="eliminarDelCarrito(index)">🗑️</button>
                </div>
              </div>
              <input v-model="item.modificaciones" placeholder="Notas (opcional)" class="w-full border border-gray-200 rounded-lg px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-[#FDB700]" />
            </div>
          </div>
        </div>

        <!-- Total y Acciones -->
        <div class="space-y-3">
          <!-- Botón cancelar (separado del total) -->
          <button 
            @click="cancelarPedidoDesktop" 
            class="w-full py-2 text-red-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-all text-sm font-medium"
          >
            🗑️ Cancelar Pedido
          </button>
          
          <!-- Total -->
          <div class="bg-gradient-to-r from-[#00126D] to-[#001a4d] rounded-xl p-4 text-white">
            <div class="flex items-center justify-between mb-3">
              <span class="font-bold text-lg">💰 TOTAL</span>
              <span class="text-2xl font-black">$ {{ totalCarrito.toFixed(2) }}</span>
            </div>
            <div class="text-xs text-blue-200 mb-3 text-center">
              💳 Pago se procesará en caja
            </div>
            <button 
              @click="enviarPedido" 
              :disabled="loading || carrito.length === 0" 
              class="w-full py-3 rounded-lg text-[#00126D] bg-[#FDB700] hover:bg-yellow-400 disabled:opacity-50 disabled:cursor-not-allowed font-bold text-lg transition-all shadow-lg hover:shadow-xl active:scale-95"
            >
              {{ loading ? '⏳ Procesando...' : (modoAgregarArticulos ? `➕ Agregar a Mesa ${mesa}` : '🍳 Enviar a Cocina') }}
            </button>
          </div>
        </div>
        </aside>
      </div>
    </main>

    <!-- Botón flotante móvil -->
    <button
      v-if="isMobile"
      @click="toggleMobileCart"
      class="fixed bottom-6 right-6 w-20 h-20 bg-[#00126D] text-white rounded-full shadow-lg flex items-center justify-center z-40 hover:scale-110 transition-all"
    >
      <div class="text-center">
        <div class="text-xl">🛒</div>
        <div v-if="carrito.length > 0" class="absolute -top-2 -right-2 bg-[#FDB700] text-black text-xs font-bold rounded-full w-6 h-6 flex items-center justify-center">
          {{ carrito.length }}
        </div>
      </div>
    </button>

    <!-- Carrito Móvil (Full Screen) -->
    <div
      v-if="isMobile && showMobileCart"
      class="fixed inset-0 z-50"
    >
      <!-- Backdrop -->
      <div class="absolute inset-0 bg-black bg-opacity-50"></div>
      
      <!-- Carrito Panel -->
      <div class="carrito-mobile relative w-full h-full bg-white transform transition-transform duration-300 ease-out translate-y-0">
        <!-- Header del carrito móvil -->
        <div class="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 class="text-lg font-bold text-[#00126D] flex items-center gap-2">
            <span v-if="tipoOrden === 'aqui'">🪑 Mesa {{ mesa }}</span>
            <span v-else-if="tipoOrden === 'llevar'">📦 {{ nombreCliente }}</span>
            <span v-else-if="tipoOrden === 'uber_eats'">🚗 {{ nombreCliente }}</span>
          </h2>
          <button @click="closeMobileCart" class="text-gray-400 hover:text-gray-600 text-xl">
            ←
          </button>
        </div>

        <!-- Contenido del carrito móvil - ESTRUCTURA FIJA -->
        <div class="flex flex-col h-[calc(100vh-80px)]">
          <!-- Items del carrito - ÁREA SCROLLEABLE -->
          <div class="flex-1 p-6 pb-0 min-h-0">
            <div class="text-xs font-semibold text-gray-600 mb-3">🛒 CARRITO ({{ carrito.length }} items)</div>
            <div class="h-full overflow-y-auto space-y-2 pb-4">
              <div v-if="carrito.length === 0" class="text-sm text-gray-500 text-center py-8">Sin artículos</div>
              <div v-for="(item, index) in carrito" :key="index" class="bg-gray-50 border-2 border-gray-100 rounded-lg p-3 hover:shadow-md transition">
                <div class="flex items-center justify-between mb-2">
                  <div class="flex-1">
                    <div class="font-bold text-[#00126D] text-sm">{{ item.platillo.kds_name || item.platillo.nombre }}</div>
                    <div class="text-xs text-[#FDB700] font-semibold">$ {{ Number(item.platillo.precio).toFixed(2) }}</div>
                  </div>
                  <div class="flex items-center gap-3">
                    <!-- Controles de cantidad -->
                    <div class="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
                      <button class="px-2 py-1 rounded bg-white hover:bg-gray-200 transition font-bold text-sm" @click="ajustarCantidad(index, -1)">−</button>
                      <div class="w-6 text-center font-bold text-sm">{{ item.cantidad }}</div>
                      <button class="px-2 py-1 rounded bg-white hover:bg-gray-200 transition font-bold text-sm" @click="ajustarCantidad(index, 1)">+</button>
                    </div>
                    <!-- Botón eliminar separado -->
                    <button class="px-2 py-1 rounded bg-red-100 hover:bg-red-200 transition text-red-600 font-bold text-sm border border-red-200" @click="eliminarDelCarrito(index)">🗑️</button>
                  </div>
                </div>
                <input v-model="item.modificaciones" placeholder="Notas (opcional)" class="w-full border border-gray-200 rounded-lg px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-[#FDB700]" />
              </div>
            </div>
          </div>
          
          <!-- Total y botones - ANCLADO EN LA PARTE INFERIOR -->
          <div class="flex-shrink-0 border-t bg-white p-6 space-y-3 shadow-lg">
            <!-- Botón cancelar móvil -->
            <button 
              @click="cancelarPedidoMovil" 
              class="w-full py-2 text-red-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-all text-sm font-medium"
            >
              🗑️ Cancelar Pedido
            </button>
            
            <!-- Total -->
            <div class="bg-gradient-to-r from-[#00126D] to-[#001a4d] rounded-xl p-4 text-white">
              <div class="flex items-center justify-between mb-3">
                <span class="font-bold text-lg">💰 TOTAL</span>
                <span class="text-2xl font-black">$ {{ totalCarrito.toFixed(2) }}</span>
              </div>
              <div class="text-xs text-blue-200 mb-3 text-center">
                💳 Pago se procesará en caja
              </div>
              <button 
                @click="enviarPedido" 
                :disabled="loading || carrito.length === 0" 
                class="w-full py-3 rounded-lg text-[#00126D] bg-[#FDB700] hover:bg-yellow-400 disabled:opacity-50 disabled:cursor-not-allowed font-bold text-lg transition-all shadow-lg hover:shadow-xl active:scale-95"
              >
                {{ loading ? '⏳ Procesando...' : (modoAgregarArticulos ? `➕ Agregar a Mesa ${mesa}` : '🍳 Enviar a Cocina') }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal Inicial - Tipo de Orden -->
    <div
      v-if="showTipoOrdenModal"
      class="fixed inset-0 z-50 flex items-center justify-center"
    >
      <!-- Backdrop -->
      <div class="absolute inset-0 bg-black bg-opacity-75"></div>
      
      <!-- Modal Content -->
      <div class="relative bg-white rounded-2xl p-8 max-w-md w-full mx-4 shadow-2xl">
        <!-- Header -->
        <div class="text-center mb-8">
          <div class="text-6xl mb-4">🍽️</div>
          <h3 class="text-2xl font-bold text-[#00126D] mb-2">Nuevo Pedido</h3>
          <p class="text-gray-600">Selecciona el tipo de orden</p>
        </div>
        
        <!-- Opciones de tipo de orden -->
        <div class="space-y-4">
          <button
            @click="mostrarPedidosActuales"
            class="w-full p-6 bg-white border-2 border-purple-200 rounded-xl hover:border-purple-500 hover:bg-purple-50 transition-all group text-left"
          >
            <div class="flex items-center gap-4">
              <div class="text-4xl">📋</div>
              <div>
                <div class="text-lg font-bold text-[#00126D] group-hover:text-purple-600">Pedidos Actuales</div>
                <div class="text-sm text-gray-600">Ver y modificar pedidos en progreso</div>
              </div>
            </div>
          </button>
          
          <button
            @click="configurarTipoOrden('aqui')"
            class="w-full p-6 bg-white border-2 border-gray-200 rounded-xl hover:border-[#FDB700] hover:bg-yellow-50 transition-all group text-left"
          >
            <div class="flex items-center gap-4">
              <div class="text-4xl">🪑</div>
              <div>
                <div class="text-lg font-bold text-[#00126D] group-hover:text-[#FDB700]">Para aquí</div>
                <div class="text-sm text-gray-600">Consumo en el restaurante</div>
              </div>
            </div>
          </button>
          
          <button
            @click="configurarTipoOrden('llevar')"
            class="w-full p-6 bg-white border-2 border-gray-200 rounded-xl hover:border-[#FDB700] hover:bg-yellow-50 transition-all group text-left"
          >
            <div class="flex items-center gap-4">
              <div class="text-4xl">📦</div>
              <div>
                <div class="text-lg font-bold text-[#00126D] group-hover:text-[#FDB700]">Para llevar</div>
                <div class="text-sm text-gray-600">Cliente recoge su orden</div>
              </div>
            </div>
          </button>
          
          <button
            @click="configurarTipoOrden('uber_eats')"
            class="w-full p-6 bg-white border-2 border-gray-200 rounded-xl hover:border-[#FDB700] hover:bg-yellow-50 transition-all group text-left"
          >
            <div class="flex items-center gap-4">
              <div class="text-4xl">🚗</div>
              <div>
                <div class="text-lg font-bold text-[#00126D] group-hover:text-[#FDB700]">Uber Eats</div>
                <div class="text-sm text-gray-600">Entrega a domicilio</div>
              </div>
            </div>
          </button>
        </div>
      </div>
    </div>

    <!-- Modal de Nombre de Cliente -->
    <div
      v-if="showNombreClienteModal"
      class="fixed inset-0 z-50 flex items-center justify-center"
    >
      <!-- Backdrop -->
      <div class="absolute inset-0 bg-black bg-opacity-75"></div>
      
      <!-- Modal Content -->
      <div class="relative bg-white rounded-2xl p-8 max-w-md w-full mx-4 shadow-2xl">
        <!-- Header -->
        <div class="text-center mb-8">
          <div class="text-6xl mb-4">{{ tipoOrden === 'uber_eats' ? '🚗' : '📦' }}</div>
          <h3 class="text-2xl font-bold text-[#00126D] mb-2">
            {{ tipoOrden === 'uber_eats' ? 'Pedido Uber Eats' : 'Pedido Para Llevar' }}
          </h3>
          <p class="text-gray-600">Ingresa el nombre del cliente</p>
        </div>
        
        <!-- Campo de nombre -->
        <div class="mb-6">
          <label class="block text-sm font-bold text-[#00126D] mb-3">
            👤 Nombre del Cliente
          </label>
          <input
            v-model="nombreCliente"
            type="text"
            placeholder="Nombre completo del cliente"
            class="w-full p-4 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-[#FDB700] focus:border-[#FDB700] transition bg-white text-lg"
            @keyup.enter="confirmarNombreCliente"
            autofocus
          />
        </div>
        
        <!-- Botones -->
        <div class="flex gap-3">
          <button
            @click="cerrarNombreClienteModal"
            class="flex-1 px-4 py-3 bg-gray-100 hover:bg-gray-200 text-[#00126D] rounded-lg transition-all"
          >
            ← Atrás
          </button>
          <button
            @click="confirmarNombreCliente"
            :disabled="!nombreCliente.trim()"
            class="flex-1 px-4 py-3 bg-[#FDB700] hover:bg-yellow-400 disabled:opacity-50 disabled:cursor-not-allowed text-[#00126D] font-bold rounded-lg transition-all"
          >
            Continuar →
          </button>
        </div>
      </div>
    </div>

    <!-- Modal de Pedidos Actuales -->
    <div
      v-if="showPedidosActualesModal"
      class="fixed inset-0 z-50 flex items-center justify-center"
    >
      <!-- Backdrop -->
      <div class="absolute inset-0 bg-black bg-opacity-75"></div>
      
      <!-- Modal Content -->
      <div class="relative bg-white rounded-2xl p-6 max-w-4xl w-full mx-4 shadow-2xl max-h-[90vh] overflow-y-auto">
        <!-- Header -->
        <div class="text-center mb-6">
          <div class="text-4xl mb-2">📋</div>
          <h3 class="text-2xl font-bold text-[#00126D] mb-2">Pedidos Actuales</h3>
          <p class="text-gray-600">Ver y modificar pedidos en progreso</p>
          <div class="mt-2 flex justify-center items-center gap-2">
            <div class="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            <span class="text-xs text-green-600 font-medium">Actualizándose en tiempo real</span>
          </div>
        </div>

        <!-- Contenido -->
        <div class="space-y-6">
          <!-- Para Aquí -->
          <div v-if="pedidosParaAqui.length > 0">
            <h4 class="text-lg font-bold text-[#00126D] mb-4 flex items-center gap-2">
              🪑 Para Aquí
            </h4>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div
                v-for="pedido in pedidosParaAqui"
                :key="pedido.id"
                class="bg-white border-2 border-gray-200 rounded-xl p-4 hover:border-[#FDB700] transition-all cursor-pointer"
                @click="verPedidoDesdeActuales(pedido)"
              >
                <div class="flex justify-between items-start mb-2">
                  <div>
                    <div class="text-lg font-bold text-[#00126D]">Mesa {{ pedido.mesa }}</div>
                    <div class="text-sm text-gray-600">#{{ pedido.numero_display }}</div>
                  </div>
                  <span :class="getEstadoColor(pedido.estado)" class="px-2 py-1 rounded-lg text-xs font-medium">
                    {{ pedido.estado }}
                  </span>
                </div>
                <div class="text-sm text-gray-600 mb-2">
                  Total: ${{ Number(pedido.total).toFixed(2) }}
                </div>
                <div class="text-xs text-gray-500">
                  {{ new Date(pedido.fecha_creacion).toLocaleTimeString() }}
                </div>
              </div>
            </div>
          </div>

          <!-- Para Llevar/Uber Eats -->
          <div v-if="pedidosParaLlevar.length > 0">
            <h4 class="text-lg font-bold text-[#00126D] mb-4 flex items-center gap-2">
              📦 Para Llevar / 🚗 Uber Eats
            </h4>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div
                v-for="pedido in pedidosParaLlevar"
                :key="pedido.id"
                class="bg-white border-2 border-gray-200 rounded-xl p-4 hover:border-[#FDB700] transition-all cursor-pointer"
                @click="verPedidoDesdeActuales(pedido)"
              >
                <div class="flex justify-between items-start mb-2">
                  <div>
                    <div class="text-lg font-bold text-[#00126D]">{{ pedido.nombre_cliente }}</div>
                    <div class="text-sm text-gray-600">
                      {{ pedido.tipo_orden === 'uber_eats' ? '🚗 Uber Eats' : '📦 Para llevar' }} 
                      #{{ pedido.numero_display }}
                    </div>
                  </div>
                  <span :class="getEstadoColor(pedido.estado)" class="px-2 py-1 rounded-lg text-xs font-medium">
                    {{ pedido.estado }}
                  </span>
                </div>
                <div class="text-sm text-gray-600 mb-2">
                  Total: ${{ Number(pedido.total).toFixed(2) }}
                </div>
                <div class="text-xs text-gray-500">
                  {{ new Date(pedido.fecha_creacion).toLocaleTimeString() }}
                </div>
              </div>
            </div>
          </div>

          <!-- Sin pedidos -->
          <div v-if="pedidosParaAqui.length === 0 && pedidosParaLlevar.length === 0" class="text-center py-8">
            <div class="text-4xl mb-4">🎉</div>
            <p class="text-gray-600">No hay pedidos en progreso</p>
          </div>
        </div>

        <!-- Botones -->
        <div class="mt-6">
          <button
            @click="cerrarPedidosActualesModal"
            class="w-full py-3 bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold rounded-lg transition-all"
          >
            ← Cerrar
          </button>
        </div>
      </div>
    </div>

    <!-- Modal de Selección de Mesas -->
    <div
      v-if="showMesaModal"
      class="fixed inset-0 z-50 flex items-center justify-center"
      @click.self="closeMesaModal"
    >
      <!-- Backdrop -->
      <div class="absolute inset-0 bg-black bg-opacity-50"></div>
      
      <!-- Modal Content -->
      <div class="relative bg-white rounded-2xl p-6 max-w-sm w-full mx-4 shadow-2xl">
        <!-- Header -->
        <div class="flex items-center justify-between mb-6">
          <h3 class="text-xl font-bold text-[#00126D] flex items-center gap-2">
            🪑 Selecciona Mesa
          </h3>
          <button @click="closeMesaModal" class="text-gray-400 hover:text-gray-600 text-xl">
            ←
          </button>
        </div>
        
        <!-- Layout de Mesas -->
        <div class="mb-6">
          
          <div class="grid grid-cols-3 gap-3">
            <div v-for="(fila, index) in mesasLayout" :key="index" class="contents">
              <button
                v-for="numeroMesa in fila"
                :key="numeroMesa"
                @click="seleccionarMesa(numeroMesa)"
                :class="[
                  'aspect-square rounded-lg border-2 font-bold text-lg transition-all relative',
                  mesasOcupadasReactivo.has(numeroMesa)
                    ? 'bg-red-100 border-red-300 text-red-600 hover:bg-red-200 cursor-pointer'
                    : 'bg-white border-gray-200 text-[#00126D] hover:border-[#FDB700] hover:bg-yellow-50'
                ]"
              >
                {{ numeroMesa }}
                <span v-if="mesasOcupadasReactivo.has(numeroMesa)" class="absolute top-0 right-0 text-xs">🔴</span>
              </button>
            </div>
          </div>
          
          <!-- Leyenda -->
          <div class="mt-4 flex justify-center gap-4 text-xs">
            <div class="flex items-center gap-1">
              <div class="w-3 h-3 bg-white border border-gray-200 rounded"></div>
              <span class="text-gray-600">Disponible</span>
            </div>
            <div class="flex items-center gap-1">
              <div class="w-3 h-3 bg-red-100 border border-red-300 rounded"></div>
              <span class="text-gray-600">Ocupada</span>
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

    <!-- Modal Ver Pedido Actual -->
    <div
      v-if="showVerPedidoModal"
      class="fixed inset-0 z-50 flex items-center justify-center"
      @click.self="cerrarVerPedidoModal"
    >
      <!-- Backdrop -->
      <div class="absolute inset-0 bg-black bg-opacity-75"></div>
      
      <!-- Modal Content -->
      <div class="relative bg-white rounded-2xl p-6 max-w-lg w-full mx-4 shadow-2xl max-h-[80vh] overflow-hidden flex flex-col">
        <!-- Header -->
        <div class="flex items-center justify-between mb-6">
          <div>
            <h3 class="text-xl font-bold text-[#00126D]">Mesa {{ mesa }}</h3>
            <p class="text-sm text-gray-600">
              Pedido #{{ pedidoActual?.numero_display }} - 
              <span :class="pedidoActual?.estado === 'pendiente' ? 'text-orange-600' : 'text-blue-600'">
                {{ pedidoActual?.estado.toUpperCase() }}
              </span>
            </p>
          </div>
          <button @click="cerrarVerPedidoModal" class="text-gray-400 hover:text-gray-600 text-xl">
            ←
          </button>
        </div>
        
        <!-- Lista de artículos - scrolleable -->
        <div class="flex-1 overflow-y-auto mb-6">
          <div v-if="articulosEditables.length === 0" class="text-center py-8 text-gray-500">
            Sin artículos
          </div>
          <div v-else class="space-y-3">
            <div 
              v-for="(articulo, index) in articulosEditables" 
              :key="articulo.id"
              v-show="!articulo.eliminado"
              class="bg-gray-50 rounded-lg p-4 border border-gray-200"
            >
              <div class="flex items-center justify-between mb-2">
                <div class="flex-1">
                  <div class="font-bold text-[#00126D]">
                    {{ articulo.platillo?.kds_name || articulo.platillo?.nombre }}
                  </div>
                  <div class="text-sm text-[#FDB700] font-semibold">
                    $ {{ Number(articulo.platillo?.precio).toFixed(2) }}
                  </div>
                </div>
                
                <!-- Controles de cantidad -->
                <div v-if="esPedidoPendiente" class="flex items-center gap-2">
                  <div class="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
                    <button 
                      @click="ajustarCantidadPedido(index, -1)"
                      class="px-2 py-1 rounded bg-white hover:bg-gray-200 transition font-bold text-sm"
                      :disabled="articulo.cantidad <= 0"
                    >
                      −
                    </button>
                    <div class="w-8 text-center font-bold text-sm">{{ articulo.cantidad }}</div>
                    <button 
                      @click="ajustarCantidadPedido(index, 1)"
                      class="px-2 py-1 rounded bg-white hover:bg-gray-200 transition font-bold text-sm"
                    >
                      +
                    </button>
                  </div>
                  <button 
                    @click="eliminarArticuloPedido(index)"
                    class="px-2 py-1 rounded bg-red-100 hover:bg-red-200 transition text-red-600 font-bold text-sm border border-red-200"
                    :disabled="articulo.cantidad === 0"
                  >
                    🗑️
                  </button>
                </div>
                
                <!-- Estado + acciones (cuando no es editable) -->
                <div v-else class="text-right">
                  <div class="text-xs font-bold" :class="getArticuloEstadoClass(articulo.estado_item)">
                    {{ getArticuloEstadoLabel(articulo.estado_item) }}
                  </div>
                  <button
                    v-if="esBebida(articulo) && articulo.estado_item !== 'entregado' && (auth.user?.rol === 'mesero' || auth.user?.rol === 'administrador')"
                    @click="marcarBebidaEntregada(articulo.id)"
                    class="mt-2 px-2 py-1 rounded-md bg-blue-100 hover:bg-blue-200 text-blue-800 text-[11px] font-bold border border-blue-200"
                  >
                    Marcar entregada
                  </button>

                  <div class="text-lg font-bold text-gray-700 mt-2">
                    {{ articulo.cantidad }}x
                  </div>
                </div>
              </div>
              
              <!-- Modificaciones -->
              <div v-if="esPedidoPendiente" class="mt-2">
                <textarea
                  v-model="articulo.modificaciones"
                  placeholder="Modificaciones (ej: Sin crema, extra lechuga...)"
                  class="w-full p-2 border border-gray-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-[#FDB700] focus:border-[#FDB700] resize-none"
                  rows="2"
                ></textarea>
              </div>
              <div v-else-if="articulo.modificaciones" class="text-xs text-gray-600 bg-yellow-50 p-2 rounded border-l-4 border-yellow-400 mt-2">
                {{ articulo.modificaciones }}
              </div>
              
              <!-- Indicador de cambio -->
              <div v-if="esPedidoPendiente && (articulo.cantidad !== articulo.cantidad_original || (articulo.modificaciones || '') !== (articulo.modificaciones_original || ''))" class="text-xs mt-2 space-y-1">
                <span v-if="articulo.cantidad === 0" class="text-red-600 font-bold block">
                  ❌ Se eliminará
                </span>
                <span v-else-if="articulo.cantidad !== articulo.cantidad_original" class="text-orange-600 font-bold block">
                  📝 Cantidad: {{ articulo.cantidad_original }}x → {{ articulo.cantidad }}x
                </span>
                <span v-if="(articulo.modificaciones || '') !== (articulo.modificaciones_original || '')" class="text-blue-600 font-bold block">
                  📝 Modificaciones actualizadas
                </span>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Total -->
        <div class="bg-gradient-to-r from-[#00126D] to-[#001a4d] rounded-xl p-4 text-white mb-4">
          <div class="flex items-center justify-between">
            <span class="font-bold">💰 TOTAL</span>
            <div class="text-right">
              <!-- Total dinámico si hay cambios pendientes -->
              <span v-if="esPedidoPendiente && hayCantidadesCambiadas" class="text-xl font-black">
                $ {{ totalDinamicoModal.toFixed(2) }}
              </span>
              <!-- Total original si no hay cambios o no es pendiente -->
              <span v-else class="text-xl font-black">
                $ {{ Number(pedidoActual?.total || 0).toFixed(2) }}
              </span>
              <!-- Indicador de total desactualizado -->
              <div v-if="totalDesactualizado" class="text-xs text-yellow-300 mt-1">
                Original: $ {{ Number(pedidoActual?.total || 0).toFixed(2) }}
              </div>
            </div>
          </div>
        </div>
        
        <!-- Botones -->
        <div class="space-y-3">
          <!-- Guardar cambios (solo si hay cambios y es pendiente) -->
          <button 
            v-if="esPedidoPendiente && hayCantidadesCambiadas"
            @click="guardarCambiosPedido"
            :disabled="loading"
            class="w-full py-3 bg-[#FDB700] hover:bg-yellow-400 disabled:opacity-50 disabled:cursor-not-allowed text-[#00126D] font-bold rounded-lg transition-all"
          >
            {{ loading ? '⏳ Guardando...' : '💾 Guardar Cambios' }}
          </button>
          
          <!-- Solicitar cuenta (solo si está entregado) -->
          <button
            v-if="pedidoActual?.estado === 'entregado'"
            @click="solicitarCuenta(pedidoActual)"
            class="w-full py-3 bg-purple-600 hover:bg-purple-700 text-white font-bold rounded-lg transition-all"
          >
            💳 Solicitar Cuenta
          </button>
          
          <!-- Agregar más artículos -->
          <button
            @click="irAAgregarMasArticulos"
            class="w-full py-3 bg-green-100 hover:bg-green-200 text-green-700 font-bold rounded-lg transition-all border border-green-300"
          >
            ➕ Agregar Más Artículos
          </button>
          
          <!-- Cerrar -->
          <button
            @click="cerrarVerPedidoModal"
            class="w-full py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-all"
          >
            ← Cerrar
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
      v-if="selectedPozoleColor"
      :color="selectedPozoleColor"
      :platillos="pozolesByColor[selectedPozoleColor]"
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

.animate-in {
  animation: slideInFromTop 0.3s ease-out;
}

.fade-in {
  animation: fadeIn 0.3s ease-out;
}

.slide-in-from-top {
  animation: slideDown 0.4s ease-out;
}

.slide-in-from-top-5 {
  animation: slideInFromTop 0.3s ease-out;
}

/* Transiciones suaves para los iconos */
.rotate-180 {
  transform: rotate(180deg);
}

/* Hover effects mejorados */
.group:hover .text-2xl {
  transform: scale(1.1);
}

/* Animación de entrada para categorías */
.duration-300 {
  transition-duration: 300ms;
}
</style>