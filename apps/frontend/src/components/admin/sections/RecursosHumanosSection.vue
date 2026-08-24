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
      <!-- Period info and Role filter -->
      <div class="flex flex-wrap items-center justify-between gap-3 pt-2">
        <div class="flex items-center gap-1 bg-slate-100 rounded-xl p-1">
          <button
            v-for="roleFilter in ['todos', 'cocina', 'mesero']"
            :key="roleFilter"
            @click="currentRoleFilter = roleFilter"
            class="px-4 py-1.5 text-xs font-bold rounded-lg transition-colors capitalize"
            :class="currentRoleFilter === roleFilter
              ? 'bg-white text-[#00126D] shadow-sm'
              : 'text-slate-500 hover:text-slate-700'"
          >
            {{ roleFilter === 'todos' ? 'Todos' : roleFilter === 'mesero' ? 'Meseros' : 'Cocina' }}
          </button>
        </div>
        
        <div class="flex items-center gap-2 text-xs text-slate-500">
          <span class="font-semibold">Período:</span>
          <span>{{ formatDate(resumen.fecha_inicio) }} — {{ formatDate(resumen.fecha_fin) }}</span>
          <span class="ml-3 font-semibold">Total:</span>
          <span>{{ filteredEmpleados.length }} empleado{{ filteredEmpleados.length !== 1 ? 's' : '' }}</span>
        </div>
      </div>

      <!-- Employee cards -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div
          v-for="emp in filteredEmpleados"
          :key="emp.usuario_id"
          @click="openDetailModal(emp)"
          class="bg-white border border-slate-100 rounded-2xl p-5 shadow-sm hover:shadow-md transition-all cursor-pointer hover:border-[#00126D]/50"
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

    <!-- Modal Detalle Asistencia -->
    <div
      v-if="showDetailModal"
      class="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      @click.self="showDetailModal = false"
    >
      <div class="bg-white rounded-3xl shadow-xl w-full max-w-2xl max-h-[85vh] flex flex-col overflow-hidden">
        <!-- Header -->
        <div class="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
          <div class="flex items-center gap-3">
            <div
              class="w-10 h-10 rounded-full flex items-center justify-center text-sm font-black text-white"
              :class="getColor(selectedEmpleado?.usuario_nombre || '')"
            >
              {{ getInitials(selectedEmpleado?.usuario_nombre || '') }}
            </div>
            <div>
              <h3 class="font-bold text-slate-800 text-base leading-tight">
                {{ selectedEmpleado?.usuario_nombre }}
              </h3>
              <span class="inline-block text-[10px] font-bold px-2 py-0.5 rounded-lg bg-slate-100 text-slate-600 capitalize mt-1">
                {{ selectedEmpleado?.rol }}
              </span>
            </div>
          </div>
          <button
            @click="showDetailModal = false"
            class="p-2 hover:bg-slate-100 rounded-full transition-colors text-slate-400 hover:text-slate-600"
          >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-5 h-5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Content -->
        <div class="p-6 overflow-y-auto flex-1 space-y-4">
          <!-- Summary/Range Info -->
          <div class="flex flex-wrap items-center justify-between gap-2 bg-[#00126D]/5 rounded-2xl p-4 border border-[#00126D]/10">
            <div>
              <p class="text-xs font-semibold text-slate-400 uppercase tracking-wide">Rango del Reporte</p>
              <p class="text-xs font-bold text-slate-700 mt-0.5">
                {{ formatDate(fechaInicio) }} — {{ formatDate(fechaFin) }}
              </p>
            </div>
            <div class="text-right">
              <p class="text-xs font-semibold text-slate-400 uppercase tracking-wide">Horas Totales</p>
              <p class="text-lg font-black text-[#00126D]">
                {{ selectedEmpleado?.horas_totales.toFixed(1) }} hrs
              </p>
            </div>
          </div>

          <!-- Loading -->
          <div v-if="loadingRegistros" class="flex items-center justify-center py-12">
            <div class="w-8 h-8 border-4 border-slate-200 border-t-[#00126D] rounded-full animate-spin"/>
          </div>

          <!-- Error -->
          <div v-else-if="errorRegistros" class="p-4 bg-red-50 border border-red-200 rounded-2xl">
            <p class="text-red-600 text-sm font-medium">{{ errorRegistros }}</p>
          </div>

          <!-- Empty -->
          <div v-else-if="registrosEmpleado.length === 0" class="text-center py-12 bg-slate-50 rounded-2xl border border-dashed border-slate-200">
            <p class="text-slate-400 font-medium">No se encontraron marcas de entrada/salida para este período</p>
          </div>

          <!-- Table of logs -->
          <div v-else class="border border-slate-100 rounded-2xl overflow-hidden bg-white">
            <div class="overflow-x-auto">
              <table class="w-full text-left border-collapse">
                <thead>
                  <tr class="bg-slate-50 border-b border-slate-100">
                    <th class="px-4 py-3 text-xs font-bold text-slate-500 uppercase tracking-wide">Día / Fecha</th>
                    <th class="px-4 py-3 text-xs font-bold text-slate-500 uppercase tracking-wide">Entrada</th>
                    <th class="px-4 py-3 text-xs font-bold text-slate-500 uppercase tracking-wide">Salida</th>
                    <th class="px-4 py-3 text-xs font-bold text-slate-500 uppercase tracking-wide text-right">Horas</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-50">
                  <tr v-for="reg in registrosEmpleado" :key="reg.id" class="hover:bg-slate-50/50 transition-colors">
                    <td class="px-4 py-3 text-sm font-bold text-slate-700 capitalize">
                      {{ formatDetailedDate(reg.fecha_entrada) }}
                    </td>
                    <td class="px-4 py-3 text-sm text-slate-600 font-medium">
                      {{ formatTime(reg.fecha_entrada) }}
                    </td>
                    <td class="px-4 py-3 text-sm font-medium">
                      <span v-if="reg.fecha_salida" class="text-slate-600">
                        {{ formatTime(reg.fecha_salida) }}
                      </span>
                      <span v-else class="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
                        En Turno
                      </span>
                    </td>
                    <td class="px-4 py-3 text-sm font-black text-[#00126D] text-right">
                      {{ reg.horas_trabajadas !== null ? reg.horas_trabajadas.toFixed(2) : '—' }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="px-6 py-4 border-t border-slate-100 bg-slate-50/50 flex justify-end">
          <button
            @click="showDetailModal = false"
            class="px-4 py-2 border border-slate-200 hover:bg-slate-100 text-slate-600 text-sm font-bold rounded-xl transition-colors"
          >
            Cerrar
          </button>
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

const currentRoleFilter = ref('todos')
const fechaInicio = ref(getMondayStr())
const fechaFin = ref(getDateStr(0))
const activeRange = ref('Esta semana')
const resumen = ref<AsistenciaResumen | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

const sortedEmpleados = computed(() =>
  [...(resumen.value?.empleados ?? [])].sort((a, b) => b.horas_totales - a.horas_totales)
)

const filteredEmpleados = computed(() => {
  const emps = sortedEmpleados.value
  if (currentRoleFilter.value === 'todos') return emps
  return emps.filter(e => e.rol?.toLowerCase() === currentRoleFilter.value)
})

const selectedEmpleado = ref<AsistenciaEmpleado | null>(null)
const showDetailModal = ref(false)
const registrosEmpleado = ref<any[]>([])
const loadingRegistros = ref(false)
const errorRegistros = ref<string | null>(null)

async function openDetailModal(emp: AsistenciaEmpleado) {
  selectedEmpleado.value = emp
  showDetailModal.value = true
  loadingRegistros.value = true
  errorRegistros.value = null
  registrosEmpleado.value = []
  
  try {
    const { data } = await api.get('/asistencia/', {
      params: {
        usuario_id: emp.usuario_id,
        fecha_inicio: fechaInicio.value,
        fecha_fin: fechaFin.value
      }
    })
    registrosEmpleado.value = data
  } catch (e: any) {
    errorRegistros.value = e?.response?.data?.detail || 'Error al cargar los detalles de asistencia'
  } finally {
    loadingRegistros.value = false
  }
}

function formatDetailedDate(iso: string): string {
  const date = new Date(iso)
  return date.toLocaleDateString('es-MX', { weekday: 'long', day: 'numeric', month: 'short' })
}

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
