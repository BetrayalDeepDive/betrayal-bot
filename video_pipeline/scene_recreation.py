"""
RECREATION register (direct user spec, this session: "Minimal Scene
Re-creation" as one of the full set of visual types Ch1 should use, not
just the stickman): a real, niche-matched environment -- no character --
looked at rather than walked through, the way a real documentary cuts to
an establishing/reenactment location shot (an empty street, a lit
window, a treeline) while the narration continues. Reuses
stickman_animation.py's proven, real background-scene builder (the exact
same one already used behind the character registers) rendered at a
larger size, then a slow Ken Burns pan/zoom crops across it -- genuine,
continuous motion for the whole segment, never a static frame held in
place.
"""
import random
from pathlib import Path
import subprocess

from stickman_animation import _draw_scene_background

W, H = 1280, 720
FPS = 24


def generate_recreation_segment(niche_name, segment_text, text_overlay, duration, seg_index,
                                 output_path, width=W, height=H, fps=FPS, log_fn=print):
    """
    Renders ONE minimal-scene-recreation clip: a real procedural
    environment (matched to the niche's visual language, varied per
    segment via the seed) with a slow cinematic Ken Burns zoom/pan.
    Returns True/False, never raises.
    """
    rnd = random.Random(seg_index * 53 + 7)
    n_frames = max(1, int(round(duration * fps)))
    tmp_dir = Path(output_path).parent / f"recreate_{seg_index}"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    # Oversized canvas so the Ken Burns pan/zoom has real room to move,
    # same technique investigation_board.py already uses for its board pans.
    OW, OH = int(width * 1.35), int(height * 1.35)

    try:
        base = _draw_scene_background(niche_name, seed=seg_index * 97 + 3, width=OW, height=OH)

        zoom_start, zoom_end = (1.0, 1.15) if rnd.random() < 0.5 else (1.15, 1.0)
        pan_dx = rnd.choice([-1, 1]) * (OW - width) * 0.5
        pan_dy = rnd.uniform(-0.15, 0.15) * (OH - height)

        for f in range(n_frames):
            t = f / max(1, n_frames - 1)
            zoom = zoom_start + (zoom_end - zoom_start) * t
            crop_w, crop_h = int(width / zoom), int(height / zoom)
            cx0 = (OW - crop_w) / 2 + pan_dx * t
            cy0 = (OH - crop_h) / 2 + pan_dy * t
            cx0 = max(0, min(OW - crop_w, cx0))
            cy0 = max(0, min(OH - crop_h, cy0))
            frame = base.crop((int(cx0), int(cy0), int(cx0) + crop_w, int(cy0) + crop_h))
            frame = frame.resize((width, height))
            frame.save(tmp_dir / f"f_{f:04d}.png")

        result = subprocess.run(
            ["ffmpeg", "-y", "-framerate", str(fps), "-i", str(tmp_dir / "f_%04d.png"),
             "-c:v", "libx264", "-preset", "fast", "-crf", "22",
             "-pix_fmt", "yuv420p", "-t", f"{duration:.2f}", str(output_path)],
            capture_output=True, timeout=120)
        ok = result.returncode == 0 and Path(output_path).exists() and Path(output_path).stat().st_size > 2000
        if not ok:
            log_fn(f"    Recreation segment {seg_index}: ffmpeg failed — "
                   f"{result.stderr.decode(errors='ignore')[-300:]}")
        return ok
    except Exception as e:
        log_fn(f"    Recreation segment {seg_index}: {e}")
        return False
    finally:
        try:
            for p in tmp_dir.glob("f_*.png"):
                p.unlink()
            tmp_dir.rmdir()
        except Exception:
            pass
