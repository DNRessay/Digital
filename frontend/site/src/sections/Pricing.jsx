import { Link } from 'react-router-dom'
import { SIGNUP_URL, SIGNUP_ENABLED } from '../lib/signup.js'
import { setQuotePlan } from '../lib/quote.js'
import SectionLink from '../components/SectionLink.jsx'
import '../styles/legal.css'

const PLANS = [
  {
    name: 'Starter Site',
    price: 'R250',
    onceOff: true,
    delay: 100,
    features: [
      'Free .co.za domain (1 per purchase, if the name is available)',
      'Pick a template and edit text, images, logo & links live',
      'Easy menu editor, plus up to 3 extra pages',
      'AI chat assistant that answers your visitors',
      'Email forwarding — you@yourbusiness.co.za to your inbox',
      'Hosting, SSL & support — no "Powered by" credit',
      'One-time payment — no monthly bill',
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
      'Free .co.za domain included',
      'Up to 10 extra pages',
      'Automated blog — up to 20 AI-written posts a month, free',
      'WhatsApp AI bot on your own business number',
      'Online booking requests and enquiries, with a customer database',
      'Staff logins for up to 5 team members',
      'Visitor analytics',
      'Premium templates, including private custom templates',
    ],
  },
  {
    name: 'Business OS',
    price: 'R699',
    setup: 'R5,500',
    delay: 300,
    cta: 'Contact sales',
    to: 'contact',
    badge: { icon: 'bi-award', text: 'Full package' },
    features: [
      'Everything in Growth Hub',
      'Free .co.za domain included',
      'Unlimited pages',
      { text: 'Free print-on-demand merch store — no stock, we print and ship per order', sales: true },
      'Online shop with PayFast checkout and order management',
      'Customer profiles with purchase and booking history',
      'A fully custom design, private to your business',
    ],
  },
]

const SCHOOL_PLANS = [
  {
    name: 'Notice Board',
    price: 'R2,500',
    onceOff: true,
    delay: 100,
    note: 'Hosting and .co.za domain included for 12 months, then R600/year',
    features: [
      'Mobile-friendly school website',
      'Principal\'s message, admissions info, news, calendar and gallery',
      'Downloadable forms, policies and stationery lists',
      'Easy admin area so staff post notices themselves',
      '1 training session (up to 5 staff) and 30 days of support',
    ],
  },
  {
    name: 'Communication Hub',
    price: 'R409',
    setup: 'R3,000',
    delay: 200,
    featured: true,
    badge: { icon: 'bi-star-fill', text: 'Most popular' },
    features: [
      'Everything in Notice Board',
      'SMS notices to parents — 500/month included',
      'Online admissions using the school\'s own forms',
      'Online payments for fundraisers, trips and events',
      'Secure parent contact list, daily backups',
      'Helpdesk in school hours, 2 training sessions (up to 10 staff)',
    ],
  },
  {
    name: 'School Efficiency OS',
    price: 'R799',
    setup: 'R5,500',
    delay: 300,
    badge: { icon: 'bi-award', text: 'Full school platform' },
    features: [
      'Everything in Communication Hub',
      '1,000 SMS/month included',
      'Parent and learner portal with individual logins',
      'Reports and results sharing (optional)',
      'WhatsApp notices and automated replies to parents',
      'Attendance and homework notices, priority support',
    ],
  },
]

function PlanCard({ plan, cta, to = plan.to }) {
  if (!SIGNUP_ENABLED) {
    to = 'contact'
    cta = cta || (plan.cta === 'Contact sales' ? 'Contact sales' : 'Request a quote')
  } else {
    cta = cta || plan.cta || 'Sign up free'
  }

  return (
    <div className="col-lg-4 col-md-6" data-aos="fade-up" data-aos-delay={plan.delay}>
      <div className={`pricing-card${plan.featured ? ' featured' : ''}`}>
        {plan.badge && (
          <div className="featured-badge"><i className={`bi ${plan.badge.icon}`}></i> {plan.badge.text}</div>
        )}
        <h3>{plan.name}</h3>
        <div className="pricing-price">{plan.price}<span>{plan.onceOff ? ' once-off' : '/month'}</span></div>
        <ul className="pricing-features">
          {plan.features.map((feature) => {
            const { text, sales } = typeof feature === 'string' ? { text: feature } : feature
            return (
              <li key={text}>
                <i className="bi bi-check-circle-fill"></i>{' '}
                <span>
                  {text}
                  {sales && <span className="sales-tag">Via our sales team</span>}
                </span>
              </li>
            )
          })}
        </ul>
        {plan.setup && (
          <div className="pricing-setup">Once-off setup fee <strong>{plan.setup}</strong></div>
        )}
        {plan.note && <div className="pricing-setup">{plan.note}</div>}
        {to
          ? <SectionLink to={to} className="btn-pricing" onClick={() => setQuotePlan(plan.name)}>{cta}</SectionLink>
          : <a href={SIGNUP_URL} className="btn-pricing">{cta}</a>}
      </div>
    </div>
  )
}

export default function Pricing({ standalone = false }) {
  return (
    <section id="pricing" className="pricing section light-background">

      <div className="container section-title" data-aos="fade-up">
        {standalone && <h1 className="visually-hidden">Pricing</h1>}
        <h2>Pricing</h2>
        <p>{SIGNUP_ENABLED
          ? "Sign up free, build your site in the editor, then pick a plan when you're ready to go live."
          : "Pick a package and request a quote — we'll confirm the details by email and get you set up."} Every paid plan includes a free .co.za domain (while the name is available — see our <Link to="/terms">terms</Link>), hosting, security and ongoing support.</p>
      </div>

      <div className="container" data-aos="fade-up" data-aos-delay="100">

        <div className="row g-4 justify-content-center">
          {PLANS.map((plan) => <PlanCard plan={plan} key={plan.name} />)}
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


        <div id="schools" className="section-title mt-5 pt-4" data-aos="fade-up">
          <h2>For Schools</h2>
          <p>A website, SMS notices to parents, online admissions and payments — built, hosted and supported for you. No IT person needed.</p>
        </div>

        <div className="row g-4 justify-content-center">
          {SCHOOL_PLANS.map((plan) => <PlanCard plan={plan} cta="Request a proposal" to="contact" key={plan.name} />)}
        </div>

        <div className="row g-4 mt-3">
          <div className="col-lg-6" data-aos="fade-up" data-aos-delay="100">
            <h4 className="addon-heading">Our promises to your school</h4>
            <ul className="pricing-features">
              <li><i className="bi bi-check-circle-fill"></i> Two months' notice, both ways — no long lock-in</li>
              <li><i className="bi bi-check-circle-fill"></i> Your data and your domain belong to the school</li>
              <li><i className="bi bi-check-circle-fill"></i> POPIA-compliant, with a written data-protection agreement</li>
              <li><i className="bi bi-check-circle-fill"></i> 99% uptime target, credited if we miss it</li>
              <li><i className="bi bi-check-circle-fill"></i> We only proceed once your SGB approves</li>
            </ul>
          </div>
          <div className="col-lg-6" data-aos="fade-up" data-aos-delay="200">
            <h4 className="addon-heading">School add-ons</h4>
            <table className="addon-table">
              <thead><tr><th>Add-on</th><th>Price</th></tr></thead>
              <tbody>
                <tr><td>Extra SMS bundle (500 SMS)</td><td>R175</td></tr>
                <tr><td>Additional training session</td><td>R350</td></tr>
                <tr><td>Extra development work</td><td>R350/hr</td></tr>
                <tr><td>School photography, logo or crest redesign</td><td>On request</td></tr>
              </tbody>
            </table>
            <p className="addon-intro mt-2">Upgrade any time — the setup fee you paid is credited toward the higher package. Payment processing fees excluded; no VAT charged.</p>
          </div>
        </div>

      </div>

    </section>
  )
}
