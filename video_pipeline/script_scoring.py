"""
Script-content rubric — Killer Hook / Narrative Craft / Topic Clarity.

Three measurable dimensions scored directly off the generated script text,
shared across all 5 channels via score_script_rubric(). Each channel's own
score_result()/score_script_er() calls this once per attempt and folds the
result into its existing 0-10 gate score — the same "adjustment, not
replacement" role the per-channel retention-hook validators already play.

Nothing here is an AI judge call: every check is a real, deterministic
signal read off the script text (specific numbers, weak openers, sentence
rhythm, keyword overlap with the assigned topic), matching how every other
scoring function in this codebase works. This keeps scoring free, instant,
and safe to run on every one of the up-to-13 attempts per episode without
burning extra AI provider quota.
"""
import re

_WEAK_OPENERS = [
    "in this video", "today we", "today i", "welcome back", "welcome to",
    "let's talk about", "have you ever wondered", "have you ever asked",
    "this is the story of", "it was a normal day", "so basically",
]

_QUESTION_CUES = ["why", "how", "what really", "what happened", "who was really",
                   "what nobody", "no one knew", "until"]

_ESCALATION_SIGNALS = ["but then", "suddenly", "everything changed", "it got worse",
                        "no one expected", "that's when", "things escalated", "spiraled"]

_RESOLUTION_SIGNALS = ["in the end", "turned out", "finally", "the truth", "what really happened",
                        "years later", "to this day", "the real reason"]

_STOPWORDS = {"the", "a", "an", "of", "in", "on", "and", "or", "to", "is", "was", "were", "that",
              "this", "for", "with", "at", "by", "from", "as", "it", "its", "his", "her", "their",
              "them", "he", "she", "they", "how", "why", "what", "who", "when", "where"}

_REHOOK_MARKERS = [
    "stop for a second", "wait.", "listen.", "stay with me", "if you're still",
    "if you are still", "if you've made it this far", "you need to understand",
    "notice something", "here's what you", "let that sink in", "sit with that",
    "you already sense", "ask yourself", "picture this for a second",
    "still with me", "you're still watching", "you are still watching",
]


def _sentences(text):
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]


def score_killer_hook(script_text):
    """
    Scores the opening ~10% of the script — the cold open — the single
    stretch that determines whether YouTube promotes the video at all.
    Real signals: a specific number/date (concrete claim beats a vague
    tease), no throat-clearing opener, an explicit unresolved question,
    and short punchy sentences rather than a scene-setting wind-up.
    """
    words = script_text.split()
    if len(words) < 40:
        return 0.0, ["Script too short to score hook"]

    hook_zone_wc = max(40, int(len(words) * 0.10))
    hook_zone = " ".join(words[:hook_zone_wc])
    hook_lower = hook_zone.lower()
    score = 3.0
    issues = []

    if re.search(r'\d', hook_zone):
        score += 2.5
    else:
        issues.append("No specific number/date in the hook")

    if any(w in hook_lower for w in _WEAK_OPENERS):
        score -= 2.0
        issues.append("Opens with a weak/generic opener")
    else:
        score += 1.5

    if any(w in hook_lower for w in _QUESTION_CUES) or "?" in hook_zone:
        score += 2.0
    else:
        issues.append("No open question/unresolved tension in the hook")

    hook_sentences = _sentences(hook_zone)
    if hook_sentences:
        avg_len = sum(len(s.split()) for s in hook_sentences) / len(hook_sentences)
        if avg_len <= 12:
            score += 1.0
        elif avg_len > 20:
            score -= 0.5
            issues.append("Hook sentences run too long")

    return round(min(max(score, 0.0), 10.0), 1), issues


def score_narrative_craft(script_text):
    """
    Scores overall script craft: does it actually escalate and resolve
    (a real beat structure across the middle/final thirds), does it vary
    sentence rhythm instead of reading flat, and does it avoid the
    repeated-phrase filler that unedited AI narration tends to produce.
    """
    words = script_text.split()
    total = len(words)
    if total < 300:
        return 0.0, ["Script too short to score narrative craft"]

    score = 4.0
    issues = []

    third = total // 3
    middle = " ".join(words[third:2 * third]).lower()
    final = " ".join(words[2 * third:]).lower()

    if any(sig in middle for sig in _ESCALATION_SIGNALS):
        score += 1.5
    else:
        issues.append("No clear escalation beat in the middle third")

    if any(sig in final for sig in _RESOLUTION_SIGNALS):
        score += 1.5
    else:
        issues.append("No clear resolution beat in the final third")

    sentences = _sentences(script_text)
    if len(sentences) >= 10:
        lengths = [len(s.split()) for s in sentences]
        mean = sum(lengths) / len(lengths)
        variance = sum((l - mean) ** 2 for l in lengths) / len(lengths)
        stdev = variance ** 0.5
        if stdev >= 4.0:
            score += 1.5
        else:
            issues.append("Flat sentence rhythm — little variation in sentence length")

    tokens = re.findall(r"[a-z']+", script_text.lower())
    if len(tokens) >= 40:
        grams = {}
        for i in range(len(tokens) - 3):
            g = " ".join(tokens[i:i + 4])
            grams[g] = grams.get(g, 0) + 1
        max_repeat = max(grams.values()) if grams else 0
        if max_repeat >= 4:
            score -= min(0.5 * (max_repeat - 3), 2.0)
            issues.append(f"A 4-word phrase repeats {max_repeat}x — likely unedited filler")
        else:
            score += 1.0

    return round(min(max(score, 0.0), 10.0), 1), issues


def score_topic_clarity(script_text, topic):
    """
    Does the script actually stay on the assigned topic, and does it state
    what the topic is early rather than making the viewer guess? Measured
    by real keyword overlap between the topic string and the script text,
    checked separately in the opening 15% and the final third to catch a
    script that starts on-topic and quietly drifts.
    """
    if not topic:
        return 5.0, []  # nothing to compare against — neutral, not a penalty

    words = script_text.split()
    total = len(words)
    if total < 300:
        return 0.0, ["Script too short to score topic clarity"]

    topic_keywords = {
        w.strip(".,;:!?\"'").lower() for w in topic.split()
        if len(w) > 3 and w.strip(".,;:!?\"'").lower() not in _STOPWORDS
    }
    if not topic_keywords:
        return 5.0, []

    score = 3.0
    issues = []

    opening = " ".join(words[:int(total * 0.15)]).lower()
    if any(k in opening for k in topic_keywords):
        score += 2.5
    else:
        issues.append("Topic isn't clearly established in the opening 15%")

    full_lower = script_text.lower()
    overall_hits = sum(1 for k in topic_keywords if k in full_lower)
    coverage = overall_hits / len(topic_keywords)
    if coverage >= 0.5:
        score += 2.5
    elif coverage >= 0.25:
        score += 1.0
    else:
        issues.append(f"Low topic-keyword coverage ({overall_hits}/{len(topic_keywords)})")

    final_third = " ".join(words[int(total * 0.66):]).lower()
    final_hits = sum(1 for k in topic_keywords if k in final_third)
    if final_hits == 0 and overall_hits > 0:
        score -= 1.0
        issues.append("Final third drifts off-topic (no topic keywords)")
    elif final_hits >= 1:
        score += 1.5

    return round(min(max(score, 0.0), 10.0), 1), issues


def validate_rehook_beat(script_text):
    """
    Checks for the mid-video "rehook" beat — a direct-address moment that
    breaks documentary narration to speak to "you" the viewer — placed at
    the drift point, roughly the 50-72% mark of the script, where
    retention research shows mid-video attention is most likely to lapse.
    Real, deterministic check: direct-address marker phrases plus a real
    density of second-person pronouns in that window, not just one or the
    other (a stray "you" elsewhere in the narration shouldn't count).

    Returns (bonus_or_penalty, issues) meant to be folded straight into a
    channel's existing score_result()/score_script_er() total, same as the
    30/60/80% retention-hook validators already do.
    """
    words = script_text.split()
    total = len(words)
    if total < 400:
        return 0.0, []

    drift_zone = " ".join(words[int(total * 0.50):int(total * 0.72)]).lower()
    has_marker = any(m in drift_zone for m in _REHOOK_MARKERS)
    you_count = len(re.findall(r'\byou\b', drift_zone))

    if has_marker and you_count >= 2:
        return 0.5, []
    elif has_marker or you_count >= 3:
        return 0.2, []
    return -0.6, ["Missing mid-video rehook — no direct-address beat near the drift point (50-72%)"]


def score_script_rubric(script_text, topic=""):
    """
    Combined Killer Hook / Narrative Craft / Topic Clarity rubric.

    Returns (bonus, issues, subscores):
      bonus     - small +/- adjustment (capped at +/-1.5) meant to be added
                  directly to a channel's existing score_result()/
                  score_script_er() total.
      issues    - combined list of human-readable issue strings, for logging.
      subscores - {"killer_hook": x, "narrative_craft": y, "topic_clarity": z},
                  each 0-10, for logging/telemetry.
    """
    if not script_text:
        return 0.0, ["Empty script"], {}

    hook_score, hook_issues = score_killer_hook(script_text)
    craft_score, craft_issues = score_narrative_craft(script_text)
    clarity_score, clarity_issues = score_topic_clarity(script_text, topic)

    subscores = {
        "killer_hook": hook_score,
        "narrative_craft": craft_score,
        "topic_clarity": clarity_score,
    }
    issues = hook_issues + craft_issues + clarity_issues

    avg = (hook_score + craft_score + clarity_score) / 3.0
    bonus = round((avg - 5.0) * 0.3, 2)
    bonus = max(-1.5, min(1.5, bonus))

    return bonus, issues, subscores
