"""
Wikimedia Commons integration — real photographs of real, named cases,
used ahead of generic mood-keyword stock photos.

Direct user request: once Ch1's topics name an actual historical case
(a real person, cult, or event — see master_pipeline.py's niche
"topics" lists and the fresh_topic_ideas real-case validator), the
background imagery should be a real photo of that actual case wherever
one exists, not a generic "dark corridor" stock mood shot standing in
for it.

Free, keyless, no signup required. Wikimedia's API etiquette policy
requires a descriptive User-Agent identifying the caller (unauthenticated
requests without one get throttled/blocked) -- set below.

If nothing matches, or Commons is unreachable, this returns (False, None)
so callers fall straight through to their existing stock-photo fallback,
unchanged -- this module only ever ADDS a better real-photo option, it
is never required for the pipeline to keep working.
"""
import requests

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = ("NoKnownCause-VideoPipeline/1.0 "
              "(https://github.com/BetrayalDeepDive/betrayal-bot; automation)")


def search_wikimedia_commons(query, out_path, min_bytes=20000):
    """
    Searches Commons' File namespace for `query`, downloads the first
    real photographic (non-SVG, non-diagram) result to `out_path`.
    Returns (True, license_short_name) on success, (False, None) on any
    failure or no match.
    """
    if not query or not query.strip():
        return False, None
    headers = {"User-Agent": USER_AGENT}
    try:
        search_r = requests.get(COMMONS_API, params={
            "action": "query", "list": "search", "srnamespace": 6,
            "srsearch": query, "srlimit": 5, "format": "json",
        }, headers=headers, timeout=20)
        if search_r.status_code != 200:
            return False, None
        hits = search_r.json().get("query", {}).get("search", [])
        if not hits:
            return False, None

        for hit in hits:
            title = hit.get("title")
            if not title:
                continue
            info_r = requests.get(COMMONS_API, params={
                "action": "query", "titles": title, "prop": "imageinfo",
                "iiprop": "url|extmetadata|mime", "format": "json",
            }, headers=headers, timeout=20)
            if info_r.status_code != 200:
                continue
            pages = info_r.json().get("query", {}).get("pages", {})
            for page in pages.values():
                imageinfo = page.get("imageinfo")
                if not imageinfo:
                    continue
                info = imageinfo[0]
                mime = info.get("mime", "")
                if not mime.startswith("image/") or mime == "image/svg+xml":
                    continue  # skip diagrams/audio/video/vector files
                img_url = info.get("url")
                if not img_url:
                    continue
                license_short = (info.get("extmetadata", {})
                                  .get("LicenseShortName", {}).get("value", "unknown"))
                img_r = requests.get(img_url, headers=headers, timeout=30)
                if img_r.status_code == 200 and len(img_r.content) > min_bytes:
                    with open(out_path, "wb") as f:
                        f.write(img_r.content)
                    return True, license_short
        return False, None
    except Exception:
        return False, None
