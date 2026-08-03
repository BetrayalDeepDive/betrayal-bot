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
An earlier pass at this was clean, teal and geometric — a lightbox, a scan
window, a heart trace — and it had no human element anywhere in it. That is
the single largest lever on click-through, and without it the ceiling is
somewhere around three to five percent no matter how tidy the rest is. So
all three formats now put a BODY on the canvas, at scale, with the affected
part marked.

Two things make each one specific to its episode rather than a template with
the words swapped: the body part comes from what the case is actually about
(clinical_anatomy.shape_for), and the finding is filled in the colour the
case itself names (anomaly_colour) — a story about blue hands renders blue
hands, which is the strangest true thing the episode owns and the most
clickable.

  MARK   Bright bone field, body dark against it, the affected region in the
         case's colour and ringed. The light tile in a dark grid.
  SPLIT  The same body twice, normal beside affected, a red divider between
         and the headline in a band beneath. A comparison is the cheapest
         curiosity gap there is.
  COUNT  One enormous number — a digit survives shrinking further than any
         word, and "28 DAYS" asks a question that "a diagnostic delay" does
         not.

Everything is drawn here, from shapes and text. Nothing depends on an image
model returning something usable, which is what made the old path
unpredictable — and nothing here can generate a realistic-looking scene, so
the synthetic-media question does not arise (see synthetic_media_policy.py).

Each takes the same inputs and returns a 1280x720 JPEG.
"""
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

import clinical_anatomy as ca

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

FORMATS = ("mark", "split", "count")


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



def _paint_region(img, shape, box, colour, soft=True):
    """Fill the affected area of the body with the case's colour.

    Two things this has to get right, both of which the first version got
    wrong. The colour must be clipped to the SILHOUETTE, or it spills into
    the background as a rectangle that reads as a rendering bug rather than
    a finding. And the region mask must be soft-edged, or the finding has
    perfect square corners no scan or symptom ever had.

    Returns the region box so the caller can put the ring in the right place.
    """
    rb = ca.region_box(shape, box)
    # The body, in the finding's colour, transparent everywhere else.
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ca.draw_shape(ImageDraw.Draw(lay), shape, box, colour + (255,), detail=False)
    # The region, as a soft ellipse.
    reg = Image.new("L", img.size, 0)
    ImageDraw.Draw(reg).ellipse(rb, fill=255)
    if soft:
        reg = reg.filter(ImageFilter.GaussianBlur(radius=14))
    # Intersect: colour only where the body IS and the region says so.
    alpha = lay.split()[3].point(lambda v: 255 if v > 128 else 0)
    from PIL import ImageChops
    lay.putalpha(ImageChops.multiply(alpha, reg))
    img.paste(lay, (0, 0), lay)
    return rb


def _body(rng, headline, tag, shape, colour):
    """MARK — the body, the finding, three words.

    Bright bone field so the tile is the light one in a dark grid; the body
    dark against it; the affected region filled in the colour the case itself
    names, ringed. Everything a viewer needs to know something is wrong,
    before they have read a word.
    """
    img = _vgrad((W, H), (240, 245, 246), (203, 219, 222))
    img = _grid(img, 40, (152, 178, 184), 55)
    d = ImageDraw.Draw(img)

    box = (742, 22, 1258, 700)
    ca.draw_shape(d, shape, box, INK)

    # The finding, in the case's own colour, clipped to the body.
    rb = _paint_region(img, shape, box, colour)

    d = ImageDraw.Draw(img)
    cx, cy = (rb[0] + rb[2]) / 2, (rb[1] + rb[3]) / 2
    _ring(d, cx, cy, max(72, (rb[2] - rb[0]) * 0.46), ALERT, width=11)

    font, lines, lh = _fit_block(d, headline.upper(), FONT_BOLD, 660, 380, 118)
    y = (H - len(lines) * lh) // 2 - 30
    for ln in lines:
        d.text((56, y), ln, font=font, fill=INK)
        y += lh
    d.rectangle([56, y + 22, 356, y + 36], fill=ALERT)
    _badge(d, tag, 56, H - 84, BONE, TEAL_DEEP)
    return img


def _split(rng, headline, tag, shape, colour):
    """SPLIT — before and after, side by side, with the question between.

    A comparison is the cheapest curiosity gap there is: two of the same
    thing, one of them wrong, and the viewer wants to know which and why.

    The headline sits in a full-width band along the bottom rather than
    floating over the artwork: the first version put it across the top,
    where it landed straight on top of the anomaly marker and hid the one
    element the whole design exists to show.
    """
    img = _vgrad((W, H), (28, 40, 48), (12, 18, 24))
    d = ImageDraw.Draw(img)

    BAND = 468
    d.rectangle([0, 0, W // 2 - 4, BAND], fill=(232, 238, 240))
    d.rectangle([W // 2 + 4, 0, W, BAND], fill=(16, 22, 28))

    # Inset from the top: the anomaly ring is drawn OUTSIDE the region
    # box, so shapes flush to the edge get their marker cropped by the
    # frame -- which loses the single most important element.
    lbox = (120, 86, 500, 452)
    rbox = (786, 86, 1166, 452)
    ca.draw_shape(d, shape, lbox, (150, 164, 172))
    # Light enough to read against the dark half — the first version drew
    # it at (46,56,64) on a (20,28,34) field, which vanished.
    ca.draw_shape(d, shape, rbox, (78, 92, 104))

    rb = _paint_region(img, shape, rbox, colour)
    d = ImageDraw.Draw(img)
    _ring(d, (rb[0] + rb[2]) / 2, (rb[1] + rb[3]) / 2,
          max(62, (rb[2] - rb[0]) * 0.46), ALERT, width=11)
    d.rectangle([W // 2 - 5, 0, W // 2 + 5, BAND], fill=ALERT)

    d.rectangle([0, BAND, W, H], fill=(12, 18, 24))
    d.rectangle([0, BAND, W, BAND + 9], fill=ALERT)
    font, lines, lh = _fit_block(d, headline.upper(), FONT_BOLD, W - 260, 190, 96)
    y = BAND + (H - BAND - len(lines) * lh) // 2 + 4
    for ln in lines:
        d.text(((W - _text_w(d, ln, font)) // 2, y), ln, font=font, fill=BONE)
        y += lh
    _badge(d, tag, 30, H - 66, INK, TEAL)
    return img


def _count(rng, headline, tag, shape, colour):
    """COUNT — one enormous number, because numbers stop a scroll.

    A digit survives being shrunk further than any word, and "28 DAYS" asks
    a question that "a long diagnostic delay" does not.
    """
    num, rest = _split_number(headline)
    img = _vgrad((W, H), (14, 66, 70), (8, 22, 30))
    img = _grid(img, 48, (96, 196, 186), 30)
    d = ImageDraw.Draw(img)

    # (17,44,52) on this gradient was near-invisible — a silhouette has to
    # clear its background by more than a few values or it reads as a stain.
    box = (656, 30, 1268, 690)
    ca.draw_shape(d, shape, box, (44, 104, 108))
    rb = _paint_region(img, shape, box, colour)
    d = ImageDraw.Draw(img)
    _ring(d, (rb[0] + rb[2]) / 2, (rb[1] + rb[3]) / 2,
          max(64, (rb[2] - rb[0]) * 0.44), ALERT, width=10)

    if num:
        nf = _font(FONT_BOLD, 300)
        d.text((58, 96), num, font=nf, fill=ALERT)
        nb = d.textbbox((58, 96), num, font=nf)
        font, lines, lh = _fit_block(d, rest.upper(), FONT_BOLD, 620, 220, 88)
        y = nb[3] + 6
    else:
        font, lines, lh = _fit_block(d, headline.upper(), FONT_BOLD, 620, 380, 104)
        y = (H - len(lines) * lh) // 2 - 20
    for ln in lines:
        d.text((60, y + 4), ln, font=font, fill=(0, 0, 0))
        d.text((58, y), ln, font=font, fill=BONE)
        y += lh
    _badge(d, tag, 58, H - 84, INK, TEAL)
    return img


def _split_number(headline):
    """Pull a leading number out so COUNT can set it enormous."""
    words = headline.split()
    for i, w in enumerate(words):
        digits = "".join(c for c in w if c.isdigit())
        if digits and len(digits) <= 3:
            rest = " ".join(words[:i] + words[i + 1:])
            return digits, rest or headline
    return "", headline


_RENDER = {"mark": _body, "split": _split, "count": _count}


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


def render(headline, out_path, episode=1, fmt=None, history=None, seed=None,
           niche_name="", topic=""):
    """Render one thumbnail. Returns the format actually used.

    headline should already be the short 3-6 word hook, not the video title —
    a title is written to be read, a thumbnail is written to be glanced at.
    niche_name and topic decide WHICH body part is shown and what colour the
    finding is, so two episodes never look the same even in the same format.
    """
    fmt = fmt or pick_format(episode, history)
    if fmt not in _RENDER:
        raise ValueError(f"unknown format {fmt!r}; expected one of {FORMATS}")
    rng = random.Random(seed if seed is not None else int(episode) * 7919)
    shape = ca.shape_for(niche_name, f"{topic} {headline}")
    colour = ca.anomaly_colour(f"{topic} {headline}")
    img = _RENDER[fmt](rng, headline, f"CASE {int(episode):02d}", shape, colour)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "JPEG", quality=92)
    return fmt
