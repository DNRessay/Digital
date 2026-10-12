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
  const isJsonBody = options.body !== undefined && typeof options.body !== 'string' && !(options.body instanceof FormData)
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

export async function register(name, username, email, password, acceptTerms) {
  const data = await apiFetch('/api/customer/register/', {
    method: 'POST',
    body: { name, username, email, password, accept_terms: acceptTerms },
  })
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

export function searchDomains(siteSlug, query) {
  return apiFetch(`/api/customer/sites/${siteSlug}/domain/search/?q=${encodeURIComponent(query)}`)
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

export function purchaseDomain(siteSlug, domain, returnUrl, cancelUrl) {
  return apiFetch(`/api/customer/sites/${siteSlug}/domain/purchase/`, {
    method: 'POST',
    body: { domain, return_url: returnUrl, cancel_url: cancelUrl },
  })
}

export function getProfile() {
  return apiFetch('/api/customer/profile/')
}

export function updateProfile(fields) {
  return apiFetch('/api/customer/profile/', { method: 'PATCH', body: fields })
}

export function getVisitors(siteSlug, days = 30) {
  return apiFetch(`/api/customer/sites/${siteSlug}/visitors/?days=${days}`)
}

export function listEmailDestinations(siteSlug) {
  return apiFetch(`/api/customer/sites/${siteSlug}/email-destinations/`)
}

export function addEmailDestination(siteSlug, email) {
  return apiFetch(`/api/customer/sites/${siteSlug}/email-destinations/`, { method: 'POST', body: { email } })
}

export function deleteEmailDestination(siteSlug, destinationId) {
  return apiFetch(`/api/customer/sites/${siteSlug}/email-destinations/${destinationId}/`, { method: 'DELETE' })
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

// Package checkout: Paystack returns a plain redirect_url, PayFast returns a
// form to POST (see redirectToPayFast).
export function redirectToCheckout(data) {
  if (data.redirect_url) {
    window.location.href = data.redirect_url
  } else {
    redirectToPayFast(data.process_url, data.fields)
  }
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

export function getSiteImages(siteSlug, page) {
  return apiFetch(`/api/customer/sites/${siteSlug}/images/?page=${encodeURIComponent(page)}`)
}

export function uploadSiteImage(siteSlug, original, file) {
  const form = new FormData()
  form.append('original', original)
  form.append('file', file)
  return apiFetch(`/api/customer/sites/${siteSlug}/images/`, { method: 'POST', body: form })
}

export function resetSiteImage(siteSlug, original) {
  return apiFetch(`/api/customer/sites/${siteSlug}/images/?original=${encodeURIComponent(original)}`, { method: 'DELETE' })
}

export function setLogoScale(siteSlug, logoScale) {
  return apiFetch(`/api/customer/sites/${siteSlug}/logo-scale/`, { method: 'POST', body: { logo_scale: logoScale } })
}

export function publishSiteImages(siteSlug) {
  return apiFetch(`/api/customer/sites/${siteSlug}/images/publish/`, { method: 'POST' })
}

export function discardSiteImages(siteSlug) {
  return apiFetch(`/api/customer/sites/${siteSlug}/images/discard/`, { method: 'POST' })
}

export function getSiteLinks(siteSlug, page) {
  return apiFetch(`/api/customer/sites/${siteSlug}/links/?page=${encodeURIComponent(page)}`)
}

export function setSiteLink(siteSlug, key, href) {
  return apiFetch(`/api/customer/sites/${siteSlug}/links/`, { method: 'POST', body: { key, href } })
}

export function getSiteMenu(siteSlug) {
  return apiFetch(`/api/customer/sites/${siteSlug}/menu/`)
}

export function saveSiteMenu(siteSlug, items) {
  return apiFetch(`/api/customer/sites/${siteSlug}/menu/`, { method: 'PUT', body: { items } })
}

export function resetSiteMenu(siteSlug) {
  return apiFetch(`/api/customer/sites/${siteSlug}/menu/`, { method: 'DELETE' })
}

export function getSitePages(siteSlug) {
  return apiFetch(`/api/customer/sites/${siteSlug}/pages/`)
}

export function createSitePage(siteSlug, title) {
  return apiFetch(`/api/customer/sites/${siteSlug}/pages/`, { method: 'POST', body: { title } })
}

export function updateSitePage(siteSlug, pageId, fields) {
  return apiFetch(`/api/customer/sites/${siteSlug}/pages/${pageId}/`, { method: 'PATCH', body: fields })
}

export function deleteSitePage(siteSlug, pageId) {
  return apiFetch(`/api/customer/sites/${siteSlug}/pages/${pageId}/`, { method: 'DELETE' })
}

export function getPageSections(siteSlug, pageId) {
  return apiFetch(`/api/customer/sites/${siteSlug}/pages/${pageId}/sections/`)
}

export function pageSectionAction(siteSlug, pageId, body) {
  return apiFetch(`/api/customer/sites/${siteSlug}/pages/${pageId}/sections/`, { method: 'POST', body })
}

export function uploadSectionImage(siteSlug, pageId, sectionId, field, file) {
  const form = new FormData()
  form.append('field', field)
  form.append('file', file)
  return apiFetch(`/api/customer/sites/${siteSlug}/pages/${pageId}/sections/${sectionId}/image/`, { method: 'POST', body: form })
}

export function getEnquiries(siteSlug, status) {
  const q = status ? `?status=${encodeURIComponent(status)}` : ''
  return apiFetch(`/api/customer/sites/${siteSlug}/enquiries/${q}`)
}

export function updateEnquiry(siteSlug, enquiryId, fields) {
  return apiFetch(`/api/customer/sites/${siteSlug}/enquiries/${enquiryId}/`, { method: 'PATCH', body: fields })
}

export function deleteEnquiry(siteSlug, enquiryId) {
  return apiFetch(`/api/customer/sites/${siteSlug}/enquiries/${enquiryId}/`, { method: 'DELETE' })
}

export function getStaff(siteSlug) {
  return apiFetch(`/api/customer/sites/${siteSlug}/staff/`)
}

export function addStaff(siteSlug, name, email, password) {
  return apiFetch(`/api/customer/sites/${siteSlug}/staff/`, { method: 'POST', body: { name, email, password } })
}

export function removeStaff(siteSlug, memberId) {
  return apiFetch(`/api/customer/sites/${siteSlug}/staff/${memberId}/`, { method: 'DELETE' })
}

export function getSiteBlog(siteSlug) {
  return apiFetch(`/api/customer/sites/${siteSlug}/blog/`)
}

export function updateSiteBlog(siteSlug, fields) {
  return apiFetch(`/api/customer/sites/${siteSlug}/blog/`, { method: 'PATCH', body: fields })
}

export function writeSitePost(siteSlug) {
  return apiFetch(`/api/customer/sites/${siteSlug}/blog/`, { method: 'POST' })
}

export function updateSitePost(siteSlug, postId, fields) {
  return apiFetch(`/api/customer/sites/${siteSlug}/blog/${postId}/`, { method: 'PATCH', body: fields })
}

export function deleteSitePost(siteSlug, postId) {
  return apiFetch(`/api/customer/sites/${siteSlug}/blog/${postId}/`, { method: 'DELETE' })
}

export function getStore(siteSlug) {
  return apiFetch(`/api/customer/sites/${siteSlug}/store/`)
}

export function addProduct(siteSlug, fields) {
  return apiFetch(`/api/customer/sites/${siteSlug}/store/`, { method: 'POST', body: fields })
}

export function setStorePayouts(siteSlug, merchantId) {
  return apiFetch(`/api/customer/sites/${siteSlug}/store/`, { method: 'PATCH', body: { payfast_merchant_id: merchantId } })
}

export function updateProduct(siteSlug, productId, fields) {
  return apiFetch(`/api/customer/sites/${siteSlug}/store/${productId}/`, { method: 'PATCH', body: fields })
}

export function deleteProduct(siteSlug, productId) {
  return apiFetch(`/api/customer/sites/${siteSlug}/store/${productId}/`, { method: 'DELETE' })
}

export function uploadProductImage(siteSlug, productId, file) {
  const form = new FormData()
  form.append('file', file)
  return apiFetch(`/api/customer/sites/${siteSlug}/store/${productId}/`, { method: 'POST', body: form })
}

export function getOrders(siteSlug) {
  return apiFetch(`/api/customer/sites/${siteSlug}/orders/`)
}

export function updateOrder(siteSlug, orderId, fields) {
  return apiFetch(`/api/customer/sites/${siteSlug}/orders/${orderId}/`, { method: 'PATCH', body: fields })
}
