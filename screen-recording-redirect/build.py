#!/usr/bin/env python3
"""
Builds output/amazon-review-redirect.mp4 from input/screen-recording.mp4 and
input/review-page.png.  Implements the timeline in MASTER_PROMPT.md.

Frames 0..196 are the recording itself (its last frame held).  Every later
frame is composed from pixels of the recording and the screenshot only:
  * status bar (clock 9:42, icons, red recording chip) = recording's last frame,
    with the chip's timer rebuilt each second from the recording's own digits;
  * Chrome toolbar = recording's last frame, with the review URL pasted from
    the screenshot once the navigation commits;
  * blue page-load bar = the bar rows copied from the first page load in the
    recording, at the same steps and timings;
  * page content = Order Details (recording) until the new page paints, then
    the review page (screenshot).
All coordinates are in 1080x2352 pixels and were measured from the recording.
"""
import os, subprocess, sys
import numpy as np
from PIL import Image

os.chdir(os.path.dirname(os.path.abspath(__file__)))
REC, IMG, OUT = "input/screen-recording.mp4", "input/review-page.png", "output/amazon-review-redirect.mp4"
DEBUG_DIR = sys.argv[sys.argv.index("--debug") + 1] if "--debug" in sys.argv else None

W, H, FPS = 1080, 2352, 30
DURATION = 11.4
N_FRAMES = round(DURATION * FPS)                 # 342

# ---- page-load sequence, measured from the first load in the recording -----
LAST = 189                                       # last recorded frame (6.094 s): stub + "00:06"
TAP = 5.524                                      # blue stub appears = tap on "Write a product review"
T0 = TAP + 1.276                                 # URL text changes, bar jumps to 223 px   (6.800 s)
BAR_STEPS = [(T0 + 0.000, 39),                   # (time, recording frame whose bar rows are copied)
             (T0 + 0.166, 41),                   #   frame 39: 223 px, 41: 532 px, 45: 587 px, 47: 773 px
             (T0 + 0.266, 45),
             (T0 + 0.378, 47)]
PAGE_SWITCH = T0 + 0.199                         # new page paints                           (6.999 s)
BAR_END = T0 + 0.466                             # bar gone                                  (7.266 s)
BAR_Y0, BAR_Y1 = 255, 263                        # rows holding the bar and its soft edges
BAR_MARGIN = 3                                   # columns copied past the bar's end cap

# ---- recording-chip timer ---------------------------------------------------
TICK = {7: 6.546, 8: 7.545, 9: 8.544, 10: 9.543, 11: 10.542}   # value -> time it appears (period 0.999 s)
SEG_A_FRAMES = int(TICK[7] * FPS) + 1            # 197: frames 0..196 straight from the recording

# ---- status bar / chip geometry --------------------------------------------
PILL_Y0, PILL_Y1 = 36, 104                       # rows of the chip block that gets rebuilt
KEEP_X = 262                                     # columns left of this (icon, "00:") are untouched
R0 = 327                                         # chip's right edge in the recording ("00:06")
CAP_W = 30                                       # width of the rounded end cap block
BG_X = 345                                       # a column of plain status-bar background
SOLID_X = 206                                    # a column of plain chip red (between icon and digits)
RIGHT_EDGE = {7: 323, 8: 325, 9: 327, 10: 314, 11: 303}   # chip right edge per timer value
TENS_X = {"0": 264, "1": 263}                    # ink-left of the tens digit
UNITS_X = {"0": 286, "1": 285, "7": 287, "8": 286, "9": 286}
UNITS_SHIFT = {"0": 0, "1": 11}                  # units digit moves left when the tens digit is "1"
GLYPH_Y0, GLYPH_Y1 = 52, 90                      # rows cropped around every digit

# ---- Chrome toolbar URL pill -------------------------------------------------
URL_X0, URL_X1, URL_Y0, URL_Y1 = 118, 723, 145, 233   # interior of the URL pill (3 px inside its edge)
URL_FLAT = (slice(148, 158), slice(400, 700))         # flat grey used to match the two sources' levels


def run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True).stdout


def rec_frame(n):
    """Recording frame n as RGB, decoded with the stream's BT.709 tags."""
    raw = run(["ffmpeg", "-v", "error", "-i", REC, "-vf", f"select='eq(n,{n})'", "-fps_mode", "passthrough",
               "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])
    return np.frombuffer(raw, np.uint8).reshape(H, W, 3).copy()


def alpha_of(src, x0, x1, bg, white, y0=GLYPH_Y0, y1=GLYPH_Y1):
    """Coverage of white text over a flat background, by least-squares projection."""
    p = src[y0:y1, x0:x1].astype(float) - bg
    d = white - bg
    return np.clip((p * d).sum(axis=2) / (d * d).sum(), 0, 1)


def draw(dst, a, x, y, white):
    h, w = a.shape
    reg = dst[y:y + h, x:x + w].astype(float)
    dst[y:y + h, x:x + w] = (reg * (1 - a[..., None]) + white * a[..., None]).round().clip(0, 255).astype(np.uint8)


def bar_extent(f):
    reg = f[256:261].astype(int)
    m = (reg[..., 2] > 140) & (reg[..., 2] > reg[..., 0] + 50)
    return int(np.nonzero(m.any(axis=0))[0].max())


def main():
    os.makedirs("output", exist_ok=True)
    last = rec_frame(LAST)
    f0, f6 = rec_frame(0), rec_frame(6)                       # chip shows "00:00" / "00:01"
    bars = {n: rec_frame(n) for _, n in BAR_STEPS}
    shot = np.asarray(Image.open(IMG).convert("RGB").resize((W, H), Image.LANCZOS)).copy()

    # ---- colours measured from the sources ---------------------------------
    red = np.median(last[55:85, 198:210].reshape(-1, 3), axis=0)
    black = np.median(last[55:85, 1040:1075].reshape(-1, 3), axis=0)
    shot_black = np.median(shot[55:85, 1040:1075].reshape(-1, 3), axis=0)
    def white_of(src, y0, y1, x0, x1):      # brightness reached only by fully covered text pixels
        return np.full(3, np.percentile(src[y0:y1, x0:x1].min(axis=2), 99.8))
    white_chip = white_of(last, 55, 85, 205, 310)
    white_bar = white_of(last, 55, 85, 65, 140)
    white_shot = white_of(shot, 55, 85, 940, 1010)

    # ---- digit glyphs: (alpha, ink-left offset inside the crop, row shift) --
    g = {}
    g["0"] = (alpha_of(last, 262, 285, red, white_chip), 2, 0)           # tens "0" of "00:06"
    a1 = alpha_of(f6, 284, 297, red, white_chip)                          # units "1" of "00:01"
    a1[:, 0] = np.clip(a1[:, 0] - alpha_of(f0, 306, 307, red, white_chip)[:, 0], 0, 1)  # drop the neighbouring 0's edge
    g["1"] = (a1, 1, 0)
    g["7"] = (alpha_of(last, 942, 962, black, white_bar), 2, 1)          # first "7" of the battery "77%"
    g["8"] = (alpha_of(shot, 962, 982, shot_black, white_shot), 2, 1)    # "8" of the screenshot's "78%"
    g["9"] = (alpha_of(last, 69, 90, black, white_bar), 2, 1)            # "9" of the clock "9:42"

    cap = last[PILL_Y0:PILL_Y1, R0 - CAP_W:R0 + 7].copy()        # end cap of the chip in the recording
    cap[GLYPH_Y0 - PILL_Y0:GLYPH_Y1 - PILL_Y0, :10] = last[GLYPH_Y0:GLYPH_Y1, SOLID_X][:, None, :]  # erase the old "6"'s tail

    def chip_block(value):
        tens, units = f"{value:02d}"
        R = RIGHT_EDGE[value]
        blk = last[PILL_Y0:PILL_Y1].copy()
        blk[:, KEEP_X:R - CAP_W] = last[PILL_Y0:PILL_Y1, SOLID_X][:, None, :]           # solid red
        blk[:, R - CAP_W:R + 7] = cap                                                   # rounded end cap
        blk[:, R + 7:360] = last[PILL_Y0:PILL_Y1, BG_X][:, None, :]                     # background
        for ch, x in ((tens, TENS_X[tens]), (units, UNITS_X[units] - UNITS_SHIFT[tens])):
            a, off, dy = g[ch]
            draw(blk, a, x - off, GLYPH_Y0 - PILL_Y0 + dy, white_chip)
        return blk[:, KEEP_X:360]
    chips = {v: chip_block(v) for v in TICK}

    # ---- toolbar with the review URL, page bases -----------------------------
    offset = np.median(last[URL_FLAT].reshape(-1, 3), axis=0) - np.median(shot[URL_FLAT].reshape(-1, 3), axis=0)
    url = (shot[URL_Y0:URL_Y1, URL_X0:URL_X1].astype(float) + offset).round().clip(0, 255).astype(np.uint8)
    loading = last.copy();  loading[URL_Y0:URL_Y1, URL_X0:URL_X1] = url      # Order Details + new URL
    review = loading.copy(); review[BAR_Y0:] = shot[BAR_Y0:]                # review page under the same chrome
    extents = {n: bar_extent(f) for n, f in bars.items()}

    if DEBUG_DIR:
        os.makedirs(DEBUG_DIR, exist_ok=True)
        print("red", red, "black", black, "shot_black", shot_black, "white_chip", white_chip, "white_bar", white_bar,
              "url offset", offset, "bar extents", extents)
        sheet = np.concatenate([last[PILL_Y0:PILL_Y1, 140:360]] + [np.concatenate([last[PILL_Y0:PILL_Y1, 140:KEEP_X], c], axis=1) for c in chips.values()], axis=0)
        Image.fromarray(sheet).resize((220 * 5, sheet.shape[0] * 5), Image.NEAREST).save(f"{DEBUG_DIR}/chips.png")
        Image.fromarray(review[:300]).save(f"{DEBUG_DIR}/review_top.png")

    # ---- encode: recording frames + composed frames, one H.264 stream -------
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-stats",
           "-i", REC,
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-framerate", str(FPS), "-i", "pipe:0",
           "-filter_complex",
           f"[0:v]fps={FPS},tpad=stop_mode=clone:stop_duration=3,trim=end_frame={SEG_A_FRAMES},setpts=PTS-STARTPTS,format=yuv420p,settb=AVTB[a];"
           f"[1:v]scale=out_color_matrix=bt709:out_range=tv,format=yuv420p,fps={FPS},setpts=PTS-STARTPTS,settb=AVTB[b];"
           f"[a][b]concat=n=2:v=1:a=0[v];"
           f"[0:a]apad,atrim=end={DURATION},asetpts=PTS-STARTPTS[aud]",
           "-map", "[v]", "-map", "[aud]",
           "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-profile:v", "high", "-level", "4.2",
           "-pix_fmt", "yuv420p", "-r", str(FPS),
           "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv",
           "-c:a", "aac", "-b:a", "96k", "-ar", "44100", "-ac", "1", "-movflags", "+faststart", OUT]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for k in range(SEG_A_FRAMES, N_FRAMES):
        t = k / FPS
        f = (last if t < T0 else loading if t < PAGE_SWITCH else review).copy()
        if T0 <= t < BAR_END:
            n = [n for ts, n in BAR_STEPS if t >= ts][-1]
            x1 = extents[n] + 1 + BAR_MARGIN
            f[BAR_Y0:BAR_Y1, :x1] = bars[n][BAR_Y0:BAR_Y1, :x1]
        value = max(v for v, ts in TICK.items() if t >= ts)
        f[PILL_Y0:PILL_Y1, KEEP_X:360] = chips[value]
        proc.stdin.write(f.tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit("ffmpeg failed")
    print(f"wrote {OUT}: {N_FRAMES} frames, {DURATION} s")


if __name__ == "__main__":
    main()
