<template>
  <div class="space-y-6 sm:space-y-10 animate-in fade-in duration-700">
    <p v-if="catalogos.error" role="alert" class="text-sm text-rose-600">{{ catalogos.error }}</p>
    <!-- Premium Header Section -->
    <div class="flex flex-col md:flex-row md:items-end justify-between gap-4 md:gap-8 pb-2 border-b border-slate-100/80">
      <div class="space-y-2">
        <div class="flex items-center gap-3 mb-1">
          <div class="h-10 w-1 bg-blue-600 rounded-full"></div>
          <h2 class="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">Gestión de Gastos</h2>
        </div>
        <p class="text-slate-500 font-medium text-sm sm:text-lg max-w-2xl">
          Control centralizado de compras, proveedores y catálogo de insumos operativos.
        </p>
      </div>
      
      <div class="flex flex-wrap items-center gap-2 sm:gap-3 self-start md:self-end">
        <button 
          @click="openNewProveedor" 
          class="inline-flex items-center px-4 sm:px-5 py-3 min-h-11 bg-white text-slate-700 border border-slate-200 rounded-2xl text-sm font-bold shadow-sm hover:bg-slate-50 hover:border-slate-300 transition-all active:scale-95"
        >
          <Truck class="h-4 w-4 mr-2.5 text-blue-500" />
          Proveedor
        </button>
        <button 
          @click="openNewArticulo" 
          class="inline-flex items-center px-4 sm:px-5 py-3 min-h-11 bg-white text-slate-700 border border-slate-200 rounded-2xl text-sm font-bold shadow-sm hover:bg-slate-50 hover:border-slate-300 transition-all active:scale-95"
        >
          <Package class="h-4 w-4 mr-2.5 text-indigo-500" />
          Artículo
        </button>
        <button 
          @click="pedirTipo" 
          class="inline-flex items-center px-5 sm:px-6 py-3 min-h-11 bg-slate-900 text-white rounded-2xl text-sm font-bold shadow-xl shadow-slate-200 hover:bg-slate-800 hover:-translate-y-0.5 active:translate-y-0 transition-all"
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
              'px-4 sm:px-6 py-3 sm:py-2.5 rounded-xl text-xs font-black uppercase tracking-widest transition-all duration-300 relative whitespace-nowrap', 
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
           <GastosDashboard @new-gasto="pedirTipo" />
        </div>

        <div v-if="gastosSubTab === 'historial'" class="animate-in slide-in-from-bottom-4 duration-500">
           <GastosHistorial 
             ref="gastosHistorialRef"
             @new-gasto="pedirTipo"
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
             />
        </div>
        
        <div v-if="gastosSubTab === 'conceptos'" class="animate-in slide-in-from-bottom-4 duration-500">
             <ConceptosGastoView ref="conceptosRef" @registrar="abrirServicio" />
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

    <!-- ¿Qué vas a registrar? -->
    <Teleport to="body">
      <div
        v-if="mostrarTipo"
        class="fixed inset-0 z-[120] flex items-end sm:items-center justify-center bg-slate-900/50 backdrop-blur-sm sm:p-4"
        role="dialog" aria-modal="true" aria-label="¿Qué vas a registrar?"
        @click.self="mostrarTipo = false"
        @keydown.esc="mostrarTipo = false"
      >
        <div class="bg-white w-full sm:max-w-md rounded-t-3xl sm:rounded-3xl p-5 space-y-3 shadow-2xl">
          <h3 class="text-lg font-black text-slate-900">¿Qué vas a registrar?</h3>
          <button type="button" @click="elegirCompra" class="w-full min-h-16 text-left px-4 py-3 rounded-2xl border border-slate-200 hover:border-blue-400 active:scale-[0.99] transition-all">
            <span class="block font-black text-slate-800">🛒 Compra o nómina</span>
            <span class="block text-xs font-bold text-slate-400">Insumos con proveedor y artículos, o pago de nómina</span>
          </button>
          <button type="button" @click="elegirServicio" class="w-full min-h-16 text-left px-4 py-3 rounded-2xl border border-slate-200 hover:border-blue-400 active:scale-[0.99] transition-all">
            <span class="block font-black text-slate-800">💡 Servicio o imprevisto</span>
            <span class="block text-xs font-bold text-slate-400">Renta, luz, gas, agua · desazolve, reparaciones, herramientas</span>
          </button>
          <button type="button" @click="mostrarTipo = false" class="w-full min-h-11 text-sm font-black text-slate-400">Cancelar</button>
        </div>
      </div>
    </Teleport>

    <RegistroRapidoModal
      v-if="servicioModal"
      :caja="false"
      modo-inicial="servicio"
      :concepto-inicial-id="servicioConceptoId"
      @close="servicioModal = false"
      @saved="onServicioGuardado"
    />

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
import { filtrarPorCategoria } from '@/utils/categoria-filtro'
import { storeToRefs } from "pinia"
import { useCatalogosGastosStore } from "@/stores/catalogos-gastos"
const catalogos = useCatalogosGastosStore()
const { proveedores: proveedoresList, categorias: categoriasArticuloList } = storeToRefs(catalogos)
import { ref, computed, onMounted } from 'vue'
import GastosDashboard from '@/components/gastos/GastosDashboard.vue'
import GastosHistorial from '@/components/gastos/GastosHistorial.vue'
import ProveedoresView from '@/components/gastos/ProveedoresView.vue'
import ArticulosView from '@/components/gastos/ArticulosView.vue'
import RegistroRapidoModal from '@/components/gastos/RegistroRapidoModal.vue'
import ConceptosGastoView from '@/components/gastos/ConceptosGastoView.vue'
import CategoriasView from '@/components/gastos/CategoriasView.vue'
import ProveedorFormModal from '@/components/gastos/ProveedorFormModal.vue'
import ArticuloFormModal from '@/components/gastos/ArticuloFormModal.vue'
import CategoriaFormModal from '@/components/gastos/CategoriaFormModal.vue'
import { Plus, Truck, Package } from 'lucide-vue-next'

const emit = defineEmits(['new-gasto', 'edit-gasto'])

const gastosTabs = [
  { id: 'dashboard', name: 'Resumen' },
  { id: 'historial', name: 'Historial' },
  { id: 'conceptos', name: 'Servicios y fijos' },
  { id: 'proveedores', name: 'Proveedores' },
  { id: 'articulos', name: 'Catálogo' },
  { id: 'categorias', name: 'Familias' }
]
const gastosSubTab = ref('dashboard')
const gastosHistorialRef = ref(null)
const conceptosRef = ref<{ cargar: () => void } | null>(null)

// "Nuevo Gasto": primero se pregunta qué es, para no obligar a conocer cada pantalla.
const mostrarTipo = ref(false)
const servicioModal = ref(false)
const servicioConceptoId = ref<number | null>(null)
const pedirTipo = () => { mostrarTipo.value = true }
const elegirCompra = () => { mostrarTipo.value = false; emit('new-gasto') }
const elegirServicio = () => { mostrarTipo.value = false; abrirServicio(null) }
function abrirServicio(conceptoId: number | null) {
  servicioConceptoId.value = conceptoId
  servicioModal.value = true
}
function onServicioGuardado() {
  servicioModal.value = false
  conceptosRef.value?.cargar()
  if (gastosHistorialRef.value) (gastosHistorialRef.value as any).loadGastos()
}

// Assets Lists
const selectedArticuloCategoria = ref<number | null>(null)
const articulosList = computed(() =>
  filtrarPorCategoria(catalogos.articulos, selectedArticuloCategoria.value))

// Modals State
const showProveedorModal = ref(false)
const editingProveedorData = ref(null)
const showArticuloModal = ref(false)
const editingArticuloData = ref(null)
const showCategoriaModal = ref(false)
const editingCategoriaData = ref(null)

async function loadCatalogos() {
  try { await catalogos.cargar() } catch { /* El error se muestra en la sección. */ }
}
const loadProveedores = loadCatalogos
const loadCategoriasArticulo = loadCatalogos
const loadArticulos = loadCatalogos


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
