<template>
  <div class="space-y-8 animate-in fade-in duration-500">
    <!-- Header -->
    <div class="flex flex-wrap items-center justify-between gap-6 bg-white p-8 rounded-3xl shadow-sm border border-slate-100">
      <div class="space-y-1">
        <h2 class="text-2xl font-extrabold text-slate-900 tracking-tight">Gestión de Usuarios</h2>
        <p class="text-sm font-medium text-slate-500">Administra los accesos y roles de tu equipo.</p>
      </div>
      
      <button 
        @click="$emit('new-user')" 
        class="inline-flex items-center px-6 py-3 bg-emerald-600 text-white rounded-2xl text-sm font-bold shadow-lg shadow-emerald-200 hover:bg-emerald-700 hover:scale-105 active:scale-95 transition-all"
      >
        <UserPlus class="h-4 w-4 mr-2" />
        Nuevo Usuario
      </button>
    </div>

    <!-- User List as Modern Table -->
    <div class="bg-white rounded-3xl shadow-sm border border-slate-100 overflow-hidden animate-in slide-in-from-bottom-2 duration-300">
      <table class="min-w-full">
        <thead class="bg-slate-50/50">
          <tr>
            <th class="px-8 py-5 text-left text-[10px] font-extrabold text-slate-400 uppercase tracking-widest">Colaborador</th>
            <th class="px-8 py-5 text-left text-[10px] font-extrabold text-slate-400 uppercase tracking-widest">Rol</th>
            <th class="px-8 py-5 text-left text-[10px] font-extrabold text-slate-400 uppercase tracking-widest">Estado</th>
            <th class="px-8 py-5 text-right text-[10px] font-extrabold text-slate-400 uppercase tracking-widest">Acción</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-50">
          <tr v-for="user in usuariosList" :key="user.id" class="group hover:bg-slate-50/30 transition-all cursor-default">
            <td class="px-8 py-5">
              <div class="flex items-center space-x-4">
                <div class="h-10 w-10 border-2 border-white rounded-2xl bg-gradient-to-br from-blue-50 to-blue-100 flex items-center justify-center text-blue-600 font-black text-sm shadow-sm group-hover:scale-110 transition-transform">
                  {{ user.nombre.charAt(0).toUpperCase() }}
                </div>
                <div class="space-y-0.5">
                  <p class="text-sm font-extrabold text-slate-800 transition-colors group-hover:text-blue-600">{{ user.nombre }}</p>
                  <p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{{ user.email || 'hidrocalida.staff' }}</p>
                </div>
              </div>
            </td>
            <td class="px-8 py-5">
              <span class="inline-flex items-center px-4 py-1 rounded-xl text-[10px] font-black uppercase tracking-widest border border-slate-100" 
                :class="user.rol === 'administrador' ? 'bg-blue-50 text-blue-600 border-blue-200/50' : 'bg-slate-50 text-slate-500 border-slate-200/50'">
                {{ user.rol }}
              </span>
            </td>
            <td class="px-8 py-5">
              <div class="flex items-center">
                <div class="h-2 w-2 rounded-full mr-3 animate-pulse" :class="user.activo ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-red-400'"></div>
                <span class="text-xs font-bold" :class="user.activo ? 'text-emerald-700' : 'text-red-500'">{{ user.activo ? 'Activo' : 'Suspendido' }}</span>
              </div>
            </td>
            <td class="px-8 py-5 text-right">
              <button 
                @click="$emit('edit-user', user)" 
                class="inline-flex items-center px-4 py-2 bg-slate-50 text-slate-500 rounded-xl text-xs font-black uppercase tracking-widest hover:bg-blue-600 hover:text-white hover:shadow-lg hover:shadow-blue-200 transition-all hover:scale-105"
              >
                <Settings class="h-3.5 w-3.5 mr-2" />
                Configurar
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Empty State if needed later -->
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api/client'
import { 
  UserPlus, Settings 
} from 'lucide-vue-next'

const emit = defineEmits(['new-user', 'edit-user'])

const usuariosList = ref<any[]>([])

const loadUsuarios = async () => {
  try {
    const res = await api.get('/usuarios/')
    usuariosList.value = res.data
    console.log('Usuarios cargados:', res.data)
  } catch (err) {
    console.error('Error cargando usuarios:', err)
  }
}

onMounted(loadUsuarios)

defineExpose({ loadUsuarios })
</script>
