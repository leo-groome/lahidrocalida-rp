import { api } from '@/api/client'

export const MAX_FOTOS = 5
const MAX_LADO = 1600
const CALIDAD = 0.8
const TIMEOUT_SUBIDA_MS = 60_000
const EXT: Record<string, string> = { 'image/webp': 'webp', 'image/png': 'png', 'image/heic': 'heic' }

/**
 * Convierte la foto a WebP (lado mayor 1600px, calidad 0.8): es más liviana y
 * más barata de renderizar. Si el navegador no puede codificar WebP (Safari
 * viejo) cae a JPEG; si no puede ni decodificar la imagen (p. ej. HEIC en
 * Chrome) se envía el original: el backend valida el formato por contenido.
 */
export async function comprimirImagen(file: File): Promise<Blob> {
  // Ya convertida al elegirla: no recomprimir (evita doble pérdida).
  if (file.type === 'image/webp' && file.size < 1_500_000) return file
  try {
    const bitmap = await createImageBitmap(file)
    const escala = Math.min(1, MAX_LADO / Math.max(bitmap.width, bitmap.height))
    const canvas = document.createElement('canvas')
    canvas.width = Math.round(bitmap.width * escala)
    canvas.height = Math.round(bitmap.height * escala)
    canvas.getContext('2d')!.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
    bitmap.close()
    let blob = await new Promise<Blob | null>((res) => canvas.toBlob(res, 'image/webp', CALIDAD))
    if (!blob || blob.type !== 'image/webp') {
      blob = await new Promise<Blob | null>((res) => canvas.toBlob(res, 'image/jpeg', CALIDAD))
    }
    return blob && blob.size < file.size ? blob : file
  } catch {
    return file
  }
}

/** Convierte a WebP al elegir la foto, para que subir después sea instantáneo. */
export async function prepararFoto(file: File): Promise<File> {
  const blob = await comprimirImagen(file)
  if (blob === file) return file
  const ext = EXT[blob.type] ?? 'jpg'
  return new File([blob], `ticket.${ext}`, { type: blob.type })
}

/** Sube las fotos de un gasto ya creado. Devuelve cuántas fallaron. */
export async function subirAdjuntos(gastoId: number, fotos: File[]): Promise<number> {
  let fallidas = 0
  for (const foto of fotos) {
    try {
      const blob = await comprimirImagen(foto)
      const form = new FormData()
      form.append('archivo', blob, `ticket.${EXT[blob.type] ?? 'jpg'}`)
      await api.post(`/gastos/${gastoId}/adjuntos`, form, { timeout: TIMEOUT_SUBIDA_MS })
    } catch {
      fallidas++
    }
  }
  return fallidas
}

/** Descarga un adjunto (endpoint autenticado) y devuelve una URL de objeto para <img>. */
export async function urlAdjunto(gastoId: number, adjuntoId: number): Promise<string> {
  const { data } = await api.get(`/gastos/${gastoId}/adjuntos/${adjuntoId}/archivo`, {
    responseType: 'blob',
  })
  return URL.createObjectURL(data)
}
