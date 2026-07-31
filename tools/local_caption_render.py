#!/usr/bin/env python3
"""
Burn real captions onto real frames and look at them.

Same principle as tools/local_episode_render.py: the caption logic had been
changed twice on the strength of reading it, and never once observed. This
generates realistic word-level timings, runs the real grouping/timing code,
renders the ASS with ffmpeg onto the real segment stills, and writes frames
to inspect.

Whisper itself cannot run here (no network), so the word timings are
SYNTHESISED -- but from a real speech model, not evenly: per-word duration
scales with syllable count, punctuation adds real pauses, and the overall
rate is pinned to the pipeline's own WPM constant. That is enough to exercise
every branch of the grouping code, which is where the defects were.

Usage: python3 tools/local_caption_render.py [outdir]
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "video_pipeline"))
sys.path.insert(0, str(ROOT / "tools"))

import caption_timing as ct                      # noqa: E402
from clinical_quality import WPM                 # noqa: E402
from local_episode_render import NARRATION       # noqa: E402


def syllables(word):
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 1
    groups = re.findall(r"[aeiouy]+", w)
    n = len(groups)
    if w.endswith("e") and n > 1:
        n -= 1
    return max(1, n)


def synth_word_timings(text, wpm=WPM):
    """
    Whisper-shaped output: [{'word','start','end'}, ...].

    Duration is proportional to syllable count rather than uniform, and
    punctuation inserts real pauses -- the two properties that decide
    whether the grouping code behaves, and the two a uniform-timing fake
    would hide.
    """
    words = text.split()
    total_syl = sum(syllables(w) for w in words)
    # Target: the whole narration takes len(words)/wpm minutes.
    speech_seconds = len(words) / wpm * 60.0
    per_syl = speech_seconds / max(1, total_syl)

    out, t = [], 0.6
    for w in words:
        dur = per_syl * syllables(w)
        out.append({"word": w, "start": round(t, 3), "end": round(t + dur, 3)})
        t += dur
        if re.search(r"[.!?]$", w):
            t += 0.55            # sentence pause
        elif re.search(r"[,;:]$", w):
            t += 0.22            # clause pause
        else:
            t += 0.03            # inter-word
    return out, t


# ── the previous implementation, for a like-for-like comparison ────────
def legacy_cues(words_data):
    MIN_DWELL, LEAD_OUT, MAX_CHARS, MAX_WORDS = 1.5, 0.35, 46, 9
    groups, cur, cur_chars = [], [], 0
    for w in words_data:
        tok = w["word"].strip()
        if cur and (cur_chars + 1 + len(tok) > MAX_CHARS or len(cur) >= MAX_WORDS):
            groups.append(cur); cur, cur_chars = [], 0
        cur.append(w); cur_chars += (1 if cur_chars else 0) + len(tok)
    if cur:
        groups.append(cur)
    cues = []
    for gi, group in enumerate(groups):
        start = group[0]["start"]
        end = group[-1]["end"] + LEAD_OUT
        nxt = groups[gi + 1][0]["start"] if gi + 1 < len(groups) else None
        if end - start < MIN_DWELL:
            end = start + MIN_DWELL
        if nxt is not None:
            end = min(end, nxt)
        if end <= start:
            continue
        text = " ".join(w["word"].strip() for w in group)
        cues.append({"start": start, "end": end, "text": text,
                     "cps": len(text) / max(0.01, end - start)})
    return cues


def summarise(name, cues):
    if not cues:
        return f"{name}: no cues"
    dwell = [c["end"] - c["start"] for c in cues]
    cps = [c["cps"] for c in cues]
    over = sum(1 for c in cps if c > ct.MAX_CPS + 0.5)
    flash = sum(1 for d in dwell if d < 1.0)
    return (f"{name}: {len(cues)} cues | mean dwell {sum(dwell)/len(dwell):.2f}s | "
            f"min {min(dwell):.2f}s | max CPS {max(cps):.1f} | "
            f"unreadable (>{ct.MAX_CPS:.0f} CPS) {over} ({over*100//len(cues)}%) | "
            f"flashing (<1.0s) {flash}")


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/caption_render")
    out.mkdir(parents=True, exist_ok=True)

    words, total = synth_word_timings(NARRATION)
    print(f"{len(words)} words, {total:.0f}s at {WPM} wpm "
          f"({len(words)/(total/60):.0f} wpm effective with pauses)\n")

    old = legacy_cues(words)
    new, stats = ct.build_cues(words, total_duration=total)
    print(summarise("BEFORE", old))
    print(summarise("AFTER ", new))
    print(f"        overlaps={stats['overlaps']}  under_dwell={stats['under_dwell']}\n")

    ass_path = out / "captions.ass"
    ass_path.write_text(ct.build_ass(new), encoding="utf-8")

    # Burn onto the real rendered stills, at the real moments those stills
    # would be on screen, and pull frames out to look at.
    stills = sorted((ROOT.parent / "x").glob("*")) if False else None
    frames_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    src = frames_dir or _find_stills()
    if not src:
        print("no rendered stills found -- run tools/local_episode_render.py first")
        return
    _burn(src, ass_path, new, total, out)


def _find_stills():
    for base in (Path("/tmp/claude-0").glob("**/ep*/work"),):
        for p in base:
            pngs = sorted(p.glob("med_*.png"))
            if len(pngs) > 20:
                return p
    return None


def _burn(stills_dir, ass_path, cues, total, out):
    """
    Build a short clip per sampled moment: the still that would be on screen,
    with the real caption burned in by libass, then extract a frame.
    """
    pngs = sorted(stills_dir.glob("med_*.png"),
                  key=lambda p: int(p.name.split("_")[1]))
    n_seg = len(pngs)
    seg_dur = total / max(1, n_seg)

    # Sample moments spread across the episode, plus the two worst cues.
    picks = [int(len(cues) * f) for f in (0.02, 0.18, 0.34, 0.5, 0.66, 0.82, 0.96)]
    worst = sorted(range(len(cues)), key=lambda i: -cues[i]["cps"])[:2]
    picks = sorted(set([min(p, len(cues) - 1) for p in picks] + worst))

    made = []
    for k, ci in enumerate(picks):
        c = cues[ci]
        mid = (c["start"] + c["end"]) / 2.0
        seg = min(n_seg - 1, int(mid / seg_dur))
        png = pngs[seg]
        png_frame = out / f"cap_{k:02d}_seg{seg}_cue{ci}.png"
        # Shift the ASS so this cue starts at t=0, then pull the frame at
        # t=0.5s -- comfortably inside the cue. The first attempt shifted the
        # cue to t=0.05 and extracted frame 0, which is BEFORE the cue starts,
        # so libass correctly drew nothing and the sheet came back with no
        # captions at all. The renderer was fine; the harness was sampling a
        # moment when no caption existed.
        shifted = out / f"_shift_{k}.ass"
        _shift_ass(ass_path, shifted, -c["start"])
        cmd = ["ffmpeg", "-y", "-loop", "1", "-t", "1.5", "-i", str(png),
               "-vf", f"subtitles='{shifted}'", "-ss", "0.5",
               "-frames:v", "1", str(png_frame)]
        r = subprocess.run(cmd, capture_output=True, timeout=90)
        if png_frame.exists():
            made.append((png_frame, ci, c))
        else:
            print("  burn failed:", r.stderr.decode()[-300:])
    _sheet(made, out)


def _shift_ass(src, dst, offset):
    lines = []
    for line in Path(src).read_text(encoding="utf-8").splitlines():
        if line.startswith("Dialogue:"):
            head, rest = line.split(":", 1)
            parts = rest.split(",", 9)
            parts[1] = ct._t(max(0.0, _sec(parts[1]) + offset))
            parts[2] = ct._t(max(0.0, _sec(parts[2]) + offset))
            line = head + ":" + ",".join(parts)
        lines.append(line)
    Path(dst).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _sec(t):
    h, m, s = t.strip().split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def _sheet(made, out):
    from PIL import Image, ImageDraw
    import medical_figure_render as mfr
    if not made:
        return
    cols = 2
    rows = (len(made) + cols - 1) // cols
    tw, th = 960, 540
    sheet = Image.new("RGB", (cols * tw, rows * th), (8, 10, 12))
    d = ImageDraw.Draw(sheet)
    for k, (p, ci, c) in enumerate(made):
        x, y = (k % cols) * tw, (k // cols) * th
        sheet.paste(Image.open(p).resize((tw, th)), (x, y))
        d.text((x + 10, y + 8),
               f"cue {ci}  {c['end']-c['start']:.2f}s  {c['cps']:.1f} CPS",
               font=mfr._font(22), fill=(255, 210, 90))
        d.rectangle([x, y, x + tw - 1, y + th - 1], outline=(60, 60, 60))
    p = out / "caption_sheet.png"
    sheet.save(p)
    print("sheet ->", p)


if __name__ == "__main__":
    main()
