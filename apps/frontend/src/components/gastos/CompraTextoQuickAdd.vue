<template>
  <div class="p-4 space-y-4">
    <div class="space-y-2">
      <label class="text-xs font-black text-slate-400 uppercase tracking-widest ml-1">
        Escribe tus compras, una por línea
      </label>
      <textarea
        v-model="texto"
        rows="4"
        placeholder="350 pesos 6kg cueritos&#10;120 pesos 2kg jitomate"
        class="w-full px-4 py-3 text-sm border border-slate-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-[#00126D]/20 focus:border-[#00126D] resize-none transition-colors font-medium"
      />
      <button
        type="button"
        @click="analizar"
        :disabled="!texto.trim()"
        class="w-full py-3 bg-slate-100 text-slate-600 font-black rounded-2xl text-sm active:scale-[0.98] transition-all disabled:opacity-40"
      >
        Analizar texto
      </button>
    </div>

    <div v-if="filas.length" class="max-h-[40vh] overflow-y-auto">
      <ComprasFilasResolver
        :filas="filas"
        :articulos="props.articulos"
        :categorias="props.categorias"
        @quitar-fila="quitarFila"
        @articulo-creado="(arts) => emit('articulo-creado', arts)"
      />
    </div>

    <button
      v-if="filas.length"
      type="button"
      @click="confirmar"
      :disabled="!todasListas"
      class="w-full py-4 bg-[#00126D] text-white font-black rounded-2xl disabled:opacity-40 disabled:cursor-not-allowed active:scale-[0.98] transition-all"
    >
      Agregar {{ filas.length }} artículo(s) a la compra
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import {
  construirFilas,
  filasListas,
  filasToDetalles,
  type FilaCompra,
} from '@/utils/parseCompraTexto'
import ComprasFilasResolver from './ComprasFilasResolver.vue'

const props = defineProps<{
  articulos: any[]
  categorias: any[]
}>()

const emit = defineEmits<{
  'agregar-detalles': [detalles: any[]]
  'articulo-creado': [articulo: any]
}>()

const texto = ref('')
const filas = ref<FilaCompra[]>([])

function analizar() {
  filas.value = construirFilas(texto.value, props.articulos)
}

function quitarFila(id: number) {
  filas.value = filas.value.filter((f) => f.id !== id)
}

const todasListas = computed(() => filasListas(filas.value))

function confirmar() {
  emit('agregar-detalles', filasToDetalles(filas.value))
  texto.value = ''
  filas.value = []
}
</script>
