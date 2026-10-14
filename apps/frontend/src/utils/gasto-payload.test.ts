import { describe, it, expect } from 'vitest'
import { prepararPayloadGasto } from './gasto-payload'
import { precioSugerido } from './precio-sugerido'

describe('contrato de gastos', () => {
  it('conserva UUID y fecha de un snapshot reintentado', () => {
    const snapshot = prepararPayloadGasto({ tipo_gasto: 'directo', metodo_pago: 'efectivo', total_manual: 100 })
    expect(prepararPayloadGasto(snapshot)).toEqual(snapshot)
    expect(snapshot.client_request_id).toBeTruthy()
  })
  it('nómina mantiene empleados sin líneas de artículos', () => {
    const input = { tipo_gasto: 'nomina', metodo_pago: 'efectivo', nomina_detalles: [{ usuario_id: 1, monto: 500 }] }
    expect(prepararPayloadGasto(input).nomina_detalles).toEqual(input.nomina_detalles)
    expect(prepararPayloadGasto(input).detalles).toEqual([])
  })
  it('sugerir precio no sobrescribe importe ni edición manual', () => {
    expect(precioSugerido(0, 42, false)).toBe(42)
    expect(precioSugerido(50, 42, false)).toBe(50)
    expect(precioSugerido(0, 42, true)).toBe(0)
    expect(precioSugerido(0, NaN, false)).toBe(0)
  })
})
