<template>
  <div class="gastos-view">
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-900">Gestión de Gastos</h1>
      <p class="text-gray-600 mt-1">Registro y control de gastos del negocio</p>
    </div>

    <!-- Pestañas de navegación -->
    <div class="bg-white rounded-lg shadow mb-6">
      <div class="border-b border-gray-200">
        <nav class="flex -mb-px">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="activeTab = tab.id"
            :class="[
              activeTab === tab.id
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
              'whitespace-nowrap py-4 px-6 border-b-2 font-medium'
            ]"
          >
            {{ tab.name }}
          </button>
        </nav>
      </div>
    </div>

    <!-- Contenido según pestaña activa -->
    <div v-if="activeTab === 'resumen'">
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="text-lg font-medium text-gray-900 mb-4">Resumen de Gastos</h3>
          <div class="grid grid-cols-2 gap-4">
            <div class="bg-blue-50 p-4 rounded-lg">
              <p class="text-sm text-gray-600">Gastos este mes</p>
              <p class="text-2xl font-bold text-blue-600">$12,450.00</p>
            </div>
            <div class="bg-green-50 p-4 rounded-lg">
              <p class="text-sm text-gray-600">Proveedores activos</p>
              <p class="text-2xl font-bold text-green-600">24</p>
            </div>
          </div>
        </div>
        
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="text-lg font-medium text-gray-900 mb-4">Gastos por categoría</h3>
          <div class="space-y-3">
            <div v-for="categoria in categoriasGastos" :key="categoria.nombre" class="flex items-center justify-between">
              <span class="text-gray-600">{{ categoria.nombre }}</span>
              <div class="flex items-center">
                <span class="text-gray-900 mr-2">${{ categoria.total }}</span>
                <span class="text-sm text-gray-500">({{ categoria.porcentaje }}%)</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="activeTab === 'historial'">
      <GastosHistorial />
    </div>

    <div v-if="activeTab === 'proveedores'">
      <ProveedoresView />
    </div>

    <div v-if="activeTab === 'articulos'">
      <ArticulosView />
    </div>

    <div v-if="activeTab === 'categorias'">
      <CategoriasView />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import GastosHistorial from './GastosHistorial.vue'
import ProveedoresView from './ProveedoresView.vue'
import ArticulosView from './ArticulosView.vue'
import CategoriasView from './CategoriasView.vue'

// Pestañas
const tabs = [
  { id: 'resumen', name: 'Resumen' },
  { id: 'historial', name: 'Historial' },
  { id: 'proveedores', name: 'Proveedores' },
  { id: 'articulos', name: 'Artículos' },
  { id: 'categorias', name: 'Categorías' }
]

const activeTab = ref('resumen')

// Datos de ejemplo para categorías
const categoriasGastos = [
  { nombre: 'Alimentos', total: 5420.50, porcentaje: 45 },
  { nombre: 'Bebidas', total: 2830.25, porcentaje: 25 },
  { nombre: 'Limpieza', total: 1200.00, porcentaje: 10 },
  { nombre: 'Mantenimiento', total: 850.75, porcentaje: 8 },
  { nombre: 'Otros', total: 2148.50, porcentaje: 12 }
]
</script>