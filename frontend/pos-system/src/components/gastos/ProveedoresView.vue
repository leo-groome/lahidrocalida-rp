<template>
  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8 animate-in slide-in-from-bottom-4 duration-500">
    <div 
      v-for="p in proveedores" 
      :key="p.id" 
      class="bg-white p-8 rounded-[2.5rem] border border-slate-100 shadow-sm hover:shadow-xl hover:shadow-blue-500/5 hover:border-blue-200 transition-all duration-300 group relative overflow-hidden"
    >
      <div class="absolute top-0 right-0 w-32 h-32 bg-blue-50/30 rounded-full -mr-16 -mt-16 transition-transform group-hover:scale-150 duration-700"></div>
      
      <div class="relative z-10">
        <div class="flex items-start justify-between mb-8">
          <div class="h-16 w-16 rounded-3xl bg-blue-50 flex items-center justify-center text-blue-600 shadow-inner group-hover:bg-blue-600 group-hover:text-white transition-all duration-300">
            <Truck class="h-8 w-8" />
          </div>
          <button @click="$emit('edit', p)" class="h-10 w-10 flex items-center justify-center rounded-full text-slate-300 hover:bg-slate-50 hover:text-blue-600 transition-all">
            <Edit3 class="h-5 w-5" />
          </button>
        </div>
        
        <div class="space-y-4">
          <h4 class="text-xl font-black text-slate-900 group-hover:text-blue-600 transition-colors">{{ p.nombre }}</h4>
          
          <div class="space-y-2">
            <div class="flex items-center text-sm text-slate-500 font-bold">
              <div class="w-8 h-8 rounded-lg bg-slate-50 flex items-center justify-center mr-3 group-hover:bg-white transition-colors">
                <Phone class="h-4 w-4 text-slate-400" />
              </div>
              {{ p.telefono }}
            </div>
            <div class="flex items-start text-sm text-slate-500 font-bold leading-relaxed">
              <div class="w-8 h-8 rounded-lg bg-slate-50 flex items-center justify-center mr-3 flex-shrink-0 group-hover:bg-white transition-colors">
                <MapPin class="h-4 w-4 text-slate-400" />
              </div>
              {{ p.direccion }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Truck, Edit3, Phone, MapPin } from 'lucide-vue-next'

defineProps<{
  proveedores: any[]
}>()

defineEmits(['edit'])
</script>