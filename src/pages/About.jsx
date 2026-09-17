import SEO from '../components/SEO.jsx'

export default function About() {
  return (
    <>
      <SEO
        title="About Us"
        description="Viincci Digital is an independent studio building web apps, automation, and AI tools for businesses across South Africa and beyond."
        path="/about"
      />

      <section className="container section">
        <p className="eyebrow">About</p>
        <h1>Built by a developer who ships.</h1>
        <p className="lead">
          Viincci Digital is a solo-led digital studio. No layers of account managers,
          no bloated timelines — just working software, built and shipped by someone
          who writes the code.
        </p>

        <div className="grid grid-2 section">
          <div className="card">
            <h3>How we work</h3>
            <p>
              Every project starts with the smallest thing that works, then grows.
              We favor proven tools — React, Python, Django, Flask, FastAPI — over
              trendy stacks that add risk without adding value.
            </p>
          </div>
          <div className="card">
            <h3>Where we're based</h3>
            <p>
              Operating out of South Africa and working with clients globally,
              with experience building for the local market — from bank statement
              parsing to WhatsApp-based customer service.
            </p>
          </div>
        </div>
      </section>
    </>
  )
}
