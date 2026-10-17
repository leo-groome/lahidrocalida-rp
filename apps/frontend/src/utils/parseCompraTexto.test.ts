import { describe, expect, it } from 'vitest'
import {
  analizarCompras,
  buscarArticuloMatch,
  construirFilas,
  filasListas,
  filasToDetalles,
  parseComprasTexto,
  parseLineaCompra,
} from './parseCompraTexto'

describe('parseLineaCompra', () => {
  it('extrae cantidad, unidad, monto, nombre y precio unitario', () => {
    const r = parseLineaCompra('350 pesos 6kg cueritos')
    expect(r.ok).toBe(true)
    expect(r.cantidad).toBe(6)
    expect(r.unidad).toBe('kg')
    expect(r.monto).toBe(350)
    expect(r.nombreArticulo).toBe('cueritos')
    expect(r.precioUnitario).toBe(58.33)
  })

  it('normaliza alias de unidad y acentos', () => {
    const r = parseLineaCompra('2 litros leché $45')
    expect(r.unidad).toBe('lt')
    expect(r.cantidad).toBe(2)
    expect(r.monto).toBe(45)
    expect(r.nombreArticulo).toBe('leche')
  })

  it('marca ok:false cuando falta cantidad/unidad', () => {
    const r = parseLineaCompra('jitomate 120 pesos')
    expect(r.ok).toBe(false)
    expect(r.error).toContain('cantidad/unidad')
  })
})

describe('parseComprasTexto', () => {
  it('una compra por línea, ignora líneas vacías', () => {
    const filas = parseComprasTexto('350 pesos 6kg cueritos\n\n  120 pesos 2kg jitomate  \n')
    expect(filas).toHaveLength(2)
    expect(filas[1].nombreArticulo).toBe('jitomate')
  })
})

describe('construirFilas + helpers', () => {
  const catalogo = [
    { id: 1, nombre: 'Cueritos' },
    { id: 2, nombre: 'Jitomate' },
  ]

  it('resuelve artículo por match y deja null cuando no hay match', () => {
    const filas = construirFilas('350 pesos 6kg cueritos\n80 pesos 1caja servilletas', catalogo)
    expect(filas[0].articulo_id).toBe(1)
    expect(filas[1].articulo_id).toBeNull()
    expect(filasListas(filas)).toBe(false)
  })

  it('filasToDetalles produce el shape del payload de POST /gastos/', () => {
    const filas = construirFilas('300 pesos 6kg cueritos', catalogo)
    expect(filasListas(filas)).toBe(true)
    const [d] = filasToDetalles(filas)
    expect(d).toMatchObject({
      articulo_id: 1,
      cantidad: 6,
      precio_unitario: 50,
      subtotal_linea: 300,
      _editadoManual: false,
    })
  })
})

describe('dictado por voz (Wispr Flow)', () => {
  const l = (t: string) => {
    const r = parseLineaCompra(t)
    return { c: r.cantidad, u: r.unidad, m: r.monto, n: r.nombreArticulo }
  }

  it('"192 pesos por 9 kg de tortilla"', () => {
    expect(l('192 pesos por 9 kg de tortilla')).toEqual({ c: 9, u: 'kg', m: 192, n: 'tortilla' })
  })
  it.each([
    ['me costó 192 pesos 9 kilos de tortilla', { c: 9, u: 'kg', m: 192, n: 'tortilla' }],
    ['9 kg. de tortilla por 192', { c: 9, u: 'kg', m: 192, n: 'tortilla' }],
    ['Tortilla, 9 kilos, $192.', { c: 9, u: 'kg', m: 192, n: 'tortilla' }],
    ['$1,200 pesos 20 kg de carne molida', { c: 20, u: 'kg', m: 1200, n: 'carne molida' }],
    ['45.50 pesos 1.5 litros de leche', { c: 1.5, u: 'lt', m: 45.5, n: 'leche' }],
    ['80 pesos dos kilos de jitomate', { c: 2, u: 'kg', m: 80, n: 'jitomate' }],
    ['35 pesos medio kilo de queso', { c: 0.5, u: 'kg', m: 35, n: 'queso' }],
    ['70 pesos kilo y medio de cebolla', { c: 1.5, u: 'kg', m: 70, n: 'cebolla' }],
    ['120 varos 3 piezas de aguacate', { c: 3, u: 'pza', m: 120, n: 'aguacate' }],
    ['80 pesos una caja de servilletas', { c: 1, u: 'caja', m: 80, n: 'servilletas' }],
  ])('%s', (texto, esperado) => {
    expect(l(texto)).toEqual(esperado)
  })

  it('varias compras en un solo dictado corrido', () => {
    const r = parseComprasTexto('192 pesos 9 kg tortilla, 80 pesos 2 kg jitomate y 45 pesos 1 lt leche.')
    expect(r.map((x) => x.nombreArticulo)).toEqual(['tortilla', 'jitomate', 'leche'])
    expect(r.every((x) => x.ok)).toBe(true)
  })
})

describe('match difuso de artículos', () => {
  const catalogo = [
    { id: 1, nombre: 'Tortilla de maíz' },
    { id: 2, nombre: 'Jitomate' },
    { id: 3, nombre: 'Cebolla blanca' },
    { id: 4, nombre: 'Carne molida de res' },
    { id: 5, nombre: 'Aguacate Hass' },
    { id: 6, nombre: 'Queso Oaxaca' },
  ]
  it.each([
    ['tortilla', 1],
    ['tortillas', 1],
    ['tortiya de maiz', 1],
    ['gitomate', 2],
    ['jitomates', 2],
    ['ji tomate', 2],
    ['sebolla', 3],
    ['cebolla', 3],
    ['carne molida', 4],
    ['carne moliada', 4],
    ['aguacates', 5],
    ['aguakate', 5],
    ['agucate', 5],
    ['queso wahaca', 6],
    ['queso oaxaca', 6],
  ])('"%s" -> artículo %i', (dictado, id) => {
    expect(buscarArticuloMatch(dictado, catalogo)).toBe(id)
  })
  it('no inventa matches para cosas que no están', () => {
    expect(buscarArticuloMatch('servilletas', catalogo)).toBeNull()
    expect(buscarArticuloMatch('refresco', catalogo)).toBeNull()
  })
})

describe('proveedor dictado', () => {
  const arts = [{ id: 1, nombre: 'Tortilla' }, { id: 2, nombre: 'Jitomate' }]
  const provs = [{ id: 10, nombre: 'Tortillería Don Chuy' }, { id: 11, nombre: 'Verduras La Central' }]

  it('proveedor al inicio, antes del monto', () => {
    const r = analizarCompras('proveedor don chuy 192 pesos 9 kg tortilla', arts, provs)
    expect(r.proveedor?.id).toBe(10)
    expect(r.filas).toHaveLength(1)
    expect(r.filas[0]).toMatchObject({ cantidad: 9, monto: 192, articulo_id: 1 })
  })
  it('proveedor al final de la línea', () => {
    const r = analizarCompras('192 pesos 9 kg tortilla proveedor tortileria don chuy', arts, provs)
    expect(r.proveedor?.id).toBe(10)
    expect(r.filas[0].nombreArticulo).toBe('tortilla')
  })
  it('proveedor en su propia línea y mal dictado', () => {
    const r = analizarCompras('Proveedor verduras la sentral\n80 pesos 2 kg jitomate', arts, provs)
    expect(r.proveedor?.id).toBe(11)
    expect(r.filas).toHaveLength(1)
  })
  it('proveedor no registrado: avisa con lo dictado', () => {
    const r = analizarCompras('proveedor abarrotes pepe 50 pesos 1 kg jitomate', arts, provs)
    expect(r.proveedor).toMatchObject({ id: null, textoDictado: 'abarrotes pepe' })
    expect(r.filas).toHaveLength(1)
  })
  it('sin la palabra proveedor no toca nada', () => {
    const r = analizarCompras('192 pesos 9 kg tortilla', arts, provs)
    expect(r.proveedor).toBeNull()
  })
})
