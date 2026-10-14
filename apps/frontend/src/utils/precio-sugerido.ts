/** Solo sugiere precio en una línea sin importe previo ni edición manual. */
export function precioSugerido(actual: number, costo: number, editado: boolean): number {
  return !editado && !actual && Number.isFinite(costo) && costo >= 0 ? costo : actual
}
