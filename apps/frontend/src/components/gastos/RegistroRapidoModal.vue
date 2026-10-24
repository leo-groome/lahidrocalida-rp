<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 z-[120] flex items-end sm:items-center justify-center bg-slate-900/50 backdrop-blur-sm sm:p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="registro-rapido-titulo"
      @click.self="emit('close')"
    >
      <div class="bg-slate-50 w-full sm:max-w-xl max-h-[92dvh] sm:max-h-[90dvh] rounded-t-3xl sm:rounded-3xl shadow-2xl flex flex-col overflow-hidden">
        <header class="flex items-center justify-between gap-3 px-4 py-3 bg-white border-b border-slate-100 flex-shrink-0">
          <div class="min-w-0">
            <p class="text-xs font-black tracking-widest text-slate-400 uppercase leading-none">Caja</p>
            <h2 id="registro-rapido-titulo" class="text-base font-black text-slate-900 tracking-tight">Registrar gasto</h2>
          </div>
          <button
            type="button"
            class="w-11 h-11 flex items-center justify-center rounded-xl bg-slate-100 text-slate-500 hover:bg-slate-900 hover:text-white transition-all flex-shrink-0"
            title="Cerrar (Esc)"
            aria-label="Cerrar"
            @click="emit('close')"
          >
            <X class="w-5 h-5" />
          </button>
        </header>

        <div class="flex-1 overflow-y-auto overscroll-contain px-4 pt-4 pb-5">
          <div
            v-if="sinTurno"
            class="mb-4 flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-bold text-amber-700"
            role="alert"
          >
            <AlertTriangle class="w-4 h-4 mt-0.5 flex-shrink-0" />
            Inicia un turno para registrar gastos de caja
          </div>
          <RegistroRapidoForm
            :turno-id="turnoId"
            :bloqueado="sinTurno"
            forzar-efectivo
            @saved="(id) => emit('saved', id)"
          />
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted } from 'vue'
import { AlertTriangle, X } from 'lucide-vue-next'
import RegistroRapidoForm from '@/components/gastos/RegistroRapidoForm.vue'

const props = defineProps<{ turnoId?: number | null }>()
const emit = defineEmits<{
  close: []
  /** Gasto confirmado por el servidor (id del pendiente en cola). */
  saved: [id: string]
}>()

const sinTurno = computed(() => props.turnoId == null)

function onKeydown(e: KeyboardEvent) {
  if (e.key !== 'Escape') return
  e.stopPropagation()
  emit('close')
}
// capture: el modal gana a los atajos globales de la vista que lo monta
onMounted(() => window.addEventListener('keydown', onKeydown, true))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown, true))
</script>
