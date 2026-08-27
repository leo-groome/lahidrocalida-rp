import { describe, expect, it } from 'vitest'
import {
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
