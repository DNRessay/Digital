import SEO from '../components/SEO.jsx'

const services = [
  {
    title: 'Web Design & Development',
    body: 'Marketing sites, dashboards, and full web apps built with React, Django, or Flask — fast, responsive, and SEO-optimized from day one.',
  },
  {
    title: 'AI Chatbots & Automation',
    body: 'WhatsApp and web chatbots powered by Groq and Claude, plus automation pipelines that remove repetitive manual work.',
  },
  {
    title: 'Financial & Data Systems',
    body: 'Bank statement parsing, ledger systems, and reporting tools that connect to ERPNext and turn raw statements into clean data.',
  },
  {
    title: 'SEO & Performance',
    body: 'Technical SEO, structured data, sitemaps, and page-speed optimization so your site actually gets found on Google.',
  },
]

export default function Services() {
  return (
    <>
      <SEO
        title="Services"
        description="Web development, AI chatbots, automation, and financial data systems — built and delivered by Viincci Digital."
        path="/services"
      />

      <section className="container section">
        <p className="eyebrow">Services</p>
        <h1>What we build</h1>
        <p className="lead">Focused services, delivered without the agency overhead.</p>

        <div className="grid grid-2 section">
          {services.map((s) => (
            <article className="card" key={s.title}>
              <h2>{s.title}</h2>
              <p>{s.body}</p>
            </article>
          ))}
        </div>
      </section>
    </>
  )
}
