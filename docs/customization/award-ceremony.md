# Generate award ceremony presentation

Create an animated HTML presentation for the tournament award ceremony using live
tournament data. The presentation is self-contained (one HTML file, no build step)
and designed for fullscreen display on stage.

## Slides

1. **Title and key numbers** — event, players, games, languages, perfect transcriptions
2. **Language battle** — easiest vs toughest languages (accuracy bars), most played
3. **Whisper fail of the day** — optional; what the player said vs. what Whisper heard
4. **Drum roll**
5. **Winners** — podium revealed one at a time (3rd → 2nd → 1st), honourable
   mentions (places 4–7 by default, `--runners N`) below it. This is the last slide.

The deck language follows the deployment's required challenge language
(`REQUIRED_CHALLENGE_LANGUAGE`, read from the running pod): Czech, Slovak or
English; other languages fall back to English. Override with `--lang cs|sk|en`.

Controls: → / space / click to advance, ← to go back, F fullscreen, B blackout.
On the podium slide each press reveals the next winner.

The deck follows Red Hat brand standards: light theme, palette colours only,
embedded Red Hat Display/Text fonts (SIL OFL) and the unmodified standard logo
from `scripts/ceremony/assets/`. It is one offline HTML file with no network
dependencies. The renderer is `scripts/ceremony/render.py` (standard library).

## Generate from live data

Requires `oc` logged into the cluster and Python 3 (standard library only).

```bash
./scripts/generate-ceremony.sh \
  --event "Innovate Together Sibenik" \
  --dates "October 13–14, 2026" \
  --namespace whisper \
  --output ceremony.html
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--event NAME` | (required) | Event/conference name |
| `--dates DATES` | (required) | Date string shown on title slide |
| `--namespace NS` | `whisper` | Kubernetes namespace |
| `--output FILE` | `ceremony.html` | Output HTML file path |
| `--winners N` | `3` | Number of podium winners |
| `--runners N` | `4` | Honourable mentions under the podium |
| `--lang CODE` | required language | Deck language: `cs`, `sk` or `en` |

### Whisper Fail of the Day

This slide is the reason to generate the deck through the agent
(`/whisper-operations`). Humor needs judgment, and nobody reads hundreds of
transcripts by hand, so a plain script run produces a deck without it.

To get it, ask the agent for the deck. It goes through the misheard
transcripts, picks the funniest one (never anything offensive or personal),
writes a one-line note in the deck language, and tells you what it picked,
so you can ask for a different one or none. You don't type any of the
options below; they're how the agent passes its pick to the script.

| Flag (set by the agent) | Purpose |
|------|---------|
| `--list-bloopers [N]` | Pre-filter candidates: partly-correct transcriptions (15–95 % similarity after ignoring case and punctuation), deduplicated, labelled Latin or non-Latin script |
| `--blooper ID` | Add the fail slide for that attempt |
| `--blooper-note TEXT` | One short line under the fail, e.g. a translation or the punchline |
| `--blooper-credit` | Show the player's nickname (anonymous by default); only when you ask for it and the player agreed |

### Data sourced

The script queries the live SQLite database via `oc exec` and extracts:
- Total players, games, attempts, perfect scores (accuracy ≥ 99%)
- Per-language accuracy rankings and attempt counts
- Most attempted language
- Top players by best single score
- Returning player count

### Output format

The HTML deck is the only supported format; there is no PPTX export. To share
or archive the results, keep the generated HTML file. It works offline.

## Presentation tips

- Press F for fullscreen on the stage display
- Test the podium reveal sequence before the ceremony — each click/keypress
  reveals one winner
- Generate the presentation just before the ceremony to include final scores
- Keep the output file private until the ceremony to preserve the surprise
