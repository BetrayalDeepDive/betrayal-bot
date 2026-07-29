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
import re
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np
import subprocess

W, H = 1280, 720
FPS = 24

# ══════════════════════════════════════════════════════════════════
# CONTENT -> ACTION mapping -- expanded from the original 5 actions to
# the full 17-pose library built this session (video_pipeline/
# character_rig_blender.py), each pose pre-rendered once by
# tools/build_character_assets.py and composited live by
# character_loop.py. Order matters: checked most-specific/dramatic
# first so a segment matching several categories lands on the one that
# actually drives the story forward (e.g. SHOCK before WALK).
# ══════════════════════════════════════════════════════════════════
_ACTION_KEYWORDS = {
    "RUN":            ["ran", "running", "fled", "flee", "chase", "chasing", "escape",
                        "sprint", "sprinted", "raced", "bolted"],
    "SIT_WRITE":      ["wrote", "notebook", "diary", "desk", "writing", "letter",
                        "journal", "typed", "typing", "logged", "recorded", "documented",
                        # FIX (direct user report, July 29 2026): analytical/
                        # planning language never mapped to anything -- fell
                        # straight to the WALK default.
                        "analyzed", "analysis", "studied", "researched", "compiled",
                        "calculated", "plotted", "planned", "schemed", "scheme",
                        "orchestrated", "engineered", "devised", "strategized"],
    "ALERT":          ["pointed", "warned", "noticed", "spotted", "watched", "realized",
                        "discovered", "stared", "witnessed", "saw",
                        # FIX (direct user report, July 29 2026 — "background
                        # not matching, stickman just moving"): the psychological-
                        # manipulation/reality-TV vocabulary this niche's own
                        # scripts actually use (manipulated, gaslit, targeted,
                        # exploited) had zero coverage anywhere in this table.
                        "manipulated", "manipulate", "manipulation", "controlled",
                        "control", "targeted", "target", "exploited", "exploit",
                        "gaslit", "gaslighting", "deceived", "deceive", "tricked",
                        "groomed", "conditioned"],
    "SHOCK":          ["found", "dead", "body", "collapsed", "screamed", "shock",
                        "shocked", "gasped", "horrified", "vanished", "disappeared",
                        "betrayed", "betrayal", "exposed", "unraveled", "shattered"],
    "CRY_GRIEF":      ["wept", "cried", "crying", "sobbed", "sobbing", "mourned",
                        "grief", "tears", "heartbroken", "devastated"],
    "ANGRY_CONFRONT": ["confronted", "accused", "argued", "shouted", "screamed at",
                        "yelled", "furious", "enraged", "demanded answers"],
    "PHONE_CALL":     ["called", "phone rang", "answered the phone", "picked up the phone",
                        "dialed", "hung up", "voicemail", "texted"],
    "COLLAPSE_KNEEL": ["collapsed", "broke down", "fell to her knees", "fell to his knees",
                        "sank to the floor", "crumpled"],
    "COWER_DEFENSE":  ["cowered", "flinched", "shielded herself", "shielded himself",
                        "recoiled", "cringed", "braced for",
                        "isolated", "isolation", "trapped", "cornered", "powerless",
                        "helpless", "vulnerable"],
    "KNOCK_DOOR":     ["knocked", "opened the door", "entered the", "walked through the door",
                        "answered the door", "let her in", "let him in"],
    "SEARCH_RUMMAGE": ["searched", "rummaged", "dug through", "went through the drawer",
                        "combed through", "ransacked", "rifled through",
                        # FIX (direct user report, July 29 2026 — "when I told
                        # it about investigative things, just moved"): this
                        # channel's own scripts say "investigate/investigation"
                        # constantly (it's even in the SEO hook template,
                        # "INVESTIGATION: ..."), yet that exact word was
                        # missing from every single category -- guaranteeing
                        # the single most common narration beat in this whole
                        # channel fell straight through to the generic WALK
                        # default every time.
                        "investigated", "investigate", "investigation", "investigating",
                        "uncovered", "uncover", "pieced together", "traced", "examined"],
    "WAIT":           ["waited", "stood there", "watched from", "kept watch",
                        "lingered", "stayed silent", "left alone", "abandoned"],
    "LOOK_AROUND":    ["looked around", "scanned the room", "glanced around",
                        "surveyed", "searched the room with her eyes", "checked the room",
                        "monitored", "observed", "surveilled", "tracked"],
    "HAPPY":          ["laughed", "smiled", "delighted", "overjoyed", "celebrated",
                        "relieved", "grateful"],
    "DANCE":          ["danced", "dancing", "twirled", "swayed to the music"],
}
_DEFAULT_ACTION = "WALK"
_ACTION_PRIORITY = ("SHOCK", "COLLAPSE_KNEEL", "ANGRY_CONFRONT", "CRY_GRIEF",
                    "COWER_DEFENSE", "ALERT", "SIT_WRITE", "PHONE_CALL",
                    "KNOCK_DOOR", "SEARCH_RUMMAGE", "RUN", "DANCE", "HAPPY",
                    "LOOK_AROUND", "WAIT")

# FIX (found live while building a demo sample, July 29 2026): plain
# substring matching meant "body" (a SHOCK keyword) matched inside
# "no**body**", "every**body**", "some**body**" -- ordinary words that
# appear constantly in narration and have nothing to do with a body
# being found. Confirmed live: "The investigation uncovered a pattern
# **nobody** expected" matched SHOCK via "body" before it ever reached
# SEARCH_RUMMAGE's genuine "investigation"/"uncovered" hits, silently
# overriding the correct pose. Same risk applies to several of this
# session's own additions (e.g. "control" inside "controller"). Word-
# boundary regex matching fixes both without changing any keyword list.
_ACTION_KEYWORD_PATTERNS = {
    action: [re.compile(r'\b' + re.escape(kw) + r'\b') for kw in kws]
    for action, kws in _ACTION_KEYWORDS.items()
}


def detect_action(segment_text):
    text = (segment_text or "").lower()
    for action in _ACTION_PRIORITY:
        if any(p.search(text) for p in _ACTION_KEYWORD_PATTERNS[action]):
            return action
    return _DEFAULT_ACTION


# ══════════════════════════════════════════════════════════════════
# NICHE -> palette + real background scene
# ══════════════════════════════════════════════════════════════════
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


_SCENE_TYPES = [
    "skyline", "room_window", "street", "treeline", "alleyway",
    "parking_lot", "porch", "staircase", "hallway", "bedroom",
    "basement", "attic", "garage", "fence_yard", "lake_dock",
    "mountain_ridge", "rural_road", "cemetery", "hospital_corridor",
    "rain_window",
]


def _draw_scene_background(niche_name, seed, width=W, height=H, force_scene=None):
    """
    Real, per-segment scene background -- the direct fix for "where is
    the background visual?". Cheap procedural flat-shape compositing
    (silhouette buildings/trees/windows against a graded sky), rendered
    ONCE per segment and reused across every frame of it, not redrawn
    per-frame. Distinct family per niche, seeded per segment so
    consecutive shots vary (a street, then a room, then a skyline) the
    way a real cut-together sequence would.

    FIX (direct user follow-up, this session -- "still showing me the
    static one, which I don't like... I want multiple... more than 18
    backgrounds... more natural... shouldn't feel like it's AI-made or
    something forced out of proportion"): expanded from 4 scene families
    to 20 (_SCENE_TYPES above), and a subtle per-image film-grain pass is
    now baked into the final static image (cheap -- this runs ONCE per
    segment, not per frame) so the flat vector-shape look picks up real
    texture instead of reading as a perfectly clean digital render. The
    real, production-side answer to "more natural" is still the real
    Pixabay/Pexels photo backgrounds already wired in photo_background.py
    (this procedural system is the FALLBACK for whenever no real photo
    hit comes back) -- this expansion makes that fallback itself far
    less repetitive and less sterile-looking in its own right.
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

    # FIX (found live, July 29 2026 -- direct user report "the background
    # doesn't even match, stickman is doing nonsense things"): the comment
    # right above this used to claim silhouette_shade was "near-black
    # regardless of the niche background color" but the actual value was
    # bg-4 -- i.e. within 2-4 RGB units of the sky it's supposed to
    # contrast against. Confirmed live by extracting real rendered frames:
    # an "alleyway" scene showed a flat black frame with only a thin
    # hanging-bulb wire and glow visible -- the two flanking building
    # walls were there in code but functionally invisible, indistinguishable
    # from both the dark sky and most of the glow gradient. A fixed,
    # genuinely near-black tone (independent of bg, since bg is often
    # already near-black itself) is what actually delivers the comment's
    # original intent: a real dark cutout that only needs to out-contrast
    # the BRIGHTEST part of the glow band near the horizon to read as a
    # skyline silhouette, the way a real night photo looks.
    silhouette_shade = (5, 5, 7)

    # FIX (found via real render + frame inspection this session): the
    # SILHOUETTE register MUST land on a backlit scene -- a silhouette
    # character rendered against "skyline"/"street"/"treeline" (which
    # put the light source at ground level, not behind the character)
    # is simply a near-black shape on a near-black background: confirmed
    # invisible in a real test frame. force_scene lets the caller pin
    # this to "room_window" (the one scene with a real light source
    # directly behind where the character stands) instead of leaving it
    # to chance.
    scene = force_scene or rnd.choice(_SCENE_TYPES)
    accent = NICHE_ACCENT.get(niche_name, NICHE_ACCENT["dark_horror"])

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
    elif scene == "treeline":
        x = 0
        while x < width:
            tw = rnd.randint(30, 70)
            th = rnd.randint(int(height * 0.15), int(height * 0.30))
            draw.polygon([(x, horizon), (x + tw / 2, horizon - th), (x + tw, horizon)], fill=silhouette_shade)
            x += tw + rnd.randint(6, 24)
    elif scene == "alleyway":
        # two flanking building walls with a narrow gap, a single hanging
        # light bulb -- a claustrophobic corridor-of-brick feel
        draw.rectangle([0, horizon - int(height * 0.5), int(width * 0.38), horizon], fill=silhouette_shade)
        draw.rectangle([int(width * 0.62), horizon - int(height * 0.5), width, horizon], fill=silhouette_shade)
        lx = width // 2
        ly = horizon - int(height * 0.30)
        draw.line([(lx, horizon - int(height * 0.5)), (lx, ly)], fill=(20, 20, 22), width=3)
        glow = tuple(min(255, int(c * 1.6) + 70) for c in accent)
        draw.ellipse([lx - 14, ly - 6, lx + 14, ly + 20], fill=glow)
    elif scene == "parking_lot":
        x = 20
        while x < width - 60:
            cw = rnd.randint(70, 110)
            draw.rectangle([x, horizon - 34, x + cw, horizon], fill=silhouette_shade)
            draw.rectangle([x + 8, horizon - 46, x + cw - 8, horizon - 30], fill=silhouette_shade)
            x += cw + rnd.randint(20, 50)
        for lx in range(60, width, 340):
            ly = horizon - rnd.randint(140, 190)
            draw.line([(lx, horizon), (lx, ly)], fill=silhouette_shade, width=5)
            draw.ellipse([lx - 10, ly - 10, lx + 10, ly + 10], fill=(210, 190, 120))
    elif scene == "porch":
        draw.rectangle([int(width * 0.15), horizon - int(height * 0.34), int(width * 0.85), horizon], fill=silhouette_shade)
        px0, py0 = int(width * 0.44), horizon - int(height * 0.14)
        px1, py1 = int(width * 0.56), horizon
        glow = tuple(min(255, int(c * 1.6) + 70) for c in accent)
        draw.rectangle([px0, py0, px1, py1], fill=glow, outline=(15, 15, 17), width=6)
        lx, ly = int(width * 0.70), horizon - int(height * 0.20)
        draw.ellipse([lx - 9, ly - 9, lx + 9, ly + 9], fill=(215, 190, 120))
        draw.line([(int(width * 0.15), horizon - 6), (int(width * 0.85), horizon - 6)], fill=(20, 20, 22), width=4)
    elif scene == "staircase":
        steps = 9
        sw, sh = width * 0.5 / steps, height * 0.28 / steps
        for i in range(steps):
            x0 = width * 0.1 + i * sw
            y0 = horizon - i * sh
            draw.rectangle([x0, y0 - sh * 0.6, x0 + sw * 1.4, horizon], fill=silhouette_shade)
        draw.line([(width * 0.1, horizon - height * 0.24), (width * 0.55, horizon - 4)], fill=(20, 20, 22), width=4)
    elif scene == "hallway":
        vp = (width * 0.5, horizon - height * 0.12)
        draw.polygon([(0, horizon - height * 0.30), vp, (vp[0], horizon), (0, horizon)], fill=silhouette_shade)
        draw.polygon([(width, horizon - height * 0.30), vp, (vp[0], horizon), (width, horizon)], fill=silhouette_shade)
        glow = tuple(min(255, int(c * 1.5) + 60) for c in accent)
        draw.ellipse([vp[0] - 16, vp[1] - 10, vp[0] + 16, vp[1] + 18], fill=glow)
    elif scene == "bedroom":
        draw.rectangle([int(width * 0.08), horizon - int(height * 0.13), int(width * 0.42), horizon], fill=silhouette_shade)
        lx, ly = int(width * 0.60), horizon - int(height * 0.22)
        glow = tuple(min(255, int(c * 1.6) + 70) for c in accent)
        draw.ellipse([lx - 20, ly - 4, lx + 20, ly + 40], fill=glow)
        draw.rectangle([lx - 3, ly + 20, lx + 3, horizon], fill=silhouette_shade)
    elif scene == "basement":
        draw.line([(0, horizon - int(height * 0.32)), (width, horizon - int(height * 0.32))], fill=silhouette_shade, width=6)
        draw.line([(0, horizon - int(height * 0.26)), (width, horizon - int(height * 0.26))], fill=silhouette_shade, width=4)
        bx, by = width * 0.5, horizon - int(height * 0.30)
        draw.line([(bx, by), (bx, by + 30)], fill=(20, 20, 22), width=2)
        glow = tuple(min(255, int(c * 1.8) + 80) for c in accent)
        draw.ellipse([bx - 10, by + 30, bx + 10, by + 50], fill=glow)
    elif scene == "attic":
        peak = (width * 0.5, horizon - int(height * 0.34))
        draw.polygon([(0, horizon), peak, (width, horizon)], outline=silhouette_shade, width=6)
        draw.line([(width * 0.2, horizon - int(height * 0.10)), (width * 0.8, horizon - int(height * 0.10))], fill=silhouette_shade, width=5)
        glow = tuple(min(255, int(c * 1.5) + 60) for c in accent)
        wx, wy = width * 0.5, horizon - int(height * 0.20)
        draw.ellipse([wx - 22, wy - 22, wx + 22, wy + 22], fill=glow, outline=(15, 15, 17), width=5)
    elif scene == "garage":
        draw.rectangle([int(width * 0.10), horizon - int(height * 0.16), int(width * 0.45), horizon], fill=silhouette_shade)
        draw.ellipse([int(width * 0.14) - 14, horizon - 14, int(width * 0.14) + 14, horizon + 14], fill=silhouette_shade)
        draw.ellipse([int(width * 0.40) - 14, horizon - 14, int(width * 0.40) + 14, horizon + 14], fill=silhouette_shade)
        draw.rectangle([int(width * 0.65), horizon - int(height * 0.22), int(width * 0.85), horizon], fill=silhouette_shade)
    elif scene == "fence_yard":
        x = 0
        while x < width:
            draw.rectangle([x, horizon - 40, x + 6, horizon], fill=silhouette_shade)
            x += 34
        draw.line([(0, horizon - 40), (width, horizon - 40)], fill=silhouette_shade, width=4)
        tx = width * 0.75
        draw.polygon([(tx, horizon - 40), (tx + 40, horizon - 140), (tx + 80, horizon - 40)], fill=silhouette_shade)
    elif scene == "lake_dock":
        draw.rectangle([0, horizon, width, height], fill=tuple(max(0, int(c * 0.5)) for c in silhouette_shade))
        dx = width * 0.5
        draw.rectangle([dx - 10, horizon - 50, dx + 10, horizon], fill=silhouette_shade)
        draw.rectangle([dx + 40, horizon - 40, dx + 60, horizon], fill=silhouette_shade)
        draw.line([(dx - 30, horizon - 55), (dx + 80, horizon - 45)], fill=silhouette_shade, width=8)
    elif scene == "mountain_ridge":
        for depth, shade_mul in ((0.6, 0.7), (0.85, 1.0)):
            pts = [(0, horizon)]
            x = 0
            while x <= width:
                pts.append((x, horizon - int(height * depth * rnd.uniform(0.12, 0.24))))
                x += rnd.randint(90, 160)
            pts.append((width, horizon))
            shade = tuple(int(c * shade_mul) for c in silhouette_shade)
            draw.polygon(pts, fill=shade)
    elif scene == "rural_road":
        vp = (width * 0.5, horizon - int(height * 0.05))
        draw.polygon([(width * 0.35, horizon), (vp[0] - 4, vp[1]), (vp[0] + 4, vp[1]), (width * 0.65, horizon)], fill=(20, 20, 22))
        for i in range(6):
            px = width * 0.2 + i * (width * 0.6 / 6)
            py = horizon - i * 4
            draw.line([(px, horizon), (px, py - 40)], fill=silhouette_shade, width=4)
    elif scene == "cemetery":
        x = 30
        while x < width - 30:
            hw = rnd.randint(24, 40)
            hh = rnd.randint(30, 55)
            draw.rectangle([x, horizon - hh, x + hw, horizon], fill=silhouette_shade)
            draw.ellipse([x, horizon - hh - hw // 2, x + hw, horizon - hh + hw // 2], fill=silhouette_shade)
            x += hw + rnd.randint(40, 90)
        tx = width * 0.85
        draw.polygon([(tx, horizon), (tx + 20, horizon - 90), (tx + 40, horizon)], fill=silhouette_shade)
    elif scene == "hospital_corridor":
        vp = (width * 0.5, horizon - int(height * 0.16))
        draw.polygon([(0, horizon - int(height * 0.28)), vp, (vp[0], horizon), (0, horizon)], fill=silhouette_shade)
        draw.polygon([(width, horizon - int(height * 0.28)), vp, (vp[0], horizon), (width, horizon)], fill=silhouette_shade)
        for i in range(3):
            lx0 = width * 0.3 + i * width * 0.15
            ly = horizon - int(height * 0.24) + i * 6
            draw.rectangle([lx0, ly, lx0 + width * 0.10, ly + 5], fill=(220, 225, 230))
    else:  # rain_window
        wx0, wy0 = int(width * 0.30), int(horizon - height * 0.30)
        wx1, wy1 = int(width * 0.70), horizon
        glow = tuple(min(255, int(c * 1.4) + 55) for c in accent)
        draw.rectangle([wx0, wy0, wx1, wy1], fill=glow, outline=(15, 15, 17), width=8)
        for i in range(14):
            rx = rnd.uniform(wx0 + 10, wx1 - 10)
            ry0 = rnd.uniform(wy0 + 5, wy1 - 40)
            draw.line([(rx, ry0), (rx - 6, ry0 + 34)], fill=(15, 15, 17), width=2)

    # Subtle per-image film-grain pass -- direct user follow-up: "shouldn't
    # feel like it's AI-made or something forced out of proportion". Runs
    # ONCE per segment (this whole function already runs once per
    # segment, not per frame), so the cost is negligible; a perfectly
    # clean flat-shade render is one of the biggest visual tells of a
    # digital/procedural origin, and real texture breaks that up.
    arr = np.asarray(img, dtype=np.float32)
    noise = np.random.default_rng(seed).normal(0, 3.5, arr.shape[:2])
    arr += noise[..., None]
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

    return img


def _render_common(niche_name, segment_text, duration, seg_index, output_path,
                    width, height, fps, log_fn, silhouette=False,
                    search_terms=None, pixabay_key="", pexels_key=""):
    """
    Delegates to the real Blender-rig character (video_pipeline/
    character_loop.py), replacing the old thin Pillow stick-figure draw.
    detect_action()'s expanded 17-way keyword mapping picks which
    pre-rendered pose asset (built once by tools/build_character_assets.py)
    to composite -- action names match pose names in
    character_rig_blender.py's SINGLE_POSE_FUNCS 1:1, no translation
    needed. SIT_WRITE has no sensible silhouette read in the backlit-
    doorway family of scenes (a seated figure needs to be see at all,
    not just a cutout), so it substitutes ALERT for that register only,
    same behavior as the previous implementation.
    """
    action = detect_action(segment_text)
    if silhouette and action == "SIT_WRITE":
        action = "ALERT"
    from character_loop import generate_character_segment
    return generate_character_segment(
        niche_name, action, segment_text, None, duration, seg_index, output_path,
        width=width, height=height, fps=fps, silhouette=silhouette,
        search_terms=search_terms, pixabay_key=pixabay_key, pexels_key=pexels_key, log_fn=log_fn)


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
