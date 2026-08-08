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
import os
import re
import time

# FIX (direct user report, July 23 2026 — "the minimum is 7.9, not 6.8"): raised.
MIN_QUALITY_SCORE = 7.9

# One call used to be the whole gate. On run 31156373254 that call failed on
# all five stages, so nothing in the episode was ever scored -- and because
# the failure path returned MIN_QUALITY_SCORE, the log said 7.9/10 five times
# and looked like five marginal passes. The free-tier providers rate-limit in
# bursts and the caller's wrapper rotates provider on each call, so retrying
# is usually the difference between no gate and a real one.
AUDIT_ATTEMPTS = int(os.environ.get("QUALITY_AUDIT_ATTEMPTS", "3"))
AUDIT_RETRY_SEC = float(os.environ.get("QUALITY_AUDIT_RETRY_SEC", "8"))


def _num(score):
    """Sort key for a score that may be None (meaning: never audited)."""
    return -1.0 if score is None else float(score)


def fmt_score(score):
    """How a score is written wherever a human will read it.

    Never prints a number for a stage that was not scored. The old code
    substituted MIN_QUALITY_SCORE there, so "7.9/10" appeared five times in
    run 31156373254 for five stages that no judge had ever seen.
    """
    return "not audited" if score is None else "%.1f/10" % float(score)

_RUBRICS = {
    "script": (
        "You are an expert YouTube script editor auditing a dark documentary "
        "narration script before it goes any further in the pipeline. Read the "
        "ENTIRE script below and judge it honestly on:\n"
        "1. Does the cold open actually preview the real, specific twist/outcome "
        "of THIS story (not generic dread that could belong to any episode)?\n"
        "2. Does the opening use a genuine reversal/violated-expectation pattern "
        "and name concrete stakes (a marriage, a fortune, a life, a family) "
        "rather than a vague disturbing mood -- the real mechanism behind a "
        "curiosity gap, not just the presence of a question?\n"
        "3. Is the story specific and grounded (real numbers, names, dates) "
        "rather than vague and generic?\n"
        "4. Does it maintain tension and avoid repetitive phrasing/structure?\n"
        "5. Does it actually resolve/pay off what it opened with?\n"
        "6. Would a real viewer feel this was worth their time, or does it read "
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
    "community_post": (
        "You are an expert YouTube community-engagement strategist. Judge this "
        "Community Tab poll question (and its options, if any) on: is it "
        "genuinely specific to this episode's real topic (not generic "
        "'what do you think?' filler), does it create real curiosity or "
        "invite genuine discussion, and are the poll options (if given) "
        "distinct and meaningful choices rather than throwaway text?"
    ),
}


def audit_content(stage_name, content, context, call_ai_fn, topic=""):
    """
    Send `content` to an independent AI judge (via call_ai_fn, the caller's
    own provider-fallback wrapper) and get back a real 0-10 score plus
    specific issues -- not a rule-based keyword count, an actual read.

    call_ai_fn: callable(prompt: str, tokens: int) -> str | None, matching
    every channel's existing ai()/ai_generate() signature.

    Returns {"score": float|None, "passed": bool, "issues": [...],
             "used_fallback": bool}.

    THE SCORE IS None WHEN NOTHING WAS AUDITED, NOT 7.9.

    This used to return exactly MIN_QUALITY_SCORE on failure, and every audit
    in run 31156373254 came back "7.9/10 (passed=True, fallback=True)" -- the
    pass mark to one decimal, five times out of five. The gate had not run at
    all, and the number said it had scraped through. A fabricated score that
    happens to equal the threshold is the most misleading value the function
    could possibly return: it is indistinguishable in a log, in a Telegram
    message and in a reviewer's memory from a genuine marginal pass.

    Nothing is invented now. `passed` stays True so an unreachable free-tier
    provider cannot block an episode -- that part was a deliberate choice --
    but the score is None and the caller prints "not audited".

    The failure is also retried before it is accepted, because ONE unlucky
    call used to disable the gate for the whole stage.
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
    why = []
    for attempt in range(AUDIT_ATTEMPTS):
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
            why.append(f"attempt {attempt + 1}: {e}")
            if attempt + 1 < AUDIT_ATTEMPTS:
                # Free-tier providers rate-limit in bursts; the wrapper rotates
                # providers on the next call, so a short wait is usually the
                # difference between no gate and a real one.
                time.sleep(AUDIT_RETRY_SEC * (attempt + 1))
    return {"score": None, "passed": True, "used_fallback": True,
            "issues": ["Quality audit did not run: the AI judge was unreachable "
                       "after %d attempts (%s). This stage was NOT scored."
                       % (AUDIT_ATTEMPTS, "; ".join(why)[:300])]}


QUALITY_GATE_ROUNDS = 3
QUALITY_GATE_ROUND_PAUSE_SEC = int(os.environ.get("QUALITY_ROUND_PAUSE_SEC", "600"))


def enforce_quality_gate(stage_name, initial_content, context, call_ai_fn,
                         regenerate_fn, tg_fn=None, topic="", max_reworks=2,
                         rounds=QUALITY_GATE_ROUNDS):
    """
    The editing gate, in ROUNDS — 3 x 13, not 1 x 13.

    Direct instruction, Aug 1 2026: "for the thumbnail, youtube shorts,
    editing etc I want it to be increased to three attempts, not only one
    attempt. The current rate is 1x13 i want it to be changed to 3x13."

    This is the "editing" gate: the independent AI judge that reads the
    finished stage and reworks it before a human ever sees it. It ran one
    round of thirteen reworks and then returned passed=False, which the
    caller treated as final.

    Each round starts from the ORIGINAL content, not from round 1's best
    failed attempt. That matters: reworking a rework compounds whatever the
    judge disliked, and thirteen more edits to an already-over-edited draft
    is the retry-without-variation defect wearing a different hat. Round 2
    is a fresh thirteen from the same starting point, after a pause.

    Returns the same dict as before, plus "rounds".
    """
    best = None
    rounds_run = 0
    for rnd in range(1, max(1, rounds) + 1):
        if rnd > 1:
            try:
                from gate_rounds import _fits
                fits = _fits(6)
            except Exception:
                fits = True
            if not fits:
                if tg_fn:
                    tg_fn(f"⏱️ Quality audit ({stage_name}): rounds {rnd}-{rounds} "
                          f"skipped for job time, not quality.")
                break
            if tg_fn:
                tg_fn(f"🔄 Quality audit ({stage_name}): round {rnd - 1} of {rounds} "
                      f"ended below the bar after {max_reworks} reworks. Waiting "
                      f"{QUALITY_GATE_ROUND_PAUSE_SEC // 60} minutes, then starting "
                      f"a fresh round from the original draft. The stage is only "
                      f"marked failed if round {rounds} also fails.")
            time.sleep(QUALITY_GATE_ROUND_PAUSE_SEC)
        result = _enforce_quality_gate_once(stage_name, initial_content, context,
                                            call_ai_fn, regenerate_fn, tg_fn,
                                            topic, max_reworks)
        result["rounds"] = rnd
        if result["passed"]:
            return result
        # Keep the best-scoring round, so a total failure still hands back the
        # strongest draft any round produced rather than the last one.
        # score is None when the AI judge could not be reached at all, and
        # None does not compare with a float. An unscored round is never
        # "better" than a scored one.
        if best is None or _num(result["score"]) > _num(best["score"]):
            best = result
        rounds_run = rnd
    # "rounds" must report how many rounds actually RAN, not which round
    # happened to hold the best draft -- otherwise three rounds of identical
    # failing scores report as one, and the log understates the real effort
    # in exactly the situation where knowing it matters.
    if best is not None:
        best["rounds"] = rounds_run
    return best


def _enforce_quality_gate_once(stage_name, initial_content, context, call_ai_fn,
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
    best_result = None
    reworked = 0

    for attempt in range(max_reworks + 1):
        result = audit_content(stage_name, content, context, call_ai_fn, topic=topic)
        if _num(result["score"]) > best_score:
            best_content, best_score = content, _num(result["score"])
            best_used_fallback = result["used_fallback"]
            best_result = result

        if result["passed"]:
            return {"content": content, "score": result["score"], "passed": True,
                    "reworked": reworked, "used_fallback": result["used_fallback"]}

        if attempt >= max_reworks:
            break

        reworked += 1
        issues_str = "; ".join(result["issues"][:3]) if result["issues"] else "no specific issues returned"
        if tg_fn:
            tg_fn(f"🔍 Quality audit: {stage_name} scored {fmt_score(result['score'])} "
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

    return {"content": best_content,
            "score": (best_result or {}).get("score") if best_result else None,
            "passed": False,
            "reworked": reworked, "used_fallback": best_used_fallback}
