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
    check("E", "avatar resolves for the live channel name",
          te.get_channel_avatar_prompt("No Known Cause", 1)[0] is not None)
    check("E", "register mix sums to 1.0",
          abs(sum(TARGET_MIX.values()) - 1.0) < 0.01)

    # With no figures, FIGURE must not be assigned.
    q = new_quota(60, figure_count=0)
    picks = [q.pick("the patient deteriorated overnight") for _ in range(60)]
    check("E", "no FIGURE segments when the paper has none",
          "FIGURE" not in picks, str(set(picks)))


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
               audit_scoring, audit_visuals, audit_integration):
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
