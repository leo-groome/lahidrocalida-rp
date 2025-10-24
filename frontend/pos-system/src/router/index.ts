import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const Login = () => import('../views/Login.vue')
const POS = () => import('../views/POS.vue')

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/login' },
  { path: '/login', name: 'login', component: Login, meta: { public: true } },
  { path: '/pos', name: 'pos', component: POS, meta: { requiresAuth: true, roles: ['cajero', 'administrador'] } },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.user && auth.token) {
    await auth.fetchMe()
  }
  if (to.meta.public) return true
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.meta.roles && auth.role && Array.isArray(to.meta.roles)) {
    if (!(to.meta.roles as string[]).includes(auth.role)) {
      // fallback por rol
      switch (auth.role) {
        case 'cajero':
          return { name: 'pos' }
        default:
          return { name: 'login' }
      }
    }
  }
  return true
})
