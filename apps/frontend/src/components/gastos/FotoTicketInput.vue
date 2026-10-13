<template>
  <div class="space-y-2">
    <div class="flex items-stretch gap-2">
      <!-- Cámara directa en móvil (capture); en escritorio abre el selector de archivos -->
      <label
        class="flex-1 flex items-center justify-center gap-2 py-3 rounded-2xl bg-[#00126D] text-white font-black text-sm cursor-pointer active:scale-[0.98] transition-all"
        :class="{ 'opacity-40 pointer-events-none': lleno }"
      >
        <Loader2 v-if="procesando" class="w-4 h-4 animate-spin" />
        <Camera v-else class="w-4 h-4" />
        {{ modelValue.length ? 'Otra foto' : 'Tomar foto del ticket' }}
        <input type="file" accept="image/*" capture="environment" class="hidden" @change="onElegir">
      </label>
      <label
        class="flex items-center justify-center gap-2 px-4 rounded-2xl border-2 border-slate-200 text-slate-500 font-black text-sm cursor-pointer active:scale-[0.98] transition-all"
        :class="{ 'opacity-40 pointer-events-none': lleno }"
        title="Elegir de la galería"
      >
        <ImageIcon class="w-4 h-4" />
        <span class="sr-only sm:not-sr-only">Galería</span>
        <input type="file" accept="image/*" class="hidden" @change="onElegir">
      </label>
    </div>

    <div v-if="previews.length" class="flex gap-2 overflow-x-auto pt-2 pr-2 pb-1">
      <div v-for="(p, i) in previews" :key="p.url" class="relative flex-shrink-0">
        <img :src="p.url" alt="Ticket" class="w-16 h-16 object-cover rounded-xl border border-slate-200">
        <button
          type="button"
          @click="quitar(i)"
          class="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-slate-900 text-white flex items-center justify-center"
          title="Quitar foto"
        >
          <X class="w-3 h-3" />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { Camera, Image as ImageIcon, Loader2, X } from 'lucide-vue-next'
import { MAX_FOTOS, prepararFoto } from '@/composables/useAdjuntosGasto'

const modelValue = defineModel<File[]>({ default: () => [] })

// URLs de vista previa derivadas de las fotos; se liberan al cambiar/desmontar.
let urls: string[] = []
const previews = computed(() => {
  urls.forEach((u) => URL.revokeObjectURL(u))
  urls = modelValue.value.map((f) => URL.createObjectURL(f))
  return urls.map((url) => ({ url }))
})
onBeforeUnmount(() => urls.forEach((u) => URL.revokeObjectURL(u)))

const procesando = ref(false)
const lleno = computed(() => modelValue.value.length >= MAX_FOTOS)

// Convierte a WebP al elegir: la vista previa es inmediata y la subida posterior no espera.
async function onElegir(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = '' // permite volver a elegir el mismo archivo
  if (!file || lleno.value) return
  procesando.value = true
  try {
    const lista = await prepararFoto(file)
    if (modelValue.value.length < MAX_FOTOS) modelValue.value = [...modelValue.value, lista]
  } finally {
    procesando.value = false
  }
}

function quitar(i: number) {
  modelValue.value = modelValue.value.filter((_, idx) => idx !== i)
}
</script>
