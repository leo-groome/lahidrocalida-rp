import { describe, expect, it } from 'vitest'
import {
  aCsv,
  filtrarProductos,
  normalizar,
  totalesDe,
  unidadesDia,
  variacionPct,
  type ProductoVenta,
} from './ventas-producto'

const p = (id: number, nombre: string, categoria: string, u: number, ing: number, dias = {}): ProductoVenta => ({
  platillo_id: id,
  nombre,
  categoria,
  unidades: u,
  ingreso: ing,
  precio_promedio: u ? ing / u : 0,
  por_dia: dias,
})

const datos = [
  p(1, 'Pozole Regular Verde Puerco', 'Pozole', 5, 650, { '2026-10-16': { unidades: 5, ingreso: 650 } }),
  p(2, 'Pozole Grande Verde Pollo', 'Pozole', 2, 300),
  p(3, 'Pozole Regular Rojo Puerco', 'Pozole', 9, 1080),
  p(4, 'Tamal Verde', 'Tamales', 4, 224),
]

describe('filtrarProductos', () => {
  it('"pozole verde" exige ambas palabras (no trae el tamal verde ni el pozole rojo)', () => {
    const r = filtrarProductos(datos, 'pozole verde', null)
    expect(r.map((x) => x.platillo_id)).toEqual([1, 2])
    expect(totalesDe(r)).toEqual({ unidades: 7, ingreso: 950 })
  })
  it('ignora acentos y mayúsculas', () => {
    expect(normalizar('  Pozolé ')).toBe('pozole')
    expect(filtrarProductos(datos, 'POZOLÉ', null)).toHaveLength(3)
  })
  it('categoría + texto se combinan', () => {
    expect(filtrarProductos(datos, 'verde', 'Tamales').map((x) => x.platillo_id)).toEqual([4])
  })
  it('sin filtros devuelve todo', () => {
    expect(filtrarProductos(datos, '', null)).toHaveLength(4)
  })
})

describe('totales y variación', () => {
  it('unidadesDia es 0 si no vendió ese día', () => {
    expect(unidadesDia(datos[0], '2026-10-16')).toBe(5)
    expect(unidadesDia(datos[0], '2026-10-17')).toBe(0)
  })
  it('variacionPct', () => {
    expect(variacionPct(150, 100)).toBe(50)
    expect(variacionPct(50, 100)).toBe(-50)
    expect(variacionPct(100, 0)).toBeNull()
  })
})

describe('aCsv', () => {
  it('encabezado con días y una fila por producto', () => {
    const csv = aCsv([datos[0]], ['2026-10-16', '2026-10-17']).split('\n')
    expect(csv[0]).toBe('Producto,Categoría,Unidades,Ingreso,Precio promedio,2026-10-16,2026-10-17')
    expect(csv[1]).toBe('Pozole Regular Verde Puerco,Pozole,5,650.00,130.00,5,0')
  })
  it('escapa comas/comillas y neutraliza fórmulas', () => {
    const raro = p(9, '=HYPERLINK("x")', 'a,b', 1, 1)
    const fila = aCsv([raro], []).split('\n')[1]
    expect(fila.startsWith('"\'=HYPERLINK(""x"")","a,b"')).toBe(true)
  })
})
