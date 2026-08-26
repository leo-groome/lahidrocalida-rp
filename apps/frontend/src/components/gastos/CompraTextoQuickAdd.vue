<template>
  <div class="p-4 space-y-4">
    <div class="space-y-2">
      <label class="text-xs font-black text-slate-400 uppercase tracking-widest ml-1">
        Escribe tus compras, una por línea
      </label>
      <textarea
        v-model="texto"
        rows="4"
        placeholder="350 pesos 6kg cueritos&#10;120 pesos 2kg jitomate"
        class="w-full px-4 py-3 text-sm border border-slate-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-[#00126D]/20 focus:border-[#00126D] resize-none transition-colors font-medium"
      />
      <button
        type="button"
        @click="analizar"
        :disabled="!texto.trim()"
        class="w-full py-3 bg-slate-100 text-slate-600 font-black rounded-2xl text-sm active:scale-[0.98] transition-all disabled:opacity-40"
      >
        Analizar texto
      </button>
    </div>

    <div v-if="filas.length" class="space-y-3 max-h-[40vh] overflow-y-auto">
      <div
        v-for="fila in filas"
        :key="fila.id"
        class="bg-slate-50 rounded-2xl p-3 space-y-2 border"
        :class="fila.ok && fila.articulo_id ? 'border-emerald-200' : 'border-amber-300'"
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
              type="number" step="0.01" min="0"
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
              type="number" step="0.01" min="0"
              v-model.number="fila.monto"
              class="w-full bg-white border border-slate-200 rounded-xl px-2 py-2 text-sm font-black text-slate-700 outline-none focus:ring-2 focus:ring-indigo-500 text-center"
            >
          </div>
        </div>

        <div class="flex items-center justify-between px-1">
          <p class="text-[10px] font-bold text-slate-400">
            P. unitario: <span class="text-indigo-600 font-black">${{ precioUnitarioFila(fila).toFixed(2) }}</span>
          </p>
          <button type="button" @click="quitarFila(fila.id)" class="text-[10px] font-black text-rose-400 hover:text-rose-600">
            Quitar
          </button>
        </div>
        <p v-if="fila.error" class="text-[10px] font-bold text-amber-600">{{ fila.error }}</p>
      </div>
    </div>

    <button
      v-if="filas.length"
      type="button"
      @click="confirmar"
      :disabled="!todasListas"
      class="w-full py-4 bg-[#00126D] text-white font-black rounded-2xl disabled:opacity-40 disabled:cursor-not-allowed active:scale-[0.98] transition-all"
    >
      Agregar {{ filas.length }} artículo(s) a la compra
    </button>

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
import { ref, computed } from 'vue'
import { parseComprasTexto, type UnidadCanonica } from '@/utils/parseCompraTexto'
import { api } from '@/api/client'
import SearchableSelect from './SearchableSelect.vue'
import ArticuloFormModal from './ArticuloFormModal.vue'

const props = defineProps<{
  articulos: any[]
  categorias: any[]
}>()

const emit = defineEmits<{
  'agregar-detalles': [detalles: any[]]
  'articulo-creado': [articulo: any]
}>()

const unidades: UnidadCanonica[] = ['kg', 'g', 'lt', 'ml', 'pza', 'caja', 'paq']

interface FilaCompra {
  id: number
  raw: string
  nombreArticulo: string
  cantidad: number | null
  unidad: UnidadCanonica | null
  monto: number | null
  articulo_id: number | null
  ok: boolean
  error?: string
}

const texto = ref('')
const filas = ref<FilaCompra[]>([])
let nextId = 1

function normalizar(s: string): string {
  return s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim()
}

function buscarMatch(nombre: string): number | null {
  const objetivo = normalizar(nombre)
  if (!objetivo) return null
  const exacto = props.articulos.find(a => normalizar(a.nombre) === objetivo)
  if (exacto) return exacto.id
  const parcial = props.articulos.filter(a => normalizar(a.nombre).includes(objetivo) || objetivo.includes(normalizar(a.nombre)))
  if (parcial.length === 1) return parcial[0].id
  return null
}

function analizar() {
  const parseadas = parseComprasTexto(texto.value)
  filas.value = parseadas.map(p => ({
    id: nextId++,
    raw: p.raw,
    nombreArticulo: p.nombreArticulo,
    cantidad: p.cantidad,
    unidad: p.unidad ?? 'kg',
    monto: p.monto,
    articulo_id: buscarMatch(p.nombreArticulo),
    ok: p.ok,
    error: p.error,
  }))
}

function opcionesArticulo(fila: FilaCompra) {
  const crearOpcion = fila.nombreArticulo
    ? [{ id: `crear:${fila.id}`, nombre: `+ Crear "${fila.nombreArticulo}"` }]
    : []
  return [...props.articulos, ...crearOpcion]
}

const creandoPara = ref<{ filaId: number, nombreSugerido: string, unidadSugerida: string } | null>(null)

function onSeleccionArticulo(fila: FilaCompra, valor: any) {
  if (typeof valor === 'string' && valor.startsWith('crear:')) {
    creandoPara.value = { filaId: fila.id, nombreSugerido: fila.nombreArticulo, unidadSugerida: fila.unidad ?? 'kg' }
    fila.articulo_id = null
  }
}

async function onArticuloCreado() {
  if (!creandoPara.value) return
  const filaId = creandoPara.value.filaId
  try {
    const { data: articulosActualizados } = await api.get('/gastos/articulos')
    const nuevo = articulosActualizados.find((a: any) =>
      normalizar(a.nombre) === normalizar(creandoPara.value!.nombreSugerido)
    )
    emit('articulo-creado', articulosActualizados)
    const fila = filas.value.find(f => f.id === filaId)
    if (fila && nuevo) fila.articulo_id = nuevo.id
  } finally {
    creandoPara.value = null
  }
}

function precioUnitarioFila(fila: FilaCompra): number {
  const cantidad = Number(fila.cantidad) || 0
  const monto = Number(fila.monto) || 0
  if (cantidad <= 0) return 0
  return Math.round((monto / cantidad) * 100) / 100
}

function quitarFila(id: number) {
  filas.value = filas.value.filter(f => f.id !== id)
}

const todasListas = computed(() =>
  filas.value.length > 0 &&
  filas.value.every(f => f.articulo_id && Number(f.cantidad) > 0 && Number(f.monto) > 0)
)

function confirmar() {
  const detalles = filas.value.map(f => {
    const precioUnitario = precioUnitarioFila(f)
    return {
      articulo_id: f.articulo_id,
      cantidad: f.cantidad,
      precio_unitario: precioUnitario,
      subtotal_linea: Math.round((Number(f.cantidad) * precioUnitario) * 100) / 100,
      _editadoManual: false,
    }
  })
  emit('agregar-detalles', detalles)
  texto.value = ''
  filas.value = []
}
</script>
