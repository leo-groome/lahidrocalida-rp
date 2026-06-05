<template>
  <div class="min-h-screen bg-gradient-to-br from-[#00126D] to-[#001D9A] flex items-center justify-center p-6">
    <div class="bg-white rounded-2xl p-10 w-full max-w-md shadow-2xl">
      <!-- Logo + título -->
      <div class="text-center mb-8">
        <div class="w-16 h-16 bg-[#00126D] rounded-2xl flex items-center justify-center mx-auto mb-4">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-9 h-9 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
          </svg>
        </div>
        <h1 class="text-2xl font-black text-[#00126D]">Panel de Administración</h1>
        <p class="text-sm text-slate-500 mt-1">Acceso restringido al equipo administrador</p>
      </div>

      <!-- Form -->
      <form @submit.prevent="onSubmit" class="space-y-4">
        <div>
          <label class="block text-sm font-semibold text-slate-700 mb-1.5">Usuario administrador</label>
          <input
            v-model="email"
            type="text"
            autocomplete="username"
            placeholder="Admin"
            required
            class="w-full px-4 py-3 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#00126D]/30 focus:border-[#00126D] transition-colors"
          />
        </div>

        <div>
          <label class="block text-sm font-semibold text-slate-700 mb-1.5">Contraseña</label>
          <input
            v-model="password"
            type="password"
            autocomplete="current-password"
            placeholder="••••••••"
            required
            class="w-full px-4 py-3 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#00126D]/30 focus:border-[#00126D] transition-colors"
          />
        </div>

        <!-- Error -->
        <div v-if="auth.error" class="p-3 bg-red-50 border border-red-200 rounded-xl">
          <p class="text-sm text-red-600 font-medium">{{ auth.error }}</p>
        </div>

        <button
          type="submit"
          :disabled="auth.loading"
          class="w-full py-3.5 bg-[#00126D] text-white font-bold rounded-xl hover:bg-[#001a8f] active:scale-[0.98] transition-all disabled:opacity-60 disabled:cursor-not-allowed mt-2"
        >
          <span v-if="auth.loading">Verificando...</span>
          <span v-else>Acceder al panel</span>
        </button>
      </form>

      <!-- Back link -->
      <div class="text-center mt-6">
        <router-link to="/login" class="text-sm text-slate-400 hover:text-slate-600 transition-colors">
          ← Volver al login de empleados
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

const email = ref('')
const password = ref('')

async function onSubmit() {
  await auth.loginAdmin(email.value, password.value)
  if (!auth.error) {
    router.replace({ name: 'admin' })
  }
}
</script>
