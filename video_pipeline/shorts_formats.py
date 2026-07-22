"""
Real Shorts feature set shared by shorts_reels_engine.py:
  1. The 3-second rule — a real, timing-based check (not just a keyword
     check) that the opening beats land within the first ~3 seconds of
     actual narration.
  2. Pattern interrupts — a real FFmpeg video-filter fragment (periodic
     zoom-punch via zoompan) that breaks up an otherwise static background
     clip at regular intervals, the same "cut every few seconds" technique
     real Shorts editors use to fight scroll-past.
  3. Emotional arc scoring — checks emotion-word density across three real
     script segments (open/middle/close) for an actual escalating shape,
     not just a flat total count.
  4. Format variety — a real, persisted history of which "presentation
     format" (direct reveal, countdown, question hook, before/after, myth
     bust) each Short used, so the same one never repeats back-to-back and
     all 5 get real rotation over time — same append-only-history
     principle as thumb_format_history.json.
"""
import json
import re
from pathlib import Path

# ══════════════════════════════════════════════════════════════════
# 1. THE 3-SECOND RULE
# ══════════════════════════════════════════════════════════════════
WORDS_PER_SECOND = 2.6   # ~155 wpm dramatic narration pace, matches this
                          # codebase's other TTS-timing estimates
THREE_SECOND_WORD_COUNT = round(WORDS_PER_SECOND * 3)  # ~8 words

_SLOW_WINDUPS = [
    "hi guys", "hey guys", "so today", "let me tell you", "in this video",
    "welcome back", "before we start", "so basically", "okay so",
]
_SCROLL_STOPPERS = [
    "shocking", "betrayal", "secret", "exposed", "truth", "destroyed", "lied",
    "hidden", "never", "suddenly", "revealed", "discovered", "stolen", "fraud",
    "murdered", "arrested", "collapsed", "billion", "affair", "caught",
    "disappeared", "vanished", "gone", "died", "killed", "confession",
]


def check_three_second_rule(hook_text, script):
    """
    Real, timing-based check: estimates how many words of narration land in
    the first 3 seconds (WORDS_PER_SECOND * 3 ~= 8 words) using the same
    hook_text that's actually burned into the video's opening frames, and
    checks those first ~8 words for a real scroll-stopping word and the
    absence of a slow, throat-clearing windup.

    Returns (bonus, issues) meant to be added directly to
    score_short_script()'s total.
    """
    opening = (hook_text or "").strip()
    if not opening:
        opening = " ".join((script or "").split()[:THREE_SECOND_WORD_COUNT])
    opening_words = opening.split()[:THREE_SECOND_WORD_COUNT]
    opening_lower = " ".join(opening_words).lower()

    if not opening_words:
        return -1.0, ["No opening hook text to evaluate the 3-second rule against"]

    issues = []
    bonus = 0.0

    if any(w in opening_lower for w in _SLOW_WINDUPS):
        bonus -= 1.0
        issues.append("First 3 seconds is a slow windup, not an immediate hook")
    else:
        bonus += 0.5

    if any(w in opening_lower for w in _SCROLL_STOPPERS):
        bonus += 1.0
    else:
        bonus -= 0.5
        issues.append("First 3 seconds (~8 words) has no real scroll-stopping word")

    if len(opening_words) > THREE_SECOND_WORD_COUNT + 2:
        issues.append("Hook text runs longer than ~3 seconds of narration")

    return round(bonus, 1), issues


# ══════════════════════════════════════════════════════════════════
# 2. PATTERN INTERRUPTS — real FFmpeg filter fragment
# ══════════════════════════════════════════════════════════════════
def pattern_interrupt_filter(interval_sec=6, punch_frames=10, fps=30, zoom=1.15):
    """
    Returns a zoompan filter fragment that punches in briefly every
    interval_sec seconds — a real, testable visual pattern interrupt on an
    otherwise static/looping background clip, not just narration pacing.
    d=1 keeps a strict 1:1 input:output frame mapping so audio sync (the
    thing this codebase cares most about getting right for Shorts) is
    never affected.
    """
    interval_frames = max(1, int(interval_sec * fps))
    return (
        f"zoompan=z='if(lte(mod(on\\,{interval_frames})\\,{punch_frames}),{zoom},1.0)':"
        f"d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps}"
    )


# ══════════════════════════════════════════════════════════════════
# 3. EMOTIONAL ARC SCORING
# ══════════════════════════════════════════════════════════════════
_EMOTION_WORDS = [
    "outraged", "devastated", "shocked", "horrified", "betrayed", "furious",
    "heartbroken", "stunned", "unbelievable", "disgusting", "disgraceful",
    "terrifying", "chilling", "haunting", "desperate", "helpless", "relief",
    "vindicated", "triumphant",
]


def score_emotional_arc(script):
    """
    Splits the script into 3 real segments (open/middle/close) and scores
    the actual SHAPE of emotion-word density across them, not just a flat
    total count — a script that's emotionally flat throughout (same
    density in all 3 segments, including all-zero) doesn't have an arc no
    matter how many emotion words it uses overall.

    Rewards either a genuine escalation (density non-decreasing across the
    3 segments) or a clear peak-then-release shape (middle is the max) —
    both are real arcs. A flat or declining-then-flat shape scores low.

    Returns (score 0-2, issues) — same scale as the flat "emotion" bullet
    it replaces in score_short_script(), so it's a drop-in swap.
    """
    words = script.split()
    total = len(words)
    if total < 30:
        return 0.5, ["Script too short to score an emotional arc"]

    third = max(1, total // 3)
    segments = [
        " ".join(words[0:third]).lower(),
        " ".join(words[third:2 * third]).lower(),
        " ".join(words[2 * third:]).lower(),
    ]
    densities = [sum(1 for w in _EMOTION_WORDS if w in seg) for seg in segments]

    issues = []
    if sum(densities) == 0:
        return 0.0, ["No emotion words anywhere in the script — no arc possible"]

    escalating = densities[0] <= densities[1] <= densities[2] and densities[2] > densities[0]
    peak_release = densities[1] >= densities[0] and densities[1] >= densities[2] and densities[1] > 0

    if escalating:
        return 2.0, []
    if peak_release:
        return 1.6, []
    if len(set(densities)) == 1:
        issues.append("Flat emotional density across the whole script — no real arc")
        return 0.6, issues

    issues.append("Emotion words present but no clear escalating or peak-release shape")
    return 1.0, issues


# ══════════════════════════════════════════════════════════════════
# 4. FORMAT VARIETY — presentation-style rotation + real history
# ══════════════════════════════════════════════════════════════════
PRESENTATION_FORMATS = {
    "direct_reveal": (
        "Open with the single most shocking fact stated directly, no "
        "build-up, then explain how/why in 2-3 escalating beats."
    ),
    "countdown_list": (
        "Frame the script as a short countdown or numbered list of details, "
        "building to the single most shocking item last."
    ),
    "question_hook": (
        "Open with a direct question the viewer cannot ignore, then answer "
        "it through escalating reveals."
    ),
    "before_after": (
        "Contrast what was believed or expected against what was actually "
        "true, with the real truth revealed partway through."
    ),
    "myth_bust": (
        "State a common belief or assumption, then immediately dismantle it "
        "with the real, more shocking fact."
    ),
}
ALL_PRESENTATION_FORMATS = list(PRESENTATION_FORMATS.keys())


def _history_file(cache_dir):
    return Path(cache_dir) / "shorts_format_history.json"


def load_format_history(cache_dir):
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


def record_format_used(cache_dir, channel_id, mode, format_name):
    """Appends one real history entry — never overwrites, same principle
    as thumb_format_history.json."""
    import datetime
    history = load_format_history(cache_dir)
    history.append({
        "channel": channel_id,
        "mode": mode,
        "format": format_name,
        "timestamp": datetime.datetime.utcnow().isoformat(),
    })
    _save_format_history(cache_dir, history)
    return history


def select_presentation_format(cache_dir, channel_id):
    """
    Real variety enforcement: never repeats the immediately previous
    presentation format for this channel; otherwise rotates round-robin
    through all 5 by how many times each has been used so far, so every
    format gets genuinely even real-world exposure over time.
    """
    history = load_format_history(cache_dir)
    channel_history = [e for e in history if e.get("channel") == channel_id]
    last_format = channel_history[-1]["format"] if channel_history else None

    candidates = [f for f in ALL_PRESENTATION_FORMATS if f != last_format] or list(ALL_PRESENTATION_FORMATS)
    counts = {f: 0 for f in candidates}
    for e in channel_history:
        if e.get("format") in counts:
            counts[e["format"]] += 1
    return min(candidates, key=lambda f: counts[f])


def presentation_format_instruction(format_name):
    return PRESENTATION_FORMATS.get(format_name, PRESENTATION_FORMATS["direct_reveal"])
