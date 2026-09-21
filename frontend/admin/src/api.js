export const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
const TOKEN_KEY = 'vicinic_admin_token'

// Bearer-token auth, not cookies — see models.CustomerAuthToken's docstring
// for the full reasoning (this app hit it in practice: a same-origin login
// worked, but the SPA's own cross-origin whoami() fetch() came back
// unauthenticated because the session cookie never attached to it).
export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    // Private browsing / storage disabled — auth just won't persist across reloads.
  }
}

async function apiFetch(path, options = {}) {
  const isFormData = options.body instanceof FormData
  const isJsonBody = options.body !== undefined && !isFormData && typeof options.body !== 'string'
  const token = getToken()
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    body: isJsonBody ? JSON.stringify(options.body) : options.body,
    headers: {
      ...(isJsonBody ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Token ${token}` } : {}),
      ...(options.headers || {}),
    },
  })
  let data = null
  try {
    data = await res.json()
  } catch {
    // no body
  }
  if (!res.ok) {
    const error = new Error((data && data.error) || `Request failed (${res.status})`)
    error.status = res.status
    throw error
  }
  return data
}

export function whoami() {
  return apiFetch('/api/whoami/')
}

export async function login(username, password) {
  const data = await apiFetch('/api/admin/login/', { method: 'POST', body: { username, password } })
  setToken(data.token)
  return data
}

export async function logout() {
  try {
    await apiFetch('/api/admin/logout/', { method: 'POST' })
  } finally {
    setToken(null)
  }
}

export function listTemplates() {
  return apiFetch('/api/templates/')
}

export function uploadTemplate(name, zipFile) {
  const formData = new FormData()
  formData.append('name', name)
  formData.append('zip_file', zipFile)
  return apiFetch('/api/templates/', { method: 'POST', body: formData })
}
