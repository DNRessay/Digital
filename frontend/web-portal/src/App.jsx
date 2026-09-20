import { useEffect, useMemo, useState } from 'react'
import { getSiteSlots, listPublicTemplates, listSites, login, logout, saveSiteSlots, signup, whoami } from './api.js'

function Login({ onLoggedIn, onSwitchToSignup }) {
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
          Don't have a site yet? <button type="button" className="link-button" onClick={onSwitchToSignup}>Create one</button>
        </p>
      </form>
    </div>
  )
}

function Signup({ onSignedUp, onSwitchToLogin }) {
  const [templates, setTemplates] = useState(null)
  const [templatesError, setTemplatesError] = useState(null)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
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
      await signup(username, password, siteName, templateSlug)
      onSignedUp()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const noTemplates = templates && templates.length === 0

  return (
    <div className="page login-prompt">
      <form className="card" onSubmit={handleSubmit}>
        <h1>Vicinic — Create your site</h1>
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

        <label htmlFor="signup-username">Username</label>
        <input id="signup-username" type="text" value={username} onChange={(e) => setUsername(e.target.value)} required autoComplete="username" />

        <label htmlFor="signup-password">Password</label>
        <input id="signup-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="new-password" />

        <button type="submit" disabled={busy || noTemplates || !templateSlug}>
          {busy ? 'Creating your site…' : 'Create account & site'}
        </button>
        <p className="switch-auth-mode">
          Already have an account? <button type="button" className="link-button" onClick={onSwitchToLogin}>Sign in</button>
        </p>
      </form>
    </div>
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

function SiteEditor({ site }) {
  const [groups, setGroups] = useState(null)
  const [values, setValues] = useState({})
  const [loadError, setLoadError] = useState(null)
  const [saveState, setSaveState] = useState('idle') // idle | saving | saved | error
  const [saveError, setSaveError] = useState(null)

  useEffect(() => {
    setGroups(null)
    setSaveState('idle')
    getSiteSlots(site.slug)
      .then((data) => {
        setGroups(data.groups)
        const initial = {}
        for (const group of data.groups) {
          for (const slot of group.slots) {
            initial[slot.key] = slot.value
          }
        }
        setValues(initial)
      })
      .catch((err) => setLoadError(err.message))
  }, [site.slug])

  const isDirty = useMemo(() => {
    if (!groups) return false
    return groups.some((g) => g.slots.some((s) => values[s.key] !== s.value))
  }, [groups, values])

  async function handleSave() {
    setSaveState('saving')
    setSaveError(null)
    try {
      const data = await saveSiteSlots(site.slug, values)
      setGroups(data.groups)
      setSaveState('saved')
    } catch (err) {
      setSaveError(err.message)
      setSaveState('error')
    }
  }

  if (loadError) return <div className="card error">Could not load this site's text: {loadError}</div>
  if (!groups) return null

  return (
    <>
      {groups.map((group) => (
        <div className="card" key={group.page ?? '__shared__'}>
          <h2>{group.label}</h2>
          {group.slots.map((slot) => (
            <SlotField
              key={slot.key}
              slot={slot}
              value={values[slot.key] ?? ''}
              onChange={(v) => setValues((prev) => ({ ...prev, [slot.key]: v }))}
            />
          ))}
        </div>
      ))}

      <div className="save-bar">
        {saveError && <div className="error">{saveError}</div>}
        <button type="button" onClick={handleSave} disabled={!isDirty || saveState === 'saving'}>
          {saveState === 'saving' ? 'Saving…' : 'Save changes'}
        </button>
        {saveState === 'saved' && !isDirty && <span className="save-status">Saved</span>}
      </div>
    </>
  )
}

export default function App() {
  const [status, setStatus] = useState('loading') // loading | anon | ready | error
  const [authView, setAuthView] = useState('login') // login | signup
  const [username, setUsername] = useState(null)
  const [sites, setSites] = useState([])
  const [selectedSlug, setSelectedSlug] = useState(null)
  const [loadError, setLoadError] = useState(null)

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
        setUsername(data.username)
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
  }

  function handleAuthenticated() {
    setStatus('loading')
    whoami().then((d) => { setUsername(d.username); loadSites() })
  }

  if (status === 'loading') return null
  if (status === 'anon') {
    return authView === 'signup'
      ? <Signup onSignedUp={handleAuthenticated} onSwitchToLogin={() => setAuthView('login')} />
      : <Login onLoggedIn={handleAuthenticated} onSwitchToSignup={() => setAuthView('signup')} />
  }
  if (status === 'error') return <div className="page error">Could not reach the backend. {loadError}</div>

  const selectedSite = sites.find((s) => s.slug === selectedSlug)

  return (
    <div className="page">
      <div className="topbar">
        <h1>Edit your site</h1>
        <div className="topbar-user">
          <span>{username}</span>
          <button type="button" className="link-button" onClick={handleLogout}>Sign out</button>
        </div>
      </div>

      {sites.length === 0 && (
        <div className="card">No site has been set up for your account yet — get in touch with us.</div>
      )}

      <SitePicker sites={sites} selected={selectedSlug} onSelect={setSelectedSlug} />

      {selectedSite && <SiteEditor site={selectedSite} />}
    </div>
  )
}
