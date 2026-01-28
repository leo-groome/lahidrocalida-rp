<template>
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div class="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col">
      <!-- Header -->
      <div class="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
        <h2 class="text-xl font-semibold text-gray-900">
          {{ isEditing ? 'Editar Gasto' : 'Nuevo Gasto' }}
        </h2>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 text-2xl">&times;</button>
      </div>
      
      <!-- Body Scrollable -->
      <div class="p-6 overflow-y-auto flex-1">
        <form @submit.prevent="submitForm" id="gastoForm" class="space-y-6">
          
          <!-- Fila 1: Fecha y Proveedor -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
               <label class="block text-sm font-medium text-gray-700 mb-1">Fecha del Gasto</label>
               <input 
                 type="datetime-local" 
                 v-model="form.fecha_gasto"
                 class="w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                 required
               >
               <p class="text-xs text-gray-500 mt-1">Si es pasado, ajusta la fecha aquí.</p>
            </div>
            
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Proveedor</label>
              <SearchableSelect 
                 v-model="form.proveedor_id" 
                 :options="proveedores"
                 placeholder="Buscar proveedor..."
                 class="w-full"
              />
            </div>
          </div>

          <!-- Fila 2: Tipo, Método, Folio -->
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
             <div>
               <label class="block text-sm font-medium text-gray-700 mb-1">Tipo</label>
               <select v-model="form.tipo_gasto" class="w-full border-gray-300 rounded-md shadow-sm">
                 <option value="directo">Directo (Insumos)</option>
                 <option value="indirecto">Indirecto (Servicios)</option>
                 <option value="nomina">Nómina</option>
               </select>
             </div>
             <div>
               <label class="block text-sm font-medium text-gray-700 mb-1">Método Pago</label>
               <select v-model="form.metodo_pago" class="w-full border-gray-300 rounded-md shadow-sm">
                 <option value="efectivo">Efectivo</option>
                 <option value="tarjeta">Tarjeta</option>
               </select>
             </div>
             <div>
               <label class="block text-sm font-medium text-gray-700 mb-1">Folio / Factura</label>
               <input v-model="form.folio" type="text" class="w-full border-gray-300 rounded-md shadow-sm" placeholder="Opcional">
             </div>
          </div>
          
          <!-- Descripción -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Descripción / Notas</label>
            <textarea v-model="form.descripcion" rows="2" class="w-full border-gray-300 rounded-md shadow-sm"></textarea>
          </div>

          <!-- SECCIÓN DETALLES (Si no es nómina) -->
          <div v-if="form.tipo_gasto !== 'nomina'" class="border-t border-gray-200 pt-4">
             <div class="flex justify-between items-center mb-2">
               <h3 class="text-sm font-medium text-gray-900">Detalle de Artículos</h3>
               <button type="button" @click="addDetalle" class="text-sm text-blue-600 hover:text-blue-800 font-medium">+ Agregar Línea</button>
             </div>
             
             <div class="space-y-2">
                <div v-for="(detalle, idx) in form.detalles" :key="idx" class="flex flex-wrap md:flex-nowrap gap-2 items-start bg-gray-50 p-2 rounded">
                   <div class="flex-1 min-w-[200px]">
                      <SearchableSelect 
                        v-model="detalle.articulo_id" 
                        :options="articulos" 
                        placeholder="Buscar artículo..."
                        class="w-full"
                      />
                   </div>
                   <div class="w-24">
                      <input type="number" step="0.01" v-model.number="detalle.cantidad" placeholder="Cant" class="w-full border-gray-300 rounded text-sm">
                   </div>
                   <div class="w-28">
                      <input type="number" step="0.01" v-model.number="detalle.precio_unitario" placeholder="Precio" class="w-full border-gray-300 rounded text-sm">
                   </div>
                   <div class="w-28 pt-2 text-right font-medium text-sm text-gray-700">
                      ${{ (detalle.cantidad * detalle.precio_unitario).toFixed(2) }}
                   </div>
                   <button type="button" @click="removeDetalle(idx)" class="text-red-500 hover:text-red-700 px-2 font-bold">&times;</button>
                </div>
             </div>

             <div class="mt-4 flex justify-end items-center gap-4">
                <div class="text-sm text-gray-500">Suma detalles: ${{ sumaDetalles.toFixed(2) }}</div>
                <div>
                   <label class="text-xs font-medium text-gray-700 mr-2">Total Manual (Opcional):</label>
                   <input type="number" step="0.01" v-model.number="form.total_manual" class="w-32 border-gray-300 rounded text-sm font-bold text-right">
                </div>
             </div>
          </div>

          <!-- SECCIÓN NOMINA (Solo total manual) -->
          <div v-else class="border-t border-gray-200 pt-4">
             <div class="bg-yellow-50 p-4 rounded border border-yellow-200">
               <label class="block text-sm font-medium text-yellow-800 mb-1">Monto Total Nómina</label>
               <input type="number" step="0.01" v-model.number="form.total_manual" class="w-full border-yellow-300 rounded text-lg font-bold" required>
               <p class="text-xs text-yellow-600 mt-1">Ingresa el total a pagar.</p>
             </div>
          </div>

        </form>
      </div>
      
      <!-- Footer -->
      <div class="px-6 py-4 border-t border-gray-200 bg-gray-50 flex justify-end gap-3 rounded-b-lg">
        <button type="button" @click="$emit('close')" class="px-4 py-2 bg-white border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50">
          Cancelar
        </button>
        <button type="submit" form="gastoForm" class="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 shadow-sm font-medium">
          {{ isEditing ? 'Guardar Cambios' : 'Registrar Gasto' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, watch } from 'vue'
import api from '@/api/client'
import SearchableSelect from './SearchableSelect.vue'

const props = defineProps<{
  initialData?: any
}>()

const emit = defineEmits(['close', 'save'])

const proveedores = ref<any[]>([])
const articulos = ref<any[]>([])

// Form state
const form = reactive({
  id: null,
  proveedor_id: null,
  fecha_gasto: new Date().toISOString().slice(0, 16), // YYYY-MM-DDTHH:mm
  tipo_gasto: 'directo',
  metodo_pago: 'efectivo',
  folio: '',
  descripcion: '',
  notas: '',
  total_manual: null as number | null,
  detalles: [] as any[]
})

const isEditing = computed(() => !!form.id)

const sumaDetalles = computed(() => {
  return form.detalles.reduce((sum, d) => sum + (d.cantidad * d.precio_unitario), 0)
})

// Loaders
const loadCatalogos = async () => {
  try {
    const [provs, arts] = await Promise.all([
      api.get('/gastos/proveedores'),
      api.get('/gastos/articulos')
    ])
    proveedores.value = provs.data
    articulos.value = arts.data
  } catch (e) { console.error(e) }
}

// Logic
const addDetalle = () => {
  form.detalles.push({ articulo_id: null, cantidad: 1, precio_unitario: 0 })
}

const removeDetalle = (idx: number) => {
  form.detalles.splice(idx, 1)
}

const submitForm = async () => {
  try {
    // Validar
    if (!form.proveedor_id) return alert('Selecciona un proveedor')
    
    // Preparar payload
    const payload = {
       ...form,
       // Asegurar fechas en ISO
       fecha_gasto: form.fecha_gasto ? new Date(form.fecha_gasto).toISOString() : null
    }

    // Limpiar detalles si es nomina
    if (form.tipo_gasto === 'nomina') {
       payload.detalles = []
    }

    if (isEditing.value) {
       await api.put(`/gastos/${form.id}`, payload)
    } else {
       await api.post('/gastos/', payload)
    }
    
    emit('save')
  } catch (e: any) {
    alert('Error al guardar: ' + (e.response?.data?.detail || e.message))
  }
}

// Init
onMounted(() => {
  loadCatalogos()
  if (props.initialData) {
    // Cargar datos existentes
    const d = props.initialData
    form.id = d.id
    form.proveedor_id = d.proveedor_id
    form.tipo_gasto = d.tipo_gasto
    form.metodo_pago = d.metodo_pago
    form.folio = d.folio
    form.descripcion = d.descripcion
    form.notas = d.notas
    form.total_manual = d.total_manual
    
    // Fecha: convertir ISO a datetime-local format (YYYY-MM-DDTHH:mm)
    if (d.fecha_gasto) {
       const dateObj = new Date(d.fecha_gasto)
       // Ajuste zona horaria local simple
       const tzOffset = dateObj.getTimezoneOffset() * 60000
       const localISOTime = (new Date(dateObj.getTime() - tzOffset)).toISOString().slice(0, 16)
       form.fecha_gasto = localISOTime
    }
    
    // Detalles
    if (d.detalles) {
       form.detalles = d.detalles.map((det: any) => ({
          articulo_id: det.articulo_id,
          cantidad: Number(det.cantidad),
          precio_unitario: Number(det.precio_unitario)
       }))
    }
  } else {
     addDetalle() // Una linea vacia por defecto
  }
})

</script>
