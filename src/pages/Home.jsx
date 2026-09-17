import { Link } from 'react-router-dom'
import SEO, { SITE_URL } from '../components/SEO.jsx'

const jsonLd = {
  '@context': 'https://schema.org',
  '@type': 'Organization',
  name: 'Viincci Digital',
  url: SITE_URL,
  logo: `${SITE_URL}/favicon.svg`,
  description:
    'Viincci Digital builds professional websites and WhatsApp systems for small and growing businesses across South Africa — hosted, secured, and supported.',
  address: {
    '@type': 'PostalAddress',
    addressCountry: 'ZA',
  },
  sameAs: ['https://github.com/MrViincciLeRoy'],
}

const services = [
  {
    title: 'Business Websites',
    body: 'A professional home, about, services, and contact site — built, hosted, and secured for you. No developer needed on your side.',
  },
  {
    title: 'WhatsApp Systems',
    body: 'Optional WhatsApp lines for customer enquiries and broadcasts, with an AI assistant available on higher tiers.',
  },
  {
    title: 'Bookings & Payments',
    body: 'Online bookings, customer databases, and payment collection as your business grows — upgrade any time, no data lost.',
  },
]

const trustPoints = [
  'Hosting, SSL security, and ongoing support included on every plan',
  'No developer or IT staff required on your side',
  'WhatsApp is optional — add it only if your business needs it',
  'Start small and upgrade later without losing your data',
]

const packages = [
  {
    name: 'Starter Site',
    price: 'R99',
    setup: 'R900',
    features: [
      'Professional static website (home, about, services, contact)',
      '1 admin login to manage content',
      'Contact form — enquiries land in your inbox',
      'Hosting, SSL security & support included',
    ],
  },
  {
    name: 'Growth Hub',
    price: 'R349',
    setup: 'R2,500',
    featured: true,
    badge: 'Best fit for most businesses',
    features: [
      'Everything in Starter Site',
      'Online bookings or enquiry form with customer database',
      'Staff logins with secure Google Sign-In',
      'Basic analytics on visitor activity',
    ],
  },
  {
    name: 'Business OS',
    price: 'R699',
    setup: 'R5,500',
    badge: 'Full package',
    features: [
      'Everything in Growth Hub',
      'Online payments and order/booking management',
      'Customer profiles and purchase/service history',
    ],
  },
]

export default function Home() {
  return (
    <>
      <SEO
        title="Websites & WhatsApp Systems for Small Businesses"
        description="Viincci Digital builds professional websites and optional WhatsApp systems for small and growing businesses in South Africa — hosted, secured, and supported."
        path="/"
        jsonLd={jsonLd}
      />

      <section className="hero">
        <div className="container">
          <p className="eyebrow">Viincci Digital</p>
          <h1>Websites & WhatsApp systems for small and growing businesses.</h1>
          <p className="lead">
            A professional website plus a WhatsApp line your customers already trust —
            built, hosted, and supported by us. No hardware, no in-house developer needed.
          </p>
          <div className="cta-row">
            <Link className="btn btn-primary" to="/contact">
              Get a quote
            </Link>
            <Link className="btn btn-ghost" to="/services">
              See packages
            </Link>
          </div>
        </div>
      </section>

      <section className="container section">
        <div className="stub-columns">
          <div>
            <p className="eyebrow">About us</p>
            <h2>Built by a developer who ships.</h2>
            <p>
              Viincci Digital is an independent South African studio building web and
              WhatsApp systems for shops, salons, clinics, consultants, and other growing
              businesses. No account managers, no bloated timelines — just working
              software, live in days, not months.
            </p>
            <Link className="btn btn-outline" to="/about">
              More about us →
            </Link>
          </div>
          <ul className="trust-list">
            {trustPoints.map((point) => (
              <li key={point}>{point}</li>
            ))}
          </ul>
        </div>
      </section>

      <section className="container section section-alt">
        <div className="section-head">
          <p className="eyebrow">What we build</p>
          <h2>Everything your business needs to be found online</h2>
        </div>
        <div className="grid grid-3">
          {services.map((item) => (
            <article className="card" key={item.title}>
              <h3>{item.title}</h3>
              <p>{item.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="container section">
        <div className="section-head">
          <p className="eyebrow">Packages</p>
          <h2>Three plans, for any type of business</h2>
          <p>
            Every plan includes hosting, security, and ongoing support. WhatsApp is
            optional on every tier — add it only if you want it.
          </p>
        </div>

        <div className="pricing-grid">
          {packages.map((pkg) => (
            <div className={`pricing-card ${pkg.featured ? 'featured' : ''}`} key={pkg.name}>
              <div className="pricing-card-head">
                {pkg.badge && <span className="badge">{pkg.badge}</span>}
                <h3>{pkg.name}</h3>
                <div className="pricing-card-price">
                  {pkg.price} <span>/ month</span>
                </div>
              </div>
              <div className="pricing-card-body">
                <ul>
                  {pkg.features.map((f) => (
                    <li key={f}>{f}</li>
                  ))}
                </ul>
                <div className="pricing-card-setup">
                  Once-off setup fee
                  <strong>{pkg.setup}</strong>
                </div>
              </div>
            </div>
          ))}
        </div>
        <p className="pricing-note">
          Need WhatsApp broadcasts, a content manager, or a full redesign?{' '}
          <Link to="/services" className="link-gold">
            See all packages & add-ons →
          </Link>
        </p>
      </section>

      <section className="container section cta-banner">
        <h2>Ready to get your business online?</h2>
        <p>Tell us about your business — we'll recommend the right package.</p>
        <Link className="btn btn-primary" to="/contact">
          Get in touch
        </Link>
      </section>
    </>
  )
}
