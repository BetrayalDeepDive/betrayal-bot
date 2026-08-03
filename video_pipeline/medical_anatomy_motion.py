"""
Anatomy that moves.

WHAT IT REPLACED
----------------
ANATOMY was one static Wikimedia diagram held on screen for the length of a
card. At 18% of the episode -- the second-largest register -- that is roughly
three minutes of a still picture with a slow zoom on it. Scored honestly it
was the weakest thing in the whole pipeline.

The register exists to answer "what was physically happening inside this
patient", and that question is about CHANGE: something spread, something was
blocked, something drained, something recovered. A still cannot show change.
So this renders a real frame sequence and encodes it.

THE FOUR MOTIONS
----------------
    SPREAD   the affected area grows outward from a focus. Infection,
             oedema, infiltration, metastasis.
    FLOW     particles travel along a route and then stop at a blockage.
             Circulation, drug distribution, obstruction.
    ONSET    the finding appears and intensifies in place. Deposition,
             degeneration, accumulation.
    RESOLVE  the affected area shrinks back toward normal. Treatment
             response, recovery.

Which one is used is decided by what the segment actually says, not by
rotation, because the wrong motion is worse than a still: showing recovery
over narration about deterioration is a factual error made in pictures.

WHY DRAWN AND NOT FETCHED
-------------------------
Same reason as the thumbnails. A fetched image is whatever a search returned;
these are deterministic, need no network, cannot fail mid-render, and cannot
produce anything mistakable for a photograph of a real patient. The body
shapes are the ones in clinical_anatomy, so an episode's anatomy card and its
thumbnail show the same body.
"""
import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

import clinical_anatomy as ca
import medical_figure_render as mfr

W, H = 1920, 1080
FPS = 12          # a diagram does not need 24; halving the frames halves the
                  # render cost on a job that already fights a 6-hour ceiling
BG = mfr.BG
PANEL = mfr.PANEL
EDGE = mfr.PANEL_EDGE
ACCENT = mfr.ACCENT
TEXT = mfr.TEXT
DIM = mfr.TEXT_DIM
ALERT = (206, 92, 80)

MOTIONS = ("spread", "flow", "onset", "resolve")

_CUES = {
    "resolve": ("resolved", "recovery", "recovered", "improved", "improving",
                "responded", "reversal", "reversed", "discharged", "returned to",
                "treatment", "treated", "corrected", "normalised", "normalized"),
    "flow":    ("blood", "circulation", "vessel", "artery", "vein", "flow",
                "perfusion", "blocked", "blockage", "occlusion", "clot",
                "embolus", "thrombus", "delivered", "distributed", "crossed"),
    "spread":  ("spread", "spreading", "progressed", "progressive", "extended",
                "infiltrat", "metasta", "swelling", "oedema", "edema",
                "inflammation", "infection", "sepsis", "worsened", "advanced"),
    "onset":   ("developed", "appeared", "onset", "began", "deposit",
                "accumulat", "build-up", "buildup", "degener", "damage",
                "lesion", "mass", "growth"),
}


def motion_for(text):
    """Pick the motion from what the narration says.

    Resolution is checked first: "the swelling spread, then resolved with
    treatment" is a recovery beat, and matching "spread" there would animate
    the opposite of what is being said.
    """
    low = (text or "").lower()
    for name in ("resolve", "flow", "spread", "onset"):
        if any(c in low for c in _CUES[name]):
            return name
    return "onset"


def _frame(shape, motion, t, colour, label, sub, citation, accent):
    """One frame at normalised time t in 0..1."""
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    for x in range(0, W, 60):
        d.line([(x, 0), (x, H)], fill=(20, 26, 31), width=1)
    for y in range(0, H, 60):
        d.line([(0, y), (W, y)], fill=(20, 26, 31), width=1)

    box = (700, 60, 1560, 900)
    fitted = ca.fit_box(shape, box)
    ca.draw_shape(d, shape, box, (46, 58, 68))
    rb = ca.region_box(shape, box)
    cx, cy = (rb[0] + rb[2]) / 2, (rb[1] + rb[3]) / 2
    base_r = max(rb[2] - rb[0], rb[3] - rb[1]) * 0.5

    # The affected area, clipped to the silhouette so it never spills into
    # the background as a floating blob.
    body = Image.new("L", (W, H), 0)
    ca.draw_shape(ImageDraw.Draw(body), shape, box, 255, detail=False)

    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)

    if motion == "spread":
        r = base_r * (0.18 + 1.15 * t)
        ld.ellipse([cx - r, cy - r, cx + r, cy + r], fill=colour + (215,))
    elif motion == "resolve":
        r = base_r * (1.33 - 1.15 * t)
        ld.ellipse([cx - r, cy - r, cx + r, cy + r], fill=colour + (215,))
    elif motion == "onset":
        r = base_r * 0.95
        ld.ellipse([cx - r, cy - r, cx + r, cy + r],
                   fill=colour + (int(40 + 175 * t),))
    else:  # flow
        r = base_r * 0.5
        ld.ellipse([cx - r, cy - r, cx + r, cy + r], fill=colour + (110,))

    reg = lay.split()[3].filter(ImageFilter.GaussianBlur(radius=26))
    from PIL import ImageChops
    lay.putalpha(ImageChops.multiply(reg, body))
    img.paste(lay, (0, 0), lay)
    d = ImageDraw.Draw(img)

    if motion == "flow":
        # Particles running down a route, halting at a blockage two thirds
        # along -- the reason the case exists, shown rather than captioned.
        x0, y0 = fitted[0] + (fitted[2] - fitted[0]) * 0.5, fitted[1] + 40
        x1, y1 = cx, cy
        stop = 0.66
        for k in range(9):
            p = ((t * 1.7) + k / 9.0) % 1.0
            p = min(p, stop)
            px_, py_ = x0 + (x1 - x0) * p, y0 + (y1 - y0) * p
            rr = 9 if p < stop else 12
            d.ellipse([px_ - rr, py_ - rr, px_ + rr, py_ + rr],
                      fill=colour if p < stop else ALERT)
        bx, by = x0 + (x1 - x0) * stop, y0 + (y1 - y0) * stop
        d.line([(bx - 34, by - 34), (bx + 34, by + 34)], fill=ALERT, width=9)
        d.line([(bx - 34, by + 34), (bx + 34, by - 34)], fill=ALERT, width=9)

    # A marker ring that breathes, so even a held beat is never a frozen frame.
    ring = base_r * (1.18 + 0.05 * math.sin(t * math.pi * 2))
    d.ellipse([cx - ring, cy - ring, cx + ring, cy + ring],
              outline=accent, width=5)

    d.rectangle([110, 96, 640, 188], fill=PANEL, outline=EDGE, width=2)
    d.rectangle([110, 96, 122, 188], fill=accent)
    d.text((150, 118), label[:26], font=mfr._font(34, True), fill=accent)
    if sub:
        d.text((110, 214), sub[:64], font=mfr._font(28, False), fill=TEXT)

    # Progress bar: the card is visibly going somewhere.
    d.rectangle([110, mfr.CONTENT_BOTTOM - 26, 640, mfr.CONTENT_BOTTOM - 16],
                fill=(38, 48, 56))
    d.rectangle([110, mfr.CONTENT_BOTTOM - 26,
                 110 + int(530 * t), mfr.CONTENT_BOTTOM - 16], fill=accent)
    if citation:
        d.text((110, H - 58), citation[:150], font=mfr._font(21, False), fill=DIM)
    return img


def render_anatomy_motion(case, segment_text, out_path, duration, work_dir,
                          niche_name="", accent=None, run_ffmpeg=None,
                          label="WHAT WAS HAPPENING"):
    """Render the animated anatomy card. Returns True on success."""
    accent = tuple(accent) if accent else ACCENT
    shape = ca.shape_for(niche_name, f"{case.get('narrative','')} {segment_text}")
    colour = ca.anomaly_colour(f"{case.get('narrative','')} {segment_text}",
                               default=ALERT)
    motion = motion_for(segment_text)

    frames = max(8, int(duration * FPS))
    work = Path(work_dir) / f"anim_{abs(hash((shape, motion, frames))) % 99999}"
    work.mkdir(parents=True, exist_ok=True)
    sub = " ".join((segment_text or "").split()[:9])
    cit = mfr.short_credit(case.get("citation", "")) if hasattr(mfr, "short_credit") else ""
    for i in range(frames):
        t = i / max(1, frames - 1)
        _frame(shape, motion, t, colour, label, sub, cit, accent).save(
            work / f"f_{i:05d}.png")

    cmd = ["ffmpeg", "-y", "-framerate", str(FPS), "-i", str(work / "f_%05d.png"),
           "-t", f"{duration:.2f}", "-r", "24",
           "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
           "-an", str(out_path)]
    if run_ffmpeg:
        run_ffmpeg(cmd, label="anatomy-motion")
    else:
        subprocess.run(cmd, capture_output=True, timeout=300)
    for f in work.glob("f_*.png"):
        f.unlink()
    try:
        work.rmdir()
    except OSError:
        pass
    return Path(out_path).exists() and Path(out_path).stat().st_size > 1000
