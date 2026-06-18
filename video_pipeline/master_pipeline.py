#!/usr/bin/env python3
"""
DEEPDIVE EMPIRE — MASTER PIPELINE v6.0
=======================================
NICHE REBUILD: Horror / Dark / Deception / Seduction / Psychological
These are the niches that make people watch back-to-back without checking the time.

NICHES (all chosen for maximum addiction + high RPM):
1. dark_horror       — Real horror stories that happened to real people. $13 RPM
2. seduction_dark    — Manipulation seduction and obsession. $14 RPM
3. psychological_trap — The documented methods people use to trap others. $12 RPM
4. supernatural_real — Real unexplained events with documented evidence. $11 RPM
5. obsession_dark    — Stalking possession and dark fixation. $13 RPM

WHY THESE NICHES:
- Horror + psychology content has the highest watch time on YouTube
- Viewers watch entire playlists at 2AM unable to stop
- These niches have almost zero quality competition at this level
- RPM is strong because audience is 18-35 educated professionals
- Suggested content algorithm loves dark storytelling — infinite loop potential

ALL REQUIREMENTS:
✅ 13-attempt system (8 fresh + 5 archive)
✅ Quality minimum 7.3 | Final floor 6.9
✅ 20 human neural voices (10 US + 10 GB)
✅ Voice quality checker — auto-switches robotic
✅ 4-trigger thumbnail system
✅ NO subtitles on main video
✅ Subtitles on Shorts ONLY with audio sync
✅ 2 Shorts per video (teaser 10% + recap 67%)
✅ Approval gate BEFORE video (30-min)
✅ Telegram + Gmail dual notification
✅ Startup Telegram test
✅ Viral intelligence engine
✅ Fresh topic per attempt
✅ Archive fallback attempts 9-13
✅ Pixabay dark background
✅ Series watermark
✅ Voice + niche memory
✅ Makeup video logic
✅ Cross-promotion
✅ Auto-cleanup
✅ Weekly tracking
✅ Gemini-only for scripts (Groq for small requests)
✅ Node.js 24 compatible workflow
"""

import os, sys, json, re, time, random, datetime, asyncio
import subprocess, shutil, requests, smtplib
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from groq import Groq

# ── CREDENTIALS ──────────────────────────────────────────────
GROQ_KEY      = os.environ["GROQ_API_KEY"]
GEMINI_KEY    = os.environ["GEMINI_API_KEY"]
PIXABAY_KEY   = os.environ["PIXABAY_KEY"]
YT_CLIENT_ID  = os.environ["YOUTUBE_CLIENT_ID"]
YT_CLIENT_SEC = os.environ["YOUTUBE_CLIENT_SECRET"]
YT_REFRESH    = os.environ["YOUTUBE_REFRESH_TOKEN"]
TG_TOKEN      = os.environ["TELEGRAM_TOKEN"]
TG_CHAT       = os.environ["TELEGRAM_CHAT_ID"]
IS_MAKEUP     = os.environ.get("IS_MAKEUP","false").lower() == "true"

groq_client   = Groq(api_key=GROQ_KEY)
GEMINI_URL    = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
GEMINI_15_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
WORK_DIR      = Path("/tmp/deepdive")
WORK_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE    = WORK_DIR / "state.json"
INTEL_FILE    = WORK_DIR / "viral_intel.json"

MIN_WORDS  = 2200
MAX_WORDS  = 2600
MIN_GATE   = 7.3
FINAL_GATE = 6.9

# ════════════════════════════════════════════════════════════
# 20 HUMAN NEURAL VOICES — 10 US + 10 GB
# ════════════════════════════════════════════════════════════
US_VOICES = [
    "en-US-AndrewNeural",       # Warm authoritative — BEST for horror storytelling
    "en-US-BrianNeural",        # Deep commanding — BEST for dark psychology
    "en-US-ChristopherNeural",  # Serious documentary
    "en-US-DavisNeural",        # Dark dramatic deep — BEST for horror
    "en-US-EricNeural",         # Professional measured
    "en-US-GuyNeural",          # Commanding serious
    "en-US-JasonNeural",        # Calm deliberate
    "en-US-RogerNeural",        # Energetic authoritative
    "en-US-SteffanNeural",      # Professional clear
    "en-US-TonyNeural",         # Confident expressive
]
GB_VOICES = [
    "en-GB-RyanNeural",         # BBC gravitas — BEST overall
    "en-GB-ThomasNeural",       # Cold measured cinematic
    "en-GB-ElliotNeural",       # Deep calm investigative
    "en-GB-NoahNeural",         # Measured dark deliberate
    "en-GB-OliverNeural",       # Professional authoritative
    "en-GB-EthanNeural",        # Warm natural storytelling
    "en-GB-SoniaNeural",        # Sharp devastating (F)
    "en-GB-LibbyNeural",        # Natural warm (F)
    "en-GB-AbbiNeural",         # Clear professional (F)
    "en-GB-HollieNeural",       # Sharp professional (F)
]
ALL_VOICES     = US_VOICES + GB_VOICES
ROBOTIC_VOICES = ["en-US-AriaNeural","en-US-AnaNeural"]

NICHE_VOICES = {
    "dark_horror":        ["en-US-DavisNeural","en-GB-RyanNeural","en-US-AndrewNeural","en-GB-ElliotNeural","en-US-BrianNeural"],
    "seduction_dark":     ["en-GB-RyanNeural","en-US-AndrewNeural","en-GB-ThomasNeural","en-US-DavisNeural","en-GB-ElliotNeural"],
    "psychological_trap": ["en-US-BrianNeural","en-GB-ThomasNeural","en-US-ChristopherNeural","en-GB-NoahNeural","en-US-DavisNeural"],
    "supernatural_real":  ["en-GB-RyanNeural","en-US-DavisNeural","en-GB-ElliotNeural","en-US-AndrewNeural","en-GB-NoahNeural"],
    "obsession_dark":     ["en-US-AndrewNeural","en-GB-RyanNeural","en-US-DavisNeural","en-GB-ThomasNeural","en-US-BrianNeural"],
}

# ── NICHES ────────────────────────────────────────────────────
DAY_NICHE = {
    0: "dark_horror",
    1: "seduction_dark",
    2: "psychological_trap",
    3: "supernatural_real",
    4: "obsession_dark",
}

NICHES = [
    {
        "name": "dark_horror", "rpm": 13.00,
        "series": "Dark Hours", "watermark": "DARK HOURS",
        "dread_triggers": ["proximity","normality","invisibility","cost"],
        "viral_search": "real horror story documentary dark terrifying true",
        "archive_search": "most terrifying real horror story viral documentary 2022 2023",
        "thumbnail_triggers": ["IT CAME BACK","STILL THERE","NEVER LEFT","THEY SAW IT"],
        "seed_topics": [
            "A family moved into a house where something had been living in the walls for 11 years before they arrived",
            "A nurse documented what she witnessed during night shifts over 6 years that nobody believed until a camera proved it",
            "A hiker survived something in the mountains in 2019 that search and rescue teams still cannot explain",
            "A woman began receiving messages from her own phone number 3 months after her phone was destroyed",
            "An entire small town reported the same experience on the same night in 2021 and authorities sealed the records",
            "A sleep researcher recorded 847 nights of footage and found the same figure appearing in 23 percent of them",
        ],
    },
    {
        "name": "seduction_dark", "rpm": 14.00,
        "series": "The Dark Seduction Files", "watermark": "DARK SEDUCTION FILES",
        "dread_triggers": ["proximity","normality","complicity","reversal"],
        "viral_search": "dark seduction manipulation obsession real story documentary",
        "archive_search": "dark seduction manipulation real story viral documentary 2022 2023",
        "thumbnail_triggers": ["YOU WANTED IT","THEY ALL DO","NOBODY RESISTS","PERFECTLY PLANNED"],
        "seed_topics": [
            "A person used a documented 14-step system to make someone fall completely in love and then destroy them",
            "A charismatic figure seduced and financially destroyed 23 people over 8 years using the same script every time",
            "A relationship that began as a chance encounter was revealed to have been planned 3 years in advance",
            "How one person made 4 different people believe they were each the only one for 6 consecutive years",
            "A cult leader who used documented seduction psychology to make educated adults give up everything in 90 days",
            "The documented playbook a manipulator used that made victims defend their abuser to investigators",
        ],
    },
    {
        "name": "psychological_trap", "rpm": 12.00,
        "series": "The Trap", "watermark": "THE TRAP",
        "dread_triggers": ["proximity","competence","normality","complicity"],
        "viral_search": "psychological manipulation trap dark true story exposed documentary",
        "archive_search": "psychological trap manipulation exposed real story viral 2022 2023",
        "thumbnail_triggers": ["YOU ARE TRAPPED","ALREADY DONE","TOO LATE NOW","PERFECTLY SET"],
        "seed_topics": [
            "The documented 9-stage process one person used to make their target completely financially dependent",
            "A psychological trap that used social media to make the victim isolate themselves over 18 months",
            "How a gaslighting campaign made a forensic psychologist temporarily doubt her own professional judgment",
            "The workplace psychological trap that destroyed 6 careers while the perpetrator was promoted 3 times",
            "A documented case where an entire family was manipulated into cutting off one member using zero obvious force",
            "The psychological method that made victims believe they were the ones causing harm for 4 years",
        ],
    },
    {
        "name": "supernatural_real", "rpm": 11.50,
        "series": "Evidence Files", "watermark": "EVIDENCE FILES",
        "dread_triggers": ["proximity","normality","detail","invisibility"],
        "viral_search": "real supernatural documented evidence unexplained events true story",
        "archive_search": "documented supernatural unexplained events real evidence viral 2022 2023",
        "thumbnail_triggers": ["OFFICIALLY UNEXPLAINED","STILL NO ANSWER","THEY FILMED IT","RECORDS SEALED"],
        "seed_topics": [
            "A 2019 incident documented by 14 independent witnesses that government agencies classified within 72 hours",
            "A building where every occupant over 40 years reported the same auditory experience that instruments confirmed",
            "A medical case from 2021 where a patient described in precise detail an event they could not have witnessed",
            "Physical evidence collected in 1987 that was finally analyzed in 2023 and produced results with no explanation",
            "A documented mass experience in a school in 2020 where 67 students simultaneously reported the same thing",
            "A location where magnetic instruments and cameras produce consistent anomalies that scientists cannot account for",
        ],
    },
    {
        "name": "obsession_dark", "rpm": 13.00,
        "series": "Consumed", "watermark": "CONSUMED",
        "dread_triggers": ["proximity","duration","normality","cost"],
        "viral_search": "dark obsession stalking fixation real story documentary true crime",
        "archive_search": "dark obsession fixation real story viral documentary 2022 2023",
        "thumbnail_triggers": ["ALWAYS WATCHING","NEVER STOPPED","12 YEARS LATER","STILL WATCHING"],
        "seed_topics": [
            "A person documented 4,380 consecutive days of obsessive behavior before anyone realized what was happening",
            "An obsession that began as admiration and became a 7-year campaign that destroyed everything the subject built",
            "A stalker who embedded themselves in the victims life as a trusted friend for 3 years before being discovered",
            "How a completely ordinary fixation transformed into something that required 3 restraining orders and 2 relocations",
            "A documented case where the subject did not realize they were being observed for 9 years until a phone was found",
            "An obsession that crossed 4 countries over 11 years and was only stopped when the obsessed person died",
        ],
    },
]

DREAD_TRIGGERS = {
    "proximity":     "Make the audience feel this is happening near them right now. 'Someone near you tonight.' 'The house next to yours.' Make it personal and immediate.",
    "duration":      "The exact duration stated obsessively. Not 7 years — 2,555 nights. Not a decade — 3,650 mornings of waking up and continuing.",
    "scale":         "Numbers that overwhelm before they can be processed. Make each one a specific person with a specific life.",
    "institutional": "The thing that should have stopped it was the thing that enabled it. The system. The family. The organization.",
    "invisibility":  "The most terrifying thing looks completely normal. It is ordinary. It is unremarkable. It is the person next to you.",
    "normality":     "The horror and the ordinary life existed simultaneously. In the same house. On the same evenings. At the same dinner table.",
    "complicity":    "The audience would have done exactly the same thing as the people who failed to stop it. Make them uncomfortable with that.",
    "competence":    "The cold intelligence of it. The patience. The planning across years. The architecture of sustained darkness.",
    "detail":        "One specific small detail that proves everything and cannot be explained away. Make it concrete and undeniable.",
    "reversal":      "The moment when everything the audience understood was wrong. The floor drops. Everything was always something else.",
    "cost":          "What was permanently destroyed. Not inconvenienced — destroyed. Name what can never be recovered.",
    "repetition":    "Every day. Every night. Without stopping. The mechanical relentless inhuman repetition of it.",
}

BG_KEYWORDS = {
    "dark_horror":        ["dark horror shadow night", "horror darkness abstract"],
    "seduction_dark":     ["dark sensual shadow night", "mysterious dark elegant"],
    "psychological_trap": ["dark corridor trap shadow", "mind darkness psychological"],
    "supernatural_real":  ["dark mysterious fog night", "supernatural darkness abstract"],
    "obsession_dark":     ["dark shadow watching night", "obsession darkness cinema"],
}


# ════════════════════════════════════════════════════════════
# UTILITIES
# ════════════════════════════════════════════════════════════
def log(msg): print(msg, flush=True)

def tg(msg):
    chunks = [msg[i:i+4000] for i in range(0, len(msg), 4000)]
    for chunk in chunks:
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                json={"chat_id":TG_CHAT,"text":chunk,"parse_mode":"HTML"},
                timeout=15)
            if r.status_code != 200:
                log(f"  TG {r.status_code}: {r.text[:60]}")
            time.sleep(0.5)
        except Exception as e:
            log(f"  TG err: {str(e)[:50]}")

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
    if not pwd: log("  Gmail: no secret"); return False
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
    return {"last_niche":"","last_voice":"","makeup_pending":False,
            "makeup_niche":"","last_title":"","last_url":"","weekly_videos":[]}

def save_state(s): STATE_FILE.write_text(json.dumps(s,indent=2))

def load_intel():
    if INTEL_FILE.exists():
        try: return json.loads(INTEL_FILE.read_text())
        except: pass
    return {}

def save_intel(d): INTEL_FILE.write_text(json.dumps(d,indent=2))

def call_gemini(prompt, temp=0.88, tokens=8000, model="2.0"):
    url = GEMINI_URL if model=="2.0" else GEMINI_15_URL
    for attempt in range(5):
        try:
            r = requests.post(f"{url}?key={GEMINI_KEY}",
                headers={"Content-Type":"application/json"},
                json={
                    "contents":[{"parts":[{"text":prompt}]}],
                    "generationConfig":{"temperature":temp,"maxOutputTokens":min(tokens,8192),"topP":0.95},
                    "safetySettings":[{"category":c,"threshold":"BLOCK_NONE"} for c in
                        ["HARM_CATEGORY_HARASSMENT","HARM_CATEGORY_HATE_SPEECH",
                         "HARM_CATEGORY_SEXUALLY_EXPLICIT","HARM_CATEGORY_DANGEROUS_CONTENT"]]
                }, timeout=90)
            if r.status_code == 200:
                c = r.json().get("candidates",[])
                if c:
                    text = c[0]["content"]["parts"][0]["text"]
                    if text and len(text.strip()) > 100:
                        return text
                    log(f"  Gemini {model}: empty — retrying")
            elif r.status_code == 429:
                wait = 60*(attempt+1)
                log(f"  Gemini {model} 429 — wait {wait}s")
                time.sleep(wait)
            elif r.status_code == 400:
                err = r.json().get("error",{}).get("message","unknown")[:120]
                log(f"  Gemini {model} 400: {err}")
                if "API_KEY_INVALID" in err or "API key not valid" in err:
                    tg("CRITICAL: Gemini API key is invalid. Update GEMINI_API_KEY in GitHub Secrets at aistudio.google.com")
                    sys.exit(1)
                if len(prompt) > 6000:
                    prompt = prompt[:6000] + " WRITE THE NARRATION NOW."
                time.sleep(5)
            else:
                log(f"  Gemini {model} {r.status_code}: {r.text[:80]}")
                time.sleep(15)
        except Exception as e:
            log(f"  Gemini {model} err: {str(e)[:60]}")
            time.sleep(15)
    raise Exception(f"Gemini {model} failed all 5 attempts")

def call_groq(prompt, temp=0.7, tokens=2000):
    for attempt in range(3):
        try:
            r = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role":"user","content":prompt}],
                temperature=temp, max_tokens=min(tokens,2000))
            return r.choices[0].message.content
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                log(f"  Groq 429 — wait 60s")
                time.sleep(60)
            else: raise
    raise Exception("Groq rate limited")

def ai(prompt, temp=0.88, tokens=8000, prefer="gemini"):
    if tokens > 1500:
        # Script generation — Gemini ONLY (Groq cannot output 2200 words)
        try: return call_gemini(prompt,temp,tokens,"2.0")
        except: return call_gemini(prompt,temp,tokens,"1.5")
    else:
        # Small requests — Groq first (faster), Gemini fallback
        if prefer != "gemini":
            try: return call_groq(prompt,temp,min(tokens,2000))
            except: return call_gemini(prompt,temp,min(tokens,4000),"2.0")
        else:
            try: return call_gemini(prompt,temp,min(tokens,4000),"2.0")
            except: return call_groq(prompt,temp,min(tokens,2000))

def strip_md(text):
    for _ in range(2):
        text = re.sub(r'^#{1,6}\s+','',text,flags=re.MULTILINE)
        text = re.sub(r'\*{1,3}([^*\n]+)\*{1,3}',r'\1',text)
        text = re.sub(r'_{1,3}([^_\n]+)_{1,3}',r'\1',text)
        text = re.sub(r'^[-*_]{3,}\s*$','',text,flags=re.MULTILINE)
        text = re.sub(r'^\s*[-*+•·▪]\s+','',text,flags=re.MULTILINE)
        text = re.sub(r'^\s*\d+[.)]\s+','',text,flags=re.MULTILINE)
        text = re.sub(r'^>\s*','',text,flags=re.MULTILINE)
        text = re.sub(r'`+[^`]*`+','',text)
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)',r'\1',text)
        text = re.sub(r'\[[^\]]*\]','',text)
        text = re.sub(r'https?://\S+','',text)
        text = re.sub(r'<[^>]+>','',text)
        text = re.sub(r'\([^)]*(?:narrator|music|sfx|pause|cut|scene|beat|fade)[^)]*\)','',text,flags=re.IGNORECASE)
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
    prompt = f"""Analyze TOP 20 viral YouTube videos (2M+ views) in "{niche['viral_search']}" niche.
Return ONLY valid JSON:
{{"top_hook_formulas":["Hook 1 used in highest watch-time videos","Hook 2","Hook 3"],
"winning_title_patterns":["Pattern 1","Pattern 2","Pattern 3"],
"thumbnail_text_examples":["3 WORDS 1","3 WORDS 2","3 WORDS 3","3 WORDS 4","3 WORDS 5"],
"emotional_arc":"One sentence: exact emotional journey in top performers",
"retention_hooks":["30pct hook","60pct hook","80pct hook"],
"niche_specific_power_words":["word1","word2","word3","word4","word5","word6","word7"],
"what_makes_videos_viral":"One sentence: single most important factor",
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
        "top_hook_formulas":["Nobody believed it until they saw the footage.","It happened at 3:17 AM. Every single time.","What was found in that room changed everything."],
        "winning_title_patterns":["The [THING] That [HAPPENED] For [DURATION] While [NORMAL]","Nobody Believed [SUBJECT] Until [EVIDENCE] Proved [HORROR]"],
        "thumbnail_text_examples": niche["thumbnail_triggers"],
        "emotional_arc":"Curiosity then dread then terror then revelation then inability to unsee",
        "retention_hooks":["What happened next has never been officially explained","The recording you are about to hear was never meant to exist","The last piece of evidence changes everything before it"],
        "niche_specific_power_words":["nobody","witnessed","documented","still","returned","impossible","proven"],
        "what_makes_videos_viral":"Documented real events that resist rational explanation delivered with precision",
        "fresh_topic_ideas": niche["seed_topics"],
        "last_run": datetime.datetime.now().isoformat()
    }
    intel[name] = fallback; save_intel(intel); return fallback


# ════════════════════════════════════════════════════════════
# FRESH TOPIC ENGINE
# ════════════════════════════════════════════════════════════
def get_fresh_topic(niche, attempt, intel, used_topics):
    is_archive = attempt > 8
    if not is_archive:
        fresh = intel.get("fresh_topic_ideas", niche["seed_topics"])
        unused = [t for t in fresh if t not in used_topics]
        if unused:
            chosen = unused[0] if attempt <= 3 else random.choice(unused)
            log(f"  Topic: {chosen[:75]}")
            return chosen
        prompt = f"""Generate 6 original compelling topics for "{niche['series']}" YouTube series.
Niche: {niche['name']} | Search: {niche['viral_search']}
Already used: {[t[:40] for t in used_topics[:4]]}
Make each specific, emotionally gripping, different from used list.
Return ONLY JSON array: ["Topic 1","Topic 2","Topic 3","Topic 4","Topic 5","Topic 6"]"""
        try:
            text = ai(prompt,temp=0.85,tokens=400,prefer="groq")
            text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]','',re.sub(r'```json|```','',text).strip())
            m = re.search(r'\[[\s\S]*?\]',text)
            if m:
                topics = json.loads(m.group())
                unused = [t for t in topics if t not in used_topics]
                if unused: return random.choice(unused)
        except Exception as e: log(f"  Topic gen err: {e}")
    else:
        prompt = f"""Find 6 documented real stories from 2022-2024 in "{niche['name']}" niche that went viral.
Focus: {niche['archive_search']}
Not: {[t[:40] for t in used_topics[:4]]}
Return ONLY JSON array: ["Story 1","Story 2","Story 3","Story 4","Story 5","Story 6"]"""
        try:
            text = ai(prompt,temp=0.8,tokens=400,prefer="groq")
            text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]','',re.sub(r'```json|```','',text).strip())
            m = re.search(r'\[[\s\S]*?\]',text)
            if m:
                topics = json.loads(m.group())
                unused = [t for t in topics if t not in used_topics]
                if unused: return random.choice(unused)
        except Exception as e: log(f"  Archive err: {e}")
    unused_seeds = [t for t in niche["seed_topics"] if t not in used_topics]
    return random.choice(unused_seeds) if unused_seeds else niche["seed_topics"][0]


# ════════════════════════════════════════════════════════════
# 5-TITLE CTR SCORING
# ════════════════════════════════════════════════════════════
def score_title_ctr(title):
    s = 5.0; tl = title.lower(); n = len(title)
    if 50<=n<=65: s+=1.5
    elif 45<=n<=70: s+=0.8
    else: s-=1.0
    power = ["nobody","witnessed","returned","still","documented","proven","impossible","sealed","watched","alone","real","found","never"]
    s += min(sum(1 for w in power if w in tl)*0.4, 2.0)
    if re.search(r'\d+\s*(year|night|day|hour|month|time)',tl): s+=1.0
    if any(w in tl for w in ["nobody believed","still unexplained","officially sealed","still watching","never left","came back"]): s+=0.8
    return min(round(s,1),10.0)

def generate_and_score_titles(niche, topic, intel, episode):
    patterns = intel.get("winning_title_patterns",[])
    power    = intel.get("niche_specific_power_words",["nobody","witnessed","real"])
    prompt = f"""Generate 5 YouTube title variants for this dark story video.
NICHE: {niche['name']} | SERIES: {niche['series']} Ep{episode}
TOPIC: {topic[:150]}
PATTERNS: {chr(10).join(patterns[:3])}
POWER WORDS: {', '.join(power)}
Rules: 50-65 chars. Maximum dread and curiosity. Specific. Documentary not sensational.
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
    return f"{niche['series']}: The Story That Changes Everything", [(f"{niche['series']}: The Story",6.0)]

def generate_thumbnail_text(niche, topic, intel):
    examples = intel.get("thumbnail_text_examples",niche["thumbnail_triggers"])
    prompt = f"""Generate the most psychologically compelling 3-word thumbnail text for a dark story video.
NICHE: {niche['name']} | TOPIC: {topic[:100]}
TOP EXAMPLES: {', '.join(examples)}
USE ALL 4 TRIGGERS: curiosity gap + dread signal + identity threat + pattern interrupt
Rules: EXACTLY 3 words ALL CAPS. Maximum psychological impact. Never generic.
Return ONLY 3 words."""
    try:
        result = ai(prompt,temp=0.85,tokens=15,prefer="groq")
        result = re.sub(r'[^A-Z\s]','',result.upper()).strip()
        words  = result.split()[:3]
        if len(words)==3: return ' '.join(words)
    except: pass
    return random.choice(niche["thumbnail_triggers"])


# ════════════════════════════════════════════════════════════
# SCRIPT GENERATION — DARK ADDICTIVE STORYTELLING
# Built specifically to make viewers watch back-to-back
# ════════════════════════════════════════════════════════════
def get_niche_and_voice(state):
    if IS_MAKEUP and state.get("makeup_pending") and state.get("makeup_niche"):
        n = next((x for x in NICHES if x["name"]==state["makeup_niche"]),None)
        if n: return n, get_best_voice(n["name"],state)
    name = DAY_NICHE.get(datetime.datetime.now().weekday(),"dark_horror")
    if name == state.get("last_niche",""):
        candidates = sorted([x for x in NICHES if x["name"]!=name],key=lambda x:x["rpm"],reverse=True)
        name = candidates[0]["name"]
    niche = next(x for x in NICHES if x["name"]==name)
    return niche, get_best_voice(name,state)

def get_best_voice(niche_name, state):
    preferred = NICHE_VOICES.get(niche_name,GB_VOICES[:5])
    available = [v for v in preferred if v!=state.get("last_voice","")]
    pool      = available or preferred
    return pool[datetime.datetime.now().timetuple().tm_yday % len(pool)]

def build_dread_prompt(niche):
    return "\n".join(
        f"DREAD {t.upper()}: {DREAD_TRIGGERS[t][:80]}"
        for t in niche.get("dread_triggers",[])[:4]
        if t in DREAD_TRIGGERS)

def generate_script(niche, topic, episode, attempt, prev_title, intel):
    temp      = min(0.82+attempt*0.012, 0.94)
    darkness  = min(40+attempt*6, 96)
    cross     = f'\nNaturally reference previous episode: "{prev_title}" in your closing.' if prev_title else ""
    dread     = build_dread_prompt(niche)
    hooks     = intel.get("top_hook_formulas",["Nobody believed it until they saw the footage."])
    retention = intel.get("retention_hooks",["What happened next has never been officially explained"])
    power     = intel.get("niche_specific_power_words",["nobody","witnessed","documented","still"])
    viral     = intel.get("what_makes_videos_viral","Documented real events delivered with precision")
    arc       = intel.get("emotional_arc","Curiosity then dread then terror then revelation")

    prompt = f"""You are the greatest dark storytelling narrator alive for YouTube documentaries.
Write Episode {episode} of "{niche['series']}" — a channel built to make people watch all night.
Story: {topic}
Darkness: {darkness}% {cross}

PROVEN HOOKS: {hooks[0]}
VIRAL FACTOR: {viral}
EMOTIONAL ARC: {arc}
POWER WORDS: {', '.join(power[:7])}
RETENTION HOOK at 30pct: {retention[0]}
RETENTION HOOK at 60pct: {retention[1] if len(retention)>1 else "Everything you understood about this is about to change"}
RETENTION HOOK at 80pct: {retention[2] if len(retention)>2 else "The final detail has never been publicly released until now"}

DREAD SYSTEM: {dread}

THE 10 LAWS — ALL MANDATORY:
1. ZERO markdown — no symbols of any kind
2. ZERO stage directions — no music pause cut narrator
3. ZERO AI filler — no moreover furthermore in conclusion it is worth noting
4. Pure spoken English — every word speakable naturally by a human
5. MAX 13 words per sentence — dread lives in short sentences
6. Every paragraph heavier and darker than the previous
7. Specific dates times exact numbers throughout — it must feel real and documented
8. EXACTLY {MIN_WORDS} to {MAX_WORDS} words
9. ZERO section labels — pure seamless narration
10. The listener must be physically unable to stop — every paragraph must earn the next one

STRUCTURE (one seamless narration, no labels):
HOOK (4 sentences): Most disturbing specific fact. One detail making it immediately worse. An exact number or time. The question that makes stopping impossible.
WORLD BEFORE (400-500w): Establish what was normal. Make the audience care. Plant 3 ordinary details that detonate later. Apply NORMALITY and INVISIBILITY triggers.
RISING DREAD (400-500w): First signs. Each dismissable alone. Together a pattern nobody named. Apply PROXIMITY and DURATION triggers.
[USE RETENTION HOOK 1]
THE DESCENT (600-700w): Full scale of what was really happening. Specific. Documented. Suffocating. Apply COMPETENCE and REPETITION triggers.
THE BREAK (200-250w): The exact moment everything collapsed. Who discovered it. What they saw.
[USE RETENTION HOOK 2]
THE TWIST (150-200w): One sentence that shatters everything. Reframe every planted detail. Apply REVERSAL trigger.
THE COST (350-400w): Specific named people. Specific permanent losses. Apply COST trigger.
[USE RETENTION HOOK 3]
THE AFTERMATH (200-250w): What followed. What failed to follow. What continues right now. Apply INSTITUTIONAL and COMPLICITY triggers.
THE RECKONING (150-200w): The hard truth with no comfort and no resolution.
THE CLOSE (100-150w): Haunting line to next episode. Natural subscribe call to {niche['series']}.

WRITE {MIN_WORDS}-{MAX_WORDS} WORDS OF PURE NARRATION. NO LABELS. NO PREAMBLE. START IMMEDIATELY."""

    raw   = ai(prompt,temp=temp,tokens=8000,prefer="gemini")
    clean = strip_md(strip_md(raw))
    wc    = len(clean.split())

    for exp in range(2):
        if wc >= MIN_WORDS: break
        deficit = MIN_WORDS - wc
        log(f"  {wc}w — expanding {exp+1}...")
        expand = f"""This narration is {wc} words. Needs {MIN_WORDS}. Add {deficit} words.
Expand: 1) THE COST — 2 more specific people with permanent losses 2) THE DESCENT — 3 more specific documented details 3) THE AFTERMATH — more about what continues now.
Zero markdown. Pure spoken English. Max 13 words per sentence. ADD only — no repetition.
Return COMPLETE script.
SCRIPT: {clean}"""
        try:
            raw2   = ai(expand,temp=0.82,tokens=8000,prefer="gemini")
            clean2 = strip_md(strip_md(raw2))
            if len(clean2.split())>wc:
                clean=clean2; wc=len(clean.split())
                log(f"  Expanded to {wc}w")
        except Exception as e:
            log(f"  Expand err: {e}"); break

    violations = len(re.findall(r'[#*_`\[\]{}<>\\]',clean))
    return {"clean":clean,"words":wc,"violations":violations,"_topic":topic}

def score_script(s):
    issues,score = [],5.0
    w,md = s["words"],s["violations"]
    if w>=MIN_WORDS:    score+=2.8
    elif w>=1800:       score+=0.8; issues.append(f"{w}w short")
    elif w>=1200:       score-=1.5; issues.append(f"SHORT:{w}w")
    else:               score-=4.0; issues.append(f"FATAL:{w}w")
    if md==0:           score+=2.2
    elif md<=2:         score+=0.8; issues.append(f"{md}md")
    else:               score-=1.5; issues.append(f"FATAL:{md}md")
    sents=[x for x in re.split(r'(?<=[.!?])\s+',s["clean"]) if len(x.split())>2]
    if sents:
        avg=sum(len(x.split()) for x in sents)/len(sents)
        long_pct=sum(1 for x in sents if len(x.split())>13)/len(sents)
        if avg<=10:     score+=1.5
        elif avg<=12:   score+=1.0
        elif avg<=15:   score+=0.4
        else:           score-=0.5; issues.append(f"Avg{avg:.0f}w")
        if long_pct>0.3:score-=0.5; issues.append(f"{long_pct:.0%}long")
    hook=s["clean"][:350].lower()
    pw=["nobody","witnessed","returned","still","documented","impossible","proven","sealed","watched","real","found","never","alone"]
    hs=sum(1 for w2 in pw if w2 in hook)
    if hs>=5:           score+=1.2
    elif hs>=3:         score+=0.7
    else:               score-=0.3; issues.append("WeakHook")
    ai_p=["moreover","furthermore","it is worth noting","in conclusion","interestingly","it should be noted","this highlights"]
    ai_c=sum(1 for p in ai_p if p in s["clean"].lower())
    if ai_c>0:          score-=ai_c*0.3; issues.append(f"{ai_c}AIphrases")
    if "subscribe" in s["clean"][-400:].lower(): score+=0.2
    return min(round(score,1),10.0), issues

def generate_metadata(niche, script, episode, best_title, thumbnail_text, prev_title, prev_url):
    cross = f'Include: "Previous episode: {prev_title} — {prev_url}"' if prev_title else ""
    prompt = f"""YouTube metadata for Episode {episode} of {niche['series']}.
Topic: {script['_topic'][:180]}. Title: {best_title}. {cross}
Return ONLY clean ASCII JSON:
title: {best_title}
description: 400 words, first 2 lines standalone hooks, 5 chapter timestamps, subscribe CTA
tags: array of 12 strings
thumbnail_text: {thumbnail_text}
chapters: array of 5 objects with time and title
category: "22" """
    try:
        text = ai(prompt,temp=0.65,tokens=1000,prefer="groq")
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]','',re.sub(r'```json|```','',text).strip())
        m = re.search(r'\{[\s\S]*\}',text)
        if m:
            meta = json.loads(re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]','',m.group()))
            meta["title"]          = best_title
            meta["thumbnail_text"] = thumbnail_text
            return meta
    except Exception as e: log(f"  Meta err: {e}")
    return {
        "title":best_title,
        "description":f"Episode {episode}. {script['_topic'][:200]}. Subscribe to {niche['series']}.",
        "tags":[niche["name"],"horror","dark","documentary","true","story","psychological","real","unexplained","obsession","dark truth","mystery"],
        "thumbnail_text":thumbnail_text,
        "chapters":[{"time":"0:00","title":"The Opening"},{"time":"3:30","title":"What Was Real"},
                    {"time":"7:00","title":"The Descent"},{"time":"11:00","title":"The Twist"},{"time":"14:30","title":"What Remains"}],
        "category":"22"
    }


# ════════════════════════════════════════════════════════════
# STAGE 1: 13-ATTEMPT ENGINE
# ════════════════════════════════════════════════════════════
def run_stage1(state):
    log("\n"+"="*65)
    log("  STAGE 1: 13-Attempt Dark Story Engine")
    log(f"  Quality: {MIN_GATE} min | {FINAL_GATE} floor")
    log("="*65)
    niche,voice = get_niche_and_voice(state)
    episode      = (datetime.datetime.now().timetuple().tm_yday//max(1,len(NICHES)))+1
    prev_title   = state.get("last_title","")
    prev_url     = state.get("last_url","")
    log(f"\nNiche: {niche['name']} | ${niche['rpm']} RPM | Ep{episode}")
    log(f"Voice: {voice}")
    log(f"IS_MAKEUP: {IS_MAKEUP}\n")
    log("Loading viral intelligence...")
    intel          = run_viral_intelligence(niche)
    used_topics    = []
    gate           = MIN_GATE
    best_score     = 0.0
    best_script    = best_meta = None
    best_title_str = f"{niche['series']}: The Story Nobody Was Supposed to Find"
    title_scores   = [(best_title_str,6.0)]
    thumbnail_text = generate_thumbnail_text(niche,niche["seed_topics"][0],intel)

    for attempt in range(1,14):
        if attempt==13:       gate=FINAL_GATE
        elif attempt>=10:     gate=7.0
        elif attempt>=7:      gate=7.2
        topic = get_fresh_topic(niche,attempt,intel,used_topics)
        used_topics.append(topic)
        if attempt in [1,5,9]:
            thumbnail_text     = generate_thumbnail_text(niche,topic,intel)
            best_title_str,title_scores = generate_and_score_titles(niche,topic,intel,episode)
            log(f"Thumbnail: {thumbnail_text}")
        log(f"\nAttempt {attempt}/13 (gate:{gate}) {'[ARCHIVE]' if attempt>8 else '[FRESH]'}...")
        log(f"Topic: {topic[:80]}")
        try:
            script        = generate_script(niche,topic,episode,attempt,prev_title,intel)
            score,issues  = score_script(script)
            log(f"  {score}/10 {'OK' if score>=gate else 'BLOCKED'} | {script['words']}w | MD:{script['violations']}")
            if issues: log(f"  {' | '.join(issues[:3])}")
            if score>best_score:
                best_score  = score
                best_script = script
                best_meta   = generate_metadata(niche,script,episode,best_title_str,thumbnail_text,prev_title,prev_url)
            if score>=gate:
                log(f"\nAPPROVED: {score}/10 | Attempt {attempt}\n")
                return niche,topic,voice,episode,best_script,best_meta,score,thumbnail_text,intel,title_scores
            time.sleep(3)
        except Exception as e:
            log(f"  Err: {str(e)[:80]}")
            time.sleep(15)

    if best_script and best_score>=FINAL_GATE:
        log(f"\nUsing best: {best_score}/10 after 13 attempts")
        tg(f"Publishing with {best_score}/10 after 13 attempts.")
        return niche,used_topics[-1],voice,episode,best_script,best_meta,best_score,thumbnail_text,intel,title_scores

    state["makeup_pending"]=True; state["makeup_niche"]=niche["name"]; save_state(state)
    tg(f"Day Skipped\nBest: {best_score}/10 after 13 attempts\nNiche: {niche['name']}\nMakeup tomorrow.")
    sys.exit(0)


# ════════════════════════════════════════════════════════════
# STAGE 2: APPROVAL GATE — Telegram + Gmail
# ════════════════════════════════════════════════════════════
def run_stage2_approval(meta, niche, voice, script, thumbnail_text, title_scores):
    log("\n"+"="*65)
    log("  STAGE 2: Approval Gate")
    log("="*65)
    deadline     = datetime.datetime.now()+datetime.timedelta(minutes=30)
    deadline_str = deadline.strftime('%I:%M %p')
    top_titles   = "\n".join(f"  {s}/10: {t[:58]}" for t,s in title_scores[:3])
    preview      = script["clean"][:450].replace("<","").replace(">","")
    tg(f"APPROVAL NEEDED — {niche['series']}\n\n"
       f"Title: {meta['title']}\n\n"
       f"Niche: {niche['name']} | ${niche['rpm']} RPM\n"
       f"Voice: {voice} | Words: {script['words']}\n"
       f"Thumbnail: {thumbnail_text}\n\n"
       f"Auto at {deadline_str} | Reply APPROVE or REJECT")
    time.sleep(1)
    tg(f"CTR SCORES:\n{top_titles}\n\nPREVIEW:\n{preview}...")
    html = f"""<!DOCTYPE html><html><body style="background:#080810;color:#e0e0e0;font-family:Arial,sans-serif;padding:20px;">
<div style="max-width:660px;margin:0 auto;background:#0d0d18;border:1px solid #2a2a3a;border-radius:8px;overflow:hidden;">
<div style="background:#0a0a14;border-bottom:3px solid #8800cc;padding:20px 26px;">
  <div style="font-size:10px;color:#888;letter-spacing:3px">{niche['series'].upper()} — APPROVAL NEEDED</div>
  <div style="font-size:19px;font-weight:bold;color:#fff;margin-top:5px">{meta['title']}</div>
  <div style="font-size:11px;color:#8844cc;margin-top:5px">Auto at {deadline_str} — Reply APPROVE or REJECT</div>
</div>
<div style="padding:20px 26px;border-bottom:1px solid #2a2a3a;">
  <table style="width:100%;font-size:12px;border-collapse:collapse">
    <tr><td style="color:#666;padding:3px 0;width:110px">Niche</td><td>{niche['name']} — ${niche['rpm']} RPM</td></tr>
    <tr><td style="color:#666;padding:3px 0">Voice</td><td>{voice}</td></tr>
    <tr><td style="color:#666;padding:3px 0">Words</td><td>{script['words']} (~{script['words']//125:.0f} min)</td></tr>
    <tr><td style="color:#666;padding:3px 0">Thumbnail</td><td style="color:#8844cc;font-weight:bold;font-size:14px">{thumbnail_text}</td></tr>
  </table>
</div>
<div style="padding:18px 26px;border-bottom:1px solid #2a2a3a;">
  <div style="font-size:10px;color:#666;margin-bottom:8px">CTR SCORES</div>
  {"".join(f'<div style="padding:6px 10px;margin:3px 0;background:{"#1a1a2a" if i==0 else "#121218"};border-left:3px solid {"#8844cc" if i==0 else "#333"};"><span style="color:{"#aa66ff" if i==0 else "#666"};font-size:10px">{s}/10{"  WINNER" if i==0 else ""}</span><br><span style="color:#e0e0e0;font-size:12px">{t}</span></div>' for i,(t,s) in enumerate(title_scores[:5]))}
</div>
<div style="padding:18px 26px;">
  <div style="font-size:10px;color:#666;margin-bottom:8px">SCRIPT PREVIEW</div>
  <div style="background:#08080f;border:1px solid #1a1a2a;border-radius:4px;padding:14px;font-size:12px;line-height:1.7;color:#bbb;font-style:italic">{preview.replace(chr(10),'<br>')}...</div>
</div>
</div></body></html>"""
    send_gmail(f"[{niche['series']}] Approve: {meta['title'][:50]} — auto {deadline_str}",html)
    updates  = tg_updates()
    offset   = (max(u["update_id"] for u in updates)+1) if updates else 0
    reminded = set()
    while datetime.datetime.now()<deadline:
        time.sleep(30)
        for u in tg_updates(offset):
            offset = u["update_id"]+1
            txt = u.get("message",{}).get("text","").upper().strip()
            cid = str(u.get("message",{}).get("chat",{}).get("id",""))
            if cid==str(TG_CHAT):
                if any(w in txt for w in ["APPROVE","YES","GO","OK","UPLOAD"]):
                    tg("APPROVED. Generating now."); return "approved"
                if any(w in txt for w in ["REJECT","NO","SKIP","CANCEL"]):
                    tg("REJECTED. Makeup tomorrow."); return "rejected"
        mins=int((deadline-datetime.datetime.now()).total_seconds()/60)
        if 13<=mins<=17 and "15" not in reminded:
            reminded.add("15"); tg(f"15 min until auto-upload\n{meta['title']}\nReply APPROVE or REJECT")
        elif 3<=mins<=6 and "5" not in reminded:
            reminded.add("5"); tg("5 MIN — Reply APPROVE or REJECT NOW")
    tg("30 min expired — AUTO-APPROVED. Generating now.")
    return "auto_approved"


# ════════════════════════════════════════════════════════════
# STAGE 3: HUMAN VOICE AUDIO + QUALITY CHECK
# ════════════════════════════════════════════════════════════
async def _tts(text, voice_id, path):
    import edge_tts
    c = edge_tts.Communicate(text,voice_id,rate="-8%",pitch="+0Hz",volume="+8%")
    await c.save(path)

def check_audio_quality(mp3_path, dur_expected):
    try:
        sz = Path(mp3_path).stat().st_size
        if sz < dur_expected*8000: return False
        if sz < 80000: return False
        return True
    except: return False

def run_stage3_audio(script_clean, voice_id, niche_name):
    log("\n"+"="*65)
    log(f"  STAGE 3: Human Voice Audio — {voice_id}")
    log("="*65)
    wc           = len(script_clean.split())
    dur_expected = (wc/125.0)*60.0
    preferred    = NICHE_VOICES.get(niche_name,GB_VOICES[:5])
    voice_queue  = [voice_id]
    for v in preferred:
        if v not in voice_queue and v not in ROBOTIC_VOICES: voice_queue.append(v)
    for v in ALL_VOICES:
        if v not in voice_queue and v not in ROBOTIC_VOICES: voice_queue.append(v)
    for v in voice_queue[:8]:
        log(f"  Trying: {v}")
        mp3 = str(WORK_DIR/"audio.mp3")
        try:
            asyncio.run(_tts(script_clean,v,mp3))
            if not Path(mp3).exists(): continue
            if not check_audio_quality(mp3,dur_expected):
                log(f"  {v} quality fail — next"); continue
            sz  = Path(mp3).stat().st_size
            dur = dur_expected
            log(f"  ACCEPTED: {v} | {sz/1024/1024:.1f}MB | ~{dur/60:.1f}min")
            wav = str(WORK_DIR/"audio.wav")
            try:
                subprocess.run(["ffmpeg","-y","-i",mp3,"-acodec","pcm_s16le","-ar","24000","-ac","1",wav],
                               capture_output=True,timeout=300)
                if Path(wav).exists() and Path(wav).stat().st_size>100000:
                    return wav,dur,sz,v
            except: pass
            return mp3,dur,sz,v
        except Exception as e:
            log(f"  {v} err: {str(e)[:60]}"); time.sleep(3)
    tg("Stage 3 FAILED — all voices failed"); sys.exit(1)


# ════════════════════════════════════════════════════════════
# STAGE 4: VIDEO — NO SUBTITLES ON MAIN
# ════════════════════════════════════════════════════════════
def fetch_background(niche_name, duration):
    kws = BG_KEYWORDS.get(niche_name,["dark cinematic shadow"])
    for kw in kws:
        try:
            r = requests.get("https://pixabay.com/api/videos/",
                params={"key":PIXABAY_KEY,"q":kw,"per_page":10,"min_duration":30,"video_type":"film"},
                timeout=30)
            if r.status_code==200:
                hits=r.json().get("hits",[])
                if hits:
                    url  = random.choice(hits[:5])["videos"]["medium"]["url"]
                    path = str(WORK_DIR/"bg.mp4")
                    resp = requests.get(url,stream=True,timeout=120)
                    with open(path,"wb") as f:
                        for chunk in resp.iter_content(8192): f.write(chunk)
                    if Path(path).stat().st_size>100000:
                        log(f"  BG: {Path(path).stat().st_size/1024/1024:.1f}MB"); return path
        except Exception as e: log(f"  Pixabay: {e}")
    path=str(WORK_DIR/"bg.mp4")
    subprocess.run(["ffmpeg","-y","-f","lavfi","-i","color=c=0x03010A:s=1920x1080:r=30",
                   "-t",str(int(duration)+20),"-vf","noise=alls=20:allf=t+u,vignette=angle=PI/3",
                   "-c:v","libx264","-preset","fast","-crf","30",path],capture_output=True)
    log("  BG: dark fallback"); return path

def assemble_video(audio_path, bg_path, duration, watermark):
    out = str(WORK_DIR/"final.mp4")
    wm  = re.sub(r"[^a-zA-Z0-9 ]","",watermark)
    result = subprocess.run([
        "ffmpeg","-y","-stream_loop","-1","-i",bg_path,"-i",audio_path,
        "-vf",(f"scale=1920:1080:force_original_aspect_ratio=increase,"
               f"crop=1920:1080,"
               f"drawtext=text='{wm}':fontcolor=white@0.15:fontsize=16:x=w-tw-30:y=28:font=Arial"),
        "-map","0:v","-map","1:a","-t",str(duration),
        "-c:v","libx264","-preset","medium","-crf","19",
        "-c:a","aac","-b:a","192k","-r","30","-pix_fmt","yuv420p",
        "-movflags","+faststart","-shortest",out
    ],capture_output=True,text=True,timeout=2400)
    if result.returncode!=0: raise Exception(f"FFmpeg: {result.stderr[-300:]}")
    log(f"  Video: {Path(out).stat().st_size/1024/1024:.0f}MB | 1080p | No subtitles")
    return out

def run_stage4_video(audio_path, duration, niche):
    log("\n"+"="*65)
    log("  STAGE 4: Video Assembly — No Subtitles on Main")
    log("="*65)
    bg = fetch_background(niche["name"],duration)
    return assemble_video(audio_path,bg,duration,niche["watermark"])


# ════════════════════════════════════════════════════════════
# STAGE 5: SHORTS WITH SUBTITLES SYNCED TO AUDIO
# ════════════════════════════════════════════════════════════
def generate_short_srt(script_clean, start, short_dur):
    words    = script_clean.split()
    total_dur = (len(words)/125.0)*60.0
    wps      = len(words)/total_dur
    sw       = int(start*wps)
    ew       = min(int((start+short_dur)*wps)+5,len(words))
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
    short_dur=55
    start    =total_dur*(0.10 if stype=="teaser" else 0.67)
    raw      =str(WORK_DIR/f"s_{stype}_raw.mp4")
    final    =str(WORK_DIR/f"short_{stype}.mp4")
    subprocess.run(["ffmpeg","-y","-ss",str(start),"-i",video_path,"-t",str(short_dur),
                    "-vf","crop=608:1080:(iw-608)/2:0,scale=1080:1920",
                    "-c:v","libx264","-preset","fast","-crf","22",
                    "-c:a","aac","-b:a","128k",raw],capture_output=True,timeout=180)
    if not Path(raw).exists() or Path(raw).stat().st_size<400000:
        log(f"  Short {stype} clip failed"); return None
    srt=generate_short_srt(script_clean,start,short_dur)
    if not srt: return raw
    sub_style=("FontName=Arial,FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
               "BackColour=&HCC000000,Bold=1,Outline=3,Shadow=1,Alignment=2,"
               "MarginL=40,MarginR=40,MarginV=130,BorderStyle=3")
    subprocess.run(["ffmpeg","-y","-i",raw,"-vf",f"subtitles={srt}:force_style='{sub_style}'",
                    "-c:v","libx264","-preset","fast","-crf","21","-c:a","copy",final],
                   capture_output=True,timeout=180)
    if Path(final).exists() and Path(final).stat().st_size>400000:
        log(f"  Short ({stype}): {Path(final).stat().st_size/1024/1024:.1f}MB + subs")
        if Path(raw).exists(): Path(raw).unlink()
        return final
    return raw if Path(raw).exists() else None


# ════════════════════════════════════════════════════════════
# STAGE 6: UPLOAD
# ════════════════════════════════════════════════════════════
def get_yt_token():
    r=requests.post("https://oauth2.googleapis.com/token",data={
        "client_id":YT_CLIENT_ID,"client_secret":YT_CLIENT_SEC,
        "refresh_token":YT_REFRESH,"grant_type":"refresh_token"})
    d=r.json()
    if "access_token" not in d: raise Exception(f"YT token failed: {d}")
    return d["access_token"]

def upload_yt(path, meta, is_short=False):
    token=get_yt_token()
    title=f"#Shorts {meta['title'][:50]}" if is_short else meta["title"]
    desc =meta["description"]
    if not is_short and meta.get("chapters"):
        desc+="\n\nCHAPTERS:\n"+"".join(f"{c['time']} {c['title']}\n" for c in meta["chapters"])
    init=requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        headers={"Authorization":f"Bearer {token}","Content-Type":"application/json"},
        json={"snippet":{"title":title,"description":desc,"tags":meta.get("tags",[]),"categoryId":"22"},
              "status":{"privacyStatus":"public","selfDeclaredMadeForKids":False}})
    url=init.headers.get("Location")
    if not url: raise Exception(f"No URL: {init.text[:200]}")
    sz=Path(path).stat().st_size
    log(f"  Uploading {sz/1024/1024:.0f}MB...")
    with open(path,"rb") as f:
        up=requests.put(url,headers={"Content-Length":str(sz),"Content-Type":"video/mp4"},
                       data=f,timeout=2400)
    if up.status_code in [200,201]:
        return f"https://www.youtube.com/watch?v={up.json().get('id')}"
    raise Exception(f"Upload {up.status_code}: {up.text[:200]}")

def cleanup():
    for f in ["audio.mp3","audio.wav","bg.mp4","final.mp4",
              "short_teaser.mp4","short_recap.mp4","s_teaser_raw.mp4","s_recap_raw.mp4"]:
        p=WORK_DIR/f
        if p.exists(): p.unlink()
    for srt in WORK_DIR.glob("short_*.srt"): srt.unlink()
    log("  Cleanup complete")

def run_stage6_upload(video_path, meta, niche, voice_id, dur, wc, episode, state,
                      thumbnail_text, title_scores, decision, script_clean):
    log("\n"+"="*65)
    log("  STAGE 6: Upload Main + 2 Shorts")
    log("="*65)
    log("  Uploading main...")
    try:
        yt_url=upload_yt(video_path,meta,is_short=False)
        log(f"  Main: {yt_url}")
    except Exception as e:
        tg(f"Upload FAILED\n{str(e)[:200]}"); sys.exit(1)
    shorts=[]
    for stype in ["teaser","recap"]:
        try:
            sp=make_short_with_subs(video_path,script_clean,stype,dur)
            if sp:
                sm=dict(meta); sm["title"]=f"{meta['title'][:46]} — {stype.upper()}"
                su=upload_yt(sp,sm,is_short=True)
                shorts.append(f"Short {stype}: {su}"); log(f"  {shorts[-1]}")
        except Exception as e: log(f"  Short {stype}: {e}")
    cleanup()
    state["last_niche"]    =niche["name"]; state["last_voice"]=voice_id
    state["last_title"]    =meta.get("title",""); state["last_url"]=yt_url
    state["makeup_pending"]=False
    if "weekly_videos" not in state: state["weekly_videos"]=[]
    state["weekly_videos"].append({"date":datetime.datetime.now().isoformat(),
        "niche":niche["name"],"voice":voice_id,"title":meta.get("title",""),
        "url":yt_url,"thumbnail":thumbnail_text})
    state["weekly_videos"]=state["weekly_videos"][-7:]
    save_state(state)
    ev=int(7000*0.9); er=round((ev/1000)*niche["rpm"],2)
    dec="APPROVED" if decision=="approved" else "AUTO-APPROVED"
    tg(f"PUBLISHED — {dec}\n\n{meta['title']}\n"
       f"Ep{episode} | {niche['name']} | ${niche['rpm']} RPM\n"
       f"Voice: {voice_id} | {dur/60:.1f}min | {wc}w\n"
       f"Thumbnail: {thumbnail_text}\n\n"
       f"Main: {yt_url}\n{chr(10).join(shorts)}\n\n"
       f"Est 30d: {ev:,} views | ${er} (Rs.{int(er*83):,})\nArtifacts deleted.")
    log(f"\nCOMPLETE: {yt_url}")


# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════
def main():
    start=time.time()
    log("\n"+"="*65)
    log("  DEEPDIVE EMPIRE — PIPELINE v6.0")
    log("  Niches: Horror | Dark Seduction | Psych Trap | Supernatural | Obsession")
    log("  Quality: 7.3 min | 6.9 floor | 13 attempts | 20 human voices")
    log("="*65)
    state=load_state()
    tg(f"Pipeline v6.0 Starting\n"
       f"Niches: Horror Dark Seduction Psychological Supernatural Obsession\n"
       f"Time: {datetime.datetime.now().strftime('%I:%M %p')}\n"
       f"Quality: {MIN_GATE} min | Approval in ~15 min.")
    log("Startup notification sent")
    (niche,topic,voice,episode,script,meta,score,
     thumbnail_text,intel,title_scores) = run_stage1(state)
    elapsed=(time.time()-start)/60
    log(f"\nStage 1: {elapsed:.1f} min")
    tg(f"Stage 1 Complete\n{niche['name']} | {script['words']}w | {score}/10\n"
       f"Title: {meta.get('title','')[:60]}\nSending approval...")
    decision=run_stage2_approval(meta,niche,voice,script,thumbnail_text,title_scores)
    if decision=="rejected": log("Rejected."); sys.exit(0)
    elapsed=(time.time()-start)/60
    log(f"\nApproved at {elapsed:.1f} min")
    tg("Generating audio and video now...")
    audio_path,duration,audio_sz,voice_used=run_stage3_audio(script["clean"],voice,niche["name"])
    tg(f"Stage 3: {voice_used} | {duration/60:.1f}min")
    video_path=run_stage4_video(audio_path,duration,niche)
    elapsed=(time.time()-start)/60
    log(f"\nVideo ready at {elapsed:.1f} min")
    tg("Video ready. Uploading...")
    run_stage6_upload(video_path,meta,niche,voice_used,duration,
                      script["words"],episode,state,
                      thumbnail_text,title_scores,decision,script["clean"])
    log(f"\nTotal: {(time.time()-start)/60:.1f} minutes")

if __name__=="__main__":
    main()
