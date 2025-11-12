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
const tipoOrden = ref<'aqui' | 'llevar'>('aqui')
const showPozoleModal = ref(false)
const selectedPozoleColor = ref<'Verde' | 'Blanco' | 'Rojo' | null>(null)

// Control del carrito móvil
const showMobileCart = ref(false)
const isMobile = ref(false)

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
    await loadPlatillos()
    
    // Inicializar WebSocket para mesero
    const wsConnected = await pedidosStore.initWebSocket('mesero')
    
    if (wsConnected) {
      console.log('✅ Mesero View: WebSocket conectado, notificaciones en tiempo real activas')
    } else {
      console.warn('⚠️ Mesero View: WebSocket falló, continuando sin notificaciones en tiempo real')
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
  showMobileCart.value = false
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

// Agregar producto al carrito (para platillos normales)
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
  agregarAlCarrito(platillo)
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

  if (tipoOrden.value === 'llevar' && !nombreCliente.value.trim()) {
    error.value = 'Ingresa el nombre del cliente para llevar'
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
      nombre_cliente: tipoOrden.value === 'llevar' ? nombreCliente.value : null,
      mesa: tipoOrden.value === 'aqui' ? mesa.value : null,
      tipo_orden: tipoOrden.value,
      articulos
    }

    const nuevoPedido = await pedidosStore.createPedido(pedidoData)
    
    if (nuevoPedido) {
      // Limpiar formulario
      carrito.value = []
      nombreCliente.value = ''
      mesa.value = ''
      
      const mensajeExito = tipoOrden.value === 'aqui' 
        ? `Pedido #${nuevoPedido.numero_display} enviado a cocina para Mesa ${mesa.value}` 
        : `Pedido #${nuevoPedido.numero_display} para llevar enviado a cocina (${nombreCliente.value})`
      
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

// Limpiar carrito
const limpiarCarrito = () => {
  carrito.value = []
  nombreCliente.value = ''
  mesa.value = ''
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
        <div v-if="loading" class="p-4 text-center text-gray-600 font-medium">Cargando platillos...</div>

        <div v-else>
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
            <div class="text-xl font-bold mb-4 px-4 py-2 rounded-lg border-2 text-white bg-gradient-to-r from-[#00126D] to-[#001a4d]">
              {{ categoria }}
            </div>
            <div class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
              <button
                v-for="platillo in platillosPorCategoria[categoria]"
                :key="platillo.id"
                @click="agregarAlCarrito(platillo)"
                class="bg-white border-2 border-gray-200 rounded-xl p-4 text-left hover:shadow-lg hover:border-[#FDB700] hover:scale-105 group transition-all active:scale-95"
              >
                <div class="text-sm font-semibold text-[#FDB700] mb-1">$ {{ Number(platillo.precio).toFixed(2) }}</div>
                <div class="font-bold text-[#00126D] group-hover:text-[#3AAD08] text-sm">{{ platillo.kds_name || platillo.nombre }}</div>
                <div class="text-xs text-gray-600 line-clamp-2 mt-1">{{ platillo.descripcion }}</div>
              </button>
            </div>
          </div>
        </div>
      </section>

        <!-- Carrito Desktop -->
        <aside class="hidden lg:block bg-gradient-to-b from-white to-blue-50 border-2 border-gray-200 rounded-2xl p-6 flex flex-col gap-5 h-fit sticky top-6 shadow-xl">
        <div class="text-center border-b pb-4">
          <h2 class="text-xl font-bold text-[#00126D] flex items-center justify-center gap-2">
            🍽️ Pedido Mesa
          </h2>
        </div>
        
        <!-- Tipo de orden -->
        <div class="mb-4">
          <label class="block text-sm font-bold text-[#00126D] mb-2">📦 Tipo de orden</label>
          <div class="grid grid-cols-2 gap-2">
            <button 
              :class="['px-3 py-3 rounded-xl border-2 text-sm font-semibold transition-all', 
                       tipoOrden === 'aqui' ? 'bg-[#00126D] text-white border-[#00126D] shadow-md' : 'bg-white border-gray-200 text-[#00126D] hover:border-[#00126D]']" 
              @click="setTipoOrden('aqui')"
            >
              🪑 Aquí
            </button>
            <button 
              :class="['px-3 py-3 rounded-xl border-2 text-sm font-semibold transition-all', 
                       tipoOrden === 'llevar' ? 'bg-[#00126D] text-white border-[#00126D] shadow-md' : 'bg-white border-gray-200 text-[#00126D] hover:border-[#00126D]']" 
              @click="setTipoOrden('llevar')"
            >
              📦 Llevar
            </button>
          </div>
        </div>

        <!-- Campos dinámicos según tipo de orden -->
        <div class="grid grid-cols-1 gap-4">
          <!-- Mesa (solo para "aquí") -->
          <div v-if="tipoOrden === 'aqui'">
            <label class="block text-sm font-bold text-[#00126D] mb-2">🪑 Mesa</label>
            <select 
              v-model="mesa" 
              class="w-full p-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-[#FDB700] focus:border-[#FDB700] transition bg-white"
              required
            >
              <option value="">Selecciona mesa</option>
              <option v-for="mesaNum in mesasDisponibles" :key="mesaNum" :value="mesaNum">
                Mesa {{ mesaNum }}
              </option>
            </select>
          </div>
          
          <!-- Nombre cliente (solo para "llevar") -->
          <div v-if="tipoOrden === 'llevar'">
            <label class="block text-sm font-bold text-[#00126D] mb-2">👤 Nombre Cliente <span class="text-red-500">*</span></label>
            <input
              v-model="nombreCliente"
              type="text"
              class="w-full p-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-[#FDB700] focus:border-[#FDB700] transition bg-white"
              placeholder="Nombre del cliente"
              required
            />
          </div>
        </div>

        <!-- Items del carrito -->
        <div class="border-t-2 border-gray-100 pt-4">
          <div class="text-xs font-semibold text-gray-600 mb-2">🛒 CARRITO ({{ carrito.length }} items)</div>
          <div class="space-y-2 max-h-[35vh] overflow-auto">
            <div v-if="carrito.length === 0" class="text-sm text-gray-500 text-center py-4">Sin artículos</div>
            <div v-for="(item, index) in carrito" :key="index" class="bg-white border-2 border-gray-100 rounded-lg p-3 hover:shadow-md transition">
              <div class="flex items-center justify-between mb-2">
                <div>
                  <div class="font-bold text-[#00126D] text-sm">{{ item.platillo.kds_name || item.platillo.nombre }}</div>
                  <div class="text-xs text-[#FDB700] font-semibold">$ {{ Number(item.platillo.precio).toFixed(2) }}</div>
                </div>
                <div class="flex items-center gap-1.5 bg-gray-100 rounded-lg p-1">
                  <button class="px-2 py-1 rounded bg-white hover:bg-gray-200 transition font-bold text-sm" @click="ajustarCantidad(index, -1)">−</button>
                  <div class="w-6 text-center font-bold text-sm">{{ item.cantidad }}</div>
                  <button class="px-2 py-1 rounded bg-white hover:bg-gray-200 transition font-bold text-sm" @click="ajustarCantidad(index, 1)">+</button>
                  <button class="px-2 py-1 rounded bg-red-100 hover:bg-red-200 transition text-red-600 font-bold text-sm" @click="eliminarDelCarrito(index)">✕</button>
                </div>
              </div>
              <input v-model="item.modificaciones" placeholder="Notas (opcional)" class="w-full border border-gray-200 rounded-lg px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-[#FDB700]" />
            </div>
          </div>
        </div>

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
            :disabled="loading || carrito.length === 0 || (tipoOrden === 'aqui' && !mesa) || (tipoOrden === 'llevar' && !nombreCliente.trim())" 
            class="w-full py-3 rounded-lg text-[#00126D] bg-[#FDB700] hover:bg-yellow-400 disabled:opacity-50 disabled:cursor-not-allowed font-bold text-lg transition-all shadow-lg hover:shadow-xl active:scale-95"
          >
            {{ loading ? '⏳ Enviando...' : '🍳 Enviar a Cocina' }}
          </button>
        </div>
        </aside>
      </div>
    </main>

    <!-- Botón flotante móvil -->
    <button
      v-if="isMobile"
      @click="toggleMobileCart"
      class="fixed bottom-6 right-6 w-16 h-16 bg-[#00126D] text-white rounded-full shadow-lg flex items-center justify-center z-40 hover:scale-110 transition-all"
    >
      <div class="text-center">
        <div class="text-xl">🛒</div>
        <div v-if="carrito.length > 0" class="absolute -top-2 -right-2 bg-[#FDB700] text-black text-xs font-bold rounded-full w-6 h-6 flex items-center justify-center">
          {{ carrito.length }}
        </div>
      </div>
    </button>

    <!-- Carrito Móvil (Bottom Sheet) -->
    <div
      v-if="isMobile && showMobileCart"
      class="fixed inset-0 z-50 flex items-end"
      @click.self="closeMobileCart"
    >
      <!-- Backdrop -->
      <div class="absolute inset-0 bg-black bg-opacity-50"></div>
      
      <!-- Carrito Panel -->
      <div class="relative w-full max-h-[85vh] bg-white rounded-t-3xl shadow-2xl">
        <!-- Header del carrito móvil -->
        <div class="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 class="text-xl font-bold text-[#00126D] flex items-center gap-2">
            🍽️ Pedido Mesa
          </h2>
          <button @click="closeMobileCart" class="text-gray-400 hover:text-gray-600 text-2xl">
            ×
          </button>
        </div>

        <!-- Contenido del carrito móvil (igual que desktop) -->
        <div class="p-6 overflow-y-auto max-h-[70vh] space-y-5">
          <!-- Tipo de orden -->
          <div class="mb-4">
            <label class="block text-sm font-bold text-[#00126D] mb-2">📦 Tipo de orden</label>
            <div class="grid grid-cols-2 gap-2">
              <button 
                :class="['px-3 py-3 rounded-xl border-2 text-sm font-semibold transition-all', 
                         tipoOrden === 'aqui' ? 'bg-[#00126D] text-white border-[#00126D] shadow-md' : 'bg-white border-gray-200 text-[#00126D] hover:border-[#00126D]']" 
                @click="setTipoOrden('aqui')"
              >
                🪑 Aquí
              </button>
              <button 
                :class="['px-3 py-3 rounded-xl border-2 text-sm font-semibold transition-all', 
                         tipoOrden === 'llevar' ? 'bg-[#00126D] text-white border-[#00126D] shadow-md' : 'bg-white border-gray-200 text-[#00126D] hover:border-[#00126D]']" 
                @click="setTipoOrden('llevar')"
              >
                📦 Llevar
              </button>
            </div>
          </div>

          <!-- Campos dinámicos según tipo de orden -->
          <div class="grid grid-cols-1 gap-4">
            <!-- Mesa (solo para "aquí") -->
            <div v-if="tipoOrden === 'aqui'">
              <label class="block text-sm font-bold text-[#00126D] mb-2">🪑 Mesa</label>
              <select 
                v-model="mesa" 
                class="w-full p-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-[#FDB700] focus:border-[#FDB700] transition bg-white"
                required
              >
                <option value="">Selecciona mesa</option>
                <option v-for="mesaNum in mesasDisponibles" :key="mesaNum" :value="mesaNum">
                  Mesa {{ mesaNum }}
                </option>
              </select>
            </div>
            
            <!-- Nombre cliente (solo para "llevar") -->
            <div v-if="tipoOrden === 'llevar'">
              <label class="block text-sm font-bold text-[#00126D] mb-2">👤 Nombre Cliente <span class="text-red-500">*</span></label>
              <input
                v-model="nombreCliente"
                type="text"
                class="w-full p-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-[#FDB700] focus:border-[#FDB700] transition bg-white"
                placeholder="Nombre del cliente"
                required
              />
            </div>
          </div>

          <!-- Items del carrito -->
          <div class="border-t-2 border-gray-100 pt-4">
            <div class="text-xs font-semibold text-gray-600 mb-2">🛒 CARRITO ({{ carrito.length }} items)</div>
            <div class="space-y-2 max-h-[25vh] overflow-auto">
              <div v-if="carrito.length === 0" class="text-sm text-gray-500 text-center py-4">Sin artículos</div>
              <div v-for="(item, index) in carrito" :key="index" class="bg-gray-50 border-2 border-gray-100 rounded-lg p-3 hover:shadow-md transition">
                <div class="flex items-center justify-between mb-2">
                  <div>
                    <div class="font-bold text-[#00126D] text-sm">{{ item.platillo.kds_name || item.platillo.nombre }}</div>
                    <div class="text-xs text-[#FDB700] font-semibold">$ {{ Number(item.platillo.precio).toFixed(2) }}</div>
                  </div>
                  <div class="flex items-center gap-1.5 bg-gray-100 rounded-lg p-1">
                    <button class="px-2 py-1 rounded bg-white hover:bg-gray-200 transition font-bold text-sm" @click="ajustarCantidad(index, -1)">−</button>
                    <div class="w-6 text-center font-bold text-sm">{{ item.cantidad }}</div>
                    <button class="px-2 py-1 rounded bg-white hover:bg-gray-200 transition font-bold text-sm" @click="ajustarCantidad(index, 1)">+</button>
                    <button class="px-2 py-1 rounded bg-red-100 hover:bg-red-200 transition text-red-600 font-bold text-sm" @click="eliminarDelCarrito(index)">✕</button>
                  </div>
                </div>
                <input v-model="item.modificaciones" placeholder="Notas (opcional)" class="w-full border border-gray-200 rounded-lg px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-[#FDB700]" />
              </div>
            </div>
          </div>

          <!-- Total y botones -->
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
              :disabled="loading || carrito.length === 0 || (tipoOrden === 'aqui' && !mesa) || (tipoOrden === 'llevar' && !nombreCliente.trim())" 
              class="w-full py-3 rounded-lg text-[#00126D] bg-[#FDB700] hover:bg-yellow-400 disabled:opacity-50 disabled:cursor-not-allowed font-bold text-lg transition-all shadow-lg hover:shadow-xl active:scale-95"
            >
              {{ loading ? '⏳ Enviando...' : '🍳 Enviar a Cocina' }}
            </button>
          </div>
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
</style>