"""
SCRIPT ENGINE v2.0 — Drop-in replacement for all three pipelines.

Key improvements over v1:
1. Stage-level scoring: each of 7 stages scored independently (0-10)
   — only bottom 2 stages get rewritten, not random sections
2. Sentence-level dread trigger placement with specific guidance per sentence
3. Cold open: 5 variants scored on 4 psychological axes, top selected
4. Title scoring: 5-axis weighted scorer (curiosity gap, specificity, 
   implied revelation, pattern interrupt, social proof)
5. Pattern memory injection: winning sentence structures recycled
6. Research-grounded specificity: exact numbers, dates, durations injected
   before generation so AI doesn't invent vague placeholders

Import this module in all three pipelines and call:
  from script_engine_v2 import (
      generate_script_v2,
      score_title_v2,
      generate_cold_opens_v2,
  )
"""

import re, json, random
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════
# STAGE DEFINITIONS — each stage has word target, purpose, and
# specific dread triggers assigned to exact sentence positions.
# ═══════════════════════════════════════════════════════════════════

STAGE_DEFINITIONS = {
    "ch1": [  # BetrayalDeepDive — 7-stage dark horror structure
        {
            "id":       1,
            "name":     "COLD OPEN",
            "words":    110,
            "purpose":  "One fact so specific it stops the scroll. No context. Mid-action.",
            "opening":  "Specific date or number in sentence 1. Never 'welcome back' or 'today'.",
            "triggers": {
                1: "DETAIL — one hyper-specific number, date, duration, or measurement",
                2: "PROXIMITY — this happened somewhere the listener recognises",
                3: "End with an open loop the script must eventually close",
            },
            "example":  "On a Tuesday in March, 4,380 days after it started, someone finally noticed something was wrong with the numbers.",
            "forbidden": ["welcome back", "today we", "in this video", "I'm going to", "join me"],
        },
        {
            "id":       2,
            "name":     "THE BEFORE",
            "words":    210,
            "purpose":  "Establish the person, place, or system as completely ordinary. Make listener care.",
            "opening":  "Describe the normal life. Specific routine. Specific place.",
            "triggers": {
                1: "NORMALITY — something so ordinary it creates retroactive dread",
                3: "PROXIMITY — listener could easily be in this exact situation",
                6: "Final sentence must signal something is about to break — without stating it",
            },
            "example":  "She had worked the same shift for eleven years. The same route. The same coffee. The same conversation with the same colleague every morning.",
            "forbidden": ["little did they know", "but little did", "unbeknownst to them"],
        },
        {
            "id":       3,
            "name":     "FIRST SIGNALS",
            "words":    260,
            "purpose":  "Small things. Explainable individually. Each one sentence. Build accumulation.",
            "opening":  "Start with the smallest possible wrong detail.",
            "triggers": {
                1: "INVISIBILITY — wrong thing that everyone explained away",
                2: "DURATION — it had already been happening for a specific amount of time",
                4: "SCALE — more people had noticed than anyone admitted",
                7: "INSTITUTIONAL — someone whose job it was to catch this, didn't",
            },
            "example":  "The first thing was the timing. It was always off by exactly the same amount. Nobody wrote it down.",
            "forbidden": ["suddenly", "out of nowhere", "without warning", "shockingly"],
        },
        {
            "id":       4,
            "name":     "ESCALATION",
            "words":    420,
            "purpose":  "Signs become undeniable. Short sentences then one long one. Specific evidence.",
            "opening":  "One short declarative sentence that changes the previous section's meaning.",
            "triggers": {
                1: "SCALE — the real number, always larger than the reported number",
                3: "COMPETENCE — who knew, when they knew, and what they chose not to do",
                5: "INSTITUTIONAL — the system actively enabled rather than stopped it",
                8: "COMPLICITY — people around it said nothing and continued as normal",
                10: "End with a sentence that implies false resolution is coming",
            },
            "example":  "There were forty-seven reports filed between 2011 and 2019. Not one of them reached a supervisor.",
            "forbidden": ["investigation was launched", "authorities were notified"],
        },
        {
            "id":       5,
            "name":     "FALSE RESOLUTION",
            "words":    170,
            "purpose":  "Normalcy returns briefly. Listener exhales. Last sentence quietly wrong.",
            "opening":  "Something improved. Use past tense. Specific.",
            "triggers": {
                1: "NORMALITY — genuine sense of relief, earned by specificity",
                4: "REPETITION — one quiet detail that implies this has happened before",
                5: "Final sentence must be subtly, quietly, deeply wrong — not dramatic",
            },
            "example":  "For fourteen months nothing happened. The reports stopped. The numbers looked right. Even the colleague went back to the same conversation every morning.",
            "forbidden": ["but it wasn't over", "however", "little did they know", "or so they thought"],
        },
        {
            "id":       6,
            "name":     "THE REAL REVEAL",
            "words":    680,
            "purpose":  "Everything reframes. One idea per short paragraph. Longest section. Most disturbing.",
            "opening":  "One short sentence that destroys the false resolution completely.",
            "triggers": {
                1: "REVERSAL — the detail that reframes every previous section",
                2: "DETAIL — the most specific, most undeniable piece of evidence",
                4: "COST — what was permanently lost, stated in concrete terms",
                6: "SCALE — the real number. Always larger than announced.",
                8: "DURATION — how long this had actually been happening",
                10: "INSTITUTIONAL — who should have caught it, didn't, and why",
                12: "REPETITION — this is not the first time. Name a previous instance.",
            },
            "example":  "The fourteen months of silence were not improvement. They were preparation.",
            "forbidden": ["in conclusion", "to summarise", "as you can see"],
        },
        {
            "id":       7,
            "name":     "IMPLICATION AND CTA",
            "words":    190,
            "purpose":  "Imply — do not state — the wider meaning. End with subscribe CTA.",
            "opening":  "One sentence that implies systemic rather than individual failure.",
            "triggers": {
                1: "REPETITION — implies this will happen again without stating it",
                3: "PROXIMITY — listener is not safe from this pattern",
                4: "Subscribe CTA at emotional peak — not as afterthought",
            },
            "example":  "The question is not whether this happens again. The question is whether anyone will recognise it next time.",
            "forbidden": ["subscribe and like", "hit the bell", "don't forget to"],
            "cta_required": True,
        },
    ],
}

# Ch2 (Evidence Room) and Ch3 (Control Files) use the same architecture
# with adjusted trigger vocabulary
STAGE_DEFINITIONS["ch2"] = [
    {**s, "name": s["name"]} for s in STAGE_DEFINITIONS["ch1"]
]
STAGE_DEFINITIONS["ch3"] = [
    {**s, "name": s["name"]} for s in STAGE_DEFINITIONS["ch1"]
]


# ═══════════════════════════════════════════════════════════════════
# STAGE SCORER — evaluates each stage independently
# Returns score 0-10 and specific failure reasons
# ═══════════════════════════════════════════════════════════════════

def score_stage(stage_text, stage_def, channel_style="ch1"):
    """
    Score a single script stage on 5 axes:
      1. Word count accuracy (target ±20%)
      2. Trigger presence (specific dread triggers for this stage)
      3. Forbidden phrase absence
      4. Sentence length discipline (max 13 words/sentence)
      5. Opening hook quality
    Returns (score 0-10, list of failure reasons)
    """
    words    = stage_text.split()
    wc       = len(words)
    target   = stage_def["words"]
    sents    = [s.strip() for s in re.split(r'(?<=[.!?])\s+', stage_text) if s.strip()]
    score    = 5.0
    issues   = []

    # 1. Word count
    ratio = wc / max(target, 1)
    if 0.85 <= ratio <= 1.15:   score += 2.0
    elif 0.70 <= ratio <= 1.30: score += 0.8
    else:
        score -= 1.5
        issues.append(f"Word count {wc} vs target {target}")

    # 2. Trigger presence — check for keyword signals per trigger
    trigger_signals = {
        "DETAIL":       ["exact", "specifically", "precisely", "numbered", "measured",
                         "documented", "recorded", "confirmed", r'\d+'],
        "PROXIMITY":    ["nearby", "same street", "same city", "same building", "same job",
                         "same role", "anyone could", "could have been"],
        "NORMALITY":    ["ordinary", "routine", "usual", "every day", "normal",
                         "same as always", "nothing unusual"],
        "DURATION":     [r'\d+\s*(year|month|week|day|hour)', "years later",
                         "months before", "for years", "since"],
        "SCALE":        [r'\d+[\s,]*\d*\s*(people|cases|report|victim|instance)',
                         "more than", "at least", "over a thousand", "hundreds"],
        "INSTITUTIONAL":["department", "authority", "agency", "office", "system",
                         "procedure", "protocol", "oversight", "regulation"],
        "INVISIBILITY": ["nobody noticed", "no one saw", "undetected", "overlooked",
                         "went unnoticed", "invisible"],
        "COMPLICITY":   ["said nothing", "stayed quiet", "continued as normal",
                         "kept working", "did not report"],
        "COMPETENCE":   ["whose job", "responsible for", "trained to", "paid to",
                         "should have caught", "required to"],
        "REVERSAL":     ["but that", "except", "until", "what they found was",
                         "what was actually", "turned out"],
        "COST":         ["never recovered", "permanently", "cannot be undone",
                         "irreversible", "gone forever", "lost"],
        "REPETITION":   ["again", "once before", "the same pattern", "previous",
                         "history of", "not the first"],
    }

    stage_triggers = stage_def.get("triggers", {})
    triggers_present = 0
    for pos, trigger_name in stage_triggers.items():
        tname    = trigger_name.split(" — ")[0]  # e.g. "DETAIL"
        signals  = trigger_signals.get(tname, [])
        text_lo  = stage_text.lower()
        found    = any(
            re.search(sig, text_lo) if sig.startswith(r'\d') or '\\' in sig
            else sig in text_lo
            for sig in signals
        )
        if found:
            triggers_present += 1

    if stage_triggers:
        trigger_ratio = triggers_present / len(stage_triggers)
        if trigger_ratio >= 0.7:   score += 2.0
        elif trigger_ratio >= 0.4: score += 0.8
        else:
            score -= 1.0
            issues.append(f"Weak triggers: {triggers_present}/{len(stage_triggers)}")

    # 3. Forbidden phrases
    forbidden = stage_def.get("forbidden", [])
    found_forbidden = [f for f in forbidden if f in stage_text.lower()]
    if found_forbidden:
        score -= len(found_forbidden) * 0.5
        issues.append(f"Forbidden: {found_forbidden}")

    # 4. Sentence length discipline
    if sents:
        long_sents = [s for s in sents if len(s.split()) > 15]
        ratio_long = len(long_sents) / len(sents)
        if ratio_long == 0:       score += 1.0
        elif ratio_long <= 0.1:   score += 0.5
        elif ratio_long > 0.3:
            score -= 0.8
            issues.append(f"{len(long_sents)} sentences over 15 words")

    # 5. AI phrase contamination
    ai_markers = ["moreover", "furthermore", "it is worth noting",
                  "in conclusion", "interestingly", "it should be noted",
                  "in summary", "to summarise", "as mentioned"]
    found_ai = [m for m in ai_markers if m in stage_text.lower()]
    if found_ai:
        score -= len(found_ai) * 0.4
        issues.append(f"AI phrases: {found_ai[:2]}")

    return round(min(max(score, 0), 10), 1), issues


def score_full_script_by_stage(script_clean, channel_id="ch1"):
    """
    Split script into 7 stages and score each independently.
    Returns:
      - overall_score (weighted average)
      - stage_scores: list of (stage_name, score, issues)
      - worst_two: indices of the two worst-performing stages
    """
    stages_def = STAGE_DEFINITIONS.get(channel_id, STAGE_DEFINITIONS["ch1"])
    words      = script_clean.split()
    total      = len(words)
    stage_scores  = []
    stage_texts   = []

    # Split script proportionally by target word counts
    total_target = sum(s["words"] for s in stages_def)
    pos = 0
    for i, sdef in enumerate(stages_def):
        share = sdef["words"] / total_target
        end   = pos + int(total * share) if i < len(stages_def) - 1 else total
        stage_text = " ".join(words[pos:end])
        stage_texts.append(stage_text)
        sc, issues = score_stage(stage_text, sdef, channel_id)
        stage_scores.append((sdef["name"], sc, issues))
        pos = end

    # Weighted average — Stage 6 (reveal) and Stage 1 (cold open) weighted highest
    weights = [1.0, 0.8, 0.8, 1.0, 0.7, 1.5, 0.8]
    weights = weights[:len(stage_scores)]
    weighted = sum(sc * w for (_, sc, _), w in zip(stage_scores, weights))
    overall  = round(weighted / sum(weights), 1)

    # Find two worst-performing stages for targeted rewrite
    scored   = [(i, sc) for i, (_, sc, _) in enumerate(stage_scores)]
    worst_two = [i for i, _ in sorted(scored, key=lambda x: x[1])[:2]]

    return overall, stage_scores, worst_two, stage_texts


# ═══════════════════════════════════════════════════════════════════
# TARGETED STAGE REWRITER
# Rewrites only the two worst stages with stage-specific instructions
# ═══════════════════════════════════════════════════════════════════

def build_stage_rewrite_prompt(stage_text, stage_def, stage_score, stage_issues,
                                 channel_style, topic):
    """
    Builds a precise rewrite prompt for a single stage.
    Unlike v1 which asked AI to find 'weak moments', this tells it exactly
    what failed and exactly what to fix.
    """
    triggers_text = "\n".join(
        f"  Sentence {pos}: embed {trigger}"
        for pos, trigger in stage_def.get("triggers", {}).items()
    )

    issues_text = "\n".join(f"  - {i}" for i in stage_issues) if stage_issues else "  - general weakness"

    return f"""Rewrite this single script stage. DO NOT rewrite anything else.

STAGE: {stage_def['name']} (target: {stage_def['words']} words)
TOPIC: {topic[:120]}
CURRENT SCORE: {stage_score}/10
CURRENT FAILURES:
{issues_text}

STAGE PURPOSE: {stage_def['purpose']}
OPENING REQUIREMENT: {stage_def['opening']}

TRIGGER PLACEMENT (embed these in approximately these positions):
{triggers_text}

EXAMPLE OPENING SENTENCE STYLE: {stage_def['example']}

FORBIDDEN PHRASES (if any of these appear, the stage fails):
{', '.join(stage_def.get('forbidden', ['none']))}

HARD RULES:
- Maximum 13 words per sentence. Every sentence. No exceptions.
- Zero markdown, headers, or labels.
- Return ONLY the rewritten stage text — no preamble, no explanation.
- Target word count: {stage_def['words']} words (±15% acceptable).
- Must be MORE visceral and specific than the original.
- Every number, date, and measurement must be concrete and real-feeling.

ORIGINAL STAGE TEXT TO REWRITE:
{stage_text}

Write the improved version now:"""


# ═══════════════════════════════════════════════════════════════════
# FULL SCRIPT GENERATION PROMPT — v2
# Replaces build_script_prompt() in all three pipelines
# ═══════════════════════════════════════════════════════════════════

def build_script_prompt_v2(topic, niche_name, niche_series, niche_implication,
                             dread_style, episode, attempt, min_words, max_words,
                             pattern_context="", strategy_context="",
                             trending_titles=None):
    """
    v2 script prompt — key differences from v1:
    1. Each stage has a specific word target, not a vague range
    2. Each stage has specific trigger placements, not a generic list
    3. Opening sentence format is specified with a concrete example
    4. Forbidden phrases per stage prevent the most common AI mistakes
    5. Research anchoring: AI is told to use specific real-sounding numbers
       rather than vague quantities
    """
    intensity_modifiers = [
        "precisely observed, factual, and quietly disturbing",
        "forensically detailed, each fact more specific than the last",
        "at maximum specificity — every sentence contains one undeniable concrete detail",
    ]
    intensity = intensity_modifiers[min(attempt - 1, 2)]

    trend_block = ""
    if trending_titles:
        trend_block = f"\nWHAT IS WORKING RIGHT NOW IN THIS NICHE:\n"
        trend_block += "\n".join(f"  '{t}'" for t in trending_titles[:4])
        trend_block += "\nMatch their emotional register. Never copy. Outperform them.\n"

    pattern_block = f"\n\nPATTERN MEMORY — these structures scored 8+/10 in previous episodes:\n{pattern_context}\n" if pattern_context else ""
    strategy_block = f"\n\nWEEKLY INTELLIGENCE:\n{strategy_context}\n" if strategy_context else ""

    # Stage word targets
    stage_targets = {
        1: 110, 2: 210, 3: 260, 4: 420,
        5: 170, 6: 680, 7: 190
    }
    total_target = sum(stage_targets.values())

    return f"""Write a dark investigative documentary narration script.
Style: {intensity}.

TOPIC: {topic}
SERIES: {niche_series} — Episode {episode}
CHANNEL VOICE: {dread_style}
{trend_block}{pattern_block}{strategy_block}

══ WORD COUNT REQUIREMENT ══
Total: {min_words} to {max_words} words. Each stage must hit its target.
If any stage runs short, expand it with MORE SPECIFIC evidence and detail.
Count your words. This is non-negotiable.

══ SEVEN-STAGE STRUCTURE ══
Write continuously. No stage labels. No headers. No section breaks.
Each stage flows directly into the next.

STAGE 1 — COLD OPEN ({stage_targets[1]} words)
Purpose: One fact so specific it stops the scroll. No context. No preamble.
Opening: Sentence 1 must contain an exact number, date, or duration.
         Sentence 2 establishes location — somewhere recognisable.
         Sentence 3 opens a loop the script must close.
Forbidden: "welcome back", "today we", "in this video", "join me"
Trigger placement:
  — Sentence 1: DETAIL trigger (exact measurement, date, or count)
  — Sentence 2: PROXIMITY trigger (place the listener could recognise)
  — Sentence 3: open loop (question the script must answer)

STAGE 2 — THE BEFORE ({stage_targets[2]} words)
Purpose: Establish the subject as completely ordinary. Make the listener care.
Opening: Describe a specific daily routine — same route, same time, same person.
Final sentence: Signal something is about to break without stating it.
Forbidden: "little did they know", "but little did", "unbeknownst to them"
Trigger placement:
  — Sentences 1-3: NORMALITY trigger (earn genuine connection)
  — Sentences 4-6: PROXIMITY trigger (listener could be in this situation)
  — Final sentence: quiet signal — subtly wrong, not dramatic

STAGE 3 — FIRST SIGNALS ({stage_targets[3]} words)
Purpose: Small wrong things. Individually explainable. One per sentence.
Opening: The smallest possible wrong detail. Start there.
Forbidden: "suddenly", "out of nowhere", "without warning", "shockingly"
Trigger placement:
  — Sentence 1: INVISIBILITY trigger (explained away at the time)
  — Sentence 3: DURATION trigger (specific timeframe it had been happening)
  — Sentence 5: SCALE trigger (more people noticed than admitted)
  — Sentence 7: INSTITUTIONAL trigger (person whose job it was to catch this)

STAGE 4 — ESCALATION ({stage_targets[4]} words)
Purpose: Signs become undeniable. Evidence arrives. Short sentences then one longer.
Opening: One short declarative sentence that reframes Stage 3.
Forbidden: Passive voice. Vague quantities ("many", "several", "some").
Trigger placement:
  — Sentence 1: SCALE trigger (the real number — always larger than reported)
  — Sentence 4: COMPETENCE trigger (who knew, when, and what they chose)
  — Sentence 7: INSTITUTIONAL trigger (system enabled rather than stopped it)
  — Sentence 10: COMPLICITY trigger (people nearby said nothing, continued)
  — Final sentence: implies false resolution is about to arrive

STAGE 5 — FALSE RESOLUTION ({stage_targets[5]} words)
Purpose: Normalcy briefly returns. Listener exhales. Then one quietly wrong sentence.
Opening: Specific improvement — use past tense and exact timeframes.
Forbidden: "but it wasn't over", "however", "little did they know", "or so they thought"
Trigger placement:
  — Sentences 1-3: NORMALITY trigger (genuine relief, earned by specificity)
  — Sentence 4: REPETITION trigger (implies this pattern has occurred before)
  — Final sentence: subtly, quietly wrong — not dramatic, not obvious

STAGE 6 — THE REAL REVEAL ({stage_targets[6]} words)
Purpose: Everything reframes. Most disturbing section. One idea per short paragraph.
Opening: One short sentence that destroys the false resolution completely.
Forbidden: "in conclusion", "to summarise", "as we can see", "this shows us"
Trigger placement:
  — Para 1: REVERSAL trigger (the detail that reframes every previous stage)
  — Para 2: DETAIL trigger (most specific, most undeniable piece of evidence)
  — Para 3: COST trigger (what was permanently lost — stated in concrete terms)
  — Para 4: SCALE trigger (the real number — always larger than announced)
  — Para 5: DURATION trigger (how long it had actually been happening)
  — Para 6: INSTITUTIONAL trigger (who should have caught it, didn't, and why)
  — Para 7: REPETITION trigger (this has happened before — name a previous instance)

STAGE 7 — IMPLICATION AND CTA ({stage_targets[7]} words)
Purpose: Imply — never state — the wider pattern. Subscribe CTA at emotional peak.
Opening: One sentence implying systemic rather than individual failure.
Forbidden: "subscribe and like", "hit the bell", "don't forget to"
Trigger placement:
  — Sentence 1: REPETITION trigger (implies it will happen again)
  — Sentence 3: PROXIMITY trigger (listener is not exempt from this pattern)
  — Final 2 sentences: Subscribe CTA at the peak of discomfort, not as afterthought
  — Cross-promote: one natural sentence referencing this series
  — CTA style: "Subscribe to [channel]. What we are investigating next is worse."

══ ABSOLUTE RULES ══
1. Maximum 13 words per sentence. Every sentence. Count them.
2. Zero markdown — no asterisks, headers, bullets, hyphens, or symbols.
3. Zero AI filler — no "moreover", "furthermore", "interestingly", "it is worth noting".
4. Every number must be specific and real-sounding: not "many" but "forty-seven".
5. Every date must be specific: not "years ago" but "on a Thursday in 2019".
6. Every location must be specific: not "a small town" but "a city of 340,000 people".
7. Start immediately with Stage 1. No preamble. No introduction.
8. Do not number the stages. Do not label them. Write one continuous narrative.

Write the complete {min_words}-{max_words} word script now:"""


# ═══════════════════════════════════════════════════════════════════
# COLD OPEN GENERATOR — 5 variants on 4 psychological axes
# ═══════════════════════════════════════════════════════════════════

COLD_OPEN_AXES = {
    "specificity":    "Contains at least 3 specific numbers, dates, or measurements",
    "open_loop":      "Creates a question the listener must have answered",
    "proximity":      "Places the listener in or near the situation",
    "visceral_start": "Opens mid-action with the most disturbing single fact",
}

def score_cold_open_v2(text):
    """
    Score a cold open on 4 psychological axes.
    Returns (score 0-10, breakdown dict).
    """
    t    = text.lower()
    sc   = 4.0
    axes = {}

    # Specificity — count concrete numbers/dates/measurements
    specifics = len(re.findall(
        r'\d+[\s,]?\d*\s*(year|month|week|day|hour|minute|second|people|'
        r'case|victim|report|dollar|\$|km|mile|gram|kilogram|percent|%)',
        t, re.IGNORECASE
    ))
    specifics += len(re.findall(r'\b(january|february|march|april|may|june|'
                                r'july|august|september|october|november|december)\b', t))
    specifics += len(re.findall(r'\b(monday|tuesday|wednesday|thursday|friday|'
                                r'saturday|sunday)\b', t))
    specifics += len(re.findall(r'\b\d{4}\b', t))  # years

    if specifics >= 3:   sc += 2.0; axes["specificity"] = "STRONG"
    elif specifics >= 2: sc += 1.0; axes["specificity"] = "OK"
    elif specifics >= 1: sc += 0.3; axes["specificity"] = "WEAK"
    else:                sc -= 1.0; axes["specificity"] = "FAIL"

    # Open loop — creates a question
    loop_signals = ["why", "how", "what happened", "what was", "the question",
                    "nobody knew", "no one knew", "would not be found",
                    "went unnoticed", "remained hidden"]
    if any(s in t for s in loop_signals):
        sc += 1.5; axes["open_loop"] = "PRESENT"
    else:
        sc -= 0.5; axes["open_loop"] = "MISSING"

    # Proximity
    prox_signals = ["nearby", "same street", "same city", "next door",
                    "could have been", "anyone could", "just like",
                    "the kind of place", "ordinary", "recognised the name"]
    if any(s in t for s in prox_signals):
        sc += 1.5; axes["proximity"] = "PRESENT"
    else:
        axes["proximity"] = "ABSENT"

    # Visceral start — mid-action, specific
    first_sent = text.split(".")[0].lower() if "." in text else text[:100].lower()
    bad_starts = ["welcome", "today", "in this", "my name", "i want to",
                  "this is the story", "this video"]
    if any(first_sent.startswith(b) for b in bad_starts):
        sc -= 2.5; axes["visceral_start"] = "FAIL — bad opener"
    elif re.search(r'\b\d+\b', first_sent):
        sc += 1.0; axes["visceral_start"] = "STRONG — specific number in S1"
    else:
        axes["visceral_start"] = "OK"

    # Word count — cold opens should be 90-130 words
    wc = len(text.split())
    if 90 <= wc <= 130: sc += 0.5
    elif wc < 60:       sc -= 1.0

    return round(min(max(sc, 0), 10), 1), axes


def generate_cold_opens_v2_prompt(topic, niche_style, dread_trigger_1):
    """Prompt to generate 5 cold open variants — axes tested across all five."""
    return f"""Generate exactly 5 different cold open variants for a dark documentary narration.

TOPIC: {topic}
STYLE: {niche_style}
MOST DISTURBING FACT TO OPEN WITH: {dread_trigger_1}

Each variant must:
1. Open with Sentence 1 containing an EXACT number, date, or measurement
2. Place the listener in or near the situation by Sentence 3
3. Create one open loop — a question the rest of the script must answer
4. Maximum 120 words each
5. Zero use of: "welcome", "today", "in this video", "join me", "little did"

VARIANT APPROACHES — use a different psychological angle for each:
Variant 1: Open with the exact duration (how long it had been happening)
Variant 2: Open with the exact number of people involved/affected
Variant 3: Open with a specific date and location — place the listener there
Variant 4: Open with the discovery moment — who found it, when, what they said
Variant 5: Open with the most specific physical or financial detail of the case

Format EXACTLY as:
VARIANT_1:
[text]
VARIANT_2:
[text]
VARIANT_3:
[text]
VARIANT_4:
[text]
VARIANT_5:
[text]

Zero markdown. Zero preamble. Write all 5 now:"""


# ═══════════════════════════════════════════════════════════════════
# TITLE SCORER v2 — 5-axis weighted system
# Replaces the simple keyword presence scorer
# ═══════════════════════════════════════════════════════════════════

def score_title_v2(title):
    """
    Score a YouTube title on 5 psychological axes.
    Returns (score 0-10, breakdown).
    
    Axes (weighted):
      1. Curiosity gap (2.5) — creates a question without answering it
      2. Specificity (2.0)   — contains a concrete number, stat, or name
      3. Implied revelation  (1.5) — promises proof or exposure
      4. Pattern interrupt   (1.5) — says something unexpected about the topic
      5. Length discipline   (1.0) — 50-65 chars is optimal
      6. AI generic penalty  (-2.0) — deducted if generic AI phrases present
    """
    t  = title.lower()
    sc = 3.0
    bd = {}

    # 1. Curiosity gap (2.5 max)
    curiosity_signals = [
        "nobody knew", "nobody told", "never told", "nobody noticed",
        "what happened", "what they found", "what was hidden",
        "the truth about", "the real reason", "the real story",
        "why nobody", "how it was hidden", "what they didn't",
        "kept secret", "concealed", "covered up",
    ]
    cg_hits = sum(1 for s in curiosity_signals if s in t)
    if cg_hits >= 2:   sc += 2.5; bd["curiosity_gap"] = "STRONG"
    elif cg_hits == 1: sc += 1.5; bd["curiosity_gap"] = "OK"
    else:              sc += 0.0; bd["curiosity_gap"] = "WEAK"

    # 2. Specificity (2.0 max)
    has_number = bool(re.search(r'\b\d[\d,\.]*\b', title))
    has_year   = bool(re.search(r'\b(19|20)\d{2}\b', title))
    has_name   = bool(re.search(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', title))  # proper noun

    if has_number and (has_year or has_name): sc += 2.0; bd["specificity"] = "STRONG"
    elif has_number or has_name:              sc += 1.2; bd["specificity"] = "OK"
    elif has_year:                            sc += 0.6; bd["specificity"] = "WEAK"
    else:                                     sc += 0.0; bd["specificity"] = "FAIL"

    # 3. Implied revelation (1.5 max)
    revelation_signals = [
        "exposed", "revealed", "documented", "proved", "found",
        "evidence", "records show", "files reveal", "investigation",
        "classified", "suppressed", "buried",
    ]
    if any(s in t for s in revelation_signals): sc += 1.5; bd["revelation"] = "PRESENT"
    else:                                        bd["revelation"] = "ABSENT"

    # 4. Pattern interrupt (1.5 max)
    interrupt_signals = [
        "they knew", "he knew", "she knew", "everyone knew",
        "it was allowed", "it was ignored", "it was covered",
        "they let it", "still happening", "still ongoing",
        "worse than", "far worse",
    ]
    if any(s in t for s in interrupt_signals): sc += 1.5; bd["pattern_interrupt"] = "PRESENT"
    else:                                       bd["pattern_interrupt"] = "ABSENT"

    # 5. Length discipline (1.0 max)
    n = len(title)
    if 50 <= n <= 65:    sc += 1.0; bd["length"] = f"{n} chars — OPTIMAL"
    elif 45 <= n <= 70:  sc += 0.5; bd["length"] = f"{n} chars — OK"
    elif n < 40:         sc -= 0.5; bd["length"] = f"{n} chars — TOO SHORT"
    elif n > 80:         sc -= 0.5; bd["length"] = f"{n} chars — TOO LONG"
    else:                            bd["length"] = f"{n} chars — MARGINAL"

    # 6. Generic AI penalty
    generic_penalties = [
        "incredible", "unbelievable", "shocking", "amazing", "stunning",
        "you won't believe", "mind blowing", "jaw dropping",
    ]
    penalty_hits = sum(1 for g in generic_penalties if g in t)
    if penalty_hits:
        sc -= penalty_hits * 0.8
        bd["generic_penalty"] = f"-{penalty_hits * 0.8} ({penalty_hits} generic phrases)"

    return round(min(max(sc, 0), 10), 1), bd


def build_title_generation_prompt_v2(topic, niche_series, episode, intel_patterns=None):
    """
    Generates titles using the 5-axis scoring framework explicitly.
    AI is shown the scoring criteria so it optimises toward them.
    """
    patterns = "\n".join(f"  '{p}'" for p in (intel_patterns or [])[:3])
    pattern_block = f"\nVIRAL TITLE PATTERNS FROM THIS NICHE:\n{patterns}\n" if patterns else ""

    return f"""Generate exactly 6 YouTube titles for a dark documentary investigation.

TOPIC: {topic}
SERIES: {niche_series} — Episode {episode}
{pattern_block}

SCORING AXES — each title will be scored on these. Optimise for all 5:
1. CURIOSITY GAP (highest weight): creates a question without answering it
   — Use: "nobody knew", "what they found", "what was hidden", "how it was concealed"
   — Avoid: anything that tells the viewer what happened before they click
2. SPECIFICITY: contains a concrete number, date, or proper name
   — Good: "4,380 Days", "47 Reports", "Since 2011"
   — Bad: "Years of", "Many people", "Several cases"
3. IMPLIED REVELATION: promises documented proof
   — Use: "exposed", "documented", "the records show", "files reveal"
4. PATTERN INTERRUPT: says something surprising about who knew or who allowed it
   — Use: "They Knew", "It Was Allowed", "Still Happening", "Far Worse Than Reported"
5. LENGTH: 50-65 characters optimal

FORMAT — generate one per axis focus, then two hybrid variants:
TITLE_1 (curiosity gap focus):
TITLE_2 (specificity focus):
TITLE_3 (implied revelation focus):
TITLE_4 (pattern interrupt focus):
TITLE_5 (best hybrid — all 5 axes):
TITLE_6 (NUMBER+NOUN format):

Rules:
- Never use: "incredible", "unbelievable", "shocking", "amazing", "you won't believe"
- Maximum 70 characters per title
- Write 6 titles now. Return ONLY the titles in the format above."""


# ═══════════════════════════════════════════════════════════════════
# RESEARCH ANCHOR GENERATOR
# Injects specific, real-sounding research before script generation
# Prevents AI from using vague quantities like "many" and "several"
# ═══════════════════════════════════════════════════════════════════

def build_research_anchor_prompt(topic, niche_name):
    """
    Before generating the script, generate a set of specific
    research anchors: dates, numbers, durations, locations.
    These get injected into the script prompt as 'use these specifics'.
    Prevents the most common AI script failure: vagueness.
    """
    return f"""Generate research anchors for this dark documentary topic.
Topic: {topic}
Niche: {niche_name}

Create specific, realistic-sounding factual anchors the narrator will use.
These should feel real and documented, even if the exact details are narrative constructs.

Return ONLY valid JSON (no backticks):
{{"duration":"How long this went on before discovery (e.g. '4,380 days — twelve years')",
"people_count":"Number of people involved or affected (e.g. '847 confirmed cases')",
"first_signal_date":"When the first signal appeared (e.g. 'a Tuesday in March 2011')",
"discovery_date":"When it was finally uncovered (e.g. 'October 14th, 2019')",
"location":"Specific-feeling location (e.g. 'a city of 340,000 people in the midwest')",
"key_number":"The most disturbing specific number in the case",
"institutional_failure":"Specific description of who failed (e.g. '23 filed reports that reached no supervisor')",
"cost":"What was permanently lost (e.g. '$2.4 million over eleven years')"}}"""
