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
print("Every provider in the live chain has a budget entry")
# THIS IS THE REGRESSION GUARD FOR THE WHOLE FIX.
#
# budget() falls back to "ask for whatever you were going to ask for" when it
# does not recognise a provider. That is the correct behaviour for an unknown
# caller, but it means a provider added to the chain WITHOUT an entry in
# PROVIDER_LIMITS silently reverts to the original bug -- asking for more than
# the account accepts, being refused, and being marked dead. Nothing would
# fail; it would just quietly stop working, which is how this went unnoticed.
import re                                                   # noqa: E402

pipeline = (Path(__file__).resolve().parents[1] /
            "channels" / "betrayal_deepdive" / "clinical_pipeline.py").read_text()
block = pipeline[pipeline.index("    providers = ["):]
block = block[:block.index("]")]
chain = re.findall(r'\("([a-z0-9_]+)",\s*call_', block)
check("chain was parsed", len(chain) >= 10, True)
missing = [p for p in chain if p not in cap.PROVIDER_LIMITS]
check("no provider missing a budget entry", missing, [])
print(f"        chain ({len(chain)}): {', '.join(chain)}")

# RULE 7 has an ordering consequence, not just a label: a finite grant must be
# reached only after everything that regenerates has been tried, or it gets
# spent while renewable capacity was sitting there unused.
non_renewable = [p for p in chain if not cap.is_renewable(p)]
for p in non_renewable:
    check(f"{p} (finite credits) is last in the chain",
          chain.index(p), len(chain) - 1)

print()
print("An unconfigured provider never enters the chain")
# THE REGRESSION GUARD FOR RUN 31943236984.
#
# Five providers were added with no keys set. Each returned None instantly --
# correct on its own -- but the chain counted that as a FAILED ATTEMPT, so
# every whole-chain sweep contained five guaranteed failures, the `revivable`
# list (which excludes only quota-exhausted and no-models-left) revived them
# forever, and eight such sweeps tripped the permanent CHAIN_DOWN breaker.
#
# The run's own ledger disproved its own conclusion: 188 calls, 138 SUCCESSES,
# and an exit message reading "every AI provider was unavailable". 143 minutes
# spent, no script written.
guard = pipeline[pipeline.index("_configured = {"):]
guard = guard[:guard.index("providers = [(n, fn) for n, fn")]
check("chain filters on configuration", "_unconfigured" in guard, True)
for p in ("kilocode", "huggingface", "modelscope", "siliconflow", "cerebras",
          "groq", "gemini", "cloudflare", "sambanova"):
    check(f"{p} has a configured-check", f'"{p}"' in guard, True)
# LLM7 needs no account at all, so it must NOT be gated behind a key.
check("llm7 is always configured (no account needed)",
      '"llm7": True' in guard, True)

print()
print("The outage message cannot contradict the ledger")
# The same run printed "every AI provider was unavailable" seconds above its
# own tally of 138 successful calls. A confident diagnosis pointing at the
# wrong thing costs more than no diagnosis.
exitmsg = pipeline[pipeline.index("EXIT 2: no script was ever generated") - 2200:]
exitmsg = exitmsg[:2600]
check("outage claim is conditional on wins",
      "_ok = sum(_cap.LEDGER.wins.values())" in exitmsg, True)
# Comments may quote the old wording — that is the record of what went wrong.
# Only executable lines matter.
_live = [l for l in pipeline.splitlines() if not l.lstrip().startswith("#")]
check("the old unconditional claim is gone from live code",
      any("every AI provider was unavailable" in l for l in _live), False)

print()
if FAILURES:
    print(f"FAILED — {len(FAILURES)} check(s):")
    for f in FAILURES:
        print("  -", f)
    sys.exit(1)
print("All checks passed.")
