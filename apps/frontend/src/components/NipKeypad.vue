<template>
  <div class="fixed inset-0 z-[150] flex items-center justify-center bg-black/60 backdrop-blur-sm">
    <div class="bg-white rounded-2xl p-8 w-full max-w-sm mx-4 shadow-2xl">
      <!-- Header -->
      <div class="text-center mb-6 flex flex-col items-center">
        <div v-if="userName" class="text-xl font-black text-[#00126D] mb-2">{{ userName }}</div>
        
        <!-- Status indicator badge -->
        <div v-if="tieneTurnoActivo !== undefined" class="inline-flex items-center justify-center mb-4">
          <span 
            v-if="tieneTurnoActivo === true" 
            class="px-3.5 py-1 rounded-full text-xs font-black bg-rose-100 text-rose-600 border border-rose-200 animate-pulse shadow-sm"
          >
            🔴 CERRAR TURNO / SALIDA
          </span>
          <span 
            v-else-if="tieneTurnoActivo === false" 
            class="px-3.5 py-1 rounded-full text-xs font-black bg-emerald-100 text-emerald-600 border border-emerald-200 shadow-sm"
          >
            🟢 INICIAR TURNO / ENTRADA
          </span>
          <span 
            v-else 
            class="px-3.5 py-1 rounded-full text-xs font-black bg-slate-100 text-slate-400 border border-slate-200 animate-pulse shadow-sm"
          >
            Cargando estado...
          </span>
        </div>

        <p class="text-sm text-slate-500 font-semibold tracking-wide">
          <template v-if="tieneTurnoActivo === true">
            Ingresa tu NIP para registrar tu salida
          </template>
          <template v-else-if="tieneTurnoActivo === false">
            Ingresa tu NIP para registrar tu entrada
          </template>
          <template v-else>
            Ingresa tu NIP
          </template>
        </p>
      </div>

      <!-- PIN dots -->
      <div class="flex gap-4 justify-center mb-6">
        <div
          v-for="i in (maxDigits ?? 4)"
          :key="i"
          class="w-4 h-4 rounded-full border-2 transition-all duration-150"
          :class="digits.length >= i
            ? (tieneTurnoActivo === true 
                ? 'bg-rose-500 border-rose-500 scale-110 shadow-lg shadow-rose-200' 
                : 'bg-emerald-500 border-emerald-500 scale-110 shadow-lg shadow-emerald-200')
            : 'bg-transparent border-slate-300'"
        />
      </div>

      <!-- Error -->
      <p v-if="error" class="text-center text-sm text-red-500 font-medium mb-4 -mt-2">
        {{ error }}
      </p>

      <!-- Keypad grid -->
      <div class="grid grid-cols-3 gap-3">
        <button
          v-for="key in keys"
          :key="key.label"
          :disabled="loading"
          @click="handleKey(key.action)"
          class="flex items-center justify-center min-h-[64px] rounded-2xl text-2xl font-black transition-all duration-100 select-none disabled:opacity-40"
          :class="key.variant === 'cancel'
            ? 'bg-red-50 text-red-400 active:bg-red-100'
            : key.variant === 'back'
              ? 'bg-slate-100 text-slate-600 active:bg-slate-200'
              : 'bg-slate-50 text-[#00126D] active:bg-slate-200 active:scale-95'"
        >
          <span v-if="key.label !== 'back'">{{ key.label }}</span>
          <svg v-else xmlns="http://www.w3.org/2000/svg" class="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 12H3M3 12l4-4M3 12l4 4"/>
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

const props = withDefaults(defineProps<{
  userName?: string
  error?: string | null
  loading?: boolean
  maxDigits?: number
  tieneTurnoActivo?: boolean | null
}>(), {
  maxDigits: 4,
  tieneTurnoActivo: undefined
})

const emit = defineEmits<{
  confirm: [pin: string]
  cancel: []
}>()

const digits = ref<string[]>([])

const keys = [
  { label: '1', action: '1', variant: 'digit' },
  { label: '2', action: '2', variant: 'digit' },
  { label: '3', action: '3', variant: 'digit' },
  { label: '4', action: '4', variant: 'digit' },
  { label: '5', action: '5', variant: 'digit' },
  { label: '6', action: '6', variant: 'digit' },
  { label: '7', action: '7', variant: 'digit' },
  { label: '8', action: '8', variant: 'digit' },
  { label: '9', action: '9', variant: 'digit' },
  { label: '×', action: 'cancel', variant: 'cancel' },
  { label: '0', action: '0', variant: 'digit' },
  { label: 'back', action: 'back', variant: 'back' },
]

function handleKey(action: string) {
  if (props.loading) return
  if (action === 'cancel') {
    digits.value = []
    emit('cancel')
    return
  }
  if (action === 'back') {
    digits.value = digits.value.slice(0, -1)
    return
  }
  if (digits.value.length >= (props.maxDigits ?? 4)) return
  digits.value = [...digits.value, action]
}

// Auto-confirm when maxDigits reached
watch(digits, (val) => {
  if (val.length === (props.maxDigits ?? 4)) {
    const pin = val.join('')
    setTimeout(() => {
      emit('confirm', pin)
      digits.value = []
    }, 150)
  }
})

// Reset digits when error changes (wrong PIN retry)
watch(() => props.error, (err) => {
  if (err) digits.value = []
})
</script>
