import { useEffect } from 'react'
import Contact from '../sections/Contact.jsx'

export default function ContactPage() {
  useEffect(() => {
    document.title = 'Contact — Vicinic'
  }, [])

  return <Contact standalone />
}
