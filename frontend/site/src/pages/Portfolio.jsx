import SEO from '../components/SEO.jsx'

const projects = [
  {
    name: 'LSuite (Ledger Suite)',
    body: 'Django-based financial management system that parses South African bank statements (Capitec, TymeBank) from PDFs and Gmail, auto-categorizes transactions, and syncs with ERPNext.',
    tags: ['Django', 'MySQL', 'ERPNext'],
  },
  {
    name: 'BHKA Bot',
    body: 'WhatsApp AI chatbot for a South African credit rehabilitation company, powered by Groq (Llama 3) and the Meta WhatsApp Cloud API.',
    tags: ['Python', 'Groq', 'WhatsApp Cloud API'],
  },
  {
    name: 'Semblance',
    body: 'A Jarvis-inspired personal AI assistant with an animated React interface and a Claude-powered backend.',
    tags: ['React', 'Claude API'],
  },
  {
    name: 'News-Forex Dataset',
    body: 'A US economic calendar dataset (2001–2026) enriched with technical indicators (RSI, MACD, Bollinger Bands) built for automated market analysis.',
    tags: ['Python', 'GitHub Actions', 'yfinance'],
  },
]

export default function Portfolio() {
  return (
    <>
      <SEO
        title="Portfolio"
        description="A selection of web apps, AI chatbots, and data systems built by Vicinic."
        path="/portfolio"
      />

      <section className="container section">
        <p className="eyebrow">Portfolio</p>
        <h1>Recent work</h1>
        <p className="lead">A few of the systems we've designed and shipped.</p>

        <div className="grid grid-2 section">
          {projects.map((p) => (
            <article className="card" key={p.name}>
              <h2>{p.name}</h2>
              <p>{p.body}</p>
              <ul className="tag-list">
                {p.tags.map((t) => (
                  <li key={t}>{t}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>
    </>
  )
}
