import { useState } from 'react'
import { ROMANIZATION_PENALTY } from '../scoring.js'

// Illustrative presets: the owner picks Easy languages the local crowd can actually say.
const BOOTHS = {
  Prague: { first: 'Czech', easy: ['Czech', 'Slovak', 'English', 'Polish', 'German'] },
  Munich: { first: 'German', easy: ['German', 'English', 'Dutch', 'French', 'Spanish'] },
  Zagreb: { first: 'Croatian', easy: ['Croatian', 'Serbian', 'Slovenian', 'English', 'Italian'] },
}

const THEMES = {
  Default: ['OpenShift is great product', 'Red Hat leads in open source innovation', 'Kubernetes simplifies application deployment'],
  Ansible: ['Ansible automates the boring parts', 'Playbooks turn chaos into routine', 'Event-Driven Ansible reacts before you do'],
}

export default function Customize() {
  const [booth, setBooth] = useState('Prague')
  const [theme, setTheme] = useState('Default')
  const [shown, setShown] = useState(false)
  const b = BOOTHS[booth]
  return (
    <div className="custom-grid">
      <section>
        <h3>Easy means local</h3>
        <p>Easy should feel easy to <em>this</em> crowd. Each booth gets its own language pools, and the first round is always in the language you choose at install.</p>
        <div className="seg" role="group" aria-label="Example booth">
          {Object.keys(BOOTHS).map((k) => <button key={k} aria-pressed={k === booth} onClick={() => setBooth(k)}>{k}</button>)}
        </div>
        <div className="chips" aria-live="polite">
          {b.easy.map((l) => <span key={l} className={`chip ${l === b.first ? 'first' : ''}`}>{l}</span>)}
        </div>
        <p className="small">Dark chip: first-round language.</p>
      </section>
      <section>
        <h3>Phrases follow the campaign</h3>
        <p>Marketing pushing Ansible this quarter? Ask <code>/whisper-operations</code> for Ansible phrases in every booth language. No rebuild.</p>
        <div className="seg" role="group" aria-label="Phrase theme">
          {Object.keys(THEMES).map((k) => <button key={k} aria-pressed={k === theme} onClick={() => setTheme(k)}>{k}</button>)}
        </div>
        <ul className="small" style={{ paddingLeft: '1.1em', marginTop: 12 }} aria-live="polite">
          {THEMES[theme].map((p) => <li key={p}>“{p}”</li>)}
        </ul>
      </section>
      <section>
        <h3>Romanization, the secret weapon</h3>
        <p>Nobody reads Korean at a booth. It’s on by default (<code>showRomanization: optional</code>): players can reveal how to say it and accept a {ROMANIZATION_PENALTY * 100}% hit to that round.</p>
        <div className="romcard">
          <div className="p">OpenShiftは素晴らしい製品です</div>
          <div className="r">{shown ? 'OpenShift wa subarashii seihin desu' : ''}</div>
          <button onClick={() => setShown((v) => !v)} aria-pressed={shown}>
            {shown ? `Revealed · round score ×${1 - ROMANIZATION_PENALTY}` : 'Show pronunciation'}
          </button>
        </div>
        <p className="small">Turns “impossible” into “one more try”, which is the whole point.</p>
      </section>
    </div>
  )
}
