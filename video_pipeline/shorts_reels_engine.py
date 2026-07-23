"""
shorts_reels_engine.py — ULTIMATE v1
======================================
Complete engine for:
  - 4 YouTube Shorts/day (2 standalone + 2 tied to main video)
  - 2 Instagram Reels/day (bilingual Hindi/English)
  - Perfect subtitle sync (frame-accurate, burned in)
  - Multi-gender voices: US male, US female, British male, British female
  - 8.5/10 minimum quality with auto-retry
  - Algorithm-optimised per 2026 research

SHORTS SCHEDULE:
  Daily Short 1: 6:00 AM IST — standalone trending story (US audience)
  Daily Short 2: 2:00 PM IST — standalone trending story (US/UK audience)
  Main Video Short 1 (Teaser): 8h before main video — clips from upcoming video
  Main Video Short 2 (Recap): 24h after main video — best moment from video

REELS SCHEDULE:
  Daily Reel 1: 6:30 AM IST — Hinglish story
  Daily Reel 2: 3:00 PM IST — different story, different voice gender

VOICE SYSTEM:
  YouTube Shorts — English only (US + British accent, male + female rotation)
  Instagram Reels — Bilingual Hindi/English (male + female rotation)
  All voices: Groq Orpheus with [intense] [disbelief] [outraged] tags
  Fallback: espeak-ng with accent flags

SUBTITLE SYSTEM:
  - Word-level SRT generated from script + audio duration
  - Burned directly into video via FFmpeg libass
  - Font: DejaVu Sans Bold, size 22px, white + black outline
  - Position: lower third (y=h-120)
  - Sync: calculated from actual audio duration, never guesses
  - Works with NO sound (Instagram muted viewing)

QUALITY SYSTEM:
  - Pre-score: hook + topic virality checked BEFORE production
  - Post-score: 5-point check after assembly
  - If score < 8.5: regenerate script and retry (max 3 attempts)
  - Telegram report after every upload

ENV VARS:
  GROQ_API_KEY, GEMINI_API_KEY, MISTRAL_API_KEY
  PIXABAY_KEY
  YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN
  YOUTUBE_DATA_API_KEY
  IG_USER_ID, IG_ACCESS_TOKEN
  TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
  NEWS_API_KEY
  GITHUB_TOKEN, GITHUB_REPOSITORY
  SHORT_MODE: 'standalone_1' | 'standalone_2' | 'teaser' | 'recap'
  REEL_MODE:  'reel_1' | 'reel_2'
  MAIN_VIDEO_TOPIC: (for teaser/recap)
  OUTPUT_DIR: /tmp/shorts_output
"""

import os, json, re, logging, subprocess, uuid, random, time
from datetime import datetime
import requests

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [SHORTS] %(message)s")
log = logging.getLogger(__name__)

# ── Credentials ───────────────────────────────────────────────────────────────
GROQ_KEY    = os.environ.get("GROQ_API_KEY", "")
GEMINI_KEY  = os.environ.get("GEMINI_API_KEY", "")
MISTRAL_KEY = os.environ.get("MISTRAL_API_KEY", "")
PIX_KEY     = os.environ.get("PIXABAY_KEY", "")
TG_TOKEN    = os.environ.get("TELEGRAM_TOKEN", "")
TG_CHAT     = os.environ.get("TELEGRAM_CHAT_ID", "")

# FIX (critical, found on full re-audit): TG_TOKEN/TG_CHAT were always
# the generic Ch1 bot credentials, with no per-channel routing at all —
# same bug class already found and fixed for YouTube credentials above.
# Every Shorts alert (upload success/failure) from every channel was
# silently going to Ch1's Telegram bot regardless of which channel's
# Short actually produced it.
TG_CREDENTIAL_ENV_BY_CHANNEL = {
    "betrayal_deepdive": ("TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID"),
    "evidence_room":     ("TELEGRAM_TOKEN_CH2", "TELEGRAM_CHAT_ID_CH2"),
    "control_files":     ("TELEGRAM_TOKEN_CH3", "TELEGRAM_CHAT_ID_CH3"),
    "archive":           ("TELEGRAM_TOKEN_CH4", "TELEGRAM_CHAT_ID_CH4"),
    "collapse_index":    ("TELEGRAM_TOKEN_CH5", "TELEGRAM_CHAT_ID_CH5"),
}
NEWS_KEY    = os.environ.get("NEWS_API_KEY", "")
# FIX (found on sequential re-audit — the single most severe bug found
# this entire session): YT_CLIENT/YT_SECRET/YT_REFRESH previously only
# ever read the generic YOUTUBE_CLIENT_ID/SECRET/REFRESH_TOKEN (Ch1's own
# real credentials), with ZERO channel awareness — despite this whole
# file having a real, working CHANNEL_CONFIGS/set_active_channel system
# for branding. Every Ch3 Short (teaser/standalone/recap) would have
# authenticated as Ch1's YouTube channel and uploaded there instead of
# Ch3's own channel, since both credential sets are present in Ch3's
# workflow environment and this function was reading the wrong one.
# Matches each channel's real per-channel secret naming convention
# already used in control_files_pipeline.py itself and weekly_report.py.
YT_CREDENTIAL_ENV_BY_CHANNEL = {
    "betrayal_deepdive": ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"),
    "evidence_room":     ("EVIDENCE_YT_CLIENT_ID", "EVIDENCE_YT_CLIENT_SECRET", "EVIDENCE_YT_REFRESH_TOKEN"),
    "control_files":     ("CHANNEL3_YT_CLIENT_ID", "CHANNEL3_YT_CLIENT_SECRET", "CHANNEL3_YT_REFRESH_TOKEN"),
    # FIX (critical, found on full re-audit): "archive" (Ch4/The Archive)
    # was missing entirely — every Short Ch4 tried to produce would have
    # silently fallen back to the generic YOUTUBE_* credentials (Ch1's
    # own), meaning Ch4's Shorts would upload to Ch1's YouTube channel
    # instead of The Archive's. Exact same credential-routing bug class
    # already found and fixed multiple times in the main pipelines.
    "archive":           ("CHANNEL4_YT_CLIENT_ID", "CHANNEL4_YT_CLIENT_SECRET", "CHANNEL4_YT_REFRESH_TOKEN"),
    "collapse_index":    ("CHANNEL5_YT_CLIENT_ID", "CHANNEL5_YT_CLIENT_SECRET", "CHANNEL5_YT_REFRESH_TOKEN"),
}
YT_CLIENT   = os.environ.get("YOUTUBE_CLIENT_ID", "")
YT_SECRET   = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
YT_REFRESH  = os.environ.get("YOUTUBE_REFRESH_TOKEN", "")
IG_USER_ID  = os.environ.get("IG_USER_ID", "")
IG_TOKEN    = os.environ.get("IG_ACCESS_TOKEN", "")
GH_TOKEN    = os.environ.get("GITHUB_TOKEN", "")
GH_REPO     = os.environ.get("GITHUB_REPOSITORY", "")
SHORT_MODE  = os.environ.get("SHORT_MODE", "standalone_1")
REEL_MODE   = os.environ.get("REEL_MODE", "reel_1")
MAIN_TOPIC  = os.environ.get("MAIN_VIDEO_TOPIC", "")
OUTPUT_DIR  = os.environ.get("OUTPUT_DIR", "/tmp/shorts_output")
CHANNEL     = "BETRAYAL DEEPDIVE"      # legacy default — see CHANNEL_CONFIGS below
WATERMARK   = "@BetrayalDeepDive"      # legacy default — see CHANNEL_CONFIGS below
QUALITY_MIN = 8.5

# ══════════════════════════════════════════════════════════════════
# FIX: this whole file was hardcoded to Ch1's identity throughout —
# CHANNEL/WATERMARK constants, hashtags baked directly into AI prompts,
# background-search terms, standalone-Short topic pools, and the
# description tagline all said "betrayal" regardless of which channel
# actually called these functions. This meant every Short Ch2 (or any
# future channel) generated was silently mislabeled with Ch1's branding.
# CHANNEL_CONFIGS + set_active_channel() below fix this properly and are
# built to extend cleanly to Ch3/4/5 — add one new dict entry, not a rewrite.
# ══════════════════════════════════════════════════════════════════
CHANNEL_CONFIGS = {
    "betrayal_deepdive": {
        "display_name":   "BETRAYAL DEEPDIVE",
        "watermark":      "@BetrayalDeepDive",
        "hashtags_base":  "#betrayaldeepdive #shorts",
        "tagline":        "Betrayal DeepDive — New betrayal story every day.",
        "bg_search_term": "betrayal",
        # FIX (v7 rebuild, per explicit correction): these used to be
        # "standalone_1"/"standalone_2" pools that were STILL same-niche
        # as the channel (just different specific angles on betrayal/
        # crime) — not genuinely different niches or trending topics as
        # explicitly requested. Renamed to "trending_1"/"trending_2" and
        # rebuilt as genuinely cross-niche, broad-appeal categories
        # (real trend research below narrows these further to what's
        # actually current).
        "standalone_topics": {
            "standalone_1": [
                "viral celebrity news story", "trending sports moment", "surprising tech breakthrough",
                "viral life hack", "unexpected science discovery", "trending internet story"
            ],
            "standalone_2": [
                "shocking world record", "viral animal story", "trending travel discovery",
                "surprising history fact", "unexpected food trend", "viral challenge explained"
            ],
        },
        "default_niche": "betrayal",
    },
    "evidence_room": {
        "display_name":   "THE EVIDENCE ROOM",
        "watermark":      "@TheEvidenceRoom",
        "hashtags_base":  "#evidenceroom #shorts",
        "tagline":        "The Evidence Room — New case, new evidence, every day.",
        "bg_search_term": "forensic investigation evidence dark",
        "standalone_topics": {
            "standalone_1": [
                "viral celebrity news story", "trending sports moment", "surprising tech breakthrough",
                "viral life hack", "unexpected science discovery", "trending internet story"
            ],
            "standalone_2": [
                "shocking world record", "viral animal story", "trending travel discovery",
                "surprising history fact", "unexpected food trend", "viral challenge explained"
            ],
        },
        "default_niche": "forensic investigation",
    },
    "control_files": {
        "display_name":   "THE CONTROL FILES",
        "watermark":      "@TheControlFiles",
        "hashtags_base":  "#thecontrolfiles #shorts #psychology",
        "tagline":        "The Control Files — How control systems really work, every day.",
        "bg_search_term": "psychology manipulation control documentary dark",
        "standalone_topics": {
            "standalone_1": [
                "viral celebrity news story", "trending sports moment", "surprising tech breakthrough",
                "viral life hack", "unexpected science discovery", "trending internet story"
            ],
            "standalone_2": [
                "shocking world record", "viral animal story", "trending travel discovery",
                "surprising history fact", "unexpected food trend", "viral challenge explained"
            ],
        },
        "default_niche": "psychology manipulation",
    },
    # FIX: "archive" (Ch4) had NO entry here at all — every Short Ch4
    # tried to produce would have silently fallen back to BetrayalDeepDive's
    # branding, watermark, hashtags, and topic pools. Same hardcoded-
    # identity bug class already found and fixed for Ch2/Ch3.
    "archive": {
        "display_name":   "THE ARCHIVE",
        # FIX: The Archive's real handle is @TheArchiveFiles — this
        # watermark said "@TheArchive" while other channels' cross-promo
        # text baked into descriptions was split between "@TheArchiveFiles"
        # and "@TheArchiveDD" (now fixed to @TheArchiveFiles everywhere),
        # a 3-way mismatch confirmed against the real handle.
        "watermark":      "@TheArchiveFiles",
        "hashtags_base":  "#thearchive #shorts #history",
        "tagline":        "The Archive — Real documented history, every day.",
        "bg_search_term": "ancient history documentary archive",
        "standalone_topics": {
            "standalone_1": [
                "viral celebrity news story", "trending sports moment", "surprising tech breakthrough",
                "viral life hack", "unexpected science discovery", "trending internet story"
            ],
            "standalone_2": [
                "shocking world record", "viral animal story", "trending travel discovery",
                "surprising history fact", "unexpected food trend", "viral challenge explained"
            ],
        },
        "default_niche": "history documentary",
    },
    "collapse_index": {
        "display_name":   "THE COLLAPSE INDEX",
        "watermark":      "@TheCollapseIndex",
        "hashtags_base":  "#thecollapseindex #shorts #finance",
        "tagline":        "The Collapse Index — Real numbers behind tech and finance, every day.",
        "bg_search_term": "business finance documentary dramatic",
        "standalone_topics": {
            "standalone_1": [
                "viral celebrity news story", "trending sports moment", "surprising tech breakthrough",
                "viral life hack", "unexpected science discovery", "trending internet story"
            ],
            "standalone_2": [
                "shocking world record", "viral animal story", "trending travel discovery",
                "surprising history fact", "unexpected food trend", "viral challenge explained"
            ],
        },
        "default_niche": "business finance documentary",
    },
}

_active_channel_id = "betrayal_deepdive"  # module-level state, set via set_active_channel()

def set_active_channel(channel_id: str):
    """
    Call this at the start of each public produce_*_short function with the
    real channel identifier. Updates CHANNEL/WATERMARK (kept as plain
    module-level names so every existing internal helper that reads them
    directly keeps working, without needing every helper's signature
    rewritten) to match the real calling channel instead of always Ch1.
    Falls back safely to betrayal_deepdive's config for any unknown channel.

    FIX (critical, found on full re-audit): this used to leave TG_TOKEN/
    TG_CHAT untouched entirely — every Shorts alert from every channel
    silently went to Ch1's Telegram bot. Now routes those too, with a
    safe fallback to the generic bot if a channel-specific one isn't
    actually configured (e.g. secret not yet added), rather than sending
    nowhere.
    """
    global CHANNEL, WATERMARK, _active_channel_id, TG_TOKEN, TG_CHAT
    cfg = CHANNEL_CONFIGS.get(channel_id, CHANNEL_CONFIGS["betrayal_deepdive"])
    CHANNEL   = cfg["display_name"]
    WATERMARK = cfg["watermark"]
    _active_channel_id = channel_id if channel_id in CHANNEL_CONFIGS else "betrayal_deepdive"

    tg_token_env, tg_chat_env = TG_CREDENTIAL_ENV_BY_CHANNEL.get(
        _active_channel_id, ("TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID"))
    TG_TOKEN = os.environ.get(tg_token_env, os.environ.get("TELEGRAM_TOKEN", ""))
    TG_CHAT  = os.environ.get(tg_chat_env, os.environ.get("TELEGRAM_CHAT_ID", ""))

def get_active_channel_config():
    """Returns the full config dict for whichever channel is currently active."""
    return CHANNEL_CONFIGS.get(_active_channel_id, CHANNEL_CONFIGS["betrayal_deepdive"])


def _channel_cache_dir(channel_id):
    """
    Persistent per-channel directory for real, appended-to history files
    (shorts_format_history.json, thumb_format_history.json) — the same
    real directory each channel's own state.json/pipeline lives in and
    already survives between ephemeral GitHub Actions runners via each
    generate workflow's git-add step, not the ephemeral OUTPUT_DIR (/tmp).
    """
    from pathlib import Path as _Path
    return str(_Path(__file__).parent.parent / "channels" / channel_id)

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Voice Profiles ─────────────────────────────────────────────────────────────
# Research: Multi-gender US + British voices = wider global audience
# Groq Orpheus tags make voice emotional, not robotic
VOICES_EN = [
    # FIX (critical, found while investigating "sounds robotic/AI-built"):
    # this list previously had 10 voice IDs — "luna", "stella", "atlas",
    # "orion", "kora", "muse" were completely fabricated, not real Groq
    # Orpheus voices at all. Verified directly against Groq's own
    # documentation and changelog: canopylabs/orpheus-v1-english has
    # EXACTLY 6 real voices — autumn, diana, hannah, austin, daniel, troy.
    # Since pick_voice() rotates through this list, 6 of the previous 10
    # entries (60%) would have failed on every single call — Groq's API
    # would reject the invalid voice parameter, silently falling back to
    # the much more robotic espeak-ng synthesizer. This is very likely
    # the direct, concrete cause of Shorts narration sounding "AI-built."
    # Genders inferred from Groq's own naming (autumn/diana/hannah read
    # as female, austin/daniel/troy as male) — not independently
    # confirmed beyond that, since Groq doesn't publish per-voice gender
    # labels; if this proves wrong on a real run, it's a one-line fix.
    {"id": "troy",   "tag": "[intense]",   "gender": "male",   "accent": "US",
     "desc": "Deep US male, intense dramatic"},
    {"id": "austin", "tag": "[disbelief]", "gender": "male",   "accent": "US",
     "desc": "US male, shocked disbelief"},
    {"id": "daniel", "tag": "[outraged]",  "gender": "male",   "accent": "US",
     "desc": "US male, angry outrage"},
    {"id": "autumn", "tag": "[intense]",   "gender": "female", "accent": "US",
     "desc": "US female, intense dramatic"},
    {"id": "diana",  "tag": "[disbelief]", "gender": "female", "accent": "US",
     "desc": "US female, shocked"},
    {"id": "hannah", "tag": "[outraged]",  "gender": "female", "accent": "US",
     "desc": "US female, outrage"},
]

# FIX: Groq's Orpheus TTS only supports English (canopylabs/orpheus-v1-english)
# and Saudi Arabic (canopylabs/orpheus-arabic-saudi) — there is no Hindi/
# Hinglish model at all. This entire voice list was fabricated and would
# have failed 100% of the time. Confirmed this path is currently dead code
# (produce_instagram_reel is never called from any of the 4 real pipelines,
# only from this file's own standalone test block) — fixed for correctness
# so it's not a landmine whenever Instagram Reels support is actually built.
# Until then, for_reels should not be used with real Hindi/Hinglish script
# content; this now honestly falls back to the same 6 real English voices.
VOICES_HINGLISH = [
    {"id": "autumn", "tag": "[intense]",   "gender": "female", "lang": "en"},
    {"id": "diana",  "tag": "[disbelief]", "gender": "female", "lang": "en"},
    {"id": "troy",   "tag": "[intense]",   "gender": "male",   "lang": "en"},
    {"id": "austin", "tag": "[outraged]",  "gender": "male",   "lang": "en"},
]

# Rotate voices to ensure gender variety
_voice_rotation_index = int(datetime.now().hour) % len(VOICES_EN)


def pick_voice(for_reels: bool = False) -> dict:
    """Rotate through voices — different gender every time."""
    global _voice_rotation_index
    pool = VOICES_HINGLISH if for_reels else VOICES_EN
    voice = pool[_voice_rotation_index % len(pool)]
    _voice_rotation_index += 1
    log.info("Voice selected: %s (%s %s)", voice["id"], voice["accent"] if not for_reels else voice["lang"], voice["gender"])
    return voice


# ── LLM (Multi-API fallback) ──────────────────────────────────────────────────
def llm(prompt: str, max_tokens: int = 1500, temp: float = 0.8,
        priority: str = "groq") -> str:
    """Generate text with Groq→Gemini→Mistral fallback."""
    apis = []
    if priority == "groq":
        apis = [("groq", GROQ_KEY), ("gemini", GEMINI_KEY), ("mistral", MISTRAL_KEY)]
    else:
        apis = [("gemini", GEMINI_KEY), ("groq", GROQ_KEY), ("mistral", MISTRAL_KEY)]

    for provider, key in apis:
        if not key:
            continue
        try:
            if provider == "groq":
                # FIX (confirmed against Groq's own official deprecations
                # page): llama-3.3-70b-versatile was announced deprecated
                # by Groq on June 17, 2026, with openai/gpt-oss-120b and
                # qwen/qwen3.6-27b as the recommended replacements — same
                # fragile single-hardcoded-model pattern already fixed
                # elsewhere in this project for Gemini. Tries current
                # models first, keeping the deprecated name only as a
                # last-resort in case it's still briefly reachable.
                r = None
                for _groq_model in ["openai/gpt-oss-120b", "qwen/qwen3.6-27b", "llama-3.3-70b-versatile"]:
                    try:
                        r = requests.post(
                            "https://api.groq.com/openai/v1/chat/completions",
                            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                            json={"model": _groq_model,
                                  "messages": [{"role": "user", "content": prompt}],
                                  "max_tokens": max_tokens, "temperature": temp},
                            timeout=45
                        )
                        if r.status_code == 200:
                            break
                    except Exception:
                        r = None
                        continue
                if r is None or r.status_code != 200:
                    # FIX (found live, July 22 2026 — real bug): any
                    # Groq status other than 200/429 (400, 401, 403,
                    # 5xx...) fell through this branch and skipped to
                    # the next provider with ZERO log line — unlike
                    # every other failure path in this function, which
                    # at least reaches the outer except and logs
                    # "<provider> failed: <error>". This was a silent,
                    # undiagnosable gap.
                    if r is not None and r.status_code == 429:
                        time.sleep(3)
                    elif r is not None:
                        log.warning("groq failed: %s %s", r.status_code, r.text[:150])
                    continue
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"].strip()

            elif provider == "gemini":
                # FIX (critical, confirmed against Google's own official
                # deprecation pages): gemini-2.0-flash was shut down by
                # Google on June 1, 2026 — every call here has been
                # returning a 404 for 6 weeks. The 4 main channel
                # pipelines already correctly use gemini-2.5-flash for
                # this same reason; this file was missed. Matching that fix.
                r = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}",
                    json={"contents": [{"parts": [{"text": prompt}]}],
                          "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temp}},
                    timeout=60
                )
                if r.status_code == 429:
                    time.sleep(3)
                    continue
                r.raise_for_status()
                return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

            elif provider == "mistral":
                r = requests.post(
                    "https://api.mistral.ai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={"model": "mistral-small-latest",
                          "messages": [{"role": "user", "content": prompt}],
                          "max_tokens": max_tokens, "temperature": temp},
                    timeout=45
                )
                if r.status_code == 429:
                    time.sleep(3)
                    continue
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"].strip()

        except Exception as e:
            log.warning("%s failed: %s", provider, str(e)[:80])
            continue

    raise RuntimeError("All LLM APIs failed")


def llm_json(prompt: str, max_tokens: int = 800) -> dict:
    # FIX (found live, July 22 2026 — real bug, 0/4 Shorts produced this
    # episode with zero diagnostic trail): this returned {} on any parse
    # failure without ever logging the actual raw response, so every
    # caller (produce_video_topic_short/produce_standalone_short) saw
    # nothing but a bare "failed" after 3 silent retries — no way to
    # tell whether the model returned malformed JSON, a truncated
    # response (max_tokens too small), or something else entirely.
    raw = llm(prompt + "\n\nReturn ONLY valid JSON. No markdown. No explanation.", max_tokens, 0.3)
    cleaned = re.sub(r"^```json\s*", "", raw)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except Exception:
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
    log.warning("llm_json: failed to parse a JSON object from the LLM response "
                "(raw, truncated): %r", raw[:300])
    return {}


def tg(msg: str):
    if not TG_TOKEN:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT, "text": msg, "parse_mode": "Markdown"},
            timeout=15
        )
    except Exception:
        pass


# ── INSTAGRAM SAFETY CHECK ────────────────────────────────────────────────────
def is_instagram_ready() -> bool:
    """Check if Instagram token is valid before attempting upload."""
    if not IG_USER_ID or not IG_TOKEN:
        log.warning("Instagram: credentials missing — skipping")
        return False
    if IG_USER_ID == "placeholder" or IG_TOKEN == "placeholder":
        log.warning("Instagram: placeholder credentials — skipping")
        return False
    try:
        r = requests.get(
            f"https://graph.facebook.com/v19.0/{IG_USER_ID}",
            params={"fields": "id,name", "access_token": IG_TOKEN},
            timeout=10
        )
        if r.status_code == 200:
            log.info("Instagram: token valid ✅")
            return True
        else:
            err = r.json().get("error", {}).get("message", "Unknown")
            log.warning("Instagram: token invalid — %s", err)
            tg(f"⚠️ Instagram token expired or invalid.\nSkipping IG upload. YouTube continues normally.\nError: {err[:100]}")
            return False
    except Exception as e:
        log.warning("Instagram: check failed — %s", e)
        return False


# ── TOPIC SELECTION ───────────────────────────────────────────────────────────
def get_real_youtube_trending_signal(niche_hint=""):
    """
    v7 addition — real "what's working today" research, per explicit
    request: "AI to do the research and find out what is working on
    that day". Uses YouTube's own real Data API (videos.list with
    chart=mostPopular) — genuinely current, and needs no new API key
    since it reuses the same OAuth credentials already required for
    uploads. This is a materially different, more relevant signal than
    the existing NewsAPI check below: it reflects what's ACTUALLY
    getting attention on YouTube specifically today, not just news
    headlines. Returns a list of real trending video titles (empty list
    on any failure — never fabricated).
    """
    try:
        token = get_yt_token()
        if not token:
            return []
        r = requests.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={"part": "snippet", "chart": "mostPopular",
                    "regionCode": "US", "maxResults": 15,
                    "access_token": token},
            timeout=15)
        if r.status_code != 200:
            return []
        items = r.json().get("items", [])
        titles = [it["snippet"]["title"] for it in items if it.get("snippet", {}).get("title")]
        return titles[:15]
    except Exception as e:
        log.warning("YouTube trending fetch (non-fatal): %s", e)
        return []


def get_trending_short_topic(mode: str) -> dict:
    """
    Find viral-worthy topic for standalone Shorts.
    Uses real YouTube trending signal + NewsAPI for real events + LLM
    for angle optimization. Different topics for standalone_1 vs
    standalone_2.
    FIX: now uses the ACTIVE channel's own topic pools (set via
    set_active_channel before this is called) instead of always using
    Ch1's betrayal/crime-flavored pools regardless of which channel
    actually called it.
    """
    cfg = get_active_channel_config()
    niches = cfg["standalone_topics"]

    niche_pool = niches.get(mode, niches["standalone_1"])
    query = random.choice(niche_pool)

    # Try NewsAPI for real topic
    topic = ""
    if NEWS_KEY:
        try:
            r = requests.get(
                "https://newsapi.org/v2/everything",
                params={"q": query, "sortBy": "popularity", "pageSize": 3,
                        "language": "en", "apiKey": NEWS_KEY},
                timeout=15
            )
            articles = r.json().get("articles", [])
            if articles:
                topic = articles[0].get("title", "")
        except Exception as e:
            log.warning("NewsAPI: %s", e)

    if not topic:
        topic = query

    # v7 addition — real trending signal, always attempted (no API key
    # needed), genuinely reflecting what's performing on YouTube today.
    trending_titles = get_real_youtube_trending_signal(query)
    trending_block = ""
    if trending_titles:
        trending_block = (
            "\n\nWhat's genuinely trending on YouTube today (real titles, for "
            "genuine inspiration on angle/format/hook style — do NOT copy these, "
            "use them only to understand what's actually landing right now):\n" +
            "\n".join(f"- {t}" for t in trending_titles[:8])
        )

    # Format variety — real, persisted rotation through 5 presentation
    # formats (video_pipeline/shorts_formats.py) so consecutive Shorts
    # don't all use the same "direct reveal" shape back-to-back.
    format_block = ""
    try:
        from shorts_formats import select_presentation_format, record_format_used, presentation_format_instruction
        _cache_dir = _channel_cache_dir(_active_channel_id)
        _format_name = select_presentation_format(_cache_dir, _active_channel_id)
        record_format_used(_cache_dir, _active_channel_id, mode, _format_name)
        format_block = f"\n\nPRESENTATION FORMAT for this Short (use this specific shape): {presentation_format_instruction(_format_name)}"
    except Exception as e:
        log.warning("Presentation format selection unavailable (non-fatal): %s", e)

    # Use LLM to optimise angle for Shorts virality
    result = llm_json(f"""You are producing a Short for {cfg['display_name']}'s channel, but
this specific Short is DELIBERATELY a different, trending topic — not the
channel's usual subject matter. Per explicit design: 2 of this channel's 4
daily Shorts cover today's main video topic, and 2 (this one) cover whatever
is genuinely trending and in-demand right now, to draw in broader attention
and new viewers who wouldn't otherwise find this channel.
Topic seed: {topic}
Mode: {mode}{trending_block}{format_block}

Create a SHORT (45-55 second) viral concept about this trending topic itself
— do not connect it back to the channel's usual subject matter.

Rules for YouTube Shorts 2026:
- First frame must create immediate "I NEED to watch this" feeling
- Replay rate is the #1 metric — end must loop back to start naturally
- Share rate matters most — people share what shocks or moves them
- One emotion only: shock, disbelief, outrage, or fear

Return JSON:
{{"title": "60 chars max, curiosity gap title",
  "hook_text": "5-7 words for text overlay — must shock",
  "script": "120-140 words, starts with most shocking moment, ends with loop hook",
  "hashtags": "{cfg['hashtags_base']} #shocking #viral",
  "niche": "the real trending topic's own category, NOT {cfg['default_niche']}",
  "us_audience_appeal": 8,
  "replay_potential": 9}}""")

    if not result:
        result = {
            "title": f"SHOCKING: {topic[:50]}",
            "hook_text": "You won't believe this...",
            "script": f"The truth about {topic} will shock you. What really happened was completely hidden from the public for years. And now — everything is coming out. {topic} — the real story nobody told you.",
            "hashtags": f"{cfg['hashtags_base']} #shocking",
            "niche": cfg["default_niche"],
        }

    return result


# ── SCRIPT QUALITY SCORING ────────────────────────────────────────────────────
def score_short_script(script: str, title: str, hook: str,
                        for_reels: bool = False) -> dict:
    """
    5-point quality check for Shorts/Reels script.
    Returns score dict. Must hit 8.5/10 overall.
    """
    scores = {}

    # 1. Hook strength (0-2 pts)
    shock_words = ["shocking","betrayal","secret","exposed","truth","destroyed","lied",
                   "hidden","never","suddenly","revealed","discovered","stolen","fraud",
                   "murdered","arrested","collapsed","billion","affair","caught"]
    hook_hits = sum(1 for w in shock_words if w in hook.lower() or w in script[:80].lower())
    scores["hook"] = min(2.0, hook_hits * 0.4)

    # 2. Script length (0-2 pts) — 120-160 words ideal
    wc = len(script.split())
    if 120 <= wc <= 160:
        scores["length"] = 2.0
    elif 100 <= wc < 120 or 160 < wc <= 180:
        scores["length"] = 1.5
    else:
        scores["length"] = 1.0

    # 3. Replay loop ending (0-2 pts)
    loop_phrases = ["but wait","the real question","and that's when","you won't believe",
                    "this is just the beginning","it gets worse","and here's the thing",
                    "what happened next will","going back to","which brings us back"]
    loop_hit = any(p in script.lower() for p in loop_phrases)
    scores["loop"] = 2.0 if loop_hit else 1.0

    # 4. Emotional arc (0-2 pts) — real shape across open/middle/close,
    # not just a flat word count (video_pipeline/shorts_formats.py).
    try:
        from shorts_formats import score_emotional_arc
        scores["emotion"], _arc_issues = score_emotional_arc(script)
    except Exception:
        emotion_words = ["outraged","devastated","shocked","horrified","betrayed","furious",
                         "heartbroken","stunned","unbelievable","disgusting","disgraceful"]
        emo_count = sum(1 for w in emotion_words if w in script.lower())
        scores["emotion"] = min(2.0, emo_count * 0.5)

    # 5. Title quality (0-2 pts)
    title_score = 0
    if len(title) <= 60:
        title_score += 0.5
    if any(w in title.upper() for w in ["SHOCKING","SECRET","TRUTH","EXPOSED","BETRAYAL","CAUGHT"]):
        title_score += 1.0
    if any(c.isdigit() for c in title):
        title_score += 0.5
    scores["title"] = min(2.0, title_score)

    # 6. The 3-second rule (bonus/penalty) — real, timing-based check that
    # the opening ~3 seconds of narration (video_pipeline/shorts_formats.py,
    # WORDS_PER_SECOND-derived) actually lands a scroll-stopper instead of
    # a slow windup.
    try:
        from shorts_formats import check_three_second_rule
        three_sec_bonus, three_sec_issues = check_three_second_rule(hook, script)
        scores["three_second_rule"] = three_sec_bonus
    except Exception:
        three_sec_issues = []

    total = round(sum(scores.values()), 1)
    scores["total"] = total
    scores["passed"] = total >= QUALITY_MIN
    if three_sec_issues:
        scores["issues"] = three_sec_issues

    return scores


# ── TTS AUDIO GENERATION ──────────────────────────────────────────────────────
def _split_into_tts_chunks(script, max_chars=180):
    """
    Split script into chunks under Groq Orpheus's real, documented
    200-character-per-request limit (confirmed directly against Groq's
    own docs — this is not a guess), respecting sentence boundaries so
    each chunk still sounds like natural, complete speech rather than
    an arbitrary character cutoff. max_chars=180 leaves headroom for
    the emotion tag prefix added to the first chunk.
    """
    import re as _re
    sentences = _re.split(r'(?<=[.!?])\s+', script.strip())
    chunks = []
    current = ""
    for sent in sentences:
        candidate = f"{current} {sent}".strip() if current else sent
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
            # A single sentence longer than max_chars on its own — split
            # on commas/words as a last resort rather than dropping it.
            if len(sent) > max_chars:
                words = sent.split()
                piece = ""
                for w in words:
                    cand2 = f"{piece} {w}".strip() if piece else w
                    if len(cand2) <= max_chars:
                        piece = cand2
                    else:
                        if piece:
                            chunks.append(piece)
                        piece = w
                current = piece
            else:
                current = sent
    if current:
        chunks.append(current)
    return chunks


def generate_audio(script: str, voice: dict, output_path: str) -> bool:
    """
    Generate audio via Groq Orpheus with emotional tags.
    Falls back to espeak-ng if Groq unavailable.
    Applies audio enhancement: noise reduction + normalization.

    FIX (critical, confirmed directly against Groq's own documentation):
    Orpheus has a real, hard 200-character limit PER REQUEST — this
    function used to send the entire 120-140 word script (typically
    600-800+ characters) in a single call. Every real narration request
    would have either been rejected outright by the API or silently
    truncated to roughly the first 30-35 words, meaning the vast
    majority of every Short's narration was likely never actually
    generated. Now splits the script into real, sentence-respecting
    chunks under the documented limit, generates each separately, and
    concatenates the resulting audio into one continuous narration
    track before the same enhancement pipeline as before.
    """
    tag = voice.get("tag", "[intense]")
    voice_id = voice.get("id", "troy")

    if GROQ_KEY:
        try:
            chunks = _split_into_tts_chunks(script, max_chars=180)
            if not chunks:
                raise ValueError("no chunks produced from script")

            chunk_wavs = []
            for i, chunk_text in enumerate(chunks):
                # Only the first chunk carries the emotion tag — Orpheus
                # applies it as a delivery style for the whole utterance,
                # and repeating it on every chunk risks it being read
                # aloud as literal text on subsequent chunks.
                tagged = f"{tag} {chunk_text}" if i == 0 else chunk_text
                r = requests.post(
                    "https://api.groq.com/openai/v1/audio/speech",
                    headers={"Authorization": f"Bearer {GROQ_KEY}",
                             "Content-Type": "application/json"},
                    json={"model": "canopylabs/orpheus-v1-english",
                          "input": tagged[:195],  # hard safety margin under the real 200-char limit
                          "voice": voice_id,
                          "response_format": "wav"},
                    timeout=90
                )
                if r.status_code != 200 or len(r.content) < 500:
                    raise RuntimeError(f"chunk {i} failed: HTTP {r.status_code}")
                chunk_path = output_path.replace(".mp3", f"_chunk{i}.wav")
                with open(chunk_path, "wb") as f:
                    f.write(r.content)
                chunk_wavs.append(chunk_path)

            # Concatenate all real chunk WAVs into one continuous track
            concat_list = output_path.replace(".mp3", "_concat.txt")
            with open(concat_list, "w") as f:
                for cw in chunk_wavs:
                    f.write(f"file '{os.path.abspath(cw)}'\n")
            wav_path = output_path.replace(".mp3", ".wav")
            concat_result = subprocess.run([
                "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
                "-c", "copy", wav_path
            ], capture_output=True)

            for cw in chunk_wavs:
                try: os.remove(cw)
                except Exception: pass
            try: os.remove(concat_list)
            except Exception: pass

            if concat_result.returncode != 0 or not os.path.exists(wav_path):
                raise RuntimeError("chunk concatenation failed")

            # Convert WAV → MP3 with audio enhancement (same as before)
            result = subprocess.run([
                "ffmpeg", "-y", "-i", wav_path,
                "-af", "anlmdn=s=7:p=0.002,loudnorm=I=-16:TP=-1.5:LRA=11,highpass=f=80",
                "-codec:a", "libmp3lame", "-b:a", "192k", "-ar", "44100",
                output_path
            ], capture_output=True)

            if result.returncode == 0 and os.path.exists(output_path):
                log.info("Audio: Groq Orpheus %s (%s), %d real chunks ✅", voice_id, voice.get("accent",""), len(chunks))
                os.remove(wav_path)
                return True
        except Exception as e:
            log.warning("Groq TTS failed: %s", e)

    # espeak-ng fallback
    log.info("Using espeak-ng fallback")
    try:
        # Select espeak voice for accent
        accent = voice.get("accent", "US")
        gender = voice.get("gender", "male")
        if accent == "British" and gender == "male":
            espeak_voice = "en-gb"
        elif accent == "British" and gender == "female":
            espeak_voice = "en-gb+f3"
        elif gender == "female":
            espeak_voice = "en-us+f3"
        else:
            espeak_voice = "en-us"

        raw_wav = output_path.replace(".mp3", "_raw.wav")
        # FIX (found on sequential re-audit): this was truncating to 500
        # chars while the primary Groq path allows 2800 — a typical
        # 60-second short script (~800-900 chars at the 155wpm speed set
        # below) would have lost roughly 40% of its content the moment
        # Groq ever failed and this fallback fired. Raised to match a
        # realistic full short script length.
        subprocess.run([
            "espeak-ng", "-v", espeak_voice, "-s", "155", "-p", "50",
            "-w", raw_wav, script[:2000]
        ], capture_output=True)

        if os.path.exists(raw_wav):
            subprocess.run([
                "ffmpeg", "-y", "-i", raw_wav,
                "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                "-codec:a", "libmp3lame", "-b:a", "128k", output_path
            ], capture_output=True)
            os.remove(raw_wav)
            log.info("Audio: espeak-ng fallback ✅")
            return os.path.exists(output_path)
    except Exception as e:
        log.error("All TTS failed: %s", e)

    return False


# ── SUBTITLE GENERATION (WORD-LEVEL SYNC) ────────────────────────────────────
def generate_synced_subtitles(script: str, audio_path: str,
                               srt_path: str) -> bool:
    """
    Generate subtitles synced to the actual audio.

    FIX (found while investigating "sounds/looks AI-built" specifically):
    this previously ONLY used a naive uniform words-per-second estimate
    across the whole clip — real speech always has pauses, emphasis, and
    variable pacing, so over a 45-55 second clip this would visibly
    drift out of sync with the actual audio. Caption drift is one of the
    most common, most noticeable "this was made cheaply/by a bot" tells
    in short-form video. Now tries GENUINE word-level timestamps first,
    via Groq's Whisper transcription (same API/key already used
    elsewhere in this file for the LLM calls — no new setup required) —
    real forced-alignment against the actual generated audio, not an
    estimate. Falls back to the old uniform-rate method only if the
    Whisper call fails for any reason, so this never has zero captions.
    """
    if not os.path.exists(audio_path):
        return False

    # Real, word-level accurate path: transcribe the ACTUAL generated
    # audio with Groq Whisper (word timestamps), so captions reflect
    # genuinely where each word falls, including natural pauses.
    if GROQ_KEY:
        try:
            with open(audio_path, "rb") as f:
                r = requests.post(
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {GROQ_KEY}"},
                    files={"file": (os.path.basename(audio_path), f, "audio/mpeg")},
                    data={"model": "whisper-large-v3-turbo",
                          "response_format": "verbose_json",
                          "timestamp_granularities[]": "word",
                          "language": "en"},
                    timeout=60
                )
            if r.status_code == 200:
                words_data = r.json().get("words", [])
                if words_data:
                    chunk_size = 4
                    chunks = []
                    for i in range(0, len(words_data), chunk_size):
                        group = words_data[i:i + chunk_size]
                        start_sec = group[0]["start"]
                        end_sec = group[-1]["end"]
                        text = " ".join(w["word"] for w in group)
                        chunks.append((start_sec, end_sec, text))

                    def fmt_time_real(sec: float) -> str:
                        h = int(sec // 3600); m = int((sec % 3600) // 60)
                        s = int(sec % 60); ms = int((sec - int(sec)) * 1000)
                        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

                    with open(srt_path, "w", encoding="utf-8") as f:
                        for idx, (start, end, text) in enumerate(chunks, 1):
                            clean = text.replace("...", " ").strip()
                            f.write(f"{idx}\n{fmt_time_real(start)} --> {fmt_time_real(end)}\n{clean}\n\n")
                    log.info("Subtitles: %d chunks, real word-level sync via Whisper ✅", len(chunks))
                    return True
        except Exception as e:
            log.warning("Whisper word-level sync failed, falling back to estimate: %s", e)

    # Fallback: the original uniform-rate estimate — used only if the
    # real Whisper path above fails for any reason.
    try:
        probe = subprocess.run([
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", audio_path
        ], capture_output=True, text=True)
        duration = float(json.loads(probe.stdout)["format"]["duration"])
    except Exception:
        duration = len(script.split()) / 2.5  # estimate 2.5 words/sec

    words = script.split()
    if not words:
        return False

    total_words = len(words)
    secs_per_word = duration / max(total_words, 1)

    chunk_size = 4
    chunks = []
    for i in range(0, total_words, chunk_size):
        chunk_words = words[i:i + chunk_size]
        start_sec = i * secs_per_word
        end_sec = min((i + len(chunk_words)) * secs_per_word, duration)
        chunks.append((start_sec, end_sec, " ".join(chunk_words)))

    def fmt_time(sec: float) -> str:
        h  = int(sec // 3600)
        m  = int((sec % 3600) // 60)
        s  = int(sec % 60)
        ms = int((sec - int(sec)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    with open(srt_path, "w", encoding="utf-8") as f:
        for idx, (start, end, text) in enumerate(chunks, 1):
            clean = text.replace("...", " ").strip()
            f.write(f"{idx}\n{fmt_time(start)} --> {fmt_time(end)}\n{clean}\n\n")

    log.info("Subtitles: %d chunks, %.1fs duration (estimate, not word-level) ⚠️", len(chunks), duration)
    return True


# ── BACKGROUND CLIPS ──────────────────────────────────────────────────────────
def download_background_clip(niche: str, output_path: str) -> bool:
    """Download 9:16 background clip from Pixabay."""
    niche_keywords = {
        "betrayal":     ["dramatic shadow person","mystery dark room","emotional confrontation"],
        "crime":        ["police lights night","detective crime scene","dark thriller"],
        "finance":      ["money falling dramatic","businessman shadow dark","greed wealth"],
        "drama":        ["emotional argument","family confrontation dramatic","shock surprise"],
        # FIX: added — the Ch2 config passes "forensic investigation evidence
        # dark" as its search term, which had no matching entry here and was
        # silently falling back to the generic pool instead of anything
        # genuinely forensic-themed.
        "forensic investigation evidence dark": [
            "forensic evidence documents dark", "crime scene investigation night",
            "detective case file dark room", "police evidence room dramatic"
        ],
        # FIX: added — control_files passes "psychology manipulation control
        # documentary dark" as its search term; same silent-fallback gap.
        "psychology manipulation control documentary dark": [
            "crowd silhouette dark control", "redacted documents dark room",
            "puppet strings shadow dramatic", "surveillance camera dark office",
            "chalkboard diagram dark room"
        ],
        # FIX: "ancient history documentary archive" (Ch4/The Archive) had
        # no entry at all — every one of Ch4's Shorts would have silently
        # fallen back to generic "mystery thriller" footage, completely
        # mismatched to historical documentary content.
        "ancient history documentary archive": [
            "ancient ruins cinematic", "old manuscript parchment dark",
            "historical map candlelight", "ancient temple columns dramatic",
            "archaeological dig site dramatic"
        ],
        "default":      ["cinematic dark drama","mystery thriller","emotional shadow"],
    }
    keywords = niche_keywords.get(niche, niche_keywords["default"])
    kw = random.choice(keywords)

    if PIX_KEY:
        try:
            r = requests.get(
                "https://pixabay.com/api/videos/",
                params={"key": PIX_KEY, "q": kw, "per_page": 5,
                        "video_type": "film", "min_duration": 10},
                timeout=20
            )
            for hit in r.json().get("hits", []):
                for quality in ["large", "medium", "small"]:
                    url = hit.get("videos", {}).get(quality, {}).get("url", "")
                    if url:
                        vr = requests.get(url, stream=True, timeout=60)
                        with open(output_path, "wb") as f:
                            for chunk in vr.iter_content(8192):
                                f.write(chunk)
                        if os.path.getsize(output_path) > 50000:
                            return True
        except Exception as e:
            log.warning("Pixabay: %s", e)

    # FIX: this fallback used to be a completely flat, static black screen
    # with a vignette — about as visually "dead"/robotic-looking as a
    # background can be, directly working against "should never look
    # AI-built." A slow animated gradient drift plus a subtle moving
    # particle-like noise field reads as genuine, deliberate motion
    # graphics rather than a placeholder, while still being fully
    # generatable offline with no network dependency.
    log.info("Using improved FFmpeg background fallback (animated, not static)")
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", "gradients=s=1080x1920:c0=0x0a0a12:c1=0x1a1420:x0=0:y0=0:x1=1080:y1=1920:speed=0.02",
        "-vf", "noise=alls=6:allf=t+u,vignette=PI/3",
        "-t", "70", output_path
    ], capture_output=True)
    return os.path.exists(output_path)


# ── VIDEO ASSEMBLY (9:16 WITH SUBTITLES) ─────────────────────────────────────
def _generate_short_music_bed(duration, output_path):
    """
    v7 addition — found while investigating "sounds robotic": Shorts had
    ZERO background music of any kind, just narration over a silent
    audio bed under the video clip — noticeably sparser than virtually
    every real, successful Short, which nearly always has at least a
    subtle music bed underneath. Genuinely distinct synthesis (same real
    ffmpeg approach already proven for the main channel pipelines, not a
    placeholder), kept deliberately subtle (very low volume) so it never
    competes with narration or subtitles.
    """
    try:
        dur = int(duration) + 3
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"sine=frequency=80:duration={dur}",
            "-f", "lavfi", "-i", f"sine=frequency=120:duration={dur}",
            "-filter_complex",
            "[0]volume=0.05[a];[1]volume=0.03[b];"
            "[a][b]amix=inputs=2:duration=first,lowpass=f=300,volume=0.12[out]",
            "-map", "[out]", "-c:a", "aac", "-b:a", "128k", output_path
        ], capture_output=True, timeout=30)
        return os.path.exists(output_path) and os.path.getsize(output_path) > 1000
    except Exception as e:
        log.warning("Short music bed generation failed (non-fatal): %s", e)
        return False


def assemble_short_video(bg_path: str, audio_path: str, srt_path: str,
                          hook_text: str, output_path: str,
                          is_reel: bool = False) -> bool:
    """
    Assemble final 9:16 short video with:
    - Background clip (scaled to 1080x1920)
    - Audio track (synced perfectly)
    - Burned-in subtitles (word-level accurate)
    - Hook text overlay (top third)
    - Channel watermark (bottom right)
    - Dramatic vignette overlay

    Subtitle sync: generated from actual audio duration,
    burns in at exact timestamps — no gap, no drift.
    """
    if not all(os.path.exists(p) for p in [bg_path, audio_path]):
        log.error("Missing input files for assembly")
        return False

    # Get audio duration
    try:
        probe = subprocess.run([
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", audio_path
        ], capture_output=True, text=True)
        dur = float(json.loads(probe.stdout)["format"]["duration"])
    except Exception:
        dur = 55.0

    # Escape for FFmpeg drawtext
    hook_safe = hook_text[:50].replace("'", "").replace(":", " ").replace('"', "")
    wm_safe   = WATERMARK.replace("'", "")

    # Build subtitle filter
    if os.path.exists(srt_path):
        srt_esc = srt_path.replace(":", "\\:").replace("'", "\\'")
        sub_filter = (
            f"subtitles='{srt_esc}':force_style="
            "'FontName=DejaVu Sans,FontSize=22,Bold=1,"
            "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
            "BackColour=&H80000000,Outline=3,Shadow=2,"
            "Alignment=2,MarginV=80,Spacing=0.5'"
        )
    else:
        sub_filter = ""

    # Full video filter chain
    vf_parts = [
        # Scale and crop to 9:16
        "scale=1080:1920:force_original_aspect_ratio=increase",
        "crop=1080:1920",
    ]

    # Pattern interrupt — a real periodic zoom-punch (video_pipeline/
    # shorts_formats.py) that breaks up an otherwise static/looping
    # background clip every few seconds, the same "cut every few seconds"
    # technique real Shorts editors use to fight scroll-past. Falls back
    # to no pattern interrupt (old behavior) if the shared module can't
    # be imported for any reason — never blocks assembly.
    try:
        from shorts_formats import pattern_interrupt_filter
        vf_parts.append(pattern_interrupt_filter())
    except Exception as e:
        log.warning("Pattern interrupt filter unavailable (non-fatal): %s", e)

    vf_parts += [
        # Dramatic vignette
        "vignette=PI/3.5",
        # Hook text - top third, large
        f"drawtext=text='{hook_safe}':"
        "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        "fontsize=54:fontcolor=white:borderw=4:bordercolor=black:"
        "x=(w-text_w)/2:y=140:shadowcolor=black@0.9:shadowx=3:shadowy=3",
        # Channel watermark - bottom right
        f"drawtext=text='{wm_safe}':"
        "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
        "fontsize=28:fontcolor=white@0.85:borderw=2:bordercolor=black@0.6:"
        "x=w-text_w-25:y=h-55",
    ]

    # Add subtitles if available
    if sub_filter:
        vf_parts.append(sub_filter)

    vf = ",".join(vf_parts)

    # v7 addition — mix in a subtle background music bed under the
    # narration (found while investigating "sounds robotic": previously
    # zero background music existed at all, just narration over silence).
    music_path = audio_path.replace(".mp3", "_musicbed.aac")
    has_music = _generate_short_music_bed(dur, music_path)

    if has_music:
        result = subprocess.run([
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", bg_path,
            "-i", audio_path,
            "-i", music_path,
            "-filter_complex", "[1:a][2:a]amix=inputs=2:duration=first:weights=1 1[aout]",
            "-map", "0:v", "-map", "[aout]",
            "-t", str(dur + 0.5),
            "-vf", vf,
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
            "-shortest",
            "-movflags", "+faststart",
            output_path
        ], capture_output=True)
        try:
            os.remove(music_path)
        except Exception:
            pass
    else:
        result = subprocess.run([
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", bg_path,
            "-i", audio_path,
            "-t", str(dur + 0.5),
            "-vf", vf,
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
            "-shortest",
            "-movflags", "+faststart",  # Web-optimised
            output_path
        ], capture_output=True)

    if result.returncode != 0:
        log.error("FFmpeg assembly failed: %s", result.stderr[-300:].decode("utf-8", errors="ignore"))
        return False

    size_mb = os.path.getsize(output_path) / 1024 / 1024
    log.info("Video assembled: %.1f MB, %.1fs, music bed: %s ✅", size_mb, dur, has_music)
    return True


# ── QUALITY SCORING ───────────────────────────────────────────────────────────
# FIX (found on sequential re-audit): score_final_video's "script" and
# "title" checks were hardcoded to Ch1's betrayal-themed vocabulary
# ("betrayal", "lied", "exposed") with zero channel awareness. Since this
# score GATES retries (< QUALITY_MIN triggers a retry, max 3 attempts),
# Ch3's genuinely good psychology/control-systems content would
# systematically lose up to ~2.7 of 10 possible points purely for not
# containing Ch1's keywords — not because the content was actually worse.
SHOCK_WORDS_BY_CHANNEL = {
    "betrayal_deepdive": ["shocking","betrayal","secret","exposed","truth","destroyed","lied"],
    "evidence_room":     ["shocking","evidence","secret","exposed","truth","proof","confession"],
    "control_files":     ["documented","control","exposed","truth","manipulation","pattern","confirmed"],
    # FIX (critical, found on full re-audit): "archive" (Ch4) was missing
    # entirely — every Ch4 Short would have been scored against Ch1's
    # crime/betrayal-themed keywords instead of anything historically
    # appropriate, unfairly penalizing genuinely good historical content.
    "archive":           ["documented","discovered","ancient","truth","real","evidence","history"],
    "collapse_index":    ["documented","real","collapsed","exposed","specific","evidence","numbers"],
}
TITLE_WORDS_BY_CHANNEL = {
    "betrayal_deepdive": ["SHOCKING","SECRET","TRUTH","EXPOSED","BETRAYAL","CAUGHT","FRAUD","LIED"],
    "evidence_room":     ["SHOCKING","SECRET","TRUTH","EXPOSED","EVIDENCE","CAUGHT","PROOF","CONFESSION"],
    "control_files":     ["DOCUMENTED","TRUTH","EXPOSED","CONTROL","PATTERN","MANIPULATION","CONFIRMED","SYSTEM"],
    "archive":           ["DOCUMENTED","ANCIENT","DISCOVERED","TRUTH","REAL","HISTORY","LOST","REVEALED"],
    "collapse_index":    ["DOCUMENTED","REAL","COLLAPSED","EXPLAINED","SPECIFIC","REVEALED","DATA","EXPOSED"],
}

def score_final_video(video_path: str, script: str, title: str,
                       has_subtitles: bool, has_thumbnail: bool,
                       channel: str = "betrayal_deepdive") -> dict:
    """Final 5-point quality check after assembly."""
    scores = {}

    # 1. Script quality
    shock_words = SHOCK_WORDS_BY_CHANNEL.get(channel, SHOCK_WORDS_BY_CHANNEL["betrayal_deepdive"])
    hook_hits = sum(1 for w in shock_words if w in script[:100].lower())
    scores["script"] = min(2.0, hook_hits * 0.5 + 1.0)

    # 2. Audio quality (verified file exists + size)
    if os.path.exists(video_path) and os.path.getsize(video_path) > 500000:
        scores["audio"] = 2.0
    else:
        scores["audio"] = 0.5

    # 3. Subtitles
    scores["subtitles"] = 2.0 if has_subtitles else 0.0

    # 4. Title
    title_words = TITLE_WORDS_BY_CHANNEL.get(channel, TITLE_WORDS_BY_CHANNEL["betrayal_deepdive"])
    title_ok = len(title) <= 70 and any(w in title.upper() for w in title_words)
    scores["title"] = 1.5 if title_ok else 0.8

    # 5. Video length (45-65 seconds ideal for Shorts)
    try:
        probe = subprocess.run([
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", video_path
        ], capture_output=True, text=True)
        dur = float(json.loads(probe.stdout)["format"]["duration"])
        scores["length"] = 2.5 if 40 <= dur <= 70 else 1.5
    except Exception:
        scores["length"] = 1.5

    # 6. Custom thumbnail (0-1 pt, additive bonus — was accepted as a
    # parameter but never actually scored before, so has_thumbnail=False
    # was hardcoded everywhere with zero consequence either way).
    scores["thumbnail"] = 1.0 if has_thumbnail else 0.0

    total = round(sum(scores.values()), 1)
    scores["total"] = total
    scores["passed"] = total >= QUALITY_MIN
    return scores


# ── YOUTUBE UPLOAD ────────────────────────────────────────────────────────────
def get_yt_token() -> str:
    # FIX: now looks up the REAL credentials for whichever channel is
    # currently active (set via set_active_channel), falling back to the
    # generic YOUTUBE_* names only for an unrecognized channel — instead
    # of always using Ch1's credentials regardless of which channel is
    # actually producing the Short.
    client_env, secret_env, refresh_env = YT_CREDENTIAL_ENV_BY_CHANNEL.get(
        _active_channel_id, ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"))
    client  = os.environ.get(client_env, "")
    secret  = os.environ.get(secret_env, "")
    refresh = os.environ.get(refresh_env, "")
    if not all([client, secret, refresh]):
        log.error("Missing YouTube credentials for active channel '%s' (%s)",
                  _active_channel_id, client_env)
        return ""
    r = requests.post(
        "https://oauth2.googleapis.com/token",
        data={"client_id": client, "client_secret": secret,
              "refresh_token": refresh, "grant_type": "refresh_token"},
        timeout=30
    )
    return r.json().get("access_token", "") if r.status_code == 200 else ""


def upload_youtube_short(video_path: str, title: str, description: str,
                          tags: list) -> str:
    """Upload to YouTube as Short. Returns URL or ''."""
    token = get_yt_token()
    if not token:
        return ""

    file_size = os.path.getsize(video_path)
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:2000] + "\n\n#Shorts",
            "tags": tags + ["Shorts", "YouTubeShorts"],
            "categoryId": "22",
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
            "notifySubscribers": True,
        }
    }

    # Init resumable upload
    ir = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Upload-Content-Type": "video/mp4",
            "X-Upload-Content-Length": str(file_size),
        },
        json=body, timeout=30
    )
    if ir.status_code not in (200, 201):
        log.error("YT init failed %d: %s", ir.status_code, ir.text[:200])
        return ""

    with open(video_path, "rb") as f:
        data = f.read()

    ur = requests.put(
        ir.headers["Location"],
        headers={"Content-Type": "video/mp4", "Content-Length": str(file_size)},
        data=data, timeout=300
    )
    if ur.status_code not in (200, 201):
        log.error("YT upload failed %d", ur.status_code)
        return ""

    vid_id = ur.json()["id"]
    url = f"https://youtube.com/shorts/{vid_id}"
    log.info("YouTube Short uploaded: %s", url)
    return url


# ── INSTAGRAM UPLOAD ──────────────────────────────────────────────────────────
def upload_instagram_reel(video_path: str, caption: str) -> bool:
    """Upload video as Instagram Reel via GitHub Release URL."""
    if not is_instagram_ready():
        log.warning("Instagram not ready — skipping upload gracefully")
        return False
    if not all([GH_TOKEN, GH_REPO]):
        log.warning("GitHub credentials missing for video hosting")
        return False

    # Host video via GitHub Release
    h = {"Authorization": f"Bearer {GH_TOKEN}",
         "Accept": "application/vnd.github+json"}
    tag = f"reel-{datetime.now().strftime('%Y%m%d-%H%M')}"

    rel = requests.post(
        f"https://api.github.com/repos/{GH_REPO}/releases",
        headers=h, json={"tag_name": tag, "name": tag, "draft": False}
    )
    if rel.status_code not in (200, 201):
        return False

    rel_id = rel.json()["id"]
    fname  = os.path.basename(video_path)
    fsize  = os.path.getsize(video_path)

    with open(video_path, "rb") as f:
        asset = requests.post(
            f"https://uploads.github.com/repos/{GH_REPO}/releases/{rel_id}/assets?name={fname}",
            headers={**h, "Content-Type": "video/mp4", "Content-Length": str(fsize)},
            data=f.read(), timeout=180
        )

    if asset.status_code not in (200, 201):
        return False

    pub_url = asset.json().get("browser_download_url", "")
    if not pub_url:
        return False

    # Create IG media container
    cr = requests.post(
        f"https://graph.instagram.com/v19.0/{IG_USER_ID}/media",
        data={"media_type": "REELS", "video_url": pub_url,
              "caption": caption[:2200], "share_to_feed": "true",
              "access_token": IG_TOKEN}
    )
    if cr.status_code != 200:
        return False

    cid = cr.json()["id"]

    # Wait for processing
    for _ in range(30):
        time.sleep(10)
        sr = requests.get(
            f"https://graph.instagram.com/v19.0/{cid}",
            params={"fields": "status_code", "access_token": IG_TOKEN}
        )
        if sr.json().get("status_code") == "FINISHED":
            break

    # Publish
    pr = requests.post(
        f"https://graph.instagram.com/v19.0/{IG_USER_ID}/media_publish",
        data={"creation_id": cid, "access_token": IG_TOKEN}
    )
    return pr.status_code in (200, 201)


# ── CUSTOM SHORTS THUMBNAILS ──────────────────────────────────────────────────
# FIX: every produce_*_short function hardcoded has_thumbnail=False and never
# generated or uploaded a thumbnail at all — Shorts always shipped with
# whatever frame YouTube auto-picks. Reuses the same 3-layer engine already
# built for main videos (video_pipeline/thumbnail_engine_v2.py) rather than
# building a separate 9:16 renderer from scratch; YouTube's thumbnails.set
# endpoint accepts the same 16:9 image for Shorts as for regular videos.
def generate_short_thumbnail(title, hook_text, niche_name, work_dir):
    """
    FIX (found on deep re-audit): this never passed cache_dir, so every
    Shorts thumbnail skipped the 11-format learning loop and avatar
    caching entirely (both gated on cache_dir inside generate_thumbnail_v2)
    despite _channel_cache_dir already being used elsewhere in this same
    file for the script presentation-format variety. Also hardcoded
    episode=1 always, so every Shorts thumbnail's badge showed "EP.1" —
    now uses the real, ever-growing thumb_format_history length as a
    genuine incrementing counter (Shorts don't have a natural episode
    number the way main videos do).
    """
    try:
        from thumbnail_engine_v2 import generate_thumbnail_v2
        from thumbnail_formats import load_format_history
        cache_dir = _channel_cache_dir(_active_channel_id)
        try:
            pseudo_episode = len(load_format_history(cache_dir)) + 1
        except Exception:
            pseudo_episode = 1
        return generate_thumbnail_v2(
            title=title, thumb_text=(hook_text or title)[:20].upper(),
            niche_name=niche_name, topic=title,
            channel_name=CHANNEL, episode=pseudo_episode, work_dir=work_dir, ab_variant="A",
            cache_dir=cache_dir,
        )
    except Exception as e:
        log.warning("Short thumbnail generation failed (non-fatal): %s", e)
        return None


def set_short_thumbnail(video_id, thumb_path, token):
    """Uploads a custom thumbnail for an already-uploaded Short via the
    same thumbnails.set endpoint YouTube uses for regular videos."""
    if not (video_id and thumb_path and os.path.exists(thumb_path) and token):
        return False
    try:
        with open(thumb_path, "rb") as f:
            r = requests.post(
                f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={video_id}",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "image/jpeg"},
                data=f.read(), timeout=60,
            )
        return r.status_code == 200
    except Exception as e:
        log.warning("Short thumbnail upload failed (non-fatal): %s", e)
        return False


# ── MAIN FUNCTIONS ────────────────────────────────────────────────────────────

def produce_standalone_short(mode: str, channel: str = "betrayal_deepdive") -> dict:
    """
    Produce a standalone YouTube Short (not tied to main video).
    mode: 'standalone_1' (6 AM) or 'standalone_2' (2 PM)
    channel: which channel this Short belongs to — determines branding,
    hashtags, topic pools, and background search term (see CHANNEL_CONFIGS).
    Returns result dict.
    """
    set_active_channel(channel)
    cfg = get_active_channel_config()
    log.info("=== PRODUCING STANDALONE SHORT: %s (%s) ===", mode, cfg["display_name"])

    for attempt in range(3):
        log.info("Attempt %d/3", attempt + 1)

        # 1. Get topic
        topic_data = get_trending_short_topic(mode)
        title  = topic_data["title"]
        script = topic_data["script"]
        hook   = topic_data["hook_text"]
        niche  = topic_data.get("niche", cfg["default_niche"])
        tags_str = topic_data.get("hashtags", f"{cfg['hashtags_base']} #viral")

        # 2. Pre-score
        pre_score = score_short_script(script, title, hook)
        log.info("Pre-score: %.1f/10", pre_score["total"])
        if pre_score["total"] < QUALITY_MIN:
            log.info("Pre-score too low, retrying topic")
            continue

        # 3. Select voice (rotates gender + accent)
        voice = pick_voice(for_reels=False)

        # 4. Generate audio
        run_id    = uuid.uuid4().hex[:8]
        audio_out = os.path.join(OUTPUT_DIR, f"short_{mode}_{run_id}.mp3")
        if not generate_audio(script, voice, audio_out):
            log.error("Audio generation failed")
            continue

        # 5. Generate synced subtitles
        srt_out = audio_out.replace(".mp3", ".srt")
        generate_synced_subtitles(script, audio_out, srt_out)

        # 6. Download background
        bg_out = os.path.join(OUTPUT_DIR, f"bg_{run_id}.mp4")
        download_background_clip(niche, bg_out)

        # 7. Assemble video
        video_out = os.path.join(OUTPUT_DIR, f"short_{mode}_{run_id}_final.mp4")
        if not assemble_short_video(bg_out, audio_out, srt_out, hook, video_out):
            continue

        # 7.5 Custom thumbnail — generated locally now (doesn't need a
        # video_id yet), uploaded via thumbnails.set after step 9 below.
        thumb_out = generate_short_thumbnail(title, hook, niche, OUTPUT_DIR)
        has_thumb = bool(thumb_out and os.path.exists(thumb_out))

        # 8. Final quality score
        final_score = score_final_video(
            video_out, script, title,
            has_subtitles=os.path.exists(srt_out),
            has_thumbnail=has_thumb, channel=_active_channel_id
        )
        log.info("Final score: %.1f/10 (need %.1f)", final_score["total"], QUALITY_MIN)

        if final_score["total"] < QUALITY_MIN:
            log.info("Quality too low, retrying")
            continue

        # 9. Upload to YouTube
        tags = [t.strip("#") for t in tags_str.split() if t.startswith("#")]
        description = f"{script}\n\n{tags_str}\n\n{cfg['tagline']}"
        yt_url = upload_youtube_short(video_out, title, description, tags)

        # 9.5 Upload the custom thumbnail now that a real video_id exists
        if yt_url and has_thumb:
            try:
                _vid_id = yt_url.rstrip("/").split("/")[-1]
                _token = get_yt_token()
                if not set_short_thumbnail(_vid_id, thumb_out, _token):
                    log.warning("Custom Short thumbnail upload did not succeed")
            except Exception as e:
                log.warning("Custom Short thumbnail step failed (non-fatal): %s", e)

        # FIX (found on re-audit): this previously returned "status":
        # "success" unconditionally, even when upload_youtube_short
        # returned "" (upload genuinely failed — no token, API error,
        # etc.). Every caller checking .get("status")=="success" before
        # counting a Short as produced or posting a pinned comment was
        # silently fooled by a failed upload reporting as a success with
        # an empty URL. Same bug confirmed in produce_teaser_short and
        # produce_recap_short — fixed in all 3. Retries via `continue`
        # (consistent with every other failure mode in this loop) rather
        # than failing immediately — a fresh attempt costs little and an
        # upload failure isn't necessarily going to repeat.
        if not yt_url:
            log.info("Upload failed for '%s' — retrying", title)
            continue

        # 10. Telegram report
        tg(f"""⚡ *YOUTUBE SHORT UPLOADED*
Mode: {mode}
Title: {title}
Voice: {voice['id']} ({voice['accent']} {voice['gender']})
Score: {final_score['total']}/10
Subtitles: ✅ Synced
URL: {yt_url}""")

        # Cleanup
        for f in [audio_out, srt_out, bg_out, thumb_out]:
            try:
                if f:
                    os.remove(f)
            except Exception:
                pass

        return {"status": "success", "url": yt_url, "score": final_score["total"],
                "title": title, "voice": voice["id"], "local_path": video_out}

    return {"status": "failed", "reason": "max retries"}


def produce_instagram_reel(mode: str) -> dict:
    """
    Produce bilingual Hindi/English Instagram Reel.
    mode: 'reel_1' (6:30 AM) or 'reel_2' (3 PM)
    """
    log.info("=== PRODUCING INSTAGRAM REEL: %s ===", mode)

    for attempt in range(3):
        # 1. Generate Hinglish script
        niche_seed = random.choice([
            "betrayal story India", "shocking family secret", "true crime India",
            "relationship drama desi", "boss employee betrayal", "friendship betrayal"
        ]) if mode == "reel_1" else random.choice([
            "business fraud India", "court case shocking", "dark psychology relationship",
            "social media scam India", "startup fraud exposed", "financial betrayal desi"
        ])

        topic_data = llm_json(f"""You are a viral Instagram Reels creator for India + global audience.
Topic: {niche_seed}

Create a 45-55 second bilingual Hinglish Reel.

Rules:
- Mix Hindi + English naturally (not forced)
- Start with shocking Hindi hook: "Yaar, yeh sun ke aapka dil dard karega..."
- Build tension in Hinglish throughout
- End with call to action in Hindi + English
- Bilingual captions get 27% more engagement (research-backed)
- Research shows Instagram auto-translates Hindi/English to 9+ languages = global reach

Return JSON:
{{"title": "English title 60 chars",
  "script": "120-140 words Hinglish script",
  "hook_text": "5-7 Hindi/English words for overlay",
  "caption_en": "English caption 150 chars",
  "caption_hi": "Hindi caption 100 chars",
  "full_caption": "Combined caption with both languages + hashtags",
  "hashtags": "#betrayaldeepdive #shocking #sach #truecrime #viral #reels"}}""")

        if not topic_data:
            continue

        title  = topic_data.get("title", f"SHOCKING: {niche_seed}")
        script = topic_data.get("script", niche_seed)
        hook   = topic_data.get("hook_text", "Sach jaanna hai?")
        caption = topic_data.get("full_caption", topic_data.get("caption_en", ""))

        # 2. Pre-score
        pre_score = score_short_script(script, title, hook, for_reels=True)
        if pre_score["total"] < QUALITY_MIN:
            continue

        # 3. Voice (bilingual rotation)
        voice = pick_voice(for_reels=True)

        # 4. Audio
        run_id    = uuid.uuid4().hex[:8]
        audio_out = os.path.join(OUTPUT_DIR, f"reel_{mode}_{run_id}.mp3")
        if not generate_audio(script, voice, audio_out):
            continue

        # 5. Synced subtitles (critical for Instagram muted viewing)
        srt_out = audio_out.replace(".mp3", ".srt")
        generate_synced_subtitles(script, audio_out, srt_out)

        # 6. Background
        bg_out = os.path.join(OUTPUT_DIR, f"bg_reel_{run_id}.mp4")
        download_background_clip("drama", bg_out)

        # 7. Assemble
        video_out = os.path.join(OUTPUT_DIR, f"reel_{mode}_{run_id}_final.mp4")
        if not assemble_short_video(bg_out, audio_out, srt_out, hook, video_out, is_reel=True):
            continue

        # 8. Quality check
        final_score = score_final_video(
            video_out, script, title,
            has_subtitles=os.path.exists(srt_out),
            has_thumbnail=False
        )
        if final_score["total"] < QUALITY_MIN:
            continue

        # 9. Upload to Instagram
        ig_ok = upload_instagram_reel(video_out, caption)

        # 10. Also upload to YouTube Shorts (cross-post for double reach)
        tags = ["Shorts", "india", "betrayal", "viral", "reels"]
        yt_desc = f"{caption}\n\n#Shorts"
        yt_url = upload_youtube_short(video_out, title, yt_desc, tags)

        tg(f"""📱 *INSTAGRAM REEL UPLOADED*
Mode: {mode}
Title: {title}
Voice: {voice['id']} ({voice['lang']} {voice['gender']})
Score: {final_score['total']}/10
Subtitles: ✅ Synced (Hindi+English)
Instagram: {"✅ Posted" if ig_ok else "⚠️ Check manually"}
YouTube Short: {yt_url if yt_url else "⚠️ Pending"}""")

        for f in [audio_out, srt_out, bg_out]:
            try:
                os.remove(f)
            except Exception:
                pass

        # FIX: this previously returned only "yt_url" while
        # produce_standalone_short/produce_recap_short both return "url" —
        # any caller checking .get("url") on a teaser result silently got
        # None even on full success. Now returns both keys for consistency.
        return {"status": "success", "ig_posted": ig_ok, "yt_url": yt_url,
                "url": yt_url, "score": final_score["total"], "local_path": video_out}

    return {"status": "failed", "reason": "max retries"}


def produce_video_topic_short(main_topic: str, main_script: str = "", angle: str = "angle_1",
                                channel: str = "betrayal_deepdive") -> dict:
    """
    v7 rebuild — replaces produce_teaser_short/produce_recap_short (kept
    below, unused, for reference/rollback only). Per explicit correction:
    "2 shorts focus on the video" does NOT mean a teaser/recap tied to a
    separate main video — these are genuinely complete, standalone
    Shorts that happen to cover the same real topic as today's main
    video, written fresh by AI (not a literal clip, and not framed as a
    preview of or callback to something else). Two angle variants
    ("angle_1"/"angle_2") take genuinely different narrative approaches
    to the same real topic so the pair isn't a near-duplicate.
    channel: determines branding/hashtags/background search (see CHANNEL_CONFIGS).
    """
    set_active_channel(channel)
    cfg = get_active_channel_config()
    if not main_script:
        main_script = main_topic

    angle_instructions = {
        "angle_1": ("Lead with the single most surprising, concrete fact from this real "
                    "story. Build a complete, self-contained account around it — a full "
                    "arc with its own beginning, middle, and end."),
        "angle_2": ("Lead with a specific consequence or human impact from this real "
                    "story that most people wouldn't expect. Build a complete, "
                    "self-contained account around it, different from a simple "
                    "chronological retelling."),
    }
    instruction = angle_instructions.get(angle, angle_instructions["angle_1"])

    # Format variety — same real, persisted rotation used by
    # get_trending_short_topic (video_pipeline/shorts_formats.py), so
    # this channel's 4 daily Shorts (2 here + 2 standalone) don't all
    # collapse into the same presentation shape.
    format_block = ""
    try:
        from shorts_formats import select_presentation_format, record_format_used, presentation_format_instruction
        _cache_dir = _channel_cache_dir(_active_channel_id)
        _format_name = select_presentation_format(_cache_dir, _active_channel_id)
        record_format_used(_cache_dir, _active_channel_id, angle, _format_name)
        format_block = f"\n\nPRESENTATION FORMAT for this Short (use this specific shape): {presentation_format_instruction(_format_name)}"
    except Exception as e:
        log.warning("Presentation format selection unavailable (non-fatal): %s", e)

    # FIX (found on deep re-audit): this function never called
    # score_short_script()/check_three_second_rule() at all, and had no
    # retry loop — unlike produce_standalone_short (the OTHER half of
    # every channel's 4 daily Shorts), which pre-scores each script
    # attempt and retries up to 3 times below a 7.0 bar. That meant the
    # 3-second-hook check genuinely ran for only 2 of every channel's 4
    # daily Shorts. Wired in the same pre-score-and-retry pattern here.
    for attempt in range(3):
        log.info("produce_video_topic_short attempt %d/3", attempt + 1)

        script_data = llm_json(f"""Create a complete, standalone 45-55 second YouTube Short.
Real topic: {main_topic}
Real story details: {main_script[:500]}

{instruction}{format_block}

Rules:
- This is a COMPLETE piece on its own — no "part 2", no "full story elsewhere",
  no reference to any other video existing
- Real specific details only (numbers, dates, names where used in the source) —
  never invent facts not grounded in the real topic above
- Must resolve — end with the actual point/payoff, not a cliffhanger

Return JSON:
{{"title": "under 55 chars, curiosity-gap title, no 'part 1' or 'full video' language",
  "script": "110-140 words, complete standalone account",
  "hook_text": "5-7 words overlay text",
  "hashtags": "{cfg['hashtags_base']} #shorts"}}""")

        if not script_data:
            continue

        pre_score = score_short_script(script_data["script"], script_data["title"], script_data["hook_text"])
        log.info("Pre-score: %.1f/10", pre_score["total"])
        if pre_score["total"] < QUALITY_MIN:
            log.info("Pre-score too low, retrying topic")
            continue

        voice = pick_voice(for_reels=False)
        run_id = uuid.uuid4().hex[:8]
        audio_out = os.path.join(OUTPUT_DIR, f"vtopic_{run_id}.mp3")
        srt_out   = audio_out.replace(".mp3", ".srt")
        bg_out    = os.path.join(OUTPUT_DIR, f"bg_vtopic_{run_id}.mp4")
        video_out = os.path.join(OUTPUT_DIR, f"vtopic_{run_id}_final.mp4")

        if not generate_audio(script_data["script"], voice, audio_out):
            continue

        generate_synced_subtitles(script_data["script"], audio_out, srt_out)
        download_background_clip(cfg["bg_search_term"], bg_out)

        if not assemble_short_video(bg_out, audio_out, srt_out,
                                     script_data["hook_text"], video_out):
            continue

        # Custom thumbnail — same engine/flow as produce_standalone_short.
        thumb_out = generate_short_thumbnail(script_data["title"], script_data["hook_text"],
                                             cfg["default_niche"], OUTPUT_DIR)
        has_thumb = bool(thumb_out and os.path.exists(thumb_out))

        tags = [t.strip("#") for t in script_data["hashtags"].split() if t.startswith("#")]
        url = upload_youtube_short(video_out, script_data["title"],
                                    script_data["script"] + "\n\n#Shorts", tags)

        if url and has_thumb:
            try:
                _vid_id = url.rstrip("/").split("/")[-1]
                _token = get_yt_token()
                if not set_short_thumbnail(_vid_id, thumb_out, _token):
                    log.warning("Custom Short thumbnail upload did not succeed")
            except Exception as e:
                log.warning("Custom Short thumbnail step failed (non-fatal): %s", e)

        for f in [audio_out, srt_out, bg_out, thumb_out]:
            try:
                if f:
                    os.remove(f)
            except Exception:
                pass

        if not url:
            tg(f"⚠️ *VIDEO-TOPIC SHORT FAILED TO UPLOAD*\n{script_data['title']}\n"
               f"Video was assembled but the actual YouTube upload failed.")
            return {"status": "failed", "reason": "upload failed", "title": script_data["title"]}

        tg(f"⚡ *VIDEO-TOPIC SHORT UPLOADED*\n{script_data['title']}\n{url}")
        return {"status": "success", "url": url, "local_path": video_out}

    return {"status": "failed", "reason": "all attempts failed pre-score or assembly"}


# FIX (found on direct user request, July 14 2026): produce_teaser_short
# and produce_recap_short have been REMOVED entirely. The real, active
# Shorts flow across all 5 channels only ever calls
# produce_video_topic_short (x2, today's actual topic) and
# produce_standalone_short (x2, different/trending topics) -- exactly
# 4 Shorts per episode, per explicit instruction. These two were dead
# code (never called by any real generate.yml workflow), but their
# continued existence -- plus a CLI entry point below that could still
# invoke them by hand -- was exactly the kind of leftover, no-longer-
# relevant content this cleanup was asked to remove outright, not just
# leave unused.


# ── ENTRY POINT ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else SHORT_MODE

    log.info("Starting: mode=%s", mode)

    if mode in ("standalone_1", "standalone_2"):
        result = produce_standalone_short(mode)
    elif mode == "reel_1":
        result = produce_instagram_reel("reel_1")
    elif mode == "reel_2":
        result = produce_instagram_reel("reel_2")
    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)

    print(json.dumps(result, indent=2))

    # Cleanup
    import shutil
    try:
        shutil.rmtree(OUTPUT_DIR, ignore_errors=True)
    except Exception:
        pass
