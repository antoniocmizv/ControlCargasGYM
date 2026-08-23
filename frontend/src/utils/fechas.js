/**
 * Las fechas de sesión viajan como AAAA-MM-DD sin hora. `new Date('2026-08-20')`
 * las interpreta como UTC, así que al oeste de Greenwich se pintaba el día
 * anterior. Aquí se construyen siempre en hora local.
 */

const ISO = /^\d{4}-\d{2}-\d{2}$/

/** Fecha local a partir de AAAA-MM-DD, o null si la cadena no es válida. */
export function fechaLocal(iso) {
  if (typeof iso !== 'string' || !ISO.test(iso)) return null
  const [anio, mes, dia] = iso.split('-').map(Number)
  const fecha = new Date(anio, mes - 1, dia)
  // Descarta días imposibles (2026-02-31 desbordaría a marzo).
  const valida =
    fecha.getFullYear() === anio && fecha.getMonth() === mes - 1 && fecha.getDate() === dia
  return valida ? fecha : null
}

export const esFechaValida = (iso) => fechaLocal(iso) !== null

/** Hoy en AAAA-MM-DD local (sv-SE da justo ese formato). */
export const hoyIso = () => new Date().toLocaleDateString('sv-SE')

function formatea(iso, opciones, alternativa) {
  const fecha = fechaLocal(iso)
  return fecha ? fecha.toLocaleDateString('es-ES', opciones) : alternativa
}

export const fechaCorta = (iso) =>
  formatea(iso, { weekday: 'short', day: 'numeric', month: 'short' }, '—')

export const fechaLarga = (iso) =>
  formatea(iso, { weekday: 'long', day: 'numeric', month: 'long' }, 'Fecha no válida')

export const fechaNumerica = (iso) => formatea(iso, {}, '—')

export const diaMes = (iso) => formatea(iso, { day: 'numeric', month: 'short' }, '—')
