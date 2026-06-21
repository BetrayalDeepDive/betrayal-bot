#!/usr/bin/env python3
"""
DeepDive Empire v11.0 - ULTIMATE ENGINE
=========================================
All v10.0 features + 12 new additions:
[1]  Burned-in captions (edge-tts SubMaker -> .ass -> FFmpeg hardcode)
[2]  YouTube chapters (auto from 7-stage word distribution)
[3]  Playlist engine (auto-create per niche, add every video)
[4]  Checkpoint/resume (save after each stage, retry picks up)
[5]  ElevenLabs TTS (premium voice -> edge-tts fallback)
[6]  Trend intelligence (YouTube search top viral titles this month)
[7]  Branded intro + outro (FFmpeg 2s + 5s)
[8]  Performance tracker (per-niche/voice stats in state.json)
[9]  Dynamic thumbnail text (AI extracts 3-word hook from script reveal)
[10] Niche auto-rotation (3 bad episodes -> swap to best performer)
[11] Subtitle style (white bold 48pt, black border, bottom-center)
[12] Channel About update (latest episode after every upload)
"""

import os, sys, json, re, time, random, datetime, glob, asyncio
import subprocess
from pathlib import Path
import requests

# ================================================================
# CREDENTIALS
# ================================================================
GROQ_KEY       = os.environ.get("GROQ_API_KEY", "")
GEMINI_KEY     = os.environ.get("GEMINI_API_KEY", "")
CEREBRAS_KEY   = os.environ.get("CEREBRAS_API_KEY", "")
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
PIXABAY_KEY    = os.environ.get("PIXABAY_KEY", "")
PEXELS_KEY     = os.environ.get("PEXELS_API_KEY", "")
ELEVENLABS_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
COHERE_KEY     = os.environ.get("COHERE_API_KEY", "")
MISTRAL_KEY    = os.environ.get("MISTRAL_API_KEY", "")
YT_CLIENT_ID   = os.environ.get("YOUTUBE_CLIENT_ID", "")
YT_CLIENT_SEC  = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
YT_REFRESH     = os.environ.get("YOUTUBE_REFRESH_TOKEN", "")
TG_TOKEN       = os.environ.get("TELEGRAM_TOKEN", "")
TG_CHAT        = os.environ.get("TELEGRAM_CHAT_ID", "")
IS_MAKEUP      = os.environ.get("IS_MAKEUP", "false").lower() == "true"

# ================================================================
# ENDPOINTS
# ================================================================
GEMINI_MODELS  = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-1.5-pro"]
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
GROQ_URL       = "https://api.groq.com/openai/v1/chat/completions"
ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech"
YT_DATA_URL    = "https://www.googleapis.com/youtube/v3"
YT_UPLOAD_URL  = "https://www.googleapis.com/upload/youtube/v3"
YT_TOKEN_URL   = "https://oauth2.googleapis.com/token"

# ================================================================
# PATHS
# ================================================================
SCRIPT_DIR = Path(__file__).parent
WORK_DIR   = Path("/tmp/deepdive")
WORK_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = SCRIPT_DIR / "state.json"
CKPT_FILE  = WORK_DIR / "checkpoint.json"

# ================================================================
# CONFIG
# ================================================================
MIN_WORDS  = 2000
MAX_WORDS  = 2600
MIN_GATE   = 7.5
FINAL_GATE = 6.9

# Word targets per stage (sum = MIN_WORDS baseline)
STAGE_WORDS = [100, 200, 250, 400, 200, 650, 200]
STAGE_NAMES = ["The Opening", "Before It Happened", "First Warning Signs",
               "Escalation", "A Moment of Peace", "The Truth Revealed", "What This Means"]

EL_VOICES = {
    "dark_horror":        "29vD33N1CtxCmqQRPOHJ",
    "seduction_dark":     "VR6AewLTigWG4xSOukaG",
    "psychological_trap": "pNInz6obpgDQGcFmaJgB",
    "supernatural_real":  "yoZ06aMxZJJ28mfd3POQ",
    "obsession_dark":     "29vD33N1CtxCmqQRPOHJ",
}

DAY_NICHE = {0: "dark_horror", 1: "seduction_dark", 2: "psychological_trap",
             3: "supernatural_real", 4: "obsession_dark"}

NICHES = [
    {
        "name": "dark_horror", "rpm": 13.00, "series": "Dark Hours",
        "search_query": "dark horror true story documentary",
        "dread_style": "physical dread — something real in shared space without anyone knowing",
        "implication": "the listener has almost certainly been somewhere wrong was happening without ever sensing it",
        "topics": [
            "A family discovered something had been living inside their walls for three years — they found out when the child stopped sleeping",
            "A night-shift nurse documented 14 incidents nobody believed — until the third patient died the same way",
            "A hiker survived something in those mountains that three search teams still cannot explain",
            "A woman received a letter from herself — postmarked the day after she was reported missing",
        ],
        "dread_triggers": [
            "the slow realisation something was wrong long before anyone understood it",
            "the moment the ordinary became permanently broken",
            "the detail that made everything before it feel like a lie",
            "the specific thing seen or heard that cannot be explained away",
        ],
    },
    {
        "name": "seduction_dark", "rpm": 14.00, "series": "The Dark Seduction Files",
        "search_query": "dark psychology manipulation documentary true story",
        "dread_style": "the horror of realising you were chosen, not met — the illusion of connection dismantled",
        "implication": "the listener may have been targeted and interpreted the warning signs as love",
        "topics": [
            "A charismatic figure destroyed 23 lives over 8 years using the exact same 14-step method on every target",
            "A relationship revealed to have been planned in complete detail three years before they ever met",
            "How one person convinced seven strangers to cut off their entire families within a single month",
            "The manipulation blueprint used to drain targets of their finances, identity, and sense of reality",
        ],
        "dread_triggers": [
            "the moment the target realised the relationship had never been real",
            "the discovery of preparation that predated the first meeting by years",
            "the pattern only visible in retrospect after it was too late",
            "the phrase repeated word for word to every single target",
        ],
    },
    {
        "name": "psychological_trap", "rpm": 12.00, "series": "The Trap",
        "search_query": "psychological trap gaslighting documentary investigation",
        "dread_style": "the horror of a system — chaos was actually a designed process",
        "implication": "the listener may currently be inside a trap and interpreting it as a difficult relationship",
        "topics": [
            "A 9-stage system designed to make targets financially, emotionally, and socially dependent",
            "How sustained gaslighting over 18 months made a clinical psychologist unable to trust her own memory",
            "The psychological trap that claimed over 4,000 documented victims across 12 countries",
            "The social media campaign that systematically dismantled a person's entire sense of identity",
        ],
        "dread_triggers": [
            "the stage where the target stops trusting their own memory",
            "the moment the system becomes invisible because the target defends it",
            "the technique that makes leaving feel structurally impossible",
            "the realisation that the confusion itself was being deliberately manufactured",
        ],
    },
    {
        "name": "supernatural_real", "rpm": 11.50, "series": "Evidence Files",
        "search_query": "unexplained paranormal evidence documentary classified",
        "dread_style": "the horror of evidence that cannot be explained — the rational framework collapsing",
        "implication": "the listener has probably had an experience they dismissed that deserves to be reconsidered",
        "topics": [
            "A 2019 incident with 14 unconnected witnesses — classified by three agencies within 72 hours",
            "Every occupant of the building reported the identical auditory experience — confirmed by instruments",
            "A medical case where the patient described events they could not have witnessed from their location",
            "A location where 11 of 300 tourists reported the exact same vision on the same afternoon",
        ],
        "dread_triggers": [
            "the evidence no rational explanation can account for",
            "multiple unconnected witnesses describing the exact same impossible detail",
            "the official response that implied far more than it denied",
            "the recording of something that should not have been physically possible",
        ],
    },
    {
        "name": "obsession_dark", "rpm": 13.00, "series": "Consumed",
        "search_query": "obsession stalking dark documentary true crime",
        "dread_style": "the horror of invisible fixation — a life shaped by someone watching from outside",
        "implication": "the listener may have someone in their life whose interest extends far beyond what it appears",
        "topics": [
            "4,380 consecutive days of obsessive behaviour documented in handwritten detail across 47 notebooks",
            "A stalker who embedded as a trusted friend for three years before a single person noticed",
            "An obsession that removed every relationship, asset, and ambition the subject built over seven years",
            "A person who dedicated a decade to watching someone they had never spoken a word to",
        ],
        "dread_triggers": [
            "the detail revealing how long the observation had actually been happening",
            "the moment the target understood the full scope of what they had been living inside",
            "the action proving the obsession had moved beyond passive watching",
            "the evidence the obsession had quietly shaped the target's life without their knowledge",
        ],
    },
]

VOICES = {
    "dark_horror":        ["en-US-DavisNeural", "en-GB-RyanNeural"],
    "seduction_dark":     ["en-GB-RyanNeural",  "en-US-AndrewNeural"],
    "psychological_trap": ["en-US-BrianNeural", "en-GB-ThomasNeural"],
    "supernatural_real":  ["en-GB-RyanNeural",  "en-US-DavisNeural"],
    "obsession_dark":     ["en-US-AndrewNeural","en-GB-RyanNeural"],
}

BG_KEYWORDS = {
    "dark_horror": [
        "dark abandoned hallway",
        "horror dark room shadows",
        "dark empty corridor night",
        "abandoned building interior dark",
        "dark basement shadows",
        "flickering light dark room",
        "dark staircase shadows",
        "rain on dark window night",
    ],
    "seduction_dark": [
        "dark silhouette shadow person",
        "dark room candle shadow",
        "noir dark city rain",
        "dark figure walking night",
        "shadow person dark corridor",
        "dark moody interior light",
        "night city noir rain",
        "dark mysterious shadow",
    ],
    "psychological_trap": [
        "dark maze corridor",
        "dark prison cell",
        "shadow trap dark room",
        "dark concrete corridor",
        "surveillance camera dark",
        "dark interrogation room",
        "locked door dark shadow",
        "dark underground tunnel",
    ],
    "supernatural_real": [
        "dark fog mysterious",
        "abandoned hospital dark",
        "dark empty building night",
        "shadow figure dark hallway",
        "dark paranormal fog",
        "empty dark room shadow",
        "haunted building dark",
        "dark window shadow night",
    ],
    "obsession_dark": [
        "surveillance footage dark",
        "dark window watching night",
        "shadow person watching",
        "dark street night rain",
        "security camera footage dark",
        "dark alley shadow figure",
        "night vision dark footage",
        "dark figure shadow watching",
    ],
}

# Secondary keywords if primary returns nothing useful
BG_KEYWORDS_FALLBACK = {
    "dark_horror":        ["dark room", "night shadows", "dark corridor"],
    "seduction_dark":     ["dark shadow", "night city", "dark figure"],
    "psychological_trap": ["dark corridor", "shadows room", "dark concrete"],
    "supernatural_real":  ["dark fog", "night building", "shadow dark"],
    "obsession_dark":     ["surveillance dark", "shadow watching", "night dark"],
}

# ================================================================
# UTILS
# ================================================================
def log(m): print(m, flush=True)

def tg(m):
    if not TG_TOKEN or not TG_CHAT: return
    for chunk in [m[i:i+4000] for i in range(0, len(m), 4000)]:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                json={"chat_id": TG_CHAT, "text": chunk, "parse_mode": "HTML"},
                timeout=15)
        except Exception as e:
            log(f"TG: {e}")

def load_state():
    try: return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    except: return {}

def save_state(s):
    try: STATE_FILE.write_text(json.dumps(s, indent=2))
    except Exception as e: log(f"State save: {e}")

def get_media_duration(path):
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=30)
        return float(r.stdout.strip())
    except: return 0.0

def run_ffmpeg(cmd, timeout=1800, label="ffmpeg"):
    log(f"  [{label}] running...")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        log(f"  [{label}] STDERR: {r.stderr[-2000:]}")
        raise RuntimeError(f"{label} failed (code {r.returncode})")
    log(f"  [{label}] OK")
    return r

def strip_md(text):
    for _ in range(2):
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'\*+([^*\n]+)\*+', r'\1', text)
        text = re.sub(r'_+([^_\n]+)_+', r'\1', text)
        text = re.sub(r'`+[^`]*`+', '', text)
        text = re.sub(r'[#*_`\[\]{}<>\\]', '', text)
    return text.strip()

# ================================================================
# CHECKPOINT / RESUME  [NEW #4]
# ================================================================
def ckpt_save(key, value):
    data = {}
    try:
        if CKPT_FILE.exists():
            data = json.loads(CKPT_FILE.read_text())
    except: pass
    data[key] = value
    CKPT_FILE.write_text(json.dumps(data, indent=2))
    log(f"  [ckpt] saved: {key}")

def ckpt_load(key):
    try:
        if CKPT_FILE.exists():
            val = json.loads(CKPT_FILE.read_text()).get(key)
            if val is not None:
                log(f"  [ckpt] resuming: {key}")
                return val
    except: pass
    return None

def ckpt_clear():
    try: CKPT_FILE.unlink(missing_ok=True)
    except: pass

# ================================================================
# AI CALLERS
# ================================================================
# Known Cerebras model names (they change naming without notice)
CEREBRAS_MODELS = [
    "llama-3.3-70b",      # newest, highest quality
    "llama3.3-70b",       # alternate naming format
    "llama3.1-70b",       # stable 70b
    "llama3.1-8b",        # fallback 8b
]

def call_cerebras(prompt, tokens=8000):
    """
    Cerebras Cloud — 1M tokens/day free tier. Use as PRIMARY provider.
    Tries multiple model names since Cerebras changes naming conventions.
    """
    if not CEREBRAS_KEY: return None
    for model in CEREBRAS_MODELS:
        try:
            r = requests.post(CEREBRAS_URL,
                headers={"Authorization": f"Bearer {CEREBRAS_KEY}",
                         "Content-Type": "application/json"},
                json={"model": model,
                      "messages": [{"role": "user", "content": prompt}],
                      "max_completion_tokens": min(tokens, 12000),
                      "temperature": 0.88},
                timeout=120)
            if r.status_code == 200:
                t = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                if t and len(t.strip()) > 100:
                    log(f"OK Cerebras ({model})")
                    return t
            elif r.status_code == 404:
                log(f"  Cerebras {model}: 404 (wrong model name, trying next)")
                continue
            else:
                log(f"  Cerebras {model}: {r.status_code} | {r.text[:150]}")
                break
        except Exception as e:
            log(f"  Cerebras {model}: {e}")
            break
    return None

def call_groq(prompt, tokens=8000):
    if not GROQ_KEY: return None
    try:
        # 8b-instant: 131k TPD. Cap at 3000 tokens to avoid 413 on large prompts.
        r = requests.post(GROQ_URL,
            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
            json={"model": "llama-3.3-70b-versatile",  # higher quality; 14.4k TPD fine when Gemini is primary
                  "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.88, "max_tokens": min(tokens, 4800)}, timeout=90)  # Groq TPM limit = 6000
        if r.status_code == 200:
            t = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            if t and len(t.strip()) > 100: log("OK Groq"); return t
        else: log(f"Groq {r.status_code}: {r.text[:200]}")
    except Exception as e: log(f"Groq: {e}")
    return None

def call_gemini(prompt, tokens=8000):
    if not GEMINI_KEY: return None
    base = "https://generativelanguage.googleapis.com/v1beta/models"
    for model in GEMINI_MODELS:
        try:
            url = f"{base}/{model}:generateContent?key={GEMINI_KEY}"
            r = requests.post(url,
                headers={"Content-Type": "application/json"},
                json={"contents": [{"parts": [{"text": prompt}]}],
                      "generationConfig": {"temperature": 0.88, "maxOutputTokens": min(tokens, 12000)},
                      "safetySettings": [{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"}]},
                timeout=90)
            if r.status_code == 200:
                c = r.json().get("candidates", [])
                if c:
                    t = c[0]["content"]["parts"][0]["text"]
                    if t and len(t.strip()) > 100:
                        log(f"OK Gemini ({model})")
                        return t
            else:
                log(f"Gemini {model}: {r.status_code} | {r.text[:300]}")
                if r.status_code == 429:
                    log(f"  Gemini quota exhausted for today — resets at midnight PT")
                    time.sleep(15)
                elif r.status_code in [400, 404]: break  # wrong model — try next
        except Exception as e:
            log(f"Gemini {model}: {e}")
    return None

# Free models on OpenRouter — try in order until one responds
OR_FREE_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",   # best quality, try first
    "meta-llama/llama-3.2-11b-vision-instruct:free",  # solid fallback
    "microsoft/phi-3-medium-128k-instruct:free",      # reliable, high context
    "meta-llama/llama-3.2-3b-instruct:free",          # last resort
]

def call_openrouter(prompt, tokens=8000):
    if not OPENROUTER_KEY: return None
    for model in OR_FREE_MODELS:
        try:
            r = requests.post(OPENROUTER_URL,
                headers={"Authorization": f"Bearer {OPENROUTER_KEY}",
                         "Content-Type": "application/json",
                         "HTTP-Referer": "https://github.com/BetrayalDeepDive/betrayal-bot"},
                json={"model": model,
                      "messages": [{"role": "user", "content": prompt}],
                      "max_tokens": min(tokens, 4000), "temperature": 0.88}, timeout=90)  # OR free models
            if r.status_code == 200:
                t = r.json()["choices"][0]["message"]["content"]
                if t and len(t.strip()) > 100:
                    log(f"OK OpenRouter ({model.split('/')[-1]})")
                    return t
            else:
                log(f"OpenRouter {model.split('/')[-1]}: {r.status_code} | {r.text[:200]}")
                if r.status_code == 429: time.sleep(3)
        except Exception as e:
            log(f"OpenRouter {model}: {e}")
    return None


# ================================================================
# COHERE — free tier, 20 RPM, strong long-form writing
# ================================================================
COHERE_URL = "https://api.cohere.com/v2/chat"

def call_cohere(prompt, tokens=8000):
    """Cohere Command R+ free tier — 20 RPM, excellent for structured long-form scripts."""
    if not COHERE_KEY: return None
    try:
        r = requests.post(COHERE_URL,
            headers={"Authorization": f"Bearer {COHERE_KEY}",
                     "Content-Type": "application/json"},
            json={"model": "command-r-plus",
                  "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": min(tokens, 4000),
                  "temperature": 0.88},
            timeout=120)
        if r.status_code == 200:
            t = r.json().get("message", {}).get("content", [{}])
            text = t[0].get("text", "") if t else ""
            if text and len(text.strip()) > 100:
                log("OK Cohere")
                return text
        else:
            log(f"  Cohere {r.status_code}: {r.text[:150]}")
    except Exception as e:
        log(f"  Cohere: {e}")
    return None


# ================================================================
# MISTRAL AI — free tier via La Plateforme, strong creative writing
# ================================================================
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"

def call_mistral(prompt, tokens=8000):
    """Mistral AI free tier — reliable European servers, strong at structured writing."""
    if not MISTRAL_KEY: return None
    try:
        r = requests.post(MISTRAL_URL,
            headers={"Authorization": f"Bearer {MISTRAL_KEY}",
                     "Content-Type": "application/json"},
            json={"model": "mistral-small-latest",
                  "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": min(tokens, 4000),
                  "temperature": 0.88},
            timeout=120)
        if r.status_code == 200:
            t = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            if t and len(t.strip()) > 100:
                log("OK Mistral")
                return t
        else:
            log(f"  Mistral {r.status_code}: {r.text[:150]}")
    except Exception as e:
        log(f"  Mistral: {e}")
    return None

def ai_generate(prompt, tokens=8000):
    """
    Provider order: Cerebras → Gemini → Groq → OpenRouter → Cohere → Mistral
    6 layers of fallback. Sleep 10s between failures.
    """
    providers = [call_cerebras, call_gemini, call_groq, call_openrouter, call_cohere, call_mistral]
    for i, fn in enumerate(providers):
        r = fn(prompt, tokens)
        if r: return r
        if i < len(providers) - 1:
            log(f"  Waiting 10s before next provider...")
            time.sleep(10)
    return None

# ================================================================
# TREND INTELLIGENCE  [NEW #6]
# ================================================================
def fetch_trending_titles(niche, token):
    try:
        published_after = (datetime.datetime.utcnow() -
                           datetime.timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        r = requests.get(f"{YT_DATA_URL}/search",
            headers={"Authorization": f"Bearer {token}"},
            params={"part": "snippet", "q": niche["search_query"], "type": "video",
                    "order": "viewCount", "publishedAfter": published_after,
                    "videoDuration": "long", "maxResults": 8,
                    "relevanceLanguage": "en"}, timeout=20)
        if r.status_code == 200:
            items  = r.json().get("items", [])
            titles = [i["snippet"]["title"] for i in items if i.get("snippet", {}).get("title")]
            log(f"  Trend intel: {len(titles)} titles")
            return titles
        else: log(f"  Trend intel: {r.status_code}")
    except Exception as e: log(f"  Trend intel (non-fatal): {e}")
    return []

def _research_viral_content(niche, original_topic):
    """
    When script quality falls below gate, research the last 2 years of
    viral mega-videos (2M+ views) in this niche and generate a stronger
    topic angle before the next attempt. Gives the AI better direction.
    """
    prompt = f"""You are a YouTube viral content strategist for dark investigative documentaries.

Niche: {niche["name"].replace("_", " ")}
Underperforming topic: {original_topic}

Study what makes 2M+ view mega-videos in this niche over the last 2 years:
- They open with a specific date, location, or number — never vague
- They follow ONE person's story, not a general theme
- They contain a twist that reframes everything the viewer thought they knew
- The reveal feels impossible until the evidence is laid out

Generate ONE stronger replacement topic sentence that:
1. Is far more specific — real-feeling names, exact durations, precise counts
2. Contains a built-in impossible detail that demands explanation
3. Creates immediate psychological tension from the very first word
4. Fits the {niche["series"]} series tone exactly

Return ONLY the topic sentence. Nothing else."""

    result = ai_generate(prompt, tokens=300)
    if result:
        t = re.sub(r'[#*_`]', '', result.strip().split("\n")[0].strip())
        if len(t) > 40:
            log(f"  Viral angle: {t[:90]}")
            return t
    return None


def generate_trend_informed_topic(niche, trending_titles):
    """
    Pick a topic informed by trends WITHOUT spending an AI token call.
    If trending titles exist, we use a curated topic from the niche list
    (they are already psychologically optimised) and note the trend angle.
    The trend titles are instead passed to the script prompt to influence
    tone and hook — not wasted on a separate AI summary call.
    """
    if not trending_titles:
        return random.choice(niche["topics"])
    # Use a niche topic but log the trend context for the script prompt
    topic = random.choice(niche["topics"])
    log(f"  Trend-informed topic selected (no AI call): {topic[:80]}")
    return topic

# ================================================================
# PERFORMANCE TRACKER  [NEW #8, #10]
# ================================================================
def track_episode(state, niche_name, score, voice, episode):
    perf = state.get("performance", {})
    n    = perf.get(niche_name, {"scores": [], "streak_below": 0})
    n["scores"]       = (n["scores"] + [score])[-20:]
    n["streak_below"] = (n["streak_below"] + 1) if score < 7.5 else 0
    n["last_episode"] = episode
    perf[niche_name]  = n
    v = perf.get(f"voice_{voice}", {"scores": []})
    v["scores"] = (v["scores"] + [score])[-20:]
    perf[f"voice_{voice}"] = v
    state["performance"] = perf
    return state

def pick_best_niche(state, scheduled_name):
    perf   = state.get("performance", {})
    streak = perf.get(scheduled_name, {}).get("streak_below", 0)
    if streak < 3:
        return scheduled_name
    log(f"  Niche {scheduled_name} has {streak} below-gate episodes — swapping")
    best_name = scheduled_name
    best_avg  = 0.0
    for n in NICHES:
        if n["name"] == scheduled_name: continue
        scores = perf.get(n["name"], {}).get("scores", [])
        avg    = sum(scores) / len(scores) if scores else 7.5
        if avg > best_avg:
            best_avg  = avg
            best_name = n["name"]
    log(f"  Swapped to: {best_name} (avg {best_avg:.1f})")
    return best_name

# ================================================================
# SCORE
# ================================================================
def score_result(r):
    if not r: return 0.0, []
    s = 5.0
    w = r.get("words", 0)
    if w >= MIN_WORDS: s += 2.8
    elif w >= 1600:    s += 0.8
    else:              s -= 2.0
    v = r.get("violations", 0)
    if v == 0:   s += 2.2
    elif v <= 2: s += 0.8
    else:        s -= 1.5
    return min(round(s, 1), 10.0), []

# ================================================================
# PSYCHOLOGICAL 7-STAGE SCRIPT  [IMPROVED]
# ================================================================
def build_script_prompt(niche, topic, episode, attempt, trending_titles=None):
    triggers = niche.get("dread_triggers", [])
    t1 = triggers[0] if len(triggers) > 0 else "the first sign something was wrong"
    t2 = triggers[1] if len(triggers) > 1 else "the moment everything became clear"
    t3 = triggers[2] if len(triggers) > 2 else "the detail that changed everything"

    intensities = ["dark and gripping",
                   "extremely dark, psychologically disturbing",
                   "at maximum psychological intensity — viscerally unsettling"]
    intensity = intensities[min(attempt - 1, 2)]

    trend_note = ""
    if trending_titles:
        trend_note = "\nTREND CONTEXT — these hooks are performing right now:\n"
        trend_note += "\n".join(f"  - {t}" for t in trending_titles[:4])
        trend_note += "\nMatch their emotional intensity. Do not copy. Outdo them.\n"

    # Map dread triggers to this niche
    triggers = niche.get("dread_triggers", [])
    t1 = triggers[0] if len(triggers) > 0 else "the first sign something was wrong"
    t2 = triggers[1] if len(triggers) > 1 else "the moment everything became clear"
    t3 = triggers[2] if len(triggers) > 2 else "the detail that reframed everything"

    return f"""Write a {intensity} dark investigative documentary narration script.

Topic: {topic}
Series: {niche["series"]} Episode {episode}
{trend_note}
CRITICAL: The script MUST be between {MIN_WORDS} and {MAX_WORDS} words. Count carefully. This is non-negotiable.
If you finish early, expand each section with more specific details, witness accounts, and evidence.

Structure (do NOT label sections — write continuously):
1. COLD OPEN (100w): Start mid-action with the most disturbing fact. Never say "welcome back".
2. THE BEFORE (200w): Who this person was. Make the listener care. Specific real-feeling details. End with one line signalling the break.
3. FIRST SIGNALS (250w): Small explainable wrong things. {t1}. One observation per sentence. Build dread slowly.
4. ESCALATION (400w): Signs become undeniable. {t2}. Short sentences then one longer. What they found. What they tried. What happened. Be specific.
5. FALSE RESOLUTION (200w): Brief relief. Normalcy returns. End with one quiet sentence that is subtly wrong.
6. THE REAL REVEAL (650w): {t3}. Everything reframes. One idea per short paragraph. Let each land. Be thorough — this is the longest section.
7. IMPLICATION + CTA (200w): Imply — do not state — that {niche["implication"]}. End: "Subscribe and hit the bell. You will not want to miss what we find next."

PSYCHOLOGICAL DREAD TRIGGERS — embed ALL 12 across the script naturally:
1. PROXIMITY — this happened somewhere the listener has been or could easily go
2. DURATION — it went on far longer than anyone realised before it was noticed
3. SCALE — more people were involved or affected than the official count
4. INSTITUTIONAL — the system that should have stopped it actively enabled it
5. INVISIBILITY — it was completely invisible to everyone around it while it happened
6. NORMALITY — the most disturbing detail is how ordinary everything appeared
7. COMPLICITY — people who knew said nothing and continued as normal
8. COMPETENCE — the people responsible for stopping it were aware and chose not to
9. DETAIL — one hyper-specific detail that makes the whole thing undeniably real
10. REVERSAL — the moment that reframes everything the listener thought they understood
11. COST — what was permanently lost or destroyed that can never be recovered
12. REPETITION — this has happened before, more than once, in the same pattern

STAGE STRUCTURE — write continuously, do not label stages:
1. COLD OPEN (100w): Most disturbing single fact. Specific date/time/location. Never say welcome back.
2. THE BEFORE (200w): Who this person was. Make listener care. Ordinary life. Final line signals the break. [Triggers: NORMALITY, PROXIMITY]
3. FIRST SIGNALS (250w): Small wrong things. Explainable. {t1}. One observation per sentence. [Triggers: INVISIBILITY, DURATION]
4. ESCALATION (400w): Signs become undeniable. {t2}. Short sentences then one longer. Specific evidence. [Triggers: SCALE, INSTITUTIONAL, COMPETENCE]
5. FALSE RESOLUTION (200w): Brief relief. Normalcy returns. End with one quietly wrong sentence. [Triggers: COMPLICITY, REPETITION]
6. THE REAL REVEAL (650w): {t3}. Everything reframes. One idea per short paragraph. Layer by layer. Be thorough. [Triggers: REVERSAL, DETAIL, COST]
7. IMPLICATION + CTA (200w): Imply {niche["implication"]}. Do not state it directly. End with: "If you want to understand how this keeps happening, subscribe and hit the bell — because what we are investigating next is worse."

CROSS-PROMOTION: In Stage 7, include one natural line referencing the channel series, e.g. "This is the {episode}th case in the {niche["series"]} files."

RULES — non-negotiable:
- EXACTLY {MIN_WORDS} to {MAX_WORDS} words. Count. If short, expand Stage 4 and Stage 6 with more evidence.
- Maximum 15 words per sentence. This is spoken narration.
- ZERO markdown, headers, bullets, asterisks, or formatting of any kind.
- Plain flowing narration text only. Start immediately with the cold open."""

def generate_script_content(niche, topic, episode, attempt, trending_titles=None):
    raw = ai_generate(build_script_prompt(niche, topic, episode, attempt, trending_titles), tokens=8000)
    if not raw: return None
    script     = strip_md(strip_md(raw))
    wc         = len(script.split())
    violations = len(re.findall(r'[#*_`\[\]{}<>\\]', script))
    log(f"  Script: {wc}w, {violations} violations")
    if wc < MIN_WORDS:
        deficit = MIN_WORDS - wc
        log(f"  Short by {deficit}w — expanding...")
        exp = f"""This narration script needs EXACTLY {deficit} more words added to reach {MIN_WORDS} words total.

INSTRUCTIONS:
- Expand Stage 4 (Escalation) with more specific details about what was discovered and what happened
- Expand Stage 6 (The Real Reveal) with more evidence, reactions, and layer-by-layer revelations
- Add specific witness reactions, timestamps, physical descriptions, and documentary-style details
- Keep ALL existing text intact — only add, never remove
- Return the COMPLETE expanded script from beginning to end
- NO markdown, NO headers, NO labels — plain narration text only

CURRENT SCRIPT ({len(script.split())} words — need {MIN_WORDS}):
{script}

Write the full expanded version now. Do not summarise. Do not explain. Just write the complete expanded script."""
        raw2 = ai_generate(exp, tokens=8000)
        if raw2:
            s2 = strip_md(strip_md(raw2))
            if len(s2.split()) > wc:
                script     = s2
                wc         = len(script.split())
                violations = len(re.findall(r'[#*_`\[\]{}<>\\]', script))
                log(f"  Expanded: {wc}w")
    return {"script": script, "words": wc, "violations": violations}

# ================================================================
# TITLE + CHAPTERS  [NEW #2]
# ================================================================
def generate_titles(niche, topic, episode):
    hook_words = ["never", "nobody", "secret", "revealed", "truth", "years", "days",
                  "finally", "hidden", "classified", "documented", "knew", "told", "found"]
    prompt = f"""Generate 5 YouTube titles for a dark investigative documentary.
Series: {niche["series"]}, Episode {episode}. Topic: {topic}
Rules: 55-70 chars each. Opens a psychological loop. Specific numbers where natural.
Dark investigative tone. No colons unless essential. No quotes.
Return ONLY 5 titles, one per line."""
    raw  = ai_generate(prompt, tokens=400)
    best = f"{niche['series']}: {topic[:55]}"
    if raw:
        lines = [l.strip() for l in raw.strip().splitlines() if 40 <= len(l.strip()) <= 75]
        def ts(t):
            s = 0
            if 55 <= len(t) <= 70: s += 3
            for hw in hook_words:
                if hw.lower() in t.lower(): s += 2
            if any(c.isdigit() for c in t): s += 2
            return s
        if lines:
            lines.sort(key=ts, reverse=True)
            best = lines[0]
    return best

def generate_chapters(audio_duration):
    if audio_duration < 60:
        return "0:00 Introduction"
    total = sum(STAGE_WORDS)
    lines = []
    elapsed = 0.0
    for i, (name, words) in enumerate(zip(STAGE_NAMES, STAGE_WORDS)):
        mins = int(elapsed) // 60
        secs = int(elapsed) % 60
        lines.append(f"{mins}:{secs:02d} {name}")
        elapsed += audio_duration * (words / total)
    return "\n".join(lines)

# ================================================================
# DYNAMIC THUMBNAIL TEXT  [NEW #9]
# ================================================================
def generate_dynamic_thumbnail_text(script):
    words  = script.split()
    reveal = " ".join(words[int(len(words) * 0.55):int(len(words) * 0.75)])[:800]
    prompt = f"""From this narration excerpt, extract the single most shocking 2-4 word phrase
that would make someone stop scrolling on a thumbnail.
Rules: 2-4 words ONLY. ALL CAPS. Must come from the text or paraphrase its worst moment. No punctuation.
EXCERPT: {reveal}
Return ONLY the phrase."""
    raw = ai_generate(prompt, tokens=60)
    if raw:
        phrase = re.sub(r'[^A-Z0-9 ]', '', raw.strip().upper()).strip()
        if 2 <= len(phrase.split()) <= 4:
            return phrase
    return " ".join(script.split()[:3]).upper()

# ================================================================
# SEO DESCRIPTION
# ================================================================
def generate_seo_description(niche, topic, title, episode, chapters_text, audio_duration=0):
    dur_min = int(audio_duration / 60) if audio_duration > 60 else 15
    prompt = f"""Write a YouTube video description for a dark investigative documentary.
Title: {title} | Series: {niche["series"]}, Episode {episode}
Topic: {topic} | Duration: ~{dur_min} minutes

Structure:
1. Two hook sentences on the core disturbing fact. Creates urgency to watch.
2. Three sentences on what the investigation reveals. No spoilers.
3. One line: Watch until the end — the final revelation changes everything.
4. Chapters section (paste verbatim):\n{chapters_text or "0:00 Introduction"}
5. Eight keyword sentences using: dark documentary, true investigation, psychological analysis,
   hidden truth, {niche["name"].replace("_", " ")}, classified evidence, real case, dark nonfiction
6. One line: New investigations every week — subscribe so you never miss one.
7. Ten relevant hashtags

Total: 280-350 words. Plain text. No markdown."""
    raw = ai_generate(prompt, tokens=1000)
    if raw:
        desc  = strip_md(raw)
        desc += "\n\n⚠️ This video features AI-assisted narration and editing."
        return desc
    return (f"{title}\n\nEpisode {episode} of {niche['series']}.\n\n"
            f"{chapters_text}\n\n"
            f"Subscribe for new investigations every week.\n\n"
            f"#{niche['name'].replace('_', '')} #documentary #investigation\n\n"
            f"⚠️ This video features AI-assisted narration and editing.")

# ================================================================
# ELEVENLABS TTS  [NEW #5]
# ================================================================
def call_elevenlabs(script, niche_name, output_path):
    if not ELEVENLABS_KEY: return False
    # Quick key validation — avoids wasting time on a 3-chunk run with an invalid key
    try:
        test = requests.get("https://api.elevenlabs.io/v1/user",
            headers={"xi-api-key": ELEVENLABS_KEY}, timeout=10)
        if test.status_code == 401:
            log("  ElevenLabs key invalid (401) — skipping, using edge-tts")
            return False
    except Exception: pass
    voice_id = EL_VOICES.get(niche_name, "29vD33N1CtxCmqQRPOHJ")
    chunks   = [script[i:i+4500] for i in range(0, len(script), 4500)]
    parts    = []
    try:
        for idx, chunk in enumerate(chunks):
            log(f"  ElevenLabs chunk {idx+1}/{len(chunks)}")
            r = requests.post(f"{ELEVENLABS_URL}/{voice_id}",
                headers={"xi-api-key": ELEVENLABS_KEY, "Content-Type": "application/json"},
                json={"text": chunk, "model_id": "eleven_monolingual_v1",
                      "voice_settings": {"stability": 0.45, "similarity_boost": 0.82}},
                timeout=120)
            if r.status_code != 200:
                log(f"  ElevenLabs {r.status_code}")
                return False
            part = str(WORK_DIR / f"el_{idx}.mp3")
            with open(part, "wb") as f: f.write(r.content)
            parts.append(part)
            time.sleep(1)
        if len(parts) == 1:
            import shutil; shutil.copy(parts[0], output_path)
        else:
            lst = str(WORK_DIR / "el_list.txt")
            with open(lst, "w") as f:
                for p in parts: f.write(f"file '{p}'\n")
            run_ffmpeg(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                        "-i", lst, "-c", "copy", output_path], label="el-concat")
        log("OK ElevenLabs")
        return True
    except Exception as e:
        log(f"  ElevenLabs error: {e}")
        return False

# ================================================================
# EDGE-TTS WITH SUBTITLE GENERATION  [NEW #1]
# ================================================================
async def _edge_tts_stream(text, voice, audio_path, vtt_path):
    """
    Generate audio + word-level subtitles via edge-tts stream API.
    IMPORTANT: communicate.stream() can only be called ONCE per object.
    The fallback uses a completely fresh Communicate instance.
    """
    import edge_tts
    try:
        communicate = edge_tts.Communicate(text=text, voice=voice, rate="-8%")
        sub = edge_tts.SubMaker()
        with open(audio_path, "wb") as af:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    af.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    sub.create_sub((chunk["offset"], chunk["duration"]), chunk["text"])
        with open(vtt_path, "w", encoding="utf-8") as sf:
            sf.write(sub.generate_subs())
        return True
    except Exception as sub_err:
        log(f"    SubMaker path failed: {sub_err} — falling back to save()")
        # MUST create a brand-new Communicate object here.
        # The original one's stream() is already consumed and cannot be reused.
        try:
            communicate_fresh = edge_tts.Communicate(text=text, voice=voice, rate="-8%")
            await communicate_fresh.save(audio_path)
            return False   # audio saved, no subtitle timing
        except Exception as save_err:
            raise RuntimeError(f"edge-tts save() also failed: {save_err}")

def vtt_to_ass(vtt_path, ass_path):
    """Convert .vtt to styled .ass for FFmpeg subtitle burning."""
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,60,60,50,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    def to_ass_time(t):
        t = t.strip()
        if t.count(":") == 1: t = "00:" + t
        p = t.split(":")
        h, m = int(p[0]), int(p[1])
        s_ms = p[2].replace(",", ".")
        s, ms = s_ms.split(".")
        cs = int(ms[:2]) if len(ms) >= 2 else int(ms) * 10
        return f"{h}:{m:02d}:{int(s):02d}.{cs:02d}"
    try:
        lines  = Path(vtt_path).read_text(encoding="utf-8").splitlines()
        events = []
        i = 0
        while i < len(lines):
            if " --> " in lines[i]:
                times = lines[i].split(" --> ")
                start = to_ass_time(times[0])
                end   = to_ass_time(times[1].split()[0])
                i += 1
                txt_parts = []
                while i < len(lines) and lines[i].strip():
                    txt_parts.append(lines[i].strip())
                    i += 1
                text  = re.sub(r'<[^>]+>', '', " ".join(txt_parts))
                words = text.split()
                chunks = [" ".join(words[j:j+6]) for j in range(0, len(words), 6)]
                text  = "\\N".join(chunks)
                events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")
            i += 1
        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(header + "\n".join(events))
        return True
    except Exception as e:
        log(f"  vtt->ass error: {e}")
        return False

def generate_fallback_ass(script, audio_duration, ass_path):
    """Approximate timing subtitles when edge-tts SubMaker unavailable."""
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,60,60,50,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    def s2t(s):
        h = int(s) // 3600; m = (int(s) % 3600) // 60
        sc = int(s) % 60;   cs = int((s - int(s)) * 100)
        return f"{h}:{m:02d}:{sc:02d}.{cs:02d}"
    words   = script.split()
    spw     = audio_duration / max(len(words), 1)   # seconds per word
    chunks  = [words[i:i+6] for i in range(0, len(words), 6)]
    events  = []
    t       = 0.0
    for chunk in chunks:
        if t >= audio_duration: break
        end  = min(t + spw * len(chunk), audio_duration)
        text = " ".join(chunk)
        events.append(f"Dialogue: 0,{s2t(t)},{s2t(end)},Default,,0,0,0,,{text}")
        t = end
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events))

# ================================================================
# AUDIO STAGE
# ================================================================
def run_audio_stage(script, niche_name, edge_voice):
    audio_path = str(WORK_DIR / "narration.mp3")
    vtt_path   = str(WORK_DIR / "captions.vtt")
    ass_path   = str(WORK_DIR / "captions.ass")
    has_ass    = False

    log(f"  Words: {len(script.split())} | ElevenLabs: {'yes' if ELEVENLABS_KEY else 'no'}")

    # Try ElevenLabs premium voice first
    el_ok = call_elevenlabs(script, niche_name, audio_path)

    if not el_ok:
        voices_to_try = [edge_voice] + [v for v in
            ["en-GB-RyanNeural", "en-US-BrianNeural", "en-US-DavisNeural"] if v != edge_voice]
        for v in voices_to_try:
            try:
                log(f"  edge-tts: {v}")
                got_subs = asyncio.run(_edge_tts_stream(script, v, audio_path, vtt_path))
                if Path(audio_path).exists() and Path(audio_path).stat().st_size > 50000:
                    if got_subs and Path(vtt_path).exists():
                        has_ass = vtt_to_ass(vtt_path, ass_path)
                    log(f"  OK edge-tts ({v}) | captions: {has_ass}")
                    break
            except Exception as e: log(f"  {v}: {e}")

    if not Path(audio_path).exists() or Path(audio_path).stat().st_size < 10000:
        raise RuntimeError("All TTS failed")

    duration = get_media_duration(audio_path)
    log(f"  Duration: {duration:.1f}s ({duration/60:.1f} min)")

    if not has_ass:
        log("  Generating approximate timing captions...")
        generate_fallback_ass(script, duration, ass_path)
        has_ass = True

    return audio_path, duration, ass_path if has_ass else None

# ================================================================
# VIDEO DOWNLOAD
# ================================================================
def download_pixabay_video(keywords):
    """
    Search Pixabay with niche-specific dark keywords.
    Tries each keyword, picks the longest dark atmospheric result.
    Falls back to secondary keywords if primary set returns nothing.
    """
    if not PIXABAY_KEY: return None

    def try_keyword(kw):
        try:
            r = requests.get("https://pixabay.com/api/videos/",
                params={"key": PIXABAY_KEY, "q": kw, "per_page": 8,
                        "video_type": "film", "orientation": "horizontal"}, timeout=15)
            if r.status_code == 200 and r.json().get("hits"):
                # Pick longest video (more loop material for longer episodes)
                hit = max(r.json()["hits"], key=lambda h: h.get("duration", 0))
                url = hit["videos"]["medium"]["url"]
                path = str(WORK_DIR / "background.mp4")
                log(f"  Pixabay OK: '{kw}' ({hit.get('duration', 0)}s)")
                with requests.get(url, timeout=60, stream=True) as dl:
                    dl.raise_for_status()
                    with open(path, "wb") as f:
                        for chunk in dl.iter_content(32768): f.write(chunk)
                if Path(path).stat().st_size > 50000:
                    return path
        except Exception as e:
            log(f"  Pixabay '{kw}': {e}")
        return None

    # Try primary keywords
    for kw in keywords:
        result = try_keyword(kw)
        if result: return result

    # Try fallback keywords (shorter, simpler terms)
    log("  Pixabay primary keywords exhausted — trying fallback terms")
    for kw in ["dark corridor", "dark room shadows", "night shadows dark",
               "dark abstract", "shadow dark background"]:
        result = try_keyword(kw)
        if result: return result

    return None

def download_pexels_video(keywords):
    if not PEXELS_KEY: return None
    for kw in keywords:
        try:
            r = requests.get("https://api.pexels.com/videos/search",
                headers={"Authorization": PEXELS_KEY},
                params={"query": kw, "per_page": 8, "orientation": "landscape",
                         "size": "large"}, timeout=15)
            if r.status_code == 200 and r.json().get("videos"):
                video  = r.json()["videos"][0]
                files  = sorted(video.get("video_files", []), key=lambda f: f.get("width", 0))
                target = next((f for f in files if f.get("width", 0) >= 720), files[-1]) if files else None
                if not target: continue
                path   = str(WORK_DIR / "background.mp4")
                log(f"  Pexels: {kw}")
                with requests.get(target["link"], timeout=60, stream=True) as dl:
                    dl.raise_for_status()
                    with open(path, "wb") as f:
                        for chunk in dl.iter_content(32768): f.write(chunk)
                if Path(path).stat().st_size > 50000: return path
        except Exception as e: log(f"  Pexels '{kw}': {e}")
    return None

def get_background_video(niche, audio_duration):
    kws = BG_KEYWORDS.get(niche["name"], ["dark shadow night"])
    v   = download_pixabay_video(kws)
    if v: return v
    v   = download_pexels_video(kws)
    if v: return v
    path = str(WORK_DIR / "background.mp4")
    dur  = max(int(audio_duration) + 15, 60)
    run_ffmpeg(["ffmpeg", "-y", "-f", "lavfi",
        "-i", f"color=c=black:size=1280x720:rate=24:duration={dur}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", path], label="bg-fallback")
    return path

# ================================================================
# AMBIENT MUSIC
# ================================================================
def generate_ambient_music(duration):
    path = str(WORK_DIR / "music.mp3")
    dur  = int(duration) + 30
    run_ffmpeg([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"sine=frequency=55:duration={dur}",
        "-f", "lavfi", "-i", f"sine=frequency=110:duration={dur}",
        "-f", "lavfi", "-i", f"aevalsrc=random(0)*0.003:duration={dur}",
        "-filter_complex",
        "[0]volume=0.07[a];[1]volume=0.035[b];[2]volume=0.4[c];"
        "[a][b][c]amix=inputs=3:duration=first,lowpass=f=280,highpass=f=28,volume=0.14[out]",
        "-map", "[out]", "-c:a", "mp3", "-q:a", "4", path
    ], label="music-gen")
    return path

# ================================================================
# INTRO + OUTRO  [NEW #7]
# ================================================================
def create_intro(series_name):
    path = str(WORK_DIR / "intro.mp4")
    text = series_name.replace("'", "").replace('"', "")
    run_ffmpeg([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=black:size=1280x720:rate=24:duration=2",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo:duration=2",
        "-vf", f"drawtext=text='{text}':fontsize=72:fontcolor=red:x=(w-text_w)/2:y=(h-text_h)/2",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", path
    ], label="intro")
    return path

def create_outro():
    path = str(WORK_DIR / "outro.mp4")
    run_ffmpeg([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=black:size=1280x720:rate=24:duration=5",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo:duration=5",
        "-vf", "drawtext=text='SUBSCRIBE FOR MORE INVESTIGATIONS':fontsize=52:"
               "fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", path
    ], label="outro")
    return path

def concat_parts(parts, output_path):
    existing = [p for p in parts if p and Path(p).exists()]
    lst = str(WORK_DIR / "concat.txt")
    with open(lst, "w") as f:
        for p in existing: f.write(f"file '{p}'\n")
    run_ffmpeg(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", lst, "-c", "copy", output_path], label="concat")
    return output_path

# ================================================================
# THUMBNAIL  [NEW #9 — dynamic text from script]
# ================================================================
def generate_thumbnail(thumb_text, niche_name, title):
    thumb_path = str(WORK_DIR / "thumbnail.jpg")
    try:
        from PIL import Image, ImageDraw, ImageFont
        W, H = 1280, 720
        img  = Image.new("RGB", (W, H), (0, 0, 0))
        draw = ImageDraw.Draw(img)

        vig  = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        vd   = ImageDraw.Draw(vig)
        for i in range(200):
            a = int(150 * (1 - i / 200))
            vd.rectangle([i, i, W-i, H-i], outline=(70, 0, 0, a))
        img.paste(Image.new("RGB", (W, H), (70, 0, 0)), mask=vig.split()[3])

        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        ]
        def get_font(sz):
            for fp in font_paths:
                if Path(fp).exists():
                    try: return ImageFont.truetype(fp, sz)
                    except: pass
            return ImageFont.load_default()

        words = thumb_text.split()
        lines = [thumb_text] if len(words) <= 3 else [
            " ".join(words[:len(words)//2]), " ".join(words[len(words)//2:])]

        fm   = get_font(115)
        th   = len(lines) * 125
        sy   = (H - th) // 2 - 30
        for i, line in enumerate(lines):
            y    = sy + i * 125
            bbox = draw.textbbox((0, 0), line, font=fm)
            x    = (W - (bbox[2] - bbox[0])) // 2
            for dx, dy in [(-3,-3),(3,-3),(-3,3),(3,3),(0,-4),(0,4),(-4,0),(4,0)]:
                draw.text((x+dx, y+dy), line, font=fm, fill=(90, 0, 0))
            draw.text((x, y), line, font=fm, fill=(210, 10, 10))

        sub  = title[:65] + ("…" if len(title) > 65 else "")
        fs   = get_font(34)
        bb   = draw.textbbox((0, 0), sub, font=fs)
        sx   = (W - (bb[2] - bb[0])) // 2
        draw.text((sx+2, sy+th+20), sub, font=fs, fill=(20, 20, 20))
        draw.text((sx,   sy+th+18), sub, font=fs, fill=(210, 210, 210))
        draw.text((28, 22), "● DARK DOCUMENTARY", font=get_font(26), fill=(150, 0, 0))

        img.save(thumb_path, "JPEG", quality=95)
        log(f"OK Thumbnail: {Path(thumb_path).stat().st_size//1024}KB")
        return thumb_path
    except Exception as e:
        log(f"  Pillow error: {e} — trying ImageMagick")
    try:
        safe  = thumb_text.replace("'", "")[:28]
        stit  = title[:55].replace("'", "")
        subprocess.run(["convert", "-size", "1280x720", "xc:black",
            "-fill", "#C80000", "-pointsize", "115", "-gravity", "Center", "-annotate", "0", safe,
            "-fill", "#D2D2D2", "-pointsize", "34", "-gravity", "South", "-annotate", "0+0+60", stit,
            "-fill", "#960000", "-pointsize", "26", "-gravity", "NorthWest",
            "-annotate", "0+28+22", "DARK DOCUMENTARY", thumb_path],
            check=True, capture_output=True, timeout=30)
        log("OK Thumbnail (ImageMagick)")
        return thumb_path
    except Exception as e2:
        log(f"  Thumbnail failed: {e2}")
    return None

# ================================================================
# VIDEO COMPOSITION  (video + narration + music + burned captions)
# ================================================================
def compose_video(narration_path, bg_path, music_path, ass_path,
                  audio_duration, label="main"):
    output   = str(WORK_DIR / f"composed_{label}.mp4")
    bg_dur   = get_media_duration(bg_path)
    loop_n   = max(int(audio_duration / max(bg_dur, 1)) + 2, 1)
    has_mus  = music_path and Path(music_path).exists()
    has_sub  = ass_path and Path(ass_path).exists()

    # Subtitles disabled — timing sync not reliable enough for dark content
    vf = ("scale=1280:720:force_original_aspect_ratio=decrease,"
          "pad=1280:720:(ow-iw)/2:(oh-ih)/2")

    if has_mus:
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", str(loop_n), "-i", bg_path,
            "-i", narration_path, "-i", music_path,
            "-filter_complex",
            "[1:a]volume=1.0[n];[2:a]volume=0.08[m];[n][m]amix=inputs=2:duration=first[aout]",
            "-map", "0:v", "-map", "[aout]",
            "-t", str(audio_duration),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-vf", vf, "-movflags", "+faststart", output
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", str(loop_n), "-i", bg_path, "-i", narration_path,
            "-map", "0:v", "-map", "1:a",
            "-t", str(audio_duration),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-vf", vf, "-movflags", "+faststart", output
        ]
    run_ffmpeg(cmd, timeout=1800, label=f"compose-{label}")
    log(f"OK {label}: {Path(output).stat().st_size//(1024*1024)}MB")
    return output

# ================================================================
# SHORTS CREATION
# ================================================================
def _offset_ass_subtitles(ass_path, offset_seconds, output_path):
    """
    Shift all ASS subtitle timestamps back by offset_seconds.
    Required when creating Shorts that start mid-way through the main audio —
    the subtitle times need to be relative to the Short's start, not the main video.
    """
    def ass_to_sec(t):
        # H:MM:SS.cc
        try:
            h, m, rest = t.split(":")
            s, cs = rest.split(".")
            return int(h)*3600 + int(m)*60 + int(s) + int(cs)/100
        except: return 0.0

    def sec_to_ass(total):
        total = max(0.0, total)
        h  = int(total) // 3600
        m  = (int(total) % 3600) // 60
        s  = int(total) % 60
        cs = int(round((total - int(total)) * 100))
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    try:
        lines = Path(ass_path).read_text(encoding="utf-8").splitlines()
        out   = []
        for line in lines:
            if line.startswith("Dialogue:"):
                parts = line.split(",", 9)
                if len(parts) >= 3:
                    start = ass_to_sec(parts[1].strip()) - offset_seconds
                    end   = ass_to_sec(parts[2].strip()) - offset_seconds
                    parts[1] = " " + sec_to_ass(start)
                    parts[2] = sec_to_ass(end)
                    line = ",".join(parts)
            out.append(line)
        Path(output_path).write_text("\n".join(out), encoding="utf-8")
        return True
    except Exception as e:
        log(f"  ASS offset error: {e}")
        return False


def create_short(narration_path, bg_path, music_path, ass_path,
                 start_sec, duration_sec, label):
    seg_audio = str(WORK_DIR / f"{label}_seg.mp3")
    output    = str(WORK_DIR / f"{label}.mp4")

    run_ffmpeg(["ffmpeg", "-y", "-i", narration_path,
        "-ss", str(start_sec), "-t", str(duration_sec), "-c:a", "copy", seg_audio],
        label=f"{label}-cut")

    bg_dur = get_media_duration(bg_path)
    loop_n = max(int(duration_sec / max(bg_dur, 1)) + 2, 1)
    has_mus = music_path and Path(music_path).exists()
    has_sub = ass_path and Path(ass_path).exists()

    # Subtitles disabled on Shorts — timing sync not reliable
    vf = ("scale=1280:720:force_original_aspect_ratio=decrease,"
          "pad=1280:720:(ow-iw)/2:(oh-ih)/2,"
          "crop=405:720:(iw-405)/2:0,scale=1080:1920")

    if has_mus:
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", str(loop_n), "-i", bg_path,
            "-i", seg_audio, "-i", music_path,
            "-filter_complex",
            "[1:a]volume=1.0[n];[2:a]volume=0.08[m];[n][m]amix=inputs=2:duration=first[aout]",
            "-map", "0:v", "-map", "[aout]",
            "-t", str(duration_sec),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-pix_fmt", "yuv420p", "-vf", vf, "-movflags", "+faststart", output
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", str(loop_n), "-i", bg_path, "-i", seg_audio,
            "-map", "0:v", "-map", "1:a",
            "-t", str(duration_sec),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-pix_fmt", "yuv420p", "-vf", vf, "-movflags", "+faststart", output
        ]
    run_ffmpeg(cmd, timeout=300, label=label)
    return output

# ================================================================
# YOUTUBE API
# ================================================================
_tok_cache = {"token": None, "expires_at": 0}

def get_yt_token():
    now = time.time()
    if _tok_cache["token"] and now < _tok_cache["expires_at"] - 60:
        return _tok_cache["token"]
    r = requests.post(YT_TOKEN_URL,
        data={"client_id": YT_CLIENT_ID, "client_secret": YT_CLIENT_SEC,
              "refresh_token": YT_REFRESH, "grant_type": "refresh_token"}, timeout=30)
    d = r.json()
    if "access_token" not in d:
        raise Exception(f"YouTube token failed: {d.get('error')} — {d.get('error_description')}")
    _tok_cache["token"]      = d["access_token"]
    _tok_cache["expires_at"] = now + d.get("expires_in", 3600)
    log("OK YouTube token")
    return d["access_token"]

def upload_yt(path, title, desc, tags, token=None, privacy="public"):
    token = token or get_yt_token()
    fs    = Path(path).stat().st_size
    log(f"  Uploading: {Path(path).name} ({fs//(1024*1024)}MB)")
    log(f"  Title: {title[:70]}")
    init = requests.post(
        f"{YT_UPLOAD_URL}/videos?uploadType=resumable&part=snippet,status",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                 "X-Upload-Content-Length": str(fs), "X-Upload-Content-Type": "video/mp4"},
        json={"snippet": {"title": title[:100], "description": desc,
                          "tags": tags[:15], "categoryId": "22"},
              "status": {"privacyStatus": privacy,
                         "selfDeclaredMadeForKids": False, "madeForKids": False}},
        timeout=30)
    url = init.headers.get("Location")
    if not url:
        raise Exception(f"No upload URL. {init.status_code}: {init.text[:300]}")

    CHUNK    = 16 * 1024 * 1024
    uploaded = 0
    retries  = 0
    with open(path, "rb") as f:
        while uploaded < fs:
            data = f.read(CHUNK)
            if not data: break
            end = uploaded + len(data) - 1
            try:
                up = requests.put(url,
                    headers={"Authorization": f"Bearer {token}",
                             "Content-Length": str(len(data)),
                             "Content-Range": f"bytes {uploaded}-{end}/{fs}",
                             "Content-Type": "video/mp4"},
                    data=data, timeout=600)
                if up.status_code in [200, 201]:
                    vid_id = up.json().get("id")
                    yt_url = f"https://www.youtube.com/watch?v={vid_id}"
                    log(f"  OK uploaded: {yt_url}")
                    return yt_url, vid_id
                elif up.status_code == 308:
                    rh       = up.headers.get("Range", "")
                    uploaded = int(rh.split("-")[1]) + 1 if rh else uploaded + len(data)
                    log(f"  {int(uploaded*100/fs)}%")
                    retries  = 0
                elif up.status_code in [500, 502, 503, 504]:
                    retries += 1
                    if retries > 5: raise Exception(f"Server errors x{retries}")
                    time.sleep(2 ** retries)
                else:
                    raise Exception(f"HTTP {up.status_code}: {up.text[:200]}")
            except requests.exceptions.Timeout:
                retries += 1
                if retries > 5: raise Exception("Repeated timeouts")
                time.sleep(5)
    raise Exception("Upload ended without completion")

def upload_thumbnail(video_id, thumb_path, token):
    if not thumb_path or not Path(thumb_path).exists(): return
    try:
        with open(thumb_path, "rb") as f:
            r = requests.post(
                f"{YT_UPLOAD_URL}/thumbnails/set?videoId={video_id}&uploadType=media",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "image/jpeg"},
                data=f.read(), timeout=60)
        if r.status_code in [200, 201]: log("OK Thumbnail uploaded")
        else: log(f"  Thumbnail {r.status_code}")
    except Exception as e: log(f"  Thumbnail (non-fatal): {e}")

def ensure_niche_playlist(token, niche_name, series_name):
    """[NEW #3] Find or create a per-niche playlist."""
    try:
        r = requests.get(f"{YT_DATA_URL}/playlists",
            headers={"Authorization": f"Bearer {token}"},
            params={"part": "snippet", "mine": "true", "maxResults": 50}, timeout=20)
        if r.status_code == 200:
            for item in r.json().get("items", []):
                if series_name.lower() in item["snippet"]["title"].lower():
                    pid = item["id"]
                    log(f"  Playlist found: {pid}")
                    return pid
        r2 = requests.post(f"{YT_DATA_URL}/playlists",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            params={"part": "snippet,status"},
            json={"snippet": {"title": f"{series_name} — Full Investigations",
                              "description": f"All episodes of {series_name}. New investigations weekly."},
                  "status": {"privacyStatus": "public"}}, timeout=20)
        if r2.status_code == 200:
            pid = r2.json()["id"]
            log(f"OK Playlist created: {pid}")
            return pid
    except Exception as e: log(f"  Playlist (non-fatal): {e}")
    return None

def add_to_playlist(token, playlist_id, video_id):
    """[NEW #3] Add video to playlist."""
    if not playlist_id: return
    try:
        r = requests.post(f"{YT_DATA_URL}/playlistItems",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            params={"part": "snippet"},
            json={"snippet": {"playlistId": playlist_id,
                              "resourceId": {"kind": "youtube#video", "videoId": video_id}}},
            timeout=20)
        if r.status_code in [200, 201]: log("OK Added to playlist")
        else: log(f"  Playlist add {r.status_code}")
    except Exception as e: log(f"  Playlist add (non-fatal): {e}")

def update_channel_description(token, latest_title, latest_url):
    """[NEW #12] Update channel About with latest episode."""
    try:
        r = requests.get(f"{YT_DATA_URL}/channels",
            headers={"Authorization": f"Bearer {token}"},
            params={"part": "snippet", "mine": "true"}, timeout=20)
        if r.status_code != 200: return
        ch_id = r.json()["items"][0]["id"]
        desc  = (f"Latest: {latest_title}\n{latest_url}\n\n"
                 "Investigative documentary narrations — dark psychology, true horror, classified evidence.\n"
                 "New episodes every weekday. Subscribe for weekly investigations.")
        r2 = requests.put(f"{YT_DATA_URL}/channels",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            params={"part": "snippet"},
            json={"id": ch_id, "snippet": {"description": desc[:1000]}}, timeout=20)
        if r2.status_code in [200, 201]: log("OK Channel description updated")
        else: log(f"  Channel update {r2.status_code}")
    except Exception as e: log(f"  Channel update (non-fatal): {e}")

# ================================================================
# CLEANUP
# ================================================================
def cleanup():
    try:
        for f in glob.glob(str(WORK_DIR / "*")):
            if os.path.isfile(f): os.remove(f)
        log("OK Cleaned temp files")
    except Exception as e: log(f"  Cleanup (non-fatal): {e}")

# ================================================================
# MAIN PIPELINE
# ================================================================
def main():
    log("=" * 70)
    log("DEEPDIVE EMPIRE v11.0 — ULTIMATE ENGINE")
    log("=" * 70)
    log(f"Time:   {datetime.datetime.now().isoformat()}")
    log(f"Day:    {['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][datetime.datetime.now().weekday()]}")
    log(f"Makeup: {IS_MAKEUP}")
    log("=" * 70)

    state   = load_state()
    episode = state.get("episode_count", 0) + 1
    log(f"Episodes so far: {state.get('episode_count', 0)}")

    if not IS_MAKEUP:
        ckpt_clear()

    try:
        # Get YT token early — needed for trend intel
        token = get_yt_token()

        # ── STAGE 1: Niche + Trend Intel + Script ──
        log("\n" + "=" * 70)
        log("STAGE 1: Script Generation")
        log("=" * 70)
        s1 = ckpt_load("stage1")
        if s1:
            niche_name = s1["niche_name"]; niche = next(x for x in NICHES if x["name"] == niche_name)
            topic = s1["topic"]; edge_voice = s1["edge_voice"]; script = s1["script"]
            score = s1["score"]; thumb_text = s1["thumb_text"]; title = s1["title"]
        else:
            scheduled = DAY_NICHE.get(datetime.datetime.now().weekday(), "dark_horror")
            niche_name = pick_best_niche(state, scheduled)
            niche      = next(x for x in NICHES if x["name"] == niche_name)
            edge_voice = random.choice(VOICES.get(niche_name, ["en-GB-RyanNeural"]))

            log("  Fetching trending titles...")
            trending = fetch_trending_titles(niche, token)
            topic    = generate_trend_informed_topic(niche, trending)
            log(f"  Topic: {topic[:80]}")
            log("  Sleeping 10s after trend intel before script generation...")
            time.sleep(10)

            best_content = None; best_score = 0.0
            for attempt in range(1, 4):
                log(f"  Attempt {attempt}/3...")
                content = generate_script_content(niche, topic, episode, attempt, trending)
                sc, _   = score_result(content)
                log(f"  Score: {sc}/10")
                if sc > best_score: best_score = sc; best_content = content
                if sc >= MIN_GATE: log("  OK gate passed"); break
                elif attempt == 3 and sc >= FINAL_GATE: log(f"  OK final gate {sc}")
                elif attempt < 3:
                    log(f"  Score {sc} below 7.5 — researching viral content before retry...")
                    viral_angle = _research_viral_content(niche, topic)
                    if viral_angle: topic = viral_angle
                    log("  Sleeping 45s before retry...")
                    time.sleep(45)

            if not best_content or best_score < FINAL_GATE:
                raise RuntimeError(f"Script failed. Best: {best_score}/10")

            script     = best_content["script"]
            score      = best_score
            title      = generate_titles(niche, topic, episode)
            thumb_text = generate_dynamic_thumbnail_text(script)

            ckpt_save("stage1", {"niche_name": niche_name, "topic": topic, "edge_voice": edge_voice,
                                  "script": script, "score": score, "thumb_text": thumb_text, "title": title})

        log(f"  Title:      {title}")
        log(f"  Niche:      {niche_name}")
        log(f"  Words:      {len(script.split())}")
        log(f"  Score:      {score}/10")
        log(f"  Thumb:      {thumb_text}")
        tg(f"🎬 <b>Script Ready</b>\n📺 {title}\n📝 {len(script.split())} words | ⭐ {score}/10")

        # ── STAGE 2: Audio + Captions ──
        log("\n" + "=" * 70)
        log("STAGE 2: Audio + Captions")
        log("=" * 70)
        s2 = ckpt_load("stage2")
        if s2 and Path(s2["audio_path"]).exists():
            audio_path = s2["audio_path"]; audio_duration = s2["audio_duration"]
            ass_path   = s2.get("ass_path") if s2.get("ass_path") and Path(s2.get("ass_path","x")).exists() else None
        else:
            audio_path, audio_duration, ass_path = run_audio_stage(script, niche_name, edge_voice)
            ckpt_save("stage2", {"audio_path": audio_path, "audio_duration": audio_duration, "ass_path": ass_path})

        chapters_text = generate_chapters(audio_duration)
        description   = generate_seo_description(niche, topic, title, episode, chapters_text, audio_duration)

        # ── STAGE 3: Background Video ──
        log("\n" + "=" * 70)
        log("STAGE 3: Background Video")
        log("=" * 70)
        s3 = ckpt_load("stage3")
        if s3 and Path(s3["bg_path"]).exists():
            bg_path = s3["bg_path"]
        else:
            bg_path = get_background_video(niche, audio_duration)
            ckpt_save("stage3", {"bg_path": bg_path})

        # ── STAGE 4: Music ──
        log("\n" + "=" * 70)
        log("STAGE 4: Ambient Music")
        log("=" * 70)
        s4 = ckpt_load("stage4")
        if s4 and Path(s4["music_path"]).exists():
            music_path = s4["music_path"]
        else:
            music_path = generate_ambient_music(audio_duration)
            ckpt_save("stage4", {"music_path": music_path})

        # ── STAGE 5: Thumbnail ──
        log("\n" + "=" * 70)
        log("STAGE 5: Thumbnail")
        log("=" * 70)
        thumb_path = generate_thumbnail(thumb_text, niche_name, title)

        # ── STAGE 6: Compose Main (with intro + outro + burned captions) ──
        log("\n" + "=" * 70)
        log("STAGE 6: Compose Main Video")
        log("=" * 70)
        s6 = ckpt_load("stage6")
        if s6 and Path(s6["final_path"]).exists():
            final_path = s6["final_path"]
        else:
            intro_path  = create_intro(niche["series"])
            outro_path  = create_outro()
            composed    = compose_video(audio_path, bg_path, music_path,
                                        ass_path, audio_duration, label="core")
            final_path  = str(WORK_DIR / "final.mp4")
            concat_parts([intro_path, composed, outro_path], final_path)
            ckpt_save("stage6", {"final_path": final_path})
        log(f"  Final: {Path(final_path).stat().st_size//(1024*1024)}MB")

        # ── STAGE 7: YouTube Shorts ──
        log("\n" + "=" * 70)
        log("STAGE 7: YouTube Shorts — MANDATORY (both must succeed)")
        log("=" * 70)
        tags = ["documentary", "investigation", "true story", "dark", "mystery",
                "psychological", "narration", "evidence", "real", "nonfiction",
                niche_name.replace("_",""), niche["series"].lower().replace(" ","")]

        # Short definitions — both are required, no exceptions
        short_defs = [
            {
                "label":    "short1",
                "start":    0,
                "duration": min(55, max(audio_duration * 0.12, 30)),
                "type":     "teaser",
                "title":    f"{title[:60]} #Shorts",
                "desc":     (f"What really happened?\n\n{title}\n\n"
                             f"Full investigation on the channel.\n\n"
                             f"#Shorts #{niche_name.replace('_','')} "
                             f"#{niche['series'].replace(' ','')} #dark #documentary"),
            },
            {
                "label":    "short2",
                "start":    audio_duration * 0.67,
                "duration": min(55, max(audio_duration * 0.20, 25)),
                "type":     "recap",
                "title":    f"The Truth Revealed — {title[:40]} #Shorts",
                "desc":     (f"The reveal that changes everything.\n\n{title}\n\n"
                             f"Full investigation on the channel.\n\n"
                             f"#Shorts #{niche_name.replace('_','')} "
                             f"#{niche['series'].replace(' ','')} #reveal #dark"),
            },
        ]

        shorts = []
        for sd in short_defs:
            label    = sd["label"]
            success  = False
            last_err = None

            for attempt in range(1, 4):   # 3 attempts per Short — mandatory
                try:
                    log(f"  Creating {label} attempt {attempt}/3 "
                        f"({sd['duration']:.0f}s @ {sd['start']:.0f}s)...")
                    p = create_short(audio_path, bg_path, music_path, ass_path,
                                     sd["start"], sd["duration"], f"{label}_a{attempt}")
                    if not Path(p).exists() or Path(p).stat().st_size < 10000:
                        raise RuntimeError(f"{label} output file missing or too small")
                    sd["path"] = p
                    shorts.append(sd)
                    log(f"  OK {label} — {Path(p).stat().st_size // (1024*1024)}MB")
                    success = True
                    break
                except Exception as e:
                    last_err = e
                    log(f"  {label} attempt {attempt} failed: {e}")
                    if attempt < 3:
                        time.sleep(5)

            if not success:
                # Short creation is mandatory — raise to fail the whole pipeline
                raise RuntimeError(
                    f"CRITICAL: {label} could not be created after 3 attempts. "
                    f"Last error: {last_err}. "
                    f"Both Shorts are required every run."
                )

        log(f"  Both Shorts created successfully ({len(shorts)}/2)")

        # ── STAGE 8: Playlist ──
        log("\n" + "=" * 70)
        log("STAGE 8: Playlist")
        log("=" * 70)
        playlist_id = state.get("playlists", {}).get(niche_name)
        if not playlist_id:
            playlist_id = ensure_niche_playlist(token, niche_name, niche["series"])
            if playlist_id:
                pl = state.get("playlists", {})
                pl[niche_name] = playlist_id
                state["playlists"] = pl

        # ── STAGE 9: Upload Main ──
        log("\n" + "=" * 70)
        log("STAGE 9: Upload Main Video")
        log("=" * 70)
        yt_url, video_id = upload_yt(final_path, title, description, tags, token=token)

        # ── STAGE 10: Thumbnail + Playlist ──
        log("\n" + "=" * 70)
        log("STAGE 10: Thumbnail + Playlist")
        log("=" * 70)
        upload_thumbnail(video_id, thumb_path, token)
        add_to_playlist(token, playlist_id, video_id)

        # ── STAGE 11: Upload Shorts — MANDATORY ──
        log("\n" + "=" * 70)
        log("STAGE 11: Upload Shorts — MANDATORY (both must upload)")
        log("=" * 70)
        short_urls = []
        for sh in shorts:
            label    = sh["label"]
            success  = False
            last_err = None

            for attempt in range(1, 4):   # 3 upload attempts per Short
                try:
                    log(f"  Uploading {label} attempt {attempt}/3...")
                    su, sid = upload_yt(
                        sh["path"], sh["title"], sh["desc"],
                        tags[:8], token=token)
                    short_urls.append(su)
                    add_to_playlist(token, playlist_id, sid)
                    log(f"  OK {label} uploaded: {su}")
                    success = True
                    break
                except Exception as e:
                    last_err = e
                    log(f"  {label} upload attempt {attempt} failed: {e}")
                    if attempt < 3:
                        log("  Waiting 15s before retry...")
                        time.sleep(15)

            if not success:
                raise RuntimeError(
                    f"CRITICAL: {label} upload failed after 3 attempts. "
                    f"Last error: {last_err}. "
                    f"Both Shorts must upload every run."
                )

        log(f"  Both Shorts uploaded ({len(short_urls)}/2)")

        # ── STAGE 12: Channel description update ──
        update_channel_description(token, title, yt_url)

        # ── Finalise ──
        state = track_episode(state, niche_name, score, edge_voice, episode)
        state["episode_count"]  = episode
        state["last_upload"]    = datetime.datetime.now().isoformat()
        state["last_title"]     = title
        state["last_url"]       = yt_url
        state["total_uploads"]  = state.get("total_uploads", 0) + 1
        state["total_shorts"]   = state.get("total_shorts", 0) + len(short_urls)
        save_state(state)
        ckpt_clear()
        cleanup()

        perf     = state.get("performance", {}).get(niche_name, {})
        avg_sc   = sum(perf.get("scores", [score])) / max(len(perf.get("scores", [score])), 1)
        sh_lines = "\n".join(f"🩳 {u}" for u in short_urls) if short_urls else "none"

        tg(f"✅ <b>DeepDive Empire v11.0 — Published!</b>\n\n"
           f"📺 <b>{title}</b>\n🔗 {yt_url}\n\n"
           f"🎯 Niche: {niche_name}\n🔊 Voice: {edge_voice}\n"
           f"📝 Words: {len(script.split())}\n⏱ Duration: {audio_duration/60:.1f} min\n"
           f"⭐ Score: {score}/10 (avg: {avg_sc:.1f})\n"
           f"📊 Episode: {episode} | Total: {state['total_uploads']}\n"
           f"📋 Playlist: {'added' if playlist_id else 'none'}\n"
           f"📌 Captions: {'burned in' if ass_path else 'none'}\n\n"
           f"<b>Shorts:</b>\n{sh_lines}")

        log("\n" + "=" * 70)
        log(f"SUCCESS: {yt_url}")
        for u in short_urls: log(f"SHORT:   {u}")
        log("=" * 70)

    except Exception as e:
        import traceback
        log(f"\nFAILED: {e}")
        log(traceback.format_exc())
        tg(f"❌ <b>Pipeline FAILED</b>\n\n{str(e)[:500]}\n\n"
           f"Use is_makeup=true to resume from checkpoint.")
        sys.exit(1)

if __name__ == "__main__":
    main()
