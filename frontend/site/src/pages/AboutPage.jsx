import { useEffect } from 'react'
import About from '../sections/About.jsx'

export default function AboutPage() {
  useEffect(() => {
    document.title = 'About — Vicinic'
  }, [])

  return <About standalone />
}
