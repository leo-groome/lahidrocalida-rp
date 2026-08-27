<template>
  <div class="min-h-screen bg-slate-50 flex flex-col">
    <!-- Header -->
    <header class="sticky top-0 z-40 bg-white/90 backdrop-blur border-b border-slate-100">
      <div class="max-w-xl mx-auto px-4 py-3 flex items-center gap-3">
        <button
          @click="volver"
          class="w-9 h-9 flex items-center justify-center rounded-xl bg-slate-100 text-slate-500 hover:bg-slate-900 hover:text-white transition-all flex-shrink-0"
          title="Volver"
        >
          <ArrowLeft class="w-4 h-4" />
        </button>
        <div class="min-w-0">
          <p class="text-[10px] font-black tracking-widest text-slate-400 uppercase leading-none">Compras</p>
          <h1 class="text-base font-black text-slate-900 tracking-tight">Registro rápido</h1>
        </div>
      </div>
    </header>

    <!-- Contenido -->
    <main class="flex-1 max-w-xl w-full mx-auto px-4 py-5 space-y-4">
      <!-- Dictado / pegado -->
      <div class="space-y-2">
        <label class="text-xs font-black text-slate-400 uppercase tracking-widest ml-1">
          Escribe o dicta tus compras, una por línea
        </label>
        <textarea
          ref="textareaRef"
          v-model="texto"
          rows="6"
          placeholder="350 pesos 6kg cueritos&#10;120 pesos 2kg jitomate&#10;80 pesos 1 caja servilletas"
          class="w-full px-4 py-3 text-sm border border-slate-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-[#00126D]/20 focus:border-[#00126D] resize-none transition-colors font-medium"
        />
        <button
          type="button"
          @click="analizar"
          :disabled="!texto.trim()"
          class="w-full py-3 bg-slate-100 text-slate-600 font-black rounded-2xl text-sm active:scale-[0.98] transition-all disabled:opacity-40"
        >
          Analizar {{ lineasContadas ? `(${lineasContadas} línea${lineasContadas > 1 ? 's' : ''})` : 'texto' }}
        </button>
      </div>

      <!-- Filas resueltas -->
      <ComprasFilasResolver
        v-if="filas.length"
        :filas="filas"
        :articulos="articulos"
        :categorias="categorias"
        @quitar-fila="quitarFila"
        @articulo-creado="onArticulosActualizados"
      />

      <!-- Ajustes del gasto -->
      <div class="bg-white border border-slate-200 rounded-2xl overflow-hidden">
        <button
          type="button"
          @click="ajustesAbiertos = !ajustesAbiertos"
          class="w-full flex items-center justify-between px-4 py-3 text-xs font-black uppercase tracking-widest text-slate-500"
        >
          <span>
            Ajustes
            <span v-if="!ajustesAbiertos && proveedorNombre" class="text-slate-400 normal-case font-bold tracking-normal">
              · {{ proveedorNombre }} · {{ metodoPago }}
            </span>
          </span>
          <ChevronDown class="w-4 h-4 transition-transform" :class="{ 'rotate-180': ajustesAbiertos }" />
        </button>

        <div v-show="ajustesAbiertos" class="px-4 pb-4 space-y-4 border-t border-slate-100 pt-4">
          <div class="space-y-1">
            <label class="block text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">
              Proveedor <span class="text-rose-400">*</span>
            </label>
            <SearchableSelect
              v-model="proveedorId"
              :options="proveedores"
              placeholder="Selecciona el proveedor..."
            />
          </div>

          <div class="space-y-1">
            <label class="block text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Método de pago</label>
            <div class="grid grid-cols-2 gap-2">
              <button
                v-for="m in metodos"
                :key="m.id"
                type="button"
                @click="metodoPago = m.id"
                class="py-2.5 rounded-xl text-sm font-black transition-all"
                :class="metodoPago === m.id ? 'bg-[#00126D] text-white' : 'bg-slate-100 text-slate-500'"
              >
                {{ m.emoji }} {{ m.label }}
              </button>
            </div>
          </div>

          <div class="space-y-1">
            <label class="block text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Fecha</label>
            <input
              type="datetime-local"
              v-model="fecha"
              class="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2.5 text-sm font-bold text-slate-700 outline-none focus:ring-2 focus:ring-[#00126D]"
            >
          </div>
        </div>
      </div>

      <p v-if="filas.length && !proveedorId" class="text-[11px] font-bold text-amber-600 text-center">
        Falta elegir proveedor (en Ajustes).
      </p>
    </main>

    <!-- Footer fijo -->
    <footer class="sticky bottom-0 bg-white/90 backdrop-blur border-t border-slate-100 px-4 py-3">
      <div class="max-w-xl mx-auto">
        <button
          type="button"
          @click="registrar"
          :disabled="!puedeRegistrar || submitting"
          class="w-full py-4 bg-[#00126D] text-white font-black rounded-2xl disabled:opacity-40 disabled:cursor-not-allowed active:scale-[0.98] transition-all flex items-center justify-center gap-2"
        >
          <Loader2 v-if="submitting" class="w-4 h-4 animate-spin" />
          {{ submitting ? 'Registrando...' : `Registrar gasto${totalTexto}` }}
        </button>
      </div>
    </footer>

    <!-- Toast -->
    <div
      v-if="toast"
      class="fixed bottom-24 left-1/2 -translate-x-1/2 z-50 px-4 py-3 rounded-2xl text-sm font-black shadow-lg max-w-[90vw] text-center"
      :class="toast.tipo === 'error' ? 'bg-rose-600 text-white' : 'bg-emerald-600 text-white'"
    >
      {{ toast.msg }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api/client'
import {
  construirFilas,
  filasListas,
  filasToDetalles,
  precioUnitarioFila,
  type FilaCompra,
} from '@/utils/parseCompraTexto'
import { useCrearGasto } from '@/composables/useCrearGasto'
import ComprasFilasResolver from '@/components/gastos/ComprasFilasResolver.vue'
import SearchableSelect from '@/components/gastos/SearchableSelect.vue'
import { ArrowLeft, ChevronDown, Loader2 } from 'lucide-vue-next'

const router = useRouter()
const { crearGasto, submitting, error } = useCrearGasto()

const PROVEEDOR_LS_KEY = 'rapido:ultimoProveedorId'
const metodos = [
  { id: 'efectivo' as const, label: 'Efectivo', emoji: '💵' },
  { id: 'tarjeta' as const, label: 'Tarjeta', emoji: '💳' },
]

const texto = ref('')
const filas = ref<FilaCompra[]>([])
const textareaRef = ref<HTMLTextAreaElement | null>(null)

const proveedores = ref<any[]>([])
const articulos = ref<any[]>([])
const categorias = ref<any[]>([])

const ultimoProveedor = Number(localStorage.getItem(PROVEEDOR_LS_KEY))
const proveedorId = ref<number | null>(Number.isFinite(ultimoProveedor) && ultimoProveedor > 0 ? ultimoProveedor : null)
const metodoPago = ref<'efectivo' | 'tarjeta'>('efectivo')
const fecha = ref(localNow())
const ajustesAbiertos = ref(false)

const toast = ref<{ msg: string; tipo: 'ok' | 'error' } | null>(null)
let toastTimer: ReturnType<typeof setTimeout> | undefined

function localNow() {
  const d = new Date()
  const tz = d.getTimezoneOffset() * 60000
  return new Date(d.getTime() - tz).toISOString().slice(0, 16)
}

const lineasContadas = computed(
  () => texto.value.split('\n').map((l) => l.trim()).filter(Boolean).length,
)
const proveedorNombre = computed(
  () => proveedores.value.find((p) => p.id === proveedorId.value)?.nombre ?? '',
)
const puedeRegistrar = computed(() => filasListas(filas.value) && !!proveedorId.value)
const totalGasto = computed(() =>
  filas.value.reduce((s, f) => s + (Number(f.cantidad) || 0) * precioUnitarioFila(f), 0),
)
const totalTexto = computed(() =>
  puedeRegistrar.value ? ` · $${totalGasto.value.toFixed(2)}` : '',
)

function mostrarToast(msg: string, tipo: 'ok' | 'error' = 'ok') {
  toast.value = { msg, tipo }
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => (toast.value = null), 3000)
}

function analizar() {
  filas.value = construirFilas(texto.value, articulos.value)
  if (filas.value.length && !proveedorId.value) ajustesAbiertos.value = true
}

function quitarFila(id: number) {
  filas.value = filas.value.filter((f) => f.id !== id)
}

function onArticulosActualizados(arts: any[]) {
  articulos.value = arts
}

async function registrar() {
  if (!puedeRegistrar.value || submitting.value) return
  try {
    await crearGasto({
      proveedorId: proveedorId.value,
      tipoGasto: 'directo',
      metodoPago: metodoPago.value,
      detalles: filasToDetalles(filas.value),
      fechaGasto: fecha.value,
    })
    localStorage.setItem(PROVEEDOR_LS_KEY, String(proveedorId.value))
    mostrarToast(`Gasto registrado · ${filas.value.length} artículo(s)`)
    texto.value = ''
    filas.value = []
    fecha.value = localNow()
    await nextTick()
    textareaRef.value?.focus()
  } catch {
    mostrarToast(error.value || 'Error al guardar', 'error')
  }
}

function volver() {
  if (window.history.length > 1) router.back()
  else router.push('/compras')
}

onMounted(async () => {
  textareaRef.value?.focus()
  try {
    const [provs, arts, cats] = await Promise.all([
      api.get('/gastos/proveedores'),
      api.get('/gastos/articulos'),
      api.get('/gastos/categorias-articulo'),
    ])
    proveedores.value = provs.data
    articulos.value = arts.data
    categorias.value = cats.data
  } catch {
    mostrarToast('No se pudieron cargar los catálogos', 'error')
  }
})
</script>
