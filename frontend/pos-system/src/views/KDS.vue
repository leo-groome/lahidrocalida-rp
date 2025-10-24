<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed } from 'vue'
import { api } from '../api/client'
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'

// Tipo mínimo para mostrar tarjetas en KDS
interface PedidoKDS {
  id: number
  numero_display: string
  nombre_cliente: string | null
  estado: 'pendiente' | 'preparando' | 'listo' | 'completado' | 'cancelado'
  fecha_creacion: string
  articulos_pedido?: Array<{
    id: number
    cantidad: number
    precio_cobrado: string | number
    modificaciones?: string | null
    platillo?: { nombre: string }
  }>
}

const auth = useAuthStore()
const router = useRouter()

const pedidos = ref<PedidoKDS[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
let timer: number | undefined

const pendientes = computed(() => pedidos.value.filter(p => p.estado === 'pendiente'))
const preparando = computed(() => pedidos.value.filter(p => p.estado === 'preparando'))
const listos = computed(() => pedidos.value.filter(p => p.estado === 'listo'))

async function fetchPedidos() {
  loading.value = true
  error.value = null
  try {
    // Trae todos y filtramos por estado en cliente; backend ya ordena por fecha
    const { data } = await api.get<PedidoKDS[]>('/pedidos')
    pedidos.value = data
  } catch (e: any) {
    error.value = e?.response?.data?.detail || 'Error cargando pedidos'
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  if (!auth.isAuthenticated) {
    router.replace({ name: 'login' })
    return
  }
  await fetchPedidos()
  timer = window.setInterval(fetchPedidos, 10000)
})

onUnmounted(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<template>
  <div class="min-h-screen flex flex-col bg-[#F8FAFC]">
    <header class="flex items-center justify-between px-4 py-3 border-b bg-white">
      <h1 class="text-xl font-semibold text-[#00126D]">KDS - Cocina</h1>
      <div class="text-sm text-[#00126D]">Actualizando cada 10s</div>
    </header>

    <main class="p-4">
      <div v-if="error" class="p-3 bg-red-50 text-red-700 border border-red-200 rounded mb-4">{{ error }}</div>
      <div v-if="loading" class="p-3">Cargando...</div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <!-- Pendientes -->
        <section class="bg-white border rounded-xl p-3">
          <h2 class="text-lg font-semibold text-[#00126D] mb-2">Pendientes</h2>
          <div class="space-y-3 max-h-[70vh] overflow-auto">
            <div v-for="p in pendientes" :key="p.id" class="border rounded-md p-3">
              <div class="flex items-center justify-between">
                <div class="text-2xl font-extrabold text-[#00126D]">{{ p.numero_display }}</div>
                <div class="text-sm text-gray-600">{{ new Date(p.fecha_creacion).toLocaleTimeString() }}</div>
              </div>
              <div class="text-sm text-gray-700">{{ p.nombre_cliente }}</div>
              <ul class="mt-2 text-sm list-disc pl-5">
                <li v-for="a in p.articulos_pedido || []" :key="a.id">
                  <span class="font-medium">{{ a.cantidad }}x</span>
                  <span class="ml-1">{{ a.platillo?.nombre || 'Platillo' }}</span>
                  <span v-if="a.modificaciones" class="text-gray-500"> — {{ a.modificaciones }}</span>
                </li>
              </ul>
            </div>
            <div v-if="pendientes.length===0" class="text-sm text-gray-500">Sin pedidos pendientes</div>
          </div>
        </section>

        <!-- Preparando -->
        <section class="bg-white border rounded-xl p-3">
          <h2 class="text-lg font-semibold text-[#00126D] mb-2">Preparando</h2>
          <div class="space-y-3 max-h-[70vh] overflow-auto">
            <div v-for="p in preparando" :key="p.id" class="border rounded-md p-3">
              <div class="flex items-center justify-between">
                <div class="text-2xl font-extrabold text-[#00126D]">{{ p.numero_display }}</div>
                <div class="text-sm text-gray-600">{{ new Date(p.fecha_creacion).toLocaleTimeString() }}</div>
              </div>
              <div class="text-sm text-gray-700">{{ p.nombre_cliente }}</div>
              <ul class="mt-2 text-sm list-disc pl-5">
                <li v-for="a in p.articulos_pedido || []" :key="a.id">
                  <span class="font-medium">{{ a.cantidad }}x</span>
                  <span class="ml-1">{{ a.platillo?.nombre || 'Platillo' }}</span>
                  <span v-if="a.modificaciones" class="text-gray-500"> — {{ a.modificaciones }}</span>
                </li>
              </ul>
            </div>
            <div v-if="preparando.length===0" class="text-sm text-gray-500">Sin pedidos preparando</div>
          </div>
        </section>

        <!-- Listos -->
        <section class="bg-white border rounded-xl p-3">
          <h2 class="text-lg font-semibold text-[#00126D] mb-2">Listos</h2>
          <div class="space-y-3 max-h-[70vh] overflow-auto">
            <div v-for="p in listos" :key="p.id" class="border rounded-md p-3">
              <div class="flex items-center justify-between">
                <div class="text-2xl font-extrabold text-[#00126D]">{{ p.numero_display }}</div>
                <div class="text-sm text-gray-600">{{ new Date(p.fecha_creacion).toLocaleTimeString() }}</div>
              </div>
              <div class="text-sm text-gray-700">{{ p.nombre_cliente }}</div>
              <ul class="mt-2 text-sm list-disc pl-5">
                <li v-for="a in p.articulos_pedido || []" :key="a.id">
                  <span class="font-medium">{{ a.cantidad }}x</span>
                  <span class="ml-1">{{ a.platillo?.nombre || 'Platillo' }}</span>
                  <span v-if="a.modificaciones" class="text-gray-500"> — {{ a.modificaciones }}</span>
                </li>
              </ul>
            </div>
            <div v-if="listos.length===0" class="text-sm text-gray-500">Sin pedidos listos</div>
          </div>
        </section>
      </div>
    </main>
  </div>
</template>

<style scoped>
</style>
