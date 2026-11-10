// Mirror of the server scoring in src/app_streaming.py
// (normalize_text, levenshtein_similarity, compute_total_score).
// Japanese and Chinese are additionally compared phonetically on the server;
// that step is not reproduced here.

export const normalize = (text) =>
  text.toLowerCase().trim().replace(/[.,!?;:]/g, '').replace(/\s+/g, ' ')

function table(a, b) {
  const d = Array.from({ length: a.length + 1 }, (_, i) => [i])
  for (let j = 1; j <= b.length; j++) d[0][j] = j
  for (let i = 1; i <= a.length; i++) {
    for (let j = 1; j <= b.length; j++) {
      d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1))
    }
  }
  return d
}

export function accuracy(transcript, phrase) {
  const t = normalize(transcript)
  const e = normalize(phrase)
  const longer = Math.max(t.length, e.length)
  if (longer === 0) return 1
  const d = table([...t], [...e])
  return (longer - d[t.length][e.length]) / longer
}

// Per-character marks for the normalized transcript: which characters match the phrase.
// Missing characters (deletions) are returned as markers so the UI can show gaps.
export function diff(transcript, phrase) {
  const a = [...normalize(transcript)]
  const b = [...normalize(phrase)]
  const d = table(a, b)
  const out = []
  let i = a.length
  let j = b.length
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && a[i - 1] === b[j - 1] && d[i][j] === d[i - 1][j - 1]) {
      out.push({ ch: a[i - 1], ok: true }); i--; j--
    } else if (i > 0 && j > 0 && d[i][j] === d[i - 1][j - 1] + 1) {
      out.push({ ch: a[i - 1], ok: false }); i--; j--
    } else if (i > 0 && d[i][j] === d[i - 1][j] + 1) {
      out.push({ ch: a[i - 1], ok: false }); i--
    } else {
      out.push({ ch: '·', ok: false, missing: true }); j--
    }
  }
  return out.reverse()
}

export const MULTIPLIER = { easy: 1.0, medium: 1.5, hard: 2.0 }
export const WIN = 0.8
export const ROMANIZATION_PENALTY = 0.3

export const speedBonus = (seconds) => Math.max(0.8, 1.2 - seconds / 600)

export const totalScore = (difficulty, avgAccuracy, seconds) =>
  Math.round(MULTIPLIER[difficulty] * avgAccuracy * 100 * speedBonus(seconds) * 10) / 10
