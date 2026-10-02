import { describe, expect, it } from 'vitest'
import { getSessionExpiration, getTokenExpiration, isTokenExpired } from './jwt'

function tokenWithPayload(payload: object): string {
  return `header.${btoa(JSON.stringify(payload))}.signature`
}

describe('JWT expiry helpers', () => {
  it('reads the exp claim in milliseconds', () => {
    expect(getTokenExpiration(tokenWithPayload({ exp: 1_800_000_000 }))).toBe(1_800_000_000_000)
  })

  it('treats expired, malformed, and exp-less tokens as invalid', () => {
    expect(isTokenExpired(tokenWithPayload({ exp: 100 }), 100_000)).toBe(true)
    expect(isTokenExpired(tokenWithPayload({}), 0)).toBe(true)
    expect(isTokenExpired('not-a-jwt')).toBe(true)
  })

  it('keeps a token valid until its exact expiration instant', () => {
    const token = tokenWithPayload({ exp: 100 })
    expect(isTokenExpired(token, 99_999)).toBe(false)
    expect(isTokenExpired(token, 100_000)).toBe(true)
  })

  it('expires a jornada token at the 05:00 Mexico cutoff', () => {
    const token = tokenWithPayload({ jornada: '2026-08-25', exp: 2_000_000_000 })
    const beforeCutoff = Date.parse('2026-08-26T10:59:59Z') // 04:59:59 CDMX
    const cutoff = Date.parse('2026-08-26T11:00:00Z') // 05:00:00 CDMX

    expect(isTokenExpired(token, beforeCutoff)).toBe(false)
    expect(getSessionExpiration(token, beforeCutoff)).toBe(cutoff)
    expect(isTokenExpired(token, cutoff)).toBe(true)
  })
})
