<template>
  <div
    class="fixed inset-0 z-[70] bg-slate-900/80 backdrop-blur-sm flex items-center justify-center p-0 sm:p-6"
    @click.self="$emit('close')"
  >
    <div class="bg-white w-full h-full sm:h-auto sm:max-h-[90vh] sm:max-w-2xl sm:rounded-[2rem] overflow-hidden flex flex-col">
      <div class="flex items-center justify-between px-5 py-4 border-b border-slate-100">
        <h3 class="text-sm font-black text-slate-800 uppercase tracking-widest">Ticket del gasto #{{ gastoId }}</h3>
        <button @click="$emit('close')" class="w-9 h-9 rounded-xl bg-slate-100 text-slate-500 flex items-center justify-center" title="Cerrar">
          <X class="w-4 h-4" />
        </button>
      </div>

      <div class="flex-1 overflow-y-auto p-4 space-y-4">
        <p v-if="cargando" class="text-center text-sm font-bold text-slate-400 py-10">Cargando...</p>
        <p v-else-if="error" class="text-center text-sm font-bold text-rose-500 py-10">{{ error }}</p>
        <template v-for="f in fotos" :key="f.id">
        <p v-if="f.error" class="text-sm text-amber-700">Esta foto no se puede mostrar en este navegador.</p>
        <img v-else @error="f.error = true"
          :key="f.id"
          :src="f.url"
          alt="Ticket"
          class="w-full rounded-2xl border border-slate-200"
        >
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { X } from 'lucide-vue-next'
import { api } from '@/api/client'
import { urlAdjunto } from '@/composables/useAdjuntosGasto'

const props = defineProps<{ gastoId: number }>()
defineEmits(['close'])

const fotos = ref<Array<{ id: number; url: string; error?: boolean }>>([])
const cargando = ref(true)
const error = ref('')

onMounted(async () => {
  try {
    const { data } = await api.get(`/gastos/${props.gastoId}/adjuntos`)
    fotos.value = await Promise.all(
      data.map(async (a: { id: number }) => ({ id: a.id, url: await urlAdjunto(props.gastoId, a.id) })),
    )
    if (!fotos.value.length) error.value = 'Este gasto no tiene fotos.'
  } catch {
    error.value = 'No se pudieron cargar las fotos.'
  } finally {
    cargando.value = false
  }
})

onBeforeUnmount(() => fotos.value.forEach((f) => URL.revokeObjectURL(f.url)))
</script>
