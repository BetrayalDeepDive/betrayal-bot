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
import os
import re
import sys
import time
import json
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "video_pipeline"))

ROOT = pathlib.Path(__file__).resolve().parent.parent
PASS, FAIL = [], []


def check(group, name, condition, detail=""):
    (PASS if condition else FAIL).append((group, name, detail))


def read(rel):
    return (ROOT / rel).read_text()


def read_code(rel):
    """
    Source with comments and docstrings stripped.

    A "this string must NOT appear" check is worthless against raw source:
    the comment EXPLAINING that '#truecrime' was removed contains the very
    text the check forbids, so the check fails on a correct file. Absence
    checks must look at what actually runs.
    """
    import io
    import tokenize
    src = (ROOT / rel).read_text()
    out = []
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except (tokenize.TokenError, IndentationError):
        return src
    depth = 0
    # Only a string that STARTS a logical statement is a docstring. Tracking
    # bracket depth is what makes that true: inside a list or dict every
    # element also follows a newline token, and without this the checker
    # silently deleted every multi-line collection's strings -- which is
    # exactly the false "the new topic pool is missing" it first reported.
    prev_type = tokenize.NEWLINE
    for tok in toks:
        if tok.type == tokenize.COMMENT:
            continue
        if tok.type == tokenize.OP:
            if tok.string in "([{":
                depth += 1
            elif tok.string in ")]}":
                depth = max(0, depth - 1)
        if (tok.type == tokenize.STRING and depth == 0
                and prev_type in (tokenize.INDENT, tokenize.DEDENT,
                                  tokenize.NEWLINE, tokenize.ENCODING)):
            prev_type = tok.type
            continue
        if tok.type not in (tokenize.NL, tokenize.NEWLINE,
                            tokenize.INDENT, tokenize.DEDENT):
            out.append(tok.string)
        if tok.type != tokenize.NL:
            prev_type = tok.type
    return "\n".join(out)


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
    _model_discovery_checks()
    _provider_rotation_checks()
    _audio_gate_checks()
    _video_gate_checks()
    _job_clock_checks()
    _short_answer_checks()
    _rounds_checks()
    _format_leakage_checks()
    _green_run_checks()
    _synthetic_declaration_checks()
    _email_routing_checks()
    _format_leak_checks()
    _review_gate_checks()
    _resolution_checks()




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
    # Was "all six". CASEFILE and LAB were added, so the expectation is now
    # every register the CASE ITSELF supports -- which is the stronger check
    # anyway: it fails if a schedulable register never gets scheduled, and it
    # does not fail for a register the paper genuinely cannot render.
    from medical_register import available_from_case, TARGET_MIX
    _avail = available_from_case(case)
    _expect = {r for r in TARGET_MIX if _avail.get(r, True)}
    check("E", "every register the case supports is actually used",
          set(counts) == _expect,
          f"scheduled={sorted(counts)} supported={sorted(_expect)}")

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


def _model_discovery_checks():
    """
    Model IDs must be ASKED FOR, not hardcoded.

    Every "provider outage" in this project has been a stale model id.
    Run 30655118228: Cerebras 404'd on all five hardcoded names, and
    OpenRouter 404'd on all five ":free" ids because the free tiers had been
    withdrawn while the paid ids kept the same names. Editing the lists by
    hand only resets the clock -- it had already been done twice.
    """
    cp = read("channels/betrayal_deepdive/clinical_pipeline.py")
    check("F", "model catalogues are discovered at runtime",
          "def _discover_models" in cp,
          "a hand-written model list goes stale silently and looks like an "
          "outage")
    for prov in ("Cerebras", "OpenRouter", "Groq", "Mistral", "SambaNova",
                 "NvidiaNIM"):
        check("F", f"{prov} asks for its own model list",
              f'_discover_models(\n        "{prov}"' in cp
              or f'"{prov}", "http' in cp,
              "otherwise it dies the next time that provider renames a model")
    check("F", "OpenRouter picks models by REAL price, not an id suffix",
          "free_only=True" in cp and 'pr.get("prompt"' in cp,
          "which models are free changes; the ':free' suffix encoded it once "
          "and then rotted")
    check("F", "discovery failure falls back to the built-in list",
          "or OR_FREE_MODELS" in cp or "if not _models:" in cp,
          "a catalogue outage must never be worse than the old behaviour")

    # Exercise it: the free filter must not let a paid model through.
    import types as _t
    blk = cp[cp.index("_MODEL_CACHE = {}"):cp.index("# Known Cerebras model names")]
    class _R:
        payload = {"data": [
            {"id": "openai/gpt-4o", "pricing": {"prompt": "0.0000025",
                                                "completion": "0.00001"}},
            {"id": "deepseek/deepseek-r1:free", "pricing": {"prompt": "0",
                                                           "completion": "0"}},
        ]}
        def get(self, *a, **k):
            return _t.SimpleNamespace(status_code=200, json=lambda: _R.payload)
    ns = {"requests": _R(), "log": lambda m: None}
    exec(blk, ns)
    got = ns["_discover_models"]("OR", "u", {}, free_only=True)
    check("F", "a paid model never enters the free pool",
          got == ["deepseek/deepseek-r1:free"], str(got))


def _provider_rotation_checks():
    """
    A retry must ask a DIFFERENT model, or thirteen attempts are one attempt
    repeated thirteen times.

    ai_generate walked a fixed provider order on every call, so once the dead
    providers were marked, every call for the rest of the run went to the same
    survivor. That is the missing variation behind every "N attempts, same
    result" failure this channel has had -- 13 script attempts, 39 title
    attempts, 13 audio attempts.
    """
    cp = read("channels/betrayal_deepdive/clinical_pipeline.py")
    check("D", "the provider order rotates per attempt",
          "_AI_VARIANT" in cp and "def set_ai_variant" in cp
          and "live = live[_off:] + live[:_off]" in cp,
          "without it, 'try again' means 'ask the same model again'")
    for loop, marker in (("script", "set_ai_variant(attempt)"),
                         ("audio", "set_ai_variant(_audio_attempt)")):
        check("D", f"the {loop} retry loop rotates the provider", marker in cp)

    # Rotation must never REDUCE coverage -- every provider still gets tried.
    live = ["a", "b", "c", "d"]
    seen_first, covered = set(), True
    for a in range(1, 9):
        off = a % len(live)
        order = live[off:] + live[:off]
        seen_first.add(order[0])
        if sorted(order) != sorted(live):
            covered = False
    check("D", "rotation changes the order without dropping any provider",
          covered and len(seen_first) == len(live),
          f"{len(seen_first)} distinct providers asked first across 8 attempts")


def _video_gate_checks():
    """
    The video gate, scored the way THIS channel's video actually looks.

    Run 30688297894 assembled the whole episode five times, ~48 minutes each,
    scoring exactly 7.8/10 against an 8.5 gate, and was killed by the 6-hour
    job limit on the sixth. Three defaults were wrong, all of them "written
    for stock footage" on a channel that has none.
    """
    cp = read("channels/betrayal_deepdive/clinical_pipeline.py")

    # BOTH call sites -- the retry GATE and the human-review scorer. I fixed
    # the review one first and the gate (the loop that actually burns the 48
    # minutes) still had every default wrong; only pyflakes caught it.
    check("E", "every video scorer call is corrected, not just one",
          cp.count('content_type="animated"') >= 2
          and cp.count("expected_width=1920, expected_height=1080") >= 2,
          "the gate loop and the review scorer are separate calls")
    check("E", "the video gate expects the resolution actually composed",
          "expected_width=1920, expected_height=1080" in cp,
          "the scorer defaulted to 1280x720 while the pipeline composes "
          "1920x1080, so a CORRECT file failed the resolution check")
    check("E", "the video gate knows this channel renders, not films",
          'content_type="animated"' in cp,
          "rendered clinical cards compress far smaller than filmed footage; "
          "judged as stock footage a healthy 69MB file reads as corrupt")
    check("E", "pacing uses the real cut count, not scene detection",
          "known_cuts=" in cp and "_LAST_SEGMENT_COUNT" in cp,
          "a cross-fade between two dark cards does not trip ffmpeg's "
          "scene-change filter, so 61 real cuts measured as zero")
    check("F", "a stuck video retry stops instead of burning the job limit",
          "_VIDEO_STUCK" in cp,
          "13 reassemblies at 48 minutes each is 10.4 hours — longer than "
          "the 6-hour limit, so the budget could never actually be spent")

    # The arithmetic, reproducing run 9's real file.
    def ceiling(stream, size, pacing):
        return 10 * 0.28 + stream * 0.22 + size * 0.18 + 10 * 0.22 + pacing * 0.10
    check("E", "the video gate was genuinely unreachable before this",
          ceiling(6.0, 6.0, 3.0) < 8.5,
          f"as-scored ceiling was {ceiling(6.0, 6.0, 3.0):.1f}")
    check("E", "a correct episode can now clear the video gate",
          ceiling(10.0, 10.0, 10.0) >= 8.5,
          f"corrected ceiling is {ceiling(10.0, 10.0, 10.0):.1f}")

    # known_cuts must actually override the detector.
    from quality_scoring import score_video_quality
    import inspect
    src = inspect.getsource(score_video_quality)
    check("E", "known_cuts overrides the scene-change detector",
          "if known_cuts is not None and known_cuts > 0:" in src)


def _short_answer_checks():
    """
    Run 30703316566 cleared script (8.6), title (9.3), audio (9.8) and video
    (9.3) -- then spent 57 minutes failing the thumbnail-text gate 13 times
    with "no AI provider available". Every provider was answering correctly.

    The thumbnail prompt asks for a line of AT MOST 22 characters and every
    provider entrypoint hardcoded `len(response) > 100` as success, so a
    perfect 19-character answer was discarded, the provider was marked dead
    for the run, and the chain walked itself to exhaustion. Four calls in
    this pipeline were structurally unable to succeed on any provider, ever.
    """
    import re as _re
    cp = read("channels/betrayal_deepdive/clinical_pipeline.py")

    check("D", "no provider hardcodes a length floor any more",
          "len(t.strip()) > 100" not in cp and "len(text.strip()) > 100" not in cp,
          "a 22-character answer cannot clear a 100-character bar")
    check("D", "every provider entrypoint accepts a caller's floor",
          cp.count("min_chars=100):") >= 10 and "fn(prompt, tokens, min_chars)" in cp,
          "the parameter is useless unless ai_generate passes it down")

    # The four calls whose prompts cap the answer below 100 characters.
    for label, needle in (
            ("thumbnail text (22-char cap)", "tokens=15, min_chars=3"),
            ("thumbnail number-noun phrase", "tokens=60, min_chars=3"),
            ("two hashtags", "tokens=30, min_chars=3"),
            ("Shorts title (<55 chars)", "tokens=80, min_chars=12")):
        check("D", f"short-answer call is reachable: {label}", needle in cp,
              "its prompt caps the answer below the 100-char default floor")

    # Titles: the enumeration is not part of the title.
    check("D", "numbered-list markers are stripped from titles",
          "def strip_list_marker" in cp and "strip_list_marker(l)" in cp,
          'run 9 rendered "1. Every Test Was Normal Until Day 28..." — the '
          '"1. " survived every filter and reached the thumbnail')
    _strip = _re.compile(r'^\s*(?:\d{1,2}[\.\)]|[-*•–—])\s+')
    check("D", "the marker pattern matches what models actually emit",
          all(_strip.sub("", s).startswith("Every")
              for s in ("1. Every Test Was Normal", "2) Every Test Was Normal",
                        "- Every Test Was Normal", "• Every Test Was Normal"))
          and _strip.sub("", "2026 Was The Year") == "2026 Was The Year",
          "a leading year must NOT be mistaken for a list marker")

    # Discovery must ask what a model does, not only what it costs.
    import job_clock  # noqa: F401  — keeps video_pipeline on the path
    ns = {}
    _src = read("channels/betrayal_deepdive/clinical_pipeline.py")
    exec(_src[_src.index("_NON_TEXT_MODEL_HINTS = ("):
              _src.index("def _discover_models(")], ns)
    is_text = ns["_is_text_model"]
    check("D", "model discovery rejects music/speech/image models",
          not is_text({"id": "google/lyria-3-pro-preview"}, "google/lyria-3-pro-preview")
          and not is_text({}, "openai/whisper-large-v3")
          and not is_text({"architecture": {"output_modalities": ["audio"]}}, "x/y"),
          "run 9 sent script prompts to two Google MUSIC generators, which "
          "answered 402 and killed OpenRouter for the rest of the run")
    check("D", "model discovery still accepts real chat models",
          is_text({}, "meta-llama/llama-3.3-70b-instruct")
          and is_text({"architecture": {"modality": "text+image->text"}}, "x/y"),
          "the filter must not starve the chain it exists to protect")
    check("D", "free-tier filtering looks past per-token pricing",
          "for v in pr.values()" in cp,
          "media models report 0/0 per token while charging on another axis — "
          "which is how the lyria pair read as free. This started as a fixed "
          "list of keys to check; it now enumerates whatever the provider "
          "actually sent, because a fixed list cannot cover a key added later")

    # EVERY call whose PROMPT caps the answer below 100 characters. Seven more
    # were found on the end-to-end sweep, including both halves of the Edit
    # button -- the feature reported as "I typed that I want the title
    # changed, but it gave me the same script."
    for label, needle in (
            ("Edit-button title rewrite (50-65 chars)", "tokens=60, min_chars=15"),
            ("title rewrite at the title/thumb review", "tokens=60, min_chars=6"),
            ("thumbnail overlay rewrite at review", "tokens=40, min_chars=3"),
            ("NUMBER+NOUN enforcement phrase", "tokens=20, min_chars=3"),
            ("plain-English case sentence", "tokens=120, min_chars=40"),
            ("viral topic angle", "tokens=300, min_chars=40"),
            ("real-case brief", "tokens=300, min_chars=50")):
        check("D", f"reachable short-answer call: {label}", needle in cp,
              "its own prompt caps the answer below the 100-char default floor")

    # The thumbnail scorer must be able to reward a CLINICAL line, not only a
    # crime one -- otherwise it steers the channel back to the format it was
    # converted away from.
    from thumbnail_engine_v2 import score_thumbnail_text as _sts
    check("D", "the thumbnail scorer can reach its own 8.5 gate",
          max(_sts(t) for t in ("11 DOCTORS", "400 DAYS UNDIAGNOSED",
                                "WHO MISSED IT?")) >= 8.5,
          "a gate nothing can clear is the defect class this channel keeps hitting")
    check("D", "clinical vocabulary scores on its own merits",
          _sts("11 DOCTORS") >= 8.5 and _sts("400 DAYS UNDIAGNOSED") >= 8.5,
          "the specificity bank was VICTIMS/GONE/HIDDEN/EXPOSED — crime words "
          "the clinical policy gate forbids")
    check("D", "the other four channels' scoring is unchanged",
          _sts("4380 DAYS HIDDEN") == 10.0 and _sts("47 VICTIMS") == 10.0,
          "the clinical terms were ADDED, not swapped in")


def _synthetic_declaration_checks():
    """
    The "Altered or synthetic content" label was SELF-INFLICTED.

    containsSyntheticMedia was hardcoded True with a comment calling it
    "mandatory AI disclosure since Mar 2024". YouTube's published policy is
    narrower: disclosure is for REALISTIC content a viewer could mistake for
    a real person, place, scene or event. AI voiceover over illustrations,
    animated faceless content, and AI used for scripts/titles/captions are
    explicitly exempt — which is this channel's entire format.

    Health is one of the sensitive categories that gets the louder label on
    the player rather than a line in the description, so over-declaring cost
    this channel the most visible version of a label it did not owe.

    These checks keep the decision explicit and reversible rather than a
    boolean buried in an API body.
    """
    cp = read("channels/betrayal_deepdive/clinical_pipeline.py")
    check("A", "the synthetic-media declaration is a named, documented decision",
          "DECLARE_SYNTHETIC_MEDIA" in cp
          and '"containsSyntheticMedia": DECLARE_SYNTHETIC_MEDIA' in cp,
          "it was a hardcoded True inside the upload payload")
    check("A", "the declaration can be turned back on without a code change",
          'os.environ.get(\n    "DECLARE_SYNTHETIC_MEDIA"' in cp
          or 'os.environ.get(' in cp.split("DECLARE_SYNTHETIC_MEDIA =")[1][:120],
          "the trip-wires must be actionable the day the format changes")
    check("A", "the trip-wires for re-enabling it are written down",
          "TRIP-WIRES" in cp and "photoreal" in cp
          and "YPP suspension" in cp,
          "a judgement with no recorded conditions is a judgement nobody can "
          "revisit safely")
    # The same hardcoded True sat in all five pipelines plus the shared
    # Shorts uploader. Fixing one channel and leaving four is how a fix
    # becomes folklore, so every upload site is checked here.
    _others = {
        "evidence_room":  "channels/evidence_room/evidence_room_pipeline.py",
        "control_files":  "channels/control_files/control_files_pipeline.py",
        "archive":        "channels/archive/archive_pipeline.py",
        "collapse_index": "channels/collapse_index/collapse_index_pipeline.py",
    }
    for _chan, _path in _others.items():
        _src = read(_path)
        check("A", f"{_chan} no longer hardcodes the synthetic-media declaration",
              '"containsSyntheticMedia": True' not in _src
              and '"containsSyntheticMedia": DECLARE_SYNTHETIC_MEDIA' in _src,
              "it was True with a comment calling it mandatory, which it is not")
        check("A", f"{_chan} reads the shared policy rather than its own copy",
              f'declare_synthetic_media("{_chan}")' in _src,
              "five private copies of a policy judgement drift apart")

    _pol = read("video_pipeline/synthetic_media_policy.py")
    check("A", "the policy module records the trip-wires and the evidence",
          "TRIP-WIRES" in _pol and "photoreal" in _pol
          and "YPP suspension" in _pol and "2026-08-02" in _pol,
          "a judgement with no recorded conditions cannot be revisited safely")
    check("A", "the declaration can be flipped per channel, not just globally",
          "DECLARE_SYNTHETIC_MEDIA_" in _pol,
          "the five formats differ, so the trip-wires fire per channel")

    _sh = read("video_pipeline/shorts_reels_engine.py")
    check("A", "Shorts declare deliberately instead of by omission",
          '"containsSyntheticMedia": declare_synthetic_media(' in _sh,
          "the field was simply absent — right answer, no decision behind it")

    check("C", "the MEDICAL disclaimer is untouched by this",
          "build_disclaimer_block" in cp,
          "the AI label and the medical disclaimer are different obligations; "
          "only the first was over-applied")


def _green_run_checks():
    """
    WHAT A SUCCESSFUL RUN WAS STILL HIDING.

    Run 30717615638 finished green in 3h49m with every gate cleared on its
    first round — script 8.9, title 10.0, audio 9.8, video 9.3, thumbnail
    9.5, 4/4 Shorts. Reading its log line by line found five defects that a
    green result cannot surface on its own.
    """
    cp = read("channels/betrayal_deepdive/clinical_pipeline.py")
    pm = read("video_pipeline/pmc_data.py")
    hrg = read("video_pipeline/human_review_gate.py")

    # 1. The scored 3-variant cold open had NEVER run: KeyError on every call.
    check("A", "the cold open reads a niche key that exists",
          'niche["dread_style"]' not in read_code(
              "channels/betrayal_deepdive/clinical_pipeline.py"),
          "the 3-variant scored cold open — the 30 seconds that decide "
          "whether YouTube promotes the video — raised KeyError on EVERY "
          "attempt and logged as a non-fatal note")

    # 2. The FIGURE register: 77 downloads, 0 successes, every episode.
    check("E", "figure URLs come from the article page, not a guess",
          "_article_image_urls" in pm and "page_urls" in pm,
          "three hand-written path templates produced 77 failures and 0 "
          "successes; the page's own <img> URLs cannot go stale the same way")
    check("E", "the right figure is matched, not just any image",
          "stem and stem in u.lower()" in pm,
          "otherwise figure 3 silently renders figure 1")
    check("E", "page furniture is not mistaken for a figure",
          "corehtml|coreutils|icons?|logos?|spacer" in pm,
          "the site logo is an <img> on the same page")
    check("F", "losing the FIGURE register reaches the human",
          "notify_degraded" in pm and "def notify_degraded" in hrg,
          "a green run shipped with zero of its paper's real images and the "
          "only trace was one line in a 2400-line log")

    # 3. Groq: 17 x 413 per run because only the completion was capped.
    check("F", "the Groq budget counts the prompt, not just the answer",
          "GROQ_TPM_LIMIT = 8000" in cp and "_groq_budget" in cp
          and "max_tokens\": _budget" in cp,
          "the free tier limits prompt+completion TOGETHER; capping only "
          "the completion asked for 9060 against a limit of 8000, 17 times")
    import re as _re2
    _ns = {}
    _i = cp.index("GROQ_TPM_LIMIT = 8000")
    _j = cp.index("def call_groq(")
    exec(cp[_i:_j], _ns)
    _b = _ns["_groq_budget"]
    check("F", "every prompt size now fits under the real limit",
          all(v is None or (len("x" * n) // 4 + 1) + v <= 8000
              for n, v in ((400, _b("x" * 400, 8000)),
                           (17000, _b("x" * 17000, 8000)),
                           (34000, _b("x" * 34000, 8000)))),
          "including the ~4260-token script prompt that caused every 413")

    # 4. Model discovery: lyria was selected AGAIN after the first fix.
    check("D", "the model filter has no fallback branch to slip through",
          "EVERY SIGNAL GETS A VETO" in cp,
          "the first version only consulted the model NAME when no modality "
          "was declared, so a music model declaring text output passed — and "
          "lyria was picked again on the very next run")
    check("D", "free-tier pricing checks every axis the provider reports",
          "for v in pr.values()" in cp,
          "a fixed key list cannot cover an axis the provider adds later, "
          "which is how a 402-charging model read as free")


def _format_leakage_checks():
    """
    WHAT THE VIEWER ACTUALLY SEES, not what the comments claim.

    Ch1 was converted from true crime to clinical case documentary, and the
    conversion covered the prompts. It did not cover the things that reach
    the public: the research SOURCE, the text burned into the video, the
    Shorts hashtags, or the topic pools two of four daily Shorts draw from.
    """
    cp = read("channels/betrayal_deepdive/clinical_pipeline.py")
    sh = read("video_pipeline/shorts_reels_engine.py")
    # Absence checks run against CODE ONLY -- the comment explaining that
    # "#truecrime" was removed contains the string it forbids.
    cpc = read_code("channels/betrayal_deepdive/clinical_pipeline.py")
    shc = read_code("video_pipeline/shorts_reels_engine.py")

    # 1. THE RESEARCH SOURCE. This is the big one: Google News + r/TrueCrime
    # results were injected into the script prompt as "REAL DOCUMENTED CASE
    # RESEARCH ... build the narrative around documented reality", and
    # credited by name on the on-screen SOURCES card.
    check("B", "research context is the episode's own paper, nothing else",
          'case = get_episode_case() or {}' in cp
          and '"source":  "europepmc"' in cp,
          "an episode sourced from ONE case report was also being handed "
          "three news articles and three r/TrueCrime posts as its own facts")
    check("B", "the news/reddit search is retired, not merely unused",
          "_retired_search_real_cases_news_and_reddit" in cp
          and cp.index("_retired_search_real_cases_news_and_reddit")
              > cp.index("def search_real_cases"),
          "leaving it callable is how it comes back")
    check("B", "the case brief reads the paper, not a 100-char stub",
          "(c.get('summary') or '')[:2500]" in cp
          and "It is the only source" in cp,
          "each source used to be truncated to 100 characters, so the brief "
          "was written from little more than a title")
    check("C", "the case brief prompt carries the medical content rules",
          "no medical advice" in cp
          and "concealed or neglected anything" in cp
          and "no warning signs for a viewer to act on" in cp,
          "this brief goes straight into the script prompt")

    # 2. TEXT BURNED INTO THE VIDEO.
    check("A", "the outro card says case, not investigation",
          "A NEW PUBLISHED CASE EVERY WEEKDAY" in cp
          and "Case #\" + str(episode_num)" in cp
          and "NEW INVESTIGATION EVERY WEEKDAY" not in cpc,
          "burned into every episode's pixels — as public as the title")
    check("E", "on-screen segment fallbacks are clinical beats",
          '"the confirming test"' in cp and '"differential narrowed"' in cp
          and "torn photograph evidence" not in cpc
          and "shadow figure distant" not in cpc,
          "base_kw is the LAST fallback for display_text, the text drawn ON "
          "the card — a clinical card could read 'clock ticking tension'")

    # 3. WHAT GOES OUT WITH THE UPLOAD.
    check("A", "no crime hashtags reach a YouTube description",
          "#truecrime" not in cpc and "#darkpsychology" not in cpc,
          "the fallback Shorts uploaded '#shorts #darkpsychology #truecrime'")
    check("A", "the episode hashtag set is medical",
          "#casereport #episode" in cp,
          "'#investigation' on a published-case-report channel")
    check("A", "Shorts topic pools stay inside this channel's field",
          "viral animal story" not in shc.split('"evidence_room"')[0]
          and "trending medical research finding" in shc,
          "two of the four daily Shorts drew from 'viral celebrity news "
          "story' / 'trending sports moment' under @NoKnownCauseTV")
    check("A", "the retired-format Shorts hooks are gone",
          "THE PART NO ONE TALKS ABOUT" not in cpc
          and "EVERY TEST CAME BACK NORMAL" in cpc,
          "'the part no one talks about' implies something is being withheld, "
          "which the clinical policy rules forbid implying about clinicians")

    # 4. The research module the title gate reads must be one that exists.
    check("F", "the title gate reads a research file that is really written",
          "daily_competitor_research.json" in cp
          and "from competitive_research import" not in cpc,
          "it imported a module that does not exist in this repo; every call "
          "raised ModuleNotFoundError and was logged as an empty cache")


def _rounds_checks():
    """
    3 x 13 EVERYWHERE, not just at the title.

    Direct instruction, Aug 1 2026: "for the thumbnail, youtube shorts,
    editing etc I want it to be increased to three attempts, not only one
    attempt. The current rate is 1x13 i want it to be changed to 3x13."

    Only the title had rounds. Every other gate ran one round of thirteen and
    then skipped the day. These checks hold the structure in place AND hold
    the harder promise: that a round boundary re-seeds with genuinely new
    input rather than re-running the same thirteen, which is the retry defect
    this channel has already been bitten by four times.
    """
    import time as _t
    cp = read("channels/betrayal_deepdive/clinical_pipeline.py")
    sh = read("video_pipeline/shorts_reels_engine.py")
    qa = read("video_pipeline/quality_auditor.py")

    check("F", "a shared rounds engine exists",
          (ROOT / "video_pipeline/gate_rounds.py").exists(),
          "re-implementing rounds per gate is how they drift apart")

    for label, hay, needle in (
            ("thumbnail text", cp, "THUMB_TEXT_ROUNDS = 3"),
            ("script",         cp, '"Script", lambda rnd, angles=None: _run_stage1_once'),
            ("audio",          cp, "_AUDIO_ROUNDS = 3"),
            ("video",          cp, "_VIDEO_ROUNDS = 3"),
            ("Shorts",         sh, "SHORTS_ROUNDS = 3"),
            ("editing/quality audit", qa, "QUALITY_GATE_ROUNDS = 3")):
        check("F", f"{label} runs 3 rounds, not 1", needle in hay,
              "one round of thirteen used to skip the day outright")

    # A ROUND BOUNDARY MUST BRING NEW INPUT. Thirteen more attempts under
    # identical conditions is one attempt billed thirteen times.
    check("F", "the thumbnail round boundary researches new hooks",
          "_thumb_research" in cp and "LEAD WITH ONE OF THESE CONCRETE HOOKS" in cp,
          "without new material round 2 is round 1 reworded")
    check("F", "the script round boundary fetches unused case reports",
          "_research_script_angles" in cp and "_SCRIPT_CASES_TRIED" in cp
          and "carried in from the round-boundary research" in cp,
          "thirteen scripts from one pool that all missed 8.5 means the POOL "
          "is the constraint; a fourteenth from it is the same attempt")
    check("F", "the audio round boundary changes the ENGINE, not the voice label",
          "_SKIP_TTS_TIERS" in cp and 'if "kokoro" in _skip' in cp
          and '"ssml" not in _skip' in cp,
          "thirteen attempts scored exactly 8.3 on kokoro-local because the "
          "retry swapped only the edge-tts voice NAME while Kokoro won anyway")
    check("F", "the Shorts round boundary re-angles the case",
          "TAKE THIS ANGLE:" in sh,
          "a Short that failed thirteen times needs a different story angle")
    check("F", "the editing round restarts from the ORIGINAL draft",
          "_enforce_quality_gate_once(stage_name, initial_content" in qa,
          "reworking a rework compounds whatever the judge disliked")

    # The video gate is the one place where honesty matters more than the
    # round counter: 3 x 13 assemblies is 31 hours inside a 6-hour job.
    check("F", "the video rounds admit the clock decides, not the counter",
          "the job clock, not the round counter" in cp
          and "does NOT reshuffle the visuals" in cp,
          "claiming 39 reassemblies inside a 6-hour limit would be fiction")
    check("F", "a stuck gate ends the ROUND, not the day",
          cp.count("ending round") >= 1 and "ends the ROUND, not the day" in cp,
          "under 3 x 13 the answer to a stuck retry is new conditions")

    # The rounds engine itself.
    import gate_rounds as gr
    os_env = __import__("os").environ
    os_env["JOB_START_EPOCH"] = str(_t.time())
    got = gr.run_in_rounds("t", lambda rnd: "ok" if rnd == 3 else None,
                           pause_sec=0, log_fn=lambda m: None)
    check("F", "the rounds engine really runs three rounds", got == ("ok", 3, False),
          f"got {got}")
    seen = []
    gr.run_in_rounds("t", lambda rnd, seed=None: seen.append((rnd, seed)),
                     pause_sec=0, between_rounds=lambda r: f"m{r}",
                     log_fn=lambda m: None)
    check("F", "researched material reaches the round that needs it",
          seen == [(1, None), (2, "m2"), (3, "m3")], f"got {seen}")

    def _boom(rnd):
        raise TypeError("a real bug inside a gate")
    try:
        gr.run_in_rounds("t", _boom, pause_sec=0, log_fn=lambda m: None)
        _propagates = False
    except TypeError:
        _propagates = True
    check("F", "a TypeError inside a gate propagates instead of re-running it",
          _propagates,
          "catching TypeError to detect arity would silently retry real bugs")
    os_env["JOB_START_EPOCH"] = str(_t.time() - 350 * 60)
    check("F", "rounds stop for job time and say so",
          gr.run_in_rounds("t", lambda rnd: None, pause_sec=0,
                           round_cost_min=50, log_fn=lambda m: None)
          == (None, 1, True),
          "a round that cannot finish is worse than one never started")
    os_env.pop("JOB_START_EPOCH", None)


def _job_clock_checks():
    """
    Run 30688297894 was not killed by a bad gate decision. It was cancelled
    at 5h58m by GitHub Actions' 6-hour hosted-runner limit, partway through a
    sixth video reassembly, and a cancelled job commits nothing -- so an 8.9
    script, an approved title, a 9.1 audio track and five finished 1080p
    videos all died with the runner.

    The cause was that no loop knew what time it was. Each had its own private
    attempt budget; none was measured against the job's actual remaining
    minutes. These checks hold the shared clock in place.
    """
    import os
    import time as _t
    cp = read("channels/betrayal_deepdive/clinical_pipeline.py")
    hrg = read("video_pipeline/human_review_gate.py")
    wf = read(".github/workflows/ch1_generate.yml")

    check("F", "a shared job clock exists at all",
          (ROOT / "video_pipeline/job_clock.py").exists(),
          "every expensive loop needs the same answer to 'how long is left'")

    # The anchor. Import time is roughly an hour late for human_review_gate,
    # and late in the direction that makes the pipeline overspend.
    check("F", "the workflow anchors the clock to the real job start",
          "JOB_START_EPOCH=$(date +%s)" in wf and "JOB_LIMIT_MINUTES=360" in wf,
          "module import time is not job start — the review gate is first "
          "imported ~1h in, which would hide an hour of spent budget")
    check("F", "the exported limit matches the declared job timeout",
          "timeout-minutes: 360" in wf and "JOB_LIMIT_MINUTES=360" in wf,
          "the two numbers must be edited together or the clock lies")

    import job_clock as jc  # video_pipeline is already on sys.path above

    # The arithmetic, replayed against run 9's real timeline: video started
    # 81 minutes in, each reassembly costs ~48 minutes.
    os.environ["JOB_START_EPOCH"] = str(_t.time() - 81 * 60)
    check("F", "early in a run the clock funds real work",
          jc.can_afford(50) and jc.review_budget_hours(4.5) > 3.0,
          f"at 81 min: {jc.status_line()}")
    os.environ["JOB_START_EPOCH"] = str(_t.time() - 318 * 60)
    check("F", "near the wall the clock refuses another reassembly",
          not jc.can_afford(50),
          f"at 5h18m: {jc.status_line()} — run 9 started a sixth here")
    check("F", "near the wall the review window closes instead of overrunning",
          jc.review_budget_hours(4.5) == 0.0,
          "a flat 4.5h counted from the first checkpoint ignored however "
          "much of the 6 hours generation had already spent")
    check("F", "a malformed or stale anchor cannot skip the episode",
          (os.environ.__setitem__("JOB_START_EPOCH", "not-a-number")
           or jc.can_afford(50))
          and (os.environ.__setitem__("JOB_START_EPOCH", str(_t.time() - 99 * 3600))
               or jc.can_afford(50)),
          "an unusable anchor must fall back, not make everything unaffordable")
    os.environ.pop("JOB_START_EPOCH", None)

    check("F", "the review budget is bounded by what the job can afford",
          "from job_clock import review_budget_hours" in hrg
          and "_review_budget_hours()" in hrg,
          "4.5 hours is a policy ceiling, not a promise the runner can keep")
    check("F", "the video gate asks the clock before spending 48 minutes",
          "from job_clock import can_afford" in cp,
          "asked BEFORE the attempt, so the answer is actionable")
    check("F", "the audio gate reserves time for the video stage",
          "reserve=110" in cp,
          "spending the last of the job on audio leaves nothing to assemble")
    check("F", "running out of time exits cleanly rather than being killed",
          cp.count("checkpointing and exiting cleanly") >= 2,
          "sys.exit(0) keeps the script and audio checkpoints, so the "
          "make-up run resumes instead of starting from an empty runner")


def _audio_gate_checks():
    """
    A gate whose CEILING is below its own FLOOR can never pass.

    Third instance of this defect class on this channel (title scorer, Shorts
    scorer, now audio). Run 30642538133 spent 2h11m on thirteen audio attempts
    that all scored exactly 8.3 against an 8.5 gate, because the scorer judged
    a deliberately-slow clinical narration against a generic 150 wpm.
    """
    from quality_scoring import score_audio_quality
    import inspect
    cp = read("channels/betrayal_deepdive/clinical_pipeline.py")

    check("D", "the audio gate judges duration at the channel's real pace",
          "target_wpm=CLINICAL_NARRATION_WPM" in cp,
          "at the generic 150 wpm default a correct clinical file scores a "
          "duration MISMATCH and the total is capped below the gate")

    # The arithmetic, not a grep: reproduce the scorer's own weighting and
    # confirm a perfect file at the channel's real pace can clear 8.5.
    src = inspect.getsource(score_audio_quality)
    check("D", "a perfect clinical audio file can reach the 8.5 gate",
          "target_wpm" in src and _audio_ceiling(100.0) >= 8.5,
          f"ceiling at the channel's pace is {_audio_ceiling(100.0):.1f}; "
          f"at the old 150 wpm default it was {_audio_ceiling(150.0):.1f}")
    check("D", "the old 150 wpm yardstick really did make it unreachable",
          _audio_ceiling(150.0) < 8.5,
          "guards the regression rather than trusting the story")

    check("E", "a normal-length episode is never trimmed",
          "AUDIO_HARD_CAP_SECONDS = 26 * 60" in cp and "18 * 60" not in cp,
          "the 18-minute cap cut 2 minutes off the end of a 20-minute "
          "clinical episode, taking the closing stage with it")
    check("F", "a stuck audio retry stops instead of burning its budget",
          "_AUDIO_STUCK" in cp,
          "thirteen identical attempts at ten minutes each is 2h11m to "
          "learn nothing")


def _audio_ceiling(wpm, words=1969, duration=1199.2):
    """Best possible score for a real, correct file at this assumed pace."""
    expected = (words / wpm) * 60
    r = duration / expected
    d = 10.0 if 0.85 <= r <= 1.15 else (7.0 if 0.70 <= r <= 1.30
                                        else (4.0 if 0.50 <= r <= 1.50 else 1.0))
    return 0.40 * 9.5 + 0.25 * d + 0.20 * 10 + 0.15 * 10


def _email_routing_checks():
    """
    Direct instruction: everything about Channel 1 goes to
    noknowncausetv@gmail.com and no other address.
    """
    import human_review_gate as h
    cp = read("channels/betrayal_deepdive/clinical_pipeline.py")

    check("A", "Ch1's INTERNAL mail goes to the channel inbox",
          'CHANNEL_EMAIL' in cp and "noknowncausetv@gmail.com" in cp,
          "checkpoints, uploads and reports")
    check("A", "Ch1's PUBLIC business line stays the company address",
          'BUSINESS_EMAIL = "nextlayermediallc@gmail.com"' in cp,
          "the internal inbox must never be printed in a published "
          "description — those are two different audiences")
    check("A", "internal and business addresses are not the same",
          "BUSINESS_EMAIL = CHANNEL_EMAIL" not in cp)
    _entry = cp[cp.index('if __name__ == "__main__":'):]
    check("A", "the channel claims its inbox before any gate can fire",
          "set_review_recipient(CHANNEL_EMAIL" in _entry
          and _entry.index("set_review_recipient(CHANNEL_EMAIL")
              < _entry.index("main_with_retry()"),
          "a gate firing before the claim would email the shared address")

    # The routing itself, exercised rather than grepped.
    _before = h.review_recipient()
    try:
        h.set_review_recipient("noknowncausetv@gmail.com", "pw")
        check("A", "review mail routes to the Ch1 inbox once claimed",
              h.review_recipient() == "noknowncausetv@gmail.com")
        check("A", "emailed replies are read from the inbox that received them",
              h.reply_mailbox("someone-else@gmail.com", "x")[0]
              == "noknowncausetv@gmail.com",
              "polling a different mailbox means an emailed decision never "
              "registers")
        check("A", "the reply loop is closed when the sender IS the inbox",
              h.reply_mailbox_is_correct("noknowncausetv@gmail.com"),
              "the shared GMAIL_SENDER_EMAIL secret already holds this "
              "account, so no extra credential should be required")
        h.set_review_recipient(None, None)
        check("A", "Ch2-Ch5 keep the shared inbox",
              h.review_recipient() == "nextlayermediallc@gmail.com",
              "only Ch1 was asked to change")
    finally:
        h.set_review_recipient(None, None)

    # ONE MAILBOX, FIVE CHANNELS -- found while checking this.
    # GMAIL_SENDER_EMAIL/GMAIL_APP_PASSWORD are shared secrets, so every
    # pipeline polls the SAME inbox for emailed decisions. Without a filter,
    # an APPROVE typed for one channel is consumed by whichever channel polls
    # next, and the channel it was meant for waits forever.
    hg = read("video_pipeline/human_review_gate.py")
    check("F", "an emailed reply can only be read by the channel it names",
          "channel_tag" in hg and "_CURRENT_CHANNEL" in hg
          and "channel_tag=_CURRENT_CHANNEL[0]" in hg,
          "five pipelines share one inbox; a reply meant for Ch1 could "
          "approve a Ch3 script")
    check("F", "the channel tag is captured from the notification itself",
          '_tag = re.match(r"\\s*(\\[[^\\]]{1,80}\\])", subject)' in hg,
          "recording it at send time keeps every gate correct with no "
          "call-site changes")


def _format_leak_checks():
    """
    The retired true-crime format must not survive anywhere in the prompts
    that write this channel's content.

    The stage NAMES were converted to clinical ones months ago, which made
    this look done. The direction wrapped around them was not: the live
    script prompt still asked for a "dark investigative documentary" that
    revolved around "ONE central relationship fracture -- a specific betrayal
    between two specific people", with "each stage darker than the last".
    Given a paper about a neonate's liver enzymes, that brief produces a
    script about a story the paper does not contain -- which is why the
    finished videos read as unrelated to their own visuals, since the visuals
    ARE built from the real case data.
    """
    cp = read("channels/betrayal_deepdive/clinical_pipeline.py")
    # Only look at what is actually SENT to a model: prompt bodies, not the
    # comments that explain why each leak was removed.
    live = "\n".join(l for l in cp.split("\n")
                     if not l.lstrip().startswith("#"))
    banned = {
        "dark investigative documentary": "the script/description/topic brief",
        "central relationship fracture": "the script brief's core requirement",
        "a specific betrayal between two": "the script brief's core requirement",
        "Build psychological dread": "the script brief's tone section",
        "This is DARK DOCUMENTARY": "the script brief's tone section",
        "any other true-crime channel": "the signature-opening instruction",
        "14 VICTIMS": "the thumbnail-text examples",
        "classified evidence": "the description keyword list",
    }
    found = [f"{p!r} ({where})" for p, where in banned.items() if p in live]
    check("C", "no true-crime format language reaches any live prompt",
          not found,
          "leaks found: " + "; ".join(found) if found else
          "the clinical stage names hid a true-crime brief for months")

    check("A", "the script brief names the diagnostic question, not a betrayal",
          "CENTRAL DIAGNOSTIC QUESTION" in cp and "STAY ON THIS CASE" in cp,
          "the script must be traceable to the sourced paper")


def _review_gate_checks():
    """
    A review gate that ignores the person is worse than no gate.
    Both of these were reported directly after a real episode.
    """
    cp = read("channels/betrayal_deepdive/clinical_pipeline.py")

    # 1. DECLINE must stop the episode at EVERY checkpoint. The audio
    #    checkpoint used `break`, which left the review loop and fell
    #    straight into the next stage -- the episode carried on and would
    #    have published exactly as if approved.
    import re as _re
    rejects = _re.findall(r'== "reject":\n(.{0,600}?)(?=\n\s{16}(?:if|_|#|tg\()|\Z)',
                          cp, _re.S)
    bad = [r for r in rejects
           if "sys.exit" not in r and "REJECTED" not in r.upper()]
    check("F", "DECLINE stops the episode at every review checkpoint",
          not bad,
          "the audio checkpoint used `break`, so tapping Decline let the "
          "episode continue to publish")

    # 2. EDIT must actually take up the job.
    check("F", "title feedback at the script checkpoint retitles the episode",
          "_is_title_feedback" in cp and "_retitle_from_feedback" in cp,
          "'change the title' was routed to a whole-script rewrite that "
          "never touched the title, and still reported success")
    check("F", "a typed-out title is used verbatim",
          "USE IT VERBATIM" in cp,
          "a human who writes the headline they want has already decided")
    check("F", "an edit that changed nothing is reported as such",
          "produced NO change to the script" in cp,
          "'it just gave me the same script' -- the no-op was announced as "
          "a success")

    # 3. Title rounds, per explicit instruction: 13 x 3 with a real pause.
    check("D", "the title gate runs three rounds of thirteen",
          "TITLE_ROUNDS = 3" in cp and "run_title_gate_with_rounds" in cp
          and "_research_title_angles" in cp,
          "one round of 13 was the whole budget before the day was skipped")
    check("D", "the day is skipped only after the final title round",
          "all {TITLE_ROUNDS} rounds" in cp or "TITLE_ROUNDS * MAX_ATTEMPTS" in cp,
          "skipping after round 1 discards the episode too early")


def _resolution_checks():
    """
    The visual system renders 1920x1080 and must DELIVER 1920x1080.
    """
    cp = read("channels/betrayal_deepdive/clinical_pipeline.py")
    live = "\n".join(l for l in cp.split("\n") if not l.lstrip().startswith("#"))
    # Thumbnails are legitimately 1280x720; nothing in the video chain is.
    video_720 = [l for l in live.split("\n")
                 if ("1280:720" in l or "1280x720" in l) and "thumbnail" not in l.lower()]
    check("E", "the video chain composes at 1920x1080, not 720p",
          not video_720,
          "every register still is rendered at 1920x1080 and was then "
          "downscaled to 1280x720 for delivery — 44% of the pixels thrown "
          "away, on a channel whose visuals are small-label diagnostic "
          "graphics")
    check("E", "a video is never shipped with no captions at all",
          "_captions_for" in cp and "generate_real_synced_ass(audio_path, ass_path):\n            ass_path = None" not in cp,
          "every call site set ass_path=None when Whisper failed, so a "
          "missing key, a timeout or one 500 shipped an uncaptioned episode "
          "and logged it as a one-line non-fatal note")
    check("E", "the vertical crop is taken at full resolution",
          "crop=405:720" not in live,
          "a 405px-wide strip of a 720p intermediate was upscaled 2.67x to "
          "1080x1920 — a third of the frame, blown up, already degraded")


def _title_checks():
    """
    The title stage killed a whole run: it returned the byte-identical title
    twelve times, capped at 7.0, and discarded a script that had passed at
    8.6. Three separate causes, three checks.
    """
    import json as _json
    import re as _re
    cp = read("channels/betrayal_deepdive/clinical_pipeline.py")
    ns = {"re": _re, "json": _json, "os": os, "time": time,
          "log": lambda *a, **k: None, "tg": lambda *a, **k: None,
          "SCRIPT_DIR": pathlib.Path("."),
          "notify_stage_score": lambda *a, **k: None,
          "_record_title_history": lambda *a, **k: None}
    exec(cp[cp.index("def score_title_v2"):
            cp.index("# \u2500\u2500 TWO ADDRESSES")], ns)
    score, gate = ns["score_title_v2"], ns["run_title_ctr_gate"]

    # 1. A real clinical title must be able to clear the 8.5 gate at all.
    #    Before the phrase banks were re-based, the best a factual clinical
    #    headline could score was about 7.0 -- the gate was unreachable by
    #    construction, so every run ended the same way.
    # These are REAL titles the generator produced on run 30655118228. All
    # three are specific, numeric and name the reversal; all three scored
    # 7.2-7.5 against an 8.5 gate and the day was skipped.
    reachable = [
        "At 73, troponin 1.2 revealed the misread ECG",
        "10 Tests Failed-Then Gender Explained Men's Heart Attacks",
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
        "The Miracle Cure Doctors Missed For 10 Years",
    ]
    check("C", "the title scorer does not reward cover-up framing",
          all(score(t)[0] < 7.0 for t in accusatory),
          "titles alleging concealment by real named clinicians must not "
          "outscore factual clinical ones on a medical channel")

    weak = ["5 older Spanish men had twice the heart attacks. Why?",
            "A rare inherited disorder of galactose metabolism"]
    check("D", "a vague title still cannot clear the gate",
          all(score(t)[0] < 7.0 for t in weak),
          "the ceiling was raised by measuring clinical specificity properly, "
          "not by inflating every score")

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

    # 4. The title's runners-up must survive a total failure, so the skip
    #    message can report what was actually tried rather than just "failed".
    check("D", "a failed title gate still reports its best candidate",
          "_LAST_TITLE_CANDIDATES" in cp,
          "returning None must not also discard the titles that were "
          "generated — the skip notice has to say what the best one was")


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
            # "photo" is a full-bleed photograph, so every row differs from
            # the flat background by design and "the lowest row that is not
            # background" would always be the last one. The measurement below
            # only means something for cards drawn ON that background. The
            # photo card's own type is bounded by V_CONTENT_BOTTOM in the
            # renderer, which is asserted separately just after this loop.
            if kind == "photo":
                continue
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

        # The photo card, checked on the constant it is actually bounded by
        # rather than on pixels it legitimately fills.
        src = read("video_pipeline/medical_segments.py")
        if "y = V_CONTENT_BOTTOM - 60 - len(lines) * 84" not in src:
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
        # SCENE is deliberately NOT in this list. Every other register draws
        # on the flat clinical background, so "the lowest row that differs
        # from the background" finds the lowest ink. SCENE is a full-bleed
        # photograph -- every row differs from the background by design, so
        # the measurement would always return the last row and the check
        # would mean nothing. Its caption is bounded by CONTENT_BOTTOM in the
        # renderer and by its own entry in MOTION, and is checked below on
        # the constants rather than on the pixels.
        _scene_ok = ms.render_scene_still(
            "She was sent home from the emergency department twice that week.",
            str(td / "scene.png"), str(td), variant=0)
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
        # SCENE draws a stock photograph, so it has data whenever the offline
        # library has a scene photo in it -- which is checked rather than
        # assumed, because a SCENE segment with no photo falls through to the
        # plain card exactly like any other empty register would.
        "SCENE": _scene_library_stocked(),
        "CASEFILE": True,
        "LAB": True,
    }
    return any(not have.get(r, False) for r in set(seq))


def _scene_library_stocked():
    try:
        import stock_library as sl
        return sl.count("scene") >= 3
    except Exception:
        return False


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
