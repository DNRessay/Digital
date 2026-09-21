import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import useActiveSection from '../hooks/useActiveSection.js'

const NAV_ITEMS = [
  { to: 'hero', route: '/', label: 'Home' },
  { to: 'about', route: '/about', label: 'About' },
  { to: 'services', route: '/services', label: 'Services' },
  { to: 'pricing', route: '/pricing', label: 'Pricing' },
  { to: 'portfolio', route: '/portfolio', label: 'Portfolio' },
  { to: 'contact', route: '/contact', label: 'Contact' },
]

export default function Header() {
  const active = useActiveSection()
  const [mobileNavActive, setMobileNavActive] = useState(false)

  useEffect(() => {
    document.body.classList.toggle('mobile-nav-active', mobileNavActive)
  }, [mobileNavActive])

  return (
    <header id="header" className="header d-flex align-items-center sticky-top">
      <div className="container position-relative d-flex align-items-center justify-content-between">

        <Link to="/" className="logo d-flex align-items-center me-auto me-xl-0">
          <img src="/assets/img/logo-mark.png" alt="" className="logo-mark-img" />
          <img src="/assets/img/logo-wordmark.png" alt="Vicinic" className="logo-wordmark-img" />
        </Link>

        <nav id="navmenu" className="navmenu">
          <ul onClick={() => setMobileNavActive(false)}>
            {NAV_ITEMS.map((item) => (
              <li key={item.to}>
                <Link to={item.route} className={active === item.to ? 'active' : undefined}>
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
          <i
            className={`mobile-nav-toggle d-xl-none bi ${mobileNavActive ? 'bi-x' : 'bi-list'}`}
            onClick={() => setMobileNavActive((v) => !v)}
          ></i>
        </nav>

        <Link to="/contact" className="btn-getstarted">Get a Quote</Link>

      </div>
    </header>
  )
}
