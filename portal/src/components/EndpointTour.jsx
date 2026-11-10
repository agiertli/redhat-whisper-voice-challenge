import { useState } from 'react'

const BOARD = [
  ['🥇', 'PolyglotPro', 'Hard', 221.4],
  ['🥈', 'Marta_ZG', 'Hard', 204.9],
  ['🥉', 'tomas-k', 'Medium', 171.3],
  ['4', 'NotARobot', 'Medium', 158.0],
  ['5', 'Ola', 'Easy', 117.6],
]

const EPS = [
  {
    path: '/',
    name: 'The game',
    who: 'Facilitators',
    text: 'What players see on the laptop and TV 1. Registration, difficulty, the five rounds.',
    view: () => (
      <div className="mini">
        <h6>Join the Voice Challenge</h6>
        <p style={{ color: '#a3a3a3', margin: '0 0 12px' }}>Username (public, shown on leaderboard)</p>
        <div style={{ background: '#292929', border: '1px solid #383838', padding: 8, borderRadius: 3, marginBottom: 12 }}>PolyglotPro</div>
        <div style={{ display: 'grid', gap: 6 }}>
          <div style={{ background: '#63993d', padding: 8, borderRadius: 3, fontWeight: 600 }}>🥉 EASY · Bronze prize</div>
          <div style={{ background: '#0066cc', padding: 8, borderRadius: 3, fontWeight: 600 }}>🥈 MEDIUM · Silver prize</div>
          <div style={{ background: '#ee0000', padding: 8, borderRadius: 3, fontWeight: 600 }}>🥇 HARD · Gold prize (日本語, 한국어, العربية…)</div>
        </div>
      </div>
    ),
  },
  {
    path: '/tv',
    name: 'Leaderboard',
    who: 'Everyone walking past',
    text: 'Full screen on TV 2. Updates live. Switched off when the tournament is disabled.',
    view: () => (
      <div className="mini">
        <h6>Innovate Together · Leaderboard</h6>
        <table><tbody>
          {BOARD.map(([r, n, d, s]) => (
            <tr key={n}><td style={{ width: 30 }}>{r}</td><td className={r === '🥇' ? 'gold' : ''}>{n}</td><td><span className="chip">{d}</span></td><td>{s}</td></tr>
          ))}
        </tbody></table>
      </div>
    ),
  },
  {
    path: '/admin',
    name: 'Admin',
    who: 'Tech owner',
    text: 'Players, games, follow-up flags for leads, CSV export, backup and restore. Behind the admin password, so keep it off TVs.',
    view: () => (
      <div className="mini">
        <h6>Tournament Admin</h6>
        <table><tbody>
          <tr><td>PolyglotPro</td><td><span className="chip">3 games</span></td><td>☑ follow up</td></tr>
          <tr><td>Marta_ZG</td><td><span className="chip">5 games</span></td><td>☐ follow up</td></tr>
          <tr><td>tomas-k</td><td><span className="chip">1 game</span></td><td>☑ follow up</td></tr>
        </tbody></table>
        <div className="flow"><div>Export CSV</div><div>Download backup</div><div>Restore</div></div>
      </div>
    ),
  },
  {
    path: '/architecture',
    name: 'Architecture',
    who: 'The guide',
    text: 'An interactive walkthrough of what runs where. Perfect when someone asks, “so where does my voice go?”',
    view: () => (
      <div className="mini">
        <h6>Whisper UI Architecture</h6>
        <div className="flow">
          <div>🎙 Browser<br /><span>mic + voice detection</span></div><span>→</span>
          <div>Game app<br /><span>OpenShift</span></div><span>→</span>
          <div className="red">Whisper large-v3<br /><span>vLLM on OpenShift AI · GPU</span></div>
        </div>
        <p style={{ color: '#a3a3a3', marginTop: 18 }}>Nothing leaves the cluster. No cloud API in the loop.</p>
      </div>
    ),
  },
]

export default function EndpointTour() {
  const [i, setI] = useState(0)
  const ep = EPS[i]
  return (
    <div className="ep">
      <ul className="ep-list" role="tablist" aria-label="Endpoints">
        {EPS.map((e, k) => (
          <li key={e.path}>
            <button role="tab" aria-selected={k === i} onClick={() => setI(k)}>
              <b>{e.path}</b>{e.name}
            </button>
          </li>
        ))}
      </ul>
      <div className="ep-view" role="tabpanel">
        <p><strong>For {ep.who.toLowerCase()}.</strong> {ep.text}</p>
        <div className="browser">
          <div className="browser-bar"><i /><i /><i /><span>https://whisper.apps.your-cluster{ep.path}</span></div>
          {ep.view()}
        </div>
      </div>
    </div>
  )
}
