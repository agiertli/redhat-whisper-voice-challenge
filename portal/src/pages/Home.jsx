import GameScreen from '../components/GameScreen.jsx'
import { prefersReducedMotion, useTimeline } from '../components/RoundSimulator.jsx'
import { SCENARIOS } from '../scenarios.js'
import { href } from '../router.js'
import LayerStack from '../components/LayerStack.jsx'

const EASIEST = [['English', 97.0], ['Portuguese', 93.9], ['Italian', 93.5], ['Romanian', 92.5]]
const HARDEST = [['Korean', 18.1], ['Chinese', 16.0], ['Thai', 13.0], ['Japanese', 6.7]]

function Rows({ data, hard }) {
  return (
    <ul className={`lang-rows ${hard ? 'hard' : ''}`}>
      {data.map(([l, v]) => (
        <li key={l}><span>{l}</span><span className="bar"><i style={{ width: `${v}%` }} /></span><span className="pct">{v}%</span></li>
      ))}
    </ul>
  )
}

function HeroScreen() {
  const tl = useTimeline(SCENARIOS[0], { loop: true, autoplay: !prefersReducedMotion() })
  return (
    <div>
      <GameScreen s={tl.state} />
      <p className="hero-caption">One round, start to finish. It takes about ten seconds.</p>
    </div>
  )
}

export default function Home() {
  return (
    <>
      <section className="hero">
        <div className="wrap">
          <div>
            <h1>The booth where people queue up to break our AI.</h1>
            <p className="lede">
              Whisper Voice Challenge is a five-round party game. Read a phrase in some language, say it out loud,
              and a speech model running on OpenShift AI scores how well it understood you. No cloud. Plenty of laughing.
            </p>
            <div className="hero-actions">
              <a className="btn primary" href={href('facilitator')}>I’m facilitating</a>
              <a className="btn" href={href('tech')}>I’m the tech owner</a>
            </div>
          </div>
          <HeroScreen />
        </div>
      </section>

      <section className="proof" aria-labelledby="proof-h">
        <div className="wrap">
          <div>
            <h3 id="proof-h">Innovate Together Sibenik, October 2026</h3>
            <p className="big"><b>145</b> players, <b>214</b> games, <b>1,104</b> attempts in <b>29</b> languages. One in four was a perfect score.</p>
          </div>
          <div>
            <h3>Easiest for Whisper</h3>
            <Rows data={EASIEST} />
          </div>
          <div>
            <h3>Toughest for humans</h3>
            <Rows data={HARDEST} hard />
          </div>
        </div>
      </section>

      <section className="doors" aria-labelledby="doors-h">
        <div className="wrap">
          <h2 id="doors-h">Pick your job</h2>
          <p className="muted">Two roles keep a booth alive. Read yours first. Reading both doesn’t hurt.</p>
          <div className="door-grid">
            <a className="door" href={href('facilitator')}>
              <span className="who">Facilitator</span>
              <span className="role">You run the show at the booth.</span>
              <ul className="door-list">
                <li>Getting strangers to grab the mic</li>
                <li>The ten-second rhythm of a perfect round</li>
                <li>What to do when the AI breaks (hint: laugh)</li>
              </ul>
              <span className="door-go">Read the facilitator guide · 6 min</span>
            </a>
            <a className="door" href={href('tech')}>
              <span className="who">Tech owner</span>
              <span className="role">You make sure it works, all day.</span>
              <ul className="door-list">
                <li>Two clusters, backups, an agent that installs it for you</li>
                <li>The booth kit: two TVs, one Mac, one good mic</li>
                <li>Local languages, campaign phrases, how scoring works</li>
              </ul>
              <span className="door-go">Read the tech owner guide · 8 min</span>
            </a>
          </div>
        </div>
      </section>

      <section className="pipeline" aria-labelledby="pipe-h">
        <div className="wrap">
          <h2 id="pipe-h">What happens when someone speaks</h2>
          <p className="muted">Scroll down and follow the voice.</p>
          <LayerStack />
          <p className="say" style={{ marginTop: 0 }}>That’s the Sovereign AI pitch, by the way. And people just played it.</p>
        </div>
      </section>
    </>
  )
}
