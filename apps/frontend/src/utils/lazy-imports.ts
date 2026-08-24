// Lazy imports para componentes grandes
export const LazyPozoleVariantModal = () => import('@/components/PozoleVariantModal.vue')

// Lazy imports para stores pesados si se necesitan
export const usePedidosStore = () => import('@/stores/pedidos').then(m => m.usePedidosStore)
export const useAuthStore = () => import('@/stores/auth').then(m => m.useAuthStore)