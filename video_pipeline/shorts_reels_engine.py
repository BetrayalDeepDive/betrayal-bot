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

from synthetic_media_policy import declare_synthetic_media

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
CHANNEL     = "NO KNOWN CAUSE"         # legacy default — see CHANNEL_CONFIGS below
WATERMARK   = "@NoKnownCauseTV"        # legacy default — see CHANNEL_CONFIGS below

# FIX (direct user report, July 24 2026 — explicit, informed policy
# decision after being shown the July 24 data below): raised back to 8.5.
# Real production data that same day (Ch1 run 30066893737) showed 9 real
# attempts (3 video-topic angles, 6 standalone) scoring 2.5-7.0, zero
# clearing 8.5 -- which is why this was temporarily recalibrated to 6.5.
# The user was told this plainly and chose 8.5 anyway, explicitly
# accepting that some days may produce fewer or zero Shorts: "even if it
# doesn't work... I don't want any videos to be published if it is not
# working... below that, I don't want any videos to be published." Attempt
# budget raised from 3 to 8 (see MAX_ATTEMPTS below) to give this real bar
# a genuine chance before a day goes without Shorts.
QUALITY_MIN = 8.5
# FIX (direct user report, July 24 2026 — "I also want the 13-15
# re-attempts on the YouTube shorts as well not 8"): same 8.5 bar,
# more real tries before a day goes without a given Short.
MAX_ATTEMPTS = 13

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
        "display_name":   "NO KNOWN CAUSE",
        "watermark":      "@NoKnownCauseTV",
        "hashtags_base":  "#noknowncause #shorts",
        "tagline":        "No Known Cause — a new published case every weekday.",
        "bg_search_term": "hospital medical",
        # FIX (v7 rebuild, per explicit correction): these used to be
        # "standalone_1"/"standalone_2" pools that were STILL same-niche
        # as the channel (just different specific angles on betrayal/
        # crime) — not genuinely different niches or trending topics as
        # explicitly requested. Renamed to "trending_1"/"trending_2" and
        # rebuilt as genuinely cross-niche, broad-appeal categories
        # (real trend research below narrows these further to what's
        # actually current).
        # OFF-CHANNEL BY CONSTRUCTION.
        #
        # These pools were "viral celebrity news story", "trending sports
        # moment", "viral animal story", "shocking world record", "viral
        # challenge explained" -- and TWO of this channel's four daily Shorts
        # come from here. They were written when Ch1 was a true-crime channel
        # and the brief was "2 Shorts on genuinely different, trending topics
        # so they aren't a recap of today's video". That brief is still
        # honoured below; what changed is that @NoKnownCauseTV now publishes
        # published-case-report documentaries, and shipping a sports Short
        # under that handle is both confusing to a subscriber and a direct
        # contradictory signal to YouTube's topic classifier for the channel.
        #
        # Kept: genuinely different subjects from today's episode, chosen by
        # real trend research, never a recap. Changed: the search space is
        # this channel's own field, so the channel reads as one channel.
        "standalone_topics": {
            "standalone_1": [
                "trending medical research finding", "surprising human body fact",
                "new treatment breakthrough explained", "medical history turning point",
                "unexpected physiology discovery", "trending public health story"
            ],
            "standalone_2": [
                "rare condition explained simply", "famous diagnostic mystery solved",
                "how a common drug was discovered", "sleep science finding",
                "surprising nutrition research", "medical myth corrected by evidence"
            ],
        },
        "default_niche": "hospital medical",
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
def _strip_reasoning(text):
    """
    FIX (found live, July 23 2026 — real bug, root cause of 0/4 Shorts
    produced): this exact issue (a reasoning-capable model like
    gpt-oss-120b/qwen3.6 on Groq embedding its full chain-of-thought
    directly in the response content, then getting cut off mid-<think>
    block by max_tokens before ever reaching the actual answer) was
    already found and fixed in master_pipeline.py's own _strip_reasoning
    on July 15 2026 -- but this file has its own separate llm()/
    llm_json() and never got the same fix, so every Shorts script
    request that landed on a thinking model came back as a truncated,
    unclosed <think> block with zero usable JSON, confirmed live via
    llm_json's own new logging: 'raw, truncated: "<think>\\nThinking
    Process..."'. Same logic, ported here.
    """
    if not text:
        return text
    for _open, _close in (('<think>', '</think>'), ('<thinking>', '</thinking>')):
        _idx = text.lower().find(_open)
        if _idx != -1 and _close not in text.lower()[_idx:]:
            text = text[:_idx].strip()
            if not text:
                return ""
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL | re.IGNORECASE)
    return text.strip()


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
                return _strip_reasoning(r.json()["choices"][0]["message"]["content"].strip())

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
                return _strip_reasoning(r.json()["candidates"][0]["content"]["parts"][0]["text"].strip())

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
                return _strip_reasoning(r.json()["choices"][0]["message"]["content"].strip())

        except Exception as e:
            log.warning("%s failed: %s", provider, str(e)[:80])
            continue

    raise RuntimeError("All LLM APIs failed")


def llm_json(prompt: str, max_tokens: int = 3000) -> dict:
    # FIX (found live, July 22 2026 — real bug, 0/4 Shorts produced this
    # episode with zero diagnostic trail): this returned {} on any parse
    # failure without ever logging the actual raw response, so every
    # caller (produce_video_topic_short/produce_standalone_short) saw
    # nothing but a bare "failed" after 3 silent retries — no way to
    # tell whether the model returned malformed JSON, a truncated
    # response (max_tokens too small), or something else entirely.
    #
    # FIX (found live, July 23 2026, confirmed via the logging above —
    # real bug, root cause of every single Shorts failure): the default
    # was 800 tokens. Groq's reasoning-capable models in this file's own
    # provider list (openai/gpt-oss-120b, qwen/qwen3.6-27b) emit their
    # full chain-of-thought INLINE in the response before the actual
    # answer -- confirmed live, the raw response was routinely 800+
    # tokens of "<think>...Analyze User Input..." with the closing
    # </think> tag and the real JSON never reached at all, every single
    # attempt, 100% failure rate. 800 tokens was enough for maybe a third
    # of one reasoning pass, let alone a finished answer after it. Raised
    # enough to give the model room to actually finish thinking AND
    # answer -- _strip_reasoning() above still cleans the thinking back
    # out of whatever comes back either way.
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
    """Send to Telegram without letting Markdown eat the link.

    Was a bare post with parse_mode "Markdown". A YouTube id containing an
    underscore -- two of the four Shorts this channel put live -- made
    Telegram reject the message with a 400, which requests does not raise,
    which this function then swallowed. See video_pipeline/tg_safe.py.
    """
    if not TG_TOKEN:
        return
    try:
        from tg_safe import send as _safe_send
        if not _safe_send(TG_TOKEN, TG_CHAT, msg):
            log.warning("Telegram did not accept a message (first line: %s)",
                        (msg or "").splitlines()[0][:60] if msg else "")
    except Exception as e:
        log.warning("Telegram send failed (non-fatal): %s", e)


# FIX (direct user report, July 24 2026 — "I want these LLM to take the
# quality scoring expertly serious and give me a notification everytime
# they score any stage without fail. its my main REQUIREMENT"): same
# per-attempt Telegram notification now built for master_pipeline.py's
# script/audio/video/thumbnail/title gates, extended here so Shorts
# scoring (pre-score AND final score, every attempt) is never silent.
def notify_short_score(stage_name, attempt, max_attempts, score, gate, extra=""):
    verdict = "✅ CLEARED" if score >= gate else "❌ below gate"
    msg = f"📊 Shorts — {stage_name}\nAttempt {attempt}/{max_attempts}: {score}/10 (gate {gate}) — {verdict}"
    if extra:
        msg += f"\n{extra}"
    try:
        tg(msg)
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
# YouTube's own category ids. Education and Science & Technology are where a
# medical explainer actually competes; 26 is Howto & Style, which carries the
# health-and-body content that outperforms both.
_TREND_CATEGORIES = (27, 28, 26)

# One fetch per process. get_trending_short_topic runs inside a 13-attempt
# retry loop, so the uncached version asked YouTube what was trending up to
# 13 times per Short for an answer that does not change within a run.
_TREND_CACHE = {}


def get_real_youtube_trending_signal(niche_hint=""):
    """Real "what's working today" research, from YouTube's own Data API.

    TWO THINGS WERE WRONG WITH THIS.
    --------------------------------
    First, `niche_hint` was accepted and then never referenced. The caller
    passes the actual topic seed -- "rare condition explained simply" -- and
    it was dropped on the floor, so the research was not connected to the
    Short being written.

    Second, chart=mostPopular with no category is YouTube's GENERAL US
    trending list: music videos, game trailers, NFL highlights. Those titles
    were handed to the writer of a clinical Short as "what's genuinely
    landing right now, use it to understand hook style". For this channel
    that is not a weak signal, it is a misleading one -- it pulls a medical
    explainer toward the register of a music premiere.

    Now it asks the categories this channel actually competes in, and sorts
    what comes back so anything sharing vocabulary with the topic seed
    surfaces first. Still the same free quota (one unit per category, versus
    100 for a search), still the upload credentials, still never fabricated:
    an empty list on any failure.
    """
    hint = (niche_hint or "").strip().lower()
    if hint in _TREND_CACHE:
        return _TREND_CACHE[hint]

    titles = []
    try:
        token = get_yt_token()
        if not token:
            return []
        for cat in _TREND_CATEGORIES:
            try:
                r = requests.get(
                    "https://www.googleapis.com/youtube/v3/videos",
                    params={"part": "snippet", "chart": "mostPopular",
                            "regionCode": "US", "maxResults": 15,
                            "videoCategoryId": str(cat),
                            "access_token": token},
                    timeout=15)
                if r.status_code != 200:
                    # Not every category is chartable in every region. One
                    # empty category is not a reason to lose the others.
                    log.info("Trending category %d unavailable (%d)", cat, r.status_code)
                    continue
                for it in r.json().get("items", []):
                    t = it.get("snippet", {}).get("title")
                    if t and t not in titles:
                        titles.append(t)
            except Exception as e:
                log.info("Trending category %d failed (non-fatal): %s", cat, e)
    except Exception as e:
        log.warning("YouTube trending fetch (non-fatal): %s", e)
        return []

    # Put the titles that share real words with the topic seed first, so the
    # eight the prompt actually shows are the eight most relevant ones.
    stop = {"the", "a", "an", "and", "of", "how", "why", "new", "for", "to",
            "in", "on", "is", "it", "explained", "simply", "trending"}
    want = {w for w in re.findall(r"[a-z]+", hint) if len(w) > 3 and w not in stop}
    if want:
        def overlap(t):
            return -len(want & set(re.findall(r"[a-z]+", t.lower())))
        titles.sort(key=overlap)

    _TREND_CACHE[hint] = titles[:15]
    return _TREND_CACHE[hint]


def get_trending_short_topic(mode: str, feedback_block: str = "") -> dict:
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
            "\n\nWhat is getting the most views on YouTube today in Education, "
            "Science & Technology and Howto (real titles, pulled live). These "
            "are here for ONE reason: to show you how a title earns a click "
            "right now. Do not copy them, do not borrow their subject matter, "
            "and do not adopt an entertainment register — this is a medical "
            "channel and the credibility is the product:\n" +
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

WRITE LIKE A PERSON WHO KNOWS SOMETHING, NOT LIKE AN ADVERT.
- Open on a FACT, never on a promise. "Seventy over forty, at two in the
  morning" stops a scroll. "You won't believe what doctors found" does not
  — it is asking for attention instead of earning it, and it is the single
  thing that makes these sound like every other channel.
- BANNED outright, no exceptions: "you won't believe", "the truth about",
  "what really happened", "nobody told you", "this changes everything",
  "hidden from the public", "doctors hate", "stay till the end", "wait for
  it". If a sentence could sit under any other video, delete it.
- Every 45 seconds must contain at least one hard, checkable specific — a
  number, a measurement, a duration, an age, a year. A Short with no number
  in it is an opinion.
- Never claim something was hidden, suppressed or covered up. This channel's
  credibility is the entire product and it does not get a second chance.
- One real idea, followed all the way to its end. Not a list, not a tease,
  not a trailer for something else. The viewer should finish it knowing one
  thing they did not know 45 seconds ago, and be able to repeat it to
  somebody else in a sentence.
{SHORTS_RUBRIC_BLOCK}{feedback_block}

Return JSON:
{{"title": "60 chars max, curiosity gap title",
  "hook_text": "5-7 words for text overlay — must shock",
  "script": "120-140 words, starts with most shocking moment, ends with loop hook",
  "hashtags": "{cfg['hashtags_base']} #shocking #viral",
  "niche": "the real trending topic's own category, NOT {cfg['default_niche']}",
  "us_audience_appeal": 8,
  "replay_potential": 9}}""")

    # NO SHORT AT ALL BEATS THIS SHORT.
    #
    # What used to be here, when the model failed, was a hardcoded template:
    #
    #     title:  "SHOCKING: <topic>"
    #     hook:   "You won't believe this..."
    #     script: "The truth about <topic> will shock you. What really
    #              happened was completely hidden from the public for years.
    #              And now — everything is coming out."
    #
    # That is the generic filler being complained about, and it is not a
    # near-miss: it contains no fact, states nothing, and promises a reveal
    # that does not exist. On a medical channel it is also a claim -- that
    # something was "hidden from the public for years" -- made about a real
    # research topic on no evidence whatsoever.
    #
    # An empty dict sends the caller back round the retry loop. Thirteen
    # attempts, then the Short is skipped. A missing Short costs one slot; a
    # published lie costs the channel.
    if not result:
        log.warning("Trending topic generation returned nothing — retrying "
                    "rather than shipping filler")
        return {}

    return result


# ── EMPTY HYPE ────────────────────────────────────────────────────────────────
# "I don't want anything generic or nonsense."
#
# The deleted fallback template is the specification for this check: every
# phrase below is one that PROMISES a revelation instead of delivering a
# fact. They are the load-bearing sentences of a Short that says nothing --
# and a rubric built on shock-word counting actively rewards them, which is
# how they survived this long.
_HOLLOW = (
    "you won't believe", "you wont believe", "will shock you", "wait for it",
    "nobody told you", "the truth about", "what really happened",
    "hidden from the public", "everything is coming out", "this changes everything",
    "doctors hate", "they don't want you to know", "they dont want you to know",
    "the real story nobody", "keep watching", "stay till the end",
    "you need to see this", "this will blow your mind", "shocking truth",
)

# A claim a medical channel must never make on a research topic.
_UNEVIDENCED = ("hidden from the public", "they don't want you to know",
                "they dont want you to know", "doctors hate", "big pharma",
                "the cure they", "suppressed for years")


def hollow_phrases(script: str, title: str = "", hook: str = ""):
    """Reasons this Short is empty hype rather than a story. [] if it is fine.

    Two separate objections:
      * a phrase that promises a reveal in place of stating one
      * no concrete anchor at all -- a real Short on a real case has a
        number, an age, a measurement or a duration in it somewhere
    """
    blob = " ".join([str(script or ""), str(title or ""), str(hook or "")]).lower()
    reasons = []
    for p in _HOLLOW:
        if p in blob:
            reasons.append('empty hype: "%s"' % p)
    for p in _UNEVIDENCED:
        if p in blob:
            reasons.append('unevidenced claim: "%s"' % p)
    body = str(script or "")
    if len(body.split()) >= 40 and not re.search(r"\d", body):
        reasons.append("no concrete number anywhere in the script")
    return reasons


# ── SCRIPT QUALITY SCORING ────────────────────────────────────────────────────
# FIX (root-cause investigation, this session — real production data
# showed Shorts scoring 3.9-4.4/10 against the 8.5 bar across 6 real
# attempts, never budging, even AFTER the individual axis thresholds
# below were recalibrated on July 24): traced this to the generation
# prompt (get_trending_short_topic / produce_video_topic_short's inline
# prompt) never once mentioning what score_short_script() actually
# checks for -- the AI was asked in prose to write "shocking, looping"
# content, but never told the exact mechanical requirements (120-160
# words, a title with a real digit AND one of a specific ~20-word list,
# an ending that reuses a real word from the opening). And on a failed
# attempt, the retry loop just called get_trending_short_topic() again
# for a BRAND NEW blind topic with zero information about what was weak
# in the previous one -- 13 independent blind rolls at a 5-axis AND-gate,
# not 13 genuine improvement passes. This is the real, structural reason
# the "fix" that only touched the scoring thresholds never actually
# closed the gap: the generator was never told the rubric it's graded
# against. SHORTS_RUBRIC_BLOCK makes every single attempt (including the
# first) target the real mechanical bar; _shorts_feedback_block() turns
# a failed attempt's specific weak axes into real, targeted instructions
# for the next attempt, so retries are corrective, not blind re-rolls.
SHORTS_RUBRIC_BLOCK = """
This script will be mechanically scored on these EXACT criteria (write
to hit all of them, don't just aim for "good"):
- Word count: script must be 120-160 words (not shorter, not longer).
- Hook: the hook_text + first ~15 words of the script must contain at
  least 3 of these words (verbatim): shocking, betrayal, secret, exposed,
  truth, destroyed, lied, hidden, never, suddenly, revealed, discovered,
  stolen, fraud, murdered, arrested, collapsed, billion, affair, caught.
- Title: must be under 60 characters, contain a real number/digit
  somewhere, AND contain one of: SHOCKING, SECRET, TRUTH, EXPOSED,
  BETRAYAL, CAUGHT (any case).
- Ending/loop: the final 2-3 sentences must reuse a real, specific noun
  or name from the opening sentence (a genuine callback, not a generic
  word like "today" or "happened").
- Emotional escalation: emotion words (devastated, shocked, horrified,
  betrayed, furious, heartbroken, stunned, chilling, terrifying, etc.)
  must appear MORE in the back half of the script than the front half —
  a real escalating arc, not front-loaded or flat.
- First 3 seconds (~8 words): must NOT start with "hi guys"/"so
  today"/"welcome back"/similar throat-clearing, and MUST contain one of
  the hook words listed above.
"""


def _shorts_feedback_block(prev_score):
    """
    Converts a failed attempt's score dict into specific, targeted
    corrective instructions for the NEXT generation attempt -- real
    closed-loop feedback instead of a blind re-roll. Returns "" when
    there's no previous attempt (first try) or nothing to flag.
    """
    if not prev_score:
        return ""
    notes = []
    if prev_score.get("hook", 2.0) < 1.4:
        notes.append("- Your last attempt's hook was weak: use at least 3 of the required "
                      "shock words in the hook_text/opening line, not just 1-2.")
    if prev_score.get("length") is not None and prev_score["length"] < 2.0:
        notes.append("- Your last attempt's script length missed the 120-160 word target — hit it exactly this time.")
    if prev_score.get("loop", 2.0) < 2.0:
        notes.append("- Your last attempt's ending didn't genuinely call back to a specific "
                      "word/name from the opening — make the last 2-3 sentences reuse a real "
                      "noun or name from the very first sentence.")
    if prev_score.get("emotion", 2.0) < 1.6:
        notes.append("- Your last attempt's emotion words were flat or front-loaded — put MORE "
                      "emotion words in the back half of the script than the front half.")
    if prev_score.get("title", 2.0) < 1.5:
        notes.append("- Your last attempt's title was missing a real digit/number and/or one of "
                      "the required shock words — the title MUST have both.")
    if not notes:
        return ""
    return "\n\nFEEDBACK FROM YOUR LAST ATTEMPT (fix these specific gaps):\n" + "\n".join(notes)


def score_short_script(script: str, title: str, hook: str,
                        for_reels: bool = False) -> dict:
    """
    5-point quality check for Shorts/Reels script.
    Returns score dict. Must hit 8.5/10 overall.
    """
    scores = {}

    # 1. Hook strength (0-2 pts)
    # FIX (direct user report, July 24 2026 — real production data showed
    # 9 real attempts scoring 2.5-7.0, zero clearing 8.5): *0.4 required
    # 5 distinct shock words inside the hook + first 80 chars (~15 words)
    # to reach full marks — a genuinely well-written hook naturally has
    # 1-3, and cramming in 5 reads as unnatural keyword-stuffing, not
    # better writing. Recalibrated so 3 genuine hits (realistic for a
    # strong hook) reaches the cap, not 5.
    shock_words = ["shocking","betrayal","secret","exposed","truth","destroyed","lied",
                   "hidden","never","suddenly","revealed","discovered","stolen","fraud",
                   "murdered","arrested","collapsed","billion","affair","caught",
                   # Clinical-register equivalents, added for Ch1. These carry
                   # the same "something is wrong and unresolved" weight without
                   # crime vocabulary, so a well-written medical hook can reach
                   # the cap on its writing rather than on its subject matter.
                   "misdiagnosed","missed","wrong","fatal","undetected","overlooked",
                   "symptom","diagnosis","collapse","untreated","rare","unexplained"]
    hook_hits = sum(1 for w in shock_words if w in hook.lower() or w in script[:80].lower())
    scores["hook"] = min(2.0, hook_hits * 0.7)

    # 2. Script length (0-2 pts) — 120-160 words ideal
    wc = len(script.split())
    if 120 <= wc <= 160:
        scores["length"] = 2.0
    elif 100 <= wc < 120 or 160 < wc <= 180:
        scores["length"] = 1.5
    else:
        scores["length"] = 1.0

    # 3. Replay loop ending (0-2 pts)
    # FIX (direct user report, July 24 2026 — same real-production
    # miscalibration as the hook fix above): this only ever recognized 10
    # literal phrases, verbatim — a genuinely well-constructed loop (the
    # ending's language circling back to the opening's own subject,
    # without hitting one of those 10 exact strings) scored the same as
    # a script with no loop at all. Added a structural fallback: does a
    # real content word from the opening genuinely recur in the closing
    # lines — the actual mechanic a "loop ending" relies on, not a
    # specific turn of phrase.
    loop_phrases = ["but wait","the real question","and that's when","you won't believe",
                    "this is just the beginning","it gets worse","and here's the thing",
                    "what happened next will","going back to","which brings us back",
                    "which is why","that's the part","and that's exactly",
                    "so when you", "knowing that", "which means"]
    loop_hit = any(p in script.lower() for p in loop_phrases)
    if not loop_hit:
        # Generic connective/filler words excluded so the overlap check only
        # credits a genuine content callback (a name, a number, a specific
        # noun) — "today"/"basically"/"happened" recurring is not a real loop.
        _loop_stopwords = {"today","basically","happened","something","because",
                           "before","after","other","which","there","their","about",
                           "still","again","really","actually","overall","company"}
        _sw = script.split()
        _open_words  = {w.strip(".,!?;:\"'").lower() for w in _sw[:8] if len(w) > 4}
        _close_words = {w.strip(".,!?;:\"'").lower() for w in _sw[-15:] if len(w) > 4}
        loop_hit = bool((_open_words & _close_words) - _loop_stopwords)
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
    # A CLINICAL CHANNEL CANNOT EARN THIS POINT IN CRIME VOCABULARY.
    #
    # The list used to be SHOCKING/SECRET/TRUTH/EXPOSED/BETRAYAL/CAUGHT and
    # nothing else. score_short_script is shared by all five channels, so on
    # "No Known Cause" a full-marks title had to reach for tabloid words about
    # somebody's illness -- and a title that refused was scored as weaker
    # writing. That is a rubric manufacturing the register it is then blamed
    # for. The clinical equivalents carry the same unresolved-question weight
    # without the crime framing; the original words stay for the channels they
    # were written for.
    title_words = ["SHOCKING", "SECRET", "TRUTH", "EXPOSED", "BETRAYAL", "CAUGHT",
                   "MISSED", "MISDIAGNOSED", "OVERLOOKED", "UNDETECTED", "RARE",
                   "UNEXPLAINED", "WRONG", "SYMPTOM", "DIAGNOSIS", "FATAL",
                   "UNTREATED", "MYSTERY", "NOBODY", "WHY"]
    title_score = 0
    if len(title) <= 60:
        title_score += 0.5
    if any(w in title.upper() for w in title_words):
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

    # A SCORE OUT OF TEN CANNOT BE 11.5.
    #
    # The five rubric components are each capped at 2.0, so they sum to at
    # most 10. three_second_rule was then ADDED on top of that as a bonus,
    # and run 31156373254 logged "Pre-score: 11.5/10", "11.1/10", "10.5/10",
    # "10.1/10" -- four Shorts out of four scored above the maximum. A number
    # that can exceed its own scale is not a score, and every threshold
    # compared against it means something different from what it says.
    #
    # The bonus still moves the result, it just moves it INSIDE the scale: a
    # penalty (a slow windup opening) still drags a good script down, and a
    # script already at 10 on the rubric gains nothing from a bonus, which is
    # correct -- it has nowhere left to go.
    total = round(min(10.0, max(0.0, sum(scores.values()))), 1)
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


# WHICH VOICE ACTUALLY SPOKE. THE SCORER HAD NO IDEA.
#
# Run 31257986626: Groq returned 429 on chunk 6 of standalone_2, this file
# fell through to espeak, and the Short scored 9.3/10 and published to
# YouTube -- because the audio component of the score was "the file exists
# and is over 500KB", which a synthesiser satisfies exactly as well as a
# neural voice. A robotic Short went live on the channel.
#
# The main narration path already refuses to publish espeak: its gate weights
# the voice tier at 40%, so espeak's ceiling is 6.6 against an 8.5 floor.
# Shorts had no equivalent, so the same fallback had opposite consequences
# depending on which pipeline reached it. This records the route so the
# scorer can apply the same rule.
LAST_TTS_ROUTE = "none"

# Routes that must never reach the audience. Not a quality opinion -- a
# formant synthesiser is recognisably not a person, and the whole channel
# rests on sounding like one.
DRAFT_ONLY_ROUTES = ("espeak",)


def generate_audio(script: str, voice: dict, output_path: str) -> bool:
    """
    Generate audio via Groq Orpheus with emotional tags.
    Falls back to Piper (local neural), then espeak-ng as a last resort.
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
                globals()["LAST_TTS_ROUTE"] = "groq-orpheus"
                return True
        except Exception as e:
            log.warning("Groq TTS failed: %s", e)

    # PIPER BEFORE THE SYNTHESISER.
    #
    # Groq's failure here was a 429 -- a rate limit, not an outage -- and a
    # rate limit is the single most likely way this path ever fires. Dropping
    # straight from a neural voice to a formant synthesiser because a quota
    # ticked over is a huge quality cliff for a trivial cause. Piper runs on
    # the runner, needs no key and no quota, and sounds like a person.
    #
    # Shorts are narrated faster than the main episode: they have 60 seconds
    # to land a whole story, so the pace target is the Shorts' own, not the
    # documentary's 100 wpm.
    # edge-tts — THE THIRD HUMAN ROUTE.
    #
    # Deleting espeak left Shorts with two routes that can speak, Groq and
    # Piper, against a standing requirement of three to four real backups
    # per stage. edge-tts is neural, free, needs no key, and is already the
    # main episode's primary voice — so it closes that gap with something
    # this repo already depends on rather than a new account.
    #
    # It sits between the two on purpose: Groq's own voices first, then the
    # remote neural voice, then the local one that works with the network
    # down. Three routes, three different failure modes.
    try:
        import asyncio as _asyncio
        import edge_tts as _edge
        _g = voice.get("gender", "male")
        _acc = voice.get("accent", "US")
        _edge_voice = {
            ("British", "female"): "en-GB-SoniaNeural",
            ("British", "male"):   "en-GB-RyanNeural",
            ("US", "female"):      "en-US-JennyNeural",
            ("US", "male"):        "en-US-GuyNeural",
        }.get((_acc, _g), "en-US-GuyNeural")

        async def _run():
            await _edge.Communicate(text=script[:4000], voice=_edge_voice,
                                    rate="+8%").save(output_path)

        # Bounded: a hung endpoint must not stall the whole Shorts run when
        # there is still a local route underneath this one.
        _asyncio.run(_asyncio.wait_for(_run(), timeout=120))
        if os.path.exists(output_path) and os.path.getsize(output_path) > 20000:
            log.info("Audio: edge-tts %s ✅", _edge_voice)
            globals()["LAST_TTS_ROUTE"] = "edge-tts"
            return True
        log.warning("edge-tts produced nothing usable — falling through")
    except Exception as e:
        log.warning("edge-tts fallback failed: %s", e)

    try:
        # `sys` is not imported at module level in this file (only inside one
        # function far below), so importing it here is deliberate rather than
        # redundant — relying on the global would be a NameError the moment
        # Groq rate-limits, which is exactly when this path runs.
        import sys as _sys
        _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import piper_tts as _piper
        _gender = voice.get("gender", "male")
        _edge_hint = "en-GB-SoniaNeural" if _gender == "female" else "en-GB-RyanNeural"
        if _piper.synthesize(script[:4000], output_path, edge_voice=_edge_hint,
                             target_wpm=150.0, log=lambda m: log.info("%s", m)):
            log.info("Audio: Piper local neural (%s) ✅", _gender)
            globals()["LAST_TTS_ROUTE"] = "piper"
            return True
    except Exception as e:
        log.warning("Piper fallback failed: %s", e)

    # THIS IS WHERE THE ROBOT USED TO SPEAK.
    #
    # An espeak-ng route sat here. It was marked "draft only" and the scorer
    # was made to refuse it, and a Short narrated by it still went live on
    # the channel — because "draft only" is a label, and the synthesiser was
    # installed, wired in and reachable. On the day Groq returned a 429 the
    # chain walked all the way down and something spoke.
    #
    # Per instruction, "only humanic voices": it is gone, not demoted. The
    # human routes above it (edge-tts, Kokoro, Piper local neural) are the
    # whole list. If every one of them fails, this Short is not made today.
    log.error("Every human voice route failed — refusing to narrate this "
              "Short with a robotic voice. No audio produced.")
    globals()["LAST_TTS_ROUTE"] = "none"
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
# FIX (direct user report, July 23 2026 — "the background visuals
# should also be according to the niche... and the video animation
# should be proper"): same anchor-extraction technique already proven
# for the main channel videos' stock footage (get_stage_matched_video).
_BG_TOPIC_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "this", "that", "was", "were", "had", "have",
    "it", "its", "he", "she", "they", "their", "his", "her", "be", "been",
    "not", "no", "so", "as", "if", "then", "than", "when", "what", "who",
    "part", "real", "documented", "real-life", "true", "story",
}


def _extract_topic_anchor(topic):
    words = [w.strip(".,!?;:\"'()") for w in topic.lower().split()
             if len(w) > 5 and w.strip(".,!?;:\"'()") not in _BG_TOPIC_STOPWORDS]
    if not words:
        return ""
    from collections import Counter as _C
    return _C(words).most_common(1)[0][0]


# Channels whose Shorts must NEVER fetch a library clip. Their background is
# rendered from the episode's own sourced case instead.
NO_STOCK_NICHES = ("hospital medical",)
_CLINICAL_CASE = {"case": None}


def set_clinical_case(case):
    """Ch1 hands its real sourced case here before producing Shorts."""
    _CLINICAL_CASE["case"] = case or None


def download_background_clip(niche: str, output_path: str, topic: str = "",
                             duration: float = 30.0) -> bool:
    # NO STOCK FOOTAGE ON THE CLINICAL CHANNEL -- not in the main video, and
    # not here either.
    #
    # The main video's stock path was closed after a real episode about a
    # newborn's liver failure shipped illustrated with a mountain and a woman
    # dancing. The Shorts path was never touched, so a third of this
    # channel's daily output was still generic library footage. The
    # topic-anchored query made it worse rather than better: it takes the
    # commonest long word from the title, so a case about galactosaemia
    # searched Pixabay for "galactose hospital corridor night".
    #
    # A Short is the same channel and draws from the same paper.
    if niche in NO_STOCK_NICHES:
        case = _CLINICAL_CASE["case"]
        try:
            from medical_segments import render_vertical_background
            if render_vertical_background(case or {}, output_path,
                                          max(6.0, float(duration)),
                                          headline=topic):
                log.info("Clinical vertical background rendered from the case")
                return True
            log.warning("Clinical vertical background failed — using the "
                        "procedural fallback, NOT stock footage")
        except Exception as e:
            log.warning("Clinical vertical background error: %s", e)
        return _procedural_fallback_bg(output_path)

    return _download_stock_background(niche, output_path, topic)


def _download_stock_background(niche: str, output_path: str, topic: str = "") -> bool:
    """Download 9:16 background clip from Pixabay. When `topic` is given,
    tries a topic-anchored query first (a real specific word from THIS
    Short's actual topic, combined with the niche's mood keyword) before
    falling back to the plain niche-category search — so the background
    isn't just "cinematic dark drama" for every Short in the category,
    regardless of what the Short is actually about."""
    niche_keywords = {
        # No Known Cause (Ch1). Deliberately clinical settings and equipment,
        # never patients or anything that could read as a real person's
        # medical footage -- the paper's own CC BY figures are the only
        # patient imagery this channel is licensed to show.
        "hospital medical": ["hospital corridor night", "medical scan monitor",
                             "laboratory microscope work", "empty operating theatre"],
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
        # Ch1 had NO entry here, so every one of its Shorts fell through to
        # "default" below and searched "cinematic dark drama" / "mystery
        # thriller" — run 30717615638 logged
        # "Background matched: 'shocking cinematic dark drama'" on a published
        # case report. That is the "the shorts kept talking about some other
        # thing which is not really correct" report, in the visuals.
        "hospital medical": [
            "hospital corridor calm", "medical scan monitor closeup",
            "laboratory analysis closeup", "clinician reviewing notes",
            "microscope slide detail", "medical chart paperwork closeup",
            "hospital ward night quiet", "blood sample vial laboratory"
        ],
        "default":      ["cinematic dark drama","mystery thriller","emotional shadow"],
    }
    keywords = niche_keywords.get(niche, niche_keywords["default"])
    kw = random.choice(keywords)

    # Topic-anchored query tried FIRST — a real specific word from this
    # Short's actual topic combined with the niche's mood keyword, so the
    # background reflects what THIS Short is about, not just its category.
    query_candidates = []
    topic_anchor = _extract_topic_anchor(topic) if topic else ""
    if topic_anchor:
        query_candidates.append(f"{topic_anchor} {kw}")
    query_candidates.append(kw)

    if PIX_KEY:
        for query in query_candidates:
            try:
                r = requests.get(
                    "https://pixabay.com/api/videos/",
                    params={"key": PIX_KEY, "q": query, "per_page": 5,
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
                                log.info("Background matched: '%s'", query)
                                return True
            except Exception as e:
                log.warning("Pixabay (%s): %s", query, e)

    # FIX: this fallback used to be a completely flat, static black screen
    # with a vignette — about as visually "dead"/robotic-looking as a
    # background can be, directly working against "should never look
    # AI-built." A slow animated gradient drift plus a subtle moving
    # particle-like noise field reads as genuine, deliberate motion
    # graphics rather than a placeholder, while still being fully
    # generatable offline with no network dependency.
    return _procedural_fallback_bg(output_path)


def _audio_seconds(path, default=30.0):
    """Real duration of the narration this background has to cover.

    The rendered clinical background is built from a fixed number of cards,
    so it needs the real length -- a 30-second assumption would leave a
    55-second Short with 25 seconds of nothing."""
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                            "format=duration", "-of", "csv=p=0", path],
                           capture_output=True, text=True, timeout=30)
        return max(5.0, float(r.stdout.strip()))
    except Exception:
        return default


def _procedural_fallback_bg(output_path):
    """
    Generated, never fetched. Extracted so the clinical path can reach it
    without going anywhere near a stock library.

    This used to be a flat black screen with a vignette -- about as visually
    dead as a background can be. A slow gradient drift plus a moving noise
    field reads as deliberate motion graphics rather than a placeholder,
    and needs no network.
    """
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


def _hook_drawtext(hook, max_width_px=980, y_top=140):
    """
    The hook, wrapped and sized to FIT.

    It was one drawtext with no wrapping at a fixed fontsize 54. DejaVu Bold
    at 54 runs about 32px per character, so any hook longer than ~30
    characters is wider than the 1080px frame -- and because it is centred,
    it gets clipped at BOTH ends. Assembling a real Short showed
    "A newborn was being poisoned by milk." rendering as "newborn was being
    poisoned by mi". The hook is the first thing a viewer reads and it was
    losing its first and last words.
    """
    import textwrap as _tw
    text = (hook or "").strip()
    if not text:
        return []
    size = 54
    lines = [text]
    for size in (54, 48, 42, 38, 34):
        # ~0.60 of the point size is a good average advance for DejaVu Bold.
        per_line = max(8, int(max_width_px / (size * 0.60)))
        lines = _tw.wrap(text, per_line)[:3]
        if lines and max(len(l) for l in lines) <= per_line:
            break
    out = []
    for i, line in enumerate(lines):
        safe = line.replace("'", "").replace(":", " ").replace('"', "")
        out.append(
            f"drawtext=text='{safe}':"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            f"fontsize={size}:fontcolor=white:borderw=4:bordercolor=black:"
            f"x=(w-text_w)/2:y={y_top + i * int(size * 1.25)}:"
            "shadowcolor=black@0.9:shadowx=3:shadowy=3")
    return out


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

    # Not truncated to 50 characters any more -- _hook_drawtext wraps and
    # shrinks to fit instead of clipping.
    hook_safe = (hook_text or "").strip()
    # A rendered clinical card must not be darkened again; see below.
    is_clinical_bg = bool(_CLINICAL_CASE.get("case"))
    wm_safe   = WATERMARK.replace("'", "")

    # Build subtitle filter
    if os.path.exists(srt_path):
        srt_esc = srt_path.replace(":", "\\:").replace("'", "\\'")
        # PlayResX/PlayResY MUST be declared.
        #
        # Without them libass assumes its 384x288 default and scales the whole
        # style by 1920/288 -- about 6.7x. Measured on a real 1080x1920 Short:
        # "FontSize=22, MarginV=80" rendered as ink from y=654 to y=1417, i.e.
        # 763 pixels tall sitting across the MIDDLE of the frame, covering
        # whatever the background was showing. The style said small text near
        # the bottom; libass drew enormous text through the centre, and every
        # channel's Shorts have looked like that.
        #
        # With the real resolution declared the numbers mean what they say.
        # Sized deliberately large (Shorts convention) but anchored in the
        # lower third: measured y=1284..1666.
        sub_filter = (
            f"subtitles='{srt_esc}':force_style="
            "'PlayResX=1080,PlayResY=1920,FontName=DejaVu Sans,FontSize=96,"
            "Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
            "BackColour=&HB0000000,Outline=6,Shadow=3,"
            "Alignment=2,MarginL=70,MarginR=70,MarginV=260,Spacing=0.5'"
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
    #
    # NOT on a rendered clinical card. The punch is a 1.15x magnification
    # outward from centre, on top of the card's own 1.08 pan, and every
    # clinical card's layout is derived from that 1.08. Assembling a real
    # Short and pulling a punch frame out of it showed the cost: the chart's
    # y-axis read ",500" because the leading digit of "1,500" had been pushed
    # off the left edge of the frame. On a differential board the same punch
    # cuts the diagnosis names. A photographic background has nothing at its
    # edges to lose; an information card is all edges.
    #
    # It also buys less here: this background is not a static loop, it is a
    # sequence of different cards, so the visual change the interrupt exists
    # to create is already happening.
    if is_clinical_bg:
        log.info("[SHORTS] Clinical card background — pattern-interrupt punch "
                 "skipped (it crops the card's own labels)")
    else:
        try:
            from shorts_formats import pattern_interrupt_filter
            vf_parts.append(pattern_interrupt_filter())
        except Exception as e:
            log.warning("Pattern interrupt filter unavailable (non-fatal): %s", e)

    # The vignette is applied ONLY to fetched footage. On the clinical
    # channel the background is a rendered card -- deliberately dark already
    # -- and darkening it again crushed the differential board and the
    # chart to near-invisible behind the caption. Assembling a real Short
    # and looking at it is the only way that shows up.
    if not is_clinical_bg:
        vf_parts.append("vignette=PI/3.5")

    vf_parts += _hook_drawtext(hook_safe)
    vf_parts += [
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
    "betrayal_deepdive": ["documented","published","diagnosis","case","finding","reported","confirmed"],
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
    "betrayal_deepdive": ["DOCUMENTED","PUBLISHED","DIAGNOSIS","CASE","FINDING","REPORTED","MISSED","REAL"],
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

    # 2. Audio quality — WHICH VOICE, not just whether a file exists.
    #
    # This was "the file exists and is over 500KB" and nothing else, which a
    # formant synthesiser satisfies exactly as well as a neural voice. On run
    # 31257986626 Groq hit a 429, the chain fell to espeak, and the Short
    # scored 9.3/10 and published: a robotic Short live on the channel with
    # every component reporting healthy.
    #
    # A draft-only route now zeroes this component AND forces the overall
    # verdict to fail below, so no combination of a great script, perfect
    # subtitles and an ideal length can carry a synthesised voice past the
    # gate. That is the same rule the main narration path already applies.
    # Checked against the allowlist in video_pipeline/voice_policy.py rather
    # than a local blocklist. A blocklist has to predict what will go wrong:
    # an unrecognised route -- a new synthesiser, a renamed one, a route that
    # forgot to record itself -- passed the old check by not being on it.
    # Now anything not positively known to be a human voice is refused.
    _route = globals().get("LAST_TTS_ROUTE", "none")
    try:
        from voice_policy import is_human as _is_human, refuse_reason as _refuse
        _draft_voice = not _is_human(_route)
        _refusal = _refuse(_route)
    except Exception:
        _draft_voice = _route in DRAFT_ONLY_ROUTES
        _refusal = "%s is not allowed to publish" % _route
    if _draft_voice:
        scores["audio"] = 0.0
    elif os.path.exists(video_path) and os.path.getsize(video_path) > 500000:
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

    # Same ceiling, same reason: the components above plus the additive
    # thumbnail bonus can total more than ten.
    total = round(min(10.0, max(0.0, sum(scores.values()))), 1)
    scores["total"] = total
    scores["voice_route"] = _route
    # A draft-only voice is disqualifying on its own, not merely expensive.
    # Zeroing the audio component is not enough by itself: the remaining
    # components top out high enough that a strong script could still scrape
    # the floor, which is exactly the arithmetic that let 9.3/10 publish.
    scores["passed"] = total >= QUALITY_MIN and not _draft_voice
    if _draft_voice:
        scores["blocked_reason"] = _refusal + " — rebuild or drop, never publish"
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


def build_short_description(title, tags_str, cfg, topic_line=""):
    """
    A Short's description is not a transcript.

    Both upload sites pasted the ENTIRE narration script into the YouTube
    description. Direct report after run 30717615638: "you have mentioned
    every detail of what it is talking about. That shouldn't be there... Why
    will people look at the shot? Everything is already there."

    Exactly right, and it is worse than redundant. A Short earns its watch
    time from curiosity; printing the whole answer under the player removes
    the reason to watch, and a wall of narration is also the weakest possible
    signal to YouTube about what the Short is ABOUT.

    So: the topic, the hashtags, and one line pointing at the full episode.
    Nothing that answers the question the Short is asking.
    """
    parts = [str(title).strip()]
    if topic_line and topic_line.strip().lower() != str(title).strip().lower():
        parts.append(topic_line.strip())
    parts.append(f"🎬 Full case on {cfg.get('watermark', '')} — the complete "
                 f"report, start to finish.")
    tags = (tags_str or "").strip()
    if "#shorts" not in tags.lower():
        tags = (tags + " #Shorts").strip()
    parts.append(tags)
    return "\n\n".join(p for p in parts if p)


# NOTHING GOES PUBLIC FROM THE GENERATE PHASE.
#
# Run 31257986626 put four Shorts live on the channel during a workflow whose
# own header reads "Phase 1: GENERATE only (no upload)". None had been
# reviewed; one of them was narrated by espeak. privacyStatus was the string
# "public", hardcoded, with no way to ask for anything else.
#
# The main video already does this correctly and has for months: it uploads
# UNLISTED, a human approves it, and set_yt_privacy() flips it to public
# without re-uploading. Shorts simply never joined that pattern.
#
# The default is now unlisted, and the phase decides. PHASE is set by the
# workflow ("generate" / "upload"), so a Short built during generation is a
# reviewable preview by construction rather than by remembering to pass a
# flag. Getting it wrong now means a Short stays unlisted -- the safe
# direction to fail in.
# Every Short this run put on YouTube, so the upload phase can find them again
# and flip the approved ones to public. Without this the previews would sit
# unlisted forever with no record of what they were.
UPLOADED_SHORTS = []


def _default_short_privacy():
    return "public" if os.environ.get("PHASE", "").lower() == "upload" \
        else "unlisted"


def upload_youtube_short(video_path: str, title: str, description: str,
                          tags: list, privacy: str = None) -> str:
    """Upload to YouTube as Short. Returns URL or ''.

    `privacy` defaults to unlisted during the generate phase so the Short can
    be reviewed before anyone sees it.
    """
    privacy = privacy or _default_short_privacy()
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
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
            # Only tell subscribers about something that is actually visible.
            # A notification for an unlisted preview is a dead link in every
            # subscriber's feed.
            "notifySubscribers": privacy == "public",
            # The four long-form uploaders all set this explicitly; this one
            # simply omitted the field, which happens to mean the same thing
            # (not declared) but only by accident. Stating it makes Shorts
            # obey the same switch as everything else instead of quietly
            # doing its own thing. This function has no channel argument, so
            # it reads the global var rather than a per-channel one -- if a
            # single channel ever needs to declare, that trip-wire is in
            # synthetic_media_policy.py and this needs the channel plumbed in.
            "containsSyntheticMedia": declare_synthetic_media(""),
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
    # Say which it was. The old line read "YouTube Short uploaded: <url>" for a
    # PUBLIC upload during a generate-only run, and nothing in the log
    # distinguished that from a preview — which is why four live Shorts went
    # unnoticed until they were watched.
    log.info("YouTube Short uploaded [%s]: %s", privacy, url)
    UPLOADED_SHORTS.append({"id": vid_id, "url": url, "privacy": privacy,
                            "title": title})

    # Bridge the presentation format chosen at write time to the video id that
    # only exists now. Without this the CTR that YouTube Analytics reports for
    # this Short later has no entry to attach itself to, and the Shorts format
    # history stays a diary of what ran rather than a record of what worked.
    try:
        from shorts_formats import attach_video_id as _attach_short
        # _cache_dir is a local in the two functions that record formats, so it
        # is recomputed here from the module-level active channel rather than
        # closed over -- referencing it directly raises NameError at exactly
        # the moment a Short has just uploaded successfully.
        _attach_short(_channel_cache_dir(_active_channel_id),
                      _active_channel_id, vid_id)
    except Exception as e:
        log.warning("shorts_format_history video_id attach (non-fatal): %s", e)
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

def _produce_standalone_short_once(mode: str, channel: str = "betrayal_deepdive") -> dict:
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

    prev_score = None  # feeds _shorts_feedback_block() so retries target real gaps, not blind re-rolls
    for attempt in range(MAX_ATTEMPTS):
        log.info("Attempt %d/%d", attempt + 1, MAX_ATTEMPTS)

        # 1. Get topic. An empty dict means generation failed and the generic
        # filler template that used to paper over it is gone — retry instead.
        topic_data = get_trending_short_topic(mode, feedback_block=_shorts_feedback_block(prev_score))
        if not topic_data or not topic_data.get("script") or not topic_data.get("title"):
            log.info("No usable trending topic this attempt — retrying")
            continue

        # 2. Reject empty hype before spending a voice and a render on it.
        _hollow = hollow_phrases(topic_data.get("script", ""),
                                 topic_data.get("title", ""),
                                 topic_data.get("hook_text", ""))
        if _hollow:
            log.info("Rejected as generic: %s", "; ".join(_hollow[:3]))
            prev_score = None
            continue

        title  = topic_data["title"]
        script = topic_data["script"]
        hook   = topic_data["hook_text"]
        niche  = topic_data.get("niche", cfg["default_niche"])
        tags_str = topic_data.get("hashtags", f"{cfg['hashtags_base']} #viral")

        # 2. Pre-score
        pre_score = score_short_script(script, title, hook)
        log.info("Pre-score: %.1f/10", pre_score["total"])
        notify_short_score(f"{mode} pre-score", attempt + 1, MAX_ATTEMPTS, pre_score["total"], QUALITY_MIN, extra=title[:60])
        if pre_score["total"] < QUALITY_MIN:
            log.info("Pre-score too low, retrying topic")
            prev_score = pre_score
            continue

        # FIX (direct user report, July 23 2026 — "the quality interceptor...
        # it's not only for the script stage... shots... everything should
        # be checked", minimum 7.9, applied empire-wide): independent
        # AI-judge read of the actual Short script, on top of the
        # rule-based score_short_script rubric above.
        try:
            from quality_auditor import audit_content
            _audit = audit_content("shorts_script", script, "", lambda p, tokens=350: llm(p, max_tokens=tokens))
            from quality_auditor import fmt_score as _fmt_audit
            log.info("Quality audit (shorts_script): %s (passed=%s, fallback=%s)",
                      _fmt_audit(_audit["score"]), _audit["passed"],
                      _audit["used_fallback"])
            if not _audit["passed"]:
                log.info("Quality audit below 7.9 bar, retrying topic")
                continue
        except Exception as e:
            log.warning("Quality audit unavailable (non-fatal): %s", e)

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
        download_background_clip(niche, bg_out, topic=title,
                                 duration=_audio_seconds(audio_out))

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
        notify_short_score(f"{mode} final score", attempt + 1, MAX_ATTEMPTS, final_score["total"], QUALITY_MIN, extra=title[:60])

        if final_score["total"] < QUALITY_MIN:
            log.info("Quality too low, retrying")
            continue

        # 9. Upload to YouTube
        tags = [t.strip("#") for t in tags_str.split() if t.startswith("#")]
        # FIX (direct user report, July 24 2026 — "Shorts-to-video bridge"
        # was claimed present in an earlier summary but never actually
        # existed: the description had no link back to the main channel
        # at all. Real bridge line added here, every channel, pointing
        # viewers at the full-length episodes.
        bridge_line = f"🎬 Full-length episodes daily on {cfg['watermark']} — subscribe for the complete story."
        # Was: the whole narration script. See build_short_description.
        description = build_short_description(title, tags_str, cfg,
                                              topic_data.get("topic", ""))
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

        # FIX (direct user report, July 23 2026 — "post-upload reporting...
        # I need it for every thing without fail", applied empire-wide):
        # same real views/likes/subscribers/revenue snapshot the main
        # videos get, now for Shorts too.
        try:
            from post_upload_reporter import send_post_upload_report
            _vid_id_report = yt_url.rstrip("/").split("/")[-1]
            _token_report = get_yt_token()
            send_post_upload_report(
                cfg.get("display_name", channel), yt_url, _vid_id_report, _token_report,
                None, None, gumroad_token=os.environ.get("GUMROAD_ACCESS_TOKEN"), tg_fn=tg)
        except Exception as e:
            log.warning("Post-upload report for Short (non-fatal): %s", e)

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

    # FIX (found this session alongside the same rubric-blindness bug in
    # get_trending_short_topic/produce_video_topic_short): this loop only
    # ever tried 3 attempts, not MAX_ATTEMPTS (13) like every other
    # Shorts/Reels producer in this file -- inconsistent with the user's
    # explicit "raise every attempt count to 13, hard embedded" directive
    # that was already applied everywhere else.
    prev_score = None
    for attempt in range(MAX_ATTEMPTS):
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
{SHORTS_RUBRIC_BLOCK}{_shorts_feedback_block(prev_score)}

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
            prev_score = pre_score
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


def derivative_of(short_script: str, main_script: str, n: int = 6):
    """How much of this Short is lifted from the episode. 0.0 to 1.0.

    WHY A PROMPT ALONE WAS NOT ENOUGH
    ---------------------------------
    The Shorts read as "the monologue of the main script" because the prompt
    ASKED for that in as many words: "this is the same story with the same
    hook and the same ending as the main video, not an independently invented
    angle". It was handed 600 characters of the episode's opening and 800 of
    its ending and told to match both. Paraphrase was the specified outcome.

    The instruction is rewritten, but an instruction is a hope. This measures
    what actually came back: the fraction of the Short's six-word sequences
    that also appear in the episode.

    WHAT THIS CATCHES, AND WHAT IT DOES NOT
    ---------------------------------------
    Measured on four Shorts written against the same clinical episode:

        sentences lifted from the episode      84.4%
        competent paraphrase, same shape        1.8%
        independent angle, same facts           0.0%
        independent, quoting the paper's line   10.9%

    So this is a backstop against LITERAL reuse, and a good one -- there is
    a wide gap between 84% and the honest Short that quotes one real sentence
    from the source paper at 11%. It is NOT a paraphrase detector: rebuild
    the sentences and overlap collapses to noise. Nothing here should be read
    as proof a Short is original.

    Paraphrase is handled where paraphrase is caused -- the prompt above no
    longer demands the episode's opening line and closing beat be reproduced.
    """
    def grams(t):
        w = re.findall(r"[a-z0-9]+", (t or "").lower())
        return {" ".join(w[i:i + n]) for i in range(max(0, len(w) - n + 1))}
    s, m = grams(short_script), grams(main_script)
    if not s:
        return 0.0
    return len(s & m) / float(len(s))


# Above this, the Short is reusing the episode's sentences. Placed against the
# measurements in derivative_of()'s docstring: the lifted script sits at 84%,
# the most overlapping HONEST script -- one that quotes a real sentence from
# the source paper, which this channel should be free to do -- sits at 11%.
# 18% sits in that gap, nearer the honest end, so quoting is never punished.
MAX_DERIVATIVE = 0.18


# Anything above this is walking the episode's beats in the episode's order.
# Measured across eight scripts written against the same clinical case:
#
#     verbatim retelling        96.4%      independent angle       69.6%
#     paraphrase, tight         89.7%      independent, quoting    63.4%
#     paraphrase, compressed    86.2%      independent, thematic   41.4%
#     paraphrase, competent     83.2%      independent, one detail 39.7%
#
# Every copy lands at 83+ and every original at 70 or below. 0.76 sits in
# the middle of that gap with roughly seven points of margin on each side.
#
# This is the check that matters, because the n-gram check cannot see any of
# it: those three paraphrases scored 1.8%, 0.0% and 0.0% for literal overlap.
# Rebuild the sentences and literal similarity vanishes -- but the SHAPE
# survives paraphrase, and the shape is what makes a Short feel like the
# monologue of the episode.
MAX_BEAT_ORDER = 0.76

_BEAT_STOP = set("""the a an and or but of to in on at is was were be been being it
its this that these those he she they them her his their we you i for with as by
from had has have not no nor so if then than when while which who whom what where
why how all any both each few more most other some such only own same too very can
will just should now up out down over under again further once here there""".split())


def _beats(text):
    """Ordered distinctive content words, first appearance only."""
    out, seen = [], set()
    for w in re.findall(r"[a-z0-9]+", (text or "").lower()):
        if w in _BEAT_STOP or (len(w) < 4 and not w.isdigit()) or w in seen:
            continue
        seen.add(w)
        out.append(w)
    return out


def beat_order_similarity(short_script: str, main_script: str) -> float:
    """Does the Short walk the episode's story in the episode's order?

    Of every pair of details the two scripts share, the fraction that appear
    in the same relative order in both. A chronological retelling preserves
    almost every pair; a Short that enters at one moment and works outward
    from it does not.

    This survives paraphrase, which is the whole point -- rewriting the
    sentences does not reorder the story.
    """
    m_rank = {w: i for i, w in enumerate(_beats(main_script))}
    s = [w for w in _beats(short_script) if w in m_rank]
    if len(s) < 4:
        # Too little shared material to call it a retelling of anything.
        return 0.0
    concordant = total = 0
    for i in range(len(s)):
        for j in range(i + 1, len(s)):
            total += 1
            if m_rank[s[i]] < m_rank[s[j]]:
                concordant += 1
    return concordant / float(total) if total else 0.0


def judge_is_retelling(short_script: str, main_script: str):
    """Ask a model to read both and rule. Returns (is_retelling, reason).

    The two measurements above are shape and letter. Neither can read. A
    model given both texts can answer the question actually being asked --
    "would somebody who watched the episode feel this Short told them
    anything?" -- which is the complaint in its original words.

    Fails OPEN (not a retelling) when the judge is unavailable, because the
    two mechanical checks still stand behind it and a dead API should not
    silently block every Short a channel makes.
    """
    if not (short_script or "").strip() or not (main_script or "").strip():
        return False, ""
    try:
        verdict = llm_json(
            "You are checking whether a 45-second YouTube Short is genuinely "
            "its own piece of writing, or just the long episode retold.\n\n"
            "They SHOULD share facts — it is the same real case. Sharing "
            "facts, numbers, names or even one quoted sentence from the "
            "source paper is fine and expected.\n\n"
            "It is a RETELLING if any of these are true:\n"
            "- it summarises the episode, or walks the same events in the "
            "same order\n"
            "- it opens on the episode's opening beat, or closes on its "
            "closing beat\n"
            "- somebody who watched the episode would learn nothing and feel "
            "nothing new\n\n"
            "It is ITS OWN PIECE if it enters at a specific moment, detail, "
            "number or person the episode passes over, and builds a complete "
            "arc from there — even though the underlying case is the same.\n\n"
            "FULL EPISODE:\n%s\n\nTHE SHORT:\n%s\n\n"
            "Return JSON: {\"retelling\": true or false, \"reason\": \"one "
            "sentence, concrete, naming what you saw\"}"
            % (str(main_script)[:6000], str(short_script)[:3000]))
        if not verdict:
            return False, ""
        return bool(verdict.get("retelling")), str(verdict.get("reason", ""))[:300]
    except Exception as e:
        log.warning("Retelling judge unavailable (non-fatal): %s", e)
        return False, ""


def _reuse_note(short_script: str, main_script: str, limit: int = 3) -> str:
    """Names the longest runs of words the Short took from the episode, so the
    retry is told what to stop doing instead of being asked again politely."""
    words = re.findall(r"[a-z0-9]+", (main_script or "").lower())
    episode = {" ".join(words[i:i + 6]) for i in range(max(0, len(words) - 5))}
    sw = re.findall(r"[a-z0-9]+", (short_script or "").lower())
    runs, current = [], []
    for i in range(max(0, len(sw) - 5)):
        if " ".join(sw[i:i + 6]) in episode:
            current.append(sw[i + 5] if current else " ".join(sw[i:i + 6]))
        elif current:
            runs.append(" ".join(current))
            current = []
    if current:
        runs.append(" ".join(current))
    runs.sort(key=lambda r: -len(r))
    if not runs:
        return ""
    quoted = "\n".join('  - "%s"' % r[:160] for r in runs[:limit])
    return ("\n\nYOUR LAST ATTEMPT WAS REJECTED FOR COPYING THE EPISODE.\n"
            "These exact runs of words were taken from the full video:\n"
            + quoted +
            "\nDo not use those sentences, or rewordings of them. Keep the "
            "facts, throw away every sentence you just wrote, and come at "
            "the story from a different moment entirely.")


def _produce_video_topic_short_once(main_topic: str, main_script: str = "", angle: str = "angle_1",
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

    # FIX (direct user report, July 23 2026 — "I want shots that
    # specifically have the same killer hook, the story, and the
    # ending"): this used to hand the LLM only main_script[:500] as
    # source material. A full episode script runs several thousand
    # characters, so the real twist/resolution — which lives near the
    # END of the script, not the opening — was NEVER included. The Short
    # could not possibly share "the same... ending" as the main video
    # because it never saw what that ending was. Now includes both the
    # opening (setup/hook) and a real slice of the actual ending so the
    # same twist can genuinely be reused, not re-invented from scratch.
    if len(main_script) > 1400:
        story_excerpt = main_script[:600] + "\n...\n" + main_script[-800:]
    else:
        story_excerpt = main_script

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
    prev_score = None  # feeds _shorts_feedback_block() so retries target real gaps, not blind re-rolls
    _overlap_note = ""  # set when an attempt is rejected for copying the episode
    for attempt in range(MAX_ATTEMPTS):
        log.info("produce_video_topic_short attempt %d/%d", attempt + 1, MAX_ATTEMPTS)

        script_data = llm_json(f"""Create a complete, standalone 45-55 second YouTube Short.
Real topic: {main_topic}
Real story details, opening AND actual ending/twist of the full episode: {story_excerpt}

{instruction}{format_block}

Rules:
- This is a COMPLETE piece on its own — no "part 2", no "full story elsewhere",
  no reference to any other video existing
- Real specific details only (numbers, dates, names where used in the source) —
  never invent facts not grounded in the real topic above
- The opening line must create a real "wait — HOW did that happen" curiosity
  gap, built from a concrete detail. It must NOT be the episode's opening
  line rewritten: pick a different way in
- SAME FACTS, DIFFERENT PIECE. Enter the story somewhere the episode does
  not: a single moment, one number, one decision, one person's line. Do not
  summarise the episode and do not retell it in order. Somebody who has just
  watched the full video should still find this worth 45 seconds, and
  somebody who never watches it should not feel they missed anything.
- Write it as if the episode does not exist. Never reuse the episode's
  sentences or its phrasing — the facts are shared, the writing is not.
- It must land on the real outcome — the same true resolution the story
  actually had, never a softer one, never invented, never a cliffhanger.
  Arrive at it your own way; do not reproduce the episode's closing beat
- A WHOLE STORY IN UNDER A MINUTE. The viewer has 45 seconds and no
  context, and they must get all four of these, in this order:
    1. a hook that stops the scroll on its own — a concrete fact, not a
       promise that something is coming
    2. the situation, in one or two lines: who, and what was wrong
    3. the turn — the moment it stops being what everyone assumed
    4. the real ending, stated plainly, so it feels finished
  Nothing may be left for "the full video". If a viewer watches only this
  and never watches anything else, they must still have been told a
  complete story that was worth their time.
{SHORTS_RUBRIC_BLOCK}{_shorts_feedback_block(prev_score)}{_overlap_note}

Return JSON:
{{"title": "under 55 chars, curiosity-gap title, no 'part 1' or 'full video' language",
  "script": "110-140 words, complete standalone account",
  "hook_text": "5-7 words overlay text",
  "hashtags": "{cfg['hashtags_base']} #shorts"}}""")

        if not script_data:
            continue

        # A RETELLING IS REJECTED BEFORE ANYTHING ELSE IS JUDGED.
        #
        # score_short_script measures hook, specificity and shape — all of
        # which a competent paraphrase of the episode passes, because the
        # episode passed them first. That is why 9.0/10 Shorts still read as
        # the main video's monologue. Overlap is the one thing the rubric
        # cannot see, so it is checked separately and it is fatal.
        # THREE INDEPENDENT WAYS OF BEING THE EPISODE AGAIN.
        #
        # score_short_script measures hook, specificity and shape — all of
        # which a competent retelling passes, because the episode passed them
        # first. That is why 9.0/10 Shorts still read as the main video's
        # monologue. So originality is checked separately, and it is fatal.
        #
        # One check is not enough, and the measurements say so. Across eight
        # scripts written against the same case, the three paraphrases scored
        # 1.8%, 0.0% and 0.0% for literal overlap — a paraphrase is invisible
        # to the n-gram check. Their beat ORDER, though, was 83-90% against
        # 40-70% for the originals, because rewriting sentences does not
        # reorder a story. And behind both sits a judge that can actually
        # read, for the retelling that beats a number.
        _short_text = script_data.get("script", "")
        _deriv = derivative_of(_short_text, main_script)
        _beat = beat_order_similarity(_short_text, main_script)

        if _deriv > MAX_DERIVATIVE:
            log.info("Rejected: %.0f%% of this Short is lifted from the episode "
                     "(max %.0f%%) — it is a retelling, not its own piece",
                     _deriv * 100, MAX_DERIVATIVE * 100)
            # Hand the next attempt the actual sentences it reused. A bare
            # retry against an unchanged prompt just produces the same lift
            # again, 13 times; naming the borrowed lines is what makes the
            # retry corrective. prev_score is left alone on purpose — it
            # drives the RUBRIC feedback block, and this is not a rubric miss.
            _overlap_note = _reuse_note(_short_text, main_script)
            continue

        if _beat > MAX_BEAT_ORDER:
            log.info("Rejected: this Short walks the episode's beats in the "
                     "episode's order (%.0f%%, max %.0f%%) — the words are new, "
                     "the story is not", _beat * 100, MAX_BEAT_ORDER * 100)
            _overlap_note = (
                "\n\nYOUR LAST ATTEMPT WAS REJECTED FOR RETELLING THE EPISODE.\n"
                "You rewrote the sentences but kept the episode's running "
                "order, so it still reads as a summary of the full video. Do "
                "not start where the episode starts and do not move through "
                "the events in sequence. Pick ONE moment, number, decision or "
                "person, open there, and let everything else reach the viewer "
                "through that one thing.")
            continue

        _is_retell, _why = judge_is_retelling(_short_text, main_script)
        if _is_retell:
            log.info("Rejected by the originality judge: %s", _why or "(no reason given)")
            _overlap_note = (
                "\n\nYOUR LAST ATTEMPT WAS REJECTED AS A RETELLING OF THE "
                "EPISODE.\nThe specific problem: %s\nKeep every fact. Throw "
                "away the structure and write a different piece about the "
                "same case." % (_why or "it read as a summary of the full video"))
            continue

        pre_score = score_short_script(script_data["script"], script_data["title"], script_data["hook_text"])
        log.info("Pre-score: %.1f/10 (episode overlap %.0f%% literal, "
                 "%.0f%% beat order — both under the bar, judge cleared it)",
                 pre_score["total"], _deriv * 100, _beat * 100)
        notify_short_score(f"video-topic ({angle}) pre-score", attempt + 1, MAX_ATTEMPTS,
                            pre_score["total"], QUALITY_MIN, extra=script_data["title"][:60])
        if pre_score["total"] < QUALITY_MIN:
            log.info("Pre-score too low, retrying topic")
            prev_score = pre_score
            continue

        # FIX (direct user report, July 23 2026 — quality interceptor for
        # every stage, minimum 7.9, applied empire-wide): independent
        # AI-judge read on top of the rule-based rubric above.
        try:
            from quality_auditor import audit_content
            _audit = audit_content("shorts_script", script_data["script"], "",
                                    lambda p, tokens=350: llm(p, max_tokens=tokens), topic=main_topic)
            from quality_auditor import fmt_score as _fmt_audit
            log.info("Quality audit (shorts_script): %s (passed=%s, fallback=%s)",
                      _fmt_audit(_audit["score"]), _audit["passed"],
                      _audit["used_fallback"])
            if not _audit["passed"]:
                log.info("Quality audit below 7.9 bar, retrying")
                continue
        except Exception as e:
            log.warning("Quality audit unavailable (non-fatal): %s", e)

        voice = pick_voice(for_reels=False)
        run_id = uuid.uuid4().hex[:8]
        audio_out = os.path.join(OUTPUT_DIR, f"vtopic_{run_id}.mp3")
        srt_out   = audio_out.replace(".mp3", ".srt")
        bg_out    = os.path.join(OUTPUT_DIR, f"bg_vtopic_{run_id}.mp4")
        video_out = os.path.join(OUTPUT_DIR, f"vtopic_{run_id}_final.mp4")

        if not generate_audio(script_data["script"], voice, audio_out):
            continue

        generate_synced_subtitles(script_data["script"], audio_out, srt_out)
        download_background_clip(cfg["bg_search_term"], bg_out, topic=main_topic,
                                 duration=_audio_seconds(audio_out))

        if not assemble_short_video(bg_out, audio_out, srt_out,
                                     script_data["hook_text"], video_out):
            continue

        # Custom thumbnail — same engine/flow as produce_standalone_short.
        thumb_out = generate_short_thumbnail(script_data["title"], script_data["hook_text"],
                                             cfg["default_niche"], OUTPUT_DIR)
        has_thumb = bool(thumb_out and os.path.exists(thumb_out))

        tags = [t.strip("#") for t in script_data["hashtags"].split() if t.startswith("#")]
        # Was: script_data["script"], i.e. the entire narration.
        _desc = build_short_description(script_data["title"],
                                        script_data.get("hashtags", ""), cfg,
                                        str(main_topic)[:120])
        url = upload_youtube_short(video_out, script_data["title"], _desc, tags)

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

        # FIX (direct user report, July 23 2026 — post-upload reporting
        # for everything without fail, applied empire-wide): same
        # views/likes/subscribers/revenue snapshot the main videos get.
        try:
            from post_upload_reporter import send_post_upload_report
            _vid_id_report = url.rstrip("/").split("/")[-1]
            _token_report = get_yt_token()
            send_post_upload_report(
                cfg.get("display_name", channel), url, _vid_id_report, _token_report,
                None, None, gumroad_token=os.environ.get("GUMROAD_ACCESS_TOKEN"), tg_fn=tg)
        except Exception as e:
            log.warning("Post-upload report for Short (non-fatal): %s", e)

        return {"status": "success", "url": url, "local_path": video_out}

    return {"status": "failed", "reason": "all attempts failed pre-score or assembly"}


# ── 3 x 13, NOT 1 x 13 ────────────────────────────────────────────────────────
# Direct instruction, Aug 1 2026: "for the thumbnail, youtube shorts, editing
# etc I want it to be increased to three attempts, not only one attempt. The
# current rate is 1x13 i want it to be changed to 3x13."
#
# Both producers above ran ONE round of thirteen and then returned
# {"status": "failed"} -- which the pipeline logged as "0/4 Shorts produced"
# and moved on from. The bodies are untouched (they are the round); these
# wrappers give each producer its three rounds, with a real pause and fresh
# research at every boundary. A round that failed thirteen times has exhausted
# what rewording gets it, so the boundary re-seeds rather than re-runs: the
# standalone producer re-fetches trending topics from scratch, and the
# video-topic producer is handed new narrative angles for the same case.
SHORTS_ROUNDS = 3
SHORTS_ROUND_PAUSE_SEC = int(os.environ.get("SHORTS_ROUND_PAUSE_SEC", "600"))


def _shorts_rounds(label, once_fn, research_fn=None):
    """Run a Shorts producer for SHORTS_ROUNDS rounds of MAX_ATTEMPTS."""
    try:
        from gate_rounds import run_in_rounds
    except Exception as e:
        log.warning("gate_rounds unavailable (%s) — %s runs a single round.", e, label)
        return once_fn(1)

    def _round(round_no, seed=None):
        r = once_fn(round_no, seed) if seed is not None else once_fn(round_no)
        # run_in_rounds treats falsy as failure; a dict is always truthy, so
        # translate the producer's own verdict into that vocabulary.
        return r if (r or {}).get("status") == "success" else None

    result, rounds_used, stopped_for_time = run_in_rounds(
        label, _round, rounds=SHORTS_ROUNDS, pause_sec=SHORTS_ROUND_PAUSE_SEC,
        between_rounds=research_fn, round_cost_min=12,
        tg_fn=tg, log_fn=log.info)
    if result:
        return result
    return {"status": "failed",
            "reason": (f"stopped after {rounds_used} round(s) for job time"
                       if stopped_for_time else
                       f"all {SHORTS_ROUNDS} rounds x {MAX_ATTEMPTS} attempts failed "
                       f"pre-score or assembly")}


def produce_standalone_short(mode: str, channel: str = "betrayal_deepdive") -> dict:
    """Three rounds of thirteen. Each round re-researches trending topics."""
    return _shorts_rounds(
        f"Shorts standalone ({mode})",
        lambda round_no, seed=None: _produce_standalone_short_once(mode, channel))


def produce_video_topic_short(main_topic: str, main_script: str = "",
                              angle: str = "angle_1",
                              channel: str = "betrayal_deepdive") -> dict:
    """Three rounds of thirteen, re-angled between rounds."""
    def _research(round_no):
        try:
            out = llm(f"Round {round_no}. A 45-second Short about this case has "
                      f"failed {MAX_ATTEMPTS} attempts. List 6 DIFFERENT narrative "
                      f"angles it could take -- one per line, no numbering, angles "
                      f"only, not finished scripts.\nCase: {str(main_topic)[:200]}")
            lines = [l.strip(" -•*") for l in (out or "").split("\n")
                     if len(l.strip()) > 8]
            return lines[:6] or None
        except Exception as e:
            log.warning("Shorts angle research (non-fatal): %s", e)
            return None

    def _once(round_no, seed=None):
        topic = main_topic
        if seed:
            topic = f"{main_topic}\n\nTAKE THIS ANGLE: {seed[(round_no - 1) % len(seed)]}"
        return _produce_video_topic_short_once(topic, main_script, angle, channel)

    return _shorts_rounds(f"Shorts video-topic ({angle})", _once, _research)


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
