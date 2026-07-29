"""
Ch1 STICKMAN/SILHOUETTE register compositor -- runs LIVE in the
per-episode pipeline (unlike character_rig_blender.py, which is
offline-only -- see that file's docstring for why). Loads a pre-
rendered pose asset (video_pipeline/character_assets/<POSE>/, built
once by tools/build_character_assets.py) and composites it over a real
Pixabay/Pexels photo when photo_background.py finds one, or the
procedural 20-scene fallback otherwise -- both paths already proven and
shipping for the RECREATION register. Adds the same Ken Burns pan/zoom
and per-frame film grain already used elsewhere in this pipeline. Pure
Python + ffmpeg, no live Blender invocation.
"""
import json
import random
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

from stickman_animation import _draw_scene_background
from photo_background import fetch_photo_background, photo_to_cover_canvas, grade_photo

ASSETS_ROOT = Path(__file__).parent / "character_assets"
W, H = 1280, 720
FPS = 24

_ASSET_CACHE = {}


def _load_pose_asset(pose):
    if pose in _ASSET_CACHE:
        return _ASSET_CACHE[pose]
    pose_dir = ASSETS_ROOT / pose
    manifest = json.loads((pose_dir / "manifest.json").read_text())
    frames = [Image.open(f).convert("RGBA") for f in sorted(pose_dir.glob("f_*.png"))]
    if not frames:
        raise FileNotFoundError(f"no pre-rendered frames for pose '{pose}' -- run tools/build_character_assets.py")
    _ASSET_CACHE[pose] = (manifest, frames)
    return manifest, frames


def _apply_grain(img, rnd, grain_strength=3.5, flicker_range=0.02):
    """Real per-frame grain + tiny brightness flicker -- regenerated
    fresh every frame (not a static overlay) so it never tiles or
    repeats visibly, the same technique already used for the
    RECREATION/scene-background fallback."""
    arr = np.asarray(img, dtype=np.float32)
    flicker = 1.0 + rnd.uniform(-flicker_range, flicker_range)
    arr *= flicker
    noise = np.random.default_rng(rnd.randint(0, 2**31 - 1)).normal(0, grain_strength, arr.shape[:2])
    arr += noise[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def _silhouette_recolor(img, color=(8, 8, 10)):
    """SILHOUETTE register -- recolors the pre-rendered (colored) pose
    asset to a solid near-black cutout at composite time, keeping the
    original alpha (anti-aliased edges) so the SAME asset serves both
    STICKMAN and SILHOUETTE without a separate Blender render."""
    r, g, b, a = img.split()
    solid = Image.new("RGB", img.size, color)
    sr, sg, sb = solid.split()
    return Image.merge("RGBA", (sr, sg, sb, a))


def generate_character_segment(niche_name, pose, segment_text, text_overlay, duration, seg_index,
                                output_path, width=W, height=H, fps=FPS, silhouette=False,
                                search_terms=None, pixabay_key="", pexels_key="", log_fn=print):
    """
    Renders ONE character-register clip: a pre-rendered pose loop
    composited over a real (or procedural-fallback) panning background,
    real photo tried first via search_terms/pixabay_key/pexels_key (same
    per-segment keyword pipeline already used for stock footage), the
    procedural 20-scene background otherwise. Returns True/False, never
    raises.
    """
    try:
        manifest, char_frames = _load_pose_asset(pose)
    except Exception as e:
        log_fn(f"    Character segment {seg_index} ({pose}): asset load failed ({e})")
        return False

    n_char_frames = len(char_frames)
    n_out_frames = max(1, int(round(duration * fps)))
    rnd = random.Random(seg_index * 61 + 7)

    OW, OH = int(width * 1.3), int(height * 1.3)
    bg = None
    if search_terms and (pixabay_key or pexels_key):
        try:
            photo_cache = Path(output_path).parent / f"photobg_char_{seg_index}.jpg"
            photo_path = fetch_photo_background(
                search_terms, niche_name, str(photo_cache),
                pixabay_key=pixabay_key, pexels_key=pexels_key, log_fn=log_fn)
            if photo_path:
                canvas = photo_to_cover_canvas(photo_path, width, height, oversize=1.3)
                bg = grade_photo(canvas, niche_name, silhouette=silhouette)
        except Exception as e:
            log_fn(f"    Character segment {seg_index} real photo (non-fatal): {e}")
    if bg is None:
        bg = _draw_scene_background(
            niche_name, seed=seg_index * 97 + 3, width=OW, height=OH,
            force_scene="room_window" if silhouette else None)

    zoom_start, zoom_end = (1.0, 1.12) if rnd.random() < 0.5 else (1.12, 1.0)
    pan_dx = rnd.choice([-1, 1]) * (OW - width) * 0.3

    tmp_dir = Path(output_path).parent / f"charloop_{seg_index}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    paste_xy = (manifest["crop_x"], manifest["crop_y"])
    char_native_fps = manifest.get("fps", 12)

    try:
        for f in range(n_out_frames):
            t = f / max(1, n_out_frames - 1)
            zoom = zoom_start + (zoom_end - zoom_start) * t
            crop_w, crop_h = int(width / zoom), int(height / zoom)
            cx0 = (OW - crop_w) / 2 + pan_dx * t
            cy0 = (OH - crop_h) / 2
            cx0 = max(0, min(OW - crop_w, cx0))
            cy0 = max(0, min(OH - crop_h, cy0))
            frame_bg = bg.crop((int(cx0), int(cy0), int(cx0) + crop_w, int(cy0) + crop_h)).resize((width, height))

            # loop the pre-rendered pose seamlessly across however long
            # this segment runs, at the asset's own native frame rate
            char_idx = int((f / fps) * char_native_fps) % n_char_frames
            char_img = char_frames[char_idx]
            if silhouette:
                char_img = _silhouette_recolor(char_img)

            composed = frame_bg.convert("RGBA")
            composed.alpha_composite(char_img, paste_xy)
            final = _apply_grain(composed.convert("RGB"), rnd)
            final.save(tmp_dir / f"f_{f:04d}.png")

        result = subprocess.run(
            ["ffmpeg", "-y", "-framerate", str(fps), "-i", str(tmp_dir / "f_%04d.png"),
             "-c:v", "libx264", "-preset", "fast", "-crf", "20",
             "-pix_fmt", "yuv420p", "-t", f"{duration:.2f}", str(output_path)],
            capture_output=True, timeout=120)
        ok = result.returncode == 0 and Path(output_path).exists() and Path(output_path).stat().st_size > 2000
        if not ok:
            log_fn(f"    Character segment {seg_index}: ffmpeg failed — "
                   f"{result.stderr.decode(errors='ignore')[-300:]}")
        return ok
    except Exception as e:
        log_fn(f"    Character segment {seg_index} ({pose}): {e}")
        return False
    finally:
        try:
            for p in tmp_dir.glob("f_*.png"):
                p.unlink()
            tmp_dir.rmdir()
        except Exception:
            pass
