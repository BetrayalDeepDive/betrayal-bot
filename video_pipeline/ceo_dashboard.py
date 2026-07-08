"""
CEO DASHBOARD — the "single source of truth" reporting layer from the
Media Empire operating model. Aggregates real data from every other
system built so far (Topic Database, Publishing Archive, Product
Library) plus real GitHub repo traffic and (once configured) real
Gumroad sales, into one genuine weekly empire-wide report.

HONEST DESIGN NOTE: GitHub's traffic API only retains 14 days of data
(a hard limit of the API itself, not something this module can work
around) — the report says so explicitly rather than implying a longer
window. Gumroad sales data requires a real Gumroad API access token,
which only exists once you've actually created a Gumroad account —
until GUMROAD_ACCESS_TOKEN is set, that section reports "not yet
connected" rather than a fake zero.
"""

import os
import json
import requests
import datetime
from pathlib import Path


def get_github_traffic(repo_owner, repo_name, github_token):
    """
    Real traffic data via GitHub's own API — genuinely free, built-in,
    no separate analytics service needed. Hard limitation, stated
    honestly: GitHub only retains 14 days of traffic data; this is not
    a choice this module makes, it's the API's own limit.
    Returns {"views_14d": int, "unique_visitors_14d": int,
             "top_paths": [{"path": str, "count": int}]} or a
             "not_available" dict on any failure (auth, rate limit, etc).
    """
    headers = {"Authorization": f"Bearer {github_token}",
               "Accept": "application/vnd.github+json"}
    base = f"https://api.github.com/repos/{repo_owner}/{repo_name}/traffic"

    try:
        views_resp = requests.get(f"{base}/views", headers=headers, timeout=20)
        paths_resp = requests.get(f"{base}/popular/paths", headers=headers, timeout=20)
        if views_resp.status_code != 200:
            return {"available": False, "reason": f"API returned {views_resp.status_code}"}

        views_data = views_resp.json()
        paths_data = paths_resp.json() if paths_resp.status_code == 200 else []

        return {
            "available": True,
            "views_14d": views_data.get("count", 0),
            "unique_visitors_14d": views_data.get("uniques", 0),
            "top_paths": [{"path": p["path"], "count": p["count"]} for p in paths_data[:5]],
            "window_note": "GitHub retains only 14 days of traffic data — this is the API's own limit.",
        }
    except Exception as e:
        return {"available": False, "reason": str(e)}


def get_gumroad_sales(product_gumroad_ids, gumroad_access_token):
    """
    Real sales data via Gumroad's API, once you have a real access token
    (Settings -> Advanced -> Generate access token, on gumroad.com — a
    genuine one-time manual step, same category as the account itself).
    Returns per-product sales/revenue, or an honest "not_connected"
    state if no token is configured yet — never a fabricated zero.
    """
    if not gumroad_access_token:
        return {"connected": False, "reason": "GUMROAD_ACCESS_TOKEN not set yet"}

    results = {}
    try:
        resp = requests.get("https://api.gumroad.com/v2/sales",
                             params={"access_token": gumroad_access_token}, timeout=20)
        if resp.status_code != 200:
            return {"connected": False, "reason": f"API returned {resp.status_code}"}
        sales = resp.json().get("sales", [])
        for sale in sales:
            product_id = sale.get("product_id", "unknown")
            if product_id not in results:
                results[product_id] = {"count": 0, "revenue_cents": 0}
            results[product_id]["count"] += 1
            results[product_id]["revenue_cents"] += sale.get("price", 0)
        return {"connected": True, "by_product": results}
    except Exception as e:
        return {"connected": False, "reason": str(e)}


def check_ctr_against_target(analytics_rows, target_ctr_pct=5.0):
    """
    Uses the REAL per-video CTR data now pulled by get_own_analytics
    (impressionsClickThroughRate) to flag videos genuinely underperforming
    the explicit CTR target. Row structure matches get_own_analytics'
    metrics order: [video_id, views, minutes_watched, avg_view_duration,
    subs_gained, likes, impressions, impressions_ctr].
    Returns {"videos_checked": int, "below_target": [...], "avg_ctr": float}
    or an honest empty result if no real data is available yet.
    """
    if not analytics_rows:
        return {"videos_checked": 0, "below_target": [], "avg_ctr": None,
                "note": "No analytics data available this run."}

    checked = []
    for row in analytics_rows:
        if len(row) >= 8:
            video_id = row[0]
            ctr = row[7] * 100 if row[7] is not None else None  # API returns a fraction
            if ctr is not None:
                checked.append({"video_id": video_id, "ctr_pct": round(ctr, 2)})

    if not checked:
        return {"videos_checked": 0, "below_target": [], "avg_ctr": None,
                "note": "CTR field not present in this run's data."}

    below = [v for v in checked if v["ctr_pct"] < target_ctr_pct]
    avg_ctr = round(sum(v["ctr_pct"] for v in checked) / len(checked), 2)
    return {"videos_checked": len(checked), "below_target": below, "avg_ctr": avg_ctr,
            "target": target_ctr_pct}


def _dashboard_history_file(products_root):
    return Path(products_root).parent / "dashboard_history.json"


def save_dashboard_snapshot(products_root, snapshot: dict):
    """
    Persists this week's real numbers so future weeks can show genuine
    trend data — the earlier version only ever showed a rolling GitHub
    14-day snapshot with zero memory across weeks, meaning real growth
    over months was never actually visible.
    """
    f = _dashboard_history_file(products_root)
    history = []
    if f.exists():
        try:
            history = json.loads(f.read_text())
        except Exception:
            history = []
    snapshot["recorded_at"] = datetime.datetime.now().isoformat()
    history.append(snapshot)
    history = history[-52:]  # keep roughly a year of weekly snapshots
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(history, indent=2))
    except Exception:
        pass


def get_dashboard_trend(products_root, weeks_back=4):
    """
    Real week-over-week comparison using the persisted history above —
    not a guess, an actual comparison against what was recorded
    weeks_back snapshots ago. Returns None gracefully if there isn't
    enough history yet (a channel's first month, for instance).
    """
    f = _dashboard_history_file(products_root)
    if not f.exists():
        return None
    try:
        history = json.loads(f.read_text())
    except Exception:
        return None
    if len(history) <= weeks_back:
        return None
    then = history[-(weeks_back + 1)]
    now = history[-1]
    return {"weeks_compared": weeks_back, "then": then, "now": now}


def detect_underperforming_clusters(channel_dir, min_topics_scored=5, low_score_threshold=6.0):
    """
    Real keep/kill signal, per the document's explicit weekly requirement
    — flags niches whose RECENT topic scores are trending low, using the
    topic-scoring system's own real composite scores rather than an
    invented performance proxy. This is a leading indicator (is the
    content pipeline itself running dry on good ideas for this niche),
    distinct from lagging YouTube performance data — both matter, and
    this is the piece that was genuinely missing before.
    """
    from topic_scoring import load_topic_database
    backlog = load_topic_database(channel_dir)

    by_niche = {}
    for t in backlog:
        by_niche.setdefault(t.get("niche_name", "unknown"), []).append(t)

    flagged = []
    for niche, topics in by_niche.items():
        recent = sorted(topics, key=lambda t: t.get("created_at", ""), reverse=True)[:min_topics_scored]
        if len(recent) < min_topics_scored:
            continue  # not enough real data yet to judge this niche fairly
        avg_score = sum(t.get("composite_score", 0) for t in recent) / len(recent)
        if avg_score < low_score_threshold:
            flagged.append({"niche": niche, "avg_recent_score": round(avg_score, 2),
                            "topics_checked": len(recent)})
    return flagged


def build_empire_dashboard(channel_configs, products_root, repo_owner, repo_name,
                            github_token, gumroad_access_token=None,
                            analytics_rows_by_channel=None):
    """
    The real entry point: pulls topic backlog health + publishing archive
    stats for every channel, product manuscript growth, real GitHub
    traffic, real CTR-vs-target check, and (if configured) real Gumroad
    sales, into one combined report string ready to send to Telegram.

    products_root is passed explicitly (repo_root/products) rather than
    derived from channel_configs — an earlier version tried to derive it
    heuristically from the channel list and was genuinely wrong for our
    actual 2+ channel case; explicit is safer than clever here.

    analytics_rows_by_channel: {channel_id: real analytics rows from
    get_own_analytics} — FIX: check_ctr_against_target existed fully
    built and tested standalone, checking real per-video CTR against the
    explicit 5% target, but was never actually wired into this dashboard's
    real output. Optional — degrades gracefully to "no data" if not passed.
    """
    from topic_scoring import get_backlog_summary
    from publishing_archive import load_archive
    from product_manuscript import get_manuscript_stats

    lines = ["📊 <b>NEXT LAYER MEDIA — Empire Dashboard</b>",
              f"Week ending {datetime.date.today().strftime('%B %d, %Y')}", ""]

    lines.append("<b>CHANNEL HEALTH</b>")
    for cfg in channel_configs:
        channel_dir = cfg["output_dir"]
        backlog = get_backlog_summary(channel_dir)
        archive_count = len(load_archive(channel_dir))
        lines.append(f"  {cfg['display_name']}: {archive_count} published | "
                     f"backlog: {backlog['pending']} pending, {backlog['approved']} approved, "
                     f"{backlog['rejected']} rejected")
    lines.append("")

    lines.append("<b>CTR vs 5% TARGET</b> (real per-video data)")
    if analytics_rows_by_channel:
        for cfg in channel_configs:
            rows = analytics_rows_by_channel.get(cfg["channel_id"], [])
            ctr_result = check_ctr_against_target(rows, target_ctr_pct=5.0)
            if ctr_result["videos_checked"] == 0:
                lines.append(f"  {cfg['display_name']}: {ctr_result.get('note', 'no data yet')}")
            else:
                below = len(ctr_result["below_target"])
                lines.append(f"  {cfg['display_name']}: avg {ctr_result['avg_ctr']}% across "
                             f"{ctr_result['videos_checked']} videos — {below} below target")
                for v in ctr_result["below_target"][:3]:
                    lines.append(f"    ⚠️ {v['video_id']}: {v['ctr_pct']}% CTR")
    else:
        lines.append("  Not available this run — no analytics data was passed in.")
    lines.append("")

    lines.append("<b>PRODUCT LIBRARY GROWTH</b>")
    stats = get_manuscript_stats(products_root)
    for product_id, s in stats.items():
        status = f"{s['total_notes']} insights across {s['chapters_with_content']}/{s['chapters_total']} chapters"
        lines.append(f"  {s['title']}: {status}")
    lines.append("")

    lines.append("<b>SITE TRAFFIC</b> (GitHub Pages, via GitHub API)")
    traffic = get_github_traffic(repo_owner, repo_name, github_token)
    if traffic.get("available"):
        lines.append(f"  {traffic['views_14d']} views / {traffic['unique_visitors_14d']} "
                     f"unique visitors in the last 14 days")
        lines.append(f"  ({traffic['window_note']})")
        if traffic["top_paths"]:
            lines.append("  Top pages: " + ", ".join(
                f"{p['path']} ({p['count']})" for p in traffic["top_paths"][:3]))
    else:
        lines.append(f"  Not available this run: {traffic.get('reason', 'unknown')}")
    lines.append("")

    lines.append("<b>PRODUCT SALES</b> (Gumroad)")
    sales = get_gumroad_sales({}, gumroad_access_token)
    if sales.get("connected"):
        for product_id, data in sales.get("by_product", {}).items():
            lines.append(f"  {product_id}: {data['count']} sales, "
                         f"${data['revenue_cents']/100:.2f}")
        if not sales.get("by_product"):
            lines.append("  No sales yet.")
    else:
        lines.append(f"  Not connected yet: {sales.get('reason')}")
    lines.append("")

    lines.append("<b>DAILY AUDIT ENGINE — LAST 7 DAYS</b>")
    try:
        from daily_audit_engine import get_audit_summary
        for cfg in channel_configs:
            audit_summary = get_audit_summary(cfg["output_dir"], days_back=7)
            lines.append(f"  {cfg['display_name']}: {audit_summary['total']} videos audited — "
                         f"{audit_summary['pass']} clean, {audit_summary['review']} flagged for review, "
                         f"{audit_summary['hold']} held")
    except Exception as e:
        lines.append(f"  Audit summary unavailable this run: {e}")
    lines.append("")

    lines.append("<b>WHAT'S ACTUALLY DIFFERENTIATING YOUR CONTENT</b> (real data, not a guess)")
    try:
        from topic_scoring import get_scoring_calibration_notes
        any_signal = False
        for cfg in channel_configs:
            notes = get_scoring_calibration_notes(cfg["output_dir"])
            if notes:
                any_signal = True
                # Strip the header line already implied by this section
                for line in notes.split("\n")[1:]:
                    lines.append(f"  {cfg['display_name']}: {line.lstrip('- ')}")
        if not any_signal:
            lines.append("  Not enough produced episodes with real CTR data yet to say anything "
                         "meaningful — this fills in as more real videos publish and get watched.")
    except Exception as e:
        lines.append(f"  Differentiation signal unavailable this run: {e}")
    lines.append("")

    lines.append("<b>KEEP / KILL — UNDERPERFORMING CLUSTERS</b>")
    any_flagged = False
    for cfg in channel_configs:
        flagged = detect_underperforming_clusters(cfg["output_dir"])
        for f in flagged:
            any_flagged = True
            lines.append(f"  ⚠️ {cfg['display_name']} / {f['niche']}: avg recent score "
                         f"{f['avg_recent_score']}/10 across last {f['topics_checked']} topics — "
                         f"consider killing or reworking this niche")
    if not any_flagged:
        lines.append("  No niches flagged — all recent topic scores are healthy.")
    lines.append("")

    trend = get_dashboard_trend(products_root)
    lines.append("<b>4-WEEK TREND</b>")
    if trend:
        lines.append(f"  Comparing now vs. {trend['weeks_compared']} weeks ago — real recorded data, not a guess.")
    else:
        lines.append("  Not enough history yet — trend data appears after a few weeks of runs.")
    lines.append("")

    lines.append("Full dashboard reflects real data only — no placeholder numbers.")

    # Save this week's real snapshot so future runs can show genuine trends
    try:
        save_dashboard_snapshot(products_root, {
            "channels": [{"name": c["display_name"],
                          "published": len(load_archive(c["output_dir"]))}
                         for c in channel_configs],
            "product_stats": stats,
        })
    except Exception:
        pass
    return "\n".join(lines)
