"""
title_score_history.json LEARNING LOOP — the title-scoring equivalent of
thumb_format_history.json (video_pipeline/thumbnail_formats.py).

FIX (found on deep re-audit): weekly_report.py's recalibrate_title_model()
claimed in its own docstring to "compare predicted CTR scores vs actual
performance," but never actually did — it wrote a static string built from
competitor title text, with score_title_v2 never referenced at all. Its own
comment admitted this was "currently write-only... a real landmine for
whenever it does get wired into something." This module is that wiring:
every generated title's real score_title_v2 result is recorded here, real
CTR is attached once YouTube Analytics has it (same growth_engine.py hooks
thumb_format_history already uses), and get_title_calibration_notes()
compares real CTR between historically high- and low-scored titles —
mirroring topic_scoring.py's get_scoring_calibration_notes(), the one
place in this codebase where this exact pattern was already proven to
work end-to-end.
"""
import json
import datetime
from pathlib import Path


def _history_file(cache_dir):
    return Path(cache_dir) / "title_score_history.json"


def load_title_history(cache_dir):
    """Returns the full history list, oldest first. Never raises — a
    missing/corrupt file just means an empty history (first run)."""
    f = _history_file(cache_dir)
    if not f.exists():
        return []
    try:
        data = json.loads(f.read_text())
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_title_history(cache_dir, history):
    f = _history_file(cache_dir)
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(history[-2000:], indent=2))
    except Exception:
        pass


def record_title_used(cache_dir, channel_name, niche_name, episode, title, score, video_id=None):
    """
    Appends one real history entry — never overwrites. video_id is filled
    in later by attach_title_video_id() once the upload has happened.
    """
    history = load_title_history(cache_dir)
    history.append({
        "channel":   channel_name,
        "niche":     niche_name,
        "episode":   episode,
        "title":     title,
        "score":     score,
        "video_id":  video_id,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "ctr_pct":   None,
    })
    _save_title_history(cache_dir, history)
    return history


def record_title_ctr(cache_dir, video_id, ctr_pct):
    """
    Called once real CTR data exists for a video (growth_engine.py's CTR
    recovery mechanism, the same real impressionsClickThroughRate pull
    thumb_format_history's record_format_ctr already uses). Finds the
    history entry for this video_id and fills in its real performance.
    """
    if not video_id:
        return False
    history = load_title_history(cache_dir)
    updated = False
    for entry in history:
        if entry.get("video_id") == video_id:
            entry["ctr_pct"] = ctr_pct
            updated = True
    if updated:
        _save_title_history(cache_dir, history)
    return updated


def attach_title_video_id(cache_dir, channel_name, video_id):
    """
    The title is chosen and recorded at generation time, before the video
    has a YouTube video_id (that only exists after upload). Called from
    the same post-upload sprint that already attaches thumb_format_history's
    video_id — fills in video_id on the most recent not-yet-attached entry
    for this channel, matching thumbnail_formats.attach_video_id's exact
    "most recent unattached entry" approach.
    """
    history = load_title_history(cache_dir)
    for entry in reversed(history):
        if entry.get("channel") == channel_name and not entry.get("video_id"):
            entry["video_id"] = video_id
            _save_title_history(cache_dir, history)
            return True
    return False


def get_title_calibration_notes(cache_dir, min_samples=5):
    """
    Compares real CTR outcomes against the original score_title_v2 score
    for every title that has both, and generates a plain-language
    calibration note when there's a real, meaningful signal — e.g. "titles
    scored 8+ have NOT been matching that with real CTR." Mirrors
    topic_scoring.get_scoring_calibration_notes() exactly.

    Returns "" if there isn't enough real data yet to say anything
    meaningful — never fabricates a signal from too little data.
    """
    history = load_title_history(cache_dir)
    scored_with_outcome = [e for e in history if e.get("ctr_pct") is not None
                            and e.get("score") is not None]
    if len(scored_with_outcome) < min_samples:
        return ""

    high_scored = [e for e in scored_with_outcome if e["score"] >= 8.0]
    low_scored = [e for e in scored_with_outcome if e["score"] < 8.0]
    if len(high_scored) < 2 or len(low_scored) < 2:
        return ""

    avg_high = sum(e["ctr_pct"] for e in high_scored) / len(high_scored)
    avg_low = sum(e["ctr_pct"] for e in low_scored) / len(low_scored)

    # Only surface a note when the real difference is large enough to be
    # a genuine signal, not noise from a handful of data points.
    if avg_high < avg_low - 0.5:
        return (f"REAL PERFORMANCE CALIBRATION (from {len(scored_with_outcome)} actual past "
                f"episodes, not a guess): titles scoring 8+/10 on score_title_v2 have NOT been "
                f"matching that with real CTR ({avg_high:.1f}% vs {avg_low:.1f}% for lower-scored "
                f"titles) — the scoring rubric is currently overconfident, treat its picks "
                f"more skeptically until this improves.")
    elif avg_high > avg_low + 0.5:
        return (f"REAL PERFORMANCE CALIBRATION (from {len(scored_with_outcome)} actual past "
                f"episodes, not a guess): titles scoring 8+/10 on score_title_v2 have genuinely "
                f"delivered stronger real CTR ({avg_high:.1f}% vs {avg_low:.1f}%) — this "
                f"scoring rubric has been a reliable real predictor, keep favoring its picks.")
    return (f"REAL PERFORMANCE CALIBRATION (from {len(scored_with_outcome)} actual past "
            f"episodes): no meaningful real CTR difference yet between high- and low-scored "
            f"titles ({avg_high:.1f}% vs {avg_low:.1f}%) — not enough signal to say the "
            f"rubric is over- or under-confident.")
