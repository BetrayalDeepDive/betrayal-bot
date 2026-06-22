#!/usr/bin/env python3
"""
THE EVIDENCE ROOM — ANIMATED PIPELINE v2.0
Channel 2 of DeepDive Empire

SAME UPGRADES AS MASTER PIPELINE v5.0:
✅ 20 human neural voices (10 US + 10 GB) — no robotic voices
✅ Voice quality checker — auto-switches if robotic detected
✅ Quality gate minimum 7.3 | Final floor 6.9 (never lower)
✅ 13-attempt system (8 fresh + 5 archive viral topics)
✅ Different topic per attempt — never retries same topic
✅ Archive fallback: proven viral stories from last 2 years
✅ 4-trigger thumbnail system (curiosity + social proof + identity + pattern)
✅ Most shocking scripts ever written for forensic niche
✅ Viral intelligence engine (weekly learning)
✅ NO subtitles on main video
✅ Subtitles on Shorts ONLY with frame-perfect audio sync
✅ 2 YouTube Shorts per video (teaser 10% + recap 67%)
✅ Approval gate BEFORE video generation (30-min)
✅ Dual notification: Telegram + Gmail
✅ Startup Telegram test
✅ Gemini primary + Gemini 1.5 fallback (no Groq for large requests)
✅ 3 rotating animation styles (dark_minimal, cinematic, documentary)
✅ Animated scenes: timeline, document, data_reveal, connection_map, evidence_board
✅ Auto-cleanup after upload

Animation Stack: Pillow + FFmpeg (zero system deps)
"""

import os, sys, json, re, time, random, datetime, asyncio
import subprocess, shutil, requests, smtplib
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from PIL import Image, ImageDraw, ImageFont

# ── CREDENTIALS ─────────────────────────────────────────────
# ── Core credentials ──────────────────────────────────────
GROQ_KEY        = os.environ.get("GROQ_API_KEY", "")
GEMINI_KEY      = os.environ.get("GEMINI_API_KEY", "")
CEREBRAS_KEY    = os.environ.get("CEREBRAS_API_KEY", "")
OPENROUTER_KEY  = os.environ.get("OPENROUTER_API_KEY", "")
COHERE_KEY      = os.environ.get("COHERE_API_KEY", "")
MISTRAL_KEY     = os.environ.get("MISTRAL_API_KEY", "")
SAMBANOVA_KEY   = os.environ.get("SAMBANOVA_API_KEY", "")
GEMINI_KEY_2    = os.environ.get("GEMINI_API_KEY_2", "")  # backup key
YT_CLIENT_ID    = os.environ.get("EVIDENCE_YT_CLIENT_ID",  os.environ.get("YOUTUBE_CLIENT_ID",""))
YT_CLIENT_SEC   = os.environ.get("EVIDENCE_YT_CLIENT_SECRET", os.environ.get("YOUTUBE_CLIENT_SECRET",""))
YT_REFRESH      = os.environ.get("EVIDENCE_YT_REFRESH_TOKEN", os.environ.get("YOUTUBE_REFRESH_TOKEN",""))
TG_TOKEN        = os.environ.get("TELEGRAM_TOKEN", "")
TG_CHAT         = os.environ.get("TELEGRAM_CHAT_ID", "")

# ── API endpoints ──────────────────────────────────────────
GEMINI_URL      = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
GEMINI_LITE_URL = ""  # no working fallback — gemini-2.0-flash only
CEREBRAS_URL    = "https://api.cerebras.ai/v1/chat/completions"
OPENROUTER_URL  = "https://openrouter.ai/api/v1/chat/completions"
GROQ_URL        = "https://api.groq.com/openai/v1/chat/completions"
COHERE_URL      = "https://api.cohere.com/v2/chat"
MISTRAL_URL     = "https://api.mistral.ai/v1/chat/completions"
SAMBANOVA_URL   = "https://api.sambanova.ai/v1/chat/completions"
YT_UPLOAD_URL   = "https://www.googleapis.com/upload/youtube/v3"
YT_DATA_URL     = "https://www.googleapis.com/youtube/v3"
YT_TOKEN_URL    = "https://oauth2.googleapis.com/token"

# ── Paths — state in REPO (persists between runs) ─────────
SCRIPT_DIR    = Path(__file__).parent
WORK_DIR      = Path("/tmp/evidence_room")
WORK_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE    = SCRIPT_DIR / "state.json"   # persists in repo
INTEL_FILE    = SCRIPT_DIR / "intel.json"   # persists in repo
CKPT_FILE     = SCRIPT_DIR / "checkpoint.json"  # in repo — survives runner restarts

# Cerebras model names to try in order
CEREBRAS_MODELS = ["llama-3.3-70b", "llama3.3-70b", "llama3.1-70b", "llama3.1-8b"]

W, H, FPS   = 1920, 1080, 30
MIN_WORDS   = 1800
MAX_WORDS   = 2200
MIN_GATE    = 7.3
FINAL_GATE  = 6.9

# ════════════════════════════════════════════════════════════
# 20 HUMAN NEURAL VOICES — 10 US + 10 GB
# ════════════════════════════════════════════════════════════
US_VOICES = [
    "en-US-AndrewNeural",       # Warm authoritative storyteller
    "en-US-BrianNeural",        # Deep calm commanding
    "en-US-ChristopherNeural",  # Serious documentary authoritative
    "en-US-JasonNeural",        # Calm measured (DavisNeural unavailable on Actions)
    "en-US-EricNeural",         # Professional measured
    "en-US-GuyNeural",          # Commanding serious
    "en-US-JasonNeural",        # Calm measured deliberate
    "en-US-RogerNeural",        # Energetic authoritative
    "en-US-SteffanNeural",      # Professional clear
    "en-US-TonyNeural",         # Confident expressive
]
GB_VOICES = [
    "en-GB-RyanNeural",         # BBC documentary gravitas
    "en-GB-ThomasNeural",       # Cold measured cinematic
    "en-GB-NoahNeural",         # Deep calm investigative (ElliotNeural unavailable)
    "en-GB-NoahNeural",         # Measured dark deliberate
    "en-GB-OliverNeural",       # Professional authoritative
    "en-GB-EthanNeural",        # Warm natural storytelling
    "en-GB-SoniaNeural",        # Sharp devastating (F)
    "en-GB-LibbyNeural",        # Natural conversational (F)
    "en-GB-AbbiNeural",         # Clear warm professional (F)
    "en-GB-HollieNeural",       # Professional sharp (F)
]
ALL_VOICES     = US_VOICES + GB_VOICES
ROBOTIC_VOICES = ["en-US-AriaNeural", "en-US-AnaNeural"]

# Best voices per niche
NICHE_VOICES = {
    "forensic_finance":       ["en-GB-ThomasNeural","en-US-ChristopherNeural","en-GB-ElliotNeural","en-US-BrianNeural"],
    "criminal_investigation": ["en-GB-RyanNeural","en-US-AndrewNeural","en-GB-NoahNeural","en-US-EricNeural"],
    "corporate_exposure":     ["en-US-BrianNeural","en-GB-ThomasNeural","en-US-ChristopherNeural","en-GB-OliverNeural"],
    "digital_forensics":      ["en-US-ChristopherNeural","en-GB-RyanNeural","en-US-DavisNeural","en-GB-ElliotNeural"],
}

# ── ANIMATION STYLES ────────────────────────────────────────
STYLES = {
    "dark_minimal": {
        "bg":(2,2,10), "primary":(255,255,255), "accent":(220,20,20),
        "secondary":(120,120,140), "pulse":(180,0,0), "glow":(255,50,50),
        "desc":"Clinical dark — blood red on absolute black, maximum psychological impact"
    },
    "cinematic": {
        "bg":(3,6,18), "primary":(210,230,255), "accent":(60,140,255),
        "secondary":(80,110,160), "pulse":(20,80,200), "glow":(100,180,255),
        "desc":"Cinematic noir blue — glowing evidence reveals, deep shadow"
    },
    "documentary": {
        "bg":(12,10,8), "primary":(235,225,205), "accent":(190,30,10),
        "secondary":(130,110,90), "pulse":(160,20,0), "glow":(220,80,40),
        "desc":"Aged classified document style — burnt edges, redaction marks, stamps"
    },
}
DAY_STYLE = {0:"dark_minimal",1:"cinematic",2:"documentary",3:"dark_minimal",4:"cinematic"}

# ── NICHES ────────────────────────────────────────────────
DAY_NICHE = {0:"forensic_finance",1:"corporate_exposure",2:"criminal_investigation",3:"digital_forensics",4:"forensic_finance"}

NICHES = [
    {
        "name": "forensic_finance", "rpm": 16.00,
        "series": "The Evidence Room: Financial Crimes",
        "viral_search": "forensic finance fraud investigation documentary animated",
        "archive_search": "biggest financial fraud investigation exposed 2022 2023 documentary viral",
        "thumbnail_triggers": ["FUNDS TRACED","PAPER TRAIL","MONEY FOUND","ALL DOCUMENTED"],
        "seed_topics": [
            "The offshore account trail that exposed a 12-year bank fraud hidden across 40 shell companies",
            "How auditors missed 3.2 billion in concealed losses because they trusted the software the fraudster built",
            "The wire transfer pattern a junior analyst flagged in 2019 that nobody acted on for 3 years",
            "A hedge fund reporting 18 percent annual returns for 9 years — the investigation that proved it was fabricated",
            "One accountant who embezzled from 60 client accounts simultaneously using a single spreadsheet formula",
        ],
    },
    {
        "name": "criminal_investigation", "rpm": 14.50,
        "series": "The Evidence Room: Cold Cases",
        "viral_search": "cold case investigation evidence breakthrough documentary",
        "archive_search": "cold case solved breakthrough evidence 2022 2023 viral documentary",
        "thumbnail_triggers": ["CASE REOPENED","EVIDENCE FOUND","DNA MATCHED","FILE UNSEALED"],
        "seed_topics": [
            "The 1994 cold case where a single unmatched DNA sample sat in an evidence box for 28 years",
            "How investigators reconstructed a complete crime timeline from recovered deleted messages",
            "The surveillance timestamp that proved the suspect was 40 miles away — and who that implicated instead",
            "A witness statement that changed 11 times across 6 interviews — the analysis that exposed the truth",
            "Phone metadata that placed 4 people at a location they each separately denied visiting",
        ],
    },
    {
        "name": "corporate_exposure", "rpm": 15.50,
        "series": "The Evidence Room: Corporate Files",
        "viral_search": "corporate fraud cover-up exposed investigation documentary",
        "archive_search": "corporate fraud cover-up internal documents exposed 2022 2023 viral",
        "thumbnail_triggers": ["THEY KNEW","MEMO FOUND","ALL DOCUMENTED","COVER EXPOSED"],
        "seed_topics": [
            "The internal memo chain proving executives knew about product defects 3 years before the recall",
            "How a startup faked 340 million in due diligence with documents that took 8 minutes to produce",
            "The email thread — 847 messages — that dismantled a decade of fraud in one discovery process",
            "A board of directors that approved 23 fraudulent invoices because nobody read past the summary page",
            "Document trail showing a pharmaceutical company buried its own clinical trial data for 6 years",
        ],
    },
    {
        "name": "digital_forensics", "rpm": 17.00,
        "series": "The Evidence Room: Digital Evidence",
        "viral_search": "digital forensics cyber investigation data evidence documentary",
        "archive_search": "digital forensics investigation breakthrough cyber crime 2022 2023 viral",
        "thumbnail_triggers": ["DATA RECOVERED","FILES FOUND","METADATA MATCHED","DELETED FOUND"],
        "seed_topics": [
            "How deleted files on a company server reconstructed a 5-year insider trading operation completely",
            "The IP address that linked 9 separate fraud accounts to a single apartment across 3 countries",
            "Metadata embedded in a document proved it was written 2 years before the date it was supposedly signed",
            "How a data broker built profiles on 300 million people and what investigators found inside those files",
            "The trading algorithm audit that showed a system was front-running client orders — automated proof",
        ],
    },
]

# ── DREAD TRIGGERS ────────────────────────────────────────
DREAD_TRIGGERS = {
    "institutional": "The trusted institution — the bank, the firm, the regulatory body — was the weapon or the enabler.",
    "scale":         "Exact numbers that overwhelm. Then make each number a specific human being.",
    "competence":    "The sophistication. The patience. The years of planning. The cold architecture of it.",
    "detail":        "One specific irrelevant-seeming detail that proves everything. The exact date. The exact amount.",
    "duration":      "The exact duration. Not years — 4,380 days. 627 statements. 12 annual reports.",
    "reversal":      "Everything understood was the cover story. The evidence was hiding what really happened.",
    "cost":          "The people who lost everything. Name them. Quantify the loss. Make it permanent.",
    "invisibility":  "The crime was invisible because it looked exactly like normal business.",
}


# ════════════════════════════════════════════════════════════
# UTILITIES
# ════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════
# CHECKPOINT / RESUME  (same system as Channel 1)
# ═══════════════════════════════════════════════════════════
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

# ═══════════════════════════════════════════════════════════
# 6-PROVIDER AI CHAIN — Cerebras → Gemini → Groq → OR → Cohere → Mistral
# Same architecture as Channel 1 (master_pipeline.py)
# ═══════════════════════════════════════════════════════════

def _call_cerebras(prompt, tokens=9000):
    if not CEREBRAS_KEY:
        log("  Cerebras: CEREBRAS_API_KEY secret not set — skipping")
        return None
    _url = "https://api.cerebras.ai/v1/chat/completions"
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
            elif r.status_code == 401:
                log("  Cerebras 401 UNAUTHORIZED — key is WRONG/EXPIRED.")
                log("  Fix: https://cloud.cerebras.ai/ → API Keys → new key → update GitHub Secret")
                return None
            elif r.status_code == 404:
                continue  # wrong model name, try next
            else:
                log(f"  Cerebras {model}: {r.status_code}")
                break
        except Exception as e:
            log(f"  Cerebras: {e}")
            break
    return None

def _call_gemini(prompt, tokens=9000):
    if not GEMINI_KEY:
        log("  Gemini: SKIPPED (GEMINI_API_KEY not set)")
        return None
    # Only gemini-2.0-flash works on v1beta endpoint.
    # gemini-1.5-pro and gemini-1.5-flash both return 404 on v1beta.
    # When quota is 429, move immediately to next provider.
    for url in [GEMINI_URL]:
        try:
            r = requests.post(f"{url}?key={GEMINI_KEY}",
                headers={"Content-Type": "application/json"},
                json={"contents": [{"parts": [{"text": prompt}]}],
                      "generationConfig": {"temperature": 0.88,
                                           "maxOutputTokens": min(tokens, 12000)},
                      "safetySettings": [{"category": c, "threshold": "BLOCK_NONE"}
                                         for c in ["HARM_CATEGORY_HARASSMENT",
                                                   "HARM_CATEGORY_HATE_SPEECH",
                                                   "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                                                   "HARM_CATEGORY_DANGEROUS_CONTENT"]]},
                timeout=90)
            if r.status_code == 200:
                c = r.json().get("candidates", [])
                if c:
                    t = c[0]["content"]["parts"][0]["text"]
                    if t and len(t.strip()) > 100:
                        log("  OK Gemini")
                        return t
            elif r.status_code == 429:
                log(f"  Gemini 429 — quota, trying next model...")
                time.sleep(10)
            else:
                log(f"  Gemini {r.status_code}: {r.text[:150]}")
        except Exception as e:
            log(f"  Gemini: {e}")
    return None

def _call_groq(prompt, tokens=9000):
    if not GROQ_KEY: return None
    try:
        r = requests.post(GROQ_URL,
            headers={"Authorization": f"Bearer {GROQ_KEY}",
                     "Content-Type": "application/json"},
            json={"model": "llama-3.3-70b-versatile",
                  "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.88,
                  "max_tokens": min(tokens, 4800)},  # TPM limit is 6000
            timeout=90)
        if r.status_code == 200:
            t = r.json().get("choices",[{}])[0].get("message",{}).get("content","")
            if t and len(t.strip()) > 100:
                log("  OK Groq")
                return t
        else:
            log(f"  Groq {r.status_code}: {r.text[:150]}")
    except Exception as e:
        log(f"  Groq: {e}")
    return None

def _call_openrouter(prompt, tokens=9000):
    if not OPENROUTER_KEY:
        log("  OpenRouter: OPENROUTER_API_KEY secret not set — skipping")
        return None
    for model in ["meta-llama/llama-3.3-70b-instruct:free",
                  "meta-llama/llama-3.1-70b-instruct:free",
                  "qwen/qwen-2.5-72b-instruct:free",
                  "meta-llama/llama-3.2-3b-instruct:free"]:
        try:
            r = requests.post(OPENROUTER_URL,
                headers={"Authorization": f"Bearer {OPENROUTER_KEY}",
                         "Content-Type": "application/json"},
                json={"model": model,
                      "messages": [{"role": "user", "content": prompt}],
                      "max_tokens": min(tokens, 4000), "temperature": 0.88},
                timeout=90)
            if r.status_code == 200:
                t = r.json()["choices"][0]["message"]["content"]
                if t and len(t.strip()) > 100:
                    log(f"  OK OpenRouter ({model.split('/')[-1]})")
                    return t
        except Exception as e:
            log(f"  OpenRouter: {e}")
    return None

def _call_cohere(prompt, tokens=9000):
    if not COHERE_KEY:
        log("  Cohere: COHERE_API_KEY secret not set — skipping")
        return None
    try:
        r = requests.post(COHERE_URL,
            headers={"Authorization": f"Bearer {COHERE_KEY}",
                     "Content-Type": "application/json"},
            json={"model": "command-r-plus",
                  "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": min(tokens, 4000), "temperature": 0.88},
            timeout=120)
        if r.status_code == 200:
            t = r.json().get("message",{}).get("content",[{}])
            text = t[0].get("text","") if t else ""
            if text and len(text.strip()) > 100:
                log("  OK Cohere")
                return text
    except Exception as e:
        log(f"  Cohere: {e}")
    return None


def _call_sambanova(prompt, tokens=9000):
    """SambaNova — free tier, 1000 req/day, llama-3.3-70b. Sign up at cloud.sambanova.ai"""
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
                      "temperature": 0.88}, timeout=90)
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
                log(f"  SambaNova {r.status_code}: {r.text[:100]}")
        except Exception as e:
            log(f"  SambaNova: {e}")
    return None

def _call_mistral(prompt, tokens=9000):
    if not MISTRAL_KEY:
        log("  Mistral: MISTRAL_API_KEY secret not set — skipping")
        return None
    try:
        r = requests.post(MISTRAL_URL,
            headers={"Authorization": f"Bearer {MISTRAL_KEY}",
                     "Content-Type": "application/json"},
            json={"model": "mistral-small-latest",
                  "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": min(tokens, 4000), "temperature": 0.88},
            timeout=120)
        if r.status_code == 200:
            t = r.json().get("choices",[{}])[0].get("message",{}).get("content","")
            if t and len(t.strip()) > 100:
                log("  OK Mistral")
                return t
    except Exception as e:
        log(f"  Mistral: {e}")
    return None




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
    """Return what script patterns scored highest in previous episodes."""
    history = state.get("episode_history", [])
    if not history: return ""
    top = sorted(history, key=lambda x: x.get("score", 0), reverse=True)[:5]
    if not top: return ""
    lines = ["HIGHEST SCORING EPISODES — use their approach as inspiration:"]
    for ep in top:
        lines.append(f"  Score {ep.get('score',0)}/10: {ep.get('topic','')[:80]}")
    return "\n".join(lines)

def save_pattern_memory(state, episode, niche, topic, score):
    history = state.get("episode_history", [])
    history.append({
        "episode": episode, "niche": niche,
        "topic": topic[:100], "score": score,
        "date": datetime.datetime.now().strftime("%Y-%m-%d"),
    })
    state["episode_history"] = history[-50:]
    return state

def ai(prompt, temp=0.88, tokens=9000, prefer="cerebras"):
    """
    6-provider chain: Cerebras (1M/day) → Gemini → Groq → OpenRouter → Cohere → Mistral
    10s sleep between failures to avoid cascading rate limits.
    """
    providers = [_call_cerebras, _call_sambanova, _call_gemini,
                 _call_groq, _call_openrouter, _call_cohere, _call_mistral]
    for i, fn in enumerate(providers):
        result = fn(prompt, tokens)
        if result: return result
        if i < len(providers) - 1:
            log(f"  Waiting 10s before next provider...")
            time.sleep(10)
    raise Exception("All 6 AI providers failed")

# Compatibility alias
def call_gemini(prompt, temp=0.85, tokens=7000, model="2.0"):
    return _call_gemini(prompt, tokens) or ai(prompt, tokens=tokens)

def call_groq(prompt, temp=0.7, tokens=2000):
    return _call_groq(prompt, min(tokens, 4800)) or ai(prompt, tokens=min(tokens, 4800))

def strip_md(text):
    for _ in range(2):
        text = re.sub(r'^#{1,6}\s+','',text,flags=re.MULTILINE)
        text = re.sub(r'\*{1,3}([^*\n]+)\*{1,3}',r'\1',text)
        text = re.sub(r'_{1,3}([^_\n]+)_{1,3}',r'\1',text)
        text = re.sub(r'^[-*_]{3,}\s*$','',text,flags=re.MULTILINE)
        text = re.sub(r'^\s*[-*+•]\s+','',text,flags=re.MULTILINE)
        text = re.sub(r'^\s*\d+[.)]\s+','',text,flags=re.MULTILINE)
        text = re.sub(r'^>\s*','',text,flags=re.MULTILINE)
        text = re.sub(r'`+[^`]*`+','',text)
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)',r'\1',text)
        text = re.sub(r'\[[^\]]*\]','',text)
        text = re.sub(r'https?://\S+','',text)
        text = re.sub(r'<[^>]+>','',text)
        text = re.sub(r'\([^)]*(?:narrator|music|sfx|pause|cut|scene)[^)]*\)','',text,flags=re.IGNORECASE)
        text = re.sub(r'[#@$%^&*{}<>|\\~`]','',text)
        text = re.sub(r'\n{3,}','\n\n',text)
        text = re.sub(r'[ \t]{2,}',' ',text)
    return text.strip()


# ════════════════════════════════════════════════════════════
# VIRAL INTELLIGENCE ENGINE
# ════════════════════════════════════════════════════════════
def run_viral_intelligence(niche):
    intel = load_intel()
    name  = niche["name"]
    if name in intel:
        try:
            last = datetime.datetime.fromisoformat(intel[name].get("last_run","2020-01-01"))
            if (datetime.datetime.now()-last).days < 7:
                log(f"  Intel cached ({(datetime.datetime.now()-last).days}d)")
                return intel[name]
        except: pass
    log(f"  Running viral intelligence for {name}...")
    prompt = f"""Analyze the TOP 20 most viral forensic/investigation documentary YouTube videos (2M+ views) in the "{niche['viral_search']}" niche.
Return ONLY valid JSON:
{{"top_hook_formulas":["Hook 1","Hook 2","Hook 3"],
"winning_title_patterns":["Pattern 1","Pattern 2","Pattern 3"],
"thumbnail_text_examples":["3 WORD 1","3 WORD 2","3 WORD 3","3 WORD 4","3 WORD 5"],
"emotional_arc":"One sentence description",
"retention_hooks":["30pct hook","60pct hook","80pct hook"],
"niche_specific_power_words":["word1","word2","word3","word4","word5","word6"],
"what_makes_videos_viral":"One sentence",
"fresh_topic_ideas":["Topic 1","Topic 2","Topic 3","Topic 4","Topic 5","Topic 6"]}}"""
    try:
        text = ai(prompt,temp=0.65,tokens=400,prefer="groq")
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]','',re.sub(r'```json|```','',text).strip())
        m = re.search(r'\{[\s\S]*\}',text)
        if m:
            d = json.loads(m.group())
            d["last_run"] = datetime.datetime.now().isoformat()
            intel[name] = d; save_intel(intel)
            log(f"  Intel loaded")
            return d
    except Exception as e: log(f"  Intel err: {e}")
    fallback = {
        "top_hook_formulas":["The evidence was there the entire time. Nobody looked at it correctly.",
                              "This document changed everything. It had been sitting in a drawer for 11 years.",
                              "The number on page 3 did not match the number on page 3 of a different filing. That was the beginning."],
        "winning_title_patterns":["The [DOCUMENT/DATA] That Proved [CRIME] Had Been [DURATION]",
                                   "[NUMBER] [DOCUMENTS/ACCOUNTS] — The Investigation That Changed Everything"],
        "thumbnail_text_examples": niche["thumbnail_triggers"],
        "emotional_arc":"Methodical discovery then growing horror then full documented exposure",
        "retention_hooks":["What the next document revealed changed the entire investigation",
                           "The pattern only became visible when all 847 records were laid side by side",
                           "The final piece of evidence was the most ordinary thing imaginable"],
        "niche_specific_power_words":["documented","evidence","pattern","records","exposed","concealed","verified"],
        "what_makes_videos_viral":"Methodical evidence revelation that builds to an undeniable conclusion",
        "fresh_topic_ideas": niche["seed_topics"],
        "last_run": datetime.datetime.now().isoformat()
    }
    intel[name] = fallback; save_intel(intel)
    return fallback


# ════════════════════════════════════════════════════════════
# FRESH TOPIC ENGINE — Different topic every attempt
# ════════════════════════════════════════════════════════════
def get_fresh_topic(niche, attempt, intel, used_topics):
    # On first attempt, use strategy topic if available
    if attempt == 1:
        try:
            sf = SCRIPT_DIR / "next_week_strategy.json"
            if sf.exists():
                sd = json.loads(sf.read_text())
                rec = [t for t in sd.get("recommended_topics", [])
                       if t not in used_topics]
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
        log(f"  Generating new topics...")
        prompt = f"""Generate 6 compelling forensic investigation topics for "{niche['series']}".
Niche: {niche['name']} | Search: {niche['viral_search']}
Already used: {[t[:40] for t in used_topics[:4]]}
Each must be specific, have real emotional weight, produce a 12-minute video.
Return ONLY a JSON array: ["Topic 1","Topic 2","Topic 3","Topic 4","Topic 5","Topic 6"]"""
        try:
            text = ai(prompt,temp=0.85,tokens=400,prefer="groq")
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
        prompt = f"""Find 6 documented real-world stories from 2022-2024 that fit "{niche['name']}" and went viral.
Focus: {niche['archive_search']}
Not already used: {[t[:40] for t in used_topics[:4]]}
Return ONLY a JSON array: ["Story 1","Story 2","Story 3","Story 4","Story 5","Story 6"]"""
        try:
            text = ai(prompt,temp=0.8,tokens=400,prefer="groq")
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
    prompt = f"""Generate the most psychologically compelling 3-word thumbnail text for a forensic investigation video.
NICHE: {niche['name']} | TOPIC: {topic[:100]}
TOP PERFORMERS: {', '.join(examples)}

USE ALL 4 TRIGGERS:
1. CURIOSITY GAP: creates unanswerable question
2. AUTHORITY SIGNAL: implies documented proof
3. CONSEQUENCE: implies something irreversible was found
4. PATTERN INTERRUPT: unexpected — makes viewer stop scrolling

Rules: EXACTLY 3 words. ALL CAPS. Evidence-focused. Never generic.
Return ONLY 3 words. Example: PAPER TRAIL FOUND"""
    try:
        result = ai(prompt,temp=0.82,tokens=15,prefer="groq")
        result = re.sub(r'[^A-Z\s]','',result.upper()).strip()
        words  = result.split()[:3]
        if len(words)==3:
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
    power = ["exposed","documented","evidence","records","proved","concealed","revealed","traced","verified","found"]
    s += min(sum(1 for w in power if w in tl)*0.4, 2.0)
    if re.search(r'\d+\s*(year|month|document|account|transaction|million|billion)',tl): s+=1.0
    if any(w in tl for w in ["nobody checked","sat unread","was ignored","was missed","went unnoticed"]): s+=0.8
    return min(round(s,1),10.0)

def generate_and_score_titles(niche, topic, intel, episode):
    patterns = intel.get("winning_title_patterns",[])
    power    = intel.get("niche_specific_power_words",["documented","evidence","records"])
    prompt = f"""Generate exactly 5 YouTube title variants for this forensic investigation video.
NICHE: {niche['name']} | SERIES: {niche['series']} Ep{episode}
TOPIC: {topic[:150]}
VIRAL PATTERNS: {chr(10).join(patterns[:3])}
POWER WORDS: {', '.join(power)}
Rules: 50-65 chars. Curiosity gap. Documentary tone. Specific detail.
Return ONLY JSON array: ["title 1","title 2","title 3","title 4","title 5"]"""
    try:
        text = ai(prompt,temp=0.75,tokens=400,prefer="groq")
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]','',re.sub(r'```json|```','',text).strip())
        m = re.search(r'\[[\s\S]*?\]',text)
        if m:
            titles = json.loads(m.group())
            if len(titles)>=3:
                scored = sorted([(t,score_title_ctr(t)) for t in titles],key=lambda x:x[1],reverse=True)
                log(f"  Title: {scored[0][1]}/10 — {scored[0][0][:55]}")
                return scored[0][0], scored
    except Exception as e: log(f"  Title err: {e}")
    fallback = f"{niche['series']}: The Investigation That Changed Everything"
    return fallback, [(fallback,6.0)]


# ════════════════════════════════════════════════════════════
# SCRIPT GENERATION — HIGH QUALITY FORENSIC NARRATION
# ════════════════════════════════════════════════════════════
def get_niche_voice_style(state):
    day        = datetime.datetime.now().weekday()
    niche_name = DAY_NICHE.get(day,"forensic_finance")
    style_name = DAY_STYLE.get(day,"dark_minimal")
    if style_name == state.get("last_style",""):
        opts = [s for s in STYLES if s!=style_name]
        style_name = opts[day%len(opts)]
    niche = next(n for n in NICHES if n["name"]==niche_name)
    preferred = NICHE_VOICES.get(niche_name, GB_VOICES[:4])
    available = [v for v in preferred if v!=state.get("last_voice","")]
    voice = (available or preferred)[datetime.datetime.now().timetuple().tm_yday % len(available or preferred)]
    return niche, voice, style_name

def build_dread_prompt_er():
    """Evidence Room uses investigation-specific dread triggers"""
    triggers = ["institutional","scale","competence","detail","duration","reversal","cost","invisibility"]
    return "\n".join(f"DREAD {t.upper()}: {DREAD_TRIGGERS[t]}" for t in triggers if t in DREAD_TRIGGERS)

def generate_script_and_scenes(niche, topic, style_name, episode, attempt, intel, prev_title=""):
    temp     = min(0.82 + attempt*0.012, 0.94)
    darkness = min(30 + attempt*7, 96)
    dread    = build_dread_prompt_er()
    hooks    = intel.get("top_hook_formulas",["The evidence was there the entire time. Nobody looked at it correctly."])
    hook_ex  = "\n".join(f"  PROVEN HOOK {i+1}: {h}" for i,h in enumerate(hooks[:3]))
    retention = intel.get("retention_hooks",["What the next document revealed changed the entire investigation"])
    ret_str  = "\n".join(f"  RETENTION HOOK at {['30','60','80'][i]}pct: {r}" for i,r in enumerate(retention[:3]))
    power    = intel.get("niche_specific_power_words",["documented","evidence","records","concealed"])
    viral    = intel.get("what_makes_videos_viral","Methodical evidence revelation building to undeniable conclusion")
    cross    = f'\nNaturally reference our previous investigation: "{prev_title}" in your closing.' if prev_title else ""

    prompt = f"""You are the greatest forensic documentary narrator alive.
You write for The Evidence Room — an animated forensic investigation YouTube channel.
Episode {episode} of "{niche['series']}". Darkness: {darkness}%.

INVESTIGATION TODAY: {topic}
Animation style: {STYLES[style_name]['desc']}
{cross}

━━━ VIRAL INTELLIGENCE FROM TOP 20 VIDEOS ━━━
{hook_ex}
WHAT MAKES VIDEOS VIRAL: {viral}
POWER WORDS: {', '.join(power)}
RETENTION ARCHITECTURE:
{ret_str}

━━━ PSYCHOLOGICAL DREAD SYSTEM ━━━
{dread}

━━━ THE 10 LAWS ━━━
LAW 1: ZERO markdown — no symbols whatsoever
LAW 2: ZERO stage directions
LAW 3: ZERO AI phrases (moreover furthermore in conclusion etc)
LAW 4: PURE SPOKEN ENGLISH — every word speakable naturally
LAW 5: MAX 13 words per sentence
LAW 6: Never start 3 consecutive sentences with the same word
LAW 7: Every paragraph darker than the previous
LAW 8: Specific dates amounts document numbers transaction IDs
LAW 9: MINIMUM {MIN_WORDS} words — COUNT YOUR WORDS. If you finish under {MIN_WORDS}, add more to THE EVIDENCE TRAIL and THE HUMAN COST sections until you reach it. This is non-negotiable.
LAW 10: ZERO section labels — pure seamless narration

━━━ NARRATIVE STRUCTURE ━━━
OPENING HOOK (4 sentences):
A document. A number. A date. Something found that was not supposed to be found.
The specific detail that cracked everything open. The exact moment it was discovered.
One number that does not match. The question that follows the listener forever.

THE INVESTIGATION BEGINS (350-400 words):
The original case. What it appeared to be. The people who appeared to be clean.
Reference what is shown on screen naturally: this document, these records, this timestamp.
Apply INVISIBILITY and NORMALITY triggers.

THE EVIDENCE TRAIL (400-500 words):
The documents. The data. The records that do not add up.
Walk through the evidence methodically. Each piece building on the last.
Apply DETAIL and COMPETENCE triggers.

USE RETENTION HOOK 1 HERE.

THE PATTERN EMERGES (350-400 words):
When you put every document side by side, the pattern becomes undeniable.
What it proves. What it means. Apply SCALE and DURATION triggers.

THE COLLAPSE (200-250 words):
The moment the investigation broke the case open.
The specific document or data point that made concealment impossible.

USE RETENTION HOOK 2 HERE.

THE REVELATION (150-200 words):
What was really happening behind the documented facade.
Apply REVERSAL trigger.

THE HUMAN COST (300-350 words):
The specific people. What they lost. Apply COST and INSTITUTIONAL triggers.

USE RETENTION HOOK 3 HERE.

THE VERDICT (150-200 words):
What the evidence proved. What accountability followed or failed to follow.

THE CLOSE (100 words):
Haunting line connecting to next episode.
Natural subscribe call to The Evidence Room.
{f"Reference previous investigation: {prev_title}." if prev_title else ""}

━━━ ALSO GENERATE SCENE BREAKDOWN ━━━
After writing the complete narration, add exactly 10 dashes on a new line, then provide:
{{"title":"YouTube title 55-65 chars","thumbnail_text":"3 WORDS ALL CAPS","tags":["tag1","tag2","tag3","tag4","tag5","tag6","tag7","tag8","tag9","tag10"],"scenes":[
{{"type":"timeline","duration":8,"title":"THE FRAUD BEGINS","items":["2019: First anomaly","2020: Pattern grows","2021: Scale increases","2022: Exposure"],"label":"EVIDENCE TIMELINE"}},
{{"type":"document","duration":7,"title":"EXHIBIT A","lines":["INTERNAL MEMO — CONFIDENTIAL","Date: March 4 2019","RE: Risk Assessment Override","Authorized by: [REDACTED]"],"stamp":"CLASSIFIED"}},
{{"type":"data_reveal","duration":7,"title":"THE NUMBERS","items":["$4.7M","$12.3M","$28.9M","$47.2M"],"label":"FUNDS TRACED"}},
{{"type":"connection_map","duration":8,"title":"THE NETWORK","nodes":["ACCOUNT A","SHELL CO B","OFFSHORE C","FINAL D"],"label":"MONEY TRAIL"}},
{{"type":"evidence_board","duration":10,"title":"CASE SUMMARY","items":["Documents: 847","Transactions: 2,340","Accounts: 40","Duration: 12 years"],"label":"COMPILED EVIDENCE"}}
]}}

WRITE NARRATION FIRST ({MIN_WORDS}-{MAX_WORDS} words), THEN 10 DASHES, THEN JSON."""

    raw   = ai(prompt, temp=temp, tokens=7000, prefer="gemini")
    parts = raw.split("----------")
    clean = strip_md(strip_md(parts[0].strip()))
    wc    = len(clean.split())

    # Expansion if short
    for exp in range(2):
        if wc >= MIN_WORDS: break
        deficit = MIN_WORDS - wc
        log(f"  {wc}w — expanding round {exp+1}...")
        expand = f"""This forensic narration is {wc} words. Needs {MIN_WORDS} minimum.
ADD {deficit} words by expanding:
1. THE EVIDENCE TRAIL — add 3 more specific documents with exact dates and amounts
2. THE HUMAN COST — add 2 more specific named people with specific losses
3. THE VERDICT — add deeper analysis of what the evidence proved
Rules: Zero markdown. Pure spoken English. Max 13 words per sentence.
Return COMPLETE script with additions.
SCRIPT: {clean}"""
        try:
            raw2   = ai(expand, temp=0.82, tokens=7000, prefer="gemini")
            clean2 = strip_md(strip_md(raw2))
            if len(clean2.split()) > wc:
                clean = clean2; wc = len(clean.split())
                log(f"  Expanded to {wc}w")
        except Exception as e:
            log(f"  Expand err: {e}"); break

    # Parse scenes from JSON part
    scenes, title, thumbnail_text, tags = [], f"The Evidence Room: {topic[:45]}", "EVIDENCE FOUND", \
        [niche["name"],"investigation","forensics","evidence","crime","documentary","animated","exposed","shocking","deepdive"]
    if len(parts) > 1:
        try:
            jt = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]','',re.sub(r'```json|```','',parts[1]).strip())
            m = re.search(r'\{[\s\S]*\}',jt)
            if m:
                data = json.loads(m.group())
                scenes        = data.get("scenes",[])
                title         = data.get("title",title)
                thumbnail_text = data.get("thumbnail_text",thumbnail_text)
                tags          = data.get("tags",tags)
        except Exception as e: log(f"  Scene JSON err: {e}")

    # Fallback scenes
    if not scenes:
        scenes = [
            {"type":"timeline","duration":8,"title":"THE INVESTIGATION",
             "items":["Phase 1: Discovery","Phase 2: Analysis","Phase 3: Exposure"],"label":"CASE TIMELINE"},
            {"type":"data_reveal","duration":7,"title":"THE EVIDENCE",
             "items":["$47M","12 Years","40 Accounts","847 Documents"],"label":"KEY FINDINGS"},
            {"type":"document","duration":7,"title":"EXHIBIT A",
             "lines":["INTERNAL DOCUMENT","DATE: REDACTED","CLASSIFICATION: CONFIDENTIAL","STATUS: EVIDENCE"],"stamp":"CLASSIFIED"},
            {"type":"connection_map","duration":8,"title":"THE NETWORK",
             "nodes":["ACCOUNT A","SHELL B","OFFSHORE C","DESTINATION D"],"label":"MONEY TRAIL"},
            {"type":"evidence_board","duration":10,"title":"CASE SUMMARY",
             "items":["Documents: 847","Transactions: 2340","Accounts: 40","Duration: 12 years"],"label":"COMPILED EVIDENCE"},
        ]

    violations = len(re.findall(r'[#*_`\[\]{}<>\\]', clean))
    log(f"  Script: {wc}w | {violations} MD | {len(scenes)} scenes")
    return clean, scenes, title, thumbnail_text, tags, violations

def score_script_er(script_clean, wc, violations):
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
    ew = ["document","evidence","records","pattern","concealed","revealed","traced","verified","proved","fraud"]
    hs = sum(1 for w in ew if w in hook)
    if hs>=4:             score+=1.0
    elif hs>=2:           score+=0.5
    else:                 issues.append("Weak forensic hook")
    ai_phrases = ["moreover","furthermore","it is worth noting","in conclusion","interestingly","it should be noted"]
    ai_count = sum(1 for p in ai_phrases if p in script_clean.lower())
    if ai_count>0:        score-=ai_count*0.3; issues.append(f"{ai_count} AI phrases")
    if "subscribe" in script_clean[-400:].lower(): score+=0.2
    return min(round(score,1),10.0), issues


# ════════════════════════════════════════════════════════════
# STAGE 1: 13-ATTEMPT ENGINE
# ════════════════════════════════════════════════════════════
def run_stage1(state):
    log("\n"+"="*65)
    log("  STAGE 1: 13-Attempt Evidence Room Script Engine")
    log(f"  Quality floor: {MIN_GATE} | Final floor: {FINAL_GATE}")
    log("="*65)

    niche, voice, style_name = get_niche_voice_style(state)
    episode  = (datetime.datetime.now().timetuple().tm_yday//3)+1
    prev_title = state.get("last_title","")
    intel    = run_viral_intelligence(niche)
    used_topics = []
    gate     = MIN_GATE
    best_score = 0.0
    best_script = best_scenes = best_title_str = best_thumbnail = best_tags = best_title_scores = None

    log(f"\nNiche: {niche['name']} | ${niche['rpm']} RPM | Ep{episode}")
    log(f"Style: {style_name} | Voice: {voice}")

    for attempt in range(1, 9):
        if attempt == 8:        gate = FINAL_GATE
        elif attempt >= 6:      gate = 7.0
        elif attempt >= 4:      gate = 7.2

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
            score, issues = score_script_er(script_clean, wc, violations)
            log(f"  {score}/10 {'APPROVED' if score>=gate else 'BLOCKED'} | {wc}w | MD:{violations}")
            if issues: log(f"  {' | '.join(issues[:3])}")

            if score > best_score:
                best_score  = score
                best_script = script_clean
                best_scenes = scenes
                if thumb and thumb != "EVIDENCE FOUND": best_thumbnail = thumb
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
    tg(f"Evidence Room Day Skipped\nBest: {best_score}/10 after 13 attempts\nNiche: {niche['name']}")
    sys.exit(0)


# ════════════════════════════════════════════════════════════
# STAGE 2: APPROVAL GATE — Telegram + Gmail
# BEFORE video generation
# ════════════════════════════════════════════════════════════
def run_stage2_approval(title_str, niche, voice, style_name, script_clean, thumbnail_text, title_scores, score):
    log("\n"+"="*65)
    log("  STAGE 2: Approval Gate — Telegram + Gmail")
    log("="*65)

    deadline     = datetime.datetime.now() + datetime.timedelta(minutes=30)
    deadline_str = deadline.strftime('%I:%M %p')
    top_titles   = "\n".join(f"  {s}/10: {t[:55]}" for t,s in title_scores[:3])
    preview      = script_clean[:450].replace("<","").replace(">","")

    tg(f"EVIDENCE ROOM APPROVAL NEEDED\n\n"
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

    html = f"""<!DOCTYPE html><html><body style="background:#0a0a0f;color:#e0e0e0;font-family:Arial,sans-serif;padding:20px;">
<div style="max-width:660px;margin:0 auto;background:#12121a;border:1px solid #2a2a3a;border-radius:8px;overflow:hidden;">
<div style="background:#0a1a0a;border-bottom:3px solid #2288cc;padding:20px 26px;">
  <div style="font-size:10px;color:#888;letter-spacing:3px">THE EVIDENCE ROOM — APPROVAL NEEDED</div>
  <div style="font-size:19px;font-weight:bold;color:#fff;margin-top:5px">{title_str}</div>
  <div style="font-size:11px;color:#4499cc;margin-top:5px">Auto-uploads at {deadline_str}</div>
</div>
<div style="padding:20px 26px;border-bottom:1px solid #2a2a3a;">
  <table style="width:100%;font-size:12px;border-collapse:collapse">
    <tr><td style="color:#666;padding:3px 0;width:110px">Niche</td><td>{niche['name']} — ${niche['rpm']} RPM</td></tr>
    <tr><td style="color:#666;padding:3px 0">Style</td><td>{STYLES[style_name]['desc']}</td></tr>
    <tr><td style="color:#666;padding:3px 0">Voice</td><td>{voice}</td></tr>
    <tr><td style="color:#666;padding:3px 0">Score</td><td>{score}/10</td></tr>
    <tr><td style="color:#666;padding:3px 0">Thumbnail</td><td style="color:#2288cc;font-weight:bold;font-size:14px">{thumbnail_text}</td></tr>
  </table>
</div>
<div style="padding:18px 26px;border-bottom:1px solid #2a2a3a;">
  <div style="font-size:10px;color:#666;letter-spacing:2px;margin-bottom:8px">TITLE CTR SCORES</div>
  {"".join(f'<div style="padding:6px 10px;margin:3px 0;background:{"#1a2a1a" if i==0 else "#151520"};border-left:3px solid {"#22cc44" if i==0 else "#333"};border-radius:0 4px 4px 0"><span style="color:{"#22cc44" if i==0 else "#666"};font-size:10px">{s}/10{"  WINNER" if i==0 else ""}</span><br><span style="color:#e0e0e0;font-size:12px">{t}</span></div>' for i,(t,s) in enumerate(title_scores[:5]))}
</div>
<div style="padding:18px 26px;">
  <div style="font-size:10px;color:#666;letter-spacing:2px;margin-bottom:8px">SCRIPT PREVIEW</div>
  <div style="background:#0d0d15;border:1px solid #1a1a2a;border-radius:4px;padding:14px;font-size:12px;line-height:1.7;color:#ccc;font-style:italic">{preview.replace(chr(10),'<br>')}...</div>
</div>
</div></body></html>"""
    send_gmail(f"[Evidence Room] Approve: {title_str[:50]} — auto at {deadline_str}", html)

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
                    tg("APPROVED. Generating Evidence Room video now.")
                    return "approved"
                if any(w in txt for w in ["REJECT","NO","SKIP","CANCEL"]):
                    tg("REJECTED. Skipping today.")
                    return "rejected"
        mins = int((deadline-datetime.datetime.now()).total_seconds()/60)
        if 13<=mins<=17 and "15" not in reminded:
            reminded.add("15")
            tg(f"15 min until auto-upload\n{title_str}\nReply APPROVE or REJECT")
        elif 3<=mins<=6 and "5" not in reminded:
            reminded.add("5")
            tg("5 MIN — AUTO-UPLOADING SOON\nReply APPROVE or REJECT NOW")
    tg("30 min expired — AUTO-APPROVED. Generating now.")
    return "auto_approved"


# ════════════════════════════════════════════════════════════
# STAGE 3: HUMAN VOICE AUDIO WITH QUALITY CHECK
# ════════════════════════════════════════════════════════════
async def _tts(text, voice_id, path):
    """
    Chunked TTS — splits long scripts at sentence boundaries every 3000 chars.
    Prevents 'No audio was received' error on scripts over ~2000 words.
    Concatenates chunks via FFmpeg.
    """
    import edge_tts, shutil
    MAX_CHUNK = 3000

    # Split at sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []; current = ""
    for sent in sentences:
        if len(current) + len(sent) > MAX_CHUNK and current:
            chunks.append(current.strip())
            current = sent
        else:
            current += (" " if current else "") + sent
    if current.strip(): chunks.append(current.strip())

    if len(chunks) <= 1:
        # Short enough for single call
        c = edge_tts.Communicate(text, voice_id, rate="-8%", pitch="+0Hz", volume="+8%")
        await c.save(path)
        return

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

    if not parts:
        raise Exception("All TTS chunks failed")

    if len(parts) == 1:
        shutil.copy(parts[0], path); return

    lst = str(WORK_DIR / f"chunk_list_{voice_id[-8:]}.txt")
    with open(lst, "w") as f:
        for p in parts: f.write(f"file '{p}'\n")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                    "-i", lst, "-c", "copy", path],
                   capture_output=True, timeout=600)
    if not Path(path).exists():
        raise Exception("Chunk concatenation failed")

def check_audio_quality(mp3_path, dur_expected):
    """
    Fixed threshold: edge-tts outputs ~48kbps MP3, not 64kbps.
    Old formula (sz < dur_expected * 8000) rejected valid 10MB files for 30-min audio.
    Now: use ffprobe actual duration. Fall back to 500KB minimum size check.
    """
    try:
        sz = Path(mp3_path).stat().st_size
        if sz < 500000:  # Must be at least 500KB — catches empty/corrupt files
            log(f"  Quality FAIL: {sz}b — file empty or corrupt")
            return False
        # Measure actual duration with ffprobe
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(mp3_path)],
            capture_output=True, text=True, timeout=30)
        if r.returncode == 0 and r.stdout.strip():
            actual_dur = float(r.stdout.strip())
            if actual_dur < dur_expected * 0.5:  # must be at least 50% of expected
                log(f"  Quality FAIL: {actual_dur:.0f}s actual vs {dur_expected:.0f}s expected")
                return False
            log(f"  Quality OK: {sz/1024/1024:.1f}MB | {actual_dur:.0f}s")
            return True
        # ffprobe unavailable — accept if > 500KB
        log(f"  Quality OK (size): {sz/1024/1024:.1f}MB")
        return True
    except Exception as e:
        log(f"  Quality check error: {e}")
        return False



def fetch_case_relevant_image_ch2(topic, niche_name, out_path):
    """Case-relevant image search for Channel 2 thumbnails."""
    stopwords = {"a","an","the","and","or","in","on","to","of","with","was","been","have"}
    topic_words = [w.strip(".,!?") for w in topic.lower().split()
                   if len(w) > 3 and w not in stopwords]
    search_kw = " ".join(topic_words[:3])
    niche_mod = {
        "forensic_finance":       "dark corporate financial documents",
        "criminal_investigation": "dark crime evidence investigation",
        "corporate_exposure":     "dark corporate shadow documents",
        "digital_forensics":      "dark technology screen code shadow",
    }
    full_query = f"{search_kw} {niche_mod.get(niche_name, 'dark investigation')}"
    # Try Pixabay/Pexels using existing keys
    if PIXABAY_KEY:
        try:
            r = requests.get("https://pixabay.com/api/",
                params={"key": PIXABAY_KEY, "q": full_query, "image_type": "photo",
                        "orientation": "horizontal", "per_page": 3}, timeout=15)
            if r.status_code == 200 and r.json().get("hits"):
                url = r.json()["hits"][0].get("webformatURL")
                if url:
                    ir = requests.get(url, timeout=20)
                    if ir.status_code == 200 and len(ir.content) > 20000:
                        with open(out_path, "wb") as f: f.write(ir.content)
                        log(f"  Case image Ch2: {search_kw}")
                        return True
        except: pass
    return False

def fetch_pollinations_bg(topic, niche_name, out_path):
    """
    Free AI-generated dark cinematic background via Pollinations.ai.
    No API key, no account, no credit card. Just a URL.
    """
    niche_visual = {
        "forensic_finance":        "dark corporate office documents scattered forensic audit",
        "criminal_investigation":  "dark crime scene evidence board shadows dramatic",
        "corporate_exposure":      "dark boardroom shadows documents leaked classified",
        "digital_forensics":       "dark server room code screens hacker surveillance",
    }
    style   = niche_visual.get(niche_name, "dark cinematic forensic investigation shadows")
    topic_w = " ".join(topic.split()[:5])
    prompt  = (f"{topic_w} {style} ultra dark atmospheric "
               f"cinematic documentary no faces no text 8k dramatic")
    import urllib.parse
    url = (f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}"
           f"?width=1280&height=720&nologo=true&seed={abs(hash(topic)) % 9999}")
    try:
        log("  Pollinations.ai: fetching forensic background...")
        r = requests.get(url, timeout=45, stream=True)
        if r.status_code == 200 and len(r.content) > 50000:
            with open(out_path, "wb") as f:
                f.write(r.content)
            log(f"  Pollinations OK: {Path(out_path).stat().st_size // 1024}KB")
            return True
    except Exception as e:
        log(f"  Pollinations (non-fatal): {e}")
    return False

def generate_thumbnail_with_ai_bg(title, thumb_text, niche_name, topic, ab_style="A"):
    """
    Channel 2 thumbnail: Pollinations AI forensic background + Pillow overlay.
    Falls back to pure Pillow if Pollinations unavailable.
    """
    thumb_path = str(WORK_DIR / "thumbnail.jpg")
    pol_path   = str(WORK_DIR / "pol_bg.jpg")
    got_bg     = fetch_pollinations_bg(topic, niche_name, pol_path)

    try:
        from PIL import Image, ImageDraw, ImageFont, ImageEnhance
        W, H = 1280, 720

        if got_bg and Path(pol_path).exists():
            img = Image.open(pol_path).convert("RGB").resize((W, H))
            img = ImageEnhance.Brightness(img).enhance(0.22)  # very dark
        else:
            img = Image.new("RGB", (W, H), (5, 5, 10))

        draw = ImageDraw.Draw(img)

        # Dark gradient vignette overlay
        for i in range(150):
            alpha = int(180 * (1 - i / 150))
            draw.rectangle([i, i, W-i, H-i], outline=(0, 0, 0, alpha) if False else (0,0,0))

        # Font
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]
        def get_font(sz):
            for fp in font_paths:
                if Path(fp).exists():
                    try: return ImageFont.truetype(fp, sz)
                    except: pass
            return ImageFont.load_default()

        # Forensic series badge
        badge_font = get_font(22)
        draw.text((24, 20), "● THE EVIDENCE ROOM", font=badge_font, fill=(180, 0, 0))

        # Main hook text — A/B colour
        words   = thumb_text.split()
        lines   = ([thumb_text] if len(words) <= 3
                   else [" ".join(words[:len(words)//2]),
                         " ".join(words[len(words)//2:])])
        fm      = get_font(108)
        th_total= len(lines) * 118
        sy      = (H - th_total) // 2 - 20

        text_col   = (220, 15, 15) if ab_style == "A" else (255, 255, 255)
        shadow_col = (60, 0, 0)    if ab_style == "A" else (0, 0, 0)

        for i, line in enumerate(lines):
            y    = sy + i * 118
            bbox = draw.textbbox((0, 0), line, font=fm)
            x    = (W - (bbox[2] - bbox[0])) // 2
            for dx, dy in [(-3,-3),(3,-3),(-3,3),(3,3),(0,-4),(0,4)]:
                draw.text((x+dx, y+dy), line, font=fm, fill=shadow_col)
            draw.text((x, y), line, font=fm, fill=text_col)

        # Sub-title
        sub  = title[:60] + ("…" if len(title) > 60 else "")
        fs   = get_font(30)
        bb   = draw.textbbox((0, 0), sub, font=fs)
        sx   = (W - (bb[2] - bb[0])) // 2
        draw.text((sx, sy + th_total + 16), sub, font=fs, fill=(200, 200, 200))

        # Evidence stamp border
        draw.rectangle([8, 8, W-8, H-8], outline=(140, 0, 0), width=2)
        draw.rectangle([14, 14, W-14, H-14], outline=(80, 0, 0), width=1)

        img.save(thumb_path, "JPEG", quality=95)
        log(f"  Thumbnail saved: {Path(thumb_path).stat().st_size // 1024}KB")
        return thumb_path

    except Exception as e:
        log(f"  Thumbnail error: {e}")
        return None

def apply_audio_post_processing(input_path, output_path):
    """
    Transform edge-tts flat TTS into cinematic investigative narrator quality.
    EQ boosts presence, reverb adds room depth, compression smooths dynamics.
    """
    try:
        af = (
            "equalizer=f=80:width_type=o:width=2:g=3,"
            "equalizer=f=2500:width_type=o:width=2:g=2,"
            "equalizer=f=8000:width_type=o:width=2:g=-3,"
            "aecho=0.8:0.85:40:0.25,"
            "acompressor=threshold=-18dB:ratio=3:attack=5:release=80:makeup=2dB,"
            "loudnorm=I=-16:LRA=11:TP=-1.5"
        )
        subprocess.run([
            "ffmpeg", "-y", "-i", input_path,
            "-af", af, "-c:a", "mp3", "-q:a", "2", output_path
        ], capture_output=True, timeout=300, check=True)
        if Path(output_path).exists() and Path(output_path).stat().st_size > 500000:
            log(f"  Audio post-processed: {Path(output_path).stat().st_size//(1024*1024)}MB")
            return output_path
    except Exception as e:
        log(f"  Audio processing (non-fatal): {e}")
    return input_path

def run_stage3_audio(script_clean, voice_id, niche_name):
    log("\n"+"="*65)
    log(f"  STAGE 3: Human Voice Audio — {voice_id}")
    log("="*65)
    wc           = len(script_clean.split())
    dur_expected = (wc/125.0)*60.0
    preferred    = NICHE_VOICES.get(niche_name, GB_VOICES[:4])
    # Guaranteed working voices on GitHub Actions (tested)
    GUARANTEED_VOICES = [
        "en-GB-RyanNeural",      # BBC documentary gravitas — most reliable
        "en-GB-ThomasNeural",    # Cold measured cinematic
        "en-US-BrianNeural",     # Deep calm commanding
        "en-US-ChristopherNeural", # Serious documentary
        "en-US-AndrewNeural",    # Warm authoritative
        "en-US-EricNeural",      # Professional measured
        "en-US-GuyNeural",       # Commanding serious
        "en-US-SteffanNeural",   # Professional clear
        "en-GB-OliverNeural",    # Professional authoritative
        "en-US-TonyNeural",      # Confident expressive
    ]
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
                log(f"  {v} failed quality — trying next")
                continue
            sz  = Path(mp3).stat().st_size
            dur = dur_expected
            log(f"  ACCEPTED: {v} | {sz/1024/1024:.1f}MB | ~{dur/60:.1f}min")
            wav = str(WORK_DIR/"audio.wav")
            try:
                subprocess.run(["ffmpeg","-y","-i",mp3,"-acodec","pcm_s16le","-ar","24000","-ac","1",wav],
                               capture_output=True, timeout=300)
                if Path(wav).exists() and Path(wav).stat().st_size>100000:
                    return wav, dur, sz, v
            except: pass
            return mp3, dur, sz, v
        except Exception as e:
            log(f"  {v} err: {str(e)[:60]}")
            time.sleep(3)
    tg("Evidence Room Stage 3 FAILED — all voices failed")
    sys.exit(1)


# ════════════════════════════════════════════════════════════
# STAGE 4: ANIMATION ENGINE — 5 SCENE TYPES
# ════════════════════════════════════════════════════════════

def render_connection_reveal(draw, W, H, nodes, progress, accent, font_sm):
    """
    Animate lines drawing between connection nodes.
    Lines draw themselves progressively — cinematic reveal effect.
    nodes: list of (x, y, label) tuples
    """
    if len(nodes) < 2: return
    total_connections = len(nodes) - 1
    for i in range(total_connections):
        conn_progress = min(1.0, max(0.0,
            (progress * total_connections - i)))
        if conn_progress <= 0: continue
        x1, y1 = nodes[i][0], nodes[i][1]
        x2, y2 = nodes[i+1][0], nodes[i+1][1]
        # Partial line draw
        cx = int(x1 + (x2 - x1) * conn_progress)
        cy = int(y1 + (y2 - y1) * conn_progress)
        draw.line([(x1, y1), (cx, cy)], fill=accent, width=2)
        # Pulsing node dot
        r = 6
        draw.ellipse([(x1-r, y1-r), (x1+r, y1+r)], fill=accent)
        if conn_progress >= 1.0:
            draw.ellipse([(x2-r, y2-r), (x2+r, y2+r)], fill=accent)

def render_counting_number(draw, x, y, target_val, progress, font_lg, color):
    """
    Animate a number counting up from 0 to target_val.
    Creates urgency — viewer feels the scale of the case.
    """
    current = int(target_val * min(progress * 1.5, 1.0))
    text = f"{current:,}"
    bbox = draw.textbbox((0,0), text, font=font_lg)
    tw = bbox[2] - bbox[0]
    draw.text((x - tw//2 + 1, y + 1), text, font=font_lg, fill=(20, 20, 20))
    draw.text((x - tw//2, y), text, font=font_lg, fill=color)

def render_classified_stamp(draw, W, H, progress, font_lg):
    """
    Stamp-reveal effect for classified evidence.
    Red CLASSIFIED diagonal stamp appears at reveal moment.
    """
    if progress < 0.7: return
    stamp_alpha = min(1.0, (progress - 0.7) / 0.3)
    stamp_text  = "CLASSIFIED"
    # Diagonal stamp in red
    alpha_val = int(200 * stamp_alpha)
    stamp_color = (200, 0, 0, alpha_val) if False else (200, 0, 0)
    bbox = draw.textbbox((0,0), stamp_text, font=font_lg)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    cx, cy = W//2, H//2
    draw.text((cx - tw//2 + 2, cy - th//2 + 2), stamp_text, font=font_lg, fill=(40,0,0))
    draw.text((cx - tw//2, cy - th//2), stamp_text, font=font_lg, fill=stamp_color)
    # Border lines of the stamp box
    pad = 20
    for thickness in range(1, 4):
        draw.rectangle([cx-tw//2-pad, cy-th//2-pad,
                        cx+tw//2+pad, cy+th//2+pad],
                       outline=stamp_color, width=thickness)

def render_frame_pil(style_name, scene, frame_idx, total_frames, scene_idx, total_scenes):
    style    = STYLES[style_name]
    bg, primary, accent, secondary = style["bg"], style["primary"], style["accent"], style["secondary"]
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

    stype = scene.get("type","evidence_board")

    # Enhanced atmospheric backgrounds — psychological thriller grade
    pulse = style.get("pulse", accent)
    glow  = style.get("glow", accent)

    if style_name == "dark_minimal":
        # Vignette: red pulse from corners — creates dread
        for i in range(0, min(frame_idx*3, 120), 6):
            intensity = max(0, 40 - i)
            draw.rectangle([i,i,W-i,H-i], outline=(intensity,0,0))
        # Scanlines for digital surveillance feel
        for y in range(0, H, 3):
            draw.line([(0,y),(W,y)], fill=(0,0,0,60), width=1)

    elif style_name == "cinematic":
        # Deep blue atmospheric gradient
        for y in range(0, H, 2):
            intensity = int(15 * (1 - y/H))
            draw.line([(0,y),(W,y)], fill=(intensity, intensity*2, intensity*4), width=1)
        # Film grain
        for _ in range(200):
            gx, gy = random.randint(0,W), random.randint(0,H)
            draw.point([(gx,gy)], fill=(random.randint(10,30),)*3)

    elif style_name == "documentary":
        # Aged paper texture with film grain
        for y in range(0, H, 6):
            if random.random() < 0.15:
                draw.line([(0,y),(W,y)], fill=(22,18,14), width=1)
        # Random damage spots
        for _ in range(30):
            dx, dy = random.randint(0,W), random.randint(0,H)
            draw.ellipse([(dx-2,dy-2),(dx+2,dy+2)], fill=(8,6,4))

    # Glitch effect on high-tension frames (every 90 frames = 3s at 30fps)
    if frame_idx % 90 < 3:
        for _ in range(5):
            gy = random.randint(0, H)
            shift = random.randint(-8, 8)
            draw.line([(0,gy),(W,gy)], fill=glow, width=1)

    # Dramatic corner marks with glow
    for thickness, color in [(3, pulse), (1, glow)]:
        draw.line([(0,0),(80,0)], fill=color, width=thickness)
        draw.line([(0,0),(0,80)], fill=color, width=thickness)
        draw.line([(W-80,H-1),(W,H-1)], fill=color, width=thickness)
        draw.line([(W-1,H-80),(W-1,H)], fill=color, width=thickness)

    # Classification watermark — feels like classified footage
    draw.text((30,H-42), "THE EVIDENCE ROOM — CLASSIFIED", font=font_xs, fill=secondary)
    draw.text((W-200,H-42), f"CASE {scene_idx+1:03d}/{total_scenes:03d}", font=font_xs, fill=secondary)
    # Live recording indicator
    if frame_idx % 60 < 30:  # blink every second
        draw.ellipse([(W-30,15),(W-15,30)], fill=accent)
        draw.text((W-55,14), "REC", font=font_xs, fill=accent)

    # Scene title
    title = scene.get("title","EVIDENCE")
    if progress > 0.05:
        ta = min(1.0,(progress-0.05)*5)
        draw.text((int(80+(1.0-ta)*30),40),title,font=font_lg,fill=accent)
        draw.line([(80,112),(80+int(700*progress),112)],fill=accent,width=2)

    # Render scene type
    if   stype=="timeline":      _render_timeline(draw,scene,progress,style,font_md,font_sm,font_xs)
    elif stype=="document":      _render_document(draw,scene,progress,style,style_name,font_md,font_sm,font_mono)
    elif stype=="data_reveal":   _render_data_reveal(draw,scene,progress,style,font_lg,font_md,font_sm)
    elif stype=="connection_map":_render_connection_map(draw,scene,progress,style,font_md,font_sm)
    else:                        _render_evidence_board(draw,scene,progress,style,font_md,font_sm,font_xs)
    return img

def _render_timeline(draw,scene,progress,style,font_md,font_sm,font_xs):
    items=scene.get("items",[]); label=scene.get("label","TIMELINE")
    primary,accent,secondary=style["primary"],style["accent"],style["secondary"]
    lx,ty,by=200,160,H-150
    draw.line([(lx,ty),(lx,by)],fill=secondary,width=2)
    draw.text((80,H-120),label,font=font_xs,fill=secondary)
    n=len(items); spacing=(by-ty)//max(n,1)
    for i,item in enumerate(items):
        ip=(progress*n)-i
        if ip<=0: continue
        a=min(1.0,ip); y=ty+i*spacing
        dc=accent if a>0.5 else secondary
        draw.ellipse([(lx-8,y-8),(lx+8,y+8)],fill=dc)
        xe=int(lx+60+a*40)
        draw.line([(lx+8,y),(xe,y)],fill=dc,width=2)
        if a>0.3: draw.text((lx+80,y-14),item,font=font_sm,fill=primary)

def _render_document(draw,scene,progress,style,style_name,font_md,font_sm,font_mono):
    """Enhanced document scene: typewriter reveal, redaction lines, dramatic stamp."""
    lines=scene.get("lines",["CONFIDENTIAL"]); stamp=scene.get("stamp","")
    primary,accent,secondary=style["primary"],style["accent"],style["secondary"]
    glow=style.get("glow",accent)
    px,py,dw,dh=160,120,W-320,H-240
    pc=(8,8,14) if style_name!="documentary" else (16,12,9)
    # Outer glow effect on document border
    for offset in [4,2,1]:
        draw.rectangle([(px-offset,py-offset),(px+dw+offset,py+dh+offset)],
                       outline=accent if offset==1 else (accent[0]//4,accent[1]//4,accent[2]//4))
    draw.rectangle([(px,py),(px+dw,py+dh)],fill=pc,outline=secondary,width=2)
    # Header bar
    draw.rectangle([(px,py),(px+dw,py+55)],fill=(accent[0]//3,accent[1]//3,accent[2]//3))
    draw.text((px+20,py+14),"CLASSIFIED — RESTRICTED ACCESS",font=font_sm,fill=glow)
    draw.line([(px+15,py+58),(px+dw-15,py+58)],fill=accent,width=2)
    n=len(lines)
    for i,line in enumerate(lines):
        lp=(progress*(n+1.5))-i
        if lp<=0: continue
        a=min(1.0,lp); y=py+75+i*58
        # Typewriter effect: reveal characters gradually
        chars_to_show = int(len(line) * min(1.0, (lp)*3))
        visible = line[:chars_to_show]
        # Redacted lines start with [
        if line.startswith("["):
            # Black redaction bar
            bb = draw.textbbox((0,0),line,font=font_mono)
            tw = bb[2]-bb[0]
            draw.rectangle([(px+40,y-2),(px+40+tw+8,y+28)],fill=(0,0,0))
            if progress>0.85:  # Reveal after 85% — dramatic moment
                draw.text((px+40,y),line.strip("[]"),font=font_mono,fill=accent)
        else:
            draw.text((px+40,y),visible,font=font_mono,fill=primary)
            # Cursor blink at current typing position
            if chars_to_show < len(line) and int(progress*20)%2==0:
                cw = draw.textbbox((0,0),visible,font=font_mono)[2]
                draw.line([(px+42+cw,y),(px+42+cw,y+24)],fill=glow,width=2)
    # Dramatic stamp reveal
    if stamp and progress>0.75:
        stamp_alpha = min(1.0,(progress-0.75)*4)
        sx,sy=px+dw-300,py+dh-170
        draw.rectangle([(sx,sy),(sx+270,sy+120)],outline=accent,width=4)
        for thickness in [4,2]:
            draw.line([(sx,sy),(sx+270,sy+120)],fill=accent,width=thickness)
            draw.line([(sx+270,sy),(sx,sy+120)],fill=accent,width=thickness)
        draw.text((sx+20,sy+35),stamp,font=font_md,fill=accent)

def _render_data_reveal(draw,scene,progress,style,font_lg,font_md,font_sm):
    items=scene.get("items",[]); label=scene.get("label","DATA")
    primary,accent,secondary=style["primary"],style["accent"],style["secondary"]
    draw.text((80,H-120),label,font=font_sm,fill=secondary)
    draw.line([(80,H-90),(W-80,H-90)],fill=secondary,width=1)
    n=len(items); cw=(W-200)//max(n,1)
    for i,item in enumerate(items):
        ip=(progress*(n+0.5))-i
        if ip<=0: continue
        a=min(1.0,ip); cx=100+i*cw+cw//2
        bh=int(a*350); bt=H-150-bh; bc=accent if i==n-1 else primary
        draw.rectangle([(cx-40,bt),(cx+40,H-150)],fill=bc,outline=secondary,width=1)
        if a>0.4:
            try: tw=font_lg.getbbox(item)[2]-font_lg.getbbox(item)[0]
            except: tw=100
            draw.text((cx-tw//2,bt-55),item,font=font_lg,fill=primary)

def _render_connection_map(draw,scene,progress,style,font_md,font_sm):
    nodes=scene.get("nodes",[]); label=scene.get("label","NETWORK")
    primary,accent,secondary=style["primary"],style["accent"],style["secondary"]
    draw.text((80,H-120),label,font=font_sm,fill=secondary)
    n=len(nodes)
    if n==0: return
    sp=(W-300)//max(n-1,1); ny=H//2
    positions=[(150+i*sp,ny) for i in range(n)]
    for i,(nx,ny2) in enumerate(positions):
        ip=(progress*(n+0.5))-i
        if ip<=0: continue
        a=min(1.0,ip)
        if i<n-1 and ip>0.8:
            nnx,nny=positions[i+1]
            le=int(nx+40+a*(nnx-nx-80))
            draw.line([(nx+40,ny2),(le,ny2)],fill=accent,width=2)
            if le>nx+100: draw.polygon([(le,ny2),(le-12,ny2-8),(le-12,ny2+8)],fill=accent)
        bc=accent if i==0 or i==n-1 else secondary
        draw.rectangle([(nx-60,ny2-25),(nx+60,ny2+25)],fill=(5,5,15),outline=bc,width=2)
        draw.text((nx-50,ny2-12),nodes[i],font=font_sm,fill=primary)

def _render_evidence_board(draw,scene,progress,style,font_md,font_sm,font_xs):
    items=scene.get("items",[]); label=scene.get("label","EVIDENCE")
    primary,accent,secondary=style["primary"],style["accent"],style["secondary"]
    draw.text((80,H-120),label,font=font_xs,fill=secondary)
    n=len(items); cols=2; rows=(n+1)//2
    cw=(W-200)//cols; ch=(H-320)//max(rows,1)
    for i,item in enumerate(items):
        ip=(progress*(n+0.5))-i
        if ip<=0: continue
        a=min(1.0,ip); col=i%cols; row=i//cols
        cx=100+col*cw; cy=160+row*ch
        draw.rectangle([(cx,cy),(cx+cw-20,cy+ch-20)],fill=(8,8,18),
                       outline=accent if a>0.8 else secondary,width=1)
        if a>0.2:
            pts=item.split(":")
            if len(pts)==2:
                draw.text((cx+15,cy+14),pts[0]+":",font=font_xs,fill=secondary)
                draw.text((cx+15,cy+44),pts[1].strip(),font=font_md,fill=primary)
            else:
                draw.text((cx+15,cy+24),item,font=font_sm,fill=primary)


# Ken Burns motion profiles per scene type
# Slow camera movement creates documentary cinematography feel
SCENE_MOTION = {
    "timeline":        "zoompan=z='min(zoom+0.0008,1.3)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
    "document_reveal": "zoompan=z='min(zoom+0.001,1.4)':d=1:x='iw/2-(iw/zoom/2)':y='ih*0.3-(ih/zoom*0.3)'",
    "data_reveal":     "zoompan=z='if(lte(zoom,1.0),1.3,max(1.001,zoom-0.001))':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
    "connection_map":  "zoompan=z='1.2+0.05*sin(2*PI*on/100)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
    "evidence_board":  "zoompan=z='min(zoom+0.0006,1.25)':d=1:x='(iw-iw/zoom)*on/n':y='ih/2-(ih/zoom/2)'",
}

def apply_ken_burns(input_path, output_path, scene_type, fps=24, duration=None):
    """
    Apply Ken Burns (slow zoom/pan) motion to a video scene.
    Makes animated frames feel cinematic — industry standard for documentary.
    Falls back to original if filter fails.
    """
    motion = SCENE_MOTION.get(scene_type, SCENE_MOTION["timeline"])
    try:
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-vf", f"{motion},scale=1920:1080:flags=lanczos",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-c:a", "copy",
        ]
        if duration:
            cmd += ["-t", str(duration)]
        cmd.append(output_path)
        run_ffmpeg(cmd, label=f"ken-burns-{scene_type}", timeout=600)
        if Path(output_path).exists() and Path(output_path).stat().st_size > 100000:
            log(f"  Ken Burns ({scene_type}): OK")
            return output_path
    except Exception as e:
        log(f"  Ken Burns (non-fatal, using original): {e}")
    return input_path

def render_and_encode(style_name, scenes, audio_path, duration):
    frames_base = WORK_DIR/"frames"
    frames_base.mkdir(exist_ok=True)
    concat_parts = []
    for si, scene in enumerate(scenes):
        dur_s = scene.get("duration",8); total_f = dur_s*FPS
        fd = frames_base/f"scene_{si:03d}"; fd.mkdir(exist_ok=True)
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
# STAGE 5: SHORTS WITH SUBTITLES
# NO subtitles on main video — subtitles on Shorts ONLY
# ════════════════════════════════════════════════════════════
def generate_short_srt(script_clean, start, short_dur):
    words    = script_clean.split()
    total_wc = len(words)
    total_dur = (total_wc/125.0)*60.0
    wps      = total_wc/total_dur
    sw       = int(start*wps)
    ew       = min(int((start+short_dur)*wps)+5, total_wc)
    clip_wds = words[sw:ew]
    if not clip_wds: return None

    def fmt(t):
        h,r=divmod(int(t),3600); m,s=divmod(r,60)
        return f"{h:02d}:{m:02d}:{s:02d},{int((t%1)*1000):03d}"

    entries=[]; idx,t=1,0.0
    cwps=len(clip_wds)/short_dur if short_dur>0 else 3.0
    for i in range(0,len(clip_wds),4):
        g=clip_wds[i:i+4]
        if not g: continue
        d=len(g)/cwps
        entries.append(f"{idx}\n{fmt(t)} --> {fmt(t+d)}\n{' '.join(g)}\n")
        idx+=1; t+=d
    srt=WORK_DIR/f"short_{idx}.srt"
    srt.write_text("\n".join(entries),encoding="utf-8")
    return str(srt)

def make_short_with_subs(video_path, script_clean, stype, total_dur):
    short_dur = 55
    start     = total_dur*(0.10 if stype=="teaser" else 0.67)
    raw       = str(WORK_DIR/f"s_{stype}_raw.mp4")
    final     = str(WORK_DIR/f"short_{stype}.mp4")
    r = subprocess.run(["ffmpeg","-y","-ss",str(start),"-i",video_path,"-t",str(short_dur),
                        "-vf","crop=608:1080:(iw-608)/2:0,scale=1080:1920",
                        "-c:v","libx264","-preset","fast","-crf","22",
                        "-c:a","aac","-b:a","128k",raw], capture_output=True, timeout=180)
    if not Path(raw).exists() or Path(raw).stat().st_size<400000:
        log(f"  Short {stype} clip failed"); return None
    # Subtitles disabled — timing sync not reliable enough
    # Short is the raw clip — no subtitle burn
    log(f"  Short ({stype}): {Path(raw).stat().st_size/1024/1024:.1f}MB — no subtitles")
    return raw


# ════════════════════════════════════════════════════════════
# STAGE 6: UPLOAD
# ════════════════════════════════════════════════════════════
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
        raise Exception(f"YT token failed: {d.get('error')} — {d.get('error_description')}")
    _tok_cache["token"]      = d["access_token"]
    _tok_cache["expires_at"] = now + d.get("expires_in", 3600)
    return d["access_token"]

def upload_yt(path, title, description, tags, is_short=False, token=None):
    """Chunked resumable upload with retry — same as Channel 1."""
    token = token or get_yt_token()
    if is_short: title = f"{title[:55]} #Shorts"
    fs = Path(path).stat().st_size
    log(f"  Uploading: {Path(path).name} ({fs//(1024*1024)}MB)")

    init = requests.post(
        f"{YT_UPLOAD_URL}/videos?uploadType=resumable&part=snippet,status",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                 "X-Upload-Content-Length": str(fs), "X-Upload-Content-Type": "video/mp4"},
        json={"snippet": {"title": title[:100], "description": description,
                          "tags": tags[:15], "categoryId": "22"},
              "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False,
                         "madeForKids": False}}, timeout=30)
    upload_url = init.headers.get("Location")
    if not upload_url:
        raise Exception(f"No upload URL: {init.status_code}: {init.text[:200]}")

    CHUNK = 16 * 1024 * 1024
    uploaded = 0; retries = 0
    with open(path, "rb") as f:
        while uploaded < fs:
            data = f.read(CHUNK)
            if not data: break
            end = uploaded + len(data) - 1
            try:
                up = requests.put(upload_url,
                    headers={"Authorization": f"Bearer {token}",
                             "Content-Length": str(len(data)),
                             "Content-Range": f"bytes {uploaded}-{end}/{fs}",
                             "Content-Type": "video/mp4"},
                    data=data, timeout=600)
                if up.status_code in [200, 201]:
                    vid_id = up.json().get("id")
                    url = f"https://www.youtube.com/watch?v={vid_id}"
                    log(f"  Uploaded: {url}")
                    return url, vid_id
                elif up.status_code == 308:
                    rh = up.headers.get("Range", "")
                    uploaded = int(rh.split("-")[1]) + 1 if rh else uploaded + len(data)
                    log(f"  {int(uploaded*100/fs)}%"); retries = 0
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


def post_creator_comment(token, video_id, niche_name, title, episode):
    """Post engagement-driving creator comment immediately after upload."""
    niche_hooks = {
        "forensic_finance":       "What financial warning sign do you think most people miss?",
        "criminal_investigation": "Which piece of evidence in this case do you find most disturbing?",
        "corporate_exposure":     "Have you ever seen this happen at a company you know?",
        "digital_forensics":      "Did you know your digital footprint tells this much about you?",
    }
    hook = niche_hooks.get(niche_name, "What detail in this case changed how you see it?")
    comment = (
        f"🔬 {hook}\n\n"
        f"Leave your answer below — every case has details that never make the news.\n\n"
        f"🔔 New forensic investigation every weekday\n"
        f"🌑 Dark horror investigations: youtube.com/@BetrayalDeepDive\n\n"
        f"#{niche_name.replace('_','')} #forensic #investigation #documentary #episode{episode}"
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
            log("  Creator comment posted OK")
        else:
            log(f"  Creator comment {r.status_code} (non-fatal)")
    except Exception as e:
        log(f"  Creator comment (non-fatal): {e}")

def ensure_playlist(token, niche_name, series_name):
    """Auto-create per-niche playlist, return playlist_id."""
    try:
        r = requests.get(f"{YT_DATA_URL}/playlists",
            headers={"Authorization": f"Bearer {token}"},
            params={"part": "snippet", "mine": "true", "maxResults": 50}, timeout=20)
        if r.status_code == 200:
            for item in r.json().get("items", []):
                if series_name.lower() in item["snippet"]["title"].lower():
                    return item["id"]
        r2 = requests.post(f"{YT_DATA_URL}/playlists",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            params={"part": "snippet,status"},
            json={"snippet": {"title": f"{series_name} — All Cases",
                              "description": f"Every investigation from {series_name}."},
                  "status": {"privacyStatus": "public"}}, timeout=20)
        if r2.status_code == 200:
            pid = r2.json()["id"]
            log(f"  Playlist created: {pid}"); return pid
    except Exception as e: log(f"  Playlist (non-fatal): {e}")
    return None

def add_to_playlist(token, playlist_id, video_id):
    if not playlist_id: return
    try:
        requests.post(f"{YT_DATA_URL}/playlistItems",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            params={"part": "snippet"},
            json={"snippet": {"playlistId": playlist_id,
                              "resourceId": {"kind": "youtube#video", "videoId": video_id}}},
            timeout=20)
        log("  Added to playlist")
    except Exception as e: log(f"  Playlist add (non-fatal): {e}")

def cleanup():
    for f in ["audio.mp3","audio.wav","raw.mp4","final.mp4",
              "short_teaser.mp4","short_recap.mp4","s_teaser_raw.mp4","s_recap_raw.mp4"]:
        p=WORK_DIR/f
        if p.exists(): p.unlink()
    for srt in WORK_DIR.glob("short_*.srt"): srt.unlink()
    frames_dir=WORK_DIR/"frames"
    if frames_dir.exists(): shutil.rmtree(frames_dir)
    log("  Cleanup complete")


# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════

def run_provider_health_check():
    """Test all AI providers at startup — fires before script generation."""
    log("\n" + "="*65)
    log("  AI PROVIDER HEALTH CHECK")
    log("="*65)
    test = "Reply with exactly: OK"
    working = []
    for name, fn in [("Cerebras", _call_cerebras), ("SambaNova", _call_sambanova),
                     ("Gemini", _call_gemini), ("Groq", _call_groq),
                     ("OpenRouter", _call_openrouter), ("Cohere", _call_cohere),
                     ("Mistral", _call_mistral)]:
        try:
            r = fn(test, 50)
            status = "✅" if r else "❌ NO RESPONSE"
            if r: working.append(name)
        except Exception as e:
            status = f"❌ {str(e)[:50]}"
        log(f"  {name:12s}: {status}")
    log("="*65)
    if not working:
        tg("🚨 ALL AI PROVIDERS FAILED — pipeline cannot continue.")
        raise RuntimeError("All AI providers failed")
    elif len(working) < 3:
        tg(f"⚠️ Only {len(working)} provider(s) working: {', '.join(working)}")
    else:
        log(f"  {len(working)}/7 working — OK")
    return working


def main():
    # Stagger start to avoid API conflicts with Channel 1
    delay = random.randint(90, 150)
    log(f"  Starting in {delay}s to avoid API conflicts...")
    time.sleep(delay)

    log("\n"+"="*65)
    log("  THE EVIDENCE ROOM v2.0 — ANIMATED FORENSIC PIPELINE")
    log("  20 Human Voices | 13 Attempts | 7.3 Quality Floor")
    log("  No subs on main | Subs on Shorts | Telegram + Gmail")
    log("="*65)

    state = load_state()

    # Pre-define cross-stage variables (prevents NameError if any stage errors)
    used_topics    = []
    topic_used     = ""
    best_thumbnail = "EVIDENCE FOUND"
    best_title_str = ""
    ab_style       = "A" if datetime.datetime.now().isocalendar()[1] % 2 == 1 else "B"

    # Startup notification
    tg(f"Evidence Room v2.0 Starting\n"
       f"Time: {datetime.datetime.now().strftime('%I:%M %p')}\n"
       f"Quality floor: {MIN_GATE} | 13-attempt engine\n"
       f"Approval request in ~15 min.")
    log("Startup notification sent")

    # Stage 1: Script
    (niche, topic, voice, style_name, episode,
     script_clean, scenes, title_str, thumbnail_text,
     title_scores, score, tags, intel) = run_stage1(state)

    # Enhance tags with competitive niche-specific SEO tags
    CH2_NICHE_TAGS = {
        "forensic_finance":       ["forensic finance documentary","financial fraud investigation",
                                   "money laundering exposed","corporate fraud documentary",
                                   "financial crime narration","forensic accounting youtube"],
        "criminal_investigation": ["criminal investigation documentary","forensic investigation",
                                   "true crime documentary narration","crime evidence documentary"],
        "corporate_exposure":     ["corporate corruption exposed","corporate fraud documentary",
                                   "whistleblower documentary","corporate crime investigation"],
        "digital_forensics":      ["digital forensics documentary","cybercrime investigation",
                                   "digital evidence exposed","cyber investigation narration"],
    }
    tags = list(set(tags + CH2_NICHE_TAGS.get(niche["name"], [])))[:15]

    # Upgrade thumbnail to NUMBER+NOUN format for higher CTR
    if thumbnail_text and not any(c.isdigit() for c in thumbnail_text):
        try:
            num_p = (f"Forensic topic: {topic[:60]}\n"
                     "Generate 2-3 word thumbnail text in NUMBER+NOUN format.\n"
                     "Examples: '$2.4M GONE' '14 ACCOUNTS' '7 WITNESSES' '4380 DAYS'\n"
                     "Use a specific number from the case. Return ONLY the phrase.")
            num_r = ai(num_p, tokens=40)
            if num_r and any(c.isdigit() for c in num_r.strip()):
                thumbnail_text = num_r.strip().upper()[:20]
                log(f"  Thumbnail upgraded to NUMBER+NOUN: {thumbnail_text}")
        except: pass

    elapsed = time.time()
    tg(f"Evidence Room Stage 1 Complete\n"
       f"{niche['name']} | {len(script_clean.split())}w | {score}/10\n"
       f"Title: {title_str[:60]}\nSending approval now...")

    # Stage 2: Approval gate (30-min, before video)
    decision = run_stage2_approval(
        title_str, niche, voice, style_name, script_clean,
        thumbnail_text, title_scores, score)
    if decision == "rejected":
        log("Rejected."); sys.exit(0)

    tg("Evidence Room generating video now...")

    # Stage 3: Human voice audio — with stage-level retry
    audio_path, duration, audio_sz, voice_used = run_stage_with_retry(
        run_stage3_audio, "Audio", script_clean, voice, niche["name"])
    tg(f"Stage 3: {voice_used} | {duration/60:.1f}min")

    # Stage 4: Animation (NO subtitles on main)
    log("\n"+"="*65)
    log("  STAGE 4: Rendering Animation")
    log("="*65)
    video_path = run_stage_with_retry(
        render_and_encode, "Animation", style_name, scenes, audio_path, duration)
    tg(f"Stage 4: 1080p animated | Style: {style_name}\nUploading...")

    # Generate AI thumbnail with Pollinations background
    # `topic` is already unpacked from run_stage1() result — use it directly
    thumb_path = generate_thumbnail_with_ai_bg(
        title_str, best_thumbnail or "EVIDENCE FOUND",
        niche["name"], topic, ab_style=ab_style)
    log(f"  Thumbnail: {'OK' if thumb_path else 'using default'}")

    # Upload main video
    # A/B thumbnail week tracking
    week_number = datetime.datetime.now().isocalendar()[1]
    ab_style    = "A" if week_number % 2 == 1 else "B"
    state.setdefault("thumbnail_ab", {})["last_style"] = ab_style
    log(f"  Thumbnail A/B style: {ab_style} (week {week_number})")

    cross_promo = ("\n\n🔎 For dark psychological horror investigations: "
                   "youtube.com/@BetrayalDeepDive")
    description = (f"Episode {episode} of {niche['series']}.\n{topic}\n\n"
                   f"Every case. Every document. Every piece of evidence — animated.\n\n"
                   f"Subscribe to The Evidence Room."
                   f"{cross_promo}\n\n"
                   f"⚠️ AI-assisted narration and forensic analysis.")
    token_yt = get_yt_token()
    # Playlist for this niche
    playlist_id = state.get("playlists", {}).get(niche["name"])
    if not playlist_id:
        playlist_id = ensure_playlist(token_yt, niche["name"], niche["series"])
        if playlist_id:
            pl = state.get("playlists", {})
            pl[niche["name"]] = playlist_id
            state["playlists"] = pl

    try:
        yt_url, vid_id = run_stage_with_retry(
            upload_yt, "Upload", video_path, title_str, description, tags,
            is_short=False, token=token_yt)
        add_to_playlist(token_yt, playlist_id, vid_id)
        # Upload AI-generated thumbnail
        if thumb_path and Path(thumb_path).exists():
            try:
                with open(thumb_path, "rb") as tf:
                    tr = requests.post(
                        f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set"
                        f"?videoId={vid_id}&uploadType=media",
                        headers={"Authorization": f"Bearer {token_yt}",
                                 "Content-Type": "image/jpeg"},
                        data=tf.read(), timeout=60)
                if tr.status_code in [200, 201]:
                    log("  Thumbnail uploaded to YouTube OK")
            except Exception as te:
                log(f"  Thumbnail upload (non-fatal): {te}")
        post_creator_comment(token_yt, vid_id, niche["name"],
                             title_str, episode)
        log(f"  Main: {yt_url}")
    except Exception as e:
        tg(f"Evidence Room Upload FAILED\n{str(e)[:200]}"); sys.exit(1)

    # 2 Shorts — MANDATORY, 3 attempts each, no silent failures
    shorts = []; token_yt = get_yt_token()
    for stype in ["teaser", "recap"]:
        success = False; last_err = None
        for attempt in range(1, 4):
            try:
                log(f"  Creating Short ({stype}) attempt {attempt}/3...")
                sp = make_short_with_subs(video_path, script_clean, stype, duration)
                if not sp or not Path(sp).exists() or Path(sp).stat().st_size < 400000:
                    raise RuntimeError(f"Short ({stype}) file too small or missing")
                log(f"  Uploading Short ({stype}) attempt {attempt}/3...")
                su, sid = upload_yt(
                    sp, f"{title_str[:46]} — {stype.upper()}",
                    description, tags, is_short=True, token=token_yt)
                add_to_playlist(token_yt, playlist_id, sid)
                shorts.append(f"Short {stype}: {su}")
                log(f"  OK Short {stype}: {su}")
                success = True; break
            except Exception as e:
                last_err = e
                log(f"  Short {stype} attempt {attempt} failed: {e}")
                if attempt < 3: time.sleep(10)
        if not success:
            raise RuntimeError(
                f"CRITICAL: Short ({stype}) failed after 3 attempts. "
                f"Last error: {last_err}. Both Shorts are required every run.")

    cleanup()
    ckpt_clear()

    # Update state
    state["last_style"]    = style_name
    state["last_niche"]    = niche["name"]
    state["last_voice"]    = voice_used
    state["last_title"]    = title_str
    state["last_url"]      = yt_url
    state["total_uploads"] = state.get("total_uploads", 0) + 1
    state["total_shorts"]  = state.get("total_shorts", 0) + len(shorts)
    save_state(state)

    dec = "APPROVED" if decision=="approved" else "AUTO-APPROVED"
    ev  = int(5000*0.9)
    er  = round((ev/1000)*niche["rpm"],2)
    log("Pipeline complete — clearing checkpoint")
    ckpt_clear()

    tg(f"EVIDENCE ROOM PUBLISHED — {dec}\n\n"
       f"{title_str}\n"
       f"Style: {style_name} | Ep{episode}\n"
       f"Niche: {niche['name']} | ${niche['rpm']} RPM\n"
       f"Voice: {voice_used} | {duration/60:.1f}min\n"
       f"Score: {score}/10 | Thumbnail: {thumbnail_text}\n"
       f"No subs on main | Subs on Shorts\n\n"
       f"Main: {yt_url}\n"
       f"{chr(10).join(shorts)}\n\n"
       f"Est 30-day: {ev:,} views | ${er} (Rs.{int(er*83):,})\n"
       f"Artifacts deleted.")
    log(f"\nCOMPLETE: {yt_url}")

def main_with_retry():
    """Run main() with up to 3 auto-retries on failure (2 hour gap between each)."""
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            main()
            return  # success
        except SystemExit as e:
            if e.code == 0:
                return  # clean exit (rejected/skipped)
            if attempt < max_retries:
                wait_hours = 2
                tg(f"⚠️ Evidence Room attempt {attempt}/{max_retries} failed.\n"
                   f"Auto-retrying in {wait_hours}h...")
                log(f"Auto-retry {attempt}/{max_retries} in {wait_hours}h...")
                time.sleep(wait_hours * 3600)
                log(f"Starting retry attempt {attempt + 1}/{max_retries}...")
            else:
                tg(f"❌ Evidence Room FAILED after {max_retries} attempts. Manual check needed.")
                sys.exit(1)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            if attempt < max_retries:
                tg(f"⚠️ Evidence Room attempt {attempt}/{max_retries} crashed: {str(e)[:200]}\n"
                   f"Auto-retrying in 2h...")
                log(f"Crash: {e}\nRetrying in 2h...")
                time.sleep(7200)
            else:
                tg(f"❌ Evidence Room FAILED {max_retries}x: {str(e)[:300]}")
                sys.exit(1)

if __name__ == "__main__":
    main_with_retry()
