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
            <option value="pozoles">Pozoles</option>
            <option value="flautas">Flautas</option>
            <option value="tacos">Tacos</option>
            <option value="sopes">Sopes</option>
            <option value="enchiladas">Enchiladas</option>
            <option value="tostadas">Tostadas</option>
            <option value="tamales">Tamales</option>
            <option value="postres">Postres</option>
            <option value="bebidas">Bebidas</option>
            <option value="extras">Extras</option>
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
          <label class="block text-sm font-medium text-gray-700">Contraseña</label>
          <input
            v-model="usuarioForm.password"
            type="password"
            :required="!editingUsuario"
            class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
            :placeholder="editingUsuario ? 'Dejar vacío para mantener actual' : 'Contraseña del usuario'"
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
  categoria: 'pozoles',
  kds_name: '',
  estado: 'disponible'
})

const usuarioForm = reactive({
  nombre: '',
  password: '',
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
    categoria: 'pozoles',
    kds_name: '',
    estado: 'disponible'
  })
}

const resetUsuarioForm = () => {
  Object.assign(usuarioForm, {
    nombre: '',
    password: '',
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
  const data = { ...usuarioForm }
  // Si es edición y no hay password, no enviar password
  if (props.editingUsuario && !data.password) {
    delete data.password
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
})

watch(() => props.editingUsuario, (newVal) => {
  if (newVal) {
    Object.assign(usuarioForm, {
      ...newVal,
      password: '' // No mostrar password actual
    })
  } else {
    resetUsuarioForm()
  }
})
</script>