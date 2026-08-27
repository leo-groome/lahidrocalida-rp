<template>
  <div class="fixed inset-0 z-[300] flex items-center justify-center bg-black/60 backdrop-blur-sm">
    <div class="bg-white rounded-2xl p-8 w-full max-w-sm mx-4 shadow-2xl">
      <!-- Header -->
      <div class="text-center mb-6 flex flex-col items-center">
        <div v-if="titulo" class="text-xl font-black text-[#00126D] mb-2">{{ titulo }}</div>
        <div v-else-if="userName" class="text-xl font-black text-[#00126D] mb-2">{{ userName }}</div>

        <!-- Status indicator badge -->
        <div v-if="!titulo && tieneTurnoActivo !== undefined" class="inline-flex items-center justify-center mb-4">
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
          <template v-if="mensaje">{{ mensaje }}</template>
          <template v-else-if="tieneTurnoActivo === true">
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

      <!-- Error / Cooldown Alert -->
      <div v-if="error" class="text-center text-sm font-bold mb-4 -mt-2 px-3 py-2 rounded-xl transition-all"
        :class="(cooldownSeconds && cooldownSeconds > 0) ? 'bg-amber-100 text-amber-800 border border-amber-300 animate-pulse' : 'text-red-500 bg-red-50/50'"
      >
        {{ error }}
      </div>

      <!-- Keypad grid -->
      <div class="grid grid-cols-3 gap-3">
        <button
          v-for="key in keys"
          :key="key.label"
          :disabled="loading || (cooldownSeconds !== undefined && cooldownSeconds > 0)"
          @click="handleKey(key.action)"
          class="flex items-center justify-center min-h-[64px] rounded-2xl text-2xl font-black transition-all duration-100 select-none disabled:opacity-40 disabled:cursor-not-allowed"
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
import { ref, watch, onMounted, onUnmounted } from 'vue'

const props = withDefaults(defineProps<{
  userName?: string
  titulo?: string
  mensaje?: string
  error?: string | null
  loading?: boolean
  maxDigits?: number
  tieneTurnoActivo?: boolean | null
  cooldownSeconds?: number
}>(), {
  maxDigits: 4,
  tieneTurnoActivo: undefined,
  cooldownSeconds: 0
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
  if (props.loading || (props.cooldownSeconds ?? 0) > 0) return
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

function handleKeyDown(e: KeyboardEvent) {
  if (props.loading || (props.cooldownSeconds ?? 0) > 0) return

  // Digit keys: '0'-'9' or 'Numpad0'-'Numpad9'
  if (/^[0-9]$/.test(e.key)) {
    e.preventDefault()
    handleKey(e.key)
    return
  }

  if (e.code && e.code.startsWith('Numpad') && e.code.length === 7) {
    const digit = e.code.replace('Numpad', '')
    if (/^[0-9]$/.test(digit)) {
      e.preventDefault()
      handleKey(digit)
      return
    }
  }

  if (e.key === 'Backspace' || e.key === 'Delete') {
    e.preventDefault()
    handleKey('back')
    return
  }

  if (e.key === 'Escape' || e.key === 'c' || e.key === 'C') {
    e.preventDefault()
    handleKey('cancel')
    return
  }

  if (e.key === 'Enter' || e.key === 'NumpadEnter') {
    e.preventDefault()
    if (digits.value.length === (props.maxDigits ?? 4)) {
      const pin = digits.value.join('')
      emit('confirm', pin)
      digits.value = []
    }
    return
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
})

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
