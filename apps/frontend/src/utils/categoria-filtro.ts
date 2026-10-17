/** `<select>` siempre entrega string: "" = todas, "4" = id 4. Comparar contra
 * `categoria_id` numérico con `===` dejaba la lista vacía (SA G1). */
export function parseCategoriaFiltro(valor: string | number | null | undefined): number | null {
  if (valor === null || valor === undefined || valor === '') return null
  const n = Number(valor)
  return Number.isInteger(n) && n > 0 ? n : null
}

export function filtrarPorCategoria<T extends { categoria_id?: number | null }>(
  items: T[],
  categoriaId: number | null,
): T[] {
  return categoriaId === null ? items : items.filter((a) => a.categoria_id === categoriaId)
}
