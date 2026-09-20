import { useEffect, useState } from 'react'
import Hero from '../sections/Hero.jsx'
import About from '../sections/About.jsx'
import Services from '../sections/Services.jsx'
import Pricing from '../sections/Pricing.jsx'
import Portfolio from '../sections/Portfolio.jsx'
import WhyUs from '../sections/WhyUs.jsx'
import Contact from '../sections/Contact.jsx'

export default function Home() {
  const [showPreloader, setShowPreloader] = useState(true)

  useEffect(() => {
    document.title = 'Vicinic — Websites & WhatsApp Systems for Small Businesses'

    if (document.readyState === 'complete') {
      setShowPreloader(false)
      return
    }
    const onLoad = () => setShowPreloader(false)
    window.addEventListener('load', onLoad)
    return () => window.removeEventListener('load', onLoad)
  }, [])

  return (
    <>
      {showPreloader && <div id="preloader"></div>}
      <Hero />
      <About />
      <Services />
      <Pricing />
      <Portfolio />
      <WhyUs />
      <Contact />
    </>
  )
}
