import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api/client'
import { websocketService } from '@/services/websocket'
import { enviarOEncolar } from '@/services/offlineQueue'
import type { PedidoResponse } from '@/types'
import { EstadoPedido, EstadoArticuloPedido, ESTADOS_PEDIDO_FINALES } from '@/constants/estados'

type WsClientType = 'kds' | 'caja' | 'mesero'

export const usePedidosStore = defineStore('pedidos', () => {
  // Estado
  const pedidos = ref<PedidoResponse[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const lastUpdate = ref<Date | null>(null)
  // Espejo reactivo del estado real de la conexión (antes era un ref que se
  // congelaba en true tras la primera conexión y nunca volvía a false)
  const wsConnected = computed(() => websocketService.isConnected.value)
  const isOutSoundThrottled = ref(false)
  const wsClientType = ref<WsClientType | null>(null)
  const listenersRegistered = ref(false)
  // IDs de pedidos que el server reporta sin acuse por >60s (ver
  // websocket_manager._avisar_acks_vencidos): puede indicar que este cliente
  // está perdiendo eventos silenciosamente aunque la conexión siga "viva".
  const pedidosSinAcuse = ref<number[]>([])

  // Getters computados
  const pedidosPorEstado = computed(() => {
    const grupos: Record<string, PedidoResponse[]> = {
      [EstadoPedido.PENDIENTE]: [],
      [EstadoPedido.PREPARANDO]: [],
      [EstadoPedido.LISTO]: [],
      [EstadoPedido.ENTREGADO]: [],
      [EstadoPedido.CUENTA_SOLICITADA]: [],
      [EstadoPedido.PAGADO]: [],
      [EstadoPedido.CANCELADO]: [],
      [EstadoPedido.DIVIDIDO]: []
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
      !([EstadoPedido.ENTREGADO, EstadoPedido.CUENTA_SOLICITADA, EstadoPedido.PAGADO, EstadoPedido.CANCELADO, EstadoPedido.DIVIDIDO] as string[]).includes(p.estado)
    ).slice(0, 60) // Limitar a 60 para performance
  })

  const pedidosCaja = computed(() => {
    // Para CAJA: mostrar todos los pedidos del día (incluye entregados y cuenta_solicitada)
    // Excluir solo los pagados y cancelados que ya no requieren seguimiento
    
    return pedidos.value.filter(p => {
      // Solo filtrar por estado, la fecha ya viene filtrada desde el backend
      const noEstaPagadoNiCancelado = !(ESTADOS_PEDIDO_FINALES as string[]).includes(p.estado)

      return noEstaPagadoNiCancelado
    }).sort((a, b) => {
      // Ordenar: pendientes de pago primero, luego por número de orden
      if (a.estado === EstadoPedido.CUENTA_SOLICITADA && b.estado !== EstadoPedido.CUENTA_SOLICITADA) return -1
      if (b.estado === EstadoPedido.CUENTA_SOLICITADA && a.estado !== EstadoPedido.CUENTA_SOLICITADA) return 1
      return (a.numero_display || '').localeCompare(b.numero_display || '')
    })
  })

  const pedidosPendientesPago = computed(() => {
    return pedidos.value.filter(p => p.estado === EstadoPedido.CUENTA_SOLICITADA)
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
        case EstadoPedido.PENDIENTE: stats.pendiente++; break
        case EstadoPedido.PREPARANDO: stats.preparando++; break
        case EstadoPedido.LISTO: stats.listo++; break
        case EstadoPedido.ENTREGADO: stats.entregado++; break
        case EstadoPedido.CUENTA_SOLICITADA: stats.cuenta_solicitada++; break
        case EstadoPedido.PAGADO: stats.pagado++; break
        case EstadoPedido.CANCELADO: stats.cancelado++; break
        case EstadoPedido.DIVIDIDO: stats.dividido++; break
      }
    })

    return stats
  })

  // Acciones
  let lastFullSync = 0

  async function loadInitialData(showLoading = true): Promise<void> {
    if (showLoading) loading.value = true
    error.value = null

    try {
      console.log('🔄 Cargando datos de pedidos...')
      lastFullSync = Date.now()
      const { data } = await api.get<PedidoResponse[]>('/pedidos')
      pedidos.value = data
      lastUpdate.value = new Date()
      console.log(`✅ ${data.length} pedidos cargados`)
    } catch (e: any) {
      error.value = e?.response?.data?.detail || 'Error cargando pedidos'
      console.error('❌ Error cargando datos:', e)
    } finally {
      if (showLoading) loading.value = false
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
    // Evitar acumular listeners duplicados si initWebSocket se llama varias veces
    if (listenersRegistered.value) return
    listenersRegistered.value = true

    console.log('📡 Configurando listeners de WebSocket...')

    // Re-sincronizar en cada (re)conexión: la DB es la fuente de verdad y todo
    // lo ocurrido durante una desconexión no se reenvía por WebSocket.
    // Debounce de 10s: con WS inestable (flapping) evita re-fetchear la lista
    // completa en cada reconexión
    websocketService.on('connection_open', () => {
      if (Date.now() - lastFullSync < 10_000) {
        console.log('🔁 WebSocket (re)conectado, sync reciente — se omite re-fetch')
        return
      }
      console.log('🔁 WebSocket (re)conectado, re-sincronizando pedidos...')
      loadInitialData(false)
    })

    // Listener para nuevos pedidos
    websocketService.on('pedido_created', (data: any) => {
      console.log('🆕 Nuevo pedido recibido via WebSocket:', data.pedido)
      lastUpdate.value = new Date()
      handlePedidoCreated(data.pedido)
    })

    // Listener para cambios de estado de pedidos
    websocketService.on('pedido_estado_changed', (data: any) => {
      console.log('🔄 Estado de pedido cambiado via WebSocket:', data)
      lastUpdate.value = new Date()
      handlePedidoEstadoChanged(data.pedido_id, data.nuevo_estado, data.pedido)
    })

    // Listener para cambios de estado de artículos
    websocketService.on('articulo_estado_changed', (data: any) => {
      console.log('🍽️ Estado de artículo cambiado via WebSocket:', data)
      lastUpdate.value = new Date()
      handleArticuloEstadoChanged(data.pedido_id, data.articulo_id, data.nuevo_estado, data.pedido)
    })

    // El server nos dice qué pedidos llevan >60s sin acuse (ver 2.9). Es un
    // snapshot, no un delta: reemplaza la lista completa cada vez.
    websocketService.on('ack_timeout', (data: any) => {
      console.warn('⚠️ Pedidos sin acuse >60s:', data.pedido_ids)
      pedidosSinAcuse.value = data.pedido_ids || []
    })

    // Reconectar limpia cualquier alerta de acuse: los mensajes pendientes de
    // la conexión vieja ya no existen del lado del server tras el reconnect.
    websocketService.on('connection_open', () => {
      pedidosSinAcuse.value = []
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
      if (nuevoEstado === EstadoPedido.PENDIENTE && estadoAnterior !== EstadoPedido.PENDIENTE) {
        playKitchenSound('/notification_in.mp3');
      }

      // Sonido de SALIDA: si un pedido se marca como listo (con freno)
      if (nuevoEstado === EstadoPedido.LISTO && estadoAnterior !== EstadoPedido.LISTO) {
        playKitchenSound('/notification_out.mp3', true);
      }

      // Notificación visual para estados importantes
      if (([EstadoPedido.LISTO, EstadoPedido.CUENTA_SOLICITADA, EstadoPedido.PAGADO] as string[]).includes(nuevoEstado)) {
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
      if (nuevoEstado === EstadoPedido.LISTO) {
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
      [EstadoPedido.PENDIENTE]: 'Pendiente',
      [EstadoPedido.PREPARANDO]: 'Preparando',
      [EstadoPedido.LISTO]: 'Listo',
      [EstadoPedido.ENTREGADO]: 'Entregado',
      [EstadoPedido.CUENTA_SOLICITADA]: 'Cuenta Solicitada',
      [EstadoPedido.PAGADO]: 'Pagado',
      [EstadoPedido.CANCELADO]: 'Cancelado',
      [EstadoPedido.DIVIDIDO]: 'Dividido'
    }
    return labels[estado] || estado
  }

  function disconnectWebSocket(): void {
    websocketService.disconnect()
    wsClientType.value = null
    console.log('👋 WebSocket desconectado desde store')
  }

  // Funciones para operaciones REST (mantener funcionalidad existente)
  async function createPedido(
    pedidoData: any
  ): Promise<{ pedido: PedidoResponse } | { queued: true } | null> {
    loading.value = true
    error.value = null

    try {
      // Sin conexión: enviarOEncolar persiste el request en localStorage y lo
      // reintenta solo (reusa pedidoData.client_request_id para idempotencia
      // — si ya llegó al backend en un intento anterior, el backend devuelve
      // el pedido existente en vez de duplicarlo).
      const resultado = await enviarOEncolar<PedidoResponse>(
        'post',
        '/pedidos/',
        pedidoData,
        pedidoData.client_request_id
      )

      if (resultado.estado === 'encolado') {
        return { queued: true }
      }

      if (resultado.estado === 'error') {
        error.value = resultado.error?.response?.data?.detail || 'Error creando pedido'
        console.error('❌ Error creando pedido:', resultado.error)
        return null
      }

      console.log(`✅ Pedido creado via REST: #${resultado.data.numero_display}`)

      // El WebSocket debería notificar automáticamente, pero por si acaso
      if (!wsConnected.value) {
        handlePedidoCreated(resultado.data)
      }

      return { pedido: resultado.data }
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
      
      // Si el WebSocket NO está conectado, actualizar el estado localmente de forma manual
      // Si el WebSocket SI está conectado, handleArticuloEstadoChanged se encargará cuando llegue el evento
      if (!wsConnected.value) {
        const pedidoId = data.pedido_id
        const pedidoEstado = data.pedido_estado
        
        const pedidoIndex = pedidos.value.findIndex(p => p.id === pedidoId)
        if (pedidoIndex !== -1) {
          // Actualizar el estado del artículo
          const articulo = pedidos.value[pedidoIndex].articulos_pedido?.find(a => a.id === articuloId)
          if (articulo) {
            articulo.estado_item = nuevoEstado as EstadoArticuloPedido
          }
          // Actualizar el estado del pedido por si cambió
          pedidos.value[pedidoIndex].estado = pedidoEstado
        }
      }
      
      return true
    } catch (e: any) {
      error.value = e?.response?.data?.detail || 'Error actualizando artículo'
      console.error('❌ Error actualizando artículo:', e)
      return false
    }
  }

  // Refresh manual/polling: siempre recarga — la DB es la fuente de verdad
  async function refreshPedidos(): Promise<void> {
    await loadInitialData(false) // No mostrar loading en refrescos de polling
  }

  // Reset del store
  function $reset(): void {
    pedidos.value = []
    loading.value = false
    error.value = null
    lastUpdate.value = null
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
    pedidosSinAcuse,

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