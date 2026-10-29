# Master Prompt: screen recording + screenshot, joined as one redirect

## Goal

Append a phone screenshot to the end of a phone screen recording so the result
plays as one continuous screen recording. The recording ends on the Amazon
"Order Details" page. The output must look like the user tapped
"Write a product review", the URL redirected, and the review page (the
screenshot) painted in. Nothing in either source is cropped, re-laid-out,
redrawn or edited.

## Inputs

| File | What it is | Properties |
| --- | --- | --- |
| `input/screen-recording.mp4` | Android screen recording, "Your Orders" -> "Order Details" | 1080x2352, H.264 yuv420p, BT.709 limited range, variable ~29 fps, 6.55 s, silent AAC mono |
| `input/review-page.png` | Screenshot of `amazon.in/review/review-your-purchases...` | 1272x2772 RGBA, same aspect ratio as the recording (0.459) |

## Rules

1. Every frame of the recording is used unchanged, in order, at the recorded speed.
2. The screenshot is only resized (Lanczos) to the recording's frame size.
   Its aspect ratio matches, so nothing is cropped or stretched visibly.
3. No overlays, cursors, captions, ripples or added UI. The status bars are
   left exactly as captured in each source.
4. The output keeps the recording's format: 1080x2352, H.264 yuv420p, BT.709
   limited range, 30 fps constant, AAC mono 44.1 kHz, MP4 with faststart.
5. Audio stays continuous: the recording's (silent) track is extended with
   silence to the end of the clip.

## Timeline

| Time (s) | On screen | Why |
| --- | --- | --- |
| 0.00 - 6.09 | The recording, exactly as captured | Original content |
| 6.09 - 6.90 | Last recorded frame held (Order Details page) | Reads as the tap on "Write a product review" plus the page-load wait |
| 6.90 - 7.40 | 0.5 s dissolve from Order Details into the review page | The URL bar changes and the page repaints, like a real redirect |
| 7.40 - 11.40 | Review page held still | 4 s to read the page before the clip ends |

Total length: 11.40 s.

## Transition parameters (tunable in `build.sh`)

| Variable | Default | Meaning |
| --- | --- | --- |
| `HOLD_END` | 6.90 | Time at which the dissolve starts |
| `FADE` | 0.50 | Dissolve length |
| `IMG_HOLD` | 4.00 | How long the review page stays after the dissolve |

## Build

```bash
bash build.sh
# writes output/amazon-review-redirect.mp4
```

## Verification

- `ffprobe` on the output: 1080x2352, 30/1 fps, ~11.40 s, h264 + aac.
- Frames at 6.5 s (Order Details), 7.15 s (mid-dissolve) and 8.0 s (review
  page) show the expected content with no letterboxing or distortion.
