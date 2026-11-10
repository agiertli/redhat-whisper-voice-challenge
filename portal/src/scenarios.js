import { accuracy } from './scoring.js'

// Each scenario is a list of narrated steps and a timeline of frames.
// A frame: { d: ms to hold, set: partial game state, step: narrated step index }.

const PHRASE = 'Red Hat leads in open source innovation'
const pct = (t, p = PHRASE) => Math.round(accuracy(t, p) * 100)

// Stream words into the transcript, ticking the timer as we go.
function stream(words, { from = '', t0 = 0, every = 260, key = 'transcript', step } = {}) {
  const frames = []
  let text = from
  words.forEach((w, i) => {
    text = text ? `${text} ${w}` : w
    frames.push({ d: every, step, set: { [key]: text, timer: t0 + (i + 1) * (every / 1000) } })
  })
  return frames
}

const intro = (step = 0) => [
  { d: 900, step, set: { cursor: 'rest' } },
  { d: 900, step, set: { cursor: 'start' } },
]

const countdown = (step) => [
  { d: 350, step, set: { pressed: 'start', click: 1, status: 'Get ready…' } },
  { d: 650, step, set: { pressed: null, phase: 'countdown', count: 3 } },
  { d: 700, step, set: { count: 2 } },
  { d: 700, step, set: { count: 1 } },
]

const speak = (step) => [
  { d: 650, step, set: { phase: 'speak', vad: 'on', status: 'Recording', cursor: 'rest' } },
]

const stopNow = (step, click = 2) => [
  { d: 750, step, set: { cursor: 'stop', vad: 'on', bubble: null } },
  { d: 450, step, set: { pressed: 'stop', click, phase: 'stopped', vad: 'idle', status: 'Stopped' } },
]

const scored = (step, transcript, extra = '') => {
  const score = pct(`${transcript} ${extra}`)
  return [
    { d: 300, step, set: { pressed: null, cursor: 'off' } },
    { d: 2800, step, set: { score, rounds: ['done', score >= 80 ? 'done' : 'fail'], status: score >= 80 ? 'Challenge passed' : 'Below 80%' } },
  ]
}

const words = PHRASE.split(' ')

export const SCENARIOS = [
  {
    id: 'clean',
    name: 'Clean round',
    good: true,
    title: 'The perfect round',
    blurb: 'This is the rhythm you want every time. Start, countdown, speak straight away, stop the moment the text lands.',
    steps: [
      { label: 'The phrase is on screen. Read it out together once if the player is nervous.' },
      { label: 'You click Start Recording.' },
      { label: '3 · 2 · 1. Nothing is recorded yet.' },
      { label: 'SPEAK! The player says the whole phrase right away, in one go.' },
      { label: 'The transcript lands. Click Stop immediately.' },
      { label: 'Score shows. Celebrate it out loud.' },
    ],
    frames: [
      ...intro(0),
      ...countdown(1),
      ...speak(3),
      { d: 200, step: 3, set: { phase: 'listening', vad: 'speaking', bubble: { who: 'player', text: PHRASE } } },
      ...stream(words, { step: 3 }),
      ...stopNow(4),
      ...scored(5, PHRASE),
    ],
  },
  {
    id: 'hesitate',
    name: 'Player hesitates',
    title: 'Whisper can smell your fear',
    blurb: 'A pause after SPEAK! is silence on the recording, and Whisper fills silence with words nobody said. Coach the player to start talking the moment the countdown ends.',
    steps: [
      { label: 'You click Start Recording.' },
      { label: '3 · 2 · 1.' },
      { label: 'SPEAK! …but the player freezes for two seconds.', alert: true },
      { label: 'Whisper invents words to fill the silence.', alert: true },
      { label: 'The player finally speaks, slowly, with gaps.' },
      { label: 'You stop on time, but the damage is done.' },
    ],
    frames: [
      ...intro(0),
      ...countdown(1).map((f, i) => ({ ...f, step: i === 0 ? 0 : 1 })),
      ...speak(2),
      { d: 1300, step: 2, set: { phase: 'listening', vad: 'on', bubble: { who: 'player', text: 'Ehm… where do I start?' } } },
      { d: 900, step: 3, set: { timer: 2, bubble: null } },
      { d: 900, step: 3, set: { transcript: 'Thank you.', timer: 3 } },
      { d: 200, step: 4, set: { vad: 'speaking', bubble: { who: 'player', text: 'Red Hat… leads in… open source… innovation' } } },
      ...stream(['Uh,', 'Red', 'Hat', 'leads', 'in', 'open', 'source', 'in', 'nova', 'tion'], { from: 'Thank you.', t0: 3, every: 420, step: 4 }),
      ...stopNow(5),
      ...scored(5, 'Thank you. Uh, Red Hat leads in open source in nova tion'),
    ],
  },
  {
    id: 'late',
    name: 'Stop too late',
    title: 'Stop clicked too late',
    blurb: 'The player nailed it, but the mic is still open. A friend leaning in to comment gets transcribed too, and the score drops.',
    steps: [
      { label: 'Start, countdown, the player speaks perfectly.' },
      { label: 'The transcript lands. Nobody clicks Stop.', alert: true },
      { label: 'A colleague leans in to the mic: "Ha ha, nice one!"', alert: true },
      { label: 'Stop finally gets clicked. The extra words count against the player.' },
    ],
    frames: [
      ...intro(0),
      ...countdown(0),
      ...speak(0),
      { d: 200, step: 0, set: { phase: 'listening', vad: 'speaking', bubble: { who: 'player', text: PHRASE } } },
      ...stream(words, { step: 0 }),
      { d: 1300, step: 1, set: { vad: 'on', bubble: null, timer: 3 } },
      { d: 300, step: 2, set: { vad: 'speaking', bubble: { who: 'other', text: 'Ha ha, nice one!' }, extraKind: 'noise' } },
      ...stream(['Ha', 'ha,', 'nice', 'one!'], { key: 'extra', t0: 3, every: 320, step: 2 }),
      ...stopNow(3),
      ...scored(3, PHRASE, 'Ha ha, nice one!'),
    ],
  },
  {
    id: 'early',
    name: 'Stop too early',
    title: 'Stop clicked too early',
    blurb: 'Clicking Stop while the text is still arriving cuts the phrase off. Wait until the full sentence is on screen, then click straight away.',
    steps: [
      { label: 'Start, countdown, the player speaks.' },
      { label: 'Half the sentence is on screen, and you click Stop.', alert: true },
      { label: 'The rest of the phrase is lost.' },
    ],
    frames: [
      ...intro(0),
      ...countdown(0),
      ...speak(0),
      { d: 200, step: 0, set: { phase: 'listening', vad: 'speaking', bubble: { who: 'player', text: PHRASE } } },
      ...stream(words.slice(0, 4), { step: 0 }),
      { d: 450, step: 1, set: { cursor: 'stop' } },
      { d: 450, step: 1, set: { pressed: 'stop', click: 2, phase: 'stopped', vad: 'idle', status: 'Stopped', bubble: null } },
      ...scored(2, words.slice(0, 4).join(' ')),
    ],
  },
  {
    id: 'break',
    name: 'Whisper breaks',
    title: 'You managed to break the AI',
    blurb: 'When not a single word is recognized in the target language, Whisper can loop on one phrase for 10–12 seconds, and Stop cannot interrupt it. It happens roughly 5 times in 100. Turn it into the best moment of the day.',
    steps: [
      { label: 'Hard mode, Japanese. The player gives it a brave try.' },
      { label: 'Not one word is recognized. Whisper starts looping.', alert: true },
      { label: 'Stop does nothing while it streams.', alert: true },
      { label: 'Make it a moment: "You managed to break AI. Wow!"' },
      { label: 'After about 10–12 s it ends. Laugh, then start a new game if needed.' },
    ],
    base: {
      flag: '🇯🇵', lang: 'Japanese', phrase: 'OpenShiftは素晴らしい製品です', round: 3, rounds: ['done', 'done'],
    },
    frames: [
      ...intro(0),
      ...countdown(0),
      ...speak(0),
      { d: 1500, step: 0, set: { phase: 'listening', vad: 'speaking', bubble: { who: 'player', text: 'Open… shifto… wa… subara… something?' } } },
      { d: 400, step: 1, set: { bubble: null, vad: 'on', extraKind: 'loop', extra: 'ご視聴ありがとうございました。', timer: 2 } },
      ...Array.from({ length: 5 }, (_, i) => ({ d: 380, step: 1, set: { extra: 'ご視聴ありがとうございました。'.repeat(i + 2), timer: 3 + i } })),
      { d: 600, step: 2, set: { cursor: 'stop' } },
      { d: 300, step: 2, set: { pressed: 'stop', click: 2 } },
      { d: 500, step: 2, set: { pressed: null, extra: 'ご視聴ありがとうございました。'.repeat(8), timer: 8 } },
      { d: 2200, step: 3, set: { cursor: 'off', bubble: { who: 'host', text: 'YOU MANAGED TO BREAK AI! WOW!' }, extra: 'ご視聴ありがとうございました。'.repeat(11), timer: 10 } },
      { d: 600, step: 4, set: { phase: 'stopped', vad: 'idle', status: 'Stopped', timer: 12 } },
      { d: 3000, step: 4, set: { score: 0, rounds: ['done', 'done', 'fail'], status: 'Below 80%' } },
    ],
  },
]
