<template>
  <svg viewBox="0 0 56 56" role="img" :aria-label="`Moneda de ${denominacion} pesos`" class="shrink-0 drop-shadow-sm">
    <circle cx="28" cy="28" r="26" :fill="c.aro" :stroke="c.borde" stroke-width="2" />
    <circle cx="28" cy="28" r="17" :fill="c.centro" :stroke="c.borde" stroke-width="1.5" />
    <circle cx="28" cy="28" r="22.5" fill="none" :stroke="c.borde" stroke-opacity="0.35" stroke-width="1" stroke-dasharray="1.5 2.5" />
    <text x="28" y="33.5" font-size="15" font-weight="800" font-family="system-ui, sans-serif" text-anchor="middle" :fill="c.texto">{{ denominacion }}</text>
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ denominacion: number }>()

interface Colores { aro: string; centro: string; borde: string; texto: string }

const PLATA = '#d9dde3'
const ORO = '#d9b45a'

const COLORES: Record<number, Colores> = {
  10: { aro: PLATA, centro: ORO, borde: '#7b7f87', texto: '#5a4515' }, // plata / centro dorado
  5: { aro: ORO, centro: PLATA, borde: '#8a6d1e', texto: '#4a4f57' }, // dorado / centro plata
  2: { aro: PLATA, centro: ORO, borde: '#7b7f87', texto: '#5a4515' },
  1: { aro: PLATA, centro: '#e8ebef', borde: '#7b7f87', texto: '#4a4f57' } // plateada
}

const c = computed<Colores>(() => COLORES[props.denominacion] ?? COLORES[1])
</script>
