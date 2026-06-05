<template>
  <!-- Modal para Platillos -->
  <div v-if="showPlatilloModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-[150]">
    <div class="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
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
        
        <div class="flex justify-end space-x-3 pt-4">
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

  <!-- Modal para Usuarios -->
  <div v-if="showUsuarioModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-[150]">
    <div class="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
      <h3 class="text-lg font-bold text-gray-900 mb-4">
        {{ editingUsuario ? 'Editar Usuario' : 'Nuevo Usuario' }}
      </h3>
      
      <form @submit.prevent="saveUsuario" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700">Nombre</label>
          <input
            v-model="usuarioForm.nombre"
            type="text"
            required
            class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
          />
        </div>
        
        <div>
          <label class="block text-sm font-medium text-gray-700">PIN</label>
          <input
            v-model="usuarioForm.pin"
            type="text"
            inputmode="numeric"
            autocomplete="off"
            maxlength="8"
            :required="!editingUsuario"
            class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
            :placeholder="editingUsuario ? 'Dejar vacío para mantener PIN actual' : 'PIN del usuario'"
          />
        </div>
        
        <div>
          <label class="block text-sm font-medium text-gray-700">Rol</label>
          <select
            v-model="usuarioForm.rol"
            required
            class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
          >
            <option value="mesero">Mesero</option>
            <option value="cajero">Cajero</option>
            <option value="cocina">Cocina</option>
            <option value="administrador">Administrador</option>
          </select>
        </div>
        
        <div>
          <label class="block text-sm font-medium text-gray-700">Sucursal ID</label>
          <input
            v-model.number="usuarioForm.sucursal_id"
            type="number"
            required
            class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
          />
        </div>
        
        <div>
          <label class="flex items-center space-x-2">
            <input
              v-model="usuarioForm.activo"
              type="checkbox"
              class="rounded border-gray-300"
            />
            <span class="text-sm font-medium text-gray-700">Activo</span>
          </label>
        </div>
        
        <div class="flex justify-end space-x-3 pt-4">
          <button
            type="button"
            @click="closeUsuarioModal"
            class="px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400"
          >
            Cancelar
          </button>
          <button
            type="submit"
            class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            {{ editingUsuario ? 'Actualizar' : 'Crear' }}
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
  showUsuarioModal: boolean
  editingPlatillo?: any
  editingUsuario?: any
}

const props = defineProps<Props>()

// Emits
const emit = defineEmits(['close-platillo-modal', 'close-usuario-modal', 'save-platillo', 'save-usuario'])

// Forms
const platilloForm = reactive({
  nombre: '',
  descripcion: '',
  precio: 0,
  categoria: 'Pozole',
  kds_name: '',
  estado: 'disponible'
})

const usuarioForm = reactive({
  nombre: '',
  pin: '',
  rol: 'mesero',
  sucursal_id: 1,
  activo: true
})

// Methods
const closePlatilloModal = () => {
  emit('close-platillo-modal')
  resetPlatilloForm()
}

const closeUsuarioModal = () => {
  emit('close-usuario-modal')
  resetUsuarioForm()
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

const resetUsuarioForm = () => {
  Object.assign(usuarioForm, {
    nombre: '',
    pin: '',
    rol: 'mesero',
    sucursal_id: 1,
    activo: true
  })
}

const savePlatillo = () => {
  const data = { ...platilloForm }
  if (!data.kds_name) {
    data.kds_name = data.nombre.substring(0, 20)
  }
  emit('save-platillo', data)
}

const saveUsuario = () => {
  const data: Record<string, any> = {}

  if (!props.editingUsuario || usuarioForm.nombre !== props.editingUsuario.nombre) {
    data.nombre = usuarioForm.nombre
  }
  if (!props.editingUsuario || usuarioForm.rol !== props.editingUsuario.rol) {
    data.rol = usuarioForm.rol
  }
  if (!props.editingUsuario || usuarioForm.activo !== props.editingUsuario.activo) {
    data.activo = usuarioForm.activo
  }
  if (!props.editingUsuario || usuarioForm.sucursal_id !== props.editingUsuario.sucursal_id) {
    data.sucursal_id = usuarioForm.sucursal_id
  }
  if (usuarioForm.pin.trim()) {
    data.pin = usuarioForm.pin.trim()
  }

  emit('save-usuario', data)
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

watch(() => props.editingUsuario, (newVal) => {
  if (newVal) {
    Object.assign(usuarioForm, {
      ...newVal,
      pin: ''
    })
  } else {
    resetUsuarioForm()
  }
}, { immediate: true })
</script>
