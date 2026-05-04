const API_BASE = import.meta.env.VITE_API_BASE ?? ''

const apiKey = import.meta.env.VITE_ECOEYE2_API_KEY ?? ''

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers)
  headers.set('Accept', 'application/json')
  if (apiKey) headers.set('X-Api-Key', apiKey)
  if (init?.body && !(init.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const j = await res.json()
      detail = (j as { detail?: string }).detail ?? JSON.stringify(j)
    } catch {
      /* ignore */
    }
    throw new Error(detail || `HTTP ${res.status}`)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}
