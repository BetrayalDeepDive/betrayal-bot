"""
quality_score_history.json — persists real per-episode audio/video
quality scores (score_audio_quality/score_video_quality from
quality_scoring.py) so weekly_report.py can surface a genuine weekly
average instead of never mentioning quality scores at all.

FIX (found on deep re-audit): audio/video quality scores were computed
for every episode (fed into the human review-gate breakdown a reviewer
sees once, per episode) but never persisted anywhere — weekly_report.py
had no way to report on them at all, real or otherwise. This module is
the missing persistence layer, mirroring the same proven pattern as
thumb_format_history.json and title_score_history.json.
"""
import json
import datetime
from pathlib import Path


def _history_file(cache_dir):
    return Path(cache_dir) / "quality_score_history.json"


def load_quality_history(cache_dir):
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


def _save_quality_history(cache_dir, history):
    f = _history_file(cache_dir)
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(history[-2000:], indent=2))
    except Exception:
        pass


def record_quality_scores(cache_dir, channel_name, episode, audio_score, video_score):
    """Appends one real history entry for an approved episode — never
    overwrites. audio_score/video_score may be None if scoring itself
    failed (recorded as None, not silently skipped, so a real scoring
    outage is visible rather than invisible)."""
    history = load_quality_history(cache_dir)
    history.append({
        "channel":      channel_name,
        "episode":      episode,
        "audio_score":  audio_score,
        "video_score":  video_score,
        "timestamp":    datetime.datetime.utcnow().isoformat(),
    })
    _save_quality_history(cache_dir, history)
    return history


def get_recent_quality_summary(cache_dir, days=7):
    """
    Real average audio/video quality score over the last `days` days,
    computed straight from recorded history — no invented numbers.
    Returns a plain-language summary string, or a clear "no data" string
    if nothing was recorded in the window (never fabricates a signal).
    """
    history = load_quality_history(cache_dir)
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    recent = []
    for e in history:
        try:
            ts = datetime.datetime.fromisoformat(e["timestamp"])
        except Exception:
            continue
        if ts >= cutoff:
            recent.append(e)

    if not recent:
        return "No episodes scored in the last 7 days."

    audio_scores = [e["audio_score"] for e in recent if e.get("audio_score") is not None]
    video_scores = [e["video_score"] for e in recent if e.get("video_score") is not None]

    audio_str = f"{sum(audio_scores) / len(audio_scores):.1f}/10" if audio_scores else "no data"
    video_str = f"{sum(video_scores) / len(video_scores):.1f}/10" if video_scores else "no data"
    return f"Avg audio quality: {audio_str} | Avg video quality: {video_str} ({len(recent)} episode(s) this week)"
