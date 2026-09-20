import { useState } from 'react'

const WEB3FORMS_ENDPOINT = 'https://api.web3forms.com/submit'

export default function Contact({ standalone = false }) {
  const [status, setStatus] = useState('idle') // idle | loading | sent | error
  const [errorText, setErrorText] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    const form = e.target
    setStatus('loading')
    setErrorText('')

    try {
      const response = await fetch(WEB3FORMS_ENDPOINT, {
        method: 'POST',
        headers: { Accept: 'application/json' },
        body: new FormData(form),
      })
      const data = await response.json()
      if (data.success) {
        setStatus('sent')
        form.reset()
      } else {
        setErrorText(data.message || 'Something went wrong. Please try again.')
        setStatus('error')
      }
    } catch {
      setErrorText('Network error. Please try again in a moment.')
      setStatus('error')
    }
  }

  return (
    <section id="contact" className="contact section">

      <div className="container section-title" data-aos="fade-up">
        {standalone && <h1 className="visually-hidden">Contact</h1>}
        <h2>Contact</h2>
        <p>Tell us about your business — we'll recommend the right package</p>
      </div>

      <div className="container" data-aos="fade-up" data-aos-delay="100">

        <div className="row gy-5 align-items-stretch">

          <div className="col-lg-5" data-aos="fade-right" data-aos-delay="200">
            <div className="info-panel">
              <div className="panel-header">
                <span className="section-badge">
                  <i className="bi bi-chat-dots-fill"></i>
                  Get In Touch
                </span>
                <h3>Let's Build Something</h3>
                <p>Send a message and we'll get back to you — usually within a day.</p>
              </div>

              <div className="contact-methods">
                <div className="method-item">
                  <div className="method-icon">
                    <i className="bi bi-clock-history"></i>
                  </div>
                  <div className="method-details">
                    <span className="method-label">Response Time</span>
                    <span>Usually within a day</span>
                  </div>
                </div>

                <div className="method-item">
                  <div className="method-icon">
                    <i className="bi bi-currency-exchange"></i>
                  </div>
                  <div className="method-details">
                    <span className="method-label">Quotes</span>
                    <span>No-obligation, straightforward pricing</span>
                  </div>
                </div>

                <div className="method-item">
                  <div className="method-icon">
                    <i className="bi bi-geo-alt-fill"></i>
                  </div>
                  <div className="method-details">
                    <span className="method-label">Based In</span>
                    <span>South Africa</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="col-lg-7" data-aos="fade-left" data-aos-delay="300">
            <div className="form-card">
              <div className="form-card-header">
                <div className="header-icon">
                  <i className="bi bi-send-fill"></i>
                </div>
                <div className="header-text">
                  <h4>Send Us a Message</h4>
                  <p>Fill out the form and we'll respond as soon as we can.</p>
                </div>
              </div>

              <form className="php-email-form" onSubmit={handleSubmit}>
                {/* Replace with your own key from https://web3forms.com */}
                <input type="hidden" name="access_key" value="YOUR_WEB3FORMS_ACCESS_KEY" />
                {/* Honeypot field — hidden from real users, catches spam bots */}
                <input type="checkbox" name="botcheck" className="d-none" style={{ display: 'none' }} tabIndex="-1" autoComplete="off" />

                <div className="row g-4">
                  <div className="col-md-6">
                    <div className="input-group-custom">
                      <label>Your Name</label>
                      <div className="input-wrapper">
                        <i className="bi bi-person"></i>
                        <input type="text" name="name" placeholder="Your name" required autoComplete="name" />
                      </div>
                    </div>
                  </div>

                  <div className="col-md-6">
                    <div className="input-group-custom">
                      <label>Email Address</label>
                      <div className="input-wrapper">
                        <i className="bi bi-envelope"></i>
                        <input type="email" name="email" placeholder="you@example.com" required autoComplete="email" />
                      </div>
                    </div>
                  </div>

                  <div className="col-12">
                    <div className="input-group-custom">
                      <label>Subject</label>
                      <div className="input-wrapper">
                        <i className="bi bi-chat-square-text"></i>
                        <input type="text" name="subject" placeholder="How can we help?" required />
                      </div>
                    </div>
                  </div>

                  <div className="col-12">
                    <div className="input-group-custom">
                      <label>Your Message</label>
                      <div className="input-wrapper textarea-wrapper">
                        <i className="bi bi-pencil-square"></i>
                        <textarea name="message" rows="5" placeholder="Tell us about your business..." required></textarea>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="form-actions">
                  <div className={`loading${status === 'loading' ? ' d-block' : ''}`}>Loading</div>
                  <div className={`error-message${status === 'error' ? ' d-block' : ''}`}>{errorText}</div>
                  <div className={`sent-message${status === 'sent' ? ' d-block' : ''}`}>Your message has been sent. Thank you!</div>

                  <button type="submit" className="btn-submit">
                    <span>Send Message</span>
                    <i className="bi bi-arrow-right-circle-fill"></i>
                  </button>
                </div>
              </form>
            </div>
          </div>

        </div>

      </div>

    </section>
  )
}
