<template>
  <svg viewBox="0 0 120 56" role="img" :aria-label="`Billete de ${denominacion} pesos`" class="shrink-0 drop-shadow-sm">
    <rect x="1" y="1" width="118" height="54" rx="5" :fill="paleta.fondo" :stroke="paleta.borde" stroke-width="2" />
    <rect x="6" y="6" width="108" height="44" rx="3" fill="none" :stroke="paleta.borde" stroke-opacity="0.45" stroke-width="1" />
    <!-- Ornamento central -->
    <circle cx="60" cy="28" r="17" :fill="paleta.acento" fill-opacity="0.35" />
    <circle cx="60" cy="28" r="12" fill="none" :stroke="paleta.borde" stroke-opacity="0.5" stroke-width="1" />
    <path d="M10 44 Q35 30 60 44 T110 44" fill="none" :stroke="paleta.borde" stroke-opacity="0.3" stroke-width="1.5" />
    <!-- Denominación -->
    <text x="13" y="21" font-size="13" font-weight="800" font-family="system-ui, sans-serif" :fill="paleta.texto">{{ denominacion }}</text>
    <text x="107" y="49" font-size="13" font-weight="800" font-family="system-ui, sans-serif" text-anchor="end" :fill="paleta.texto">{{ denominacion }}</text>
    <text x="60" y="33" font-size="11" font-weight="800" font-family="system-ui, sans-serif" text-anchor="middle" :fill="paleta.texto">$</text>
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ denominacion: number }>()

interface Paleta { fondo: string; borde: string; acento: string; texto: string }

const PALETAS: Record<number, Paleta> = {
  1000: { fondo: '#f9d5de', borde: '#9d2449', acento: '#c9577a', texto: '#6b1230' },
  500: { fondo: '#cfe0f5', borde: '#1d4f91', acento: '#4a86c9', texto: '#12376b' },
  200: { fondo: '#d4efd6', borde: '#2e7d32', acento: '#5fb564', texto: '#1b5e20' },
  100: { fondo: '#f8d0d0', borde: '#c62828', acento: '#e56b6b', texto: '#8e1a1a' },
  50: { fondo: '#ecd0ee', borde: '#9c27b0', acento: '#c869d6', texto: '#6a1b7a' },
  20: { fondo: '#d3ecf8', borde: '#2a8bc7', acento: '#6cbbe6', texto: '#17618f' }
}

const paleta = computed<Paleta>(() => PALETAS[props.denominacion] ?? PALETAS[20])
</script>
