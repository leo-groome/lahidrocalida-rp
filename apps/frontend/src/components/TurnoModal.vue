<template>
  <div
    class="fixed inset-0 flex items-center justify-center z-[150] p-0 sm:p-4 bg-black/60 backdrop-blur-sm"
    @click.self="$emit('cancelar')"
  >
    <div
      class="bg-white sm:rounded-2xl w-full max-w-2xl shadow-2xl border border-slate-100 flex flex-col max-h-[100dvh] sm:max-h-[85vh] overflow-hidden"
      role="dialog"
      aria-modal="true"
      :aria-label="tipo === 'inicio' ? 'Iniciar turno' : 'Cerrar turno'"
    >
      <!-- Header -->
      <div class="bg-gradient-to-r from-[#00126D] to-[#001D9A] px-4 sm:px-6 py-3 flex items-center justify-between text-white shrink-0">
        <h2 class="text-lg sm:text-xl font-bold tracking-tight">
          {{ tipo === 'inicio' ? 'Iniciar Turno' : 'Cerrar Turno' }}
        </h2>
        <div class="flex items-center gap-3">
          <div class="hidden sm:flex items-center gap-1.5 text-blue-100 text-xs font-medium bg-black/20 px-3 py-1.5 rounded-full border border-white/10">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
            Guardado automático
          </div>
          <button type="button" aria-label="Cancelar" @click="$emit('cancelar')"
                  class="w-11 h-11 flex items-center justify-center text-white hover:text-rose-300 text-3xl leading-none font-light focus:outline-none focus-visible:ring-2 focus-visible:ring-white rounded-lg">
            &times;
          </button>
        </div>
      </div>

      <!-- Contenido (único scroll) -->
      <div class="flex-1 overflow-y-auto bg-slate-50 p-4 space-y-4">

        <!-- 1. Resumen del turno (solo cierre) -->
        <div v-if="tipo === 'cierre' && reporteTurno" class="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <div class="px-4 py-3 bg-slate-50 border-b border-slate-100">
            <h3 class="font-bold text-slate-800 text-sm">Resumen del Turno</h3>
          </div>
          <div class="p-4 grid grid-cols-2 gap-3">
            <div class="bg-slate-50 p-3 rounded-xl border border-slate-100 relative overflow-hidden">
              <div class="absolute inset-y-0 left-0 w-1 bg-emerald-400"></div>
              <div class="text-[10px] text-slate-500 font-bold uppercase mb-1 tracking-wider">Ventas Efectivo</div>
              <div class="font-black text-slate-800 tabular-nums">{{ money(reporteTurno.ventas_hasta_ahora?.ventas_efectivo) }}</div>
            </div>
            <div class="bg-slate-50 p-3 rounded-xl border border-slate-100 relative overflow-hidden">
              <div class="absolute inset-y-0 left-0 w-1 bg-blue-400"></div>
              <div class="text-[10px] text-slate-500 font-bold uppercase mb-1 tracking-wider">Propinas efectivo</div>
              <div class="font-black text-slate-800 tabular-nums">{{ money(reporteTurno.ventas_hasta_ahora?.propinas_efectivo) }}</div>
            </div>
            <div class="bg-slate-50 p-3 rounded-xl border border-slate-100 relative overflow-hidden">
              <div class="absolute inset-y-0 left-0 w-1 bg-indigo-400"></div>
              <div class="text-[10px] text-slate-500 font-bold uppercase mb-1 tracking-wider">Fondo Inicial</div>
              <div class="font-black text-indigo-900 tabular-nums">+ {{ money(reporteTurno.conteo_inicial?.total) }}</div>
            </div>
            <div class="bg-rose-50/50 p-3 rounded-xl border border-rose-100 relative overflow-hidden">
              <div class="absolute inset-y-0 left-0 w-1 bg-rose-400"></div>
              <div class="text-[10px] text-rose-600 font-bold uppercase mb-1 tracking-wider">Gastos</div>
              <div class="font-black text-rose-700 tabular-nums">- {{ money(reporteTurno.ventas_hasta_ahora?.gastos ?? reporteTurno.gastos_turno) }}</div>
            </div>
          </div>

          <!-- Esperado vs contado vs diferencia (en vivo) -->
          <div class="border-t border-slate-100 grid grid-cols-3 text-center divide-x divide-slate-100">
            <div class="px-2 py-3">
              <div class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Esperado</div>
              <div class="text-base sm:text-lg font-black text-slate-800 tabular-nums">{{ money(totalEsperado) }}</div>
            </div>
            <div class="px-2 py-3">
              <div class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Contado</div>
              <div class="text-base sm:text-lg font-black text-[#00126D] tabular-nums">{{ money(totalCalculado) }}</div>
            </div>
            <div class="px-2 py-3" :class="diferenciaClases.bg" aria-live="polite">
              <div class="text-[10px] font-bold uppercase tracking-wider" :class="diferenciaClases.label">Diferencia</div>
              <div class="text-base sm:text-lg font-black tabular-nums" :class="diferenciaClases.valor">
                {{ diferencia > 0.004 ? '+' : '' }}{{ money(diferencia) }}
              </div>
              <div class="text-[10px] font-semibold" :class="diferenciaClases.label">{{ diferenciaTexto }}</div>
            </div>
          </div>

          <!-- Uber Eats: aparte del efectivo esperado -->
          <div v-if="(reporteTurno.uber_eats?.pedidos ?? 0) > 0" class="px-4 py-3 border-t border-slate-100 flex justify-between items-center bg-slate-50 gap-3">
            <span class="text-xs font-bold text-slate-600 uppercase tracking-wider">Uber Eats ({{ reporteTurno.uber_eats.pedidos }}) · no entra a caja</span>
            <span class="text-base font-black text-slate-800 tabular-nums">{{ money(reporteTurno.uber_eats.total) }}</span>
          </div>
        </div>

        <!-- Fondo esperado (inicio) -->
        <div v-if="tipo === 'inicio' && fondoAnterior !== undefined && fondoAnterior !== null"
             class="bg-blue-50 border border-blue-100 px-4 py-3 rounded-xl flex items-center justify-between">
          <div class="text-xs text-blue-700 font-bold uppercase tracking-wider">Fondo esperado</div>
          <div class="text-lg font-black text-blue-900 tabular-nums">{{ money(fondoAnterior) }}</div>
        </div>

        <!-- 2. Conteo -->
        <div>
          <div class="flex items-center justify-between gap-3 mb-2">
            <p class="text-slate-600 font-medium text-sm">
              {{ tipo === 'inicio'
                ? 'Cantidad de cada denominación en tu fondo inicial:'
                : 'Cantidad de dinero físico actual en tu caja:' }}
            </p>
            <button v-if="totalItems > 0" type="button" @click="limpiarTodo"
                    class="shrink-0 min-h-[44px] px-3 text-xs font-semibold bg-white hover:bg-rose-50 text-rose-600 rounded-lg border border-rose-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-400">
              Limpiar
            </button>
          </div>

          <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div class="px-3 py-1.5 bg-slate-100 text-[11px] font-black uppercase tracking-widest text-slate-500">Billetes</div>
            <DenominacionRow v-for="d in billetes" :key="d" :denominacion="d" :model-value="conteos[d] || 0"
                             @update:model-value="conteos[d] = $event" />
            <div class="px-3 py-1.5 bg-slate-100 text-[11px] font-black uppercase tracking-widest text-slate-500 border-t border-slate-200">Monedas</div>
            <DenominacionRow v-for="d in monedas" :key="d" :denominacion="d" :model-value="conteos[d] || 0"
                             @update:model-value="conteos[d] = $event" />
          </div>
        </div>

        <!-- 3. Fondo en caja / retiro (cierre) -->
        <div v-if="tipo === 'cierre'" class="bg-white border border-blue-100 rounded-2xl shadow-sm p-4 space-y-3">
          <div>
            <label for="monto-restante" class="block text-sm font-bold text-blue-900 mb-2">¿Cuánto dinero dejarás de fondo en caja?</label>
            <div class="relative">
              <span class="absolute inset-y-0 left-0 pl-4 flex items-center text-blue-500 font-black text-xl pointer-events-none">$</span>
              <input id="monto-restante" v-model.number="montoRestante" type="number" inputmode="decimal" step="0.01" min="0"
                     class="w-full pl-10 pr-4 h-12 border-2 border-blue-100 rounded-xl text-xl font-black text-[#00126D] bg-blue-50/30 focus:bg-white focus:ring-4 focus:ring-blue-100 focus:border-blue-500 outline-none"
                     placeholder="0.00" />
            </div>
          </div>
          <div class="bg-slate-50 rounded-xl p-3 flex justify-between items-center border border-slate-200">
            <div class="text-xs font-bold text-slate-500 uppercase tracking-wider">Monto a retirar (Dueños)</div>
            <div class="text-2xl font-black text-slate-800 tabular-nums">{{ money(montoARetirar) }}</div>
          </div>
        </div>

        <!-- Observaciones -->
        <div class="bg-white border border-slate-200 rounded-2xl shadow-sm p-4">
          <label for="turno-observaciones" class="block text-sm font-bold text-slate-700 mb-2">Observaciones</label>
          <textarea id="turno-observaciones" v-model="observaciones" rows="2"
                    class="w-full px-3 py-2 border border-slate-200 bg-slate-50 rounded-xl focus:bg-white focus:border-blue-500 focus:ring-4 focus:ring-blue-50 text-sm resize-none outline-none"
                    :placeholder="tipo === 'inicio' ? 'Ej: Se dejan billetes de cambio...' : 'Ej: Hay un faltante justificado...'"></textarea>
        </div>
      </div>

      <!-- Footer fijo: total + confirmar -->
      <div class="shrink-0 bg-gradient-to-br from-[#00126D] to-[#000a3d] text-white px-4 py-3 sm:px-6 border-t border-[#00126D]">
        <div class="flex items-center justify-between gap-3 mb-3">
          <div>
            <div class="text-blue-200 text-[11px] font-bold uppercase tracking-wider">Total {{ tipo === 'inicio' ? 'inicial' : 'contado' }}</div>
            <div class="text-3xl font-black tracking-tight tabular-nums">{{ money(totalCalculado) }}</div>
          </div>
          <div class="text-right space-y-1">
            <div class="bg-white/10 px-3 py-1 rounded-full border border-white/20 text-blue-100 text-xs font-medium inline-block">{{ totalItems }} piezas</div>
            <div v-if="tipo === 'cierre' && reporteTurno" class="text-xs font-bold" :class="diferenciaFooterClase">
              {{ diferenciaTexto }}
            </div>
          </div>
        </div>
        <button type="button" @click="onConfirmClick"
                class="w-full min-h-[52px] bg-white text-[#00126D] hover:bg-slate-50 font-black rounded-xl transition-all active:scale-[0.99] text-base focus:outline-none focus-visible:ring-4 focus-visible:ring-blue-300">
          {{ tipo === 'inicio' ? 'CONFIRMAR INICIO DE TURNO' : 'CONFIRMAR CIERRE DE TURNO' }}
        </button>
      </div>
    </div>

    <!-- Confirmación: total $0.00 -->
    <div v-if="showConfirmCero" class="fixed inset-0 flex items-center justify-center z-[160] p-4 bg-black/60 backdrop-blur-sm" @click.self="showConfirmCero = false">
      <div class="bg-white rounded-2xl max-w-sm w-full shadow-2xl overflow-hidden border border-rose-100">
        <div class="bg-rose-500 px-6 py-4 flex items-center gap-2">
          <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
          <div class="text-white font-bold text-lg">Confirmar Total Cero</div>
        </div>
        <div class="p-6">
          <p class="text-gray-700 text-base mb-6 leading-relaxed">
            Estás a punto de <strong class="text-rose-600 bg-rose-50 px-1 rounded">{{ tipo === 'inicio' ? 'iniciar' : 'cerrar' }}</strong> el turno con <strong>$0.00</strong> calculados. ¿Estás seguro de que tu caja no tiene dinero?
          </p>
          <div class="flex gap-3 justify-end">
            <button type="button" @click="showConfirmCero = false" class="min-h-[44px] px-5 bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold rounded-xl transition-colors">
              Cancelar
            </button>
            <button type="button" @click="confirmarCero" class="min-h-[44px] px-5 bg-rose-500 hover:bg-rose-600 text-white font-bold rounded-xl transition-all shadow-md">
              Sí, confirmar $0.00
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import DenominacionRow from '@/components/turno/DenominacionRow.vue'

const props = defineProps<{
  tipo: 'inicio' | 'cierre'
  denominacionesIniciales?: Array<{
    denominacion: number
    cantidad: number
  }>
  reporteTurno?: any
  fondoAnterior?: number
}>()

const emit = defineEmits<{
  cancelar: []
  confirmar: [data: {
    denominaciones: Array<{
      denominacion: number
      cantidad: number
      subtotal: number
    }>
    total: number
    monto_retirado?: number
    monto_restante_en_caja?: number
    observaciones?: string
  }]
}>()

function handleKeyDown(e: KeyboardEvent) {
  if (showConfirmCero.value) {
    if (e.key === 'Escape') {
      e.preventDefault()
      showConfirmCero.value = false
      return
    }
    if (e.key === 'Enter' || e.key === 'NumpadEnter') {
      e.preventDefault()
      confirmarCero()
      return
    }
  }

  if (e.key === 'Escape') {
    e.preventDefault()
    emit('cancelar')
    return
  }

  // Only handle Enter if user is not actively typing in observations or number inputs
  if (e.key === 'Enter' || e.key === 'NumpadEnter') {
    const target = e.target as HTMLElement
    if (target && target.tagName === 'TEXTAREA') return
    e.preventDefault()
    onConfirmClick()
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
})

const billetes = [1000, 500, 200, 100, 50, 20]
const monedas = [10, 5, 2, 1]
const denominaciones = [...billetes, ...monedas].map(value => ({ value }))

const money = (n?: number | null) =>
  '$' + Number(n ?? 0).toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const conteos = ref<Record<number, number>>({})
const observaciones = ref('')
const montoRestante = ref<number | null>(null)
const showConfirmCero = ref(false)

// LocalStorage key based on type
const CACHE_KEY = computed(() => `turno_conteo_${props.tipo}`)

// Auto-save watch logic
watch([conteos, observaciones, montoRestante], () => {
  const data = {
    conteos: conteos.value,
    observaciones: observaciones.value,
    montoRestante: montoRestante.value,
    timestamp: Date.now()
  }
  localStorage.setItem(CACHE_KEY.value, JSON.stringify(data))
}, { deep: true })

const cargarDesdeCache = () => {
  const saved = localStorage.getItem(CACHE_KEY.value)
  if (saved) {
    try {
      const data = JSON.parse(saved)
      if (data.conteos) {
         Object.keys(data.conteos).forEach(key => {
            conteos.value[Number(key)] = data.conteos[key]
         })
      }
      observaciones.value = data.observaciones || ''
      if (data.montoRestante !== undefined) {
        montoRestante.value = data.montoRestante
      }
    } catch (e) {
      console.error('Error cargando cache automática:', e)
    }
  }
}

const limpiarCache = () => {
  localStorage.removeItem(CACHE_KEY.value)
}

onMounted(() => {
  // Inicializamos en 0
  denominaciones.forEach(denom => {
    conteos.value[denom.value] = 0
  })

  // Si venimos de la prop
  if (props.tipo === 'cierre' && props.denominacionesIniciales) {
    props.denominacionesIniciales.forEach(item => {
      if (item.denominacion in conteos.value) {
        conteos.value[item.denominacion] = item.cantidad
      }
    })
  }

  // Cargar caché si existe
  cargarDesdeCache()
})

const totalCalculado = computed(() => {
  return denominaciones.reduce((total, denom) => {
    return total + (denom.value * (conteos.value[denom.value] || 0))
  }, 0)
})

const totalItems = computed(() => {
  return denominaciones.reduce((total, denom) => {
    return total + (conteos.value[denom.value] || 0)
  }, 0)
})

const limpiarTodo = () => {
  denominaciones.forEach(denom => {
    conteos.value[denom.value] = 0
  })
}

// Resumen en vivo (solo cierre). Campos opcionales: un reporte con comandas
// no efectivo (metodo_pago) o sin propina_efectivo no rompe nada, solo usamos totales.
const totalEsperado = computed(() => Number(props.reporteTurno?.ventas_hasta_ahora?.total_esperado ?? 0))
const diferencia = computed(() => Math.round((totalCalculado.value - totalEsperado.value) * 100) / 100)
const montoARetirar = computed(() => Math.max(0, totalCalculado.value - (montoRestante.value || 0)))

const diferenciaTexto = computed(() => {
  if (Math.abs(diferencia.value) < 0.005) return 'Cuadra'
  return diferencia.value < 0 ? 'Faltante' : 'Sobrante'
})
const diferenciaClases = computed(() => {
  if (Math.abs(diferencia.value) < 0.005) return { bg: 'bg-emerald-50', label: 'text-emerald-700', valor: 'text-emerald-800' }
  if (diferencia.value < 0) return { bg: 'bg-rose-50', label: 'text-rose-700', valor: 'text-rose-700' }
  return { bg: 'bg-amber-50', label: 'text-amber-700', valor: 'text-amber-700' }
})
const diferenciaFooterClase = computed(() => {
  if (Math.abs(diferencia.value) < 0.005) return 'text-emerald-300'
  return diferencia.value < 0 ? 'text-rose-300' : 'text-amber-300'
})

const onConfirmClick = () => {
  if (totalItems.value === 0) {
    showConfirmCero.value = true
    return
  }
  confirmar()
}

const confirmarCero = () => {
  showConfirmCero.value = false
  confirmar()
}

const confirmar = () => {
  const denominacionesData = denominaciones
    .filter(denom => conteos.value[denom.value] > 0)
    .map(denom => ({
      denominacion: denom.value,
      cantidad: conteos.value[denom.value],
      subtotal: denom.value * conteos.value[denom.value]
    }))

  const monto_restante_en_caja = props.tipo === 'cierre' ? (montoRestante.value || 0) : 0
  const monto_retirado = props.tipo === 'cierre' ? Math.max(0, totalCalculado.value - monto_restante_en_caja) : 0

  limpiarCache()

  emit('confirmar', {
    denominaciones: denominacionesData,
    total: totalCalculado.value,
    monto_restante_en_caja,
    monto_retirado,
    observaciones: observaciones.value.trim() || undefined
  })
}
</script>
