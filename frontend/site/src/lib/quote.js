const KEY = 'vicinic_quote_plan'

export function setQuotePlan(plan) {
  try {
    sessionStorage.setItem(KEY, plan)
  } catch {
    // storage unavailable — the form just opens without a preselected package
  }
  window.dispatchEvent(new CustomEvent('quote-plan', { detail: plan }))
}

export function getQuotePlan() {
  try {
    return sessionStorage.getItem(KEY) || ''
  } catch {
    return ''
  }
}
