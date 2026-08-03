"""
Thumbnails for No Known Cause — a clinical case channel.

WHY A NEW RENDERER RATHER THAN NEW PROMPTS
------------------------------------------
The channel's thumbnails were near-black (background 14,18,22) with
brightness pulled to 0.40 and a 0.55 vignette on top, then whatever image
the search chain returned was laid underneath modest text. On the two
episodes actually on the channel, that chain returned a scientific figure
from the source paper — so the thumbnail became a dark diagram with its own
tiny caption baked in. At the ~210px a thumbnail is really seen at, that is
a smudge. Reported as, accurately, boring.

Darkening was never the problem to solve. YouTube's own interface is dark,
so a dark thumbnail is camouflage. The thing that makes a clinical thumbnail
work is the same thing that makes a real case interesting: ONE anomaly,
marked, with the fewest possible words next to it.

THE THREE FORMATS
-----------------
Every one is drawn here, from shapes and text. Nothing depends on an image
model returning something usable, which is what made the old path
unpredictable — and nothing here can generate a realistic-looking scene, so
the synthetic-media question does not arise (see synthetic_media_policy.py).

  LIGHTBOX   A radiology lightbox: pale, cold, backlit. Dark text on a
             bright field. In a feed of dark thumbnails the bright one is
             the one the eye lands on, which is the entire job.
  ANOMALY    Deep teal field, scan window on the right, one finding ringed
             in red with a leader line to it. The red ring is the visual
             convention of medical mystery content and it survives being
             shrunk further than any other element.
  VITALS     A monitor trace across the whole frame that spikes and then
             flatlines, with the text sitting on the baseline. The most
             kinetic of the three — it reads as something going wrong.

Each takes the same inputs and returns a 1280x720 JPEG.
"""
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1280, 720

FONT_BOLD = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]
FONT_MONO = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
]

INK = (16, 22, 28)
BONE = (238, 243, 244)
TEAL = (34, 168, 156)
TEAL_DEEP = (12, 74, 78)
ALERT = (232, 62, 58)

FORMATS = ("lightbox", "anomaly", "vitals")


def _font(paths, size):
    for fp in paths:
        if Path(fp).exists():
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _text_w(draw, s, font):
    b = draw.textbbox((0, 0), s, font=font)
    return b[2] - b[0]


def _wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if _text_w(draw, trial, font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _fit_block(draw, text, paths, max_w, max_h, start, min_size=34):
    """Largest size at which the wrapped text still fits the box.

    Thumbnail text that overflows is worse than thumbnail text that is a
    little small, so this only ever shrinks — it never crops.
    """
    size = start
    while size > min_size:
        font = _font(paths, size)
        lines = _wrap(draw, text, font, max_w)
        lh = int(size * 1.12)
        if len(lines) * lh <= max_h and len(lines) <= 3:
            return font, lines, lh
        size -= 4
    font = _font(paths, min_size)
    return font, _wrap(draw, text, font, max_w)[:3], int(min_size * 1.12)


def _vgrad(size, top, bottom):
    w, h = size
    base = Image.new("RGB", (1, h))
    px = base.load()
    for y in range(h):
        t = y / max(1, h - 1)
        px[0, y] = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
    return base.resize((w, h), Image.BICUBIC)


def _grid(img, step, colour, alpha):
    """Faint measurement grid — the thing that says 'clinical' without a word."""
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for x in range(0, img.size[0], step):
        d.line([(x, 0), (x, img.size[1])], fill=colour + (alpha,), width=1)
    for y in range(0, img.size[1], step):
        d.line([(0, y), (img.size[0], y)], fill=colour + (alpha,), width=1)
    return Image.alpha_composite(img.convert("RGBA"), lay).convert("RGB")


def _trace(d, x0, x1, baseline, amp, rng, colour, width, flatline_at=None):
    """One monitor trace: quiet baseline, QRS-style spikes, optional flatline."""
    pts, x = [], x0
    while x < x1:
        if flatline_at and x > flatline_at:
            pts.append((x, baseline))
            x += 8
            continue
        phase = (x - x0) % 190
        if phase < 8:
            y = baseline + amp * 0.18
        elif phase < 16:
            y = baseline - amp
        elif phase < 24:
            y = baseline + amp * 0.45
        elif phase < 40:
            y = baseline - amp * 0.12
        else:
            y = baseline + rng.uniform(-2.5, 2.5)
        pts.append((x, y))
        x += 4
    d.line(pts, fill=colour, width=width, joint="curve")
    return pts


def _badge(d, text, x, y, fg, bg):
    f = _font(FONT_MONO, 26)
    tw = _text_w(d, text, f)
    d.rectangle([x, y, x + tw + 30, y + 44], fill=bg)
    d.text((x + 15, y + 8), text, font=f, fill=fg)
    return x + tw + 30


def _ring(d, cx, cy, r, colour, width=8, ticks=True):
    """The anomaly marker. Survives being shrunk further than anything else."""
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=colour, width=width)
    if ticks:
        for a in (0, 90, 180, 270):
            rad = math.radians(a)
            d.line([(cx + math.cos(rad) * (r + 6), cy + math.sin(rad) * (r + 6)),
                    (cx + math.cos(rad) * (r + 22), cy + math.sin(rad) * (r + 22))],
                   fill=colour, width=width - 2)


def _scan_window(rng, w, h, warm=False):
    """An abstract scan field: soft blobs, no anatomy, nothing photoreal.

    Deliberately NOT a picture of a body. It reads as imaging at a glance and
    depicts no real person, which is both the policy position and the honest
    one -- the only real patient imagery on this channel comes from the
    paper's own CC BY figures, inside the video, attributed.
    """
    img = Image.new("RGB", (w, h), (8, 14, 18) if not warm else (22, 26, 30))
    d = ImageDraw.Draw(img)
    for _ in range(14):
        cx, cy = rng.randint(0, w), rng.randint(0, h)
        rr = rng.randint(int(w * 0.10), int(w * 0.40))
        v = rng.randint(28, 96)
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=(v, v + 8, v + 12))
    img = img.filter(ImageFilter.GaussianBlur(radius=w * 0.045))
    return img


def _lightbox(rng, headline, tag):
    img = _vgrad((W, H), (232, 240, 242), (196, 214, 218))
    img = _grid(img, 40, (150, 176, 182), 60)
    d = ImageDraw.Draw(img)

    # Four film panels along the top — the lightbox read, in one gesture.
    for i in range(4):
        x = 44 + i * 306
        panel = _scan_window(rng, 268, 214).point(lambda v: min(255, int(v * 1.5) + 40))
        img.paste(panel, (x, 40))
        d.rectangle([x, 40, x + 268, 254], outline=(120, 150, 158), width=3)
    # One panel holds the finding.
    hit = rng.randint(0, 3)
    hx = 44 + hit * 306 + 134
    d2 = ImageDraw.Draw(img)
    _ring(d2, hx, 147, 56, ALERT, width=9)

    d.rectangle([0, 292, W, 300], fill=TEAL)
    font, lines, lh = _fit_block(d, headline.upper(), FONT_BOLD, W - 110, 300, 108)
    y = 336
    for ln in lines:
        d.text((56, y), ln, font=font, fill=INK)
        y += lh
    _badge(d, tag, 56, H - 76, BONE, TEAL_DEEP)
    return img


def _anomaly(rng, headline, tag):
    img = _vgrad((W, H), (14, 62, 66), (9, 26, 34))
    img = _grid(img, 48, (90, 190, 180), 26)

    scan = _scan_window(rng, 560, 560)
    mask = Image.new("L", (560, 560), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, 559, 559], fill=255)
    img.paste(scan, (664, 80), mask)

    d = ImageDraw.Draw(img)
    d.ellipse([664, 80, 1223, 639], outline=(120, 214, 204), width=6)

    ax, ay = 1000, 300
    _ring(d, ax, ay, 74, ALERT, width=10)
    d.line([(ax - 74, ay + 40), (600, 470)], fill=ALERT, width=6)
    d.ellipse([592, 462, 608, 478], fill=ALERT)

    font, lines, lh = _fit_block(d, headline.upper(), FONT_BOLD, 560, 330, 96)
    y = 150
    for ln in lines:
        d.text((56, y + 4), ln, font=font, fill=(0, 0, 0))
        d.text((54, y), ln, font=font, fill=BONE)
        y += lh
    d.rectangle([56, y + 18, 56 + 240, y + 28], fill=TEAL)
    _badge(d, tag, 56, H - 84, INK, TEAL)
    return img


def _vitals(rng, headline, tag):
    img = _vgrad((W, H), (10, 30, 36), (6, 14, 18))
    img = _grid(img, 32, (60, 150, 150), 30)
    d = ImageDraw.Draw(img)

    glow = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    flat = rng.randint(880, 1010)
    _trace(gd, 0, W, 470, 150, rng, TEAL, 16, flatline_at=flat)
    img = Image.blend(img, glow.filter(ImageFilter.GaussianBlur(18)), 0.55)

    d = ImageDraw.Draw(img)
    _trace(d, 0, W, 470, 150, rng, (150, 255, 236), 7, flatline_at=flat)
    d.line([(flat, 470), (W, 470)], fill=ALERT, width=7)
    _ring(d, flat, 470, 52, ALERT, width=9, ticks=False)

    font, lines, lh = _fit_block(d, headline.upper(), FONT_BOLD, W - 120, 300, 104)
    y = 92
    for ln in lines:
        d.text((60, y + 5), ln, font=font, fill=(0, 0, 0))
        d.text((58, y), ln, font=font, fill=BONE)
        y += lh
    _badge(d, tag, 58, H - 86, INK, TEAL)
    return img


_RENDER = {"lightbox": _lightbox, "anomaly": _anomaly, "vitals": _vitals}


def pick_format(episode, history=None):
    """Rotate formats so consecutive episodes never look identical.

    history is the list of formats already used, newest last; the next pick
    is the least recently used one. Falls back to rotating on episode number.
    """
    if history:
        recent = [f for f in reversed(history) if f in FORMATS]
        for f in FORMATS:
            if f not in recent[:len(FORMATS) - 1]:
                return f
    return FORMATS[int(episode) % len(FORMATS)]


def render(headline, out_path, episode=1, fmt=None, history=None, seed=None):
    """Render one thumbnail. Returns the format actually used.

    headline should already be the short 3-6 word hook, not the video title —
    a title is written to be read, a thumbnail is written to be glanced at.
    """
    fmt = fmt or pick_format(episode, history)
    if fmt not in _RENDER:
        raise ValueError(f"unknown format {fmt!r}; expected one of {FORMATS}")
    rng = random.Random(seed if seed is not None else int(episode) * 7919)
    img = _RENDER[fmt](rng, headline, f"CASE {int(episode):02d}")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "JPEG", quality=92)
    return fmt
