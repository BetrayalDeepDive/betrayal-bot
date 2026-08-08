"""
Read the finished script and decide what every beat needs to LOOK like.

THE IDEA
--------
Until now the visual system worked backwards. A quota decided the mix of
registers up front, a classifier guessed a register per segment from keywords,
and the renderer then went looking for something to put on screen. The script
was never actually read as a piece of film. So the episode got the visuals the
library happened to contain, in the proportions a table decided, and the
complaint that came back was the obvious consequence: generic.

This inverts it. The script is read first, beat by beat, and each beat states
what it NEEDS — what the shot has to do, what it is of, and how it should be
made. The renderers then serve that brief instead of the brief being whatever
the renderers could manage.

A brief is a plain dict, so it is inspectable, loggable, reviewable and
testable without rendering anything:

    {"index": 12,
     "text":  "The clot travelled from the calf to the lung in under a minute.",
     "intent": "mechanism",       # what the shot has to DO
     "subject": "clot lung",      # what it is OF
     "treatment": "generated",    # how it should be made
     "prompt": "...",             # if generated
     "forbid": ["scan", "record"],
     "why": "a mechanism beat: the shot has to show a change, not a place"}

WHAT MAY BE GENERATED, AND WHAT MAY NOT
---------------------------------------
This is a documentary about a REAL patient in a REAL published paper, and the
channel's whole differentiator is that everything on screen is sourced. That
puts a hard line through the middle of "generate new visuals":

  INTERPRETIVE imagery may be generated. A vessel narrowing, a spreading
  darkness, an empty corridor at 3am, a clock. These are the film's own
  language for what the narration is describing. Nobody mistakes them for
  evidence, and they are exactly what a documentary editor would cut in.

  EVIDENTIARY imagery may NEVER be generated. A CT slice, an ECG trace, a
  histology slide, an X-ray, a lab report, a patient's face. Those are claims
  about what was found in this specific patient. Generating one is fabricating
  medical evidence inside a factual programme — the fastest possible way to
  destroy a medical channel, and a synthetic-media problem on top.

So a beat whose subject is evidence is routed to the REAL figure from the
paper, or to a photograph, or to a drawn chart built from the paper's own
reported values — never to a generator. medical_policy_gate enforces it and
`forbid` carries the reason to the renderer.

The generated style is also deliberately non-photoreal. A frame that could be
mistaken for a photograph of this patient's hospital is a frame that has to be
disclosed and defended; a frame that is plainly an illustration is not.
"""
import re


# ── what a shot has to DO ──────────────────────────────────────────────
#
# Six intents, because a documentary shot is only ever doing one of six jobs.
# Ordered by how specific the signal is: the first that fires wins, so a line
# that both names a place and reports a value is read as the value.
INTENTS = ("evidence", "mechanism", "value", "chronology", "place", "state")

_SIGNALS = (
    # A finding was SEEN. This is the paper's own image or nothing.
    ("evidence", (
        r"\b(?:showed|revealed|demonstrated|confirmed|visible|seen) on\b",
        r"\b(?:the |a |an )?(?:ct|mri|x-ray|radiograph|ultrasound|ecg|eeg|"
        r"echocardiogram|angiogram|biopsy|histology|scan)\b",
        r"\bimaging\b", r"\bslide\b", r"\bspecimen\b",
    )),
    # Something CHANGED inside the body. This is what generation is for.
    ("mechanism", (
        r"\b(?:travelled|traveled|spread|blocked|obstruct|narrow|rupture|"
        r"leak|compress|starv|deprive|flood|accumulat|build up|built up)\w*\b",
        r"\bmechanism\b", r"\bwhy (?:it|this) happen\w*\b",
        r"\b(?:cut off|shut down|gave way|broke down)\b",
        r"\bbecause the\b.*\b(?:could not|failed|stopped)\b",
    )),
    # A NUMBER moved. This is a chart built from the paper's own values.
    ("value", (
        # A NARRATION script spells its units out -- the voice says "one
        # hundred and eighteen millimoles per litre", never "118 mmol/L". The
        # symbol-only pattern read a real value beat as atmosphere.
        r"\b\d+(?:\.\d+)?\s*(?:mg|ml|mmol|mcg|g/dl|mm|cm|kg|%|bpm)\b",
        r"\b\d+(?:\.\d+)?\s+(?:milli|micro|kilo|centi)?"
        r"(?:moles?|grams?|litres?|liters?|metres?|meters?|degrees?|beats?|"
        r"percent|units?)\b",
        r"\b(?:rose|fell|dropped|climbed|peaked|doubled|halved) to\b",
        r"\b(?:level|count|concentration|reading|titre|titer)s?\b",
    )),
    # TIME passed. This is a timeline.
    ("chronology", (
        r"\bday (?:one|two|three|four|five|six|seven|eight|nine|ten|\d+)\b",
        r"\b(?:hours|days|weeks|months|years) (?:later|after|earlier|before)\b",
        r"\b(?:by|on) the (?:following|next|fourth|fifth|ninth)\b",
        r"\bover the (?:next|following)\b", r"\bthat (?:evening|night|morning)\b",
    )),
    # Somewhere REAL. This is a photograph.
    ("place", (
        r"\b(?:hospital|ward|clinic|emergency department|emergency room|"
        r"intensive care|theatre|ambulance|corridor|waiting room)\b",
        r"\b(?:sent home|discharged|admitted|referred|arrived at|brought in)\b",
        r"\b(?:at home|at work|in the car)\b",
    )),
)

# Anything that did not fire above is a STATE beat: how things stood, what
# nobody could explain, what it felt like to be the patient. These are the
# beats a documentary carries on atmosphere, and the ones the old system had
# nothing for except another diagram.


# ── what the shot is OF ────────────────────────────────────────────────
_SUBJECT_HINTS = (
    ("brain",   r"\b(?:brain|cerebral|cortex|neurolog|seizure|stroke|meningi)\w*"),
    ("heart",   r"\b(?:heart|cardiac|ventricl|atri|coronary|arrhythmi)\w*"),
    ("lung",    r"\b(?:lung|pulmonary|breath|respirat|chest|oxygen)\w*"),
    ("vessel",  r"\b(?:clot|thrombus|embol|artery|arterial|vein|venous|vessel)\w*"),
    ("blood",   r"\b(?:blood|serum|plasma|haemoglobin|hemoglobin|platelet|sodium|"
                r"potassium|creatinine)\w*"),
    ("liver",   r"\b(?:liver|hepat|bile|jaundice)\w*"),
    ("kidney",  r"\b(?:kidney|renal|dialysis|urine)\w*"),
    ("gut",     r"\b(?:stomach|bowel|intestin|abdomen|gastr)\w*"),
    ("eye",     r"\b(?:eye|pupil|iris|retina|vision|visual)\w*"),
    ("nerve",   r"\b(?:nerve|neuropath|numb|tingl|weakness)\w*"),
    ("skin",    r"\b(?:skin|rash|lesion|blister|ulcer)\w*"),
)


# ── the look, locked ───────────────────────────────────────────────────
#
# One style for every generated frame in the channel, for the same reason a
# film has one grade: forty frames in forty styles is not a documentary, it is
# a mood board. Held here rather than written into each prompt so it can be
# changed once.
#
# Explicitly NOT photoreal. A generated frame that could pass for a photograph
# of this patient's hospital is a frame that has to be disclosed and defended.
# A frame that is plainly an illustration is neither.
STYLE = ("dark editorial medical illustration, deep teal and near-black, "
         "single cool light source, high contrast, minimal, matte, "
         "clean vector-like forms, no text, no logos, no watermark, "
         "no recognisable human face, not a photograph")

# Never generated, under any prompt. These are claims about what was found in
# a real patient; the paper's own figure is the only acceptable source.
NEVER_GENERATE = (
    "ct scan", "mri scan", "x-ray", "radiograph", "ultrasound image",
    "ecg", "ekg", "electrocardiogram", "eeg", "histology", "biopsy slide",
    "microscope slide", "pathology slide", "lab report", "blood report",
    "medical record", "patient chart", "patient photograph", "patient face",
    "prescription", "test result",
)

_TREATMENT_FOR = {
    "evidence":   "figure",      # the paper's own image, or a photograph
    "value":      "chart",       # the paper's own reported numbers
    "chronology": "timeline",
    "place":      "photograph",
    "mechanism":  "generated",   # the one intent generation is FOR
    "state":      "generated",
}


def classify(text):
    """(intent, why) for one beat."""
    low = (text or "").lower()
    for intent, patterns in _SIGNALS:
        for pat in patterns:
            if re.search(pat, low):
                return intent, "matched /%s/" % pat[:38]
    return "state", "no evidence, mechanism, value, time or place signal"


def subject_of(text, topic=""):
    """The concrete thing THIS BEAT is about, or "" when it names none.

    The topic is consulted only when the beat itself names nothing. Folding it
    in unconditionally made every beat of an episode about a clot come back
    "vessel", including the ones about a waiting room -- the same failure
    stock_match had, where the episode title drowned all 106 segments.
    """
    def _hits(blob):
        return [name for name, pat in _SUBJECT_HINTS if re.search(pat, blob)]
    own = _hits((text or "").lower())
    if own:
        return " ".join(own[:2])
    return " ".join(_hits((topic or "").lower())[:1])


def _prompt_for(intent, subject, text):
    """A real generation prompt, or None when this beat must not be generated."""
    if intent in ("evidence", "value"):
        return None
    core = {
        "vessel": "a narrowing vessel, one dark mass carried along it",
        "brain":  "a cross-section of a brain rendered as clean abstract form",
        "heart":  "a stylised heart in cross-section, one chamber highlighted",
        "lung":   "stylised branching airways, one branch going dark",
        "blood":  "abstract flowing particles in a channel",
        "liver":  "a stylised liver form, one region discoloured",
        "kidney": "stylised filtering structures, one blocked",
        "gut":    "a stylised loop of bowel in cross-section",
        "eye":    "an abstract iris and pupil, geometric",
        "nerve":  "a branching nerve rendered as thin light lines",
        "skin":   "an abstract layered cross-section of skin",
    }.get(subject.split()[0] if subject else "", "")

    if intent == "mechanism":
        body = core or "an abstract diagram of one thing being blocked by another"
        return "%s, %s" % (body, STYLE)

    # state: atmosphere. A place or a passage of time, never a person.
    mood = "an empty clinical space at night, one light on, long shadows"
    if re.search(r"\b(?:wait|waited|month|week|year|still|again)\w*\b",
                 (text or "").lower()):
        mood = "an empty waiting area, rows of chairs, one light on, long shadows"
    if re.search(r"\b(?:worse|deteriorat|collaps|fail)\w*\b", (text or "").lower()):
        mood = "a dark clinical corridor receding, cold light at the far end"
    return "%s, %s" % (mood, STYLE)


def brief_for(text, index=0, topic=""):
    """The full brief for one beat."""
    intent, why = classify(text)
    subject = subject_of(text, topic)
    treatment = _TREATMENT_FOR[intent]
    prompt = _prompt_for(intent, subject, text)
    if treatment == "generated" and not prompt:
        treatment = "photograph"
    if treatment != "generated":
        # A prompt on a beat that will not be generated is a loaded gun: the
        # next caller to read the field would use it.
        prompt = None

    return {
        "index": index,
        "text": (text or "").strip(),
        "intent": intent,
        "subject": subject,
        "treatment": treatment,
        "prompt": prompt,
        "forbid": list(NEVER_GENERATE) if intent in ("evidence", "value") else [],
        "why": why,
    }


def shot_list(beats, topic=""):
    """A brief per beat, plus the run of them read as one film.

    The second part matters as much as the first. A shot list where thirty
    consecutive beats all come back "state" is a script problem, not a visual
    one, and it is worth knowing BEFORE eighteen minutes are rendered.
    """
    briefs = [brief_for(t, i, topic) for i, t in enumerate(beats)]

    counts = {}
    for b in briefs:
        counts[b["intent"]] = counts.get(b["intent"], 0) + 1

    longest, cur, prev = 0, 0, None
    for b in briefs:
        cur = cur + 1 if b["intent"] == prev else 1
        prev = b["intent"]
        longest = max(longest, cur)

    return briefs, {"counts": counts, "longest_run": longest,
                    "n": len(briefs),
                    "generated": sum(1 for b in briefs
                                     if b["treatment"] == "generated")}


def split_beats(script, n):
    """Cut a script into n beats on sentence boundaries.

    Splitting on word count alone put half a sentence under one picture and
    half under the next, which is how a shot ends up illustrating a clause.
    """
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", script or "")
                 if s.strip()]
    if not sentences or n <= 0:
        return []
    if len(sentences) <= n:
        return sentences + [""] * (n - len(sentences))

    per = len(sentences) / float(n)
    out, at = [], 0.0
    for i in range(n):
        start, at = int(round(at)), at + per
        out.append(" ".join(sentences[start:max(start + 1, int(round(at)))]))
    return out
