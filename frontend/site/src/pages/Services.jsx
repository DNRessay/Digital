import { Link } from 'react-router-dom'
import SEO from '../components/SEO.jsx'

const packages = [
  {
    name: 'Starter Site',
    price: 'R99',
    setup: 'R900',
    features: [
      'Professional static business website (home, about, services/products, contact)',
      '1 admin login to manage content',
      'Contact form — enquiries land straight in your inbox',
      'Hosting, security (SSL) and support included',
      'WhatsApp not included — add it any time',
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
      'Online bookings or enquiry form with customer database (up to 2,000 contacts)',
      'Staff logins with secure Google Sign-In',
      'Basic analytics — see what customers are viewing',
      'WhatsApp not included — add it any time',
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
      'WhatsApp not included — add it any time',
    ],
  },
]

const whatsappAddons = [
  { name: 'Basic — customer inquiries + up to 500 broadcasts/month', price: 'R99 / month' },
  { name: 'Standard — up to 1,500 broadcasts/month', price: 'R220 / month' },
  { name: 'Pro — up to 5,000 broadcasts/month + WhatsApp AI assistant', price: 'R720 / month' },
]

const otherAddons = [
  { name: 'Content Manager — we keep your site updated for you', price: 'R350 / month' },
  { name: 'Data Capturing — we load your existing customer/product records', price: 'R500 once' },
  { name: 'Website Refresh — annual redesign', price: 'R800 / year' },
]

export default function Services() {
  return (
    <>
      <SEO
        title="Services & Pricing"
        description="Website packages from R99/month and optional WhatsApp systems for small businesses — hosting, security, and support included on every plan."
        path="/services"
      />

      <section className="container section">
        <p className="eyebrow">Services & Pricing</p>
        <h1>Three packages, for any type of business</h1>
        <p className="lead">
          Every plan includes hosting, security (SSL), and ongoing support. The once-off
          setup fee is a single payment; the monthly fee renews. WhatsApp is optional on
          every tier — add it only if your business actually wants it.
        </p>

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
      </section>

      <section className="container section section-alt">
        <h2>WhatsApp add-ons</h2>
        <p>Not every business runs on WhatsApp — so it's priced separately, added only when you want it.</p>
        <table className="addon-table">
          <thead>
            <tr>
              <th>Plan</th>
              <th>Price</th>
            </tr>
          </thead>
          <tbody>
            {whatsappAddons.map((row) => (
              <tr key={row.name}>
                <td>{row.name}</td>
                <td>{row.price}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="container section">
        <h2>Other optional add-ons</h2>
        <p>Available on any tier, whenever you need them.</p>
        <table className="addon-table">
          <thead>
            <tr>
              <th>Add-on</th>
              <th>Price</th>
            </tr>
          </thead>
          <tbody>
            {otherAddons.map((row) => (
              <tr key={row.name}>
                <td>{row.name}</td>
                <td>{row.price}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="container section cta-banner">
        <h2>Not sure which package fits?</h2>
        <p>Tell us about your business and we'll recommend the right plan.</p>
        <Link className="btn btn-primary" to="/contact">
          Get a quote
        </Link>
      </section>
    </>
  )
}
