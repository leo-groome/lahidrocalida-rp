<template>
  <div class="min-h-dvh bg-slate-50 flex flex-col">
    <!-- Header -->
    <header class="safe-area-top sticky top-0 z-40 bg-white/90 backdrop-blur border-b border-slate-100">
      <div class="max-w-xl mx-auto px-4 py-3 flex items-center gap-3">
        <button
          @click="volver"
          class="w-11 h-11 flex items-center justify-center rounded-xl bg-slate-100 text-slate-500 hover:bg-slate-900 hover:text-white transition-all flex-shrink-0"
          title="Volver"
        >
          <ArrowLeft class="w-5 h-5" />
        </button>
        <div class="min-w-0">
          <p class="text-xs font-black tracking-widest text-slate-400 uppercase leading-none">Compras</p>
          <h1 class="text-base font-black text-slate-900 tracking-tight">Registro rápido</h1>
        </div>
      </div>
      <div class="max-w-xl mx-auto px-4 empty:hidden"><InstallPWA class="mb-3" /></div>
    </header>

    <main class="flex-1 max-w-xl w-full mx-auto px-4 pt-5 pb-5">
      <RegistroRapidoForm />
    </main>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ArrowLeft } from 'lucide-vue-next'
import InstallPWA from '@/components/InstallPWA.vue'
import RegistroRapidoForm from '@/components/gastos/RegistroRapidoForm.vue'

const router = useRouter()

function volver() {
  if (window.history.length > 1) router.back()
  else router.push('/compras')
}
</script>
