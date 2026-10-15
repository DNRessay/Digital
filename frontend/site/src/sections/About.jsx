import SectionLink from '../components/SectionLink.jsx'

export default function About({ standalone = false }) {
  return (
    <section id="about" className="about section">

      <div className="container" data-aos="fade-up" data-aos-delay="100">

        <div className="row gy-5 align-items-center">

          <div className="col-xl-6" data-aos="fade-right" data-aos-delay="200">
            <div className="about-images-wrapper">
              <div className="image-main">
                <img src="/assets/img/about/about-5.webp" alt="Working on a client project" className="img-fluid" />
              </div>
              <div className="image-offset">
                <img src="/assets/img/about/about-square-3.webp" alt="Detail shot" className="img-fluid" />
              </div>
              <div className="shape-pattern"></div>
            </div>
          </div>

          <div className="col-xl-6" data-aos="fade-left" data-aos-delay="300">
            <div className="about-content">
              <div className="section-subtitle">Who We Are</div>
              {standalone && <h1 className="visually-hidden">Built by a Developer Who Ships</h1>}
              <h2>Built by a Developer Who Ships</h2>
              <p className="lead-text">
                Vicinic is a solo-led digital studio based in South Africa. No layers of account managers,
                no bloated timelines — just working websites and WhatsApp systems, built and shipped by
                someone who writes the code.
              </p>
              <p className="mb-4 description">
                Every project starts with the smallest thing that works — a fast, secure, SEO-ready
                website — then grows with you. Hosting, SSL security, and support are included from day
                one, and you can upgrade any time without losing your data.
              </p>

              <div className="features-grid">
                <div className="feature-card">
                  <i className="bi bi-check-circle-fill"></i>
                  <span>Fast Delivery</span>
                </div>
                <div className="feature-card">
                  <i className="bi bi-check-circle-fill"></i>
                  <span>Hosting Included</span>
                </div>
                <div className="feature-card">
                  <i className="bi bi-check-circle-fill"></i>
                  <span>No Middlemen</span>
                </div>
                <div className="feature-card">
                  <i className="bi bi-check-circle-fill"></i>
                  <span>Ongoing Support</span>
                </div>
              </div>

              <div className="action-buttons">
                <SectionLink to="services" className="btn btn-primary-custom">
                  See What We Build <i className="bi bi-arrow-right"></i>
                </SectionLink>
                <div className="contact-info">
                  <div className="icon-box">
                    <i className="bi bi-envelope-fill"></i>
                  </div>
                  <div className="text">
                    <span>Have a project?</span>
                    <SectionLink to="contact">Get in touch</SectionLink>
                  </div>
                </div>
              </div>

            </div>
          </div>

        </div>

      </div>

    </section>
  )
}
