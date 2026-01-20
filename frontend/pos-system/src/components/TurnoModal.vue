<template>
  <div
    class="fixed inset-0 flex items-center justify-center z-[70] p-4"
    @click.self="$emit('cancelar')"
  >
    <div class="bg-white rounded-2xl max-w-2xl w-full shadow-2xl border-2 border-blue-300 max-h-[85vh] flex flex-col">
      <!-- Header profesional -->
      <div class="bg-gradient-to-r from-blue-600 to-blue-700 px-5 py-3 rounded-t-2xl">
        <div class="flex items-center justify-between text-white">
          <h2 class="text-lg font-bold flex items-center gap-1.5">
            <span v-if="tipo === 'inicio'">💰</span>
            <span v-else>📊</span>
            {{ tipo === 'inicio' ? 'Iniciar Turno' : 'Cerrar Turno' }}
          </h2>
          <button
            @click="$emit('cancelar')"
            class="text-white hover:text-gray-200 text-xl font-bold"
          >
            ×
          </button>
        </div>
      </div>

      <!-- Contenido -->
      <div class="p-3 flex-1 overflow-y-auto">
        <!-- Instrucciones -->
        <div class="mb-6 text-center">
          <p class="text-gray-600 text-sm">
            {{ tipo === 'inicio'
              ? 'Ingresa la cantidad de cada denominación para el conteo inicial'
              : 'Ingresa la cantidad de cada denominación para el conteo final'
            }}
          </p>
        </div>

         <!-- Reporte (solo cierre) -->
         <div v-if="tipo === 'cierre' && reporteTurno" class="mb-4 p-3 rounded-lg border border-amber-200 bg-amber-50">
           <div class="flex items-center justify-between mb-2">
             <div class="font-bold text-amber-900">📋 Reporte del turno (efectivo)</div>
             <div class="text-xs text-amber-800">Previo al cierre</div>
           </div>

           <div class="grid grid-cols-2 gap-2 text-xs">
             <div class="bg-white rounded-md p-2 border border-amber-100">
               <div class="text-gray-600">Ventas efectivo</div>
               <div class="font-black text-amber-900">$ {{ (reporteTurno.ventas_hasta_ahora?.ventas_efectivo ?? 0).toFixed(2) }}</div>
             </div>
             <div class="bg-white rounded-md p-2 border border-amber-100">
               <div class="text-gray-600">Propinas efectivo</div>
               <div class="font-black text-amber-900">$ {{ (reporteTurno.ventas_hasta_ahora?.propinas_efectivo ?? 0).toFixed(2) }}</div>
             </div>
             <div class="bg-white rounded-md p-2 border border-amber-100">
               <div class="text-gray-600">Gastos (resta)</div>
               <div class="font-black text-red-700">- $ {{ (reporteTurno.ventas_hasta_ahora?.gastos ?? reporteTurno.gastos_turno ?? 0).toFixed(2) }}</div>
             </div>
             <div class="bg-white rounded-md p-2 border border-amber-100">
               <div class="text-gray-600">Total esperado</div>
               <div class="font-black text-green-800">$ {{ (reporteTurno.ventas_hasta_ahora?.total_esperado ?? 0).toFixed(2) }}</div>
             </div>
           </div>

           <div class="mt-3">
             <div class="text-xs font-bold text-amber-900 mb-2">💳 Comandas cobradas (efectivo): {{ (reporteTurno.comandas_cobradas || []).length }}</div>
             <div class="max-h-40 overflow-y-auto bg-white rounded-md border border-amber-100">
               <table class="w-full text-[11px]">
                 <thead class="sticky top-0 bg-amber-50">
                   <tr>
                     <th class="text-left px-2 py-1">Pedido</th>
                     <th class="text-left px-2 py-1">Mesa/Cliente</th>
                     <th class="text-right px-2 py-1">Total</th>
                   </tr>
                 </thead>
                 <tbody>
                   <tr v-for="p in (reporteTurno.comandas_cobradas || [])" :key="p.id" class="border-t">
                     <td class="px-2 py-1">#{{ p.numero_display }}</td>
                     <td class="px-2 py-1">{{ p.mesa ? `Mesa ${p.mesa}` : (p.nombre_cliente || '-') }}</td>
                     <td class="px-2 py-1 text-right font-bold">$ {{ Number(p.total || 0).toFixed(2) }}</td>
                   </tr>
                 </tbody>
               </table>
             </div>
           </div>
         </div>

         <!-- Tabla de denominaciones -->
        <div class="overflow-x-auto">
          <table class="w-full text-xs">
            <thead>
              <tr class="bg-gray-50 text-gray-700">
                  <th class="py-1.5 px-2 text-left font-medium">Denominación</th>
                  <th class="py-1.5 px-2 text-center font-medium">Cantidad</th>
                  <th class="py-1.5 px-2 text-right font-medium">Subtotal</th>
                </tr>
            </thead>
            <tbody>
              <tr
                v-for="denominacion in denominaciones"
                :key="denominacion.value"
                class="border-b border-gray-100 hover:bg-gray-50"
              >
                <!-- Columna de denominación -->
                <td class="py-1.5 px-2">
                  <div class="flex items-center">
                    <span class="text-sm font-bold text-gray-800">
                      ${{ denominacion.value.toLocaleString() }}
                    </span>
                    <span v-if="denominacion.value >= 100" class="ml-1 text-[9px] text-gray-500">
                      (billete)
                    </span>
                    <span v-else class="ml-1 text-[9px] text-gray-500">
                      (moneda)
                    </span>
                  </div>
                </td>

                <!-- Columna de cantidad con controles -->
                <td class="py-1.5 px-2">
                  <div class="flex items-center justify-center space-x-1.5">
                    <!-- Botón disminuir -->
                    <button
                      @click="decrementar(denominacion.value)"
                      :disabled="conteos[denominacion.value] <= 0"
                      class="w-6 h-6 flex items-center justify-center bg-gray-200 hover:bg-gray-300 disabled:opacity-30 disabled:cursor-not-allowed rounded-lg transition-colors"
                    >
                      <span class="text-gray-700 font-bold text-sm">−</span>
                    </button>

                    <!-- Input numérico -->
                    <input
                      v-model.number="conteos[denominacion.value]"
                      @input="validarInput(denominacion.value)"
                      type="number"
                      min="0"
                      step="1"
                      class="w-14 py-1 px-1.5 text-center border border-gray-300 rounded-lg focus:border-blue-500 focus:ring-2 focus:ring-blue-200 font-medium text-xs"
                    />

                    <!-- Botón aumentar -->
                    <button
                      @click="incrementar(denominacion.value)"
                      class="w-6 h-6 flex items-center justify-center bg-blue-100 hover:bg-blue-200 text-blue-700 rounded-lg transition-colors"
                    >
                      <span class="font-bold text-sm">+</span>
                    </button>
                  </div>
                </td>

                <!-- Columna de subtotal -->
                <td class="py-1.5 px-2 text-right">
                  <div class="font-bold text-gray-800 text-xs">
                    ${{ (denominacion.value * conteos[denominacion.value]).toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Campo de observaciones -->
        <div class="mt-3">
          <label class="block text-xs font-medium text-gray-700 mb-1.5">
            Observaciones (opcional)
          </label>
          <textarea
            v-model="observaciones"
            rows="1"
            class="w-full px-2 py-1 border border-gray-300 rounded-lg focus:border-blue-500 focus:ring-2 focus:ring-blue-200 text-xs"
            :placeholder="tipo === 'inicio' ? 'Ej: Fondo inicial, billetes de muestra, etc.' : 'Ej: Diferencias, incidentes, etc.'"
          ></textarea>
        </div>

        <!-- Total calculado -->
        <div class="mt-3 p-2 rounded-lg bg-gradient-to-r from-blue-50 to-indigo-50 border-2 border-blue-200">
          <div class="flex justify-between items-center">
            <div>
              <div class="text-xs font-medium text-blue-700">
                Total {{ tipo === 'inicio' ? 'inicial' : 'final' }}
              </div>
              <div class="text-[10px] text-blue-600">
                {{ totalItems }} items
              </div>
            </div>
            <div class="text-right">
              <div class="text-xl font-black text-blue-700">
                ${{ totalCalculado.toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
              </div>
              <div class="text-[10px] text-blue-600 mt-0.5">
                Tiempo real
              </div>
            </div>
          </div>
        </div>

        <!-- Botones de acción -->
        <div class="mt-3 space-y-2">
          <button
            @click="onConfirmClick"
            class="w-full py-2.5 bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 text-white font-bold rounded-lg transition-all flex items-center justify-center gap-2 text-sm"
          >
            <span v-if="tipo === 'inicio'">✅</span>
            <span v-else>📊</span>
            {{ tipo === 'inicio' ? 'Iniciar Turno' : 'Cerrar Turno' }}
          </button>

          <button
            @click="$emit('cancelar')"
            class="w-full py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 font-medium rounded-lg transition-all text-sm"
          >
            Cancelar
          </button>

          <!-- Botón rápido para limpiar todo -->
          <button
            v-if="totalItems > 0"
            @click="limpiarTodo"
            class="w-full py-1 text-xs bg-red-50 hover:bg-red-100 text-red-600 font-medium rounded-lg transition-all border border-red-200"
          >
            Limpiar todo
          </button>
        </div>
      </div>
    </div>

    <!-- Confirmación: total $0.00 -->
    <div
      v-if="showConfirmCero"
      class="fixed inset-0 flex items-center justify-center z-[80] p-4"
      @click.self="showConfirmCero = false"
    >
      <div class="bg-white rounded-xl max-w-sm w-full shadow-2xl border-2 border-amber-200">
        <div class="bg-gradient-to-r from-amber-500 to-amber-600 px-5 py-4 rounded-t-xl">
          <div class="text-white font-bold text-lg">Confirmar $0.00</div>
          <div class="text-amber-100 text-sm mt-1">
            {{ tipo === 'inicio' ? 'Iniciar' : 'Cerrar' }} turno con total en cero
          </div>
        </div>

        <div class="p-5">
          <div class="text-sm text-gray-700">
            Estas a punto de <span class="font-bold">{{ tipo === 'inicio' ? 'iniciar' : 'cerrar' }}</span> el turno con <span class="font-bold">$0.00</span>.
            Confirma si es correcto.
          </div>

          <div class="mt-5 flex gap-3 justify-end">
            <button
              @click="showConfirmCero = false"
              class="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-800 font-semibold rounded-lg transition-all"
            >
              Cancelar
            </button>
            <button
              @click="confirmarCero"
              class="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white font-bold rounded-lg transition-all"
            >
              Si, {{ tipo === 'inicio' ? 'iniciar' : 'cerrar' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'

// Definir props
const props = defineProps<{
  tipo: 'inicio' | 'cierre'
  denominacionesIniciales?: Array<{
    denominacion: number
    cantidad: number
  }>
  reporteTurno?: any
}>()

// Definir emits
const emit = defineEmits<{
  cancelar: []
  confirmar: [data: {
    denominaciones: Array<{
      denominacion: number
      cantidad: number
      subtotal: number
    }>
    total: number
    observaciones?: string
  }]
}>()

// Denominaciones disponibles (ordenadas de mayor a menor)
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

// Estado reactivo para conteos
const conteos = ref<Record<number, number>>({})
const observaciones = ref('')

// Inicializar conteos
const inicializarConteos = () => {
  denominaciones.forEach(denom => {
    conteos.value[denom.value] = 0
  })
}

// Si hay denominaciones iniciales (para cierre), cargarlas
onMounted(() => {
  inicializarConteos()

  if (props.tipo === 'cierre' && props.denominacionesIniciales) {
    props.denominacionesIniciales.forEach(item => {
      if (item.denominacion in conteos.value) {
        conteos.value[item.denominacion] = item.cantidad
      }
    })
  }
})

// Computed properties
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

// Métodos
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
  inicializarConteos()
}

const showConfirmCero = ref(false)

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
  // Preparar array de denominaciones
  const denominacionesData = denominaciones
    .filter(denom => conteos.value[denom.value] > 0)
    .map(denom => ({
      denominacion: denom.value,
      cantidad: conteos.value[denom.value],
      subtotal: denom.value * conteos.value[denom.value]
    }))

  // Emitir datos
  emit('confirmar', {
    denominaciones: denominacionesData,
    total: totalCalculado.value,
    observaciones: observaciones.value.trim() || undefined
  })
}

// Watch para debug (opcional)
watch(conteos, (newConteos) => {
  console.log('Conteos actualizados:', newConteos)
}, { deep: true })
</script>
