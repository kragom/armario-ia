export const API_ORIGIN = `http://${window.location.hostname}:8000`
export const API_BASE = `${API_ORIGIN}/api`

export function toImageUrl(path) {
  if (!path) return ''
  if (/^https?:\/\//i.test(path)) return path
  const normalized = path.startsWith('/') ? path : `/${path}`
  return `${API_ORIGIN}${normalized}`
}
