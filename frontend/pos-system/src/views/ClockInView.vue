<template>
  <div class="min-h-screen bg-[#00126D] flex flex-col">
    <!-- Header -->
    <header class="flex items-center justify-between px-6 pt-8 pb-4">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
          </svg>
        </div>
        <div>
          <h1 class="text-white font-black text-lg leading-tight">Registro de Asistencia</h1>
          <p class="text-white/60 text-xs">Selecciona tu nombre e ingresa tu NIP</p>
        </div>
      </div>
      <router-link
        to="/login"
        class="text-white/50 text-sm font-medium hover:text-white/80 transition-colors flex items-center gap-1"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M19 12H5M5 12l7-7M5 12l7 7"/>
        </svg>
        Login
      </router-link>
    </header>

    <!-- User grid -->
    <main class="flex-1 px-6 pb-8">
      <div v-if="loadingUsers" class="flex items-center justify-center py-20">
        <div class="w-8 h-8 border-4 border-white/30 border-t-white rounded-full animate-spin"/>
      </div>

      <div v-else-if="users.length === 0" class="text-center py-20">
        <p class="text-white/60">No hay empleados registrados</p>
      </div>

      <div v-else class="grid grid-cols-3 sm:grid-cols-4 gap-4 mt-2">
        <button
          v-for="user in users"
          :key="user.id"
          @click="selectUser(user)"
          class="flex flex-col items-center gap-2.5 p-4 rounded-2xl bg-white/10 active:bg-white/20 transition-colors"
        >
          <div
            class="w-16 h-16 rounded-full flex items-center justify-center text-xl font-black text-white flex-shrink-0"
            :class="getColor(user.nombre)"
          >
            {{ getInitials(user.nombre) }}
          </div>
          <span class="text-white text-xs font-semibold text-center leading-tight line-clamp-2">
            {{ user.nombre }}
          </span>
        </button>
      </div>
    </main>

    <!-- NIP Overlay -->
    <NipKeypad
      v-if="selectedUser"
      :user-name="selectedUser.nombre"
      :error="nipError"
      :loading="loadingNip"
      @confirm="handleConfirm"
      @cancel="selectedUser = null; nipError = null"
    />

    <!-- Toast feedback -->
    <Teleport to="body">
      <Transition name="toast">
        <div
          v-if="feedback"
          class="fixed bottom-8 left-1/2 -translate-x-1/2 z-[200] flex items-center gap-3 px-6 py-4 rounded-2xl shadow-2xl min-w-[280px] max-w-sm"
          :class="feedback.type === 'success' ? 'bg-emerald-500' : 'bg-red-500'"
        >
          <div class="w-8 h-8 bg-white/20 rounded-full flex items-center justify-center flex-shrink-0">
            <svg v-if="feedback.type === 'success'" xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
            <svg v-else xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </div>
          <div>
            <p class="text-white font-bold text-sm">{{ feedback.userName }}</p>
            <p class="text-white/90 text-xs">{{ feedback.message }}</p>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '@/api/client'
import NipKeypad from '@/components/NipKeypad.vue'

interface StaffUser {
  id: number
  nombre: string
  rol: string
}

interface Feedback {
  type: 'success' | 'error'
  message: string
  userName: string
}

const COLORS = [
  'bg-blue-500', 'bg-emerald-500', 'bg-violet-500',
  'bg-amber-500', 'bg-rose-500', 'bg-cyan-500',
]

const users = ref<StaffUser[]>([])
const selectedUser = ref<StaffUser | null>(null)
const nipError = ref<string | null>(null)
const loadingUsers = ref(false)
const loadingNip = ref(false)
const feedback = ref<Feedback | null>(null)

function getInitials(nombre: string): string {
  return nombre.trim().split(/\s+/).slice(0, 2).map(w => w[0]).join('').toUpperCase()
}

function getColor(nombre: string): string {
  const hash = nombre.split('').reduce((a, c) => a + c.charCodeAt(0), 0)
  return COLORS[hash % COLORS.length]
}

function selectUser(user: StaffUser) {
  nipError.value = null
  selectedUser.value = user
}

function formatTime(isoString: string): string {
  return new Date(isoString).toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' })
}

async function handleConfirm(pin: string) {
  if (!selectedUser.value) return
  loadingNip.value = true
  nipError.value = null
  try {
    const { data } = await api.post('/auth/asistencia', {
      usuario_id: selectedUser.value.id,
      pin,
    })
    const action = data.fecha_salida ? 'Salida registrada' : 'Entrada registrada'
    const time = data.fecha_salida
      ? formatTime(data.fecha_salida)
      : formatTime(data.fecha_entrada)
    feedback.value = {
      type: 'success',
      message: `${action} — ${time}`,
      userName: selectedUser.value.nombre,
    }
    selectedUser.value = null
    setTimeout(() => { feedback.value = null }, 3500)
  } catch (e: any) {
    nipError.value = e?.response?.data?.detail || 'NIP incorrecto'
  } finally {
    loadingNip.value = false
  }
}

onMounted(async () => {
  loadingUsers.value = true
  try {
    const { data } = await api.get('/auth/users')
    users.value = data
  } finally {
    loadingUsers.value = false
  }
})
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(20px);
}
</style>
