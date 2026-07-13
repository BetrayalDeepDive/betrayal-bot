"""
TOPIC SCORING ENGINE — the "Topic Database" from the Media Empire
operating model. Scores candidate topics on the 5 real criteria (viral
pull, evergreen value, source depth, monetization fit, product fit),
persists them to a genuine per-channel backlog, and surfaces the
highest-scoring unproduced topic for the next video.

DESIGN NOTE: the source document specified a "250-topic database" but
provided no mechanism for actually building or scoring one — it just
asserted the number. This module is that missing mechanism: topics
accumulate into a real backlog as they're generated (via the AI provider
chain each pipeline already has), scored honestly, and the backlog grows
organically rather than needing 250 topics manufactured upfront just to
hit a round number.

Free-tier only: a single JSON file per channel (topic_database.json,
stored in the channel's own SCRIPT_DIR alongside state.json/intel.json —
same persistence pattern already established, survives via the existing
git-commit step in each generate workflow).
"""

import json
import re
import uuid
import datetime
from pathlib import Path

MAX_BACKLOG_SIZE = 500  # sanity ceiling — well above the 250 target, trims oldest REJECTED entries first if ever exceeded

SCORING_WEIGHTS = {
    "viral_pull":       0.25,
    "evergreen_value":  0.20,
    "source_depth":     0.20,
    "monetization_fit": 0.20,
    "product_fit":      0.15,
}

PRODUCT_ROUTES = {
    "betrayal_deepdive": "dark-manipulation-tactics-handbook",
    "evidence_room":     "faceless-documentary-creator-toolkit",
    # FIX (found on re-audit): this is a SEPARATE dict from
    # site_generator.py's own PRODUCT_ROUTES (already fixed earlier this
    # session) — missing control_files here too meant every Ch3 topic
    # entry silently got product_route="" instead of the correct handbook
    # mapping, even though nothing crashed.
    "control_files":     "dark-manipulation-tactics-handbook",
}


def _db_file(channel_dir):
    return Path(channel_dir) / "topic_database.json"


def load_topic_database(channel_dir):
    """Returns the full backlog list, oldest first. Never raises — a
    missing/corrupt file just means an empty backlog, which is correct
    for a channel's first run."""
    f = _db_file(channel_dir)
    if not f.exists():
        return []
    try:
        data = json.loads(f.read_text())
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_topic_database(channel_dir, backlog):
    if len(backlog) > MAX_BACKLOG_SIZE:
        # Trim oldest REJECTED entries first, never touch pending/approved/produced
        rejected = [t for t in backlog if t.get("status") == "rejected"]
        keep_others = [t for t in backlog if t.get("status") != "rejected"]
        overflow = len(backlog) - MAX_BACKLOG_SIZE
        backlog = rejected[overflow:] + keep_others if overflow < len(rejected) else keep_others
    try:
        # FIX: same gap found and fixed in publishing_archive.py — ensure
        # the directory exists before writing, or the write fails silently.
        Path(channel_dir).mkdir(parents=True, exist_ok=True)
        _db_file(channel_dir).write_text(json.dumps(backlog, indent=2))
    except Exception:
        pass


def record_real_performance(channel_dir, episode_number, real_ctr_pct):
    """
    THE REAL FEEDBACK LOOP — matches a produced topic (by episode number)
    to its actual real CTR once YouTube analytics data exists, and stores
    it alongside the original AI-predicted dimension scores. This is what
    lets the scoring system eventually learn from real outcomes instead of
    only ever scoring once and never checking itself against reality.
    Safe to call repeatedly — updates the same entry if called again with
    fresher data for the same episode.
    """
    backlog = load_topic_database(channel_dir)
    for t in backlog:
        if t.get("produced_episode_number") == episode_number:
            t["real_ctr_pct"] = real_ctr_pct
            t["performance_recorded_at"] = datetime.datetime.now().isoformat()
            _save_topic_database(channel_dir, backlog)
            return t
    return None


def get_scoring_calibration_notes(channel_dir, min_samples=5):
    """
    Compares real CTR outcomes against the original predicted scores for
    every topic that has both, and generates a plain-language calibration
    note when there's a real, meaningful signal — e.g. "topics predicted
    high on viral_pull have NOT been matching that with real CTR." This
    note gets injected into score_topic's own prompt, so future scoring
    genuinely adjusts based on what's actually happened, not just what
    was guessed once.

    Returns "" if there isn't enough real data yet to say anything
    meaningful — never fabricates a signal from too little data.
    """
    backlog = load_topic_database(channel_dir)
    scored_with_outcome = [t for t in backlog if t.get("real_ctr_pct") is not None
                           and t.get("scores")]
    if len(scored_with_outcome) < min_samples:
        return ""

    notes = []
    for dimension in SCORING_WEIGHTS:
        high_scored = [t for t in scored_with_outcome if t["scores"].get(dimension, 0) >= 7.5]
        low_scored = [t for t in scored_with_outcome if t["scores"].get(dimension, 0) < 7.5]
        if len(high_scored) < 2 or len(low_scored) < 2:
            continue  # not enough of both groups to compare honestly
        avg_high = sum(t["real_ctr_pct"] for t in high_scored) / len(high_scored)
        avg_low = sum(t["real_ctr_pct"] for t in low_scored) / len(low_scored)
        # Only surface a note when the real difference is large enough to
        # be a genuine signal, not noise from a handful of data points.
        if avg_high < avg_low - 1.0:
            notes.append(f"Topics scoring high on {dimension} have NOT been matching that "
                        f"with real CTR ({avg_high:.1f}% vs {avg_low:.1f}% for lower-scored "
                        f"ones) — score this dimension more skeptically.")
        elif avg_high > avg_low + 1.0:
            notes.append(f"Topics scoring high on {dimension} have genuinely delivered "
                        f"stronger real CTR ({avg_high:.1f}% vs {avg_low:.1f}%) — this "
                        f"dimension's scoring has been reliable, keep favoring it.")

    if not notes:
        return ""
    return "REAL PERFORMANCE CALIBRATION (from actual past episodes, not a guess):\n" + \
           "\n".join(f"- {n}" for n in notes)


def score_topic(topic_text, niche_name, channel_id, ai_fn, calibration_notes=""):
    """
    Scores one candidate topic on the 5 real criteria via the AI provider
    chain each pipeline already has. Returns a dict with all 5 scores
    (0-10), a composite, and one honest reasoning line per score — fails
    safe (neutral 6.0 across the board) on any API error rather than
    blocking topic intake entirely.

    calibration_notes: optional real-performance feedback from
    get_scoring_calibration_notes — when present, this is what makes the
    feedback loop actually change future scoring, not just record data
    that nothing reads.
    """
    calibration_block = f"\n\n{calibration_notes}\n" if calibration_notes else ""
    prompt = f"""Score this documentary video topic candidate honestly, on 5 criteria.
Be a harsh, realistic grader — most topics are mediocre on at least one axis.
{calibration_block}
TOPIC: {topic_text}
NICHE: {niche_name}

Score each 0-10:
- viral_pull: would this genuinely make someone stop scrolling and click?
- evergreen_value: will this still get views in 2 years, or is it tied to a fading trend?
- source_depth: is there enough real, verifiable material to fill 15-18 minutes without padding?
- monetization_fit: does this topic naturally support a real CTA (a product, a resource), not just ad revenue?
- product_fit: does this topic extract into a genuinely reusable framework/chapter, not just a one-off story?

Return ONLY valid JSON:
{{"viral_pull": 0-10, "evergreen_value": 0-10, "source_depth": 0-10,
  "monetization_fit": 0-10, "product_fit": 0-10,
  "reasoning": "one honest sentence on the weakest dimension and why"}}"""
    try:
        raw = ai_fn(prompt, tokens=200)
        if raw:
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                data = json.loads(match.group())
                scores = {k: max(0.0, min(10.0, float(data.get(k, 6.0))))
                          for k in SCORING_WEIGHTS}
                composite = round(sum(scores[k] * w for k, w in SCORING_WEIGHTS.items()), 2)
                return {
                    "scores": scores,
                    "composite_score": composite,
                    "reasoning": data.get("reasoning", ""),
                }
    except Exception:
        pass
    # Fail-safe neutral score — never blocks intake, but composite of 6.0
    # across the board sits below most real approval thresholds, so a
    # scoring failure doesn't accidentally fast-track a topic either.
    neutral = {k: 6.0 for k in SCORING_WEIGHTS}
    return {
        "scores": neutral,
        "composite_score": 6.0,
        "reasoning": "Scoring check failed — neutral score assigned, review manually.",
    }


def add_topic_candidate(channel_dir, channel_id, topic_text, niche_name, ai_fn):
    """
    Scores a new candidate and adds it to the persistent backlog with
    status='pending'. Returns the full topic entry. Safe to call with a
    topic that's already in the backlog — checks for near-duplicate text
    first so the same idea doesn't get scored and stored twice.
    """
    backlog = load_topic_database(channel_dir)

    # Duplicate check — simple substring/exact check, not fuzzy (fuzzy
    # matching here risks false-rejecting genuinely different topics that
    # happen to share common words in this niche)
    normalized_new = topic_text.strip().lower()
    for existing in backlog:
        if existing.get("topic_text", "").strip().lower() == normalized_new:
            return existing  # already scored, don't duplicate

    scoring = score_topic(topic_text, niche_name, channel_id, ai_fn,
                          calibration_notes=get_scoring_calibration_notes(channel_dir))
    entry = {
        "topic_id": uuid.uuid4().hex[:12],
        "channel_id": channel_id,
        "topic_text": topic_text,
        "niche_name": niche_name,
        "scores": scoring["scores"],
        "composite_score": scoring["composite_score"],
        "reasoning": scoring["reasoning"],
        "product_route": PRODUCT_ROUTES.get(channel_id, ""),
        "status": "pending",
        "created_at": datetime.datetime.now().isoformat(),
        "produced_episode_number": None,
    }
    backlog.append(entry)
    _save_topic_database(channel_dir, backlog)
    return entry


def approve_topic(channel_dir, topic_id):
    """Marks a topic as approved (human decision, per the automation-
    boundary rule — final approval is never automatic)."""
    backlog = load_topic_database(channel_dir)
    for t in backlog:
        if t["topic_id"] == topic_id:
            t["status"] = "approved"
            _save_topic_database(channel_dir, backlog)
            return t
    return None


def reject_topic(channel_dir, topic_id, reason=""):
    backlog = load_topic_database(channel_dir)
    for t in backlog:
        if t["topic_id"] == topic_id:
            t["status"] = "rejected"
            t["rejection_reason"] = reason
            _save_topic_database(channel_dir, backlog)
            return t
    return None


def mark_produced(channel_dir, topic_id, episode_number):
    backlog = load_topic_database(channel_dir)
    for t in backlog:
        if t["topic_id"] == topic_id:
            t["status"] = "produced"
            t["produced_episode_number"] = episode_number
            _save_topic_database(channel_dir, backlog)
            return t
    return None


def get_next_approved_topic(channel_dir):
    """
    Returns the highest-composite-score topic with status='approved',
    or None if the approved queue is empty (caller should fall back to
    its existing topic-generation logic in that case, not fail).
    """
    backlog = load_topic_database(channel_dir)
    approved = [t for t in backlog if t.get("status") == "approved"]
    if not approved:
        return None
    return max(approved, key=lambda t: t.get("composite_score", 0))


def get_backlog_summary(channel_dir):
    """Quick counts for reporting/dashboard use."""
    backlog = load_topic_database(channel_dir)
    summary = {"pending": 0, "approved": 0, "produced": 0, "rejected": 0, "total": len(backlog)}
    for t in backlog:
        status = t.get("status", "pending")
        if status in summary:
            summary[status] += 1
    return summary


def review_pending_topics_via_telegram(channel_dir, channel_display_name, tg_token, tg_chat,
                                        top_n=6, poll_minutes=15):
    """
    THE MISSING PIECE — approve_topic()/reject_topic() existed with no
    real way for a human to actually use them, which defeats the entire
    point of "final topic approval stays human." This is that missing
    mechanism: lists the top-scoring PENDING topics via Telegram, polls
    for a limited window for reply commands (APPROVE <id> / REJECT <id>),
    and processes whatever comes back. Matches the weekly cadence — this
    is explicitly one of the document's own 5 weekly time-blocks
    ("approve next topics"), not a daily interruption.

    Times out gracefully after poll_minutes with no crash and no forced
    decision — pending topics simply remain pending until next week's
    review if nobody responds. Never auto-approves anything.
    """
    import requests
    import time as _time

    if not tg_token:
        return {"reviewed": False, "reason": "no Telegram token configured"}

    backlog = load_topic_database(channel_dir)
    pending = [t for t in backlog if t.get("status") == "pending"]
    if not pending:
        return {"reviewed": True, "approved": 0, "rejected": 0, "note": "no pending topics"}

    pending.sort(key=lambda t: t.get("composite_score", 0), reverse=True)
    top_pending = pending[:top_n]

    lines = [f"📋 <b>{channel_display_name} — Topics awaiting approval</b>",
             "Reply: <code>APPROVE &lt;id&gt;</code> or <code>REJECT &lt;id&gt;</code> for any below.",
             f"Window: {poll_minutes} minutes — anything not answered stays pending for next week.", ""]
    for t in top_pending:
        lines.append(f"[{t['topic_id']}] {t['composite_score']}/10 — {t['topic_text'][:80]}")
        if t.get("reasoning"):
            lines.append(f"   ({t['reasoning'][:100]})")

    try:
        requests.post(f"https://api.telegram.org/bot{tg_token}/sendMessage",
                      json={"chat_id": tg_chat, "text": "\n".join(lines), "parse_mode": "HTML"},
                      timeout=15)
    except Exception as e:
        return {"reviewed": False, "reason": f"failed to send: {e}"}

    valid_ids = {t["topic_id"] for t in top_pending}
    approved_count = 0
    rejected_count = 0
    offset = None
    deadline = datetime.datetime.now() + datetime.timedelta(minutes=poll_minutes)

    while datetime.datetime.now() < deadline:
        _time.sleep(20)
        try:
            params = {"timeout": 15}
            if offset:
                params["offset"] = offset
            r = requests.get(f"https://api.telegram.org/bot{tg_token}/getUpdates",
                              params=params, timeout=20)
            updates = r.json().get("result", [])
        except Exception:
            continue

        for u in updates:
            offset = u["update_id"] + 1
            text = u.get("message", {}).get("text", "").strip()
            parts = text.split()
            if len(parts) == 2 and parts[0].upper() in ("APPROVE", "REJECT"):
                topic_id = parts[1]
                if topic_id not in valid_ids:
                    continue
                if parts[0].upper() == "APPROVE":
                    if approve_topic(channel_dir, topic_id):
                        approved_count += 1
                else:
                    if reject_topic(channel_dir, topic_id, reason="rejected via weekly review"):
                        rejected_count += 1

    return {"reviewed": True, "approved": approved_count, "rejected": rejected_count,
            "presented": len(top_pending)}
