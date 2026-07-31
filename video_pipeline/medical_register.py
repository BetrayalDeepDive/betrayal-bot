"""
Visual register classifier for the clinical-case channel.

Decides, per narration segment, which visual register renders it. Same
greedy-deficit quota algorithm as scene_register.py (Ch1's dark-documentary
classifier), but a completely different register set: there is NO character
animation register here at all. Stickman and silhouette were the two
registers repeatedly rejected on Ch1, and a clinical case has nothing for a
character puppet to do.

    FIGURE     30%  -- the real CC BY figure from the actual paper (this
                       patient's own CT/ECG/histology), with on-screen
                       attribution. The channel's whole differentiator.
    CHART      22%  -- the case's real reported values plotted over time
                       (labs, vitals, temperature curve, drug levels),
                       rendered by the chart code built for Ch5's FRED work
    BOARD      18%  -- differential-diagnosis board: the real candidate
                       diagnoses, eliminated one by one -> investigation_board
    TIMELINE   14%  -- real clinical timeline (day 1 admission, day 4
                       deterioration, day 9 diagnosis) -> motion_graphics
    ANATOMY    10%  -- Wikimedia anatomical diagram / molecular structure of
                       the real organ or drug involved -> real_case_images
    TEXT        6%  -- a real quoted line from the paper's own discussion
                       -> kinetic_text

FIGURE availability is not guaranteed: a given paper may have zero figures
that survive the graphic-content screen in pmc_data.extract_figures().
Rather than emit blank FIGURE segments (the exact "irrelevant filler"
failure that sank stock footage on Ch1), the quota redistributes to ANATOMY
and CHART -- see new_quota(figure_count=...).
"""

FIGURE, CHART, BOARD, TIMELINE, ANATOMY, TEXT = (
    "FIGURE", "CHART", "BOARD", "TIMELINE", "ANATOMY", "TEXT"
)

TARGET_MIX = {
    FIGURE:   0.30,
    CHART:    0.22,
    BOARD:    0.18,
    TIMELINE: 0.14,
    ANATOMY:  0.10,
    TEXT:     0.06,
}

# Real content signals per register. A clinical narrative is unusually rich
# in these -- published case reports describe imaging, values, differentials
# and chronology in consistent, recognisable language.
_FIGURE_KEYWORDS = [
    "imaging", "scan", "ct ", "mri", "x-ray", "radiograph", "ultrasound",
    "echocardiogram", "ecg", "ekg", "electrocardiogram", "eeg", "biopsy",
    "histology", "histological", "micrograph", "staining", "angiogram",
    "revealed on", "showed on", "demonstrated a", "visible on", "confirmed by",
]
_CHART_KEYWORDS = [
    "level", "levels", "count", "concentration", "rose to", "fell to",
    "dropped to", "climbed to", "peaked at", "measured", "mg/dl", "mmol",
    "sodium", "potassium", "creatinine", "haemoglobin", "hemoglobin",
    "white cell", "platelet", "temperature of", "blood pressure",
    "heart rate", "saturation", "titre", "titer", "over the following hours",
]
_BOARD_KEYWORDS = [
    "differential", "considered", "ruled out", "excluded", "suspected",
    "initially thought", "first assumed", "possibilities", "candidate",
    "misdiagnos", "presumed", "working diagnosis", "could not explain",
    "did not fit", "inconsistent with", "investigation", "workup", "work-up",
]
_TIMELINE_KEYWORDS = [
    "day one", "day two", "day three", "day four", "on admission",
    "hours later", "hours after", "days later", "days after", "weeks later",
    "months later", "by the following", "within hours", "within days",
    "over the next", "that evening", "the next morning", "on the fourth day",
    "eventually", "three days before", "two weeks earlier",
]
_ANATOMY_KEYWORDS = [
    "artery", "vein", "ventricle", "atrium", "cortex", "cerebral", "hepatic",
    "renal", "pulmonary", "cardiac", "gastric", "thyroid", "adrenal",
    "pancrea", "spinal", "nerve", "receptor", "enzyme", "metaboli",
    "bloodstream", "membrane", "anatomy", "anatomical", "molecule",
    "compound", "binds to", "mechanism of action",
]


def _hit(text_lower, keywords):
    return any(kw in text_lower for kw in keywords)


def classify_hint(segment_text):
    """
    Real content signal for ONE segment -> the register it's eligible for,
    or None for plain narration with no strong signal.

    A literal quoted line is checked first: it's the least ambiguous signal
    available, exactly as in scene_register.classify_hint().
    """
    text = segment_text or ""
    if '"' in text or '“' in text or '‘' in text:
        return TEXT
    low = text.lower()
    # Order matters: FIGURE before CHART, because "imaging showed a sodium of
    # 121" is fundamentally a figure moment that happens to cite a value,
    # while "sodium rose to 148" with no imaging language is a chart moment.
    if _hit(low, _FIGURE_KEYWORDS):
        return FIGURE
    if _hit(low, _TIMELINE_KEYWORDS):
        return TIMELINE
    if _hit(low, _BOARD_KEYWORDS):
        return BOARD
    if _hit(low, _CHART_KEYWORDS):
        return CHART
    if _hit(low, _ANATOMY_KEYWORDS):
        return ANATOMY
    return None


# How many segments one unit of each register's source data can carry before
# consecutive frames become pixel-identical. Every register here reveals its
# content progressively, so its capacity is set by how many DISTINCT states
# its data has, not by an aesthetic preference.
#
# All of these were measured on full local renders. FIGURE was capped first
# (3 figures were being asked to fill ~18 segments). The rest were not, and
# each one in turn became the register the surplus piled onto: capping CHART
# alone pushed BOARD to 15 segments on a 4-item differential, which is the
# same defect wearing a different name. So the cap is a rule, not a special
# case.
#
# ANATOMY and TEXT are absent from this table because their capacity is not
# a function of the paper's data counts -- both are given explicit ceilings
# below.
SEGMENTS_PER_DATUM = {
    FIGURE:   3.0,    # a held shot plus re-approaches, per real figure
    CHART:    1.5,    # per plotted point
    BOARD:    2.5,    # per candidate diagnosis
    TIMELINE: 2.0,    # per event
}

# ANATOMY's capacity is not set by the paper's data -- it is procedural --
# but it is not infinite either: three motifs, each with a progressive reveal,
# sustain roughly a dozen genuinely distinct frames. Without this it became
# the sink for everything the capped registers refused, and a thin paper
# produced sixteen procedural diagrams in one episode: the same defect the
# caps were added to remove, relocated.
ANATOMY_CAPACITY_SEGMENTS = 12.0

# TEXT shows one real quoted line. A case report yields one quotable
# sentence, so beyond a couple of appearances it is the identical card.
# This MUST match RegisterQuota.text_budget: when TEXT was left uncapped
# here, it was the only register with unbounded headroom, so the whole
# surplus landed on it -- a nominal 29% share that pick() then refused to
# spend, which distorted every other register's deficit for the whole
# episode.
TEXT_CAPACITY_SEGMENTS = 2.0


def _capacity_shares(mix, counts):
    """{register: max share it can sustain}."""
    caps = {}
    for reg, per in SEGMENTS_PER_DATUM.items():
        have = counts.get(reg)
        if have is None or mix.get(reg, 0) <= 0:
            continue
        caps[reg] = min(TARGET_MIX[reg], (have * per) / 60.0)
    if mix.get(ANATOMY, 0) > 0:
        caps[ANATOMY] = ANATOMY_CAPACITY_SEGMENTS / 60.0
    if mix.get(TEXT, 0) > 0:
        caps[TEXT] = TEXT_CAPACITY_SEGMENTS / 60.0
    return caps


def build_mix(figure_count, available=None, chart_points=0, data_counts=None):
    """
    The active target mix for THIS paper.

    Two corrections are applied to TARGET_MIX:

    1. AVAILABILITY. A register the paper cannot render at all is zeroed and
       the mix renormalised. Found by simulating a realistic paper (no chart
       data, one differential, no timeline -- exactly what run 30563819566's
       logs showed): the quota still assigned 21 CHART and 9 TIMELINE
       segments, so HALF the episode would have rendered the identical
       fallback card. Not a crash; sixty seconds of the same slide.

    2. CAPACITY. A register the paper CAN render, but thinly, is capped at
       what its data can actually sustain. Availability alone is not enough --
       a six-point series is "available" and still cannot fill seventeen
       segments without repeating itself exactly.

    Surplus is redistributed ONLY into registers that still have headroom
    under their own cap, iteratively. A single proportional pass was not
    enough: it handed FIGURE's surplus straight back to CHART, pushing CHART
    from its 9-segment cap back up to 12 and reproducing the repeats the cap
    existed to prevent. Whatever no capped register can absorb ends up in
    ANATOMY, which is procedural and has no data to exhaust.
    """
    mix = dict(TARGET_MIX)
    if available:
        # ANATOMY is procedural and therefore always available, so the mix
        # can never collapse to nothing.
        for reg in list(mix):
            if reg != ANATOMY and not available.get(reg, True):
                mix[reg] = 0.0
        live = sum(mix.values())
        if live <= 0:
            return {ANATOMY: 1.0, **{k: 0.0 for k in TARGET_MIX if k != ANATOMY}}
        mix = {k: v / live for k, v in mix.items()}

    counts = dict(data_counts or {})
    counts.setdefault(FIGURE, figure_count)
    if chart_points:
        counts.setdefault(CHART, chart_points)
    caps = _capacity_shares(mix, counts)

    for _ in range(8):
        surplus = 0.0
        for reg, cap in caps.items():
            if mix.get(reg, 0) > cap:
                surplus += mix[reg] - cap
                mix[reg] = cap
        if surplus <= 1e-9:
            break
        # Headroom = uncapped registers at their current share, plus capped
        # ones only up to their cap.
        room = {}
        for reg, share in mix.items():
            if share <= 0:
                continue
            if reg in caps:
                if caps[reg] - share > 1e-9:
                    room[reg] = caps[reg] - share
            else:
                room[reg] = float("inf")
        finite = {k: v for k, v in room.items() if v != float("inf")}
        infinite = [k for k, v in room.items() if v == float("inf")]
        if infinite:
            base = sum(mix[k] for k in infinite) or 1.0
            for k in infinite:
                mix[k] += surplus * (mix[k] / base)
            break
        total_room = sum(finite.values())
        take = min(surplus, total_room)
        if total_room > 1e-9:
            for k, v in finite.items():
                mix[k] += take * (v / total_room)
        residual = surplus - take
        if residual > 1e-9:
            # EVERY register is now at capacity and the episode still has
            # segments left. This means the paper is genuinely too thin to
            # fill it -- three figures, one six-point series, four
            # differentials and six events cannot produce fifty-nine
            # distinct frames, and no scheduling rule can invent more.
            #
            # The residual is therefore spread across all live registers in
            # proportion to their caps, NOT dumped on one of them. Dumping it
            # on ANATOMY (the previous behaviour) concentrated every repeat
            # into one visual treatment -- sixteen procedural diagrams in a
            # row-ish. Repetition spread thinly across six registers is far
            # less visible than the same amount piled into one.
            live = {k: caps.get(k, mix[k]) for k in mix if mix[k] > 0}
            base = sum(live.values()) or 1.0
            for k, w in live.items():
                mix[k] += residual * (w / base)
            break
    return mix


class RegisterQuota:
    """
    Per-episode (never persisted across episodes) running tracker. Create one
    fresh per video via new_quota(), feed every segment in order via pick().

    Keyword signals decide which register a segment is *eligible* for, so a
    line about imaging genuinely becomes a figure shot. A running cumulative
    deficit then breaks ties and guarantees the realised mix converges on
    the target across the episode regardless of how the source paper happens
    to be worded -- the same largest-remainder greedy scheduling used in
    scene_register.py, including the 1.15x saturation cap that fixed
    front-loading there.
    """

    # Registers that can always be rendered from the case's own material, so
    # they are safe to assign to a segment with no keyword signal. TEXT is
    # absent by design: it needs a real quotation to display (see _neediest).
    FILLABLE = (FIGURE, CHART, BOARD, TIMELINE, ANATOMY)

    def __init__(self, total_segments, figure_count=0, available=None,
                 chart_points=0, data_counts=None):
        self.total = max(1, total_segments)
        self.figure_count = figure_count
        self.mix = build_mix(figure_count, available, chart_points, data_counts)
        self.counts = {k: 0 for k in self.mix}
        self.done = 0
        self.last = None
        # 21 identical segments in a row was measured on a 6-figure
        # paper -- roughly five straight minutes of one visual. A
        # documentary changes what you are looking at.
        self.run_len = 0
        self.MAX_RUN = 2
        # TEXT is reachable by deficit-fill ONLY when the paper actually
        # supplied a quotation, and even then only a couple of times.
        #
        # Measured on a full local render: TEXT fired 0 times out of 59.
        # classify_hint() only returns TEXT when the narration contains a
        # literal quote character, and clinical narration written for TTS
        # rarely does -- so a register worth 6% of the mix was dead, and the
        # episode ran on five registers instead of six. Simply adding TEXT to
        # FILLABLE is the wrong fix in the other direction: there is one
        # quote, so deficit-filling would show the identical card four or
        # five times. Capped instead.
        _has_quote = bool(available.get(TEXT, False)) if available else False
        self.text_budget = int(TEXT_CAPACITY_SEGMENTS) if _has_quote else 0

    def _deficit(self, register):
        return self.mix[register] * self.total - self.counts[register]

    def _neediest(self, exclude=None):
        """
        Register with the largest cumulative deficit.

        TEXT is excluded from deficit-filling (FILLABLE below). FIX found by
        running a real 61-segment episode through this: TEXT was being handed
        to segments with no quotation in them at all, because it was simply
        the register furthest behind quota. A kinetic-quote card with nothing
        to quote is the same class of defect as a FIGURE segment on a paper
        with no figures -- it would have to invent something to display.
        TEXT is now only ever reachable via a real quote signal in
        classify_hint(); its unused share is absorbed by the registers that
        can always be rendered from the case's own data.
        """
        fillable = list(self.FILLABLE)
        if self.counts.get(TEXT, 0) < self.text_budget and self.mix.get(TEXT, 0) > 0:
            fillable.append(TEXT)
        eligible = [r for r in fillable
                    if self.mix.get(r, 0) > 0 and r != exclude]
        if not eligible:
            eligible = [r for r in fillable if self.mix.get(r, 0) > 0]
        if not eligible:                      # pathological: nothing fillable
            eligible = [r for r in self.mix if self.mix[r] > 0]
        return max(eligible, key=self._deficit)

    def pick(self, segment_text, force_switch=False):
        """
        Register for this segment.

        force_switch=True means a real audio cue or chapter boundary lands
        here, so returning the previous segment's register would produce a
        beat with no visual change at all. Mirrors the audio_cue_hit
        behaviour in scene_register.pick().
        """
        hint = classify_hint(segment_text)
        chosen = None

        if hint and self.mix.get(hint, 0) > 0:
            # Respect the real content signal only while that register still
            # has budget. 1.15x tolerance, matching scene_register.
            if self.counts[hint] < self.mix[hint] * self.total * 1.15:
                chosen = hint

        if chosen is None:
            chosen = self._neediest()

        if force_switch and chosen == self.last:
            chosen = self._neediest(exclude=self.last)

        # Hard cap on consecutive identical registers. Measured before run 5:
        # a 6-figure paper produced 21 FIGURE segments back to back, about
        # five unbroken minutes of one visual treatment.
        if chosen == self.last:
            if self.run_len >= self.MAX_RUN:
                alt = self._neediest(exclude=self.last)
                if alt != self.last:
                    chosen = alt

        self.counts[chosen] += 1
        self.done += 1
        self.run_len = self.run_len + 1 if chosen == self.last else 1
        self.last = chosen
        return chosen

    def reveal(self, register):
        """
        (occurrence, expected_total) for the register just picked, both
        counted IN THAT REGISTER'S OWN SEQUENCE.

        Every renderer varies its output on something the caller supplies:
        the progressive reveal on `progress`, the ANATOMY motif on `variant`,
        which figure to show on the segment index. All of those used to be
        derived from the GLOBAL segment position -- and a register that
        appears on twelve of fifty-nine segments moves through a global
        0..1 ramp in twelve coarse jumps that mostly land on the same value.

        Rendering a full episode made the consequence obvious and uniform:
        CHART segments 3 and 8 were the same frame, BOARD 4/9/20 the same
        frame, TIMELINE 2 and 6 the same frame, and FIGURE 0/21/24 all showed
        Figure 1 because 0, 21 and 24 are all ≡ 0 (mod 3). Five separate
        symptoms, one cause.

        Counting within the register's own run makes each of its appearances
        advance by exactly one step, which is what a progressive reveal was
        supposed to mean in the first place.
        """
        occurrence = self.counts.get(register, 1)          # 1-based, post-pick
        expected = max(1, int(round(self.mix.get(register, 0) * self.total)))
        return occurrence, max(expected, occurrence)

    def realised_mix(self):
        """Actual proportions so far -- for logging and the video gate."""
        if not self.done:
            return {k: 0.0 for k in self.mix}
        return {k: v / self.done for k, v in self.counts.items()}


def available_from_case(case):
    """
    What this specific paper can actually render, derived from the case dict
    the pipeline already builds. ANATOMY is procedural so it is always True.
    """
    case = case or {}
    return {
        FIGURE:   bool(case.get("figures")),
        CHART:    bool((case.get("chart_data") or {}).get("labels")),
        BOARD:    bool(case.get("differentials")),
        TIMELINE: len(case.get("timeline") or []) >= 2,
        TEXT:     bool((case.get("quote") or "").strip()),
        ANATOMY:  True,
    }


def new_quota(total_segments, figure_count=0, case=None, available=None):
    """Fresh per-episode tracker. Always call this, never reuse one."""
    if available is None and case is not None:
        available = available_from_case(case)
    c = case or {}
    counts = {
        FIGURE:   len(c.get("figures") or []) or figure_count,
        CHART:    len((c.get("chart_data") or {}).get("labels") or []),
        BOARD:    len(c.get("differentials") or []),
        TIMELINE: len(c.get("timeline") or []),
    }
    return RegisterQuota(total_segments, figure_count=figure_count,
                         available=available, data_counts=counts)
