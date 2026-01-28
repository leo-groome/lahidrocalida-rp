<template>
  <div class="categorias-view">
    <div class="bg-white rounded-lg shadow">
      <div class="px-6 py-4 border-b border-gray-200">
        <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <h2 class="text-lg font-medium text-gray-900">Categorías de Artículos</h2>
          <div class="flex flex-wrap gap-2">
            <button class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm">
              + Nueva Categoría
            </button>
          </div>
        </div>
      </div>
      
      <!-- Lista de categorías -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-6">
        <div 
          v-for="categoria in categorias" 
          :key="categoria.id"
          class="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
        >
          <div class="flex justify-between items-center">
            <h3 class="font-medium text-gray-900">{{ categoria.nombre }}</h3>
            <button class="text-blue-600 hover:text-blue-800 text-sm">
              Editar
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

// Datos de ejemplo
const categorias = ref([
  { id: 1, nombre: 'Verduras' },
  { id: 2, nombre: 'Bebidas' },
  { id: 3, nombre: 'Carnes' },
  { id: 4, nombre: 'Lácteos' },
  { id: 5, nombre: 'Frutas' },
  { id: 6, nombre: 'Panadería' }
])
</script>