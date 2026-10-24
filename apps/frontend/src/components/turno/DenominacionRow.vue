<template>
  <div class="flex flex-col items-center gap-1.5 rounded-xl border border-slate-200 bg-white p-2">
    <div class="h-12 flex items-center justify-center">
      <BilleteSvg v-if="esBillete" :denominacion="denominacion" class="w-[88px] h-auto" />
      <MonedaSvg v-else :denominacion="denominacion" class="w-10 h-auto" />
    </div>

    <div class="flex items-baseline gap-2 leading-none">
      <span class="text-base font-black text-slate-800">${{ denominacion.toLocaleString('es-MX') }}</span>
      <span class="text-[11px] font-bold tabular-nums" :class="modelValue > 0 ? 'text-[#00126D]' : 'text-slate-400'">
        ${{ subtotal.toLocaleString('es-MX') }}
      </span>
    </div>

    <div class="flex items-center gap-1 w-full justify-center">
      <button
        type="button"
        :disabled="modelValue <= 0"
        :aria-label="`Quitar uno de ${denominacion} pesos`"
        class="w-10 h-10 flex items-center justify-center rounded-lg bg-white border border-slate-300 text-rose-600 text-xl font-bold hover:bg-rose-50 active:bg-rose-100 disabled:opacity-40 disabled:cursor-not-allowed focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00126D] transition-colors"
        @click="emit('update:modelValue', Math.max(0, modelValue - 1))"
      >&minus;</button>
      <input
        :value="modelValue"
        type="number"
        inputmode="numeric"
        min="0"
        step="1"
        :aria-label="`Cantidad de ${denominacion} pesos`"
        class="w-12 h-10 text-center text-base font-black text-slate-800 bg-slate-50 border border-slate-300 rounded-lg appearance-none focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00126D] focus:bg-white"
        @focus="($event.target as HTMLInputElement).select()"
        @input="onInput"
      />
      <button
        type="button"
        :aria-label="`Agregar uno de ${denominacion} pesos`"
        class="w-10 h-10 flex items-center justify-center rounded-lg bg-white border border-slate-300 text-emerald-600 text-xl font-bold hover:bg-emerald-50 active:bg-emerald-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00126D] transition-colors"
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
