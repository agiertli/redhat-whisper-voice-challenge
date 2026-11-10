import { useEffect } from 'react'
import { href, useRoute } from './router.js'
import Mark from './components/Mark.jsx'
import Home from './pages/Home.jsx'
import Facilitator from './pages/Facilitator.jsx'
import TechOwner from './pages/TechOwner.jsx'
import CheatSheet from './pages/CheatSheet.jsx'
import { REPO } from './links.js'
import { Mail } from './components/Contact.jsx'

const PAGES = {
  home: { C: Home, title: 'Booth guide' },
  facilitator: { C: Facilitator, title: 'Facilitator guide' },
  tech: { C: TechOwner, title: 'Tech owner guide' },
  cheatsheet: { C: CheatSheet, title: 'Cheat sheet' },
}

export default function App() {
  const { page, section } = useRoute()
  const current = PAGES[page] ? page : 'home'
  const { C, title } = PAGES[current]

  useEffect(() => {
    document.title = `${title} · Whisper Voice Challenge`
    if (!section) window.scrollTo(0, 0)
  }, [current]) // eslint-disable-line react-hooks/exhaustive-deps

  const nav = [['facilitator', 'Facilitators'], ['tech', 'Tech owners'], ['cheatsheet', 'Cheat sheet']]
  return (
    <>
      <a href="#main" className="skip" onClick={(e) => { e.preventDefault(); document.getElementById('main')?.focus() }}>Skip to content</a>
      <header className="topbar">
        <div className="wrap">
          <a className="brand" href={href('home')}>
            <Mark />
            <span>Whisper Voice Challenge<small>Booth guide</small></span>
          </a>
          <nav className="topnav" aria-label="Main">
            {nav.map(([p, label]) => (
              <a key={p} href={href(p)} aria-current={current === p ? 'page' : undefined}>{label}</a>
            ))}
          </nav>
        </div>
      </header>
      <main id="main" tabIndex="-1" style={{ outline: 'none' }}>
        <C section={section} />
      </main>
      <footer className="foot">
        <div className="wrap">
          <span>Whisper Voice Challenge, a Red Hat booth game running on OpenShift AI. Created by Anton Giertli. <Mail>Get in touch</Mail>.</span>
          <a href={REPO}>Source and docs on GitHub</a>
        </div>
      </footer>
    </>
  )
}
