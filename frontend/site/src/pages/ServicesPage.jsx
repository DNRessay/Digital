import { useEffect } from 'react'
import Services from '../sections/Services.jsx'

export default function ServicesPage() {
  useEffect(() => {
    document.title = 'Services — Vicinic'
  }, [])

  return <Services standalone />
}
