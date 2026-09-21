import { useEffect, useRef, useState } from 'react'
import {
  API_BASE,
  checkDomainAvailability,
  checkout,
  clearDraft,
  connectDomain,
  createEmailRoute,
  createSite,
  deleteEmailRoute,
  disconnectDomain,
  getDomain,
  getSiteSlots,
  listEmailRoutes,
  listPackages,
  listPublicTemplates,
  listSites,
  loadDraft,
  login,
  logout,
  purchaseDomain,
  redirectToPayFast,
  register,
  saveSiteSlots,
  storeDraft,
  updateSite,
  whoami,
} from './api.js'

// Tags whose text can never be wrapped for click-to-edit (a <title> or
// <option> can only ever hold plain text) — mirrors
// backend/builder/views.py's NON_INLINE_EDITABLE_TAGS/_slot_tag, both
// reading the same "<tagname> preview" prefix slot_extractor.py puts in
// every slot's label.
const NON_INLINE_TAGS = new Set(['title', 'option', 'textarea', 'noscript', '[document]'])

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
        <h1>Vicinic — Edit your site</h1>
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
        <h1>Vicinic — Create an account</h1>
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

  return (
    <form className="card" onSubmit={handleSubmit}>
      <h2>Create your site</h2>
      <p>Pick a template and we'll set it up — every bit of its text is yours to edit right away.</p>
      {error && <div className="error">{error}</div>}
      {templatesError && <div className="error">Could not load templates: {templatesError}</div>}
      {noTemplates && <div className="error">No templates are available yet — check back soon.</div>}

      <label htmlFor="site-name">Site name</label>
      <input id="site-name" type="text" value={siteName} onChange={(e) => setSiteName(e.target.value)} required />

      <label htmlFor="template">Template</label>
      <select
        id="template"
        value={templateSlug}
        onChange={(e) => setTemplateSlug(e.target.value)}
        required
        disabled={!templates || noTemplates}
      >
        {!templates && <option value="">Loading…</option>}
        {templates && templates.map((t) => (
          <option key={t.slug} value={t.slug}>{t.name}</option>
        ))}
      </select>

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
      <p>Your site currently shows a small credit linking back to us. Subscribing to a package removes it.</p>
      {site.subscription_status === 'pending' && (
        <div className="notice">Payment pending — this can take a minute to confirm after you pay.</div>
      )}
      {error && <div className="error">{error}</div>}
      {packagesError && <div className="error">Could not load packages: {packagesError}</div>}

      <label htmlFor="package">Package</label>
      <select id="package" value={packageId} onChange={(e) => setPackageId(e.target.value)} disabled={!packages}>
        {!packages && <option value="">Loading…</option>}
        {packages && packages.map((p) => (
          <option key={p.id} value={p.id}>{p.label} — R{p.monthly}/month (R{p.setup} once-off setup)</option>
        ))}
      </select>

      <button type="submit" disabled={busy || !packageId}>
        {busy ? 'Redirecting to PayFast…' : 'Subscribe with PayFast'}
      </button>
    </form>
  )
}

function BuyDomainFields({ site }) {
  const [domainInput, setDomainInput] = useState('')
  const [checkResult, setCheckResult] = useState(null) // null | {available, price_zar} | {available: false, reason}
  const [checking, setChecking] = useState(false)
  const [showRegistrantForm, setShowRegistrantForm] = useState(false)
  const [registrant, setRegistrant] = useState({
    name: '', email: '', phone: '', street: '', city: '', state: '', postal_code: '', country_code: 'ZA',
  })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  function setRegistrantField(key, value) {
    setRegistrant((prev) => ({ ...prev, [key]: value }))
  }

  async function handleCheck(e) {
    e.preventDefault()
    setChecking(true)
    setError(null)
    setCheckResult(null)
    setShowRegistrantForm(false)
    try {
      const data = await checkDomainAvailability(site.slug, domainInput.trim())
      setCheckResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setChecking(false)
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
        checkResult.domain,
        {
          name: registrant.name,
          email: registrant.email,
          phone: registrant.phone,
          address: {
            street: registrant.street,
            city: registrant.city,
            state: registrant.state,
            postal_code: registrant.postal_code,
            country_code: registrant.country_code,
          },
        },
        `${base}?checkout=success`,
        `${base}?checkout=cancelled`
      )
      redirectToPayFast(data.process_url, data.fields)
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <>
      {error && <div className="error">{error}</div>}

      <form onSubmit={handleCheck}>
        <label htmlFor="buy-domain">Domain you want</label>
        <input
          id="buy-domain"
          type="text"
          placeholder="mybusiness.com"
          value={domainInput}
          onChange={(e) => {
            setDomainInput(e.target.value)
            setCheckResult(null)
          }}
          disabled={checking}
          required
        />
        <button type="submit" disabled={checking || !domainInput.trim()}>
          {checking ? 'Checking…' : 'Check availability'}
        </button>
      </form>

      {checkResult && !checkResult.available && (
        <div className="notice">{checkResult.reason}</div>
      )}

      {checkResult && checkResult.available && !showRegistrantForm && (
        <div className="notice">
          <strong>{checkResult.domain}</strong> is available for <strong>R{checkResult.price_zar}</strong> (first year).
          {' '}
          <button type="button" className="link-button" onClick={() => setShowRegistrantForm(true)}>
            Buy this domain
          </button>
        </div>
      )}

      {checkResult && checkResult.available && showRegistrantForm && (
        <form onSubmit={handleBuy}>
          <p className="field-hint">
            Domain registries require real contact details for the registrant — this is who legally owns {checkResult.domain}.
          </p>
          <label htmlFor="registrant-name">Full name or business name</label>
          <input id="registrant-name" type="text" value={registrant.name} onChange={(e) => setRegistrantField('name', e.target.value)} required />
          <label htmlFor="registrant-email">Email</label>
          <input id="registrant-email" type="email" value={registrant.email} onChange={(e) => setRegistrantField('email', e.target.value)} required />
          <label htmlFor="registrant-phone">Phone (with country code, e.g. +27821234567)</label>
          <input id="registrant-phone" type="text" value={registrant.phone} onChange={(e) => setRegistrantField('phone', e.target.value)} required />
          <label htmlFor="registrant-street">Street address</label>
          <input id="registrant-street" type="text" value={registrant.street} onChange={(e) => setRegistrantField('street', e.target.value)} required />
          <label htmlFor="registrant-city">City</label>
          <input id="registrant-city" type="text" value={registrant.city} onChange={(e) => setRegistrantField('city', e.target.value)} required />
          <label htmlFor="registrant-state">Province/State (optional)</label>
          <input id="registrant-state" type="text" value={registrant.state} onChange={(e) => setRegistrantField('state', e.target.value)} />
          <label htmlFor="registrant-postal">Postal code</label>
          <input id="registrant-postal" type="text" value={registrant.postal_code} onChange={(e) => setRegistrantField('postal_code', e.target.value)} required />
          <label htmlFor="registrant-country">Country code (2 letters, e.g. ZA)</label>
          <input
            id="registrant-country"
            type="text"
            maxLength={2}
            value={registrant.country_code}
            onChange={(e) => setRegistrantField('country_code', e.target.value.toUpperCase())}
            required
          />
          <button type="submit" disabled={busy}>
            {busy ? 'Redirecting to PayFast…' : `Pay R${checkResult.price_zar} with PayFast`}
          </button>
        </form>
      )}
    </>
  )
}

function DomainSection({ site, onSiteUpdated }) {
  const [domainInput, setDomainInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [mode, setMode] = useState('connect') // 'connect' | 'buy'

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
          <div className="domain-mode-toggle">
            <button type="button" className={mode === 'connect' ? '' : 'link-button'} onClick={() => setMode('connect')}>
              I already own a domain
            </button>
            <button type="button" className={mode === 'buy' ? '' : 'link-button'} onClick={() => setMode('buy')}>
              Buy a new domain
            </button>
          </div>
          {mode === 'connect' && (
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
          )}
          {mode === 'buy' && <BuyDomainFields site={site} />}
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

function EmailRoutingSection({ site }) {
  const domainReady = site.domain_status === 'active'
  const disabled = !domainReady
  const [routes, setRoutes] = useState(null)
  const [error, setError] = useState(null)
  const [fromLocal, setFromLocal] = useState('')
  const [toAddress, setToAddress] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!domainReady) {
      setRoutes([])
      return
    }
    listEmailRoutes(site.slug)
      .then((data) => setRoutes(data.email_routes))
      .catch((err) => setError(err.message))
  }, [site.slug, domainReady])

  async function handleAdd(e) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const fromAddress = `${fromLocal.trim()}@${site.custom_domain}`
      const data = await createEmailRoute(site.slug, fromAddress, toAddress.trim())
      setRoutes((prev) => [...(prev || []), data.route])
      setFromLocal('')
      setToAddress('')
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
      {!domainReady && <p className="notice">Connect and activate your custom domain above first.</p>}
      {error && <div className="error">{error}</div>}

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
        <input
          id="route-to"
          type="email"
          placeholder="you@gmail.com"
          value={toAddress}
          onChange={(e) => setToAddress(e.target.value)}
          disabled={disabled || busy}
          required
        />
        <button type="submit" disabled={disabled || busy || !fromLocal.trim() || !toAddress.trim()}>
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
    </div>
  )
}

function DeployTab({ site, onSiteUpdated }) {
  // UpgradeCard (subscription plans) is intentionally left out for now —
  // plans aren't finalized yet, so domain connect/buy and email routing
  // below are open to every site rather than gated behind one. Bring it
  // back here once there's a plan to actually sell.
  return (
    <>
      <DomainSection site={site} onSiteUpdated={onSiteUpdated} />
      <EmailRoutingSection site={site} />
    </>
  )
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

      <div className="card">
        <h2>{site.name}</h2>
        <p>
          Status: <strong>{site.subscription_status === 'active' ? 'Paid plan' : 'Free plan'}</strong>
          {site.subscription_status === 'pending' && ' (payment pending)'}
        </p>
        <p>
          Live at <a href={`${API_BASE}/${site.slug}/`} target="_blank" rel="noreferrer">{`${API_BASE}/${site.slug}/`}</a>
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
        <input id="site-profile-phone" type="text" value={form.phone} onChange={(e) => setField('phone', e.target.value)} />

        <label htmlFor="site-profile-whatsapp">WhatsApp number</label>
        <input
          id="site-profile-whatsapp"
          type="text"
          value={form.whatsapp_number}
          onChange={(e) => setField('whatsapp_number', e.target.value)}
        />

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

function ProfileTab({ displayName, username, email, onLogout }) {
  return (
    <div className="card">
      <h2>Profile</h2>
      <p><strong>Name:</strong> {displayName}</p>
      <p><strong>Username:</strong> {username}</p>
      <p><strong>Email:</strong> {email}</p>
      <button type="button" className="link-button" onClick={onLogout}>Sign out</button>
    </div>
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

function BottomNav({ active, onSelect }) {
  return (
    <nav className="bottom-nav">
      {TABS.map((tab) => (
        <button
          key={tab.key}
          type="button"
          className={`bottom-nav-item${active === tab.key ? ' active' : ''}`}
          onClick={() => onSelect(tab.key)}
        >
          {tab.icon}
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

function VisualEditor({ site }) {
  const [groups, setGroups] = useState(null)
  const [loadError, setLoadError] = useState(null)
  const [activePage, setActivePage] = useState(null)
  const [drafts, setDrafts] = useState({})
  const [saveState, setSaveState] = useState('idle') // idle | saving | saved | error
  const [saveError, setSaveError] = useState(null)
  const iframeRef = useRef(null)

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

  useEffect(() => {
    function handleMessage(e) {
      if (iframeRef.current && e.source !== iframeRef.current.contentWindow) return
      const msg = e.data
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
      const data = await saveSiteSlots(site.slug, drafts)
      setGroups(data.groups)
      clearDraft(site.slug)
      setDrafts({})
      setSaveState('saved')
    } catch (err) {
      setSaveError(err.message)
      setSaveState('error')
    }
  }

  function handleDiscard() {
    clearDraft(site.slug)
    setDrafts({})
    setSaveState('idle')
    iframeRef.current?.contentWindow?.location.reload()
  }

  if (loadError) return <div className="card error">Could not load this site's text: {loadError}</div>
  if (!groups || activePage === null) return null

  const pages = groups.filter((g) => g.page !== null)
  const isFreeTier = site.subscription_status !== 'active'
  const isDirty = Object.keys(drafts).length > 0
  const previewUrl = `${API_BASE}/${site.slug}/${activePage ? `${activePage}/` : ''}?vicinic_edit=1`
  const fallbackSlots = groups
    .filter((g) => g.page === null || g.page === activePage)
    .flatMap((g) => g.slots.filter((s) => NON_INLINE_TAGS.has(slotTag(s.label))))

  return (
    <>
      {!isFreeTier && pages.length > 1 && (
        <div className="card site-picker">
          <label htmlFor="preview-page">Page</label>
          <select id="preview-page" value={activePage} onChange={(e) => setActivePage(e.target.value)}>
            {pages.map((g) => (
              <option key={g.page} value={g.page}>{g.label}</option>
            ))}
          </select>
        </div>
      )}
      {isFreeTier && pages.length > 1 && (
        <div className="card notice">
          Free sites can only edit the homepage — upgrade on the Deploy tab to edit every page.
        </div>
      )}

      <div className="card notice">Click any text on the preview below to edit it in place.</div>

      <div className="visual-editor-frame">
        <iframe ref={iframeRef} src={previewUrl} title="Site preview" onLoad={sendDraftToPreview} />
      </div>

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
  const [sites, setSites] = useState([])
  const [selectedSlug, setSelectedSlug] = useState(null)
  const [loadError, setLoadError] = useState(null)
  const [checkoutNotice, setCheckoutNotice] = useState(null) // null | 'success' | 'cancelled'
  const [activeTab, setActiveTab] = useState('overview')

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const notice = params.get('checkout')
    if (!notice) return
    setCheckoutNotice(notice)
    params.delete('checkout')
    const rest = params.toString()
    window.history.replaceState({}, '', window.location.pathname + (rest ? `?${rest}` : ''))
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
        <h1>Vicinic</h1>
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
            />
          )}
          {activeTab === 'profile' && (
            <ProfileTab displayName={displayName} username={username} email={email} onLogout={handleLogout} />
          )}
          <BottomNav active={activeTab} onSelect={setActiveTab} />
        </>
      )}
    </div>
  )
}
