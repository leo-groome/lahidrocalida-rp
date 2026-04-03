import { defineStore } from 'pinia'
import { api } from '../api/client'

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
    token: localStorage.getItem('token'),
    user: null,
    loading: false,
    error: null,
  }),
  getters: {
    isAuthenticated: (state) => !!state.token,
    role: (state): Rol | null => state.user?.rol ?? null,
  },
  actions: {
    async login(user_id: string, password: string) {
      this.loading = true
      this.error = null
      try {
        const { data } = await api.post('/auth/login-simple', { user_id, password })
        const token: string = data.access_token
        this.token = token
        localStorage.setItem('token', token)
        await this.fetchMe()
      } catch (e: any) {
        this.error = e?.response?.data?.detail || 'Error de autenticación'
        this.token = null
        localStorage.removeItem('token')
        throw e
      } finally {
        this.loading = false
      }
    },
    async fetchMe() {
      if (!this.token) return
      try {
        const { data } = await api.get('/auth/me')
        this.user = data as Usuario
      } catch (e) {
        this.logout()
      }
    },
    logout() {
      this.token = null
      this.user = null
      localStorage.removeItem('token')
    },
  },
})
