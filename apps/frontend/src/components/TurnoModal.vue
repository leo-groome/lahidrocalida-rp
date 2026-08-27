<template>
  <div
    class="fixed inset-0 flex items-center justify-center z-[150] p-4 bg-black/60 backdrop-blur-sm transition-opacity"
    @click.self="$emit('cancelar')"
  >
    <div class="bg-white rounded-2xl max-w-5xl w-full shadow-2xl border border-gray-100 flex flex-col max-h-[90vh] overflow-hidden">
      <!-- Header -->
      <div class="bg-gradient-to-r from-[#00126D] to-[#001D9A] px-6 py-4 flex items-center justify-between text-white border-b border-[#000d4d]">
        <h2 class="text-xl font-bold flex items-center gap-2 tracking-tight">
          <span v-if="tipo === 'inicio'" class="text-2xl drop-shadow-sm">💰</span>
          <span v-else class="text-2xl drop-shadow-sm">📊</span>
          {{ tipo === 'inicio' ? 'Iniciar Turno' : 'Cerrar Turno' }}
        </h2>
        <div class="flex items-center gap-4">
          <!-- Auto-save indicator -->
          <div class="flex items-center gap-1.5 text-blue-100 text-xs font-medium bg-black/20 px-3 py-1.5 rounded-full border border-white/10 shadow-inner">
             <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
             Guardado automático
          </div>
          <button @click="$emit('cancelar')" class="text-white hover:text-rose-300 transition-colors text-3xl leading-none font-light hover:rotate-90 transform duration-200">
            &times;
          </button>
        </div>
      </div>

      <!-- Contenido -->
      <div class="p-6 flex-1 overflow-y-auto bg-gray-50">
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          <!-- Lado Izquierdo: Denominaciones (7 columnas) -->
          <div class="lg:col-span-7 space-y-5">
            <div>
              <p class="text-gray-600 font-medium text-sm">
                {{ tipo === 'inicio'
                  ? 'Ingresa la cantidad de cada denominación para tu fondo inicial:'
                  : 'Ingresa la cantidad de dinero físico actual en tu caja:'
                }}
              </p>
            </div>

            <div class="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-5 gap-3">
              <div v-for="denominacion in denominaciones" :key="denominacion.value" 
                   class="bg-white p-2.5 rounded-2xl shadow-sm border border-gray-100 flex flex-col items-center gap-2 transition-all hover:border-blue-200 hover:shadow-md group">
                <div class="text-center">
                  <span class="text-xl font-black text-gray-800 tracking-tight">${{ denominacion.value.toLocaleString() }}</span>
                  <div class="text-[10px] text-gray-400 font-bold uppercase tracking-widest mt-0.5 group-hover:text-blue-500 transition-colors">
                    {{ denominacion.value >= 20 ? 'Billete' : 'Moneda' }}
                  </div>
                </div>
                
                <div class="flex items-center justify-between w-full bg-slate-50 rounded-lg p-1 border border-slate-200 shadow-inner">
                  <button @click="decrementar(denominacion.value)" :disabled="conteos[denominacion.value] <= 0"
                          class="w-7 h-7 flex items-center justify-center bg-white text-rose-500 hover:bg-rose-50 active:bg-rose-100 rounded-md font-bold text-base shadow-sm border border-slate-200 disabled:opacity-40 disabled:cursor-not-allowed transition-all">
                    &minus;
                  </button>
                  <input v-model.number="conteos[denominacion.value]" @input="validarInput(denominacion.value)"
                         type="number" min="0" step="1"
                         class="w-10 text-center bg-transparent font-bold text-gray-800 focus:outline-none appearance-none text-sm px-0" />
                  <button @click="incrementar(denominacion.value)"
                          class="w-7 h-7 flex items-center justify-center bg-white text-emerald-600 hover:bg-emerald-50 active:bg-emerald-100 rounded-md font-bold text-base shadow-sm border border-slate-200 transition-all">
                    +
                  </button>
                </div>
                
                <div class="text-xs font-black text-[#00126D] bg-blue-50 w-full text-center py-1 rounded-lg border border-blue-100/50">
                  ${{ (denominacion.value * (conteos[denominacion.value] || 0)).toLocaleString('es-MX', { minimumFractionDigits: 2 }) }}
                </div>
              </div>
            </div>
            
            <!-- Botón limpiar -->
            <div class="flex justify-end pt-2">
              <button v-if="totalItems > 0" @click="limpiarTodo"
                      class="px-4 py-2 text-xs font-semibold bg-white hover:bg-rose-50 text-rose-600 rounded-lg shadow-sm border border-rose-200 transition-all flex items-center gap-1.5 hover:shadow-md">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                Limpiar contadores
              </button>
            </div>
          </div>
          
          <!-- Lado Derecho: Resumen y Acciones (5 columnas) -->
          <div class="lg:col-span-5 flex flex-col gap-5">
            
            <!-- Fondo anterior -->
            <div v-if="tipo === 'inicio' && fondoAnterior !== undefined" 
                 class="bg-blue-50 border border-blue-100 p-4 rounded-xl flex items-center gap-3">
              <div class="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 shadow-inner">
                <span class="text-xl">💡</span>
              </div>
              <div>
                <div class="text-xs text-blue-600 font-bold uppercase tracking-wider">Fondo esperado</div>
                <div class="text-lg font-black text-blue-900">${{ fondoAnterior.toLocaleString('es-MX', { minimumFractionDigits: 2 }) }}</div>
              </div>
            </div>

            <!-- Modern Reporte Turno (Renovación de cuadro amarillo) -->
            <div v-if="tipo === 'cierre' && reporteTurno" class="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden transform transition-all hover:shadow-md hover:border-gray-300">
              <div class="px-5 py-3.5 bg-gray-50 border-b border-gray-100 flex justify-between items-center">
                <h3 class="font-bold text-gray-800 text-sm flex items-center gap-2">
                  <svg class="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                  Resumen del Turno
                </h3>
              </div>
              <div class="p-5 grid grid-cols-2 gap-4">
                <div class="bg-gray-50 p-3 rounded-xl border border-gray-100 relative overflow-hidden group">
                  <div class="absolute inset-y-0 left-0 w-1 bg-emerald-400 rounded-l-xl"></div>
                  <div class="text-[10px] text-gray-500 font-bold uppercase mb-1 tracking-wider">Ventas Efectivo</div>
                  <div class="font-black text-gray-800 text-base">$ {{ (reporteTurno.ventas_hasta_ahora?.ventas_efectivo ?? 0).toLocaleString('es-MX', {minimumFractionDigits: 2}) }}</div>
                </div>
                <div class="bg-gray-50 p-3 rounded-xl border border-gray-100 relative overflow-hidden group">
                  <div class="absolute inset-y-0 left-0 w-1 bg-blue-400 rounded-l-xl"></div>
                  <div class="text-[10px] text-gray-500 font-bold uppercase mb-1 tracking-wider">Propinas</div>
                  <div class="font-black text-gray-800 text-base">$ {{ (reporteTurno.ventas_hasta_ahora?.propinas_efectivo ?? 0).toLocaleString('es-MX', {minimumFractionDigits: 2}) }}</div>
                </div>
                <div class="bg-gray-50 p-3 rounded-xl border border-gray-100 relative overflow-hidden">
                  <div class="absolute inset-y-0 left-0 w-1 bg-indigo-400 rounded-l-xl"></div>
                  <div class="text-[10px] text-gray-500 font-bold uppercase mb-1 tracking-wider">Fondo Inicial</div>
                  <div class="font-black text-indigo-900 text-base">+ $ {{ (reporteTurno.conteo_inicial?.total ?? 0).toLocaleString('es-MX', {minimumFractionDigits: 2}) }}</div>
                </div>
                <div class="bg-rose-50/50 p-3 rounded-xl border border-rose-100 relative overflow-hidden">
                  <div class="absolute inset-y-0 left-0 w-1 bg-rose-400 rounded-l-xl"></div>
                  <div class="text-[10px] text-rose-600 font-bold uppercase mb-1 tracking-wider">Gastos</div>
                  <div class="font-black text-rose-700 text-base">- $ {{ (reporteTurno.ventas_hasta_ahora?.gastos ?? reporteTurno.gastos_turno ?? 0).toLocaleString('es-MX', {minimumFractionDigits: 2}) }}</div>
                </div>
              </div>
              <div class="bg-gradient-to-r from-emerald-50 to-teal-50 px-5 py-4 border-t border-emerald-100 flex justify-between items-center">
                <span class="text-xs font-bold text-emerald-800 uppercase tracking-widest">Total Esperado</span>
                <span class="text-xl font-black text-emerald-900 drop-shadow-sm">$ {{ (reporteTurno.ventas_hasta_ahora?.total_esperado ?? 0).toLocaleString('es-MX', {minimumFractionDigits: 2}) }}</span>
              </div>
            </div>
            
            <!-- Retiro vs Fondo (Cierre) -->
            <div v-if="tipo === 'cierre'" class="bg-white border border-blue-100 rounded-2xl shadow-sm p-5 space-y-4">
              <div>
                <label class="block text-sm font-bold text-blue-900 mb-2">¿Cuánto dinero dejarás de fondo en caja?</label>
                <div class="relative group">
                  <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <span class="text-blue-500 font-black text-xl">$</span>
                  </div>
                  <input v-model.number="montoRestante" type="number" step="0.01" min="0"
                         class="w-full pl-10 pr-4 py-3 border-2 border-blue-100 rounded-xl text-xl font-black text-[#00126D] bg-blue-50/30 focus:bg-white focus:ring-4 focus:ring-blue-100 focus:border-blue-500 transition-all shadow-inner outline-none"
                         placeholder="0.00" />
                </div>
              </div>
              
              <div class="bg-slate-50 rounded-xl p-4 flex justify-between items-center border border-slate-200">
                <div>
                  <div class="text-xs font-bold text-slate-500 uppercase tracking-wider">Monto a retirar libre (Dueños)</div>
                </div>
                <div class="text-2xl font-black text-slate-800">
                  ${{ Math.max(0, totalCalculado - (montoRestante || 0)).toLocaleString('es-MX', { minimumFractionDigits: 2 }) }}
                </div>
              </div>
            </div>

            <!-- Observaciones -->
            <div class="bg-white border border-gray-200 rounded-2xl shadow-sm p-5">
              <label class="block text-sm font-bold text-gray-700 mb-2">Observaciones</label>
              <textarea v-model="observaciones" rows="2"
                        class="w-full px-4 py-3 border border-gray-200 bg-gray-50 rounded-xl focus:bg-white focus:border-blue-500 focus:ring-4 focus:ring-blue-50 text-sm resize-none transition-all outline-none"
                        :placeholder="tipo === 'inicio' ? 'Ej: Se dejan billetes de cambio...' : 'Ej: Hay un faltante justificado...'"></textarea>
            </div>
            
            <!-- Totales Globales y Confirmar -->
            <div class="bg-gradient-to-br from-[#00126D] to-[#000a3d] rounded-2xl shadow-xl p-6 text-white mt-auto border border-[#00126D] relative overflow-hidden">
              <!-- Decorative element -->
              <div class="absolute top-0 right-0 -mt-10 -mr-10 w-40 h-40 bg-white opacity-[0.03] rounded-full"></div>
              <div class="absolute bottom-0 left-0 -mb-10 -ml-10 w-32 h-32 bg-white opacity-[0.03] rounded-full"></div>
              
              <div class="flex justify-between items-end mb-6 relative z-10">
                <div>
                  <div class="text-blue-200 text-xs font-bold uppercase tracking-wider mb-1">Total {{ tipo === 'inicio' ? 'Inicial' : 'Contado' }}</div>
                  <div class="text-4xl font-black tracking-tight drop-shadow-md">${{ totalCalculado.toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</div>
                </div>
                <div class="text-right">
                  <div class="bg-white/10 px-3 py-1 rounded-full border border-white/20 text-blue-100 text-xs font-medium backdrop-blur-sm">{{ totalItems }} items</div>
                </div>
              </div>
              
              <button @click="onConfirmClick"
                      class="w-full py-4 bg-white text-[#00126D] hover:bg-gray-50 border border-white font-black rounded-xl transition-all shadow-[0_4px_14px_0_rgba(255,255,255,0.39)] hover:shadow-[0_6px_20px_rgba(255,255,255,0.23)] hover:-translate-y-0.5 active:translate-y-0 active:shadow-none flex items-center justify-center gap-2 text-base relative z-10">
                {{ tipo === 'inicio' ? 'CONFIRMAR INICIO DE TURNO' : 'CONFIRMAR CIERRE DE TURNO' }}
              </button>
            </div>
          </div>
        </div>
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
            <button @click="showConfirmCero = false" class="px-5 py-2.5 bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold rounded-xl transition-colors">
              Cancelar
            </button>
            <button @click="confirmarCero" class="px-5 py-2.5 bg-rose-500 hover:bg-rose-600 text-white font-bold rounded-xl transition-all shadow-md hover:shadow-lg">
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

const denominaciones = [
  { value: 1000, label: '$1,000' },
  { value: 500, label: '$500' },
  { value: 200, label: '$200' },
  { value: 100, label: '$100' },
  { value: 50, label: '$50' },
  { value: 20, label: '$20' },
  { value: 10, label: '$10' },
  { value: 5, label: '$5' },
  { value: 2, label: '$2' },
  { value: 1, label: '$1' }
]

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

const incrementar = (valor: number) => {
  conteos.value[valor] = (conteos.value[valor] || 0) + 1
}

const decrementar = (valor: number) => {
  if (conteos.value[valor] > 0) {
    conteos.value[valor] -= 1
  }
}

const validarInput = (valor: number) => {
  const cantidad = conteos.value[valor]
  if (cantidad < 0 || isNaN(cantidad)) {
    conteos.value[valor] = 0
  }
}

const limpiarTodo = () => {
  denominaciones.forEach(denom => {
    conteos.value[denom.value] = 0
  })
}

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
