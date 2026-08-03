"""
Camera moves for held cards.

WHAT WAS THERE
--------------
One zoompan, the same direction, on every card:

    zoompan=z='min(zoom+0.00045,1.12)'

A slow push in, sixty times an episode, for thirteen minutes. The eye stops
reading that as motion within about two cards and starts reading it as drift,
which is worse than a static frame -- a static frame at least reads as a
deliberate hold.

THE MOVES
---------
    push_in     into the frame, ending tighter
    pull_out    starting tight, opening out to reveal the whole card
    pan_right   across the card, left to right
    pan_left    across the card, right to left
    tilt_down   down the card
    tilt_up     up the card
    hold_drift  almost still, a slow diagonal -- the quiet one, so the
                episode has some rest in it

WHY THE INPUT IS UPSCALED FIRST
-------------------------------
zoompan samples the SOURCE pixel grid per output frame. On a 1920x1080 still
at 1920x1080 output, a fractional zoom lands between source pixels and the
whole frame shivers -- a well-known artefact, and very visible on a card made
of thin rules and small type, which is exactly what this channel renders. The
input is scaled to 2x first so zoompan has sub-pixel headroom, then the result
comes back down to 1080p. It costs a scale pass and removes the shiver.

WHY MOVES ARE CHOSEN, NOT RANDOM
--------------------------------
A pan across a card whose content sits in the middle shows a lot of empty
margin. So the move is picked per register: a dense panel earns a pan because
there is something to pan across, a figure earns a push because the interest
is in one place, and a text card barely moves because moving text is harder
to read.
"""

MOVES = ("push_in", "pull_out", "pan_right", "pan_left",
         "tilt_down", "tilt_up", "hold_drift")

# Which moves suit which register, most-preferred first.
_BY_REGISTER = {
    "FIGURE":   ("push_in", "pull_out", "hold_drift"),
    "LAB":      ("tilt_down", "pull_out", "push_in"),
    "CASEFILE": ("tilt_down", "hold_drift", "pull_out"),
    "BOARD":    ("tilt_down", "pan_right", "pull_out"),
    "CHART":    ("pan_right", "pull_out", "push_in"),
    "TIMELINE": ("pan_right", "pan_left", "pull_out"),
    "ANATOMY":  ("push_in", "hold_drift", "pull_out"),
    "TEXT":     ("hold_drift", "push_in"),
    "TITLE":    ("pull_out", "hold_drift"),
}

# How far each move travels. Kept modest: a card is 9-13.5 seconds and the
# move should be felt rather than noticed.
_Z_NEAR, _Z_FAR = 1.16, 1.02


def move_for(register, index, last=None):
    """Pick this card's move. Never the same one twice running."""
    pool = [m for m in _BY_REGISTER.get(register or "", MOVES) if m != last]
    if not pool:
        pool = [m for m in MOVES if m != last] or list(MOVES)
    return pool[index % len(pool)]


def filter_for(move, duration, fps=24, w=1920, h=1080):
    """The scale+zoompan chain for one move.

    Returns a filter string ready to sit at the head of a card's chain.
    """
    n = max(2, int(round(duration * fps)))
    # p is 0..1 across the card, from zoompan's output frame counter.
    p = f"(on/{n - 1})"
    big_w, big_h = w * 2, h * 2
    pre = f"scale={big_w}:{big_h}"

    cx = "iw/2-(iw/zoom/2)"
    cy = "ih/2-(ih/zoom/2)"

    if move == "push_in":
        z, x, y = f"{_Z_FAR}+{_Z_NEAR - _Z_FAR:.3f}*{p}", cx, cy
    elif move == "pull_out":
        z, x, y = f"{_Z_NEAR}-{_Z_NEAR - _Z_FAR:.3f}*{p}", cx, cy
    elif move == "pan_right":
        z, x, y = "1.14", f"(iw-iw/zoom)*{p}", cy
    elif move == "pan_left":
        z, x, y = "1.14", f"(iw-iw/zoom)*(1-{p})", cy
    elif move == "tilt_down":
        z, x, y = "1.14", cx, f"(ih-ih/zoom)*{p}"
    elif move == "tilt_up":
        z, x, y = "1.14", cx, f"(ih-ih/zoom)*(1-{p})"
    else:  # hold_drift
        z = f"1.05+0.03*{p}"
        x, y = f"(iw-iw/zoom)*(0.5+0.06*{p})", f"(ih-ih/zoom)*(0.5-0.05*{p})"

    return (f"{pre},zoompan=z='{z}':x='{x}':y='{y}':"
            f"d={n}:s={w}x{h}:fps={fps}")
