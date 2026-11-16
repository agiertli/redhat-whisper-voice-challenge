#!/usr/bin/env python3
"""Render the award ceremony deck as one self-contained HTML file.

Called by scripts/generate-ceremony.sh. Inputs come from environment variables
(STATS_JSON, EVENT_NAME, EVENT_DATES, OUTPUT_FILE, NUM_WINNERS, NUM_RUNNERS,
BLOOPER_CREDIT, BLOOPER_NOTE, DECK_LANG). Standard library only.

Branding follows https://www.redhat.com/en/about/brand/standards: light theme,
palette colours only, Red Hat Display/Text Regular and Bold embedded (SIL OFL,
see assets/OFL.txt), the unmodified standard Red Hat logo (trademark of
Red Hat, Inc.), sentence case, no third-party icons. No network access is
needed at the venue.
"""
import base64
import html
import json
import os
from pathlib import Path

ASSETS = Path(__file__).resolve().parent / 'assets'

LANG_NAMES = {
    'en': {
        'sk': 'Slovak', 'cs': 'Czech', 'en': 'English', 'pl': 'Polish', 'hu': 'Hungarian',
        'de': 'German', 'es': 'Spanish', 'fi': 'Finnish', 'fr': 'French', 'hr': 'Croatian',
        'is': 'Icelandic', 'no': 'Norwegian', 'sr': 'Serbian', 'tr': 'Turkish', 'it': 'Italian',
        'pt': 'Portuguese', 'nl': 'Dutch', 'sv': 'Swedish', 'ro': 'Romanian', 'uk': 'Ukrainian',
        'ja': 'Japanese', 'ko': 'Korean', 'ar': 'Arabic', 'zh': 'Chinese', 'th': 'Thai',
        'hi': 'Hindi', 'sl': 'Slovenian', 'bg': 'Bulgarian', 'ka': 'Georgian', 'ru': 'Russian',
        'el': 'Greek', 'da': 'Danish',
    },
    'cs': {
        'sk': 'slovenština', 'cs': 'čeština', 'en': 'angličtina', 'pl': 'polština',
        'hu': 'maďarština', 'de': 'němčina', 'es': 'španělština', 'fi': 'finština',
        'fr': 'francouzština', 'hr': 'chorvatština', 'is': 'islandština', 'no': 'norština',
        'sr': 'srbština', 'tr': 'turečtina', 'it': 'italština', 'pt': 'portugalština',
        'nl': 'nizozemština', 'sv': 'švédština', 'ro': 'rumunština', 'uk': 'ukrajinština',
        'ja': 'japonština', 'ko': 'korejština', 'ar': 'arabština', 'zh': 'čínština',
        'th': 'thajština', 'hi': 'hindština', 'sl': 'slovinština', 'bg': 'bulharština',
        'ka': 'gruzínština', 'ru': 'ruština', 'el': 'řečtina', 'da': 'dánština',
    },
    'sk': {
        'sk': 'slovenčina', 'cs': 'čeština', 'en': 'angličtina', 'pl': 'poľština',
        'hu': 'maďarčina', 'de': 'nemčina', 'es': 'španielčina', 'fi': 'fínčina',
        'fr': 'francúzština', 'hr': 'chorvátčina', 'is': 'islandčina', 'no': 'nórčina',
        'sr': 'srbčina', 'tr': 'turečtina', 'it': 'taliančina', 'pt': 'portugalčina',
        'nl': 'holandčina', 'sv': 'švédčina', 'ro': 'rumunčina', 'uk': 'ukrajinčina',
        'ja': 'japončina', 'ko': 'kórejčina', 'ar': 'arabčina', 'zh': 'čínština',
        'th': 'thajčina', 'hi': 'hindčina', 'sl': 'slovinčina', 'bg': 'bulharčina',
        'ka': 'gruzínčina', 'ru': 'ruština', 'el': 'gréčtina', 'da': 'dánčina',
    },
}

# Deck texts. Phrasing avoids Czech/Slovak plural forms after numbers.
TEXT = {
    'en': {
        'players': 'Players', 'games': 'Games played', 'langs': 'Languages',
        'perfect': 'Perfect transcriptions', 'battle': 'The language battle',
        'easiest': 'Easiest for Whisper', 'toughest': 'Toughest for players',
        'avg': 'Average transcription accuracy', 'most': 'Most played: {lang} ({n}×)',
        'fail': 'Whisper fail of the day', 'said': 'The player said ({lang})',
        'heard': 'Whisper heard', 'acc': '{v} % accuracy', 'credit': 'Player: {name}',
        'drum': 'And the winners are…', 'winners': 'Winners', 'score': '{v} points',
        'mentions': 'Honourable mentions',
        'diff': {'easy': 'Easy', 'medium': 'Medium', 'hard': 'Hard'},
    },
    'cs': {
        'players': 'Hráči', 'games': 'Odehrané hry', 'langs': 'Jazyky',
        'perfect': 'Bezchybné přepisy', 'battle': 'Souboj jazyků',
        'easiest': 'Whisperu šly nejlépe', 'toughest': 'Pro hráče nejtěžší',
        'avg': 'Průměrná přesnost přepisu', 'most': 'Nejoblíbenější jazyk: {lang} ({n}×)',
        'fail': 'Whisperův přešlap dne', 'said': 'Hráč řekl ({lang})',
        'heard': 'Whisper slyšel', 'acc': 'přesnost {v} %', 'credit': 'Hráč: {name}',
        'drum': 'A vítězi jsou…', 'winners': 'Vítězové', 'score': 'skóre {v}',
        'mentions': 'Čestné uznání',
        'diff': {'easy': 'Lehká', 'medium': 'Střední', 'hard': 'Těžká'},
    },
    'sk': {
        'players': 'Hráči', 'games': 'Odohrané hry', 'langs': 'Jazyky',
        'perfect': 'Bezchybné prepisy', 'battle': 'Súboj jazykov',
        'easiest': 'Whisperu išli najlepšie', 'toughest': 'Pre hráčov najťažšie',
        'avg': 'Priemerná presnosť prepisu', 'most': 'Najobľúbenejší jazyk: {lang} ({n}×)',
        'fail': 'Whisperov prešľap dňa', 'said': 'Hráč povedal ({lang})',
        'heard': 'Whisper počul', 'acc': 'presnosť {v} %', 'credit': 'Hráč: {name}',
        'drum': 'A víťazmi sú…', 'winners': 'Víťazi', 'score': 'skóre {v}',
        'mentions': 'Čestné uznanie',
        'diff': {'easy': 'Ľahká', 'medium': 'Stredná', 'hard': 'Ťažká'},
    },
}


def esc(s):
    return html.escape(str(s))


def font_face(family, weight, filename):
    data = base64.b64encode((ASSETS / filename).read_bytes()).decode()
    return (f"@font-face {{ font-family: '{family}'; font-weight: {weight}; font-style: normal; "
            f"src: url(data:font/ttf;base64,{data}) format('truetype'); }}")


def main():
    data = json.loads(os.environ['STATS_JSON'])
    event_name = os.environ['EVENT_NAME']
    event_dates = os.environ['EVENT_DATES']
    output_file = os.environ['OUTPUT_FILE']
    num_winners = int(os.environ.get('NUM_WINNERS', '3'))
    num_runners = int(os.environ.get('NUM_RUNNERS', '4'))
    blooper_credit = os.environ.get('BLOOPER_CREDIT') == 'true'
    blooper_note = os.environ.get('BLOOPER_NOTE', '').strip()
    lang = (os.environ.get('DECK_LANG') or data.get('required_language') or 'en').strip().lower()
    if lang not in TEXT:
        lang = 'en'
    t = TEXT[lang]

    def num(v):
        s = f'{v:.1f}'.rstrip('0').rstrip('.') if isinstance(v, float) else str(v)
        return s.replace('.', ',') if lang in ('cs', 'sk') else s

    def lname(code, cap=False):
        n = LANG_NAMES[lang].get(code) or LANG_NAMES['en'].get(code) or str(code).upper()
        return n[:1].upper() + n[1:] if cap else n

    def diff(d):
        return t['diff'].get(str(d).lower(), str(d).capitalize())

    fonts = '\n'.join([
        font_face('Red Hat Display', 400, 'RedHatDisplay-Regular.ttf'),
        font_face('Red Hat Display', 700, 'RedHatDisplay-Bold.ttf'),
        font_face('Red Hat Text', 400, 'RedHatText-Regular.ttf'),
        font_face('Red Hat Text', 700, 'RedHatText-Bold.ttf'),
    ])
    logo = base64.b64encode((ASSETS / 'redhat-logo-a-standard-rgb.svg').read_bytes()).decode()

    slides = []

    # 1. Title and key numbers
    tiles = [(data['total_players'], t['players']), (data['total_games'], t['games']),
             (data['unique_langs'], t['langs']), (data['perfect_scores'], t['perfect'])]
    tile_html = ''.join(
        f'<div class="tile" data-delay="{200 + i * 150}"><div class="tile-num">{esc(num(n))}</div>'
        f'<div class="tile-label">{esc(label)}</div></div>'
        for i, (n, label) in enumerate(tiles))
    slides.append(f"""
<section class="slide" id="s-title">
  <div class="accent"></div>
  <h1>Whisper Voice Challenge</h1>
  <p class="sub">{esc(event_name)} · {esc(event_dates)}</p>
  <div class="tiles">{tile_html}</div>
</section>""")

    # 2. Language battle (only with enough data)
    langs = [l for l in data.get('lang_stats', []) if l.get('avg_acc') is not None]
    if len(langs) >= 2:
        n = min(3, len(langs) // 2) or 1
        easiest, hardest = langs[:n], list(reversed(langs[-n:]))

        def rows(items, cls, base):
            return ''.join(
                f'<div class="lrow" data-delay="{base + i * 150}">'
                f'<div class="lname">{esc(lname(l["lang"], cap=True))}</div>'
                f'<div class="ltrack"><div class="lbar {cls}" style="width:{max(4, min(100, l["avg_acc"]))}%"></div></div>'
                f'<div class="lval">{esc(num(l["avg_acc"]))} %</div></div>'
                for i, l in enumerate(items))
        most = data.get('most_attempted')
        most_html = (f'<p class="foot" data-delay="1300">'
                     f'{esc(t["most"].format(lang=lname(most["lang"]), n=most["count"]))}</p>') if most else ''
        slides.append(f"""
<section class="slide" id="s-langs">
  <div class="accent"></div>
  <h2>{esc(t['battle'])}</h2>
  <div class="lcols">
    <div><h3>{esc(t['easiest'])}</h3>{rows(easiest, 'good', 200)}</div>
    <div><h3>{esc(t['toughest'])}</h3>{rows(hardest, 'hard', 700)}</div>
  </div>
  <p class="caption">{esc(t['avg'])}</p>
  {most_html}
</section>""")

    # 3. Whisper fail of the day (optional)
    b = data.get('blooper')
    if b:
        note = f'<p class="bnote" data-delay="1500">{esc(blooper_note)}</p>' if blooper_note else ''
        credit = (f'<p class="caption" data-delay="1700">{esc(t["credit"].format(name=b["nickname"]))}</p>'
                  if blooper_credit else '')
        slides.append(f"""
<section class="slide" id="s-blooper">
  <div class="accent"></div>
  <h2>{esc(t['fail'])}</h2>
  <div class="bcard" data-delay="200">
    <div class="blabel">{esc(t['said'].format(lang=lname(b['lang'])))}</div>
    <div class="btext">{esc(b['phrase'])}</div>
  </div>
  <div class="bcard heard" data-delay="1000">
    <div class="blabel">{esc(t['heard'])}</div>
    <div class="btext">{esc(b['heard'])}</div>
    <div class="bacc">{esc(t['acc'].format(v=num(b['accuracy'])))}</div>
  </div>
  {note}{credit}
</section>""")

    # 4. Drum roll
    slides.append(f"""
<section class="slide center" id="s-drum">
  <h2 class="drum">{esc(t['drum'])}</h2>
  <div class="dots"><span></span><span></span><span></span></div>
</section>""")

    # 5. Winners: podium revealed 3rd -> 2nd -> 1st, honourable mentions below
    top = data.get('top_players', [])
    winners = top[:min(num_winners, 3)]
    podium, reveal = '', []
    for idx, cls in [(1, 'second'), (0, 'first'), (2, 'third')]:
        if idx >= len(winners):
            continue
        w = winners[idx]
        wid = f'place{idx + 1}'
        reveal.append((idx, wid))
        podium += f"""
    <div class="place {cls}" id="{wid}">
      <div class="pname">{esc(w['nickname'])}</div>
      <div class="pscore">{esc(t['score'].format(v=num(w['score'])))}</div>
      <div class="pdiff">{esc(diff(w['difficulty']))}</div>
      <div class="pbar"><span>{idx + 1}</span></div>
    </div>"""
    reveal_order = json.dumps([wid for _, wid in sorted(reveal, reverse=True)])
    runners = top[len(winners):len(winners) + num_runners]
    mentions = ''
    if runners:
        items = ''.join(
            f'<span class="mention"><b>{len(winners) + i + 1}.</b> {esc(r["nickname"])} '
            f'<span class="mscore">{esc(num(r["score"]))}</span></span>'
            for i, r in enumerate(runners))
        mentions = (f'<div class="mentions" data-delay="400">'
                    f'<span class="mlabel">{esc(t["mentions"])}</span>{items}</div>')
    slides.append(f"""
<section class="slide" id="s-podium">
  <div class="accent"></div>
  <h2>{esc(t['winners'])}</h2>
  <div class="podium">{podium}
  </div>
  {mentions}
</section>""")

    page = TEMPLATE.replace('/*FONTS*/', fonts) \
        .replace('{{LANG}}', lang) \
        .replace('{{LOGO}}', logo) \
        .replace('{{SLIDES}}', '\n'.join(slides)) \
        .replace('{{REVEAL}}', reveal_order) \
        .replace('{{TITLE}}', esc(f'Whisper Voice Challenge · {event_name}'))
    Path(output_file).write_text(page, encoding='utf-8')
    print(f'Ceremony presentation saved: {output_file} (language: {lang})')


TEMPLATE = r'''<!DOCTYPE html>
<html lang="{{LANG}}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{TITLE}}</title>
<!-- Fonts: Red Hat Display/Text, SIL Open Font License 1.1 (github.com/RedHatOfficial/RedHatFont).
     Logo: Red Hat standard logo, unmodified; trademark of Red Hat, Inc. -->
<style>
/*FONTS*/
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { width: 100%; height: 100%; overflow: hidden; }
body { font-family: 'Red Hat Text', sans-serif; font-weight: 400; background: #ffffff; color: #151515; line-height: 1.4; }
b { font-weight: 700; }

.slide { position: absolute; inset: 0; padding: 120px 140px 110px; display: flex; flex-direction: column; justify-content: center;
         opacity: 0; transform: translateX(40px); transition: opacity .45s ease, transform .45s ease; pointer-events: none; }
.slide.active { opacity: 1; transform: none; pointer-events: auto; }
.slide.center { align-items: center; text-align: center; }

.logo { position: fixed; top: 44px; left: 56px; height: 44px; z-index: 10; }
.accent { width: 72px; height: 6px; background: #ee0000; margin-bottom: 28px; }
h1 { font-family: 'Red Hat Display', sans-serif; font-weight: 700; font-size: 5rem; line-height: 1.2; }
h2 { font-family: 'Red Hat Display', sans-serif; font-weight: 700; font-size: 3.4rem; line-height: 1.2; margin-bottom: 44px; }
h3 { font-family: 'Red Hat Display', sans-serif; font-weight: 700; font-size: 1.6rem; line-height: 1.3; margin-bottom: 20px; }
.sub { font-size: 1.8rem; color: #4d4d4d; margin: 12px 0 64px; }
.caption { font-size: 1.2rem; color: #4d4d4d; margin-top: 28px; }
.foot { font-size: 1.5rem; margin-top: 20px; }

[data-delay] { opacity: 0; transform: translateY(16px); }
[data-delay].in { opacity: 1; transform: none; transition: opacity .5s ease, transform .5s ease; }

/* Title */
.tiles { display: grid; grid-template-columns: repeat(4, 1fr); gap: 28px; max-width: 1300px; }
.tile { background: #f2f2f2; border-radius: 16px; padding: 36px 32px; }
.tile-num { font-family: 'Red Hat Display', sans-serif; font-weight: 700; font-size: 4.2rem; line-height: 1.2; color: #ee0000; }
.tile-label { font-size: 1.3rem; color: #4d4d4d; margin-top: 8px; }

/* Language battle */
.lcols { display: grid; grid-template-columns: 1fr 1fr; gap: 96px; max-width: 1400px; }
.lrow { display: grid; grid-template-columns: 200px 1fr 110px; align-items: center; gap: 20px; margin-bottom: 22px; }
.lname { font-weight: 700; font-size: 1.6rem; }
.ltrack { height: 22px; background: #f2f2f2; border-radius: 11px; overflow: hidden; }
.lbar { height: 100%; border-radius: 11px; }
.lbar.good { background: #ee0000; }
.lbar.hard { background: #707070; }
.lval { font-weight: 700; font-size: 1.6rem; text-align: right; }

/* Blooper */
.bcard { background: #f2f2f2; border-radius: 16px; padding: 30px 40px; max-width: 1300px; margin-bottom: 24px; border-left: 8px solid #c7c7c7; }
.bcard.heard { background: #ffffff; border: 2px solid #e0e0e0; border-left: 8px solid #ee0000; }
.blabel { font-size: 1.2rem; color: #4d4d4d; margin-bottom: 8px; }
.btext { font-family: 'Red Hat Display', sans-serif; font-weight: 700; font-size: 2.6rem; line-height: 1.25; }
.bacc { font-size: 1.2rem; font-weight: 700; color: #a60000; margin-top: 10px; }
.bnote { font-size: 1.8rem; margin-top: 12px; max-width: 1300px; }

/* Drum roll */
.drum { font-size: 4.6rem; margin-bottom: 36px; }
.dots { display: flex; gap: 22px; }
.dots span { width: 22px; height: 22px; border-radius: 50%; background: #ee0000; animation: pulse 1.2s ease-in-out infinite; }
.dots span:nth-child(2) { animation-delay: .2s; } .dots span:nth-child(3) { animation-delay: .4s; }
@keyframes pulse { 0%, 100% { opacity: .2; } 50% { opacity: 1; } }

/* Podium */
.podium { display: flex; align-items: flex-end; justify-content: center; gap: 40px; width: 100%; max-width: 1200px; align-self: center; }
.place { flex: 1; text-align: center; opacity: 0; transform: translateY(40px); }
.place.shown { opacity: 1; transform: none; transition: opacity .6s ease, transform .6s cubic-bezier(.34, 1.4, .64, 1); }
.pname { font-family: 'Red Hat Display', sans-serif; font-weight: 700; font-size: 2.2rem; line-height: 1.2; overflow-wrap: anywhere; }
.first .pname { font-size: 2.9rem; }
.pscore { font-size: 1.5rem; margin-top: 6px; }
.pdiff { font-size: 1.2rem; color: #4d4d4d; margin-top: 2px; }
.pbar { margin-top: 20px; border-radius: 16px 16px 0 0; display: flex; align-items: flex-start; justify-content: center; padding-top: 18px; }
.pbar span { font-family: 'Red Hat Display', sans-serif; font-weight: 700; font-size: 3.4rem; line-height: 1.2; }
.first .pbar { height: 220px; background: #ee0000; color: #ffffff; }
.second .pbar { height: 165px; background: #4d4d4d; color: #ffffff; }
.third .pbar { height: 115px; background: #c7c7c7; color: #151515; }

/* Honourable mentions */
.mentions { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: center; gap: 12px 36px;
            margin-top: 36px; padding-top: 24px; border-top: 2px solid #e0e0e0; max-width: 1200px; width: 100%; align-self: center; font-size: 1.5rem; }
.mlabel { color: #4d4d4d; }
.mention b { font-family: 'Red Hat Display', sans-serif; color: #707070; }
.mscore { color: #4d4d4d; margin-left: 6px; }

.nav { position: fixed; bottom: 40px; left: 50%; transform: translateX(-50%); display: flex; gap: 12px; z-index: 10; }
.nav i { width: 12px; height: 12px; border-radius: 50%; background: #c7c7c7; cursor: pointer; }
.nav i.on { background: #ee0000; }
#blackout { position: fixed; inset: 0; background: #000000; z-index: 100; display: none; }
</style>
</head>
<body>
<img class="logo" alt="Red Hat" src="data:image/svg+xml;base64,{{LOGO}}">
{{SLIDES}}
<div class="nav"></div>
<div id="blackout"></div>
<script>
const slides = Array.from(document.querySelectorAll('.slide'));
const nav = document.querySelector('.nav');
slides.forEach((_, i) => { const d = document.createElement('i'); d.onclick = e => { e.stopPropagation(); go(i); }; nav.appendChild(d); });
const PODIUM = slides.findIndex(s => s.id === 's-podium');
const reveal = {{REVEAL}};
let cur = -1, step = 0;

function animate(s) {
  s.querySelectorAll('[data-delay]').forEach(el => {
    el.classList.remove('in');
    setTimeout(() => el.classList.add('in'), parseInt(el.dataset.delay, 10) || 0);
  });
}
function go(i) {
  if (i < 0 || i >= slides.length || i === cur) return;
  if (cur >= 0) slides[cur].classList.remove('active');
  if (cur === PODIUM) { reveal.forEach(id => document.getElementById(id).classList.remove('shown')); step = 0; }
  cur = i;
  slides[cur].classList.add('active');
  nav.querySelectorAll('i').forEach((d, k) => d.classList.toggle('on', k === cur));
  animate(slides[cur]);
}
function next() {
  if (cur === PODIUM && step < reveal.length) { document.getElementById(reveal[step++]).classList.add('shown'); return; }
  go(cur + 1);
}
document.addEventListener('keydown', e => {
  const k = e.key.toLowerCase();
  if (k === 'arrowright' || k === ' ' || k === 'pagedown') { e.preventDefault(); next(); }
  else if (k === 'arrowleft' || k === 'pageup') { e.preventDefault(); go(cur - 1); }
  else if (k === 'f') { document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen(); }
  else if (k === 'b') { const b = document.getElementById('blackout'); b.style.display = b.style.display === 'block' ? 'none' : 'block'; }
});
document.addEventListener('click', e => { (e.clientX / window.innerWidth > 0.3) ? next() : go(cur - 1); });
go(0);
</script>
</body>
</html>'''


if __name__ == '__main__':
    main()
