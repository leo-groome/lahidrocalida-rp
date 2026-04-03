<template>
  <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 gap-6 animate-in slide-in-from-bottom-4 duration-500">
    <div 
      v-for="c in categorias" 
      :key="c.id" 
      class="aspect-square bg-white border border-slate-100 rounded-[2rem] flex flex-col items-center justify-center gap-4 group hover:shadow-xl hover:shadow-indigo-500/10 hover:border-indigo-200 transition-all cursor-pointer relative overflow-hidden"
      @click="$emit('edit', c)"
    >
      <div class="h-14 w-14 rounded-2xl bg-slate-50 flex items-center justify-center text-slate-400 group-hover:bg-indigo-600 group-hover:text-white shadow-inner transition-all duration-300 group-hover:rotate-6">
        <TagIcon class="h-6 w-6" />
      </div>
      <span class="text-[11px] font-black text-slate-700 uppercase tracking-widest text-center px-4 leading-tight">{{ c.nombre }}</span>
      
      <div class="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <Edit3 class="h-3 w-3 text-indigo-400" />
      </div>
    </div>
    
    <button 
      @click="$emit('new')"
      class="aspect-square border-2 border-dashed border-slate-200 rounded-[2rem] flex flex-col items-center justify-center gap-3 text-slate-400 hover:border-blue-400 hover:bg-blue-50/30 hover:text-blue-500 transition-all duration-300"
    >
      <div class="h-12 w-12 rounded-full bg-slate-50 flex items-center justify-center">
        <Plus class="h-6 w-6" />
      </div>
      <span class="text-[11px] font-black uppercase tracking-widest text-center">Añadir Familia</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { Tag as TagIcon, Edit3, Plus } from 'lucide-vue-next'

defineProps<{
  categorias: any[]
}>()

defineEmits(['edit', 'new'])
</script>