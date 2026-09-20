import { Link } from 'react-router-dom'
import SEO from '../components/SEO.jsx'

export default function NotFound() {
  return (
    <>
      <SEO
        title="Page Not Found"
        description="The page you're looking for doesn't exist."
        path="/404"
      />

      <section className="container section not-found">
        <h1>404</h1>
        <p>That page doesn't exist.</p>
        <Link className="btn btn-primary" to="/">
          Back to home
        </Link>
      </section>
    </>
  )
}
