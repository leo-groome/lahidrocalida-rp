<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Platillo } from '../types'

interface Props {
  color: 'Verde' | 'Blanco' | 'Rojo'
  platillos: Platillo[]
  isOpen: boolean
}

interface Emit {
  (e: 'close'): void
  (e: 'select', platillo: Platillo): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emit>()

const selectedTamaño = ref<string | null>(null)
const selectedProteína = ref<string | null>(null)

const tamaños = ['Infantil', 'Regular', 'Grande']
const proteínas = ['Puerco', 'Pollo']

const tamañosDisponibles = computed(() => {
  return tamaños.filter(t => 
    props.platillos.some(p => p.nombre.includes(t))
  )
})

const proteínasDisponibles = computed(() => {
  return proteínas.filter(p => 
    props.platillos.some(pl => pl.nombre.includes(p))
  )
})

const selectedPlatillo = computed(() => {
  if (!selectedTamaño.value || !selectedProteína.value) return null
  return props.platillos.find(p => 
    p.nombre.includes(selectedTamaño.value!) && 
    p.nombre.includes(selectedProteína.value!)
  )
})

function handleSelect() {
  if (selectedPlatillo.value) {
    emit('select', selectedPlatillo.value)
    resetSelection()
  }
}

function resetSelection() {
  selectedTamaño.value = null
  selectedProteína.value = null
}

function handleClose() {
  emit('close')
  resetSelection()
}
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 flex items-end justify-center z-50 pointer-events-none">
    <div class="bg-gradient-to-b from-white to-blue-50 rounded-t-3xl p-8 w-full max-w-2xl pointer-events-auto shadow-2xl">
      <!-- Header -->
      <div class="flex items-center justify-between mb-8">
        <div>
          <h2 class="text-2xl font-bold text-[#00126D]">🍲 Pozole {{ color }}</h2>
          <p class="text-xs text-gray-600 mt-1">Selecciona tamaño y proteína</p>
        </div>
        <button @click="handleClose" class="text-gray-400 hover:text-gray-600 text-3xl leading-none transition">×</button>
      </div>

      <!-- Tamaño Selection -->
      <div class="mb-8">
        <label class="block text-sm font-bold text-[#00126D] mb-3">📏 Tamaño</label>
        <div class="flex gap-3 flex-wrap">
          <button
            v-for="t in tamañosDisponibles"
            :key="t"
            @click="selectedTamaño = t"
            :class="[
              'px-5 py-3 rounded-lg border-2 text-sm font-bold transition-all',
              selectedTamaño === t
                ? 'bg-[#00126D] text-white border-[#00126D] shadow-md'
                : 'bg-white border-gray-200 text-[#00126D] hover:border-[#00126D] hover:shadow-sm'
            ]"
          >
            {{ t }}
          </button>
        </div>
      </div>

      <!-- Proteína Selection -->
      <div class="mb-8">
        <label class="block text-sm font-bold text-[#00126D] mb-3">🍗 Proteína</label>
        <div class="flex gap-3 flex-wrap">
          <button
            v-for="p in proteínasDisponibles"
            :key="p"
            @click="selectedProteína = p"
            :class="[
              'px-5 py-3 rounded-lg border-2 text-sm font-bold transition-all',
              selectedProteína === p
                ? 'bg-[#FDB700] text-[#00126D] border-[#FDB700] shadow-md'
                : 'bg-white border-gray-200 text-[#00126D] hover:border-[#FDB700] hover:shadow-sm'
            ]"
          >
            {{ p }}
          </button>
        </div>
      </div>

      <!-- Price and Action -->
      <div v-if="selectedPlatillo" class="bg-gradient-to-r from-[#00126D] to-[#001a4d] rounded-xl p-6 text-white">
        <div class="flex items-center justify-between">
          <div>
            <div class="text-sm text-blue-100">{{ selectedPlatillo.nombre }}</div>
            <div class="text-3xl font-black mt-1">$ {{ Number(selectedPlatillo.precio).toFixed(2) }}</div>
          </div>
          <button
            @click="handleSelect"
            class="px-8 py-4 rounded-lg bg-[#FDB700] text-[#00126D] hover:bg-yellow-400 font-bold text-lg transition-all shadow-lg hover:shadow-xl active:scale-95"
          >
            ✓ Agregar
          </button>
        </div>
      </div>

      <!-- Empty State -->
      <div v-else class="text-center py-8 text-gray-500 bg-gray-50 rounded-lg">
        <p class="text-lg font-semibold">Selecciona tamaño y proteína</p>
      </div>
    </div>
  </div>
</template>
