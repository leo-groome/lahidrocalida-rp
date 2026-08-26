import { ref, reactive } from 'vue'
import { useAuthStore } from '@/stores/auth'
import type { PedidoResponse } from '@/types'

export interface WebSocketMessage {
  type: string
  data: any
  timestamp?: string
  message_id?: string
}

export interface WebSocketConfig {
  reconnectInterval: number
  maxReconnectAttempts: number
  heartbeatInterval: number
}

export class WebSocketService {
  private ws: WebSocket | null = null
  private reconnectAttempts = 0
  private heartbeatTimer: number | null = null
  private reconnectTimer: number | null = null
  private listeners: Map<string, Array<(data: any) => void>> = new Map()
  private clientType: 'kds' | 'caja' | 'mesero' | null = null
  private intentionalDisconnect = false
  private visibilityHandler: (() => void) | null = null
  private onlineHandler: (() => void) | null = null

  // Estado reactivo
  public isConnected = ref(false)
  public connectionStatus = ref<'disconnected' | 'connecting' | 'connected' | 'reconnecting'>('disconnected')
  public lastError = ref<string | null>(null)
  public stats = reactive({
    messagesReceived: 0,
    messagesSent: 0,
    reconnectCount: 0,
    connectedSince: null as Date | null
  })

  private config: WebSocketConfig = {
    reconnectInterval: 3000, // 3 segundos
    maxReconnectAttempts: 0, // 0 = ilimitado
    heartbeatInterval: 30000 // 30 segundos
  }

  constructor(config?: Partial<WebSocketConfig>) {
    if (config) {
      this.config = { ...this.config, ...config }
    }
  }

  /**
   * Conectar al WebSocket con el tipo de cliente especificado
   */
  async connect(clientType: 'kds' | 'caja' | 'mesero'): Promise<boolean> {
    const authStore = useAuthStore()

    if (!authStore.isAuthenticated || !authStore.token) {
      this.lastError.value = 'No hay token de autenticación'
      console.error('WebSocket: No hay token de autenticación')
      return false
    }

    // Guardar tipo de cliente para reconexiones
    this.clientType = clientType
    this.intentionalDisconnect = false

    // Registrar event listeners del browser (una sola vez)
    this._registerBrowserListeners()

    // Si ya está conectado, no reconectar
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log('WebSocket: Ya está conectado')
      return true
    }

    // Cerrar conexión existente si existe
    if (this.ws) {
      this.ws.onopen = null
      this.ws.onmessage = null
      this.ws.onclose = null
      this.ws.onerror = null
      if (this.ws.readyState === WebSocket.OPEN) {
        this.ws.close(1000, 'Reconectando')
      }
      this.ws = null
    }

    // El token NO va en la URL: el query string del handshake queda en texto
    // plano en los access logs del proxy. Se manda como primer frame (ver
    // handleOpen -> sendAuth).
    const wsUrl = `${import.meta.env.VITE_WS_URL || 'ws://localhost:8000'}/ws/${clientType}`
    const authToken = authStore.token

    try {
      this.connectionStatus.value = 'connecting'
      console.log(`WebSocket: Conectando a ${clientType}...`)

      this.ws = new WebSocket(wsUrl)

      // Promesa para esperar conexión
      return new Promise((resolve) => {
        const timeout = setTimeout(() => {
          this.lastError.value = 'Timeout conectando al WebSocket'
          resolve(false)
        }, 10000) // 10 segundos timeout

        this.ws!.onopen = (event) => {
          clearTimeout(timeout)
          // Primer frame obligatorio: auth. El server cierra con 4001 si no
          // llega un token válido dentro de su timeout.
          this.sendAuth(authToken)
          this.handleOpen(event)
          resolve(true)
        }

        this.ws!.onmessage = this.handleMessage.bind(this)
        this.ws!.onclose = this.handleClose.bind(this)

        this.ws!.onerror = () => {
          clearTimeout(timeout)
          resolve(false)
        }
      })

    } catch (error) {
      this.lastError.value = `Error creando WebSocket: ${error}`
      console.error('WebSocket: Error creando conexión:', error)
      this.connectionStatus.value = 'disconnected'
      return false
    }
  }

  /**
   * Forzar reconexión manual inmediata
   */
  async reconnect(): Promise<boolean> {
    if (!this.clientType) {
      console.warn('WebSocket: No se puede reconectar, tipo de cliente no especificado')
      return false
    }
    
    console.log('WebSocket: Forzando reconexión manual...')
    
    // Limpiar temporizador de reconexión si existe
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    
    // Resetear contador de intentos para que no use backoff exponencial largo en este intento
    this.reconnectAttempts = 0
    
    return await this.connect(this.clientType)
  }

  /**
   * Desconectar WebSocket (intencional, no reconecta)
   */
  disconnect(): void {
    console.log('WebSocket: Desconectando...')
    this.intentionalDisconnect = true

    // Remover event listeners del browser
    this._unregisterBrowserListeners()

    // Limpiar timers
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }

    // Cerrar conexión
    if (this.ws) {
      this.ws.onopen = null
      this.ws.onmessage = null
      this.ws.onclose = null
      this.ws.onerror = null

      if (this.ws.readyState === WebSocket.OPEN) {
        this.ws.close(1000, 'Cliente desconectando')
      }

      this.ws = null
    }

    // Resetear estado
    this.isConnected.value = false
    this.connectionStatus.value = 'disconnected'
    this.reconnectAttempts = 0
    this.stats.connectedSince = null
    this.clientType = null
  }

  /**
   * Enviar mensaje al WebSocket
   */
  send(message: WebSocketMessage): boolean {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket: No está conectado, no se puede enviar mensaje')
      return false
    }

    try {
      this.ws.send(JSON.stringify(message))
      this.stats.messagesSent++
      return true
    } catch (error) {
      console.error('WebSocket: Error enviando mensaje:', error)
      this.lastError.value = `Error enviando mensaje: ${error}`
      return false
    }
  }

  /**
   * Suscribirse a eventos específicos
   */
  on(eventType: string, callback: (data: any) => void): void {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, [])
    }
    this.listeners.get(eventType)!.push(callback)
  }

  /**
   * Desuscribirse de eventos
   */
  off(eventType: string, callback?: (data: any) => void): void {
    if (!this.listeners.has(eventType)) return

    if (!callback) {
      // Remover todos los listeners del tipo
      this.listeners.delete(eventType)
    } else {
      // Remover listener específico
      const callbacks = this.listeners.get(eventType)!
      const index = callbacks.indexOf(callback)
      if (index > -1) {
        callbacks.splice(index, 1)
      }
    }
  }

  /**
   * Enviar el frame de autenticación (primer mensaje de toda conexión)
   */
  private sendAuth(token: string): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return

    try {
      this.ws.send(JSON.stringify({ type: 'auth', token }))
      this.stats.messagesSent++
    } catch (error) {
      console.error('WebSocket: Error enviando auth:', error)
      this.lastError.value = 'Error enviando autenticación'
    }
  }

  /**
   * Enviar ping para mantener conexión viva
   */
  private sendPing(): void {
    this.send({
      type: 'ping',
      data: {},
      timestamp: new Date().toISOString()
    })
  }

  /**
   * Manejar apertura de conexión
   */
  private handleOpen(event: Event): void {
    console.log('WebSocket: Conexión establecida')
    this.isConnected.value = true
    this.connectionStatus.value = 'connected'
    this.lastError.value = null
    this.reconnectAttempts = 0
    this.stats.connectedSince = new Date()

    // Iniciar heartbeat
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
    }
    this.heartbeatTimer = window.setInterval(() => {
      this.sendPing()
    }, this.config.heartbeatInterval)

    // Notificar a los listeners para que re-sincronicen estado tras (re)conexión
    this.emit('connection_open', { clientType: this.clientType })
  }

  /**
   * Emitir evento a los listeners suscritos
   */
  private emit(eventType: string, data: any): void {
    if (!this.listeners.has(eventType)) return
    this.listeners.get(eventType)!.forEach(callback => {
      try {
        callback(data)
      } catch (error) {
        console.error(`WebSocket: Error en callback de ${eventType}:`, error)
      }
    })
  }

  /**
   * Manejar mensajes recibidos
   */
  private handleMessage(event: MessageEvent): void {
    try {
      const message: WebSocketMessage = JSON.parse(event.data)
      this.stats.messagesReceived++

      console.log('WebSocket: Mensaje recibido:', message.type, message)

      // Manejar mensajes especiales
      if (message.type === 'pong') {
        console.log('WebSocket: Pong recibido')
        return
      }

      if (message.type === 'connection_established') {
        console.log('WebSocket: Conexión confirmada por servidor')
        return
      }

      // Acuse: el server solo adjunta message_id a los eventos de pedidos
      // enviados al KDS (ver websocket_manager.py). Confirmarlo de inmediato
      // es lo que permite al server distinguir "el cliente lo recibió" de
      // "se perdió en tránsito" — sin esto, un mensaje caído era silencioso.
      if (message.message_id) {
        this.send({ type: 'ack', data: {}, message_id: message.message_id })
      }

      // Emitir evento a listeners
      this.emit(message.type, message.data)

      // Emitir evento genérico
      this.emit('*', message)

    } catch (error) {
      console.error('WebSocket: Error parseando mensaje:', error)
      this.lastError.value = `Error parseando mensaje: ${error}`
    }
  }

  /**
   * Manejar cierre de conexión
   */
  private handleClose(event: CloseEvent): void {
    console.log('WebSocket: Conexión cerrada', event.code, event.reason)
    this.isConnected.value = false
    this.stats.connectedSince = null

    // Limpiar heartbeat
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }

    // Reconectar en cualquier cierre no-intencional
    if (!this.intentionalDisconnect) {
      this.attemptReconnect()
    } else {
      this.connectionStatus.value = 'disconnected'
    }
  }

  /**
   * Manejar errores
   */
  private handleError(event: Event): void {
    console.error('WebSocket: Error de conexión:', event)
    this.lastError.value = 'Error de conexión WebSocket'
    // handleClose se llama automáticamente después de onerror
  }

  /**
   * Intentar reconexión automática con backoff exponencial
   */
  private attemptReconnect(): void {
    if (this.intentionalDisconnect) return

    if (this.config.maxReconnectAttempts > 0 && this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      console.error('WebSocket: Máximo de intentos de reconexión alcanzado')
      this.connectionStatus.value = 'disconnected'
      this.lastError.value = 'No se pudo reconectar al WebSocket'
      return
    }

    this.reconnectAttempts++
    this.stats.reconnectCount++
    this.connectionStatus.value = 'reconnecting'

    const delay = Math.min(
      this.config.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1),
      30000 // Máximo 30 segundos
    )

    console.log(`WebSocket: Reintentando conexión en ${delay}ms (intento ${this.reconnectAttempts})`)

    this.reconnectTimer = window.setTimeout(async () => {
      if (!this.intentionalDisconnect && this.clientType) {
        console.log('WebSocket: Reintentando conexión...')
        await this.connect(this.clientType)
      }
    }, delay)
  }

  /**
   * Reconectar cuando el tab vuelve a estar activo
   */
  private handleVisibilityChange(): void {
    if (document.visibilityState === 'visible' && !this.intentionalDisconnect && this.clientType) {
      if (!this.isConnected.value || this.ws?.readyState !== WebSocket.OPEN) {
        console.log('WebSocket: Tab activo de nuevo, reconectando...')
        if (this.reconnectTimer) {
          clearTimeout(this.reconnectTimer)
          this.reconnectTimer = null
        }
        this.connectionStatus.value = 'reconnecting'
        this.connect(this.clientType)
      } else {
        // Conexión viva: enviar ping inmediato para renovar last_ping en el server
        this.sendPing()
      }
    }
  }

  /**
   * Reconectar cuando se restaura la red
   */
  private handleOnline(): void {
    if (!this.intentionalDisconnect && this.clientType && !this.isConnected.value) {
      console.log('WebSocket: Red restaurada, reconectando...')
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer)
        this.reconnectTimer = null
      }
      this.connectionStatus.value = 'reconnecting'
      this.connect(this.clientType)
    }
  }

  private _registerBrowserListeners(): void {
    // Solo registrar si no están ya registrados
    if (!this.visibilityHandler) {
      this.visibilityHandler = this.handleVisibilityChange.bind(this)
      document.addEventListener('visibilitychange', this.visibilityHandler)
    }
    if (!this.onlineHandler) {
      this.onlineHandler = this.handleOnline.bind(this)
      window.addEventListener('online', this.onlineHandler)
    }
  }

  private _unregisterBrowserListeners(): void {
    if (this.visibilityHandler) {
      document.removeEventListener('visibilitychange', this.visibilityHandler)
      this.visibilityHandler = null
    }
    if (this.onlineHandler) {
      window.removeEventListener('online', this.onlineHandler)
      this.onlineHandler = null
    }
  }

  /**
   * Obtener estadísticas de la conexión
   */
  getStats() {
    return {
      ...this.stats,
      isConnected: this.isConnected.value,
      connectionStatus: this.connectionStatus.value,
      lastError: this.lastError.value,
      reconnectAttempts: this.reconnectAttempts
    }
  }
}

// Instancia singleton del servicio
export const websocketService = new WebSocketService()
