#!/usr/bin/env bash
# Builds output/amazon-review-redirect.mp4 from the recording and the screenshot.
# Implements the timeline in MASTER_PROMPT.md.
set -euo pipefail
cd "$(dirname "$0")"

REC="input/screen-recording.mp4"
IMG="input/review-page.png"
OUT="output/amazon-review-redirect.mp4"

W=1080; H=2352; FPS=30
HOLD_END=6.90   # last recorded frame is held until this time (tap + page-load wait)
FADE=0.50       # dissolve length
IMG_HOLD=4.00   # review page held still after the dissolve

REC_LEN=$(python3 -c "print(round($HOLD_END + $FADE, 3))")              # first input length
IMG_LEN=$(python3 -c "print(round($FADE + $IMG_HOLD, 3))")              # second input length
TOTAL=$(python3 -c "print(round($HOLD_END + $FADE + $IMG_HOLD, 3))")    # output length

mkdir -p output
ffmpeg -y -hide_banner -loglevel error -stats \
  -i "$REC" \
  -loop 1 -framerate "$FPS" -t "$IMG_LEN" -i "$IMG" \
  -filter_complex "
    [0:v]fps=${FPS},format=yuv420p,tpad=stop_mode=clone:stop_duration=3,trim=end=${REC_LEN},setpts=PTS-STARTPTS,settb=AVTB[rec];
    [1:v]scale=${W}:${H}:flags=lanczos:out_color_matrix=bt709:out_range=tv,format=yuv420p,fps=${FPS},settb=AVTB[img];
    [rec][img]xfade=transition=fade:duration=${FADE}:offset=${HOLD_END}[v];
    [0:a]apad,atrim=end=${TOTAL},asetpts=PTS-STARTPTS[a]
  " \
  -map "[v]" -map "[a]" \
  -c:v libx264 -preset slow -crf 17 -profile:v high -level 4.2 -pix_fmt yuv420p -r "$FPS" \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv \
  -c:a aac -b:a 96k -ar 44100 -ac 1 \
  -movflags +faststart \
  "$OUT"

echo "wrote $OUT"
