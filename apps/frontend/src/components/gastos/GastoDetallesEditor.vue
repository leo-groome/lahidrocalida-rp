<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3 px-1">
      <div class="space-y-1">
        <h3 class="text-xs font-black text-slate-400 uppercase tracking-[0.2em]">Desglose de Artículos</h3>
        <p class="text-[10px] text-slate-300 font-bold">Cantidad · precio unitario · total (editable)</p>
      </div>
      <button
        type="button"
        @click="addDetalle"
        class="px-5 py-2.5 bg-indigo-50 text-indigo-600 rounded-xl text-[10px] font-black uppercase tracking-widest hover:bg-indigo-600 hover:text-white transition-all flex items-center justify-center gap-2"
      >
        <Plus class="w-3.5 h-3.5" /> Agregar Artículo
      </button>
    </div>

    <div class="bg-slate-50/50 rounded-[2rem] border border-slate-100 overflow-hidden">
      <div class="p-2 space-y-2">
        <p v-if="detalles.length === 0" class="text-center py-8 text-xs font-bold text-slate-300">
          Sin artículos. Agrega el primero para empezar.
        </p>

        <!-- Cada línea: tarjeta apilada en móvil, fila en desktop -->
        <div
          v-for="(detalle, idx) in detalles"
          :key="idx"
          class="bg-white p-3 rounded-[1.25rem] shadow-sm animate-in zoom-in-95 flex flex-col md:flex-row md:items-end gap-3"
        >
          <!-- Artículo -->
          <div class="flex-1 min-w-0 space-y-1">
            <label class="block text-[8px] font-black text-slate-300 uppercase tracking-widest ml-1 md:hidden">Artículo</label>
            <SearchableSelect
              v-model="detalle.articulo_id"
              :options="articulos"
              placeholder="Buscar artículo..."
              class="w-full"
            />
          </div>

          <!-- Cantidad / P.Unit / Total -->
          <div class="grid grid-cols-3 gap-2 md:flex md:items-end md:gap-3">
            <div class="space-y-1 md:w-24">
              <label class="block text-[8px] font-black text-slate-300 uppercase tracking-widest ml-1">Cantidad</label>
              <input
                type="number"
                step="0.01"
                min="0"
                v-model.number="detalle.cantidad"
                @input="recalcLinea(idx)"
                class="w-full bg-slate-50 border-0 rounded-xl px-3 py-2.5 text-sm font-black text-slate-700 outline-none focus:ring-2 focus:ring-indigo-500 text-center"
              >
            </div>
            <div class="space-y-1 md:w-28">
              <label class="block text-[8px] font-black text-slate-300 uppercase tracking-widest ml-1">P. Unitario</label>
              <div class="relative">
                <span class="absolute left-2.5 top-1/2 -translate-y-1/2 text-[10px] font-black text-slate-300">$</span>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  v-model.number="detalle.precio_unitario"
                  @input="recalcLinea(idx)"
                  class="w-full bg-slate-50 border-0 rounded-xl pl-5 pr-2 py-2.5 text-sm font-black text-slate-700 outline-none focus:ring-2 focus:ring-indigo-500 text-right"
                >
              </div>
            </div>
            <div class="space-y-1 md:w-32">
              <label class="block text-[8px] font-black text-indigo-300 uppercase tracking-widest ml-1">Total</label>
              <div class="relative">
                <span class="absolute left-2.5 top-1/2 -translate-y-1/2 text-[10px] font-black text-indigo-300">$</span>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  v-model.number="detalle.subtotal_linea"
                  @input="detalle._editadoManual = true"
                  class="w-full bg-indigo-50/60 border border-indigo-100 rounded-xl pl-5 pr-2 py-2.5 text-sm font-black text-indigo-900 outline-none focus:ring-2 focus:ring-indigo-500 text-right"
                >
              </div>
            </div>
          </div>

          <!-- Eliminar -->
          <button
            type="button"
            @click="removeDetalle(idx)"
            class="self-end md:self-auto w-10 h-[42px] flex items-center justify-center rounded-xl text-slate-300 hover:bg-rose-50 hover:text-rose-500 transition-all flex-shrink-0"
          >
            <Trash2 class="w-4 h-4" />
          </button>
        </div>
      </div>

      <!-- Resumen -->
      <div class="bg-indigo-50/50 p-5 flex flex-col md:flex-row justify-between items-stretch md:items-center gap-5 border-t border-indigo-100">
        <div class="flex items-center gap-4">
          <div class="p-3 bg-white rounded-2xl shadow-sm text-indigo-600">
            <ShoppingBag class="w-5 h-5" />
          </div>
          <div>
            <p class="text-[10px] font-black tracking-widest text-indigo-400 uppercase">Suma de Artículos</p>
            <p class="text-lg font-black text-indigo-900 tracking-tighter">${{ formatCurrency(sumaDetalles) }}</p>
          </div>
        </div>

        <div class="relative w-full md:w-auto">
          <label class="absolute -top-3 left-4 bg-white px-2 text-[8px] font-black text-indigo-400 uppercase tracking-widest rounded-full border border-indigo-100 shadow-sm">Total Manual Ajustado</label>
          <div class="flex items-center gap-3">
            <span class="text-lg font-black text-slate-300">$</span>
            <input
              type="number"
              step="0.01"
              min="0"
              v-model.number="totalManual"
              class="w-full md:w-48 bg-white border-2 border-indigo-200 rounded-2xl px-6 py-3.5 text-xl font-black text-indigo-900 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all outline-none text-right shadow-lg shadow-indigo-100/50"
              placeholder="0.00"
            >
          </div>
          <p class="text-[9px] text-indigo-400 font-bold mt-2 text-right">Dejar en blanco para usar la suma automática</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import SearchableSelect from './SearchableSelect.vue'
import { Plus, Trash2, ShoppingBag } from 'lucide-vue-next'

defineProps<{
  articulos: any[]
}>()

// Líneas: { articulo_id, cantidad, precio_unitario, subtotal_linea, _editadoManual }
const detalles = defineModel<any[]>('detalles', { default: () => [] })
const totalManual = defineModel<number | null>('totalManual', { default: null })

const formatCurrency = (val: number) =>
  (val || 0).toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const sumaDetalles = computed(() =>
  detalles.value.reduce((sum, d) => {
    const linea = d.subtotal_linea != null
      ? Number(d.subtotal_linea)
      : (Number(d.cantidad) || 0) * (Number(d.precio_unitario) || 0)
    return sum + (Number(linea) || 0)
  }, 0)
)

// Recalcula el total de línea salvo que el usuario lo haya editado a mano.
const recalcLinea = (idx: number) => {
  const d = detalles.value[idx]
  if (!d || d._editadoManual) return
  const cant = Number(d.cantidad) || 0
  const pu = Number(d.precio_unitario) || 0
  d.subtotal_linea = Number((cant * pu).toFixed(2))
}

const addDetalle = () => {
  detalles.value.push({ articulo_id: null, cantidad: 1, precio_unitario: 0, subtotal_linea: 0, _editadoManual: false })
}

const removeDetalle = (idx: number) => {
  detalles.value.splice(idx, 1)
}
</script>
