"""
WHAT A SHORT ON THIS CHANNEL IS FOR.

Built from real 2026 platform data rather than taste, after the instruction
that the Shorts "are really boring and not even picking up the audience",
and the decision that they must drive SUBSCRIBERS and LONG-FORM VIEWS with
revenue incidental.

The three numbers that set everything else
------------------------------------------
1. LENGTH.  Shorts of 34-52s carry the highest median view count, 2.7x the
   median of Shorts over 90s. Shorts under 40s win on loop rate, and a Short
   that loops earns 3-5x the views of a comparable one that does not. Under
   30s, retention above 100% is routine because the replay counts again.

   The engine used to REQUIRE 120-160 words. At this pipeline's own
   2.6 words/sec that is 46-62 seconds: the top of the good band at best,
   and always past the <40s line where looping actually happens. The single
   biggest multiplier in the format was excluded by the word counter. This
   module sets the band from the seconds, not the other way round.

2. THE FIRST FRAME.  There is no intro in a Short. The first frame is the
   hook and the first word is the hook; 30-50% of viewers leave between
   second 1 and second 3, and the algorithm reads that cliff as low value no
   matter how good the rest is. So a Short may not open with throat-clearing,
   and its opening line must carry a concrete, specific claim.

3. THE LOOP.  The ending must recontextualise the opening so the replay is
   worth having. This is scored structurally -- does a real, specific noun
   from the opening genuinely return at the close -- not by matching a list
   of stock phrases, because a phrase list rewards a formula rather than the
   mechanic.

Why revenue is not the target
-----------------------------
Shorts RPM runs about $0.01-$0.06 against $6-15 for health long-form, and
qualifying at all needs 10M Shorts views in 90 days. Optimising a Short for
its own ad revenue optimises the smallest number in the system. Every source
agrees the earnings come from the funnel: a viewer moved to long-form is
worth 50-100x the same viewer kept on the Short. So the rubric here scores
whether a Short OPENS A QUESTION IT DOES NOT CLOSE -- something the long
video answers -- and whether it gives a real reason to subscribe. Revenue
follows the audience; it is not steered at directly.
"""

import re

# ── length ─────────────────────────────────────────────────────────────
# The band is expressed in SECONDS, because that is what the platform
# measures. Words are derived, so changing the narration pace cannot
# silently move the real duration out of the band again.
TARGET_SECONDS_MIN = 30.0
TARGET_SECONDS_MAX = 42.0     # inside <40s for most of the band, never past 52
HARD_SECONDS_MAX = 52.0       # beyond this the median view count falls away


def words_for_seconds(seconds, words_per_second=2.6):
    return int(round(seconds * words_per_second))


def target_word_band(words_per_second=2.6):
    """(min_words, max_words) for the target seconds band."""
    return (words_for_seconds(TARGET_SECONDS_MIN, words_per_second),
            words_for_seconds(TARGET_SECONDS_MAX, words_per_second))


def seconds_for_words(word_count, words_per_second=2.6):
    return float(word_count) / max(0.1, words_per_second)


# ── the opening ────────────────────────────────────────────────────────
# Throat-clearing. Any of these in the first breath means the hook is not
# in the first frame, which is the one thing a Short cannot survive.
_THROAT_CLEARING = (
    "hi guys", "hey guys", "hello everyone", "welcome back", "in this video",
    "in this short", "today i", "so today", "let me tell you", "you won't believe",
    "before we start", "make sure to", "don't forget to", "what's up",
    "i want to talk about", "let's talk about", "here's a story",
)

# A first line that asserts something checkable beats one that promises.
# A digit, a measurement, a time, or a named role is concrete; "amazing"
# and "incredible" are not.
_CONCRETE = re.compile(
    r"\b\d|\b(?:percent|per cent|hours?|days?|weeks?|months?|years?|minutes?|"
    r"doctors?|surgeons?|nurses?|patients?|scan|scans|biopsy|dose|doses|"
    r"milligrams?|millilitres?|milliliters?|millimoles?|degrees?)\b", re.I)


def opening_line(script):
    s = (script or "").strip()
    m = re.split(r"(?<=[.!?])\s+", s)
    return m[0] if m else s


def score_first_frame(script, hook_text=""):
    """
    0-2. Is the hook genuinely in the first frame?

    Full marks need both halves: no throat-clearing AND a concrete claim in
    the opening line. A clean opening that says nothing specific still loses
    the viewer at second three; it just loses them politely.
    """
    first = (hook_text or opening_line(script) or "").strip()
    low = first.lower()
    if not first:
        return 0.0, ["no opening line"]
    issues = []
    score = 2.0
    if any(low.startswith(p) or p in low[:60] for p in _THROAT_CLEARING):
        score -= 1.5
        issues.append("opens with throat-clearing instead of the hook")
    if not _CONCRETE.search(first):
        score -= 0.7
        issues.append("opening line has no concrete, checkable detail")
    if len(first.split()) > 18:
        score -= 0.4
        issues.append("opening line is too long to land in the first frame")
    return max(0.0, round(score, 2)), issues


# ── the loop ───────────────────────────────────────────────────────────
_LOOP_STOP = {
    "today", "basically", "happened", "something", "because", "before",
    "after", "other", "which", "there", "their", "about", "still", "again",
    "really", "actually", "overall", "would", "could", "should", "these",
    "those", "being", "doing", "going", "where", "while",
}


def score_loop(script):
    """
    0-2. Does the close hand the viewer back to the open?

    Structural on purpose. Matching stock phrases ("but wait", "here's the
    thing") rewards a formula that any script can wear; what actually makes
    a replay worth having is the ending returning to the opening's own
    subject so the first line means something different the second time.
    """
    words = (script or "").split()
    if len(words) < 20:
        return 0.0, ["script too short to carry a loop"]
    # The windows SCALE with the script. Fixed counts (first 12 / last 18)
    # were tuned for a 150-word Short; on the 80-110 word Short this module
    # now targets, the last 18 words are barely the final sentence, so a
    # genuine callback sitting one sentence earlier scored as no loop at all.
    # Checked against a hand-written example that plainly loops and was being
    # marked 0.5. A third of the script at each end is the real "opening" and
    # "closing" of something this length.
    n = len(words)
    head = max(10, int(n * 0.22))
    tail = max(18, int(n * 0.33))
    opening = {w.strip(".,!?;:\"'").lower() for w in words[:head] if len(w) > 4}
    closing = {w.strip(".,!?;:\"'").lower() for w in words[-tail:] if len(w) > 4}
    shared = (opening & closing) - _LOOP_STOP
    if shared:
        return 2.0, []
    return 0.5, ["the ending does not return to anything specific from the "
                 "opening, so a replay adds nothing"]


# ── stakes, for a channel that does not shout ──────────────────────────
# The shared Shorts rubric scores an EMOTIONAL ARC by counting words like
# "devastated" and "horrified" rising across the script. On this channel
# that axis reads 0.0 on every correctly-written script, because the whole
# editorial line is that a real patient's illness is not narrated in tabloid
# adjectives. Same mismatch already fixed for the thumbnail specificity bank
# and the title word list: a rubric manufacturing the register it then
# penalises.
#
# What carries a clinical Short is not emotion vocabulary, it is a TURN --
# the moment the expected outcome stops happening. That is measurable, and
# it is what the viewer actually stays for.
_TURN = re.compile(
    r"\b(then|but|instead|until|however|except|despite|yet|"
    r"reversed?|recovered?|survived?|returned?|stopped|started|"
    r"unexplained|paradoxical|absent from|no one|nobody|never seen)\b", re.I)


def score_turn(script):
    """0-2. Does the story actually turn, and does the turn land late?"""
    s = script or ""
    words = s.split()
    if len(words) < 20:
        return 0.0, ["too short to carry a turn"]
    hits = [m.start() for m in _TURN.finditer(s)]
    if not hits:
        return 0.0, ["nothing turns — the script states a case without a "
                     "moment where the expected outcome stops happening"]
    score = 1.0
    # A turn in the back half is a reveal; a turn in the first line is a
    # throwaway connective.
    if any(h > len(s) * 0.45 for h in hits):
        score += 1.0
    return min(2.0, score), []


# ── the funnel ─────────────────────────────────────────────────────────
# The point of the Short. It must leave one real question open -- the one
# the long video answers -- rather than resolving everything in 40 seconds.
_OPEN_QUESTION = re.compile(
    r"(\?|what (?:no|nobody|none)|why (?:no|nobody|it|she|he|they)|"
    r"(?:no ?one|nobody) (?:has |have |ever |still )?"
    r"(?:could|can|knew|knows|explained|explains|accounted|account)|"
    r"the (?:reason|answer|cause|explanation) (?:was|is|turned out|came)|"
    r"until (?:someone|a|the)|what (?:they|doctors|nobody) (?:found|missed)|"
    r"still (?:unexplained|unknown|no answer))", re.I)

# Asking for the subscribe outright converts worse than giving a reason to
# expect the next one. Both are credited; a real series promise scores best.
_SERIES_PROMISE = re.compile(
    r"(every (?:case|week|day)|one case (?:a|every)|the full case|"
    r"the whole case|next case|more cases|full breakdown|full story)", re.I)
_BARE_ASK = re.compile(r"(subscribe|follow (?:me|us|for))", re.I)


def score_funnel(script):
    """
    0-2. Does this Short send the viewer somewhere, or end in itself?

    A Short that answers its own question completely is a dead end: the
    viewer got the whole thing in 40 seconds and has no reason to click
    anything. That is the difference between a Short that entertains and a
    Short that grows a channel.
    """
    s = script or ""
    issues = []
    score = 0.0
    if _OPEN_QUESTION.search(s):
        score += 1.2
    else:
        issues.append("closes every loop — nothing is left for the long video "
                      "to answer, so there is no reason to click through")
    if _SERIES_PROMISE.search(s):
        score += 0.8
    elif _BARE_ASK.search(s):
        score += 0.3
        issues.append("asks for the subscribe without giving a reason to "
                      "expect the next one")
    else:
        issues.append("gives the viewer no reason to come back")
    return min(2.0, round(score, 2)), issues


def score_length(word_count, words_per_second=2.6):
    """0-2 on the real duration, with the band read off the seconds."""
    secs = seconds_for_words(word_count, words_per_second)
    if TARGET_SECONDS_MIN <= secs <= TARGET_SECONDS_MAX:
        return 2.0, [], secs
    if 25.0 <= secs < TARGET_SECONDS_MIN or TARGET_SECONDS_MAX < secs <= HARD_SECONDS_MAX:
        return 1.2, ["%.0fs is outside the 30-42s band where loops happen" % secs], secs
    return 0.3, ["%.0fs is well outside the band — 34-52s carries 2.7x the "
                 "median views of long Shorts, and looping needs under 40s"
                 % secs], secs


def spec_block(words_per_second=2.6):
    """The mechanical spec, written for the generator rather than for a human."""
    lo, hi = target_word_band(words_per_second)
    return """
This Short is mechanically scored. Write to hit every one of these.

LENGTH: %d-%d words. That is %.0f-%.0f seconds of narration. Do not go
  over: Shorts past ~52s lose most of their reach, and under 40s is where
  the replay loop that multiplies views actually happens.

FIRST FRAME: the very first sentence IS the hook. No "hi guys", no "in this
  video", no setup. Open on a concrete, checkable detail -- a number, a
  measurement, a timespan, a named role. Not "something incredible".

LOOP: the last sentence must return to a specific noun, name or number from
  the FIRST sentence, so that replaying the opening means something new.
  Not a stock phrase -- the actual subject.

LEAVE ONE QUESTION OPEN: this Short must NOT answer everything. End on the
  thing the full video explains. A Short that resolves itself gives the
  viewer no reason to click through, and clicking through is the entire
  point.

GIVE A REASON TO COME BACK: promise what the next one is ("a real case
  every week", "the full case is on the channel"). Do not simply say
  "subscribe" -- a bare ask converts worse than a stated reason.
""" % (lo, hi, TARGET_SECONDS_MIN, TARGET_SECONDS_MAX)
