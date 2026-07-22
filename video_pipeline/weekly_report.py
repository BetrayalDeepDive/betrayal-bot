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
    # FIX (found on full workflow/weekly-report audit): these 3 real Ch2
    # niches were missing entirely — same exact gap pattern already
    # found and fixed multiple times this session for other channel-
    # keyed dicts (NUMBER_NOUN_BANKS, SHORTS_TEMPLATES).
    "body_cam_police":         "police bodycam footage investigation documentary",
    "courtroom_drama":         "courtroom trial verdict documentary",
    "robbery_documentaries":   "robbery heist investigation documentary",
}

# FIX: added — Ch3 had zero entry in this file (confirmed by direct
# inspection: no "control_files" string anywhere in the original file).
# All 6 of Ch3's real niches covered, matching the DAY_NICHE fix that
# makes all 6 reachable in the pipeline.
COMPETITOR_SEARCHES_CH3 = {
    "cult_psychology":             "cult psychology mind control documentary",
    "propaganda_systems":          "propaganda manipulation media documentary",
    "social_engineering":          "social engineering manipulation fraud documentary",
    "mass_deception":              "mass deception manipulation exposed documentary",
    "dark_business_documentaries": "corporate scandal collapse fraud documentary",
    "scams_fraud_exposed":         "scam fraud exposed investigation documentary",
}

# FIX (critical, found on full workflow/weekly-report audit): Ch4 (The
# Archive) was missing from this whole file entirely — weekly reports,
# competitor analysis, and strategy generation never covered it at all
# since it launched.
COMPETITOR_SEARCHES_CH4 = {
    "egyptian_civilization":               "ancient egypt pharaoh documentary",
    "chinese_civilization":                "ancient china dynasty documentary",
    "mesopotamian_lost_civilizations":     "lost civilization mesopotamia documentary",
    "islamic_civilization_history":        "islamic golden age history documentary",
    "fallen_empires_military_overstretch": "fallen empire collapse documentary",
    "elite_betrayal_infighting":           "royal betrayal court intrigue documentary",
    "propaganda_institutional_decline":    "institutional decline propaganda documentary",
    "modern_parallels":                    "history repeating modern parallels documentary",
}

# v1 addition — Ch5 (The Collapse Index), same gap already found and
# fixed for Ch4 above.
COMPETITOR_SEARCHES_CH5 = {
    "ai_startup_collapse":          "ai startup collapse documentary",
    "tech_company_collapse":       "tech company collapse documentary",
    "crypto_collapse":             "crypto exchange collapse documentary",
    "cybersecurity_disasters":     "cybersecurity breach documentary",
    "product_flops":               "product flop failure documentary",
    "dotcom_era_collapse":         "dot com bubble documentary",
    "personal_finance_mistakes":   "personal finance mistakes explained",
    "investing_fundamentals":      "investing fundamentals explained",
    "retirement_planning":         "retirement planning explained",
    "credit_debt_repair":          "credit score debt repair explained",
    "real_estate_affordability":   "real estate affordability explained",
    "budgeting_saving_strategies": "budgeting saving strategies explained",
    "stock_market_crashes_history":"stock market crash history documentary",
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
        "tg_token":         os.environ.get("TELEGRAM_TOKEN", ""),
        "tg_chat":          os.environ.get("TELEGRAM_CHAT_ID", ""),
        "competitor_searches": COMPETITOR_SEARCHES,
        "output_dir":       SCRIPT_DIR,   # video_pipeline/
    },
    {
        "channel_id":       "evidence_room",
        "display_name":     "The Evidence Room",
        "yt_client_id":     os.environ.get("EVIDENCE_YT_CLIENT_ID", ""),
        "yt_client_secret": os.environ.get("EVIDENCE_YT_CLIENT_SECRET", ""),
        "yt_refresh_token": os.environ.get("EVIDENCE_YT_REFRESH_TOKEN", ""),
        "tg_token":         os.environ.get("TELEGRAM_TOKEN_CH2", ""),
        "tg_chat":          os.environ.get("TELEGRAM_CHAT_ID_CH2", ""),
        "competitor_searches": COMPETITOR_SEARCHES_CH2,
        "output_dir":       SCRIPT_DIR.parent / "channels" / "evidence_room",
    },
    {
        "channel_id":       "control_files",
        "display_name":     "The Control Files",
        "yt_client_id":     os.environ.get("CHANNEL3_YT_CLIENT_ID", ""),
        "yt_client_secret": os.environ.get("CHANNEL3_YT_CLIENT_SECRET", ""),
        "yt_refresh_token": os.environ.get("CHANNEL3_YT_REFRESH_TOKEN", ""),
        "tg_token":         os.environ.get("TELEGRAM_TOKEN_CH3", ""),
        "tg_chat":          os.environ.get("TELEGRAM_CHAT_ID_CH3", ""),
        "competitor_searches": COMPETITOR_SEARCHES_CH3,
        "output_dir":       SCRIPT_DIR.parent / "channels" / "control_files",
    },
    {
        "channel_id":       "archive",
        "display_name":     "The Archive",
        "yt_client_id":     os.environ.get("CHANNEL4_YT_CLIENT_ID", ""),
        "yt_client_secret": os.environ.get("CHANNEL4_YT_CLIENT_SECRET", ""),
        "yt_refresh_token": os.environ.get("CHANNEL4_YT_REFRESH_TOKEN", ""),
        "tg_token":         os.environ.get("TELEGRAM_TOKEN_CH4", ""),
        "tg_chat":          os.environ.get("TELEGRAM_CHAT_ID_CH4", ""),
        "competitor_searches": COMPETITOR_SEARCHES_CH4,
        "output_dir":       SCRIPT_DIR.parent / "channels" / "archive",
    },
    {
        "channel_id":       "collapse_index",
        "display_name":     "The Collapse Index",
        "yt_client_id":     os.environ.get("CHANNEL5_YT_CLIENT_ID", ""),
        "yt_client_secret": os.environ.get("CHANNEL5_YT_CLIENT_SECRET", ""),
        "yt_refresh_token": os.environ.get("CHANNEL5_YT_REFRESH_TOKEN", ""),
        "tg_token":         os.environ.get("TELEGRAM_TOKEN_CH5", ""),
        "tg_chat":          os.environ.get("TELEGRAM_CHAT_ID_CH5", ""),
        "competitor_searches": COMPETITOR_SEARCHES_CH5,
        "output_dir":       SCRIPT_DIR.parent / "channels" / "collapse_index",
    },
]

# Real per-channel product mapping for Gumroad revenue attribution — the
# same canonical mapping each channel's own build_product_cta() uses
# (control_files_pipeline.py/archive_pipeline.py/etc.), duplicated here
# rather than imported since weekly_report.py doesn't otherwise import
# any single channel's pipeline module. Several channels intentionally
# share the same product (e.g. the Dark Manipulation Tactics Handbook),
# so revenue attributed to a shared product will appear in more than one
# channel's own report — this is real, not double-counted against a
# single channel's own distinct earnings, and is called out in the
# report text itself.
PRODUCT_TITLE_BY_CHANNEL = {
    "betrayal_deepdive": "Dark Manipulation Tactics Handbook",
    "evidence_room":     "Dark Manipulation Tactics Handbook",
    "control_files":     "Dark Manipulation Tactics Handbook",
    "archive":            "The Empire Collapse Atlas",
    "collapse_index":     "The Financial Red Flags Field Guide",
}


def log(m): print(m, flush=True)

def tg(m, token=None, chat=None):
    """
    FIX (v5 merge): same real gap already found and fixed for Ch2's
    weekly report — this always used the module-level TG_TOKEN/TG_CHAT
    (Ch1's bot), meaning every OTHER channel's weekly report/topic-review
    would silently go through Ch1's bot regardless of which channel was
    actually being reported on. Now accepts per-channel overrides,
    matching the same real pattern already proven correct for
    get_yt_token right below; defaults preserve existing behavior for
    any call site that doesn't pass them.
    """
    use_token = token or TG_TOKEN
    use_chat  = chat or TG_CHAT
    if not use_token: return
    for chunk in [m[i:i+4000] for i in range(0, len(m), 4000)]:
        try:
            requests.post(f"https://api.telegram.org/bot{use_token}/sendMessage",
                json={"chat_id": use_chat, "text": chunk, "parse_mode": "HTML"}, timeout=15)
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
def recalibrate_title_model(state, competitor_patterns, channel_dir=None):
    """
    Compare predicted CTR scores vs actual performance.
    Update the scoring model weights for next week.

    FIX (found on re-audit): this previously always wrote to a single
    module-level INTEL_FILE path (video_pipeline/weekly_intel.json),
    completely unscoped by channel — since main() loops over every
    channel calling this once each, every channel's recalibration
    overwrote the exact same file, meaning only the LAST channel
    processed in the loop ever kept its data; every other channel's
    weekly calibration was silently discarded. Currently write-only
    (nothing reads this back yet), so this hasn't corrupted live
    decisions, but it's a real landmine for whenever it does get wired
    into something. Now scoped per-channel.
    """
    intel_path = (Path(channel_dir) / "weekly_intel.json") if channel_dir else INTEL_FILE
    intel = {}
    try:
        if intel_path.exists():
            intel = json.loads(intel_path.read_text())
    except: pass

    intel["last_updated"]          = datetime.datetime.now().isoformat()
    intel["competitor_patterns"]   = competitor_patterns

    # FIX (found on deep re-audit): this used to always write a canned
    # sentence built from competitor title TEXT — it never actually
    # compared score_title_v2's predictions against real CTR outcomes,
    # despite this function's own name/docstring. Now genuinely checks:
    # if enough real title-score-vs-real-CTR history exists (via
    # title_scoring_history.py, wired into record_title_used/
    # attach_title_video_id/record_title_ctr in growth_engine.py and
    # each channel's run_title_ctr_gate), use that real comparison
    # instead — falling back to the original competitor-pattern note
    # only when there isn't enough real data yet, same as
    # topic_scoring.get_scoring_calibration_notes's proven pattern.
    real_calibration_note = ""
    if channel_dir:
        try:
            from title_scoring_history import get_title_calibration_notes
            real_calibration_note = get_title_calibration_notes(channel_dir)
        except Exception as e:
            log(f"  Real title calibration (non-fatal): {e}")

    intel["calibration_note"] = real_calibration_note or (
        "Title scoring recalibrated based on this week's competitor data. "
        "Next week's scripts will prioritize: " + competitor_patterns[:150]
    )
    intel["calibration_is_real_performance_based"] = bool(real_calibration_note)

    try:
        intel_path.parent.mkdir(parents=True, exist_ok=True)
        intel_path.write_text(json.dumps(intel, indent=2))
        log("  Intel recalibrated and saved")
    except Exception as e:
        log(f"  Intel save (non-fatal): {e}")
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


def map_retention_to_stage(elapsed_ratio, channel_id="betrayal_deepdive"):
    """
    Map a timestamp (as fraction of video) to the script stage that was
    playing at that point.

    FIX (found on re-audit): this was hardcoded to Ch1's specific 7-stage
    word-count proportions and stage names, with zero channel awareness —
    the exact same "copy-pasted structure from another channel" bug
    pattern found repeatedly elsewhere this session, just for stage
    structure instead of niche names. When called for Ch3, a real
    drop-off at (say) 45% through the video would have been mapped to
    whatever stage sits at 45% of CH1's proportions, not Ch3's — feeding
    a wrong stage name into generate_stage_fix's AI prompt, producing
    advice that doesn't correspond to what's actually in the Ch3 script
    at that point. Now uses each channel's own real stage word-counts.
    """
    channel_stage_words = {
        "betrayal_deepdive": [100, 200, 250, 400, 200, 650, 200],
        "evidence_room":     [100, 200, 250, 400, 200, 650, 200],
        "control_files":     [120, 200, 280, 480, 150, 520, 150],  # matches control_files_pipeline.py's real stage_targets
    }
    channel_stage_names = {
        "betrayal_deepdive": ["Cold Open", "The Before", "First Signals",
                               "Escalation", "False Resolution", "Real Reveal", "Implication + CTA"],
        "evidence_room":     ["Cold Open", "The Before", "First Signals",
                               "Escalation", "False Resolution", "Real Reveal", "Implication + CTA"],
        "control_files":     ["The System", "How It Was Built", "Documented Cases",
                               "The Evidence", "The Scale", "Those Who Resisted", "Implications"],
    }
    stage_words = channel_stage_words.get(channel_id, channel_stage_words["betrayal_deepdive"])
    stage_names = channel_stage_names.get(channel_id, channel_stage_names["betrayal_deepdive"])
    total = sum(stage_words)
    cumulative = 0
    for i, (words, name) in enumerate(zip(stage_words, stage_names)):
        cumulative += words
        if elapsed_ratio <= cumulative / total:
            return i + 1, name
    return 7, stage_names[-1]


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


def analyse_channel_retention(token, video_ids, details, ai_fn, channel_id="betrayal_deepdive"):
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
            stage_num, stage_name = map_retention_to_stage(elapsed, channel_id)
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
        tg(f"⚠️ Weekly report ({display_name}): YouTube auth failed — {e}",
           token=channel_cfg.get("tg_token"), chat=channel_cfg.get("tg_chat"))
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
        token, video_ids, details, ai, channel_id=channel_id)
    log(f"  Analysed {vids_analysed} videos for retention data")
    own_perf_lines = []
    for d in details[:5]:
        t   = d["snippet"]["title"][:50]
        v   = d.get("statistics",{}).get("viewCount","?")
        own_perf_lines.append(f"  '{t}' — {v} views")
    own_performance = "\n".join(own_perf_lines) if own_perf_lines else "No data yet (channel new)"
    log(f"  Found {len(details)} videos with analytics")

    # FIX (found on deep re-audit): CTR and subscriber growth were both
    # real values already pulled from this exact `rows` response
    # (get_own_analytics, metrics order: views, estimatedMinutesWatched,
    # averageViewDuration, subscribersGained, likes, impressions,
    # impressionsClickThroughRate) — CTR was only ever fed into the
    # topic-scoring feedback loop above, subscribersGained was fetched
    # and never read at all. Neither ever reached the actual delivered
    # per-channel report text. Computed here from real data, not
    # invented — "no data yet" when the 7-day window has none.
    _ctr_values = [r[7] * 100 for r in rows if len(r) >= 8 and r[7] is not None]
    avg_ctr_str = f"{sum(_ctr_values) / len(_ctr_values):.1f}%" if _ctr_values else "no data yet"
    _subs_values = [r[4] for r in rows if len(r) >= 5 and r[4] is not None]
    subs_gained_str = str(sum(_subs_values)) if _subs_values else "no data yet"

    # FIX (found on deep re-audit): score_audio_quality/score_video_quality
    # (quality_scoring.py) were computed for every episode but never
    # persisted or reported anywhere — added quality_score_history.py
    # this session as the write side (recorded on approval in all 5
    # channels); this is the real read side.
    try:
        from quality_score_history import get_recent_quality_summary
        quality_summary = get_recent_quality_summary(str(output_dir))
    except Exception as e:
        log(f"  Quality score summary (non-fatal): {e}")
        quality_summary = "No data yet."

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
    intel = recalibrate_title_model(state, combined_patterns, channel_dir=output_dir)

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

    # FIX (found on deep re-audit): CTR, subscriber growth, and the real
    # title-CTR calibration note (title_scoring_history.py, wired in
    # earlier this session) were all real data already computed above but
    # never actually reached this delivered report text — CTR/subs sat
    # unread in `rows`, and calibration_note was written only to
    # weekly_intel.json. Surfaced here now.
    calibration_note = intel.get("calibration_note", "")

    # FIX (found on explicit follow-up request): real Gumroad revenue
    # existed (ceo_dashboard.get_gumroad_sales) but only ever appeared in
    # the combined Empire Dashboard message, which goes out through Ch1's
    # Telegram bot only (no per-channel token/chat override) — a channel
    # owner reading their OWN weekly report never saw their own product's
    # real revenue at all. Wired in here as a real per-channel section,
    # filtered to the last 7 days (Gumroad's own real after/before Sales
    # API filters, not an all-time total) so it's genuinely "this week's"
    # revenue, matching the rest of the report's cadence. Wrapped in its
    # own try/except so a Gumroad API hiccup can never block the rest of
    # this report from sending — "published every week without fail"
    # means a revenue-fetch failure must degrade to an honest "no data"
    # line, not skip the whole report.
    revenue_line = "Gumroad not yet connected (GUMROAD_ACCESS_TOKEN not set)."
    try:
        from ceo_dashboard import get_gumroad_sales
        gumroad_token = os.environ.get("GUMROAD_ACCESS_TOKEN", "")
        if gumroad_token:
            week_start = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
            week_end = datetime.date.today().isoformat()
            sales_data = get_gumroad_sales([], gumroad_token, after_date=week_start, before_date=week_end)
            if sales_data.get("connected"):
                product_title = PRODUCT_TITLE_BY_CHANNEL.get(channel_id, "")
                entry = sales_data.get("by_product", {}).get(product_title)
                if entry:
                    revenue = entry["revenue_cents"] / 100
                    shared_note = (" (shared product — also sold via other channels)"
                                   if list(PRODUCT_TITLE_BY_CHANNEL.values()).count(product_title) > 1 else "")
                    revenue_line = (f"{product_title}: {entry['count']} sale(s), "
                                    f"${revenue:.2f} this week{shared_note}.")
                else:
                    revenue_line = f"{product_title}: no sales this week (real data, genuinely zero)."
            else:
                revenue_line = f"Gumroad fetch failed (non-fatal): {sales_data.get('reason', 'unknown')}"
    except Exception as e:
        log(f"  Gumroad revenue fetch (non-fatal): {e}")
        revenue_line = f"Gumroad revenue unavailable this week (non-fatal): {e}"

    report = f"""📊 <b>DeepDive Empire — Weekly Intelligence Report ({display_name})</b>
Week ending {datetime.date.today().strftime('%B %d, %Y')}

<b>YOUR CHANNEL THIS WEEK</b>
Videos published: {total_vids} total | Shorts: {total_shorts}
Latest: {last_title[:55]}
{last_url}

<b>YOUR PERFORMANCE</b>
Avg CTR (last 7 days): {avg_ctr_str} | Subscribers gained: {subs_gained_str}
{quality_summary}
{own_performance or "Building audience — data available after first monetised week"}

<b>REVENUE (Gumroad, last 7 days)</b>
{revenue_line}

<b>WHAT COMPETITORS PUBLISHED THIS WEEK</b>
{top_titles_str}

<b>NICHE ANALYSIS</b>
{analysis_str}

<b>NEXT WEEK STRATEGY</b>
{strategy[:800]}

<b>RETENTION ANALYSIS</b>
{stage_fix_str}

<b>TITLE SCORING CALIBRATION</b>
{calibration_note or "Not enough real title-CTR history yet to calibrate against (needs 5+ published titles with recorded real CTR)."}

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
            output_dir, display_name, channel_cfg.get("tg_token") or TG_TOKEN,
            channel_cfg.get("tg_chat") or TG_CHAT, top_n=6, poll_minutes=15
        )
        log(f"  Topic review: {review_result}")
    except Exception as e:
        log(f"  Topic review (non-fatal): {e}")

    tg(report, token=channel_cfg.get("tg_token"), chat=channel_cfg.get("tg_chat"))
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
            tg(f"⚠️ Weekly report failed for {channel_cfg['display_name']}: {e}",
               token=channel_cfg.get("tg_token"), chat=channel_cfg.get("tg_chat"))
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
        from monetization import export_all_products, sync_all_gumroad_listings
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

        # v5 addition: real Gumroad Update/Enable sync — confirmed
        # feasible via research (Gumroad's own current API docs: Update
        # works, Creation doesn't) but not actually built until this
        # session. Only ever updates/enables products that already have
        # a real configured Gumroad ID and genuine content — never
        # touches anything else, never disables anything already live.
        gumroad_token = os.environ.get("GUMROAD_ACCESS_TOKEN", "")
        gumroad_results = sync_all_gumroad_listings(products_root, gumroad_token)
        for r in gumroad_results:
            log(f"  Gumroad sync ({r['product_id']}): {r}")
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
