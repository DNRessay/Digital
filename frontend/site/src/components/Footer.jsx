import { SIGNUP_URL } from '../lib/signup.js'
import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer id="footer" className="footer light-background">

      <div className="container footer-top">
        <div className="row gy-4">
          <div className="col-lg-3 col-md-6 footer-info">
            <Link to="/" className="logo d-flex align-items-center mb-4">
              <img src="/assets/img/logo-mark.png" alt="" className="logo-mark-img" />
              <img src="/assets/img/logo-wordmark.png" alt="Vicinic" className="logo-wordmark-img" />
            </Link>
            <p>Websites & WhatsApp systems for small and growing businesses across South Africa — hosted, secured, and supported.</p>
            <p><a href="mailto:info@vicinic.co.za">info@vicinic.co.za</a></p>

            <div className="social-links d-flex mt-4">
              <a href="https://github.com/MrViincciLeRoy" aria-label="GitHub" target="_blank" rel="noopener"><i className="bi bi-github"></i></a>
            </div>
          </div>

          <div className="col-lg-3 col-md-6 footer-links">
            <h4>Company</h4>
            <ul>
              <li><Link to="/about">About</Link></li>
              <li><Link to="/services">Services</Link></li>
              <li><Link to="/pricing">Pricing</Link></li>
              <li><Link to="/portfolio">Portfolio</Link></li>
              <li><a href="https://blog.vicinic.co.za">Blog</a></li>
            </ul>
          </div>

          <div className="col-lg-3 col-md-6 footer-links">
            <h4>Get In Touch</h4>
            <ul>
              <li><Link to="/contact">Contact</Link></li>
              <li><Link to="/privacy">Privacy Policy</Link></li>
              <li><Link to="/terms">Terms of Service</Link></li>
              <li><Link to="/cookies">Cookie Policy</Link></li>
            </ul>
          </div>

          <div className="col-lg-3 col-md-6">
            <div className="footer-newsletter">
              <h4>Ready to start?</h4>
              <p>Create your account free, pick a template and edit your site live — upgrade when you're ready.</p>
              <a href={SIGNUP_URL} className="btn-pricing">Sign up free</a>
            </div>
          </div>
        </div>
      </div>

      <div className="container footer-bottom">
        <div className="row gy-3">
          <div className="col-md-6 order-2 order-md-1">
            <div className="copyright">
              <p>© <span>Copyright</span> <strong className="sitename">Vicinic</strong>. All Rights Reserved.</p>
              <p className="registration-status">VICINIC (Pty Ltd) — registered with the CIPC (South Africa), Enterprise Number 2026/760598/07.</p>
            </div>
          </div>
          <div className="col-md-6 order-1 order-md-2">
            <div className="legal-links">
              <Link to="/terms">Terms of Service</Link>
              <Link to="/privacy">Privacy Policy</Link>
              <Link to="/cookies">Cookie Policy</Link>
            </div>
          </div>
        </div>
      </div>

    </footer>
  )
}
