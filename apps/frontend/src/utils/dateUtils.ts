/**
 * utilidades para manejo de fechas y horas en La Hidrocálida
 */

export const TIMEZONE = 'America/Mexico_City';

/**
 * Parsea una cadena de fecha de forma segura, manejando formatos ISO con espacios
 * Ej: "2026-02-05 22:10:23.245896+00" -> Date object
 */
export const parseSafeDate = (dateStr: any): Date | null => {
  if (!dateStr) return null;
  
  try {
    // Si la fecha ya es un objeto Date
    if (dateStr instanceof Date) return isNaN(dateStr.getTime()) ? null : dateStr;

    // Si es una cadena en formato YYYY-MM-DD (solo fecha), parsear localmente
    // para evitar el desplazamiento de zona horaria (UTC vs Local)
    if (typeof dateStr === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
      const [year, month, day] = dateStr.split('-').map(Number);
      return new Date(year, month - 1, day);
    }

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
 * Formatea una fecha a HH:mm en la zona horaria del restaurante (America/Mexico_City)
 */
export const formatTime = (dateStr: string | Date | null | undefined, options?: Intl.DateTimeFormatOptions): string => {
  const date = parseSafeDate(dateStr);
  if (!date) return '--:--';
  
  return date.toLocaleTimeString('es-MX', {
    timeZone: TIMEZONE,
    hour: '2-digit',
    minute: '2-digit',
    ...options
  });
};

/**
 * Formatea una fecha a DD/MM/YYYY HH:mm en la zona horaria del restaurante (America/Mexico_City)
 */
export const formatDateTime = (dateStr: string | Date | null | undefined): string => {
  const date = parseSafeDate(dateStr);
  if (!date) return '--:--';
  
  const formatter = new Intl.DateTimeFormat('es-MX', {
    timeZone: TIMEZONE,
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  });
  return formatter.format(date).replace(',', '');
};

/**
 * Formatea una fecha a formato corto con fecha y hora (ej: "26 ago, 12:15")
 */
export const formatDateTimeShort = (dateStr: string | Date | null | undefined): string => {
  const date = parseSafeDate(dateStr);
  if (!date) return '--:--';
  
  return date.toLocaleString('es-MX', {
    timeZone: TIMEZONE,
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

/**
 * Formatea una fecha a "DD MMM YYYY" (ej: "26 ago 2026")
 */
export const formatDate = (dateStr: string | Date | null | undefined): string => {
  const date = parseSafeDate(dateStr);
  if (!date) return '--/--/----';
  
  return date.toLocaleDateString('es-MX', {
    timeZone: TIMEZONE,
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  });
};

/**
 * Formatea una fecha a "Día, D de Mes" (ej: "miércoles, 26 de ago")
 */
export const formatDetailedDate = (dateStr: string | Date | null | undefined): string => {
  const date = parseSafeDate(dateStr);
  if (!date) return '';
  
  return date.toLocaleDateString('es-MX', {
    timeZone: TIMEZONE,
    weekday: 'long',
    day: 'numeric',
    month: 'short'
  });
};

/**
 * Calcula minutos transcurridos desde una fecha hasta ahora
 */
export const getMinutesElapsed = (dateStr: string | Date | null | undefined): number => {
  const date = parseSafeDate(dateStr);
  if (!date) return 0;
  
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  return Math.floor(diffMs / (1000 * 60));
};

/**
 * Formatea tiempo transcurrido (mm:ss o hh:mm)
 */
export const formatElapsed = (dateStr: string | Date | null | undefined): string => {
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

