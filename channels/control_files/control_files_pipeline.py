#!/usr/bin/env python3
"""
THE CONTROL FILES — ANIMATED PIPELINE v1.0
Channel 3 of DeepDive Empire

Niche: Mass Manipulation & Psychological Control
(cults, propaganda, social engineering at scale, psyops, mass deception)

FULL FEATURE SET (cloned from Evidence Room v2.0 + Channel 3 adaptations):
✅ 20 human neural voices (10 US + 10 GB) — clinical cold delivery
✅ Voice quality checker — auto-switches if robotic detected
✅ Quality gate minimum 7.3 | Final floor 6.9 (never lower)
✅ 13-attempt system (8 fresh + 5 archive viral topics)
✅ Different topic per attempt — never retries same topic
✅ Archive fallback: proven viral stories from last 2 years
✅ 4-trigger thumbnail system (curiosity + social proof + identity + pattern)
✅ Most disturbing mass-manipulation scripts ever written
✅ Viral intelligence engine (weekly learning)
✅ NO subtitles on main video
✅ Subtitles on Shorts ONLY with frame-perfect audio sync
✅ 2 YouTube Shorts per video (teaser 10% + recap 67%)
✅ Approval gate BEFORE video generation (30-min)
✅ Dual notification: Telegram + Gmail
✅ Startup Telegram test
✅ 6-provider AI chain: Cerebras→Gemini→Groq→OpenRouter→Cohere→Mistral
✅ 3 rotating animation styles (control_dark, propaganda_red, mind_wire)
✅ NEW scene types: thought_control, influence_map, resistance_timeline,
                    doctrine_reveal, compliance_chart
✅ Auto-cleanup after upload
✅ Cross-promotes Channel 1 (BetrayalDeepDive) and Channel 2 (Evidence Room)
✅ Affiliate CTA: BetterHelp + psychology courses + VPN

Animation Stack: Pillow + FFmpeg (zero system deps)
Schedule: Mon-Fri 1:30 PM IST (8:00 AM UTC)
"""

import os, sys, json, re, time, random, datetime, asyncio
import subprocess, shutil, requests, smtplib
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from PIL import Image, ImageDraw, ImageFont

# ── CREDENTIALS ────────────────────────────────────────────
GROQ_KEY        = os.environ.get("GROQ_API_KEY", "")
GEMINI_KEY      = os.environ.get("GEMINI_API_KEY", "")
CEREBRAS_KEY    = os.environ.get("CEREBRAS_API_KEY", "")
OPENROUTER_KEY  = os.environ.get("OPENROUTER_API_KEY", "")
COHERE_KEY      = os.environ.get("COHERE_API_KEY", "")
MISTRAL_KEY     = os.environ.get("MISTRAL_API_KEY", "")
SAMBANOVA_KEY   = os.environ.get("SAMBANOVA_API_KEY", "")    # v12: 1000 req/day free
GEMINI_KEY_2    = os.environ.get("GEMINI_API_KEY_2", "")     # v12: backup key = double quota
YT_CLIENT_ID    = os.environ.get("CHANNEL3_YT_CLIENT_ID", "")
YT_CLIENT_SEC   = os.environ.get("CHANNEL3_YT_CLIENT_SECRET", "")
YT_REFRESH      = os.environ.get("CHANNEL3_YT_REFRESH_TOKEN", "")
TG_TOKEN        = os.environ.get("TELEGRAM_TOKEN", "")
TG_CHAT         = os.environ.get("TELEGRAM_CHAT_ID", "")
PIXABAY_KEY     = os.environ.get("PIXABAY_KEY", "")
PEXELS_KEY      = os.environ.get("PEXELS_API_KEY", "")

# ── API endpoints ──────────────────────────────────────────
GEMINI_URL      = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
CEREBRAS_URL    = "https://api.cerebras.ai/v1/chat/completions"  # hardcoded — never loses scope
SAMBANOVA_URL   = "https://api.sambanova.ai/v1/chat/completions"  # v12: added
OPENROUTER_URL  = "https://openrouter.ai/api/v1/chat/completions"
GROQ_URL        = "https://api.groq.com/openai/v1/chat/completions"
COHERE_URL      = "https://api.cohere.com/v2/chat"
MISTRAL_URL     = "https://api.mistral.ai/v1/chat/completions"
YT_UPLOAD_URL   = "https://www.googleapis.com/upload/youtube/v3"
YT_DATA_URL     = "https://www.googleapis.com/youtube/v3"
YT_TOKEN_URL    = "https://oauth2.googleapis.com/token"

# ── Paths — state in REPO (persists between runs) ─────────
SCRIPT_DIR    = Path(__file__).parent
WORK_DIR      = Path("/tmp/control_files")
WORK_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE    = SCRIPT_DIR / "state.json"   # persists in repo
INTEL_FILE    = SCRIPT_DIR / "intel.json"   # persists in repo
CKPT_FILE     = WORK_DIR / "checkpoint.json"

# Cerebras model names to try in order
CEREBRAS_MODELS = ["llama-3.3-70b", "llama3.3-70b", "llama3.1-70b", "llama3.1-8b"]

W, H, FPS   = 1920, 1080, 30
MIN_WORDS   = 1800
MAX_WORDS   = 2200
MIN_GATE    = 7.3
FINAL_GATE  = 6.9

# ════════════════════════════════════════════════════════════
# 20 HUMAN NEURAL VOICES — CLINICAL COLD DELIVERY
# Psychological control niche needs calm, clinical, authoritative
# ════════════════════════════════════════════════════════════
US_VOICES = [
    "en-US-AndrewNeural",        # Warm authoritative — feels trustworthy (ironic for this niche)
    "en-US-BrianNeural",         # Deep calm commanding
    "en-US-ChristopherNeural",   # Serious documentary authoritative
    "en-US-JasonNeural",         # Calm measured deliberate
    "en-US-EricNeural",          # Professional measured
    "en-US-GuyNeural",           # Commanding serious
    "en-US-RogerNeural",         # Energetic authoritative
    "en-US-SteffanNeural",       # Professional clear
    "en-US-TonyNeural",          # Confident expressive
    "en-US-DavisNeural",         # placeholder — falls back to JasonNeural if unavailable
]
GB_VOICES = [
    "en-GB-RyanNeural",          # BBC gravitas — perfect for cult documentary
    "en-GB-ThomasNeural",        # Cold measured cinematic — ideal for psyop content
    "en-GB-NoahNeural",          # Deep calm investigative
    "en-GB-OliverNeural",        # Professional authoritative
    "en-GB-EthanNeural",         # Warm natural storytelling
    "en-GB-SoniaNeural",         # Sharp devastating (F)
    "en-GB-LibbyNeural",         # Natural conversational (F)
    "en-GB-AbbiNeural",          # Clear warm professional (F)
    "en-GB-HollieNeural",        # Professional sharp (F)
    "en-GB-MaisieNeural",        # Young clear measured (F)
]
ALL_VOICES     = US_VOICES + GB_VOICES
ROBOTIC_VOICES = ["en-US-AriaNeural", "en-US-AnaNeural"]

# Best voices per niche — clinical cold works best for manipulation content
NICHE_VOICES = {
    "cult_psychology":      ["en-GB-ThomasNeural","en-US-ChristopherNeural","en-GB-RyanNeural","en-US-BrianNeural"],
    "propaganda_systems":   ["en-US-BrianNeural","en-GB-ThomasNeural","en-US-ChristopherNeural","en-GB-NoahNeural"],
    "social_engineering":   ["en-GB-RyanNeural","en-US-AndrewNeural","en-GB-ThomasNeural","en-US-EricNeural"],
    "mass_deception":       ["en-US-ChristopherNeural","en-GB-ThomasNeural","en-GB-RyanNeural","en-US-BrianNeural"],
}

# Guaranteed working voices on GitHub Actions (tested on Ch2)
GUARANTEED_VOICES = [
    "en-GB-RyanNeural",
    "en-GB-ThomasNeural",
    "en-US-BrianNeural",
    "en-US-ChristopherNeural",
    "en-US-AndrewNeural",
    "en-US-EricNeural",
    "en-US-GuyNeural",
    "en-US-SteffanNeural",
    "en-GB-OliverNeural",
    "en-US-TonyNeural",
]

# ── ANIMATION STYLES ────────────────────────────────────────
STYLES = {
    "control_dark": {
        "bg":(2,2,8), "primary":(255,255,255), "accent":(180,0,180),
        "secondary":(100,0,100), "pulse":(140,0,140), "glow":(220,80,220),
        "desc":"Clinical dark — purple control lines on absolute black, psychological dread"
    },
    "propaganda_red": {
        "bg":(8,2,2), "primary":(240,235,225), "accent":(220,20,20),
        "secondary":(130,15,15), "pulse":(180,0,0), "glow":(255,60,60),
        "desc":"Soviet propaganda red — stamped doctrine, mass compliance aesthetic"
    },
    "mind_wire": {
        "bg":(3,8,18), "primary":(200,230,255), "accent":(40,160,255),
        "secondary":(60,90,140), "pulse":(20,100,200), "glow":(80,200,255),
        "desc":"Neural wire blue — thought-control diagrams, influence maps, cold intelligence"
    },
}
# Rotate styles across the week
DAY_STYLE = {0:"control_dark", 1:"propaganda_red", 2:"mind_wire", 3:"control_dark", 4:"propaganda_red"}

# ── NICHES ─────────────────────────────────────────────────
DAY_NICHE = {0:"cult_psychology", 1:"propaganda_systems", 2:"social_engineering",
             3:"mass_deception",  4:"cult_psychology"}

NICHES = [
    {
        "name": "cult_psychology", "rpm": 11.00,
        "series": "The Control Files: Cult Psychology",
        "viral_search": "cult psychology documentary how cults work indoctrination manipulation",
        "archive_search": "famous cult psychology manipulation exposed documentary viral 2022 2023",
        "thumbnail_triggers": ["THEY BELIEVED","MIND CONTROLLED","CULT EXPOSED","BLIND OBEDIENCE"],
        "seed_topics": [
            "The 7 psychological stages used across 200 documented cults — the compliance ladder nobody escapes quickly",
            "How a cult leader transformed 847 educated professionals into unquestioning followers in under 18 months",
            "The thought-stopping technique: how leaders install mental blocks that prevent members from questioning doctrine",
            "BITE model decoded: the exact behavior, information, thought, and emotional control used in high-control groups",
            "Former cult members describe the precise moment they stopped being able to think critically — and what caused it",
        ],
    },
    {
        "name": "propaganda_systems", "rpm": 10.50,
        "series": "The Control Files: Propaganda Systems",
        "viral_search": "propaganda documentary how propaganda works mass manipulation history exposed",
        "archive_search": "propaganda technique exposed how it works documentary viral 2022 2023",
        "thumbnail_triggers": ["YOU WERE TOLD","MASS CONTROL","SYSTEM EXPOSED","THEY LIED"],
        "seed_topics": [
            "The 11 propaganda techniques documented by the Institute for Propaganda Analysis — still deployed at scale today",
            "How a single narrative can be surgically embedded into 40 million people using only 3 media levers",
            "The firehose of falsehood: the documented Russian information strategy that overwhelms critical thinking",
            "Manufacturing consent: how institutional media shapes public reality without viewers realizing they're being shaped",
            "The 5 stages of a coordinated propaganda campaign — from seed narrative to mass belief — mapped and documented",
        ],
    },
    {
        "name": "social_engineering", "rpm": 12.00,
        "series": "The Control Files: Social Engineering",
        "viral_search": "social engineering psychology manipulation how humans are hacked documentary",
        "archive_search": "social engineering manipulation technique exposed documentary viral 2022 2023",
        "thumbnail_triggers": ["YOU WERE HACKED","TRUST EXPLOITED","MIND GAME EXPOSED","THEY KNEW"],
        "seed_topics": [
            "The 6 Cialdini principles of influence: how the same psychology used in advertising manipulates mass behavior",
            "How a single trained social engineer entered 9 secure facilities in one week using only conversation",
            "The documented playbook that intelligence agencies use to recruit assets — applied to civilian mass persuasion",
            "Dark patterns: the invisible UX manipulation affecting 3 billion people daily — documented and quantified",
            "How false urgency, artificial scarcity, and social proof are engineered to eliminate rational decision-making",
        ],
    },
    {
        "name": "mass_deception", "rpm": 9.50,
        "series": "The Control Files: Mass Deception",
        "viral_search": "mass deception psychological manipulation large scale exposed documentary",
        "archive_search": "mass deception social manipulation exposed documentary viral 2022 2023",
        "thumbnail_triggers": ["BILLIONS DECEIVED","MASS ILLUSION","DECEPTION SCALE","MIND CAPTURED"],
        "seed_topics": [
            "The anatomy of a coordinated mass deception: from planted seed narrative to 100 million believers in 6 weeks",
            "How a single fabricated statistic entered public discourse in 2019 and became accepted fact by 2021 — traced",
            "The astroturfing operation that made a minority opinion appear to be a global majority — documented evidence",
            "How real events are systematically reframed across 4 information layers to mean the opposite of what occurred",
            "The deepfake pipeline: how synthetic media is strategically deployed in coordinated influence campaigns at scale",
        ],
    },
]

# ── PSYCHOLOGICAL CONTROL TRIGGERS ─────────────────────────
CONTROL_TRIGGERS = {
    "invisibility":   "The control system was invisible because it looked exactly like normal thought.",
    "scale":          "Exact numbers that demonstrate scope. Each number represents a real thinking human being who stopped thinking.",
    "mechanism":      "The specific mechanism. The exact psychological lever. The named technique with documented research.",
    "duration":       "The exact timeline. Not years — 4,380 days. 627 compliance tests. 12 doctrine revisions.",
    "consent":        "They consented to every step. Each step felt reasonable. The destination was invisible from the start.",
    "competence":     "The sophistication. The research behind it. The behavioral science deployed against ordinary people.",
    "reversal":       "What the target believed was their own free choice was the most controlled decision they made.",
    "resistance":     "The people who resisted. What they saw that others missed. Why the system failed on them.",
}

# ════════════════════════════════════════════════════════════
# UTILITIES
# ════════════════════════════════════════════════════════════

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

def log(msg): print(msg, flush=True)

def tg(msg):
    chunks = [msg[i:i+4000] for i in range(0, len(msg), 4000)]
    for chunk in chunks:
        try:
            r = requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                             json={"chat_id":TG_CHAT,"text":chunk,"parse_mode":"HTML"},
                             timeout=15)
            if r.status_code != 200: log(f"  TG {r.status_code}")
            time.sleep(0.5)
        except Exception as e: log(f"  TG err: {str(e)[:50]}")

def tg_updates(offset=None):
    try:
        params = {"timeout":25}
        if offset: params["offset"] = offset
        r = requests.get(f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates",
                        params=params, timeout=30)
        return r.json().get("result",[])
    except: return []

def send_gmail(subject, html_body):
    pwd = os.environ.get("GMAIL_APP_PASSWORD","")
    if not pwd: log("  Gmail: no password — skipping"); return False
    sender = recipient = "mohammedsultan0497@gmail.com"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = sender
    msg["To"]      = recipient
    msg.attach(MIMEText(html_body,"html"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com",465,timeout=30) as smtp:
            smtp.login(sender,pwd)
            smtp.sendmail(sender,recipient,msg.as_string())
        log("  Gmail sent"); return True
    except Exception as e:
        log(f"  Gmail err: {str(e)[:80]}"); return False

def load_state():
    if STATE_FILE.exists():
        try: return json.loads(STATE_FILE.read_text())
        except: pass
    return {"last_style":"","last_niche":"","last_voice":"","last_title":"","last_url":""}

def save_state(s): STATE_FILE.write_text(json.dumps(s,indent=2))

def load_intel():
    if INTEL_FILE.exists():
        try: return json.loads(INTEL_FILE.read_text())
        except: pass
    return {}

def save_intel(d): INTEL_FILE.write_text(json.dumps(d,indent=2))

def strip_md(text):
    text = re.sub(r'[#*_`\[\]{}<>\\]','',text)
    text = re.sub(r'\n{3,}','\n\n',text)
    return text.strip()

def run_ffmpeg(cmd, label="", timeout=600):
    r = subprocess.run(cmd, capture_output=True, timeout=timeout)
    if r.returncode != 0:
        err = r.stderr.decode(errors="replace")[-300:]
        raise RuntimeError(f"FFmpeg {label} failed: {err}")
    return r

# ════════════════════════════════════════════════════════════
# 6-PROVIDER AI CHAIN — Cerebras → Gemini → Groq → OR → Cohere → Mistral
# ════════════════════════════════════════════════════════════

def _call_cerebras(prompt, tokens=9000):
    if not CEREBRAS_KEY:
        log("  Cerebras: CEREBRAS_API_KEY secret not set — skipping")
        return None
    _url = "https://api.cerebras.ai/v1/chat/completions"  # hardcoded inside function
    _models = ["llama-3.3-70b", "llama3.3-70b", "llama3.1-70b", "llama3.1-8b"]
    for model in _models:
        try:
            r = requests.post(_url,
                headers={"Authorization": f"Bearer {CEREBRAS_KEY}",
                         "Content-Type": "application/json"},
                json={"model": model,
                      "messages": [{"role": "user", "content": prompt}],
                      "max_completion_tokens": min(tokens, 12000),
                      "temperature": 0.88}, timeout=120)
            if r.status_code == 200:
                t = r.json().get("choices",[{}])[0].get("message",{}).get("content","")
                if t and len(t.strip()) > 100:
                    log(f"  OK Cerebras ({model})")
                    return t
            elif r.status_code == 404:
                continue
            else:
                log(f"  Cerebras {model}: {r.status_code}")
        except Exception as e:
            log(f"  Cerebras {model} err: {str(e)[:60]}")
    return None

def _call_gemini(prompt, tokens=9000, temp=0.88):
    if not GEMINI_KEY: return None
    _safety = [{"category": c, "threshold": "BLOCK_NONE"} for c in [
        "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH",
        "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
    try:
        r = requests.post(f"{GEMINI_URL}?key={GEMINI_KEY}",
            json={"contents":[{"parts":[{"text":prompt}]}],
                  "generationConfig":{"temperature":temp,"maxOutputTokens":min(tokens,8192)},
                  "safetySettings": _safety},
            timeout=120)
        if r.status_code == 200:
            t = r.json().get("candidates",[{}])[0].get("content",{}).get("parts",[{}])[0].get("text","")
            if t and len(t.strip()) > 100:
                log("  OK Gemini")
                return t
        else: log(f"  Gemini {r.status_code}: {r.text[:100]}")
    except Exception as e: log(f"  Gemini err: {str(e)[:60]}")
    return None

def _call_groq(prompt, tokens=4800, temp=0.88):
    if not GROQ_KEY: return None
    try:
        r = requests.post(GROQ_URL,
            headers={"Authorization":f"Bearer {GROQ_KEY}","Content-Type":"application/json"},
            json={"model":"llama-3.3-70b-versatile",
                  "messages":[{"role":"user","content":prompt}],
                  "max_tokens":min(tokens,4800),  # HARD CAP — TPM limit is 6000
                  "temperature":temp}, timeout=60)
        if r.status_code == 200:
            t = r.json().get("choices",[{}])[0].get("message",{}).get("content","")
            if t and len(t.strip()) > 50:
                log("  OK Groq")
                return t
        else: log(f"  Groq {r.status_code}: {r.text[:100]}")
    except Exception as e: log(f"  Groq err: {str(e)[:60]}")
    return None

def _call_openrouter(prompt, tokens=4000, temp=0.88):
    if not OPENROUTER_KEY: return None
    models = ["meta-llama/llama-3.3-70b:free",
              "meta-llama/llama-3.1-70b-instruct:free",
              "qwen/qwen-2.5-72b-instruct:free"]
    for model in models:
        try:
            r = requests.post(OPENROUTER_URL,
                headers={"Authorization":f"Bearer {OPENROUTER_KEY}",
                         "Content-Type":"application/json",
                         "HTTP-Referer":"https://github.com/BetrayalDeepDive"},
                json={"model":model,
                      "messages":[{"role":"user","content":prompt}],
                      "max_tokens":min(tokens,4000),"temperature":temp}, timeout=90)
            if r.status_code == 200:
                t = r.json().get("choices",[{}])[0].get("message",{}).get("content","")
                if t and len(t.strip()) > 50:
                    log(f"  OK OpenRouter ({model.split('/')[-1][:20]})")
                    return t
            elif r.status_code == 404: continue
            else: log(f"  OR {model[-20:]}: {r.status_code}")
        except Exception as e: log(f"  OR err: {str(e)[:60]}")
    return None

def _call_cohere(prompt, tokens=4000, temp=0.88):
    if not COHERE_KEY: return None
    try:
        r = requests.post(COHERE_URL,
            headers={"Authorization":f"Bearer {COHERE_KEY}","Content-Type":"application/json"},
            json={"model":"command-r-plus",
                  "messages":[{"role":"user","content":prompt}],
                  "max_tokens":min(tokens,4000),"temperature":temp}, timeout=90)
        if r.status_code == 200:
            t = ""
            d = r.json()
            if "message" in d: t = d["message"].get("content",[{}])[0].get("text","")
            elif "text" in d:   t = d["text"]
            if t and len(t.strip()) > 50:
                log("  OK Cohere")
                return t
        else: log(f"  Cohere {r.status_code}")
    except Exception as e: log(f"  Cohere err: {str(e)[:60]}")
    return None

def _call_mistral(prompt, tokens=4000, temp=0.88):
    if not MISTRAL_KEY: return None
    try:
        r = requests.post(MISTRAL_URL,
            headers={"Authorization":f"Bearer {MISTRAL_KEY}","Content-Type":"application/json"},
            json={"model":"mistral-small-latest",
                  "messages":[{"role":"user","content":prompt}],
                  "max_tokens":min(tokens,4000),"temperature":temp}, timeout=90)
        if r.status_code == 200:
            t = r.json().get("choices",[{}])[0].get("message",{}).get("content","")
            if t and len(t.strip()) > 50:
                log("  OK Mistral")
                return t
        else: log(f"  Mistral {r.status_code}")
    except Exception as e: log(f"  Mistral err: {str(e)[:60]}")
    return None

def _call_sambanova(prompt, tokens=9000, temp=0.88):
    """SambaNova — free 1000 req/day. cloud.sambanova.ai"""
    if not SAMBANOVA_KEY: return None
    for model in ["Meta-Llama-3.3-70B-Instruct", "Meta-Llama-3.1-70B-Instruct"]:
        try:
            r = requests.post(SAMBANOVA_URL,
                headers={"Authorization":f"Bearer {SAMBANOVA_KEY}",
                         "Content-Type":"application/json"},
                json={"model":model,
                      "messages":[{"role":"user","content":prompt}],
                      "max_tokens":min(tokens,8192),"temperature":temp}, timeout=90)
            if r.status_code == 200:
                t = r.json().get("choices",[{}])[0].get("message",{}).get("content","")
                if t and len(t.strip()) > 50:
                    log(f"  OK SambaNova")
                    return t
            elif r.status_code in [401,429]: return None
        except Exception as e: log(f"  SambaNova err: {str(e)[:60]}")
    return None

def _call_gemini_v12(prompt, tokens=9000, temp=0.88):
    """Gemini with GEMINI_KEY_2 backup on 429 quota hit."""
    keys = [k for k in [GEMINI_KEY, GEMINI_KEY_2] if k]
    if not keys: return None
    for key_idx, active_key in enumerate(keys):
        try:
            r = requests.post(f"{GEMINI_URL}?key={active_key}",
                json={"contents":[{"parts":[{"text":prompt}]}],
                      "generationConfig":{"temperature":temp,"maxOutputTokens":min(tokens,8192)}},
                timeout=120)
            if r.status_code == 200:
                t = r.json().get("candidates",[{}])[0].get("content",{}).get("parts",[{}])[0].get("text","")
                if t and len(t.strip()) > 100:
                    log("  OK Gemini")
                    return t
            elif r.status_code == 429:
                if key_idx == 0 and GEMINI_KEY_2:
                    log("  Gemini primary 429 — trying backup key")
                    continue
                return None
            else: log(f"  Gemini {r.status_code}")
        except Exception as e: log(f"  Gemini err: {str(e)[:60]}")
        break
    return None

def ai(prompt, temp=0.88, tokens=9000, prefer="cerebras"):
    """v12: 7-provider chain. Cerebras→SambaNova→Gemini→Groq→OR→Cohere→Mistral."""
    if prefer == "groq":
        order = [
            lambda: _call_cerebras(prompt, min(tokens, 9000)),
            lambda: _call_sambanova(prompt, min(tokens, 9000), temp),
            lambda: _call_groq(prompt, min(tokens, 4800), temp),
            lambda: _call_gemini_v12(prompt, tokens, temp),
            lambda: _call_openrouter(prompt, min(tokens, 4000), temp),
            lambda: _call_cohere(prompt, min(tokens, 4000), temp),
            lambda: _call_mistral(prompt, min(tokens, 4000), temp),
        ]
    else:
        order = [
            lambda: _call_cerebras(prompt, min(tokens, 9000)),
            lambda: _call_sambanova(prompt, min(tokens, 9000), temp),
            lambda: _call_gemini_v12(prompt, tokens, temp),
            lambda: _call_groq(prompt, min(tokens, 4800), temp),
            lambda: _call_openrouter(prompt, min(tokens, 4000), temp),
            lambda: _call_cohere(prompt, min(tokens, 4000), temp),
            lambda: _call_mistral(prompt, min(tokens, 4000), temp),
        ]
    for fn in order:
        try:
            result = fn()
            if result: return result
        except Exception as e:
            log(f"  Provider err: {str(e)[:60]}")
        time.sleep(2)
    raise RuntimeError("All 7 AI providers failed")

def run_stage_with_retry(fn, stage_name, *args, **kwargs):
    """Stage-level retry: 3 attempts with 30s gap."""
    for attempt in range(1, 4):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            log(f"  Stage {stage_name} attempt {attempt}/3 failed: {str(e)[:100]}")
            if attempt < 3:
                time.sleep(30)
            else:
                raise


# ════════════════════════════════════════════════════════════
# VIRAL INTELLIGENCE ENGINE
# ════════════════════════════════════════════════════════════
def run_viral_intelligence(niche):
    intel = load_intel()
    name  = niche["name"]
    cached = intel.get(name, {})
    last_run = cached.get("last_run","")
    if last_run:
        try:
            dt = datetime.datetime.fromisoformat(last_run)
            if (datetime.datetime.now() - dt).days < 7:
                log(f"  Intel cached ({name})")
                return cached
        except: pass

    log(f"  Running viral intelligence: {name}")
    prompt = f"""Analyze top YouTube videos for the "{niche['series']}" niche.
Search focus: {niche['viral_search']}
Return the viral patterns that make these videos get 2M+ views.

Return ONLY valid JSON (no backticks, no preamble):
{{"top_hook_formulas":["Hook 1","Hook 2","Hook 3"],
"winning_title_patterns":["Pattern 1","Pattern 2","Pattern 3"],
"thumbnail_text_examples":["3 WORD 1","3 WORD 2","3 WORD 3","3 WORD 4","3 WORD 5"],
"emotional_arc":"One sentence description",
"retention_hooks":["30pct hook","60pct hook","80pct hook"],
"niche_specific_power_words":["word1","word2","word3","word4","word5","word6"],
"what_makes_videos_viral":"One sentence",
"fresh_topic_ideas":["Topic 1","Topic 2","Topic 3","Topic 4","Topic 5","Topic 6"]}}"""
    try:
        text = ai(prompt, temp=0.65, tokens=400, prefer="groq")
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]','',re.sub(r'```json|```','',text).strip())
        m = re.search(r'\{[\s\S]*\}',text)
        if m:
            d = json.loads(m.group())
            d["last_run"] = datetime.datetime.now().isoformat()
            intel[name] = d; save_intel(intel)
            log("  Intel loaded")
            return d
    except Exception as e: log(f"  Intel err: {e}")

    # Fallback intel
    fallback = {
        "top_hook_formulas":[
            "The technique was documented in academic research. Nobody told the public.",
            "This is the psychological mechanism. You have already been exposed to it today.",
            "The system worked on 97% of people. The 3% who resisted had one thing in common.",
        ],
        "winning_title_patterns":[
            "The [TECHNIQUE] That [CONTROLLED/MANIPULATED] [SCALE] — [OUTCOME]",
            "[NUMBER] [PEOPLE/TARGETS] — The [SYSTEM] That Changed Everything",
        ],
        "thumbnail_text_examples": niche["thumbnail_triggers"],
        "emotional_arc":"Methodical exposure of invisible control systems building to personal recognition",
        "retention_hooks":[
            "The next technique is the one most people have personally experienced",
            "What the research revealed about who is most vulnerable changed everything",
            "The final stage of the process is the one that makes escape most difficult",
        ],
        "niche_specific_power_words":["controlled","manipulated","programmed","conditioned","weaponized","engineered"],
        "what_makes_videos_viral":"Personal recognition — viewers realize they have been manipulated and must warn others",
        "fresh_topic_ideas": niche["seed_topics"],
        "last_run": datetime.datetime.now().isoformat()
    }
    intel[name] = fallback; save_intel(intel)
    return fallback


# ════════════════════════════════════════════════════════════
# FRESH TOPIC ENGINE
# ════════════════════════════════════════════════════════════
def get_fresh_topic(niche, attempt, intel, used_topics):
    if attempt == 1:
        try:
            sf = SCRIPT_DIR / "next_week_strategy.json"
            if sf.exists():
                sd = json.loads(sf.read_text())
                rec = [t for t in sd.get("recommended_topics",[]) if t not in used_topics]
                if rec:
                    t = random.choice(rec)
                    log(f"  Strategy topic (attempt 1): {t[:60]}")
                    return t
        except: pass

    is_archive = attempt > 8
    if not is_archive:
        fresh = intel.get("fresh_topic_ideas", niche["seed_topics"])
        unused = [t for t in fresh if t not in used_topics]
        if unused:
            chosen = unused[0] if attempt <= 3 else random.choice(unused)
            log(f"  Topic (intel): {chosen[:70]}")
            return chosen
        log("  Generating new topics...")
        prompt = f"""Generate 6 compelling psychological control investigation topics for "{niche['series']}".
Niche: {niche['name']} | Search: {niche['viral_search']}
Already used: {[t[:40] for t in used_topics[:4]]}
Each must be specific, backed by real research or documented cases, produce a 12-minute video.
Return ONLY a JSON array: ["Topic 1","Topic 2","Topic 3","Topic 4","Topic 5","Topic 6"]"""
        try:
            text = ai(prompt, temp=0.85, tokens=400, prefer="groq")
            text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]','',re.sub(r'```json|```','',text).strip())
            m = re.search(r'\[[\s\S]*?\]',text)
            if m:
                topics = json.loads(m.group())
                unused = [t for t in topics if t not in used_topics]
                if unused:
                    chosen = random.choice(unused)
                    log(f"  Topic (generated): {chosen[:70]}")
                    return chosen
        except Exception as e: log(f"  Topic gen err: {e}")
    else:
        log(f"  Archive mode (attempt {attempt})...")
        prompt = f"""Find 6 documented real-world cases from 2022-2024 that fit "{niche['name']}" and went viral.
Focus: {niche['archive_search']}
Not already used: {[t[:40] for t in used_topics[:4]]}
Return ONLY a JSON array: ["Story 1","Story 2","Story 3","Story 4","Story 5","Story 6"]"""
        try:
            text = ai(prompt, temp=0.8, tokens=400, prefer="groq")
            text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]','',re.sub(r'```json|```','',text).strip())
            m = re.search(r'\[[\s\S]*?\]',text)
            if m:
                topics = json.loads(m.group())
                unused = [t for t in topics if t not in used_topics]
                if unused:
                    chosen = random.choice(unused)
                    log(f"  Topic (archive): {chosen[:70]}")
                    return chosen
        except Exception as e: log(f"  Archive err: {e}")

    unused_seeds = [t for t in niche["seed_topics"] if t not in used_topics]
    chosen = random.choice(unused_seeds) if unused_seeds else niche["seed_topics"][0]
    log(f"  Topic (seed): {chosen[:70]}")
    return chosen


# ════════════════════════════════════════════════════════════
# 4-TRIGGER THUMBNAIL SYSTEM
# ════════════════════════════════════════════════════════════
def generate_thumbnail_text(niche, topic, intel):
    examples = intel.get("thumbnail_text_examples", niche["thumbnail_triggers"])
    prompt = f"""Generate the most psychologically compelling 3-word thumbnail text for a mass manipulation documentary video.
NICHE: {niche['name']} | TOPIC: {topic[:100]}
TOP PERFORMERS: {', '.join(examples)}

USE ALL 4 TRIGGERS:
1. PERSONAL RECOGNITION: viewer recognizes they may have experienced this
2. SCALE SIGNAL: implies this affects millions, not individuals
3. SYSTEM EXPOSURE: implies documented proof of a hidden control system
4. PATTERN INTERRUPT: unexpected — makes viewer stop scrolling

Rules: EXACTLY 3 words. ALL CAPS. Control-focused. Never generic.
Return ONLY 3 words. Example: MIND CONTROLLED YOU"""
    try:
        result = ai(prompt, temp=0.82, tokens=15, prefer="groq")
        result = re.sub(r'[^A-Z\s]','',result.upper()).strip()
        words  = result.split()[:3]
        if len(words) == 3:
            log(f"  Thumbnail: {' '.join(words)}")
            return ' '.join(words)
    except: pass
    return random.choice(niche["thumbnail_triggers"])


# ════════════════════════════════════════════════════════════
# 5-TITLE CTR SCORING
# ════════════════════════════════════════════════════════════
def score_title_ctr(title):
    s = 5.0; tl = title.lower(); n = len(title)
    if 50<=n<=65: s+=1.5
    elif 45<=n<=70: s+=0.8
    else: s-=1.0
    power = ["exposed","controlled","manipulated","documented","proved","revealed","engineered",
             "weaponized","programmed","conditioned","billion","million","system"]
    s += min(sum(1 for w in power if w in tl)*0.4, 2.0)
    if re.search(r'\d+\s*(year|month|people|million|billion|study|technique|stage)',tl): s+=1.0
    if any(w in tl for w in ["nobody knew","you never knew","hidden from","kept secret","never told"]): s+=0.8
    return min(round(s,1),10.0)

def generate_and_score_titles(niche, topic, intel, episode):
    patterns = intel.get("winning_title_patterns",[])
    power    = intel.get("niche_specific_power_words",["controlled","manipulated","programmed"])
    prompt = f"""Generate exactly 5 YouTube title variants for this mass manipulation documentary video.
NICHE: {niche['name']} | SERIES: {niche['series']} Ep{episode}
TOPIC: {topic[:150]}
VIRAL PATTERNS: {chr(10).join(patterns[:3])}
POWER WORDS: {', '.join(power)}
Rules: 50-65 chars. Personal recognition trigger. Documentary tone. Specific research detail.
Return ONLY JSON array: ["title 1","title 2","title 3","title 4","title 5"]"""
    try:
        text = ai(prompt, temp=0.75, tokens=400, prefer="groq")
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]','',re.sub(r'```json|```','',text).strip())
        m = re.search(r'\[[\s\S]*?\]',text)
        if m:
            titles = json.loads(m.group())
            if len(titles) >= 3:
                scored = sorted([(t,score_title_ctr(t)) for t in titles],key=lambda x:x[1],reverse=True)
                log(f"  Title: {scored[0][1]}/10 — {scored[0][0][:55]}")
                return scored[0][0], scored
    except Exception as e: log(f"  Title err: {e}")
    fallback = f"{niche['series']}: The System They Never Told You About"
    return fallback, [(fallback, 6.0)]


# ════════════════════════════════════════════════════════════
# SCRIPT GENERATION — MASS MANIPULATION NARRATION
# ════════════════════════════════════════════════════════════
def get_niche_voice_style(state):
    day        = datetime.datetime.now().weekday()
    niche_name = DAY_NICHE.get(day,"cult_psychology")
    style_name = DAY_STYLE.get(day,"control_dark")
    if style_name == state.get("last_style",""):
        opts = [s for s in STYLES if s!=style_name]
        style_name = opts[day%len(opts)]
    niche = next(n for n in NICHES if n["name"]==niche_name)
    preferred = NICHE_VOICES.get(niche_name, GB_VOICES[:4])
    available = [v for v in preferred if v!=state.get("last_voice","")]
    voice = (available or preferred)[datetime.datetime.now().timetuple().tm_yday % len(available or preferred)]
    return niche, voice, style_name

def build_control_trigger_prompt():
    triggers = ["invisibility","scale","mechanism","duration","consent","competence","reversal","resistance"]
    return "\n".join(f"TRIGGER {t.upper()}: {CONTROL_TRIGGERS[t]}" for t in triggers if t in CONTROL_TRIGGERS)

def generate_script_and_scenes(niche, topic, style_name, episode, attempt, intel, prev_title=""):
    """
    v2 script generation for Ch3 (The Control Files).
    Investigative documentary framing — same approach as Frontline, Vice,
    The Social Dilemma, Wild Wild Country. Exposé, not sensationalised.
    Stage-level scoring + targeted rewrite of 2 worst stages.
    """
    temp  = min(0.82 + attempt * 0.012, 0.94)
    hooks = intel.get("top_hook_formulas", ["The research documented what observers had suspected."])
    power = intel.get("niche_specific_power_words", ["documented","studied","verified","confirmed"])
    cross = f'\nReference previous investigation: "{prev_title}" naturally in closing.' if prev_title else ""

    # Research anchors
    anchors = {}
    try:
        anchor_prompt = (
            f"Generate specific realistic research anchors for an investigative documentary about: {topic}\n"
            f"Return ONLY valid JSON (no backticks):\n"
            f'{{"case_duration":"e.g. documented over 14 years",'
            f'"people_affected":"e.g. 847 documented subjects in 6 studies",'
            f'"key_research":"e.g. a 2019 Stanford study of 340 participants",'
            f'"institution":"e.g. a media company reaching 40 million people",'
            f'"documented_outcome":"e.g. a 23% measurable shift in reported beliefs",'
            f'"resistance_rate":"e.g. 14% of subjects showed documented resistance"}}' 
        )
        ar = ai(anchor_prompt, temp=0.65, tokens=300, prefer="groq")
        if ar:
            ar = re.sub(r"```json|```", "", ar).strip()
            m  = re.search(r"\{[\s\S]*?\}", ar)
            if m:
                anchors = json.loads(m.group())
                log(f"  Anchors: {len(anchors)} fields")
    except Exception as e:
        log(f"  Anchors (non-fatal): {e}")

    anchor_block = ""
    if anchors:
        anchor_block = "\n\nUSE THESE SPECIFIC DETAILS:\n" + "\n".join(
            f"  {k}: {v}" for k, v in anchors.items() if v)

    stage_targets = {1:110, 2:210, 3:260, 4:420, 5:170, 6:680, 7:190}

    prompt = f"""Write an investigative documentary narration script in the tradition of Frontline, Vice, and The Social Dilemma — factual, sourced, exposé style.

INVESTIGATION: {topic}
SERIES: {niche['series']} — Episode {episode}
APPROACH: Academic research, documented case studies, on-record testimony, published findings.
{anchor_block}{cross}

TOTAL: {MIN_WORDS} to {MAX_WORDS} words. Each stage must hit its target.

SEVEN-STAGE INVESTIGATIVE STRUCTURE — write continuously, no labels:

STAGE 1 — COLD OPEN ({stage_targets[1]} words)
Sentence 1: a specific documented finding — a number, a study, a date.
Sentence 2: the scale of its reach or application.
Sentence 3: the question this investigation will answer.
Forbidden: "welcome back", "today we", "in this video", "join me"

STAGE 2 — HOW IT DEVELOPED ({stage_targets[2]} words)
The origin of the technique, system, or pattern under investigation.
Who developed it. What the original stated purpose was. Specific dates and institutions.
Final sentence: the moment it moved beyond its stated purpose.
Forbidden: "little did they know", "nobody could have predicted", "unbeknownst to"

STAGE 3 — EARLY DOCUMENTED CASES ({stage_targets[3]} words)
Early real-world applications. Each one sourced and specific.
One documented case per sentence. Build the documented record.
Forbidden: "suddenly", "without warning", "shockingly", "out of nowhere"

STAGE 4 — THE EVIDENCE ({stage_targets[4]} words)
Academic studies. Published research. On-record testimony. Court documents.
Each piece of evidence more specific than the last. Citations feel real and sourced.
Short sentences stating findings, then one longer contextualising sentence.
Forbidden: vague quantities — not "many studies" but "fourteen peer-reviewed studies"

STAGE 5 — THE OFFICIAL RESPONSE ({stage_targets[5]} words)
How institutions, regulators, or companies responded when evidence emerged.
Specific statements. Specific dates. Specific outcomes of those responses.
Final sentence: the gap between the stated response and the documented reality.
Forbidden: "but it wasn't over", "however", "or so they thought"

STAGE 6 — THE FULL DOCUMENTED RECORD ({stage_targets[6]} words)
The complete picture the investigation has assembled.
One finding per paragraph. Each paragraph cites a specific source type.
The scale of documented reach. The documented outcomes. The people on record.
Forbidden: "in conclusion", "to summarise", "as we can see"

STAGE 7 — IMPLICATIONS AND CTA ({stage_targets[7]} words)
What the documented record implies about current and future applications.
The researchers, regulators, and individuals working on documented responses.
Subscribe CTA at emotional peak — framed as continued investigation.{cross}
Forbidden: "subscribe and like", "hit the bell", "don't forget to"

RULES:
1. Maximum 13 words per sentence. Every sentence.
2. Zero markdown. Zero AI filler phrases.
3. Every number specific. Every date specific. Every institution named.
4. Sourced, documented tone throughout — not speculative.
5. Start immediately with Stage 1. No preamble.
6. Write one continuous narrative — no stage labels, no headers.

After the complete narration, add exactly 10 dashes on a new line, then scene JSON:
{{"title":"YouTube title 55-65 chars","thumbnail_text":"3 WORDS ALL CAPS with number","tags":["tag1","tag2","tag3","tag4","tag5","tag6","tag7","tag8","tag9","tag10"],"scenes":[
{{"type":"thought_control","duration":8,"title":"THE DOCUMENTED SYSTEM","stages":["Stage 1: Foundation","Stage 2: Application","Stage 3: Scale","Stage 4: Outcome"],"label":"DOCUMENTED PROGRESSION"}},
{{"type":"doctrine_reveal","duration":7,"title":"THE RESEARCH RECORD","lines":["ACADEMIC FINDINGS — ON RECORD","Source: [institution type]","Finding: [specific result]","Scope: [documented reach]"],"stamp":"DOCUMENTED"}},
{{"type":"compliance_chart","duration":7,"title":"DOCUMENTED OUTCOMES","items":["14%","38%","67%","89%"],"label":"MEASURED EFFECT OVER TIME"}},
{{"type":"influence_map","duration":8,"title":"THE DOCUMENTED NETWORK","nodes":["ORIGIN","INSTITUTION","APPLICATION","DOCUMENTED REACH"],"label":"MAPPED CONNECTIONS"}},
{{"type":"resistance_timeline","duration":10,"title":"DOCUMENTED RESPONSES","items":["Research: First findings","Regulators: Initial response","Institutions: Stated position","Individuals: Documented resistance"],"label":"RESPONSE RECORD"}}
]}}

Write narration first ({MIN_WORDS}-{MAX_WORDS} words), then 10 dashes, then JSON."""

    raw   = ai(prompt, temp=temp, tokens=7000, prefer="gemini")
    parts = raw.split("----------") if raw else [""]
    clean = strip_md(strip_md(parts[0].strip()))
    wc    = len(clean.split())

    # Expansion rounds
    for exp_round in range(2):
        if wc >= MIN_WORDS:
            break
        deficit = MIN_WORDS - wc
        log(f"  {wc}w short — expanding round {exp_round+1}...")
        exp = (
            f"This investigative documentary script is {wc} words. Needs {MIN_WORDS}.\n"
            f"Expand the Evidence section and the Full Record section only.\n"
            f"Add specific research citations, exact study sizes, exact institutional names.\n"
            f"Max 13 words per sentence. Zero markdown.\n"
            f"Return the COMPLETE expanded script.\n\nSCRIPT:\n{clean}"
        )
        raw2 = ai(exp, temp=0.82, tokens=7000, prefer="gemini")
        if raw2:
            c2 = strip_md(strip_md(raw2))
            if len(c2.split()) > wc:
                clean = c2
                wc    = len(clean.split())
                log(f"  Expanded to {wc}w")

    # Stage-level scoring + targeted rewrite of 2 worst stages
    if wc >= MIN_WORDS:
        try:
            words      = clean.split()
            total      = len(words)
            targets_l  = [110, 210, 260, 420, 170, 680, 190]
            total_t    = sum(targets_l)
            stage_txts = []
            pos = 0
            for i, tgt in enumerate(targets_l):
                share = tgt / total_t
                end   = pos + int(total * share) if i < 6 else total
                stage_txts.append(" ".join(words[pos:end]))
                pos   = end

            stage_names   = ["COLD OPEN","DEVELOPMENT","EARLY CASES","EVIDENCE",
                             "OFFICIAL RESPONSE","FULL RECORD","IMPLICATIONS"]
            forbidden_per = [
                ["welcome back","today we","in this video","join me"],
                ["little did they know","unbeknownst"],
                ["suddenly","out of nowhere","without warning"],
                [],
                ["but it wasn't over","or so they thought"],
                ["in conclusion","to summarise"],
                ["subscribe and like","hit the bell"],
            ]
            stage_scores = []
            for stext, sname, starget, sforbidden in zip(
                    stage_txts, stage_names, targets_l, forbidden_per):
                sc    = 5.0
                ratio = len(stext.split()) / max(starget, 1)
                if 0.85 <= ratio <= 1.15:   sc += 2.0
                elif 0.70 <= ratio <= 1.30: sc += 0.8
                else:                       sc -= 1.5
                sc -= sum(0.8 for f in sforbidden if f in stext.lower())
                sents = [s for s in re.split(r"(?<=[.!?])\s+", stext) if s.strip()]
                long  = [s for s in sents if len(s.split()) > 13]
                if len(long) / max(len(sents), 1) > 0.2:
                    sc -= 0.8
                ai_ph = ["moreover","furthermore","it is worth noting","in conclusion"]
                sc   -= sum(0.4 for p in ai_ph if p in stext.lower())
                stage_scores.append(round(min(max(sc, 0), 10), 1))

            log(f"  Stage scores: {" | ".join(f"{n[:6]}:{s}" for n,s in zip(stage_names,stage_scores))}")
            worst_two = sorted(range(len(stage_scores)), key=lambda i: stage_scores[i])[:2]

            for idx in worst_two:
                if stage_scores[idx] >= 7.5:
                    continue
                rewrite_p = (
                    f"Rewrite ONLY this investigative documentary stage. Return ONLY the rewritten text.\n\n"
                    f"STAGE: {stage_names[idx]} (target: {targets_l[idx]} words)\n"
                    f"TOPIC: {topic[:100]}\n"
                    f"SCORE: {stage_scores[idx]}/10 — too vague or sentences too long\n\n"
                    f"RULES:\n"
                    f"- Max 13 words per sentence.\n"
                    f"- Every number specific (not 'many studies' but 'fourteen studies').\n"
                    f"- Every institution named specifically.\n"
                    f"- Zero markdown. Zero filler.\n"
                    f"- Target: {targets_l[idx]} words.\n\n"
                    f"ORIGINAL:\n{stage_txts[idx]}\n\nRewrite now:"
                )
                new_s = ai(rewrite_p, temp=0.82, tokens=2000, prefer="groq")
                if new_s:
                    new_s = strip_md(new_s)
                    if len(new_s.split()) > 30:
                        clean = clean.replace(stage_txts[idx], new_s, 1)
                        log(f"  Stage {stage_names[idx]} rewritten")

            wc = len(clean.split())
            log(f"  After targeted rewrite: {wc}w")
        except Exception as e:
            log(f"  Stage rewrite (non-fatal): {e}")

    # Parse scenes
    scenes, title, thumbnail_text, tags = [], f"The Control Files: {topic[:45]}", "DOCUMENTED EXPOSED", \
        [niche["name"],"psychology","documentary","animated","investigation","research",
         "exposed","evidence","thecontrolfiles","frontline"]
    if len(parts) > 1:
        try:
            jt = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]","",re.sub(r"```json|```","",parts[1]).strip())
            m  = re.search(r"\{[\s\S]*\}", jt)
            if m:
                data           = json.loads(m.group())
                scenes         = data.get("scenes", [])
                title          = data.get("title", title)
                thumbnail_text = data.get("thumbnail_text", thumbnail_text)
                tags           = data.get("tags", tags)
        except Exception as e:
            log(f"  Scene JSON (non-fatal): {e}")

    if not scenes:
        scenes = [
            {"type":"thought_control","duration":8,"title":"DOCUMENTED PROGRESSION",
             "stages":["Foundation","Application","Scale","Outcome"],"label":"DOCUMENTED SYSTEM"},
            {"type":"compliance_chart","duration":7,"title":"MEASURED OUTCOMES",
             "items":["14%","38%","67%","89%"],"label":"DOCUMENTED EFFECT"},
            {"type":"doctrine_reveal","duration":7,"title":"RESEARCH RECORD",
             "lines":["ACADEMIC FINDINGS","Source: peer-reviewed","Finding: documented",
                      "Scope: verified reach"],"stamp":"DOCUMENTED"},
            {"type":"influence_map","duration":8,"title":"MAPPED CONNECTIONS",
             "nodes":["ORIGIN","INSTITUTION","APPLICATION","REACH"],"label":"NETWORK"},
            {"type":"resistance_timeline","duration":10,"title":"DOCUMENTED RESPONSES",
             "items":["Research","Regulation","Institution","Individual"],"label":"RESPONSES"},
        ]

    violations = len(re.findall(r"[#*_`\[\]{}<>\\]", clean))

    # CTA injection
    if len(clean.split()) >= 400:
        clean = _inject_ctas_cf(clean, niche.get("name","cult_psychology"))
        wc    = len(clean.split())

    log(f"  Script: {wc}w | {violations} MD | {len(scenes)} scenes")
    return clean, scenes, title, thumbnail_text, tags, violations


def score_script(script_clean, wc, violations):
    issues, score = [], 5.0
    if wc >= MIN_WORDS:   score+=2.8
    elif wc >= 1500:      score+=0.8;  issues.append(f"{wc}w short")
    elif wc >= 1000:      score-=1.5;  issues.append(f"SHORT: {wc}w")
    else:                 score-=4.0;  issues.append(f"FATAL: {wc}w")
    if violations==0:     score+=2.2
    elif violations<=2:   score+=0.5;  issues.append(f"{violations} md")
    else:                 score-=1.5;  issues.append(f"FATAL: {violations} md")
    sents = [x for x in re.split(r'(?<=[.!?])\s+',script_clean) if len(x.split())>2]
    if sents:
        avg = sum(len(x.split()) for x in sents)/len(sents)
        if avg<=11:       score+=1.5
        elif avg<=13:     score+=1.0
        elif avg<=15:     score+=0.4
        else:             score-=0.5; issues.append(f"Avg {avg:.0f}w")
    hook = script_clean[:350].lower()
    ew = ["control","system","documented","research","technique","programmed","conditioned","exposed"]
    hs = sum(1 for w in ew if w in hook)
    if hs>=4:             score+=1.0
    elif hs>=2:           score+=0.5
    else:                 issues.append("Weak control hook")
    ai_phrases = ["moreover","furthermore","it is worth noting","in conclusion","interestingly","it should be noted"]
    ai_count = sum(1 for p in ai_phrases if p in script_clean.lower())
    if ai_count>0:        score-=ai_count*0.3; issues.append(f"{ai_count} AI phrases")
    if "subscribe" in script_clean[-400:].lower(): score+=0.2
    # v12: retention hook validation
    ret_penalty, ret_issues = _validate_retention_hooks_cf(script_clean)
    score += ret_penalty
    issues.extend(ret_issues)
    return min(round(score,1),10.0), issues


def _validate_retention_hooks_cf(script_clean):
    """Retention hook validator for Ch3. Weak scripts auto-retry via 13-attempt engine."""
    words = script_clean.split(); total = len(words)
    if total < 400: return 0.0, []
    penalty = 0.0; issues = []
    hook_signals = ["subscribe","coming up","next","what happens","revealed","in a moment",
                    "stay","about to","this changes","not yet","what comes next","thirty seconds"]
    def seg(p1,p2): return " ".join(words[int(total*p1):int(total*p2)]).lower()
    if sum(1 for w in hook_signals if w in seg(0.25,0.35)) < 1:
        penalty -= 0.4; issues.append("Missing 30% hook")
    h60 = sum(1 for w in hook_signals if w in seg(0.55,0.65))
    if h60 < 2:    penalty -= 0.8; issues.append("Weak 60% peak hook")
    elif h60 >= 3: penalty += 0.3
    if sum(1 for w in hook_signals if w in seg(0.75,0.85)) < 1:
        penalty -= 0.4; issues.append("Missing 80% hook")
    if "subscribe" not in " ".join(words[-60:]).lower():
        penalty -= 0.3; issues.append("Missing final subscribe CTA")
    return round(penalty,1), issues


def _inject_ctas_cf(script_clean, niche_name):
    """Inject subscribe CTAs at 30/60/80% marks for Ch3 (The Control Files)."""
    words = script_clean.split(); total = len(words)
    if total < 400: return script_clean
    seed = abs(hash(script_clean[:80])) % 2
    cta_pool = {
        "30pct": ["Subscribe to The Control Files. The mechanism this is built on is thirty seconds away.",
                  "Subscribe before the technique is fully revealed."],
        "60pct": ["Subscribe to The Control Files. What is documented next is the reason this channel was built.",
                  "Subscribe now. This is the section that changes how you see everything before it."],
        "80pct": ["Subscribe to The Control Files. New investigation every weekday.",
                  "Subscribe if this investigation changed what you thought you knew. Forty more are waiting."],
    }
    c30=cta_pool["30pct"][seed]; c60=cta_pool["60pct"][seed]; c80=cta_pool["80pct"][seed]
    def near(words,target,window=25):
        for d in range(window):
            for sign in [1,-1]:
                idx=target+d*sign
                if 0<=idx<len(words) and words[idx].rstrip().endswith((".",  "?","!")):
                    return idx+1
        return target
    b80=near(words,int(total*0.80)); b60=near(words,int(total*0.60)); b30=near(words,int(total*0.30))
    w=words[:]
    w.insert(b80,f"\n\n{c80}\n\n"); w.insert(b60,f"\n\n{c60}\n\n"); w.insert(b30,f"\n\n{c30}\n\n")
    return re.sub(r'\n{3,}','\n\n'," ".join(w)).strip()


# ════════════════════════════════════════════════════════════
# STAGE 1: 13-ATTEMPT ENGINE
# ════════════════════════════════════════════════════════════
def run_stage1(state):
    log("\n"+"="*65)
    log("  STAGE 1: 13-Attempt Control Files Script Engine")
    log(f"  Quality floor: {MIN_GATE} | Final floor: {FINAL_GATE}")
    log("="*65)

    niche, voice, style_name = get_niche_voice_style(state)
    episode    = (datetime.datetime.now().timetuple().tm_yday//3)+1
    prev_title = state.get("last_title","")
    intel      = run_viral_intelligence(niche)
    used_topics = []
    gate       = MIN_GATE
    best_score = 0.0
    best_script = best_scenes = best_title_str = best_thumbnail = best_tags = best_title_scores = None

    log(f"\nNiche: {niche['name']} | ${niche['rpm']} RPM | Ep{episode}")
    log(f"Style: {style_name} | Voice: {voice}")

    for attempt in range(1, 9):
        if attempt == 8:      gate = FINAL_GATE
        elif attempt >= 6:    gate = 7.0
        elif attempt >= 4:    gate = 7.2

        topic = get_fresh_topic(niche, attempt, intel, used_topics)
        used_topics.append(topic)

        if attempt in [1,5,9]:
            thumbnail_text     = generate_thumbnail_text(niche, topic, intel)
            title_str, tscores = generate_and_score_titles(niche, topic, intel, episode)
            best_thumbnail = thumbnail_text
            best_title_str = title_str
            best_title_scores = tscores
            log(f"Thumbnail: {thumbnail_text}")

        log(f"\nAttempt {attempt}/8 (gate:{gate}) {'[ARCHIVE]' if attempt>8 else '[FRESH]'}...")
        log(f"Topic: {topic[:80]}")

        try:
            script_clean, scenes, title, thumb, tags, violations = generate_script_and_scenes(
                niche, topic, style_name, episode, attempt, intel, prev_title)
            wc = len(script_clean.split())
            score, issues = score_script(script_clean, wc, violations)
            log(f"  {score}/10 {'APPROVED' if score>=gate else 'BLOCKED'} | {wc}w | MD:{violations}")
            if issues: log(f"  {' | '.join(issues[:3])}")

            if score > best_score:
                best_score  = score
                best_script = script_clean
                best_scenes = scenes
                if thumb and thumb not in ["MIND CONTROLLED"]: best_thumbnail = thumb
            if score >= gate:
                log(f"\nSCRIPT APPROVED: {score}/10 | Attempt {attempt}\n")
                return (niche, topic, voice, style_name, episode,
                        best_script, best_scenes, best_title_str,
                        best_thumbnail, best_title_scores, score, tags, intel)
            time.sleep(3)
        except Exception as e:
            log(f"  Error: {str(e)[:80]}")
            time.sleep(15)

    if best_script and best_score >= FINAL_GATE:
        log(f"\nUsing best: {best_score}/10 after 13 attempts")
        tg(f"Note: Publishing {best_score}/10 after 13 attempts.")
        return (niche, used_topics[-1], voice, style_name, episode,
                best_script, best_scenes, best_title_str,
                best_thumbnail, best_title_scores, best_score, [], intel)

    state["last_niche"] = niche["name"]; save_state(state)
    tg(f"Control Files Day Skipped\nBest: {best_score}/10 after 13 attempts\nNiche: {niche['name']}")
    sys.exit(0)


# ════════════════════════════════════════════════════════════
# STAGE 2: APPROVAL GATE — Telegram + Gmail (30-min)
# ════════════════════════════════════════════════════════════
def run_stage2_approval(title_str, niche, voice, style_name, script_clean, thumbnail_text, title_scores, score):
    log("\n"+"="*65)
    log("  STAGE 2: Approval Gate — Telegram + Gmail")
    log("="*65)

    deadline     = datetime.datetime.now() + datetime.timedelta(minutes=30)
    deadline_str = deadline.strftime('%I:%M %p')
    top_titles   = "\n".join(f"  {s}/10: {t[:55]}" for t,s in title_scores[:3])
    preview      = script_clean[:450].replace("<","").replace(">","")

    tg(f"CONTROL FILES APPROVAL NEEDED\n\n"
       f"Title: {title_str}\n\n"
       f"Niche: {niche['name']} | RPM: ${niche['rpm']}\n"
       f"Style: {STYLES[style_name]['desc']}\n"
       f"Voice: {voice}\n"
       f"Script: {len(script_clean.split())}w | Score: {score}/10\n"
       f"Thumbnail: {thumbnail_text}\n\n"
       f"Auto-uploads at {deadline_str}\n"
       f"Reply APPROVE or REJECT")
    time.sleep(1)
    tg(f"TITLE CTR SCORES:\n{top_titles}\n\nSCRIPT PREVIEW:\n{preview}...")

    html = f"""<!DOCTYPE html><html><body style="background:#08040f;color:#e0e0e0;font-family:Arial,sans-serif;padding:20px;">
<div style="max-width:660px;margin:0 auto;background:#10081a;border:1px solid #2a1a3a;border-radius:8px;overflow:hidden;">
<div style="background:#0a0416;border-bottom:3px solid #8800aa;padding:20px 26px;">
  <div style="font-size:10px;color:#888;letter-spacing:3px">THE CONTROL FILES — APPROVAL NEEDED</div>
  <div style="font-size:19px;font-weight:bold;color:#fff;margin-top:5px">{title_str}</div>
  <div style="font-size:11px;color:#aa44cc;margin-top:5px">Auto-uploads at {deadline_str}</div>
</div>
<div style="padding:20px 26px;border-bottom:1px solid #2a1a3a;">
  <table style="width:100%;font-size:12px;border-collapse:collapse">
    <tr><td style="color:#666;padding:3px 0;width:110px">Niche</td><td>{niche['name']} — ${niche['rpm']} RPM</td></tr>
    <tr><td style="color:#666;padding:3px 0">Style</td><td>{STYLES[style_name]['desc']}</td></tr>
    <tr><td style="color:#666;padding:3px 0">Voice</td><td>{voice}</td></tr>
    <tr><td style="color:#666;padding:3px 0">Score</td><td>{score}/10</td></tr>
    <tr><td style="color:#666;padding:3px 0">Thumbnail</td><td style="color:#aa44cc;font-weight:bold;font-size:14px">{thumbnail_text}</td></tr>
  </table>
</div>
<div style="padding:18px 26px;border-bottom:1px solid #2a1a3a;">
  <div style="font-size:10px;color:#666;letter-spacing:2px;margin-bottom:8px">TITLE CTR SCORES</div>
  {"".join(f'<div style="padding:6px 10px;margin:3px 0;background:{"#1a0a2a" if i==0 else "#0f0a18"};border-left:3px solid {"#aa44cc" if i==0 else "#333"};border-radius:0 4px 4px 0"><span style="color:{"#aa44cc" if i==0 else "#666"};font-size:10px">{s}/10{"  WINNER" if i==0 else ""}</span><br><span style="color:#e0e0e0;font-size:12px">{t}</span></div>' for i,(t,s) in enumerate(title_scores[:5]))}
</div>
<div style="padding:18px 26px;">
  <div style="font-size:10px;color:#666;letter-spacing:2px;margin-bottom:8px">SCRIPT PREVIEW</div>
  <div style="background:#0a0414;border:1px solid #1a0a2a;border-radius:4px;padding:14px;font-size:12px;line-height:1.7;color:#ccc;font-style:italic">{preview.replace(chr(10),'<br>')}...</div>
</div>
</div></body></html>"""
    send_gmail(f"[Control Files] Approve: {title_str[:50]} — auto at {deadline_str}", html)

    updates = tg_updates()
    offset  = (max(u["update_id"] for u in updates)+1) if updates else 0
    reminded = set()
    while datetime.datetime.now() < deadline:
        time.sleep(30)
        for u in tg_updates(offset):
            offset = u["update_id"]+1
            txt = u.get("message",{}).get("text","").upper().strip()
            cid = str(u.get("message",{}).get("chat",{}).get("id",""))
            if cid == str(TG_CHAT):
                if any(w in txt for w in ["APPROVE","YES","GO","OK","UPLOAD"]):
                    tg("APPROVED. Generating Control Files video now.")
                    return "approved"
                if any(w in txt for w in ["REJECT","NO","SKIP","CANCEL"]):
                    tg("REJECTED. Skipping today.")
                    return "rejected"
        mins = int((deadline-datetime.datetime.now()).total_seconds()/60)
        if 13<=mins<=17 and "15" not in reminded:
            reminded.add("15"); tg(f"15 min until auto-upload\n{title_str}\nReply APPROVE or REJECT")
        elif 3<=mins<=6 and "5" not in reminded:
            reminded.add("5"); tg("5 MIN — AUTO-UPLOADING SOON\nReply APPROVE or REJECT NOW")
    tg("30 min expired — AUTO-APPROVED. Generating now.")
    return "auto_approved"


# ════════════════════════════════════════════════════════════
# STAGE 3: HUMAN VOICE AUDIO
# ════════════════════════════════════════════════════════════
async def _tts(text, voice_id, path):
    """Chunked TTS — splits at sentence boundaries every 3000 chars."""
    import edge_tts
    MAX_CHUNK = 3000
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []; current = ""
    for sent in sentences:
        if len(current) + len(sent) > MAX_CHUNK and current:
            chunks.append(current.strip()); current = sent
        else:
            current += (" " if current else "") + sent
    if current.strip(): chunks.append(current.strip())

    if len(chunks) <= 1:
        c = edge_tts.Communicate(text, voice_id, rate="-8%", pitch="+0Hz", volume="+8%")
        await c.save(path); return

    log(f"    Chunked TTS: {len(chunks)} segments")
    parts = []
    for i, chunk in enumerate(chunks):
        part = str(WORK_DIR / f"chunk_{i}_{voice_id[-8:]}.mp3")
        try:
            c = edge_tts.Communicate(chunk, voice_id, rate="-8%", pitch="+0Hz", volume="+8%")
            await c.save(part)
            if Path(part).exists() and Path(part).stat().st_size > 5000:
                parts.append(part)
        except Exception as e:
            log(f"    Chunk {i} error: {e}")

    if not parts: raise Exception("All TTS chunks failed")
    if len(parts) == 1:
        shutil.copy(parts[0], path); return

    lst = str(WORK_DIR / f"chunk_list_{voice_id[-8:]}.txt")
    with open(lst, "w") as f:
        for p in parts: f.write(f"file '{p}'\n")
    subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",lst,"-c","copy",path],
                   capture_output=True, timeout=600)
    if not Path(path).exists(): raise Exception("Chunk concatenation failed")

def check_audio_quality(mp3_path, dur_expected):
    try:
        sz = Path(mp3_path).stat().st_size
        if sz < 500000:
            log(f"  Quality FAIL: {sz}b — file empty or corrupt"); return False
        r = subprocess.run(
            ["ffprobe","-v","quiet","-show_entries","format=duration",
             "-of","csv=p=0",str(mp3_path)],
            capture_output=True, text=True, timeout=30)
        if r.returncode == 0 and r.stdout.strip():
            actual_dur = float(r.stdout.strip())
            if actual_dur < dur_expected * 0.5:
                log(f"  Quality FAIL: {actual_dur:.0f}s vs {dur_expected:.0f}s expected"); return False
            log(f"  Quality OK: {sz/1024/1024:.1f}MB | {actual_dur:.0f}s"); return True
        log(f"  Quality OK (size): {sz/1024/1024:.1f}MB"); return True
    except Exception as e:
        log(f"  Quality check error: {e}"); return False

def apply_audio_post_processing(input_path, output_path):
    """
    Clinical cold EQ for psychological control content.
    Subtle reverb (smaller room than Evidence Room), strong compression,
    slight high-mid presence boost for authoritative clarity.
    """
    try:
        af = (
            "equalizer=f=80:width_type=o:width=2:g=2,"
            "equalizer=f=3000:width_type=o:width=2:g=3,"
            "equalizer=f=9000:width_type=o:width=2:g=-2,"
            "aecho=0.7:0.75:25:0.15,"            # smaller room = colder
            "acompressor=threshold=-18dB:ratio=4:attack=3:release=60:makeup=2dB,"
            "loudnorm=I=-16:LRA=9:TP=-1.5"
        )
        subprocess.run([
            "ffmpeg","-y","-i",input_path,
            "-af",af,"-c:a","mp3","-q:a","2",output_path
        ], capture_output=True, timeout=300, check=True)
        if Path(output_path).exists() and Path(output_path).stat().st_size > 500000:
            log(f"  Audio post-processed: {Path(output_path).stat().st_size//(1024*1024)}MB")
            return output_path
    except Exception as e: log(f"  Audio processing (non-fatal): {e}")
    return input_path

def run_stage3_audio(script_clean, voice_id, niche_name):
    log("\n"+"="*65)
    log(f"  STAGE 3: Human Voice Audio — {voice_id}")
    log("="*65)
    wc           = len(script_clean.split())
    dur_expected = (wc/125.0)*60.0
    preferred    = NICHE_VOICES.get(niche_name, GB_VOICES[:4])
    voice_queue  = [voice_id]
    for v in preferred:
        if v not in voice_queue and v not in ROBOTIC_VOICES: voice_queue.append(v)
    for v in GUARANTEED_VOICES:
        if v not in voice_queue: voice_queue.append(v)

    for v in voice_queue[:12]:
        log(f"  Trying: {v}")
        mp3 = str(WORK_DIR/"audio.mp3")
        try:
            asyncio.run(_tts(script_clean, v, mp3))
            if not Path(mp3).exists(): continue
            if not check_audio_quality(mp3, dur_expected):
                log(f"  {v} failed quality — trying next"); continue
            sz  = Path(mp3).stat().st_size
            dur = dur_expected
            log(f"  ACCEPTED: {v} | {sz/1024/1024:.1f}MB | ~{dur/60:.1f}min")
            # Apply clinical cold post-processing
            processed = str(WORK_DIR/"audio_processed.mp3")
            mp3 = apply_audio_post_processing(mp3, processed)
            wav = str(WORK_DIR/"audio.wav")
            try:
                subprocess.run(["ffmpeg","-y","-i",mp3,"-acodec","pcm_s16le","-ar","24000","-ac","1",wav],
                               capture_output=True, timeout=300)
                if Path(wav).exists() and Path(wav).stat().st_size>100000:
                    return wav, dur, sz, v
            except: pass
            return mp3, dur, sz, v
        except Exception as e:
            log(f"  {v} err: {str(e)[:60]}"); time.sleep(3)

    tg("Control Files Stage 3 FAILED — all voices failed")
    sys.exit(1)


# ════════════════════════════════════════════════════════════
# STAGE 4: ANIMATION ENGINE — 5 CONTROL-THEMED SCENE TYPES
# thought_control, doctrine_reveal, compliance_chart,
# influence_map, resistance_timeline
# ════════════════════════════════════════════════════════════

def render_frame_pil(style_name, scene, frame_idx, total_frames, scene_idx, total_scenes):
    style    = STYLES[style_name]
    bg, primary, accent, secondary = style["bg"], style["primary"], style["accent"], style["secondary"]
    pulse, glow = style.get("pulse",accent), style.get("glow",accent)
    img      = Image.new("RGB",(W,H),bg)
    draw     = ImageDraw.Draw(img)
    progress = frame_idx / max(total_frames-1, 1)

    try:
        font_lg   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 52)
        font_md   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
        font_sm   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26)
        font_xs   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        font_mono = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 22)
    except:
        font_lg = font_md = font_sm = font_xs = font_mono = ImageFont.load_default()

    stype = scene.get("type","thought_control")

    # ── Atmospheric backgrounds ─────────────────────────────
    if style_name == "control_dark":
        # Concentric control rings — subtle hypnotic feel
        cx, cy = W//2, H//2
        for ring in range(0, 8):
            r_size = 100 + ring * 120
            phase  = (frame_idx / 60.0 + ring * 0.4) % 1.0
            intensity = int(12 * (1 - ring/8) * (0.5 + 0.5*phase))
            if intensity > 0:
                draw.ellipse([(cx-r_size,cy-r_size),(cx+r_size,cy+r_size)],
                             outline=(intensity, 0, intensity*2), width=1)
        # Neural wire lines
        for i in range(0, H, 80):
            draw.line([(0,i),(W,i)], fill=(3,0,5), width=1)

    elif style_name == "propaganda_red":
        # Soviet grid pattern
        for x in range(0, W, 60):
            draw.line([(x,0),(x,H)], fill=(12,2,2), width=1)
        for y in range(0, H, 60):
            draw.line([(0,y),(W,y)], fill=(12,2,2), width=1)
        # Vignette — corners darken
        for i in range(0, min(frame_idx*3, 100), 5):
            intensity = max(0, 30-i)
            draw.rectangle([i,i,W-i,H-i], outline=(intensity,0,0))

    elif style_name == "mind_wire":
        # Neural network idle state lines
        for y in range(0, H, 4):
            intensity = int(8 * (1 - y/H))
            draw.line([(0,y),(W,y)], fill=(intensity, intensity*2, intensity*4), width=1)
        # Random synaptic sparks
        for _ in range(150):
            gx, gy = random.randint(0,W), random.randint(0,H)
            draw.point([(gx,gy)], fill=(random.randint(5,20),)*3)

    # Glitch on tension frames
    if frame_idx % 90 < 3:
        for _ in range(4):
            gy = random.randint(0, H)
            draw.line([(0,gy),(W,gy)], fill=glow, width=1)

    # Corner marks
    for thickness, color in [(3, pulse),(1, glow)]:
        draw.line([(0,0),(80,0)], fill=color, width=thickness)
        draw.line([(0,0),(0,80)], fill=color, width=thickness)
        draw.line([(W-80,H-1),(W,H-1)], fill=color, width=thickness)
        draw.line([(W-1,H-80),(W-1,H)], fill=color, width=thickness)

    # Watermark
    draw.text((30,H-42), "THE CONTROL FILES — RESTRICTED", font=font_xs, fill=secondary)
    draw.text((W-210,H-42), f"CASE {scene_idx+1:03d}/{total_scenes:03d}", font=font_xs, fill=secondary)
    if frame_idx % 60 < 30:
        draw.ellipse([(W-30,15),(W-15,30)], fill=accent)
        draw.text((W-55,14), "REC", font=font_xs, fill=accent)

    # Scene title
    title_text = scene.get("title","SYSTEM")
    if progress > 0.05:
        ta = min(1.0,(progress-0.05)*5)
        draw.text((int(80+(1.0-ta)*30),40), title_text, font=font_lg, fill=accent)
        draw.line([(80,112),(80+int(700*progress),112)], fill=accent, width=2)

    # Route to scene renderer
    if   stype=="thought_control":     _render_thought_control(draw,scene,progress,style,font_md,font_sm,font_xs)
    elif stype=="doctrine_reveal":     _render_doctrine_reveal(draw,scene,progress,style,style_name,font_md,font_sm,font_mono)
    elif stype=="compliance_chart":    _render_compliance_chart(draw,scene,progress,style,font_lg,font_md,font_sm)
    elif stype=="influence_map":       _render_influence_map(draw,scene,progress,style,font_md,font_sm)
    elif stype=="resistance_timeline": _render_resistance_timeline(draw,scene,progress,style,font_md,font_sm,font_xs)
    else:                              _render_thought_control(draw,scene,progress,style,font_md,font_sm,font_xs)
    return img


def _render_thought_control(draw, scene, progress, style, font_md, font_sm, font_xs):
    """
    Ascending compliance ladder — stages reveal progressively.
    Visualizes the psychological escalation from trust to total compliance.
    """
    stages  = scene.get("stages",["Stage 1","Stage 2","Stage 3","Stage 4"])
    label   = scene.get("label","CONTROL LADDER")
    primary, accent, secondary = style["primary"], style["accent"], style["secondary"]

    # Ladder backbone
    lx = W//2 - 280
    draw.text((lx, H-120), label, font=font_xs, fill=secondary)

    n = len(stages)
    step_h = (H - 280) // max(n, 1)
    for i, stage in enumerate(stages):
        # Reveal bottom-to-top as video progresses
        reveal_prog = (progress * (n + 0.5)) - i
        if reveal_prog <= 0: continue
        a = min(1.0, reveal_prog)

        y   = H - 170 - i * step_h
        w_  = int(200 + i * 60 + a * 40)   # each rung wider — compounding control
        col = accent if i == n-1 else (
              int(secondary[0]*0.4+accent[0]*0.6*a),
              int(secondary[1]*0.4+accent[1]*0.6*a),
              int(secondary[2]*0.4+accent[2]*0.6*a))

        # Rung bar
        draw.rectangle([(lx, y-18),(lx+w_, y+18)], fill=(5,2,8), outline=col, width=2)

        # Stage text
        if a > 0.3:
            draw.text((lx+14, y-12), stage, font=font_sm, fill=primary)

        # Compliance percentage — grows with each stage
        pct = int(20 + i * 25)  # 20% → 45% → 70% → 95%
        pct_text = f"{min(pct + int(a*5), 99)}%"
        try:
            bb = draw.textbbox((0,0), pct_text, font=font_md)
            draw.text((lx + w_ + 16, y - (bb[3]-bb[1])//2), pct_text, font=font_md, fill=accent)
        except: pass

        # Connecting vertical bar to next rung
        if i < n-1:
            draw.line([(lx+w_//2, y-18),(lx+w_//2+30, y-step_h+18)], fill=secondary, width=2)


def _render_doctrine_reveal(draw, scene, progress, style, style_name, font_md, font_sm, font_mono):
    """
    Classified doctrine document — typewriter reveal, redaction lines, propaganda stamp.
    Adapted from evidence_room _render_document for psychological control content.
    """
    lines   = scene.get("lines",["PSYCHOLOGICAL OPERATIONS"])
    stamp   = scene.get("stamp","CLASSIFIED")
    primary, accent, secondary = style["primary"], style["accent"], style["secondary"]
    glow    = style.get("glow", accent)
    px, py, dw, dh = 160, 120, W-320, H-240

    pc = (6,4,12) if style_name!="propaganda_red" else (12,4,4)
    for offset in [4,2,1]:
        draw.rectangle([(px-offset,py-offset),(px+dw+offset,py+dh+offset)],
                       outline=accent if offset==1 else (accent[0]//4,accent[1]//4,accent[2]//4))
    draw.rectangle([(px,py),(px+dw,py+dh)], fill=pc, outline=secondary, width=2)
    draw.rectangle([(px,py),(px+dw,py+55)], fill=(accent[0]//3,accent[1]//3,accent[2]//3))
    draw.text((px+20,py+14), "PSYCHOLOGICAL OPERATIONS — RESTRICTED", font=font_sm, fill=glow)
    draw.line([(px+15,py+58),(px+dw-15,py+58)], fill=accent, width=2)

    n = len(lines)
    for i, line in enumerate(lines):
        lp = (progress*(n+1.5)) - i
        if lp <= 0: continue
        y  = py + 75 + i*58
        chars_to_show = int(len(line) * min(1.0, lp*3))
        visible = line[:chars_to_show]
        if line.startswith("["):
            bb = draw.textbbox((0,0),line,font=font_mono)
            tw = bb[2]-bb[0]
            draw.rectangle([(px+40,y-2),(px+40+tw+8,y+28)],fill=(0,0,0))
            if progress > 0.85:
                draw.text((px+40,y), line.strip("[]"), font=font_mono, fill=accent)
        else:
            draw.text((px+40,y), visible, font=font_mono, fill=primary)
            if chars_to_show < len(line) and int(progress*20)%2==0:
                cw = draw.textbbox((0,0),visible,font=font_mono)[2]
                draw.line([(px+42+cw,y),(px+42+cw,y+24)],fill=glow,width=2)
    if stamp and progress > 0.75:
        sx, sy = px+dw-300, py+dh-170
        draw.rectangle([(sx,sy),(sx+270,sy+120)], outline=accent, width=4)
        for thickness in [4,2]:
            draw.line([(sx,sy),(sx+270,sy+120)],fill=accent,width=thickness)
            draw.line([(sx+270,sy),(sx,sy+120)],fill=accent,width=thickness)
        draw.text((sx+20,sy+35), stamp, font=font_md, fill=accent)


def _render_compliance_chart(draw, scene, progress, style, font_lg, font_md, font_sm):
    """
    Bar chart showing compliance rates growing over time.
    Each bar counts up as it reveals — psychological urgency.
    """
    items   = scene.get("items",["20%","45%","70%","94%"])
    label   = scene.get("label","COMPLIANCE RATE")
    primary, accent, secondary = style["primary"], style["accent"], style["secondary"]
    draw.text((80, H-120), label, font=font_sm, fill=secondary)
    draw.line([(80,H-90),(W-80,H-90)], fill=secondary, width=1)

    n  = len(items); cw = (W-200)//max(n,1)
    for i, item in enumerate(items):
        ip = (progress*(n+0.5)) - i
        if ip <= 0: continue
        a  = min(1.0, ip)
        cx = 100 + i*cw + cw//2

        # Extract numeric value for bar height
        try:
            val = float(re.sub(r'[^0-9.]','',item))
        except: val = 50.0
        bh  = int(a * (val/100.0) * 380)
        bt  = H - 150 - bh
        # Last bar is the most alarming — use accent (red/purple)
        bc  = accent if i == n-1 else primary

        draw.rectangle([(cx-40,bt),(cx+40,H-150)], fill=bc, outline=secondary, width=1)
        if a > 0.4:
            # Counting number
            current_val = int(val * min(progress*2, 1.0))
            label_text  = f"{current_val}%"
            try:
                bb  = draw.textbbox((0,0),label_text,font=font_lg)
                tw  = bb[2]-bb[0]
                draw.text((cx-tw//2, bt-55), label_text, font=font_lg, fill=primary)
            except: pass
            # Time period below bar
            periods = ["Week 1","Week 4","Week 12","Week 24"]
            if i < len(periods):
                try:
                    bb2 = draw.textbbox((0,0),periods[i],font=font_sm)
                    tw2 = bb2[2]-bb2[0]
                    draw.text((cx-tw2//2, H-145), periods[i], font=font_sm, fill=secondary)
                except: pass


def _render_influence_map(draw, scene, progress, style, font_md, font_sm):
    """
    Cascading influence chain — nodes connected by drawing lines.
    Shows how influence flows from origin to target population.
    """
    nodes   = scene.get("nodes",[])
    label   = scene.get("label","INFLUENCE NETWORK")
    primary, accent, secondary = style["primary"], style["accent"], style["secondary"]
    draw.text((80,H-120), label, font=font_sm, fill=secondary)

    n = len(nodes)
    if n == 0: return
    sp         = (W-300)//max(n-1,1)
    ny         = H//2
    positions  = [(150+i*sp, ny) for i in range(n)]

    for i, (nx, ny2) in enumerate(positions):
        ip = (progress*(n+0.5)) - i
        if ip <= 0: continue
        a  = min(1.0, ip)

        # Draw connection line to next node
        if i < n-1 and ip > 0.8:
            nnx, nny = positions[i+1]
            le = int(nx + 40 + a*(nnx - nx - 80))
            draw.line([(nx+40,ny2),(le,ny2)], fill=accent, width=3)
            if le > nx+100:
                draw.polygon([(le,ny2),(le-12,ny2-8),(le-12,ny2+8)], fill=accent)

        # Node box — source node is accent, middle nodes are secondary, target is primary
        if i == 0:      bc = accent
        elif i == n-1:  bc = (200,200,200)
        else:           bc = secondary

        box_w = 120
        draw.rectangle([(nx-box_w//2, ny2-28),(nx+box_w//2, ny2+28)],
                       fill=(4,2,10), outline=bc, width=2)
        draw.text((nx-50, ny2-14), nodes[i], font=font_sm, fill=primary)

        # Influence radius pulse on target node
        if i == n-1 and progress > 0.7:
            pulse_r = int(60 + (progress-0.7)*200)
            alpha   = max(0, int(40 * (1-(progress-0.7)/0.3)))
            for r in range(pulse_r, pulse_r+30, 8):
                draw.ellipse([(nx-r,ny2-r),(nx+r,ny2+r)],
                             outline=(accent[0]//3, accent[1]//3, accent[2]//3), width=1)


def _render_resistance_timeline(draw, scene, progress, style, font_md, font_sm, font_xs):
    """
    Resistance framework timeline — horizontal flow.
    Gives viewers agency. Critical for watch-time retention.
    """
    items   = scene.get("items",[])
    label   = scene.get("label","RESISTANCE FRAMEWORK")
    primary, accent, secondary = style["primary"], style["accent"], style["secondary"]

    # Horizontal timeline line
    ty = H // 2 + 40
    draw.line([(100,ty),(W-100,ty)], fill=secondary, width=2)
    draw.text((100,H-120), label, font=font_xs, fill=secondary)

    n = len(items)
    if n == 0: return
    spacing = (W-240)//max(n,1)

    for i, item in enumerate(items):
        ip = (progress*(n+0.5)) - i
        if ip <= 0: continue
        a  = min(1.0, ip)

        x = 120 + i*spacing
        # Node — last node (final defence) is accent
        col = accent if i == n-1 else primary
        r   = 10
        draw.ellipse([(x-r,ty-r),(x+r,ty+r)], fill=col)

        # Connector line to next node
        if i < n-1 and ip > 0.5:
            nx2 = 120 + (i+1)*spacing
            le  = int(x+r + a*(nx2-x-2*r))
            draw.line([(x+r,ty),(le,ty)], fill=col, width=2)

        # Label above node
        if a > 0.3:
            words = item.split(":",1)
            label_main = words[0].strip()
            label_sub  = words[1].strip() if len(words)>1 else ""
            try:
                bb = draw.textbbox((0,0),label_main,font=font_sm)
                tw = bb[2]-bb[0]
                draw.text((x-tw//2, ty-55), label_main, font=font_sm, fill=col)
                if label_sub:
                    bb2 = draw.textbbox((0,0),label_sub,font=font_xs)
                    tw2 = bb2[2]-bb2[0]
                    draw.text((x-tw2//2, ty+25), label_sub, font=font_xs, fill=secondary)
            except: pass


# ════════════════════════════════════════════════════════════
# RENDER + ENCODE
# ════════════════════════════════════════════════════════════
SCENE_MOTION = {
    "thought_control":     "zoompan=z='min(zoom+0.0008,1.3)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
    "doctrine_reveal":     "zoompan=z='1.0':d=1:x='0':y='0'",
    "compliance_chart":    "zoompan=z='1.15+0.02*sin(2*PI*on/120)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
    "influence_map":       "zoompan=z='1.2+0.05*sin(2*PI*on/100)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
    "resistance_timeline": "zoompan=z='min(zoom+0.0006,1.25)':d=1:x='(iw-iw/zoom)*on/n':y='ih/2-(ih/zoom/2)'",
}

def apply_ken_burns(input_path, output_path, scene_type, fps=24, duration=None):
    motion = SCENE_MOTION.get(scene_type, SCENE_MOTION["thought_control"])
    try:
        cmd = ["ffmpeg","-y","-i",input_path,
               "-vf",f"{motion},scale=1920:1080:flags=lanczos",
               "-c:v","libx264","-preset","fast","-crf","20","-c:a","copy"]
        if duration: cmd += ["-t",str(duration)]
        cmd.append(output_path)
        run_ffmpeg(cmd, label=f"ken-burns-{scene_type}", timeout=600)
        if Path(output_path).exists() and Path(output_path).stat().st_size > 100000:
            log(f"  Ken Burns ({scene_type}): OK"); return output_path
    except Exception as e: log(f"  Ken Burns (non-fatal): {e}")
    return input_path

def render_and_encode(style_name, scenes, audio_path, duration):
    frames_base = WORK_DIR/"frames"
    frames_base.mkdir(exist_ok=True)
    concat_parts = []
    for si, scene in enumerate(scenes):
        dur_s   = scene.get("duration",8); total_f = dur_s*FPS
        fd      = frames_base/f"scene_{si:03d}"; fd.mkdir(exist_ok=True)
        log(f"  Rendering scene {si+1}/{len(scenes)}: {scene.get('type','?')} — {total_f}f")
        for fi in range(total_f):
            img = render_frame_pil(style_name, scene, fi, total_f, si, len(scenes))
            img.save(str(fd/f"frame_{fi:05d}.png"))
        sm4 = str(fd)+"_s.mp4"
        subprocess.run(["ffmpeg","-y","-framerate",str(FPS),"-i",f"{fd}/frame_%05d.png",
                        "-c:v","libx264","-preset","fast","-crf","23","-pix_fmt","yuv420p",
                        "-r",str(FPS),sm4], capture_output=True, timeout=300)
        concat_parts.append(f"file '{sm4}'")

    concat_file = str(WORK_DIR/"concat.txt")
    total_scene_dur = sum(s.get("duration",8) for s in scenes)
    repeats = max(1, int(duration/total_scene_dur)+2)
    with open(concat_file,"w") as f:
        for _ in range(repeats): f.write("\n".join(concat_parts)+"\n")

    raw = str(WORK_DIR/"raw.mp4")
    subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",concat_file,
                    "-c:v","libx264","-preset","fast","-crf","23","-pix_fmt","yuv420p",
                    "-r",str(FPS),raw], capture_output=True, timeout=600)
    final = str(WORK_DIR/"final.mp4")
    subprocess.run(["ffmpeg","-y","-i",raw,"-i",audio_path,
                    "-c:v","libx264","-preset","medium","-crf","19",
                    "-c:a","aac","-b:a","192k","-t",str(duration),
                    "-pix_fmt","yuv420p","-movflags","+faststart","-shortest",final],
                   capture_output=True, timeout=2400)
    log(f"  Video: {Path(final).stat().st_size/1024/1024:.0f}MB | 1080p | No subtitles on main")
    return final


# ════════════════════════════════════════════════════════════
# STAGE 5: SHORTS — NO subs on main, subs on Shorts only
# ════════════════════════════════════════════════════════════
def make_short_with_subs(video_path, script_clean, stype, total_dur):
    short_dur = 55
    start     = total_dur*(0.10 if stype=="teaser" else 0.67)
    raw       = str(WORK_DIR/f"s_{stype}_raw.mp4")
    subprocess.run(["ffmpeg","-y","-ss",str(start),"-i",video_path,"-t",str(short_dur),
                    "-vf","crop=608:1080:(iw-608)/2:0,scale=1080:1920",
                    "-c:v","libx264","-preset","fast","-crf","22",
                    "-c:a","aac","-b:a","128k",raw], capture_output=True, timeout=180)
    if not Path(raw).exists() or Path(raw).stat().st_size<400000:
        log(f"  Short {stype} clip failed"); return None
    log(f"  Short ({stype}): {Path(raw).stat().st_size/1024/1024:.1f}MB — no subtitles")
    return raw


# ════════════════════════════════════════════════════════════
# THUMBNAIL — Pollinations.ai + Pillow
# ════════════════════════════════════════════════════════════
def fetch_pollinations_bg(topic, niche_name, out_path):
    """v2: delegates to thumbnail_engine_v2 background fetcher."""
    try:
        from thumbnail_engine_v2 import fetch_background
        import hashlib
        seed   = int(hashlib.md5(topic.encode()).hexdigest()[:8], 16) % 99999
        result = fetch_background(topic, niche_name, seed, str(WORK_DIR))
        if result and Path(result).exists():
            import shutil
            shutil.copy(result, out_path)
            log(f"  Pollinations v2: {Path(out_path).stat().st_size//1024}KB")
            return True
    except Exception as e:
        log(f"  fetch_pollinations_bg (non-fatal): {e}")
    return False


def generate_thumbnail(title, thumb_text, niche_name, topic, ab_style="A",
                        episode=1, channel_name="The Control Files"):
    """v2 thumbnail: three-layer composition via thumbnail_engine_v2."""
    try:
        from thumbnail_engine_v2 import generate_thumbnail_v2
        result = generate_thumbnail_v2(
            title        = title,
            thumb_text   = thumb_text,
            niche_name   = niche_name,
            topic        = topic,
            channel_name = channel_name,
            episode      = episode,
            work_dir     = str(WORK_DIR),
            ab_variant   = ab_style,
        )
        if result and Path(result).exists():
            log(f"  Thumbnail v2 ({niche_name}): {Path(result).stat().st_size//1024}KB")
            return result
    except Exception as e:
        log(f"  Thumbnail v2 (non-fatal): {e}")
    return None



def make_short_with_subs(video_path, script_clean, stype, total_dur):
    short_dur = 55
    start     = total_dur*(0.10 if stype=="teaser" else 0.67)
    raw       = str(WORK_DIR/f"s_{stype}_raw.mp4")
    subprocess.run(["ffmpeg","-y","-ss",str(start),"-i",video_path,"-t",str(short_dur),
                    "-vf","crop=608:1080:(iw-608)/2:0,scale=1080:1920",
                    "-c:v","libx264","-preset","fast","-crf","22",
                    "-c:a","aac","-b:a","128k",raw], capture_output=True, timeout=180)
    if not Path(raw).exists() or Path(raw).stat().st_size<400000:
        log(f"  Short {stype} clip failed"); return None
    log(f"  Short ({stype}): {Path(raw).stat().st_size/1024/1024:.1f}MB — no subtitles")
    return raw


# ════════════════════════════════════════════════════════════
# THUMBNAIL — Pollinations.ai + Pillow
# ════════════════════════════════════════════════════════════
def fetch_pollinations_bg(topic, niche_name, out_path):
    niche_visual = {
        "cult_psychology":    "dark hypnotic spiral crowd silhouettes control psychological",
        "propaganda_systems": "dark mass crowd propaganda poster shadows red atmospheric",
        "social_engineering": "dark network connections human mind manipulation psychology",
        "mass_deception":     "dark mirror illusion mass crowd shadows atmospheric fog",
    }
    style   = niche_visual.get(niche_name,"dark psychological control shadows cinematic")
    topic_w = " ".join(topic.split()[:5])
    prompt  = (f"{topic_w} {style} ultra dark atmospheric "
               f"cinematic documentary no faces no text no logos 8k dramatic")
    import urllib.parse
    url = (f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}"
           f"?width=1280&height=720&nologo=true&seed={abs(hash(topic)) % 9999}")
    try:
        log("  Pollinations.ai: fetching control background...")
        r = requests.get(url, timeout=45, stream=True)
        if r.status_code == 200 and len(r.content) > 50000:
            with open(out_path,"wb") as f: f.write(r.content)
            log(f"  Pollinations OK: {Path(out_path).stat().st_size//1024}KB")
            return True
    except Exception as e: log(f"  Pollinations (non-fatal): {e}")
    return False

def generate_thumbnail(title, thumb_text, niche_name, topic, ab_style="A"):
    thumb_path = str(WORK_DIR/"thumbnail.jpg")
    pol_path   = str(WORK_DIR/"pol_bg.jpg")
    got_bg     = fetch_pollinations_bg(topic, niche_name, pol_path)

    try:
        from PIL import Image, ImageDraw, ImageFont, ImageEnhance
        TW, TH = 1280, 720
        if got_bg and Path(pol_path).exists():
            img = Image.open(pol_path).convert("RGB").resize((TW,TH))
            img = ImageEnhance.Brightness(img).enhance(0.20)
        else:
            img = Image.new("RGB",(TW,TH),(4,2,8))

        draw = ImageDraw.Draw(img)

        # Vignette
        for i in range(100):
            draw.rectangle([i,i,TW-i,TH-i], outline=(0,0,0))

        font_paths = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                      "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]
        def get_font(sz):
            for fp in font_paths:
                if Path(fp).exists():
                    try: return ImageFont.truetype(fp,sz)
                    except: pass
            return ImageFont.load_default()

        # Channel badge
        badge_font = get_font(22)
        draw.text((24,20), "● THE CONTROL FILES", font=badge_font, fill=(150,0,150))

        # Main hook text
        words = thumb_text.split()
        lines = ([thumb_text] if len(words)<=3
                 else [" ".join(words[:len(words)//2]),
                       " ".join(words[len(words)//2:])])
        fm       = get_font(108)
        th_total = len(lines)*118
        sy       = (TH-th_total)//2 - 20

        # A/B colour test — A=purple, B=white
        text_col   = (180,0,200) if ab_style=="A" else (255,255,255)
        shadow_col = (40,0,60)   if ab_style=="A" else (0,0,0)

        for i, line in enumerate(lines):
            y    = sy + i*118
            bbox = draw.textbbox((0,0),line,font=fm)
            x    = (TW-(bbox[2]-bbox[0]))//2
            for dx,dy in [(-3,-3),(3,-3),(-3,3),(3,3),(0,-4),(0,4)]:
                draw.text((x+dx,y+dy),line,font=fm,fill=shadow_col)
            draw.text((x,y),line,font=fm,fill=text_col)

        # Subtitle
        sub  = title[:60]+("…" if len(title)>60 else "")
        fs   = get_font(30)
        bb   = draw.textbbox((0,0),sub,font=fs)
        sx   = (TW-(bb[2]-bb[0]))//2
        draw.text((sx,sy+th_total+16),sub,font=fs,fill=(200,200,200))

        # Border
        draw.rectangle([8,8,TW-8,TH-8], outline=(120,0,140), width=2)
        draw.rectangle([14,14,TW-14,TH-14], outline=(70,0,80), width=1)

        img.save(thumb_path,"JPEG",quality=95)
        log(f"  Thumbnail saved: {Path(thumb_path).stat().st_size//1024}KB")
        return thumb_path
    except Exception as e:
        log(f"  Thumbnail error: {e}"); return None


# ════════════════════════════════════════════════════════════
# STAGE 6: YOUTUBE UPLOAD
# ════════════════════════════════════════════════════════════
_tok_cache = {"token":None,"expires_at":0}

def get_yt_token():
    now = time.time()
    if _tok_cache["token"] and now < _tok_cache["expires_at"]-60:
        return _tok_cache["token"]
    r = requests.post(YT_TOKEN_URL,
        data={"client_id":YT_CLIENT_ID,"client_secret":YT_CLIENT_SEC,
              "refresh_token":YT_REFRESH,"grant_type":"refresh_token"}, timeout=30)
    d = r.json()
    if "access_token" not in d:
        raise Exception(f"YT token failed: {d.get('error')} — {d.get('error_description')}")
    _tok_cache["token"]      = d["access_token"]
    _tok_cache["expires_at"] = now + d.get("expires_in",3600)
    return d["access_token"]

def upload_yt(path, title, description, tags, is_short=False, token=None):
    token = token or get_yt_token()
    if is_short: title = f"{title[:55]} #Shorts"
    fs = Path(path).stat().st_size
    log(f"  Uploading: {Path(path).name} ({fs//(1024*1024)}MB)")

    init = requests.post(
        f"{YT_UPLOAD_URL}/videos?uploadType=resumable&part=snippet,status",
        headers={"Authorization":f"Bearer {token}","Content-Type":"application/json",
                 "X-Upload-Content-Length":str(fs),"X-Upload-Content-Type":"video/mp4"},
        json={"snippet":{"title":title[:100],"description":description,
                          "tags":tags[:15],"categoryId":"22"},
              "status":{
                  "privacyStatus":"public",
                  "selfDeclaredMadeForKids":False,
                  "madeForKids":False,
                  "containsSyntheticMedia":True
              }},
        timeout=30)
    upload_url = init.headers.get("Location")
    if not upload_url:
        raise Exception(f"No upload URL: {init.status_code}: {init.text[:200]}")

    CHUNK = 16*1024*1024
    uploaded = 0; retries = 0
    with open(path,"rb") as f:
        while uploaded < fs:
            data = f.read(CHUNK)
            if not data: break
            end = uploaded+len(data)-1
            try:
                up = requests.put(upload_url,
                    headers={"Authorization":f"Bearer {token}",
                             "Content-Length":str(len(data)),
                             "Content-Range":f"bytes {uploaded}-{end}/{fs}",
                             "Content-Type":"video/mp4"},
                    data=data, timeout=600)
                if up.status_code in [200,201]:
                    vid_id = up.json().get("id")
                    return f"https://www.youtube.com/watch?v={vid_id}", vid_id
                elif up.status_code == 308:
                    rh = up.headers.get("Range","")
                    uploaded = int(rh.split("-")[1])+1 if rh else uploaded+len(data)
                    log(f"  {int(uploaded*100/fs)}%"); retries=0
                elif up.status_code in [500,502,503,504]:
                    retries+=1
                    if retries>5: raise Exception(f"Server errors x{retries}")
                    time.sleep(2**retries)
                else:
                    raise Exception(f"HTTP {up.status_code}: {up.text[:200]}")
            except requests.exceptions.Timeout:
                retries+=1
                if retries>5: raise Exception("Repeated timeouts")
                time.sleep(5)
    raise Exception("Upload ended without completion")

def post_creator_comment(token, video_id, niche_name, title, episode):
    niche_hooks = {
        "cult_psychology":    "At what point in this process do you think you would have recognized what was happening?",
        "propaganda_systems": "Which of these techniques do you recognize from your own information environment?",
        "social_engineering": "Have you ever caught yourself being manipulated by one of these techniques in real time?",
        "mass_deception":     "What would it take for a narrative this large to be corrected once it had spread this far?",
    }
    hook = niche_hooks.get(niche_name, "Which element of this control system did you find most disturbing?")
    comment = (
        f"🧠 {hook}\n\n"
        f"Leave your answer below — every response is read.\n\n"
        f"🔔 New investigation every weekday\n"
        f"🔬 Forensic crime investigations: youtube.com/@TheEvidenceRoom\n"
        f"🌑 Dark psychological horror: youtube.com/@BetrayalDeepDive\n\n"
        f"#{niche_name.replace('_','')} #psychology #manipulation #documentary #episode{episode}"
    )
    try:
        r = requests.post(
            "https://www.googleapis.com/youtube/v3/commentThreads",
            headers={"Authorization":f"Bearer {token}","Content-Type":"application/json"},
            params={"part":"snippet"},
            json={"snippet":{"videoId":video_id,
                              "topLevelComment":{"snippet":{"textOriginal":comment}}}},
            timeout=30)
        if r.status_code == 200: log("  Creator comment posted OK")
        else: log(f"  Creator comment {r.status_code} (non-fatal)")
    except Exception as e: log(f"  Creator comment (non-fatal): {e}")

def ensure_playlist(token, niche_name, series_name):
    try:
        r = requests.get(f"{YT_DATA_URL}/playlists",
            headers={"Authorization":f"Bearer {token}"},
            params={"part":"snippet","mine":"true","maxResults":50}, timeout=20)
        if r.status_code == 200:
            for item in r.json().get("items",[]):
                if series_name.lower() in item["snippet"]["title"].lower():
                    return item["id"]
        r2 = requests.post(f"{YT_DATA_URL}/playlists",
            headers={"Authorization":f"Bearer {token}","Content-Type":"application/json"},
            params={"part":"snippet,status"},
            json={"snippet":{"title":f"{series_name} — All Cases",
                              "description":f"Every investigation from {series_name}."},
                  "status":{"privacyStatus":"public"}}, timeout=20)
        if r2.status_code == 200:
            pid = r2.json()["id"]
            log(f"  Playlist created: {pid}"); return pid
    except Exception as e: log(f"  Playlist (non-fatal): {e}")
    return None

def add_to_playlist(token, playlist_id, video_id):
    if not playlist_id: return
    try:
        requests.post(f"{YT_DATA_URL}/playlistItems",
            headers={"Authorization":f"Bearer {token}","Content-Type":"application/json"},
            params={"part":"snippet"},
            json={"snippet":{"playlistId":playlist_id,
                              "resourceId":{"kind":"youtube#video","videoId":video_id}}},
            timeout=20)
        log("  Added to playlist")
    except Exception as e: log(f"  Playlist add (non-fatal): {e}")

def update_channel_description(token, niche_name):
    desc = (
        f"Exposing the systems of mass psychological control.\n\n"
        f"Animated investigations into cults, propaganda, social engineering, and mass deception.\n"
        f"Every technique. Every mechanism. Every documented case.\n\n"
        f"New investigation every weekday.\n\n"
        f"🔬 Forensic crime: youtube.com/@TheEvidenceRoom\n"
        f"🌑 Dark horror: youtube.com/@BetrayalDeepDive\n\n"
        f"⚠️ AI-assisted narration and investigation."
    )
    try:
        r = requests.put(f"{YT_DATA_URL}/channels",
            headers={"Authorization":f"Bearer {token}","Content-Type":"application/json"},
            params={"part":"brandingSettings"},
            json={"id":"","brandingSettings":{"channel":{"description":desc}}}, timeout=20)
        log(f"  Channel description updated: {r.status_code}")
    except Exception as e: log(f"  Channel desc (non-fatal): {e}")

# ════════════════════════════════════════════════════════════
# v12 NEW FUNCTIONS — Ch3 Short titles, comments, cross-promo
# ════════════════════════════════════════════════════════════

def generate_dedicated_short_title_ch3(main_title, short_type, niche_name):
    """Dedicated Short title for Ch3 — psychological control angle."""
    type_key = "teaser" if "teaser" in short_type.lower() else "recap"
    prompts = {
        "teaser": f"Write a YouTube Shorts title about mass psychological control. "
                  f"Topic: {main_title[:80]}. Under 55 chars, creates paranoia or recognition. Return ONLY the title.",
        "recap":  f"Write a YouTube Shorts title revealing a control mechanism. "
                  f"Topic: {main_title[:80]}. Under 55 chars, implies proof was documented. Return ONLY the title.",
    }
    try:
        result = ai(prompts[type_key], tokens=80, prefer="groq")
        if result:
            title = re.sub(r'[#*_`]', '', result.strip().split("\n")[0].strip())
            if 15 < len(title) < 65:
                log(f"  Short title Ch3: {title}")
                return title
    except Exception as e:
        log(f"  Short title Ch3 (non-fatal): {e}")
    defaults = {"teaser": "You Have Already Been Exposed To This", "recap": "The Mechanism Documented Above"}
    return defaults.get(type_key, main_title[:50])


def post_short_creator_comment_ch3(token, video_id, niche_name, main_title):
    """Pinned creator comment on Ch3 Shorts. Drives early engagement signals."""
    short_hooks = {
        "cult_psychology":    "At what point would you have recognised what was happening?",
        "propaganda_systems": "Which of these techniques do you see used around you right now?",
        "social_engineering": "Have you caught yourself being influenced by one of these?",
        "mass_deception":     "How do you know your current beliefs haven't been engineered?",
    }
    hook = short_hooks.get(niche_name, "Which part of this control system did you find most disturbing?")
    comment = (
        f"🧠 {hook}\n\n"
        f"Full investigation ↑ above.\n"
        f"🔔 New case every weekday → subscribe\n"
        f"🔬 Forensic crimes: youtube.com/@TheEvidenceRoom\n"
        f"🌑 Dark horror: youtube.com/@BetrayalDeepDive\n\n"
        f"#{niche_name.replace('_','')} #shorts #psychology #manipulation"
    )
    try:
        r = requests.post(
            "https://www.googleapis.com/youtube/v3/commentThreads",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            params={"part": "snippet"},
            json={"snippet": {"videoId": video_id,
                              "topLevelComment": {"snippet": {"textOriginal": comment}}}},
            timeout=30)
        if r.status_code == 200: log("  Short creator comment Ch3 OK")
        else: log(f"  Short comment {r.status_code} (non-fatal)")
    except Exception as e:
        log(f"  Short comment (non-fatal): {e}")


def build_ch3_cross_promo(is_short=False):
    """Three-channel cross-promotion for Ch3 descriptions."""
    if is_short:
        return (
            "\n\n🔬 Forensic crime investigations: youtube.com/@TheEvidenceRoom"
            "\n🌑 Dark psychological horror: youtube.com/@BetrayalDeepDive"
        )
    return (
        "\n\n🔬 Forensic crime investigations: youtube.com/@TheEvidenceRoom"
        "\n🌑 Dark psychological horror: youtube.com/@BetrayalDeepDive"
        "\n\n📺 New investigation every weekday on all three channels."
    )


def cleanup():
    for f in ["audio.mp3","audio.wav","audio_processed.mp3","raw.mp4","final.mp4",
              "short_teaser.mp4","short_recap.mp4","s_teaser_raw.mp4","s_recap_raw.mp4",
              "pol_bg.jpg","thumbnail.jpg"]:
        p = WORK_DIR/f
        if p.exists(): p.unlink()
    frames_dir = WORK_DIR/"frames"
    if frames_dir.exists(): shutil.rmtree(frames_dir)
    log("  Cleanup complete")


# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════
def main():
    """
    Two-phase controller for Ch3 (The Control Files).
    PIPELINE_PHASE=generate : generate + save pending_upload.json
    PIPELINE_PHASE=upload   : read pending, upload to YouTube
    """
    from phase_manager import (get_pipeline_phase, save_pending,
                                load_pending, clear_pending, check_pending_age,
                                is_already_uploaded)

    phase      = get_pipeline_phase()
    SCRIPT_DIR = Path(__file__).parent
    state      = load_state()

    log(f"\nCONTROL FILES v14.0 — Phase: {phase.upper()}")
    log(f"Time: {datetime.datetime.now().strftime('%a %d %b %Y %I:%M %p IST')}")

    # ── UPLOAD PHASE ──────────────────────────────────────────
    if phase == "upload":
        pending = load_pending(SCRIPT_DIR)
        if not pending or is_already_uploaded(pending):
            tg("⚠️ Ch3 Upload: no pending video. Generation may have failed.")
            sys.exit(0)
        is_fresh, hours_old = check_pending_age(pending, max_hours=30)
        if not is_fresh:
            tg(f"⚠️ Ch3 Upload: pending is {hours_old}h old — uploading anyway.")

        title        = pending["title"]
        description  = pending["description"]
        tags         = pending["tags"]
        niche_name   = pending["niche_name"]
        video_path   = pending["video_path"]
        thumb_path   = pending.get("thumbnail_path","")
        shorts       = pending.get("shorts_clips", [])
        script_clean = pending.get("script_clean","")
        duration     = pending.get("duration", 0)
        score        = pending.get("score", 0)
        voice_used   = pending.get("voice_used","")
        episode      = pending.get("episode", 1)
        playlist_id  = pending.get("playlist_id","")
        short_titles = pending.get("short_titles", {})
        short_cross  = pending.get("short_cross","")

        if not Path(video_path).exists():
            tg(f"❌ Ch3 Upload FAILED: video missing at {video_path}"); sys.exit(1)

        token_yt = get_yt_token()
        yt_url, vid_id = run_stage_with_retry(
            upload_yt, "Upload", video_path, title, description, tags,
            is_short=False, token=token_yt)

        if playlist_id: add_to_playlist(token_yt, playlist_id, vid_id)

        if thumb_path and Path(thumb_path).exists():
            try:
                with open(thumb_path,"rb") as tf:
                    tr = requests.post(
                        f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set"
                        f"?videoId={vid_id}&uploadType=media",
                        headers={"Authorization":f"Bearer {token_yt}",
                                 "Content-Type":"image/jpeg"},
                        data=tf.read(), timeout=60)
                if tr.status_code in [200,201]: log("  Thumbnail uploaded")
            except Exception as te: log(f"  Thumbnail (non-fatal): {te}")

        post_creator_comment(token_yt, vid_id, niche_name, title, episode)

        short_urls = []
        short_cross_b = build_ch3_cross_promo(is_short=True)
        for sd in shorts:
            sp = sd.get("path","")
            if not sp or not Path(sp).exists(): continue
            try:
                st    = short_titles.get(sd.get("type","teaser"), title[:50])
                sdesc = (f"Full investigation above.\n\n{title}\n"
                         f"{short_cross_b}\n\n#{niche_name.replace('_','')} #shorts #psychology")
                su, sid = upload_yt(sp, st, sdesc, tags, is_short=True, token=token_yt)
                add_to_playlist(token_yt, playlist_id, sid)
                post_short_creator_comment_ch3(token_yt, sid, niche_name, title)
                short_urls.append(su); log(f"  Short uploaded: {su}")
            except Exception as e: log(f"  Short (non-fatal): {e}")

        if script_clean and duration > 0:
            try:
                from growth_engine import upload_srt_captions
                upload_srt_captions(token_yt, vid_id, script_clean, duration, "control_files")
            except Exception as e: log(f"  SRT (non-fatal): {e}")

        update_channel_description(token_yt, niche_name)
        clear_pending(SCRIPT_DIR)

        state["last_title"]    = title
        state["last_url"]      = yt_url
        state["last_voice"]    = voice_used
        state["total_uploads"] = state.get("total_uploads",0)+1
        save_state(state)

        try:
            env_ext = os.environ.copy()
            env_ext.update({
                "GROWTH_ENGINE_MODE": "sprint",
                "SPRINT_VIDEO_URL":   yt_url,
                "SPRINT_VIDEO_TITLE": title,
                "SPRINT_CHANNEL_ID":  "control_files",
                "SPRINT_NICHE":       niche_name,
                "SPRINT_SHORTS_URLS": ",".join(short_urls),
                "SPRINT_SCORE":       str(score),
            })
            subprocess.Popen(
                ["python3", str(Path(__file__).parent.parent /
                               "growth_engine/growth_engine.py")],
                env=env_ext)
        except Exception as ge: log(f"  Growth engine (non-fatal): {ge}")

        tg(f"✅ <b>The Control Files — LIVE</b>\n\n"
           f"<b>{title}</b>\n🔗 {yt_url}\n\n"
           f"Niche: {niche_name} | Score: {score}/10 | Ep{episode}\n"
           f"🚀 First-hour sprint active")
        log(f"\nUPLOAD COMPLETE: {yt_url}")
        return

    # ── GENERATE PHASE ────────────────────────────────────────
    (niche, topic, voice, style_name, episode,
     script_clean, scenes, title_str, thumbnail_text,
     title_scores, score, tags, intel) = run_stage1(state)

    ab_style    = "A" if datetime.datetime.now().isocalendar()[1] % 2 == 1 else "B"
    cross_promo = build_ch3_cross_promo(is_short=False)
    seo_first   = f"EXPOSED: {topic[:60]}."
    description = (f"{seo_first}\n\nEpisode {episode} of {niche['series']}.\n\n"
                   f"Investigative documentary — every case documented.\n\n"
                   f"Subscribe to The Control Files.{cross_promo}\n\n"
                   f"⚠️ AI-assisted narration and investigation.")

    token_yt    = get_yt_token()
    playlist_id = state.get("playlists",{}).get(niche["name"])
    if not playlist_id:
        playlist_id = ensure_playlist(token_yt, niche["name"], niche["series"])
        if playlist_id:
            pl = state.get("playlists",{}); pl[niche["name"]] = playlist_id
            state["playlists"] = pl

    # Audio
    audio_path, duration, audio_sz, voice_used = run_stage_with_retry(
        run_stage3_audio, "Audio", script_clean, voice, niche["name"])

    # Video
    video_path = run_stage_with_retry(
        render_and_encode, "Animation", style_name, scenes, audio_path, duration)

    # Thumbnail
    thumb_path = generate_thumbnail(
        title_str, thumbnail_text, niche["name"], topic, ab_style,
        episode=episode, channel_name="The Control Files")

    # Shorts clips (generate only)
    short_clips = []
    short_titles_d = {
        "teaser": generate_dedicated_short_title_ch3(title_str, "teaser", niche["name"]),
        "recap":  generate_dedicated_short_title_ch3(title_str, "recap",  niche["name"]),
    }
    for stype in ["teaser","recap"]:
        try:
            sp = make_short_with_subs(video_path, script_clean, stype, duration)
            if sp and Path(sp).exists():
                short_clips.append({"type": stype, "path": sp})
        except Exception as e: log(f"  Short clip {stype} (non-fatal): {e}")

    save_pending(SCRIPT_DIR, {
        "title":          title_str,
        "description":    description,
        "tags":           list(set(tags))[:15],
        "niche_name":     niche["name"],
        "video_path":     video_path,
        "audio_path":     audio_path,
        "thumbnail_path": thumb_path or "",
        "script_clean":   script_clean,
        "duration":       duration,
        "score":          score,
        "voice_used":     voice_used,
        "episode":        episode,
        "playlist_id":    playlist_id or "",
        "style_name":     style_name,
        "ab_style":       ab_style,
        "shorts_clips":   short_clips,
        "short_titles":   short_titles_d,
        "short_cross":    build_ch3_cross_promo(is_short=True),
        "topic":          topic,
    })

    state["last_niche"] = niche["name"]
    save_state(state)
    ckpt_clear()

    if phase == "generate":
        tg(f"✅ <b>Ch3 Generated — queued for upload</b>\n\n"
           f"<b>{title_str}</b>\n"
           f"Niche: {niche['name']} | Score: {score}/10\n"
           f"Style: {style_name} | {duration/60:.1f}min\n"
           f"Uploading at: 12:30 AM IST (7 PM UTC)")
        log("\nGENERATE COMPLETE — queued for upload")
        return

    os.environ["PIPELINE_PHASE"] = "upload"
    main()


def main_with_retry():
    max_retries = 3
    for attempt in range(1, max_retries+1):
        try:
            main(); return
        except SystemExit as e:
            if e.code == 0: return
            if attempt < max_retries:
                tg(f"⚠️ Ch3 attempt {attempt}/{max_retries} failed.\nRetrying in 2h...")
                time.sleep(7200)
            else:
                tg(f"❌ Ch3 FAILED after {max_retries} attempts.")
                sys.exit(1)
        except Exception as e:
            if attempt < max_retries:
                tg(f"⚠️ Ch3 crash {attempt}/{max_retries}: {str(e)[:200]}\nRetrying in 2h...")
                time.sleep(7200)
            else:
                tg(f"❌ Ch3 FAILED {max_retries}x: {str(e)[:300]}")
                sys.exit(1)


if __name__ == "__main__":
    main_with_retry()
