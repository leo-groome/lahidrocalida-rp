<template>
  <div class="fixed inset-0 bg-slate-900/60 backdrop-blur-md flex items-center justify-center z-[150] p-4 md:p-8 animate-in fade-in duration-300">
    <div class="bg-white rounded-[3rem] shadow-2xl w-full max-w-5xl max-h-[92vh] flex flex-col overflow-hidden border border-white/20 animate-in zoom-in-95 duration-500">
      
      <!-- Header -->
      <div class="px-10 py-8 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
        <div class="space-y-1">
          <p class="text-[10px] font-black tracking-[0.3em] text-indigo-400 uppercase">Registro Contable</p>
          <h2 class="text-3xl font-black text-slate-900 tracking-tight flex items-center gap-3">
            {{ isEditing ? 'EDITAR' : 'NUEVO' }} <span class="text-indigo-600">GASTO</span>
          </h2>
        </div>
        <button 
          @click="$emit('close')" 
          class="w-12 h-12 flex items-center justify-center rounded-2xl bg-slate-100 text-slate-400 hover:bg-slate-900 hover:text-white transition-all duration-300 group"
        >
          <X class="w-6 h-6 group-hover:rotate-90 transition-transform duration-500" />
        </button>
      </div>
      
      <!-- Body Scrollable -->
      <div class="p-10 overflow-y-auto flex-1 custom-scrollbar space-y-10">
        <form @submit.prevent="submitForm" id="gastoForm" class="space-y-10">
          
          <!-- Section Heading: General Info -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-10">
            <div class="space-y-4">
              <label class="text-[10px] font-black tracking-widest text-slate-400 uppercase ml-1 flex items-center gap-2">
                <Calendar class="w-3 h-3" /> Fecha y Hora
              </label>
              <div class="relative group">
                <input 
                  type="datetime-local" 
                  v-model="form.fecha_gasto"
                  class="w-full bg-slate-50 border-0 rounded-2xl px-6 py-4 text-sm font-bold text-slate-700 focus:ring-2 focus:ring-indigo-500 transition-all outline-none"
                  required
                >
              </div>
            </div>
            
            <div class="space-y-4">
              <label class="text-[10px] font-black tracking-widest text-slate-400 uppercase ml-1 flex items-center gap-2">
                <Truck class="w-3 h-3" /> Proveedor Responsable
              </label>
              <SearchableSelect 
                 v-model="form.proveedor_id" 
                 :options="proveedores"
                 placeholder="Selecciona el proveedor..."
                 class="w-full"
              />
            </div>
          </div>

          <!-- Section Heading: Details -->
          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
             <div class="space-y-4">
               <label class="text-[10px] font-black tracking-widest text-slate-400 uppercase ml-1">Tipo de Gasto</label>
               <select v-model="form.tipo_gasto" class="w-full bg-slate-50 border-0 rounded-2xl px-6 py-4 text-sm font-bold text-slate-700 focus:ring-2 focus:ring-indigo-500 transition-all outline-none appearance-none cursor-pointer">
                 <option value="directo">Directo (Insumos)</option>
                 <option value="indirecto">Indirecto (Servicios)</option>
               </select>
             </div>
             <div class="space-y-4">
               <label class="text-[10px] font-black tracking-widest text-slate-400 uppercase ml-1">Método de Pago</label>
               <select 
                 v-model="form.metodo_pago" 
                 class="w-full bg-slate-50 border-0 rounded-2xl px-6 py-4 text-sm font-bold text-slate-700 focus:ring-2 focus:ring-indigo-500 transition-all outline-none appearance-none cursor-pointer disabled:opacity-50"
                 :disabled="pagadoDesdeCaja"
               >
                 <option value="efectivo">Efectivo 💵</option>
                 <option value="tarjeta">Tarjeta 💳</option>
               </select>
             </div>
             <div class="space-y-4">
               <label class="text-[10px] font-black tracking-widest text-slate-400 uppercase ml-1 flex items-center gap-2">
                <Hash class="w-3 h-3" /> Folio / Factura
               </label>
               <input v-model="form.folio" type="text" class="w-full bg-slate-50 border-0 rounded-2xl px-6 py-4 text-sm font-bold text-slate-700 focus:ring-2 focus:ring-indigo-500 transition-all outline-none" placeholder="Opcional">
             </div>
          </div>

          <!-- Opción de Caja - High Visibility -->
          <div v-if="turnoId || isEditing" class="p-1">
            <label :class="[
              'relative flex items-center gap-6 p-6 rounded-[2rem] border-2 transition-all cursor-pointer group',
              pagadoDesdeCaja ? 'bg-indigo-600 border-indigo-600 shadow-xl shadow-indigo-100' : 'bg-slate-50 border-slate-100 hover:border-indigo-200'
            ]">
              <div :class="[
                'w-8 h-8 rounded-full flex items-center justify-center transition-all',
                pagadoDesdeCaja ? 'bg-white text-indigo-600' : 'bg-slate-200 text-slate-400'
              ]">
                <Check v-if="pagadoDesdeCaja" class="w-5 h-5" />
                <div v-else class="w-3 h-3 bg-white rounded-full"></div>
              </div>
              
              <input 
                v-model="pagadoDesdeCaja"
                type="checkbox"
                class="hidden"
              />
              
              <div class="flex-1">
                <span :class="['block text-sm font-black tracking-tight', pagadoDesdeCaja ? 'text-white' : 'text-slate-900']">
                  ¿Pagar con efectivo de caja actual?
                </span>
                <span :class="['block text-[11px] font-bold opacity-70 uppercase tracking-widest', pagadoDesdeCaja ? 'text-white/80' : 'text-slate-500']">
                  Se descontará del arqueo del turno #{{ turnoId }}
                </span>
              </div>

              <div :class="[
                'w-12 h-12 rounded-2xl flex items-center justify-center transition-all',
                pagadoDesdeCaja ? 'bg-white/20 text-white' : 'bg-slate-100 text-slate-400'
              ]">
                <Banknote class="w-6 h-6" />
              </div>
            </label>
          </div>
          
          <!-- Descripción -->
          <div class="space-y-4">
            <label class="text-[10px] font-black tracking-widest text-slate-400 uppercase ml-1">Observaciones / Notas adicionales</label>
            <textarea v-model="form.descripcion" rows="3" class="w-full bg-slate-50 border-0 rounded-[1.5rem] px-6 py-4 text-sm font-bold text-slate-700 focus:ring-2 focus:ring-indigo-500 transition-all outline-none resize-none" placeholder="Escribe aquí cualquier detalle extra del gasto..."></textarea>
          </div>

          <!-- SECCIÓN DETALLES (artículos) -->
          <div>
             <GastoDetallesEditor
               v-model:detalles="form.detalles"
               v-model:total-manual="form.total_manual"
               :articulos="articulos"
             />
          </div>

        </form>
      </div>
      
      <!-- Footer -->
      <div class="px-10 py-8 border-t border-slate-100 bg-slate-50/50 flex flex-col md:flex-row justify-between items-center gap-6">
        <div class="flex items-center gap-4">
          <div class="w-12 h-12 bg-white rounded-2xl flex items-center justify-center text-indigo-600 shadow-sm">
            <Calculator class="w-6 h-6" />
          </div>
          <div>
            <p class="text-[10px] font-black tracking-widest text-slate-400 uppercase mb-0.5">Total Liquidación</p>
            <p class="text-2xl font-black text-slate-900 tracking-tighter">
              ${{ formatCurrency(form.total_manual || sumaDetalles) }}
            </p>
          </div>
        </div>

        <div class="flex items-center gap-4 w-full md:w-auto">
          <button 
            type="button" 
            @click="$emit('close')" 
            class="flex-1 md:flex-none px-8 py-4 bg-white text-slate-500 rounded-2xl text-[10px] font-black uppercase tracking-widest hover:bg-slate-100 transition-all"
          >
            Cancelar
          </button>
          <button 
            type="submit" 
            form="gastoForm" 
            class="flex-1 md:flex-none h-[60px] px-12 bg-indigo-600 text-white rounded-2xl text-[10px] font-black uppercase tracking-widest shadow-xl shadow-indigo-200 hover:bg-indigo-700 hover:-translate-y-1 transition-all active:translate-y-0"
          >
            {{ isEditing ? 'Actualizar Registro' : 'Confirmar Gasto' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, watch } from 'vue'
import api from '@/api/client'
import SearchableSelect from './SearchableSelect.vue'
import GastoDetallesEditor from './GastoDetallesEditor.vue'
import {
  X, Calendar, Truck, Banknote,
  Hash, Calculator, Check
} from 'lucide-vue-next'

const props = defineProps<{
  initialData?: any
  turnoId?: number | null
}>()

const emit = defineEmits(['close', 'save'])

const proveedores = ref<any[]>([])
const articulos = ref<any[]>([])

const formatCurrency = (val: number) => val.toLocaleString('es-MX', { 
  minimumFractionDigits: 2, 
  maximumFractionDigits: 2 
})

// Form state
const form = reactive({
  id: null,
  proveedor_id: null,
  fecha_gasto: new Date().toISOString().slice(0, 16),
  tipo_gasto: 'directo',
  metodo_pago: 'efectivo',
  folio: '',
  descripcion: '',
  notas: '',
  total_manual: null as number | null,
  turno_id: null as number | null,
  detalles: [] as any[]
})

const pagadoDesdeCaja = ref(false)

watch(pagadoDesdeCaja, (val) => {
  if (val) {
    form.metodo_pago = 'efectivo'
    form.turno_id = props.turnoId || null
  } else {
    form.turno_id = null
  }
})

const isEditing = computed(() => !!form.id)

const sumaDetalles = computed(() => {
  return form.detalles.reduce((sum, d) => {
    const linea = d.subtotal_linea != null
      ? Number(d.subtotal_linea)
      : (Number(d.cantidad) || 0) * (Number(d.precio_unitario) || 0)
    return sum + (Number(linea) || 0)
  }, 0)
})

const loadCatalogos = async () => {
  try {
    const [provs, arts] = await Promise.all([
      api.get('/gastos/proveedores'),
      api.get('/gastos/articulos')
    ])
    proveedores.value = provs.data
    articulos.value = arts.data
  } catch (e) { console.error(e) }
}

const submitForm = async () => {
  try {
    if (!form.proveedor_id) return alert('Selecciona un proveedor')

    const detalles = form.tipo_gasto === 'nomina'
      ? []
      : form.detalles.map((d: any) => ({
          articulo_id: d.articulo_id,
          cantidad: d.cantidad,
          precio_unitario: d.precio_unitario,
          subtotal_linea: d.subtotal_linea,
        }))

    const payload = {
       ...form,
       detalles,
       fecha_gasto: form.fecha_gasto ? new Date(form.fecha_gasto).toISOString() : null
    }

    if (isEditing.value) {
       await api.put(`/gastos/${form.id}`, payload)
    } else {
       await api.post('/gastos/', payload)
    }
    
    emit('save')
  } catch (e: any) {
    alert('Error al guardar: ' + (e.response?.data?.detail || e.message))
  }
}

onMounted(() => {
  // La nómina se gestiona en el módulo de Compras (tanda de empleados).
  if (props.initialData?.tipo_gasto === 'nomina') {
    alert('La nómina se edita desde el módulo de Compras. Para cambiarla, elimínala y créala de nuevo.')
    emit('close')
    return
  }
  loadCatalogos()
  if (props.initialData) {
    const d = props.initialData
    form.id = d.id
    form.proveedor_id = d.proveedor_id
    form.tipo_gasto = d.tipo_gasto
    form.metodo_pago = d.metodo_pago
    form.folio = d.folio
    form.descripcion = d.descripcion
    form.notas = d.notas
    form.total_manual = d.total_manual
    form.turno_id = d.turno_id
    
    if (d.turno_id) {
      pagadoDesdeCaja.value = true
    }
    
    if (d.fecha_gasto) {
       const dateObj = new Date(d.fecha_gasto)
       const tzOffset = dateObj.getTimezoneOffset() * 60000
       const localISOTime = (new Date(dateObj.getTime() - tzOffset)).toISOString().slice(0, 16)
       form.fecha_gasto = localISOTime
    }
    
    if (d.detalles) {
       form.detalles = d.detalles.map((det: any) => {
          const cantidad = Number(det.cantidad)
          const precio_unitario = Number(det.precio_unitario)
          const subtotal_linea = det.subtotal_linea != null
             ? Number(det.subtotal_linea)
             : Number((cantidad * precio_unitario).toFixed(2))
          // Marcar como editado manualmente si no cuadra con cantidad×unitario,
          // para no sobreescribir el ajuste al reeditar la línea.
          const _editadoManual = Math.abs(subtotal_linea - cantidad * precio_unitario) > 0.005
          return { articulo_id: det.articulo_id, cantidad, precio_unitario, subtotal_linea, _editadoManual }
       })
    }
  } else {
     form.detalles.push({ articulo_id: null, cantidad: 1, precio_unitario: 0, subtotal_linea: 0, _editadoManual: false })
  }
})
</script>

<style scoped>
.animate-in {
  animation: fadeIn 0.5s ease-out forwards;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

select {
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%23475569' stroke-width='2'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M19 9l-7 7-7-7'%3E%3C/path%3E%3C/svg%3E");
  background-position: right 1.5rem center;
  background-repeat: no-repeat;
  background-size: 1.5em;
  padding-right: 3.5rem;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #e2e8f0;
  border-radius: 10px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: #cbd5e1;
}
</style>
