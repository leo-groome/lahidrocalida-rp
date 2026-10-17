import { describe, expect, it } from 'vitest'
import {
  datetimeLocalAhora,
  hoyJornada,
  rangoAnio,
  rangoMes,
  rangoSemana,
  rangoUltimosDias,
} from './fecha'

// 2026-10-17 es sábado. México = UTC-6 todo el año.
const sabado1200 = Date.parse('2026-10-17T12:00:00-06:00')
const sabado2300 = Date.parse('2026-10-17T23:00:00-06:00') // ya es 18 oct en UTC
const domingo0020 = Date.parse('2026-10-18T00:20:00-06:00') // sigue la jornada del sábado

describe('hoyJornada', () => {
  it('a las 23:00 locales sigue siendo hoy (no el día UTC)', () => {
    expect(hoyJornada(sabado2300)).toBe('2026-10-17')
  })
  it('a las 00:20 locales todavía es la jornada de ayer', () => {
    expect(hoyJornada(domingo0020)).toBe('2026-10-17')
  })
})

describe('rangoSemana (Martes→Domingo)', () => {
  it('sábado → martes 13 a domingo 18', () => {
    expect(rangoSemana(sabado1200)).toEqual({ inicio: '2026-10-13', fin: '2026-10-18' })
  })
  it('es estable a las 23:00 (no se recorre un día)', () => {
    expect(rangoSemana(sabado2300)).toEqual({ inicio: '2026-10-13', fin: '2026-10-18' })
  })
  it('semana pasada = calendario anterior, no ventana móvil', () => {
    expect(rangoSemana(sabado1200, -1)).toEqual({ inicio: '2026-10-06', fin: '2026-10-11' })
  })
  it('lunes pertenece a la semana que termina el domingo anterior', () => {
    const lunes = Date.parse('2026-10-12T15:00:00-06:00')
    expect(rangoSemana(lunes)).toEqual({ inicio: '2026-10-06', fin: '2026-10-11' })
  })
})

describe('rangoMes / rangoAnio / rangoUltimosDias', () => {
  it('mes actual y anterior', () => {
    expect(rangoMes(sabado1200)).toEqual({ inicio: '2026-10-01', fin: '2026-10-31' })
    expect(rangoMes(sabado1200, -1)).toEqual({ inicio: '2026-09-01', fin: '2026-09-30' })
  })
  it('último día del mes a las 23:00 no salta de mes', () => {
    const fin = Date.parse('2026-10-31T23:30:00-06:00')
    expect(rangoMes(fin)).toEqual({ inicio: '2026-10-01', fin: '2026-10-31' })
  })
  it('año', () => {
    expect(rangoAnio(sabado1200)).toEqual({ inicio: '2026-01-01', fin: '2026-12-31' })
  })
  it('últimos 7 días incluye hoy', () => {
    expect(rangoUltimosDias(7, sabado1200)).toEqual({ inicio: '2026-10-11', fin: '2026-10-17' })
  })
})

describe('datetimeLocalAhora', () => {
  it('formato YYYY-MM-DDTHH:mm', () => {
    expect(datetimeLocalAhora(new Date())).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/)
  })
})
