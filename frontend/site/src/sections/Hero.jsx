import SectionLink from '../components/SectionLink.jsx'

export default function Hero() {
  return (
    <section id="hero" className="hero section">

      <div className="container" data-aos="fade-up" data-aos-delay="100">

        <div className="row align-items-center gy-5">

          <div className="col-lg-6" data-aos="fade-right" data-aos-delay="200">
            <div className="hero-content">
              <div className="hero-tag" data-aos="fade-up" data-aos-delay="250">
                <span className="tag-dot"></span>
                <span className="tag-text">Websites & WhatsApp Systems</span>
              </div>

              <h1 className="hero-headline" data-aos="fade-up" data-aos-delay="300">Websites & WhatsApp Systems for Small & Growing Businesses</h1>

              <p className="hero-text" data-aos="fade-up" data-aos-delay="350">A professional website plus a WhatsApp line your customers already trust — built, hosted, and supported by us. No hardware, no in-house developer needed.</p>

              <div className="hero-cta" data-aos="fade-up" data-aos-delay="400">
                <SectionLink to="pricing" className="cta-button">
                  <span>See Packages</span>
                  <i className="bi bi-arrow-right"></i>
                </SectionLink>
                <SectionLink to="contact" className="cta-link">
                  <i className="bi bi-chat-dots"></i>
                  <span>Get a Quote</span>
                </SectionLink>
              </div>
            </div>
          </div>

          <div className="col-lg-6" data-aos="fade-left" data-aos-delay="300">
            <div className="stats-grid">
              <div className="stat-card stat-card-primary" data-aos="zoom-in" data-aos-delay="350">
                <div className="stat-icon-wrap">
                  <i className="bi bi-boxes"></i>
                </div>
                <div className="stat-info">
                  <span className="stat-value">3</span>
                  <span className="stat-title">Flexible Packages</span>
                </div>
              </div>

              <div className="stat-card" data-aos="zoom-in" data-aos-delay="400">
                <div className="stat-icon-wrap">
                  <i className="bi bi-shield-check"></i>
                </div>
                <div className="stat-info">
                  <span className="stat-value">SSL</span>
                  <span className="stat-title">Security Included</span>
                </div>
              </div>

              <div className="stat-card" data-aos="zoom-in" data-aos-delay="450">
                <div className="stat-icon-wrap">
                  <i className="bi bi-whatsapp"></i>
                </div>
                <div className="stat-info">
                  <span className="stat-value">Optional</span>
                  <span className="stat-title">WhatsApp Add-on</span>
                </div>
              </div>

              <div className="stat-card stat-card-accent" data-aos="zoom-in" data-aos-delay="500">
                <div className="stat-icon-wrap">
                  <i className="bi bi-geo-alt"></i>
                </div>
                <div className="stat-info">
                  <span className="stat-value">South Africa</span>
                  <span className="stat-title">Locally Based</span>
                </div>
              </div>
            </div>
          </div>

        </div>

      </div>

    </section>
  )
}
