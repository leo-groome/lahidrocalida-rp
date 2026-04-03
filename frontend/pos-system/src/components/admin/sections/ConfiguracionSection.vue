<template>
  <div class="space-y-8 animate-in fade-in duration-500 pb-12">
    <!-- Header -->
    <div class="bg-white p-8 rounded-3xl shadow-sm border border-slate-100">
      <div class="flex items-center space-x-4 mb-2">
        <div class="p-3 bg-blue-50 rounded-2xl text-blue-600">
          <Settings class="h-6 w-6" />
        </div>
        <div>
          <h2 class="text-2xl font-extrabold text-slate-900 tracking-tight">Configuración del Sistema</h2>
          <p class="text-sm font-medium text-slate-500">Ajusta los parámetros globales de tu operación.</p>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
      <!-- Printer Configuration -->
      <div class="bg-white rounded-3xl shadow-sm border border-slate-100 overflow-hidden flex flex-col">
        <div class="p-8 border-b border-slate-50">
          <div class="flex items-center justify-between mb-6">
            <h3 class="text-lg font-bold text-slate-800 flex items-center">
              <Printer class="h-5 w-5 mr-3 text-slate-400" />
              Servicio de Impresión
            </h3>
            <div 
              class="px-4 py-1.5 rounded-full text-[10px] font-black uppercase tracking-widest flex items-center shadow-sm"
              :class="printServiceStatus === 'online' ? 'bg-emerald-50 text-emerald-600 border border-emerald-100' : 'bg-red-50 text-red-600 border border-red-100'"
            >
              <div class="h-1.5 w-1.5 rounded-full mr-2" :class="printServiceStatus === 'online' ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'"></div>
              {{ printServiceStatus }}
            </div>
          </div>

          <p class="text-sm text-slate-500 mb-8 font-medium">Configura el host y puerto de tu servidor de impresión local para tickets automáticos.</p>

          <form @submit.prevent="savePrintConfig" class="space-y-6">
            <div class="grid grid-cols-2 gap-6">
              <div class="space-y-2">
                <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Host del Servidor</label>
                <div class="relative group">
                  <Globe class="absolute left-4 top-3.5 h-4 w-4 text-slate-400 group-hover:text-blue-500 transition-colors" />
                  <input 
                    v-model="printConfig.host" 
                    type="text" 
                    class="w-full pl-12 pr-4 py-3 bg-slate-50 border-none rounded-2xl text-sm font-bold text-slate-700 focus:ring-2 focus:ring-blue-500/20 transition-all"
                  />
                </div>
              </div>
              <div class="space-y-2">
                <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Puerto</label>
                <div class="relative group">
                  <Hash class="absolute left-4 top-3.5 h-4 w-4 text-slate-400 group-hover:text-blue-500 transition-colors" />
                  <input 
                    v-model.number="printConfig.port" 
                    type="number" 
                    class="w-full pl-12 pr-4 py-3 bg-slate-50 border-none rounded-2xl text-sm font-bold text-slate-700 focus:ring-2 focus:ring-blue-500/20 transition-all"
                  />
                </div>
              </div>
            </div>

            <div class="flex items-center p-4 bg-slate-50/50 rounded-2xl border border-slate-100 group cursor-pointer" @click="printConfig.autoprint = !printConfig.autoprint">
              <div class="h-10 w-10 bg-white rounded-xl flex items-center justify-center shadow-sm mr-4 group-hover:scale-110 transition-transform">
                <Zap class="h-5 w-5" :class="printConfig.autoprint ? 'text-blue-500' : 'text-slate-300'" />
              </div>
              <div class="flex-1">
                <p class="text-sm font-extrabold text-slate-700">Auto-impresión</p>
                <p class="text-xs font-medium text-slate-400">Imprimir tickets al solicitar cuenta</p>
              </div>
              <div class="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" v-model="printConfig.autoprint" class="sr-only peer">
                <div class="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              </div>
            </div>

            <div class="flex gap-3 pt-2">
              <button 
                type="button"
                @click="testPrintService"
                class="flex-1 px-6 py-3 bg-slate-100 text-slate-600 rounded-2xl text-xs font-black uppercase tracking-widest hover:bg-slate-200 transition-all"
              >
                Probar Conexión
              </button>
              <button 
                type="submit"
                class="flex-1 px-6 py-3 bg-blue-600 text-white rounded-2xl text-xs font-black uppercase tracking-widest shadow-lg shadow-blue-200 hover:bg-blue-700 hover:scale-[1.02] active:scale-[0.98] transition-all"
              >
                Guardar Cambios
              </button>
            </div>
          </form>
        </div>
      </div>

      <!-- General Operations -->
      <div class="bg-white rounded-3xl shadow-sm border border-slate-100 overflow-hidden flex flex-col">
        <div class="p-8 border-b border-slate-50 flex-1">
          <h3 class="text-lg font-bold text-slate-800 flex items-center mb-6">
            <Clock class="h-5 w-5 mr-3 text-slate-400" />
            Horarios de Operación
          </h3>

          <p class="text-sm text-slate-500 mb-8 font-medium">Define los horarios en los que el sistema permitirá la apertura de comandas.</p>

          <form @submit.prevent="saveGeneralConfig" class="space-y-8">
            <div class="grid grid-cols-2 gap-8">
              <div class="space-y-3">
                <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Apertura</label>
                <input 
                  v-model="generalConfig.horario_apertura" 
                  type="time" 
                  class="w-full px-6 py-4 bg-slate-50 border-none rounded-3xl text-sm font-black text-slate-700 focus:ring-2 focus:ring-blue-500/20 transition-all text-center"
                />
              </div>
              <div class="space-y-3">
                <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Cierre Estupulado</label>
                <input 
                  v-model="generalConfig.horario_cierre" 
                  type="time" 
                  class="w-full px-6 py-4 bg-slate-50 border-none rounded-3xl text-sm font-black text-slate-700 focus:ring-2 focus:ring-blue-500/20 transition-all text-center"
                />
              </div>
            </div>

            <div class="p-8 bg-blue-50/30 rounded-3xl border border-blue-100/50">
              <div class="flex items-start">
                <div class="p-2 bg-blue-100 rounded-xl text-blue-600 mr-4">
                  <Info class="h-5 w-5" />
                </div>
                <div>
                  <h4 class="text-sm font-black text-blue-900 mb-1 leading-tight tracking-tight">Nota de Seguridad</h4>
                  <p class="text-xs font-medium text-blue-700/80 leading-relaxed">
                    Estos horarios restringen la creación de pedidos fuera del turno. Asegúrate de sincronizar estos valores con los turnos de tus cajeros.
                  </p>
                </div>
              </div>
            </div>

            <button 
              type="submit"
              class="w-full px-6 py-4 bg-slate-900 text-white rounded-2xl text-xs font-black uppercase tracking-widest shadow-xl shadow-slate-200 hover:bg-black hover:scale-[1.01] active:scale-[0.99] transition-all"
            >
              Actualizar Operación
            </button>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api/client'
import { 
  Settings, Printer, Clock, Zap, Globe, Hash, Info
} from 'lucide-vue-next'

const printServiceStatus = ref('offline')
const printConfig = ref({
  host: 'localhost',
  port: 3001,
  autoprint: true
})

const generalConfig = ref({
  horario_apertura: '10:00',
  horario_cierre: '22:00'
})

const loadConfig = async () => {
  try {
    const res = await api.get('/config/print')
    if (res.data) printConfig.value = res.data
    
    const resGen = await api.get('/config/general')
    if (resGen.data) generalConfig.value = resGen.data
    
    testPrintService()
  } catch (error) {
    console.error('Error loading config:', error)
  }
}

const testPrintService = async () => {
  try {
    const res = await fetch(`http://${printConfig.value.host}:${printConfig.value.port}/health`)
    if (res.ok) printServiceStatus.value = 'online'
    else printServiceStatus.value = 'offline'
  } catch {
    printServiceStatus.value = 'offline'
  }
}

const savePrintConfig = async () => {
  await api.post('/config/print', printConfig.value)
  alert('Configuración de impresión guardada')
  testPrintService()
}

const saveGeneralConfig = async () => {
  await api.post('/config/general', generalConfig.value)
  alert('Configuración general guardada')
}

onMounted(loadConfig)
</script>
