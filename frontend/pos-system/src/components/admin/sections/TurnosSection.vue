<template>
  <div class="p-6 space-y-6">
    <!-- Header + filtros -->
    <div class="flex flex-wrap items-center gap-4">
      <div>
        <h2 class="text-xl font-black text-slate-800">Historial de Turnos</h2>
        <p class="text-sm text-slate-500 mt-0.5">Arqueos de caja y discrepancias por turno</p>
      </div>
      <div class="flex items-center gap-3 ml-auto flex-wrap">
        <div class="flex items-center gap-2">
          <label class="text-xs font-semibold text-slate-500 uppercase tracking-wide">Desde</label>
          <input
            v-model="fechaInicio"
            type="date"
            class="px-3 py-2 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#00126D]/20 focus:border-[#00126D]"
          />
        </div>
        <div class="flex items-center gap-2">
          <label class="text-xs font-semibold text-slate-500 uppercase tracking-wide">Hasta</label>
          <input
            v-model="fechaFin"
            type="date"
            class="px-3 py-2 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#00126D]/20 focus:border-[#00126D]"
          />
        </div>
        <button
          @click="loadTurnos"
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

    <!-- Empty -->
    <div v-else-if="turnos.length === 0" class="text-center py-16 bg-slate-50 rounded-2xl border-2 border-dashed border-slate-200">
      <p class="text-slate-400 font-medium">No hay turnos cerrados en este período</p>
    </div>

    <!-- Turnos list -->
    <div v-else class="space-y-4">
      <!-- Summary row -->
      <div class="grid grid-cols-3 gap-4 p-4 bg-[#00126D]/5 rounded-2xl border border-[#00126D]/10">
        <div class="text-center">
          <p class="text-2xl font-black text-[#00126D]">{{ turnos.length }}</p>
          <p class="text-xs font-semibold text-slate-500 uppercase tracking-wide mt-0.5">Turnos</p>
        </div>
        <div class="text-center">
          <p class="text-2xl font-black text-emerald-600">${{ totalVentas.toFixed(2) }}</p>
          <p class="text-xs font-semibold text-slate-500 uppercase tracking-wide mt-0.5">Total Ventas</p>
        </div>
        <div class="text-center">
          <p class="text-2xl font-black" :class="totalDiscrepancia === 0 ? 'text-slate-600' : totalDiscrepancia < 0 ? 'text-red-600' : 'text-amber-600'">
            ${{ totalDiscrepancia.toFixed(2) }}
          </p>
          <p class="text-xs font-semibold text-slate-500 uppercase tracking-wide mt-0.5">Discrepancia Total</p>
        </div>
      </div>

      <!-- Individual turno cards -->
      <div
        v-for="turno in turnos"
        :key="turno.id"
        class="bg-white border border-slate-100 rounded-2xl p-5 shadow-sm hover:shadow-md transition-shadow"
      >
        <div class="flex items-start justify-between gap-4 mb-4">
          <div>
            <div class="flex items-center gap-2 mb-1">
              <span class="text-xs font-black text-slate-400 uppercase tracking-widest">#{{ turno.id }}</span>
              <span
                class="text-xs font-bold px-2 py-0.5 rounded-lg"
                :class="turno.estado === 'cerrado' ? 'bg-slate-100 text-slate-600' : 'bg-emerald-100 text-emerald-700'"
              >
                {{ turno.estado === 'cerrado' ? 'Cerrado' : 'Abierto' }}
              </span>
            </div>
            <p class="font-bold text-slate-800">{{ turno.usuario_nombre || 'Cajero desconocido' }}</p>
          </div>
          <div class="text-right text-xs text-slate-500">
            <p>{{ formatDateTime(turno.fecha_apertura) }}</p>
            <p v-if="turno.fecha_cierre">→ {{ formatDateTime(turno.fecha_cierre) }}</p>
          </div>
        </div>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div class="bg-slate-50 rounded-xl p-3">
            <p class="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1">Fondo Inicial</p>
            <p class="font-black text-slate-700">${{ Number(turno.total_inicial || 0).toFixed(2) }}</p>
          </div>
          <div class="bg-emerald-50 rounded-xl p-3">
            <p class="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1">Ventas Efectivo</p>
            <p class="font-black text-emerald-700">${{ Number(turno.ventas_efectivo || 0).toFixed(2) }}</p>
          </div>
          <div class="bg-slate-50 rounded-xl p-3">
            <p class="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1">Total Final</p>
            <p class="font-black text-slate-700">${{ Number(turno.total_final || 0).toFixed(2) }}</p>
          </div>
          <div class="rounded-xl p-3" :class="discrepanciaClass(turno.diferencia)">
            <p class="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1">Discrepancia</p>
            <p class="font-black" :class="discrepanciaTextClass(turno.diferencia)">
              {{ turno.diferencia !== null ? `$${Number(turno.diferencia).toFixed(2)}` : '—' }}
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onActivated } from 'vue'
import { api } from '@/api/client'
import type { Turno } from '@/types'

const turnos = ref<Turno[]>([])
const loading = ref(false)

function getDateStr(daysAgo: number): string {
  const d = new Date()
  d.setDate(d.getDate() - daysAgo)
  return d.toISOString().split('T')[0]
}

const fechaInicio = ref(getDateStr(7))
const fechaFin = ref(getDateStr(0))

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('es-MX', {
    month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function discrepanciaClass(diferencia: number | null): string {
  if (diferencia === null) return 'bg-slate-50'
  if (diferencia === 0) return 'bg-emerald-50'
  if (diferencia < 0) return 'bg-red-50'
  return 'bg-amber-50'
}

function discrepanciaTextClass(diferencia: number | null): string {
  if (diferencia === null) return 'text-slate-400'
  if (diferencia === 0) return 'text-emerald-700'
  if (diferencia < 0) return 'text-red-700'
  return 'text-amber-700'
}

const totalVentas = computed(() =>
  turnos.value.reduce((sum, t) => sum + Number(t.ventas_efectivo || 0), 0)
)

const totalDiscrepancia = computed(() =>
  turnos.value.reduce((sum, t) => sum + Number(t.diferencia || 0), 0)
)

async function loadTurnos() {
  loading.value = true
  try {
    const { data } = await api.get('/turnos/', {
      params: {
        fecha_inicio: fechaInicio.value,
        fecha_fin: fechaFin.value,
        estado: 'cerrado',
      },
    })
    turnos.value = data
  } catch (e) {
    console.error('Error cargando turnos:', e)
  } finally {
    loading.value = false
  }
}

onMounted(loadTurnos)
onActivated(loadTurnos)
</script>
