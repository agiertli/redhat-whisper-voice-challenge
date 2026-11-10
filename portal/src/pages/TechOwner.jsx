import { Chapter, Track } from '../components/Track.jsx'
import BoothDiagram from '../components/BoothDiagram.jsx'
import EndpointTour from '../components/EndpointTour.jsx'
import Customize from '../components/Customize.jsx'
import ScoringPlayground from '../components/ScoringPlayground.jsx'
import { doc, REPO } from '../links.js'
import { href } from '../router.js'

const SECTIONS = [
  { id: 'plate', title: 'What’s on your plate' },
  { id: 'install', title: 'Installing' },
  { id: 'kit', title: 'Booth kit' },
  { id: 'endpoints', title: 'The four URLs' },
  { id: 'customize', title: 'Make it local' },
  { id: 'scoring', title: 'How scoring works' },
  { id: 'planb', title: 'Backups and plan B' },
  { id: 'show-up', title: 'Show up' },
]

export default function TechOwner({ section }) {
  return (
    <>
      <header className="track-head">
        <div className="wrap">
          <p className="who">For tech owners</p>
          <h1>Make it work, then make it yours.</h1>
          <p className="lede">An agent does the install. Your job is the decisions: which languages, which phrases, where the TVs go and what happens if a cluster dies.</p>
        </div>
      </header>

      <Track page="tech" sections={SECTIONS} section={section}>
        <Chapter id="plate" title="What’s on your plate">
          <ul className="owns">
            <li><b>A primary cluster</b><span>Where the booth plays. One RHDP order.</span></li>
            <li><b>A backup cluster</b><span>Same config, ready to take over. Keep it in sync.</span></li>
            <li><b>Backups, every few minutes</b><span>One script on a laptop, running all day.</span></li>
            <li><b>Language pools</b><span>What Easy, Medium and Hard mean for this crowd.</span></li>
            <li><b>Challenge phrases</b><span>Default tech phrases, or whatever marketing is pushing.</span></li>
            <li><b>The booth kit</b><span>Mac, two TVs, mic. Tested before doors open.</span></li>
            <li><b>The award ceremony</b><span>Generated from live data in one command.</span></li>
            <li><b>Being there</b><span>Facilitators will need you. More on that below.</span></li>
          </ul>
        </Chapter>

        <Chapter id="install" title="Installing: let the agent drive" lede="One thing to order, a few questions to answer, and the agent handles the rest.">
          <div className="note red">
            <p><strong>The only technical prerequisite:</strong> order the <strong>OpenShift AI 3</strong> item from the Red Hat Demo Platform (RHDP). It comes with a single-node cluster and an NVIDIA GPU, which is everything Whisper needs. Order two: one primary, one backup.</p>
          </div>
          <ol className="steps">
            <li><b>Log in with <code>oc</code></b> to the new cluster, using the credentials from the RHDP email.</li>
            <li><b>Clone the repo, open Claude Code or Codex in it and call the skill by name.</b> Don’t just say “install Whisper” and hope. Start with the skill, so the agent follows the runbook instead of improvising:
              <pre className="cmd"><span className="c"># Claude Code</span>{'\n'}/whisper-operations Install Whisper on this cluster{'\n'}{'\n'}<span className="c"># Codex</span>{'\n'}$whisper-operations Install Whisper on this cluster</pre>
              No skill in the list? Restart the agent session inside the repo folder.</li>
            <li><b>Answer its questions.</b> First challenge language (always your call), registration mode, the admin password, and whether it may stop the RHDP demo Llama to free the GPU.</li>
            <li><b>Let it verify.</b> It checks the model, the routes, monitoring and a test transcription, then hands you the URLs.</li>
            <li><b>Repeat on the backup cluster</b> with the same values file.</li>
          </ol>
          <div className="note">
            <p><strong>One skill for everything after the install too.</strong> Language changes, phrases, upgrades, backups and readiness checks all go through <code>/whisper-operations</code>. For example: <code>/whisper-operations Check booth readiness; report gaps without changing the deployment</code></p>
          </div>
          <p className="muted">Prefer doing it by hand? There’s a direct Helm path. It uses the same chart and gives the same result.</p>
          <div className="docs-links">
            <a className="btn small" href={doc('docs/INSTALLATION.md')}>Installation runbook</a>
            <a className="btn small" href={doc('docs/AGENT-INSTALLATION.md')}>Agent procedure</a>
            <a className="btn small" href={doc('docs/HELM-INSTALLATION.md')}>Helm by hand</a>
          </div>
        </Chapter>

        <Chapter id="kit" title="Booth kit" lede="Small kit, big impact. Click around.">
          <BoothDiagram />
        </Chapter>

        <Chapter id="endpoints" title="The four URLs" lede="One app, four faces. Know which one goes where.">
          <EndpointTour />
        </Chapter>

        <Chapter id="customize" title="Make it local" lede="The same game should feel different in Prague and Munich. Three settings do most of the work.">
          <Customize />
          <div className="docs-links" style={{ marginTop: 22 }}>
            <a className="btn small" href={doc('docs/customization/difficulty-groups.md')}>Difficulty groups</a>
            <a className="btn small" href={doc('docs/customization/languages-and-phrases.md')}>Languages and phrases</a>
            <a className="btn small" href={doc('docs/customization/registration.md')}>Registration</a>
            <a className="btn small" href={doc('docs/customization/game-mode.md')}>Tournament or anonymous</a>
          </div>
        </Chapter>

        <Chapter id="scoring" title="How scoring works" lede="Players will ask why they got 78%. Have a go yourself first.">
          <ScoringPlayground />
          <div className="docs-links" style={{ marginTop: 18 }}>
            <a className="btn small" href={doc('docs/customization/tournament-scoring.md')}>Full scoring rules</a>
          </div>
        </Chapter>

        <Chapter id="planb" title="Backups and plan B" lede="Conference Wi-Fi, borrowed GPUs, a two-day event. Assume something will fail.">
          <p>Run the backup script on a laptop (not the booth Mac) and leave it running. It pulls a validated snapshot every five minutes.</p>
          <pre className="cmd"><span className="c"># no oc, no cluster credentials, just curl</span>{'\n'}WHISPER_URL=https://whisper.apps.your-cluster \{'\n'}ADMIN_TOKEN_FILE=./admin-token \{'\n'}./scripts/backup.sh --loop</pre>
          <ul>
            <li><strong>Restore through the admin upload</strong>, never by copying the database into a pod. That route corrupts it.</li>
            <li><strong>Switch to the backup cluster</strong> by restoring the latest snapshot there and pointing the booth Mac at its URL.</li>
            <li><strong>Try the switch once before the event.</strong> A plan B nobody has tested is just a hope.</li>
          </ul>
          <div className="docs-links">
            <a className="btn small" href={doc('docs/customization/backups-and-restore.md')}>Backups and restore</a>
            <a className="btn small" href={doc('docs/customization/award-ceremony.md')}>Award ceremony</a>
          </div>
        </Chapter>

        <Chapter id="show-up" title="Show up" lede="The cluster isn’t the hard part. The booth is.">
          <p>On the morning of each day, run <code>/whisper-operations</code> with “Check booth readiness” before doors open. Then be at the booth for the first hour and the busy slots. Check the mic, watch a few rounds, and make sure the facilitators know who to call. When things go wrong, nobody in the aisle cares whose fault it was. Help out.</p>
          <p>Send your facilitators the <a href={href('facilitator')}>facilitator guide</a> before the event and print the <a href={href('cheatsheet')}>cheat sheet</a> for the booth.</p>
          <p className="muted small">Everything else lives in the <a href={REPO}>repository</a>.</p>
        </Chapter>
      </Track>
    </>
  )
}
