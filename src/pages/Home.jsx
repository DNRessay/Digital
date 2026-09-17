import { Link } from 'react-router-dom'
import SEO, { SITE_URL } from '../components/SEO.jsx'

const jsonLd = {
  '@context': 'https://schema.org',
  '@type': 'Organization',
  name: 'Viincci Digital',
  url: SITE_URL,
  logo: `${SITE_URL}/favicon.svg`,
  description:
    'Viincci Digital builds websites, web apps, automation, and AI-powered tools for businesses across South Africa and beyond.',
  address: {
    '@type': 'PostalAddress',
    addressCountry: 'ZA',
  },
  sameAs: ['https://github.com/MrViincciLeRoy'],
}

const highlights = [
  {
    title: 'Websites & Web Apps',
    body: 'Fast, modern, SEO-ready sites and apps built with React, Django, and Flask.',
  },
  {
    title: 'AI & Automation',
    body: 'Chatbots, WhatsApp integrations, and LLM-powered tools using Groq and Claude.',
  },
  {
    title: 'Financial & Data Tools',
    body: 'Bank statement parsing, ledgers, and dashboards that turn raw data into decisions.',
  },
]

export default function Home() {
  return (
    <>
      <SEO
        title="Web, AI & Automation Studio"
        description="Viincci Digital designs and builds websites, AI chatbots, and automation tools for businesses in South Africa and worldwide."
        path="/"
        jsonLd={jsonLd}
      />

      <section className="hero">
        <div className="container">
          <p className="eyebrow">Viincci Digital</p>
          <h1>Digital products that actually move your business forward.</h1>
          <p className="lead">
            We design and build websites, AI-powered automation, and financial tools —
            fast, functional, and built to be found.
          </p>
          <div className="cta-row">
            <Link className="btn btn-primary" to="/contact">
              Start a project
            </Link>
            <Link className="btn btn-ghost" to="/portfolio">
              See our work
            </Link>
          </div>
        </div>
      </section>

      <section className="container section">
        <h2>What we do</h2>
        <div className="grid grid-3">
          {highlights.map((item) => (
            <article className="card" key={item.title}>
              <h3>{item.title}</h3>
              <p>{item.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="container section cta-banner">
        <h2>Have a project in mind?</h2>
        <p>Tell us what you're building — we'll tell you how to ship it.</p>
        <Link className="btn btn-primary" to="/contact">
          Get in touch
        </Link>
      </section>
    </>
  )
}
