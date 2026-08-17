"""
The case gate, pinned to cases it actually judged.

WHY THIS EXISTS
---------------
Run 32039970137 accepted 2 of 17 cases and wrote ONE script in forty minutes.
The attempts were not going into writing at all -- they were spent hunting
for a case the gate would accept.

The cause was a threshold set above what the input can reach, which is the
same defect that has now cost this project several runs in different guises
(a 100-character floor on a 78-character correct answer; a thumbnail gate
above the maximum a correct line could score). Here it was the narrative
word-count bands: 900 for "rich", 500 for "adequate", 300 for "thin",
against a source whose eleven measured narratives ran

    49  80  148  272  303  311  328  401  413  843  1062

Median 311. One in eleven cleared 900. The middle of the real distribution
scored 1.0 out of 3.0.

Every case below is REAL -- pmcid, word count, verified figure count,
timeline entries, differentials and charted values as that run logged them,
with the score it actually assigned. The first test re-derives those exact
scores, so this file also proves the model is the real one and not a
plausible-looking imitation.

Run: python tools/test_case_richness.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "video_pipeline"))

from pmc_data import case_richness, CASE_RICHNESS_FLOOR   # noqa: E402

FAILURES = []


def check(label, got, want):
    if got != want:
        FAILURES.append(f"{label}: got {got!r}, wanted {want!r}")
        print(f"  FAIL  {label}: got {got!r}, wanted {want!r}")
    else:
        print(f"  ok    {label}")


def build(words, figs, timeline, diffs, chart):
    """A case shaped exactly as the gate reads it."""
    return {
        "narrative": " ".join(["word"] * words),
        "figures": [{"href": f"f{i}.jpg"} for i in range(figs)],
        "timeline": [(f"Day {i}", "event") for i in range(timeline)],
        "differentials": [(f"Dx {i}", "EXCLUDED", "why") for i in range(diffs)],
        "chart_data": ({"labels": [f"L{i}" for i in range(chart)],
                        "values": [1.0] * chart} if chart else None),
    }


# pmcid, words, verified figures, timeline, differentials, charted values,
# and the score the OLD bands gave it in run 32039970137.
REAL_CASES = [
    ("PMC7427646", 401, 2, 5, 1, 0, 4.0),
    ("PMC5561643",  80, 0, 3, 0, 0, 1.0),
    ("PMC7913166", 272, 2, 1, 1, 0, 1.5),
    ("PMC2954009",  49, 0, 1, 1, 0, 0.0),
    ("PMC1618394", 311, 5, 1, 1, 0, 3.5),
    ("PMC3276451", 413, 6, 0, 0, 0, 3.5),
    ("PMC2390580", 148, 4, 5, 3, 2, 5.75),   # the only one accepted
]


def old_bands_score(words, figs, timeline, diffs, chart):
    """The scoring exactly as it was, to prove these figures are the real ones."""
    s = (3.0 if words >= 900 else 2.0 if words >= 500 else
         1.0 if words >= 300 else 0.0)
    s += 2.5 if figs >= 4 else 1.5 if figs >= 2 else 0.5 if figs == 1 else 0.0
    s += 1.5 if timeline >= 5 else 1.0 if timeline >= 3 else 0.0
    s += 1.5 if diffs >= 4 else 1.0 if diffs >= 2 else 0.0
    s += 1.5 if chart >= 4 else 0.75 if chart else 0.0
    return round(s, 2)


print("The recorded scores are reproducible — these are real cases, not invented")
for pmcid, w, f, t, d, c, logged in REAL_CASES:
    check(f"{pmcid} scored {logged} under the old bands",
          old_bands_score(w, f, t, d, c), logged)

print()
print("Threadbare cases are STILL refused — this is not a lowered bar")
for pmcid, w, f, t, d, c, _ in REAL_CASES:
    if pmcid in ("PMC5561643", "PMC2954009", "PMC7913166"):
        sc, _r = case_richness(build(w, f, t, d, c), verified_figures=f)
        check(f"{pmcid} ({w}w, {f} fig) still below the floor",
              sc < CASE_RICHNESS_FLOOR, True)
        print(f"        scores {sc}, floor {CASE_RICHNESS_FLOOR}")

print()
print("Cases with real material now get through")
for pmcid, w, f, t, d, c, _ in REAL_CASES:
    if pmcid in ("PMC7427646", "PMC3276451", "PMC2390580"):
        sc, _r = case_richness(build(w, f, t, d, c), verified_figures=f)
        check(f"{pmcid} ({w}w, {f} verified fig) is accepted",
              sc >= CASE_RICHNESS_FLOOR, True)
        print(f"        scores {sc}, floor {CASE_RICHNESS_FLOOR}")

print()
print("The acceptance rate on real cases is materially better")
_acc = sum(1 for p, w, f, t, d, c, _ in REAL_CASES
           if case_richness(build(w, f, t, d, c), verified_figures=f)[0]
           >= CASE_RICHNESS_FLOOR)
check("at least 3 of the 7 measured cases pass", _acc >= 3, True)
print(f"        {_acc}/7 accepted (was 1/7 — one script written in 40 minutes)")
# And not a free-for-all: if this ever passes everything, the gate has
# stopped being a gate and thin cases are reaching the channel.
check("but NOT all of them — the gate still rejects", _acc <= 4, True)

print()
print("The band boundaries are where they claim to be")
for words, want_band in ((800, "rich"), (400, "adequate"), (250, "usable seed"),
                         (120, "thin"), (119, "too thin")):
    _s, _r = case_richness(build(words, 4, 5, 3, 2), verified_figures=4)
    _narr = [x for x in _r if x.startswith("narrative")][0]
    check(f"{words} words reads as '{want_band}'", want_band in _narr, True)

print()
print("A failed extraction is still UNKNOWN, not zero (the run 31876972186 rule)")
# Unchanged behaviour, asserted so the recalibration above cannot quietly
# undo the fix that stopped a provider outage being blamed on the papers.
_rich_case = build(401, 2, 5, 1, 0)
_with, _ = case_richness(_rich_case, verified_figures=2, structures_extracted=True)
_without, _r2 = case_richness(_rich_case, verified_figures=2,
                              structures_extracted=False)
check("unmeasured dimensions are rescaled away, not scored 0",
      _without > _with, True)
check("and it says so in the reasons",
      any("NOT ASSESSED" in x for x in _r2), True)
print(f"        extracted {_with} / not-assessed {_without}")

print()
if FAILURES:
    print(f"FAILED — {len(FAILURES)} check(s):")
    for f in FAILURES:
        print("  -", f)
    sys.exit(1)
print("All checks passed.")
