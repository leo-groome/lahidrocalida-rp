<template>
  <RouterLink v-if="count" to="/rapido" class="inline-flex min-h-11 items-center rounded-xl px-2 text-xs font-bold text-amber-700 bg-amber-50" aria-label="Recuperar gastos pendientes">
    Pendientes {{ count }}
  </RouterLink>
</template>
<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useGastosPendientesStore } from '@/stores/gastos-pendientes'
const cola = useGastosPendientesStore()
const count = computed(() => cola.pendientes.filter(p => p.estado !== 'ok').length)
onMounted(() => { void cola.cargar().catch(() => {}) })
</script>
