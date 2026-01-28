<template>
  <div class="proveedores-view">
    <div class="bg-white rounded-lg shadow">
      <div class="px-6 py-4 border-b border-gray-200">
        <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <h2 class="text-lg font-medium text-gray-900">Proveedores</h2>
          <div class="flex flex-wrap gap-2">
            <button class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm">
              + Nuevo Proveedor
            </button>
          </div>
        </div>
      </div>
      
      <!-- Lista de proveedores -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-6">
        <div 
          v-for="proveedor in proveedores" 
          :key="proveedor.id"
          class="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
        >
          <div class="flex justify-between items-start">
            <div>
              <h3 class="font-medium text-gray-900">{{ proveedor.nombre }}</h3>
              <p class="text-sm text-gray-500 mt-1">{{ proveedor.telefono }}</p>
            </div>
            <button class="text-blue-600 hover:text-blue-800 text-sm">
              Editar
            </button>
          </div>
          <div class="mt-2 text-xs text-gray-500">
            <p>{{ proveedor.direccion }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

// Datos de ejemplo
const proveedores = ref([
  {
    id: 1,
    nombre: 'Distribuidora ABC',
    telefono: '555-1234',
    direccion: 'Calle Principal 123'
  },
  {
    id: 2,
    nombre: 'Comercial XYZ',
    telefono: '555-5678',
    direccion: 'Avenida Siempre Viva 456'
  },
  {
    id: 3,
    nombre: 'Alimentos Gourmet',
    telefono: '555-9012',
    direccion: 'Boulevard Central 789'
  }
])
</script>