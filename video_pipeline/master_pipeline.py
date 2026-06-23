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
SAMBANOVA_KEY  = os.environ.get("SAMBANOVA_API_KEY", "")
GEMINI_KEY_2   = os.environ.get("GEMINI_API_KEY_2", "")  # backup Gemini key
YT_CLIENT_ID   = os.environ.get("YOUTUBE_CLIENT_ID", "")
YT_CLIENT_SEC  = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
YT_REFRESH     = os.environ.get("YOUTUBE_REFRESH_TOKEN", "")
TG_TOKEN       = os.environ.get("TELEGRAM_TOKEN", "")
TG_CHAT        = os.environ.get("TELEGRAM_CHAT_ID", "")
IS_MAKEUP      = os.environ.get("IS_MAKEUP", "false").lower() == "true"

# ================================================================
# ENDPOINTS
# ================================================================
GEMINI_MODELS  = ["gemini-2.0-flash"]  # only working model — 1.5-pro and 1.5-flash both 404
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
GROQ_URL       = "https://api.groq.com/openai/v1/chat/completions"
SAMBANOVA_URL  = "https://api.sambanova.ai/v1/chat/completions"  # 1000 req/day free
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
CKPT_FILE  = SCRIPT_DIR / "checkpoint.json"  # in repo — survives runner restarts

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

def tg_buttons(text):
    """Send Telegram message with ✅ APPROVE / ❌ REJECT / ✏️ CHANGE inline buttons."""
    if not TG_TOKEN or not TG_CHAT: return None
    keyboard = {"inline_keyboard": [[
        {"text": "✅ APPROVE",      "callback_data": "approved"},
        {"text": "❌ REJECT",       "callback_data": "rejected"},
        {"text": "✏️ CHANGE TITLE", "callback_data": "change"},
    ]]}
    try:
        r = requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT, "text": text,
                  "parse_mode": "HTML", "reply_markup": keyboard}, timeout=15)
        return r.json().get("result", {}).get("message_id")
    except: return None

def tg_answer_callback(callback_id, answer_text="Got it"):
    """Dismiss button spinner after press."""
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/answerCallbackQuery",
            json={"callback_query_id": callback_id, "text": answer_text}, timeout=10)
    except: pass

def tg_get_updates(offset=None):
    """Get updates including button callbacks."""
    try:
        params = {"timeout": 25,
                  "allowed_updates": ["message", "callback_query"]}
        if offset: params["offset"] = offset
        r = requests.get(f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates",
                         params=params, timeout=30)
        return r.json().get("result", [])
    except: return []

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
    Cerebras Cloud — 1M tokens/day free tier. PRIMARY provider.
    URL + models hardcoded — never relies on module scope.
    401 = bad key. 404 = wrong model name. 429 = rate limit.
    """
    if not CEREBRAS_KEY:
        log("  Cerebras: CEREBRAS_API_KEY not in GitHub Secrets — ADD IT")
        return None
    _url    = "https://api.cerebras.ai/v1/chat/completions"
    _models = ["llama-3.3-70b", "llama3.3-70b", "llama3.1-70b", "llama3.1-8b"]
    for model in _models:
        try:
            r = requests.post(_url,
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
                    log(f"  OK Cerebras ({model})")
                    return t
            elif r.status_code == 401:
                log("  Cerebras 401 UNAUTHORIZED — API key is WRONG or EXPIRED.")
                log("  Fix: go to https://cloud.cerebras.ai/ → API Keys → create new key")
                log("  Then update CEREBRAS_API_KEY in GitHub Secrets.")
                return None  # Wrong key — no point trying other model names
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
    """
    Tries primary GEMINI_API_KEY first.
    If 429 quota exhausted, tries backup GEMINI_API_KEY_2.
    Create a second Google Cloud project for a free second key — doubles quota.
    """
    keys = [k for k in [GEMINI_KEY, GEMINI_KEY_2] if k]
    if not keys:
        log("  Gemini: GEMINI_API_KEY not set")
        return None
    base = "https://generativelanguage.googleapis.com/v1beta/models"
    for key_idx, active_key in enumerate(keys):
        key_label = "primary" if key_idx == 0 else "backup"
        quota_hit = False
        for model in GEMINI_MODELS:
            try:
                url = f"{base}/{model}:generateContent?key={active_key}"
                r = requests.post(url,
                    headers={"Content-Type": "application/json"},
                    json={"contents": [{"parts": [{"text": prompt}]}],
                          "generationConfig": {"temperature": 0.88, "maxOutputTokens": min(tokens, 12000)},
                          "safetySettings": [{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"}, {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"}, {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"}, {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}]},
                    timeout=90)
                if r.status_code == 200:
                    c = r.json().get("candidates", [])
                    if c:
                        t = c[0]["content"]["parts"][0]["text"]
                        if t and len(t.strip()) > 100:
                            log(f"  OK Gemini ({model})")
                            return t
                elif r.status_code == 429:
                    log(f"  Gemini ({key_label}) quota exhausted — resets midnight PT")
                    if key_idx == 0 and GEMINI_KEY_2:
                        log("  Trying backup Gemini key (GEMINI_API_KEY_2)...")
                    quota_hit = True
                    break  # break model loop, try next key
                elif r.status_code in [400, 404]:
                    log(f"  Gemini {model}: {r.status_code} — skipping model")
                    break
                else:
                    log(f"  Gemini {model}: {r.status_code} | {r.text[:200]}")
            except Exception as e:
                log(f"  Gemini {model}: {e}")
        if not quota_hit:
            break  # succeeded or non-quota failure — don't try backup key
    return None

# Free models on OpenRouter — try in order until one responds
OR_FREE_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",    # best quality
    "meta-llama/llama-3.1-70b-instruct:free",    # solid fallback
    "qwen/qwen-2.5-72b-instruct:free",           # strong alternative
    "meta-llama/llama-3.2-3b-instruct:free",     # last resort
]

def call_openrouter(prompt, tokens=8000):
    if not OPENROUTER_KEY:
        log("  OpenRouter: OPENROUTER_API_KEY not set — skipping")
        return None
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
    if not COHERE_KEY:
        log("  Cohere: COHERE_API_KEY not set — skipping")
        return None
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


def call_sambanova(prompt, tokens=8000):
    """
    SambaNova Cloud — free tier, no daily quota wall, llama-3.3-70b.
    Sign up free at https://cloud.sambanova.ai — takes 2 minutes.
    Add SAMBANOVA_API_KEY to GitHub Secrets.
    1,000 requests/day free. Fast inference.
    """
    if not SAMBANOVA_KEY:
        log("  SambaNova: SAMBANOVA_API_KEY not set — add free key from cloud.sambanova.ai")
        return None
    for model in ["Meta-Llama-3.3-70B-Instruct", "Meta-Llama-3.1-70B-Instruct"]:
        try:
            r = requests.post(SAMBANOVA_URL,
                headers={"Authorization": f"Bearer {SAMBANOVA_KEY}",
                         "Content-Type": "application/json"},
                json={"model": model,
                      "messages": [{"role": "user", "content": prompt}],
                      "max_tokens": min(tokens, 8192),
                      "temperature": 0.88},
                timeout=90)
            if r.status_code == 200:
                t = r.json().get("choices",[{}])[0].get("message",{}).get("content","")
                if t and len(t.strip()) > 100:
                    log(f"  OK SambaNova ({model.split('-')[2]})")
                    return t
            elif r.status_code == 401:
                log("  SambaNova 401 — API key invalid. Check SAMBANOVA_API_KEY secret.")
                return None
            elif r.status_code == 429:
                log("  SambaNova 429 — daily limit reached")
                return None
            else:
                log(f"  SambaNova {r.status_code}: {r.text[:120]}")
        except Exception as e:
            log(f"  SambaNova: {e}")
    return None

def call_mistral(prompt, tokens=8000):
    """Mistral AI free tier — reliable European servers, strong at structured writing."""
    if not MISTRAL_KEY:
        log("  Mistral: MISTRAL_API_KEY not set — skipping")
        return None
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
    # Provider order: primary free → backup free → quota-based → fallbacks
    # SambaNova is between Cerebras and Gemini — same quality, no quota wall
    providers = [call_cerebras, call_sambanova, call_gemini,
                 call_groq, call_openrouter, call_cohere, call_mistral]
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
    # v12: retention hook validation
    script = r.get("script", "")
    if script:
        penalty, hook_issues = _validate_retention_hooks_ch1(script)
        s += penalty
    return min(round(s, 1), 10.0), []


def _validate_retention_hooks_ch1(script_clean):
    """
    Validates retention hooks at 30/60/80% positions.
    Returns (penalty, issues). Penalty deducted from script score.
    Called inside score_result so weak scripts retry automatically.
    """
    words   = script_clean.split()
    total   = len(words)
    if total < 400:
        return 0.0, []
    penalty = 0.0; issues = []

    def seg(p1, p2):
        return " ".join(words[int(total*p1):int(total*p2)]).lower()

    hook_signals = ["subscribe","coming up","next","what happens","the answer","revealed",
                    "in a moment","stay","about to","this changes","not yet","what comes next"]

    if sum(1 for w in hook_signals if w in seg(0.25, 0.35)) < 1:
        penalty -= 0.4; issues.append("Missing 30% hook")
    h60 = sum(1 for w in hook_signals if w in seg(0.55, 0.65))
    if h60 < 2:
        penalty -= 0.8; issues.append("Weak 60% hook — peak CTA missing")
    elif h60 >= 3:
        penalty += 0.3
    if sum(1 for w in hook_signals if w in seg(0.75, 0.85)) < 1:
        penalty -= 0.4; issues.append("Missing 80% hook")
    if "subscribe" not in " ".join(words[-60:]).lower():
        penalty -= 0.3; issues.append("Missing final subscribe CTA")
    if issues: log(f"  Retention issues: {' | '.join(issues)}")
    return round(penalty, 1), issues

# ================================================================
# PSYCHOLOGICAL 7-STAGE SCRIPT  [IMPROVED]
# ================================================================
def generate_best_cold_open(niche, topic, trending_titles=None):
    """
    Generate 3 cold open variants, score each on hook strength, return the best.
    The cold open is the most important 30 seconds — it determines whether
    YouTube promotes the video or buries it.
    """
    trend_hint = ""
    if trending_titles:
        trend_hint = f"These hooks are working in this niche right now:\n"
        trend_hint += "\n".join(f"  - {t}" for t in trending_titles[:3])

    prompt = f"""Generate exactly 3 different cold open variants for a dark documentary narration.
Topic: {topic}
Niche style: {niche["dread_style"]}
{trend_hint}

Each cold open must:
- Be 80-120 words
- Start with the single most disturbing fact — mid-action, no preamble
- Never say "welcome back", "today", "in this video"
- Use a specific date, time, or number in the first sentence
- Create a question the listener cannot stop thinking about

Format your response EXACTLY as:
VARIANT_1:
[cold open text here]
VARIANT_2:
[cold open text here]
VARIANT_3:
[cold open text here]

Write all 3 now. Zero markdown."""

    raw = ai_generate(prompt, tokens=1200)
    if not raw:
        return None

    # Parse variants
    variants = []
    for i in range(1, 4):
        pattern = f"VARIANT_{i}:"
        next_p  = f"VARIANT_{i+1}:" if i < 3 else None
        start = raw.find(pattern)
        if start == -1: continue
        start += len(pattern)
        end   = raw.find(next_p, start) if next_p else len(raw)
        text  = strip_md(raw[start:end].strip())
        if len(text.split()) >= 60:
            variants.append(text)

    if not variants:
        return None

    # Score each variant on hook strength
    def score_cold_open(text):
        s = 0.0
        words = text.lower()
        # Specific numbers/dates signal
        if re.search(r'\d', text): s += 2.0
        # Short punchy sentences
        sentences = [x.strip() for x in re.split(r'(?<=[.!?])\s+', text) if x.strip()]
        if sentences:
            avg_len = sum(len(x.split()) for x in sentences) / len(sentences)
            if avg_len <= 10: s += 2.0
            elif avg_len <= 13: s += 1.0
        # Dread keywords
        dread = ["discovered","found","nobody","never","years","days","inside","unknown","hidden","only"]
        s += sum(0.4 for w in dread if w in words)
        # Opens mid-action (no weak openers)
        weak = ["in this", "today we", "welcome", "hello", "this is the story", "have you ever"]
        if not any(w in words[:50] for w in weak): s += 1.5
        return round(min(s, 10.0), 1)

    scored = [(v, score_cold_open(v)) for v in variants]
    scored.sort(key=lambda x: x[1], reverse=True)
    best_text, best_score = scored[0]
    log(f"  Cold opens scored: {[s for _,s in scored]} — picked {best_score}/10")
    return best_text


# ================================================================
# REAL CASE RESEARCH
# Pulls real documented cases from free sources before script generation.
# AI narrates real facts instead of inventing plausible-sounding ones.
# Sources: Google News RSS (free) + Reddit r/TrueCrime (free read-only)
# ================================================================

def search_real_cases(niche_name, topic_hint):
    """
    Search Google News RSS and Reddit for real documented cases
    matching this niche. Returns list of real case summaries.
    No API key required for either source.
    """
    import xml.etree.ElementTree as ET
    import urllib.parse

    # Build niche-specific search queries
    niche_queries = {
        "dark_horror":        f"{topic_hint.split()[0]} horror true story documented",
        "seduction_dark":     f"manipulation relationship psychology documented case",
        "psychological_trap": f"gaslighting psychological abuse documented case",
        "supernatural_real":  f"unexplained phenomenon documented evidence case",
        "obsession_dark":     f"stalking obsession documented court case",
    }
    query = niche_queries.get(niche_name, topic_hint.split()[0] + " documented case")
    cases = []

    # Source 1: Google News RSS — completely free, no key
    try:
        gn_url = ("https://news.google.com/rss/search"
                  f"?q={urllib.parse.quote(query)}&hl=en-US&gl=US&ceid=US:en")
        r = requests.get(gn_url, timeout=15,
                        headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            root = ET.fromstring(r.content)
            items = root.findall(".//item")[:5]
            for item in items:
                title = item.find("title")
                desc  = item.find("description")
                pub   = item.find("pubDate")
                if title is not None and title.text:
                    cases.append({
                        "source":  "news",
                        "title":   title.text[:120],
                        "summary": desc.text[:200] if desc is not None and desc.text else "",
                        "date":    pub.text[:20] if pub is not None and pub.text else "",
                    })
            log(f"  Real cases from news: {len(cases)}")
    except Exception as e:
        log(f"  News RSS (non-fatal): {e}")

    # Source 2: Reddit r/TrueCrime — free read-only JSON API
    try:
        reddit_url = (f"https://www.reddit.com/r/TrueCrime/search.json"
                      f"?q={urllib.parse.quote(query)}&sort=top&t=year&limit=5")
        r2 = requests.get(reddit_url, timeout=15,
                         headers={"User-Agent": "DeepDiveResearch/1.0"})
        if r2.status_code == 200:
            posts = r2.json().get("data", {}).get("children", [])
            for post in posts[:3]:
                d = post.get("data", {})
                title = d.get("title", "")
                if title and len(title) > 20:
                    cases.append({
                        "source":  "reddit",
                        "title":   title[:120],
                        "summary": d.get("selftext", "")[:200],
                        "date":    "",
                        "score":   d.get("score", 0),
                    })
            log(f"  Real cases from Reddit: {len([c for c in cases if c['source']=='reddit'])}")
    except Exception as e:
        log(f"  Reddit (non-fatal): {e}")

    return cases[:6]  # top 6 real cases


def extract_real_case_facts(cases, niche_name):
    """
    Use AI to extract the most compelling documented facts from
    the real cases found. Returns a brief that gets injected
    into the script prompt — AI narrates real facts, doesn't invent.
    """
    if not cases:
        return ""

    cases_text = "\n".join(
        f"- [{c['source'].upper()}] {c['title']} | {c['summary'][:100]}"
        for c in cases[:5]
    )

    prompt = f"""From these REAL documented cases in the {niche_name.replace('_', ' ')} niche:

{cases_text}

Extract the single most compelling REAL case with:
1. ONE specific verifiable fact (exact number, date, duration, or amount)
2. ONE detail that makes it feel completely real and documented
3. The core disturbing element that would make someone watch a full documentary

Return as: REAL CASE BRIEF (3 sentences max, plain text, use the actual facts):
[fact 1]. [fact 2]. [core disturbing element]."""

    result = ai_generate(prompt, tokens=300)
    if result:
        brief = result.strip()[:400]
        if len(brief) > 50:
            log(f"  Real case brief: {brief[:80]}...")
            return brief
    return ""


def get_research_context(niche_name, topic):
    """
    Main research entry point. Returns a research context string
    to inject into the script prompt before generation.
    """
    log("  Researching real documented cases...")
    cases = search_real_cases(niche_name, topic)
    if not cases:
        log("  No real cases found — proceeding with AI-generated topic")
        return ""
    brief = extract_real_case_facts(cases, niche_name)
    if not brief:
        return ""
    return (
        f"REAL DOCUMENTED CASE RESEARCH (use these real facts in your script):\n"
        f"{brief}\n"
        f"IMPORTANT: Use these real facts as the foundation. Do not invent details. "
        f"Build the narrative around documented reality."
    )

def build_script_prompt(niche, topic, episode, attempt,
                        trending_titles=None, research_context=""):
    """
    v2 script prompt — 7-stage architecture with stage-specific
    word targets, trigger placements, and forbidden phrases per stage.
    """
    intensities = [
        "precisely observed, factual, and quietly disturbing",
        "forensically detailed — each fact more specific than the last",
        "at maximum specificity — every sentence contains one undeniable concrete detail",
    ]
    intensity = intensities[min(attempt - 1, 2)]

    trend_block = ""
    if trending_titles:
        trend_block = "\nWHAT IS WORKING IN THIS NICHE RIGHT NOW:\n"
        trend_block += "\n".join(f"  '{t}'" for t in trending_titles[:4])
        trend_block += "\nMatch their emotional register. Never copy. Outperform them.\n"

    pattern_ctx  = load_pattern_memory(load_state())
    strategy_ctx = load_weekly_strategy()
    combined     = "\n".join(filter(None, [pattern_ctx, strategy_ctx]))
    pattern_block = f"\nPATTERN MEMORY (scored 8+/10 previously):\n{combined}\n" if combined else ""

    research_block = f"\nRESEARCH CONTEXT:\n{research_context}\n" if research_context else ""

    stage_targets = {1:110, 2:210, 3:260, 4:420, 5:170, 6:680, 7:190}

    return f"""Write a {intensity} dark investigative documentary narration.

TOPIC: {topic}
SERIES: {niche["series"]} — Episode {episode}
{trend_block}{pattern_block}{research_block}

TOTAL WORD REQUIREMENT: {MIN_WORDS} to {MAX_WORDS} words.
Each stage must hit its target. If any stage runs short, expand with more specific evidence.

SEVEN-STAGE STRUCTURE — write continuously, no labels, no headers:

STAGE 1 — COLD OPEN ({stage_targets[1]} words)
Sentence 1 must contain an exact number, date, or duration.
Sentence 2 places the listener somewhere recognisable.
Sentence 3 opens a loop the script must close.
Forbidden: "welcome back", "today we", "in this video", "join me"
Trigger: DETAIL (sentence 1), PROXIMITY (sentence 2), open loop (sentence 3)

STAGE 2 — THE BEFORE ({stage_targets[2]} words)
Establish the subject as completely ordinary. Specific routine, specific place.
Final sentence: signal something is about to break — without stating it.
Forbidden: "little did they know", "but little did", "unbeknownst to them"
Trigger: NORMALITY (sentences 1-3), PROXIMITY (sentences 4-6)

STAGE 3 — FIRST SIGNALS ({stage_targets[3]} words)
Small wrong things. Individually explainable. One per sentence. Build accumulation.
Start with the smallest possible wrong detail.
Forbidden: "suddenly", "out of nowhere", "without warning"
Trigger: INVISIBILITY (s1), DURATION (s3), SCALE (s5), INSTITUTIONAL (s7)

STAGE 4 — ESCALATION ({stage_targets[4]} words)
Open with one short sentence that reframes Stage 3 entirely.
Signs become undeniable. Short sentences, then one longer one. Specific evidence.
Forbidden: passive voice, vague quantities ("many", "several", "some")
Trigger: SCALE (s1), COMPETENCE (s4), INSTITUTIONAL (s7), COMPLICITY (s10)

STAGE 5 — FALSE RESOLUTION ({stage_targets[5]} words)
Normalcy briefly returns. Specific timeframe. Listener exhales.
Final sentence: subtly, quietly wrong — not dramatic, not announced.
Forbidden: "but it wasn't over", "however", "little did they know", "or so they thought"
Trigger: NORMALITY (s1-3), REPETITION (s4), quiet wrongness (final)

STAGE 6 — THE REAL REVEAL ({stage_targets[6]} words)
One short sentence destroys the false resolution. Then one idea per short paragraph.
Most disturbing section. Be thorough. Let each paragraph land before moving on.
Forbidden: "in conclusion", "to summarise", "as we can see"
Trigger per paragraph: REVERSAL, DETAIL, COST, SCALE, DURATION, INSTITUTIONAL, REPETITION

STAGE 7 — IMPLICATION AND CTA ({stage_targets[7]} words)
Imply — never state — that this pattern extends beyond this case.
Subscribe CTA at the emotional peak, not as afterthought.
Forbidden: "subscribe and like", "hit the bell", "don't forget to"
Trigger: REPETITION (s1), PROXIMITY (s3), subscribe CTA (final 2 sentences)

ABSOLUTE RULES:
1. Maximum 13 words per sentence. Count them.
2. Zero markdown — no symbols, headers, bullets, asterisks.
3. Zero AI filler — no "moreover", "furthermore", "interestingly", "it is worth noting".
4. Every number must be specific: not "many" but "forty-seven".
5. Every date must be specific: not "years ago" but "a Thursday in March 2019".
6. Every location must be specific: not "a small town" but "a city of 340,000 people".
7. Start immediately. No preamble. No introduction.
8. Write one continuous narrative — do not number or label stages.

Write the complete script now:"""


def generate_script_content(niche, topic, episode, attempt,
                             trending_titles=None, research_context=""):
    """
    v2 script generation:
    1. Generate full script with stage-structured v2 prompt
    2. Score each of 7 stages independently
    3. Rewrite only the 2 worst-scoring stages with targeted instructions
    4. Inject subscribe CTAs at 30/60/80% marks
    """
    # Step 1: Generate research anchors to prevent vague AI output
    anchors = {}
    try:
        anchor_prompt = (
            f"Generate specific realistic research anchors for a documentary about: {topic}\n"
            f"Return ONLY valid JSON (no backticks):\n"
            f'{{"duration":"how long before discovery e.g. 4380 days",'
            f'"people_count":"number affected e.g. 847 confirmed cases",'
            f'"first_signal_date":"e.g. a Tuesday in March 2011",'
            f'"discovery_date":"e.g. October 14 2019",'
            f'"location":"specific-feeling place e.g. a city of 340000 people",'
            f'"key_number":"most disturbing specific number",'
            f'"cost":"what was permanently lost e.g. $2.4 million over eleven years"}}'
        )
        anchor_raw = ai_generate(anchor_prompt, tokens=300)
        if anchor_raw:
            anchor_raw = re.sub(r"```json|```", "", anchor_raw).strip()
            m = re.search(r"\{[\s\S]*?\}", anchor_raw)
            if m:
                anchors = json.loads(m.group())
                log(f"  Research anchors loaded: {len(anchors)} fields")
    except Exception as e:
        log(f"  Anchors (non-fatal): {e}")

    # Inject anchors into research_context
    if anchors:
        anchor_lines = "\n".join(f"  {k}: {v}" for k, v in anchors.items() if v)
        research_context = f"USE THESE SPECIFIC DETAILS:\n{anchor_lines}\n{research_context}"

    # Step 2: Generate script
    raw = ai_generate(build_script_prompt(
        niche, topic, episode, attempt, trending_titles, research_context), tokens=8000)
    if not raw:
        return None
    script     = strip_md(strip_md(raw))
    wc         = len(script.split())
    violations = len(re.findall(r"[#*_`\[\]{}<>\\]", script))
    log(f"  Script: {wc}w | {violations} violations")

    # Step 3: Expand if short
    if wc < MIN_WORDS:
        deficit = MIN_WORDS - wc
        log(f"  Short by {deficit}w — expanding stages 4 and 6...")
        exp = (
            f"This documentary script is {wc} words. It needs {MIN_WORDS} minimum. "
            f"Expand the Escalation section and the Reveal section only. "
            f"Add specific evidence, exact numbers, exact dates, witness reactions. "
            f"Max 13 words per sentence. Zero markdown. "
            f"Return the COMPLETE expanded script.\n\nSCRIPT:\n{script}"
        )
        raw2 = ai_generate(exp, tokens=8000)
        if raw2:
            s2 = strip_md(strip_md(raw2))
            if len(s2.split()) > wc:
                script     = s2
                wc         = len(script.split())
                violations = len(re.findall(r"[#*_`\[\]{}<>\\]", script))
                log(f"  Expanded: {wc}w")

    # Step 4: Stage-level scoring + targeted rewrite of 2 worst stages
    if wc >= MIN_WORDS:
        try:
            # Split script proportionally into 7 stages
            words    = script.split()
            total    = len(words)
            targets  = [110, 210, 260, 420, 170, 680, 190]
            total_t  = sum(targets)
            stage_texts = []
            pos = 0
            for i, tgt in enumerate(targets):
                share = tgt / total_t
                end   = pos + int(total * share) if i < 6 else total
                stage_texts.append(" ".join(words[pos:end]))
                pos   = end

            # Score each stage
            stage_names   = ["COLD OPEN","THE BEFORE","FIRST SIGNALS",
                             "ESCALATION","FALSE RESOLUTION","THE REVEAL","IMPLICATION"]
            hook_signals  = ["subscribe","next","what happens","revealed","about to",
                             "this changes","thirty seconds","coming up","stay"]
            forbidden_per = [
                ["welcome back","today we","in this video","join me"],
                ["little did they know","unbeknownst"],
                ["suddenly","out of nowhere","without warning"],
                [],
                ["but it wasn't over","however","or so they thought"],
                ["in conclusion","to summarise","as we can see"],
                ["subscribe and like","hit the bell","don't forget"],
            ]

            stage_scores = []
            for i, (stext, sname, starget, sforbidden) in enumerate(
                    zip(stage_texts, stage_names, targets, forbidden_per)):
                sc    = 5.0
                sw    = len(stext.split())
                ratio = sw / max(starget, 1)
                if 0.85 <= ratio <= 1.15:   sc += 2.0
                elif 0.70 <= ratio <= 1.30: sc += 0.8
                else:                       sc -= 1.5
                found_forbidden = [f for f in sforbidden if f in stext.lower()]
                sc -= len(found_forbidden) * 0.8
                sents = [s for s in re.split(r"(?<=[.!?])\s+", stext) if s.strip()]
                long  = [s for s in sents if len(s.split()) > 13]
                if len(long) / max(len(sents), 1) > 0.2:
                    sc -= 0.8
                if i in [0, 6]:  # cold open and CTA — check for hooks
                    if not any(h in stext.lower() for h in hook_signals[:3]):
                        sc -= 0.5
                ai_phrases = ["moreover","furthermore","it is worth noting","in conclusion"]
                sc -= sum(0.4 for p in ai_phrases if p in stext.lower())
                stage_scores.append(round(min(max(sc, 0), 10), 1))

            score_str = " | ".join(f"{n[:8]}:{s}" for n,s in zip(stage_names, stage_scores))
            log(f"  Stage scores: {score_str}")

            # Rewrite the 2 worst stages
            worst_two = sorted(range(len(stage_scores)), key=lambda i: stage_scores[i])[:2]
            for idx in worst_two:
                if stage_scores[idx] >= 7.5:
                    continue
                sdef_name   = stage_names[idx]
                sdef_target = targets[idx]
                sdef_forb   = forbidden_per[idx]
                forb_str    = ", ".join(f'"{f}"' for f in sdef_forb) if sdef_forb else "none"
                rewrite_p   = (
                    f"Rewrite ONLY this single script stage. Return ONLY the rewritten stage.\n\n"
                    f"STAGE: {sdef_name} (target: {sdef_target} words)\n"
                    f"TOPIC: {topic[:100]}\n"
                    f"CURRENT SCORE: {stage_scores[idx]}/10\n"
                    f"PROBLEMS: sentences over 13 words, vague quantities, forbidden phrases\n"
                    f"FORBIDDEN: {forb_str}\n\n"
                    f"RULES:\n"
                    f"- Maximum 13 words per sentence. Every sentence.\n"
                    f"- Every number must be specific (not 'many' but '47').\n"
                    f"- Zero markdown. Zero AI filler phrases.\n"
                    f"- More visceral and specific than the original.\n"
                    f"- Target: {sdef_target} words (±15% acceptable).\n\n"
                    f"ORIGINAL STAGE:\n{stage_texts[idx]}\n\n"
                    f"Write the improved version now:"
                )
                new_stage = ai_generate(rewrite_p, tokens=2000)
                if new_stage:
                    new_stage = strip_md(new_stage)
                    if len(new_stage.split()) > 30:
                        script = script.replace(stage_texts[idx], new_stage, 1)
                        log(f"  Stage {sdef_name} rewritten ({stage_scores[idx]}/10 → improved)")

            wc         = len(script.split())
            violations = len(re.findall(r"[#*_`\[\]{}<>\\]", script))
            log(f"  After targeted rewrite: {wc}w | {violations} violations")
        except Exception as e:
            log(f"  Stage rewrite (non-fatal): {e}")

    # Step 5: CTA injection
    if len(script.split()) >= 400:
        script = _inject_ctas_ch1(script, niche["name"])
        wc     = len(script.split())
        log(f"  CTAs injected — final: {wc}w")

    return {"script": script, "words": wc, "violations": violations}


def _inject_ctas_ch1(script_clean, niche_name):
    """
    Inject subscribe CTAs at 30%/60%/80% marks for Ch1 (BetrayalDeepDive).
    Uses sentence boundary detection so CTAs never split mid-sentence.
    """
    words = script_clean.split()
    total = len(words)
    if total < 400:
        return script_clean

    cta_pool = {
        "dark_horror": {
            "30pct": ["Subscribe to BetrayalDeepDive. The worst part is thirty seconds away.",
                      "If what you just heard disturbed you, subscribe. There is more."],
            "60pct": ["Subscribe now. What comes next is why this channel exists.",
                      "Subscribe to BetrayalDeepDive before the next revelation."],
            "80pct": ["Subscribe. New investigation every weekday.",
                      "Subscribe to BetrayalDeepDive if you want the rest of them."],
        },
        "seduction_dark": {
            "30pct": ["Subscribe. The psychology behind this gets darker from here.",
                      "Subscribe to BetrayalDeepDive. The pattern you are seeing repeats."],
            "60pct": ["Subscribe before the mechanism is fully revealed.",
                      "Subscribe to BetrayalDeepDive. The next section changes the whole story."],
            "80pct": ["Subscribe. The final layer is thirty seconds away.",
                      "Subscribe to BetrayalDeepDive — new case every weekday."],
        },
        "psychological_trap": {
            "30pct": ["Subscribe. The trap is about to be fully visible.",
                      "Subscribe to BetrayalDeepDive. Every step was deliberate."],
            "60pct": ["Subscribe before the final mechanism is shown.",
                      "Subscribe to BetrayalDeepDive. What is documented next changes everything."],
            "80pct": ["Subscribe. Every weekday. A new case that redefines what you thought you knew.",
                      "Subscribe to BetrayalDeepDive if you want the forty-seven other cases."],
        },
        "supernatural_real": {
            "30pct": ["Subscribe. The documented evidence arrives in thirty seconds.",
                      "Subscribe to BetrayalDeepDive. The explanation is not what you expect."],
            "60pct": ["Subscribe before the final evidence is shown.",
                      "Subscribe to BetrayalDeepDive. This is the part that has no rational explanation."],
            "80pct": ["Subscribe. What was documented here has never been explained.",
                      "Subscribe to BetrayalDeepDive — new investigation every weekday."],
        },
        "obsession_dark": {
            "30pct": ["Subscribe. The escalation documented next is why this case is different.",
                      "Subscribe to BetrayalDeepDive. Every detail here was deliberate."],
            "60pct": ["Subscribe before the final revelation.",
                      "Subscribe to BetrayalDeepDive. The next sixty seconds reframe everything."],
            "80pct": ["Subscribe. New case every weekday. You will not regret it.",
                      "Subscribe to BetrayalDeepDive if you want to understand what drove this."],
        },
    }
    pool  = cta_pool.get(niche_name, cta_pool["dark_horror"])
    seed  = abs(hash(script_clean[:80])) % 2
    c30   = pool["30pct"][seed]
    c60   = pool["60pct"][seed]
    c80   = pool["80pct"][seed]

    def nearest_boundary(words, target, window=25):
        for delta in range(window):
            for d in [1, -1]:
                idx = target + delta * d
                if 0 <= idx < len(words):
                    if words[idx].rstrip().endswith((".", "?", "!")):
                        return idx + 1
        return target

    b80 = nearest_boundary(words, int(total * 0.80))
    b60 = nearest_boundary(words, int(total * 0.60))
    b30 = nearest_boundary(words, int(total * 0.30))

    w = words[:]
    w.insert(b80, f"\n\n{c80}\n\n")
    w.insert(b60, f"\n\n{c60}\n\n")
    w.insert(b30, f"\n\n{c30}\n\n")
    return re.sub(r'\n{3,}', '\n\n', " ".join(w)).strip()

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
IMPORTANT: Start with a NUMBER or specific statistic for highest CTR.
Return ONLY 5 titles, one per line."""
    raw  = ai_generate(prompt, tokens=400)
    best = f"{niche['series']}: {topic[:55]}"
    best_score = 0
    if raw:
        lines = [l.strip() for l in raw.strip().splitlines() if 30 <= len(l.strip()) <= 80]
        def ts(t):
            s = 0
            if 55 <= len(t) <= 70: s += 3
            for hw in hook_words:
                if hw.lower() in t.lower(): s += 2
            if any(c.isdigit() for c in t): s += 3  # number bonus
            return s
        if lines:
            lines.sort(key=ts, reverse=True)
            best       = lines[0]
            best_score = ts(best)

    # Title CTR gate — if best score is low, regenerate with stronger prompt
    if best_score < 7:
        log(f"  Title gate: score {best_score} — regenerating with NUMBER+NOUN prompt...")
        regen = ai_generate(
            f"Generate 5 dark documentary YouTube titles for: {topic}\n"
            f"MUST start with a specific NUMBER (days/victims/years/dollars).\n"
            f"Under 68 chars. Visceral, specific, dark. No generic phrases.\n"
            f"Return 5 titles, one per line.", tokens=300)
        if regen:
            new_lines = [l.strip() for l in regen.splitlines() if 30 <= len(l.strip()) <= 80]
            if new_lines:
                new_lines.sort(key=ts, reverse=True)
                if ts(new_lines[0]) > best_score:
                    best = new_lines[0]
                    log(f"  Title regenerated: {ts(best)} — {best[:55]}")
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
    """
    Generate NUMBER+NOUN thumbnail text — the highest CTR format in dark documentary.
    Examples: "4,380 DAYS"  "14 VICTIMS"  "ONE LETTER"  "$2.4M GONE"  "7 WITNESSES"
    The specific number creates believability. The noun creates visceral impact.
    Both together create a loop the viewer must close by watching.
    """
    words  = script.split()
    # Sample key sections of script for numbers and nouns
    sample = " ".join(words[:80]) + " " + " ".join(words[int(len(words)*0.4):int(len(words)*0.6)])
    sample = sample[:1000]
    prompt = f"""From this documentary narration, generate thumbnail text following the NUMBER+NOUN format.

This format drives the highest click-through rates in dark documentary YouTube:
- A SPECIFIC NUMBER (exact, real-feeling: days, victims, years, dollars, witnesses, documents)
- A POWERFUL NOUN (visceral, specific to the case)
- 2-4 words total, ALL CAPS

EXAMPLES OF HIGH-CTR FORMAT:
"4,380 DAYS" | "14 VICTIMS" | "ONE LETTER" | "$2.4M GONE" | "7 WITNESSES"
"17 YEARS" | "3 BODIES" | "ONE ENVELOPE" | "23 ACCOUNTS" | "48 HOURS"

AVOID generic phrases like "SOMETHING WRONG" or "DARK TRUTH" — these have low CTR.
The number must come from or be inspired by the actual content below.

NARRATION EXCERPT:
{sample}

Return ONLY the 2-4 word phrase in ALL CAPS. Nothing else."""
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
    # Build SEO hook for first 100 chars (shown in YouTube search results)
    # Format: [SPECIFIC CLAIM]. [EMOTIONAL HOOK]. Full investigation below.
    seo_hooks = {
        "dark_horror":        f"DOCUMENTED: {topic[:45]}.",
        "seduction_dark":     f"EXPOSED: {topic[:45]}.",
        "psychological_trap": f"CLASSIFIED: {topic[:45]}.",
        "supernatural_real":  f"EVIDENCE: {topic[:45]}.",
        "obsession_dark":     f"DOCUMENTED: {topic[:45]}.",
    }
    seo_first_line = seo_hooks.get(niche["name"], f"INVESTIGATION: {topic[:55]}.")

    raw = ai_generate(prompt, tokens=1000)
    # v12: three-channel cross-promo in every description
    cross_promo = (
        "\n\n🔬 Forensic crime investigations: youtube.com/@TheEvidenceRoom"
        "\n🧠 Mass manipulation & propaganda: youtube.com/@TheControlFiles"
        "\n\n📺 New investigation every weekday on all three channels."
    )
    if raw:
        desc  = seo_first_line + "\n\n" + strip_md(raw)
        desc += cross_promo
        desc += "\n\n⚠️ This video features AI-assisted narration and editing."
        return desc
    return (f"{title}\n\nEpisode {episode} of {niche['series']}.\n\n"
            f"{chapters_text}\n\n"
            f"Subscribe for new investigations every week.\n\n"
            f"#{niche['name'].replace('_', '')} #documentary #investigation"
            f"{cross_promo}\n\n"
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
            # edge-tts SubMaker API varies by version
            try:
                subs_text = sub.generate_subs()
            except TypeError:
                subs_text = getattr(sub, 'generate_subs', None)
                if callable(subs_text):
                    subs_text = subs_text()
            sf.write(subs_text if isinstance(subs_text, str) else "WEBVTT\n")
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
def inject_ssml_rate(script):
    """
    Split script into 7 stages by word proportion and inject
    SSML prosody rate markers. Edge-tts supports rate parameter
    but not inline SSML. Instead we split the audio into segments
    with different rates and concatenate.
    Returns list of (text_segment, rate_string) tuples.
    """
    words = script.split()
    total = len(words)
    # Stage word boundaries (proportional to STAGE_WORDS)
    stage_rates = [
        (100,  "-5%"),   # Cold open: urgent, attention-grabbing
        (200,  "-8%"),   # The Before: normal documentary pace
        (250,  "-8%"),   # First Signals: measured, building
        (400,  "-5%"),   # Escalation: faster, momentum
        (200,  "-12%"),  # False Resolution: slow, relief
        (650,  "-18%"),  # Real Reveal: devastatingly slow
        (200,  "-10%"),  # Implication + CTA: deliberate
    ]
    segments = []
    idx = 0
    for word_count, rate in stage_rates:
        end = min(idx + word_count, total)
        segment = " ".join(words[idx:end])
        if segment.strip():
            segments.append((segment, rate))
        idx = end
        if idx >= total:
            break
    # Any remaining words go to last rate
    if idx < total:
        remaining = " ".join(words[idx:])
        if remaining.strip():
            segments.append((remaining, "-10%"))
    return segments

async def _edge_tts_segment(text, voice, rate, path):
    """Generate audio for one segment with a specific rate."""
    import edge_tts
    comm = edge_tts.Communicate(text=text, voice=voice, rate=rate)
    await comm.save(path)

def run_audio_with_ssml(script, niche_name, edge_voice):
    """
    Multi-rate audio: split script into 7 stage segments,
    generate each with its own delivery rate, concatenate via FFmpeg.
    Produces audio that sounds like a real documentary narrator.
    """
    segments = inject_ssml_rate(script)
    log(f"  SSML segments: {len(segments)} at rates {[r for _,r in segments]}")

    part_paths = []
    for i, (text, rate) in enumerate(segments):
        part_path = str(WORK_DIR / f"audio_seg_{i}.mp3")
        voices_to_try = [edge_voice, "en-GB-RyanNeural", "en-US-BrianNeural"]
        for v in voices_to_try:
            try:
                asyncio.run(_edge_tts_segment(text, v, rate, part_path))
                if Path(part_path).exists() and Path(part_path).stat().st_size > 5000:
                    part_paths.append(part_path)
                    break
            except Exception as e:
                log(f"    Segment {i} {v}: {e}")
        else:
            log(f"  Segment {i} failed all voices — skipping")

    if not part_paths:
        return None, 0.0

    if len(part_paths) == 1:
        import shutil
        out = str(WORK_DIR / "narration.mp3")
        shutil.copy(part_paths[0], out)
        return out, get_media_duration(out)

    # Concatenate all segments
    list_file = str(WORK_DIR / "seg_list.txt")
    with open(list_file, "w") as f:
        for p in part_paths:
            f.write(f"file '{p}'\n")
    out = str(WORK_DIR / "narration.mp3")
    run_ffmpeg(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", list_file, "-c", "copy", out], label="ssml-concat")
    duration = get_media_duration(out)
    log(f"  SSML audio: {duration:.1f}s ({duration/60:.1f} min)")
    return out, duration

def run_audio_stage(script, niche_name, edge_voice):
    audio_path = str(WORK_DIR / "narration.mp3")
    vtt_path   = str(WORK_DIR / "captions.vtt")
    ass_path   = str(WORK_DIR / "captions.ass")
    has_ass    = False

    log(f"  Words: {len(script.split())} | ElevenLabs: {'yes' if ELEVENLABS_KEY else 'no'}")

    # Try ElevenLabs premium voice first
    el_ok = call_elevenlabs(script, niche_name, audio_path)

    if el_ok:
        pass  # ElevenLabs doesn't support SSML rate — use as-is
    else:
        # Try SSML multi-rate audio (7 delivery speeds across 7 stages)
        log("  Trying SSML dynamic-rate audio...")
        ssml_path, ssml_dur = run_audio_with_ssml(script, niche_name, edge_voice)
        if ssml_path and ssml_dur > 60:
            import shutil
            shutil.copy(ssml_path, audio_path)
            duration = ssml_dur
            log(f"  SSML audio OK: {duration:.1f}s")
            return audio_path, duration, None

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

    # Apply documentary-grade audio post-processing
    processed_path = str(WORK_DIR / "narration_processed.mp3")
    audio_path = apply_audio_post_processing(audio_path, processed_path, niche_name=niche_name)

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

def get_stage_matched_video(niche, script, audio_duration):
    """
    Stage-matched footage: extract keywords from each script stage,
    search Pixabay for matching dark footage, concatenate 7 clips.
    Falls back to single looped video if this fails.
    """
    words     = script.split()
    total     = len(words)
    # Stage boundaries (proportional)
    stage_defs = [
        (100,  "dark discovery opening"),
        (200,  "ordinary life before dark"),
        (250,  "warning signs shadows"),
        (400,  "dark escalation danger"),
        (200,  "calm relief break"),
        (650,  "dark revelation truth exposed"),
        (200,  "dark aftermath consequences"),
    ]
    stage_clips = []
    idx = 0
    stage_dur   = audio_duration / len(stage_defs)

    for i, (word_count, base_kw) in enumerate(stage_defs):
        end        = min(idx + word_count, total)
        stage_text = " ".join(words[idx:end]).lower()
        idx        = end

        # Extract 2 most relevant nouns from stage text
        # Simple approach: most common non-stopwords
        stopwords  = {"the","a","an","and","or","but","in","on","at","to","for",
                      "of","with","by","from","this","that","was","were","had","have",
                      "it","its","he","she","they","their","his","her","be","been",
                      "not","no","so","as","if","then","than","when","what","who"}
        stage_words= [w.strip(".,!?;:") for w in stage_text.split()
                      if len(w) > 4 and w not in stopwords]
        from collections import Counter
        top_nouns  = [w for w,_ in Counter(stage_words).most_common(2)]
        kw         = " ".join(top_nouns[:1]) + " " + base_kw if top_nouns else base_kw

        clip_path  = str(WORK_DIR / f"stage_{i}.mp4")
        log(f"  Stage {i+1} footage: '{kw[:40]}'")

        # Try Pixabay then Pexels
        downloaded = False
        for search_kw in [kw, base_kw, BG_KEYWORDS.get(niche["name"], ["dark shadows"])[i % 3]]:
            try:
                if not PIXABAY_KEY: break
                r = requests.get("https://pixabay.com/api/videos/",
                    params={"key": PIXABAY_KEY, "q": search_kw, "per_page": 5,
                            "video_type": "film", "orientation": "horizontal"}, timeout=15)
                if r.status_code == 200 and r.json().get("hits"):
                    hit = max(r.json()["hits"], key=lambda h: h.get("duration", 0))
                    url = hit["videos"]["medium"]["url"]
                    with requests.get(url, timeout=45, stream=True) as dl:
                        dl.raise_for_status()
                        with open(clip_path, "wb") as f:
                            for chunk in dl.iter_content(32768): f.write(chunk)
                    if Path(clip_path).exists() and Path(clip_path).stat().st_size > 50000:
                        downloaded = True; break
            except Exception as e:
                log(f"    Stage {i+1} Pixabay: {e}")

        if not downloaded:
            # Generate black clip as fallback
            dur = max(int(stage_dur), 8)
            run_ffmpeg(["ffmpeg","-y","-f","lavfi",
                f"-i","color=c=black:size=1280x720:rate=24:duration={dur}",
                "-c:v","libx264","-pix_fmt","yuv420p", clip_path],
                label=f"stage-{i}-fallback")

        if Path(clip_path).exists():
            stage_clips.append((clip_path, stage_dur))

    if len(stage_clips) < 3:
        log("  Stage footage insufficient — falling back to single looped video")
        return None

    # Concatenate all stage clips scaled/padded to 1280x720
    parts = []
    for i, (clip, dur) in enumerate(stage_clips):
        scaled = str(WORK_DIR / f"stage_{i}_scaled.mp4")
        run_ffmpeg(["ffmpeg","-y","-i",clip,
            "-vf","scale=1280:720:force_original_aspect_ratio=decrease,"
                  "pad=1280:720:(ow-iw)/2:(oh-ih)/2",
            "-t",str(dur),"-c:v","libx264","-preset","ultrafast",
            "-pix_fmt","yuv420p","-an", scaled], label=f"scale-{i}")
        if Path(scaled).exists():
            parts.append(scaled)

    if not parts:
        return None

    list_file = str(WORK_DIR / "stage_list.txt")
    combined  = str(WORK_DIR / "background_staged.mp4")
    with open(list_file, "w") as f:
        # Repeat to cover full duration
        loops = max(1, int(audio_duration / (len(parts) * 8)) + 2)
        for _ in range(loops):
            for p in parts: f.write(f"file '{p}'\n")

    run_ffmpeg(["ffmpeg","-y","-f","concat","-safe","0","-i",list_file,
                "-c","copy","-t",str(audio_duration+5),combined], label="stage-concat")
    if Path(combined).exists() and Path(combined).stat().st_size > 50000:
        log(f"  Stage-matched video: {Path(combined).stat().st_size//(1024*1024)}MB")
        return combined
    return None

def get_background_video(niche, audio_duration, script=""):
    # Try stage-matched footage first (7 clips matching 7 script stages)
    if script:
        staged = get_stage_matched_video(niche, script, audio_duration)
        if staged: return staged
        log("  Stage-matched failed — using single keyword search")

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


def apply_audio_post_processing(input_path, output_path, niche_name=None):
    """
    Niche-specific documentary-grade audio processing via FFmpeg.
    Uses NICHE_AUDIO_PROFILES to select the right EQ chain per niche.
    Falls back to default chain if niche not found.
    """
    try:
        af = NICHE_AUDIO_PROFILES.get(niche_name,
            # Default: warm documentary — broad appeal
            "equalizer=f=80:width_type=o:width=2:g=3,"
            "equalizer=f=2500:width_type=o:width=2:g=2,"
            "equalizer=f=8000:width_type=o:width=2:g=-3,"
            "aecho=0.8:0.85:40:0.25,"
            "acompressor=threshold=-18dB:ratio=3:attack=5:release=80:makeup=2dB,"
            "loudnorm=I=-16:LRA=11:TP=-1.5"
        )
        run_ffmpeg([
            "ffmpeg", "-y", "-i", input_path,
            "-af", af,
            "-c:a", "mp3", "-q:a", "2", output_path
        ], label=f"audio-{niche_name or 'default'}", timeout=300)

        if Path(output_path).exists() and Path(output_path).stat().st_size > 500000:
            log(f"  Audio post-processed ({niche_name}): {Path(output_path).stat().st_size//(1024*1024)}MB")
            return output_path
    except Exception as e:
        log(f"  Audio processing failed (non-fatal): {e}")
    return input_path


# ── Niche-specific audio profiles ────────────────────────────
# Each niche has a unique emotional target requiring different EQ/dynamics.
NICHE_AUDIO_PROFILES = {
    "dark_horror": (
        # Deep physical dread — heavy bass, cavernous reverb, dark tone
        "equalizer=f=60:width_type=o:width=2:g=5,"
        "equalizer=f=2500:width_type=o:width=2:g=2,"
        "equalizer=f=10000:width_type=o:width=2:g=-4,"
        "aecho=0.85:0.88:80:0.55,"              # long cavernous reverb
        "acompressor=threshold=-18dB:ratio=4:attack=3:release=100:makeup=3dB,"
        "loudnorm=I=-16:LRA=11:TP=-1.5"
    ),
    "seduction_dark": (
        # Intimate and warm — close-mic feel, barely any reverb
        "equalizer=f=100:width_type=o:width=2:g=4,"
        "equalizer=f=200:width_type=o:width=2:g=3,"
        "equalizer=f=8000:width_type=o:width=2:g=-4,"
        "aecho=0.7:0.75:25:0.15,"               # barely noticeable warmth
        "acompressor=threshold=-15dB:ratio=2.5:attack=8:release=60:makeup=2dB,"
        "loudnorm=I=-16:LRA=11:TP=-1.5"
    ),
    "psychological_trap": (
        # Dry and clinical — no reverb, tight compression, analytical voice
        "equalizer=f=300:width_type=o:width=2:g=-2,"
        "equalizer=f=3000:width_type=o:width=2:g=3,"
        "equalizer=f=8000:width_type=o:width=2:g=-2,"
        # No aecho — completely dry, clinical, no escape
        "acompressor=threshold=-15dB:ratio=4:attack=3:release=40:makeup=3dB,"
        "loudnorm=I=-16:LRA=8:TP=-1.5"          # tighter range = more controlled
    ),
    "supernatural_real": (
        # Wide ethereal space — large reverb, bass depth, mysterious
        "equalizer=f=80:width_type=o:width=2:g=4,"
        "equalizer=f=2000:width_type=o:width=2:g=2,"
        "equalizer=f=12000:width_type=o:width=2:g=-3,"
        "aecho=0.8:0.88:100:0.5,"               # wide supernatural space
        "acompressor=threshold=-20dB:ratio=3:attack=5:release=120:makeup=2dB,"
        "loudnorm=I=-16:LRA=13:TP=-1.5"         # wider dynamics = more uncanny
    ),
    "obsession_dark": (
        # Intimate obsessive — no reverb, maximum presence, suffocating
        "equalizer=f=200:width_type=o:width=2:g=5,"
        "equalizer=f=400:width_type=o:width=2:g=3,"
        "equalizer=f=8000:width_type=o:width=2:g=-5,"
        # No echo — obsession has no space, no distance
        "acompressor=threshold=-12dB:ratio=5:attack=2:release=30:makeup=4dB,"
        "loudnorm=I=-18:LRA=7:TP=-1.5"          # quieter, more intimate
    ),
}
DEFAULT_AUDIO_PROFILE = NICHE_AUDIO_PROFILES["dark_horror"]

# Dark footage keywords for standalone Shorts per niche
NICHE_SHORT_KEYWORDS = {
    "dark_horror":        "dark abandoned shadow horror atmospheric",
    "seduction_dark":     "dark silhouette shadow noir dramatic",
    "psychological_trap": "dark corridor psychology shadow mind",
    "supernatural_real":  "dark fog mysterious night paranormal",
    "obsession_dark":     "dark surveillance shadow night watching",
}

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

def create_outro(series_name="Dark Hours", episode_num=1):
    """
    8-second end screen outro with visual end screen:
    - 0-3s: SUBSCRIBE CTA with series name
    - 3-8s: NEXT INVESTIGATION card pointing to channel
    Revenue driver: end screens are responsible for 15-30% of subscriber conversions.
    """
    path = str(WORK_DIR / "outro.mp4")
    run_ffmpeg([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=black:size=1280x720:rate=24:duration=8",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo:duration=8",
        "-vf",
        # Layer 1: Background pulse (red border)
        "drawbox=x=0:y=0:w=iw:h=ih:color=red@0.3:t=4,"
        # Layer 2: Series name (top)
        "drawtext=text='SUBSCRIBE TO " + series_name.upper() + "':fontsize=38:"
        "fontcolor=red:x=(w-text_w)/2:y=80:enable='between(t,0,8)',"
        # Layer 3: Bell icon substitute text
        "drawtext=text='🔔 NEW INVESTIGATION EVERY WEEKDAY':fontsize=28:"
        "fontcolor=white:x=(w-text_w)/2:y=160:enable='between(t,0,8)',"
        # Layer 4: End screen card (appears at 3s)
        "drawbox=x=780:y=200:w=460:h=260:color=red@0.8:t=fill:"
        "enable='between(t,3,8)',"
        "drawbox=x=780:y=200:w=460:h=260:color=white:t=3:"
        "enable='between(t,3,8)',"
        "drawtext=text='NEXT':fontsize=32:fontcolor=white:"
        "x=850:y=230:enable='between(t,3,8)',"
        "drawtext=text='INVESTIGATION':fontsize=28:fontcolor=white:"
        "x=800:y=275:enable='between(t,3,8)',"
        "drawtext=text='→':fontsize=48:fontcolor=red:"
        "x=940:y=310:enable='between(t,3,8)',"
        # Layer 5: Subscribe button card
        "drawbox=x=40:y=200:w=420:h=120:color=red@0.9:t=fill:"
        "enable='between(t,3,8)',"
        "drawtext=text='SUBSCRIBE':fontsize=48:fontcolor=white:"
        "x=90:y=235:enable='between(t,3,8)',"
        # Layer 6: Episode counter
        "drawtext=text='Investigation #" + str(episode_num) + "':fontsize=26:"
        "fontcolor=gray:x=40:y=H-60:enable='between(t,0,8)'",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", path
    ], label="outro-endscreen")
    return path

def concat_parts(parts, output_path):
    existing = [p for p in parts if p and Path(p).exists()]
    lst = str(WORK_DIR / "concat.txt")
    with open(lst, "w") as f:
        for p in existing: f.write(f"file '{p}'\n")
    run_ffmpeg(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", lst, "-c", "copy", output_path], label="concat")
    return output_path




def run_stage_with_retry(stage_fn, stage_name, *args, max_attempts=3, **kwargs):
    """
    Run a pipeline stage with up to 3 attempts before escalating.
    Handles transient failures (network timeouts, temp API errors)
    in under 2 minutes instead of triggering the 2-hour full-pipeline retry.
    """
    last_err = None
    for attempt in range(1, max_attempts + 1):
        try:
            result = stage_fn(*args, **kwargs)
            if attempt > 1:
                log(f"  Stage {stage_name}: OK on attempt {attempt}")
            return result
        except Exception as e:
            last_err = e
            if attempt < max_attempts:
                log(f"  Stage {stage_name} attempt {attempt}/{max_attempts} failed: {e}")
                log(f"  Retrying in 30s...")
                time.sleep(30)
            else:
                log(f"  Stage {stage_name} FAILED after {max_attempts} attempts: {e}")
    raise RuntimeError(f"Stage {stage_name} failed after {max_attempts} attempts: {last_err}")

def load_weekly_strategy():
    """
    Read the strategy file written by weekly_report.py every Sunday.
    Injects competitor intelligence and recommended topics into script generation.
    Returns strategy context string or empty string if not available.
    """
    strategy_file = SCRIPT_DIR / "next_week_strategy.json"
    try:
        if strategy_file.exists():
            data = json.loads(strategy_file.read_text())
            # Only use if generated this week
            generated = data.get("generated_date", "")
            if generated:
                gen_date = datetime.date.fromisoformat(generated)
                days_old = (datetime.date.today() - gen_date).days
                if days_old <= 7:
                    lines = ["COMPETITOR INTELLIGENCE FROM THIS WEEK:"]
                    topics = data.get("recommended_topics", [])
                    if topics:
                        lines.append("Recommended topics based on competitor gaps:")
                        for t in topics[:3]:
                            lines.append(f"  - {t}")
                    hook_fmt = data.get("winning_hook_format", "")
                    if hook_fmt:
                        lines.append(f"Winning hook format: {hook_fmt}")
                    top_titles = data.get("top_competitor_titles", [])
                    if top_titles:
                        lines.append("Top competitor titles this week:")
                        for t in top_titles[:4]:
                            lines.append(f"  - {t}")
                    return "\n".join(lines)
    except Exception as e:
        log(f"  Strategy load (non-fatal): {e}")
    return ""


def select_best_voice(state, niche_name, available_voices):
    """
    After 5 episodes in a niche, lock in the voice that has produced
    the highest average scores. Viewers build a relationship with THE voice.
    Before 5 episodes: rotate to gather data.
    """
    perf = state.get("performance", {})
    niche_episodes = [ep for ep in state.get("episode_history", [])
                      if ep.get("niche") == niche_name]
    if len(niche_episodes) < 5:
        # Not enough data — rotate voices for data gathering
        ep_count = len(niche_episodes)
        voice = available_voices[ep_count % len(available_voices)]
        log(f"  Voice (gathering data, ep {ep_count+1}/5): {voice}")
        return voice

    # Score each available voice by average episode score
    voice_scores = {}
    for ep in niche_episodes:
        ep_ep = ep.get("episode", 0)
        # Find voice from performance tracker
        for key, val in perf.items():
            if key.startswith("voice_") and isinstance(val, dict):
                v_name = key.replace("voice_", "")
                if v_name in available_voices:
                    scores = val.get("scores", [])
                    if scores:
                        voice_scores[v_name] = sum(scores) / len(scores)

    if voice_scores:
        best = max(voice_scores, key=voice_scores.get)
        log(f"  Voice (locked — best avg {voice_scores[best]:.1f}/10): {best}")
        return best

    # Fallback to first voice
    return available_voices[0]

def load_pattern_memory(state):
    """
    Load the top-performing script patterns from state.json.
    Used to inform the next script generation with what actually worked.
    """
    history = state.get("episode_history", [])
    if not history: return ""
    # Sort by score, take top 5
    top = sorted(history, key=lambda x: x.get("score", 0), reverse=True)[:5]
    if not top: return ""
    lines = ["WHAT HAS WORKED BEST FOR THIS CHANNEL (use as inspiration):"]
    for ep in top:
        lines.append(f"  Score {ep.get('score',0)}/10: {ep.get('topic','')[:80]}")
        lines.append(f"    Hook: {ep.get('hook_type','')}")
        lines.append(f"    Cold open style: {ep.get('cold_open_style','')}")
    return "\n".join(lines)

def save_pattern_memory(state, episode, niche_name, topic, score,
                        hook_type="", cold_open_style=""):
    """Store this episode's pattern data for future learning."""
    history = state.get("episode_history", [])
    history.append({
        "episode":         episode,
        "niche":           niche_name,
        "topic":           topic[:100],
        "score":           score,
        "hook_type":       hook_type,
        "cold_open_style": cold_open_style,
        "date":            datetime.datetime.now().strftime("%Y-%m-%d"),
    })
    state["episode_history"] = history[-50:]  # keep last 50 episodes
    return state

# ================================================================
# THUMBNAIL  [NEW #9 — dynamic text from script]
# ================================================================

def get_thumbnail_style(state, episode):
    """
    A/B thumbnail testing — alternate between 2 styles.
    Style A: Blood red text on AI-generated dark background (weeks 1,3,5...)
    Style B: White text with strong glow on darker AI background (weeks 2,4,6...)
    Weekly report will identify which drives better CTR.
    """
    week_number = datetime.datetime.now().isocalendar()[1]
    style       = "A" if week_number % 2 == 1 else "B"
    state.setdefault("thumbnail_ab", {})
    state["thumbnail_ab"]["last_style"]   = style
    state["thumbnail_ab"]["last_episode"] = episode
    log(f"  Thumbnail style: {style} (week {week_number})")
    return style


def fetch_case_relevant_image(topic, niche_name, out_path):
    """
    Search for a REAL case-relevant image using Pixabay/Pexels photo APIs.
    These keys are already set — zero additional cost.

    Priority:
    1. Pixabay photos (topic-specific search)
    2. Pexels photos (topic-specific search)
    3. Pollinations.ai (AI-generated atmospheric, free fallback)

    A real case-relevant image drives 2-3× higher CTR vs generic dark backgrounds
    because it creates immediate visual context for what the video covers.
    """
    # Extract 2-3 most specific keywords from topic for image search
    stopwords = {"a","an","the","and","or","but","in","on","at","to","for",
                 "of","with","by","from","this","that","was","were","had",
                 "have","it","he","she","they","who","what","when","how"}
    topic_words = [w.strip(".,!?-") for w in topic.lower().split()
                   if len(w) > 3 and w not in stopwords]
    search_kw = " ".join(topic_words[:3])

    # Niche visual modifiers — add context to make images darker/more relevant
    niche_mod = {
        "dark_horror":        "dark shadow dramatic",
        "seduction_dark":     "shadow silhouette mystery",
        "psychological_trap": "dark corridor abstract",
        "supernatural_real":  "mysterious dark atmospheric",
        "obsession_dark":     "shadow watching dark",
    }
    mod = niche_mod.get(niche_name, "dark dramatic")
    full_query = f"{search_kw} {mod}"

    # Try Pixabay photos first
    if PIXABAY_KEY:
        try:
            r = requests.get("https://pixabay.com/api/",
                params={"key": PIXABAY_KEY, "q": full_query,
                        "image_type": "photo", "orientation": "horizontal",
                        "min_width": 1280, "safesearch": "true",
                        "per_page": 5, "order": "popular"},
                timeout=15)
            if r.status_code == 200 and r.json().get("hits"):
                hit = r.json()["hits"][0]
                img_url = hit.get("webformatURL") or hit.get("largeImageURL")
                if img_url:
                    ir = requests.get(img_url, timeout=30)
                    if ir.status_code == 200 and len(ir.content) > 20000:
                        with open(out_path, "wb") as f:
                            f.write(ir.content)
                        log(f"  Case image (Pixabay): {search_kw}")
                        return True, "photo"
        except Exception as e:
            log(f"  Pixabay photo (non-fatal): {e}")

    # Try Pexels photos
    if PEXELS_KEY:
        try:
            r = requests.get("https://api.pexels.com/v1/search",
                headers={"Authorization": PEXELS_KEY},
                params={"query": full_query, "per_page": 5,
                        "orientation": "landscape", "size": "large"},
                timeout=15)
            if r.status_code == 200 and r.json().get("photos"):
                photo = r.json()["photos"][0]
                img_url = photo.get("src", {}).get("large2x") or photo.get("src", {}).get("large")
                if img_url:
                    ir = requests.get(img_url, timeout=30)
                    if ir.status_code == 200 and len(ir.content) > 20000:
                        with open(out_path, "wb") as f:
                            f.write(ir.content)
                        log(f"  Case image (Pexels): {search_kw}")
                        return True, "photo"
        except Exception as e:
            log(f"  Pexels photo (non-fatal): {e}")

    # Fallback: Pollinations AI-generated atmospheric
    import urllib.parse
    prompt = (f"{search_kw} {mod} ultra dark atmospheric cinematic "
              f"documentary no faces no text 8k dramatic")
    url = (f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}"
           f"?width=1280&height=720&nologo=true&seed={abs(hash(topic)) % 9999}")
    try:
        r = requests.get(url, timeout=45)
        if r.status_code == 200 and len(r.content) > 30000:
            with open(out_path, "wb") as f:
                f.write(r.content)
            log(f"  Case image (Pollinations AI): {search_kw}")
            return True, "ai"
    except Exception as e:
        log(f"  Pollinations (non-fatal): {e}")

    return False, "none"


def composite_thumbnail(bg_path, bg_type, thumb_text, title, ab_style, niche_name):
    """
    v2 thumbnail: three-layer composition using thumbnail_engine_v2.
    Layer 1: background (Pollinations.ai, niche-specific prompt)
    Layer 2: silhouette figure (ab_style A only)
    Layer 3: text with 5-layer shadow stack
    """
    try:
        from thumbnail_engine_v2 import generate_thumbnail_v2
        result = generate_thumbnail_v2(
            title        = title,
            thumb_text   = thumb_text,
            niche_name   = niche_name,
            topic        = title,
            channel_name = "BetrayalDeepDive",
            episode      = 1,
            work_dir     = str(WORK_DIR),
            ab_variant   = ab_style,
        )
        if result and Path(result).exists():
            log(f"  Thumbnail v2: {Path(result).stat().st_size//1024}KB | {ab_style} variant")
            return result
    except Exception as e:
        log(f"  Thumbnail v2 (non-fatal): {e}")
    return None


def fetch_case_relevant_image(topic, niche_name, out_path):
    """Delegate to thumbnail_engine_v2 background fetcher."""
    try:
        from thumbnail_engine_v2 import fetch_background
        import hashlib
        seed = int(hashlib.md5(topic.encode()).hexdigest()[:8], 16) % 99999
        result = fetch_background(topic, niche_name, seed, str(WORK_DIR))
        if result and Path(result).exists():
            import shutil
            shutil.copy(result, out_path)
            return True, "pollinations_v2"
    except Exception as e:
        log(f"  fetch_case_relevant_image (non-fatal): {e}")
    return False, "none"


def fetch_pollinations_image(topic, niche_name, thumb_path):
    """Legacy wrapper — delegates to thumbnail_engine_v2."""
    got, _ = fetch_case_relevant_image(topic, niche_name, thumb_path)
    return got


def generate_thumbnail(thumb_text, niche_name, title, topic="", episode=0):
    """
    Full thumbnail pipeline:
    1. Search for REAL case-relevant image (Pixabay photo → Pexels photo → Pollinations AI)
    2. Composite the image with NUMBER+NOUN text overlay
    3. A/B style (red/white) based on week number
    Case-specific real imagery drives 2-3× higher CTR vs generic backgrounds.
    """
    state    = load_state()
    ab_style = get_thumbnail_style(state, episode)
    save_state(state)

    # Fetch case-relevant image (real photo or AI-generated)
    bg_path = str(WORK_DIR / "thumb_bg.jpg")
    got_image, bg_type = fetch_case_relevant_image(topic or thumb_text, niche_name, bg_path)

    # Composite with NUMBER+NOUN text
    result = composite_thumbnail(
        bg_path if got_image else None,
        bg_type, thumb_text, title, ab_style, niche_name)
    if result:
        return result

    # Final fallback: original Pillow-only method
    thumb_path = str(WORK_DIR / "thumbnail.jpg")
    pol_path   = str(WORK_DIR / "pollinations_bg.jpg")
    got_image  = fetch_pollinations_image(topic or thumb_text, niche_name, pol_path)

    try:
        from PIL import Image, ImageDraw, ImageFont, ImageFilter
        W, H = 1280, 720
        if got_image and Path(pol_path).exists():
            # Use Pollinations AI image as background, darkened
            bg_img = Image.open(pol_path).convert("RGB").resize((W, H))
            # Darken significantly so text remains readable
            from PIL import ImageEnhance
            bg_img = ImageEnhance.Brightness(bg_img).enhance(0.25)
            img = bg_img
        else:
            img = Image.new("RGB", (W, H), (0, 0, 0))
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
            # A/B style colours
            if ab_style == "A":
                shadow_col = (80, 0, 0)
                text_col   = (220, 15, 15)
            else:
                shadow_col = (0, 0, 0)
                text_col   = (255, 255, 255)
            for dx, dy in [(-3,-3),(3,-3),(-3,3),(3,3),(0,-4),(0,4),(-4,0),(4,0)]:
                draw.text((x+dx, y+dy), line, font=fm, fill=shadow_col)
            draw.text((x, y), line, font=fm, fill=text_col)

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
                         "selfDeclaredMadeForKids": False, "madeForKids": False,
                         "containsSyntheticMedia": True}},  # mandatory AI disclosure since Mar 2024
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


def post_creator_comment(token, video_id, niche_name, title, episode):
    """
    Post a creator comment immediately after upload.
    Critical for revenue: early engagement signals boost algorithmic distribution.
    The comment contains SEO keywords, cross-promotion, and a hook question
    that drives replies (more engagement signals).
    """
    niche_hooks = {
        "dark_horror":        "Have you ever been somewhere and felt something was wrong?",
        "seduction_dark":     "Have you ever ignored warning signs because you wanted to believe?",
        "psychological_trap": "Have you ever been manipulated without realising it at the time?",
        "supernatural_real":  "Have you ever had an experience you couldn't rationally explain?",
        "obsession_dark":     "Is there someone in your life whose interest feels like more than it appears?",
    }
    hook = niche_hooks.get(niche_name,
        "What was the detail in this case that disturbed you the most?")
    comment = (
        f"👁️ {hook}\n\n"
        f"Drop your answer below — I read every reply.\n\n"
        f"🔔 Subscribe for a new investigation every weekday\n"
        f"📋 Full case sources in the description\n"
        f"🔎 Evidence Room channel: youtube.com/@TheEvidenceRoom\n\n"
        f"#{niche_name.replace('_','')} #documentary #investigation #episode{episode}"
    )
    try:
        r = requests.post(
            "https://www.googleapis.com/youtube/v3/commentThreads",
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"},
            params={"part": "snippet"},
            json={"snippet": {
                "videoId": video_id,
                "topLevelComment": {"snippet": {"textOriginal": comment}}
            }}, timeout=30)
        if r.status_code == 200:
            log(f"  Creator comment posted OK")
            return r.json()["id"]
        else:
            log(f"  Creator comment {r.status_code} (non-fatal): {r.text[:100]}")
    except Exception as e:
        log(f"  Creator comment (non-fatal): {e}")
    return None

# ================================================================
# v12.0 NEW FUNCTIONS — TRAFFIC & REVENUE MAXIMISATION
# ================================================================

def generate_dedicated_short_title(main_title, short_type, niche_name):
    """
    Generate a dedicated Short title optimised for Shorts algorithm.
    DIFFERENT from the main video title — Shorts have their own discovery.
    Targets: curiosity gap, specific claim, under 60 chars.
    """
    prompts = {
        "teaser": f"Write a YouTube Shorts title that creates maximum curiosity. Topic: {main_title[:80]}. "
                  "Rules: under 55 chars, starts with a shocking fact or question, no 'watch' or 'click'. "
                  "Return ONLY the title.",
        "recap":  f"Write a YouTube Shorts title revealing the key finding. Topic: {main_title[:80]}. "
                  "Rules: under 55 chars, implies the truth was found, feels conclusive. "
                  "Return ONLY the title.",
    }
    type_key = "teaser" if "teaser" in short_type.lower() else "recap"
    try:
        result = ai_generate(prompts[type_key], tokens=80)
        if result:
            title = re.sub(r'[#*_`]', '', result.strip().split("\n")[0].strip())
            if 15 < len(title) < 65:
                log(f"  Short title: {title}")
                return title
    except Exception as e:
        log(f"  Short title (non-fatal): {e}")
    # Fallback: use a hook from the main title
    hooks = {"teaser": "This Is What Nobody Told You", "recap": "The Truth They Didn't Want Found"}
    return hooks.get(type_key, main_title[:50])


def post_short_creator_comment(token, video_id, niche_name, main_title):
    """
    Post a creator comment on each Short immediately after upload.
    Shorts comments drive early engagement signals = algorithmic boost.
    Different from main video comment — Shorts audience is colder.
    """
    short_hooks = {
        "dark_horror":        "Does this happen more than we know?",
        "seduction_dark":     "Have you ever seen these warning signs in real life?",
        "psychological_trap": "Is this happening around you right now?",
        "supernatural_real":  "What is the rational explanation for this?",
        "obsession_dark":     "Do you know someone whose interest feels like this?",
    }
    hook = short_hooks.get(niche_name, "What do you think happened?")
    comment = (
        f"💬 {hook}\n\n"
        f"Full investigation ↑ above.\n"
        f"🔔 New case every weekday → subscribe\n"
        f"🔬 Forensic crimes: youtube.com/@TheEvidenceRoom\n"
        f"🧠 Mass manipulation: youtube.com/@TheControlFiles\n\n"
        f"#{niche_name.replace('_','')} #shorts #documentary"
    )
    try:
        r = requests.post(
            "https://www.googleapis.com/youtube/v3/commentThreads",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            params={"part": "snippet"},
            json={"snippet": {"videoId": video_id,
                              "topLevelComment": {"snippet": {"textOriginal": comment}}}},
            timeout=30)
        if r.status_code == 200:
            log("  Short creator comment OK")
        else:
            log(f"  Short comment {r.status_code} (non-fatal)")
    except Exception as e:
        log(f"  Short comment (non-fatal): {e}")


def build_three_channel_cross_promo(niche_name, is_short=False):
    """
    Build standardised three-channel cross-promotion block.
    Injects in every description — main video AND Shorts.
    Three-channel flywheel: each channel sends viewers to both others.
    """
    if is_short:
        return (
            "\n\n🔬 Full forensic investigations: youtube.com/@TheEvidenceRoom"
            "\n🧠 Mass manipulation exposed: youtube.com/@TheControlFiles"
        )
    return (
        "\n\n🔬 Forensic crime investigations: youtube.com/@TheEvidenceRoom"
        "\n🧠 Mass manipulation & propaganda: youtube.com/@TheControlFiles"
        "\n\n📺 New investigation every weekday on all three channels."
    )


def run_ch1_viral_intelligence(niche):
    """
    Viral intelligence engine for Ch1 (ported from Ch2).
    Runs weekly — results cached in state.json under 'viral_intel'.
    Finds what's working in the dark horror/psychological documentary niche.
    """
    state = load_state()
    intel = state.get("viral_intel", {})
    name  = niche["name"]
    if name in intel:
        try:
            last = datetime.datetime.fromisoformat(intel[name].get("last_run", "2020-01-01"))
            if (datetime.datetime.now() - last).days < 7:
                log(f"  Ch1 viral intel cached ({name})")
                return intel[name]
        except: pass

    log(f"  Running Ch1 viral intelligence: {name}...")
    prompt = f"""Analyze the TOP 20 most viral dark documentary YouTube videos (2M+ views) in the
"{niche['search_query']}" niche.
Return ONLY valid JSON:
{{"top_hook_formulas":["Hook 1","Hook 2","Hook 3"],
"winning_title_patterns":["Pattern 1","Pattern 2","Pattern 3"],
"thumbnail_text_examples":["3 WORD 1","3 WORD 2","3 WORD 3","3 WORD 4","3 WORD 5"],
"retention_hooks":["30pct","60pct","80pct"],
"niche_power_words":["word1","word2","word3","word4","word5","word6"],
"fresh_topic_ideas":["Topic 1","Topic 2","Topic 3","Topic 4","Topic 5","Topic 6"]}}"""
    try:
        text = ai_generate(prompt, tokens=400)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]','', re.sub(r'```json|```','',text).strip())
        m = re.search(r'\{[\s\S]*\}', text)
        if m:
            d = json.loads(m.group())
            d["last_run"] = datetime.datetime.now().isoformat()
            intel[name] = d
            state["viral_intel"] = intel
            save_state(state)
            log("  Ch1 viral intel loaded")
            return d
    except Exception as e:
        log(f"  Ch1 viral intel err: {e}")

    fallback = {
        "top_hook_formulas": niche.get("dread_triggers", [])[:3],
        "winning_title_patterns": ["NUMBER + NOUN format", "The [THING] That Changed Everything"],
        "thumbnail_text_examples": [t.upper() for t in niche.get("topics", [])[:3]],
        "retention_hooks": ["The next detail is the one that changes everything",
                            "What was found at this point made investigators stop",
                            "The final revelation is the one nobody expected"],
        "niche_power_words": ["documented","witnessed","concealed","discovered","classified","permanent"],
        "fresh_topic_ideas": niche.get("topics", []),
        "last_run": datetime.datetime.now().isoformat()
    }
    intel[name] = fallback
    state["viral_intel"] = intel
    save_state(state)
    return fallback


def get_ch1_archive_topic(niche, attempt, used_topics):
    """
    Archive fallback: when fresh topics are exhausted (attempt > 8),
    dig into proven viral stories from 2022-2024.
    """
    prompt = f"""Find 6 documented real-world stories from 2022-2024 that fit
the "{niche['name'].replace('_',' ')}" niche and went viral as documentary YouTube videos.
Focus: {niche['search_query']}
Not already used: {[t[:40] for t in used_topics[:4]]}
Return ONLY a JSON array: ["Story 1","Story 2","Story 3","Story 4","Story 5","Story 6"]"""
    try:
        text = ai_generate(prompt, tokens=400)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]','', re.sub(r'```json|```','',text).strip())
        m = re.search(r'\[[\s\S]*?\]', text)
        if m:
            topics = json.loads(m.group())
            unused = [t for t in topics if t not in used_topics]
            if unused:
                chosen = random.choice(unused)
                log(f"  Archive topic: {chosen[:70]}")
                return chosen
    except Exception as e:
        log(f"  Archive topic err: {e}")
    unused_seeds = [t for t in niche["topics"] if t not in used_topics]
    return random.choice(unused_seeds) if unused_seeds else niche["topics"][0]


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

def run_provider_health_check():
    """
    Tests all AI providers at pipeline startup.
    Fires BEFORE script generation so you see exactly what works.
    Results sent to Telegram so you can see them in the approval gate.
    """
    log("\n" + "="*65)
    log("  AI PROVIDER HEALTH CHECK")
    log("="*65)
    test = "Reply with exactly: OK"
    results = {}

    checks = [
        ("Cerebras",    call_cerebras),
        ("SambaNova",   call_sambanova),
        ("Gemini",      call_gemini),
        ("Groq",        call_groq),
        ("OpenRouter",  call_openrouter),
        ("Cohere",      call_cohere),
        ("Mistral",     call_mistral),
    ]
    working = []
    for name, fn in checks:
        try:
            r = fn(test, tokens=50)
            status = "✅ WORKING" if r else "❌ NO RESPONSE"
            if r: working.append(name)
        except Exception as e:
            status = f"❌ ERROR: {str(e)[:60]}"
        results[name] = status
        log(f"  {name:12s}: {status}")

    log("="*65)

    # Alert to Telegram so Mohammed can see it without checking logs
    status_lines = "\n".join(f"  {n}: {s}" for n, s in results.items())
    if len(working) == 0:
        tg(f"🚨 CRITICAL: ALL AI PROVIDERS FAILED\n{status_lines}\n\nPipeline cannot continue.")
        raise RuntimeError("All AI providers failed health check")
    elif len(working) < 3:
        tg(f"⚠️ Only {len(working)} AI provider(s) working:\n{status_lines}")
    else:
        log(f"  {len(working)}/7 providers working — OK to proceed")

    return working


def generate_ch1_short_script(niche_name, topic, short_num):
    """45-second standalone Short script optimised for Shorts algorithm."""
    angles = {
        0: "the single most psychologically disturbing documented fact",
        1: "the warning sign that was visible but ignored — and what happened next",
    }
    prompt = (
        f"Write a 45-second YouTube Shorts narration script.\n"
        f"Topic: {topic}\nFocus: {angles.get(short_num, angles[0])}\n"
        f"Tone: Dark investigative psychological documentary\n\n"
        f"STRUCTURE:\n"
        f"Line 1 (HOOK 3sec): Specific number/date/fact. Mid-action. No intro.\n"
        f"Lines 2-4 (BUILD 20sec): Three short sentences max 10 words each.\n"
        f"Lines 5-6 (REVEAL 15sec): Most disturbing documented detail.\n"
        f"Line 7 (CTA 5sec): Follow for the full investigation.\n\n"
        f"RULES: 120-130 words total. No markdown. Plain text only."
    )
    result = ai_generate(prompt, tokens=350)
    if result:
        clean = result.strip().replace("**","").replace("##","").replace("*","")
        words = clean.split()
        return " ".join(words[:130]) if len(words) > 132 else clean
    return None

def create_ch1_standalone_short(script, niche_name, short_num, edge_voice):
    """Create standalone Short: dark atmospheric footage + narration. No subtitles."""
    audio_out = str(WORK_DIR / f"ch1_short_audio_{short_num}.mp3")
    try:
        import edge_tts as _edge
        async def _gen():
            comm = _edge.Communicate(text=script, voice=edge_voice, rate="-5%")
            await comm.save(audio_out)
        asyncio.run(_gen())
    except Exception as e:
        log(f"  Short {short_num+1} audio: {e}"); return None

    if not Path(audio_out).exists() or Path(audio_out).stat().st_size < 20000:
        return None

    try:
        import json as _j
        dp = subprocess.run(["ffprobe","-v","quiet","-print_format","json",
                             "-show_streams",audio_out], capture_output=True, text=True)
        dur = 45.0
        for s in _j.loads(dp.stdout).get("streams",[]):
            if s.get("codec_type") == "audio":
                dur = float(s.get("duration", 45.0)); break
    except: dur = 45.0

    kw  = NICHE_SHORT_KEYWORDS.get(niche_name, "dark shadow atmospheric")
    bg  = None
    if PIXABAY_KEY:
        try:
            r = requests.get("https://pixabay.com/api/videos/",
                params={"key": PIXABAY_KEY, "q": kw, "per_page": 3}, timeout=15)
            if r.status_code == 200 and r.json().get("hits"):
                url = r.json()["hits"][0]["videos"]["medium"]["url"]
                bgp = str(WORK_DIR / f"ch1_short_bg_{short_num}.mp4")
                with requests.get(url, timeout=30, stream=True) as dl:
                    with open(bgp, "wb") as f:
                        for chunk in dl.iter_content(32768): f.write(chunk)
                if Path(bgp).exists() and Path(bgp).stat().st_size > 50000:
                    bg = bgp
        except: pass

    out = str(WORK_DIR / f"ch1_standalone_short_{short_num}.mp4")
    if bg:
        # Real footage — vertical crop, darkened, NO subtitles
        run_ffmpeg(["ffmpeg","-y","-stream_loop","-1","-i",bg,"-i",audio_out,
            "-vf","scale=1280:720:force_original_aspect_ratio=decrease,"
                  "pad=1280:720:(ow-iw)/2:(oh-ih)/2,"
                  "crop=405:720:(iw-405)/2:0,scale=1080:1920,"
                  "eq=brightness=-0.3:contrast=1.3",
            "-c:v","libx264","-preset","fast","-crf","22",
            "-pix_fmt","yuv420p","-c:a","aac","-b:a","128k",
            "-t",str(dur+0.3),"-shortest",out],
            label=f"ch1-short-{short_num}", timeout=180)
    else:
        run_ffmpeg(["ffmpeg","-y","-f","lavfi",
            "-i","color=c=black:size=1080x1920:rate=24",
            "-i",audio_out,"-c:v","libx264","-preset","fast","-crf","22",
            "-pix_fmt","yuv420p","-c:a","aac","-b:a","128k",
            "-t",str(dur+0.3),"-shortest",out],
            label=f"ch1-short-fallback-{short_num}", timeout=120)

    if Path(out).exists() and Path(out).stat().st_size > 200000:
        log(f"  Ch1 Short {short_num+1}: {Path(out).stat().st_size//(1024*1024)}MB")
        return out
    return None


def main():
    """
    Two-phase pipeline controller.
    PIPELINE_PHASE=generate : runs script/audio/video/thumbnail, saves pending_upload.json
    PIPELINE_PHASE=upload   : reads pending_upload.json, uploads to YouTube
    PIPELINE_PHASE=full     : legacy single-run mode (backward compatible)
    """
    from phase_manager import (get_pipeline_phase, save_pending,
                                load_pending, clear_pending, check_pending_age,
                                is_already_uploaded)

    phase = get_pipeline_phase()
    log("=" * 70)
    log(f"BETRAYAL DEEPDIVE v14.0 — Phase: {phase.upper()}")
    log(f"Time (IST): {datetime.datetime.now().strftime('%a %d %b %Y %I:%M %p')}")
    log("=" * 70)

    SCRIPT_DIR = Path(__file__).parent
    state = load_state()

    # ══════════════════════════════════════════════════════════
    # UPLOAD PHASE — reads pending_upload.json, uploads, done
    # ══════════════════════════════════════════════════════════
    if phase == "upload":
        pending = load_pending(SCRIPT_DIR)
        if not pending or is_already_uploaded(pending):
            tg("⚠️ Ch1 Upload: no pending video found. Generation may have failed last night.")
            log("No pending upload — exiting.")
            sys.exit(0)

        is_fresh, hours_old = check_pending_age(pending, max_hours=30)
        if not is_fresh:
            tg(f"⚠️ Ch1 Upload: pending video is {hours_old}h old — may be stale. Uploading anyway.")

        log(f"Loading pending video ({hours_old}h old): {pending.get('title','?')[:60]}")
        title       = pending["title"]
        description = pending["description"]
        tags        = pending["tags"]
        niche_name  = pending["niche_name"]
        video_path  = pending["video_path"]
        thumb_path  = pending.get("thumbnail_path","")
        shorts      = pending.get("shorts_clips", [])
        script_clean= pending.get("script_clean","")
        duration    = pending.get("duration", 0)
        score       = pending.get("score", 0)
        edge_voice  = pending.get("voice_used","")
        episode     = pending.get("episode", 1)
        playlist_id = pending.get("playlist_id","")
        short_titles= pending.get("short_titles", {})
        short_cross = pending.get("short_cross", "")

        # Verify video file exists
        if not Path(video_path).exists():
            tg(f"❌ Ch1 Upload FAILED: video file missing at {video_path}")
            sys.exit(1)

        token = get_yt_token()

        # Upload main video
        yt_url, vid_id = run_stage_with_retry(
            upload_yt, "Upload",
            video_path, title, description, tags, token=token)

        if playlist_id:
            add_to_playlist(token, playlist_id, vid_id)

        # Thumbnail
        if thumb_path and Path(thumb_path).exists():
            try:
                with open(thumb_path,"rb") as tf:
                    tr = requests.post(
                        f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set"
                        f"?videoId={vid_id}&uploadType=media",
                        headers={"Authorization":f"Bearer {token}","Content-Type":"image/jpeg"},
                        data=tf.read(), timeout=60)
                if tr.status_code in [200,201]: log("  Thumbnail uploaded")
            except Exception as te: log(f"  Thumbnail (non-fatal): {te}")

        post_creator_comment(token, vid_id, niche_name, title, episode)

        # Upload Shorts
        short_urls = []
        for sd in shorts:
            sp = sd.get("path","")
            if not sp or not Path(sp).exists():
                continue
            try:
                st = short_titles.get(sd.get("type","teaser"), title[:50] + " #Shorts")
                sd_desc = (f"Full investigation above.\n\n{title}\n"
                           f"{short_cross}\n\n#{niche_name.replace('_','')} #shorts")
                su, sid = upload_yt(sp, st, sd_desc, tags[:8], token=token)
                add_to_playlist(token, playlist_id, sid)
                post_short_creator_comment(token, sid, niche_name, title)
                short_urls.append(su)
                log(f"  Short uploaded: {su}")
            except Exception as e:
                log(f"  Short upload (non-fatal): {e}")

        # SRT captions
        if script_clean and duration > 0:
            try:
                from growth_engine import upload_srt_captions
                upload_srt_captions(token, vid_id, script_clean, duration, "betrayal_deepdive")
            except Exception as e:
                log(f"  SRT (non-fatal): {e}")

        update_channel_description(token, title, yt_url)
        clear_pending(SCRIPT_DIR)

        # Save state
        state["last_title"]    = title
        state["last_url"]      = yt_url
        state["last_voice"]    = edge_voice
        state["total_uploads"] = state.get("total_uploads", 0) + 1
        save_state(state)

        # First-hour sprint
        try:
            env_ext = os.environ.copy()
            env_ext.update({
                "GROWTH_ENGINE_MODE":  "sprint",
                "SPRINT_VIDEO_URL":    yt_url,
                "SPRINT_VIDEO_TITLE":  title,
                "SPRINT_CHANNEL_ID":   "betrayal_deepdive",
                "SPRINT_NICHE":        niche_name,
                "SPRINT_SHORTS_URLS":  ",".join(short_urls),
                "SPRINT_SCORE":        str(score),
                "SPRINT_DURATION_SECS":str(duration),
            })
            subprocess.Popen(
                ["python3", str(Path(__file__).parent.parent /
                               "channels/growth_engine/growth_engine.py")],
                env=env_ext)
        except Exception as ge:
            log(f"  Growth engine sprint (non-fatal): {ge}")

        tg(f"✅ <b>BetrayalDeepDive — LIVE</b>\n\n"
           f"<b>{title}</b>\n🔗 {yt_url}\n\n"
           f"Niche: {niche_name} | Score: {score}/10\n"
           f"Ep{episode} | {len(short_urls)} Shorts uploaded\n"
           f"🚀 First-hour sprint active — watch + Hype now")
        log(f"\nUPLOAD COMPLETE: {yt_url}")
        return

    # ══════════════════════════════════════════════════════════
    # GENERATE PHASE (or legacy full mode)
    # ══════════════════════════════════════════════════════════
    episode = state.get("episode_count", 0) + 1
    if not IS_MAKEUP:
        ckpt_clear()

    try:
        token = get_yt_token()

        log("\nSTAGE 1: Script")
        niche_name, niche, topic, script_result, trending_titles = run_stage1(state)
        script_clean = script_result["script"]
        wc           = script_result["words"]
        score_val    = score_result(script_result)[0]
        edge_voice   = pick_voice(niche_name, state)

        tg(f"Ch1 Script ready: {niche_name} | {wc}w | {score_val}/10\n{topic[:80]}")

        # Approval gate
        title_result = run_stage_with_retry(generate_titles, "Titles", niche, topic, episode)
        title        = title_result[0] if title_result else f"{niche['series']} Ep{episode}"

        decision = run_approval_gate(title, niche_name, script_clean, edge_voice, score_val)
        if decision == "rejected":
            log("Rejected by approval gate."); sys.exit(0)

        log("\nSTAGE 3: Audio")
        audio_path, audio_duration, audio_size, voice_used = run_stage_with_retry(
            run_audio_stage, "Audio", script_clean, niche_name, edge_voice)
        edge_voice = voice_used

        log("\nSTAGE 4: Video")
        video_path = run_stage_with_retry(
            assemble_video, "Video", niche_name, audio_path, audio_duration, topic)

        log("\nSTAGE 5: Thumbnail")
        ab_style    = "A" if datetime.datetime.now().isocalendar()[1] % 2 == 1 else "B"
        thumb_text  = generate_thumbnail_text(niche, topic)
        thumb_path  = run_thumbnail_stage(title, thumb_text, niche_name, topic, ab_style, episode)

        log("\nSTAGE 6: Shorts")
        short_title_1 = generate_dedicated_short_title(title, "teaser", niche_name)
        short_title_2 = generate_dedicated_short_title(title, "recap",  niche_name)
        short_cross   = build_three_channel_cross_promo(niche_name, is_short=True)
        shorts = make_both_shorts(video_path, script_clean, audio_duration)

        # Build description
        description = generate_seo_description(
            niche, topic, title, episode,
            generate_chapter_timestamps(script_clean, audio_duration, "betrayal_deepdive"),
            audio_duration)

        # Playlist
        playlist_id = state.get("playlists", {}).get(niche_name)
        if not playlist_id:
            temp_token = get_yt_token()
            playlist_id = ensure_playlist(temp_token, niche_name, niche["series"])
            if playlist_id:
                pl = state.get("playlists", {}); pl[niche_name] = playlist_id
                state["playlists"] = pl

        tags = build_niche_tags(niche_name)

        # Save pending (generate phase ends here)
        save_pending(SCRIPT_DIR, {
            "title":         title,
            "description":   description,
            "tags":          tags,
            "niche_name":    niche_name,
            "video_path":    video_path,
            "audio_path":    audio_path,
            "thumbnail_path":thumb_path or "",
            "script_clean":  script_clean,
            "duration":      audio_duration,
            "score":         score_val,
            "voice_used":    voice_used,
            "episode":       episode,
            "playlist_id":   playlist_id or "",
            "ab_style":      ab_style,
            "shorts_clips":  shorts,
            "short_titles":  {"teaser": short_title_1, "recap": short_title_2},
            "short_cross":   short_cross,
            "topic":         topic,
        })

        state["episode_count"] = episode
        save_state(state)

        if phase == "generate":
            # Find upload time for this channel
            upload_time_msg = "10:30 PM IST (5 PM UTC)"
            tg(f"✅ <b>Ch1 Generated — queued for upload</b>\n\n"
               f"<b>{title}</b>\n"
               f"Niche: {niche_name} | {wc}w | {score_val}/10\n"
               f"Voice: {voice_used} | {audio_duration/60:.1f}min\n"
               f"Uploading at: {upload_time_msg}\n\n"
               f"🎯 Reply CANCEL to abort upload before that time.")
            log(f"\nGENERATE COMPLETE — video queued for upload at {upload_time_msg}")
            return

        # Legacy full mode: upload immediately
        log("\nLEGACY FULL MODE: uploading now...")
        os.environ["PIPELINE_PHASE"] = "upload"
        main()  # re-enter in upload phase

    except Exception as e:
        log(f"\nFAILED: {e}")
        tg(f"❌ <b>Ch1 Pipeline FAILED</b>\n\n{str(e)[:400]}")
        raise


if __name__ == "__main__":
    main()
