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


def build_mix(figure_count, available=None):
    """
    available: optional {register: bool} of what this paper can actually
    render. A register with no data is set to zero share and its budget is
    redistributed, instead of being scheduled and silently degrading.

    Found before run 5 by simulating a realistic paper (no chart data, one
    differential, no timeline -- exactly what run 30563819566's logs showed):
    the quota still assigned 21 CHART and 9 TIMELINE segments, so HALF the
    episode would have rendered the identical fallback card. That is not a
    visible crash; it is sixty seconds of the same slide, repeatedly, which
    is why it survived every check until it was simulated.
    """
    """
    Active target mix given how many usable figures this paper actually has.

    Real papers vary from zero usable figures (all screened out as graphic,
    or none present) to a dozen. Asking for 30% FIGURE segments when only
    two real figures exist would mean re-showing the same image ~18 times in
    one episode. The cap allows each real figure to carry roughly three
    segments (a held shot plus depth-motion re-approaches), and any
    unusable share is redistributed 60/40 to ANATOMY and CHART -- both of
    which are always available, since anatomy comes from Wikimedia and
    charts are generated from the case's own reported values.
    """
    mix = dict(TARGET_MIX)
    if available:
        # Zero anything with no data, then renormalise over what is left.
        # ANATOMY is procedural and therefore always available, so the mix
        # can never collapse to nothing.
        for reg in list(mix):
            if reg != ANATOMY and not available.get(reg, True):
                mix[reg] = 0.0
        live = sum(mix.values())
        if live <= 0:
            mix = {ANATOMY: 1.0, **{k: 0.0 for k in TARGET_MIX if k != ANATOMY}}
        else:
            mix = {k: v / live for k, v in mix.items()}
    if figure_count <= 0:
        spare = mix[FIGURE]
        mix[FIGURE] = 0.0
        mix[ANATOMY] += spare * 0.6
        mix[CHART] += spare * 0.4
        return mix
    # Roughly 60 segments/episode; ~3 segments per real figure is the
    # comfortable ceiling before repetition becomes visible.
    max_share = min(TARGET_MIX[FIGURE], (figure_count * 3) / 60.0)
    spare = mix[FIGURE] - max_share
    if spare > 0:
        mix[FIGURE] = max_share
        mix[ANATOMY] += spare * 0.6
        mix[CHART] += spare * 0.4
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

    def __init__(self, total_segments, figure_count=0, available=None):
        self.total = max(1, total_segments)
        self.figure_count = figure_count
        self.mix = build_mix(figure_count, available)
        self.counts = {k: 0 for k in self.mix}
        self.done = 0
        self.last = None
        # 21 identical segments in a row was measured on a 6-figure
        # paper -- roughly five straight minutes of one visual. A
        # documentary changes what you are looking at.
        self.run_len = 0
        self.MAX_RUN = 3

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
        eligible = [r for r in self.FILLABLE
                    if self.mix.get(r, 0) > 0 and r != exclude]
        if not eligible:
            eligible = [r for r in self.FILLABLE if self.mix.get(r, 0) > 0]
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
    return RegisterQuota(total_segments, figure_count=figure_count,
                         available=available)
