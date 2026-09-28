import { useEffect, useState } from 'react'
import { NavLink, Route, Routes } from 'react-router-dom'
import {
  blogPostAction,
  deleteTemplate,
  getAnalytics,
  getBlogPost,
  listBlogPosts,
  listSites,
  listTemplates,
  login,
  logout,
  updateBlogPost,
  uploadTemplate,
  whoami,
} from './api.js'

function Login({ onLoggedIn }) {
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
        <h1>Vicinic Admin</h1>
        <p>Sign in with your staff account.</p>
        {error && <div className="error">{error}</div>}
        <label htmlFor="username">Username</label>
        <input id="username" type="text" value={username} onChange={(e) => setUsername(e.target.value)} required autoComplete="username" />
        <label htmlFor="password">Password</label>
        <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" />
        <button type="submit" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
      </form>
    </div>
  )
}

const PACKAGE_LABELS = { none: 'Free (no package)', starter: 'Starter Site', growth: 'Growth Hub', business_os: 'Business OS' }
const SUBSCRIPTION_LABELS = { none: 'None', pending: 'Pending', active: 'Active', cancelled: 'Cancelled' }
const DOMAIN_LABELS = { none: 'Not connected', pending: 'Pending', active: 'Active', error: 'Error' }

function StatTile({ label, value }) {
  return (
    <div className="stat-tile">
      <div className="stat-tile-value">{value}</div>
      <div className="stat-tile-label">{label}</div>
    </div>
  )
}

function BreakdownList({ title, counts, labels }) {
  const entries = Object.entries(counts)
  return (
    <div className="card">
      <h2>{title}</h2>
      {entries.length === 0 ? (
        <p>No data yet.</p>
      ) : (
        <ul className="breakdown-list">
          {entries.map(([key, count]) => (
            <li key={key}>
              <span>{labels[key] || key}</span>
              <strong>{count}</strong>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function Dashboard() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    getAnalytics()
      .then(setData)
      .catch((err) => setError(err.message))
  }, [])

  if (error) return <div className="card error">Could not load analytics: {error}</div>
  if (!data) return <div className="card">Loading analytics…</div>

  return (
    <>
      <div className="stat-grid">
        <StatTile label="Total sites" value={data.sites_total} />
        <StatTile label="Published" value={data.sites_published} />
        <StatTile label="Paid sites" value={data.sites_paid} />
        <StatTile label="Free sites" value={data.sites_free} />
        <StatTile label="Templates" value={data.templates_total} />
        <StatTile label="Domains registered" value={data.domain_purchases_registered} />
        <StatTile label="Active email routes" value={data.email_routes_active} />
      </div>
      <BreakdownList title="Sites by plan" counts={data.by_package} labels={PACKAGE_LABELS} />
      <BreakdownList title="Sites by subscription status" counts={data.by_subscription_status} labels={SUBSCRIPTION_LABELS} />
      <BreakdownList title="Sites by domain status" counts={data.by_domain_status} labels={DOMAIN_LABELS} />
    </>
  )
}

function SiteCard({ site }) {
  const rows = [
    ['Owner', site.owner_email ? `${site.owner} · ${site.owner_email}` : site.owner || '—'],
    ['Template', site.template],
    ['Subscription', SUBSCRIPTION_LABELS[site.subscription_status] || site.subscription_status],
    ['Domain', site.custom_domain ? `${site.custom_domain} (${DOMAIN_LABELS[site.domain_status] || site.domain_status})` : 'None'],
    ['Visitors (30 days)', site.visitors_30d],
    ['Custom pages', site.custom_pages],
    ['AI assistant', site.ai_assistant_enabled ? 'On' : 'Off'],
    ['WhatsApp', site.whatsapp_connected ? 'Connected' : 'Not connected'],
    ['Contact', [site.email, site.phone].filter(Boolean).join(' · ') || '—'],
    ['Created', new Date(site.created_at).toLocaleDateString()],
  ]
  return (
    <details className="site-card">
      <summary>
        <span className="site-card-name">{site.name}</span>
        <span className={`pill ${site.has_paid_plan ? 'pill-paid' : ''}`}>
          {site.has_paid_plan ? PACKAGE_LABELS[site.package] || 'Paid' : 'Free'}
        </span>
        {!site.is_published && <span className="pill">Unpublished</span>}
      </summary>
      <ul className="breakdown-list">
        {rows.map(([label, value]) => (
          <li key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </li>
        ))}
      </ul>
    </details>
  )
}

function Sites() {
  const [sites, setSites] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    listSites()
      .then((data) => setSites(data.sites))
      .catch((err) => setError(err.message))
  }, [])

  if (error) return <div className="card error">Could not load sites: {error}</div>
  if (!sites) return <div className="card">Loading sites…</div>

  const paid = sites.filter((s) => s.has_paid_plan)
  const free = sites.filter((s) => !s.has_paid_plan)
  return (
    <>
      {[
        ['Paid plans', paid],
        ['Free', free],
      ].map(([title, list]) => (
        <div className="card" key={title}>
          <h2>
            {title} <span className="muted">({list.length})</span>
          </h2>
          {list.length === 0 ? <p>None yet.</p> : list.map((site) => <SiteCard key={site.slug} site={site} />)}
        </div>
      ))}
    </>
  )
}

const BLOG_STATUS_LABELS = { draft: 'Draft', approved: 'Approved — goes live within the hour', published: 'Live', rejected: 'Rejected' }

function timeLeft(iso) {
  const ms = new Date(iso) - Date.now()
  if (ms <= 0) return 'any minute now'
  const hours = Math.floor(ms / 3600000)
  return hours >= 1 ? `in ${hours}h ${Math.floor((ms % 3600000) / 60000)}m` : `in ${Math.ceil(ms / 60000)}m`
}

function BlogEditor({ postId, onChanged, onClose }) {
  const [post, setPost] = useState(null)
  const [form, setForm] = useState(null)
  const [editing, setEditing] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  function load(data) {
    setPost(data.post)
    setForm({ title: data.post.title, summary: data.post.summary, tags: data.post.tags, body: data.post.body })
  }

  useEffect(() => {
    getBlogPost(postId)
      .then(load)
      .catch((err) => setError(err.message))
  }, [postId])

  async function run(fn) {
    setBusy(true)
    setError(null)
    try {
      load(await fn())
      setEditing(false)
      onChanged()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  if (error && !post) return <div className="card error">{error}</div>
  if (!post) return <div className="card">Loading post…</div>
  const locked = post.status === 'published'

  return (
    <div className="card blog-editor">
      <button type="button" className="link-button" onClick={onClose}>← All posts</button>
      <p className="muted">
        {post.category} · {BLOG_STATUS_LABELS[post.status]}
        {post.status === 'draft' && (post.auto_publish_at ? ` · auto-publishes ${timeLeft(post.auto_publish_at)}` : ' · on hold')}
      </p>
      {error && <div className="error">{error}</div>}
      {editing ? (
        <>
          {['title', 'summary', 'tags'].map((field) => (
            <div key={field}>
              <label htmlFor={`blog-${field}`}>{field[0].toUpperCase() + field.slice(1)}</label>
              <input
                id={`blog-${field}`}
                type="text"
                value={form[field]}
                onChange={(e) => setForm({ ...form, [field]: e.target.value })}
              />
            </div>
          ))}
          <label htmlFor="blog-body">Body (Markdown)</label>
          <textarea id="blog-body" rows={22} value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} />
          <div className="button-row">
            <button type="button" disabled={busy} onClick={() => run(() => updateBlogPost(post.id, form))}>
              {busy ? 'Saving…' : 'Save'}
            </button>
            <button type="button" className="link-button" onClick={() => setEditing(false)}>Cancel</button>
          </div>
        </>
      ) : (
        <>
          <h1 className="blog-title">{post.title}</h1>
          {post.summary && <p className="blog-summary">{post.summary}</p>}
          <article className="blog-preview" dangerouslySetInnerHTML={{ __html: post.body_html }} />
          {!locked && (
            <div className="button-row">
              {post.status !== 'approved' && (
                <button type="button" disabled={busy} onClick={() => run(() => blogPostAction(post.id, 'approve'))}>Approve & publish</button>
              )}
              <button type="button" className="secondary" disabled={busy} onClick={() => setEditing(true)}>Edit</button>
              {post.status === 'draft' && post.auto_publish_at && (
                <button type="button" className="secondary" disabled={busy} onClick={() => run(() => blogPostAction(post.id, 'hold'))}>Hold</button>
              )}
              {(post.status !== 'draft' || !post.auto_publish_at) && (
                <button type="button" className="secondary" disabled={busy} onClick={() => run(() => blogPostAction(post.id, 'resume'))}>Back to review</button>
              )}
              {post.status !== 'rejected' && (
                <button type="button" className="danger" disabled={busy} onClick={() => run(() => blogPostAction(post.id, 'reject'))}>Reject</button>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}

function Blog() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [openId, setOpenId] = useState(null)

  function refresh() {
    listBlogPosts()
      .then(setData)
      .catch((err) => setError(err.message))
  }

  useEffect(refresh, [])

  if (openId) return <BlogEditor postId={openId} onChanged={refresh} onClose={() => setOpenId(null)} />
  if (error) return <div className="card error">Could not load posts: {error}</div>
  if (!data) return <div className="card">Loading posts…</div>

  return (
    <div className="card">
      <h2>Blog</h2>
      <p className="muted">
        AI drafts arrive Mon, Wed and Fri. Anything you don't approve, hold or reject goes live on its own after{' '}
        {data.review_hours} hours.
      </p>
      {data.posts.length === 0 ? (
        <p>No drafts yet.</p>
      ) : (
        <ul className="blog-list">
          {data.posts.map((p) => (
            <li key={p.id}>
              <button type="button" className="blog-row" onClick={() => setOpenId(p.id)}>
                <strong>{p.title}</strong>
                <span className="muted">
                  {p.category} · {BLOG_STATUS_LABELS[p.status]}
                  {p.status === 'draft' && (p.auto_publish_at ? ` · auto-publishes ${timeLeft(p.auto_publish_at)}` : ' · on hold')}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
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

function TemplateList({ templates, onDelete, deletingId, deleteError }) {
  return (
    <div className="card">
      <h2>Existing templates</h2>
      {deleteError && <div className="error">{deleteError}</div>}
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
              <th></th>
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
                <td>
                  <button
                    type="button"
                    className="link-button"
                    onClick={() => onDelete(t)}
                    disabled={deletingId === t.id}
                  >
                    {deletingId === t.id ? 'Deleting…' : 'Delete'}
                  </button>
                </td>
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
  const [deletingId, setDeletingId] = useState(null)
  const [deleteError, setDeleteError] = useState(null)

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

  async function handleDelete(template) {
    if (!window.confirm(`Delete "${template.name}"? This can't be undone.`)) return
    setDeletingId(template.id)
    setDeleteError(null)
    try {
      await deleteTemplate(template.id)
      await refresh()
    } catch (err) {
      setDeleteError(err.message)
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <>
      {loadError && <div className="card error">Could not load templates: {loadError}</div>}
      <UploadForm onUploaded={refresh} />
      <TemplateList templates={templates} onDelete={handleDelete} deletingId={deletingId} deleteError={deleteError} />
    </>
  )
}

export default function App() {
  const [status, setStatus] = useState('loading') // loading | anon | ready | error
  const [loadError, setLoadError] = useState(null)
  const [navOpen, setNavOpen] = useState(false)

  function checkAuth() {
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
  }

  useEffect(checkAuth, [])

  async function handleLogout() {
    await logout().catch(() => {})
    setStatus('anon')
  }

  if (status === 'loading') return <div className="page">Loading…</div>
  if (status === 'anon') return <Login onLoggedIn={() => setStatus('ready')} />
  if (status === 'error') return <div className="page error">Could not reach the backend. {loadError}</div>

  return (
    <div className="layout">
      <div className="topbar-mobile">
        <button type="button" className="hamburger" onClick={() => setNavOpen(true)} aria-label="Open menu">☰</button>
        <span>Vicinic Admin</span>
      </div>
      {navOpen && <div className="sidebar-backdrop" onClick={() => setNavOpen(false)} />}
      <aside className={`sidebar${navOpen ? ' open' : ''}`}>
        <h1>Vicinic Admin</h1>
        <nav onClick={() => setNavOpen(false)}>
          <NavLink to="/" end>
            Dashboard
          </NavLink>
          <NavLink to="/sites">Sites</NavLink>
          <NavLink to="/blog">Blog</NavLink>
          <NavLink to="/templates">Templates</NavLink>
        </nav>
        <button type="button" className="link-button" onClick={handleLogout}>Sign out</button>
      </aside>
      <main className="main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/sites" element={<Sites />} />
          <Route path="/blog" element={<Blog />} />
          <Route path="/templates" element={<Templates />} />
        </Routes>
      </main>
    </div>
  )
}
