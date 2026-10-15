import { useEffect } from 'react'
import Portfolio from '../sections/Portfolio.jsx'

export default function PortfolioPage() {
  useEffect(() => {
    document.title = 'Portfolio — Vicinic'
  }, [])

  return <Portfolio standalone />
}
