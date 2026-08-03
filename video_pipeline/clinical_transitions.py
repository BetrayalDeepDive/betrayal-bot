"""
Card-opening transitions in medical grammar.

WHAT WAS THERE BEFORE
---------------------
    fade=t=in:st=0:d=0.4

One transition, on all ~60 cards of every episode, forever. That is the
loudest tell of an assembled video: not that any one cut is bad, but that
every single one is identical.

WHAT THESE ARE
--------------
Each is a thing that happens on medical equipment rather than a stock video
wipe — a slice advancing, a lightbox stuttering on, contrast washing through
a vessel, a shutter opening. clinical_variation picks one per card and never
picks the same one twice running.

WHY overlay AND NOT drawbox
---------------------------
The first implementation built the wipes from drawbox with expressions like
h='ih*t/0.6'. Measured on ffmpeg 6.1.1, that silently does not animate:
drawbox evaluates its geometry ONCE at filter init, so the box is drawn at a
single fixed size for the whole clip. The failure is invisible in the exit
code — every render succeeded — and it produced two opposite bugs from the
same cause. A growing box came out covering the entire frame forever; a
shrinking one came out covering nothing at all. Adding enable= changed
nothing, because the geometry was already frozen.

overlay does re-evaluate x/y per frame (eval=frame is its default), so every
wipe here is a full-frame cover that SLIDES off, rather than a box that
resizes. Same look, and it actually moves.

fade and eq are used where they fit: both genuinely animate, both are cheap.

Each transition returns the extra ffmpeg inputs it needs plus a
filter_complex fragment, because an overlay needs something to overlay.
"""

TEAL_HEX = "0x5FA8A0"

DURATIONS = {
    "scanline": 0.60,
    "lightbox": 0.42,
    "contrast": 0.55,
    "slice":    0.38,
    "shutter":  0.45,
    "fade":     0.40,
}

NAMES = tuple(DURATIONS)


def _cover(w, h, dur):
    """A black source to slide across the frame."""
    return ["-f", "lavfi", "-i", f"color=black:s={w}x{h}:d={dur + 1:.2f}:r=24"]


def build(name, duration=None, w=1920, h=1080):
    """Return (extra_input_args, complex_fragment).

    The fragment consumes [base] and produces [vout]. Fragments that need no
    second input simply filter [base] through.

    An unknown name falls back to a plain fade rather than raising: a typo
    should cost one card its transition, not kill a four-hour render.
    """
    d = duration if duration is not None else DURATIONS.get(name, 0.40)

    if name == "scanline":
        # Full-frame black with a teal band along its top edge, sliding down.
        # The band ends up riding the leading edge of the reveal, which is
        # what a scanner actually looks like.
        return _cover(w, h, d), (
            f"[1:v]drawbox=x=0:y=0:w=iw:h=14:color={TEAL_HEX}@0.9:t=fill[cov];"
            f"[base][cov]overlay=x=0:y='H*min(t/{d}\\,1)':eval=frame[vout]"
        )

    if name == "slice":
        # The next slice advancing across the previous one, left to right.
        return _cover(w, h, d), (
            f"[base][1:v]overlay=x='W*min(t/{d}\\,1)':y=0:eval=frame[vout]"
        )

    if name == "shutter":
        # Two half-height covers retracting from the centre line.
        half = h // 2
        ins = (["-f", "lavfi", "-i", f"color=black:s={w}x{half}:d={d + 1:.2f}:r=24"] * 2)
        return ins, (
            f"[base][1:v]overlay=x=0:y='-(H/2)*min(t/{d}\\,1)':eval=frame[s1];"
            f"[s1][2:v]overlay=x=0:y='H/2+(H/2)*min(t/{d}\\,1)':eval=frame[vout]"
        )

    if name == "lightbox":
        # A backlit panel stuttering on: two false starts, then it holds.
        #
        # Not chained fades. Measured: a completed fade=t=out holds the
        # stream black for the rest of the clip, so a following fade=t=in
        # ramps black up to black. Five chained fades produced a card that
        # was simply black the whole way through — and it rendered without
        # error, which is how it survived the first check.
        #
        # One brightness envelope instead, which eq re-evaluates per frame.
        ramp = max(0.08, d - 0.22)
        return [], (
            "[base]eq=brightness='"
            "if(lt(t,0.05),-1,"
            "if(lt(t,0.09),0,"
            "if(lt(t,0.13),-1,"
            "if(lt(t,0.18),0,"
            "if(lt(t,0.22),-1,"
            f"if(lt(t,{d}),-1+(t-0.22)/{ramp:.3f},0))))))'"
            ":eval=frame[vout]"
        )

    if name == "contrast":
        # Brightness washing in, the way contrast fills a vessel.
        return [], (
            f"[base]eq=brightness='if(lt(t,{d}),-0.42+0.42*t/{d},0)':eval=frame,"
            f"fade=t=in:st=0:d={min(0.25, d):.2f}[vout]"
        )

    return [], f"[base]fade=t=in:st=0:d={d:.2f}[vout]"
