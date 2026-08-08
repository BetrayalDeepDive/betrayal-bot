"""
TEXT register (5% of Ch1's mix, per direct spec): "use kinetic text for
a key quote." Reserved for segments with a real quoted line (detected
by scene_register.classify_hint finding an actual quotation mark in the
narration) -- word-by-word animated reveal, each word scaling in with a
fade, over a slow-pulsing radial glow background. Deliberately the
simplest of the 4 new registers (5% budget) but still genuinely
animated frame-by-frame, not a static card.
"""
import math
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import subprocess

# Guarded: this module is imported by every channel's pipeline, and several of
# them do not put video_pipeline on sys.path the same way. A missing helper
# must degrade to the previous behaviour, never break an unrelated channel's
# render.
try:
    import screen_text as _screen_text
except Exception:                                   # pragma: no cover
    _screen_text = None

W, H = 1280, 720
FPS = 24

NICHE_ACCENT = {
    "dark_horror":        (210, 30, 30),
    "seduction_dark":     (210, 40, 90),
    "psychological_trap": (60, 190, 130),
    "supernatural_real":  (90, 140, 220),
    "obsession_dark":     (220, 160, 40),
}
NICHE_BG = {
    "dark_horror":        (6, 6, 10),
    "seduction_dark":     (12, 5, 7),
    "psychological_trap": (5, 10, 8),
    "supernatural_real":  (6, 6, 11),
    "obsession_dark":     (11, 9, 5),
}


def _font(size):
    for fp in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
               "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"):
        if Path(fp).exists():
            return ImageFont.truetype(fp, size)
    return None


def _extract_quote(text):
    m = re.search(r'["“]([^"”]{4,80})["”]', text or "")
    return m.group(1) if m else (text or "").strip()


def generate_text_segment(niche_name, segment_text, text_overlay, duration, seg_index,
                           output_path, width=W, height=H, fps=FPS, log_fn=print):
    """
    Renders ONE kinetic-text clip: the segment's quoted line revealed
    word by word (each word scales up + fades in as its turn arrives),
    over a slow-pulsing radial glow. Returns True/False, never raises.
    """
    accent = NICHE_ACCENT.get(niche_name, NICHE_ACCENT["dark_horror"])
    bg = NICHE_BG.get(niche_name, NICHE_BG["dark_horror"])
    # Same fault as the anatomy card: slicing the first twelve words off a
    # segment that began mid-sentence put a fragment on screen, one word at a
    # time, as the whole point of the shot. Prefer a complete thought; fall
    # back to the raw quote rather than to "..." , because a kinetic-TEXT
    # segment with no text is a blank shot.
    quote = _extract_quote(text_overlay or segment_text or "")
    _clean = _screen_text.caption_label(quote, max_words=12) if _screen_text else ""
    words = (_clean or quote).split()[:12] or ["..."]

    n_frames = max(1, int(round(duration * fps)))
    tmp_dir = Path(output_path).parent / f"text_{seg_index}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    font = _font(52)

    reveal_frames = max(1, n_frames // max(1, len(words) + 1))

    try:
        import numpy as np
        cx, cy = width // 2, height // 2
        yy, xx = np.mgrid[0:height, 0:width]
        base_dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)

        for f in range(n_frames):
            pulse = 0.85 + 0.15 * math.sin(f / fps * 1.3)
            radius = height * 0.55 * pulse
            falloff = np.clip(1.0 - base_dist / radius, 0, 1) ** 1.8
            layer = np.zeros((height, width, 3), dtype=np.uint8)
            for i in range(3):
                layer[:, :, i] = (bg[i] + falloff * (accent[i] - bg[i]) * 0.35).astype(np.uint8)
            img = Image.fromarray(layer, "RGB")
            draw = ImageDraw.Draw(img)

            n_visible = min(len(words), f // reveal_frames + 1)
            line = " ".join(words[:n_visible])
            if font and line:
                bbox = draw.textbbox((0, 0), line, font=font)
                tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                # newest word gets a brief scale-in pop
                just_added_frame = (f % reveal_frames)
                scale = 1.0
                if just_added_frame < 4 and n_visible > 0:
                    scale = 0.85 + 0.15 * (just_added_frame / 4)
                x, y = (width - tw * scale) / 2, (height - th * scale) / 2
                draw.text((x, y), line, fill=(245, 245, 245), font=font,
                          stroke_width=3, stroke_fill=(0, 0, 0))
            quote_mark_font = _font(90)
            if quote_mark_font:
                draw.text((width * 0.06, height * 0.15), "“", fill=accent, font=quote_mark_font)

            img.save(tmp_dir / f"f_{f:04d}.png")

        result = subprocess.run(
            ["ffmpeg", "-y", "-framerate", str(fps), "-i", str(tmp_dir / "f_%04d.png"),
             "-c:v", "libx264", "-preset", "fast", "-crf", "22",
             "-pix_fmt", "yuv420p", "-t", f"{duration:.2f}", str(output_path)],
            capture_output=True, timeout=120)
        ok = result.returncode == 0 and Path(output_path).exists() and Path(output_path).stat().st_size > 2000
        if not ok:
            log_fn(f"    Text segment {seg_index}: ffmpeg failed — "
                   f"{result.stderr.decode(errors='ignore')[-300:]}")
        return ok
    except Exception as e:
        log_fn(f"    Text segment {seg_index}: {e}")
        return False
    finally:
        try:
            for p in tmp_dir.glob("f_*.png"):
                p.unlink()
            tmp_dir.rmdir()
        except Exception:
            pass
