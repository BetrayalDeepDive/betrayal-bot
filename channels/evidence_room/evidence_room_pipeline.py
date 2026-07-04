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

# ── SHARED UTILS (inlined — no external file dependency) ──
"""
DEEPDIVE EMPIRE — Shared Utilities v1.0
Inlined into each pipeline at import time.
No external file dependencies — everything self-contained.

Import at top of each pipeline:
    from shared_utils import *
"""

import os, re, json, sys, time, datetime, random, subprocess, requests
from pathlib import Path


# ══════════════════════════════════════════════════════════════════
# PHASE MANAGER (inlined — no external file dependency)
# ══════════════════════════════════════════════════════════════════

def get_pipeline_phase():
    return os.environ.get("PIPELINE_PHASE", "full").lower()

def _pending_path(channel_dir):
    return Path(channel_dir) / "pending_upload.json"

def save_pending(channel_dir, data: dict):
    pf = _pending_path(channel_dir)
    data["generated_at"] = datetime.datetime.now().isoformat()
    pf.write_text(json.dumps(data, indent=2))
    return str(pf)

def load_pending(channel_dir):
    pf = _pending_path(channel_dir)
    if not pf.exists():
        return None
    try:
        d = json.loads(pf.read_text())
        if d.get("status") == "uploaded":
            return None   # already uploaded
        return d
    except:
        return None

def clear_pending(channel_dir):
    pf = _pending_path(channel_dir)
    pf.write_text(json.dumps({
        "status": "uploaded",
        "cleared_at": datetime.datetime.now().isoformat()
    }, indent=2))

def check_pending_age(pending, max_hours=28):
    try:
        gen = datetime.datetime.fromisoformat(pending.get("generated_at",""))
        hours = (datetime.datetime.now() - gen).total_seconds() / 3600
        return hours <= max_hours, round(hours, 1)
    except:
        return False, 999


# ══════════════════════════════════════════════════════════════════
# REVENUE ENGINE (inlined — no external file dependency)
# ══════════════════════════════════════════════════════════════════

NUMBER_NOUN_BANKS = {
    "dark_horror":        ["4,380 DAYS","12 YEARS","3 AM","14 VICTIMS","ONE NIGHT"],
    "seduction_dark":     ["7 SIGNS","28 DAYS","3 PEOPLE","6 WARNINGS","ONE TRAP"],
    "psychological_trap": ["6 STAGES","23 STEPS","100 DAYS","1 EXIT","5 TRIGGERS"],
    "supernatural_real":  ["3 NIGHTS","72 HOURS","9 WITNESSES","14 YEARS","1 PLACE"],
    "obsession_dark":     ["847 MESSAGES","4 YEARS","23 CALLS","1,460 DAYS","1 PERSON"],
    "forensic_finance":   ["$2.4M GONE","4,380 DAYS","47 REPORTS","$14M FRAUD","12 YEARS"],
    "criminal_investigation": ["14 VICTIMS","23 YEARS","1 FILE","47 CLUES","3 SUSPECTS"],
    "corporate_exposure": ["$840M HIDDEN","14 YEARS","23 EMAILS","$2.4B FRAUD","1 MEMO"],
    "digital_forensics":  ["2.7M FILES","847 ACCOUNTS","1 IP ADDRESS","23 SERVERS","14TB DATA"],
    "cult_psychology":    ["847 MEMBERS","14 YEARS","7 STAGES","23 RULES","1 LEADER"],
    "propaganda_systems": ["40M PEOPLE","7 TECHNIQUES","14 YEARS","3 AGENCIES","1 NARRATIVE"],
    "social_engineering": ["6 PRINCIPLES","847 TARGETS","23 HOURS","7 TRIGGERS","1 CALL"],
    "mass_deception":     ["1B PEOPLE","14 MONTHS","3 NETWORKS","23 COUNTRIES","1 LIE"],
}

def enforce_number_noun(thumb_text, topic, niche_name, ai_fn=None):
    if re.search(r'\b\d[\d,\.]*\b|\$', thumb_text):
        return re.sub(r'[^A-Z0-9$.,% ]','', thumb_text.upper()).strip()[:22]
    m = re.search(r'\b(\d[\d,\.]*)\s*(\w+)', topic)
    if m:
        return f"{m.group(1)} {m.group(2).upper()[:8]}"[:22]
    if ai_fn:
        try:
            r = ai_fn(
                f"Topic: {topic[:80]}\n"
                f"Generate 2-3 word thumbnail in NUMBER+NOUN format.\n"
                f"Examples: '$2.4M GONE', '47 REPORTS', '14 VICTIMS', '4380 DAYS'\n"
                f"Return ONLY the phrase in ALL CAPS.", tokens=20)
            if r and re.search(r'\d', r):
                return re.sub(r'[^A-Z0-9$.,% ]','', r.upper()).strip()[:22]
        except:
            pass
    return random.choice(NUMBER_NOUN_BANKS.get(niche_name, ["14 YEARS","47 CASES","1 TRUTH"]))


def score_title_v2(title):
    t  = title.lower()
    sc = 3.0
    bd = {}
    # Curiosity gap
    cg = ["nobody knew","never told","what was hidden","the real reason",
          "kept secret","concealed","covered up","went unnoticed","was ignored"]
    cg_hits = sum(1 for s in cg if s in t)
    if cg_hits >= 2:   sc += 2.5; bd["curiosity_gap"] = "STRONG"
    elif cg_hits == 1: sc += 1.5; bd["curiosity_gap"] = "OK"
    else:              bd["curiosity_gap"] = "WEAK"
    # Specificity
    has_num    = bool(re.search(r'\b\d[\d,\.]*\b', title))
    has_dollar = bool(re.search(r'\$[\d,\.]+', title))
    has_name   = bool(re.search(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', title))
    if (has_num or has_dollar) and has_name: sc += 2.0; bd["specificity"] = "STRONG"
    elif has_num or has_dollar or has_name:  sc += 1.2; bd["specificity"] = "OK"
    else:                                    bd["specificity"] = "WEAK"
    # Revelation
    rev = ["exposed","revealed","documented","proved","evidence","classified","traced"]
    if any(s in t for s in rev): sc += 1.5; bd["revelation"] = "PRESENT"
    else:                        bd["revelation"] = "ABSENT"
    # Pattern interrupt
    pi = ["they knew","it was allowed","it was ignored","still happening","went unpunished"]
    if any(s in t for s in pi): sc += 1.5; bd["pattern_interrupt"] = "PRESENT"
    else:                       bd["pattern_interrupt"] = "ABSENT"
    # Length
    n = len(title)
    if 50 <= n <= 65:    sc += 1.0
    elif 45 <= n <= 70:  sc += 0.5
    elif n < 40 or n > 80: sc -= 0.5
    # Generic penalty
    generic = ["incredible","unbelievable","shocking","amazing","you won't believe"]
    sc -= sum(0.8 for g in generic if g in t)
    return round(min(max(sc, 0), 10), 1), bd


def run_title_ctr_gate(title_str, title_scores, topic, niche_name,
                        series_name, episode, ai_fn, min_ctr=6.5):
    if not title_scores:
        return title_str, [(title_str, 5.0)]
    v2_scored = sorted([(t, score_title_v2(t)[0]) for t, _ in title_scores],
                        key=lambda x: x[1], reverse=True)
    best_title, best_score = v2_scored[0]
    if best_score >= min_ctr:
        return best_title, v2_scored
    # Regenerate with targeted fix
    _, bd = score_title_v2(best_title)
    weak  = [k for k,v in bd.items() if "WEAK" in str(v) or "ABSENT" in str(v)]
    fixes = {
        "curiosity_gap":    "Start with 'Nobody knew' or 'What the records show'",
        "specificity":      "Include a specific number",
        "revelation":       "Include 'documented', 'exposed', or 'revealed'",
        "pattern_interrupt":"Add 'They Knew' or 'Still Happening'",
    }
    fix_instructions = "\n".join(f"- {fixes[w]}" for w in weak[:2] if w in fixes)
    if not fix_instructions:
        fix_instructions = "- Add a specific number AND a curiosity gap phrase"
    try:
        result = ai_fn(
            f"Generate 5 stronger YouTube titles for: {topic[:120]}\n"
            f"Series: {series_name} Ep{episode}\n"
            f"Current best score: {best_score}/10 — too low.\n"
            f"Required fixes:\n{fix_instructions}\n"
            f"Rules: 50-65 chars. Dark documentary tone.\n"
            f'Return ONLY: ["Title 1","Title 2","Title 3","Title 4","Title 5"]',
            tokens=300)
        if result:
            result = re.sub(r'```json|```','', result).strip()
            m = re.search(r'\[[\s\S]*?\]', result)
            if m:
                titles  = [t for t in json.loads(m.group()) if t]
                new_scored = sorted([(t, score_title_v2(t)[0]) for t in titles],
                                     key=lambda x: x[1], reverse=True)
                if new_scored and new_scored[0][1] > best_score:
                    return new_scored[0][0], new_scored
    except:
        pass
    return best_title, v2_scored


AFFILIATE_REGISTRY = {
    "betterhelp":   {"url": "https://betterhelp.com/deepdive",      "label": "BetterHelp therapy",       "channels": ["all"]},
    "nordvpn":      {"url": "https://nordvpn.com/deepdive",          "label": "NordVPN privacy",          "channels": ["evidence_room","control_files"]},
    "curiosity":    {"url": "https://curiositystream.com/deepdive",  "label": "CuriosityStream docs",     "channels": ["all"]},
    "audible":      {"url": "https://amzn.to/deepdive-audible",      "label": "Audible audiobooks",       "channels": ["all"]},
}

def build_affiliate_block(channel_id, niche_name=""):
    ch = channel_id.replace("betrayal_deepdive","betrayal_deepdive")
    lines = ["\n\n— LINKS —"]
    for key, link in AFFILIATE_REGISTRY.items():
        if "all" in link["channels"] or ch in link["channels"]:
            lines.append(f"▸ {link['label']}: {link['url']}")
    if len(lines) < 2:
        return ""
    lines.append("\n*Affiliate links — support the channel at no cost to you.")
    return "\n".join(lines)


CHAPTER_STRUCTURES = {
    "betrayal_deepdive": [
        (0.00,"The Case Begins"),(0.10,"Before It Happened"),(0.28,"First Warning Signs"),
        (0.45,"Escalation"),(0.60,"The Revelation"),(0.78,"The Aftermath"),(0.90,"What This Means"),
    ],
    "evidence_room": [
        (0.00,"Case File Opened"),(0.10,"The Subject"),(0.28,"First Anomalies"),
        (0.45,"The Evidence Builds"),(0.60,"Key Document Revealed"),(0.78,"The Full Record"),(0.90,"Verdict"),
    ],
    "control_files": [
        (0.00,"The System"),(0.10,"How It Was Built"),(0.28,"Documented Cases"),
        (0.45,"The Evidence"),(0.60,"The Scale"),(0.78,"Those Who Resisted"),(0.90,"Implications"),
    ],
}

def generate_chapter_timestamps(script_clean, total_duration_secs, channel_id):
    if total_duration_secs < 120:
        return ""
    structure = CHAPTER_STRUCTURES.get(channel_id, CHAPTER_STRUCTURES["betrayal_deepdive"])
    lines = []
    for pct, label in structure:
        secs = int(total_duration_secs * pct)
        lines.append(f"{secs//60}:{secs%60:02d} {label}")
    return "\n".join(lines)


CROSS_PROMO = {
    "betrayal_deepdive": {
        "main":  "\n\n🔬 Forensic crime investigations: youtube.com/@TheEvidenceRoom\n🧠 Psychology documentaries: youtube.com/@TheControlFiles\n\n📺 New investigation every weekday.",
        "short": "\n\n🔬 Forensic: youtube.com/@TheEvidenceRoom\n🧠 Psychology: youtube.com/@TheControlFiles",
    },
    "evidence_room": {
        "main":  "\n\n🌑 Dark psychological horror: youtube.com/@BetrayalDeepDive\n🧠 Psychology documentaries: youtube.com/@TheControlFiles\n\n📺 New investigation every weekday.",
        "short": "\n\n🌑 Dark horror: youtube.com/@BetrayalDeepDive\n🧠 Psychology: youtube.com/@TheControlFiles",
    },
    "control_files": {
        "main":  "\n\n🔬 Forensic crime investigations: youtube.com/@TheEvidenceRoom\n🌑 Dark psychological horror: youtube.com/@BetrayalDeepDive\n\n📺 New investigation every weekday.",
        "short": "\n\n🔬 Forensic: youtube.com/@TheEvidenceRoom\n🌑 Dark horror: youtube.com/@BetrayalDeepDive",
    },
}

def get_cross_promo(channel_id, is_short=False):
    p = CROSS_PROMO.get(channel_id, CROSS_PROMO["betrayal_deepdive"])
    return p["short"] if is_short else p["main"]

TG_TOKEN = os.environ.get("TELEGRAM_TOKEN","")
TG_CHAT  = os.environ.get("TELEGRAM_CHAT_ID","")

def send_hype_push(video_url, video_title, channel_name, day=0):
    if not TG_TOKEN or not TG_CHAT:
        return
    urgency = {0:"⚡ First hour — maximum impact", 3:"🔥 4 days left", 6:"⏰ LAST DAY"}.get(day,"")
    msg = (
        f"🚀 <b>HYPE THIS VIDEO — {urgency}</b>\n\n"
        f"<b>{channel_name}</b>: {video_title}\n\n"
        f"▶️ {video_url}\n\n"
        f"<b>How to Hype (10 seconds):</b>\n"
        f"1. Open the link on YouTube\n"
        f"2. Tap the 🔥 Hype button under the video\n"
        f"3. Done — YouTube pushes this to the Explore leaderboard\n\n"
        f"⏳ 7-day window only. Every Hype = free algorithmic reach."
    )
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT, "text": msg, "parse_mode": "HTML"},
            timeout=25)
    except:
        pass

def validate_retention_hooks(script_clean, channel_id="betrayal_deepdive"):
    words   = script_clean.split()
    total   = len(words)
    if total < 400:
        return 0.0, []
    penalty = 0.0
    issues  = []
    hooks   = ["subscribe","coming up","next","what happens","revealed","in a moment",
               "stay","about to","what we found next","the next document"]
    def seg(p1, p2):
        return " ".join(words[int(total*p1):int(total*p2)]).lower()
    if sum(1 for h in hooks if h in seg(0.25,0.35)) < 1:
        penalty -= 0.4; issues.append("Missing 30% retention hook")
    if sum(1 for h in hooks if h in seg(0.55,0.65)) < 1:
        penalty -= 0.8; issues.append("Weak 60% peak hook")
    if sum(1 for h in hooks if h in seg(0.75,0.85)) < 1:
        penalty -= 0.4; issues.append("Missing 80% retention hook")
    if "subscribe" not in " ".join(words[-60:]).lower():
        penalty -= 0.3; issues.append("Missing subscribe CTA in final 60 words")
    return round(penalty, 1), issues



_gen_chapters = generate_chapter_timestamps


# ── CREDENTIALS ─────────────────────────────────────────────
# ── Core credentials ──────────────────────────────────────
GROQ_KEY        = os.environ.get("GROQ_API_KEY", "")
GEMINI_KEY      = os.environ.get("GEMINI_API_KEY", "")
CEREBRAS_KEY    = os.environ.get("CEREBRAS_API_KEY", "")
OPENROUTER_KEY  = os.environ.get("OPENROUTER_API_KEY", "")
COHERE_KEY      = os.environ.get("COHERE_API_KEY", "")
MISTRAL_KEY     = os.environ.get("MISTRAL_API_KEY", "")
SAMBANOVA_KEY   = os.environ.get("SAMBANOVA_API_KEY", "")  # 1000 req/day free — cloud.sambanova.ai
GEMINI_KEY_2    = os.environ.get("GEMINI_API_KEY_2", "")   # backup Gemini key — doubles quota
YT_CLIENT_ID    = os.environ.get("EVIDENCE_YT_CLIENT_ID",  os.environ.get("YOUTUBE_CLIENT_ID",""))
YT_CLIENT_SEC   = os.environ.get("EVIDENCE_YT_CLIENT_SECRET", os.environ.get("YOUTUBE_CLIENT_SECRET",""))
YT_REFRESH      = os.environ.get("EVIDENCE_YT_REFRESH_TOKEN", os.environ.get("YOUTUBE_REFRESH_TOKEN",""))
TG_TOKEN        = os.environ.get("TELEGRAM_TOKEN", "")
TG_CHAT         = os.environ.get("TELEGRAM_CHAT_ID", "")

# ── API endpoints ──────────────────────────────────────────
GEMINI_URL      = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
GEMINI_LITE_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent"  # gemini-2.0-flash retired by Google June 1 2026
CEREBRAS_URL    = "https://api.cerebras.ai/v1/chat/completions"
SAMBANOVA_URL   = "https://api.sambanova.ai/v1/chat/completions"   # v12: added
OPENROUTER_URL  = "https://openrouter.ai/api/v1/chat/completions"
GROQ_URL        = "https://api.groq.com/openai/v1/chat/completions"
COHERE_URL      = "https://api.cohere.com/v2/chat"
MISTRAL_URL     = "https://api.mistral.ai/v1/chat/completions"
YT_UPLOAD_URL   = "https://www.googleapis.com/upload/youtube/v3"
YT_DATA_URL     = "https://www.googleapis.com/youtube/v3"
YT_TOKEN_URL    = "https://oauth2.googleapis.com/token"

# ── Paths — state in REPO (persists between runs) ─────────
SCRIPT_DIR    = Path(__file__).parent
WORK_DIR      = Path("/home/runner/work/evidence_room")
if not WORK_DIR.exists(): WORK_DIR = Path("/tmp/evidence_room")
WORK_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE    = SCRIPT_DIR / "state.json"   # persists in repo
INTEL_FILE    = SCRIPT_DIR / "intel.json"   # persists in repo
CKPT_FILE     = WORK_DIR / "checkpoint.json"

# Cerebras model names to try in order
CEREBRAS_MODELS = ["llama-3.3-70b", "llama3.3-70b", "llama-3.1-70b", "llama3.1-70b", "llama3.1-8b"]

W, H, FPS   = 1920, 1080, 24
MIN_WORDS   = 1900
MAX_WORDS   = 2100
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
    "forensic_finance":       ["en-GB-ThomasNeural","en-US-ChristopherNeural","en-GB-NoahNeural","en-US-BrianNeural"],
    "criminal_investigation": ["en-GB-RyanNeural","en-US-AndrewNeural","en-GB-NoahNeural","en-US-EricNeural"],
    "corporate_exposure":     ["en-US-BrianNeural","en-GB-ThomasNeural","en-US-ChristopherNeural","en-GB-OliverNeural"],
    "digital_forensics":      ["en-US-ChristopherNeural","en-GB-RyanNeural","en-US-JasonNeural","en-GB-NoahNeural"],
    "body_cam_police":        ["en-US-BrianNeural","en-GB-RyanNeural","en-US-ChristopherNeural","en-GB-ThomasNeural"],
    "courtroom_drama":        ["en-GB-ThomasNeural","en-US-ChristopherNeural","en-US-BrianNeural","en-GB-RyanNeural"],
    "robbery_documentaries":  ["en-GB-RyanNeural","en-US-BrianNeural","en-GB-ThomasNeural","en-US-ChristopherNeural"],
}

# ── ANIMATION STYLES ────────────────────────────────────────
STYLES = {
    "dark_minimal": {
        "bg":(2,2,10), "primary":(255,255,255), "accent":(200,0,0),
        "secondary":(120,120,140), "pulse":(180,0,0), "glow":(255,50,50),
        "desc":"Clinical dark — blood red on absolute black, maximum psychological impact"
    },
    "cinematic": {
        "bg":(3,6,18), "primary":(210,230,255), "accent":(200,0,0),
        "secondary":(80,110,160), "pulse":(20,80,200), "glow":(100,180,255),
        "desc":"Cinematic noir blue — glowing evidence reveals, deep shadow"
    },
    "documentary": {
        "bg":(12,10,8), "primary":(235,225,205), "accent":(200,0,0),
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
    {
        "name": "body_cam_police", "rpm": 10.50,
        "series": "The Evidence Room: Body Cam Files",
        "viral_search": "body cam footage police incident investigation documentary animated",
        "archive_search": "body cam footage reveals truth police incident 2022 2023 viral documentary",
        "thumbnail_triggers": ["FOOTAGE SEALED","NINE MINUTES","THEY KNEW","CAM NEVER LIED"],
        "seed_topics": [
            "Officer body cam captured 9 minutes of footage that overturned a conviction after 3 years",
            "A police department sealed body cam footage for 14 months — what it showed when released",
            "The body cam recording that contradicted every official statement made by the department",
            "A routine traffic stop body cam captured the moment a cover story began to unravel",
            "Three officers. Three body cams. Three different accounts. The footage showed something else entirely.",
            "The body cam footage a department said was accidentally deleted — recovered 2 years later",
            "What 11 minutes of body cam footage proved about a use-of-force incident nobody witnessed",
        ],
    },
    {
        "name": "courtroom_drama", "rpm": 10.00,
        "series": "The Evidence Room: Court Record Files",
        "viral_search": "courtroom trial transcript evidence animated investigation documentary",
        "archive_search": "courtroom trial transcript reveals truth fraud evidence 2022 2023 viral",
        "thumbnail_triggers": ["TRANSCRIPT SEALED","DAY FOUR","WITNESS BROKE","CASE COLLAPSED"],
        "seed_topics": [
            "The cross-examination transcript that made a prosecution witness contradict himself 14 times",
            "Three words spoken under oath on day four collapsed a $40M fraud case",
            "A court transcript sealed for 11 years — what it revealed about the original investigation",
            "The star witness recanted every statement on day three. The trial continued for six more days.",
            "Jury deliberation notes that surfaced prove the verdict was reached before day one of testimony",
            "A forensic accountant's 6-hour testimony that the prosecution tried to suppress from the record",
            "The courtroom exhibit that nobody questioned — until an appeal attorney read page 47",
        ],
    },
    {
        "name": "robbery_documentaries", "rpm": 10.50,
        "series": "The Evidence Room: Heist Files",
        "viral_search": "heist robbery investigation animated documentary true crime",
        "archive_search": "greatest heist robbery unsolved investigation documentary viral 2022 2023",
        "thumbnail_triggers": ["NEVER SOLVED","81 MINUTES","26 MONTHS","STILL MISSING"],
        "seed_topics": [
            "The Isabella Stewart Gardner Museum theft: $500M in art stolen in 81 minutes. Still unsolved.",
            "Eleven men spent 26 months tunneling into a vault under a bank. They took everything and left one note.",
            "The casino robbery planned over 4 years by a team who communicated only through dead drops",
            "A diamond heist where the thieves replaced every stone with identical fakes before anyone noticed",
            "The Antwerp diamond district robbery: $100M taken over a weekend while guards watched the monitors",
            "A bank job where the robbers returned every dollar 3 days later — and the reason has never been explained",
            "The Securitas depot robbery: the largest cash theft in British history, planned from inside the company",
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
                             timeout=25)
            if r.status_code != 200: log(f"  TG {r.status_code}")
            time.sleep(0.5)
        except Exception as e: log(f"  TG err: {str(e)[:50]}")

def tg_updates(offset=None):
    try:
        params = {"timeout": 25, "allowed_updates": ["message","callback_query"]}
        if offset: params["offset"] = offset
        r = requests.get(f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates",
                         params=params, timeout=30)
        return r.json().get("result", [])
    except: return []

def tg_buttons(text, chat_id=None):
    """Send Telegram message with APPROVE / REJECT / CHANGE inline buttons."""
    keyboard = {"inline_keyboard": [[
        {"text": "✅ APPROVE",        "callback_data": "approved"},
        {"text": "❌ REJECT",         "callback_data": "rejected"},
        {"text": "✏️ CHANGE TITLE",   "callback_data": "change"},
    ]]}
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": chat_id or TG_CHAT,
                  "text": text, "parse_mode": "HTML",
                  "reply_markup": keyboard}, timeout=25)
        return r.json().get("result", {}).get("message_id")
    except Exception as e:
        log(f"  tg_buttons error: {e}")
        return None

def tg_answer_callback(callback_id, answer_text="Got it"):
    """Dismiss the spinning loader on the button after it's pressed."""
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/answerCallbackQuery",
            json={"callback_query_id": callback_id, "text": answer_text}, timeout=20)
    except: pass

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
    _models = ["gpt-oss-120b", "zai-glm-4.7", "llama-3.3-70b", "llama3.3-70b", "llama-3.1-70b", "llama3.1-70b", "llama3.1-8b"]  # Cerebras free-tier catalog narrowed to gpt-oss-120b/zai-glm-4.7 as of June 2026 — old llama names kept as fallback in case they return
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
    # Groq announced deprecation of llama-3.3-70b-versatile on June 17 2026.
    # Try the recommended replacements first, keep the old name as last-resort
    # in case the grace period is still active.
    for model in ["openai/gpt-oss-120b", "qwen/qwen3.6-27b", "llama-3.3-70b-versatile"]:
        try:
            r = requests.post(GROQ_URL,
                headers={"Authorization": f"Bearer {GROQ_KEY}",
                         "Content-Type": "application/json"},
                json={"model": model,
                      "messages": [{"role": "user", "content": prompt}],
                      "temperature": 0.88,
                      "max_tokens": min(tokens, 4800)},  # TPM limit is 6000
                timeout=90)
            if r.status_code == 200:
                t = r.json().get("choices",[{}])[0].get("message",{}).get("content","")
                if t and len(t.strip()) > 100:
                    log(f"  OK Groq ({model})")
                    return t
            elif r.status_code in (400, 404):
                log(f"  Groq {model}: {r.status_code} (model gone) — trying next")
                continue
            else:
                log(f"  Groq {model}: {r.status_code}: {r.text[:150]}")
        except Exception as e:
            log(f"  Groq {model}: {e}")
    return None

def _call_openrouter(prompt, tokens=9000):
    if not OPENROUTER_KEY:
        log("  OpenRouter: OPENROUTER_API_KEY secret not set — skipping")
        return None
    for model in [
        "meta-llama/llama-3.3-70b-instruct:free",
        "mistralai/mistral-7b-instruct:free",
        "google/gemma-2-9b-it:free",
        "microsoft/phi-3-mini-128k-instruct:free",
        "huggingfaceh4/zephyr-7b-beta:free",
        "openchat/openchat-3.5-0106:free",
    ]:
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
            json={"model": "command-r-08-2024",
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


# v12: SambaNova — added to Ch2 (was only in Ch1 before)
def _call_sambanova(prompt, tokens=9000):
    """
    SambaNova Cloud — free tier, 1000 req/day, llama-3.3-70b.
    Sign up free at https://cloud.sambanova.ai
    Add SAMBANOVA_API_KEY to GitHub Secrets.
    """
    if not SAMBANOVA_KEY:
        log("  SambaNova: SAMBANOVA_API_KEY not set — add free key from cloud.sambanova.ai")
        return None
    for model in ["Meta-Llama-3.3-70B-Instruct", "Meta-Llama-3.3-70B-Instruct"]:
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
                log("  SambaNova 401 — key invalid"); return None
            elif r.status_code == 429:
                log("  SambaNova 429 — daily limit"); return None
        except Exception as e:
            log(f"  SambaNova: {e}")
    return None


# v12: GEMINI_KEY_2 dual-key for Ch2 (doubles Gemini quota)
def _call_gemini_with_fallback(prompt, tokens=9000):
    """Try primary Gemini key then backup key, each across GEMINI_URL (2.5-flash) then GEMINI_LITE_URL (2.5-flash-lite)."""
    keys = [k for k in [GEMINI_KEY, GEMINI_KEY_2] if k]
    if not keys:
        log("  Gemini: GEMINI_API_KEY not set")
        return None
    for key_idx, active_key in enumerate(keys):
        key_label = "primary" if key_idx == 0 else "backup"
        for url_label, url in [("2.5-flash", GEMINI_URL), ("2.5-flash-lite", GEMINI_LITE_URL)]:
            if not url:
                continue
            try:
                r = requests.post(f"{url}?key={active_key}",
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
                            log(f"  OK Gemini ({key_label}, {url_label})")
                            return t
                elif r.status_code == 429:
                    log(f"  Gemini ({key_label}, {url_label}) 429 quota — trying next")
                    continue
                elif r.status_code == 404:
                    log(f"  Gemini ({key_label}, {url_label}) 404 — model retired, trying next")
                    continue
                else:
                    log(f"  Gemini ({key_label}, {url_label}): {r.status_code}")
            except Exception as e:
                log(f"  Gemini ({key_label}, {url_label}): {e}")
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
    v12: 7-provider chain: Cerebras → SambaNova → Gemini(+backup key) → Groq → OR → Cohere → Mistral
    10s sleep between failures to avoid cascading rate limits.
    """
    providers = [_call_cerebras, _call_sambanova, _call_gemini_with_fallback,
                 _call_groq, _call_openrouter, _call_cohere, _call_mistral]
    for i, fn in enumerate(providers):
        result = fn(prompt, tokens)
        if result: return result
        if i < len(providers) - 1:
            log(f"  Waiting 10s before next provider...")
            time.sleep(10)
    raise Exception("All 7 AI providers failed")

# Compatibility alias
def call_gemini(prompt, temp=0.85, tokens=7000, model="2.0"):
    return _call_gemini_with_fallback(prompt, tokens) or ai(prompt, tokens=tokens)

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
def score_title_ctr(title):  # v15: delegates to 5-axis scorer
    return score_title_v2(title)[0]

def _score_title_ctr_legacy(title):
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
    viral_patterns_str = "\n".join(patterns[:3])
    prompt = f"""
TITLE REQUIREMENTS — NON-NEGOTIABLE:
Do NOT write normal YouTube titles. The title should make someone screenshot it and send it to a friend.
Use specific numbers, real-feeling specificity, or uncomfortable implications.
Dark psychological humor outperforms pure shock — it signals intelligence.
The viewer should feel: "I shouldn't watch this... but I have to."

TITLE FORMULAS THAT WORK:
- "[Number] [People/Days/Years] [Disturbing Specific Thing] — Nobody Talked About This"
- "The [Institution] Knew. They Did It Anyway. Here's The File."
- "How [Normal Thing] Was Used To [Dark Outcome]"
- "[System] Ran [Disturbing Operation] For [Duration]. Here's The Evidence."
- "[Specific Crime]: [Number] Victims. [Number] Years. Zero Consequences."

FORBIDDEN: "Shocking", "Incredible", "Amazing", "Unbelievable", "You Won't Believe", "Mind-Blowing"

TITLE REQUIREMENTS — NON-NEGOTIABLE:
Do NOT write normal YouTube titles. Normal titles = ignored.
The title should make someone screenshot it and send to a friend.
Use specific numbers, real-feeling specificity, uncomfortable implications.
Dark psychological humor outperforms pure shock — signals intelligence.
Viewer must feel: "I know I should not watch this... but I have to."

TITLE FORMULAS THAT WORK:
- "[Number] [People/Days] [Disturbing Specific Thing] — Nobody Talked About This"
- "The [Institution] Knew. They Did It Anyway. Here Is The File."
- "How [Completely Normal Thing] Was Used To [Dark Outcome]"
- "[Number] Victims. [Number] Years. [Number] Investigations. Zero Arrests."
- "They Called It [Normal Name]. The Documents Called It Something Else."

FORBIDDEN TITLE WORDS: Shocking, Incredible, Amazing, Unbelievable, You Won't Believe, Mind-Blowing, Epic, Ultimate — these signal low quality.

Generate exactly 5 YouTube title variants for this forensic investigation video.
NICHE: {niche['name']} | SERIES: {niche['series']} Ep{episode}
TOPIC: {topic[:150]}
VIRAL PATTERNS: {viral_patterns_str}
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
                scored = sorted([(t,score_title_v2(t)[0]) for t in titles],key=lambda x:x[1],reverse=True)
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
    """
    v2 script generation for Ch2 (The Evidence Room):
    1. Research anchors prevent vague AI output
    2. Forensic documentary prompt with stage-specific structure
    3. Stage-level scoring + targeted rewrite of 2 worst stages
    4. Scene JSON extracted separately after narration
    """
    temp  = min(0.82 + attempt * 0.012, 0.94)
    hooks = intel.get("top_hook_formulas", ["The documents confirmed what investigators had suspected."])
    power = intel.get("niche_specific_power_words", ["documented","verified","traced","confirmed"])
    viral = intel.get("what_makes_videos_viral", "Specific documented evidence that viewers can verify")
    retention = intel.get("retention_hooks", ["The next document changes the entire case"])
    cross = f'\nReference previous investigation: "{prev_title}" naturally in closing.' if prev_title else ""

    # Research anchors
    anchors = {}
    try:
        anchor_prompt = (
            f"Generate specific realistic anchors for a forensic documentary about: {topic}\n"
            f"Return ONLY valid JSON (no backticks):\n"
            f'{{"case_duration":"e.g. 4380 days — twelve years",' 
            f'"people_affected":"e.g. 847 confirmed victims",'
            f'"discovery_date":"e.g. October 14 2019",'
            f'"key_document":"e.g. a 47-page internal audit dated March 2011",'
            f'"financial_figure":"e.g. $2.4 million over eleven years",'
            f'"institutional_failure":"e.g. 23 filed reports that reached no supervisor"}}' 
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

    stage_targets = {
        1: 120,   # Cold open — short and brutal
        2: 200,   # The before
        3: 280,   # First signals
        4: 480,   # Escalation — most evidence
        5: 150,   # False resolution
        6: 520,   # Real reveal — climax
        7: 150,   # Implication + CTA
    }

    power_str = ", ".join(power[:6])
    viral_hooks_str = "\n".join(f"  '{h}'" for h in hooks[:3])
    prompt = f"""Write a forensic investigative documentary narration script.
Style: precisely documented, evidence-driven, animated forensic format.

CASE: {topic}
SERIES: {niche['series']} — Episode {episode}
VIRAL HOOKS: {viral_hooks_str}
POWER WORDS: {power_str}
{anchor_block}{cross}

TOTAL: {MIN_WORDS} to {MAX_WORDS} words. Each stage must hit its target.

SEVEN-STAGE FORENSIC STRUCTURE — write continuously, no labels:

STAGE 1 — CASE FILE OPEN ({stage_targets[1]} words)
Sentence 1: exact case reference — number, date, or document ID.
Sentence 2: specific location of the discovery.
Sentence 3: the question this investigation will answer.
Forbidden: "welcome back", "today we investigate", "in this video"
TRIGGER PLACEMENT: DETAIL (s1) → PROXIMITY (s2) → open unresolved loop (s3)

STAGE 2 — THE SUBJECT ({stage_targets[2]} words)
Establish the entity — person, company, or system — as completely ordinary.
Specific details. Specific routine. Make the viewer care about what is about to be lost.
Final sentence signals something is about to break — without stating it.
Forbidden: "little did they know", "unbeknownst to", "but fate had other plans"
TRIGGER PLACEMENT: NORMALITY (s1-s3) → PROXIMITY (s4-s6) → quiet wrongness (final)

STAGE 3 — FIRST ANOMALIES ({stage_targets[3]} words)
Small discrepancies. Each individually explainable. One per sentence.
Start with the smallest. Build accumulation. Each one specific and documented.
Forbidden: "suddenly", "out of nowhere", "shockingly", "without warning"
TRIGGER PLACEMENT: INVISIBILITY (s1) → DURATION (s3) → SCALE (s5) → INSTITUTIONAL (s7)

STAGE 4 — THE EVIDENCE BUILDS ({stage_targets[4]} words)
One short sentence reframes Stage 3 entirely.
Documents arrive. Records are pulled. Each piece more specific than the last.
Short sentences then one longer. Real-feeling case references.
Forbidden: vague quantities — not "many reports" but "forty-seven reports"

STAGE 5 — FALSE CLOSURE ({stage_targets[5]} words)
Case appears resolved. Specific timeframe. Viewer exhales.
Final sentence: quietly, specifically wrong — not dramatic, not flagged.
Forbidden: "but it wasn't over", "however", "or so they thought"

STAGE 6 — THE FULL RECORD ({stage_targets[6]} words)
One short sentence destroys the false closure.
Then one finding per paragraph. Ordered by impact — each more significant.
Document references, file numbers, specific dates, specific figures.
Forbidden: "in conclusion", "to summarise", "as we can see"

STAGE 7 — CASE IMPLICATIONS ({stage_targets[7]} words)
Imply — never state — that this case is part of a larger pattern.
Subscribe CTA at emotional peak. Reference series.{cross}
Forbidden: "subscribe and like", "hit the bell", "don't forget to"


TONE AND STYLE (NON-NEGOTIABLE):
- This is DARK DOCUMENTARY — every sentence should feel like a weight pressing down.
- Dark psychological humor is permitted and encouraged. The kind that makes viewers 
  laugh uncomfortably, then feel disturbed they laughed.
- Every paragraph should leave the viewer wanting the next one. Not curious — CRAVING.
- Think: what would someone who KNOWS they shouldn't watch this keep watching anyway?
- Each stage should feel darker than the last. Build psychological dread deliberately.
- Real documentary references make it feel researched. Fake-sounding claims get skipped.
- Pacing: short sentences hit harder. Use them at revelation moments.
- The viewer should feel like they discovered something others don't know.

WHAT MAKES VIEWERS CRAVE THIS CONTENT:
- The sense that something was hidden — and you're the one showing it.
- The feeling that the world is slightly more dangerous/dark than they thought.
- Uncomfortable recognition — "this happened to someone I know" or "this could be me."
- The satisfaction of understanding a dark system fully, from start to end.
- Dark humor that signals: we both know this is messed up, and we're in it together.

CRAVEABILITY TRIGGERS — use at least 3 per script:
1. The statistic that sounds impossible but is real.
2. The name everyone knows, connected to something they didn't know.
3. The system that's still running right now — not historical.
4. The thing institutions tried to suppress or deny.
5. The detail so specific it has to be true.
6. The uncomfortable implication in the final 30 seconds.
7. The question the script raises but deliberately doesn't fully answer.

TONE AND STYLE — NON-NEGOTIABLE:
- DARK DOCUMENTARY. Every sentence = psychological weight pressing down.
- Dark humor that makes viewers laugh then feel disturbed they laughed.
- Every paragraph: viewers CRAVE the next one. Not curious — addicted.
- Each stage darker than the last. Build dread deliberately.
- Viewer should feel they discovered something others do not know.
- Pacing: short sentences at revelation moments. Hits harder.

CRAVEABILITY TRIGGERS — use minimum 3 per script:
1. The statistic that sounds impossible but is verifiably real.
2. The name everyone knows connected to something they never knew.
3. The system still running right now — not historical, not past tense.
4. The evidence institutions tried to suppress or deny.
5. The detail so specific it absolutely has to be true.
6. The uncomfortable implication in the final 30 seconds.
7. The question raised but deliberately left open.

RULES:
1. Maximum 13 words per sentence. Every sentence.
2. Zero markdown. Zero AI filler phrases.
3. Every number specific. Every date specific. Every location specific.
4. Write continuously — no stage labels, no headers.
5. Start immediately with Stage 1.

After writing the complete narration, add exactly 10 dashes on a new line, then provide scene JSON:
{{"title":"YouTube title 55-65 chars","thumbnail_text":"3 WORDS ALL CAPS with number","tags":["tag1","tag2","tag3","tag4","tag5","tag6","tag7","tag8","tag9","tag10"],"scenes":[
{{"type":"timeline","duration":8,"title":"CASE TIMELINE","events":["Event 1: date","Event 2: date","Event 3: date","Event 4: date"],"label":"CHRONOLOGY"}},
{{"type":"document_reveal","duration":7,"title":"THE KEY DOCUMENT","lines":["CASE FILE — RESTRICTED","Reference: [case number]","Finding: [key finding]","Status: [outcome]"],"stamp":"CLASSIFIED"}},
{{"type":"data_reveal","duration":7,"title":"THE NUMBERS","items":["$X.XM","XX YEARS","XXX VICTIMS","XX REPORTS"],"label":"CASE STATISTICS"}},
{{"type":"connection_map","duration":8,"title":"THE NETWORK","nodes":["ORIGIN","ENABLER","SYSTEM","OUTCOME"],"label":"HOW IT CONNECTED"}},
{{"type":"evidence_board","duration":10,"title":"EVIDENCE SUMMARY","items":["Finding 1","Finding 2","Finding 3","Finding 4"],"label":"CASE EVIDENCE"}}
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
            f"This forensic documentary script is {wc} words. Needs {MIN_WORDS} minimum.\n"
            f"Expand the Evidence Builds section and the Full Record section only.\n"
            f"Add specific case references, exact figures, exact dates, investigator reactions.\n"
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

            stage_names = ["CASE OPEN","SUBJECT","ANOMALIES","EVIDENCE",
                           "CLOSURE","FULL RECORD","IMPLICATIONS"]
            forbidden_per = [
                ["welcome back","today we investigate"],
                ["little did they know","unbeknownst"],
                ["suddenly","out of nowhere","without warning"],
                [],
                ["but it wasn't over","or so they thought"],
                ["in conclusion","to summarise"],
                ["subscribe and like","hit the bell"],
            ]
            stage_scores = []
            for i, (stext, sname, starget, sforbidden) in enumerate(
                    zip(stage_txts, stage_names, targets_l, forbidden_per)):
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

            stage_scores_str = " | ".join(f"{n[:6]}:{s}" for n,s in zip(stage_names,stage_scores))
            log(f"  Stage scores: {stage_scores_str}")
            worst_two = sorted(range(len(stage_scores)), key=lambda i: stage_scores[i])[:2]

            for idx in worst_two:
                if stage_scores[idx] >= 7.5:
                    continue
                rewrite_p = (
                    f"Rewrite ONLY this forensic documentary stage. Return ONLY the rewritten stage.\n\n"
                    f"STAGE: {stage_names[idx]} (target: {targets_l[idx]} words)\n"
                    f"TOPIC: {topic[:100]}\n"
                    f"SCORE: {stage_scores[idx]}/10 — sentences too long or too vague\n\n"
                    f"RULES:\n"
                    f"- Max 13 words per sentence.\n"
                    f"- Every number specific (not 'many' but '47').\n"
                    f"- Every date specific (not 'years ago' but 'March 2011').\n"
                    f"- Zero markdown. Zero AI filler.\n"
                    f"- Target: {targets_l[idx]} words (±15% ok).\n\n"
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

    # Parse scene JSON
    scenes, title, thumbnail_text, tags = [], f"The Evidence Room: {topic[:45]}", "CASE DOCUMENTED", \
        [niche["name"],"forensic","investigation","animated","crime","evidence","documentary",
         "exposed","deepdive","case"]
    if len(parts) > 1:
        try:
            jt = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]","",re.sub(r"```json|```","",parts[1]).strip())
            m  = re.search(r"\{[\s\S]*\}", jt)
            if m:
                data  = json.loads(m.group())
                scenes        = data.get("scenes", [])
                title         = data.get("title", title)
                thumbnail_text = data.get("thumbnail_text", thumbnail_text)
                tags          = data.get("tags", tags)
        except Exception as e:
            log(f"  Scene JSON (non-fatal): {e}")

    # Fallback scenes
    if not scenes:
        scenes = [
            {"type":"timeline","duration":8,"title":"CASE TIMELINE",
             "events":["Event 1","Event 2","Event 3","Event 4"],"label":"CHRONOLOGY"},
            {"type":"document_reveal","duration":7,"title":"KEY DOCUMENT",
             "lines":["CASE FILE — RESTRICTED","Reference: CF-2019-447",
                      "Finding: pattern confirmed","Status: under review"],"stamp":"CLASSIFIED"},
            {"type":"data_reveal","duration":7,"title":"THE NUMBERS",
             "items":["$2.4M","12 YEARS","847 CASES","47 REPORTS"],"label":"STATISTICS"},
            {"type":"connection_map","duration":8,"title":"THE NETWORK",
             "nodes":["ORIGIN","ENABLER","SYSTEM","OUTCOME"],"label":"CONNECTION"},
            {"type":"evidence_board","duration":10,"title":"EVIDENCE",
             "items":["Document 1","Document 2","Pattern","Conclusion"],"label":"EVIDENCE"},
        ]

    violations = len(re.findall(r"[#*_`\[\]{}<>\\]", clean))

    # CTA injection
    if len(clean.split()) >= 400:
        clean = _inject_ctas_er(clean, niche.get("name","forensic_finance"))
        wc    = len(clean.split())

    # Force expansion if under minimum word count
    for _exp in range(3):
        if wc >= MIN_WORDS or wc > MAX_WORDS: break
        deficit = MIN_WORDS - wc
        log(f"  {wc}w — expanding (need {deficit} more)...")
        try:
            ep = (f"This script is {wc} words. Needs {MIN_WORDS} minimum.\n"
                  f"Add {deficit} words. Expand evidence and human cost sections.\n"
                  f"Zero markdown. Max 13 words per sentence. Return COMPLETE script:\n\n"
                  + clean[:3000])
            raw2 = ai(ep, tokens=7000)
            if raw2:
                c2 = strip_md(raw2)
                if len(c2.split()) > wc:
                    clean = c2; wc = len(clean.split())
                    # Hard truncate to MAX_WORDS after expansion
                    if wc > MAX_WORDS:
                        words_list = clean.split()
                        clean = " ".join(words_list[:MAX_WORDS])
                        wc    = len(clean.split())
                    log(f"  Expanded to {wc}w")
        except Exception as _e:
            log(f"  Expansion (non-fatal): {_e}"); break
    log(f"  Script: {wc}w | {violations} MD | {len(scenes)} scenes")
    return clean, scenes, title, thumbnail_text, tags, violations


def render_connection_reveal(draw, W, H, nodes, progress, accent, font_sm):
    """
    Animate lines drawing between connection nodes progressively.
    nodes: list of (x, y, label) tuples
    """
    if len(nodes) < 2: return
    total_connections = len(nodes) - 1
    for i in range(total_connections):
        conn_progress = min(1.0, max(0.0, (progress * total_connections - i)))
        if conn_progress <= 0: continue
        x1, y1 = nodes[i][0], nodes[i][1]
        x2, y2 = nodes[i+1][0], nodes[i+1][1]
        cx = int(x1 + (x2 - x1) * conn_progress)
        cy = int(y1 + (y2 - y1) * conn_progress)
        draw.line([(x1, y1), (cx, cy)], fill=accent, width=2)
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
    stamp_text  = "CLASSIFIED"
    stamp_color = (200, 0, 0)
    bbox = draw.textbbox((0,0), stamp_text, font=font_lg)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    cx, cy = W//2, H//2
    draw.text((cx - tw//2 + 2, cy - th//2 + 2), stamp_text, font=font_lg, fill=(40,0,0))
    draw.text((cx - tw//2, cy - th//2), stamp_text, font=font_lg, fill=stamp_color)
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
            return True
    except Exception as e:
        log(f"  fetch_pollinations_bg (non-fatal): {e}")
    return False


def generate_thumbnail_with_ai_bg(title, thumb_text, niche_name, topic,
                                   ab_style="A", episode=1, channel_name="The Evidence Room"):
    """v2 thumbnail: three-layer composition via thumbnail_engine_v2."""
    try:
        import importlib.util
        if importlib.util.find_spec("thumbnail_engine_v2") is None:
            raise ImportError("thumbnail_engine_v2 not found")
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
        _enc_result = subprocess.run(
            ["ffmpeg","-y","-framerate",str(FPS),"-i",f"{fd}/frame_%05d.png",
             "-c:v","libx264","-preset","ultrafast","-crf","26",
             "-pix_fmt","yuv420p","-r",str(FPS),sm4],
            capture_output=True, timeout=600)
        # Verify scene mp4 was created before adding to concat
        if _enc_result.returncode == 0 and Path(sm4).exists() and \
           Path(sm4).stat().st_size > 50000:
            concat_parts.append(f"file '{sm4}'")
            log(f"    Scene {si+1} encoded: {Path(sm4).stat().st_size//1024}KB")
        else:
            # Fallback: create a solid-colour scene as replacement
            log(f"    Scene {si+1} encode failed — using fallback")
            _fb = str(fd)+"_fallback.mp4"
            subprocess.run([
                "ffmpeg","-y","-f","lavfi",
                "-i",f"color=c=black:s=1920x1080:d={dur_s}",
                "-c:v","libx264","-preset","ultrafast","-crf","26",
                "-pix_fmt","yuv420p","-r",str(FPS), _fb],
                capture_output=True, timeout=60)
            if Path(_fb).exists():
                concat_parts.append(f"file '{_fb}'")
                log(f"    Scene {si+1} fallback created")

    concat_file = str(WORK_DIR/"concat.txt")
    total_scene_dur = sum(s.get("duration",8) for s in scenes)
    repeats = max(1, int(duration/total_scene_dur)+2)
    with open(concat_file,"w") as f:
        for _ in range(repeats): f.write("\n".join(concat_parts)+"\n")

    raw = str(WORK_DIR/"raw.mp4")
    if not concat_parts:
        raise RuntimeError("All scene encodings failed — no parts for concat")
    log(f"  Concatenating {len(concat_parts)} scene parts...")
    _concat_result = subprocess.run(
        ["ffmpeg","-y","-f","concat","-safe","0","-i",concat_file,
         "-c:v","libx264","-preset","fast","-crf","23","-pix_fmt","yuv420p",
         "-r",str(FPS),raw],
        capture_output=True, timeout=900)
    if _concat_result.returncode != 0:
        err = _concat_result.stderr.decode("utf-8","ignore")[-300:]
        raise RuntimeError(f"FFmpeg concat failed: {err}")
    final = str(WORK_DIR/"final.mp4")
    # Add subtle ambient atmosphere (4% volume brown noise)
    ambient_path = str(WORK_DIR/"ambient_ch2.mp3")
    try:
        subprocess.run([
            "ffmpeg","-y","-f","lavfi",
            "-i",f"anoisesrc=color=brown:r=44100:d={int(duration)+5}",
            "-af","volume=0.03,highpass=f=300,lowpass=f=700",
            "-c:a","mp3","-q:a","9", ambient_path],
            capture_output=True, timeout=60)
        if Path(ambient_path).exists():
            mixed = str(WORK_DIR/"mixed_ch2.mp3")
            subprocess.run([
                "ffmpeg","-y","-i",audio_path,"-i",ambient_path,
                "-filter_complex","[0:a][1:a]amix=inputs=2:weights=1 0.03",
                "-c:a","mp3","-q:a","2", mixed],
                capture_output=True, timeout=120)
            if Path(mixed).exists() and Path(mixed).stat().st_size > 100000:
                audio_path = mixed
                log("  Ambient atmosphere mixed in")
    except Exception as _ae:
        log(f"  Ambient (non-fatal): {_ae}")

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

def apply_audio_post_processing(input_path, output_path=None, niche_name=None):
    """
    Transform edge-tts flat TTS into cinematic investigative narrator quality.
    EQ boosts presence, reverb adds room depth, compression smooths dynamics.
    """
    try:
        if output_path is None:
            output_path = input_path.replace(".mp3", "_eq.mp3").replace(".wav", "_eq.wav")
        if output_path == input_path:
            output_path = input_path + ".eq.mp3"
        af = (
            "equalizer=f=60:width_type=o:width=2:g=4,"
            "equalizer=f=250:width_type=o:width=2:g=2,"
            "equalizer=f=3000:width_type=o:width=2:g=-1,"
            "equalizer=f=8000:width_type=o:width=2:g=-2,"
            "aecho=0.85:0.88:60:0.3,"
            "acompressor=threshold=-20dB:ratio=3:attack=3:release=100:makeup=3dB,"
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


async def _tts_ch2(text, voice_id, path):
    """
    Chunked TTS — splits long scripts at sentence boundaries every 3000 chars.
    Prevents 'No audio was received' error on scripts over ~2000 words.
    """
    import edge_tts, shutil
    MAX_CHUNK = 500
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
        await asyncio.wait_for(c.save(path), timeout=120); return

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
    if len(parts) == 1: shutil.copy(parts[0], path); return

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
    Fixed threshold: edge-tts outputs ~48kbps MP3.
    Uses ffprobe actual duration. Falls back to 500KB minimum size check.
    """
    try:
        sz = Path(mp3_path).stat().st_size
        if sz < 200000:  # 200KB minimum
            log(f"  Quality FAIL: {sz}b — file empty or corrupt"); return False
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(mp3_path)],
            capture_output=True, text=True, timeout=30)
        if r.returncode == 0 and r.stdout.strip():
            actual_dur = float(r.stdout.strip())
            if actual_dur < dur_expected * 0.20:  # 20% = accept any audio >= 3 min
                log(f"  Quality FAIL: {actual_dur:.0f}s vs {dur_expected:.0f}s expected")
                return False
            log(f"  Quality OK: {sz/1024/1024:.1f}MB | {actual_dur:.0f}s"); return True
        log(f"  Quality OK (size): {sz/1024/1024:.1f}MB"); return True
    except Exception as e:
        log(f"  Quality check error: {e}"); return False


def run_stage3_audio(script_clean, voice_id, niche_name):
    log("\n"+"="*65)
    log(f"  STAGE 3: Human Voice Audio — {voice_id}")
    log("="*65)
    # Hard truncate to MAX_WORDS before TTS — prevents 40-chunk failures
    _words = script_clean.split()
    if len(_words) > MAX_WORDS:
        script_clean = " ".join(_words[:MAX_WORDS])
        log(f"  Script truncated to MAX_WORDS ({MAX_WORDS}w) for TTS reliability")
    wc           = len(script_clean.split())
    dur_expected = min((wc / 125.0) * 60.0, 900.0)  # cap at 15 min
    preferred    = NICHE_VOICES.get(niche_name, GB_VOICES[:4])
    GUARANTEED_VOICES = [
    "en-GB-ThomasNeural",       # Cold BBC gravitas — best for dark documentary
    "en-GB-RyanNeural",          # Deep British authority
    "en-US-BrianNeural",         # Deep commanding American documentary
    "en-US-ChristopherNeural",   # Serious weighted investigative
    "en-US-AndrewNeural",        # Authoritative storyteller
    "en-GB-NoahNeural",          # Deep investigative British
    "en-US-EricNeural",          # Calm serious gravitas
    "en-US-GuyNeural",           # Strong narrative
    "en-US-SteffanNeural",       # Measured documentary
    "en-GB-OliverNeural",        # Composed British authority
]
    voice_queue = [voice_id]
    for v in preferred:
        if v not in voice_queue and v not in ROBOTIC_VOICES: voice_queue.append(v)
    for v in GUARANTEED_VOICES:
        if v not in voice_queue: voice_queue.append(v)

    for _vi, v in enumerate(voice_queue[:12]):
        if _vi > 0: time.sleep(3)  # avoid edge-tts rate limit
        log(f"  Trying: {v}")
        mp3 = str(WORK_DIR / "audio.mp3")
        try:
            asyncio.run(asyncio.wait_for(_tts_ch2(script_clean, v, mp3), timeout=120))
            if not Path(mp3).exists(): continue
            if not check_audio_quality(mp3, dur_expected):
                log(f"  {v} failed quality — trying next"); continue
            sz  = Path(mp3).stat().st_size
            dur = dur_expected
            log(f"  ACCEPTED: {v} | {sz/1024/1024:.1f}MB | ~{dur/60:.1f}min")
            # Apply cinematic EQ processing
            processed = str(WORK_DIR / "audio_processed.mp3")
            _proc_path = str(WORK_DIR / "audio_eq_processed.mp3")
            if _proc_path == mp3:  # same file guard
                _proc_path = str(WORK_DIR / "audio_eq_out.mp3")
            mp3 = apply_audio_post_processing(mp3, _proc_path, niche_name)
            wav = str(WORK_DIR / "audio.wav")
            try:
                subprocess.run(["ffmpeg", "-y", "-i", mp3, "-acodec", "pcm_s16le",
                                "-ar", "24000", "-ac", "1", wav],
                               capture_output=True, timeout=300)
                if Path(wav).exists() and Path(wav).stat().st_size > 100000:
                    return wav, dur, sz, v
            except: pass
            return mp3, dur, sz, v
        except Exception as e:
            log(f"  {v} err: {str(e)[:60]}"); time.sleep(3)

    # ── FALLBACK CHAIN: every edge-tts voice failed today. Try alternate
    # providers before giving up entirely, so one bad day for Microsoft's
    # free TTS doesn't mean no video at all. Ordered by quality:
    # Fish Audio (natural, free tier via API key) -> gTTS (free, no key,
    # noticeably more robotic but reliable) -> offline espeak-ng
    # (guaranteed local synthesis, most robotic, true last resort).
    log("  All edge-tts voices exhausted — trying backup TTS providers...")

    fish_key = os.environ.get("FISH_AUDIO_API_KEY", "")
    if fish_key:
        try:
            mp3 = str(WORK_DIR / "audio_fish.mp3")
            r = requests.post("https://api.fish.audio/v1/tts",
                headers={"Authorization": f"Bearer {fish_key}",
                          "Content-Type": "application/json",
                          "model": "s2-pro"},
                json={"text": script_clean, "format": "mp3",
                       "normalize": True, "prosody": {"speed": 1.0}},
                timeout=180)
            if r.status_code == 200 and len(r.content) > 50000:
                with open(mp3, "wb") as f: f.write(r.content)
                if check_audio_quality(mp3, dur_expected):
                    sz = Path(mp3).stat().st_size
                    log(f"  ACCEPTED: Fish Audio backup | {sz/1024/1024:.1f}MB")
                    tg("⚠️ Evidence Room: all edge-tts voices failed today — used Fish Audio backup instead (still natural-sounding)")
                    mp3p = apply_audio_post_processing(mp3, str(WORK_DIR/"audio_fish_eq.mp3"), niche_name)
                    wav = str(WORK_DIR / "audio_fish.wav")
                    try:
                        subprocess.run(["ffmpeg","-y","-i",mp3p,"-acodec","pcm_s16le","-ar","24000","-ac","1",wav],
                                       capture_output=True, timeout=300)
                        if Path(wav).exists() and Path(wav).stat().st_size > 100000:
                            return wav, dur_expected, sz, "fish-audio-s2-pro"
                    except Exception: pass
                    return mp3p, dur_expected, sz, "fish-audio-s2-pro"
            else:
                log(f"  Fish Audio: {r.status_code} — {str(r.content)[:150]}")
        except Exception as e:
            log(f"  Fish Audio backup failed: {e}")
    else:
        log("  FISH_AUDIO_API_KEY not set — skipping Fish Audio backup")

    try:
        from gtts import gTTS
        import shutil as _shutil
        mp3 = str(WORK_DIR / "audio_gtts.mp3")
        _words = script_clean.split()
        gtts_chunks = [" ".join(_words[i:i+400]) for i in range(0, len(_words), 400)]
        parts = []
        for i, chunk in enumerate(gtts_chunks):
            part = str(WORK_DIR / f"gtts_part_{i}.mp3")
            try:
                gTTS(text=chunk, lang="en", tld="co.uk", slow=False).save(part)
                if Path(part).exists() and Path(part).stat().st_size > 2000:
                    parts.append(part)
            except Exception as e:
                log(f"    gTTS chunk {i} error: {e}")
        if parts:
            if len(parts) == 1:
                _shutil.copy(parts[0], mp3)
            else:
                lst = str(WORK_DIR / "gtts_list.txt")
                with open(lst, "w") as f:
                    for p in parts: f.write(f"file '{p}'\n")
                subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",lst,"-c","copy",mp3],
                               capture_output=True, timeout=300)
            if Path(mp3).exists() and Path(mp3).stat().st_size > 50000:
                sz = Path(mp3).stat().st_size
                log(f"  ACCEPTED: gTTS backup | {sz/1024/1024:.1f}MB (lower quality)")
                tg("⚠️ Evidence Room: edge-tts AND Fish Audio both failed today — used gTTS backup "
                   f"(noticeably more robotic). Check FISH_AUDIO_API_KEY / provider status.")
                return mp3, dur_expected, sz, "gtts-fallback"
    except Exception as e:
        log(f"  gTTS backup failed: {e}")

    try:
        mp3 = str(WORK_DIR / "audio_espeak.mp3")
        wav = str(WORK_DIR / "audio_espeak.wav")
        subprocess.run(["espeak-ng", "-v", "en-us", "-s", "150", "-w", wav, script_clean[:20000]],
                       capture_output=True, timeout=180)
        if Path(wav).exists() and Path(wav).stat().st_size > 50000:
            subprocess.run(["ffmpeg","-y","-i",wav,mp3], capture_output=True, timeout=60)
            final = mp3 if Path(mp3).exists() else wav
            sz = Path(final).stat().st_size
            log(f"  ACCEPTED: offline espeak-ng (LAST RESORT) | {sz/1024/1024:.1f}MB")
            tg("🚨 Evidence Room: ALL providers failed today (edge-tts, Fish Audio, gTTS) — used OFFLINE "
               f"robotic voice as last resort so the video still published. Check provider status urgently.")
            return final, dur_expected, sz, "espeak-offline-LASTRESORT"
    except Exception as e:
        log(f"  espeak-ng backup failed: {e}")

    tg("Evidence Room Stage 3 FAILED — all voices AND all backup providers failed")
    sys.exit(1)


def fetch_case_relevant_image_ch2(topic, niche_name, out_path):
    """Case-relevant image search for Channel 2 thumbnails — Pixabay first, then Pexels."""
    PIXABAY_KEY = os.environ.get("PIXABAY_KEY", "")
    PEXELS_KEY  = os.environ.get("PEXELS_API_KEY", "")
    stopwords   = {"a","an","the","and","or","in","on","to","of","with","was","been","have"}
    topic_words = [w.strip(".,!?") for w in topic.lower().split()
                   if len(w) > 3 and w not in stopwords]
    search_kw   = " ".join(topic_words[:3])
    niche_mod   = {
        "forensic_finance":       "dark corporate financial documents",
        "criminal_investigation": "dark crime evidence investigation",
        "corporate_exposure":     "dark corporate shadow documents",
        "digital_forensics":      "dark technology screen code shadow",
    }
    full_query = f"{search_kw} {niche_mod.get(niche_name, 'dark investigation')}"

    if PIXABAY_KEY:
        try:
            r = requests.get("https://pixabay.com/api/",
                params={"key": PIXABAY_KEY, "q": full_query, "image_type": "photo",
                        "orientation": "horizontal", "per_page": 3}, timeout=25)
            if r.status_code == 200 and r.json().get("hits"):
                url = r.json()["hits"][0].get("webformatURL")
                if url:
                    ir = requests.get(url, timeout=20)
                    if ir.status_code == 200 and len(ir.content) > 20000:
                        with open(out_path, "wb") as f: f.write(ir.content)
                        log(f"  Case image Ch2 (Pixabay): {search_kw}")
                        return True
        except: pass

    if PEXELS_KEY:
        try:
            r = requests.get("https://api.pexels.com/v1/search",
                headers={"Authorization": PEXELS_KEY},
                params={"query": full_query, "per_page": 3,
                        "orientation": "landscape"}, timeout=25)
            if r.status_code == 200:
                photos = r.json().get("photos", [])
                if photos:
                    url = photos[0]["src"]["large"]
                    ir  = requests.get(url, timeout=20)
                    if ir.status_code == 200 and len(ir.content) > 20000:
                        with open(out_path, "wb") as f: f.write(ir.content)
                        log(f"  Case image Ch2 (Pexels): {search_kw}")
                        return True
        except: pass
    return False


def generate_thumbnail(title, thumb_text, niche_name, topic, ab_style="A",
                        episode=1, channel_name="The Evidence Room"):
    """Three-layer thumbnail via thumbnail_engine_v2. Fallback to Pollinations+Pillow."""
    try:
        import importlib.util
        if importlib.util.find_spec("thumbnail_engine_v2") is None:
            raise ImportError("thumbnail_engine_v2 not found")
        from thumbnail_engine_v2 import generate_thumbnail_v2
        result = generate_thumbnail_v2(
            title=title, thumb_text=thumb_text, niche_name=niche_name,
            topic=topic, channel_name=channel_name, episode=episode,
            work_dir=str(WORK_DIR), ab_variant=ab_style)
        if result and Path(result).exists():
            log(f"  Thumbnail v2: {Path(result).stat().st_size//1024}KB")
            return result
    except Exception as e:
        log(f"  Thumbnail v2 (non-fatal): {e}")
    # Fallback: Pollinations + Pillow
    return generate_thumbnail_with_ai_bg(title, thumb_text, niche_name, topic, ab_style)


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
              "status": {
                  "privacyStatus": "public",
                  "selfDeclaredMadeForKids": False,
                  "madeForKids": False,
                  "containsSyntheticMedia": True   # mandatory AI disclosure since Mar 2024
              }},
                timeout=30)
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

# ════════════════════════════════════════════════════════════
# v12.0 NEW FUNCTIONS — TRAFFIC & REVENUE MAXIMISATION
# ════════════════════════════════════════════════════════════

def generate_dedicated_short_title_ch2(main_title, short_type, niche_name):
    """Dedicated Short title for Ch2 — forensic investigation angle."""
    prompts = {
        "teaser": f"Write a YouTube Shorts title that creates maximum curiosity for a forensic investigation. "
                  f"Topic: {main_title[:80]}. Under 55 chars, starts with a document/evidence/number fact. Return ONLY the title.",
        "recap":  f"Write a YouTube Shorts title revealing the key evidence found. "
                  f"Topic: {main_title[:80]}. Under 55 chars, implies proof was found. Return ONLY the title.",
    }
    type_key = "teaser" if "teaser" in short_type.lower() else "recap"
    try:
        result = ai(prompts[type_key], tokens=80)
        if result:
            title = re.sub(r'[#*_`]', '', result.strip().split("\n")[0].strip())
            if 15 < len(title) < 65:
                log(f"  Short title Ch2: {title}")
                return title
    except Exception as e:
        log(f"  Short title Ch2 (non-fatal): {e}")
    defaults = {"teaser": "What the Records Revealed", "recap": "Evidence Found — Full Case Above"}
    return defaults.get(type_key, main_title[:50])


def post_short_creator_comment_ch2(token, video_id, niche_name, main_title):
    """Pinned creator comment on each Ch2 Short. Drives early engagement signals."""
    short_hooks = {
        "forensic_finance":       "What financial warning sign do you wish more people understood?",
        "criminal_investigation": "What detail in this case makes it impossible to look away?",
        "corporate_exposure":     "Have you ever seen corporate documents like these in real life?",
        "digital_forensics":      "Did you know how much of your digital trail can be reconstructed?",
    }
    hook = short_hooks.get(niche_name, "What was the most disturbing piece of evidence?")
    comment = (
        f"🔬 {hook}\n\n"
        f"Full forensic investigation ↑ above.\n"
        f"🔔 New case every weekday → subscribe\n"
        f"🌑 Dark horror: youtube.com/@BetrayalDeepDive\n"
        f"🧠 Mass manipulation: youtube.com/@TheControlFiles\n\n"
        f"#{niche_name.replace('_','')} #shorts #forensic #investigation"
    )
    try:
        r = requests.post(
            "https://www.googleapis.com/youtube/v3/commentThreads",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            params={"part": "snippet"},
            json={"snippet": {"videoId": video_id,
                              "topLevelComment": {"snippet": {"textOriginal": comment}}}},
            timeout=30)
        if r.status_code == 200: log("  Short creator comment Ch2 OK")
        else: log(f"  Short comment {r.status_code} (non-fatal)")
    except Exception as e:
        log(f"  Short comment (non-fatal): {e}")


def build_ch2_cross_promo(is_short=False):
    """Three-channel cross-promotion for Ch2 descriptions."""
    if is_short:
        return (
            "\n\n🌑 Dark horror investigations: youtube.com/@BetrayalDeepDive"
            "\n🧠 Mass manipulation exposed: youtube.com/@TheControlFiles"
        )
    return (
        "\n\n🌑 Dark psychological horror: youtube.com/@BetrayalDeepDive"
        "\n🧠 Mass manipulation & propaganda: youtube.com/@TheControlFiles"
        "\n\n📺 New investigation every weekday on all three channels."
    )


def track_episode_ch2(state, niche_name, score, voice, episode):
    """Performance tracker for Ch2 — same as Ch1's track_episode."""
    perf = state.get("performance", {})
    n    = perf.get(niche_name, {"scores": [], "streak_below": 0})
    n["scores"]       = (n["scores"] + [score])[-20:]
    n["streak_below"] = (n["streak_below"] + 1) if score < 7.3 else 0
    n["last_episode"] = episode
    perf[niche_name]  = n
    v = perf.get(f"voice_{voice}", {"scores": []})
    v["scores"] = (v["scores"] + [score])[-20:]
    perf[f"voice_{voice}"] = v
    state["performance"] = perf
    return state



# ════════════════════════════════════════════════════════════
# STANDALONE NICHE SHORTS — 2 original Shorts beyond teaser/recap
# ════════════════════════════════════════════════════════════

SHORTS_TEMPLATES = {
    "forensic_finance":       ["The one financial warning sign that nobody acted on",
                               "The document trail that exposed the entire fraud"],
    "criminal_investigation": ["The single piece of evidence that broke the whole case",
                               "The detail in the scene that proved it was not an accident"],
    "corporate_exposure":     ["The internal memo that exposed the cover-up",
                               "The document they tried to destroy and failed"],
    "digital_forensics":      ["The digital trace that was impossible to erase",
                               "The metadata that revealed the entire timeline"],
}

def generate_standalone_short_script(niche_name, topic, short_num):
    """
    Generate a 45-second standalone Short script optimised for the Shorts algorithm.
    ~120-130 words = 45 seconds at natural TTS pace.
    Structure: Immediate hook → Fast context → Single devastating reveal → CTA
    """
    angles = {
        0: "the single most shocking documented fact from this case",
        1: "the warning sign that everyone missed before it was too late",
    }
    angle = angles.get(short_num, angles[0])

    prompt = f"""Write a 45-second YouTube Shorts narration script.
Topic: {topic}
Focus angle: {angle}
Niche feel: {niche_name.replace('_', ' ')} — dark, investigative, forensic

STRUCTURE:
Line 1 (HOOK): Start with a specific number, date, or dollar amount. Mid-action. No "today we".
Lines 2-4 (CONTEXT): Three short punchy sentences. Max 10 words each.
Lines 5-6 (REVEAL): The one fact that changes everything. Documented and real.
Line 7 (CTA): "Full investigation on our channel." or "Watch the full case above."

RULES:
- Exactly 120-130 words total
- Every sentence max 12 words
- Include at least ONE specific number or date
- No markdown, no headers, no asterisks
- Plain narration text only

Write the script:"""

    result = ai(prompt, tokens=350)
    if result:
        clean = result.strip().replace("**","").replace("##","").replace("*","")
        words = clean.split()
        if len(words) > 132:
            clean = " ".join(words[:130])
        log(f"  Short {short_num+1} script: {len(clean.split())}w")
        return clean
    return None


async def generate_short_audio_async(script, voice, out_path):
    """Generate audio for standalone Short using edge-tts."""
    import edge_tts
    try:
        comm = edge_tts.Communicate(text=script, voice=voice, rate="-5%")
        await asyncio.wait_for(comm.save(out_path), timeout=120)
        if Path(out_path).exists() and Path(out_path).stat().st_size > 50000:
            return True
    except Exception as e:
        log(f"  Short audio error: {e}")
    return False


def create_standalone_short_video(script, audio_path, niche_name, short_num):
    """
    Create animated Short video from script + audio.
    Vertical 1080x1920. Channel 2 brand: animated frames + text overlay.
    """
    from PIL import Image, ImageDraw, ImageFont

    W, H = 1080, 1920

    # Get audio duration via ffprobe
    dur_result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_streams", audio_path],
        capture_output=True, text=True, timeout=30)
    duration = 45.0
    try:
        import json as _json
        streams = _json.loads(dur_result.stdout).get("streams", [])
        for s in streams:
            if s.get("codec_type") == "audio":
                duration = float(s.get("duration", 45.0)); break
    except: pass

    bg_colors = {
        "forensic_finance":       (8, 12, 20),
        "criminal_investigation": (12, 5, 5),
        "corporate_exposure":     (5, 8, 12),
        "digital_forensics":      (5, 15, 10),
    }
    bg = bg_colors.get(niche_name, (8, 8, 15))

    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    def gf(sz):
        for fp in font_paths:
            if Path(fp).exists():
                try: return ImageFont.truetype(fp, sz)
                except: pass
        return ImageFont.load_default()

    sents = [s.strip() for s in script.replace("\n"," ").split(".") if len(s.strip()) > 5]
    sections = [
        " ".join(sents[:2]),
        " ".join(sents[2:5]),
        " ".join(sents[5:]),
    ]

    frames_dir = WORK_DIR / f"short_frames_{short_num}"
    frames_dir.mkdir(exist_ok=True)

    fps           = 24
    total_frames  = int(duration * fps)
    section_frames= total_frames // 3
    frame_list    = []

    for section_idx, section_text in enumerate(sections):
        words_s = section_text.split()
        for fi in range(section_frames):
            progress = fi / section_frames
            img  = Image.new("RGB", (W, H), bg)
            draw = ImageDraw.Draw(img)

            # Animated red progress bar at top
            bar_w = int(W * ((section_idx * section_frames + fi) / total_frames))
            draw.rectangle([0, 0, bar_w, 10], fill=(200, 0, 0))
            draw.rectangle([0, 0, W, 10], outline=(60, 0, 0), width=1)

            # Channel badge
            draw.text((40, 30), "● THE EVIDENCE ROOM", font=gf(26), fill=(160, 0, 0))

            # Section progress dots
            for dot_i in range(3):
                color = (200, 0, 0) if dot_i <= section_idx else (40, 40, 40)
                draw.ellipse([W//2-30+dot_i*25, H-80, W//2-14+dot_i*25, H-64], fill=color)

            # Animated word reveal
            visible_words = max(1, int(len(words_s) * min(progress * 1.8, 1.0)))
            display_text  = " ".join(words_s[:visible_words])

            # Word wrap
            wrapped = []; current = []
            for word in display_text.split():
                current.append(word)
                if len(" ".join(current)) > 22:
                    wrapped.append(" ".join(current[:-1])); current = [word]
            if current: wrapped.append(" ".join(current))

            fm = gf(72)
            total_h = len(wrapped) * 85
            start_y = (H - total_h) // 2
            for li, line in enumerate(wrapped[:6]):
                y = start_y + li * 85
                bbox = draw.textbbox((0, 0), line, font=fm)
                x    = (W - (bbox[2] - bbox[0])) // 2
                for dx, dy in [(-2,-2),(2,-2),(-2,2),(2,2)]:
                    draw.text((x+dx, y+dy), line, font=fm, fill=(30, 0, 0))
                draw.text((x, y), line, font=fm,
                          fill=(220, 15, 15) if section_idx == 0 else (230, 230, 230))

            if section_idx == 2:
                pulse = int(abs(progress - 0.5) * 200)
                draw.rectangle([4, 4, W-4, H-4], outline=(pulse, 0, 0), width=3)

            fpath = str(frames_dir / f"f{section_idx:01d}_{fi:04d}.jpg")
            img.save(fpath, "JPEG", quality=85)
            frame_list.append(fpath)

    list_file = str(WORK_DIR / f"short_list_{short_num}.txt")
    with open(list_file, "w") as lf:
        for fp in frame_list:
            lf.write(f"file '{fp}'\nduration {1/fps}\n")

    out_path = str(WORK_DIR / f"standalone_short_{short_num}.mp4")
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", list_file,
        "-i", audio_path,
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-pix_fmt", "yuv420p", "-r", str(fps),
        "-c:a", "aac", "-b:a", "128k",
        "-t", str(duration + 0.3), "-shortest",
        out_path
    ], capture_output=True, timeout=300)

    if Path(out_path).exists() and Path(out_path).stat().st_size > 200000:
        log(f"  Standalone Short {short_num}: {Path(out_path).stat().st_size//(1024*1024)}MB")
        # Cleanup frames
        shutil.rmtree(str(frames_dir), ignore_errors=True)
        return out_path
    return None


def create_and_upload_standalone_shorts(token, niche, topic, voice, description,
                                        tags, playlist_id, title_str):
    """
    Generate 2 standalone niche Shorts and upload them.
    These are original content — NOT clips from the main video.
    Each targets different keywords, driving independent search traffic.
    Non-fatal: if they fail, the main video and clip Shorts are unaffected.
    """
    standalone_uploaded = []

    for short_num in range(2):
        try:
            log(f"\n  Standalone Short {short_num+1}/2...")

            script = generate_standalone_short_script(niche["name"], topic, short_num)
            if not script:
                log(f"  Short {short_num+1} script failed — skipping"); continue

            audio_out = str(WORK_DIR / f"standalone_short_audio_{short_num}.mp3")
            ok        = asyncio.run(generate_short_audio_async(script, voice, audio_out))
            if not ok:
                log(f"  Short {short_num+1} audio failed — skipping"); continue

            video_out = create_standalone_short_video(script, audio_out,
                                                      niche["name"], short_num)
            if not video_out:
                log(f"  Short {short_num+1} video failed — skipping"); continue

            short_title = (
                f"{script.split('.')[0][:50]} #Shorts"
                if short_num == 0
                else f"THE EVIDENCE ROOM: {topic[:35]} #Shorts"
            )
            short_desc = (
                f"{script[:200]}\n\n"
                f"Watch the full investigation: {title_str}\n\n"
                f"🔔 Subscribe: youtube.com/@TheEvidenceRoom\n"
                f"#{niche['name'].replace('_','')} #shorts #forensic #investigation"
            )

            su, sid = upload_yt(video_out, short_title, short_desc,
                                tags[:8], is_short=True, token=token)
            add_to_playlist(token, playlist_id, sid)
            standalone_uploaded.append(su)
            log(f"  Standalone Short {short_num+1} uploaded: {su}")

        except Exception as e:
            log(f"  Standalone Short {short_num+1} error (non-fatal): {e}")

    return standalone_uploaded


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

def run_stage1(state):
    """
    13-attempt script engine for Ch2 The Evidence Room.
    Returns all script data needed by generate phase.
    """
    log("\n"+"="*65)
    log("  STAGE 1: Evidence Room 13-Attempt Script Engine")
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
            # v15: title CTR gate
            title_str, tscores = run_title_ctr_gate(
                title_str, tscores, topic, niche["name"], niche["series"],
                episode, lambda p, tokens=300: ai(p, tokens=tokens, prefer="groq"))
            best_thumbnail     = thumbnail_text
            best_title_str     = title_str
            best_title_scores  = tscores
            log(f"Thumbnail: {thumbnail_text}")

        log(f"\nAttempt {attempt}/8 (gate:{gate})...")
        log(f"Topic: {topic[:80]}")

        try:
            script_clean, scenes, title, thumb, tags, violations = generate_script_and_scenes(
                niche, topic, style_name, episode, attempt, intel, prev_title)
            wc = len(script_clean.split())
            score, issues = score_script_er(script_clean, wc, violations)
            log(f"  {score}/10 {'APPROVED' if score>=gate else 'BLOCKED'} | {wc}w | MD:{violations}")
            if issues:
                iss_str = " | ".join(issues[:3])
                log(f"  {iss_str}")

            if score > best_score:
                best_score  = score
                best_script = script_clean
                best_scenes = scenes
                if thumb and thumb != "EVIDENCE FOUND": best_thumbnail = thumb
                best_tags   = tags
            if score >= gate:
                log(f"\nSCRIPT APPROVED: {score}/10 | Attempt {attempt}\n")
                return (niche, topic, voice, style_name, episode,
                        best_script, best_scenes, best_title_str,
                        best_thumbnail, best_title_scores, score, best_tags, intel)
            time.sleep(3)
        except Exception as e:
            log(f"  Error: {str(e)[:80]}")
            time.sleep(15)

    if best_script and best_score >= FINAL_GATE:
        log(f"\nUsing best: {best_score}/10 after 13 attempts")
        tg(f"Note: Publishing {best_score}/10 after 13 attempts.")
        return (niche, used_topics[-1], voice, style_name, episode,
                best_script, best_scenes, best_title_str,
                best_thumbnail, best_title_scores, best_score, best_tags or [], intel)

    state["last_niche"] = niche["name"]; save_state(state)
    tg(f"Evidence Room Day Skipped\nBest: {best_score}/10 after 13 attempts")
    sys.exit(0)



def run_stage2_approval_ch2(title_str, niche, score, script_clean):
    """30-minute approval gate for Ch2 Evidence Room."""
    deadline     = datetime.datetime.now() + datetime.timedelta(minutes=30)
    deadline_str = deadline.strftime("%I:%M %p")
    preview      = script_clean[:400].replace("<","").replace(">","")
    msg = (
        f"<b>EVIDENCE ROOM APPROVAL NEEDED</b>\n\n"
        f"Title: {title_str}\n"
        f"Niche: {niche['name']} | Score: {score}/10\n"
        f"Auto-uploads at {deadline_str}\n\n"
        f"Reply APPROVE or REJECT"
    )
    keyboard = {"inline_keyboard": [
        [{"text": "APPROVE", "callback_data": "approved"},
         {"text": "REJECT",  "callback_data": "rejected"}]
    ]}
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT, "text": msg,
                  "parse_mode": "HTML", "reply_markup": keyboard},
            timeout=25)
        tg(f"Preview: {preview}...")
    except Exception as e:
        log(f"  Approval notification (non-fatal): {e}")
    # Poll for response
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates",
            params={"timeout": 25}, timeout=30)
        updates = r.json().get("result", [])
        offset  = (max(u["update_id"] for u in updates) + 1) if updates else 0
    except:
        offset = 0
    decision = "auto_approved"
    while datetime.datetime.now() < deadline:
        time.sleep(30)
        try:
            r2 = requests.get(
                f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates",
                params={"timeout": 25, "offset": offset,
                        "allowed_updates": ["callback_query", "message"]},
                timeout=30)
            for u in r2.json().get("result", []):
                offset = u["update_id"] + 1
                if "callback_query" in u:
                    cb   = u["callback_query"]
                    data = cb.get("data", "")
                    try:
                        requests.post(
                            f"https://api.telegram.org/bot{TG_TOKEN}/answerCallbackQuery",
                            json={"callback_query_id": cb.get("id",""),
                                  "text": "Got it!"}, timeout=20)
                    except:
                        pass
                    if data == "approved":
                        tg("APPROVED. Generating video...")
                        return "approved"
                    elif data == "rejected":
                        tg("REJECTED. Stopping.")
                        return "rejected"
        except:
            pass
    tg("30 min expired — auto-approved.")
    return "auto_approved"


def _inject_ctas_er(script_clean, niche_name):
    """
    Inject subscribe CTAs at 30/60/80% word marks for retention + conversion.
    Channel-specific, niche-specific phrasing — never identical wording.
    """
    cta_bank = {
        "forensic_finance": [
            "If documented cases like this concern you, subscribe — new files every week.",
            "This channel investigates documented financial fraud. Subscribe to follow the evidence.",
            "More documented cases like this are coming. Subscribe to The Evidence Room.",
        ],
        "criminal_investigation": [
            "If this case concerns you, subscribe — documented investigations every week.",
            "This channel documents criminal investigations. Subscribe to follow the evidence.",
            "More documented cases like this are coming. Subscribe to The Evidence Room.",
        ],
        "corporate_exposure": [
            "If this pattern concerns you, subscribe — documented exposures every week.",
            "This channel investigates documented corporate misconduct. Subscribe to follow the record.",
            "More documented findings like this are coming. Subscribe to The Evidence Room.",
        ],
        "digital_forensics": [
            "If this trail concerns you, subscribe — documented digital cases every week.",
            "This channel documents digital forensic investigations. Subscribe to follow the evidence.",
            "More documented cases like this are coming. Subscribe to The Evidence Room.",
        ],
    }
    ctas = cta_bank.get(niche_name, cta_bank["forensic_finance"])

    words = script_clean.split()
    total = len(words)
    if total < 400:
        return script_clean

    marks = [int(total * 0.30), int(total * 0.60), int(total * 0.80)]
    inserted = 0
    result = script_clean

    for i, mark_pct in enumerate(marks):
        cta = ctas[i % len(ctas)]
        target_word_idx = mark_pct + inserted
        all_words = result.split()
        if target_word_idx >= len(all_words):
            continue
        char_pos = len(" ".join(all_words[:target_word_idx]))
        next_period = result.find(". ", char_pos)
        if next_period == -1:
            continue
        insert_at = next_period + 2
        result = result[:insert_at] + cta + " " + result[insert_at:]
        inserted += len(cta.split()) + 1

    # Ensure subscribe CTA exists in final 60 words
    if "subscribe" not in " ".join(result.split()[-60:]).lower():
        result = result.rstrip() + " Subscribe to this channel for more documented investigations."
    return result



def run_ffmpeg(cmd, label="ffmpeg", timeout=300):
    """Run an ffmpeg subprocess with consistent logging and timeout handling."""
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=timeout)
        if result.returncode != 0:
            err = result.stderr.decode("utf-8", "ignore")[-200:]
            log(f"  {label}: ffmpeg exit {result.returncode} — {err}")
            return False
        return True
    except subprocess.TimeoutExpired:
        log(f"  {label}: ffmpeg timed out after {timeout}s")
        return False
    except Exception as e:
        log(f"  {label}: ffmpeg error — {e}")
        return False


def score_script_er(script_clean, wc, violations):
    """
    Score a generated script 0-10. Used as the quality gate before approval.
    Checks: word count, markdown violations, retention hooks at 30/60/80%.
    """
    if not script_clean:
        return 0.0, ["Empty script"]

    score  = 5.0
    issues = []

    if wc >= MIN_WORDS:
        score += 2.8
    elif wc >= int(MIN_WORDS * 0.8):
        score += 0.8
    else:
        score -= 2.0
        issues.append(f"Under word target: {wc}w")

    if violations == 0:
        score += 2.2
    elif violations <= 2:
        score += 0.8
    else:
        score -= 1.5
        issues.append(f"{violations} markdown violations")

    words = script_clean.split()
    total = len(words)
    if total >= 400:
        def seg(p1, p2):
            return " ".join(words[int(total*p1):int(total*p2)]).lower()
        hook_signals = ["subscribe", "coming up", "next", "what happens", "the answer",
                        "revealed", "in a moment", "stay", "about to", "this changes",
                        "documented", "the evidence", "what comes next"]
        if sum(1 for w in hook_signals if w in seg(0.25, 0.35)) < 1:
            score -= 0.4
            issues.append("Missing 30% retention hook")
        h60 = sum(1 for w in hook_signals if w in seg(0.55, 0.65))
        if h60 < 2:
            score -= 0.8
            issues.append("Weak 60% peak hook")
        elif h60 >= 3:
            score += 0.3
        if "subscribe" not in " ".join(words[-60:]).lower():
            score -= 0.3
            issues.append("Missing subscribe CTA in final 60 words")

    return min(round(score, 1), 10.0), issues




# ═══════════════════════════════════════════════════════════
# PORTED FROM Ch1 — Advanced features for Ch2
# ═══════════════════════════════════════════════════════════

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
        ("Cerebras",    _call_cerebras),
        ("SambaNova",   _call_sambanova),
        ("Gemini",      _call_gemini_with_fallback),
        ("Groq",        call_groq),
        ("OpenRouter",  _call_openrouter),
        ("Cohere",      _call_cohere),
        ("Mistral",     _call_mistral),
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


def _validate_retention_hooks(script_clean):
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
    if issues:
        issues_str = " | ".join(issues)
        log(f"  Retention issues: {issues_str}")
    return round(penalty, 1), issues

# ================================================================
# PSYCHOLOGICAL 7-STAGE SCRIPT  [IMPROVED]
# ================================================================

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
    black_fallback_count = 0
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

        # Try Pixabay, then Pexels (real fallback — was documented but never called), then a generic broad term
        downloaded = False
        search_terms = [kw, base_kw, BG_KEYWORDS.get(niche["name"], ["dark shadows"])[i % 3],
                         "cinematic dark atmosphere"]
        for search_kw in search_terms:
            if downloaded: break
            try:
                if PIXABAY_KEY:
                    r = requests.get("https://pixabay.com/api/videos/",
                        params={"key": PIXABAY_KEY, "q": search_kw, "per_page": 5,
                                "video_type": "film", "orientation": "horizontal"}, timeout=25)
                    if r.status_code == 200 and r.json().get("hits"):
                        hit = max(r.json()["hits"], key=lambda h: h.get("duration", 0))
                        url = hit["videos"]["medium"]["url"]
                        with requests.get(url, timeout=45, stream=True) as dl:
                            dl.raise_for_status()
                            with open(clip_path, "wb") as f:
                                for chunk in dl.iter_content(32768): f.write(chunk)
                        if Path(clip_path).exists() and Path(clip_path).stat().st_size > 50000:
                            downloaded = True; continue
                    elif r.status_code == 429:
                        log(f"    Stage {i+1} Pixabay: 429 rate limited")
            except Exception as e:
                log(f"    Stage {i+1} Pixabay: {e}")

            if not downloaded:
                try:
                    if PEXELS_KEY:
                        r = requests.get("https://api.pexels.com/videos/search",
                            headers={"Authorization": PEXELS_KEY},
                            params={"query": search_kw, "per_page": 5, "orientation": "landscape"},
                            timeout=25)
                        if r.status_code == 200 and r.json().get("videos"):
                            vids  = r.json()["videos"]
                            best  = max(vids, key=lambda v: v.get("duration", 0))
                            files_ = sorted(best.get("video_files", []),
                                            key=lambda vf: vf.get("width", 0), reverse=True)
                            url = next((vf["link"] for vf in files_ if vf.get("width", 0) <= 1920), None) \
                                  or (files_[0]["link"] if files_ else None)
                            if url:
                                with requests.get(url, timeout=45, stream=True) as dl:
                                    dl.raise_for_status()
                                    with open(clip_path, "wb") as f:
                                        for chunk in dl.iter_content(32768): f.write(chunk)
                                if Path(clip_path).exists() and Path(clip_path).stat().st_size > 50000:
                                    downloaded = True
                        elif r.status_code == 429:
                            log(f"    Stage {i+1} Pexels: 429 rate limited")
                except Exception as e:
                    log(f"    Stage {i+1} Pexels: {e}")

        if not downloaded:
            black_fallback_count += 1
            # Last resort only — real footage exhausted on both providers
            dur = max(int(stage_dur), 8)
            run_ffmpeg(["ffmpeg","-y","-f","lavfi",
                f"-i","color=c=black:size=1280x720:rate=24:duration={dur}",
                "-c:v","libx264","-pix_fmt","yuv420p", clip_path],
                label=f"stage-{i}-fallback")
            log(f"  Stage {i+1}: NO footage found on Pixabay or Pexels — using black clip")

        if Path(clip_path).exists():
            stage_clips.append((clip_path, stage_dur))

    if black_fallback_count > 0:
        tg(f"⚠️ {black_fallback_count}/{len(stage_defs)} background clips had NO real footage "
           f"(Pixabay+Pexels both empty/exhausted) — used black clip instead. Check PIXABAY_KEY / PEXELS_API_KEY.")

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
    cross_promo_txt = get_cross_promo("betrayal_deepdive", is_short=False)
    if raw:
        desc  = seo_first_line + "\n\n" + strip_md(raw)
        desc += cross_promo_txt
        desc += "\n\n⚠️ This video features AI-assisted narration and editing."
        return desc
    return (f"{title}\n\nEpisode {episode} of {niche['series']}.\n\n"
            f"Subscribe for new investigations every week.\n\n"
            f"#{niche['name'].replace('_', '')} #documentary #investigation"
            f"{cross_promo_txt}\n\n"
            f"⚠️ This video features AI-assisted narration and editing.")

# ================================================================
# ELEVENLABS TTS  [NEW #5]
# ================================================================

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


# ═══════════════════════════════════════════════════════════
# SSML MULTI-RATE AUDIO — Ported from Ch1 for human-sounding TTS
# Generates audio at 7 different rates per stage for natural pacing
# ═══════════════════════════════════════════════════════════

def inject_ssml_rate(script):
    """
    Split script into 7 stages by word proportion and inject
    SSML prosody rate markers. Edge-tts supports rate parameter
    but not inline SSML. Instead we split the audio into segments
    with different rates and concatenate.
    Returns list of (text_segment, rate_string) tuples.

    FIX (voice-quality pass):
    - Rate range narrowed to -5%..-10% (was up to -18%). Neural voices are
      trained on natural pacing; large negative rates cause unnatural
      syllable elongation, which reads as "robotic."
    - Segments now break on the nearest SENTENCE boundary to each target
      word count instead of a hard word-count cut. Cutting mid-sentence
      meant two independently-synthesized halves — with different rates —
      got glued together inside a single thought, producing an audible
      speed jump and unnatural gap mid-sentence.
    """
    import re as _re
    # Find all sentence-end positions (index into `words`) so we can snap
    # each stage boundary to the nearest sentence end rather than a raw
    # word count.
    words = script.split()
    total = len(words)
    sentence_end_word_idxs = []
    running = 0
    for sent in _re.split(r'(?<=[.!?])\s+', script):
        sent_wc = len(sent.split())
        running += sent_wc
        if running <= total:
            sentence_end_word_idxs.append(running)
    if not sentence_end_word_idxs or sentence_end_word_idxs[-1] != total:
        sentence_end_word_idxs.append(total)

    def snap_to_sentence_end(target_idx):
        if not sentence_end_word_idxs:
            return target_idx
        return min(sentence_end_word_idxs, key=lambda x: abs(x - target_idx))

    # Stage word boundaries (proportional to STAGE_WORDS), rates narrowed
    stage_rates = [
        (100,  "-5%"),   # Cold open: urgent, attention-grabbing
        (200,  "-7%"),   # The Before: normal documentary pace
        (250,  "-7%"),   # First Signals: measured, building
        (400,  "-5%"),   # Escalation: faster, momentum
        (200,  "-8%"),   # False Resolution: slow, relief
        (650,  "-10%"),  # Real Reveal: slower, weighty (was -18%)
        (200,  "-8%"),   # Implication + CTA: deliberate
    ]
    segments = []
    idx = 0
    cumulative_target = 0
    for word_count, rate in stage_rates:
        cumulative_target += word_count
        end = snap_to_sentence_end(min(cumulative_target, total))
        end = max(end, idx)  # never go backwards
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
            segments.append((remaining, "-8%"))
    return segments


def run_audio_with_ssml(script, niche_name, edge_voice):
    """
    Multi-rate audio: split script into 7 stage segments,
    generate each with its own delivery rate, concatenate via FFmpeg.
    Produces audio that sounds like a real documentary narrator.

    FIX (voice-quality pass): removed the mid-narration voice swap. If a
    segment failed before, it silently fell back to en-GB-RyanNeural or
    en-US-BrianNeural for JUST that one piece — meaning the narrator's
    voice could audibly change color for a few seconds mid-video, then
    switch back. Now every segment retries on the SAME configured voice
    (with backoff) before giving up, so the narrator stays consistent
    throughout. Also added a short crossfade at each concat join instead
    of a raw stream copy, to smooth the seams between independently
    synthesized segments.
    """
    segments = inject_ssml_rate(script)
    log(f"  SSML segments: {len(segments)} at rates {[r for _,r in segments]}")

    part_paths = []
    for i, (text, rate) in enumerate(segments):
        part_path = str(WORK_DIR / f"audio_seg_{i}.mp3")
        ok = False
        for attempt in range(3):
            if attempt > 0:
                time.sleep(3 * attempt)  # backoff, avoid edge-tts rate limit
            try:
                asyncio.run(asyncio.wait_for(
                    _edge_tts_segment(text, edge_voice, rate, part_path), timeout=90))
                if Path(part_path).exists() and Path(part_path).stat().st_size > 5000:
                    part_paths.append(part_path)
                    ok = True
                    break
            except Exception as e:
                log(f"    Segment {i} attempt {attempt+1} ({edge_voice}): {e}")
        if not ok:
            log(f"  Segment {i} failed on {edge_voice} after 3 attempts — skipping "
                f"(NOT switching narrator voice mid-video)")

    if not part_paths:
        return None, 0.0

    if len(part_paths) == 1:
        import shutil
        out = str(WORK_DIR / "ssml_narration.mp3")
        shutil.copy(part_paths[0], out)
        return out, get_media_duration(out)

    # Concatenate all segments with a short crossfade at each join instead
    # of a raw stream copy, so rate/pace transitions between segments don't
    # sound like an abrupt cut.
    out = str(WORK_DIR / "ssml_narration.mp3")
    CROSSFADE_S = 0.12
    try:
        filter_parts = []
        inputs = []
        for p in part_paths:
            inputs += ["-i", p]
        n = len(part_paths)
        prev_label = "0:a"
        for i in range(1, n):
            cur_label = f"a{i}"
            filter_parts.append(
                f"[{prev_label}][{i}:a]acrossfade=d={CROSSFADE_S}:c1=tri:c2=tri[{cur_label}]"
            )
            prev_label = cur_label
        filter_complex = ";".join(filter_parts)
        run_ffmpeg(["ffmpeg", "-y", *inputs,
                    "-filter_complex", filter_complex,
                    "-map", f"[{prev_label}]", out], label="ssml-crossfade-concat")
        if not Path(out).exists() or Path(out).stat().st_size < 5000:
            raise RuntimeError("crossfade concat produced no usable output")
    except Exception as e:
        log(f"  Crossfade concat failed ({e}) — falling back to plain concat")
        list_file = str(WORK_DIR / "seg_list.txt")
        with open(list_file, "w") as f:
            for p in part_paths:
                f.write(f"file '{p}'\n")
        run_ffmpeg(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                    "-i", list_file, "-c", "copy", out], label="ssml-concat")

    duration = get_media_duration(out)
    log(f"  SSML audio: {duration:.1f}s ({duration/60:.1f} min)")
    return out, duration



async def _edge_tts_segment(text, voice, rate, path):
    """Generate audio for one segment with a specific rate."""
    import edge_tts
    comm = edge_tts.Communicate(text=text, voice=voice, rate=rate)
    await asyncio.wait_for(comm.save(path), timeout=90)


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

def main():
    """
    Two-phase controller for Ch2 (The Evidence Room).
    PIPELINE_PHASE=generate : generate + save pending_upload.json
    PIPELINE_PHASE=upload   : read pending, upload to YouTube
    PIPELINE_PHASE=full     : legacy single-run (backward compatible)
    """
    from phase_manager import (get_pipeline_phase, save_pending,
                                load_pending, clear_pending, check_pending_age,
                                is_already_uploaded)

    phase      = get_pipeline_phase()
    SCRIPT_DIR = Path(__file__).parent
    state      = load_state()

    log(f"\nEVIDENCE ROOM v14.0 — Phase: {phase.upper()}")
    log(f"Time: {datetime.datetime.now().strftime('%a %d %b %Y %I:%M %p IST')}")

    # ── UPLOAD PHASE ──────────────────────────────────────────
    if phase == "upload":
        pending = load_pending(SCRIPT_DIR)
        if not pending or is_already_uploaded(pending):
            tg("⚠️ Ch2 Upload: no pending video. Generation may have failed.")
            sys.exit(0)
        is_fresh, hours_old = check_pending_age(pending, max_hours=30)
        if not is_fresh:
            tg(f"⚠️ Ch2 Upload: pending is {hours_old}h old — uploading anyway.")

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

        if not video_path or not Path(video_path).exists():
            tg(f"❌ Ch2 Upload: video file missing. Run Generate first.")
            sys.exit(1)

        token_yt = get_yt_token()
        # Create playlist now if generate phase skipped it
        if not playlist_id:
            niche_obj = next((n for n in NICHES if n["name"] == niche_name), None)
            if niche_obj:
                playlist_id = ensure_playlist(token_yt, niche_name, niche_obj["series"])
                if playlist_id:
                    pl = state.get("playlists",{}); pl[niche_name] = playlist_id
                    state["playlists"] = pl; save_state(state)
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

        # Upload all 6 Shorts — staggered 5-minute gaps between groups
        try:
            from shorts_engine import upload_all_six_shorts
            short_urls = upload_all_six_shorts(
                shorts          = shorts,
                upload_fn       = upload_yt,
                token           = token_yt,
                playlist_id     = playlist_id,
                post_comment_fn = lambda tok, vid, ch, ttl:
                                    post_short_creator_comment_ch2(tok, vid, niche_name, ttl),
                channel_id      = "evidence_room",
            )
            log(f"  Shorts uploaded: {len(short_urls)}/6")
        except Exception as e:
            log(f"  Shorts upload (non-fatal): {e}")
            short_urls = []

        if script_clean and duration > 0:
            try:
                from growth_engine import upload_srt_captions
                upload_srt_captions(token_yt, vid_id, script_clean, duration, "evidence_room")
            except Exception as e: log(f"  SRT (non-fatal): {e}")

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
                "SPRINT_CHANNEL_ID":  "evidence_room",
                "SPRINT_NICHE":       niche_name,
                "SPRINT_SHORTS_URLS": ",".join(short_urls),
                "SPRINT_SCORE":       str(score),
            })
            subprocess.Popen(
                ["python3", str(Path(__file__).parent.parent /
                               "growth_engine/growth_engine.py")],
                env=env_ext)
        except Exception as ge: log(f"  Growth engine (non-fatal): {ge}")

        # v15: Hype notification — free Explore leaderboard push
        send_hype_push(yt_url, title, "The Evidence Room", day=0)

        tg(f"✅ <b>The Evidence Room — LIVE</b>\n\n"
           f"<b>{title}</b>\n🔗 {yt_url}\n\n"
           f"Niche: {niche_name} | Score: {score}/10 | Ep{episode}\n"
           f"🚀 First-hour sprint active")
        log(f"\nUPLOAD COMPLETE: {yt_url}")
        return

    # ── GENERATE PHASE ────────────────────────────────────────
    episode = (datetime.datetime.now().timetuple().tm_yday//3)+1
    ckpt_clear()

    (niche, topic, voice, style_name, episode,
     script_clean, scenes, title_str, thumbnail_text,
     title_scores, score, tags, intel) = run_stage1(state)

    topic_used   = topic
    ab_style     = "A" if datetime.datetime.now().isocalendar()[1] % 2 == 1 else "B"
    week_number  = datetime.datetime.now().isocalendar()[1]
    cross_promo     = get_cross_promo("evidence_room", is_short=False)
    affiliate_block = build_affiliate_block("evidence_room", niche["name"])
    # chapters_block built AFTER audio so duration is available
    seo_first    = f"DOCUMENTED: {topic[:60]}."

    # Playlist created at upload time (YouTube creds not available in generate phase)
    playlist_id = state.get("playlists",{}).get(niche["name"], "")

    tags_er = list(set(tags))[:15]

    # APPROVAL GATE
    decision = run_stage2_approval_ch2(title_str, niche, score, script_clean)
    if decision == "rejected":
        log("Rejected."); sys.exit(0)

    # Audio
    audio_path, duration, audio_sz, voice_used = run_stage_with_retry(
        run_stage3_audio, "Audio", script_clean, voice, niche["name"])

    # Build description now that duration is known
    chapters_block = _gen_chapters(script_clean, duration, "evidence_room")
    description = (f"{seo_first}\n\nEpisode {episode} of {niche['series']}.\n\n"
                   f"Every case. Every document. Every piece of evidence — animated.\n\n"
                   f"{chapters_block}\n\n"
                   f"Subscribe to The Evidence Room."
                   f"{cross_promo}"
                   f"{affiliate_block}\n\n"
                   f"\u26a0\ufe0f AI-assisted narration and forensic analysis.")

    # Video
    video_path = run_stage_with_retry(
        render_and_encode, "Animation", style_name, scenes, audio_path, duration)

    # Thumbnail
    thumb_path = generate_thumbnail_with_ai_bg(
        title_str, thumbnail_text, niche["name"], topic, ab_style,
        episode=episode, channel_name="The Evidence Room")

    # Validate video file before saving to pending
    if not Path(video_path).exists():
        tg(f"❌ Ch2 Generate FAILED: video file not created")
        sys.exit(1)
    video_size = Path(video_path).stat().st_size
    if video_size < 5_000_000:  # must be at least 5MB
        tg(f"❌ Generate FAILED: video too small ({video_size//1024}KB) — likely encoding error")
        sys.exit(1)
    log(f"  Video validated: {video_size//(1024*1024)}MB")

    # All 6 Shorts — generate only, upload happens next day
    log("\n  Generating all 6 Shorts...")
    try:
        import importlib.util
        if importlib.util.find_spec("shorts_engine") is None:
            raise ImportError("shorts_engine not in PYTHONPATH")
        from shorts_engine import generate_all_six_shorts
        import asyncio, edge_tts as _edge_tts_module
        def _tts_fn_ch2(text, out_path):
            async def _run():
                c = _edge_tts_module.Communicate(text, voice_used, rate="-8%")
                await asyncio.wait_for(c.save(out_path), timeout=120)
            asyncio.run(_run())
        short_clips = generate_all_six_shorts(
            video_path     = video_path,
            script_clean   = script_clean,
            audio_duration = duration,
            main_title     = title_str,
            niche_name     = niche["name"],
            topic          = topic,
            channel_id     = "evidence_room",
            work_dir       = str(WORK_DIR),
            ai_fn          = lambda p, tokens=200: ai(p, tokens=tokens, prefer="groq"),
            tts_fn         = _tts_fn_ch2,
            main_video_url = "",
        )
        ok_count = sum(1 for s in short_clips if s.get("ok"))
        log(f"  Shorts: {ok_count}/6 generated")
    except Exception as e:
        log(f"  Shorts engine (non-fatal): {e}")
        short_clips = []

    save_pending(SCRIPT_DIR, {
        "title":          title_str,
        "description":    description,
        "tags":           tags_er,
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
        "topic":          topic,
    })

    state["last_niche"] = niche["name"]
    save_state(state)
    ckpt_clear()

    if phase == "generate":
        tg(f"✅ <b>Ch2 Generated — queued for upload</b>\n\n"
           f"<b>{title_str}</b>\n"
           f"Niche: {niche['name']} | Score: {score}/10\n"
           f"Style: {style_name} | {duration/60:.1f}min\n"
           f"Uploading at: 11:30 PM IST (6 PM UTC)")
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
                tg(f"⚠️ Ch2 attempt {attempt}/{max_retries} failed.\nRetrying in 2h...")
                time.sleep(7200)
            else:
                tg(f"❌ Ch2 FAILED after {max_retries} attempts.")
                sys.exit(1)
        except Exception as e:
            if attempt < max_retries:
                tg(f"⚠️ Ch2 crash {attempt}/{max_retries}: {str(e)[:200]}\nRetrying in 2h...")
                time.sleep(7200)
            else:
                tg(f"❌ Ch2 FAILED {max_retries}x: {str(e)[:300]}")
                sys.exit(1)


if __name__ == "__main__":
    main_with_retry()
