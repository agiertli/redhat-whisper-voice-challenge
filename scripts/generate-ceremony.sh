#!/usr/bin/env bash
# Generate an animated HTML ceremony presentation from live tournament data.
# Usage: ./scripts/generate-ceremony.sh --event "Conference Name" --dates "Oct 13–14, 2026"
#        [--namespace whisper] [--output ceremony.html] [--winners 3] [--runners 4]
#        [--blooper ATTEMPT_ID] [--blooper-credit]   # blooper flags are set by the agent
#        ./scripts/generate-ceremony.sh --list-bloopers [N]   # "Whisper Fail of the Day" candidates
# Requires: oc logged into the cluster, Python 3 (standard library only).
set -Eeuo pipefail

NS=whisper
OUTPUT=ceremony.html
EVENT_NAME=""
EVENT_DATES=""
NUM_WINNERS=3
NUM_RUNNERS=4
BLOOPER_ID=""
BLOOPER_CREDIT=false
BLOOPER_NOTE=""
DECK_LANG=""
LIST_BLOOPERS=""

usage() {
    cat <<'USAGE'
Usage: ./scripts/generate-ceremony.sh [options]
  --event NAME       Event/conference name (required)
  --dates DATES      Event dates string, e.g. "October 13–14, 2026" (required)
  --namespace NS     Kubernetes namespace (default: whisper)
  --output FILE      Output HTML file (default: ceremony.html)
  --winners N        Number of podium winners (default: 3)
  --runners N        Honourable mentions under the podium (default: 4)
  --lang CODE        Deck language: cs, sk or en (default: the deployment's
                     required challenge language; others fall back to en)
  --list-bloopers [N] Print up to N (default 25) "Whisper fail" candidates
                     (expected phrase vs. what Whisper heard) and exit
  --blooper ID       Add a "Whisper Fail of the Day" slide for attempt ID
                     (pick the ID from --list-bloopers)
  --blooper-credit   Show the player's nickname on the fail slide
                     (default: anonymous)
  --blooper-note TEXT One short line under the fail (e.g. a translation or
                     why it is funny)
  -h, --help         Show this help
USAGE
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --event)     EVENT_NAME="$2"; shift 2 ;;
        --dates)     EVENT_DATES="$2"; shift 2 ;;
        --namespace) NS="$2"; shift 2 ;;
        --output)    OUTPUT="$2"; shift 2 ;;
        --winners)   NUM_WINNERS="$2"; shift 2 ;;
        --runners)   NUM_RUNNERS="$2"; shift 2 ;;
        --blooper)   BLOOPER_ID="$2"; shift 2 ;;
        --blooper-credit) BLOOPER_CREDIT=true; shift ;;
        --blooper-note) BLOOPER_NOTE="$2"; shift 2 ;;
        --lang)      DECK_LANG="$2"; shift 2 ;;
        --list-bloopers)
            if [[ "${2:-}" =~ ^[0-9]+$ ]]; then LIST_BLOOPERS="$2"; shift 2
            else LIST_BLOOPERS=25; shift; fi ;;
        -h|--help)   usage ;;
        *)           echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

if [[ -n "$BLOOPER_ID" && ! "$BLOOPER_ID" =~ ^[0-9]+$ ]]; then
    echo "ERROR: --blooper must be a numeric attempt ID (see --list-bloopers)." >&2
    exit 1
fi

if [[ -n "$LIST_BLOOPERS" ]]; then
    echo "Fetching Whisper fail candidates from namespace $NS..." >&2
    # Partly-right misheard sentences are the funny ones. Similarity is
    # recomputed here (letters/digits only) because stored accuracy can include
    # the romanization penalty, which would list correct answers as fails.
    oc exec deployment/whisper-ui -n "$NS" -- python3 -c "
import sqlite3, difflib
db = sqlite3.connect('/app/data/tournament.db')
rows = db.execute('''
    SELECT a.id, a.language, a.phrase, a.transcription, p.nickname
    FROM attempts a
    JOIN games g ON g.id = a.game_id
    JOIN players p ON p.id = g.player_id
    WHERE a.status != 'skip' AND a.transcription IS NOT NULL
      AND length(trim(a.transcription)) >= 8
    ORDER BY a.id
''').fetchall()
db.close()
norm = lambda s: ''.join(ch for ch in s.lower() if ch.isalnum())
seen, out = set(), []
for aid, lang, phrase, heard, nick in rows:
    key = norm(heard)
    if key in seen:
        continue
    seen.add(key)
    sim = difflib.SequenceMatcher(None, norm(phrase), key).ratio()
    if 0.15 <= sim < 0.95:
        out.append((sim, aid, lang, phrase, heard, nick))
out.sort()
if not out:
    print('No candidates yet.')
for sim, aid, lang, phrase, heard, nick in out[:$LIST_BLOOPERS]:
    script = 'latin' if all(ord(c) < 0x250 for c in norm(phrase)) else 'non-latin'
    print(f'#{aid}  [{lang}, {script}]  similarity {round(sim * 100)}%  player={nick}')
    print(f'    expected: {phrase}')
    print(f'    heard:    {heard}')
"
    exit 0
fi

if [[ -z "$EVENT_NAME" || -z "$EVENT_DATES" ]]; then
    echo "ERROR: --event and --dates are required." >&2
    usage
fi

echo "Fetching tournament data from namespace $NS..."

STATS_JSON=$(oc exec deployment/whisper-ui -n "$NS" -- python3 -c "
import sqlite3, json

db = sqlite3.connect('/app/data/tournament.db')
db.row_factory = sqlite3.Row

total_players = db.execute('SELECT COUNT(DISTINCT player_id) FROM games WHERE completed_at IS NOT NULL').fetchone()[0]
total_games = db.execute('SELECT COUNT(*) FROM games WHERE completed_at IS NOT NULL').fetchone()[0]
total_attempts = db.execute('SELECT COUNT(*) FROM attempts WHERE status != \"skip\"').fetchone()[0]
perfect_scores = db.execute('SELECT COUNT(*) FROM attempts WHERE accuracy >= 0.99').fetchone()[0]
unique_langs = db.execute('SELECT COUNT(DISTINCT language) FROM attempts').fetchone()[0]
returning = db.execute('''
    SELECT COUNT(*) FROM (
        SELECT player_id FROM games WHERE completed_at IS NOT NULL
        GROUP BY player_id HAVING COUNT(*) > 1
    )
''').fetchone()[0]

lang_stats = db.execute('''
    SELECT language, COUNT(*) as attempts,
           ROUND(AVG(CASE WHEN status != 'skip' THEN accuracy END)*100,1) as avg_acc
    FROM attempts WHERE status != 'skip'
    GROUP BY language ORDER BY avg_acc DESC
''').fetchall()

most_attempted = db.execute('''
    SELECT language, COUNT(*) as cnt
    FROM attempts WHERE status != 'skip'
    GROUP BY language ORDER BY cnt DESC LIMIT 1
''').fetchone()

top_players = db.execute('''
    SELECT p.nickname, MAX(g.total_score) as best, g.difficulty
    FROM games g JOIN players p ON p.id = g.player_id
    WHERE g.completed_at IS NOT NULL AND g.total_score IS NOT NULL
    GROUP BY g.player_id ORDER BY best DESC LIMIT 10
''').fetchall()

blooper = None
if '$BLOOPER_ID':
    r = db.execute('''
        SELECT a.language, a.phrase, a.transcription, a.accuracy, p.nickname
        FROM attempts a
        JOIN games g ON g.id = a.game_id
        JOIN players p ON p.id = g.player_id
        WHERE a.id = ?
    ''', (int('$BLOOPER_ID'),)).fetchone()
    if r is None:
        raise SystemExit('Attempt $BLOOPER_ID not found')
    blooper = {'lang': r[0], 'phrase': r[1], 'heard': r[2] or '',
               'accuracy': round((r[3] or 0) * 100), 'nickname': r[4]}

import os
result = {
    'required_language': os.environ.get('REQUIRED_CHALLENGE_LANGUAGE', ''),
    'blooper': blooper,
    'total_players': total_players,
    'total_games': total_games,
    'total_attempts': total_attempts,
    'perfect_scores': perfect_scores,
    'unique_langs': unique_langs,
    'returning': returning,
    'lang_stats': [{'lang': r[0], 'attempts': r[1], 'avg_acc': r[2]} for r in lang_stats],
    'most_attempted': {'lang': most_attempted[0], 'count': most_attempted[1]} if most_attempted else None,
    'top_players': [{'nickname': r[0], 'score': round(r[1],1), 'difficulty': r[2]} for r in top_players]
}
db.close()
print(json.dumps(result))
")

echo "Generating ceremony presentation..."

# Render with scripts/ceremony/render.py. Data goes via environment variables:
# transcriptions and names may contain quotes.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATS_JSON="$STATS_JSON" EVENT_NAME="$EVENT_NAME" EVENT_DATES="$EVENT_DATES" \
OUTPUT_FILE="$OUTPUT" NUM_WINNERS="$NUM_WINNERS" NUM_RUNNERS="$NUM_RUNNERS" \
BLOOPER_CREDIT="$BLOOPER_CREDIT" BLOOPER_NOTE="$BLOOPER_NOTE" DECK_LANG="$DECK_LANG" \
    python3 "$SCRIPT_DIR/ceremony/render.py"

echo "Done: $OUTPUT"
