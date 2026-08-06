#!/usr/bin/env python3
"""
One-time ingest of the presenter pose library.

    python3 tools/build_presenter_library.py --src <dir-of-pngs>

WHAT THIS DOES NOT DO: cut the presenter out of his background.

That is the whole reason this version works. The poses are supplied on a
background measured at exactly (0, 0, 0), and every channel card is near-black,
so the plate is composited by SCREEN rather than masked. Screen leaves a zero
pixel showing whatever is underneath, which means the background disappears on
its own -- no threshold to tune, no edge to feather, and every hair and every
soft shadow on the shirt survives intact because nothing was ever classified.

An earlier attempt on differently-lit source spent five separate mechanisms
trying to separate subject from background and put holes through the subject.
Nothing here separates anything.

WHAT IT STORES
--------------
The plate at working resolution, plus the geometry needed to place it:

    crown_y     top of the head
    head_w      head width, measured across the widest part of the skull
    head_cx     horizontal centre of the head

Poses are framed inconsistently at source -- the gesture shots sit further
back, so the head is about 20% smaller in frame than in the portraits. Storing
geometry instead of re-cropping means the compositor can scale every pose to
the same head size at render time without anything being thrown away, and the
hand in a pointing shot never gets cropped off to make a head match.
"""
import argparse
import glob
import json
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.normpath(os.path.join(HERE, "..", "video_pipeline", "presenter_library"))

# Stored edge length. Thumbnails are 1280x720 and the presenter occupies at most
# the full height, so 1000px carries more detail than any output needs.
EDGE = 1000
WEBP = dict(format="WEBP", quality=88, method=6)

# Luminance above which a pixel is subject rather than background. The plate
# background is exactly 0, so this only has to clear sensor-free PNG noise.
FLOOR = 18.0

# id -> (name, register, gaze, gesture, keep_to)
#
# keep_to is the fraction of the plate's height that MUST stay on the card.
# Without it, sizing purely by head height crops a gesture straight out of
# frame: the arms-crossed pose came back as a plain head-and-shoulders with the
# folded arms below the bottom edge, which is the entire content of the pose
# gone while the render still looked fine. None means head sizing is free to
# run, which is right for a pose whose meaning is all above the collarbone.
#
# register  what the face is doing, in story terms
# gaze      where the eyes go: camera / up / down / away_left / away_right
# gesture   none / hand_to_chin / hand_to_ear / open_palm / pointing / arms_crossed
#
# Tags describe what is VISIBLE, not what the pose was called when it was
# generated. "eyes off to the left with a furrowed brow" can be verified by
# looking; "determined" cannot, and a library indexed on unverifiable labels
# fails silently the first time one is wrong.
POSES = [
    ("2027", "neutral_three_quarter", "neutral",     "camera",      "none", None),
    ("2031", "neutral_front",         "neutral",     "camera",      "none", None),
    ("2047", "calm",                  "neutral",     "camera",      "none", None),
    ("2046", "resolve",               "resolve",     "camera",      "none", None),
    ("2040", "concern",               "concern",     "camera",      "none", None),
    ("2048", "concern_b",             "concern",     "camera",      "none", None),
    ("2029", "confusion",             "confusion",   "camera",      "none", None),
    ("2030", "curiosity",             "curiosity",   "camera",      "none", None),
    ("2043", "surprise",              "surprise",    "camera",      "none", None),
    ("2039", "skepticism",            "suspicion",   "away_left",   "none", None),
    ("2036", "suspicion",             "suspicion",   "away_left",   "none", None),
    ("2044", "suspicion_b",           "suspicion",   "away_left",   "none", None),
    ("2034", "recall",                "recall",      "up",          "none", None),
    ("2042", "recall_b",              "recall",      "up",          "none", None),
    ("2028", "grief",                 "grief",       "down",        "none", None),
    ("2035", "grief_b",               "grief",       "down",        "none", None),
    ("2033", "profile_left",          "neutral",     "away_left",   "none", None),
    ("2037", "profile_right",         "neutral",     "away_right",  "none", None),
    ("2038", "deliberation",          "deliberation", "away_left",  "hand_to_chin", 0.74),
    ("2052", "alert",                 "alert",       "away_left",   "hand_to_ear",  0.62),
    ("2053", "presenting",            "presenting",  "camera",      "open_palm",    0.86),
    ("2054", "directing",             "directing",   "away_right",  "pointing",     0.72),
    ("2055", "authority",             "authority",   "camera",      "arms_crossed", 0.94),
]


def geometry(a):
    """crown_y, head_w, head_cx for a plate. All in stored-image pixels."""
    h, w, _ = a.shape
    m = a.mean(axis=2) > FLOOR
    ys, xs = np.nonzero(m)
    if ys.size == 0:
        return 0, w // 2, w // 2
    crown = int(ys.min())

    # Head width is taken across a band below the crown rather than at a single
    # row: one row can land on a stray lock of hair and read 40px wide. The band
    # spans the skull and stops above the jaw, so it is stable across poses that
    # tilt or turn.
    lo = crown + int(0.10 * h)
    hi = crown + int(0.22 * h)
    widths, centres = [], []
    for y in range(lo, min(hi, h)):
        cols = np.nonzero(m[y])[0]
        if cols.size:
            widths.append(cols.max() - cols.min())
            centres.append((cols.max() + cols.min()) * 0.5)
    if not widths:
        return crown, w // 2, w // 2
    return crown, int(np.median(widths)), int(np.median(centres))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", default=LIB)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    manifest = {"poses": {}, "screen_composite": True, "edge": EDGE}
    for pid, name, register, gaze, gesture, keep_to in POSES:
        hits = glob.glob(os.path.join(args.src, "*%s*.png" % pid))
        if not hits:
            print("  MISSING %-22s (%s)" % (name, pid))
            continue
        im = Image.open(hits[0]).convert("RGB")
        im = im.resize((EDGE, EDGE), Image.LANCZOS) if im.size != (EDGE, EDGE) \
            else im
        a = np.asarray(im).astype(np.float32)
        crown, head_w, head_cx = geometry(a)

        path = os.path.join(args.out, name + ".webp")
        im.save(path, **WEBP)
        manifest["poses"][name] = {
            "file": name + ".webp",
            "register": register,
            "gaze": gaze,
            "gesture": gesture,
            "crown_y": crown,
            "head_w": head_w,
            "head_cx": head_cx,
            "keep_to": keep_to,
        }
        print("  %-22s %-12s %-11s %-13s crown=%-4d head_w=%-4d  %5.1f kB"
              % (name, register, gaze, gesture, crown, head_w,
                 os.path.getsize(path) / 1024.0))

    with open(os.path.join(args.out, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
    print("\n%d poses written to %s" % (len(manifest["poses"]), args.out))


if __name__ == "__main__":
    main()
