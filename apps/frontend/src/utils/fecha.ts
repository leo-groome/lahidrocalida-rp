/**
 * Fechas de negocio en jornada hora México (05:00→05:00).
 *
 * Nunca construir fechas YYYY-MM-DD con `new Date().toISOString()`: eso es la
 * fecha UTC y, a partir de las 18:00 locales, ya es "mañana". Todo helper de
 * rango parte de la jornada en curso (`jornadaActual`) y hace la aritmética de
 * días sobre strings YYYY-MM-DD en UTC puro, sin depender de la zona del navegador.
 */
import { jornadaActual } from './jwt'

export interface RangoFechas {
  inicio: string
  fin: string
}

const aDate = (iso: string): Date => new Date(`${iso}T00:00:00Z`)
const aIso = (d: Date): string => d.toISOString().slice(0, 10)

export function sumarDias(iso: string, dias: number): string {
  const d = aDate(iso)
  d.setUTCDate(d.getUTCDate() + dias)
  return aIso(d)
}

/** Jornada operativa en curso (YYYY-MM-DD). Antes de las 05:00 sigue siendo la de ayer. */
export function hoyJornada(now: number = Date.now()): string {
  return jornadaActual(now)
}

/** Semana operativa Martes→Domingo. `offset` -1 = la anterior. */
export function rangoSemana(now: number = Date.now(), offset = 0): RangoFechas {
  const hoy = hoyJornada(now)
  const desdeMartes = (aDate(hoy).getUTCDay() - 2 + 7) % 7
  const inicio = sumarDias(hoy, -desdeMartes + offset * 7)
  return { inicio, fin: sumarDias(inicio, 5) }
}

export function rangoMes(now: number = Date.now(), offset = 0): RangoFechas {
  const [y, m] = hoyJornada(now).split('-').map(Number)
  const primero = new Date(Date.UTC(y, m - 1 + offset, 1))
  const ultimo = new Date(Date.UTC(y, m + offset, 0))
  return { inicio: aIso(primero), fin: aIso(ultimo) }
}

export function rangoAnio(now: number = Date.now()): RangoFechas {
  const y = hoyJornada(now).slice(0, 4)
  return { inicio: `${y}-01-01`, fin: `${y}-12-31` }
}

/** Últimos `dias` días terminando en la jornada en curso (inclusive). */
export function rangoUltimosDias(dias: number, now: number = Date.now()): RangoFechas {
  const fin = hoyJornada(now)
  return { inicio: sumarDias(fin, -(dias - 1)), fin }
}

/**
 * Valor por defecto para un <input type="datetime-local">: la hora actual del
 * navegador (que es como `new Date(valor)` la interpreta al guardar).
 */
export function datetimeLocalAhora(now: Date = new Date()): string {
  return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
}
