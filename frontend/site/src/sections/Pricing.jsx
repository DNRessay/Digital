import SectionLink from '../components/SectionLink.jsx'

const PLANS = [
  {
    name: 'Starter Site',
    price: 'R250',
    onceOff: true,
    delay: 100,
    features: [
      'Professional static website (home, about, services, contact)',
      '1 admin login to manage content',
      'Contact form — enquiries land in your inbox',
      'Hosting, SSL security & support included',
      'One-time payment — yours to keep, no monthly bill',
    ],
  },
  {
    name: 'Growth Hub',
    price: 'R349',
    setup: 'R2,500',
    delay: 200,
    featured: true,
    badge: { icon: 'bi-star-fill', text: 'Best fit for most businesses' },
    features: [
      'Everything in Starter Site',
      'Online bookings or enquiry form with customer database',
      'Staff logins with secure Google Sign-In',
      'Basic analytics on visitor activity',
      'Access to premium templates — contact us to pick one',
    ],
  },
  {
    name: 'Business OS',
    price: 'R699',
    setup: 'R5,500',
    delay: 300,
    badge: { icon: 'bi-award', text: 'Full package' },
    features: [
      'Everything in Growth Hub',
      'Online payments and order/booking management',
      'Customer profiles and purchase/service history',
      'Premium templates, or a fully custom design — contact us',
    ],
  },
]

export default function Pricing({ standalone = false }) {
  return (
    <section id="pricing" className="pricing section light-background">

      <div className="container section-title" data-aos="fade-up">
        {standalone && <h1 className="visually-hidden">Pricing</h1>}
        <h2>Pricing</h2>
        <p>Three packages, for any type of business. Every plan includes hosting, security, and ongoing support.</p>
      </div>

      <div className="container" data-aos="fade-up" data-aos-delay="100">

        <div className="row g-4 justify-content-center">
          {PLANS.map((plan) => (
            <div className="col-lg-4 col-md-6" data-aos="fade-up" data-aos-delay={plan.delay} key={plan.name}>
              <div className={`pricing-card${plan.featured ? ' featured' : ''}`}>
                {plan.badge && (
                  <div className="featured-badge"><i className={`bi ${plan.badge.icon}`}></i> {plan.badge.text}</div>
                )}
                <h3>{plan.name}</h3>
                <div className="pricing-price">{plan.price}<span>{plan.onceOff ? ' once-off' : '/month'}</span></div>
                <ul className="pricing-features">
                  {plan.features.map((feature) => (
                    <li key={feature}><i className="bi bi-check-circle-fill"></i> {feature}</li>
                  ))}
                </ul>
                {!plan.onceOff && (
                  <div className="pricing-setup">Once-off setup fee <strong>{plan.setup}</strong></div>
                )}
                <SectionLink to="contact" className="btn-pricing">Get a Quote</SectionLink>
              </div>
            </div>
          ))}
        </div>

        <div className="row g-4 mt-3">
          <div className="col-lg-6" data-aos="fade-up" data-aos-delay="100">
            <h4 className="addon-heading">WhatsApp add-ons</h4>
            <p className="addon-intro">Not every business runs on WhatsApp — so it's priced separately, added only when you want it.</p>
            <table className="addon-table">
              <thead><tr><th>Plan</th><th>Price</th></tr></thead>
              <tbody>
                <tr><td>Basic — inquiries + up to 500 broadcasts/month</td><td>R99/mo</td></tr>
                <tr><td>Standard — up to 1,500 broadcasts/month</td><td>R220/mo</td></tr>
                <tr><td>Pro — up to 5,000 broadcasts/month + AI assistant</td><td>R720/mo</td></tr>
              </tbody>
            </table>
          </div>
          <div className="col-lg-6" data-aos="fade-up" data-aos-delay="200">
            <h4 className="addon-heading">Other add-ons</h4>
            <p className="addon-intro">Available on any tier, whenever you need them.</p>
            <table className="addon-table">
              <thead><tr><th>Add-on</th><th>Price</th></tr></thead>
              <tbody>
                <tr><td>Content Manager — we keep your site updated</td><td>R350/mo</td></tr>
                <tr><td>Data Capturing — load existing records</td><td>R500 once</td></tr>
                <tr><td>Website Refresh — annual redesign</td><td>R800/yr</td></tr>
              </tbody>
            </table>
          </div>
        </div>

      </div>

    </section>
  )
}
