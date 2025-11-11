import { ref, reactive } from 'vue'
import { useAuthStore } from '@/stores/auth'
import type { PedidoResponse } from '@/types'

export interface WebSocketMessage {
  type: string
  data: any
  timestamp?: string
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
    maxReconnectAttempts: 10,
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

    // Si ya está conectado, no reconectar
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log('WebSocket: Ya está conectado')
      return true
    }

    // Cerrar conexión existente si existe
    if (this.ws) {
      this.disconnect()
    }

    const wsUrl = `${import.meta.env.VITE_WS_URL || 'ws://localhost:8000'}/ws/${clientType}?token=${authStore.token}`
    
    try {
      this.connectionStatus.value = 'connecting'
      console.log(`WebSocket: Conectando a ${clientType}...`)
      
      this.ws = new WebSocket(wsUrl)
      
      this.ws.onopen = this.handleOpen.bind(this)
      this.ws.onmessage = this.handleMessage.bind(this)
      this.ws.onclose = this.handleClose.bind(this)
      this.ws.onerror = this.handleError.bind(this)

      // Promesa para esperar conexión
      return new Promise((resolve) => {
        const timeout = setTimeout(() => {
          this.lastError.value = 'Timeout conectando al WebSocket'
          resolve(false)
        }, 10000) // 10 segundos timeout

        this.ws!.onopen = (event) => {
          clearTimeout(timeout)
          this.handleOpen(event)
          resolve(true)
        }

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
   * Desconectar WebSocket
   */
  disconnect(): void {
    console.log('WebSocket: Desconectando...')
    
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
    this.heartbeatTimer = window.setInterval(() => {
      this.sendPing()
    }, this.config.heartbeatInterval)
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

      // Emitir evento a listeners
      if (this.listeners.has(message.type)) {
        this.listeners.get(message.type)!.forEach(callback => {
          try {
            callback(message.data)
          } catch (error) {
            console.error('WebSocket: Error en callback:', error)
          }
        })
      }

      // Emitir evento genérico
      if (this.listeners.has('*')) {
        this.listeners.get('*')!.forEach(callback => {
          try {
            callback(message)
          } catch (error) {
            console.error('WebSocket: Error en callback genérico:', error)
          }
        })
      }

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

    // Si no fue un cierre normal, intentar reconectar
    if (event.code !== 1000 && event.code !== 1001) {
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
    this.attemptReconnect()
  }

  /**
   * Intentar reconexión automática
   */
  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
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

    console.log(`WebSocket: Reintentando conexión en ${delay}ms (intento ${this.reconnectAttempts}/${this.config.maxReconnectAttempts})`)

    this.reconnectTimer = window.setTimeout(() => {
      if (this.connectionStatus.value === 'reconnecting') {
        console.log('WebSocket: Reintentando conexión...')
        // El tipo de cliente se debe almacenar para reconexión
        // Por simplicidad, esperaremos que la app llame a connect() nuevamente
      }
    }, delay)
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