<template>
  <main class="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-slate-100 p-5 sm:p-8">
    <section class="mx-auto max-w-5xl">
      <div class="mb-8 flex items-center justify-between gap-4">
        <div>
          <p class="text-xs font-black uppercase tracking-[0.2em] text-blue-600">Sesión de administrador</p>
          <h1 class="mt-2 text-3xl font-black tracking-tight text-slate-900 sm:text-4xl">¿A qué área deseas entrar?</h1>
          <p class="mt-2 text-sm text-slate-500">Elige el módulo que necesitas operar.</p>
        </div>
        <button
          class="rounded-xl px-4 py-2 text-sm font-bold text-slate-500 transition hover:bg-white hover:text-red-600"
          @click="logout"
        >
          Cerrar sesión
        </button>
      </div>

      <div class="grid gap-4 sm:grid-cols-2">
        <router-link
          v-for="area in areas"
          :key="area.name"
          :to="{ name: area.name }"
          class="group rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:border-blue-200 hover:shadow-xl"
        >
          <component :is="area.icon" class="mb-5 h-9 w-9 text-blue-600 transition group-hover:scale-110" />
          <h2 class="text-xl font-black text-slate-800">{{ area.title }}</h2>
          <p class="mt-2 text-sm leading-6 text-slate-500">{{ area.description }}</p>
          <span class="mt-5 inline-block text-sm font-bold text-blue-600">Entrar →</span>
        </router-link>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { LayoutDashboard, ReceiptText, ChefHat, UtensilsCrossed } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const areas = [
  { name: 'mesero', title: 'Mesero', description: 'Tomar pedidos y dar seguimiento a las mesas.', icon: UtensilsCrossed },
  { name: 'caja', title: 'Caja', description: 'Cobrar pedidos, gestionar turnos y revisar el corte.', icon: ReceiptText },
  { name: 'kds-manager', title: 'Cocina', description: 'Preparar y entregar los pedidos de cocina.', icon: ChefHat },
  { name: 'admin', title: 'Administración', description: 'Configurar el negocio y consultar la gestión.', icon: LayoutDashboard },
]

function logout() {
  auth.logout()
  router.replace({ name: 'login' })
}
</script>
