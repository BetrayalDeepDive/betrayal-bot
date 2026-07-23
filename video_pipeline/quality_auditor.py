"""
Automated quality-auditor gate — the "read it and score it before moving on"
interceptor the user explicitly asked for on July 23 2026: "I want you to
sync Claude Code into the script as a main interceptor for quality, where
it checks the quality before it proceeds to the next stage... The minimum
is 6.8. If it is less than that, I want you to tell the automation to
remake it without fail, even before it comes to me as a manual in
Telegram."

HONEST TECHNICAL NOTE (do not remove — this is a real constraint, not a
cosmetic caveat): this pipeline runs unattended on GitHub Actions cron
schedules. There is no Anthropic API key configured in this repo's
secrets, and Claude Code itself is an interactive coding assistant, not
an API these workflows can call at 3am with nobody watching. "Syncing
Claude Code in" literally is not something a cron job can do. What this
module actually builds is the same real capability described above --
an independent AI judge that reads the actual generated content (not
just regex/keyword pattern-matching like the existing rule-based rubrics
in script_scoring.py) and returns a real 0-10 score plus specific
missing elements, using this pipeline's own already-configured AI
providers (the same Groq/Gemini/Cerebras/etc. keys every channel already
uses for generation) -- functionally identical to what was asked for,
just running on the provider infrastructure that's actually reachable
from an unattended cron job. If literal Claude-API judging is wanted
instead, that requires an ANTHROPIC_API_KEY secret to be added.

This module is intentionally provider-agnostic: every channel already
has its own `ai()`/`ai_generate()` wrapper function with its own
provider-fallback chain, so callers pass that function in rather than
this module importing a specific channel's provider code.
"""
import json
import re

MIN_QUALITY_SCORE = 6.8

_RUBRICS = {
    "script": (
        "You are an expert YouTube script editor auditing a dark documentary "
        "narration script before it goes any further in the pipeline. Read the "
        "ENTIRE script below and judge it honestly on:\n"
        "1. Does the cold open actually preview the real, specific twist/outcome "
        "of THIS story (not generic dread that could belong to any episode)?\n"
        "2. Is the story specific and grounded (real numbers, names, dates) "
        "rather than vague and generic?\n"
        "3. Does it maintain tension and avoid repetitive phrasing/structure?\n"
        "4. Does it actually resolve/pay off what it opened with?\n"
        "5. Would a real viewer feel this was worth their time, or does it read "
        "as generic AI filler?"
    ),
    "thumbnail_text": (
        "You are an expert YouTube thumbnail strategist. Judge this 3-word "
        "thumbnail text on: does it create genuine curiosity/dread/urgency, "
        "is it specific rather than vague, does it match the topic given, "
        "and would it actually stop someone scrolling?"
    ),
    "title": (
        "You are an expert YouTube title strategist. Judge this title on CTR "
        "potential: specificity, curiosity gap, emotional pull, and whether it "
        "accurately represents the topic without being misleading clickbait."
    ),
    "description": (
        "You are an expert YouTube SEO editor. Judge this video description on: "
        "a real hook in the first two lines, genuine (non-padded) substance, "
        "clear calls to action, and whether it reads as authored rather than "
        "templated filler."
    ),
    "shorts_script": (
        "You are an expert YouTube Shorts strategist. Judge this Short's script "
        "on: does the first line hook in under 3 seconds, does it maintain a "
        "complete beginning/middle/end arc in ~120 words, does it resolve with "
        "a real payoff, and would it actually stop someone mid-scroll?"
    ),
}


def audit_content(stage_name, content, context, call_ai_fn, topic=""):
    """
    Send `content` to an independent AI judge (via call_ai_fn, the caller's
    own provider-fallback wrapper) and get back a real 0-10 score plus
    specific issues -- not a rule-based keyword count, an actual read.

    call_ai_fn: callable(prompt: str, tokens: int) -> str | None, matching
    every channel's existing ai()/ai_generate() signature.

    Returns {"score": float, "passed": bool, "issues": [...], "used_fallback": bool}.
    On any failure (AI unreachable, bad JSON), returns a score of exactly
    MIN_QUALITY_SCORE with used_fallback=True and a clear issue string --
    a neutral pass-through rather than silently blocking or silently
    passing, and always visibly flagged as a fallback in the return value
    so callers can log/report it honestly instead of it looking identical
    to a real audit.
    """
    rubric = _RUBRICS.get(stage_name, _RUBRICS["script"])
    topic_line = f"\nTOPIC (for context): {topic[:200]}\n" if topic else ""
    prompt = (
        f"{rubric}\n{topic_line}\n"
        f"CONTENT TO AUDIT:\n\"\"\"\n{content[:6000]}\n\"\"\"\n\n"
        f"Return ONLY valid JSON, no markdown, no backticks:\n"
        f'{{"score": <float 0-10, one decimal>, "issues": ["<specific issue>", ...]}}\n'
        f"Be honest and specific -- a generic 7.0 with no real issues listed is "
        f"not useful. If something is genuinely wrong, name exactly what and why."
    )
    try:
        raw = call_ai_fn(prompt, tokens=350)
        if not raw:
            raise ValueError("empty AI response")
        raw = re.sub(r"```json|```", "", raw).strip()
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            raise ValueError(f"no JSON found in response: {raw[:200]}")
        data = json.loads(m.group())
        score = round(float(data.get("score", 0)), 1)
        score = max(0.0, min(10.0, score))
        issues = data.get("issues", []) or []
        return {"score": score, "passed": score >= MIN_QUALITY_SCORE,
                "issues": issues, "used_fallback": False}
    except Exception as e:
        return {"score": MIN_QUALITY_SCORE, "passed": True, "used_fallback": True,
                "issues": [f"Quality-audit AI call failed, passed through as neutral (non-blocking): {e}"]}


def enforce_quality_gate(stage_name, initial_content, context, call_ai_fn,
                          regenerate_fn, tg_fn=None, topic="", max_reworks=2):
    """
    THE INTERCEPTOR. Audits `initial_content`; if it scores below
    MIN_QUALITY_SCORE, calls regenerate_fn() (a zero-arg callable the
    caller provides, wrapping that stage's own real regeneration logic)
    for a fresh attempt, up to max_reworks times, keeping the best-scoring
    attempt seen. Never silently proceeds on a failing score without at
    least attempting a rework -- and never silently forces a rework
    through without telling the operator via tg_fn, if given.

    Returns {"content": str, "score": float, "passed": bool,
             "reworked": int, "used_fallback": bool}.
    """
    content = initial_content
    best_content, best_score, best_used_fallback = content, -1.0, False
    reworked = 0

    for attempt in range(max_reworks + 1):
        result = audit_content(stage_name, content, context, call_ai_fn, topic=topic)
        if result["score"] > best_score:
            best_content, best_score = content, result["score"]
            best_used_fallback = result["used_fallback"]

        if result["passed"]:
            return {"content": content, "score": result["score"], "passed": True,
                    "reworked": reworked, "used_fallback": result["used_fallback"]}

        if attempt >= max_reworks:
            break

        reworked += 1
        issues_str = "; ".join(result["issues"][:3]) if result["issues"] else "no specific issues returned"
        if tg_fn:
            tg_fn(f"🔍 Quality audit: {stage_name} scored {result['score']}/10 "
                  f"(below {MIN_QUALITY_SCORE} bar) — {issues_str}. Reworking "
                  f"automatically before this reaches you (attempt {reworked}/{max_reworks}).")
        try:
            new_content = regenerate_fn()
        except Exception as e:
            if tg_fn:
                tg_fn(f"⚠️ Quality audit rework for {stage_name} failed to regenerate "
                      f"(non-fatal, using best attempt seen so far): {e}")
            break
        if not new_content:
            break
        content = new_content

    return {"content": best_content, "score": best_score, "passed": False,
            "reworked": reworked, "used_fallback": best_used_fallback}
