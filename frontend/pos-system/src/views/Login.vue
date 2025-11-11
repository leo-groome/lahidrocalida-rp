<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const userId = ref('')
const password = ref('')
const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

async function onSubmit() {
  const idTrimmed = userId.value.trim()
  if (!idTrimmed || !password.value) return
  // validar que user_id sea numérico (el backend espera ID de usuario)
  if (!/^\d+$/.test(idTrimmed)) {
    auth.error = 'Ingresa el ID numérico del usuario (no el nombre)'
    return
  }
  try {
    await auth.login(idTrimmed, password.value)
    const redirect = (route.query.redirect as string) || null
    if (redirect) {
      router.replace(redirect)
      return
    }
    switch (auth.role as any) {
      case 'cajero':
        router.replace({ name: 'caja' })
        break
      case 'mesero':
        router.replace({ name: 'mesero' })
        break
      case 'cocina':
        router.replace({ name: 'kds-view' })
        break
      case 'administrador':
        router.replace({ name: 'admin' })
        break
      default:
        router.replace({ name: 'mesero' })
        break
    }
  } catch {
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-[#FFFFFF]">
    <div class="w-full max-w-sm p-8 rounded-xl shadow border border-gray-100">
      <div class="flex flex-col items-center gap-3 mb-6">
        <img src="/src/assets/Logo.png" alt="Logo" class="h-14" />
        <h1 class="text-2xl font-semibold text-[#00126D]">Iniciar sesión</h1>
      </div>
      <form @submit.prevent="onSubmit" class="space-y-4">
        <div>
          <label class="block text-sm text-[#00126D] mb-1">ID de usuario</label>
          <input v-model="userId" type="text" class="w-full border rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-[#FDB700]" placeholder="Ej. 1" />
        </div>
        <div>
          <label class="block text-sm text-[#00126D] mb-1">Contraseña</label>
          <input v-model="password" type="password" class="w-full border rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-[#FDB700]" />
        </div>
        <div v-if="auth.error" class="text-red-600 text-sm">{{ auth.error }}</div>
        <button type="submit" :disabled="auth.loading" class="w-full py-2 rounded-md text-white bg-[#00126D] hover:opacity-90 disabled:opacity-60">
          {{ auth.loading ? 'Entrando...' : 'Entrar' }}
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
</style>
