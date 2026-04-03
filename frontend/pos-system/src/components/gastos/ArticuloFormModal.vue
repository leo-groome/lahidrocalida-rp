<template>
  <div class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center z-[60] animate-in fade-in duration-200">
    <div class="bg-white p-8 rounded-[3rem] shadow-2xl w-full max-w-lg animate-in zoom-in-95 duration-200 overflow-hidden">
      <div class="mb-8">
        <h3 class="text-2xl font-black text-slate-800 tracking-tight">
          {{ initialData ? 'Editar Artículo' : 'Nuevo Artículo' }}
        </h3>
        <p class="text-slate-400 text-sm font-bold uppercase tracking-widest mt-1">Catálogo de insumos operativos</p>
      </div>

      <div class="space-y-6">
        <!-- Main Field: Nombre -->
        <div class="space-y-2">
          <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Descripción del Artículo</label>
          <input 
            v-model="form.nombre" 
            placeholder="Ej. Tomatillo, Servilletas..." 
            class="w-full px-6 py-4 bg-slate-50 border-none rounded-2xl text-sm font-bold border border-slate-100 focus:ring-2 focus:ring-blue-500/20 shadow-inner transition-all"
          >
        </div>

        <div class="grid grid-cols-2 gap-6">
          <!-- Categoria -->
          <div class="space-y-2">
            <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Categoría / Familia</label>
            <select 
              v-model="form.categoria_id" 
              class="w-full px-6 py-4 bg-slate-50 border-none rounded-2xl text-sm font-bold border border-slate-100 focus:ring-2 focus:ring-blue-500/20 shadow-inner transition-all appearance-none cursor-pointer"
            >
              <option :value="null" disabled>Seleccionar...</option>
              <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.nombre }}</option>
            </select>
          </div>

          <!-- Unidad -->
          <div class="space-y-2">
            <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Unidad de Medida</label>
            <select 
              v-model="form.unidad" 
              class="w-full px-6 py-4 bg-slate-50 border-none rounded-2xl text-sm font-bold border border-slate-100 focus:ring-2 focus:ring-blue-500/20 shadow-inner transition-all appearance-none cursor-pointer"
            >
              <option value="kg">kg</option>
              <option value="g">g</option>
              <option value="lt">lt</option>
              <option value="ml">ml</option>
              <option value="pza">pza</option>
              <option value="caja">caja</option>
              <option value="paq">paq</option>
            </select>
          </div>
        </div>

        <!-- Costo Estandar -->
        <div class="space-y-2">
          <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Costo Estándar Sugerido ($)</label>
          <div class="relative">
             <div class="absolute inset-y-0 left-0 pl-6 flex items-center pointer-events-none">
                <span class="text-slate-400 font-black">$</span>
             </div>
             <input 
               v-model.number="form.costo_estandar" 
               type="number"
               step="0.01"
               placeholder="0.00" 
               class="w-full pl-12 pr-6 py-4 bg-slate-50 border-none rounded-2xl text-lg font-black border border-slate-100 focus:ring-2 focus:ring-blue-500/20 shadow-inner transition-all"
             >
          </div>
        </div>
      </div>

      <div class="flex items-center justify-end gap-4 mt-12 bg-slate-50 -mx-8 -mb-8 p-8 border-t border-slate-100">
        <button 
          @click="$emit('close')" 
          class="px-8 py-3 bg-white text-slate-500 border border-slate-200 rounded-2xl text-xs font-black uppercase tracking-widest hover:bg-slate-100 transition-all shadow-sm"
        >
          Cancelar
        </button>
        <button 
          @click="save" 
          :disabled="!form.nombre || !form.categoria_id"
          class="px-8 py-4 bg-slate-900 text-white rounded-2xl text-xs font-black uppercase tracking-widest shadow-xl shadow-slate-200 hover:bg-slate-800 disabled:opacity-50 transition-all hover:-translate-y-0.5 active:translate-y-0"
        >
          {{ initialData ? 'Actualizar Artículo' : 'Registrar Artículo' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api/client'

const props = defineProps<{
  initialData?: any,
  categories: any[]
}>()

const emit = defineEmits(['close', 'save'])

const form = ref({
  nombre: '',
  categoria_id: null as number | null,
  unidad: 'kg',
  costo_estandar: 0
})

onMounted(() => {
  if (props.initialData) {
    // Note: for edit, initialData category id should be checked
    form.value = { 
      ...props.initialData,
      categoria_id: props.initialData.categoria_id || props.initialData.categoria?.id 
    }
  }
})

const save = async () => {
  try {
    if (props.initialData?.id) {
      await api.put(`/gastos/articulos/${props.initialData.id}`, form.value)
    } else {
      await api.post('/gastos/articulos', form.value)
    }
    emit('save')
  } catch (error) {
    alert('Error al guardar artículo')
  }
}
</script>
