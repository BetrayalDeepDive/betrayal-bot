#!/usr/bin/env python3
"""
Generate the YouTube Studio branding assets for No Known Cause (Ch1).

WHY THIS IS A SCRIPT AND NOT A ONE-OFF IMAGE
--------------------------------------------
Branding gets revised -- a tagline changes, the safe area gets clipped on a
TV, a colour reads badly in dark mode. Regenerating from source beats
editing a PNG nobody can reproduce. It also keeps the channel art locked to
the same palette constants the video renderer uses
(medical_figure_render.BG / ACCENT), so the banner, the profile picture and
the first frame of every episode are provably the same colours rather than
three near-misses.

OUTPUTS
  banner_2048x1152.png   channel art (YouTube's required upload size)
  profile_800x800.png    channel avatar
  _safe_area_check.png   the banner with YouTube's crop regions drawn on top.
                         Diagnostic only -- never upload this one.

SAFE AREA, WHICH IS THE ONLY HARD CONSTRAINT HERE
-------------------------------------------------
YouTube crops channel art differently per device. Only the central
1235x338 region is guaranteed visible everywhere; TVs show all 2048x1152.
Anything that must be read -- the name, the tagline -- goes inside 1235x338.
Everything outside it is atmosphere that is allowed to be cropped away.

Free-tier: Pillow only, no external services, no fonts beyond DejaVu (present
on every GitHub Actions runner and on this sandbox).

Usage:  python3 tools/build_channel_branding.py [output_dir]
"""
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# Palette shared with video_pipeline/medical_figure_render.py. Kept as
# literals rather than an import so this script runs standalone, but they
# must stay identical -- see the module docstring.
BG = (14, 18, 22)
PANEL = (24, 31, 37)
EDGE = (52, 66, 76)
ACCENT = (95, 168, 160)
TEXT = (232, 238, 240)
TEXT_DIM = (144, 163, 170)

W, H = 2048, 1152
SAFE_W, SAFE_H = 1235, 338

CHANNEL_NAME = "NO KNOWN CAUSE"
TAGLINE = "Real published medical cases, one at a time."

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def _font(size, bold=True):
    try:
        return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)
    except Exception:
        return ImageFont.load_default()


def _ecg_points(width, height, baseline, amplitude, cycles):
    """
    A repeating ECG-like trace. Deliberately stylised rather than a real
    rhythm strip: this is channel art, and drawing something that reads as
    a genuine diagnostic tracing on a channel that explicitly gives no
    medical advice invites exactly the wrong inference.
    """
    pts = []
    span = width / cycles
    for x in range(width):
        t = (x % span) / span
        if t < 0.42 or t > 0.78:
            y = 0.0
        elif t < 0.46:            # Q
            y = -0.18
        elif t < 0.50:            # R rise
            y = (t - 0.46) / 0.04
        elif t < 0.55:            # R fall
            y = 1.0 - (t - 0.50) / 0.05
        elif t < 0.60:            # S
            y = -0.34 * (1 - (t - 0.55) / 0.05)
        else:                     # T
            y = 0.24 * math.sin((t - 0.60) / 0.18 * math.pi)
        pts.append((x, baseline - y * amplitude))
    return pts


def build_banner(out_path):
    canvas = Image.new("RGB", (W, H), BG)

    # ── atmosphere layer, drawn on its own image then blended ──────────
    # Drawing directly onto the canvas and then painting a vignette over it
    # leaves visible stroke residue wherever the vignette is partly
    # transparent. Compositing through a mask avoids that entirely.
    layer = Image.new("RGB", (W, H), BG)
    ld = ImageDraw.Draw(layer)

    for gx in range(0, W, 64):
        ld.line([(gx, 0), (gx, H)], fill=PANEL, width=1)
    for gy in range(0, H, 64):
        ld.line([(0, gy), (W, gy)], fill=PANEL, width=1)

    ld.line(_ecg_points(W, H, baseline=int(H * 0.30), amplitude=150, cycles=7),
            fill=EDGE, width=3, joint="curve")
    ld.line(_ecg_points(W, H, baseline=int(H * 0.78), amplitude=110, cycles=5),
            fill=EDGE, width=2, joint="curve")

    # Radial falloff: full strength at the edges, nothing in the middle, so
    # the atmosphere never competes with the name.
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    cx, cy = W // 2, H // 2
    steps = 60
    for i in range(steps):
        f = i / steps
        r = int(140 + f * (W * 0.62 - 140))
        md.ellipse([cx - r * 1.0, cy - r * 0.62, cx + r * 1.0, cy + r * 0.62],
                   outline=int(255 * (f ** 1.6)), width=int(W * 0.62 / steps) + 2)
    mask = mask.filter(ImageFilter.GaussianBlur(38))
    canvas = Image.composite(layer, canvas, mask)

    d = ImageDraw.Draw(canvas)

    # ── everything below is inside the 1235x338 all-device safe area ───
    sx0, sy0 = (W - SAFE_W) // 2, (H - SAFE_H) // 2

    # 96, not 112. At 112 "NO KNOWN CAUSE" spans ~1170 of the 1235 safe-area
    # width, leaving ~30px each side -- it reads as text that only just fit
    # rather than text that was placed. 96 leaves a real margin.
    f_name = _font(96)
    f_tag = _font(34, bold=False)
    f_meta = _font(27)

    name_w = d.textlength(CHANNEL_NAME, font=f_name)
    name_x = sx0 + (SAFE_W - name_w) // 2
    name_y = sy0 + 74

    # Accent rule above the name, sized to the name so it scales with it.
    rule_w = int(name_w * 0.30)
    d.line([(sx0 + (SAFE_W - rule_w) // 2, name_y - 30),
            (sx0 + (SAFE_W + rule_w) // 2, name_y - 30)], fill=ACCENT, width=4)

    d.text((name_x, name_y), CHANNEL_NAME, font=f_name, fill=TEXT)

    tag_w = d.textlength(TAGLINE, font=f_tag)
    d.text((sx0 + (SAFE_W - tag_w) // 2, name_y + 138), TAGLINE,
           font=f_tag, fill=TEXT_DIM)

    meta = "NEW CASE EVERY WEEKDAY"
    meta_w = d.textlength(meta, font=f_meta)
    mx = sx0 + (SAFE_W - meta_w) // 2
    my = name_y + 196
    d.line([(mx - 58, my + 14), (mx - 22, my + 14)], fill=ACCENT, width=3)
    d.line([(mx + meta_w + 22, my + 14), (mx + meta_w + 58, my + 14)],
           fill=ACCENT, width=3)
    d.text((mx, my), meta, font=f_meta, fill=ACCENT)

    canvas.save(out_path)
    return canvas


def build_safe_area_check(banner, out_path):
    """The banner with YouTube's three crop regions overlaid. Diagnostic."""
    img = banner.copy()
    d = ImageDraw.Draw(img)
    regions = [
        (1235, 338, (240, 90, 90), "ALL DEVICES (must contain everything readable)"),
        (1546, 423, (230, 180, 70), "tablet"),
        (2048, 1152, (110, 200, 190), "desktop / TV"),
    ]
    for rw, rh, col, label in regions:
        x0, y0 = (W - rw) // 2, (H - rh) // 2
        d.rectangle([x0, y0, x0 + rw, y0 + rh], outline=col, width=4)
        d.text((x0 + 12, y0 + 10), label, font=_font(24), fill=col)
    img.save(out_path)


def build_profile(out_path):
    """
    800x800, but YouTube renders it as a small circle -- often under 48px in
    a comment thread. So this is a monogram and one ECG beat, nothing more:
    anything with detail turns to mush at that size.
    """
    S = 800
    img = Image.new("RGB", (S, S), BG)
    d = ImageDraw.Draw(img)

    # Single ring, and inset far enough to survive YouTube's circular crop.
    # The first version had two concentric rings 22px apart, which at 48px in
    # a comment thread merge into one thick fuzzy band that reads as a
    # rendering error rather than a design.
    d.ellipse([54, 54, S - 54, S - 54], outline=ACCENT, width=8)

    # The trace is the whole mark -- no letter. A lone "N" identifies nothing
    # (every channel starting with N looks the same at this size), and the
    # channel name is always rendered beside the avatar anyway, so the icon's
    # job is to be recognisable, not to spell anything. A flat line with one
    # beat is unmistakably medical at any size and survives the crop.
    span = 470
    pts = _ecg_points(span, S, baseline=S // 2, amplitude=150, cycles=1)
    d.line([(x + (S - span) / 2, y) for x, y in pts],
           fill=TEXT, width=17, joint="curve")

    img.save(out_path)


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "branding")
    out.mkdir(parents=True, exist_ok=True)

    banner = build_banner(out / "banner_2048x1152.png")
    build_safe_area_check(banner, out / "_safe_area_check.png")
    build_profile(out / "profile_800x800.png")

    for p in sorted(out.iterdir()):
        print(f"  {p.name:26} {p.stat().st_size // 1024:5} KB")
    print("\nUpload banner_2048x1152.png and profile_800x800.png.")
    print("_safe_area_check.png is a diagnostic overlay — do NOT upload it.")


if __name__ == "__main__":
    main()
