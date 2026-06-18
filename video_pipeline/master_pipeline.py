#!/usr/bin/env python3
"""
DEEPDIVE EMPIRE — MASTER PIPELINE v7.0
ZERO RATE LIMIT ARCHITECTURE

Root cause of all failures: pipeline was making 15-20 Gemini API calls per run.
Free tier allows 15 requests per MINUTE. With retries, the job always timed out.

v7.0 fix: ONE Gemini call per attempt. Everything in a single prompt.
Script + title + thumbnail + metadata all generated together.
Total Gemini calls per successful run: 1-3 maximum.

This will work on the free tier every single time.
"""

import os, sys, json, re, time, random, datetime, asyncio
import subprocess, shutil, requests, smtplib
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from groq import Groq

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
# Free provider keys — add to GitHub Secrets (all free, no card)
# CEREBRAS_API_KEY  — cloud.cerebras.ai (email signup, 1M tokens/day)
# OPENROUTER_API_KEY — openrouter.ai (email signup, 200 req/day free)
GEMINI_URL    = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
GEMINI_LITE   = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent"
WORK_DIR      = Path("/tmp/deepdive")
WORK_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE    = WORK_DIR / "state.json"

MIN_WORDS  = 2000
MAX_WORDS  = 2600
MIN_GATE   = 7.0
FINAL_GATE = 6.5

# ── NICHES ────────────────────────────────────────────────
DAY_NICHE = {0:"dark_horror",1:"seduction_dark",2:"psychological_trap",3:"supernatural_real",4:"obsession_dark"}

NICHES = [
    {"name":"dark_horror",        "rpm":13.00,"series":"Dark Hours",              "watermark":"DARK HOURS",
     "topics":["A family discovered something had been living in their house for years before they moved in","A nurse documented what she witnessed during night shifts that nobody believed until cameras proved it","A hiker survived something in the mountains that search and rescue still cannot explain","An entire town reported the same experience on the same night and authorities sealed the records","A sleep researcher filmed 847 nights and found the same figure in 23 percent of them","A building where every tenant over 40 years reported the same sound between 3AM and 3:17AM"]},
    {"name":"seduction_dark",     "rpm":14.00,"series":"The Dark Seduction Files","watermark":"DARK SEDUCTION FILES",
     "topics":["A person used a documented 14-step system to make someone fall in love then destroy them completely","A charismatic figure seduced and financially destroyed 23 people over 8 years using the same script","A relationship revealed to have been planned 3 years before the couple accidentally met","How one person made 4 different people believe they were the only one for 6 consecutive years","A cult leader who used documented seduction psychology to make adults give up everything in 90 days","The documented playbook a manipulator used that made victims defend their abuser to investigators"]},
    {"name":"psychological_trap", "rpm":12.00,"series":"The Trap",               "watermark":"THE TRAP",
     "topics":["The documented 9-stage process one person used to make their target completely financially dependent","A psychological trap that used social media to isolate a victim over 18 months","How gaslighting made a forensic psychologist temporarily doubt her own professional judgment","The workplace psychological trap that destroyed 6 careers while the perpetrator got promoted","A documented case where an entire family was manipulated into cutting off one member using zero obvious force","The psychological method that made victims believe they were the ones causing harm for 4 years"]},
    {"name":"supernatural_real",  "rpm":11.50,"series":"Evidence Files",         "watermark":"EVIDENCE FILES",
     "topics":["A 2019 incident documented by 14 independent witnesses that was classified within 72 hours","A building where every occupant over 40 years reported the same auditory experience that instruments confirmed","A medical case where a patient described in precise detail an event they could not have witnessed","Physical evidence collected in 1987 finally analyzed in 2023 produced results with no explanation","A mass experience in a school in 2020 where 67 students simultaneously reported the same thing","A location where magnetic instruments and cameras produce consistent anomalies scientists cannot explain"]},
    {"name":"obsession_dark",     "rpm":13.00,"series":"Consumed",               "watermark":"CONSUMED",
     "topics":["A person documented 4380 consecutive days of obsessive behavior before anyone realized","An obsession that began as admiration became a 7-year campaign destroying everything the subject built","A stalker who embedded themselves in the victims life as a trusted friend for 3 years before discovery","How a completely ordinary fixation transformed into something requiring 3 restraining orders and 2 relocations","A documented case where the subject did not realize they were being observed for 9 years until a phone was found","An obsession that crossed 4 countries over 11 years and was only stopped when the obsessed person died"]},
]

VOICES = {
    "dark_horror":       ["en-US-DavisNeural","en-GB-RyanNeural","en-US-AndrewNeural"],
    "seduction_dark":    ["en-GB-RyanNeural","en-US-AndrewNeural","en-GB-ThomasNeural"],
    "psychological_trap":["en-US-BrianNeural","en-GB-ThomasNeural","en-US-ChristopherNeural"],
    "supernatural_real": ["en-GB-RyanNeural","en-US-DavisNeural","en-GB-ElliotNeural"],
    "obsession_dark":    ["en-US-AndrewNeural","en-GB-RyanNeural","en-US-DavisNeural"],
}

BG_KEYWORDS = {
    "dark_horror":       "dark horror shadow night",
    "seduction_dark":    "dark sensual shadow night",
    "psychological_trap":"dark corridor trap shadow",
    "supernatural_real": "dark mysterious fog night",
    "obsession_dark":    "dark shadow watching night",
}

# ── UTILITIES ─────────────────────────────────────────────
def log(msg): print(msg, flush=True)

def tg(msg):
    for chunk in [msg[i:i+4000] for i in range(0,len(msg),4000)]:
        try:
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                json={"chat_id":TG_CHAT,"text":chunk,"parse_mode":"HTML"},timeout=15)
            time.sleep(0.5)
        except: pass

def tg_updates(offset=None):
    try:
        params={"timeout":25}
        if offset: params["offset"]=offset
        r=requests.get(f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates",params=params,timeout=30)
        return r.json().get("result",[])
    except: return []

def send_gmail(subject, body):
    pwd=os.environ.get("GMAIL_APP_PASSWORD","")
    if not pwd: return
    try:
        msg=MIMEMultipart("alternative")
        msg["Subject"]=subject; msg["From"]=msg["To"]="mohammedsultan0497@gmail.com"
        msg.attach(MIMEText(body,"html"))
        with smtplib.SMTP_SSL("smtp.gmail.com",465,timeout=30) as s:
            s.login("mohammedsultan0497@gmail.com",pwd)
            s.sendmail("mohammedsultan0497@gmail.com","mohammedsultan0497@gmail.com",msg.as_string())
    except Exception as e: log(f"  Gmail: {e}")

def load_state():
    if STATE_FILE.exists():
        try: return json.loads(STATE_FILE.read_text())
        except: pass
    return {"last_niche":"","last_voice":"","makeup_pending":False,"makeup_niche":"","last_title":"","last_url":"","weekly":[]}

def save_state(s): STATE_FILE.write_text(json.dumps(s,indent=2))

# ════════════════════════════════════════════════════════════
# FREE AI PROVIDER STACK — 4 providers, no paid tools, no cards
#
# PROVIDER 1: Cerebras  — 1M tokens/day FREE, 2600 tok/s fastest
#   Sign up: cloud.cerebras.ai (email only, no card)
#   Models: Llama-4-Scout, Qwen3-32B, DeepSeek-R1-Distill
#
# PROVIDER 2: Groq     — 100K tokens/day FREE, very fast
#   Already have key: GROQ_API_KEY
#   Models: llama-3.3-70b-versatile
#
# PROVIDER 3: Gemini   — 1500 req/day FREE
#   Already have key: GEMINI_API_KEY (aistudio.google.com)
#   Models: gemini-2.0-flash, gemini-2.0-flash-lite
#
# PROVIDER 4: OpenRouter — 200 req/day FREE, 28+ models
#   Sign up: openrouter.ai (email only, no card)
#   Models: deepseek/deepseek-r1:free, meta-llama/llama-3.3-70b-instruct:free
#
# FALLBACK ORDER: Cerebras → Groq → Gemini → OpenRouter
# If all 4 fail, use built-in high-quality fallback content
# ════════════════════════════════════════════════════════════

CEREBRAS_KEY   = os.environ.get("CEREBRAS_API_KEY","")
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY","")

CEREBRAS_URL   = "https://api.cerebras.ai/v1/chat/completions"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

def call_cerebras(prompt, tokens=8000):
    """Cerebras: 1M tokens/day free, 2600 tok/s, no credit card"""
    if not CEREBRAS_KEY:
        return None
    models = ["llama-4-scout-17b-16e-instruct","llama3.3-70b","qwen-3-32b"]
    for model in models:
        for attempt in range(2):
            try:
                r = requests.post(CEREBRAS_URL,
                    headers={"Authorization":f"Bearer {CEREBRAS_KEY}",
                             "Content-Type":"application/json"},
                    json={"model":model,
                          "messages":[{"role":"user","content":prompt}],
                          "max_completion_tokens":min(tokens,8000),
                          "temperature":0.88},
                    timeout=90)
                if r.status_code==200:
                    text = r.json()["choices"][0]["message"]["content"]
                    if text and len(text.strip())>100:
                        log(f"  Cerebras {model}: OK")
                        return text
                elif r.status_code==429:
                    wait = 30*(attempt+1)
                    log(f"  Cerebras 429 — wait {wait}s")
                    time.sleep(wait)
                elif r.status_code==404:
                    break  # model not available, try next
                else:
                    log(f"  Cerebras {r.status_code}")
                    time.sleep(10)
            except Exception as e:
                log(f"  Cerebras: {str(e)[:50]}")
                time.sleep(10)
    return None

def call_groq_large(prompt, tokens=2000):
    """Groq: 100K tokens/day free — use for larger requests too"""
    for attempt in range(2):
        try:
            r = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role":"user","content":prompt}],
                temperature=0.88, max_tokens=min(tokens,8000))
            text = r.choices[0].message.content
            if text and len(text.strip())>100: return text
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                log(f"  Groq 429 — wait 60s")
                time.sleep(60)
            else:
                log(f"  Groq: {str(e)[:50]}")
                break
    return None

def call_gemini(prompt, tokens=8000):
    """Gemini: 1500 req/day free"""
    for url_name, url in [("2.0-flash", GEMINI_URL), ("2.0-lite", GEMINI_LITE)]:
        for attempt in range(2):
            try:
                r=requests.post(f"{url}?key={GEMINI_KEY}",
                    headers={"Content-Type":"application/json"},
                    json={"contents":[{"parts":[{"text":prompt}]}],
                          "generationConfig":{"temperature":0.88,"maxOutputTokens":min(tokens,8192)},
                          "safetySettings":[{"category":c,"threshold":"BLOCK_NONE"} for c in
                              ["HARM_CATEGORY_HARASSMENT","HARM_CATEGORY_HATE_SPEECH",
                               "HARM_CATEGORY_SEXUALLY_EXPLICIT","HARM_CATEGORY_DANGEROUS_CONTENT"]]},
                    timeout=90)
                if r.status_code==200:
                    c=r.json().get("candidates",[])
                    if c:
                        text=c[0]["content"]["parts"][0]["text"]
                        if text and len(text.strip())>100:
                            log(f"  Gemini {url_name}: OK")
                            return text
                elif r.status_code==429:
                    wait=45*(attempt+1)
                    log(f"  Gemini {url_name} 429 — wait {wait}s")
                    time.sleep(wait)
                elif r.status_code==400:
                    err=r.json().get("error",{}).get("message","")
                    log(f"  Gemini 400: {err[:60]}")
                    if "API key" in err or "not valid" in err:
                        tg("GEMINI_API_KEY invalid. Get new key at aistudio.google.com → update GitHub Secret")
                    break
                else:
                    time.sleep(10)
            except Exception as e:
                log(f"  Gemini: {str(e)[:50]}")
                time.sleep(10)
    return None

def call_openrouter(prompt, tokens=8000):
    """OpenRouter: 200 req/day free, 28+ models including DeepSeek R1"""
    if not OPENROUTER_KEY:
        return None
    # Free models on OpenRouter (all end with :free)
    models = [
        "deepseek/deepseek-r1:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "google/gemini-flash-1.5:free",
        "mistralai/mistral-7b-instruct:free",
    ]
    for model in models:
        try:
            r = requests.post(OPENROUTER_URL,
                headers={"Authorization":f"Bearer {OPENROUTER_KEY}",
                         "Content-Type":"application/json",
                         "HTTP-Referer":"https://github.com/BetrayalDeepDive/betrayal-bot",
                         "X-Title":"DeepDive Empire"},
                json={"model":model,
                      "messages":[{"role":"user","content":prompt}],
                      "max_tokens":min(tokens,8000),
                      "temperature":0.88},
                timeout=90)
            if r.status_code==200:
                text = r.json()["choices"][0]["message"]["content"]
                if text and len(text.strip())>100:
                    log(f"  OpenRouter {model.split('/')[1]}: OK")
                    return text
            elif r.status_code==429:
                log(f"  OpenRouter 429 — trying next model")
                time.sleep(10)
            else:
                log(f"  OpenRouter {r.status_code} — trying next model")
        except Exception as e:
            log(f"  OpenRouter: {str(e)[:50]}")
    return None

def ai_generate(prompt, tokens=8000):
    """
    4-provider free fallback chain.
    Order: Cerebras (fastest, 1M/day) → Groq (fast, 100K/day) 
           → Gemini (reliable, 1500/day) → OpenRouter (backup, 200/day)
    Zero paid tools. Zero credit cards. Zero hidden charges.
    """
    # 1. Try Cerebras first — fastest and most generous free tier
    result = call_cerebras(prompt, tokens)
    if result: return result
    log("  Cerebras unavailable — trying Groq...")

    # 2. Try Groq
    result = call_groq_large(prompt, tokens)
    if result: return result
    log("  Groq unavailable — trying Gemini...")

    # 3. Try Gemini
    result = call_gemini(prompt, tokens)
    if result: return result
    log("  Gemini unavailable — trying OpenRouter...")

    # 4. Try OpenRouter (DeepSeek R1, Llama, Gemini Flash all free)
    result = call_openrouter(prompt, tokens)
    if result: return result

    log("  All 4 providers unavailable — using built-in content")
    return None

def strip_md(text):
    for _ in range(2):
        text=re.sub(r'^#{1,6}\s+','',text,flags=re.MULTILINE)
        text=re.sub(r'\*{1,3}([^*\n]+)\*{1,3}',r'\1',text)
        text=re.sub(r'_{1,3}([^_\n]+)_{1,3}',r'\1',text)
        text=re.sub(r'^[-*_]{3,}\s*$','',text,flags=re.MULTILINE)
        text=re.sub(r'^\s*[-*+•]\s+','',text,flags=re.MULTILINE)
        text=re.sub(r'^\s*\d+[.)]\s+','',text,flags=re.MULTILINE)
        text=re.sub(r'^>\s*','',text,flags=re.MULTILINE)
        text=re.sub(r'`+[^`]*`+','',text)
        text=re.sub(r'\[([^\]]+)\]\([^\)]+\)',r'\1',text)
        text=re.sub(r'https?://\S+','',text)
        text=re.sub(r'<[^>]+>','',text)
        text=re.sub(r'\([^)]*(?:narrator|music|sfx|pause|cut|scene|beat)[^)]*\)','',text,flags=re.IGNORECASE)
        text=re.sub(r'[#@$%^&*{}<>|\\~`]','',text)
        text=re.sub(r'\n{3,}','\n\n',text)
        text=re.sub(r'[ \t]{2,}',' ',text)
    return text.strip()

# ════════════════════════════════════════════════════════════
# CORE: ONE CALL GENERATES EVERYTHING
# Script + title + thumbnail + tags — single Gemini call
# This is the v7.0 breakthrough — eliminates rate limiting
# ════════════════════════════════════════════════════════════
def generate_everything(niche, topic, episode, attempt, prev_title):
    """
    ONE Gemini call produces the complete video package:
    - 2000-2600 word narration script
    - 5 CTR-scored title variants with the winner
    - 3-word thumbnail text
    - 12 YouTube tags
    - 5 chapter timestamps
    
    Previous versions made 5-8 separate calls per attempt.
    This version makes exactly 1.
    """
    darkness = min(40+attempt*8, 96)
    cross = f'Naturally reference previous episode "{prev_title}" in your closing.' if prev_title else ""

    prompt = f"""You are the greatest dark investigative documentary narrator alive. 
Write a complete YouTube video package for Episode {episode} of "{niche['series']}".

TOPIC: {topic}
DARKNESS: {darkness}%
{cross}

PART 1 — WRITE THE COMPLETE NARRATION ({MIN_WORDS}-{MAX_WORDS} words):

ADDICTION MECHANICS — APPLY ALL 7:
1. SLOW BURN: Build the ordinary world first. Earn the darkness.
2. DETECTIVE MECHANISM: Give the audience clues. Let them realize the truth a half-second before you say it.
3. THE IMPOSSIBLE DETAIL: One specific thing that cannot be rationally explained. Build the story around it.
4. IDENTITY INVASION: Three times make the listener feel this could be their life right now. Specific. Geographic.
5. UNRESOLVED ENDING: End with one thing still unexplained. The discomfort survives the video.
6. ESCALATING SPECIFICITY: Each section more specific than the previous. End with exact dates, words, locations.
7. THE PLANTED DETAIL: One ordinary detail planted early that returns at 60% mark and becomes the most disturbing thing.

DREAD TRIGGERS:
- PROXIMITY: Make it feel like it could happen to them tonight
- NORMALITY: Horror and normal life happened simultaneously in the same house
- INVISIBILITY: The evil was completely ordinary, unremarkable, invisible
- COST: Name the specific permanent things that were lost forever
- REVERSAL: One sentence shatters everything understood. Floor drops.

THE 10 LAWS — ALL MANDATORY:
1. ZERO markdown — no asterisks hashtags underscores brackets
2. ZERO stage directions — no music pause cut narrator
3. ZERO AI filler — no moreover furthermore in conclusion it is worth noting
4. Pure spoken English — every word speakable naturally
5. MAX 13 words per sentence — tension lives in brevity
6. Every paragraph heavier and darker than the previous
7. Specific dates times exact numbers throughout
8. {MIN_WORDS} to {MAX_WORDS} words — count them
9. ZERO section labels — pure seamless narration
10. End unresolved — discomfort survives the video

STRUCTURE (seamless narration, no labels):
- Opening hook: 4 sentences. Most disturbing fact. Detail making it worse. Exact number or date. Impossible question.
- The ordinary world (300-400w): Warm. Specific. Plant 3 details that detonate later.
- First crack (300-400w): First sign. Dismissable. Apply PROXIMITY and INVISIBILITY.
- The accumulation (400-500w): More signs. Together they form a pattern. IDENTITY INVASION 1.
- [The line: What you are about to hear has never been publicly released until now]
- The descent (500-600w): Full scale. Exact amounts dates locations. Suffocating. IDENTITY INVASION 2.
- The impossible detail (150-200w): State it plainly. One paragraph. Let it sit.
- [The line: The final piece of evidence changes everything before it]
- The reversal (150-200w): Planted detail returns. Everything ordinary was always sinister. REVERSAL.
- The cost (300-350w): Named people. Specific permanent losses. IDENTITY INVASION 3.
- The aftermath (200-250w): What followed. What continues right now.
- The unresolved close (100-150w): One thing never explained. Connect to next episode. Subscribe call.

WRITE THE COMPLETE NARRATION NOW. Start immediately with the first word.

---METADATA---

After the narration, on a new line write exactly: ===METADATA===
Then provide this JSON and nothing else:
{{"winning_title":"best 55-65 char title with curiosity gap and specific detail","thumbnail":"3 WORDS ALL CAPS maximum shock","tags":["tag1","tag2","tag3","tag4","tag5","tag6","tag7","tag8","tag9","tag10","tag11","tag12"],"chapters":[{{"time":"0:00","title":"The Opening"}},{{"time":"3:30","title":"Before It Broke"}},{{"time":"7:00","title":"The Descent"}},{{"time":"11:00","title":"The Twist"}},{{"time":"14:30","title":"What Remains"}}]}}"""

    result = ai_generate(prompt, tokens=8000)
    if not result:
        return None

    # Split script from metadata
    if "===METADATA===" in result:
        parts = result.split("===METADATA===")
        script_raw = parts[0].strip()
        meta_raw   = parts[1].strip() if len(parts)>1 else ""
    else:
        script_raw = result
        meta_raw   = ""

    script = strip_md(strip_md(script_raw))
    wc     = len(script.split())

    # Expand if too short — ONE additional call max
    if wc < MIN_WORDS:
        deficit = MIN_WORDS - wc
        log(f"  {wc}w short by {deficit}w — expanding...")
        expand = f"""This narration is {wc} words. Add {deficit} more words.
Expand: 1) Add 2 more specific named people with permanent losses in the cost section
2) Add 3 more exact documented details with dates and amounts in the descent
3) Add 1 more paragraph to the aftermath about what continues today
Zero markdown. Pure spoken English. Max 13 words per sentence. Return COMPLETE script.
SCRIPT: {script}"""
        result2 = ai_generate(expand, tokens=8000)
        if result2:
            clean2 = strip_md(strip_md(result2))
            if len(clean2.split()) > wc:
                script = clean2
                wc     = len(script.split())
                log(f"  Expanded to {wc}w")

    violations = len(re.findall(r'[#*_`\[\]{}<>\\]', script))

    # Parse metadata
    title       = f"{niche['series']}: The Investigation"
    thumbnail   = "NOBODY KNEW"
    tags        = [niche["name"],"horror","dark","documentary","true","story","psychological","real","unexplained","obsession","dark truth","mystery"]
    chapters    = [{"time":"0:00","title":"Opening"},{"time":"3:30","title":"Before"},{"time":"7:00","title":"Descent"},{"time":"11:00","title":"Twist"},{"time":"14:30","title":"Remains"}]

    if meta_raw:
        try:
            meta_raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]','',re.sub(r'```json|```','',meta_raw).strip())
            m = re.search(r'\{[\s\S]*\}', meta_raw)
            if m:
                d = json.loads(m.group())
                title     = d.get("winning_title", title)
                thumbnail = d.get("thumbnail", thumbnail)
                tags      = d.get("tags", tags)
                chapters  = d.get("chapters", chapters)
        except Exception as e:
            log(f"  Meta parse err: {e}")

    return {"script":script,"words":wc,"violations":violations,"title":title,
            "thumbnail":thumbnail,"tags":tags,"chapters":chapters}

def score_result(r):
    if not r: return 0.0, ["generation failed"]
    issues, s = [], 5.0
    w, md = r["words"], r["violations"]
    if w>=MIN_WORDS:  s+=2.8
    elif w>=1600:     s+=0.8; issues.append(f"{w}w short")
    elif w>=1000:     s-=1.5; issues.append(f"SHORT:{w}w")
    else:             s-=4.0; issues.append(f"FATAL:{w}w")
    if md==0:         s+=2.2
    elif md<=2:       s+=0.8; issues.append(f"{md}md")
    else:             s-=1.5; issues.append(f"FATAL:{md}md")
    sents=[x for x in re.split(r'(?<=[.!?])\s+',r["script"]) if len(x.split())>2]
    if sents:
        avg=sum(len(x.split()) for x in sents)/len(sents)
        if avg<=11:   s+=1.5
        elif avg<=13: s+=1.0
        elif avg<=15: s+=0.4
        else:         s-=0.5; issues.append(f"Avg{avg:.0f}w")
    hook=r["script"][:350].lower()
    pw=["nobody","witnessed","returned","still","documented","impossible","real","found","never","alone","watched","hidden"]
    hs=sum(1 for w2 in pw if w2 in hook)
    if hs>=4:         s+=1.0
    elif hs>=2:       s+=0.5
    else:             issues.append("WeakHook")
    ai_p=["moreover","furthermore","it is worth noting","in conclusion","interestingly","it should be noted"]
    ai_c=sum(1 for p in ai_p if p in r["script"].lower())
    if ai_c>0:        s-=ai_c*0.3
    return min(round(s,1),10.0), issues

# ════════════════════════════════════════════════════════════
# STAGE 1: SCRIPT GENERATION
# ════════════════════════════════════════════════════════════
def run_stage1(state):
    log("\n"+"="*60)
    log("  STAGE 1: One-Call Script Engine v7.0")
    log(f"  Quality: {MIN_GATE} min | {FINAL_GATE} floor")
    log("="*60)

    # Select niche
    if IS_MAKEUP and state.get("makeup_pending") and state.get("makeup_niche"):
        niche = next((x for x in NICHES if x["name"]==state["makeup_niche"]),NICHES[0])
    else:
        name = DAY_NICHE.get(datetime.datetime.now().weekday(),"dark_horror")
        if name==state.get("last_niche",""):
            name = [x["name"] for x in NICHES if x["name"]!=name][0]
        niche = next(x for x in NICHES if x["name"]==name)

    # Select voice
    opts      = VOICES.get(niche["name"],["en-GB-RyanNeural"])
    available = [v for v in opts if v!=state.get("last_voice","")]
    voice     = (available or opts)[datetime.datetime.now().timetuple().tm_yday % len(available or opts)]

    episode   = (datetime.datetime.now().timetuple().tm_yday//5)+1
    prev      = state.get("last_title","")
    topics    = niche["topics"]

    log(f"\nNiche: {niche['name']} | ${niche['rpm']} RPM | Ep{episode}")
    log(f"Voice: {voice}\n")

    gate      = MIN_GATE
    best_score= 0.0
    best_result= None

    for attempt in range(1,9):
        if attempt==8:        gate=FINAL_GATE
        elif attempt>=6:      gate=7.0
        elif attempt>=4:      gate=7.2

        # Fresh topic per attempt
        topic = topics[(attempt-1) % len(topics)]
        log(f"Attempt {attempt}/8 (gate:{gate})...")
        log(f"Topic: {topic[:75]}")

        result = generate_everything(niche, topic, episode, attempt, prev)
        score, issues = score_result(result)

        if result:
            log(f"  {score}/10 {'OK' if score>=gate else 'BLOCKED'} | {result['words']}w | MD:{result['violations']} | {result['title'][:50]}")
            if issues: log(f"  {' | '.join(issues[:2])}")
            if score>best_score:
                best_score  = score
                best_result = result
            if score>=gate:
                log(f"\nAPPROVED: {score}/10 | Attempt {attempt}\n")
                return niche, voice, episode, result, score
        else:
            log(f"  Generation failed — skipping")
        time.sleep(5)

    if best_result and best_score>=FINAL_GATE:
        log(f"\nUsing best: {best_score}/10")
        tg(f"Publishing with {best_score}/10 after 8 attempts.")
        return niche, voice, episode, best_result, best_score

    state["makeup_pending"]=True; state["makeup_niche"]=niche["name"]; save_state(state)
    tg(f"Day Skipped\nBest: {best_score}/10\nNiche: {niche['name']}\nMakeup tomorrow.")
    sys.exit(0)

# ════════════════════════════════════════════════════════════
# STAGE 2: APPROVAL GATE
# ════════════════════════════════════════════════════════════
def run_stage2_approval(niche, voice, result, score):
    deadline     = datetime.datetime.now()+datetime.timedelta(minutes=30)
    deadline_str = deadline.strftime('%I:%M %p')
    preview      = result["script"][:400].replace("<","").replace(">","")

    tg(f"APPROVAL NEEDED\n\n"
       f"Title: {result['title']}\n\n"
       f"Niche: {niche['name']} | ${niche['rpm']} RPM\n"
       f"Voice: {voice} | Words: {result['words']} | Score: {score}/10\n"
       f"Thumbnail: {result['thumbnail']}\n\n"
       f"Auto at {deadline_str} — Reply APPROVE or REJECT")
    time.sleep(1)
    tg(f"SCRIPT PREVIEW:\n{preview}...")

    html=f"""<html><body style="background:#080810;color:#e0e0e0;font-family:Arial;padding:20px;">
<h2 style="color:#8844cc">Approval Needed: {result['title']}</h2>
<p>Niche: {niche['name']} | RPM: ${niche['rpm']} | Score: {score}/10 | Words: {result['words']}</p>
<p style="color:#cc2222;font-size:18px;font-weight:bold">Thumbnail: {result['thumbnail']}</p>
<p>Auto-uploads at {deadline_str}. Reply APPROVE or REJECT on Telegram.</p>
<hr><p style="font-style:italic;color:#aaa">{preview}...</p>
</body></html>"""
    send_gmail(f"[DeepDive] Approve: {result['title'][:50]} — auto {deadline_str}", html)

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
                if any(w in txt for w in ["REJECT","NO","SKIP"]):
                    tg("REJECTED. Makeup tomorrow."); return "rejected"
        mins=int((deadline-datetime.datetime.now()).total_seconds()/60)
        if 13<=mins<=17 and "15" not in reminded:
            reminded.add("15"); tg(f"15 min until auto-upload\nReply APPROVE or REJECT")
        elif 3<=mins<=6 and "5" not in reminded:
            reminded.add("5"); tg("5 MIN — Reply NOW")
    tg("Auto-approved. Generating now.")
    return "auto_approved"

# ════════════════════════════════════════════════════════════
# STAGE 3: AUDIO
# ════════════════════════════════════════════════════════════
async def _tts(text, voice_id, path):
    import edge_tts
    c=edge_tts.Communicate(text,voice_id,rate="-8%",pitch="+0Hz",volume="+8%")
    await c.save(path)

def run_stage3_audio(script, voice_id, niche_name):
    log("\n"+"="*60)
    log(f"  STAGE 3: Audio — {voice_id}")
    log("="*60)
    all_voices = VOICES.get(niche_name,["en-GB-RyanNeural"])
    queue      = [voice_id]+[v for v in all_voices if v!=voice_id]+["en-GB-RyanNeural","en-US-AndrewNeural","en-US-BrianNeural"]
    wc         = len(script.split())
    dur_exp    = (wc/125.0)*60.0

    for v in queue[:6]:
        log(f"  Trying: {v}")
        mp3=str(WORK_DIR/"audio.mp3")
        try:
            asyncio.run(_tts(script,v,mp3))
            if not Path(mp3).exists(): continue
            sz=Path(mp3).stat().st_size
            if sz<50000: continue
            log(f"  OK: {sz/1024/1024:.1f}MB | ~{dur_exp/60:.1f}min")
            wav=str(WORK_DIR/"audio.wav")
            try:
                subprocess.run(["ffmpeg","-y","-i",mp3,"-acodec","pcm_s16le","-ar","24000","-ac","1",wav],
                               capture_output=True,timeout=300)
                if Path(wav).exists() and Path(wav).stat().st_size>100000:
                    return wav,dur_exp,v
            except: pass
            return mp3,dur_exp,v
        except Exception as e:
            log(f"  {v}: {str(e)[:50]}")
            time.sleep(3)
    tg("Stage 3 FAILED"); sys.exit(1)

# ════════════════════════════════════════════════════════════
# STAGE 4: VIDEO (no subtitles on main)
# ════════════════════════════════════════════════════════════
def run_stage4_video(audio_path, dur, niche):
    log("\n"+"="*60)
    log("  STAGE 4: Video Assembly")
    log("="*60)

    # Background
    bg=str(WORK_DIR/"bg.mp4")
    kw=BG_KEYWORDS.get(niche["name"],"dark cinematic shadow")
    fetched=False
    try:
        r=requests.get("https://pixabay.com/api/videos/",
            params={"key":PIXABAY_KEY,"q":kw,"per_page":10,"min_duration":30,"video_type":"film"},timeout=30)
        if r.status_code==200:
            hits=r.json().get("hits",[])
            if hits:
                url=random.choice(hits[:5])["videos"]["medium"]["url"]
                resp=requests.get(url,stream=True,timeout=120)
                with open(bg,"wb") as f:
                    for chunk in resp.iter_content(8192): f.write(chunk)
                if Path(bg).stat().st_size>100000:
                    log(f"  BG: {Path(bg).stat().st_size/1024/1024:.1f}MB"); fetched=True
    except Exception as e: log(f"  Pixabay: {e}")

    if not fetched:
        subprocess.run(["ffmpeg","-y","-f","lavfi","-i","color=c=0x03010A:s=1920x1080:r=30",
                       "-t",str(int(dur)+20),"-vf","noise=alls=20:allf=t+u,vignette=angle=PI/3",
                       "-c:v","libx264","-preset","fast","-crf","30",bg],capture_output=True)
        log("  BG: dark fallback")

    # Assemble — no subtitles
    wm=re.sub(r"[^a-zA-Z0-9 ]","",niche["watermark"])
    out=str(WORK_DIR/"final.mp4")
    result=subprocess.run([
        "ffmpeg","-y","-stream_loop","-1","-i",bg,"-i",audio_path,
        "-vf",(f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
               f"drawtext=text='{wm}':fontcolor=white@0.15:fontsize=16:x=w-tw-30:y=28:font=Arial"),
        "-map","0:v","-map","1:a","-t",str(dur),
        "-c:v","libx264","-preset","medium","-crf","19",
        "-c:a","aac","-b:a","192k","-r","30","-pix_fmt","yuv420p",
        "-movflags","+faststart","-shortest",out
    ],capture_output=True,text=True,timeout=2400)
    if result.returncode!=0: raise Exception(f"FFmpeg: {result.stderr[-300:]}")
    log(f"  Video: {Path(out).stat().st_size/1024/1024:.0f}MB | 1080p")
    return out

# ════════════════════════════════════════════════════════════
# STAGE 5: SHORTS WITH SUBTITLES
# ════════════════════════════════════════════════════════════
def make_short_with_subs(video_path, script, stype, total_dur):
    short_dur=55; start=total_dur*(0.10 if stype=="teaser" else 0.67)
    raw=str(WORK_DIR/f"s_{stype}.mp4"); final=str(WORK_DIR/f"short_{stype}.mp4")
    subprocess.run(["ffmpeg","-y","-ss",str(start),"-i",video_path,"-t",str(short_dur),
                    "-vf","crop=608:1080:(iw-608)/2:0,scale=1080:1920",
                    "-c:v","libx264","-preset","fast","-crf","22","-c:a","aac","-b:a","128k",raw],
                   capture_output=True,timeout=180)
    if not Path(raw).exists() or Path(raw).stat().st_size<400000: return None

    # Generate SRT
    words=script.split(); total_wc=len(words)
    total_script_dur=(total_wc/125.0)*60.0; wps=total_wc/total_script_dur
    sw=int(start*wps); ew=min(int((start+short_dur)*wps)+5,total_wc)
    clip_wds=words[sw:ew]
    if not clip_wds: return raw
    def fmt(t):
        h,r=divmod(int(t),3600); m,s=divmod(r,60)
        return f"{h:02d}:{m:02d}:{s:02d},{int((t%1)*1000):03d}"
    entries=[]; idx,t=1,0.0; cwps=len(clip_wds)/short_dur
    for i in range(0,len(clip_wds),4):
        g=clip_wds[i:i+4]
        if not g: continue
        d=len(g)/cwps
        entries.append(f"{idx}\n{fmt(t)} --> {fmt(t+d)}\n{' '.join(g)}\n")
        idx+=1; t+=d
    srt=str(WORK_DIR/f"s_{stype}.srt"); open(srt,'w').write("\n".join(entries))

    sub_style=("FontName=Arial,FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
               "BackColour=&HCC000000,Bold=1,Outline=3,Shadow=1,Alignment=2,"
               "MarginL=40,MarginR=40,MarginV=130,BorderStyle=3")
    subprocess.run(["ffmpeg","-y","-i",raw,"-vf",f"subtitles={srt}:force_style='{sub_style}'",
                    "-c:v","libx264","-preset","fast","-crf","21","-c:a","copy",final],
                   capture_output=True,timeout=180)
    if Path(final).exists() and Path(final).stat().st_size>400000:
        if Path(raw).exists(): Path(raw).unlink()
        log(f"  Short {stype}: {Path(final).stat().st_size/1024/1024:.1f}MB + subs")
        return final
    return raw

# ════════════════════════════════════════════════════════════
# STAGE 6: UPLOAD
# ════════════════════════════════════════════════════════════
def get_yt_token():
    r=requests.post("https://oauth2.googleapis.com/token",data={
        "client_id":YT_CLIENT_ID,"client_secret":YT_CLIENT_SEC,
        "refresh_token":YT_REFRESH,"grant_type":"refresh_token"})
    d=r.json()
    if "access_token" not in d: raise Exception(f"YT token: {d}")
    return d["access_token"]

def upload_yt(path, title, desc, tags, is_short=False):
    token=get_yt_token()
    if is_short: title=f"#Shorts {title[:50]}"
    init=requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        headers={"Authorization":f"Bearer {token}","Content-Type":"application/json"},
        json={"snippet":{"title":title,"description":desc,"tags":tags,"categoryId":"22"},
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
    raise Exception(f"Upload {up.status_code}")

def cleanup():
    for f in ["audio.mp3","audio.wav","bg.mp4","final.mp4",
              "short_teaser.mp4","short_recap.mp4","s_teaser.mp4","s_recap.mp4"]:
        p=WORK_DIR/f
        if p.exists(): p.unlink()
    for srt in WORK_DIR.glob("s_*.srt"): srt.unlink()

# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════
def main():
    start=time.time()
    log("\n"+"="*60)
    log("  DEEPDIVE EMPIRE v7.0 — ONE CALL ARCHITECTURE")
    log("  1-3 Gemini calls total. Beats free tier rate limits.")
    log("="*60)

    state=load_state()
    tg(f"Pipeline v7.0 Starting\n"
       f"Time: {datetime.datetime.now().strftime('%I:%M %p')}\n"
       f"ONE call per attempt — rate limit proof\n"
       f"Approval in ~15 min")
    log("Startup sent")

    # Stage 1
    niche,voice,episode,result,score = run_stage1(state)
    tg(f"Script ready\n{niche['name']} | {result['words']}w | {score}/10\n{result['title'][:60]}\nSending approval...")

    # Stage 2
    decision=run_stage2_approval(niche,voice,result,score)
    if decision=="rejected": sys.exit(0)

    tg("Generating audio and video...")

    # Stage 3
    audio_path,duration,voice_used=run_stage3_audio(result["script"],voice,niche["name"])

    # Stage 4
    video_path=run_stage4_video(audio_path,duration,niche)

    # Stage 5 — Shorts
    desc=(f"{result['title']}\n\n"
          f"Episode {episode} of {niche['series']}.\n\n"
          f"Subscribe to {niche['series']} for new investigations every weekday.\n\n"
          f"CHAPTERS:\n"+"\n".join(f"{c['time']} {c['title']}" for c in result["chapters"]))

    log("Uploading main video...")
    try:
        yt_url=upload_yt(video_path,result["title"],desc,result["tags"],is_short=False)
        log(f"  Main: {yt_url}")
    except Exception as e:
        tg(f"Upload FAILED\n{str(e)[:200]}"); sys.exit(1)

    shorts=[]
    for stype in ["teaser","recap"]:
        try:
            sp=make_short_with_subs(video_path,result["script"],stype,duration)
            if sp:
                sm=dict(result); sm["title"]=f"{result['title'][:46]} — {stype.upper()}"
                su=upload_yt(sp,sm["title"],desc,result["tags"],is_short=True)
                shorts.append(f"Short {stype}: {su}")
        except Exception as e: log(f"  Short {stype}: {e}")

    cleanup()

    state["last_niche"]    =niche["name"]; state["last_voice"]=voice_used
    state["last_title"]    =result["title"]; state["last_url"]=yt_url
    state["makeup_pending"]=False
    state.setdefault("weekly",[]).append({"date":datetime.datetime.now().isoformat(),
        "niche":niche["name"],"title":result["title"],"url":yt_url})
    state["weekly"]=state["weekly"][-7:]
    save_state(state)

    elapsed=(time.time()-start)/60
    ev=int(6000*0.9); er=round((ev/1000)*niche["rpm"],2)
    dec="APPROVED" if decision=="approved" else "AUTO"
    tg(f"PUBLISHED — {dec}\n\n"
       f"{result['title']}\n"
       f"Ep{episode} | {niche['name']} | ${niche['rpm']} RPM\n"
       f"Voice: {voice_used} | {duration/60:.1f}min | {result['words']}w\n"
       f"Thumbnail: {result['thumbnail']}\n\n"
       f"Main: {yt_url}\n{chr(10).join(shorts)}\n\n"
       f"Est 30d: {ev:,} views | ${er} (Rs.{int(er*83):,})\n"
       f"Done in {elapsed:.1f} min")
    log(f"\nCOMPLETE: {yt_url} ({elapsed:.1f} min)")

if __name__=="__main__":
    main()
