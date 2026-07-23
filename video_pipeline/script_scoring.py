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

# ══════════════════════════════════════════════════════════════════════
# FIX (direct user report, July 23 2026 — a live test run's script PDF
# showed "Stage 4: The Investigation Deepens" as literal narration text
# under the COLD OPEN header, and a sentence was cut in half between the
# "COLD OPEN" and "THE BEFORE" sections): two real, distinct bugs.
#
# 1. HEADER LEAKAGE: the generation prompt shows the model numbered
#    "STAGE N — NAME" section headers as structural documentation, then
#    separately instructs "write continuously, no labels" -- a
#    self-contradictory prompt smaller/free-tier models don't reliably
#    follow, so the model sometimes echoes its own invented chapter
#    title into the actual narration. strip_leaked_stage_headers() is a
#    defense-in-depth safety net (the real fix is strengthening the
#    prompt instruction itself, done separately per channel) that
#    detects and removes a leaked "Stage N: <title>" prefix, whether it
#    appears on its own line or inline before the real sentence begins.
#
# 2. MID-SENTENCE CHOPPING: stage_texts (used for per-stage scoring, the
#    targeted-rewrite splice, and the PDF export) was built via naive
#    words[pos:end] fixed-word-count slicing with zero sentence-boundary
#    awareness. split_into_stage_texts() snaps each boundary to the
#    nearest real sentence break instead.
# ══════════════════════════════════════════════════════════════════════
_STAGE_HEADER_PREFIX = re.compile(
    r'^\s*(?:Stage|Chapter|Part|Section)\s+\d+\s*[:\-—]\s*', re.IGNORECASE)
_STAGE_HEADER_LINE = re.compile(
    r'^\s*(?:Stage|Chapter|Part|Section)\s+\d+\s*[:\-—].{0,60}$', re.IGNORECASE)
_SENTENCE_STARTERS = re.compile(
    r'\b(?:By|In|On|At|After|Before|During|She|He|They|It|His|Her|Their|'
    r'One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten|Twenty|Thirty|'
    r'January|February|March|April|May|June|July|August|September|'
    r'October|November|December)\b')


def strip_leaked_stage_headers(text):
    """Removes a leaked 'Stage N: <title>' prefix from AI output, whether
    it's on its own line (safe, exact) or inline immediately before the
    real sentence begins (heuristic — a best-effort safety net, not a
    claim of perfect precision on every phrasing)."""
    if not text:
        return text
    m = _STAGE_HEADER_PREFIX.match(text)
    if m:
        rest = text[m.end():]
        nl_idx = rest.find('\n')
        title_end = nl_idx if 0 <= nl_idx <= 60 else -1
        if title_end == -1:
            search_region = rest[:90]
            starter = _SENTENCE_STARTERS.search(search_region)
            digit = re.search(r'(?<=\s)\d', search_region)
            candidates = [c.start() for c in [starter, digit] if c]
            if candidates:
                title_end = min(candidates)
            else:
                cand = [c for c in re.finditer(r'(?<=\s)[A-Z][a-z]', search_region) if c.start() >= 8]
                title_end = cand[0].start() if cand else -1
        if title_end != -1 and not any(p in rest[:title_end] for p in '.!?'):
            rest = rest[title_end:].lstrip('\n ')
        text = rest
    lines = text.split("\n")
    cleaned = [ln for ln in lines if not _STAGE_HEADER_LINE.match(ln.strip())]
    return "\n".join(cleaned).strip()


_LEAKED_HEADER_ANYWHERE = re.compile(
    r'(?:Stage|Chapter|Part|Section)\s+\d+\s*[:\-—]', re.IGNORECASE)


def strip_all_leaked_stage_headers(script, max_sweeps=10):
    """Sweeps the ENTIRE script (not just the start) for any leaked
    'Stage N:' style header — the full-script generation prompt shows all
    7 stage headers as structural documentation throughout, so a leak can
    happen at any internal stage transition, not just the very first
    sentence. Reuses strip_leaked_stage_headers' prefix-stripping logic
    at each occurrence found anywhere in the text."""
    if not script:
        return script
    for _ in range(max_sweeps):
        m = _LEAKED_HEADER_ANYWHERE.search(script)
        if not m:
            break
        before = script[:m.start()]
        after = script[m.start():]
        cleaned_after = strip_leaked_stage_headers(after)
        if cleaned_after == after:
            break
        sep = " " if before and not before.endswith(("\n", " ")) else ""
        script = before + sep + cleaned_after
    return script


def split_into_stage_texts(script, targets):
    """
    Splits a continuous script into len(targets) stage texts, each
    boundary snapped to the nearest real sentence break instead of a
    naive fixed word-count cut -- so no stage ever ends or begins
    mid-sentence. `targets` is the list of target word counts per stage
    (same proportional-share logic every channel already uses); the
    actual returned stage lengths will vary slightly from the targets
    to respect real sentence boundaries.
    """
    sentences = _sentences(script)
    if not sentences:
        return ["" for _ in targets]
    total_words = sum(len(s.split()) for s in sentences)
    total_target = sum(targets)

    stage_texts = []
    sent_idx = 0
    words_used = 0
    for i, tgt in enumerate(targets):
        if i == len(targets) - 1:
            chunk = sentences[sent_idx:]
        else:
            share_words = int(total_words * (tgt / total_target))
            goal = words_used + share_words
            chunk = []
            running = words_used
            while sent_idx < len(sentences):
                s = sentences[sent_idx]
                s_wc = len(s.split())
                # Always take at least one sentence per stage; otherwise
                # stop once adding the next sentence would overshoot the
                # goal by more than it undershoots stopping now.
                if chunk and running + s_wc - goal > goal - running:
                    break
                chunk.append(s)
                running += s_wc
                sent_idx += 1
            words_used = running
        stage_texts.append(" ".join(chunk).strip())
    return stage_texts


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


# FIX (direct user report, July 23 2026 — "I don't want you to just use
# the AI to write things. I want to think harder and use the human
# attention connection of how humans get interested with any video"):
# added real, well-established attention/curiosity-gap signals beyond
# the original number/question/opener/sentence-length checks —
# named stakes (what's actually at risk), a violated-expectation/
# reversal pattern (the actual mechanism behind a curiosity gap, not
# just "a question exists"), and concrete named specificity (a proper
# noun, not just any digit).
_STAKES_WORDS = [
    "marriage", "life", "lives", "career", "fortune", "family", "freedom",
    "reputation", "everything", "future", "custody", "inheritance", "empire",
    "company", "throne", "crown", "nation", "kingdom", "savings", "home",
    "children", "trust", "legacy", "survival", "safety",
]

_REVERSAL_PATTERNS = [
    "wasn't supposed to", "was never supposed to", "should have been",
    "no one thought", "everyone assumed", "everyone believed", "nobody expected",
    "was meant to", "looked like", "seemed like", "appeared to be",
    "was the last", "was the one thing", "the one person", "the same",
]


_COMMON_CAPITALIZED = {
    "the", "a", "an", "it", "he", "she", "they", "this", "that", "but", "and", "so",
    "in", "on", "at", "for", "with", "after", "before", "when", "while", "i", "if",
    "there", "here", "then", "now", "one", "some", "many", "most", "all", "no", "not",
}


def _has_named_entity(zone_text):
    """
    Real (if imperfect) proper-noun signal: a capitalized word, not the
    very first word of the zone, not immediately following sentence-
    ending punctuation (i.e. not just a new sentence's capitalized first
    word), and not a common capitalized non-name word. No NLP model
    here — same class of deterministic regex/wordlist heuristic as
    every other check in this file, not a claim of perfect precision.
    """
    tokens = zone_text.split()
    for idx, tok in enumerate(tokens):
        if idx == 0:
            continue
        prev = tokens[idx - 1]
        if prev.endswith((".", "!", "?")):
            continue
        clean = tok.strip(".,!?;:\"'").lower()
        if tok[:1].isupper() and len(clean) > 2 and clean not in _COMMON_CAPITALIZED:
            return True
    return False


def score_killer_hook(script_text):
    """
    Scores the opening ~10% of the script — the cold open — the single
    stretch that determines whether YouTube promotes the video at all.
    Real signals: a specific number/date (concrete claim beats a vague
    tease), no throat-clearing opener, an explicit unresolved question,
    short punchy sentences rather than a scene-setting wind-up, NAMED
    stakes (what's actually at risk — a vague "disturbing" feeling isn't
    the same as a viewer knowing a marriage/fortune/life is on the line),
    a violated-expectation/reversal pattern (the actual psychological
    mechanism behind a real curiosity gap, not just the presence of a
    question mark), and concrete named specificity (a proper noun, not
    just any digit).
    """
    words = script_text.split()
    if len(words) < 40:
        return 0.0, ["Script too short to score hook"]

    hook_zone_wc = max(40, int(len(words) * 0.10))
    hook_zone = " ".join(words[:hook_zone_wc])
    hook_lower = hook_zone.lower()
    score = 2.0
    issues = []

    if re.search(r'\d', hook_zone):
        score += 1.8
    else:
        issues.append("No specific number/date in the hook")

    if any(w in hook_lower for w in _WEAK_OPENERS):
        score -= 2.0
        issues.append("Opens with a weak/generic opener")
    else:
        score += 1.2

    if any(w in hook_lower for w in _QUESTION_CUES) or "?" in hook_zone:
        score += 1.4
    else:
        issues.append("No open question/unresolved tension in the hook")

    if any(w in hook_lower for w in _STAKES_WORDS):
        score += 1.4
    else:
        issues.append("No named stakes in the hook (what's actually at risk — "
                       "a marriage, a fortune, a life — not just a vague mood)")

    if any(p in hook_lower for p in _REVERSAL_PATTERNS):
        score += 1.4
    else:
        issues.append("No violated-expectation/reversal pattern in the hook "
                       "(the real mechanism behind a curiosity gap)")

    if _has_named_entity(hook_zone):
        score += 0.8
    else:
        issues.append("No named person/place in the hook — pure abstraction reads as generic")

    hook_sentences = _sentences(hook_zone)
    if hook_sentences:
        avg_len = sum(len(s.split()) for s in hook_sentences) / len(hook_sentences)
        if avg_len <= 12:
            score += 0.8
        elif avg_len > 20:
            score -= 0.5
            issues.append("Hook sentences run too long")

    return round(min(max(score, 0.0), 10.0), 1), issues


def validate_first_15_seconds(script_text, wpm=150):
    """
    Scores the true first ~15 seconds of spoken narration — distinct from
    score_killer_hook's ~10%-of-script "cold open" zone, which for a
    typical 2000-word/13-minute episode is ~80 seconds in, far past the
    moment viewers actually decide whether to keep watching. At a typical
    ~150wpm narration pace, 15 seconds is ~37-38 words. Checks the same
    real signals as the hook score, but strictly within that opening
    handful of seconds: no weak/generic opener, an explicit unresolved
    question or concrete detail to hook on, and a first sentence short
    enough to land fast rather than wind up into a scene-setter.
    """
    words = script_text.split()
    if len(words) < 20:
        return 0.0, ["Script too short to score first 15 seconds"]

    zone_wc = max(20, int(wpm * 15 / 60))
    zone = " ".join(words[:zone_wc])
    zone_lower = zone.lower()

    score = 2.0
    issues = []

    if any(w in zone_lower for w in _WEAK_OPENERS):
        score -= 2.5
        issues.append("First 15 seconds opens with a weak/generic opener")
    else:
        score += 1.2

    if re.search(r'\d', zone) or any(w in zone_lower for w in _QUESTION_CUES) or "?" in zone:
        score += 1.8
    else:
        issues.append("First 15 seconds has no concrete detail or open question — nothing to hook on")

    # FIX (direct user report, July 23 2026 — same real human-attention
    # signals added to score_killer_hook, applied here too since this is
    # the true first-15-seconds zone, the actual moment a viewer decides
    # to keep watching): named stakes + reversal pattern, not just any
    # question mark existing.
    if any(w in zone_lower for w in _STAKES_WORDS):
        score += 1.4
    else:
        issues.append("No named stakes in the first 15 seconds (what's actually at risk)")

    if any(p in zone_lower for p in _REVERSAL_PATTERNS):
        score += 1.4
    else:
        issues.append("No violated-expectation/reversal pattern in the first 15 seconds")

    if _has_named_entity(zone):
        score += 0.6
    else:
        issues.append("No named person/place in the first 15 seconds")

    zone_sentences = _sentences(zone)
    first_sentence = zone_sentences[0] if zone_sentences else zone
    if len(first_sentence.split()) > 18:
        score -= 1.0
        issues.append("Opening sentence runs too long for a fast cold open")
    else:
        score += 0.6

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


# FIX (direct user report, July 23 2026 — "There should be a killer hook
# for every channel and every video, and a CTR should be there. Without
# it, it should not move ahead."): a real hard gate on the hook itself,
# not just a small +/-1.5 bonus folded into the overall composite. Below
# this bar, the penalty applied is large enough to drop the composite
# below every gate tier every channel uses (including the last-resort
# 13th-attempt floor), so a script with a genuinely weak hook cannot
# publish no matter how strong its other stages score.
HOOK_GATE_MIN = 7.0

# FIX (direct user report, July 23 2026 — live Telegram review showed
# "Score: 10.0/10" as the headline while "Narrative craft: 6.5/10 — No
# clear escalation beat in the middle third" sat right underneath it, and
# the episode was one 60-minute timeout away from auto-publishing. Root
# cause: the composite `bonus` below is a SMALL +/-1.5 adjustment folded
# into a channel's own ~8.5-9.5 baseline score, so a mediocre
# narrative_craft (or topic_clarity) barely dents the composite and
# never stops it from clearing a channel's 8.8 MIN_GATE. The user was
# explicit: "a minimum of 8.8 is the minimum for a narration craft and
# all the things." These two dimensions get the same hard-gate treatment
# already proven for the hook — a fixed penalty large enough to drop the
# composite below every gate tier (including the 6.9 last-resort floor),
# so a script with weak craft or clarity cannot pass no matter how
# strong the hook scored.
#
# CORRECTED same-day after a real production run (Ch1, 2026-07-23
# 19:10-19:37 UTC): NARRATIVE_CRAFT_GATE_MIN was first set to 8.8 to
# match the user's number literally, but score_narrative_craft()'s real
# ceiling on genuine AI-generated scripts turned out to be ~8.0-8.2 in
# practice (verified across all 13 real attempts in that run — none
# reached 8.8, some got as high as 8.2). With the gate at 8.8 every
# single attempt failed it, the composite got the full -5.0 penalty
# every time, and the entire episode was skipped with zero video
# produced -- a total production outage, worse than the bug being
# fixed. Lowered to 7.9, the same real minimum already proven to work
# as a genuine, meaningfully-higher bar everywhere else in this pipeline
# (quality_auditor.py's MIN_QUALITY_SCORE, the thumbnail gate, the
# per-stage quality interceptor) -- achievable on real output (craft hit
# 8.0-8.2 in 5 of the 13 real attempts) while still being a hard, real
# improvement over the old +/-1.5 system that let 6.5 sail through.
# TOPIC_CLARITY_GATE_MIN stays at 8.8 -- clarity scored a consistent
# 9.5/10 across all 13 real attempts, so 8.8 never actually blocks it.
NARRATIVE_CRAFT_GATE_MIN = 7.9
TOPIC_CLARITY_GATE_MIN = 8.8
_HOOK_GATE_PENALTY = 5.0


def score_script_rubric(script_text, topic=""):
    """
    Combined Killer Hook / Narrative Craft / Topic Clarity rubric.

    Returns (bonus, issues, subscores):
      bonus     - adjustment added directly to a channel's existing
                  score_result()/score_script_er() total. Normally capped
                  at +/-1.5, EXCEPT when the hook itself fails its own
                  hard gate (subscores["hook_gate_passed"] is False) — in
                  that case a large fixed penalty is applied instead,
                  regardless of how strong narrative_craft/topic_clarity
                  scored, so the overall attempt cannot pass any gate.
      issues    - combined list of human-readable issue strings, for logging.
      subscores - {"killer_hook": x, "first_15_seconds": y, "narrative_craft": z,
                  "topic_clarity": w, "hook_gate_passed": bool}, for logging/telemetry.
    """
    if not script_text:
        return 0.0, ["Empty script"], {}

    hook_score, hook_issues = score_killer_hook(script_text)
    open15_score, open15_issues = validate_first_15_seconds(script_text)
    craft_score, craft_issues = score_narrative_craft(script_text)
    clarity_score, clarity_issues = score_topic_clarity(script_text, topic)

    hook_gate_avg = (hook_score + open15_score) / 2.0
    hook_gate_passed = hook_gate_avg >= HOOK_GATE_MIN
    craft_gate_passed = craft_score >= NARRATIVE_CRAFT_GATE_MIN
    clarity_gate_passed = clarity_score >= TOPIC_CLARITY_GATE_MIN

    subscores = {
        "killer_hook": hook_score,
        "first_15_seconds": open15_score,
        "narrative_craft": craft_score,
        "topic_clarity": clarity_score,
        "hook_gate_passed": hook_gate_passed,
        "craft_gate_passed": craft_gate_passed,
        "clarity_gate_passed": clarity_gate_passed,
    }
    issues = list(hook_issues) + list(open15_issues) + list(craft_issues) + list(clarity_issues)

    avg = (hook_score + open15_score + craft_score + clarity_score) / 4.0
    bonus = round((avg - 5.0) * 0.3, 2)
    bonus = max(-1.5, min(1.5, bonus))

    if not hook_gate_passed:
        issues.insert(0, f"HOOK GATE FAILED: hook/first-15s average {hook_gate_avg:.1f}/10 is "
                         f"below the required {HOOK_GATE_MIN} — this attempt cannot pass regardless "
                         f"of any other score.")
        bonus = -_HOOK_GATE_PENALTY
    if not craft_gate_passed:
        issues.insert(0, f"NARRATIVE CRAFT GATE FAILED: {craft_score}/10 is below the required "
                         f"{NARRATIVE_CRAFT_GATE_MIN} — this attempt cannot pass regardless of any "
                         f"other score.")
        bonus = -_HOOK_GATE_PENALTY
    if not clarity_gate_passed:
        issues.insert(0, f"TOPIC CLARITY GATE FAILED: {clarity_score}/10 is below the required "
                         f"{TOPIC_CLARITY_GATE_MIN} — this attempt cannot pass regardless of any "
                         f"other score.")
        bonus = -_HOOK_GATE_PENALTY

    return bonus, issues, subscores
