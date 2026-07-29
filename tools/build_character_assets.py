"""
Offline batch build: renders every Ch1 character pose ONCE via Blender
(video_pipeline/character_rig_blender.py), then crops each frame to the
smallest region that safely contains the character across the whole
loop (with padding) and writes a compact PNG-sequence asset + a
manifest.json (recording where that crop sits inside the full 1280x720
frame) under video_pipeline/character_assets/<POSE>/.

Why crop: a full 1280x720 RGBA frame is ~470KB even though the
character occupies a small fraction of it (mostly transparent). Cropped
to the character's own bounding box it's ~30-50KB -- a real, necessary
size reduction for something checked into a git repo across 17 poses x
~60 frames each.

Run once (or whenever the rig script changes), not part of the live
per-episode pipeline -- see character_rig_blender.py's docstring for why.

Usage: python3 tools/build_character_assets.py [POSE ...]
       (no args = build every pose)
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).parent.parent
RIG_SCRIPT = REPO_ROOT / "video_pipeline" / "character_rig_blender.py"
ASSETS_ROOT = REPO_ROOT / "video_pipeline" / "character_assets"

ALL_POSES = [
    "ONE_CHAR", "WALK", "RUN", "SIT_WRITE", "ALERT", "SHOCK", "WAIT",
    "LOOK_AROUND", "CRY_GRIEF", "ANGRY_CONFRONT", "PHONE_CALL",
    "COLLAPSE_KNEEL", "COWER_DEFENSE", "KNOCK_DOOR", "SEARCH_RUMMAGE",
    "HAPPY", "DANCE", "TWO_CHAR",
]

FRAME_W, FRAME_H = 1280, 720
PAD = 20  # px, safety margin around the union bounding box


def build_pose(pose, tmp_root):
    tmp_dir = tmp_root / pose
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    print(f"[{pose}] rendering via Blender...")
    result = subprocess.run(
        ["blender", "--background", "--factory-startup", "--python", str(RIG_SCRIPT),
         "--", pose, str(tmp_dir)],
        capture_output=True, text=True, timeout=180)
    if "SAMPLE_V3_RENDER_OK" not in result.stdout:
        print(f"[{pose}] RENDER FAILED:\n{result.stdout[-2000:]}\n{result.stderr[-2000:]}")
        return False

    frames = sorted(tmp_dir.glob("ch_*.png"))
    if not frames:
        print(f"[{pose}] no frames produced")
        return False

    # union bbox across every frame -- the character moves within the
    # loop (bob/stride/etc), so any single frame's bbox would clip others
    union = None
    imgs = []
    for fp in frames:
        img = Image.open(fp).convert("RGBA")
        imgs.append(img)
        bbox = img.split()[-1].getbbox()
        if bbox is None:
            continue
        union = bbox if union is None else (
            min(union[0], bbox[0]), min(union[1], bbox[1]),
            max(union[2], bbox[2]), max(union[3], bbox[3]))
    if union is None:
        print(f"[{pose}] every frame fully transparent -- skipping")
        return False

    x0 = max(0, union[0] - PAD)
    y0 = max(0, union[1] - PAD)
    x1 = min(FRAME_W, union[2] + PAD)
    y1 = min(FRAME_H, union[3] + PAD)

    out_dir = ASSETS_ROOT / pose
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    for i, img in enumerate(imgs):
        cropped = img.crop((x0, y0, x1, y1))
        cropped.save(out_dir / f"f_{i:04d}.png", optimize=True)

    manifest = {
        "pose": pose, "n_frames": len(imgs),
        "full_w": FRAME_W, "full_h": FRAME_H,
        "crop_x": x0, "crop_y": y0, "crop_w": x1 - x0, "crop_h": y1 - y0,
        "fps": 12,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    shutil.rmtree(tmp_dir)
    size_kb = sum(f.stat().st_size for f in out_dir.glob("*.png")) / 1024
    print(f"[{pose}] OK -- {len(imgs)} frames, crop {x1-x0}x{y1-y0}, {size_kb:.0f}KB total")
    return True


def main():
    poses = sys.argv[1:] or ALL_POSES
    tmp_root = Path("/tmp/character_asset_build")
    tmp_root.mkdir(parents=True, exist_ok=True)
    ASSETS_ROOT.mkdir(parents=True, exist_ok=True)
    ok, failed = [], []
    for pose in poses:
        if pose not in ALL_POSES:
            print(f"Unknown pose: {pose}")
            failed.append(pose)
            continue
        if build_pose(pose, tmp_root):
            ok.append(pose)
        else:
            failed.append(pose)
    shutil.rmtree(tmp_root, ignore_errors=True)
    print(f"\nDone: {len(ok)} OK, {len(failed)} failed")
    if failed:
        print("Failed:", failed)
        sys.exit(1)


if __name__ == "__main__":
    main()
