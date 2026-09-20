const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`))
  return match ? decodeURIComponent(match[1]) : null
}

async function apiFetch(path, options = {}) {
  const isJsonBody = options.body !== undefined && typeof options.body !== 'string'
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    ...options,
    body: isJsonBody ? JSON.stringify(options.body) : options.body,
    headers: {
      ...(isJsonBody ? { 'Content-Type': 'application/json' } : {}),
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

export function whoami() {
  return apiFetch('/api/customer/whoami/')
}

export function login(username, password) {
  return apiFetch('/api/customer/login/', { method: 'POST', body: { username, password } })
}

export function listPublicTemplates() {
  return apiFetch('/api/customer/templates/')
}

export function register(username, password) {
  return apiFetch('/api/customer/register/', { method: 'POST', body: { username, password } })
}

export function createSite(siteName, templateSlug) {
  return apiFetch('/api/customer/sites/', {
    method: 'POST',
    body: { site_name: siteName, template_slug: templateSlug },
  })
}

export function logout() {
  return apiFetch('/api/customer/logout/', { method: 'POST' })
}

export function listSites() {
  return apiFetch('/api/customer/sites/')
}

export function getSiteSlots(siteSlug) {
  return apiFetch(`/api/customer/sites/${siteSlug}/slots/`)
}

export function saveSiteSlots(siteSlug, values) {
  return apiFetch(`/api/customer/sites/${siteSlug}/slots/`, { method: 'POST', body: values })
}

export function listPackages() {
  return apiFetch('/api/customer/packages/')
}

export function checkout(siteSlug, packageId, returnUrl, cancelUrl) {
  return apiFetch(`/api/customer/sites/${siteSlug}/checkout/`, {
    method: 'POST',
    body: { package: packageId, return_url: returnUrl, cancel_url: cancelUrl },
  })
}

// PayFast needs a real browser form POST (not fetch) to its hosted
// checkout page — build one on the fly, in the exact field order the
// backend signed, and submit it.
export function redirectToPayFast(processUrl, fields) {
  const form = document.createElement('form')
  form.method = 'POST'
  form.action = processUrl
  for (const { name, value } of fields) {
    const input = document.createElement('input')
    input.type = 'hidden'
    input.name = name
    input.value = value
    form.appendChild(input)
  }
  document.body.appendChild(form)
  form.submit()
}
