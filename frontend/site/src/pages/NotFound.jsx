import { useEffect } from 'react'
import SectionLink from '../components/SectionLink.jsx'

export default function NotFound() {
  useEffect(() => {
    document.title = 'Page Not Found - Vicinic'
  }, [])

  return (
    <section id="error-404" className="error-404 section">
      <div className="container" data-aos="fade-up" data-aos-delay="100">
        <div className="row align-items-center g-5">
          <div className="col-lg-6" data-aos="fade-right" data-aos-delay="200">
            <div className="error-visual">
              <div className="error-code">
                <span className="digit">4</span>
                <span className="digit middle"><i className="bi bi-emoji-frown"></i></span>
                <span className="digit">4</span>
              </div>
              <div className="error-decoration">
                <div className="circle circle-1"></div>
                <div className="circle circle-2"></div>
                <div className="circle circle-3"></div>
              </div>
            </div>
          </div>

          <div className="col-lg-6" data-aos="fade-left" data-aos-delay="300">
            <div className="error-content">
              <span className="error-badge">Oops!</span>
              <h1 className="error-heading">Page Not Found</h1>
              <p className="error-text">The page you're looking for doesn't exist or may have moved.</p>
              <div className="action-buttons">
                <SectionLink to="hero" className="btn-home">
                  <i className="bi bi-arrow-left"></i>
                  Return Home
                </SectionLink>
              </div>
            </div>
          </div>
        </div>

        <div className="row mt-5 pt-4">
          <div className="col-12">
            <div className="quick-navigation" data-aos="fade-up" data-aos-delay="400">
              <h4 className="nav-title">Quick Navigation</h4>
              <div className="nav-links">
                <SectionLink to="hero" className="nav-link-item">
                  <div className="icon-wrap"><i className="bi bi-house-door"></i></div>
                  <div className="link-content">
                    <span className="link-title">Homepage</span>
                    <span className="link-desc">Start fresh</span>
                  </div>
                </SectionLink>
                <SectionLink to="portfolio" className="nav-link-item">
                  <div className="icon-wrap"><i className="bi bi-collection"></i></div>
                  <div className="link-content">
                    <span className="link-title">Portfolio</span>
                    <span className="link-desc">View our work</span>
                  </div>
                </SectionLink>
                <SectionLink to="pricing" className="nav-link-item">
                  <div className="icon-wrap"><i className="bi bi-tags"></i></div>
                  <div className="link-content">
                    <span className="link-title">Pricing</span>
                    <span className="link-desc">See packages</span>
                  </div>
                </SectionLink>
                <SectionLink to="contact" className="nav-link-item">
                  <div className="icon-wrap"><i className="bi bi-envelope"></i></div>
                  <div className="link-content">
                    <span className="link-title">Contact</span>
                    <span className="link-desc">Get in touch</span>
                  </div>
                </SectionLink>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
