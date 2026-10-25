# Explainer film: catching colluding AI agents

A 75-second explainer for this project: what collusion is, the 4-agent Rock-Paper-Scissors experiment, how pairwise net influence (Bonjour et al., UAI 2022) works, what we found when we ran it on LLM agents, and why it matters. Lighthearted tone, no voiceover (captions carry the narration).

> [claude] Made with Claude as writer, designer and render engineer. It is a companion piece, not report prose. Every number on screen is traced in `SOURCES.md` to `notes/results/fact-sheet.md`. The S04 bar heights are illustrative and labelled as such.

## Deliverables

| File | What |
|---|---|
| `out/master_16x9.mp4` | 1920×1080, 30 fps, 75 s, AAC audio, captions drawn in |
| `out/cut_9x16.mp4` | 1080×1920, re-laid out (table above panel), not cropped |
| `out/cut_1x1.mp4` | 1080×1080, re-laid out |
| `out/reduced_motion_16x9.mp4` | Same sequence of ideas; movement replaced by cuts, fades kept |
| `out/animatic_16x9.mp4` | Timing pass: grey blocks + scene IDs on the real timeline, 10 fps |
| `captions.srt` | Generated from `TIMELINE.captions` |
| `contact.png` | One still per scene with ID, time range and what it teaches |
| `directions.html` | Three design directions at the same beat; A chosen |
| `STORY.md`, `SCENES.md`, `DECISIONS.md`, `SOURCES.md` | Story, scene specs, decision log, sources |
| `review/` | Before/after frame pairs for every fix from the design review, determinism frames, 390 px readability sheets |
| `src/` | Everything that re-renders the film |

## Re-render

Needs Node with Playwright + Chromium, ffmpeg, and Python 3 (for the loudness pass).

```sh
cd film && sh build.sh
```

`src/index.html?aspect=16x9|9x16|1x1&reduced=1&t=34.5` opens any frame in a browser; `window.seek(t)` repaints it. `src/stills.mjs` writes stills, `src/render.mjs` writes one cut, `src/audio.mjs` renders the sound offline, `src/captions.mjs` writes the .srt.

## What was tested (and how)

RESULTS_PLACEHOLDER

## Known limitations

- **No voiceover.** No text-to-speech engine was available in the build container. The audio-only pass carries mood and structure (motif on "collusion", "flag" and the ending; cues on wins, stamps and stats) but not the idea. Captions are drawn into every frame and shipped as `.srt`.
- **Small labels in the 16:9 cut on phones.** At 390 px wide the 16:9 frame scales to 0.2×; captions and headlines stay legible, model tags and footnotes do not. Use the 9:16 or 1:1 cut on mobile.
- **Dimmed agents in S07** (C and D, behind the blind-spot card) are deliberately low contrast (about 2.3:1 per the review). They are not carrying information in that scene.
- **S01 rounds are an illustration**, not data from a run.
