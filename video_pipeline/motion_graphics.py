"""
MOTION register (10% of Ch1's mix, per direct spec): "end with motion
graphics summarizing the timeline." An animated horizontal timeline bar
with event markers and a progress head that sweeps across as the
segment plays, current event label following it -- a genuinely
different visual language from the character/board registers (flat
infographic, not a rig or a scene), matching how real explainer/
documentary recaps look.
"""
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import subprocess

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
    "dark_horror":        (10, 10, 16),
    "seduction_dark":     (16, 8, 10),
    "psychological_trap": (8, 14, 11),
    "supernatural_real":  (9, 10, 17),
    "obsession_dark":     (15, 12, 8),
}


def _font(size, bold=True):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    for fp in (f"/usr/share/fonts/truetype/dejavu/{name}",
               f"/usr/share/fonts/truetype/liberation/Liberation{'Sans-Bold' if bold else 'Sans'}.ttf"):
        if Path(fp).exists():
            return ImageFont.truetype(fp, size)
    return None


def generate_motion_segment(niche_name, segment_text, text_overlay, duration, seg_index,
                             output_path, width=W, height=H, fps=FPS, log_fn=print,
                             n_markers=5):
    """
    Renders ONE animated-timeline clip: a horizontal bar with n_markers
    tick points, a progress head that sweeps left->right over the full
    duration, and this segment's own text as the currently-highlighted
    event label. Returns True/False, never raises.
    """
    accent = NICHE_ACCENT.get(niche_name, NICHE_ACCENT["dark_horror"])
    bg = NICHE_BG.get(niche_name, NICHE_BG["dark_horror"])
    n_frames = max(1, int(round(duration * fps)))
    tmp_dir = Path(output_path).parent / f"motion_{seg_index}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    font_small = _font(20, bold=False)

    # FIX (direct user report, this session — "two things happening... hard
    # to read"): this used to burn the segment's own narration text (label)
    # directly under the timeline, duplicating the real word-synced
    # subtitles rendered elsewhere in the pipeline. Removed -- the real
    # subtitles are the only text that should appear on screen. The
    # "TIMELINE" tag stays (a fixed UI label, not narration).
    active_idx = seg_index % n_markers
    line_y = int(height * 0.52)
    x0, x1 = int(width * 0.1), int(width * 0.9)

    try:
        for f in range(n_frames):
            t = f / max(1, n_frames - 1)
            # Subtle vertical gradient instead of a flat void -- real
            # motion-graphics/infographic pieces read as a clean designed
            # panel, not a scene, so a gradient (not an illustrated
            # background) is the genre-appropriate real background here.
            img = Image.new("RGB", (width, height), bg)
            draw = ImageDraw.Draw(img)
            for y in range(0, height, 4):
                shade = tuple(min(255, int(c + (accent[i] - c) * 0.05 * (y / height))) for i, c in enumerate(bg))
                draw.line([(0, y), (width, y)], fill=shade)

            # base timeline
            draw.line([(x0, line_y), (x1, line_y)], fill=(90, 90, 100), width=4)
            for i in range(n_markers):
                mx = x0 + (x1 - x0) * i / (n_markers - 1)
                is_active = (i == active_idx)
                r = 14 if is_active else 8
                color = accent if is_active else (140, 140, 150)
                draw.ellipse([mx - r, line_y - r, mx + r, line_y + r], fill=color, outline=(0, 0, 0))

            # sweeping progress head
            head_x = x0 + (x1 - x0) * t
            draw.line([(x0, line_y), (head_x, line_y)], fill=accent, width=6)
            draw.polygon([(head_x, line_y - 16), (head_x - 10, line_y - 32), (head_x + 10, line_y - 32)],
                         fill=accent)

            if font_small:
                tag = "TIMELINE"
                bbox = draw.textbbox((0, 0), tag, font=font_small)
                tw = bbox[2] - bbox[0]
                draw.text(((width - tw) / 2, line_y - 90), tag, fill=accent, font=font_small)

            img.save(tmp_dir / f"f_{f:04d}.png")

        result = subprocess.run(
            ["ffmpeg", "-y", "-framerate", str(fps), "-i", str(tmp_dir / "f_%04d.png"),
             "-c:v", "libx264", "-preset", "fast", "-crf", "22",
             "-pix_fmt", "yuv420p", "-t", f"{duration:.2f}", str(output_path)],
            capture_output=True, timeout=120)
        ok = result.returncode == 0 and Path(output_path).exists() and Path(output_path).stat().st_size > 2000
        if not ok:
            log_fn(f"    Motion segment {seg_index}: ffmpeg failed — "
                   f"{result.stderr.decode(errors='ignore')[-300:]}")
        return ok
    except Exception as e:
        log_fn(f"    Motion segment {seg_index}: {e}")
        return False
    finally:
        try:
            for p in tmp_dir.glob("f_*.png"):
                p.unlink()
            tmp_dir.rmdir()
        except Exception:
            pass
