<template>
  <div class="space-y-10 animate-in fade-in duration-700">
    <!-- Premium Header Section -->
    <div class="flex flex-col md:flex-row md:items-end justify-between gap-8 pb-2 border-b border-slate-100/80">
      <div class="space-y-2">
        <div class="flex items-center gap-3 mb-1">
          <div class="h-10 w-1 bg-blue-600 rounded-full"></div>
          <h2 class="text-3xl font-black text-slate-900 tracking-tight">Gestión de Gastos</h2>
        </div>
        <p class="text-slate-500 font-medium text-lg max-w-2xl">
          Control centralizado de compras, proveedores y catálogo de insumos operativos.
        </p>
      </div>
      
      <div class="flex items-center gap-3 self-start md:self-end">
        <button 
          @click="openNewProveedor" 
          class="inline-flex items-center px-5 py-3 bg-white text-slate-700 border border-slate-200 rounded-2xl text-sm font-bold shadow-sm hover:bg-slate-50 hover:border-slate-300 transition-all active:scale-95"
        >
          <Truck class="h-4 w-4 mr-2.5 text-blue-500" />
          Proveedor
        </button>
        <button 
          @click="openNewArticulo" 
          class="inline-flex items-center px-5 py-3 bg-white text-slate-700 border border-slate-200 rounded-2xl text-sm font-bold shadow-sm hover:bg-slate-50 hover:border-slate-300 transition-all active:scale-95"
        >
          <Package class="h-4 w-4 mr-2.5 text-indigo-500" />
          Artículo
        </button>
        <button 
          @click="$emit('new-gasto')" 
          class="inline-flex items-center px-6 py-3 bg-slate-900 text-white rounded-2xl text-sm font-bold shadow-xl shadow-slate-200 hover:bg-slate-800 hover:-translate-y-0.5 active:translate-y-0 transition-all"
        >
          <Plus class="h-5 w-5 mr-2" />
          Nuevo Gasto
        </button>
      </div>
    </div>

    <!-- Modern Tab Navigation -->
    <div class="flex flex-col space-y-6">
      <div class="flex items-center justify-between">
        <div class="inline-flex p-1.5 bg-slate-100/80 backdrop-blur-md rounded-2xl border border-slate-200 shadow-inner overflow-x-auto max-w-full no-scrollbar">
          <button v-for="sub in gastosTabs" :key="sub.id"
            @click="gastosSubTab = sub.id"
            :class="[
              'px-6 py-2.5 rounded-xl text-xs font-black uppercase tracking-widest transition-all duration-300 relative whitespace-nowrap', 
              gastosSubTab === sub.id 
                ? 'bg-white text-blue-600 shadow-md ring-1 ring-slate-200/20' 
                : 'text-slate-500 hover:text-slate-800 hover:bg-white/50'
            ]"
          >
            {{ sub.name }}
            <div v-if="gastosSubTab === sub.id" class="absolute -bottom-4 left-1/2 -translate-x-1/2 w-1.5 h-1.5 bg-blue-600 rounded-full animate-in fade-in zoom-in"></div>
          </button>
        </div>
      </div>

      <!-- Content Sections -->
      <div class="min-h-[60vh]">
        <div v-if="gastosSubTab === 'dashboard'" class="animate-in slide-in-from-bottom-4 duration-500">
           <GastosDashboard @new-gasto="$emit('new-gasto')" />
        </div>

        <div v-if="gastosSubTab === 'historial'" class="animate-in slide-in-from-bottom-4 duration-500">
           <GastosHistorial 
             ref="gastosHistorialRef"
             @new-gasto="$emit('new-gasto')"
             @edit-gasto="$emit('edit-gasto', $event)"
           />
        </div>
        
        <div v-if="gastosSubTab === 'proveedores'" class="animate-in slide-in-from-bottom-4 duration-500">
            <ProveedoresView 
              :proveedores="proveedoresList" 
              @edit="editProveedor" 
            />
        </div>
        
        <div v-if="gastosSubTab === 'articulos'" class="animate-in slide-in-from-bottom-4 duration-500">
             <ArticulosView 
               :articulos="articulosList" 
               :categorias="categoriasArticuloList" 
               v-model="selectedArticuloCategoria"
               @edit="editArticulo"
               @update:model-value="loadArticulos"
             />
        </div>
        
        <div v-if="gastosSubTab === 'categorias'" class="animate-in slide-in-from-bottom-4 duration-500">
             <CategoriasView 
               :categorias="categoriasArticuloList" 
               @edit="editCategoria"
               @new="openNewCategoria"
             />
        </div>
      </div>
    </div>

    <!-- MODALES LOCALES -->
    <ProveedorFormModal 
      v-if="showProveedorModal"
      :initial-data="editingProveedorData"
      @close="showProveedorModal = false"
      @save="onProveedorSaved"
    />

    <ArticuloFormModal 
      v-if="showArticuloModal"
      :initial-data="editingArticuloData"
      :categories="categoriasArticuloList"
      @close="showArticuloModal = false"
      @save="onArticuloSaved"
    />

    <CategoriaFormModal 
      v-if="showCategoriaModal"
      :initial-data="editingCategoriaData"
      @close="showCategoriaModal = false"
      @save="onCategoriaSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api/client'
import GastosDashboard from '@/components/gastos/GastosDashboard.vue'
import GastosHistorial from '@/components/gastos/GastosHistorial.vue'
import ProveedoresView from '@/components/gastos/ProveedoresView.vue'
import ArticulosView from '@/components/gastos/ArticulosView.vue'
import CategoriasView from '@/components/gastos/CategoriasView.vue'
import ProveedorFormModal from '@/components/gastos/ProveedorFormModal.vue'
import ArticuloFormModal from '@/components/gastos/ArticuloFormModal.vue'
import CategoriaFormModal from '@/components/gastos/CategoriaFormModal.vue'
import { Plus, Truck, Package } from 'lucide-vue-next'

const emit = defineEmits(['new-gasto', 'edit-gasto'])

const gastosTabs = [
  { id: 'dashboard', name: 'Resumen' },
  { id: 'historial', name: 'Historial' },
  { id: 'proveedores', name: 'Proveedores' },
  { id: 'articulos', name: 'Catálogo' },
  { id: 'categorias', name: 'Familias' }
]
const gastosSubTab = ref('dashboard')
const gastosHistorialRef = ref(null)

// Assets Lists
const proveedoresList = ref<any[]>([])
const categoriasArticuloList = ref<any[]>([])
const articulosList = ref<any[]>([])
const selectedArticuloCategoria = ref(null)

// Modals State
const showProveedorModal = ref(false)
const editingProveedorData = ref(null)
const showArticuloModal = ref(false)
const editingArticuloData = ref(null)
const showCategoriaModal = ref(false)
const editingCategoriaData = ref(null)

const loadProveedores = async () => {
  try {
    const res = await api.get('/gastos/proveedores')
    proveedoresList.value = res.data
  } catch (e) { console.error(e) }
}

const loadCategoriasArticulo = async () => {
  try {
    const res = await api.get('/gastos/categorias-articulo')
    categoriasArticuloList.value = res.data
  } catch (e) { console.error(e) }
}

const loadArticulos = async () => {
  try {
    const params: any = {}
    if (selectedArticuloCategoria.value) params.categoria_id = selectedArticuloCategoria.value
    const res = await api.get('/gastos/articulos', { params })
    articulosList.value = res.data
  } catch (e) { console.error(e) }
}

// Handlers
const openNewProveedor = () => {
  editingProveedorData.value = null
  showProveedorModal.value = true
}
const editProveedor = (p: any) => {
  editingProveedorData.value = p
  showProveedorModal.value = true
}
const onProveedorSaved = () => {
  showProveedorModal.value = false
  loadProveedores()
}

const openNewArticulo = () => {
  editingArticuloData.value = null
  showArticuloModal.value = true
}
const editArticulo = (a: any) => {
  editingArticuloData.value = a
  showArticuloModal.value = true
}
const onArticuloSaved = () => {
  showArticuloModal.value = false
  loadArticulos()
}

const openNewCategoria = () => {
  editingCategoriaData.value = null
  showCategoriaModal.value = true
}
const editCategoria = (c: any) => {
  editingCategoriaData.value = c
  showCategoriaModal.value = true
}
const onCategoriaSaved = () => {
  showCategoriaModal.value = false
  loadCategoriasArticulo()
}

onMounted(() => {
  loadProveedores()
  loadCategoriasArticulo()
  loadArticulos()
})

defineExpose({
  loadAll: () => {
    loadProveedores()
    loadCategoriasArticulo()
    loadArticulos()
    if(gastosHistorialRef.value) (gastosHistorialRef.value as any).loadGastos()
  }
})
</script>

<style scoped>
.no-scrollbar::-webkit-scrollbar {
  display: none;
}
.no-scrollbar {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
</style>
