// Match difuso para texto dictado por voz (Wispr Flow): tolera plurales, acentos,
// confusiones fonéticas del español (b/v, c/s/z, ll/y, h muda, qu/k) y typos.

const STOPWORDS = new Set(['de', 'del', 'la', 'el', 'los', 'las', 'y', 'con', 'en', 'para', 'por', 'al'])

export function quitarAcentos(texto: string): string {
  return texto.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim()
}

/** Forma fonética aproximada de UNA palabra (ya sin acentos, minúsculas). */
function fonetica(palabra: string): string {
  let p = palabra
    .replace(/[^a-z0-9]/g, '')
    .replace(/^h/, '')
    .replace(/h/g, '')
    .replace(/ll/g, 'y')
    .replace(/qu([ei])/g, 'k$1')
    .replace(/c([ei])/g, 's$1')
    .replace(/z/g, 's')
    .replace(/c/g, 'k')
    .replace(/v/g, 'b')
    .replace(/w/g, 'b')
    .replace(/g([ei])/g, 'j$1')
    .replace(/x/g, 's')
    .replace(/(.)\1+/g, '$1')
  // plural: -es / -s (solo si queda una raíz razonable)
  if (p.length > 4 && p.endsWith('es')) p = p.slice(0, -2)
  else if (p.length > 3 && p.endsWith('s')) p = p.slice(0, -1)
  return p
}

export function tokensFoneticos(texto: string): string[] {
  return quitarAcentos(texto)
    .split(/[^a-z0-9]+/)
    .filter((t) => t && !STOPWORDS.has(t))
    .map(fonetica)
    .filter(Boolean)
}

function levenshtein(a: string, b: string): number {
  if (a === b) return 0
  if (!a.length) return b.length
  if (!b.length) return a.length
  let prev = Array.from({ length: b.length + 1 }, (_, i) => i)
  for (let i = 1; i <= a.length; i++) {
    const cur = [i]
    for (let j = 1; j <= b.length; j++) {
      cur[j] = Math.min(
        prev[j] + 1,
        cur[j - 1] + 1,
        prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1),
      )
    }
    prev = cur
  }
  return prev[b.length]
}

/** Similitud 0..1 entre dos tokens fonéticos. */
function simToken(a: string, b: string): number {
  if (a === b) return 1
  const max = Math.max(a.length, b.length)
  if (max === 0) return 0
  let s = 1 - levenshtein(a, b) / max
  // prefijo compartido largo ("tortilla" vs "tortillas de harina"): ayuda con cortes de dictado
  const minLen = Math.min(a.length, b.length)
  if (minLen >= 4 && (a.startsWith(b) || b.startsWith(a))) s = Math.max(s, 0.85)
  // palabras muy cortas con 1 error son poco confiables
  if (max <= 3 && s < 1) s = Math.min(s, 0.5)
  return s
}

/** Puntaje 0..1 de qué tan bien `consulta` describe a `candidato`. */
export function puntajeMatch(consulta: string, candidato: string): number {
  const q = tokensFoneticos(consulta)
  const c = tokensFoneticos(candidato)
  if (!q.length || !c.length) return 0

  const mejor = (t: string, pool: string[]) => pool.reduce((m, x) => Math.max(m, simToken(t, x)), 0)
  // tokens que no se parecen a nada cuentan 0 (no arrastran puntaje por azar)
  const umbral = (s: number) => (s >= 0.6 ? s : 0)
  const qCov = q.reduce((s, t) => s + umbral(mejor(t, c)), 0) / q.length
  const cCov = c.reduce((s, t) => s + umbral(mejor(t, q)), 0) / c.length

  // El nombre dictado casi siempre es una versión corta/larga del del catálogo:
  // pesa más que lo dictado quede cubierto que el catálogo completo.
  const tokens = 0.7 * qCov + 0.3 * cCov
  // Comparación de cadena completa por si el dictado partió/unió palabras ("jitomate" / "ji tomate")
  const fq = q.join('')
  const fc = c.join('')
  const completo = 1 - levenshtein(fq, fc) / Math.max(fq.length, fc.length)
  return Math.max(tokens, fq.length >= 5 && fc.length >= 5 ? completo : 0)
}

export interface ResultadoMatch<T> {
  item: T
  puntaje: number
}

export interface MatchElegido<T> {
  item: T
  puntaje: number
  /** true si conviene que el usuario lo revise (no es exacto o hay otro casi igual) */
  dudoso: boolean
}

export const UMBRAL_MATCH = 0.62
const UMBRAL_SEGURO = 0.88
const MARGEN_SEGURO = 0.1

export function rankear<T extends { nombre: string }>(consulta: string, items: T[]): ResultadoMatch<T>[] {
  return items
    .map((item) => ({ item, puntaje: puntajeMatch(consulta, item.nombre) }))
    .filter((r) => r.puntaje > 0)
    .sort((a, b) => b.puntaje - a.puntaje)
}

/**
 * Elige la mejor coincidencia de forma optimista: si hay una razonablemente
 * parecida la devuelve, marcándola `dudoso` cuando no es clara.
 */
export function mejorMatch<T extends { nombre: string }>(consulta: string, items: T[]): MatchElegido<T> | null {
  const objetivo = quitarAcentos(consulta)
  if (!objetivo) return null
  const exacto = items.find((i) => quitarAcentos(i.nombre) === objetivo)
  if (exacto) return { item: exacto, puntaje: 1, dudoso: false }

  const ranking = rankear(consulta, items)
  const [top, segundo] = ranking
  if (!top || top.puntaje < UMBRAL_MATCH) return null
  const ambiguo = !!segundo && top.puntaje - segundo.puntaje < MARGEN_SEGURO
  return { item: top.item, puntaje: top.puntaje, dudoso: top.puntaje < UMBRAL_SEGURO || ambiguo }
}
