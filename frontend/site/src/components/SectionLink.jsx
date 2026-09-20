import { Link, useLocation } from 'react-router-dom'

// Home ("/") keeps every section on one page, so on Home these links behave
// exactly as the original template's in-page anchors (scroll to #id).
// On a dedicated page (e.g. /services) the same section is its own route,
// so the link becomes a real navigation there instead.
export const SECTION_ROUTES = {
  hero: '/',
  about: '/about',
  services: '/services',
  pricing: '/pricing',
  portfolio: '/portfolio',
  contact: '/contact',
}

export default function SectionLink({ to, children, onClick, ...rest }) {
  const { pathname } = useLocation()
  const route = SECTION_ROUTES[to]

  if (pathname === '/') {
    return (
      <a href={`#${to}`} onClick={onClick} {...rest}>
        {children}
      </a>
    )
  }

  return (
    <Link to={route} onClick={onClick} {...rest}>
      {children}
    </Link>
  )
}
