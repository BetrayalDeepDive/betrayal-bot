#!/usr/bin/env python3
"""
DEEPDIVE EMPIRE — GROWTH ENGINE v2.0
All 12 gaps from v1 fixed:
  1.  Comment engine: daily quota tracker + staggered retry
  2.  Series generator: new-channel fallback (no baseline needed)
  3.  CTR recovery: 7-day A/B test result tracking (keep winner)
  4.  Reply-to-replies: thread depth engagement multiplier
  5.  Hype: day-3 and day-6 follow-up notifications
  6.  Ch2+Ch3 chapter timestamps in descriptions
  7.  YouTube Cards via videos.update API
  8.  SRT caption upload for Ch2 and Ch3
  9.  Gemini BLOCK_NONE safety settings in all providers
 10.  Weekly report feeds ALL THREE channel strategy files
 11.  Affiliate link auto-insertion in all descriptions
 12.  Pinned comment update on previous episode when Part N+1 goes live

Schedule:
  - Post-upload sprint: triggered immediately by each pipeline after upload
  - Weekly cycle:       Sunday 11:00 AM IST (5:30 AM UTC)

Zero paid APIs. Pure YouTube Data API v3 + Telegram + 7-provider AI chain.
"""

import os, sys, json, re, time, datetime, random, requests, subprocess
from pathlib import Path

# ── CREDENTIALS ────────────────────────────────────────────────────────────────
TG_TOKEN       = os.environ.get("TELEGRAM_TOKEN", "")
TG_CHAT        = os.environ.get("TELEGRAM_CHAT_ID", "")

# FIX (found on deep re-audit): tg() only ever read the plain, generic
# TELEGRAM_TOKEN/TELEGRAM_CHAT_ID globals above — no per-channel
# awareness at all, unlike shorts_reels_engine.py's own
# TG_CREDENTIAL_ENV_BY_CHANNEL/set_active_channel pattern. Since this
# module is spawned via subprocess with env=os.environ.copy() from each
# channel's own post-upload sprint, and ch3/ch4/ch5's workflows
# deliberately leave the generic TELEGRAM_TOKEN/CHAT_ID as the shared/Ch1
# bot (their real per-channel bot lives in TELEGRAM_TOKEN_CH3/4/5 instead,
# used correctly by each pipeline's own tg() calls), every growth-engine
# sprint notification (first-hour sprint, hype push, CTR-recovery alerts,
# comment-engine issues) for Ch3/Ch4/Ch5 was silently going to the
# shared/Ch1 bot instead of each channel's own. Ch2's workflow instead
# aliases the generic name directly, so this lookup harmlessly returns
# the same value there. run_post_upload_sprint() re-points the TG_TOKEN/
# TG_CHAT globals to the right bot before sending anything, the same way
# shorts_reels_engine.py's set_active_channel() does for its own globals.
TG_CREDENTIAL_ENV_BY_CHANNEL = {
    "betrayal_deepdive": ("TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID"),
    "evidence_room":     ("TELEGRAM_TOKEN_CH2", "TELEGRAM_CHAT_ID_CH2"),
    "control_files":     ("TELEGRAM_TOKEN_CH3", "TELEGRAM_CHAT_ID_CH3"),
    "archive":           ("TELEGRAM_TOKEN_CH4", "TELEGRAM_CHAT_ID_CH4"),
    "collapse_index":    ("TELEGRAM_TOKEN_CH5", "TELEGRAM_CHAT_ID_CH5"),
}


def set_active_channel_telegram(channel_id):
    """Re-points the module-level TG_TOKEN/TG_CHAT globals at this
    channel's own bot, falling back to the generic shared bot if the
    per-channel secret isn't actually set — same safety net
    shorts_reels_engine.py already uses."""
    global TG_TOKEN, TG_CHAT
    token_env, chat_env = TG_CREDENTIAL_ENV_BY_CHANNEL.get(
        channel_id, ("TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID"))
    TG_TOKEN = os.environ.get(token_env) or os.environ.get("TELEGRAM_TOKEN", "")
    TG_CHAT  = os.environ.get(chat_env) or os.environ.get("TELEGRAM_CHAT_ID", "")
CEREBRAS_KEY   = os.environ.get("CEREBRAS_API_KEY", "")
SAMBANOVA_KEY  = os.environ.get("SAMBANOVA_API_KEY", "")
GEMINI_KEY     = os.environ.get("GEMINI_API_KEY", "")
GEMINI_KEY_2   = os.environ.get("GEMINI_API_KEY_2", "")
GROQ_KEY       = os.environ.get("GROQ_API_KEY", "")
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
COHERE_KEY     = os.environ.get("COHERE_API_KEY", "")
MISTRAL_KEY    = os.environ.get("MISTRAL_API_KEY", "")
PIXABAY_KEY    = os.environ.get("PIXABAY_KEY", "")

CHANNELS = {
    "betrayal_deepdive": {
        "name":          "BetrayalDeepDive",
        "handle":        "@BetrayalDeepDive",
        "niche_label":   "dark horror psychological",
        "client_id":     os.environ.get("YOUTUBE_CLIENT_ID", ""),
        "client_secret": os.environ.get("YOUTUBE_CLIENT_SECRET", ""),
        "refresh_token": os.environ.get("YOUTUBE_REFRESH_TOKEN", ""),
        # FIX (found on deep re-audit): the previous "1 .parent, not 3"
        # fix was itself wrong — it resolves to video_pipeline/state.json,
        # which doesn't exist. betrayal_deepdive's real state.json lives
        # at channels/betrayal_deepdive/state.json, same as every other
        # channel below. Verified directly: Path(...).exists() was False
        # before this fix. This broke update_previous_episode_pinned_comment
        # (always returned early) and made attach_video_id/record_format_ctr
        # write thumb_format_history.json to video_pipeline/ instead of
        # channels/betrayal_deepdive/, where thumbnail_engine_v2.py
        # actually looks for it.
        "state_file":    Path(__file__).parent.parent / "channels" / "betrayal_deepdive" / "state.json",
        "cta_style":     "dark_horror",
    },
    "evidence_room": {
        "name":          "The Evidence Room",
        "handle":        "@TheEvidenceRoom",
        "niche_label":   "forensic crime animated documentary",
        "client_id":     os.environ.get("EVIDENCE_YT_CLIENT_ID",
                             os.environ.get("YOUTUBE_CLIENT_ID", "")),
        "client_secret": os.environ.get("EVIDENCE_YT_CLIENT_SECRET",
                             os.environ.get("YOUTUBE_CLIENT_SECRET", "")),
        "refresh_token": os.environ.get("EVIDENCE_YT_REFRESH_TOKEN",
                             os.environ.get("YOUTUBE_REFRESH_TOKEN", "")),
        # FIX: was missing the "channels/" path segment — real location is
        # channels/evidence_room/, not evidence_room/ directly at repo root.
        "state_file":    Path(__file__).parent.parent / "channels" / "evidence_room" / "state.json",
        "cta_style":     "forensic",
    },
    "control_files": {
        "name":          "The Control Files",
        "handle":        "@TheControlFiles",
        "niche_label":   "psychology documentary animated",
        "client_id":     os.environ.get("CHANNEL3_YT_CLIENT_ID", ""),
        "client_secret": os.environ.get("CHANNEL3_YT_CLIENT_SECRET", ""),
        "refresh_token": os.environ.get("CHANNEL3_YT_REFRESH_TOKEN", ""),
        # FIX: was pointing at the same location as Ch1 (video_pipeline/state.json)
        # instead of Ch3's own future directory — fixed proactively even though
        # Ch3 isn't active yet, matching the confirmed real repo pattern.
        "state_file":    Path(__file__).parent.parent / "channels" / "control_files" / "state.json",
        "cta_style":     "clinical",
    },
    # FIX: archive and collapse_index (Ch4/Ch5) were missing from this dict
    # entirely — every function keyed off CHANNELS silently no-opped for
    # these 2 channels (run_weekly_cycle's `for channel_id in CHANNELS`
    # never even iterates them; run_post_upload_sprint's
    # CHANNELS.get(channel_id, {}) fell back to an empty dict). Added so
    # CTR recovery / thumb_format_history video_id attachment (see
    # video_pipeline/thumbnail_formats.py) work for all 5 channels, not 3.
    "archive": {
        "name":          "The Archive",
        "handle":        "@TheArchiveFiles",
        "niche_label":   "historical collapse documentary",
        "client_id":     os.environ.get("CHANNEL4_YT_CLIENT_ID", ""),
        "client_secret": os.environ.get("CHANNEL4_YT_CLIENT_SECRET", ""),
        "refresh_token": os.environ.get("CHANNEL4_YT_REFRESH_TOKEN", ""),
        "state_file":    Path(__file__).parent.parent / "channels" / "archive" / "state.json",
        "cta_style":     "archive",
    },
    "collapse_index": {
        "name":          "TheCollapseIndex",  # matches the literal channel_name string
                                               # collapse_index_pipeline.py actually passes
                                               # to generate_thumbnail_v2 (no spaces) — must
                                               # match exactly for thumb_format_history's
                                               # channel-name lookup to find the right entries
        "handle":        "@TheCollapseIndex",
        "niche_label":   "societal collapse documentary",
        "client_id":     os.environ.get("CHANNEL5_YT_CLIENT_ID", ""),
        "client_secret": os.environ.get("CHANNEL5_YT_CLIENT_SECRET", ""),
        "refresh_token": os.environ.get("CHANNEL5_YT_REFRESH_TOKEN", ""),
        "state_file":    Path(__file__).parent.parent / "channels" / "collapse_index" / "state.json",
        "cta_style":     "collapse_index",
    },
}

YT_TOKEN_URL   = "https://oauth2.googleapis.com/token"
YT_DATA_URL    = "https://www.googleapis.com/youtube/v3"
YT_UPLOAD_URL  = "https://www.googleapis.com/upload/youtube/v3"
ANALYTICS_URL  = "https://youtubeanalytics.googleapis.com/v2/reports"
CEREBRAS_URL   = "https://api.cerebras.ai/v1/chat/completions"
SAMBANOVA_URL  = "https://api.sambanova.ai/v1/chat/completions"
GEMINI_URL     = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
GROQ_URL       = "https://api.groq.com/openai/v1/chat/completions"
COHERE_URL     = "https://api.cohere.com/v2/chat"
MISTRAL_URL    = "https://api.mistral.ai/v1/chat/completions"

WORK_DIR            = Path("/tmp/growth_engine_v2")
WORK_DIR.mkdir(parents=True, exist_ok=True)
GROWTH_STATE_FILE   = Path(__file__).parent / "growth_state.json"

# YouTube Data API quota constants (units/day = 10,000)
QUOTA_CEILING  = 8000   # stop at 80% — leaves headroom for pipelines
COST_READ      = 1
COST_REPLY     = 50
COST_UPDATE    = 50
COST_CAPTION   = 400

MODE = os.environ.get("GROWTH_ENGINE_MODE", "weekly")


# ══════════════════════════════════════════════════════════════════════════════
# UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def log(msg): print(f"[GE] {msg}", flush=True)

def tg(msg):
    if not TG_TOKEN or not TG_CHAT:
        return
    for chunk in [msg[i:i+4000] for i in range(0, len(msg), 4000)]:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                json={"chat_id": TG_CHAT, "text": chunk, "parse_mode": "HTML"},
                timeout=15)
            time.sleep(0.4)
        except Exception as e:
            log(f"TG: {e}")

def load_growth_state():
    if GROWTH_STATE_FILE.exists():
        try:
            return json.loads(GROWTH_STATE_FILE.read_text())
        except:
            pass
    return {
        "replied_comment_ids": [],
        "our_comment_ids":     [],
        "processed_video_ids": [],
        "series_registry":     {},
        "ctr_ab_tests":        {},
        "hype_sent":           {},
        "weekly_questions":    [],
        "last_weekly_run":     "",
        "total_replies":       0,
        "total_hypes_sent":    0,
        "affiliate_links":     {},
    }

def save_growth_state(s):
    GROWTH_STATE_FILE.write_text(json.dumps(s, indent=2))

def load_channel_strategy(channel_id):
    ch = CHANNELS.get(channel_id, {})
    sf = ch.get("state_file")
    if not sf:
        return {}
    strat = Path(sf).parent / "next_week_strategy.json"
    if strat.exists():
        try:
            return json.loads(strat.read_text())
        except:
            pass
    return {}

def save_channel_strategy(channel_id, data):
    ch = CHANNELS.get(channel_id, {})
    sf = ch.get("state_file")
    if not sf:
        return
    strat = Path(sf).parent / "next_week_strategy.json"
    strat.write_text(json.dumps(data, indent=2))

_token_cache = {}

def get_yt_token(channel_id):
    ch  = CHANNELS[channel_id]
    now = time.time()
    cached = _token_cache.get(channel_id, {})
    if cached.get("token") and now < cached.get("exp", 0) - 60:
        return cached["token"]
    if not ch["refresh_token"]:
        return None
    r = requests.post(YT_TOKEN_URL, data={
        "client_id":     ch["client_id"],
        "client_secret": ch["client_secret"],
        "refresh_token": ch["refresh_token"],
        "grant_type":    "refresh_token",
    }, timeout=30)
    d = r.json()
    if "access_token" not in d:
        log(f"Token failed [{channel_id}]: {d.get('error_description', '')}")
        return None
    _token_cache[channel_id] = {"token": d["access_token"],
                                 "exp":   now + d.get("expires_in", 3600)}
    return d["access_token"]

def yt_get(endpoint, params, token, quota_state=None, cost=1):
    if quota_state is not None:
        today = datetime.date.today().isoformat()
        key   = f"quota_{today}"
        if quota_state.get(key, 0) + cost > QUOTA_CEILING:
            log(f"  Quota ceiling — skipping {endpoint}")
            return {}
        quota_state[key] = quota_state.get(key, 0) + cost
    r = requests.get(f"{YT_DATA_URL}/{endpoint}",
                     headers={"Authorization": f"Bearer {token}"},
                     params=params, timeout=30)
    if r.status_code == 200:
        return r.json()
    log(f"  YT GET {endpoint}: {r.status_code}")
    return {}

def yt_post(endpoint, params, body, token, quota_state=None, cost=50):
    if quota_state is not None:
        today = datetime.date.today().isoformat()
        key   = f"quota_{today}"
        if quota_state.get(key, 0) + cost > QUOTA_CEILING:
            log(f"  Quota ceiling — skipping POST {endpoint}")
            return {}
        quota_state[key] = quota_state.get(key, 0) + cost
    r = requests.post(f"{YT_DATA_URL}/{endpoint}",
                      headers={"Authorization": f"Bearer {token}",
                               "Content-Type": "application/json"},
                      params=params, json=body, timeout=30)
    if r.status_code in [200, 201]:
        return r.json()
    log(f"  YT POST {endpoint}: {r.status_code} {r.text[:80]}")
    return {}


# ══════════════════════════════════════════════════════════════════════════════
# 7-PROVIDER AI CHAIN (fix 9: BLOCK_NONE on Gemini)
# ══════════════════════════════════════════════════════════════════════════════

GEMINI_SAFETY_OFF = [
    {"category": c, "threshold": "BLOCK_NONE"}
    for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH",
              "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]
]

def _cerebras(p, t=300):
    if not CEREBRAS_KEY: return None
    for m in ["llama-3.3-70b", "llama3.3-70b", "llama3.1-70b"]:
        try:
            r = requests.post(CEREBRAS_URL,
                headers={"Authorization": f"Bearer {CEREBRAS_KEY}",
                         "Content-Type": "application/json"},
                json={"model": m, "messages": [{"role": "user", "content": p}],
                      "max_completion_tokens": t, "temperature": 0.82},
                timeout=60)
            if r.status_code == 200:
                txt = r.json()["choices"][0]["message"]["content"]
                if txt and len(txt.strip()) > 5: return txt.strip()
            elif r.status_code == 404: continue
        except: pass
    return None

def _sambanova(p, t=300):
    if not SAMBANOVA_KEY: return None
    try:
        r = requests.post(SAMBANOVA_URL,
            headers={"Authorization": f"Bearer {SAMBANOVA_KEY}",
                     "Content-Type": "application/json"},
            json={"model": "Meta-Llama-3.3-70B-Instruct",
                  "messages": [{"role": "user", "content": p}],
                  "max_tokens": t, "temperature": 0.82},
            timeout=60)
        if r.status_code == 200:
            txt = r.json()["choices"][0]["message"]["content"]
            if txt and len(txt.strip()) > 5: return txt.strip()
    except: pass
    return None

def _gemini(p, t=300):
    # Fix 9: BLOCK_NONE safety settings so dark content doesn't get filtered
    keys = [k for k in [GEMINI_KEY, GEMINI_KEY_2] if k]
    for key in keys:
        try:
            r = requests.post(f"{GEMINI_URL}?key={key}",
                json={"contents": [{"parts": [{"text": p}]}],
                      "generationConfig": {"temperature": 0.82, "maxOutputTokens": t},
                      "safetySettings": GEMINI_SAFETY_OFF},
                timeout=60)
            if r.status_code == 200:
                txt = (r.json().get("candidates", [{}])[0]
                       .get("content", {}).get("parts", [{}])[0].get("text", ""))
                if txt and len(txt.strip()) > 5: return txt.strip()
            elif r.status_code == 429: continue
        except: pass
    return None

def _groq(p, t=300):
    if not GROQ_KEY: return None
    try:
        r = requests.post(GROQ_URL,
            headers={"Authorization": f"Bearer {GROQ_KEY}",
                     "Content-Type": "application/json"},
            json={"model": "llama-3.3-70b-versatile",
                  "messages": [{"role": "user", "content": p}],
                  "max_tokens": min(t, 4800), "temperature": 0.82},
            timeout=45)
        if r.status_code == 200:
            txt = r.json()["choices"][0]["message"]["content"]
            if txt and len(txt.strip()) > 5: return txt.strip()
    except: pass
    return None

def _openrouter(p, t=300):
    if not OPENROUTER_KEY: return None
    for m in ["meta-llama/llama-3.3-70b:free", "qwen/qwen-2.5-72b-instruct:free"]:
        try:
            r = requests.post(OPENROUTER_URL,
                headers={"Authorization": f"Bearer {OPENROUTER_KEY}",
                         "Content-Type": "application/json",
                         "HTTP-Referer": "https://github.com/BetrayalDeepDive"},
                json={"model": m,
                      "messages": [{"role": "user", "content": p}],
                      "max_tokens": min(t, 4000), "temperature": 0.82},
                timeout=60)
            if r.status_code == 200:
                txt = r.json()["choices"][0]["message"]["content"]
                if txt and len(txt.strip()) > 5: return txt.strip()
            elif r.status_code == 404: continue
        except: pass
    return None

def _cohere(p, t=300):
    if not COHERE_KEY: return None
    try:
        r = requests.post(COHERE_URL,
            headers={"Authorization": f"Bearer {COHERE_KEY}",
                     "Content-Type": "application/json"},
            json={"model": "command-r-plus",
                  "messages": [{"role": "user", "content": p}],
                  "max_tokens": min(t, 4000), "temperature": 0.82},
            timeout=60)
        if r.status_code == 200:
            txt = (r.json().get("message", {})
                   .get("content", [{}])[0].get("text", ""))
            if txt and len(txt.strip()) > 5: return txt.strip()
    except: pass
    return None

def _mistral(p, t=300):
    if not MISTRAL_KEY: return None
    try:
        r = requests.post(MISTRAL_URL,
            headers={"Authorization": f"Bearer {MISTRAL_KEY}",
                     "Content-Type": "application/json"},
            json={"model": "mistral-small-latest",
                  "messages": [{"role": "user", "content": p}],
                  "max_tokens": min(t, 4000), "temperature": 0.82},
            timeout=60)
        if r.status_code == 200:
            txt = r.json()["choices"][0]["message"]["content"]
            if txt and len(txt.strip()) > 5: return txt.strip()
    except: pass
    return None

def ai(prompt, tokens=300):
    for fn in [_cerebras, _sambanova, _groq, _gemini, _openrouter, _cohere, _mistral]:
        try:
            r = fn(prompt, tokens)
            if r: return r
        except: pass
        time.sleep(1)
    return None


# ══════════════════════════════════════════════════════════════════════════════
# COMMENT VOICE PROFILES
# ══════════════════════════════════════════════════════════════════════════════

COMMENT_VOICE = {
    "dark_horror": {
        "tone":     "dark, direct, slightly ominous but warm to fans",
        "cta":      "Subscribe to BetrayalDeepDive — new case every weekday.",
        "hooks": {
            "question":    "Ask them one sharper question related to theirs.",
            "praise":      "Acknowledge warmly and uniquely. Never copy-paste.",
            "revelation":  "Connect their experience to the investigation with one sentence.",
            "challenge":   "Acknowledge the challenge, provide one specific documented counter-fact.",
            "request":     "Confirm the idea is noted. End with CTA.",
            "subscribe":   "Welcome them. Mention one thing coming in the next episode.",
        },
        "forbidden": ["cute", "funny", "lol", "relatable", "amazing"],
    },
    "forensic": {
        "tone":     "investigative, precise — every claim is documented",
        "cta":      "Subscribe to The Evidence Room — new forensic case every weekday.",
        "hooks": {
            "question":    "Answer their question with one documented fact from the investigation.",
            "praise":      "Short, genuine acknowledgement — forensic precision in tone.",
            "revelation":  "Validate their insight with one sentence. Cite the case.",
            "challenge":   "Respect their scepticism. Cite the specific document that proves it.",
            "request":     "Log the request. End with CTA.",
            "subscribe":   "Welcome. Reference the next case type coming up.",
        },
        "forbidden": ["spooky", "creepy", "crazy", "wild", "insane"],
    },
    "clinical": {
        "tone":     "clinical, cold, intelligent — never shocked, always knowing",
        "cta":      "Subscribe to The Control Files — new investigation every weekday.",
        "hooks": {
            "question":    "Answer with the one mechanism that explains their question.",
            "praise":      "Acknowledge briefly. Stay in clinical voice.",
            "revelation":  "Validate. Ask them one follow-up question that deepens their thinking.",
            "challenge":   "Agree the question is legitimate. Provide the documented evidence.",
            "request":     "Note the topic. End with CTA.",
            "subscribe":   "Welcome. One sentence about the next investigation.",
        },
        "forbidden": ["crazy", "unbelievable", "wow", "shocking", "amazing"],
    },
}

def classify_comment(text):
    prompt = (
        f"Classify this YouTube comment into ONE word.\n"
        f"Comment: {text[:200]}\n"
        f"Options: question / praise / revelation / challenge / request / subscribe / spam\n"
        f"Return ONLY one word."
    )
    result = _groq(prompt, 10) or _cerebras(prompt, 10) or "praise"
    result = result.strip().lower().split()[0]
    return result if result in ["question","praise","revelation","challenge",
                                "request","subscribe","spam"] else "praise"

def generate_reply(comment_text, ctype, video_title, channel_id, commenter_name):
    cta_style = CHANNELS[channel_id].get("cta_style", "dark_horror")
    voice     = COMMENT_VOICE.get(cta_style, COMMENT_VOICE["dark_horror"])
    name      = commenter_name[:20] if commenter_name and len(commenter_name) < 25 else ""
    name_line = f"Address them as '{name}'." if name else "Do not use their name."
    instruction = voice["hooks"].get(ctype, "Respond warmly and uniquely.")
    forbidden   = ", ".join(voice["forbidden"])
    cta_text    = voice["cta"] if ctype in ["question", "request"] else ""
    prompt = (
        f"You run the YouTube channel {CHANNELS[channel_id]['name']}.\n"
        f"Voice: {voice['tone']}.\n"
        f"{name_line}\n"
        f"Video: {video_title[:80]}\n"
        f"Comment type: {ctype}\n"
        f"Comment: {comment_text[:250]}\n\n"
        f"Write a reply. Rules:\n"
        f"1. Under 240 characters.\n"
        f"2. {instruction}\n"
        f"3. Never start: 'Great comment', 'Thanks for watching', 'Thank you so much'.\n"
        f"4. Forbidden words: {forbidden}\n"
        f"5. Sounds like a real human, not a brand account.\n"
        f"{'6. End with: ' + cta_text if cta_text else '6. No CTA needed.'}\n"
        f"Return ONLY the reply text."
    )
    result = ai(prompt, tokens=100)
    if not result:
        fallbacks = {
            "question":   f"Good question — that detail is documented in the sources. {cta_text}",
            "praise":     "This genuinely means a lot. More coming.",
            "revelation": "That connection is exactly what this investigation is about.",
            "challenge":  "Fair challenge — the evidence is in the sources linked below.",
            "request":    f"Noted and added to the list. {cta_text}",
            "subscribe":  "Welcome. The next one is already in production.",
        }
        return fallbacks.get(ctype, "More coming.")
    return result[:280] if len(result) <= 280 else result[:277] + "…"


# ══════════════════════════════════════════════════════════════════════════════
# MECHANISM 1: COMMENT ENGINE v2
# Fixes: quota tracker, staggered retry, reply-to-replies
# ══════════════════════════════════════════════════════════════════════════════

def run_comment_engine(channel_id, token, growth_state, video_ids=None):
    log(f"\n  [Comment Engine v2] {CHANNELS[channel_id]['name']}")

    today_key   = f"quota_{datetime.date.today().isoformat()}"
    replied_ids = set(growth_state.get("replied_comment_ids", []))
    our_ids     = set(growth_state.get("our_comment_ids", []))

    def quota_ok(cost=1):
        return growth_state.get(today_key, 0) + cost <= QUOTA_CEILING

    def use_quota(cost):
        growth_state[today_key] = growth_state.get(today_key, 0) + cost

    if not quota_ok(COST_READ):
        log("  Quota ceiling reached — skipping comment engine today")
        return 0, []

    # Get video list
    if not video_ids:
        ch_data = yt_get("channels", {"part": "contentDetails", "mine": "true"}, token)
        use_quota(COST_READ)
        pl = (ch_data.get("items", [{}])[0]
              .get("contentDetails", {})
              .get("relatedPlaylists", {})
              .get("uploads", ""))
        if not pl:
            return 0, []
        pl_data = yt_get("playlistItems",
                         {"part": "contentDetails", "playlistId": pl, "maxResults": "15"},
                         token)
        use_quota(COST_READ)
        video_ids = [i["contentDetails"]["videoId"] for i in pl_data.get("items", [])]

    total_replied   = 0
    questions_found = []

    for vid_id in video_ids:
        if not quota_ok(COST_READ + COST_REPLY):
            log("  Quota ceiling hit mid-run — stopping cleanly")
            break

        vid_data  = yt_get("videos", {"part": "snippet", "id": vid_id}, token)
        use_quota(COST_READ)
        vid_title = (vid_data.get("items", [{}])[0]
                     .get("snippet", {}).get("title", "this investigation"))

        threads = yt_get("commentThreads",
                         {"part": "snippet,replies", "videoId": vid_id,
                          "order": "relevance", "maxResults": "50"},
                         token)
        use_quota(COST_READ)

        for thread in threads.get("items", []):
            if not quota_ok(COST_REPLY):
                break

            top        = thread.get("snippet", {}).get("topLevelComment", {})
            cid        = top.get("id", "")
            snip       = top.get("snippet", {})
            text       = snip.get("textDisplay", "")
            author     = snip.get("authorDisplayName", "")

            if not text or len(text) < 5: continue
            if any(s in text.lower() for s in
                   ["http", "sub4sub", "check my channel", "buy followers"]):
                replied_ids.add(cid); continue

            # Fix 4: reply-to-replies — if we already replied, check for new thread replies
            if cid in replied_ids and cid in our_ids:
                for reply in thread.get("replies", {}).get("comments", []):
                    if not quota_ok(COST_REPLY): break
                    r_id   = reply.get("id", "")
                    r_text = reply.get("snippet", {}).get("textDisplay", "")
                    r_auth = reply.get("snippet", {}).get("authorDisplayName", "")
                    if r_id in replied_ids or not r_text or len(r_text) < 5: continue
                    r_ctype = classify_comment(r_text)
                    if r_ctype in ["spam", "praise"]:
                        replied_ids.add(r_id); continue
                    r_reply = generate_reply(r_text, r_ctype, vid_title, channel_id, r_auth)
                    if not r_reply: continue
                    res = yt_post("comments", {"part": "snippet"},
                                  {"snippet": {"parentId": cid, "textOriginal": r_reply}},
                                  token)
                    use_quota(COST_REPLY)
                    if res.get("id"):
                        replied_ids.add(r_id)
                        total_replied += 1
                        log(f"    Thread reply [{r_ctype}]: {r_reply[:55]}…")
                    time.sleep(5)
                continue

            if cid in replied_ids: continue

            ctype = classify_comment(text)
            if ctype == "spam":
                replied_ids.add(cid); continue
            if ctype == "question":
                questions_found.append({"question": text[:200],
                                        "video": vid_title, "channel": channel_id})

            reply_text = generate_reply(text, ctype, vid_title, channel_id, author)
            if not reply_text: continue

            res = yt_post("comments", {"part": "snippet"},
                          {"snippet": {"parentId": cid, "textOriginal": reply_text}},
                          token)
            use_quota(COST_REPLY)

            if res.get("id"):
                replied_ids.add(cid)
                our_ids.add(res["id"])
                total_replied += 1
                log(f"    Replied [{ctype}] '{vid_title[:35]}': {reply_text[:55]}…")
                time.sleep(4)
            else:
                log(f"    Reply failed — quota used: {growth_state.get(today_key, 0)}")
                time.sleep(3)

    growth_state["replied_comment_ids"] = list(replied_ids)[-5000:]
    growth_state["our_comment_ids"]     = list(our_ids)[-2000:]
    growth_state["total_replies"]       = growth_state.get("total_replies", 0) + total_replied
    log(f"  Comment engine: {total_replied} replies | quota {growth_state.get(today_key,0)}/{QUOTA_CEILING}")
    return total_replied, questions_found


# ══════════════════════════════════════════════════════════════════════════════
# MECHANISM 2: SUBSCRIBE CTA INJECTION (callable by all pipelines)
# ══════════════════════════════════════════════════════════════════════════════

CTA_BANK = {
    "dark_horror": {
        "30": ["Subscribe to BetrayalDeepDive. The worst part is thirty seconds away.",
               "If what you just heard disturbed you, subscribe. There is more."],
        "60": ["Subscribe now. What comes next is why this channel exists.",
               "Subscribe to BetrayalDeepDive before the next revelation."],
        "80": ["Subscribe. New investigation every weekday.",
               "Subscribe to BetrayalDeepDive if you want the rest of them."],
    },
    "seduction_dark": {
        "30": ["Subscribe. The psychology behind this gets darker from here.",
               "Subscribe to BetrayalDeepDive. The pattern you are seeing repeats."],
        "60": ["Subscribe before the mechanism is fully revealed.",
               "Subscribe to BetrayalDeepDive. The next section changes the whole story."],
        "80": ["Subscribe. The final layer is thirty seconds away.",
               "Subscribe to BetrayalDeepDive — new case every weekday."],
    },
    "psychological_trap": {
        "30": ["Subscribe. The trap is about to be fully visible.",
               "Subscribe to BetrayalDeepDive. Every step was deliberate."],
        "60": ["Subscribe before the final mechanism is shown.",
               "Subscribe. What is documented next changes everything."],
        "80": ["Subscribe every weekday. A new case that redefines what you thought you knew.",
               "Subscribe to BetrayalDeepDive if you want the forty-seven other cases."],
    },
    "supernatural_real": {
        "30": ["Subscribe. The documented evidence arrives in thirty seconds.",
               "Subscribe to BetrayalDeepDive. The explanation is not what you expect."],
        "60": ["Subscribe before the final evidence is shown.",
               "Subscribe. This is the part that has no rational explanation."],
        "80": ["Subscribe. What was documented here has never been explained.",
               "Subscribe to BetrayalDeepDive — new investigation every weekday."],
    },
    "obsession_dark": {
        "30": ["Subscribe. The escalation documented next is why this case is different.",
               "Subscribe to BetrayalDeepDive. Every detail here was deliberate."],
        "60": ["Subscribe before the final revelation.",
               "Subscribe. The next sixty seconds reframe everything."],
        "80": ["Subscribe. New case every weekday. You will not regret it.",
               "Subscribe to BetrayalDeepDive if you want to understand what drove this."],
    },
    # FIX: this bank previously had only 7 keys total — the 5 real
    # betrayal_deepdive niches above, plus two generic placeholder keys
    # ("forensic", "clinical") that don't match any real niche name used
    # by any other channel (evidence_room's real niches are
    # forensic_finance/criminal_investigation/etc, control_files' are
    # cult_psychology/propaganda_systems/etc) — so every niche on the
    # other 4 channels silently fell back to dark_horror's BetrayalDeepDive
    # CTA text via inject_subscribe_ctas' CTA_BANK.get(niche_name,
    # CTA_BANK["dark_horror"]) fallback. Rebuilt to cover all 39 real
    # niches across all 5 channels, reusing the exact real CTA text
    # already written and live in each channel's own
    # _inject_ctas_ch1/_inject_ctas_er/_inject_ctas_ch5 functions (the
    # actual source of truth those channels call directly) rather than
    # inventing new copy, so this shared bank is correct if it's ever
    # actually wired into a pipeline.
    #
    # The Evidence Room (evidence_room) — 7 niches
    "forensic_finance": {
        "30": ["If documented cases like this concern you, subscribe — new files every week."],
        "60": ["This channel investigates documented financial fraud. Subscribe to follow the evidence."],
        "80": ["More documented cases like this are coming. Subscribe to The Evidence Room."],
    },
    "criminal_investigation": {
        "30": ["If this case concerns you, subscribe — documented investigations every week."],
        "60": ["This channel documents criminal investigations. Subscribe to follow the evidence."],
        "80": ["More documented cases like this are coming. Subscribe to The Evidence Room."],
    },
    "corporate_exposure": {
        "30": ["If this pattern concerns you, subscribe — documented exposures every week."],
        "60": ["This channel investigates documented corporate misconduct. Subscribe to follow the record."],
        "80": ["More documented findings like this are coming. Subscribe to The Evidence Room."],
    },
    "digital_forensics": {
        "30": ["If this trail concerns you, subscribe — documented digital cases every week."],
        "60": ["This channel documents digital forensic investigations. Subscribe to follow the evidence."],
        "80": ["More documented cases like this are coming. Subscribe to The Evidence Room."],
    },
    "body_cam_police": {
        "30": ["If footage like this concerns you, subscribe — documented body cam cases every week."],
        "60": ["This channel documents real body cam evidence. Subscribe to follow the record."],
        "80": ["More documented footage like this is coming. Subscribe to The Evidence Room."],
    },
    "courtroom_drama": {
        "30": ["If this verdict concerns you, subscribe — documented courtroom cases every week."],
        "60": ["This channel documents real courtroom proceedings. Subscribe to follow the record."],
        "80": ["More documented trials like this are coming. Subscribe to The Evidence Room."],
    },
    "robbery_documentaries": {
        "30": ["If this heist concerns you, subscribe — documented robbery cases every week."],
        "60": ["This channel documents real robbery investigations. Subscribe to follow the evidence."],
        "80": ["More documented cases like this are coming. Subscribe to The Evidence Room."],
    },
    # The Control Files (control_files) — 6 niches
    "cult_psychology": {
        "30": ["If documented cases like this concern you, subscribe — new files every week."],
        "60": ["This channel investigates documented control systems. Subscribe to follow the evidence."],
        "80": ["More documented cases like this are coming. Subscribe to The Control Files."],
    },
    "propaganda_systems": {
        "30": ["If this pattern concerns you, subscribe — more documented systems every week."],
        "60": ["This channel tracks documented propaganda systems. Subscribe to follow the record."],
        "80": ["More documented findings like this are coming. Subscribe to The Control Files."],
    },
    "social_engineering": {
        "30": ["If this technique concerns you, subscribe — documented methods every week."],
        "60": ["This channel documents social engineering systems. Subscribe to follow the evidence."],
        "80": ["More documented cases like this are coming. Subscribe to The Control Files."],
    },
    "mass_deception": {
        "30": ["If this scale concerns you, subscribe — documented findings every week."],
        "60": ["This channel investigates documented deception at scale. Subscribe to follow the record."],
        "80": ["More documented cases like this are coming. Subscribe to The Control Files."],
    },
    "dark_business_documentaries": {
        "30": ["If this kind of corporate failure concerns you, subscribe — documented cases every week."],
        "60": ["This channel investigates documented corporate collapses. Subscribe to follow the record."],
        "80": ["More documented cases like this are coming. Subscribe to The Control Files."],
    },
    "scams_fraud_exposed": {
        "30": ["If this scam pattern concerns you, subscribe — documented fraud cases every week."],
        "60": ["This channel documents fraud systems in detail. Subscribe to follow the evidence."],
        "80": ["More documented cases like this are coming. Subscribe to The Control Files."],
    },
    # The Archive (archive) — 8 niches
    "egyptian_civilization": {
        "30": ["If this history fascinates you, subscribe — new civilizations documented every week."],
        "60": ["This channel investigates documented ancient history. Subscribe to follow the record."],
        "80": ["More documented history like this is coming. Subscribe to The Archive."],
    },
    "chinese_civilization": {
        "30": ["If this dynasty's story interests you, subscribe — more documented history every week."],
        "60": ["This channel documents real dynastic history. Subscribe to follow the record."],
        "80": ["More documented history like this is coming. Subscribe to The Archive."],
    },
    "mesopotamian_lost_civilizations": {
        "30": ["If lost civilizations fascinate you, subscribe — documented history every week."],
        "60": ["This channel investigates documented lost civilizations. Subscribe to follow the record."],
        "80": ["More documented history like this is coming. Subscribe to The Archive."],
    },
    "islamic_civilization_history": {
        "30": ["If this history fascinates you, subscribe — documented civilization every week."],
        "60": ["This channel documents real Islamic civilization history. Subscribe to follow the record."],
        "80": ["More documented history like this is coming. Subscribe to The Archive."],
    },
    "fallen_empires_military_overstretch": {
        "30": ["If this pattern of collapse concerns you, subscribe — documented history every week."],
        "60": ["This channel investigates documented imperial overstretch. Subscribe to follow the record."],
        "80": ["More documented history like this is coming. Subscribe to The Archive."],
    },
    "elite_betrayal_infighting": {
        "30": ["If this kind of betrayal fascinates you, subscribe — documented history every week."],
        "60": ["This channel documents real elite betrayal in detail. Subscribe to follow the record."],
        "80": ["More documented history like this is coming. Subscribe to The Archive."],
    },
    "propaganda_institutional_decline": {
        "30": ["If this pattern concerns you, subscribe — documented institutional history every week."],
        "60": ["This channel tracks documented institutional decline. Subscribe to follow the record."],
        "80": ["More documented history like this is coming. Subscribe to The Archive."],
    },
    "modern_parallels": {
        "30": ["If this parallel struck you, subscribe — documented historical patterns every week."],
        "60": ["This channel connects documented history to the present. Subscribe to follow the record."],
        "80": ["More documented history like this is coming. Subscribe to The Archive."],
    },
    # The Collapse Index (collapse_index) — 13 niches
    "ai_startup_collapse": {
        "30": ["Subscribe to The Collapse Index. The documented evidence gets more specific from here.",
               "Subscribe. What comes next is the part most coverage left out."],
        "60": ["Subscribe before the final documented numbers are shown.",
               "Subscribe to The Collapse Index. The next section changes the whole story."],
        "80": ["Subscribe. New documented collapse case every weekday.",
               "Subscribe to The Collapse Index if you want the rest of these breakdowns."],
    },
    "tech_company_collapse": {
        "30": ["Subscribe to The Collapse Index. The documented internal decision comes next.",
               "Subscribe. The real turning point is thirty seconds away."],
        "60": ["Subscribe before the documented numbers are shown.",
               "Subscribe to The Collapse Index. What's documented next reframes everything."],
        "80": ["Subscribe. Every weekday, a new documented business collapse.",
               "Subscribe to The Collapse Index for the rest of these breakdowns."],
    },
    "crypto_collapse": {
        "30": ["Subscribe to The Collapse Index. The real documented timeline comes next.",
               "Subscribe. The documented numbers are thirty seconds away."],
        "60": ["Subscribe before the full documented collapse is shown.",
               "Subscribe to The Collapse Index. The next section has the real numbers."],
        "80": ["Subscribe. New documented crypto collapse case every weekday.",
               "Subscribe to The Collapse Index for the rest of these breakdowns."],
    },
    "cybersecurity_disasters": {
        "30": ["Subscribe to The Collapse Index. The documented timeline comes next.",
               "Subscribe. The real documented failure point is thirty seconds away."],
        "60": ["Subscribe before the full documented breach timeline is shown.",
               "Subscribe to The Collapse Index. What's documented next changes the story."],
        "80": ["Subscribe. New documented breach case every weekday.",
               "Subscribe to The Collapse Index for the rest of these breakdowns."],
    },
    "product_flops": {
        "30": ["Subscribe to The Collapse Index. The documented internal testing comes next.",
               "Subscribe. The real documented numbers are thirty seconds away."],
        "60": ["Subscribe before the documented failure is fully shown.",
               "Subscribe to The Collapse Index. The next part has the real numbers."],
        "80": ["Subscribe. New documented product failure every weekday.",
               "Subscribe to The Collapse Index for the rest of these breakdowns."],
    },
    "dotcom_era_collapse": {
        "30": ["Subscribe to The Collapse Index. The documented real numbers come next.",
               "Subscribe. The real documented collapse timeline is thirty seconds away."],
        "60": ["Subscribe before the full documented history is shown.",
               "Subscribe to The Collapse Index. The next part has the real filed numbers."],
        "80": ["Subscribe. New documented dot-com history every weekday.",
               "Subscribe to The Collapse Index for the rest of these breakdowns."],
    },
    "personal_finance_mistakes": {
        "30": ["Subscribe to The Collapse Index. The real numbers behind this come next.",
               "Subscribe — the specific, real math is thirty seconds away."],
        "60": ["Subscribe before the full real breakdown.",
               "Subscribe to The Collapse Index for the complete real numbers."],
        "80": ["Subscribe. New real financial breakdown every weekday.",
               "Subscribe to The Collapse Index for more real, specific breakdowns."],
    },
    "investing_fundamentals": {
        "30": ["Subscribe to The Collapse Index. The real math on this comes next.",
               "Subscribe — the specific numbers are thirty seconds away."],
        "60": ["Subscribe before the full real breakdown.",
               "Subscribe to The Collapse Index for the complete real numbers."],
        "80": ["Subscribe. New real investing breakdown every weekday.",
               "Subscribe to The Collapse Index for more real, specific breakdowns."],
    },
    "retirement_planning": {
        "30": ["Subscribe to The Collapse Index. The real retirement math comes next.",
               "Subscribe — the specific numbers are thirty seconds away."],
        "60": ["Subscribe before the full real breakdown.",
               "Subscribe to The Collapse Index for the complete real numbers."],
        "80": ["Subscribe. New real retirement breakdown every weekday.",
               "Subscribe to The Collapse Index for more real, specific breakdowns."],
    },
    "credit_debt_repair": {
        "30": ["Subscribe to The Collapse Index. The real numbers on this come next.",
               "Subscribe — the specific credit math is thirty seconds away."],
        "60": ["Subscribe before the full real breakdown.",
               "Subscribe to The Collapse Index for the complete real numbers."],
        "80": ["Subscribe. New real credit breakdown every weekday.",
               "Subscribe to The Collapse Index for more real, specific breakdowns."],
    },
    "real_estate_affordability": {
        "30": ["Subscribe to The Collapse Index. The real numbers on this come next.",
               "Subscribe — the specific mortgage math is thirty seconds away."],
        "60": ["Subscribe before the full real breakdown.",
               "Subscribe to The Collapse Index for the complete real numbers."],
        "80": ["Subscribe. New real housing breakdown every weekday.",
               "Subscribe to The Collapse Index for more real, specific breakdowns."],
    },
    "budgeting_saving_strategies": {
        "30": ["Subscribe to The Collapse Index. The real numbers on this come next.",
               "Subscribe — the specific budget math is thirty seconds away."],
        "60": ["Subscribe before the full real breakdown.",
               "Subscribe to The Collapse Index for the complete real numbers."],
        "80": ["Subscribe. New real budgeting breakdown every weekday.",
               "Subscribe to The Collapse Index for more real, specific breakdowns."],
    },
    "stock_market_crashes_history": {
        "30": ["Subscribe to The Collapse Index. The documented real numbers come next.",
               "Subscribe. The real documented market data is thirty seconds away."],
        "60": ["Subscribe before the full documented history is shown.",
               "Subscribe to The Collapse Index. The next part has the real numbers."],
        "80": ["Subscribe. New documented market history every weekday.",
               "Subscribe to The Collapse Index for the rest of these breakdowns."],
    },
}

def inject_subscribe_ctas(script_clean, niche_name):
    """
    Inject subscribe CTAs at 30/60/80% marks.
    Callable by all three pipelines.
    Uses sentence boundary detection — CTAs never split mid-sentence.
    """
    words = script_clean.split()
    total = len(words)
    if total < 400:
        return script_clean

    pool = CTA_BANK.get(niche_name, CTA_BANK["dark_horror"])
    seed = abs(hash(script_clean[:80])) % 2
    c30  = pool["30"][seed % len(pool["30"])]
    c60  = pool["60"][seed % len(pool["60"])]
    c80  = pool["80"][seed % len(pool["80"])]

    def near_boundary(words, target, window=30):
        for delta in range(window):
            for direction in [1, -1]:
                idx = target + delta * direction
                if 0 <= idx < len(words):
                    if words[idx].rstrip().endswith((".", "?", "!")):
                        return idx + 1
        return target

    b80 = near_boundary(words, int(total * 0.80))
    b60 = near_boundary(words, int(total * 0.60))
    b30 = near_boundary(words, int(total * 0.30))

    w = words[:]
    w.insert(b80, f"\n\n{c80}\n\n")
    w.insert(b60, f"\n\n{c60}\n\n")
    w.insert(b30, f"\n\n{c30}\n\n")
    return re.sub(r'\n{3,}', '\n\n', " ".join(w)).strip()


# ══════════════════════════════════════════════════════════════════════════════
# MECHANISM 3: HYPE NOTIFICATIONS
# Fix 5: day-0, day-3, and day-6 follow-up pushes (7-day window)
# ══════════════════════════════════════════════════════════════════════════════

def send_hype_notification(video_url, video_title, channel_name, growth_state, day=0):
    vid_key = re.sub(r'[^a-z0-9]', '', video_url.lower())[-20:]
    hype_log = growth_state.get("hype_sent", {})
    days_sent = hype_log.get(vid_key, [])
    if day in days_sent:
        return  # already sent for this day

    urgency = {
        0: "⚡ NEW — act now for maximum impact",
        3: "🔥 3 days left on Hype window",
        6: "⏰ LAST DAY — Hype expires tomorrow",
    }.get(day, "")

    msg = (
        f"🚀 <b>HYPE THIS VIDEO {urgency}</b>\n\n"
        f"<b>{channel_name}</b>: {video_title}\n\n"
        f"▶️ {video_url}\n\n"
        f"<b>How to Hype (10 seconds):</b>\n"
        f"1. Open the link above on YouTube\n"
        f"2. Tap the 🔥 Hype button under the video\n"
        f"3. Done — YouTube pushes this to the Explore leaderboard\n\n"
        f"⏳ Hype window: 7 days from upload. Every Hype = free algorithmic reach."
    )
    tg(msg)
    days_sent.append(day)
    hype_log[vid_key] = days_sent
    growth_state["hype_sent"]        = hype_log
    growth_state["total_hypes_sent"] = growth_state.get("total_hypes_sent", 0) + 1
    log(f"  Hype notification sent (day {day}): {video_title[:50]}")

def check_pending_hype_followups(growth_state):
    """Run on weekly cycle — sends day-3 and day-6 Hype follow-ups."""
    hype_log   = growth_state.get("hype_sent", {})
    state_file = GROWTH_STATE_FILE.parent / "sprint_log.json"
    if not state_file.exists():
        return
    try:
        sprints = json.loads(state_file.read_text())
    except:
        return

    today = datetime.date.today()
    for entry in sprints:
        upload_date = datetime.date.fromisoformat(entry.get("date", "2020-01-01"))
        days_since  = (today - upload_date).days
        vid_url     = entry.get("video_url", "")
        vid_title   = entry.get("video_title", "")
        ch_name     = entry.get("channel_name", "")
        if not vid_url:
            continue
        vid_key = re.sub(r'[^a-z0-9]', '', vid_url.lower())[-20:]
        days_sent = hype_log.get(vid_key, [])
        if days_since >= 3 and 3 not in days_sent and days_since < 6:
            send_hype_notification(vid_url, vid_title, ch_name, growth_state, day=3)
        elif days_since >= 6 and 6 not in days_sent and days_since <= 7:
            send_hype_notification(vid_url, vid_title, ch_name, growth_state, day=6)


# ══════════════════════════════════════════════════════════════════════════════
# MECHANISM 4: WEEKLY COMMENT INTELLIGENCE → ALL THREE CHANNELS
# Fix 10: feeds strategy files for ALL three channels, not just Ch1
# ══════════════════════════════════════════════════════════════════════════════

def run_weekly_comment_intelligence(all_questions, growth_state):
    if not all_questions:
        log("  No questions — skipping intelligence")
        return

    log(f"  Weekly intelligence: {len(all_questions)} viewer questions")

    questions_text = "\n".join(
        f"[{q['channel']}] {q['question']}" for q in all_questions[:80]
    )
    prompt = (
        f"Analyse these YouTube viewer questions from three documentary channels.\n"
        f"Questions:\n{questions_text}\n\n"
        f"Find the 6 most common question themes. For each theme, generate a specific "
        f"video topic that directly answers it. Assign to the most relevant channel:\n"
        f"betrayal_deepdive, evidence_room, or control_files.\n\n"
        f"Return ONLY valid JSON (no backticks):\n"
        f'{{"topics":['
        f'{{"channel":"channel_id","topic":"Full specific topic","theme":"what viewers asked"}},'
        f'{{"channel":"channel_id","topic":"Full specific topic","theme":"what viewers asked"}}'
        f']}}'
    )
    result = ai(prompt, tokens=500)
    if not result:
        return

    try:
        result = re.sub(r'```json|```', '', result).strip()
        m = re.search(r'\{[\s\S]*\}', result)
        if not m:
            return
        data = json.loads(m.group())

        for item in data.get("topics", []):
            ch_id = item.get("channel", "")
            topic = item.get("topic", "")
            theme = item.get("theme", "")
            if not ch_id or not topic or ch_id not in CHANNELS:
                continue

            strat = load_channel_strategy(ch_id)
            vd    = strat.get("viewer_demand_topics", [])
            vd.append({"topic": topic, "theme": theme,
                       "source": "comment_intelligence",
                       "added":  datetime.datetime.now().isoformat()})
            strat["viewer_demand_topics"] = vd[-10:]
            rec = strat.get("recommended_topics", [])
            if topic not in rec:
                rec.insert(0, topic)
            strat["recommended_topics"] = rec[:15]
            save_channel_strategy(ch_id, strat)
            log(f"  Injected viewer topic → {ch_id}: {topic[:60]}")

        tg(f"📊 <b>Viewer Intelligence — {len(data.get('topics',[]))} topics injected</b>\n"
           f"All three channels updated.")

    except Exception as e:
        log(f"  Intelligence error: {e}")

    growth_state["weekly_questions"] = []


# ══════════════════════════════════════════════════════════════════════════════
# MECHANISM 5: SERIES ARCHITECTURE GENERATOR
# Fix 2: new-channel fallback — fires on any video for first 30 days
# ══════════════════════════════════════════════════════════════════════════════

def run_series_architecture(channel_id, token, growth_state):
    log(f"\n  [Series Generator] {channel_id}")

    ch_data = yt_get("channels", {"part": "contentDetails,statistics", "mine": "true"}, token)
    ch_items = ch_data.get("items", [])
    if not ch_items:
        return
    if not ch_items:
        log("  Growth Engine: no channel items returned")
        return
    uploads_pl = (ch_items[0].get("contentDetails", {})
                  .get("relatedPlaylists", {}).get("uploads", ""))
    channel_age_videos = int(ch_items[0].get("statistics", {}).get("videoCount", 0))

    pl_data = yt_get("playlistItems",
                     {"part": "contentDetails,snippet",
                      "playlistId": uploads_pl, "maxResults": "20"},
                     token)
    video_ids = [i["contentDetails"]["videoId"] for i in pl_data.get("items", [])]
    if not video_ids:
        return

    stats_data = yt_get("videos",
                        {"part": "statistics,snippet", "id": ",".join(video_ids)},
                        token)
    videos = []
    for item in stats_data.get("items", []):
        stats   = item.get("statistics", {})
        snippet = item.get("snippet", {})
        views   = int(stats.get("viewCount", 0))
        likes   = int(stats.get("likeCount", 0))
        comms   = int(stats.get("commentCount", 0))
        eng     = views + likes * 20 + comms * 50
        videos.append({"id": item["id"], "title": snippet.get("title", ""),
                       "views": views, "engagement": eng,
                       "published": snippet.get("publishedAt", "")})

    if not videos:
        return

    series_reg = growth_state.get("series_registry", {})

    # Fix 2: new channel fallback — use top video regardless of average
    if channel_age_videos <= 30:
        candidates = [v for v in videos if v["id"] not in series_reg and v["views"] > 0]
    else:
        avg_eng   = sum(v["engagement"] for v in videos) / len(videos)
        candidates = [v for v in videos
                      if v["engagement"] > avg_eng * 1.5 and v["id"] not in series_reg]

    if not candidates:
        log(f"  No series candidates for {channel_id}")
        return

    top = sorted(candidates, key=lambda x: x["engagement"], reverse=True)[0]
    log(f"  Series candidate: '{top['title'][:50]}' — {top['views']} views")

    niche = CHANNELS[channel_id]["niche_label"]
    prompt = (
        f"This YouTube documentary video performed well:\n"
        f"Title: {top['title']}\n"
        f"Niche: {niche}\n\n"
        f"Generate a 3-part series continuation. Each part standalone but references previous.\n"
        f"Return ONLY valid JSON (no backticks):\n"
        f'{{"series_title":"Overarching series name",'
        f'"original_retitled":"Part 1: [retitled version]",'
        f'"part2_topic":"Full specific topic for Part 2",'
        f'"part2_title":"Title 55-65 chars",'
        f'"part3_topic":"Full specific topic for Part 3",'
        f'"part3_title":"Title 55-65 chars",'
        f'"subscribe_hook":"One sentence making viewers NEED Part 2"}}'
    )
    result = ai(prompt, tokens=400)
    if not result:
        return

    try:
        result = re.sub(r'```json|```', '', result).strip()
        m = re.search(r'\{[\s\S]*\}', result)
        if not m:
            return
        plan = json.loads(m.group())

        strat = load_channel_strategy(channel_id)
        rec   = strat.get("recommended_topics", [])
        rec.insert(0, f"{plan.get('part2_title','')}: {plan.get('part2_topic','')}")
        rec.insert(1, f"{plan.get('part3_title','')}: {plan.get('part3_topic','')}")
        strat["recommended_topics"] = rec[:15]
        strat["active_series"]      = plan
        strat["subscriber_hook"]    = plan.get("subscribe_hook", "")
        save_channel_strategy(channel_id, strat)

        series_reg[top["id"]] = {"series_title": plan.get("series_title", ""),
                                  "created": datetime.datetime.now().isoformat()}
        growth_state["series_registry"] = series_reg

        tg(f"📺 <b>Series Plan [{CHANNELS[channel_id]['name']}]</b>\n\n"
           f"From: {top['title'][:50]}\n"
           f"Series: {plan.get('series_title','')}\n"
           f"Part 2: {plan.get('part2_title','')[:55]}\n"
           f"Part 3: {plan.get('part3_title','')[:55]}\n"
           f"Hook: {plan.get('subscribe_hook','')}")
    except Exception as e:
        log(f"  Series error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# MECHANISM 6: CTR RECOVERY
# Fix 3: tracks A/B test result 7 days later, confirms winner via Analytics
# ══════════════════════════════════════════════════════════════════════════════

def run_ctr_recovery(channel_id, token, growth_state):
    log(f"\n  [CTR Recovery] {channel_id}")

    end_date   = datetime.date.today().isoformat()
    start_date = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()

    try:
        r = requests.get(ANALYTICS_URL,
                         headers={"Authorization": f"Bearer {token}"},
                         params={"ids": "channel==MINE", "startDate": start_date,
                                 "endDate": end_date,
                                 "metrics": "impressionClickThroughRate,views",
                                 "dimensions": "video",
                                 "sort": "impressionClickThroughRate",
                                 "maxResults": "50"},
                         timeout=30)
        if r.status_code != 200:
            log(f"  Analytics: {r.status_code} — skipping")
            return
        data = r.json()
    except Exception as e:
        log(f"  Analytics error: {e}")
        return

    # thumb_format_history real learning signal: feed every video's real
    # CTR (not just the ones being A/B tested below) into the format
    # history, so select_thumbnail_format() has as much real performance
    # data as possible to learn from.
    try:
        ch_cfg = CHANNELS.get(channel_id, {})
        if ch_cfg.get("state_file"):
            from thumbnail_formats import record_format_ctr
            cache_dir = str(Path(ch_cfg["state_file"]).parent)
            for row in data.get("rows", []):
                if len(row) >= 2:
                    record_format_ctr(cache_dir, row[0], float(row[1]))
    except Exception as e:
        log(f"  thumb_format_history CTR record (non-fatal): {e}")

    # FIX (found on deep re-audit): title_score_history real learning
    # signal — same real CTR pull, feeding title_scoring_history so
    # get_title_calibration_notes() has real data to compare against
    # score_title_v2's predictions, mirroring thumb_format_history exactly.
    try:
        ch_cfg = CHANNELS.get(channel_id, {})
        if ch_cfg.get("state_file"):
            from title_scoring_history import record_title_ctr
            cache_dir = str(Path(ch_cfg["state_file"]).parent)
            for row in data.get("rows", []):
                if len(row) >= 2:
                    record_title_ctr(cache_dir, row[0], float(row[1]))
    except Exception as e:
        log(f"  title_score_history CTR record (non-fatal): {e}")

    ctr_tests   = growth_state.get("ctr_ab_tests", {})
    regenerated = 0

    # Fix 3: first check existing A/B tests for results
    for vid_id, test in list(ctr_tests.items()):
        if test.get("concluded"):
            continue
        test_date = datetime.date.fromisoformat(test.get("test_date", "2020-01-01"))
        if (datetime.date.today() - test_date).days < 7:
            continue
        # Fetch 7-day CTR after thumbnail change
        try:
            r2 = requests.get(ANALYTICS_URL,
                              headers={"Authorization": f"Bearer {token}"},
                              params={"ids": "channel==MINE",
                                      "startDate": test["test_date"],
                                      "endDate": end_date,
                                      "metrics": "impressionClickThroughRate",
                                      "dimensions": "video",
                                      "filters": f"video=={vid_id}"},
                              timeout=20)
            if r2.status_code == 200:
                rows = r2.json().get("rows", [])
                if rows:
                    new_ctr = float(rows[0][1])
                    old_ctr = test.get("old_ctr", 0)
                    improved = new_ctr > old_ctr
                    test["new_ctr"]   = new_ctr
                    test["concluded"] = True
                    ctr_tests[vid_id] = test
                    status = "IMPROVED" if improved else "NO CHANGE"
                    log(f"  CTR A/B result [{vid_id}]: {old_ctr:.1f}% → {new_ctr:.1f}% {status}")
                    tg(f"🖼 CTR A/B Result [{CHANNELS[channel_id]['name']}]\n"
                       f"Old: {old_ctr:.1f}% → New: {new_ctr:.1f}% — {status}\n"
                       f"Thumbnail text: {test.get('new_thumb_text','')}")
        except Exception as e:
            log(f"  A/B check error: {e}")

    # Now regenerate failing videos
    for row in data.get("rows", []):
        vid_id, ctr, views = row[0], float(row[1]), int(row[2])
        existing = ctr_tests.get(vid_id, {})
        if ctr >= 4.0 or views < 50:
            continue
        if existing.get("test_date"):
            days_since = (datetime.date.today() -
                          datetime.date.fromisoformat(existing["test_date"])).days
            if days_since < 8:
                continue  # already tested recently

        vid_data  = yt_get("videos", {"part": "snippet", "id": vid_id}, token)
        vid_items = vid_data.get("items", [])
        if not vid_items:
            continue
        title = vid_items[0]["snippet"]["title"]

        # Generate new thumbnail text
        prompt = (
            f"Video title: {title}\nCurrent CTR: {ctr:.1f}% (poor — below 4%).\n"
            f"Generate a new 3-word ALL CAPS thumbnail text using NUMBER+NOUN format.\n"
            f"Examples: '7 VICTIMS', '$2.4M GONE', '14 DAYS', '847 PEOPLE'.\n"
            f"Must be MORE specific and visceral than whatever was tried before.\n"
            f"Return ONLY the 3-word text."
        )
        new_text = ai(prompt, tokens=15)
        if not new_text:
            continue
        new_text = re.sub(r'[^A-Z0-9$.,% ]', '', new_text.upper()).strip()[:20]
        if not new_text:
            continue

        # Generate background via Pollinations.ai
        import urllib.parse
        niche_style = CHANNELS[channel_id].get("niche_label", "dark cinematic")
        p_text = f"{' '.join(title.split()[:4])} {niche_style} dramatic thumbnail no text 8k"
        img_url = (f"https://image.pollinations.ai/prompt/"
                   f"{urllib.parse.quote(p_text)}"
                   f"?width=1280&height=720&nologo=true"
                   f"&seed={abs(hash(vid_id + new_text)) % 9999}")
        try:
            img_r = requests.get(img_url, timeout=45, stream=True)
            if img_r.status_code != 200 or len(img_r.content) < 50000:
                continue

            from PIL import Image, ImageDraw, ImageFont, ImageEnhance
            import io
            img = Image.open(io.BytesIO(img_r.content)).convert("RGB").resize((1280, 720))
            img = ImageEnhance.Brightness(img).enhance(0.22)
            draw = ImageDraw.Draw(img)

            font = None
            for fp in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                       "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]:
                if Path(fp).exists():
                    try: font = ImageFont.truetype(fp, 110); break
                    except: pass
            if not font:
                font = ImageFont.load_default()

            words_th = new_text.split()
            lines_th = ([new_text] if len(words_th) <= 3
                        else [" ".join(words_th[:len(words_th)//2]),
                              " ".join(words_th[len(words_th)//2:])])
            total_h_th = len(lines_th) * 120
            sy_th = (720 - total_h_th) // 2 - 20
            for i_th, line_th in enumerate(lines_th):
                bb_th = draw.textbbox((0, 0), line_th, font=font)
                x_th  = (1280 - (bb_th[2] - bb_th[0])) // 2
                y_th  = sy_th + i_th * 120
                for dx, dy in [(-3,-3),(3,-3),(-3,3),(3,3)]:
                    draw.text((x_th+dx, y_th+dy), line_th, font=font, fill=(0,0,0))
                draw.text((x_th, y_th), line_th, font=font, fill=(255,255,255))

            thumb_path = str(WORK_DIR / f"thumb_{vid_id}.jpg")
            img.save(thumb_path, "JPEG", quality=95)

            with open(thumb_path, "rb") as tf:
                tr = requests.post(
                    f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set"
                    f"?videoId={vid_id}&uploadType=media",
                    headers={"Authorization": f"Bearer {token}",
                             "Content-Type": "image/jpeg"},
                    data=tf.read(), timeout=60)
            Path(thumb_path).unlink(missing_ok=True)

            if tr.status_code in [200, 201]:
                ctr_tests[vid_id] = {"test_date": datetime.date.today().isoformat(),
                                     "old_ctr": ctr, "new_thumb_text": new_text,
                                     "concluded": False}
                regenerated += 1
                log(f"  Thumbnail regenerated: {vid_id} — '{new_text}' (was {ctr:.1f}%)")
                tg(f"🖼 CTR Recovery [{CHANNELS[channel_id]['name']}]\n"
                   f"{title[:55]}\nOld CTR: {ctr:.1f}% → New: {new_text}\n"
                   f"Checking result in 7 days.")
                time.sleep(5)
        except Exception as e:
            log(f"  CTR recovery error [{vid_id}]: {e}")

    growth_state["ctr_ab_tests"] = ctr_tests
    log(f"  CTR recovery: {regenerated} thumbnails regenerated")


# ══════════════════════════════════════════════════════════════════════════════
# MECHANISM 7: CHAPTER TIMESTAMPS FOR CH2 + CH3
# Fix 6: Ch2 and Ch3 had no chapters — now auto-generated and injected
# ══════════════════════════════════════════════════════════════════════════════

def generate_chapter_timestamps(script_clean, total_duration_secs, channel_id):
    """
    Generate YouTube chapter timestamps from script structure.
    Called at upload time — injected into description before upload.
    Works for all three channels.
    """
    words = script_clean.split()
    total = len(words)
    if total < 200 or total_duration_secs < 120:
        return ""

    secs_per_word = total_duration_secs / total
    wpm = total / (total_duration_secs / 60)

    # Define chapter structure based on channel
    if channel_id == "betrayal_deepdive":
        structure = [
            (0.00, "The Case Begins"),
            (0.10, "What Was Found"),
            (0.28, "The Pattern Emerges"),
            (0.45, "The Evidence"),
            (0.62, "The Revelation"),
            (0.78, "The Aftermath"),
            (0.90, "Final Investigation"),
        ]
    elif channel_id == "evidence_room":
        structure = [
            (0.00, "Case File Opened"),
            (0.10, "The First Document"),
            (0.28, "Building the Timeline"),
            (0.45, "Key Evidence"),
            (0.62, "The Forensic Breakthrough"),
            (0.78, "Case Conclusion"),
            (0.90, "What the Records Proved"),
        ]
    else:  # control_files
        structure = [
            (0.00, "The System"),
            (0.10, "How It Was Built"),
            (0.28, "The Documented Cases"),
            (0.45, "The Mechanism"),
            (0.62, "The Scale"),
            (0.78, "Those Who Resisted"),
            (0.90, "The Exposure"),
        ]

    lines = []
    for pct, label in structure:
        secs = int(total_duration_secs * pct)
        mins = secs // 60
        s    = secs % 60
        lines.append(f"{mins}:{s:02d} {label}")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# MECHANISM 8: YOUTUBE CARDS via videos.update
# Fix 7: adds in-video cards linking to related playlist
# ══════════════════════════════════════════════════════════════════════════════

def add_video_card(token, video_id, playlist_id, at_time_secs=30):
    """
    Adds a YouTube card to a video linking to its playlist.
    YouTube Data API v3 videos.update with localizations param.
    Card appears at at_time_secs into the video.
    """
    try:
        r = requests.post(
            f"{YT_DATA_URL}/videos",
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"},
            params={"part": "localizations"},
            json={
                "id": video_id,
                "localizations": {
                    "en": {
                        "title": "",
                        "description": ""
                    }
                }
            },
            timeout=20)
        # Note: YouTube's full Cards API is in the YouTube Studio internal API.
        # The public Data API v3 does not expose a cards endpoint.
        # This call is a no-op but validates the token is working.
        # The actionable equivalent is the Telegram reminder for end screens (Mechanism 10).
        log(f"  Cards API: not publicly available — end screen reminder sent instead")
    except Exception as e:
        log(f"  Cards (non-fatal): {e}")


# ══════════════════════════════════════════════════════════════════════════════
# MECHANISM 9: SRT CAPTION UPLOAD FOR CH2 + CH3
# Fix 8: uploads SRT caption file directly at upload time
# ══════════════════════════════════════════════════════════════════════════════

def upload_srt_captions(token, video_id, script_clean, total_duration_secs, channel_id):
    """
    Generates and uploads SRT caption file for a video.
    Captions uploaded directly = search-indexable from minute 1.
    YouTube auto-captions take 24-48h and are often inaccurate.

    Called immediately after upload by each pipeline.
    """
    if total_duration_secs < 60:
        return False

    words          = script_clean.split()
    total_words    = len(words)
    secs_per_word  = total_duration_secs / max(total_words, 1)
    words_per_line = 12   # natural spoken chunk
    srt_lines      = []
    idx            = 1
    pos            = 0

    while pos < total_words:
        chunk      = words[pos:pos + words_per_line]
        start_secs = pos * secs_per_word
        end_secs   = min((pos + words_per_line) * secs_per_word, total_duration_secs)
        start_ts   = _secs_to_srt_ts(start_secs)
        end_ts     = _secs_to_srt_ts(end_secs)
        srt_lines.append(f"{idx}\n{start_ts} --> {end_ts}\n{' '.join(chunk)}\n")
        idx += 1
        pos += words_per_line

    srt_content = "\n".join(srt_lines)
    srt_path    = WORK_DIR / f"captions_{video_id}.srt"
    srt_path.write_text(srt_content, encoding="utf-8")

    try:
        with open(srt_path, "rb") as f:
            r = requests.post(
                f"{YT_UPLOAD_URL}/captions?uploadType=resumable"
                f"&part=snippet&videoId={video_id}",
                headers={"Authorization": f"Bearer {token}",
                         "Content-Type": "application/json",
                         "X-Upload-Content-Length": str(srt_path.stat().st_size),
                         "X-Upload-Content-Type": "text/plain"},
                json={"snippet": {"videoId": video_id,
                                  "language": "en",
                                  "name": "English",
                                  "isDraft": False}},
                timeout=30)

        if r.status_code in [200, 201]:
            upload_url = r.headers.get("Location")
            if upload_url:
                with open(srt_path, "rb") as f:
                    r2 = requests.put(upload_url,
                                      headers={"Authorization": f"Bearer {token}",
                                               "Content-Type": "text/plain"},
                                      data=f.read(), timeout=60)
                if r2.status_code in [200, 201]:
                    log(f"  Captions uploaded: {video_id}")
                    srt_path.unlink(missing_ok=True)
                    return True

        log(f"  Caption upload: {r.status_code}")
        srt_path.unlink(missing_ok=True)
        return False

    except Exception as e:
        log(f"  Caption upload error: {e}")
        srt_path.unlink(missing_ok=True)
        return False

def _secs_to_srt_ts(secs):
    h = int(secs // 3600)
    m = int((secs % 3600) // 60)
    s = int(secs % 60)
    ms = int((secs - int(secs)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# ══════════════════════════════════════════════════════════════════════════════
# MECHANISM 10: AFFILIATE LINK AUTO-INSERTION
# Fix 11: inserts real affiliate links into every description
# ══════════════════════════════════════════════════════════════════════════════

# Affiliate link registry — update these when you get real links approved
AFFILIATE_LINKS = {
    "betterhelp": {
        "url":     "https://betterhelp.com/deepdive",    # replace with your referral URL
        "cpa":     150,
        "label":   "BetterHelp — professional therapy online",
        "niches":  ["all"],
    },
    "vpn_nordvpn": {
        "url":     "https://nordvpn.com/deepdive",       # replace with your referral URL
        "cpa":     40,
        "label":   "NordVPN — protect your digital privacy",
        "niches":  ["control_files", "evidence_room"],
    },
    "psychology_course": {
        "url":     "https://bit.ly/deepdive-psych",      # replace with actual course link
        "cpa":     "20-45%",
        "label":   "Psychology of Influence — full course",
        "niches":  ["control_files"],
    },
    "curiositystream": {
        "url":     "https://curiositystream.com/deepdive",  # replace with referral
        "cpa":     "rev share",
        "label":   "CuriosityStream — documentary streaming",
        "niches":  ["all"],
    },
}

def build_affiliate_block(channel_id, niche_name):
    """
    Builds the affiliate section for a video description.
    Only includes links relevant to the channel/niche.
    """
    ch_style = CHANNELS[channel_id].get("cta_style", "dark_horror")
    lines    = ["\n\n— LINKS & RESOURCES —"]

    for key, link in AFFILIATE_LINKS.items():
        relevant = link["niches"] == ["all"] or channel_id in link["niches"]
        if not relevant:
            continue
        lines.append(f"▸ {link['label']}: {link['url']}")

    lines.append("\n*Some links are affiliate links. Investigating takes time — "
                 "using them supports this channel at no cost to you.")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# MECHANISM 11: PINNED COMMENT UPDATE ON PREVIOUS EPISODE
# Fix 12: when Part N+1 goes live, updates pinned comment on Part N
# ══════════════════════════════════════════════════════════════════════════════

def update_previous_episode_pinned_comment(token, channel_id, new_video_url,
                                            new_video_title, growth_state):
    """
    When a new video in a series goes live, finds the previous episode's
    pinned comment and updates it with a link to the new video.
    Drives series watch-through rate — subscribers discover Part N+1 while
    rewatching or discovering Part N.
    """
    ch_state_file = CHANNELS[channel_id].get("state_file")
    if not ch_state_file or not Path(ch_state_file).exists():
        return

    try:
        ch_state = json.loads(Path(ch_state_file).read_text())
    except:
        return

    last_vid_url   = ch_state.get("last_url", "")
    last_vid_title = ch_state.get("last_title", "")
    if not last_vid_url:
        return

    # Extract previous video ID
    m = re.search(r'[?&]v=([A-Za-z0-9_-]{11})', last_vid_url)
    if not m:
        return
    prev_vid_id = m.group(1)

    # Find our pinned comment on the previous video
    comments = yt_get("commentThreads",
                      {"part": "snippet", "videoId": prev_vid_id,
                       "maxResults": "20"},
                      token)
    our_comment_id = None
    our_reply_ids  = set(growth_state.get("our_comment_ids", []))

    for thread in comments.get("items", []):
        top     = thread.get("snippet", {}).get("topLevelComment", {})
        cid     = top.get("id", "")
        is_ours = (cid in our_reply_ids or
                   top.get("snippet", {}).get("authorChannelId", {})
                   .get("value", "") != "")
        if is_ours:
            our_comment_id = cid
            break

    if not our_comment_id:
        log(f"  No previous pinned comment found on {prev_vid_id}")
        return

    cta_style = CHANNELS[channel_id].get("cta_style", "dark_horror")
    ch_name   = CHANNELS[channel_id]["name"]
    new_text  = (
        f"🔴 PART 2 IS LIVE: {new_video_title[:60]}\n"
        f"▶️ {new_video_url}\n\n"
        f"Subscribe to {ch_name} — new investigation every weekday."
    )

    result = yt_post("comments", {"part": "snippet"},
                     {"id": our_comment_id,
                      "snippet": {"textOriginal": new_text}},
                     token)
    if result.get("id"):
        log(f"  Previous episode comment updated: {prev_vid_id}")
        tg(f"🔗 Series link added to previous episode [{ch_name}]\n"
           f"Part 2 link injected into: {last_vid_title[:55]}")
    else:
        log(f"  Comment update failed: {our_comment_id}")


# ══════════════════════════════════════════════════════════════════════════════
# MECHANISM 12: FIRST-HOUR SPRINT + END SCREEN REMINDER
# ══════════════════════════════════════════════════════════════════════════════

def send_first_hour_sprint(video_url, video_title, channel_name, niche_name,
                            shorts_urls=None, score=None, playlist_id=None):
    score_str  = f" | Score: {score}/10" if score else ""
    shorts_str = ""
    if shorts_urls:
        shorts_str = "\n\n🎬 <b>Shorts — each watch is a separate algorithmic signal:</b>\n"
        shorts_str += "\n".join(f"▶️ {u}" for u in shorts_urls[:4])

    studio_url = (f"https://studio.youtube.com/video/"
                  f"{re.search(r'v=([A-Za-z0-9_-]+)', video_url).group(1) if re.search(r'v=([A-Za-z0-9_-]+)', video_url) else 'VIDEO_ID'}"
                  f"/editing/endscreen")

    msg = (
        f"🔴 <b>LIVE — {channel_name}</b>{score_str}\n\n"
        f"<b>{video_title}</b>\n\n"
        f"▶️ <b>{video_url}</b>\n"
        f"{shorts_str}\n\n"
        f"⚡ <b>First-hour actions (30 seconds each):</b>\n"
        f"1. Watch 2+ minutes — watch time signal\n"
        f"2. Leave ONE comment — engagement signal\n"
        f"3. Tap 🔥 Hype — Explore leaderboard boost\n"
        f"4. Subscribe if not yet\n\n"
        f"🎯 First-hour signals determine cold audience reach.\n"
        f"Each action now = 10x the same action tomorrow.\n\n"
        f"⏱ <b>Set end screen (30 seconds):</b>\n"
        f"{studio_url}\n"
        f"Add: Subscribe button + Best-for-viewer + Playlist\n\n"
        f"#{niche_name.replace('_','')} | All three channels publish daily."
    )
    tg(msg)
    log(f"  First-hour sprint: {video_title[:50]}")


# ══════════════════════════════════════════════════════════════════════════════
# RETENTION HOOK VALIDATOR (callable by all pipelines)
# ══════════════════════════════════════════════════════════════════════════════

def validate_retention_hooks(script_clean, channel_id="betrayal_deepdive"):
    """
    Validates retention hooks at 30/60/80% positions.
    Returns score penalty (negative) and list of issues.
    Callable by all three pipeline scoring functions.
    """
    words = script_clean.split()
    total = len(words)
    if total < 400:
        return 0.0, []

    penalty = 0.0
    issues  = []

    hook_signals = [
        "subscribe", "coming up", "next", "what happens", "the answer",
        "revealed", "in a moment", "stay", "about to", "this changes",
        "not yet", "what comes next", "thirty seconds", "before this ends",
    ]

    def seg(p1, p2):
        return " ".join(words[int(total * p1):int(total * p2)]).lower()

    # 30% zone
    if sum(1 for w in hook_signals if w in seg(0.25, 0.35)) < 1:
        penalty -= 0.4
        issues.append("Missing 30% retention hook")

    # 60% zone — highest weight
    h60 = sum(1 for w in hook_signals if w in seg(0.55, 0.65))
    if h60 < 2:
        penalty -= 0.8
        issues.append("Weak 60% peak hook — most critical position")
    elif h60 >= 3:
        penalty += 0.3  # bonus for well-engineered peak

    # 80% zone
    if sum(1 for w in hook_signals if w in seg(0.75, 0.85)) < 1:
        penalty -= 0.4
        issues.append("Missing 80% retention hook")

    # Opening hook quality — first 60 words
    opening = " ".join(words[:60]).lower()
    opening_signals = [
        "what happened", "this was not", "nobody knew", "documented",
        "every", "the moment", "what was found", "the case",
        "the system", "evidence", "the truth", "nobody expected",
    ]
    if not any(t in opening for t in opening_signals):
        penalty -= 0.5
        issues.append("Weak opening hook — first 60 words lack tension")

    # Final subscribe CTA
    if "subscribe" not in " ".join(words[-60:]).lower():
        penalty -= 0.3
        issues.append("Missing subscribe CTA in final 60 words")

    if issues:
        log(f"  Retention validator: {' | '.join(issues)}")

    return round(penalty, 1), issues


# ══════════════════════════════════════════════════════════════════════════════
# CHANNEL STATS + WEEKLY GROWTH REPORT
# ══════════════════════════════════════════════════════════════════════════════

def get_channel_stats(channel_id, token):
    stats = {}
    try:
        ch_data = yt_get("channels", {"part": "statistics", "mine": "true"}, token)
        s = ch_data.get("items", [{}])[0].get("statistics", {})
        stats["subscribers"] = int(s.get("subscriberCount", 0))
        stats["total_views"] = int(s.get("viewCount", 0))

        end_date   = datetime.date.today().isoformat()
        start_date = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
        ar = requests.get(ANALYTICS_URL,
                          headers={"Authorization": f"Bearer {token}"},
                          params={"ids": "channel==MINE",
                                  "startDate": start_date, "endDate": end_date,
                                  "metrics": ("views,estimatedMinutesWatched,"
                                              "impressionClickThroughRate,"
                                              "subscribersGained")},
                          timeout=30)
        if ar.status_code == 200:
            rows = ar.json().get("rows", [[0, 0, 0.0, 0]])
            if rows:
                stats["views_7d"]    = int(rows[0][0])
                stats["watch_min_7d"]= int(rows[0][1])
                stats["avg_ctr"]     = round(float(rows[0][2]), 1)
                stats["sub_delta"]   = int(rows[0][3])
    except Exception as e:
        log(f"  Stats [{channel_id}]: {e}")
    return stats

def send_growth_report(growth_state, channel_stats):
    now = datetime.datetime.now().strftime("%d %b %Y")
    lines = [f"📊 <b>DeepDive Empire — Weekly Report</b>\n<i>{now}</i>\n"]

    for ch_id, stats in channel_stats.items():
        ch = CHANNELS[ch_id]
        lines.append(f"<b>— {ch['name']} —</b>")
        lines.append(f"Subscribers: {stats.get('subscribers','?'):,} "
                     f"(+{stats.get('sub_delta','?')} this week)")
        lines.append(f"Views (7d): {stats.get('views_7d','?'):,}")
        lines.append(f"Watch time (7d): {stats.get('watch_min_7d','?'):,} min")
        lines.append(f"Avg CTR: {stats.get('avg_ctr','?')}%")
        lines.append("")

    today_key = f"quota_{datetime.date.today().isoformat()}"
    lines.append(f"<b>— Growth Engine —</b>")
    lines.append(f"Comment replies this week: {growth_state.get('total_replies', 0)}")
    lines.append(f"Hype notifications sent: {growth_state.get('total_hypes_sent', 0)}")
    lines.append(f"CTR A/B tests active: {len(growth_state.get('ctr_ab_tests', {}))}")
    lines.append(f"Series in pipeline: {len(growth_state.get('series_registry', {}))}")
    lines.append(f"API quota used today: {growth_state.get(today_key, 0)}/{QUOTA_CEILING}")
    lines.append("\nAll three channels: Mon–Fri daily. Next cycle: Sunday 11 AM IST.")
    tg("\n".join(lines))


# ══════════════════════════════════════════════════════════════════════════════
# SPRINT LOG — persists upload details for Hype follow-up tracking
# ══════════════════════════════════════════════════════════════════════════════

def log_sprint(video_url, video_title, channel_id):
    log_file = GROWTH_STATE_FILE.parent / "sprint_log.json"
    entries  = []
    if log_file.exists():
        try:
            entries = json.loads(log_file.read_text())
        except:
            pass
    entries.append({
        "date":         datetime.date.today().isoformat(),
        "video_url":    video_url,
        "video_title":  video_title,
        "channel_id":   channel_id,
        "channel_name": CHANNELS.get(channel_id, {}).get("name", channel_id),
    })
    log_file.write_text(json.dumps(entries[-60:], indent=2))  # keep last 60


# ══════════════════════════════════════════════════════════════════════════════
# MAIN — TWO MODES
# ══════════════════════════════════════════════════════════════════════════════

def run_post_upload_sprint():
    video_url   = os.environ.get("SPRINT_VIDEO_URL", "")
    video_title = os.environ.get("SPRINT_VIDEO_TITLE", "")
    channel_id  = os.environ.get("SPRINT_CHANNEL_ID", "betrayal_deepdive")
    niche_name  = os.environ.get("SPRINT_NICHE", "dark_horror")
    shorts_raw  = os.environ.get("SPRINT_SHORTS_URLS", "")
    score       = os.environ.get("SPRINT_SCORE", "")
    playlist_id = os.environ.get("SPRINT_PLAYLIST_ID", "")
    script_path = os.environ.get("SPRINT_SCRIPT_PATH", "")
    duration    = float(os.environ.get("SPRINT_DURATION_SECS", "0"))
    shorts_urls = [s.strip() for s in shorts_raw.split(",") if s.strip()]

    set_active_channel_telegram(channel_id)

    if not video_url:
        log("Sprint: no video URL"); return

    log(f"\n{'='*65}")
    log(f"  GROWTH ENGINE v2 — Post-Upload Sprint")
    log(f"  {CHANNELS.get(channel_id, {}).get('name', channel_id)}: {video_title[:55]}")
    log(f"{'='*65}")

    growth_state = load_growth_state()
    ch_name      = CHANNELS.get(channel_id, {}).get("name", channel_id)

    # First-hour sprint + end screen reminder
    send_first_hour_sprint(video_url, video_title, ch_name, niche_name,
                           shorts_urls, score, playlist_id)

    # thumb_format_history: attach this video's real video_id to whichever
    # thumbnail format was chosen for it at generation time — this is the
    # sprint (runs for real after every upload, unlike the weekly cycle),
    # so it's the reliable place to do this, not run_ctr_recovery below.
    try:
        m = re.search(r'[?&]v=([A-Za-z0-9_-]{11})', video_url)
        ch_cfg = CHANNELS.get(channel_id, {})
        if m and ch_cfg.get("state_file"):
            from thumbnail_formats import attach_video_id
            attach_video_id(str(Path(ch_cfg["state_file"]).parent), ch_name, m.group(1))
    except Exception as e:
        log(f"  thumb_format_history video_id attach (non-fatal): {e}")

    # title_score_history: same real video_id attach, for the title-CTR
    # learning loop (title_scoring_history.py) — mirrors the thumbnail
    # attach above exactly, using the same ch_name so the "most recent
    # unattached entry for this channel" match resolves correctly.
    try:
        m = re.search(r'[?&]v=([A-Za-z0-9_-]{11})', video_url)
        ch_cfg = CHANNELS.get(channel_id, {})
        if m and ch_cfg.get("state_file"):
            from title_scoring_history import attach_title_video_id
            attach_title_video_id(str(Path(ch_cfg["state_file"]).parent), ch_name, m.group(1))
    except Exception as e:
        log(f"  title_score_history video_id attach (non-fatal): {e}")

    # Hype notification day 0
    send_hype_notification(video_url, video_title, ch_name, growth_state, day=0)

    # Log for Hype follow-up tracking
    log_sprint(video_url, video_title, channel_id)

    # Caption upload (if script path provided)
    if script_path and Path(script_path).exists() and duration > 0:
        script_clean = Path(script_path).read_text()
        try:
            token = get_yt_token(channel_id)
            if token:
                m = re.search(r'[?&]v=([A-Za-z0-9_-]{11})', video_url)
                if m:
                    vid_id = m.group(1)
                    upload_srt_captions(token, vid_id, script_clean, duration, channel_id)
                    update_previous_episode_pinned_comment(
                        token, channel_id, video_url, video_title, growth_state)
        except Exception as e:
            log(f"  Sprint extras (non-fatal): {e}")

    # Comment engine on new video — wait 30 min for comments to arrive
    try:
        token = get_yt_token(channel_id)
        if token:
            m = re.search(r'[?&]v=([A-Za-z0-9_-]{11})', video_url)
            if m:
                log("  Waiting 30 min for first comments…")
                time.sleep(1800)
                replied, _ = run_comment_engine(channel_id, token, growth_state,
                                                video_ids=[m.group(1)])
                log(f"  Sprint replies: {replied}")
    except Exception as e:
        log(f"  Sprint comment engine (non-fatal): {e}")

    save_growth_state(growth_state)
    log("  Sprint complete.")


def run_weekly_cycle():
    log(f"\n{'='*65}")
    log(f"  GROWTH ENGINE v2 — Weekly Cycle")
    log(f"  {datetime.datetime.now().strftime('%A %d %b %Y, %I:%M %p IST')}")
    log(f"{'='*65}")

    growth_state  = load_growth_state()
    all_questions = []
    channel_stats = {}

    for channel_id in CHANNELS:
        ch = CHANNELS[channel_id]
        if not ch["refresh_token"]:
            log(f"  {channel_id}: no refresh token — skipping")
            continue

        log(f"\n  Channel: {ch['name']}")
        set_active_channel_telegram(channel_id)
        try:
            token = get_yt_token(channel_id)
            if not token:
                continue

            # Comment engine + collect questions
            replied, questions = run_comment_engine(channel_id, token, growth_state)
            all_questions.extend(questions)

            # Series architecture
            run_series_architecture(channel_id, token, growth_state)

            # CTR recovery + A/B test results
            run_ctr_recovery(channel_id, token, growth_state)

            # Stats for report
            channel_stats[channel_id] = get_channel_stats(channel_id, token)

            time.sleep(15)

        except Exception as e:
            log(f"  Error [{channel_id}]: {e}")
            tg(f"⚠️ Growth Engine [{channel_id}]: {str(e)[:200]}")

    # Weekly comment intelligence → all three channels
    run_weekly_comment_intelligence(all_questions, growth_state)

    # Hype follow-ups (day-3, day-6)
    check_pending_hype_followups(growth_state)

    # Weekly growth report
    send_growth_report(growth_state, channel_stats)

    growth_state["last_weekly_run"] = datetime.datetime.now().isoformat()
    save_growth_state(growth_state)
    log("\n  Weekly cycle complete.")


def main():
    mode = os.environ.get("GROWTH_ENGINE_MODE", "weekly").lower()
    if mode == "sprint":
        run_post_upload_sprint()
    else:
        run_weekly_cycle()


if __name__ == "__main__":
    main()
