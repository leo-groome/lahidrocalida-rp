<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useAuthStore } from '../stores/auth'
import { api } from '../api/client'
import type { Platillo, ArticuloPedidoCreate } from '../types'
import { useRouter } from 'vue-router'

const auth = useAuthStore()
const router = useRouter()

const platillos = ref<Platillo[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

const nombreCliente = ref('')
const metodoPago = ref<'efectivo' | 'tarjeta' | 'transferencia'>('efectivo')
const tipoOrden = ref<'aqui' | 'llevar' | 'uber_eats'>('aqui')

interface CartItem {
  platillo: Platillo
  cantidad: number
  modificaciones: string
}
const cart = ref<CartItem[]>([])

function addToCart(p: Platillo) {
  const existing = cart.value.find(ci => ci.platillo.id === p.id)
  if (existing) existing.cantidad += 1
  else cart.value.push({ platillo: p, cantidad: 1, modificaciones: '' })
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

const grouped = computed(() => {
  const map: Record<string, Platillo[]> = {}
  for (const p of platillos.value) {
    if (!map[p.categoria]) map[p.categoria] = []
    if (p.estado === 'disponible') map[p.categoria].push(p)
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
  if (!nombreCliente.value.trim()) {
    error.value = 'El nombre del cliente es obligatorio'
    return
  }
  if (cart.value.length === 0) {
    error.value = 'Agrega al menos un artículo'
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
    await api.post('/pedidos', {
      nombre_cliente: nombreCliente.value.trim(),
      metodo_pago: metodoPago.value,
      tipo_orden: tipoOrden.value,
      articulos,
    })
    // limpiar
    cart.value = []
    nombreCliente.value = ''
    metodoPago.value = 'efectivo'
    tipoOrden.value = 'aqui'
    alert('Pedido creado')
  } catch (e: any) {
    error.value = e?.response?.data?.detail || 'Error creando pedido'
  } finally {
    loading.value = false
  }
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
  <div class="min-h-screen flex flex-col">
    <!-- Header -->
    <header class="flex items-center justify-between px-4 py-3 border-b bg-white">
      <div class="flex items-center gap-3">
        <img src="/src/assets/Logo.png" alt="Logo" class="h-8" />
        <h1 class="text-xl font-semibold text-[#00126D]">Caja - POS</h1>
      </div>
      <div class="flex items-center gap-3 text-sm">
        <span class="text-[#00126D]">{{ auth.user?.nombre }} ({{ auth.user?.rol }})</span>
        <button @click="logout" class="px-3 py-1.5 rounded-md border text-[#00126D] hover:bg-gray-50">Salir</button>
      </div>
    </header>

    <main class="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-4 p-4 bg-[#F8FAFC]">
      <!-- Menu -->
      <section class="lg:col-span-2 space-y-4">
        <div v-if="error" class="p-3 bg-red-50 text-red-700 border border-red-200 rounded">{{ error }}</div>
        <div v-if="loading" class="p-3">Cargando...</div>

        <div v-for="(items, cat) in grouped" :key="cat" class="">
          <h2 class="text-lg font-semibold text-[#00126D] mb-2">{{ cat }}</h2>
          <div class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-3">
            <button
              v-for="p in items"
              :key="p.id"
              class="bg-white border rounded-lg p-3 text-left hover:shadow group"
              @click="addToCart(p)"
            >
              <div class="text-sm text-gray-500">$ {{ Number(p.precio).toFixed(2) }}</div>
              <div class="font-medium text-[#00126D] group-hover:text-[#3AAD08]">{{ p.nombre }}</div>
              <div class="text-xs text-gray-500 line-clamp-2">{{ p.descripcion }}</div>
            </button>
          </div>
        </div>
      </section>

      <!-- Carrito -->
      <aside class="bg-white border rounded-xl p-4 flex flex-col gap-4">
        <div>
          <label class="block text-sm text-[#00126D] mb-1">Nombre del cliente</label>
          <input v-model="nombreCliente" type="text" class="w-full border rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-[#FDB700]" placeholder="Nombre" />
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="block text-sm text-[#00126D] mb-1">Tipo de orden</label>
            <div class="flex gap-2 flex-wrap">
              <button :class="['px-3 py-2 rounded border text-sm flex-1 min-w-[90px]', tipoOrden==='aqui' ? 'bg-[#00126D] text-white' : 'bg-white']" @click="tipoOrden='aqui'">Aquí</button>
              <button :class="['px-3 py-2 rounded border text-sm flex-1 min-w-[90px]', tipoOrden==='llevar' ? 'bg-[#00126D] text-white' : 'bg-white']" @click="tipoOrden='llevar'">Llevar</button>
              <button :class="['px-3 py-2 rounded border text-sm flex-1 min-w-[90px]', tipoOrden==='uber_eats' ? 'bg-[#00126D] text-white' : 'bg-white']" @click="tipoOrden='uber_eats'">UberEats</button>
            </div>
          </div>
          <div>
            <label class="block text-sm text-[#00126D] mb-1">Método de pago</label>
            <div class="flex gap-2 flex-wrap">
              <button :class="['px-3 py-2 rounded border text-sm flex-1 min-w-[110px]', metodoPago==='efectivo' ? 'bg-[#FDB700] text-[#00126D]' : 'bg-white']" @click="metodoPago='efectivo'">Efectivo</button>
              <button :class="['px-3 py-2 rounded border text-sm flex-1 min-w-[110px]', metodoPago==='tarjeta' ? 'bg-[#FDB700] text-[#00126D]' : 'bg-white']" @click="metodoPago='tarjeta'">Tarjeta</button>
              <button :class="['px-3 py-2 rounded border text-sm flex-1 min-w-[110px]', metodoPago==='transferencia' ? 'bg-[#FDB700] text-[#00126D]' : 'bg-white']" @click="metodoPago='transferencia'">Transferencia</button>
            </div>
          </div>
        </div>

        <div class="border-t pt-3 space-y-3 max-h-[45vh] overflow-auto">
          <div v-if="cart.length === 0" class="text-sm text-gray-500">Sin artículos</div>
          <div v-for="ci in cart" :key="ci.platillo.id" class="border rounded-md p-2">
            <div class="flex items-center justify-between">
              <div>
                <div class="font-medium text-[#00126D]">{{ ci.platillo.nombre }}</div>
                <div class="text-xs text-gray-500">$ {{ Number(ci.platillo.precio).toFixed(2) }}</div>
              </div>
              <div class="flex items-center gap-2">
                <button class="px-2 py-1 border rounded" @click="decQty(ci.platillo.id)">-</button>
                <div class="w-8 text-center">{{ ci.cantidad }}</div>
                <button class="px-2 py-1 border rounded" @click="incQty(ci.platillo.id)">+</button>
                <button class="px-2 py-1 border rounded text-red-600" @click="removeFromCart(ci.platillo.id)">x</button>
              </div>
            </div>
            <div class="mt-2">
              <input v-model="ci.modificaciones" placeholder="Modificadores (opcional)" class="w-full border rounded-md px-2 py-1 text-sm" />
            </div>
          </div>
        </div>

        <div class="mt-auto space-y-3">
          <div class="flex items-center justify-between text-lg">
            <span class="text-[#00126D] font-medium">Total</span>
            <span class="font-semibold">$ {{ total.toFixed(2) }}</span>
          </div>
          <button @click="enviarPedido" :disabled="loading || cart.length===0" class="w-full py-3 rounded-md text-white bg-[#3AAD08] hover:opacity-90 disabled:opacity-60">
            {{ loading ? 'Enviando...' : 'Enviar pedido' }}
          </button>
        </div>
      </aside>
    </main>
  </div>
</template>

<style scoped>
</style>
