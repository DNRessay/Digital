import { useEffect, useState } from 'react'
import SectionLink from './SectionLink.jsx'
import useActiveSection from '../hooks/useActiveSection.js'

const NAV_ITEMS = [
  { to: 'hero', label: 'Home' },
  { to: 'about', label: 'About' },
  { to: 'services', label: 'Services' },
  { to: 'pricing', label: 'Pricing' },
  { to: 'portfolio', label: 'Portfolio' },
  { to: 'contact', label: 'Contact' },
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

        <SectionLink to="hero" className="logo d-flex align-items-center me-auto me-xl-0">
          <img src="/assets/img/logo.png" alt="Vicinic" className="logo-img" />
        </SectionLink>

        <nav id="navmenu" className="navmenu">
          <ul onClick={() => setMobileNavActive(false)}>
            {NAV_ITEMS.map((item) => (
              <li key={item.to}>
                <SectionLink to={item.to} className={active === item.to ? 'active' : undefined}>
                  {item.label}
                </SectionLink>
              </li>
            ))}
          </ul>
          <i
            className={`mobile-nav-toggle d-xl-none bi ${mobileNavActive ? 'bi-x' : 'bi-list'}`}
            onClick={() => setMobileNavActive((v) => !v)}
          ></i>
        </nav>

        <SectionLink to="contact" className="btn-getstarted">Get a Quote</SectionLink>

      </div>
    </header>
  )
}
