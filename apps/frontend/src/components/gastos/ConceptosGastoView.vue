<template>
  <div class="space-y-8">
    <p v-if="error" role="alert" class="text-sm font-bold text-rose-600">{{ error }}</p>

    <!-- Pagos recurrentes: lo que vence primero, arriba -->
    <section class="space-y-3">
      <div class="flex items-center justify-between gap-3">
        <h3 class="text-xs font-black tracking-widest text-slate-400 uppercase">Pagos recurrentes</h3>
        <button type="button" @click="nuevo('mensual')" class="inline-flex items-center gap-1.5 min-h-11 px-3 text-sm font-black text-blue-600">
          <Plus class="h-4 w-4" /> Añadir
        </button>
      </div>
      <p v-if="!recurrentes.length" class="text-sm font-bold text-slate-400">
        Aún no hay pagos recurrentes. Agrega los de abajo con un toque.
      </p>
      <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <div
          v-for="c in recurrentes"
          :key="c.concepto.id"
          class="bg-white border rounded-2xl p-4 space-y-3"
          :class="[
            c.estado === 'vencido' ? 'border-rose-200' : c.estado === 'pendiente' ? 'border-amber-200' : 'border-slate-100',
            { 'opacity-50': !c.concepto.activo },
          ]"
        >
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0">
              <p class="font-black text-slate-800 truncate">{{ c.concepto.nombre }}</p>
              <p class="text-xs font-bold text-slate-400">
                {{ etiquetaFrecuencia(c.concepto) }}<template v-if="c.concepto.monto_tipico"> · ~${{ c.concepto.monto_tipico }}</template>
              </p>
              <p class="text-xs font-bold text-slate-400">{{ c.ultimo_gasto ? `Último pago: ${c.ultimo_gasto.slice(0, 10)}` : 'Sin pagos registrados' }}</p>
            </div>
            <span
              class="shrink-0 text-[10px] font-black uppercase tracking-widest px-2 py-1 rounded-lg"
              :class="{
                'bg-rose-50 text-rose-700': c.estado === 'vencido',
                'bg-amber-50 text-amber-700': c.estado === 'pendiente',
                'bg-emerald-50 text-emerald-700': c.estado === 'al_corriente',
              }"
            >{{ c.estado.replace('_', ' ') }}</span>
          </div>
          <div class="flex gap-2">
            <button type="button" @click="$emit('registrar', c.concepto.id)" class="flex-1 min-h-11 rounded-xl bg-[#00126D] text-white text-sm font-black active:scale-[0.98]">
              Registrar pago
            </button>
            <button type="button" @click="editar(c.concepto)" class="min-h-11 px-4 rounded-xl bg-slate-100 text-slate-600 text-sm font-black" aria-label="Editar concepto">
              <Pencil class="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      <!-- Sugeridos -->
      <div v-if="sugeridos.length" class="space-y-2 pt-2">
        <p class="text-xs font-bold text-slate-400">Sugeridos (se abre el formulario para ajustar monto y frecuencia):</p>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="s in sugeridos"
            :key="s.nombre"
            type="button"
            @click="desdeSugerido(s)"
            class="min-h-11 px-3 rounded-xl border border-dashed border-slate-300 text-sm font-bold text-slate-600 hover:border-blue-400 hover:text-blue-600"
          >
            + {{ s.nombre }}
          </button>
        </div>
      </div>
    </section>

    <!-- Imprevistos -->
    <section class="space-y-3">
      <div class="flex items-center justify-between gap-3">
        <h3 class="text-xs font-black tracking-widest text-slate-400 uppercase">Imprevistos</h3>
        <button type="button" @click="nuevo('eventual')" class="inline-flex items-center gap-1.5 min-h-11 px-3 text-sm font-black text-blue-600">
          <Plus class="h-4 w-4" /> Añadir
        </button>
      </div>
      <p class="text-xs font-bold text-slate-400">Desazolves, reparaciones, herramientas: no tienen fecha fija, siempre piden describir qué pasó.</p>
      <div class="flex flex-wrap gap-2">
        <div v-for="c in imprevistos" :key="c.concepto.id" class="inline-flex rounded-xl border border-slate-200 bg-white overflow-hidden" :class="{ 'opacity-50': !c.concepto.activo }">
          <button type="button" @click="$emit('registrar', c.concepto.id)" class="min-h-11 px-4 text-sm font-black text-slate-700 hover:bg-slate-50">
            {{ c.concepto.nombre }}
          </button>
          <button type="button" @click="editar(c.concepto)" class="min-h-11 px-3 border-l border-slate-100 text-slate-400 hover:text-slate-700" aria-label="Editar concepto">
            <Pencil class="h-4 w-4" />
          </button>
        </div>
      </div>
    </section>

    <form v-if="form" @submit.prevent="guardar" class="bg-white border border-slate-200 rounded-2xl p-4 sm:p-6 space-y-4 max-w-xl">
      <h3 class="font-black text-slate-800">{{ form.id ? 'Editar' : 'Nuevo' }}</h3>
      <label class="block space-y-1">
        <span class="text-xs font-black text-slate-400 uppercase tracking-widest">Nombre</span>
        <input v-model="form.nombre" required maxlength="100" placeholder="Renta, Agua, Gas..." class="w-full border border-slate-200 rounded-xl px-3 py-3 text-base font-bold">
      </label>
      <label class="block space-y-1">
        <span class="text-xs font-black text-slate-400 uppercase tracking-widest">¿Cada cuándo se paga?</span>
        <select v-model="form.frecuencia" class="w-full border border-slate-200 rounded-xl px-3 py-3 text-base font-bold bg-white">
          <option v-for="f in frecuencias" :key="f.id" :value="f.id">{{ f.label }}</option>
        </select>
      </label>
      <div v-if="form.frecuencia !== 'eventual'" class="grid grid-cols-2 gap-3">
        <label class="block space-y-1">
          <span class="text-xs font-black text-slate-400 uppercase tracking-widest">Monto típico</span>
          <input v-model.number="form.monto_tipico" type="number" min="0" step="0.01" inputmode="decimal" class="w-full border border-slate-200 rounded-xl px-3 py-3 text-base font-bold">
        </label>
        <label v-if="form.frecuencia === 'cada_n_dias'" class="block space-y-1">
          <span class="text-xs font-black text-slate-400 uppercase tracking-widest">Cada cuántos días</span>
          <input v-model.number="form.intervalo_dias" type="number" min="1" max="365" required inputmode="numeric" class="w-full border border-slate-200 rounded-xl px-3 py-3 text-base font-bold">
        </label>
        <label v-else-if="form.frecuencia === 'mensual'" class="block space-y-1">
          <span class="text-xs font-black text-slate-400 uppercase tracking-widest">Día que vence (1-31)</span>
          <input v-model.number="form.dia_vencimiento" type="number" min="1" max="31" inputmode="numeric" class="w-full border border-slate-200 rounded-xl px-3 py-3 text-base font-bold">
        </label>
      </div>
      <label class="flex items-center gap-2 min-h-11 text-sm font-bold text-slate-600">
        <input v-model="form.activo" type="checkbox" class="h-5 w-5"> Activo
      </label>
      <div class="flex gap-2">
        <button type="submit" :disabled="guardando" class="flex-1 min-h-12 bg-[#00126D] text-white font-black rounded-xl disabled:opacity-40">Guardar</button>
        <button type="button" @click="form = null" class="min-h-12 px-5 bg-slate-100 text-slate-600 font-black rounded-xl">Cancelar</button>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Pencil, Plus } from 'lucide-vue-next'
import { api } from '@/api/client'
import type { ConceptoGasto, ConceptoPendiente } from '@/stores/catalogos-gastos'

defineEmits<{ registrar: [conceptoId: number] }>()

const frecuencias = [
  { id: 'mensual', label: 'Cada mes (renta, internet...)' },
  { id: 'semanal', label: 'Cada semana' },
  { id: 'bimestral', label: 'Cada 2 meses' },
  { id: 'anual', label: 'Cada año (permisos...)' },
  { id: 'cada_n_dias', label: 'Cada cierto número de días (gas...)' },
  { id: 'eventual', label: 'Imprevisto, sin fecha fija' },
] as const
const sugeridosBase: Array<Pick<ConceptoGasto, 'nombre' | 'frecuencia'> & { intervalo_dias?: number }> = [
  { nombre: 'Renta', frecuencia: 'mensual' },
  { nombre: 'Luz', frecuencia: 'mensual' },
  { nombre: 'Agua', frecuencia: 'mensual' },
  { nombre: 'Gas', frecuencia: 'cada_n_dias', intervalo_dias: 21 },
  { nombre: 'Internet', frecuencia: 'mensual' },
  { nombre: 'Teléfono', frecuencia: 'mensual' },
  { nombre: 'Recolección de basura', frecuencia: 'mensual' },
  { nombre: 'Fumigación', frecuencia: 'bimestral' },
  { nombre: 'Contador', frecuencia: 'mensual' },
  { nombre: 'Sistema POS / software', frecuencia: 'mensual' },
  { nombre: 'Alarma / seguridad', frecuencia: 'mensual' },
  { nombre: 'Permisos y licencias', frecuencia: 'anual' },
]
type Form = Partial<ConceptoGasto> & Pick<ConceptoGasto, 'nombre' | 'frecuencia' | 'activo'>

const conceptos = ref<ConceptoPendiente[]>([])
const form = ref<Form | null>(null)
const guardando = ref(false)
const error = ref('')

const recurrentes = computed(() => conceptos.value.filter((c) => c.concepto.frecuencia !== 'eventual'))
const imprevistos = computed(() => conceptos.value.filter((c) => c.concepto.frecuencia === 'eventual'))
const sugeridos = computed(() => {
  const existentes = new Set(conceptos.value.map((c) => c.concepto.nombre.toLowerCase()))
  return sugeridosBase.filter((s) => !existentes.has(s.nombre.toLowerCase()))
})

function etiquetaFrecuencia(c: ConceptoGasto) {
  if (c.frecuencia === 'cada_n_dias') return `cada ${c.intervalo_dias} días`
  return frecuencias.find((f) => f.id === c.frecuencia)?.label.split(' (')[0].toLowerCase() ?? c.frecuencia
}

async function cargar() {
  try {
    conceptos.value = (await api.get('/gastos/conceptos/pendientes')).data
    error.value = ''
  } catch {
    error.value = 'No se pudieron cargar los conceptos'
  }
}
const nuevo = (frecuencia: ConceptoGasto['frecuencia']) => {
  form.value = { nombre: '', monto_tipico: null, frecuencia, dia_vencimiento: null, intervalo_dias: null, activo: true }
}
const desdeSugerido = (s: (typeof sugeridosBase)[number]) => {
  form.value = { nombre: s.nombre, monto_tipico: null, frecuencia: s.frecuencia, dia_vencimiento: null, intervalo_dias: s.intervalo_dias ?? null, activo: true }
}
const editar = (c: ConceptoGasto) => { form.value = { ...c } }

async function guardar() {
  if (!form.value) return
  guardando.value = true
  const { id, ...body } = form.value
  if (body.frecuencia === 'eventual') body.monto_tipico = null
  if (body.frecuencia !== 'mensual') body.dia_vencimiento = null
  if (body.frecuencia !== 'cada_n_dias') body.intervalo_dias = null
  if (!body.monto_tipico) body.monto_tipico = null
  try {
    if (id) await api.put(`/gastos/conceptos/${id}`, body)
    else await api.post('/gastos/conceptos', body)
    form.value = null
    window.dispatchEvent(new Event('catalogos-gastos-cambiados'))
    await cargar()
  } catch (e: any) {
    error.value = e?.response?.status === 409 ? 'Ya existe uno con ese nombre' : 'No se pudo guardar'
  } finally {
    guardando.value = false
  }
}

onMounted(cargar)
defineExpose({ cargar })
</script>
