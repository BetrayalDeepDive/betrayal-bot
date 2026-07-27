"""
Real stick-figure character animation for Ch1 — replaces the abstract
glow/grain visual system (video_pipeline/niche_animation.py), per
direct user feedback (July 25 2026): "I don't want abstract glow or
grain fields with text... I specifically wanted animation that looks
real, not something abstract... find out if we can use stickman
animated videos."

A real jointed humanoid rig (head, neck, shoulders, 2-segment arms and
legs) drawn frame-by-frame with Pillow — verified this session by
actually rendering and visually inspecting individual frames of a full
walk cycle before building the rest of the action library, the same
render-then-look discipline used for the earlier (rejected) system, so
this one doesn't repeat that mistake: it's checked against what a
"real stick figure" should look like, not just what compiles.

Zero new dependencies (Pillow is already a pipeline dependency),
zero GPU requirement, zero external-asset licensing risk (procedurally
drawn, not fetched).

ACTIONS map real segment content to a real, distinct pose-cycle:
  WALK    — the default: forward motion, natural counter-swing gait
  RUN     — faster stride, more forward lean, higher arm pump
  SIT_WRITE — seated, one hand making a small back-and-forth writing motion
  ALERT   — standing still, one arm raised/pointing, idle sway
  SHOCK   — recoiled/thrown-back startle pose with a held tremor

Honest limitation: this is a single, generic humanoid silhouette, not a
cast of distinct characters, and the action set is a fixed library
(matched by keyword detection), not freeform generative motion. That's
a real, deliberate scope choice — a working, good-looking, reliable
library beats an ambitious but unverified "animate anything" attempt.
"""
import math
import re
from pathlib import Path
from PIL import Image, ImageDraw
import subprocess

W, H = 1280, 720
FPS = 24

# ══════════════════════════════════════════════════════════════════
# CONTENT -> ACTION mapping (real keyword detection, same principle as
# content_sfx.py's category detection — not random, not niche-only).
# ══════════════════════════════════════════════════════════════════
_ACTION_KEYWORDS = {
    "RUN":       ["ran", "running", "fled", "flee", "chase", "chasing", "escape",
                  "sprint", "sprinted", "raced", "bolted"],
    "SIT_WRITE": ["wrote", "notebook", "diary", "desk", "writing", "letter",
                  "journal", "typed", "typing", "logged", "recorded", "documented"],
    "ALERT":     ["pointed", "warned", "noticed", "spotted", "watched", "realized",
                  "discovered", "stared", "witnessed", "saw"],
    "SHOCK":     ["found", "dead", "body", "collapsed", "screamed", "shock",
                  "shocked", "gasped", "horrified", "vanished", "disappeared"],
}
_DEFAULT_ACTION = "WALK"


def detect_action(segment_text):
    """Real keyword scan of THIS segment's own narration text (same
    text already used for the old stock-footage search term) -- picks
    the first action category with a real keyword hit, in a fixed
    priority order so results are deterministic, not random."""
    text = (segment_text or "").lower()
    for action in ("SHOCK", "ALERT", "SIT_WRITE", "RUN"):
        if any(kw in text for kw in _ACTION_KEYWORDS[action]):
            return action
    return _DEFAULT_ACTION


# ══════════════════════════════════════════════════════════════════
# NICHE -> figure color/mood (kept from the earlier system's identity
# work, applied to the figure's stroke color and background tint only
# — the figure itself is drawn the same way for every niche).
# ══════════════════════════════════════════════════════════════════
NICHE_FIGURE_COLOR = {
    "dark_horror":        (210, 220, 232),
    "seduction_dark":     (232, 200, 208),
    "psychological_trap": (204, 232, 216),
    "supernatural_real":  (224, 232, 244),
    "obsession_dark":     (232, 220, 176),
}
NICHE_BG_COLOR = {
    "dark_horror":        (7, 9, 14),
    "seduction_dark":     (14, 6, 8),
    "psychological_trap": (6, 12, 9),
    "supernatural_real":  (7, 9, 15),
    "obsession_dark":     (13, 10, 6),
}


def _draw_walk_run(draw, cx, cy, phase, color, scale, running=False):
    s = scale
    speed = 1.4 if running else 1.0
    lean = 8 if running else 0
    hip_y = cy - (26 if running else 14)*s*abs(math.sin(phase*2))
    hip = (cx, hip_y)
    neck = (cx + lean*s, hip_y - 55*s)
    shoulder_w = 14*s
    l_sh = (neck[0] - shoulder_w, neck[1] + 4*s)
    r_sh = (neck[0] + shoulder_w, neck[1] + 4*s)
    head_c = (neck[0] + lean*0.5*s, hip_y - 78*s)
    head_r = 15*s

    leg_swing = 46 if running else 32
    r_thigh_ang = math.radians(90 + leg_swing*math.sin(phase*speed))
    l_thigh_ang = math.radians(90 + leg_swing*math.sin(phase*speed + math.pi))

    def leg_points(hip_pt, thigh_ang, lead_val):
        knee_len = 34*s
        shin_len = 34*s
        knee = (hip_pt[0] + knee_len*math.cos(thigh_ang),
                hip_pt[1] + knee_len*math.sin(thigh_ang))
        bend_deg = 90 + ((40 if running else 25) if lead_val < -0.2 else (-10 if lead_val > 0.2 else 5))
        bend = math.radians(bend_deg)
        foot = (knee[0] + shin_len*math.cos(bend), knee[1] + shin_len*math.sin(bend))
        return knee, foot

    r_knee, r_foot = leg_points(hip, r_thigh_ang, math.sin(phase*speed))
    l_knee, l_foot = leg_points(hip, l_thigh_ang, math.sin(phase*speed + math.pi))

    arm_swing = 55 if running else 30
    arm_base = 95 if running else 115
    r_arm_ang = math.radians(arm_base + arm_swing*math.sin(phase*speed + math.pi))
    l_arm_ang = math.radians(180 - arm_base - arm_swing*math.sin(phase*speed + math.pi)*-1)

    def arm_points(sh_pt, ang, side):
        upper_len = 28*s
        fore_len = 26*s
        elbow = (sh_pt[0] + upper_len*math.cos(ang), sh_pt[1] + upper_len*math.sin(ang))
        fore_ang = ang + (0.4 if side > 0 else -0.4)
        fore = (elbow[0] + fore_len*math.cos(fore_ang), elbow[1] + fore_len*math.sin(fore_ang))
        return elbow, fore

    r_elbow, r_hand = arm_points(r_sh, r_arm_ang, 1)
    l_elbow, l_hand = arm_points(l_sh, math.radians(180) - l_arm_ang, -1)

    lw = max(3, int(5*s))
    draw.line([hip, r_knee], fill=color, width=lw)
    draw.line([r_knee, r_foot], fill=color, width=lw)
    draw.line([hip, l_knee], fill=color, width=lw)
    draw.line([l_knee, l_foot], fill=color, width=lw)
    draw.line([hip, neck], fill=color, width=lw+1)
    draw.line([neck, head_c], fill=color, width=lw)
    draw.line([l_sh, r_sh], fill=color, width=lw)
    draw.line([r_sh, r_elbow], fill=color, width=lw)
    draw.line([r_elbow, r_hand], fill=color, width=lw)
    draw.line([l_sh, l_elbow], fill=color, width=lw)
    draw.line([l_elbow, l_hand], fill=color, width=lw)
    draw.ellipse([head_c[0]-head_r, head_c[1]-head_r, head_c[0]+head_r, head_c[1]+head_r],
                 outline=color, width=lw)


def _draw_sit_write(draw, cx, cy, phase, color, scale):
    s = scale
    hip = (cx, cy)
    neck = (cx, cy - 50*s)
    shoulder_w = 14*s
    l_sh = (neck[0] - shoulder_w, neck[1] + 4*s)
    r_sh = (neck[0] + shoulder_w, neck[1] + 4*s)
    # slight head-down nod, as if looking at the page
    head_c = (cx + 6*s, cy - 70*s)
    head_r = 15*s
    # Legs bent forward (seated) — thigh horizontal, shin vertical down
    knee = (cx + 30*s, cy + 4*s)
    foot = (cx + 30*s, cy + 38*s)
    l_knee = (cx - 30*s, cy + 4*s)
    l_foot = (cx - 30*s, cy + 38*s)
    # Writing arm: small real back-and-forth motion at the wrist/hand,
    # anchored at a desk-height point in front of the figure.
    desk_y = cy + 6*s
    write_x = cx + 44*s + 4*s*math.sin(phase*6)
    r_elbow = (cx + 24*s, cy - 20*s)
    r_hand = (write_x, desk_y)
    l_elbow = (cx - 20*s, cy - 15*s)
    l_hand = (cx - 32*s, desk_y - 2*s)

    lw = max(3, int(5*s))
    draw.line([hip, knee], fill=color, width=lw)
    draw.line([knee, foot], fill=color, width=lw)
    draw.line([hip, l_knee], fill=color, width=lw)
    draw.line([l_knee, l_foot], fill=color, width=lw)
    draw.line([hip, neck], fill=color, width=lw+1)
    draw.line([neck, head_c], fill=color, width=lw)
    draw.line([l_sh, r_sh], fill=color, width=lw)
    draw.line([r_sh, r_elbow], fill=color, width=lw)
    draw.line([r_elbow, r_hand], fill=color, width=lw)
    draw.line([l_sh, l_elbow], fill=color, width=lw)
    draw.line([l_elbow, l_hand], fill=color, width=lw)
    draw.ellipse([head_c[0]-head_r, head_c[1]-head_r, head_c[0]+head_r, head_c[1]+head_r],
                 outline=color, width=lw)
    # A simple desk-edge line so the writing pose reads clearly, not
    # as an arm just randomly bent in space.
    draw.line([(cx + 10*s, desk_y), (cx + 70*s, desk_y)], fill=color, width=max(2, int(3*s)))


def _draw_alert(draw, cx, cy, phase, color, scale):
    s = scale
    sway = 3*s*math.sin(phase*1.2)  # real idle motion, never fully static
    hip = (cx + sway, cy)
    neck = (cx + sway, cy - 55*s)
    shoulder_w = 14*s
    l_sh = (neck[0] - shoulder_w, neck[1] + 4*s)
    r_sh = (neck[0] + shoulder_w, neck[1] + 4*s)
    head_c = (cx + sway*1.5, cy - 78*s)
    head_r = 15*s
    knee = (cx + sway*0.5 + 10*s, cy + 34*s)
    foot = (cx + sway*0.3 + 10*s, cy + 66*s)
    l_knee = (cx + sway*0.5 - 10*s, cy + 34*s)
    l_foot = (cx + sway*0.3 - 10*s, cy + 66*s)
    # One arm raised, pointing at something off-frame — the clearest
    # real "alert/witness" pose.
    r_elbow = (r_sh[0] + 20*s, r_sh[1] - 18*s)
    r_hand = (r_elbow[0] + 30*s, r_elbow[1] - 6*s)
    l_elbow = (l_sh[0] - 10*s, l_sh[1] + 24*s)
    l_hand = (l_elbow[0] - 6*s, l_elbow[1] + 22*s)

    lw = max(3, int(5*s))
    draw.line([hip, knee], fill=color, width=lw)
    draw.line([knee, foot], fill=color, width=lw)
    draw.line([hip, l_knee], fill=color, width=lw)
    draw.line([l_knee, l_foot], fill=color, width=lw)
    draw.line([hip, neck], fill=color, width=lw+1)
    draw.line([neck, head_c], fill=color, width=lw)
    draw.line([l_sh, r_sh], fill=color, width=lw)
    draw.line([r_sh, r_elbow], fill=color, width=lw)
    draw.line([r_elbow, r_hand], fill=color, width=lw)
    draw.line([l_sh, l_elbow], fill=color, width=lw)
    draw.line([l_elbow, l_hand], fill=color, width=lw)
    draw.ellipse([head_c[0]-head_r, head_c[1]-head_r, head_c[0]+head_r, head_c[1]+head_r],
                 outline=color, width=lw)


def _draw_shock(draw, cx, cy, phase, color, scale):
    s = scale
    # Recoiled/thrown-back startle, held with a small real tremor
    # rather than perfectly frozen (a genuinely static frame reads as
    # broken, not dramatic).
    tremor = 2*s*math.sin(phase*10)
    hip = (cx + tremor, cy)
    neck = (cx - 12*s + tremor, cy - 50*s)
    shoulder_w = 14*s
    l_sh = (neck[0] - shoulder_w, neck[1] + 4*s)
    r_sh = (neck[0] + shoulder_w, neck[1] + 4*s)
    head_c = (cx - 20*s + tremor, cy - 74*s)
    head_r = 15*s
    knee = (cx + 12*s, cy + 34*s)
    foot = (cx + 20*s, cy + 66*s)
    l_knee = (cx - 4*s, cy + 34*s)
    l_foot = (cx - 10*s, cy + 66*s)
    # Both arms thrown up/back — the universal "shock" read.
    r_elbow = (r_sh[0] + 22*s, r_sh[1] - 26*s)
    r_hand = (r_elbow[0] + 10*s, r_elbow[1] - 24*s)
    l_elbow = (l_sh[0] - 22*s, l_sh[1] - 24*s)
    l_hand = (l_elbow[0] - 8*s, l_elbow[1] - 24*s)

    lw = max(3, int(5*s))
    draw.line([hip, knee], fill=color, width=lw)
    draw.line([knee, foot], fill=color, width=lw)
    draw.line([hip, l_knee], fill=color, width=lw)
    draw.line([l_knee, l_foot], fill=color, width=lw)
    draw.line([hip, neck], fill=color, width=lw+1)
    draw.line([neck, head_c], fill=color, width=lw)
    draw.line([l_sh, r_sh], fill=color, width=lw)
    draw.line([r_sh, r_elbow], fill=color, width=lw)
    draw.line([r_elbow, r_hand], fill=color, width=lw)
    draw.line([l_sh, l_elbow], fill=color, width=lw)
    draw.line([l_elbow, l_hand], fill=color, width=lw)
    draw.ellipse([head_c[0]-head_r, head_c[1]-head_r, head_c[0]+head_r, head_c[1]+head_r],
                 outline=color, width=lw)


_DRAW_FN = {
    "WALK":      lambda d, cx, cy, ph, c, s: _draw_walk_run(d, cx, cy, ph, c, s, running=False),
    "RUN":       lambda d, cx, cy, ph, c, s: _draw_walk_run(d, cx, cy, ph, c, s, running=True),
    "SIT_WRITE": _draw_sit_write,
    "ALERT":     _draw_alert,
    "SHOCK":     _draw_shock,
}


def _radial_backlight(width, height, cx_frac, color, strength=70):
    """
    A soft lighter patch behind the silhouette so a solid black figure
    actually reads against a dark background -- direct fix for the real
    bug found this session in the thumbnail silhouette layer (45%-
    opacity dark-on-dark = invisible). Cheap to compute: one small
    radial gradient drawn straight into the frame each time, not a
    cached asset.
    """
    from PIL import Image
    import numpy as np
    w, h = int(width), int(height)
    cx, cy = int(w * cx_frac), int(h * 0.55)
    yy, xx = np.mgrid[0:h, 0:w]
    dist = np.sqrt((xx - cx) ** 2 + ((yy - cy) * 1.3) ** 2)
    radius = h * 0.55
    falloff = np.clip(1.0 - dist / radius, 0, 1) ** 1.6
    layer = np.zeros((h, w, 3), dtype=np.uint8)
    for i in range(3):
        layer[:, :, i] = (falloff * color[i] * (strength / 255)).astype(np.uint8)
    return Image.fromarray(layer, "RGB")


def generate_silhouette_segment(niche_name, segment_text, text_overlay, duration, seg_index,
                                 output_path, width=W, height=H, fps=FPS, log_fn=print):
    """
    SILHOUETTE register (25% of the mix, per direct spec): the same
    jointed rig, but rendered as a solid black cutout in front of a soft
    backlight glow instead of the full-color WALK/RUN treatment --
    visually distinct from the STICKMAN register on purpose (suspense/
    atmosphere beats: alone, silence, shadow), not just a recolor.
    """
    action = detect_action(segment_text)
    if action in ("SIT_WRITE",):
        action = "ALERT"  # writing detail doesn't read as a suspense beat; alert/idle does
    draw_fn = _DRAW_FN[action]
    glow_color = NICHE_FIGURE_COLOR.get(niche_name, NICHE_FIGURE_COLOR["dark_horror"])
    bg = NICHE_BG_COLOR.get(niche_name, NICHE_BG_COLOR["dark_horror"])

    n_frames = max(1, int(round(duration * fps)))
    tmp_dir = Path(output_path).parent / f"sil_{seg_index}"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    font_path = next((fp for fp in font_paths if Path(fp).exists()), None)
    from PIL import ImageFont
    font = ImageFont.truetype(font_path, 30) if font_path else None
    esc_text = (text_overlay or "")[:42]

    try:
        cycle_speed = 2 * math.pi / (fps * 4.0)
        phase_offset = (seg_index * 1.7) % 6.28
        backlight = _radial_backlight(width, height, 0.62, glow_color, strength=95)
        for f in range(n_frames):
            phase = phase_offset + f * cycle_speed
            img = Image.new("RGB", (width, height), bg)
            img.paste(backlight, (0, 0))
            draw = ImageDraw.Draw(img)
            draw_fn(draw, width * 0.62, height * 0.66, phase, (0, 0, 0), 2.3)
            if font and esc_text:
                bbox = draw.textbbox((0, 0), esc_text, font=font)
                tw = bbox[2] - bbox[0]
                draw.text(((width - tw) / 2, height - height / 6), esc_text,
                          fill=glow_color, font=font, stroke_width=2, stroke_fill=(0, 0, 0))
            img.save(tmp_dir / f"f_{f:04d}.png")

        result = subprocess.run(
            ["ffmpeg", "-y", "-framerate", str(fps), "-i", str(tmp_dir / "f_%04d.png"),
             "-c:v", "libx264", "-preset", "fast", "-crf", "22",
             "-pix_fmt", "yuv420p", "-t", f"{duration:.2f}", str(output_path)],
            capture_output=True, timeout=120)
        ok = result.returncode == 0 and Path(output_path).exists() and Path(output_path).stat().st_size > 2000
        if not ok:
            log_fn(f"    Silhouette segment {seg_index}: ffmpeg failed — "
                   f"{result.stderr.decode(errors='ignore')[-300:]}")
        return ok
    except Exception as e:
        log_fn(f"    Silhouette segment {seg_index}: {e}")
        return False
    finally:
        try:
            for p in tmp_dir.glob("f_*.png"):
                p.unlink()
            tmp_dir.rmdir()
        except Exception:
            pass


def generate_stickman_segment(niche_name, segment_text, text_overlay, duration, seg_index,
                               output_path, width=W, height=H, fps=FPS, log_fn=print):
    """
    Renders ONE real stick-figure animation clip for this segment,
    action chosen by real keyword detection on segment_text (the same
    per-segment narration slice already used for the old stock-footage
    search), with the same content-derived phrase burned in as on-
    screen kinetic text. Returns True/False, never raises.
    """
    action = detect_action(segment_text)
    draw_fn = _DRAW_FN[action]
    color = NICHE_FIGURE_COLOR.get(niche_name, NICHE_FIGURE_COLOR["dark_horror"])
    bg = NICHE_BG_COLOR.get(niche_name, NICHE_BG_COLOR["dark_horror"])

    n_frames = max(1, int(round(duration * fps)))
    tmp_dir = Path(output_path).parent / f"stick_{seg_index}"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    font_path = next((fp for fp in font_paths if Path(fp).exists()), None)
    from PIL import ImageFont
    font = ImageFont.truetype(font_path, 30) if font_path else None
    esc_text = (text_overlay or "")[:42]

    try:
        cycle_speed = 2 * math.pi / (fps * (1.6 if action in ("WALK", "RUN") else 4.0))
        # FIX (found this session via a real end-to-end render + frame
        # inspection): every segment started its OWN clip at phase=0,
        # so a WALK/RUN action landed on the exact same neutral
        # leg-crossing pose at the start of every single one of the
        # 55-65 cuts in an episode -- confirmed live, a real frame at
        # t=15s came back frozen on that crossing pose. A per-segment
        # phase offset (same technique already proven for the earlier
        # glow system's drift) means consecutive segments start at
        # different points in the gait instead of all resetting together.
        phase_offset = (seg_index * 1.7) % 6.28
        for f in range(n_frames):
            phase = phase_offset + f * cycle_speed
            img = Image.new("RGB", (width, height), bg)
            draw = ImageDraw.Draw(img)
            draw_fn(draw, width*0.28, height*0.62, phase, color, 2.1)
            if font and esc_text:
                bbox = draw.textbbox((0, 0), esc_text, font=font)
                tw = bbox[2] - bbox[0]
                draw.text(((width - tw) / 2, height - height/6), esc_text,
                           fill=color, font=font, stroke_width=2, stroke_fill=(0, 0, 0))
            img.save(tmp_dir / f"f_{f:04d}.png")

        result = subprocess.run(
            ["ffmpeg", "-y", "-framerate", str(fps), "-i", str(tmp_dir / "f_%04d.png"),
             "-c:v", "libx264", "-preset", "fast", "-crf", "22",
             "-pix_fmt", "yuv420p", "-t", f"{duration:.2f}", str(output_path)],
            capture_output=True, timeout=120)

        # FIX (found this session, real false negative): a >20000-byte
        # floor rejected genuinely valid, correctly-encoded clips for
        # simpler/more static poses (SIT_WRITE, ALERT measured at
        # 18-20KB for a real 3s 1280x720 h264 clip, confirmed valid via
        # ffprobe) -- ffmpeg's own returncode is the real signal;
        # >2000 bytes only guards against a truly empty/corrupt file.
        ok = result.returncode == 0 and Path(output_path).exists() and Path(output_path).stat().st_size > 2000
        if not ok:
            log_fn(f"    Stickman segment {seg_index}: ffmpeg failed — "
                   f"{result.stderr.decode(errors='ignore')[-300:]}")
        return ok
    except Exception as e:
        log_fn(f"    Stickman segment {seg_index}: {e}")
        return False
    finally:
        try:
            for p in tmp_dir.glob("f_*.png"):
                p.unlink()
            tmp_dir.rmdir()
        except Exception:
            pass
