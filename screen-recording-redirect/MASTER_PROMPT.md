# Master Prompt: screen recording + screenshot, joined as one redirect

## Goal

Append a phone screenshot to the end of a phone screen recording so the result
plays as one continuous screen recording. The recording ends on Amazon's
"Order Details" page right after the tap on "Write a product review": the blue
page-load stub under the URL bar is already visible in its last frames. The
output must continue that page load exactly the way the first page load in the
recording looks (URL text changes, blue bar grows in the same steps, new page
paints) and keep the status bar continuous: clock 9:42, the red recording chip
with its timer still counting, battery 77 %.

## Inputs

| File | What it is | Properties |
| --- | --- | --- |
| `input/screen-recording.mp4` | Android screen recording, "Your Orders" -> "Order Details" -> tap on "Write a product review" | 1080x2352, H.264 yuv420p, BT.709 limited range, variable ~29 fps, 6.55 s, silent AAC mono |
| `input/review-page.png` | Screenshot of `amazon.in/review/review-your-purchases...` | 1272x2772 RGBA, same aspect ratio as the recording (0.459) |

## Rules

1. Every frame of the recording is used unchanged, in order, at the recorded
   speed. Its last frame is held while the new page loads.
2. The screenshot is only resized (Lanczos) to the recording's frame size. Its
   aspect ratio matches, so nothing is cropped or stretched visibly.
3. Every pixel of the appended part comes from the two sources. Nothing is
   drawn, typed or overlaid from outside:
   - status bar and Chrome toolbar: the recording's last frame;
   - timer digits "0" and "1": the chip itself in the recording; "7" and "9":
     the recording's battery "77%" and clock "9:42"; "8": the screenshot's
     battery "78%" (same typeface and size as the chip);
   - review URL: the inside of the screenshot's URL pill, pasted into the
     recording's toolbar with its grey level matched;
   - blue bar: the bar rows of the recording's first page load, copied at the
     same widths;
   - page content: Order Details (recording) until the new page paints, then
     the review page (screenshot).
4. The output keeps the recording's format: 1080x2352, H.264 yuv420p, BT.709
   limited range, 30 fps constant, AAC mono 44.1 kHz, MP4 with faststart. The
   (silent) audio track is extended to the end so the file stays continuous.

## Timeline

Load timings are the ones measured on the first page load in the recording
(stub -> URL change 1.276 s; then +0.166, +0.199, +0.266, +0.378, +0.466 s).

| Time (s) | On screen |
| --- | --- |
| 0.000 - 6.094 | Recording as captured. The stub appears at 5.524 (the tap). |
| 6.094 - 6.800 | Last frame held: Order Details with the stub. Chip ticks to 00:07 at 6.546. |
| 6.800 | URL becomes `amazon.in/review/review-your...`, bar jumps to 223 px |
| 6.966 | bar 532 px |
| 6.999 | review page paints (bar stays) |
| 7.066 | bar 587 px |
| 7.178 | bar 773 px |
| 7.266 | bar gone, page loaded |
| 7.266 - 11.400 | Review page held. Chip: 00:08 at 7.545, 00:09 at 8.544, 00:10 at 9.543, 00:11 at 10.542 |

Total length: 11.40 s (342 frames).

## Measured facts the build relies on

- Bar: rows 256-260, light blue (167,198,253), soft edges on rows 255 and 261;
  stub 54 px wide; steps 223 / 532 / 587 / 773 px; gone 0.466 s after the URL
  change; the new page paints 0.199 s after it.
- Chip: left-anchored, its right edge follows the digits (proportional
  figures): "00:0x" ends at 323-327 px, "00:10" at 314, "00:11" at 303. Timer
  period 0.999 s (ticks at 1.552, 2.550, 3.548, 4.549, 5.547 in the recording).
- Clock and battery use the same typeface and size as the chip, in the
  fixed-width figure style (their "1" has a foot; the chip's has none).
- The toolbars of both sources align at zero pixel shift; the URL pill grey
  differs by (2,1,2) levels and is matched on paste.

## Build

```bash
bash build.sh              # python3 build.py; needs ffmpeg, numpy, Pillow
bash build.sh --debug DIR  # also writes chip and toolbar previews into DIR
```

## Verification

- `ffprobe`: 1080x2352, 30/1 fps, 11.40 s, 342 frames, h264 + aac.
- Frame-to-frame differences in the appended part are limited to the chip,
  the bar steps and the single page-paint frame.
- Chip previews (`--debug`) show 00:07 ... 00:11 with clean digits and the
  pill width changing as in the recording.
