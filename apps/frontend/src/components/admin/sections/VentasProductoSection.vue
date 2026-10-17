<template>
  <div class="space-y-6">
    <!-- Totales del filtro actual -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <div class="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm">
        <p class="text-xs font-bold text-slate-400 uppercase tracking-widest">Unidades vendidas</p>
        <p class="text-3xl font-extrabold text-slate-900 mt-1">{{ totales.unidades }}</p>
        <p class="text-xs text-slate-400 mt-1">{{ filtrados.length }} producto{{ filtrados.length === 1 ? '' : 's' }}{{ hayFiltro ? ' en el filtro' : '' }}</p>
      </div>
      <div class="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm">
        <p class="text-xs font-bold text-slate-400 uppercase tracking-widest">Ingreso por productos</p>
        <p class="text-3xl font-extrabold text-slate-900 mt-1">${{ dinero(totales.ingreso) }}</p>
        <p class="text-xs text-slate-400 mt-1">Incluye Uber Eats; sin propinas</p>
      </div>
      <div class="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm">
        <p class="text-xs font-bold text-slate-400 uppercase tracking-widest">Precio promedio por unidad</p>
        <p class="text-3xl font-extrabold text-slate-900 mt-1">${{ dinero(totales.unidades ? totales.ingreso / totales.unidades : 0) }}</p>
        <p class="text-xs text-slate-400 mt-1">{{ periodoLabel }}</p>
      </div>
    </div>

    <!-- Herramientas -->
    <div class="bg-white p-4 rounded-2xl border border-slate-100 shadow-sm space-y-4">
      <div class="flex flex-wrap items-center gap-3">
        <div class="relative flex-1 min-w-[220px]">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            v-model="texto"
            type="search"
            placeholder='Buscar: "pozole verde", "tamal", "horchata"…'
            class="w-full pl-9 pr-3 py-2.5 text-sm font-medium bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-400/30 focus:bg-white"
          />
        </div>
        <div class="inline-flex p-1 bg-slate-100 rounded-xl border border-slate-200">
          <button
            v-for="v in vistas"
            :key="v.id"
            @click="vista = v.id"
            :class="[
              'px-4 py-2 text-xs font-bold rounded-lg transition-all',
              vista === v.id ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-800',
            ]"
          >
            {{ v.label }}
          </button>
        </div>
        <button
          @click="exportarCsv"
          :disabled="!filtrados.length"
          class="inline-flex items-center gap-2 px-4 py-2.5 text-xs font-bold text-slate-700 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 disabled:opacity-40 transition-colors"
        >
          <Download class="h-4 w-4" /> CSV
        </button>
      </div>

      <div class="flex flex-wrap gap-2">
        <button
          @click="categoria = null"
          :class="chipClass(categoria === null)"
        >
          Todas
        </button>
        <button
          v-for="c in data?.categorias ?? []"
          :key="c.categoria"
          @click="categoria = categoria === c.categoria ? null : c.categoria"
          :class="chipClass(categoria === c.categoria)"
        >
          {{ c.categoria }} <span class="opacity-60">· {{ c.unidades }}</span>
        </button>
      </div>
    </div>

    <!-- Estados -->
    <div v-if="loading" class="py-16 flex justify-center">
      <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div>
    </div>
    <div v-else-if="error" class="p-4 bg-red-50 border border-red-200 rounded-2xl text-sm font-medium text-red-600">
      {{ error }}
    </div>
    <div v-else-if="!filtrados.length" class="text-center py-16 bg-slate-50 rounded-2xl border-2 border-dashed border-slate-200">
      <p class="text-slate-400 font-medium">
        {{ data?.productos.length ? 'Ningún producto coincide con el filtro' : 'No hay ventas en este periodo' }}
      </p>
    </div>

    <!-- Tabla total -->
    <div v-else-if="vista === 'total'" class="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-slate-50 text-[11px] uppercase tracking-widest text-slate-400">
            <tr>
              <th class="text-left px-4 py-3 font-extrabold w-10">#</th>
              <th class="text-left px-4 py-3 font-extrabold">
                <button @click="ordenar('nombre')" class="uppercase tracking-widest">Producto{{ flecha('nombre') }}</button>
              </th>
              <th class="text-left px-4 py-3 font-extrabold">Categoría</th>
              <th class="text-right px-4 py-3 font-extrabold">
                <button @click="ordenar('unidades')" class="uppercase tracking-widest">Unidades{{ flecha('unidades') }}</button>
              </th>
              <th class="text-right px-4 py-3 font-extrabold">
                <button @click="ordenar('ingreso')" class="uppercase tracking-widest">Ingreso{{ flecha('ingreso') }}</button>
              </th>
              <th class="text-right px-4 py-3 font-extrabold">Precio prom.</th>
              <th class="text-right px-4 py-3 font-extrabold">% ingreso</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-50">
            <tr v-for="(p, i) in ordenados" :key="p.platillo_id" class="hover:bg-slate-50/60">
              <td class="px-4 py-3 text-slate-300 font-bold">{{ i + 1 }}</td>
              <td class="px-4 py-3 font-bold text-slate-800">{{ p.nombre }}</td>
              <td class="px-4 py-3">
                <span class="px-2 py-0.5 text-[10px] font-bold rounded-md bg-slate-100 text-slate-500">{{ p.categoria }}</span>
              </td>
              <td class="px-4 py-3 text-right">
                <div class="flex items-center justify-end gap-3">
                  <div class="hidden sm:block w-24 h-1.5 rounded-full bg-slate-100 overflow-hidden">
                    <div class="h-full bg-blue-500 rounded-full" :style="{ width: barra(p.unidades) + '%' }"></div>
                  </div>
                  <span class="font-extrabold text-slate-900 tabular-nums">{{ p.unidades }}</span>
                </div>
              </td>
              <td class="px-4 py-3 text-right font-bold text-slate-700 tabular-nums">${{ dinero(p.ingreso) }}</td>
              <td class="px-4 py-3 text-right text-slate-500 tabular-nums">${{ dinero(p.precio_promedio) }}</td>
              <td class="px-4 py-3 text-right text-slate-500 tabular-nums">
                {{ totales.ingreso ? ((p.ingreso / totales.ingreso) * 100).toFixed(1) : '0.0' }}%
              </td>
            </tr>
          </tbody>
          <tfoot class="bg-slate-50 font-extrabold text-slate-800">
            <tr>
              <td colspan="3" class="px-4 py-3 text-xs uppercase tracking-widest text-slate-400">Total{{ hayFiltro ? ' del filtro' : '' }}</td>
              <td class="px-4 py-3 text-right tabular-nums">{{ totales.unidades }}</td>
              <td class="px-4 py-3 text-right tabular-nums">${{ dinero(totales.ingreso) }}</td>
              <td colspan="2"></td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>

    <!-- Matriz producto × día -->
    <div v-else class="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
      <div class="overflow-x-auto">
        <table class="text-sm min-w-full">
          <thead class="bg-slate-50 text-[11px] uppercase tracking-widest text-slate-400">
            <tr>
              <th class="sticky left-0 z-10 bg-slate-50 text-left px-4 py-3 font-extrabold min-w-[220px]">Producto</th>
              <th v-for="d in dias" :key="d" class="px-3 py-3 font-extrabold text-center whitespace-nowrap">{{ etiquetaDia(d) }}</th>
              <th class="px-4 py-3 font-extrabold text-right">Total</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-50">
            <tr v-for="p in ordenados" :key="p.platillo_id" class="hover:bg-slate-50/60">
              <td class="sticky left-0 bg-white px-4 py-2.5 font-bold text-slate-800 whitespace-nowrap">{{ p.nombre }}</td>
              <td
                v-for="d in dias"
                :key="d"
                class="px-3 py-2.5 text-center tabular-nums"
                :class="unidadesDia(p, d) ? 'font-extrabold text-slate-900' : 'text-slate-200'"
                :title="p.por_dia[d] ? `$${dinero(p.por_dia[d].ingreso)}` : ''"
              >
                {{ unidadesDia(p, d) || '·' }}
              </td>
              <td class="px-4 py-2.5 text-right font-extrabold text-blue-700 tabular-nums">{{ p.unidades }}</td>
            </tr>
          </tbody>
          <tfoot class="bg-slate-50 font-extrabold text-slate-800">
            <tr>
              <td class="sticky left-0 bg-slate-50 px-4 py-3 text-xs uppercase tracking-widest text-slate-400">Total{{ hayFiltro ? ' del filtro' : '' }}</td>
              <td v-for="d in dias" :key="d" class="px-3 py-3 text-center tabular-nums">{{ totalDia(d) }}</td>
              <td class="px-4 py-3 text-right tabular-nums">{{ totales.unidades }}</td>
            </tr>
          </tfoot>
        </table>
      </div>
      <p class="px-4 py-3 text-[11px] text-slate-400 border-t border-slate-50">
        Unidades por jornada (05:00→05:00 hora Ags). Pasa el cursor sobre un número para ver el ingreso de ese día.
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Download, Search } from 'lucide-vue-next'
import api from '@/api/client'
import { parseSafeDate } from '@/utils/dateUtils'
import {
  aCsv,
  filtrarProductos,
  totalesDe,
  unidadesDia,
  type ProductoVenta,
} from '@/utils/ventas-producto'

interface Reporte {
  periodo: { inicio: string; fin: string }
  dias: string[]
  productos: ProductoVenta[]
  categorias: { categoria: string; unidades: number; ingreso: number; porcentaje: number }[]
  totales: { unidades: number; ingreso: number }
}

const props = defineProps<{ inicio: string; fin: string }>()

const data = ref<Reporte | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

const texto = ref('')
const categoria = ref<string | null>(null)
const vista = ref<'total' | 'dias'>('total')
const vistas = [
  { id: 'total' as const, label: 'Total' },
  { id: 'dias' as const, label: 'Por día' },
]
const orden = ref<{ campo: 'nombre' | 'unidades' | 'ingreso'; asc: boolean }>({
  campo: 'unidades',
  asc: false,
})

const dias = computed(() => data.value?.dias ?? [])
const filtrados = computed(() => filtrarProductos(data.value?.productos ?? [], texto.value, categoria.value))
const totales = computed(() => totalesDe(filtrados.value))
const hayFiltro = computed(() => !!texto.value.trim() || categoria.value !== null)
const maxUnidades = computed(() => Math.max(1, ...filtrados.value.map((p) => p.unidades)))
const periodoLabel = computed(() =>
  props.inicio === props.fin ? props.inicio : `${props.inicio} → ${props.fin}`,
)

const ordenados = computed(() => {
  const { campo, asc } = orden.value
  const dir = asc ? 1 : -1
  return [...filtrados.value].sort((a, b) =>
    campo === 'nombre'
      ? dir * a.nombre.localeCompare(b.nombre, 'es')
      : dir * (a[campo] - b[campo]) || a.nombre.localeCompare(b.nombre, 'es'),
  )
})

const dinero = (n: number) =>
  Number(n || 0).toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const barra = (u: number) => Math.round((u / maxUnidades.value) * 100)
const totalDia = (d: string) => filtrados.value.reduce((s, p) => s + unidadesDia(p, d), 0)
const chipClass = (activo: boolean) => [
  'px-3 py-1.5 text-xs font-bold rounded-full border transition-colors',
  activo
    ? 'bg-blue-600 text-white border-blue-600'
    : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50',
]

function ordenar(campo: 'nombre' | 'unidades' | 'ingreso') {
  orden.value =
    orden.value.campo === campo
      ? { campo, asc: !orden.value.asc }
      : { campo, asc: campo === 'nombre' }
}
const flecha = (campo: string) =>
  orden.value.campo === campo ? (orden.value.asc ? ' ↑' : ' ↓') : ''

function etiquetaDia(iso: string): string {
  const d = parseSafeDate(iso)
  return d
    ? d.toLocaleDateString('es-MX', { weekday: 'short', day: 'numeric', month: 'short' })
    : iso
}

async function cargar() {
  loading.value = true
  error.value = null
  try {
    const { data: body } = await api.get<Reporte>('/admin/analytics/productos', {
      params: { fecha_inicio: props.inicio, fecha_fin: props.fin },
    })
    data.value = body
    if (categoria.value && !body.categorias.some((c) => c.categoria === categoria.value)) {
      categoria.value = null
    }
  } catch (e: any) {
    data.value = null
    error.value = e?.response?.data?.detail || 'No se pudo cargar el reporte de productos'
  } finally {
    loading.value = false
  }
}

function exportarCsv() {
  const csv = aCsv(ordenados.value, dias.value)
  // BOM para que Excel abra los acentos correctamente.
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `ventas-por-producto_${props.inicio}_${props.fin}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

watch(() => [props.inicio, props.fin], cargar, { immediate: true })
</script>
