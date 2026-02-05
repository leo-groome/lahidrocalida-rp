/**
 * utilidades para manejo de fechas y horas en La Hidrocálida
 */

/**
 * Parsea una cadena de fecha de forma segura, manejando formatos ISO con espacios
 * Ej: "2026-02-05 22:10:23.245896+00" -> Date object
 */
export const parseSafeDate = (dateStr: string | null | undefined): Date | null => {
  if (!dateStr) return null;
  
  try {
    // Si la fecha ya es un objeto Date
    if (dateStr instanceof Date) return dateStr;

    // Normalizar formato: reemplazar espacio entre fecha y hora por 'T' si no lo tiene
    // Esto asegura compatibilidad con estándares ISO en todos los navegadores
    let normalized = dateStr;
    if (typeof dateStr === 'string' && dateStr.includes(' ') && !dateStr.includes('T')) {
      normalized = dateStr.replace(' ', 'T');
    }

    const date = new Date(normalized);
    
    // Validar si es una fecha válida
    if (isNaN(date.getTime())) {
      console.error('❌ Fecha inválida:', dateStr);
      return null;
    }
    
    return date;
  } catch (e) {
    console.error('❌ Error parseando fecha:', dateStr, e);
    return null;
  }
};

/**
 * Formatea una fecha a HH:mm (24h o 12h según configuración regional es-MX)
 */
export const formatTime = (dateStr: string | null | undefined): string => {
  const date = parseSafeDate(dateStr);
  if (!date) return '--:--';
  
  return date.toLocaleTimeString('es-MX', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: true
  });
};

/**
 * Formatea una fecha a DD/MM/YYYY HH:mm
 */
export const formatDateTime = (dateStr: string | null | undefined): string => {
  const date = parseSafeDate(dateStr);
  if (!date) return '--:--';
  
  const pad = (n: number) => String(n).padStart(2, '0');
  
  const day = pad(date.getDate());
  const month = pad(date.getMonth() + 1);
  const year = date.getFullYear();
  const hours = pad(date.getHours());
  const minutes = pad(date.getMinutes());
  
  return `${day}/${month}/${year} ${hours}:${minutes}`;
};

/**
 * Calcula minutos transcurridos desde una fecha hasta ahora
 */
export const getMinutesElapsed = (dateStr: string | null | undefined): number => {
  const date = parseSafeDate(dateStr);
  if (!date) return 0;
  
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  return Math.floor(diffMs / (1000 * 60));
};

/**
 * Formatea tiempo transcurrido (mm:ss o hh:mm)
 */
export const formatElapsed = (dateStr: string | null | undefined): string => {
  const date = parseSafeDate(dateStr);
  if (!date) return '0s';
  
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const totalSeconds = Math.floor(diffMs / 1000);
  
  if (totalSeconds < 0) return '0s';
  
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  } else if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  } else {
    return `${seconds}s`;
  }
};
