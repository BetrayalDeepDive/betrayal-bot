#!/usr/bin/env python3
"""
Pre-run audit for No Known Cause (Ch1).

WHY THIS IS EXECUTABLE AND NOT A CHECKLIST
------------------------------------------
Every claim below is a real assertion against real code. A checklist in a
document rots the moment someone edits a module; this fails loudly instead.
Three of the defects found across runs 1-3 were things I had previously
believed were fine, so "I checked it" is not evidence -- this is.

Run:  python3 tools/audit_no_known_cause.py
Exit: 0 = all checks pass, 1 = at least one failed.

Checks are grouped by what they protect:
  A  IDENTITY       nothing from the retired channel reaches a viewer
  B  SOURCING       topics and cases come from the same real paper
  C  POLICY         medical rules hold, and don't fire on innocent prose
  D  SCORING        quality is measured, length is not
  E  VISUALS        the six registers can actually render
  F  INTEGRATION    the pieces agree with each other
"""
import re
import sys
import json
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "video_pipeline"))

ROOT = pathlib.Path(__file__).resolve().parent.parent
PASS, FAIL = [], []


def check(group, name, condition, detail=""):
    (PASS if condition else FAIL).append((group, name, detail))


def read(rel):
    return (ROOT / rel).read_text()


# ── A. IDENTITY ────────────────────────────────────────────────────────
def audit_identity():
    import growth_engine as ge
    import shorts_reels_engine as se
    import thumbnail_formats as tf
    import product_manuscript as pm
    import topic_scoring as ts
    import site_generator as sg

    ch = ge.CHANNELS["betrayal_deepdive"]
    check("A", "growth engine display name", ch["name"] == "No Known Cause", ch["name"])
    check("A", "growth engine handle", ch["handle"] == "@NoKnownCauseTV", ch["handle"])
    check("A", "comment voice profile exists",
          ch["cta_style"] in ge.COMMENT_VOICE, ch["cta_style"])
    check("A", "every channel has a voice profile",
          all(c["cta_style"] in ge.COMMENT_VOICE for c in ge.CHANNELS.values()),
          "Ch4/Ch5 previously fell through to dark_horror")
    check("A", "Short watermark",
          se.CHANNEL_CONFIGS["betrayal_deepdive"]["watermark"] == "@NoKnownCauseTV")
    check("A", "thumbnail format pool is clinical",
          "silhouette_dramatic" not in tf.CHANNEL_PREFERRED_FORMATS["No Known Cause"])

    # Cross-promo in the other four channels must name the live handle.
    for chan in ("evidence_room", "control_files", "archive", "collapse_index"):
        src = read(f"channels/{chan}/{chan}_pipeline.py")
        m = re.search(r"CROSS_PROMO = \{(.*?)\n\}\n", src, re.S)
        ns = {}
        exec("CROSS_PROMO = {" + m.group(1) + "\n}", ns)
        handles = {"@" + l.split("youtube.com/@")[1].strip()
                   for e in ns["CROSS_PROMO"].values()
                   for l in (e["main"] + e["short"]).splitlines()
                   if "NoKnownCause" in l}
        check("A", f"{chan} promotes the live handle",
              handles == {"@NoKnownCauseTV"}, str(handles))
        check("A", f"{chan} has no dead Ch1 handle",
              "youtube.com/@BetrayalDeepDive" not in src)

    # No product or affiliate monetisation on a medical channel.
    check("A", "no product route for Ch1",
          pm.CHANNEL_TO_PRODUCT.get("betrayal_deepdive") is None
          and ts.PRODUCT_ROUTES.get("betrayal_deepdive") is None
          and sg.PRODUCT_ROUTES.get("betrayal_deepdive", {}) == {})
    cp = read("channels/betrayal_deepdive/clinical_pipeline.py")
    check("A", "affiliate block not emitted (BetterHelp under a case study)",
          "affiliate_block = build_affiliate_block" not in cp)

    # Upload category must be Education, which Studio cannot override.
    check("A", "uploads use Education (27), not People & Blogs (22)",
          '"categoryId": "22"' not in cp and '"categoryId": "27"' in cp)


# ── B. SOURCING ────────────────────────────────────────────────────────
def audit_sourcing():
    import pmc_data as P
    cp = read("channels/betrayal_deepdive/clinical_pipeline.py")

    check("B", "topics come from PMC, not the LLM",
          "get_real_cases(niche_name" in cp and "case_to_topic(attempt_case)" in cp)
    check("B", "viral intel is NOT a topic source",
          'intel.get("fresh_topic_ideas"' not in cp,
          "this is how Sylvia Plath became a clinical topic")
    check("B", "case is threaded into script generation",
          "preselected_case=attempt_case" in cp,
          "prevents topic and case being different papers")
    check("B", "all 10 niches have a PMC query",
          len(P.NICHE_PMC_QUERIES) == 10, str(len(P.NICHE_PMC_QUERIES)))
    check("B", "every niche excludes unshowable papers",
          all("NOT (" in q for q in P.NICHE_PMC_QUERIES.values()))
    check("B", "figure fetch has a fallback URL",
          len(P.FIGURE_URL_PATTERNS) >= 2, str(len(P.FIGURE_URL_PATTERNS)))

    # Licensing is the one thing that must never regress.
    for lic, want in (("CC BY", True), ("CC BY-NC", False), ("CC BY-ND", False),
                      ("CC BY-NC-ND", False), ("CC0", True), ("", False)):
        check("B", f"licence {lic or '(empty)'} -> {want}",
              P._license_ok(lic) == want)


# ── C. POLICY ──────────────────────────────────────────────────────────
def audit_policy():
    from medical_policy_gate import check_script, build_disclaimer_block
    CIT = "Smith J. BMJ Case Rep. 2020. CC BY."

    must_pass = [
        "The enzyme was breaking down the drug faster than expected.",
        "Protein unfolding in the cytosol triggered the cascade.",
        "By the end of that week, the sodium had normalised.",
        "What you are looking at right now is the admission scan.",
    ]
    must_block = [
        "This is breaking news out of Florida tonight.",
        "The outbreak is unfolding as officials scramble.",
        "You should stop taking your medication immediately.",
        "This is the miracle cure for the condition.",
        "If you have these symptoms, see your doctor about your condition.",
    ]
    for t in must_pass:
        ok, v = check_script(t, citation=CIT)
        blocks = [x for x in v if x["severity"] == "block"]
        check("C", f"clinical prose passes: {t[:40]}", not blocks,
              str([b["matched"] for b in blocks]))
    for t in must_block:
        ok, v = check_script(t, citation=CIT)
        check("C", f"violation blocked: {t[:40]}",
              any(x["severity"] == "block" for x in v))

    check("C", "missing citation blocks",
          any(x["rule"] == "rule2_missing_citation"
              for x in check_script("A case occurred.", citation="")[1]))
    check("C", "disclaimer wording matches the Studio About text",
          "not medical advice, diagnosis, or treatment guidance"
          in build_disclaimer_block(""))

    # A rehook marker must never be a policy trap.
    from script_scoring import _REHOOK_MARKERS
    traps = [m for m in _REHOOK_MARKERS
             if any(x["severity"] == "block"
                    for x in check_script(f"The finding was odd. {m} the sequence.",
                                          citation=CIT)[1])]
    check("C", "no rehook marker trips the policy gate", not traps, str(traps))


# ── D. SCORING ─────────────────────────────────────────────────────────
def audit_scoring():
    from clinical_quality import (score_script, clinical_specificity,
                                  DURATION_FLOOR_WORDS, duration_check)
    from script_scoring import score_killer_hook, TOPIC_CLARITY_GATE_MIN

    DENSE = ("A fifty-one-year-old man presented after drinking a litre of soy sauce. "
             "His serum sodium reached one hundred and seventy-one milliequivalents "
             "per litre. On the second day imaging showed a haemorrhage. ") * 8

    # Length must not buy quality.
    good_short = score_script(1300, 0, DENSE, 8.5, 9.0, 8.5)[0]
    bad_long = score_script(2000, 0, DENSE, 6.6, 7.0, 7.5)[0]
    check("D", "excellent short outscores mediocre long",
          good_short > bad_long, f"{good_short} vs {bad_long}")
    check("D", "excellent short can pass 8.5", good_short >= 8.5, str(good_short))

    # The floor is absolute.
    _, ok, rep = score_script(1100, 0, DENSE, 9.0, 9.5, 9.5)
    check("D", "below-floor blocked despite high quality",
          not ok and "duration floor" in rep["blocked_on"])
    check("D", "duration floor is ~10 min", DURATION_FLOOR_WORDS == 1250)

    # Specificity must read spelled-out numbers (TTS writes words, not digits).
    spoken = ("A fifty-one-year-old man received six litres of fluid. His sodium "
              "reached one hundred and seventy-one milliequivalents per litre. ") * 8
    sc, counts = clinical_specificity(spoken)
    check("D", "specificity reads spelled-out numbers",
          counts["values"] > 0 and counts["ages"] > 0,
          f"values={counts['values']} ages={counts['ages']}")
    # and must not be gamed by length
    a, _ = clinical_specificity(DENSE)
    b, _ = clinical_specificity(DENSE * 3)
    check("D", "specificity is length-independent", abs(a - b) < 0.01)

    check("D", "clarity gate lowered to 8.0", TOPIC_CLARITY_GATE_MIN == 8.0)

    # The hook must be winnable by a compliant clinical cold open.
    HOOK = ("A fifty-one-year-old woman lost the use of both kidneys in nine days. "
            "Her scans were normal. Every test came back clean. What caused it?"
            + " The team reviewed the findings." * 40)
    hs, hissues = score_killer_hook(HOOK)
    check("D", "clinical hook can reach 10.0", hs >= 9.5, f"{hs} {hissues}")


def audit_script_craft():
    """
    The mechanism that IMPROVES a script, not the ones that judge it.
    """
    cp = read("channels/betrayal_deepdive/clinical_pipeline.py")
    code = "\n".join(l for l in cp.splitlines() if not l.lstrip().startswith("#"))

    check("D", "stage rewrite runs at the lengths this channel produces",
          "if wc >= DURATION_FLOOR_WORDS:" in code,
          "gated at MIN_WORDS (1900) it never ran on a 1,600-word clinical "
          "episode -- the one tool for raising craft was unreachable")
    check("D", "stage targets are proportions, not the retired absolutes",
          "[110, 210, 260, 420, 170, 680, 190]" not in code
          and "_SHAPE" in code,
          "absolute targets summing to 2,040 words docked every stage of "
          "every clinical script for being 'under target'")
    check("D", "stage names describe a clinical case, not a crime",
          '"FALSE RESOLUTION"' not in code and '"THE PATIENT"' in code,
          "the rewrite prompt feeds the stage name to the model as its "
          "purpose; a true-crime beat sheet steers it back to the retired "
          "format")
    check("D", "stage specificity uses the clinical detector",
          "clinical_specificity(stext)" in code,
          r"the digit regex \d+ matched almost nothing, because the "
          "prompt requires numbers spelled out for TTS")
    check("D", "the GENERATION prompt describes a clinical case",
          "STAGE 5 — FALSE RESOLUTION" not in cp
          and "STAGE 6 — THE REVERSAL" in cp,
          "this prompt is what actually shapes the script")
    check("D", "no true-crime trigger vocabulary reaches the writer",
          "COMPLICITY (s10)" not in cp and "INSTITUTIONAL (s7)" not in cp
          and "single most disturbing fact —" not in cp,
          "instructing a writer to imply COMPLICITY over a documented "
          "medical case is unsafe, not just off-format")
    check("D", "the prompt forbids blaming clinicians",
          "blaming any clinician" in cp)
    check("D", "review section labels match the scorer and the act cards",
          '"THE REVERSAL"' in cp and "_stage_names_ch1" in cp
          and '"COLD OPEN","THE BEFORE"' not in cp,
          "EDIT feedback could not resolve to a section that no longer exists")
    check("D", "rewrite prompts name the stage's real problems",
          "_problem_summary(stext" in code,
          "a fixed problem string on every rewrite is a re-roll, not a fix")

    # Sentence-length rule, measured on real documentary prose.
    sys.path.insert(0, str(ROOT / "tools"))
    from local_episode_render import NARRATION
    m = re.search(r"^MAX_SENTENCE_WORDS = (\d+)", cp, re.M)
    check("D", "sentence cap defined once, as a constant", m is not None)
    cap = int(m.group(1)) if m else 13
    sents = [x for x in re.split(r"(?<=[.!?])\s+", NARRATION) if x.strip()]
    over = [x for x in sents if len(x.split()) > cap]
    check("D", "the sentence cap does not fight ordinary documentary prose",
          len(over) / max(1, len(sents)) < 0.35,
          f"{len(over)}/{len(sents)} sentences of a realistic clinical "
          f"episode exceed {cap} words")
    check("D", "sentence-length VARIETY is measured, not just a ceiling",
          "no rhythm" in cp,
          "uniform sentence length reads as machine prose at any length")


# ── E. VISUALS ─────────────────────────────────────────────────────────
def audit_visuals():
    import thumbnail_engine_v2 as te
    from medical_register import TARGET_MIX, new_quota

    NICHES = ["toxicology_cases", "diagnostic_odyssey", "rare_disease_cases",
              "senior_health_longevity", "medical_mystery_outbreak",
              "surgical_case_studies", "neurology_cases", "medical_history",
              "drug_discovery_stories", "sleep_science"]
    for n in NICHES:
        p = te.NICHE_PROFILES.get(n)
        check("E", f"thumbnail profile: {n}",
              p is not None and p["bg_color"] == (14, 18, 22),
              "missing -> falls back to blood-red horror styling")
    # Thumbnails, measured on real output.
    T = ("Acute liver failure in a neonate following a rare inherited "
         "disorder of galactose metabolism")
    for _ in range(6):
        out = te.enforce_number_noun("", T, "rare_disease_cases")
        check("E", "the thumbnail never invents a number",
              not re.search(r"\b\d", out),
              f"got {out!r} — a case about a 21-day-old newborn was coming "
              f"back as '14 YEARS', picked at random from a bank with no "
              f"clinical entry. That is a false claim on the most visible "
              f"surface the channel has.")
    check("E", "a REAL number from the topic is still allowed",
          "47" in te.enforce_number_noun("", "A 47 year old man with hepatic failure",
                                         "rare_disease_cases"))
    check("E", "medical thumbnails never fall back to a stock photo",
          "rare_disease_cases" in te.MEDICAL_NICHES
          and "_clinical_procedural_background" in read(
              "video_pipeline/thumbnail_engine_v2.py"))
    check("E", "the generated backdrop is visible, not near-black",
          _thumbnail_backdrop_is_visible(),
          "a black rectangle in YouTube's grid is the only place a "
          "thumbnail has to work")

    check("E", "avatar resolves for the live channel name",
          te.get_channel_avatar_prompt("No Known Cause", 1)[0] is not None)
    check("E", "register mix sums to 1.0",
          abs(sum(TARGET_MIX.values()) - 1.0) < 0.01)

    # With no figures, FIGURE must not be assigned.
    q = new_quota(60, figure_count=0)
    picks = [q.pick("the patient deteriorated overnight") for _ in range(60)]
    check("E", "no FIGURE segments when the paper has none",
          "FIGURE" not in picks, str(set(picks)))

    audit_rendered_episode()
    audit_sourcing_robustness()
    audit_calibration()


# ── D2. CALIBRATION, AGAINST REAL SCRIPTS ──────────────────────────────
def audit_calibration():
    """
    The specificity threshold is derived, not guessed. Re-check it here so a
    change to the detector or the threshold cannot silently invalidate it.
    """
    import subprocess
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "calibrate_specificity.py")],
                       capture_output=True, text=True, timeout=180)
    check("D", "the specificity threshold is supported by real scripts",
          r.returncode == 0,
          (r.stdout or "")[-300:])

    # And the figure-fetch path, exercised for real against a local server.
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "figure_fetch_selftest.py")],
                       capture_output=True, text=True, timeout=300)
    check("B", "the real figure-fetch path passes its self-test",
          r.returncode == 0,
          (r.stdout or "")[-300:])


# ── B2. SOURCING, MEASURED ─────────────────────────────────────────────
def audit_sourcing_robustness():
    import pmc_data as P
    from io import BytesIO
    from PIL import Image
    cp = read("channels/betrayal_deepdive/clinical_pipeline.py")

    check("B", "figure fetch tries the canonical PMC host first",
          P.FIGURE_URL_PATTERNS[0].startswith("https://pmc.ncbi.nlm.nih.gov"),
          "www.ncbi.nlm.nih.gov/pmc now redirects; relying on a redirect for "
          "the one asset that differentiates this channel is a needless risk")
    check("B", "figure fetch has three independent URL patterns",
          len(P.FIGURE_URL_PATTERNS) >= 3)

    # The bytes must really be a usable image.
    def _jpg(w, h):
        b = BytesIO(); Image.new("RGB", (w, h)).save(b, "JPEG"); return b.getvalue()
    check("B", "HTML masquerading as a figure is rejected",
          not P._decodes_as_usable_image(b"<html>error</html>"))
    check("B", "a thumbnail-sized figure is rejected",
          not P._decodes_as_usable_image(_jpg(100, 80)),
          "would render as a postage stamp in a 1080p frame")
    check("B", "a real image is accepted", P._decodes_as_usable_image(_jpg(800, 600)))

    check("B", "figures are proven downloadable before the quota is built",
          "prefetch_figures" in cp,
          "the quota commits ~30% of the episode to FIGURE from METADATA; if "
          "the binaries fail every one of those segments silently renders the "
          "fallback card")
    check("B", "figure prefetch prunes to what actually landed",
          P.prefetch_figures({"figures": [{"pmcid": "PMC0", "filename": "x.jpg"}]},
                             "/tmp")["figures"] == [],
          "an unreachable figure must not stay in the case")

    # Shorts must not fetch library footage either.
    import shorts_reels_engine as sre
    import medical_segments as _ms
    check("B", "the clinical channel is on the no-stock list",
          "hospital medical" in sre.NO_STOCK_NICHES)
    check("B", "clinical Shorts render from the case, not Pixabay",
          hasattr(sre, "set_clinical_case")
          and hasattr(_ms, "render_vertical_background")
          and "set_clinical_case(get_episode_case())" in cp,
          "the main video's stock path was closed; the Shorts path was not")
    check("B", "the Shorts caption declares its real resolution",
          "PlayResX=1080,PlayResY=1920" in read("video_pipeline/shorts_reels_engine.py"),
          "without it libass scales the style ~6.7x and draws enormous "
          "captions across the MIDDLE of every Short on every channel")
    check("B", "the Shorts hook wraps instead of clipping",
          _hook_fits(),
          "a single unwrapped drawtext clipped the hook at BOTH ends")
    check("B", "vertical cards clear the measured Shorts caption",
          _vertical_cards_clear_caption(),
          "content low in the frame is pushed further down by the zoom")
    check("B", "every vertical card kind renders",
          _all_vertical_cards_render(),
          "a Short that cannot render its card would fall back to footage")

    check("B", "case-structure extraction retries rather than failing silently",
          "_parse_structures" in cp and "for attempt in range(3)" in cp,
          "one malformed response used to leave five of six registers empty")
    # The extraction parser has never seen a real model response. These are
    # the shapes a model actually emits when it goes wrong -- every one of
    # them used to be a crash or a silently malformed structure reaching a
    # renderer.
    _adversarial_extraction()

    check("B", "an invented quotation is rejected",
          "not found verbatim" in cp,
          "TEXT would otherwise put a paraphrase on screen attributed to a "
          "real paper")

    # ── the four defects run 30637537806 died of ────────────────────────
    check("B", "every PMC niche selects CASE REPORTS",
          all('PUB_TYPE:"Case Reports"' in q
              for q in P.NICHE_PMC_QUERIES.values()),
          "five niches had no case-report filter and returned Cell, Archives "
          "of Toxicology and Signal Transduction research papers — no patient, "
          "no chronology, no differential to build an episode from")
    _title_checks()




# ── E2. VISUALS, MEASURED ON A REAL RENDER ─────────────────────────────
# Everything above this line inspects code. The defects that actually
# shipped were invisible to that: the audit passed 83/83 while the CHART
# register rendered NOTHING on any segment of any episode, because the
# pipeline passed a chart function it had never imported, the NameError was
# swallowed by a try/except, and the fallback card it produced logs as a
# success. 29% of a measured episode was that card.
#
# So these checks drive the real quota and the real renderers over a full
# episode and assert on the OUTPUT.
def audit_rendered_episode():
    import importlib
    import medical_segments as ms
    from medical_register import (new_quota, SEGMENTS_PER_DATUM,
                                  TEXT_CAPACITY_SEGMENTS, RegisterQuota)

    sys.path.insert(0, str(ROOT / "tools"))
    ler = importlib.import_module("local_episode_render")
    case, narration = ler.CASE, ler.NARRATION

    cp = read("channels/betrayal_deepdive/clinical_pipeline.py")
    # Comments are stripped first: the fix's own explanation names the bug,
    # and a check that its own rationale trips is a check nobody keeps.
    cp_code = "\n".join(l for l in cp.splitlines()
                        if not l.lstrip().startswith("#"))
    check("E", "no undefined chart function is passed to the renderers",
          "generate_data_chart" not in cp_code,
          "clinical_pipeline defines no such name; passing it raised "
          "NameError on every CHART segment and silently produced the "
          "fallback card")
    check("E", "medical_segments owns a chart renderer",
          hasattr(ms, "render_chart_still"))
    check("E", "renderers receive the narration's own capitalisation",
          "stage_display, segment_dur" in cp_code
          and "render_last_resort_still(stage_display" in cp_code,
          "stage_text is lowercased for keyword matching; drawing it "
          "produces cards with lowercase sentence starts")
    check("E", "reveal is counted per register, not per episode",
          hasattr(RegisterQuota, "reveal") and "register_quota.reveal(" in cp_code)
    check("E", "TEXT capacity and TEXT budget agree",
          RegisterQuota(60, available={"TEXT": True}).text_budget
          == int(TEXT_CAPACITY_SEGMENTS))
    check("E", "every data-driven register has a capacity rule",
          set(SEGMENTS_PER_DATUM) == {"FIGURE", "CHART", "BOARD", "TIMELINE"},
          str(sorted(SEGMENTS_PER_DATUM)))

    # Drive a full episode's scheduling exactly as the pipeline does.
    words = narration.split()
    n = 59
    bw = max(1, len(words) // n)
    quota = new_quota(n, figure_count=len(case["figures"]), case=case)
    seq, reveals = [], {}
    for i in range(n):
        text = " ".join(words[i * bw:(i + 1) * bw]).lower()
        reg = quota.pick(text)
        occ, exp = quota.reveal(reg)
        seq.append(reg)
        reveals.setdefault(reg, []).append(occ)

    from collections import Counter
    counts = Counter(seq)
    check("E", "all six registers are used on a case that supports them",
          len(counts) == 6, str(dict(counts)))

    longest, cur = 1, 1
    for a, b in zip(seq, seq[1:]):
        cur = cur + 1 if a == b else 1
        longest = max(longest, cur)
    check("E", "no register runs longer than its cap",
          longest <= quota.MAX_RUN, f"longest run {longest}")

    check("E", "every register's reveal advances by one per appearance",
          all(v == list(range(1, len(v) + 1)) for v in reveals.values()),
          "a register that repeats its reveal position renders identical frames")

    # No single register may dominate. 30% is the highest share TARGET_MIX
    # ever assigns, so anything above it means surplus piled onto one
    # register -- the exact failure that produced 17 CHART and later 16
    # ANATOMY segments on this same case.
    worst, worst_n = counts.most_common(1)[0]
    check("E", "no register takes more than 30% of the episode",
          worst_n <= n * 0.30, f"{worst} took {worst_n}/{n}")

    check("E", "the fallback card is never needed on a well-formed case",
          all(quota.mix.get(r, 0) >= 0 for r in counts) and
          not _fallbacks_needed(ms, case, seq, reveals),
          "a register scheduled without data renders the plain text card")


def _thumbnail_backdrop_is_visible():
    """
    Real pixel measurement: the generated clinical backdrop must have some
    actual luminance range, not be a flat near-black field.
    """
    import tempfile
    from PIL import Image
    import thumbnail_engine_v2 as te
    with tempfile.TemporaryDirectory() as td:
        prof = te.NICHE_PROFILES["rare_disease_cases"]
        path = te._clinical_procedural_background(td, 7, prof)
        px = list(Image.open(path).convert("L").getdata())
        return (max(px) - min(px)) >= 25 and sum(px) / len(px) >= 8


def _adversarial_extraction():
    """
    Run the pipeline's own _parse_structures against malformed model output.

    Extracted from clinical_pipeline by source so the REAL parser is tested,
    not a copy. Every case here is a shape a model genuinely produces:
    fenced JSON, prose wrapped around JSON, a differential given as dicts
    instead of pairs, string values where numbers belong, a chart with
    mismatched label/value lengths, nulls everywhere, and a truncated
    response. Any one of them reaching a renderer is a broken segment.
    """
    src = read("channels/betrayal_deepdive/clinical_pipeline.py")
    start = src.index("        def _parse_structures(raw):")
    end = src.index("        def _score(st):")
    body = "\n".join(l[8:] if l.startswith("        ") else l
                     for l in src[start:end].splitlines())
    ns = {"re": re, "json": json,
          "case": {"narrative": "the infant deteriorated despite antibiotics"},
          "log": lambda *a: None}
    exec(body, ns)
    parse = ns["_parse_structures"]

    cases = [
        ("empty string", "", None),
        ("None", None, None),
        ("prose with no JSON", "I could not find that information.", None),
        ("fenced JSON", '```json\n{"differentials":[["Sepsis","EXCLUDED","x"]]}\n```', "ok"),
        ("prose wrapped around JSON",
         'Here is what I found:\n{"timeline":[["Day 1","admitted"]]}\nHope that helps.', "ok"),
        ("truncated JSON", '{"differentials":[["Sepsis","EXCLUDED"', None),
        ("a JSON list, not an object", '[1,2,3]', None),
        ("differentials as dicts",
         '{"differentials":[{"name":"Sepsis","verdict":"EXCLUDED"}]}', "ok"),
        ("chart values as strings",
         '{"chart_data":{"labels":["a","b"],"values":["1","2"]}}', "ok"),
        ("chart label/value length mismatch",
         '{"chart_data":{"labels":["a","b","c"],"values":[1,2]}}', "ok"),
        ("chart with one point",
         '{"chart_data":{"labels":["a"],"values":[1]}}', "ok"),
        ("everything null",
         '{"differentials":null,"timeline":null,"chart_data":null,'
         '"anatomy":null,"quote":null}', "ok"),
        ("anatomy as a string", '{"anatomy":"the liver"}', "ok"),
        ("blocked_step out of range",
         '{"anatomy":{"pathway":["a","b"],"blocked_step":9}}', "ok"),
        ("pathway with one step",
         '{"anatomy":{"pathway":["only one"],"blocked_step":0}}', "ok"),
    ]
    for name, raw, want in cases:
        try:
            got = parse(raw)
        except Exception as e:
            check("B", f"extraction survives: {name}", False,
                  f"{type(e).__name__}: {e}")
            continue
        if want is None:
            check("B", f"extraction rejects: {name}", got is None, str(got)[:80])
        else:
            check("B", f"extraction survives: {name}", got is not None)
            if got:
                # Whatever survives must be the exact shape the renderers
                # expect, or it breaks one level further down where it is
                # much harder to see.
                shape_ok = (
                    all(isinstance(r, tuple) and len(r) == 3
                        for r in got["differentials"])
                    and all(isinstance(r, tuple) and len(r) == 2
                            for r in got["timeline"])
                    and (got["chart_data"] is None
                         or (len(got["chart_data"]["labels"])
                             == len(got["chart_data"]["values"])
                             and len(got["chart_data"]["values"]) >= 2
                             and all(isinstance(v, float)
                                     for v in got["chart_data"]["values"])))
                    and isinstance(got["anatomy"], dict)
                    and (got["anatomy"]["pathway"] is None
                         or len(got["anatomy"]["pathway"]) >= 2)
                    and (got["anatomy"]["blocked_step"] is None
                         or (got["anatomy"]["pathway"] is not None
                             and 0 <= got["anatomy"]["blocked_step"]
                             < len(got["anatomy"]["pathway"])))
                    and isinstance(got["quote"], str))
                check("B", f"extraction normalises correctly: {name}", shape_ok,
                      str(got)[:110])


def _hook_fits(max_px=1080):
    import shorts_reels_engine as sre
    for hook in ("A newborn was being poisoned by milk.",
                 "The negative result that redirected an entire investigation",
                 "Short."):
        parts = sre._hook_drawtext(hook)
        if not parts:
            return False
        for pt in parts:
            size = int(re.search(r"fontsize=(\d+)", pt).group(1))
            text = pt.split("'")[1]
            if len(text) * size * 0.62 > max_px:
                return False
    return True


def _title_checks():
    """
    The title stage killed a whole run: it returned the byte-identical title
    twelve times, capped at 7.0, and discarded a script that had passed at
    8.6. Three separate causes, three checks.
    """
    import json as _json
    import re as _re
    cp = read("channels/betrayal_deepdive/clinical_pipeline.py")
    ns = {"re": _re, "json": _json, "log": lambda *a, **k: None,
          "notify_stage_score": lambda *a, **k: None,
          "_record_title_history": lambda *a, **k: None}
    exec(cp[cp.index("def score_title_v2"):
            cp.index("# Real business-inquiries contact")], ns)
    score, gate = ns["score_title_v2"], ns["run_title_ctr_gate"]

    # 1. A real clinical title must be able to clear the 8.5 gate at all.
    #    Before the phrase banks were re-based, the best a factual clinical
    #    headline could score was about 7.0 -- the gate was unreachable by
    #    construction, so every run ended the same way.
    reachable = [
        "Nobody Knew Why: The 21-Day-Old Diagnosed Too Late",
        "The One Test That Finally Explained A 14-Year Illness",
        "Treated As Sepsis For 96 Hours. It Was Never Infection",
    ]
    check("D", "a factual clinical title can clear the 8.5 title gate",
          all(score(t)[0] >= 8.5 for t in reachable),
          "the scorer's phrase banks were true-crime; a clinical headline "
          "could not reach the gate no matter how many times it regenerated")

    # 2. Cover-up framing must NOT score well. The old banks paid +1.5 for
    #    "covered up" and +1.5 for "they knew" -- the scorer was rewarding
    #    exactly the allegations the medical policy rules forbid.
    accusatory = [
        "Doctors Covered Up What They Knew: 14 Years Of Silence",
        "The Hospital That Let It Happen And Went Unpunished",
    ]
    check("C", "the title scorer does not reward cover-up framing",
          all(score(t)[0] < 7.5 for t in accusatory),
          "titles alleging concealment by real named clinicians must not "
          "outscore factual clinical ones on a medical channel")

    # 3. Every retry must ASK SOMETHING DIFFERENT. This is the actual bug:
    #    a deterministic provider given an identical prompt returns an
    #    identical answer, so a stalled loop burns every remaining attempt.
    prompts = []
    def _ai(prompt, tokens=300):
        prompts.append(prompt)
        return _json.dumps(["Nobody knew the rates were this uneven"] * 5)
    gate("seed", [("Nobody knew the rates were this uneven", 7.0)],
         "a neonate with galactosaemia", "toxicology_cases",
         "No Known Cause", 12, _ai, min_ctr=8.5, max_attempts=8)
    check("D", "every title retry sends a different prompt",
          len(prompts) > 1 and len(set(prompts)) == len(prompts),
          "attempts 2-13 of run 30637537806 were byte-identical, wasting "
          "twelve calls on a guaranteed failure")
    check("D", "title retries name the titles already rejected",
          all("Already rejected" in p for p in prompts[1:]),
          "without it the model re-proposes the same headline")
    check("C", "title retry prompts carry no true-crime instruction",
          not any(w in p for p in prompts
                  for w in ("They Knew", "Still Happening", "Dark documentary")),
          "the retry loop was telling a medical channel to add conspiracy "
          "phrasing")

    # 4. A failing title must escalate, not destroy an approved script.
    check("F", "a below-gate title escalates to a human instead of exiting",
          "review_title" in cp and "_LAST_TITLE_CANDIDATES" in cp
          and "Escalating to human review" in cp,
          "run 30637537806 threw away a script that had passed at 8.6/10 "
          "because a one-line string scored 7.0")


def _vertical_cards_clear_caption():
    """
    Pixel test in 9:16, zoom-aware -- the vertical twin of the horizontal
    caption-band check, and derived from the same kind of real measurement.
    """
    import tempfile
    from PIL import Image
    import medical_segments as ms
    from local_episode_render import CASE
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        for kind in ms.VERTICAL_SEQUENCE:
            p = td / f"{kind}.png"
            if not ms.render_vertical_card(kind, CASE, str(p),
                                           headline="A baby girl stopped feeding "
                                                    "on the second day of her life.",
                                           progress=1.0):
                return False
            im = Image.open(p).convert("RGB")
            lowest = None
            for y in range(ms.VH - 1, 0, -1):
                row = [im.getpixel((x, y)) for x in range(0, ms.VW, 4)]
                if max(max(abs(px[k] - ms.BG[k]) for k in range(3))
                       for px in row) > 12:
                    lowest = y
                    break
            if lowest is None:
                continue
            landed = ms.VH / 2 + (lowest - ms.VH / 2) * ms.V_MAX_ZOOM
            if landed > ms.V_CAPTION_INK_TOP - 1:
                return False
            # And nothing may sit under the hook band either.
            highest = None
            for y in range(ms.VH):
                row = [im.getpixel((x, y)) for x in range(0, ms.VW, 4)]
                if max(max(abs(px[k] - ms.BG[k]) for k in range(3))
                       for px in row) > 12:
                    highest = y
                    break
            if highest is not None and highest < 350:
                return False
    return True


def _all_vertical_cards_render():
    import tempfile
    import medical_segments as ms
    from local_episode_render import CASE
    with tempfile.TemporaryDirectory() as td:
        return all(
            ms.render_vertical_card(k, CASE, f"{td}/{k}.png",
                                    headline="A baby girl stopped feeding.",
                                    progress=0.6)
            for k in ms.VERTICAL_SEQUENCE)


def _no_truncated_speech(words, cues):
    """
    No cue may disappear while its own words are still being spoken.

    My first draft of the timing capped every cue at MAX_DWELL, which clipped
    the opening caption at 7.00s while the sentence ran to 8.6s -- the
    caption vanished mid-word. Grepping for a constant would never catch
    that; comparing cue ends against word ends does.
    """
    for i, c in enumerate(cues):
        hi = cues[i + 1]["start"] if i + 1 < len(cues) else float("inf")
        owned = [w for w in words if c["start"] - 1e-6 <= w["start"] < hi]
        if owned and c["end"] + 1e-6 < max(w["end"] for w in owned):
            return False
    return True


def _measured_caption_ink_top():
    """
    Where the REAL caption actually starts, measured by burning a two-line
    cue with libass onto white and finding the first row of ink.

    Not read from a constant. The constant is derived from this number, and
    a check that reads its own input from the thing it is checking proves
    nothing.
    """
    import subprocess, tempfile
    from PIL import Image
    import caption_timing as capt
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        cue = [{"start": 0.0, "end": 5.0, "cps": 1.0,
                "text": "Newborns tire, newborns refuse, and tired mothers "
                        "are told gently"}]
        ass = td / "c.ass"
        ass.write_text(capt.build_ass(cue), encoding="utf-8")
        white = td / "w.png"
        Image.new("RGB", (1920, 1080), (255, 255, 255)).save(white)
        out = td / "o.png"
        subprocess.run(["ffmpeg", "-y", "-loop", "1", "-t", "1.5", "-i", str(white),
                        "-vf", f"subtitles='{ass}'", "-ss", "0.5",
                        "-frames:v", "1", str(out)], capture_output=True, timeout=120)
        if not out.exists():
            return None
        im = Image.open(out).convert("L")
        for y in range(1080):
            if min(im.getpixel((x, y)) for x in range(0, 1920, 4)) < 200:
                return y
    return None


def _nothing_in_caption_band():
    """
    A real PIXEL test, applied to the ZOOMED frame.

    This is the check that caught the collision -- twice, at two different
    depths.
      * First pass: every renderer independently chose the bottom of the
        frame for its secondary text, and captions live there.
      * Second pass, only visible in the finished video: still_to_clip
        applies a zoompan, and a zoom magnifies OUTWARD from the centre, so
        content near the bottom moves further down as the shot pushes in. A
        band that is clear in the still can be crossed in the clip. Measured
        on a real FIGURE shot at its 1.14 ceiling, content at y=880 landed
        at y=928, thirty-four pixels inside the caption.
    So this measures the caption for real, then applies each register's own
    maximum zoom to the lowest ink in each rendered still.
    """
    import tempfile
    from PIL import Image
    import medical_figure_render as mfr
    import medical_segments as ms
    from local_episode_render import CASE

    ink_top = _measured_caption_ink_top()
    if ink_top is None:
        return False
    # The derived constant must match what libass actually does.
    if abs(ink_top - mfr.CAPTION_INK_TOP) > 6:
        return False
    if mfr.MAX_REGISTER_ZOOM < max(m["max"] for m in ms.MOTION.values()) - 1e-9:
        return False

    bg = mfr.BG
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        renders = []
        p = td / "board.png"
        if ms.render_board_still(CASE["differentials"], str(p), progress=1.0):
            renders.append(("BOARD", p))
        p = td / "timeline.png"
        if mfr.render_timeline_frame(CASE["timeline"], str(p)):
            renders.append(("TIMELINE", p))
        cd = CASE["chart_data"]
        p = td / "chart.png"
        if ms.render_chart_still(cd["chart_type"], cd["title"], cd["labels"],
                                 cd["values"], str(p), y_label=cd["y_label"],
                                 citation=CASE["citation"], progress=1.0):
            renders.append(("CHART", p))
        a = CASE["anatomy"]
        p = td / "anatomy.png"
        if ms.render_anatomy_still(a["title"], a["explanation"], str(p),
                                   pathway=a["pathway"],
                                   blocked_index=a["blocked_step"],
                                   variant=0, progress=1.0, variant_total=6):
            renders.append(("ANATOMY", p))
        p = td / "text.png"
        if ms.render_text_still(CASE["quote"], str(p),
                                attribution=mfr.short_credit(CASE["citation"])):
            renders.append(("TEXT", p))
        p = td / "last.png"
        if ms.render_last_resort_still("A long line of narration " * 6, str(p),
                                       citation=mfr.short_credit(CASE["citation"])):
            renders.append(("ANATOMY", p))
        p = td / "title.png"
        if ms.render_title_card(CASE["title"], str(p),
                                source_line="J Med Case Rep 2023",
                                citation=CASE["citation"]):
            renders.append(("TITLE", p))

        if not renders:
            return False
        for reg, path in renders:
            im = Image.open(path).convert("RGB")
            lowest = None
            for y in range(mfr.H - 1, 0, -1):
                row = [im.getpixel((x, y)) for x in range(0, mfr.W, 4)]
                if max(max(abs(px[k] - bg[k]) for k in range(3))
                       for px in row) > 12:
                    lowest = y
                    break
            if lowest is None:
                continue
            zoom = ms.MOTION.get(reg, {"max": 1.14})["max"]
            landed = mfr.H / 2 + (lowest - mfr.H / 2) * zoom
            if landed > ink_top - 1:
                return False
    return True


def _fallbacks_needed(ms, case, seq, reveals):
    """True if any scheduled register has no data to render from."""
    have = {
        "FIGURE": bool(case.get("figures")),
        "CHART": bool((case.get("chart_data") or {}).get("labels")),
        "BOARD": bool(case.get("differentials")),
        "TIMELINE": len(case.get("timeline") or []) >= 2,
        "TEXT": bool((case.get("quote") or "").strip()),
        "ANATOMY": True,
    }
    return any(not have.get(r, False) for r in set(seq))


# ── F. INTEGRATION ─────────────────────────────────────────────────────
def audit_integration():
    cp = read("channels/betrayal_deepdive/clinical_pipeline.py")
    check("F", "no-video run exits non-zero",
          "sys.exit(2)" in cp, "a silent no-op must not look like success")
    check("F", "false compositing disclosure disabled",
          "needs_fiction_disclosure = False" in cp,
          "it contradicted the citation directly below it")
    check("F", "expansion preserves the rehook beat",
          cp.count("Preserve the existing mid-video direct-address beat") >= 2)
    check("F", "expansion sends the whole script, not raw[:4000]",
          "+ raw[:4000])" not in cp)
    check("F", "leading title line is stripped from narration",
          "strip_leading_title_line" in cp and cp.count("strip_leading_title_line") >= 3,
          "run 4 opened by speaking an invented title")
    from script_scoring import strip_leading_title_line as _slt
    check("F", "title stripper removes a quoted title",
          not _slt('"The Forgotten Girl: A Silent Fight"\nA baby was born.').startswith('"'))
    check("F", "title stripper keeps real narration",
          _slt("A baby girl was born on a Tuesday.\nShe weighed 2,500 grams.").startswith("A baby"))

    # Defects found by simulation before run 5, each now locked in.
    from medical_register import new_quota, available_from_case
    POOR = {"figures": [], "chart_data": None,
            "differentials": [("X", "EXCLUDED", "y")], "timeline": [], "quote": ""}
    q = new_quota(60, figure_count=0, case=POOR)
    picks = [q.pick("the patient deteriorated overnight") for _ in range(60)]
    avail = available_from_case(POOR)
    dead = sum(1 for r in picks if not avail.get(r, False))
    check("F", "quota never schedules a register with no data", dead == 0,
          f"{dead}/60 would render the fallback card")

    run = longest = 1
    for a, b in zip(picks, picks[1:]):
        run = run + 1 if a == b else 1
        longest = max(longest, run)
    check("F", "no more than 3 identical registers in a row", longest <= 3,
          f"longest run {longest}")

    q2 = new_quota(60, figure_count=6,
                   case={"figures": [1] * 6, "chart_data": {"labels": [1, 2], "values": [1, 2]},
                         "differentials": [("a", "b", "c")], "timeline": [("d", "e"), ("f", "g")],
                         "quote": "q"})
    p2 = [q2.pick("scan repeated") for _ in range(60)]
    run = longest = 1
    for a, b in zip(p2, p2[1:]):
        run = run + 1 if a == b else 1
        longest = max(longest, run)
    check("F", "6-figure paper does not run 21 FIGUREs in a row", longest <= 3,
          f"longest run {longest}")

    check("F", "episode case survives a resumed run",
          'ckpt_save("episode_case"' in cp and 'ckpt_load("episode_case")' in cp,
          "resume would otherwise render every segment as a fallback card")
    # Captions, measured rather than grepped. The previous check here looked
    # for a literal constant name in the pipeline source, which proved
    # nothing about the output and broke the moment the logic moved into its
    # own module. These run the real timing code over the real narration.
    import caption_timing as capt
    sys.path.insert(0, str(ROOT / "tools"))
    from local_caption_render import synth_word_timings
    from local_episode_render import NARRATION

    # Runtime accountability.
    import human_review_gate as hrg
    cp_code = "\n".join(l for l in cp.splitlines()
                        if not l.lstrip().startswith("#"))
    check("F", "every review gate is named for the runtime breakdown",
          cp_code.count("review_") > 0 and
          read("video_pipeline/human_review_gate.py").count('set_current_gate("') >= 9,
          "an unattributed 5-hour run is a run nobody can reason about")
    check("F", "per-gate review timeout is overridable for test runs",
          hasattr(hrg, "default_review_timeout"),
          "a test run should not cost 4 hours of idle polling")
    check("F", "the pipeline prints where the wall-clock went",
          "_log_runtime_breakdown" in cp_code)

    check("F", "caption timing lives in a testable module",
          "from caption_timing import ass_from_words" in cp)
    for wpm in (110, 150):
        words, total = synth_word_timings(NARRATION, wpm)
        cues, st = capt.build_cues(words, total_duration=total)
        check("F", f"captions never overlap ({wpm} wpm)", st["overlaps"] == 0,
              str(st["overlaps"]))
        check("F", f"no caption flashes below the dwell floor ({wpm} wpm)",
              st["under_dwell"] == 0, str(st["under_dwell"]))
        check("F", f"every caption is readable at <= {capt.MAX_CPS:.0f} CPS "
                   f"({wpm} wpm)", st["over_cps"] == 0,
              f"{st['over_cps']} cues above, max {st['max_cps']}")
        check("F", f"no caption is cut off mid-sentence ({wpm} wpm)",
              _no_truncated_speech(words, cues),
              "a cue ended before its own last word finished")

    check("F", "ASS override characters are escaped",
          capt.escape_ass("a {b} c") == "a \\{b\\} c")
    check("F", "caption style uses an installed font and an opaque box",
          "DejaVu Sans" in capt.ASS_HEADER
          and ",3,14,0,2," in capt.ASS_HEADER,
          "Arial is not installed on the runner; outline-only white text is "
          "unreadable over medical imaging")

    # Nothing else may be drawn in the caption band.
    import medical_figure_render as _mfr
    import medical_segments as _ms
    check("F", "renderers reserve a caption-safe band",
          _mfr.CAPTION_SAFE_H >= 180 and _ms.CONTENT_BOTTOM == _mfr.CONTENT_BOTTOM)
    check("F", "no renderer draws below the caption band",
          _nothing_in_caption_band(),
          "burned-in captions would sit on top of it")
    check("F", "pace is set in exactly one place",
          'rate="-8%"' not in cp and 'rate="-5%"' not in cp
          and "CLINICAL_PACE" in cp and "EDGE_RATE" in cp)
    check("F", "stock footage is unreachable",
          "NO STOCK FOOTAGE ON THIS CHANNEL" in cp)

    check("F", "disclaimer is appended to the description",
          "_clin_block" in cp and "description = f\"{description}{_clin_block}\"" in cp)

    md = read("channels/betrayal_deepdive/STUDIO_BRANDING.md")
    blocks = re.findall(r"```\n(.*?)\n```", md, re.S)
    check("F", "About text within 1000 chars", len(blocks[0]) <= 1000, str(len(blocks[0])))
    check("F", "keywords within 500 chars", len(blocks[1]) <= 500, str(len(blocks[1])))
    for i, lim in ((8, 60), (9, 60), (10, 60), (11, 85)):
        check("F", f"Studio field {i} within {lim} chars", len(blocks[i]) <= lim,
              str(len(blocks[i])))


def main():
    for fn in (audit_identity, audit_sourcing, audit_policy,
               audit_scoring, audit_script_craft, audit_visuals,
               audit_integration):
        try:
            fn()
        except Exception as e:
            FAIL.append((fn.__name__, f"AUDIT ITSELF CRASHED: {type(e).__name__}", str(e)[:200]))

    groups = {"A": "IDENTITY", "B": "SOURCING", "C": "POLICY",
              "D": "SCORING", "E": "VISUALS", "F": "INTEGRATION"}
    for g, title in groups.items():
        p = sum(1 for x in PASS if x[0] == g)
        f = [x for x in FAIL if x[0] == g]
        status = "OK" if not f else f"{len(f)} FAILED"
        print(f"  {g}  {title:12} {p:3} passed   {status}")
        for _, name, detail in f:
            print(f"       FAIL: {name}  {detail}")
    other = [x for x in FAIL if x[0] not in groups]
    for g, name, detail in other:
        print(f"  !!  {g}: {name} {detail}")

    print(f"\n  {len(PASS)} passed, {len(FAIL)} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
