"""
Quality scoring for the clinical-case channel, rebuilt to stop measuring
length and start measuring quality.

THE PROBLEM THIS REPLACES
-------------------------
score_result() gave word count a 4.8-point swing on a 10-point scale
(+2.8 at >=1900 words, +0.8 at 1600-1899, -2.0 below) against an 8.5 gate.
Length was therefore the single largest term in the score -- larger than
craft, hook and clarity combined could recover from. A tight, well-sourced
1,700-word script scored 8.0 and failed; a padded 1,900-word one started at
10.0. That is backwards: padding a script makes it worse to watch and better
to score.

Two live runs confirmed it. Run 30561361514 produced 766-1161 words on all
13 attempts, every one mathematically incapable of passing. Run 30563819566
reached 1,300-1,800 and still could not clear the floor.

THE SEPARATION
--------------
Length and quality are different questions and are now answered separately.

  DURATION is a floor, not a gradient. Below DURATION_FLOOR_WORDS the video
  is too short to be the product this channel promises, and no amount of
  craft changes that -- it blocks. Above the floor, length contributes
  NOTHING to the quality score. A 1,300-word episode and a 2,000-word
  episode are scored purely on how good they are.

  QUALITY is craft, hook, clarity, cleanliness, and -- specific to this
  channel -- how densely the script carries real reported clinical detail.

WHY 1250 WORDS
--------------
At the pipeline's 125 wpm that is ~10 minutes. YouTube requires 8+ minutes
for mid-roll ad eligibility, which is a real revenue cliff, so the floor
sits above it with margin rather than on it. TARGET_WORDS stays 1900 (~15
min) as the thing expansion aims for, but missing it is no longer fatal.

COMPENSATION, AND ITS LIMIT
---------------------------
The old hook/craft/clarity gates were kill switches: miss any one by 0.1
and the whole attempt scored -0.4 regardless of everything else. They are
now two-level. Below a RED LINE the attempt still blocks outright -- those
are genuine "this is not publishable" levels. Between the red line and the
target, the shortfall costs points proportionally, so real strength in one
dimension can carry a modest weakness in another. Excellence compensates;
failure does not.
"""
import re

# ── duration ───────────────────────────────────────────────────────────
WPM = 110                     # slowed from 125 after "the audio pacing is very fast"
DURATION_FLOOR_WORDS = 1250   # ~10 min; mid-roll eligibility is 8 min
TARGET_WORDS = 1900           # ~15 min; what expansion aims for, not a gate

# ── quality gates: (red line, target) ──────────────────────────────────
# Red line = block outright. Target = full marks; between the two the
# shortfall is charged against the score instead of zeroing it.
HOOK_RED, HOOK_TARGET = 4.5, 6.5
CRAFT_RED, CRAFT_TARGET = 6.0, 7.9
# Clarity target drops from 8.8 to 8.0. 8.8 was calibrated on
# dark-documentary topics, where the subject is simple by construction. A
# clinical case carries irreducible complexity -- naming the actual
# mechanism is the point of the channel -- so demanding near-perfect
# lay clarity punished the content for being what it is.
CLARITY_RED, CLARITY_TARGET = 6.0, 8.0

# How much a full miss (red line) costs, per dimension. Sum is deliberately
# less than the passing margin so two mild shortfalls are survivable and
# three are not.
_DEFICIT_WEIGHT = {"hook": 1.2, "craft": 1.1, "clarity": 0.9}


def projected_runtime_minutes(words):
    return round(words / WPM, 1)


def duration_check(words):
    """
    (ok, message). The ONLY place length is allowed to decide anything.
    """
    mins = projected_runtime_minutes(words)
    if words < DURATION_FLOOR_WORDS:
        return False, (f"{words}w -> ~{mins} min, below the {DURATION_FLOOR_WORDS}w "
                       f"(~{projected_runtime_minutes(DURATION_FLOOR_WORDS)} min) floor. "
                       f"Too short to publish; mid-roll ads need 8+ min.")
    if words < TARGET_WORDS:
        return True, (f"{words}w -> ~{mins} min. Under the {TARGET_WORDS}w target but "
                      f"over the floor: allowed, and NOT penalised on quality.")
    return True, f"{words}w -> ~{mins} min."


# ── clinical specificity: the points word count used to occupy ─────────
# Deliberately measured PER 100 WORDS. An absolute count would just be
# length wearing a different hat, which is the bug being removed.
# Numbers appear as WORDS in these scripts, not digits. build_script_prompt
# instructs it directly: 'Every number must be specific: not "many" but
# "forty-seven"' -- because the text is read aloud by TTS, where "171" is
# ambiguous and "one hundred and seventy-one" is not.
#
# The first version of this module matched digits only. Measured on identical
# content, that under-counted by ~8x (14.96 details/100w written with digits
# vs 1.81 spelled out), and on run 30569528382 it scored a genuinely detailed
# 1,953-word script at 1.29/10 specificity -- becoming the sole reason the
# only attempt to pass every other gate was blocked. The metric was wrong,
# not the script.
# Spelled-out numbers, including compounds. The continuation group used to
# allow only one..ten, hundred, thousand and "and" -- so "one hundred and
# forty micromoles per litre", a completely ordinary reported value, matched
# as far as "one hundred and" and then stopped, missing the unit and scoring
# nothing. Every tens word is now a legal continuation, which is what
# English actually does.
_NUMWORD_ATOM = (r"(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|"
                 r"twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|"
                 r"nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|"
                 r"ninety|hundred|thousand|million)")
_NUMWORD = rf"(?:{_NUMWORD_ATOM}(?:[-\s](?:{_NUMWORD_ATOM}|and))*)"
_NUM = rf"(?:\d+(?:[.,]\d+)?|{_NUMWORD})"

# Units. The first list was assembled from memory and had a hole big enough
# to change the score: it contained `mmol` and `millimol\w*` but NOT
# micromoles -- and "micromoles per litre" is the single most common unit in
# the biochemistry these cases turn on. Measured on a realistic 1,193-word
# clinical narration, that one gap alone lost every serum and bilirubin
# concentration in the script.
_UNIT = (r"(?:mg|mcg|µg|ug|ng|pg|g|kg|ml|mL|l|L|dL|dl|litres?|liters?|"
         r"mmol|micromol\w*|millimol\w*|nanomol\w*|µmol|umol|mol|mEq|meq|"
         r"milliequivalents?|mmHg|kPa|millimet\w*|mm|cm|centimet\w*|"
         r"IU|U/L|U/l|units?\s+per\s+litre|%|percent|"
         r"beats?|bpm|degrees?|celsius|centigrade|"
         r"grams?|kilograms?|micrograms?|milligrams?|nanograms?|"
         r"cells?\s+per|copies\s+per|per\s+litre|per\s+decilitre)")

_LAB_VALUE = re.compile(rf"\b{_NUM}\s?(?:per\s+)?{_UNIT}\b", re.I)

# A decimal spoken aloud. build_script_prompt requires numbers to be written
# as words for TTS, so a real reported value like an INR of 2.8 or a pH of
# 7.1 reaches the script as "two point eight" -- carrying no unit and
# therefore invisible to _LAB_VALUE. These are among the most specific
# statements a clinical script can make and were scoring zero.
_SPOKEN_DECIMAL = re.compile(rf"\b{_NUMWORD}\s+point\s+{_NUMWORD}\b", re.I)

_AGE = re.compile(rf"\b{_NUM}[-\s]year[-\s]old\b", re.I)
_TIMEPOINT = re.compile(rf"\b(?:day|hour|week|month|year)s?\s+{_NUM}\b|"
                        rf"\b{_NUM}\s+(?:day|hour|week|month|year)s?\b|"
                        rf"\bon the {_NUM}(?:st|nd|rd|th)?\s+day\b", re.I)
_CLINICAL_NOUN = re.compile(
    r"\b(?:diagnosis|diagnosed|diagnostic|presented|presentation|admitted|"
    r"admission|discharged|biopsy|serum|plasma|imaging|scan|MRI|CT|ECG|EEG|"
    r"ultrasound|echocardiogram|radiograph|endoscopy|colonoscopy|"
    r"differential|prognosis|histology|histological|titre|titer|culture|"
    r"cultures|assay|enzyme|antibody|antibodies|marker|biomarker|mutation|"
    r"genotype|sequencing|panel|screening|referral|coagulopathy|"
    r"electrolytes?|metabolite|metabolic|workup|work-up)\b", re.I)

# A named mechanism, enzyme, syndrome or disease. A script that says
# "galactose-1-phosphate uridylyltransferase" is being vastly more specific
# than one that says "an enzyme", and no amount of unit-matching sees the
# difference. Matched structurally rather than from a word list, because a
# word list for all of medicine is not maintainable.
_TECHNICAL_TERM = re.compile(
    r"\b(?:[a-z]+(?:-[a-z0-9]+){1,}(?:ase|ine|ide|ate|ol)?"
    r"|[a-z]{6,}(?:ase|aemia|emia|osis|itis|pathy|oma|opathy|uria|plasia))\b")


# Density of concrete clinical detail, per 100 words, that earns full marks.
#
# CALIBRATION, WITH THE ACTUAL MEASUREMENTS
# -----------------------------------------
# The first value was 6.0, chosen with no evidence at all. The second was
# 3.0, chosen against two references. Both were measured with a DETECTOR
# THAT WAS ITSELF BROKEN, which made the threshold meaningless either way:
#
#   * it had no unit for micromoles -- the single most common unit in the
#     biochemistry these cases turn on
#   * its spelled-number pattern allowed only one..ten as a continuation, so
#     "one hundred and forty micromoles per litre" matched as far as "one
#     hundred and" and stopped, missing the unit entirely
#   * it could not see a spoken decimal ("an INR of two point eight"), even
#     though the prompt REQUIRES numbers to be spelled out for TTS
#   * it had no notion of a named mechanism, so a script saying
#     "galactose-1-phosphate uridylyltransferase" scored the same as one
#     saying "an enzyme"
#
# Re-measured with the detector fixed:
#
#   0.00 /100w   non-clinical documentary narration -- the floor, what
#                storytelling prose with no clinical content looks like
#   3.94 /100w   a realistic 1,193-word clinical episode of the kind this
#                channel exists to make: real values, real timepoints, a
#                full differential, named mechanisms
#  14.66 /100w   synthetic prose that is nothing but clinical facts, which
#                reads as a list and nobody would watch
#
# 4.5 places that target episode at 8.8/10 -- clearly good, with headroom
# left for a denser one -- while remaining unreachable by anything that is
# merely storytelling and well short of the unwatchable ceiling.
#
# Honest limitation: the 3.94 reference is ONE sample. It is the right KIND
# of evidence, which the previous two numbers were not, but the threshold
# should be revisited once several real accepted scripts have been measured.
SPECIFICITY_TARGET_PER_100W = 4.5


def clinical_specificity(script, max_points=2.8):
    """
    0..max_points. How densely the script carries real reported detail --
    values with units, ages, timepoints, clinical findings.

    This is what replaces word count's share of the score, and it is the
    right substitute for THIS channel: the whole premise is that every
    detail comes from a published paper, so density of concrete detail is
    a direct proxy for whether the sourced case was actually used rather
    than gestured at. It cannot be gamed by padding -- padding lowers it.
    """
    if not script or not script.strip():
        return 0.0, {}
    words = max(1, len(script.split()))
    counts = {
        "values":     len(_LAB_VALUE.findall(script)),
        "decimals":   len(_SPOKEN_DECIMAL.findall(script)),
        "ages":       len(_AGE.findall(script)),
        "timepoints": len(_TIMEPOINT.findall(script)),
        # Unique, not total: counting every occurrence would reward saying
        # "diagnosis" forty times, which is padding wearing a lab coat.
        "clinical":   len(set(m.lower() for m in _CLINICAL_NOUN.findall(script))),
        "technical":  len(set(m.lower() for m in _TECHNICAL_TERM.findall(script))),
    }
    hits = sum(counts.values())
    per100 = hits / (words / 100.0)
    # See SPECIFICITY_TARGET_PER_100W for the calibration and its evidence.
    score = max_points * min(1.0, per100 / SPECIFICITY_TARGET_PER_100W)
    counts["per_100_words"] = round(per100, 2)
    return round(score, 2), counts


# ── the composite ──────────────────────────────────────────────────────
def gate_deficits(hook, craft, clarity):
    """
    (blocked, penalty, notes). Blocked only on a red line.
    """
    dims = (("hook", hook, HOOK_RED, HOOK_TARGET),
            ("craft", craft, CRAFT_RED, CRAFT_TARGET),
            ("clarity", clarity, CLARITY_RED, CLARITY_TARGET))
    blocked, penalty, notes = [], 0.0, []
    for name, val, red, target in dims:
        if val < red:
            blocked.append(f"{name} {val:.1f} below red line {red}")
            continue
        if val < target:
            span = target - red
            frac = (target - val) / span if span else 0.0
            cost = _DEFICIT_WEIGHT[name] * frac
            penalty += cost
            notes.append(f"{name} {val:.1f} < {target} (-{cost:.2f})")
    return blocked, round(penalty, 2), notes


# Weighted composite. Every dimension is 0-10 and every one genuinely moves
# the result -- which the first version of this function did not achieve: it
# kept the old "5.0 base + fixed bonuses" shape, so base 5.0 + 2.2 clean +
# 2.8 specificity already hit the 10.0 ceiling and hook/craft/clarity could
# only ever shave small amounts off. A bad hook scored the same as a good
# one. Caught by running the real attempts through it before shipping.
_WEIGHTS = {
    "craft":       0.30,   # heaviest: it is the thing viewers actually feel
    "hook":        0.25,   # decides whether anything else gets watched
    "clarity":     0.20,
    "specificity": 0.15,   # channel-specific: is the sourced case really used
    "clean":       0.10,   # markdown/formatting leakage
}


def score_script(words, violations, script, hook, craft, clarity):
    """
    Returns (score, passed, report).

    Length never contributes to `score` -- it is checked once, as a floor,
    and then ignored. A 1,300-word episode that is genuinely well made
    outscores a 2,000-word one that is not, which is the entire intent.
    """
    report = {}
    dur_ok, dur_msg = duration_check(words)
    report["duration"] = dur_msg
    report["runtime_min"] = projected_runtime_minutes(words)

    spec_pts, spec_counts = clinical_specificity(script)
    spec10 = round(spec_pts / 2.8 * 10.0, 2)          # rescale to 0-10
    clean10 = 10.0 if violations == 0 else (7.0 if violations <= 2 else 3.0)
    report["specificity"] = spec10
    report["specificity_detail"] = spec_counts
    report["cleanliness"] = clean10

    dims = {"craft": craft, "hook": hook, "clarity": clarity,
            "specificity": spec10, "clean": clean10}
    s = sum(_WEIGHTS[k] * v for k, v in dims.items())

    # Shortfall against target still costs, on top of the weighting, so a
    # dimension sitting just above its red line cannot be fully laundered
    # by strength elsewhere.
    blocked, penalty, notes = gate_deficits(hook, craft, clarity)
    s -= penalty

    report["dimensions"] = {k: round(v, 2) for k, v in dims.items()}
    report["gate_penalty"] = penalty
    report["gate_notes"] = notes
    report["blocked_on"] = list(blocked)
    if not dur_ok:
        report["blocked_on"].append("duration floor")

    s = round(max(0.0, min(10.0, s)), 2)
    return s, bool(dur_ok and not blocked), report
