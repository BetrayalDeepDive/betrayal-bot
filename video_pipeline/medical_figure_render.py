"""
FIGURE register renderer for the clinical-case channel.

Renders a real published figure (fetched by pmc_data.download_figure) into a
1920x1080 video frame with the CC BY attribution burned in.

TWO DESIGN RULES THAT ARE NOT NEGOTIABLE
----------------------------------------
1. ASPECT RATIO IS PRESERVED, ALWAYS. Medical imaging is diagnostic: a
   stretched chest CT is a distorted anatomy, and distorting a figure while
   citing the paper it came from misrepresents the source. Figures are
   letterboxed onto a clinical backing panel, never scaled to fill.

2. ATTRIBUTION IS PART OF THE FRAME, not an optional overlay. CC BY reuse is
   conditional on credit, so the credit is composited into the same image as
   the figure -- it cannot be lost by a later ffmpeg stage, a crop, or a
   Shorts re-frame. medical_policy_gate.check_publish_package() independently
   verifies that on-screen credit was rendered.

The output is a still PNG. The pipeline turns it into a moving clip with the
same Ken Burns / depth-motion treatment used elsewhere, so a held FIGURE shot
is never a static image sitting on screen.
"""
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080

# Clinical palette -- deliberately not the dark-red documentary look of the
# previous Ch1 channel. Cool slate with a desaturated teal accent reads as
# clinical/reference rather than true-crime dramatic.
BG = (14, 18, 22)
PANEL = (24, 31, 37)
PANEL_EDGE = (52, 66, 76)
ACCENT = (95, 168, 160)
TEXT = (232, 238, 240)
TEXT_DIM = (144, 163, 170)

_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def _font(size, bold=True):
    for path in (_FONT_CANDIDATES if bold else reversed(_FONT_CANDIDATES)):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _fit_preserving_aspect(img, box_w, box_h):
    """
    Largest size fitting inside the box with aspect ratio intact. Never
    upscales beyond 2x -- a small thumbnail-resolution figure blown up to
    full frame looks like a mistake and reads as low effort.
    """
    scale = min(box_w / img.width, box_h / img.height)
    scale = min(scale, 2.0)
    return img.resize((max(1, int(img.width * scale)),
                       max(1, int(img.height * scale))), Image.LANCZOS)


def _wrap(draw, text, font, max_width):
    """Greedy wrap by measured pixel width (font metrics, not char count)."""
    words = (text or "").split()
    if not words:
        return []
    lines, cur = [], words[0]
    for word in words[1:]:
        trial = f"{cur} {word}"
        if draw.textlength(trial, font=font) <= max_width:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    lines.append(cur)
    return lines


def render_figure_frame(figure_path, out_path, caption="", label="",
                        citation="", niche_label="NO KNOWN CAUSE"):
    """
    Compose one FIGURE frame.

    figure_path -- the real downloaded figure (any size/aspect)
    caption     -- the paper's own figure caption
    label       -- e.g. "Figure 2"
    citation    -- build_citation() output; rendered as the CC BY credit
    Returns True on success; False lets the caller fall back to ANATOMY.
    """
    try:
        fig = Image.open(figure_path).convert("RGB")
    except Exception:
        return False

    canvas = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(canvas)

    f_eyebrow = _font(24)
    f_label = _font(34)
    f_caption = _font(30, bold=False)
    f_credit = _font(21, bold=False)

    margin = 70
    # Reserve vertical space: eyebrow strip on top, caption + credit below.
    top_reserved = margin + 46
    bottom_reserved = 210
    box_w = W - margin * 2
    box_h = H - top_reserved - bottom_reserved

    fitted = _fit_preserving_aspect(fig, box_w, box_h)

    # Backing panel sized to the fitted figure, so a portrait X-ray gets a
    # portrait panel rather than floating in a wide empty band.
    pad = 18
    panel_box = [
        (W - fitted.width) // 2 - pad,
        top_reserved + (box_h - fitted.height) // 2 - pad,
        (W + fitted.width) // 2 + pad,
        top_reserved + (box_h + fitted.height) // 2 + pad,
    ]
    draw.rectangle(panel_box, fill=PANEL, outline=PANEL_EDGE, width=2)
    canvas.paste(fitted, ((W - fitted.width) // 2,
                          top_reserved + (box_h - fitted.height) // 2))

    # Eyebrow: channel register marker + the paper's own figure label.
    draw.line([(margin, margin + 6), (margin + 54, margin + 6)],
              fill=ACCENT, width=3)
    draw.text((margin + 68, margin - 8), niche_label, font=f_eyebrow, fill=ACCENT)
    if label:
        lw = draw.textlength(label.upper(), font=f_label)
        draw.text((W - margin - lw, margin - 14), label.upper(),
                  font=f_label, fill=TEXT_DIM)

    # Caption -- the paper's own words, max three lines so a very long
    # caption truncates rather than colliding with the credit line.
    y = H - bottom_reserved + 22
    if caption:
        lines = _wrap(draw, caption, f_caption, W - margin * 2)
        for line in lines[:3]:
            draw.text((margin, y), line, font=f_caption, fill=TEXT)
            y += 38
        if len(lines) > 3:
            draw.text((margin, y), "…", font=f_caption, fill=TEXT_DIM)
            y += 38

    # Credit -- the CC BY condition. Rendered last, always, at a fixed
    # distance from the bottom edge so it cannot be pushed off-frame by a
    # long caption above it.
    if citation:
        draw.line([(margin, H - 74), (W - margin, H - 74)],
                  fill=PANEL_EDGE, width=1)
        credit_lines = _wrap(draw, citation, f_credit, W - margin * 2)
        cy = H - 62
        for line in credit_lines[:2]:
            draw.text((margin, cy), line, font=f_credit, fill=TEXT_DIM)
            cy += 26

    canvas.save(out_path)
    return Path(out_path).exists()


def render_timeline_frame(events, out_path, title="CLINICAL COURSE",
                          niche_label="NO KNOWN CAUSE"):
    """
    TIMELINE register: the case's real chronology.

    events -- ordered list of (day_label, description) from the source paper.
    Rendered as a vertical spine so long descriptions stay readable, rather
    than a horizontal axis that forces text to tiny sizes.
    """
    canvas = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(canvas)
    f_eyebrow, f_title = _font(24), _font(46)
    f_day, f_desc = _font(30), _font(28, bold=False)

    margin = 90
    draw.line([(margin, 82), (margin + 54, 82)], fill=ACCENT, width=3)
    draw.text((margin + 68, 68), niche_label, font=f_eyebrow, fill=ACCENT)
    draw.text((margin, 118), title, font=f_title, fill=TEXT)

    shown = events[:6]
    if not shown:
        return False
    top, bottom = 230, H - 120
    spine_x = margin + 26
    draw.line([(spine_x, top), (spine_x, bottom)], fill=PANEL_EDGE, width=3)
    step = (bottom - top) / max(1, len(shown) - 1) if len(shown) > 1 else 0

    for i, (day, desc) in enumerate(shown):
        y = int(top + step * i)
        draw.ellipse([spine_x - 11, y - 11, spine_x + 11, y + 11],
                     fill=ACCENT, outline=BG, width=3)
        draw.text((spine_x + 42, y - 34), str(day).upper(), font=f_day, fill=ACCENT)
        for j, line in enumerate(_wrap(draw, desc, f_desc, W - spine_x - 160)[:2]):
            draw.text((spine_x + 42, y + 2 + j * 34), line, font=f_desc, fill=TEXT)

    canvas.save(out_path)
    return Path(out_path).exists()
