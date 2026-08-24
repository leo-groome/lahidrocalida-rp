<template>
  <div class="gastos-view">
    <!-- Pestañas de navegación -->
    <div class="bg-white rounded-2xl border border-slate-100 shadow-sm mb-6">
      <div class="border-b border-slate-100">
        <nav class="flex overflow-x-auto">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="activeTab = tab.id"
            class="whitespace-nowrap py-4 px-6 border-b-2 font-bold text-sm transition-colors"
            :class="activeTab === tab.id
              ? 'border-[#00126D] text-[#00126D]'
              : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'"
          >
            {{ tab.name }}
          </button>
        </nav>
      </div>
    </div>

    <!-- Contenido según pestaña activa -->
    <div v-if="activeTab === 'historial'">
      <GastosHistorial
        :key="historialKey"
        @new-gasto="showRapidoModal = true"
        @edit-gasto="openEditModal"
      />
    </div>

    <div v-else-if="activeTab === 'proveedores'">
      <ProveedoresView />
    </div>

    <div v-else-if="activeTab === 'articulos'">
      <ArticulosView />
    </div>

    <div v-else-if="activeTab === 'categorias'">
      <CategoriasView />
    </div>

    <!-- Modal: Nuevo Gasto (3-step) -->
    <GastoRapidoModal
      v-if="showRapidoModal"
      :turno-id="null"
      @save="onGastoSaved"
      @cancel="showRapidoModal = false"
    />

    <!-- Modal: Editar Gasto (full form) -->
    <GastoFormModal
      v-if="showEditModal && editingGasto"
      :initial-data="editingGasto"
      @save="onGastoSaved"
      @close="showEditModal = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import GastosHistorial from './GastosHistorial.vue'
import ProveedoresView from './ProveedoresView.vue'
import ArticulosView from './ArticulosView.vue'
import CategoriasView from './CategoriasView.vue'
import GastoRapidoModal from './GastoRapidoModal.vue'
import GastoFormModal from './GastoFormModal.vue'

const tabs = [
  { id: 'historial', name: 'Historial' },
  { id: 'proveedores', name: 'Proveedores' },
  { id: 'articulos', name: 'Artículos' },
  { id: 'categorias', name: 'Categorías' },
]

const activeTab = ref('historial')

const showRapidoModal = ref(false)
const showEditModal = ref(false)
const editingGasto = ref<any>(null)

// Key to force GastosHistorial remount and reload after save
const historialKey = ref(0)

function openEditModal(gasto: any) {
  editingGasto.value = gasto
  showEditModal.value = true
}

function onGastoSaved() {
  showRapidoModal.value = false
  showEditModal.value = false
  editingGasto.value = null
  historialKey.value++
}
</script>
