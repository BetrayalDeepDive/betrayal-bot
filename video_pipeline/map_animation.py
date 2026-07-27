"""
MAP register (direct user spec, this session: "I want you to use Animated
Maps as well"): a real-geography map clip, base world map (genuine country
borders from the same public-domain dataset Ch4's map system already
uses) with the story's actual country progressively highlighted and
labeled -- for segments where the narration actually names a real place,
not decoration for its own sake.

Deliberately reuses the proven rendering approach already built and
shipping for Ch4 (archive_pipeline.py's _render_map_highlight): real
equirectangular lon/lat projection, progressive fade-in reveal of the
highlighted country, real polygon geometry -- not a random shape. This
module takes the country's GeoJSON feature and the full feature list as
plain parameters (no file I/O of its own), so the caller controls which
real dataset/path is loaded, matching how every other Ch1 renderer in
this package takes its inputs directly.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import subprocess

W, H = 1280, 720
FPS = 24

NICHE_ACCENT = {
    "dark_horror":        (210, 30, 30),
    "seduction_dark":     (210, 40, 90),
    "psychological_trap": (60, 190, 130),
    "supernatural_real":  (90, 140, 220),
    "obsession_dark":     (220, 160, 40),
}
NICHE_BG = {
    "dark_horror":        (10, 10, 16),
    "seduction_dark":     (16, 8, 10),
    "psychological_trap": (8, 14, 11),
    "supernatural_real":  (9, 10, 17),
    "obsession_dark":     (15, 12, 8),
}


def _font(size, bold=True):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    for fp in (f"/usr/share/fonts/truetype/dejavu/{name}",
               f"/usr/share/fonts/truetype/liberation/Liberation{'Sans-Bold' if bold else 'Sans'}.ttf"):
        if Path(fp).exists():
            return ImageFont.truetype(fp, size)
    return None


def _lonlat_to_xy(lon, lat, map_w, map_h, offset_x, offset_y):
    """Real equirectangular projection -- same formula as Ch4's map system."""
    x = offset_x + (lon + 180) / 360 * map_w
    y = offset_y + (90 - lat) / 180 * map_h
    return x, y


def _draw_country_polygon(draw, geometry, map_w, map_h, offset_x, offset_y, fill, outline):
    def draw_ring(ring):
        pts = [_lonlat_to_xy(lon, lat, map_w, map_h, offset_x, offset_y) for lon, lat in ring]
        if len(pts) >= 3:
            draw.polygon(pts, fill=fill, outline=outline)
    gtype = geometry.get("type", "")
    if gtype == "Polygon":
        for ring in geometry["coordinates"]:
            draw_ring(ring)
    elif gtype == "MultiPolygon":
        for poly in geometry["coordinates"]:
            for ring in poly:
                draw_ring(ring)


def generate_map_segment(niche_name, country_feature, all_features, label_text, duration, seg_index,
                          output_path, width=W, height=H, fps=FPS, log_fn=print):
    """
    Renders ONE real-geography map clip: dim base world map (all real
    country borders) with the story's actual country progressively
    fading in/highlighted in the niche's accent color, labeled with the
    real country name plus an optional caption. Returns True/False,
    never raises.
    """
    accent = NICHE_ACCENT.get(niche_name, NICHE_ACCENT["dark_horror"])
    bg = NICHE_BG.get(niche_name, NICHE_BG["dark_horror"])
    n_frames = max(1, int(round(duration * fps)))
    tmp_dir = Path(output_path).parent / f"map_{seg_index}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    font_label = _font(34)
    font_country = _font(26, bold=False)

    map_w, map_h = int(width * 0.82), int(height * 0.68)
    offset_x, offset_y = int(width * 0.09), int(height * 0.18)
    country_name = (country_feature or {}).get("name", "")
    geometry = (country_feature or {}).get("geometry")

    try:
        # FIX (found via real integration test this session -- a full
        # episode's MAP segments alone blew past a 10-minute timeout):
        # this used to redraw all 258 country polygons from scratch on
        # EVERY single frame, when only ONE country (the target) ever
        # changes color frame-to-frame. Render the static base map (every
        # OTHER country, which never changes) exactly once and reuse it,
        # same "render once per segment" principle already used by
        # stickman_animation.py's background builder -- cuts real
        # per-frame cost from 258 polygon fills to 1.
        base_map = Image.new("RGB", (width, height), bg)
        base_draw = ImageDraw.Draw(base_map)
        for feat in all_features:
            if geometry is not None and feat is country_feature:
                continue
            _draw_country_polygon(base_draw, feat["geometry"], map_w, map_h, offset_x, offset_y,
                                   fill=(26, 26, 32), outline=(44, 44, 52))

        for f in range(n_frames):
            t = f / max(1, n_frames - 1)
            reveal = min(1.0, t * 1.6)
            img = base_map.copy()
            draw = ImageDraw.Draw(img)

            if geometry is not None:
                fill = tuple(int(c * reveal + b * (1 - reveal)) for c, b in zip(accent, (30, 28, 34)))
                _draw_country_polygon(draw, geometry, map_w, map_h, offset_x, offset_y,
                                       fill=fill, outline=accent)

            if font_label:
                tag = "LOCATION"
                draw.text((offset_x, offset_y - 46), tag, fill=accent, font=font_country)
            if country_name and font_label and reveal > 0.2:
                bbox = draw.textbbox((0, 0), country_name, font=font_label)
                tw = bbox[2] - bbox[0]
                draw.text(((width - tw) / 2, height - 78), country_name, fill=(235, 235, 240), font=font_label)
            if label_text and font_country and reveal > 0.35:
                bbox = draw.textbbox((0, 0), label_text[:60], font=font_country)
                tw = bbox[2] - bbox[0]
                draw.text(((width - tw) / 2, height - 42), label_text[:60], fill=accent, font=font_country)

            img.save(tmp_dir / f"f_{f:04d}.png")

        result = subprocess.run(
            ["ffmpeg", "-y", "-framerate", str(fps), "-i", str(tmp_dir / "f_%04d.png"),
             "-c:v", "libx264", "-preset", "fast", "-crf", "22",
             "-pix_fmt", "yuv420p", "-t", f"{duration:.2f}", str(output_path)],
            capture_output=True, timeout=120)
        ok = result.returncode == 0 and Path(output_path).exists() and Path(output_path).stat().st_size > 2000
        if not ok:
            log_fn(f"    Map segment {seg_index}: ffmpeg failed — "
                   f"{result.stderr.decode(errors='ignore')[-300:]}")
        return ok
    except Exception as e:
        log_fn(f"    Map segment {seg_index}: {e}")
        return False
    finally:
        try:
            for p in tmp_dir.glob("f_*.png"):
                p.unlink()
            tmp_dir.rmdir()
        except Exception:
            pass
