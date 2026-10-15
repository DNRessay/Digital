import SectionLink from '../components/SectionLink.jsx'

export default function WhyUs() {
  return (
    <section id="why-us" className="why-us section light-background">

      <div className="container section-title" data-aos="fade-up">
        <h2>Why Us</h2>
        <p>What makes working with Vicinic different</p>
      </div>

      <div className="container" data-aos="fade-up" data-aos-delay="100">

        <div className="row g-5">
          <div className="col-lg-5" data-aos="fade-right" data-aos-delay="200">
            <div className="sidebar-content">
              <div className="badge-wrapper">
                <span className="section-badge"><i className="bi bi-stars"></i> Our Difference</span>
              </div>
              <h2>Why Businesses Choose Vicinic</h2>
              <p className="description">Straightforward pricing, no long contracts, and a direct line to the person actually building your site.</p>

              <div className="stat-cards">
                <div className="stat-card" data-aos="zoom-in" data-aos-delay="300">
                  <div className="stat-text">No Lock-in</div>
                </div>
                <div className="stat-card" data-aos="zoom-in" data-aos-delay="350">
                  <div className="stat-text">Hosting Included</div>
                </div>
                <div className="stat-card" data-aos="zoom-in" data-aos-delay="400">
                  <div className="stat-text">You Own Your Data</div>
                </div>
              </div>

              <div className="action-buttons">
                <SectionLink to="contact" className="btn-main">Get Started Today</SectionLink>
                <SectionLink to="portfolio" className="btn-outline">Explore Portfolio</SectionLink>
              </div>
            </div>
          </div>

          <div className="col-lg-7" data-aos="fade-left" data-aos-delay="200">
            <div className="features-grid">
              <div className="feature-box highlight" data-aos="fade-up" data-aos-delay="250">
                <div className="feature-icon">
                  <i className="bi bi-rocket-takeoff-fill"></i>
                </div>
                <div className="feature-content">
                  <h4>No Developer Needed</h4>
                  <p>We handle the tech so you don't have to hire, manage, or maintain anyone.</p>
                  <SectionLink to="contact" className="feature-link">Get in touch <i className="bi bi-chevron-right"></i></SectionLink>
                </div>
              </div>

              <div className="feature-box" data-aos="fade-up" data-aos-delay="300">
                <div className="feature-icon">
                  <i className="bi bi-arrow-repeat"></i>
                </div>
                <div className="feature-content">
                  <h4>Start Small, Grow Later</h4>
                  <p>Upgrade any time without losing your data or starting over.</p>
                  <SectionLink to="pricing" className="feature-link">See packages <i className="bi bi-chevron-right"></i></SectionLink>
                </div>
              </div>

              <div className="feature-box" data-aos="fade-up" data-aos-delay="350">
                <div className="feature-icon">
                  <i className="bi bi-shield-check"></i>
                </div>
                <div className="feature-content">
                  <h4>Hosting & Security Included</h4>
                  <p>SSL, hosting, and support are part of every plan from day one.</p>
                  <SectionLink to="pricing" className="feature-link">See packages <i className="bi bi-chevron-right"></i></SectionLink>
                </div>
              </div>
            </div>

            <div className="process-timeline" data-aos="fade-up" data-aos-delay="400">
              <h5 className="timeline-title"><i className="bi bi-diagram-3-fill"></i> How It Works</h5>
              <div className="timeline-steps">
                <div className="timeline-step">
                  <div className="step-marker">1</div>
                  <div className="step-info">
                    <strong>Chat</strong>
                    <span>Tell us about your business</span>
                  </div>
                </div>
                <div className="timeline-connector"></div>
                <div className="timeline-step">
                  <div className="step-marker">2</div>
                  <div className="step-info">
                    <strong>Plan</strong>
                    <span>We recommend the right package</span>
                  </div>
                </div>
                <div className="timeline-connector"></div>
                <div className="timeline-step">
                  <div className="step-marker">3</div>
                  <div className="step-info">
                    <strong>Build</strong>
                    <span>Your site goes live in days</span>
                  </div>
                </div>
                <div className="timeline-connector"></div>
                <div className="timeline-step">
                  <div className="step-marker">4</div>
                  <div className="step-info">
                    <strong>Support</strong>
                    <span>Ongoing hosting & help included</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="capabilities-section" data-aos="fade-up" data-aos-delay="450">
              <h5 className="capabilities-heading">What Sets Us Apart</h5>
              <div className="capabilities-grid">
                <div className="capability-card">
                  <div className="capability-icon">
                    <i className="bi bi-file-earmark-text"></i>
                  </div>
                  <h6>No Long Contracts</h6>
                  <p>Month-to-month packages — cancel or upgrade any time.</p>
                </div>
                <div className="capability-card">
                  <div className="capability-icon">
                    <i className="bi bi-lightning-charge"></i>
                  </div>
                  <h6>Fast Turnaround</h6>
                  <p>Most sites go live in days, not months.</p>
                </div>
                <div className="capability-card">
                  <div className="capability-icon">
                    <i className="bi bi-person-check"></i>
                  </div>
                  <h6>Direct Access</h6>
                  <p>Work directly with the person building your site — no account managers.</p>
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>

    </section>
  )
}
