import { ref } from 'vue'

/**
 * Modal de PIN de administrador reusable para acciones sensibles (borrar
 * artículo, cancelar cuenta, editar propina, ver analíticas del turno).
 *
 * No hay cajero fijo: cualquier mesero de confianza usa la sesión de caja,
 * así que estas acciones se autorizan con el PIN de un administrador activo
 * en el momento, no con el rol de la sesión. La verificación real ocurre en
 * el backend (misma llamada que ejecuta la acción); este composable solo
 * junta el PIN y deja reintentar si el backend lo rechaza.
 */
export function useAdminPin(titulo: string, mensaje?: string) {
  const isOpen = ref(false)
  const error = ref<string | null>(null)

  let resolvePin: ((pin: string) => void) | null = null
  let rejectPin: (() => void) | null = null

  function requestPin(): Promise<string> {
    // No se limpia `error` aquí a propósito: un reintento tras PIN inválido
    // vuelve a llamar requestPin() y el mensaje debe seguir visible al
    // reabrir el modal. Se limpia al cerrar (onConfirm/onCancel) en su lugar.
    isOpen.value = true
    return new Promise<string>((resolve, reject) => {
      resolvePin = resolve
      rejectPin = reject
    })
  }

  function onConfirm(pin: string) {
    isOpen.value = false
    error.value = null
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
   * (401/400), reabre el modal con el mensaje de error y vuelve a pedirlo.
   * Se cancela (rechaza la promesa) si el usuario cierra el modal.
   */
  async function requestPinVerificado<T>(verificar: (pin: string) => Promise<T>): Promise<T> {
    for (;;) {
      const pin = await requestPin()
      try {
        return await verificar(pin)
      } catch (e: any) {
        const status = e?.response?.status
        if (status === 401 || status === 400) {
          error.value = e?.response?.data?.detail || 'PIN inválido'
          continue
        }
        throw e
      }
    }
  }

  return { isOpen, error, titulo, mensaje, requestPin, requestPinVerificado, onConfirm, onCancel }
}
