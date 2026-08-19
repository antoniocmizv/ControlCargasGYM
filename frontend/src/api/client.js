const BASE_URL = import.meta.env.VITE_API_URL || '/api'

let onUnauthorized = null

/** El router registra aquí el "expulsar al login" para evitar un import circular. */
export function setUnauthorizedHandler(handler) {
  onUnauthorized = handler
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

function readToken() {
  return localStorage.getItem('cargas_token')
}

async function request(path, { method = 'GET', body, params, raw = false } = {}) {
  const url = new URL(`${BASE_URL}${path}`, window.location.origin)
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') url.searchParams.set(key, value)
  })

  const headers = {}
  const token = readToken()
  if (token) headers.Authorization = `Bearer ${token}`
  if (body !== undefined) headers['Content-Type'] = 'application/json'

  let response
  try {
    response = await fetch(url, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined
    })
  } catch {
    throw new ApiError('Sin conexión con el servidor', 0)
  }

  if (response.status === 401) {
    onUnauthorized?.()
    throw new ApiError('Tu sesión ha caducado, vuelve a entrar', 401)
  }

  if (!response.ok) {
    let detail = 'Algo ha fallado, inténtalo de nuevo'
    try {
      const data = await response.json()
      if (typeof data.detail === 'string') detail = data.detail
      else if (Array.isArray(data.detail)) detail = data.detail[0]?.msg || detail
    } catch {
      /* respuesta sin cuerpo JSON */
    }
    throw new ApiError(detail, response.status)
  }

  if (raw) return response
  if (response.status === 204) return null
  return response.json()
}

export const api = {
  get: (path, params) => request(path, { params }),
  post: (path, body, params) => request(path, { method: 'POST', body, params }),
  patch: (path, body) => request(path, { method: 'PATCH', body }),
  put: (path, body) => request(path, { method: 'PUT', body }),
  delete: (path) => request(path, { method: 'DELETE' }),
  download: (path, params) => request(path, { params, raw: true })
}
