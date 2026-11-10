import { useState } from 'react'

// Passers-by drift toward the booth when the facilitator announces a Hard game.
const PEOPLE = [
  [60, 210], [120, 120], [175, 240], [230, 80], [270, 190], [90, 60], [320, 255],
  [350, 110], [40, 150], [205, 155], [300, 40], [150, 280], [380, 200], [255, 265],
]
const SPOTS = [
  [470, 150], [455, 190], [470, 230], [500, 110], [510, 265], [420, 130], [425, 170],
  [415, 215], [440, 255], [390, 150], [385, 195], [395, 240], [545, 92], [550, 282],
]

function Person({ x, y, color = '#707070' }) {
  return (
    <g>
      <circle cx={x} cy={y - 16} r="7" fill={color} />
      <rect x={x - 8} y={y - 7} width="16" height="22" rx="7" fill={color} />
    </g>
  )
}

export default function HardHype() {
  const [on, setOn] = useState(false)
  return (
    <div className="hype">
      <svg viewBox="0 0 800 320" role="img" aria-label={on ? 'A crowd has gathered around the booth to watch the Hard game.' : 'People walk past the booth.'}>
        {/* booth */}
        <rect x="600" y="60" width="170" height="210" fill="#fff" stroke="#151515" strokeWidth="2" />
        <rect x="620" y="76" width="130" height="78" rx="4" fill="#151515" />
        <text x="685" y="110" textAnchor="middle" fill="#ee0000" fontFamily="Red Hat Display" fontWeight="800" fontSize="15">HARD</text>
        <text x="685" y="130" textAnchor="middle" fill="#fff" fontFamily="Red Hat Text" fontSize="11">日本語 · 한국어 · العربية</text>
        <rect x="610" y="196" width="150" height="16" fill="#d2d2d2" />
        <text x="685" y="296" textAnchor="middle" fill="#4d4d4d" fontFamily="Red Hat Text" fontSize="13">Your booth</text>
        {/* player + facilitator */}
        <Person x={585} y={200} color="#151515" />
        <Person x={565} y={150} color="#ee0000" />
        {/* crowd */}
        {PEOPLE.map(([x, y], i) => {
          const [tx, ty] = SPOTS[i]
          return (
            <g key={i} className="person" style={{ transform: on ? `translate(${tx - x}px, ${ty - y}px)` : 'none', transitionDelay: `${(i % 7) * 70}ms` }}>
              <Person x={x} y={y} />
            </g>
          )
        })}
      </svg>
      {on && <div className="hype-shout" key="shout">EVERYBODY STOP. WE ARE ABOUT TO PLAY HARD!</div>}
      <div className="hype-bar">
        <span className="muted small">{on ? 'People come to watch, and the next player is already in the queue.' : 'Someone just picked Hard. What do you do?'}</span>
        <button className="btn primary small" onClick={() => setOn((v) => !v)} aria-pressed={on}>
          {on ? 'Reset the scene' : 'Make the announcement'}
        </button>
      </div>
    </div>
  )
}
