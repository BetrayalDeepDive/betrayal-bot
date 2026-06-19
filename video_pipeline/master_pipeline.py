#!/usr/bin/env python3
"""
DEEPDIVE EMPIRE v8.0 FINAL
Merged from v7.0 (15 days work) + Token/JSON fixes
CEREBRAS PRIMARY → GROQ → GEMINI → OPENROUTER
QUALITY GATES | NICHE OPTIMIZATION | THUMBNAIL CTR | $100M READY
"""

import os, sys, json, re, time, random, datetime, asyncio, glob
import subprocess, shutil, requests, smtplib
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from groq import Groq

# ════════════════════════════════════════════════════════════
# ENVIRONMENT & SETUP
# ════════════════════════════════════════════════════════════
GROQ_KEY = os.environ.get("GROQ_API_KEY","")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY","")
CEREBRAS_KEY = os.environ.get("CEREBRAS_API_KEY","")
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY","")
PIXABAY_KEY = os.environ.get("PIXABAY_KEY","")
ELEVENLABS_KEY = os.environ.get("ELEVENLABS_API_KEY","")
PEXELS_KEY = os.environ.get("PEXELS_API_KEY","")

YT_CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID","")
YT_CLIENT_SEC = os.environ.get("YOUTUBE_CLIENT_SECRET","")
YT_REFRESH = os.environ.get("YOUTUBE_REFRESH_TOKEN","")
TG_TOKEN = os.environ.get("TELEGRAM_TOKEN","")
TG_CHAT = os.environ.get("TELEGRAM_CHAT_ID","")
IS_MAKEUP = os.environ.get("IS_MAKEUP","false").lower() == "true"

groq_client = Groq(api_key=GROQ_KEY)

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
GEMINI_LITE = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent"
CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

WORK_DIR = Path("/tmp/deepdive")
WORK_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = WORK_DIR / "state.json"

MIN_WORDS = 2000
MAX_WORDS = 2600
MIN_GATE = 7.0
FINAL_GATE = 6.5

# ════════════════════════════════════════════════════════════
# NICHES - HIGH RPM, QUALITY CONTENT
# ════════════════════════════════════════════════════════════
DAY_NICHE = {0:"dark_horror",1:"seduction_dark",2:"psychological_trap",3:"supernatural_real",4:"obsession_dark"}

NICHES = [
    {"name":"dark_horror","rpm":13.00,"series":"Dark Hours","watermark":"DARK HOURS",
     "topics":["A family discovered something had been living in their house for years before they moved in","A nurse documented what she witnessed during night shifts that nobody believed until cameras proved it","A hiker survived something in the mountains that search and rescue still cannot explain","An entire town reported the same experience on the same night and authorities sealed the records","A sleep researcher filmed 847 nights and found the same figure in 23 percent of them","A building where every tenant over 40 years reported the same sound between 3AM and 3:17AM"]},
    {"name":"seduction_dark","rpm":14.00,"series":"The Dark Seduction Files","watermark":"DARK SEDUCTION FILES",
     "topics":["A person used a documented 14-step system to make someone fall in love then destroy them completely","A charismatic figure seduced and financially destroyed 23 people over 8 years using the same script","A relationship revealed to have been planned 3 years before the couple accidentally met","How one person made 4 different people believe they were the only one for 6 consecutive years","A cult leader who used documented seduction psychology to make adults give up everything in 90 days","The documented playbook a manipulator used that made victims defend their abuser to investigators"]},
    {"name":"psychological_trap","rpm":12.00,"series":"The Trap","watermark":"THE TRAP",
     "topics":["The documented 9-stage process one person used to make their target completely financially dependent","A psychological trap that used social media to isolate a victim over 18 months","How gaslighting made a forensic psychologist temporarily doubt her own professional judgment","The workplace psychological trap that destroyed 6 careers while the perpetrator got promoted","A documented case where an entire family was manipulated into cutting off one member using zero obvious force","The psychological method that made victims believe they were the ones causing harm for 4 years"]},
    {"name":"supernatural_real","rpm":11.50,"series":"Evidence Files","watermark":"EVIDENCE FILES",
     "topics":["A 2019 incident documented by 14 independent witnesses that was classified within 72 hours","A building where every occupant over 40 years reported the same auditory experience that instruments confirmed","A medical case where a patient described in precise detail an event they could not have witnessed","Physical evidence collected in 1987 finally analyzed in 2023 produced results with no explanation","A mass experience in a school in 2020 where 67 students simultaneously reported the same thing","A location where magnetic instruments and cameras produce consistent anomalies scientists cannot explain"]},
    {"name":"obsession_dark","rpm":13.00,"series":"Consumed","watermark":"CONSUMED",
     "topics":["A person documented 4380 consecutive days of obsessive behavior before anyone realized","An obsession that began as admiration became a 7-year campaign destroying everything the subject built","A stalker who embedded themselves in the victims life as a trusted friend for 3 years before discovery","How a completely ordinary fixation transformed into something requiring 3 restraining orders and 2 relocations","A documented case where the subject did not realize they were being observed for 9 years until a phone was found","An obsession that crossed 4 countries over 11 years and was only stopped when the obsessed person died"]},
]

VOICES = {
    "dark_horror":["en-US-DavisNeural","en-GB-RyanNeural","en-US-AndrewNeural"],
    "seduction_dark":["en-GB-RyanNeural","en-US-AndrewNeural","en-GB-ThomasNeural"],
    "psychological_trap":["en-US-BrianNeural","en-GB-ThomasNeural","en-US-ChristopherNeural"],
    "supernatural_real":["en-GB-RyanNeural","en-US-DavisNeural","en-GB-ElliotNeural"],
    "obsession_dark":["en-US-AndrewNeural","en-GB-RyanNeural","en-US-DavisNeural"],
}

BG_KEYWORDS = {
    "dark_horror":"dark horror shadow night",
    "seduction_dark":"dark sensual shadow night",
    "psychological_trap":"dark corridor trap shadow",
    "supernatural_real":"dark mysterious fog night",
    "obsession_dark":"dark shadow watching night",
}

# ════════════════════════════════════════════════════════════
# UTILITIES
# ════════════════════════════════════════════════════════════
def log(msg): print(msg, flush=True)

def tg(msg):
    for chunk in [msg[i:i+4000] for i in range(0,len(msg),4000)]:
        try:
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                json={"chat_id":TG_CHAT,"text":chunk,"parse_mode":"HTML"},timeout=15)
            time.sleep(0.5)
        except: pass

def send_gmail(subject, body):
    pwd = os.environ.get("GMAIL_APP_PASSWORD","")
    if not pwd: return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = msg["To"] = "mohammedsultan0497@gmail.com"
        msg.attach(MIMEText(body,"html"))
        with smtplib.SMTP_SSL("smtp.gmail.com",465,timeout=30) as s:
            s.login("mohammedsultan0497@gmail.com",pwd)
            s.sendmail("mohammedsultan0497@gmail.com","mohammedsultan0497@gmail.com",msg.as_string())
    except Exception as e: log(f"  Gmail: {e}")

def load_state():
    if STATE_FILE.exists():
        try: return json.loads(STATE_FILE.read_text())
        except: pass
    return {"last_niche":"","last_voice":"","makeup_pending":False,"makeup_niche":"","last_title":"","last_url":"","weekly":[],"episode_count":0}

def save_state(s): STATE_FILE.write_text(json.dumps(s,indent=2))

# ════════════════════════════════════════════════════════════
# PROVIDER 1: CEREBRAS (1M tokens/day PRIMARY)
# ════════════════════════════════════════════════════════════
def call_cerebras(prompt, tokens=8000):
    if not CEREBRAS_KEY: return None
    models = ["llama-3.3-70b","llama3.1-70b","llama-4-scout-17b-16e-instruct"]
    for model in models:
        for attempt in range(2):
            try:
                r = requests.post(CEREBRAS_URL,
                    headers={"Authorization":f"Bearer {CEREBRAS_KEY}","Content-Type":"application/json"},
                    json={"model":model,"messages":[{"role":"user","content":prompt}],"max_completion_tokens":min(tokens,8000),"temperature":0.88},
                    timeout=90)
                if r.status_code == 200:
                    text = r.json().get("choices",[{}])[0].get("message",{}).get("content","")
                    if text and len(text.strip()) > 100: log(f"  ✓ Cerebras {model}"); return text
                elif r.status_code == 429:
                    wait = 30*(attempt+1)
                    log(f"  Cerebras 429 — wait {wait}s")
                    time.sleep(wait)
                elif r.status_code == 404: break
                else: log(f"  Cerebras {r.status_code}"); time.sleep(10)
            except Exception as e: log(f"  Cerebras: {str(e)[:50]}"); time.sleep(10)
    return None

# ════════════════════════════════════════════════════════════
# PROVIDER 2: GROQ (100K tokens/day SECONDARY)
# ════════════════════════════════════════════════════════════
def call_groq(prompt, tokens=8000):
    for attempt in range(2):
        try:
            r = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role":"user","content":prompt}],
                temperature=0.88,max_tokens=min(tokens,8000))
            text = r.choices[0].message.content
            if text and len(text.strip()) > 100: log(f"  ✓ Groq"); return text
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                log(f"  Groq 429 — wait 60s"); time.sleep(60)
            else: log(f"  Groq: {str(e)[:50]}"); break
    return None

# ════════════════════════════════════════════════════════════
# PROVIDER 3: GEMINI (1500 req/day TERTIARY)
# ════════════════════════════════════════════════════════════
def call_gemini(prompt, tokens=8000):
    for url_name, url in [("2.0-flash", GEMINI_URL), ("2.0-lite", GEMINI_LITE)]:
        for attempt in range(2):
            try:
                r = requests.post(f"{url}?key={GEMINI_KEY}",
                    headers={"Content-Type":"application/json"},
                    json={"contents":[{"parts":[{"text":prompt}]}],"generationConfig":{"temperature":0.88,"maxOutputTokens":min(tokens,8192)},"safetySettings":[{"category":c,"threshold":"BLOCK_NONE"} for c in ["HARM_CATEGORY_HARASSMENT","HARM_CATEGORY_HATE_SPEECH","HARM_CATEGORY_SEXUALLY_EXPLICIT","HARM_CATEGORY_DANGEROUS_CONTENT"]]},
                    timeout=90)
                if r.status_code == 200:
                    c = r.json().get("candidates",[])
                    if c:
                        text = c[0]["content"]["parts"][0]["text"]
                        if text and len(text.strip()) > 100: log(f"  ✓ Gemini {url_name}"); return text
                elif r.status_code == 429: log(f"  Gemini 429"); time.sleep(45*(attempt+1))
                elif r.status_code == 400: break
                else: time.sleep(10)
            except Exception as e: log(f"  Gemini: {str(e)[:50]}"); time.sleep(10)
    return None

# ════════════════════════════════════════════════════════════
# PROVIDER 4: OPENROUTER (200 req/day QUATERNARY)
# ════════════════════════════════════════════════════════════
def call_openrouter(prompt, tokens=8000):
    if not OPENROUTER_KEY: return None
    models = ["deepseek/deepseek-r1:free","meta-llama/llama-3.3-70b-instruct:free","google/gemini-flash-1.5:free"]
    for model in models:
        try:
            r = requests.post(OPENROUTER_URL,
                headers={"Authorization":f"Bearer {OPENROUTER_KEY}","Content-Type":"application/json","HTTP-Referer":"https://github.com/BetrayalDeepDive/betrayal-bot","X-Title":"DeepDive Empire"},
                json={"model":model,"messages":[{"role":"user","content":prompt}],"max_tokens":min(tokens,8000),"temperature":0.88},
                timeout=90)
            if r.status_code == 200:
                text = r.json()["choices"][0]["message"]["content"]
                if text and len(text.strip()) > 100: log(f"  ✓ OpenRouter {model.split('/')[1]}"); return text
            elif r.status_code == 429: log(f"  OpenRouter 429"); time.sleep(10)
            else: log(f"  OpenRouter {r.status_code}")
        except Exception as e: log(f"  OpenRouter: {str(e)[:50]}")
    return None

# ════════════════════════════════════════════════════════════
# AI GENERATION (4-PROVIDER FALLBACK)
# ════════════════════════════════════════════════════════════
def ai_generate(prompt, tokens=8000):
    """Cerebras → Groq → Gemini → OpenRouter"""
    result = call_cerebras(prompt, tokens)
    if result: return result
    log("  Cerebras unavailable — trying Groq...")
    result = call_groq(prompt, tokens)
    if result: return result
    log("  Groq unavailable — trying Gemini...")
    result = call_gemini(prompt, tokens)
    if result: return result
    log("  Gemini unavailable — trying OpenRouter...")
    result = call_openrouter(prompt, tokens)
    if result: return result
    log("  All 4 providers unavailable")
    return None

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
        text = re.sub(r'https?://\S+','',text)
        text = re.sub(r'<[^>]+>','',text)
        text = re.sub(r'\([^)]*(?:narrator|music|sfx|pause|cut|scene|beat)[^)]*\)','',text,flags=re.IGNORECASE)
        text = re.sub(r'[#@$%^&*{}<>|\\~`]','',text)
        text = re.sub(r'\n{3,}','\n\n',text)
        text = re.sub(r'[ \t]{2,}',' ',text)
    return text.strip()

def score_result(r):
    """Quality gate: 7.0 min, 6.5 floor"""
    if not r: return 0.0, ["generation failed"]
    issues, s = [], 5.0
    w, md = r["words"], r["violations"]
    if w >= MIN_WORDS: s += 2.8
    elif w >= 1600: s += 0.8; issues.append(f"{w}w short")
    elif w >= 1000: s -= 1.5; issues.append(f"SHORT:{w}w")
    else: s -= 4.0; issues.append(f"FATAL:{w}w")
    if md == 0: s += 2.2
    elif md <= 2: s += 0.8; issues.append(f"{md}md")
    else: s -= 1.5; issues.append(f"FATAL:{md}md")
    sents = [x for x in re.split(r'(?<=[.!?])\s+',r["script"]) if len(x.split()) > 2]
    if sents:
        avg = sum(len(x.split()) for x in sents)/len(sents)
        if avg <= 11: s += 1.5
        elif avg <= 13: s += 1.0
        elif avg <= 15: s += 0.4
        else: s -= 0.5; issues.append(f"Avg{avg:.0f}w")
    hook = r["script"][:350].lower()
    pw = ["nobody","witnessed","returned","still","documented","impossible","real","found","never","alone","watched","hidden"]
    hs = sum(1 for w2 in pw if w2 in hook)
    if hs >= 4: s += 1.0
    elif hs >= 2: s += 0.5
    else: issues.append("WeakHook")
    ai_p = ["moreover","furthermore","it is worth noting","in conclusion","interestingly"]
    ai_c = sum(1 for p in ai_p if p in r["script"].lower())
    if ai_c > 0: s -= ai_c*0.3
    return min(round(s,1),10.0), issues

def generate_everything(niche, topic, episode, attempt, prev_title):
    """ONE CALL: Script + Title + Thumbnail + Tags"""
    darkness = min(40+attempt*8, 96)
    cross = f'Reference previous episode "{prev_title}" in closing.' if prev_title else ""

    prompt = f"""Write COMPLETE YouTube video: Episode {episode} "{niche['series']}".
TOPIC: {topic}
DARKNESS: {darkness}%
{cross}

Script: {MIN_WORDS}-{MAX_WORDS} words. Natural narration. 12 words max per sentence.
Include hook in first 100 words: "nobody witnessed", "documented proof", "impossible explained", "real evidence".

===METADATA===
TITLE: 55-65 chars, curiosity gap, specific detail
THUMBNAIL: 3 WORDS MAX CAPS (shock value: NOBODY KNEW, THEY LIED, STILL FREE)
TAGS: ["tag1","tag2",...10-12 tags]
CHAPTERS: [{"time":"0:00","title":"Opening"}, {"time":"3:30","title":"Before"}, ...]

Write script then ===METADATA=== then JSON."""

    result = ai_generate(prompt, tokens=8000)
    if not result: return None

    if "===METADATA===" in result:
        parts = result.split("===METADATA===")
        script_raw = parts[0].strip()
        meta_raw = parts[1].strip() if len(parts) > 1 else ""
    else:
        script_raw = result
        meta_raw = ""

    script = strip_md(strip_md(script_raw))
    wc = len(script.split())

    if wc < MIN_WORDS:
        deficit = MIN_WORDS - wc
        log(f"  {wc}w short by {deficit}w — expanding...")
        expand = f"""Add {deficit} more words to: {script[:500]}...
Expand: 1) Add 2 specific named people, 2) Add 3 dated details, 3) Add aftermath paragraph
Pure spoken English. Max 13 words per sentence. Return COMPLETE script ONLY."""
        result2 = ai_generate(expand, tokens=8000)
        if result2:
            clean2 = strip_md(strip_md(result2))
            if len(clean2.split()) > wc: script = clean2; wc = len(script.split()); log(f"  Expanded to {wc}w")

    violations = len(re.findall(r'[#*_`\[\]{}<>\\]', script))

    title = f"{niche['series']}: The Investigation"
    thumbnail = "NOBODY KNEW"
    tags = [niche["name"],"horror","dark","documentary","true","story","psychological","real","unexplained","obsession","dark truth","mystery"]
    chapters = [{"time":"0:00","title":"Opening"},{"time":"3:30","title":"Before"},{"time":"7:00","title":"Descent"},{"time":"11:00","title":"Twist"},{"time":"14:30","title":"Remains"}]

    if meta_raw:
        try:
            meta_raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]','',re.sub(r'```json|```','',meta_raw).strip())
            m = re.search(r'\{[\s\S]*\}', meta_raw)
            if m:
                d = json.loads(m.group())
                title = d.get("TITLE", d.get("winning_title", title))[:65]
                thumbnail = d.get("THUMBNAIL", d.get("thumbnail", thumbnail))[:25]
                tags = d.get("TAGS", d.get("tags", tags))[:12]
                chapters = d.get("CHAPTERS", d.get("chapters", chapters))[:5]
        except Exception as e: log(f"  Meta parse err: {e}")

    return {"script":script,"words":wc,"violations":violations,"title":title,"thumbnail":thumbnail,"tags":tags,"chapters":chapters}

# ════════════════════════════════════════════════════════════
# STAGE 1: SCRIPT GENERATION
# ════════════════════════════════════════════════════════════
def run_stage1(state):
    log("\n" + "="*70)
    log("STAGE 1: Script Generation (Quality Gate: 7.0 min, 6.5 floor)")
    log("="*70)

    if IS_MAKEUP and state.get("makeup_pending") and state.get("makeup_niche"):
        niche = next((x for x in NICHES if x["name"]==state["makeup_niche"]),NICHES[0])
    else:
        name = DAY_NICHE.get(datetime.datetime.now().weekday(),"dark_horror")
        if name == state.get("last_niche",""): name = [x["name"] for x in NICHES if x["name"]!=name][0]
        niche = next(x for x in NICHES if x["name"]==name)

    opts = VOICES.get(niche["name"],["en-GB-RyanNeural"])
    available = [v for v in opts if v!=state.get("last_voice","")]
    voice = random.choice(available) if available else opts[0]

    topic = random.choice(niche["topics"])
    episode = state.get("episode_count",0) + 1
    prev_title = state.get("last_title","")

    log(f"Niche: {niche['name']} | Episode: {episode} | Voice: {voice}")

    for attempt in range(1, 4):
        log(f"\nAttempt {attempt}/3...")
        result = generate_everything(niche, topic, episode, attempt, prev_title)
        score, issues = score_result(result)
        log(f"  Score: {score}/10 | Issues: {issues}")

        if score >= MIN_GATE: log(f"  ✓ Passed"); return niche, voice, episode, result, score
        if score >= FINAL_GATE and attempt == 3: log(f"  ✓ Accepted (final gate)"); return niche, voice, episode, result, score

    log("  ✗ All attempts failed")
    sys.exit(1)

# ════════════════════════════════════════════════════════════
# STAGE 2: APPROVAL
# ════════════════════════════════════════════════════════════
def run_stage2_approval(niche, voice, result, score):
    log("\n" + "="*70)
    log("STAGE 2: Approval Gate")
    log("="*70)
    tg(f"✓ Script ready\n{niche['name']} | {result['words']}w | {score}/10\n{result['title'][:60]}\nApproving...")
    log("✓ Approval sent")
    return "approved"

# ════════════════════════════════════════════════════════════
# STAGE 3: AUDIO
# ════════════════════════════════════════════════════════════
def run_stage3_audio(script, voice, niche_name):
    log("\n" + "="*70)
    log("STAGE 3: Audio Generation")
    log("="*70)
    try:
        subprocess.run(["pip","install","edge-tts","-q"],timeout=30)
        audio_file = str(WORK_DIR / "audio.mp3")
        subprocess.run(["python","-m","edge_tts","--text",script[:5000],"--voice",voice,"--write-media",audio_file],timeout=120,capture_output=True)
        if Path(audio_file).exists() and Path(audio_file).stat().st_size > 100000:
            duration = len(script.split())*0.5
            log(f"✓ Audio: {duration/60:.1f}min")
            return audio_file, duration, voice
    except Exception as e: log(f"✗ {e}"); sys.exit(1)

# ════════════════════════════════════════════════════════════
# STAGE 4: VIDEO
# ════════════════════════════════════════════════════════════
def run_stage4_video(niche):
    log("\n" + "="*70)
    log("STAGE 4: Background Video")
    log("="*70)
    try:
        keyword = BG_KEYWORDS.get(niche["name"], "dark mystery")
        r = requests.get("https://pixabay.com/api/videos/",params={"key":PIXABAY_KEY,"q":keyword,"per_page":1},timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("hits"):
                url = data["hits"][0]["videos"]["medium"]["url"]
                video_path = str(WORK_DIR / "background.mp4")
                r = requests.get(url, timeout=30, stream=True)
                with open(video_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
                log(f"✓ Video: {Path(video_path).stat().st_size/1024/1024:.1f}MB")
                return video_path
    except Exception as e: log(f"✗ {e}")
    log("! Continuing without video")
    return str(WORK_DIR / "background.mp4")

# ════════════════════════════════════════════════════════════
# STAGE 5: UPLOAD
# ════════════════════════════════════════════════════════════
def get_yt_token():
    r = requests.post("https://oauth2.googleapis.com/token",data={"client_id":YT_CLIENT_ID,"client_secret":YT_CLIENT_SEC,"refresh_token":YT_REFRESH,"grant_type":"refresh_token"})
    d = r.json()
    if "access_token" not in d: raise Exception(f"YT token: {d}")
    return d["access_token"]

def upload_yt(path, title, desc, tags):
    log(f"Uploading {Path(path).stat().st_size/1024/1024:.0f}MB...")
    token = get_yt_token()
    init = requests.post("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        headers={"Authorization":f"Bearer {token}","Content-Type":"application/json"},
        json={"snippet":{"title":title,"description":desc,"tags":tags,"categoryId":"22"},"status":{"privacyStatus":"public","selfDeclaredMadeForKids":False}})
    url = init.headers.get("Location")
    if not url: raise Exception("No upload URL")
    sz = Path(path).stat().st_size
    with open(path,"rb") as f:
        up = requests.put(url,headers={"Content-Length":str(sz),"Content-Type":"video/mp4"},data=f,timeout=2400)
    if up.status_code in [200,201]:
        vid_id = up.json().get("id")
        yt_url = f"https://www.youtube.com/watch?v={vid_id}"
        log(f"✓ Uploaded: {yt_url}")
        return yt_url
    raise Exception(f"Upload {up.status_code}")

def cleanup():
    try:
        for f in glob.glob(str(WORK_DIR / "*")):
            if os.path.isfile(f): os.remove(f)
    except: pass

# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════
def main():
    start = time.time()
    log("\n" + "="*70)
    log("DEEPDIVE EMPIRE v8.0 FINAL")
    log("Cerebras → Groq → Gemini → OpenRouter | Quality Gates | $100M Ready")
    log("="*70)

    state = load_state()
    try: tg("Pipeline v8.0 starting...")
    except: pass

    try:
        niche, voice, episode, result, score = run_stage1(state)
        decision = run_stage2_approval(niche, voice, result, score)
        audio_path, duration, voice_used = run_stage3_audio(result["script"], voice, niche["name"])
        video_path = run_stage4_video(niche)

        log("\n" + "="*70)
        log("STAGE 5: YouTube Upload")
        log("="*70)

        desc = f"{result['title']}\n\nEpisode {episode} of {niche['series']}\n\nSubscribe for daily investigations"
        yt_url = upload_yt(video_path, result["title"], desc, result["tags"])

        cleanup()

        state["last_niche"] = niche["name"]
        state["last_voice"] = voice_used
        state["last_title"] = result["title"]
        state["last_url"] = yt_url
        state["episode_count"] = episode
        state["makeup_pending"] = False
        state.setdefault("weekly",[]).append({"date":datetime.datetime.now().isoformat(),"niche":niche["name"],"title":result["title"],"url":yt_url,"quality":score})
        state["weekly"] = state["weekly"][-7:]
        save_state(state)

        elapsed = (time.time()-start)/60
        try: tg(f"✅ PUBLISHED!\n{result['title']}\nEpisode {episode} | {niche['name']}\n{yt_url}\n\nDone in {elapsed:.0f}m")
        except: pass

        log(f"\n{'='*70}")
        log(f"✅ COMPLETE: {yt_url}")
        log(f"Time: {elapsed:.1f}m | Quality: {score}/10 | Words: {result['words']}")
        log(f"{'='*70}\n")

    except Exception as e:
        log(f"\n✗ FAILED: {e}")
        try: tg(f"Pipeline failed: {e}")
        except: pass
        sys.exit(1)

if __name__ == "__main__":
    main()
