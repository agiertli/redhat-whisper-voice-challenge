import { useEffect, useState } from 'react'
import GameScreen, { BASE } from './GameScreen.jsx'
import { SCENARIOS } from '../scenarios.js'

export const prefersReducedMotion = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

// Plays a scenario's frames in order. Mount with key={scenario.id} to switch scenarios.
export function useTimeline(scenario, { loop = false, autoplay = false } = {}) {
  const initial = () => ({ ...BASE, ...(scenario.base || {}) })
  const [state, setState] = useState(initial)
  const [pos, setPos] = useState(0)
  const [step, setStep] = useState(-1)
  const [playing, setPlaying] = useState(autoplay)

  const reset = () => { setState(initial()); setPos(0); setStep(-1) }
  const done = pos >= scenario.frames.length

  useEffect(() => {
    if (!playing) return
    if (done) {
      if (!loop) { setPlaying(false); return }
      const t = setTimeout(reset, 900)
      return () => clearTimeout(t)
    }
    const f = scenario.frames[pos]
    setState((s) => ({ ...s, ...f.set }))
    if (f.step != null) setStep(f.step)
    const t = setTimeout(() => setPos((p) => p + 1), f.d)
    return () => clearTimeout(t)
  }, [playing, pos]) // eslint-disable-line react-hooks/exhaustive-deps

  return {
    state, step, playing, done,
    play: () => { if (done) reset(); setPlaying(true) },
    pause: () => setPlaying(false),
    replay: () => { reset(); setPlaying(true) },
  }
}

function Player({ scenario, autoplay }) {
  const tl = useTimeline(scenario, { autoplay: autoplay && !prefersReducedMotion() })
  return (
    <div className="sim-stage">
      <GameScreen s={tl.state} label="Main game screen (mirrored)" />
      <div className="sim-side">
        <h3>{scenario.title}</h3>
        <p>{scenario.blurb}</p>
        <ol className="sim-steps" aria-live="polite">
          {scenario.steps.map((st, i) => (
            <li key={i} className={`${i < tl.step ? 'past' : ''} ${i === tl.step ? 'now' : ''} ${st.alert ? 'alert' : ''}`}>
              <span className="n">{i + 1}</span>
              <span>{st.label}</span>
            </li>
          ))}
        </ol>
        <div className="sim-controls">
          {tl.playing
            ? <button className="btn small" onClick={tl.pause}>Pause</button>
            : <button className="btn primary small" onClick={tl.play}>{tl.done ? 'Play again' : tl.step < 0 ? 'Play this round' : 'Resume'}</button>}
          {tl.step >= 0 && !tl.done && <button className="btn small" onClick={tl.replay}>Restart</button>}
        </div>
      </div>
    </div>
  )
}

// Controlled when `id`/`onSelect` are passed (lets other sections jump to a scenario).
export default function RoundSimulator({ id: controlled, onSelect }) {
  const [own, setOwn] = useState('clean')
  const id = controlled ?? own
  const [touched, setTouched] = useState(false)
  const [nonce, setNonce] = useState(0)
  const setId = (x) => { setTouched(true); setNonce((n) => n + 1); (onSelect ?? setOwn)(x) }
  const scenario = SCENARIOS.find((x) => x.id === id)
  return (
    <div className="sim">
      <div className="sim-tabs" role="tablist" aria-label="Round scenarios">
        {SCENARIOS.map((sc) => (
          <button key={sc.id} role="tab" aria-selected={sc.id === id} className="sim-tab" onClick={() => setId(sc.id)}>
            <span className={`dot ${sc.good ? '' : 'bad'}`} />{sc.name}
          </button>
        ))}
      </div>
      <Player key={`${id}-${nonce}`} scenario={scenario} autoplay={touched || id !== 'clean'} />
    </div>
  )
}
