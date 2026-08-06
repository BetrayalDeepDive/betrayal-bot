#!/usr/bin/env python3
"""
Everything that has to be true before Channel 1 runs for real.

    python3 tools/preflight_ch1_thumbnails.py

Each check is a thing that has actually broken, or that would break silently.
The point of running it before a test rather than after is that a thumbnail
defect is invisible in a log: the run goes green, the file is written, and the
fault only shows up when a human looks at the picture -- or, in the case of the
duration badge, only once the video is live.

Exit code 0 means the run is safe to start.
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "video_pipeline"))
sys.path.insert(0, os.path.join(ROOT, "channels"))

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append((name, detail))
    print("  %s  %-52s %s" % ("PASS" if ok else "FAIL", name, detail))


def main():
    print("\nCh1 thumbnail pre-flight\n" + "-" * 78)

    import photo_thumbnail as pt
    import presenter_library as pl
    import stock_library as sl
    import thumbnail_formats as tf
    import shorts_formats as sf

    # ── the five formats are the five that were chosen ─────────────
    chosen = ("reaction", "bubbles", "pointing", "verdict", "banner")
    check("five chosen formats in rotation", tuple(pt.FORMATS) == chosen,
          ", ".join(pt.FORMATS))
    pool = tf.CHANNEL_PREFERRED_FORMATS.get("No Known Cause", [])
    check("CTR learning pool matches the renderer's keys",
          set(pool) == set(chosen),
          "a mismatch means CTR attaches to a format that cannot be rendered")

    # ── the presenter library is intact ────────────────────────────
    poses = pl.poses()
    check("presenter poses present", len(poses) >= 23, "%d poses" % len(poses))
    missing = [n for n, p in poses.items()
               if not os.path.exists(os.path.join(pl.LIB, p["file"]))]
    check("every pose file on disk", not missing, ", ".join(missing[:4]))

    # ── the stock library can carry a run on its own ───────────────
    counts = {r: sl.count(r) for r in sl.ROLES}
    check("stock library covers scene + evidence",
          counts["scene"] >= 3 and counts["evidence"] >= 3, str(counts))

    # ── render every format with the network dead ──────────────────
    def dead(q, niche, out):
        raise RuntimeError("preflight: pretending the API is down")

    work = tempfile.mkdtemp()
    photos = pt.resolve_photos(dead, "brain lesion mri", "neurology_cases",
                               work, log=lambda m: None)
    check("photos resolve with no network", set(photos) >= {"scene", "evidence"},
          "roles: %s" % ", ".join(sorted(photos)))

    results = {}
    for fmt in pt.FORMATS:
        try:
            r = pt.render(os.path.join(work, fmt + ".jpg"),
                          "Every test came back clean and nobody could say why",
                          photos, fmt=fmt, episode=3, kicker="CASE 03")
            results[fmt] = r
        except Exception as e:
            check("render %s" % fmt, False, repr(e))
    check("all five formats render offline", len(results) == len(pt.FORMATS),
          "%d/%d" % (len(results), len(pt.FORMATS)))

    if results:
        check("nothing under YouTube's duration badge",
              all(r["badge_clear"] for r in results.values()),
              "badge covers the bottom-right corner in every feed")
        check("headline never exceeds the word cap",
              all(r["words"] <= pt.MAX_WORDS for r in results.values()),
              "max %d words" % max(r["words"] for r in results.values()))
        worst = min(r["contrast_120px"] for r in results.values())
        check("legible at 120px", worst >= 45, "worst %.1f" % worst)

    # ── a drawing can never reach a card ───────────────────────────
    from PIL import Image, ImageDraw
    flat = os.path.join(work, "flat.png")
    im = Image.new("RGB", (900, 600), (232, 240, 250))
    ImageDraw.Draw(im).ellipse([200, 150, 700, 450], fill=(200, 40, 40))
    im.save(flat)
    check("a flat drawing is detected", pt.looks_drawn(flat),
          "vector diagrams must never reach a thumbnail")
    check("a photograph is not mistaken for a drawing",
          not pt.looks_drawn(photos["scene"]))

    # ── both learning loops are wired, not just present ────────────
    for mod, label in ((tf, "long-form"), (sf, "shorts")):
        have = all(hasattr(mod, f) for f in
                   ("record_format_used", "record_format_ctr", "attach_video_id"))
        check("%s CTR loop complete" % label, have,
              "record + attach + feedback")

    src = open(os.path.join(ROOT, "video_pipeline", "growth_engine.py")).read()
    check("shorts CTR is fed from YouTube Analytics",
          "from shorts_formats import record_format_ctr" in src,
          "without this the Shorts history never learns")
    src2 = open(os.path.join(ROOT, "video_pipeline",
                             "shorts_reels_engine.py")).read()
    check("shorts video_id is attached after upload",
          "attach_video_id as _attach_short" in src2)

    # ── the pipeline actually calls the new renderer ───────────────
    src3 = open(os.path.join(ROOT, "channels", "betrayal_deepdive",
                             "clinical_pipeline.py")).read()
    check("Ch1 pipeline calls the photographic renderer",
          "import photo_thumbnail as _pt" in src3)
    check("Ch1 pipeline records the format for CTR learning",
          "record_format_used(_cache" in src3)

    print("-" * 78)
    print("  %d passed, %d failed\n" % (len(PASS), len(FAIL)))
    if FAIL:
        print("  NOT READY:")
        for n, d in FAIL:
            print("    - %s %s" % (n, ("(%s)" % d) if d else ""))
        return 1
    print("  Ready for a real run.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
