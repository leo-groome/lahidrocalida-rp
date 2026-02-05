<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <AppHeader title="Panel de Administración" />

    <!-- Navegación principal (3 pestañas) -->
    <div class="bg-white border-b border-gray-200 sticky top-0 z-20">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <nav class="flex space-x-8" aria-label="Tabs">
          <button
            v-for="tab in mainTabs"
            :key="tab.id"
            @click="activeMainTab = tab.id"
            :class="[
              activeMainTab === tab.id
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
              'whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center space-x-2'
            ]"
          >
            <span>{{ tab.icon }}</span>
            <span>{{ tab.name }}</span>
          </button>
        </nav>
      </div>
    </div>

    <!-- Contenido principal -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      
      <!-- TAB 1: ANALÍTICAS -->
      <div v-if="activeMainTab === 'analiticas'" class="space-y-6">
        <!-- Controles de Analíticas -->
        <div class="bg-white p-4 rounded-lg shadow flex flex-wrap items-center justify-between gap-4">
          <div class="flex items-center space-x-2">
            <h2 class="text-lg font-semibold text-gray-900">Analíticas</h2>
          </div>
          
          <div class="flex flex-wrap items-center gap-4">
            <!-- Selector de Rango Rápido -->
            <div class="flex bg-gray-100 rounded-lg p-1">
              <button 
                v-for="range in dateRanges" 
                :key="range.id"
                @click="setAnalyticsRange(range.id)"
                :class="[
                  'px-3 py-1.5 text-xs font-medium rounded-md transition-colors',
                  selectedRangeId === range.id 
                    ? 'bg-white text-blue-600 shadow-sm' 
                    : 'text-gray-600 hover:text-gray-900'
                ]"
              >
                {{ range.label }}
              </button>
            </div>

            <div class="h-6 w-px bg-gray-300"></div>

            <!-- Filtro Método Pago -->
            <div class="flex items-center space-x-2">
               <label class="text-xs text-gray-500">Pago:</label>
               <select v-model="selectedPaymentMethodFilter" @change="loadAnalytics" class="text-sm border-gray-300 rounded-md shadow-sm py-1.5 pl-2 pr-8">
                  <option value="todos">Todos</option>
                  <option value="efectivo">Efectivo</option>
                  <option value="tarjeta">Tarjeta</option>
                  <option value="transferencia">Transferencia</option>
               </select>
            </div>

            <div class="h-6 w-px bg-gray-300"></div>

            <!-- Selectores de Fecha Manuales -->
            <div class="flex items-center space-x-2">
              <input type="date" v-model="analyticsDates.start" class="text-sm border-gray-300 rounded-md shadow-sm" />
              <span class="text-gray-400">→</span>
              <input type="date" v-model="analyticsDates.end" class="text-sm border-gray-300 rounded-md shadow-sm" />
              <button 
                @click="loadAnalytics"
                :disabled="loadingAnalytics"
                class="px-3 py-1.5 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 disabled:opacity-50"
              >
                {{ loadingAnalytics ? '...' : 'Filtrar' }}
              </button>
            </div>
          </div>
        </div>

        <!-- KPIs Cards -->
        <div v-if="analyticsData" class="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div class="bg-white p-6 rounded-lg shadow border-l-4 border-green-500">
            <dt class="text-sm font-medium text-gray-500 truncate">Ventas Totales</dt>
            <dd class="mt-1 text-2xl font-semibold text-gray-900">${{ formatCurrency(analyticsData.resumen.total_ventas) }}</dd>
          </div>
          <div class="bg-white p-6 rounded-lg shadow border-l-4 border-red-500">
            <dt class="text-sm font-medium text-gray-500 truncate">Gastos Totales</dt>
            <dd class="mt-1 text-2xl font-semibold text-gray-900">${{ formatCurrency(analyticsData.resumen.total_gastos) }}</dd>
          </div>
          <div class="bg-white p-6 rounded-lg shadow border-l-4 border-blue-500">
            <dt class="text-sm font-medium text-gray-500 truncate">Utilidad Neta</dt>
            <dd class="mt-1 text-2xl font-semibold" :class="analyticsData.resumen.utilidad_neta >= 0 ? 'text-green-600' : 'text-red-600'">
              ${{ formatCurrency(analyticsData.resumen.utilidad_neta) }}
            </dd>
          </div>
          <div class="bg-white p-6 rounded-lg shadow border-l-4 border-purple-500">
            <dt class="text-sm font-medium text-gray-500 truncate">Ticket Promedio</dt>
            <dd class="mt-1 text-2xl font-semibold text-gray-900">${{ formatCurrency(analyticsData.resumen.ticket_promedio) }}</dd>
          </div>
        </div>

        <!-- Gráfico Principal -->
        <div v-if="analyticsData" class="bg-white p-6 rounded-lg shadow">
          <h3 class="text-lg font-medium text-gray-900 mb-4">Tendencia de Ingresos vs Egresos</h3>
          <div class="h-80 w-full">
            <Line :data="chartData" :options="chartOptions" />
          </div>
        </div>

        <!-- ANALÍTICAS AVANZADAS -->
        <div v-if="loadingAdvanced" class="py-12 flex justify-center">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
        
        <div v-else-if="advancedAnalyticsData" class="grid grid-cols-1 lg:grid-cols-2 gap-6">
           
           <!-- Top Platillos -->
           <div class="bg-white p-6 rounded-lg shadow lg:col-span-2">
             <h3 class="text-lg font-medium text-gray-900 mb-4">🏆 Top 10 Platillos Vendidos</h3>
             <div class="overflow-x-auto">
               <table class="min-w-full divide-y divide-gray-200">
                 <thead class="bg-gray-50">
                   <tr>
                     <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">#</th>
                     <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Platillo</th>
                     <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider text-right">Cantidad</th>
                     <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider text-right">Total Generado</th>
                   </tr>
                 </thead>
                 <tbody class="bg-white divide-y divide-gray-200">
                   <tr v-for="(item, index) in advancedAnalyticsData.top_platillos" :key="index">
                     <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ index + 1 }}</td>
                     <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{{ item.nombre }}</td>
                     <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-right">{{ item.cantidad }}</td>
                     <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-medium text-right">${{ formatCurrency(item.total) }}</td>
                   </tr>
                 </tbody>
               </table>
             </div>
           </div>

           <!-- Ventas por Categoría (Gráfico Circular) -->
           <div class="bg-white p-6 rounded-lg shadow">
             <h3 class="text-lg font-medium text-gray-900 mb-4">🍕 Ventas por Categoría</h3>
             <div class="h-64 flex justify-center">
                <Doughnut v-if="categoryChartData" :data="categoryChartData" :options="doughnutOptions" />
                <div v-else class="flex items-center text-gray-500">Sin datos disponibles</div>
             </div>
           </div>

           <!-- Top Meseros -->
           <div class="bg-white p-6 rounded-lg shadow">
             <h3 class="text-lg font-medium text-gray-900 mb-4">🤵 Rendimiento del Personal</h3>
             <ul class="divide-y divide-gray-200">
               <li v-for="(mesero, idx) in advancedAnalyticsData.top_meseros" :key="idx" class="py-4 flex justify-between items-center">
                 <div class="flex items-center">
                   <div class="flex-shrink-0 h-8 w-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-bold text-xs">
                     {{ mesero.nombre.charAt(0).toUpperCase() }}
                   </div>
                   <div class="ml-3">
                     <p class="text-sm font-medium text-gray-900">{{ mesero.nombre }}</p>
                     <p class="text-xs text-gray-500">{{ mesero.pedidos }} pedidos procesados</p>
                   </div>
                 </div>
                 <div class="text-sm font-semibold text-gray-900">${{ formatCurrency(mesero.total) }}</div>
               </li>
             </ul>
           </div>

        </div>

      </div>

      <!-- TAB 2: GASTOS (Mantenemos funcionalidad existente) -->
      <div v-if="activeMainTab === 'gastos'" class="space-y-6">
        <div class="mb-6">
          <div class="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 class="text-xl font-semibold text-gray-900">Gestión de Gastos</h2>
              <p class="text-sm text-gray-600 mt-1">Registra compras, proveedores y artículos.</p>
            </div>
            <div class="flex flex-wrap gap-2">
              <button @click="showAddGastoModal = true" class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">+ Nuevo Gasto</button>
              <button @click="openNewProveedor" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">+ Proveedor</button>
              <button @click="openNewArticulo" class="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">+ Artículo</button>
              <button @click="openNewCategoria" class="px-4 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-900">+ Categoría</button>
            </div>
          </div>
        </div>

        <!-- Subtabs de Gastos -->
        <div class="mb-6 flex flex-wrap gap-2">
           <button v-for="sub in gastosTabs" :key="sub.id"
             @click="gastosSubTab = sub.id"
             :class="['px-4 py-2 rounded-full text-sm font-medium', gastosSubTab === sub.id ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-700']"
           >
             {{ sub.name }}
           </button>
        </div>

        <!-- Contenido Subtabs Gastos -->
        <div v-if="gastosSubTab === 'dashboard'">
           <GastosDashboard @new-gasto="handleNewGasto" />
        </div>

        <div v-if="gastosSubTab === 'gastos'">
           <GastosHistorial 
             ref="gastosHistorialRef"
             @new-gasto="handleNewGasto"
             @edit-gasto="handleEditGasto"
           />
        </div>
        
        <!-- Proveedores, Articulos, Categorias (Simplificado para vista) -->
        <div v-if="gastosSubTab === 'proveedores'">
            <!-- Listado Proveedores Reuse -->
             <div class="bg-white shadow rounded-lg p-4">
                <div v-for="p in proveedoresList" :key="p.id" class="flex justify-between items-center py-3 border-b">
                   <div>
                      <div class="font-medium">{{ p.nombre }}</div>
                      <div class="text-xs text-gray-500">{{ p.telefono }}</div>
                   </div>
                   <button @click="editProveedor(p)" class="text-blue-600 text-sm">Editar</button>
                </div>
             </div>
        </div>
        
        <div v-if="gastosSubTab === 'articulos'">
             <div class="bg-white shadow rounded-lg p-4">
                <div class="mb-4">
                  <select v-model="selectedArticuloCategoria" @change="loadArticulos" class="border p-2 rounded w-full md:w-auto">
                    <option :value="null">Todas las categorías</option>
                    <option v-for="c in categoriasArticuloList" :key="c.id" :value="c.id">{{ c.nombre }}</option>
                  </select>
                </div>
                <div v-for="a in articulosList" :key="a.id" class="flex justify-between items-center py-3 border-b">
                   <div>
                      <div class="font-medium">{{ a.nombre }}</div>
                      <div class="text-xs text-gray-500">{{ a.categoria.nombre }} - Costo: ${{ a.costo_estandar }}</div>
                   </div>
                   <button @click="editArticulo(a)" class="text-indigo-600 text-sm">Editar</button>
                </div>
             </div>
        </div>
        
        <div v-if="gastosSubTab === 'categorias'">
             <div class="bg-white shadow rounded-lg p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                <div v-for="c in categoriasArticuloList" :key="c.id" class="flex justify-between items-center p-3 border rounded">
                   <span class="font-medium">{{ c.nombre }}</span>
                   <button @click="editCategoria(c)" class="text-gray-600 text-sm">Editar</button>
                </div>
             </div>
        </div>

      </div>

      <!-- TAB 3: AJUSTES -->
      <div v-if="activeMainTab === 'ajustes'" class="flex flex-col md:flex-row gap-6">
        <!-- Sidebar Ajustes -->
        <div class="w-full md:w-64 flex-shrink-0">
          <div class="bg-white shadow rounded-lg overflow-hidden">
            <nav class="flex flex-col">
              <button
                v-for="sub in ajustesTabs"
                :key="sub.id"
                @click="ajustesSubTab = sub.id"
                :class="[
                  'px-4 py-3 text-left text-sm font-medium border-l-4 transition-colors',
                  ajustesSubTab === sub.id 
                    ? 'bg-blue-50 border-blue-600 text-blue-700' 
                    : 'border-transparent text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                ]"
              >
                {{ sub.name }}
              </button>
            </nav>
          </div>
        </div>

        <!-- Contenido Ajustes -->
        <div class="flex-1 space-y-6">
           
           <!-- PLATILLOS -->
           <div v-if="ajustesSubTab === 'platillos'">
              <div class="flex justify-between items-center mb-4">
                <h3 class="text-xl font-bold text-gray-800">Menú y Platillos</h3>
                <button @click="openNewPlatilloModal" class="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 text-sm">Nuevo Platillo</button>
              </div>
              
              <!-- Filtro Categorias Platillos -->
              <div class="flex flex-wrap gap-2 mb-4">
                 <button @click="selectedCategory = null" :class="['px-3 py-1 rounded-full text-xs', !selectedCategory ? 'bg-blue-600 text-white' : 'bg-gray-200']">Todas</button>
                 <button v-for="cat in categories" :key="cat" @click="selectedCategory = cat" :class="['px-3 py-1 rounded-full text-xs capitalize', selectedCategory === cat ? 'bg-blue-600 text-white' : 'bg-gray-200']">
                   {{ cat }}
                 </button>
              </div>

              <div class="bg-white shadow rounded-lg overflow-hidden">
                <ul class="divide-y divide-gray-200">
                  <li v-for="platillo in filteredPlatillos" :key="platillo.id" class="px-6 py-4 flex justify-between items-center hover:bg-gray-50">
                     <div>
                        <div class="font-medium text-gray-900">{{ platillo.nombre }}</div>
                        <div class="text-sm text-gray-500">{{ platillo.descripcion }}</div>
                        <div class="text-xs text-gray-400 mt-1">${{ platillo.precio }} | {{ platillo.categoria }}</div>
                     </div>
                     <div class="flex space-x-2">
                        <button @click="editPlatillo(platillo)" class="text-blue-600 hover:underline text-sm">Editar</button>
                        <button @click="deletePlatillo(platillo.id, platillo.nombre)" class="text-red-600 hover:underline text-sm">Eliminar</button>
                     </div>
                  </li>
                </ul>
              </div>
           </div>

           <!-- USUARIOS -->
           <div v-if="ajustesSubTab === 'usuarios'">
              <div class="flex justify-between items-center mb-4">
                <h3 class="text-xl font-bold text-gray-800">Usuarios del Sistema</h3>
                <button @click="openNewUsuarioModal" class="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 text-sm">Nuevo Usuario</button>
              </div>
              
              <div class="bg-white shadow rounded-lg overflow-hidden">
                <ul class="divide-y divide-gray-200">
                  <li v-for="user in usuariosList" :key="user.id" class="px-6 py-4 flex justify-between items-center">
                     <div>
                        <div class="font-medium">{{ user.nombre }}</div>
                        <div class="text-xs text-gray-500 capitalize">{{ user.rol }} - {{ user.activo ? 'Activo' : 'Inactivo' }}</div>
                     </div>
                     <div class="flex space-x-2">
                        <button @click="editUsuario(user)" class="text-blue-600 text-sm">Editar</button>
                     </div>
                  </li>
                </ul>
              </div>
           </div>

           <!-- CONFIGURACION -->
           <div v-if="ajustesSubTab === 'configuracion'" class="space-y-6">
              <!-- Impresoras -->
              <div class="bg-white shadow rounded-lg p-6">
                <h3 class="text-lg font-medium text-gray-900 mb-4">🖨️ Impresión</h3>
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                   <div class="border rounded p-4">
                      <div class="text-sm text-gray-600 mb-2">Estado Servidor: <span :class="printServiceStatus === 'online' ? 'text-green-600' : 'text-red-600'">{{ printServiceStatus }}</span></div>
                      <button @click="testPrintService" class="text-xs bg-gray-200 px-2 py-1 rounded">Verificar Conexión</button>
                   </div>
                   <form @submit.prevent="savePrintConfig" class="border rounded p-4 space-y-2">
                      <div>
                        <label class="text-xs font-medium">Host</label>
                        <input v-model="printConfig.host" class="w-full border rounded text-sm px-2 py-1">
                      </div>
                      <div>
                        <label class="text-xs font-medium">Puerto</label>
                        <input v-model.number="printConfig.port" type="number" class="w-full border rounded text-sm px-2 py-1">
                      </div>
                      <div class="flex items-center">
                        <input v-model="printConfig.autoprint" type="checkbox" class="mr-2">
                        <span class="text-sm">Auto-impresión</span>
                      </div>
                      <button type="submit" class="w-full bg-blue-600 text-white text-sm py-1 rounded">Guardar</button>
                   </form>
                </div>
              </div>

              <!-- Horarios -->
              <div class="bg-white shadow rounded-lg p-6">
                 <h3 class="text-lg font-medium text-gray-900 mb-4">🕐 Horarios</h3>
                 <form @submit.prevent="saveGeneralConfig" class="grid grid-cols-2 gap-4">
                    <div>
                      <label class="text-sm text-gray-600">Apertura</label>
                      <input v-model="generalConfig.horario_apertura" type="time" class="w-full border rounded p-1">
                    </div>
                    <div>
                      <label class="text-sm text-gray-600">Cierre</label>
                      <input v-model="generalConfig.horario_cierre" type="time" class="w-full border rounded p-1">
                    </div>
                    <div class="col-span-2">
                       <button type="submit" class="bg-purple-600 text-white px-4 py-2 rounded text-sm">Actualizar Horarios</button>
                    </div>
                 </form>
              </div>
           </div>
        </div>
      </div>

    </div>

    <!-- MODALES GLOBALEs -->
    <AdminModals
      :show-platillo-modal="showPlatilloModal"
      :show-usuario-modal="showUsuarioModal"
      :editing-platillo="editingPlatillo"
      :editing-usuario="editingUsuario"
      @close-platillo-modal="closePlatilloModal"
      @close-usuario-modal="closeUsuarioModal"
      @save-platillo="savePlatillo"
      @save-usuario="saveUsuario"
    />

    <!-- Modal Gasto NUEVO -->
    <GastoFormModal
      v-if="showGastoModal"
      :initial-data="editingGastoData"
      @close="showGastoModal = false"
      @save="handleGastoSaved"
    />
    
    <!-- Otros Modales (Proveedor, Articulo, Categoria) se mantienen con lógica similar -->
    <div v-if="showProveedorModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
       <div class="bg-white p-6 rounded w-96">
          <h3 class="font-bold mb-4">Proveedor</h3>
          <input v-model="proveedorForm.nombre" placeholder="Nombre" class="w-full border p-2 mb-2 rounded">
          <input v-model="proveedorForm.telefono" placeholder="Teléfono" class="w-full border p-2 mb-2 rounded">
          <input v-model="proveedorForm.direccion" placeholder="Dirección" class="w-full border p-2 mb-2 rounded">
          <textarea v-model="proveedorForm.notas" placeholder="Notas" class="w-full border p-2 mb-2 rounded" rows="3"></textarea>
          <div class="flex justify-end gap-2">
             <button @click="showProveedorModal = false" class="bg-gray-200 px-3 py-1 rounded">Cancelar</button>
             <button @click="saveProveedor" class="bg-blue-600 text-white px-3 py-1 rounded">Guardar</button>
          </div>
       </div>
    </div>
    
    <div v-if="showArticuloModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
       <div class="bg-white p-6 rounded w-96">
          <h3 class="font-bold mb-4">Artículo</h3>
          <input v-model="articuloForm.nombre" placeholder="Nombre" class="w-full border p-2 mb-2 rounded">
          <select v-model="articuloForm.categoria_id" class="w-full border p-2 mb-2 rounded">
             <option :value="null">Categoría...</option>
             <option v-for="c in categoriasArticuloList" :key="c.id" :value="c.id">{{ c.nombre }}</option>
          </select>
          <select v-model="articuloForm.unidad" class="w-full border p-2 mb-2 rounded">
             <option value="kg">Kilogramos (kg)</option>
             <option value="g">Gramos (g)</option>
             <option value="lt">Litros (lt)</option>
             <option value="ml">Mililitros (ml)</option>
             <option value="pza">Piezas (pza)</option>
             <option value="caja">Caja</option>
             <option value="paq">Paquete (paq)</option>
          </select>
          <input v-model.number="articuloForm.costo_estandar" type="number" placeholder="Costo Estándar" class="w-full border p-2 mb-2 rounded">
          <div class="flex justify-end gap-2">
             <button @click="showArticuloModal = false" class="bg-gray-200 px-3 py-1 rounded">Cancelar</button>
             <button @click="saveArticulo" class="bg-indigo-600 text-white px-3 py-1 rounded">Guardar</button>
          </div>
       </div>
    </div>
    
    <div v-if="showCategoriaModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
       <div class="bg-white p-6 rounded w-96">
          <h3 class="font-bold mb-4">Categoría Artículo</h3>
          <input v-model="categoriaForm.nombre" placeholder="Nombre" class="w-full border p-2 mb-2 rounded">
          <div class="flex justify-end gap-2">
             <button @click="showCategoriaModal = false" class="bg-gray-200 px-3 py-1 rounded">Cancelar</button>
             <button @click="saveCategoria" class="bg-gray-800 text-white px-3 py-1 rounded">Guardar</button>
          </div>
       </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { parseSafeDate } from '@/utils/dateUtils'
import api from '@/api/client'
import AppHeader from '@/components/AppHeader.vue'
import AdminModals from '@/components/AdminModals.vue'
import GastosDashboard from '@/components/gastos/GastosDashboard.vue'
import GastosHistorial from '@/components/gastos/GastosHistorial.vue'
import GastoFormModal from '@/components/gastos/GastoFormModal.vue'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  ArcElement, // Importado para Doughnut
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'
import { Line, Doughnut } from 'vue-chartjs' // Importado Doughnut

// Registro de componentes Chart.js
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

const auth = useAuthStore()
const router = useRouter()

// Permisos
if (auth.user?.rol !== 'administrador') {
  router.replace({ name: 'login' })
}

// --- PESTAÑAS PRINCIPALES ---
const mainTabs = [
  { id: 'analiticas', name: 'Analíticas', icon: '📊' },
  { id: 'gastos', name: 'Gastos', icon: '💰' },
  { id: 'ajustes', name: 'Ajustes', icon: '⚙️' }
]
const activeMainTab = ref('analiticas')

// --- PESTAÑAS SUB-NIVELES ---
const gastosTabs = [
  { id: 'dashboard', name: 'Dashboard' },
  { id: 'gastos', name: 'Historial' },
  { id: 'proveedores', name: 'Proveedores' },
  { id: 'articulos', name: 'Artículos' },
  { id: 'categorias', name: 'Cat. Artículos' }
]
const gastosSubTab = ref('dashboard')

const showGastoModal = ref(false)
const editingGastoData = ref(null)
const gastosHistorialRef = ref(null) // Para recargar tabla

const handleNewGasto = () => {
  editingGastoData.value = null
  showGastoModal.value = true
}

const handleEditGasto = (gasto: any) => {
  editingGastoData.value = gasto
  showGastoModal.value = true
}

const handleGastoSaved = () => {
  showGastoModal.value = false
  // Recargar tabla si existe ref
  if (gastosHistorialRef.value) {
    (gastosHistorialRef.value as any).loadGastos()
  }
}

const ajustesTabs = [
  { id: 'platillos', name: 'Menú & Platillos' },
  { id: 'usuarios', name: 'Usuarios' },
  { id: 'configuracion', name: 'Sistema & Impresión' }
]
const ajustesSubTab = ref('platillos')


// ==========================================
// 1. LÓGICA ANALÍTICAS
// ==========================================
const loadingAnalytics = ref(false)
const loadingAdvanced = ref(false) // Nueva variable de carga
const analyticsData = ref<any>(null)
const advancedAnalyticsData = ref<any>(null) // Nueva variable para datos avanzados

const analyticsDates = ref({
  start: new Date().toISOString().split('T')[0],
  end: new Date().toISOString().split('T')[0]
})
const selectedRangeId = ref('today')
const selectedPaymentMethodFilter = ref('todos') // Nuevo filtro

const dateRanges = [
  { id: 'today', label: 'Hoy' },
  { id: 'week', label: 'Esta Semana' },
  { id: 'month', label: 'Este Mes' },
  { id: 'year', label: 'Este Año' }
]

const setAnalyticsRange = (rangeId: string) => {
  selectedRangeId.value = rangeId
  const today = new Date()
  let start = new Date()
  let end = new Date()

  if (rangeId === 'today') {
    // start y end son today
  } else if (rangeId === 'week') {
    // Lunes a Domingo de la semana actual
    const day = today.getDay()
    const diff = today.getDate() - day + (day === 0 ? -6 : 1) // adjust when day is sunday
    start = new Date(today.setDate(diff))
    end = new Date(today.setDate(start.getDate() + 6))
  } else if (rangeId === 'month') {
    start = new Date(today.getFullYear(), today.getMonth(), 1)
    end = new Date(today.getFullYear(), today.getMonth() + 1, 0)
  } else if (rangeId === 'year') {
    start = new Date(today.getFullYear(), 0, 1)
    end = new Date(today.getFullYear(), 11, 31)
  }

  analyticsDates.value.start = start.toISOString().split('T')[0]
  analyticsDates.value.end = end.toISOString().split('T')[0]
  loadAnalytics()
}

const loadAnalytics = async () => {
  loadingAnalytics.value = true
  loadingAdvanced.value = true
  
  // Limpiar datos previos
  analyticsData.value = null
  advancedAnalyticsData.value = null

  try {
    const { start, end } = analyticsDates.value
    let url = `/admin/analytics?fecha_inicio=${start}&fecha_fin=${end}`
    if (selectedPaymentMethodFilter.value !== 'todos') {
       url += `&metodo_pago=${selectedPaymentMethodFilter.value}`
    }
    
    // Carga básica primero
    const response = await api.get(url)
    analyticsData.value = response.data
    loadingAnalytics.value = false // Termina carga básica

    // Carga avanzada en segundo plano
    let advancedUrl = `/admin/analytics/advanced?fecha_inicio=${start}&fecha_fin=${end}`
    if (selectedPaymentMethodFilter.value !== 'todos') {
       advancedUrl += `&metodo_pago=${selectedPaymentMethodFilter.value}`
    }
    const advancedResponse = await api.get(advancedUrl)
    advancedAnalyticsData.value = advancedResponse.data

  } catch (err) {
    console.error('Error loading analytics', err)
  } finally {
    loadingAnalytics.value = false
    loadingAdvanced.value = false
  }
}

// Configuración de Chart.js
const chartData = computed(() => {
  if (!analyticsData.value) return { labels: [], datasets: [] }
  
  const timeline = analyticsData.value.timeline
  const labels = timeline.map((d: any) => {
    const date = parseSafeDate(d.fecha)
    return date ? date.toLocaleDateString(undefined, { day: 'numeric', month: 'short' }) : ''
  })
  
  return {
    labels,
    datasets: [
      {
        label: 'Ventas',
        backgroundColor: 'rgba(59, 130, 246, 0.2)',
        borderColor: '#3b82f6',
        data: timeline.map((d: any) => d.ventas),
        fill: true,
        tension: 0.4
      },
      {
        label: 'Gastos',
        backgroundColor: 'rgba(239, 68, 68, 0.2)',
        borderColor: '#ef4444',
        data: timeline.map((d: any) => d.gastos),
        fill: true,
        tension: 0.4
      }
    ]
  }
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'top' as const }
  },
  scales: {
    y: {
      beginAtZero: true,
      ticks: {
         callback: function(value: any) { return '$' + value }
      }
    }
  }
}

// Chart Circular para Categorias
const categoryChartData = computed(() => {
   if (!advancedAnalyticsData.value?.ventas_categoria?.length) return null
   const data = advancedAnalyticsData.value.ventas_categoria
   return {
      labels: data.map((d: any) => d.categoria),
      datasets: [{
         data: data.map((d: any) => d.total),
         backgroundColor: ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#6366F1'],
         borderWidth: 0
      }]
   }
})

const doughnutOptions = {
   responsive: true,
   maintainAspectRatio: false,
   plugins: {
      legend: { position: 'right' as const }
   }
}


// ==========================================
// 2. LÓGICA GASTOS (Migrada a Componentes)
// ==========================================
// Variables de estado para sub-tabs de proveedores/artículos (aún en AdminView)
const proveedoresList = ref<any[]>([])
const categoriasArticuloList = ref<any[]>([])
const articulosList = ref<any[]>([])

const showProveedorModal = ref(false)
const showArticuloModal = ref(false)
const showCategoriaModal = ref(false)

const proveedorForm = ref({ nombre: '', telefono: '', direccion: '', notas: '' })
const articuloForm = ref({ nombre: '', unidad: 'kg', costo_estandar: 0, categoria_id: null })
const categoriaForm = ref({ nombre: '' })

const editingProveedor = ref<any>(null)
const editingArticulo = ref<any>(null)
const editingCategoria = ref<any>(null)
const selectedArticuloCategoria = ref(null)


// -- Fetchers Proveedores/Artículos --
const loadProveedores = async () => {
  try {
    const res = await api.get('/gastos/proveedores')
    proveedoresList.value = res.data
  } catch (e) { console.error(e) }
}

const loadCategoriasArticulo = async () => {
  try {
    const res = await api.get('/gastos/categorias-articulo')
    categoriasArticuloList.value = res.data
  } catch (e) { console.error(e) }
}

const loadArticulos = async () => {
  try {
    const params: any = {}
    if (selectedArticuloCategoria.value) params.categoria_id = selectedArticuloCategoria.value
    const res = await api.get('/gastos/articulos', { params })
    articulosList.value = res.data
  } catch (e) { console.error(e) }
}


// -- Actions Proveedores/Artículos/Categorías --
const openNewProveedor = () => { editingProveedor.value = null; proveedorForm.value = { nombre:'', telefono:'', direccion:'', notas:'' }; showProveedorModal.value = true }
const editProveedor = (p: any) => { editingProveedor.value = p; proveedorForm.value = { ...p }; showProveedorModal.value = true }
const saveProveedor = async () => {
   if(editingProveedor.value) await api.put(`/gastos/proveedores/${editingProveedor.value.id}`, proveedorForm.value)
   else await api.post('/gastos/proveedores', proveedorForm.value)
   showProveedorModal.value = false; loadProveedores()
}

const openNewArticulo = () => { editingArticulo.value = null; articuloForm.value = { nombre:'', unidad:'kg', costo_estandar:0, categoria_id:null }; showArticuloModal.value = true }
const editArticulo = (a: any) => { editingArticulo.value = a; articuloForm.value = { ...a }; showArticuloModal.value = true }
const saveArticulo = async () => {
   const payload = { ...articuloForm.value, categoria_id: Number(articuloForm.value.categoria_id) }
   if(editingArticulo.value) await api.put(`/gastos/articulos/${editingArticulo.value.id}`, payload)
   else await api.post('/gastos/articulos', payload)
   showArticuloModal.value = false; loadArticulos()
}

const openNewCategoria = () => { editingCategoria.value = null; categoriaForm.value = { nombre:'' }; showCategoriaModal.value = true }
const editCategoria = (c: any) => { editingCategoria.value = c; categoriaForm.value = { ...c }; showCategoriaModal.value = true }
const saveCategoria = async () => {
   if(editingCategoria.value) await api.put(`/gastos/categorias-articulo/${editingCategoria.value.id}`, categoriaForm.value)
   else await api.post('/gastos/categorias-articulo', categoriaForm.value)
   showCategoriaModal.value = false; loadCategoriasArticulo()
}


// ==========================================
// 3. LÓGICA AJUSTES (Platillos, Usuarios, Config)
// ==========================================
const platillosList = ref<any[]>([])
const usuariosList = ref<any[]>([])
const categories = ref<string[]>([])
const selectedCategory = ref<string | null>(null)

const showPlatilloModal = ref(false)
const showUsuarioModal = ref(false)
const editingPlatillo = ref<any>(null)
const editingUsuario = ref<any>(null)

const printConfig = ref({ host: 'localhost', port: 3001, autoprint: true })
const generalConfig = ref({ horario_apertura: '08:00', horario_cierre: '22:00', timezone: 'America/Mexico_City' })
const printServiceStatus = ref('offline')

// Fetchers Ajustes
const loadPlatillos = async () => {
   const res = await api.get('/platillos')
   platillosList.value = res.data
   // Extract unique categories
   categories.value = [...new Set(res.data.map((p: any) => p.categoria))] as string[]
}

const loadUsuarios = async () => {
   const res = await api.get('/users')
   usuariosList.value = res.data
}

const filteredPlatillos = computed(() => {
   if(!selectedCategory.value) return platillosList.value
   return platillosList.value.filter(p => p.categoria === selectedCategory.value)
})

// Actions Ajustes
const openNewPlatilloModal = () => { editingPlatillo.value = null; showPlatilloModal.value = true }
const editPlatillo = (p: any) => { editingPlatillo.value = p; showPlatilloModal.value = true }
const deletePlatillo = async (id: number, nombre: string) => {
   if(confirm(`¿Eliminar ${nombre}?`)) {
      await api.delete(`/platillos/${id}`)
      loadPlatillos()
   }
}
const closePlatilloModal = () => { showPlatilloModal.value = false }
const savePlatillo = async (data: any) => {
   if(editingPlatillo.value) await api.put(`/platillos/${editingPlatillo.value.id}`, data)
   else await api.post('/platillos', data)
   closePlatilloModal(); loadPlatillos()
}

const openNewUsuarioModal = () => { editingUsuario.value = null; showUsuarioModal.value = true }
const editUsuario = (u: any) => { editingUsuario.value = u; showUsuarioModal.value = true }
const closeUsuarioModal = () => { showUsuarioModal.value = false }
const saveUsuario = async (data: any) => {
   if(editingUsuario.value) await api.put(`/users/${editingUsuario.value.id}`, data)
   else await api.post('/users', data)
   closeUsuarioModal(); loadUsuarios()
}

// Config Actions
const savePrintConfig = () => {
   localStorage.setItem('print_config', JSON.stringify(printConfig.value))
   alert('Configuración de impresión guardada (Local)')
}
const saveGeneralConfig = () => {
   alert('Configuración general guardada (Simulado)')
}
const testPrintService = async () => {
   try {
      await fetch(`http://${printConfig.value.host}:${printConfig.value.port}/health`)
      printServiceStatus.value = 'online'
   } catch {
      printServiceStatus.value = 'offline'
   }
}


// Helpers Globales
const formatCurrency = (val: any) => {
  const n = Number(val)
  return isNaN(n) ? '0.00' : n.toFixed(2)
}
const getPaymentMethodIcon = (m: string) => {
   if(m === 'efectivo') return '💵'
   if(m === 'tarjeta') return '💳'
   return '💰'
}


// INIT
onMounted(() => {
   // Cargar datos iniciales según tab por defecto
   setAnalyticsRange('today')
   loadPlatillos()
   loadUsuarios()
   loadProveedores()
   loadCategoriasArticulo()
   loadArticulos()
   
   // Cargar config local
   const savedPrint = localStorage.getItem('print_config')
   if(savedPrint) printConfig.value = JSON.parse(savedPrint)
   testPrintService()
})

// Watchers para cargar datos al cambiar de tab si fuera necesario optimizar
watch(activeMainTab, (newTab) => {
   // if(newTab === 'gastos') loadGastosList() // ERROR: Function not defined
   if(newTab === 'analiticas') loadAnalytics()
})
</script>
