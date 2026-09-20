import { Link } from 'react-router-dom'

export default function Footer() {
  const year = new Date().getFullYear()

  return (
    <footer className="footer">
      <div className="footer-inner">
        <div>
          <div className="brand">
            Vicinic
          </div>
          <p>Websites & WhatsApp systems for small and growing businesses.</p>
        </div>

        <nav className="footer-links" aria-label="Footer navigation">
          <Link to="/">Home</Link>
          <Link to="/about">About</Link>
          <Link to="/services">Services</Link>
          <Link to="/portfolio">Portfolio</Link>
          <Link to="/contact">Contact</Link>
        </nav>

        <div className="footer-contact">
          <a href="mailto:hello@vicinic.com">hello@vicinic.com</a>
          <a href="https://github.com/MrViincciLeRoy" target="_blank" rel="noreferrer noopener">
            GitHub
          </a>
        </div>
      </div>
      <p className="footer-copy">© {year} Vicinic. All rights reserved.</p>
    </footer>
  )
}
