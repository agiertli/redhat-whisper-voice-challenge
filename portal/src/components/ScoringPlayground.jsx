import { useMemo, useState } from 'react'
import { accuracy, diff, MULTIPLIER, ROMANIZATION_PENALTY, speedBonus, totalScore, WIN } from '../scoring.js'

const PHRASE = 'Red Hat leads in open source innovation'
const PRESETS = [
  ['Perfect', 'Red Hat leads in open source innovation'],
  ['Strong accent', 'Red Hat lids in open sorce inovation'],
  ['Friend chimed in', 'Red Hat leads in open source innovation ha ha nice one'],
  ['Stopped early', 'Red Hat leads in'],
  ['Hesitated', 'Thank you. Uh, Red Hat leads in open source innovation'],
]

export default function ScoringPlayground() {
  const [text, setText] = useState(PRESETS[1][1])
  const [level, setLevel] = useState('medium')
  const [secs, setSecs] = useState(90)
  const [roman, setRoman] = useState(false)

  const raw = useMemo(() => accuracy(text, PHRASE), [text])
  const marks = useMemo(() => diff(text, PHRASE), [text])
  const acc = roman ? raw * (1 - ROMANIZATION_PENALTY) : raw
  const win = acc >= WIN
  const score = totalScore(level, acc, secs)

  return (
    <div className="play">
      <div className="play-in">
        <div className="field">
          <label>Challenge phrase</label>
          <div style={{ fontFamily: 'var(--display)', fontWeight: 700, fontSize: '1.2rem' }}>{PHRASE}</div>
        </div>
        <div className="field">
          <label htmlFor="tr">What Whisper heard</label>
          <input id="tr" type="text" value={text} onChange={(e) => setText(e.target.value)} spellCheck="false" />
          <div className="presets" style={{ marginTop: 8 }}>
            {PRESETS.map(([n, v]) => (
              <button key={n} className="sim-tab" style={{ padding: '5px 11px', fontSize: '0.82rem' }} aria-selected={text === v} onClick={() => setText(v)}>{n}</button>
            ))}
          </div>
        </div>
        <div className="field">
          <label>Difficulty</label>
          <div className="seg" role="group" aria-label="Difficulty">
            {Object.keys(MULTIPLIER).map((k) => (
              <button key={k} aria-pressed={k === level} onClick={() => setLevel(k)}>{k[0].toUpperCase() + k.slice(1)} ×{MULTIPLIER[k]}</button>
            ))}
          </div>
        </div>
        <div className="field">
          <label htmlFor="secs">Whole game took {secs} s</label>
          <input id="secs" type="range" min="30" max="300" step="5" value={secs} onChange={(e) => setSecs(+e.target.value)} />
          <div className="hint">Measured from game start to finish, chit-chat included.</div>
        </div>
        <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontWeight: 600, fontSize: '0.92rem' }}>
          <input type="checkbox" checked={roman} onChange={(e) => setRoman(e.target.checked)} style={{ accentColor: 'var(--red)', width: 18, height: 18 }} />
          Player revealed the pronunciation (−{ROMANIZATION_PENALTY * 100}%)
        </label>
      </div>

      <div className="play-out" aria-live="polite">
        <div className="field">
          <label>Character by character</label>
          <div className="diff">
            {marks.length ? marks.map((m, i) => <span key={i} className={m.ok ? 'ok' : 'bad'}>{m.ch === ' ' ? ' ' : m.ch}</span>) : <span className="muted">Nothing heard</span>}
          </div>
        </div>
        <div className="meter">
          <div className="meter-track">
            <div className={`meter-fill ${win ? 'win' : ''}`} style={{ width: `${Math.max(0, acc) * 100}%` }} />
            <div className="meter-line"><span>80%</span></div>
          </div>
        </div>
        <div className={`verdict ${win ? 'win' : 'lose'}`}>{(acc * 100).toFixed(1)}% · {win ? 'round passed' : 'below 80%'}</div>
        <div className="calc">
          <div className="row"><span>avg accuracy (if every round went like this)</span><span>{acc.toFixed(3)}</span></div>
          <div className="row"><span>× difficulty</span><span>{MULTIPLIER[level].toFixed(1)}</span></div>
          <div className="row"><span>× speed bonus</span><span>{speedBonus(secs).toFixed(2)}</span></div>
          <div className="row"><span>× 100</span><span /></div>
          <div className="total">{score.toFixed(1)}</div>
        </div>
        <p className="small muted" style={{ marginTop: 8 }}>
          Accuracy = 1 − edit distance ÷ length of the longer text, after lowercasing and dropping punctuation.
          Accents count. To win, the average over five rounds must be at least 80%. Hard can lose and still beat an Easy winner on the leaderboard.
        </p>
      </div>
    </div>
  )
}
