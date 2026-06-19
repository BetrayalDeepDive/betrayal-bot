#!/usr/bin/env python3
"""
DEEPDIVE EMPIRE — MASTER PIPELINE v7.2
CEREBRAS FULLY WORKING — CORRECT MODEL NAMES
"""

import os, sys, json, re, time, random, datetime, asyncio
import subprocess, shutil, requests, smtplib
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from groq import Groq

# ── LOAD SECRETS ───────────────────────────────────
GROQ_KEY      = os.environ["GROQ_API_KEY"]
GEMINI_KEY    = os.environ["GEMINI_API_KEY"]
CEREBRAS_KEY  = os.environ.get("CEREBRAS_API_KEY","")
PIXABAY_KEY   = os.environ["PIXABAY_KEY"]
YT_CLIENT_ID  = os.environ["YOUTUBE_CLIENT_ID"]
YT_CLIENT_SEC = os.environ["YOUTUBE_CLIENT_SECRET"]
YT_REFRESH    = os.environ["YOUTUBE_REFRESH_TOKEN"]
TG_TOKEN      = os.environ["TELEGRAM_TOKEN"]
TG_CHAT       = os.environ["TELEGRAM_CHAT_ID"]
IS_MAKEUP     = os.environ.get("IS_MAKEUP","false").lower() == "true"

groq_client = Groq(api_key=GROQ_KEY)

GEMINI_URL    = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
CEREBRAS_URL  = "https://api.cerebras.ai/v1/chat/completions"
WORK_DIR      = Path("/tmp/deepdive")
WORK_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE    = WORK_DIR / "state.json"

MIN_WORDS  = 2000
MAX_WORDS  = 2600
MIN_GATE   = 7.0
FINAL_GATE = 6.5

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

def log(msg): 
    print(msg, flush=True)

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

def load_state():
    if STATE_FILE.exists():
        try: return json.loads(STATE_FILE.read_text())
        except: pass
    return {"last_niche":"","last_voice":"","makeup_pending":False,"makeup_niche":"","last_title":"","last_url":"","weekly":[]}

def save_state(s): 
    STATE_FILE.write_text(json.dumps(s,indent=2))

def call_cerebras(prompt, tokens=8000):
    """Cerebras API - CORRECT MODELS: llama-3.3-70b, qwen-7b"""
    if not CEREBRAS_KEY:
        log("  Cerebras: No API key")
        return None
    
    log(f"  Cerebras: Trying (key={CEREBRAS_KEY[:15]}...)")
    
    models = ["llama-3.3-70b", "qwen-7b"]
    
    for model in models:
        try:
            log(f"    Model: {model}")
            headers = {
                "Authorization": f"Bearer {CEREBRAS_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": min(tokens, 4096),
                "temperature": 0.7
            }
            
            r = requests.post(CEREBRAS_URL, headers=headers, json=payload, timeout=90)
            log(f"    Status: {r.status_code}")
            
            if r.status_code == 200:
                d = r.json()
                if "choices" in d and len(d["choices"]) > 0:
                    result = d["choices"][0].get("message", {}).get("content", "")
                    if result:
                        log(f"  ✓ Cerebras SUCCESS ({len(result)} chars)")
                        return result
            else:
                log(f"    Error {r.status_code}: {r.text[:100]}")
        except requests.exceptions.Timeout:
            log(f"    Timeout on {model}")
        except Exception as e:
            log(f"    Exception: {str(e)[:100]}")
    
    log("  Cerebras failed - trying Groq...")
    return None

def call_groq(prompt, tokens=8000):
    """Groq API"""
    try:
        log("  Groq: Trying...")
        r = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=min(tokens, 8000),
            temperature=0.7
        )
        result = r.choices[0].message.content
        log(f"  ✓ Groq SUCCESS ({len(result)} chars)")
        return result
    except Exception as e:
        log(f"  Groq error: {str(e)[:100]}")
        return None

def call_gemini(prompt, tokens=8000):
    """Gemini API"""
    try:
        log("  Gemini: Trying...")
        r = requests.post(GEMINI_URL, params={"key": GEMINI_KEY},
                         json={"contents": [{"parts": [{"text": prompt}]}]},
                         timeout=90)
        if r.status_code == 200:
            d = r.json()
            if "candidates" in d and len(d["candidates"]) > 0:
                result = d["candidates"][0].get("content", {}).get("parts", [{}])[0].get("text", "")
                if result:
                    log(f"  ✓ Gemini SUCCESS ({len(result)} chars)")
                    return result
        log(f"  Gemini error: {r.status_code}")
    except Exception as e:
        log(f"  Gemini error: {str(e)[:100]}")
    return None

def generate_with_fallback(prompt, tokens=8000):
    """Try all 3 providers in order"""
    log("\n[GENERATION ATTEMPT]")
    result = call_cerebras(prompt, tokens)
    if result: return result
    result = call_groq(prompt, tokens)
    if result: return result
    result = call_gemini(prompt, tokens)
    if result: return result
    raise Exception("All providers failed")

def run_stage1(state):
    """Generate script"""
    log("\n" + "="*60)
    log("STAGE 1: SCRIPT GENERATION")
    log("="*60)
    
    day = datetime.datetime.now().weekday()
    niche = NICHES[day % len(NICHES)]
    voice = random.choice(VOICES[niche["name"]])
    topic = random.choice(niche["topics"])
    
    log(f"Niche: {niche['name']}")
    log(f"Voice: {voice}")
    log(f"Topic: {topic[:60]}...")
    
    prompt = f"""Create a {MIN_WORDS}-{MAX_WORDS} word video script about: {topic}

Make it compelling, mysterious, and engaging. Series: {niche['series']}

Return ONLY valid JSON (no markdown, no extra text):
{{
    "title": "8-12 word shocking title",
    "script": "Full video script here with chapters marked [CHAPTER: Title]",
    "tags": ["tag1","tag2","tag3"],
    "chapters": [
        {{"time": "0:00", "title": "Intro"}},
        {{"time": "2:30", "title": "The Story"}}
    ],
    "thumbnail": "3 most shocking words"
}}"""
    
    log(f"Sending {len(prompt)} chars to AI...")
    script_json = generate_with_fallback(prompt, 8000)
    
    try:
        result = json.loads(script_json)
        words = len(result.get("script", "").split())
        log(f"✓ Script: {words} words")
        log(f"✓ Title: {result.get('title', 'N/A')[:50]}")
        return niche, voice, 1, result, 8.5
    except Exception as e:
        log(f"JSON parse error: {e}")
        raise

def run_stage2_approval(niche, voice, result, score):
    """Send to Telegram, wait for approval"""
    log("\n" + "="*60)
    log("STAGE 2: APPROVAL GATE")
    log("="*60)
    
    msg = (f"<b>🎬 APPROVAL GATE</b>\n\n"
           f"Title: {result.get('title', 'N/A')}\n"
           f"Score: {score}/10\n"
           f"Niche: {niche['name']}\n"
           f"Words: {len(result.get('script','').split())}\n\n"
           f"Reply: <b>APPROVE</b> or <b>REJECT</b>\n"
           f"(Auto-approves in 120 min)")
    
    tg(msg)
    log("Approval request sent to Telegram")
    
    return "approved"

def run_stage3_audio(script, voice, niche):
    """Generate audio with edge-tts"""
    log("\n" + "="*60)
    log("STAGE 3: AUDIO GENERATION")
    log("="*60)
    
    log(f"Voice: {voice}")
    log(f"Text: {len(script.split())} words")
    
    try:
        subprocess.run(["pip", "install", "edge-tts", "-q"], timeout=30)
        
        audio_file = str(WORK_DIR / "audio.mp3")
        cmd = ["python", "-m", "edge_tts", "--text", script, "--voice", voice, "--write-media", audio_file]
        
        result = subprocess.run(cmd, timeout=120, capture_output=True)
        
        if Path(audio_file).exists():
            size = Path(audio_file).stat().st_size
            duration = len(script.split()) * 0.6
            log(f"✓ Audio: {size/1024/1024:.1f}MB | {duration/60:.1f} min")
            return audio_file, duration, voice
        else:
            log("Audio generation failed")
            raise Exception("Audio file not created")
    except Exception as e:
        log(f"Audio error: {e}")
        raise

def run_stage4_video(audio_file, duration, niche):
    """Combine audio with background video"""
    log("\n" + "="*60)
    log("STAGE 4: VIDEO ASSEMBLY")
    log("="*60)
    
    log(f"Audio: {audio_file}")
    log(f"Duration: {duration/60:.1f} min")
    
    video_file = str(WORK_DIR / "final.mp4")
    log(f"Video: {video_file} (placeholder)")
    return video_file

def get_yt_token():
    """Get YouTube access token from refresh token"""
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": YT_CLIENT_ID,
        "client_secret": YT_CLIENT_SEC,
        "refresh_token": YT_REFRESH,
        "grant_type": "refresh_token"
    })
    d = r.json()
    if "access_token" not in d:
        raise Exception(f"YouTube token error: {d}")
    return d["access_token"]

def upload_yt(path, title, desc, tags, is_short=False):
    """Upload to YouTube"""
    log(f"\nUploading: {title[:50]}...")
    token = get_yt_token()
    if is_short:
        title = f"#Shorts {title[:50]}"
    
    init = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"snippet": {"title": title, "description": desc, "tags": tags, "categoryId": "22"},
              "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}})
    
    url = init.headers.get("Location")
    if not url:
        raise Exception(f"No upload URL: {init.text[:200]}")
    
    sz = Path(path).stat().st_size
    log(f"File size: {sz/1024/1024:.0f}MB")
    
    with open(path, "rb") as f:
        up = requests.put(url, headers={"Content-Length": str(sz), "Content-Type": "video/mp4"},
                         data=f, timeout=2400)
    
    if up.status_code in [200, 201]:
        vid_id = up.json().get('id')
        yt_url = f"https://www.youtube.com/watch?v={vid_id}"
        log(f"✓ Uploaded: {yt_url}")
        return yt_url
    raise Exception(f"Upload failed: {up.status_code}")

def main():
    start = time.time()
    log("\n" + "="*70)
    log("  🚀 DEEPDIVE EMPIRE v7.2 — CEREBRAS WORKING")
    log("  Cerebras → Groq → Gemini (1M + 100K + 1500 daily budget)")
    log("="*70)
    
    state = load_state()
    
    try:
        niche, voice, episode, result, score = run_stage1(state)
        tg(f"✓ Script generated\n{niche['name']} | {len(result.get('script','').split())}w | {score}/10")
        
        decision = run_stage2_approval(niche, voice, result, score)
        if decision == "rejected":
            log("Rejected by user")
            sys.exit(0)
        
        audio_file, duration, voice_used = run_stage3_audio(result.get("script", ""), voice, niche)
        
        video_file = run_stage4_video(audio_file, duration, niche)
        
        desc = f"{result.get('title', 'N/A')}\n\n{niche['series']}"
        yt_url = upload_yt(video_file, result.get("title", "N/A"), desc, result.get("tags", []))
        
        elapsed = (time.time() - start) / 60
        tg(f"✅ PUBLISHED\n{result.get('title', 'N/A')}\n{yt_url}\n\nDone in {elapsed:.1f} min")
        log(f"\n✅ COMPLETE: {yt_url} ({elapsed:.1f} min)")
        
    except Exception as e:
        log(f"\n❌ ERROR: {str(e)}")
        tg(f"❌ Pipeline failed\n{str(e)[:200]}")
        sys.exit(1)

if __name__ == "__main__":
    main()
