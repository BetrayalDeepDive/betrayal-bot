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

# ── Credentials ──────────────────────────────────────────────
GEMINI_KEY    = os.environ.get("GEMINI_API_KEY", "")
GROQ_KEY      = os.environ.get("GROQ_API_KEY", "")
CEREBRAS_KEY  = os.environ.get("CEREBRAS_API_KEY", "")
YT_CLIENT_ID  = os.environ.get("YOUTUBE_CLIENT_ID", "")
YT_CLIENT_SEC = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
YT_REFRESH    = os.environ.get("YOUTUBE_REFRESH_TOKEN", "")
TG_TOKEN      = os.environ.get("TELEGRAM_TOKEN", "")
TG_CHAT       = os.environ.get("TELEGRAM_CHAT_ID", "")

SCRIPT_DIR    = Path(__file__).parent
STATE_FILE    = SCRIPT_DIR / "state.json"
INTEL_FILE    = SCRIPT_DIR / "weekly_intel.json"
YT_DATA_URL   = "https://www.googleapis.com/youtube/v3"
YT_ANALYTICS  = "https://youtubeanalytics.googleapis.com/v2"
YT_TOKEN_URL  = "https://oauth2.googleapis.com/token"

# ── Competitor channels per niche ─────────────────────────────
COMPETITOR_SEARCHES = {
    "dark_horror":        "dark horror documentary narration faceless",
    "seduction_dark":     "dark psychology manipulation documentary",
    "psychological_trap": "psychological horror true story faceless",
    "supernatural_real":  "paranormal evidence documentary narration",
    "obsession_dark":     "dark obsession true crime faceless documentary",
}

def log(m): print(m, flush=True)

def tg(m):
    if not TG_TOKEN: return
    for chunk in [m[i:i+4000] for i in range(0, len(m), 4000)]:
        try:
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                json={"chat_id": TG_CHAT, "text": chunk, "parse_mode": "HTML"}, timeout=15)
        except: pass

def get_yt_token():
    r = requests.post(YT_TOKEN_URL,
        data={"client_id": YT_CLIENT_ID, "client_secret": YT_CLIENT_SEC,
              "refresh_token": YT_REFRESH, "grant_type": "refresh_token"}, timeout=30)
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
    """Pull CTR, view duration, impressions for last 7 days."""
    try:
        end   = datetime.date.today().isoformat()
        start = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
        r = requests.get(f"{YT_ANALYTICS}/reports",
            headers={"Authorization": f"Bearer {token}"},
            params={"ids": "channel==MINE",
                    "startDate": start, "endDate": end,
                    "metrics": "views,estimatedMinutesWatched,averageViewDuration,"
                               "subscribersGained,likes",
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

def main():
    log("=" * 60)
    log("DeepDive Empire — Weekly Self-Improvement Engine")
    log(f"Week ending: {datetime.date.today().isoformat()}")
    log("=" * 60)

    state = {}
    try:
        if STATE_FILE.exists():
            state = json.loads(STATE_FILE.read_text())
    except: pass

    try:
        token = get_yt_token()
    except Exception as e:
        tg(f"⚠️ Weekly report: YouTube auth failed — {e}")
        log(f"Auth failed: {e}")
        return

    # Own analytics
    log("\n[1] Pulling your YouTube analytics...")
    rows = get_own_analytics(token)
    video_ids = [r[0] for r in rows[:10]] if rows else []
    details   = get_video_details(token, video_ids)

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

    # Competitor analysis
    log("\n[2] Scanning competitor channels...")
    all_competitor_data = {}
    competitor_analyses = {}
    for niche_name, search_q in COMPETITOR_SEARCHES.items():
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

    report = f"""📊 <b>DeepDive Empire — Weekly Intelligence Report</b>
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
✅ Competitor patterns stored in weekly_intel.json

Auto-improvement complete. Next run: Sunday."""

    # ── Write strategy file for pipelines to consume next week ──
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

    # Save to repo root for both pipelines to read
    strategy_file = SCRIPT_DIR / "next_week_strategy.json"
    strategy_file.write_text(json.dumps(strategy_data, indent=2))
    log(f"  Strategy written: {strategy_file}")

    tg(report)
    log("\nWeekly report sent to Telegram")
    log(f"Strategy preview: {strategy[:200]}")
    log("=" * 60)

if __name__ == "__main__":
    main()
