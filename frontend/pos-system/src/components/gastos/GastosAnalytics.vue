<template>
  <div class="gastos-analytics">
    <div class="bg-white rounded-lg shadow p-6">
      <div class="mb-6">
        <h2 class="text-xl font-bold text-gray-900">Analíticas de Gastos</h2>
        <p class="text-gray-600 mt-1">Visualización detallada de gastos por período, proveedor y categoría</p>
      </div>
      
      <!-- Controles de fecha -->
      <div class="flex flex-wrap items-center gap-4 mb-6">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Período</label>
          <select 
            v-model="periodo"
            class="border border-gray-300 rounded-md px-3 py-2 text-sm"
          >
            <option value="semana">Última semana</option>
            <option value="mes">Último mes</option>
            <option value="trimestre">Último trimestre</option>
            <option value="anio">Último año</option>
          </select>
        </div>
        
        <div class="flex items-center">
          <input 
            type="date" 
            v-model="fechaInicio"
            class="border border-gray-300 rounded-md px-3 py-2 text-sm"
          >
          <span class="mx-2">a</span>
          <input 
            type="date" 
            v-model="fechaFin"
            class="border border-gray-300 rounded-md px-3 py-2 text-sm"
          >
        </div>
        
        <button 
          @click="filtrar"
          class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          Filtrar
        </button>
      </div>
      
      <!-- Resumen ejecutivo -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div class="bg-blue-50 p-4 rounded-lg">
          <div class="text-sm text-gray-600">Total de gastos</div>
          <div class="text-2xl font-bold text-blue-700">$12,450.00</div>
          <div class="text-xs text-gray-500 mt-1">-5% vs. período anterior</div>
        </div>
        
        <div class="bg-green-50 p-4 rounded-lg">
          <div class="text-sm text-gray-600">Proveedor más frecuente</div>
          <div class="text-lg font-bold text-green-700">Distribuidora ABC</div>
          <div class="text-xs text-gray-500 mt-1">52 gastos registrados</div>
        </div>
        
        <div class="bg-yellow-50 p-4 rounded-lg">
          <div class="text-sm text-gray-600">Categoría principal</div>
          <div class="text-lg font-bold text-yellow-700">Alimentos</div>
          <div class="text-xs text-gray-500 mt-1">65% del total</div>
        </div>
        
        <div class="bg-purple-50 p-4 rounded-lg">
          <div class="text-sm text-gray-600">Método de pago más usado</div>
          <div class="text-lg font-bold text-purple-700">Efectivo</div>
          <div class="text-xs text-gray-500 mt-1">78% de transacciones</div>
        </div>
      </div>
      
      <!-- Gráficos -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <!-- Gastos por período -->
        <div class="bg-gray-50 p-4 rounded-lg">
          <h3 class="font-medium text-gray-900 mb-4">Gastos por período</h3>
          <div class="h-64 flex items-center justify-center">
            <div class="text-gray-500">[Gráfico de barras - Gastos por período]</div>
          </div>
        </div>
        
        <!-- Gastos por categoría -->
        <div class="bg-gray-50 p-4 rounded-lg">
          <h3 class="font-medium text-gray-900 mb-4">Gastos por categoría</h3>
          <div class="h-64 flex items-center justify-center">
            <div class="text-gray-500">[Gráfico circular - Gastos por categoría]</div>
          </div>
        </div>
      </div>
      
      <!-- Tabla de análisis detallado -->
      <div>
        <h3 class="font-medium text-gray-900 mb-4">Análisis detallado</h3>
        <div class="border border-gray-200 rounded-lg overflow-hidden">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Proveedor</th>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Categoría</th>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Total</th>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Método</th>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Fecha</th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr v-for="gasto in gastos" :key="gasto.id">
                <td class="px-4 py-2 text-sm text-gray-900">{{ gasto.proveedor }}</td>
                <td class="px-4 py-2 text-sm text-gray-500">{{ gasto.categoria }}</td>
                <td class="px-4 py-2 text-sm text-gray-900 font-medium">${{ gasto.total }}</td>
                <td class="px-4 py-2">
                  <span class="px-2 py-1 text-xs rounded-full bg-gray-100 capitalize">
                    {{ gasto.metodo_pago }}
                  </span>
                </td>
                <td class="px-4 py-2 text-sm text-gray-500">{{ gasto.fecha }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

// Datos de ejemplo
const periodo = ref('mes')
const fechaInicio = ref('')
const fechaFin = ref('')

const gastos = ref([
  {
    id: 1,
    proveedor: 'Distribuidora ABC',
    categoria: 'Alimentos',
    total: 1250.00,
    metodo_pago: 'efectivo',
    fecha: '2023-05-15'
  },
  {
    id: 2,
    proveedor: 'Comercial XYZ',
    categoria: 'Bebidas',
    total: 850.50,
    metodo_pago: 'tarjeta',
    fecha: '2023-05-14'
  },
  {
    id: 3,
    proveedor: 'Servicios Generales',
    categoria: 'Mantenimiento',
    total: 3200.00,
    metodo_pago: 'efectivo',
    fecha: '2023-05-13'
  }
])

const filtrar = () => {
  console.log('Filtrando datos...')
  // Aquí iría la lógica de filtrado
}
</script>