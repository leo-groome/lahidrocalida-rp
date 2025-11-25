<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <AppHeader title="Panel de Administración" />

    <!-- Navegación de pestañas -->
    <div class="bg-white border-b border-gray-200">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <nav class="flex space-x-8" aria-label="Tabs">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="activeTab = tab.id"
            :class="[
              activeTab === tab.id
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
              'whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm'
            ]"
          >
            {{ tab.name }}
          </button>
        </nav>
      </div>
    </div>

    <!-- Contenido principal -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Tab: Dashboard -->
      <div v-if="activeTab === 'dashboard'">
        <div class="mb-6">
          <div class="flex justify-between items-center">
            <h2 class="text-xl font-semibold text-gray-900">Dashboard - Hoy</h2>
            <button
              @click="refreshDashboard"
              :disabled="loadingDashboard"
              class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {{ loadingDashboard ? 'Actualizando...' : 'Actualizar' }}
            </button>
          </div>
        </div>

        <!-- Métricas del día -->
        <div v-if="dashboardData" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <!-- Total Pedidos -->
          <div class="bg-white overflow-hidden shadow rounded-lg">
            <div class="p-5">
              <div class="flex items-center">
                <div class="flex-shrink-0">
                  <div class="w-8 h-8 bg-blue-500 rounded-md flex items-center justify-center">
                    <span class="text-white text-sm font-bold">#</span>
                  </div>
                </div>
                <div class="ml-5 w-0 flex-1">
                  <dl>
                    <dt class="text-sm font-medium text-gray-500 truncate">Total Pedidos</dt>
                    <dd class="text-lg font-medium text-gray-900">{{ dashboardData.total_pedidos }}</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <!-- Total Efectivo -->
          <div class="bg-white overflow-hidden shadow rounded-lg">
            <div class="p-5">
              <div class="flex items-center">
                <div class="flex-shrink-0">
                  <div class="w-8 h-8 bg-green-500 rounded-md flex items-center justify-center">
                    <span class="text-white text-sm font-bold">$</span>
                  </div>
                </div>
                <div class="ml-5 w-0 flex-1">
                  <dl>
                    <dt class="text-sm font-medium text-gray-500 truncate">Efectivo</dt>
                    <dd class="text-lg font-medium text-gray-900">${{ dashboardData.ingresos.efectivo.toFixed(2) }}</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <!-- Total Tarjeta -->
          <div class="bg-white overflow-hidden shadow rounded-lg">
            <div class="p-5">
              <div class="flex items-center">
                <div class="flex-shrink-0">
                  <div class="w-8 h-8 bg-purple-500 rounded-md flex items-center justify-center">
                    <span class="text-white text-sm font-bold">💳</span>
                  </div>
                </div>
                <div class="ml-5 w-0 flex-1">
                  <dl>
                    <dt class="text-sm font-medium text-gray-500 truncate">Tarjeta</dt>
                    <dd class="text-lg font-medium text-gray-900">${{ dashboardData.ingresos.tarjeta.toFixed(2) }}</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <!-- Total -->
          <div class="bg-white overflow-hidden shadow rounded-lg">
            <div class="p-5">
              <div class="flex items-center">
                <div class="flex-shrink-0">
                  <div class="w-8 h-8 bg-yellow-500 rounded-md flex items-center justify-center">
                    <span class="text-white text-sm font-bold">💰</span>
                  </div>
                </div>
                <div class="ml-5 w-0 flex-1">
                  <dl>
                    <dt class="text-sm font-medium text-gray-500 truncate">Total Ingresos</dt>
                    <dd class="text-lg font-medium text-gray-900">${{ dashboardData.ingresos.total.toFixed(2) }}</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <!-- Ticket Promedio -->
          <div class="bg-white overflow-hidden shadow rounded-lg">
            <div class="p-5">
              <div class="flex items-center">
                <div class="flex-shrink-0">
                  <div class="w-8 h-8 bg-indigo-500 rounded-md flex items-center justify-center">
                    <span class="text-white text-sm font-bold">🎫</span>
                  </div>
                </div>
                <div class="ml-5 w-0 flex-1">
                  <dl>
                    <dt class="text-sm font-medium text-gray-500 truncate">Ticket Promedio</dt>
                    <dd class="text-lg font-medium text-gray-900">${{ dashboardData.promedio_ticket.toFixed(2) }}</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <!-- Cancelaciones (si hay) -->
          <div v-if="dashboardData.cancelaciones > 0" class="bg-red-50 overflow-hidden shadow rounded-lg border border-red-200">
            <div class="p-5">
              <div class="flex items-center">
                <div class="flex-shrink-0">
                  <div class="w-8 h-8 bg-red-500 rounded-md flex items-center justify-center">
                    <span class="text-white text-sm font-bold">🚫</span>
                  </div>
                </div>
                <div class="ml-5 w-0 flex-1">
                  <dl>
                    <dt class="text-sm font-medium text-red-700 truncate">Cancelaciones</dt>
                    <dd class="text-lg font-medium text-red-900">{{ dashboardData.cancelaciones }}</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Nuevas Secciones: Gráficas y Estado -->
        <div v-if="dashboardData" class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
            <!-- Ventas por Hora -->
            <div class="lg:col-span-2 bg-white shadow rounded-lg p-6">
                <h3 class="text-lg font-medium text-gray-900 mb-4">⏰ Ventas por Hora</h3>
                <div class="h-64 flex items-end justify-between space-x-1">
                    <div v-for="hora in 24" :key="hora" class="flex flex-col items-center flex-1 h-full justify-end group">
                         <div class="w-full bg-blue-100 rounded-t hover:bg-blue-200 transition-all relative"
                              :style="{ height: `${Math.max(getPorcentajeHora(hora-1), 5)}%` }">
                              <!-- Tooltip -->
                              <div class="opacity-0 group-hover:opacity-100 absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2 bg-gray-800 text-white text-xs rounded py-1 px-2 whitespace-nowrap z-10 pointer-events-none">
                                {{ hora-1 }}:00 - {{ getDataHora(hora-1).cantidad }} pedidos (${{ getDataHora(hora-1).total }})
                              </div>
                         </div>
                         <span class="text-[10px] text-gray-500 mt-1">{{ hora-1 }}h</span>
                    </div>
                </div>
            </div>

            <!-- Estado y Tipos -->
            <div class="space-y-6">
                <!-- Estado en Vivo -->
                <div class="bg-white shadow rounded-lg p-6">
                    <h3 class="text-lg font-medium text-gray-900 mb-4">🟢 Estado en Vivo</h3>
                    <div class="space-y-3">
                        <div v-for="estado in ['pendiente', 'preparando', 'listo', 'entregado']" :key="estado" 
                             class="flex justify-between items-center">
                            <span class="capitalize text-sm text-gray-600">{{ estado }}</span>
                            <span class="px-3 py-1 rounded-full text-sm font-bold"
                                  :class="{
                                    'bg-red-100 text-red-800': estado === 'pendiente',
                                    'bg-yellow-100 text-yellow-800': estado === 'preparando',
                                    'bg-green-100 text-green-800': estado === 'listo',
                                    'bg-blue-100 text-blue-800': estado === 'entregado'
                                  }">
                                {{ getCantidadEstado(estado) }}
                            </span>
                        </div>
                    </div>
                </div>

                <!-- Tipos de Orden -->
                <div class="bg-white shadow rounded-lg p-6">
                    <h3 class="text-lg font-medium text-gray-900 mb-4">📊 Tipos de Orden</h3>
                    <div class="space-y-4">
                        <div v-for="tipo in dashboardData.tipos_orden" :key="tipo.tipo">
                            <div class="flex justify-between text-sm mb-1">
                                <span class="capitalize">{{ tipo.tipo.replace('_', ' ') }}</span>
                                <span class="font-medium">{{ tipo.cantidad }}</span>
                            </div>
                            <div class="w-full bg-gray-200 rounded-full h-2">
                                <div class="bg-blue-600 h-2 rounded-full"
                                     :style="{ width: `${(tipo.cantidad / dashboardData.total_pedidos) * 100}%` }"></div>
                            </div>
                        </div>
                        <div v-if="dashboardData.tipos_orden.length === 0" class="text-sm text-gray-500 text-center">
                          Sin datos aún
                        </div>
                    </div>
                </div>
            </div>
        </div>
      </div>

      <!-- Tab: Reportes -->
      <div v-if="activeTab === 'reportes'">
        <div class="mb-6">
          <div class="flex justify-between items-center">
            <h2 class="text-xl font-semibold text-gray-900">Reportes Semanales</h2>
            <div class="flex space-x-4 items-center">
              <input
                v-model="selectedWeekDate"
                type="date"
                class="px-3 py-2 border border-gray-300 rounded-md"
              />
              <button
                @click="loadWeeklyReport"
                :disabled="loadingWeekly"
                class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {{ loadingWeekly ? 'Cargando...' : 'Cargar Reporte' }}
              </button>
            </div>
          </div>
        </div>

        <!-- Reporte semanal -->
        <div v-if="weeklyData" class="space-y-6">
          <!-- Resumen principal -->
          <div class="bg-white shadow rounded-lg p-6">
            <h3 class="text-lg font-medium text-gray-900 mb-4">
              {{ weeklyData.periodo.descripcion }}
            </h3>
            
            <div class="grid grid-cols-2 md:grid-cols-5 gap-6">
              <div>
                <dt class="text-sm font-medium text-gray-500">Pedidos Pagados</dt>
                <dd class="mt-1 text-2xl font-semibold text-gray-900">{{ weeklyData.resumen.total_pedidos }}</dd>
              </div>
              <div>
                <dt class="text-sm font-medium text-gray-500">Total Ingresos</dt>
                <dd class="mt-1 text-2xl font-semibold text-green-600">${{ weeklyData.ingresos.total.toFixed(2) }}</dd>
              </div>
              <div>
                <dt class="text-sm font-medium text-gray-500">Promedio Ticket</dt>
                <dd class="mt-1 text-2xl font-semibold text-blue-600">${{ weeklyData.resumen.promedio_ticket.toFixed(2) }}</dd>
              </div>
              <div>
                <dt class="text-sm font-medium text-gray-500">Tasa Cancelación</dt>
                <dd class="mt-1 text-2xl font-semibold text-red-600">{{ weeklyData.resumen.tasa_cancelacion }}%</dd>
              </div>
              <div>
                <dt class="text-sm font-medium text-gray-500">Utilidad Bruta</dt>
                <dd class="mt-1 text-2xl font-semibold text-purple-600">${{ weeklyData.utilidad_bruta.toFixed(2) }}</dd>
              </div>
            </div>
          </div>

          <!-- Ventas por día -->
          <div class="bg-white shadow rounded-lg p-6">
            <h4 class="text-lg font-medium text-gray-900 mb-4">Ventas por Día</h4>
            <div class="overflow-x-auto">
              <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                  <tr>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Fecha</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Pedidos</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Ingresos</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Ticket Promedio</th>
                  </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                  <tr v-for="dia in weeklyData.ventas_por_dia" :key="dia.fecha">
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {{ new Date(dia.fecha).toLocaleDateString('es-ES', { weekday: 'short', day: 'numeric', month: 'short' }) }}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ dia.pedidos }}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${{ dia.total.toFixed(2) }}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${{ dia.promedio_ticket_dia.toFixed(2) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Análisis por tipo de orden -->
          <div class="bg-white shadow rounded-lg p-6">
            <h4 class="text-lg font-medium text-gray-900 mb-4">Análisis por Tipo de Orden</h4>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div v-for="tipo in weeklyData.analisis_tipos_orden" :key="tipo.tipo" 
                   class="border border-gray-200 rounded-lg p-4">
                <div class="flex items-center justify-between mb-2">
                  <h5 class="text-sm font-medium text-gray-900 capitalize">{{ getTipoOrdenLabel(tipo.tipo) }}</h5>
                  <span class="text-2xl">{{ getTipoOrdenEmoji(tipo.tipo) }}</span>
                </div>
                <div class="space-y-1">
                  <div class="flex justify-between text-sm">
                    <span class="text-gray-500">Pedidos:</span>
                    <span class="font-medium">{{ tipo.cantidad }} ({{ tipo.porcentaje_pedidos }}%)</span>
                  </div>
                  <div class="flex justify-between text-sm">
                    <span class="text-gray-500">Ingresos:</span>
                    <span class="font-medium">${{ tipo.ingresos.toFixed(2) }} ({{ tipo.porcentaje_ingresos }}%)</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Top productos y gastos por categoría -->
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <!-- Top productos -->
            <div class="bg-white shadow rounded-lg p-6">
              <h4 class="text-lg font-medium text-gray-900 mb-4">Top 10 Productos</h4>
              <div class="space-y-3">
                <div v-for="(producto, index) in weeklyData.productos_mas_vendidos" :key="producto.nombre"
                     class="flex justify-between items-center py-2 border-b border-gray-100 last:border-b-0">
                  <div class="flex items-center space-x-3">
                    <span class="flex items-center justify-center w-6 h-6 rounded-full text-xs font-medium"
                          :class="index < 3 ? 'bg-yellow-100 text-yellow-800' : 'bg-gray-100 text-gray-600'">
                      {{ index + 1 }}
                    </span>
                    <span class="text-sm font-medium text-gray-900">{{ producto.nombre }}</span>
                  </div>
                  <span class="text-sm font-semibold text-blue-600">{{ producto.cantidad }}</span>
                </div>
              </div>
            </div>

            <!-- Gastos por categoría -->
            <div class="bg-white shadow rounded-lg p-6">
              <h4 class="text-lg font-medium text-gray-900 mb-4">Gastos por Categoría</h4>
              <div class="space-y-3">
                <div class="flex justify-between items-center text-sm font-medium text-gray-900 border-b border-gray-200 pb-2">
                  <span>Total Gastos: ${{ weeklyData.gastos.total.toFixed(2) }}</span>
                </div>
                <div v-for="categoria in weeklyData.gastos.por_categoria" :key="categoria.categoria"
                     class="flex justify-between items-center py-2">
                  <span class="text-sm font-medium text-gray-900 capitalize">{{ categoria.categoria }}</span>
                  <div class="text-right">
                    <span class="text-sm font-semibold text-red-600">${{ categoria.total.toFixed(2) }}</span>
                    <span class="text-xs text-gray-500 ml-2">({{ categoria.porcentaje }}%)</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Tab: Gastos -->
      <div v-if="activeTab === 'gastos'">
        <div class="mb-6">
          <div class="flex justify-between items-center">
            <h2 class="text-xl font-semibold text-gray-900">Gestión de Gastos</h2>
            <button
              @click="showAddGastoModal = true"
              class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
            >
              + Nuevo Gasto
            </button>
          </div>
        </div>

        <!-- Lista de gastos -->
        <div class="bg-white shadow overflow-hidden sm:rounded-md">
          <ul class="divide-y divide-gray-200">
            <li v-for="gasto in gastosList" :key="gasto.id" class="px-6 py-4">
              <div class="flex items-center justify-between">
                <div class="flex-1">
                  <div class="flex items-center justify-between">
                    <div>
                      <h4 class="text-lg font-medium text-gray-900">{{ gasto.descripcion }}</h4>
                      <div class="mt-1 flex items-center space-x-4 text-sm text-gray-500">
                        <span class="font-medium">${{ gasto.monto }}</span>
                        <span class="capitalize">{{ gasto.categoria }}</span>
                        <span>{{ new Date(gasto.fecha_gasto).toLocaleDateString() }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </li>
          </ul>
        </div>

        <!-- Modal para nuevo gasto -->
        <div v-if="showAddGastoModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div class="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <h3 class="text-lg font-bold text-gray-900 mb-4">Nuevo Gasto</h3>
            
            <form @submit.prevent="addGasto" class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-gray-700">Descripción</label>
                <input
                  v-model="newGasto.descripcion"
                  type="text"
                  required
                  class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              
              <div>
                <label class="block text-sm font-medium text-gray-700">Monto</label>
                <input
                  v-model.number="newGasto.monto"
                  type="number"
                  step="0.01"
                  required
                  class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              
              <div>
                <label class="block text-sm font-medium text-gray-700">Categoría</label>
                <input
                  v-model="newGasto.categoria"
                  type="text"
                  required
                  class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              
              <div class="flex justify-end space-x-3 pt-4">
                <button
                  type="button"
                  @click="showAddGastoModal = false"
                  class="px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  Guardar
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>

      <!-- Tab: Platillos - CRUD COMPLETO -->
      <div v-if="activeTab === 'platillos'">
        <div class="mb-6">
          <div class="flex justify-between items-center">
            <div>
              <h2 class="text-xl font-semibold text-gray-900">Gestión de Platillos</h2>
              <p class="text-sm text-gray-600 mt-1">Crear, editar y gestionar platillos del menú</p>
            </div>
            <button
              @click="openNewPlatilloModal"
              class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
            >
              + Nuevo Platillo
            </button>
          </div>
        </div>

        <!-- Filtros por categoría -->
        <div class="mb-6">
          <div class="flex flex-wrap gap-2">
            <button
              @click="selectedCategory = null"
              :class="[
                'px-4 py-2 rounded-full text-sm font-medium',
                selectedCategory === null
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              ]"
            >
              Todas
            </button>
            <button
              v-for="category in categories"
              :key="category"
              @click="selectedCategory = category"
              :class="[
                'px-4 py-2 rounded-full text-sm font-medium capitalize',
                selectedCategory === category
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              ]"
            >
              {{ category }}
            </button>
          </div>
        </div>

        <!-- Lista de platillos filtrada -->
        <div v-if="loadingPlatillos" class="text-center py-4">
          <p>Cargando platillos...</p>
        </div>
        
        <div v-else class="bg-white shadow overflow-hidden sm:rounded-md">
          <ul class="divide-y divide-gray-200">
            <li v-for="platillo in filteredPlatillos" :key="platillo.id" class="px-6 py-4">
              <div class="flex items-center justify-between">
                <div class="flex-1">
                  <div class="flex items-center justify-between">
                    <div>
                      <h4 class="text-lg font-medium text-gray-900">{{ platillo.nombre }}</h4>
                      <p class="text-sm text-gray-600">{{ platillo.descripcion }}</p>
                      <div class="mt-1 flex items-center space-x-4 text-sm text-gray-500">
                        <span class="font-medium">${{ platillo.precio }}</span>
                        <span class="capitalize">{{ platillo.categoria }}</span>
                        <span class="px-2 py-1 rounded-full text-xs" :class="platillo.estado === 'disponible' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'">
                          {{ platillo.estado }}
                        </span>
                        <span v-if="platillo.kds_name" class="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs">
                          KDS: {{ platillo.kds_name }}
                        </span>
                      </div>
                    </div>
                    <div class="flex space-x-2">
                      <button
                        @click="editPlatillo(platillo)"
                        class="px-3 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                      >
                        Editar
                      </button>
                      <button
                        @click="deletePlatillo(platillo.id, platillo.nombre)"
                        class="px-3 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200"
                      >
                        Eliminar
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </li>
          </ul>
        </div>
      </div>

      <!-- Tab: Usuarios -->
      <div v-if="activeTab === 'usuarios'">
        <div class="mb-6">
          <div class="flex justify-between items-center">
            <h2 class="text-xl font-semibold text-gray-900">Gestión de Usuarios</h2>
            <button
              @click="openNewUsuarioModal"
              class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
            >
              + Nuevo Usuario
            </button>
          </div>
        </div>

        <!-- Lista de usuarios -->
        <div v-if="loadingUsuarios" class="text-center py-4">
          <p>Cargando usuarios...</p>
        </div>
        
        <div v-else class="bg-white shadow overflow-hidden sm:rounded-md">
          <ul class="divide-y divide-gray-200">
            <li v-for="usuario in usuariosList" :key="usuario.id" class="px-6 py-4">
              <div class="flex items-center justify-between">
                <div class="flex-1">
                  <div class="flex items-center justify-between">
                    <div>
                      <h4 class="text-lg font-medium text-gray-900">{{ usuario.nombre }}</h4>
                      <div class="mt-1 flex items-center space-x-4 text-sm text-gray-500">
                        <span class="font-medium capitalize">{{ usuario.rol }}</span>
                        <span>Sucursal: {{ usuario.sucursal_id }}</span>
                        <span class="px-2 py-1 rounded-full text-xs" :class="usuario.activo ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'">
                          {{ usuario.activo ? 'Activo' : 'Inactivo' }}
                        </span>
                      </div>
                    </div>
                    <div class="flex space-x-2">
                      <button
                        @click="editUsuario(usuario)"
                        class="px-3 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                      >
                        Editar
                      </button>
                      <button
                        @click="deleteUsuario(usuario.id)"
                        :disabled="usuario.id === auth.user?.id"
                        class="px-3 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200 disabled:opacity-50"
                      >
                        Desactivar
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </li>
          </ul>
        </div>
      </div>

      <!-- Tab: Configuración -->
      <div v-if="activeTab === 'configuracion'">
        <div class="mb-6">
          <div class="flex justify-between items-center">
            <h2 class="text-xl font-semibold text-gray-900">Configuración del Sistema</h2>
          </div>
        </div>

        <div class="space-y-6">
          <!-- Configuración de Impresoras -->
          <div class="bg-white shadow rounded-lg p-6">
            <h3 class="text-lg font-medium text-gray-900 mb-4">🖨️ Sistema de Impresión</h3>
            
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <!-- Estado del Print Service -->
              <div class="border border-gray-200 rounded-lg p-4">
                <h4 class="text-md font-medium text-gray-900 mb-3">Estado del Servidor de Impresión</h4>
                <div class="space-y-3">
                  <div class="flex justify-between items-center">
                    <span class="text-sm text-gray-600">Estado del Servidor:</span>
                    <span :class="printServiceStatus === 'online' ? 'text-green-600' : 'text-red-600'" 
                          class="text-sm font-medium">
                      {{ printServiceStatus === 'online' ? '🟢 Conectado' : '🔴 Desconectado' }}
                    </span>
                  </div>
                  <div class="flex justify-between items-center">
                    <span class="text-sm text-gray-600">URL del Servidor:</span>
                    <span class="text-sm font-mono bg-gray-100 px-2 py-1 rounded">{{ printServiceUrl }}</span>
                  </div>
                  <button
                    @click="testPrintService"
                    :disabled="testingPrintService"
                    class="w-full px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 disabled:opacity-50"
                  >
                    {{ testingPrintService ? 'Actualizando...' : 'Actualizar Estado' }}
                  </button>
                </div>
              </div>

              <!-- Configuración de Impresora -->
              <div class="border border-gray-200 rounded-lg p-4">
                <h4 class="text-md font-medium text-gray-900 mb-3">Configuración de Impresora</h4>
                <form @submit.prevent="savePrintConfig" class="space-y-3">
                  <div>
                    <label class="block text-sm font-medium text-gray-700">Puerto del Servidor</label>
                    <input
                      v-model.number="printConfig.port"
                      type="number"
                      min="1000"
                      max="65535"
                      class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                    />
                  </div>
                  <div>
                    <label class="block text-sm font-medium text-gray-700">Host del Servidor</label>
                    <input
                      v-model="printConfig.host"
                      type="text"
                      class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                    />
                  </div>
                  <div class="flex items-center">
                    <input
                      v-model="printConfig.autoprint"
                      type="checkbox"
                      class="h-4 w-4 text-blue-600 border-gray-300 rounded"
                    />
                    <label class="ml-2 block text-sm text-gray-700">Auto-impresión habilitada</label>
                  </div>
                  <button
                    type="submit"
                    class="w-full px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
                  >
                    Guardar Configuración
                  </button>
                </form>
              </div>
            </div>

            <!-- Instrucciones de instalación -->
            <div class="mt-6 bg-amber-50 border border-amber-200 rounded-lg p-4">
              <h4 class="text-sm font-medium text-amber-900 mb-2">⚠️ Instrucciones Importantes</h4>
              <div class="text-sm text-amber-800 space-y-2">
                <p><strong>🖥️ Ejecutar en la computadora de CAJA:</strong></p>
                <p><strong>Windows:</strong> <code class="bg-amber-100 px-1 rounded">print_service/inicio_rapido.bat</code></p>
                <p><strong>Linux:</strong> <code class="bg-amber-100 px-1 rounded">./print_service/start_print_service.sh</code></p>
                <p><strong>Manual:</strong> <code class="bg-amber-100 px-1 rounded">cd print_service && python print_server.py --port {{ printConfig.port }}</code></p>
                <p class="mt-2 text-xs text-amber-700">
                  💡 <strong>Nota:</strong> El panel de administración solo configura parámetros. 
                  La impresión real ocurre únicamente desde el sistema de caja.
                </p>
              </div>
            </div>
          </div>

          <!-- Configuración General -->
          <div class="bg-white shadow rounded-lg p-6">
            <h3 class="text-lg font-medium text-gray-900 mb-4">⚙️ Configuración General</h3>
            
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <!-- Configuración de horarios -->
              <div class="border border-gray-200 rounded-lg p-4">
                <h4 class="text-md font-medium text-gray-900 mb-3">🕐 Horarios de Operación</h4>
                <form @submit.prevent="saveGeneralConfig" class="space-y-3">
                  <div class="grid grid-cols-2 gap-3">
                    <div>
                      <label class="block text-sm font-medium text-gray-700">Apertura</label>
                      <input
                        v-model="generalConfig.horario_apertura"
                        type="time"
                        class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                      />
                    </div>
                    <div>
                      <label class="block text-sm font-medium text-gray-700">Cierre</label>
                      <input
                        v-model="generalConfig.horario_cierre"
                        type="time"
                        class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                      />
                    </div>
                  </div>
                  <div>
                    <label class="block text-sm font-medium text-gray-700">Zona Horaria</label>
                    <select
                      v-model="generalConfig.timezone"
                      class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                    >
                      <option value="America/Mexico_City">México (UTC-6)</option>
                      <option value="America/New_York">Nueva York (UTC-5)</option>
                      <option value="America/Los_Angeles">Los Ángeles (UTC-8)</option>
                    </select>
                  </div>
                  <button
                    type="submit"
                    class="w-full px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700"
                  >
                    Guardar Horarios
                  </button>
                </form>
              </div>

              <!-- Información del sistema -->
              <div class="border border-gray-200 rounded-lg p-4">
                <h4 class="text-md font-medium text-gray-900 mb-3">📊 Información del Sistema</h4>
                <div class="space-y-2 text-sm">
                  <div class="flex justify-between">
                    <span class="text-gray-600">Versión:</span>
                    <span class="font-mono">v1.0.0</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-gray-600">Base de Datos:</span>
                    <span :class="dbStatus === 'online' ? 'text-green-600' : 'text-red-600'">
                      {{ dbStatus === 'online' ? '🟢 Conectada' : '🔴 Sin conexión' }}
                    </span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-gray-600">WebSockets:</span>
                    <span class="text-green-600">🟢 Activos</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-gray-600">Última actualización:</span>
                    <span class="text-gray-500">Enero 2025</span>
                  </div>
                </div>
                <button
                  @click="checkSystemHealth"
                  :disabled="checkingHealth"
                  class="w-full mt-4 px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 disabled:opacity-50"
                >
                  {{ checkingHealth ? 'Verificando...' : 'Verificar Estado' }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

    </div>

    <!-- Modales -->
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

    <!-- Loading overlay -->
    <div v-if="loading" class="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white p-6 rounded-lg shadow-lg">
        <div class="flex items-center space-x-3">
          <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
          <span>Cargando...</span>
        </div>
      </div>
    </div>

    <!-- Error/Success messages -->
    <div v-if="error" class="fixed top-4 right-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded z-50">
      {{ error }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import api from '@/api/client'
import AppHeader from '@/components/AppHeader.vue'
import AdminModals from '@/components/AdminModals.vue'

const auth = useAuthStore()
const router = useRouter()

// Verificar permisos
if (auth.user?.rol !== 'administrador') {
  router.replace({ name: 'login' })
}

// Estado general
const error = ref('')
const loading = ref(false)

// Configuración de tabs
const tabs = [
  { id: 'dashboard', name: 'Dashboard' },
  { id: 'reportes', name: 'Reportes Semanales' },
  { id: 'gastos', name: 'Gestión de Gastos' },
  { id: 'platillos', name: 'Platillos' },
  { id: 'usuarios', name: 'Usuarios' },
  { id: 'configuracion', name: 'Configuración' }
]

const activeTab = ref('dashboard')

// Estado para dashboard
const dashboardData = ref<DashboardData | null>(null)
const loadingDashboard = ref(false)

// Estado para reportes
const weeklyData = ref<WeeklyData | null>(null)
const loadingWeekly = ref(false)

// Estado para gastos
const gastosList = ref<Gasto[]>([])
const selectedWeekDate = ref(new Date().toISOString().split('T')[0])
const showAddGastoModal = ref(false)
const newGasto = ref({
  descripcion: '',
  monto: 0,
  categoria: ''
})

// Estado para CRUD de platillos y usuarios
const platillosList = ref<any[]>([])
const usuariosList = ref<any[]>([])
const loadingPlatillos = ref(false)
const loadingUsuarios = ref(false)
const showPlatilloModal = ref(false)
const showUsuarioModal = ref(false)
const editingPlatillo = ref<any>(null)
const editingUsuario = ref<any>(null)

// Filtros para platillos
const selectedCategory = ref<string | null>(null)
const categories = ref<string[]>([])

// Estado para configuración
const printServiceStatus = ref<'online' | 'offline'>('offline')
const printServiceUrl = ref('http://localhost:3001')
const testingPrintService = ref(false)
const dbStatus = ref<'online' | 'offline'>('online')
const checkingHealth = ref(false)

const printConfig = ref({
  port: 3001,
  host: 'localhost',
  autoprint: true
})

// Helpers para dashboard
const getDataHora = (hora: number) => {
  if (!dashboardData.value) return { cantidad: 0, total: 0 }
  const data = dashboardData.value.ventas_por_hora.find(d => d.hora === hora)
  return data || { cantidad: 0, total: 0 }
}

const getPorcentajeHora = (hora: number) => {
  if (!dashboardData.value) return 0
  const maxVentas = Math.max(...dashboardData.value.ventas_por_hora.map(d => d.total), 1)
  const data = getDataHora(hora)
  return (data.total / maxVentas) * 100
}

const getCantidadEstado = (estado: string) => {
  if (!dashboardData.value) return 0
  const data = dashboardData.value.estado_actual.find(d => d.estado === estado)
  return data ? data.cantidad : 0
}

const generalConfig = ref({
  horario_apertura: '08:00',
  horario_cierre: '22:00',
  timezone: 'America/Mexico_City'
})

// Computed para platillos filtrados
const filteredPlatillos = computed(() => {
  if (!selectedCategory.value) return platillosList.value
  return platillosList.value.filter(p => p.categoria === selectedCategory.value)
})

// Interfaces
interface DashboardData {
  fecha: string
  total_pedidos: number
  promedio_ticket: number
  cancelaciones: number
  ingresos: {
    efectivo: number
    tarjeta: number
    transferencia: number
    total: number
  }
  ventas_por_hora: Array<{
    hora: number
    cantidad: number
    total: number
  }>
  tipos_orden: Array<{
    tipo: string
    cantidad: number
  }>
  estado_actual: Array<{
    estado: string
    cantidad: number
  }>
  productos_mas_vendidos: Array<{
    nombre: string
    cantidad: number
  }>
}

interface WeeklyData {
  periodo: {
    inicio: string
    fin: string
    descripcion: string
  }
  resumen: {
    total_pedidos: number
    total_pedidos_creados: number
    pedidos_cancelados: number
    tasa_cancelacion: number
    promedio_ticket: number
  }
  ingresos: {
    efectivo: number
    tarjeta: number
    transferencia: number
    total: number
  }
  gastos: {
    total: number
    por_categoria: Array<{
      categoria: string
      total: number
      porcentaje: number
    }>
  }
  analisis_tipos_orden: Array<{
    tipo: string
    cantidad: number
    ingresos: number
    porcentaje_pedidos: number
    porcentaje_ingresos: number
  }>
  ventas_por_dia: Array<{
    fecha: string
    total: number
    pedidos: number
    promedio_ticket_dia: number
  }>
  productos_mas_vendidos: Array<{
    nombre: string
    cantidad: number
  }>
  utilidad_bruta: number
}

interface Gasto {
  id: number
  descripcion: string
  monto: number
  categoria: string
  fecha_gasto: string
}

// Funciones Dashboard
const refreshDashboard = async () => {
  loadingDashboard.value = true
  error.value = ''
  
  try {
    const response = await api.get('/admin/dashboard')
    dashboardData.value = response.data
  } catch (err: any) {
    error.value = 'Error al cargar dashboard'
    console.error('Dashboard error:', err)
  } finally {
    loadingDashboard.value = false
  }
}

// Funciones Reportes
const loadWeeklyReport = async () => {
  loadingWeekly.value = true
  error.value = ''
  
  try {
    const response = await api.get(`/admin/reportes/semanal?fecha=${selectedWeekDate.value}`)
    weeklyData.value = response.data
  } catch (err: any) {
    error.value = 'Error al cargar reporte semanal'
    console.error('Weekly report error:', err)
  } finally {
    loadingWeekly.value = false
  }
}

// Funciones Gastos
const loadGastosList = async () => {
  try {
    const response = await api.get('/gastos/')
    gastosList.value = response.data
  } catch (err: any) {
    error.value = 'Error al cargar gastos'
    console.error('Gastos error:', err)
  }
}

const addGasto = async () => {
  try {
    await api.post('/gastos/', newGasto.value)
    showAddGastoModal.value = false
    newGasto.value = { descripcion: '', monto: 0, categoria: '' }
    await loadGastosList()
    error.value = ''
  } catch (err: any) {
    error.value = 'Error al crear gasto'
    console.error('Add gasto error:', err)
  }
}

// === FUNCIONES CRUD PLATILLOS (SOLO EDICIÓN) ===
const loadPlatillosList = async () => {
  loadingPlatillos.value = true
  try {
    const response = await api.get('/platillos/')
    platillosList.value = response.data
    
    // Extraer categorías únicas
    const uniqueCategories = [...new Set(response.data.map((p: any) => p.categoria))]
    categories.value = uniqueCategories
  } catch (err: any) {
    error.value = 'Error al cargar platillos'
    console.error('Error cargando platillos:', err)
  } finally {
    loadingPlatillos.value = false
  }
}

const openNewPlatilloModal = () => {
  editingPlatillo.value = null
  showPlatilloModal.value = true
}

const editPlatillo = (platillo: any) => {
  editingPlatillo.value = { ...platillo }
  showPlatilloModal.value = true
}

const closePlatilloModal = () => {
  showPlatilloModal.value = false
  editingPlatillo.value = null
}

const savePlatillo = async (data: any) => {
  try {
    if (editingPlatillo.value) {
      // Actualizar platillo existente
      await api.put(`/platillos/${editingPlatillo.value.id}`, data)
      error.value = 'Platillo actualizado exitosamente'
    } else {
      // Crear nuevo platillo
      await api.post('/platillos/', data)
      error.value = 'Platillo creado exitosamente'
    }
    
    setTimeout(() => error.value = '', 1000)
    closePlatilloModal()
    await loadPlatillosList()
  } catch (err: any) {
    error.value = err?.response?.data?.detail || 'Error al guardar platillo'
    console.error('Error guardando platillo:', err)
  }
}

const deletePlatillo = async (id: number, nombre: string) => {
  if (!confirm(`¿Estás seguro de eliminar "${nombre}"?\n\nNota: Si tiene pedidos asociados, se marcará como no disponible.`)) return
  
  try {
    const response = await api.delete(`/platillos/${id}`)
    
    // Mostrar mensaje apropiado según la respuesta
    if (response.data.message.includes('no disponible')) {
      error.value = `"${nombre}" marcado como no disponible (tiene pedidos asociados)`
    } else {
      error.value = `"${nombre}" eliminado correctamente`
    }
    
    setTimeout(() => error.value = '', 2000)
    await loadPlatillosList()
  } catch (err: any) {
    error.value = err?.response?.data?.detail || 'Error al eliminar platillo'
    console.error('Error eliminando platillo:', err)
  }
}

// === FUNCIONES CRUD USUARIOS ===
const loadUsuariosList = async () => {
  loadingUsuarios.value = true
  try {
    const response = await api.get('/usuarios/')
    usuariosList.value = response.data
  } catch (err: any) {
    error.value = 'Error al cargar usuarios'
    console.error('Error cargando usuarios:', err)
  } finally {
    loadingUsuarios.value = false
  }
}

const openNewUsuarioModal = () => {
  editingUsuario.value = null
  showUsuarioModal.value = true
}

const editUsuario = (usuario: any) => {
  editingUsuario.value = { ...usuario }
  showUsuarioModal.value = true
}

const closeUsuarioModal = () => {
  showUsuarioModal.value = false
  editingUsuario.value = null
}

const saveUsuario = async (data: any) => {
  try {
    if (editingUsuario.value) {
      // Actualizar
      await api.put(`/usuarios/${editingUsuario.value.id}`, data)
      error.value = 'Usuario actualizado exitosamente'
    } else {
      // Crear nuevo
      await api.post('/usuarios/', data)
      error.value = 'Usuario creado exitosamente'
    }
    setTimeout(() => error.value = '', 1000)
    
    closeUsuarioModal()
    await loadUsuariosList()
  } catch (err: any) {
    error.value = err?.response?.data?.detail || 'Error al guardar usuario'
    console.error('Error guardando usuario:', err)
  }
}

const deleteUsuario = async (id: number) => {
  if (!confirm('¿Estás seguro de desactivar este usuario?')) return
  
  try {
    await api.delete(`/usuarios/${id}`)
    await loadUsuariosList()
    error.value = 'Usuario desactivado exitosamente'
    setTimeout(() => error.value = '', 1000)
  } catch (err: any) {
    error.value = err?.response?.data?.detail || 'Error al desactivar usuario'
    console.error('Error desactivando usuario:', err)
  }
}

// Funciones auxiliares para tipos de orden
function getTipoOrdenLabel(tipo: string): string {
  const labels: Record<string, string> = {
    'aqui': 'Para Aquí',
    'llevar': 'Para Llevar',
    'uber_eats': 'Uber Eats'
  }
  return labels[tipo] || tipo
}

function getTipoOrdenEmoji(tipo: string): string {
  const emojis: Record<string, string> = {
    'aqui': '🍽️',
    'llevar': '🥡', 
    'uber_eats': '🚗'
  }
  return emojis[tipo] || '📦'
}

// === FUNCIONES DE CONFIGURACIÓN ===

// Funciones para configuración de impresión (solo parámetros, sin verificación real)
const testPrintService = async () => {
  testingPrintService.value = true
  try {
    // Solo hacer ping básico a la URL configurada (silencioso)
    const response = await fetch(`${printServiceUrl.value}/health`, { 
      method: 'GET',
      signal: AbortSignal.timeout(2000) // 2 segundos timeout
    })
    if (response.ok) {
      printServiceStatus.value = 'online'
    } else {
      printServiceStatus.value = 'offline'
    }
  } catch (err) {
    printServiceStatus.value = 'offline'
    // No mostrar error - es normal desde admin remoto
  } finally {
    testingPrintService.value = false
  }
}

const savePrintConfig = () => {
  // Actualizar URL del servicio de impresión
  const newUrl = `http://${printConfig.value.host}:${printConfig.value.port}`
  printServiceUrl.value = newUrl
  
  // Guardar en localStorage para persistencia (la caja lo leerá cuando reinicie)
  localStorage.setItem('print_config', JSON.stringify(printConfig.value))
  
  error.value = '✅ Configuración de impresión guardada exitosamente'
  setTimeout(() => error.value = '', 2000)
  
  // Actualizar estado silenciosamente
  setTimeout(() => {
    testPrintService()
  }, 500)
}

const saveGeneralConfig = () => {
  // Guardar en localStorage para persistencia
  localStorage.setItem('general_config', JSON.stringify(generalConfig.value))
  
  error.value = 'Configuración general guardada exitosamente'
  setTimeout(() => error.value = '', 2000)
}

const checkSystemHealth = async () => {
  checkingHealth.value = true
  try {
    // Verificar base de datos
    await api.get('/health/database')
    dbStatus.value = 'online'
    
    // Verificar print service
    await testPrintService()
    
    error.value = 'Verificación de sistema completada'
    setTimeout(() => error.value = '', 2000)
  } catch (err) {
    dbStatus.value = 'offline'
    error.value = 'Error al verificar el estado del sistema'
  } finally {
    checkingHealth.value = false
  }
}

const loadConfig = () => {
  // Cargar configuración desde localStorage
  const savedPrintConfig = localStorage.getItem('print_config')
  if (savedPrintConfig) {
    printConfig.value = { ...printConfig.value, ...JSON.parse(savedPrintConfig) }
    printServiceUrl.value = `http://${printConfig.value.host}:${printConfig.value.port}`
  }
  
  const savedGeneralConfig = localStorage.getItem('general_config')
  if (savedGeneralConfig) {
    generalConfig.value = { ...generalConfig.value, ...JSON.parse(savedGeneralConfig) }
  }
  
  // Solo verificar URL (no configurar print service desde admin)
  testPrintService()
}

// Cargar datos iniciales
onMounted(async () => {
  await Promise.all([
    refreshDashboard(),
    loadGastosList(),
    loadPlatillosList(),
    loadUsuariosList()
  ])
  
  // Cargar configuración después de las otras operaciones
  loadConfig()
})
</script>