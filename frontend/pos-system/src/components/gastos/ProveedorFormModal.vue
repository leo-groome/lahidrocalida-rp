<template>
  <div class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center z-[60] animate-in fade-in duration-200">
    <div class="bg-white p-10 rounded-[3rem] shadow-2xl w-full max-w-xl animate-in zoom-in-95 duration-200 overflow-hidden">
      <div class="mb-10 flex items-center justify-between">
        <div class="space-y-1">
          <h3 class="text-3xl font-black text-slate-800 tracking-tight">
            {{ initialData ? 'Editar Socio' : 'Aliado Operativo' }}
          </h3>
          <p class="text-slate-400 text-xs font-black uppercase tracking-[0.2em] mt-1 ml-1">Eslabón de Suministro</p>
        </div>
        <div class="h-16 w-16 rounded-[1.75rem] bg-blue-50 flex items-center justify-center text-blue-600 shadow-inner ring-4 ring-white">
           <Truck class="h-8 w-8" />
        </div>
      </div>

      <div class="space-y-8">
        <!-- Main: Nombre -->
        <div class="space-y-2">
          <label class="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] ml-1">Nombre Comercial de la Empresa</label>
          <div class="relative group">
            <input 
              v-model="form.nombre" 
              placeholder="Ej. Distribuidor Regional de Carnes..." 
              class="w-full px-8 py-5 bg-slate-50 border-none rounded-[1.75rem] text-sm font-black text-slate-800 placeholder:text-slate-300 border border-slate-100 focus:ring-4 focus:ring-blue-500/10 shadow-inner group-hover:bg-slate-100 transition-all outline-none"
            >
            <div class="absolute inset-y-0 right-0 pr-6 flex items-center pointer-events-none opacity-20">
               <Building class="h-5 w-5" />
            </div>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-8">
          <!-- Telefono -->
          <div class="space-y-2">
            <label class="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] ml-1">Contacto Directo</label>
            <div class="relative group">
              <input 
                v-model="form.telefono" 
                placeholder="Teléfono (10 dígitos)" 
                class="w-full px-8 py-5 bg-slate-50 border-none rounded-[1.75rem] text-sm font-black text-slate-800 placeholder:text-slate-300 border border-slate-100 focus:ring-4 focus:ring-blue-500/10 shadow-inner group-hover:bg-slate-100 transition-all outline-none"
              >
              <div class="absolute inset-y-0 right-0 pr-6 flex items-center pointer-events-none opacity-20">
                 <Phone class="h-4 w-4" />
              </div>
            </div>
          </div>

          <!-- Direccion -->
          <div class="space-y-2">
            <label class="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] ml-1">Centro de Operación</label>
            <div class="relative group">
              <input 
                v-model="form.direccion" 
                placeholder="Calle, Número, Col..." 
                class="w-full px-8 py-5 bg-slate-50 border-none rounded-[1.75rem] text-sm font-black text-slate-800 placeholder:text-slate-300 border border-slate-100 focus:ring-4 focus:ring-blue-500/10 shadow-inner group-hover:bg-slate-100 transition-all outline-none"
              >
              <div class="absolute inset-y-0 right-0 pr-6 flex items-center pointer-events-none opacity-20">
                 <MapPin class="h-4 w-4" />
              </div>
            </div>
          </div>
        </div>

        <!-- Notas -->
        <div class="space-y-2">
          <label class="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] ml-1">Notas de Logística / Facturación</label>
          <textarea 
            v-model="form.notas" 
            placeholder="Días de crédito, horarios de entrega..." 
            rows="3"
            class="w-full px-8 py-5 bg-slate-50 border-none rounded-[2rem] text-sm font-bold text-slate-700 placeholder:text-slate-300 border border-slate-100 focus:ring-4 focus:ring-blue-500/10 shadow-inner hover:bg-slate-100 transition-all outline-none resize-none"
          ></textarea>
        </div>
      </div>

      <div class="flex items-center justify-end gap-5 mt-14 bg-slate-50 -mx-10 -mb-10 p-10 border-t border-slate-100">
        <button 
          @click="$emit('close')" 
          class="px-10 py-4 bg-white text-slate-400 border border-slate-200 rounded-[1.5rem] text-xs font-black uppercase tracking-[0.2em] hover:bg-slate-100 hover:text-slate-600 transition-all shadow-sm"
        >
          Cancelar
        </button>
        <button 
          @click="save" 
          :disabled="!form.nombre"
          class="px-10 py-4 bg-blue-600 text-white rounded-[1.5rem] text-xs font-black uppercase tracking-[0.2em] shadow-xl shadow-blue-200 hover:bg-blue-700 disabled:opacity-50 transition-all hover:scale-105 active:scale-95"
        >
          {{ initialData ? 'Actualizar Socio' : 'Afiliar Aliado' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api/client'
import { Truck, Phone, MapPin, Building } from 'lucide-vue-next'

const props = defineProps<{
  initialData?: any
}>()

const emit = defineEmits(['close', 'save'])

const form = ref({
  nombre: '',
  telefono: '',
  direccion: '',
  notas: ''
})

onMounted(() => {
  if (props.initialData) {
    form.value = { ...props.initialData }
  }
})

const save = async () => {
  try {
    if (props.initialData?.id) {
      await api.put(`/gastos/proveedores/${props.initialData.id}`, form.value)
    } else {
      await api.post('/gastos/proveedores', form.value)
    }
    emit('save')
  } catch (error) {
    alert('Error al guardar proveedor')
  }
}
</script>
