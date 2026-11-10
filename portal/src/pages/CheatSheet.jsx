export default function CheatSheet() {
  return (
    <div className="sheet">
      <div className="sheet-head">
        <h1>Whisper booth cheat sheet</h1>
        <button className="btn small no-print" onClick={() => window.print()}>Print this page</button>
      </div>
      <div className="sheet-cols">
        <div className="big-rule">Speak the moment SPEAK! appears. Stop the moment the text lands.</div>
        <section>
          <h2>Every round</h2>
          <ol>
            <li>Player reads the phrase once in their head.</li>
            <li>Click <b>Start Recording</b>. 3 · 2 · 1 is not recorded.</li>
            <li><b>SPEAK!</b> The whole phrase, in one go, no pauses.</li>
            <li>Full sentence on screen? Click <b>Stop</b> straight away.</li>
            <li>Celebrate the score, whatever it is.</li>
          </ol>
        </section>
        <section>
          <h2>Lines that work</h2>
          <ul>
            <li>“Fancy a quick game? There are prizes.”</li>
            <li>“Whisper doesn’t like silence, hesitation… and it can smell your fear.”</li>
            <li>“EVERYBODY STOP, WE ARE ABOUT TO PLAY HARD!”</li>
            <li>“Check back in an hour to see if you’re still top 3.”</li>
            <li>“You managed to break AI. Wow!”</li>
          </ul>
        </section>
        <section>
          <h2>When it goes sideways</h2>
          <ul>
            <li><b>Looping text, Stop does nothing:</b> it ends in 10–12 s. Make it a moment, or start a new game.</li>
            <li><b>Extra words in the transcript:</b> you stopped late, or a friend talked into the mic.</li>
            <li><b>Half a sentence:</b> you stopped early.</li>
            <li><b>Random words at the start:</b> the player hesitated.</li>
            <li><b>Mic dead:</b> swap to the charged transmitter in the case.</li>
          </ul>
        </section>
        <section>
          <h2>House rules</h2>
          <ul>
            <li>Two facilitators at all times: host and guide.</li>
            <li>Never tease pronunciation. Laugh at the AI, not at people.</li>
            <li>Prizes = top 3 on the leaderboard. Hard ×2, Medium ×1.5.</li>
            <li>Retries welcome. Best game counts.</li>
            <li>Business talk? The guide takes it, the game keeps going.</li>
            <li>Queue too long? Shorter chats, snappier rounds.</li>
            <li>Ceremony: podium reveals 3rd → 2nd → 1st, one click each.</li>
          </ul>
        </section>
        <section>
          <h2>Screens</h2>
          <ul>
            <li><b>TV 1:</b> game, mirrored from the Mac.</li>
            <li><b>TV 2:</b> <code>/tv</code> leaderboard, extended, full screen.</li>
            <li><b>Never</b> show <code>/admin</code> on a TV.</li>
          </ul>
        </section>
        <section>
          <h2>Tech owner</h2>
          <ul>
            <li>Name: ____________________</li>
            <li>Phone: ____________________</li>
            <li>Backup cluster URL lives with the tech owner, not on this sheet.</li>
          </ul>
        </section>
      </div>
    </div>
  )
}
