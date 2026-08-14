"""
Blocking content-policy gate for the clinical-case channel.

WHY THIS IS A GATE AND NOT A GUIDELINE
--------------------------------------
2026 YouTube policy explicitly names the failure mode this channel could
fall into: "An AI 'doctor' providing medical diagnoses, health advice, or
wellness remedies is subject to these restrictions." Medical claims without
evidence draw limited ads or demonetisation; educational health content
qualifies only when presented in a neutral, informative tone.

The entire economic case for this niche is the $25-40 CPM band. A
limited-ads label removes that band. So the upside and the risk share a
single point of failure, which is precisely why this is enforced in code
with a hard block, in the same architectural position as the existing 8.5
quality floor -- not left to prompt wording and good intentions.

The six rules mirror the build spec exactly:
  1. Third-person past tense -- no second-person medical direction
  2. Every clinical claim traces to the cited paper (citation must exist)
  3. No drug comparison or efficacy claims
  4. No graphic surgical/wound imagery
  5. Mandatory disclaimer + CC BY attribution present
  6. Closed, published, retrospective cases only

check_script() and check_publish_package() both return
(passed: bool, violations: list[dict]) so the caller can log every specific
failure rather than a single opaque rejection.
"""
import re

# ---------------------------------------------------------------------------
# RULE 1 -- second-person medical direction.
#
# Deliberately NOT "any use of the word you". Documentary narration
# legitimately says "what you are about to hear" or "you might imagine",
# and blocking that would make this gate so noisy it would get switched
# off -- which is the real failure mode for an over-eager gate. What is
# actually prohibited is second person used to DIRECT, DIAGNOSE, or
# PRESCRIBE. Those constructions are what read as medical advice.
# ---------------------------------------------------------------------------
_DIRECTIVE_SECOND_PERSON = [
    r"\byou should\b", r"\byou must\b", r"\byou need to\b", r"\byou ought\b",
    r"\byou can treat\b", r"\byou can cure\b", r"\byou should take\b",
    r"\bif you (?:have|feel|experience|notice|suffer|develop)\b",
    r"\byour (?:symptom|diagnosis|condition|treatment|dose|dosage|medication|prescription)",
    r"\b(?:consult|see|ask|talk to|speak to) your (?:doctor|physician|gp|clinician|pharmacist)\b",
    r"\bwe recommend\b", r"\bi recommend\b", r"\brecommended dose\b",
    r"\btry (?:taking|using) \b", r"\bavoid taking\b",
    r"\bhow to treat\b", r"\bhow to cure\b", r"\bthe cure for\b",
]

# ---------------------------------------------------------------------------
# RULE 3 -- drug comparison / efficacy claims. Named limited-ads territory.
# Historical discovery framing is fine; "X beats Y" or "X is effective for
# Y" is not.
# ---------------------------------------------------------------------------
_DRUG_CLAIM_PATTERNS = [
    r"\b(?:more|less) effective than\b",
    r"\bworks better than\b", r"\bbetter than (?:taking|using)\b",
    r"\bsafer than\b", r"\bsuperior to\b", r"\boutperform",
    r"\bis (?:the )?(?:best|most effective) (?:treatment|drug|medication|remedy)\b",
    r"\bproven to (?:cure|treat|prevent|reverse)\b",
    r"\bguaranteed to\b", r"\bmiracle (?:cure|drug|treatment)\b",
    r"\bnatural (?:cure|remedy) for\b",
    r"\bwill (?:cure|heal|reverse) your\b",
]

# ---------------------------------------------------------------------------
# RULE 6 -- closed, retrospective cases only. Live/breaking health content
# carries both a policy risk and a factual-accuracy risk this pipeline
# cannot verify in real time.
# ---------------------------------------------------------------------------
# The rule is: do not present a live, unresolved public-health event as if
# reporting the news. It is NOT "avoid these words".
#
# Run 30563819566 lost 3 of 13 attempts to this list matching ordinary
# clinical prose. \bbreaking\b fires on "breaking down the drug" and
# "breaking the blood-brain barrier"; \bunfolding\b fires on protein
# unfolding, which is literally a biochemistry term this channel will use
# constantly; \bthis week\b fires on a patient's own timeline ("by the end
# of that week"). Same class of error as the "ct" substring bug in the
# figure ranker: matching a token instead of the meaning.
#
# Each pattern now requires the news framing that actually breaches the
# rule. The genuinely unambiguous phrases are kept bare.
_LIVE_CASE_PATTERNS = [
    r"\bongoing outbreak\b", r"\bcurrent outbreak\b",
    r"\bas of today\b", r"\bstill spreading\b", r"\bdeveloping story\b",
    r"\bbreaking news\b", r"\bbreaking story\b",
    r"\b(?:story|crisis|situation|outbreak|investigation) (?:is )?unfolding\b",
    r"\bunfolding (?:story|crisis|situation|outbreak|investigation)\b",
    r"\b(?:is|are) happening right now\b",
    r"\bhappening as we speak\b",
    r"\bhealth officials are (?:currently )?(?:investigating|warning)\b",
]

# ---------------------------------------------------------------------------
# RULE 4 -- graphic imagery. pmc_data.extract_figures() screens figures at
# fetch time; this is the second, independent check at publish time, because
# a single-point screen on a licensing/policy matter is not enough.
# ---------------------------------------------------------------------------
_GRAPHIC_MARKERS = (
    "intraoperative", "intra-operative", "operative field", "resected specimen",
    "gross specimen", "autopsy", "cadaver", "dissection", "amputat",
    "wound", "ulcer", "necrosis", "necrotic", "gangrene", "abscess",
    "laceration", "degloving", "excised", "post-mortem", "postmortem",
    "surgical site", "incision",
)

# ---------------------------------------------------------------------------
# RULE 7 -- actionable dosing and treatment recommendation.
#
# ADDED BECAUSE THE GATE PASSED A SCRIPT THAT SHOULD NOT HAVE PASSED. The
# episode from run 31740721781 cleared every check above while narrating
# "argatroban at 2 micrograms per kilogram per minute", "IVIG 1 g/kg/day",
# and "first-line therapies". None of the rules were looking for it: rule 1
# catches second-person direction and this was third person, rule 3 catches
# comparative claims and this compared nothing. It was simply a dosing
# regimen, stated plainly, in a documentary a member of the public can act on.
#
# THE HARD PART IS NOT MATCHING DOSES, IT IS NOT MATCHING LAB VALUES.
#
# This channel's entire CHART register plots the case's real reported
# numbers -- sodium 118 mmol/L, platelets 12,000 per microlitre, creatinine
# 2.4 mg/dL. Those are measurements OF the patient and they are the content.
# A regex that swallowed them would block every good script and get switched
# off, which is how an over-eager gate becomes no gate at all.
#
# The distinction is the denominator. A dose is an amount per body weight,
# per body surface, or per unit of time -- mg/kg, µg/kg/min, g/day. A lab
# value is an amount per volume of fluid -- mg/dL, mmol/L, per microlitre.
# So the numerator list and the denominator list are both closed, and no
# per-volume unit appears in the denominator list at all.
_DOSING_PATTERNS = [
    # 2 µg/kg/min, 1 g/kg/day, 500 mg/m2, 10 units/kg -- amount per body or
    # per time. Deliberately excludes /dL, /L, /mL, /µL: those are assays.
    r"\d+(?:\.\d+)?\s*(?:mg|mcg|µg|μg|ug|g|grams?|milligrams?|micrograms?|"
    r"units?|iu|mmol|mEq)\s*(?:/|\s+per\s+)\s*(?:kg|kilogram|m2|m\^2|"
    r"square metre|square meter|day|hour|hr|minute|min|dose|week)\b",
    # the same thing spelled out, which is how narration actually says it
    r"\d+(?:\.\d+)?\s*(?:micrograms?|milligrams?|grams?|units?)\s+per\s+"
    r"(?:kilogram|kilo|square metre|square meter|day|hour|minute)\b",
    # 500 mg twice daily / 20 mg once a day / 5 g every eight hours
    r"\d+(?:\.\d+)?\s*(?:mg|mcg|µg|μg|ug|g|grams?|milligrams?|micrograms?|"
    r"units?|iu)\b[^.]{0,20}\b(?:once|twice|three times|four times|daily|"
    r"nightly|hourly|every\s+\w+\s+hours?|per\s+day|a\s+day)\b",
    # dosing language even without a number attached
    r"\b(?:at|in) a dose of\b", r"\bdosed at\b", r"\bdosage of\b",
    r"\bloading dose\b", r"\bmaintenance dose\b", r"\btitrated to\b",
]

# Treatment-recommendation framing. "First-line" and "treatment of choice"
# are not descriptions of what happened to one patient -- they are clinical
# guidance about what should be done, which is precisely the line this
# channel does not cross. Narration can always say what the team actually
# tried instead: "the first drugs they reached for", "what they gave next".
_TREATMENT_RECOMMENDATION_PATTERNS = [
    r"\bfirst[- ]line\b", r"\bsecond[- ]line\b", r"\bthird[- ]line\b",
    r"\btreatment of choice\b", r"\bdrug of choice\b",
    r"\bmainstay of (?:treatment|therapy|management)\b",
    r"\bstandard of care\b", r"\bstandard treatment for\b",
    r"\bshould be treated with\b", r"\bmust be treated with\b",
    # PRESENT TENSE ONLY, AND THAT IS THE WHOLE POINT. "She was treated with
    # argatroban" is this patient's history and is exactly what the channel
    # exists to narrate. "HIT is treated with a direct thrombin inhibitor" is
    # a general clinical rule a viewer can apply to themselves. Same verb,
    # opposite meaning, and the tense is what separates them.
    r"\bis treated with\b", r"\bis managed with\b",
    r"\bthe recommended (?:treatment|therapy|regimen|management)\b",
    r"\btreatment guidelines? (?:recommend|require|state)\b",
    r"\bindicated for the treatment of\b",
]

REQUIRED_DISCLAIMER_MARKERS = ("not medical advice", "published medical literature")


def _findings(text, patterns, rule, severity="block"):
    out = []
    low = text.lower()
    for pat in patterns:
        for match in re.finditer(pat, low):
            start = max(0, match.start() - 45)
            out.append({
                "rule": rule,
                "severity": severity,
                "matched": match.group(0),
                "context": text[start:match.end() + 45].strip(),
            })
    return out


def check_script(script_text, citation=""):
    """
    Rules 1, 2, 3 and 6 against the narration script.

    Returns (passed, violations). passed=False means do not proceed -- the
    caller should rewrite and re-attempt, exactly as it already does for a
    failed quality score.
    """
    violations = []
    text = script_text or ""

    violations += _findings(text, _DIRECTIVE_SECOND_PERSON,
                            "rule1_second_person_direction")
    violations += _findings(text, _DRUG_CLAIM_PATTERNS,
                            "rule3_drug_efficacy_claim")
    violations += _findings(text, _LIVE_CASE_PATTERNS,
                            "rule6_live_case")
    violations += _findings(text, _DOSING_PATTERNS,
                            "rule7_actionable_dosing")
    violations += _findings(text, _TREATMENT_RECOMMENDATION_PATTERNS,
                            "rule7_treatment_recommendation")

    # Rule 2 -- a sourced clinical claim requires a source. This cannot
    # verify each individual claim automatically (that would need the paper
    # re-read against every sentence), so it enforces the checkable half:
    # a real citation must exist for the episode at all.
    if not (citation or "").strip():
        violations.append({
            "rule": "rule2_missing_citation",
            "severity": "block",
            "matched": "",
            "context": "No source citation supplied for this episode.",
        })

    return (not any(v["severity"] == "block" for v in violations)), violations


def check_publish_package(description="", on_screen_credits=None,
                          figure_captions=None, citation=""):
    """
    Rules 4 and 5 immediately before publish.

    description        -- the final YouTube description text
    on_screen_credits  -- attribution strings actually rendered on screen
    figure_captions    -- captions of figures that made it into the video
    citation           -- the CC BY citation for the source paper
    """
    violations = []
    desc_low = (description or "").lower()

    # Rule 5a -- disclaimer present in the description.
    missing = [m for m in REQUIRED_DISCLAIMER_MARKERS if m not in desc_low]
    if missing:
        violations.append({
            "rule": "rule5_missing_disclaimer",
            "severity": "block",
            "matched": ", ".join(missing),
            "context": "Description must state this is a report on published "
                       "medical literature and not medical advice.",
        })

    # Rule 5b -- CC BY attribution present in the description. This is a
    # licensing condition, not a stylistic preference: without it, a
    # licensed reuse becomes an unlicensed one.
    if citation and citation.strip():
        key = (citation.split(".")[0] or "").strip().lower()
        if key and key not in desc_low:
            violations.append({
                "rule": "rule5_missing_attribution_in_description",
                "severity": "block",
                "matched": key[:60],
                "context": "CC BY requires the source citation in the description.",
            })
    else:
        violations.append({
            "rule": "rule5_missing_attribution_in_description",
            "severity": "block",
            "matched": "",
            "context": "No citation available to attribute.",
        })

    # Rule 5c -- attribution rendered on screen at the figure itself.
    if figure_captions and not on_screen_credits:
        violations.append({
            "rule": "rule5_missing_onscreen_credit",
            "severity": "block",
            "matched": "",
            "context": f"{len(figure_captions)} figure(s) used with no "
                       "on-screen attribution rendered.",
        })

    # Rule 4 -- independent re-screen of anything that reached the video.
    for cap in (figure_captions or []):
        low = (cap or "").lower()
        if not low.strip():
            violations.append({
                "rule": "rule4_unscreenable_figure",
                "severity": "block",
                "matched": "",
                "context": "Figure with no caption cannot be content-screened.",
            })
            continue
        for marker in _GRAPHIC_MARKERS:
            if marker in low:
                violations.append({
                    "rule": "rule4_graphic_figure",
                    "severity": "block",
                    "matched": marker,
                    "context": cap[:120],
                })
                break

    return (not any(v["severity"] == "block" for v in violations)), violations


def build_disclaimer_block(citation=""):
    """
    The exact description text that satisfies rule 5. Pipelines should use
    this rather than hand-writing the wording, so the gate and the content
    can never drift out of sync.
    """
    lines = [
        "",
        "———",
        "This video is a report on a published, peer-reviewed medical case "
        "from the open-access literature. It is educational commentary on "
        "published medical literature and is not medical advice, diagnosis, "
        "or treatment guidance. Always consult a qualified healthcare "
        "professional about your own health.",
    ]
    if citation:
        lines += ["", f"Source: {citation}",
                  "Figures reproduced under their Creative Commons licence, "
                  "with attribution as shown."]
    return "\n".join(lines)


def format_violations(violations, limit=12):
    """One-line-per-violation summary for logs and the Telegram review card."""
    if not violations:
        return "no policy violations"
    out = []
    for v in violations[:limit]:
        out.append(f"[{v['severity'].upper()}] {v['rule']}: "
                   f"{v['matched'] or v['context'][:70]}")
    if len(violations) > limit:
        out.append(f"...and {len(violations) - limit} more")
    return "\n".join(out)


# The hard prompt clause injected into script generation. Kept here, beside
# the gate that enforces it, so the instruction and the check can never
# describe different rules.
SCRIPT_PROMPT_RULES = """
MANDATORY MEDICAL CONTENT RULES (non-negotiable — a script violating any of
these is rejected outright and rewritten):
1. Write in third person, past tense, about the documented patient in the
   source paper: "The patient presented with...", "Her sodium had fallen
   to...". Never address the viewer's own health. Never write "you should",
   "if you have", "your symptoms", or "consult your doctor".
2. Every clinical detail — every value, date, finding, and outcome — must
   come from the sourced case text provided. Do not invent numbers. Do not
   invent quotes or attribute speech to any real clinician or patient.
3. Never compare drugs, never claim one treatment is better, safer, or more
   effective than another, and never describe anything as proven to cure,
   prevent, or reverse a condition. Drug content is historical discovery
   narrative only.
4. Do not describe graphic surgical, wound, or post-mortem detail. Explain
   mechanism and findings clinically, not viscerally.
5. Close by explaining what this case changed in medical understanding —
   never by telling the viewer what to do about their own health.
6. Write about the case only in the past tense as a closed, published,
   resolved investigation. Never frame anything as ongoing or breaking.
7. NEVER state a drug dose or a dosing schedule, and never say what a
   condition "is treated with". No "2 micrograms per kilogram per minute",
   no "1 g/kg/day", no "500 mg twice daily", no "first-line", no "treatment
   of choice", no "standard of care". Name the drug if the case turns on it
   and say what happened — "they started argatroban; the platelet count kept
   falling" — and stop there. The viewer must never be able to act on the
   episode as if it were a prescription.
   Laboratory VALUES are different and are wanted: "her sodium was 118",
   "the platelet count was twelve thousand" are measurements of the patient
   and belong in the script. The prohibited thing is an amount given per
   kilogram, per square metre, or per unit of time.
"""
