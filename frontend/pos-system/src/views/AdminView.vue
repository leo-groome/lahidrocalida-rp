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

          <!-- Propina Efectivo -->
          <div class="bg-white overflow-hidden shadow rounded-lg">
            <div class="p-5">
              <div class="flex items-center">
                <div class="flex-shrink-0">
                  <div class="w-8 h-8 bg-green-500 rounded-md flex items-center justify-center">
                    <span class="text-white text-sm font-bold">💵</span>
                  </div>
                </div>
                <div class="ml-5 w-0 flex-1">
                  <dl>
                    <dt class="text-sm font-medium text-gray-500 truncate">Propina Efectivo</dt>
                    <dd class="text-lg font-medium text-gray-900">${{ dashboardData.propinas.efectivo.toFixed(2) }}</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <!-- Propina Tarjeta -->
          <div class="bg-white overflow-hidden shadow rounded-lg">
            <div class="p-5">
              <div class="flex items-center">
                <div class="flex-shrink-0">
                  <div class="w-8 h-8 bg-blue-500 rounded-md flex items-center justify-center">
                    <span class="text-white text-sm font-bold">💳</span>
                  </div>
                </div>
                <div class="ml-5 w-0 flex-1">
                  <dl>
                    <dt class="text-sm font-medium text-gray-500 truncate">Propina Tarjeta</dt>
                    <dd class="text-lg font-medium text-gray-900">${{ dashboardData.propinas.tarjeta.toFixed(2) }}</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <!-- Propina Total -->
          <div class="bg-white overflow-hidden shadow rounded-lg">
            <div class="p-5">
              <div class="flex items-center">
                <div class="flex-shrink-0">
                  <div class="w-8 h-8 bg-purple-500 rounded-md flex items-center justify-center">
                    <span class="text-white text-sm font-bold">💰</span>
                  </div>
                </div>
                <div class="ml-5 w-0 flex-1">
                  <dl>
                    <dt class="text-sm font-medium text-gray-500 truncate">Propina Total</dt>
                    <dd class="text-lg font-medium text-gray-900">${{ dashboardData.propinas.total.toFixed(2) }}</dd>
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

          <!-- Lista de Pedidos del Día -->
           <div v-if="dashboardData" class="bg-white shadow rounded-lg overflow-hidden lg:col-span-3 lg:col-start-1">
               <div class="px-6 py-4 border-b border-gray-200 bg-gray-50">
                   <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                     <div class="flex-1">
                       <div class="flex items-center space-x-3">
                         <h3 class="text-lg font-semibold text-gray-900">📋 Pedidos del Día</h3>
                         <div class="hidden md:flex items-center space-x-4">
                           <div class="flex items-center space-x-2">
                             <span class="text-sm text-gray-600">Mostrando:</span>
                             <span class="px-2 py-1 bg-white border border-gray-300 rounded-md text-sm font-medium text-gray-700">
                               {{ filteredPedidosDelDia.length }} de {{ dashboardData.pedidos_del_dia.length }}
                             </span>
                           </div>
                           <div class="h-4 w-px bg-gray-300"></div>
                           <div class="flex items-center space-x-2">
                             <span class="text-sm text-gray-600">Orden:</span>
                             <button
                               @click="sortDescending = !sortDescending"
                               :class="[
                                 'px-3 py-1 rounded-md text-xs font-medium flex items-center space-x-1 border transition-colors',
                                 sortDescending 
                                   ? 'bg-gray-800 text-white border-gray-800' 
                                   : 'bg-white text-gray-700 border-gray-300 hover:border-gray-400'
                               ]"
                             >
                               <span>{{ sortDescending ? '🔼' : '🔽' }}</span>
                               <span>{{ sortDescending ? 'Más Reciente' : 'Más Antiguo' }}</span>
                             </button>
                           </div>
                         </div>
                       </div>
                       <p class="text-sm text-gray-500 mt-2 md:mt-1">Vista detallada de todos los pedidos realizados hoy</p>
                     </div>
                     
                     <!-- Filtros compactos -->
                     <div class="flex-shrink-0">
                       <div class="flex flex-col sm:flex-row gap-3">
                         <div class="flex items-center space-x-2">
                           <span class="text-sm font-medium text-gray-700 hidden sm:inline">Filtrar:</span>
                           <div class="flex flex-wrap gap-1">
                             <button
                               @click="selectedPaymentMethod = 'todos'"
                               :class="[
                                 'px-3 py-1.5 rounded-md text-xs font-medium transition-colors border',
                                 selectedPaymentMethod === 'todos'
                                   ? 'bg-blue-600 text-white border-blue-700'
                                   : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                               ]"
                             >
                               Todos
                             </button>
                             <button
                               @click="selectedPaymentMethod = 'efectivo'"
                               :class="[
                                 'px-3 py-1.5 rounded-md text-xs font-medium transition-colors border flex items-center space-x-1',
                                 selectedPaymentMethod === 'efectivo'
                                   ? 'bg-green-600 text-white border-green-700'
                                   : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                               ]"
                             >
                               <span>💵</span>
                               <span>Efectivo</span>
                             </button>
                             <button
                               @click="selectedPaymentMethod = 'tarjeta'"
                               :class="[
                                 'px-3 py-1.5 rounded-md text-xs font-medium transition-colors border flex items-center space-x-1',
                                 selectedPaymentMethod === 'tarjeta'
                                   ? 'bg-blue-500 text-white border-blue-600'
                                   : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                               ]"
                             >
                               <span>💳</span>
                               <span>Tarjeta</span>
                             </button>
                             <button
                               @click="selectedPaymentMethod = 'transferencia'"
                               :class="[
                                 'px-3 py-1.5 rounded-md text-xs font-medium transition-colors border flex items-center space-x-1',
                                 selectedPaymentMethod === 'transferencia'
                                   ? 'bg-purple-500 text-white border-purple-600'
                                   : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                               ]"
                             >
                               <span>📱</span>
                               <span>Transferencia</span>
                             </button>
                           </div>
                         </div>
                       </div>
                      </div>
                    </div>
                </div>
                
                <!-- Estados vacíos -->
                <div v-if="dashboardData.pedidos_del_dia.length === 0" class="px-6 py-12 text-center">
                    <div class="mx-auto max-w-md">
                        <div class="text-4xl mb-4">📋</div>
                        <h3 class="text-lg font-medium text-gray-900 mb-2">No hay pedidos hoy</h3>
                        <p class="text-gray-500">Aún no se han realizado pedidos en el día de hoy.</p>
                    </div>
                </div>
                
                <div v-else-if="filteredPedidosDelDia.length === 0" class="px-6 py-12 text-center">
                    <div class="mx-auto max-w-md">
                        <div class="text-4xl mb-4">🔍</div>
                        <h3 class="text-lg font-medium text-gray-900 mb-2">No hay pedidos con el filtro seleccionado</h3>
                        <p class="text-gray-500">Intenta cambiar el método de pago o revisa los pedidos de hoy.</p>
                        <button
                            @click="selectedPaymentMethod = 'todos'"
                            class="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium"
                        >
                            Ver todos los pedidos
                        </button>
                    </div>
                </div>
                
                <div v-else class="overflow-x-auto lg:overflow-x-visible rounded-b-lg border border-gray-200 border-t-0">
                   <table class="w-full table-fixed divide-y divide-gray-200">
                      <thead class="bg-gray-50 sticky top-0 z-10">
                           <tr>
                                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-[8%]">Pedido</th>
                                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-[25%]">Mesa/Cliente</th>
                                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-[7%]">Tipo</th>
                                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-[10%]">Total</th>
                                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-[12%]">Pago</th>
                                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-[13%]">Propinas</th>
                                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-[8%]">Hora</th>
                                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-[17%]">Acciones</th>
                            </tr>
                     </thead>
                     <tbody class="bg-white divide-y divide-gray-200">
                           <tr v-for="(pedido, index) in filteredPedidosDelDia" :key="pedido.id" 
                               :class="[
                                 'transition-colors duration-150',
                                 index % 2 === 0 ? 'bg-white' : 'bg-gray-50',
                                 'hover:bg-blue-50'
                               ]">
                              <td class="px-4 py-3 whitespace-nowrap">
                                  <div class="text-sm font-bold text-gray-900">#{{ pedido.numero_display }}</div>
                              </td>
                               <td class="px-4 py-3">
                                   <div class="text-sm text-gray-700 truncate max-w-[120px] lg:max-w-[180px] xl:max-w-[220px]" :title="getMesaClienteDisplay(pedido)">
                                       {{ getMesaClienteDisplay(pedido) }}
                                   </div>
                               </td>
                              <td class="px-4 py-3 whitespace-nowrap">
                                  <div class="flex items-center space-x-1">
                                      <span class="text-lg">{{ getOrderTypeIcon(pedido.tipo_orden) }}</span>
                                      <span class="text-xs text-gray-500 capitalize hidden lg:inline">
                                          {{ pedido.tipo_orden.replace('_', ' ') }}
                                      </span>
                                  </div>
                              </td>
                              <td class="px-4 py-3 whitespace-nowrap">
                                  <div class="text-sm font-bold text-green-700">${{ pedido.total.toFixed(2) }}</div>
                              </td>
                                <td class="px-4 py-3 whitespace-nowrap">
                                    <div class="flex items-center space-x-1">
                                        <span class="text-sm">{{ getPaymentMethodIcon(pedido.metodo_pago) }}</span>
                                        <span :class="['px-2 py-1 rounded-full text-xs font-medium capitalize hidden md:inline', getPaymentMethodColor(pedido.metodo_pago)]"
                                              :title="pedido.metodo_pago || '-'">
                                            {{ pedido.metodo_pago || '-' }}
                                        </span>
                                    </div>
                                </td>
                                <td class="px-4 py-3">
                                    <div class="text-sm text-gray-700 truncate" :title="formatTipDisplay(pedido)">
                                        <template v-if="pedido.propina_total === 0">
                                            Sin propina
                                        </template>
                                        <template v-else>
                                            ${{ pedido.propina_total.toFixed(2) }}
                                            <span class="hidden lg:inline text-xs text-gray-500 ml-1">
                                                <template v-if="pedido.propina_efectivo > 0 && pedido.propina_tarjeta > 0">
                                                    💵💳
                                                </template>
                                                <template v-else-if="pedido.propina_efectivo > 0">
                                                    💵
                                                </template>
                                                <template v-else-if="pedido.propina_tarjeta > 0">
                                                    💳
                                                </template>
                                            </span>
                                        </template>
                                    </div>
                                </td>
                               <td class="px-4 py-3 whitespace-nowrap">
                                   <div class="text-xs text-gray-500">
                                       {{ new Date(pedido.fecha_creacion).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' }) }}
                                   </div>
                               </td>
                              <td class="px-4 py-3 whitespace-nowrap">
                                  <button
                                      @click="openOrderModal(pedido)"
                                      class="px-3 py-1.5 bg-blue-50 text-blue-700 hover:bg-blue-100 text-xs font-medium rounded-md transition-colors"
                                  >
                                      Ver
                                  </button>
                              </td>
                          </tr>
                      </tbody>
                      <tfoot v-if="filteredSummary" class="bg-gray-800 text-white">
                          <tr>
                              <td colspan="8" class="px-4 py-3">
                                  <div class="flex flex-wrap items-center justify-between gap-4">
                                      <div class="flex items-center space-x-6">
                                          <div>
                                              <div class="text-xs font-medium text-gray-300">Total Pedidos</div>
                                              <div class="text-lg font-bold">{{ filteredSummary.count }}</div>
                                          </div>
                                          <div>
                                              <div class="text-xs font-medium text-gray-300">Total Ventas</div>
                                              <div class="text-lg font-bold text-green-300">${{ filteredSummary.total.toFixed(2) }}</div>
                                          </div>
                                          <div>
                                              <div class="text-xs font-medium text-gray-300">Propinas Totales</div>
                                              <div class="text-lg font-bold text-yellow-300">${{ filteredSummary.propina_total.toFixed(2) }}</div>
                                          </div>
                                          <div class="hidden md:block">
                                              <div class="text-xs font-medium text-gray-300">Ticket Promedio</div>
                                              <div class="text-lg font-bold text-blue-300">${{ filteredSummary.promedio_ticket.toFixed(2) }}</div>
                                          </div>
                                      </div>
                                      <div class="text-xs text-gray-400">
                                          Resumen de {{ filteredSummary.count }} pedidos filtrados
                                      </div>
                                  </div>
                              </td>
                          </tr>
                      </tfoot>
                  </table>
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

            <!-- Gastos por tipo -->
            <div class="bg-white shadow rounded-lg p-6">
              <h4 class="text-lg font-medium text-gray-900 mb-4">Gastos por Tipo</h4>
              <div class="space-y-3">
                <div class="flex justify-between items-center text-sm font-medium text-gray-900 border-b border-gray-200 pb-2">
                  <span>Total Gastos: ${{ formatCurrency(weeklyData.gastos.total) }}</span>
                </div>
                <div v-for="categoria in weeklyData.gastos.por_categoria" :key="categoria.categoria"
                     class="flex justify-between items-center py-2">
                  <span class="text-sm font-medium text-gray-900 capitalize">{{ categoria.categoria }}</span>
                  <div class="text-right">
                    <span class="text-sm font-semibold text-red-600">${{ formatCurrency(categoria.total) }}</span>
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
          <div class="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 class="text-xl font-semibold text-gray-900">Gestión de Gastos</h2>
              <p class="text-sm text-gray-600 mt-1">Registra compras, proveedores y artículos desde un solo lugar.</p>
            </div>
            <div class="flex flex-wrap gap-2">
              <button
                @click="showAddGastoModal = true"
                class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
              >
                + Nuevo Gasto
              </button>
              <button
                @click="openNewProveedor"
                class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                + Proveedor
              </button>
              <button
                @click="openNewArticulo"
                class="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
              >
                + Artículo
              </button>
              <button
                @click="openNewCategoria"
                class="px-4 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-900"
              >
                + Categoría
              </button>
            </div>
          </div>
        </div>

        <div class="mb-6 flex flex-wrap gap-2">
          <button
            @click="gastosSubTab = 'gastos'"
            :class="[
              'px-4 py-2 rounded-full text-sm font-medium',
              gastosSubTab === 'gastos' ? 'bg-green-600 text-white' : 'bg-gray-100 text-gray-700'
            ]"
          >
            Gastos
          </button>
          <button
            @click="gastosSubTab = 'proveedores'"
            :class="[
              'px-4 py-2 rounded-full text-sm font-medium',
              gastosSubTab === 'proveedores' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700'
            ]"
          >
            Proveedores
          </button>
          <button
            @click="gastosSubTab = 'articulos'"
            :class="[
              'px-4 py-2 rounded-full text-sm font-medium',
              gastosSubTab === 'articulos' ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-700'
            ]"
          >
            Artículos
          </button>
          <button
            @click="gastosSubTab = 'categorias'"
            :class="[
              'px-4 py-2 rounded-full text-sm font-medium',
              gastosSubTab === 'categorias' ? 'bg-gray-800 text-white' : 'bg-gray-100 text-gray-700'
            ]"
          >
            Categorías
          </button>
        </div>

        <div v-if="gastosSubTab === 'gastos'">
          <div class="bg-white shadow rounded-lg p-4 mb-6">
            <h3 class="text-sm font-semibold text-gray-900 mb-3">Filtros</h3>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div>
                <label class="block text-xs font-medium text-gray-600">Inicio</label>
                <input v-model="gastoFilters.fecha_inicio" type="date" class="mt-1 w-full border border-gray-200 rounded-md px-2 py-1 text-sm" />
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-600">Fin</label>
                <input v-model="gastoFilters.fecha_fin" type="date" class="mt-1 w-full border border-gray-200 rounded-md px-2 py-1 text-sm" />
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-600">Proveedor</label>
                <select v-model="gastoFilters.proveedor_id" class="mt-1 w-full border border-gray-200 rounded-md px-2 py-1 text-sm">
                  <option :value="null">Todos</option>
                  <option v-for="proveedor in proveedoresList" :key="proveedor.id" :value="proveedor.id">
                    {{ proveedor.nombre }}
                  </option>
                </select>
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-600">Tipo</label>
                <select v-model="gastoFilters.tipo_gasto" class="mt-1 w-full border border-gray-200 rounded-md px-2 py-1 text-sm">
                  <option value="">Todos</option>
                  <option value="directo">Directo</option>
                  <option value="indirecto">Indirecto</option>
                  <option value="nomina">Nómina</option>
                </select>
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-600">Método pago</label>
                <select v-model="gastoFilters.metodo_pago" class="mt-1 w-full border border-gray-200 rounded-md px-2 py-1 text-sm">
                  <option value="">Todos</option>
                  <option value="efectivo">Efectivo</option>
                  <option value="tarjeta">Tarjeta</option>
                </select>
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-600">Categoría artículo</label>
                <select v-model="gastoFilters.categoria_id" class="mt-1 w-full border border-gray-200 rounded-md px-2 py-1 text-sm">
                  <option :value="null">Todas</option>
                  <option v-for="categoria in categoriasArticuloList" :key="categoria.id" :value="categoria.id">
                    {{ categoria.nombre }}
                  </option>
                </select>
              </div>
            </div>
            <div class="flex gap-2 mt-4">
              <button @click="loadGastosList" class="px-3 py-1.5 bg-gray-900 text-white rounded-md text-sm">Aplicar</button>
              <button
                @click="() => { gastoFilters.fecha_inicio = ''; gastoFilters.fecha_fin = ''; gastoFilters.proveedor_id = null; gastoFilters.tipo_gasto = ''; gastoFilters.metodo_pago = ''; gastoFilters.categoria_id = null; loadGastosList() }"
                class="px-3 py-1.5 bg-gray-200 text-gray-700 rounded-md text-sm"
              >
                Limpiar
              </button>
            </div>
          </div>

          <div class="bg-white shadow overflow-hidden sm:rounded-md">
            <ul class="divide-y divide-gray-200">
              <li v-for="gasto in gastosList" :key="gasto.id" class="px-6 py-4">
                <div class="flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <h4 class="text-lg font-medium text-gray-900">{{ gasto.proveedor.nombre }}</h4>
                    <div class="mt-1 flex flex-wrap items-center gap-3 text-sm text-gray-500">
                      <span class="font-medium">${{ formatCurrency(gasto.total) }}</span>
                      <span class="capitalize">{{ gasto.tipo_gasto }}</span>
                      <span class="capitalize">{{ gasto.metodo_pago }}</span>
                      <span v-if="gasto.folio">Folio {{ gasto.folio }}</span>
                      <span>{{ new Date(gasto.fecha_gasto).toLocaleDateString() }}</span>
                    </div>
                  </div>
                  <button
                    @click="toggleGastoExpanded(gasto.id)"
                    class="text-sm text-blue-600 hover:text-blue-700"
                  >
                    {{ isGastoExpanded(gasto.id) ? 'Ocultar detalles' : 'Ver detalles' }}
                  </button>
                </div>
                <div v-if="isGastoExpanded(gasto.id)" class="mt-4 bg-gray-50 rounded-lg p-4">
                  <div class="flex flex-wrap items-center justify-between gap-3 mb-3">
                    <div class="text-sm text-gray-700">
                      <span class="font-semibold">Subtotal:</span> ${{ formatCurrency(gasto.subtotal) }}
                      <span v-if="gasto.total_manual" class="ml-3 text-gray-500">Total manual: ${{ formatCurrency(gasto.total_manual) }}</span>
                    </div>
                    <div class="text-sm text-gray-500">
                      {{ gasto.descripcion || 'Sin descripción' }}
                    </div>
                  </div>
                  <div v-if="gasto.tipo_gasto === 'nomina'" class="text-sm text-gray-700">
                    <span class="font-semibold">Notas:</span> {{ gasto.notas || 'Sin notas' }}
                  </div>
                  <div v-else>
                    <div class="grid grid-cols-1 gap-2">
                      <div v-for="detalle in gasto.detalles" :key="detalle.id" class="flex flex-wrap items-center justify-between text-sm text-gray-600">
                        <div>
                          <span class="font-medium text-gray-900">{{ detalle.articulo.nombre }}</span>
                          <span class="ml-2 text-xs text-gray-500">{{ detalle.articulo.categoria.nombre }}</span>
                        </div>
                        <div class="flex items-center gap-3">
                          <span>{{ detalle.cantidad }} {{ detalle.articulo.unidad }}</span>
                          <span>${{ formatCurrency(detalle.precio_unitario) }}</span>
                          <span class="font-semibold text-gray-900">${{ formatCurrency(detalle.subtotal_linea) }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </li>
            </ul>
          </div>
        </div>

        <div v-else-if="gastosSubTab === 'proveedores'">
          <div class="bg-white shadow rounded-lg p-4">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-base font-semibold text-gray-900">Proveedores</h3>
              <button @click="openNewProveedor" class="px-3 py-1.5 bg-blue-600 text-white rounded-md text-sm">Nuevo</button>
            </div>
            <div class="space-y-3">
              <div v-for="proveedor in proveedoresList" :key="proveedor.id" class="flex flex-wrap items-center justify-between gap-3 border border-gray-100 rounded-lg px-4 py-3">
                <div>
                  <div class="text-sm font-semibold text-gray-900">{{ proveedor.nombre }}</div>
                  <div class="text-xs text-gray-500">{{ proveedor.telefono || 'Sin teléfono' }}</div>
                  <div class="text-xs text-gray-500">{{ proveedor.direccion || 'Sin dirección' }}</div>
                </div>
                <button @click="editProveedor(proveedor)" class="text-sm text-blue-600 hover:text-blue-700">Editar</button>
              </div>
            </div>
          </div>
        </div>

        <div v-else-if="gastosSubTab === 'articulos'">
          <div class="bg-white shadow rounded-lg p-4">
            <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
              <h3 class="text-base font-semibold text-gray-900">Artículos</h3>
              <div class="flex flex-wrap gap-2">
                <select v-model="selectedArticuloCategoria" @change="loadArticulos" class="border border-gray-200 rounded-md px-2 py-1 text-sm">
                  <option :value="null">Todas las categorías</option>
                  <option v-for="categoria in categoriasArticuloList" :key="categoria.id" :value="categoria.id">
                    {{ categoria.nombre }}
                  </option>
                </select>
                <button @click="openNewArticulo" class="px-3 py-1.5 bg-indigo-600 text-white rounded-md text-sm">Nuevo</button>
              </div>
            </div>
            <div class="space-y-3">
              <div v-for="articulo in articulosList" :key="articulo.id" class="flex flex-wrap items-center justify-between gap-3 border border-gray-100 rounded-lg px-4 py-3">
                <div>
                  <div class="text-sm font-semibold text-gray-900">{{ articulo.nombre }}</div>
                  <div class="text-xs text-gray-500">{{ articulo.categoria.nombre }} · {{ articulo.unidad }}</div>
                  <div class="text-xs text-gray-500">Costo estándar: ${{ articulo.costo_estandar }}</div>
                </div>
                <button @click="editArticulo(articulo)" class="text-sm text-indigo-600 hover:text-indigo-700">Editar</button>
              </div>
            </div>
          </div>
        </div>

        <div v-else-if="gastosSubTab === 'categorias'">
          <div class="bg-white shadow rounded-lg p-4">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-base font-semibold text-gray-900">Categorías de artículo</h3>
              <button @click="openNewCategoria" class="px-3 py-1.5 bg-gray-900 text-white rounded-md text-sm">Nueva</button>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div v-for="categoria in categoriasArticuloList" :key="categoria.id" class="flex items-center justify-between border border-gray-100 rounded-lg px-4 py-3">
                <div class="text-sm font-semibold text-gray-900">{{ categoria.nombre }}</div>
                <button @click="editCategoria(categoria)" class="text-sm text-gray-700 hover:text-gray-900">Editar</button>
              </div>
            </div>
          </div>
        </div>

        <!-- Modal para nuevo gasto -->
        <div v-if="showAddGastoModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div class="relative top-10 mx-auto p-6 border w-full max-w-4xl shadow-lg rounded-md bg-white">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-lg font-bold text-gray-900">Nuevo Gasto</h3>
              <button @click="showAddGastoModal = false" class="text-gray-500 hover:text-gray-700">✕</button>
            </div>

            <form @submit.prevent="addGasto" class="space-y-5">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label class="block text-sm font-medium text-gray-700">Proveedor</label>
                  <select v-model="newGasto.proveedor_id" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md" required>
                    <option :value="null">Selecciona proveedor</option>
                    <option v-for="proveedor in proveedoresList" :key="proveedor.id" :value="proveedor.id">
                      {{ proveedor.nombre }}
                    </option>
                  </select>
                </div>
                <div>
                  <label class="block text-sm font-medium text-gray-700">Tipo de gasto</label>
                  <select v-model="newGasto.tipo_gasto" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md">
                    <option value="directo">Directo</option>
                    <option value="indirecto">Indirecto</option>
                    <option value="nomina">Nómina</option>
                  </select>
                </div>
                <div>
                  <label class="block text-sm font-medium text-gray-700">Método de pago</label>
                  <select v-model="newGasto.metodo_pago" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md">
                    <option value="efectivo">Efectivo</option>
                    <option value="tarjeta">Tarjeta</option>
                  </select>
                </div>
                <div>
                  <label class="block text-sm font-medium text-gray-700">Folio</label>
                  <input v-model="newGasto.folio" type="text" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md" />
                </div>
                <div>
                  <label class="block text-sm font-medium text-gray-700">Descripción</label>
                  <input v-model="newGasto.descripcion" type="text" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md" />
                </div>
                <div>
                  <label class="block text-sm font-medium text-gray-700">Total manual (opcional)</label>
                  <input v-model.number="newGasto.total_manual" type="number" step="0.01" min="0" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md" />
                </div>
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700">Notas</label>
                <textarea v-model="newGasto.notas" rows="2" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md" />
              </div>

              <div v-if="newGasto.tipo_gasto !== 'nomina'">
                <div class="flex items-center justify-between mb-2">
                  <h4 class="text-sm font-semibold text-gray-900">Artículos</h4>
                  <button type="button" @click="addDetalleLine" class="text-sm text-green-600 hover:text-green-700">+ Agregar línea</button>
                </div>
                <div class="space-y-3">
                  <div v-for="(detalle, index) in newGasto.detalles" :key="index" class="grid grid-cols-1 md:grid-cols-4 gap-3 items-center">
                    <select v-model="detalle.articulo_id" class="border border-gray-300 rounded-md px-2 py-2">
                      <option :value="null">Artículo</option>
                      <option v-for="articulo in articulosList" :key="articulo.id" :value="articulo.id">
                        {{ articulo.nombre }} ({{ articulo.unidad }})
                      </option>
                    </select>
                    <input v-model.number="detalle.cantidad" type="number" step="0.01" min="0" class="border border-gray-300 rounded-md px-2 py-2" />
                    <input v-model.number="detalle.precio_unitario" type="number" step="0.01" min="0" class="border border-gray-300 rounded-md px-2 py-2" />
                    <div class="flex items-center gap-2">
                      <span class="text-sm text-gray-600">${{ formatCurrency(detalle.cantidad * detalle.precio_unitario) }}</span>
                      <button type="button" @click="removeDetalleLine(index)" class="text-sm text-red-600 hover:text-red-700">Quitar</button>
                    </div>
                  </div>
                </div>
              </div>

              <div class="flex flex-wrap items-center justify-between gap-3 text-sm text-gray-700">
                <div>
                  <span class="font-medium">Subtotal:</span>
                  ${{ formatCurrency(calcularSubtotal(newGasto.detalles)) }}
                </div>
                <div>
                  <span class="font-medium">Total:</span>
                  ${{ formatCurrency(getGastoTotal(newGasto)) }}
                </div>
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

        <!-- Modal proveedor -->
        <div v-if="showProveedorModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div class="relative top-20 mx-auto p-6 border w-full max-w-md shadow-lg rounded-md bg-white">
            <h3 class="text-lg font-bold text-gray-900 mb-4">{{ editingProveedor ? 'Editar proveedor' : 'Nuevo proveedor' }}</h3>
            <form @submit.prevent="saveProveedor" class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-gray-700">Nombre</label>
                <input v-model="proveedorForm.nombre" type="text" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md" required />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700">Teléfono</label>
                <input v-model="proveedorForm.telefono" type="text" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md" />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700">Dirección</label>
                <textarea v-model="proveedorForm.direccion" rows="2" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md" />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700">Notas</label>
                <textarea v-model="proveedorForm.notas" rows="2" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md" />
              </div>
              <div class="flex justify-end space-x-3 pt-2">
                <button type="button" @click="showProveedorModal = false" class="px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400">Cancelar</button>
                <button type="submit" class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">Guardar</button>
              </div>
            </form>
          </div>
        </div>

        <!-- Modal articulo -->
        <div v-if="showArticuloModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div class="relative top-20 mx-auto p-6 border w-full max-w-md shadow-lg rounded-md bg-white">
            <h3 class="text-lg font-bold text-gray-900 mb-4">{{ editingArticulo ? 'Editar artículo' : 'Nuevo artículo' }}</h3>
            <form @submit.prevent="saveArticulo" class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-gray-700">Nombre</label>
                <input v-model="articuloForm.nombre" type="text" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md" required />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700">Categoría</label>
                <select v-model="articuloForm.categoria_id" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md" required>
                  <option :value="null">Selecciona categoría</option>
                  <option v-for="categoria in categoriasArticuloList" :key="categoria.id" :value="categoria.id">
                    {{ categoria.nombre }}
                  </option>
                </select>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700">Unidad</label>
                <select v-model="articuloForm.unidad" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md">
                  <option value="kg">kg</option>
                  <option value="g">g</option>
                  <option value="lt">lt</option>
                  <option value="ml">ml</option>
                  <option value="pza">pza</option>
                  <option value="caja">caja</option>
                  <option value="paq">paq</option>
                </select>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700">Costo estándar</label>
                <input v-model.number="articuloForm.costo_estandar" type="number" step="0.01" min="0" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md" required />
              </div>
              <div class="flex justify-end space-x-3 pt-2">
                <button type="button" @click="showArticuloModal = false" class="px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400">Cancelar</button>
                <button type="submit" class="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700">Guardar</button>
              </div>
            </form>
          </div>
        </div>

        <!-- Modal categoria -->
        <div v-if="showCategoriaModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div class="relative top-20 mx-auto p-6 border w-full max-w-md shadow-lg rounded-md bg-white">
            <h3 class="text-lg font-bold text-gray-900 mb-4">{{ editingCategoria ? 'Editar categoría' : 'Nueva categoría' }}</h3>
            <form @submit.prevent="saveCategoria" class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-gray-700">Nombre</label>
                <input v-model="categoriaForm.nombre" type="text" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md" required />
              </div>
              <div class="flex justify-end space-x-3 pt-2">
                <button type="button" @click="showCategoriaModal = false" class="px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400">Cancelar</button>
                <button type="submit" class="px-4 py-2 bg-gray-900 text-white rounded-md hover:bg-gray-950">Guardar</button>
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

     <!-- Modal para detalles del pedido -->
     <div v-if="showOrderModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
       <div class="relative top-20 mx-auto p-5 border w-11/12 max-w-2xl shadow-lg rounded-md bg-white">
         <div class="mt-3">
           <div class="flex items-center justify-between mb-4">
             <h3 class="text-lg font-bold text-gray-900">
               Pedido #{{ selectedOrder?.numero_display }}
             </h3>
             <button
               @click="showOrderModal = false"
               class="text-gray-400 hover:text-gray-600"
             >
               <span class="sr-only">Cerrar</span>
               ✕
             </button>
           </div>

           <div class="space-y-4">
             <!-- Información del pedido -->
             <div class="grid grid-cols-2 gap-4 text-sm">
               <div>
                 <span class="font-medium text-gray-700">Cliente:</span>
                 <span class="ml-2">{{ selectedOrder?.nombre_cliente || 'Sin nombre' }}</span>
               </div>
               <div>
                 <span class="font-medium text-gray-700">Mesa:</span>
                 <span class="ml-2">{{ selectedOrder?.mesa || 'N/A' }}</span>
               </div>
               <div>
                 <span class="font-medium text-gray-700">Tipo:</span>
                 <span class="ml-2 capitalize">{{ selectedOrder?.tipo_orden.replace('_', ' ') }}</span>
               </div>
               <div>
                 <span class="font-medium text-gray-700">Método de pago:</span>
                 <span class="ml-2 capitalize">{{ selectedOrder?.metodo_pago || 'N/A' }}</span>
               </div>
               <div>
                 <span class="font-medium text-gray-700">Fecha/Hora:</span>
                 <span class="ml-2">
                   {{ new Date(selectedOrder?.fecha_creacion).toLocaleString('es-ES') }}
                 </span>
               </div>
               <div>
                 <span class="font-medium text-gray-700">Total:</span>
                 <span class="ml-2 font-semibold text-green-600">${{ selectedOrder?.total.toFixed(2) }}</span>
               </div>
             </div>

             <!-- Artículos del pedido -->
             <div>
               <h4 class="font-medium text-gray-900 mb-3">Artículos del Pedido</h4>
               <div class="space-y-2">
                 <div v-for="articulo in selectedOrder?.articulos_pedido" :key="articulo.platillo"
                      class="flex justify-between items-center py-2 border-b border-gray-100">
                   <div class="flex-1">
                     <span class="font-medium">{{ articulo.platillo }}</span>
                     <span v-if="articulo.modificaciones" class="text-sm text-gray-500 ml-2">
                       ({{ articulo.modificaciones }})
                     </span>
                   </div>
                   <div class="text-right">
                     <span class="text-sm text-gray-600">{{ articulo.cantidad }}x</span>
                     <span class="ml-2 font-medium">${{ articulo.precio_cobrado.toFixed(2) }}</span>
                   </div>
                 </div>
               </div>
             </div>
           </div>
         </div>
       </div>
     </div>

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
const showOrderModal = ref(false)
const selectedOrder = ref<any>(null)
const selectedPaymentMethod = ref<string>('todos')
const sortDescending = ref(true)

// Estado para reportes
const weeklyData = ref<WeeklyData | null>(null)
const loadingWeekly = ref(false)

// Estado para gastos
const gastosList = ref<Gasto[]>([])
const selectedWeekDate = ref(new Date().toISOString().split('T')[0])
const gastosSubTab = ref<'gastos' | 'proveedores' | 'articulos' | 'categorias'>('gastos')
const showAddGastoModal = ref(false)
const showProveedorModal = ref(false)
const showArticuloModal = ref(false)
const showCategoriaModal = ref(false)
const proveedoresList = ref<Proveedor[]>([])
const categoriasArticuloList = ref<CategoriaArticulo[]>([])
const articulosList = ref<Articulo[]>([])
const selectedArticuloCategoria = ref<number | null | string>(null)
const expandedGastos = ref<number[]>([])
const categoriasSeeded = ref(false)
const gastoFilters = ref({
  fecha_inicio: '',
  fecha_fin: '',
  proveedor_id: null as number | null | string,
  tipo_gasto: '',
  metodo_pago: '',
  categoria_id: null as number | null | string
})
const newGasto = ref<GastoForm>({
  proveedor_id: null,
  tipo_gasto: 'directo',
  metodo_pago: 'efectivo',
  descripcion: '',
  folio: '',
  total_manual: null,
  notas: '',
  detalles: []
})
const proveedorForm = ref<ProveedorForm>({
  nombre: '',
  telefono: '',
  direccion: '',
  notas: ''
})
const editingProveedor = ref<Proveedor | null>(null)
const articuloForm = ref<ArticuloForm>({
  nombre: '',
  unidad: 'kg',
  costo_estandar: 0,
  categoria_id: null
})
const editingArticulo = ref<Articulo | null>(null)
const categoriaForm = ref<CategoriaForm>({
  nombre: ''
})
const editingCategoria = ref<CategoriaArticulo | null>(null)

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

// Helpers para tabla de pedidos
const getOrderTypeIcon = (tipo: string) => {
  const icons: Record<string, string> = {
    'aqui': '🍽️',
    'llevar': '🥡',
    'uber_eats': '🚗'
  }
  return icons[tipo] || '📦'
}

const getPaymentMethodColor = (metodo: string) => {
  const colors: Record<string, string> = {
    'efectivo': 'text-green-600 bg-green-100',
    'tarjeta': 'text-blue-600 bg-blue-100',
    'transferencia': 'text-purple-600 bg-purple-100'
  }
  return colors[metodo] || 'text-gray-600 bg-gray-100'
}

const getPaymentMethodIcon = (metodo: string) => {
  const icons: Record<string, string> = {
    'efectivo': '💵',
    'tarjeta': '💳',
    'transferencia': '📱'
  }
  return icons[metodo] || '💳'
}

const getMesaClienteDisplay = (pedido: any) => {
  if (pedido.tipo_orden === 'aqui') {
    return pedido.mesa ? `Mesa ${pedido.mesa}` : 'Sin mesa'
  } else {
    return pedido.nombre_cliente || 'Sin nombre'
  }
}

const formatTipDisplay = (pedido: any) => {
  const total = pedido.propina_total
  const efectivo = pedido.propina_efectivo
  const tarjeta = pedido.propina_tarjeta
  
  if (total === 0) return 'Sin propina'
  
  return `$${total.toFixed(2)} (💵$${efectivo.toFixed(2)}/💳$${tarjeta.toFixed(2)})`
}

const formatTipDisplayCompact = (pedido: any) => {
  const total = pedido.propina_total
  const efectivo = pedido.propina_efectivo
  const tarjeta = pedido.propina_tarjeta
  
  if (total === 0) return 'Sin propina'
  
  return `$${total.toFixed(2)}`
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

// Computed para pedidos del día filtrados y ordenados
 const filteredPedidosDelDia = computed(() => {
   if (!dashboardData.value) return []
   
   let pedidos = [...dashboardData.value.pedidos_del_dia]
   
   // Filtrar por método de pago
   if (selectedPaymentMethod.value !== 'todos') {
     pedidos = pedidos.filter(p => p.metodo_pago === selectedPaymentMethod.value)
   }
   
   // Ordenar por fecha_creacion (más reciente primero por defecto)
   pedidos.sort((a, b) => {
     const dateA = new Date(a.fecha_creacion).getTime()
     const dateB = new Date(b.fecha_creacion).getTime()
     return sortDescending.value ? dateB - dateA : dateA - dateB
   })
   
   return pedidos
 })

 // Resumen de pedidos filtrados
 const filteredSummary = computed(() => {
   if (!filteredPedidosDelDia.value.length) return null
   
   const totals = filteredPedidosDelDia.value.reduce((acc, pedido) => ({
     total: acc.total + pedido.total,
     propina_efectivo: acc.propina_efectivo + pedido.propina_efectivo,
     propina_tarjeta: acc.propina_tarjeta + pedido.propina_tarjeta,
     propina_total: acc.propina_total + pedido.propina_total,
     count: acc.count + 1
   }), {
     total: 0,
     propina_efectivo: 0,
     propina_tarjeta: 0,
     propina_total: 0,
     count: 0
   })
   
   return {
     ...totals,
     promedio_ticket: totals.count > 0 ? totals.total / totals.count : 0
   }
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
  propinas: {
    efectivo: number
    tarjeta: number
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
  pedidos_del_dia: Array<{
    id: number
    numero_display: string
    mesa: string | null
    nombre_cliente: string | null
    tipo_orden: string
    total: number
    metodo_pago: string | null
    propina_efectivo: number
    propina_tarjeta: number
    propina_total: number
    fecha_creacion: string
    articulos_pedido: Array<{
      platillo: string
      cantidad: number
      precio_cobrado: number
      modificaciones: string | null
    }>
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

interface Proveedor {
  id: number
  nombre: string
  telefono?: string | null
  direccion?: string | null
  notas?: string | null
}

interface CategoriaArticulo {
  id: number
  nombre: string
}

interface Articulo {
  id: number
  nombre: string
  unidad: string
  costo_estandar: number
  categoria_id: number
  categoria: CategoriaArticulo
}

interface GastoDetalle {
  id: number
  articulo_id: number
  cantidad: number
  precio_unitario: number
  subtotal_linea: number
  articulo: Articulo
}

interface Gasto {
  id: number
  proveedor_id: number
  proveedor: Proveedor
  tipo_gasto: 'directo' | 'indirecto' | 'nomina'
  metodo_pago: 'efectivo' | 'tarjeta'
  descripcion?: string | null
  folio?: string | null
  subtotal: number
  total: number
  total_manual?: number | null
  notas?: string | null
  fecha_gasto: string
  detalles: GastoDetalle[]
}

interface GastoDetalleForm {
  articulo_id: number | null
  cantidad: number
  precio_unitario: number
}

interface GastoForm {
  proveedor_id: number | null
  tipo_gasto: 'directo' | 'indirecto' | 'nomina'
  metodo_pago: 'efectivo' | 'tarjeta'
  descripcion: string
  folio: string
  total_manual: number | null
  notas: string
  detalles: GastoDetalleForm[]
}

interface ProveedorForm {
  nombre: string
  telefono: string
  direccion: string
  notas: string
}

interface ArticuloForm {
  nombre: string
  unidad: string
  costo_estandar: number
  categoria_id: number | null
}

interface CategoriaForm {
  nombre: string
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

 const openOrderModal = (order: any) => {
   selectedOrder.value = order
   showOrderModal.value = true
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
    const params: Record<string, string> = {}
    if (gastoFilters.value.fecha_inicio) params.fecha_inicio = gastoFilters.value.fecha_inicio
    if (gastoFilters.value.fecha_fin) params.fecha_fin = gastoFilters.value.fecha_fin
    if (gastoFilters.value.proveedor_id !== null && gastoFilters.value.proveedor_id !== '') {
      params.proveedor_id = String(gastoFilters.value.proveedor_id)
    }
    if (gastoFilters.value.tipo_gasto) params.tipo_gasto = gastoFilters.value.tipo_gasto
    if (gastoFilters.value.metodo_pago) params.metodo_pago = gastoFilters.value.metodo_pago
    if (gastoFilters.value.categoria_id !== null && gastoFilters.value.categoria_id !== '') {
      params.categoria_id = String(gastoFilters.value.categoria_id)
    }

    const response = await api.get('/gastos/', { params })
    gastosList.value = response.data
  } catch (err: any) {
    error.value = 'Error al cargar gastos'
    console.error('Gastos error:', err)
  }
}

const loadProveedores = async () => {
  try {
    const response = await api.get('/gastos/proveedores')
    proveedoresList.value = response.data
  } catch (err: any) {
    error.value = 'Error al cargar proveedores'
    console.error('Proveedores error:', err)
  }
}

const loadCategoriasArticulo = async () => {
  try {
    const response = await api.get('/gastos/categorias-articulo')
    categoriasArticuloList.value = response.data
    if (!categoriasSeeded.value && categoriasArticuloList.value.length === 0) {
      categoriasSeeded.value = true
      await seedCategoriasArticulo()
      const refreshed = await api.get('/gastos/categorias-articulo')
      categoriasArticuloList.value = refreshed.data
    }
  } catch (err: any) {
    error.value = 'Error al cargar categorías'
    console.error('Categorias error:', err)
  }
}

const seedCategoriasArticulo = async () => {
  const seed = ['frutas', 'verduras', 'proteinas', 'lacteos', 'abarrotes', 'limpieza', 'plasticos']
  for (const nombre of seed) {
    try {
      await api.post('/gastos/categorias-articulo', { nombre })
    } catch (err) {
      // Ignorar duplicados en seed
    }
  }
}

const loadArticulos = async () => {
  try {
    const params: Record<string, string> = {}
    if (selectedArticuloCategoria.value) {
      params.categoria_id = String(selectedArticuloCategoria.value)
    }
    const response = await api.get('/gastos/articulos', { params })
    articulosList.value = response.data
  } catch (err: any) {
    error.value = 'Error al cargar artículos'
    console.error('Articulos error:', err)
  }
}

const resetGastoForm = () => {
  newGasto.value = {
    proveedor_id: null,
    tipo_gasto: 'directo',
    metodo_pago: 'efectivo',
    descripcion: '',
    folio: '',
    total_manual: null,
    notas: '',
    detalles: []
  }
}

const addDetalleLine = () => {
  newGasto.value.detalles.push({ articulo_id: null, cantidad: 1, precio_unitario: 0 })
}

const removeDetalleLine = (index: number) => {
  newGasto.value.detalles.splice(index, 1)
}

const getArticuloById = (articuloId: number | null) => {
  return articulosList.value.find(articulo => articulo.id === articuloId)
}

const calcularSubtotal = (detalles: GastoDetalleForm[]) => {
  return detalles.reduce((acc, detalle) => acc + detalle.cantidad * detalle.precio_unitario, 0)
}

const getGastoTotal = (gasto: GastoForm) => {
  const subtotal = calcularSubtotal(gasto.detalles)
  return gasto.total_manual !== null && gasto.total_manual !== undefined ? gasto.total_manual : subtotal
}

const formatCurrency = (value: number | string | null | undefined) => {
  const parsed = Number(value ?? 0)
  return Number.isFinite(parsed) ? parsed.toFixed(2) : '0.00'
}

const addGasto = async () => {
  try {
    if (!newGasto.value.proveedor_id) {
      error.value = 'Selecciona un proveedor'
      return
    }

    if (newGasto.value.tipo_gasto !== 'nomina') {
      const hasInvalidLine = newGasto.value.detalles.some(detalle => !detalle.articulo_id)
      if (hasInvalidLine) {
        error.value = 'Selecciona artículos en todas las líneas'
        return
      }
      if (newGasto.value.detalles.length === 0) {
        error.value = 'Agrega al menos un artículo'
        return
      }
    }

    if (newGasto.value.tipo_gasto === 'nomina' && newGasto.value.total_manual === null) {
      error.value = 'Captura el total de nómina'
      return
    }

    const payload = {
      proveedor_id: Number(newGasto.value.proveedor_id),
      tipo_gasto: newGasto.value.tipo_gasto,
      metodo_pago: newGasto.value.metodo_pago,
      descripcion: newGasto.value.descripcion || null,
      folio: newGasto.value.folio || null,
      total_manual: newGasto.value.total_manual,
      notas: newGasto.value.notas || null,
      detalles: newGasto.value.tipo_gasto === 'nomina'
        ? []
        : newGasto.value.detalles.map(detalle => ({
            articulo_id: Number(detalle.articulo_id),
            cantidad: detalle.cantidad,
            precio_unitario: detalle.precio_unitario
          }))
    }

    await api.post('/gastos/', payload)
    showAddGastoModal.value = false
    resetGastoForm()
    await loadGastosList()
    error.value = ''
  } catch (err: any) {
    error.value = err?.response?.data?.detail || 'Error al crear gasto'
    console.error('Add gasto error:', err)
  }
}

const toggleGastoExpanded = (gastoId: number) => {
  if (expandedGastos.value.includes(gastoId)) {
    expandedGastos.value = expandedGastos.value.filter(id => id !== gastoId)
  } else {
    expandedGastos.value.push(gastoId)
  }
}

const isGastoExpanded = (gastoId: number) => expandedGastos.value.includes(gastoId)

const openNewProveedor = () => {
  editingProveedor.value = null
  proveedorForm.value = { nombre: '', telefono: '', direccion: '', notas: '' }
  showProveedorModal.value = true
}

const editProveedor = (proveedor: Proveedor) => {
  editingProveedor.value = proveedor
  proveedorForm.value = {
    nombre: proveedor.nombre,
    telefono: proveedor.telefono || '',
    direccion: proveedor.direccion || '',
    notas: proveedor.notas || ''
  }
  showProveedorModal.value = true
}

const saveProveedor = async () => {
  try {
    if (!proveedorForm.value.nombre) {
      error.value = 'Nombre de proveedor requerido'
      return
    }
    if (editingProveedor.value) {
      await api.put(`/gastos/proveedores/${editingProveedor.value.id}`, proveedorForm.value)
    } else {
      await api.post('/gastos/proveedores', proveedorForm.value)
    }
    showProveedorModal.value = false
    await loadProveedores()
    error.value = ''
  } catch (err: any) {
    error.value = err?.response?.data?.detail || 'Error al guardar proveedor'
    console.error('Proveedor error:', err)
  }
}

const openNewArticulo = () => {
  editingArticulo.value = null
  articuloForm.value = { nombre: '', unidad: 'kg', costo_estandar: 0, categoria_id: null }
  showArticuloModal.value = true
}

const editArticulo = (articulo: Articulo) => {
  editingArticulo.value = articulo
  articuloForm.value = {
    nombre: articulo.nombre,
    unidad: articulo.unidad,
    costo_estandar: articulo.costo_estandar,
    categoria_id: articulo.categoria_id
  }
  showArticuloModal.value = true
}

const saveArticulo = async () => {
  try {
    if (!articuloForm.value.nombre || !articuloForm.value.categoria_id) {
      error.value = 'Nombre y categoría del artículo son requeridos'
      return
    }
    const payload = {
      ...articuloForm.value,
      categoria_id: Number(articuloForm.value.categoria_id)
    }
    if (editingArticulo.value) {
      await api.put(`/gastos/articulos/${editingArticulo.value.id}`, payload)
    } else {
      await api.post('/gastos/articulos', payload)
    }
    showArticuloModal.value = false
    await loadArticulos()
    error.value = ''
  } catch (err: any) {
    error.value = err?.response?.data?.detail || 'Error al guardar artículo'
    console.error('Articulo error:', err)
  }
}

const openNewCategoria = () => {
  editingCategoria.value = null
  categoriaForm.value = { nombre: '' }
  showCategoriaModal.value = true
}

const editCategoria = (categoria: CategoriaArticulo) => {
  editingCategoria.value = categoria
  categoriaForm.value = { nombre: categoria.nombre }
  showCategoriaModal.value = true
}

const saveCategoria = async () => {
  try {
    if (!categoriaForm.value.nombre) {
      error.value = 'Nombre de categoría requerido'
      return
    }
    if (editingCategoria.value) {
      await api.put(`/gastos/categorias-articulo/${editingCategoria.value.id}`, categoriaForm.value)
    } else {
      await api.post('/gastos/categorias-articulo', categoriaForm.value)
    }
    showCategoriaModal.value = false
    await loadCategoriasArticulo()
    error.value = ''
  } catch (err: any) {
    error.value = err?.response?.data?.detail || 'Error al guardar categoría'
    console.error('Categoria error:', err)
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
      loadProveedores(),
      loadCategoriasArticulo(),
      loadArticulos(),
      loadPlatillosList(),
      loadUsuariosList()
    ])
    
    // Cargar configuración después de las otras operaciones
    loadConfig()
  })

</script>