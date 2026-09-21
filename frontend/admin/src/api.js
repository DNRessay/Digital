const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`))
  return match ? decodeURIComponent(match[1]) : null
}

async function apiFetch(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    ...options,
    headers: {
      ...(options.headers || {}),
      ...(options.method && options.method !== 'GET' ? { 'X-CSRFToken': getCookie('csrftoken') || '' } : {}),
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

export function loginUrl() {
  // Django admin's own login only honors a same-origin `next=` redirect
  // (its built-in open-redirect protection) — pointing it straight at
  // this app's URL (a different origin, Cloudflare Pages) gets silently
  // dropped, landing on the backend's own bare /admin/ index instead of
  // bouncing back here. Routing through admin-login-redirect/ (same
  // origin as the backend, so it passes that check) with the *real*
  // destination as `target` fixes that — see builder/views.admin_login_redirect.
  const target = encodeURIComponent(window.location.href)
  const next = encodeURIComponent(`${API_BASE}/admin-login-redirect/?target=${target}`)
  return `${API_BASE}/admin/login/?next=${next}`
}

export function whoami() {
  return apiFetch('/api/whoami/')
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
