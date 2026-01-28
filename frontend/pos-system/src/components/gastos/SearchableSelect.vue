<template>
  <div class="searchable-select">
    <div class="relative">
      <input
        v-model="searchTerm"
        type="text"
        :placeholder="placeholder"
        class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        @focus="showOptions = true"
        @blur="handleBlur"
        @input="filterOptions"
      >
      
      <div 
        v-if="showOptions" 
        class="absolute z-10 mt-1 w-full bg-white shadow-lg rounded-md py-1 overflow-auto"
        style="max-height: 15rem;"
        @mousedown="preventBlur = true"
      >
        <div 
          v-for="option in filteredOptions" 
          :key="option.id"
          class="cursor-default select-none py-2 px-3 text-sm hover:bg-blue-100"
          @click="selectOption(option)"
        >
          <div class="font-medium text-gray-900">{{ option.nombre }}</div>
          <div class="text-gray-500 text-xs">{{ option.descripcion }}</div>
        </div>
        <div 
          v-if="filteredOptions.length === 0" 
          class="py-2 px-3 text-sm text-gray-500"
        >
          No se encontraron resultados
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: [String, Number],
    default: null
  },
  options: {
    type: Array,
    default: () => []
  },
  placeholder: {
    type: String,
    default: 'Seleccionar opción'
  }
})

const emit = defineEmits(['update:modelValue'])

const searchTerm = ref('')
const showOptions = ref(false)
const preventBlur = ref(false)

const filteredOptions = computed(() => {
  if (!searchTerm.value) return props.options
  
  return (props.options as any[]).filter(option => 
    option.nombre.toLowerCase().includes(searchTerm.value.toLowerCase())
  )
})

const selectOption = (option: any) => {
  emit('update:modelValue', option.id)
  searchTerm.value = option.nombre
  showOptions.value = false
}

const handleBlur = () => {
  if (!preventBlur.value) {
    showOptions.value = false
  }
  preventBlur.value = false
}

const filterOptions = () => {
  showOptions.value = true
}
</script>