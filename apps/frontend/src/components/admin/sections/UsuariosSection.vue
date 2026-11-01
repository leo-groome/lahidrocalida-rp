<template>
  <div class="space-y-6">
    <header class="flex flex-wrap items-center justify-between gap-4">
      <div>
        <h2 class="text-2xl font-black text-slate-900 tracking-tight">Usuarios</h2>
        <p class="text-sm font-medium text-slate-500">{{ filtrados.length }} de {{ usuarios.length }} · accesos, pago y horario del equipo</p>
      </div>
      <button @click="$emit('new-user')" class="inline-flex items-center gap-2 min-h-11 px-5 bg-emerald-600 text-white rounded-2xl text-sm font-black shadow-lg shadow-emerald-200 hover:bg-emerald-700 active:scale-95 transition-all">
        <UserPlus class="h-4 w-4" /> Nuevo usuario
      </button>
    </header>

    <!-- Filtros -->
    <div class="bg-white rounded-2xl border border-slate-100 p-3 space-y-3">
      <div class="flex flex-wrap items-center gap-3">
        <label class="relative flex-1 min-w-52">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input v-model="busqueda" type="search" placeholder="Buscar por nombre…" aria-label="Buscar usuario" class="w-full min-h-11 pl-10 pr-3 rounded-xl border border-slate-200 text-sm font-bold focus:outline-none focus:ring-2 focus:ring-[#00126D]/20 focus:border-[#00126D]">
        </label>
        <label class="flex items-center gap-2 text-xs font-black text-slate-400 uppercase tracking-widest">
          Orden
          <select v-model="orden" class="min-h-11 rounded-xl border border-slate-200 bg-white px-3 text-sm font-bold normal-case tracking-normal text-slate-700">
            <option value="nombre">Nombre (A-Z)</option>
            <option value="rol">Rol</option>
            <option value="tarifa">Pago por hora (mayor)</option>
            <option value="reciente">Más recientes</option>
          </select>
        </label>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <button v-for="r in filtrosRol" :key="r.id" type="button" @click="rol = r.id" class="min-h-10 px-3 rounded-xl text-xs font-black transition-colors" :class="rol === r.id ? 'bg-[#00126D] text-white' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'">
          {{ r.label }} <span class="opacity-60">{{ cuenta(r.id) }}</span>
        </button>
        <span class="mx-1 h-5 w-px bg-slate-200" aria-hidden="true"></span>
        <button v-for="e in filtrosEstado" :key="e.id" type="button" @click="estado = e.id" class="min-h-10 px-3 rounded-xl text-xs font-black transition-colors" :class="estado === e.id ? 'bg-slate-800 text-white' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'">
          {{ e.label }}
        </button>
        <label v-if="hayEmpleadosSinTarifa" class="ml-auto inline-flex items-center gap-2 min-h-10 px-3 text-xs font-black text-amber-700 cursor-pointer">
          <input v-model="soloSinTarifa" type="checkbox" class="h-4 w-4"> Solo sin tarifa de pago
        </label>
      </div>
    </div>

    <!-- Lista -->
    <div v-if="!filtrados.length" class="text-center py-16 bg-slate-50 rounded-2xl border-2 border-dashed border-slate-200">
      <p class="font-bold text-slate-400">{{ usuarios.length ? 'Ningún usuario coincide con los filtros' : 'Aún no hay usuarios' }}</p>
    </div>
    <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      <article v-for="u in filtrados" :key="u.id" class="bg-white rounded-2xl border border-slate-100 p-4 space-y-3 hover:border-slate-300 transition-colors" :class="{ 'opacity-60': !u.activo }">
        <div class="flex items-center gap-3">
          <div class="h-11 w-11 rounded-2xl bg-gradient-to-br from-blue-50 to-blue-100 text-blue-600 flex items-center justify-center text-base font-black shrink-0">
            {{ u.nombre.charAt(0).toUpperCase() }}
          </div>
          <div class="min-w-0 flex-1">
            <p class="font-black text-slate-800 truncate">{{ u.nombre }}</p>
            <p class="text-[10px] font-black uppercase tracking-widest text-slate-400">{{ u.rol }}<template v-if="!u.activo"> · suspendido</template></p>
          </div>
          <button @click="$emit('edit-user', u)" class="min-h-10 px-3 rounded-xl bg-slate-100 text-slate-600 text-xs font-black hover:bg-[#00126D] hover:text-white transition-colors inline-flex items-center gap-1.5" :aria-label="`Configurar ${u.nombre}`">
            <Settings class="h-3.5 w-3.5" /> Configurar
          </button>
        </div>
        <div v-if="u.rol !== 'administrador'" class="text-xs font-bold space-y-1">
          <p v-if="u.pago" class="text-slate-600 tabular-nums">${{ pesos(u.pago.tarifa_hora) }}/h · extra ${{ pesos(u.pago.tarifa_hora_extra) }}/h</p>
          <p v-else class="text-amber-600">Sin tarifa de pago</p>
          <p class="text-slate-400">{{ u.horario?.length ? `${u.horario.length} días · ${horasSemana(u)} h por semana` : 'Sin horario' }}</p>
        </div>
      </article>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Search, Settings, UserPlus } from 'lucide-vue-next'
import api from '@/api/client'

defineEmits(['new-user', 'edit-user'])

const usuarios = ref<any[]>([])
const busqueda = ref('')
const rol = ref('todos')
const estado = ref<'activos' | 'suspendidos' | 'todos'>('activos')
const orden = ref<'nombre' | 'rol' | 'tarifa' | 'reciente'>('nombre')
const soloSinTarifa = ref(false)

const filtrosRol = [
  { id: 'todos', label: 'Todos' },
  { id: 'mesero', label: 'Meseros' },
  { id: 'cajero', label: 'Caja' },
  { id: 'cocina', label: 'Cocina' },
  { id: 'compras', label: 'Compras' },
  { id: 'administrador', label: 'Admins' },
]
const filtrosEstado = [
  { id: 'activos' as const, label: 'Activos' },
  { id: 'suspendidos' as const, label: 'Suspendidos' },
  { id: 'todos' as const, label: 'Todos' },
]

const pesos = (v: number | string) => Number(v).toLocaleString('es-MX', { maximumFractionDigits: 2 })
const horasDelDia = (e: string, s: string) => {
  const [he, me] = e.split(':').map(Number)
  const [hs, ms] = s.split(':').map(Number)
  let min = hs * 60 + ms - (he * 60 + me)
  if (min <= 0) min += 24 * 60
  return min / 60
}
const horasSemana = (u: any) => u.horario.reduce((s: number, d: any) => s + horasDelDia(d.hora_entrada, d.hora_salida), 0).toFixed(1)

const normaliza = (t: string) => t.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
const porEstado = (u: any) => estado.value === 'todos' || (estado.value === 'activos') === !!u.activo
const cuenta = (id: string) => usuarios.value.filter((u) => porEstado(u) && (id === 'todos' || u.rol === id)).length
const hayEmpleadosSinTarifa = computed(() => usuarios.value.some((u) => u.rol !== 'administrador' && u.activo && !u.pago))

const filtrados = computed(() => {
  const q = normaliza(busqueda.value.trim())
  const lista = usuarios.value.filter(
    (u) =>
      porEstado(u) &&
      (rol.value === 'todos' || u.rol === rol.value) &&
      (!q || normaliza(u.nombre).includes(q)) &&
      (!soloSinTarifa.value || (u.rol !== 'administrador' && !u.pago)),
  )
  const por = {
    nombre: (a: any, b: any) => a.nombre.localeCompare(b.nombre, 'es'),
    rol: (a: any, b: any) => a.rol.localeCompare(b.rol) || a.nombre.localeCompare(b.nombre, 'es'),
    tarifa: (a: any, b: any) => Number(b.pago?.tarifa_hora ?? 0) - Number(a.pago?.tarifa_hora ?? 0),
    reciente: (a: any, b: any) => b.id - a.id,
  }[orden.value]
  return [...lista].sort(por)
})

const loadUsuarios = async () => {
  try {
    const lista: any[] = (await api.get('/usuarios/')).data
    let empleados: any[] = []
    try {
      empleados = (await api.get('/nomina/empleados')).data
    } catch {
      // Solo el administrador ve pagos y horarios.
    }
    const porId = new Map(empleados.map((e) => [e.usuario_id, e]))
    usuarios.value = lista.map((u) => ({ ...u, pago: porId.get(u.id)?.pago ?? null, horario: porId.get(u.id)?.horario ?? [] }))
  } catch (err) {
    console.error('Error cargando usuarios:', err)
  }
}

onMounted(loadUsuarios)
defineExpose({ loadUsuarios })
</script>
