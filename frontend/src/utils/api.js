export const API_ORIGIN = window.location.origin
export const API_BASE = `${API_ORIGIN}/api`

export function toImageUrl(path) {
  if (!path) return ''
  if (/^https?:\/\//i.test(path)) return path
  const normalized = path.startsWith('/') ? path : `/${path}`
  return `${API_ORIGIN}${normalized}`
}

export function authHeaders() {
  const token = localStorage.getItem('auth_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export function authFetch(url, options = {}) {
  const headers = { ...options.headers, ...authHeaders() }
  const isFormData = options.body instanceof FormData
  if (!isFormData && (!options.headers || !options.headers['Content-Type'])) {
    headers['Content-Type'] = 'application/json'
  }
  return fetch(url, { ...options, headers })
}