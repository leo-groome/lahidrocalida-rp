import { isAxiosError } from 'axios'
import { mensajeErrorGasto } from '@/utils/gasto-error'
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { api } from '@/api/client'
import { useAuthStore } from './auth'
import { prepararPayloadGasto, type GastoPayload } from '@/utils/gasto-payload'
import { leerPendientes, guardarPendiente, borrarPendiente, type GastoPendiente } from '@/utils/gasto-queue-db'

export const useGastosPendientesStore = defineStore('gastos-pendientes', () => {
  const auth = useAuthStore()
  const operaciones = ref<GastoPendiente[]>([])
  const escribiendo = ref(false)
  const activos = new Set<string>()
  const pendientes = computed(() => operaciones.value.filter(p =>
    p.usuarioId === auth.user?.id && p.sucursalId === auth.user?.sucursal_id))
  function verificar(p: GastoPendiente) {
    if (!auth.isAuthenticated || p.usuarioId !== auth.user?.id || p.sucursalId !== auth.user?.sucursal_id)
      throw new Error('Inicia sesión con el usuario que registró este gasto')
  }
  async function cargar() {
    const recovered = await leerPendientes()
    // No sustituir objetos en vuelo al remontar la vista.
    for (const p of recovered) {
      if (operaciones.value.some(o => o.id === p.id)) continue
      if (p.estado === 'enviando') p.estado = p.gastoId ? 'parcial' : 'pendiente'
      operaciones.value.push(p)
    }
  }
  async function agregar(input: GastoPayload, fotos: File[], total: number, resumen: string) {
    if (escribiendo.value) throw new Error('Espera a que termine de guardar la captura')
    const user = auth.user
    if (!user || !auth.isAuthenticated) throw new Error('Inicia sesión para registrar el gasto')
    const payload = prepararPayloadGasto(input)
    const p: GastoPendiente = { id: payload.client_request_id!, usuarioId: user.id,
      sucursalId: user.sucursal_id, total, resumen, estado: 'pendiente', error: '',
      fotosFallidas: 0, payload, fotos: fotos.map(file => ({ id: crypto.randomUUID(), file })) }
    escribiendo.value = true
    try {
      await guardarPendiente(p)
      operaciones.value.unshift(p)
      return operaciones.value[0]!
    } finally { escribiendo.value = false }
  }
  async function descartar(id: string) {
    const p = pendientes.value.find(o => o.id === id)
    if (!p || activos.has(id)) return
    await borrarPendiente(id)
    operaciones.value = operaciones.value.filter(o => o.id !== id)
  }
  async function ejecutar(p: GastoPendiente) {
    verificar(p)
    // Recuperar progreso escrito por otra pestaña después de adquirir su lock.
    const saved = (await leerPendientes()).find(o => o.id === p.id)
    if (!saved) return
    Object.assign(p, saved)
    if (p.estado === 'ok') return
    p.estado = 'enviando'; p.error = ''
    try {
      await guardarPendiente(p)
      if (!p.gastoId) {
        verificar(p)
        const { data } = await api.post('/gastos/', p.payload)
        p.gastoId = data.id
        await guardarPendiente(p)
      }
      for (const foto of [...p.fotos]) {
        verificar(p)
        const form = new FormData()
        form.append('archivo', foto.file, foto.file.name)
        await api.post(`/gastos/${p.gastoId}/adjuntos`, form, {
          params: { client_request_id: foto.id }, timeout: 60_000,
        })
        p.fotos = p.fotos.filter(f => f.id !== foto.id)
        await guardarPendiente(p)
      }
      p.estado = 'ok'; p.fotosFallidas = 0
      await guardarPendiente(p)
    } catch (e: unknown) {
      p.rechazado = !p.gastoId && isAxiosError(e) && [400, 422].includes(e.response?.status ?? 0)
      p.estado = p.gastoId ? 'parcial' : 'error'
      p.fotosFallidas = p.fotos.length
      p.error = mensajeErrorGasto(e)
      try { await guardarPendiente(p) } catch { p.error += ' · No se pudo conservar el progreso local' }
    }
  }
  async function enviar(p: GastoPendiente) {
    if (activos.has(p.id)) return
    activos.add(p.id)
    try {
      if (navigator.locks) await navigator.locks.request(`gasto:${p.id}`, () => ejecutar(p))
      else await ejecutar(p) // La BD del servidor conserva idempotencia entre pestañas.
    } finally { activos.delete(p.id) }
  }
  return { pendientes, escribiendo, cargar, agregar, enviar, descartar }
})
