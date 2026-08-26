<template>
  <div class="bg-white rounded-[2rem] border border-slate-100 shadow-sm overflow-hidden flex flex-col">
    <!-- Header + progreso -->
    <div class="px-5 sm:px-8 pt-6 pb-4 border-b border-slate-100">
      <div class="flex items-center justify-between mb-4">
        <div>
          <p class="text-[10px] font-black tracking-widest text-slate-400 uppercase">Paso {{ step }} de 3</p>
          <h2 class="text-xl font-black text-slate-900 tracking-tight">{{ pasoTitulo }}</h2>
        </div>
        <div class="flex items-center gap-2">
          <div
            v-for="n in 3"
            :key="n"
            class="transition-all duration-300 rounded-full"
            :class="n === step ? 'w-6 h-2.5 bg-[#00126D]' : n < step ? 'w-2.5 h-2.5 bg-[#00126D]/40' : 'w-2.5 h-2.5 bg-slate-200'"
          />
        </div>
      </div>
    </div>

    <div class="px-5 sm:px-8 py-6 flex-1">
      <!-- ══ PASO 1 — Datos ══ -->
      <div v-if="step === 1" class="space-y-6">
        <div class="space-y-3">
          <label class="text-[10px] font-black tracking-widest text-slate-400 uppercase">Tipo de gasto</label>
          <div class="grid gap-3">
            <button
              v-for="tipo in tiposGasto"
              :key="tipo.id"
              type="button"
              @click="selectTipo(tipo.id)"
              class="w-full flex items-center gap-4 px-5 py-4 rounded-2xl border-2 transition-all active:scale-[0.98] text-left"
              :class="tipoGasto === tipo.id ? 'border-[#00126D] bg-[#00126D]/5' : 'border-slate-100 bg-slate-50 hover:border-slate-200'"
            >
              <span class="text-2xl">{{ tipo.emoji }}</span>
              <div class="flex-1 min-w-0">
                <p class="font-black text-slate-800">{{ tipo.label }}</p>
                <p class="text-xs text-slate-500">{{ tipo.desc }}</p>
              </div>
              <div
                class="w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0"
                :class="tipoGasto === tipo.id ? 'border-[#00126D] bg-[#00126D]' : 'border-slate-300'"
              >
                <div v-if="tipoGasto === tipo.id" class="w-2 h-2 bg-white rounded-full" />
              </div>
            </button>
          </div>
        </div>

        <!-- Proveedor (no aplica a nómina) -->
        <div v-if="tipoGasto !== 'nomina'" class="space-y-3">
          <label class="text-[10px] font-black tracking-widest text-slate-400 uppercase">Proveedor</label>
          <SearchableSelect v-model="proveedorId" :options="proveedores" placeholder="Busca o selecciona proveedor..." />
        </div>
      </div>

      <!-- ══ PASO 2 — Artículos (o tanda de nómina) ══ -->
      <div v-else-if="step === 2">
        <!-- Nómina: tanda de empleados -->
        <div v-if="tipoGasto === 'nomina'" class="space-y-4">
          <div v-if="nominaLineas.length" class="space-y-2">
            <div v-for="(l, idx) in nominaLineas" :key="idx" class="flex items-center gap-3 bg-slate-50 rounded-2xl p-3">
              <div class="w-9 h-9 rounded-xl bg-[#00126D]/10 text-[#00126D] flex items-center justify-center font-black flex-shrink-0">
                {{ nombreEmpleado(l.usuario_id).charAt(0).toUpperCase() }}
              </div>
              <div class="flex-1 min-w-0">
                <p class="font-black text-slate-800 text-sm truncate">{{ nombreEmpleado(l.usuario_id) }}</p>
                <p v-if="l.notas" class="text-xs text-slate-500 truncate">{{ l.notas }}</p>
              </div>
              <p class="text-sm font-black text-slate-900 flex-shrink-0">${{ fmt(l.monto) }}</p>
              <div class="flex items-center gap-1 flex-shrink-0">
                <button type="button" @click="editEmp(idx)" class="w-8 h-8 flex items-center justify-center rounded-xl text-slate-400 hover:bg-white hover:text-[#00126D] transition-all">
                  <Pencil class="w-4 h-4" />
                </button>
                <button type="button" @click="removeEmp(idx)" class="w-8 h-8 flex items-center justify-center rounded-xl text-slate-400 hover:bg-rose-50 hover:text-rose-500 transition-all">
                  <Trash2 class="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
          <p v-else class="text-center py-6 text-xs font-bold text-slate-300">Aún no agregas empleados a la tanda.</p>

          <div class="flex items-center justify-between px-1">
            <div>
              <p class="text-[10px] font-black tracking-widest text-slate-400 uppercase">Total nómina</p>
              <p class="text-lg font-black text-slate-900">${{ fmt(sumaNomina) }}</p>
            </div>
            <button
              type="button"
              @click="openAddEmp"
              :disabled="empleadosDisponibles.length === 0"
              class="px-5 py-3 bg-[#00126D] text-white rounded-2xl text-xs font-black uppercase tracking-widest flex items-center gap-2 active:scale-95 transition-all disabled:opacity-40"
            >
              <Plus class="w-4 h-4" /> Agregar empleado
            </button>
          </div>
        </div>

        <!-- Carrito de artículos -->
        <div v-else class="space-y-4">
          <div v-if="detalles.length" class="space-y-2">
            <div v-for="(d, idx) in detalles" :key="idx" class="flex items-center gap-3 bg-slate-50 rounded-2xl p-3">
              <div class="flex-1 min-w-0">
                <p class="font-black text-slate-800 text-sm truncate">{{ nombreArticulo(d.articulo_id) }}</p>
                <p class="text-xs text-slate-500 font-semibold">{{ fmtNum(d.cantidad) }} × ${{ fmt(d.precio_unitario) }}</p>
              </div>
              <p class="text-sm font-black text-slate-900 flex-shrink-0">${{ fmt(d.subtotal_linea) }}</p>
              <div class="flex items-center gap-1 flex-shrink-0">
                <button type="button" @click="editLinea(idx)" class="w-8 h-8 flex items-center justify-center rounded-xl text-slate-400 hover:bg-white hover:text-[#00126D] transition-all">
                  <Pencil class="w-4 h-4" />
                </button>
                <button type="button" @click="removeLinea(idx)" class="w-8 h-8 flex items-center justify-center rounded-xl text-slate-400 hover:bg-rose-50 hover:text-rose-500 transition-all">
                  <Trash2 class="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
          <p v-else class="text-center py-6 text-xs font-bold text-slate-300">Aún no agregas artículos.</p>

          <div class="flex items-center justify-between px-1 gap-2">
            <div>
              <p class="text-[10px] font-black tracking-widest text-slate-400 uppercase">Suma</p>
              <p class="text-lg font-black text-slate-900">${{ fmt(suma) }}</p>
            </div>
            <div class="flex items-center gap-2">
              <button type="button" @click="showTexto = true" class="px-5 py-3 bg-indigo-50 text-indigo-600 rounded-2xl text-xs font-black uppercase tracking-widest flex items-center gap-2 active:scale-95 transition-all">
                <Sparkles class="w-4 h-4" /> Texto rápido
              </button>
              <button type="button" @click="openAdd" class="px-5 py-3 bg-[#00126D] text-white rounded-2xl text-xs font-black uppercase tracking-widest flex items-center gap-2 active:scale-95 transition-all">
                <Plus class="w-4 h-4" /> Agregar artículo
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- ══ PASO 3 — Confirmar ══ -->
      <div v-else-if="step === 3" class="space-y-6">
        <div class="bg-slate-50 rounded-2xl p-5 space-y-3">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-slate-500">{{ tiposGasto.find(t => t.id === tipoGasto)?.label }}</span>
            <span v-if="tipoGasto !== 'nomina'" class="text-xs font-bold text-slate-700 truncate max-w-[55%] text-right">{{ nombreProveedor }}</span>
          </div>
          <div v-if="tipoGasto === 'nomina'" class="flex items-center justify-between text-xs text-slate-500 font-semibold">
            <span>{{ nominaLineas.length }} empleado(s)</span>
            <span>Total ${{ fmt(sumaNomina) }}</span>
          </div>
          <div v-else class="flex items-center justify-between text-xs text-slate-500 font-semibold">
            <span>{{ detalles.length }} artículo(s)</span>
            <span>Suma ${{ fmt(suma) }}</span>
          </div>
        </div>

        <div class="space-y-3">
          <label class="text-[10px] font-black tracking-widest text-slate-400 uppercase">Método de pago</label>
          <div class="grid grid-cols-2 gap-2">
            <button
              v-for="m in metodosPago"
              :key="m.id"
              type="button"
              @click="metodoPago = m.id"
              class="flex items-center justify-center gap-2 py-3.5 rounded-2xl border-2 font-black text-sm transition-all"
              :class="metodoPago === m.id ? 'border-[#00126D] bg-[#00126D] text-white' : 'border-slate-200 text-slate-600'"
            >
              <span>{{ m.emoji }}</span> {{ m.label }}
            </button>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div class="space-y-2">
            <label class="text-[10px] font-black tracking-widest text-slate-400 uppercase">Fecha</label>
            <input type="datetime-local" v-model="fechaGasto" class="w-full bg-slate-50 border-0 rounded-2xl px-4 py-3 text-sm font-bold text-slate-700 outline-none focus:ring-2 focus:ring-[#00126D]">
          </div>
          <div class="space-y-2">
            <label class="text-[10px] font-black tracking-widest text-slate-400 uppercase">Folio / Referencia</label>
            <input type="text" v-model="folio" placeholder="Opcional" class="w-full bg-slate-50 border-0 rounded-2xl px-4 py-3 text-sm font-bold text-slate-700 outline-none focus:ring-2 focus:ring-[#00126D]">
          </div>
        </div>

        <div class="space-y-2">
          <label class="text-[10px] font-black tracking-widest text-slate-400 uppercase">Notas</label>
          <textarea v-model="notas" rows="2" placeholder="Opcional" class="w-full bg-slate-50 border-0 rounded-2xl px-4 py-3 text-sm font-bold text-slate-700 outline-none focus:ring-2 focus:ring-[#00126D] resize-none"></textarea>
        </div>

        <div class="bg-[#00126D] rounded-2xl p-5 flex items-center justify-between">
          <div>
            <p class="text-[10px] font-black tracking-widest text-white/60 uppercase">Total a pagar</p>
            <p class="text-3xl font-black text-white tracking-tighter">${{ fmt(totalFinal) }}</p>
          </div>
          <button
            v-if="tipoGasto !== 'nomina'"
            type="button"
            @click="ajustarTotal = !ajustarTotal"
            class="px-3 py-2 rounded-xl bg-white/10 text-white text-[10px] font-black uppercase tracking-widest"
          >
            {{ ajustarTotal ? 'Usar suma' : 'Ajustar' }}
          </button>
        </div>
        <div v-if="ajustarTotal && tipoGasto !== 'nomina'" class="relative">
          <span class="absolute left-5 top-1/2 -translate-y-1/2 text-lg font-black text-slate-300">$</span>
          <input
            type="number" inputmode="decimal" step="0.01" min="0"
            v-model.number="totalManual"
            class="w-full bg-slate-50 border-2 border-[#00126D]/20 rounded-2xl pl-10 pr-5 py-4 text-xl font-black text-slate-900 text-right outline-none focus:ring-2 focus:ring-[#00126D]"
            placeholder="Total manual"
          >
        </div>

        <p v-if="submitError" class="text-sm text-rose-500 font-bold text-center">{{ submitError }}</p>
      </div>
    </div>

    <!-- Footer navegación -->
    <div class="px-5 sm:px-8 py-5 border-t border-slate-100 bg-slate-50/50 flex gap-3">
      <button
        v-if="step > 1"
        type="button"
        @click="step--"
        class="flex-none px-6 py-4 bg-white text-slate-500 border border-slate-200 font-black rounded-2xl text-sm active:scale-95 transition-all"
      >
        ← Atrás
      </button>
      <button
        v-if="step < 3"
        type="button"
        @click="next"
        :disabled="!canAdvance"
        class="flex-1 py-4 bg-[#00126D] text-white font-black rounded-2xl disabled:opacity-40 disabled:cursor-not-allowed active:scale-[0.98] transition-all"
      >
        Siguiente →
      </button>
      <button
        v-else
        type="button"
        @click="submit"
        :disabled="submitting"
        class="flex-1 py-4 bg-[#00126D] text-white font-black rounded-2xl disabled:opacity-40 active:scale-[0.98] transition-all"
      >
        <span v-if="submitting">Guardando...</span>
        <span v-else>✓ Confirmar {{ tipoGasto === 'nomina' ? 'nómina' : 'gasto' }}</span>
      </button>
    </div>

    <!-- ══ Sub-modal: agregar / editar artículo ══ -->
    <div v-if="showAdd" class="fixed inset-0 z-[160] flex items-end sm:items-center justify-center bg-slate-900/60 backdrop-blur-sm p-0 sm:p-4">
      <div class="bg-white w-full sm:max-w-md rounded-t-[2rem] sm:rounded-[2rem] shadow-2xl flex flex-col max-h-[90vh] animate-in">
        <div class="px-6 py-5 border-b border-slate-100 flex items-center justify-between">
          <h3 class="text-lg font-black text-slate-900">{{ editIdx === null ? 'Agregar artículo' : 'Editar artículo' }}</h3>
          <button type="button" @click="closeAdd" class="w-9 h-9 flex items-center justify-center rounded-xl bg-slate-100 text-slate-400 hover:bg-slate-900 hover:text-white transition-all">
            <X class="w-5 h-5" />
          </button>
        </div>
        <div class="px-6 py-5 space-y-5 overflow-y-auto">
          <div class="space-y-2">
            <label class="text-[10px] font-black tracking-widest text-slate-400 uppercase">Artículo</label>
            <SearchableSelect v-model="draft.articulo_id" :options="articulos" placeholder="Buscar artículo..." />
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div class="space-y-2">
              <label class="text-[10px] font-black tracking-widest text-slate-400 uppercase">Cantidad</label>
              <input type="number" inputmode="decimal" step="0.01" min="0" v-model.number="draft.cantidad" @input="recalcDraft" class="w-full bg-slate-50 border-0 rounded-2xl px-4 py-3.5 text-lg font-black text-slate-800 text-center outline-none focus:ring-2 focus:ring-[#00126D]">
            </div>
            <div class="space-y-2">
              <label class="text-[10px] font-black tracking-widest text-slate-400 uppercase">P. Unitario</label>
              <div class="relative">
                <span class="absolute left-3 top-1/2 -translate-y-1/2 text-sm font-black text-slate-300">$</span>
                <input type="number" inputmode="decimal" step="0.01" min="0" v-model.number="draft.precio_unitario" @input="recalcDraft" class="w-full bg-slate-50 border-0 rounded-2xl pl-7 pr-3 py-3.5 text-lg font-black text-slate-800 text-right outline-none focus:ring-2 focus:ring-[#00126D]">
              </div>
            </div>
          </div>
          <div class="space-y-2">
            <label class="text-[10px] font-black tracking-widest text-indigo-400 uppercase">Total (editable)</label>
            <div class="relative">
              <span class="absolute left-4 top-1/2 -translate-y-1/2 text-lg font-black text-indigo-300">$</span>
              <input type="number" inputmode="decimal" step="0.01" min="0" v-model.number="draft.subtotal_linea" @input="draft._editadoManual = true" class="w-full bg-indigo-50/60 border border-indigo-100 rounded-2xl pl-9 pr-4 py-4 text-xl font-black text-indigo-900 text-right outline-none focus:ring-2 focus:ring-[#00126D]">
            </div>
          </div>
        </div>
        <div class="px-6 py-5 border-t border-slate-100">
          <button type="button" @click="confirmAdd" :disabled="!draft.articulo_id" class="w-full py-4 bg-[#00126D] text-white font-black rounded-2xl disabled:opacity-40 active:scale-[0.98] transition-all">
            {{ editIdx === null ? 'Agregar al carrito' : 'Guardar cambios' }}
          </button>
        </div>
      </div>
    </div>

    <!-- ══ Sub-modal: captura rápida de artículos por texto ══ -->
    <div v-if="showTexto" class="fixed inset-0 z-[160] flex items-end sm:items-center justify-center bg-slate-900/60 backdrop-blur-sm p-0 sm:p-4">
      <div class="bg-white w-full sm:max-w-md rounded-t-[2rem] sm:rounded-[2rem] shadow-2xl flex flex-col max-h-[90vh] animate-in">
        <div class="px-6 py-5 border-b border-slate-100 flex items-center justify-between">
          <h3 class="text-lg font-black text-slate-900">Texto rápido</h3>
          <button type="button" @click="showTexto = false" class="w-9 h-9 flex items-center justify-center rounded-xl bg-slate-100 text-slate-400 hover:bg-slate-900 hover:text-white transition-all">
            <X class="w-5 h-5" />
          </button>
        </div>
        <div class="overflow-y-auto">
          <CompraTextoQuickAdd
            :articulos="articulos"
            :categorias="categorias"
            @agregar-detalles="onAgregarDetallesTexto"
            @articulo-creado="onArticuloCreadoTexto"
          />
        </div>
      </div>
    </div>

    <!-- ══ Sub-modal: agregar / editar empleado (nómina) ══ -->
    <div v-if="showAddEmp" class="fixed inset-0 z-[160] flex items-end sm:items-center justify-center bg-slate-900/60 backdrop-blur-sm p-0 sm:p-4">
      <div class="bg-white w-full sm:max-w-md rounded-t-[2rem] sm:rounded-[2rem] shadow-2xl flex flex-col max-h-[90vh] animate-in">
        <div class="px-6 py-5 border-b border-slate-100 flex items-center justify-between">
          <h3 class="text-lg font-black text-slate-900">{{ empEditIdx === null ? 'Agregar empleado' : 'Editar pago' }}</h3>
          <button type="button" @click="closeAddEmp" class="w-9 h-9 flex items-center justify-center rounded-xl bg-slate-100 text-slate-400 hover:bg-slate-900 hover:text-white transition-all">
            <X class="w-5 h-5" />
          </button>
        </div>
        <div class="px-6 py-5 space-y-5 overflow-y-auto">
          <div class="space-y-2">
            <label class="text-[10px] font-black tracking-widest text-slate-400 uppercase">Empleado</label>
            <SearchableSelect v-model="empDraft.usuario_id" :options="empOptions" placeholder="Buscar empleado..." />
          </div>
          <div class="space-y-2">
            <label class="text-[10px] font-black tracking-widest text-slate-400 uppercase">Monto a pagar</label>
            <div class="relative">
              <span class="absolute left-5 top-1/2 -translate-y-1/2 text-2xl font-black text-slate-300">$</span>
              <input type="number" inputmode="decimal" step="0.01" min="0" v-model.number="empDraft.monto" class="w-full bg-slate-50 border-0 rounded-2xl pl-12 pr-5 py-5 text-2xl font-black text-slate-800 text-center outline-none focus:ring-2 focus:ring-[#00126D]" placeholder="0.00">
            </div>
          </div>
          <div class="space-y-2">
            <label class="text-[10px] font-black tracking-widest text-slate-400 uppercase">Concepto / Notas</label>
            <input type="text" v-model="empDraft.notas" placeholder="Opcional (ej. quincena, bono)" class="w-full bg-slate-50 border-0 rounded-2xl px-4 py-3 text-sm font-bold text-slate-700 outline-none focus:ring-2 focus:ring-[#00126D]">
          </div>
        </div>
        <div class="px-6 py-5 border-t border-slate-100">
          <button type="button" @click="confirmAddEmp" :disabled="!empDraft.usuario_id || (Number(empDraft.monto) || 0) <= 0" class="w-full py-4 bg-[#00126D] text-white font-black rounded-2xl disabled:opacity-40 active:scale-[0.98] transition-all">
            {{ empEditIdx === null ? 'Agregar a la tanda' : 'Guardar cambios' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { api } from '@/api/client'
import SearchableSelect from './SearchableSelect.vue'
import CompraTextoQuickAdd from './CompraTextoQuickAdd.vue'
import { Plus, Trash2, Pencil, X, Sparkles } from 'lucide-vue-next'

const emit = defineEmits<{ saved: [] }>()

const tiposGasto = [
  { id: 'directo', label: 'Insumos', emoji: '🛒', desc: 'Materia prima y suministros' },
  { id: 'indirecto', label: 'Servicios', emoji: '🔧', desc: 'Mantenimiento, luz, agua, internet' },
  { id: 'nomina', label: 'Nómina', emoji: '👥', desc: 'Pago a empleados (tanda)' },
]
const metodosPago = [
  { id: 'efectivo', label: 'Efectivo', emoji: '💵' },
  { id: 'tarjeta', label: 'Tarjeta', emoji: '💳' },
]

const step = ref(1)
const tipoGasto = ref<string | null>(null)
const proveedorId = ref<number | null>(null)
const proveedores = ref<any[]>([])
const articulos = ref<any[]>([])
const categorias = ref<any[]>([])
const empleados = ref<any[]>([])
const showTexto = ref(false)

const detalles = ref<any[]>([])
const nominaLineas = ref<any[]>([]) // { usuario_id, monto, notas }

const metodoPago = ref('efectivo')
const folio = ref('')
const notas = ref('')
const fechaGasto = ref(localNow())
const totalManual = ref<number | null>(null)
const ajustarTotal = ref(false)

const submitting = ref(false)
const submitError = ref<string | null>(null)

// ── sub-modal artículo ──
const showAdd = ref(false)
const editIdx = ref<number | null>(null)
const draft = reactive<any>({ articulo_id: null, cantidad: 1, precio_unitario: 0, subtotal_linea: 0, _editadoManual: false })

// ── sub-modal empleado ──
const showAddEmp = ref(false)
const empEditIdx = ref<number | null>(null)
const empDraft = reactive<any>({ usuario_id: null, monto: null, notas: '' })

function localNow() {
  const d = new Date()
  const tz = d.getTimezoneOffset() * 60000
  return new Date(d.getTime() - tz).toISOString().slice(0, 16)
}

const fmt = (v: any) => (Number(v) || 0).toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const fmtNum = (v: any) => (Number(v) || 0).toLocaleString('es-MX', { maximumFractionDigits: 2 })

const nombreArticulo = (id: number) => articulos.value.find(a => a.id === id)?.nombre ?? 'Artículo'
const nombreEmpleado = (id: number) => empleados.value.find(e => e.id === id)?.nombre ?? 'Empleado'
const nombreProveedor = computed(() => proveedores.value.find(p => p.id === proveedorId.value)?.nombre ?? '—')

// Empleados aún no agregados a la tanda (para el buscador del sub-modal).
const empleadosDisponibles = computed(() => {
  const usados = new Set(nominaLineas.value.map(l => l.usuario_id))
  return empleados.value.filter(e => !usados.has(e.id))
})
// Opciones del select: disponibles + (si editando) el ya seleccionado.
const empOptions = computed(() => {
  if (empEditIdx.value !== null) {
    const cur = nominaLineas.value[empEditIdx.value]?.usuario_id
    return empleados.value.filter(e => !nominaLineas.value.some((l, i) => i !== empEditIdx.value && l.usuario_id === e.id) || e.id === cur)
  }
  return empleadosDisponibles.value
})

const pasoTitulo = computed(() => {
  if (step.value === 1) return 'Datos del gasto'
  if (step.value === 2) return tipoGasto.value === 'nomina' ? 'Tanda de nómina' : 'Artículos'
  return 'Confirmar'
})

const suma = computed(() => detalles.value.reduce((s, d) => {
  const linea = d.subtotal_linea != null ? Number(d.subtotal_linea) : (Number(d.cantidad) || 0) * (Number(d.precio_unitario) || 0)
  return s + (Number(linea) || 0)
}, 0))

const sumaNomina = computed(() => nominaLineas.value.reduce((s, l) => s + (Number(l.monto) || 0), 0))

const totalFinal = computed(() => {
  if (tipoGasto.value === 'nomina') return sumaNomina.value
  if (ajustarTotal.value && totalManual.value != null) return Number(totalManual.value) || 0
  return suma.value
})

const canAdvance = computed(() => {
  if (step.value === 1) {
    return tipoGasto.value === 'nomina' ? !!tipoGasto.value : (!!tipoGasto.value && !!proveedorId.value)
  }
  if (step.value === 2) {
    return tipoGasto.value === 'nomina' ? (nominaLineas.value.length > 0 && sumaNomina.value > 0) : detalles.value.length > 0
  }
  return true
})

function selectTipo(id: string) {
  tipoGasto.value = id
}

function next() {
  if (canAdvance.value && step.value < 3) step.value++
}

// ── carrito artículos ──
function openAdd() {
  editIdx.value = null
  Object.assign(draft, { articulo_id: null, cantidad: 1, precio_unitario: 0, subtotal_linea: 0, _editadoManual: false })
  showAdd.value = true
}
function editLinea(idx: number) {
  editIdx.value = idx
  Object.assign(draft, { ...detalles.value[idx] })
  showAdd.value = true
}
function closeAdd() { showAdd.value = false; editIdx.value = null }
function recalcDraft() {
  if (draft._editadoManual) return
  draft.subtotal_linea = Number(((Number(draft.cantidad) || 0) * (Number(draft.precio_unitario) || 0)).toFixed(2))
}
function confirmAdd() {
  if (!draft.articulo_id) return
  const line = {
    articulo_id: draft.articulo_id,
    cantidad: Number(draft.cantidad) || 0,
    precio_unitario: Number(draft.precio_unitario) || 0,
    subtotal_linea: Number(draft.subtotal_linea) || 0,
    _editadoManual: !!draft._editadoManual,
  }
  if (editIdx.value === null) detalles.value.push(line)
  else detalles.value[editIdx.value] = line
  closeAdd()
}
function removeLinea(idx: number) { detalles.value.splice(idx, 1) }

function onAgregarDetallesTexto(nuevasLineas: any[]) {
  detalles.value.push(...nuevasLineas)
  showTexto.value = false
}
function onArticuloCreadoTexto(articulosActualizados: any[]) {
  articulos.value = articulosActualizados
}

// ── tanda nómina ──
function openAddEmp() {
  empEditIdx.value = null
  Object.assign(empDraft, { usuario_id: null, monto: null, notas: '' })
  showAddEmp.value = true
}
function editEmp(idx: number) {
  empEditIdx.value = idx
  Object.assign(empDraft, { ...nominaLineas.value[idx] })
  showAddEmp.value = true
}
function closeAddEmp() { showAddEmp.value = false; empEditIdx.value = null }
function confirmAddEmp() {
  if (!empDraft.usuario_id || (Number(empDraft.monto) || 0) <= 0) return
  const line = { usuario_id: empDraft.usuario_id, monto: Number(empDraft.monto) || 0, notas: empDraft.notas || null }
  if (empEditIdx.value === null) nominaLineas.value.push(line)
  else nominaLineas.value[empEditIdx.value] = line
  closeAddEmp()
}
function removeEmp(idx: number) { nominaLineas.value.splice(idx, 1) }

async function submit() {
  submitError.value = null
  const esNomina = tipoGasto.value === 'nomina'
  if (!esNomina && !proveedorId.value) { submitError.value = 'Selecciona un proveedor'; step.value = 1; return }
  if (esNomina && nominaLineas.value.length === 0) { submitError.value = 'Agrega al menos un empleado'; step.value = 2; return }
  if (!esNomina && detalles.value.length === 0) { submitError.value = 'Agrega al menos un artículo'; step.value = 2; return }

  submitting.value = true
  try {
    const payload: Record<string, any> = {
      proveedor_id: esNomina ? null : proveedorId.value,
      tipo_gasto: tipoGasto.value,
      metodo_pago: metodoPago.value,
      folio: folio.value || null,
      notas: notas.value || null,
      descripcion: notas.value || null,
      fecha_gasto: fechaGasto.value ? new Date(fechaGasto.value).toISOString() : new Date().toISOString(),
      turno_id: null,
      total_manual: esNomina ? null : (ajustarTotal.value && totalManual.value != null ? Number(totalManual.value) : null),
      detalles: esNomina ? [] : detalles.value.map(d => ({
        articulo_id: d.articulo_id,
        cantidad: d.cantidad,
        precio_unitario: d.precio_unitario,
        subtotal_linea: d.subtotal_linea,
      })),
      nomina_detalles: esNomina ? nominaLineas.value.map(l => ({
        usuario_id: l.usuario_id,
        monto: l.monto,
        notas: l.notas || null,
      })) : [],
    }
    await api.post('/gastos/', payload)
    emit('saved')
  } catch (e: any) {
    submitError.value = e?.response?.data?.detail || 'Error al guardar'
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  try {
    const [provs, arts, emps, cats] = await Promise.all([
      api.get('/gastos/proveedores'),
      api.get('/gastos/articulos'),
      api.get('/gastos/empleados'),
      api.get('/gastos/categorias-articulo'),
    ])
    proveedores.value = provs.data
    articulos.value = arts.data
    empleados.value = emps.data
    categorias.value = cats.data
  } catch { /* ignore */ }
})
</script>

<style scoped>
.animate-in { animation: slideUp 0.25s ease-out; }
@keyframes slideUp { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: translateY(0); } }
</style>
