import { Routes, Route } from 'react-router'
import Header from './components/Header'
import Hero from './components/Hero'
import Footer from './components/Footer'
import CookieBanner from './components/CookieBanner'
import Privacy from './screens/Privacy'

function LandingPage() {
  return (
    <>
      <Header />
      <main>
        <Hero />
        {/* Phase 3: Features, HowItWorks, Tariffs, Compliance, FAQ */}
      </main>
      <Footer />
      <CookieBanner />
    </>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/privacy" element={<Privacy />} />
    </Routes>
  )
}
