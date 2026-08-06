"""
The presenter pose library: choosing a face, and putting it on a card.

THE COMPOSITE IS A SCREEN, NOT A MASK
-------------------------------------
Every plate is the presenter lit against a background of exactly (0, 0, 0), and
every channel card is near-black. So the plate goes down with

    out = 255 - (255 - card) * (255 - plate) / 255

A zero pixel in the plate leaves the card exactly as it was; a bright pixel
takes over. The background removes itself. There is no threshold to tune, no
alpha to feather, and -- the point -- no pixel is ever CLASSIFIED as subject or
background, so no amount of dark hair or soft shadow can be mistaken for
background and deleted. Hair strands, the shadowed side of the shirt and the
soft edge of the jaw all survive because nothing was ever cut.

The one constraint this imposes: whatever sits behind the presenter in a layout
must stay dark. Screen over a bright panel would make him look transparent. In
practice the layouts keep his side of the card dark anyway, because that is
what makes a face read.

WHY GEOMETRY IS STORED RATHER THAN BAKED IN
-------------------------------------------
The source poses are not framed alike -- the gesture shots stand further back,
so the head measures around 294px against 443px for a profile, a spread of
about 1.5x. Cropping them to match at ingest would mean cutting the pointing
hand off to make the heads agree.

Instead each plate carries crown_y, head_w and head_cx, and place() scales and
positions from those at render time. Every pose can therefore be asked for at
the same head size, with the head landing in the same spot, while keeping
whatever else is in frame.
"""
import json
import os
import random

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "presenter_library")

_MANIFEST = None


def manifest():
    global _MANIFEST
    if _MANIFEST is None:
        with open(os.path.join(LIB, "manifest.json")) as fh:
            _MANIFEST = json.load(fh)
    return _MANIFEST


def poses():
    return manifest()["poses"]


# ── which face suits which moment ──────────────────────────────────────
#
# Keyed on what the episode is doing, not on the channel. The same beat wants
# the same face whether the subject is a misdiagnosis or a coup -- what changes
# between channels is which beats occur, not what doubt looks like.
BEAT_REGISTERS = {
    "hook":        ("surprise", "concern", "confusion"),
    "question":    ("confusion", "curiosity", "suspicion"),
    "evidence":    ("presenting", "directing", "deliberation"),
    "doubt":       ("suspicion", "skepticism"),
    "reveal":      ("surprise", "concern"),
    "consequence": ("grief", "concern"),
    "authority":   ("authority", "resolve"),
    "reflection":  ("recall", "deliberation", "neutral"),
}

# Per-channel leaning, applied as a preference among whatever the beat allows.
CHANNEL_BIAS = {
    "no_known_cause":    ("confusion", "concern", "curiosity", "grief"),
    "betrayal_deepdive": ("suspicion", "skepticism", "surprise"),
    "dark":              ("suspicion", "grief", "alert"),
    "archive":           ("authority", "resolve", "recall"),
    "economics":         ("presenting", "authority", "directing"),
}


def select(beat="question", channel=None, history=(), seed=None):
    """Pick a pose name for a story beat, avoiding recent repeats.

    history is the pose names used on the last few episodes of this channel.
    A presenter who pulls the same face every week stops being a presenter and
    becomes a logo, so anything recently used is excluded outright rather than
    merely down-weighted.
    """
    wanted = BEAT_REGISTERS.get(beat, BEAT_REGISTERS["question"])
    pool = [n for n, p in poses().items() if p["register"] in wanted]
    if not pool:
        pool = list(poses())

    # A beat maps to two or three registers, so its pool is small -- "hook" on
    # the medical channel is four poses. A history of four therefore exhausts
    # it routinely, and the first version simply reopened the whole pool at
    # that point. That let the pose used LAST episode come straight back:
    # episodes 11 and 12 both drew concern_b. Falling back has to keep the one
    # exclusion that a viewer would actually notice.
    fresh = [n for n in pool if n not in history]
    if not fresh:
        last = history[-1] if history else None
        fresh = [n for n in pool if n != last]
    if fresh:
        pool = fresh

    bias = CHANNEL_BIAS.get(channel or "", ())
    preferred = [n for n in pool if poses()[n]["register"] in bias]
    if preferred:
        pool = preferred

    rng = random.Random(seed) if seed is not None else random
    return rng.choice(sorted(pool))


# ── loading and placing ────────────────────────────────────────────────

def load(name, mirror=False):
    """Return (plate float array, geometry dict). Mirroring is free.

    A horizontal flip is undetectable here -- plain shirt, no text, no logo --
    so every left-facing pose supplies a right-facing one and the library
    covers both directions at half the generation cost.
    """
    p = dict(poses()[name])
    im = Image.open(os.path.join(LIB, p["file"])).convert("RGB")
    a = np.asarray(im).astype(np.float32)
    if mirror:
        a = a[:, ::-1, :].copy()
        p["head_cx"] = a.shape[1] - p["head_cx"]
        if p["gaze"] == "away_left":
            p["gaze"] = "away_right"
        elif p["gaze"] == "away_right":
            p["gaze"] = "away_left"
    return a, p


def place(card, name, head_h=260, head_at=(0.30, 0.34), mirror=False):
    """Screen a pose onto `card`, sized and positioned by head geometry.

    head_h    desired head height in output pixels
    head_at   where the centre of the head should land, as a fraction of the
              card's width and height
    """
    plate, g = load(name, mirror=mirror)

    # head_w is measured across the skull; head height runs about 1.35x that
    # for this subject. Scaling on a measured width rather than a guessed
    # height keeps every pose the same size on screen.
    scale = float(head_h) / (g["head_w"] * 1.35)
    ph, pw, _ = plate.shape

    # ── keep the gesture on the card ───────────────────────────────────
    # Sizing on the head alone crops whatever the hands are doing straight off
    # the bottom. The arms-crossed pose rendered as an ordinary head-and-
    # shoulders with the folded arms below the frame -- the whole content of
    # the pose missing, and nothing in the output to say so. Where a pose
    # declares how far down it must stay visible, the scale is capped to
    # honour it, so a gesture shot simply sits smaller rather than losing its
    # gesture.
    keep_to = g.get("keep_to")
    if keep_to:
        head_top = card.shape[0] * head_at[1] - head_h * 0.5
        room = card.shape[0] - max(0.0, head_top)
        max_scale = room / (ph * keep_to - g["crown_y"])
        scale = min(scale, max_scale)

    nw, nh = max(1, int(round(pw * scale))), max(1, int(round(ph * scale)))
    small = np.asarray(
        Image.fromarray(plate.astype(np.uint8)).resize((nw, nh), Image.LANCZOS)
    ).astype(np.float32)

    ch, cw, _ = card.shape
    # Head centre in the scaled plate, then offset so it lands on head_at.
    hx = g["head_cx"] * scale
    hy = (g["crown_y"] * scale) + head_h * 0.5
    x0 = int(round(cw * head_at[0] - hx))
    y0 = int(round(ch * head_at[1] - hy))

    # Clip to the card.
    sx0, sy0 = max(0, -x0), max(0, -y0)
    dx0, dy0 = max(0, x0), max(0, y0)
    w = min(nw - sx0, cw - dx0)
    h = min(nh - sy0, ch - dy0)
    if w <= 0 or h <= 0:
        return card

    out = card.astype(np.float32).copy()
    region = out[dy0:dy0 + h, dx0:dx0 + w]
    piece = small[sy0:sy0 + h, sx0:sx0 + w]
    out[dy0:dy0 + h, dx0:dx0 + w] = 255.0 - (255.0 - region) * (255.0 - piece) / 255.0
    return np.clip(out, 0, 255)
