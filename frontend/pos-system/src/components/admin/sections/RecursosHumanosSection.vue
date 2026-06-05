<template>
  <div class="p-6 space-y-6">
    <!-- Header + filtros -->
    <div class="flex flex-wrap items-start gap-4">
      <div>
        <h2 class="text-xl font-black text-slate-800">Recursos Humanos</h2>
        <p class="text-sm text-slate-500 mt-0.5">Horas trabajadas y registro de asistencia por empleado</p>
      </div>

      <div class="flex flex-wrap items-center gap-3 ml-auto">
        <!-- Quick range buttons -->
        <div class="flex items-center gap-1 bg-slate-100 rounded-xl p-1">
          <button
            v-for="range in quickRanges"
            :key="range.label"
            @click="applyRange(range)"
            class="px-3 py-1.5 text-xs font-bold rounded-lg transition-colors"
            :class="activeRange === range.label
              ? 'bg-white text-[#00126D] shadow-sm'
              : 'text-slate-500 hover:text-slate-700'"
          >
            {{ range.label }}
          </button>
        </div>

        <div class="flex items-center gap-2">
          <input
            v-model="fechaInicio"
            type="date"
            class="px-3 py-2 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#00126D]/20 focus:border-[#00126D]"
          />
          <span class="text-slate-400 text-sm">—</span>
          <input
            v-model="fechaFin"
            type="date"
            class="px-3 py-2 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#00126D]/20 focus:border-[#00126D]"
          />
        </div>

        <button
          @click="loadResumen"
          class="px-4 py-2 bg-[#00126D] text-white text-sm font-bold rounded-xl hover:bg-[#001a8f] transition-colors"
        >
          Filtrar
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-16">
      <div class="w-8 h-8 border-4 border-slate-200 border-t-[#00126D] rounded-full animate-spin"/>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="p-4 bg-red-50 border border-red-200 rounded-2xl">
      <p class="text-red-600 text-sm font-medium">{{ error }}</p>
    </div>

    <!-- Empty -->
    <div v-else-if="!resumen || resumen.empleados.length === 0" class="text-center py-16 bg-slate-50 rounded-2xl border-2 border-dashed border-slate-200">
      <p class="text-slate-400 font-medium">No hay registros de asistencia en este período</p>
    </div>

    <!-- Content -->
    <div v-else class="space-y-4">
      <!-- Period info -->
      <div class="flex items-center gap-2 text-xs text-slate-500">
        <span class="font-semibold">Período:</span>
        <span>{{ formatDate(resumen.fecha_inicio) }} — {{ formatDate(resumen.fecha_fin) }}</span>
        <span class="ml-auto">{{ resumen.empleados.length }} empleado{{ resumen.empleados.length !== 1 ? 's' : '' }}</span>
      </div>

      <!-- Employee cards -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div
          v-for="emp in sortedEmpleados"
          :key="emp.usuario_id"
          class="bg-white border border-slate-100 rounded-2xl p-5 shadow-sm hover:shadow-md transition-shadow"
        >
          <div class="flex items-center gap-4 mb-4">
            <!-- Avatar -->
            <div
              class="w-12 h-12 rounded-full flex items-center justify-center text-base font-black text-white flex-shrink-0"
              :class="getColor(emp.usuario_nombre)"
            >
              {{ getInitials(emp.usuario_nombre) }}
            </div>
            <div class="flex-1 min-w-0">
              <p class="font-bold text-slate-800 truncate">{{ emp.usuario_nombre }}</p>
              <span class="inline-block text-xs font-bold px-2 py-0.5 rounded-lg bg-slate-100 text-slate-600 capitalize mt-0.5">
                {{ emp.rol }}
              </span>
            </div>
            <!-- Hours big -->
            <div class="text-right">
              <p class="text-3xl font-black text-[#00126D]">{{ emp.horas_totales.toFixed(1) }}</p>
              <p class="text-xs font-semibold text-slate-400 uppercase tracking-wide">hrs</p>
            </div>
          </div>

          <div class="grid grid-cols-3 gap-2 text-center">
            <div class="bg-slate-50 rounded-xl py-2">
              <p class="text-sm font-black text-slate-700">{{ emp.total_registros }}</p>
              <p class="text-[10px] font-semibold text-slate-400 uppercase tracking-wide">Registros</p>
            </div>
            <div class="bg-slate-50 rounded-xl py-2">
              <p class="text-sm font-black text-slate-700">{{ emp.ultima_entrada ? formatTime(emp.ultima_entrada) : '—' }}</p>
              <p class="text-[10px] font-semibold text-slate-400 uppercase tracking-wide">Últ. Entrada</p>
            </div>
            <div class="bg-slate-50 rounded-xl py-2">
              <p class="text-sm font-black text-slate-700">{{ emp.ultima_salida ? formatTime(emp.ultima_salida) : '—' }}</p>
              <p class="text-[10px] font-semibold text-slate-400 uppercase tracking-wide">Últ. Salida</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onActivated } from 'vue'
import { api } from '@/api/client'

interface AsistenciaEmpleado {
  usuario_id: number
  usuario_nombre: string
  rol: string
  total_registros: number
  horas_totales: number
  ultima_entrada: string | null
  ultima_salida: string | null
}

interface AsistenciaResumen {
  fecha_inicio: string
  fecha_fin: string
  empleados: AsistenciaEmpleado[]
}

const COLORS = [
  'bg-blue-500', 'bg-emerald-500', 'bg-violet-500',
  'bg-amber-500', 'bg-rose-500', 'bg-cyan-500',
]

function getInitials(nombre: string): string {
  return nombre.trim().split(/\s+/).slice(0, 2).map(w => w[0]).join('').toUpperCase()
}

function getColor(nombre: string): string {
  const hash = nombre.split('').reduce((a, c) => a + c.charCodeAt(0), 0)
  return COLORS[hash % COLORS.length]
}

function formatDate(iso: string): string {
  return new Date(iso + 'T00:00:00').toLocaleDateString('es-MX', { day: 'numeric', month: 'short', year: 'numeric' })
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' })
}

function getDateStr(daysAgo: number): string {
  const d = new Date()
  d.setDate(d.getDate() - daysAgo)
  return d.toISOString().split('T')[0]
}

function getMondayStr(): string {
  const d = new Date()
  const day = d.getDay()
  const diff = d.getDate() - day + (day === 0 ? -6 : 1)
  d.setDate(diff)
  return d.toISOString().split('T')[0]
}

function getFirstOfMonth(): string {
  const d = new Date()
  d.setDate(1)
  return d.toISOString().split('T')[0]
}

const quickRanges = [
  { label: 'Esta semana', getInicio: getMondayStr, getFin: () => getDateStr(0) },
  { label: 'Semana pasada', getInicio: () => getDateStr(13), getFin: () => getDateStr(7) },
  { label: 'Este mes', getInicio: getFirstOfMonth, getFin: () => getDateStr(0) },
]

const fechaInicio = ref(getMondayStr())
const fechaFin = ref(getDateStr(0))
const activeRange = ref('Esta semana')
const resumen = ref<AsistenciaResumen | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

const sortedEmpleados = computed(() =>
  [...(resumen.value?.empleados ?? [])].sort((a, b) => b.horas_totales - a.horas_totales)
)

function applyRange(range: typeof quickRanges[0]) {
  fechaInicio.value = range.getInicio()
  fechaFin.value = range.getFin()
  activeRange.value = range.label
  loadResumen()
}

async function loadResumen() {
  loading.value = true
  error.value = null
  try {
    const { data } = await api.get('/asistencia/resumen', {
      params: { fecha_inicio: fechaInicio.value, fecha_fin: fechaFin.value },
    })
    resumen.value = data
  } catch (e: any) {
    error.value = e?.response?.data?.detail || 'Error al cargar datos de asistencia'
  } finally {
    loading.value = false
  }
}

onMounted(loadResumen)
onActivated(loadResumen)
</script>
