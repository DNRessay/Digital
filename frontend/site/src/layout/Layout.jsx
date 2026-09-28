import { useEffect } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import Header from '../components/Header.jsx'
import Footer from '../components/Footer.jsx'
import CookieBanner from '../components/CookieBanner.jsx'
import useOrbitChrome from '../hooks/useOrbitChrome.js'

export default function Layout() {
  useOrbitChrome()
  const { pathname } = useLocation()

  // Each page is its own canonical URL on vicinic.co.za (the SPA ships one index.html).
  useEffect(() => {
    const href = `https://vicinic.co.za${pathname}`
    document.querySelector('link[rel="canonical"]')?.setAttribute('href', href)
    document.querySelector('meta[property="og:url"]')?.setAttribute('content', href)
  }, [pathname])

  return (
    <>
      <Header />
      <main className="main">
        <Outlet />
      </main>
      <Footer />
      <CookieBanner />
      <a href="#" id="scroll-top" className="scroll-top d-flex align-items-center justify-content-center" onClick={(e) => e.preventDefault()}>
        <i className="bi bi-arrow-up-short"></i>
      </a>
    </>
  )
}
