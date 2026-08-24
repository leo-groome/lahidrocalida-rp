<template>
  <div class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center z-[60] animate-in fade-in duration-200">
    <div class="bg-white p-8 rounded-3xl shadow-2xl w-full max-w-md animate-in zoom-in-95 duration-200">
      <h3 class="text-xl font-bold text-slate-800 mb-6">
        {{ initialData ? 'Editar Familia' : 'Nueva Familia' }}
      </h3>
      <div class="space-y-4">
        <div class="space-y-1">
          <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Nombre de la Categoría</label>
          <input 
            v-model="form.nombre" 
            placeholder="Ej. Alimentos, Limpieza..." 
            class="w-full px-4 py-3 bg-slate-50 border-none rounded-2xl text-sm font-bold border border-slate-100 focus:ring-2 focus:ring-indigo-500/20 transition-all"
          >
        </div>
      </div>
      <div class="flex justify-end gap-3 mt-8">
        <button 
          @click="$emit('close')" 
          class="px-6 py-3 bg-slate-50 text-slate-500 rounded-2xl text-xs font-black uppercase tracking-widest hover:bg-slate-100 transition-all"
        >
          Cancelar
        </button>
        <button 
          @click="save" 
          :disabled="!form.nombre"
          class="px-6 py-3 bg-indigo-600 text-white rounded-2xl text-xs font-black uppercase tracking-widest shadow-lg shadow-indigo-200 hover:bg-indigo-700 disabled:opacity-50 transition-all"
        >
          {{ initialData ? 'Actualizar' : 'Guardar Familia' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api/client'

const props = defineProps<{
  initialData?: any
}>()

const emit = defineEmits(['close', 'save'])

const form = ref({
  nombre: ''
})

onMounted(() => {
  if (props.initialData) {
    form.value = { ...props.initialData }
  }
})

const save = async () => {
  try {
    if (props.initialData?.id) {
      await api.put(`/gastos/categorias-articulo/${props.initialData.id}`, form.value)
    } else {
      await api.post('/gastos/categorias-articulo', form.value)
    }
    emit('save')
  } catch (error) {
    alert('Error al guardar categoría')
  }
}
</script>
