import { useState } from 'react'
import SEO from '../components/SEO.jsx'

const WEB3FORMS_ACCESS_KEY = import.meta.env.VITE_WEB3FORMS_ACCESS_KEY || ''

const STATUS = {
  IDLE: 'idle',
  SENDING: 'sending',
  SUCCESS: 'success',
  ERROR: 'error',
}

export default function Contact() {
  const [status, setStatus] = useState(STATUS.IDLE)
  const [errorMessage, setErrorMessage] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()

    if (!WEB3FORMS_ACCESS_KEY) {
      setStatus(STATUS.ERROR)
      setErrorMessage(
        'Contact form is not configured yet. Set VITE_WEB3FORMS_ACCESS_KEY to enable it.'
      )
      return
    }

    setStatus(STATUS.SENDING)
    setErrorMessage('')

    const form = e.target
    const formData = new FormData(form)
    formData.append('access_key', WEB3FORMS_ACCESS_KEY)

    try {
      const res = await fetch('https://api.web3forms.com/submit', {
        method: 'POST',
        headers: { Accept: 'application/json' },
        body: formData,
      })
      const data = await res.json()

      if (data.success) {
        setStatus(STATUS.SUCCESS)
        form.reset()
      } else {
        setStatus(STATUS.ERROR)
        setErrorMessage(data.message || 'Something went wrong. Please try again.')
      }
    } catch {
      setStatus(STATUS.ERROR)
      setErrorMessage('Network error. Please try again in a moment.')
    }
  }

  return (
    <>
      <SEO
        title="Contact"
        description="Get in touch with Vicinic to get a quote for your business website or WhatsApp system."
        path="/contact"
      />

      <section className="container section">
        <p className="eyebrow">Contact</p>
        <h1>Let's build something.</h1>
        <p className="lead">
          Send a message and we'll get back to you — usually within a day.
        </p>

        <form className="contact-form" onSubmit={handleSubmit}>
          <input type="hidden" name="subject" value="New message from Vicinic site" />
          {/* Honeypot field — hidden from real users, catches spam bots */}
          <input type="checkbox" name="botcheck" className="hidden-field" tabIndex="-1" autoComplete="off" />

          <div className="form-row">
            <label htmlFor="name">Name</label>
            <input id="name" name="name" type="text" required autoComplete="name" />
          </div>

          <div className="form-row">
            <label htmlFor="email">Email</label>
            <input id="email" name="email" type="email" required autoComplete="email" />
          </div>

          <div className="form-row">
            <label htmlFor="message">Message</label>
            <textarea id="message" name="message" rows="6" required />
          </div>

          <button className="btn btn-primary" type="submit" disabled={status === STATUS.SENDING}>
            {status === STATUS.SENDING ? 'Sending…' : 'Send message'}
          </button>

          {status === STATUS.SUCCESS && (
            <p className="form-status success" role="status">
              Thanks — your message has been sent. We'll be in touch soon.
            </p>
          )}
          {status === STATUS.ERROR && (
            <p className="form-status error" role="alert">
              {errorMessage}
            </p>
          )}
        </form>
      </section>
    </>
  )
}
