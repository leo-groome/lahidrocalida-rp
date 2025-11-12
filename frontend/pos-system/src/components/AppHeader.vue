<template>
  <header class="bg-gradient-to-r from-[#00126D] to-[#001a4d] shadow-lg border-b-2 border-[#FDB700]">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex justify-between items-center h-16">
        <!-- Logo y título -->
        <div class="flex items-center space-x-4">
          <div class="bg-white rounded-lg p-2 shadow-lg">
            <img src="/src/assets/Logo.png" alt="La Hidrocálida" class="h-8 w-8" />
          </div>
          <div>
            <h1 class="text-xl md:text-2xl font-bold text-white">{{ title }}</h1>
            <p class="text-xs text-[#FDB700] font-medium">La Hidrocálida</p>
          </div>
        </div>

        <!-- Usuario y logout minimalista -->
        <div class="flex items-center space-x-4">
          <!-- Nombre del usuario -->
          <div class="flex items-center space-x-2">
            <span class="text-[#FDB700] text-sm">👤</span>
            <span class="text-white text-sm font-medium">{{ auth.user?.nombre || 'Usuario' }}</span>
          </div>
          
          <!-- Separador visual -->
          <div class="h-6 w-px bg-gray-300 opacity-50"></div>
          
          <!-- Botón logout minimalista -->
          <button 
            @click="handleLogout"
            class="text-white hover:text-[#FDB700] text-sm font-medium transition-colors duration-200 flex items-center space-x-1"
          >
            <span>Salir</span>
            <span class="text-xs">🚪</span>
          </button>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

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