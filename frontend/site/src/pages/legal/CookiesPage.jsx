import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import LegalPage from './LegalPage.jsx'
import { CONSENT_EVENT, clearConsent, getConsent } from '../../lib/consent.js'

const LABELS = { all: 'All cookies accepted', essential: 'Necessary cookies only' }

export default function CookiesPage() {
  const [consent, setConsentState] = useState(getConsent)

  useEffect(() => {
    const onChange = (e) => setConsentState(e.detail)
    window.addEventListener(CONSENT_EVENT, onChange)
    return () => window.removeEventListener(CONSENT_EVENT, onChange)
  }, [])

  return (
    <LegalPage
      title="Cookie Policy"
      intro="Cookies and similar browser storage are small pieces of data saved on your device. This page explains which ones Vicinic uses and how to control them."
    >
      <h2>Your choice</h2>
      <p>
        Current setting: <strong>{LABELS[consent] || 'Not chosen yet'}</strong>.{' '}
        <button type="button" className="cookie-btn cookie-btn-inline" onClick={clearConsent}>
          Change my choice
        </button>
      </p>

      <h2>Essential (always on)</h2>
      <ul>
        <li>Your cookie choice, so we don't ask again on every page.</li>
        <li>Your sign-in on the customer portal, so you stay logged in.</li>
        <li>Security cookies set by Cloudflare to protect the site from bots and attacks.</li>
      </ul>

      <h2>Analytics (only if you accept)</h2>
      <p>
        With your permission we record which pages you visit, what you click, how you arrived and your device type, so
        we can see what's useful and improve Vicinic. We don't use this to identify you personally or sell it, and we
        don't use advertising cookies.
      </p>

      <h2>Managing cookies</h2>
      <p>
        You can change your choice at any time with the button above, or clear cookies in your browser settings.
        Blocking essential cookies may stop parts of the site, like signing in, from working.
      </p>

      <p>
        More detail on how we handle personal information is in our <Link to="/privacy">Privacy Policy</Link>.
      </p>
    </LegalPage>
  )
}
