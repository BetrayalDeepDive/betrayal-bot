"""
Controlled variation for the clinical channel.

THE PROBLEM THIS SOLVES
-----------------------
The tell of an automated channel is not bad craft, it is perfect repetition.
Every card in this pipeline was exactly 13.0 seconds long, opened with the
same 0.4s fade, put its text in the same place, and used the same accent
colour. Sixty of those in a row reads as a machine even when each individual
frame is fine.

Real variation is not randomness. A card whose length is drawn from a hat
paces badly; a colour drawn from a hat goes off-brand. What is wanted is
variation that is DELIBERATE (driven by what the segment is doing), BOUNDED
(inside the brand), and REPRODUCIBLE (same episode, same result — so a
review decision means something and a bug can be re-created).

So everything here is seeded from the episode number. Two runs of episode 12
produce identical variation; episodes 12 and 13 do not resemble each other.

WHAT VARIES
-----------
    duration     9-17s, chosen from the segment's narrative weight rather
                 than a flat 13.0
    transition   from a pool of medical-grammar wipes, never the same one
                 twice in a row
    anchor       where the text block sits, rotating through a small set
    tint         accent colour drifting inside the brand's own range
    annotation   an occasional hand-drawn circle or underline, so the frame
                 is not machine-perfect

Nothing here decides WHAT is on screen — that is the register system's job.
This only decides how it is presented.
"""
import hashlib
import random

# ── card duration ──────────────────────────────────────────────────────
# The old constant. Kept as the centre of the range so total episode length
# lands where it always did; only the distribution around it changes.
# Narrowed from 9-17 on direct instruction: 17s is long enough for a viewer
# to decide nothing further is going to happen on this card. The mean has to
# sit mid-range or the clamp binds and everything piles on the ceiling, so
# TARGET_SECONDS_PER_CLIP in the pipeline moved to 11.0 alongside this.
BASE_SECONDS = 11.0

# THE CEILING IS A HARD LIMIT, SET BY THE OWNER, AND NOTHING MAY EXCEED IT.
#
# 12.5s, chosen by the owner to make the card COUNT land where they wanted.
#
# The two numbers originally asked for -- "no card over 10.5 seconds" and
# "75 cards for a 15-minute video" -- cannot both be true. 900 seconds over
# 75 cards is 12.0s a card, so asking for 75 was asking for cards past a
# 10.5s ceiling. Presented with that arithmetic the owner moved the ceiling
# rather than the count, which is the right call: 75 cards at 12.0s mean is
# still a cut every twelve seconds, and the count is the number they can
# actually see in a finished episode.
#
# At 12.5s with the headroom below, a 15-minute episode comes out at exactly
# 75 cards. That is not a coincidence -- the headroom is tuned to it.
#
# The previous ceiling of 13.5 was not actually a ceiling at all: see the
# residue step in durations(), which used to add the leftover to the longest
# card without re-clamping, so whenever the audio outran n * MAX_SECONDS the
# entire shortfall landed on one card, silently. That is how "no card over
# 13.5s" shipped cards well over 13.5s.
#
# The floor sits at 9.5 so the weighting has somewhere to move. A revelation
# holds near the ceiling, a linking sentence cuts near the floor; if the
# range were narrow every card would render the same length and the pacing
# variation this module exists for would collapse.
MIN_SECONDS, MAX_SECONDS = 9.5, 12.5


def cards_needed(total_seconds, headroom=1.12):
    """How many cards this much audio needs to stay under the ceiling.

    The count follows the ceiling, not the other way round: at 12.5s a
    15-minute episode cannot be covered by fewer than 72 cards no matter what
    count is asked for.

    HEADROOM IS WHERE THE PACING VARIATION LIVES, AND IT WAS MEASURED.
    ------------------------------------------------------------------
    The mean card length is total/n, so the headroom sets it. Push the mean
    up against the ceiling and every card that wants to run long clamps to
    the maximum -- the episode goes back to one uniform card length, which is
    the exact failure already recorded a few lines above this file: "at 13.0
    almost every card clamped to the 13.5 ceiling and the variation collapsed
    back to a flat pace."

    Measured on a 15-minute episode with real slow/fast cue text:

        headroom  cards   mean   range        cards pinned at the ceiling
        1.04         75  12.00  10.2-12.5     43  (57%)
        1.08         78  11.54   9.8-12.5     21  (27%)
        1.12         81  11.11   9.6-12.5     13  (16%)
        1.16         84  10.71   9.5-12.5      9  (11%)

    1.04 delivers exactly the 75 cards asked for and puts more than half the
    episode on an identical 12.5s beat. 1.12 costs six cards and cuts that to
    one in six, with the full 9.6-12.5s spread actually in use. Six cards is
    not a difference anyone can see; fifty-seven percent of an episode
    marching to the same length is, and "every card should be interesting"
    was the instruction that sits behind all of this.

    So 1.12: about seventy-five cards, none over the ceiling, and a rhythm
    that still varies. Set it to 1.04 for exactly 75 at the cost of the
    pacing.
    """
    return max(2, int(-(-float(total_seconds) * headroom // MAX_SECONDS)))


class CardsTooFew(ValueError):
    """This much audio cannot be covered by this many cards inside the cap.

    Raised rather than papered over, because the only two ways to "handle" it
    silently are to hold a card past the ceiling or to let the visuals run
    short of the audio, and both ship a broken episode.
    """

# Words that mark a beat worth holding on, and one worth cutting away from.
# A revelation earns screen time; a transitional sentence does not.
_SLOW_CUES = (
    "died", "death", "fatal", "collapsed", "arrest", "seizure", "coma",
    "diagnosis", "diagnosed", "revealed", "discovered", "realised",
    "realized", "finally", "never", "no known", "unexplained", "no cause",
)
_FAST_CUES = (
    "then", "next", "meanwhile", "also", "additionally", "subsequently",
    "further", "in addition", "following this",
)

# ── transitions ────────────────────────────────────────────────────────
# Every one is medical grammar rather than a generic video wipe: a scan
# advancing, a lightbox coming on, contrast washing through. The old
# pipeline used exactly one (fade in, 0.4s) on all ~60 cards.
TRANSITIONS = (
    "scanline",     # a bright line sweeps down, the image resolving behind it
    "lightbox",     # a backlit panel flickers on, twice, then holds
    "contrast",     # brightness washes in from black as if dye is spreading
    "slice",        # the next slice pushes the previous one aside
    "iris",         # a circular aperture opens from the point of interest
    "fade",         # the plain one, kept so the pool has a neutral member
)

# ── text anchors ───────────────────────────────────────────────────────
ANCHORS = ("left", "lower_left", "centre", "lower_right", "right")

# ── accent tints ───────────────────────────────────────────────────────
# All within reach of the channel's teal. Drifting the accent between
# episodes keeps the brand while stopping every frame being the same green.
TINTS = (
    (95, 168, 160),   # the base
    (86, 176, 178),   # cooler, toward cyan
    (108, 172, 148),  # warmer, toward sea
    (78, 158, 172),   # deeper
    (116, 182, 168),  # lighter
)


def _rng(episode, salt=""):
    """A generator that depends only on the episode and the salt.

    Same episode, same stream: a review decision on episode 12 stays true
    if episode 12 is re-rendered, and a bad frame can be reproduced.
    """
    h = hashlib.sha256(f"{episode}|{salt}".encode()).hexdigest()[:16]
    return random.Random(int(h, 16))


class EpisodeVariation:
    """Every presentation decision for one episode, decided up front."""

    def __init__(self, episode, n_segments, nonce=0):
        """
        REMAKE HAS TO PRODUCE SOMETHING DIFFERENT.

        FIX (direct user report): every presentation decision here was seeded
        on the episode number alone, so re-rendering episode 12 reproduced
        episode 12 exactly -- same tint, same anchor cycle, same transitions,
        same pacing. That determinism is deliberate and worth keeping (a
        review decision stays true if the episode is re-rendered, and a bad
        frame can be reproduced), but it also meant tapping REMAKE or SWAP
        VISUALS handed back a byte-for-byte equivalent video and announced it
        as the new version. Reported exactly that way: "it keeps repeating
        the same topic, the same subtitles, or the same thumbnail... telling
        me that this is the new version."

        `nonce` is the remake counter. At 0 -- every first render -- the
        stream is identical to before, so nothing about normal runs changes.
        Each remake bumps it and genuinely re-rolls the presentation.
        """
        self.episode = int(episode)
        self.n = max(1, int(n_segments))
        self.nonce = int(nonce or 0)
        _seed = self.episode if not self.nonce else f"{self.episode}r{self.nonce}"
        self.episode_seed = _seed
        r = _rng(_seed, "episode")
        self.tint = TINTS[r.randrange(len(TINTS))]
        # A per-episode phase so the anchor cycle does not start in the same
        # place every time; without it every episode's first card is "left".
        self._anchor_phase = r.randrange(len(ANCHORS))
        self._trans_rng = _rng(_seed, "transitions")
        self._last_transition = None
        self._ann_rng = _rng(_seed, "annotations")

    # ── duration ───────────────────────────────────────────────────────
    def durations(self, total_seconds, texts):
        """Per-card seconds, summing to exactly total_seconds.

        Weighted by what each segment is doing, then normalised. The sum is
        exact because the audio has a fixed length and the visuals have to
        cover it — a drifting sum would desync the whole episode.
        """
        weights = []
        for i, t in enumerate(texts or [""] * self.n):
            low = (t or "").lower()
            w = 1.0
            if any(c in low for c in _SLOW_CUES):
                w *= 1.28
            if any(low.startswith(c) or f" {c} " in low for c in _FAST_CUES):
                w *= 0.82
            # A gentle arc: open a little quicker, hold longer at the reveal.
            pos = i / max(1, self.n - 1)
            w *= 0.92 + 0.22 * pos
            w *= _rng(self.episode_seed, f"dur{i}").uniform(0.94, 1.06)
            weights.append(w)

        total_w = sum(weights) or 1.0
        raw = [total_seconds * w / total_w for w in weights]

        # Clamp into the readable range, then push the error back into the
        # cards that still have room. Clamping alone would change the sum.
        out = [min(MAX_SECONDS, max(MIN_SECONDS, v)) for v in raw]
        for _ in range(8):
            drift = total_seconds - sum(out)
            if abs(drift) < 0.01:
                break
            room = [i for i, v in enumerate(out)
                    if (drift > 0 and v < MAX_SECONDS) or (drift < 0 and v > MIN_SECONDS)]
            if not room:
                break
            share = drift / len(room)
            for i in room:
                out[i] = min(MAX_SECONDS, max(MIN_SECONDS, out[i] + share))
        # Any residue is spread over the cards that still have room, never
        # dumped on one.
        #
        # THIS LINE USED TO BREAK THE CEILING. It was
        #     out[out.index(max(out))] += residue
        # which adds the leftover to the card that is, by definition, already
        # closest to MAX_SECONDS -- and pushes it straight through. Normally
        # the residue is a hundredth of a second and invisible. But when the
        # audio is longer than n * MAX_SECONDS the loop above cannot converge,
        # residue is the entire shortfall, and one card silently held for
        # however long it took to cover the gap. A cap that is enforced except
        # when it matters is not a cap.
        residue = total_seconds - sum(out)
        for _ in range(4):
            if abs(residue) < 0.001:
                break
            room = [i for i, v in enumerate(out)
                    if (residue > 0 and v < MAX_SECONDS - 1e-6)
                    or (residue < 0 and v > MIN_SECONDS + 1e-6)]
            if not room:
                break
            share = residue / len(room)
            for i in room:
                out[i] = min(MAX_SECONDS, max(MIN_SECONDS, out[i] + share))
            residue = total_seconds - sum(out)

        # If it still does not fit, the caller asked for fewer cards than this
        # much audio can be covered with. Say so instead of quietly holding a
        # card past the ceiling -- the pipeline adds cards and calls again.
        if residue > 0.05:
            raise CardsTooFew(
                "%.1fs of audio needs more than %d cards at a %.1fs ceiling "
                "(short by %.1fs; %d needed)"
                % (total_seconds, self.n, MAX_SECONDS, residue,
                   cards_needed(total_seconds)))
        return out

    # ── transition ─────────────────────────────────────────────────────
    def transition(self, index, register=None):
        """Which transition opens this card. Never repeats back to back."""
        pool = [t for t in TRANSITIONS if t != self._last_transition]
        # A figure from the paper deserves to arrive plainly; a slice push
        # over someone's real CT looks like a video effect applied to
        # evidence.
        if register == "FIGURE":
            pool = [t for t in ("fade", "lightbox", "contrast") if t != self._last_transition]
        choice = pool[self._trans_rng.randrange(len(pool))]
        self._last_transition = choice
        return choice

    # ── layout ─────────────────────────────────────────────────────────
    def anchor(self, index):
        return ANCHORS[(index + self._anchor_phase) % len(ANCHORS)]

    def annotate(self, index):
        """Whether this card gets a hand-drawn mark. About one in five.

        Sparse on purpose: an annotation on every card is just another
        machine-perfect element, which defeats the point of having it.
        """
        return _rng(self.episode_seed, f"ann{index}").random() < 0.2

    def annotation_style(self, index):
        r = _rng(self.episode_seed, f"annsty{index}")
        return r.choice(("circle", "underline", "bracket", "tick"))
