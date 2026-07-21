"""
11-FORMAT THUMBNAIL LIBRARY + thumb_format_history LEARNING LOOP.

Shared across all 5 channels via thumbnail_engine_v2.generate_thumbnail_v2().
Each of the 11 formats is a named, general-purpose compositional archetype
(not niche-specific) that modulates the existing 3-layer renderer:
silhouette on/off, text composition, an extra background-prompt style hint,
and an optional highlight annotation (red circle / arrow).

REAL LEARNING LOOP: every thumbnail generated appends one entry to
thumb_format_history.json (in the channel's persistent cache_dir) —
{channel, niche, episode, format, video_id, timestamp, ctr_pct}. This
replaces the old state["thumbnail_ab"] pattern, which only ever stored a
single overwritten last_style/last_episode value and could never support
a learning loop no matter what was built on top of it — a real *history*
was the missing piece.

ctr_pct is filled in later, once real YouTube Analytics CTR data exists
for that video (video_pipeline/growth_engine.py's CTR-recovery mechanism
already pulls impressionsClickThroughRate per video — record_format_ctr()
is the hook it calls). Once at least MIN_SAMPLES_TO_TRUST videos of a
format have real CTR data, select_thumbnail_format() weights selection
toward the higher-performing formats (epsilon-greedy: explore unproven/
under-sampled formats some of the time, exploit the best-known formats
the rest of the time) instead of pure rotation — genuine performance-
driven learning, not just a fixed cycle.
"""
import json
import random
import datetime
from pathlib import Path

# ══════════════════════════════════════════════════════════════════
# THE 11 FORMATS
# ══════════════════════════════════════════════════════════════════
FORMAT_LIBRARY = {
    "big_face_reaction": {
        "silhouette": True,
        "composition_override": "text_lower_third",
        "bg_style_suffix": "extreme close-up dramatic reaction shocked expression partial face",
        "highlight": None,
    },
    "before_after_split": {
        "silhouette": False,
        "composition_override": "text_center",
        "bg_style_suffix": "split screen before and after comparison dramatic contrast",
        "highlight": None,
    },
    "bold_text_statement": {
        "silhouette": False,
        "composition_override": "text_center",
        "bg_style_suffix": "minimal dark background bold dramatic atmosphere",
        "highlight": None,
    },
    "candid_shot": {
        "silhouette": True,
        "composition_override": "text_lower_third",
        "bg_style_suffix": "candid unposed natural moment caught off guard documentary style",
        "highlight": None,
    },
    "object_evidence_closeup": {
        "silhouette": False,
        "composition_override": "text_upper_third",
        "bg_style_suffix": "single object extreme macro close-up forensic evidence dramatic lighting",
        "highlight": None,
    },
    "silhouette_dramatic": {
        "silhouette": True,
        "composition_override": "text_center",
        "bg_style_suffix": "dramatic silhouette backlit figure atmospheric",
        "highlight": None,
    },
    "red_circle_highlight": {
        "silhouette": False,
        "composition_override": "text_lower_third",
        "bg_style_suffix": "wide establishing scene with one small significant detail visible",
        "highlight": "circle",
    },
    "comparison_grid": {
        "silhouette": False,
        "composition_override": "text_upper_third",
        "bg_style_suffix": "two contrasting scenes side by side grid layout dramatic",
        "highlight": None,
    },
    "number_countdown": {
        "silhouette": False,
        "composition_override": "text_center",
        "bg_style_suffix": "dark atmospheric clock or countdown or numeric motif dramatic",
        "highlight": None,
    },
    "question_hook_text": {
        "silhouette": False,
        "composition_override": "text_center",
        "bg_style_suffix": "mysterious dark scene with one obscured detail dramatic atmosphere",
        "highlight": None,
    },
    "map_diagram_overlay": {
        "silhouette": False,
        "composition_override": "text_lower_third",
        "bg_style_suffix": "map or diagram or timeline overlay dark documentary style",
        "highlight": "arrow",
    },
}

ALL_FORMATS = list(FORMAT_LIBRARY.keys())
MIN_SAMPLES_TO_TRUST = 2   # a format needs at least this many CTR data points before its average is trusted
EXPLORE_PROBABILITY  = 0.35  # even once formats have proven data, keep sampling untested/weaker ones sometimes


def _history_file(cache_dir):
    return Path(cache_dir) / "thumb_format_history.json"


def load_format_history(cache_dir):
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


def _save_format_history(cache_dir, history):
    f = _history_file(cache_dir)
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(history[-2000:], indent=2))
    except Exception:
        pass


def record_format_used(cache_dir, channel_name, niche_name, episode, format_name, video_id=None):
    """
    Appends one real history entry — never overwrites. This is the fix for
    the old single-value thumbnail_ab overwrite: every episode's format
    choice is preserved, which is what select_thumbnail_format() and
    record_format_ctr() both depend on.
    """
    history = load_format_history(cache_dir)
    history.append({
        "channel":   channel_name,
        "niche":     niche_name,
        "episode":   episode,
        "format":    format_name,
        "video_id":  video_id,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "ctr_pct":   None,
    })
    _save_format_history(cache_dir, history)
    return history


def record_format_ctr(cache_dir, video_id, ctr_pct):
    """
    Called once real CTR data exists for a video (growth_engine.py's CTR
    recovery mechanism, which already pulls impressionsClickThroughRate
    from YouTube Analytics per video). Finds the history entry for this
    video_id and fills in its real performance — the data
    select_thumbnail_format() actually learns from.
    """
    if not video_id:
        return False
    history = load_format_history(cache_dir)
    updated = False
    for entry in history:
        if entry.get("video_id") == video_id:
            entry["ctr_pct"] = ctr_pct
            updated = True
    if updated:
        _save_format_history(cache_dir, history)
    return updated


def attach_video_id(cache_dir, channel_name, video_id):
    """
    The format is chosen and recorded at generation time, before the video
    has a YouTube video_id (that only exists after upload). Called from
    the post-upload sprint (growth_engine.py's run_post_upload_sprint,
    which runs for real after every upload — unlike the weekly cycle) to
    fill in video_id on the most recent not-yet-attached entry for this
    channel, so record_format_ctr() has something to match against once
    real CTR data comes in. Matches on "most recent unattached entry" for
    the channel rather than requiring an episode number, since the sprint
    doesn't carry one — safe given uploads happen strictly in sequence.
    """
    history = load_format_history(cache_dir)
    for entry in reversed(history):
        if entry.get("channel") == channel_name and not entry.get("video_id"):
            entry["video_id"] = video_id
            _save_format_history(cache_dir, history)
            return True
    return False


def _format_avg_ctr(history, format_name):
    samples = [e["ctr_pct"] for e in history if e.get("format") == format_name and e.get("ctr_pct") is not None]
    if not samples:
        return None, 0
    return sum(samples) / len(samples), len(samples)


def select_thumbnail_format(cache_dir, channel_name, niche_name, episode):
    """
    Real, measurable format selection:
      1. Never repeat the immediately previous format for this channel
         (format variety, same principle as the Shorts format-variety rule).
      2. If enough formats have >=MIN_SAMPLES_TO_TRUST real CTR samples,
         mostly (1 - EXPLORE_PROBABILITY) pick the best-performing proven
         format; the rest of the time, explore an unproven/under-sampled
         format so new data keeps coming in.
      3. With no proven data yet (cold start), rotate through the library
         round-robin by episode number so all 11 get real exposure.
    """
    history = load_format_history(cache_dir)
    channel_history = [e for e in history if e.get("channel") == channel_name]

    last_format = channel_history[-1]["format"] if channel_history else None
    candidates = [f for f in ALL_FORMATS if f != last_format] or list(ALL_FORMATS)

    proven = {}
    for f in candidates:
        avg, n = _format_avg_ctr(history, f)
        if avg is not None and n >= MIN_SAMPLES_TO_TRUST:
            proven[f] = avg

    if proven and random.random() > EXPLORE_PROBABILITY:
        return max(proven, key=proven.get)

    unproven = [f for f in candidates if f not in proven]
    pool = unproven or candidates
    return pool[episode % len(pool)]


def apply_format(profile, format_name):
    """
    Returns (composition, bg_style_suffix, force_silhouette, highlight) for
    a chosen format, falling back to the niche profile's own defaults for
    anything a format doesn't override.
    """
    fmt = FORMAT_LIBRARY.get(format_name, {})
    composition = fmt.get("composition_override") or profile.get("composition", "text_center")
    bg_suffix   = fmt.get("bg_style_suffix", "")
    silhouette  = fmt.get("silhouette", False)
    highlight   = fmt.get("highlight")
    return composition, bg_suffix, silhouette, highlight
