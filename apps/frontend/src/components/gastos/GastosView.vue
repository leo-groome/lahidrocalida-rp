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
      <ProveedoresView :proveedores="proveedoresList" />
    </div>

    <div v-else-if="activeTab === 'articulos'">
      <ArticulosView
        :articulos="articulosList"
        :categorias="categoriasArticuloList"
        v-model="selectedArticuloCategoria"
        @update:model-value="loadArticulos"
      />
    </div>

    <div v-else-if="activeTab === 'categorias'">
      <CategoriasView :categorias="categoriasArticuloList" />
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
import { ref, onMounted } from 'vue'
import api from '@/api/client'
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

// Catálogos para las pestañas de proveedores/artículos/categorías
const proveedoresList = ref<any[]>([])
const categoriasArticuloList = ref<any[]>([])
const articulosList = ref<any[]>([])
const selectedArticuloCategoria = ref(null)

async function loadProveedores() {
  try {
    const res = await api.get('/gastos/proveedores')
    proveedoresList.value = res.data
  } catch (e) { console.error(e) }
}

async function loadCategoriasArticulo() {
  try {
    const res = await api.get('/gastos/categorias-articulo')
    categoriasArticuloList.value = res.data
  } catch (e) { console.error(e) }
}

async function loadArticulos() {
  try {
    const params: any = {}
    if (selectedArticuloCategoria.value) params.categoria_id = selectedArticuloCategoria.value
    const res = await api.get('/gastos/articulos', { params })
    articulosList.value = res.data
  } catch (e) { console.error(e) }
}

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

onMounted(() => {
  loadProveedores()
  loadCategoriasArticulo()
  loadArticulos()
})
</script>
