import { useEffect } from 'react'

export const COMPANY = {
  name: 'VICINIC (Pty) Ltd',
  reg: '2026/760598/07',
  address: '3006 Thembelihle Road, Winterveldt, Tshwane, 0198, South Africa',
  email: 'mmehgoss@gmail.com',
  officer: 'Miguel Nyobole, Director',
}

export const UPDATED = '28 September 2026'

export default function LegalPage({ title, intro, children }) {
  useEffect(() => {
    document.title = `${title} — Vicinic`
  }, [title])

  return (
    <section className="legal section">
      <div className="container legal-body">
        <h1>{title}</h1>
        <p className="legal-updated">Last updated: {UPDATED}</p>
        {intro && <p className="legal-intro">{intro}</p>}
        {children}
      </div>
    </section>
  )
}
