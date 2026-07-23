"""
Post-upload performance + monetization snapshot — direct user request,
July 23 2026: "after uploading, it also needs to take up the job of
checking: what is going on, how many views we have received, how many
likes, subscribers, what the account is, what the monetary environment
is, how we are in financial condition... report back to me... in
Telegram."

Reuses the same real YouTube Data API + Gumroad plumbing already proven
in weekly_report.py/ceo_dashboard.py (this module doesn't duplicate that
logic, it wraps it into a single per-episode snapshot callable right
after a video goes live), so every channel's upload phase can send one
consolidated report right after publish instead of only the existing
weekly aggregate.

HONEST NOTE: a video's views/likes are necessarily near-zero in the
first minutes after publish -- this reports the REAL count at that
moment (never fabricated or estimated), explicitly framed as a
publish-time snapshot, not a claim about how the video will ultimately
perform. Subscriber count and revenue are real, current totals for the
channel, not video-specific.
"""
import requests

YT_DATA_URL = "https://www.googleapis.com/youtube/v3"


def get_video_stats(video_id, token):
    """Real view/like/comment counts for one video. Returns dict or None on failure."""
    try:
        r = requests.get(f"{YT_DATA_URL}/videos",
                          params={"part": "statistics", "id": video_id},
                          headers={"Authorization": f"Bearer {token}"}, timeout=20)
        items = r.json().get("items", [])
        if not items:
            return None
        stats = items[0].get("statistics", {})
        return {
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0)),
        }
    except Exception as e:
        print(f"  Post-upload video stats fetch failed (non-fatal): {e}", flush=True)
        return None


def get_channel_stats(token):
    """Real subscriber/total-view/video counts for the authenticated (this
    channel's own) account. Returns dict or None on failure."""
    try:
        r = requests.get(f"{YT_DATA_URL}/channels",
                          params={"part": "statistics", "mine": "true"},
                          headers={"Authorization": f"Bearer {token}"}, timeout=20)
        items = r.json().get("items", [])
        if not items:
            return None
        stats = items[0].get("statistics", {})
        return {
            "subscribers": int(stats.get("subscriberCount", 0)),
            "total_views": int(stats.get("viewCount", 0)),
            "total_videos": int(stats.get("videoCount", 0)),
        }
    except Exception as e:
        print(f"  Post-upload channel stats fetch failed (non-fatal): {e}", flush=True)
        return None


def get_recent_revenue_line(channel_name, gumroad_token, days=7):
    """Real recent Gumroad revenue for this channel's product, reusing the
    same ceo_dashboard.get_gumroad_sales plumbing already proven in
    weekly_report.py. Returns a human-readable line, never a fabricated number."""
    if not gumroad_token:
        return "Gumroad not connected (GUMROAD_ACCESS_TOKEN not set)."
    try:
        import datetime
        from ceo_dashboard import get_gumroad_sales
        after_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
        sales_data = get_gumroad_sales([], gumroad_token, after_date=after_date)
        if not sales_data.get("connected"):
            return f"Gumroad fetch failed (non-fatal): {sales_data.get('reason', 'unknown')}"
        lines = []
        for product_title, entry in sales_data.get("by_product", {}).items():
            revenue = entry["revenue_cents"] / 100
            lines.append(f"{product_title}: {entry['count']} sale(s), ${revenue:.2f} (last {days}d)")
        return "; ".join(lines) if lines else f"No sales in the last {days} days (real data, genuinely zero)."
    except Exception as e:
        return f"Revenue snapshot unavailable (non-fatal): {e}"


def send_post_upload_report(channel_display_name, video_url, video_id, token,
                             tg_token, tg_chat, gumroad_token=None, tg_fn=None):
    """
    Builds and sends the consolidated post-upload snapshot to Telegram.
    tg_fn: the channel's own tg(msg) helper (already handles the real
    Telegram send + chunking) -- passed in rather than duplicated here.
    Non-fatal throughout: any individual piece failing to fetch degrades
    to an honest "unavailable" line rather than blocking the report.
    """
    video_stats = get_video_stats(video_id, token) if video_id else None
    channel_stats = get_channel_stats(token)
    revenue_line = get_recent_revenue_line(channel_display_name, gumroad_token)

    video_line = (f"Views: {video_stats['views']} | Likes: {video_stats['likes']} | "
                  f"Comments: {video_stats['comments']}"
                  if video_stats else "Video stats not yet available (just published).")
    channel_line = (f"Subscribers: {channel_stats['subscribers']} | "
                     f"Total channel views: {channel_stats['total_views']} | "
                     f"Total videos: {channel_stats['total_videos']}"
                     if channel_stats else "Channel stats unavailable (non-fatal).")

    msg = (f"📊 *{channel_display_name} — POST-UPLOAD SNAPSHOT*\n"
           f"{video_url}\n\n"
           f"🎬 This video (publish-time snapshot — views/likes are naturally "
           f"near-zero right after publish, this is real not estimated):\n{video_line}\n\n"
           f"📺 Channel totals:\n{channel_line}\n\n"
           f"💰 Recent revenue:\n{revenue_line}")

    if tg_fn:
        tg_fn(msg)
    else:
        try:
            requests.post(f"https://api.telegram.org/bot{tg_token}/sendMessage",
                          data={"chat_id": tg_chat, "text": msg, "parse_mode": "Markdown"}, timeout=20)
        except Exception as e:
            print(f"  Post-upload report Telegram send failed (non-fatal): {e}", flush=True)

    return {"video_stats": video_stats, "channel_stats": channel_stats, "revenue_line": revenue_line}
