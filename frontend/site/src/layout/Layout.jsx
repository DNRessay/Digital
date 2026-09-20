import { Outlet } from 'react-router-dom'
import Header from '../components/Header.jsx'
import Footer from '../components/Footer.jsx'
import useOrbitChrome from '../hooks/useOrbitChrome.js'

export default function Layout() {
  useOrbitChrome()

  return (
    <>
      <Header />
      <main className="main">
        <Outlet />
      </main>
      <Footer />
      <a href="#" id="scroll-top" className="scroll-top d-flex align-items-center justify-content-center" onClick={(e) => e.preventDefault()}>
        <i className="bi bi-arrow-up-short"></i>
      </a>
    </>
  )
}
