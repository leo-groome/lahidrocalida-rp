// Parser de texto libre para captura rápida de compras, estilo "quick add" de Todoist.
// Ejemplo: "350 pesos 6kg cueritos" -> cantidad 6, unidad kg, monto 350, articulo "cueritos".
// Debe coincidir con UNIDADES_PERMITIDAS de apps/backend/app/routers/gastos.py.

export type UnidadCanonica = 'kg' | 'g' | 'lt' | 'ml' | 'pza' | 'caja' | 'paq'

export interface LineaParseada {
  raw: string
  cantidad: number | null
  unidad: UnidadCanonica | null
  monto: number | null
  nombreArticulo: string
  precioUnitario: number | null
  ok: boolean
  error?: string
}

// Alias más comunes en español (sin acentos, minúsculas) -> unidad canónica.
const ALIAS_UNIDAD: Record<string, UnidadCanonica> = {
  kg: 'kg', kgs: 'kg', kilo: 'kg', kilos: 'kg', kilogramo: 'kg', kilogramos: 'kg',
  g: 'g', gr: 'g', grs: 'g', gramo: 'g', gramos: 'g',
  lt: 'lt', lts: 'lt', l: 'lt', litro: 'lt', litros: 'lt',
  ml: 'ml', mls: 'ml', mililitro: 'ml', mililitros: 'ml',
  pza: 'pza', pzas: 'pza', pieza: 'pza', piezas: 'pza', unidad: 'pza', unidades: 'pza', u: 'pza',
  caja: 'caja', cajas: 'caja',
  paq: 'paq', paqs: 'paq', paquete: 'paq', paquetes: 'paq',
}

const UNIDAD_REGEX = new RegExp(
  `\\b(\\d+(?:[.,]\\d+)?)\\s*(${Object.keys(ALIAS_UNIDAD).join('|')})\\b`,
  'i',
)

const MONTO_CON_PALABRA_REGEX = /\$?\s*(\d+(?:[.,]\d+)?)\s*(pesos|peso|mxn)\b|\$\s*(\d+(?:[.,]\d+)?)/i
const NUMERO_SUELTO_REGEX = /\b(\d+(?:[.,]\d+)?)\b/

const CONECTORES_SUELTOS = /^(de|del|la|el|los|las|-|,)+\s*|\s*(de|del|-|,)+$/gi

function normalizar(texto: string): string {
  return texto
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .trim()
}

function toNumero(valor: string): number {
  return parseFloat(valor.replace(',', '.'))
}

export function parseLineaCompra(textoOriginal: string): LineaParseada {
  const raw = textoOriginal.trim()
  const texto = normalizar(raw)

  let cantidad: number | null = null
  let unidad: UnidadCanonica | null = null
  let restante = texto

  const matchUnidad = texto.match(UNIDAD_REGEX)
  if (matchUnidad) {
    cantidad = toNumero(matchUnidad[1])
    unidad = ALIAS_UNIDAD[matchUnidad[2].toLowerCase()]
    restante = restante.slice(0, matchUnidad.index) + restante.slice(matchUnidad.index! + matchUnidad[0].length)
  }

  let monto: number | null = null
  const matchMontoConPalabra = restante.match(MONTO_CON_PALABRA_REGEX)
  if (matchMontoConPalabra) {
    monto = toNumero(matchMontoConPalabra[1] ?? matchMontoConPalabra[3])
    restante = restante.slice(0, matchMontoConPalabra.index) + restante.slice(matchMontoConPalabra.index! + matchMontoConPalabra[0].length)
  } else {
    const matchNumeroSuelto = restante.match(NUMERO_SUELTO_REGEX)
    if (matchNumeroSuelto) {
      monto = toNumero(matchNumeroSuelto[1])
      restante = restante.slice(0, matchNumeroSuelto.index) + restante.slice(matchNumeroSuelto.index! + matchNumeroSuelto[0].length)
    }
  }

  const nombreArticulo = restante
    .replace(CONECTORES_SUELTOS, '')
    .replace(/\s+/g, ' ')
    .trim()

  const faltantes: string[] = []
  if (cantidad == null || unidad == null) faltantes.push('no se detectó cantidad/unidad (ej. 6kg)')
  if (monto == null) faltantes.push('no se detectó el monto pagado')
  if (!nombreArticulo) faltantes.push('no se detectó el nombre del artículo')

  const ok = faltantes.length === 0
  const precioUnitario = ok && cantidad ? Math.round((monto! / cantidad) * 100) / 100 : null

  return {
    raw,
    cantidad,
    unidad,
    monto,
    nombreArticulo,
    precioUnitario,
    ok,
    error: faltantes.length ? faltantes.join('; ') : undefined,
  }
}

export function parseComprasTexto(textoMultilinea: string): LineaParseada[] {
  return textoMultilinea
    .split('\n')
    .map((linea) => linea.trim())
    .filter((linea) => linea.length > 0)
    .map(parseLineaCompra)
}

// ── Fila editable en la UI de resolución (texto rápido / registro rápido) ──
// Es una LineaParseada + el artículo del catálogo al que se resolvió.
export interface FilaCompra {
  id: number
  raw: string
  nombreArticulo: string
  cantidad: number | null
  unidad: UnidadCanonica | null
  monto: number | null
  articulo_id: number | null
  ok: boolean
  error?: string
}

let filaSeq = 1

/** Match de un nombre libre contra el catálogo: exacto, luego parcial único. */
export function buscarArticuloMatch(nombre: string, articulos: { id: number; nombre: string }[]): number | null {
  const objetivo = normalizar(nombre)
  if (!objetivo) return null
  const exacto = articulos.find((a) => normalizar(a.nombre) === objetivo)
  if (exacto) return exacto.id
  const parcial = articulos.filter(
    (a) => normalizar(a.nombre).includes(objetivo) || objetivo.includes(normalizar(a.nombre)),
  )
  return parcial.length === 1 ? parcial[0].id : null
}

/** Texto multilínea + catálogo -> filas listas para editar/resolver. */
export function construirFilas(
  textoMultilinea: string,
  articulos: { id: number; nombre: string }[],
): FilaCompra[] {
  return parseComprasTexto(textoMultilinea).map((p) => ({
    id: filaSeq++,
    raw: p.raw,
    nombreArticulo: p.nombreArticulo,
    cantidad: p.cantidad,
    unidad: p.unidad ?? 'kg',
    monto: p.monto,
    articulo_id: buscarArticuloMatch(p.nombreArticulo, articulos),
    ok: p.ok,
    error: p.error,
  }))
}

export function precioUnitarioFila(fila: Pick<FilaCompra, 'cantidad' | 'monto'>): number {
  const cantidad = Number(fila.cantidad) || 0
  const monto = Number(fila.monto) || 0
  if (cantidad <= 0) return 0
  return Math.round((monto / cantidad) * 100) / 100
}

export function filaLista(fila: FilaCompra): boolean {
  return !!fila.articulo_id && Number(fila.cantidad) > 0 && Number(fila.monto) > 0
}

export function filasListas(filas: FilaCompra[]): boolean {
  return filas.length > 0 && filas.every(filaLista)
}

/** Filas resueltas -> `detalles[]` del payload de POST /gastos/. */
export function filasToDetalles(filas: FilaCompra[]) {
  return filas.map((f) => {
    const precio_unitario = precioUnitarioFila(f)
    return {
      articulo_id: f.articulo_id,
      cantidad: f.cantidad,
      precio_unitario,
      subtotal_linea: Math.round(Number(f.cantidad) * precio_unitario * 100) / 100,
      _editadoManual: false,
    }
  })
}
