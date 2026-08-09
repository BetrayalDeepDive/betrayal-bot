"""
Choose the stock photograph that actually fits what the narration is saying.

WHY THIS EXISTS
---------------
The library already held the right pictures and nothing was reading them.

stock_library.pick() scores a photograph by how many of its tags appear in the
caller's search words, which is the correct idea. But the SCENE renderer was
not passing it the narration. It rotated through a fixed list of twelve
generic phrases -- "hospital corridor empty", "medical chart on a clipboard" --
indexed by the segment number. So a card over "the clot travelled from the
calf to the lung in under a minute" could get a photograph of a waiting room,
and the next episode would get the same waiting room in the same slot.

That is the "generic" complaint in its purest form: not a missing picture, a
picture chosen without reference to the words it sits under.

WHAT THIS DOES
--------------
Three things the round-robin could not.

1. READS THE NARRATION. A vocabulary maps what a clinical sentence talks about
   to what a photograph of it looks like -- "embolism" and "clot" reach for
   lung and chest imaging, "discharged" and "sent home" reach for a corridor
   and an exit, "collapsed" and "resuscitation" reach for a paramedic and ECG
   leads. The case topic is folded in too, so an episode about the brain
   prefers the brain scan over the blood tube for its whole length.

2. WEIGHTS RARE TAGS ABOVE COMMON ONES. Plain overlap counting treats a match
   on "hospital" (in a third of the library) the same as a match on
   "paramedic" (in one photograph). The rare tag is the one carrying the
   meaning, so matches are weighted by how unusual the tag is across the
   library -- the same reasoning as inverse document frequency, computed on
   the manifest that is already there.

3. NEVER REPEATS INSIDE ONE EPISODE UNTIL IT HAS TO. A perfect match shown
   four times reads worse than a decent match shown once. Photographs already
   used this episode are penalised, not banned, so a small library still fills
   a long episode -- it just exhausts its variety before it starts recycling.

It degrades honestly: with no tags, no vocabulary hit and no library it
returns None and the caller falls back exactly as before.
"""
import os
import re


# What a clinical sentence is ABOUT -> what a photograph of it looks like.
#
# Written from the vocabulary case reports actually use, and pointed at the
# tags the library actually carries (see stock_library/manifest.json), so a
# hit here reaches a real photograph rather than an aspiration.
VISUAL_VOCAB = {
    # imaging
    ("scan", "scanned", "imaging", "ct", "mri", "radiograph", "x-ray",
     "tomography", "angiogram", "ultrasound"):
        "mri ct scan scanner radiology imaging film lightbox",
    # A LESION IS NOT AUTOMATICALLY A BRAIN LESION, AND BLEEDING IS NOT A SCAN.
    #
    # This entry used to end "... brain slices ...", which meant every one of
    # these words resolved to BRAIN imagery. The delivered episode narrated
    # "vaginal bleeding that had lasted three days" over a sheet of brain CT
    # slices, scoring 18.0 — the highest match in the library — because "bleed"
    # was hard-wired to a brain scan.
    #
    # A mass or a nodule can be anywhere in the body, so the tags stay generic
    # imaging and the dedicated brain entry below picks up the cases that are
    # actually about the brain.
    #
    # "haemorrhage" stays here and "bleeding" moves to blood, because they are
    # not synonyms in practice. Haemorrhage is what a radiologist writes about
    # something visible on a scan; bleeding is what the patient reports. Sorting
    # them by which word was used gets both cases right:
    #
    #     "vaginal bleeding that had lasted three days"  -> blood, lab
    #     "a brain haemorrhage was found on the CT"      -> brain imaging
    #
    # Keeping them together is what put brain CT slices under a gynaecological
    # symptom, at the highest match score in the library.
    ("lesion", "mass", "tumour", "tumor", "nodule", "opacity", "infarct",
     "haemorrhage", "hemorrhage"):
        "mri ct scan radiology film lightbox imaging",
    # the brain
    ("brain", "cerebral", "cortex", "neurological", "seizure", "stroke",
     "meningitis", "encephalitis", "consciousness"):
        "brain mri ct scan slices radiology film",
    # blood and the lab
    ("blood", "bloods", "bleed", "bleeding",
     "serum", "plasma", "haemoglobin", "hemoglobin",
     "platelet", "white cell", "sodium", "potassium", "creatinine",
     "sample", "specimen", "culture", "serology", "assay"):
        "blood sample tube pipette laboratory gloved hand",
    ("laboratory", "lab", "biochemistry", "haematology", "hematology",
     "analysed", "analyzed", "reported", "result", "results", "panel"):
        "laboratory blood test pipette gloved hand",
    ("clot", "thrombus", "thrombosis", "embolism", "embolus", "embolic",
     "artery", "arterial", "vein", "venous", "vessel", "circulation",
     "lung", "lungs", "pulmonary", "breathless", "oxygen", "saturation"):
        "chest lung ct scan radiology film scanner imaging",
    # the body, examined
    ("examination", "examined", "palpation", "auscultation", "abdomen",
     "chest", "limb", "arm", "leg", "skin", "rash", "swelling", "tender"):
        "clinical examination hands arm patient",
    # emergency
    ("collapsed", "collapse", "arrest", "resuscitation", "resuscitated",
     "ambulance", "paramedic", "emergency", "crash", "defibrillat",
     "intubated", "unresponsive", "critical"):
        "paramedic ecg leads emergency patient resuscitation",
    ("ecg", "ekg", "electrocardiogram", "rhythm", "heart rate", "cardiac",
     "arrhythmia", "tachycardia", "bradycardia"):
        "paramedic ecg leads emergency resuscitation",
    # the places
    ("admitted", "admission", "ward", "inpatient", "bed", "overnight",
     "night", "hourly", "observation", "monitored"):
        "hospital corridor ward hallway",
    ("discharged", "sent home", "went home", "outpatient", "follow up",
     "follow-up", "referred", "referral", "appointment", "clinic"):
        "clinic waiting room chairs corridor door examination",
    ("waiting", "waited", "queue", "hours later", "days later", "returned"):
        "clinic corridor chairs waiting area",
    ("theatre", "operating", "surgery", "surgical", "operated", "resected",
     "biopsy", "biopsied"):
        "hospital corridor ward theatre",
    # the eye, and other close detail
    ("eye", "eyes", "pupil", "iris", "vision", "visual", "retina", "ocular",
     "blurred", "sight"):
        "human eye macro iris pupil close up",
}

# Tags that describe mood rather than subject. They break ties; they never win
# on their own, because a dark corridor over a sentence about a blood result
# is atmosphere standing in for relevance -- the exact substitution that made
# the old stock-footage era fail.
_MOOD = {"dark", "bright", "empty", "wide", "night", "close", "up", "macro"}


def terms_for(segment_text, topic="", extra="", flat=True, topic_rank=6):
    # topic_rank exists because the episode topic fires on EVERY segment. An
    # episode titled "eleven months of normal scans" put the word "scans" into
    # all 106 cards, so a line about a pupil not reacting to light was scored
    # against imaging terms and got an MRI film instead of the eye macro. The
    # topic should tilt a close call, never decide one, so its terms enter at
    # a fixed low rank behind anything the segment itself said.
    """The words this segment would search for. Most specific first.

    With flat=False, each word comes back paired with the RANK of the
    vocabulary entry it came from (0 = the entry whose trigger matched most
    specifically). Rank matters more than it looks: "she was sent home from
    the emergency department" fires both the discharge entry (on the phrase
    "sent home") and the emergency entry (on the word "emergency"), and the
    paramedic photograph happens to carry six of the emergency entry's tags
    against the waiting room's four. On a flat count the resuscitation shot
    wins a sentence about being sent home. Rank is what stops that.

    Specificity is measured on the TRIGGER that matched, not on where the
    entry happens to sit in the table. "She was sent home from the emergency
    department" hits both the emergency entry (on the single word "emergency")
    and the discharge entry (on the phrase "sent home") -- and it is plainly
    about being sent home. The longer phrase matched, so its terms lead.
    """
    said = " ".join(x for x in (segment_text, extra) if x).lower()
    background = (topic or "").lower()

    def _fire(blob):
        out = []
        for triggers, visual in VISUAL_VOCAB.items():
            spec = 0
            for t in triggers:
                if re.search(r"\b%s" % re.escape(t), blob):
                    spec = max(spec, len(t.split()) * 10 + len(t))
            if spec:
                out.append((spec, visual))
        out.sort(key=lambda x: -x[0])
        return out

    hits, seen = [], set()
    for rank, (_spec, visual) in enumerate(_fire(said)):
        for w in visual.split():
            if w not in seen:
                seen.add(w)
                hits.append((w, rank))
    # Whatever the topic adds enters behind everything the segment said.
    for _spec, visual in _fire(background):
        for w in visual.split():
            if w not in seen:
                seen.add(w)
                hits.append((w, topic_rank))
    return [w for w, _ in hits] if flat else hits


def _tag_weights(photos):
    """Rarer tag, higher weight. Plain counting made 'hospital' decisive."""
    freq = {}
    for p in photos:
        for t in set((p.get("tags") or "").lower().split()):
            freq[t] = freq.get(t, 0) + 1
    n = max(1, len(photos))
    # 1.0 for a tag on one photograph, falling toward 0 as it approaches
    # being on all of them.
    return {t: 1.0 - (c - 1) / float(n) for t, c in freq.items()}


def best(role, segment_text, topic="", used=(), extra="", min_score=0.0):
    """The library photograph that best fits this segment, or None.

    `used` is what this episode has already shown -- penalised so variety is
    spent before anything is repeated, rather than banned, so a small library
    can still carry a long episode.

    Returns (path, why) where `why` is the matched tags, for the log. A caller
    that only wants the path can ignore it.
    """
    try:
        import stock_library as sl
    except Exception:
        return None, ""

    photos = [p for p in sl.manifest()["photos"]
              if p.get("role") == role
              and os.path.exists(os.path.join(sl.LIB, p["file"]))]
    if not photos:
        return None, ""

    ranked = terms_for(segment_text, topic, extra, flat=False)
    if not ranked:
        return None, ""
    weights = _tag_weights(photos)
    want_set = {w for w, _ in ranked}
    # A term from the entry that matched most specifically counts for far more
    # than one from a broader entry that merely also fired. The decay is steep
    # on purpose: a shallow bonus let a photograph win on tag COUNT alone.
    order = {}
    for w, rank in ranked:
        order[w] = max(order.get(w, 0.0), 3.0 / (1.0 + 2.0 * rank))

    scored = []
    for p in photos:
        tags = set((p.get("tags") or "").lower().split())
        shared = tags & want_set
        subject = shared - _MOOD
        if not subject:
            continue                    # mood alone is not relevance
        s = sum(weights.get(t, 0.5) * order.get(t, 1.0) for t in subject)
        s += 0.15 * len(shared & _MOOD)
        if p["file"] in used:
            s -= 2.0                    # seen already: strongly deprioritised
        scored.append((s, p, sorted(subject)))

    if not scored:
        return None, ""
    scored.sort(key=lambda x: (-x[0], x[1]["file"]))
    top, photo, matched = scored[0]
    if top < min_score:
        return None, ""
    best.last_score = top
    return os.path.join(sl.LIB, photo["file"]), " ".join(matched)


best.last_score = 0.0


def gaps(role, wanted_terms, threshold=1):
    """Vocabulary words this role has little or no photograph for.

    Feeds harvest() so the library grows toward what episodes actually ask
    for, instead of toward a fixed list written once. A term nothing matches
    is the one worth spending an API call on.
    """
    try:
        import stock_library as sl
    except Exception:
        return list(wanted_terms)
    photos = [p for p in sl.manifest()["photos"] if p.get("role") == role]
    have = {}
    for p in photos:
        for t in set((p.get("tags") or "").lower().split()):
            have[t] = have.get(t, 0) + 1
    return [w for w in wanted_terms
            if have.get(w.lower(), 0) < threshold and w.lower() not in _MOOD]


# Preference order when a card can legitimately use any photograph. The roles
# were invented for THUMBNAILS -- scene is the background, evidence is the
# inset panel, hero fills the frame -- and an episode's full-bleed SCENE card
# is none of those. It just wants the best picture for the sentence.
#
# So a line about a sodium result should be able to reach the blood tube filed
# under `evidence`, and a line about a pupil should reach the eye macro filed
# under `hero`. Restricting the card to role="scene" put a corridor under both.
ANY_ROLES = ("scene", "evidence", "hero")


def best_any(segment_text, topic="", used=(), extra="", roles=ANY_ROLES):
    """Best photograph for this segment across every role.

    Returns (path, why, role). The role each candidate came from breaks ties
    only: `scene` first, because a card that fills the frame usually wants a
    place rather than a close-up, and the close-up wins whenever it is the
    genuinely better match rather than merely available.
    """
    best_hit = (None, "", "", -1e9)
    for i, role in enumerate(roles):
        path, why = best(role, segment_text, topic=topic, used=used, extra=extra)
        if not path:
            continue
        # Compare on the SCORE each role's search actually produced, not on
        # how many tags happened to match. Counting tags let a CT film beat
        # the eye macro on a line about a pupil, because "mri ct scan
        # radiology film lightbox" is six words and "eye iris pupil human" is
        # four -- while the eye photograph was the obviously right answer.
        score = best.last_score - 0.15 * i
        if score > best_hit[3]:
            best_hit = (path, why, role, score)
    return best_hit[0], best_hit[1], best_hit[2]
