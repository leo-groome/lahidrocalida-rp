<template>
  <header class="h-16 flex items-center justify-between px-8 bg-white/80 backdrop-blur-md border-b border-slate-200 sticky top-0 z-20">
    <div class="flex items-center space-x-4">
      <h1 class="text-xl font-bold text-slate-800 tracking-tight">{{ title }}</h1>
    </div>

    <div class="flex items-center space-x-6">
      <!-- Search/Filters Placeholder if needed -->
      <slot name="filters"></slot>

      <div class="h-6 w-px bg-slate-200"></div>

      <div class="flex items-center space-x-3 group cursor-default">
        <div class="h-8 w-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-bold text-xs ring-2 ring-transparent group-hover:ring-blue-400/20 transition-all">
          {{ userName.charAt(0).toUpperCase() }}
        </div>
        <div class="flex flex-col">
          <span class="text-sm font-semibold text-slate-700 leading-none truncate max-w-[120px]">{{ userName }}</span>
          <span class="text-[10px] text-slate-400 font-bold uppercase mt-0.5 tracking-wider">Admin</span>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  title: string
  userName?: string
}>(), {
  userName: 'Administrador'
})
</script>
