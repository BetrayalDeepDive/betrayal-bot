"""
Segment renderer dispatch for the clinical-case channel.

One entry point -- render_medical_segment() -- turns a register name plus the
episode's real sourced case into a finished video clip. Keeps the pipeline's
per-segment loop to a single call, and keeps every register's rendering
decision in one testable place.

Every register draws from the SAME source paper as the script. That is the
whole point: there is no register here whose content has to be invented or
substituted with generic filler, which is exactly what failed when this
channel used stock footage and character animation.

Registers:
  FIGURE    real CC BY figure from the paper + burned-in attribution
  CHART     real reported values, plotted
  BOARD     differential diagnosis, candidates struck out
  TIMELINE  real clinical course
  ANATOMY   anatomical/molecular diagram (Wikimedia, else procedural)
  TEXT      real quoted line from the paper's discussion

Every renderer returns True/False. False is always safe: the caller falls
through to its existing stock-footage path, so a failed register degrades to
a worse-looking segment rather than a broken render.
"""
import math
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import medical_figure_render as mfr
from medical_figure_render import _clip_words, _tidy_display_line, short_credit

W, H = 1920, 1080
BG = mfr.BG
PANEL = mfr.PANEL
EDGE = mfr.PANEL_EDGE
TEAL = mfr.ACCENT
TEXT_C = mfr.TEXT
DIM = mfr.TEXT_DIM
# Bottom band reserved for burned-in captions -- see medical_figure_render.
CONTENT_BOTTOM = mfr.CONTENT_BOTTOM
RED = (192, 85, 75)
AMBER = (195, 154, 69)


def _f(size, bold=True):
    return mfr._font(size, bold)


def _eyebrow(draw, label, y=82):
    draw.line([(90, y), (144, y)], fill=TEAL, width=3)
    draw.text((158, y - 14), label, font=_f(24), fill=TEAL)


# Per-register motion. One identical Ken Burns push on every shot for
# thirteen minutes is its own kind of monotony -- the eye stops reading it as
# motion and starts reading it as drift. A figure earns a slow push in; a
# chart or a board is a diagram and should be nearly still, because moving
# text is harder to read; a title card holds.
MOTION = {
    "FIGURE":   {"zoom": 0.00055, "max": 1.14},
    "ANATOMY":  {"zoom": 0.00035, "max": 1.09},
    "TEXT":     {"zoom": 0.00022, "max": 1.05},
    "CHART":    {"zoom": 0.00016, "max": 1.04},
    "BOARD":    {"zoom": 0.00016, "max": 1.04},
    "TIMELINE": {"zoom": 0.00016, "max": 1.04},
    "TITLE":    {"zoom": 0.00012, "max": 1.03},
    "CASEFILE": {"zoom": 0.00014, "max": 1.04},
    "LAB":      {"zoom": 0.00016, "max": 1.04},
    # SCENE is a full-bleed photograph: the whole frame is picture, so a big
    # push would crop the subject out of it and drag the caption toward the
    # burned-in subtitle band. A slow drift is all it needs.
    "SCENE":    {"zoom": 0.00018, "max": 1.05},
}


def still_to_clip(still_path, duration, out_path, run_ffmpeg=None, zoom=True,
                  register=None, transition="fade", index_hint=0,
                  last_move=None):
    """
    Turn a rendered still into a clip with continuous slow motion.

    A held 14-15s shot that is genuinely static reads as a slideshow -- the
    specific failure this channel already hit twice. The zoompan below keeps
    something moving inside every held frame.

    The rate is per register (MOTION): a diagram covered in small labels that
    is slowly scaling is measurably harder to read than one that is holding
    still, and the previous single rate was tuned for photographs.

    TRANSITION. This used to end in a hardcoded `fade=t=in:st=0:d=0.4` -- the
    same opening move on all ~60 cards of every episode. clinical_transitions
    supplies a different one per card now; some need a second input to slide
    across the frame, so the chain is built as a filter_complex rather than a
    plain -vf.
    """
    # CAMERA. Was one zoompan, the same slow push, on all ~60 cards. The eye
    # stops reading an unchanging move as motion within a couple of cards and
    # starts reading it as drift. clinical_camera picks a move suited to the
    # register -- a dense panel is panned because there is something to pan
    # across, a figure is pushed into because the interest is in one place --
    # and never repeats the same move back to back.
    try:
        import clinical_camera as ccam
        move = ccam.move_for(register, index_hint, last=last_move)
        base = ccam.filter_for(move, duration) if zoom else "scale=1920:1080"
    except Exception:
        move = "push_in"
        m = MOTION.get(register or "", {"zoom": 0.00045, "max": 1.12})
        base = ("scale=1920:1080"
                + (f",zoompan=z='min(zoom+{m['zoom']},{m['max']})':"
                   f"d={max(1, int(duration * 24))}:s=1920x1080:fps=24"
                   if zoom else ""))

    try:
        import clinical_transitions as ctr
        extra, frag = ctr.build(transition, w=1920, h=1080)
    except Exception:
        extra, frag = [], "[base]fade=t=in:st=0:d=0.40[vout]"

    cmd = (["ffmpeg", "-y", "-loop", "1", "-i", str(still_path)] + extra +
           ["-filter_complex", f"[0:v]{base}[base];{frag}",
            "-map", "[vout]", "-t", f"{duration:.2f}",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            "-an", str(out_path)])
    if run_ffmpeg:
        run_ffmpeg(cmd, label="medical-segment")
    else:
        subprocess.run(cmd, capture_output=True, timeout=180)
    still_to_clip.last_move = move
    return Path(out_path).exists() and Path(out_path).stat().st_size > 1000


# ── TITLE / ACT CARDS ──────────────────────────────────────────────────────
# The episode had no opening at all. Segment zero was whatever register the
# quota happened to schedule -- in a real local render, a half-drawn chart.
# A documentary opens by telling you what it is, and marks its acts; without
# that a 13-minute film of clinical graphics reads as a slide deck, which is
# the note this channel has already had once.
ACT_LABELS = ("THE PRESENTATION", "THE FIRST ANSWER",
              "THE REVERSAL", "WHAT IT CHANGED")


def act_boundaries(n_segments, acts=len(ACT_LABELS)):
    """
    Segment indices where an act card lands. Segment 0 is the title card, so
    acts start after it and are spaced across the remainder.
    """
    if n_segments < 12:
        return {}
    step = n_segments / float(acts)
    out = {}
    for k in range(acts):
        idx = int(round(k * step)) + (1 if k == 0 else 0)
        idx = max(1, min(n_segments - 1, idx))
        if idx not in out:
            out[idx] = ACT_LABELS[k]
    return out


def render_title_card(title, out_path, niche_label="NO KNOWN CAUSE",
                      source_line="", citation=""):
    """
    The opening frame. Deliberately typographic and still: the narration's
    own hook is carrying the first fifteen seconds, and a busy graphic would
    compete with it.
    """
    c = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(c)
    _eyebrow(d, niche_label, y=150)

    t = _tidy_display_line(title, 120) or "A PUBLISHED CASE"
    size = 96
    lines = mfr._wrap(d, t, _f(size), W - 320)
    while len(lines) > 3 and size > 52:
        size -= 8
        lines = mfr._wrap(d, t, _f(size), W - 320)
    f = _f(size)
    lh = size + 26
    y = max(240, (CONTENT_BOTTOM - len(lines) * lh) // 2 - 40)
    for ln in lines[:3]:
        d.text((160, y), ln, font=f, fill=TEXT_C)
        y += lh

    d.line([(160, y + 34), (520, y + 34)], fill=TEAL, width=4)
    if source_line:
        d.text((160, y + 64), _clip_words(source_line, 84), font=_f(30, False),
               fill=TEAL)
    cred = short_credit(citation)
    if cred:
        d.text((160, y + 112), cred, font=_f(24, False), fill=DIM)
    c.save(out_path)
    return Path(out_path).exists()


def render_act_card(index, label, out_path, niche_label="NO KNOWN CAUSE"):
    """A held act marker: large number, act name, single rule."""
    c = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(c)
    _eyebrow(d, niche_label, y=150)
    num = f"{index:02d}"
    fn = _f(200)
    cy = CONTENT_BOTTOM // 2
    # The number sits ABOVE the label, not behind it. Drawn as a ghost behind
    # the text it half-covered the first word and read as a rendering error.
    d.text((160, cy - 250), num, font=fn, fill=(38, 50, 58))
    d.line([(160, cy - 22), (420, cy - 22)], fill=TEAL, width=4)
    lab = _clip_words(label.upper(), 34)
    fl = _f(76)
    d.text((160, cy + 16), lab, font=fl, fill=TEXT_C)
    c.save(out_path)
    return Path(out_path).exists()


# ── CHART ──────────────────────────────────────────────────────────────────
def _fmt_value(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if abs(f) >= 1000 and f == int(f):
        return f"{int(f):,}"
    if f == int(f):
        return str(int(f))
    return f"{f:.1f}"


def _nice_ticks(lo, hi, want=5):
    """
    Round tick values spanning [lo, hi].

    The first version labelled the gridlines with raw fractions of the data
    range, so a real series produced an axis reading 1411.8 / 1039.6 / 667.5
    / 295.4 / -76.8. Nobody reads a value off that, and the bottom label is a
    negative bilirubin -- a number that cannot exist -- printed on a channel
    whose entire claim is that the numbers are the paper's own.
    """
    span = float(hi) - float(lo)
    if span <= 0:
        span = abs(float(hi)) or 1.0
    raw = span / max(1, want - 1)
    mag = 10.0 ** math.floor(math.log10(raw)) if raw > 0 else 1.0
    step = 10.0 * mag
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag:
            step = m * mag
            break
    # Cover [lo, hi] completely: the top tick must be at or above the largest
    # value, or the tallest bar runs past the last gridline and reads as
    # off-the-chart.
    v, top = math.floor(lo / step) * step, math.ceil(hi / step) * step
    out = []
    while v <= top + step * 0.001 and len(out) < 16:
        out.append(round(v, 10))
        v += step
    if len(out) < 2:
        out = [lo, hi]
    return out


def render_chart_still(chart_type, title, labels, values, out_path,
                       y_label="", niche_label="NO KNOWN CAUSE",
                       progress=1.0, citation=""):
    """
    CHART register: the case's own reported values, plotted.

    THIS REGISTER WAS RENDERING NOTHING AT ALL. clinical_pipeline passed
    chart_fn=generate_data_chart, a name that is defined in
    collapse_index_pipeline.py and was never imported into the clinical
    pipeline. The call therefore raised NameError on every CHART segment,
    was swallowed by the surrounding try/except, and fell through to the
    plain fallback text card. Rendering a full episode locally measured the
    damage: 17 of 59 segments -- 29% of the video, including six of the
    first eight -- were that card. It was invisible in logs because the
    fallback is a legitimate outcome that logs as success.

    Drawn here, in the channel's own palette, rather than by importing
    another channel's 9,000-line pipeline module for one function.

    progress drives a left-to-right reveal, so the curve draws itself across
    the episode's CHART segments instead of showing the finished plot (and
    therefore the answer) in the first thirty seconds.
    """
    labels = list(labels or [])
    values = list(values or [])
    n = min(len(labels), len(values))
    if n < 2:
        return False
    labels, values = labels[:n], values[:n]
    try:
        nums = [float(v) for v in values]
    except (TypeError, ValueError):
        return False

    c = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(c)
    _eyebrow(d, niche_label)
    d.text((90, 118), _clip_words(str(title or "REPORTED VALUES").upper(), 46),
           font=_f(46), fill=TEXT_C)
    if y_label:
        d.text((90, 182), _clip_words(str(y_label), 70), font=_f(27, False), fill=DIM)

    # B leaves room for BOTH the x-axis labels (B+26) and the CC BY credit
    # below them. At CONTENT_BOTTOM-60 the credit was drawn straight through
    # "Day 3 / Day 6 / Day 9" -- visible the moment the caption safe-zone
    # push moved them into each other.
    T, B = 250, CONTENT_BOTTOM - 105
    is_bar = str(chart_type).lower().startswith("bar")

    # AXIS RANGE.
    #
    # The old range was min-15% .. max+15% unconditionally, which invented
    # impossible readings for every strictly positive clinical series: a
    # bilirubin axis that bottomed out at -76.8, a cell count at -1,854,825.
    # A bar chart additionally MUST be zero-based -- a bar whose baseline is
    # not zero misrepresents the ratio between its bars, which on this
    # channel would be misrepresenting the patient's own values.
    dlo, dhi = min(nums), max(nums)
    if is_bar:
        # 8% headroom above the tallest bar so the callout badge has somewhere
        # to sit other than on top of the bar it is labelling.
        lo, hi = min(0.0, dlo * 1.08), max(0.0, dhi * 1.08)
    else:
        pad = (dhi - dlo) * 0.15 or (abs(dhi) * 0.1 or 1.0)
        lo, hi = dlo - pad, dhi + pad
        if dlo >= 0:
            lo = max(0.0, lo)       # never below zero for non-negative data
    if hi <= lo:
        hi, lo = lo + 1.0, lo - 1.0
    ticks = _nice_ticks(lo, hi)
    lo, hi = ticks[0], ticks[-1]
    if hi <= lo:
        hi = lo + 1.0

    # LEFT GUTTER, measured rather than assumed.
    #
    # Tick labels were drawn at a fixed x = L-130. "14,259,325" is wider than
    # that, so it ran off the left edge of the frame; the fuzz run caught ink
    # at x=0 on every wide-value series.
    f_tick = _f(24, False)
    gutter = max(int(d.textlength(_fmt_value(v), font=f_tick)) for v in ticks)
    L = min(90 + gutter + 22, 460)
    R = W - 110

    def py(v):
        return B - (v - lo) / (hi - lo) * (B - T)

    # Gridlines with real value labels -- an unlabelled grid is decoration.
    for v in ticks:
        gy = py(v)
        if gy < T - 1 or gy > B + 1:
            continue
        d.line([(L, gy), (R, gy)], fill=EDGE, width=1)
        t = _fmt_value(v)
        tw = d.textlength(t, font=f_tick)
        # Right-aligned into the gutter, and lifted off the baseline so the
        # bottom tick does not sit in the x-label row.
        ty = min(gy - 15, B - 30) if abs(gy - B) < 16 else gy - 15
        d.text((L - 18 - tw, ty), t, font=f_tick, fill=DIM)
    d.line([(L, T), (L, B)], fill=EDGE, width=2)
    d.line([(L, B), (R, B)], fill=EDGE, width=2)

    # At least two points, so the register never renders as a single dot on
    # an empty grid -- which is what the first two CHART segments looked like.
    shown = max(2, min(n, math.ceil(progress * n)))
    f_lab = _f(25, False)

    # X POSITIONS.
    #
    # Bars live in slots; points sit on the axis ends. Bars were previously
    # centred on the point positions, so on a two-point series the first bar
    # was centred on the y-axis and the last on the right edge and BOTH ran
    # off the frame -- half the chart drawn outside the picture.
    if is_bar:
        slot = (R - L) / n
        xs = [L + slot * (i + 0.5) for i in range(n)]
        bw = max(14.0, min(slot * 0.62, 150.0))
    else:
        step = (R - L) / (n - 1) if n > 1 else 0
        xs = [L + step * i for i in range(n)]

    # NOTHING PAST THE REVEAL IS DRAWN.
    #
    # The first version sketched the un-reached part of the curve as a faint
    # guide, to keep the composition stable. Looking at the rendered frames
    # killed that idea immediately: a six-point recovery curve is perfectly
    # readable in outline, so segment zero -- twelve seconds into the video --
    # showed the viewer that the child gets better. The axes are already
    # fixed to the full series range, so nothing shifts position anyway;
    # the guide bought nothing and gave away the ending.
    if is_bar:
        zero = py(max(lo, min(hi, 0.0)))
        for i in range(shown):
            top, bot = sorted((py(nums[i]), zero))
            d.rectangle([xs[i] - bw / 2, top, xs[i] + bw / 2, bot], fill=TEAL)
    else:
        pts = [(xs[i], py(nums[i])) for i in range(shown)]
        if shown >= 2:
            d.line(pts, fill=TEAL, width=5, joint="curve")
        for x, y in pts:
            d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=TEAL,
                      outline=TEAL, width=3)

    # x labels, thinned so they never collide, and clamped inside the frame
    # so the last one cannot hang off the right edge.
    every = max(1, n // 8)
    for i in range(n):
        if i % every and i != n - 1:
            continue
        t = _clip_words(str(labels[i]), 12)
        tw = d.textlength(t, font=f_lab)
        tx = min(max(xs[i] - tw / 2, 90), W - 90 - tw)
        d.text((tx, B + 26), t, font=f_lab,
               fill=TEXT_C if i < shown else DIM)

    # Call out the value the narration has just reached.
    i = shown - 1
    vx, vy = xs[i], py(nums[i])
    vt = _fmt_value(nums[i])
    vw = d.textlength(vt, font=_f(38))
    bw_box = vw + 36
    bx0 = min(max(vx - bw_box / 2, L + 4), W - 90 - bw_box)
    by0 = vy - 82 if vy - 82 >= T + 4 else min(vy + 26, B - 58)
    d.rectangle([bx0, by0, bx0 + bw_box, by0 + 54], fill=PANEL, outline=TEAL, width=2)
    d.text((bx0 + 18, by0 + 8), vt, font=_f(38), fill=TEAL)

    cred = short_credit(citation)
    if cred:
        d.text((90, CONTENT_BOTTOM - 40), cred, font=_f(24, False), fill=DIM)
    c.save(out_path)
    return Path(out_path).exists()


# ── BOARD ──────────────────────────────────────────────────────────────────
def _cap_differentials(rows, cap=5):
    """
    Trim a differential list to what fits on the board WITHOUT losing the
    answer.

    The old code took the first N. Fuzzing a nine-differential case showed
    what that costs: a real paper lists the candidates roughly in the order
    they were considered, so the diagnosis that was finally CONFIRMED is
    usually near the END of the list -- exactly the row a head-slice throws
    away. A differential board whose confirmed row has been silently dropped
    is not a shortened board, it is a wrong one.
    """
    rows = list(rows or [])
    if len(rows) <= cap:
        return rows
    def rank(r):
        v = str(r[1] if len(r) > 1 else "").lower()
        return 0 if "confirm" in v else (1 if "partial" in v else 2)
    keep = sorted(range(len(rows)), key=lambda i: (rank(rows[i]), i))[:cap]
    return [rows[i] for i in sorted(keep)]


def render_board_still(differentials, out_path, niche_label="NO KNOWN CAUSE",
                       progress=1.0):
    """
    differentials: list of (name, verdict, reason). verdict drives the colour:
    anything containing 'confirm' reads teal, 'partial' amber, else red.
    """
    if not differentials:
        return False
    c = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(c)
    _eyebrow(d, niche_label)
    d.text((90, 118), "DIFFERENTIAL DIAGNOSIS", font=_f(46), fill=TEXT_C)

    # Progressive reveal. Rendering the finished board on every BOARD
    # segment means the same still repeatedly -- measured at 39 identical
    # renders on a paper with one differential. Revealing it in step with the
    # narration is both the fix and the correct documentary device: the
    # viewer watches the possibilities get eliminated as the team eliminates
    # them, instead of being shown the answer and then told the story.
    rows_all = _cap_differentials(differentials, 5)
    resolved = max(1, min(len(rows_all), int(round(progress * len(rows_all)))))

    # WHAT IS REVEALED IS THE VERDICT, NOT THE CANDIDATE.
    #
    # The first version revealed whole rows, so an early BOARD segment drew
    # one row and three empty "?" boxes on an otherwise black 1080-line
    # frame. Rendering a real episode and looking at it made the problem
    # obvious: for the first half of the video this register is mostly empty
    # space, and the row positions jump every time another one appears.
    #
    # It is also the wrong dramatic order. A differential board is a list of
    # everything still possible; the story is watching those possibilities
    # get struck off. So every candidate is on the board from the first
    # frame, the layout is computed for the full list so nothing moves, and
    # the verdict column fills in as the narration eliminates each one.
    y = 248
    row_h = min(138, int((CONTENT_BOTTOM - 260) / max(1, len(rows_all))))
    for i, (name, verdict, reason) in enumerate(rows_all):
        decided = i < resolved
        v = (verdict or "").lower()
        col = (TEAL if "confirm" in v else (AMBER if "partial" in v else RED)) \
            if decided else EDGE
        d.rectangle([90, y, W - 90, y + row_h - 20],
                    fill=PANEL if decided else BG, outline=EDGE, width=2)
        d.rectangle([90, y, 96, y + row_h - 20], fill=col)
        d.text((130, y + 22), _clip_words(str(name), 44), font=_f(34),
               fill=TEXT_C if decided else DIM)
        if reason and decided:
            d.text((130, y + 68), _clip_words(str(reason), 76),
                   font=_f(26, False), fill=DIM)
        vt = (verdict or "").upper()[:12] if decided else "PENDING"
        vw = d.textlength(vt, font=_f(26))
        d.rectangle([W - 130 - vw - 26, y + 34, W - 104, y + 78], outline=col, width=2)
        d.text((W - 130 - vw - 13, y + 44), vt, font=_f(26), fill=col)
        # A struck-through candidate reads as eliminated at a glance, which
        # a coloured word on the far right of the row does not.
        if decided and "exclud" in v:
            nw = d.textlength(_clip_words(str(name), 44), font=_f(34))
            d.line([(130, y + 40), (130 + nw, y + 40)], fill=col, width=3)
        y += row_h
    c.save(out_path)
    return Path(out_path).exists()


# ── ANATOMY ────────────────────────────────────────────────────────────────
def _draw_pathway(d, steps, blocked_index, progress=1.0):
    """
    The mechanism motif that actually carries information: the metabolic or
    physiological chain, with the step that failed marked.

    A published case almost always turns on one broken step in a sequence --
    an enzyme that is absent, a clearance route that is saturated, a receptor
    that is blocked. Drawing the chain and putting a red cross on the step
    that failed says the thing the narration is saying. The concentric-circle
    motif this replaces said nothing at all, and said it twelve times per
    episode.
    """
    steps = [str(s) for s in (steps or []) if str(s).strip()][:4]
    if len(steps) < 2:
        return False
    n = len(steps)
    gap = 80
    box_w = int((W - 220 - (n - 1) * gap) / n)
    box_h = 200
    total = n * box_w + (n - 1) * gap
    x = (W - total) // 2
    cy = 520
    live = max(1, min(n, int(round(progress * n))))

    # Pick ONE font size that fits every step's longest word inside the box,
    # and use it for all of them. A fixed size overflowed the box on real
    # step names -- "Galactose-1-phosphate" ran straight through the border,
    # visible in the rendered frames -- and sizing each box independently
    # would make the chain look like four unrelated labels.
    f_step = _f(30)
    for size in (32, 28, 25, 22, 19, 17):
        f_try = _f(size)
        longest = max((max(d.textlength(w, font=f_try) for w in s.split())
                       for s in steps), default=0)
        if longest <= box_w - 36:
            f_step = f_try
            break

    for i, label in enumerate(steps):
        on = i < live
        is_blocked = (blocked_index is not None and i == blocked_index and on)
        col = RED if is_blocked else (TEAL if on else EDGE)
        d.rectangle([x, cy - box_h // 2, x + box_w, cy + box_h // 2],
                    fill=PANEL if on else BG, outline=col, width=3)
        f = f_step
        lines = mfr._wrap(d, label, f, box_w - 36)[:3]
        lh = f.size + 8
        ty = cy - len(lines) * lh / 2
        for ln in lines:
            tw = d.textlength(ln, font=f)
            d.text((x + (box_w - tw) / 2, ty), ln, font=f,
                   fill=TEXT_C if on else DIM)
            ty += lh
        if is_blocked:
            m = 34
            d.line([(x + box_w / 2 - m, cy - box_h // 2 - 46),
                    (x + box_w / 2 + m, cy - box_h // 2 + 18)], fill=RED, width=7)
            d.line([(x + box_w / 2 + m, cy - box_h // 2 - 46),
                    (x + box_w / 2 - m, cy - box_h // 2 + 18)], fill=RED, width=7)
        if i < n - 1:
            ax0, ax1 = x + box_w + 16, x + box_w + 74
            acol = TEAL if (i + 1) < live else EDGE
            # The arrow INTO the blocked step is the one that stops.
            if blocked_index is not None and i + 1 == blocked_index and (i + 1) < live:
                acol = RED
            d.line([(ax0, cy), (ax1, cy)], fill=acol, width=5)
            d.polygon([(ax1 + 16, cy), (ax1 - 4, cy - 13), (ax1 - 4, cy + 13)],
                      fill=acol)
        x += box_w + 90
    return True


def _draw_accumulation(d, progress=1.0):
    """
    Second motif: the consequence half of the mechanism -- something building
    up inside a cell because the step after it is blocked. Exists so
    consecutive ANATOMY segments are not the same drawing.
    """
    cx, cy = W // 2, 520
    d.ellipse([cx - 300, cy - 230, cx + 300, cy + 230], outline=TEAL, width=4)
    d.ellipse([cx - 110, cy - 85, cx + 110, cy + 85], outline=EDGE, width=3)
    filled = int(round(progress * 26))
    rnd_pts = [(-238, -60), (-196, 96), (-150, -140), (-118, 168), (-70, -40),
               (-52, 122), (-14, -168), (16, 66), (48, -104), (86, 152),
               (120, -52), (158, 88), (196, -128), (228, 42), (-268, 24),
               (-160, -8), (-96, -122), (-30, 178), (62, -150), (140, 8),
               (208, 122), (254, -70), (-208, 156), (-124, 52), (24, -70),
               (104, 96)]
    for k, (dx, dy) in enumerate(rnd_pts):
        r = 13 if k % 3 else 18
        col = AMBER if k < filled else EDGE
        d.ellipse([cx + dx - r, cy + dy - r, cx + dx + r, cy + dy + r], fill=col)


def _draw_radial(d):
    """Third motif: the original concentric figure, kept for rotation."""
    cx, cy = W // 2, 520
    for r, col in ((250, EDGE), (170, TEAL)):
        d.ellipse([cx - r, cy - r, cx + r, cy + r],
                  outline=col, width=4 if col == TEAL else 2)
    for a in range(0, 360, 45):
        r0, r1 = 200, 300
        x0 = cx + r0 * math.cos(math.radians(a))
        y0 = cy + r0 * math.sin(math.radians(a))
        x1 = cx + r1 * math.cos(math.radians(a))
        y1 = cy + r1 * math.sin(math.radians(a))
        d.line([(x0, y0), (x1, y1)], fill=TEAL, width=3)
        d.ellipse([x1 - 6, y1 - 6, x1 + 6, y1 + 6], fill=TEAL)


def render_anatomy_still(title, explanation, out_path, image_path=None,
                         niche_label="MECHANISM", pathway=None,
                         blocked_index=None, variant=0, progress=1.0,
                         variant_total=1):
    """
    A real Wikimedia diagram when one was found (image_path), otherwise one of
    three procedural mechanism motifs. The procedural path exists so ANATOMY
    is ALWAYS renderable -- it is the register the quota redistributes to when
    a paper has no usable figures, so it can never fail for lack of an asset.

    `variant` rotates the motif. Rendering a full episode showed ANATOMY
    landing on twelve of fifty-nine segments with the identical concentric
    figure every time; one motif repeated twelve times is a screensaver.
    """
    c = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(c)
    _eyebrow(d, niche_label)
    d.text((90, 118), _clip_words((title or "MECHANISM").upper(), 46),
           font=_f(46), fill=TEXT_C)

    if image_path and Path(image_path).exists():
        try:
            img = Image.open(image_path).convert("RGB")
            fitted = mfr._fit_preserving_aspect(img, W - 300, H - 460)
            pad = 16
            x0 = (W - fitted.width) // 2
            y0 = 240 + (H - 460 - fitted.height) // 2
            d.rectangle([x0 - pad, y0 - pad, x0 + fitted.width + pad,
                         y0 + fitted.height + pad],
                        fill=PANEL, outline=EDGE, width=2)
            c.paste(fitted, (x0, y0))
        except Exception:
            image_path = None
    if not image_path:
        # Motif order is a preference list, not a rotation for its own sake:
        # the pathway carries the case's actual mechanism, so it leads
        # whenever the case has one. Accumulation and the radial figure
        # alternate behind it so no two consecutive ANATOMY frames match.
        motifs = []
        if pathway:
            motifs.append(lambda p: _draw_pathway(d, pathway, blocked_index, p))
        motifs.append(lambda p: (_draw_accumulation(d, p), True)[1])
        motifs.append(lambda p: (_draw_radial(d), True)[1])
        # Each motif advances on ITS OWN appearances, not on ANATOMY's.
        # ANATOMY rotates through three motifs, so a motif is seen every third
        # ANATOMY segment -- driving its reveal off the ANATOMY counter meant
        # the pathway diagram was still on step one at its fourth showing.
        # Segments 0 and 5 of a rendered episode were the identical diagram
        # under different captions. Same class of error as the global-progress
        # bug this parameter was introduced to fix, one level further down.
        n_motifs = len(motifs)
        motif_occ = variant // n_motifs
        motif_total = max(1, math.ceil(max(1, variant_total) / n_motifs))
        motif_progress = min(1.0, (motif_occ + 1) / motif_total)
        for k in range(n_motifs):
            if motifs[(variant + k) % n_motifs](motif_progress):
                break

    if explanation:
        f = _f(30, False)
        for j, line in enumerate(mfr._wrap(d, explanation, f, W - 180)[:2]):
            d.text((90, CONTENT_BOTTOM - 96 + j * 42), line, font=f, fill=TEXT_C)
    c.save(out_path)
    return Path(out_path).exists()


# ── TEXT ───────────────────────────────────────────────────────────────────
def render_text_still(quote, out_path, attribution="From the source paper",
                      niche_label="FROM THE PAPER"):
    """
    A real quoted line. Emphasis falls on the final third, so the payoff
    clause lands in accent colour rather than the whole block shouting.
    """
    if not quote or not quote.strip():
        return False
    c = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(c)
    _eyebrow(d, niche_label)
    q = quote.strip().strip('"“”')
    # The quote block plus its rule and attribution must all fit ABOVE the
    # caption band. A fixed six-line cap overflowed it: six lines at 104px
    # from y=280 ends at 904, and the attribution sat 52px below that, both
    # inside the band. Caught by the pixel check, not by reading the code.
    TOP, LINE_H, FOOTER = 280, 104, 96
    room = CONTENT_BOTTOM - TOP - FOOTER
    max_lines = max(1, room // LINE_H)
    size = 72
    lines = mfr._wrap(d, f'“{q}”', _f(size), W - 300)
    # A long quotation shrinks rather than being cut off in the middle.
    while len(lines) > max_lines and size > 40:
        size -= 6
        lines = mfr._wrap(d, f'“{q}”', _f(size), W - 300)
    f = _f(size)
    line_h = size + 32
    lines = lines[:max(1, (CONTENT_BOTTOM - TOP - FOOTER) // line_h)]
    emph_from = max(1, int(len(lines) * 0.66))
    y = max(TOP, (CONTENT_BOTTOM - FOOTER - len(lines) * line_h) // 2)
    for i, line in enumerate(lines):
        d.text((150, y), line, font=f, fill=TEAL if i >= emph_from else TEXT_C)
        y += line_h
    d.line([(150, y + 24), (430, y + 24)], fill=EDGE, width=2)
    d.text((150, y + 52), _clip_words(attribution, 90), font=_f(26, False), fill=DIM)
    c.save(out_path)
    return Path(out_path).exists()


_SCENE_TERMS = (
    "hospital corridor empty",
    "hospital ward bed night",
    "intensive care monitor screen",
    "emergency department entrance",
    "doctor reading notes",
    "waiting room chairs empty",
    "hospital window rain",
    "operating theatre lights",
    "stethoscope on a desk",
    "medical chart on a clipboard",
    "ambulance at night",
    "laboratory bench glassware",
)


def render_scene_still(segment_text, out_path, work_dir, variant=0,
                       niche_label="NO KNOWN CAUSE", fetch_fn=None,
                       log_fn=print):
    """
    A REAL PHOTOGRAPH of the world the case happened in.

    Every other register in this module draws something. Run 31156373254
    shipped 106 segments and not one photograph: the figures failed to
    download, so the mix collapsed onto ANATOMY and TIMELINE and the episode
    alternated between two kinds of diagram for nineteen minutes. The
    complaint that came back -- "boring, something generic, and it's taking
    too much time changing the visuals" -- is what that looks like from the
    other side of the screen. The cards were 9.1-13.5s, inside spec; two
    consecutive cards that LOOK alike simply read as one long one.

    The photograph comes from stock_library first, which works with the
    network completely down, and only reaches for the API when the library
    has nothing new. Anything that scores as a drawing is rejected: this
    register exists to NOT be a drawing.

    The narration line is set over the lower third rather than beside it, so
    the picture is the card and the words are the caption.
    """
    from pathlib import Path as _P
    work = _P(work_dir)
    term = _SCENE_TERMS[variant % len(_SCENE_TERMS)]
    photo = None

    try:
        import stock_library as sl
        photo = sl.pick("scene", [term], seed=variant)
    except Exception as e:
        log_fn(f"  SCENE: stock library unavailable ({e})")

    if not photo and fetch_fn:
        cand = work / f"scene_{variant}.jpg"
        try:
            if fetch_fn(term, niche_label, str(cand)) and cand.exists():
                photo = str(cand)
        except Exception as e:
            log_fn(f"  SCENE: photo fetch failed ({e})")

    if not photo or not _P(photo).exists():
        return False

    # A diagram here would defeat the entire purpose of the register.
    try:
        import photo_thumbnail as _pt
        if _pt.looks_drawn(photo):
            log_fn(f"  SCENE: rejected a drawing ({_P(photo).name})")
            return False
    except Exception:
        pass

    try:
        im = Image.open(photo).convert("RGB")
    except Exception as e:
        log_fn(f"  SCENE: photo will not open ({e})")
        return False

    # Cover the frame, cropping rather than letterboxing.
    s = max(W / im.width, H / im.height)
    im = im.resize((max(W, int(im.width * s)), max(H, int(im.height * s))),
                   Image.LANCZOS)
    im = im.crop(((im.width - W) // 2, (im.height - H) // 2,
                  (im.width - W) // 2 + W, (im.height - H) // 2 + H))

    # Darken toward the bottom so the caption has something to sit on without
    # a box drawn around it -- a box would make it look like a slide again.
    import numpy as _np
    a = _np.asarray(im).astype(_np.float32)
    # Full brightness down to 48% of the frame, then a smooth fall to 22% at
    # the bottom edge. The first version added a constant back after the ramp,
    # which left the bottom at 77% -- white type on a white corridor floor,
    # unreadable. Measured on the render, not assumed.
    t = _np.clip((_np.arange(H) - H * 0.48) / (H * 0.52), 0.0, 1.0)
    ramp = 1.0 - 0.78 * (t ** 1.6)
    # A short darkening at the very top too, so the channel eyebrow is legible
    # over a bright ceiling as well as over a dark corridor.
    top = _np.clip((H * 0.14 - _np.arange(H)) / (H * 0.14), 0.0, 1.0)
    ramp = (ramp * (1.0 - 0.45 * top)).reshape(H, 1, 1)
    im = Image.fromarray(_np.clip(a * ramp, 0, 255).astype("uint8"))

    d = ImageDraw.Draw(im)
    _eyebrow(d, niche_label)
    line = _tidy_display_line(segment_text or "", 150)
    if line:
        f = _f(58)
        lines = mfr._wrap(d, line, f, W - 300)[:3]
        y = CONTENT_BOTTOM - 40 - len(lines) * 78
        for ln in lines:
            # A photograph is never uniformly dark, whatever the ramp does, so
            # the type carries its own shadow rather than trusting the picture.
            d.text((153, y + 3), ln, font=f, fill=(0, 0, 0))
            d.text((150, y), ln, font=f, fill=TEXT_C)
            y += 78
    im.save(out_path)
    return Path(out_path).exists()


def render_last_resort_still(segment_text, out_path, niche_label="NO KNOWN CAUSE",
                             citation=""):
    """
    The visual that renders when every other register has declined.

    Exists because this channel must NEVER fall through to stock footage.
    Run 30578466862 shipped an episode whose visuals were generic library
    clips -- a mountain, a woman dancing -- under a narration about a
    newborn's liver failure. That is worse than a plain card: it is
    actively misleading, and it is the exact failure that got the previous
    incarnation of this channel abandoned.

    A typographic card carrying this segment's own narration line is always
    renderable from local fonts, needs no network, and cannot be irrelevant
    because it literally shows what is being said.
    """
    c = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(c)
    _eyebrow(d, niche_label)

    line = _tidy_display_line(segment_text, 240)
    f = _f(52, bold=False)
    lines = mfr._wrap(d, line, f, W - 320)[:7]
    y = max(250, (CONTENT_BOTTOM - len(lines) * 78) // 2)
    for ln in lines:
        d.text((160, y), ln, font=f, fill=TEXT_C)
        y += 78

    d.line([(160, y + 30), (420, y + 30)], fill=EDGE, width=2)
    if citation:
        d.text((160, y + 56), citation[:96], font=_f(24, False), fill=DIM)
    c.save(out_path)
    return Path(out_path).exists()


# ── dispatch ───────────────────────────────────────────────────────────────
def render_medical_segment(register, case, segment_text, duration, index,
                           out_path, work_dir, niche_label="NO KNOWN CAUSE",
                           chart_fn=None, run_ffmpeg=None, log_fn=print,
                           progress=1.0, variant=None, variant_total=1,
                           accent=None, transition="fade", last_move=None,
                           photo_fn=None):
    """
    Render one segment. Returns True on success.

    case      -- dict from pmc_data.get_real_case() (may be None)
    progress  -- how far through THIS REGISTER'S own sequence of appearances
                 this segment is (RegisterQuota.reveal), not how far through
                 the episode. A register that appears twelve times must
                 advance twelve times; driving it off global position made
                 several of its appearances render identically.
    variant   -- this register's own occurrence index, for anything that
                 rotates (which figure, which mechanism motif). Same reason.
    chart_fn  -- optional override for the chart renderer.
    photo_fn  -- optional photo fetcher, fetch(query, niche, out_path) -> bool.
                 SCENE works without it from the offline stock library; this
                 only widens the pool.
    """
    if variant is None:
        variant = index
    work = Path(work_dir)
    still = work / f"med_{index}_{register.lower()}.png"
    case = case or {}
    ok = False

    try:
        if register == "CASEFILE":
            # The channel's signature opening, and the record filling in as
            # the episode learns more. Reads only what the paper states; any
            # field the paper omits shows as NOT STATED rather than being
            # invented, because a plausible fabricated age carrying a real
            # citation is the worst possible failure on a medical channel.
            from medical_casefile import render_casefile_still
            ok = render_casefile_still(
                case, str(still), narrative=segment_text or case.get("narrative", ""),
                niche_label=niche_label, accent=accent, reveal=max(0.34, progress))

        elif register == "LAB":
            # A panel of results at once, each against its reference range.
            # Returns False when the paper reports no values at all, which
            # sends the segment to another register instead of drawing an
            # empty dashboard that would imply results the paper never gave.
            from medical_lab import render_lab_still
            _src = " ".join(x for x in (case.get("narrative", ""), segment_text) if x)
            ok = render_lab_still(case, _src, str(still),
                                  niche_label=niche_label, accent=accent,
                                  reveal=max(0.25, progress))

        elif register == "FIGURE":
            figs = case.get("figures") or []
            if figs:
                # Rotate through available figures so a 6-figure paper shows
                # all six across its ~20 FIGURE segments rather than one.
                fig = figs[variant % len(figs)]
                # prefetch_figures already downloaded and validated these and
                # recorded where each one landed. The path fallback keeps the
                # renderer usable standalone (tests, other callers).
                local = Path(fig.get("local_path")
                             or (work / f"pmcfig_{variant % len(figs)}.jpg"))
                if not local.exists():
                    from pmc_data import download_figure
                    if not download_figure(fig, str(local), log_fn=log_fn):
                        # Reasons are already logged per URL attempt above.
                        # Naming the figure matters: "download failed" alone
                        # is indistinguishable from "paper had no figures",
                        # and those need opposite responses.
                        log_fn(f"  FIGURE {index}: all URL patterns failed for "
                               f"{fig.get('pmcid','?')} / {fig.get('filename','?')}")
                        return False
                ok = mfr.render_figure_frame(
                    str(local), str(still),
                    caption=fig.get("caption", ""), label=fig.get("label", ""),
                    citation=case.get("citation", ""), niche_label=niche_label)

        elif register == "CHART":
            cd = case.get("chart_data")
            if cd and cd.get("labels") and cd.get("values"):
                # chart_fn is optional now. It used to be required, and the
                # clinical pipeline passed a name it had never imported --
                # so every CHART segment raised NameError, was swallowed, and
                # rendered the plain fallback card instead. 29% of a measured
                # episode. The renderer below is the default; an injected
                # chart_fn only overrides it.
                if chart_fn:
                    ok = chart_fn(cd.get("chart_type", "bar"), cd.get("title", ""),
                                  cd["labels"], cd["values"], str(still),
                                  y_label=cd.get("y_label", ""))
                if not ok:
                    ok = render_chart_still(
                        cd.get("chart_type", "line"), cd.get("title", ""),
                        cd["labels"], cd["values"], str(still),
                        y_label=cd.get("y_label", ""), niche_label=niche_label,
                        progress=progress, citation=case.get("citation", ""))

        elif register == "BOARD":
            ok = render_board_still(case.get("differentials") or [], str(still),
                                    niche_label=niche_label, progress=progress)

        elif register == "TIMELINE":
            # Progressive reveal is a HIGHLIGHT over the full course, not a
            # slice of it -- slicing left the frame nearly empty for the first
            # half of the episode and moved every event as the reveal grew.
            _tl = case.get("timeline") or []
            _n = max(1, min(len(_tl), int(round(progress * len(_tl))))) if _tl else 0
            ok = mfr.render_timeline_frame(_tl, str(still),
                                           niche_label=niche_label,
                                           reached=_n)

        elif register == "ANATOMY":
            # MOTION FIRST.
            #
            # This register answers "what was physically happening inside
            # this patient", and that question is about CHANGE -- something
            # spread, something was blocked, something recovered. It used to
            # answer it with one fetched still held for the length of the
            # card. At 18% of the episode that is roughly three minutes of a
            # static picture, and it was the weakest thing in the pipeline.
            #
            # medical_anatomy_motion renders a real frame sequence, choosing
            # the motion from what the narration actually says rather than by
            # rotation: animating recovery over narration about deterioration
            # would be a factual error made in pictures.
            #
            # The still path below stays as the fallback, so a failure here
            # degrades to exactly what shipped before rather than to nothing.
            try:
                from medical_anatomy_motion import render_anatomy_motion
                if render_anatomy_motion(
                        case, segment_text, out_path, duration, work_dir,
                        niche_name=case.get("niche_name", ""), accent=accent,
                        run_ffmpeg=run_ffmpeg):
                    return True
            except Exception as _e:
                log_fn(f"  Segment {index + 1} anatomy motion "
                       f"(non-fatal, using the still): {_e}")

            anat = case.get("anatomy") or {}
            img = None
            kw = anat.get("search")
            if kw:
                try:
                    from real_case_images import search_wikimedia_commons
                    cand = work / f"anat_{index}.jpg"
                    got, _lic = search_wikimedia_commons(kw, str(cand))
                    if got:
                        img = str(cand)
                except Exception:
                    img = None
            # Alternate between the mechanism explanation and THIS segment's
            # own narration line, so consecutive ANATOMY segments are not the
            # same frame with the same caption.
            _expl = (anat.get("explanation") or "") if variant % 2 == 0 else ""
            _bi = anat.get("blocked_step")
            ok = render_anatomy_still(anat.get("title", "Mechanism"),
                                      _expl or _tidy_display_line(segment_text, 150),
                                      str(still), image_path=img,
                                      pathway=anat.get("pathway"),
                                      blocked_index=(int(_bi) if isinstance(_bi, (int, float))
                                                     else None),
                                      variant=variant, progress=progress,
                                      variant_total=variant_total)

        elif register == "SCENE":
            ok = render_scene_still(segment_text, str(still), work_dir,
                                    variant=variant, niche_label=niche_label,
                                    fetch_fn=photo_fn, log_fn=log_fn)

        elif register == "TEXT":
            ok = render_text_still(case.get("quote") or "", str(still),
                                    attribution=short_credit(case.get("citation", ""))
                                                 or "From the source paper")
    except Exception as e:
        log_fn(f"  {register} segment {index} render failed (non-fatal): {e}")
        return False

    if not ok:
        # Never return False. A False here sends the caller to stock footage,
        # which is how an episode about a newborn's liver failure ended up
        # showing a mountain and a woman dancing. ANATOMY and this card are
        # both procedural and always renderable, so there is no legitimate
        # reason to ever need a library clip on this channel.
        log_fn(f"  {register} {index}: no data -> clinical fallback card")
        ok = render_last_resort_still(segment_text, str(still),
                                      niche_label=niche_label,
                                      citation=short_credit(case.get("citation", "")))
        if not ok:
            return False
    # FIGURE holds are panned more gently -- aggressive zoom on diagnostic
    # imaging starts to crop anatomy out of frame.
    return still_to_clip(still, duration, out_path, run_ffmpeg=run_ffmpeg,
                         zoom=True, register=register, transition=transition,
                         index_hint=index, last_move=last_move)


# ── VERTICAL (9:16) — Shorts ───────────────────────────────────────────────
# Ch1's Shorts were still downloading Pixabay clips. The main video had stock
# footage removed after a real episode about a newborn's liver failure shipped
# illustrated with a mountain and a woman dancing -- but the Shorts path was
# never touched, so a third of this channel's daily output was still generic
# library footage of "hospital corridor night", and the topic-anchored query
# made it worse: it takes the commonest long word from the title, so a case
# about galactosaemia searched Pixabay for "galactose hospital corridor".
#
# A Short is the same channel. It draws from the same paper.
VW, VH = 1080, 1920

# Derived from the MEASURED Shorts caption, not guessed -- the same mistake
# was made once already on the horizontal episode, where a guessed 200px band
# was clear in the still and crossed in the zoomed clip.
#
# Measured by burning a real cue with the Shorts style: ink starts at y=1284.
# The vertical background zooms to 1.08, and a zoom magnifies outward from
# the centre, so content low in the frame moves further down.
V_CAPTION_INK_TOP = 1284
V_MAX_ZOOM = 1.08
V_CONTENT_BOTTOM = int(VH / 2 + ((V_CAPTION_INK_TOP - 6) - VH / 2) / V_MAX_ZOOM)
V_CAPTION_SAFE_H = VH - V_CONTENT_BOTTOM


def _vf(size, bold=True):
    return mfr._font(size, bold)


# A Short burns its HOOK across the top of the frame -- up to three lines at
# 54px starting at y=140, so it can reach y=342. The card's own header sat at
# y=150 and its title at y=250, directly underneath it: assembling a real
# Short showed the hook printed straight through the channel eyebrow and into
# the paper title. The card therefore starts below the hook's worst case.
V_TOP_RESERVED = 380


def _v_eyebrow(d, label, y=V_TOP_RESERVED):
    d.line([(80, y), (140, y)], fill=TEAL, width=4)
    d.text((156, y - 18), label, font=_vf(32), fill=TEAL)


def render_vertical_card(kind, case, out_path, headline="",
                         niche_label="NO KNOWN CAUSE", progress=1.0):
    """
    One 1080x1920 card built from the episode's own case.

    kind: "title" | "board" | "timeline" | "chart" | "quote" | "statement"
    Returns True on success. Falls back to "statement" (always renderable
    from the headline alone) rather than to anything fetched.
    """
    case = case or {}
    c = Image.new("RGB", (VW, VH), BG)
    d = ImageDraw.Draw(c)
    _v_eyebrow(d, niche_label)
    y = V_TOP_RESERVED + 100

    def _heading(text, size=62, fill=TEXT_C, max_lines=4):
        """Shrinks to fit rather than truncating -- a quotation cut off at
        "rather than its" reads as a bug, and the quote card is the one that
        most often needs the room."""
        nonlocal y
        f = _vf(size)
        lines = mfr._wrap(d, text, f, VW - 160)
        while len(lines) > max_lines and size > 34:
            size -= 6
            f = _vf(size)
            lines = mfr._wrap(d, text, f, VW - 160)
        for ln in lines[:max_lines]:
            d.text((80, y), ln, font=f, fill=fill)
            y += size + 16
        y += 24

    try:
        if kind == "title":
            _heading(_tidy_display_line(headline or case.get("title", ""), 140), 66)
            d.line([(80, y), (400, y)], fill=TEAL, width=5)
            src = f"{case.get('journal','')} {case.get('year','')}".strip()
            if src:
                d.text((80, y + 30), _clip_words(src, 46), font=_vf(34, False),
                       fill=TEAL)

        elif kind == "board":
            rows = _cap_differentials(case.get("differentials"), 4)
            if not rows:
                return render_vertical_card("statement", case, out_path,
                                            headline, niche_label)
            _heading("DIFFERENTIAL", 54, TEXT_C)
            resolved = max(1, min(len(rows), int(round(progress * len(rows)))))
            for i, (name, verdict, _reason) in enumerate(rows):
                on = i < resolved
                v = (verdict or "").lower()
                col = (TEAL if "confirm" in v else
                       (AMBER if "partial" in v else RED)) if on else EDGE
                d.rectangle([80, y, VW - 80, y + 150],
                            fill=PANEL if on else BG, outline=EDGE, width=2)
                d.rectangle([80, y, 88, y + 150], fill=col)
                for j, ln in enumerate(mfr._wrap(d, str(name), _vf(40),
                                                 VW - 220)[:2]):
                    d.text((116, y + 24 + j * 46), ln, font=_vf(40),
                           fill=TEXT_C if on else DIM)
                vt = (verdict or "").upper()[:10] if on else ""
                if vt:
                    d.text((116, y + 108), vt, font=_vf(28), fill=col)
                y += 170

        elif kind == "timeline":
            events, _kept = mfr.condense_timeline(case.get("timeline"), 5)
            if len(events) < 2:
                return render_vertical_card("statement", case, out_path,
                                            headline, niche_label)
            _heading("CLINICAL COURSE", 54)
            live = max(1, min(len(events), int(round(progress * len(events)))))
            spine = 108
            # The reserve below the LAST dot has to cover that event's own
            # description, not just the dot. At 60 it covered a one-line
            # description only, so any event whose text wrapped to two lines
            # pushed ink past the safe bottom and into the Shorts caption --
            # invisible until the condensed timeline happened to end on a
            # longer event. Two lines of 36px plus the 4px offset is 76.
            step = (V_CONTENT_BOTTOM - y - 92) / max(1, len(events) - 1)
            d.line([(spine, y), (spine, y + step * (len(events) - 1))],
                   fill=EDGE, width=4)
            for i, (day, desc) in enumerate(events):
                ey = int(y + step * i)
                on = i < live
                r = 15 if on else 11
                d.ellipse([spine - r, ey - r, spine + r, ey + r],
                          fill=TEAL if on else BG,
                          outline=TEAL if on else EDGE, width=4)
                d.text((spine + 44, ey - 40), str(day).upper(), font=_vf(36),
                       fill=TEAL if on else DIM)
                if on:
                    for j, ln in enumerate(mfr._wrap(d, desc, _vf(30, False),
                                                     VW - spine - 120)[:2]):
                        d.text((spine + 44, ey + 4 + j * 36), ln,
                               font=_vf(30, False), fill=TEXT_C)

        elif kind == "chart":
            cd = case.get("chart_data") or {}
            labels, values = cd.get("labels") or [], cd.get("values") or []
            n = min(len(labels), len(values))
            if n < 2:
                return render_vertical_card("statement", case, out_path,
                                            headline, niche_label)
            nums = [float(v) for v in values[:n]]
            _heading(_clip_words(str(cd.get("title", "REPORTED VALUES")).upper(), 34), 50)
            R = VW - 90
            T, B = y + 40, V_CONTENT_BOTTOM - 120
            # Same axis rules as the horizontal chart: round tick values, and
            # never a floor below zero for non-negative data. The old
            # min-15%..max+15% padding printed a negative bilirubin under a
            # curve of the patient's real bilirubin.
            dlo, dhi = min(nums), max(nums)
            pad = (dhi - dlo) * 0.15 or (abs(dhi) * 0.1 or 1.0)
            lo, hi = dlo - pad, dhi + pad
            if dlo >= 0:
                lo = max(0.0, lo)
            if hi <= lo:
                hi, lo = lo + 1.0, lo - 1.0
            vticks = _nice_ticks(lo, hi, want=4)
            lo, hi = vticks[0], vticks[-1]
            if hi <= lo:
                hi = lo + 1.0
            py = lambda v: B - (v - lo) / (hi - lo) * (B - T)
            f_vt = _vf(26, False)
            # The left gutter is measured, not fixed: a cell count reaching
            # eight figures is wider than the 150px the fixed L=190 left it,
            # and ran off the side of the Short.
            _gut = max(int(d.textlength(_fmt_value(v), font=f_vt)) for v in vticks)
            L = min(60 + _gut + 20, 460)
            for v in vticks:
                gy = py(v)
                if gy < T - 1 or gy > B + 1:
                    continue
                d.line([(L, gy), (R, gy)], fill=EDGE, width=1)
                t = _fmt_value(v)
                d.text((L - 20 - d.textlength(t, font=f_vt), gy - 18),
                       t, font=f_vt, fill=DIM)
            d.line([(L, T), (L, B)], fill=EDGE, width=3)
            d.line([(L, B), (R, B)], fill=EDGE, width=3)
            shown = max(2, min(n, math.ceil(progress * n)))
            step = (R - L) / (n - 1)
            pts = [(L + step * i, py(nums[i])) for i in range(shown)]
            d.line(pts, fill=TEAL, width=7, joint="curve")
            for x, yy in pts:
                d.ellipse([x - 11, yy - 11, x + 11, yy + 11], fill=TEAL)
            for i in (0, n - 1):
                t = _clip_words(str(labels[i]), 10)
                tw = d.textlength(t, font=_vf(28, False))
                d.text((min(max(L, L + step * i - tw / 2), R - tw), B + 22), t,
                       font=_vf(28, False), fill=DIM)

        elif kind == "quote":
            q = (case.get("quote") or "").strip()
            if not q:
                return render_vertical_card("statement", case, out_path,
                                            headline, niche_label)
            _heading(f'"{q}"', 54, TEXT_C, max_lines=7)
            d.line([(80, y), (360, y)], fill=EDGE, width=3)
            cred = short_credit(case.get("citation", ""))
            if cred:
                d.text((80, y + 26), _clip_words(cred, 54), font=_vf(24, False),
                       fill=DIM)

        else:  # statement — always renderable
            # Do NOT repeat the title card. The pipeline passes the paper's
            # title as `headline`, so a statement card built from it was the
            # title card again -- twice in a six-card Short. Prefer the
            # mechanism explanation, which is the most interesting sentence
            # the case has and is not shown anywhere else in the sequence.
            _body = ((case.get("anatomy") or {}).get("explanation")
                     or headline or case.get("title", ""))
            _heading(_tidy_display_line(_body, 240), 54, max_lines=7)
            cred = short_credit(case.get("citation", ""))
            if cred:
                d.line([(80, V_CONTENT_BOTTOM - 90),
                        (400, V_CONTENT_BOTTOM - 90)], fill=EDGE, width=3)
                d.text((80, V_CONTENT_BOTTOM - 64), _clip_words(cred, 54),
                       font=_vf(24, False), fill=DIM)
    except Exception:
        return False

    c.save(out_path)
    return Path(out_path).exists()


VERTICAL_SEQUENCE = ("title", "board", "timeline", "chart", "quote", "statement")


# Vertical card kinds mapped to the register whose camera behaviour suits
# them, so a Short's moves are chosen on the same logic as the main video's.
_VCARD_REGISTER = {
    "title": "TITLE", "statement": "TEXT", "quote": "TEXT",
    "board": "BOARD", "timeline": "TIMELINE", "chart": "CHART",
}


def render_vertical_background(case, out_path, duration, headline="",
                               niche_label="NO KNOWN CAUSE", run_ffmpeg=None,
                               work_dir=None):
    """
    A full 9:16 background for one Short: a sequence of real clinical cards
    from THIS case, cut at a Shorts pace, concatenated.

    Replaces the Pixabay download entirely for this channel. Nothing is
    fetched, so nothing can be irrelevant.
    """
    work = Path(work_dir or Path(out_path).parent)
    work.mkdir(parents=True, exist_ok=True)
    kinds = [k for k in VERTICAL_SEQUENCE
             if k in ("title", "statement")
             or (k == "board" and case.get("differentials"))
             or (k == "timeline" and len(case.get("timeline") or []) >= 2)
             or (k == "chart" and (case.get("chart_data") or {}).get("labels"))
             or (k == "quote" and (case.get("quote") or "").strip())]
    if not kinds:
        kinds = ["statement"]
    # ACCELERATING PACE.
    #
    # Cards were a flat ~4s each. On a Short a constant cut rate tells the
    # viewer nothing is building, and the drop-off is in the middle. Opening
    # card gets the most room (it is the hook and it has to be read), then
    # each card is shorter than the last, so the Short feels like it is
    # speeding toward something. Same total length either way.
    n = max(3, min(len(kinds) * 2, int(round(duration / 3.6))))

    # RENDER THE STILLS FIRST, THEN DIVIDE THE TIME.
    #
    # Time used to be divided up front and a card that failed to render was
    # skipped with `continue` -- taking its slice of the Short with it.
    # Measured: a 26.0s Short came out 22.08s, because one card of the seven
    # did not render. A Short that is four seconds shorter than its audio is
    # desynced for its whole second half.
    #
    # Deciding the split only over the cards that actually exist makes the
    # total exact regardless of how many fail.
    stills = []
    for i in range(n):
        kind = kinds[i % len(kinds)]
        still = work / f"vcard_{i}_{kind}.png"
        if render_vertical_card(kind, case, str(still), headline=headline,
                                niche_label=niche_label, progress=(i + 1) / n):
            stills.append((kind, still))
    if not stills:
        return False

    # Opening card gets the most room -- it is the hook and it has to be read
    # -- then each card is shorter than the last, so the Short feels like it
    # is speeding toward something. A constant cut rate tells a viewer
    # nothing is building, and the drop-off on Shorts is in the middle.
    weights = [1.45] + [1.0 - 0.055 * i for i in range(len(stills) - 1)]
    wsum = sum(weights) or 1.0
    durs = [duration * w / wsum for w in weights]

    try:
        import clinical_camera as ccam
        import clinical_transitions as ctr
    except Exception:
        ccam = ctr = None

    clips = []
    last_move = None
    last_trans = None
    for i, (kind, still) in enumerate(stills):
        per = durs[i]
        clip = work / f"vclip_{i}.mp4"

        # Same treatment the main video just got: a camera move suited to the
        # card and a transition that is never the one before it. A Short is
        # the format least able to afford looking automated.
        if ccam and ctr:
            move = ccam.move_for(_VCARD_REGISTER.get(kind, "TEXT"), i, last=last_move)
            last_move = move
            base = ccam.filter_for(move, per, w=VW, h=VH)
            pool = [t for t in ("scanline", "slice", "shutter", "contrast", "fade")
                    if t != last_trans]
            trans = pool[i % len(pool)]
            last_trans = trans
            extra, frag = ctr.build(trans, duration=min(0.28, per / 4), w=VW, h=VH)
            cmd = (["ffmpeg", "-y", "-loop", "1", "-i", str(still)] + extra +
                   ["-filter_complex", f"[0:v]{base}[base];{frag}",
                    "-map", "[vout]", "-t", f"{per:.2f}",
                    "-c:v", "libx264", "-preset", "ultrafast",
                    "-pix_fmt", "yuv420p", "-an", str(clip)])
        else:
            cmd = ["ffmpeg", "-y", "-loop", "1", "-i", str(still),
                   "-vf", (f"scale={VW}:{VH},zoompan=z='min(zoom+0.0004,1.08)':"
                           f"d={max(1, int(per * 24))}:s={VW}x{VH}:fps=24,"
                           # 0.3 was a main-video fade length applied to a
                           # Short. Measured on a real 25s assembly: with six
                           # cards it put a visible dip to black at every one
                           # of the five cuts, up to 0.29s each -- roughly 4%
                           # of the Short is black, in the format least able
                           # to afford it.
                           f"fade=t=in:st=0:d=0.12"),
                   "-t", f"{per:.2f}", "-c:v", "libx264", "-preset", "ultrafast",
                   "-pix_fmt", "yuv420p", "-an", str(clip)]
        (run_ffmpeg(cmd, label="short-card") if run_ffmpeg
         else subprocess.run(cmd, capture_output=True, timeout=180))
        if clip.exists() and clip.stat().st_size > 1000:
            clips.append(clip)
    if not clips:
        return False
    lst = work / "vconcat.txt"
    lst.write_text("".join(f"file '{c.resolve()}'\n" for c in clips))
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
           "-c", "copy", str(out_path)]
    (run_ffmpeg(cmd, label="short-bg") if run_ffmpeg
     else subprocess.run(cmd, capture_output=True, timeout=180))
    return Path(out_path).exists() and Path(out_path).stat().st_size > 10000
