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

All run on 2026-10-25 in the build container.

- **Outputs:** `ffprobe` shows each cut at 75.000 s and 30 fps with one H.264 and one AAC stream. Sizes: 16:9 1920×1080, 9:16 1080×1920, 1:1 1080×1080.
- **Video determinism:** the same frames (t = 34.5 s and 52.3 s, 16:9) were rendered twice and `cmp` found them byte-identical (`review/determinism/`).
- **Audio determinism:** three offline renders were **not** bit-identical. They differ by at most 1 LSB (16-bit) on 576–625 of 6,615,000 samples. That is inaudible, but it is not exact.
- **Loudness** (`ffmpeg -af ebur128=peak=true` on `out/master_16x9.mp4`): integrated −16.0 LUFS, true peak −1.5 dBFS, after a two-pass `loudnorm` (I = −16, TP = −1.5).
- **Caption reading time:** every caption is on screen for at least max(1.5 s, 0.3 s × words). Two failed this check and were reworded (see `DECISIONS.md`).
- **Stills at every beat midpoint** in all three aspects (`stills/`). Readability sheets at 390 px wide for 9:16 and 1:1 are in `review/at390_*.png`. Captions and headlines are readable at that width; agent tags and footnotes are marginal in 1:1.
- **Reduced-motion cut:** frames pulled from both cuts at 5, 25.15, 34.5 and 57 s (`review/final/master_vs_reduced.png`). Mid-tween, the reduced cut shows a cut where the master shows movement (the bar at 25.15 s). Settled frames match.
- **Design review:** a fresh-context subagent reviewed the stills against `SCENES.md`. Its fixes have before/after pairs in `review/pair_*.png`. It found no colour-only signals and nothing that flashes. It checked the on-screen numbers against `SOURCES.md` and they match.
- **Not done:** the full film was not watched end to end by a person. The muted and audio-only passes were not done by ear. I only checked muted frames as stills and confirmed the audio cue list against `TIMELINE.cues`.

## Known limitations

- **No voiceover.** No text-to-speech engine was available in the build container. The audio-only pass carries mood and structure (motif on "collusion", "flag" and the ending; cues on wins, stamps and stats) but not the idea. Captions are drawn into every frame and shipped as `.srt`.
- **Small labels in the 16:9 cut on phones.** At 390 px wide the 16:9 frame scales to 0.2×; captions and headlines stay legible, model tags and footnotes do not. Use the 9:16 or 1:1 cut on mobile.
- **Dimmed agents in S07** (C and D, behind the blind-spot card) are deliberately low contrast (about 2.3:1 per the review). They are not carrying information in that scene.
- **S01 rounds are an illustration**, not data from a run.
