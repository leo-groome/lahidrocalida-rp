<template>
  <div class="space-y-4">
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
        <span v-else-if="p.estado === 'parcial'" class="font-medium">· {{ p.fotosFallidas }} foto(s) sin subir · {{ p.error }}</span>
        <span v-else-if="p.estado === 'error'" class="font-medium">· {{ p.error }}</span>
      </span>
      <template v-if="p.estado !== 'enviando'">
        <button type="button" v-if="p.estado !== 'ok'" class="font-black underline" @click="reintentar(p)">{{ p.gastoId ? 'Reintentar fotos' : 'Reintentar' }}</button>
        <button type="button" class="w-11 h-11 -mr-2 flex items-center justify-center" title="Descartar" aria-label="Descartar" @click="descartar(p.id)"><X class="w-4 h-4" /></button>
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
    <FotoTicketInput v-model="fotos" v-model:processing="preparandoFotos" />
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

  <!-- Artículos manuales (conviven con las filas del texto dictado) -->
  <div class="space-y-3">
    <button
      v-if="!manualAbierto"
      type="button"
      @click="abrirManual"
      class="w-full min-h-12 py-3 bg-white border border-dashed border-slate-300 text-slate-600 font-black rounded-2xl text-sm active:scale-[0.98] transition-all flex items-center justify-center gap-2"
    >
      <Plus class="w-4 h-4" /> Agregar artículo manualmente
    </button>
    <GastoDetallesEditor
      v-else
      v-model:detalles="detallesManuales"
      :articulos="articulos"
    />
  </div>

  <!-- Ajustes del gasto -->
  <div class="bg-white border border-slate-200 rounded-2xl overflow-hidden">
    <button
      type="button"
      @click="ajustesAbiertos = !ajustesAbiertos"
      class="w-full min-h-12 flex items-center justify-between px-4 py-3 text-xs font-black uppercase tracking-widest text-slate-500"
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
        <label class="block text-xs font-black text-slate-400 uppercase tracking-widest ml-1">
          Proveedor <span class="normal-case font-bold tracking-normal">(opcional)</span>
        </label>
        <SearchableSelect
          v-model="proveedorId"
          :options="proveedores"
          placeholder="Selecciona el proveedor..."
        />
      </div>

      <div class="space-y-1">
        <label class="block text-xs font-black text-slate-400 uppercase tracking-widest ml-1">Método de pago</label>
        <p
          v-if="forzarEfectivo"
          class="min-h-12 flex items-center rounded-xl bg-emerald-50 border border-emerald-200 px-4 text-sm font-black text-emerald-700"
        >
          💵 Efectivo de caja — se descuenta del turno
        </p>
        <div v-else class="grid grid-cols-2 gap-2">
          <button
            v-for="m in metodos"
            :key="m.id"
            type="button"
            @click="metodoPago = m.id"
            class="min-h-12 rounded-xl text-sm font-black transition-all"
            :class="metodoPago === m.id ? 'bg-[#00126D] text-white' : 'bg-slate-100 text-slate-500'"
          >
            {{ m.emoji }} {{ m.label }}
          </button>
        </div>
      </div>

      <div class="space-y-1">
        <label class="block text-xs font-black text-slate-400 uppercase tracking-widest ml-1">Fecha</label>
        <input
          type="datetime-local"
          v-model="fecha"
          class="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-3 text-base font-bold text-slate-700 outline-none focus:ring-2 focus:ring-[#00126D]"
        >
      </div>
    </div>
  </div>

  <!-- Footer pegajoso: funciona dentro de la vista y del modal (el padre scrollea) -->
  <div class="safe-area-bottom sticky bottom-0 z-10 -mx-4 -mb-5 mt-4 bg-white/90 backdrop-blur border-t border-slate-100 px-4 py-3">
    <p v-if="bloqueado" class="text-xs font-bold text-amber-600 text-center mb-2">Inicia un turno para registrar gastos de caja</p>
    <button
      type="button"
      @click="registrar"
      :disabled="bloqueado || !puedeRegistrar || cola.escribiendo || preparandoFotos"
      class="w-full py-4 bg-[#00126D] text-white font-black rounded-2xl disabled:opacity-40 disabled:cursor-not-allowed active:scale-[0.98] transition-all flex items-center justify-center gap-2"
    >
      {{ `Registrar gasto${totalTexto}` }}
    </button>
  </div>

  <!-- Toast -->
  <div
    v-if="toast"
    class="fixed bottom-24 left-1/2 -translate-x-1/2 z-[130] px-4 py-3 rounded-2xl text-sm font-black shadow-lg max-w-[90vw] text-center"
    :class="toast.tipo === 'error' ? 'bg-rose-600 text-white' : 'bg-emerald-600 text-white'"
  >
    {{ toast.msg }}
  </div>
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia"
import { useCatalogosGastosStore } from "@/stores/catalogos-gastos"
const catalogos = useCatalogosGastosStore()
const { proveedores, articulos, categorias, empleados } = storeToRefs(catalogos)
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import {
  analizarCompras,
  dividirLineas,
  filasListas,
  filasToDetalles,
  precioUnitarioFila,
  type FilaCompra,
} from '@/utils/parseCompraTexto'
import { useGastosPendientesStore } from '@/stores/gastos-pendientes'
import type { GastoPendiente } from '@/utils/gasto-queue-db'
import ComprasFilasResolver from '@/components/gastos/ComprasFilasResolver.vue'
import SearchableSelect from '@/components/gastos/SearchableSelect.vue'
import FotoTicketInput from '@/components/gastos/FotoTicketInput.vue'
import GastoDetallesEditor from '@/components/gastos/GastoDetallesEditor.vue'
import { AlertTriangle, Check, ChevronDown, Loader2, Plus, X } from 'lucide-vue-next'

const props = withDefaults(defineProps<{
  turnoId?: number | null
  forzarEfectivo?: boolean
  /** Bloquea el registro (p. ej. modal de caja sin turno activo). */
  bloqueado?: boolean
}>(), { turnoId: null, forzarEfectivo: false, bloqueado: false })

const emit = defineEmits<{
  /** El gasto quedó en la cola local (el envío sigue en segundo plano). */
  submitted: [id: string]
  /** El servidor confirmó el gasto creado por este formulario. */
  saved: [id: string]
}>()

const cola = useGastosPendientesStore()
const pendientes = computed(() => cola.pendientes)

const PROVEEDOR_LS_KEY = 'rapido:ultimoProveedorId'
const metodos = [
  { id: 'efectivo' as const, label: 'Efectivo', emoji: '💵' },
  { id: 'tarjeta' as const, label: 'Tarjeta', emoji: '💳' },
]

const texto = ref('')
const filas = ref<FilaCompra[]>([])
const textareaRef = ref<HTMLTextAreaElement | null>(null)


const ultimoProveedor = Number(localStorage.getItem(PROVEEDOR_LS_KEY))
const proveedorId = ref<number | null>(Number.isFinite(ultimoProveedor) && ultimoProveedor > 0 ? ultimoProveedor : null)
const metodoPago = ref<'efectivo' | 'tarjeta'>('efectivo')
watch(() => props.forzarEfectivo, (f) => { if (f) { metodoPago.value = 'efectivo'; ajustesAbiertos.value = true } })
const fecha = ref(localNow())
const ajustesAbiertos = ref(props.forzarEfectivo)
const montoTotal = ref<string>('')
// Artículos agregados a mano (GastoDetallesEditor). Terminan en el mismo `detalles` que las filas del texto.
const detallesManuales = ref<any[]>([])
const manualAbierto = ref(false)
function abrirManual() {
  manualAbierto.value = true
  if (!detallesManuales.value.length) {
    detallesManuales.value.push({ articulo_id: null, cantidad: 1, precio_unitario: 0, subtotal_linea: 0, _editadoManual: false })
  }
}
const fotos = ref<File[]>([])
const preparandoFotos = ref(false)

const toast = ref<{ msg: string; tipo: 'ok' | 'error' } | null>(null)
let toastTimer: ReturnType<typeof setTimeout> | undefined

function localNow() {
  const d = new Date()
  const tz = d.getTimezoneOffset() * 60000
  return new Date(d.getTime() - tz).toISOString().slice(0, 16)
}

const lineasContadas = computed(() => dividirLineas(texto.value).length)
const proveedorNombre = computed(
  () => proveedores.value.find((p) => p.id === proveedorId.value)?.nombre ?? '',
)
const montoNum = computed(() => Number(montoTotal.value) || 0)
// Filas manuales con artículo elegido; las vacías (sin artículo) se ignoran.
const manualesElegidos = computed(() => detallesManuales.value.filter((d) => d.articulo_id))
const manualesValidos = computed(() =>
  manualesElegidos.value.every((d) => Number(d.cantidad) > 0 && Number(d.subtotal_linea) > 0),
)
const totalManuales = computed(() =>
  manualesElegidos.value.reduce((s, d) => s + (Number(d.subtotal_linea) || 0), 0),
)
// Con artículos (dictados y/o manuales): todos válidos. Sin artículos: basta un monto > 0.
const modoLista = computed(() => filas.value.length > 0 || manualesElegidos.value.length > 0)
const puedeRegistrar = computed(() =>
  modoLista.value
    ? (filas.value.length === 0 || filasListas(filas.value)) && manualesValidos.value
    : montoNum.value > 0,
)
const totalGasto = computed(() =>
  modoLista.value
    ? filas.value.reduce((s, f) => s + (Number(f.cantidad) || 0) * precioUnitarioFila(f), 0) + totalManuales.value
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
  const r = analizarCompras(texto.value, articulos.value, proveedores.value)
  filas.value = r.filas
  if (!r.proveedor) return
  if (r.proveedor.id) {
    proveedorId.value = r.proveedor.id
    mostrarToast(`Proveedor: ${r.proveedor.nombre}${r.proveedor.dudoso ? ' (aprox., revisa)' : ''}`)
  } else {
    mostrarToast(`Proveedor "${r.proveedor.textoDictado}" no está registrado`, 'error')
  }
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
const hayEnVuelo = computed(() => cola.escribiendo)
function avisarSalida(e: BeforeUnloadEvent) {
  if (hayEnVuelo.value) e.preventDefault()
}
window.addEventListener('beforeunload', avisarSalida)
onBeforeUnmount(() => window.removeEventListener('beforeunload', avisarSalida))
onBeforeRouteLeave(() => !cola.escribiendo)

const okProgramados = new Set<string>()
const propios = new Set<string>() // gastos creados por esta instancia (para emitir `saved`)
watch(
  () => pendientes.value.filter((p) => p.estado === 'ok').map((p) => ({ id: p.id, total: p.total })),
  (oks) => {
    for (const { id, total } of oks) {
      if (okProgramados.has(id)) continue
      okProgramados.add(id)
      mostrarToast(`Gasto registrado · $${total.toFixed(2)}`)
      if (propios.delete(id)) emit('saved', id)
      setTimeout(() => {
        okProgramados.delete(id)
        void cola.descartar(id).catch(() => {})
      }, 3000)
    }
  },
  { immediate: true },
)

async function descartar(id: string) {
  try {
    await cola.descartar(id)
    mostrarToast('Pendiente descartado (el gasto registrado permanece)')
  } catch {
    mostrarToast('No se pudo descartar el pendiente', 'error')
  }
}
function reintentar(p: GastoPendiente) {
  void cola.enviar(p).catch(() => mostrarToast('Inicia sesión para reintentar', 'error'))
}

async function registrar() {
  if (props.bloqueado || !puedeRegistrar.value || cola.escribiendo || preparandoFotos.value) return
  let p: GastoPendiente
  try {
    p = await cola.agregar({
      proveedor_id: proveedorId.value, tipo_gasto: 'directo', metodo_pago: props.forzarEfectivo ? 'efectivo' : metodoPago.value,
      detalles: modoLista.value
        ? [
            ...filasToDetalles(filas.value),
            ...manualesElegidos.value.map((d) => ({
              articulo_id: d.articulo_id,
              cantidad: Number(d.cantidad),
              precio_unitario: Number(d.precio_unitario) || 0,
              subtotal_linea: Number(d.subtotal_linea),
              _editadoManual: false,
            })),
          ]
        : [],
      turno_id: props.turnoId ?? null,
      total_manual: modoLista.value ? null : montoNum.value,
      fecha_gasto: new Date(fecha.value).toISOString(),
    }, [...fotos.value], totalGasto.value,
    modoLista.value ? `${filas.value.length + manualesElegidos.value.length} artículo(s)` : 'compra rápida')
  } catch {
    mostrarToast('No se pudo conservar el gasto. La captura sigue en el formulario.', 'error')
    return
  }
  if (proveedorId.value) localStorage.setItem(PROVEEDOR_LS_KEY, String(proveedorId.value))
  propios.add(p.id)
  emit('submitted', p.id)
  texto.value = ''
  filas.value = []
  detallesManuales.value = []
  manualAbierto.value = false
  montoTotal.value = ''
  fotos.value = []
  fecha.value = localNow()
  void cola.enviar(p).catch(() => mostrarToast("Inicia sesión para enviar el pendiente", "error"))
  await nextTick()
  textareaRef.value?.focus()
}

onMounted(async () => {
  textareaRef.value?.focus()
  try { await cola.cargar() } catch { mostrarToast("No se pudieron recuperar los pendientes", "error") }
  try {
    await catalogos.cargar()
  } catch {
    mostrarToast('No se pudieron cargar los catálogos', 'error')
  }
})
</script>
