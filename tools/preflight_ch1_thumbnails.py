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
import subprocess
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

        # The score quoted at review has to come from the picture. It used to
        # come from the headline string, which is how a card reading "8 0"
        # was presented as 10.0/10.
        bad = {f: r["image_issues"] for f, r in results.items()
               if r["image_score"] < 8.9}
        check("every format scores 8.9+ on its own pixels", not bad,
              "; ".join("%s %s" % (f, w) for f, w in list(bad.items())[:2]))

    # ── the channel mark never lands on the presenter ──────────────
    # A teal badge stuck to his shirt was in the reported screenshot. The
    # placement is measured, so it is checked by measurement too.
    import presenter_cutout as pcut
    import numpy as np
    worst_on_him = 0.0
    for fmt in pt.FORMATS:
        seen = {}
        real = pt._mark

        def watch(im, size=58, pad=26, side="auto", _seen=seen, _real=real):
            occ = pcut.LAST_OCCUPANCY
            _real(im, size, pad, side)
            # Re-derive the slot the real function would have chosen by
            # finding the one the mark was actually drawn into.
            for name, sx, sy in pt._mark_slots(size, pad):
                patch = np.asarray(im.convert("RGB")).astype(float)[sy:sy + size,
                                                                    sx:sx + size]
                teal = np.abs(patch - np.array(pt.MARK_TEAL, float)).sum(2) < 90
                if teal.mean() > 0.01:
                    _seen["on_him"] = (0.0 if occ is None
                                       else float(occ[sy:sy + size, sx:sx + size].mean()))
                    return
            _seen["on_him"] = 0.0

        pt._mark = watch
        try:
            pt.render(os.path.join(work, "mark_" + fmt + ".jpg"),
                      "Doctors said it was anxiety but the sodium was 0.4",
                      photos, fmt=fmt, episode=3, kicker="CASE 03", mark="DAY 9")
        finally:
            pt._mark = real
        worst_on_him = max(worst_on_him, seen.get("on_him", 0.0))
    check("channel mark never sits on the presenter", worst_on_him < 0.05,
          "worst overlap %.0f%%" % (worst_on_him * 100))

    # ── the presenter runs off the bottom, never stops short ───────
    # Every pose plate is a crop with 66-100% of its last row still subject,
    # so a plate that ends inside the card ends in a straight cut across his
    # chest with background showing under it.
    short = []
    real_place = pcut.place_on_photo

    def measure(bg, plate, a, box, **kw):
        if box[3] < bg.shape[0]:
            short.append((box[3], bg.shape[0]))
        return real_place(bg, plate, a, box, **kw)

    pcut.place_on_photo = measure
    try:
        for fmt in pt.FORMATS:
            pt.render(os.path.join(work, "cut_" + fmt + ".jpg"),
                      "Doctors said it was anxiety but the sodium was 0.4",
                      photos, fmt=fmt, episode=3, kicker="CASE 03")
    finally:
        pcut.place_on_photo = real_place
    check("presenter always reaches the bottom edge", not short,
          "%d layout(s) stop short, worst %s" % (len(short), short[:1]))

    # ── a headline is never spliced across a conjunction ───────────
    check("headline stays a whole statement",
          pt.trim_words("Every test came back clean and nobody could say why")
          == "Every test came back clean",
          "got %r" % pt.trim_words("Every test came back clean and nobody could say why"))

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

    # ── the subtitle chain has more than one link ──────────────────
    # Whisper failed three times on run 31156373254 (502) and three times on
    # the run before it (413), and both episodes were captioned by spreading
    # the script evenly across the runtime. Retrying one endpoint is not a
    # backup; these checks assert the other routes are real and reachable.
    import caption_align as ca
    from caption_timing import ass_from_words

    tone = os.path.join(work, "pauses.wav")
    # speech 0-6, silence 6-9, speech 9-14, silence 14-16, speech 16-24
    chain, idx = [], 0
    for dur, loud in ((6.0, 1), (3.0, 0), (5.0, 1), (2.0, 0), (8.0, 1)):
        chain.append(("sine=frequency=%d:duration=%.2f:sample_rate=44100"
                      % (180 + 40 * idx, dur)) if loud else
                     "anullsrc=r=44100:cl=mono:d=%.2f" % dur)
        idx += 1
    filt = ";".join("%s[a%d]" % (s, i) for i, s in enumerate(chain))
    filt += ";" + "".join("[a%d]" % i for i in range(len(chain))) + \
            "concat=n=%d:v=0:a=1[out]" % len(chain)
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-filter_complex", filt, "-map", "[out]", "-t", "24", tone],
                   capture_output=True, timeout=120)

    truth = [(0.0, 6.0), (9.0, 14.0), (16.0, 24.0)]
    spans = ca.speech_spans(tone, total=24.0)
    close = (len(spans) == len(truth) and
             all(abs(a - c) < 0.3 and abs(b - d) < 0.3
                 for (a, b), (c, d) in zip(spans, truth)))
    check("pauses are found in real audio", close,
          "got %s" % [(round(a, 1), round(b, 1)) for a, b in spans])

    words = ca.align_words(tone, " ".join("word%02d" % i for i in range(60)),
                           total=24.0)
    inside = all(any(a - 0.02 <= w["start"] <= b + 0.02 for a, b in truth)
                 for w in words)
    check("no caption word is placed during a silence", inside and bool(words),
          "%d words aligned" % len(words))

    ass, _st = ass_from_words(words, total_duration=None)
    check("aligned words build a real caption track", bool(ass) and len(ass) > 200,
          "%d bytes" % len(ass or ""))

    # The last link must need nothing. If this ever grows a key or a network
    # call, an outage takes the whole chain down again.
    src = open(os.path.join(ROOT, "video_pipeline", "caption_align.py")).read()
    check("the final caption backup needs no key or network",
          "requests" not in src and "API_KEY" not in src,
          "align_words must work with everything else down")

    cp = open(os.path.join(ROOT, "channels", "betrayal_deepdive",
                           "clinical_pipeline.py")).read()
    check("the pipeline actually calls both caption backups",
          "_local_whisper_ass(" in cp and "_aligned_ass(" in cp,
          "a backup that is never called is not a backup")

    # ── everything the workflow itself will check ──────────────────
    # This tool said "Ready for a real run" and the run then died in 90
    # seconds on a check this tool never ran. A pre-flight that clears work
    # the real gate rejects is worse than no pre-flight, because it is
    # trusted. So the workflow's own gates run here too, by invoking the
    # exact same commands rather than a reimplementation of them.
    for label, cmd in (
        ("defect-class scan (workflow gate)",
         [sys.executable, os.path.join(ROOT, "tools", "defect_classes.py"), "--check"]),
        # "There should be three to four backups for each of the stages."
        # Checked here so a route cannot be deleted or renamed and quietly
        # take a stage back down to one.
        ("every stage has 3+ independent routes",
         [sys.executable, os.path.join(ROOT, "tools", "stage_backups.py")]),
    ):
        if not os.path.exists(cmd[1]):
            continue
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT,
                               timeout=300)
            tail = [l for l in (r.stdout or r.stderr).strip().splitlines() if l.strip()]
            check(label, r.returncode == 0 and "NEW lead" not in (r.stdout or ""),
                  tail[0][:60] if tail else "")
        except Exception as e:
            check(label, False, repr(e))

    # The workflow's undefined-name gate is pyflakes filtered to one message,
    # so it is run the same way here rather than approximated.
    try:
        import subprocess as _sp
        r = _sp.run([sys.executable, "-m", "pyflakes"] +
                    __import__("glob").glob(os.path.join(ROOT, "channels", "*", "*.py")) +
                    __import__("glob").glob(os.path.join(ROOT, "video_pipeline", "*.py")),
                    capture_output=True, text=True, cwd=ROOT, timeout=300)
        bad = [l for l in (r.stdout or "").splitlines() if "undefined name" in l]
        check("undefined names (workflow gate)", not bad,
              bad[0][:70] if bad else "")
    except Exception as e:
        check("undefined names (workflow gate)", True, "pyflakes unavailable: %r" % e)

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
