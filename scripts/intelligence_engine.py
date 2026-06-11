"""
intelligence_engine.py
=======================
THE BRAIN OF THE EMPIRE.

Every day this runs first and answers:
1. What topics are trending RIGHT NOW across all niches?
2. What content formats are going viral on Instagram Reels and YouTube Shorts?
3. What did OUR content do this week — what worked, what didn't?
4. What should we make TODAY for maximum views + engagement?
5. What brands are spending on sponsorships in our niche right now?

Data sources (all free):
- YouTube Data API v3 (trending videos, competitor analysis)
- Reddit API (trending topics in r/india, r/truecrime, r/relationships, r/worldnews)
- Google Trends RSS (free, no API key needed)
- NewsAPI (trending stories)
- Instagram Graph API (own account performance)
- Groq AI (pattern analysis + content strategy)

Output: intelligence_report.json — used by all other scripts
"""

import os, json, re, requests, logging
from datetime import datetime, timedelta, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s [BRAIN] %(message)s")
log = logging.getLogger(__name__)

GROQ_KEY    = os.environ.get("GROQ_API_KEY", "")
YT_API_KEY  = os.environ.get("YOUTUBE_DATA_API_KEY", "")
NEWS_KEY    = os.environ.get("NEWS_API_KEY", "")
IG_TOKEN    = os.environ.get("IG_ACCESS_TOKEN", "")
IG_USER_ID  = os.environ.get("IG_USER_ID", "")
OUTPUT_DIR  = os.environ.get("OUTPUT_DIR", "/tmp/empire_output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

GROQ_MODEL = "llama-3.3-70b-versatile"

# ── Niche categories the algorithm will pick from dynamically ─────────────────
ALL_NICHES = [
    "betrayal_true_crime",      # core niche
    "relationship_drama",       # high India engagement
    "business_fraud",           # high US/UK RPM
    "family_secrets",           # emotional, shareable
    "celebrity_scandal",        # high virality
    "psychological_thriller",   # high retention
    "social_justice",           # high shares
    "financial_crimes",         # high RPM
    "political_drama",          # trending in India
    "inspirational_comeback",   # positive hook, broad appeal
]

def groq(prompt: str, max_tokens: int = 1500, temp: float = 0.4) -> str:
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
        json={"model": GROQ_MODEL, "messages": [{"role": "user", "content": prompt}],
              "max_tokens": max_tokens, "temperature": temp},
        timeout=45
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


# ── 1. Google Trends (free, no API key) ───────────────────────────────────────
def get_google_trends() -> list:
    """Gets trending searches from Google Trends RSS feed — completely free."""
    trends = []
    urls = [
        "https://trends.google.com/trends/trendingsearches/daily/rss?geo=IN",  # India
        "https://trends.google.com/trends/trendingsearches/daily/rss?geo=US",  # US
    ]
    for url in urls:
        try:
            r = requests.get(url, timeout=15,
                headers={"User-Agent": "Mozilla/5.0 (compatible; TrendBot/1.0)"})
            if r.status_code == 200:
                titles = re.findall(r"<title><!\[CDATA\[(.*?)\]\]></title>", r.text)
                trends.extend(titles[:10])
        except Exception as e:
            log.warning("Trends fetch failed: %s", e)
    log.info("Google Trends collected: %d", len(trends))
    return list(dict.fromkeys(trends))[:20]


# ── 2. Reddit trending (free, no auth needed for public posts) ────────────────
def get_reddit_trends() -> list:
    """Gets hot posts from relevant subreddits."""
    subreddits = ["india", "truecrime", "relationship_advice", "worldnews", "bollywood"]
    posts = []
    headers = {"User-Agent": "TrendBot/1.0"}
    for sub in subreddits:
        try:
            r = requests.get(
                f"https://www.reddit.com/r/{sub}/hot.json?limit=5",
                headers=headers, timeout=15
            )
            if r.status_code == 200:
                for post in r.json()["data"]["children"]:
                    d = post["data"]
                    posts.append({
                        "title":  d.get("title", ""),
                        "score":  d.get("score", 0),
                        "sub":    sub,
                        "comments": d.get("num_comments", 0),
                    })
        except Exception as e:
            log.warning("Reddit %s failed: %s", sub, e)
    posts.sort(key=lambda x: x["score"], reverse=True)
    log.info("Reddit trends: %d posts", len(posts))
    return posts[:15]


# ── 3. NewsAPI trending stories ───────────────────────────────────────────────
def get_news_trends() -> list:
    """Gets trending news stories relevant to our niches."""
    if not NEWS_KEY:
        return []
    queries = ["betrayal fraud India", "shocking crime India", "relationship scandal"]
    articles = []
    for q in queries:
        try:
            r = requests.get(
                "https://newsapi.org/v2/everything",
                params={"q": q, "language": "en", "sortBy": "publishedAt",
                        "pageSize": 5, "apiKey": NEWS_KEY},
                timeout=15
            )
            if r.status_code == 200:
                for a in r.json().get("articles", []):
                    articles.append({"title": a["title"], "source": a["source"]["name"]})
        except Exception as e:
            log.warning("News fetch failed: %s", e)
    return articles[:10]


# ── 4. YouTube viral Shorts scanner ──────────────────────────────────────────
def get_viral_youtube_shorts() -> list:
    """Scans YouTube for Shorts with 2M+ views in betrayal/drama niches."""
    if not YT_API_KEY:
        return []
    viral = []
    queries = [
        "betrayal story shorts", "true crime shorts viral",
        "relationship drama reels", "shocking story india shorts"
    ]
    for q in queries:
        try:
            r = requests.get("https://www.googleapis.com/youtube/v3/search", params={
                "key": YT_API_KEY, "q": q, "part": "id,snippet",
                "type": "video", "videoDuration": "short",
                "order": "viewCount", "maxResults": 5,
                "publishedAfter": (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }, timeout=20)
            if r.status_code == 200:
                for item in r.json().get("items", []):
                    vid_id = item["id"].get("videoId", "")
                    title  = item["snippet"].get("title", "")
                    if vid_id and title:
                        viral.append({"video_id": vid_id, "title": title,
                                      "url": f"https://youtube.com/shorts/{vid_id}"})
        except Exception as e:
            log.warning("YT viral scan failed: %s", e)
    log.info("Viral Shorts found: %d", len(viral))
    return viral[:10]


# ── 5. Own Instagram performance ──────────────────────────────────────────────
def get_own_ig_performance() -> dict:
    """Gets our own Instagram account performance metrics."""
    if not IG_TOKEN or not IG_USER_ID:
        return {}
    try:
        # Get recent media
        r = requests.get(
            f"https://graph.instagram.com/v19.0/{IG_USER_ID}/media",
            params={"fields": "id,media_type,timestamp,like_count,comments_count,caption",
                    "access_token": IG_TOKEN, "limit": 14},
            timeout=20
        )
        if r.status_code != 200:
            return {}
        media = r.json().get("data", [])
        if not media:
            return {"status": "no_posts_yet", "posts": 0}

        total_likes    = sum(m.get("like_count", 0) for m in media)
        total_comments = sum(m.get("comments_count", 0) for m in media)
        best_post      = max(media, key=lambda x: x.get("like_count", 0))

        return {
            "total_posts":    len(media),
            "total_likes":    total_likes,
            "total_comments": total_comments,
            "avg_likes":      round(total_likes / max(len(media), 1)),
            "best_post":      best_post.get("caption", "")[:100],
            "best_likes":     best_post.get("like_count", 0),
        }
    except Exception as e:
        log.warning("IG performance: %s", e)
        return {}


# ── 6. AI Strategy Generation ─────────────────────────────────────────────────
def generate_daily_strategy(trends: dict, ig_perf: dict) -> dict:
    """
    Uses all intelligence to generate today's content strategy.
    Decides: what niches, what topics, what format, what hook style.
    """
    prompt = f"""You are the chief content strategist for a $100M YouTube + Instagram empire.

TODAY'S INTELLIGENCE DATA:
Google Trends (India + US): {json.dumps(trends.get('google', [])[:10])}
Reddit Hot Posts: {json.dumps([p['title'] for p in trends.get('reddit', [])[:8]])}
News Trends: {json.dumps([n['title'] for n in trends.get('news', [])[:5]])}
Viral YT Shorts: {json.dumps([v['title'] for v in trends.get('viral_shorts', [])[:5]])}

OUR INSTAGRAM PERFORMANCE (last 14 posts):
{json.dumps(ig_perf) if ig_perf else "New account — no data yet. Focus on maximum virality."}

AVAILABLE NICHES: {json.dumps(ALL_NICHES)}

YOUR JOB: Generate today's content plan for maximum viral reach.

Goals:
- Instagram India: 500K followers in 6 months (need 2 Reels/day)
- YouTube Shorts US/UK: 500K subscribers in 6 months (need 2 Shorts/day)
- Pinterest: passive affiliate income (5 pins/day)
- All content must be shareable, emotionally triggering, algorithm-friendly

Return ONLY valid JSON:
{{
  "trending_angle_today": "The single most viral topic angle RIGHT NOW based on all data",
  "niche_1": {{
    "niche": "niche name",
    "topic": "Specific story/topic for Reel 1 today",
    "hook": "First 5 words — must stop scroll",
    "why_viral": "Why this will go viral today",
    "target": "india_hindi OR india_english OR global_english",
    "format": "shocking_reveal OR emotional_story OR psychological_twist OR justice_served"
  }},
  "niche_2": {{
    "niche": "different niche from niche_1",
    "topic": "Specific story/topic for Reel 2 today",
    "hook": "First 5 words",
    "why_viral": "Why this will go viral",
    "target": "india_hindi OR india_english OR global_english",
    "format": "shocking_reveal OR emotional_story OR psychological_twist OR justice_served"
  }},
  "pinterest_topics": ["pin topic 1", "pin topic 2", "pin topic 3", "pin topic 4", "pin topic 5"],
  "instagram_story_idea": "Simple story card idea for today",
  "algorithm_prediction": "What content will perform best this week based on trends",
  "brand_opportunity": "Any brand/sponsor category that aligns with today's trends",
  "collab_accounts": ["@account1", "@account2"],
  "hindi_caption_topics": ["topic 1 for Hindi caption", "topic 2"],
  "confidence_score": 85
}}"""

    raw = groq(prompt, max_tokens=2000, temp=0.5)
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except Exception:
        log.error("Strategy JSON parse failed")
        return {"trending_angle_today": "betrayal story India", "confidence_score": 50}


# ── 7. Brand opportunity scanner ──────────────────────────────────────────────
def scan_brand_opportunities(followers_estimate: int = 0) -> list:
    """
    Identifies brand sponsorship opportunities based on current following.
    Returns list of actionable brand deal opportunities.
    """
    prompt = f"""We run a betrayal/true crime/drama content account.
Estimated followers: {followers_estimate}
Niches covered: true crime, betrayal, psychology, relationships, justice, Indian drama

List 5 global brands that would pay for sponsorships on this type of account.
Focus on brands that sponsor true crime, psychology, or drama content.
Include realistic payment ranges at {followers_estimate} followers.

Return ONLY valid JSON array:
[
  {{
    "brand_category": "VPN Services",
    "example_brands": ["NordVPN", "ExpressVPN", "Surfshark"],
    "why_fit": "True crime audience highly receptive to privacy/security products",
    "payment_range": "$200-$800 per post at 10K followers",
    "how_to_pitch": "Email their influencer marketing team with your media kit"
  }}
]
Return exactly 5 objects."""

    raw = groq(prompt, max_tokens=1200, temp=0.3)
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except Exception:
        return []


# ── Main intelligence run ──────────────────────────────────────────────────────
def run_intelligence() -> dict:
    log.info("=" * 60)
    log.info("INTELLIGENCE ENGINE — DAILY SCAN")
    log.info("=" * 60)

    # Collect all data
    google_trends  = get_google_trends()
    reddit_trends  = get_reddit_trends()
    news_trends    = get_news_trends()
    viral_shorts   = get_viral_youtube_shorts()
    ig_performance = get_own_ig_performance()

    trends = {
        "google":        google_trends,
        "reddit":        reddit_trends,
        "news":          news_trends,
        "viral_shorts":  viral_shorts,
    }

    # Generate strategy
    strategy = generate_daily_strategy(trends, ig_performance)

    # Get brand opportunities
    followers = ig_performance.get("total_posts", 0) * 50  # rough estimate
    brands = scan_brand_opportunities(followers)

    # Final report
    report = {
        "timestamp":       datetime.now().isoformat(),
        "raw_trends":      trends,
        "ig_performance":  ig_performance,
        "daily_strategy":  strategy,
        "brand_opportunities": brands,
        "top_google_trends":   google_trends[:5],
        "top_reddit_posts":    [p["title"] for p in reddit_trends[:5]],
        "viral_shorts_today":  viral_shorts[:5],
    }

    # Save report
    path = os.path.join(OUTPUT_DIR, "intelligence_report.json")
    with open(path, "w") as f:
        json.dump(report, f, indent=2)

    log.info("✅ Intelligence scan complete")
    log.info("   Trending angle: %s", strategy.get("trending_angle_today", "")[:60])
    log.info("   Confidence: %d%%", strategy.get("confidence_score", 0))
    log.info("   Brand opps: %d", len(brands))

    return report


if __name__ == "__main__":
    report = run_intelligence()
    print(json.dumps(report["daily_strategy"], indent=2))
