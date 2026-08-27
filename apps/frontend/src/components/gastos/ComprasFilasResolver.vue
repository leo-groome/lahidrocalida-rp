<template>
  <div class="space-y-3">
    <div
      v-for="fila in filas"
      :key="fila.id"
      class="bg-slate-50 rounded-2xl p-3 space-y-2 border"
      :class="filaLista(fila) ? 'border-emerald-200' : 'border-amber-300'"
    >
      <p class="text-[11px] font-bold text-slate-400 truncate">"{{ fila.raw }}"</p>

      <!-- Resolución de artículo -->
      <div class="space-y-1">
        <label class="block text-[8px] font-black text-slate-300 uppercase tracking-widest ml-1">Artículo</label>
        <SearchableSelect
          v-model="fila.articulo_id"
          :options="opcionesArticulo(fila)"
          placeholder="Selecciona o crea el artículo..."
          @update:modelValue="(val) => onSeleccionArticulo(fila, val)"
        />
      </div>

      <div class="grid grid-cols-3 gap-2">
        <div class="space-y-1">
          <label class="block text-[8px] font-black text-slate-300 uppercase tracking-widest ml-1">Cantidad</label>
          <input
            type="number" step="0.01" min="0" inputmode="decimal"
            v-model.number="fila.cantidad"
            class="w-full bg-white border border-slate-200 rounded-xl px-2 py-2 text-sm font-black text-slate-700 outline-none focus:ring-2 focus:ring-indigo-500 text-center"
          >
        </div>
        <div class="space-y-1">
          <label class="block text-[8px] font-black text-slate-300 uppercase tracking-widest ml-1">Unidad</label>
          <select
            v-model="fila.unidad"
            class="w-full bg-white border border-slate-200 rounded-xl px-2 py-2 text-sm font-bold text-slate-700 outline-none focus:ring-2 focus:ring-indigo-500 text-center"
          >
            <option v-for="u in unidades" :key="u" :value="u">{{ u }}</option>
          </select>
        </div>
        <div class="space-y-1">
          <label class="block text-[8px] font-black text-slate-300 uppercase tracking-widest ml-1">Monto ($)</label>
          <input
            type="number" step="0.01" min="0" inputmode="decimal"
            v-model.number="fila.monto"
            class="w-full bg-white border border-slate-200 rounded-xl px-2 py-2 text-sm font-black text-slate-700 outline-none focus:ring-2 focus:ring-indigo-500 text-center"
          >
        </div>
      </div>

      <div class="flex items-center justify-between px-1">
        <p class="text-[10px] font-bold text-slate-400">
          P. unitario: <span class="text-indigo-600 font-black">${{ precioUnitarioFila(fila).toFixed(2) }}</span>
        </p>
        <button type="button" @click="emit('quitar-fila', fila.id)" class="text-[10px] font-black text-rose-400 hover:text-rose-600">
          Quitar
        </button>
      </div>
      <p v-if="fila.error" class="text-[10px] font-bold text-amber-600">{{ fila.error }}</p>
    </div>

    <ArticuloFormModal
      v-if="creandoPara"
      :initial-data="{ nombre: creandoPara.nombreSugerido, unidad: creandoPara.unidadSugerida, categoria_id: null, costo_estandar: 0 }"
      :categories="categorias"
      @close="creandoPara = null"
      @save="onArticuloCreado"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import {
  filaLista,
  precioUnitarioFila,
  type FilaCompra,
  type UnidadCanonica,
} from '@/utils/parseCompraTexto'
import { api } from '@/api/client'
import SearchableSelect from './SearchableSelect.vue'
import ArticuloFormModal from './ArticuloFormModal.vue'

// `filas` se muta en sitio (cantidad/unidad/monto/articulo_id); el padre es dueño
// del array y observa esos campos. La eliminación la maneja el padre vía `quitar-fila`.
const props = defineProps<{
  filas: FilaCompra[]
  articulos: any[]
  categorias: any[]
}>()

const emit = defineEmits<{
  'quitar-fila': [id: number]
  'articulo-creado': [articulos: any[]]
}>()

const unidades: UnidadCanonica[] = ['kg', 'g', 'lt', 'ml', 'pza', 'caja', 'paq']

function normalizar(s: string): string {
  return s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim()
}

function opcionesArticulo(fila: FilaCompra) {
  const crearOpcion = fila.nombreArticulo
    ? [{ id: `crear:${fila.id}`, nombre: `+ Crear "${fila.nombreArticulo}"` }]
    : []
  return [...props.articulos, ...crearOpcion]
}

const creandoPara = ref<{ filaId: number; nombreSugerido: string; unidadSugerida: string } | null>(null)

function onSeleccionArticulo(fila: FilaCompra, valor: any) {
  if (typeof valor === 'string' && valor.startsWith('crear:')) {
    creandoPara.value = {
      filaId: fila.id,
      nombreSugerido: fila.nombreArticulo,
      unidadSugerida: fila.unidad ?? 'kg',
    }
    fila.articulo_id = null
  }
}

async function onArticuloCreado() {
  if (!creandoPara.value) return
  const { filaId, nombreSugerido } = creandoPara.value
  try {
    const { data: articulosActualizados } = await api.get('/gastos/articulos')
    emit('articulo-creado', articulosActualizados)
    const nuevo = articulosActualizados.find(
      (a: any) => normalizar(a.nombre) === normalizar(nombreSugerido),
    )
    const fila = props.filas.find((f) => f.id === filaId)
    if (fila && nuevo) fila.articulo_id = nuevo.id
  } finally {
    creandoPara.value = null
  }
}
</script>
