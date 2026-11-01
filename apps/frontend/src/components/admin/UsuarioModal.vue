<template>
  <div class="fixed inset-0 z-[150] flex items-end sm:items-center justify-center bg-slate-900/50 backdrop-blur-sm p-0 sm:p-4" @click.self="$emit('close')">
    <form @submit.prevent="guardar" class="bg-white w-full sm:max-w-xl max-h-[95vh] sm:max-h-[90vh] flex flex-col rounded-t-3xl sm:rounded-3xl shadow-2xl overflow-hidden" role="dialog" aria-modal="true">
      <!-- Cabecera -->
      <header class="flex items-center gap-4 px-6 py-5 border-b border-slate-100">
        <div class="h-12 w-12 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 text-white flex items-center justify-center text-lg font-black shrink-0">
          {{ (form.nombre || '?').charAt(0).toUpperCase() }}
        </div>
        <div class="min-w-0 flex-1">
          <h3 class="text-lg font-black text-slate-900 truncate">{{ usuario ? form.nombre || 'Editar usuario' : 'Nuevo usuario' }}</h3>
          <p class="text-xs font-bold text-slate-400 uppercase tracking-widest">{{ usuario ? `ID #${usuario.id}` : 'Acceso, pago y horario' }}</p>
        </div>
        <button type="button" @click="$emit('close')" class="h-10 w-10 rounded-full text-slate-400 hover:bg-slate-100 hover:text-slate-700 flex items-center justify-center" aria-label="Cerrar">✕</button>
      </header>

      <!-- Pestañas -->
      <nav v-if="esEmpleado" class="flex gap-1 px-6 pt-3 border-b border-slate-100" role="tablist">
        <button v-for="t in tabs" :key="t.id" type="button" role="tab" :aria-selected="tab === t.id" @click="tab = t.id" class="px-4 py-2 text-sm font-black border-b-2 -mb-px transition-colors" :class="tab === t.id ? 'border-[#00126D] text-[#00126D]' : 'border-transparent text-slate-400 hover:text-slate-600'">
          {{ t.label }}
        </button>
      </nav>

      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-5">
        <!-- Datos -->
        <section v-show="tab === 'datos' || !esEmpleado" class="space-y-5">
          <label class="block space-y-1.5">
            <span :class="etiqueta">Nombre</span>
            <input v-model="form.nombre" required maxlength="100" autocomplete="off" :class="campo">
          </label>
          <label class="block space-y-1.5">
            <span :class="etiqueta">PIN</span>
            <input v-model="form.pin" inputmode="numeric" autocomplete="off" maxlength="8" :required="!usuario" :class="campo" :placeholder="usuario ? 'Vacío = conservar el PIN actual' : 'De 4 a 8 dígitos'">
          </label>
          <div class="space-y-1.5">
            <span :class="etiqueta">Rol</span>
            <div class="flex flex-wrap gap-2">
              <button v-for="r in roles" :key="r.id" type="button" @click="form.rol = r.id" class="min-h-11 px-4 rounded-xl text-sm font-black border transition-all" :class="form.rol === r.id ? 'bg-[#00126D] border-[#00126D] text-white' : 'bg-white border-slate-200 text-slate-600 hover:border-slate-300'">
                {{ r.label }}
              </button>
            </div>
          </div>
          <label class="flex items-center justify-between gap-3 rounded-2xl border border-slate-200 px-4 py-3 cursor-pointer">
            <span>
              <span class="block text-sm font-black text-slate-800">{{ form.activo ? 'Activo' : 'Suspendido' }}</span>
              <span class="block text-xs font-medium text-slate-400">Un usuario suspendido no puede entrar ni checar.</span>
            </span>
            <input v-model="form.activo" type="checkbox" role="switch" class="peer sr-only">
            <span class="relative h-7 w-12 shrink-0 rounded-full bg-slate-300 transition-colors peer-checked:bg-emerald-500 after:absolute after:top-0.5 after:left-0.5 after:h-6 after:w-6 after:rounded-full after:bg-white after:shadow after:transition-transform peer-checked:after:translate-x-5" aria-hidden="true"></span>
          </label>
          <label v-if="!usuario" class="block space-y-1.5">
            <span :class="etiqueta">Sucursal (ID)</span>
            <input v-model.number="form.sucursal_id" type="number" min="1" required :class="campo">
          </label>
        </section>

        <!-- Pago -->
        <section v-if="esEmpleado" v-show="tab === 'pago'" class="space-y-4">
          <p class="text-sm font-medium text-slate-500">Con esto se calcula su nómina a partir de las horas que checa. Déjalo vacío si todavía no quieres pagarle por el sistema.</p>
          <div class="grid grid-cols-2 gap-3">
            <label class="block space-y-1.5">
              <span :class="etiqueta">Por hora ($)</span>
              <input v-model.number="pago.tarifa_hora" type="number" min="0.01" step="0.01" inputmode="decimal" :class="campo">
            </label>
            <label class="block space-y-1.5">
              <span :class="etiqueta">Por hora extra ($)</span>
              <input v-model.number="pago.tarifa_hora_extra" type="number" min="0.01" step="0.01" inputmode="decimal" :class="campo">
            </label>
          </div>
          <label class="block space-y-1.5">
            <span :class="etiqueta">Cuenta como extra después de (horas por día)</span>
            <input v-model.number="pago.horas_jornada" type="number" min="1" max="16" step="0.5" inputmode="decimal" :class="campo">
          </label>
          <p v-if="pago.tarifa_hora && pago.horas_jornada" class="rounded-2xl bg-slate-50 px-4 py-3 text-sm font-bold text-slate-600">
            Un día de {{ pago.horas_jornada }} h = {{ dinero(pago.tarifa_hora * pago.horas_jornada) }}
            <template v-if="pago.tarifa_hora_extra"> · cada hora extra {{ dinero(pago.tarifa_hora_extra) }}</template>
          </p>
        </section>

        <!-- Horario -->
        <section v-if="esEmpleado" v-show="tab === 'horario'" class="space-y-3">
          <div class="flex items-start justify-between gap-3">
            <p class="text-sm font-medium text-slate-500">Marca los días que trabaja. Su último día de la semana es cuando se le paga.</p>
            <button type="button" @click="copiarATodos" class="shrink-0 min-h-10 px-3 rounded-xl bg-slate-100 text-xs font-black text-slate-600 hover:bg-slate-200">Copiar el primero a todos</button>
          </div>
          <div v-for="d in dias" :key="d.id" class="flex items-center gap-2 rounded-2xl border px-3 py-2 transition-colors" :class="horario[d.id].trabaja ? 'border-slate-200 bg-white' : 'border-transparent bg-slate-50'">
            <label class="flex items-center gap-2 w-20 min-h-10 text-sm font-black text-slate-700 cursor-pointer">
              <input type="checkbox" v-model="horario[d.id].trabaja" class="h-5 w-5 accent-[#00126D]"> {{ d.corto }}
            </label>
            <template v-if="horario[d.id].trabaja">
              <input v-model="horario[d.id].entrada" type="time" required :class="`${campo} flex-1`" :aria-label="`Entrada ${d.corto}`">
              <span class="text-slate-400">–</span>
              <input v-model="horario[d.id].salida" type="time" required :class="`${campo} flex-1`" :aria-label="`Salida ${d.corto}`">
            </template>
            <span v-else class="text-xs font-bold text-slate-400">Descanso</span>
          </div>
          <p class="text-xs font-bold text-slate-400">{{ resumenHorario }}</p>
        </section>

        <p v-if="error" role="alert" class="rounded-xl bg-rose-50 border border-rose-200 px-3 py-2 text-sm font-bold text-rose-700">{{ error }}</p>
      </div>

      <footer class="flex justify-end gap-3 px-6 py-4 border-t border-slate-100 bg-slate-50/60">
        <button type="button" @click="$emit('close')" class="min-h-11 px-5 rounded-xl bg-white border border-slate-200 text-sm font-black text-slate-600 hover:bg-slate-100">Cancelar</button>
        <button type="submit" :disabled="guardando" class="min-h-11 px-6 rounded-xl bg-[#00126D] text-sm font-black text-white hover:bg-[#001a8f] disabled:opacity-40">
          {{ guardando ? 'Guardando…' : usuario ? 'Guardar cambios' : 'Crear usuario' }}
        </button>
      </footer>
    </form>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { api } from '@/api/client'

interface Props { usuario: any | null }
const props = defineProps<Props>()
const emit = defineEmits<{
  close: []
  save: [payload: { data: Record<string, any>; pago: any | null; horario: any[] | null }]
}>()

const etiqueta = 'text-[11px] font-black text-slate-400 uppercase tracking-widest'
const campo = 'w-full border border-slate-200 rounded-xl px-3 py-2.5 text-base font-bold bg-white min-h-11 focus:outline-none focus:ring-2 focus:ring-[#00126D]/20 focus:border-[#00126D]'
const roles = [
  { id: 'mesero', label: 'Mesero' },
  { id: 'cajero', label: 'Cajero' },
  { id: 'cocina', label: 'Cocina' },
  { id: 'compras', label: 'Compras' },
  { id: 'administrador', label: 'Administrador' },
]
// dia_semana: 0 = lunes. La semana operativa va de martes a lunes.
const dias = [
  { id: 1, corto: 'Mar' }, { id: 2, corto: 'Mié' }, { id: 3, corto: 'Jue' }, { id: 4, corto: 'Vie' },
  { id: 5, corto: 'Sáb' }, { id: 6, corto: 'Dom' }, { id: 0, corto: 'Lun' },
]

const form = reactive({
  nombre: props.usuario?.nombre ?? '',
  pin: '',
  rol: props.usuario?.rol ?? 'mesero',
  sucursal_id: props.usuario?.sucursal_id ?? 1,
  activo: props.usuario?.activo ?? true,
})
const pago = reactive<{ tarifa_hora: number | null; tarifa_hora_extra: number | null; horas_jornada: number }>({
  tarifa_hora: null, tarifa_hora_extra: null, horas_jornada: 8,
})
const horario = reactive<Record<number, { trabaja: boolean; entrada: string; salida: string }>>({})
for (const d of dias) horario[d.id] = { trabaja: false, entrada: '08:00', salida: '16:00' }

const tab = ref<'datos' | 'pago' | 'horario'>('datos')
const guardando = ref(false)
const error = ref('')
const horarioCargado = ref(false)

const esEmpleado = computed(() => form.rol !== 'administrador')
const tabs = [
  { id: 'datos' as const, label: 'Datos' },
  { id: 'pago' as const, label: 'Pago' },
  { id: 'horario' as const, label: 'Horario' },
]
const dinero = (v: number) => v.toLocaleString('es-MX', { style: 'currency', currency: 'MXN' })
const hhmm = (t: string) => t.slice(0, 5)

function horasDelDia(entrada: string, salida: string) {
  const [he, me] = entrada.split(':').map(Number)
  const [hs, ms] = salida.split(':').map(Number)
  let min = hs * 60 + ms - (he * 60 + me)
  if (min <= 0) min += 24 * 60 // la salida cae al día siguiente
  return min / 60
}
const resumenHorario = computed(() => {
  const activos = dias.filter((d) => horario[d.id].trabaja)
  const horas = activos.reduce((s, d) => s + horasDelDia(horario[d.id].entrada, horario[d.id].salida), 0)
  return activos.length ? `${activos.length} días · ${horas.toFixed(1)} h por semana` : 'Sin días de trabajo marcados'
})
function copiarATodos() {
  const origen = dias.map((d) => horario[d.id]).find((h) => h.trabaja)
  if (!origen) return
  for (const d of dias) {
    if (horario[d.id].trabaja) Object.assign(horario[d.id], { entrada: origen.entrada, salida: origen.salida })
  }
}

async function cargarEmpleado() {
  if (!props.usuario) return
  try {
    const empleados: any[] = (await api.get('/nomina/empleados')).data
    const e = empleados.find((x) => x.usuario_id === props.usuario.id)
    if (!e) return
    if (e.pago) {
      Object.assign(pago, {
        tarifa_hora: Number(e.pago.tarifa_hora),
        tarifa_hora_extra: Number(e.pago.tarifa_hora_extra),
        horas_jornada: Number(e.pago.horas_jornada),
      })
    }
    for (const d of dias) {
      const h = e.horario.find((x: any) => x.dia_semana === d.id)
      if (h) horario[d.id] = { trabaja: true, entrada: hhmm(h.hora_entrada), salida: hhmm(h.hora_salida) }
    }
    horarioCargado.value = true
  } catch {
    // Sin permiso o sin red: pago y horario quedan vacíos y no se envían.
  }
}

function guardar() {
  error.value = ''
  const data: Record<string, any> = {}
  const u = props.usuario
  if (!u || form.nombre !== u.nombre) data.nombre = form.nombre.trim()
  if (!u || form.rol !== u.rol) data.rol = form.rol
  if (!u || form.activo !== u.activo) data.activo = form.activo
  if (!u || form.sucursal_id !== u.sucursal_id) data.sucursal_id = form.sucursal_id
  if (form.pin.trim()) data.pin = form.pin.trim()

  let pagoPayload = null
  let horarioPayload = null
  if (esEmpleado.value) {
    if (!!pago.tarifa_hora !== !!pago.tarifa_hora_extra) {
      tab.value = 'pago'
      error.value = 'Indica el pago por hora y por hora extra, o deja los dos vacíos'
      return
    }
    if (pago.tarifa_hora && pago.tarifa_hora_extra) pagoPayload = { ...pago }
    // Solo se manda el horario si se pudo cargar o si el admin marcó algo: así no se borra por accidente.
    const activos = dias.filter((d) => horario[d.id].trabaja)
    if (horarioCargado.value || activos.length) {
      horarioPayload = activos.map((d) => ({ dia_semana: d.id, hora_entrada: horario[d.id].entrada, hora_salida: horario[d.id].salida }))
    }
  }
  guardando.value = true
  emit('save', { data, pago: pagoPayload, horario: horarioPayload })
}

defineExpose({ fallo(msg: string) { guardando.value = false; error.value = msg } })
onMounted(cargarEmpleado)
</script>
