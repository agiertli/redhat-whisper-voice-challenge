import { useEffect, useRef, useState } from 'react'

// Scroll-driven isometric stack: the voice travels from the browser down to the GPU,
// then the transcript comes back up. The stack stays pinned while the steps scroll.
const LAYERS = [
  { name: 'Browser', fill: '#ffffff', ink: '#151515' },
  { name: 'Game app', fill: '#d2d2d2', ink: '#151515' },
  { name: 'Whisper large-v3', fill: '#ff9a9a', ink: '#151515' },
  { name: 'vLLM · OpenShift AI', fill: '#ee0000', ink: '#ffffff' },
  { name: 'OpenShift', fill: '#a60000', ink: '#ffffff' },
  { name: 'NVIDIA GPU', fill: '#151515', ink: '#ffffff' },
]

const STEPS = [
  { h: 'You speak', p: 'The mic feeds the browser, which notices when you start and stop talking and streams the audio. This is why the laptop matters.' },
  { h: 'The game passes it on', p: 'A small web app on OpenShift. It keeps the phrases, the scores and the leaderboard. Your voice just passes through.' },
  { h: 'Whisper listens', p: 'Open-source Whisper large-v3, in an FP8 build from Red Hat AI. Ninety-nine languages, no internet required.' },
  { h: 'vLLM serves it', p: 'The same inference engine OpenShift AI uses for every model. The transcript streams back word by word.' },
  { h: 'OpenShift keeps it alive', p: 'Routes, storage, monitoring, restarts. The boring bits that make a two-day event survivable.' },
  { h: 'On a GPU you own', p: 'One NVIDIA GPU in your own cluster. That’s the whole hardware list. Nothing leaves the building.' },
  { h: 'And back it comes', p: 'Text climbs back up, gets compared with the phrase, and the score lands on the TV before the player has stopped grinning.' },
]

const CX = 220, W = 150, H = 75, T = 18

function Slab({ y, layer, lit, active }) {
  const top = `${CX},${-H} ${CX + W},0 ${CX},${H} ${CX - W},0`
  const left = `${CX - W},0 ${CX},${H} ${CX},${H + T} ${CX - W},${T}`
  const right = `${CX},${H} ${CX + W},0 ${CX + W},${T} ${CX},${H + T}`
  const fill = lit ? layer.fill : '#f2f2f2'
  const stroke = lit ? (layer.fill === '#ffffff' ? '#151515' : 'rgba(0,0,0,.25)') : '#c7c7c7'
  const ink = lit ? layer.ink : '#9a9a9a'
  return (
    <g className="slab" style={{ transform: `translateY(${y - (active ? 16 : 0)}px)` }}>
      <polygon points={left} fill={fill} stroke={stroke} />
      <polygon points={left} fill="#000" opacity={lit ? 0.18 : 0.05} />
      <polygon points={right} fill={fill} stroke={stroke} />
      <polygon points={right} fill="#000" opacity={lit ? 0.32 : 0.1} />
      <polygon points={top} fill={fill} stroke={active ? '#151515' : stroke} strokeWidth={active ? 2 : 1} />
      <text transform={`translate(${CX - W + 22}, 6) skewY(26.565)`} textAnchor="start" fill={ink}
        fontFamily="Red Hat Display" fontWeight="800" fontSize="15" style={{ transition: 'fill .6s' }}>{layer.name}</text>
    </g>
  )
}

export default function LayerStack() {
  const [step, setStep] = useState(0)
  const refs = useRef([])

  useEffect(() => {
    const io = new IntersectionObserver(
      (es) => es.forEach((e) => e.isIntersecting && setStep(+e.target.dataset.i)),
      { rootMargin: '-45% 0px -45% 0px' },
    )
    refs.current.forEach((el) => el && io.observe(el))
    return () => io.disconnect()
  }, [])

  const back = step === STEPS.length - 1
  const gap = 86
  const y0 = 120
  const ys = LAYERS.map((_, i) => y0 + i * gap)
  const voiceY = back ? 18 : ys[step] + 30

  return (
    <div className="stack">
      <div className="stack-pin">
        <svg viewBox="0 0 440 660" role="img" aria-label={`Layer diagram, now showing: ${STEPS[step].h}`}>
          {/* paint bottom-up so higher layers sit on top */}
          {LAYERS.map((l, i) => ({ l, i })).reverse().map(({ l, i }) => (
            <Slab key={l.name} y={ys[i]} layer={l} lit={back || i <= step} active={!back && i === step} />
          ))}
          {/* the voice travelling down / the text travelling back */}
          <g className="voice" style={{ transform: `translateY(${voiceY}px)` }}>
            {back ? (
              <g>
                <rect x={CX - 150} y="-20" width="300" height="40" rx="20" fill="#151515" />
                <text x={CX} y="6" textAnchor="middle" fill="#fff" fontFamily="Red Hat Text" fontWeight="600" fontSize="15">“Red Hat leads in…” · 100%</text>
              </g>
            ) : (
              <g>
                <circle cx={CX} cy="0" r="12" fill="#fff" stroke="#ee0000" strokeWidth="5" />
                {[0, 1, 2].map((k) => <circle key={k} className="ripple-ring" cx={CX} cy="0" r="13" fill="none" stroke="#151515" strokeWidth="2" opacity=".6" style={{ animationDelay: `${k * 0.5}s` }} />)}
              </g>
            )}
          </g>
        </svg>
      </div>
      <ol className="stack-steps">
        {STEPS.map((s, i) => (
          <li key={s.h} data-i={i} ref={(el) => (refs.current[i] = el)} className={i === step ? 'on' : ''}>
            <h3>{s.h}</h3>
            <p>{s.p}</p>
          </li>
        ))}
      </ol>
    </div>
  )
}
