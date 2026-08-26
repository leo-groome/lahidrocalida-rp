<template>
  <div class="fixed inset-0 z-[150] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
    <div class="bg-white rounded-3xl shadow-2xl w-full max-w-md flex flex-col overflow-hidden">

      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-5 border-b border-slate-100">
        <!-- Step indicator -->
        <div class="flex items-center gap-2">
          <div
            v-for="n in 3"
            :key="n"
            class="transition-all duration-300 rounded-full"
            :class="n === step
              ? 'w-6 h-2.5 bg-[#00126D]'
              : n < step
                ? 'w-2.5 h-2.5 bg-[#00126D]/40'
                : 'w-2.5 h-2.5 bg-slate-200'"
          />
        </div>
        <button
          @click="$emit('cancel')"
          class="w-9 h-9 flex items-center justify-center rounded-xl text-slate-400 hover:bg-slate-100 transition-colors"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>

      <!-- ══════════════════════════════════
           PASO 1 — Tipo de Gasto
      ═════════════════════════════════════ -->
      <div v-if="step === 1" class="p-6 space-y-4">
        <div class="text-center mb-6">
          <p class="text-xs font-black text-slate-400 uppercase tracking-widest">Paso 1 de 3</p>
          <h2 class="text-2xl font-black text-slate-800 mt-1">¿Qué tipo de gasto?</h2>
        </div>

        <button
          v-for="tipo in tiposGasto"
          :key="tipo.id"
          @click="selectTipo(tipo.id)"
          class="w-full flex items-center gap-5 px-6 py-5 rounded-2xl border-2 transition-all active:scale-[0.97]"
          :class="tipoGasto === tipo.id
            ? 'border-[#00126D] bg-[#00126D]/5'
            : 'border-slate-100 bg-slate-50 hover:border-slate-200'"
        >
          <span class="text-3xl">{{ tipo.emoji }}</span>
          <div class="text-left">
            <p class="font-black text-slate-800">{{ tipo.label }}</p>
            <p class="text-xs text-slate-500 mt-0.5">{{ tipo.desc }}</p>
          </div>
          <div
            class="ml-auto w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-all"
            :class="tipoGasto === tipo.id ? 'border-[#00126D] bg-[#00126D]' : 'border-slate-300'"
          >
            <div v-if="tipoGasto === tipo.id" class="w-2 h-2 bg-white rounded-full"/>
          </div>
        </button>

        <button
          @click="step = 2"
          :disabled="!tipoGasto"
          class="w-full py-4 bg-[#00126D] text-white font-black rounded-2xl mt-2 disabled:opacity-40 disabled:cursor-not-allowed active:scale-[0.98] transition-all"
        >
          Siguiente →
        </button>
      </div>

      <!-- ══════════════════════════════════
           PASO 2 — Monto (rápido o desglose)
      ═════════════════════════════════════ -->
      <div v-else-if="step === 2" class="flex flex-col">
        <!-- Toggle modo (no aplica a nómina) -->
        <div v-if="tipoGasto !== 'nomina'" class="px-4 pt-4">
          <div class="grid grid-cols-3 gap-2 bg-slate-100 p-1 rounded-2xl">
            <button
              @click="modoCaptura = 'rapido'"
              class="py-2.5 rounded-xl text-xs font-black transition-all"
              :class="modoCaptura === 'rapido' ? 'bg-white text-[#00126D] shadow-sm' : 'text-slate-500'"
            >Monto rápido</button>
            <button
              @click="modoCaptura = 'texto'"
              class="py-2.5 rounded-xl text-xs font-black transition-all"
              :class="modoCaptura === 'texto' ? 'bg-white text-[#00126D] shadow-sm' : 'text-slate-500'"
            >Texto rápido</button>
            <button
              @click="enableDesglose"
              class="py-2.5 rounded-xl text-xs font-black transition-all"
              :class="modoCaptura === 'desglose' ? 'bg-white text-[#00126D] shadow-sm' : 'text-slate-500'"
            >Desglose</button>
          </div>
        </div>

        <!-- ── Modo texto rápido ── -->
        <template v-if="modoCaptura === 'texto' && tipoGasto !== 'nomina'">
          <CompraTextoQuickAdd
            :articulos="articulos"
            :categorias="categorias"
            @agregar-detalles="onAgregarDetalles"
            @articulo-creado="onArticuloCreado"
          />
        </template>

        <!-- ── Modo desglose ── -->
        <template v-else-if="modoCaptura === 'desglose' && tipoGasto !== 'nomina'">
          <div class="p-4 max-h-[55vh] overflow-y-auto">
            <GastoDetallesEditor
              v-model:detalles="detalles"
              v-model:total-manual="totalManualDetalle"
              :articulos="articulos"
            />
          </div>
        </template>

        <!-- ── Modo monto rápido (keypad) ── -->
        <template v-else>
          <!-- Amount display -->
          <div class="px-6 py-8 text-center bg-slate-50 border-b border-slate-100">
            <p class="text-xs font-black text-slate-400 uppercase tracking-widest mb-2">Paso 2 de 3 — Monto</p>
            <div class="flex items-baseline justify-center gap-2">
              <span class="text-2xl font-black text-slate-400">$</span>
              <span
                class="text-5xl font-black tracking-tighter transition-all"
                :class="amountDisplay === '0' ? 'text-slate-300' : 'text-slate-800'"
              >
                {{ formatAmount(amountDisplay) }}
              </span>
            </div>
            <p class="text-xs text-slate-400 mt-2 font-semibold">
              {{ tiposGasto.find(t => t.id === tipoGasto)?.label }}
            </p>
          </div>

          <!-- Keypad -->
          <div class="p-4 grid grid-cols-3 gap-2">
            <button
              v-for="key in amountKeys"
              :key="key.label"
              @click="handleAmountKey(key.action)"
              class="flex items-center justify-center min-h-[56px] rounded-2xl text-xl font-black transition-all active:scale-95 select-none"
              :class="key.variant === 'action'
                ? 'bg-slate-100 text-slate-600 active:bg-slate-200'
                : key.variant === 'clear'
                  ? 'bg-red-50 text-red-400 active:bg-red-100'
                  : 'bg-slate-50 text-slate-700 active:bg-slate-200'"
            >
              <svg v-if="key.label === '⌫'" xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 12H3M3 12l4-4M3 12l4 4"/>
              </svg>
              <span v-else>{{ key.label }}</span>
            </button>
          </div>
        </template>

        <div class="px-4 pb-4 flex gap-3">
          <button
            @click="step = 1"
            class="flex-none px-6 py-4 bg-slate-100 text-slate-600 font-black rounded-2xl text-sm active:scale-95 transition-all"
          >
            ← Atrás
          </button>
          <button
            @click="step = 3"
            :disabled="amountValue <= 0"
            class="flex-1 py-4 bg-[#00126D] text-white font-black rounded-2xl disabled:opacity-40 disabled:cursor-not-allowed active:scale-[0.98] transition-all"
          >
            Confirmar monto →
          </button>
        </div>
      </div>

      <!-- ══════════════════════════════════
           PASO 3 — Confirmación
      ═════════════════════════════════════ -->
      <div v-else-if="step === 3" class="flex flex-col overflow-hidden max-h-[80vh]">
        <div class="px-6 py-4 overflow-y-auto flex-1 space-y-5">
          <div class="text-center">
            <p class="text-xs font-black text-slate-400 uppercase tracking-widest">Paso 3 de 3 — Confirmación</p>
          </div>

          <!-- Summary card -->
          <div class="bg-slate-50 rounded-2xl p-4 flex items-center justify-between">
            <div class="flex items-center gap-3">
              <span class="text-2xl">{{ tiposGasto.find(t => t.id === tipoGasto)?.emoji }}</span>
              <div>
                <p class="font-black text-slate-700 text-sm">{{ tiposGasto.find(t => t.id === tipoGasto)?.label }}</p>
                <p class="text-xs text-slate-400">Tipo de gasto</p>
              </div>
            </div>
            <div class="text-right">
              <p class="text-2xl font-black text-[#00126D]">${{ amountFormatted }}</p>
              <p v-if="modoCaptura === 'desglose' && detalles.length" class="text-[10px] text-slate-400 font-bold">{{ detalles.length }} artículo(s)</p>
            </div>
          </div>

          <!-- Turno auto-link badge -->
          <div
            v-if="turnoId"
            class="flex items-center gap-3 p-3 bg-emerald-50 border border-emerald-200 rounded-2xl"
          >
            <div class="w-7 h-7 bg-emerald-100 rounded-lg flex items-center justify-center flex-shrink-0">
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-emerald-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
            </div>
            <p class="text-sm font-bold text-emerald-700">
              Se vinculará al <span class="font-black">Turno #{{ turnoId }}</span>
            </p>
          </div>

          <!-- Proveedor -->
          <div class="space-y-2">
            <label class="text-xs font-black text-slate-500 uppercase tracking-widest">Proveedor <span class="text-red-400">*</span></label>
            <SearchableSelect
              v-model="proveedorId"
              :options="proveedores"
              placeholder="Selecciona el proveedor..."
            />
          </div>

          <!-- Método de pago -->
          <div class="space-y-2">
            <label class="text-xs font-black text-slate-500 uppercase tracking-widest">Método de pago</label>
            <div class="grid grid-cols-2 gap-2">
              <button
                v-for="metodo in metodosPago"
                :key="metodo.id"
                @click="metodoPago = metodo.id"
                :disabled="!!turnoId"
                class="flex items-center justify-center gap-2 py-3 rounded-2xl border-2 font-black text-sm transition-all disabled:opacity-50"
                :class="metodoPago === metodo.id
                  ? 'border-[#00126D] bg-[#00126D] text-white'
                  : 'border-slate-200 text-slate-600 hover:border-slate-300'"
              >
                <span>{{ metodo.emoji }}</span>
                {{ metodo.label }}
              </button>
            </div>
            <p v-if="turnoId" class="text-xs text-slate-400 font-semibold">Forzado a efectivo (pago desde caja)</p>
          </div>

          <!-- Notas -->
          <div class="space-y-2">
            <label class="text-xs font-black text-slate-500 uppercase tracking-widest">Notas <span class="text-slate-300">(opcional)</span></label>
            <textarea
              v-model="notas"
              rows="2"
              placeholder="Descripción o referencia del gasto..."
              class="w-full px-4 py-3 text-sm border border-slate-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-[#00126D]/20 focus:border-[#00126D] resize-none transition-colors"
            />
          </div>

          <!-- Error -->
          <p v-if="submitError" class="text-sm text-red-500 font-medium text-center">{{ submitError }}</p>
        </div>

        <!-- Footer -->
        <div class="px-4 py-4 border-t border-slate-100 flex gap-3">
          <button
            @click="step = 2"
            class="flex-none px-6 py-4 bg-slate-100 text-slate-600 font-black rounded-2xl text-sm active:scale-95 transition-all"
          >
            ← Atrás
          </button>
          <button
            @click="submit"
            :disabled="!proveedorId || submitting"
            class="flex-1 py-4 bg-[#00126D] text-white font-black rounded-2xl disabled:opacity-40 disabled:cursor-not-allowed active:scale-[0.98] transition-all"
          >
            <span v-if="submitting">Guardando...</span>
            <span v-else>✓ Confirmar Gasto</span>
          </button>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { api } from '@/api/client'
import SearchableSelect from './SearchableSelect.vue'
import GastoDetallesEditor from './GastoDetallesEditor.vue'
import CompraTextoQuickAdd from './CompraTextoQuickAdd.vue'

const props = defineProps<{
  turnoId?: number | null
}>()

const emit = defineEmits<{
  save: []
  cancel: []
}>()

// ── Step state ──────────────────────────────────
const step = ref(1)

// ── Step 1 ──────────────────────────────────────
const tipoGasto = ref<string | null>(null)

// Nómina se paga en el módulo de Compras (tanda de empleados), no desde caja.
const tiposGasto = [
  { id: 'directo', label: 'Insumos', emoji: '🛒', desc: 'Compras de materia prima y suministros' },
  { id: 'indirecto', label: 'Servicios', emoji: '🔧', desc: 'Mantenimiento, luz, agua, internet' },
]

function selectTipo(id: string) {
  tipoGasto.value = id
  // Nómina nunca lleva desglose de artículos.
  if (id === 'nomina') modoCaptura.value = 'rapido'
}

// ── Step 2 — Modo de captura: monto rápido / texto rápido / desglose ──
const modoCaptura = ref<'rapido' | 'texto' | 'desglose'>('rapido')
const detalles = ref<any[]>([])
const totalManualDetalle = ref<number | null>(null)
const articulos = ref<any[]>([])
const categorias = ref<any[]>([])

const sumaDetalles = computed(() =>
  detalles.value.reduce((sum, d) => {
    const linea = d.subtotal_linea != null
      ? Number(d.subtotal_linea)
      : (Number(d.cantidad) || 0) * (Number(d.precio_unitario) || 0)
    return sum + (Number(linea) || 0)
  }, 0)
)

function enableDesglose() {
  modoCaptura.value = 'desglose'
  if (detalles.value.length === 0) {
    detalles.value.push({ articulo_id: null, cantidad: 1, precio_unitario: 0, subtotal_linea: 0, _editadoManual: false })
  }
}

function onAgregarDetalles(nuevasLineas: any[]) {
  detalles.value.push(...nuevasLineas)
  modoCaptura.value = 'desglose'
}

function onArticuloCreado(articulosActualizados: any[]) {
  articulos.value = articulosActualizados
}

// ── Step 2 — Currency keypad ─────────────────────
const amountDisplay = ref('0')

const amountValue = computed(() => {
  if (modoCaptura.value === 'desglose' && tipoGasto.value !== 'nomina') {
    return totalManualDetalle.value != null ? Number(totalManualDetalle.value) : sumaDetalles.value
  }
  return parseFloat(amountDisplay.value) || 0
})

const amountFormatted = computed(() =>
  amountValue.value.toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
)

const amountKeys = [
  { label: '1', action: '1', variant: 'digit' },
  { label: '2', action: '2', variant: 'digit' },
  { label: '3', action: '3', variant: 'digit' },
  { label: '4', action: '4', variant: 'digit' },
  { label: '5', action: '5', variant: 'digit' },
  { label: '6', action: '6', variant: 'digit' },
  { label: '7', action: '7', variant: 'digit' },
  { label: '8', action: '8', variant: 'digit' },
  { label: '9', action: '9', variant: 'digit' },
  { label: 'C', action: 'clear', variant: 'clear' },
  { label: '0', action: '0', variant: 'digit' },
  { label: '⌫', action: 'back', variant: 'action' },
]

function handleAmountKey(action: string) {
  const cur = amountDisplay.value

  if (action === 'clear') {
    amountDisplay.value = '0'
    return
  }
  if (action === 'back') {
    if (cur.length <= 1) {
      amountDisplay.value = '0'
    } else {
      const trimmed = cur.slice(0, -1)
      amountDisplay.value = trimmed || '0'
    }
    return
  }
  // Digit
  if (action === '.') {
    if (cur.includes('.')) return
    amountDisplay.value = cur + '.'
    return
  }
  // Limit 2 decimal places
  if (cur.includes('.')) {
    const parts = cur.split('.')
    if (parts[1].length >= 2) return
  }
  if (cur === '0' && action !== '.') {
    amountDisplay.value = action
  } else {
    amountDisplay.value = cur + action
  }
}

function formatAmount(val: string): string {
  const num = parseFloat(val)
  if (isNaN(num)) return '0.00'
  const parts = val.split('.')
  const intPart = parseInt(parts[0] || '0').toLocaleString('es-MX')
  if (parts.length === 2) {
    return intPart + '.' + parts[1]
  }
  return intPart
}

// ── Step 3 ───────────────────────────────────────
const proveedores = ref<any[]>([])
const proveedorId = ref<number | null>(null)
const metodoPago = ref<string>('efectivo')
const notas = ref('')
const submitting = ref(false)
const submitError = ref<string | null>(null)

const metodosPago = [
  { id: 'efectivo', label: 'Efectivo', emoji: '💵' },
  { id: 'tarjeta', label: 'Tarjeta', emoji: '💳' },
]

// Force efectivo when turno linked
watch(() => props.turnoId, (id) => {
  if (id) metodoPago.value = 'efectivo'
}, { immediate: true })

async function submit() {
  if (!proveedorId.value) {
    submitError.value = 'Selecciona un proveedor'
    return
  }
  const usaDesglose = modoCaptura.value === 'desglose' && tipoGasto.value !== 'nomina'
  const detallesValidos = detalles.value.filter(d => d.articulo_id)
  if (usaDesglose && detallesValidos.length === 0) {
    submitError.value = 'Agrega al menos un artículo o usa monto rápido'
    return
  }
  if (amountValue.value <= 0) {
    submitError.value = 'El monto debe ser mayor a 0'
    return
  }
  submitting.value = true
  submitError.value = null
  try {
    const payload: Record<string, any> = {
      proveedor_id: proveedorId.value,
      tipo_gasto: tipoGasto.value,
      metodo_pago: metodoPago.value,
      // Con desglose, el total sale de la suma (o del total manual ajustado);
      // en monto rápido se manda el valor del keypad como total_manual.
      total_manual: usaDesglose ? (totalManualDetalle.value ?? null) : amountValue.value,
      notas: notas.value || null,
      descripcion: notas.value || null,
      detalles: usaDesglose
        ? detallesValidos.map(d => ({
            articulo_id: d.articulo_id,
            cantidad: d.cantidad,
            precio_unitario: d.precio_unitario,
            subtotal_linea: d.subtotal_linea,
          }))
        : [],
      fecha_gasto: new Date().toISOString(),
      turno_id: props.turnoId ?? null,
    }
    await api.post('/gastos/', payload)
    emit('save')
  } catch (e: any) {
    submitError.value = e?.response?.data?.detail || 'Error al guardar el gasto'
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  try {
    const [provs, arts, cats] = await Promise.all([
      api.get('/gastos/proveedores'),
      api.get('/gastos/articulos'),
      api.get('/gastos/categorias-articulo'),
    ])
    proveedores.value = provs.data
    articulos.value = arts.data
    categorias.value = cats.data
  } catch { /* silently ignore */ }
})
</script>
