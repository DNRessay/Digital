import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'

const PATH_TO_SECTION = {
  '/': 'hero',
  '/about': 'about',
  '/services': 'services',
  '/pricing': 'pricing',
  '/portfolio': 'portfolio',
  '/contact': 'contact',
}

const SECTION_IDS = ['hero', 'about', 'services', 'pricing', 'portfolio', 'contact']

// On Home this reproduces the original navmenuScrollspy() from main.js.
// On a dedicated page there's nothing to scroll-spy, so the nav just
// highlights whichever item matches the current route.
export default function useActiveSection() {
  const { pathname } = useLocation()
  const [active, setActive] = useState(PATH_TO_SECTION[pathname] || '')

  useEffect(() => {
    if (pathname !== '/') {
      setActive(PATH_TO_SECTION[pathname] || '')
      return
    }

    function onScroll() {
      const position = window.scrollY + 200
      for (const id of SECTION_IDS) {
        const section = document.getElementById(id)
        if (!section) continue
        if (position >= section.offsetTop && position <= section.offsetTop + section.offsetHeight) {
          setActive(id)
          return
        }
      }
    }

    onScroll()
    window.addEventListener('scroll', onScroll)
    return () => window.removeEventListener('scroll', onScroll)
  }, [pathname])

  return active
}
