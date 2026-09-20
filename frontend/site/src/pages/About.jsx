import SEO from '../components/SEO.jsx'

export default function About() {
  return (
    <>
      <SEO
        title="About Us"
        description="Vicinic is an independent South African studio building websites and WhatsApp systems for shops, salons, clinics, consultants, and growing businesses."
        path="/about"
      />

      <section className="container section">
        <p className="eyebrow">About</p>
        <h1>Built by a developer who ships.</h1>
        <p className="lead">
          Vicinic is a solo-led digital studio based in South Africa. No layers
          of account managers, no bloated timelines — just working websites and WhatsApp
          systems, built and shipped by someone who writes the code.
        </p>

        <div className="grid grid-2 section">
          <div className="card">
            <h3>Who we work with</h3>
            <p>
              Shops, salons, clinics, consultants, and other small and growing
              businesses that need a professional website and, when it makes sense,
              a WhatsApp line their customers already trust. No hardware and no
              in-house developer required on your side.
            </p>
          </div>
          <div className="card">
            <h3>How we work</h3>
            <p>
              Every project starts with the smallest thing that works — a fast,
              secure, SEO-ready website — then grows with you. Hosting, SSL security,
              and support are included from day one, and you can upgrade any time
              without losing your data.
            </p>
          </div>
        </div>
      </section>
    </>
  )
}
