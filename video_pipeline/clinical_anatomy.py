"""
Flat vector body shapes for clinical thumbnails.

WHY THESE EXIST
---------------
The single largest lever on thumbnail click-through is a human element at
large scale. A chart has none. An abstract scan field has none. That is the
difference between a thumbnail that looks professional and one that gets
clicked, and it is why the first pass at this channel's thumbnails — clean,
teal, geometric — would have settled somewhere around three to five percent
and stayed there.

So: real body shapes, drawn as flat silhouettes from polygon data. Big enough
to read as a person at 210 pixels, abstract enough that no one could mistake
one for a photograph of a patient. Every shape carries a named REGION — a
sub-area that can be lit in an alarm colour to say "the problem is HERE"
without a single word.

Coordinates are normalised 0..1 inside the shape's own box, so a shape can be
dropped at any size. y increases downward, matching the image convention.
"""

# ── head, in profile, facing right ───────────────────────────────────
# Reads as a person at a glance, which a front-facing outline does not:
# a profile has a nose, and a nose is what makes a silhouette human.
# Deliberately low on facial detail. Two earlier versions modelled lips,
# philtrum and mentolabial crease faithfully; at the ~210px a thumbnail is
# actually seen at, those are eight-pixel wobbles and they read as noise, not
# as a mouth. A profile is legible at that size because of two features only
# — the nose and the chin — so those are the only two this draws.
HEAD = [
    # skull, over the top
    (0.100, 0.420), (0.112, 0.300), (0.162, 0.190), (0.252, 0.110),
    (0.382, 0.068), (0.520, 0.078), (0.630, 0.140), (0.688, 0.240),
    (0.702, 0.340),
    # Face. A nose needs a bridge, a tip and a base — as a single far-out
    # point it renders as a beak, which is what the previous version did.
    (0.700, 0.400),   # brow
    (0.652, 0.436),   # bridge dip
    (0.706, 0.480),   # bridge
    (0.754, 0.514),
    (0.786, 0.540),   # tip
    (0.762, 0.558),   # under the tip
    (0.706, 0.568),   # nostril base
    (0.694, 0.614),   # upper lip
    (0.712, 0.648),   # lip
    (0.678, 0.688),   # under the lip
    (0.706, 0.724),   # chin, front
    (0.686, 0.774),   # chin, underside
    (0.600, 0.810), (0.492, 0.826), (0.412, 0.802),
    # Neck. The previous version jogged in to x=0.356 before descending,
    # which cut a notch out of the skull and left the jaw floating with
    # nothing joining it to the head. It runs straight down from the jaw
    # now, and the column is as wide as a neck actually is.
    (0.432, 0.900), (0.448, 1.000),
    (0.152, 1.000), (0.132, 0.820), (0.108, 0.660), (0.098, 0.540),
]
# The cranial vault — where a neurological finding goes.
HEAD_REGION = (0.20, 0.13, 0.66, 0.42)

# ── open hand, fingers up ────────────────────────────────────────────
HAND_PALM = [
    (0.20, 0.52), (0.24, 0.40), (0.76, 0.40), (0.82, 0.54),
    (0.80, 0.80), (0.68, 0.97), (0.34, 0.97), (0.20, 0.78),
]
# (x_centre, top_y, width) per digit; the last is the thumb.
HAND_FINGERS = [
    (0.30, 0.16, 0.11), (0.43, 0.07, 0.115), (0.565, 0.06, 0.115),
    (0.695, 0.13, 0.105),
]
HAND_THUMB = [
    (0.22, 0.55), (0.10, 0.44), (0.03, 0.50), (0.06, 0.60), (0.19, 0.68),
]
# Fingertips — where a peripheral finding goes.
HAND_REGION = (0.24, 0.05, 0.76, 0.30)

# ── bust: head and shoulders, facing forward ─────────────────────────
# Was a whole standing body, which at thumbnail size read as a gingerbread
# man. Head-and-shoulders is the shape every thumbnail with a person in it
# actually uses, and it fills the frame instead of shrinking to fit legs.
TORSO = [
    (0.500, 0.030), (0.590, 0.055), (0.646, 0.130), (0.652, 0.230),
    (0.634, 0.300), (0.590, 0.352), (0.560, 0.386), (0.560, 0.430),
    (0.700, 0.480), (0.830, 0.560), (0.900, 0.680), (0.940, 0.850),
    (0.955, 1.000), (0.045, 1.000), (0.060, 0.850), (0.100, 0.680),
    (0.170, 0.560), (0.300, 0.480), (0.440, 0.430), (0.440, 0.386),
    (0.410, 0.352), (0.366, 0.300), (0.348, 0.230), (0.354, 0.130),
    (0.410, 0.055),
]
# The chest — where a cardiac or respiratory finding goes.
TORSO_REGION = (0.330, 0.620, 0.670, 0.900)


def _lens(cx, cy, rx, ry, n=28):
    """An almond, not an octagon: two arcs meeting at sharp corners.

    The first attempt spread eight points evenly around an ellipse, which
    draws an octagon. An eye is defined by its pointed corners, so those are
    built in rather than approximated.
    """
    import math
    top = [(cx - rx + 2 * rx * (i / n),
            cy - ry * math.sin(math.pi * (i / n)) ** 0.72)
           for i in range(n + 1)]
    bot = [(cx + rx - 2 * rx * (i / n),
            cy + ry * math.sin(math.pi * (i / n)) ** 0.72)
           for i in range(n + 1)]
    return top + bot


EYE_OUTER = _lens(0.50, 0.50, 0.475, 0.315)
EYE_REGION = (0.34, 0.30, 0.66, 0.70)

SHAPES = ("head", "hand", "torso", "eye")

# Which body shape a niche is about. A neurology case gets a head; a
# toxicology case gets the hand that turned a colour it should not have.
NICHE_SHAPE = {
    "neurology_cases":          "head",
    "sleep_science":            "head",
    "medical_history":          "head",
    "toxicology_cases":         "hand",
    "drug_discovery_stories":   "hand",
    "surgical_case_studies":    "torso",
    "medical_mystery_outbreak": "torso",
    "senior_health_longevity":  "torso",
    "rare_disease_cases":       "eye",
    "diagnostic_odyssey":       "eye",
}

# Words in the topic that name a body part beat the niche default — a
# neurology case whose actual story is about hands should show hands.
TOPIC_SHAPE = {
    "hand": "hand", "hands": "hand", "finger": "hand", "fingers": "hand",
    "limb": "hand", "grip": "hand", "skin": "hand",
    "brain": "head", "neuro": "head", "cognit": "head", "memory": "head",
    "seizure": "head", "headache": "head", "sleep": "head", "speech": "head",
    "lung": "torso", "heart": "torso", "chest": "torso", "cardiac": "torso",
    "breath": "torso", "abdom": "torso", "liver": "torso", "kidney": "torso",
    "eye": "eye", "vision": "eye", "retina": "eye", "sight": "eye",
    "blind": "eye", "pupil": "eye",
}


def shape_for(niche_name, topic=""):
    """Pick the body shape this episode is actually about."""
    low = (topic or "").lower()
    for key, shape in TOPIC_SHAPE.items():
        if key in low:
            return shape
    return NICHE_SHAPE.get(niche_name, "head")


# Colours named in the case itself. "Blue Dye Saved Frozen Hands" should put
# a BLUE hand on the thumbnail — the specific, strange, true detail is the
# most clickable thing the episode owns, and a generic teal wash throws it
# away.
TOPIC_COLOUR = {
    "blue":   (58, 128, 240),
    "green":  (46, 190, 118),
    "yellow": (238, 194, 44),
    "jaundice": (238, 194, 44),
    "purple": (150, 92, 226),
    "violet": (150, 92, 226),
    "orange": (243, 137, 42),
    "red":    (232, 62, 58),
    "grey":   (150, 158, 166),
    "gray":   (150, 158, 166),
    "black":  (54, 60, 68),
    "white":  (226, 232, 236),
    "silver": (186, 196, 204),
    "copper": (198, 118, 62),
    "gold":   (222, 176, 72),
}


def anomaly_colour(topic="", default=(232, 62, 58)):
    """The colour the case itself names, if it names one."""
    low = (topic or "").lower()
    for word, rgb in TOPIC_COLOUR.items():
        if word in low:
            return rgb
    return default


# A shape's own proportions, width relative to height. Without these a shape
# handed a non-square box stretches — a head in a wide box becomes a fat head,
# which is one of the ways the early renders looked wrong.
ASPECT = {"head": 0.78, "hand": 0.86, "torso": 1.00, "eye": 1.55}


def fit_box(shape, box):
    """Largest box of the shape's own proportions, centred inside box."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    a = ASPECT.get(shape, 1.0)
    if w / h > a:
        nw, nh = h * a, h
    else:
        nw, nh = w, w / a
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    return (cx - nw / 2, cy - nh / 2, cx + nw / 2, cy + nh / 2)


def _scale(points, box):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    return [(x0 + px * w, y0 + py * h) for px, py in points]


def draw_shape(d, shape, box, fill, outline=None, width=0, detail=True):
    """Draw one body silhouette into box=(x0,y0,x1,y1), aspect preserved.

    detail=False omits interior features (currently the eye's iris). The
    finding-colour layer needs the bare silhouette: with the iris drawn, it
    painted over the very region the colour was meant to fill, so an eye
    case rendered its anomaly as a black disc.
    """
    box = fit_box(shape, box)
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    if shape == "hand":
        for cx, top, fw in HAND_FINGERS:
            fx0 = x0 + (cx - fw / 2) * w
            fx1 = x0 + (cx + fw / 2) * w
            d.rounded_rectangle([fx0, y0 + top * h, fx1, y0 + 0.56 * h],
                                radius=(fx1 - fx0) / 2, fill=fill)
        d.polygon(_scale(HAND_THUMB, box), fill=fill)
        d.polygon(_scale(HAND_PALM, box), fill=fill)
        if outline:
            d.line(_scale(HAND_PALM + HAND_PALM[:1], box),
                   fill=outline, width=width, joint="curve")
        return
    pts = {"head": HEAD, "torso": TORSO, "eye": EYE_OUTER}[shape]
    d.polygon(_scale(pts, box), fill=fill)
    if outline:
        d.line(_scale(pts + pts[:1], box), fill=outline, width=width,
               joint="curve")
    if shape == "eye" and detail:
        # Iris and pupil, so it reads as an eye rather than a leaf.
        cx, cy = x0 + 0.50 * w, y0 + 0.50 * h
        r = 0.19 * w
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(14, 20, 26))


def region_box(shape, box):
    """Where the finding goes, in absolute coordinates.

    Applies the same aspect fit as draw_shape, or the marker would land
    somewhere the shape is not.
    """
    x0, y0, x1, y1 = fit_box(shape, box)
    w, h = x1 - x0, y1 - y0
    rx0, ry0, rx1, ry1 = {
        "head": HEAD_REGION, "hand": HAND_REGION,
        "torso": TORSO_REGION, "eye": EYE_REGION,
    }[shape]
    return (x0 + rx0 * w, y0 + ry0 * h, x0 + rx1 * w, y0 + ry1 * h)
