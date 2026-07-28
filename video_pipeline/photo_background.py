"""
Real, topic-matched environment photo backgrounds for Ch1's character
segments (STICKMAN/SILHOUETTE registers) -- direct user follow-up after
reviewing sample renders that used a procedurally-drawn background:
"the pictures look the same, and the dots or the stars or whatever you
have made are too generic. I want something that is based on the
specific niche and the topic. For example: if it talks about some kind
of dark room, it should show a dark room. If it is talking about
walking in some place in the forest, it should show that. If it is
doing something else, like a murderous place, it should show that. If
it is showing any kind of office, it should show that... can we use the
real pictures for it so that it feels more entertaining than a made-up
background."

Deliberately reuses the EXACT Pixabay-then-Pexels photo-API priority
chain, free already-configured keys (PIXABAY_KEY/PEXELS_KEY), and the
same post-fetch relevance-check technique already proven and shipping
elsewhere in this pipeline (master_pipeline.fetch_case_relevant_image
for thumbnail case images, and the per-segment stock FOOTAGE fetch in
get_stage_matched_video) -- not a new integration, the same one this
channel already runs successfully every episode.

Matches the existing pattern in map_animation.py/scene_recreation.py:
the caller passes in its own already-computed real inputs (the segment's
tuned search_terms: topic anchor / concrete noun / nation context, the
same values already used for stock footage search) rather than this
module doing its own text analysis.
"""
from pathlib import Path
from PIL import Image, ImageEnhance
import requests

# Same real-hit relevance problem already solved for stock footage: a
# query can look fine and still come back with a bright, mismatched
# photo (a "dark room" search returning a cheerfully lit living room
# stock photo). Checked against the hit's own tags (Pixabay) or
# descriptive URL slug (Pexels), not the outgoing query.
DEFAULT_BLOCKLIST = {
    "flowers", "flower", "garden", "wedding", "birthday", "party", "parties",
    "sunshine", "sunny", "picnic", "vacation", "holiday", "holidays", "beach",
    "celebration", "celebrate", "smiling", "smile", "laughing", "laughter",
    "balloons", "cake", "gift", "gifts", "present", "presents", "rainbow",
    "puppy", "kitten", "baby", "babies", "graduation", "summer",
    "playground", "festival", "carnival", "circus", "confetti",
    "butterfly", "butterflies", "insect", "insects", "bug", "bugs", "bee", "bees",
    "wildlife", "macro", "bloom", "blossom", "meadow", "daisy", "tulip", "pollen",
}

# Same dark per-niche mood palette already established for the
# procedurally-drawn background (stickman_animation.NICHE_BG_COLOR) --
# reused here so a real photo grades into this channel's look instead
# of showing up at its own original, unrelated exposure/color.
NICHE_BG_TINT = {
    "dark_horror":        (7, 9, 14),
    "seduction_dark":     (14, 6, 8),
    "psychological_trap": (6, 12, 9),
    "supernatural_real":  (7, 9, 15),
    "obsession_dark":     (13, 10, 6),
}


def _looks_mismatched(text, blocklist):
    low = (text or "").lower()
    return any(w in low for w in blocklist)


def fetch_photo_background(search_terms, niche_name, out_path, pixabay_key="", pexels_key="",
                            relevance_blocklist=None, log_fn=print):
    """
    Tries each of search_terms in order (most specific/real first --
    the caller's own segment keyword pipeline, same as stock footage),
    Pixabay photo API then Pexels photo API for each term, skipping any
    candidate whose own tags/description hits relevance_blocklist.

    Returns out_path on a real download, or None so the caller can fall
    back to its own default (procedurally-drawn) background. Never
    raises -- a missing key, a network error, or zero real hits are all
    just "no real photo this time", not a fatal condition.
    """
    blocklist = relevance_blocklist if relevance_blocklist is not None else DEFAULT_BLOCKLIST
    for term in search_terms:
        if not term:
            continue
        if pixabay_key:
            try:
                r = requests.get("https://pixabay.com/api/",
                    params={"key": pixabay_key, "q": term, "image_type": "photo",
                            "orientation": "horizontal", "min_width": 1280,
                            "safesearch": "true", "per_page": 6, "order": "popular"},
                    timeout=20)
                if r.status_code == 200:
                    for hit in r.json().get("hits", []):
                        if _looks_mismatched(hit.get("tags", ""), blocklist):
                            continue
                        img_url = hit.get("webformatURL") or hit.get("largeImageURL")
                        if not img_url:
                            continue
                        ir = requests.get(img_url, timeout=25)
                        if ir.status_code == 200 and len(ir.content) > 20000:
                            with open(out_path, "wb") as f:
                                f.write(ir.content)
                            log_fn(f"    Real photo background (Pixabay): '{term}'")
                            return out_path
            except Exception as e:
                log_fn(f"    Photo background Pixabay '{term}' (non-fatal): {e}")

        if pexels_key:
            try:
                r = requests.get("https://api.pexels.com/v1/search",
                    headers={"Authorization": pexels_key},
                    params={"query": term, "per_page": 6, "orientation": "landscape", "size": "large"},
                    timeout=20)
                if r.status_code == 200:
                    for photo in r.json().get("photos", []):
                        if _looks_mismatched(photo.get("url", ""), blocklist):
                            continue
                        img_url = (photo.get("src", {}).get("large2x")
                                   or photo.get("src", {}).get("large"))
                        if not img_url:
                            continue
                        ir = requests.get(img_url, timeout=25)
                        if ir.status_code == 200 and len(ir.content) > 20000:
                            with open(out_path, "wb") as f:
                                f.write(ir.content)
                            log_fn(f"    Real photo background (Pexels): '{term}'")
                            return out_path
            except Exception as e:
                log_fn(f"    Photo background Pexels '{term}' (non-fatal): {e}")
    return None


def photo_to_cover_canvas(photo_path, width, height, oversize=1.0):
    """
    Real downloaded photo -> a canvas cropped/resized to fully COVER
    (width*oversize, height*oversize) without distortion (same fit a
    real editor would use), cropping any excess rather than stretching.
    oversize > 1.0 leaves margin for a Ken Burns pan/zoom crop on top
    (scene_recreation.py's technique) to run unchanged over a real photo
    exactly as it already does over the procedurally-drawn background.
    """
    img = Image.open(photo_path).convert("RGB")
    ow, oh = int(width * oversize), int(height * oversize)
    src_ratio = img.width / img.height
    dst_ratio = ow / oh
    if src_ratio > dst_ratio:
        new_h = oh
        new_w = max(ow, int(oh * src_ratio))
    else:
        new_w = ow
        new_h = max(oh, int(ow / src_ratio))
    img = img.resize((new_w, new_h))
    left = (new_w - ow) // 2
    top = (new_h - oh) // 2
    return img.crop((left, top, left + ow, top + oh))


def grade_photo(img, niche_name, silhouette=False):
    """
    Darkens/tints a real photo toward this niche's established mood
    palette so ANY real photo (regardless of its own original lighting)
    still gives the character enough contrast to read against it, and
    stays visually consistent with this channel's dark aesthetic --
    same grading principle already applied to the procedurally-drawn
    background, just applied to a real photo instead of a flat-shape
    render. silhouette=True darkens further since a pure-black cutout
    character needs stronger contrast than a lit-color one.
    """
    tint = NICHE_BG_TINT.get(niche_name, NICHE_BG_TINT["dark_horror"])
    img = ImageEnhance.Brightness(img).enhance(0.38 if silhouette else 0.55)
    img = ImageEnhance.Contrast(img).enhance(1.15)
    overlay = Image.new("RGB", img.size, tint)
    return Image.blend(img, overlay, 0.4 if silhouette else 0.3)
