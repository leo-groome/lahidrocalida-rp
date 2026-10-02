/** Lee el payload de un JWT sin verificar su firma.
 * La firma siempre la valida el backend; esto solo evita conservar o enviar un
 * token cuyo `exp` o jornada ya vencieron.
 */
interface JwtPayload {
  exp?: unknown
  jornada?: unknown
}

function getTokenPayload(token: string): JwtPayload | null {
  try {
    const payload = token.split('.')[1]
    if (!payload) return null

    const normalizedPayload = payload.replace(/-/g, '+').replace(/_/g, '/')
    return JSON.parse(atob(normalizedPayload)) as JwtPayload
  } catch {
    return null
  }
}

export function getTokenExpiration(token: string): number | null {
  const expiration = getTokenPayload(token)?.exp
  return typeof expiration === 'number' && Number.isFinite(expiration)
    ? expiration * 1000
    : null
}

function jornadaActual(now: number): string {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Mexico_City',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(new Date(now))
  const value = (type: string) => parts.find((part) => part.type === type)?.value ?? ''
  const fecha = new Date(Date.UTC(Number(value('year')), Number(value('month')) - 1, Number(value('day'))))
  if (Number(value('hour')) < 5) fecha.setUTCDate(fecha.getUTCDate() - 1)
  return fecha.toISOString().slice(0, 10)
}

/** Refleja la invalidez localmente verificable que aplica el backend. */
export function isTokenExpired(token: string, now = Date.now()): boolean {
  const payload = getTokenPayload(token)
  const expiration = getTokenExpiration(token)
  if (!payload || expiration === null || expiration <= now) return true

  return typeof payload.jornada === 'string' && payload.jornada !== jornadaActual(now)
}

/** Momento más próximo en que el token deja de ser válido en el cliente. */
export function getSessionExpiration(token: string, now = Date.now()): number | null {
  const payload = getTokenPayload(token)
  const expiration = getTokenExpiration(token)
  if (!payload || expiration === null) return null
  if (typeof payload.jornada !== 'string') return expiration

  // La jornada del backend termina a las 05:00 hora de México. Actualmente
  // America/Mexico_City no observa DST, por lo que -06:00 es su offset fijo.
  const jornadaDate = new Date(`${payload.jornada}T00:00:00Z`)
  jornadaDate.setUTCDate(jornadaDate.getUTCDate() + 1)
  const cutoffDay = jornadaDate.toISOString().slice(0, 10)
  const jornadaExpiration = new Date(`${cutoffDay}T05:00:00-06:00`).getTime()
  return Math.min(expiration, jornadaExpiration > now ? jornadaExpiration : expiration)
}
