import { useState } from 'react'
import { Chapter, Track } from '../components/Track.jsx'
import Contact from '../components/Contact.jsx'
import RoundSimulator from '../components/RoundSimulator.jsx'
import HardHype from '../components/HardHype.jsx'
import { href } from '../router.js'

const SECTIONS = [
  { id: 'vibe', title: 'The vibe' },
  { id: 'round', title: 'Running a round' },
  { id: 'noise', title: 'Make some noise' },
  { id: 'sideways', title: 'When it goes sideways' },
  { id: 'team', title: 'Two of you' },
  { id: 'prizes', title: 'Prizes and retries' },
]

const FIXES = [
  {
    t: 'Stop clicked too early or too late',
    d: 'The most common mistake, and it’s yours, not the player’s. Wait for the full sentence, then click Stop at once.',
    try: 'early',
  },
  {
    t: 'A friend is talking near the mic',
    d: 'Everything the mic hears ends up in the transcript. Ask the cheering section to cheer after Stop.',
    try: 'late',
  },
  {
    t: 'The player freezes after SPEAK!',
    d: 'Silence turns into made-up words. Before Start, have them read the phrase once in their head and go straight on SPEAK!',
    try: 'hesitate',
  },
  {
    t: 'Whisper loops and won’t stop',
    d: 'When not a single word lands, Whisper can stream the same line for 10–12 seconds. Stop won’t help. Announce “You managed to break AI. Wow!” and enjoy it. Start a new game if you need to. Roughly 5 rounds in 100.',
    try: 'break',
  },
  {
    t: 'A low score and a long face',
    d: 'Find the win: “Japanese on Hard? Respect.” Point at the leaderboard and offer another go.',
  },
]

export default function Facilitator({ section }) {
  const [scenario, setScenario] = useState('clean')
  const jump = (id) => {
    setScenario(id)
    document.getElementById('round')?.scrollIntoView({ behavior: 'smooth' })
  }

  return (
    <>
      <header className="track-head">
        <div className="wrap">
          <p className="who">For facilitators</p>
          <h1>You’re the host. The AI is the show.</h1>
          <p className="lede">Nobody needs to understand speech recognition to have fun at your booth. They need you, a mic and five quick rounds.</p>
        </div>
      </header>

      <Track page="facilitator" sections={SECTIONS} section={section} extra={<a className="print-link" href={href('cheatsheet')}>Printable cheat sheet</a>}>
        <Chapter id="vibe" title="Be the person people want to play with" lede="No script needed. Be natural, keep it light, and make everyone look good.">
          <div className="say">“Fancy a quick game? Takes a minute, and you can win a prize.”</div>
          <div className="pairs">
            <div>
              <h4><span className="mark yes" aria-hidden="true">✓</span> Do</h4>
              <ul>
                <li>Just ask people walking by. Simple beats clever.</li>
                <li>Throw in a joke or two. Laugh at the AI, never at the player.</li>
                <li>Turn every score into something positive.</li>
                <li>Cheer loudly. Volume is free marketing.</li>
              </ul>
            </div>
            <div>
              <h4><span className="mark no" aria-hidden="true">✕</span> Don’t</h4>
              <ul>
                <li>Never tease anyone about their pronunciation.</li>
                <li>Don’t lecture about AI before they’ve played.</li>
                <li>Don’t hand over the mic without one quick tip (next section).</li>
              </ul>
            </div>
          </div>
        </Chapter>

        <Chapter id="round" title="Running a round">
          <blockquote className="quote">
            “Whisper doesn’t like silence. It doesn’t like hesitation. And it can smell your fear.”
            <cite>Say this before every first round. It’s funny and it’s true.</cite>
          </blockquote>
          <p>
            Two rules decide most scores. The player speaks <strong>the moment SPEAK! appears</strong>, the whole phrase in one go.
            You click <strong>Stop the moment the transcript lands</strong>, before the room adds its own words.
            Play the clean round first, then break it on purpose.
          </p>
          <RoundSimulator id={scenario} onSelect={setScenario} />
        </Chapter>

        <Chapter id="noise" title="Make some noise" lede="A crowd attracts a crowd. Your job is to start one.">
          <p>When someone picks Hard, stop everything and announce it. People drift over to watch, and half of them end up in the queue.</p>
          <HardHype />
        </Chapter>

        <Chapter id="sideways" title="When it goes sideways" lede="Things will break. The booth is fine as long as you’re smiling.">
          <ul className="fixes">
            {FIXES.map((f) => (
              <li key={f.t}>
                <h4>{f.t}</h4>
                <div>
                  <p>{f.d}</p>
                  {f.try && (
                    <div className="try"><button className="btn small" onClick={() => jump(f.try)}>See it happen</button></div>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </Chapter>

        <Chapter id="team" title="Two of you, one booth" lede="Always staff the booth with two people. One keeps the game going, the other has the real conversations.">
          <div className="roles">
            <div className="role-card">
              <h4>The host</h4>
              <p>Runs rounds, works the aisle, keeps the energy up. Owns the Start and Stop buttons.</p>
            </div>
            <div className="role-card tech">
              <h4>The guide</h4>
              <p>The more technical one. When a player asks “wait, where does this run?”, the guide takes them aside.</p>
            </div>
          </div>
          <p>
            The hook is <strong>Sovereign AI</strong>: this runs on our own cluster, nothing goes to the cloud. Mention it, don’t force it.
            If someone bites, the guide walks them through <code>/architecture</code>. If nobody does, that’s fine. They’ll remember the booth.
          </p>
          <div className="note">
            <p><strong>Watch the queue.</strong> A small crowd is gold. A long queue makes people walk away, so keep rounds snappy when it builds up.</p>
          </div>
        </Chapter>

        <Chapter id="prizes" title="Prizes and retries" lede="We want people to come back. Competition is the fun part.">
          <ul>
            <li>A game wins with an <strong>average of 80% or more</strong> across five rounds.</li>
            <li>Hard scores double and Medium scores one and a half times, so brave players climb the leaderboard faster.</li>
            <li>Retries are encouraged. Play as many games as you like. Your best score counts.</li>
          </ul>
          <div className="say">“Nice one, you’re third. Check back in an hour to see if you’re still in the top 3.”</div>
          <p className="muted">The tech owner prepares the award ceremony from live data. You bring the drum roll.</p>
        </Chapter>
        <Contact />
      </Track>
    </>
  )
}
