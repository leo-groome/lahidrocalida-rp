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

      <div v-else class="space-y-8">
        <div v-for="role in ['cajero', 'mesero', 'cocina', 'administrador']" :key="role">
          <div v-if="groupedUsers[role] && groupedUsers[role].length > 0">
            <h2 class="text-white/40 text-xs font-black uppercase tracking-widest mb-3 px-2">
              {{ role === 'cajero' ? '💰 Cajeros' : role === 'mesero' ? '🍽️ Meseros' : role === 'cocina' ? '👨‍🍳 Cocina' : '🔑 Administradores' }}
            </h2>
            <div class="grid grid-cols-3 sm:grid-cols-4 gap-4">
              <button
                v-for="user in groupedUsers[role]"
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
          </div>
        </div>
      </div>
    </main>

    <!-- NIP Overlay -->
    <!-- NIP Overlay -->
    <NipKeypad
      v-if="selectedUser"
      :user-name="selectedUser.nombre"
      :error="nipError"
      :loading="loadingNip"
      :tiene-turno-activo="tieneTurnoActivo"
      @confirm="handleConfirm"
      @cancel="selectedUser = null; nipError = null; tieneTurnoActivo = null"
    />

    <!-- Mercado Libre style success full-screen overlay -->
    <Teleport to="body">
      <Transition name="success-fade">
        <div
          v-if="showSuccessOverlay"
          class="fixed inset-0 z-[300] flex flex-col items-center justify-center p-6 text-white text-center select-none"
          :class="successAction === 'Entrada'
            ? 'bg-gradient-to-br from-emerald-600 to-teal-900'
            : 'bg-gradient-to-br from-amber-600 to-rose-950'"
        >
          <!-- Background decorative shapes -->
          <div class="absolute inset-0 overflow-hidden pointer-events-none">
            <div class="absolute -top-1/4 -left-1/4 w-[80vw] h-[80vw] bg-white/5 rounded-full blur-3xl animate-pulse"></div>
            <div class="absolute -bottom-1/4 -right-1/4 w-[80vw] h-[80vw] bg-white/5 rounded-full blur-3xl animate-pulse"></div>
          </div>

          <!-- Animated checkmark circle -->
          <div class="relative mb-8 scale-up-bounce">
            <div class="absolute -inset-4 rounded-full border-4 border-white/20 animate-ping opacity-35"></div>
            <svg class="w-32 h-32 text-white drop-shadow-lg" viewBox="0 0 100 100">
              <circle
                class="checkmark-circle"
                cx="50"
                cy="50"
                r="42"
                fill="none"
                stroke="currentColor"
                stroke-width="5"
              />
              <path
                class="checkmark-check"
                fill="none"
                d="M32 50 L45 63 L68 36"
                stroke="currentColor"
                stroke-width="7"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
          </div>

          <!-- Details Card -->
          <div class="space-y-6 max-w-md z-10 w-full px-4">
            <h2 class="text-3xl md:text-4xl font-black tracking-tight animate-fade-in-up">
              {{ successAction === 'Entrada' ? '¡Entrada Registrada!' : '¡Salida Registrada!' }}
            </h2>
            <div class="p-6 bg-white/10 backdrop-blur-md rounded-3xl border border-white/15 shadow-2xl animate-fade-in-up-delay">
              <p class="text-white/60 text-xs uppercase tracking-widest font-black mb-1">Colaborador</p>
              <p class="text-2xl font-black text-white mb-4">{{ successUserName }}</p>
              <div class="h-[1px] bg-white/15 w-full mb-4"></div>
              <p class="text-white/60 text-xs uppercase tracking-widest font-black mb-1">Hora de Registro</p>
              <p class="text-4xl font-extrabold text-white tracking-tight">{{ successTime }}</p>
            </div>
            <p class="text-white/80 text-sm font-semibold animate-fade-in-up-delay-2 italic">
              {{ successAction === 'Entrada' ? '✨ ¡Que tengas un excelente turno!' : '🏡 ¡Buen descanso y gracias por tu día!' }}
            </p>
          </div>

          <!-- Click to dismiss -->
          <button
            @click="showSuccessOverlay = false"
            class="absolute bottom-10 px-8 py-3 rounded-full bg-white/15 hover:bg-white/20 active:scale-95 transition-all text-xs font-black tracking-wider uppercase border border-white/10 shadow-lg hover:shadow-xl z-20 cursor-pointer"
          >
            Entendido
          </button>
        </div>
      </Transition>
    </Teleport>

    <!-- Fallback/Error Toast feedback -->
    <Teleport to="body">
      <Transition name="toast">
        <div
          v-if="feedback && feedback.type === 'error'"
          class="fixed bottom-8 left-1/2 -translate-x-1/2 z-[200] flex items-center gap-3 px-6 py-4 rounded-2xl shadow-2xl min-w-[280px] max-w-sm bg-red-500"
        >
          <div class="w-8 h-8 bg-white/20 rounded-full flex items-center justify-center flex-shrink-0">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
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
import { ref, onMounted, computed } from 'vue'
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

// State for active shift indicator
const tieneTurnoActivo = ref<boolean | null>(null)

// State for full-screen success overlay
const showSuccessOverlay = ref(false)
const successAction = ref<'Entrada' | 'Salida'>('Entrada')
const successUserName = ref('')
const successTime = ref('')

const groupedUsers = computed(() => {
  const groups: Record<string, StaffUser[]> = {
    cajero: [],
    mesero: [],
    cocina: [],
    administrador: [],
  }
  users.value.forEach(u => {
    if (groups[u.rol]) {
      groups[u.rol].push(u)
    } else {
      groups[u.rol] = [u]
    }
  })
  return groups
})

function getInitials(nombre: string): string {
  return nombre.trim().split(/\s+/).slice(0, 2).map(w => w[0]).join('').toUpperCase()
}

function getColor(nombre: string): string {
  const hash = nombre.split('').reduce((a, c) => a + c.charCodeAt(0), 0)
  return COLORS[hash % COLORS.length]
}

async function selectUser(user: StaffUser) {
  nipError.value = null
  selectedUser.value = user
  tieneTurnoActivo.value = null // start with neutral loading state
  try {
    const { data } = await api.get(`/auth/asistencia/status/${user.id}`)
    tieneTurnoActivo.value = data.tiene_turno_activo
  } catch (e) {
    console.error('Error al obtener estado de asistencia:', e)
    tieneTurnoActivo.value = null // fallback to neutral
  }
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
    const action = data.fecha_salida ? 'Salida' : 'Entrada'
    const time = data.fecha_salida
      ? formatTime(data.fecha_salida)
      : formatTime(data.fecha_entrada)

    successAction.value = action
    successUserName.value = selectedUser.value.nombre
    successTime.value = time
    showSuccessOverlay.value = true

    // Close keypad immediately
    selectedUser.value = null
    tieneTurnoActivo.value = null

    // Auto-dismiss full-screen success overlay after 4 seconds
    setTimeout(() => {
      showSuccessOverlay.value = false
    }, 4000)

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

/* Success Overlay Transitions */
.success-fade-enter-active,
.success-fade-leave-active {
  transition: opacity 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}
.success-fade-enter-from,
.success-fade-leave-to {
  opacity: 0;
}

/* Drawing animations for checkmark SVG */
.checkmark-circle {
  stroke-dasharray: 270;
  stroke-dashoffset: 270;
  transform-origin: center;
  animation: draw-circle 0.7s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}

.checkmark-check {
  stroke-dasharray: 60;
  stroke-dashoffset: 60;
  animation: draw-check 0.4s ease-out 0.6s forwards;
}

@keyframes draw-circle {
  to {
    stroke-dashoffset: 0;
  }
}

@keyframes draw-check {
  to {
    stroke-dashoffset: 0;
  }
}

/* Scale bounce in */
.scale-up-bounce {
  animation: scale-up-bounce 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
}

@keyframes scale-up-bounce {
  from {
    transform: scale(0.65);
    opacity: 0;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}

/* Slide up and fade in text layers */
.animate-fade-in-up {
  opacity: 0;
  animation: fade-in-up 0.6s cubic-bezier(0.16, 1, 0.3, 1) 0.3s forwards;
}

.animate-fade-in-up-delay {
  opacity: 0;
  animation: fade-in-up 0.6s cubic-bezier(0.16, 1, 0.3, 1) 0.45s forwards;
}

.animate-fade-in-up-delay-2 {
  opacity: 0;
  animation: fade-in-up 0.6s cubic-bezier(0.16, 1, 0.3, 1) 0.6s forwards;
}

@keyframes fade-in-up {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
