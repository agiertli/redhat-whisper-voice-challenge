import { useEffect, useState } from 'react'

// Name-tag sticker: a greeting in a random language is already a tiny challenge.
const HELLOS = ['Cześć!', 'Ahoj!', 'Servus!', 'Hola!', 'Bok!', 'Hej!', 'Ciao!', 'こんにちは!', 'Szia!', 'Olá!']

export default function Sticker() {
  const [i, setI] = useState(0)
  useEffect(() => {
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return
    const t = setInterval(() => setI((n) => (n + 1) % HELLOS.length), 1800)
    return () => clearInterval(t)
  }, [])
  return (
    <div className="badge" aria-label="Example name tag with a Whisper sticker">
      <div className="badge-clip" />
      <div className="badge-event">Your conference</div>
      <div className="sticker">
        <b key={i}>{HELLOS[i]}</b>
        <span>Come play with AI</span>
        <span className="sticker-rh">at the Red Hat booth</span>
      </div>
      <div className="badge-name">Jana Novak<small>Example Corp</small></div>
    </div>
  )
}
