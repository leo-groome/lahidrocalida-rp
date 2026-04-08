<script setup lang="ts">
import { ref, onMounted } from 'vue'

const deferredPrompt = ref<any>(null)
const showInstallButton = ref(false)
const showIOSInstructions = ref(false)

onMounted(() => {
  if (localStorage.getItem('pwa-dismissed')) return

  const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent)
  const isStandalone = window.matchMedia('(display-mode: standalone)').matches

  if (isStandalone) return

  if (isIOS) {
    showIOSInstructions.value = true
    return
  }

  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault()
    deferredPrompt.value = e
    showInstallButton.value = true
  })
})

async function installApp() {
  if (!deferredPrompt.value) return
  deferredPrompt.value.prompt()
  const { outcome } = await deferredPrompt.value.userChoice
  if (outcome === 'accepted') showInstallButton.value = false
  deferredPrompt.value = null
}

function dismiss() {
  showInstallButton.value = false
  showIOSInstructions.value = false
  localStorage.setItem('pwa-dismissed', '1')
}
</script>

<template>
  <!-- Android / Windows / Desktop Chrome: install button -->
  <div v-if="showInstallButton" class="mt-4 p-3 rounded-lg bg-[#00126D]/8 border border-[#00126D]/20 flex items-center gap-3">
    <div class="flex-1">
      <p class="text-sm font-medium text-[#00126D]">Instalar app</p>
      <p class="text-xs text-gray-500">Accede más rápido desde tu pantalla de inicio</p>
    </div>
    <div class="flex gap-2">
      <button
        @click="installApp"
        class="text-sm px-3 py-1.5 rounded-md bg-[#00126D] text-white hover:opacity-90"
      >
        Instalar
      </button>
      <button @click="dismiss" class="text-sm px-2 py-1.5 text-gray-400 hover:text-gray-600">✕</button>
    </div>
  </div>

  <!-- iOS: manual instructions -->
  <div v-if="showIOSInstructions" class="mt-4 p-3 rounded-lg bg-[#FDB700]/10 border border-[#FDB700]/30">
    <div class="flex items-start justify-between gap-2">
      <div>
        <p class="text-sm font-medium text-[#00126D]">Agrega a pantalla de inicio</p>
        <p class="text-xs text-gray-600 mt-0.5">
          Toca <span class="font-semibold">Compartir</span> <span class="text-base">⎦</span> y luego
          <span class="font-semibold">"Agregar a pantalla de inicio"</span>
        </p>
      </div>
      <button @click="dismiss" class="text-gray-400 hover:text-gray-600 flex-shrink-0">✕</button>
    </div>
  </div>
</template>
