<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed } from 'vue'
import { api } from '../api/client'

interface Pedido {
  id: number
  numero_display: string
  tipo_orden: 'aqui' | 'llevar' | 'uber_eats'
  estado: 'pendiente' | 'preparando' | 'listo' | 'completado' | 'cancelado'
  fecha_creacion: string
}

const pedidos = ref<Pedido[]>([])
let timer: number | undefined

const pedidosListos = computed(() => {
  const listos = pedidos.value.filter(p => p.estado === 'listo')
  return listos.sort((a, b) => new Date(a.fecha_creacion).getTime() - new Date(b.fecha_creacion).getTime())
})

const pedidosVisibles = computed(() => {
  if (pedidosListos.value.length === 0) return []
  return pedidosListos.value.slice(0, 4)
})

function getTipoOrdenEmoji(tipo: string) {
  const emojis: Record<string, string> = {
    'aqui': '🍽️',
    'llevar': '📦',
    'uber_eats': '🚗'
  }
  return emojis[tipo] || '📋'
}

function getTipoOrdenLabel(tipo: string) {
  const labels: Record<string, string> = {
    'aqui': 'Para aquí',
    'llevar': 'Para llevar',
    'uber_eats': 'UberEats'
  }
  return labels[tipo] || tipo
}

async function fetchPedidos() {
  try {
    const { data } = await api.get<Pedido[]>('/pedidos')
    pedidos.value = data
  } catch (e: any) {
    console.error('Error cargando pedidos:', e)
  }
}

onMounted(async () => {
  await fetchPedidos()
  timer = window.setInterval(fetchPedidos, 3000)
})

onUnmounted(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<template>
  <div class="min-h-screen flex flex-col bg-gradient-to-br from-[#00126D] to-[#001a4d]">
    <!-- Header -->
    <header class="px-6 py-6 text-center border-b-4 border-[#FDB700]">
      <div class="flex items-center justify-center gap-4 mb-4">
        <img src="/src/assets/Logo.png" alt="Logo" class="h-16" />
      </div>
      <h1 class="text-5xl font-black text-white mb-2">¡Tu Pedido está Listo!</h1>
      <p class="text-xl text-blue-100">Acércate a recoger tu orden</p>
    </header>

    <!-- Main Content -->
    <main class="flex-1 flex items-center justify-center p-8">
      <div v-if="pedidosListos.length === 0" class="text-center">
        <div class="text-9xl mb-6 animate-bounce">⏳</div>
        <p class="text-4xl font-bold text-white mb-4">Preparando tu pedido...</p>
        <p class="text-2xl text-blue-100">Vuelve en un momento</p>
      </div>

      <div v-else class="w-full">
        <!-- Grid de 4 columnas -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div
            v-for="p in pedidosVisibles"
            :key="p.id"
            class="bg-white rounded-3xl shadow-2xl overflow-hidden transform hover:shadow-xl transition-shadow duration-300"
          >
            <!-- Número de Pedido Grande -->
            <div class="bg-gradient-to-r from-green-400 to-green-500 px-6 py-10 text-center">
              <p class="text-green-100 text-xl font-bold mb-2">PEDIDO</p>
              <p class="text-7xl font-black text-white drop-shadow-lg">{{ p.numero_display }}</p>
            </div>

            <!-- Tipo de Orden -->
            <div class="px-6 py-8 text-center border-b-4 border-gray-200">
              <div class="text-5xl mb-3">{{ getTipoOrdenEmoji(p.tipo_orden) }}</div>
              <p class="text-lg font-bold text-[#00126D]">{{ getTipoOrdenLabel(p.tipo_orden) }}</p>
            </div>

            <!-- Footer -->
            <div class="px-6 py-6 bg-gray-50 text-center">
              <p class="text-green-600 text-lg font-bold">✓ LISTO</p>
            </div>
          </div>
        </div>

        <!-- Contador -->
        <div class="text-center mt-8">
          <p class="text-white text-lg font-semibold">Mostrando {{ pedidosVisibles.length }} de {{ pedidosListos.length }} pedidos listos</p>
        </div>
      </div>
    </main>

    <!-- Footer Info -->
    <footer class="px-6 py-4 text-center border-t-4 border-[#FDB700] bg-black bg-opacity-20">
      <p class="text-blue-100 text-lg">La Hidrocálida - Pozolería</p>
    </footer>
  </div>
</template>

<style scoped>
@keyframes bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-20px);
  }
}

.animate-bounce {
  animation: bounce 2s infinite;
}
</style>
