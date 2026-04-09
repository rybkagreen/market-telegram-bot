import { Routes, Route } from 'react-router'
import { ThemeProvider } from './context/ThemeContext'
import Header from './components/Header'
import Hero from './components/Hero'
import Features from './components/Features'
import HowItWorks from './components/HowItWorks'
import Tariffs from './components/Tariffs'
import Compliance from './components/Compliance'
import FAQ from './components/FAQ'
import Footer from './components/Footer'
import CookieBanner from './components/CookieBanner'
import Privacy from './screens/Privacy'

function LandingPage() {
  return (
    <>
      <Header />
      <main>
        <Hero />
        <Features />
        <HowItWorks />
        <Tariffs />
        <Compliance />
        <FAQ />
      </main>
      <Footer />
      <CookieBanner />
    </>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/privacy" element={<Privacy />} />
      </Routes>
    </ThemeProvider>
  )
}
