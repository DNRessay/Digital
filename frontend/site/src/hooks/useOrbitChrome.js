import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import AOS from 'aos'
import GLightbox from 'glightbox'

// Ports the one-time, DOM-wide behaviors from the Orbit template's main.js
// into React. Runs once for the header/scroll-top/AOS setup, and again on
// every route change for the bits that depend on which DOM nodes exist
// (AOS targets, GLightbox links).
export default function useOrbitChrome() {
  const location = useLocation()

  // One-time setup: header .scrolled class + scroll-top button.
  useEffect(() => {
    function toggleScrolled() {
      const header = document.querySelector('#header')
      if (!header) return
      if (!header.classList.contains('sticky-top') && !header.classList.contains('fixed-top')) return
      document.body.classList.toggle('scrolled', window.scrollY > 100)
    }

    function toggleScrollTop() {
      const scrollTop = document.querySelector('.scroll-top')
      if (!scrollTop) return
      scrollTop.classList.toggle('active', window.scrollY > 100)
    }

    function handleScrollTopClick(e) {
      e.preventDefault()
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }

    toggleScrolled()
    toggleScrollTop()

    document.addEventListener('scroll', toggleScrolled)
    document.addEventListener('scroll', toggleScrollTop)

    const scrollTopEl = document.querySelector('.scroll-top')
    scrollTopEl?.addEventListener('click', handleScrollTopClick)

    AOS.init({ duration: 600, easing: 'ease-in-out', once: true, mirror: false })

    return () => {
      document.removeEventListener('scroll', toggleScrolled)
      document.removeEventListener('scroll', toggleScrollTop)
      scrollTopEl?.removeEventListener('click', handleScrollTopClick)
    }
  }, [])

  // Re-run per route: AOS needs to re-scan the DOM, GLightbox needs to
  // re-bind to whichever .glightbox links exist on the current page.
  useEffect(() => {
    const raf = requestAnimationFrame(() => AOS.refreshHard())

    const lightbox = GLightbox({ selector: '.glightbox' })

    return () => {
      cancelAnimationFrame(raf)
      lightbox.destroy()
    }
  }, [location.pathname])

  // Correct scroll position for URLs loaded directly with a hash (Home only).
  useEffect(() => {
    if (location.pathname !== '/' || !location.hash) return
    const id = location.hash.slice(1)
    const timer = setTimeout(() => {
      const section = document.getElementById(id)
      if (!section) return
      const scrollMarginTop = parseInt(getComputedStyle(section).scrollMarginTop, 10) || 0
      window.scrollTo({ top: section.offsetTop - scrollMarginTop, behavior: 'smooth' })
    }, 100)
    return () => clearTimeout(timer)
  }, [location.pathname, location.hash])
}
