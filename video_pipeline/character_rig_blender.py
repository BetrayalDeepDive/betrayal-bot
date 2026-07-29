"""
Ch1 character rig -- Blender Grease Pencil, run headless via
`blender --background --factory-startup --python character_rig_blender.py -- MODE OUT_DIR`.

OFFLINE ASSET-GENERATION SCRIPT, NOT part of the live per-episode
pipeline: Blender takes ~30s to render a single 5s/60-frame pose loop,
and a real episode has 15-20 character segments -- invoking Blender
fresh per segment would add 20-25 minutes per episode and risks CI
timeouts. Real fix (how automated video pipelines actually handle this):
render each pose ONCE into a reusable transparent PNG-sequence asset
(see tools/build_character_assets.py, which drives this script and
crops/stores the output under video_pipeline/character_assets/<POSE>/),
then the live pipeline (video_pipeline/character_loop.py) composites
that pre-rendered asset over a real/procedural background per segment
using pure Python + ffmpeg -- no live Blender invocation at runtime.

MODE: ONE_CHAR | TWO_CHAR | WALK | RUN | SIT_WRITE | ALERT | SHOCK |
WAIT | LOOK_AROUND | CRY_GRIEF | ANGRY_CONFRONT | PHONE_CALL |
COLLAPSE_KNEEL | COWER_DEFENSE | KNOCK_DOOR | SEARCH_RUMMAGE | HAPPY |
DANCE (17 single-character poses total, direct user spec: "add a
minimum of 15 poses"), plus TWO_CHAR (two-character conversation with a
real speech bubble).
"""
import bpy
import math
import random
import sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MODE = argv[0] if argv else "TWO_CHAR"
OUT = argv[1] if len(argv) > 1 else "/tmp/sample.mp4"
SINGLE_FRAME = "--still" in argv

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in [
    e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
FPS_RENDER = 12
scene.render.fps = FPS_RENDER
DURATION_S = 5.0
N_FRAMES = int(DURATION_S * FPS_RENDER)
scene.frame_start = 1
scene.frame_end = N_FRAMES
try:
    scene.eevee.taa_render_samples = 16
except Exception:
    pass

# FIX (direct user report -- "the background... stagnant with one
# forest/trees kind of silhouette... not just one"): rather than
# reimplementing the 4-type scene variety (skyline/room/street/treeline)
# a SECOND time inside Blender, the character now renders on a
# TRANSPARENT background (no GP background objects at all here) and gets
# composited afterward, in plain Python/Pillow, over stickman_animation's
# existing, already-varied, already-panning background system -- the
# exact same real code the other registers already use. This also
# directly fixes "the background... stagnant": that compositing step
# reuses scene_recreation.py's Ken Burns pan/zoom, so the background is
# never a single frozen frame even during a character shot.
world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0, 0, 0, 0)
scene.render.film_transparent = True

cam_data = bpy.data.cameras.new("Cam")
cam_data.type = 'ORTHO'
# FIX (direct user report -- "the stickman should be a little short, not
# taking the whole page dimension"): zoomed OUT from the previous 6.2/7.0
# (which made the character fill ~85-90% of frame height) to a real,
# proportionate size -- the character now reads as a figure IN a scene,
# not a close-up crop of just the character.
cam_data.ortho_scale = 9.5 if MODE == "TWO_CHAR" else 8.6
cam_obj = bpy.data.objects.new("Cam", cam_data)
scene.collection.objects.link(cam_obj)
cam_obj.location = (0, -10, 0.72 if MODE == "TWO_CHAR" else 0.42)
cam_obj.rotation_euler = (math.radians(90), 0, 0)
scene.camera = cam_obj

sun = bpy.data.lights.new("Sun", type='SUN')
sun.energy = 1.0
sun_obj = bpy.data.objects.new("Sun", sun)
scene.collection.objects.link(sun_obj)
sun_obj.location = (0, -5, 4)
sun_obj.rotation_euler = (math.radians(55), 0, math.radians(20))

# ---------------------------------------------------------------
# Character materials -- filled body shapes with a thin outline
# (the "flat 2D vector character" look real storytime channels use,
# not a bare stick-figure outline)
# ---------------------------------------------------------------
def mat_fill_stroke(name, fill, stroke):
    m = bpy.data.materials.new(name)
    bpy.data.materials.create_gpencil_data(m)
    m.grease_pencil.show_stroke = True
    m.grease_pencil.show_fill = True
    m.grease_pencil.fill_color = fill
    m.grease_pencil.color = stroke
    return m

gp_data = bpy.data.grease_pencils.new("Character")
gp_obj = bpy.data.objects.new("Character", gp_data)
scene.collection.objects.link(gp_obj)
layer = gp_data.layers.new("Body")

# FIX (direct user report, second round -- "someone is wearing big
# pampers diapers... so stupid"): TWO real, compounding causes, both
# fixed here. (1) The "rim light" was an offset, fully-outlined SECOND
# shape drawn behind the coat -- Grease Pencil fill materials are flat
# color with a hard stroke outline, so an offset copy reads as a solid
# extra costume panel, not a soft glow; there is no cheap way to fake a
# gradient highlight with flat-fill GP materials, so this technique is
# abandoned entirely rather than re-tuned again. (2) The legs were
# rendered in bare SKIN color with a coat hem stopping at the hip --
# bare skin-toned legs directly under a coat is exactly what reads as a
# diaper. Real fix: actual trousers (a dark slacks material) and actual
# shoes (a dark shoe material), not bare skin, below the coat.
SKIN = (0.62, 0.52, 0.46, 1.0)
OUTLINE = (0.04, 0.04, 0.05, 1.0)
SHIRT_A = (0.15, 0.17, 0.23, 1.0)   # charcoal-navy coat
SHIRT_B = (0.26, 0.12, 0.14, 1.0)   # deep maroon coat
HAIR_A = (0.09, 0.07, 0.06, 1.0)
HAIR_B = (0.16, 0.12, 0.10, 1.0)
TROUSERS = (0.11, 0.11, 0.13, 1.0)   # dark slacks -- NOT bare skin
SHOE = (0.06, 0.06, 0.07, 1.0)        # dark shoes -- NOT bare skin
# Direct user spec, this round: "if it is angry, the face turns red...
# if happy, turns something else" -- real emotion-tinted skin variants,
# selected per pose via EMOTION_TINT below, instead of one flat skin
# tone for every pose regardless of what's happening in the story.
SKIN_ANGRY = (0.68, 0.32, 0.28, 1.0)   # flushed red
SKIN_PALE = (0.58, 0.54, 0.52, 1.0)    # drained/pale (shock, fear)
SKIN_WARM = (0.72, 0.54, 0.44, 1.0)    # warm/rosy (happy, content)

skin_mat = mat_fill_stroke("Skin", SKIN, OUTLINE)
shirt_a_mat = mat_fill_stroke("ShirtA", SHIRT_A, OUTLINE)
shirt_b_mat = mat_fill_stroke("ShirtB", SHIRT_B, OUTLINE)
hair_a_mat = mat_fill_stroke("HairA", HAIR_A, OUTLINE)
hair_b_mat = mat_fill_stroke("HairB", HAIR_B, OUTLINE)
trousers_mat = mat_fill_stroke("Trousers", TROUSERS, OUTLINE)
shoe_mat = mat_fill_stroke("Shoe", SHOE, OUTLINE)
skin_angry_mat = mat_fill_stroke("SkinAngry", SKIN_ANGRY, OUTLINE)
skin_pale_mat = mat_fill_stroke("SkinPale", SKIN_PALE, OUTLINE)
skin_warm_mat = mat_fill_stroke("SkinWarm", SKIN_WARM, OUTLINE)
gp_data.materials.append(skin_mat)    # 0
gp_data.materials.append(shirt_a_mat) # 1
gp_data.materials.append(shirt_b_mat) # 2
gp_data.materials.append(hair_a_mat)  # 3
gp_data.materials.append(hair_b_mat)  # 4

# speech bubble material
bubble_mat = mat_fill_stroke("Bubble", (0.96, 0.96, 0.98, 1.0), (0.08, 0.07, 0.09, 1.0))
gp_data.materials.append(bubble_mat)  # 5
gp_data.materials.append(trousers_mat)   # 6
gp_data.materials.append(shoe_mat)       # 7
gp_data.materials.append(skin_angry_mat) # 8
gp_data.materials.append(skin_pale_mat)  # 9
gp_data.materials.append(skin_warm_mat)  # 10
MAT_TROUSERS, MAT_SHOE = 6, 7
MAT_SKIN_ANGRY, MAT_SKIN_PALE, MAT_SKIN_WARM = 8, 9, 10


def filled_capsule(frame, p0, p1, radius, material_index, y_off=0.0):
    """A real filled stadium shape (two half-circle caps + straight sides)
    -- this is what gives limbs actual body mass/thickness, not a thin
    stroke outline."""
    import math as _m
    dx, dz = p1[0] - p0[0], p1[1] - p0[1]
    length = _m.hypot(dx, dz)
    if length < 1e-6:
        ang = 0.0
    else:
        ang = _m.atan2(dz, dx)
    n = 10
    pts = []
    # cap around p1
    for i in range(n + 1):
        a = ang - math.pi / 2 + (math.pi * i / n)
        pts.append((p1[0] + radius * math.cos(a), p1[1] + radius * math.sin(a)))
    # cap around p0 (offset by pi)
    for i in range(n + 1):
        a = ang + math.pi / 2 + (math.pi * i / n)
        pts.append((p0[0] + radius * math.cos(a), p0[1] + radius * math.sin(a)))
    s = frame.strokes.new()
    s.points.add(len(pts))
    for i, (x, z) in enumerate(pts):
        s.points[i].co = (x, y_off, z)
    s.use_cyclic = True
    s.material_index = material_index
    s.line_width = 12
    return s


def filled_circle(frame, center, radius, material_index, y_off=0.0, n=24):
    s = frame.strokes.new()
    s.points.add(n)
    for i in range(n):
        a = 2 * math.pi * i / n
        s.points[i].co = (center[0] + radius * math.cos(a), y_off, center[1] + radius * math.sin(a))
    s.use_cyclic = True
    s.material_index = material_index
    s.line_width = 12
    return s


def draw_profile_shape(frame, base, tip, profile, mat_idx, y_off=0.0, n_cap=10):
    """A single closed silhouette with a VARYING radius along its length
    (profile = ordered [(t, radius), ...], t=0 at base, t=1 at tip, t<0
    extends past the base) -- rounded cap at the tip using the last
    radius, one side traced through the profile, rounded cap at the
    base using the first radius, other side traced back. Generalizes
    filled_capsule (constant radius) to a real tapered/flared garment
    silhouette -- direct user report: the plain capsule torso read as
    "a doodle... general", a coat-shaped silhouette (broad shoulders,
    tapered waist, flared hem) is a far more deliberate design choice."""
    dx, dz = tip[0] - base[0], tip[1] - base[1]
    length = math.hypot(dx, dz) or 1e-6
    ux, uz = dx / length, dz / length
    nx, nz = -uz, ux
    ang = math.atan2(dz, dx)

    def pt_at(t):
        return (base[0] + ux * t * length, base[1] + uz * t * length)

    pts = []
    tip_t, tip_r = profile[-1]
    tip_pt = pt_at(tip_t)
    for i in range(n_cap + 1):
        a = ang - math.pi / 2 + (math.pi * i / n_cap)
        pts.append((tip_pt[0] + tip_r * math.cos(a), tip_pt[1] + tip_r * math.sin(a)))
    for t, r in reversed(profile[:-1]):
        p = pt_at(t)
        pts.append((p[0] + nx * r, p[1] + nz * r))
    base_t, base_r = profile[0]
    base_pt = pt_at(base_t)
    for i in range(n_cap + 1):
        a = ang + math.pi / 2 + (math.pi * i / n_cap)
        pts.append((base_pt[0] + base_r * math.cos(a), base_pt[1] + base_r * math.sin(a)))
    for t, r in profile[1:]:
        p = pt_at(t)
        pts.append((p[0] - nx * r, p[1] - nz * r))
    s = frame.strokes.new()
    s.points.add(len(pts))
    for i, (x, z) in enumerate(pts):
        s.points[i].co = (x, y_off, z)
    s.use_cyclic = True
    s.material_index = mat_idx
    s.line_width = 12
    return s


def draw_bent_leg(frame, hip_pt, knee_pt, foot_pt, radius, mat_idx, y_off=0.0):
    """A real bent leg -- thigh (hip->knee) and shin (knee->foot) as two
    SAME-radius capsules plus a matching-radius circle at the knee
    (drawn after both, same fill color) so the two segments blend into
    one continuous limb with no seam. FIX (direct user report -- "legs
    feel like they are stretching out"): the earlier version's seam bug
    came from mismatched thigh/shin radii (0.16 vs 0.13), not from
    having a real knee bend at all -- so the original fix (collapsing to
    one straight hip-to-ankle capsule) also threw out the ability to
    ever show a bent knee, which is exactly what a real walk cycle's
    swing leg and a real sitting pose both need. Equal radii + a
    congruent join-circle fixes the seam without giving up the bend --
    when knee_pt sits on the straight hip->foot line (the default for
    standing poses), this renders identically to a straight leg."""
    filled_capsule(frame, hip_pt, knee_pt, radius, mat_idx, y_off)
    filled_capsule(frame, knee_pt, foot_pt, radius, mat_idx, y_off)
    filled_circle(frame, knee_pt, radius, mat_idx, y_off + 0.001, n=16)


def draw_fingers(frame, elbow, hand, skin_idx, y_off=0.0, n_fingers=3):
    """Real fingers -- direct user report: "for the legs and the hands, I
    want fingers. Where are the fingers?". Three short capsules fanning
    out from the hand in the forearm's own direction, drawn AFTER the
    hand blob so they read as digits extending past it, not a blank
    mitten/paddle shape."""
    dx, dz = hand[0] - elbow[0], hand[1] - elbow[1]
    length = math.hypot(dx, dz) or 1e-6
    ang = math.atan2(dz, dx)
    spread = math.radians(16)
    flen, frad = 0.085, 0.026
    for i in range(n_fingers):
        a = ang + spread * (i - (n_fingers - 1) / 2)
        tip = (hand[0] + flen * math.cos(a), hand[1] + flen * math.sin(a))
        filled_capsule(frame, hand, tip, frad, skin_idx, y_off)


def draw_toes(frame, foot_pt, skin_idx, y_off=0.0):
    """Real toes -- same user report, applied to the feet. Small bumps
    along the front edge of the foot oval instead of a blank paddle."""
    fx = foot_pt[0] + 0.05 + 0.12
    for dz in (-0.032, 0.0, 0.032):
        filled_circle(frame, (fx, foot_pt[1] - 0.05 + dz), 0.024, skin_idx, y_off + 0.001, n=8)


def build_character(frame, origin_x, segs, head_c, head_r, shirt_mat, hair_mat, y_off, face_dir=1, eye_state="open", emotion="neutral", profile_dir=0):
    hip, neck = segs["hip"], segs["neck"]
    # skin tint per emotion -- direct user spec: "if it is angry, the
    # face turns red... if happy, turns something else" -- a real,
    # selected material variant per pose's emotional register, applied
    # to the head and hands, instead of one flat skin tone always.
    skin_idx = {"angry": MAT_SKIN_ANGRY, "pale": MAT_SKIN_PALE, "warm": MAT_SKIN_WARM}.get(emotion, 0)
    for hip_pt, knee_pt, foot_pt in ((segs["r_hip"], segs["r_knee"], segs["r_foot"]),
                                       (segs["l_hip"], segs["l_knee"], segs["l_foot"])):
        # FIX (direct user report -- "someone is wearing big pampers
        # diapers"): legs used to be bare SKIN color under a coat hem --
        # real trousers now, not bare skin.
        draw_bent_leg(frame, hip_pt, knee_pt, foot_pt, 0.145, MAT_TROUSERS, y_off - 0.01)
        # foot -- real dark shoe color, not bare skin, plus toes
        foot_shape = frame.strokes.new()
        fw, fh = 0.24, 0.11
        fn = 12
        pts = []
        for i in range(fn):
            a = 2 * math.pi * i / fn
            pts.append((foot_pt[0] + 0.05 + (fw / 2) * math.cos(a), foot_pt[1] - 0.05 + (fh / 2) * math.sin(a)))
        foot_shape.points.add(fn)
        for i, (x, z) in enumerate(pts):
            foot_shape.points[i].co = (x, y_off - 0.011, z)
        foot_shape.use_cyclic = True
        foot_shape.material_index = MAT_SHOE
        foot_shape.line_width = 12
        draw_toes(frame, foot_pt, skin_idx, y_off)
    # torso -- a real coat silhouette: broad shoulders, a tapered waist,
    # a hem that flares out and extends below the hip. FIX (direct user
    # report, second round): the rim-light offset-shape trick from the
    # last pass is REMOVED entirely -- flat-fill GP materials with a
    # hard stroke outline can't fake a soft glow; an offset copy just
    # reads as a second, solid costume panel (part of what caused the
    # "diaper" look). Single clean coat fill only.
    coat_profile = [(-0.20, 0.28), (0.0, 0.24), (0.35, 0.26), (0.7, 0.30), (1.0, 0.33)]
    draw_profile_shape(frame, hip, neck, coat_profile, shirt_mat, y_off)
    # arms + fingers -- FIX (direct user report: "it has two hands side
    # by side, which is really incorrect because it's walking... it
    # should have only one hand"): a real profile view of a walking
    # person only shows ONE arm -- the near arm swings fully visible,
    # the far arm is hidden behind the body. Drawing both arms
    # side-by-side only makes anatomical sense for a FRONT-FACING pose;
    # for a profile pose (profile_dir != 0) only the single visible
    # swinging arm is drawn.
    if profile_dir != 0:
        filled_capsule(frame, segs["r_sh"], segs["r_elbow"], 0.15, shirt_mat, y_off + 0.005)
        filled_capsule(frame, segs["r_elbow"], segs["r_hand"], 0.13, skin_idx, y_off + 0.005)
        draw_fingers(frame, segs["r_elbow"], segs["r_hand"], skin_idx, y_off + 0.006)
    else:
        filled_capsule(frame, segs["r_sh"], segs["r_elbow"], 0.15, shirt_mat, y_off + 0.005)
        filled_capsule(frame, segs["r_elbow"], segs["r_hand"], 0.13, skin_idx, y_off + 0.005)
        draw_fingers(frame, segs["r_elbow"], segs["r_hand"], skin_idx, y_off + 0.006)
        filled_capsule(frame, segs["l_sh"], segs["l_elbow"], 0.15, shirt_mat, y_off + 0.005)
        filled_capsule(frame, segs["l_elbow"], segs["l_hand"], 0.13, skin_idx, y_off + 0.005)
        draw_fingers(frame, segs["l_elbow"], segs["l_hand"], skin_idx, y_off + 0.006)
    # head -- tinted per emotion, no rim light (see torso note above)
    filled_circle(frame, head_c, head_r, skin_idx, y_off + 0.01)
    if profile_dir != 0:
        # FIX (direct user correction, this round -- "the sideways walk
        # is a walk... the face shouldn't look into the camera, it
        # should look in front"): a walking character needs a real
        # PROFILE face looking in the direction of travel, not a
        # front-facing face staring at the viewer while the legs do a
        # side-view stride -- that mismatch is what read as "robotic".
        # Real profile head: a nose/chin bump on the leading side, ONE
        # eye near it, hair covering mostly the BACK of the head.
        face_a = 0.0 if profile_dir > 0 else math.pi
        nose_len = head_r * 0.30
        nose_y = head_c[1] - head_r * 0.02
        tip = (head_c[0] + profile_dir * (head_r + nose_len), nose_y)
        b1 = (head_c[0] + profile_dir * head_r * 0.88, nose_y + head_r * 0.16)
        b2 = (head_c[0] + profile_dir * head_r * 0.88, nose_y - head_r * 0.20)
        nose = frame.strokes.new()
        nose.points.add(3)
        for i, (x, z) in enumerate((tip, b1, b2)):
            nose.points[i].co = (x, y_off + 0.011, z)
        nose.use_cyclic = True
        nose.material_index = skin_idx
        nose.line_width = 12
        # hair -- covers roughly 260 degrees, leaving a wedge open at
        # the face so the profile reads clearly
        n = 18
        pts = []
        hair_z_offset = head_r * 0.12
        start_a = face_a + math.radians(55)
        end_a = face_a + math.radians(305)
        for i in range(n + 1):
            a = start_a + (end_a - start_a) * i / n
            pts.append((head_c[0] + head_r * 1.15 * math.cos(a),
                        head_c[1] + hair_z_offset + head_r * 1.0 * math.sin(a)))
        s = frame.strokes.new()
        s.points.add(len(pts))
        for i, (x, z) in enumerate(pts):
            s.points[i].co = (x, y_off + 0.015, z)
        s.use_cyclic = True
        s.material_index = hair_mat
        s.line_width = 12
        # one eye, near the leading edge
        eye_x = head_c[0] + profile_dir * head_r * 0.42
        eye_y = head_c[1] + head_r * 0.04
        eye = frame.strokes.new()
        eye.points.add(2)
        eye.points[0].co = (eye_x - profile_dir * 0.02, y_off + 0.02, eye_y)
        eye.points[1].co = (eye_x + profile_dir * 0.025, y_off + 0.02, eye_y - head_r * 0.02)
        eye.line_width = 50
        eye.material_index = 0
        eye.use_cyclic = False
    else:
        # hair -- a clean, symmetric hairline, front-facing
        n = 14
        pts = []
        hair_z_offset = head_r * 0.15
        for i in range(n + 1):
            a = math.pi * i / n
            pts.append((head_c[0] + head_r * 1.12 * math.cos(a), head_c[1] + hair_z_offset + head_r * 1.02 * math.sin(a)))
        s = frame.strokes.new()
        s.points.add(len(pts))
        for i, (x, z) in enumerate(pts):
            s.points[i].co = (x, y_off + 0.015, z)
        s.use_cyclic = True
        s.material_index = hair_mat
        s.line_width = 12
        # eyes -- two, symmetric, facing the camera
        for ex in (-head_r * 0.35 * face_dir, head_r * 0.05 * face_dir):
            if eye_state == "open":
                eye = frame.strokes.new()
                eye.points.add(2)
                eye.points[0].co = (head_c[0] + ex - 0.025, y_off + 0.02, head_c[1] + head_r * 0.05)
                eye.points[1].co = (head_c[0] + ex + 0.025, y_off + 0.02, head_c[1] + head_r * 0.05)
                eye.line_width = 60
                eye.material_index = 0
                eye.use_cyclic = False
            else:  # closed / blink -- flat line already covers it visually the same width, kept simple
                eye = frame.strokes.new()
                eye.points.add(2)
                eye.points[0].co = (head_c[0] + ex - 0.02, y_off + 0.02, head_c[1] + head_r * 0.05)
                eye.points[1].co = (head_c[0] + ex + 0.02, y_off + 0.02, head_c[1] + head_r * 0.05)
                eye.line_width = 20
                eye.material_index = 0


def pose_stand_talk(t, gesture_phase=0.0, seed=0):
    """A standing conversational pose -- weight shift + one arm gesturing,
    not a walk cycle (this register is 'two people talking', not walking)."""
    sway = 0.04 * math.sin(t * 2 * math.pi * 0.5 + seed)
    hip = (0.0, 0.0 + sway * 0.3)
    neck = (0.02 * math.sin(t * 2 * math.pi * 0.5 + seed), 1.35)
    head_c = (neck[0] + 0.01, 1.62)
    r_hip = (0.14, 0.02)
    l_hip = (-0.14, 0.02)
    r_knee = (0.16, -0.55)
    l_knee = (-0.15, -0.55)
    r_foot = (0.18, -1.05)
    l_foot = (-0.17, -1.05)
    r_sh = (0.32, 1.28)
    l_sh = (-0.32, 1.28)
    gesture = 0.5 * math.sin(gesture_phase)
    r_elbow = (r_sh[0] + 0.22, r_sh[1] - 0.15 + 0.15 * max(0, gesture))
    r_hand = (r_elbow[0] + 0.18 + 0.15 * max(0, gesture), r_elbow[1] + 0.05 * max(0, gesture))
    l_elbow = (l_sh[0] - 0.20, l_sh[1] - 0.30)
    l_hand = (l_elbow[0] - 0.05, l_elbow[1] - 0.28)
    return {
        "hip": hip, "neck": neck, "r_hip": r_hip, "l_hip": l_hip,
        "r_knee": r_knee, "l_knee": l_knee, "r_foot": r_foot, "l_foot": l_foot,
        "r_sh": r_sh, "l_sh": l_sh, "r_elbow": r_elbow, "r_hand": r_hand,
        "l_elbow": l_elbow, "l_hand": l_hand,
    }, head_c


WALK_FACE_DIR = 1  # WALK/RUN always face +x (right) -- profile head + stride direction must agree


def pose_walk_run(t, running=False, seed=0):
    """WALK/RUN, PROFILE (side) view -- direct user correction, second
    round: "the sideways walk is a walk... the face shouldn't look into
    the camera, it should look in front... legs and hands should be
    moving accordingly".

    Real research/reasoning: a side-view gait is the STANDARD, correct
    way to depict a walking human in 2D -- this is how Muybridge's
    original human/horse locomotion studies were filmed, how Richard
    Williams' "Animator's Survival Kit" walk-cycle chapter builds every
    reference walk, and how virtually every 2D explainer/reenactment
    walk-cycle asset works: the fore-aft leg and arm swing only reads
    clearly in profile. My previous pass mistakenly kept the FACE
    front-on (staring at the camera) while trying to show this stride --
    that mismatch (a profile gait bolted onto a front-facing face) is
    what actually read as "robotic", not the sideways leg motion, which
    was correct all along. Real fix: restore the full fore-aft stride
    (this is the same structure as the very first version, since that
    part was right), and pair it with a genuine PROFILE FACE (see
    build_character's profile_dir param) so the character visibly looks
    in the direction it's walking, not at the viewer. Bent-knee swing-
    leg mechanic (draw_bent_leg) and the real 4-key CONTACT/DOWN/
    PASSING/UP body-bob timing (Williams' reference) are kept from the
    last pass -- those were genuine improvements, independent of the
    front-vs-profile question."""
    speed = 1.5 if running else 1.0
    phase = t * 4 * math.pi * speed + seed
    stride = 0.44 if running else 0.30
    lift = 0.28 if running else 0.16
    hip_bob = (0.055 if running else 0.032) * abs(math.sin(phase))
    lean = 0.12 if running else 0.03
    hip = (lean * 0.3, -hip_bob)
    neck = (lean, 1.35 - hip_bob * 0.5)
    head_c = (lean + 0.02, 1.62 - hip_bob * 0.3)
    r_swing = math.sin(phase)
    l_swing = math.sin(phase + math.pi)
    r_bend = max(0, r_swing)
    l_bend = max(0, l_swing)
    # real fore-aft stride -- both legs share the same hip line (we are
    # looking at the character edge-on, so left/right legs sit close
    # together, offset only by which is forward vs back in the stride)
    r_hip = (0.02, 0.0)
    l_hip = (-0.02, 0.0)
    r_foot = (0.02 + stride * r_swing, -1.05 + r_bend * lift)
    l_foot = (-0.02 + stride * l_swing, -1.05 + l_bend * lift)
    r_knee = (r_hip[0] + (r_foot[0] - r_hip[0]) * 0.5 + 0.08 * r_bend, -0.55 + lift * 1.05 * r_bend)
    l_knee = (l_hip[0] + (l_foot[0] - l_hip[0]) * 0.5 + 0.08 * l_bend, -0.55 + lift * 1.05 * l_bend)
    r_sh = (0.11 + lean, 1.28 - hip_bob * 0.5)
    l_sh = (-0.07 + lean, 1.28 - hip_bob * 0.5)
    # arms swing opposite the same-side leg, fore-aft, matching the gait
    # -- FIX (found via real render this pass): the first version had
    # both shoulders too close together (0.10 apart) with a wide swing,
    # so the two forearms crossed through each other's path at mid-
    # swing, reading as "arms crossed/self-hug" instead of a natural
    # walking swing. Real fix: more shoulder separation plus a smaller
    # swing amplitude so each arm stays in its own lane.
    arm_r = math.sin(phase + math.pi)
    arm_l = math.sin(phase)
    r_elbow = (r_sh[0] + 0.09 * arm_r, r_sh[1] - 0.32 + 0.05 * abs(arm_r))
    r_hand = (r_elbow[0] + 0.11 * arm_r, r_elbow[1] - 0.30)
    l_elbow = (l_sh[0] + 0.09 * arm_l, l_sh[1] - 0.32 + 0.05 * abs(arm_l))
    l_hand = (l_elbow[0] + 0.11 * arm_l, l_elbow[1] - 0.30)
    return {
        "hip": hip, "neck": neck, "r_hip": r_hip, "l_hip": l_hip,
        "r_knee": r_knee, "l_knee": l_knee, "r_foot": r_foot, "l_foot": l_foot,
        "r_sh": r_sh, "l_sh": l_sh, "r_elbow": r_elbow, "r_hand": r_hand,
        "l_elbow": l_elbow, "l_hand": l_hand,
    }, head_c


SEAT_DROP = 0.40
DESK_TOP_Z = 0.08  # shared with draw_desk below so the writing hand rests ON the desktop, not hidden inside its apron


def pose_sit_write(t, seed=0):
    """SIT_WRITE -- direct user report on the first version: "I didn't see
    anything... a person is standing, and opposite to him there is some
    desk... not really correct... should show that it is sitting
    properly... shouldn't feel forced". Root cause: the first version
    hid the ENTIRE lower body behind a tall desk panel, so nothing
    on-screen ever showed a seated silhouette -- just a standing pose
    with a box in front of it. Real fix, now that draw_bent_leg exists:
    genuinely bent knees (thighs angled forward/out from the seat, shins
    down to the floor) drawn fully VISIBLE above a short desk apron, plus
    a real chair back behind the torso -- the classic, unambiguous
    "bent knee + chair back" combination is what actually reads as
    sitting, not just a lower torso position."""
    wiggle = 0.05 * math.sin(t * 2 * math.pi * 3 + seed)
    hip = (0.0, -SEAT_DROP)
    neck = (0.02, 1.28 - SEAT_DROP)
    head_c = (0.04, 1.48 - SEAT_DROP)  # tilted down toward the notebook
    r_hip = (0.14, -SEAT_DROP + 0.02)
    l_hip = (-0.14, -SEAT_DROP + 0.02)
    # real bent knees -- thigh angles forward+out from the seat (reads as
    # the knee pushing lower and wider than the hip), shin then drops
    # straight down to a foot planted on the floor, a genuine seated bend
    r_knee = (0.34, -SEAT_DROP - 0.22)
    l_knee = (-0.32, -SEAT_DROP - 0.22)
    r_foot = (0.32, -1.05)
    l_foot = (-0.30, -1.05)
    r_sh = (0.30, 1.20 - SEAT_DROP)
    l_sh = (-0.30, 1.20 - SEAT_DROP)
    # writing hand rests ON the desktop surface (DESK_TOP_Z), not below it
    # -- resting inside the desk's apron z-range would get drawn over and
    # hidden once draw_desk runs after the character in the frame loop
    r_elbow = (0.42, DESK_TOP_Z + 0.30)
    r_hand = (0.50 + wiggle, DESK_TOP_Z + 0.05)
    l_elbow = (l_sh[0] - 0.05, l_sh[1] - 0.28)
    l_hand = (l_elbow[0] - 0.08, l_elbow[1] - 0.22)
    return {
        "hip": hip, "neck": neck, "r_hip": r_hip, "l_hip": l_hip,
        "r_knee": r_knee, "l_knee": l_knee, "r_foot": r_foot, "l_foot": l_foot,
        "r_sh": r_sh, "l_sh": l_sh, "r_elbow": r_elbow, "r_hand": r_hand,
        "l_elbow": l_elbow, "l_hand": l_hand,
    }, head_c


def pose_alert(t, seed=0):
    """ALERT -- direct user report on the first version: "I don't think it
    is really pointing out alert, because it's just the hand raised...
    make changes to show that it feels alert, somewhat like a flag or
    some instruction or some movement". A static raised arm reads as
    "waving hello", not "alert" -- real fix: the arm SWEEPS a real arc
    (like flagging someone down / signaling), the body leans into the
    direction and bounces on the balls of the feet (urgency), and the
    other arm counter-gestures for emphasis, instead of one arm just
    sitting still in the air."""
    sweep = math.sin(t * 2 * math.pi * 1.8 + seed)  # a real, fairly fast back-and-forth signal
    lean = 0.10 + 0.03 * max(0, sweep)
    bounce = 0.035 * abs(math.sin(t * 2 * math.pi * 3.6 + seed))  # weight bouncing on the toes -- urgency
    hip = (lean * 0.3, bounce)
    neck = (lean * 0.8, 1.35 + bounce * 0.5)
    head_c = (lean + 0.03, 1.62 + bounce * 0.5)
    r_hip = (0.14, bounce * 0.3)
    l_hip = (-0.14, bounce * 0.3)
    r_knee = (0.16, -0.55)
    l_knee = (-0.15, -0.55)
    r_foot = (0.20, -1.05 + bounce * 0.4)
    l_foot = (-0.15, -1.02 + bounce * 0.4)  # weight forward, onto the front foot
    r_sh = (0.32 + lean, 1.28 + bounce * 0.5)
    l_sh = (-0.32 + lean, 1.28 + bounce * 0.5)
    # signaling arm sweeps a real arc from up-and-forward to out-to-the-side
    # (like flagging someone down), not a static hold
    sweep_angle = math.radians(35) + math.radians(45) * sweep
    reach = 0.60
    r_elbow = (r_sh[0] + reach * 0.55 * math.cos(sweep_angle * 0.75), r_sh[1] + reach * 0.55 * math.sin(sweep_angle * 0.75))
    r_hand = (r_sh[0] + reach * math.cos(sweep_angle), r_sh[1] + reach * math.sin(sweep_angle))
    # other arm counter-gestures, low and out, for real emphasis/balance
    l_elbow = (l_sh[0] - 0.20, l_sh[1] - 0.08 - 0.06 * max(0, -sweep))
    l_hand = (l_elbow[0] - 0.18, l_elbow[1] - 0.04 * max(0, -sweep))
    return {
        "hip": hip, "neck": neck, "r_hip": r_hip, "l_hip": l_hip,
        "r_knee": r_knee, "l_knee": l_knee, "r_foot": r_foot, "l_foot": l_foot,
        "r_sh": r_sh, "l_sh": l_sh, "r_elbow": r_elbow, "r_hand": r_hand,
        "l_elbow": l_elbow, "l_hand": l_hand,
    }, head_c


def pose_shock(t, seed=0):
    """SHOCK -- direct user report on the first version: "make sure the
    hands really feel like a continuation of the ears... it's not
    something that feels like a shock". Root cause: the hands were
    placed at head_c[0]+-0.18, which is INSIDE the head circle's own
    radius (0.30) -- they landed near the cheeks/jaw, floating apart
    from the head rather than pressed against it. Real fix: hands
    positioned exactly at the head's own edge at ear height (head_c[0]
    +- HEAD_R*0.92), so the forearm reads as running straight up into
    the side of the head -- "hands clamped over the ears", the classic
    shock/disbelief gesture, not hands hovering near the face."""
    HEAD_R = 0.30
    jolt = math.sin(t * 2 * math.pi * 0.6 + seed)
    lean_back = -0.08 - 0.03 * max(0, jolt)
    hip = (lean_back * 0.3, 0.0)
    neck = (lean_back, 1.35)
    head_c = (lean_back * 1.3, 1.65 + 0.02 * max(0, jolt))
    r_hip = (0.14, 0.02)
    l_hip = (-0.14, 0.02)
    r_knee = (0.17, -0.55)
    l_knee = (-0.16, -0.55)
    r_foot = (0.20, -1.05)
    l_foot = (-0.19, -1.05)
    r_sh = (0.32 + lean_back, 1.28)
    l_sh = (-0.32 + lean_back, 1.28)
    # hands clamped directly over the ears -- at the head's own edge,
    # not floating near the cheeks
    r_hand = (head_c[0] + HEAD_R * 0.92, head_c[1] - HEAD_R * 0.05)
    l_hand = (head_c[0] - HEAD_R * 0.92, head_c[1] - HEAD_R * 0.05)
    r_elbow = (r_sh[0] + 0.10, r_sh[1] + 0.10)
    l_elbow = (l_sh[0] - 0.10, l_sh[1] + 0.10)
    return {
        "hip": hip, "neck": neck, "r_hip": r_hip, "l_hip": l_hip,
        "r_knee": r_knee, "l_knee": l_knee, "r_foot": r_foot, "l_foot": l_foot,
        "r_sh": r_sh, "l_sh": l_sh, "r_elbow": r_elbow, "r_hand": r_hand,
        "l_elbow": l_elbow, "l_hand": l_hand,
    }, head_c


def draw_chair_back(frame, y_off=0.0):
    """Chair back for SIT_WRITE, drawn BEFORE the character (in the
    per-frame loop) so it sits behind the torso -- one of the strongest,
    most unambiguous "this person is sitting" visual cues even from
    straight-on, reinforcing the now-visible bent knees below."""
    chair_mat = 2
    x0, x1 = -0.34, 0.34
    z0, z1 = -SEAT_DROP - 0.05, 1.50 - SEAT_DROP
    pts = [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]
    s = frame.strokes.new()
    s.points.add(len(pts))
    for i, (x, z) in enumerate(pts):
        s.points[i].co = (x, y_off - 0.10, z)
    s.use_cyclic = True
    s.material_index = chair_mat
    s.line_width = 12


def draw_desk(frame, y_off=0.0):
    """Desk prop for SIT_WRITE -- direct user report on the first
    version: "I didn't see anything... a person is standing... not
    really correct". The first version's desk was a full floor-to-
    desktop panel that hid the ENTIRE lower body, so nothing on screen
    ever showed a seated silhouette at all. Real fix: the desktop sits
    at real forearm height with only a SHORT apron below it (not down to
    the floor), so the genuinely bent knees (now drawn via
    draw_bent_leg in pose_sit_write) stay fully visible beneath the
    desk edge -- the bent-knee silhouette is what actually reads as
    "sitting", not a taller desk hiding more of the body."""
    desk_mat = 2  # reuse ShirtB (a plain wood-brown tone) for the desk
    desk_top_z = DESK_TOP_Z
    apron_h = 0.20
    front = frame.strokes.new()
    fpts = [(-0.62, desk_top_z), (0.72, desk_top_z), (0.72, desk_top_z - apron_h), (-0.62, desk_top_z - apron_h)]
    front.points.add(len(fpts))
    for i, (x, z) in enumerate(fpts):
        front.points[i].co = (x, y_off + 0.05, z)
    front.use_cyclic = True
    front.material_index = desk_mat
    front.line_width = 12
    # desktop surface -- a thin highlight bar along the top edge
    top = frame.strokes.new()
    tpts = [(-0.62, desk_top_z), (0.72, desk_top_z),
            (0.72, desk_top_z + 0.07), (-0.62, desk_top_z + 0.07)]
    top.points.add(len(tpts))
    for i, (x, z) in enumerate(tpts):
        top.points[i].co = (x, y_off + 0.06, z)
    top.use_cyclic = True
    top.material_index = desk_mat
    top.line_width = 12
    # notebook -- small light rectangle on the desktop
    nb = frame.strokes.new()
    npts = [(0.08, desk_top_z + 0.01), (0.42, desk_top_z + 0.01),
            (0.42, desk_top_z + 0.06), (0.08, desk_top_z + 0.06)]
    nb.points.add(len(npts))
    for i, (x, z) in enumerate(npts):
        nb.points[i].co = (x, y_off + 0.055, z)
    nb.use_cyclic = True
    nb.material_index = 5  # Bubble material (near-white) reused for paper
    nb.line_width = 10


# ══════════════════════════════════════════════════════════════════
# Direct user spec, this round: "add a minimum of 15 poses... get back
# to me with every pose with the proper details". 9 new poses below,
# on top of the 6 already built and fixed above (STAND_TALK, WALK, RUN,
# SIT_WRITE, ALERT, SHOCK) + TWO_CHAR = 16 distinct modes total.
# ══════════════════════════════════════════════════════════════════

def pose_wait_arms_crossed(t, seed=0):
    """WAIT -- "waited, watching, stood there" narration. Still, tense,
    arms crossed -- a held, patient tension, not a walk or a talk."""
    sway = 0.025 * math.sin(t * 2 * math.pi * 0.3 + seed)
    hip = (sway * 0.3, 0.0)
    neck = (sway, 1.35)
    head_c = (sway * 1.2, 1.62)
    r_hip = (0.14, 0.02); l_hip = (-0.14, 0.02)
    r_knee = (0.155, -0.55); l_knee = (-0.145, -0.55)
    r_foot = (0.17, -1.05); l_foot = (-0.16, -1.05)
    r_sh = (0.32, 1.28); l_sh = (-0.32, 1.28)
    r_elbow = (0.10, 0.95); r_hand = (-0.22, 1.00)
    l_elbow = (-0.10, 0.90); l_hand = (0.20, 0.96)
    return {
        "hip": hip, "neck": neck, "r_hip": r_hip, "l_hip": l_hip,
        "r_knee": r_knee, "l_knee": l_knee, "r_foot": r_foot, "l_foot": l_foot,
        "r_sh": r_sh, "l_sh": l_sh, "r_elbow": r_elbow, "r_hand": r_hand,
        "l_elbow": l_elbow, "l_hand": l_hand,
    }, head_c


def pose_look_around(t, seed=0):
    """LOOK_AROUND -- "noticed, scanned, searched the room" narration.
    Head/torso turning side to side, one hand near the chin/temple."""
    turn = math.sin(t * 2 * math.pi * 0.4 + seed)
    hip = (0.0, 0.0)
    neck = (0.02 * turn, 1.35)
    head_c = (0.10 * turn, 1.62)
    r_hip = (0.14, 0.02); l_hip = (-0.14, 0.02)
    r_knee = (0.155, -0.55); l_knee = (-0.145, -0.55)
    r_foot = (0.16, -1.05); l_foot = (-0.16, -1.05)
    r_sh = (0.32, 1.28); l_sh = (-0.32, 1.28)
    r_elbow = (r_sh[0] + 0.05, r_sh[1] - 0.30)
    r_hand = (r_elbow[0] + 0.02, r_elbow[1] - 0.28)
    l_elbow = (l_sh[0] - 0.10, l_sh[1] - 0.05)
    l_hand = (head_c[0] - 0.12, head_c[1] - 0.10)  # hand raised toward the chin, thinking/scanning
    return {
        "hip": hip, "neck": neck, "r_hip": r_hip, "l_hip": l_hip,
        "r_knee": r_knee, "l_knee": l_knee, "r_foot": r_foot, "l_foot": l_foot,
        "r_sh": r_sh, "l_sh": l_sh, "r_elbow": r_elbow, "r_hand": r_hand,
        "l_elbow": l_elbow, "l_hand": l_hand,
    }, head_c


def pose_cry_grief(t, seed=0):
    """CRY_GRIEF -- "wept, broke down, mourned" narration. Hunched
    forward, both hands over the face, small shudder -- distinct from
    SHOCK (a sudden jolt) by being a settled, sustained collapse."""
    shake = 0.018 * math.sin(t * 2 * math.pi * 5 + seed)
    hunch = 0.20
    HEAD_R = 0.30
    hip = (0.0, -0.06)
    neck = (shake, 1.35 - hunch)
    head_c = (shake * 1.4, 1.53 - hunch)
    r_hip = (0.14, -0.04); l_hip = (-0.14, -0.04)
    r_knee = (0.155, -0.58); l_knee = (-0.145, -0.58)
    r_foot = (0.16, -1.05); l_foot = (-0.16, -1.05)
    r_sh = (0.30, 1.18 - hunch); l_sh = (-0.30, 1.18 - hunch)
    r_hand = (head_c[0] + HEAD_R * 0.55, head_c[1] - HEAD_R * 0.15)
    l_hand = (head_c[0] - HEAD_R * 0.55, head_c[1] - HEAD_R * 0.15)
    r_elbow = (r_sh[0] + 0.08, r_sh[1] - 0.02)
    l_elbow = (l_sh[0] - 0.08, l_sh[1] - 0.02)
    return {
        "hip": hip, "neck": neck, "r_hip": r_hip, "l_hip": l_hip,
        "r_knee": r_knee, "l_knee": l_knee, "r_foot": r_foot, "l_foot": l_foot,
        "r_sh": r_sh, "l_sh": l_sh, "r_elbow": r_elbow, "r_hand": r_hand,
        "l_elbow": l_elbow, "l_hand": l_hand,
    }, head_c


def pose_angry_confront(t, seed=0):
    """ANGRY_CONFRONT -- "confronted, accused, argued" narration. Weight
    forward, one arm jabbing/pointing accusingly, the other a clenched
    fist held tense at the side."""
    jab = max(0, math.sin(t * 2 * math.pi * 1.2 + seed))
    lean = 0.11
    hip = (lean * 0.3, 0.0); neck = (lean, 1.35); head_c = (lean * 1.2, 1.60)
    r_hip = (0.14, 0.02); l_hip = (-0.14, 0.02)
    r_knee = (0.16, -0.55); l_knee = (-0.15, -0.55)
    r_foot = (0.24, -1.05); l_foot = (-0.13, -1.02)
    r_sh = (0.32 + lean, 1.28); l_sh = (-0.32 + lean, 1.28)
    r_elbow = (r_sh[0] + 0.32, r_sh[1] - 0.04)
    r_hand = (r_elbow[0] + 0.36 + 0.10 * jab, r_elbow[1] - 0.01)
    l_elbow = (l_sh[0] - 0.08, l_sh[1] - 0.30)
    l_hand = (l_elbow[0] - 0.02, l_elbow[1] - 0.20)
    return {
        "hip": hip, "neck": neck, "r_hip": r_hip, "l_hip": l_hip,
        "r_knee": r_knee, "l_knee": l_knee, "r_foot": r_foot, "l_foot": l_foot,
        "r_sh": r_sh, "l_sh": l_sh, "r_elbow": r_elbow, "r_hand": r_hand,
        "l_elbow": l_elbow, "l_hand": l_hand,
    }, head_c


def pose_phone_call(t, seed=0):
    """PHONE_CALL -- "called, the phone rang, answered" narration. Phone
    hand held right at the ear (same ear-anchor fix as SHOCK), a slow
    pace underfoot."""
    HEAD_R = 0.30
    pace = 0.05 * math.sin(t * 2 * math.pi * 0.3 + seed)
    hip = (pace, 0.0); neck = (pace * 0.6, 1.35); head_c = (pace * 0.5 + 0.06, 1.62)
    r_hip = (0.14, 0.02); l_hip = (-0.14, 0.02)
    r_knee = (0.155, -0.55); l_knee = (-0.145, -0.55)
    r_foot = (0.16 + pace, -1.05); l_foot = (-0.16 + pace, -1.05)
    r_sh = (0.32, 1.28); l_sh = (-0.32, 1.28)
    r_hand = (head_c[0] + HEAD_R * 0.85, head_c[1] + HEAD_R * 0.10)
    r_elbow = (r_sh[0] + 0.14, r_sh[1] + 0.08)
    l_elbow = (l_sh[0] - 0.10, l_sh[1] - 0.30)
    l_hand = (l_elbow[0] - 0.05, l_elbow[1] - 0.28)
    return {
        "hip": hip, "neck": neck, "r_hip": r_hip, "l_hip": l_hip,
        "r_knee": r_knee, "l_knee": l_knee, "r_foot": r_foot, "l_foot": l_foot,
        "r_sh": r_sh, "l_sh": l_sh, "r_elbow": r_elbow, "r_hand": r_hand,
        "l_elbow": l_elbow, "l_hand": l_hand,
    }, head_c


def pose_collapse_kneel(t, seed=0):
    """COLLAPSE_KNEEL -- "collapsed, broke down, fell to her knees"
    narration. Sinks down over the first half of the clip then holds --
    a real bent-knee kneel via draw_bent_leg, one leg tucked under."""
    sink = min(1.0, t * 2.2)
    drop = 0.55 * sink
    hip = (0.0, -drop); neck = (0.02, 1.18 - drop); head_c = (0.03, 1.36 - drop - 0.08 * sink)
    r_hip = (0.14, -drop + 0.02); l_hip = (-0.14, -drop + 0.02)
    r_knee = (0.20, -drop - 0.30 * sink); l_knee = (-0.19, -drop - 0.30 * sink)
    r_foot = (0.14, -1.05)
    l_foot = (-0.30, -0.95 + 0.28 * sink)  # tucks under as the sink completes
    r_sh = (0.28, 1.08 - drop); l_sh = (-0.28, 1.08 - drop)
    r_elbow = (r_sh[0] + 0.02, r_sh[1] - 0.24)
    r_hand = (head_c[0] + 0.10, head_c[1] - 0.08)
    l_elbow = (l_sh[0] - 0.02, l_sh[1] - 0.24)
    l_hand = (head_c[0] - 0.10, head_c[1] - 0.08)
    return {
        "hip": hip, "neck": neck, "r_hip": r_hip, "l_hip": l_hip,
        "r_knee": r_knee, "l_knee": l_knee, "r_foot": r_foot, "l_foot": l_foot,
        "r_sh": r_sh, "l_sh": l_sh, "r_elbow": r_elbow, "r_hand": r_hand,
        "l_elbow": l_elbow, "l_hand": l_hand,
    }, head_c


def pose_cower_defense(t, seed=0):
    """COWER_DEFENSE -- "cowered, flinched, shielded herself" narration.
    Crouched low, both arms raised protectively over the head."""
    HEAD_R = 0.30
    tremor = 0.02 * math.sin(t * 2 * math.pi * 7 + seed)
    crouch = 0.30
    hip = (tremor, -crouch); neck = (tremor * 1.3, 1.12 - crouch); head_c = (tremor * 1.5, 1.28 - crouch)
    r_hip = (0.14, -crouch + 0.02); l_hip = (-0.14, -crouch + 0.02)
    r_knee = (0.20, -crouch - 0.35); l_knee = (-0.19, -crouch - 0.35)
    r_foot = (0.18, -1.05); l_foot = (-0.17, -1.05)
    r_sh = (0.28, 1.02 - crouch); l_sh = (-0.28, 1.02 - crouch)
    r_elbow = (head_c[0] + HEAD_R * 0.7, head_c[1] + HEAD_R * 0.6)
    r_hand = (head_c[0] + HEAD_R * 0.3, head_c[1] + HEAD_R * 1.05)
    l_elbow = (head_c[0] - HEAD_R * 0.7, head_c[1] + HEAD_R * 0.6)
    l_hand = (head_c[0] - HEAD_R * 0.3, head_c[1] + HEAD_R * 1.05)
    return {
        "hip": hip, "neck": neck, "r_hip": r_hip, "l_hip": l_hip,
        "r_knee": r_knee, "l_knee": l_knee, "r_foot": r_foot, "l_foot": l_foot,
        "r_sh": r_sh, "l_sh": l_sh, "r_elbow": r_elbow, "r_hand": r_hand,
        "l_elbow": l_elbow, "l_hand": l_hand,
    }, head_c


def pose_knock_door(t, seed=0):
    """KNOCK_DOOR -- "knocked, opened the door, entered" narration. Fist
    rapping forward/down in a real repeated knocking motion."""
    knock = max(0, math.sin(t * 2 * math.pi * 2.4 + seed))
    hip = (0.0, 0.0); neck = (0.02, 1.35); head_c = (0.03, 1.62)
    r_hip = (0.14, 0.02); l_hip = (-0.14, 0.02)
    r_knee = (0.155, -0.55); l_knee = (-0.145, -0.55)
    r_foot = (0.16, -1.05); l_foot = (-0.16, -1.05)
    r_sh = (0.32, 1.28); l_sh = (-0.32, 1.28)
    r_elbow = (r_sh[0] + 0.28, r_sh[1] - 0.05)
    r_hand = (r_elbow[0] + 0.20, r_elbow[1] - 0.02 - 0.12 * knock)
    l_elbow = (l_sh[0] - 0.08, l_sh[1] - 0.30)
    l_hand = (l_elbow[0] - 0.05, l_elbow[1] - 0.28)
    return {
        "hip": hip, "neck": neck, "r_hip": r_hip, "l_hip": l_hip,
        "r_knee": r_knee, "l_knee": l_knee, "r_foot": r_foot, "l_foot": l_foot,
        "r_sh": r_sh, "l_sh": l_sh, "r_elbow": r_elbow, "r_hand": r_hand,
        "l_elbow": l_elbow, "l_hand": l_hand,
    }, head_c


def pose_search_rummage(t, seed=0):
    """SEARCH_RUMMAGE -- "searched, rummaged, dug through the drawer"
    narration. Bent forward at the waist, both hands digging with a
    real back-and-forth motion."""
    dig = math.sin(t * 2 * math.pi * 1.6 + seed)
    bend = 0.35
    hip = (0.0, -0.05); neck = (0.0, 1.05 - bend); head_c = (0.02, 1.20 - bend)
    r_hip = (0.14, -0.03); l_hip = (-0.14, -0.03)
    r_knee = (0.155, -0.56); l_knee = (-0.145, -0.56)
    r_foot = (0.18, -1.05); l_foot = (-0.18, -1.05)
    r_sh = (0.30, 0.98 - bend); l_sh = (-0.30, 0.98 - bend)
    r_elbow = (0.35, 0.55 - bend); r_hand = (0.30 + 0.10 * dig, 0.20 - bend)
    l_elbow = (-0.35, 0.55 - bend); l_hand = (-0.30 - 0.10 * dig, 0.20 - bend)
    return {
        "hip": hip, "neck": neck, "r_hip": r_hip, "l_hip": l_hip,
        "r_knee": r_knee, "l_knee": l_knee, "r_foot": r_foot, "l_foot": l_foot,
        "r_sh": r_sh, "l_sh": l_sh, "r_elbow": r_elbow, "r_hand": r_hand,
        "l_elbow": l_elbow, "l_hand": l_hand,
    }, head_c


def pose_happy(t, seed=0):
    """HAPPY -- direct user spec ("if it's happy, turns something else"):
    a real lighter, buoyant stance -- weight bounces on the toes, both
    arms swing loosely, head tilts slightly. Paired with the warm skin
    tint in the dispatch table below."""
    bounce = abs(math.sin(t * 2 * math.pi * 1.1 + seed))
    hip = (0.0, bounce * 0.05); neck = (0.03, 1.35 + bounce * 0.03); head_c = (0.05, 1.63 + bounce * 0.03)
    r_hip = (0.14, bounce * 0.05); l_hip = (-0.14, bounce * 0.05)
    r_knee = (0.155, -0.55 + bounce * 0.03); l_knee = (-0.145, -0.55 + bounce * 0.03)
    r_foot = (0.17, -1.05); l_foot = (-0.16, -1.05)
    r_sh = (0.32, 1.28 + bounce * 0.03); l_sh = (-0.32, 1.28 + bounce * 0.03)
    swing = math.sin(t * 2 * math.pi * 1.1 + seed)
    r_elbow = (r_sh[0] + 0.16, r_sh[1] - 0.10 + 0.10 * swing)
    r_hand = (r_elbow[0] + 0.14, r_elbow[1] - 0.05 + 0.14 * swing)
    l_elbow = (l_sh[0] - 0.16, l_sh[1] - 0.10 - 0.10 * swing)
    l_hand = (l_elbow[0] - 0.14, l_elbow[1] - 0.05 - 0.14 * swing)
    return {
        "hip": hip, "neck": neck, "r_hip": r_hip, "l_hip": l_hip,
        "r_knee": r_knee, "l_knee": l_knee, "r_foot": r_foot, "l_foot": l_foot,
        "r_sh": r_sh, "l_sh": l_sh, "r_elbow": r_elbow, "r_hand": r_hand,
        "l_elbow": l_elbow, "l_hand": l_hand,
    }, head_c


def pose_dance(t, seed=0):
    """DANCE -- direct user example of an expected natural pose ("sitting,
    standing, walking, or dancing"). A rhythmic side-to-side sway with
    both arms raised and swinging opposite the hips, on a real 2-beat
    cycle (not a walk cycle), feet stepping side to side in place."""
    beat = t * 2 * math.pi * 1.8 + seed
    sway = 0.10 * math.sin(beat)
    bob = 0.04 * abs(math.sin(beat))
    hip = (sway, bob); neck = (sway * 0.6, 1.35 + bob * 0.5); head_c = (sway * 0.4, 1.62 + bob * 0.5)
    step = 0.06 * math.sin(beat)
    r_hip = (0.14 + sway, bob * 0.3); l_hip = (-0.14 + sway, bob * 0.3)
    r_knee = (0.155 + sway, -0.55); l_knee = (-0.145 + sway, -0.55)
    r_foot = (0.17 + step, -1.05); l_foot = (-0.16 - step, -1.05)
    r_sh = (0.32 + sway * 0.6, 1.28 + bob * 0.5); l_sh = (-0.32 + sway * 0.6, 1.28 + bob * 0.5)
    arm_swing = math.sin(beat + math.pi)
    r_elbow = (r_sh[0] + 0.15, r_sh[1] + 0.20 + 0.12 * arm_swing)
    r_hand = (r_elbow[0] + 0.10, r_elbow[1] + 0.25 + 0.14 * arm_swing)
    l_elbow = (l_sh[0] - 0.15, l_sh[1] + 0.20 - 0.12 * arm_swing)
    l_hand = (l_elbow[0] - 0.10, l_elbow[1] + 0.25 - 0.14 * arm_swing)
    return {
        "hip": hip, "neck": neck, "r_hip": r_hip, "l_hip": l_hip,
        "r_knee": r_knee, "l_knee": l_knee, "r_foot": r_foot, "l_foot": l_foot,
        "r_sh": r_sh, "l_sh": l_sh, "r_elbow": r_elbow, "r_hand": r_hand,
        "l_elbow": l_elbow, "l_hand": l_hand,
    }, head_c


def speech_bubble(frame, anchor, text_w, side=1, y_off=0.02):
    """A rounded speech-bubble shape with a small pointer tail toward the
    speaking character -- the 'cloud pops up and tells something' device.

    FIX: the tail used to be spliced in at a fixed fractional index that
    didn't necessarily line up with the point closest to the character,
    so the tail's "out and back" edges crossed clean across the ellipse
    interior -- a self-intersecting polygon that rendered as a visible
    X/crossing line through the bubble. Now the insertion point is the
    ellipse vertex whose own angle is closest to the true direction from
    the bubble center to the character's head, so the tail only ever
    pokes out locally from the nearest edge -- no crossing."""
    cx = anchor[0] + side * 0.55
    cz = anchor[1] + 0.35
    w, h = 0.9, 0.5
    n = 20
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        pts.append((cx + (w / 2) * math.cos(a), cz + (h / 2) * math.sin(a)))
    dir_angle = math.atan2(anchor[1] - cz, anchor[0] - cx)
    best_idx = min(range(n), key=lambda i: abs(((2 * math.pi * i / n) - dir_angle + math.pi) % (2 * math.pi) - math.pi))
    pts.insert(best_idx + 1, (anchor[0] + side * 0.1, anchor[1] + 0.08))
    s = frame.strokes.new()
    s.points.add(len(pts))
    for i, (x, z) in enumerate(pts):
        s.points[i].co = (x, y_off, z)
    s.use_cyclic = True
    s.material_index = 5
    s.line_width = 10
    return (cx, cz)


# Data-driven single-character pose dispatch -- 15 distinct poses (direct
# user spec: "add a minimum of 15 poses... get back to me with every pose
# with the proper details"), plus TWO_CHAR (conversation) handled below.
SINGLE_POSE_FUNCS = {
    "ONE_CHAR":       lambda t: pose_stand_talk(t, gesture_phase=t * 4 * math.pi, seed=0),
    "WALK":           lambda t: pose_walk_run(t, running=False, seed=0),
    "RUN":            lambda t: pose_walk_run(t, running=True, seed=0),
    "SIT_WRITE":      lambda t: pose_sit_write(t, seed=0),
    "ALERT":          lambda t: pose_alert(t, seed=0),
    "SHOCK":          lambda t: pose_shock(t, seed=0),
    "WAIT":           lambda t: pose_wait_arms_crossed(t, seed=0),
    "LOOK_AROUND":    lambda t: pose_look_around(t, seed=0),
    "CRY_GRIEF":      lambda t: pose_cry_grief(t, seed=0),
    "ANGRY_CONFRONT": lambda t: pose_angry_confront(t, seed=0),
    "PHONE_CALL":     lambda t: pose_phone_call(t, seed=0),
    "COLLAPSE_KNEEL": lambda t: pose_collapse_kneel(t, seed=0),
    "COWER_DEFENSE":  lambda t: pose_cower_defense(t, seed=0),
    "KNOCK_DOOR":     lambda t: pose_knock_door(t, seed=0),
    "SEARCH_RUMMAGE": lambda t: pose_search_rummage(t, seed=0),
    "HAPPY":          lambda t: pose_happy(t, seed=0),
    "DANCE":          lambda t: pose_dance(t, seed=0),
}

# Direct user spec: "if it is angry, the face turns red... if happy,
# turns something else" -- real per-pose emotional skin tint, not one
# flat tone regardless of story content.
POSE_EMOTION = {
    "ANGRY_CONFRONT": "angry",
    "SHOCK": "pale",
    "COWER_DEFENSE": "pale",
    "HAPPY": "warm",
    "DANCE": "warm",
}

_frac_args = [a for a in argv[2:] if a != "--still"]
STILL_FRAC = float(_frac_args[0]) if SINGLE_FRAME and _frac_args else 0.5
RENDER_FRAMES = [int(N_FRAMES * STILL_FRAC)] if SINGLE_FRAME else list(range(N_FRAMES))
if SINGLE_FRAME:
    scene.frame_end = 1

for out_f, f in enumerate(RENDER_FRAMES):
    gp_frame = layer.frames.new(out_f + 1)
    t = f / N_FRAMES

    if MODE in SINGLE_POSE_FUNCS:
        segs, head_c = SINGLE_POSE_FUNCS[MODE](t)
        if MODE == "SIT_WRITE":
            draw_chair_back(gp_frame, y_off=0.0)
        build_character(gp_frame, 0.0, segs, head_c, 0.30, 1, 3, 0.0, face_dir=1,
                         emotion=POSE_EMOTION.get(MODE, "neutral"),
                         profile_dir=(WALK_FACE_DIR if MODE in ("WALK", "RUN") else 0))
        if MODE == "SIT_WRITE":
            draw_desk(gp_frame, y_off=0.0)
    else:
        # Two characters, one speaking at a time (alternating every ~2.5s),
        # speech bubble over whichever is "active".
        speaker = "A" if (t * DURATION_S) % 5.0 < 2.5 else "B"
        segsA, headA = pose_stand_talk(t, gesture_phase=(t * 4 * math.pi if speaker == "A" else 0.3), seed=0)
        segsB, headB = pose_stand_talk(t, gesture_phase=(t * 4 * math.pi if speaker == "B" else 0.3), seed=1.7)
        # shift into two positions
        offA, offB = -1.15, 1.15
        def shift(segs, dx):
            return {k: (v[0] + dx, v[1]) for k, v in segs.items()}
        segsA = shift(segsA, offA)
        segsB = shift(segsB, offB)
        headA = (headA[0] + offA, headA[1])
        headB = (headB[0] + offB, headB[1])
        build_character(gp_frame, offA, segsA, headA, 0.28, 2, 4, 0.05, face_dir=1)
        build_character(gp_frame, offB, segsB, headB, 0.28, 1, 3, -0.05, face_dir=-1)
        active_head = headA if speaker == "A" else headB
        active_side = 1 if speaker == "A" else -1
        speech_bubble(gp_frame, (active_head[0], active_head[1] + 0.30), 0.8, side=active_side,
                       y_off=(0.06 if speaker == "A" else -0.06))

# PNG sequence with alpha (not direct-to-video) -- the character frames
# get composited over a separately-generated, panning Pillow background
# afterward, so the alpha channel here has to survive.
import os
os.makedirs(OUT, exist_ok=True)
scene.render.filepath = os.path.join(OUT, "ch_")
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
import time
t0 = time.time()
bpy.ops.render.render(animation=True)
print(f"SAMPLE_V3_RENDER_OK in {time.time()-t0:.1f}s -> {OUT}")
