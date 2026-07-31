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
import re
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080

# Burned-in captions occupy the bottom of every frame for essentially the
# whole episode. Nothing else may be drawn there -- and "there" has to
# account for the fact that every shot is ZOOMING.
#
# Found in two stages, both by looking at real output:
#
# 1. Burning the real ASS onto the real stills showed the caption box
#    landing on top of the ANATOMY explanation, the TIMELINE's last event,
#    the CHART's axis labels and the CC BY credit. Each renderer had been
#    designed in isolation and every one chose the bottom of the frame,
#    which in isolation is correct.
#
# 2. A 200px band fixed the STILLS and was still wrong in the VIDEO,
#    which is what a viewer sees. still_to_clip applies a zoompan, and a
#    zoom magnifies outward from the centre -- so content near the bottom
#    of the frame MOVES DOWN as the shot pushes in. Measured against the
#    real burned caption (ink starts at y=894 for the two-line case), a
#    FIGURE shot at its 1.14 ceiling carried content at y=880 down to
#    y=928: thirty-four pixels inside the caption. FIGURE, ANATOMY and TEXT
#    all did it, which is about half the episode.
#
# So the band is DERIVED, not chosen: from the measured caption top and the
# largest zoom any register uses.
CAPTION_INK_TOP = 894      # measured by burning a real two-line cue (libass)
CAPTION_CLEARANCE = 4      # do not let content touch the box edge
MAX_REGISTER_ZOOM = 1.14   # the largest 'max' in medical_segments.MOTION

# Solve 540 + (CONTENT_BOTTOM - 540) * MAX_REGISTER_ZOOM <= CAPTION_INK_TOP
CONTENT_BOTTOM = int(H / 2 + ((CAPTION_INK_TOP - CAPTION_CLEARANCE) - H / 2)
                     / MAX_REGISTER_ZOOM)
CAPTION_SAFE_H = H - CONTENT_BOTTOM

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


def _clip_words(text, limit):
    """
    Truncate on a WORD boundary.

    Every renderer here used to slice with [:70] / [:96], which on a real
    citation produced "...following a rare inherited d" -- a line that ends
    mid-word reads as a rendering bug to a viewer, not as an abbreviation.
    """
    t = (text or "").strip()
    if len(t) <= limit:
        return t
    cut = t[:limit].rsplit(" ", 1)[0].rstrip(" ,;:—-")
    return (cut or t[:limit]) + "…"


_ABBREV = ("dr", "mr", "mrs", "ms", "prof", "vs", "eg", "ie", "no", "st")


def _tidy_display_line(text, limit=240):
    """
    Make a narration slice presentable as on-screen text.

    The pipeline hands every renderer `stage_text`, which is
    `" ".join(words[start:end]).lower()` -- lowercased for keyword matching
    and cut on an arbitrary word index. Put straight on a card, that reads
    as "rare. newborns tire, newborns refuse, and tired mothers are told,
    gently and constantly, that this is normal. what was not". Lowercase
    sentence starts and both ends dangling mid-clause. It looks like a bug,
    because it is one.

    So: prefer whole sentences inside the slice, and restore sentence case.
    Words that were already capitalised in the source cannot be recovered
    once lowercased -- the real fix for that is upstream, passing the
    original-case text -- but this is correct either way and is the safety
    net if any caller still passes a lowercased slice.
    """
    t = " ".join((text or "").split())
    if not t:
        return ""
    # Whole sentences within the slice, if there are any.
    sentences = re.findall(r"[^.!?]+[.!?]", t)
    if sentences:
        picked, out = [], 0
        for s in sentences:
            s = s.strip()
            if out and out + len(s) + 1 > limit:
                break
            picked.append(s)
            out += len(s) + 1
        if picked:
            t = " ".join(picked)
        else:
            t = _clip_words(sentences[0], limit)
    else:
        t = _clip_words(t, limit)

    def _cap(m):
        return m.group(1) + m.group(2).upper()

    t = re.sub(r"(^|[.!?]\s+)([a-z])", _cap, t)
    # "i" as a standalone pronoun, and nothing else -- guessing at proper
    # nouns would corrupt clinical terms, which is worse than lowercase.
    t = re.sub(r"\bi\b", "I", t)
    return t


def short_credit(citation, max_len=88):
    """
    The on-screen form of a CC BY credit.

    The full citation is authors + full paper title + journal + year +
    licence, which is ~150 characters and unreadable at the size a credit
    line is drawn. The LICENCE only requires attribution, and the full
    citation is carried in the description (enforced by
    medical_policy_gate.check_publish_package). On screen, the identifying
    part -- authors, journal, year, licence -- is both sufficient and
    legible. The paper title is what gets dropped.
    """
    c = " ".join((citation or "").split())
    if not c:
        return ""
    # Split on sentence-ending periods only. A naive split(".") cuts "CC BY
    # 4.0" into "CC BY 4" and "0", which is a licence statement that no
    # longer names the licence version.
    parts = [p.strip(" .") for p in re.split(r"\.\s+", c) if p.strip(" .")]
    if len(parts) >= 3:
        # The paper TITLE is what makes a citation unreadable on screen, and
        # it is reliably the longest part. Everything else -- authors,
        # journal, year, licence -- is what identifies the source.
        title_i = max(range(1, len(parts)), key=lambda i: len(parts[i]))
        kept = [p for i, p in enumerate(parts) if i != title_i]
        rebuilt = ". ".join(kept)
        if len(rebuilt) <= max_len:
            return rebuilt
        return _clip_words(rebuilt, max_len)
    return _clip_words(c, max_len)


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
    f_credit = _font(25, bold=False)

    margin = 70
    # Reserve vertical space: eyebrow strip on top, caption + credit below.
    top_reserved = margin + 46
    bottom_reserved = 210 + CAPTION_SAFE_H
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
        draw.line([(margin, CONTENT_BOTTOM - 96), (W - margin, CONTENT_BOTTOM - 96)],
                  fill=PANEL_EDGE, width=1)
        credit_lines = _wrap(draw, short_credit(citation, 110), f_credit,
                             W - margin * 2)
        cy = CONTENT_BOTTOM - 66
        for line in credit_lines[:2]:
            draw.text((margin, cy), line, font=f_credit, fill=TEXT_DIM)
            cy += 26

    canvas.save(out_path)
    return Path(out_path).exists()


def condense_timeline(events, cap=6):
    """
    Reduce a long clinical course to `cap` rows that still SPAN it.

    Returns (rows, original_indices).

    A head-slice was the old behaviour and it removed the end of the story:
    on a fourteen-event course the frame stopped at day six, so the
    deterioration, the diagnosis and the outcome -- the reason the episode
    exists -- were never drawn. Sampling evenly and always keeping the first
    and last event means the spine still runs from admission to resolution.
    """
    ev = list(events or [])
    if len(ev) <= cap:
        return ev, list(range(len(ev)))
    idx, seen = [], set()
    for i in range(cap):
        k = int(round(i * (len(ev) - 1) / (cap - 1)))
        if k not in seen:
            seen.add(k)
            idx.append(k)
    return [ev[k] for k in idx], idx


def render_timeline_frame(events, out_path, title="CLINICAL COURSE",
                          niche_label="NO KNOWN CAUSE", reached=None):
    """
    TIMELINE register: the case's real chronology.

    events   -- ordered list of (day_label, description) from the source paper
    reached  -- how many events the narration has got to. Events past that
                point are still LAID OUT and drawn dim, never omitted.

    Rendered as a vertical spine so long descriptions stay readable, rather
    than a horizontal axis that forces text to tiny sizes.

    The caller used to implement its progressive reveal by SLICING the event
    list, which meant an early TIMELINE segment drew a single dot at the top
    of an otherwise empty 1080-line frame, and every event's position moved
    as more were added. Rendering a full episode locally and looking at the
    frames is what exposed it -- it logs as a clean success. The reveal is
    now a highlight over a fixed layout: the whole clinical course is always
    on screen, and the point the narration has reached is the lit one.
    """
    canvas = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(canvas)
    f_eyebrow, f_title = _font(24), _font(46)
    f_day, f_desc = _font(30), _font(28, bold=False)

    margin = 90
    draw.line([(margin, 82), (margin + 54, 82)], fill=ACCENT, width=3)
    draw.text((margin + 68, 68), niche_label, font=f_eyebrow, fill=ACCENT)
    draw.text((margin, 118), title, font=f_title, fill=TEXT)

    shown, kept = condense_timeline(events, 6)
    if not shown:
        return False
    n = len(shown)
    # `reached` counts events in the ORIGINAL list, so map it onto the rows
    # that survived condensation. Before this, a fourteen-event case laid out
    # only the first six and clamped reached to six, so every TIMELINE segment
    # in the back half of the episode drew the identical fully-lit frame --
    # and the frame it drew ended on day six, with the diagnosis and the
    # outcome nowhere on screen.
    live = n if reached is None else max(1, sum(1 for k in kept if k < int(reached)))

    # Same reserve rule as the vertical card: the bottom of the spine is the
    # last DOT, and that event's description is drawn below it (two lines of
    # 34px from y+2). Reserving 40 only fitted a one-line description.
    top, bottom = 230, CONTENT_BOTTOM - 96
    spine_x = margin + 26
    draw.line([(spine_x, top), (spine_x, bottom)], fill=PANEL_EDGE, width=3)
    step = (bottom - top) / max(1, n - 1) if n > 1 else 0
    # The spine fills in behind the narration, so the frame carries a real
    # sense of travel through the case rather than being a static list.
    if live > 1:
        draw.line([(spine_x, top), (spine_x, int(top + step * (live - 1)))],
                  fill=ACCENT, width=3)

    for i, (day, desc) in enumerate(shown):
        y = int(top + step * i)
        on = i < live
        current = i == live - 1
        r = 13 if current else 11
        draw.ellipse([spine_x - r, y - r, spine_x + r, y + r],
                     fill=ACCENT if on else BG,
                     outline=ACCENT if on else PANEL_EDGE, width=3)
        draw.text((spine_x + 42, y - 34), str(day).upper(), font=f_day,
                  fill=ACCENT if on else TEXT_DIM)
        if on:
            for j, line in enumerate(_wrap(draw, desc, f_desc,
                                           W - spine_x - 160)[:2]):
                draw.text((spine_x + 42, y + 2 + j * 34), line, font=f_desc,
                          fill=TEXT)
        else:
            # The DAY LABEL of a future event is drawn (it holds the layout
            # and shows how far the case still has to run); its DESCRIPTION
            # is not. Drawing it dim was still perfectly readable in the
            # rendered frames, which meant an early timeline segment showed
            # "Day 21 -- liver function normalised; discharged". The ending,
            # in the first minute.
            draw.line([(spine_x + 42, y + 16), (spine_x + 42 + 260, y + 16)],
                      fill=PANEL_EDGE, width=2)

    canvas.save(out_path)
    return Path(out_path).exists()
