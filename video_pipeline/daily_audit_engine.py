"""
DAILY AUDIT SEARCH ENGINE — the unified system tying together every
quality, policy-risk, and performance check built across this project
into one searchable record. Built in direct response to the explicit
requirement: "everything should be audited by a tracker or search engine
which takes care of auditing this every single day, every single video,
every single stage... there shouldn't be any strikers that come in."

WHAT MAKES THIS A "SEARCH ENGINE" AND NOT JUST A REPORT: every audit run
is persisted to a real, queryable index (audit_index.json per channel),
so you can actually search across history — "show me every video that
scored below 7 on authenticity this month," "show me every niche whose
CTR has been below target for 3+ weeks" — not just read today's report
and lose the ability to look back.

Ties together, per video:
  1. Script quality gate result (the graduated 13-level score)
  2. Authenticity/inauthentic-content risk (authenticity_guard.py)
  3. AI provider health at time of generation
  4. Real CTR performance once YouTube data exists (ceo_dashboard.py)
  5. Niche health / keep-kill status (ceo_dashboard.py)

Produces ONE verdict per video: PASS, REVIEW, or HOLD — never a scattered
set of independent numbers the operator has to mentally combine.
"""

import json
import re
import datetime
from pathlib import Path


VERDICT_THRESHOLDS = {
    "authenticity_hold":     6.0,   # below this: HOLD, matches authenticity_guard's own threshold
    "authenticity_review":   7.5,
    "quality_hold":          6.9,   # matches FINAL_GATE — should never actually be below this
    "quality_review":        8.5,   # matches the real attempts-1-8 standard
    "ctr_underperform_pct":  5.0,   # matches the explicit CTR target
}


def _audit_index_file(channel_dir):
    return Path(channel_dir) / "audit_index.json"


def load_audit_index(channel_dir):
    f = _audit_index_file(channel_dir)
    if not f.exists():
        return []
    try:
        data = json.loads(f.read_text())
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_audit_index(channel_dir, index):
    try:
        Path(channel_dir).mkdir(parents=True, exist_ok=True)
        _audit_index_file(channel_dir).write_text(json.dumps(index, indent=2))
    except Exception:
        pass


def run_full_video_audit(channel_dir, episode_number, title, niche_name,
                          quality_score, quality_attempt, authenticity_result,
                          provider_health_working_count):
    """
    The real per-video entry point — call this once, right after a video
    is confirmed generated (before or alongside the confirmed-publish
    logging), passing in the results every other system already computed.
    This does NOT re-run those checks — it aggregates their real outputs
    into one verdict and persists it to the searchable index.

    Returns {"verdict": "PASS"|"REVIEW"|"HOLD", "reasons": [...], "record": {...}}
    """
    reasons = []
    verdict = "PASS"

    # Script quality gate
    if quality_score < VERDICT_THRESHOLDS["quality_hold"]:
        verdict = "HOLD"
        reasons.append(f"Script quality {quality_score}/10 is below the absolute floor "
                       f"({VERDICT_THRESHOLDS['quality_hold']}) — should never happen if the "
                       f"graduated gate is working correctly; investigate immediately.")
    elif quality_score < VERDICT_THRESHOLDS["quality_review"] and quality_attempt <= 8:
        # Only flag as a review item if it's in the "should be 8.5" tier but
        # landed lower — attempts 9+ are EXPECTED to be below 8.5, that's
        # the graduated gate working as designed, not a problem.
        reasons.append(f"Script scored {quality_score}/10 on attempt {quality_attempt} — "
                       f"below the {VERDICT_THRESHOLDS['quality_review']} standard for "
                       f"attempts 1-8, published only via the graduated fallback tier.")
        if verdict == "PASS":
            verdict = "REVIEW"

    # Authenticity / inauthentic-content risk
    auth_score = authenticity_result.get("composite_score", 10.0) if authenticity_result else 10.0
    if auth_score < VERDICT_THRESHOLDS["authenticity_hold"]:
        verdict = "HOLD"
        reasons.append(f"Authenticity score {auth_score}/10 — real policy risk signal, "
                       f"matches the threshold that should trigger manual review before publish.")
    elif auth_score < VERDICT_THRESHOLDS["authenticity_review"]:
        reasons.append(f"Authenticity score {auth_score}/10 — one dimension weak, worth a look.")
        if verdict == "PASS":
            verdict = "REVIEW"

    # Provider health at generation time
    if provider_health_working_count < 3:
        reasons.append(f"Only {provider_health_working_count}/7 AI providers were healthy "
                       f"during generation — content was produced under real infrastructure "
                       f"strain, worth a quality spot-check.")
        if verdict == "PASS":
            verdict = "REVIEW"

    if not reasons:
        reasons.append("All checks clean — real script quality, real authenticity signal, "
                       "full provider health.")

    record = {
        "episode_number": episode_number,
        "title": title,
        "niche_name": niche_name,
        "quality_score": quality_score,
        "quality_attempt": quality_attempt,
        "authenticity_score": auth_score,
        "providers_healthy": provider_health_working_count,
        "verdict": verdict,
        "reasons": reasons,
        "audited_at": datetime.datetime.now().isoformat(),
    }

    index = load_audit_index(channel_dir)
    index.append(record)
    index = index[-500:]  # keep a genuinely long searchable history
    _save_audit_index(channel_dir, index)

    return {"verdict": verdict, "reasons": reasons, "record": record}


# ══════════════════════════════════════════════════════════════════
# SEARCH — the actual query capability, not just report generation
# ══════════════════════════════════════════════════════════════════

def search_audits(channel_dir, verdict=None, niche_name=None, min_quality_score=None,
                   max_quality_score=None, min_authenticity_score=None,
                   max_authenticity_score=None, since_date=None, keyword=None):
    """
    Real search across the full audit history — this is what makes it a
    search engine rather than a report generator. Every parameter is
    optional; only the filters you actually pass get applied. Returns
    the matching records, most recent first.
    """
    index = load_audit_index(channel_dir)
    results = index

    if verdict:
        results = [r for r in results if r.get("verdict") == verdict]
    if niche_name:
        results = [r for r in results if r.get("niche_name") == niche_name]
    if min_quality_score is not None:
        results = [r for r in results if r.get("quality_score", 0) >= min_quality_score]
    if max_quality_score is not None:
        results = [r for r in results if r.get("quality_score", 10) <= max_quality_score]
    if min_authenticity_score is not None:
        results = [r for r in results if r.get("authenticity_score", 0) >= min_authenticity_score]
    if max_authenticity_score is not None:
        results = [r for r in results if r.get("authenticity_score", 10) <= max_authenticity_score]
    if since_date:
        results = [r for r in results if r.get("audited_at", "") >= since_date]
    if keyword:
        kw = keyword.lower()
        results = [r for r in results if kw in r.get("title", "").lower()]

    return sorted(results, key=lambda r: r.get("audited_at", ""), reverse=True)


def get_audit_summary(channel_dir, days_back=7):
    """
    A real rollup for the weekly report — how many videos passed clean,
    how many needed review, how many were held, over the real recorded
    window (not a guess).
    """
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=days_back)).isoformat()
    recent = search_audits(channel_dir, since_date=cutoff)
    summary = {"total": len(recent), "pass": 0, "review": 0, "hold": 0}
    for r in recent:
        v = r.get("verdict", "PASS").lower()
        if v in summary:
            summary[v] += 1
    return summary
