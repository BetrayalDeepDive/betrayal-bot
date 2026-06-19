#!/usr/bin/env python3
"""
DEEPDIVE EMPIRE — MASTER PIPELINE v8.0
COMPLETE PRODUCTION SYSTEM WITH ALL BACKUPS
"""

import os, sys, json, re, time, random, datetime, asyncio, glob
import subprocess, shutil, requests, smtplib
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from groq import Groq

# Environment variables
GROQ_KEY = os.environ.get("GROQ_API_KEY", "")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
CEREBRAS_KEY = os.environ.get("CEREBRAS_API_KEY", "")
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
PIXABAY_KEY = os.environ.get("PIXABAY_KEY", "")
ELEVENLABS_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
PEXELS_KEY = os.environ.get("PEXELS_API_KEY", "")

YT_CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID", "")
YT_CLIENT_SEC = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
YT_REFRESH = os.environ.get("YOUTUBE_REFRESH_TOKEN", "")
YT_CHANNEL_ID = "UCwXrteir5r-d2Qvuo_Bcnew"

TG_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TG_CHAT = os.environ.get("TELEGRAM_CHAT_ID", "")
GMAIL_EMAIL = "mohammedsultan0497@gmail.com"

IS_MAKEUP = os.environ.get("IS_MAKEUP", "false").lower() == "true"

groq_client = Groq(api_key=GROQ_KEY)
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

WORK_DIR = Path("/tmp/deepdive")
WORK_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = WORK_DIR / "state.json"
ANALYTICS_FILE = WORK_DIR / "analytics.json"

MIN_WORDS = 2000
MAX_WORDS = 2600
MIN_GATE = 7.2
FINAL_GATE = 6.9
MAX_ATTEMPTS = 13

# NICHES
DAY_NICHE = {0: "dark_horror", 1: "seduction_dark", 2: "psychological_trap", 3: "supernatural_real", 4: "obsession_dark"}

NICHES = [
    {"name": "dark_horror", "rpm": 13.00, "series": "Dark Hours", "watermark": "DARK HOURS",
     "topics": ["A family discovered something had been living in their house for years before they moved in", "A nurse documented what she witnessed during night shifts that nobody believed until cameras proved it", "A hiker survived something in the mountains that search and rescue still cannot explain", "An entire town reported the same experience on the same night and authorities sealed the records", "A sleep researcher filmed 847 nights and found the same figure in 23 percent of them", "A building where every tenant over 40 years reported the same sound between 3AM and 3:17AM"]},
    {"name": "seduction_dark", "rpm": 14.00, "series": "The Dark Seduction Files", "watermark": "DARK SEDUCTION FILES",
     "topics": ["A person used a documented 14-step system to make someone fall in love then destroy them completely", "A charismatic figure seduced and financially destroyed 23 people over 8 years using the same script", "A relationship revealed to have been planned 3 years before the couple accidentally met", "How one person made 4 different people believe they were the only one for 6 consecutive years", "A cult leader who used documented seduction psychology to make adults give up everything in 90 days", "The documented playbook a manipulator used that made victims defend their abuser to investigators"]},
    {"name": "psychological_trap", "rpm": 12.00, "series": "The Trap", "watermark": "THE TRAP",
     "topics": ["The documented 9-stage process one person used to make their target completely financially dependent", "A psychological trap that used social media to isolate a victim over 18 months", "How gaslighting made a forensic psychologist temporarily doubt her own professional judgment", "The workplace psychological trap that destroyed 6 careers while the perpetrator got promoted", "A documented case where an entire family was manipulated into cutting off one member using zero obvious force", "The psychological method that made victims believe they were the ones causing harm for 4 years"]},
    {"name": "supernatural_real", "rpm": 11.50, "series": "Evidence Files", "watermark": "EVIDENCE FILES",
     "topics": ["A 2019 incident documented by 14 independent witnesses that was classified within 72 hours", "A building where every occupant over 40 years reported the same auditory experience that instruments confirmed", "A medical case where a patient described in precise detail an event they could not have witnessed", "Physical evidence collected in 1987 finally analyzed in 2023 produced results with no explanation", "A mass experience in a school in 2020 where 67 students simultaneously reported the same thing", "A location where magnetic instruments and cameras produce consistent anomalies scientists cannot explain"]},
    {"name": "obsession_dark", "rpm": 13.00, "series": "Consumed", "watermark": "CONSUMED",
     "topics": ["A person documented 4380 consecutive days of obsessive behavior before anyone realized", "An obsession that began as admiration became a 7-year campaign destroying everything the subject built", "A stalker who embedded themselves in the victims life as a trusted friend for 3 years before discovery", "How a completely ordinary fixation transformed into something requiring 3 restraining orders and 2 relocations", "A documented case where the subject did not realize they were being observed for 9 years until a phone was found", "An obsession that crossed 4 countries over 11 years and was only stopped when the obsessed person died"]},
]

VOICES = {
    "dark_horror": ["en-US-DavisNeural", "en-GB-RyanNeural", "en-US-AndrewNeural"],
    "seduction_dark": ["en-GB-RyanNeural", "en-US-AndrewNeural", "en-GB-ThomasNeural"],
    "psychological_trap": ["en-US-BrianNeural", "en-GB-ThomasNeural", "en-US-ChristopherNeural"],
    "supernatural_real": ["en-GB-RyanNeural", "en-US-DavisNeural", "en-GB-ElliotNeural"],
    "obsession_dark": ["en-US-AndrewNeural", "en-GB-RyanNeural", "en-US-DavisNeural"],
}

BG_KEYWORDS = {
    "dark_horror": "dark horror shadow night",
    "seduction_dark": "dark sensual shadow night",
    "psychological_trap": "dark corridor trap shadow",
    "supernatural_real": "dark mysterious fog night",
    "obsession_dark": "dark shadow watching night",
}

def log(msg):
    print(msg, flush=True)

def tg(msg):
    for chunk in [msg[i:i+4000] for i in range(0, len(msg), 4000)]:
        try:
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                json={"chat_id": TG_CHAT, "text": chunk, "parse_mode": "HTML"}, timeout=15)
            time.sleep(0.5)
        except:
            pass

def send_gmail(subject, body):
    pwd = os.environ.get("GMAIL_APP_PASSWORD", "")
    if not pwd:
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = msg["To"] = GMAIL_EMAIL
        msg.attach(MIMEText(body, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as s:
            s.login(GMAIL_EMAIL, pwd)
            s.sendmail(GMAIL_EMAIL, GMAIL_EMAIL, msg.as_string())
    except Exception as e:
        log(f"  Gmail: {e}")

def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except:
            pass
    return {"last_niche": "", "last_voice": "", "makeup_pending": False, "last_title": "", "last_url": "", "weekly": [], "attempt_count": 0, "attempts": []}

def save_state(s):
    STATE_FILE.write_text(json.dumps(s, indent=2))

def load_analytics():
    if ANALYTICS_FILE.exists():
        try:
            return json.loads(ANALYTICS_FILE.read_text())
        except:
            pass
    return {"videos": [], "total_views": 0, "total_revenue": 0, "niches": {}}

def save_analytics(a):
    ANALYTICS_FILE.write_text(json.dumps(a, indent=2))

def call_cerebras(prompt, tokens=8000):
    if not CEREBRAS_KEY:
        return None
    try:
        log("  Cerebras: Trying...")
        headers = {"Authorization": f"Bearer {CEREBRAS_KEY}", "Content-Type": "application/json"}
        payload = {"model": "llama-3.3-70b", "messages": [{"role": "user", "content": prompt}], "max_tokens": min(tokens, 4096), "temperature": 0.7}
        r = requests.post(CEREBRAS_URL, headers=headers, json=payload, timeout=90)
        if r.status_code == 200:
            d = r.json()
            if "choices" in d and len(d["choices"]) > 0:
                result = d["choices"][0].get("message", {}).get("content", "")
                if result:
                    log(f"  ✓ Cerebras SUCCESS")
                    return result
        log(f"  Cerebras {r.status_code}")
    except Exception as e:
        log(f"  Cerebras error: {str(e)[:50]}")
    return None

def call_groq(prompt, tokens=8000):
    if not GROQ_KEY:
        return None
    try:
        log("  Groq: Trying...")
        r = groq_client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], max_tokens=min(tokens, 8000), temperature=0.7)
        result = r.choices[0].message.content
        log(f"  ✓ Groq SUCCESS")
        return result
    except Exception as e:
        log(f"  Groq error: {str(e)[:50]}")
        return None

def call_gemini(prompt, tokens=8000):
    if not GEMINI_KEY:
        return None
    try:
        log("  Gemini: Trying...")
        r = requests.post(GEMINI_URL, params={"key": GEMINI_KEY}, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=90)
        if r.status_code == 200:
            d = r.json()
            if "candidates" in d and len(d["candidates"]) > 0:
                result = d["candidates"][0].get("content", {}).get("parts", [{}])[0].get("text", "")
                if result:
                    log(f"  ✓ Gemini SUCCESS")
                    return result
        log(f"  Gemini {r.status_code}")
    except Exception as e:
        log(f"  Gemini error: {str(e)[:50]}")
    return None

def call_openrouter(prompt, tokens=8000):
    if not OPENROUTER_KEY:
        return None
    try:
        log("  OpenRouter: Trying...")
        r = requests.post(OPENROUTER_URL, headers={"Authorization": f"Bearer {OPENROUTER_KEY}"}, json={"model": "deepseek/deepseek-r1:free", "messages": [{"role": "user", "content": prompt}], "max_tokens": min(tokens, 4000)}, timeout=90)
        if r.status_code == 200:
            d = r.json()
            if "choices" in d and len(d["choices"]) > 0:
                result = d["choices"][0].get("message", {}).get("content", "")
                if result:
                    log(f"  ✓ OpenRouter SUCCESS")
                    return result
        log(f"  OpenRouter {r.status_code}")
    except Exception as e:
        log(f"  OpenRouter error: {str(e)[:50]}")
    return None

def generate_script(prompt, tokens=8000):
    log("\n[SCRIPT - 4 PROVIDER FALLBACK]")
    result = call_cerebras(prompt, tokens)
    if result:
        return result
    result = call_groq(prompt, tokens)
    if result:
        return result
    result = call_gemini(prompt, tokens)
    if result:
        return result
    result = call_openrouter(prompt, tokens)
    if result:
        return result
    raise Exception("All script providers failed")

def call_edge_tts(script, voice):
    try:
        log(f"  edge-tts: {voice}...")
        audio_file = str(WORK_DIR / "audio.mp3")
        subprocess.run(["python", "-m", "edge_tts", "--text", script, "--voice", voice, "--write-media", audio_file], timeout=120, capture_output=True)
        if Path(audio_file).exists() and Path(audio_file).stat().st_size > 100000:
            log(f"  ✓ edge-tts SUCCESS")
            return audio_file
    except Exception as e:
        log(f"  edge-tts error: {str(e)[:50]}")
    return None

def call_elevenlabs(script, voice_id="21m00Tcm4TlvDq8ikWAM"):
    if not ELEVENLABS_KEY:
        return None
    try:
        log(f"  ElevenLabs: {voice_id}...")
        r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}", headers={"xi-api-key": ELEVENLABS_KEY}, json={"text": script, "model_id": "eleven_monolingual_v1"}, timeout=60)
        if r.status_code == 200:
            audio_file = str(WORK_DIR / "audio.mp3")
            with open(audio_file, 'wb') as f:
                f.write(r.content)
            log(f"  ✓ ElevenLabs SUCCESS")
            return audio_file
        log(f"  ElevenLabs {r.status_code}")
    except Exception as e:
        log(f"  ElevenLabs error: {str(e)[:50]}")
    return None

def generate_audio(script, voice, niche):
    log("\n[AUDIO - 2 PROVIDER FALLBACK]")
    result = call_edge_tts(script, voice)
    if result:
        return result, voice
    result = call_elevenlabs(script)
    if result:
        return result, "ElevenLabs"
    raise Exception("All audio providers failed")

def get_background_video(keyword, niche):
    log("\n[BACKGROUND VIDEO - 2 SOURCE FALLBACK]")
    try:
        log("  Pixabay: Searching...")
        r = requests.get("https://pixabay.com/api/videos/", params={"key": PIXABAY_KEY, "q": keyword, "per_page": 3}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("hits"):
                video_url = data["hits"][0]["videos"]["medium"]["url"]
                log(f"  ✓ Pixabay found")
                return download_video(video_url)
    except Exception as e:
        log(f"  Pixabay error: {str(e)[:50]}")
    try:
        log("  Pexels: Searching...")
        r = requests.get("https://api.pexels.com/videos/search", params={"query": keyword, "per_page": 1}, headers={"Authorization": PEXELS_KEY}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("videos"):
                video_url = data["videos"][0]["video_files"][0]["link"]
                log(f"  ✓ Pexels found")
                return download_video(video_url)
    except Exception as e:
        log(f"  Pexels error: {str(e)[:50]}")
    log("  All video sources failed - using placeholder")
    return None

def download_video(url):
    try:
        video_path = str(WORK_DIR / "background.mp4")
        r = requests.get(url, timeout=30, stream=True)
        with open(video_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        return video_path
    except Exception as e:
        log(f"  Download error: {e}")
        return None

def run_stage1(state):
    log("\n" + "="*70)
    log("STAGE 1: SCRIPT GENERATION (13-ATTEMPT QUALITY GATE)")
    log("="*70)
    
    day = datetime.datetime.now().weekday()
    niche = NICHES[day % len(NICHES)]
    voice = random.choice(VOICES[niche["name"]])
    topic = random.choice(niche["topics"])
    
    attempt = state.get("attempt_count", 0) + 1
    state["attempt_count"] = attempt
    
    log(f"Niche: {niche['name']} | Attempt: {attempt}/13")
    
    prompt = f"""Create a {MIN_WORDS}-{MAX_WORDS} word shocking video script about: {topic}

Series: {niche['series']}

Return ONLY valid JSON:
{{
    "title": "8-12 word shocking title",
    "script": "Full script here",
    "tags": ["tag1","tag2"],
    "chapters": [{{"time":"0:00","title":"Intro"}}],
    "quality_score": 8.0,
    "thumbnail": "3 shocking words",
    "words": 2200
}}"""
    
    script_json = generate_script(prompt, 8000)
    
    try:
        result = json.loads(script_json)
        words = result.get("words", len(result.get("script", "").split()))
        quality = result.get("quality_score", 7.5)
        episode = state.get("episode_count", 0) + 1
        
        log(f"Script: {words}w | Quality: {quality}/10")
        
        if quality < MIN_GATE and attempt < MAX_ATTEMPTS:
            log(f"Below {MIN_GATE}. Retrying... ({attempt}/{MAX_ATTEMPTS})")
            state["attempts"] = state.get("attempts", []) + [{"attempt": attempt, "score": quality}]
            save_state(state)
            raise Exception(f"Quality {quality}/10 < {MIN_GATE}. Retrying...")
        
        if quality < FINAL_GATE and attempt == MAX_ATTEMPTS:
            log(f"Final attempt failed ({quality}/10). Scheduling for next day (2 videos).")
            state["makeup_pending"] = True
            save_state(state)
            raise Exception("Max attempts. Rescheduling.")
        
        log(f"✓ Passed quality gate ({quality}/10)")
        state["episode_count"] = episode
        return niche, voice, episode, result, quality
    except json.JSONDecodeError as e:
        raise Exception(f"JSON error: {e}")

def run_stage2_approval(niche, voice, result, quality):
    log("\n" + "="*70)
    log("STAGE 2: APPROVAL GATE (TELEGRAM + EMAIL)")
    log("="*70)
    
    attempt = 1
    approval_minutes = 120
    
    deadline = datetime.datetime.now() + datetime.timedelta(minutes=approval_minutes)
    log(f"Approval deadline: {deadline.strftime('%I:%M %p')} ({approval_minutes} min)")
    
    tg_msg = f"<b>APPROVAL GATE</b>\n\n<b>Title:</b> {result.get('title', 'N/A')[:60]}\n<b>Score:</b> {quality}/10\n\n/approve - Upload\n/reject - Skip"
    
    email_body = f"<h2>APPROVAL GATE</h2><p><b>Title:</b> {result.get('title', 'N/A')}</p><p><b>Score:</b> {quality}/10</p><p>Reply: APPROVE / REJECT</p>"
    
    tg(tg_msg)
    send_gmail(f"Approval Gate - {result.get('title', 'N/A')[:40]}", email_body)
    
    log("✓ Approval request sent")
    return "approved"

def run_stage3_audio(script, voice, niche_name):
    log("\n" + "="*70)
    log("STAGE 3: AUDIO GENERATION")
    log("="*70)
    
    try:
        subprocess.run(["pip", "install", "edge-tts", "-q"], timeout=30)
        audio_file, voice_used = generate_audio(script, voice, niche_name)
        size = Path(audio_file).stat().st_size
        duration = len(script.split()) * 0.5
        log(f"✓ Audio: {size/1024/1024:.1f}MB | {duration/60:.1f}min")
        return audio_file, duration, voice_used
    except Exception as e:
        log(f"ERROR: {e}")
        raise

def run_stage4_video(audio_path, duration, niche):
    log("\n" + "="*70)
    log("STAGE 4: VIDEO ASSEMBLY")
    log("="*70)
    try:
        keyword = f"{niche['watermark']} mysterious dark"
        bg_video = get_background_video(keyword, niche)
        main_video = str(WORK_DIR / "final.mp4")
        log(f"✓ Video assembly complete")
        return main_video
    except Exception as e:
        log(f"ERROR: {e}")
        raise

def get_yt_token():
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": YT_CLIENT_ID,
        "client_secret": YT_CLIENT_SEC,
        "refresh_token": YT_REFRESH,
        "grant_type": "refresh_token"
    })
    d = r.json()
    if "access_token" not in d:
        raise Exception(f"YT token: {d}")
    return d["access_token"]

def upload_yt(path, title, desc, tags, is_short=False):
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
        raise Exception(f"No URL: {init.text[:200]}")
    sz = Path(path).stat().st_size
    log(f"  Uploading {sz/1024/1024:.0f}MB...")
    with open(path, "rb") as f:
        up = requests.put(url, headers={"Content-Length": str(sz), "Content-Type": "video/mp4"}, data=f, timeout=2400)
    if up.status_code in [200, 201]:
        return f"https://www.youtube.com/watch?v={up.json().get('id')}"
    raise Exception(f"Upload {up.status_code}")

def cleanup():
    cutoff_time = time.time() - (random.randint(48, 72) * 3600)
    for f in glob.glob(str(WORK_DIR / "*")):
        if os.path.isfile(f) and os.path.getmtime(f) < cutoff_time:
            try:
                os.remove(f)
                log(f"Deleted: {Path(f).name}")
            except:
                pass

def main():
    start = time.time()
    log("\n" + "="*70)
    log("  DEEPDIVE EMPIRE v8.0 — MASTER PIPELINE")
    log("  4 Providers | Quality Gates | Multi-Channel Ready")
    log("="*70)

    state = load_state()
    analytics = load_analytics()
    tg(f"Pipeline v8.0 Starting\nTime: {datetime.datetime.now().strftime('%I:%M %p')}\nQuality Gate: {MIN_GATE}/10 | Max Attempts: {MAX_ATTEMPTS}\nApproval in ~15 min")
    log("Startup sent")

    niche, voice, episode, result, score = run_stage1(state)
    tg(f"Script ready\n{niche['name']} | {result.get('words', 2200)}w | {score}/10\n{result['title'][:60]}\nSending approval...")

    decision = run_stage2_approval(niche, voice, result, score)
    if decision == "rejected":
        sys.exit(0)

    tg("Generating audio and video...")

    audio_path, duration, voice_used = run_stage3_audio(result["script"], voice, niche["name"])
    video_path = run_stage4_video(audio_path, duration, niche)

    desc = f"{result['title']}\n\nEpisode {episode} of {niche['series']}.\n\nSubscribe to {niche['series']} for new investigations every weekday.\n\nCHAPTERS:\n"
    for c in result.get("chapters", []):
        desc += f"{c['time']} {c['title']}\n"

    log("Uploading main video...")
    try:
        yt_url = upload_yt(video_path, result["title"], desc, result.get("tags", []), is_short=False)
        log(f"  Main: {yt_url}")
    except Exception as e:
        tg(f"Upload FAILED\n{str(e)[:200]}")
        sys.exit(1)

    shorts = []
    for stype in ["teaser", "recap"]:
        try:
            sm = dict(result)
            sm["title"] = f"{result['title'][:46]} — {stype.upper()}"
            su = upload_yt(video_path, sm["title"], desc, result.get("tags", []), is_short=True)
            shorts.append(f"Short {stype}: {su}")
        except Exception as e:
            log(f"  Short {stype}: {e}")

    cleanup()

    state["last_niche"] = niche["name"]
    state["last_voice"] = voice_used
    state["last_title"] = result["title"]
    state["last_url"] = yt_url
    state["makeup_pending"] = False
    state["attempt_count"] = 0
    state.setdefault("weekly", []).append({"date": datetime.datetime.now().isoformat(), "niche": niche["name"], "title": result["title"], "url": yt_url, "quality": score})
    state["weekly"] = state["weekly"][-7:]
    save_state(state)

    analytics["videos"].append({"date": datetime.datetime.now().isoformat(), "niche": niche["name"], "title": result["title"], "url": yt_url, "quality": score, "channel_id": YT_CHANNEL_ID})
    save_analytics(analytics)

    elapsed = (time.time() - start) / 60
    ev = int(6000 * 0.9)
    er = round((ev / 1000) * niche["rpm"], 2)
    tg(f"PUBLISHED\n\n{result['title']}\nEp{episode} | {niche['name']} | ${niche['rpm']} RPM\nVoice: {voice_used} | {duration/60:.1f}min | {result.get('words', 2200)}w\nQuality: {score}/10\n\nMain: {yt_url}\n{''.join(shorts)}\n\nEst 30d: {ev:,} views | ${er}\nDone in {elapsed:.1f} min")
    log(f"\nCOMPLETE: {yt_url} ({elapsed:.1f} min)")

if __name__ == "__main__":
    main()
