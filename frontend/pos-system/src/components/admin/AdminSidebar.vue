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
} from 'lucide-vue-next'

const props = withDefaults(defineProps<{
  activeTab: string
  isOpen?: boolean
  userName?: string
}>(), {
  isOpen: true,
  userName: 'Admin'
})

defineEmits(['select-tab', 'logout'])

const isHovered = ref(false)

const menuItems = [
  { id: 'dashboard', name: 'Dashboard', icon: LayoutDashboard },
  { id: 'gastos', name: 'Gastos', icon: Wallet },
  { id: 'turnos', name: 'Turnos', icon: Clock },
  { id: 'menu', name: 'Menú', icon: UtensilsCrossed },
  { id: 'usuarios', name: 'Usuarios', icon: Users },
  { id: 'rrhh', name: 'Recursos Humanos', icon: Users2 },
  { id: 'configuracion', name: 'Ajustes', icon: Settings },
]
</script>

<template>
  <aside 
    class="fixed lg:relative inset-y-0 left-0 bg-slate-900 text-slate-300 border-r border-slate-800 z-30 transition-all duration-300 ease-in-out group/sidebar overflow-hidden"
    :class="[
      isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
      isHovered ? 'w-64 shadow-2xl shadow-black/50' : 'w-20'
    ]"
    @mouseenter="isHovered = true"
    @mouseleave="isHovered = false"
  >
    <div class="flex flex-col h-full w-64">
      <!-- Logo Section -->
      <div class="h-16 flex items-center px-6 border-b border-slate-800/50 flex-shrink-0">
        <div class="flex items-center space-x-3 whitespace-nowrap">
          <div class="bg-white rounded-xl p-1.5 shadow-sm transform transition-transform group-hover/sidebar:rotate-12">
            <img src="/src/assets/LogoOptimized.png" alt="Logo" class="h-6 w-6" />
          </div>
          <span 
            class="font-black text-white tracking-tighter text-lg transition-all duration-300"
            :class="[isHovered ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-4 pointer-events-none']"
          >
            HIDROCALIDA
          </span>
        </div>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 overflow-y-auto py-6 px-3 space-y-2 custom-scrollbar">
        <button
          v-for="item in menuItems"
          :key="item.id"
          @click="$emit('select-tab', item.id)"
          :class="[
            activeTab === item.id
              ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/40 translate-x-0'
              : 'text-slate-400 hover:text-white hover:bg-white/5',
            'w-full flex items-center px-4 py-3 rounded-2xl text-sm font-bold transition-all duration-200 group text-left relative overflow-hidden'
          ]"
        >
          <component 
            :is="item.icon" 
            class="h-5 w-5 flex-shrink-0 transition-transform duration-300 group-hover:scale-110"
            :class="[activeTab === item.id ? 'text-white' : 'text-slate-500 group-hover:text-white']" 
          />
          <span 
            class="ml-4 whitespace-nowrap transition-all duration-300"
            :class="[isHovered ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-10']"
          >
            {{ item.name }}
          </span>
          
          <!-- Tooltip for collapsed mode -->
          <div 
            v-if="!isHovered" 
            class="absolute left-full ml-6 px-2 py-1 bg-slate-900 text-white text-[10px] rounded opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity font-black uppercase tracking-widest whitespace-nowrap border border-slate-700 shadow-xl z-50"
          >
            {{ item.name }}
          </div>
        </button>
      </nav>

      <!-- Footer User Info -->
      <div class="p-4 border-t border-slate-800/50 bg-slate-900/50">
        <div 
          class="flex items-center p-2 rounded-2xl transition-all duration-300 overflow-hidden"
          :class="[isHovered ? 'bg-slate-800/40 border border-slate-700/50 w-full' : 'w-12 bg-transparent border-transparent px-0 ml-1']"
        >
          <div class="h-10 w-10 rounded-2xl bg-gradient-to-br from-slate-700 to-slate-800 flex flex-shrink-0 items-center justify-center text-xs font-black text-slate-300 border border-slate-600 shadow-inner">
            {{ userName.charAt(0).toUpperCase() }}
          </div>
          
          <div 
            class="ml-3 flex-1 min-w-0 transition-all duration-300 whitespace-nowrap"
            :class="[isHovered ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-10']"
          >
            <p class="text-[11px] font-black text-white truncate leading-tight tracking-tight">{{ userName }}</p>
            <p class="text-[9px] text-slate-500 truncate uppercase mt-0.5 tracking-widest font-black opacity-80">Root Admin</p>
          </div>
          
          <button 
            @click="$emit('logout')"
            class="p-2 text-slate-500 hover:text-red-400 transition-all duration-300 rounded-xl hover:bg-red-500/10"
            :class="[isHovered ? 'opacity-100 rotate-0 scale-100' : 'opacity-0 rotate-90 scale-0 pointer-events-none']"
            title="Cerrar Sesión"
          >
            <LogOut class="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  </aside>
</template>

