"""
Cutting the presenter out so he can stand on a photograph.

WHY THIS EXISTS ALONGSIDE THE SCREEN COMPOSITE
----------------------------------------------
presenter_library.place() screens the plate onto a dark card. Screen is exact
and unbreakable there, but it is addition: over a bright photograph the card
under him shows straight through and he reads as a ghost. A photo background
therefore needs a real alpha channel.

Getting an alpha channel is where the earlier photo work put holes through the
face, so the method here is chosen for what it CANNOT do rather than for how
clever it is.

THE PLATE IS ALREADY PREMULTIPLIED
----------------------------------
Every plate is the presenter against exactly (0, 0, 0), which is the definition
of an image premultiplied over black:

    plate = subject * coverage + 0 * (1 - coverage)

So the composite is just

    out = plate + background * (1 - alpha)

No division, no unpremultiply, no colour reconstruction — the three steps that
produced the pale fringes and bruised skin last time. Where alpha is 1 the
output is the plate untouched; where it is 0 the output is the background
untouched.

ALPHA COMES FROM SHAPE, NOT FROM BRIGHTNESS
-------------------------------------------
The trap is that dark hair and a navy shirt are as dark as the background, so
any brightness rule deletes them. Measured on these plates the hair is not
merely dark, it is black: the median pixel on top of the skull reads 9 out of
255, and on the grief pose 18% of the hair is exactly (0, 0, 0). Those pixels
carry no information at all. No threshold, however low, can recover them,
because there is nothing there to recover.

Two shape arguments recover them instead, and neither one looks at how bright a
pixel is:

1. CLOSING. Black hair is speckle inside a mass of lit strands -- every black
   pixel has a lit one within a few pixels. A morphological close therefore
   welds the mass solid while leaving the outer boundary where the outermost
   lit strand puts it. This is what makes the hair read as hair rather than as
   a grey see-through cloud with the background coming through it.

2. CONNECTIVITY. Background is whatever can be REACHED from outside the frame.
   After closing, the flood is stopped at the hair, and anything it cannot
   reach is subject no matter how dark. A shadowed patch enclosed by the face
   can never be reached, so it can never be punched out. That is the guarantee
   the earlier photo attempt did not have.

Brightness is used in exactly one place: outside the silhouette, for flyaway
strands, where a partial value genuinely does mean partial coverage.

Where the hair is black right at the outer edge, it is simply lost -- but it is
lost into black, which over any background reads as hair in shadow.

The plate is cut off by the bottom of the frame, so the shirt runs off the
bottom edge. Seeding the flood there would let it march up inside him. The
bottom row is therefore sealed across the subject's own run of columns and left
open everywhere else.
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

# Above this a pixel is unambiguously subject. The plate background is exactly
# zero, so this only has to clear WEBP ringing around the silhouette; it is not
# a subject/background decision in any meaningful sense, and it is deliberately
# low because the hair sits just above it.
FLOOR = 6.0

# Radius of the close, in plate pixels at the stored 1000px edge. It has to
# exceed the widest run of black between lit strands (measured at 6-8px on the
# darkest pose) and stay under the narrowest real gap the silhouette contains
# -- the space between the pointing hand and the shoulder, measured at 60px.
# Anywhere in between behaves identically, so the middle of that range is the
# safe choice rather than a tuned one.
CLOSE = 12

# Radius of the second close, applied to the finished mask to seal channels the
# flood crawled down and left as notches in the outline.
#
# There are two numbers because there are two kinds of plate. On a gesture pose
# the gap between the raised hand and the shoulder is REAL and has to survive:
# measured across those five poses, a seal of 32 still leaves them alone and a
# seal of 44 starts eating the gap. On a head-and-shoulders portrait there is
# no legitimate background anywhere inside the silhouette -- nothing separates
# the man from himself -- so every intrusion is an artefact and the seal can be
# far more aggressive.
SEAL = 20
SEAL_PORTRAIT = 40


def _blur(a, radius):
    """Gaussian blur a float [0,1] plane. PIL's is C; ours would not be."""
    if radius <= 0:
        return a
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(radius))).astype(np.float32) / 255.0


def _morph(a, px, filt):
    """Dilate (MaxFilter) or erode (MinFilter) a float [0,1] plane by px."""
    if px <= 0:
        return a
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    step = 2
    for _ in range(max(1, int(round(px / step)))):
        im = im.filter(filt(2 * step + 1))
    return np.asarray(im).astype(np.float32) / 255.0


def _grow(a, px):
    return _morph(a, px, ImageFilter.MaxFilter)


def _close(a, px):
    """Weld speckle into a solid mass without moving the outer boundary.

    Done with a blur and a threshold rather than max/min filters. PIL's
    morphology only offers square windows, and a square close leaves a visible
    staircase of little blocks down every diagonal edge -- it was clearly
    readable along the shoulder at 1:1. A Gaussian is isotropic, so the welded
    boundary curves the way the shoulder does.
    """
    if px <= 0:
        return a
    d = (_blur(a, px * 0.55) > 0.10).astype(np.float32)
    return (_blur(d, px * 0.55) > 0.90).astype(np.float32)


def alpha(plate, floor=FLOOR, close=CLOSE, seal=SEAL):
    """Coverage for a plate shot on black. Returns float [0,1], plate-sized."""
    # max() rather than mean(): the navy shirt carries almost all its signal in
    # blue, and averaging it with two near-zero channels pushes it under any
    # sane floor.
    lum = plate.max(axis=2)

    # Weld the hair before asking what is reachable. Without this the flood
    # walks straight into the black speckle between the strands -- it is
    # genuinely connected to the outside -- and the hair composites at about
    # 30% coverage, so the background comes through it and a dark-haired man
    # renders with a grey translucent cloud on his head.
    dark = (_close((lum > floor).astype(np.float32), close) < 0.5)

    h, w = dark.shape
    # Seal the bottom across the subject so the flood cannot climb the shirt.
    # Named for what it is rather than "seal", which is also the radius
    # argument -- the two shadowed each other and the close silently received a
    # boolean array where it wanted a number.
    floor_run = np.zeros(w, dtype=bool)
    lit = np.nonzero(~dark[h - 1])[0]
    if lit.size:
        floor_run[lit.min():lit.max() + 1] = True

    canvas = np.zeros((h + 2, w + 2), np.uint8)
    canvas[1:-1, 1:-1] = np.where(dark, 255, 0)
    canvas[0, :] = 255          # top, left and right stay open
    canvas[:, 0] = 255
    canvas[:, -1] = 255
    canvas[-1, :] = 255
    canvas[-1, 1:-1][floor_run] = 0  # ...the bottom does not, under him

    # Pillow's floodfill silently no-ops on an image that still shares its
    # buffer with the numpy array it came from; .copy() detaches it. Without
    # this the function returns "nothing is background" and every composite
    # comes out as a black rectangle.
    im = Image.fromarray(canvas).copy()
    ImageDraw.floodfill(im, (0, 0), 128)
    outside = np.asarray(im)[1:-1, 1:-1] == 128

    solid = (~outside).astype(np.float32)

    # Seal narrow channels. The flood only needs one thread of background-dark
    # pixels to get in, and on the curiosity pose it found one at the temple:
    # it slipped between a hair strand and the ear, opened out into a blob, and
    # the stroke then drew a white keyhole in the middle of his hair. Closing
    # the finished mask fills anything a channel that thin can lead to, while
    # the gaps that must stay open -- between the pointing hand and the
    # shoulder -- are three times wider than this radius.
    solid = _close(solid, seal)

    # There is deliberately no soft ramp on the dim pixels outside the
    # silhouette. It sounds right -- a dim pixel is a half-covered hair strand
    # -- but every pixel above the floor is already inside `solid`, so the ramp
    # can only ever act on what is BELOW it, and below it there is nothing but
    # WEBP ringing. It rendered as a staircase of grey 8x8 blocks stepping down
    # the shoulder, clearly visible at 1:1 against white. The strands it was
    # meant to save are black hair against a black plate: invisible over any
    # background, so nothing is lost by dropping it.
    #
    # A pixel of feather is all the edge needs. It costs a sliver of background
    # bleed just inside the outline, which is what antialiasing is.
    return np.clip(_blur(solid, 1.2), 0.0, 1.0)


def _cut_edges(plane, A, rect):
    """Zero a stroke/shadow plane where it would outline the plate's own crop.

    The presenter runs off the edge of his plate -- the shirt off the bottom, a
    shoulder off the side. Those edges are not silhouette, so drawing an
    outline along them puts a white bar across his chest and a white stripe
    down his arm. Suppression is per-column and per-row rather than per-side,
    so a genuine silhouette that happens to share a border with a crop still
    gets its outline.
    """
    y0, x0, y1, x1 = rect
    p = plane.copy()
    solid = A > 0.5
    p[:y0][:, solid[y0]] = 0.0
    p[y1 + 1:][:, solid[y1]] = 0.0
    p[solid[:, x0], :x0] = 0.0
    p[solid[:, x1], x1 + 1:] = 0.0
    return p


def place_on_photo(bg, plate, a, box, stroke=9, stroke_rgb=(255, 255, 255),
                   shadow=0.55, anchor="bottom"):
    """Composite a matted plate into `box` on a photographic background.

    bg      float HxWx3 background, modified copy returned
    plate   float PxPx3 plate (premultiplied over black)
    a       matching coverage plane from alpha()
    box     (x0, y0, x1, y1) region the plate is fitted into
    stroke  outline width in output pixels; 0 for none

    The order is shadow, then stroke, then subject. Drawing the stroke before
    the subject rather than around him means the outline sits UNDER his edge,
    so it never eats into the jaw or the hairline.
    """
    x0, y0, x1, y1 = box
    tw, th = max(1, x1 - x0), max(1, y1 - y0)
    ph, pw, _ = plate.shape
    s = min(tw / float(pw), th / float(ph))
    nw, nh = max(1, int(round(pw * s))), max(1, int(round(ph * s)))

    p = np.asarray(Image.fromarray(plate.astype(np.uint8))
                   .resize((nw, nh), Image.LANCZOS)).astype(np.float32)
    aa = np.asarray(Image.fromarray((a * 255).astype(np.uint8))
                    .resize((nw, nh), Image.LANCZOS)).astype(np.float32) / 255.0

    dx = x0 + (tw - nw) // 2
    dy = y1 - nh if anchor == "bottom" else y0 + (th - nh) // 2

    H, W, _ = bg.shape
    sx, sy = max(0, -dx), max(0, -dy)
    dx, dy = max(0, dx), max(0, dy)
    w = min(nw - sx, W - dx)
    h = min(nh - sy, H - dy)
    if w <= 0 or h <= 0:
        return bg

    out = bg.astype(np.float32).copy()

    # Work on a full-canvas plane so the grown stroke and the shadow are free
    # to spill outside the plate's own rectangle.
    A = np.zeros((H, W), np.float32)
    P = np.zeros((H, W, 3), np.float32)
    A[dy:dy + h, dx:dx + w] = aa[sy:sy + h, sx:sx + w]
    P[dy:dy + h, dx:dx + w] = p[sy:sy + h, sx:sx + w]

    rect = (dy, dx, dy + h - 1, dx + w - 1)
    if shadow > 0:
        sh = _cut_edges(_blur(_grow(A, 14), 20) * shadow, A, rect)
        out *= (1.0 - sh[:, :, None])

    if stroke > 0:
        ring = _cut_edges(np.clip(_grow(A, stroke) - A, 0.0, 1.0), A, rect)
        out = out * (1.0 - ring[:, :, None]) \
            + np.array(stroke_rgb, np.float32) * ring[:, :, None]

    out = out * (1.0 - A[:, :, None]) + P
    return np.clip(out, 0, 255)


_CACHE = {}


def stand(canvas, name, head_h, head_at, mirror=False, stroke=9,
          stroke_rgb=(255, 255, 255), shadow=0.55):
    """Put a pose on a photographic canvas, sized and placed by head geometry.

    The presenter_library twin of this is place(), and the arguments mean the
    same things there: head_h is the head's height in output pixels and head_at
    is where its centre lands as a fraction of the canvas. Sizing on the
    measured head rather than on the plate keeps every pose the same size on
    screen even though the gesture shots were framed further back.
    """
    import presenter_library as _pl  # local: avoids a cycle at import time

    plate, g = _pl.load(name, mirror=mirror)
    ph, pw, _ = plate.shape
    ch, cw, _ = canvas.shape
    scale = float(head_h) / (g["head_w"] * 1.35)

    # Same cap as place(): a pose that declares how far down it must stay
    # visible sits smaller rather than losing its hand off the bottom edge.
    keep_to = g.get("keep_to")
    if keep_to:
        top = ch * head_at[1] - head_h * 0.5
        scale = min(scale, (ch - max(0.0, top)) / (ph * keep_to - g["crown_y"]))

    nw, nh = int(round(pw * scale)), int(round(ph * scale))
    x0 = int(round(cw * head_at[0] - g["head_cx"] * scale))
    y0 = int(round(ch * head_at[1] - g["crown_y"] * scale - head_h * 0.5))

    # A portrait has no real gap inside its outline, so it gets the stronger
    # seal; a gesture pose has one that must survive, so it does not.
    seal = SEAL if keep_to else SEAL_PORTRAIT
    key = (name, mirror, seal)
    if key not in _CACHE:
        _CACHE[key] = alpha(plate, seal=seal)
    return place_on_photo(canvas, plate, _CACHE[key], (x0, y0, x0 + nw, y0 + nh),
                          stroke=stroke, stroke_rgb=stroke_rgb, shadow=shadow,
                          anchor="fill")
