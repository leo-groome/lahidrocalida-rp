<template>
  <div class="articulos-view">
    <div class="bg-white rounded-lg shadow">
      <div class="px-6 py-4 border-b border-gray-200">
        <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <h2 class="text-lg font-medium text-gray-900">Artículos</h2>
          <div class="flex flex-wrap gap-2">
            <button class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm">
              + Nuevo Artículo
            </button>
          </div>
        </div>
      </div>
      
      <!-- Filtros -->
      <div class="px-6 py-4 border-b border-gray-200 bg-gray-50">
        <div class="flex flex-col md:flex-row md:items-center gap-4">
          <div class="flex-1">
            <input 
              type="text" 
              placeholder="Buscar artículos..." 
              class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
              v-model="searchTerm"
            >
          </div>
          <div>
            <select 
              class="border border-gray-300 rounded-md px-3 py-2 text-sm"
              v-model="selectedCategoria"
            >
              <option value="">Todas las categorías</option>
              <option v-for="categoria in categorias" :key="categoria.id" :value="categoria.id">
                {{ categoria.nombre }}
              </option>
            </select>
          </div>
        </div>
      </div>
      
      <!-- Lista de artículos -->
      <div class="divide-y divide-gray-200">
        <div 
          v-for="articulo in articulosFiltrados" 
          :key="articulo.id"
          class="px-6 py-4 hover:bg-gray-50"
        >
          <div class="flex items-center justify-between">
            <div>
              <h3 class="font-medium text-gray-900">{{ articulo.nombre }}</h3>
              <div class="mt-1 flex flex-wrap items-center gap-2">
                <span class="text-sm text-gray-500 bg-gray-100 px-2 py-1 rounded">
                  {{ articulo.categoria }}
                </span>
                <span class="text-sm text-gray-500">
                  ${{ articulo.costo_estandar }} / {{ articulo.unidad }}
                </span>
              </div>
            </div>
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
import { ref, computed } from 'vue'

// Datos de ejemplo
const searchTerm = ref('')
const selectedCategoria = ref('')

const articulos = ref([
  {
    id: 1,
    nombre: 'Tomate',
    categoria: 'Verduras',
    costo_estandar: 25.50,
    unidad: 'kg'
  },
  {
    id: 2,
    nombre: 'Cebolla',
    categoria: 'Verduras',
    costo_estandar: 20.00,
    unidad: 'kg'
  },
  {
    id: 3,
    nombre: 'Papa',
    categoria: 'Verduras',
    costo_estandar: 15.00,
    unidad: 'kg'
  },
  {
    id: 4,
    nombre: 'Refresco',
    categoria: 'Bebidas',
    costo_estandar: 18.50,
    unidad: 'litro'
  }
])

const categorias = ref([
  { id: 1, nombre: 'Verduras' },
  { id: 2, nombre: 'Bebidas' },
  { id: 3, nombre: 'Carnes' },
  { id: 4, nombre: 'Lácteos' }
])

// Filtrado de artículos
const articulosFiltrados = computed(() => {
  return articulos.value.filter(articulo => {
    const matchesSearch = articulo.nombre.toLowerCase().includes(searchTerm.value.toLowerCase())
    const matchesCategoria = selectedCategoria.value ? 
      articulo.categoria === selectedCategoria.value : true
    return matchesSearch && matchesCategoria
  })
})
</script>