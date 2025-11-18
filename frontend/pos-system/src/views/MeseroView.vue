<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
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

// Control del modal inicial de tipo de orden
const showTipoOrdenModal = ref(true)
const pedidoConfigurado = ref(false)

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


// Categorías únicas de platillos (excluyendo Pozoles)
const categorias = computed(() => {
  const cats = [...new Set(platillos.value
    .filter(p => p.categoria !== 'Pozole' && p.estado === 'disponible')
    .map(p => p.categoria))]
  return cats.sort()
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
    'Tostadas': ['Sin crema', 'Sin lechuga', 'Sin queso', 'Sin frijoles']
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

// Enviar pedido (sin pago - flujo mesero)
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

    const pedidoData: PedidoCreate = {
      nombre_cliente: (tipoOrden.value === 'llevar' || tipoOrden.value === 'uber_eats') ? nombreCliente.value : null,
      mesa: tipoOrden.value === 'aqui' ? mesa.value : null,
      tipo_orden: tipoOrden.value,
      articulos
    }

    const nuevoPedido = await pedidosStore.createPedido(pedidoData)
    
    if (nuevoPedido) {
      // Las mesas ocupadas se actualizan automáticamente via WebSocket y computed reactivo
      
      // Limpiar formulario y reiniciar flujo
      carrito.value = []
      nombreCliente.value = ''
      mesa.value = ''
      pedidoConfigurado.value = false
      showTipoOrdenModal.value = true
      showNombreClienteModal.value = false
      
      const mensajeExito = tipoOrden.value === 'aqui' 
        ? `Pedido #${nuevoPedido.numero_display} enviado a cocina para Mesa ${mesa.value}` 
        : `Pedido #${nuevoPedido.numero_display} ${tipoOrden.value === 'uber_eats' ? 'Uber Eats' : 'para llevar'} enviado a cocina (${nombreCliente.value})`
      
      showSuccessNotification(mensajeExito)
      
      // Cerrar carrito móvil si está abierto
      if (isMobile.value && showMobileCart.value) {
        closeMobileCart()
      }
    } else {
      showErrorNotification(pedidosStore.error || 'Error al crear pedido')
    }
    
  } catch (e: any) {
    showErrorNotification(e?.response?.data?.detail || 'Error al enviar pedido')
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
    showErrorNotification(`Mesa ${numeroMesa} está ocupada`)
    return
  }
  
  mesa.value = numeroMesa
  // Automáticamente continuar cuando se selecciona una mesa
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
              {{ loading ? '⏳ Enviando...' : '🍳 Enviar a Cocina' }}
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
                {{ loading ? '⏳ Enviando...' : '🍳 Enviar a Cocina' }}
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
                :disabled="mesasOcupadasReactivo.has(numeroMesa)"
                :class="[
                  'aspect-square rounded-lg border-2 font-bold text-lg transition-all relative',
                  mesasOcupadasReactivo.has(numeroMesa)
                    ? 'bg-red-100 border-red-300 text-red-400 cursor-not-allowed'
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