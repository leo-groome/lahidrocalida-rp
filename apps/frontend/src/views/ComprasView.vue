<template>
  <div class="min-h-screen bg-slate-50 flex flex-col">
    <!-- ── Top bar ── -->
    <header class="sticky top-0 z-40 bg-white/90 backdrop-blur border-b border-slate-100">
      <div class="max-w-[1400px] mx-auto px-4 sm:px-6 py-4 flex items-center justify-between gap-3">
        <div class="flex items-center gap-3 min-w-0">
          <div class="w-10 h-10 rounded-2xl bg-[#00126D] text-white flex items-center justify-center flex-shrink-0">
            <ShoppingCart class="w-5 h-5" />
          </div>
          <div class="min-w-0">
            <p class="text-[10px] font-black tracking-widest text-slate-400 uppercase leading-none">Módulo</p>
            <h1 class="text-lg font-black text-slate-900 tracking-tight truncate">Compras y Gastos</h1>
          </div>
        </div>
        <div class="flex items-center gap-3 flex-shrink-0">
          <div class="text-right hidden sm:block">
            <p class="text-sm font-black text-slate-800 leading-none">{{ auth.user?.nombre }}</p>
            <p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-1">{{ auth.role }}</p>
          </div>
          <button
            @click="logout"
            class="w-10 h-10 flex items-center justify-center rounded-2xl bg-slate-100 text-slate-500 hover:bg-slate-900 hover:text-white transition-all"
            title="Salir"
          >
            <LogOut class="w-5 h-5" />
          </button>
        </div>
      </div>

      <!-- ── Tabs (scrollables en móvil) ── -->
      <div class="max-w-[1400px] mx-auto px-4 sm:px-6">
        <nav class="flex gap-2 overflow-x-auto no-scrollbar pb-3">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="activeTab = tab.id"
            class="whitespace-nowrap px-4 py-2.5 rounded-2xl text-xs font-black uppercase tracking-widest transition-all flex items-center gap-2"
            :class="activeTab === tab.id
              ? 'bg-[#00126D] text-white shadow-lg shadow-[#00126D]/20'
              : 'bg-white text-slate-500 border border-slate-200 hover:border-slate-300'"
          >
            <component :is="tab.icon" class="w-3.5 h-3.5" />
            {{ tab.name }}
          </button>
        </nav>
      </div>
    </header>

    <!-- ── Contenido ── -->
    <main class="flex-1 max-w-[1400px] w-full mx-auto px-4 sm:px-6 py-6">
      <!-- Registrar (wizard tipo checkout) -->
      <div v-if="activeTab === 'registrar'" class="max-w-2xl mx-auto">
        <GastoCheckout :key="checkoutKey" @saved="onSaved" />
      </div>

      <!-- Historial -->
      <div v-else-if="activeTab === 'historial'">
        <GastosHistorial ref="historialRef" @new-gasto="goRegistrar" @edit-gasto="openEdit" />
      </div>

      <!-- Proveedores -->
      <div v-else-if="activeTab === 'proveedores'">
        <ProveedoresView :proveedores="proveedoresList" />
      </div>

      <!-- Artículos -->
      <div v-else-if="activeTab === 'articulos'">
        <ArticulosView
          :articulos="articulosList"
          :categorias="categoriasArticuloList"
          v-model="selectedArticuloCategoria"
          @update:model-value="loadArticulos"
        />
      </div>

      <!-- Categorías -->
      <div v-else-if="activeTab === 'categorias'">
        <CategoriasView :categorias="categoriasArticuloList" />
      </div>
    </main>

    <!-- Modal de alta/edición (form completo con desglose) -->
    <GastoFormModal
      v-if="showFormModal"
      :initial-data="editingGasto"
      :turno-id="null"
      @save="onSaved"
      @close="closeModal"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import api from '@/api/client'
import GastosHistorial from '@/components/gastos/GastosHistorial.vue'
import ProveedoresView from '@/components/gastos/ProveedoresView.vue'
import ArticulosView from '@/components/gastos/ArticulosView.vue'
import CategoriasView from '@/components/gastos/CategoriasView.vue'
import GastoFormModal from '@/components/gastos/GastoFormModal.vue'
import GastoCheckout from '@/components/gastos/GastoCheckout.vue'
import { ShoppingCart, LogOut, ReceiptText, History, Truck, Package, Tags } from 'lucide-vue-next'

const auth = useAuthStore()
const router = useRouter()

const tabs = [
  { id: 'registrar', name: 'Registrar', icon: ReceiptText },
  { id: 'historial', name: 'Historial', icon: History },
  { id: 'proveedores', name: 'Proveedores', icon: Truck },
  { id: 'articulos', name: 'Artículos', icon: Package },
  { id: 'categorias', name: 'Categorías', icon: Tags },
]

const activeTab = ref('registrar')

const showFormModal = ref(false)
const editingGasto = ref<any>(null)
const historialRef = ref<any>(null)
const checkoutKey = ref(0)

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

// El botón "nuevo" del historial lleva al wizard de registro.
function goRegistrar() {
  activeTab.value = 'registrar'
}

function openEdit(gasto: any) {
  editingGasto.value = gasto
  showFormModal.value = true
}

function closeModal() {
  showFormModal.value = false
  editingGasto.value = null
}

async function onSaved() {
  closeModal()
  checkoutKey.value++ // reinicia el wizard para el próximo gasto
  activeTab.value = 'historial'
  await nextTick()
  historialRef.value?.loadGastos?.()
}

function logout() {
  auth.logout()
  router.push('/login')
}

onMounted(() => {
  loadProveedores()
  loadCategoriasArticulo()
  loadArticulos()
})
</script>

<style scoped>
.no-scrollbar::-webkit-scrollbar { display: none; }
.no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
</style>
