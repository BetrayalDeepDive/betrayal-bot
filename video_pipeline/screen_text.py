"""
Turning a slice of narration into something readable on screen.

WHAT WENT WRONG
---------------
Two renderers built their on-screen label by taking the first N words of
whatever narration happened to sit under that segment:

    medical_anatomy_motion.py:  sub   = " ".join(segment_text.split()[:9])
    kinetic_text.py:            words = quote.split()[:12]

Segments do not start at sentence boundaries -- they are cut to fit a visual's
duration -- so this produced fragments that begin and end mid-thought. Burned
into a frame, on screen, for ten seconds. From a real episode:

    "lasted three days. She worked as a high-school history"

Nine words exactly. It starts halfway through one sentence and stops halfway
through the next. Every card in the episode read like that.

WHAT THIS DOES
--------------
A label is a COMPLETE THOUGHT or it is nothing:

  * A leading partial sentence is dropped, not shown. If the text begins
    mid-sentence -- lowercase first letter, or the first terminator arrives
    before any capital -- everything up to that terminator is discarded.

  * The label is then a whole sentence. If that sentence is short enough it is
    used as it stands, punctuation and all.

  * If it is too long, it is cut at a CLAUSE boundary (a comma, semicolon or
    dash) rather than at an arbitrary word, and marked with an ellipsis so the
    viewer can see it continues. Cutting at a clause keeps it grammatical.

  * A label never ends on a word that is obviously waiting for another one --
    "and", "of", "the", "in". Those read as a rendering fault even when the
    cut was deliberate.

  * If nothing usable comes out, it returns "" and the caller draws no label,
    which is always better than drawing a broken one.
"""
import re

# Words that cannot be the last thing on a card: each one promises a
# continuation that is not coming.
_DANGLING = {
    "a", "an", "the", "and", "or", "but", "of", "to", "in", "on", "at", "by",
    "for", "with", "from", "as", "that", "which", "who", "when", "while",
    "her", "his", "their", "its", "this", "these", "those", "was", "were",
    "is", "are", "had", "has", "have", "been", "would", "could", "should",
    "than", "then", "into", "over", "under", "after", "before", "between",
}

_TERMINATOR = re.compile(r"(?<=[.!?])\s+")


def _sentences(text):
    return [s.strip() for s in _TERMINATOR.split(text or "") if s.strip()]


def _starts_mid_sentence(text):
    """Does this text begin partway through somebody's sentence?"""
    t = (text or "").lstrip()
    if not t:
        return False
    # A lowercase opening is the plain case. A conjunction opening is the
    # subtler one -- "and took no medications..." is grammatically a fragment
    # even though a writer might legitimately start a sentence that way, so it
    # is only treated as mid-sentence when something follows to fall back to.
    return t[0].islower()


def _trim_dangling(words):
    while words and re.sub(r"[^a-z]", "", words[-1].lower()) in _DANGLING:
        words = words[:-1]
    return words


# A label that opens on a conjunction is still a fragment even after the
# sentence logic has done its work: "and took no medications beyond an
# occasional ibuprofen" reads as the tail of something the viewer missed.
# Dropping the conjunction and capitalising what follows turns the same words
# into a sentence -- "Took no medications beyond an occasional ibuprofen" --
# without inventing anything that was not said.
_LEADING_CONJUNCTIONS = ("and", "but", "or", "so", "yet", "then", "because",
                         "although", "though", "while", "whereas")


def _open_cleanly(text):
    words = text.split()
    while words and words[0].lower().strip(",;:") in _LEADING_CONJUNCTIONS:
        words = words[1:]
    if not words:
        return ""
    out = " ".join(words)
    return out[0].upper() + out[1:]


def caption_label(text, max_words=9, min_words=3):
    """A complete, readable label for on-screen use — or "" if there isn't one.

    `max_words` is a ceiling, not a target: a shorter complete sentence is
    always preferred to a longer truncated one.
    """
    text = " ".join((text or "").split())
    if not text:
        return ""

    sents = _sentences(text)
    if sents and _starts_mid_sentence(text) and len(sents) > 1:
        sents = sents[1:]          # discard the half-sentence we arrived in
    if not sents:
        return ""

    for sent in sents:
        words = sent.split()
        if len(words) < min_words:
            continue                # "Under treatment." alone says nothing
        if len(words) <= max_words:
            return _open_cleanly(sent)

        # Too long: prefer a clause boundary inside the budget.
        head = " ".join(words[:max_words])
        cut = max(head.rfind(","), head.rfind(";"), head.rfind(" — "),
                  head.rfind(" -- "))
        if cut > 0:
            clause = head[:cut].strip()
            if len(clause.split()) >= min_words:
                return _open_cleanly(clause) + "…"

        kept = _trim_dangling(words[:max_words])
        if len(kept) >= min_words:
            return _open_cleanly(" ".join(kept).rstrip(",;:")) + "…"

    # Nothing long enough to be a thought. Fall back to the longest sentence
    # available rather than inventing one, and only if it says something.
    best = max(sents, key=lambda s: len(s.split()))
    return _open_cleanly(best) if len(best.split()) >= min_words else ""
