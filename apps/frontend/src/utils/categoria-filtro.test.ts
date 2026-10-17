import { describe, expect, it } from 'vitest'
import { filtrarPorCategoria, parseCategoriaFiltro } from './categoria-filtro'

describe('parseCategoriaFiltro', () => {
  it('convierte el string del select a número', () => {
    expect(parseCategoriaFiltro('4')).toBe(4)
  })
  it('"Todas" (vacío/null) es null', () => {
    expect(parseCategoriaFiltro('')).toBeNull()
    expect(parseCategoriaFiltro(null)).toBeNull()
  })
  it('basura no pasa', () => {
    expect(parseCategoriaFiltro('abc')).toBeNull()
    expect(parseCategoriaFiltro('-3')).toBeNull()
  })
})

describe('filtrarPorCategoria', () => {
  const items = [
    { id: 1, categoria_id: 4 },
    { id: 2, categoria_id: 5 },
    { id: 3, categoria_id: null },
  ]
  it('filtra por id numérico', () => {
    expect(filtrarPorCategoria(items, parseCategoriaFiltro('4')).map((i) => i.id)).toEqual([1])
  })
  it('null devuelve todo, incluso sin categoría', () => {
    expect(filtrarPorCategoria(items, null)).toHaveLength(3)
  })
})
