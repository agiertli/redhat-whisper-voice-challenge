import { useState } from 'react'

const ITEMS = {
  mac: {
    title: 'A high-spec laptop',
    lines: [
      'Audio is processed in the browser, so the laptop matters. Bring a recent, well-specced one.',
      'Any M-series Mac does the job, even an M1. A high-end Windows laptop should be fine too.',
      'Whatever you bring, play a few rounds on it at the booth before doors open.',
      'Chrome, full screen, sleep and notifications off. Displays: mirror to TV 1, extend to TV 2.',
    ],
  },
  tv1: {
    title: 'TV 1: the game, mirrored',
    lines: [
      'Shows exactly what the laptop shows, so the crowd follows the phrase, the countdown and the score.',
      'Point it at the aisle. It is your best hook.',
    ],
  },
  tv2: {
    title: 'TV 2: /tv leaderboard, extended',
    lines: [
      'Live top players in full screen. It quietly does the selling while you play.',
      'Running without the tournament? /tv is switched off, so show /architecture instead.',
    ],
  },
  mic: {
    title: 'DJI Mic Mini 2',
    lines: [
      'Pairs with the laptop over Bluetooth. Pick it in the game’s microphone list before the first round.',
      'One transmitter goes to the player. The other waits charged in the case: swap at lunch.',
      'Keep it close to the player’s mouth and away from chatty friends.',
    ],
  },
  tablet: {
    title: 'Registration tablet (optional)',
    lines: [
      'Worth it when registration asks for name and email. The tablet shows only /register.',
      'People register while they wait, then type just their nickname at the game. The mic stays busy, the queue moves.',
      'Not needed with username-only registration: /register just redirects to the game.',
    ],
  },
  people: {
    title: 'Two facilitators, always',
    lines: [
      'The host runs rounds and brings the energy.',
      'The guide (the more technical one) takes whoever wants to talk Sovereign AI or OpenShift AI, without stopping the game.',
    ],
  },
  queue: {
    title: 'The crowd',
    lines: [
      'You want a queue, just not a long one. Three to five people waiting is the sweet spot.',
      'Longer than that? Snappier rounds, deep-dive talks go to the guide, and send newcomers to the registration tablet first.',
    ],
  },
}

const ORDER = ['tv1', 'tv2', 'mac', 'mic', 'tablet', 'people', 'queue']

function Hot({ id, on, set, children, label }) {
  return (
    <g className={`hot ${on === id ? 'on' : ''}`} tabIndex="0" role="button" aria-label={label} aria-pressed={on === id}
      onClick={() => set(id)} onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), set(id))}>
      {children}
    </g>
  )
}

const P = ({ x, y, c = '#707070' }) => (
  <g><circle cx={x} cy={y} r="11" fill={c} /><circle cx={x} cy={y} r="5" fill="#fff" opacity=".25" /></g>
)

export default function BoothDiagram() {
  const [on, setOn] = useState('mac')
  const item = ITEMS[on]
  const t = { fontFamily: 'Red Hat Text', fontSize: 16, fill: '#151515' }
  return (
    <div className="booth">
      <svg viewBox="80 14 560 418" role="group" aria-label="Booth layout seen from above. Select a part to learn more.">
        <rect x="20" y="20" width="660" height="10" fill="#151515" />
        <text x="350" y="50" textAnchor="middle" {...t} fill="#707070" fontSize="15">back wall</text>

        {/* cables */}
        <path d="M320 205 C 260 150, 220 120, 210 92" fill="none" stroke="#151515" strokeWidth="2" className="signal" />
        <path d="M380 205 C 440 150, 480 120, 490 92" fill="none" stroke="#151515" strokeWidth="2" className="signal" />
        <path d="M352 318 L 352 252" fill="none" stroke="#ee0000" strokeWidth="2" className="signal" />

        <Hot id="tv1" on={on} set={setOn} label="TV 1, game screen">
          <rect className="hl" x="110" y="62" width="200" height="30" rx="3" fill="#151515" stroke="#151515" />
          <text x="210" y="82" textAnchor="middle" fill="#fff" fontFamily="Red Hat Display" fontWeight="700" fontSize="16">TV 1 · game</text>
          <text x="210" y="112" textAnchor="middle" {...t} fontSize="15">mirrored</text>
        </Hot>
        <Hot id="tv2" on={on} set={setOn} label="TV 2, leaderboard">
          <rect className="hl" x="390" y="62" width="200" height="30" rx="3" fill="#151515" stroke="#151515" />
          <text x="490" y="82" textAnchor="middle" fill="#fff" fontFamily="Red Hat Display" fontWeight="700" fontSize="16">TV 2 · /tv</text>
          <text x="490" y="112" textAnchor="middle" {...t} fontSize="15">extended</text>
        </Hot>

        <rect x="170" y="180" width="360" height="72" fill="#e6e6e6" stroke="#bdbdbd" />
        <Hot id="mac" on={on} set={setOn} label="Laptop">
          <rect className="hl" x="312" y="192" width="78" height="50" rx="4" fill="#fff" stroke="#151515" strokeWidth="2" />
          <text x="351" y="223" textAnchor="middle" {...t} fontWeight="700">Laptop</text>
        </Hot>
        <Hot id="mic" on={on} set={setOn} label="DJI Mic Mini 2">
          <rect className="hl" x="440" y="196" width="80" height="42" rx="6" fill="#fff" stroke="#151515" strokeWidth="1.5" />
          <text x="480" y="214" textAnchor="middle" {...t} fontSize="13">case</text>
          <text x="480" y="230" textAnchor="middle" {...t} fontSize="13">+ TX 2</text>
          <circle className="hl" cx="352" cy="324" r="7" fill="#ee0000" stroke="#ee0000" />
        </Hot>

        <Hot id="people" on={on} set={setOn} label="Facilitators">
          <circle className="hl" cx="250" cy="300" r="15" fill="#ee0000" stroke="#ee0000" />
          <text x="250" y="334" textAnchor="middle" {...t} fontSize="15">host</text>
          <circle className="hl" cx="590" cy="300" r="15" fill="#ee0000" stroke="#ee0000" />
          <text x="590" y="334" textAnchor="middle" {...t} fontSize="15">guide</text>
        </Hot>
        <Hot id="tablet" on={on} set={setOn} label="Registration tablet">
          <rect className="hl" x="96" y="276" width="44" height="58" rx="5" fill="#fff" stroke="#151515" strokeWidth="2" />
          <rect x="102" y="284" width="32" height="40" fill="#151515" />
          <text x="118" y="352" textAnchor="middle" {...t} fontSize="15">tablet</text>
        </Hot>
        <P x={352} y={300} c="#151515" />
        <text x="352" y="350" textAnchor="middle" {...t} fontSize="15" fontWeight="600">player</text>

        <Hot id="queue" on={on} set={setOn} label="Crowd and queue">
          <rect className="hl" x="150" y="364" width="400" height="58" rx="29" fill="transparent" stroke="#d2d2d2" strokeDasharray="4 4" />
          {[190, 232, 274, 316, 388, 430, 472, 514].map((x, i) => <P key={x} x={x} y={393 + (i % 2 ? 6 : -4)} />)}
          <text x="352" y="398" textAnchor="middle" {...t} fontSize="15" fill="#4d4d4d">crowd</text>
        </Hot>
      </svg>
      <div className="booth-info" aria-live="polite">
        <h3>{item.title}</h3>
        <ul>{item.lines.map((l) => <li key={l}>{l}</li>)}</ul>
        <div className="booth-pick">
          {ORDER.map((k) => (
            <button key={k} className="sim-tab" aria-selected={k === on} onClick={() => setOn(k)} style={{ padding: '6px 12px', fontSize: '0.85rem' }}>
              {ITEMS[k].title.split(':')[0].replace('Two facilitators, always', 'Facilitators').replace(' (optional)', '')}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
