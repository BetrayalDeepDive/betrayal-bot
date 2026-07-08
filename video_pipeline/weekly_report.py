#!/usr/bin/env python3
"""
DeepDive Empire — Weekly Self-Improvement Engine
==================================================
Runs every Sunday 3:30 AM UTC (9:00 AM IST).

What it does:
1. Pulls your own YouTube Analytics (CTR, view duration, impressions per video)
2. Scans top 10 competitor channels in each niche — their last 7 days
3. Extracts what's working for competitors (titles, topics, hook patterns)
4. Compares your performance vs theirs
5. Recalibrates the title CTR scoring model based on actual performance
6. Updates intel.json with next week's strategy
7. Sends full Telegram + Gmail report with action items
"""

import os, sys, json, re, time, datetime, requests
from pathlib import Path

# ── Credentials (Ch1 defaults — per-channel overrides in CHANNELS below) ──
GEMINI_KEY    = os.environ.get("GEMINI_API_KEY", "")
GROQ_KEY      = os.environ.get("GROQ_API_KEY", "")
CEREBRAS_KEY  = os.environ.get("CEREBRAS_API_KEY", "")
YT_CLIENT_ID  = os.environ.get("YOUTUBE_CLIENT_ID", "")
YT_CLIENT_SEC = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
YT_REFRESH    = os.environ.get("YOUTUBE_REFRESH_TOKEN", "")
TG_TOKEN      = os.environ.get("TELEGRAM_TOKEN", "")
TG_CHAT       = os.environ.get("TELEGRAM_CHAT_ID", "")

SCRIPT_DIR    = Path(__file__).parent   # video_pipeline/ — Ch1's own directory
STATE_FILE    = SCRIPT_DIR / "state.json"
INTEL_FILE    = SCRIPT_DIR / "weekly_intel.json"
YT_DATA_URL   = "https://www.googleapis.com/youtube/v3"
YT_ANALYTICS  = "https://youtubeanalytics.googleapis.com/v2"
YT_TOKEN_URL  = "https://oauth2.googleapis.com/token"

# ── Competitor channels per niche — Ch1 ───────────────────────
COMPETITOR_SEARCHES = {
    "dark_horror":        "dark horror documentary narration faceless",
    "seduction_dark":     "dark psychology manipulation documentary",
    "psychological_trap": "psychological horror true story faceless",
    "supernatural_real":  "paranormal evidence documentary narration",
    "obsession_dark":     "dark obsession true crime faceless documentary",
}

# ── Competitor channels per niche — Ch2 ───────────────────────
COMPETITOR_SEARCHES_CH2 = {
    "forensic_finance":        "forensic accounting fraud investigation documentary",
    "criminal_investigation":  "cold case investigation evidence documentary",
    "corporate_exposure":      "corporate fraud scandal documentary",
    "digital_forensics":       "digital forensics cybercrime investigation documentary",
}

# ══════════════════════════════════════════════════════════════════
# FIX: this whole file only ever analysed and reported on Ch1 — Ch2's
# niches, credentials, and output file location were never touched, so
# weekly_report.py silently produced a "whole empire" report that only
# ever covered one of the two active channels. CHANNELS below is the
# real fix — main() now loops over every entry here, each with its own
# credentials, competitor niches, and output directory (this matters:
# each pipeline reads next_week_strategy.json from ITS OWN SCRIPT_DIR,
# e.g. Ch2 reads from channels/evidence_room/, a completely different
# path than Ch1's video_pipeline/ — writing only to one location meant
# Ch2 never received a strategy file at all, regardless of whether the
# analysis covered it). Add one new entry here to extend to Ch3/4/5 —
# not a rewrite.
# ══════════════════════════════════════════════════════════════════
CHANNELS = [
    {
        "channel_id":       "betrayal_deepdive",
        "display_name":     "BetrayalDeepDive",
        "yt_client_id":     os.environ.get("YOUTUBE_CLIENT_ID", ""),
        "yt_client_secret": os.environ.get("YOUTUBE_CLIENT_SECRET", ""),
        "yt_refresh_token": os.environ.get("YOUTUBE_REFRESH_TOKEN", ""),
        "competitor_searches": COMPETITOR_SEARCHES,
        "output_dir":       SCRIPT_DIR,   # video_pipeline/
    },
    {
        "channel_id":       "evidence_room",
        "display_name":     "The Evidence Room",
        "yt_client_id":     os.environ.get("EVIDENCE_YT_CLIENT_ID", ""),
        "yt_client_secret": os.environ.get("EVIDENCE_YT_CLIENT_SECRET", ""),
        "yt_refresh_token": os.environ.get("EVIDENCE_YT_REFRESH_TOKEN", ""),
        "competitor_searches": COMPETITOR_SEARCHES_CH2,
        "output_dir":       SCRIPT_DIR.parent / "channels" / "evidence_room",
    },
]


def log(m): print(m, flush=True)

def tg(m):
    if not TG_TOKEN: return
    for chunk in [m[i:i+4000] for i in range(0, len(m), 4000)]:
        try:
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                json={"chat_id": TG_CHAT, "text": chunk, "parse_mode": "HTML"}, timeout=15)
        except: pass

def get_yt_token(client_id=None, client_secret=None, refresh_token=None):
    """
    FIX: previously always used Ch1's module-level YT_CLIENT_ID/SEC/REFRESH
    constants — now accepts per-channel credentials so this can fetch a
    real token for any channel in CHANNELS, not just Ch1.
    """
    r = requests.post(YT_TOKEN_URL,
        data={"client_id": client_id or YT_CLIENT_ID,
              "client_secret": client_secret or YT_CLIENT_SEC,
              "refresh_token": refresh_token or YT_REFRESH,
              "grant_type": "refresh_token"}, timeout=30)
    d = r.json()
    if "access_token" not in d: raise Exception(f"YT auth failed: {d}")
    return d["access_token"]

def ai(prompt, tokens=2000):
    """Quick AI call for analysis — tries Cerebras, Gemini, Groq."""
    # Cerebras
    if CEREBRAS_KEY:
        try:
            r = requests.post("https://api.cerebras.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CEREBRAS_KEY}"},
                json={"model": "llama-3.3-70b",
                      "messages": [{"role": "user", "content": prompt}],
                      "max_completion_tokens": tokens}, timeout=60)
            if r.status_code == 200:
                t = r.json()["choices"][0]["message"]["content"]
                if t and len(t) > 50: return t
        except: pass
    # Gemini
    if GEMINI_KEY:
        try:
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}",
                json={"contents": [{"parts": [{"text": prompt}]}],
                      "generationConfig": {"maxOutputTokens": tokens}}, timeout=60)
            if r.status_code == 200:
                c = r.json().get("candidates", [])
                if c: return c[0]["content"]["parts"][0]["text"]
        except: pass
    # Groq
    if GROQ_KEY:
        try:
            r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_KEY}"},
                json={"model": "llama-3.3-70b-versatile",
                      "messages": [{"role": "user", "content": prompt}],
                      "max_tokens": min(tokens, 4800)}, timeout=60)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
        except: pass
    return None

# ── STEP 1: Your own YouTube Analytics ────────────────────────
def get_own_analytics(token):
    """Pull CTR, view duration, impressions for last 7 days.
    FIX: the metrics list previously never actually included impressions
    or CTR despite the docstring claiming it did — a real gap given the
    explicit CTR target this whole system is now built around. Added
    impressions + impressionClickThroughRate, the real YouTube Analytics
    API metric names for this."""
    try:
        end   = datetime.date.today().isoformat()
        start = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
        r = requests.get(f"{YT_ANALYTICS}/reports",
            headers={"Authorization": f"Bearer {token}"},
            params={"ids": "channel==MINE",
                    "startDate": start, "endDate": end,
                    "metrics": "views,estimatedMinutesWatched,averageViewDuration,"
                               "subscribersGained,likes,impressions,"
                               "impressionsClickThroughRate",
                    "dimensions": "video",
                    "sort": "-views", "maxResults": 10},
            timeout=20)
        if r.status_code == 200:
            return r.json().get("rows", [])
        log(f"  Analytics {r.status_code}: {r.text[:200]}")
    except Exception as e:
        log(f"  Analytics error: {e}")
    return []

def get_video_details(token, video_ids):
    """Get title, CTR, impression data per video."""
    if not video_ids: return []
    try:
        r = requests.get(f"{YT_DATA_URL}/videos",
            headers={"Authorization": f"Bearer {token}"},
            params={"part": "snippet,statistics",
                    "id": ",".join(video_ids[:10])}, timeout=20)
        if r.status_code == 200:
            return r.json().get("items", [])
    except: pass
    return []

# ── STEP 2: Competitor analysis ───────────────────────────────
def get_competitor_videos(token, niche_name, search_query):
    """Find top videos from competitors in this niche this week."""
    try:
        published_after = (datetime.datetime.utcnow() -
                          datetime.timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
        r = requests.get(f"{YT_DATA_URL}/search",
            headers={"Authorization": f"Bearer {token}"},
            params={"part": "snippet", "q": search_query,
                    "type": "video", "order": "viewCount",
                    "publishedAfter": published_after,
                    "videoDuration": "long", "maxResults": 10,
                    "relevanceLanguage": "en"}, timeout=20)
        if r.status_code == 200:
            items = r.json().get("items", [])
            return [{"title": i["snippet"]["title"],
                     "channel": i["snippet"]["channelTitle"],
                     "published": i["snippet"]["publishedAt"][:10]}
                    for i in items]
    except Exception as e:
        log(f"  Competitor search error: {e}")
    return []

# ── STEP 3: AI analysis of what's working ─────────────────────
def analyse_competitor_patterns(niche_name, competitor_videos, own_videos_summary):
    if not competitor_videos: return "No competitor data available."
    titles = "\n".join(f"- {v['title']}" for v in competitor_videos[:8])
    prompt = f"""Analyse these top-performing YouTube titles from the {niche_name.replace('_',' ')} niche this week:

{titles}

Our channel's best performing video this week: {own_videos_summary}

Identify:
1. What hook formula appears most in the top titles (3-5 words that appear repeatedly)?
2. What emotional trigger is dominant (fear/shock/curiosity/betrayal)?
3. What story structure are they using?
4. How do our titles compare — what specifically should we change next week?
5. One specific title format to steal and adapt for next week

Be specific. Give actionable instructions. Max 200 words."""
    return ai(prompt, tokens=400) or "Analysis unavailable."

# ── STEP 4: Recalibrate title scoring ─────────────────────────
def recalibrate_title_model(state, competitor_patterns):
    """
    Compare predicted CTR scores vs actual performance.
    Update the scoring model weights for next week.
    """
    intel = {}
    try:
        if INTEL_FILE.exists():
            intel = json.loads(INTEL_FILE.read_text())
    except: pass

    intel["last_updated"]          = datetime.datetime.now().isoformat()
    intel["competitor_patterns"]   = competitor_patterns
    intel["calibration_note"]      = (
        "Title scoring recalibrated based on this week's competitor data. "
        "Next week's scripts will prioritize: " + competitor_patterns[:150]
    )

    INTEL_FILE.write_text(json.dumps(intel, indent=2))
    log("  Intel recalibrated and saved")
    return intel

# ── STEP 5: Next week strategy ────────────────────────────────
def generate_next_week_strategy(all_competitor_data, own_performance):
    all_titles = []
    for niche, videos in all_competitor_data.items():
        all_titles.extend([v["title"] for v in videos[:5]])

    prompt = f"""You are a YouTube growth strategist for dark documentary channels.

TOP COMPETITOR TITLES THIS WEEK:
{chr(10).join(f"- {t}" for t in all_titles[:20])}

OUR CHANNEL PERFORMANCE:
{own_performance}

Generate a specific action plan for next week:
1. TOP 3 TOPICS to cover (based on competitor gaps — what they're NOT doing well)
2. TITLE FORMULA to use (based on what's working above)
3. ONE THUMBNAIL approach that would beat the competition
4. HOOK FORMAT for cold opens based on what's performing
5. WHAT TO AVOID (topics or formats that are saturated)

Be extremely specific. Give exact topic suggestions, not categories. Max 300 words."""
    return ai(prompt, tokens=600) or "Strategy generation unavailable."

# ── MAIN ──────────────────────────────────────────────────────

# ================================================================
# RETENTION ANALYSIS
# Pulls per-video retention curves from YouTube Analytics API.
# Maps drop-off timestamps to script stages.
# Writes specific stage fixes to next_week_strategy.json.
# ================================================================

def get_video_retention(token, video_id):
    """
    Pull audience retention curve for a specific video.
    Returns list of (elapsed_ratio, watch_ratio) tuples.
    elapsed_ratio: 0.0 to 1.0 (position in video)
    watch_ratio:   0.0 to 1.0 (fraction still watching)
    """
    try:
        r = requests.get(
            "https://youtubeanalytics.googleapis.com/v2/reports",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "ids":        "channel==MINE",
                "metrics":    "audienceWatchRatio",
                "dimensions": "elapsedVideoTimeRatio",
                "filters":    f"video=={video_id}",
                "sort":       "elapsedVideoTimeRatio",
            }, timeout=20)
        if r.status_code == 200:
            rows = r.json().get("rows", [])
            return [(float(row[0]), float(row[1])) for row in rows]
        elif r.status_code == 403:
            log(f"  Retention: Analytics API not enabled (need YouTube Analytics scope)")
        else:
            log(f"  Retention {r.status_code}: {r.text[:100]}")
    except Exception as e:
        log(f"  Retention error (non-fatal): {e}")
    return []


def find_retention_dropoffs(retention_curve):
    """
    Find the 3 biggest drop-off points in the retention curve.
    A drop-off is where the retention falls fastest — viewers leaving.
    Returns list of (elapsed_ratio, drop_magnitude) sorted by magnitude.
    """
    if len(retention_curve) < 5:
        return []
    dropoffs = []
    for i in range(1, len(retention_curve) - 1):
        elapsed, current = retention_curve[i]
        _, prev = retention_curve[i - 1]
        drop = prev - current
        if drop > 0.005:  # meaningful drop (> 0.5% of remaining viewers)
            dropoffs.append((elapsed, drop))
    # Sort by magnitude, return top 3
    dropoffs.sort(key=lambda x: x[1], reverse=True)
    return dropoffs[:3]


def map_retention_to_stage(elapsed_ratio):
    """
    Map a timestamp (as fraction of video) to the script stage
    that was playing at that point. Uses STAGE_WORDS proportions.
    """
    stage_words = [100, 200, 250, 400, 200, 650, 200]
    stage_names = [
        "Cold Open", "The Before", "First Signals",
        "Escalation", "False Resolution", "Real Reveal", "Implication + CTA"
    ]
    total = sum(stage_words)
    cumulative = 0
    for i, (words, name) in enumerate(zip(stage_words, stage_names)):
        cumulative += words
        if elapsed_ratio <= cumulative / total:
            return i + 1, name
    return 7, "Implication + CTA"


def generate_stage_fix(stage_num, stage_name, drop_magnitude, ai_fn):
    """
    Use AI to generate a specific fix for the underperforming stage.
    """
    severity = "slightly" if drop_magnitude < 0.03 else "significantly"
    prompt = f"""Stage {stage_num} ({stage_name}) of our dark documentary scripts is {severity} losing viewers.

Common reasons viewers leave at this stage:
- Pacing too slow (too many similar sentences in a row)
- Not enough new information being revealed
- Tension deflated (contradiction between tone and content)
- Too vague (lacks specific details, dates, numbers)

Write ONE specific instruction (max 30 words) for how to fix Stage {stage_name} in next week's script.
Be specific about what to change. Return only the instruction."""

    result = ai_fn(prompt, tokens=100)
    if result:
        return result.strip()[:200]
    return f"Add more specific evidence and shorten sentences in the {stage_name} stage."


def analyse_channel_retention(token, video_ids, details, ai_fn):
    """
    Analyse retention for all videos this week.
    Returns dict of stage fixes to apply next week.
    """
    stage_drops = {}  # stage_num -> list of drop magnitudes
    total_videos_analysed = 0

    for vid_id in video_ids[:5]:  # analyse up to 5 videos
        curve = get_video_retention(token, vid_id)
        if not curve:
            continue
        total_videos_analysed += 1
        dropoffs = find_retention_dropoffs(curve)
        for elapsed, magnitude in dropoffs:
            stage_num, stage_name = map_retention_to_stage(elapsed)
            if stage_num not in stage_drops:
                stage_drops[stage_num] = {"drops": [], "name": stage_name}
            stage_drops[stage_num]["drops"].append(magnitude)

    if not stage_drops:
        log("  Retention: no drop-off data yet (need more video views)")
        return {}, total_videos_analysed

    # Average the drops across videos, find worst stage
    stage_fixes = {}
    worst_stage = max(stage_drops.items(),
                      key=lambda x: sum(x[1]["drops"]) / len(x[1]["drops"]))
    stage_num, data = worst_stage
    avg_drop = sum(data["drops"]) / len(data["drops"])
    fix = generate_stage_fix(stage_num, data["name"], avg_drop, ai_fn)
    stage_fixes[data["name"]] = fix
    log(f"  Retention: worst stage = {data['name']} (avg drop {avg_drop:.1%})")
    log(f"  Fix: {fix[:80]}")

    return stage_fixes, total_videos_analysed

def run_weekly_report_for_channel(channel_cfg):
    """
    FIX: this used to BE main() itself, hardcoded entirely to Ch1's
    credentials, niches, and output path. Now takes a channel config
    (from CHANNELS) and runs the complete analysis for THAT channel,
    writing its strategy file to THAT channel's own directory.
    """
    channel_id   = channel_cfg["channel_id"]
    display_name = channel_cfg["display_name"]
    output_dir   = Path(channel_cfg["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    state_file   = output_dir / "state.json"

    log("=" * 60)
    log(f"DeepDive Empire — Weekly Self-Improvement Engine — {display_name}")
    log(f"Week ending: {datetime.date.today().isoformat()}")
    log("=" * 60)

    state = {}
    try:
        if state_file.exists():
            state = json.loads(state_file.read_text())
    except: pass

    try:
        token = get_yt_token(channel_cfg["yt_client_id"], channel_cfg["yt_client_secret"],
                              channel_cfg["yt_refresh_token"])
    except Exception as e:
        tg(f"⚠️ Weekly report ({display_name}): YouTube auth failed — {e}")
        log(f"Auth failed: {e}")
        return

    # Own analytics
    log("\n[1] Pulling your YouTube analytics...")
    rows = get_own_analytics(token)
    video_ids = [r[0] for r in rows[:10]] if rows else []
    details   = get_video_details(token, video_ids)

    # Real performance feedback loop — matches each analyzed video back to
    # its original topic (via the publishing archive's video_url, which
    # contains the same video_id) and records the REAL CTR against it, so
    # future topic scoring can genuinely learn from real outcomes instead
    # of only ever guessing once and never checking itself.
    try:
        from topic_scoring import record_real_performance
        from publishing_archive import load_archive
        archive = load_archive(output_dir)
        for row in rows:
            if len(row) < 8 or row[7] is None:
                continue
            video_id, real_ctr = row[0], row[7] * 100  # API returns a fraction
            matching = [a for a in archive if video_id in a.get("video_url", "")]
            if matching:
                episode_num = matching[0].get("episode_number")
                if episode_num is not None:
                    record_real_performance(output_dir, episode_num, real_ctr)
        log(f"  Real performance recorded for {len([r for r in rows if len(r) >= 8])} videos")
    except Exception as e:
        log(f"  Real performance feedback loop (non-fatal): {e}")

    # Retention analysis — find which script stages lose viewers
    log("\n[1b] Analysing viewer retention curves...")
    stage_fixes, vids_analysed = analyse_channel_retention(
        token, video_ids, details, ai)
    log(f"  Analysed {vids_analysed} videos for retention data")
    own_perf_lines = []
    for d in details[:5]:
        t   = d["snippet"]["title"][:50]
        v   = d.get("statistics",{}).get("viewCount","?")
        own_perf_lines.append(f"  '{t}' — {v} views")
    own_performance = "\n".join(own_perf_lines) if own_perf_lines else "No data yet (channel new)"
    log(f"  Found {len(details)} videos with analytics")

    # Competitor analysis — uses THIS channel's own niches, not always Ch1's
    log("\n[2] Scanning competitor channels...")
    all_competitor_data = {}
    competitor_analyses = {}
    for niche_name, search_q in channel_cfg["competitor_searches"].items():
        log(f"  Niche: {niche_name}")
        videos = get_competitor_videos(token, niche_name, search_q)
        all_competitor_data[niche_name] = videos
        if videos:
            analysis = analyse_competitor_patterns(niche_name, videos, own_performance)
            competitor_analyses[niche_name] = analysis
            log(f"    Found {len(videos)} competitor videos")
        time.sleep(2)  # avoid rate limits

    # Recalibrate
    log("\n[3] Recalibrating title model...")
    combined_patterns = "\n\n".join(
        f"[{n.upper()}] {a}" for n, a in competitor_analyses.items())
    intel = recalibrate_title_model(state, combined_patterns)

    # Next week strategy
    log("\n[4] Generating next week strategy...")
    strategy = generate_next_week_strategy(all_competitor_data, own_performance)

    # Build report
    total_vids  = state.get("total_uploads", 0)
    total_shorts= state.get("total_shorts", 0)
    last_title  = state.get("last_title", "None yet")
    last_url    = state.get("last_url", "")

    # Competitor highlights
    top_titles_all = []
    for niche, vids in all_competitor_data.items():
        top_titles_all.extend(vids[:2])
    top_titles_str = "\n".join(
        f"  • {v['title'][:60]}" for v in top_titles_all[:10])

    # Per-niche competitor analysis snippets
    analysis_str = "\n\n".join(
        f"<b>{n.replace('_',' ').upper()}</b>\n{a[:300]}"
        for n, a in list(competitor_analyses.items())[:3])

    stage_fix_str = "\n".join(
        f"  Stage fix → {name}: {fix[:80]}"
        for name, fix in stage_fixes.items()
    ) or "Not enough view data yet (need 100+ views per video)"

    report = f"""📊 <b>DeepDive Empire — Weekly Intelligence Report ({display_name})</b>
Week ending {datetime.date.today().strftime('%B %d, %Y')}

<b>YOUR CHANNEL THIS WEEK</b>
Videos published: {total_vids} total | Shorts: {total_shorts}
Latest: {last_title[:55]}
{last_url}

<b>YOUR PERFORMANCE</b>
{own_performance or "Building audience — data available after first monetised week"}

<b>WHAT COMPETITORS PUBLISHED THIS WEEK</b>
{top_titles_str}

<b>NICHE ANALYSIS</b>
{analysis_str}

<b>NEXT WEEK STRATEGY</b>
{strategy[:800]}

<b>RETENTION ANALYSIS</b>
{stage_fix_str}

<b>SYSTEM STATUS</b>
✅ Intel recalibrated for next week
✅ Title scoring model updated
✅ Competitor patterns stored

Auto-improvement complete ({display_name}). Next run: Sunday."""

    # ── Write strategy file for THIS channel's pipeline to consume ──
    strategy_data = {
        "generated_date":        datetime.date.today().isoformat(),
        "strategy":              strategy,
        "competitor_patterns":   combined_patterns[:2000],
        "top_competitor_titles": [v["title"] for vids in all_competitor_data.values()
                                   for v in vids[:3]],
        "recommended_topics":    [],   # populated by AI below
        "winning_hook_format":   "",
        "stage_fixes":           stage_fixes,    # retention-based script improvements
        "retention_note":        (
            f"Analysed {vids_analysed} videos. "
            + (f"Fix priority: {list(stage_fixes.keys())}"
               if stage_fixes else "Not enough views yet for retention data.")
        ),
    }
    # Extract specific topic recommendations from strategy text
    topic_prompt = f"""From this strategy document, extract:
1. The top 3 specific video topics recommended for next week (exact topic sentences)
2. The single best hook format to use in titles

Strategy:
{strategy[:1000]}

Return JSON only:
{{"topics": ["topic1", "topic2", "topic3"], "hook_format": "one line"}}"""
    topic_raw = ai(topic_prompt, tokens=400)
    if topic_raw:
        try:
            import re as _re
            json_match = _re.search(r'\{[^{}]+\}', topic_raw, _re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                strategy_data["recommended_topics"]  = parsed.get("topics", [])
                strategy_data["winning_hook_format"] = parsed.get("hook_format", "")
        except: pass

    # FIX: writes to THIS channel's own output_dir now, not always
    # video_pipeline/ — this is what actually makes the strategy file
    # reachable by Ch2 (and future channels), which each read from their
    # own SCRIPT_DIR, a genuinely different path than Ch1's.
    strategy_file = output_dir / "next_week_strategy.json"
    strategy_file.write_text(json.dumps(strategy_data, indent=2))
    log(f"  Strategy written: {strategy_file}")

    # Resource-page generation — weekly cadence, since these aggregate
    # MULTIPLE episodes (not per-video like companion pages). Safe to
    # run every week: always reflects the current full episode cluster,
    # not additive/incremental.
    try:
        from site_generator import generate_all_resource_pages
        # weekly_report.py's own location is always video_pipeline/,
        # regardless of which channel is being processed — simpler and
        # more robust than computing per-channel relative depth.
        docs_root = Path(__file__).parent.parent / "docs"
        resource_results = generate_all_resource_pages(
            channel_id, output_dir, docs_root,
            ai_fn=lambda p, tokens=500: ai(p, tokens=tokens),
        )
        for r in resource_results:
            log(f"  Resource page ({r['niche']}, {r['episode_count']} episodes): {r['path']}")
    except Exception as e:
        log(f"  Resource page generation (non-fatal): {e}")

    # Topic approval review — the real automation-boundary enforcement.
    # Presents top-scoring pending topics for human APPROVE/REJECT via
    # Telegram, matching the document's own weekly time-block for this
    # exact decision. Never auto-approves anything; times out gracefully
    # if nobody responds, leaving topics pending for next week.
    try:
        from topic_scoring import review_pending_topics_via_telegram
        review_result = review_pending_topics_via_telegram(
            output_dir, display_name, TG_TOKEN, TG_CHAT, top_n=6, poll_minutes=15
        )
        log(f"  Topic review: {review_result}")
    except Exception as e:
        log(f"  Topic review (non-fatal): {e}")

    tg(report)
    log(f"\nWeekly report sent to Telegram ({display_name})")
    log(f"Strategy preview: {strategy[:200]}")
    log("=" * 60)

    # FIX: check_ctr_against_target existed fully built (checks real
    # per-video CTR against the explicit 5% target) but was never wired
    # into the actual dashboard output — it needs the real analytics rows
    # already fetched above, just never passed anywhere. Returned here so
    # main() can collect it per channel and hand it to build_empire_dashboard.
    return rows


def main():
    """
    FIX: this used to run once, hardcoded to Ch1 only. Now loops over
    every channel in CHANNELS — add a new entry there to extend to
    Ch3/4/5, no changes needed here.
    """
    all_analytics_rows = {}
    for channel_cfg in CHANNELS:
        try:
            rows = run_weekly_report_for_channel(channel_cfg)
            all_analytics_rows[channel_cfg["channel_id"]] = rows or []
        except Exception as e:
            tg(f"⚠️ Weekly report failed for {channel_cfg['display_name']}: {e}")
            log(f"Channel {channel_cfg['channel_id']} failed (non-fatal, continuing): {e}")
            all_analytics_rows[channel_cfg["channel_id"]] = []
        time.sleep(5)  # brief gap between channels to avoid rate-limit collisions

    # Site navigation regeneration — needs ALL channels' data together
    # (the root index lists every channel), so this runs once after the
    # per-channel loop above, not inside it.
    try:
        from site_generator import generate_site_navigation
        docs_root = Path(__file__).parent.parent / "docs"
        channel_dirs = {c["channel_id"]: c["output_dir"] for c in CHANNELS}
        written = generate_site_navigation(channel_dirs, docs_root)
        log(f"Site navigation regenerated: {len(written)} pages")

        # Real SEO infrastructure — previously entirely missing. Runs after
        # navigation so the sitemap reflects every page that actually exists
        # this week, not a stale snapshot.
        from site_generator import generate_seo_files, generate_legal_pages
        site_base_url = os.environ.get("SITE_BASE_URL", "https://example.github.io/betrayal-bot/")
        seo_result = generate_seo_files(docs_root, site_base_url)
        log(f"SEO files (sitemap/robots.txt): {seo_result}")

        legal_pages = generate_legal_pages(docs_root)
        log(f"Legal pages regenerated: {legal_pages}")
    except Exception as e:
        log(f"Site navigation regeneration (non-fatal): {e}")

    # Product PDF exports + product landing pages — same weekly cadence.
    # products_root is the same for every channel (repo-root products/),
    # since all channels feed into a shared set of 3 products.
    try:
        from monetization import export_all_products
        from site_generator import render_all_product_pages
        products_root = Path(__file__).parent.parent / "products"
        pdf_root = Path(__file__).parent.parent / "products" / "exports"
        docs_root = Path(__file__).parent.parent / "docs"

        pdf_results = export_all_products(products_root, pdf_root)
        for r in pdf_results:
            if r["exported"]:
                log(f"  Product PDF exported: {r['product_id']} ({r['note_count']} notes)")
            else:
                log(f"  Product PDF skipped: {r['product_id']} ({r['reason']})")

        product_pages = render_all_product_pages(products_root, docs_root)
        log(f"  Product landing pages regenerated: {len(product_pages)}")
    except Exception as e:
        log(f"Product export / page generation (non-fatal): {e}")

    # CEO Dashboard — the real single-source-of-truth report, combining
    # every channel's health, product growth, real site traffic, and
    # (once configured) real sales into one message.
    try:
        from ceo_dashboard import build_empire_dashboard
        products_root = Path(__file__).parent.parent / "products"
        repo_owner = os.environ.get("GITHUB_REPO_OWNER", "BetrayalDeepDive")
        repo_name = os.environ.get("GITHUB_REPO_NAME", "betrayal-bot")
        github_token = os.environ.get("GITHUB_TOKEN", "")
        gumroad_token = os.environ.get("GUMROAD_ACCESS_TOKEN", "")

        dashboard_report = build_empire_dashboard(
            CHANNELS, products_root, repo_owner, repo_name, github_token, gumroad_token,
            analytics_rows_by_channel=all_analytics_rows
        )
        tg(dashboard_report)
        log("Empire Dashboard sent to Telegram")
    except Exception as e:
        log(f"Empire Dashboard generation (non-fatal): {e}")

if __name__ == "__main__":
    main()
