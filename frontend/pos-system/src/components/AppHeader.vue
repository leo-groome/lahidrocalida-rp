<template>
  <header class="sticky top-0 z-40 bg-white/80 backdrop-blur-xl border-b border-slate-200/60 shadow-sm">
    <div class="max-w-[1600px] mx-auto px-6 lg:px-8">
      <div class="flex justify-between items-center h-16">
        <!-- Logo and Title Group -->
        <div class="flex items-center gap-2 sm:gap-4 overflow-hidden">
          <div class="hidden xs:flex bg-blue-600 rounded-xl p-2 sm:p-2.5 shadow-lg shadow-blue-200/50 transition-transform hover:scale-105 duration-300 flex-shrink-0">
            <img src="/src/assets/LogoOptimized.png" alt="La Hidrocálida" class="h-4 w-4 sm:h-6 sm:w-6 brightness-0 invert" />
          </div>
          <div class="flex flex-col min-w-0">
            <h1 class="text-base sm:text-xl font-black text-slate-800 tracking-tight leading-none truncate">{{ title }}</h1>
            <p class="text-[8px] sm:text-[10px] font-black text-blue-600 uppercase tracking-[0.1em] sm:tracking-[0.2em] mt-1 truncate">LA HIDROCÁLIDA</p>
          </div>
        </div>

        <!-- Right Side Actions -->
        <div class="flex items-center gap-3 sm:gap-6">
          <!-- User Profile -->
          <div class="flex items-center gap-2 sm:gap-3 px-2 sm:px-4 py-1.5 sm:py-2 bg-slate-50 border border-slate-100 rounded-2xl group transition-all duration-300 hover:bg-white hover:border-blue-100">
            <div class="w-7 h-7 sm:w-8 sm:h-8 rounded-lg sm:rounded-xl bg-blue-100 flex items-center justify-center group-hover:bg-blue-600 transition-colors duration-300">
              <User class="w-3.5 h-3.5 sm:w-4 sm:h-4 text-blue-600 group-hover:text-white transition-colors" />
            </div>
            <div class="hidden md:flex flex-col">
              <span class="text-xs font-black text-slate-700 tracking-tight leading-none">{{ auth.user?.nombre || 'Usuario' }}</span>
              <span class="text-[9px] font-bold text-slate-400 uppercase tracking-widest mt-1">{{ auth.user?.rol || 'Personal' }}</span>
            </div>
          </div>
          
          <!-- Vertical Separator -->
          <div class="hidden xs:block h-6 sm:h-8 w-px bg-slate-200"></div>
          
          <!-- Action Buttons -->
          <button 
            @click="handleLogout"
            class="flex items-center gap-1 sm:gap-2 text-slate-400 hover:text-red-500 font-black text-[10px] uppercase tracking-widest transition-all duration-300 group"
          >
            <span class="hidden sm:inline">Cerrar Sesión</span>
            <div class="p-2 rounded-xl group-hover:bg-red-50 transition-colors">
              <LogOut class="w-4 h-4" />
            </div>
          </button>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { User, LogOut } from 'lucide-vue-next'

interface Props {
  title: string
}

const props = defineProps<Props>()

const router = useRouter()
const auth = useAuthStore()

const handleLogout = () => {
  auth.logout()
  router.push({ name: 'login' })
}
</script>