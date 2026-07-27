"""
BOARD register (20% of Ch1's mix, per direct spec): "switch to an
investigation board as evidence is introduced." A cork-board scene with
pinned evidence cards, red string connecting them, and the segment's own
text pinned as a note -- animated with a slow Ken Burns pan/zoom (a
real detective board is looked AT, not walked through, so camera motion
carries the "cinematic" feel here instead of a character rig).

Deterministic per-segment layout (seeded off seg_index, not random.seed
globally) so pin/photo positions are stable and reproducible frame-to-
frame within one segment, but vary segment-to-segment.
"""
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import subprocess

W, H = 1280, 720
FPS = 24

NICHE_BOARD_TINT = {
    "dark_horror":        (58, 44, 30),
    "seduction_dark":     (54, 30, 34),
    "psychological_trap": (40, 46, 34),
    "supernatural_real":  (36, 40, 48),
    "obsession_dark":     (56, 46, 26),
}
NICHE_ACCENT = {
    "dark_horror":        (200, 30, 30),
    "seduction_dark":     (210, 40, 90),
    "psychological_trap": (60, 190, 130),
    "supernatural_real":  (90, 140, 220),
    "obsession_dark":     (220, 160, 40),
}


def _font(size):
    for fp in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
               "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"):
        if Path(fp).exists():
            return ImageFont.truetype(fp, size)
    return None


def _cork_texture(w, h, base_color, seed):
    img = Image.new("RGB", (w, h), base_color)
    px = img.load()
    rnd = random.Random(seed)
    for _ in range(int(w * h * 0.015)):
        x, y = rnd.randrange(w), rnd.randrange(h)
        shade = rnd.randint(-14, 14)
        c = px[x, y]
        px[x, y] = tuple(max(0, min(255, ch + shade)) for ch in c)
    return img


def _draw_evidence_card(draw, cx, cy, w, h, label, accent, font, filled=True, style="doc", seed=0):
    """
    FIX (found this session via a real render + frame inspection): every
    card was an identical flat cream rectangle labeled "EXHIBIT N" --
    reads as an obvious placeholder, not evidence. Two real alternating
    looks now: "photo" (a grayscale vignette rectangle simulating an old
    photograph -- no faces/generated content, just tone/shading so it
    reads as a photo silhouette) and "doc" (an off-white card with
    horizontal redaction-bar lines simulating a typed/printed document).
    Alternated by seg_index in generate_board_segment so a single board
    always shows a genuine mix of both, not one style repeated.
    """
    x0, y0, x1, y1 = cx - w/2, cy - h/2, cx + w/2, cy + h/2
    if not filled:
        draw.rectangle([x0, y0, x1, y1], outline=(200, 200, 200), width=2)
    elif style == "plain":
        # Used for the note card, which has real narration text drawn on
        # top separately -- doc-style redaction bars would visually
        # collide with that real text, so this stays a clean flat card.
        draw.rectangle([x0, y0, x1, y1], fill=(224, 216, 196), outline=(30, 30, 30), width=2)
    elif style == "photo":
        rnd = random.Random(seed)
        base = rnd.randint(70, 110)
        for yy in range(int(y0), int(y1), 3):
            shade = base + int(20 * math.sin((yy - y0) / h * math.pi))
            draw.rectangle([x0, yy, x1, yy + 3], fill=(shade, shade, shade + 4))
        # vignette corners
        draw.rectangle([x0, y0, x1, y1], outline=(15, 15, 15), width=3)
        for k in range(4):
            draw.rectangle([x0 + k, y0 + k, x1 - k, y1 - k], outline=(max(0, base - 25 - k*4),)*3)
    else:  # "doc" — typed/printed document with redaction bars
        draw.rectangle([x0, y0, x1, y1], fill=(232, 228, 214), outline=(30, 30, 30), width=2)
        rnd = random.Random(seed + 500)
        n_lines = 5
        for li in range(n_lines):
            ly = y0 + 16 + li * ((h - 30) / n_lines)
            line_w = rnd.uniform(0.4, 0.85) * (w - 20)
            redacted = rnd.random() < 0.35
            color = (30, 30, 30) if not redacted else (20, 20, 20)
            if redacted:
                draw.rectangle([x0 + 10, ly, x0 + 10 + line_w, ly + 8], fill=color)
            else:
                draw.line([(x0 + 10, ly + 4), (x0 + 10 + line_w, ly + 4)], fill=(90, 90, 90), width=2)
    # pin
    draw.ellipse([cx - 6, y0 - 10, cx + 6, y0 + 2], fill=accent, outline=(20, 20, 20))
    if label and font:
        words = label.split()
        line = " ".join(words[:3])[:18]
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        tag_y = y1 + 4
        draw.rectangle([cx - tw/2 - 4, tag_y, cx + tw/2 + 4, tag_y + 20], fill=(20, 20, 20))
        draw.text((cx - tw/2, tag_y + 1), line, fill=(255, 255, 255), font=font)


def generate_board_segment(niche_name, segment_text, text_overlay, duration, seg_index,
                            output_path, width=W, height=H, fps=FPS, log_fn=print):
    """
    Renders ONE investigation-board clip: 3-4 pinned cards + red string
    + the segment's own key phrase pinned front-and-center, slow Ken
    Burns zoom/pan across the board. Returns True/False, never raises.
    """
    tint = NICHE_BOARD_TINT.get(niche_name, NICHE_BOARD_TINT["dark_horror"])
    accent = NICHE_ACCENT.get(niche_name, NICHE_ACCENT["dark_horror"])
    rnd = random.Random(seg_index * 97 + 13)

    n_frames = max(1, int(round(duration * fps)))
    tmp_dir = Path(output_path).parent / f"board_{seg_index}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    font_lbl = _font(20)
    font_note = _font(26)

    # Oversized canvas so the Ken Burns pan/zoom has room to move.
    OW, OH = int(width * 1.25), int(height * 1.25)

    try:
        base = _cork_texture(OW, OH, tint, seed=seg_index)
        draw = ImageDraw.Draw(base)

        # FIX (found this session via a real render + frame inspection):
        # fully random (cx, cy) per card had no collision check, so
        # cards regularly overlapped each other (confirmed: EXHIBIT 2/3
        # stacked directly on top of one another in a test frame).
        # Real fix: reject-and-retry placement with a minimum center
        # distance before falling back to a deterministic grid slot.
        n_cards = 3 + (seg_index % 2)
        card_positions = []
        min_dist = 195
        for i in range(n_cards):
            placed = False
            for _try in range(25):
                cx = rnd.randint(int(OW*0.15), int(OW*0.85))
                cy = rnd.randint(int(OH*0.15), int(OH*0.50))
                if all(math.hypot(cx - px, cy - py) >= min_dist for px, py in card_positions):
                    card_positions.append((cx, cy))
                    placed = True
                    break
            if not placed:
                col = i % 3
                cx = int(OW * (0.2 + col * 0.3))
                cy = int(OH * (0.18 + (i // 3) * 0.28))
                card_positions.append((cx, cy))
            card_style = "photo" if i % 2 == 0 else "doc"
            _draw_evidence_card(draw, cx, cy, 130, 90, f"EXHIBIT {i+1}", accent, font_lbl,
                                 style=card_style, seed=seg_index * 31 + i)

        # Red string connecting the cards in sequence.
        for i in range(len(card_positions) - 1):
            draw.line([card_positions[i], card_positions[i+1]], fill=(180, 20, 20), width=3)

        # The segment's own key phrase, pinned as a centered note card.
        note_text = (text_overlay or segment_text or "")[:40]
        note_cx, note_cy = OW // 2, int(OH * 0.78)
        _draw_evidence_card(draw, note_cx, note_cy, 420, 110, "", accent, None, style="plain")
        if font_note and note_text:
            bbox = draw.textbbox((0, 0), note_text, font=font_note)
            tw = bbox[2] - bbox[0]
            draw.text((note_cx - tw/2, note_cy - 14), note_text, fill=(20, 20, 20), font=font_note)

        # Ken Burns: slow zoom+pan crop window sliding across the oversized board.
        zoom_start, zoom_end = 1.0, 1.12
        pan_dx = rnd.choice([-1, 1]) * (OW - width) * 0.5
        for f in range(n_frames):
            t = f / max(1, n_frames - 1)
            zoom = zoom_start + (zoom_end - zoom_start) * t
            crop_w, crop_h = int(width / zoom), int(height / zoom)
            cx0 = (OW - crop_w) / 2 + pan_dx * t
            cy0 = (OH - crop_h) / 2 * 0.6
            cx0 = max(0, min(OW - crop_w, cx0))
            cy0 = max(0, min(OH - crop_h, cy0))
            frame = base.crop((int(cx0), int(cy0), int(cx0) + crop_w, int(cy0) + crop_h))
            frame = frame.resize((width, height), Image.LANCZOS)
            frame.save(tmp_dir / f"f_{f:04d}.png")

        result = subprocess.run(
            ["ffmpeg", "-y", "-framerate", str(fps), "-i", str(tmp_dir / "f_%04d.png"),
             "-c:v", "libx264", "-preset", "fast", "-crf", "22",
             "-pix_fmt", "yuv420p", "-t", f"{duration:.2f}", str(output_path)],
            capture_output=True, timeout=120)
        ok = result.returncode == 0 and Path(output_path).exists() and Path(output_path).stat().st_size > 2000
        if not ok:
            log_fn(f"    Board segment {seg_index}: ffmpeg failed — "
                   f"{result.stderr.decode(errors='ignore')[-300:]}")
        return ok
    except Exception as e:
        log_fn(f"    Board segment {seg_index}: {e}")
        return False
    finally:
        try:
            for p in tmp_dir.glob("f_*.png"):
                p.unlink()
            tmp_dir.rmdir()
        except Exception:
            pass
