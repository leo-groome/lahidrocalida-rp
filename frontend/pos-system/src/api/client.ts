import axios from 'axios'

const baseURL = import.meta.env.VITE_API_URL || 'http://172.24.13.255:8000'

const api = axios.create({
  baseURL,
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
