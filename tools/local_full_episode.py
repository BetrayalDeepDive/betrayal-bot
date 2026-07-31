#!/usr/bin/env python3
"""
Build a COMPLETE episode locally: title card, act cards, every segment,
per-register motion, concatenation, and burned captions. Then look at it.

WHY THIS AND NOT local_episode_render.py
----------------------------------------
That harness renders the stills. This one produces the finished mp4 the way
compose_video does, which is the only artefact a viewer ever sees. Every
piece had been verified in isolation; the assembled whole never had, and
"verified as parts" is exactly the state the pipeline was in when it shipped
an episode illustrated with a mountain and a woman dancing.

What is real here: the register schedule, the title and act cards, every
renderer, the per-register zoompan, the concat, and the same `ass=` filter
compose_video uses to burn captions.

What is substituted (and reported): the narration AUDIO. Real TTS is
unreachable from this sandbox -- the gateway returns 403 on the Microsoft
speech endpoint -- so a silent track of the correct duration stands in. That
makes the VIDEO end-to-end real and leaves the voice itself unproven, which
is stated rather than hidden.

Usage: python3 tools/local_full_episode.py [outdir]
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "video_pipeline"))
sys.path.insert(0, str(ROOT / "tools"))

import caption_timing as ct                    # noqa: E402
import medical_segments as ms                  # noqa: E402
from clinical_quality import WPM               # noqa: E402
from medical_register import new_quota         # noqa: E402
from local_caption_render import synth_word_timings   # noqa: E402
from local_episode_render import (CASE, NARRATION,    # noqa: E402
                                  make_placeholder_figure)

NICHE = "NO KNOWN CAUSE"


def run(cmd, timeout=600):
    return subprocess.run(cmd, capture_output=True, timeout=timeout)


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/full_episode")
    work = out / "work"
    work.mkdir(parents=True, exist_ok=True)

    # Stand-in figures, exactly as the prefetch would have left them.
    case = dict(CASE)
    figs = []
    for i, kind in enumerate(("portrait", "square", "wide")):
        p = work / f"pmcfig_{i}.jpg"
        make_placeholder_figure(p, kind, seed=i)
        f = dict(CASE["figures"][i]); f["local_path"] = str(p)
        figs.append(f)
    case["figures"] = figs

    import real_case_images
    real_case_images.search_wikimedia_commons = lambda *a, **k: (False, "")

    words, total = synth_word_timings(NARRATION, WPM)
    audio_duration = total
    n_buckets = max(55, min(65, int(round(audio_duration / 15.0))))
    cards = ms.act_boundaries(n_buckets)
    n_register_segments = n_buckets - (1 + len(cards))
    quota = new_quota(n_register_segments, figure_count=len(figs), case=case)

    seg_dur = audio_duration / n_buckets
    bucket_words = max(1, len(NARRATION.split()) // n_buckets)
    src_words = NARRATION.split()

    print(f"{len(src_words)} words | {audio_duration:.0f}s | {n_buckets} segments "
          f"| title card + {len(cards)} act cards")

    clips, plan = [], []
    for i in range(n_buckets):
        clip = work / f"seg_{i:03d}.mp4"
        display = " ".join(src_words[i * bucket_words:(i + 1) * bucket_words])

        if i == 0 or i in cards:
            still = work / f"card_{i}.png"
            if i == 0:
                ok = ms.render_title_card(
                    case["title"], str(still), niche_label=NICHE,
                    source_line=f"{case['journal']} {case['year']}",
                    citation=case["citation"])
                label = "TITLE"
            else:
                ok = ms.render_act_card(sorted(cards).index(i) + 1, cards[i],
                                        str(still), niche_label=NICHE)
                label = f"ACT {sorted(cards).index(i) + 1}"
            if ok and ms.still_to_clip(str(still), seg_dur, str(clip),
                                       register="TITLE"):
                clips.append(clip); plan.append((i, label))
                continue

        reg = quota.pick(display.lower())
        occ, exp = quota.reveal(reg)
        ok = ms.render_medical_segment(
            reg, case, display, seg_dur, i, str(clip), work_dir=str(work),
            niche_label=NICHE, log_fn=lambda m: None,
            progress=occ / max(1, exp), variant=occ - 1, variant_total=exp)
        if ok:
            clips.append(clip); plan.append((i, reg))
        else:
            print(f"  segment {i} FAILED to render")

    print(f"  {len(clips)}/{n_buckets} clips rendered")

    # Concatenate exactly as the pipeline does.
    lst = work / "concat.txt"
    lst.write_text("".join(f"file '{c.resolve()}'\n" for c in clips))
    silent = work / "silent.m4a"
    run(["ffmpeg", "-y", "-f", "lavfi", "-i",
         f"anullsrc=r=44100:cl=stereo", "-t", f"{audio_duration:.2f}",
         "-c:a", "aac", str(silent)])

    ass = work / "captions.ass"
    cues, stats = ct.build_cues(words, total_duration=audio_duration)
    ass.write_text(ct.build_ass(cues), encoding="utf-8")
    print(f"  captions: {stats['cues']} cues, mean dwell {stats['mean_dwell']}s, "
          f"max {stats['max_cps']} CPS, {stats['overlaps']} overlaps")

    final = out / "episode.mp4"
    esc = str(ass).replace("\\", "\\\\\\\\").replace(":", "\\:").replace("'", "\\'")
    r = run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
             "-i", str(silent), "-map", "0:v", "-map", "1:a",
             "-t", f"{audio_duration:.2f}",
             "-vf", f"scale=1920:1080,ass='{esc}'",
             "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26",
             "-c:a", "aac", "-pix_fmt", "yuv420p", str(final)], timeout=1800)
    if not final.exists():
        print("FINAL ASSEMBLY FAILED:", r.stderr.decode()[-800:])
        return 1
    print(f"  episode: {final} ({final.stat().st_size // 1024 // 1024} MB)")

    _verify(final, audio_duration, clips, plan, out)
    return 0


def _verify(final, audio_duration, clips, plan, out):
    """Measure the finished file, then pull frames from it to look at."""
    def probe(path, entries, stream="v:0"):
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", stream,
                            "-show_entries", entries, "-of", "csv=p=0",
                            str(path)], capture_output=True, text=True)
        return r.stdout.strip()

    dur = float(probe(final, "format=duration", stream="v:0").split(",")[0]
                if "," in probe(final, "format=duration", stream="v:0")
                else subprocess.run(
                    ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                     "-of", "csv=p=0", str(final)],
                    capture_output=True, text=True).stdout.strip())
    wh = probe(final, "stream=width,height")
    print(f"  probe: {wh}, {dur:.1f}s (audio {audio_duration:.1f}s, "
          f"drift {abs(dur - audio_duration):.2f}s)")

    # PER-REGISTER MOTION, measured rather than assumed: compare the first
    # and last frame of a real clip of each register and confirm the zoom
    # actually moved, and moved by different amounts for different registers.
    print("  motion (measured on real clips):")
    seen = {}
    for (idx, reg) in plan:
        if reg in seen or reg == "TITLE":
            continue
        c = [c for c in clips if f"seg_{idx:03d}" in c.name]
        if not c:
            continue
        a, b = out / f"m_{reg}_a.png", out / f"m_{reg}_b.png"
        subprocess.run(["ffmpeg", "-y", "-i", str(c[0]), "-vf",
                        "select=eq(n\\,2)", "-frames:v", "1", str(a)],
                       capture_output=True)
        subprocess.run(["ffmpeg", "-y", "-sseof", "-0.3", "-i", str(c[0]),
                        "-frames:v", "1", str(b)], capture_output=True)
        if a.exists() and b.exists():
            seen[reg] = _zoom_delta(a, b)
            print(f"    {reg:9} scale change {seen[reg]:.4f}")
    if len(seen) >= 3 and max(seen.values()) - min(seen.values()) < 0.002:
        print("    WARNING: every register moves by the same amount")

    # Frames from the FINISHED file, including a card and a caption.
    stamps = [1.0, audio_duration * 0.25, audio_duration * 0.5,
              audio_duration * 0.62, audio_duration * 0.78, audio_duration - 6]
    shots = []
    for k, t in enumerate(stamps):
        f = out / f"final_{k}_{int(t)}s.png"
        subprocess.run(["ffmpeg", "-y", "-ss", f"{t:.2f}", "-i", str(final),
                        "-frames:v", "1", str(f)], capture_output=True)
        if f.exists():
            shots.append((f, t))
    _sheet(shots, out)


def _zoom_delta(a, b):
    """
    Crude but real: how much did the frame content scale between two frames?
    Compares the mean absolute difference against a re-scaled version.
    """
    from PIL import Image, ImageChops
    ia = Image.open(a).convert("L").resize((320, 180))
    ib = Image.open(b).convert("L").resize((320, 180))
    best, best_s = None, 0.0
    for s in [1.0 + i * 0.01 for i in range(0, 20)]:
        w, h = int(320 * s), int(180 * s)
        z = ia.resize((w, h)).crop(((w - 320) // 2, (h - 180) // 2,
                                    (w - 320) // 2 + 320, (h - 180) // 2 + 180))
        diff = sum(ImageChops.difference(z, ib).getdata())
        if best is None or diff < best:
            best, best_s = diff, s
    return best_s - 1.0


def _sheet(shots, out):
    from PIL import Image, ImageDraw
    import medical_figure_render as mfr
    if not shots:
        return
    cols, tw, th = 2, 960, 540
    rows = (len(shots) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * th), (8, 10, 12))
    d = ImageDraw.Draw(sheet)
    for k, (p, t) in enumerate(shots):
        x, y = (k % cols) * tw, (k // cols) * th
        sheet.paste(Image.open(p).resize((tw, th)), (x, y))
        d.text((x + 10, y + 8), f"t={t:.0f}s", font=mfr._font(24),
               fill=(255, 210, 90))
        d.rectangle([x, y, x + tw - 1, y + th - 1], outline=(60, 60, 60))
    p = out / "final_frames.png"
    sheet.save(p)
    print("  sheet ->", p)


if __name__ == "__main__":
    sys.exit(main())
