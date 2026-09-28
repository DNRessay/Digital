const KEY = 'vicinic_cookie_consent'
export const CONSENT_EVENT = 'vicinic:consent'

export function getConsent() {
  try {
    return localStorage.getItem(KEY)
  } catch {
    return null
  }
}

export function setConsent(value) {
  try {
    localStorage.setItem(KEY, value)
  } catch {
    // Storage blocked — the choice just won't be remembered.
  }
  window.dispatchEvent(new CustomEvent(CONSENT_EVENT, { detail: value }))
}

export function clearConsent() {
  try {
    localStorage.removeItem(KEY)
  } catch {
    // ignore
  }
  window.dispatchEvent(new CustomEvent(CONSENT_EVENT, { detail: null }))
}

// Analytics (pages visited, clicks) may only run once the visitor has accepted.
export function analyticsAllowed() {
  return getConsent() === 'all'
}
