import axios from 'axios'
import { isTokenExpired } from '../utils/jwt'

const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL,
  timeout: 15000, // Sin timeout un POST puede colgar el spinner indefinidamente con red mala
})

export { api }
export default api

api.interceptors.request.use(async (config) => {
  const token = localStorage.getItem('token')
  if (token) {
    // El temporizador puede retrasarse mientras una PWA está suspendida. Esta
    // segunda barrera evita mandar un request con un JWT ya vencido.
    if (isTokenExpired(token)) {
      const { useAuthStore } = await import('../stores/auth')
      useAuthStore().expireSession()
      return Promise.reject(new axios.CanceledError('Sesión expirada'))
    }
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Solo estos endpoints usan 401 para indicar credenciales de una acción
// concreta, no que la sesión actual haya expirado. No incluir prefijos como
// `/pedidos`: sus operaciones protegidas deben cerrar la sesión ante un 401.
const RUTAS_401_SIN_LOGOUT = new Set([
  '/auth/login',
  '/auth/login-simple',
  '/auth/login-admin',
  '/auth/asistencia',
  '/auth/verify-admin-pin',
])

function isCredentialEndpoint(url: string): boolean {
  return RUTAS_401_SIN_LOGOUT.has(url.split('?')[0])
}

// Import dinámico (no estático) de la store de auth y el router: ambos
// importan `api` de este módulo, así que un `import` estático aquí crearía
// un ciclo. El dinámico se resuelve en tiempo de llamada, no de carga.
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      const url: string = error.config?.url ?? ''
      if (!isCredentialEndpoint(url)) {
        const { useAuthStore } = await import('../stores/auth')
        useAuthStore().expireSession()
      }
    }
    return Promise.reject(error)
  }
)
