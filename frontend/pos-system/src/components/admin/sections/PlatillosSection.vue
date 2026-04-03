<template>
  <div class="space-y-8 animate-in fade-in duration-500">
    <!-- Header -->
    <div class="flex flex-wrap items-center justify-between gap-6 bg-white p-8 rounded-3xl shadow-sm border border-slate-100">
      <div class="space-y-1">
        <h2 class="text-2xl font-extrabold text-slate-900 tracking-tight">Menú y Platillos</h2>
        <p class="text-sm font-medium text-slate-500">Configura los platillos, precios y categorías de tu restaurante.</p>
      </div>
      
      <button 
        @click="$emit('new-platillo')" 
        class="inline-flex items-center px-6 py-3 bg-blue-600 text-white rounded-2xl text-sm font-bold shadow-lg shadow-blue-200 hover:bg-blue-700 hover:scale-105 active:scale-95 transition-all"
      >
        <Plus class="h-4 w-4 mr-2" />
        Nuevo Platillo
      </button>
    </div>

    <!-- Filters and Search -->
    <div class="flex flex-wrap items-center justify-between gap-6">
      <div class="flex flex-wrap gap-2 p-1 bg-slate-100 rounded-2xl w-fit border border-slate-200 shadow-inner">
         <button 
           @click="selectedCategory = null" 
           :class="['px-5 py-2.5 rounded-xl text-xs font-black uppercase tracking-widest transition-all duration-200', !selectedCategory ? 'bg-white text-blue-600 shadow-sm ring-1 ring-slate-200/50' : 'text-slate-500 hover:text-slate-800']"
         >
           Todos
         </button>
         <button 
            v-for="cat in categories" :key="cat" 
            @click="selectedCategory = cat" 
            :class="['px-5 py-2.5 rounded-xl text-xs font-black uppercase tracking-widest transition-all duration-200 flex items-center gap-2', selectedCategory === cat ? 'bg-white text-blue-600 shadow-sm ring-1 ring-slate-200/50' : 'text-slate-500 hover:text-slate-800']"
          >
            <span class="text-sm">{{ getCategoryIcon(cat) }}</span>
            {{ cat }}
          </button>
      </div>

      <div class="flex items-center space-x-3 bg-white border border-slate-200 rounded-2xl px-5 py-2.5 shadow-sm group focus-within:ring-2 focus-within:ring-blue-400/20 focus-within:border-blue-400 transition-all">
         <Search class="h-4 w-4 text-slate-400" />
         <input v-model="searchQuery" placeholder="Buscar platillo..." class="bg-transparent text-sm font-bold text-slate-600 focus:outline-none w-48 md:w-64" />
      </div>
    </div>

    <!-- Visual Grid of Platillos -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-6 animate-in slide-in-from-bottom-2 duration-300">
       <div 
         v-for="platillo in filteredPlatillos" 
         :key="platillo.id" 
         class="bg-white rounded-3xl p-5 border border-slate-100 shadow-sm hover:shadow-xl hover:border-blue-200 transition-all duration-300 group cursor-default flex flex-col"
       >
          <!-- Card Header: Icon + Name + Actions -->
          <div class="flex items-start gap-4">
             <!-- Enhanced Icon Badge -->
             <div 
               class="flex-shrink-0 h-14 w-14 rounded-2xl bg-slate-50 flex items-center justify-center text-slate-400 transition-all duration-300 group-hover:bg-blue-600 group-hover:text-white shadow-inner group-hover:shadow-blue-200 group-hover:scale-105"
             >
                <span class="text-3xl transition-transform duration-300 group-hover:scale-110">{{ getCategoryIcon(platillo.categoria) }}</span>
             </div>

             <!-- Name and Category -->
             <div class="flex-1 min-w-0">
                <div class="flex items-center justify-between gap-2">
                  <p class="text-[10px] font-black text-blue-600 uppercase tracking-[0.2em] mb-0.5 opacity-80">{{ platillo.categoria }}</p>
                  <div class="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button @click="$emit('edit-platillo', platillo)" class="p-1.5 bg-slate-50 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-all">
                       <Edit3 class="h-4 w-4" />
                    </button>
                    <button @click="confirmDelete(platillo)" class="p-1.5 bg-slate-50 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all">
                       <Trash2 class="h-4 w-4" />
                    </button>
                  </div>
                </div>
                <h4 class="text-lg font-black text-slate-800 leading-tight group-hover:text-blue-700 transition-colors truncate" :title="platillo.nombre">
                  {{ platillo.nombre }}
                </h4>
                <div class="mt-1 text-xl font-black text-slate-900 tracking-tighter">
                  ${{ formatCurrency(platillo.precio) }}
                </div>
             </div>
          </div>

          <!-- Description -->
          <p class="mt-4 text-xs font-medium text-slate-500 line-clamp-2 italic h-9 leading-relaxed">
            {{ platillo.descripcion || 'Sin descripción detallada' }}
          </p>

          <!-- Footer -->
          <div class="mt-4 pt-4 border-t border-slate-50 flex items-center justify-between">
             <div v-if="platillo.tiene_opciones" class="inline-flex items-center text-[9px] font-black text-emerald-600 uppercase tracking-widest bg-emerald-50 px-2 py-1 rounded-lg">
               <Zap class="h-3 w-3 mr-1" /> Con opciones
             </div>
             <div v-else class="text-[9px] font-bold text-slate-300 uppercase tracking-widest">Simple</div>
             
             <div v-if="platillo.imagen_url" class="h-8 w-8 rounded-full border-2 border-white shadow-sm overflow-hidden bg-slate-100 ring-2 ring-slate-100">
               <img :src="platillo.imagen_url" class="w-full h-full object-cover">
             </div>
          </div>
       </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import api from '@/api/client'
import { 
  Plus, Edit3, Trash2, Search, 
  Zap 
} from 'lucide-vue-next'

const emit = defineEmits(['new-platillo', 'edit-platillo', 'delete-platillo'])

const platillosList = ref<any[]>([])
const categories = ref<string[]>([])
const selectedCategory = ref<string | null>(null)
const searchQuery = ref('')

// Mapeo de iconos por categoría
const getCategoryIcon = (categoria: string) => {
  const map: Record<string, string> = {
    'Pozole': '🍲',
    'Bebidas': '🥤',
    'Antojitos': '🌮',
    'Postres': '🍰',
    'Extras': '🍽️',
    'Enchiladas': '🥘',
    'Flautas': '🌯',
    'Sopes': '🫓',
    'Tacos': '🌮',
    'Tostadas': '🥪',
    'Tamales': '🫔',
    'Especialidades': '✨',
    'Guarniciones': '🥗',
    'Entradas': '🥗'
  }
  return map[categoria] || '🍴'
}

const loadPlatillos = async () => {
   const res = await api.get('/platillos')
   platillosList.value = res.data
   // Ordenar categorías alfabéticamente para que el filtro también se vea ordenado
   const rawCats = [...new Set(res.data.map((p: any) => p.categoria))] as string[]
   categories.value = rawCats.sort((a, b) => a.localeCompare(b))
}

const filteredPlatillos = computed(() => {
   let list = [...platillosList.value] // Clonar para poder ordenar
   
   // Filtro de categoría
   if (selectedCategory.value) {
     list = list.filter(p => p.categoria === selectedCategory.value)
   }
   
   // Filtro de búsqueda
   if (searchQuery.value) {
     const query = searchQuery.value.toLowerCase()
     list = list.filter(p => 
       p.nombre.toLowerCase().includes(query) || 
       (p.descripcion && p.descripcion.toLowerCase().includes(query))
     )
   }

   // ORDENAR: Primero por categoría, luego por nombre
   return list.sort((a, b) => {
      // Si estamos en "Todos", ordenar primero por categoría
      if (!selectedCategory.value) {
        const catCompare = a.categoria.localeCompare(b.categoria)
        if (catCompare !== 0) return catCompare
      }
      // Luego ordenar por nombre
      return a.nombre.localeCompare(b.nombre)
   })
})

const formatCurrency = (val: any) => {
  const n = Number(val)
  return isNaN(n) ? '0.00' : n.toFixed(2)
}

const confirmDelete = (p: any) => {
   if (confirm(`¿Confirmar eliminación de "${p.nombre}"?`)) {
     emit('delete-platillo', p.id)
   }
}

onMounted(loadPlatillos)

defineExpose({ loadPlatillos })
</script>
