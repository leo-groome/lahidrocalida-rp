import axios from 'axios'

const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL,
  timeout: 15000, // Sin timeout un POST puede colgar el spinner indefinidamente con red mala
})

export { api }
export default api

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Endpoints donde un 401 significa "credencial incorrecta" (login, clock-in
// por NIP), no "sesión expirada" — ahí NO hay que cerrar sesión ni redirigir,
// el propio formulario ya maneja el error.
const RUTAS_401_SIN_LOGOUT = ['/auth/login', '/auth/asistencia']

// Import dinámico (no estático) de la store de auth y el router: ambos
// importan `api` de este módulo, así que un `import` estático aquí crearía
// un ciclo. El dinámico se resuelve en tiempo de llamada, no de carga.
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      const url: string = error.config?.url ?? ''
      const esRutaDeCredenciales = RUTAS_401_SIN_LOGOUT.some((ruta) => url.includes(ruta))
      if (!esRutaDeCredenciales) {
        const [{ useAuthStore }, { router }] = await Promise.all([
          import('../stores/auth'),
          import('../router'),
        ])
        useAuthStore().logout()
        if (router.currentRoute.value.name !== 'login') {
          router.push({ name: 'login', query: { redirect: router.currentRoute.value.fullPath } })
        }
      }
    }
    return Promise.reject(error)
  }
)
