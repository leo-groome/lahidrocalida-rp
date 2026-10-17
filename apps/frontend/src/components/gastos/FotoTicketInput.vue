<template>
  <div class="space-y-2">
    <div class="flex items-stretch gap-2">
      <!-- Cámara directa en móvil (capture); en escritorio abre el selector de archivos -->
      <label
        class="flex-1 flex items-center justify-center gap-2 py-3 rounded-2xl bg-[#00126D] text-white font-black text-sm cursor-pointer active:scale-[0.98] transition-all"
        :class="{ 'opacity-40 pointer-events-none': lleno || procesando }"
      >
        <Loader2 v-if="procesando" class="w-4 h-4 animate-spin" />
        <Camera v-else class="w-4 h-4" />
        {{ modelValue.length ? 'Otra foto' : 'Tomar foto del ticket' }}
        <input type="file" accept="image/*" capture="environment" class="hidden" @change="onElegir">
      </label>
      <label
        class="flex items-center justify-center gap-2 px-4 rounded-2xl border-2 border-slate-200 text-slate-500 font-black text-sm cursor-pointer active:scale-[0.98] transition-all"
        :class="{ 'opacity-40 pointer-events-none': lleno || procesando }"
        title="Elegir de la galería"
      >
        <ImageIcon class="w-4 h-4" />
        <span class="sr-only sm:not-sr-only">Galería</span>
        <input type="file" accept="image/*" class="hidden" @change="onElegir">
      </label>
    </div>

    <div v-if="previews.length" class="flex gap-2 overflow-x-auto pt-2 pr-2 pb-1">
      <div v-for="(p, i) in previews" :key="p.url" class="relative flex-shrink-0">
        <span v-if="p.error" class="w-16 h-16 flex items-center text-center text-[10px] bg-slate-100 rounded-xl">Vista previa no disponible</span>
        <button
          v-else
          type="button"
          class="group block rounded-xl focus:outline-none focus:ring-2 focus:ring-[#00126D] focus:ring-offset-2"
          title="Ampliar foto"
          :aria-label="`Ampliar foto ${i + 1} del ticket`"
          @click="fotoAmpliada = p.url"
        >
          <img @error="p.error = true" :src="p.url" :alt="`Foto ${i + 1} del ticket`" class="w-16 h-16 object-cover rounded-xl border border-slate-200">
          <span class="absolute inset-0 rounded-xl bg-slate-900/0 group-hover:bg-slate-900/35 flex items-center justify-center transition-colors">
            <Maximize2 class="w-4 h-4 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
          </span>
        </button>
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

    <Teleport to="body">
      <div
        v-if="fotoAmpliada"
        class="fixed inset-0 z-[80] flex items-center justify-center bg-slate-950/90 p-4 sm:p-8"
        role="dialog"
        aria-modal="true"
        aria-label="Vista ampliada de la foto del ticket"
        @click.self="cerrarAmpliacion"
      >
        <button
          type="button"
          class="absolute right-4 top-4 sm:right-6 sm:top-6 flex h-11 w-11 items-center justify-center rounded-xl bg-white/15 text-white hover:bg-white/25 focus:outline-none focus:ring-2 focus:ring-white"
          title="Cerrar vista ampliada"
          aria-label="Cerrar vista ampliada"
          @click="cerrarAmpliacion"
        >
          <X class="w-5 h-5" />
        </button>
        <img :src="fotoAmpliada" alt="Vista ampliada del ticket" class="max-h-full max-w-full rounded-xl object-contain shadow-2xl">
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { Camera, Image as ImageIcon, Loader2, Maximize2, X } from 'lucide-vue-next'
import { MAX_FOTOS, prepararFoto } from '@/composables/useAdjuntosGasto'

const modelValue = defineModel<File[]>({ default: () => [] })

// URLs de vista previa derivadas de las fotos; se liberan al cambiar/desmontar.
let urls: string[] = []
const previews = computed(() => {
  urls.forEach((u) => URL.revokeObjectURL(u))
  urls = modelValue.value.map((f) => URL.createObjectURL(f))
  return urls.map((url) => reactive({ url, error: false }))
})
onBeforeUnmount(() => urls.forEach((u) => URL.revokeObjectURL(u)))

const procesando = defineModel<boolean>('processing', { default: false })
const lleno = computed(() => modelValue.value.length >= MAX_FOTOS)
const fotoAmpliada = ref<string | null>(null)

// Convierte a WebP al elegir: la vista previa es inmediata y la subida posterior no espera.
async function onElegir(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = '' // permite volver a elegir el mismo archivo
  if (!file || lleno.value || procesando.value) return
  procesando.value = true
  try {
    const lista = await prepararFoto(file)
    if (modelValue.value.length < MAX_FOTOS) modelValue.value = [...modelValue.value, lista]
  } finally {
    procesando.value = false
  }
}

function quitar(i: number) {
  if (fotoAmpliada.value === previews.value[i]?.url) cerrarAmpliacion()
  modelValue.value = modelValue.value.filter((_, idx) => idx !== i)
}

function cerrarAmpliacion() {
  fotoAmpliada.value = null
}

function alPresionarTecla(event: KeyboardEvent) {
  if (event.key === 'Escape' && fotoAmpliada.value) cerrarAmpliacion()
}

onMounted(() => window.addEventListener('keydown', alPresionarTecla))
onBeforeUnmount(() => window.removeEventListener('keydown', alPresionarTecla))
</script>
