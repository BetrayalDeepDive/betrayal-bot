"""
AUTHENTICITY GUARD — pre-publish inauthentic-content risk checker.

Built in response to YouTube's real 2025-2026 enforcement shift: the actual
policy test (verbatim from YouTube's own wording, confirmed via research
before building this) is "content that looks like it's made with a template
with little to no variation across videos, or content that's easily
replicable at scale" — NOT "was AI used." Enforcement happens at the
CHANNEL level: one detected pattern across a channel's last ~30 uploads
can pull monetization from every video on that channel, not just one.

This module checks the specific signals that actually matter:
  1. Structural variation — is this video's opening/pacing/structure too
     similar to this SAME channel's own recent uploads (not other
     channels — the risk is a channel repeating ITSELF).
  2. Editorial fingerprint — does the script contain genuine interpretation
     or POV, or is it flat fact-recitation a template could produce.
  3. Upload cadence — real enforcement data shows channels that fail this
     test publish more often than channels that pass it.
  4. Thumbnail-family variation — the 3-fixed-thumbnail-family system
     (built for brand consistency) is a double-edged sword: too-rigid
     repetition of the exact same composition is itself a risk signal.
     This checks that within a family, the specific pose/background
     actually varies episode to episode, not just the text overlay.

Each channel gets its own rolling history file (fingerprint_history.json,
stored in that channel's own SCRIPT_DIR — same principle as pending_upload.json
and state.json) so this genuinely compares a channel against ITS OWN past,
not a shared/global history.

Free-tier only: pure Python text-similarity (difflib), no embeddings, no
vector DB, no paid API. Reuses whichever AI provider chain the calling
pipeline already has (passed in as ai_fn) for the one LLM-scored check.
"""

import json
import re
import difflib
import statistics
import datetime
from pathlib import Path

HISTORY_LOOKBACK = 15          # how many past videos to compare against
MAX_HISTORY_STORED = 30        # trim the history file so it doesn't grow forever
CADENCE_WINDOW_HOURS = 20       # flag if 2+ uploads land within this window


# ══════════════════════════════════════════════════════════════════
# HISTORY STORAGE
# ══════════════════════════════════════════════════════════════════

def _history_file(channel_dir):
    return Path(channel_dir) / "fingerprint_history.json"


def load_fingerprint_history(channel_dir):
    """Returns the list of past fingerprint records, oldest first. Never
    raises — a missing or corrupted history file just means no history yet,
    which is the correct behavior for a channel's very first videos."""
    f = _history_file(channel_dir)
    if not f.exists():
        return []
    try:
        data = json.loads(f.read_text())
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_fingerprint_record(channel_dir, record: dict):
    """Appends one video's fingerprint to the rolling history, trimming to
    MAX_HISTORY_STORED so the file never grows unbounded. Call this AFTER
    a video is confirmed published, not during generation attempts, so
    rejected/regenerated attempts don't pollute the comparison history."""
    history = load_fingerprint_history(channel_dir)
    record["logged_at"] = datetime.datetime.now().isoformat()
    history.append(record)
    history = history[-MAX_HISTORY_STORED:]
    try:
        _history_file(channel_dir).write_text(json.dumps(history, indent=2))
    except Exception:
        pass  # non-fatal — losing one history write shouldn't break a publish


def build_fingerprint(script_clean, stage_texts, thumbnail_family, thumbnail_pose, title):
    """
    Builds the compact fingerprint record for one video. stage_texts should
    be the list of the 7 (or however many) individual script section texts
    already available mid-pipeline — no extra work to reconstruct them.
    """
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", script_clean) if s.strip()]
    opening = sentences[0] if sentences else ""
    stage_word_counts = [len(s.split()) for s in stage_texts] if stage_texts else []
    total = sum(stage_word_counts) or 1
    stage_ratios = [round(c / total, 3) for c in stage_word_counts]
    return {
        "title": title,
        "opening_sentence": opening[:200],
        "stage_ratios": stage_ratios,
        "thumbnail_family": thumbnail_family,
        "thumbnail_pose": thumbnail_pose,
        "word_count": total,
    }


# ══════════════════════════════════════════════════════════════════
# MINI-CHECK 1: STRUCTURAL VARIATION
# ══════════════════════════════════════════════════════════════════

def check_structural_variation(new_fingerprint, history):
    """
    Compares this video's opening sentence and stage-length pattern against
    the channel's own recent history. Returns (score 0-10, details dict).
    A LOW score means this video looks too similar to the channel's own
    recent output — the exact signal real enforcement reportedly weighs,
    since the risk is a channel repeating a rigid template, not any single
    video in isolation.
    """
    if not history:
        return 10.0, {"note": "No history yet — first videos can't be compared, scored clean by default."}

    recent = history[-HISTORY_LOOKBACK:]
    opening_similarities = []
    for past in recent:
        past_opening = past.get("opening_sentence", "")
        if not past_opening:
            continue
        ratio = difflib.SequenceMatcher(None, new_fingerprint["opening_sentence"].lower(),
                                         past_opening.lower()).ratio()
        opening_similarities.append(ratio)

    max_opening_sim = max(opening_similarities) if opening_similarities else 0.0

    # Stage-ratio variance check: if EVERY past video has almost identical
    # stage-length proportions, that rigid pattern is itself a risk signal,
    # regardless of how this one specific video compares.
    ratio_variance_flag = False
    if len(recent) >= 5 and new_fingerprint["stage_ratios"]:
        stage_count = len(new_fingerprint["stage_ratios"])
        per_stage_values = [[] for _ in range(stage_count)]
        for past in recent:
            past_ratios = past.get("stage_ratios", [])
            if len(past_ratios) == stage_count:
                for i, v in enumerate(past_ratios):
                    per_stage_values[i].append(v)
        stdevs = [statistics.pstdev(vals) for vals in per_stage_values if len(vals) >= 3]
        if stdevs and max(stdevs) < 0.015:  # suspiciously rigid — same shape every time
            ratio_variance_flag = True

    score = 10.0
    if max_opening_sim > 0.75:
        score -= 5.0   # near-identical opening line to a recent video — real, serious flag
    elif max_opening_sim > 0.55:
        score -= 2.5
    if ratio_variance_flag:
        score -= 3.0   # the whole channel's structure looks rigidly templated

    score = max(0.0, round(score, 1))
    return score, {
        "max_opening_similarity_to_recent_video": round(max_opening_sim, 2),
        "structure_looks_rigidly_templated_across_channel": ratio_variance_flag,
        "videos_compared_against": len(recent),
    }


# ══════════════════════════════════════════════════════════════════
# MINI-CHECK 2: EDITORIAL FINGERPRINT (the one LLM-scored check)
# ══════════════════════════════════════════════════════════════════

def check_editorial_fingerprint(script_clean, ai_fn):
    """
    Asks the AI to honestly judge whether this script contains genuine
    interpretation/analysis/POV, or reads as flat fact-recitation a
    template could produce. This directly targets the real distinction
    YouTube's own guidance draws: "AI executes, the human directs" vs
    "AI does the directing, creator presses publish."
    Returns (score 0-10, reasoning string). Fails safe: any error returns
    a neutral 7.0 rather than blocking a publish over an API hiccup.
    """
    prompt = f"""Read this documentary video script excerpt and answer honestly.

SCRIPT (first 800 chars): {script_clean[:800]}

Does this script show genuine editorial interpretation, a distinct angle,
or analytical framing — or does it read as flat recitation of events/facts
that any similar template could produce with different names swapped in?

Rate 0-10 where 10 = clearly has a distinct authored perspective and
framing, 0 = could be regenerated from a template with zero real judgment.
Answer with ONLY a number 0-10 on the first line, then one sentence of
reasoning on the second line."""
    try:
        result = ai_fn(prompt, tokens=100)
        if not result:
            return 7.0, "AI check unavailable this run — scored neutral, not blocked."
        lines = [l.strip() for l in result.strip().splitlines() if l.strip()]
        score_match = re.search(r'\b(\d+(?:\.\d+)?)\b', lines[0]) if lines else None
        score = float(score_match.group(1)) if score_match else 7.0
        score = max(0.0, min(10.0, score))
        reasoning = lines[1] if len(lines) > 1 else "No reasoning returned."
        return round(score, 1), reasoning
    except Exception as e:
        return 7.0, f"Check failed (non-fatal, scored neutral): {e}"


# ══════════════════════════════════════════════════════════════════
# MINI-CHECK 3: UPLOAD CADENCE
# ══════════════════════════════════════════════════════════════════

def check_upload_cadence(history):
    """
    Real enforcement data shows channels that fail the inauthentic-content
    test publish more frequently than channels that pass it. This checks
    whether recent uploads are landing suspiciously close together — a
    single-video-per-day schedule (this project's actual cadence) is safe;
    this exists to catch it if that ever gets pushed higher for "growth."
    """
    if len(history) < 2:
        return 10.0, {"note": "Not enough history to assess cadence yet."}
    timestamps = []
    for h in history[-10:]:
        try:
            timestamps.append(datetime.datetime.fromisoformat(h["logged_at"]))
        except Exception:
            continue
    if len(timestamps) < 2:
        return 10.0, {"note": "Insufficient timestamp data."}
    timestamps.sort()
    gaps_hours = [(timestamps[i+1] - timestamps[i]).total_seconds() / 3600
                  for i in range(len(timestamps) - 1)]
    min_gap = min(gaps_hours)
    tight_gaps = sum(1 for g in gaps_hours if g < CADENCE_WINDOW_HOURS)
    score = 10.0
    if tight_gaps >= 3:
        score = 4.0   # multiple back-to-back uploads — real cadence risk
    elif tight_gaps >= 1:
        score = 7.0
    return score, {"min_gap_hours": round(min_gap, 1), "tight_gap_count": tight_gaps}


# ══════════════════════════════════════════════════════════════════
# MINI-CHECK 4: THUMBNAIL-FAMILY VARIATION
# ══════════════════════════════════════════════════════════════════

def check_thumbnail_variation(new_family, new_pose, history):
    """
    The 3-fixed-thumbnail-family system exists for brand consistency, but
    real research is explicit: thumbnails become a risk signal specifically
    when they form "a templated pattern — same composition, same overlay,
    same character placement" across uploads. This checks that the exact
    same family+pose combination isn't repeating too soon.
    """
    if not history:
        return 10.0, {"note": "No history yet."}
    recent = history[-HISTORY_LOOKBACK:]
    same_combo_count = sum(
        1 for h in recent
        if h.get("thumbnail_family") == new_family and h.get("thumbnail_pose") == new_pose
    )
    score = 10.0
    if same_combo_count >= 2:
        score = 3.0   # this exact family+pose combo has repeated 2+ times recently
    elif same_combo_count == 1:
        score = 7.0
    return score, {"same_exact_combo_in_recent_history": same_combo_count}


# ══════════════════════════════════════════════════════════════════
# COMPOSITE SCORE — mirrors the existing per-stage script scoring model
# ══════════════════════════════════════════════════════════════════

def run_authenticity_check(channel_dir, script_clean, stage_texts, title,
                            thumbnail_family, thumbnail_pose, ai_fn):
    """
    The main entry point. Runs all 4 mini-checks, returns a composite
    score (0-10) plus a full mini-stage breakdown — same shape as the
    existing script-quality scoring, so this slots into the pipeline the
    same way. Does NOT itself decide to block publishing; the calling
    pipeline decides what to do with the score (see recommended gate
    logic in the docstring below).

    Returns: {
        "composite_score": float,
        "structural_variation": {"score": ..., "details": {...}},
        "editorial_fingerprint": {"score": ..., "reasoning": "..."},
        "upload_cadence": {"score": ..., "details": {...}},
        "thumbnail_variation": {"score": ..., "details": {...}},
    }

    RECOMMENDED GATE (apply in the calling pipeline):
      composite >= 7.5  -> publish normally
      6.0 <= composite < 7.5 -> publish, but send a Telegram flag noting
                                 which specific dimension was weak, for
                                 awareness (not blocking — early in a
                                 channel's life there's little history to
                                 compare against, so don't over-block)
      composite < 6.0  -> hold and alert for manual review before
                           publishing; this is a real, specific risk
                           signal, not a false-positive-prone guess
    """
    history = load_fingerprint_history(channel_dir)
    new_fp = build_fingerprint(script_clean, stage_texts, thumbnail_family, thumbnail_pose, title)

    struct_score, struct_details = check_structural_variation(new_fp, history)
    edit_score, edit_reasoning = check_editorial_fingerprint(script_clean, ai_fn)
    cadence_score, cadence_details = check_upload_cadence(history)
    thumb_score, thumb_details = check_thumbnail_variation(thumbnail_family, thumbnail_pose, history)

    # Weighted composite — structural variation and editorial fingerprint
    # matter most (they're the direct proxies for the real enforcement
    # test); cadence and thumbnail variation are real but secondary signals.
    composite = round(
        struct_score * 0.35 + edit_score * 0.35 + cadence_score * 0.15 + thumb_score * 0.15, 1
    )

    return {
        "composite_score": composite,
        "structural_variation": {"score": struct_score, "details": struct_details},
        "editorial_fingerprint": {"score": edit_score, "reasoning": edit_reasoning},
        "upload_cadence": {"score": cadence_score, "details": cadence_details},
        "thumbnail_variation": {"score": thumb_score, "details": thumb_details},
        "_fingerprint_to_log": new_fp,   # calling pipeline saves this AFTER confirmed publish
    }


def format_authenticity_report(result, channel_display_name=""):
    """Formats the check result into a readable Telegram-ready summary."""
    c = result["composite_score"]
    lines = [f"🛡️ Authenticity check ({channel_display_name}): {c}/10"]
    lines.append(f"  Structural variation: {result['structural_variation']['score']}/10")
    lines.append(f"  Editorial fingerprint: {result['editorial_fingerprint']['score']}/10 — "
                 f"{result['editorial_fingerprint']['reasoning']}")
    lines.append(f"  Upload cadence: {result['upload_cadence']['score']}/10")
    lines.append(f"  Thumbnail variation: {result['thumbnail_variation']['score']}/10")
    return "\n".join(lines)
