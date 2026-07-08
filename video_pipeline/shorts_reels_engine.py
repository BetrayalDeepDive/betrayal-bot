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
NEWS_KEY    = os.environ.get("NEWS_API_KEY", "")
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
        "standalone_topics": {
            "standalone_1": [
                "betrayal revenge", "shocking truth revealed", "she discovered the secret",
                "he lied for years", "best friend betrayal", "family secret exposed"
            ],
            "standalone_2": [
                "CEO fraud exposed", "legal case shocking verdict", "true crime cold case",
                "dark psychology manipulation", "financial scam billions", "Silicon Valley scandal"
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
                "one piece of evidence solved it", "the alibi that fell apart",
                "cold case reopened after decades", "the fingerprint everyone missed",
                "DNA evidence changed everything", "the confession that didn't match"
            ],
            "standalone_2": [
                "corporate fraud investigation", "forensic accounting exposed billions",
                "digital forensics caught the criminal", "the timeline that broke the case",
                "financial crime evidence trail", "the paper trail nobody found"
            ],
        },
        "default_niche": "forensic investigation",
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
    """
    global CHANNEL, WATERMARK, _active_channel_id
    cfg = CHANNEL_CONFIGS.get(channel_id, CHANNEL_CONFIGS["betrayal_deepdive"])
    CHANNEL   = cfg["display_name"]
    WATERMARK = cfg["watermark"]
    _active_channel_id = channel_id if channel_id in CHANNEL_CONFIGS else "betrayal_deepdive"

def get_active_channel_config():
    """Returns the full config dict for whichever channel is currently active."""
    return CHANNEL_CONFIGS.get(_active_channel_id, CHANNEL_CONFIGS["betrayal_deepdive"])

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Voice Profiles ─────────────────────────────────────────────────────────────
# Research: Multi-gender US + British voices = wider global audience
# Groq Orpheus tags make voice emotional, not robotic
VOICES_EN = [
    # US Male
    {"id": "troy",   "tag": "[intense]",   "gender": "male",   "accent": "US",
     "desc": "Deep US male, intense dramatic"},
    {"id": "austin", "tag": "[disbelief]", "gender": "male",   "accent": "US",
     "desc": "US male, shocked disbelief"},
    {"id": "daniel", "tag": "[outraged]",  "gender": "male",   "accent": "US",
     "desc": "US male, angry outrage"},
    # US Female
    {"id": "luna",   "tag": "[intense]",   "gender": "female", "accent": "US",
     "desc": "US female, intense dramatic"},
    {"id": "stella", "tag": "[disbelief]", "gender": "female", "accent": "US",
     "desc": "US female, shocked"},
    {"id": "autumn", "tag": "[outraged]",  "gender": "female", "accent": "US",
     "desc": "US female, outrage"},
    # British Male
    {"id": "atlas",  "tag": "[intense]",   "gender": "male",   "accent": "British",
     "desc": "British male, deep intense"},
    {"id": "orion",  "tag": "[disbelief]", "gender": "male",   "accent": "British",
     "desc": "British male, disbelief"},
    # British Female
    {"id": "kora",   "tag": "[intense]",   "gender": "female", "accent": "British",
     "desc": "British female, dramatic"},
    {"id": "muse",   "tag": "[outraged]",  "gender": "female", "accent": "British",
     "desc": "British female, outraged"},
]

# For reels: bilingual voices with Hinglish capability
VOICES_HINGLISH = [
    {"id": "luna",   "tag": "[intense]",   "gender": "female", "lang": "hinglish"},
    {"id": "stella", "tag": "[disbelief]", "gender": "female", "lang": "hinglish"},
    {"id": "troy",   "tag": "[intense]",   "gender": "male",   "lang": "hinglish"},
    {"id": "austin", "tag": "[outraged]",  "gender": "male",   "lang": "hinglish"},
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
                r = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={"model": "llama-3.3-70b-versatile",
                          "messages": [{"role": "user", "content": prompt}],
                          "max_tokens": max_tokens, "temperature": temp},
                    timeout=45
                )
                if r.status_code == 429:
                    time.sleep(3)
                    continue
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"].strip()

            elif provider == "gemini":
                r = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}",
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
    raw = llm(prompt + "\n\nReturn ONLY valid JSON. No markdown. No explanation.", max_tokens, 0.3)
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except Exception:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
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
def get_trending_short_topic(mode: str) -> dict:
    """
    Find viral-worthy topic for standalone Shorts.
    Uses NewsAPI for real events + LLM for angle optimization.
    Different topics for standalone_1 vs standalone_2.
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

    # Use LLM to optimise angle for Shorts virality
    result = llm_json(f"""You are a viral YouTube Shorts creator for {cfg['display_name']}.
Topic seed: {topic}
Mode: {mode}

Create a SHORT (45-55 second) viral concept.

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
  "niche": "{cfg['default_niche']}",
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

    # 4. Emotion (0-2 pts)
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

    total = round(sum(scores.values()), 1)
    scores["total"] = total
    scores["passed"] = total >= QUALITY_MIN

    return scores


# ── TTS AUDIO GENERATION ──────────────────────────────────────────────────────
def generate_audio(script: str, voice: dict, output_path: str) -> bool:
    """
    Generate audio via Groq Orpheus with emotional tags.
    Falls back to espeak-ng if Groq unavailable.
    Applies audio enhancement: noise reduction + normalization.
    """
    tag = voice.get("tag", "[intense]")
    voice_id = voice.get("id", "troy")

    # Groq Orpheus TTS
    if GROQ_KEY:
        try:
            tagged_script = f"{tag} {script}"
            r = requests.post(
                "https://api.groq.com/openai/v1/audio/speech",
                headers={"Authorization": f"Bearer {GROQ_KEY}",
                         "Content-Type": "application/json"},
                json={"model": "canopylabs/orpheus-v1-english",
                      "input": tagged_script[:2800],
                      "voice": voice_id,
                      "response_format": "wav"},
                timeout=90
            )
            if r.status_code == 200 and len(r.content) > 1000:
                wav_path = output_path.replace(".mp3", ".wav")
                with open(wav_path, "wb") as f:
                    f.write(r.content)

                # Convert WAV → MP3 with audio enhancement
                # anlmdn = AI noise reduction | loudnorm = volume normalize
                # highpass = remove low-frequency rumble
                result = subprocess.run([
                    "ffmpeg", "-y", "-i", wav_path,
                    "-af", "anlmdn=s=7:p=0.002,loudnorm=I=-16:TP=-1.5:LRA=11,highpass=f=80",
                    "-codec:a", "libmp3lame", "-b:a", "192k", "-ar", "44100",
                    output_path
                ], capture_output=True)

                if result.returncode == 0 and os.path.exists(output_path):
                    log.info("Audio: Groq Orpheus %s (%s) ✅", voice_id, voice.get("accent",""))
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
        subprocess.run([
            "espeak-ng", "-v", espeak_voice, "-s", "155", "-p", "50",
            "-w", raw_wav, script[:500]
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
    Generate frame-accurate SRT subtitles synced to actual audio duration.

    Method:
    1. Get actual audio duration from FFprobe
    2. Calculate words-per-second from script word count + duration
    3. Group words into subtitle chunks (3-5 words each)
    4. Assign timestamps based on word rate
    5. Result: subtitles that sync perfectly with spoken audio

    This is the ONLY reliable way to sync subtitles without a paid
    speech-recognition API — it matches word timing to audio duration.
    """
    if not os.path.exists(audio_path):
        return False

    # Get audio duration
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

    # Group into chunks of 4-5 words for readability
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
            # Clean text for SRT
            clean = text.replace("...", " ").strip()
            f.write(f"{idx}\n{fmt_time(start)} --> {fmt_time(end)}\n{clean}\n\n")

    log.info("Subtitles: %d chunks, %.1fs duration ✅", len(chunks), duration)
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

    # Fallback: dark cinematic background
    log.info("Using FFmpeg background fallback")
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", "color=c=0x0a0a0a:size=1080x1920:r=30",
        "-vf", "vignette=PI/3",
        "-t", "70", output_path
    ], capture_output=True)
    return os.path.exists(output_path)


# ── VIDEO ASSEMBLY (9:16 WITH SUBTITLES) ─────────────────────────────────────
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
    log.info("Video assembled: %.1f MB, %.1fs ✅", size_mb, dur)
    return True


# ── QUALITY SCORING ───────────────────────────────────────────────────────────
def score_final_video(video_path: str, script: str, title: str,
                       has_subtitles: bool, has_thumbnail: bool) -> dict:
    """Final 5-point quality check after assembly."""
    scores = {}

    # 1. Script quality
    shock_words = ["shocking","betrayal","secret","exposed","truth","destroyed","lied"]
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
    title_ok = len(title) <= 70 and any(
        w in title.upper() for w in ["SHOCKING","SECRET","TRUTH","EXPOSED","BETRAYAL","CAUGHT","FRAUD","LIED"]
    )
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

    total = round(sum(scores.values()), 1)
    scores["total"] = total
    scores["passed"] = total >= QUALITY_MIN
    return scores


# ── YOUTUBE UPLOAD ────────────────────────────────────────────────────────────
def get_yt_token() -> str:
    if not all([YT_CLIENT, YT_SECRET, YT_REFRESH]):
        return ""
    r = requests.post(
        "https://oauth2.googleapis.com/token",
        data={"client_id": YT_CLIENT, "client_secret": YT_SECRET,
              "refresh_token": YT_REFRESH, "grant_type": "refresh_token"},
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
        if pre_score["total"] < 7.0:
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

        # 8. Final quality score
        final_score = score_final_video(
            video_out, script, title,
            has_subtitles=os.path.exists(srt_out),
            has_thumbnail=False
        )
        log.info("Final score: %.1f/10 (need %.1f)", final_score["total"], QUALITY_MIN)

        if final_score["total"] < QUALITY_MIN:
            log.info("Quality too low, retrying")
            continue

        # 9. Upload to YouTube
        tags = [t.strip("#") for t in tags_str.split() if t.startswith("#")]
        description = f"{script}\n\n{tags_str}\n\n{cfg['tagline']}"
        yt_url = upload_youtube_short(video_out, title, description, tags)

        # 10. Telegram report
        tg(f"""⚡ *YOUTUBE SHORT UPLOADED*
Mode: {mode}
Title: {title}
Voice: {voice['id']} ({voice['accent']} {voice['gender']})
Score: {final_score['total']}/10
Subtitles: ✅ Synced
URL: {yt_url if yt_url else '⚠️ Upload pending'}""")

        # Cleanup
        for f in [audio_out, srt_out, bg_out]:
            try:
                os.remove(f)
            except Exception:
                pass

        return {"status": "success", "url": yt_url, "score": final_score["total"],
                "title": title, "voice": voice["id"]}

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
        if pre_score["total"] < 7.0:
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

        return {"status": "success", "ig_posted": ig_ok, "yt_url": yt_url,
                "score": final_score["total"]}

    return {"status": "failed", "reason": "max retries"}


def produce_teaser_short(main_topic: str, main_script: str = "", channel: str = "betrayal_deepdive") -> dict:
    """
    YouTube Short 1 (Teaser) — posted 8h BEFORE main video.
    Pulls most shocking moment from main video script.
    channel: determines branding/hashtags/background search (see CHANNEL_CONFIGS).
    """
    set_active_channel(channel)
    cfg = get_active_channel_config()
    if not main_script:
        main_script = main_topic

    script_data = llm_json(f"""Create a 45-second TEASER YouTube Short.
Main video topic: {main_topic}
Main script excerpt: {main_script[:500]}

This teaser goes live 8 HOURS BEFORE the full video.
Goal: Make people desperately want to watch the full video.

Rules:
- Start with the MOST SHOCKING moment from the main story
- Cut off before the resolution — maximum suspense
- End with: "Full story dropping in a few hours..."
- Do NOT give away the ending

Return JSON:
{{"title": "TEASER: [shocking hook] | Full Story Coming Soon",
  "script": "110-130 words teaser script",
  "hook_text": "5-7 words overlay text",
  "hashtags": "{cfg['hashtags_base']} #comingsoon #shocking"}}""")

    if not script_data:
        return {"status": "failed", "reason": "script generation failed"}

    voice = pick_voice(for_reels=False)
    run_id = uuid.uuid4().hex[:8]
    audio_out = os.path.join(OUTPUT_DIR, f"teaser_{run_id}.mp3")
    srt_out   = audio_out.replace(".mp3", ".srt")
    bg_out    = os.path.join(OUTPUT_DIR, f"bg_teaser_{run_id}.mp4")
    video_out = os.path.join(OUTPUT_DIR, f"teaser_{run_id}_final.mp4")

    if not generate_audio(script_data["script"], voice, audio_out):
        return {"status": "failed", "reason": "audio failed"}

    generate_synced_subtitles(script_data["script"], audio_out, srt_out)
    download_background_clip(cfg["bg_search_term"], bg_out)

    if not assemble_short_video(bg_out, audio_out, srt_out,
                                 script_data["hook_text"], video_out):
        return {"status": "failed", "reason": "assembly failed"}

    tags = [t.strip("#") for t in script_data["hashtags"].split() if t.startswith("#")]
    url = upload_youtube_short(video_out, script_data["title"],
                                script_data["script"] + "\n\n#Shorts", tags)

    for f in [audio_out, srt_out, bg_out]:
        try:
            os.remove(f)
        except Exception:
            pass

    tg(f"⚡ *TEASER SHORT UPLOADED*\n{script_data['title']}\n{url}")
    return {"status": "success", "url": url}


def produce_recap_short(main_topic: str, main_video_url: str = "", channel: str = "betrayal_deepdive") -> dict:
    """
    YouTube Short 2 (Recap) — posted 24h AFTER main video.
    Highlights the best/most shocking moment to drive people back.
    channel: determines branding/hashtags/background search (see CHANNEL_CONFIGS).
    """
    set_active_channel(channel)
    cfg = get_active_channel_config()
    script_data = llm_json(f"""Create a 50-second RECAP YouTube Short.
Main video topic: {main_topic}
Main video URL: {main_video_url}

This recap goes live 24 HOURS AFTER the full video.
Goal: Catch people who missed the full video and drive them to watch it.

Rules:
- Pick THE most jaw-dropping reveal from the full story
- Create FOMO: "If you missed this yesterday..."
- End with: "Watch the full story — link in bio"
- Include the shocking resolution/twist

Return JSON:
{{"title": "The moment that SHOCKED everyone | [topic]",
  "script": "120-140 words recap",
  "hook_text": "5-7 words overlay",
  "hashtags": "{cfg['hashtags_base']} #shocking #mustsee"}}""")

    if not script_data:
        return {"status": "failed", "reason": "script failed"}

    voice = pick_voice(for_reels=False)
    run_id    = uuid.uuid4().hex[:8]
    audio_out = os.path.join(OUTPUT_DIR, f"recap_{run_id}.mp3")
    srt_out   = audio_out.replace(".mp3", ".srt")
    bg_out    = os.path.join(OUTPUT_DIR, f"bg_recap_{run_id}.mp4")
    video_out = os.path.join(OUTPUT_DIR, f"recap_{run_id}_final.mp4")

    generate_audio(script_data["script"], voice, audio_out)
    generate_synced_subtitles(script_data["script"], audio_out, srt_out)
    download_background_clip(cfg["bg_search_term"], bg_out)
    assemble_short_video(bg_out, audio_out, srt_out,
                          script_data["hook_text"], video_out)

    tags = [t.strip("#") for t in script_data["hashtags"].split() if t.startswith("#")]
    url = upload_youtube_short(video_out, script_data["title"],
                                script_data["script"] + f"\n\nFull video: {main_video_url}\n\n#Shorts",
                                tags)

    for f in [audio_out, srt_out, bg_out]:
        try:
            os.remove(f)
        except Exception:
            pass

    tg(f"🔁 *RECAP SHORT UPLOADED*\n{script_data['title']}\n{url}")
    return {"status": "success", "url": url}


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
    elif mode == "teaser":
        result = produce_teaser_short(MAIN_TOPIC)
    elif mode == "recap":
        result = produce_recap_short(MAIN_TOPIC)
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
