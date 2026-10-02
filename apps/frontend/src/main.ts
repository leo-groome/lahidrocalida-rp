import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import { createPinia } from 'pinia'
import { router } from './router'
import { useAuthStore } from './stores/auth'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
// El JWT se valida localmente antes de que el guard consulte /auth/me y se
// programa su cierre exacto para no dejar al operador con una sesión vencida.
const auth = useAuthStore(pinia)
auth.initializeSession()
// Al despertar de suspensión los timers pueden haberse pausado; validar antes
// de que el operador vuelva a capturar o enviar una orden.
const validateSessionOnWake = () => auth.initializeSession()
window.addEventListener('focus', validateSessionOnWake)
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') validateSessionOnWake()
})
app.use(router)
app.mount('#app')
