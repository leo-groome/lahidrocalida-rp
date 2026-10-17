/** Lógica pura de la vista "Ventas por producto" (testeable sin montar componentes). */

export interface VentaDia {
  unidades: number
  ingreso: number
}

export interface ProductoVenta {
  platillo_id: number
  nombre: string
  categoria: string
  unidades: number
  ingreso: number
  precio_promedio: number
  por_dia: Record<string, VentaDia>
}

export interface Totales {
  unidades: number
  ingreso: number
}

/** minúsculas y sin acentos, para que "pozole" encuentre "Pozolé" y viceversa */
export const normalizar = (s: string): string =>
  s
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .trim()

/**
 * Filtra por texto (todas las palabras deben aparecer en nombre o categoría:
 * "pozole verde" → solo pozoles verdes) y por categoría exacta.
 */
export function filtrarProductos(
  productos: ProductoVenta[],
  texto: string,
  categoria: string | null,
): ProductoVenta[] {
  const palabras = normalizar(texto).split(/\s+/).filter(Boolean)
  return productos.filter((p) => {
    if (categoria && p.categoria !== categoria) return false
    if (!palabras.length) return true
    const hay = normalizar(`${p.nombre} ${p.categoria}`)
    return palabras.every((w) => hay.includes(w))
  })
}

export function totalesDe(productos: ProductoVenta[]): Totales {
  let unidades = 0
  let ingreso = 0
  for (const p of productos) {
    unidades += p.unidades
    ingreso += p.ingreso
  }
  return { unidades, ingreso: Math.round(ingreso * 100) / 100 }
}

/** Unidades vendidas de un producto en un día (0 si no vendió). */
export const unidadesDia = (p: ProductoVenta, dia: string): number => p.por_dia[dia]?.unidades ?? 0

/** Variación porcentual vs el periodo anterior; null si no hay base para comparar. */
export function variacionPct(actual: number, anterior: number): number | null {
  if (!anterior) return null
  return Math.round(((actual - anterior) / anterior) * 100)
}

const celdaCsv = (v: string | number): string => {
  const s = String(v)
  // Escapa comillas y evita inyección de fórmulas al abrir en Excel/Sheets.
  const seguro = /^[=+\-@\t\r]/.test(s) ? `'${s}` : s
  return /[",\n]/.test(seguro) ? `"${seguro.replace(/"/g, '""')}"` : seguro
}

/** CSV con una fila por producto: totales + unidades por día. Separador coma, UTF-8. */
export function aCsv(productos: ProductoVenta[], dias: string[]): string {
  const encabezado = ['Producto', 'Categoría', 'Unidades', 'Ingreso', 'Precio promedio', ...dias]
  const filas = productos.map((p) => [
    p.nombre,
    p.categoria,
    p.unidades,
    p.ingreso.toFixed(2),
    p.precio_promedio.toFixed(2),
    ...dias.map((d) => unidadesDia(p, d)),
  ])
  return [encabezado, ...filas].map((f) => f.map(celdaCsv).join(',')).join('\n')
}
