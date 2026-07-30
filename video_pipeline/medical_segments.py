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
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import medical_figure_render as mfr

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


# ── BOARD ──────────────────────────────────────────────────────────────────
def render_board_still(differentials, out_path, niche_label="NO KNOWN CAUSE"):
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

    rows = differentials[:5]
    y = 248
    row_h = min(138, int((H - 300) / max(1, len(rows))))
    for name, verdict, reason in rows:
        v = (verdict or "").lower()
        col = TEAL if "confirm" in v else (AMBER if "partial" in v else RED)
        d.rectangle([90, y, W - 90, y + row_h - 20], fill=PANEL, outline=EDGE, width=2)
        d.rectangle([90, y, 96, y + row_h - 20], fill=col)
        d.text((130, y + 22), str(name)[:44], font=_f(34), fill=TEXT_C)
        if reason:
            d.text((130, y + 68), str(reason)[:70], font=_f(26, False), fill=DIM)
        vt = (verdict or "").upper()[:12]
        vw = d.textlength(vt, font=_f(26))
        d.rectangle([W - 130 - vw - 26, y + 34, W - 104, y + 78], outline=col, width=2)
        d.text((W - 130 - vw - 13, y + 44), vt, font=_f(26), fill=col)
        y += row_h
    c.save(out_path)
    return Path(out_path).exists()


# ── ANATOMY ────────────────────────────────────────────────────────────────
def render_anatomy_still(title, explanation, out_path, image_path=None,
                         niche_label="MECHANISM"):
    """
    A real Wikimedia diagram when one was found (image_path), otherwise a
    procedural concentric mechanism figure. The procedural fallback exists so
    ANATOMY is ALWAYS renderable -- it is one of the registers the quota
    redistributes to when a paper has no usable figures, so it can never be
    allowed to fail for lack of an asset.
    """
    c = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(c)
    _eyebrow(d, niche_label)
    d.text((90, 118), (title or "MECHANISM").upper()[:46], font=_f(46), fill=TEXT_C)

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


# ── dispatch ───────────────────────────────────────────────────────────────
def render_medical_segment(register, case, segment_text, duration, index,
                           out_path, work_dir, niche_label="NO KNOWN CAUSE",
                           chart_fn=None, run_ffmpeg=None, log_fn=print):
    """
    Render one segment. Returns True on success.

    case      -- dict from pmc_data.get_real_case() (may be None)
    chart_fn  -- the pipeline's existing generate_data_chart, injected so the
                 chart code built for Ch5's FRED work is genuinely reused
                 rather than duplicated here.
    """
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
                fig = figs[index % len(figs)]
                local = work / f"pmcfig_{index % len(figs)}.jpg"
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
            if cd and chart_fn:
                ok = chart_fn(cd.get("chart_type", "bar"), cd.get("title", ""),
                              cd["labels"], cd["values"], str(still),
                              y_label=cd.get("y_label", ""))

        elif register == "BOARD":
            ok = render_board_still(case.get("differentials") or [], str(still),
                                    niche_label=niche_label)

        elif register == "TIMELINE":
            ok = mfr.render_timeline_frame(case.get("timeline") or [], str(still),
                                           niche_label=niche_label)

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
            ok = render_anatomy_still(anat.get("title", "Mechanism"),
                                      anat.get("explanation", segment_text[:150]),
                                      str(still), image_path=img)

        elif register == "TEXT":
            ok = render_text_still(case.get("quote") or "", str(still),
                                    attribution=case.get("citation", "")[:70]
                                                 or "From the source paper")
    except Exception as e:
        log_fn(f"  {register} segment {index} render failed (non-fatal): {e}")
        return False

    if not ok:
        return False
    # FIGURE holds are panned more gently -- aggressive zoom on diagnostic
    # imaging starts to crop anatomy out of frame.
    return still_to_clip(still, duration, out_path, run_ffmpeg=run_ffmpeg,
                         zoom=(register != "FIGURE") or True)
