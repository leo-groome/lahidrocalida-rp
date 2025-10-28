<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useAuthStore } from '../stores/auth'
import { api } from '../api/client'
import type { Platillo, ArticuloPedidoCreate } from '../types'
import { useRouter } from 'vue-router'
import PozoleVariantModal from '../components/PozoleVariantModal.vue'

const auth = useAuthStore()
const router = useRouter()

const platillos = ref<Platillo[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const searchQuery = ref('')
const successMessage = ref<string | null>(null)
const showNotification = ref(false)

const metodoPago = ref<'efectivo' | 'tarjeta' | 'transferencia'>('efectivo')
const tipoOrden = ref<'aqui' | 'llevar' | 'uber_eats'>('aqui')
const ultimoNumeroDisplay = ref<string | null>(null)

interface CartItem {
  platillo: Platillo
  cantidad: number
  modificaciones: string
}
const cart = ref<CartItem[]>([])
const selectedPozoleColor = ref<'Verde' | 'Blanco' | 'Rojo' | null>(null)
const showPozoleModal = ref(false)

function addToCart(p: Platillo) {
  const existing = cart.value.find(ci => ci.platillo.id === p.id)
  if (existing) existing.cantidad += 1
  else cart.value.push({ platillo: p, cantidad: 1, modificaciones: '' })
}

function openPozoleVariants(color: 'Verde' | 'Blanco' | 'Rojo') {
  selectedPozoleColor.value = color
  showPozoleModal.value = true
}

function setTipoOrden(tipo: 'aqui' | 'llevar' | 'uber_eats') {
  tipoOrden.value = tipo
  if (tipo === 'uber_eats') {
    metodoPago.value = 'tarjeta'
  }
}

function closePozoleModal() {
  showPozoleModal.value = false
  selectedPozoleColor.value = null
}

function selectPozoleVariant(platillo: Platillo) {
  addToCart(platillo)
  closePozoleModal()
}

function decQty(pId: number) {
  const ci = cart.value.find(ci => ci.platillo.id === pId)
  if (!ci) return
  ci.cantidad -= 1
  if (ci.cantidad <= 0) {
    removeFromCart(pId)
  }
}

function incQty(pId: number) {
  const ci = cart.value.find(ci => ci.platillo.id === pId)
  if (!ci) return
  ci.cantidad += 1
}

function removeFromCart(pId: number) {
  cart.value = cart.value.filter(ci => ci.platillo.id !== pId)
}

const total = computed(() => {
  return cart.value.reduce((acc, ci) => {
    const price = Number(ci.platillo?.precio ?? 0)
    return acc + price * ci.cantidad
  }, 0)
})

const hasAnyPozole = computed(() => {
  return platillos.value.some(p => p.categoria === 'Pozole' && p.estado === 'disponible')
})

const filteredPlatillos = computed(() => {
  if (!searchQuery.value.trim()) return platillos.value
  const query = searchQuery.value.toLowerCase()
  return platillos.value.filter(p => 
    p.nombre.toLowerCase().includes(query) || 
    p.descripcion?.toLowerCase().includes(query)
  )
})

const categoryOrder = ['Flautas', 'Enchiladas Rojas', 'Sopes', 'Tacos', 'Tostadas', 'Tamales']

const groupedFiltered = computed(() => {
  const map: Record<string, Platillo[]> = {}
  for (const p of filteredPlatillos.value) {
    if (p.estado !== 'disponible') continue
    if (p.categoria === 'Pozole') continue
    if (!map[p.categoria]) map[p.categoria] = []
    const category = map[p.categoria]
    if (category) category.push(p)
  }
  // Ordenar categorías según categoryOrder
  const sorted: Record<string, Platillo[]> = {}
  for (const cat of categoryOrder) {
    if (map[cat]) sorted[cat] = map[cat]
  }
  // Agregar categorías no listadas al final
  for (const cat in map) {
    if (!sorted[cat] && map[cat]) sorted[cat] = map[cat]
  }
  return sorted
})

const getCategoryColor = (category: string) => {
  const colors: Record<string, string> = {
    'Flautas': 'from-yellow-50 to-yellow-100 border-yellow-300',
    'Tacos': 'from-orange-50 to-orange-100 border-orange-300',
    'Sopes': 'from-amber-50 to-amber-100 border-amber-300',
    'Tostadas': 'from-red-50 to-red-100 border-red-300',
    'Enchiladas Rojas': 'from-rose-50 to-rose-100 border-rose-300',
    'Tamales': 'from-green-50 to-green-100 border-green-300'
  }
  return colors[category] || 'from-gray-50 to-gray-100 border-gray-300'
}

const getCategoryTextColor = (category: string) => {
  const colors: Record<string, string> = {
    'Flautas': 'text-yellow-700',
    'Tacos': 'text-orange-700',
    'Sopes': 'text-amber-700',
    'Tostadas': 'text-red-700',
    'Enchiladas Rojas': 'text-rose-700',
    'Tamales': 'text-green-700'
  }
  return colors[category] || 'text-gray-700'
}

const pozolesByColorFiltered = computed(() => {
  const map: Record<'Verde' | 'Blanco' | 'Rojo', Platillo[]> = {
    'Verde': [],
    'Blanco': [],
    'Rojo': []
  }
  for (const p of filteredPlatillos.value) {
    if (p.categoria !== 'Pozole' || p.estado !== 'disponible') continue
    const parts = p.nombre.split(' ')
    const color = parts[2] as 'Verde' | 'Blanco' | 'Rojo'
    if (map[color]) {
      map[color].push(p)
    }
  }
  return map
})

async function loadPlatillos() {
  loading.value = true
  error.value = null
  try {
    const { data } = await api.get<Platillo[]>('/platillos')
    platillos.value = data
  } catch (e: any) {
    error.value = e?.response?.data?.detail || 'Error cargando platillos'
  } finally {
    loading.value = false
  }
}

async function enviarPedido() {
  if (cart.value.length === 0) {
    showErrorNotification('Agrega al menos un artículo')
    return
  }
  const articulos: ArticuloPedidoCreate[] = cart.value.map(ci => ({
    platillo_id: ci.platillo.id,
    cantidad: ci.cantidad,
    modificaciones: ci.modificaciones || undefined,
  }))
  try {
    loading.value = true
    error.value = null
    const response = await api.post<any>('/pedidos', {
      metodo_pago: metodoPago.value,
      tipo_orden: tipoOrden.value,
      articulos,
    })
    ultimoNumeroDisplay.value = response.data.numero_display
    // limpiar
    cart.value = []
    metodoPago.value = 'efectivo'
    tipoOrden.value = 'aqui'
    showSuccessNotification(`¡Pedido #${response.data.numero_display} creado!`)
  } catch (e: any) {
    showErrorNotification(e?.response?.data?.detail || 'Error creando pedido')
  } finally {
    loading.value = false
  }
}

function showErrorNotification(message: string) {
  error.value = message
  showNotification.value = true
  setTimeout(() => {
    showNotification.value = false
  }, 5000)
}

function showSuccessNotification(message: string) {
  successMessage.value = message
  showNotification.value = true
  setTimeout(() => {
    showNotification.value = false
  }, 3000)
}

function logout() {
  auth.logout()
  router.replace({ name: 'login' })
}

onMounted(async () => {
  if (!auth.isAuthenticated) {
    router.replace({ name: 'login' })
    return
  }
  await loadPlatillos()
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
          <h1 class="text-2xl font-bold text-white">Caja - POS</h1>
          <p class="text-xs text-blue-100">La Hidrocálida</p>
        </div>
      </div>
      <div class="flex items-center gap-4 text-sm">
        <div class="bg-white bg-opacity-10 px-4 py-2 rounded-lg backdrop-blur">
          <p class="text-[#00126D] text-xs">Usuario</p>
          <p class="text-blue-500 font-semibold">{{ auth.user?.nombre }}</p>
        </div>
        <button @click="logout" class="px-4 py-2 rounded-lg bg-white text-[#00126D] font-semibold hover:bg-blue-50 transition shadow-md hover:shadow-lg">Salir</button>
      </div>
    </header>

    <main class="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-6 p-6">
      <!-- Menu -->
      <section class="lg:col-span-2 space-y-6">
        <div v-if="loading" class="p-4 text-center text-gray-600 font-medium">Cargando platillos...</div>

        <!-- Search Bar -->
        <div class="relative">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Buscar platillo..."
            class="w-full border-2 border-gray-200 rounded-xl px-5 py-3 pl-12 focus:outline-none focus:ring-2 focus:ring-[#FDB700] focus:border-[#FDB700] transition shadow-sm hover:shadow-md"
          />
          <svg class="absolute left-4 top-3.5 w-5 h-5 text-[#FDB700]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>

        <!-- Pozoles Section -->
        <div v-if="hasAnyPozole && pozolesByColorFiltered.Verde.length + pozolesByColorFiltered.Blanco.length + pozolesByColorFiltered.Rojo.length > 0" class="">
          <h2 class="text-xl font-bold text-[#00126D] mb-4 flex items-center gap-2">
            <span class="text-2xl">🍲</span> Pozoles Especiales
          </h2>
          <div class="grid grid-cols-3 gap-4">
            <button
              v-if="pozolesByColorFiltered.Verde.length > 0"
              @click="openPozoleVariants('Verde')"
              class="bg-gradient-to-br from-green-50 to-green-100 border-2 border-green-500 rounded-xl p-6 text-center hover:shadow-xl hover:scale-105 transition-all font-bold text-green-700 active:scale-95"
            >
              🟢<br>Verde
            </button>
            <button
              v-if="pozolesByColorFiltered.Blanco.length > 0"
              @click="openPozoleVariants('Blanco')"
              class="bg-gradient-to-br from-gray-50 to-gray-100 border-2 border-gray-400 rounded-xl p-6 text-center hover:shadow-xl hover:scale-105 transition-all font-bold text-gray-700 active:scale-95"
            >
              ⚪<br>Blanco
            </button>
            <button
              v-if="pozolesByColorFiltered.Rojo.length > 0"
              @click="openPozoleVariants('Rojo')"
              class="bg-gradient-to-br from-red-50 to-red-100 border-2 border-red-500 rounded-xl p-6 text-center hover:shadow-xl hover:scale-105 transition-all font-bold text-red-700 active:scale-95"
            >
              🔴<br>Rojo
            </button>
          </div>
        </div>

        <!-- Other Categories -->
        <div v-for="(items, cat) in groupedFiltered" :key="cat" class="">
          <div :class="['text-xl font-bold mb-4 px-4 py-2 rounded-lg border-2', getCategoryTextColor(cat), getCategoryColor(cat)]">{{ cat }}</div>
          <div class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
            <button
              v-for="p in items"
              :key="p.id"
              class="bg-white border-2 border-gray-200 rounded-xl p-4 text-left hover:shadow-lg hover:border-[#FDB700] hover:scale-105 group transition-all active:scale-95"
              @click="addToCart(p)"
            >
              <div class="text-sm font-semibold text-[#FDB700] mb-1">$ {{ Number(p.precio).toFixed(2) }}</div>
              <div class="font-bold text-[#00126D] group-hover:text-[#3AAD08] text-sm">{{ p.nombre }}</div>
              <div class="text-xs text-gray-600 line-clamp-2 mt-1">{{ p.descripcion }}</div>
            </button>
          </div>
        </div>
      </section>

      <!-- Carrito -->
      <aside class="bg-gradient-to-b from-white to-blue-50 border-2 border-gray-200 rounded-2xl p-6 flex flex-col gap-5 h-fit sticky top-6 shadow-xl">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-bold text-[#00126D] mb-2">📦 Tipo de orden</label>
            <div class="flex flex-col gap-2">
              <button :class="['px-3 py-2.5 rounded-lg border-2 text-sm font-semibold transition-all', tipoOrden==='aqui' ? 'bg-[#00126D] text-white border-[#00126D] shadow-md' : 'bg-white border-gray-200 text-[#00126D] hover:border-[#00126D]']" @click="setTipoOrden('aqui')">Aquí</button>
              <button :class="['px-3 py-2.5 rounded-lg border-2 text-sm font-semibold transition-all', tipoOrden==='llevar' ? 'bg-[#00126D] text-white border-[#00126D] shadow-md' : 'bg-white border-gray-200 text-[#00126D] hover:border-[#00126D]']" @click="setTipoOrden('llevar')">Llevar</button>
              <button :class="['px-3 py-2.5 rounded-lg border-2 text-sm font-semibold transition-all', tipoOrden==='uber_eats' ? 'bg-[#00126D] text-white border-[#00126D] shadow-md' : 'bg-white border-gray-200 text-[#00126D] hover:border-[#00126D]']" @click="setTipoOrden('uber_eats')">UberEats</button>
            </div>
          </div>
          <div>
            <label class="block text-sm font-bold text-[#00126D] mb-2">💳 Método de pago</label>
            <div class="flex flex-col gap-2">
              <button :disabled="tipoOrden==='uber_eats'" :class="['px-3 py-2.5 rounded-lg border-2 text-sm font-semibold transition-all', metodoPago==='efectivo' ? 'bg-[#FDB700] text-[#00126D] border-[#FDB700] shadow-md' : 'bg-white border-gray-200 text-[#00126D] hover:border-[#FDB700]', tipoOrden==='uber_eats' ? 'opacity-40 cursor-not-allowed' : '']" @click="metodoPago='efectivo'">Efectivo</button>
              <button :class="['px-3 py-2.5 rounded-lg border-2 text-sm font-semibold transition-all', metodoPago==='tarjeta' ? 'bg-[#FDB700] text-[#00126D] border-[#FDB700] shadow-md' : 'bg-white border-gray-200 text-[#00126D] hover:border-[#FDB700]']" @click="metodoPago='tarjeta'">Tarjeta</button>
              <button :disabled="tipoOrden==='uber_eats'" :class="['px-3 py-2.5 rounded-lg border-2 text-sm font-semibold transition-all', metodoPago==='transferencia' ? 'bg-[#FDB700] text-[#00126D] border-[#FDB700] shadow-md' : 'bg-white border-gray-200 text-[#00126D] hover:border-[#FDB700]', tipoOrden==='uber_eats' ? 'opacity-40 cursor-not-allowed' : '']" @click="metodoPago='transferencia'">Transferencia</button>
            </div>
          </div>
        </div>

        <div class="border-t-2 border-gray-100 pt-4">
          <div class="text-xs font-semibold text-gray-600 mb-2">🛒 CARRITO ({{ cart.length }} items)</div>
          <div class="space-y-2 max-h-[35vh] overflow-auto">
            <div v-if="cart.length === 0" class="text-sm text-gray-500 text-center py-4">Sin artículos</div>
            <div v-for="ci in cart" :key="ci.platillo.id" class="bg-white border-2 border-gray-100 rounded-lg p-3 hover:shadow-md transition">
              <div class="flex items-center justify-between mb-2">
                <div>
                  <div class="font-bold text-[#00126D] text-sm">{{ ci.platillo.nombre }}</div>
                  <div class="text-xs text-[#FDB700] font-semibold">$ {{ Number(ci.platillo.precio).toFixed(2) }}</div>
                </div>
                <div class="flex items-center gap-1.5 bg-gray-100 rounded-lg p-1">
                  <button class="px-2 py-1 rounded bg-white hover:bg-gray-200 transition font-bold text-sm" @click="decQty(ci.platillo.id)">−</button>
                  <div class="w-6 text-center font-bold text-sm">{{ ci.cantidad }}</div>
                  <button class="px-2 py-1 rounded bg-white hover:bg-gray-200 transition font-bold text-sm" @click="incQty(ci.platillo.id)">+</button>
                  <button class="px-2 py-1 rounded bg-red-100 hover:bg-red-200 transition text-red-600 font-bold text-sm" @click="removeFromCart(ci.platillo.id)">✕</button>
                </div>
              </div>
              <input v-model="ci.modificaciones" placeholder="Notas (opcional)" class="w-full border border-gray-200 rounded-lg px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-[#FDB700]" />
            </div>
          </div>
        </div>

        <div class="bg-gradient-to-r from-[#00126D] to-[#001a4d] rounded-xl p-4 text-white">
          <div class="flex items-center justify-between mb-3">
            <span class="font-bold text-lg">💰 TOTAL</span>
            <span class="text-2xl font-black">$ {{ total.toFixed(2) }}</span>
          </div>
          <button @click="enviarPedido" :disabled="loading || cart.length===0" class="w-full py-3 rounded-lg text-[#00126D] bg-[#FDB700] hover:bg-yellow-400 disabled:opacity-50 disabled:cursor-not-allowed font-bold text-lg transition-all shadow-lg hover:shadow-xl active:scale-95">
            {{ loading ? '⏳ Enviando...' : '✓ Enviar pedido' }}
          </button>
        </div>
      </aside>
    </main>

    <!-- Pozole Variant Modal -->
    <PozoleVariantModal
      v-if="selectedPozoleColor"
      :color="selectedPozoleColor"
      :platillos="pozolesByColorFiltered[selectedPozoleColor]"
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
