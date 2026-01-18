import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api/client'
import { websocketService } from '@/services/websocket'
import type { PedidoResponse } from '@/types'

type WsClientType = 'kds' | 'caja' | 'mesero'

export const usePedidosStore = defineStore('pedidos', () => {
  // Estado
  const pedidos = ref<PedidoResponse[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const lastUpdate = ref<Date | null>(null)
  const wsConnected = ref(false)
  const isOutSoundThrottled = ref(false)
  const wsClientType = ref<WsClientType | null>(null)

  // Getters computados
  const pedidosPorEstado = computed(() => {
    const grupos: Record<string, PedidoResponse[]> = {
      pendiente: [],
      preparando: [],
      listo: [],
      entregado: [],
      cuenta_solicitada: [],
      pagado: [],
      cancelado: [],
      dividido: []
    }

    pedidos.value.forEach(pedido => {
      if (grupos[pedido.estado]) {
        grupos[pedido.estado].push(pedido)
      }
    })

    return grupos
  })

  const pedidosKDS = computed(() => {
    // Para KDS: mostrar solo pedidos activos (no entregados ni pagados)
    return pedidos.value.filter(p => 
      !['entregado', 'cuenta_solicitada', 'pagado', 'cancelado', 'dividido'].includes(p.estado)
    ).slice(0, 60) // Limitar a 60 para performance
  })

  const pedidosCaja = computed(() => {
    // Para CAJA: mostrar todos los pedidos del día (incluye entregados y cuenta_solicitada)
    // Excluir solo los pagados y cancelados que ya no requieren seguimiento
    
    return pedidos.value.filter(p => {
      // Solo filtrar por estado, la fecha ya viene filtrada desde el backend
      const noEstaPagadoNiCancelado = !['pagado', 'cancelado', 'dividido'].includes(p.estado)
      
      return noEstaPagadoNiCancelado
    }).sort((a, b) => {
      // Ordenar: pendientes de pago primero, luego por número de orden
      if (a.estado === 'cuenta_solicitada' && b.estado !== 'cuenta_solicitada') return -1
      if (b.estado === 'cuenta_solicitada' && a.estado !== 'cuenta_solicitada') return 1
      return (a.numero_display || '').localeCompare(b.numero_display || '')
    })
  })

  const pedidosPendientesPago = computed(() => {
    return pedidos.value.filter(p => p.estado === 'cuenta_solicitada')
  })

  const estadisticasPedidos = computed(() => {
    // Estadísticas para la caja - pedidos del día (ya filtrados desde backend)
    const pedidosHoy = pedidos.value

    const stats = {
      total: pedidosHoy.length,
      pendiente: 0,
      preparando: 0,
      listo: 0,
      entregado: 0,
      cuenta_solicitada: 0,
      pagado: 0,
      cancelado: 0,
      dividido: 0
    }

    pedidosHoy.forEach(pedido => {
      switch (pedido.estado) {
        case 'pendiente': stats.pendiente++; break
        case 'preparando': stats.preparando++; break
        case 'listo': stats.listo++; break
        case 'entregado': stats.entregado++; break
        case 'cuenta_solicitada': stats.cuenta_solicitada++; break
        case 'pagado': stats.pagado++; break
        case 'cancelado': stats.cancelado++; break
        case 'dividido': stats.dividido++; break
      }
    })

    return stats
  })

  // Acciones
  async function loadInitialData(): Promise<void> {
    loading.value = true
    error.value = null

    try {
      console.log('🔄 Cargando datos iniciales de pedidos...')
      const { data } = await api.get<PedidoResponse[]>('/pedidos')
      pedidos.value = data
      lastUpdate.value = new Date()
      console.log(`✅ ${data.length} pedidos cargados inicialmente`)
    } catch (e: any) {
      error.value = e?.response?.data?.detail || 'Error cargando pedidos'
      console.error('❌ Error cargando datos iniciales:', e)
    } finally {
      loading.value = false
    }
  }


  async function initWebSocket(clientType: WsClientType): Promise<boolean> {
    wsClientType.value = clientType // Guardar el tipo de cliente
    console.log(`🔌 Store configurado para cliente tipo: ${wsClientType.value}`)

    try {
      console.log(`🌐 Inicializando WebSocket para ${clientType}...`)
      
      // Configurar listeners antes de conectar
      setupWebSocketListeners()
      
      // Conectar al WebSocket
      const connected = await websocketService.connect(clientType)
      
      if (connected) {
        wsConnected.value = true
        console.log(`✅ WebSocket conectado para ${clientType}`)
        return true
      } else {
        console.error(`❌ No se pudo conectar WebSocket para ${clientType}`)
        return false
      }
      
    } catch (error) {
      console.error('❌ Error inicializando WebSocket:', error)
      error.value = `Error WebSocket: ${error}`
      return false
    }
  }

  function setupWebSocketListeners(): void {
    console.log('📡 Configurando listeners de WebSocket...')

    // Listener para nuevos pedidos
    websocketService.on('pedido_created', (data: any) => {
      console.log('🆕 Nuevo pedido recibido via WebSocket:', data.pedido)
      handlePedidoCreated(data.pedido)
    })

    // Listener para cambios de estado de pedidos
    websocketService.on('pedido_estado_changed', (data: any) => {
      console.log('🔄 Estado de pedido cambiado via WebSocket:', data)
      handlePedidoEstadoChanged(data.pedido_id, data.nuevo_estado, data.pedido)
    })

    // Listener para cambios de estado de artículos
    websocketService.on('articulo_estado_changed', (data: any) => {
      console.log('🍽️ Estado de artículo cambiado via WebSocket:', data)
      handleArticuloEstadoChanged(data.pedido_id, data.articulo_id, data.nuevo_estado, data.pedido)
    })

    // Listener genérico para debugging
    websocketService.on('*', (message: any) => {
      console.log('📡 WebSocket message:', message)
      lastUpdate.value = new Date()
    })
  }

  function playKitchenSound(soundFile: string, throttle = false): void {
    // El sonido solo debe sonar en las vistas de cocina
    if (wsClientType.value !== 'kds') {
      return
    }

    if (throttle) {
      if (isOutSoundThrottled.value) {
        return // Sonido frenado, no hacer nada
      }
      isOutSoundThrottled.value = true
      setTimeout(() => {
        isOutSoundThrottled.value = false
      }, 500) // 500ms de "freno"
    }

    try {
      // Asume que los archivos de sonido están en /public/
      const audio = new Audio(soundFile)
      audio.play().catch(e => console.error(`Error al reproducir ${soundFile}:`, e))
    } catch (e) {
      console.error(`No se pudo reproducir el sonido ${soundFile}.`, e)
    }
  }

  function handlePedidoCreated(nuevoPedido: PedidoResponse): void {
    // Verificar si el pedido ya existe (evitar duplicados)
    const existePedido = pedidos.value.find(p => p.id === nuevoPedido.id)
    
    if (!existePedido) {
      // Agregar al inicio de la lista
      pedidos.value.unshift(nuevoPedido)
      console.log(`✅ Pedido #${nuevoPedido.numero_display} agregado a la lista`)
      
      playKitchenSound('/notification_in.mp3') // Sonido de entrada

      // Mostrar notificación visual si el navegador lo soporta
      showNotification(`Nuevo pedido #${nuevoPedido.numero_display}`, {
        body: `Mesa: ${nuevoPedido.mesa || 'N/A'} - Cliente: ${nuevoPedido.nombre_cliente || 'N/A'}`,
        icon: '/favicon.ico'
      })
    } else {
      console.log(`ℹ️ Pedido #${nuevoPedido.numero_display} ya existe, actualizando...`)
      handlePedidoEstadoChanged(nuevoPedido.id, nuevoPedido.estado, nuevoPedido)
    }
  }

  function handlePedidoEstadoChanged(pedidoId: number, nuevoEstado: string, pedidoActualizado: PedidoResponse): void {
    const index = pedidos.value.findIndex(p => p.id === pedidoId)
    
    if (index !== -1) {
      const estadoAnterior = pedidos.value[index].estado;
      // Actualizar pedido existente con todos los datos nuevos
      pedidos.value[index] = { ...pedidos.value[index], ...pedidoActualizado }
      console.log(`🔄 Pedido #${pedidos.value[index].numero_display} actualizado a estado: ${nuevoEstado}`)
      
      // Sonido de ENTRADA: si un pedido vuelve a pendiente (se agregaron items)
      if (nuevoEstado === 'pendiente' && estadoAnterior !== 'pendiente') {
        playKitchenSound('/notification_in.mp3');
      }

      // Sonido de SALIDA: si un pedido se marca como listo (con freno)
      if (nuevoEstado === 'listo' && estadoAnterior !== 'listo') {
        playKitchenSound('/notification_out.mp3', true);
      }

      // Notificación visual para estados importantes
      if (['listo', 'cuenta_solicitada', 'pagado'].includes(nuevoEstado)) {
        showNotification(`Pedido #${pedidos.value[index].numero_display}`, {
          body: `Cambió a: ${getEstadoLabel(nuevoEstado)}`,
          icon: '/favicon.ico'
        })
      }
    } else {
      // Si el pedido no existe, agregarlo (puede pasar si se conectó después)
      console.log(`ℹ️ Pedido #${pedidoActualizado.numero_display} no encontrado, agregando...`)
      pedidos.value.push(pedidoActualizado)
      playKitchenSound('/notification_in.mp3'); // Sonido de entrada para un pedido nuevo en la sesión
    }
  }

  function handleArticuloEstadoChanged(pedidoId: number, articuloId: number, nuevoEstado: string, pedidoActualizado: PedidoResponse): void {
    const index = pedidos.value.findIndex(p => p.id === pedidoId)
    
    if (index !== -1) {
      // Sonido de SALIDA: si un artículo se marca como listo (con freno)
      if (nuevoEstado === 'listo') {
        playKitchenSound('/notification_out.mp3', true);
      }
      // Actualizar pedido completo (incluye los artículos actualizados)
      pedidos.value[index] = { ...pedidos.value[index], ...pedidoActualizado }
      console.log(`🍽️ Artículo ${articuloId} del pedido #${pedidos.value[index].numero_display} → ${nuevoEstado}`)
    }
  }

  function showNotification(title: string, options?: NotificationOptions): void {
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification(title, options)
    } else if ('Notification' in window && Notification.permission === 'default') {
      // Solicitar permiso para notificaciones
      Notification.requestPermission().then(permission => {
        if (permission === 'granted') {
          new Notification(title, options)
        }
      })
    }
  }

  function getEstadoLabel(estado: string): string {
    const labels: Record<string, string> = {
      'pendiente': 'Pendiente',
      'preparando': 'Preparando',
      'listo': 'Listo',
      'entregado': 'Entregado',
      'cuenta_solicitada': 'Cuenta Solicitada',
      'pagado': 'Pagado',
      'cancelado': 'Cancelado',
      'dividido': 'Dividido'
    }
    return labels[estado] || estado
  }

  function disconnectWebSocket(): void {
    websocketService.disconnect()
    wsConnected.value = false
    wsClientType.value = null
    console.log('👋 WebSocket desconectado desde store')
  }

  // Funciones para operaciones REST (mantener funcionalidad existente)
  async function createPedido(pedidoData: any): Promise<PedidoResponse | null> {
    loading.value = true
    error.value = null

    try {
      const { data } = await api.post<PedidoResponse>('/pedidos/', pedidoData)
      console.log(`✅ Pedido creado via REST: #${data.numero_display}`)
      
      // El WebSocket debería notificar automáticamente, pero por si acaso
      if (!wsConnected.value) {
        handlePedidoCreated(data)
      }
      
      return data
    } catch (e: any) {
      error.value = e?.response?.data?.detail || 'Error creando pedido'
      console.error('❌ Error creando pedido:', e)
      return null
    } finally {
      loading.value = false
    }
  }

  async function updatePedidoEstado(
    pedidoId: number, 
    nuevoEstado: string, 
    metodoPago?: string, 
    propinaEfectivo?: number, 
    propinaTarjeta?: number
  ): Promise<boolean> {
    // NO poner loading = true para updates individuales
    error.value = null

    try {
      const updateData: any = { estado: nuevoEstado }
      if (metodoPago) {
        updateData.metodo_pago = metodoPago
      }
      if (propinaEfectivo !== undefined) {
        updateData.propina_efectivo = propinaEfectivo
      }
      if (propinaTarjeta !== undefined) {
        updateData.propina_tarjeta = propinaTarjeta
      }

      const { data } = await api.put<PedidoResponse>(`/pedidos/${pedidoId}`, updateData)
      console.log(`✅ Estado actualizado via REST: #${data.numero_display} → ${nuevoEstado}`)
      
      // El WebSocket debería notificar automáticamente
      if (!wsConnected.value) {
        handlePedidoEstadoChanged(pedidoId, nuevoEstado, data)
      }
      
      return true
    } catch (e: any) {
      error.value = e?.response?.data?.detail || 'Error actualizando pedido'
      console.error('❌ Error actualizando pedido:', e)
      return false
    }
    // NO hay finally que ponga loading = false
  }

  async function updateArticuloEstado(articuloId: number, nuevoEstado: string): Promise<boolean> {
    // NO poner loading = true para updates individuales
    error.value = null

    try {
      const { data } = await api.put(`/pedidos/articulos/${articuloId}`, {
        estado_item: nuevoEstado
      })
      console.log(`✅ Artículo actualizado via REST: ${articuloId} → ${nuevoEstado}`)
      
      // El WebSocket debería notificar automáticamente
      if (!wsConnected.value) {
        // Buscar el pedido y actualizarlo - pero sin loading general
        console.log('⚠️ WebSocket desconectado, actualizando datos...')
        await loadInitialData()
      }
      
      return true
    } catch (e: any) {
      error.value = e?.response?.data?.detail || 'Error actualizando artículo'
      console.error('❌ Error actualizando artículo:', e)
      return false
    }
    // NO hay finally que ponga loading = false
  }

  // Función para refresh manual (fallback)
  async function refreshPedidos(): Promise<void> {
    if (!wsConnected.value) {
      console.log('🔄 WebSocket desconectado, refrescando manualmente...')
      await loadInitialData()
    } else {
      console.log('ℹ️ WebSocket activo, no es necesario refresh manual')
    }
  }

  // Reset del store
  function $reset(): void {
    pedidos.value = []
    loading.value = false
    error.value = null
    lastUpdate.value = null
    wsConnected.value = false
    wsClientType.value = null
    disconnectWebSocket()
  }

  return {
    // Estado
    pedidos,
    loading,
    error,
    lastUpdate,
    wsConnected,
    
    // Getters
    pedidosPorEstado,
    pedidosKDS,
    pedidosCaja,
    pedidosPendientesPago,
    estadisticasPedidos,
    
    // Acciones
    loadInitialData,
    initWebSocket,
    disconnectWebSocket,
    createPedido,
    updatePedidoEstado,
    updateArticuloEstado,
    refreshPedidos,
    $reset
  }
})