#!/usr/bin/env python3
"""
Drive every renderer through structurally DIFFERENT cases and check invariants.

WHY
---
Every visual verification in this repo so far rests on exactly one fixture:
three figures, four differentials, six timeline events, six chart points, one
quote, a four-step pathway, a 1,193-word narrative. Real PMC papers are not
that. Looking at one shape found the dead CHART register, the orphan cues and
the zoom band -- all real, all found by looking. This drives the same code
through the shapes that fixture never exercises: no differentials, nine of
them, a forty-point series, a title long enough to wrap four times, step
names longer than their box, a citation with no periods, an empty case.

INVARIANTS, checked on the PIXELS of every frame
------------------------------------------------
  1. the renderer returns success and writes a real image
  2. no ink in the caption band AFTER that register's own zoom is applied
     (the bug class that survived a still-only check)
  3. no ink outside the horizontal margins -- text that runs off the frame
     edge is clipped text, which reads as a broken render
  4. no ink above the header line
  5. the frame is not blank (a "successful" render of nothing is a failure)
  6. the register schedule never assigns a register the case cannot render
  7. no register runs longer than MAX_RUN, and every reveal advances

Deterministic: each case has a fixed seed, so any failure is reproducible.

Usage: python3 tools/fuzz_case_shapes.py [--render-dir DIR] [--encode]
Exit:  0 all shapes pass, 1 otherwise

By default the ffmpeg clip encode is stubbed out. Every invariant here is
checked on the rendered STILL, and the zoom is applied arithmetically from
MOTION -- encoding ~430 twelve-second clips to look at nothing would turn a
90-second run into half an hour. --encode does the real thing; the full
episode render (tools/local_full_episode.py) already exercises that path.
"""
import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "video_pipeline"))
sys.path.insert(0, str(ROOT / "tools"))

from PIL import Image, ImageChops                      # noqa: E402
import medical_figure_render as mfr                    # noqa: E402
import medical_segments as ms                          # noqa: E402
from medical_register import new_quota, available_from_case   # noqa: E402
from local_episode_render import make_placeholder_figure      # noqa: E402

LOREM = ("The patient was admitted on the second day with a conjugated "
         "bilirubin of one hundred and forty micromoles per litre. ")

FAILURES = []
CHECKED = 0
ENCODE = False


def _stub_ffmpeg(cmd, label=""):
    """Skip the encode but satisfy still_to_clip's existence/size check."""
    Path(cmd[-1]).write_bytes(b"\0" * 2048)


def fail(shape, what, detail=""):
    FAILURES.append((shape, what, detail))


def _figs(n, work, seed=0):
    out = []
    kinds = ("portrait", "square", "wide")
    for i in range(n):
        p = Path(work) / f"pmcfig_{i}.jpg"
        make_placeholder_figure(p, kinds[i % 3], seed=seed + i)
        out.append({"pmcid": "PMC1", "filename": f"f{i}.jpg",
                    "label": f"Figure {i + 1}", "local_path": str(p),
                    "caption": ("Serial measurements from admission through "
                                "day twenty-one of life. " * (1 + i % 4))})
    return out


def shapes(work):
    """Every case shape worth exercising, with a name that says why."""
    long_title = ("An exceptionally protracted diagnostic odyssey in a "
                  "previously well adult presenting with recurrent "
                  "unexplained hypoglycaemia and progressive hepatic "
                  "dysfunction of uncertain aetiology")
    cases = []

    def C(name, **over):
        base = {
            "pmcid": "PMC1", "journal": "J Med Case Rep", "year": "2023",
            "title": "A rare inherited disorder of galactose metabolism",
            "citation": ("Okonkwo A, Vasquez M. A rare inherited disorder of "
                         "galactose metabolism. J Med Case Rep. 2023;17:214. "
                         "CC BY 4.0."),
            "narrative": LOREM * 12,
            "figures": [],
            "differentials": [("Neonatal sepsis", "EXCLUDED", "Cultures sterile"),
                              ("Biliary atresia", "EXCLUDED", "Normal gallbladder"),
                              ("Classic galactosaemia", "CONFIRMED",
                               "GALT undetectable")],
            "timeline": [("Day 2", "Poor feeding noted"),
                         ("Day 4", "Coagulopathy developed"),
                         ("Day 9", "Enzyme assay returned")],
            "chart_data": {"chart_type": "line", "title": "Serum values",
                           "y_label": "micromoles per litre",
                           "labels": ["Day 3", "Day 6", "Day 9"],
                           "values": [1240.0, 610.0, 95.0]},
            "anatomy": {"title": "GALT deficiency",
                        "explanation": "The intermediate accumulates and is toxic.",
                        "pathway": ["Lactose", "Galactose", "Gal-1-P"],
                        "blocked_step": 2},
            "quote": "The absence of infection redirected the investigation.",
        }
        base.update(over)
        cases.append((name, base))

    # ── the dimension this project has never varied ────────────────────
    C("figures=0", figures=[])
    C("figures=1", figures=_figs(1, work, 1))
    C("figures=12", figures=_figs(12, work, 2))

    C("differentials=0", differentials=[])
    C("differentials=1", differentials=[("Sepsis", "EXCLUDED", "Cultures sterile")])
    C("differentials=9", differentials=[
        (f"Candidate diagnosis number {i}", ["EXCLUDED", "PARTIAL", "CONFIRMED"][i % 3],
         "A reason that is really quite long and keeps going for a while " * (1 + i % 2))
        for i in range(9)])

    C("timeline=0", timeline=[])
    C("timeline=1", timeline=[("Day 2", "Poor feeding noted")])
    C("timeline=14", timeline=[
        (f"Day {i}", "A described event that runs on at some length indeed " * (1 + i % 3))
        for i in range(1, 15)])

    C("chart=none", chart_data=None)
    C("chart=2pts", chart_data={"chart_type": "bar", "title": "Two points",
                                "y_label": "units", "labels": ["A", "B"],
                                "values": [1.0, 2.0]})
    C("chart=40pts", chart_data={
        "chart_type": "line", "title": "A very long series of reported values",
        "y_label": "micromoles per litre of red cells, measured daily",
        "labels": [f"Day {i}" for i in range(1, 41)],
        "values": [float(1500 - i * 33) for i in range(40)]})
    C("chart=identical values", chart_data={
        "chart_type": "line", "title": "Flat", "y_label": "units",
        "labels": ["A", "B", "C"], "values": [7.0, 7.0, 7.0]})
    C("chart=huge numbers", chart_data={
        "chart_type": "bar", "title": "Counts", "y_label": "cells per litre",
        "labels": ["Day 1", "Day 2", "Day 3"],
        "values": [12400000.0, 980000.0, 4500.0]})
    C("chart=negative values", chart_data={
        "chart_type": "line", "title": "Base excess", "y_label": "mmol",
        "labels": ["Day 1", "Day 2", "Day 3"], "values": [-18.0, -6.0, 2.0]})

    C("quote=none", quote="")
    C("quote=very long", quote=(
        "The infant's deterioration continued despite broad-spectrum "
        "antibiotic therapy, and it was ultimately the absence of any "
        "identifiable infective organism, rather than the presence of one, "
        "that redirected the diagnostic pathway towards an inherited "
        "metabolic disorder of galactose handling."))

    C("pathway=none", anatomy={"title": "Mechanism",
                               "explanation": "Something accumulates.",
                               "pathway": None, "blocked_step": None})
    C("pathway=2 steps", anatomy={"title": "Mechanism", "explanation": "x",
                                  "pathway": ["In", "Out"], "blocked_step": 1})
    C("pathway=very long names", anatomy={
        "title": "Galactose-1-phosphate uridylyltransferase deficiency",
        "explanation": "The half-finished product of breaking it down is toxic "
                       "to liver and kidney cells and to the lens of the eye.",
        "pathway": ["Lactose from milk feeds", "Galactose in circulation",
                    "Galactose-1-phosphate intermediate",
                    "Glucose-1-phosphate for energy"],
        "blocked_step": 3})

    C("title=very long", title=long_title)
    C("citation=no periods", citation="Okonkwo A and Vasquez M 2023 CC BY 4 0")
    C("citation=missing", citation="")
    C("everything empty", figures=[], differentials=[], timeline=[],
      chart_data=None, quote="",
      anatomy={"title": "", "explanation": "", "pathway": None,
               "blocked_step": None})
    C("everything rich", figures=_figs(6, work, 9), differentials=[
        (f"Diagnosis {i}", ["EXCLUDED", "PARTIAL", "CONFIRMED"][i % 3], "reason")
        for i in range(5)],
      timeline=[(f"Day {i}", "event") for i in range(1, 7)],
      chart_data={"chart_type": "line", "title": "Values", "y_label": "u",
                  "labels": [f"D{i}" for i in range(8)],
                  "values": [float(100 - i * 9) for i in range(8)]})
    return cases


def ink_box(path, bg):
    """
    Bounding box of everything that differs from the background by more than
    12 in ANY channel. Done through ImageChops so it runs in C -- the
    equivalent Python double loop cost about four of the five minutes this
    whole fuzz run used to take.
    """
    im = Image.open(path).convert("RGB")
    diff = ImageChops.difference(im, Image.new("RGB", im.size, bg))
    mask = None
    for band in diff.split():
        b = band.point(lambda v: 255 if v > 12 else 0)
        mask = b if mask is None else ImageChops.lighter(mask, b)
    return mask.getbbox() and tuple(
        v - (1 if i >= 2 else 0) for i, v in enumerate(mask.getbbox()))


# Registers whose frame IS the picture. Every invariant in check_frame() is
# built on ink_box(), which finds the bounding box of everything that differs
# from the flat clinical background -- a sound measure for a card DRAWN on
# that background, and meaningless for a full-bleed photograph, where every
# pixel differs by design. Adding the photographic SCENE/PHOTO cards produced
# 150 identical "failures" saying the photo reached the edge of the frame,
# which is what a photograph is supposed to do.
#
# These are not skipped, they are checked on the thing that can actually be
# wrong: their TYPE has to stay above the burned-in caption band, which is
# bounded by CONTENT_BOTTOM in the renderer and asserted in the audit.
FULL_BLEED = {"SCENE", "PHOTO"}


def check_frame(shape, reg, path, horizontal=True):
    """The five pixel invariants."""
    global CHECKED
    CHECKED += 1
    if reg in FULL_BLEED:
        if not Path(path).exists() or Path(path).stat().st_size < 500:
            fail(shape, f"{reg}: no image written")
        return
    if not Path(path).exists() or Path(path).stat().st_size < 500:
        fail(shape, f"{reg}: no image written")
        return
    W = mfr.W if horizontal else ms.VW
    H = mfr.H if horizontal else ms.VH
    bottom = mfr.CONTENT_BOTTOM if horizontal else ms.V_CONTENT_BOTTOM
    ink_top = mfr.CAPTION_INK_TOP if horizontal else ms.V_CAPTION_INK_TOP
    zoom = (ms.MOTION.get(reg, {"max": 1.14})["max"] if horizontal
            else ms.V_MAX_ZOOM)
    top_limit = 40 if horizontal else 350

    box = ink_box(path, ms.BG)
    if box is None:
        fail(shape, f"{reg}: frame is blank")
        return
    minx, miny, maxx, maxy = box
    landed = H / 2 + (maxy - H / 2) * zoom
    if landed > ink_top - 1:
        fail(shape, f"{reg}: content reaches the caption band",
             f"lowest ink y={maxy}, lands at {landed:.0f} (caption {ink_top})")
    if minx < 40 or maxx > W - 40:
        fail(shape, f"{reg}: ink runs to the frame edge",
             f"x range {minx}..{maxx} of {W}")
    if miny < top_limit:
        fail(shape, f"{reg}: ink above the header", f"top y={miny}")
    if maxy - miny < 30:
        fail(shape, f"{reg}: frame is nearly empty",
             f"ink height {maxy - miny}px")


def run_shape(name, case, work):
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    avail = available_from_case(case)

    # ── horizontal registers ───────────────────────────────────────────
    for reg in ("FIGURE", "CHART", "BOARD", "TIMELINE", "ANATOMY", "TEXT"):
        if not avail.get(reg):
            continue
        for progress in (0.05, 0.5, 1.0):
            out = work / f"h_{reg}_{int(progress*100)}.png"
            try:
                ok = ms.render_medical_segment(
                    reg, case, "The patient deteriorated overnight and the "
                               "team requested a further set of cultures.",
                    12.0, 0, str(out.with_suffix(".mp4")), work_dir=str(work),
                    log_fn=lambda m: None, progress=progress, variant=0,
                    variant_total=6,
                    run_ffmpeg=None if ENCODE else _stub_ffmpeg)
            except Exception as e:
                fail(name, f"{reg}: raised", f"{type(e).__name__}: {e}")
                continue
            # render_medical_segment writes med_<idx>_<reg>.png
            still = work / f"med_0_{reg.lower()}.png"
            if not ok:
                fail(name, f"{reg}: returned False")
                continue
            if still.exists():
                check_frame(name, reg, still)

    # ── cards ──────────────────────────────────────────────────────────
    p = work / "title.png"
    try:
        if ms.render_title_card(case.get("title") or "", str(p),
                                source_line=f"{case.get('journal','')} "
                                            f"{case.get('year','')}".strip(),
                                citation=case.get("citation", "")):
            check_frame(name, "TITLE", p)
    except Exception as e:
        fail(name, "TITLE card raised", f"{type(e).__name__}: {e}")
    p = work / "act.png"
    try:
        if ms.render_act_card(3, "THE REVERSAL", str(p)):
            check_frame(name, "TITLE", p)
    except Exception as e:
        fail(name, "ACT card raised", f"{type(e).__name__}: {e}")

    # ── vertical (Shorts) ──────────────────────────────────────────────
    # Progress matters here: a progressive card only DRAWS the rows it has
    # reached, so the tallest the layout ever gets is at 1.0. Checking 0.6
    # alone missed a vertical timeline whose last event's description ran
    # into the Shorts caption band.
    for kind in ms.VERTICAL_SEQUENCE:
        for progress in (0.4, 1.0):
            p = work / f"v_{kind}_{int(progress*10)}.png"
            try:
                ok = ms.render_vertical_card(
                    kind, case, str(p),
                    headline=case.get("title") or "A published case",
                    progress=progress)
            except Exception as e:
                fail(name, f"vertical {kind}: raised", f"{type(e).__name__}: {e}")
                continue
            if not ok:
                fail(name, f"vertical {kind}: returned False")
                continue
            check_frame(name, kind.upper(), p, horizontal=False)

    # ── content survival ───────────────────────────────────────────────
    # A register that trims its input to fit the frame must not trim away the
    # part the episode is about. Both of these were head-slices until a
    # nine-differential and a fourteen-event case were run through them.
    global CHECKED
    diffs = case.get("differentials") or []
    if diffs:
        CHECKED += 1
        kept = ms._cap_differentials(diffs, 5)
        for row in diffs:
            if "confirm" in str(row[1]).lower() and row not in kept:
                fail(name, "BOARD dropped the CONFIRMED differential",
                     f"{row[0]!r} is not on the board")
    tl = case.get("timeline") or []
    if tl:
        CHECKED += 1
        rows, idx = mfr.condense_timeline(tl, 6)
        if idx and idx[-1] != len(tl) - 1:
            fail(name, "TIMELINE dropped the last event",
                 f"course ends at index {idx[-1]} of {len(tl)-1}")

    # ── scheduling ─────────────────────────────────────────────────────
    n = 54
    q = new_quota(n, figure_count=len(case.get("figures") or []), case=case)
    seq, reveals = [], {}
    for i in range(n):
        r = q.pick("the patient deteriorated overnight after the second dose")
        occ, exp = q.reveal(r)
        seq.append(r)
        reveals.setdefault(r, []).append(occ)
    for r in set(seq):
        if not avail.get(r):
            fail(name, f"scheduled {r} with no data",
                 "every one of those segments renders the fallback card")
    longest, cur = 1, 1
    for a, b in zip(seq, seq[1:]):
        cur = cur + 1 if a == b else 1
        longest = max(longest, cur)
    # MAX_RUN is only arithmetically keepable when a second register exists.
    # A case that renders exactly one register cannot alternate with anything,
    # and the pipeline now refuses such a case outright (see clinical_pipeline
    # step 2c) rather than shipping one visual for thirteen minutes.
    if q.max_run_enforceable:
        if longest > q.MAX_RUN:
            fail(name, "register run too long", f"{longest} > {q.MAX_RUN}")
        if q.forced_repeats:
            fail(name, "run cap breached despite an alternative existing",
                 f"{q.forced_repeats} forced repeats")
    elif len([r for r, ok in avail.items()
              if ok and r not in ("ANATOMY", "SCENE")]):
        fail(name, "quota collapsed to one register with data available",
             f"live={q.live_registers}")
    for r, v in reveals.items():
        if v != list(range(1, len(v) + 1)):
            fail(name, f"{r}: reveal does not advance monotonically", str(v[:8]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--render-dir")
    ap.add_argument("--encode", action="store_true",
                    help="actually encode each segment clip (slow)")
    args = ap.parse_args()
    global ENCODE
    ENCODE = args.encode

    import real_case_images
    real_case_images.search_wikimedia_commons = lambda *a, **k: (False, "")

    base = Path(args.render_dir) if args.render_dir else Path(tempfile.mkdtemp())
    base.mkdir(parents=True, exist_ok=True)
    figwork = base / "_figs"
    figwork.mkdir(exist_ok=True)

    all_shapes = shapes(figwork)
    print(f"Fuzzing {len(all_shapes)} case shapes through every renderer\n")
    for name, case in all_shapes:
        before = len(FAILURES)
        run_shape(name, case, base / name.replace("=", "_").replace(" ", "_"))
        n_new = len(FAILURES) - before
        print(f"  {'FAIL' if n_new else 'ok  '}  {name:26} "
              f"{f'{n_new} problem(s)' if n_new else ''}")

    print(f"\n  {CHECKED} frames checked across {len(all_shapes)} shapes")
    if FAILURES:
        print(f"\n  {len(FAILURES)} FAILURES:")
        for shape, what, detail in FAILURES:
            print(f"    [{shape}] {what}" + (f"  — {detail}" if detail else ""))
        return 1
    print("  no invariant violations")
    return 0


if __name__ == "__main__":
    sys.exit(main())
