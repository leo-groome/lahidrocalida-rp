import { ref } from 'vue'

/**
 * Modal de PIN de administrador reusable para acciones sensibles (borrar
 * artículo, cancelar cuenta, editar propina, ver analíticas del turno).
 */
export function useAdminPin(titulo: string, mensaje?: string) {
  const isOpen = ref(false)
  const error = ref<string | null>(null)
  const failedAttempts = ref(0)
  const cooldownSeconds = ref(0)
  let cooldownTimer: number | null = null

  let resolvePin: ((pin: string) => void) | null = null
  let rejectPin: (() => void) | null = null

  function startCooldown(seconds = 30) {
    cooldownSeconds.value = seconds
    if (cooldownTimer) clearInterval(cooldownTimer)
    cooldownTimer = window.setInterval(() => {
      if (cooldownSeconds.value > 1) {
        cooldownSeconds.value -= 1
        error.value = `⚠️ Demasiados intentos fallidos (3/3). Intenta de nuevo en ${cooldownSeconds.value}s`
      } else {
        cooldownSeconds.value = 0
        failedAttempts.value = 0
        error.value = null
        if (cooldownTimer) clearInterval(cooldownTimer)
        cooldownTimer = null
      }
    }, 1000)
  }

  function requestPin(): Promise<string> {
    isOpen.value = true
    return new Promise<string>((resolve, reject) => {
      resolvePin = resolve
      rejectPin = reject
    })
  }

  function onConfirm(pin: string) {
    if (cooldownSeconds.value > 0) return
    isOpen.value = false
    resolvePin?.(pin)
    resolvePin = null
    rejectPin = null
  }

  function onCancel() {
    isOpen.value = false
    error.value = null
    rejectPin?.()
    resolvePin = null
    rejectPin = null
  }

  /**
   * Pide el PIN y lo verifica contra `verificar`; si el backend lo rechaza
   * (401/400/403), reabre el modal mostrando el conteo de intentos y activando
   * pausa de 30s tras 3 fallos consecutivos en lugar de cerrar sesión.
   */
  async function requestPinVerificado<T>(verificar: (pin: string) => Promise<T>): Promise<T> {
    for (;;) {
      const pin = await requestPin()
      try {
        const result = await verificar(pin)
        // Reset de intentos exitosos
        failedAttempts.value = 0
        error.value = null
        if (cooldownTimer) clearInterval(cooldownTimer)
        cooldownTimer = null
        cooldownSeconds.value = 0
        return result
      } catch (e: any) {
        const status = e?.response?.status
        if (status === 401 || status === 400 || status === 403) {
          failedAttempts.value += 1
          const msg = e?.response?.data?.detail || 'PIN de administrador incorrecto'
          if (failedAttempts.value >= 3) {
            startCooldown(30)
          } else {
            error.value = `${msg} (Intento ${failedAttempts.value} de 3)`
          }
          continue
        }
        throw e
      }
    }
  }

  return {
    isOpen,
    error,
    titulo,
    mensaje,
    failedAttempts,
    cooldownSeconds,
    requestPin,
    requestPinVerificado,
    onConfirm,
    onCancel
  }
}
