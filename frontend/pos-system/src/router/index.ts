import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const Login = () => import('../views/Login.vue')
const AdminLogin = () => import('../views/AdminLogin.vue')
const ClockInView = () => import('../views/ClockInView.vue')
const MeseroView = () => import('../views/MeseroView.vue')
const CajaView = () => import('../views/CajaView.vue')
const KDSView = () => import('../views/KDSView.vue')
const KDSManager = () => import('../views/KDSManager.vue')
const AdminView = () => import('../views/AdminView.vue')

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/login' },
  { path: '/login', name: 'login', component: Login, meta: { public: true } },
  { path: '/mesero', name: 'mesero', component: MeseroView, meta: { requiresAuth: true, roles: ['mesero', 'administrador'] } },
  { path: '/caja', name: 'caja', component: CajaView, meta: { requiresAuth: true, roles: ['cajero', 'administrador'] } },
  { path: '/kds-view', name: 'kds-view', component: KDSView, meta: { public: true } },
  { path: '/kds-manager', name: 'kds-manager', component: KDSManager, meta: { requiresAuth: true, roles: ['cocina', 'administrador'] } },
  { path: '/admin', name: 'admin', component: AdminView, meta: { requiresAuth: true, roles: ['administrador'] } },
  { path: '/kds', name: 'kds', component: KDSView, meta: { public: true } },
  { path: '/admin-login', name: 'admin-login', component: AdminLogin, meta: { public: true } },
  { path: '/checkin', name: 'checkin', component: ClockInView, meta: { public: true } },
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
      switch (auth.role as any) {
        case 'cajero':
          return { name: 'caja' }
        case 'mesero':
          return { name: 'mesero' }
        case 'cocina':
          return { name: 'kds-manager' }
        case 'administrador':
          return { name: 'admin' }
        default:
          return { name: 'login' }
      }
    }
  }
  return true
})
