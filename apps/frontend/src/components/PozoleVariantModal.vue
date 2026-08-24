<script setup lang="ts">
import { ref, computed } from 'vue'
import type { PlatilloResponse } from '../types'

interface Props {
  platillos: PlatilloResponse[]
  isOpen: boolean
}

interface Emit {
  (e: 'close'): void
  (e: 'select', payload: { platillo: PlatilloResponse; cantidad: number; proteina: string; tamano: string; tipo_pozole: string }): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emit>()

const selectedTamaño = ref<string | null>(null)
const selectedProteína = ref<string | null>(null)
const selectedColor = ref<'Verde' | 'Blanco' | 'Rojo' | null>(null)
const cantidad = ref(1)

const tamaños = ['Infantil', 'Regular', 'Grande']
const proteínas = ['Puerco', 'Pollo', 'Surtida', 'Mixta']
const colores = ['Verde', 'Blanco', 'Rojo'] as const

const tamañosDisponibles = computed(() => {
  return tamaños.filter(t => 
    props.platillos.some(p => p.nombre.toLowerCase().includes(t.toLowerCase()) && p.categoria === 'Pozole')
  )
})

const proteínasDisponibles = computed(() => {
  return proteínas.filter(p => 
    props.platillos.some(pl => pl.nombre.toLowerCase().includes(p.toLowerCase()) && pl.categoria === 'Pozole')
  )
})

const coloresDisponibles = computed(() => {
  return colores.filter(c => 
    props.platillos.some(p => p.nombre.toLowerCase().includes(c.toLowerCase()) && p.categoria === 'Pozole')
  )
})

const selectedPlatillo = computed(() => {
  if (!selectedTamaño.value || !selectedProteína.value || !selectedColor.value) return null
  
  // Buscar un platillo que contenga los tres términos en su nombre
  // Esto es más robusto que un formato de string exacto
  return props.platillos.find(p => {
    if (p.categoria !== 'Pozole') return false
    const nombre = p.nombre.toLowerCase()
    return nombre.includes(selectedTamaño.value!.toLowerCase()) &&
           nombre.includes(selectedColor.value!.toLowerCase()) &&
           nombre.includes(selectedProteína.value!.toLowerCase())
  })
})

function handleSelect() {
  if (selectedPlatillo.value && selectedProteína.value && selectedTamaño.value && selectedColor.value) {
    emit('select', {
      platillo: selectedPlatillo.value,
      cantidad: cantidad.value,
      proteina: selectedProteína.value,
      tamano: selectedTamaño.value,
      tipo_pozole: selectedColor.value
    })
    handleClose()
  }
}

function resetSelection() {
  selectedTamaño.value = null
  selectedProteína.value = null
  selectedColor.value = null
  cantidad.value = 1
}

function handleClose() {
  emit('close')
  resetSelection()
}
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 flex items-center justify-center z-[150]">
    <!-- Backdrop -->
    <div class="absolute inset-0 bg-black bg-opacity-75" @click="handleClose"></div>
    
    <!-- Modal Content -->
    <div class="relative bg-white rounded-2xl p-8 max-w-2xl w-full mx-4 shadow-2xl overflow-y-auto max-h-[90vh]">
      <!-- Header -->
      <div class="flex items-center justify-between mb-8">
        <div class="flex items-center gap-3">
          <span class="text-4xl">🍲</span>
          <h2 class="text-2xl font-bold text-[#00126D]">Pozoles</h2>
        </div>
        <button @click="handleClose" class="text-gray-400 hover:text-gray-600 text-3xl leading-none transition">×</button>
      </div>

      <!-- Proteína Selection -->
      <div class="mb-8">
        <div class="flex items-center gap-2 mb-3">
          <span class="text-xl">🍗</span>
          <label class="text-sm font-bold text-[#00126D]">Proteína</label>
        </div>
        <div class="flex gap-3 flex-wrap">
          <button
            v-for="p in proteínas"
            :key="p"
            @click="selectedProteína = p"
            :class="[
              'px-5 py-3 rounded-lg border-2 text-sm font-bold transition-all',
              selectedProteína === p
                ? 'bg-[#00126D] text-white border-[#00126D] shadow-md'
                : 'bg-white border-gray-200 text-[#00126D] hover:border-[#00126D] hover:shadow-sm'
            ]"
          >
            {{ p }}
          </button>
        </div>
      </div>

      <!-- Tamaño Selection -->
      <div class="mb-8">
        <div class="flex items-center gap-2 mb-3">
          <span class="text-xl">📏</span>
          <label class="text-sm font-bold text-[#00126D]">Tamaño</label>
        </div>
        <div class="flex gap-3 flex-wrap">
          <button
            v-for="t in tamaños"
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

      <!-- Tipo (Color) Selection -->
      <div class="mb-8">
        <div class="flex items-center gap-2 mb-3">
          <span class="text-xl">🎨</span>
          <label class="text-sm font-bold text-[#00126D]">Tipos de pozole</label>
        </div>
        <div class="flex gap-3 flex-wrap">
          <button
            v-for="c in colores"
            :key="c"
            @click="selectedColor = c"
            :class="[
              'px-5 py-3 rounded-lg border-2 text-sm font-bold transition-all',
              selectedColor === c
                ? (c === 'Verde' ? 'bg-green-600 border-green-600 text-white' : 
                   c === 'Rojo' ? 'bg-red-600 border-red-600 text-white' : 
                   'bg-gray-200 border-gray-400 text-gray-800')
                : 'bg-white border-gray-200 text-[#00126D] hover:shadow-sm'
            ]"
          >
            {{ c }}
          </button>
        </div>
      </div>

      <!-- Footer: Price and Action -->
      <div v-if="selectedPlatillo" class="bg-[#00126D] rounded-xl p-6 text-white animate-in fade-in zoom-in duration-300">
        <div class="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div class="flex-1 w-full">
            <div class="text-xs text-blue-200 uppercase tracking-wider font-bold mb-1">Total a pagar</div>
            <div class="text-sm text-blue-100 mb-1">{{ selectedPlatillo.nombre }}</div>
            <div class="text-3xl font-black">$ {{ (Number(selectedPlatillo.precio) * cantidad).toFixed(2) }}</div>
          </div>
          
          <div class="flex items-center gap-4 bg-white/10 p-2 rounded-lg">
            <button @click="cantidad > 1 && cantidad--" class="w-10 h-10 rounded bg-white/20 hover:bg-white/30 flex items-center justify-center font-bold text-xl">−</button>
            <span class="text-2xl font-black w-8 text-center">{{ cantidad }}</span>
            <button @click="cantidad++" class="w-10 h-10 rounded bg-white/20 hover:bg-white/30 flex items-center justify-center font-bold text-xl">+</button>
          </div>

          <button
            @click="handleSelect"
            class="w-full sm:w-auto px-5 py-3 rounded-lg bg-[#FDB700] text-[#00126D] hover:bg-yellow-400 font-bold text-base transition-all shadow-lg hover:shadow-xl active:scale-95 flex items-center justify-center gap-2"
          >
            <span>✓</span> Agregar
          </button>
        </div>
      </div>

      <!-- Missing Selection Message -->
      <div v-else class="text-center py-6 text-gray-400 bg-gray-50 rounded-xl border-2 border-dashed border-gray-200">
        <p class="font-medium">Selecciona proteína, tamaño y tipo para continuar</p>
      </div>
    </div>
  </div>
</template>
