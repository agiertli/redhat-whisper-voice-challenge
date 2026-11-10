# Whisper booth guide

Interactive onboarding portal for facilitators and technical owners.
Published at https://agiertli.github.io/redhat-whisper-voice-challenge/

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # static output in dist/
```

Deployed by `.github/workflows/portal.yml` on every push to `main` that touches
`portal/`. The site is public: never add cluster URLs, tokens or passwords.

The game screen in the simulator is a mock of `src/templates/index.html`
(labelled v2.13). Scoring in `src/scoring.js` mirrors `src/app_streaming.py`;
update both together.
