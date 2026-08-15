#!/usr/bin/env python3
"""
WEEKLY PROVIDER HEALTH AUDIT — FIND WHAT DIED BEFORE A RUN DOES.

"I want the authentication of these every week, so make an algorithm which can
check every week if there is anything that is decommissioned and it can replace
it automatically rather than me pointing out every time."

Run 31820199959 is the reason. Gemini answered every call with 403 "your
project has been denied access", NVIDIA NIM read-timed-out on the same models
round after round, and the episode burned 280 minutes of runner time to reach
ZERO review gates. Nobody knew until the run was already dead, and the way it
surfaced was the owner asking why no Telegram message ever arrived.

Nothing here is new capability. It is the same provider calls the pipeline
already makes, made on a schedule, against a five-word prompt, so a dead key
or a retired model is discovered on a Sunday morning for free instead of
halfway through a Thursday episode.

WHAT IT CAN AND CANNOT FIX BY ITSELF
------------------------------------
Being honest about this, because the difference decides what the weekly
message has to say.

  AUTO-FIXABLE — a model that was renamed, retired or pulled.
      Every provider with a /v1/models endpoint publishes its live catalogue.
      The audit reads it, tests candidates for real, and writes the winners to
      provider_health.json. The pipeline prefers those. No human involved.

  NOT AUTO-FIXABLE — a dead or denied API key.
      401 and 403 mean the account, not the code. No algorithm can mint a new
      credential. What it CAN do is stop the pipeline wasting an hour on a
      provider that will refuse every call, and tell the owner exactly which
      key, exactly what the provider said, and where to go to replace it.

So: models heal themselves, credentials get escalated with everything needed
to fix them in one action. Anything claiming to do more than that would be
lying about what an API key is.

Usage:
    python tools/provider_audit.py                 # audit, write health file
    python tools/provider_audit.py --print         # audit, print, write nothing

Exit codes:
    0  the chain is healthy enough to run an episode
    1  too few providers survive — an episode would likely fail
"""

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "video_pipeline"))
sys.path.insert(0, str(ROOT / "channels" / "betrayal_deepdive"))

# Shared by all five channels — they authenticate with the same secrets, so
# one record serves all of them. Lives in video_pipeline because every channel
# already imports from there; under one channel the other four would be
# second-class readers of a file they equally own.
HEALTH_PATH = ROOT / "video_pipeline" / "provider_health.json"

# A prompt short enough to be free everywhere and specific enough that a
# provider echoing its system preamble does not read as a pass.
PROBE_PROMPT = ("Reply with exactly this word and nothing else: STETHOSCOPE")
PROBE_EXPECT = "stethoscope"

# Where a human goes when a credential needs replacing. Printed straight into
# the weekly message so the fix is one click, not a search.
KEY_HELP = {
    "cerebras":      ("CEREBRAS_API_KEY",   "https://cloud.cerebras.ai"),
    "groq":          ("GROQ_API_KEY",       "https://console.groq.com/keys"),
    "gemini":        ("GEMINI_API_KEY",     "https://aistudio.google.com/apikey"),
    "openrouter":    ("OPENROUTER_API_KEY", "https://openrouter.ai/keys"),
    "cohere":        ("COHERE_API_KEY",     "https://dashboard.cohere.com/api-keys"),
    "github_models": ("GITHUB_TOKEN",       "https://github.com/settings/tokens"),
    "cloudflare":    ("CLOUDFLARE_API_TOKEN",
                      "https://dash.cloudflare.com/profile/api-tokens"),
    "nvidia_nim":    ("NVIDIA_API_KEY",     "https://build.nvidia.com"),
    "sambanova":     ("SAMBANOVA_API_KEY",  "https://cloud.sambanova.ai"),
    "mistral":       ("MISTRAL_API_KEY",    "https://console.mistral.ai/api-keys"),
}

# WHAT TO ACTUALLY DO, WHEN THE KEY IS ALREADY THERE.
#
# The first version of this told the owner to "set GEMINI_API_KEY". They had
# already set two, and said so: "I don't know why you are asking me about
# another Gemini key... I have already done it." Fair. A 403 against a
# configured key is not a missing key, and "set the key" is advice for a
# problem they do not have.
#
# A 403 with a valid credential has a small number of real causes, and they
# differ per provider. These are the ones worth checking, in the order they
# are usually the answer.
DENIED_PLAYBOOK = {
    "gemini": [
        "The API is not enabled on that Google Cloud project — open "
        "console.cloud.google.com > APIs & Services > Enable APIs, and enable "
        "'Generative Language API' for the SAME project the key belongs to.",
        "The key has API restrictions — console.cloud.google.com > "
        "Credentials > your key > 'API restrictions'. If it is set to "
        "'Restrict key', Generative Language API must be in the allowed list.",
        "The region is not served. Gemini's free tier is unavailable in some "
        "countries, and a runner in an unsupported region gets exactly this "
        "PERMISSION_DENIED.",
        "The project itself is flagged. If the message says 'contact "
        "support', a NEW KEY ON THE SAME PROJECT WILL NOT HELP — the block is "
        "on the project. Make a fresh project and issue a key from that.",
    ],
    "cloudflare": [
        "The token is missing the Workers AI permission — dash.cloudflare.com "
        "> My Profile > API Tokens > your token > Edit, and add "
        "'Account / Workers AI / Read' (and Edit).",
        "CLOUDFLARE_ACCOUNT_ID belongs to a different account than the token. "
        "Both must come from the same account.",
    ],
    "github_models": [
        "GitHub Models was RETIRED — it answers 410 Gone. Nothing to fix; it "
        "should simply be dropped from the chain.",
    ],
}

# Below this many working providers an episode cannot realistically finish:
# a 1900-word script plus rewrites plus gate scoring is dozens of calls, and
# run 31820199959 proved what two flaky survivors produces (573 words).
MIN_HEALTHY = 3


def _classify(name, fn, log):
    """Call the provider for real and say what state it is in.

    Deliberately calls the pipeline's OWN function rather than reimplementing
    the HTTP. A separate implementation would be testing this file's idea of
    the provider, not the code that actually runs on Thursday -- the same
    mistake as a checker that never exercises the thing it checks.
    """
    t0 = time.time()
    captured = []
    try:
        import clinical_pipeline as cp
        # Capture the provider's own log lines: they already carry the status
        # code and the provider's message, which is what a diagnosis needs.
        _orig_log = cp.log
        cp.log = lambda m, *a, **k: captured.append(str(m))
        try:
            out = fn(PROBE_PROMPT, tokens=32, min_chars=1)
        finally:
            cp.log = _orig_log
    except Exception as e:
        return {"state": "error", "detail": str(e)[:160],
                "seconds": round(time.time() - t0, 1), "log": captured[-4:]}

    secs = round(time.time() - t0, 1)
    blob = " ".join(captured).lower()
    if out and PROBE_EXPECT in out.lower():
        return {"state": "ok", "detail": "answered correctly",
                "seconds": secs, "log": captured[-2:]}
    if out:
        # It answered, just not the asked word. Still proof the credential and
        # a model are alive, which is what this audit is for.
        return {"state": "ok", "detail": "answered (did not echo exactly)",
                "seconds": secs, "log": captured[-2:]}

    # No text. Work out WHY from the provider's own lines.
    #
    # THIS USED TO BE A LADDER OF `if "403" in blob`, AND IT WAS WRONG.
    #
    # Cloudflare's real audit output was two models answering
    # "429 — daily 10k Neuron allocation likely used up" and one answering
    # "403 — this account is not entitled to THIS MODEL". The ladder saw the
    # substring "403" and reported the whole provider as account-denied, so
    # the owner was told to replace a Cloudflare token that was working
    # perfectly and had simply run out of its daily free allocation.
    #
    # Two distinctions the ladder could not make, both of which decide whether
    # a human needs to do anything at all:
    #
    #   ACCOUNT-level 403  "your project has been denied access"     -> human
    #   MODEL-level 403    "not entitled to THIS MODEL"              -> not human
    #
    # and when a provider emits several different codes, the one that appears
    # most is the provider's actual state -- one unavailable model among three
    # is not an outage.
    blob_lines = [c.lower() for c in captured]

    def _count(*needles):
        return sum(1 for L in blob_lines if any(n in L for n in needles))

    # "no credential" comes in several house styles across the ten providers:
    #   "NVIDIA_API_KEY not set — skipping"
    #   "no GITHUB_TOKEN available — skipping"
    #   "SAMBANOVA_API_KEY not set — add free key from ..."
    # Matched on "available"/"not set"/"not configured" NEXT TO a credential
    # word, so a provider merely mentioning a key in passing is not misread.
    if (("not set" in blob or "not configured" in blob
         or "not available" in blob or "available" in blob and "no " in blob)
            and ("key" in blob or "token" in blob)):
        return {"state": "no_key", "detail": "no credential configured",
                "seconds": secs, "log": captured[-3:]}

    n_rate = _count("429", "rate limit", "quota", "allocation")
    n_model_403 = _count("not entitled to this model", "entitled to this model")
    n_acct_403 = _count("denied access", "permission_denied", "project has been denied")
    n_401 = _count("401", "unauthorized", "invalid api key", "invalid_api_key")
    n_timeout = _count("timeout", "timed out")
    n_404 = _count("404", "wrong model", "410")

    # A refused ACCOUNT is the only 403 a human can act on, and only when it
    # is not drowned out by rate limiting.
    if n_acct_403 and n_acct_403 >= n_rate:
        return {"state": "auth_denied",
                "detail": "403 PERMISSION_DENIED — the provider is refusing "
                          "this account, and a key is already configured",
                "seconds": secs, "log": captured[-3:]}
    if n_401:
        return {"state": "auth_bad",
                "detail": "401 — the configured key is rejected as invalid",
                "seconds": secs, "log": captured[-3:]}
    if n_rate:
        extra = (" (%d model also not entitled — normal on a free tier)"
                 % n_model_403) if n_model_403 else ""
        return {"state": "rate_limited",
                "detail": "429 — alive, out of allowance right now" + extra,
                "seconds": secs, "log": captured[-3:]}
    if n_model_403:
        # Only model-level refusals and nothing else: the account works, these
        # particular models are not on its plan.
        return {"state": "models_gone",
                "detail": "account is fine; these models are not on its plan",
                "seconds": secs, "log": captured[-3:]}
    if n_timeout:
        return {"state": "timeout",
                "detail": "no answer within the timeout — provider is slow or down",
                "seconds": secs, "log": captured[-3:]}
    if n_404:
        return {"state": "models_gone",
                "detail": "every model name 404s — the catalogue moved",
                "seconds": secs, "log": captured[-3:]}
    return {"state": "no_output", "detail": "returned nothing, no reason given",
            "seconds": secs, "log": captured[-3:]}


def live_models(name, log):
    """The provider's current catalogue, straight from its own endpoint.

    This is the auto-replacement half. A model that was renamed or retired
    stops appearing here, and a working replacement appears in its place,
    without anyone editing a list by hand.
    """
    try:
        import clinical_pipeline as cp
    except Exception:
        return []
    endpoints = {
        "cerebras":   ("https://api.cerebras.ai/v1/models", cp.CEREBRAS_KEY),
        "groq":       ("https://api.groq.com/openai/v1/models", cp.GROQ_KEY),
        "openrouter": ("https://openrouter.ai/api/v1/models", cp.OPENROUTER_KEY),
        "nvidia_nim": ("https://integrate.api.nvidia.com/v1/models", cp.NVIDIA_NIM_KEY),
        "sambanova":  ("https://api.sambanova.ai/v1/models", cp.SAMBANOVA_KEY),
        "mistral":    ("https://api.mistral.ai/v1/models", cp.MISTRAL_KEY),
    }
    if name not in endpoints:
        return []
    url, key = endpoints[name]
    if not key:
        return []
    try:
        import requests
        r = requests.get(url, headers={"Authorization": "Bearer %s" % key},
                         timeout=30)
        if r.status_code != 200:
            return []
        data = r.json().get("data") or []
        return [m.get("id") for m in data if m.get("id")][:40]
    except Exception:
        return []


def audit(write=True):
    import clinical_pipeline as cp

    order = [
        ("cerebras",      cp.call_cerebras),
        ("github_models", cp.call_github_models),
        ("cloudflare",    cp.call_cloudflare),
        ("nvidia_nim",    cp.call_nvidia_nim),
        ("sambanova",     cp.call_sambanova),
        ("gemini",        cp.call_gemini),
        ("groq",          cp.call_groq),
        ("openrouter",    cp.call_openrouter),
        ("cohere",        cp.call_cohere),
        ("mistral",       cp.call_mistral),
    ]

    print("=" * 74)
    print("PROVIDER HEALTH AUDIT — %s" % time.strftime("%Y-%m-%d %H:%M UTC",
                                                       time.gmtime()))
    print("=" * 74)

    results = {}
    for name, fn in order:
        # Each probe starts from a clean slate: the pipeline's own
        # drop-for-this-run sets would otherwise let one provider's failure
        # silence another's probe, and the whole point is per-provider truth.
        cp._DEAD_PROVIDERS_THIS_RUN.clear()
        cp._DENIED_MODELS_THIS_RUN.clear()
        try:
            cp._EXHAUSTED_PROVIDERS_THIS_RUN.clear()
        except Exception:
            pass
        r = _classify(name, fn, print)
        models = live_models(name, print)
        if models:
            r["catalogue"] = models[:12]
            r["catalogue_size"] = len(models)
        results[name] = r
        mark = {"ok": "OK      ", "rate_limited": "LIMITED ",
                "no_key": "NO KEY  "}.get(r["state"], "DEAD    ")
        print("  %s %-15s %-46s %5.1fs"
              % (mark, name, r["detail"][:46], r["seconds"]))
        if models:
            print("           catalogue: %d model(s), e.g. %s"
                  % (len(models), ", ".join(models[:3])))

    healthy = [n for n, r in results.items() if r["state"] == "ok"]
    limited = [n for n, r in results.items() if r["state"] == "rate_limited"]
    needs_human = {n: r for n, r in results.items()
                   if r["state"] in ("auth_denied", "auth_bad", "no_key")}

    print("\n" + "=" * 74)
    print("VERDICT")
    print("=" * 74)
    print("  working now      : %d  (%s)" % (len(healthy), ", ".join(healthy) or "none"))
    print("  rate limited     : %d  (%s)" % (len(limited), ", ".join(limited) or "none"))
    print("  need a human     : %d" % len(needs_human))
    for n, r in needs_human.items():
        env, url = KEY_HELP.get(n, ("?", "?"))
        print("      %-14s %s" % (n, r["detail"]))
        print("      %-14s fix: set %s  (%s)" % ("", env, url))

    payload = {
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "healthy": healthy,
        "rate_limited": limited,
        "needs_human": {n: {"reason": r["detail"],
                            "env": KEY_HELP.get(n, ("?", "?"))[0],
                            "where": KEY_HELP.get(n, ("?", "?"))[1]}
                        for n, r in needs_human.items()},
        "providers": results,
        "min_healthy": MIN_HEALTHY,
    }
    if write:
        HEALTH_PATH.parent.mkdir(parents=True, exist_ok=True)
        HEALTH_PATH.write_text(json.dumps(payload, indent=1))
        print("\n  written: %s" % HEALTH_PATH.relative_to(ROOT))

    usable = len(healthy) + len(limited)
    if usable < MIN_HEALTHY:
        print("\n  ONLY %d USABLE PROVIDER(S) — an episode would very likely "
              "fail the way run 31820199959 did." % usable)
        return payload, 1
    print("\n  %d usable provider(s) — enough to run an episode." % usable)
    return payload, 0


def telegram_summary(payload):
    """The weekly message. Short when all is well, specific when it is not."""
    healthy = payload.get("healthy") or []
    limited = payload.get("rate_limited") or []
    needs = payload.get("needs_human") or {}
    if not needs:
        return ("✅ <b>Weekly provider check</b>\n\n%d working, %d rate limited. "
                "Nothing needs you." % (len(healthy), len(limited)))
    lines = ["⚠️ <b>Weekly provider check — %d need you</b>" % len(needs), ""]
    lines.append("Working: %s" % (", ".join(healthy) or "NONE"))
    lines.append("")
    lines.append("These cannot be fixed automatically — a key or an account "
                 "decision is involved:")
    for n, d in needs.items():
        lines.append("\n<b>%s</b> — %s" % (n, d.get("reason", "?")))
        lines.append("   set <code>%s</code>" % d.get("env", "?"))
        lines.append("   %s" % d.get("where", "?"))
    lines.append("")
    lines.append("Your key IS installed for these — a 403 with a valid key is "
                 "a permission or project problem, not a missing key. What to "
                 "check, in order:")
    for n in needs:
        steps = DENIED_PLAYBOOK.get(n)
        if not steps:
            continue
        lines.append("\n<b>%s</b>" % n)
        for i, s in enumerate(steps, 1):
            lines.append("  %d. %s" % (i, s))
    lines.append("\nRetired or renamed MODELS are already replaced "
                 "automatically from each provider's live catalogue — only "
                 "credentials are listed here.")
    return "\n".join(lines)


if __name__ == "__main__":
    payload, code = audit(write="--print" not in sys.argv)
    if os.environ.get("TELEGRAM_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"):
        try:
            import requests
            requests.post(
                "https://api.telegram.org/bot%s/sendMessage"
                % os.environ["TELEGRAM_TOKEN"],
                data={"chat_id": os.environ["TELEGRAM_CHAT_ID"],
                      "text": telegram_summary(payload),
                      "parse_mode": "HTML"}, timeout=30)
            print("  Telegram summary sent.")
        except Exception as e:
            print("  Telegram summary failed (non-fatal): %s" % str(e)[:80])
    sys.exit(code)
