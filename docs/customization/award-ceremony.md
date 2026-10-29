# Generate award ceremony presentation

Create an animated HTML presentation for the tournament award ceremony using live
tournament data. The presentation is self-contained (one HTML file, no build step)
and designed for fullscreen display on stage.

## Slides

1. **Title + Key Numbers** — event name, player count, games, languages, perfect scores
2. **Language Battle** — top 3 easiest vs hardest languages, most attempted language
3. **By the Numbers** — fun facts with animated card reveals
4. **Drum Roll** — suspense transition
5. **Winners Podium** — gold/silver/bronze revealed one at a time (3rd → 2nd → 1st)
6. **Runner-Up** — additional ranked players (optional)

Navigate with arrow keys, spacebar, or click. On the podium slide, each press
reveals the next winner instead of advancing.

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
| `--runners N` | `4` | Number of runner-up entries |

### Data sourced

The script queries the live SQLite database via `oc exec` and extracts:
- Total players, games, attempts, perfect scores (accuracy ≥ 99%)
- Per-language accuracy rankings and attempt counts
- Most attempted language
- Top players by best single score
- Returning player count

### PPTX generation

The HTML deck is the primary ceremony format (animations, dark theme, podium
reveals). For offline sharing or archiving, generate a PPTX alongside it.
The repository includes reference scripts (`generate_stats_pptx.py`) that use
`python-pptx`. Install it with `pip install python-pptx` if needed. The agent
can generate a PPTX using the same data and the Red Hat brand colors from the
reference scripts. This is not automated in `generate-ceremony.sh` because
`python-pptx` is not a standard library package.

## Presentation tips

- Run fullscreen (F11 in Chrome) on the stage display
- Dark theme (#151515 background) works well in dimly lit conference halls
- Test the podium reveal sequence before the ceremony — each click/keypress
  reveals one winner
- Generate the presentation just before the ceremony to include final scores
- Keep the output file private until the ceremony to preserve the surprise
