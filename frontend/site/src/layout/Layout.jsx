import { useEffect } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import Header from '../components/Header.jsx'
import Footer from '../components/Footer.jsx'
import CookieBanner from '../components/CookieBanner.jsx'
import useOrbitChrome from '../hooks/useOrbitChrome.js'
import SEO from '../seo.json'

export default function Layout() {
  useOrbitChrome()
  const { pathname } = useLocation()

  // Each page is its own canonical URL on vicinic.co.za (the SPA ships one index.html).
  useEffect(() => {
    const path = pathname.replace(/\/+$/, '') || '/'
    const href = `https://vicinic.co.za${path}`
    const meta = SEO[path]
    const set = (sel, attr, value) => document.querySelector(sel)?.setAttribute(attr, value)
    set('link[rel="canonical"]', 'href', href)
    set('meta[property="og:url"]', 'content', href)
    if (meta) {
      document.title = meta.title
      set('meta[name="description"]', 'content', meta.description)
      set('meta[property="og:title"]', 'content', meta.title)
      set('meta[property="og:description"]', 'content', meta.description)
    }
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
