<template>
  <div class="flex items-center gap-3 px-3 py-2 bg-white border-b border-slate-100 last:border-b-0">
    <!-- Visual -->
    <div class="w-[84px] sm:w-[104px] flex justify-center shrink-0">
      <BilleteSvg v-if="esBillete" :denominacion="denominacion" class="w-[84px] sm:w-[104px] h-auto" />
      <MonedaSvg v-else :denominacion="denominacion" class="w-10 sm:w-11 h-auto" />
    </div>

    <!-- Etiqueta + subtotal -->
    <div class="min-w-0 flex-1">
      <div class="text-base font-black text-slate-800 leading-tight">${{ denominacion.toLocaleString('es-MX') }}</div>
      <div class="text-xs font-bold tabular-nums" :class="modelValue > 0 ? 'text-[#00126D]' : 'text-slate-400'">
        ${{ subtotal.toLocaleString('es-MX', { minimumFractionDigits: 2 }) }}
      </div>
    </div>

    <!-- Stepper -->
    <div class="flex items-center gap-1 shrink-0">
      <button
        type="button"
        :disabled="modelValue <= 0"
        :aria-label="`Quitar uno de ${denominacion} pesos`"
        class="w-11 h-11 flex items-center justify-center rounded-xl bg-white border border-slate-300 text-rose-600 text-2xl font-bold hover:bg-rose-50 active:bg-rose-100 disabled:opacity-40 disabled:cursor-not-allowed focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00126D] transition-colors"
        @click="emit('update:modelValue', Math.max(0, modelValue - 1))"
      >&minus;</button>
      <input
        :value="modelValue"
        type="number"
        inputmode="numeric"
        min="0"
        step="1"
        :aria-label="`Cantidad de ${denominacion} pesos`"
        class="w-14 h-11 text-center text-lg font-black text-slate-800 bg-slate-50 border border-slate-300 rounded-xl appearance-none focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00126D] focus:bg-white"
        @focus="($event.target as HTMLInputElement).select()"
        @input="onInput"
      />
      <button
        type="button"
        :aria-label="`Agregar uno de ${denominacion} pesos`"
        class="w-11 h-11 flex items-center justify-center rounded-xl bg-white border border-slate-300 text-emerald-600 text-2xl font-bold hover:bg-emerald-50 active:bg-emerald-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00126D] transition-colors"
        @click="emit('update:modelValue', modelValue + 1)"
      >+</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import BilleteSvg from './BilleteSvg.vue'
import MonedaSvg from './MonedaSvg.vue'

const props = defineProps<{
  denominacion: number
  modelValue: number
}>()

const emit = defineEmits<{
  'update:modelValue': [value: number]
}>()

const esBillete = computed(() => props.denominacion >= 20)
const subtotal = computed(() => props.denominacion * (props.modelValue || 0))

function onInput(e: Event) {
  const n = Math.floor(Number((e.target as HTMLInputElement).value))
  const valor = Number.isFinite(n) && n > 0 ? n : 0
  emit('update:modelValue', valor)
  // Normaliza lo mostrado si se tecleó algo inválido (negativo, vacío, decimal)
  ;(e.target as HTMLInputElement).value = String(valor)
}
</script>

<style scoped>
input[type='number']::-webkit-outer-spin-button,
input[type='number']::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
input[type='number'] {
  -moz-appearance: textfield;
  appearance: textfield;
}
</style>
