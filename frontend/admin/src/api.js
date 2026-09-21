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
  // admin-login-redirect/ (not /admin/login/ directly) handles both
  // "already logged in" (Django's own admin login shortcuts straight to
  // /admin/ in that case, ignoring next= entirely — a redirect-safety
  // check can't fix that, it never even runs) and "needs to log in first"
  // — see builder/views.admin_login_redirect for why this extra hop
  // exists.
  const target = encodeURIComponent(window.location.href)
  return `${API_BASE}/admin-login-redirect/?target=${target}`
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
