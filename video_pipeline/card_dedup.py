"""
NO TWO CARDS NEAR EACH OTHER MAY LOOK THE SAME.

The complaint this exists to answer, verbatim: "the background visuals are
very less and they are only repeating in entire video. I saw somewhere around
8-10 cards that were playing continuously for entire video."

That episode rendered 122 segments. It did not render 8-10. What it rendered
was 122 cards drawn from about four pieces of source material -- the paper's
figures had all failed to download, there was no chart data, one timeline
entry and one differential -- so the same handful of frames came back around
and around. Every existing check passed, because every existing check asks
"did a card render?" and the answer was yes, 122 times.

Nothing in the pipeline had ever looked at two finished cards and asked
whether they were the same picture. This does.

HOW IT DECIDES
--------------
A difference hash (dHash) of a frame pulled from the middle of the card.
Each frame is reduced to 9x8 greyscale and turned into 64 bits, one per
horizontal neighbour comparison. Two cards are "the same" when their hashes
differ in fewer than DISTINCT_BITS positions.

dHash rather than an exact checksum because the cards are not bit-identical:
the same underlying photograph rendered with a different accent tint, a
different transition or a different anchor produces different bytes and the
same picture. A checksum would call those distinct and report a clean run
over exactly the footage the owner complained about. dHash compares what the
frame LOOKS like, which is the thing being judged.

The middle frame, not the first: cards open on a transition, and every card
that opens on a fade starts from the same near-black frame.

WINDOW, NOT WHOLE EPISODE
-------------------------
Repeats are only checked inside a rolling window. A paper has five figures
and an episode has a hundred cards; demanding a hundred distinct images is
demanding something the source cannot supply, and a rule that cannot be
satisfied gets switched off. What actually reads as "it keeps repeating" is
the same picture coming back while the viewer still remembers it. Outside the
window a reprise is fine, and in a case documentary it is often right --
returning to the CT at the reveal is a deliberate callback.
"""
import subprocess
import tempfile
import os

# Hamming distance below which two frames are the same picture. 10 of 64
# bits: tight enough that a re-tinted reuse of one photograph still counts as
# a repeat, loose enough that two genuinely different photographs of the same
# ward corridor do not both get thrown away.
DISTINCT_BITS = 10

# How many cards must pass before the same picture may come back. At roughly
# 9s a card, 12 cards is about a minute and three quarters of screen time.
DEFAULT_WINDOW = 12


def _middle_frame_png(clip_path, seconds=None, timeout=25):
    """One frame from the middle of the clip, as PNG bytes. None on failure."""
    ts = 1.0 if not seconds else max(0.2, float(seconds) / 2.0)
    fd, tmp = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-ss", "%.2f" % ts,
             "-i", str(clip_path), "-frames:v", "1", "-vf", "scale=64:64",
             tmp],
            check=True, timeout=timeout,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with open(tmp, "rb") as f:
            data = f.read()
        return data or None
    except Exception:
        return None
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def fingerprint(clip_path, seconds=None):
    """64-bit dHash of this card's middle frame, or None if it can't be read.

    None is returned rather than raised, and the ledger treats None as "no
    opinion". A fingerprint that cannot be computed must never be the reason
    a card gets rejected -- that would turn an ffmpeg hiccup into a rendering
    failure, which is a worse bug than the one being fixed.
    """
    png = _middle_frame_png(clip_path, seconds)
    if not png:
        return None
    try:
        import io
        from PIL import Image
        im = Image.open(io.BytesIO(png)).convert("L").resize((9, 8))
        px = list(im.getdata())
        bits = 0
        for row in range(8):
            for col in range(8):
                left = px[row * 9 + col]
                right = px[row * 9 + col + 1]
                bits = (bits << 1) | (1 if left > right else 0)
        return bits
    except Exception:
        return None


def distance(a, b):
    """How many of the 64 bits differ."""
    return bin(a ^ b).count("1")


class VisualLedger:
    """Every card's fingerprint, and whether each one repeated a recent card."""

    def __init__(self, window=DEFAULT_WINDOW, bits=DISTINCT_BITS):
        self.window = window
        self.bits = bits
        self.prints = []          # (index, fingerprint) in render order
        self.repeats = []         # (index, matched_index, distance)
        self.unreadable = 0

    def check(self, index, fp):
        """Does this card repeat one still fresh in the viewer's memory?

        Returns (is_repeat, matched_index, distance). Records either way, so
        the run-end summary reflects what was actually rendered rather than
        what survived a filter.
        """
        if fp is None:
            self.unreadable += 1
            return (False, None, None)
        best_i, best_d = None, 65
        for j, (idx, other) in enumerate(self.prints[-self.window:]):
            d = distance(fp, other)
            if d < best_d:
                best_i, best_d = idx, d
        if best_i is not None and best_d < self.bits:
            self.repeats.append((index, best_i, best_d))
            return (True, best_i, best_d)
        return (False, best_i, best_d if best_i is not None else None)

    def record(self, index, fp):
        """Accept this card into the ledger. Call after check() passes, or
        after the last retry, so the next card compares against what is
        actually on screen."""
        if fp is not None:
            self.prints.append((index, fp))

    def distinct_count(self):
        """How many genuinely different pictures the episode contains.

        This is the number the owner was really reporting when they said
        "8-10 cards". Greedy clustering: walk the fingerprints in order and
        open a new cluster whenever a frame is far from every cluster seen so
        far. Approximate by construction, and that is fine -- it is a health
        readout, not a gate.
        """
        clusters = []
        for _idx, fp in self.prints:
            if not any(distance(fp, c) < self.bits for c in clusters):
                clusters.append(fp)
        return len(clusters)

    def summary(self):
        n = len(self.prints)
        distinct = self.distinct_count()
        pct = (100.0 * distinct / n) if n else 0.0
        line = ("Visual variety: %d distinct pictures across %d cards (%.0f%%), "
                "%d near-repeat(s) inside a %d-card window"
                % (distinct, n, pct, len(self.repeats), self.window))
        if self.unreadable:
            line += ", %d card(s) unreadable" % self.unreadable
        return line

    def too_repetitive(self, floor=0.55):
        """True when the episode is the failure the owner described.

        The floor is a share of cards, not an absolute count, so it means the
        same thing for a 15-minute episode and a 30-minute one. 0.55 is set
        from the episode that prompted this: it would have scored far under,
        while an episode that reprises each of a paper's five figures a
        couple of times at the right moments sits comfortably above.
        """
        n = len(self.prints)
        if n < 10:
            return False
        return (self.distinct_count() / float(n)) < floor
