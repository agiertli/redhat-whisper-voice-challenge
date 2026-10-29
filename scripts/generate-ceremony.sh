#!/usr/bin/env bash
# Generate an animated HTML ceremony presentation from live tournament data.
# Usage: ./scripts/generate-ceremony.sh --event "Conference Name" --dates "Oct 13–14, 2026"
#        [--namespace whisper] [--output ceremony.html] [--winners 3] [--runners 4]
# Requires: oc logged into the cluster, Python 3 (standard library only).
set -Eeuo pipefail

NS=whisper
OUTPUT=ceremony.html
EVENT_NAME=""
EVENT_DATES=""
NUM_WINNERS=3
NUM_RUNNERS=4

usage() {
    cat <<'USAGE'
Usage: ./scripts/generate-ceremony.sh [options]
  --event NAME       Event/conference name (required)
  --dates DATES      Event dates string, e.g. "October 13–14, 2026" (required)
  --namespace NS     Kubernetes namespace (default: whisper)
  --output FILE      Output HTML file (default: ceremony.html)
  --winners N        Number of podium winners (default: 3)
  --runners N        Number of runner-up rows (default: 4)
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
        -h|--help)   usage ;;
        *)           echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

if [[ -z "$EVENT_NAME" || -z "$EVENT_DATES" ]]; then
    echo "ERROR: --event and --dates are required." >&2
    usage
fi

echo "Fetching tournament data from namespace $NS..."

STATS_JSON=$(oc exec deployment/whisper-ui -n "$NS" -- python3 -c "
import sqlite3, json

db = sqlite3.connect('/app/data/tournament.db')
db.row_factory = sqlite3.Row

total_players = db.execute('SELECT COUNT(*) FROM players').fetchone()[0]
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

result = {
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

python3 -c "
import json, sys, html as html_mod

data = json.loads('''$STATS_JSON''')
event_name = '''$EVENT_NAME'''
event_dates = '''$EVENT_DATES'''
num_winners = $NUM_WINNERS
num_runners = $NUM_RUNNERS
output_file = '''$OUTPUT'''

LANG_NAMES = {
    'sk':'Slovak','cs':'Czech','en':'English','pl':'Polish','hu':'Hungarian',
    'de':'German','es':'Spanish','fi':'Finnish','fr':'French','hr':'Croatian',
    'is':'Icelandic','no':'Norwegian','sr':'Serbian','tr':'Turkish','it':'Italian',
    'pt':'Portuguese','nl':'Dutch','sv':'Swedish','ro':'Romanian','uk':'Ukrainian',
    'ja':'Japanese','ko':'Korean','ar':'Arabic','zh':'Chinese','th':'Thai','hi':'Hindi',
    'sl':'Slovenian','bg':'Bulgarian','bs':'Bosnian','da':'Danish','el':'Greek',
    'he':'Hebrew','id':'Indonesian','ms':'Malay','ru':'Russian','vi':'Vietnamese',
    'fa':'Persian','ta':'Tamil','te':'Telugu','bn':'Bengali','ur':'Urdu',
    'ka':'Georgian','hy':'Armenian','sw':'Swahili','af':'Afrikaans','ca':'Catalan',
    'eu':'Basque','gl':'Galician','cy':'Welsh','ga':'Irish','mt':'Maltese',
    'et':'Estonian','lv':'Latvian','lt':'Lithuanian',
}
LANG_FLAGS = {
    'sk':'\U0001f1f8\U0001f1f0','cs':'\U0001f1e8\U0001f1ff','en':'\U0001f1ec\U0001f1e7',
    'pl':'\U0001f1f5\U0001f1f1','hu':'\U0001f1ed\U0001f1fa','de':'\U0001f1e9\U0001f1ea',
    'es':'\U0001f1ea\U0001f1f8','fi':'\U0001f1eb\U0001f1ee','fr':'\U0001f1eb\U0001f1f7',
    'hr':'\U0001f1ed\U0001f1f7','is':'\U0001f1ee\U0001f1f8','no':'\U0001f1f3\U0001f1f4',
    'sr':'\U0001f1f7\U0001f1f8','tr':'\U0001f1f9\U0001f1f7','it':'\U0001f1ee\U0001f1f9',
    'pt':'\U0001f1f5\U0001f1f9','nl':'\U0001f1f3\U0001f1f1','sv':'\U0001f1f8\U0001f1ea',
    'ro':'\U0001f1f7\U0001f1f4','uk':'\U0001f1fa\U0001f1e6','ja':'\U0001f1ef\U0001f1f5',
    'ko':'\U0001f1f0\U0001f1f7','ar':'\U0001f1f8\U0001f1e6','zh':'\U0001f1e8\U0001f1f3',
    'th':'\U0001f1f9\U0001f1ed','hi':'\U0001f1ee\U0001f1f3','sl':'\U0001f1f8\U0001f1ee',
    'bg':'\U0001f1e7\U0001f1ec','bs':'\U0001f1e7\U0001f1e6','da':'\U0001f1e9\U0001f1f0',
    'el':'\U0001f1ec\U0001f1f7','he':'\U0001f1ee\U0001f1f1','id':'\U0001f1ee\U0001f1e9',
    'ms':'\U0001f1f2\U0001f1fe','ru':'\U0001f1f7\U0001f1fa','vi':'\U0001f1fb\U0001f1f3',
    'fa':'\U0001f1ee\U0001f1f7','ta':'\U0001f1ee\U0001f1f3','te':'\U0001f1ee\U0001f1f3',
    'bn':'\U0001f1e7\U0001f1e9','ur':'\U0001f1f5\U0001f1f0','ka':'\U0001f1ec\U0001f1ea',
    'hy':'\U0001f1e6\U0001f1f2','sw':'\U0001f1f0\U0001f1ea','af':'\U0001f1ff\U0001f1e6',
    'ca':'\U0001f1ea\U0001f1f8','eu':'\U0001f1ea\U0001f1f8','gl':'\U0001f1ea\U0001f1f8',
    'cy':'\U0001f3f4\U000e0067\U000e0062\U000e0077\U000e006c\U000e0073\U000e007f',
    'ga':'\U0001f1ee\U0001f1ea','mt':'\U0001f1f2\U0001f1f9','et':'\U0001f1ea\U0001f1ea',
    'lv':'\U0001f1f1\U0001f1fb','lt':'\U0001f1f1\U0001f1f9',
}

langs = data['lang_stats']
easiest = langs[:3]
hardest = list(reversed(langs[-3:]))
top = data['top_players']
winners = top[:num_winners]
runners = top[num_winners:num_winners + num_runners]

def flag(code):
    return LANG_FLAGS.get(code, '')

def name(code):
    return LANG_NAMES.get(code, code.upper())

def esc(s):
    return html_mod.escape(str(s))

# Build easiest/hardest language cards
def lang_card(lang, delay, acc_class):
    return f'''<div class=\"s2-lang-card\" data-delay=\"{delay}\">
                <div class=\"s2-flag\">{flag(lang['lang'])}</div>
                <div class=\"s2-lang-info\">
                    <div class=\"s2-lang-name\">{esc(name(lang['lang']))}</div>
                    <div class=\"s2-lang-detail\">{lang['attempts']} attempts</div>
                </div>
                <div class=\"s2-lang-acc {acc_class}\">{lang['avg_acc']}%</div>
            </div>'''

easy_cards = '\\n'.join(lang_card(l, 200 + i*200, 'green') for i, l in enumerate(easiest))
hard_cards = '\\n'.join(lang_card(l, 800 + i*200, 'red') for i, l in enumerate(hardest))

# Fun facts
most = data.get('most_attempted')
most_lang_name = name(most['lang']) if most else '?'
most_lang_flag = flag(most['lang']) if most else ''
most_lang_count = most['count'] if most else 0
best_acc = langs[0]['avg_acc'] if langs else 0
best_acc_lang = name(langs[0]['lang']) if langs else '?'
worst_acc = langs[-1]['avg_acc'] if langs else 0
worst_acc_lang = name(langs[-1]['lang']) if langs else '?'
pct_perfect = round(data['perfect_scores'] / max(data['total_attempts'], 1) * 100, 1)

# Podium
MEDAL_HTML = ['&#129351;', '&#129352;', '&#129353;']
PLACE_CLASS = ['gold', 'silver', 'bronze']
BAR_COLORS = {'gold': '#ffd700', 'silver': '#c0c0c0', 'bronze': '#cd7f32'}
BAR_HEIGHTS = [160, 120, 90]
# Podium order: 2nd, 1st, 3rd (visual layout)
podium_order = [1, 0, 2] if len(winners) >= 3 else list(range(len(winners)))

podium_html = ''
reveal_ids = []
for visual_idx, rank_idx in enumerate(podium_order):
    if rank_idx >= len(winners):
        continue
    w = winners[rank_idx]
    cls = PLACE_CLASS[rank_idx]
    wid = f'winner{rank_idx + 1}'
    reveal_ids.append(wid)
    podium_html += f'''<div class=\"podium-place {cls}\" id=\"{wid}\">
            <div class=\"podium-medal\">{MEDAL_HTML[rank_idx]}</div>
            <div class=\"podium-name\">{esc(w['nickname'])}</div>
            <div class=\"podium-score\">{w['score']} pts</div>
            <div class=\"podium-diff\">{esc(w['difficulty'])}</div>
            <div class=\"podium-bar\"></div>
        </div>'''

# Reverse reveal order: 3rd, 2nd, 1st
reveal_order_js = json.dumps(list(reversed(reveal_ids)))

# Runner-up rows
runner_html = ''
for i, r in enumerate(runners):
    runner_html += f'''<div class=\"runner-row\" data-delay=\"{200 + i * 200}\">
            <span class=\"runner-rank\">#{num_winners + i + 1}</span>
            <span class=\"runner-name\">{esc(r['nickname'])}</span>
            <span class=\"runner-score\">{r['score']} pts</span>
            <span class=\"runner-diff\">{esc(r['difficulty'])}</span>
        </div>'''

num_slides = 6 if runners else 5
dots = '\\n'.join(f'<div class=\"dot{\" active\" if i == 0 else \"\"}\" onclick=\"goTo({i})\"></div>' for i in range(num_slides))

# Slide 6: runner-up (only if runners exist)
runner_slide = ''
if runners:
    runner_slide = f'''
<!-- SLIDE 6: Runner-Up -->
<div class=\"slide\" id=\"slide6\">
    <div class=\"red-bar\"></div>
    <div class=\"s6-heading\">Runner-Up</div>
    <div class=\"runner-list\">
        {runner_html}
    </div>
</div>'''

HTML = f'''<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>Whisper Voice Challenge — Results</title>
    <link href=\"https://fonts.googleapis.com/css2?family=Red+Hat+Display:wght@400;500;700;900&family=Red+Hat+Text:wght@400;500;700&family=Red+Hat+Mono:wght@400;700&display=swap\" rel=\"stylesheet\">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        html, body {{ width: 100%; height: 100%; overflow: hidden; }}
        body {{ font-family: 'Red Hat Text', sans-serif; background: #151515; color: #fff; }}

        .slide {{
            position: absolute; inset: 0;
            display: flex; flex-direction: column; align-items: center; justify-content: center;
            padding: 60px 80px;
            opacity: 0; transform: translateX(60px);
            transition: opacity 0.5s ease, transform 0.5s ease;
            pointer-events: none;
        }}
        .slide.active {{ opacity: 1; transform: translateX(0); pointer-events: all; }}
        .slide.exit-left {{ opacity: 0; transform: translateX(-60px); }}

        .nav-dots {{
            position: fixed; bottom: 32px; left: 50%; transform: translateX(-50%);
            display: flex; gap: 12px; z-index: 100;
        }}
        .dot {{
            width: 12px; height: 12px; border-radius: 50%;
            background: #383838; cursor: pointer; transition: all 0.3s;
        }}
        .dot.active {{ background: #ee0000; transform: scale(1.3); }}
        .nav-hint {{
            position: fixed; bottom: 60px; left: 50%; transform: translateX(-50%);
            font-size: 0.75rem; color: #4a4a4a; letter-spacing: 1px; text-transform: uppercase;
        }}

        .red-bar {{ width: 80px; height: 4px; background: #ee0000; border-radius: 2px; margin-bottom: 24px; }}

        /* Slide 1: Title + Numbers */
        .s1-title {{ font-family: 'Red Hat Display', sans-serif; font-weight: 900; font-size: 3.5rem; color: #ee0000; text-align: center; line-height: 1.1; }}
        .s1-subtitle {{ font-size: 1.2rem; color: #a3a3a3; margin-top: 8px; margin-bottom: 48px; text-align: center; }}
        .s1-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 24px; width: 100%; max-width: 900px; }}
        .s1-card {{ background: #1f1f1f; border: 1px solid #292929; border-radius: 16px; padding: 32px 16px; text-align: center; opacity: 0; transform: translateY(30px); }}
        .s1-card.animate {{ animation: cardIn 0.6s ease forwards; }}
        .s1-num {{ font-family: 'Red Hat Mono', monospace; font-weight: 700; font-size: 3.2rem; color: #ee0000; line-height: 1; }}
        .s1-label {{ font-size: 0.85rem; color: #a3a3a3; margin-top: 10px; text-transform: uppercase; letter-spacing: 1px; font-weight: 500; }}

        /* Slide 2: Language Battle */
        .s2-heading {{ font-family: 'Red Hat Display', sans-serif; font-weight: 900; font-size: 2.2rem; text-align: center; margin-bottom: 40px; }}
        .s2-columns {{ display: grid; grid-template-columns: 1fr 80px 1fr; gap: 0; width: 100%; max-width: 900px; align-items: start; }}
        .s2-col {{ display: flex; flex-direction: column; gap: 12px; }}
        .s2-col-title {{ font-family: 'Red Hat Display', sans-serif; font-weight: 900; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 8px; text-align: center; }}
        .s2-col-title.green {{ color: #63993d; }}
        .s2-col-title.red {{ color: #ee0000; }}
        .s2-lang-card {{ background: #1f1f1f; border: 1px solid #292929; border-radius: 12px; padding: 18px 20px; display: flex; align-items: center; gap: 14px; opacity: 0; transform: scale(0.9); }}
        .s2-lang-card.animate {{ animation: popIn 0.4s ease forwards; }}
        .s2-flag {{ font-size: 2rem; }}
        .s2-lang-info {{ flex: 1; }}
        .s2-lang-name {{ font-weight: 700; font-size: 1.05rem; }}
        .s2-lang-detail {{ font-size: 0.78rem; color: #6a6e73; margin-top: 2px; }}
        .s2-lang-acc {{ font-family: 'Red Hat Mono', monospace; font-weight: 700; font-size: 1.4rem; }}
        .s2-lang-acc.green {{ color: #63993d; }}
        .s2-lang-acc.red {{ color: #ee0000; }}
        .s2-vs {{ display: flex; align-items: center; justify-content: center; font-family: 'Red Hat Display', sans-serif; font-weight: 900; font-size: 1.6rem; color: #383838; }}
        .s2-most-popular {{ margin-top: 32px; text-align: center; opacity: 0; }}
        .s2-most-popular.animate {{ animation: fadeIn 0.6s ease forwards; }}
        .s2-most-popular .flag {{ font-size: 2.4rem; }}
        .s2-most-popular .label {{ font-size: 0.8rem; color: #6a6e73; text-transform: uppercase; letter-spacing: 1px; margin-top: 4px; }}
        .s2-most-popular .val {{ font-family: 'Red Hat Mono', monospace; font-weight: 700; color: #f0ab00; font-size: 1.1rem; }}

        /* Slide 3: Fun Facts */
        .s3-heading {{ font-family: 'Red Hat Display', sans-serif; font-weight: 900; font-size: 2.2rem; text-align: center; margin-bottom: 40px; }}
        .s3-facts {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; width: 100%; max-width: 800px; }}
        .s3-fact {{ background: #1f1f1f; border: 1px solid #292929; border-radius: 14px; padding: 28px 24px; text-align: center; opacity: 0; transform: translateY(20px); }}
        .s3-fact.animate {{ animation: cardIn 0.5s ease forwards; }}
        .s3-fact-icon {{ font-size: 2.4rem; margin-bottom: 12px; }}
        .s3-fact-num {{ font-family: 'Red Hat Mono', monospace; font-weight: 700; font-size: 2rem; color: #ee0000; }}
        .s3-fact-text {{ font-size: 0.9rem; color: #a3a3a3; margin-top: 6px; line-height: 1.4; }}

        /* Slide 4: Drum Roll */
        .s4-drum {{ text-align: center; }}
        .s4-drum-heading {{ font-family: 'Red Hat Display', sans-serif; font-weight: 900; font-size: 2.8rem; color: #ee0000; margin-bottom: 32px; }}
        .s4-drum-dots {{ font-size: 3rem; animation: pulse 1s ease-in-out infinite; }}
        .s4-drum-hint {{ margin-top: 40px; font-size: 0.9rem; color: #4a4a4a; text-transform: uppercase; letter-spacing: 2px; }}
        @keyframes pulse {{ 0%, 100% {{ opacity: 0.3; }} 50% {{ opacity: 1; }} }}

        /* Slide 5: Podium */
        .podium {{ display: flex; align-items: flex-end; gap: 24px; max-width: 750px; width: 100%; }}
        .podium-place {{ flex: 1; text-align: center; opacity: 0; transform: scale(0.3); transition: none; }}
        .podium-place.revealed {{ animation: medalDrop 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) forwards; }}
        .podium-medal {{ font-size: 3.5rem; margin-bottom: 8px; }}
        .podium-name {{ font-family: 'Red Hat Display', sans-serif; font-weight: 900; font-size: 1.8rem; }}
        .podium-score {{ font-family: 'Red Hat Mono', monospace; font-weight: 700; font-size: 1.3rem; color: #63993d; margin-top: 4px; }}
        .podium-diff {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; color: #6a6e73; margin-top: 4px; }}
        .podium-bar {{ border-radius: 12px 12px 0 0; margin-top: 16px; width: 100%; }}
        .silver .podium-bar {{ background: #c0c0c0; height: 120px; }}
        .gold .podium-bar {{ background: #ffd700; height: 160px; }}
        .bronze .podium-bar {{ background: #cd7f32; height: 90px; }}
        .silver .podium-name {{ color: #c0c0c0; }}
        .gold .podium-name {{ color: #ffd700; }}
        .gold .podium-medal {{ font-size: 4.5rem; }}
        .gold .podium-name {{ font-size: 2.4rem; }}
        .bronze .podium-name {{ color: #cd7f32; }}
        @keyframes medalDrop {{ to {{ opacity: 1; transform: scale(1); }} }}

        /* Slide 6: Runner-Up */
        .s6-heading {{ font-family: 'Red Hat Display', sans-serif; font-weight: 900; font-size: 2.2rem; text-align: center; margin-bottom: 40px; }}
        .runner-list {{ width: 100%; max-width: 600px; }}
        .runner-row {{
            display: grid; grid-template-columns: 60px 1fr 100px 80px;
            gap: 12px; align-items: center;
            background: #1f1f1f; border: 1px solid #292929; border-radius: 12px;
            padding: 18px 24px; margin-bottom: 12px;
            opacity: 0; transform: translateY(20px);
        }}
        .runner-row.animate {{ animation: cardIn 0.5s ease forwards; }}
        .runner-rank {{ font-family: 'Red Hat Mono', monospace; font-weight: 700; font-size: 1.1rem; color: #6a6e73; }}
        .runner-name {{ font-weight: 700; font-size: 1.1rem; }}
        .runner-score {{ font-family: 'Red Hat Mono', monospace; font-weight: 700; color: #63993d; font-size: 1.1rem; text-align: right; }}
        .runner-diff {{ font-size: 0.75rem; text-transform: uppercase; color: #6a6e73; text-align: right; }}

        @keyframes cardIn {{ to {{ opacity: 1; transform: translateY(0); }} }}
        @keyframes popIn {{ to {{ opacity: 1; transform: scale(1); }} }}
        @keyframes fadeIn {{ to {{ opacity: 1; }} }}
    </style>
</head>
<body>

<!-- SLIDE 1: Title + Numbers -->
<div class=\"slide active\" id=\"slide1\">
    <div class=\"red-bar\"></div>
    <div class=\"s1-title\">Whisper Voice Challenge</div>
    <div class=\"s1-subtitle\">{esc(event_name)} — {esc(event_dates)}</div>
    <div class=\"s1-grid\">
        <div class=\"s1-card\" data-delay=\"200\">
            <div class=\"s1-num\">{data['total_players']}</div>
            <div class=\"s1-label\">Players</div>
        </div>
        <div class=\"s1-card\" data-delay=\"400\">
            <div class=\"s1-num\">{data['total_games']}</div>
            <div class=\"s1-label\">Games</div>
        </div>
        <div class=\"s1-card\" data-delay=\"600\">
            <div class=\"s1-num\">{data['unique_langs']}</div>
            <div class=\"s1-label\">Languages</div>
        </div>
        <div class=\"s1-card\" data-delay=\"800\">
            <div class=\"s1-num\">{data['perfect_scores']}</div>
            <div class=\"s1-label\">Perfect Scores</div>
        </div>
    </div>
</div>

<!-- SLIDE 2: Language Battle -->
<div class=\"slide\" id=\"slide2\">
    <div class=\"red-bar\"></div>
    <div class=\"s2-heading\">The Language Battle</div>
    <div class=\"s2-columns\">
        <div class=\"s2-col\">
            <div class=\"s2-col-title green\">Easiest for Whisper</div>
            {easy_cards}
        </div>
        <div class=\"s2-vs\">VS</div>
        <div class=\"s2-col\">
            <div class=\"s2-col-title red\">Toughest for Humans</div>
            {hard_cards}
        </div>
    </div>
    <div class=\"s2-most-popular\" data-delay=\"1400\">
        <div class=\"label\">Most Attempted Language</div>
        <div class=\"flag\">{most_lang_flag}</div>
        <div class=\"val\">{esc(most_lang_name)} — {most_lang_count} attempts</div>
    </div>
</div>

<!-- SLIDE 3: Fun Facts -->
<div class=\"slide\" id=\"slide3\">
    <div class=\"red-bar\"></div>
    <div class=\"s3-heading\">By the Numbers</div>
    <div class=\"s3-facts\">
        <div class=\"s3-fact\" data-delay=\"200\">
            <div class=\"s3-fact-icon\">&#127760;</div>
            <div class=\"s3-fact-num\">{data['unique_langs']}</div>
            <div class=\"s3-fact-text\">Languages spoken<br>by participants</div>
        </div>
        <div class=\"s3-fact\" data-delay=\"400\">
            <div class=\"s3-fact-icon\">&#127919;</div>
            <div class=\"s3-fact-num\">{data['perfect_scores']}</div>
            <div class=\"s3-fact-text\">Perfect transcriptions<br>out of {data['total_attempts']} attempts</div>
        </div>
        <div class=\"s3-fact\" data-delay=\"600\">
            <div class=\"s3-fact-icon\">&#128293;</div>
            <div class=\"s3-fact-num\">{best_acc}%</div>
            <div class=\"s3-fact-text\">Average accuracy<br>for {esc(best_acc_lang)}</div>
        </div>
        <div class=\"s3-fact\" data-delay=\"800\">
            <div class=\"s3-fact-icon\">&#129504;</div>
            <div class=\"s3-fact-num\">{worst_acc}%</div>
            <div class=\"s3-fact-text\">Average accuracy<br>for {esc(worst_acc_lang)} — the toughest</div>
        </div>
    </div>
</div>

<!-- SLIDE 4: Drum Roll -->
<div class=\"slide\" id=\"slide4\">
    <div class=\"s4-drum\">
        <div class=\"s4-drum-heading\">&#127942; And the Winners Are...</div>
        <div class=\"s4-drum-dots\">&#9679; &#9679; &#9679;</div>
    </div>
</div>

<!-- SLIDE 5: Podium -->
<div class=\"slide\" id=\"slide5\">
    <div class=\"red-bar\"></div>
    <div class=\"s4-drum-heading\" style=\"margin-bottom:32px\">&#127942; Winners</div>
    <div class=\"podium\">
        {podium_html}
    </div>
</div>

{runner_slide}

<!-- Navigation -->
<div class=\"nav-dots\">
    {dots}
</div>
<div class=\"nav-hint\">&#8592; &#8594; arrow keys to navigate</div>

<script>
    const slides = document.querySelectorAll('.slide');
    const dots = document.querySelectorAll('.dot');
    let current = 0;
    let transitioning = false;

    const PODIUM_SLIDE = 4;
    const revealOrder = {reveal_order_js};
    let revealStep = 0;

    function advance() {{
        if (current === PODIUM_SLIDE && revealStep < revealOrder.length) {{
            document.getElementById(revealOrder[revealStep]).classList.add('revealed');
            revealStep++;
            return;
        }}
        goTo(current + 1);
    }}

    function goTo(idx) {{
        if (idx < 0 || idx >= slides.length || idx === current || transitioning) return;
        transitioning = true;

        slides[current].className = 'slide';
        dots[current].classList.remove('active');

        if (current === PODIUM_SLIDE) {{
            revealOrder.forEach(id => document.getElementById(id).classList.remove('revealed'));
            revealStep = 0;
        }}

        current = idx;
        slides[current].className = 'slide active';
        dots[current].classList.add('active');

        animateSlide(current);
        setTimeout(() => {{ transitioning = false; }}, 500);
    }}

    function animateSlide(idx) {{
        const items = slides[idx].querySelectorAll('[data-delay]');
        items.forEach(el => {{
            el.classList.remove('animate');
            void el.offsetWidth;
            setTimeout(() => el.classList.add('animate'), parseInt(el.dataset.delay) || 0);
        }});
    }}

    document.addEventListener('keydown', e => {{
        if (e.key === 'ArrowRight' || e.key === ' ') {{ e.preventDefault(); advance(); }}
        if (e.key === 'ArrowLeft') {{ e.preventDefault(); goTo(current - 1); }}
    }});

    document.addEventListener('click', e => {{
        if (e.target.closest('.nav-dots')) return;
        if (e.clientX / window.innerWidth > 0.3) advance();
        else goTo(current - 1);
    }});

    animateSlide(0);
</script>
</body>
</html>'''

with open(output_file, 'w') as f:
    f.write(HTML)
print(f'Ceremony presentation saved: {output_file}')
"

echo "Done: $OUTPUT"
