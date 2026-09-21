import { useEffect, useState } from 'react'
import { NavLink, Route, Routes } from 'react-router-dom'
import { listTemplates, loginUrl, uploadTemplate, whoami } from './api.js'

function LoginPrompt() {
  return (
    <div className="page login-prompt">
      <div className="card">
        <h1>Vicinic Admin</h1>
        <p>Sign in with your superuser account.</p>
        <a href={loginUrl()}>Sign in</a>
      </div>
    </div>
  )
}

function Dashboard() {
  return (
    <div className="card">
      <h2>Dashboard</h2>
      <p>Placeholder — overview of sites, templates, and activity goes here.</p>
    </div>
  )
}

function Sites() {
  return (
    <div className="card">
      <h2>Sites</h2>
      <p>Placeholder — list of customer sites goes here.</p>
    </div>
  )
}

function UploadForm({ onUploaded }) {
  const [name, setName] = useState('')
  const [file, setFile] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!name || !file) return
    setBusy(true)
    setError(null)
    try {
      await uploadTemplate(name, file)
      setName('')
      setFile(null)
      e.target.reset()
      onUploaded()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="card" onSubmit={handleSubmit}>
      <h2>Add a template</h2>
      <p>Upload a static HTML template zip. It's converted via Templify and becomes available for customer sites to use — no code deploy needed.</p>
      {error && <div className="error">{error}</div>}
      <label htmlFor="name">Template name</label>
      <input id="name" type="text" value={name} onChange={(e) => setName(e.target.value)} required />
      <label htmlFor="zip">Template zip</label>
      <input id="zip" type="file" accept=".zip" onChange={(e) => setFile(e.target.files[0])} required />
      <button type="submit" disabled={busy}>
        {busy ? 'Converting…' : 'Convert & add template'}
      </button>
    </form>
  )
}

function TemplateList({ templates }) {
  return (
    <div className="card">
      <h2>Existing templates</h2>
      {templates.length === 0 ? (
        <p>No templates yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Slug</th>
              <th>Pages</th>
              <th>Slots</th>
              <th>Added</th>
            </tr>
          </thead>
          <tbody>
            {templates.map((t) => (
              <tr key={t.id}>
                <td>{t.name}</td>
                <td>{t.slug}</td>
                <td>{t.pages}</td>
                <td>{t.slots}</td>
                <td>{new Date(t.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

function Templates() {
  const [templates, setTemplates] = useState([])
  const [loadError, setLoadError] = useState(null)

  async function refresh() {
    try {
      const data = await listTemplates()
      setTemplates(data.templates)
    } catch (err) {
      setLoadError(err.message)
    }
  }

  useEffect(() => {
    refresh()
  }, [])

  return (
    <>
      {loadError && <div className="card error">Could not load templates: {loadError}</div>}
      <UploadForm onUploaded={refresh} />
      <TemplateList templates={templates} />
    </>
  )
}

export default function App() {
  const [status, setStatus] = useState('loading') // loading | anon | ready | error
  const [loadError, setLoadError] = useState(null)

  useEffect(() => {
    whoami()
      .then(() => setStatus('ready'))
      .catch((err) => {
        if (err.status === 401) {
          setStatus('anon')
        } else {
          setLoadError(err.message)
          setStatus('error')
        }
      })
  }, [])

  if (status === 'loading') return null
  if (status === 'anon') return <LoginPrompt />
  if (status === 'error') return <div className="page error">Could not reach the backend. {loadError}</div>

  return (
    <div className="layout">
      <aside className="sidebar">
        <h1>Vicinic Admin</h1>
        <nav>
          <NavLink to="/" end>
            Dashboard
          </NavLink>
          <NavLink to="/sites">Sites</NavLink>
          <NavLink to="/templates">Templates</NavLink>
        </nav>
      </aside>
      <main className="main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/sites" element={<Sites />} />
          <Route path="/templates" element={<Templates />} />
        </Routes>
      </main>
    </div>
  )
}
