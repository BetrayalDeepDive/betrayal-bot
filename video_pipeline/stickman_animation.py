"""
Real character animation for Ch1 — v2 rebuild, direct user feedback this
session: "the stickman that you developed is too boring... it can't tell
the story... what is the use of a stickman when it can't tell the story?
...how is it showing something in the black? Where is the background
visual?"

Root problems in v1 (confirmed via direct user review of a real published
sample, not assumed): the figure was outline-only (no face, no weight),
composited over a FLAT SOLID COLOR with nothing behind it, and a small
burned-in keyword caption duplicated the real narration subtitles
elsewhere in the pipeline (two competing text elements on screen at once).

v2 fixes, in order of how directly they map to that feedback:
  1. A real background scene behind every character shot -- per-niche,
     procedurally drawn once per segment (not per-frame, for speed),
     giving the character somewhere to actually exist.
  2. A filled body (thick capsule limbs, filled head) with a simple face
     (eyes + brow) instead of bare outline strokes -- reads as a
     character, not a wireframe.
  3. No more burned-in on-screen text anywhere in this module. The real
     word-synced subtitles (compose_video()'s .ass burn-in) are the only
     text that should ever appear on screen -- this was the direct
     "subtitles as well as a text overlay... two things happening" bug.

Still a real, disclosed scope limit: this is procedural 2D compositing
via Pillow, not hand-illustrated or rigged 3D/Grease Pencil character
work. If this pass still doesn't clear the bar on a real render, the
next real step is Blender Grease Pencil (confirmed working headless in
this environment) for genuine rigged 2D character animation -- a bigger
lift, not attempted here until this cheaper pass is verified.
"""
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw
import subprocess

W, H = 1280, 720
FPS = 24

# ══════════════════════════════════════════════════════════════════
# CONTENT -> ACTION mapping (unchanged from v1 -- this part was never
# the complaint; the complaint was what the action was drawn ONTO).
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
    text = (segment_text or "").lower()
    for action in ("SHOCK", "ALERT", "SIT_WRITE", "RUN"):
        if any(kw in text for kw in _ACTION_KEYWORDS[action]):
            return action
    return _DEFAULT_ACTION


# ══════════════════════════════════════════════════════════════════
# NICHE -> palette + real background scene
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
NICHE_ACCENT = {
    "dark_horror":        (150, 40, 40),
    "seduction_dark":     (170, 50, 90),
    "psychological_trap": (50, 140, 100),
    "supernatural_real":  (70, 100, 170),
    "obsession_dark":     (170, 130, 40),
}


def _draw_scene_background(niche_name, seed, width=W, height=H, force_scene=None):
    """
    Real, per-segment scene background -- the direct fix for "where is
    the background visual?". Cheap procedural flat-shape compositing
    (silhouette buildings/trees/windows against a graded sky), rendered
    ONCE per segment and reused across every frame of it, not redrawn
    per-frame. Distinct family per niche, seeded per segment so
    consecutive shots vary (a street, then a room, then a skyline) the
    way a real cut-together sequence would.
    """
    bg = NICHE_BG_COLOR.get(niche_name, NICHE_BG_COLOR["dark_horror"])
    rnd = random.Random(seed)
    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)
    horizon = int(height * rnd.uniform(0.58, 0.72))

    # FIX (found via real render + frame inspection this session): the
    # first version's silhouette contrast was only bg-color +/- 6 units
    # -- completely invisible on screen (confirmed: a real rendered
    # frame showed a totally flat black background, buildings
    # imperceptible). A real horror/night scene needs a genuinely
    # brighter glow band near the horizon (moonlight/fog/dusk) so
    # silhouette shapes actually read as dark cutouts against it,
    # instead of trying to vary an already-near-black color by a few
    # RGB units.
    glow_band = tuple(min(255, int(c * 3.2) + 14) for c in bg)
    for y in range(0, horizon, 3):
        t = y / max(1, horizon)  # 0 at top (dark sky) -> 1 at horizon (glow)
        shade = tuple(int(bg[i] + (glow_band[i] - bg[i]) * (t ** 1.6)) for i in range(3))
        draw.line([(0, y), (width, y)], fill=shade)
    ground_shade = tuple(max(0, int(c * 0.6)) for c in glow_band)
    draw.rectangle([0, horizon, width, height], fill=ground_shade)

    # Real, visible silhouette shapes: near-black regardless of the
    # niche background color, so they always read as solid cutouts
    # against the lighter glow band above, the same way a real night
    # skyline/treeline photograph looks.
    silhouette_shade = (max(0, bg[0] - 4), max(0, bg[1] - 4), max(0, bg[2] - 2))

    # FIX (found via real render + frame inspection this session): the
    # SILHOUETTE register MUST land on a backlit scene -- a silhouette
    # character rendered against "skyline"/"street"/"treeline" (which
    # put the light source at ground level, not behind the character)
    # is simply a near-black shape on a near-black background: confirmed
    # invisible in a real test frame. force_scene lets the caller pin
    # this to "room_window" (the one scene with a real light source
    # directly behind where the character stands) instead of leaving it
    # to chance.
    scene = force_scene or rnd.choice(["skyline", "room_window", "street", "treeline"])

    if scene == "skyline":
        x = 0
        while x < width:
            bw = rnd.randint(60, 140)
            bh = rnd.randint(int(height * 0.12), int(height * 0.32))
            draw.rectangle([x, horizon - bh, x + bw, horizon], fill=silhouette_shade)
            if rnd.random() < 0.6:
                wx = x + rnd.randint(10, max(11, bw - 20))
                wy = horizon - rnd.randint(10, max(11, bh - 10))
                accent = NICHE_ACCENT.get(niche_name, NICHE_ACCENT["dark_horror"])
                draw.rectangle([wx, wy, wx + 9, wy + 13], fill=tuple(min(255, c + 90) for c in accent))
            x += bw + rnd.randint(4, 14)
    elif scene == "room_window":
        # A dark room with a single lit window/doorway -- real interior cue
        wx0, wy0 = int(width * 0.62), int(horizon - height * 0.28)
        wx1, wy1 = int(width * 0.82), horizon
        accent = NICHE_ACCENT.get(niche_name, NICHE_ACCENT["dark_horror"])
        glow = tuple(min(255, int(c * 1.6) + 70) for c in accent)
        draw.rectangle([wx0, wy0, wx1, wy1], fill=glow, outline=(15, 15, 17), width=8)
        draw.line([(wx0, (wy0 + wy1) // 2), (wx1, (wy0 + wy1) // 2)], fill=(15, 15, 17), width=5)
        draw.line([((wx0 + wx1) // 2, wy0), ((wx0 + wx1) // 2, wy1)], fill=(15, 15, 17), width=5)
        draw.rectangle([int(width * 0.03), horizon - 60, int(width * 0.32), horizon], fill=silhouette_shade)
    elif scene == "street":
        draw.line([(0, horizon), (width, horizon)], fill=silhouette_shade, width=4)
        for lx in range(80, width, 260):
            ly = horizon - rnd.randint(70, 130)
            draw.line([(lx, horizon), (lx, ly)], fill=silhouette_shade, width=7)
            draw.ellipse([lx - 15, ly - 15, lx + 15, ly + 15], fill=(200, 170, 90))
    else:  # treeline
        x = 0
        while x < width:
            tw = rnd.randint(30, 70)
            th = rnd.randint(int(height * 0.15), int(height * 0.30))
            draw.polygon([(x, horizon), (x + tw / 2, horizon - th), (x + tw, horizon)], fill=silhouette_shade)
            x += tw + rnd.randint(6, 24)

    return img


def _draw_face(draw, head_c, head_r, color, action, mirror=1):
    """Minimal but real face -- two eyes + a brow -- the direct fix for
    "it can't tell the story" (a faceless figure reads as an abstract
    wireframe, not a character with a reaction)."""
    ex = head_r * 0.35
    ey = -head_r * 0.05
    eye_r = max(2, head_r * 0.11)
    for side in (-1, 1):
        cx = head_c[0] + side * ex * mirror
        cy = head_c[1] + ey
        draw.ellipse([cx - eye_r, cy - eye_r, cx + eye_r, cy + eye_r], fill=color)
        # brow: angled for alert/shock, flat otherwise
        brow_y = cy - eye_r * 2.4
        if action in ("ALERT", "SHOCK"):
            tilt = eye_r * 1.1 * (1 if side * mirror > 0 else -1)
        else:
            tilt = 0
        draw.line([(cx - eye_r * 1.3, brow_y + tilt * 0.3), (cx + eye_r * 1.3, brow_y - tilt * 0.3)],
                  fill=color, width=max(2, int(head_r * 0.09)))


def _draw_walk_run(draw, cx, cy, phase, color, scale, running=False, filled=True, action="WALK"):
    s = scale
    speed = 1.4 if running else 1.0
    lean = 8 if running else 0
    hip_y = cy - (26 if running else 14)*s*abs(math.sin(phase*2))
    hip = (cx, hip_y)
    neck = (cx + lean*s, hip_y - 55*s)
    shoulder_w = 15*s
    l_sh = (neck[0] - shoulder_w, neck[1] + 4*s)
    r_sh = (neck[0] + shoulder_w, neck[1] + 4*s)
    head_c = (neck[0] + lean*0.5*s, hip_y - 80*s)
    head_r = 17*s

    leg_swing = 46 if running else 32
    r_thigh_ang = math.radians(90 + leg_swing*math.sin(phase*speed))
    l_thigh_ang = math.radians(90 + leg_swing*math.sin(phase*speed + math.pi))

    def leg_points(hip_pt, thigh_ang, lead_val):
        knee_len = 34*s
        shin_len = 34*s
        knee = (hip_pt[0] + knee_len*math.cos(thigh_ang),
                hip_pt[1] + knee_len*math.sin(thigh_ang))
        # FIX (found via real render + frame inspection at t=400s of the
        # full integration-test video): the shin used to bend to an
        # ABSOLUTE world angle (90 +/- offset), disconnected from the
        # thigh's own angle. At the extremes of the stride (thigh swung
        # far to one side), that absolute shin angle pointed back across
        # the body's centerline, crossing the other leg into a broken-
        # looking diamond/tangled pose. The shin must continue in the
        # thigh's own direction with a small knee-bend offset (bigger
        # when trailing, smaller when leading) so it never reverses
        # across the centerline.
        thigh_deg = math.degrees(thigh_ang)
        knee_bend = ((36 if running else 22) if lead_val < -0.2
                     else (-6 if lead_val > 0.2 else 4))
        bend = math.radians(thigh_deg + knee_bend)
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

    lw = max(5, int(9*s)) if filled else max(3, int(5*s))
    # torso as a filled rounded capsule instead of a bare line -- gives
    # the character actual body mass instead of reading as a wireframe.
    _capsule(draw, hip, neck, lw * 1.6, color)
    _capsule(draw, hip, r_knee, lw, color)
    _capsule(draw, r_knee, r_foot, lw, color)
    _capsule(draw, hip, l_knee, lw, color)
    _capsule(draw, l_knee, l_foot, lw, color)
    _capsule(draw, neck, head_c, lw, color)
    _capsule(draw, l_sh, r_sh, lw, color)
    _capsule(draw, r_sh, r_elbow, lw, color)
    _capsule(draw, r_elbow, r_hand, lw, color)
    _capsule(draw, l_sh, l_elbow, lw, color)
    _capsule(draw, l_elbow, l_hand, lw, color)
    if filled:
        draw.ellipse([head_c[0]-head_r, head_c[1]-head_r, head_c[0]+head_r, head_c[1]+head_r], fill=color)
    else:
        draw.ellipse([head_c[0]-head_r, head_c[1]-head_r, head_c[0]+head_r, head_c[1]+head_r], outline=color, width=lw)
    return head_c, head_r


def _capsule(draw, p0, p1, width, color):
    """A thick, round-ended line segment -- the basic unit that turns a
    bare stick-line rig into something with real body mass."""
    draw.line([p0, p1], fill=color, width=int(width))
    r = width / 2
    draw.ellipse([p0[0]-r, p0[1]-r, p0[0]+r, p0[1]+r], fill=color)
    draw.ellipse([p1[0]-r, p1[1]-r, p1[0]+r, p1[1]+r], fill=color)


def _draw_sit_write(draw, cx, cy, phase, color, scale, filled=True):
    s = scale
    hip = (cx, cy)
    neck = (cx, cy - 50*s)
    shoulder_w = 15*s
    l_sh = (neck[0] - shoulder_w, neck[1] + 4*s)
    r_sh = (neck[0] + shoulder_w, neck[1] + 4*s)
    head_c = (cx + 6*s, cy - 74*s)
    head_r = 17*s
    knee = (cx + 30*s, cy + 4*s)
    foot = (cx + 30*s, cy + 38*s)
    l_knee = (cx - 30*s, cy + 4*s)
    l_foot = (cx - 30*s, cy + 38*s)
    desk_y = cy + 6*s
    write_x = cx + 44*s + 4*s*math.sin(phase*6)
    r_elbow = (cx + 24*s, cy - 20*s)
    r_hand = (write_x, desk_y)
    l_elbow = (cx - 20*s, cy - 15*s)
    l_hand = (cx - 32*s, desk_y - 2*s)

    lw = max(5, int(9*s))
    _capsule(draw, hip, knee, lw, color)
    _capsule(draw, knee, foot, lw, color)
    _capsule(draw, hip, l_knee, lw, color)
    _capsule(draw, l_knee, l_foot, lw, color)
    _capsule(draw, hip, neck, lw * 1.6, color)
    _capsule(draw, neck, head_c, lw, color)
    _capsule(draw, l_sh, r_sh, lw, color)
    _capsule(draw, r_sh, r_elbow, lw, color)
    _capsule(draw, r_elbow, r_hand, lw, color)
    _capsule(draw, l_sh, l_elbow, lw, color)
    _capsule(draw, l_elbow, l_hand, lw, color)
    draw.ellipse([head_c[0]-head_r, head_c[1]-head_r, head_c[0]+head_r, head_c[1]+head_r], fill=color)
    draw.line([(cx + 10*s, desk_y), (cx + 70*s, desk_y)], fill=color, width=max(3, int(4*s)))
    return head_c, head_r


def _draw_alert(draw, cx, cy, phase, color, scale, filled=True):
    s = scale
    sway = 3*s*math.sin(phase*1.2)
    hip = (cx + sway, cy)
    neck = (cx + sway, cy - 55*s)
    shoulder_w = 15*s
    l_sh = (neck[0] - shoulder_w, neck[1] + 4*s)
    r_sh = (neck[0] + shoulder_w, neck[1] + 4*s)
    head_c = (cx + sway*1.5, cy - 78*s)
    head_r = 17*s
    knee = (cx + sway*0.5 + 10*s, cy + 34*s)
    foot = (cx + sway*0.3 + 10*s, cy + 66*s)
    l_knee = (cx + sway*0.5 - 10*s, cy + 34*s)
    l_foot = (cx + sway*0.3 - 10*s, cy + 66*s)
    r_elbow = (r_sh[0] + 20*s, r_sh[1] - 18*s)
    r_hand = (r_elbow[0] + 30*s, r_elbow[1] - 6*s)
    l_elbow = (l_sh[0] - 10*s, l_sh[1] + 24*s)
    l_hand = (l_elbow[0] - 6*s, l_elbow[1] + 22*s)

    lw = max(5, int(9*s))
    _capsule(draw, hip, knee, lw, color)
    _capsule(draw, knee, foot, lw, color)
    _capsule(draw, hip, l_knee, lw, color)
    _capsule(draw, l_knee, l_foot, lw, color)
    _capsule(draw, hip, neck, lw * 1.6, color)
    _capsule(draw, neck, head_c, lw, color)
    _capsule(draw, l_sh, r_sh, lw, color)
    _capsule(draw, r_sh, r_elbow, lw, color)
    _capsule(draw, r_elbow, r_hand, lw, color)
    _capsule(draw, l_sh, l_elbow, lw, color)
    _capsule(draw, l_elbow, l_hand, lw, color)
    draw.ellipse([head_c[0]-head_r, head_c[1]-head_r, head_c[0]+head_r, head_c[1]+head_r], fill=color)
    return head_c, head_r


def _draw_shock(draw, cx, cy, phase, color, scale, filled=True):
    s = scale
    tremor = 2*s*math.sin(phase*10)
    hip = (cx + tremor, cy)
    neck = (cx - 12*s + tremor, cy - 50*s)
    shoulder_w = 15*s
    l_sh = (neck[0] - shoulder_w, neck[1] + 4*s)
    r_sh = (neck[0] + shoulder_w, neck[1] + 4*s)
    head_c = (cx - 20*s + tremor, cy - 74*s)
    head_r = 17*s
    knee = (cx + 12*s, cy + 34*s)
    foot = (cx + 20*s, cy + 66*s)
    l_knee = (cx - 4*s, cy + 34*s)
    l_foot = (cx - 10*s, cy + 66*s)
    r_elbow = (r_sh[0] + 22*s, r_sh[1] - 26*s)
    r_hand = (r_elbow[0] + 10*s, r_elbow[1] - 24*s)
    l_elbow = (l_sh[0] - 22*s, l_sh[1] - 24*s)
    l_hand = (l_elbow[0] - 8*s, l_elbow[1] - 24*s)

    lw = max(5, int(9*s))
    _capsule(draw, hip, knee, lw, color)
    _capsule(draw, knee, foot, lw, color)
    _capsule(draw, hip, l_knee, lw, color)
    _capsule(draw, l_knee, l_foot, lw, color)
    _capsule(draw, hip, neck, lw * 1.6, color)
    _capsule(draw, neck, head_c, lw, color)
    _capsule(draw, l_sh, r_sh, lw, color)
    _capsule(draw, r_sh, r_elbow, lw, color)
    _capsule(draw, r_elbow, r_hand, lw, color)
    _capsule(draw, l_sh, l_elbow, lw, color)
    _capsule(draw, l_elbow, l_hand, lw, color)
    draw.ellipse([head_c[0]-head_r, head_c[1]-head_r, head_c[0]+head_r, head_c[1]+head_r], fill=color)
    return head_c, head_r


_DRAW_FN = {
    "WALK":      lambda d, cx, cy, ph, c, s, **kw: _draw_walk_run(d, cx, cy, ph, c, s, running=False, action="WALK"),
    "RUN":       lambda d, cx, cy, ph, c, s, **kw: _draw_walk_run(d, cx, cy, ph, c, s, running=True, action="RUN"),
    "SIT_WRITE": _draw_sit_write,
    "ALERT":     _draw_alert,
    "SHOCK":     _draw_shock,
}


def _render_common(niche_name, segment_text, duration, seg_index, output_path,
                    width, height, fps, log_fn, silhouette=False,
                    search_terms=None, pixabay_key="", pexels_key=""):
    action = detect_action(segment_text)
    if silhouette and action == "SIT_WRITE":
        action = "ALERT"
    draw_fn = _DRAW_FN[action]
    figure_color = NICHE_FIGURE_COLOR.get(niche_name, NICHE_FIGURE_COLOR["dark_horror"])
    char_color = (10, 10, 12) if silhouette else figure_color

    n_frames = max(1, int(round(duration * fps)))
    tag = "sil" if silhouette else "stick"
    tmp_dir = Path(output_path).parent / f"{tag}_{seg_index}"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    try:
        # FIX (direct user follow-up after reviewing sample renders: "the
        # pictures look the same... too generic... I want something
        # based on the specific niche and the topic... can we use real
        # pictures for it"): try a real, topic-matched photo (Pixabay/
        # Pexels, same free keys/relevance-check already proven for
        # stock footage) before falling back to the procedural
        # silhouette-shape background. search_terms is this segment's
        # own already-tuned keyword list (topic anchor / concrete noun /
        # nation context) threaded in by the caller -- a "dark room" or
        # "forest trail" segment searches for THAT real scene, not a
        # generic mood phrase.
        background = None
        if search_terms and (pixabay_key or pexels_key):
            try:
                from photo_background import fetch_photo_background, photo_to_cover_canvas, grade_photo
                photo_cache = Path(output_path).parent / f"photobg_{tag}_{seg_index}.jpg"
                photo_path = fetch_photo_background(
                    search_terms, niche_name, str(photo_cache),
                    pixabay_key=pixabay_key, pexels_key=pexels_key, log_fn=log_fn)
                if photo_path:
                    canvas = photo_to_cover_canvas(photo_path, width, height, oversize=1.0)
                    background = grade_photo(canvas, niche_name, silhouette=silhouette)
            except Exception as e:
                log_fn(f"    Real photo background (non-fatal, falling back to drawn scene): {e}")
        if background is None:
            background = _draw_scene_background(
                niche_name, seed=seg_index * 31 + (7 if silhouette else 0), width=width, height=height,
                force_scene="room_window" if silhouette else None)
        cycle_speed = 2 * math.pi / (fps * (1.6 if action in ("WALK", "RUN") else 4.0))
        phase_offset = (seg_index * 1.7) % 6.28
        cx_frac = 0.72 if silhouette else 0.30
        for f in range(n_frames):
            phase = phase_offset + f * cycle_speed
            img = background.copy()
            draw = ImageDraw.Draw(img)
            head_c, head_r = draw_fn(draw, width * cx_frac, height * 0.66, phase, char_color, 2.2)
            if not silhouette:
                _draw_face(draw, head_c, head_r, tuple(max(0, c - 160) for c in figure_color), action)
            img.save(tmp_dir / f"f_{f:04d}.png")

        result = subprocess.run(
            ["ffmpeg", "-y", "-framerate", str(fps), "-i", str(tmp_dir / "f_%04d.png"),
             "-c:v", "libx264", "-preset", "fast", "-crf", "22",
             "-pix_fmt", "yuv420p", "-t", f"{duration:.2f}", str(output_path)],
            capture_output=True, timeout=120)
        ok = result.returncode == 0 and Path(output_path).exists() and Path(output_path).stat().st_size > 2000
        if not ok:
            log_fn(f"    {tag} segment {seg_index}: ffmpeg failed — "
                   f"{result.stderr.decode(errors='ignore')[-300:]}")
        return ok
    except Exception as e:
        log_fn(f"    {tag} segment {seg_index}: {e}")
        return False
    finally:
        try:
            for p in tmp_dir.glob("f_*.png"):
                p.unlink()
            tmp_dir.rmdir()
        except Exception:
            pass


def generate_stickman_segment(niche_name, segment_text, text_overlay, duration, seg_index,
                               output_path, width=W, height=H, fps=FPS, log_fn=print,
                               search_terms=None, pixabay_key="", pexels_key=""):
    """
    STICKMAN register (40% of the mix). text_overlay is accepted for
    call-site compatibility but deliberately unused -- the real, word-
    synced subtitles (compose_video()'s .ass burn-in) are the only text
    that should appear on screen; this stopped burning its own separate
    keyword caption per direct user report of two competing text
    elements on screen at once. search_terms/pixabay_key/pexels_key are
    optional -- when given, this segment's background tries a real,
    topic-matched photo before falling back to the drawn scene (see
    photo_background.py).
    """
    return _render_common(niche_name, segment_text, duration, seg_index, output_path,
                           width, height, fps, log_fn, silhouette=False,
                           search_terms=search_terms, pixabay_key=pixabay_key, pexels_key=pexels_key)


def generate_silhouette_segment(niche_name, segment_text, text_overlay, duration, seg_index,
                                 output_path, width=W, height=H, fps=FPS, log_fn=print,
                                 search_terms=None, pixabay_key="", pexels_key=""):
    """
    SILHOUETTE register (25% of the mix) -- same real background scene,
    character rendered as a solid dark cutout in the "room_window"/
    backlit-doorway family of scenes so it reads as a distinct shot, not
    a recolor of the STICKMAN register. No burned-in text (see above).
    search_terms/pixabay_key/pexels_key: see generate_stickman_segment.
    """
    return _render_common(niche_name, segment_text, duration, seg_index, output_path,
                           width, height, fps, log_fn, silhouette=True,
                           search_terms=search_terms, pixabay_key=pixabay_key, pexels_key=pexels_key)
