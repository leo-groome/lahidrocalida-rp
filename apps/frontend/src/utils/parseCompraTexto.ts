// Parser de texto libre para captura rápida de compras, estilo "quick add" de Todoist.
// Ejemplo: "350 pesos 6kg cueritos" -> cantidad 6, unidad kg, monto 350, articulo "cueritos".
// Debe coincidir con UNIDADES_PERMITIDAS de apps/backend/app/routers/gastos.py.
// Tolerante a dictado por voz (Wispr Flow): ver fuzzyMatch.ts para el match de catálogo.

import { mejorMatch, quitarAcentos } from './fuzzyMatch'

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
  `(?<![\\w.,])(\\d+(?:[.,]\\d+)?)\\s*(${Object.keys(ALIAS_UNIDAD).sort((a, b) => b.length - a.length).join('|')})(?![a-z])`,
  'i',
)

// Números dictados en palabras, solo cuando preceden a una unidad ("dos kilos", "una caja").
const NUMEROS_PALABRA: Record<string, number> = {
  un: 1, uno: 1, una: 1, dos: 2, tres: 3, cuatro: 4, cinco: 5, seis: 6, siete: 7, ocho: 8, nueve: 9,
  diez: 10, once: 11, doce: 12, quince: 15, veinte: 20, treinta: 30, cuarenta: 40, cincuenta: 50,
  medio: 0.5, media: 0.5,
}
const UNIDADES_ALT = Object.keys(ALIAS_UNIDAD).sort((a, b) => b.length - a.length).join('|')
const PALABRAS_NUM = Object.keys(NUMEROS_PALABRA).join('|')

const MONTO_CON_PALABRA_REGEX =
  /\$?\s*(\d+(?:[.,]\d+)?)\s*(?:pesos|peso|mxn|varos|baros|pesitos)(?![a-z])|\$\s*(\d+(?:[.,]\d+)?)/i
const NUMERO_SUELTO_REGEX = /(?<![\w.,])(\d+(?:[.,]\d+)?)(?![\w])/

// Muletillas de dictado que sobran en los bordes del nombre del artículo.
const RELLENO = new Set([
  'de', 'del', 'la', 'el', 'los', 'las', 'por', 'a', 'en', 'un', 'una', 'unos', 'unas', 'me', 'costo',
  'costaron', 'cuesta', 'pague', 'pagamos', 'compre', 'compramos', 'fueron', 'son', 'es', 'y', 'con',
  'para', 'pesos', 'peso', 'mxn', 'total', 'al', 'x',
])

export const normalizar = quitarAcentos

function toNumero(valor: string): number {
  // "1,200" -> miles; "9,5" -> decimal
  if (/^\d{1,3}(,\d{3})+$/.test(valor)) return parseFloat(valor.replace(/,/g, ''))
  return parseFloat(valor.replace(',', '.'))
}

/** Limpia ruido típico del dictado: puntuación, "$ 192", "1,200", números en palabras. */
function limpiarDictado(texto: string): string {
  let t = texto
    .replace(/[;:!?¿¡"“”()]/g, ' ')
    .replace(/\.(?=\s|$)/g, ' ') // punto final de oración, no decimales
    .replace(/\$\s+(?=\d)/g, '$')
  // "kilo y medio" / "litro y medio" -> 1.5 kg
  t = t.replace(
    new RegExp(`(?<![\\w])(${PALABRAS_NUM}|\\d+)?\\s*(${UNIDADES_ALT})\\s+y\\s+medio(?![a-z])`, 'g'),
    (_m, n: string | undefined, u: string) => {
      const base = n ? (NUMEROS_PALABRA[n] ?? Number(n)) : 1
      return `${base + 0.5} ${u}`
    },
  )
  // "dos kilos" -> "2 kilos"
  t = t.replace(
    new RegExp(`(?<![\\w])(${PALABRAS_NUM})\\s+(?=(?:${UNIDADES_ALT})(?![a-z]))`, 'g'),
    (_m, n: string) => `${NUMEROS_PALABRA[n]} `,
  )
  return t.replace(/\s+/g, ' ').trim()
}

function recortarRelleno(nombre: string): string {
  const toks = nombre.split(/\s+/).filter(Boolean)
  while (toks.length && (RELLENO.has(toks[0]) || /^[-,.]+$/.test(toks[0]))) toks.shift()
  while (toks.length && (RELLENO.has(toks[toks.length - 1]) || /^[-,.]+$/.test(toks[toks.length - 1]))) toks.pop()
  return toks.join(' ').replace(/^[-,.\s]+|[-,.\s]+$/g, '')
}

export function parseLineaCompra(textoOriginal: string): LineaParseada {
  const raw = textoOriginal.trim()
  const texto = limpiarDictado(normalizar(raw))

  let cantidad: number | null = null
  let unidad: UnidadCanonica | null = null
  let restante = texto

  const matchUnidad = texto.match(UNIDAD_REGEX)
  if (matchUnidad) {
    cantidad = toNumero(matchUnidad[1])
    unidad = ALIAS_UNIDAD[matchUnidad[2].toLowerCase()]
    restante = restante.slice(0, matchUnidad.index) + ' ' + restante.slice(matchUnidad.index! + matchUnidad[0].length)
  }

  let monto: number | null = null
  const matchMontoConPalabra = restante.match(MONTO_CON_PALABRA_REGEX)
  if (matchMontoConPalabra) {
    monto = toNumero(matchMontoConPalabra[1] ?? matchMontoConPalabra[2])
    restante = restante.slice(0, matchMontoConPalabra.index) + ' ' + restante.slice(matchMontoConPalabra.index! + matchMontoConPalabra[0].length)
  } else {
    const matchNumeroSuelto = restante.match(NUMERO_SUELTO_REGEX)
    if (matchNumeroSuelto) {
      monto = toNumero(matchNumeroSuelto[1])
      restante = restante.slice(0, matchNumeroSuelto.index) + ' ' + restante.slice(matchNumeroSuelto.index! + matchNumeroSuelto[0].length)
    }
  }

  const nombreArticulo = recortarRelleno(restante.replace(/\s+/g, ' ').trim())

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

/**
 * Separa el dictado en compras. Corta por salto de línea, ";", ". " y por coma/"y"/"luego"
 * cuando lo que sigue empieza con número ("..., 80 pesos 2 kg tomate").
 */
export function dividirLineas(textoMultilinea: string): string[] {
  return textoMultilinea
    .split(/\n|;|\.\s+|,\s+(?=\$?\d)|\s+(?:y|luego|despues|después|otro|otra)\s+(?=\$?\d)/i)
    .map((l) => l.trim())
    .filter((l) => l.length > 0)
}

export function parseComprasTexto(textoMultilinea: string): LineaParseada[] {
  return dividirLineas(textoMultilinea).map(parseLineaCompra)
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
  /** el artículo se eligió por aproximación; conviene revisarlo */
  matchDudoso?: boolean
  matchNombre?: string
  ok: boolean
  error?: string
}

let filaSeq = 1

type ItemCatalogo = { id: number; nombre: string }

/** Match optimista de un nombre libre contra el catálogo (exacto, luego el más parecido). */
export function buscarArticuloMatch(nombre: string, articulos: ItemCatalogo[]): number | null {
  return mejorMatch(nombre, articulos)?.item.id ?? null
}

export interface ProveedorDetectado {
  id: number | null
  nombre: string | null
  /** lo que se dictó, tal cual (útil para avisar cuando no hay match) */
  textoDictado: string
  dudoso: boolean
}

export interface AnalisisCompras {
  filas: FilaCompra[]
  proveedor: ProveedorDetectado | null
}

const KEYWORD_PROVEEDOR = /(?<![a-z])(?:proveedor|proveedora|prov)(?![a-z])\.?\s*/i

/**
 * Busca "proveedor X" en un segmento. X se resuelve probando prefijos de las palabras
 * que siguen a la palabra clave (el mejor match gana) para no depender de delimitadores.
 * Devuelve el segmento sin la parte del proveedor.
 */
function extraerProveedor(
  segmento: string,
  proveedores: ItemCatalogo[],
): { resto: string; proveedor: ProveedorDetectado } | null {
  const norm = normalizar(segmento)
  const m = norm.match(KEYWORD_PROVEEDOR)
  if (!m || m.index === undefined) return null
  const antes = norm.slice(0, m.index)
  let despues = norm.slice(m.index + m[0].length).replace(/^(?:de|del|es|:|-|,)\s+/, '')
  const palabras = despues.split(/\s+/).filter(Boolean)
  // El nombre es la racha de palabras hasta el primer número/monto.
  let corte = palabras.findIndex((w) => /\d|^\$/.test(w))
  if (corte === -1) corte = palabras.length
  const candidatas = palabras.slice(0, corte)
  if (!candidatas.length) return null

  let mejor: { n: number; id: number; nombre: string; puntaje: number; dudoso: boolean } | null = null
  for (let n = 1; n <= Math.min(candidatas.length, 5); n++) {
    const r = mejorMatch(candidatas.slice(0, n).join(' '), proveedores)
    if (r && (!mejor || r.puntaje > mejor.puntaje + 0.001 || (r.puntaje >= mejor.puntaje - 0.001 && n > mejor.n))) {
      mejor = { n, id: r.item.id, nombre: r.item.nombre, puntaje: r.puntaje, dudoso: r.dudoso }
    }
  }
  if (!mejor) {
    // sin match en catálogo: todo lo que sigue hasta el número es el nombre dictado
    return {
      resto: `${antes} ${palabras.slice(corte).join(' ')}`.replace(/\s+/g, ' ').trim(),
      proveedor: { id: null, nombre: null, textoDictado: candidatas.join(' '), dudoso: true },
    }
  }
  return {
    resto: `${antes} ${candidatas.slice(mejor.n).join(' ')} ${palabras.slice(corte).join(' ')}`.replace(/\s+/g, ' ').trim(),
    proveedor: { id: mejor.id, nombre: mejor.nombre, textoDictado: candidatas.slice(0, mejor.n).join(' '), dudoso: mejor.dudoso },
  }
}

/** Texto multilínea + catálogos -> filas listas para editar/resolver (+ proveedor dictado). */
export function analizarCompras(
  textoMultilinea: string,
  articulos: ItemCatalogo[],
  proveedores: ItemCatalogo[] = [],
): AnalisisCompras {
  let proveedor: ProveedorDetectado | null = null
  const filas: FilaCompra[] = []

  for (const segmento of dividirLineas(textoMultilinea)) {
    let linea = segmento
    const prov = extraerProveedor(linea, proveedores)
    if (prov) {
      proveedor = prov.proveedor
      linea = prov.resto
      if (!linea) continue
    } else if (proveedores.length && !/\d/.test(linea)) {
      // Línea sin números que es claramente un proveedor ("don chuy"): lo toma como proveedor.
      const p = mejorMatch(linea, proveedores)
      const a = mejorMatch(linea, articulos)
      if (p && !p.dudoso && (!a || p.puntaje > a.puntaje)) {
        proveedor = { id: p.item.id, nombre: p.item.nombre, textoDictado: linea, dudoso: false }
        continue
      }
    }

    const p = parseLineaCompra(linea)
    const m = mejorMatch(p.nombreArticulo, articulos)
    const fila: FilaCompra = {
      id: filaSeq++,
      raw: p.raw,
      nombreArticulo: p.nombreArticulo,
      cantidad: p.cantidad,
      unidad: p.unidad ?? 'kg',
      monto: p.monto,
      articulo_id: m?.item.id ?? null,
      ok: p.ok,
      error: p.error,
      matchDudoso: m?.dudoso ?? false,
      matchNombre: m?.item.nombre,
    }
    filas.push(fila)
  }
  return { filas, proveedor }
}

/** Texto multilínea + catálogo -> filas listas para editar/resolver. */
export function construirFilas(textoMultilinea: string, articulos: ItemCatalogo[]): FilaCompra[] {
  return analizarCompras(textoMultilinea, articulos).filas
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
