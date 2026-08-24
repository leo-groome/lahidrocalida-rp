<template>
  <div class="min-h-screen bg-[#00126D] flex flex-col">

    <!-- ═══════════════════════════════════════════════
         ESTADO A — Selector de rol del dispositivo
    ════════════════════════════════════════════════ -->
    <div v-if="!deviceRole" class="flex-1 flex flex-col items-center justify-center p-8">
      <div class="w-20 h-20 bg-white/20 rounded-3xl flex items-center justify-center mb-8">
        <svg xmlns="http://www.w3.org/2000/svg" class="w-10 h-10 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="5" y="2" width="14" height="20" rx="2" ry="2"/><line x1="12" y1="18" x2="12.01" y2="18"/>
        </svg>
      </div>
      <h1 class="text-white text-3xl font-black text-center mb-2">
        ¿Qué rol tiene<br/>esta tablet?
      </h1>
      <p class="text-white/60 text-sm text-center mb-10">
        Esta configuración se guarda en el dispositivo.<br/>Solo se hace una vez.
      </p>

      <div class="w-full max-w-xs space-y-3">
        <button
          v-for="role in deviceRoles"
          :key="role.id"
          @click="setDeviceRole(role.id)"
          class="w-full flex items-center gap-4 px-6 py-5 bg-white rounded-2xl text-[#00126D] font-black text-lg hover:bg-white/95 active:scale-[0.97] transition-all shadow-lg"
        >
          <span class="text-3xl">{{ role.emoji }}</span>
          <span>{{ role.label }}</span>
        </button>
      </div>

      <div class="mt-10">
        <router-link to="/admin-login" class="text-white/40 text-xs hover:text-white/60 transition-colors">
          Acceso administrativo →
        </router-link>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════════
         ESTADO B — Grid de usuarios
    ════════════════════════════════════════════════ -->
    <template v-else>
      <!-- Top bar -->
      <header class="flex items-center justify-between px-6 pt-8 pb-4">
        <div>
          <p class="text-white/60 text-xs uppercase tracking-widest font-bold">
            {{ currentRoleLabel }}
          </p>
          <h1 class="text-white font-black text-xl leading-tight">Hola, ¿quién eres?</h1>
        </div>
        <button
          @click="resetDeviceRole"
          class="w-10 h-10 bg-white/10 rounded-xl flex items-center justify-center text-white/40 hover:text-white/70 hover:bg-white/20 active:scale-95 transition-all"
          title="Cambiar configuración de tablet"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
          </svg>
        </button>
      </header>

      <!-- User grid -->
      <main class="flex-1 px-6 pb-24">
        <div v-if="loadingUsers" class="flex items-center justify-center py-20">
          <div class="w-8 h-8 border-4 border-white/30 border-t-white rounded-full animate-spin"/>
        </div>

        <div v-else-if="users.length === 0" class="text-center py-20">
          <p class="text-white/50 font-medium">No hay empleados con este rol</p>
          <button @click="resetDeviceRole" class="mt-4 text-white/60 underline text-sm">
            Cambiar rol del dispositivo
          </button>
        </div>

        <div v-else class="grid grid-cols-3 sm:grid-cols-4 gap-4 mt-2">
          <button
            v-for="user in users"
            :key="user.id"
            @click="selectUser(user)"
            class="flex flex-col items-center gap-2.5 p-4 rounded-2xl bg-white/10 active:bg-white/25 active:scale-95 transition-all"
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

    </template>

    <!-- Global Floating Button: Registrar Asistencia -->
    <div class="fixed bottom-6 left-0 right-0 flex justify-center pointer-events-none z-50">
      <router-link
        to="/checkin"
        class="pointer-events-auto flex items-center gap-2 px-6 py-3 rounded-full bg-white/10 hover:bg-white/20 border border-white/20 text-white font-bold text-sm tracking-wide shadow-lg backdrop-blur-md active:scale-95 transition-all duration-300"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-emerald-400 animate-pulse" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <polyline points="12 6 12 12 16 14"/>
        </svg>
        Registrar Asistencia
      </router-link>
    </div>

    <!-- NIP Overlay -->
    <NipKeypad
      v-if="selectedUser"
      :user-name="selectedUser.nombre"
      :error="nipError"
      :loading="loadingLogin"
      @confirm="handleNipConfirm"
      @cancel="selectedUser = null; nipError = null"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/api/client'
import NipKeypad from '@/components/NipKeypad.vue'

interface StaffUser {
  id: number
  nombre: string
  rol: string
}

const COLORS = [
  'bg-blue-500', 'bg-emerald-500', 'bg-violet-500',
  'bg-amber-500', 'bg-rose-500', 'bg-cyan-500',
]

const deviceRoles = [
  { id: 'mesero', label: 'Mesero', emoji: '🍽️' },
  { id: 'cajero', label: 'Cajero', emoji: '💰' },
  { id: 'cocina', label: 'Cocina', emoji: '👨‍🍳' },
]

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const deviceRole = ref<string | null>(localStorage.getItem('device_role'))
const users = ref<StaffUser[]>([])
const selectedUser = ref<StaffUser | null>(null)
const nipError = ref<string | null>(null)
const loadingUsers = ref(false)
const loadingLogin = ref(false)

const currentRoleLabel = computed(() =>
  deviceRoles.find(r => r.id === deviceRole.value)?.label ?? deviceRole.value ?? ''
)

function getInitials(nombre: string): string {
  return nombre.trim().split(/\s+/).slice(0, 2).map(w => w[0]).join('').toUpperCase()
}

function getColor(nombre: string): string {
  const hash = nombre.split('').reduce((a, c) => a + c.charCodeAt(0), 0)
  return COLORS[hash % COLORS.length]
}

function setDeviceRole(role: string) {
  localStorage.setItem('device_role', role)
  deviceRole.value = role
}

function resetDeviceRole() {
  localStorage.removeItem('device_role')
  deviceRole.value = null
  users.value = []
  selectedUser.value = null
}

function selectUser(user: StaffUser) {
  nipError.value = null
  selectedUser.value = user
}

function routeByRole() {
  const redirect = route.query.redirect as string | undefined
  if (redirect) {
    router.replace(redirect)
    return
  }
  switch (auth.role) {
    case 'cajero': router.replace({ name: 'caja' }); break
    case 'mesero': router.replace({ name: 'mesero' }); break
    case 'cocina': router.replace({ name: 'kds-manager' }); break
    case 'administrador': router.replace({ name: 'admin' }); break
    default: router.replace({ name: 'mesero' })
  }
}

async function handleNipConfirm(pin: string) {
  if (!selectedUser.value) return
  loadingLogin.value = true
  nipError.value = null
  try {
    await auth.login(String(selectedUser.value.id), pin)
    routeByRole()
  } catch {
    nipError.value = auth.error || 'NIP incorrecto'
    loadingLogin.value = false
  }
}

watch(deviceRole, async (role) => {
  if (!role) return
  loadingUsers.value = true
  try {
    const { data } = await api.get('/auth/users', { params: { rol: role } })
    users.value = data
  } catch {
    users.value = []
  } finally {
    loadingUsers.value = false
  }
}, { immediate: true })
</script>
