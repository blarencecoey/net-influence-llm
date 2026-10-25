#!/bin/sh
# Re-render everything from src/. Needs node with Playwright (Chromium) and ffmpeg.
# Usage: sh build.sh        (run from film/)
set -e
mkdir -p out
node src/captions.mjs captions.srt
node src/audio.mjs out/audio.wav
LN=$(ffmpeg -hide_banner -i out/audio.wav -af loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p' \
  | python3 -c "import json,sys; j=json.load(sys.stdin); print(f\"loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true\")")
ffmpeg -y -loglevel error -i out/audio.wav -af "$LN" -ar 48000 out/audio_norm.wav

node src/render.mjs 16x9 0 out/video_16x9.mp4 &
node src/render.mjs 9x16 0 out/video_9x16.mp4 &
node src/render.mjs 1x1 0 out/video_1x1.mp4 &
node src/render.mjs 16x9 1 out/video_reduced_16x9.mp4 &
wait

mux() { ffmpeg -y -loglevel error -i "$1" -i out/audio_norm.wav -c:v copy -c:a aac -b:a 192k -shortest "$2"; }
mux out/video_16x9.mp4 out/master_16x9.mp4
mux out/video_9x16.mp4 out/cut_9x16.mp4
mux out/video_1x1.mp4 out/cut_1x1.mp4
mux out/video_reduced_16x9.mp4 out/reduced_motion_16x9.mp4
rm -f out/video_*.mp4
