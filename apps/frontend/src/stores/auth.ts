import { defineStore } from 'pinia'
import { api } from '../api/client'
import { getSessionExpiration, isTokenExpired } from '../utils/jwt'

const storedToken = localStorage.getItem('token')
const initialToken = storedToken && !isTokenExpired(storedToken) ? storedToken : null
if (storedToken && !initialToken) {
  localStorage.removeItem('token')
}

let expirationTimer: ReturnType<typeof window.setTimeout> | null = null

function redirectToLogin(): void {
  void import('../router').then(({ router }) => {
    const currentRoute = router.currentRoute.value
    if (!currentRoute.meta.public) {
      router.replace({ name: 'login', query: { redirect: currentRoute.fullPath } })
    }
  })
}

export type Rol = 'mesero' | 'cajero' | 'cocina' | 'administrador' | 'compras'

export interface Usuario {
  id: number
  nombre: string
  rol: Rol
  activo: boolean
  sucursal_id: number
}

interface State {
  token: string | null
  user: Usuario | null
  loading: boolean
  error: string | null
}

export const useAuthStore = defineStore('auth', {
  state: (): State => ({
    token: initialToken,
    user: null,
    loading: false,
    error: null,
  }),
  getters: {
    isAuthenticated: (state) => !!state.token,
    role: (state): Rol | null => state.user?.rol ?? null,
  },
  actions: {
    async login(user_id: string, pin: string) {
      this.loading = true
      this.error = null
      try {
        const { data } = await api.post('/auth/login-simple', { user_id, pin })
        this.setToken(data.access_token as string)
        await this.fetchMe()
      } catch (e: any) {
        const detail = e?.response?.data?.detail
        this.error = Array.isArray(detail) ? 'Error de validación' : (detail || 'Error de autenticación')
        this.logout()
        throw e
      } finally {
        this.loading = false
      }
    },
    async loginAdmin(email: string, password: string) {
      this.loading = true
      this.error = null
      try {
        const { data } = await api.post('/auth/login-admin', { email, password })
        this.setToken(data.access_token as string)
        await this.fetchMe()
      } catch (e: any) {
        this.error = e?.response?.data?.detail || 'Credenciales incorrectas'
        this.logout()
        throw e
      } finally {
        this.loading = false
      }
    },
    initializeSession() {
      if (!this.token) return
      if (isTokenExpired(this.token)) {
        this.expireSession()
        return
      }
      this.scheduleExpiration()
    },
    setToken(token: string) {
      this.token = token
      localStorage.setItem('token', token)
      this.scheduleExpiration()
    },
    scheduleExpiration() {
      if (expirationTimer) {
        clearTimeout(expirationTimer)
        expirationTimer = null
      }
      if (!this.token) return

      const expiration = getSessionExpiration(this.token)
      if (expiration === null || expiration <= Date.now()) {
        this.expireSession()
        return
      }
      expirationTimer = window.setTimeout(() => this.expireSession(), expiration - Date.now())
    },
    expireSession() {
      this.logout()
      redirectToLogin()
    },
    async fetchMe() {
      if (!this.token) return
      if (isTokenExpired(this.token)) {
        this.expireSession()
        return
      }
      try {
        const { data } = await api.get('/auth/me')
        this.user = data as Usuario
      } catch (e) {
        this.logout()
      }
    },
    logout() {
      if (expirationTimer) {
        clearTimeout(expirationTimer)
        expirationTimer = null
      }
      this.token = null
      this.user = null
      localStorage.removeItem('token')
    },
  },
})
