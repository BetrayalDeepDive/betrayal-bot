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
from groq import Groq

# ── CREDENTIALS ─────────────────────────────────────────────
GROQ_KEY      = os.environ["GROQ_API_KEY"]
GEMINI_KEY    = os.environ["GEMINI_API_KEY"]
YT_CLIENT_ID  = os.environ.get("EVIDENCE_YT_CLIENT_ID",  os.environ.get("YOUTUBE_CLIENT_ID",""))
YT_CLIENT_SEC = os.environ.get("EVIDENCE_YT_CLIENT_SECRET", os.environ.get("YOUTUBE_CLIENT_SECRET",""))
YT_REFRESH    = os.environ.get("EVIDENCE_YT_REFRESH_TOKEN", os.environ.get("YOUTUBE_REFRESH_TOKEN",""))
TG_TOKEN      = os.environ["TELEGRAM_TOKEN"]
TG_CHAT       = os.environ["TELEGRAM_CHAT_ID"]

groq_client   = Groq(api_key=GROQ_KEY)
GEMINI_URL    = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
GEMINI_LITE_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent"
WORK_DIR      = Path("/tmp/evidence_room")
WORK_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE    = WORK_DIR / "state.json"
INTEL_FILE    = WORK_DIR / "intel.json"

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
    "en-US-DavisNeural",        # Dark dramatic deep
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
    "en-GB-ElliotNeural",       # Deep calm investigative
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
    "dark_minimal":  {"bg":(2,2,10),    "primary":(255,255,255),"accent":(200,30,30), "secondary":(120,120,140),"desc":"Clinical dark — white/red on black"},
    "cinematic":     {"bg":(5,10,25),   "primary":(220,235,255),"accent":(80,160,255),"secondary":(100,130,180),"desc":"Cinematic dark blue — glowing reveals"},
    "documentary":   {"bg":(18,15,12),  "primary":(230,220,200),"accent":(180,40,20), "secondary":(140,120,100),"desc":"Documentary — aged documents stamps"},
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

def call_gemini(prompt, temp=0.85, tokens=7000, model="2.0"):
    url = GEMINI_URL if model=="2.0" else GEMINI_LITE_URL
    for attempt in range(5):
        try:
            r = requests.post(f"{url}?key={GEMINI_KEY}",
                headers={"Content-Type":"application/json"},
                json={"contents":[{"parts":[{"text":prompt}]}],
                      "generationConfig":{"temperature":temp,"maxOutputTokens":min(tokens,8192)},
                      "safetySettings":[{"category":c,"threshold":"BLOCK_NONE"} for c in
                          ["HARM_CATEGORY_HARASSMENT","HARM_CATEGORY_HATE_SPEECH",
                           "HARM_CATEGORY_SEXUALLY_EXPLICIT","HARM_CATEGORY_DANGEROUS_CONTENT"]]},
                timeout=90)
            if r.status_code==200:
                c = r.json().get("candidates",[])
                if c: return c[0]["content"]["parts"][0]["text"]
            elif r.status_code==429:
                wait = 60*(attempt+1)
                log(f"  Gemini {model} 429 — wait {wait}s")
                time.sleep(wait)
            else: time.sleep(20)
        except Exception as e:
            log(f"  Gemini {model} err: {str(e)[:60]}")
            time.sleep(20)
    raise Exception(f"Gemini {model} failed")

def call_groq(prompt, temp=0.7, tokens=2000):
    for attempt in range(4):
        try:
            r = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role":"user","content":prompt}],
                temperature=temp, max_tokens=min(tokens,2000))
            return r.choices[0].message.content
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                wait = min(90*(2**attempt),360)
                log(f"  Groq 429 — wait {wait}s")
                time.sleep(wait)
            else: raise
    raise Exception("Groq failed")

def ai(prompt, temp=0.85, tokens=7000, prefer="gemini"):
    """Gemini-first. Groq only for small metadata requests."""
    if tokens > 500:
        try: return call_gemini(prompt, temp, tokens, "2.0")
        except: return call_gemini(prompt, temp, tokens, "1.5")
    else:
        try: return call_groq(prompt, temp, min(tokens,2000))
        except: return call_gemini(prompt, temp, tokens, "2.0")

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
LAW 9: {MIN_WORDS} to {MAX_WORDS} words — reach the minimum
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
    import edge_tts
    c = edge_tts.Communicate(text, voice_id, rate="-8%", pitch="+0Hz", volume="+8%")
    await c.save(path)

def check_audio_quality(mp3_path, dur_expected):
    try:
        sz = Path(mp3_path).stat().st_size
        if sz < dur_expected * 8000:
            log(f"  Quality FAIL: {sz}b too small for {dur_expected:.0f}s")
            return False
        if sz < 80000:
            log(f"  Quality FAIL: {sz/1024:.0f}KB too small")
            return False
        log(f"  Quality OK: {sz/1024/1024:.1f}MB")
        return True
    except: return False

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
    for v in ALL_VOICES:
        if v not in voice_queue and v not in ROBOTIC_VOICES: voice_queue.append(v)

    for v in voice_queue[:8]:
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

    # Style-specific background treatment
    if style_name == "cinematic":
        for y in range(0,H,4): draw.line([(0,y),(W,y)],fill=(20,40,80),width=1)
    elif style_name == "documentary":
        for y in range(0,H,8):
            if random.random()<0.12: draw.line([(0,y),(W,y)],fill=(28,22,18),width=1)

    # Corner marks
    draw.line([(0,0),(70,0)],fill=accent,width=2)
    draw.line([(0,0),(0,70)],fill=accent,width=2)
    draw.line([(W-70,H-1),(W,H-1)],fill=accent,width=2)
    draw.line([(W-1,H-70),(W-1,H)],fill=accent,width=2)

    # Watermark
    draw.text((30,H-38),"THE EVIDENCE ROOM",font=font_xs,fill=secondary)
    draw.text((W-260,H-38),f"SCENE {scene_idx+1}/{total_scenes}",font=font_xs,fill=secondary)

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
    lines=scene.get("lines",["CONFIDENTIAL"]); stamp=scene.get("stamp","")
    primary,accent,secondary=style["primary"],style["accent"],style["secondary"]
    px,py,dw,dh=200,160,W-400,H-280
    pc=(12,12,18) if style_name!="documentary" else (20,16,12)
    draw.rectangle([(px,py),(px+dw,py+dh)],fill=pc,outline=secondary,width=1)
    draw.line([(px+20,py+60),(px+dw-20,py+60)],fill=secondary,width=1)
    n=len(lines)
    for i,line in enumerate(lines):
        lp=(progress*(n+1))-i
        if lp<=0: continue
        a=min(1.0,lp); y=py+80+i*55
        color=primary if not line.startswith("[") else secondary
        draw.text((px+40,y),line,font=font_mono,fill=color)
    if stamp and progress>0.7:
        sx,sy=px+dw-280,py+dh-200
        draw.rectangle([(sx,sy),(sx+240,sy+100)],outline=accent,width=3)
        draw.text((sx+15,sy+15),stamp,font=font_md,fill=accent)

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
    srt = generate_short_srt(script_clean, start, short_dur)
    if not srt: return raw
    sub_style = ("FontName=Arial,FontSize=24,PrimaryColour=&H00FFFFFF,"
                 "OutlineColour=&H00000000,BackColour=&HCC000000,"
                 "Bold=1,Outline=3,Shadow=1,Alignment=2,MarginL=40,MarginR=40,MarginV=130,BorderStyle=3")
    subprocess.run(["ffmpeg","-y","-i",raw,f"-vf","subtitles={srt}:force_style='{sub_style}'",
                    "-c:v","libx264","-preset","fast","-crf","21","-c:a","copy",final],
                   capture_output=True, timeout=180)
    if Path(final).exists() and Path(final).stat().st_size>400000:
        log(f"  Short ({stype}): {Path(final).stat().st_size/1024/1024:.1f}MB + subtitles")
        if Path(raw).exists(): Path(raw).unlink()
        return final
    return raw if Path(raw).exists() else None


# ════════════════════════════════════════════════════════════
# STAGE 6: UPLOAD
# ════════════════════════════════════════════════════════════
def get_yt_token():
    r = requests.post("https://oauth2.googleapis.com/token",data={
        "client_id":YT_CLIENT_ID,"client_secret":YT_CLIENT_SEC,
        "refresh_token":YT_REFRESH,"grant_type":"refresh_token"})
    d = r.json()
    if "access_token" not in d: raise Exception(f"YT token failed: {d}")
    return d["access_token"]

def upload_yt(path, title, description, tags, is_short=False):
    token = get_yt_token()
    if is_short: title = f"#Shorts {title[:50]}"
    init = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        headers={"Authorization":f"Bearer {token}","Content-Type":"application/json"},
        json={"snippet":{"title":title,"description":description,"tags":tags,"categoryId":"22"},
              "status":{"privacyStatus":"public","selfDeclaredMadeForKids":False}})
    url = init.headers.get("Location")
    if not url: raise Exception(f"No URL: {init.text[:200]}")
    sz = Path(path).stat().st_size
    log(f"  Uploading {sz/1024/1024:.0f}MB...")
    with open(path,"rb") as f:
        up = requests.put(url,headers={"Content-Length":str(sz),"Content-Type":"video/mp4"},
                         data=f,timeout=2400)
    if up.status_code in [200,201]:
        return f"https://www.youtube.com/watch?v={up.json().get('id')}"
    raise Exception(f"Upload {up.status_code}")

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

    # Stage 3: Human voice audio
    audio_path, duration, audio_sz, voice_used = run_stage3_audio(
        script_clean, voice, niche["name"])
    tg(f"Stage 3: {voice_used} | {duration/60:.1f}min")

    # Stage 4: Animation (NO subtitles on main)
    log("\n"+"="*65)
    log("  STAGE 4: Rendering Animation")
    log("="*65)
    video_path = render_and_encode(style_name, scenes, audio_path, duration)
    tg(f"Stage 4: 1080p animated | Style: {style_name}\nUploading...")

    # Upload main video
    description = (f"Episode {episode} of {niche['series']}.\n{topic}\n\n"
                   f"Every case. Every document. Every piece of evidence — animated.\n\n"
                   f"Subscribe to The Evidence Room.")
    try:
        yt_url = upload_yt(video_path, title_str, description, tags, is_short=False)
        log(f"  Main: {yt_url}")
    except Exception as e:
        tg(f"Evidence Room Upload FAILED\n{str(e)[:200]}"); sys.exit(1)

    # 2 Shorts WITH subtitles
    shorts = []
    for stype in ["teaser","recap"]:
        try:
            sp = make_short_with_subs(video_path, script_clean, stype, duration)
            if sp:
                su = upload_yt(sp, f"{title_str[:46]} — {stype.upper()}", description, tags, is_short=True)
                shorts.append(f"Short {stype}: {su}")
                log(f"  {shorts[-1]}")
        except Exception as e: log(f"  Short {stype} err: {e}")

    cleanup()

    # Update state
    state["last_style"] = style_name
    state["last_niche"]  = niche["name"]
    state["last_voice"]  = voice_used
    state["last_title"]  = title_str
    state["last_url"]    = yt_url
    save_state(state)

    dec = "APPROVED" if decision=="approved" else "AUTO-APPROVED"
    ev  = int(5000*0.9)
    er  = round((ev/1000)*niche["rpm"],2)
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

if __name__ == "__main__":
    main()
