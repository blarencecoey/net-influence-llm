# Decisions

**Idea:** To catch colluding AI agents, don't ask who moves together; ask who moves together *more than anyone else can explain*, and set the bar using honest games, because honest copies of the same model look like colluders.

**Viewer outcome:** after watching, a viewer can define collusion, describe net influence in one sentence, and name why LLM twins break the published threshold and how calibration fixes it.

## Log (one line each)
- Audience: sprint judges and technically curious viewers who know what an LLM is but not conditional mutual information. Assumed belief: correlated moves = collusion.
- Length: 75 s (brief default 60 s): define + why + method + two results + blind spots does not fit 60 s at readable caption speed.
- No voiceover: no text-to-speech engine in the container. Captions carry the narration and are drawn into every frame (burned in by construction); `captions.srt` ships too. Audio is a music bed + meaning cues, so the audio-only pass carries mood and structure, not the idea (logged as a known limitation).
- Brand: none in the repo (`./brand`, `./refs`, `./screens` absent). Built a neutral token set (warm paper ground, ink, one coral accent) in `src/tokens.css` / `src/tokens.js`. No real screenshots used; the film draws its own diagrams.
- Fonts: Inter (OFL-1.1) + DejaVu Sans Mono (Bitstream Vera license), copied from the system packages into `src/fonts/` with their license files.
- Frame rate: 30 fps (not 60) to keep four headless renders under ~15 min on a 4-core CPU; nothing in the film moves fast enough to need 60.
- Renderer: Playwright Chromium (pre-installed) instead of Puppeteer; drawing on one `<canvas>` so each frame is a pure function of `t`.
- Tone: lighthearted via faces (blinks, a wink, smiles), "Suspiciously helpful.", "Plot twist". No jokes inside the numbers.
- Accent colour = collusion / flag only. Model families are told apart by head shape *and* a text tag, never colour alone.
- S04 bar heights are illustrative and labelled so; every other number is from `notes/results/fact-sheet.md` (see `SOURCES.md`).
- Arc: the twin false-positive (S06) sits in Proof (it is the detector run on real LLM data); the Turn (S07) changes how collusion is carried (agreed in advance, three colluders). S07 lands at 80–91 %.
- Direction chosen: **A, "Paper & ink"** (see `directions.html`): warm and friendly matches the lighthearted brief; B (chalkboard) read as a lecture, C (blueprint) read as corporate.
- Retimed two captions that read too fast (< 0.3 s/word): S06 "…Mostly the twins.", S07 "a pre-agreed plan only shows up one move later". Changed in `TIMELINE.captions`, not by stretching tweens.
- Design review (fresh-context subagent) fixes, before/after pairs in `review/`:
  - S04: rival bars (C→B, D→B) now dim after the subtraction with the note "rivals: only used to subtract"; the 0.05 line runs only under the A→B bar; "both ways" shown as "A→B ✓ B→A ✓". Before, the raw rival bars sat above the 0.05 line and invited "why aren't C and D flagged?".
  - S03: the Auctions / Pricing / Trading cards stay on screen beside the question ("Same trick, real money.").
  - S07: one term, "one move later", on the link, the card and the caption; "Runs flagged, looking at:" moved above the two rows.
  - 1:1: table text gets a size floor; the "0.000" triangle label is dropped in 1:1 (the card carries it); link labels sit above the heads.
  - Footnote text sizes raised to ≥ 28 px in the virtual panel.
- Not fixed: S01 has no running tally beyond the per-agent points (the points already show B at 0); dimmed agents in S07 stay low contrast on purpose.
