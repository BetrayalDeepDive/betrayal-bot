"""
ONE PROVIDER HEALTH RECORD, SHARED BY ALL FIVE CHANNELS.

"It's not only for one channel. There are five channels, and it needs to keep
repeating. It's a process."

The five channels each have their own provider chain, but they all authenticate
with the SAME secrets -- one GEMINI_API_KEY, one CLOUDFLARE_API_TOKEN, one
GROQ_API_KEY. So a credential that is refused for Ch1 on Thursday is refused
for Ch4 on Friday, and there is no reason for five pipelines to each rediscover
that the hard way. This file is the single record they all read and all write.

TWO WAYS IT LEARNS, WHICH IS WHAT MAKES IT CONTINUOUS RATHER THAN WEEKLY
------------------------------------------------------------------------
  Sunday      tools/provider_audit.py probes all ten deliberately and writes
              the full picture.
  Every run   note_denied() records a credential refusal the moment a live
              episode hits one. Thursday's discovery protects Friday's run
              without waiting for the weekend.

The second half matters more than the first. A weekly audit alone leaves a
six-day window in which every channel rediscovers the same dead key from
scratch -- which is exactly the five hours run 31820199959 spent.

WHAT IS AND IS NOT RECORDED AS "NEEDS A HUMAN"
----------------------------------------------
Only credential refusals: 401, and an ACCOUNT-level 403. Deliberately not:

  429 rate limited        a busy day, retry tomorrow
  model-level 403         "not entitled to THIS MODEL" -- the account is fine
  timeout                 slow, not refused
  404 on a model name     the catalogue moved; discovery handles it

Cloudflare was misreported as account-denied on the first audit because one
of its three models answered "not entitled to this model" while the other two
answered 429. The owner was told to replace a working token. That distinction
is why this module records a REASON alongside every entry rather than a bare
provider name.
"""
import json
import time
from pathlib import Path

# Lives in video_pipeline because every channel already imports from here.
# Putting it under one channel would make the other four second-class readers
# of a file they equally own.
HEALTH_PATH = Path(__file__).parent / "provider_health.json"

# A verdict older than this is ignored. A stale one is worse than none: it
# would keep skipping a provider whose key was fixed a fortnight ago, and
# nothing would ever put it back.
MAX_AGE_DAYS = 14

_CACHE = [None]


def _load():
    try:
        if HEALTH_PATH.exists():
            return json.loads(HEALTH_PATH.read_text())
    except Exception:
        pass
    return {}


def _age_days(data):
    try:
        import datetime as dt
        when = dt.datetime.strptime(data.get("checked_at", ""),
                                    "%Y-%m-%dT%H:%M:%SZ")
        return (dt.datetime.utcnow() - when).days
    except Exception:
        return 999


def providers_known_dead(log_fn=None, max_age_days=MAX_AGE_DAYS):
    """Providers refusing on CREDENTIALS at last check. Advisory, never final.

    Returns a set of provider names a run should not waste time on. Empty when
    the file is missing, stale, or unreadable -- a health record must never be
    the reason nothing is attempted.
    """
    if _CACHE[0] is not None:
        return _CACHE[0]
    data = _load()
    dead = set()
    if data:
        age = _age_days(data)
        if age <= max_age_days:
            dead = set((data.get("needs_human") or {}).keys())
            if dead and log_fn:
                log_fn("  Provider health (%dd old): skipping %s — credentials "
                       "refused at last check." % (age, sorted(dead)))
        elif log_fn:
            log_fn("  Provider health is %dd old — ignoring it." % age)
    _CACHE[0] = dead
    return dead


def note_denied(provider, reason, env_name="", where="", log_fn=None):
    """A live run just hit a credential refusal. Record it for every channel.

    This is the continuous half. Called from a pipeline the moment a provider
    answers 401 or an account-level 403, so the next run of ANY channel starts
    already knowing, instead of paying for the same discovery again.
    """
    try:
        data = _load()
        if not data:
            data = {"checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                time.gmtime()),
                    "healthy": [], "rate_limited": [], "needs_human": {},
                    "providers": {}}
        needs = data.setdefault("needs_human", {})
        if provider in needs:
            return False                       # already known, nothing to do
        needs[provider] = {"reason": reason, "env": env_name, "where": where,
                           "found_by": "live run",
                           "found_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                     time.gmtime())}
        # Do NOT refresh checked_at: this is one observation, not a full audit,
        # and letting it reset the clock would keep a half-picture alive for
        # another fortnight.
        for k in ("healthy", "rate_limited"):
            if provider in (data.get(k) or []):
                data[k] = [p for p in data[k] if p != provider]
        HEALTH_PATH.write_text(json.dumps(data, indent=1))
        _CACHE[0] = None                       # next reader picks it up
        if log_fn:
            log_fn("  Recorded %s as credential-refused for every channel: %s"
                   % (provider, reason))
        return True
    except Exception as e:
        if log_fn:
            log_fn("  Could not record provider health (non-fatal): %s" % e)
        return False


def record_working_model(provider, model, log_fn=None):
    """Remember the model that actually answered for `provider`.

    THE MISSING HALF OF "REPLACE DECOMMISSIONED MODELS AUTOMATICALLY".
    ----------------------------------------------------------------
    Model discovery re-ranks a live catalogue on every run and keeps no memory
    of which of its suggestions ever produced a sentence. In run 31876972186
    that cost the whole job: NVIDIA's /v1/models advertises the full catalogue
    (base models included), the six-name cap landed entirely on names the chat
    endpoint does not serve, all three 404'd, and the run had no way to know
    that a different NVIDIA name had answered perfectly well that morning.

    So a name that DID work is written down here, shared by all five channels,
    and put at the head of the list next time. Discovery still leads on
    everything else -- this only stops the pipeline from forgetting a proven
    answer between one run and the next.
    """
    if not provider or not model:
        return False
    try:
        data = _load()
        if not data:
            data = {"checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                time.gmtime()),
                    "healthy": [], "rate_limited": [], "needs_human": {},
                    "providers": {}}
        known = data.setdefault("working_models", {})
        if known.get(provider) == model:
            return False
        known[provider] = model
        HEALTH_PATH.write_text(json.dumps(data, indent=1))
        _CACHE[0] = None
        if log_fn:
            log_fn("  Recorded %s as a working model for %s." % (model, provider))
        return True
    except Exception as e:
        if log_fn:
            log_fn("  Could not record working model (non-fatal): %s" % e)
        return False


def working_model(provider, max_age_days=MAX_AGE_DAYS):
    """The model last PROVEN to answer for `provider`, or "" if unknown.

    Returns "" rather than a guess when the record is missing or stale: a
    fourteen-day-old name is no better than what discovery would suggest, and
    a health file must never be the reason a provider is asked the wrong
    question.
    """
    data = _load()
    if not data or _age_days(data) > max_age_days:
        return ""
    return (data.get("working_models") or {}).get(provider, "") or ""


def summary_line():
    """One line for a run log or a report."""
    data = _load()
    if not data:
        return "provider health: never checked"
    return ("provider health (%dd old): %d working, %d limited, %d need a human"
            % (_age_days(data), len(data.get("healthy") or []),
               len(data.get("rate_limited") or []),
               len(data.get("needs_human") or {})))
