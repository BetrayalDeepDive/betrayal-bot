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

def fetch_background(topic, niche_name, seed, work_dir):
    """
    Fetch background image from Pollinations.ai.
    Uses niche-specific visual direction for non-generic results.
    """
    import urllib.parse
    profile = NICHE_PROFILES.get(niche_name, FALLBACK_PROFILE)
    style   = profile["pollinations_style"]
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
    except Exception as e:
        pass
    return None


# ═══════════════════════════════════════════════════════════════════
# LAYER 2: SILHOUETTE — Pollinations.ai (separate call)
# ═══════════════════════════════════════════════════════════════════

def fetch_silhouette(niche_name, seed, work_dir):
    """
    Fetch a human silhouette figure image matched to the niche.
    Composited at 30-50% opacity over the background for depth.
    """
    import urllib.parse
    profile = NICHE_PROFILES.get(niche_name, FALLBACK_PROFILE)
    style   = profile["silhouette_style"]
    url     = (
        f"https://image.pollinations.ai/prompt/"
        f"{urllib.parse.quote(style)}"
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
    }
    bank = number_banks.get(niche_name, ["14 YEARS", "47 CASES", "1 TRUTH", "23 HOURS"])
    # Try to extract a number from the topic
    m = re.search(r'\b(\d[\d,\.]*)\b', topic)
    if m:
        return f"{m.group(1)} {topic.split()[0].upper()[:8]}"[:20]
    return random.choice(bank)


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
                           ab_variant="A"):
    """
    Generate a three-layer thumbnail.
    Variant A: with silhouette layer (weeks 1, 3, 5...)
    Variant B: without silhouette, stronger text contrast (weeks 2, 4, 6...)
    This is composition A/B testing, not just colour A/B testing.

    Returns: path to generated thumbnail JPEG
    """
    profile     = NICHE_PROFILES.get(niche_name, FALLBACK_PROFILE)
    seed        = abs(hash(f"{title}{niche_name}{episode}")) % 99999
    out_path    = str(Path(work_dir) / "thumbnail.jpg")
    composition = profile["composition"]

    # Enforce NUMBER+NOUN
    thumb_text = enforce_number_noun(thumb_text, topic, niche_name)

    # ── LAYER 1: Background ────────────────────────────────────────
    bg_path = fetch_background(topic, niche_name, seed, work_dir)
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

    # ── LAYER 2: Silhouette (A variant only) ──────────────────────
    if ab_variant == "A":
        sil_path = fetch_silhouette(niche_name, seed, work_dir)
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
    draw = ImageDraw.Draw(img.convert("RGBA")).im  # draw on RGB
    img_rgba = img.convert("RGBA")
    draw     = ImageDraw.Draw(img_rgba)

    primary    = profile["primary_text"]
    accent     = profile["accent_text"]
    shadow_col = profile["shadow_color"]
    glow_col   = profile["glow_color"]
    badge_col  = profile["badge_color"]

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
