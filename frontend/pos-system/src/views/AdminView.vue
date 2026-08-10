<template>
  <div class="flex h-screen bg-slate-50 font-sans selection:bg-blue-100 selection:text-blue-900 overflow-hidden">
    <!-- Sidebar Navegación -->
    <AdminSidebar 
      :active-tab="activeTab" 
      :user-name="auth.user?.nombre || 'Administrador'"
      @select-tab="selectTab" 
      @logout="() => { auth.logout(); router.push('/login') }"
    />

    <!-- Contenido Principal -->
    <div class="flex-1 flex flex-col min-w-0 relative h-screen overflow-hidden">
      <!-- Topbar -->
      <AdminTopbar 
        :title="currentTabName" 
        :subtitle="currentTabSubtitle"
        :user-name="auth.user?.nombre || 'Administrador'"
      />

      <!-- Scrollable Content Area -->
      <main class="flex-1 overflow-y-auto p-4 md:p-8 scroll-smooth custom-scrollbar">
        <div class="max-w-[1400px] mx-auto">
          
          <keep-alive>
            <component 
              :is="currentSectionComponent"
              @new-gasto="handleNewGasto"
              @edit-gasto="handleEditGasto"
              @new-platillo="openNewPlatilloModal"
              @edit-platillo="editPlatillo"
              @new-user="openNewUsuarioModal"
              @edit-user="editUsuario"
            />
          </keep-alive>

        </div>
      </main>
    </div>

    <!-- MODALES GLOBALES (Mantenidos desde original con leve ajuste visual) -->
    <AdminModals
      v-if="showPlatilloModal || showUsuarioModal"
      :show-platillo-modal="showPlatilloModal"
      :show-usuario-modal="showUsuarioModal"
      :editing-platillo="editingPlatillo"
      :editing-usuario="editingUsuario"
      @close-platillo-modal="closePlatilloModal"
      @close-usuario-modal="closeUsuarioModal"
      @save-platillo="savePlatillo"
      @save-usuario="saveUsuario"
    />

    <!-- Modal Gasto NUEVO -->
    <GastoFormModal
      v-if="showGastoModal"
      :initial-data="editingGastoData"
      @close="showGastoModal = false"
      @save="handleGastoSaved"
    />

  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import api from '@/api/client'

// Componentes Nucleo
import AdminSidebar from '@/components/admin/AdminSidebar.vue'
import AdminTopbar from '@/components/admin/AdminTopbar.vue'

// Secciones
import DashboardSection from '@/components/admin/sections/DashboardSection.vue'
import GastosSection from '@/components/admin/sections/GastosSection.vue'
import PlatillosSection from '@/components/admin/sections/PlatillosSection.vue'
import UsuariosSection from '@/components/admin/sections/UsuariosSection.vue'
import ConfiguracionSection from '@/components/admin/sections/ConfiguracionSection.vue'
import TurnosSection from '@/components/admin/sections/TurnosSection.vue'
import RecursosHumanosSection from '@/components/admin/sections/RecursosHumanosSection.vue'

// Modales y Formas
import AdminModals from '@/components/AdminModals.vue'
import GastoFormModal from '@/components/gastos/GastoFormModal.vue'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

// Seguridad
if (auth.user?.rol !== 'administrador') {
  router.replace({ name: 'login' })
}

// Navegación - Sincronizar con URL
const activeTab = ref(route.query.tab as string || 'dashboard')

// Watcher para cambios en la URL (al navegar vía sidebar o histórico)
watch(() => route.query.tab, (newTab) => {
  if (newTab && typeof newTab === 'string') {
    activeTab.value = newTab
  }
}, { immediate: true })

// Función para cambiar de pestaña actualizando la URL
const selectTab = (id: string) => {
  // 'compras' es una vista dedicada standalone, no una sección interna.
  if (id === 'compras') {
    router.push('/compras')
    return
  }
  activeTab.value = id
  router.push({ query: { ...route.query, tab: id } })
}

const sections: Record<string, { name: string, subtitle: string, component: any }> = {
  dashboard: { 
    name: 'Analíticas', 
    subtitle: 'Visión general del rendimiento del restaurante.',
    component: DashboardSection 
  },
  gastos: {
    name: 'Egresos',
    subtitle: 'Gestión de compras, nómina y proveedores.',
    component: GastosSection
  },
  turnos: {
    name: 'Turnos',
    subtitle: 'Historial de turnos y arqueos de caja.',
    component: TurnosSection
  },
  menu: { 
    name: 'Menú', 
    subtitle: 'Administra tus platillos, precios y categorías.',
    component: PlatillosSection 
  },
  usuarios: {
    name: 'Equipo',
    subtitle: 'Colaboradores y permisos de acceso.',
    component: UsuariosSection
  },
  rrhh: {
    name: 'Recursos Humanos',
    subtitle: 'Horas trabajadas y registro de asistencia.',
    component: RecursosHumanosSection
  },
  configuracion: { 
    name: 'Ajustes', 
    subtitle: 'Parámetros globales del sistema e impresión.',
    component: ConfiguracionSection 
  }
}

const currentTabName = computed(() => sections[activeTab.value]?.name || '')
const currentTabSubtitle = computed(() => sections[activeTab.value]?.subtitle || '')
const currentSectionComponent = computed(() => sections[activeTab.value]?.component)

// --- LÓGICA DE MODALES ---
const showPlatilloModal = ref(false)
const showUsuarioModal = ref(false)
const editingPlatillo = ref<any>(null)
const editingUsuario = ref<any>(null)

const openNewPlatilloModal = () => {
  editingPlatillo.value = null
  showPlatilloModal.value = true
}

const editPlatillo = (platillo: any) => {
  editingPlatillo.value = platillo
  showPlatilloModal.value = true
}

const closePlatilloModal = () => {
  showPlatilloModal.value = false
  editingPlatillo.value = null
}

const savePlatillo = async (data: any) => {
  try {
    if (editingPlatillo.value) {
      await api.put(`/platillos/${editingPlatillo.value.id}`, data)
    } else {
      await api.post('/platillos/', data)
    }
    closePlatilloModal()
    window.location.reload()
  } catch (error) {
    alert('Error al guardar platillo')
  }
}

// LOGICA GASTOS
const showGastoModal = ref(false)
const editingGastoData = ref(null)

const handleNewGasto = () => {
  editingGastoData.value = null
  showGastoModal.value = true
}

const handleEditGasto = (gasto: any) => {
  editingGastoData.value = gasto
  showGastoModal.value = true
}

const handleGastoSaved = () => {
  showGastoModal.value = false
  // Note: GastosSection will reload itself via onMounted or exposed methods if needed
}

// LOGICA USUARIOS
const openNewUsuarioModal = () => {
  editingUsuario.value = null
  showUsuarioModal.value = true
}

const editUsuario = (user: any) => {
  editingUsuario.value = user
  showUsuarioModal.value = true
}

const closeUsuarioModal = () => {
  showUsuarioModal.value = false
  editingUsuario.value = null
}

const saveUsuario = async (data: any) => {
  try {
    if (editingUsuario.value) {
      await api.put(`/usuarios/${editingUsuario.value.id}`, data)
    } else {
      await api.post('/usuarios/', data)
    }
    closeUsuarioModal()
    window.location.reload()
  } catch (error) {
    alert('Error al guardar usuario')
  }
}
</script>


<style>
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #e2e8f0;
  border-radius: 10px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: #cbd5e1;
}

/* Transitions */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>
