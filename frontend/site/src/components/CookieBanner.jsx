import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CONSENT_EVENT, getConsent, setConsent } from '../lib/consent.js'
import '../styles/legal.css'

export default function CookieBanner() {
  const [open, setOpen] = useState(() => !getConsent())

  useEffect(() => {
    const onChange = (e) => setOpen(!e.detail)
    window.addEventListener(CONSENT_EVENT, onChange)
    return () => window.removeEventListener(CONSENT_EVENT, onChange)
  }, [])

  useEffect(() => {
    // Hold the page still until a choice is made.
    document.body.style.overflow = open ? 'hidden' : ''
    return () => {
      document.body.style.overflow = ''
    }
  }, [open])

  if (!open) return null

  return (
    <>
    <div className="cookie-backdrop" />
    <div className="cookie-banner" role="dialog" aria-modal="true" aria-label="Cookie consent">
      <div className="cookie-banner-text">
        <strong>We use cookies</strong>
        <p>
          We use cookies to give you a smooth, personalised experience and to keep improving Vicinic. Details are in our{' '}
          <Link to="/cookies">Cookie Policy</Link>.
        </p>
      </div>
      <div className="cookie-banner-actions">
        <button type="button" className="cookie-btn cookie-btn-secondary" onClick={() => setConsent('essential')}>
          Accept necessary
        </button>
        <button type="button" className="cookie-btn" onClick={() => setConsent('all')}>
          Accept all
        </button>
      </div>
    </div>
    </>
  )
}
