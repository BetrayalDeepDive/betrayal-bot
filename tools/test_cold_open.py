"""
The first-15-seconds scorer must not punish correct narration style.

WHY THIS EXISTS
---------------
Run 32039970137 wrote exactly one script in forty minutes. It scored 7.1/10
overall and was blocked by two sub-gates, the weaker being first_15_seconds
at 3.8 against a required 6.5.

Part of that was the script's fault. Part was not: the check for "a concrete
detail" tested `\\d` only, so

    "A fifty-one-year-old teacher lost the use of both kidneys in nine days."

counted as having NO concrete detail, while the identical sentence written
"51-year-old" and "9 days" passed. Every other instruction in this project
tells the writer to spell numbers out, because the script is read aloud. The
check was penalising the form the house style demands — the same defect as a
100-character floor on a correct 78-character answer.

Run: python tools/test_cold_open.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "video_pipeline"))
from script_scoring import validate_first_15_seconds, _SPELLED_NUMBER  # noqa: E402

FAILURES = []


def check(label, got, want):
    if got != want:
        FAILURES.append(f"{label}: got {got!r}, wanted {want!r}")
        print(f"  FAIL  {label}: got {got!r}, wanted {want!r}")
    else:
        print(f"  ok    {label}")


FILLER = "Filler narration continues here. " * 80

# The example shape given to the model in Ch1's cold-open instruction. If the
# example we hand the writer cannot itself clear the bar, the instruction is
# asking for something it does not demonstrate.
PROMPT_EXAMPLE = (
    "A fifty-one-year-old teacher lost the use of both kidneys in nine days. "
    "Her scans were normal. Every test came back clean. The cause was sitting "
    "on her kitchen counter. ") + FILLER

THROAT_CLEARING = (
    "In this video we are going to look at a case that has puzzled doctors "
    "for a very long time and which raises difficult questions about how "
    "illness is understood. ") + FILLER

VAGUE = (
    "A patient became unwell over a period of time and the doctors were "
    "unable to work out the reason for it despite their best efforts and "
    "many careful examinations. ") + FILLER

HOOK_FLOOR = 6.5   # what the gate requires of the hook average

print("Spelled-out numbers are recognised, without false positives")
for text, want in (("nine days", True), ("fifty-one-year-old", True),
                   ("seventeen tests", True), ("three hundred", True),
                   ("none of it", False), ("someone arrived", False),
                   ("only later", False), ("gone", False)):
    check(f"{text!r}", bool(_SPELLED_NUMBER.search(text)), want)

print()
print("The example we give the writer clears the bar it is teaching")
_score, _issues = validate_first_15_seconds(PROMPT_EXAMPLE)
check("prompt example scores at or above the hook floor", _score >= HOOK_FLOOR, True)
print(f"        {_score} vs floor {HOOK_FLOOR}")
check("and it is not scored as lacking a concrete detail",
      any("no concrete detail" in i for i in _issues), False)

print()
print("Weak openings are STILL rejected — this did not loosen the gate")
_bad, _ = validate_first_15_seconds(THROAT_CLEARING)
check("a 'In this video...' opener stays far below the floor", _bad < 2.0, True)
print(f"        {_bad}")
_vague, _vi = validate_first_15_seconds(VAGUE)
check("a vague opener with no specifics stays below the floor",
      _vague < HOOK_FLOOR, True)
print(f"        {_vague}")
check("and it IS told it has no concrete detail",
      any("no concrete detail" in i for i in _vi), True)

print()
print("The digit form and the spelled form now score the same")
_digits = ("A 51-year-old teacher lost the use of both kidneys in 9 days. "
           "Her scans were normal. Every test came back clean. The cause was "
           "sitting on her kitchen counter. ") + FILLER
check("identical opening, digits vs words, scores identically",
      validate_first_15_seconds(_digits)[0],
      validate_first_15_seconds(PROMPT_EXAMPLE)[0])

print()
if FAILURES:
    print(f"FAILED — {len(FAILURES)} check(s):")
    for f in FAILURES:
        print("  -", f)
    sys.exit(1)
print("All checks passed.")
