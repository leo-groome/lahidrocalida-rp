<script setup lang="ts">
import { ref } from 'vue'
import {
  LayoutDashboard,
  Wallet,
  UtensilsCrossed,
  Users,
  Settings,
  LogOut,
  Clock,
  Users2,
  ShoppingCart,
  LayoutGrid,
  X,
} from 'lucide-vue-next'
import { useRouter } from 'vue-router'

withDefaults(defineProps<{
  activeTab: string
  // Solo aplica bajo `lg`: abre el drawer. En escritorio el sidebar siempre está visible.
  isOpen?: boolean
  userName?: string
}>(), {
  isOpen: false,
  userName: 'Admin'
})

defineEmits(['select-tab', 'logout', 'close'])

const router = useRouter()

const isHovered = ref(false)

const menuItems = [
  { id: 'dashboard', name: 'Dashboard', icon: LayoutDashboard },
  { id: 'gastos', name: 'Gastos', icon: Wallet },
  { id: 'compras', name: 'Compras', icon: ShoppingCart },
  { id: 'turnos', name: 'Turnos', icon: Clock },
  { id: 'menu', name: 'Menú', icon: UtensilsCrossed },
  { id: 'usuarios', name: 'Usuarios', icon: Users },
  { id: 'rrhh', name: 'Recursos Humanos', icon: Users2 },
  { id: 'configuracion', name: 'Ajustes', icon: Settings },
]
</script>

<template>
  <aside 
    class="fixed lg:relative inset-y-0 left-0 w-72 bg-slate-900 text-slate-300 border-r border-slate-800 z-40 lg:z-30 transition-all duration-300 ease-in-out group/sidebar overflow-hidden"
    :class="[
      isOpen ? 'translate-x-0 shadow-2xl shadow-black/50' : '-translate-x-full lg:translate-x-0',
      isHovered ? 'lg:w-64 lg:shadow-2xl lg:shadow-black/50' : 'lg:w-20'
    ]"
    @mouseenter="isHovered = true"
    @mouseleave="isHovered = false"
  >
    <div class="flex flex-col h-full w-72 lg:w-64">
      <!-- Logo Section -->
      <div class="h-16 flex items-center justify-between px-6 border-b border-slate-800/50 flex-shrink-0">
        <div class="flex items-center space-x-3 whitespace-nowrap">
          <div class="bg-white rounded-xl p-1.5 shadow-sm transform transition-transform group-hover/sidebar:rotate-12">
            <img src="/src/assets/LogoOptimized.png" alt="Logo" class="h-6 w-6" />
          </div>
          <span 
            class="font-black text-white tracking-tighter text-lg transition-all duration-300"
            :class="[isHovered ? 'lg:opacity-100 lg:translate-x-0' : 'lg:opacity-0 lg:-translate-x-4 lg:pointer-events-none']"
          >
            HIDROCALIDA
          </span>
        </div>
        <button
          class="lg:hidden p-2 -mr-2 text-slate-400 hover:text-white rounded-xl"
          aria-label="Cerrar menú"
          @click="$emit('close')"
        >
          <X class="h-5 w-5" />
        </button>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 overflow-y-auto py-6 px-3 space-y-2 custom-scrollbar">
        <!-- Volver al hub: mesero, caja, cocina y administración -->
        <button
          class="w-full flex items-center px-4 py-3 min-h-11 rounded-2xl text-sm font-bold text-left relative transition-all duration-200 group bg-white/5 text-slate-200 hover:bg-white/10 hover:text-white"
          @click="router.push({ name: 'admin-hub' })"
        >
          <LayoutGrid class="h-5 w-5 flex-shrink-0 text-blue-400" />
          <span
            class="ml-4 whitespace-nowrap transition-all duration-300"
            :class="[isHovered ? 'lg:opacity-100 lg:translate-x-0' : 'lg:opacity-0 lg:translate-x-10']"
          >
            Áreas
          </span>
          <div
            v-if="!isHovered"
            class="hidden lg:block absolute left-full ml-6 px-2 py-1 bg-slate-900 text-white text-[10px] rounded opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity font-black uppercase tracking-widest whitespace-nowrap border border-slate-700 shadow-xl z-50"
          >
            Áreas
          </div>
        </button>
        <div class="h-px bg-slate-800 mx-2 my-2"></div>
        <button
          v-for="item in menuItems"
          :key="item.id"
          @click="$emit('select-tab', item.id)"
          :class="[
            activeTab === item.id
              ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/40 translate-x-0'
              : 'text-slate-400 hover:text-white hover:bg-white/5',
            'w-full flex items-center px-4 py-3 min-h-11 rounded-2xl text-sm font-bold transition-all duration-200 group text-left relative overflow-hidden'
          ]"
        >
          <component 
            :is="item.icon" 
            class="h-5 w-5 flex-shrink-0 transition-transform duration-300 group-hover:scale-110"
            :class="[activeTab === item.id ? 'text-white' : 'text-slate-500 group-hover:text-white']" 
          />
          <span 
            class="ml-4 whitespace-nowrap transition-all duration-300"
            :class="[isHovered ? 'lg:opacity-100 lg:translate-x-0' : 'lg:opacity-0 lg:translate-x-10']"
          >
            {{ item.name }}
          </span>
          
          <!-- Tooltip for collapsed mode -->
          <div 
            v-if="!isHovered" 
            class="hidden lg:block absolute left-full ml-6 px-2 py-1 bg-slate-900 text-white text-[10px] rounded opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity font-black uppercase tracking-widest whitespace-nowrap border border-slate-700 shadow-xl z-50"
          >
            {{ item.name }}
          </div>
        </button>
      </nav>

      <!-- Footer User Info -->
      <div class="p-4 border-t border-slate-800/50 bg-slate-900/50">
        <div 
          class="flex items-center p-2 rounded-2xl transition-all duration-300 overflow-hidden"
          :class="[isHovered ? 'lg:bg-slate-800/40 lg:border lg:border-slate-700/50 lg:w-full' : 'lg:w-12 lg:bg-transparent lg:border-transparent lg:px-0 lg:ml-1', 'bg-slate-800/40 border border-slate-700/50 w-full']"
        >
          <div class="h-10 w-10 rounded-2xl bg-gradient-to-br from-slate-700 to-slate-800 flex flex-shrink-0 items-center justify-center text-xs font-black text-slate-300 border border-slate-600 shadow-inner">
            {{ userName.charAt(0).toUpperCase() }}
          </div>
          
          <div 
            class="ml-3 flex-1 min-w-0 transition-all duration-300 whitespace-nowrap"
            :class="[isHovered ? 'lg:opacity-100 lg:translate-x-0' : 'lg:opacity-0 lg:-translate-x-10']"
          >
            <p class="text-[11px] font-black text-white truncate leading-tight tracking-tight">{{ userName }}</p>
            <p class="text-[9px] text-slate-500 truncate uppercase mt-0.5 tracking-widest font-black opacity-80">Root Admin</p>
          </div>
          
          <button 
            @click="$emit('logout')"
            class="p-3 text-slate-500 hover:text-red-400 transition-all duration-300 rounded-xl hover:bg-red-500/10"
            :class="[isHovered ? 'lg:opacity-100 lg:scale-100' : 'lg:opacity-0 lg:scale-0 lg:pointer-events-none']"
            title="Cerrar Sesión"
          >
            <LogOut class="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  </aside>
</template>

