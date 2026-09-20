import SectionLink from '../components/SectionLink.jsx'

const SERVICES = [
  {
    icon: 'bi-window',
    title: 'Business Websites',
    text: 'A professional home, about, services, and contact site — built, hosted, and secured for you. No developer needed on your side.',
  },
  {
    icon: 'bi-whatsapp',
    title: 'WhatsApp Systems',
    text: 'Optional WhatsApp lines for customer enquiries and broadcasts, with an AI assistant available on higher tiers.',
  },
  {
    icon: 'bi-calendar-check',
    title: 'Bookings & Payments',
    text: 'Online bookings, customer databases, and payment collection as your business grows — upgrade any time, no data lost.',
    featured: true,
  },
  {
    icon: 'bi-shield-check',
    title: 'Hosting & Security',
    text: 'Hosting, SSL security, and uptime included on every plan — no extra setup or separate bills on your side.',
  },
  {
    icon: 'bi-headset',
    title: 'Ongoing Support',
    text: 'Support is included from day one. No developer or IT staff required on your side, ever.',
  },
  {
    icon: 'bi-graph-up-arrow',
    title: 'SEO & Analytics',
    text: "Built to be found online, with basic analytics on visitor activity from the Growth Hub tier up.",
  },
]

export default function Services({ standalone = false }) {
  return (
    <section id="services" className="services section">

      <div className="container section-title" data-aos="fade-up">
        {standalone && <h1 className="visually-hidden">Services</h1>}
        <h2>Services</h2>
        <p>Everything your business needs to be found online — hosting and support included on every plan</p>
      </div>

      <div className="container" data-aos="fade-up" data-aos-delay="100">

        <div className="row g-4">
          {SERVICES.map((service, i) => (
            <div className="col-lg-4 col-md-6" data-aos="fade-up" data-aos-delay={100 * ((i % 3) + 1)} key={service.title}>
              <div className={`service-card${service.featured ? ' featured' : ''}`}>
                {service.featured && (
                  <div className="featured-badge">
                    <i className="bi bi-star-fill"></i>
                    <span>Popular</span>
                  </div>
                )}
                <div className="icon-wrapper">
                  <i className={`bi ${service.icon}`}></i>
                </div>
                <h3>{service.title}</h3>
                <p>{service.text}</p>
                <SectionLink to="pricing" className="service-link">
                  <span>See Packages</span>
                  <i className="bi bi-arrow-right"></i>
                </SectionLink>
              </div>
            </div>
          ))}
        </div>

      </div>

    </section>
  )
}
