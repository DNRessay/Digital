import SectionLink from './SectionLink.jsx'

export default function Footer() {
  return (
    <footer id="footer" className="footer light-background">

      <div className="container footer-top">
        <div className="row gy-4">
          <div className="col-lg-3 col-md-6 footer-info">
            <SectionLink to="hero" className="logo d-flex align-items-center mb-4">
              <img src="/assets/img/logo.png" alt="Vicinic" className="logo-img" />
            </SectionLink>
            <p>Websites & WhatsApp systems for small and growing businesses across South Africa — hosted, secured, and supported.</p>

            <div className="social-links d-flex mt-4">
              <a href="https://github.com/MrViincciLeRoy" aria-label="GitHub" target="_blank" rel="noopener"><i className="bi bi-github"></i></a>
            </div>
          </div>

          <div className="col-lg-3 col-md-6 footer-links">
            <h4>Company</h4>
            <ul>
              <li><SectionLink to="about">About</SectionLink></li>
              <li><SectionLink to="services">Services</SectionLink></li>
              <li><SectionLink to="pricing">Pricing</SectionLink></li>
              <li><SectionLink to="portfolio">Portfolio</SectionLink></li>
            </ul>
          </div>

          <div className="col-lg-3 col-md-6 footer-links">
            <h4>Get In Touch</h4>
            <ul>
              <li><SectionLink to="contact">Contact</SectionLink></li>
              <li><a href="/privacy">Privacy Policy</a></li>
              <li><a href="/terms">Terms of Service</a></li>
            </ul>
          </div>

          <div className="col-lg-3 col-md-6">
            <div className="footer-newsletter">
              <h4>Ready to start?</h4>
              <p>Tell us about your business and we'll recommend the right package.</p>
              <SectionLink to="contact" className="btn-pricing">Get a Quote</SectionLink>
            </div>
          </div>
        </div>
      </div>

      <div className="container footer-bottom">
        <div className="row gy-3">
          <div className="col-md-6 order-2 order-md-1">
            <div className="copyright">
              <p>© <span>Copyright</span> <strong className="sitename">Vicinic</strong>. All Rights Reserved.</p>
            </div>
            <div className="credits">
              {/* All the links in the footer should remain intact. */}
              {/* You can delete the links only if you've purchased the pro version. */}
              {/* Licensing information: https://bootstrapmade.com/license/ */}
              Designed by <a href="https://bootstrapmade.com/">BootstrapMade</a> | <a href="https://bootstrapmade.com/tools/">DevTools</a>
            </div>
          </div>
          <div className="col-md-6 order-1 order-md-2">
            <div className="legal-links">
              <a href="/terms">Terms of Service</a>
              <a href="/privacy">Privacy Policy</a>
            </div>
          </div>
        </div>
      </div>

    </footer>
  )
}
