<template>
  <!-- Modal para Platillos -->
  <div v-if="showPlatilloModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-[150]">
    <div class="relative sm:top-20 mx-auto p-5 border w-full sm:w-96 min-h-full sm:min-h-0 shadow-lg sm:rounded-md bg-white">
      <h3 class="text-lg font-bold text-gray-900 mb-4">
        {{ editingPlatillo ? 'Editar Platillo' : 'Nuevo Platillo' }}
      </h3>
      
      <form @submit.prevent="savePlatillo" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700">Nombre</label>
          <input
            v-model="platilloForm.nombre"
            type="text"
            required
            class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
          />
        </div>
        
        <div>
          <label class="block text-sm font-medium text-gray-700">Descripción</label>
          <textarea
            v-model="platilloForm.descripcion"
            class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
            rows="2"
          ></textarea>
        </div>
        
        <div>
          <label class="block text-sm font-medium text-gray-700">Precio</label>
          <input
            v-model.number="platilloForm.precio"
            type="number"
            step="0.01"
            required
            class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
          />
        </div>
        
        <div>
          <label class="block text-sm font-medium text-gray-700">Categoría</label>
          <select
            v-model="platilloForm.categoria"
            required
            class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
          >
            <option value="Pozole">Pozole</option>
            <option value="Flautas">Flautas</option>
            <option value="Tacos">Tacos</option>
            <option value="Sopes">Sopes</option>
            <option value="Enchiladas">Enchiladas</option>
            <option value="Tostadas">Tostadas</option>
            <option value="Tamales">Tamales</option>
            <option value="Postres">Postres</option>
            <option value="Bebidas">Bebidas</option>
            <option value="Aguas">Aguas</option>
            <option value="Refrescos">Refrescos</option>
            <option value="Extras">Extras</option>
          </select>
        </div>
        
        <div>
          <label class="block text-sm font-medium text-gray-700">Nombre KDS</label>
          <input
            v-model="platilloForm.kds_name"
            type="text"
            maxlength="20"
            class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
            placeholder="Nombre corto para cocina (máx 20 caracteres)"
          />
        </div>
        
        <div>
          <label class="block text-sm font-medium text-gray-700">Estado</label>
          <select
            v-model="platilloForm.estado"
            class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
          >
            <option value="disponible">Disponible</option>
            <option value="no_disponible">No Disponible</option>
          </select>
        </div>
        
        <div class="safe-area-bottom flex justify-end space-x-3 pt-4">
          <button
            type="button"
            @click="closePlatilloModal"
            class="px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400"
          >
            Cancelar
          </button>
          <button
            type="submit"
            class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            {{ editingPlatillo ? 'Actualizar' : 'Crear' }}
          </button>
        </div>
      </form>
    </div>
  </div>

</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'

// Props
interface Props {
  showPlatilloModal: boolean
  editingPlatillo?: any
}

const props = defineProps<Props>()

// Emits
const emit = defineEmits(['close-platillo-modal', 'save-platillo'])

// Forms
const platilloForm = reactive({
  nombre: '',
  descripcion: '',
  precio: 0,
  categoria: 'Pozole',
  kds_name: '',
  estado: 'disponible'
})

// Methods
const closePlatilloModal = () => {
  emit('close-platillo-modal')
  resetPlatilloForm()
}

const resetPlatilloForm = () => {
  Object.assign(platilloForm, {
    nombre: '',
    descripcion: '',
    precio: 0,
    categoria: 'Pozole',
    kds_name: '',
    estado: 'disponible'
  })
}

const savePlatillo = () => {
  const data = { ...platilloForm }
  if (!data.kds_name) {
    data.kds_name = data.nombre.substring(0, 20)
  }
  emit('save-platillo', data)
}

// Watchers para cargar datos cuando se edita
import { watch } from 'vue'

watch(() => props.editingPlatillo, (newVal) => {
  if (newVal) {
    Object.assign(platilloForm, newVal)
  } else {
    resetPlatilloForm()
  }
}, { immediate: true })

</script>
