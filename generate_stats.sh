#!/bin/bash
# Generates stats HTML page from live tournament data
# Usage: ./generate_stats.sh [output_file]
# Requires: oc logged into the primary cluster, whisper namespace

OUTPUT="${1:-tournament-stats.html}"

echo "Fetching data from primary cluster..."

STATS_JSON=$(oc exec deployment/whisper-ui -n whisper -- python3 -c "
import sqlite3, json

db = sqlite3.connect('/app/data/tournament.db')

# Total players
total_players = db.execute('SELECT COUNT(*) FROM players').fetchone()[0]
rh_players = db.execute(\"SELECT COUNT(*) FROM players WHERE email LIKE '%@redhat.com'\").fetchone()[0]
ext_players = total_players - rh_players

# Total games
total_games = db.execute('SELECT COUNT(*) FROM games WHERE completed_at IS NOT NULL').fetchone()[0]

# Per-language stats
lang_stats = db.execute('''
    SELECT language, COUNT(*) as attempts,
           ROUND(AVG(CASE WHEN status != 'skip' THEN accuracy END)*100,1) as avg_acc,
           ROUND(MAX(accuracy)*100,1) as max_acc,
           COUNT(CASE WHEN accuracy >= 0.99 THEN 1 END) as perfect
    FROM attempts WHERE status != 'skip'
    GROUP BY language ORDER BY avg_acc DESC
''').fetchall()

# Top 5 leaderboard
top5 = db.execute('''
    SELECT p.nickname, MAX(g.total_score) as best, g.difficulty
    FROM games g JOIN players p ON p.id = g.player_id
    WHERE g.completed_at IS NOT NULL AND g.total_score IS NOT NULL
    GROUP BY g.player_id ORDER BY best DESC LIMIT 5
''').fetchall()

# Total attempts
total_attempts = db.execute('SELECT COUNT(*) FROM attempts WHERE status != \"skip\"').fetchone()[0]
perfect_scores = db.execute('SELECT COUNT(*) FROM attempts WHERE accuracy >= 0.99').fetchone()[0]

# Unique languages attempted
unique_langs = db.execute('SELECT COUNT(DISTINCT language) FROM attempts').fetchone()[0]

# Returning players
returning = db.execute('''
    SELECT COUNT(*) FROM (
        SELECT player_id FROM games WHERE completed_at IS NOT NULL
        GROUP BY player_id HAVING COUNT(*) > 1
    )
''').fetchone()[0]

result = {
    'total_players': total_players,
    'rh_players': rh_players,
    'ext_players': ext_players,
    'total_games': total_games,
    'total_attempts': total_attempts,
    'perfect_scores': perfect_scores,
    'unique_langs': unique_langs,
    'returning': returning,
    'lang_stats': [{'lang': r[0], 'attempts': r[1], 'avg_acc': r[2], 'max_acc': r[3], 'perfect': r[4]} for r in lang_stats],
    'top5': [{'nickname': r[0], 'score': r[1], 'difficulty': r[2]} for r in top5]
}
db.close()
print(json.dumps(result))
")

echo "Generating HTML..."

python3 -c "
import json, sys

data = json.loads('''$STATS_JSON''')

lang_names = {
    'sk':'Slovak','cs':'Czech','en':'English','pl':'Polish','hu':'Hungarian',
    'de':'German','es':'Spanish','fi':'Finnish','fr':'French','hr':'Croatian',
    'is':'Icelandic','no':'Norwegian','sr':'Serbian','tr':'Turkish','it':'Italian',
    'pt':'Portuguese','nl':'Dutch','sv':'Swedish','ro':'Romanian','uk':'Ukrainian',
    'ja':'Japanese','ko':'Korean','ar':'Arabic','zh':'Chinese','th':'Thai','hi':'Hindi',
    'sl':'Slovenian','bg':'Bulgarian','bs':'Bosnian'
}

lang_flags = {
    'sk':'\U0001f1f8\U0001f1f0','cs':'\U0001f1e8\U0001f1ff','en':'\U0001f1ec\U0001f1e7',
    'pl':'\U0001f1f5\U0001f1f1','hu':'\U0001f1ed\U0001f1fa','de':'\U0001f1e9\U0001f1ea',
    'es':'\U0001f1ea\U0001f1f8','fi':'\U0001f1eb\U0001f1ee','fr':'\U0001f1eb\U0001f1f7',
    'hr':'\U0001f1ed\U0001f1f7','is':'\U0001f1ee\U0001f1f8','no':'\U0001f1f3\U0001f1f4',
    'sr':'\U0001f1f7\U0001f1f8','tr':'\U0001f1f9\U0001f1f7','it':'\U0001f1ee\U0001f1f9',
    'pt':'\U0001f1f5\U0001f1f9','nl':'\U0001f1f3\U0001f1f1','sv':'\U0001f1f8\U0001f1ea',
    'ro':'\U0001f1f7\U0001f1f4','uk':'\U0001f1fa\U0001f1e6','ja':'\U0001f1ef\U0001f1f5',
    'ko':'\U0001f1f0\U0001f1f7','ar':'\U0001f1f8\U0001f1e6','zh':'\U0001f1e8\U0001f1f3',
    'th':'\U0001f1f9\U0001f1ed','hi':'\U0001f1ee\U0001f1f3','sl':'\U0001f1f8\U0001f1ee',
    'bg':'\U0001f1e7\U0001f1ec','bs':'\U0001f1e7\U0001f1e6'
}

langs = data['lang_stats']
easiest = langs[:3]
hardest = list(reversed(langs[-3:]))

# Build language bars HTML
lang_bars = ''
for l in langs:
    flag = lang_flags.get(l['lang'], '')
    name = lang_names.get(l['lang'], l['lang'])
    acc = l['avg_acc'] or 0
    color = '#63993d' if acc >= 85 else '#f0ab00' if acc >= 60 else '#ee0000'
    lang_bars += f'''
        <div class=\"lang-row\">
            <div class=\"lang-name\">{flag} {name}</div>
            <div class=\"lang-bar-bg\">
                <div class=\"lang-bar\" style=\"width:{acc}%;background:{color}\"></div>
            </div>
            <div class=\"lang-acc\">{acc}%</div>
            <div class=\"lang-tries\">{l['attempts']}</div>
        </div>'''

# Top 5
top_rows = ''
for i, t in enumerate(data['top5']):
    medal = ['&#129351;','&#129352;','&#129353;','',''][i] if i < 3 else ''
    top_rows += f'''
        <div class=\"top-row\">
            <span class=\"top-rank\">{medal} #{i+1}</span>
            <span class=\"top-nick\">{t['nickname']}</span>
            <span class=\"top-score\">{t['score']:.1f}</span>
            <span class=\"top-diff\">{t['difficulty']}</span>
        </div>'''

html = f'''<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>Whisper Voice Challenge — Tournament Stats</title>
    <link href=\"https://fonts.googleapis.com/css2?family=Red+Hat+Display:wght@400;500;700;900&family=Red+Hat+Text:wght@400;500;700&family=Red+Hat+Mono:wght@400;700&display=swap\" rel=\"stylesheet\">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: \"Red Hat Text\", sans-serif; background: #151515; color: #fff; padding: 40px; }}
        h1 {{ font-family: \"Red Hat Display\", sans-serif; font-weight: 900; color: #ee0000; font-size: 2.2rem; margin-bottom: 4px; }}
        .subtitle {{ color: #a3a3a3; margin-bottom: 32px; font-size: 1rem; }}
        .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 36px; }}
        .stat-card {{ background: #1f1f1f; border-radius: 10px; padding: 20px; text-align: center; }}
        .stat-num {{ font-family: \"Red Hat Mono\", monospace; font-weight: 700; font-size: 2.6rem; color: #ee0000; }}
        .stat-label {{ font-size: 0.85rem; color: #a3a3a3; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; }}
        .two-col {{ display: grid; grid-template-columns: 2fr 1fr; gap: 32px; }}
        .section-title {{ font-family: \"Red Hat Display\", sans-serif; font-weight: 900; font-size: 1.2rem; color: #ee0000; margin-bottom: 16px; text-transform: uppercase; letter-spacing: 1px; }}
        .lang-header {{ display: grid; grid-template-columns: 120px 1fr 60px 50px; gap: 8px; font-size: 0.7rem; color: #6a6e73; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; padding: 0 4px; }}
        .lang-row {{ display: grid; grid-template-columns: 120px 1fr 60px 50px; gap: 8px; align-items: center; padding: 5px 4px; border-bottom: 1px solid #292929; }}
        .lang-name {{ font-size: 0.85rem; white-space: nowrap; }}
        .lang-bar-bg {{ height: 14px; background: #292929; border-radius: 7px; overflow: hidden; }}
        .lang-bar {{ height: 100%; border-radius: 7px; transition: width 0.3s; }}
        .lang-acc {{ font-family: \"Red Hat Mono\", monospace; font-size: 0.85rem; text-align: right; font-weight: 700; }}
        .lang-tries {{ font-size: 0.75rem; color: #6a6e73; text-align: right; }}
        .top-row {{ display: grid; grid-template-columns: 70px 1fr 80px 70px; gap: 8px; padding: 10px 8px; border-bottom: 1px solid #292929; align-items: center; }}
        .top-rank {{ font-size: 1rem; }}
        .top-nick {{ font-weight: 700; font-size: 1rem; }}
        .top-score {{ font-family: \"Red Hat Mono\", monospace; font-weight: 700; color: #63993d; font-size: 1.1rem; text-align: right; }}
        .top-diff {{ font-size: 0.75rem; text-transform: uppercase; color: #a3a3a3; text-align: right; }}
        .highlight-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 24px; }}
        .highlight {{ background: #1f1f1f; border-radius: 10px; padding: 16px 20px; }}
        .highlight-title {{ font-size: 0.75rem; color: #6a6e73; text-transform: uppercase; margin-bottom: 8px; }}
        .highlight-langs {{ font-size: 0.95rem; }}
        .highlight-langs .acc {{ font-family: \"Red Hat Mono\", monospace; font-weight: 700; color: #63993d; }}
        .highlight-langs.hard .acc {{ color: #ee0000; }}
    </style>
</head>
<body>
    <h1>Whisper Voice Challenge</h1>
    <div class=\"subtitle\">Innovate Together Sibenik — October 13–14, 2026</div>

    <div class=\"grid\">
        <div class=\"stat-card\">
            <div class=\"stat-num\">{data['total_players']}</div>
            <div class=\"stat-label\">Players</div>
        </div>
        <div class=\"stat-card\">
            <div class=\"stat-num\">{data['total_games']}</div>
            <div class=\"stat-label\">Games Played</div>
        </div>
        <div class=\"stat-card\">
            <div class=\"stat-num\">{data['unique_langs']}</div>
            <div class=\"stat-label\">Languages Tested</div>
        </div>
        <div class=\"stat-card\">
            <div class=\"stat-num\">{data['perfect_scores']}</div>
            <div class=\"stat-label\">Perfect Transcriptions</div>
        </div>
    </div>

    <div class=\"two-col\">
        <div>
            <div class=\"section-title\">Accuracy by Language</div>
            <div class=\"lang-header\">
                <div>Language</div><div></div><div style=\"text-align:right\">Avg</div><div style=\"text-align:right\">n</div>
            </div>
            {lang_bars}

            <div class=\"highlight-row\">
                <div class=\"highlight\">
                    <div class=\"highlight-title\">Easiest for Whisper</div>
                    <div class=\"highlight-langs\">
                        {'<br>'.join(f'{lang_flags.get(l[\"lang\"],\"\")} {lang_names.get(l[\"lang\"],l[\"lang\"])} <span class=\"acc\">{l[\"avg_acc\"]}%</span>' for l in easiest)}
                    </div>
                </div>
                <div class=\"highlight\">
                    <div class=\"highlight-title\">Toughest for Whisper</div>
                    <div class=\"highlight-langs hard\">
                        {'<br>'.join(f'{lang_flags.get(l[\"lang\"],\"\")} {lang_names.get(l[\"lang\"],l[\"lang\"])} <span class=\"acc\">{l[\"avg_acc\"]}%</span>' for l in hardest)}
                    </div>
                </div>
            </div>
        </div>
        <div>
            <div class=\"section-title\">Top 5 Players</div>
            {top_rows}
        </div>
    </div>
</body>
</html>'''

with open('$OUTPUT', 'w') as f:
    f.write(html)
print('Done: $OUTPUT')
"

echo "Stats page generated: $OUTPUT"
