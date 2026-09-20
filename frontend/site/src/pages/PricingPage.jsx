import { useEffect } from 'react'
import Pricing from '../sections/Pricing.jsx'

export default function PricingPage() {
  useEffect(() => {
    document.title = 'Pricing — Vicinic'
  }, [])

  return <Pricing standalone />
}
