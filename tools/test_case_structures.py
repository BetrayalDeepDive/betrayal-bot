"""
The case-structure parser must accept the shapes models actually produce.

WHY THIS EXISTS
---------------
_parse_structures accepted [["Sarcoidosis", "raised ACE", "ruled out"]] and
nothing else. A model asked for named fields answers with
[{"diagnosis": ..., "evidence": ..., "outcome": ...}] far more often than not,
and every one of those rows was dropped without a word.

The failure is invisible by design. Nothing errors. The case simply arrives
with zero differentials and zero timeline events, scores under the richness
floor, and is rejected as "thin" -- so the pipeline repicks, and repicks, and
spends all 39 of its attempts on case selection without ever writing a script.
Run 31952331323 did exactly that for 120 minutes while 82 of its 87 AI calls
were succeeding.

Run: python tools/test_case_structures.py
"""
import json
import re
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "channels" / "betrayal_deepdive" / "clinical_pipeline.py"

FAILURES = []


def load_parser():
    """Lift _parse_structures out of its enclosing function to test it alone."""
    src = SRC.read_text()
    i = src.index("        def _parse_structures(raw):")
    lines = src[i:].splitlines()
    out = [lines[0]]
    for line in lines[1:]:
        if line.strip() and not line.startswith("            "):
            break
        out.append(line)
    ns = {"re": re, "json": json, "log": lambda *a, **k: None,
          "case": {"narrative": "the patient had raised ACE and a biopsy"}}
    exec(textwrap.dedent("\n".join(out)), ns)
    return ns["_parse_structures"]


def check(label, got, want):
    if got != want:
        FAILURES.append(f"{label}: got {got!r}, wanted {want!r}")
        print(f"  FAIL  {label}: got {got!r}, wanted {want!r}")
    else:
        print(f"  ok    {label}")


P = load_parser()


def shape(raw):
    r = P(raw)
    if r is None:
        return None
    return (len(r["differentials"]), len(r["timeline"]))


print("Both row shapes are accepted")
check("positional arrays (the original shape)",
      shape('{"differentials":[["Sarcoidosis","raised ACE","ruled out"]],'
            '"timeline":[["Day 1","fever"]]}'), (1, 1))
check("objects with the obvious key names",
      shape('{"differentials":[{"diagnosis":"Sarcoidosis","evidence":"raised ACE",'
            '"outcome":"ruled out"}],"timeline":[{"when":"Day 1","what":"fever"}]}'),
      (1, 1))
check("objects with unfamiliar keys fall back to their own order",
      shape('{"differentials":[{"dx":"Sarcoidosis","because":"raised ACE",'
            '"verdict":"out"}],"timeline":[{"t":"Day 1","e":"fever"}]}'), (1, 1))
check("a list may mix both shapes",
      shape('{"differentials":[["A","b","c"],{"diagnosis":"B","evidence":"d",'
            '"outcome":"e"}],"timeline":[{"when":"D1","what":"f"},["D2","g"]]}'),
      (2, 2))

print()
print("The values survive, not just the row count")
r = P('{"differentials":[{"diagnosis":"Sarcoidosis","evidence":"raised ACE",'
      '"outcome":"ruled out on biopsy"}],"timeline":[]}')
check("object row keeps its three fields in order",
      r["differentials"][0], ("Sarcoidosis", "raised ACE", "ruled out on biopsy"))

print()
print("Genuine emptiness is still rejected, not invented")
check("empty object rows are dropped", shape('{"differentials":[{}],"timeline":[{}]}'),
      (0, 0))
check("a prose refusal is still None",
      shape("The text does not contain a structured differential list."), None)
check("nothing at all is still None", shape(""), None)
check("no JSON object anywhere is still None", shape("differentials: none found"),
      None)

print()
print("A quote the model paraphrased is still refused")
# Unchanged behaviour, asserted so the tolerance added above cannot quietly
# relax the one rule that keeps invented sentences off the screen.
r = P('{"differentials":[],"timeline":[],"quote":"a sentence never written"}')
check("invented quote dropped", r["quote"], "")
r = P('{"differentials":[],"timeline":[],"quote":"raised ACE and a biopsy"}')
check("verbatim quote kept", r["quote"], "raised ACE and a biopsy")

print()
if FAILURES:
    print(f"FAILED — {len(FAILURES)} check(s)")
    for f in FAILURES:
        print("  -", f)
    sys.exit(1)
print("All checks passed.")
