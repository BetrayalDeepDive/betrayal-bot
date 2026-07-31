#!/usr/bin/env python3
"""
Calibrate (or re-check) SPECIFICITY_TARGET_PER_100W against real scripts.

WHY THIS IS A TOOL AND NOT A NUMBER IN A COMMENT
------------------------------------------------
This threshold has been wrong twice. 6.0 was picked with no evidence. 3.0
was picked against two references, one of which I wrote and one of which was
synthetic, using a detector that was itself broken. Both times the number
looked reasonable in a comment and was not.

The fix is not a better guess. It is to derive the number from every real
script available and to make that derivation re-runnable, so it can be
re-checked the moment more scripts exist instead of ossifying in a docstring.

THE EVIDENCE IT USES
--------------------
Every `script_clean` in channels/*/pending_upload.json. These are REAL
model-generated production scripts -- not written by me, not synthetic. They
are all non-clinical (the other four channels), which makes them the exact
negative control this metric needs: they show what the model's ordinary
documentary prose scores when it is NOT talking about a clinical case.

The positive reference is still a single clinical sample, which is the one
remaining weakness and is reported as such. When real accepted clinical
scripts exist, drop them in and re-run.

Usage: python3 tools/calibrate_specificity.py
Exit:  0 if the configured threshold is supported by the evidence, 1 if not
"""
import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "video_pipeline"))
sys.path.insert(0, str(ROOT / "tools"))

import clinical_quality as cq                     # noqa: E402
from local_episode_render import NARRATION        # noqa: E402

# How far above the real non-clinical ceiling the "full marks" threshold must
# sit. The metric's job is to distinguish clinical density from ordinary
# documentary prose; if the threshold is not comfortably clear of what
# non-clinical prose actually scores, it is measuring noise.
MIN_SEPARATION_FACTOR = 4.0

# A genuinely detailed clinical episode should score well but NOT max out --
# a metric with no headroom cannot tell good from excellent.
CLINICAL_BAND = (7.5, 9.6)


def real_non_clinical():
    out = []
    for f in sorted(glob.glob(str(ROOT / "channels/*/pending_upload.json"))):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        s = d.get("script_clean") or ""
        if len(s.split()) < 400:
            continue
        _, c = cq.clinical_specificity(s)
        out.append((Path(f).parent.name, len(s.split()), c["per_100_words"]))
    return out


def main():
    non_clinical = real_non_clinical()
    if not non_clinical:
        print("No real scripts found in channels/*/pending_upload.json.")
        print("Cannot calibrate from evidence; leaving the threshold alone.")
        return 0

    print("REAL model-generated scripts (non-clinical — the negative control):")
    for name, words, per100 in non_clinical:
        pts, _ = cq.clinical_specificity("x " * 10)  # keep import warm
        print(f"  {name:16} {words:5}w   {per100:5.2f} /100w")
    ceiling = max(p for _, _, p in non_clinical)
    print(f"  -> real non-clinical CEILING: {ceiling:.2f} /100w")

    pts, c = cq.clinical_specificity(NARRATION)
    clinical = c["per_100_words"]
    print(f"\nClinical reference (1 sample, authored — the weak link):")
    print(f"  {len(NARRATION.split()):5}w   {clinical:5.2f} /100w")
    print(f"  -> separation from real non-clinical: {clinical / max(0.01, ceiling):.1f}x")

    t = cq.SPECIFICITY_TARGET_PER_100W
    print(f"\nConfigured threshold: {t}")
    ok = True

    sep = t / max(0.01, ceiling)
    if sep < MIN_SEPARATION_FACTOR:
        print(f"  FAIL threshold is only {sep:.1f}x the real non-clinical "
              f"ceiling (need >= {MIN_SEPARATION_FACTOR})")
        ok = False
    else:
        print(f"  ok   {sep:.1f}x the real non-clinical ceiling")

    worst_nc = max(min(10.0, p / t * 10.0) for _, _, p in non_clinical)
    if worst_nc > 2.5:
        print(f"  FAIL a real non-clinical script scores {worst_nc:.1f}/10")
        ok = False
    else:
        print(f"  ok   the best-scoring non-clinical script gets "
              f"{worst_nc:.1f}/10")

    cl_score = min(10.0, clinical / t * 10.0)
    if not (CLINICAL_BAND[0] <= cl_score <= CLINICAL_BAND[1]):
        print(f"  FAIL the clinical reference scores {cl_score:.1f}/10 "
              f"(want {CLINICAL_BAND[0]}-{CLINICAL_BAND[1]}: clearly good, "
              f"with headroom above)")
        ok = False
    else:
        print(f"  ok   the clinical reference scores {cl_score:.1f}/10 "
              f"— good, with headroom")

    suggested = round(clinical / 0.88, 1)
    print(f"\n  threshold that would place the clinical reference at 8.8/10: "
          f"{suggested}")
    print("\n  REMAINING WEAKNESS: one clinical reference, and I wrote it.")
    print("  Add real accepted clinical scripts and re-run this.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
