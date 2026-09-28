import { useEffect, useRef, useState } from 'react'
import {
  API_BASE,
  checkout,
  clearDraft,
  connectDomain,
  connectWhatsApp,
  createEmailRoute,
  createSite,
  addEmailDestination,
  deleteEmailDestination,
  discardSiteImages,
  deleteEmailRoute,
  deleteSite,
  disconnectDomain,
  disconnectWhatsApp,
  getDomain,
  getProfile,
  getSiteImages,
  getSiteLinks,
  getSiteMenu,
  resetSiteMenu,
  saveSiteMenu,
  getSiteSlots,
  getVisitors,
  listEmailDestinations,
  listEmailRoutes,
  listPackages,
  listPublicTemplates,
  listSites,
  loadDraft,
  login,
  logout,
  publishSiteImages,
  purchaseDomain,
  redirectToPayFast,
  resetSiteImage,
  register,
  saveSiteSlots,
  searchDomains,
  setLogoScale,
  setSiteLink,
  storeDraft,
  updateProfile,
  updateSite,
  uploadSiteImage,
  whoami,
  createSitePage,
  deleteSitePage,
  getPageSections,
  getSitePages,
  pageSectionAction,
  updateSitePage,
  uploadSectionImage,
} from './api.js'

const WHATSAPP_APP_ID = import.meta.env.VITE_WHATSAPP_APP_ID || ''
const WHATSAPP_CONFIG_ID = import.meta.env.VITE_WHATSAPP_CONFIG_ID || ''
let fbSdkLoading = null

// Loads Meta's JS SDK once per page (not once per component mount — several
// DeployTab visits shouldn't inject the script tag repeatedly), and
// resolves once window.FB is actually ready to call.
function loadFacebookSdk() {
  if (window.FB) return Promise.resolve(window.FB)
  if (fbSdkLoading) return fbSdkLoading
  fbSdkLoading = new Promise((resolve) => {
    window.fbAsyncInit = function () {
      window.FB.init({ appId: WHATSAPP_APP_ID, xfbml: false, version: 'v21.0' })
      resolve(window.FB)
    }
    const script = document.createElement('script')
    script.src = 'https://connect.facebook.net/en_US/sdk.js'
    script.async = true
    script.defer = true
    document.body.appendChild(script)
  })
  return fbSdkLoading
}

// Tags whose text can never be wrapped for click-to-edit (a <title> or
// <option> can only ever hold plain text) — mirrors
// backend/builder/views.py's NON_INLINE_EDITABLE_TAGS/_slot_tag, both
// reading the same "<tagname> preview" prefix slot_extractor.py puts in
// every slot's label.
const NON_INLINE_TAGS = new Set(['title', 'option', 'textarea', 'noscript', '[document]'])

const DIAL_CODES = [
  { code: '27', label: '🇿🇦 +27' },
  { code: '264', label: '🇳🇦 +264' },
  { code: '267', label: '🇧🇼 +267' },
  { code: '263', label: '🇿🇼 +263' },
  { code: '258', label: '🇲🇿 +258' },
  { code: '266', label: '🇱🇸 +266' },
  { code: '268', label: '🇸🇿 +268' },
  { code: '260', label: '🇿🇲 +260' },
  { code: '265', label: '🇲🇼 +265' },
  { code: '254', label: '🇰🇪 +254' },
  { code: '234', label: '🇳🇬 +234' },
  { code: '233', label: '🇬🇭 +233' },
  { code: '44', label: '🇬🇧 +44' },
  { code: '1', label: '🇺🇸 +1' },
  { code: '61', label: '🇦🇺 +61' },
  { code: '971', label: '🇦🇪 +971' },
]

function splitPhone(value) {
  const digits = (value || '').replace(/\D/g, '')
  if (!digits) return { code: '27', local: '' }
  if (digits.startsWith('0')) return { code: '27', local: digits.slice(1) }
  const match = [...DIAL_CODES].sort((a, b) => b.code.length - a.code.length).find((d) => digits.startsWith(d.code))
  return match ? { code: match.code, local: digits.slice(match.code.length) } : { code: '27', local: digits }
}

// Country-code picker (South Africa by default) + local number. Calls
// onChange with the full international number, e.g. "+27821234567".
function PhoneInput({ id, value, onChange, disabled, required }) {
  const initial = splitPhone(value)
  const [code, setCode] = useState(initial.code)
  const local = splitPhone(value).code === code ? splitPhone(value).local : initial.local

  function emit(nextCode, nextLocal) {
    const digits = nextLocal.replace(/\D/g, '').replace(/^0+/, '')
    onChange(digits ? `+${nextCode}${digits}` : '')
  }

  return (
    <div className="phone-input">
      <select
        aria-label="Country code"
        value={code}
        disabled={disabled}
        onChange={(e) => {
          setCode(e.target.value)
          emit(e.target.value, local)
        }}
      >
        {DIAL_CODES.map((d) => <option key={d.code} value={d.code}>{d.label}</option>)}
      </select>
      <input
        id={id}
        type="text"
        inputMode="tel"
        placeholder="82 123 4567"
        value={local}
        disabled={disabled}
        required={required}
        onChange={(e) => emit(code, e.target.value)}
      />
    </div>
  )
}

function slotTag(label) {
  if (label.startsWith('<')) {
    const end = label.indexOf('>')
    if (end !== -1) return label.slice(1, end)
  }
  return ''
}

function Login({ onLoggedIn, onSwitchToRegister }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await login(username, password)
      onLoggedIn()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="page login-prompt">
      <form className="card" onSubmit={handleSubmit}>
        <img src="/logo.png" alt="Vicinic" className="brand-logo" />
        <h1>Edit your site</h1>
        <p>Sign in to edit your site's text.</p>
        {error && <div className="error">{error}</div>}
        <label htmlFor="username">Username</label>
        <input id="username" type="text" value={username} onChange={(e) => setUsername(e.target.value)} required autoComplete="username" />
        <label htmlFor="password">Password</label>
        <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" />
        <button type="submit" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
        <p className="switch-auth-mode">
          New here? <button type="button" className="link-button" onClick={onSwitchToRegister}>Create an account</button>
        </p>
      </form>
    </div>
  )
}

function Register({ onRegistered, onSwitchToLogin }) {
  const [name, setName] = useState('')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await register(name, username, email, password)
      onRegistered()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="page login-prompt">
      <form className="card" onSubmit={handleSubmit}>
        <img src="/logo.png" alt="Vicinic" className="brand-logo" />
        <h1>Create an account</h1>
        <p>Once you're signed in you can set up your site.</p>
        {error && <div className="error">{error}</div>}
        <label htmlFor="register-name">Full name</label>
        <input id="register-name" type="text" value={name} onChange={(e) => setName(e.target.value)} required autoComplete="name" />
        <label htmlFor="register-username">Username</label>
        <input id="register-username" type="text" value={username} onChange={(e) => setUsername(e.target.value)} required autoComplete="username" />
        <label htmlFor="register-email">Email</label>
        <input id="register-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
        <label htmlFor="register-password">Password</label>
        <input id="register-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="new-password" />
        <button type="submit" disabled={busy}>{busy ? 'Creating account…' : 'Create account'}</button>
        <p className="switch-auth-mode">
          Already have an account? <button type="button" className="link-button" onClick={onSwitchToLogin}>Sign in</button>
        </p>
      </form>
    </div>
  )
}

function CreateSite({ onCreated }) {
  const [templates, setTemplates] = useState(null)
  const [templatesError, setTemplatesError] = useState(null)
  const [siteName, setSiteName] = useState('')
  const [templateSlug, setTemplateSlug] = useState('')
  const [step, setStep] = useState('name') // name | template
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    listPublicTemplates()
      .then((data) => {
        setTemplates(data.templates)
        if (data.templates.length > 0) setTemplateSlug(data.templates[0].slug)
      })
      .catch((err) => setTemplatesError(err.message))
  }, [])

  async function handleSubmit(e) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await createSite(siteName, templateSlug)
      onCreated()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const noTemplates = templates && templates.length === 0

  if (step === 'name') {
    return (
      <form
        className="card"
        onSubmit={(e) => {
          e.preventDefault()
          setStep('template')
        }}
      >
        <h2>Create your site</h2>
        <p>First, what's your business called?</p>
        <label htmlFor="site-name">Site name</label>
        <input id="site-name" type="text" value={siteName} onChange={(e) => setSiteName(e.target.value)} autoFocus required />
        <button type="submit" disabled={!siteName.trim()}>Next</button>
      </form>
    )
  }

  return (
    <form className="card" onSubmit={handleSubmit}>
      <button type="button" className="link-button" onClick={() => setStep('name')}>← Back</button>
      <h2>Pick a look for {siteName.trim()}</h2>
      <p>Swipe through the templates — every bit of text is yours to edit once it's set up.</p>
      {error && <div className="error">{error}</div>}
      {templatesError && <div className="error">Could not load templates: {templatesError}</div>}
      {noTemplates && <div className="error">No templates are available yet — check back soon.</div>}
      {!templates && !templatesError && <p className="field-hint">Loading templates…</p>}

      {templates && templates.length > 0 && (
        <div className="template-carousel" role="radiogroup" aria-label="Templates">
          {templates.map((t) => (
            <button
              key={t.slug}
              type="button"
              role="radio"
              aria-checked={templateSlug === t.slug}
              className={`template-card${templateSlug === t.slug ? ' selected' : ''}`}
              onClick={() => setTemplateSlug(t.slug)}
            >
              <div className="template-preview">
                <iframe src={`${API_BASE}/template-preview/${t.slug}/`} title={`${t.name} preview`} loading="lazy" tabIndex={-1} />
              </div>
              <span className="template-name">{t.name}</span>
            </button>
          ))}
        </div>
      )}

      <button type="submit" disabled={busy || noTemplates || !templateSlug}>
        {busy ? 'Creating your site…' : 'Create site'}
      </button>
    </form>
  )
}

function SitePicker({ sites, selected, onSelect }) {
  if (sites.length <= 1) return null
  return (
    <div className="card site-picker">
      <label htmlFor="site">Site</label>
      <select id="site" value={selected} onChange={(e) => onSelect(e.target.value)}>
        {sites.map((s) => (
          <option key={s.slug} value={s.slug}>{s.name}</option>
        ))}
      </select>
    </div>
  )
}

function UpgradeCard({ site }) {
  const [packages, setPackages] = useState(null)
  const [packagesError, setPackagesError] = useState(null)
  const [packageId, setPackageId] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    listPackages()
      .then((data) => {
        setPackages(data.packages)
        if (data.packages.length > 0) setPackageId(data.packages[0].id)
      })
      .catch((err) => setPackagesError(err.message))
  }, [])

  async function handleSubscribe(e) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const base = `${window.location.origin}${window.location.pathname}`
      const data = await checkout(site.slug, packageId, `${base}?checkout=success`, `${base}?checkout=cancelled`)
      redirectToPayFast(data.process_url, data.fields)
      // Browser is navigating away to PayFast now — nothing else to do.
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  if (site.subscription_status === 'active') {
    const activePackage = packages?.find((p) => p.id === site.package)
    return (
      <div className="card upgrade-card">
        <h2>Plan</h2>
        <p>
          You're on the <strong>{activePackage ? activePackage.label : site.package}</strong> plan — no
          "Powered by Vicinic" credit is shown on your site.
        </p>
      </div>
    )
  }

  return (
    <form className="card upgrade-card" onSubmit={handleSubscribe}>
      <h2>Remove the "Powered by Vicinic" credit</h2>
      <p>Your site currently shows a small credit linking back to us. Pick a plan below to remove it.</p>
      {site.subscription_status === 'pending' && (
        <div className="notice">Payment pending — this can take a minute to confirm after you pay.</div>
      )}
      {error && <div className="error">{error}</div>}
      {packagesError && <div className="error">Could not load packages: {packagesError}</div>}

      <label htmlFor="package">Package</label>
      <select id="package" value={packageId} onChange={(e) => setPackageId(e.target.value)} disabled={!packages}>
        {!packages && <option value="">Loading…</option>}
        {packages && packages.map((p) => (
          <option key={p.id} value={p.id}>
            {p.once_off ? `${p.label} — R${p.setup} once-off, yours forever` : `${p.label} — R${p.monthly}/month (R${p.setup} once-off setup)`}
          </option>
        ))}
      </select>

      <button type="submit" disabled={busy || !packageId}>
        {busy ? 'Redirecting to PayFast…' : 'Pay with PayFast'}
      </button>
    </form>
  )
}

function DomainOption({ option, onBuy }) {
  return (
    <li className={`domain-option${option.recommended ? ' recommended' : ''}`}>
      <div>
        <strong>{option.domain}</strong>
        {option.recommended && <span className="domain-badge">Recommended</span>}
        {option.manual && <span className="field-hint domain-manual">Registered by our team within a business day</span>}
      </div>
      <div className="domain-option-buy">
        {option.included ? (
          <span className="domain-price domain-included">Included</span>
        ) : (
          <span className="domain-price">R{option.price_zar}<small>/yr</small></span>
        )}
        <button type="button" onClick={() => onBuy(option)}>{option.included ? 'Claim' : 'Buy'}</button>
      </div>
    </li>
  )
}

function DomainSearchSheet({ site, onClose, onSiteUpdated, onGoToProfile }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [searching, setSearching] = useState(false)
  const [selected, setSelected] = useState(null)
  const [profile, setProfile] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [claimed, setClaimed] = useState(null)

  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [onClose])

  useEffect(() => {
    getProfile().then((data) => setProfile(data.profile)).catch(() => {})
  }, [])

  async function handleSearch(e) {
    e.preventDefault()
    setSearching(true)
    setError(null)
    setResults(null)
    setSelected(null)
    try {
      setResults(await searchDomains(site.slug, query.trim()))
    } catch (err) {
      setError(err.message)
    } finally {
      setSearching(false)
    }
  }

  async function handleBuy(e) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const base = `${window.location.origin}${window.location.pathname}`
      const data = await purchaseDomain(
        site.slug,
        selected.domain,
        `${base}?checkout=success`,
        `${base}?checkout=cancelled`
      )
      if (data.included) {
        setClaimed(selected.domain)
        setBusy(false)
        onSiteUpdated(data.site)
        return
      }
      redirectToPayFast(data.process_url, data.fields)
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  const nothingFound = results && !results.searched && !results.recommended && results.options.length === 0

  return (
    <div className="sheet-backdrop" onClick={onClose}>
      <div className="sheet" role="dialog" aria-modal="true" aria-label="Find a domain" onClick={(e) => e.stopPropagation()}>
        <div className="sheet-header">
          {selected ? (
            <button type="button" className="link-button" onClick={() => setSelected(null)}>← Back to results</button>
          ) : (
            <h2>Find a domain</h2>
          )}
          <button type="button" className="sheet-close" onClick={onClose} aria-label="Close">×</button>
        </div>

        <div className="sheet-body">
          {error && <div className="error">{error}</div>}

          {claimed && (
            <div className="notice">
              <strong>{claimed}</strong> is yours — it's included with your plan. Our team registers it within one
              business day and your site switches over automatically once it's live.
            </div>
          )}

          {!selected && !claimed && site.free_domain_available && (
            <p className="field-hint">Your plan includes one free .co.za — search for the name you want.</p>
          )}

          {!selected && !claimed && (
            <>
              <form onSubmit={handleSearch} className="domain-search-form">
                <input
                  type="text"
                  placeholder="mybusiness"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  disabled={searching}
                  autoFocus
                  aria-label="Name to search"
                  required
                />
                <button type="submit" disabled={searching || !query.trim()}>
                  {searching ? 'Searching…' : 'Search'}
                </button>
              </form>

              {searching && <p className="field-hint">Checking every extension…</p>}

              {results && (
                <>
                  {results.searched && (
                    <ul className="domain-list">
                      <DomainOption option={results.searched} onBuy={setSelected} />
                    </ul>
                  )}
                  {results.searched_taken && (
                    <div className="notice"><strong>{results.searched_domain}</strong> is already taken.</div>
                  )}
                  {results.searched_domain && !results.searched && !results.searched_taken && (
                    <div className="notice">We couldn't check <strong>{results.searched_domain}</strong> right now.</div>
                  )}
                  {results.recommended && (
                    <ul className="domain-list">
                      <DomainOption option={results.recommended} onBuy={setSelected} />
                    </ul>
                  )}
                  {results.recommended_taken && (
                    <div className="notice"><strong>{results.name}.co.za</strong> is already taken.</div>
                  )}
                  {results.options.length > 0 && (
                    <>
                      <h3 className="domain-list-title">Other available options</h3>
                      <ul className="domain-list">
                        {results.options.map((o) => <DomainOption key={o.domain} option={o} onBuy={setSelected} />)}
                      </ul>
                    </>
                  )}
                  {nothingFound && <div className="notice">Nothing available for "{results.name}". Try another name.</div>}
                  {results.partial && <p className="field-hint">Some extensions couldn't be checked right now.</p>}
                </>
              )}
            </>
          )}

          {selected && !claimed && (
            <form onSubmit={handleBuy}>
              <p>
                <strong>{selected.domain}</strong> —{' '}
                {selected.included ? 'included with your plan.' : `R${selected.price_zar} for the first year.`}
              </p>
              {selected.manual && (
                <p className="field-hint">
                  Our team registers this one by hand, usually within one business day of payment. Your site switches over
                  automatically once it's live.
                </p>
              )}
              {profile && !profile.complete ? (
                <div className="notice">
                  Domain registries need the legal owner's contact details. Complete your details on the Profile tab
                  first — you only do this once.{' '}
                  <button type="button" className="link-button" onClick={onGoToProfile}>Complete my profile</button>
                </div>
              ) : (
                profile && (
                  <p className="field-hint">
                    Registered to <strong>{profile.legal_name}</strong> ({profile.email}) — from your Profile.{' '}
                    <button type="button" className="link-button" onClick={onGoToProfile}>Edit</button>
                  </p>
                )
              )}
              <button type="submit" disabled={busy || !profile || !profile.complete}>
                {busy
                  ? selected.included ? 'Claiming…' : 'Redirecting to PayFast…'
                  : selected.included ? `Claim ${selected.domain}` : `Pay R${selected.price_zar} with PayFast`}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}

function DomainSection({ site, onSiteUpdated, onGoToProfile, onOpenSearch }) {
  const [domainInput, setDomainInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  // While a domain is waiting on the customer's nameserver change to
  // land, poll Cloudflare (via our own backend) every so often so this
  // flips to "Active" without the customer having to refresh by hand.
  useEffect(() => {
    if (site.domain_status !== 'pending') return
    const id = setInterval(() => {
      getDomain(site.slug).then((data) => onSiteUpdated(data.site)).catch(() => {})
    }, 15000)
    return () => clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [site.slug, site.domain_status])

  async function handleConnect(e) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const data = await connectDomain(site.slug, domainInput.trim())
      onSiteUpdated(data.site)
      setDomainInput('')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function handleDisconnect() {
    setBusy(true)
    setError(null)
    try {
      const data = await disconnectDomain(site.slug)
      onSiteUpdated(data.site)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const hasDomain = site.custom_domain && site.domain_status !== 'none'

  return (
    <div className="card">
      <h2>Custom domain</h2>
      {error && <div className="error">{error}</div>}

      {!hasDomain ? (
        <>
          {site.free_domain_available && (
            <div className="notice">Your plan includes a free .co.za domain. Claim it below.</div>
          )}
          <button type="button" className="buy-domain-button" onClick={onOpenSearch}>
            {site.free_domain_available ? 'Claim your free .co.za' : 'Buy a new domain'}
          </button>
          <p className="field-hint domain-or">or connect one you already own:</p>
          <form onSubmit={handleConnect}>
            <label htmlFor="domain">Your domain</label>
            <input
              id="domain"
              type="text"
              placeholder="mybusiness.com"
              value={domainInput}
              onChange={(e) => setDomainInput(e.target.value)}
              disabled={busy}
              required
            />
            <button type="submit" disabled={busy || !domainInput.trim()}>
              {busy ? 'Connecting…' : 'Connect domain'}
            </button>
          </form>
        </>
      ) : (
        <>
          <p>
            <strong>{site.custom_domain}</strong>
            {' — '}
            {site.domain_status === 'active' && <span className="save-status">Active</span>}
            {site.domain_status === 'pending' && 'waiting for nameservers to update'}
            {site.domain_status === 'error' && <span className="error">Something went wrong connecting this domain</span>}
          </p>
          {site.domain_status === 'pending' && site.cloudflare_nameservers.length > 0 && (
            <div className="notice">
              At your domain registrar, set your nameservers to:
              <ul>
                {site.cloudflare_nameservers.map((ns) => <li key={ns}><code>{ns}</code></li>)}
              </ul>
              This can take anywhere from a few minutes to a few hours.
            </div>
          )}
          <button type="button" className="link-button" onClick={handleDisconnect} disabled={busy}>
            {busy ? 'Removing…' : 'Disconnect domain'}
          </button>
        </>
      )}
    </div>
  )
}

function EmailInboxes({ site, destinations, setDestinations }) {
  const [email, setEmail] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  async function refresh() {
    try {
      setDestinations((await listEmailDestinations(site.slug)).destinations)
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleAdd(e) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await addEmailDestination(site.slug, email.trim())
      setEmail('')
      await refresh()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function handleDelete(id) {
    setBusy(true)
    setError(null)
    try {
      await deleteEmailDestination(site.slug, id)
      await refresh()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const hasPending = destinations.some((d) => !d.verified)

  return (
    <div className="email-inboxes">
      <h3 className="domain-list-title">Your inboxes</h3>
      <p className="field-hint">
        Where forwarded mail can go. Each inbox gets a one-time confirmation email (sent by Cloudflare, our email partner) —
        click its link, then tap Refresh.
      </p>
      {error && <div className="error">{error}</div>}
      {destinations.length > 0 && (
        <ul className="email-route-list">
          {destinations.map((d) => (
            <li key={d.id}>
              <span>{d.email}</span>
              <span className={d.verified ? 'save-status' : 'field-hint'}>{d.verified ? 'Verified' : 'Check your inbox'}</span>
              <button type="button" className="link-button" onClick={() => handleDelete(d.id)} disabled={busy}>
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}
      {hasPending && (
        <button type="button" className="link-button" onClick={refresh} disabled={busy}>Refresh</button>
      )}
      <form onSubmit={handleAdd} className="domain-search-form">
        <input
          type="email"
          placeholder="you@gmail.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={busy}
          aria-label="Inbox to add"
          required
        />
        <button type="submit" disabled={busy || !email.trim()}>{busy ? 'Adding…' : 'Add inbox'}</button>
      </form>
    </div>
  )
}

function EmailRoutingSection({ site, onOpenSearch }) {
  const domainReady = site.domain_status === 'active'
  const [routes, setRoutes] = useState(null)
  const [externalRoutes, setExternalRoutes] = useState([])
  const [destinations, setDestinations] = useState([])
  const [error, setError] = useState(null)
  const [fromLocal, setFromLocal] = useState('')
  const [toAddress, setToAddress] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    listEmailDestinations(site.slug)
      .then((data) => setDestinations(data.destinations))
      .catch((err) => setError(err.message))
  }, [site.slug])

  useEffect(() => {
    if (!domainReady) {
      setRoutes([])
      setExternalRoutes([])
      return
    }
    listEmailRoutes(site.slug)
      .then((data) => {
        setRoutes(data.email_routes)
        setExternalRoutes(data.external_routes || [])
      })
      .catch((err) => setError(err.message))
  }, [site.slug, domainReady])

  const verified = destinations.filter((d) => d.verified)
  const disabled = !domainReady || verified.length === 0
  const available = site.ai_assistant_available && domainReady

  async function handleAdd(e) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const fromAddress = `${fromLocal.trim()}@${site.custom_domain}`
      const data = await createEmailRoute(site.slug, fromAddress, toAddress)
      setRoutes((prev) => [...(prev || []), data.route])
      setFromLocal('')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function handleDelete(routeId) {
    setBusy(true)
    setError(null)
    try {
      await deleteEmailRoute(site.slug, routeId)
      setRoutes((prev) => prev.filter((r) => r.id !== routeId))
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="card">
      <h2>Email routing</h2>
      {!available && (
        <div className="notice">
          {!site.ai_assistant_available
            ? 'Email forwarding (e.g. hello@yourbusiness.co.za to your Gmail) comes with every paid plan and your own domain — upgrade above to set it up.'
            : site.free_domain_available
              ? 'Email forwarding needs your own domain — and your plan includes a free .co.za.'
              : 'Email forwarding switches on once your custom domain above is connected and active.'}
          {site.ai_assistant_available && site.free_domain_available && !site.custom_domain && (
            <>
              {' '}
              <button type="button" className="link-button" onClick={onOpenSearch}>Claim your free .co.za</button>
            </>
          )}
        </div>
      )}
      {error && available && <div className="error">{error}</div>}

      <fieldset className={available ? 'plain-fieldset' : 'plain-fieldset locked-section'} disabled={!available}>
      <EmailInboxes site={site} destinations={destinations} setDestinations={setDestinations} />

      <h3 className="domain-list-title">Forwarding rules</h3>
      {available && verified.length === 0 && <p className="notice">Verify at least one inbox above first.</p>}

      <form onSubmit={handleAdd} className="email-route-form">
        <label htmlFor="route-from">Forward mail sent to</label>
        <div className="email-route-from">
          <input
            id="route-from"
            type="text"
            placeholder="hello"
            value={fromLocal}
            onChange={(e) => setFromLocal(e.target.value)}
            disabled={disabled || busy}
            required
          />
          <span>@{site.custom_domain || 'yourdomain.com'}</span>
        </div>
        <label htmlFor="route-to">to</label>
        <select id="route-to" value={toAddress} onChange={(e) => setToAddress(e.target.value)} disabled={disabled || busy} required>
          <option value="">Choose a verified inbox</option>
          {verified.map((d) => <option key={d.id} value={d.email}>{d.email}</option>)}
        </select>
        <button type="submit" disabled={disabled || busy || !fromLocal.trim() || !toAddress}>
          {busy ? 'Adding…' : 'Add forwarding rule'}
        </button>
      </form>

      {routes && routes.length > 0 && (
        <ul className="email-route-list">
          {routes.map((r) => (
            <li key={r.id}>
              <span>{r.from_address} → {r.to_address}</span>
              <span className={r.status === 'active' ? 'save-status' : r.status === 'error' ? 'error' : ''}>
                {r.status === 'active' && 'Active'}
                {r.status === 'pending_verification' && 'Waiting on inbox verification'}
                {r.status === 'error' && (r.error_message || 'Error')}
              </span>
              <button type="button" className="link-button" onClick={() => handleDelete(r.id)} disabled={busy}>
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}

      {externalRoutes.length > 0 && (
        <div className="external-routes">
          <p className="field-hint">Already forwarding on this domain:</p>
          <ul className="email-route-list">
            {externalRoutes.map((r) => (
              <li key={r.id}>
                <span>{r.from_address} → {r.to_address}</span>
                <span className={r.enabled ? 'save-status' : ''}>{r.enabled ? 'Active' : 'Paused'}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      </fieldset>
    </div>
  )
}

function AiAssistantSection({ site, onSiteUpdated }) {
  const [form, setForm] = useState(() => ({
    ai_assistant_enabled: site.ai_assistant_enabled,
    ai_assistant_description: site.ai_assistant_description,
    whatsapp_number: site.whatsapp_number,
  }))
  const [saveState, setSaveState] = useState('idle') // idle | saving | saved | error
  const [saveError, setSaveError] = useState(null)

  useEffect(() => {
    setForm({
      ai_assistant_enabled: site.ai_assistant_enabled,
      ai_assistant_description: site.ai_assistant_description,
      whatsapp_number: site.whatsapp_number,
    })
    setSaveState('idle')
  }, [site.slug])

  function setField(key, value) {
    setForm((prev) => ({ ...prev, [key]: value }))
    setSaveState('idle')
  }

  async function handleSave(e) {
    e.preventDefault()
    setSaveState('saving')
    setSaveError(null)
    try {
      const data = await updateSite(site.slug, form)
      onSiteUpdated(data.site)
      setSaveState('saved')
    } catch (err) {
      setSaveError(err.message)
      setSaveState('error')
    }
  }

  return (
    <form className="card" onSubmit={handleSave}>
      <h2>WhatsApp &amp; AI assistant</h2>
      <p>
        Adds an AI chat bubble to your site that answers simple visitor questions using the description
        below, plus a "Chat on WhatsApp" link if you add a number.
      </p>
      {!site.ai_assistant_available && (
        <div className="notice">The AI assistant comes with every paid plan — upgrade above to switch it on.</div>
      )}
      {saveError && <div className="error">{saveError}</div>}

      <label htmlFor="ai-whatsapp">WhatsApp number</label>
      <PhoneInput id="ai-whatsapp" value={form.whatsapp_number} onChange={(v) => setField('whatsapp_number', v)} />
      <p className="field-hint">Same number shown on the Overview tab — changing it here updates both.</p>

      <label htmlFor="ai-description">Describe your business</label>
      <textarea
        id="ai-description"
        rows={4}
        maxLength={2000}
        placeholder="What you sell or do, hours, what makes you different — whatever a customer would want to know."
        value={form.ai_assistant_description}
        onChange={(e) => setField('ai_assistant_description', e.target.value)}
      />

      <label htmlFor="ai-business-name">Business name</label>
      <input id="ai-business-name" type="text" value={site.name} disabled />
      <p className="field-hint">Set once when you created the site — used as-is by the assistant.</p>

      <label htmlFor="ai-enabled" className="checkbox-label">
        <input
          id="ai-enabled"
          type="checkbox"
          disabled={!site.ai_assistant_available}
          checked={site.ai_assistant_available && form.ai_assistant_enabled}
          onChange={(e) => setField('ai_assistant_enabled', e.target.checked)}
          style={{ marginRight: '8px' }}
        />
        Show the AI chat assistant on my site
      </label>

      <div className="save-bar">
        <button type="submit" disabled={saveState === 'saving'}>
          {saveState === 'saving' ? 'Saving…' : 'Save'}
        </button>
        {saveState === 'saved' && <span className="save-status">Saved</span>}
      </div>
    </form>
  )
}

function WhatsAppConnectSection({ site, onSiteUpdated }) {
  const [state, setState] = useState('idle') // idle | connecting | error
  const [error, setError] = useState(null)

  useEffect(() => {
    function handleMessage(event) {
      if (event.origin !== 'https://www.facebook.com' && event.origin !== 'https://web.facebook.com') return
      let data
      try {
        data = JSON.parse(event.data)
      } catch {
        return // Meta posts some non-JSON messages too — not ours to handle.
      }
      if (data.type !== 'WA_EMBEDDED_SIGNUP') return
      if (data.event === 'FINISH' || data.event === 'FINISH_ONLY_WABA') {
        const { waba_id: wabaId, phone_number_id: phoneNumberId } = data.data || {}
        if (!wabaId || !phoneNumberId) {
          setError("Facebook didn't return a phone number — try again.")
          setState('error')
          return
        }
        setState('connecting')
        connectWhatsApp(site.slug, wabaId, phoneNumberId)
          .then((res) => {
            onSiteUpdated(res.site)
            setState('idle')
          })
          .catch((err) => {
            setError(err.message)
            setState('error')
          })
      } else if (data.event === 'CANCEL' || data.event === 'ERROR') {
        setError(data.data?.error_message || 'Connection cancelled.')
        setState('error')
      }
    }
    window.addEventListener('message', handleMessage)
    return () => window.removeEventListener('message', handleMessage)
  }, [site.slug, onSiteUpdated])

  async function handleConnect() {
    setError(null)
    if (!WHATSAPP_APP_ID || !WHATSAPP_CONFIG_ID) {
      setError('WhatsApp connect is not configured yet.')
      setState('error')
      return
    }
    setState('connecting')
    const FB = await loadFacebookSdk()
    FB.login(
      () => {
        // The real result arrives via the WA_EMBEDDED_SIGNUP postMessage
        // listener above, not this callback — this just fires when the
        // popup itself closes, success or not.
        setState((s) => (s === 'connecting' ? 'idle' : s))
      },
      {
        config_id: WHATSAPP_CONFIG_ID,
        response_type: 'code',
        override_default_response_type: true,
        extras: { feature: 'whatsapp_embedded_signup', sessionInfoVersion: '3' },
      },
    )
  }

  async function handleDisconnect() {
    setState('connecting')
    try {
      const res = await disconnectWhatsApp(site.slug)
      onSiteUpdated(res.site)
      setState('idle')
    } catch (err) {
      setError(err.message)
      setState('error')
    }
  }

  return (
    <div className={`card${!site.whatsapp_bot_available && !site.whatsapp_connected ? ' locked-card' : ''}`}>
      <h2>Connect your own WhatsApp number</h2>
      <p>
        The AI assistant above answers on your site and via a wa.me link. Connecting your own number here goes
        further — a real WhatsApp Business number that replies automatically using the same description, in
        WhatsApp itself.
      </p>
      {!site.whatsapp_bot_available && !site.whatsapp_connected && (
        <div className="notice">The WhatsApp AI bot comes with Growth Hub and Business OS — upgrade above to connect your number.</div>
      )}
      {error && <div className="error">{error}</div>}
      {site.whatsapp_connected ? (
        <>
          <p className="save-status">Connected</p>
          <button type="button" onClick={handleDisconnect} disabled={state === 'connecting'}>
            {state === 'connecting' ? 'Disconnecting…' : 'Disconnect'}
          </button>
        </>
      ) : (
        <button type="button" onClick={handleConnect} disabled={state === 'connecting' || !site.whatsapp_bot_available}>
          {state === 'connecting' ? 'Connecting…' : 'Connect your WhatsApp number'}
        </button>
      )}
    </div>
  )
}

function DeployTab({ site, onSiteUpdated, onGoToProfile }) {
  const [showSearch, setShowSearch] = useState(false)
  // Domain connect/buy and email routing below are still open to every
  // site regardless of plan (that gating was deliberately dropped
  // earlier and hasn't been asked back) — this card is just the "remove
  // branding" upsell, now with a finalized once-off first tier.
  const domain = <DomainSection site={site} onSiteUpdated={onSiteUpdated} onGoToProfile={onGoToProfile} onOpenSearch={() => setShowSearch(true)} />
  return (
    <>
      <UpgradeCard site={site} />
      <AiAssistantSection site={site} onSiteUpdated={onSiteUpdated} />
      <WhatsAppConnectSection site={site} onSiteUpdated={onSiteUpdated} />
      {site.managed_deploy ? (
        <>
          {/* Only the domain is managed for these sites; everything else follows the plan. */}
          <div className="card notice">Your domain is managed by Vicinic. Contact us if it needs to change.</div>
          <fieldset className="locked-section" disabled>
            {domain}
          </fieldset>
        </>
      ) : (
        domain
      )}
      <EmailRoutingSection site={site} onOpenSearch={() => setShowSearch(true)} />
      {showSearch && !site.managed_deploy && (
        <DomainSearchSheet
          site={site}
          onSiteUpdated={onSiteUpdated}
          onGoToProfile={onGoToProfile}
          onClose={() => setShowSearch(false)}
        />
      )}
    </>
  )
}

function DeleteSiteSection({ site, onSiteDeleted }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  async function handleDelete() {
    const confirmed = window.confirm(
      `Delete "${site.name}"? This can't be undone — your site's text, editor history and email routing rules ` +
      'all go with it.' +
      (site.custom_domain
        ? ` Your domain (${site.custom_domain}) is NOT affected — you keep it for whatever period you've already paid for; only stops pointing at this site.`
        : '')
    )
    if (!confirmed) return
    setBusy(true)
    setError(null)
    try {
      await deleteSite(site.slug)
      onSiteDeleted(site.slug)
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <div className="card danger-zone">
      <h2>Danger zone</h2>
      {error && <div className="error">{error}</div>}
      <p>Deleting your site removes its text, editing history and email routing rules permanently.</p>
      {site.custom_domain && (
        <p className="field-hint">
          Your domain <strong>{site.custom_domain}</strong> stays yours — you keep it for whatever period you've
          already paid for. Deleting the site here only stops it pointing at Vicinic.
        </p>
      )}
      <button type="button" className="danger-button" onClick={handleDelete} disabled={busy}>
        {busy ? 'Deleting…' : 'Delete this site'}
      </button>
    </div>
  )
}

function VisitorsChart({ site }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [hover, setHover] = useState(null)

  useEffect(() => {
    setData(null)
    setError(null)
    getVisitors(site.slug, 30).then(setData).catch((err) => setError(err.message))
  }, [site.slug])

  const days = data?.days || []
  const max = Math.max(1, ...days.map((d) => d.visitors))
  const W = 600
  const H = 140
  const gap = 2
  const barW = days.length ? W / days.length - gap : 0
  const fmt = (iso) => new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
  const active = hover != null ? days[hover] : null

  return (
    <div className="card visitors-card">
      <h2>Unique visitors</h2>
      {error && <div className="error">{error}</div>}
      {!data && !error && <p className="field-hint">Loading…</p>}
      {data && (
        <>
          <p className="visitors-headline">
            <strong>{active ? active.visitors : data.total_unique}</strong>
            <span>{active ? fmt(active.date) : 'last 30 days'}</span>
          </p>
          <svg
            className="visitors-chart"
            viewBox={`0 0 ${W} ${H}`}
            preserveAspectRatio="none"
            role="img"
            aria-label={`Unique visitors per day, last 30 days: ${data.total_unique} in total`}
            onMouseLeave={() => setHover(null)}
          >
            <line x1="0" y1={H - 0.5} x2={W} y2={H - 0.5} className="visitors-baseline" />
            {days.map((d, i) => {
              const h = d.visitors ? Math.max(3, (d.visitors / max) * (H - 8)) : 0
              const x = i * (barW + gap)
              return (
                <g key={d.date} onMouseEnter={() => setHover(i)} onTouchStart={() => setHover(i)}>
                  <rect x={x} y="0" width={barW + gap} height={H} fill="transparent" />
                  {h > 0 && (
                    <rect
                      x={x}
                      y={H - h}
                      width={barW}
                      height={h}
                      rx="2"
                      className={`visitors-bar${hover === i ? ' active' : ''}`}
                    />
                  )}
                </g>
              )
            })}
          </svg>
          <div className="visitors-axis">
            <span>{days.length ? fmt(days[0].date) : ''}</span>
            <span>Today</span>
          </div>
        </>
      )}
    </div>
  )
}

function liveUrl(site) {
  return site.custom_domain && site.domain_status === 'active' ? `https://${site.custom_domain}/` : `${API_BASE}/${site.slug}/`
}

function OverviewTab({ site, checkoutNotice, onSiteUpdated }) {
  const [form, setForm] = useState(() => ({
    primary_color: site.primary_color || site.default_primary_color || '#2e8b57',
    email: site.email,
    phone: site.phone,
    whatsapp_number: site.whatsapp_number,
  }))
  const [saveState, setSaveState] = useState('idle') // idle | saving | saved | error
  const [saveError, setSaveError] = useState(null)

  useEffect(() => {
    setForm({
      primary_color: site.primary_color || site.default_primary_color || '#2e8b57',
      email: site.email,
      phone: site.phone,
      whatsapp_number: site.whatsapp_number,
    })
    setSaveState('idle')
  }, [site.slug])

  function setField(key, value) {
    setForm((prev) => ({ ...prev, [key]: value }))
    setSaveState('idle')
  }

  async function handleSave(e) {
    e.preventDefault()
    setSaveState('saving')
    setSaveError(null)
    try {
      const data = await updateSite(site.slug, form)
      onSiteUpdated(data.site)
      setSaveState('saved')
    } catch (err) {
      setSaveError(err.message)
      setSaveState('error')
    }
  }

  return (
    <>
      {checkoutNotice === 'success' && (
        <div className="card notice">
          Payment received — activating your site's plan. This can take a minute; refresh if it doesn't update.
        </div>
      )}
      {checkoutNotice === 'cancelled' && <div className="card notice">Checkout cancelled — your site is still on the free plan.</div>}

      <VisitorsChart site={site} />

      <div className="card">
        <h2>{site.name}</h2>
        <p>
          Status: <strong>{site.subscription_status === 'active' ? 'Paid plan' : 'Free plan'}</strong>
          {site.subscription_status === 'pending' && ' (payment pending)'}
        </p>
        <p>
          Live at{' '}
          <a className="live-link" href={liveUrl(site)} target="_blank" rel="noreferrer">
            {site.custom_domain && site.domain_status === 'active' ? site.custom_domain : 'Open your site ↗'}
          </a>
        </p>
      </div>

      <form className="card" onSubmit={handleSave}>
        <h2>Site details</h2>
        {saveError && <div className="error">{saveError}</div>}

        <label htmlFor="site-profile-name">Site name</label>
        <input id="site-profile-name" type="text" value={site.name} disabled />
        <p className="field-hint">Set once when you created the site — can't be changed here.</p>

        <label htmlFor="site-profile-color">Theme color</label>
        <input
          id="site-profile-color"
          type="color"
          value={form.primary_color}
          onChange={(e) => setField('primary_color', e.target.value)}
        />

        <label htmlFor="site-profile-email">Contact email</label>
        <input id="site-profile-email" type="email" value={form.email} onChange={(e) => setField('email', e.target.value)} />

        <label htmlFor="site-profile-phone">Phone</label>
        <PhoneInput id="site-profile-phone" value={form.phone} onChange={(v) => setField('phone', v)} />

        <label htmlFor="site-profile-whatsapp">WhatsApp number</label>
        <PhoneInput id="site-profile-whatsapp" value={form.whatsapp_number} onChange={(v) => setField('whatsapp_number', v)} />

        <div className="save-bar">
          <button type="submit" disabled={saveState === 'saving'}>
            {saveState === 'saving' ? 'Saving…' : 'Save details'}
          </button>
          {saveState === 'saved' && <span className="save-status">Saved</span>}
        </div>
      </form>
    </>
  )
}

const PROFILE_FIELDS = [
  { key: 'legal_name', label: 'Full name or business name', hint: "The legal owner of any domain you buy." },
  { key: 'phone', label: 'Phone', phone: true },
  { key: 'street', label: 'Street address' },
  { key: 'city', label: 'City' },
  { key: 'state', label: 'Province/State (optional)', optional: true },
  { key: 'postal_code', label: 'Postal code' },
  { key: 'country_code', label: 'Country code (2 letters, e.g. ZA)', maxLength: 2 },
]

function ProfileDetails({ onCompleteChange }) {
  const [form, setForm] = useState(null)
  const [saveState, setSaveState] = useState('idle') // idle | saving | saved | error
  const [error, setError] = useState(null)

  useEffect(() => {
    getProfile().then((data) => setForm(data.profile)).catch((err) => setError(err.message))
  }, [])

  function setField(key, value) {
    setForm((prev) => ({ ...prev, [key]: value }))
    setSaveState('idle')
  }

  async function handleSave(e) {
    e.preventDefault()
    setSaveState('saving')
    setError(null)
    try {
      const { email: _email, complete: _complete, ...fields } = form
      const data = await updateProfile(fields)
      setForm(data.profile)
      onCompleteChange(data.profile.complete)
      setSaveState('saved')
    } catch (err) {
      setError(err.message)
      setSaveState('error')
    }
  }

  if (!form) return error ? <div className="card error">{error}</div> : null

  return (
    <form className="card" onSubmit={handleSave}>
      <h2>Your details</h2>
      {!form.complete && (
        <div className="notice">
          Complete your profile — we use these details as the legal owner when you buy a domain, so you never have to
          type them again.
        </div>
      )}
      {error && <div className="error">{error}</div>}
      {PROFILE_FIELDS.map((f) => (
        <div key={f.key}>
          <label htmlFor={`profile-${f.key}`}>{f.label}</label>
          {f.phone ? (
            <PhoneInput id={`profile-${f.key}`} value={form[f.key] || ''} onChange={(v) => setField(f.key, v)} required />
          ) : (
          <input
            id={`profile-${f.key}`}
            type="text"
            maxLength={f.maxLength}
            value={form[f.key] || ''}
            onChange={(e) => setField(f.key, f.key === 'country_code' ? e.target.value.toUpperCase() : e.target.value)}
            required={!f.optional}
          />
          )}
          {f.hint && <p className="field-hint">{f.hint}</p>}
        </div>
      ))}
      <div className="save-bar">
        <button type="submit" disabled={saveState === 'saving'}>
          {saveState === 'saving' ? 'Saving…' : 'Save details'}
        </button>
        {saveState === 'saved' && <span className="save-status">Saved</span>}
      </div>
    </form>
  )
}

function ProfileTab({ displayName, username, email, onLogout, site, onSiteDeleted, onProfileCompleteChange }) {
  return (
    <>
      <div className="card">
        <h2>Profile</h2>
        <p><strong>Name:</strong> {displayName}</p>
        <p><strong>Username:</strong> {username}</p>
        <p><strong>Email:</strong> {email}</p>
        <button type="button" className="link-button" onClick={onLogout}>Sign out</button>
      </div>
      <ProfileDetails onCompleteChange={onProfileCompleteChange} />
      {site && <DeleteSiteSection site={site} onSiteDeleted={onSiteDeleted} />}
    </>
  )
}

const TABS = [
  {
    key: 'overview',
    label: 'Overview',
    icon: (
      <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="3" y="3" width="8" height="8" rx="1.5" />
        <rect x="13" y="3" width="8" height="8" rx="1.5" />
        <rect x="3" y="13" width="8" height="8" rx="1.5" />
        <rect x="13" y="13" width="8" height="8" rx="1.5" />
      </svg>
    ),
  },
  {
    key: 'edit',
    label: 'Edit',
    icon: (
      <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 20h9" strokeLinecap="round" />
        <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    key: 'deploy',
    label: 'Deploy',
    icon: (
      <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="9" />
        <path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    key: 'profile',
    label: 'Profile',
    icon: (
      <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="8" r="3.5" />
        <path d="M4.5 20a7.5 7.5 0 0 1 15 0" strokeLinecap="round" />
      </svg>
    ),
  },
]

function BottomNav({ active, onSelect, badges = {} }) {
  return (
    <nav className="bottom-nav">
      {TABS.map((tab) => (
        <button
          key={tab.key}
          type="button"
          className={`bottom-nav-item${active === tab.key ? ' active' : ''}`}
          onClick={() => onSelect(tab.key)}
        >
          <span className="bottom-nav-icon">
            {tab.icon}
            {badges[tab.key] && <span className="nav-badge" aria-label="Needs attention" />}
          </span>
          <span>{tab.label}</span>
        </button>
      ))}
    </nav>
  )
}

function SlotField({ slot, value, onChange }) {
  // Decided once from the slot's own default text (stable) rather than the
  // live value, so the field doesn't flip between <input> and <textarea>
  // (and lose focus) as the user types past the threshold.
  const isLong = slot.default_text.length > 60
  const Field = isLong ? 'textarea' : 'input'
  return (
    <div className="slot-field">
      <div className="slot-field-header">
        <label>{slot.label}</label>
        {value !== slot.default_text && (
          <button type="button" className="link-button" onClick={() => onChange(slot.default_text)}>
            Reset to default
          </button>
        )}
      </div>
      <Field
        {...(isLong ? { rows: 3 } : { type: 'text' })}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  )
}

// Phones take photos far bigger than a website needs (and than the upload
// limit allows) — scale anything large down to 2400px before sending.
async function shrinkImage(file) {
  if (file.size <= 3.5 * 1024 * 1024 || !/^image\/(jpeg|png|webp)$/.test(file.type)) return file
  const bitmap = await createImageBitmap(file)
  const scale = Math.min(1, 2400 / Math.max(bitmap.width, bitmap.height))
  const canvas = document.createElement('canvas')
  canvas.width = Math.round(bitmap.width * scale)
  canvas.height = Math.round(bitmap.height * scale)
  canvas.getContext('2d').drawImage(bitmap, 0, 0, canvas.width, canvas.height)
  const type = file.type === 'image/jpeg' ? 'image/jpeg' : 'image/webp'
  const blob = await new Promise((resolve) => canvas.toBlob(resolve, type, 0.85))
  return new File([blob], file.name.replace(/\.\w+$/, type === 'image/jpeg' ? '.jpg' : '.webp'), { type })
}

function ImageTile({ img, selected, busy, tileRef, onFile, onReset }) {
  return (
    <div ref={tileRef} className={`image-tile${selected ? ' selected' : ''}`}>
      <div className="image-thumb"><img src={img.current} alt="" loading="lazy" /></div>
      <div className="image-badges">
        {img.logo && <span className="domain-badge">Logo</span>}
        {img.favicon && !img.logo && <span className="domain-badge">Site icon</span>}
        {img.pending && <span className="pending-badge">Unpublished</span>}
      </div>
      <div className="image-actions">
        <label className="image-replace">
          {busy ? 'Uploading…' : 'Replace'}
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp,image/gif"
            onChange={(e) => {
              onFile(e.target.files[0])
              e.target.value = ''
            }}
          />
        </label>
        {img.replaced && (
          <button type="button" className="link-button" onClick={onReset}>Reset</button>
        )}
      </div>
    </div>
  )
}

function ImagesPanel({ site, page, selectedSrc, refreshKey, onChanged, onPendingChange }) {
  const [images, setImages] = useState(null)
  const [state, setState] = useState({ available: true, logo_scale: 100, has_pending: false })
  const [busy, setBusy] = useState(null) // original url being changed
  const [error, setError] = useState(null)
  const tileRefs = useRef({})
  const scaleTimer = useRef(null)

  function applyState(data) {
    const next = { available: data.available, logo_scale: data.logo_scale, has_pending: data.has_pending }
    setState(next)
    onPendingChange(next.has_pending)
  }

  useEffect(() => {
    setImages(null)
    setError(null)
    getSiteImages(site.slug, page)
      .then((data) => {
        setImages(data.images)
        applyState(data)
      })
      .catch((err) => setError(err.message))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [site.slug, page, refreshKey])

  const selected = images && selectedSrc
    ? images.find((img) => img.current === selectedSrc || img.original === selectedSrc || selectedSrc.endsWith(img.current))
    : null

  useEffect(() => {
    // After PanelCard has opened, so the tile is visible to scroll to.
    if (selected) setTimeout(() => tileRefs.current[selected.original]?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 50)
  }, [selected])

  async function run(image, action) {
    setBusy(image.original)
    setError(null)
    try {
      const data = await action()
      setImages((prev) => prev.map((img) => (img.original === image.original ? { ...data.image, logo: img.logo } : img)))
      applyState(data)
      onChanged()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(null)
    }
  }

  function handleScale(value) {
    setState((prev) => ({ ...prev, logo_scale: value }))
    clearTimeout(scaleTimer.current)
    scaleTimer.current = setTimeout(async () => {
      try {
        applyState(await setLogoScale(site.slug, value))
        onChanged()
      } catch (err) {
        setError(err.message)
      }
    }, 400)
  }

  if (images && images.length === 0) return null

  const logos = images ? images.filter((img) => img.logo) : []
  const favicons = images ? images.filter((img) => img.favicon && !img.logo) : []
  const others = images ? images.filter((img) => !img.logo && !img.favicon) : []
  const tile = (img) => (
    <ImageTile
      key={img.original}
      img={img}
      selected={selected && selected.original === img.original}
      busy={busy === img.original}
      tileRef={(el) => { tileRefs.current[img.original] = el }}
      onFile={(file) => file && run(img, async () => uploadSiteImage(site.slug, img.original, await shrinkImage(file)))}
      onReset={() => run(img, () => resetSiteImage(site.slug, img.original))}
    />
  )

  return (
    <PanelCard title="Images" count={images ? images.length : null} openSignal={selectedSrc}>
      {state.available ? (
        <p className="field-hint images-hint">
          Tap an image on the preview, or pick one below. Changes show in the preview and go live when you tap Publish changes.
        </p>
      ) : (
        <div className="notice">Replacing your logo and images comes with every paid plan — upgrade on the Deploy tab.</div>
      )}
      {error && <div className="error">{error}</div>}
      {!images && !error && <p className="field-hint">Loading images…</p>}
      {images && (
        <fieldset className={state.available ? 'plain-fieldset' : 'plain-fieldset locked-section'} disabled={!state.available || busy !== null}>
          {logos.length > 0 && (
            <>
              <h3 className="domain-list-title">Logo</h3>
              <div className="image-grid">{logos.map(tile)}</div>
              <label htmlFor="logo-scale" className="logo-scale-label">
                Logo size <strong>{state.logo_scale}%</strong>
              </label>
              <input
                id="logo-scale"
                type="range"
                min="50"
                max="200"
                step="5"
                value={state.logo_scale}
                onChange={(e) => handleScale(Number(e.target.value))}
              />
            </>
          )}
          {favicons.length > 0 && (
            <>
              <h3 className="domain-list-title">Site icon</h3>
              <p className="field-hint">Shown on the browser tab and phone home screens — a square image works best.</p>
              <div className="image-grid">{favicons.map(tile)}</div>
            </>
          )}
          {others.length > 0 && (
            <>
              <h3 className="domain-list-title">Other images</h3>
              <div className="image-grid">{others.map(tile)}</div>
            </>
          )}
        </fieldset>
      )}
    </PanelCard>
  )
}

// A long editor card that folds away; `openSignal` changing (e.g. a tap in
// the preview picked something inside it) opens it again.
function PanelCard({ title, count, openSignal, children }) {
  const [open, setOpen] = useState(false)
  useEffect(() => {
    if (openSignal) setOpen(true)
  }, [openSignal])
  return (
    <details className="card panel-card" open={open} onToggle={(e) => setOpen(e.currentTarget.open)}>
      <summary>
        <h2>{title}</h2>
        {count != null && <span className="panel-count">{count}</span>}
      </summary>
      {children}
    </details>
  )
}

const TARGET_KINDS = [
  ['page', 'A page on your site'],
  ['section', 'A section of this page'],
  ['url', 'Web address'],
  ['email', 'Email'],
  ['phone', 'Phone call'],
  ['whatsapp', 'WhatsApp'],
]

function targetKind(target) {
  if (target.startsWith('page:')) return 'page'
  if (target.startsWith('#')) return 'section'
  if (target.startsWith('mailto:')) return 'email'
  if (target.startsWith('tel:')) return 'phone'
  if (/^https:\/\/wa\.me\//.test(target)) return 'whatsapp'
  return 'url'
}

// Where a link or menu item goes, as plain choices instead of a raw href.
function TargetPicker({ value, pages, sections, site, disabled, label, onChange }) {
  const [kind, setKind] = useState(targetKind(value))
  const [text, setText] = useState('')
  useEffect(() => {
    const k = targetKind(value)
    setKind(k)
    setText(
      k === 'email' ? value.slice(7) : k === 'phone' ? value.slice(4) : k === 'whatsapp' ? value.replace('https://wa.me/', '+') : k === 'url' && value !== '#' ? value : ''
    )
  }, [value])

  function pickKind(next) {
    setKind(next)
    if (next === 'page') onChange(pages[0]?.target || 'page:')
    else if (next === 'section') onChange(sections[0]?.target || '#')
    else if (next === 'email' && site.email) onChange(`mailto:${site.email}`)
    else if (next === 'phone' && site.phone) onChange(`tel:${site.phone.replace(/[^\d+]/g, '')}`)
    else if (next === 'whatsapp' && (site.whatsapp_number || site.phone)) {
      onChange(`https://wa.me/${(site.whatsapp_number || site.phone).replace(/\D/g, '').replace(/^0/, '27')}`)
    } else setText('')
  }

  function commitText() {
    const t = text.trim()
    if (!t) return
    if (kind === 'email') onChange(`mailto:${t}`)
    else if (kind === 'phone') onChange(`tel:${t.replace(/[^\d+]/g, '')}`)
    else if (kind === 'whatsapp') onChange(`https://wa.me/${t.replace(/\D/g, '').replace(/^0/, '27')}`)
    else onChange(/^[a-z]+:|^\//i.test(t) ? t : `https://${t}`)
  }

  const knownPage = pages.some((p) => p.target === value)
  const knownSection = sections.some((s) => s.target === value)
  return (
    <div className="target-picker">
      <select value={kind} disabled={disabled} aria-label={`What "${label}" links to`} onChange={(e) => pickKind(e.target.value)}>
        {TARGET_KINDS.map(([k, name]) => (
          <option key={k} value={k}>{name}</option>
        ))}
      </select>
      {kind === 'page' && (
        <select value={knownPage ? value : ''} disabled={disabled} aria-label="Page" onChange={(e) => onChange(e.target.value)}>
          {!knownPage && <option value="">Choose a page…</option>}
          {pages.map((p) => (
            <option key={p.target} value={p.target}>{p.title}</option>
          ))}
        </select>
      )}
      {kind === 'section' && (
        <select value={knownSection ? value : ''} disabled={disabled} aria-label="Section" onChange={(e) => onChange(e.target.value)}>
          {!knownSection && <option value="">{value === '#' ? 'Nowhere yet — choose a section…' : 'Choose a section…'}</option>}
          {sections.map((s) => (
            <option key={s.target} value={s.target}>{s.title}</option>
          ))}
        </select>
      )}
      {['url', 'email', 'phone', 'whatsapp'].includes(kind) && (
        <input
          type={kind === 'email' ? 'email' : kind === 'url' ? 'url' : 'tel'}
          inputMode={kind === 'url' ? 'url' : kind === 'email' ? 'email' : 'tel'}
          placeholder={{ url: 'https://…', email: 'you@business.co.za', phone: '082 123 4567', whatsapp: '082 123 4567' }[kind]}
          value={text}
          disabled={disabled}
          aria-label={TARGET_KINDS.find(([k]) => k === kind)[1]}
          onChange={(e) => setText(e.target.value)}
          onBlur={commitText}
          onKeyDown={(e) => e.key === 'Enter' && e.currentTarget.blur()}
        />
      )}
    </div>
  )
}

function LinkRow({ link, site, choices, selected, rowRef, disabled, onSave }) {
  return (
    <li ref={rowRef} className={`link-row${selected ? ' selected' : ''}`}>
      <div className="link-row-head">
        <strong>{link.label}</strong>
        {link.pending && <span className="pending-badge">Unpublished</span>}
      </div>
      {link.locked ? (
        <p className="field-hint">Template credit — it stays on the Starter plan. Growth and Business OS can change it.</p>
      ) : (
        <>
          <TargetPicker
            value={link.href}
            pages={choices.pages}
            sections={choices.sections}
            site={site}
            label={link.label}
            disabled={disabled}
            onChange={(href) => href !== link.href && onSave(href)}
          />
          {link.changed && (
            <button type="button" className="link-button" disabled={disabled} onClick={() => onSave('')}>
              Back to the template's link
            </button>
          )}
        </>
      )}
    </li>
  )
}

function MenuItemEditor({ item, index, count, site, choices, disabled, onChange, onMove, onRemove, isChild }) {
  const hasChildren = !isChild && item.children.length > 0
  return (
    <li className={`menu-item${isChild ? ' menu-child' : ''}`}>
      <div className="menu-item-head">
        <input
          type="text"
          value={item.label}
          maxLength={40}
          disabled={disabled}
          aria-label="Menu item name"
          placeholder="Name"
          onChange={(e) => onChange({ ...item, label: e.target.value })}
        />
        <button type="button" className="icon-button" disabled={disabled || index === 0} aria-label="Move up" onClick={() => onMove(-1)}>↑</button>
        <button type="button" className="icon-button" disabled={disabled || index === count - 1} aria-label="Move down" onClick={() => onMove(1)}>↓</button>
        <button type="button" className="icon-button danger" disabled={disabled} aria-label="Remove" onClick={onRemove}>✕</button>
      </div>
      {hasChildren ? (
        <p className="field-hint">Dropdown — opens the links below.</p>
      ) : (
        <TargetPicker
          value={item.target}
          pages={choices.pages}
          sections={choices.sections}
          site={site}
          label={item.label}
          disabled={disabled}
          onChange={(target) => onChange({ ...item, target })}
        />
      )}
      {!isChild && (
        <>
          {hasChildren && (
            <ul className="menu-children">
              {item.children.map((child, i) => (
                <MenuItemEditor
                  key={i}
                  item={child}
                  index={i}
                  count={item.children.length}
                  site={site}
                  choices={choices}
                  disabled={disabled}
                  isChild
                  onChange={(next) => onChange({ ...item, children: item.children.map((c, j) => (j === i ? next : c)) })}
                  onMove={(d) => onChange({ ...item, children: moveItem(item.children, i, d) })}
                  onRemove={() => onChange({ ...item, children: item.children.filter((_c, j) => j !== i) })}
                />
              ))}
            </ul>
          )}
          <button
            type="button"
            className="link-button"
            disabled={disabled || item.children.length >= 10}
            onClick={() =>
              onChange({
                ...item,
                target: '',
                children: [...item.children, { label: '', target: choices.pages[0]?.target || 'page:' }],
              })
            }
          >
            {hasChildren ? '+ Add a dropdown link' : '+ Turn into a dropdown'}
          </button>
        </>
      )}
    </li>
  )
}

function moveItem(list, index, delta) {
  const next = [...list]
  const [item] = next.splice(index, 1)
  next.splice(index + delta, 0, item)
  return next
}

function MenuPanel({ site, refreshKey, onChanged, onPendingChange }) {
  const [data, setData] = useState(null)
  const [items, setItems] = useState(null)
  const [dirty, setDirty] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  function apply(res) {
    setData(res)
    setItems(res.items.map((i) => ({ ...i, children: i.children || [] })))
    setDirty(false)
    onPendingChange(res.has_pending)
  }

  useEffect(() => {
    setData(null)
    setError(null)
    getSiteMenu(site.slug).then(apply).catch((err) => setError(err.message))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [site.slug, refreshKey])

  function edit(next) {
    setItems(next)
    setDirty(true)
  }

  async function run(fn) {
    setBusy(true)
    setError(null)
    try {
      apply(await fn())
      onChanged()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  if (error && !data) return <div className="card error">Could not load the menu: {error}</div>
  if (!data || !items) return null

  return (
    <PanelCard title="Menu" count={items.length}>
      {data.available ? (
        <p className="field-hint images-hint">
          The links across the top of your site. Rename, reorder, add or remove them — a page, a section, or any web
          address. Tap Save menu, then Publish changes.
        </p>
      ) : (
        <div className="notice">Editing your menu comes with every paid plan — upgrade on the Deploy tab.</div>
      )}
      {error && <div className="error">{error}</div>}
      <fieldset className={data.available ? 'plain-fieldset' : 'plain-fieldset locked-section'} disabled={!data.available || busy}>
        <ul className="menu-list">
          {items.map((item, i) => (
            <MenuItemEditor
              key={i}
              item={item}
              index={i}
              count={items.length}
              site={site}
              choices={data}
              disabled={busy}
              onChange={(next) => edit(items.map((it, j) => (j === i ? next : it)))}
              onMove={(d) => edit(moveItem(items, i, d))}
              onRemove={() => edit(items.filter((_it, j) => j !== i))}
            />
          ))}
        </ul>
        <div className="button-row">
          <button
            type="button"
            className="secondary"
            disabled={items.length >= 12}
            onClick={() => edit([...items, { label: '', target: data.pages[0]?.target || 'page:', children: [] }])}
          >
            + Add menu item
          </button>
          <button type="button" disabled={!dirty} onClick={() => run(() => saveSiteMenu(site.slug, items))}>
            {busy ? 'Saving…' : 'Save menu'}
          </button>
          {(data.customized || dirty) && (
            <button type="button" className="link-button" onClick={() => run(() => resetSiteMenu(site.slug))}>
              Use the template's menu
            </button>
          )}
        </div>
        {data.menu_pending && !dirty && <p className="field-hint">Saved — tap Publish changes to put it live.</p>}
      </fieldset>
    </PanelCard>
  )
}

function LinksPanel({ site, page, selectedKey, refreshKey, onChanged, onPendingChange }) {
  const [links, setLinks] = useState(null)
  const [choices, setChoices] = useState({ pages: [], sections: [] })
  const [available, setAvailable] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const rowRefs = useRef({})

  function load() {
    return getSiteLinks(site.slug, page).then((data) => {
      setLinks(data.links)
      setChoices({ pages: data.pages || [], sections: data.sections || [] })
      setAvailable(data.available)
      onPendingChange(data.has_pending)
    })
  }

  useEffect(() => {
    setLinks(null)
    setError(null)
    load().catch((err) => setError(err.message))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [site.slug, page, refreshKey])

  useEffect(() => {
    // After PanelCard has opened, so the row is visible to scroll to.
    if (selectedKey) setTimeout(() => rowRefs.current[selectedKey]?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 50)
  }, [selectedKey])

  async function handleSave(key, href) {
    setBusy(true)
    setError(null)
    try {
      await setSiteLink(site.slug, key, href)
      await load()
      onChanged()
    } catch (err) {
      setError(err.message)
      await load().catch(() => {})
    } finally {
      setBusy(false)
    }
  }

  if (links && links.length === 0) return null

  return (
    <PanelCard title="Buttons & links" count={links ? links.length : null} openSignal={selectedKey}>
      {available ? (
        <p className="field-hint images-hint">
          Tap a button on the preview, or pick one below, to change where it goes — a page, a section, a web address,
          email, phone or WhatsApp. Your top menu has its own panel. Goes live when you tap Publish changes.
        </p>
      ) : (
        <div className="notice">Changing where your buttons and links go comes with every paid plan — upgrade on the Deploy tab.</div>
      )}
      {error && <div className="error">{error}</div>}
      {!links && !error && <p className="field-hint">Loading links…</p>}
      {links && (
        <fieldset className={available ? 'plain-fieldset' : 'plain-fieldset locked-section'} disabled={!available}>
          <ul className="link-list">
            {links.map((link) => (
              <LinkRow
                key={link.key}
                link={link}
                site={site}
                choices={choices}
                selected={selectedKey === link.key}
                disabled={busy}
                rowRef={(el) => { rowRefs.current[link.key] = el }}
                onSave={(href) => handleSave(link.key, href)}
              />
            ))}
          </ul>
        </fieldset>
      )}
    </PanelCard>
  )
}

function SectionsPanel({ site, customPage, refreshKey, onChanged, onPendingChange, onPagesChanged }) {
  const [data, setData] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [title, setTitle] = useState(customPage.title)

  useEffect(() => setTitle(customPage.title), [customPage.title])

  function apply(result) {
    setData(result)
    onPendingChange(result.has_pending)
  }

  useEffect(() => {
    setData(null)
    getPageSections(site.slug, customPage.id).then(apply).catch((err) => setError(err.message))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [site.slug, customPage.id, refreshKey])

  async function run(fn) {
    setBusy(true)
    setError(null)
    try {
      const result = await fn()
      if (result && result.sections) apply(result)
      onChanged()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const act = (body) => run(() => pageSectionAction(site.slug, customPage.id, body))

  async function saveSettings(fields) {
    setError(null)
    try {
      await updateSitePage(site.slug, customPage.id, fields)
      onPagesChanged()
      onChanged()
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleDelete() {
    if (!window.confirm(`Delete the "${customPage.title}" page and everything on it? This can't be undone.`)) return
    try {
      await deleteSitePage(site.slug, customPage.id)
      onPagesChanged(null)
    } catch (err) {
      setError(err.message)
    }
  }

  if (!data) return error ? <div className="card error">{error}</div> : null

  return (
    <>
      <div className="card">
        <h2>Sections on this page</h2>
        <p className="field-hint images-hint">Tap any text on the preview to edit it. Change pictures and button links here.</p>
        {error && <div className="error">{error}</div>}
        <fieldset className="plain-fieldset" disabled={busy}>
          {data.sections.length === 0 && <p className="field-hint">No sections yet — add one below.</p>}
          {data.sections.map((sec, i) => {
            const fields = Object.keys(sec.fields)
            return (
              <div key={sec.id} className="section-card">
                <div className="link-row-head">
                  <strong>{sec.label}</strong>
                  <span className="section-tools">
                    <button type="button" className="chip" disabled={i === 0} onClick={() => act({ action: 'move', id: sec.id, direction: -1 })} aria-label="Move up">↑</button>
                    <button type="button" className="chip" disabled={i === data.sections.length - 1} onClick={() => act({ action: 'move', id: sec.id, direction: 1 })} aria-label="Move down">↓</button>
                    <button type="button" className="link-button" onClick={() => act({ action: 'remove', id: sec.id })}>Remove</button>
                  </span>
                </div>
                {fields.filter((f) => f.endsWith('image')).length > 0 && (
                  <div className="image-grid">
                    {fields.filter((f) => f.endsWith('image')).map((f) => (
                      <div key={f} className="image-tile">
                        <div className="image-thumb"><img src={sec.fields[f]} alt="" /></div>
                        <label className="image-replace">
                          Replace
                          <input
                            type="file"
                            accept="image/jpeg,image/png,image/webp,image/gif"
                            onChange={async (e) => {
                              const file = e.target.files[0]
                              e.target.value = ''
                              if (file) run(async () => uploadSectionImage(site.slug, customPage.id, sec.id, f, await shrinkImage(file)))
                            }}
                          />
                        </label>
                      </div>
                    ))}
                  </div>
                )}
                {fields.filter((f) => f.endsWith('_url')).map((f) => {
                  const labelField = f.replace(/_url$/, '')
                  return (
                    <div key={f} className="section-link">
                      <label htmlFor={`${sec.id}-${f}`}>"{sec.fields[labelField] || 'Button'}" goes to</label>
                      <input
                        id={`${sec.id}-${f}`}
                        type="text"
                        inputMode="url"
                        defaultValue={sec.fields[f]}
                        key={sec.fields[f]}
                        onBlur={(e) => e.target.value.trim() !== sec.fields[f] && act({ action: 'set', id: sec.id, field: f, value: e.target.value.trim() })}
                        onKeyDown={(e) => e.key === 'Enter' && e.currentTarget.blur()}
                      />
                    </div>
                  )
                })}
              </div>
            )
          })}
          <h3 className="domain-list-title">Add a section</h3>
          <div className="section-catalog">
            {data.catalog.map((c) => (
              <button key={c.type} type="button" className="section-type" onClick={() => act({ action: 'add', type: c.type })}>
                <strong>{c.label}</strong>
                <span>{c.description}</span>
              </button>
            ))}
          </div>
        </fieldset>
      </div>

      <div className="card">
        <h2>Page settings</h2>
        <label htmlFor="page-title">Page name</label>
        <input
          id="page-title"
          type="text"
          maxLength={80}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onBlur={() => title.trim() && title.trim() !== customPage.title && saveSettings({ title: title.trim() })}
        />
        <p className="field-hint">Address: /{customPage.slug}/</p>
        <label htmlFor="page-nav" className="checkbox-label">
          <input
            id="page-nav"
            type="checkbox"
            checked={customPage.show_in_nav}
            onChange={(e) => saveSettings({ show_in_nav: e.target.checked })}
            style={{ marginRight: '8px' }}
          />
          Show this page in the site's menu
        </label>
        <button type="button" className="danger-button" onClick={handleDelete}>Delete this page</button>
      </div>
    </>
  )
}

function AddPageButton({ site, pagesState, onCreated }) {
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  if (!pagesState) return null
  if (!pagesState.available) {
    return <p className="field-hint add-page-hint">Adding your own pages comes with every paid plan.</p>
  }
  const used = pagesState.pages.length
  const limitText = pagesState.limit === null ? '' : ` (${used} of ${pagesState.limit})`

  async function handleCreate(e) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const data = await createSitePage(site.slug, title.trim())
      setTitle('')
      setOpen(false)
      onCreated(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  if (!open) {
    return (
      <button type="button" className="add-page-button" disabled={!pagesState.can_add} onClick={() => setOpen(true)}>
        + Add a page{limitText}
      </button>
    )
  }
  return (
    <form onSubmit={handleCreate} className="add-page-form">
      {error && <div className="error">{error}</div>}
      <label htmlFor="new-page-title">New page name</label>
      <div className="domain-search-form">
        <input id="new-page-title" type="text" maxLength={80} placeholder="e.g. Pricing" value={title} onChange={(e) => setTitle(e.target.value)} autoFocus required />
        <button type="submit" disabled={busy || !title.trim()}>{busy ? 'Adding…' : 'Add'}</button>
      </div>
      <button type="button" className="link-button" onClick={() => setOpen(false)}>Cancel</button>
    </form>
  )
}

function VisualEditor({ site }) {
  const [groups, setGroups] = useState(null)
  const [loadError, setLoadError] = useState(null)
  const [activePage, setActivePage] = useState(null)
  const [drafts, setDrafts] = useState({})
  const [saveState, setSaveState] = useState('idle') // idle | saving | saved | error
  const [saveError, setSaveError] = useState(null)
  const [selectedImage, setSelectedImage] = useState(null)
  const [selectedLink, setSelectedLink] = useState(null)
  const [pagesState, setPagesState] = useState(null)
  const [imagesPending, setImagesPending] = useState(false)
  const [previewNonce, setPreviewNonce] = useState(0)
  const [imagesRefresh, setImagesRefresh] = useState(0)
  const iframeRef = useRef(null)
  // The preview is on another origin, so it can't be reloaded through
  // contentWindow.location — changing its URL reloads it instead.
  const reloadPreview = () => setPreviewNonce((n) => n + 1)

  useEffect(() => {
    setGroups(null)
    setLoadError(null)
    setSaveState('idle')
    setDrafts(loadDraft(site.slug))
    getSiteSlots(site.slug)
      .then((data) => {
        setGroups(data.groups)
        if (site.subscription_status !== 'active') {
          // Free-tier sites can only edit their home page — the backend
          // already silently drops an edit to any other page's slots, so
          // there's no point ever pointing the preview at one.
          setActivePage('')
        } else {
          const firstPage = data.groups.find((g) => g.page !== null)
          setActivePage(firstPage ? firstPage.page : '')
        }
      })
      .catch((err) => setLoadError(err.message))
  }, [site.slug, site.subscription_status])

  function loadCustomPages() {
    return getSitePages(site.slug).then(setPagesState).catch(() => setPagesState(null))
  }

  useEffect(() => {
    loadCustomPages()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [site.slug, site.subscription_status])

  useEffect(() => {
    function handleMessage(e) {
      if (iframeRef.current && e.source !== iframeRef.current.contentWindow) return
      const msg = e.data
      if (msg && msg.source === 'vicinic-editor' && msg.type === 'image-clicked') {
        setSelectedImage(msg.src)
        return
      }
      if (msg && msg.source === 'vicinic-editor' && msg.type === 'link-clicked') {
        setSelectedLink(msg.key)
        return
      }
      if (!msg || msg.source !== 'vicinic-editor' || msg.type !== 'slot-changed') return
      setDrafts((prev) => {
        const next = { ...prev, [msg.key]: msg.value }
        storeDraft(site.slug, next)
        return next
      })
    }
    window.addEventListener('message', handleMessage)
    return () => window.removeEventListener('message', handleMessage)
  }, [site.slug])

  function setDraftValue(key, value) {
    setDrafts((prev) => {
      const next = { ...prev, [key]: value }
      storeDraft(site.slug, next)
      return next
    })
  }

  function sendDraftToPreview() {
    iframeRef.current?.contentWindow?.postMessage(
      { source: 'vicinic-editor', type: 'apply-draft', values: drafts },
      '*'
    )
  }

  async function handlePublish() {
    setSaveState('saving')
    setSaveError(null)
    try {
      const slotDrafts = {}
      const sectionDrafts = {}
      Object.entries(drafts).forEach(([key, value]) => {
        if (key.startsWith('sp:')) {
          const pageId = key.split(':')[1]
          sectionDrafts[pageId] = { ...(sectionDrafts[pageId] || {}), [key]: value }
        } else {
          slotDrafts[key] = value
        }
      })
      for (const [pageId, values] of Object.entries(sectionDrafts)) {
        await pageSectionAction(site.slug, pageId, { action: 'set_many', values })
      }
      if (Object.keys(slotDrafts).length > 0) {
        const data = await saveSiteSlots(site.slug, slotDrafts)
        setGroups(data.groups)
      }
      if (Object.keys(drafts).length > 0) {
        clearDraft(site.slug)
        setDrafts({})
      }
      if (imagesPending || Object.keys(sectionDrafts).length > 0) {
        await publishSiteImages(site.slug)
        setImagesPending(false)
        setImagesRefresh((n) => n + 1)
        loadCustomPages()
      }
      setSaveState('saved')
    } catch (err) {
      setSaveError(err.message)
      setSaveState('error')
    }
  }

  async function handleDiscard() {
    clearDraft(site.slug)
    setDrafts({})
    setSaveState('idle')
    if (imagesPending) {
      try {
        await discardSiteImages(site.slug)
      } catch (err) {
        setSaveError(err.message)
      }
      setImagesPending(false)
      setImagesRefresh((n) => n + 1)
      const refreshed = await getSitePages(site.slug).catch(() => null)
      setPagesState(refreshed)
      if (refreshed && !refreshed.pages.some((p) => p.slug === activePage) && !groups.some((g) => g.page === activePage)) {
        setActivePage('')
      }
    }
    reloadPreview()
  }

  if (loadError) return <div className="card error">Could not load this site's text: {loadError}</div>
  if (!groups || activePage === null) return null

  // Templates whose text is all shared (header/footer slots) have no page
  // groups at all — the home page still exists, so always offer it.
  const pageGroups = groups.filter((g) => g.page !== null)
  const pages = pageGroups.some((g) => g.page === '') ? pageGroups : [{ page: '', label: 'Home' }, ...pageGroups]
  const isFreeTier = site.subscription_status !== 'active'
  const isDirty = Object.keys(drafts).length > 0 || imagesPending
  const previewUrl = `${API_BASE}/${site.slug}/${activePage ? `${activePage}/` : ''}?vicinic_edit=1&v=${previewNonce}`
  const customPages = pagesState ? pagesState.pages : []
  const activeCustom = customPages.find((p) => p.slug === activePage) || null
  const fallbackSlots = activeCustom
    ? []
    : groups
        .filter((g) => g.page === null || g.page === activePage)
        .flatMap((g) => g.slots.filter((s) => NON_INLINE_TAGS.has(slotTag(s.label))))

  return (
    <>
      {!isFreeTier && (
        <div className="card site-picker">
          <label htmlFor="preview-page">Page</label>
          <select id="preview-page" value={activePage} onChange={(e) => setActivePage(e.target.value)}>
            {pages.map((g) => (
              <option key={g.page} value={g.page}>{g.label}</option>
            ))}
            {customPages.length > 0 && (
              <optgroup label="Your pages">
                {customPages.map((p) => (
                  <option key={p.slug} value={p.slug}>{p.title}{p.published ? '' : ' (not published yet)'}</option>
                ))}
              </optgroup>
            )}
          </select>
          <AddPageButton
            site={site}
            pagesState={pagesState}
            onCreated={(data) => {
              setPagesState(data)
              setImagesPending(true)
              setActivePage(data.page.slug)
            }}
          />
        </div>
      )}
      {isFreeTier && pages.length > 1 && (
        <div className="card notice">
          Free sites can only edit the homepage — upgrade on the Deploy tab to edit every page.
        </div>
      )}

      <div className="card notice">Tap any text on the preview to edit it — or tap an image or button to change it below.</div>

      <div className="visual-editor-frame">
        <iframe ref={iframeRef} src={previewUrl} title="Site preview" onLoad={sendDraftToPreview} />
      </div>

      {activeCustom && (
        <SectionsPanel
          site={site}
          customPage={activeCustom}
          refreshKey={imagesRefresh}
          onChanged={reloadPreview}
          onPendingChange={setImagesPending}
          onPagesChanged={(deleted) => {
            loadCustomPages()
            if (deleted === null) setActivePage('')
          }}
        />
      )}

      {!activeCustom && (
      <ImagesPanel
        site={site}
        page={activePage}
        selectedSrc={selectedImage}
        refreshKey={imagesRefresh}
        onChanged={reloadPreview}
        onPendingChange={setImagesPending}
      />

      )}

      {!isFreeTier && (
        <MenuPanel site={site} refreshKey={imagesRefresh} onChanged={reloadPreview} onPendingChange={setImagesPending} />
      )}

      {!activeCustom && (
      <LinksPanel
        site={site}
        page={activePage}
        selectedKey={selectedLink}
        refreshKey={imagesRefresh}
        onChanged={reloadPreview}
        onPendingChange={setImagesPending}
      />
      )}

      {fallbackSlots.length > 0 && (
        <div className="card">
          <h2>Page settings</h2>
          <p>These aren't part of the visible page, so they're edited here instead.</p>
          {fallbackSlots.map((slot) => (
            <SlotField
              key={slot.key}
              slot={slot}
              value={drafts[slot.key] ?? slot.value}
              onChange={(v) => setDraftValue(slot.key, v)}
            />
          ))}
        </div>
      )}

      <div className="save-bar">
        {saveError && <div className="error">{saveError}</div>}
        {isDirty && (
          <button type="button" className="link-button" onClick={handleDiscard} disabled={saveState === 'saving'}>
            Discard changes
          </button>
        )}
        <button type="button" onClick={handlePublish} disabled={!isDirty || saveState === 'saving'}>
          {saveState === 'saving' ? 'Publishing…' : 'Publish changes'}
        </button>
        {saveState === 'saved' && !isDirty && <span className="save-status">Published</span>}
      </div>
    </>
  )
}

export default function App() {
  const [status, setStatus] = useState('loading') // loading | anon | ready | error
  const [authView, setAuthView] = useState('login') // login | register
  const [displayName, setDisplayName] = useState(null)
  const [username, setUsername] = useState(null)
  const [email, setEmail] = useState(null)
  const [profileComplete, setProfileComplete] = useState(true)
  const [sites, setSites] = useState([])
  const [selectedSlug, setSelectedSlug] = useState(null)
  const [loadError, setLoadError] = useState(null)
  const [checkoutNotice, setCheckoutNotice] = useState(null) // null | 'success' | 'cancelled'
  const [activeTab, setActiveTabState] = useState(() => {
    const fromHash = window.location.hash.replace('#', '')
    return TABS.some((t) => t.key === fromHash) ? fromHash : 'overview'
  })

  // Keep the open tab in the URL (#profile, #deploy, ...) so a refresh stays put.
  function setActiveTab(tab) {
    setActiveTabState(tab)
    window.history.replaceState({}, '', `${window.location.pathname}${window.location.search}#${tab}`)
  }

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const notice = params.get('checkout')
    if (!notice) return
    setCheckoutNotice(notice)
    params.delete('checkout')
    const rest = params.toString()
    window.history.replaceState({}, '', window.location.pathname + (rest ? `?${rest}` : '') + window.location.hash)
  }, [])

  async function loadSites() {
    try {
      const data = await listSites()
      setSites(data.sites)
      if (data.sites.length > 0) setSelectedSlug(data.sites[0].slug)
      setStatus('ready')
    } catch (err) {
      setLoadError(err.message)
      setStatus('error')
    }
  }

  useEffect(() => {
    whoami()
      .then((data) => {
        setDisplayName(data.name || data.username)
        setUsername(data.username)
        setEmail(data.email)
        setProfileComplete(data.profile_complete !== false)
        loadSites()
      })
      .catch((err) => setStatus(err.status === 401 ? 'anon' : 'error'))
  }, [])

  async function handleLogout() {
    await logout().catch(() => {})
    setStatus('anon')
    setAuthView('login')
    setSites([])
    setSelectedSlug(null)
    setActiveTab('overview')
  }

  function handleAuthenticated() {
    setStatus('loading')
    whoami().then((d) => {
      setDisplayName(d.name || d.username)
      setUsername(d.username)
      setEmail(d.email)
      setProfileComplete(d.profile_complete !== false)
      loadSites()
    })
  }

  if (status === 'loading') return null
  if (status === 'anon') {
    return authView === 'register'
      ? <Register onRegistered={handleAuthenticated} onSwitchToLogin={() => setAuthView('login')} />
      : <Login onLoggedIn={handleAuthenticated} onSwitchToRegister={() => setAuthView('register')} />
  }
  if (status === 'error') return <div className="page error">Could not reach the backend. {loadError}</div>

  const selectedSite = sites.find((s) => s.slug === selectedSlug)
  const hasSite = sites.length > 0

  return (
    <div className={`page${hasSite ? ' has-bottom-nav' : ''}`}>
      <div className="topbar">
        <img src="/logo.png" alt="Vicinic" className="brand-logo" />
      </div>

      {!hasSite ? (
        <CreateSite onCreated={loadSites} />
      ) : (
        <>
          {sites.length > 1 && <SitePicker sites={sites} selected={selectedSlug} onSelect={setSelectedSlug} />}
          {selectedSite && activeTab === 'overview' && (
            <OverviewTab
              site={selectedSite}
              checkoutNotice={checkoutNotice}
              onSiteUpdated={(updated) => setSites((prev) => prev.map((s) => (s.slug === updated.slug ? updated : s)))}
            />
          )}
          {selectedSite && activeTab === 'edit' && <VisualEditor site={selectedSite} />}
          {selectedSite && activeTab === 'deploy' && (
            <DeployTab
              site={selectedSite}
              onSiteUpdated={(updated) => setSites((prev) => prev.map((s) => (s.slug === updated.slug ? updated : s)))}
              onGoToProfile={() => setActiveTab('profile')}
            />
          )}
          {activeTab === 'profile' && (
            <ProfileTab
              displayName={displayName}
              username={username}
              email={email}
              onLogout={handleLogout}
              onProfileCompleteChange={setProfileComplete}
              site={selectedSite}
              onSiteDeleted={(deletedSlug) => {
                setSites((prev) => {
                  const next = prev.filter((s) => s.slug !== deletedSlug)
                  setSelectedSlug(next.length > 0 ? next[0].slug : null)
                  return next
                })
                setActiveTab('overview')
              }}
            />
          )}
          <BottomNav active={activeTab} onSelect={setActiveTab} badges={profileComplete ? {} : { profile: true }} />
        </>
      )}
    </div>
  )
}
