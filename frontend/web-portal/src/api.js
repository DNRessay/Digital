export const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
const TOKEN_KEY = 'vicinic_token'

// Bearer-token auth, not cookies: web-portal's backend is a different site
// from this app, and browsers increasingly block third-party cookies by
// default — a cross-site session cookie can silently never get set at all
// (the page still loads fine; only a later POST needing it fails). A token
// in localStorage + an explicit header sidesteps that entirely, and needs
// no CSRF dance since a cross-site page can't read or set this header.
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
  const isJsonBody = options.body !== undefined && typeof options.body !== 'string'
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
  return apiFetch('/api/customer/whoami/')
}

export async function login(username, password) {
  const data = await apiFetch('/api/customer/login/', { method: 'POST', body: { username, password } })
  setToken(data.token)
  return data
}

export function listPublicTemplates() {
  return apiFetch('/api/customer/templates/')
}

export async function register(name, username, email, password) {
  const data = await apiFetch('/api/customer/register/', { method: 'POST', body: { name, username, email, password } })
  setToken(data.token)
  return data
}

export function createSite(siteName, templateSlug) {
  return apiFetch('/api/customer/sites/', {
    method: 'POST',
    body: { site_name: siteName, template_slug: templateSlug },
  })
}

export async function logout() {
  try {
    await apiFetch('/api/customer/logout/', { method: 'POST' })
  } finally {
    setToken(null)
  }
}

export function listSites() {
  return apiFetch('/api/customer/sites/')
}

export function updateSite(siteSlug, fields) {
  return apiFetch(`/api/customer/sites/${siteSlug}/`, { method: 'PATCH', body: fields })
}

export function deleteSite(siteSlug) {
  return apiFetch(`/api/customer/sites/${siteSlug}/`, { method: 'DELETE' })
}

export function getSiteSlots(siteSlug) {
  return apiFetch(`/api/customer/sites/${siteSlug}/slots/`)
}

export function saveSiteSlots(siteSlug, values) {
  return apiFetch(`/api/customer/sites/${siteSlug}/slots/`, { method: 'POST', body: values })
}

// Edits made in the click-to-edit preview are cached here — per site,
// in this browser only — rather than saved as they happen; "Publish
// changes" is what actually sends them via saveSiteSlots above. Survives
// a reload so an in-progress edit isn't lost if the tab closes early.
function draftKey(siteSlug) {
  return `vicinic_draft_${siteSlug}`
}

export function loadDraft(siteSlug) {
  try {
    const raw = localStorage.getItem(draftKey(siteSlug))
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

export function storeDraft(siteSlug, values) {
  try {
    localStorage.setItem(draftKey(siteSlug), JSON.stringify(values))
  } catch {
    // Private browsing / storage disabled — edits just won't survive a reload.
  }
}

export function clearDraft(siteSlug) {
  try {
    localStorage.removeItem(draftKey(siteSlug))
  } catch {
    // Nothing to do — see storeDraft.
  }
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

export function getDomain(siteSlug) {
  return apiFetch(`/api/customer/sites/${siteSlug}/domain/`)
}

export function connectDomain(siteSlug, domain) {
  return apiFetch(`/api/customer/sites/${siteSlug}/domain/`, { method: 'POST', body: { domain } })
}

export function disconnectDomain(siteSlug) {
  return apiFetch(`/api/customer/sites/${siteSlug}/domain/`, { method: 'DELETE' })
}

export function checkDomainAvailability(siteSlug, domain) {
  return apiFetch(`/api/customer/sites/${siteSlug}/domain/check/?domain=${encodeURIComponent(domain)}`)
}

export function connectWhatsApp(siteSlug, wabaId, phoneNumberId) {
  return apiFetch(`/api/customer/sites/${siteSlug}/whatsapp/`, {
    method: 'POST',
    body: { waba_id: wabaId, phone_number_id: phoneNumberId },
  })
}

export function disconnectWhatsApp(siteSlug) {
  return apiFetch(`/api/customer/sites/${siteSlug}/whatsapp/`, { method: 'DELETE' })
}

export function purchaseDomain(siteSlug, domain, registrant, returnUrl, cancelUrl) {
  return apiFetch(`/api/customer/sites/${siteSlug}/domain/purchase/`, {
    method: 'POST',
    body: { domain, registrant, return_url: returnUrl, cancel_url: cancelUrl },
  })
}

export function listEmailRoutes(siteSlug) {
  return apiFetch(`/api/customer/sites/${siteSlug}/email-routes/`)
}

export function createEmailRoute(siteSlug, fromAddress, toAddress) {
  return apiFetch(`/api/customer/sites/${siteSlug}/email-routes/`, {
    method: 'POST',
    body: { from_address: fromAddress, to_address: toAddress },
  })
}

export function deleteEmailRoute(siteSlug, routeId) {
  return apiFetch(`/api/customer/sites/${siteSlug}/email-routes/${routeId}/`, { method: 'DELETE' })
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
