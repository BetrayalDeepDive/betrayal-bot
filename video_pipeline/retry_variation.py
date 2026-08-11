"""
A RETRY THAT PRODUCES THE SAME ANSWER IS NOT A RETRY.

Direct user report, repeated over several days and finally with a
screenshot: the thumbnail gate logged

    Attempt  1/13: 5.5/10 (gate 8.5) - below gate 'HOURS LATER'
    Attempt  2/13: 5.5/10 (gate 8.5) - below gate 'HOURS LATER'
    ... thirteen identical lines ...

Thirteen attempts, one candidate. The gate was not being given thirteen
chances to find something better; it was being handed the same answer
thirteen times and scoring it thirteen times. The same shape shows up
wherever a stage "remakes" after a failure: the prompt does not change, so
the model has no reason to answer differently, and the rework is a
formality that burns the budget and reports progress it did not make.

The missing ingredient is memory. A model asked the identical question
returns its most likely answer, which is the answer that just failed.
Telling it what has already been rejected is what makes attempt two a
genuinely different attempt from attempt one.

This module is deliberately small and has no dependencies: every gate can
adopt it without restructuring, which is the only way it gets adopted
everywhere rather than in the one place that was complained about.
"""

import re


def _norm(text):
    """Case/spacing/punctuation-insensitive form, for comparing candidates."""
    return re.sub(r"[^a-z0-9 ]", "", str(text or "").lower()).strip()


def _tokens(text):
    return set(_norm(text).split())


def similarity(a, b):
    """Jaccard overlap of word sets. 1.0 identical, 0.0 nothing shared."""
    ta, tb = _tokens(a), _tokens(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / float(len(ta | tb))


class AttemptLedger:
    """
    Remembers what a gate has already tried and rejected.

    `near` is why this is not just a set: "HOURS LATER" and "HOURS LATER?"
    are the same idea wearing a different hat, and counting the second as a
    fresh attempt is how thirteen attempts became one.
    """

    def __init__(self, label="", near=0.8):
        self.label = label
        self.near = float(near)
        self.rejected = []   # [(text, score)]

    def is_repeat(self, text):
        """True when this candidate is one already rejected, or near enough."""
        if not str(text or "").strip():
            return False
        for prev, _ in self.rejected:
            if _norm(prev) == _norm(text):
                return True
            if similarity(prev, text) >= self.near:
                return True
        return False

    def note(self, text, score=None):
        if str(text or "").strip():
            self.rejected.append((str(text), score))

    def avoid_clause(self, limit=10, what="answer"):
        """
        The prompt fragment that makes the next attempt a real attempt.

        Empty on the first try -- there is nothing to avoid yet -- so a gate
        can add it unconditionally without special-casing attempt one.
        """
        if not self.rejected:
            return ""
        seen = []
        for text, score in reversed(self.rejected):
            if text not in seen:
                seen.append(text)
            if len(seen) >= limit:
                break
        listed = "\n".join("- %s" % s for s in seen)
        return (
            "\n\nALREADY TRIED AND REJECTED — do not repeat any of these, and "
            "do not return a reworded version of one. Produce a genuinely "
            "different %s, from a different angle:\n%s\n" % (what, listed)
        )

    def __len__(self):
        return len(self.rejected)
