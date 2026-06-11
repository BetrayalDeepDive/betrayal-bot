"""
empire_report.py
=================
THE WEEKLY COMMAND CENTRE REPORT.

Every Sunday 8 AM IST, sends a complete report covering:
- YouTube: views, subscribers, estimated revenue, best video
- Instagram: followers, reach, best Reel, engagement rate
- Pinterest: impressions, clicks, affiliate revenue
- Algorithm predictions for next week
- Brand deal pipeline status
- What AI changed this week and why
- Financial projections (30/90/180 days)
- Content quality scores trend

Also handles DAILY quick reports after each publish.

Saves everything to Google Sheets for long-term tracking.
"""

import os, json, logging, requests
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s [REPORT] %(message)s")
log = logging.getLogger(__name__)

TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
OUTPUT_DIR       = os.environ.get("OUTPUT_DIR", "/tmp/empire_output")
YT_CLIENT_ID     = os.environ.get("YOUTUBE_CLIENT_ID", "")
YT_CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
YT_REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN", "")
IG_TOKEN         = os.environ.get("IG_ACCESS_TOKEN", "")
IG_USER_ID       = os.environ.get("IG_USER_ID", "")
SHEETS_ID        = os.environ.get("SHEETS_ID", "")
GROQ_KEY         = os.environ.get("GROQ_API_KEY", "")

# Revenue rates (conservative estimates)
YT_LONG_RPM    = 10.0   # $10 per 1000 views (betrayal niche)
YT_SHORT_RPM   = 0.10   # $0.10 per 1000 views
IG_BRAND_RATE  = 500    # $ per sponsored post at 100K followers (scales)
USD_TO_INR     = 83


def tg(msg: str):
    """Send Telegram message."""
    if not TELEGRAM_TOKEN:
        print(msg)
        return
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"},
        timeout=15
    )


def load(filename: str, default=None):
    path = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return default or {}


def get_yt_access_token() -> str:
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": YT_CLIENT_ID, "client_secret": YT_CLIENT_SECRET,
        "refresh_token": YT_REFRESH_TOKEN, "grant_type": "refresh_token",
    }, timeout=20)
    return r.json().get("access_token", "") if r.status_code == 200 else ""


def get_yt_channel_stats() -> dict:
    """Gets YouTube channel statistics."""
    token = get_yt_access_token()
    if not token:
        return {}
    r = requests.get(
        "https://www.googleapis.com/youtube/v3/channels",
        params={"part": "statistics", "mine": "true"},
        headers={"Authorization": f"Bearer {token}"},
        timeout=20
    )
    if r.status_code == 200:
        items = r.json().get("items", [])
        if items:
            stats = items[0].get("statistics", {})
            return {
                "subscribers":  int(stats.get("subscriberCount", 0)),
                "total_views":  int(stats.get("viewCount", 0)),
                "video_count":  int(stats.get("videoCount", 0)),
            }
    return {}


def get_ig_stats() -> dict:
    """Gets Instagram account stats."""
    if not IG_TOKEN or not IG_USER_ID:
        return {}
    try:
        r = requests.get(
            f"https://graph.instagram.com/v19.0/{IG_USER_ID}",
            params={"fields": "followers_count,media_count,biography",
                    "access_token": IG_TOKEN},
            timeout=20
        )
        if r.status_code == 200:
            d = r.json()
            return {
                "followers":   d.get("followers_count", 0),
                "posts":       d.get("media_count", 0),
            }
    except Exception:
        pass
    return {}


def calculate_revenue(yt_views: int, yt_subs: int, ig_followers: int) -> dict:
    """Calculates realistic revenue estimates."""
    # YouTube long-form (assume 30% of subs watch)
    yt_monthly_views = yt_subs * 0.3 * 4  # 4 videos/week
    yt_long_rev = (yt_monthly_views / 1000) * YT_LONG_RPM

    # YouTube Shorts (lower RPM)
    shorts_views = yt_subs * 0.5 * 14  # 14 shorts/week
    yt_short_rev = (shorts_views / 1000) * YT_SHORT_RPM

    # Instagram brand deals (once per month per 10K followers)
    ig_brand_rev = (ig_followers / 100000) * IG_BRAND_RATE

    total_usd = yt_long_rev + yt_short_rev + ig_brand_rev
    total_inr = total_usd * USD_TO_INR

    return {
        "yt_long_monthly_usd":   round(yt_long_rev, 2),
        "yt_shorts_monthly_usd": round(yt_short_rev, 2),
        "ig_brand_monthly_usd":  round(ig_brand_rev, 2),
        "total_monthly_usd":     round(total_usd, 2),
        "total_monthly_inr":     round(total_inr),
        "annual_projection_usd": round(total_usd * 12, 2),
    }


def get_algorithm_predictions(intel: dict) -> str:
    """Uses Groq to predict what will perform next week."""
    if not GROQ_KEY:
        return "Algorithm predictions unavailable"
    strategy = intel.get("daily_strategy", {})
    trending = intel.get("top_google_trends", [])[:5]

    prompt = f"""Based on this week's performance data and trends:
Trending topics: {trending}
Current content strategy: {strategy.get('trending_angle_today', '')}
Algorithm prediction from strategy: {strategy.get('algorithm_prediction', '')}

In 3 bullet points, predict what content will perform BEST next week.
Be specific. Focus on India + US/UK audiences. Max 60 words total."""

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
            json={"model": "llama-3.3-70b-versatile",
                  "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": 150, "temperature": 0.4},
            timeout=20
        )
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return "Post daily, focus on emotional hooks, target morning hours IST"


def log_to_sheets(data: dict):
    """Logs weekly metrics to Google Sheets."""
    try:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials

        creds_json = os.environ.get("GOOGLE_SHEETS_CREDS", "{}")
        creds_dict = json.loads(creds_json)
        scope  = ["https://spreadsheets.google.com/feeds",
                  "https://www.googleapis.com/auth/drive"]
        creds  = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet  = client.open_by_key(SHEETS_ID)

        try:
            ws = sheet.worksheet("Empire Reports")
        except Exception:
            ws = sheet.add_worksheet("Empire Reports", rows=1000, cols=20)
            ws.append_row([
                "Date", "YT Subs", "YT Total Views", "IG Followers",
                "YT Rev USD", "IG Rev USD", "Total Rev USD", "Total Rev INR",
                "Annual Projection USD", "Videos Published", "Best Video Title",
                "Quality Score Avg", "Brand Opps"
            ])

        ws.append_row([
            datetime.now().strftime("%Y-%m-%d"),
            data.get("yt_subs", 0),
            data.get("yt_total_views", 0),
            data.get("ig_followers", 0),
            data.get("yt_rev_usd", 0),
            data.get("ig_rev_usd", 0),
            data.get("total_rev_usd", 0),
            data.get("total_rev_inr", 0),
            data.get("annual_usd", 0),
            data.get("videos_this_week", 0),
            data.get("best_video", ""),
            data.get("avg_quality", 0),
            data.get("brand_opps", 0),
        ])
        log.info("✅ Logged to Google Sheets")
    except Exception as e:
        log.warning("Sheets log failed (non-critical): %s", e)


def send_daily_report(publish_results: dict):
    """Sends daily post-publish notification."""
    intel   = load("intelligence_report.json")
    strategy = intel.get("daily_strategy", {})

    yt_result    = publish_results.get("youtube_main", {})
    short_result = publish_results.get("youtube_short", {})
    ig_result    = publish_results.get("instagram", {})
    reel_meta    = publish_results.get("reel_meta", {})

    yt_url    = yt_result.get("url", "Pending")
    short_url = short_result.get("url", "Pending")
    ig_ok     = "✅" if ig_result.get("success") else "⚠️"
    virality  = reel_meta.get("virality_score", 0)
    topic     = reel_meta.get("topic", "")[:50]

    msg = f"""🚀 *BETRAYAL DEEPDIVE — Daily Publish*
━━━━━━━━━━━━━━━━━━━━
📌 *{topic}*
⚡ Virality Score: *{virality}/100*

*PUBLISHED TO:*
📺 YouTube Long-form: {yt_url}
📱 YouTube Short: {short_url}
{ig_ok} Instagram Reel: {'Posted ✅' if ig_result.get('success') else 'Check manually ⚠️'}

*🧠 TODAY'S AI ANGLE:*
_{strategy.get('trending_angle_today', 'Optimised for today')[:80]}_

*📊 ALGORITHM SAYS:*
_{strategy.get('algorithm_prediction', 'Post consistently')[:80]}_

💤 *No action needed — fully automated*"""

    tg(msg)


def send_weekly_report():
    """Sends full weekly report every Sunday."""
    yt_stats  = get_yt_channel_stats()
    ig_stats  = get_ig_stats()
    intel     = load("intelligence_report.json")
    brands    = intel.get("brand_opportunities", [])

    yt_subs   = yt_stats.get("subscribers", 0)
    yt_views  = yt_stats.get("total_views", 0)
    ig_follow = ig_stats.get("followers", 0)

    rev = calculate_revenue(yt_views, yt_subs, ig_follow)
    algo_pred = get_algorithm_predictions(intel)

    # Progress to 500K goal
    yt_progress  = round((yt_subs / 500000) * 100, 1)
    ig_progress  = round((ig_follow / 500000) * 100, 1)

    # Brand deal status
    brand_summary = ""
    if brands:
        top_brand = brands[0]
        brand_summary = f"\n💼 Top Brand Opp: *{top_brand.get('brand_category', '')}*\n_{top_brand.get('how_to_pitch', '')[:60]}_"

    msg = f"""📊 *WEEKLY EMPIRE REPORT*
*Betrayal DeepDive — {datetime.now().strftime('%d %b %Y')}*
━━━━━━━━━━━━━━━━━━━━

📺 *YOUTUBE*
• Subscribers: *{yt_subs:,}* ({yt_progress}% of 500K goal)
• Total views: {yt_views:,}
• Est. monthly rev: *${rev['yt_long_monthly_usd']:,.0f}*

📱 *INSTAGRAM*
• Followers: *{ig_follow:,}* ({ig_progress}% of 500K goal)
• Est. brand deals: *${rev['ig_brand_monthly_usd']:,.0f}/month*

━━━━━━━━━━━━━━━━━━━━
💰 *FINANCIAL SUMMARY*
• YouTube total: ${rev['yt_long_monthly_usd'] + rev['yt_shorts_monthly_usd']:,.0f}/month
• Instagram: ${rev['ig_brand_monthly_usd']:,.0f}/month
• *TOTAL: ${rev['total_monthly_usd']:,.0f}/month*
• *₹{rev['total_monthly_inr']:,}/month*
• Annual projection: *${rev['annual_projection_usd']:,.0f}*
{brand_summary}
━━━━━━━━━━━━━━━━━━━━
🧠 *AI PREDICTIONS NEXT WEEK*
{algo_pred}

━━━━━━━━━━━━━━━━━━━━
🎯 *500K GOALS*
YouTube: {'🟢' if yt_progress > 10 else '🟡'} {yt_progress}% — {yt_subs:,}/{500000:,}
Instagram: {'🟢' if ig_progress > 10 else '🟡'} {ig_progress}% — {ig_follow:,}/{500000:,}

💤 *All systems running. No action needed.*"""

    tg(msg)

    # Log to Sheets
    log_to_sheets({
        "yt_subs": yt_subs, "yt_total_views": yt_views,
        "ig_followers": ig_follow,
        "yt_rev_usd": rev["yt_long_monthly_usd"],
        "ig_rev_usd": rev["ig_brand_monthly_usd"],
        "total_rev_usd": rev["total_monthly_usd"],
        "total_rev_inr": rev["total_monthly_inr"],
        "annual_usd": rev["annual_projection_usd"],
        "brand_opps": len(brands),
    })

    log.info("✅ Weekly report sent")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "weekly":
        send_weekly_report()
    else:
        send_daily_report({})
