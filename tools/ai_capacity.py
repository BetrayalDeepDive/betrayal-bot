"""
How much each AI provider will actually accept, and how much this run has spent.

Two problems live here, and they are the same problem seen from both ends.

ASKING FOR MORE ROOM THAN THE ACCOUNT HAS
-----------------------------------------
Every provider's free tier caps how big a single request may be. Some cap the
COMBINED size of the question and the answer; some cap only the answer. Ask for
more than the cap and the request is refused outright -- not throttled, not
served short, refused -- and the chain moves on believing the provider is down.

call_groq already had this right. `_groq_budget` measured the prompt, subtracted
it from Groq's 8000-token combined limit, and asked for the remainder. Nothing
else did. call_cerebras asked for `min(tokens, 12000)` on every call, which is
why the LARGEST free allowance in the chain -- a million tokens a day -- was
refusing script-length prompts and being marked dead. Gemini, Cloudflare, NIM,
SambaNova, OpenRouter, Cohere and Mistral all had the same shape of bug.

WE DO NOT ACTUALLY KNOW THE LIMITS
----------------------------------
Published figures for these free tiers contradict each other. Cerebras' context
cap is documented as 8,192 in one place and 64,000 in another. Gemini's daily
request allowance is quoted anywhere between 20 and 1,500. Hard-coding either
number is a guess, and a guess that is too small wastes the allowance we are
trying to protect while a guess that is too large reproduces the original bug.

So the numbers below are STARTING ASSUMPTIONS, not facts, and they are the
optimistic end of what is published. When a provider refuses a request because
it was too big, it almost always says so in words -- Groq's own refusal reads
"Limit 8000, Requested 9060" -- and `note_limit_error` parses that sentence and
remembers the real number for the rest of the run. One refusal per provider per
run, instead of one on every call, and after the first run the daily health
check has the measured figure on disk.

That is the whole idea: stop trusting anybody's documentation, and let each
provider tell us its own limit exactly once.
"""

import json
import os
import re
import time
from pathlib import Path

# Where the daily audit and the pipelines share what they have learned.
# Must match tools/provider_audit.py's HEALTH_PATH exactly -- two files
# disagreeing about where the health file lives means the measurements are
# written to one place and read from another, and nothing ever learns.
HEALTH_FILE = (Path(__file__).resolve().parents[1] /
               "video_pipeline" / "provider_health.json")

# ── STARTING ASSUMPTIONS ──────────────────────────────────────────────────
#
# combined  -- provider caps question + answer together against this number.
# answer    -- provider caps only the answer; the question is separate.
#
# A provider needs exactly one of the two. `combined` is the conservative
# shape: if we are unsure which kind a provider is, treating it as combined
# only ever asks for less, which is safe.
#
# renewable -- False means the allowance is a fixed sum that never comes back
#              (see RULE 7 below). Those are excluded from daily capacity.
PROVIDER_LIMITS = {
    # Groq's free "on_demand" tier: prompt + completion together, per minute.
    # This one is measured, not published-guessed -- run 30717615638 collected
    # seventeen refusals that each stated the number.
    "groq":         {"combined": 8000,  "renewable": True},

    # Cerebras: documented as both 8,192 and 64,000 depending on the source.
    # Starting at the larger figure because the smaller one would throw away
    # the biggest daily allowance in the chain; note_limit_error corrects it
    # on the first refusal if 8,192 turns out to be the real one.
    "cerebras":     {"combined": 64000, "renewable": True},

    # Gemini caps the answer only; the context window is separate and large.
    "gemini":       {"answer":   8192,  "renewable": True},

    "openrouter":   {"combined": 8000,  "renewable": True},
    "cohere":       {"answer":   4000,  "renewable": True},
    "cloudflare":   {"combined": 8000,  "renewable": True},
    "nvidia_nim":   {"combined": 16000, "renewable": True},
    "mistral":      {"answer":   8000,  "renewable": True},
    "github_models":{"combined": 8000,  "renewable": True},

    # RULE 7 -- A ONE-OFF GRANT IS NOT A FREE TIER.
    #
    # SambaNova hands out a fixed sum of credits on signup. It does not renew.
    # Counting it in the daily ceiling makes the chain look healthier than it
    # is, and the day it runs dry it fails exactly like an outage: same error,
    # same silence, no warning. Marked non-renewable so it is excluded from
    # capacity totals and reported in its own words when it stops.
    "sambanova":    {"combined": 8000,  "renewable": False},

    # ── The additions (see FIVE_CHANNEL_PRODUCTION_PLAN.pdf, section 6) ──
    "kilocode":     {"combined": 16000, "renewable": True},
    "huggingface":  {"combined": 8000,  "renewable": True},
    "llm7":         {"combined": 8000,  "renewable": True},
    "modelscope":   {"combined": 8000,  "renewable": True},
    "siliconflow":  {"combined": 16000, "renewable": True},

    # Runs on the build machine itself. No account, no quota, no rate limit,
    # and nothing anybody can decommission -- so it has no meaningful cap
    # beyond the model's own context window.
    "local":        {"combined": 4096,  "renewable": True},
}

# Limits this run has been TOLD, which always beat the assumptions above.
_OBSERVED = {}

# Roughly four characters per token. Deliberately crude and deliberately
# pessimistic: over-estimating the prompt asks for a slightly shorter answer,
# which costs nothing, while under-estimating it reproduces the 413.
CHARS_PER_TOKEN = 4

# Room left for the envelope the provider wraps around the conversation --
# role markers, system scaffolding, its own bookkeeping.
ENVELOPE = 200

# Below this an answer is not worth the round-trip.
MIN_USABLE_ANSWER_TOKENS = 256


def _load_observed():
    """Pick up limits measured on previous runs, if the health file has any."""
    try:
        d = json.loads(HEALTH_FILE.read_text())
        for name, rec in (d.get("providers") or {}).items():
            lim = rec.get("observed_limit")
            if isinstance(lim, int) and lim > 0:
                _OBSERVED[name] = lim
    except Exception:
        pass


_load_observed()


def estimate_tokens(text):
    """Rough token count for a string. Over-estimates on purpose."""
    return len(text or "") // CHARS_PER_TOKEN + 1


def limit_for(provider):
    """The combined limit we currently believe this provider enforces.

    Returns (limit, kind) where kind is "combined" or "answer", or
    (None, None) for a provider we know nothing about -- in which case the
    caller should just use whatever it was going to use anyway.
    """
    spec = PROVIDER_LIMITS.get(provider)
    if not spec:
        return None, None
    if provider in _OBSERVED:
        # A measured limit is always combined-shaped: the provider refused a
        # request of a known total size, so the total is what it was judging.
        return _OBSERVED[provider], "combined"
    if "combined" in spec:
        return spec["combined"], "combined"
    return spec.get("answer"), "answer"


def budget(provider, prompt, want):
    """How many answer-tokens to ask `provider` for, given this prompt.

    Returns None when the prompt alone leaves no room for a usable answer.
    Skipping the provider for this one call is strictly better than spending
    a round-trip to be told the request was too big -- that is the seventeen
    refusals of run 30717615638, and it is what marked a working provider dead.
    """
    lim, kind = limit_for(provider)
    if not lim:
        return want
    if kind == "answer":
        # The question is not counted against this cap, so the only ceiling
        # is the answer size itself.
        return max(1, min(want, lim))
    room = lim - estimate_tokens(prompt) - ENVELOPE
    if room < MIN_USABLE_ANSWER_TOKENS:
        return None
    return max(1, min(want, room))


# Sentences providers use to state their real limit. Ordered most specific
# first. Every one of these is a real refusal shape seen from these accounts
# or documented by the provider.
_LIMIT_PATTERNS = [
    # Groq: "Limit 8000, Requested 9060"
    re.compile(r"limit\s+(\d{3,7})\s*,\s*requested", re.I),
    # OpenAI-shaped: "maximum context length is 8192 tokens"
    re.compile(r"maximum\s+context\s+length\s+is\s+(\d{3,7})", re.I),
    # "max_tokens must be <= 4096"
    re.compile(r"max_?_?tokens?\s*(?:must be)?\s*<=?\s*(\d{3,7})", re.I),
    # "This model supports at most 8192 completion tokens"
    re.compile(r"at\s+most\s+(\d{3,7})\s+(?:completion\s+)?tokens", re.I),
    # Generic trailing statement: "... limit of 16384 tokens"
    re.compile(r"limit\s+of\s+(\d{3,7})\s+tokens", re.I),
]


def note_limit_error(provider, status, text, log_fn=None):
    """Learn this provider's real size limit from the refusal it just sent.

    Returns True when a limit was learned, which tells the caller the request
    is worth retrying immediately at the corrected size rather than moving on
    to the next provider. A provider that has just told us exactly how much it
    will accept is not down -- it is available and we asked wrongly.
    """
    if int(status) not in (400, 413, 422):
        return False
    body = str(text or "")[:2000]
    for pat in _LIMIT_PATTERNS:
        m = pat.search(body)
        if not m:
            continue
        try:
            found = int(m.group(1))
        except (TypeError, ValueError):
            continue
        if found < 512 or found > 2_000_000:
            continue          # not a plausible token limit
        prev = _OBSERVED.get(provider)
        if prev == found:
            return True       # already known; still worth one retry
        _OBSERVED[provider] = found
        if log_fn:
            log_fn(f"  {provider}: told us its real limit is {found} tokens "
                   f"(we assumed {limit_for(provider)[0]}). Remembering it for "
                   f"the rest of this run and writing it to the health file.")
        return True
    return False


def observed_limits():
    """Everything measured this run, for the health file to persist."""
    return dict(_OBSERVED)


def is_renewable(provider):
    """False for allowances that are a fixed grant and never come back."""
    return bool(PROVIDER_LIMITS.get(provider, {}).get("renewable", True))


def renewable_providers(names):
    """Filter to providers whose allowance actually resets. See RULE 7."""
    return [n for n in names if is_renewable(n)]


# ── RULE 1: EVERY RUN HAS A SPENDING LIMIT ────────────────────────────────
#
# Run 31876972186 spent 130 minutes and an entire day's allowance re-asking
# three model names that did not exist. The faults behind that specific run
# are fixed, but "one run can consume the whole day" is a shape of failure,
# not a single bug, and the only general defence is a budget the run cannot
# talk its way past.
#
# The number below is deliberately generous. A healthy episode is modelled at
# 30-90 calls; this allows several times that, so it never interrupts normal
# work -- including the 13-attempt x 3-round gate retries, which are supposed
# to be expensive. It exists to catch the runaway, not to ration the work.
#
# It is also the instrument that replaces the modelling with measurement: the
# tally it prints at the end of every run is the first real per-episode call
# count this project will have.
DEFAULT_CALL_BUDGET = int(os.environ.get("AI_CALL_BUDGET", "600"))


class Ledger:
    """Counts what a run spends, and stops it before it spends everything."""

    def __init__(self, budget=None):
        self.budget = int(budget or DEFAULT_CALL_BUDGET)
        self.calls = 0
        self.by_provider = {}
        self.wins = {}
        self.prompt_tokens = 0
        self.started = time.time()
        self.stopped_reason = None

    def record(self, provider, ok, prompt=""):
        self.calls += 1
        self.by_provider[provider] = self.by_provider.get(provider, 0) + 1
        if ok:
            self.wins[provider] = self.wins.get(provider, 0) + 1
        self.prompt_tokens += estimate_tokens(prompt)

    def exceeded(self):
        return self.calls >= self.budget

    def stop(self, reason):
        self.stopped_reason = reason

    def summary(self):
        """The line that turns an estimate into a measurement."""
        mins = (time.time() - self.started) / 60.0
        parts = ", ".join(
            f"{p} {n}" + (f" ({self.wins.get(p, 0)} ok)" if self.wins.get(p) else "")
            for p, n in sorted(self.by_provider.items(), key=lambda kv: -kv[1]))
        return (f"AI calls this run: {self.calls} of {self.budget} budgeted, "
                f"over {mins:.0f} min. By provider: {parts or 'none'}. "
                f"Prompt tokens sent: ~{self.prompt_tokens:,}.")


# One ledger per process. The pipelines are single-run scripts, so a module
# global is the honest shape here -- there is exactly one run to count.
LEDGER = Ledger()


def persist(path=None, extra=None):
    """Merge what this run learned back into the health file.

    Never raises: a bookkeeping failure must not take an episode down.
    """
    target = Path(path or HEALTH_FILE)
    try:
        try:
            doc = json.loads(target.read_text())
        except Exception:
            doc = {}
        provs = doc.setdefault("providers", {})
        for name, lim in _OBSERVED.items():
            provs.setdefault(name, {})["observed_limit"] = lim
        for name, n in LEDGER.by_provider.items():
            rec = provs.setdefault(name, {})
            rec["calls_last_run"] = n
            rec["wins_last_run"] = LEDGER.wins.get(name, 0)
        doc["last_run"] = {
            "calls": LEDGER.calls,
            "budget": LEDGER.budget,
            "stopped_reason": LEDGER.stopped_reason,
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        if extra:
            doc.update(extra)
        # indent=1 MATCHES tools/provider_audit.py. It has to.
        #
        # This file is committed on every run. Written at a different indent
        # from the audit, each side reformats all 200 lines the other wrote, so
        # every commit shows the whole file as changed and the one line that
        # actually moved -- a provider going dead, a limit being learned -- is
        # invisible in the diff. A health file nobody can read the history of
        # is most of the way to not having one.
        target.write_text(json.dumps(doc, indent=1))
        return True
    except Exception:
        return False
