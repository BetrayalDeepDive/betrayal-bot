#!/usr/bin/env python3
"""
Assemble a COMPLETE Short and look at it.

The vertical clinical cards were verified as images. A Short is not images:
it is those cards plus burned subtitles plus a hook overlay plus a watermark
plus a vignette, all composited by assemble_short_video -- and "verified as
parts" is exactly the state the main video was in when it shipped with a
mountain in it.

This runs the real download_background_clip (which for this channel routes
to the clinical vertical renderer and must never touch a stock library) and
the real assemble_short_video, then pulls frames out of the finished file.

The narration AUDIO is substituted with a silent track of the right length,
because real TTS is unreachable from this sandbox. Everything composited on
top of it is real.

Usage: python3 tools/local_short_render.py [outdir]
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "video_pipeline"))
sys.path.insert(0, str(ROOT / "tools"))

import shorts_reels_engine as sre               # noqa: E402
from local_episode_render import CASE           # noqa: E402

HOOK = "A newborn was being poisoned by milk."
LINES = [
    ("On the second day of her life, a baby girl stopped feeding.", 0.0, 4.2),
    ("Nothing about that is rare.", 4.4, 6.6),
    ("Ninety-six hours later her blood told a different story.", 6.8, 11.4),
    ("The first diagnosis was sepsis. It almost always is.", 11.6, 15.8),
    ("The cultures came back sterile.", 16.0, 18.8),
    ("It was the absence of infection that redirected everything.", 19.0, 24.0),
]


def srt_time(t):
    h = int(t) // 3600
    m = (int(t) % 3600) // 60
    s = int(t) % 60
    ms = int((t - int(t)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/short_render")
    out.mkdir(parents=True, exist_ok=True)
    duration = LINES[-1][2] + 1.5

    audio = out / "narration.m4a"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i",
                    "anullsrc=r=44100:cl=stereo", "-t", f"{duration:.2f}",
                    "-c:a", "aac", str(audio)], capture_output=True)

    srt = out / "subs.srt"
    srt.write_text("".join(
        f"{i+1}\n{srt_time(a)} --> {srt_time(b)}\n{txt}\n\n"
        for i, (txt, a, b) in enumerate(LINES)), encoding="utf-8")

    # The REAL entry point. For this channel it must render from the case
    # and must NOT reach Pixabay.
    sre.set_clinical_case(CASE)
    bg = out / "bg.mp4"
    ok = sre.download_background_clip("hospital medical", str(bg),
                                      topic=CASE["title"], duration=duration)
    print(f"background: {'ok' if ok else 'FAILED'}  {bg.stat().st_size // 1024 if bg.exists() else 0} KB")
    if bg.exists():
        wh = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                             "-show_entries", "stream=width,height", "-of",
                             "csv=p=0", str(bg)], capture_output=True, text=True)
        print(f"  dimensions: {wh.stdout.strip()}")

    final = out / "short.mp4"
    ok = sre.assemble_short_video(str(bg), str(audio), str(srt), HOOK, str(final))
    if not ok or not final.exists():
        print("assemble_short_video FAILED")
        return 1
    print(f"short: {final} ({final.stat().st_size // 1024} KB)")

    shots = []
    for t in (1.0, 5.5, 12.0, 17.5, 22.0):
        f = out / f"s_{int(t*10)}.png"
        subprocess.run(["ffmpeg", "-y", "-ss", f"{t:.2f}", "-i", str(final),
                        "-frames:v", "1", str(f)], capture_output=True)
        if f.exists():
            shots.append((f, t))
    _sheet(shots, out)
    return 0


def _sheet(shots, out):
    from PIL import Image, ImageDraw
    import medical_figure_render as mfr
    if not shots:
        print("no frames extracted")
        return
    tw, th = 360, 640
    sheet = Image.new("RGB", (tw * len(shots), th), (8, 10, 12))
    d = ImageDraw.Draw(sheet)
    for k, (p, t) in enumerate(shots):
        sheet.paste(Image.open(p).resize((tw, th)), (k * tw, 0))
        d.text((k * tw + 8, 6), f"t={t:.1f}s", font=mfr._font(22),
               fill=(255, 210, 90))
        d.rectangle([k * tw, 0, k * tw + tw - 1, th - 1], outline=(70, 70, 70))
    p = out / "short_frames.png"
    sheet.save(p)
    print("sheet ->", p)


if __name__ == "__main__":
    sys.exit(main())
