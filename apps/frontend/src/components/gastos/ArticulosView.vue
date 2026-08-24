<template>
  <div class="animate-in slide-in-from-bottom-4 duration-500 space-y-8">
    <div class="flex items-center gap-6 max-w-2xl bg-white p-2 pl-6 rounded-3xl border border-slate-200 shadow-sm group focus-within:border-blue-400 transition-all">
      <Filter class="h-5 w-5 text-slate-400 group-focus-within:text-blue-500" />
      <div class="h-6 w-px bg-slate-200"></div>
      <select 
        :value="modelValue" 
        @change="$emit('update:modelValue', ($event.target as HTMLSelectElement).value)" 
        class="flex-1 bg-transparent py-4 text-sm font-black text-slate-800 focus:outline-none appearance-none cursor-pointer"
      >
        <option :value="null">Todas las categorías</option>
        <option v-for="c in categorias" :key="c.id" :value="c.id">{{ c.nombre }}</option>
      </select>
      <div class="pr-6 text-slate-300 pointer-events-none">
        <TagIcon class="h-4 w-4" />
      </div>
    </div>
    
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      <div 
        v-for="a in articulos" 
        :key="a.id" 
        class="bg-white p-6 rounded-3xl border border-slate-100 shadow-sm hover:shadow-lg hover:border-slate-300 transition-all flex flex-col justify-between h-48 group"
      >
        <div>
          <div class="flex items-center justify-between mb-4">
            <span class="px-3 py-1 rounded-full bg-blue-50 text-[10px] font-black text-blue-600 uppercase tracking-widest">{{ a.categoria.nombre }}</span>
            <button @click="$emit('edit', a)" class="h-8 w-8 flex items-center justify-center rounded-lg text-slate-300 hover:text-blue-600 transition-all opacity-0 group-hover:opacity-100">
              <Edit3 class="h-4 w-4" />
            </button>
          </div>
          <h5 class="text-lg font-black text-slate-800 mb-1 leading-tight">{{ a.nombre }}</h5>
        </div>
        
        <div class="pt-4 border-t border-slate-50 flex items-center justify-between">
          <div class="flex flex-col">
            <span class="text-[10px] uppercase font-black text-slate-400 tracking-tighter">Costo Estándar</span>
            <span class="text-xl font-black text-slate-900">${{ a.costo_estandar }}</span>
          </div>
          <span class="text-xs font-black text-slate-400 uppercase bg-slate-50 px-3 py-1.5 rounded-xl">{{ a.unidad }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Filter, Tag as TagIcon, Edit3 } from 'lucide-vue-next'

defineProps<{
  articulos: any[],
  categorias: any[],
  modelValue: any
}>()

defineEmits(['update:modelValue', 'edit'])
</script>