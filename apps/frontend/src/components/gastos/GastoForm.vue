<template>
  <div class="gasto-form bg-white rounded-lg shadow">
    <div class="px-6 py-4 border-b border-gray-200">
      <h2 class="text-lg font-medium text-gray-900">Registrar Nuevo Gasto</h2>
    </div>
    
    <form @submit.prevent="submitForm" class="p-6">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Información básica del gasto -->
        <div>
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Proveedor</label>
              <SearchableSelect 
                v-model="form.proveedor_id" 
                :options="proveedores"
                placeholder="Seleccionar proveedor"
              />
            </div>
            
            <div>
              <label class="block text-sm font="block text-sm font-medium text-gray-700 mb-1">Tipo de gasto</label>
              <select 
                v-model="form.tipo_gasto"
                class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
              >
                <option value="directo">Directo</option>
                <option value="indirecto">Indirecto</option>
                <option value="nomina">Nómina</option>
              </select>
            </div>
            
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Método de pago</label>
              <select 
                v-model="form.metodo_pago"
                class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
              >
                <option value="efectivo">Efectivo</option>
                <option value="tarjeta">Tarjeta</option>
              </select>
            </div>
            
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Folio (opcional)</label>
              <input 
                v-model="form.folio"
                type="text"
                class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                placeholder="Número de factura"
              >
            </div>
          </div>
        </div>
        
        <!-- Detalles del gasto -->
        <div>
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Descripción</label>
              <textarea 
                v-model="form.descripcion"
                rows="3"
                class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                placeholder="Descripción del gasto"
              ></textarea>
            </div>
            
            <div v-if="form.tipo_gasto !== 'nomina'">
              <label class="block text-sm font-medium text-gray-700 mb-1">Total manual (opcional)</label>
              <input 
                v-model.number="form.total_manual"
                type="number"
                step="0.01"
                class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                placeholder="Total si es diferente a la suma de detalles"
              >
            </div>
            
            <div v-else>
              <label class="block text-sm font-medium text-gray-700 mb-1">Total nómina</label>
              <input 
                v-model.number="form.total_nomina"
                type="number"
                step="0.01"
                class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                placeholder="Total de la nómina"
                required
              >
            </div>
          </div>
        </div>
      </div>
      
      <!-- Detalles de artículos (si no es nómina) -->
      <div v-if="form.tipo_gasto !== 'nomina'" class="mt-6">
        <h3 class="text-lg font-medium text-gray-900 mb-4">Detalles del gasto</h3>
        <div class="border border-gray-200 rounded-lg overflow-hidden">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Artículo</th>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Cantidad</th>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Precio unitario</th>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Subtotal</th>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Acciones</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(detalle, index) in form.detalles" :key="index">
                <td class="px-4 py-2">
                  <SearchableSelect 
                    v-model="detalle.articulo_id" 
                    :options="articulos"
                    placeholder="Seleccionar artículo"
                  />
                </td>
                <td class="px-4 py-2">
                  <input 
                    v-model.number="detalle.cantidad"
                    type="number"
                    step="0.01"
                    class="w-24 border border-gray-300 rounded-md px-2 py-1 text-sm"
                  >
                </td>
                <td class="px-4 py-2">
                  <input 
                    v-model.number="detalle.precio_unitario"
                    type="number"
                    step="0.01"
                    class="w-24 border border-gray-300 rounded-md px-2 py-1 text-sm"
                  >
                </td>
                <td class="px-4 py-2 text-sm">
                  ${{ (detalle.cantidad * detalle.precio_unitario).toFixed(2) }}
                </td>
                <td class="px-4 py-2">
                  <button 
                    type="button" 
                    @click="removeDetalle(index)"
                    class="text-red-500 hover:text-red-700"
                  >
                    Eliminar
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
          <div class="px-4 py-3 bg-gray-50">
            <button 
              type="button" 
              @click="addDetalle"
              class="text-blue-600 hover:text-blue-800 text-sm"
            >
              + Agregar artículo
            </button>
          </div>
        </div>
      </div>
      
      <div class="mt-6 flex justify-end">
        <button 
          type="submit"
          class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Guardar gasto
        </button>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import SearchableSelect from './SearchableSelect.vue'

// Datos de ejemplo
const proveedores = ref([
  { id: 1, nombre: 'Distribuidora ABC', descripcion: 'Proveedor principal de alimentos' },
  { id: 2, nombre: 'Comercial XYZ', descripcion: 'Proveedor de bebidas' }
])

const articulos = ref([
  { id: 1, nombre: 'Tomate', descripcion: 'Kg' },
  { id: 2, nombre: 'Cebolla', descripcion: 'Kg' },
  { id: 3, nombre: 'Papa', descripcion: 'Kg' }
])

// Formulario reactivo
const form = reactive({
  proveedor_id: null,
  tipo_gasto: 'directo',
  metodo_pago: 'efectivo',
  folio: '',
  descripcion: '',
  total_manual: null,
  total_nomina: null,
  detalles: [
    {
      articulo_id: null,
      cantidad: 1,
      precio_unitario: 0
    }
  ]
})

// Funciones para manejar detalles
const addDetalle = () => {
  form.detalles.push({
    articulo_id: null,
    cantidad: 1,
    precio_unitario: 0
  })
}

const removeDetalle = (index: number) => {
  if (form.detalles.length > 1) {
    form.detalles.splice(index, 1)
  }
}

// Función para enviar el formulario
const submitForm = () => {
  console.log('Formulario enviado:', form)
  // Aquí iría la lógica de envío al backend
}
</script>