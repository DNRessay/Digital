import { useEffect, useState } from 'react'
import { NavLink, Route, Routes } from 'react-router-dom'
import {
  blogPostAction,
  browseBlogNews,
  generateBlogPost,
  suggestBlogIdeas,
  deleteTemplate,
  getAnalytics,
  getBlogPost,
  listBlogPosts,
  listSites,
  listTemplates,
  setSitePlan,
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

function SitePlan({ site, onChanged }) {
  const current = site.has_paid_plan ? site.package : ''
  const [value, setValue] = useState(current)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  async function save() {
    const name = value ? PACKAGE_LABELS[value] : 'the free tier'
    if (!window.confirm(`Move ${site.name} to ${name}? It takes effect immediately, without a PayFast payment.`)) return
    setBusy(true)
    setError(null)
    try {
      await setSitePlan(site.slug, value)
      onChanged()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="site-plan">
      <label htmlFor={`plan-${site.slug}`}>Plan</label>
      <div className="site-plan-row">
        <select id={`plan-${site.slug}`} value={value} onChange={(e) => setValue(e.target.value)} disabled={busy}>
          <option value="">Free (no package)</option>
          <option value="starter">Starter Site</option>
          <option value="growth">Growth Hub</option>
          <option value="business_os">Business OS</option>
        </select>
        <button type="button" disabled={busy || value === current} onClick={save}>
          {busy ? 'Saving…' : 'Change plan'}
        </button>
      </div>
      {error && <div className="error">{error}</div>}
    </div>
  )
}

function SiteCard({ site, onChanged }) {
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
      <SitePlan site={site} onChanged={onChanged} />
    </details>
  )
}

function Sites() {
  const [sites, setSites] = useState(null)
  const [error, setError] = useState(null)

  function refresh() {
    listSites()
      .then((data) => setSites(data.sites))
      .catch((err) => setError(err.message))
  }

  useEffect(refresh, [])

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
          {list.length === 0 ? <p>None yet.</p> : list.map((site) => <SiteCard key={site.slug} site={site} onChanged={refresh} />)}
        </div>
      ))}
    </>
  )
}

const BLOG_STATUS_LABELS = {
  generating: 'Researching & writing…',
  failed: 'Failed',
  draft: 'Draft', approved: 'Approved — publishing to the blog',
  published: 'Live',
  rejected: 'Rejected',
}

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

  if (post.status === 'generating' || post.status === 'failed') {
    return (
      <div className="card blog-editor">
        <button type="button" className="link-button" onClick={onClose}>← All posts</button>
        <h1 className="blog-title">{post.title}</h1>
        {post.status === 'generating' ? (
          <p>Researching and writing — this takes a few minutes. It'll show up as a draft in the list.</p>
        ) : (
          <>
            <div className="error">{post.error || 'Something went wrong.'}</div>
            <div className="button-row">
              <button type="button" disabled={busy} onClick={() => run(() => blogPostAction(post.id, 'retry'))}>Try again</button>
              <button type="button" className="danger" disabled={busy} onClick={() => run(() => blogPostAction(post.id, 'reject'))}>Discard</button>
            </div>
          </>
        )}
        {post.instructions && <p className="muted">Your instructions: {post.instructions}</p>}
      </div>
    )
  }

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

const MAX_PICKS = 5

function BlogComposer({ categories = [], onStarted }) {
  const [category, setCategory] = useState(categories[0]?.key || '')
  const [postType, setPostType] = useState('deep')
  const [news, setNews] = useState(null)
  const [picked, setPicked] = useState([])
  const [ideas, setIdeas] = useState(null)
  const [links, setLinks] = useState('')
  const [instructions, setInstructions] = useState('')
  const [busy, setBusy] = useState(null) // news | ideas | write
  const [error, setError] = useState(null)

  async function run(kind, fn) {
    setBusy(kind)
    setError(null)
    try {
      await fn()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(null)
    }
  }

  function changeCategory(key) {
    setCategory(key)
    setNews(null)
    setPicked([])
    setIdeas(null)
  }

  function toggle(id) {
    setPicked((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : cur.length < MAX_PICKS ? [...cur, id] : cur))
  }

  const loadNews = () =>
    run('news', async () => {
      const data = await browseBlogNews(category)
      setNews(data.items)
      setPicked([])
      setIdeas(null)
    })

  const loadIdeas = () =>
    run('ideas', async () => {
      const data = await suggestBlogIdeas(category, news || [], instructions)
      if (!news) setNews(data.items)
      setIdeas({ list: data.ideas, items: data.items })
    })

  function useIdea(idea) {
    setPicked(idea.items.slice(0, MAX_PICKS).map((n) => ideas.items[n].id))
    setInstructions(`Write "${idea.title}". ${idea.angle}`)
  }

  const newsItem = (item) => (
    <li key={item.id}>
      <label className="news-item">
        <input type="checkbox" checked={picked.includes(item.id)} onChange={() => toggle(item.id)} />
        <span>
          <span className="news-title">
            {picked.includes(item.id) && <span className="pill pill-paid">{picked.indexOf(item.id) + 1}</span>} {item.title}
          </span>
          <span className="muted">
            {item.source}
            {item.published && ` · ${new Date(item.published).toLocaleDateString()}`} ·{' '}
            <a href={item.url} target="_blank" rel="noreferrer">open</a>
          </span>
        </span>
      </label>
    </li>
  )
  const papers = (news || []).filter((i) => i.is_paper)
  const stories = (news || []).filter((i) => !i.is_paper)

  const write = () =>
    run('write', async () => {
      const items = (news || []).filter((i) => picked.includes(i.id))
      items.sort((a, b) => picked.indexOf(a.id) - picked.indexOf(b.id))
      const urls = links.split(/\s+/).filter((u) => /^https?:\/\//.test(u))
      await generateBlogPost({ category, post_type: postType, items, urls, instructions })
      setPicked([])
      setLinks('')
      setInstructions('')
      setIdeas(null)
      onStarted()
    })

  return (
    <div className="card">
      <h2>Write a post</h2>
      {error && <div className="error">{error}</div>}
      <label htmlFor="blog-category">Category</label>
      <select id="blog-category" value={category} onChange={(e) => changeCategory(e.target.value)}>
        {categories.map((c) => (
          <option key={c.key} value={c.key}>{c.name}</option>
        ))}
      </select>
      <label htmlFor="blog-type">Kind of post</label>
      <select id="blog-type" value={postType} onChange={(e) => setPostType(e.target.value)}>
        <option value="deep">Deep dive — one main story</option>
        <option value="pulse">News digest — several stories</option>
      </select>

      <div className="button-row">
        <button type="button" className="secondary" disabled={busy !== null} onClick={loadNews}>
          {busy === 'news' ? 'Loading news…' : news ? 'Refresh news' : 'Show latest news'}
        </button>
        <button type="button" className="secondary" disabled={busy !== null} onClick={loadIdeas}>
          {busy === 'ideas' ? 'Thinking…' : 'Suggest post ideas'}
        </button>
      </div>

      {ideas && (
        <ul className="idea-list">
          {ideas.list.map((idea, n) => (
            <li key={n}>
              <span className="pill">{{ paper: 'From a paper', news: 'From the news', topic: 'Evergreen topic' }[idea.kind]}</span>
              <strong>{idea.title}</strong>
              <span className="muted">{idea.angle}</span>
              <button type="button" className="link-button" onClick={() => useIdea(idea)}>Use this idea</button>
            </li>
          ))}
        </ul>
      )}

      {news && (
        news.length === 0 ? (
          <p className="muted">Nothing new in this category right now.</p>
        ) : (
          <>
            <p className="muted">Pick up to {MAX_PICKS} — the first one you pick leads the post.</p>
            {papers.length > 0 && (
              <>
                <h3 className="list-heading">Research papers</h3>
                <ul className="news-list">{papers.map(newsItem)}</ul>
              </>
            )}
            {stories.length > 0 && (
              <>
                <h3 className="list-heading">News</h3>
                <ul className="news-list">{stories.map(newsItem)}</ul>
              </>
            )}
          </>
        )
      )}

      <label htmlFor="blog-links">Paper or article links (optional, one per line)</label>
      <textarea
        id="blog-links"
        rows={3}
        placeholder="https://arxiv.org/abs/… or any article URL"
        value={links}
        onChange={(e) => setLinks(e.target.value)}
      />
      <label htmlFor="blog-instructions">Tell the AI what you want (optional)</label>
      <textarea
        id="blog-instructions"
        rows={4}
        placeholder="e.g. Focus on what this means for hair salons, keep it under 800 words, end with a WhatsApp tip."
        value={instructions}
        onChange={(e) => setInstructions(e.target.value)}
      />
      <p className="muted">
        Picked nothing? The AI picks the freshest news in the category itself.
      </p>
      <div className="button-row">
        <button type="button" disabled={busy !== null} onClick={write}>
          {busy === 'write' ? 'Starting…' : 'Write draft'}
        </button>
      </div>
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

  const generating = data?.posts.some((p) => p.status === 'generating')
  useEffect(() => {
    if (!generating) return undefined
    const timer = setInterval(refresh, 8000)
    return () => clearInterval(timer)
  }, [generating])

  if (openId) return <BlogEditor postId={openId} onChanged={refresh} onClose={() => setOpenId(null)} />
  if (error) return <div className="card error">Could not load posts: {error}</div>
  if (!data) return <div className="card">Loading posts…</div>

  return (
    <>
      {data.categories?.length > 0 && <BlogComposer categories={data.categories} onStarted={refresh} />}
      <div className="card">
        <h2>Posts</h2>
        <p className="muted">
          AI drafts also arrive on their own Mon, Wed and Fri. Approved posts go live in a few minutes; anything you
          don't approve, hold or reject goes live after {data.review_hours} hours.
        </p>
        {data.posts.length === 0 ? (
          <p>No posts yet.</p>
        ) : (
          <ul className="blog-list">
            {data.posts.map((p) => (
              <li key={p.id}>
                <button type="button" className="blog-row" onClick={() => setOpenId(p.id)}>
                  <strong>{p.title}</strong>
                  <span className={p.status === 'failed' ? 'error' : 'muted'}>
                    {p.status !== 'generating' && p.status !== 'failed' && `${p.category} · `}
                    {BLOG_STATUS_LABELS[p.status]}
                    {p.status === 'draft' && (p.auto_publish_at ? ` · auto-publishes ${timeLeft(p.auto_publish_at)}` : ' · on hold')}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
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
