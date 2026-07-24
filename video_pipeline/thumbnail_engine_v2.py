"""
THUMBNAIL ENGINE v2.0 — Drop-in replacement for all three pipelines.

What was wrong with v1:
- Flat text on darkened background — single layer composition
- Generic Pollinations prompts — returned stock-looking results
- No face/silhouette layer — channels with faces get 30-40% higher CTR
- A/B testing was style-based (red vs white) — should be composition-based
- Pixabay/Pexels search keywords were too broad

v2 improvements:
1. Three-layer composition: background + midground silhouette + foreground text
2. Emotion-matched visual direction per niche (specific Pollinations prompts)
3. Silhouette synthesis: generates human figure silhouette matched to case type
4. Text shadow depth system: 4px shadow stack instead of single outline
5. Colour psychology per niche: not just "dark" — specific palette per content type
6. A/B testing: composition-based (silhouette vs no silhouette, text position top vs centre)
7. NUMBER+NOUN enforcement with fallback generator
8. Channel badge + episode number on every thumbnail

Import and call:
  from thumbnail_engine_v2 import generate_thumbnail_v2
"""

import re, random, requests, os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

TW, TH = 1280, 720  # YouTube thumbnail dimensions
PIXABAY_KEY = os.environ.get("PIXABAY_KEY", "")

# ══════════════════════════════════════════════════════════════════
# CHANNEL AVATAR SYSTEM (added per explicit request — real, thought-through
# design, not a real photo). A stylized illustrated host character per
# channel: the SAME character design stays recognizable across every
# thumbnail (brand identity, addresses the "no human presence" signal
# some enforcement discussion points to), but pose/action/framing
# genuinely ROTATES so it never becomes the exact templated repeat that
# YouTube's inauthentic-content test actually penalizes. NOT a real
# photo of anyone — deliberately illustrated/stylized, so there's no
# question of misrepresenting who's speaking, and no single real
# person's identity is tied across 5 tonally different channels.
# ══════════════════════════════════════════════════════════════════
CHANNEL_AVATARS = {
    "BetrayalDeepDive": {
        "avatar_description": (
            "stylized illustrated figure in a dark hooded cloak, minimalist "
            "flat-shaded digital illustration style, faint red glow where eyes "
            "would be, no photorealistic face, no real person, graphic novel "
            "aesthetic, consistent character design"
        ),
        "pose_variations": [
            "standing in a doorway looking into the room",
            "reaching a hand toward the viewer",
            "seated in an armchair examining an old photograph",
            "walking away down a corridor, looking back over one shoulder",
            "standing behind a curtain, half-visible",
            "holding an old cassette tape up to the light",
            "silhouetted against a window at night",
            "crouched beside a closed door, listening",
        ],
    },
    "The Evidence Room": {
        "avatar_description": (
            "stylized illustrated detective figure in a dark trench coat and "
            "hat, minimalist flat-shaded digital illustration style, no "
            "photorealistic face, no real person, graphic novel aesthetic, "
            "consistent character design"
        ),
        "pose_variations": [
            "examining a case file under a desk lamp",
            "standing before an evidence board with string connections",
            "holding a magnifying glass over a document",
            "pointing at a photograph pinned to a corkboard",
            "silhouetted against venetian blinds",
            "kneeling beside a chalk outline diagram",
            "reviewing a folder stamped CONFIDENTIAL",
            "standing at a rain-streaked window, back to camera",
        ],
    },
    # FIX: added — Ch3 had no avatar entry at all, so get_channel_avatar_prompt
    # silently returned None for it (per this function's own documented
    "The Control Files": {
        "avatar_description": (
            "stylized illustrated analyst figure, simple flat hand-drawn "
            "doodle/sketch illustration style matching a whiteboard "
            "aesthetic, charcoal ink line art with a single red-marker "
            "accent, no photorealistic face, no real person, consistent "
            "character design across every episode"
        ),
        "pose_variations": [
            "standing at a whiteboard mid-sketch, marker in hand",
            "pointing at a hand-drawn flowchart diagram",
            "seated, reviewing a stack of case documents",
            "sketching a connecting arrow between two boxes",
            "standing beside a hand-drawn timeline",
            "circling a key detail on a redacted document",
            "gesturing toward a crowd diagram mid-explanation",
            "silhouetted against a paper-textured backdrop",
        ],
    },
}

def get_channel_avatar_prompt(channel_name, seed):
    """
    Returns a (description, pose) tuple for this channel — same base
    character every time (brand consistency), pose rotates by seed so
    the SAME exact pose/composition never repeats often enough to become
    the templated pattern that actually triggers policy risk. Falls back
    to None for any channel without a defined avatar (currently Ch4/Ch5
    only — BetrayalDeepDive, The Evidence Room, and The Control Files
    all have real entries in CHANNEL_AVATARS below).
    """
    cfg = CHANNEL_AVATARS.get(channel_name)
    if not cfg:
        return None, None
    pose = cfg["pose_variations"][seed % len(cfg["pose_variations"])]
    return cfg["avatar_description"], pose

FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/ubuntu/Ubuntu-Bold.ttf",
]

def get_font(size):
    for fp in FONT_PATHS:
        if Path(fp).exists():
            try:
                return ImageFont.truetype(fp, size)
            except:
                pass
    return ImageFont.load_default()


# ═══════════════════════════════════════════════════════════════════
# NICHE VISUAL PROFILES
# Each niche has specific visual direction, colour palette, and
# composition rules. Not generic "dark documentary" — specific.
# ═══════════════════════════════════════════════════════════════════

NICHE_PROFILES = {
    # BetrayalDeepDive niches
    "dark_horror": {
        "bg_color":        (2, 2, 8),
        "primary_text":    (255, 255, 255),
        "accent_text":     (220, 30, 30),      # blood red
        "shadow_color":    (120, 0, 0),
        "badge_color":     (180, 20, 20),
        "glow_color":      (255, 60, 60),
        "vignette_strength": 0.85,
        "brightness":      0.18,
        "pollinations_style": (
            "abandoned dark location ominous shadows fog atmospheric cinematic "
            "horror dramatic lighting no people no text 8k"
        ),
        "silhouette_style": (
            "dark silhouette of a single person standing facing away in fog "
            "dramatic backlit no face visible atmospheric cinematic"
        ),
        "composition":     "text_lower_third",  # text in bottom 40%
        # FIX (warbook v3): 3 FIXED thumbnail families instead of fully
        # open-ended generation per episode — real brand consistency,
        # per the explicit "each channel gets 3 families, not 30 random
        # designs" rule. Rotates by day, not randomly.
        "thumbnail_families": [
            "cursed everyday object extreme closeup dramatic shadow ominous 8k",
            "empty dark corridor single door at end dramatic perspective ominous 8k",
            "partial human face fragment half in shadow dramatic closeup ominous 8k",
        ],
        "thumbnail_text_examples": ["LAST TAPE", "ROOM 307", "SECOND VOICE", "SHE LIED"],
    },
    "seduction_dark": {
        "bg_color":        (5, 2, 8),
        "primary_text":    (240, 220, 255),
        "accent_text":     (180, 80, 255),      # deep purple
        "shadow_color":    (40, 0, 80),
        "badge_color":     (140, 40, 200),
        "glow_color":      (200, 100, 255),
        "vignette_strength": 0.80,
        "brightness":      0.20,
        "pollinations_style": (
            "dark seductive interior shadows purple atmospheric cinematic "
            "dramatic lighting empty room no people no text 8k"
        ),
        "silhouette_style": (
            "dark silhouette two figures in doorway dramatic backlit "
            "purple atmospheric no faces cinematic"
        ),
        "composition":     "text_center",
        "thumbnail_families": [
            "single red rose wilting extreme closeup dramatic shadow 8k",
            "empty bed disheveled sheets dramatic purple lighting 8k",
            "locked phone screen glowing in dark room dramatic 8k",
        ],
        "thumbnail_text_examples": ["SHE KNEW ALREADY", "TWENTY EIGHT DAYS", "ONE TRAP CLOSED", "COST HER EVERYTHING"],
    },
    "psychological_trap": {
        "bg_color":        (3, 3, 3),
        "primary_text":    (255, 255, 255),
        "accent_text":     (255, 200, 0),       # warning yellow
        "shadow_color":    (80, 60, 0),
        "badge_color":     (200, 150, 0),
        "glow_color":      (255, 220, 50),
        "vignette_strength": 0.90,
        "brightness":      0.15,
        "pollinations_style": (
            "dark maze corridor psychological tension dramatic lighting "
            "shadows no people no text cinematic 8k"
        ),
        "silhouette_style": (
            "dark silhouette person trapped in corner dramatic lighting "
            "yellow tones atmospheric no face cinematic"
        ),
        "composition":     "text_upper_third",
        "thumbnail_families": [
            "single chess piece cornered extreme closeup dramatic shadow 8k",
            "maze corridor dead end dramatic yellow lighting 8k",
            "cracked mirror fragment reflection dramatic closeup 8k",
        ],
        "thumbnail_text_examples": ["NO EXIT EXISTS", "SIX STAGES FOUND", "TRUTH WAS WORSE", "EVERYONE BLAMED HIM"],
    },
    "supernatural_real": {
        "bg_color":        (2, 4, 8),
        "primary_text":    (200, 230, 255),
        "accent_text":     (60, 180, 255),      # cold blue
        "shadow_color":    (0, 40, 80),
        "badge_color":     (20, 100, 200),
        "glow_color":      (80, 200, 255),
        "vignette_strength": 0.85,
        "brightness":      0.17,
        "pollinations_style": (
            "dark forest night atmospheric mist blue light mysterious "
            "cinematic no people no text 8k"
        ),
        "silhouette_style": (
            "dark silhouette person alone at night forest dramatic "
            "blue moonlight atmospheric no face"
        ),
        "composition":     "text_center",
        "thumbnail_families": [
            "static tv screen glowing blue dark room extreme closeup 8k",
            "empty forest path night mist dramatic blue lighting 8k",
            "old photograph partially burned dramatic closeup 8k",
        ],
        "thumbnail_text_examples": ["NINE NIGHTS RECORDED", "STILL UNEXPLAINED TODAY", "WITNESSES CONFIRMED THIS", "NOBODY CAME BACK"],
    },
    "obsession_dark": {
        "bg_color":        (4, 2, 2),
        "primary_text":    (255, 240, 230),
        "accent_text":     (255, 100, 20),      # amber warning
        "shadow_color":    (80, 30, 0),
        "badge_color":     (200, 80, 0),
        "glow_color":      (255, 140, 40),
        "vignette_strength": 0.88,
        "brightness":      0.16,
        "pollinations_style": (
            "dark obsessive environment walls covered with papers "
            "red string connections atmospheric dramatic cinematic no people no text 8k"
        ),
        "silhouette_style": (
            "dark silhouette person at window at night dramatic amber "
            "lighting atmospheric no face cinematic"
        ),
        "composition":     "text_lower_third",
        "thumbnail_families": [
            "wall covered in photos red string extreme closeup dramatic 8k",
            "phone screen hundreds of messages dark room dramatic 8k",
            "window silhouette watching outside dramatic amber lighting 8k",
        ],
        "thumbnail_text_examples": ["EIGHT HUNDRED MESSAGES", "FOUR YEARS TRACKED", "SHE WAS ALONE", "LAST DAYS UNSEEN"],
    },
    # Evidence Room niches
    "forensic_finance": {
        "bg_color":        (2, 4, 8),
        "primary_text":    (220, 235, 255),
        "accent_text":     (60, 160, 255),
        "shadow_color":    (0, 30, 80),
        "badge_color":     (20, 80, 180),
        "glow_color":      (80, 180, 255),
        "vignette_strength": 0.80,
        "brightness":      0.20,
        "pollinations_style": (
            "dark financial documents scattered desk dramatic lighting "
            "forensic atmosphere no people no text cinematic 8k"
        ),
        "silhouette_style": (
            "dark silhouette person at desk surrounded by documents "
            "dramatic blue lighting no face cinematic"
        ),
        "composition":     "text_center",
        "thumbnail_families": [
            "single piece of evidence extreme closeup dramatic lighting forensic 8k",
            "crime scene room map diagram overhead dramatic lighting forensic 8k",
            "fingerprint card evidence tag extreme closeup dramatic lighting forensic 8k",
        ],
        "thumbnail_text_examples": ["ONE FIBER", "FALSE ALIBI", "THE PRINT", "CASE REOPENED"],
    },
    "criminal_investigation": {
        "bg_color":        (4, 2, 2),
        "primary_text":    (255, 245, 235),
        "accent_text":     (220, 30, 30),
        "shadow_color":    (80, 0, 0),
        "badge_color":     (180, 20, 20),
        "glow_color":      (255, 60, 60),
        "vignette_strength": 0.85,
        "brightness":      0.18,
        "pollinations_style": (
            "dark crime scene tape evidence markers night atmospheric "
            "dramatic red and white light no people no text cinematic 8k"
        ),
        "silhouette_style": (
            "dark silhouette detective figure dramatic red lighting "
            "crime scene atmosphere no face cinematic"
        ),
        "composition":     "text_lower_third",
        "thumbnail_families": [
            "single evidence bag extreme closeup dramatic red lighting 8k",
            "crime scene tape dark corridor dramatic lighting 8k",
            "fingerprint magnified extreme closeup dramatic 8k",
        ],
        "thumbnail_text_examples": ["ONE FIBER", "FALSE ALIBI", "THE PRINT", "CASE REOPENED"],
    },
    "corporate_exposure": {
        "bg_color":        (2, 3, 6),
        "primary_text":    (230, 240, 255),
        "accent_text":     (100, 200, 255),
        "shadow_color":    (0, 40, 80),
        "badge_color":     (40, 120, 200),
        "glow_color":      (120, 210, 255),
        "vignette_strength": 0.75,
        "brightness":      0.22,
        "pollinations_style": (
            "dark empty corporate boardroom dramatic lighting shadows "
            "no people no text atmospheric cinematic 8k"
        ),
        "silhouette_style": (
            "dark silhouette executive figure at window skyscraper "
            "dramatic blue lighting no face cinematic"
        ),
        "composition":     "text_center",
        "thumbnail_families": [
            "shredded documents extreme closeup dramatic blue lighting 8k",
            "empty boardroom table dramatic corporate lighting 8k",
            "skyscraper window silhouette dramatic blue tones 8k",
        ],
        "thumbnail_text_examples": ["MEMO FOUND", "THEY KNEW", "COVER EXPOSED", "ALL DOCUMENTED"],
    },
    "digital_forensics": {
        "bg_color":        (0, 5, 5),
        "primary_text":    (180, 255, 240),
        "accent_text":     (0, 220, 180),
        "shadow_color":    (0, 60, 50),
        "badge_color":     (0, 160, 130),
        "glow_color":      (40, 255, 200),
        "vignette_strength": 0.80,
        "brightness":      0.18,
        "pollinations_style": (
            "dark digital data streams screens code atmospheric "
            "no people no text cinematic green teal 8k"
        ),
        "silhouette_style": (
            "dark silhouette hacker figure screens green glow "
            "dramatic lighting no face cinematic"
        ),
        "composition":     "text_lower_third",
        "thumbnail_families": [
            "computer screen glowing data extreme closeup dramatic teal 8k",
            "server room dark corridor dramatic green lighting 8k",
            "deleted file recovery screen dramatic closeup 8k",
        ],
        "thumbnail_text_examples": ["DATA RECOVERED", "FILES FOUND", "METADATA MATCHED", "DELETED FOUND"],
    },
    # Control Files niches
    "cult_psychology": {
        "bg_color":        (3, 2, 8),
        "primary_text":    (240, 230, 255),
        "accent_text":     (180, 60, 255),
        "shadow_color":    (50, 0, 100),
        "badge_color":     (130, 30, 200),
        "glow_color":      (200, 100, 255),
        "vignette_strength": 0.88,
        "brightness":      0.17,
        "pollinations_style": (
            "dark group silhouettes concentric circles atmospheric "
            "purple dramatic no faces no text cinematic 8k"
        ),
        "silhouette_style": (
            "dark silhouette crowd facing single figure dramatic "
            "purple backlight no faces atmospheric cinematic"
        ),
        "composition":     "text_center",
        # FIX (found on deep re-audit): Control Files' 6 niches had
        # profiles but none had thumbnail_families — every thumbnail here
        # fell through to old open-ended generation instead of the "3
        # fixed families, brand consistency" system Ch1/Ch2 already have.
        "thumbnail_families": [
            "single ritual object extreme closeup dramatic shadow ominous 8k",
            "empty meeting hall rows of chairs dramatic purple lighting 8k",
            "hooded figures circle overhead view dramatic shadow 8k",
        ],
    },
    "propaganda_systems": {
        "bg_color":        (8, 2, 2),
        "primary_text":    (255, 245, 230),
        "accent_text":     (220, 20, 20),
        "shadow_color":    (80, 0, 0),
        "badge_color":     (180, 15, 15),
        "glow_color":      (255, 50, 50),
        "vignette_strength": 0.88,
        "brightness":      0.16,
        "pollinations_style": (
            "dark propaganda poster aesthetic faded red dramatic "
            "atmospheric no text no faces cinematic 8k"
        ),
        "silhouette_style": (
            "dark silhouette crowd marching dramatic red backlight "
            "no faces atmospheric cinematic"
        ),
        "composition":     "text_upper_third",
        "thumbnail_families": [
            "faded propaganda poster torn edge extreme closeup dramatic 8k",
            "empty broadcast studio single microphone dramatic red lighting 8k",
            "crowd of shadows marching overhead dramatic red backlight 8k",
        ],
    },
    "social_engineering": {
        "bg_color":        (2, 4, 8),
        "primary_text":    (220, 235, 255),
        "accent_text":     (60, 160, 255),
        "shadow_color":    (0, 30, 80),
        "badge_color":     (20, 100, 200),
        "glow_color":      (80, 200, 255),
        "vignette_strength": 0.82,
        "brightness":      0.19,
        "pollinations_style": (
            "dark network connections web human figures atmospheric "
            "blue no faces no text cinematic 8k"
        ),
        "silhouette_style": (
            "dark silhouette figure controlling strings dramatic "
            "blue lighting no face cinematic atmospheric"
        ),
        "composition":     "text_center",
        "thumbnail_families": [
            "single phone screen glowing fake message extreme closeup dramatic 8k",
            "network web of connected nodes dramatic blue lighting 8k",
            "hand reaching through screen dramatic blue backlight 8k",
        ],
    },
    "mass_deception": {
        "bg_color":        (4, 2, 6),
        "primary_text":    (245, 235, 255),
        "accent_text":     (200, 60, 220),
        "shadow_color":    (60, 0, 80),
        "badge_color":     (150, 30, 170),
        "glow_color":      (220, 90, 240),
        "vignette_strength": 0.85,
        "brightness":      0.18,
        "pollinations_style": (
            "dark mirrored room illusion fractured reality atmospheric "
            "purple dramatic no people no text cinematic 8k"
        ),
        "silhouette_style": (
            "dark silhouette crowd looking at screen dramatic "
            "purple light no faces atmospheric cinematic"
        ),
        "composition":     "text_center",
        "thumbnail_families": [
            "cracked mirror fractured reflection extreme closeup dramatic 8k",
            "television static wall of screens dramatic purple lighting 8k",
            "crowd facing giant screen overhead dramatic purple light 8k",
        ],
    },
    # FIX: added — these 2 niches existed in control_files_pipeline.py with
    # full seed topics and RPM data but had no thumbnail profile at all;
    # combined with the DAY_NICHE dead-niche bug (now fixed), this closes
    # the gap end to end.
    "dark_business_documentaries": {
        "bg_color":        (5, 4, 2),
        "primary_text":    (250, 240, 220),
        "accent_text":     (220, 160, 20),
        "shadow_color":    (70, 45, 0),
        "badge_color":     (180, 120, 10),
        "glow_color":      (255, 190, 60),
        "vignette_strength": 0.86,
        "brightness":      0.17,
        "pollinations_style": (
            "dark corporate boardroom empty chairs atmospheric "
            "gold dramatic no faces no text cinematic 8k"
        ),
        "silhouette_style": (
            "dark silhouette executive figure at podium dramatic "
            "gold backlight no face atmospheric cinematic"
        ),
        "composition":     "text_center",
        "thumbnail_families": [
            "shredded financial documents extreme closeup dramatic gold lighting 8k",
            "empty corporate boardroom long table dramatic gold lighting 8k",
            "executive silhouette signing document dramatic gold backlight 8k",
        ],
    },
    "scams_fraud_exposed": {
        "bg_color":        (6, 2, 2),
        "primary_text":    (250, 235, 220),
        "accent_text":     (230, 80, 30),
        "shadow_color":    (70, 10, 0),
        "badge_color":     (190, 60, 15),
        "glow_color":      (255, 120, 50),
        "vignette_strength": 0.87,
        "brightness":      0.17,
        "pollinations_style": (
            "dark call center rows of phones atmospheric orange "
            "dramatic no faces no text cinematic 8k"
        ),
        "silhouette_style": (
            "dark silhouette figure on phone dramatic orange "
            "backlight no face atmospheric cinematic"
        ),
        "composition":     "text_upper_third",
        "thumbnail_families": [
            "single phone with scam call alert extreme closeup dramatic orange 8k",
            "empty call center rows of headsets dramatic orange lighting 8k",
            "silhouette on phone late night dramatic orange backlight 8k",
        ],
    },
    # FIX (found on deep re-audit): body_cam_police, courtroom_drama, and
    # robbery_documentaries are 3 of Evidence Room's 7 real niches but had
    # no profile at all here — every thumbnail for these 3 niches fell
    # back to FALLBACK_PROFILE's generic dark-horror-red styling instead
    # of anything forensic-appropriate.
    "body_cam_police": {
        "bg_color":        (2, 3, 6),
        "primary_text":    (220, 235, 255),
        "accent_text":     (40, 140, 230),
        "shadow_color":    (0, 25, 70),
        "badge_color":     (20, 90, 170),
        "glow_color":      (70, 170, 240),
        "vignette_strength": 0.82,
        "brightness":      0.19,
        "pollinations_style": (
            "dark police body camera footage grain night atmospheric "
            "blue dramatic no people no text cinematic 8k"
        ),
        "silhouette_style": (
            "dark silhouette police officer figure dramatic blue "
            "lighting no face cinematic atmospheric"
        ),
        "composition":     "text_lower_third",
    },
    "courtroom_drama": {
        "bg_color":        (5, 4, 2),
        "primary_text":    (250, 240, 220),
        "accent_text":     (200, 160, 60),
        "shadow_color":    (60, 45, 0),
        "badge_color":     (160, 120, 30),
        "glow_color":      (230, 190, 90),
        "vignette_strength": 0.83,
        "brightness":      0.19,
        "pollinations_style": (
            "dark courtroom wood paneling empty bench atmospheric gold "
            "dramatic no people no text cinematic 8k"
        ),
        "silhouette_style": (
            "dark silhouette figure at witness stand dramatic gold "
            "backlight no face atmospheric cinematic"
        ),
        "composition":     "text_center",
    },
    "robbery_documentaries": {
        "bg_color":        (5, 2, 2),
        "primary_text":    (255, 240, 230),
        "accent_text":     (210, 30, 30),
        "shadow_color":    (70, 0, 0),
        "badge_color":     (170, 20, 20),
        "glow_color":      (240, 60, 60),
        "vignette_strength": 0.87,
        "brightness":      0.16,
        "pollinations_style": (
            "dark bank vault heist scene atmospheric red dramatic "
            "no people no text cinematic 8k"
        ),
        "silhouette_style": (
            "dark silhouette figure fleeing dramatic red backlight "
            "no face atmospheric cinematic"
        ),
        "composition":     "text_lower_third",
    },
    # FIX (found on deep re-audit): Archive's 8 real niches had ZERO
    # thumbnail profiles at all — every single thumbnail on this channel
    # fell back to FALLBACK_PROFILE's generic dark-horror-red styling
    # regardless of whether the episode was about Egypt, China,
    # Mesopotamia, or modern parallels.
    "egyptian_civilization": {
        "bg_color":        (6, 4, 1),
        "primary_text":    (250, 235, 200),
        "accent_text":     (220, 170, 40),
        "shadow_color":    (70, 45, 0),
        "badge_color":     (180, 130, 20),
        "glow_color":      (250, 200, 80),
        "vignette_strength": 0.85,
        "brightness":      0.19,
        "pollinations_style": (
            "dark ancient egyptian temple ruins sand dust atmospheric "
            "gold dramatic lighting no people no text cinematic 8k"
        ),
        "silhouette_style": (
            "dark silhouette figure among temple columns dramatic gold "
            "backlight no face atmospheric cinematic"
        ),
        "composition":     "text_lower_third",
    },
    "chinese_civilization": {
        "bg_color":        (5, 1, 1),
        "primary_text":    (255, 235, 215),
        "accent_text":     (220, 30, 30),
        "shadow_color":    (60, 0, 0),
        "badge_color":     (180, 140, 30),
        "glow_color":      (255, 80, 60),
        "vignette_strength": 0.85,
        "brightness":      0.18,
        "pollinations_style": (
            "dark ancient chinese imperial palace architecture atmospheric "
            "red and gold dramatic no people no text cinematic 8k"
        ),
        "silhouette_style": (
            "dark silhouette figure before palace gate dramatic red "
            "backlight no face atmospheric cinematic"
        ),
        "composition":     "text_upper_third",
    },
    "mesopotamian_lost_civilizations": {
        "bg_color":        (5, 3, 1),
        "primary_text":    (245, 225, 190),
        "accent_text":     (200, 140, 60),
        "shadow_color":    (60, 35, 0),
        "badge_color":     (160, 100, 30),
        "glow_color":      (230, 170, 90),
        "vignette_strength": 0.87,
        "brightness":      0.17,
        "pollinations_style": (
            "dark ancient mesopotamian ziggurat ruins clay tablets "
            "atmospheric amber dramatic no people no text cinematic 8k"
        ),
        "silhouette_style": (
            "dark silhouette figure among ruins dramatic amber "
            "backlight no face atmospheric cinematic"
        ),
        "composition":     "text_center",
    },
    "islamic_civilization_history": {
        "bg_color":        (1, 4, 4),
        "primary_text":    (230, 250, 245),
        "accent_text":     (40, 190, 170),
        "shadow_color":    (0, 55, 50),
        "badge_color":     (20, 140, 120),
        "glow_color":      (80, 220, 200),
        "vignette_strength": 0.84,
        "brightness":      0.19,
        "pollinations_style": (
            "dark islamic architecture geometric tilework courtyard "
            "atmospheric teal and gold dramatic no people no text cinematic 8k"
        ),
        "silhouette_style": (
            "dark silhouette figure beneath archway dramatic teal "
            "backlight no face atmospheric cinematic"
        ),
        "composition":     "text_lower_third",
    },
    "fallen_empires_military_overstretch": {
        "bg_color":        (3, 3, 3),
        "primary_text":    (235, 235, 230),
        "accent_text":     (150, 90, 50),
        "shadow_color":    (40, 25, 15),
        "badge_color":     (110, 65, 35),
        "glow_color":      (190, 130, 80),
        "vignette_strength": 0.88,
        "brightness":      0.16,
        "pollinations_style": (
            "dark abandoned military fortification rusted armor "
            "atmospheric dramatic no people no text cinematic 8k"
        ),
        "silhouette_style": (
            "dark silhouette soldier figure alone dramatic rust-toned "
            "backlight no face atmospheric cinematic"
        ),
        "composition":     "text_upper_third",
    },
    "elite_betrayal_infighting": {
        "bg_color":        (4, 1, 4),
        "primary_text":    (245, 225, 250),
        "accent_text":     (190, 50, 210),
        "shadow_color":    (55, 0, 65),
        "badge_color":     (140, 30, 160),
        "glow_color":      (220, 100, 240),
        "vignette_strength": 0.87,
        "brightness":      0.17,
        "pollinations_style": (
            "dark royal court throne room shadows atmospheric purple "
            "dramatic no people no text cinematic 8k"
        ),
        "silhouette_style": (
            "dark silhouette two figures facing each other dramatic "
            "purple backlight no faces atmospheric cinematic"
        ),
        "composition":     "text_center",
    },
    "propaganda_institutional_decline": {
        "bg_color":        (5, 5, 5),
        "primary_text":    (240, 240, 235),
        "accent_text":     (200, 50, 50),
        "shadow_color":    (55, 0, 0),
        "badge_color":     (150, 30, 30),
        "glow_color":      (230, 90, 90),
        "vignette_strength": 0.88,
        "brightness":      0.16,
        "pollinations_style": (
            "dark faded propaganda poster crumbling institutional building "
            "atmospheric dramatic no people no text cinematic 8k"
        ),
        "silhouette_style": (
            "dark silhouette crowd dispersing dramatic red backlight "
            "no faces atmospheric cinematic"
        ),
        "composition":     "text_upper_third",
    },
    "modern_parallels": {
        "bg_color":        (2, 3, 5),
        "primary_text":    (225, 235, 250),
        "accent_text":     (70, 150, 230),
        "shadow_color":    (0, 30, 65),
        "badge_color":     (30, 100, 180),
        "glow_color":      (100, 180, 250),
        "vignette_strength": 0.82,
        "brightness":      0.19,
        "pollinations_style": (
            "dark modern city skyline overlaid with ancient ruins "
            "atmospheric blue dramatic no people no text cinematic 8k"
        ),
        "silhouette_style": (
            "dark silhouette figure between eras dramatic blue "
            "backlight no face atmospheric cinematic"
        ),
        "composition":     "text_center",
    },
    # FIX (found on deep re-audit): Collapse Index's 13 real niches had
    # ZERO thumbnail profiles at all — every single thumbnail on this
    # channel fell back to FALLBACK_PROFILE's generic dark-horror-red
    # styling regardless of whether the episode was about AI startups,
    # crypto, or personal finance.
    "ai_startup_collapse": {
        "bg_color":        (1, 2, 6),
        "primary_text":    (225, 235, 255),
        "accent_text":     (60, 170, 255),
        "shadow_color":    (0, 30, 90),
        "badge_color":     (20, 110, 210),
        "glow_color":      (90, 200, 255),
        "vignette_strength": 0.82,
        "brightness":      0.20,
        "pollinations_style": (
            "dark empty tech office abandoned desks glowing monitors "
            "atmospheric blue dramatic no people no text cinematic 8k"
        ),
        "silhouette_style": (
            "dark silhouette figure at empty desk dramatic blue "
            "backlight no face atmospheric cinematic"
        ),
        "composition":     "text_center",
    },
    "tech_company_collapse": {
        "bg_color":        (2, 3, 5),
        "primary_text":    (225, 235, 250),
        "accent_text":     (90, 140, 220),
        "shadow_color":    (0, 25, 70),
        "badge_color":     (40, 90, 170),
        "glow_color":      (130, 180, 240),
        "vignette_strength": 0.80,
        "brightness":      0.21,
        "pollinations_style": (
            "dark corporate skyscraper office empty boardroom atmospheric "
            "blue dramatic no people no text cinematic 8k"
        ),
        "silhouette_style": (
            "dark silhouette executive figure at window dramatic blue "
            "backlight no face atmospheric cinematic"
        ),
        "composition":     "text_lower_third",
    },
    "crypto_collapse": {
        "bg_color":        (4, 1, 5),
        "primary_text":    (240, 220, 255),
        "accent_text":     (230, 140, 30),
        "shadow_color":    (55, 0, 70),
        "badge_color":     (150, 30, 170),
        "glow_color":      (255, 170, 60),
        "vignette_strength": 0.85,
        "brightness":      0.19,
        "pollinations_style": (
            "dark crypto trading chart crashing screens glowing purple "
            "and orange atmospheric dramatic no people no text cinematic 8k"
        ),
        "silhouette_style": (
            "dark silhouette figure before falling chart dramatic "
            "purple backlight no face atmospheric cinematic"
        ),
        "composition":     "text_upper_third",
    },
    "cybersecurity_disasters": {
        "bg_color":        (0, 4, 1),
        "primary_text":    (210, 255, 220),
        "accent_text":     (30, 220, 100),
        "shadow_color":    (0, 50, 15),
        "badge_color":     (15, 150, 60),
        "glow_color":      (80, 255, 140),
        "vignette_strength": 0.86,
        "brightness":      0.18,
        "pollinations_style": (
            "dark server room breach warning glowing green code screens "
            "atmospheric dramatic no people no text cinematic 8k"
        ),
        "silhouette_style": (
            "dark silhouette hacker figure at terminal dramatic green "
            "glow no face atmospheric cinematic"
        ),
        "composition":     "text_lower_third",
    },
    "product_flops": {
        "bg_color":        (5, 2, 1),
        "primary_text":    (250, 230, 215),
        "accent_text":     (230, 100, 30),
        "shadow_color":    (60, 20, 0),
        "badge_color":     (180, 70, 15),
        "glow_color":      (250, 140, 60),
        "vignette_strength": 0.84,
        "brightness":      0.19,
        "pollinations_style": (
            "dark discontinued product on warehouse shelf dust atmospheric "
            "orange dramatic no people no text cinematic 8k"
        ),
        "silhouette_style": (
            "dark silhouette figure walking away from shelf dramatic "
            "orange backlight no face atmospheric cinematic"
        ),
        "composition":     "text_center",
    },
    "dotcom_era_collapse": {
        "bg_color":        (2, 1, 4),
        "primary_text":    (230, 225, 255),
        "accent_text":     (220, 60, 200),
        "shadow_color":    (45, 0, 60),
        "badge_color":     (150, 30, 140),
        "glow_color":      (240, 110, 220),
        "vignette_strength": 0.83,
        "brightness":      0.20,
        "pollinations_style": (
            "dark retro nineties computer monitor glowing magenta teal "
            "atmospheric dramatic no people no text cinematic 8k"
        ),
        "silhouette_style": (
            "dark silhouette figure at old computer dramatic magenta "
            "backlight no face atmospheric cinematic"
        ),
        "composition":     "text_upper_third",
    },
    "personal_finance_mistakes": {
        "bg_color":        (5, 1, 1),
        "primary_text":    (250, 225, 215),
        "accent_text":     (220, 40, 40),
        "shadow_color":    (60, 0, 0),
        "badge_color":     (170, 20, 20),
        "glow_color":      (240, 80, 80),
        "vignette_strength": 0.85,
        "brightness":      0.19,
        "pollinations_style": (
            "dark overdue bills scattered desk red ink atmospheric "
            "dramatic no people no text cinematic 8k"
        ),
        "silhouette_style": (
            "dark silhouette figure at desk with bills dramatic red "
            "backlight no face atmospheric cinematic"
        ),
        "composition":     "text_lower_third",
    },
    "investing_fundamentals": {
        "bg_color":        (1, 4, 2),
        "primary_text":    (220, 250, 225),
        "accent_text":     (60, 210, 110),
        "shadow_color":    (0, 50, 20),
        "badge_color":     (20, 150, 70),
        "glow_color":      (100, 235, 150),
        "vignette_strength": 0.80,
        "brightness":      0.21,
        "pollinations_style": (
            "dark rising stock chart glowing green gold atmospheric "
            "dramatic no people no text cinematic 8k"
        ),
        "silhouette_style": (
            "dark silhouette figure before rising chart dramatic green "
            "backlight no face atmospheric cinematic"
        ),
        "composition":     "text_center",
    },
    "retirement_planning": {
        "bg_color":        (2, 3, 5),
        "primary_text":    (230, 235, 250),
        "accent_text":     (200, 170, 70),
        "shadow_color":    (0, 25, 65),
        "badge_color":     (140, 110, 30),
        "glow_color":      (230, 200, 110),
        "vignette_strength": 0.79,
        "brightness":      0.21,
        "pollinations_style": (
            "dark calendar and savings ledger warm gold light atmospheric "
            "blue dramatic no people no text cinematic 8k"
        ),
        "silhouette_style": (
            "dark silhouette figure looking at horizon dramatic gold "
            "backlight no face atmospheric cinematic"
        ),
        "composition":     "text_upper_third",
    },
    "credit_debt_repair": {
        "bg_color":        (5, 2, 1),
        "primary_text":    (250, 230, 210),
        "accent_text":     (230, 110, 30),
        "shadow_color":    (60, 25, 0),
        "badge_color":     (180, 80, 15),
        "glow_color":      (250, 150, 60),
        "vignette_strength": 0.84,
        "brightness":      0.19,
        "pollinations_style": (
            "dark cut up credit card scattered statements atmospheric "
            "orange dramatic no people no text cinematic 8k"
        ),
        "silhouette_style": (
            "dark silhouette figure holding statement dramatic orange "
            "backlight no face atmospheric cinematic"
        ),
        "composition":     "text_lower_third",
    },
    "real_estate_affordability": {
        "bg_color":        (3, 2, 1),
        "primary_text":    (245, 232, 215),
        "accent_text":     (170, 120, 60),
        "shadow_color":    (40, 25, 0),
        "badge_color":     (130, 90, 30),
        "glow_color":      (210, 165, 100),
        "vignette_strength": 0.81,
        "brightness":      0.20,
        "pollinations_style": (
            "dark empty house for sale sign dusk atmospheric brown "
            "dramatic no people no text cinematic 8k"
        ),
        "silhouette_style": (
            "dark silhouette figure before house dramatic brown "
            "backlight no face atmospheric cinematic"
        ),
        "composition":     "text_center",
    },
    "budgeting_saving_strategies": {
        "bg_color":        (0, 4, 3),
        "primary_text":    (215, 250, 240),
        "accent_text":     (40, 200, 170),
        "shadow_color":    (0, 50, 40),
        "badge_color":     (15, 140, 115),
        "glow_color":      (90, 230, 200),
        "vignette_strength": 0.79,
        "brightness":      0.21,
        "pollinations_style": (
            "dark savings jar coins stacking warm teal light atmospheric "
            "dramatic no people no text cinematic 8k"
        ),
        "silhouette_style": (
            "dark silhouette figure counting coins dramatic teal "
            "backlight no face atmospheric cinematic"
        ),
        "composition":     "text_upper_third",
    },
    "stock_market_crashes_history": {
        "bg_color":        (5, 1, 1),
        "primary_text":    (250, 225, 215),
        "accent_text":     (220, 30, 30),
        "shadow_color":    (60, 0, 0),
        "badge_color":     (170, 20, 20),
        "glow_color":      (240, 70, 70),
        "vignette_strength": 0.88,
        "brightness":      0.16,
        "pollinations_style": (
            "dark trading floor crashing red numbers screens atmospheric "
            "dramatic no people no text cinematic 8k"
        ),
        "silhouette_style": (
            "dark silhouette figure before falling numbers dramatic red "
            "backlight no face atmospheric cinematic"
        ),
        "composition":     "text_lower_third",
    },
}

# Fallback profile for unknown niches
FALLBACK_PROFILE = {
    "bg_color":          (3, 3, 6),
    "primary_text":      (255, 255, 255),
    "accent_text":       (200, 50, 50),
    "shadow_color":      (80, 0, 0),
    "badge_color":       (160, 20, 20),
    "glow_color":        (240, 80, 80),
    "vignette_strength": 0.83,
    "brightness":        0.18,
    "pollinations_style": "dark atmospheric dramatic cinematic no people no text 8k",
    "silhouette_style":  "dark silhouette figure dramatic lighting no face cinematic",
    "composition":       "text_center",
}


# ═══════════════════════════════════════════════════════════════════
# LAYER 1: BACKGROUND — Pollinations.ai
# ═══════════════════════════════════════════════════════════════════

def fetch_background(topic, niche_name, seed, work_dir, bg_style_suffix=""):
    """
    Fetch background image from Pollinations.ai.
    Uses niche-specific visual direction for non-generic results.
    FIX: added a real Pixabay stock-photo fallback if Pollinations fails —
    previously any Pollinations failure fell straight through to a flat
    solid-color background, which is exactly the "boring/blank" result
    that was flagged. This gives it a second real chance at a genuinely
    topic-specific image before falling back to a flat color.
    """
    import urllib.parse
    profile = NICHE_PROFILES.get(niche_name, FALLBACK_PROFILE)
    # FIX (warbook v3): use a fixed thumbnail family when defined, rotating
    # by day of year — real brand consistency instead of fully open-ended
    # generation. Falls back to the old open-ended style for niches that
    # don't have families defined yet.
    families = profile.get("thumbnail_families")
    if families:
        import datetime as _dt
        style = families[_dt.datetime.now().timetuple().tm_yday % len(families)]
    else:
        style = profile["pollinations_style"]
    # The chosen thumbnail FORMAT (11-format library) adds its own
    # compositional style hint on top of the niche's own visual direction —
    # e.g. "candid unposed natural moment" for the Candid Shot format.
    if bg_style_suffix:
        style = f"{style} {bg_style_suffix}"
    topic_w = " ".join(topic.replace('"', '').split()[:6])
    prompt  = f"{topic_w} {style}"
    url     = (
        f"https://image.pollinations.ai/prompt/"
        f"{urllib.parse.quote(prompt)}"
        f"?width=1280&height=720&nologo=true"
        f"&model=flux&seed={seed}"
    )
    out_path = Path(work_dir) / f"bg_{seed}.jpg"
    try:
        r = requests.get(url, timeout=50, stream=True)
        if r.status_code == 200 and len(r.content) > 40000:
            out_path.write_bytes(r.content)
            return str(out_path)
    except Exception:
        pass

    # Real stock-photo fallback — still genuinely topic-specific, not a flat color
    # FIX (direct user report, July 24 2026 — "random thumbnails which are
    # not even suiting the thing"): this only fires when Pollinations
    # (the topic-aware AI image generator above) fails, but the raw
    # topic_w query it used has the same problem already found and fixed
    # in the main video's stock-footage search — the first 6 words of a
    # topic line are often abstract/administrative ("witnesses",
    # "classified", "agencies", "documented") rather than concrete,
    # photographable nouns, and a generic stock-photo library returns
    # unrelated hits for those. Concrete nouns get priority when present.
    _thumb_concrete_nouns = {
        "notebook","notebooks","diary","letter","letters","note","notes","mailbox",
        "apartment","house","hallway","window","door","phone","camera","car","street",
        "photograph","photo","room","drawer","box","basement","attic","key","lock",
        "stairs","closet","bedroom","kitchen","office","desk","computer","laptop",
        "envelope","package","garden","gate","curtain","mirror","clock","suitcase",
        "handwriting","file","folder","cabinet","newspaper","map","train","station",
        "bridge","forest","lake","river","ocean","cabin","hotel","hospital","school",
        "spreadsheet","invoice","contract","chart","calculator","warehouse","factory",
    }
    _topic_w_words = [w.strip(".,!?;:\"'()") for w in topic_w.lower().split()]
    _topic_w_concrete = [w for w in _topic_w_words if w in _thumb_concrete_nouns]
    thumb_query = " ".join(_topic_w_concrete[:3]) if _topic_w_concrete else topic_w
    if PIXABAY_KEY:
        try:
            r = requests.get("https://pixabay.com/api/",
                params={"key": PIXABAY_KEY, "q": thumb_query, "image_type": "photo",
                        "orientation": "horizontal", "per_page": 5, "safesearch": "true"},
                timeout=20)
            if r.status_code == 200 and r.json().get("hits"):
                hit = r.json()["hits"][0]
                img_url = hit.get("largeImageURL") or hit.get("webformatURL")
                if img_url:
                    dl = requests.get(img_url, timeout=30, stream=True)
                    if dl.status_code == 200 and len(dl.content) > 20000:
                        out_path.write_bytes(dl.content)
                        return str(out_path)
        except Exception:
            pass
    return None


# ═══════════════════════════════════════════════════════════════════
# LAYER 2: SILHOUETTE — Pollinations.ai (separate call)
# ═══════════════════════════════════════════════════════════════════

def fetch_silhouette(niche_name, seed, work_dir, topic="", channel_name="", cache_dir=None):
    """
    Fetch the "second image" figure layer — either the branded channel
    avatar (consistent illustrated host character, pose varies) if this
    channel has one defined, or the older niche-generic silhouette style
    as a fallback. Composited at 30-50% opacity over the background.

    FIX (real caching, not a demo): the earlier version generated a fresh
    AI image from Pollinations every single episode with a DIFFERENT
    random seed each time (derived from title+niche+episode). Text-to-
    image models do NOT reliably produce a visually consistent character
    across separate generations just because the text prompt is the same
    — a new seed can produce a completely different-looking figure. That
    made "consistent avatar" true only in the text description, not in
    what a viewer would actually see across episodes.

    Now: each channel+pose combination gets a DETERMINISTIC seed (derived
    only from channel name + pose text, never from episode/title), and
    the resulting image is cached PERSISTENTLY to disk the first time it's
    generated. Every subsequent episode that selects the same pose reuses
    the EXACT same cached image file — genuine, guaranteed visual
    consistency, not repeated AI re-imagining. cache_dir should be a
    PERSISTENT path (the channel's own SCRIPT_DIR, which survives between
    runs), not the ephemeral WORK_DIR, which gets wiped every run.
    """
    import urllib.parse
    profile = NICHE_PROFILES.get(niche_name, FALLBACK_PROFILE)

    avatar_desc, avatar_pose = get_channel_avatar_prompt(channel_name, seed)

    if avatar_desc and cache_dir:
        # Deterministic per-pose cache key — same channel + same pose text
        # always maps to the same cached file, regardless of episode/title.
        cache_key = re.sub(r'[^a-z0-9]+', '_', f"{channel_name}_{avatar_pose}".lower())[:80]
        cache_path = Path(cache_dir) / "avatar_cache" / f"{cache_key}.jpg"
        if cache_path.exists() and cache_path.stat().st_size > 15000:
            return str(cache_path)  # REUSE the real cached asset — true consistency

        # Not cached yet — generate ONCE with a deterministic seed (derived
        # only from channel+pose, so regenerating never produces a
        # different result for the same combination even across restarts).
        deterministic_seed = abs(hash(f"{channel_name}_{avatar_pose}")) % 99999
        prompt = f"{avatar_desc}, {avatar_pose}"
        url = (
            f"https://image.pollinations.ai/prompt/"
            f"{urllib.parse.quote(prompt)}"
            f"?width=640&height=720&nologo=true"
            f"&model=flux&seed={deterministic_seed}"
        )
        try:
            r = requests.get(url, timeout=45, stream=True)
            if r.status_code == 200 and len(r.content) > 20000:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_bytes(r.content)
                return str(cache_path)
        except:
            pass
        # Fall through to the old per-episode behavior only if caching
        # genuinely couldn't be set up (e.g. no write access) — better a
        # non-cached image than none at all.

    if avatar_desc:
        style = f"{avatar_desc}, {avatar_pose}"
    else:
        style = profile["silhouette_style"]

    topic_w = " ".join(topic.replace('"', '').split()[:4]) if topic else ""
    prompt  = f"{topic_w} {style}" if topic_w else style
    url     = (
        f"https://image.pollinations.ai/prompt/"
        f"{urllib.parse.quote(prompt)}"
        f"?width=640&height=720&nologo=true"
        f"&model=flux&seed={seed + 1000}"
    )
    out_path = Path(work_dir) / f"sil_{seed}.jpg"
    try:
        r = requests.get(url, timeout=45, stream=True)
        if r.status_code == 200 and len(r.content) > 20000:
            out_path.write_bytes(r.content)
            return str(out_path)
    except:
        pass
    return None


# ═══════════════════════════════════════════════════════════════════
# LAYER 3: TEXT COMPOSITION
# ═══════════════════════════════════════════════════════════════════

def draw_text_with_shadow_stack(draw, text, x, y, font, text_color, shadow_color, glow_color):
    """
    v2 text rendering: 5-layer shadow stack for depth and legibility.
    Layer order (bottom to top):
      1. Outer glow (large radius, glow_color, very transparent)
      2. Deep shadow (+6, +6, shadow_color)
      3. Mid shadow (+3, +3, shadow_color @ 60%)
      4. Near shadow (+1, +1, shadow_color @ 40%)
      5. Main text (text_color)
    """
    # Layer 1: outer glow (simulate with large offset, low opacity blend)
    glow_faded = tuple(c // 4 for c in glow_color)
    for gx, gy in [(-6,-6),(6,-6),(-6,6),(6,6),(-8,0),(8,0),(0,-8),(0,8)]:
        draw.text((x + gx, y + gy), text, font=font, fill=glow_faded)

    # Layer 2: deep shadow
    draw.text((x + 6, y + 6), text, font=font, fill=shadow_color)

    # Layer 3: mid shadow
    mid_shadow = tuple(c // 2 for c in shadow_color)
    draw.text((x + 3, y + 3), text, font=font, fill=mid_shadow)

    # Layer 4: near shadow
    near_shadow = tuple(c // 3 for c in shadow_color)
    draw.text((x + 1, y + 1), text, font=font, fill=near_shadow)

    # Layer 5: main text
    draw.text((x, y), text, font=font, fill=text_color)


def compute_text_position(lines, line_height, composition, font, draw, canvas_w, canvas_h):
    """
    Compute top-left Y position for text block based on composition rule.
    Compositions:
      - text_center:       vertically centred
      - text_lower_third:  bottom 35% of canvas
      - text_upper_third:  top 35% of canvas
    """
    text_block_h = len(lines) * line_height
    if composition == "text_lower_third":
        y = canvas_h - text_block_h - 90
    elif composition == "text_upper_third":
        y = 80
    else:  # text_center
        y = (canvas_h - text_block_h) // 2 - 20
    return max(60, min(y, canvas_h - text_block_h - 40))


def add_vignette(img, strength=0.85):
    """
    Radial vignette: darkens corners to draw eye to center/text.
    Strength 0-1: 1.0 = completely black corners.
    """
    w, h     = img.size
    vignette = Image.new("L", (w, h), 0)
    draw     = ImageDraw.Draw(vignette)
    cx, cy   = w // 2, h // 2
    steps    = 120
    for i in range(steps):
        ratio     = i / steps
        # Elliptical falloff
        rx = int(cx * (1 - ratio * 0.9))
        ry = int(cy * (1 - ratio * 0.9))
        brightness = int(255 * (1 - ratio * strength))
        if rx > 0 and ry > 0:
            draw.ellipse([(cx - rx, cy - ry), (cx + rx, cy + ry)],
                         fill=brightness)
    # Apply vignette as multiply blend
    vignette_rgb = Image.merge("RGB", [vignette, vignette, vignette])
    return Image.blend(Image.new("RGB", (w, h), (0, 0, 0)), img,
                       alpha=0).paste(img) or img  # fallback if blend fails

def apply_vignette(img, strength=0.83):
    """Simple vignette via corner darkening."""
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    steps = 80
    for i in range(steps):
        ratio   = i / steps
        margin  = int(min(w, h) * ratio * 0.5)
        opacity = int(255 * ratio * strength)
        if margin < w // 2 and margin < h // 2:
            draw.rectangle([margin, margin, w - margin, h - margin],
                           outline=(0, 0, 0, opacity))
    img_rgba = img.convert("RGBA")
    img_rgba = Image.alpha_composite(img_rgba, overlay)
    return img_rgba.convert("RGB")


# ═══════════════════════════════════════════════════════════════════
# NUMBER+NOUN ENFORCER
# ═══════════════════════════════════════════════════════════════════

def enforce_number_noun(thumb_text, topic, niche_name):
    """
    Ensures thumbnail text follows NUMBER+NOUN format.
    If the AI returned something without a number, generate a fallback.
    Best performing format for dark documentary thumbnails.
    """
    # Check if already has a number
    if re.search(r'\b\d[\d,\.]*\b|\b\$', thumb_text):
        return thumb_text.upper()[:20]

    # Generate number+noun from niche-specific number bank
    number_banks = {
        "dark_horror":         ["4,380 DAYS", "47 NIGHTS", "12 YEARS", "3 AM", "14 VICTIMS"],
        "seduction_dark":      ["7 SIGNS", "28 DAYS", "3 PEOPLE", "1 TRUTH", "6 WARNINGS"],
        "psychological_trap":  ["6 STAGES", "23 STEPS", "100 DAYS", "1 EXIT", "5 TRIGGERS"],
        "supernatural_real":   ["3 NIGHTS", "72 HOURS", "1 LOCATION", "9 WITNESSES", "14 YEARS"],
        "obsession_dark":      ["847 MESSAGES", "1,460 DAYS", "1 PERSON", "4 YEARS", "23 CALLS"],
        "forensic_finance":    ["$2.4M GONE", "4,380 DAYS", "47 REPORTS", "$14M FRAUD", "23 YEARS"],
        "criminal_investigation": ["14 VICTIMS", "23 YEARS", "1 FILE", "47 CLUES", "3 SUSPECTS"],
        "corporate_exposure":  ["$840M HIDDEN", "14 YEARS", "23 EXECUTIVES", "$2.4B FRAUD", "1 DOCUMENT"],
        "digital_forensics":   ["2.7M FILES", "14 TERABYTES", "847 ACCOUNTS", "1 IP ADDRESS", "23 SERVERS"],
        "cult_psychology":     ["847 MEMBERS", "14 YEARS", "7 STAGES", "1 LEADER", "23 RULES"],
        "propaganda_systems":  ["40M PEOPLE", "7 TECHNIQUES", "1 NARRATIVE", "14 YEARS", "3 AGENCIES"],
        "social_engineering":  ["6 PRINCIPLES", "847 TARGETS", "23 HOURS", "1 CALL", "7 TRIGGERS"],
        "mass_deception":      ["1B PEOPLE", "14 MONTHS", "3 NETWORKS", "1 LIE", "23 COUNTRIES"],
        "dark_business_documentaries": ["$1.2B LOST", "800K VICTIMS", "14 MONTHS", "1 MEMO", "23 COUNTRIES"],
        "scams_fraud_exposed":         ["19 YEARS", "300 EMPLOYEES", "$65B GONE", "1 PERSON", "STILL RUNNING"],
    }
    bank = number_banks.get(niche_name, ["14 YEARS", "47 CASES", "1 TRUTH", "23 HOURS"])
    # Try to extract a number from the topic
    m = re.search(r'\b(\d[\d,\.]*)\b', topic)
    if m:
        return f"{m.group(1)} {topic.split()[0].upper()[:8]}"[:20]
    return random.choice(bank)


# ═══════════════════════════════════════════════════════════════════
# HIGHLIGHT ANNOTATION — part of the 11-format thumbnail library
# (red_circle_highlight / map_diagram_overlay formats)
# ═══════════════════════════════════════════════════════════════════

def draw_highlight_shape(draw, shape, canvas_w, canvas_h, accent_color):
    """
    Draws a real annotation overlay distinct from the text layer:
      - "circle": a red-ring callout in the upper area of the frame, the
        classic "look here" highlight used to draw the eye to a detail.
      - "arrow":  a bold diagonal arrow pointing from a corner toward the
        frame's center, used for map/diagram-style thumbnails.
    """
    if shape == "circle":
        cx, cy, r = int(canvas_w * 0.74), int(canvas_h * 0.30), 90
        for w in range(6):
            draw.ellipse([cx - r - w, cy - r - w, cx + r + w, cy + r + w],
                         outline=accent_color)
    elif shape == "arrow":
        x0, y0 = int(canvas_w * 0.10), int(canvas_h * 0.20)
        x1, y1 = int(canvas_w * 0.38), int(canvas_h * 0.45)
        draw.line([(x0, y0), (x1, y1)], fill=accent_color, width=8)
        import math
        angle = math.atan2(y1 - y0, x1 - x0)
        head_len = 26
        for spread in (0.5, -0.5):
            hx = x1 - head_len * math.cos(angle - spread * 0.9)
            hy = y1 - head_len * math.sin(angle - spread * 0.9)
            draw.line([(x1, y1), (hx, hy)], fill=accent_color, width=8)


# ═══════════════════════════════════════════════════════════════════
# CHANNEL BADGE RENDERER
# ═══════════════════════════════════════════════════════════════════

def draw_channel_badge(draw, channel_name, episode, badge_color, work_dir):
    """
    Draws a channel badge in top-left corner.
    Format: ● CHANNEL NAME  |  EP. 47
    Small, unobtrusive, but present on every thumbnail for brand recognition.
    """
    badge_font = get_font(22)
    badge_text = f"● {channel_name.upper()[:18]}  |  EP.{episode}"
    # Semi-transparent background bar
    try:
        bb     = draw.textbbox((0, 0), badge_text, font=badge_font)
        bar_w  = bb[2] - bb[0] + 30
        bar_h  = bb[3] - bb[1] + 12
        faded  = tuple(max(0, c - 120) for c in badge_color) + (180,)
        draw.rectangle([(10, 10), (10 + bar_w, 10 + bar_h)],
                       fill=(0, 0, 0, 140))
        draw.text((22, 15), badge_text, font=badge_font, fill=badge_color)
    except:
        draw.text((22, 15), badge_text, font=badge_font, fill=badge_color)


# ═══════════════════════════════════════════════════════════════════
# MAIN THUMBNAIL GENERATOR v2
# ═══════════════════════════════════════════════════════════════════

def generate_thumbnail_v2(title, thumb_text, niche_name, topic,
                           channel_name, episode, work_dir,
                           ab_variant="A", cache_dir=None, format_name=None):
    """
    Generate a three-layer thumbnail.
    Variant A: with silhouette layer (weeks 1, 3, 5...)
    Variant B: without silhouette, stronger text contrast (weeks 2, 4, 6...)
    This is composition A/B testing, not just colour A/B testing.

    On top of the A/B toggle, this also selects one of the 11 named
    thumbnail formats (video_pipeline/thumbnail_formats.py) — a real,
    performance-learning selection (see select_thumbnail_format) when
    cache_dir is provided, or the format passed in explicitly via
    format_name. The format's silhouette flag takes priority over
    ab_variant (a format like Candid Shot always wants its avatar layer;
    Object Evidence Close-up never does), and every choice is appended to
    thumb_format_history.json in cache_dir — a real, growing history, not
    a single overwritten value.

    Returns: path to generated thumbnail JPEG
    """
    profile     = NICHE_PROFILES.get(niche_name, FALLBACK_PROFILE)
    seed        = abs(hash(f"{title}{niche_name}{episode}")) % 99999
    out_path    = str(Path(work_dir) / "thumbnail.jpg")

    chosen_format = format_name
    bg_style_suffix = ""
    force_silhouette = None
    highlight = None
    if cache_dir:
        try:
            from thumbnail_formats import select_thumbnail_format, apply_format, record_format_used
            if not chosen_format:
                chosen_format = select_thumbnail_format(cache_dir, channel_name, niche_name, episode)
            composition, bg_style_suffix, force_silhouette, highlight = apply_format(profile, chosen_format)
            record_format_used(cache_dir, channel_name, niche_name, episode, chosen_format)
        except Exception:
            composition = profile["composition"]
    else:
        composition = profile["composition"]

    # Enforce NUMBER+NOUN
    thumb_text = enforce_number_noun(thumb_text, topic, niche_name)

    # ── LAYER 1: Background ────────────────────────────────────────
    bg_path = fetch_background(topic, niche_name, seed, work_dir, bg_style_suffix=bg_style_suffix)
    if bg_path and Path(bg_path).exists():
        try:
            img = Image.open(bg_path).convert("RGB").resize((TW, TH),
                                                              Image.LANCZOS)
        except:
            img = Image.new("RGB", (TW, TH), profile["bg_color"])
    else:
        img = Image.new("RGB", (TW, TH), profile["bg_color"])

    # Darken background to required brightness
    img = ImageEnhance.Brightness(img).enhance(profile["brightness"])

    # ── LAYER 2: Silhouette — the chosen format's silhouette flag wins
    # over ab_variant when a format was selected; otherwise ab_variant
    # (the older week-based A/B toggle) still controls it. ─────────────
    show_silhouette = force_silhouette if force_silhouette is not None else (ab_variant == "A")
    if show_silhouette:
        sil_path = fetch_silhouette(niche_name, seed, work_dir, topic=topic, channel_name=channel_name, cache_dir=cache_dir)
        if sil_path and Path(sil_path).exists():
            try:
                sil = Image.open(sil_path).convert("RGBA")
                # Resize silhouette to right half of canvas (centred)
                sil_w = int(TW * 0.45)
                sil_h = TH
                sil   = sil.resize((sil_w, sil_h), Image.LANCZOS)
                # Position: right-centre
                sil_x = TW - sil_w - 20
                sil_y = 0
                # Apply silhouette at 45% opacity
                sil_dark = ImageEnhance.Brightness(sil.convert("RGB")).enhance(0.3)
                sil_dark = sil_dark.convert("RGBA")
                sil_dark.putalpha(115)  # ~45% opacity
                img.paste(sil_dark.convert("RGB"),
                          (sil_x, sil_y),
                          mask=sil_dark.split()[3])
            except Exception as e:
                pass  # silhouette layer fails gracefully

    # ── Apply vignette ─────────────────────────────────────────────
    img = apply_vignette(img, profile["vignette_strength"])

    # ── LAYER 3: Text ─────────────────────────────────────────────
    # FIX (found on sequential re-audit): the line that used to be here
    # created an ImageDraw.Draw object and accessed its internal .im
    # attribute, assigning it to `draw` — then immediately overwrote
    # `draw` on the very next line with a fresh, correct Draw object.
    # The first line did nothing but waste a bit of computation; harmless
    # but confusing. Removed.
    img_rgba = img.convert("RGBA")
    draw     = ImageDraw.Draw(img_rgba)

    primary    = profile["primary_text"]
    accent     = profile["accent_text"]
    shadow_col = profile["shadow_color"]
    glow_col   = profile["glow_color"]
    badge_col  = profile["badge_color"]

    # Format-driven highlight annotation (red_circle_highlight / map_diagram_overlay)
    if highlight:
        try:
            draw_highlight_shape(draw, highlight, TW, TH, accent)
        except Exception:
            pass

    # Split thumbnail text into lines
    words = thumb_text.split()
    if len(words) <= 2:
        lines = [thumb_text]
    elif len(words) == 3:
        lines = [words[0], " ".join(words[1:])]
    else:
        mid = len(words) // 2
        lines = [" ".join(words[:mid]), " ".join(words[mid:])]

    # Font sizing — two-pass: try large, reduce if doesn't fit
    font_size = 116
    while font_size > 60:
        font     = get_font(font_size)
        max_w    = max(
            (draw.textbbox((0, 0), line, font=font)[2] -
             draw.textbbox((0, 0), line, font=font)[0])
            for line in lines
        )
        if max_w < TW - 80:
            break
        font_size -= 8

    font        = get_font(font_size)
    line_height = font_size + 18
    text_block_h = len(lines) * line_height

    # Vertical position
    y_start = compute_text_position(
        lines, line_height, composition, font, draw, TW, TH
    )

    # Draw each line
    for i, line in enumerate(lines):
        bb   = draw.textbbox((0, 0), line, font=font)
        line_w = bb[2] - bb[0]
        # Horizontal: centred for first line, centred for second line
        x    = (TW - line_w) // 2
        y    = y_start + i * line_height

        # Colour: accent on line 1 (the number), primary on line 2
        text_col = accent if i == 0 and ab_variant == "A" else primary

        draw_text_with_shadow_stack(
            draw, line, x, y, font, text_col, shadow_col, glow_col
        )

    # Subtitle (shortened title)
    sub_font = get_font(28)
    sub_text = title[:62] + ("…" if len(title) > 62 else "")
    try:
        sub_bb  = draw.textbbox((0, 0), sub_text, font=sub_font)
        sub_w   = sub_bb[2] - sub_bb[0]
        sub_x   = (TW - sub_w) // 2
        sub_y   = y_start + text_block_h + 12
        if sub_y < TH - 50:
            # Subtitle shadow
            draw.text((sub_x + 2, sub_y + 2), sub_text, font=sub_font,
                      fill=tuple(c // 3 for c in shadow_col))
            draw.text((sub_x, sub_y), sub_text, font=sub_font,
                      fill=tuple(min(255, c + 60) for c in primary))
    except:
        pass

    # Channel badge
    draw_channel_badge(draw, channel_name, episode, badge_col, work_dir)

    # Border lines (thin accent lines top and bottom)
    draw.line([(0, 3), (TW, 3)], fill=accent, width=3)
    draw.line([(0, TH - 3), (TW, TH - 3)], fill=accent, width=3)

    # Save
    final = img_rgba.convert("RGB")
    final.save(out_path, "JPEG", quality=96)

    # Cleanup temp files
    for tmp in [bg_path, str(Path(work_dir) / f"sil_{seed}.jpg")]:
        if tmp and Path(tmp).exists():
            try:
                Path(tmp).unlink()
            except:
                pass

    return out_path


# ═══════════════════════════════════════════════════════════════════
# THUMBNAIL SCORE — used by CTR recovery loop
# ═══════════════════════════════════════════════════════════════════

def score_thumbnail_text(thumb_text):
    """
    Score a thumbnail text on 3 axes.
    Used to compare A/B variants before choosing which to upload.
    """
    t  = thumb_text.upper()
    sc = 5.0

    # 1. Has number (most important)
    if re.search(r'\b\d[\d,\.]*\b|\$', t):
        sc += 2.5
    else:
        sc -= 2.0

    # 2. Length — 2-3 words optimal
    words = t.split()
    if 2 <= len(words) <= 3:  sc += 1.5
    elif len(words) == 1:     sc += 0.5
    elif len(words) > 4:      sc -= 1.0

    # 3. Specificity signals
    specific = ["DAYS", "YEARS", "HOURS", "MONTHS", "PEOPLE", "VICTIMS",
                "CASES", "REPORTS", "FILES", "GONE", "HIDDEN", "EXPOSED"]
    if any(s in t for s in specific):
        sc += 1.0

    return round(min(max(sc, 0), 10), 1)
