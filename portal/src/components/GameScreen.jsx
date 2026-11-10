import { useLayoutEffect, useRef, useState } from 'react'
import Mark from './Mark.jsx'

// A faithful-enough mock of the booth game screen (src/templates/index.html, v2.13).
// Pure presentation: everything it shows comes from `s`.
export const BASE = {
  phase: 'ready',          // ready | countdown | speak | listening | stopped
  count: 3,
  transcript: '',
  extra: '',               // text picked up after the phrase (noise or hallucination)
  extraKind: 'noise',      // noise | loop
  vad: 'on',               // idle | on | speaking
  status: 'Ready',
  timer: 0,
  flag: '🇬🇧',
  lang: 'English',
  phrase: 'Red Hat leads in open source innovation',
  roman: '',
  round: 2,
  rounds: ['done'],
  avg: '100%',
  score: null,
  pressed: null,           // start | stop
  cursor: 'off',           // off | start | stop | rest
  click: 0,                // bump to replay the ripple
  bubble: null,            // { who: 'player' | 'other' | 'host', text }
}

const fmt = (t) => `00:${String(Math.floor(t)).padStart(2, '0')}`

export default function GameScreen({ s, label }) {
  const root = useRef(null)
  const startRef = useRef(null)
  const stopRef = useRef(null)
  const [pos, setPos] = useState({ x: '70%', y: '80%' })

  useLayoutEffect(() => {
    const place = () => {
      const box = root.current?.getBoundingClientRect()
      const target = s.cursor === 'start' ? startRef.current : s.cursor === 'stop' ? stopRef.current : null
      if (!box) return
      if (!target) { setPos({ x: '72%', y: '86%' }); return }
      const r = target.getBoundingClientRect()
      setPos({ x: `${r.left - box.left + r.width * 0.55}px`, y: `${r.top - box.top + r.height * 0.6}px` })
    }
    place()
    window.addEventListener('resize', place)
    return () => window.removeEventListener('resize', place)
  }, [s.cursor])

  const recording = s.phase === 'speak' || s.phase === 'listening'
  const scoreClass = s.score == null ? 'idle' : s.score >= 80 ? 'win' : 'lose'

  let box
  if (s.phase === 'countdown') box = <div className="g-trans"><span className="g-count" key={s.count}>{s.count}</span></div>
  else if (s.phase === 'speak') box = <div className="g-trans"><span className="g-count speak">🎤 SPEAK!</span></div>
  else if (s.transcript || s.extra) {
    box = (
      <div className="g-trans text">
        <span>
          {s.transcript}
          {s.extra && <span className={s.extraKind === 'loop' ? 'loop' : 'noise'}> {s.extra}</span>}
        </span>
      </div>
    )
  } else box = <div className="g-trans"><span style={{ color: 'var(--g-muted)' }}>{recording ? 'Listening…' : 'Transcript appears here'}</span></div>

  return (
    <div className="tv">
      {label && <span className="tv-label">{label}</span>}
      <div className="game" ref={root} role="img" aria-label={`Game screen: ${s.status}. ${s.transcript ? `Transcript: ${s.transcript} ${s.extra}` : ''}`}>
        <div className="game-bar">
          <Mark /> Whisper Voice Challenge <span className="ver">v2.13 mock</span>
        </div>
        <div className="game-body">
          <div className="g-panel">
            <div className="g-controls">
              <span className="g-select">🎙 DJI Mic Mini 2</span>
              <span ref={startRef} className={`g-btn ${s.pressed === 'start' ? 'pressed' : ''}`} aria-disabled={recording || s.phase === 'countdown'}>Start Recording</span>
              <span ref={stopRef} className={`g-btn stop ${s.pressed === 'stop' ? 'pressed' : ''}`} aria-disabled={!recording}>Stop</span>
            </div>
            <div className="g-status">
              <Mark state={s.vad} className="ind" />
              <span>{s.status}</span>
              <span className="timer">{fmt(s.timer)}</span>
            </div>
            {box}
          </div>
          <div className="g-bottom">
            <div className="g-panel">
              <div className="g-meta"><span>Challenge {s.round}/5 · need ≥80% avg</span><span>Avg {s.avg}</span></div>
              <div className="g-progress">
                {[0, 1, 2, 3, 4].map((i) => (
                  <i key={i} className={s.rounds[i] || (i === s.round - 1 ? 'now' : '')} />
                ))}
              </div>
              <div className="g-card">
                <div className="g-lang">{s.flag} {s.lang}</div>
                <div className="g-phrase">{s.phrase}</div>
                {s.roman && <div className="g-roman">{s.roman}</div>}
              </div>
            </div>
            <div className="g-panel g-score">
              <small>Score</small>
              <b className={scoreClass}>{s.score == null ? '--' : `${s.score}%`}</b>
            </div>
          </div>
        </div>

        {s.bubble && <div className={`speech ${s.bubble.who}`} key={s.bubble.text}>{s.bubble.text}</div>}

        <svg className={`cursor ${s.click ? 'click' : ''}`} key={`c${s.click}`} style={{ left: pos.x, top: pos.y, opacity: s.cursor === 'off' ? 0 : 1 }} viewBox="0 0 24 24" aria-hidden="true">
          <path d="M3 2l7.5 19 2.6-7.9L21 10.5z" fill="#fff" stroke="#151515" strokeWidth="1.4" strokeLinejoin="round" />
        </svg>
      </div>
    </div>
  )
}
