<template>
  <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 hover:border-blue-400/20 hover:shadow-md transition-all duration-300 group">
    <div class="flex items-center justify-between mb-4">
      <div 
        class="h-10 w-10 rounded-xl flex items-center justify-center transition-all duration-300 group-hover:scale-110"
        :class="iconBg"
      >
        <component :is="icon" class="h-5 w-5" :class="iconColor" />
      </div>
      
      <span 
        v-if="trend !== undefined" 
        class="text-xs font-bold px-2 py-1 rounded-full flex items-center"
        :class="trend >= 0 ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-600'"
      >
        <ArrowUp v-if="trend >= 0" class="h-3 w-3 mr-1" />
        <ArrowDown v-else class="h-3 w-3 mr-1" />
        {{ Math.abs(trend) }}%
      </span>
    </div>

    <div>
      <p class="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-1">{{ label }}</p>
      <div class="flex items-baseline space-x-2">
        <span class="text-3xl font-extrabold text-slate-900 tracking-tight">{{ value }}</span>
        <span v-if="unit" class="text-xs font-bold text-slate-400">{{ unit }}</span>
      </div>
      <p v-if="subtext" class="mt-2 text-xs text-slate-400 font-medium italic truncate">{{ subtext }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ArrowUp, ArrowDown } from 'lucide-vue-next'

defineProps<{
  label: string
  value: string | number
  icon: any
  iconColor: string
  iconBg: string
  trend?: number
  subtext?: string
  unit?: string
}>()
</script>
