"""
Daily competitor research — real, per-niche competitive intelligence
refreshed once per calendar day, feeding real patterns into that same
day's script/title/thumbnail generation.

Distinct from two systems that already exist in this codebase:
- run_viral_intelligence() (per-channel): an AI call asked to "analyze
  the top 20 viral videos," grounded in a handful of real titles as
  context when a token is available, but the actual "patterns" it
  returns (hook formulas, retention hooks, etc.) are still AI-invented,
  and it's cached for 7 days — weekly, not daily.
- weekly_report.py's get_competitor_videos()/analyse_competitor_patterns():
  real data, but channel-wide and weekly, feeding the FOLLOWING week's
  strategy file rather than the SAME day's generation.

This module fetches real video statistics (views, likes) for the
niche's actual current top-performing videos via the YouTube Data API,
and extracts patterns deterministically — real word-frequency analysis
over real titles, not an AI guess — so "what's working today" is
genuinely measured, not imagined. Thumbnail signal is limited to real
thumbnail URLs and the channel/view context around them; no vision-model
image analysis is performed (none exists elsewhere in this codebase to
build on safely within scope).
"""
import json
import datetime
import requests
from pathlib import Path
from collections import Counter

YT_DATA_URL = "https://www.googleapis.com/youtube/v3"

_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "this", "that", "was", "were", "had",
    "have", "it", "its", "he", "she", "they", "their", "his", "her",
    "be", "been", "not", "no", "so", "as", "if", "then", "than", "when",
    "what", "who", "how", "why", "you", "your", "will", "did", "did",
}


def _cache_file(cache_dir):
    return Path(cache_dir) / "daily_competitor_research.json"


def _load_cache(cache_dir):
    f = _cache_file(cache_dir)
    if not f.exists():
        return {}
    try:
        data = json.loads(f.read_text())
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_cache(cache_dir, data):
    f = _cache_file(cache_dir)
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(data, indent=2))
    except Exception:
        pass


def fetch_daily_competitor_research(niche, token, cache_dir):
    """
    Real, per-niche, once-a-day competitive research.

    Returns a dict:
      {"videos": [{"title","channel_title","thumbnail_url","views","likes"}, ...],
       "common_title_words": [...],
       "avg_views": float or None, "avg_likes": float or None,
       "research_block": "<text ready to splice into a generation prompt>"}

    Cached per calendar day per niche in cache_dir/daily_competitor_research.json
    — a retry later the same day reuses the cached result instead of
    re-hitting the API. Fails safe (empty result) on any error or a
    missing token; never blocks generation.
    """
    name = niche["name"]
    today = datetime.date.today().isoformat()
    cache = _load_cache(cache_dir)
    cached = cache.get(name)
    if cached and cached.get("date") == today:
        return cached["data"]

    result = {"videos": [], "common_title_words": [], "avg_views": None,
              "avg_likes": None, "research_block": ""}
    if not token:
        return result

    try:
        published_after = (datetime.datetime.utcnow() -
                            datetime.timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%SZ")
        r = requests.get(f"{YT_DATA_URL}/search",
            headers={"Authorization": f"Bearer {token}"},
            params={"part": "snippet", "q": niche.get("viral_search", niche["name"]),
                    "type": "video", "order": "viewCount", "publishedAfter": published_after,
                    "videoDuration": "long", "maxResults": 10, "relevanceLanguage": "en"},
            timeout=20)
        if r.status_code != 200:
            return result
        items = r.json().get("items", [])
        video_ids = [i["id"]["videoId"] for i in items if i.get("id", {}).get("videoId")]
        if not video_ids:
            return result

        r2 = requests.get(f"{YT_DATA_URL}/videos",
            headers={"Authorization": f"Bearer {token}"},
            params={"part": "snippet,statistics", "id": ",".join(video_ids)},
            timeout=20)
        if r2.status_code != 200:
            return result
        vids = r2.json().get("items", [])

        videos = []
        for v in vids:
            snip = v.get("snippet", {})
            stats = v.get("statistics", {})
            videos.append({
                "title":         snip.get("title", ""),
                "channel_title": snip.get("channelTitle", ""),
                "thumbnail_url": snip.get("thumbnails", {}).get("high", {}).get("url", ""),
                "views":         int(stats.get("viewCount", 0) or 0),
                "likes":         int(stats.get("likeCount", 0) or 0),
            })
        videos.sort(key=lambda v: v["views"], reverse=True)
        result["videos"] = videos

        if videos:
            result["avg_views"] = sum(v["views"] for v in videos) / len(videos)
            result["avg_likes"] = sum(v["likes"] for v in videos) / len(videos)

        all_words = []
        for v in videos:
            all_words += [w.strip(".,!?:;\"'").lower() for w in v["title"].split()
                          if len(w) > 3 and w.strip(".,!?:;\"'").lower() not in _STOPWORDS]
        result["common_title_words"] = [w for w, _ in Counter(all_words).most_common(8)]

        lines = ["REAL COMPETITOR RESEARCH — TODAY'S TOP PERFORMING VIDEOS IN THIS NICHE "
                 "(last 14 days, real YouTube data, not invented):"]
        for v in videos[:5]:
            lines.append(f'  - "{v["title"]}" ({v["channel_title"]}) — '
                         f'{v["views"]:,} views, {v["likes"]:,} likes')
        if result["common_title_words"]:
            lines.append(f"Common words across today's top titles: {', '.join(result['common_title_words'])}")
        result["research_block"] = "\n".join(lines)
    except Exception:
        pass

    cache[name] = {"date": today, "data": result}
    _save_cache(cache_dir, cache)
    return result
