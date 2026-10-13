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
      <!-- Envíos en curso (UI optimista): el formulario ya quedó libre para el siguiente gasto -->
      <ul v-if="pendientes.length" class="space-y-2" aria-live="polite">
        <li
          v-for="p in pendientes"
          :key="p.id"
          class="flex items-center gap-3 rounded-2xl border px-4 py-3 text-sm font-bold transition-colors"
          :class="{
            'bg-white border-slate-200 text-slate-600': p.estado === 'enviando',
            'bg-emerald-50 border-emerald-200 text-emerald-700': p.estado === 'ok',
            'bg-amber-50 border-amber-200 text-amber-700': p.estado === 'parcial',
            'bg-rose-50 border-rose-200 text-rose-700': p.estado === 'error',
          }"
        >
          <Loader2 v-if="p.estado === 'enviando'" class="w-4 h-4 animate-spin flex-shrink-0" />
          <Check v-else-if="p.estado === 'ok'" class="w-4 h-4 flex-shrink-0" />
          <AlertTriangle v-else class="w-4 h-4 flex-shrink-0" />
          <span class="flex-1 min-w-0 truncate">
            ${{ p.total.toFixed(2) }} · {{ p.resumen }}
            <span v-if="p.estado === 'enviando'" class="font-medium">· guardando…</span>
            <span v-else-if="p.estado === 'parcial'" class="font-medium">· {{ p.fotosFallidas }} foto(s) sin subir</span>
            <span v-else-if="p.estado === 'error'" class="font-medium">· {{ p.error }}</span>
          </span>
          <template v-if="p.estado === 'error'">
            <button type="button" class="font-black underline" @click="reintentar(p)">Reintentar</button>
            <button type="button" class="p-1" title="Descartar" @click="descartar(p.id)"><X class="w-4 h-4" /></button>
          </template>
        </li>
      </ul>

      <!-- Captura rápida: monto + foto del ticket -->
      <div class="bg-white border border-slate-200 rounded-2xl p-4 space-y-3">
        <label class="text-xs font-black text-slate-400 uppercase tracking-widest">
          Monto total <span class="normal-case font-bold tracking-normal">(si no vas a listar artículos)</span>
        </label>
        <div class="relative">
          <span class="absolute inset-y-0 left-4 flex items-center text-slate-400 font-black text-xl">$</span>
          <input
            v-model="montoTotal"
            type="number"
            inputmode="decimal"
            min="0"
            step="0.01"
            placeholder="0.00"
            class="w-full pl-9 pr-4 py-3 text-2xl font-black text-slate-900 border border-slate-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-[#00126D]/20 focus:border-[#00126D]"
          >
        </div>
        <FotoTicketInput v-model="fotos" />
      </div>

      <!-- Dictado / pegado -->
      <div class="space-y-2">
        <label class="text-xs font-black text-slate-400 uppercase tracking-widest ml-1">
          O escribe / dicta tus compras, una por línea
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
              Proveedor <span class="normal-case font-bold tracking-normal">(opcional)</span>
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

    </main>

    <!-- Footer fijo -->
    <footer class="sticky bottom-0 bg-white/90 backdrop-blur border-t border-slate-100 px-4 py-3">
      <div class="max-w-xl mx-auto">
        <button
          type="button"
          @click="registrar"
          :disabled="!puedeRegistrar"
          class="w-full py-4 bg-[#00126D] text-white font-black rounded-2xl disabled:opacity-40 disabled:cursor-not-allowed active:scale-[0.98] transition-all flex items-center justify-center gap-2"
        >
          {{ `Registrar gasto${totalTexto}` }}
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
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api/client'
import {
  construirFilas,
  filasListas,
  filasToDetalles,
  precioUnitarioFila,
  type FilaCompra,
} from '@/utils/parseCompraTexto'
import { enviarGasto, type CrearGastoArgs } from '@/composables/useCrearGasto'
import ComprasFilasResolver from '@/components/gastos/ComprasFilasResolver.vue'
import SearchableSelect from '@/components/gastos/SearchableSelect.vue'
import FotoTicketInput from '@/components/gastos/FotoTicketInput.vue'
import { AlertTriangle, ArrowLeft, Check, ChevronDown, Loader2, X } from 'lucide-vue-next'

const router = useRouter()

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
const montoTotal = ref<string>('')
const fotos = ref<File[]>([])

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
const montoNum = computed(() => Number(montoTotal.value) || 0)
// Con artículos: todas las filas resueltas. Sin artículos: basta un monto > 0.
const modoLista = computed(() => filas.value.length > 0)
const puedeRegistrar = computed(() =>
  modoLista.value ? filasListas(filas.value) : montoNum.value > 0,
)
const totalGasto = computed(() =>
  modoLista.value
    ? filas.value.reduce((s, f) => s + (Number(f.cantidad) || 0) * precioUnitarioFila(f), 0)
    : montoNum.value,
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
}

function quitarFila(id: number) {
  filas.value = filas.value.filter((f) => f.id !== id)
}

function onArticulosActualizados(arts: any[]) {
  articulos.value = arts
}

// --- UI optimista -----------------------------------------------------------
// Al registrar, el formulario se limpia al instante y el envío corre en segundo
// plano; cada gasto aparece en `pendientes` y solo el que falla pide acción.
interface Pendiente {
  id: number
  total: number
  resumen: string
  estado: 'enviando' | 'ok' | 'parcial' | 'error'
  fotosFallidas: number
  error: string
  args: CrearGastoArgs
}
const pendientes = ref<Pendiente[]>([])
let siguienteId = 1

const hayEnVuelo = computed(() => pendientes.value.some((p) => p.estado === 'enviando'))
function avisarSalida(e: BeforeUnloadEvent) {
  if (hayEnVuelo.value) e.preventDefault()
}
window.addEventListener('beforeunload', avisarSalida)
onBeforeUnmount(() => window.removeEventListener('beforeunload', avisarSalida))

function descartar(id: number) {
  pendientes.value = pendientes.value.filter((p) => p.id !== id)
}

async function enviar(p: Pendiente) {
  p.estado = 'enviando'
  p.error = ''
  try {
    const r = await enviarGasto(p.args)
    p.fotosFallidas = r.fotosFallidas
    p.estado = r.fotosFallidas ? 'parcial' : 'ok'
    if (!r.fotosFallidas) setTimeout(() => descartar(p.id), 4000)
  } catch (e: any) {
    p.estado = 'error'
    p.error = e?.response?.data?.detail || 'No se pudo guardar'
  }
}

function reintentar(p: Pendiente) {
  // Riesgo conocido: si el POST llegó pero se perdió la respuesta, reintentar duplica el
  // gasto (el backend aún no tiene idempotencia en /gastos). El usuario decide con el botón.
  void enviar(p)
}

async function registrar() {
  if (!puedeRegistrar.value) return
  const args: CrearGastoArgs = {
    proveedorId: proveedorId.value,
    tipoGasto: 'directo',
    metodoPago: metodoPago.value,
    detalles: modoLista.value ? filasToDetalles(filas.value) : [],
    totalManual: modoLista.value ? null : montoNum.value,
    fechaGasto: fecha.value,
    fotos: [...fotos.value],
  }
  const p: Pendiente = {
    id: siguienteId++,
    total: totalGasto.value,
    resumen: modoLista.value ? `${filas.value.length} artículo(s)` : 'compra rápida',
    estado: 'enviando',
    fotosFallidas: 0,
    error: '',
    args,
  }
  if (proveedorId.value) localStorage.setItem(PROVEEDOR_LS_KEY, String(proveedorId.value))

  // Optimista: se limpia ya, no se espera al servidor.
  pendientes.value = [p, ...pendientes.value]
  texto.value = ''
  filas.value = []
  montoTotal.value = ''
  fotos.value = []
  fecha.value = localNow()
  void enviar(pendientes.value[0])
  await nextTick()
  textareaRef.value?.focus()
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
