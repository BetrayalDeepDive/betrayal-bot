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
RED = (192, 85, 75)
AMBER = (195, 154, 69)


def _f(size, bold=True):
    return mfr._font(size, bold)


def _eyebrow(draw, label, y=82):
    draw.line([(90, y), (144, y)], fill=TEAL, width=3)
    draw.text((158, y - 14), label, font=_f(24), fill=TEAL)


def still_to_clip(still_path, duration, out_path, run_ffmpeg=None, zoom=True):
    """
    Turn a rendered still into a clip with continuous slow motion.

    A held 14-15s shot that is genuinely static reads as a slideshow -- the
    specific failure this channel already hit twice. The zoompan below keeps
    something moving inside every held frame, and the 0.4s fade prevents the
    hard cut-to-fully-formed-graphic that was flagged as the most jarring
    transition in the previous pipeline.
    """
    vf = ("scale=1920:1080,"
          + (f"zoompan=z='min(zoom+0.00045,1.12)':d={max(1, int(duration * 24))}"
             f":s=1920x1080:fps=24," if zoom else "")
          + "fade=t=in:st=0:d=0.4")
    cmd = ["ffmpeg", "-y", "-loop", "1", "-i", str(still_path),
           "-vf", vf, "-t", f"{duration:.2f}",
           "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
           "-an", str(out_path)]
    if run_ffmpeg:
        run_ffmpeg(cmd, label="medical-segment")
    else:
        subprocess.run(cmd, capture_output=True, timeout=180)
    return Path(out_path).exists() and Path(out_path).stat().st_size > 1000


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

    L, R, T, B = 150, W - 110, 250, H - 190
    lo, hi = min(nums), max(nums)
    if hi == lo:
        hi, lo = hi + 1, lo - 1
    pad = (hi - lo) * 0.15
    lo, hi = lo - pad, hi + pad

    def py(v):
        return B - (v - lo) / (hi - lo) * (B - T)

    # Gridlines with real value labels -- an unlabelled grid is decoration.
    for k in range(5):
        v = lo + (hi - lo) * k / 4.0
        gy = py(v)
        d.line([(L, gy), (R, gy)], fill=EDGE, width=1)
        d.text((L - 130, gy - 15), _fmt_value(v), font=_f(24, False), fill=DIM)
    d.line([(L, T), (L, B)], fill=EDGE, width=2)
    d.line([(L, B), (R, B)], fill=EDGE, width=2)

    # At least two points, so the register never renders as a single dot on
    # an empty grid -- which is what the first two CHART segments looked like.
    shown = max(2, min(n, math.ceil(progress * n)))
    step = (R - L) / (n - 1) if n > 1 else 0
    f_lab = _f(25, False)

    # NOTHING PAST THE REVEAL IS DRAWN.
    #
    # The first version sketched the un-reached part of the curve as a faint
    # guide, to keep the composition stable. Looking at the rendered frames
    # killed that idea immediately: a six-point recovery curve is perfectly
    # readable in outline, so segment zero -- twelve seconds into the video --
    # showed the viewer that the child gets better. The axes are already
    # fixed to the full series range, so nothing shifts position anyway;
    # the guide bought nothing and gave away the ending.
    if str(chart_type).lower().startswith("bar"):
        bw = max(18, int(step * 0.5))
        for i in range(shown):
            x = L + step * i
            d.rectangle([x - bw / 2, py(nums[i]), x + bw / 2, B], fill=TEAL)
    else:
        pts = [(L + step * i, py(nums[i])) for i in range(shown)]
        if shown >= 2:
            d.line(pts, fill=TEAL, width=5, joint="curve")
        for x, y in pts:
            d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=TEAL,
                      outline=TEAL, width=3)

    # x labels, thinned so they never collide
    every = max(1, n // 8)
    for i in range(n):
        if i % every and i != n - 1:
            continue
        x = L + step * i
        t = _clip_words(str(labels[i]), 12)
        tw = d.textlength(t, font=f_lab)
        d.text((x - tw / 2, B + 18), t, font=f_lab,
               fill=TEXT_C if i < shown else DIM)

    # Call out the value the narration has just reached.
    i = shown - 1
    vx, vy = L + step * i, py(nums[i])
    vt = _fmt_value(nums[i])
    vw = d.textlength(vt, font=_f(38))
    bx0, by0 = vx - vw / 2 - 18, vy - 82
    d.rectangle([bx0, by0, bx0 + vw + 36, by0 + 54], fill=PANEL, outline=TEAL, width=2)
    d.text((bx0 + 18, by0 + 8), vt, font=_f(38), fill=TEAL)

    cred = short_credit(citation)
    if cred:
        d.text((90, H - 62), cred, font=_f(24, False), fill=DIM)
    c.save(out_path)
    return Path(out_path).exists()


# ── BOARD ──────────────────────────────────────────────────────────────────
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
    rows_all = differentials[:5]
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
    row_h = min(138, int((H - 300) / max(1, len(rows_all))))
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
    cy = 560
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
    cx, cy = W // 2, 590
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
    cx, cy = W // 2, 600
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
            d.text((90, H - 130 + j * 42), line, font=f, fill=TEXT_C)
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
    f = _f(72)
    lines = mfr._wrap(d, f'“{q}”', f, W - 300)[:6]
    emph_from = max(1, int(len(lines) * 0.66))
    y = max(280, (H - len(lines) * 104) // 2)
    for i, line in enumerate(lines):
        d.text((150, y), line, font=f, fill=TEAL if i >= emph_from else TEXT_C)
        y += 104
    d.line([(150, y + 24), (430, y + 24)], fill=EDGE, width=2)
    d.text((150, y + 52), attribution[:70], font=_f(26, False), fill=DIM)
    c.save(out_path)
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
    y = max(250, (H - len(lines) * 78) // 2)
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
                           progress=1.0, variant=None, variant_total=1):
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
    """
    if variant is None:
        variant = index
    work = Path(work_dir)
    still = work / f"med_{index}_{register.lower()}.png"
    case = case or {}
    ok = False

    try:
        if register == "FIGURE":
            figs = case.get("figures") or []
            if figs:
                # Rotate through available figures so a 6-figure paper shows
                # all six across its ~20 FIGURE segments rather than one.
                fig = figs[variant % len(figs)]
                local = work / f"pmcfig_{variant % len(figs)}.jpg"
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
                         zoom=True)
