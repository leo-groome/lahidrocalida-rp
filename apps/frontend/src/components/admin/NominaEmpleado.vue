<template>
  <div class="space-y-4">
    <!-- Semana -->
    <div class="flex flex-wrap items-center gap-2">
      <div class="flex items-center gap-1 bg-slate-100 rounded-xl p-1">
        <button type="button" @click="cambiarSemana(-1)" class="min-h-10 px-3 rounded-lg text-sm font-black text-slate-600 hover:bg-white" aria-label="Semana anterior">‹</button>
        <span class="px-2 text-sm font-black text-slate-800 tabular-nums">{{ etiquetaSemana }}</span>
        <button type="button" @click="cambiarSemana(1)" :disabled="offset >= 0" class="min-h-10 px-3 rounded-lg text-sm font-black text-slate-600 hover:bg-white disabled:opacity-30" aria-label="Semana siguiente">›</button>
      </div>
      <span v-if="ln?.pagada" class="px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest bg-emerald-100 text-emerald-700">Pagado</span>
      <button v-else-if="ln" type="button" @click="recalcular" :disabled="trabajando" class="ml-auto min-h-10 px-3 rounded-xl bg-slate-100 text-xs font-black text-slate-600 disabled:opacity-40">
        Restablecer horas
      </button>
    </div>

    <p v-if="error" role="alert" class="text-sm font-bold text-rose-600">{{ error }}</p>
    <p v-if="cargando" class="text-sm font-bold text-slate-400">Calculando…</p>
    <p v-else-if="periodo && !ln" class="rounded-2xl bg-slate-50 border border-dashed border-slate-200 p-4 text-sm font-bold text-slate-500">
      Esta persona no tiene tarifa de pago. Configúrala en Usuarios → Configurar → Pago.
    </p>

    <template v-if="ln">
      <!-- Días y horas -->
      <div class="border border-slate-100 rounded-2xl overflow-hidden bg-white">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-slate-50 border-b border-slate-100">
              <th class="px-4 py-2 text-xs font-bold text-slate-500 uppercase tracking-wide">Día</th>
              <th class="px-4 py-2 text-xs font-bold text-slate-500 uppercase tracking-wide">Entrada</th>
              <th class="px-4 py-2 text-xs font-bold text-slate-500 uppercase tracking-wide">Salida</th>
              <th class="px-4 py-2 text-xs font-bold text-slate-500 uppercase tracking-wide text-right">Horas</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-50">
            <tr v-for="(d, i) in ln.dias" :key="i">
              <td class="px-4 py-2 text-sm font-bold text-slate-700 capitalize">{{ dia(d.fecha) }}</td>
              <td class="px-4 py-2 text-sm text-slate-600 font-medium">{{ hora(d.entrada) }}</td>
              <td class="px-4 py-2 text-sm text-slate-600 font-medium">
                <template v-if="d.salida">{{ hora(d.salida) }}</template>
                <span v-else class="text-amber-700 font-bold">En turno</span>
                <span v-if="d.automatica" class="ml-1 px-1.5 py-0.5 rounded-md text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200" title="No checó salida: el sistema la cerró a las 00:30">Automática</span>
              </td>
              <td class="px-4 py-2 text-sm font-black text-[#00126D] text-right tabular-nums">{{ d.abierta ? '—' : n(d.horas) }}</td>
            </tr>
            <tr v-if="!ln.dias.length"><td colspan="4" class="px-4 py-6 text-center text-sm font-bold text-slate-400">Sin checadas esta semana</td></tr>
          </tbody>
        </table>
      </div>

      <p v-if="ln.salidas_automaticas > 0" class="rounded-xl bg-amber-50 border border-amber-200 px-3 py-2 text-xs font-bold text-amber-800" role="alert">
        ⚠ {{ ln.salidas_automaticas }} salida(s) la cerró el sistema a las 00:30 porque no checó. Las horas pueden venir infladas: corrígelas abajo.
      </p>

      <!-- Cálculo -->
      <div class="rounded-2xl bg-[#00126D]/5 border border-[#00126D]/10 p-4 space-y-1">
        <div class="flex items-baseline justify-between">
          <span class="text-xs font-black text-slate-400 uppercase tracking-widest">A pagar</span>
          <span class="text-3xl font-black text-slate-900 tabular-nums" data-testid="total-linea">{{ dinero(ln.total) }}</span>
        </div>
        <p class="text-xs font-bold text-slate-500 tabular-nums">
          {{ n(ln.horas_trabajadas) }} h · {{ ln.dias_trabajados }} de {{ ln.dias_esperados }} días
          <span v-if="ln.faltas > 0" class="text-rose-600">({{ ln.faltas }} falta(s))</span><br>
          Horas normales {{ dinero(ln.base) }} · Extras {{ dinero(ln.extra_monto) }} ({{ n(ln.horas_extra) }} h)
          <template v-if="Number(ln.bonos)"> · Bonos {{ dinero(ln.bonos) }}</template>
          <template v-if="Number(ln.descuentos)"> · Descuentos −{{ dinero(ln.descuentos) }}</template>
        </p>
      </div>
      <p v-if="!ln.pagada && Number(ln.total) === 0 && ln.dias_trabajados > 0" class="rounded-xl bg-rose-50 border border-rose-200 px-3 py-2 text-xs font-bold text-rose-700" role="alert">
        ⚠ Total en $0 con días trabajados: no se le pagará nada. Revisa los descuentos.
      </p>

      <!-- Ajustes manuales -->
      <section class="rounded-2xl border border-slate-200 p-4 space-y-3" aria-labelledby="ajustes-titulo">
        <div>
          <h4 id="ajustes-titulo" class="text-sm font-black text-slate-800">Ajustes manuales</h4>
          <p class="text-xs font-medium text-slate-500">
            {{ ln.pagada ? 'Esta semana ya se pagó: no se puede modificar.' : 'Corrige horas, suma bonos o resta descuentos. El total se recalcula al momento.' }}
          </p>
        </div>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <label v-for="c in campos" :key="c.key" class="block space-y-1">
            <span :class="etiqueta">{{ c.label }}</span>
            <input :value="n(ln[c.key])" :disabled="ln.pagada" @change="editar({ [c.key]: num($event) })" type="number" min="0" :step="c.step" inputmode="decimal" :class="[campo, 'disabled:bg-slate-50 disabled:text-slate-400']" :aria-label="c.label">
          </label>
        </div>
        <label class="block space-y-1">
          <span :class="etiqueta">Motivo del ajuste</span>
          <input :value="ln.notas ?? ''" :disabled="ln.pagada" @change="editar({ notas: ($event.target as HTMLInputElement).value })" maxlength="255" placeholder="Ej. bono por doble turno, descuento por préstamo…" :class="[campo, 'disabled:bg-slate-50 disabled:text-slate-400']" aria-label="Motivo del ajuste">
        </label>
      </section>

      <!-- Pago -->
      <div v-if="!ln.pagada" class="space-y-3">
        <div class="flex flex-wrap items-center gap-2">
          <div class="inline-flex rounded-xl bg-slate-100 p-1">
            <button v-for="m in metodos" :key="m.id" type="button" @click="editar({ metodo_pago: m.id })" class="min-h-10 px-3 rounded-lg text-sm font-black transition-all" :class="ln.metodo_pago === m.id ? 'bg-[#00126D] text-white' : 'text-slate-500'">
              {{ m.label }}
            </button>
          </div>
          <label v-if="ln.metodo_pago === 'efectivo'" class="inline-flex items-center gap-2 min-h-10 px-2 text-sm font-bold text-slate-600">
            <input type="checkbox" :checked="ln.sale_de_caja" @change="editar({ sale_de_caja: ($event.target as HTMLInputElement).checked })" class="h-5 w-5"> Sale de la caja
          </label>
        </div>
        <button type="button" @click="pagar" :disabled="trabajando || !!ln.bloqueo || Number(ln.total) <= 0" class="w-full min-h-12 bg-[#00126D] text-white font-black rounded-xl disabled:opacity-40 active:scale-[0.99]" data-testid="pagar-empleado">
          {{ trabajando ? 'Procesando…' : `Pagar nómina · ${dinero(ln.total)}` }}
        </button>
        <p v-if="ln.bloqueo" class="text-xs font-bold text-amber-700">{{ ln.bloqueo }}</p>
      </div>
      <p v-else class="text-sm font-black text-emerald-700">
        ✓ Pagado · {{ ln.metodo_pago === 'efectivo' ? (ln.sale_de_caja ? 'Efectivo de caja' : 'Efectivo') : 'Tarjeta / transferencia' }}. Quedó en Egresos como nómina.
      </p>
    </template>

    <NipKeypad
      v-if="pin.isOpen.value"
      :titulo="pin.titulo"
      :mensaje="pin.mensaje"
      :error="pin.error.value"
      :cooldown-seconds="pin.cooldownSeconds.value"
      @confirm="pin.onConfirm"
      @cancel="pin.onCancel"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '@/api/client'
import { useAdminPin } from '@/composables/useAdminPin'
import NipKeypad from '@/components/NipKeypad.vue'
import { rangoSemana, sumarDias } from '@/utils/fecha'

interface DiaNomina { fecha: string; entrada: string; salida: string | null; horas: string; automatica: boolean; abierta: boolean }
interface Linea {
  usuario_id: number; nombre: string
  dias_esperados: number; dias_trabajados: number; faltas: number
  horas_trabajadas: string; horas_extra: string
  base: string; extra_monto: string; bonos: string; descuentos: string; total: string
  metodo_pago: 'efectivo' | 'tarjeta'; sale_de_caja: boolean; notas: string | null; pagada: boolean
  salidas_automaticas: number; ultimo_dia: string; bloqueo: string | null; dias: DiaNomina[]
}
interface Periodo { id: number; estado: 'borrador' | 'pagada'; lineas: Linea[] }

const props = defineProps<{ usuarioId: number }>()

const etiqueta = 'text-[10px] font-black text-slate-400 uppercase tracking-widest'
const campo = 'w-full border border-slate-200 rounded-xl px-3 py-2 text-base font-bold bg-white min-h-10'
const metodos = [
  { id: 'efectivo' as const, label: '💵 Efectivo' },
  { id: 'tarjeta' as const, label: '💳 Tarjeta / transf.' },
]
const campos = [
  { key: 'horas_trabajadas' as const, label: 'Horas', step: 0.25 },
  { key: 'horas_extra' as const, label: 'Horas extra', step: 0.25 },
  { key: 'bonos' as const, label: 'Bonos ($)', step: 0.01 },
  { key: 'descuentos' as const, label: 'Descuentos ($)', step: 0.01 },
]

const offset = ref(0)
const periodo = ref<Periodo | null>(null)
const cargando = ref(false)
const trabajando = ref(false)
const error = ref('')
const pin = useAdminPin('Pagar nómina', 'Ingresa el PIN de un administrador para registrar el pago')

const ln = computed(() => periodo.value?.lineas.find((l) => l.usuario_id === props.usuarioId) ?? null)
const inicio = computed(() => rangoSemana(Date.now(), offset.value).inicio)
const etiquetaSemana = computed(() => {
  const fmt = (iso: string) => new Date(`${iso}T12:00:00Z`).toLocaleDateString('es-MX', { day: 'numeric', month: 'short', timeZone: 'UTC' })
  return `${fmt(inicio.value)} – ${fmt(sumarDias(inicio.value, 6))}`
})

const n = (v: string | number) => String(Number(v))
const num = (e: Event) => Number((e.target as HTMLInputElement).value || 0)
const dinero = (v: string | number) => Number(v).toLocaleString('es-MX', { style: 'currency', currency: 'MXN' })
const dia = (iso: string) => new Date(`${iso}T12:00:00Z`).toLocaleDateString('es-MX', { weekday: 'long', day: 'numeric', month: 'short', timeZone: 'UTC' })
const hora = (iso: string) => new Date(iso).toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit', timeZone: 'America/Mexico_City' })
const mensaje = (e: any, defecto: string) => {
  const d = e?.response?.data?.detail
  return typeof d === 'string' ? d : defecto
}

async function abrir() {
  cargando.value = true
  error.value = ''
  try {
    periodo.value = (await api.post('/nomina/periodos', { fecha_inicio: inicio.value })).data
  } catch (e) {
    periodo.value = null
    error.value = mensaje(e, 'No se pudo calcular la nómina')
  } finally {
    cargando.value = false
  }
}
function cambiarSemana(d: number) {
  if (offset.value + d > 0) return
  offset.value += d
  void abrir()
}
async function recalcular() {
  if (!periodo.value) return
  trabajando.value = true
  try {
    periodo.value = (await api.post(`/nomina/periodos/${periodo.value.id}/recalcular`)).data
    error.value = ''
  } catch (e) {
    error.value = mensaje(e, 'No se pudo restablecer')
  } finally {
    trabajando.value = false
  }
}
async function editar(cambios: Record<string, unknown>) {
  if (!periodo.value) return
  try {
    periodo.value = (await api.put(`/nomina/periodos/${periodo.value.id}/lineas/${props.usuarioId}`, cambios)).data
    error.value = ''
  } catch (e) {
    error.value = mensaje(e, 'No se pudo guardar el cambio')
    await abrir()
  }
}
async function pagar() {
  if (!periodo.value) return
  const id = periodo.value.id
  trabajando.value = true
  try {
    periodo.value = await pin.requestPinVerificado(
      async (p) => (await api.post(`/nomina/periodos/${id}/pagar`, { pin_autorizacion: p, usuario_ids: [props.usuarioId] })).data,
    )
    error.value = ''
    window.dispatchEvent(new Event('catalogos-gastos-cambiados'))
  } catch (e) {
    error.value = mensaje(e, 'No se pudo pagar la nómina')
  } finally {
    trabajando.value = false
  }
}

onMounted(abrir)
</script>
