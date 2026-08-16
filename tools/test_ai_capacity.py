"""
Tests for the request-size budget.

This is the change that unlocks the biggest allowance in the chain, and the
failure it fixes was invisible: the provider answered with a refusal, the
chain read "no response", and a working account was marked dead. A bug that
looks exactly like an outage deserves a test that fails loudly.

Run: python tools/test_ai_capacity.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import ai_capacity as cap   # noqa: E402

FAILURES = []


def check(label, got, want):
    if got != want:
        FAILURES.append(f"{label}: got {got!r}, wanted {want!r}")
        print(f"  FAIL  {label}: got {got!r}, wanted {want!r}")
    else:
        print(f"  ok    {label}")


def approx(label, got, want, slack=2):
    if got is None or abs(got - want) > slack:
        FAILURES.append(f"{label}: got {got!r}, wanted ~{want}")
        print(f"  FAIL  {label}: got {got!r}, wanted ~{want}")
    else:
        print(f"  ok    {label}  ({got})")


print("A short prompt leaves room for the full answer")
short = "x" * 400                       # ~100 tokens
check("cerebras/short", cap.budget("cerebras", short, 8000), 8000)
check("groq/short", cap.budget("groq", short, 2000), 2000)

print()
print("A script-length prompt is subtracted from a COMBINED ceiling")
# ~4,260 tokens: the real prompt size from run 30717615638.
script = "x" * (4260 * cap.CHARS_PER_TOKEN)
# Groq's ceiling is 8000, so 8000 - 4260 - 200 envelope = ~3540.
approx("groq/script", cap.budget("groq", script, 8000), 3540, slack=3)
# THE ACTUAL BUG: this used to ask for min(8000, 12000) = 8000 on top of a
# 4,260-token prompt and be refused. Cerebras' ceiling is far larger, so the
# full answer fits -- the provider was never the problem.
check("cerebras/script", cap.budget("cerebras", script, 8000), 8000)

print()
print("A prompt with no room left returns None rather than wasting a call")
huge = "x" * (9000 * cap.CHARS_PER_TOKEN)
check("groq/huge", cap.budget("groq", huge, 8000), None)

print()
print("An ANSWER-only ceiling ignores the prompt size")
# Gemini counts the prompt separately, so a long prompt must not shrink the
# answer -- capping it there would silently truncate scripts.
check("gemini/script", cap.budget("gemini", script, 8000), 8000)
check("gemini/over", cap.budget("gemini", script, 99000), 8192)

print()
print("A refusal that states the real limit is learned, not just logged")
before = cap.limit_for("cerebras")[0]
learned = cap.note_limit_error(
    "cerebras", 400,
    '{"error":{"message":"Please reduce the length of the messages; '
    'maximum context length is 8192 tokens"}}')
check("learned from refusal", learned, True)
check("limit updated", cap.limit_for("cerebras")[0], 8192)
print(f"        (was {before}, provider corrected it to 8192)")
# And the budget must immediately respect the corrected figure.
approx("cerebras/after-learning", cap.budget("cerebras", script, 8000),
       8192 - 4260 - 200, slack=3)

print()
print("Groq's own refusal wording is understood")
cap._OBSERVED.pop("groq", None)
check("groq refusal parsed",
      cap.note_limit_error("groq", 413,
                           "Request too large. Limit 8000, Requested 9060."),
      True)
check("groq limit learned", cap.limit_for("groq")[0], 8000)

print()
print("Nonsense in an error body is not mistaken for a limit")
cap._OBSERVED.pop("mistral", None)
check("no false positive",
      cap.note_limit_error("mistral", 400, "Bad Request: invalid role 'user2'"),
      False)
check("a 429 is not a size problem",
      cap.note_limit_error("cohere", 429, "Limit 8000, Requested 9060"), False)

print()
print("One-off credit grants are not counted as renewable capacity (RULE 7)")
check("sambanova not renewable", cap.is_renewable("sambanova"), False)
check("cerebras renewable", cap.is_renewable("cerebras"), True)
check("filtered out of capacity",
      cap.renewable_providers(["cerebras", "sambanova", "groq"]),
      ["cerebras", "groq"])

print()
print("The ledger counts what a run actually spends (RULE 1)")
led = cap.Ledger(budget=5)
for i in range(4):
    led.record("cerebras", ok=(i % 2 == 0), prompt=short)
check("counted", led.calls, 4)
check("not yet over", led.exceeded(), False)
led.record("groq", ok=False, prompt=short)
check("budget reached", led.exceeded(), True)
check("per-provider tally", led.by_provider, {"cerebras": 4, "groq": 1})
check("wins tracked", led.wins, {"cerebras": 2})
print("        " + led.summary())

print()
if FAILURES:
    print(f"FAILED — {len(FAILURES)} check(s):")
    for f in FAILURES:
        print("  -", f)
    sys.exit(1)
print("All checks passed.")
