"""
Photographic thumbnails for the clinical channel.

WHAT CHANGED, AND WHY
---------------------
The first version of this drew its subjects: a lightbox, a heart, a flatline,
all as flat polygons. Held next to a real medical channel's thumbnail it read
as a diagram, and a diagram is something a viewer scrolls past. The rule now is
absolute: EVERY pictorial element on the card is a photograph. Nothing here
depicts an object. The only marks this module draws are annotation -- a ring, an
arrow, a cross -- which is what a clinician does ON a photograph, not instead of
one.

THE GRAMMAR
-----------
Pulled off six thumbnails from channels that already work in this niche. All
six shared the same five things, and none of them is a stylistic preference:

  1. The background is a real photograph.
  2. The presenter is cut out with a hard white stroke, 6-10px. The stroke is
     what makes a photographed person read as a graphic element rather than as
     a second, competing photograph.
  3. Text sits in a filled box or a bubble with a heavy black outline. Bare
     text on a photograph disappears -- the photograph has every value in it,
     so there is no colour that contrasts everywhere.
  4. One curved arrow points at the thing.
  5. Saturated yellow, red and white. Not the muted channel teal, which is a
     video palette and vanishes at 120px.

WORDS
-----
The loud element is a clinical fact, not a brand: BEFORE, DAY 9, 0.4 mm,
NEGATIVE. The channel name is never the headline -- a viewer who already knows
the channel does not need telling, and one who does not is not persuaded by it.
Twelve characters is the working ceiling for the loudest element; past that the
type has to shrink to fit and the shrink is what actually costs the click.

SIZE
----
Every format is checked at 120px, because that is what most of the audience
sees. The check is in the render path, not in a test, so a format that fails it
cannot ship quietly.
"""
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import presenter_cutout as pcut

W, H = 1280, 720

YELLOW = (255, 209, 26)
RED = (219, 30, 38)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
INK = (14, 17, 21)

_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
_COND = "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf"

# The five in rotation, chosen by the channel owner from a set of six. Four
# carry the channel and `banner` is the fifth, kept as a change of pace.
#
# `hero` -- one photographed organ filling the frame -- is implemented and
# tested but deliberately NOT in this tuple. It was not chosen. It stays in the
# code because putting it back is a one-word edit, and because its organ search
# terms are what the other formats now use to find a real heart or a real brain
# rather than an illustration of one.
FORMATS = ("reaction", "bubbles", "pointing", "verdict", "banner")
ALL_FORMATS = ("reaction", "bubbles", "pointing", "verdict", "banner", "hero")

# Which pose register suits each format's job. The presenter is reacting to the
# evidence in some formats and presenting it in others, and those are different
# faces.
_POSES = {
    "reaction": ("surprise", "concern", "confusion"),
    "bubbles":  ("confusion", "skepticism", "curiosity"),
    "pointing": ("directing",),
    "verdict":  ("skepticism", "suspicion", "authority"),
    "hero":     ("concern", "grief"),
    "banner":   ("concern", "resolve", "authority"),
}

# What to ask Pixabay/Pexels for, per role. Ordered most specific first, the
# same way the stock-footage search is ordered, so a real match wins and the
# generic term is only a floor.
SEARCH_TERMS = {
    "scene": ["hospital corridor", "hospital ward night", "emergency department",
              "clinic hallway", "hospital"],
    "evidence": ["mri brain scan", "ct scan film", "blood sample tube",
                 "laboratory blood test", "medical scan"],
    "hero": ["human eye macro", "eye close up", "iris macro", "human eye"],
}

# When the case is about an organ, the evidence photograph should BE that organ.
#
# The trap is that "heart" on a stock search returns valentines, and "heart
# anatomy" returns the vintage engraving and the vector diagram -- both
# drawings, which is the one thing barred here. Every term below is worded to
# pull a photograph: a specimen, a model, a surgical still, a scan of the real
# organ. The word "illustration" never appears, and `_looks_drawn()` throws out
# anything that slips through anyway.
ORGAN_TERMS = {
    "heart":    ["human heart specimen", "cardiac surgery operating", "heart mri scan",
                 "cardiology ultrasound screen"],
    "brain":    ["brain mri scan", "human brain specimen", "neurosurgery operating",
                 "brain ct scan film"],
    "lung":     ["chest x-ray film", "lung ct scan", "thoracic surgery operating"],
    "liver":    ["liver ultrasound screen", "abdominal ct scan", "liver biopsy sample"],
    "kidney":   ["kidney ultrasound screen", "dialysis machine patient",
                 "renal ct scan"],
    "eye":      ["human eye macro", "retina fundus photograph", "eye examination slit lamp"],
    "skin":     ["dermatology examination skin", "skin lesion close up photograph"],
    "bone":     ["bone x-ray film", "orthopaedic x-ray", "skeleton radiograph"],
    "blood":    ["blood sample tube", "blood smear microscope", "laboratory blood test"],
    "stomach":  ["endoscopy screen", "abdominal ultrasound screen"],
    "spine":    ["spine mri scan", "spinal x-ray film"],
    "thyroid":  ["thyroid ultrasound screen", "neck examination doctor"],
    "pancreas": ["abdominal ct scan", "endoscopy screen"],
    "muscle":   ["muscle biopsy microscope", "physiotherapy examination"],
    "nerve":    ["nerve conduction test", "neurology examination patient"],
}


def organ_terms(text):
    """Search terms for whichever organ this episode is actually about.

    Returns [] when the case names no organ, so the caller falls through to the
    generic clinical terms rather than forcing an organ that has nothing to do
    with the story.
    """
    low = (text or "").lower()
    out = []
    for organ, terms in ORGAN_TERMS.items():
        if organ in low:
            out.extend(terms)
    return out


# ── where the card is allowed to put anything that matters ─────────────
#
# YouTube stamps the video's duration over the bottom-right corner of every
# thumbnail in every feed. It is not optional and it is not previewed in the
# upload dialog, so it is invisible until the video is live -- which is exactly
# how a headline ends up with its last word covered by "12:47". Measured at
# roughly 90x34px at 1280x720, and the guidance is to keep anything that
# matters 150x60 clear of the corner.
#
# The rest is the standard safe area: feeds, cards and TV crop differently, so
# critical content stays inside a 90px inset.
SAFE = (90, 90, 1190, 630)
BADGE = (1060, 640, 1280, 720)

# The one element that never moves. Channels that are recognised in a feed keep
# roughly 80% of the card fixed and vary the rest; this red case chip, always
# the same colour in the same corner, is this channel's fixed part. It is worth
# more than it looks: a returning viewer identifies the channel before reading
# a single word.
BRAND_AT = (96, 96)

# Words in the headline. Three or fewer tests best, and three to five is the
# band where the gain still holds; past that the type has to shrink to fit and
# the shrink is what costs the click, so the cap is enforced rather than
# advised.
MAX_WORDS = 5

# Outline on the presenter. It was 9px, which is the reference channels' look
# but reads as a sticker pasted onto the scene -- the channel owner asked for
# him to sit IN the photograph, not on top of it. At 3px the edge still
# separates him from a busy background at 120px, but at full size it reads as
# depth of field rather than as a border. The shadow does more of the work now,
# which is what actually makes something look like it is standing in a room.
STROKE = 2
SHADOW = 0.66

# Filler that carries no meaning at a glance. Dropping these is what turns
# "IT WAS IN THE FIRST BLOOD TEST" (seven words, small type) into
# "IN THE FIRST BLOOD TEST" and then "FIRST BLOOD TEST" (three words, huge).
_FILLER = ("the", "a", "an", "of", "to", "in", "on", "at", "it", "is", "was",
           "were", "that", "this", "and", "for", "with", "his", "her", "their")


def trim_words(text, cap=MAX_WORDS):
    """Cut a headline to `cap` words, dropping filler before content.

    Truncating from the end would throw away the payload -- the last word of a
    clinical headline is usually the finding. Filler goes first, and only if
    that is not enough does the tail go.
    """
    words = [w for w in (text or "").split() if w]
    if len(words) <= cap:
        return " ".join(words)
    keep = [w for w in words if w.lower().strip(".,;:") not in _FILLER]
    if len(keep) > cap:
        keep = keep[-cap:]          # the finding sits at the end
    return " ".join(keep or words[:cap])


def _font(path, size):
    return ImageFont.truetype(path, size)


# ── type ───────────────────────────────────────────────────────────────

def _measure(d, text, font, ow):
    b = d.textbbox((0, 0), text, font=font, stroke_width=ow)
    return b[2] - b[0], b[3] - b[1]


def _heavy(text, font, weight, ow):
    """Render text as a genuinely fatter letterform, plus its outline.

    Returns (fill_mask, outline_mask) as L-mode images.

    This machine has no display face -- DejaVu and Liberation are text faces,
    and the thumbnails that work in this niche are set in something like Anton:
    very heavy, very condensed. Anton is free, but the proxy blocks GitHub and
    PyPI has no package carrying it, so it cannot be fetched.

    Rather than fake the weight with a thick outline -- which reads as a thin
    letter wearing a border -- the glyphs are dilated in raster space. That is
    what emboldening physically IS: the outline offset outwards. The stems
    genuinely thicken, the counters genuinely close up, and the result is a
    display weight rather than a text weight with decoration.
    """
    pad = weight + ow + 8
    tmp = Image.new("L", (1, 1))
    b = ImageDraw.Draw(tmp).textbbox((0, 0), text, font=font)
    w, h = b[2] - b[0] + pad * 2, b[3] - b[1] + pad * 2
    m = Image.new("L", (max(1, w), max(1, h)), 0)
    ImageDraw.Draw(m).text((pad - b[0], pad - b[1]), text, font=font, fill=255)

    def grow(im, px):
        for _ in range(max(0, int(round(px / 2)))):
            im = im.filter(ImageFilter.MaxFilter(5))
        return im

    fill = grow(m, weight)
    return fill, grow(fill, ow)


def _draw_heavy(img, xy, text, font, colour, weight=6, ow=9, outline=BLACK,
                anchor="la"):
    """Paste heavy outlined caps onto img. Returns the box it occupied."""
    fill, out = _heavy(text, font, weight, ow)
    x, y = xy
    if anchor[0] == "m":
        x -= out.width // 2
    elif anchor[0] == "r":
        x -= out.width
    if anchor[1] == "b":
        y -= out.height
    img.paste(Image.new("RGB", out.size, outline), (x, y), out)
    img.paste(Image.new("RGB", fill.size, colour), (x, y), fill)
    return (x, y, x + out.width, y + out.height)


def _fit(d, lines, path, box_w, box_h, start, ow, lead=1.02, floor=22):
    """Largest size at which every line fits the width and the block fits the
    height. Measured WITH the outline, because the outline is what actually
    overran the frame the last time this was done by eye."""
    size = start
    while size > floor:
        f = _font(path, size)
        wide = max(_measure(d, ln, f, ow)[0] for ln in lines)
        tall = len(lines) * int(size * lead) + ow * 2
        if wide <= box_w and tall <= box_h:
            return f
        size -= 2
    return _font(path, floor)


def _caps(d, xy, text, font, fill, ow=7, outline=BLACK, anchor="la"):
    d.text(xy, text, font=font, fill=fill, anchor=anchor,
           stroke_width=ow, stroke_fill=outline)


def _block(img, lines, path, box, fill, start=120, ow=None, align="left",
           weight=6, anchor_bottom=True):
    """A heavy caps block fitted into box.

    Bottom-anchored by default: a headline sitting on the floor of its box is
    predictable, whereas a top-anchored one moves up and down the card as the
    fitted size changes, which is how a two-line headline ends up overlapping
    whatever is below it.
    """
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = box
    f = _fit(d, lines, path, x1 - x0, y1 - y0, start, (ow or 9) + weight)

    # Weight has to be a FRACTION of the size, not a pixel count. A flat 6px
    # dilation is invisible on 110pt type and closes every counter on 40pt --
    # "EVERY TEST CAME BACK CLEAN" came out as a solid white blob with no
    # letters in it at all, while "NINE MONTHS APART" on the same setting was
    # fine. Emboldening is proportional in every real type family, and 5.5% of
    # the em is about the step from a bold to a black.
    weight = max(2, int(round(f.size * 0.055)))
    # ow=0 means the caller wants no outline at all -- black caps on the yellow
    # banner, where an outline is the same colour as the type and welds the
    # whole line into one black slab. Only "unspecified" gets the auto value.
    ow = 0 if ow == 0 else max(3, int(round(f.size * 0.085)))
    lead = int(f.size * 1.06) + weight
    total = lead * len(lines)
    y = (y1 - total) if anchor_bottom else y0
    for ln in lines:
        x = x0 if align == "left" else (x0 + x1) // 2
        _draw_heavy(img, (x, y), ln, f, fill, weight=weight, ow=ow,
                    anchor="la" if align == "left" else "ma")
        y += lead
    return y


def _label(d, text, xy, bg, fg=BLACK, size=44, pad=(20, 10), ow=5, anchor="lt"):
    """Filled box with a heavy black outline. The reference format's workhorse:
    it is legible over any photograph because it replaces the photograph."""
    f = _font(_BOLD, size)
    tw, th = _measure(d, text, f, 0)
    x, y = xy
    bw, bh = tw + pad[0] * 2, th + pad[1] * 2 + int(size * 0.28)
    if anchor[0] == "r":
        x -= bw
    elif anchor[0] == "c":
        x -= bw // 2
    if anchor[1] == "b":
        y -= bh
    elif anchor[1] == "c":
        y -= bh // 2
    d.rectangle([x, y, x + bw, y + bh], fill=bg, outline=BLACK, width=ow)
    d.text((x + bw // 2, y + bh // 2), text, font=f, fill=fg, anchor="mm")
    return (x, y, x + bw, y + bh)


# ── annotation: what a clinician puts ON a photograph ──────────────────

def _hand(rng, pts, jitter=2.4):
    """Nudge a path off true so a mark reads as drawn by a hand rather than
    generated. A geometrically perfect ring reads as a UI element."""
    return [(x + rng.uniform(-jitter, jitter), y + rng.uniform(-jitter, jitter))
            for x, y in pts]


def _ring(d, cx, cy, rx, ry, colour=RED, width=11, rng=None, sweep=1.08):
    rng = rng or random.Random(7)
    n = 64
    span = 2 * math.pi * sweep
    a0 = rng.uniform(0, 2 * math.pi)
    pts = [(cx + rx * math.cos(a0 + span * i / n) * (1 + 0.03 * math.sin(i * 0.7)),
            cy + ry * math.sin(a0 + span * i / n) * (1 + 0.03 * math.cos(i * 0.5)))
           for i in range(n + 1)]
    d.line(_hand(rng, pts, 2.0), fill=colour, width=width, joint="curve")


def _cross(d, cx, cy, r, colour=RED, width=22, rng=None):
    rng = rng or random.Random(11)
    for a, b in (((-1, -1), (1, 1)), ((1, -1), (-1, 1))):
        p = [(cx + a[0] * r * (1 - t) + b[0] * r * t,
              cy + a[1] * r * (1 - t) + b[1] * r * t) for t in
             [i / 12.0 for i in range(13)]]
        d.line(_hand(rng, p, 3.0), fill=colour, width=width, joint="curve")


def _arrow(d, p0, p1, bend=0.32, colour=YELLOW, width=13, head=34, rng=None):
    """One curved arrow, drawn as a quadratic through a bent control point."""
    rng = rng or random.Random(3)
    mx, my = (p0[0] + p1[0]) / 2.0, (p0[1] + p1[1]) / 2.0
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    cx, cy = mx - dy * bend, my + dx * bend
    pts = []
    for i in range(41):
        t = i / 40.0
        u = 1 - t
        pts.append((u * u * p0[0] + 2 * u * t * cx + t * t * p1[0],
                    u * u * p0[1] + 2 * u * t * cy + t * t * p1[1]))
    # Outline first, then the fill: the same trick the type uses, and for the
    # same reason -- a bare yellow line vanishes over a bright photograph.
    d.line(_hand(rng, pts, 1.2), fill=BLACK, width=width + 8, joint="curve")
    d.line(pts, fill=colour, width=width, joint="curve")

    ang = math.atan2(pts[-1][1] - pts[-4][1], pts[-1][0] - pts[-4][0])
    tip = pts[-1]
    wing = [(tip[0] - head * math.cos(ang + s), tip[1] - head * math.sin(ang + s))
            for s in (0.46, -0.46)]
    d.polygon([tip, wing[0], wing[1]], fill=colour, outline=BLACK, width=5)


def _bubble(d, text, cx, cy, tail, size=46, bg=YELLOW, fg=BLACK, max_w=420):
    """Speech bubble with a heavy outline and a tail toward `tail`."""
    f = _font(_BOLD, size)
    words, lines, cur = text.split(), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if _measure(d, t, f, 0)[0] <= max_w:
            cur = t
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    tw = max(_measure(d, ln, f, 0)[0] for ln in lines)
    lead = int(size * 1.16)
    bw, bh = tw + 56, lead * len(lines) + 44
    x0, y0 = cx - bw // 2, cy - bh // 2

    ang = math.atan2(tail[1] - cy, tail[0] - cx)
    base = (cx + math.cos(ang) * bw * 0.32, cy + math.sin(ang) * bh * 0.42)
    perp = ang + math.pi / 2
    tri = [(base[0] + math.cos(perp) * 26, base[1] + math.sin(perp) * 26),
           (base[0] - math.cos(perp) * 26, base[1] - math.sin(perp) * 26), tail]
    d.polygon(tri, fill=bg, outline=BLACK, width=6)
    d.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], radius=26, fill=bg,
                        outline=BLACK, width=6)
    y = y0 + 22
    for ln in lines:
        d.text((cx, y), ln, font=f, fill=fg, anchor="ma")
        y += lead


# ── photographs ────────────────────────────────────────────────────────

def looks_drawn(path, limit=0.75):
    """True if this file is an illustration rather than a photograph.

    A stock search for "human heart" returns diagrams, and a diagram is the one
    thing this module is barred from putting on a card. The search terms are
    worded to avoid them, but wording is a request, not a guarantee, so the
    downloaded file is checked.

    The test is for sensor noise. A camera never produces two neighbouring
    pixels that are EXACTLY equal -- there is always grain -- while a vector
    drawing is made of flat fills where nearly every neighbour is identical.
    Measured on the reference set: the flat diagrams and the cartoon score
    89-98%, and the twelve photographs top out at 59% (a greyscale CT sheet,
    which is as close to flat as a real photograph gets).

    Its blind spot, stated plainly: a SCANNED drawing -- an old engraving --
    carries the scanner's own grain and reads as a photograph, 21% on the
    vintage heart plate. Nothing in the pixels separates that from a
    photograph of a painting. The defence against it is the search wording
    ("specimen", "surgery", "scan" rather than "anatomy"), and the human
    review gate behind that.
    """
    try:
        im = Image.open(path).convert("RGB")
    except Exception:
        return False
    if im.width > 1400:
        x = (im.width - 1400) // 2
        im = im.crop((x, 0, x + 1400, im.height))
    a = np.asarray(im).astype(np.int16)
    if a.shape[1] < 2:
        return False
    return float((np.abs(np.diff(a, axis=1)).sum(axis=2) == 0).mean()) >= limit


def resolve_photos(fetch, topic, niche_name, work_dir, roles=("scene", "evidence"),
                   log=print):
    """Download one usable photograph per role. Returns {role: path}.

    `fetch(query, niche_name, out_path) -> (ok, kind)` is injected rather than
    imported so this module stays independent of any one channel's pipeline;
    Ch1 passes its own fetch_case_relevant_image, which already walks
    Wikimedia Commons, then Pixabay, then Pexels, then an image model.

    For the evidence role the episode's own subject comes first, so a case
    about a heart gets a photograph of a heart rather than generic glassware.
    """
    import stock_library as sl

    out = {}
    all_terms = {}
    for role in roles:
        terms = list(SEARCH_TERMS.get(role, []))
        if role == "evidence":
            terms = (organ_terms(topic) or []) + [topic] + terms
        all_terms[role] = terms
        path = os.path.join(str(work_dir), "thumb_%s.jpg" % role)
        for q in terms:
            if not q:
                continue
            try:
                ok, _kind = fetch(q, niche_name, path)
            except Exception as e:
                log("    thumbnail photo '%s' (non-fatal): %s" % (q, e))
                continue
            if not ok or not os.path.exists(path):
                continue
            if looks_drawn(path):
                log("    thumbnail photo '%s' rejected: it is a drawing" % q)
                continue
            out[role] = path
            log("    thumbnail photo [%s]: '%s'" % (role, q))
            break

        # Nothing came back for this role: a rate limit, a dead key, a network
        # blip, or a search that returned only diagrams. The library is what
        # stops any of those turning into a drawn thumbnail.
        if role not in out:
            local = sl.pick(role, terms, seed=hash(topic or "") & 0xffff)
            if local:
                out[role] = local
                log("    thumbnail photo [%s]: from the local library "
                    "(the search returned nothing usable)" % role)

    # Top the library up with whatever this episode's searches found. Small,
    # so it compounds over weeks rather than hammering the free tier now.
    try:
        n = sl.harvest(fetch, all_terms, work_dir, verify=looks_drawn, log=log)
        if n:
            log("    stock library: %d new, %d held" % (n, sl.count()))
    except Exception as e:
        log("    stock library harvest (non-fatal): %s" % e)
    return out


def _cover(path, w, h, focus=0.5):
    """Crop-to-cover, never stretch. focus is the horizontal centre of interest."""
    im = Image.open(path).convert("RGB")
    s = max(w / im.width, h / im.height)
    im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))),
                   Image.LANCZOS)
    x = int((im.width - w) * focus)
    y = max(0, (im.height - h) // 3)      # faces and detail sit above centre
    return im.crop((x, y, x + w, y + h))


def _focus_point(im, zone=(0.0, 0.0, 1.0, 1.0), prefer="detail", min_salience=2.1,
                 centre_bias=False):
    """Where in this photograph the mark should go, or None if nowhere.

    Hard-coding the ring's coordinates works exactly once, for the photograph
    you had in front of you. In production the photograph comes back from a
    Pixabay search, so the syringe is wherever it happens to be -- and a ring
    drawn at a fixed point lands on empty wall, which is worse than no ring at
    all because it tells the viewer there is something to see and there isn't.

    "detail" finds the busiest region: an instrument, a lesion, a hand at work.
    "dark" finds the darkest compact one, which on a macro of an eye is the
    pupil. Both run on a thumbnail of the photograph, because the answer wanted
    is a region, not a pixel.
    """
    gw, gh = 240, 135
    g = np.asarray(im.convert("L").resize((gw, gh), Image.LANCZOS)).astype(np.float32)
    if prefer == "dark":
        # Difference of Gaussians, not plain darkness. Plain darkness picks the
        # single darkest pixel, which on an eye macro is the shadow in the
        # outer corner -- it put the ring on bare skin. A DoG asks the useful
        # question instead: which region is dark COMPARED WITH WHAT SURROUNDS
        # IT. That is a pupil, and it is a lesion on a scan.
        def blur(k):
            return np.asarray(Image.fromarray(g.astype(np.uint8))
                              .filter(ImageFilter.GaussianBlur(k))).astype(np.float32)
        field = np.clip(blur(21) - blur(4), 0, None)
    else:
        field = (np.abs(np.diff(g, axis=1, prepend=g[:, :1]))
                 + np.abs(np.diff(g, axis=0, prepend=g[:1, :])))
        field = np.asarray(Image.fromarray(np.clip(field, 0, 255).astype(np.uint8))
                           .filter(ImageFilter.GaussianBlur(7))).astype(np.float32)

    if centre_bias:
        # A tie-break toward the middle. On a macro of an eye the pupil and the
        # shadow under the brow are both dark blobs; the one the photograph is
        # about is the one near the centre of the frame.
        yy, xx = np.mgrid[0:gh, 0:gw]
        r2 = ((xx / gw - 0.5) ** 2 + (yy / gh - 0.5) ** 2)
        field = field * np.exp(-r2 / 0.10)

    x0, y0, x1, y1 = zone
    m = np.zeros_like(field)
    m[int(y0 * gh):max(1, int(y1 * gh)), int(x0 * gw):max(1, int(x1 * gw))] = 1.0
    sel = field * m
    peak = float(sel.max())

    # Is there anything here worth ringing? An empty corridor has a busiest
    # region too -- a door frame -- and a ring drawn on it promises the viewer
    # a finding that does not exist, which is worse than no ring at all. So the
    # peak has to stand clear of the rest of the zone or the caller gets None
    # and draws nothing.
    inside = sel[m > 0]
    if peak <= 0 or peak < min_salience * float(inside.mean() + 1e-6):
        return None

    yy, xx = np.unravel_index(int(np.argmax(sel)), field.shape)
    return int((xx + 0.5) / gw * W), int((yy + 0.5) / gh * H)


def _recede(im, blur=2.0, dark=0.74, tint=(0.94, 0.99, 1.05)):
    """Push a photograph back a little, without throwing it away.

    The first version pushed it back so far that the picture stopped being a
    picture: a corridor blurred by 8 and dimmed to 46% is a grey smear, and a
    viewer cannot tell it is a hospital, which is the only reason it was there.
    The background still has to lose to the face, but losing is not the same as
    being unreadable, so both numbers are now much gentler and the separation
    comes from the white stroke and the shadow instead.
    """
    a = np.asarray(im.filter(ImageFilter.GaussianBlur(blur))).astype(np.float32)
    a *= dark
    a *= np.array(tint, np.float32)
    return np.clip(a, 0, 255)


def _panel(canvas, photo_path, box, rot=0.0, stroke=10, blur=0.0):
    """A photograph inset with a hard white stroke, optionally rotated.

    The stroke and the tilt are what stop an inset reading as a hole cut in the
    card. Both come straight from the reference thumbnails.
    """
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    im = _cover(photo_path, w, h)
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    # No frame. The white border and the black keyline were drawn lines on a
    # photograph, and a drawn line is exactly what this module is not allowed
    # to put on a picture. The shadow alone lifts the inset off the background,
    # which is what the frame was there to do.
    pad = 0
    card = im.convert("RGBA")
    if rot:
        card = card.rotate(rot, Image.BICUBIC, expand=True)
    base = Image.fromarray(canvas.astype(np.uint8))
    # Offset the shadow down and right. Centred on the card it is a halo, which
    # reads as a glow; offset, it reads as a print lying on the scene, and that
    # is what makes the inset sit ON the card rather than IN it.
    sh = Image.new("RGBA", base.size, (0, 0, 0, 0))
    sh.paste(card, (x0 - pad + 12, y0 - pad + 14), card)
    sh = sh.filter(ImageFilter.GaussianBlur(16))
    base.paste(Image.new("RGB", base.size, BLACK), (0, 0),
               sh.split()[3].point(lambda v: int(v * 0.55)))
    base.paste(card, (x0 - pad, y0 - pad), card)
    return np.asarray(base.convert("RGB")).astype(np.float32)


# ── the six formats ────────────────────────────────────────────────────
#
# Each one gets the canvas, a copy of the spec, and an rng. Each returns the
# canvas. Layout constants are chosen so the presenter's column and the text's
# column cannot overlap -- the overlap is prevented by the geometry rather than
# detected afterwards, because a check that runs afterwards has nothing to do
# about it except shrink the type.

# ── the channel mark ───────────────────────────────────────────────────

# Same ring-and-single-ECG-beat as the channel avatar, drawn small in the
# corner. Reusing the avatar's mark rather than inventing a second one is the
# point: a viewer who has seen the channel once recognises the card before
# reading it, and the mark is doing brand work rather than watermark work.
MARK_TEAL = (95, 168, 160)


def _mark(im, size=58, pad=26):
    """Channel mark, bottom right, clear of YouTube's duration badge.

    The badge covers the true corner, so a mark placed there would be hidden
    in every feed -- which is the opposite of what a mark is for. It sits at
    the bottom-right of the SAFE area instead: still bottom right to the eye,
    still visible everywhere.
    """
    x1, y1 = SAFE[2] - pad, SAFE[3] - pad
    x0, y0 = x1 - size, y1 - size
    plate = Image.new("RGBA", (size * 3, size * 3), (0, 0, 0, 0))
    d = ImageDraw.Draw(plate)
    s3 = size * 3

    # A soft dark disc under it so the mark survives a bright photograph
    # without needing an opaque box, which would read as a sticker.
    d.ellipse([0, 0, s3 - 1, s3 - 1], fill=(10, 14, 18, 150))
    d.ellipse([9, 9, s3 - 10, s3 - 10], outline=MARK_TEAL + (235,), width=7)

    # One beat: flat, up, down, flat. Unmistakably medical at any size.
    cx, cy, sp = s3 / 2.0, s3 / 2.0, s3 * 0.46
    pts = [(cx - sp / 2, cy), (cx - sp * 0.18, cy), (cx - sp * 0.07, cy - sp * 0.30),
           (cx + sp * 0.05, cy + sp * 0.26), (cx + sp * 0.16, cy), (cx + sp / 2, cy)]
    d.line(pts, fill=(238, 244, 246, 245), width=9, joint="curve")

    plate = plate.resize((size, size), Image.LANCZOS)
    im.paste(plate, (x0, y0), plate)


def _shoulder(head_at, head_h, side=1):
    """Roughly where the presenter's near shoulder is, for anchoring an arrow.

    An arrow that starts in empty air is a floating graphic; one that starts at
    his shoulder reads as HIM indicating the thing, which is the whole point of
    having a person on the card.
    """
    return (int(W * head_at[0] + side * head_h * 0.62),
            int(H * head_at[1] + head_h * 0.62))


def _f_reaction(spec, rng):
    """Presenter reacts; the evidence sits beside him, marked."""
    box = (628, 100, 1150, 424)
    c = _recede(_cover(spec["scene"], W, H), blur=3.0, dark=0.62)
    c = _panel(c, spec["evidence"], box, rot=-2.2)
    head_at = (0.19, 0.33)
    c = pcut.stand(c, spec["pose"], head_h=300, head_at=head_at,
                   mirror=spec.get("mirror", False), stroke=STROKE, shadow=SHADOW)
    im = Image.fromarray(c.astype(np.uint8))
    d = ImageDraw.Draw(im)

    # The mark goes where the panel photograph is actually busiest, mapped back
    # out of the panel's own crop into card coordinates.
    # A low bar here on purpose. The evidence role is a clinical still by
    # construction -- a scan sheet, a tube, a pair of hands -- so there is
    # always something on it worth ringing, and a sheet of 24 near-identical
    # slices has a flat saliency field precisely BECAUSE it is all findings.
    at = _focus_point(_cover(spec["evidence"], box[2] - box[0], box[3] - box[1]),
                      zone=(0.24, 0.26, 0.80, 0.76), min_salience=1.25)
    if at:
        mx = box[0] + int(at[0] / float(W) * (box[2] - box[0]))
        my = box[1] + int(at[1] / float(H) * (box[3] - box[1]))
        _ring(d, mx, my, 96, 78, rng=rng)
        _arrow(d, _shoulder(head_at, 300), (mx - 112, my - 20), bend=-0.24, rng=rng)
    if spec.get("mark"):
        _label(d, spec["mark"], (1178, 108), YELLOW, size=46, anchor="rt")
    _label(d, spec["kicker"], BRAND_AT, RED, fg=WHITE, size=34)

    _block(im, spec["lines"], _COND, (470, 448, 1040, 618), WHITE, start=92)
    _mark(im)
    return np.asarray(im).astype(np.float32)


def _f_bubbles(spec, rng):
    """What everyone said, in their own boxes, over a real corridor."""
    c = _recede(_cover(spec["scene"], W, H), blur=2.6, dark=0.66)
    c = pcut.stand(c, spec["pose"], head_h=310, head_at=(0.27, 0.36),
                   mirror=spec.get("mirror", False), stroke=STROKE, shadow=SHADOW)
    im = Image.fromarray(c.astype(np.uint8))
    d = ImageDraw.Draw(im)

    # Tails aim down and away, never back at him. Pointed at his head they put
    # a white spike through his ear -- and they would be wrong anyway: these are
    # what everyone ELSE said to the patient, not what he is saying.
    #
    # Two bubbles and NO separate headline. With one as well the card carried
    # four things competing for the same second -- face, bubble, bubble,
    # headline -- and two or three is the working limit. The second bubble IS
    # the headline, so nothing is lost: the dismissal sets it up and the
    # episode's own line lands underneath it.
    quotes = spec["quotes"][:2]
    _bubble(d, quotes[0], 900, 162, (836, 292), size=50, bg=WHITE, max_w=430)
    if len(quotes) > 1:
        _bubble(d, quotes[1], 934, 424, (876, 548), size=50, bg=YELLOW, max_w=430)
    _label(d, spec["kicker"], BRAND_AT, RED, fg=WHITE, size=34)
    _mark(im)
    return np.asarray(im).astype(np.float32)


def _f_pointing(spec, rng):
    """He points at the thing, and the thing is a photograph of the thing."""
    shot = _cover(spec["evidence"], W, H, focus=0.38)
    c = _recede(shot, blur=1.2, dark=0.84)
    head_at = (0.77, 0.35)
    c = pcut.stand(c, "directing", head_h=286, head_at=head_at, mirror=True,
                   stroke=STROKE, shadow=SHADOW)
    im = Image.fromarray(c.astype(np.uint8))
    d = ImageDraw.Draw(im)

    # Upper left only. He stands on the right, so a ring further right would
    # circle his own shoulder; and the headline owns the bottom strip, so a
    # ring low down drags its label into the type.
    at = _focus_point(shot, zone=(0.08, 0.16, 0.48, 0.62), min_salience=1.4)
    mx, my = at if at else (356, 300)
    if at:
        _ring(d, mx, my, 112, 96, rng=rng)
    # No arrow on this one. His arm already IS the arrow, and the drawn one ran
    # from his shoulder to a point his own hand was covering -- a yellow stub
    # with no visible start and no visible end. Two elements beat three.
    if spec.get("mark"):
        # Below the ring if there is room above the headline, otherwise above
        # it. Choosing by measurement rather than by a fixed offset is what
        # stops "0.4 mmol/L" being printed through the word BLOOD.
        below = my + 150
        _label(d, spec["mark"], (mx, below if below < 500 else my - 128),
               YELLOW, size=48, anchor="ct")
    _label(d, spec["kicker"], BRAND_AT, RED, fg=WHITE, size=34)
    _block(im, spec["lines"], _COND, (92, 440, 660, 616), WHITE, start=88)
    _mark(im)
    return np.asarray(im).astype(np.float32)


def _f_verdict(spec, rng):
    """Two states of the same patient, and a mark over the one that matters."""
    a = (338, 92, 786, 424)
    b = (818, 92, 1246, 424)
    c = _recede(_cover(spec["scene"], W, H), blur=6.0, dark=0.44)
    c = _panel(c, spec["evidence"], a, rot=1.6)
    c = _panel(c, spec.get("evidence_b") or spec["evidence"], b, rot=-1.6)
    # He belongs on this one too. Without a face the card is two documents, and
    # a channel whose thumbnails have no person in them has nothing for a
    # returning viewer to recognise in a feed.
    c = pcut.stand(c, spec["pose"], head_h=236, head_at=(0.12, 0.46),
                   mirror=False)
    im = Image.fromarray(c.astype(np.uint8))
    d = ImageDraw.Draw(im)

    _label(d, spec["state_a"], ((a[0] + a[2]) // 2, a[1] + 18), WHITE, size=40,
           anchor="ct")
    _label(d, spec["state_b"], ((b[0] + b[2]) // 2, b[1] + 18), WHITE, size=40,
           anchor="ct")
    _cross(d, (b[0] + b[2]) // 2, (b[1] + b[3]) // 2, 128, rng=rng)
    _label(d, spec["kicker"], BRAND_AT, RED, fg=WHITE, size=34)
    _block(im, spec["lines"], _COND, (92, 452, 1046, 618), WHITE, start=104,
           align="centre")
    _mark(im)
    return np.asarray(im).astype(np.float32)


def _f_hero(spec, rng):
    """One photographed organ, filling the frame, with the finding marked."""
    im = _cover(spec["hero"], W, H)
    a = np.asarray(im).astype(np.float32)
    # Vignette rather than a flat darken: it holds the eye on the mark instead
    # of flattening the whole photograph.
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W * 0.42) / (W * 0.72)) ** 2 + ((yy - H * 0.42) / (H * 0.78)) ** 2)
    c = np.clip(a * np.clip(1.16 - 0.62 * r, 0.30, 1.12)[:, :, None], 0, 255)

    shown = Image.fromarray(c.astype(np.uint8))
    im = shown
    d = ImageDraw.Draw(im)
    # On a macro of an eye the darkest compact region is the pupil, which is
    # exactly what the card is about. Edge energy would find the eyelashes.
    at = spec.get("mark_at") or _focus_point(shown, zone=(0.16, 0.18, 0.78, 0.66),
                                             prefer="dark", centre_bias=True,
                                             min_salience=1.5)
    mx, my = at if at else (int(W * 0.44), int(H * 0.40))
    if at:
        _ring(d, mx, my, 130, 118, rng=rng, width=13)
    if at and spec.get("mark"):
        lx = mx + 168 if mx < W * 0.62 else mx - 168
        _label(d, spec["mark"], (lx, my - 34), YELLOW, size=52,
               anchor="lt" if mx < W * 0.62 else "rt")
    _label(d, spec["kicker"], BRAND_AT, RED, fg=WHITE, size=34)
    _block(im, spec["lines"], _COND, (92, 430, 1046, 618), WHITE, start=132,
           weight=8, align="centre")
    _mark(im)
    return np.asarray(im).astype(np.float32)


def _f_banner(spec, rng):
    """Full-bleed scene, headline banded across the top, presenter in the corner."""
    shot = _cover(spec["scene"], W, H, focus=0.42)
    c = _recede(shot, blur=1.6, dark=0.78)
    head_at = (0.81, 0.44)
    c = pcut.stand(c, spec["pose"], head_h=268, head_at=head_at,
                   mirror=spec.get("mirror", True), stroke=STROKE, shadow=SHADOW)
    im = Image.fromarray(c.astype(np.uint8))
    d = ImageDraw.Draw(im)

    # Banner first is wrong: the arrow has to know where the banner ends before
    # it can avoid running under it.
    d.rectangle([0, 0, W, 176], fill=YELLOW)
    d.rectangle([0, 168, W, 184], fill=BLACK)
    # One band, so the headline is joined rather than truncated. Taking
    # lines[:1] silently shipped "EVERY TEST" and dropped "CAME BACK CLEAN",
    # which reads as a sentence someone forgot to finish.
    _block(im, [" ".join(spec["lines"])], _COND, (96, 26, 1184, 148), BLACK,
           start=118, ow=0, weight=5, align="centre")

    # An empty corridor has no finding in it. When the scene is just a place,
    # the banner and the presenter carry the card on their own.
    at = _focus_point(shot, zone=(0.10, 0.32, 0.56, 0.86), min_salience=2.6)
    if at:
        mx, my = at
        _ring(d, mx, my, 104, 92, rng=rng)
        _arrow(d, _shoulder(head_at, 268, side=-1), (mx + 118, my + 24),
               bend=0.22, rng=rng)
    if spec.get("mark"):
        _label(d, spec["mark"], (96, 618), RED, fg=WHITE, size=52, anchor="lb")
    _mark(im)
    return np.asarray(im).astype(np.float32)


_RENDER = {"reaction": _f_reaction, "bubbles": _f_bubbles, "pointing": _f_pointing,
           "verdict": _f_verdict, "hero": _f_hero, "banner": _f_banner}


# ── entry point ────────────────────────────────────────────────────────

def pick_format(episode, history=None):
    """Rotate formats, never repeating what ran last."""
    hist = list(history or [])
    pool = [f for f in FORMATS if f not in hist[-3:]] or \
           [f for f in FORMATS if not hist or f != hist[-1]]
    return pool[episode % len(pool)]


def punch(arr, contrast=1.16, sat=1.24):
    """Final grade. High-contrast thumbnails measurably out-click flat ones.

    Applied once at the end rather than to each layer, so the photograph, the
    presenter and the type all shift together and the card still reads as one
    image rather than as a person pasted onto a scene.
    """
    a = arr.astype(np.float32)
    grey = a.mean(axis=2, keepdims=True)
    a = grey + (a - grey) * sat                      # saturation
    a = 128.0 + (a - 128.0) * contrast               # contrast about mid grey
    return np.clip(a, 0, 255)


def badge_clear(arr, ink=0.035):
    """True if the duration badge will not cover anything that matters.

    The badge is drawn by YouTube after upload, so this cannot be checked by
    looking at the file -- which is exactly why headlines end up half-hidden.
    The test is whether the corner carries strong local detail (type or a hard
    graphic edge) rather than photograph.
    """
    x0, y0, x1, y1 = BADGE
    g = np.asarray(Image.fromarray(arr.astype(np.uint8)).convert("L")
                   ).astype(np.float32)[y0:y1, x0:x1]
    if g.size == 0:
        return True
    edge = (np.abs(np.diff(g, axis=1))[:, :] > 70).mean()
    return float(edge) <= ink


def legible_at(arr, px=120):
    """Contrast that survives a 120px mobile row.

    Returned rather than asserted, so the caller's quality gate decides. A
    thumbnail that fails this is not broken, it is weak, and the difference
    matters when the alternative is shipping nothing.
    """
    small = Image.fromarray(arr.astype(np.uint8)).resize(
        (px, int(px * H / W)), Image.LANCZOS)
    g = np.asarray(small.convert("L")).astype(np.float32)
    return float(g.std())


# What a patient actually gets told before anyone believes them. The bubble
# format needs two lines and the pipeline only has one -- the episode headline
# -- so the first bubble comes from here and rotates by episode, and the second
# is the episode's own line. Without this every bubbles thumbnail the channel
# ever published would carry the same two sentences.
DISMISSALS = ("IT'S JUST STRESS", "YOU'RE FINE", "ALL TESTS NORMAL",
              "IT'S ANXIETY", "NOTHING ON THE SCAN", "COME BACK IN SIX MONTHS",
              "PROBABLY A VIRUS", "TRY SLEEPING MORE")


def _default_quotes(episode, lines):
    return [DISMISSALS[(episode or 1) % len(DISMISSALS)], " ".join(lines)]


def render(out_path, headline, photos, fmt=None, episode=1, history=None,
           kicker="CASE", mark=None, quotes=None, pose=None, seed=None,
           state_a="BEFORE", state_b="AFTER", mark_at=None):
    """Render one thumbnail. `photos` maps role -> file path.

    Roles: scene (wide location), evidence (the clinical still), hero (a macro
    subject). Missing roles fall back to whatever else was supplied, so a run
    that only got one photo out of Pixabay still produces a card.
    """
    rng = random.Random(seed if seed is not None else episode * 7919)
    fmt = fmt or pick_format(episode, history)

    have = {k: v for k, v in (photos or {}).items() if v and os.path.exists(v)}
    if not have:
        raise ValueError("photo_thumbnail needs at least one real photograph")
    any_one = next(iter(have.values()))

    # Trim to the word cap first, then lay out. Doing it the other way round
    # caps each LINE at five words and lets a two-line headline reach ten.
    flat = trim_words(" ".join((headline or "").split()), MAX_WORDS).upper()
    words = flat.split()
    if len(words) <= 3:
        lines = [flat]
    else:
        half = (len(words) + 1) // 2
        lines = [" ".join(words[:half]), " ".join(words[half:])]
    spec = {
        "scene": have.get("scene", any_one),
        "evidence": have.get("evidence", any_one),
        "evidence_b": have.get("evidence_b"),
        "hero": have.get("hero", have.get("evidence", any_one)),
        "lines": lines or ["NO CAUSE FOUND"],
        "kicker": (kicker or "CASE").upper(),
        "mark": (mark or "").upper() or None,
        "quotes": [q.upper() for q in (quotes or _default_quotes(episode, lines))],
        "pose": pose or rng.choice(_POSES[fmt]),
        "mirror": rng.random() < 0.5,
        "state_a": state_a.upper(),
        "state_b": state_b.upper(),
        "mark_at": mark_at,
    }
    if not spec["mark_at"]:
        spec.pop("mark_at")

    arr = punch(_RENDER[fmt](spec, rng))
    Image.fromarray(arr.astype(np.uint8)).save(out_path, quality=94)
    return {"path": out_path, "format": fmt, "pose": spec["pose"],
            "contrast_120px": round(legible_at(arr), 1),
            "words": len(flat.split()),
            "badge_clear": badge_clear(arr)}
