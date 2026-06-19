#!/usr/bin/env python3
"""
DEEPDIVE EMPIRE v8.0
NO JSON PARSING - BULLETPROOF - WILL WORK
"""

import os, sys, json, re, time, random, datetime, glob
import subprocess, shutil, requests, smtplib
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from groq import Groq

GROQ_KEY = os.environ.get("GROQ_API_KEY", "")
PIXABAY_KEY = os.environ.get("PIXABAY_KEY", "")

YT_CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID", "")
YT_CLIENT_SEC = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
YT_REFRESH = os.environ.get("YOUTUBE_REFRESH_TOKEN", "")

TG_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TG_CHAT = os.environ.get("TELEGRAM_CHAT_ID", "")
GMAIL_EMAIL = "mohammedsultan0497@gmail.com"

groq_client = Groq(api_key=GROQ_KEY)

WORK_DIR = Path("/tmp/deepdive")
WORK_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = WORK_DIR / "state.json"

NICHES = [
    {"name": "dark_horror", "rpm": 13.00, "series": "Dark Hours", "watermark": "DARK HOURS",
     "topics": ["A family discovered something had been living in their house for years before they moved in", "A nurse documented what she witnessed during night shifts that nobody believed until cameras proved it"]},
    {"name": "seduction_dark", "rpm": 14.00, "series": "The Dark Seduction Files", "watermark": "DARK SEDUCTION FILES",
     "topics": ["A person used a documented 14-step system to make someone fall in love then destroy them completely", "A charismatic figure seduced and financially destroyed 23 people over 8 years using the same script"]},
    {"name": "psychological_trap", "rpm": 12.00, "series": "The Trap", "watermark": "THE TRAP",
     "topics": ["The documented 9-stage process one person used to make their target completely financially dependent", "A psychological trap that used social media to isolate a victim over 18 months"]},
    {"name": "supernatural_real", "rpm": 11.50, "series": "Evidence Files", "watermark": "EVIDENCE FILES",
     "topics": ["A 2019 incident documented by 14 independent witnesses that was classified within 72 hours", "A building where every occupant over 40 years reported the same auditory experience that instruments confirmed"]},
    {"name": "obsession_dark", "rpm": 13.00, "series": "Consumed", "watermark": "CONSUMED",
     "topics": ["A person documented 4380 consecutive days of obsessive behavior before anyone realized", "An obsession that began as admiration became a 7-year campaign destroying everything the subject built"]},
]

VOICES = {
    "dark_horror": ["en-US-DavisNeural", "en-GB-RyanNeural"],
    "seduction_dark": ["en-GB-RyanNeural", "en-US-AndrewNeural"],
    "psychological_trap": ["en-US-BrianNeural", "en-GB-ThomasNeural"],
    "supernatural_real": ["en-GB-RyanNeural", "en-US-DavisNeural"],
    "obsession_dark": ["en-US-AndrewNeural", "en-GB-RyanNeural"],
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
    except:
        pass

def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except:
            pass
    return {"episode_count": 0, "last_url": "", "weekly": []}

def save_state(s):
    STATE_FILE.write_text(json.dumps(s, indent=2))

def generate_script(topic, series):
    """Generate script - NO JSON PARSING"""
    log("  Generating script...")
    try:
        prompt = f"""Write a 2000-2600 word shocking video script about: {topic}

For series: {series}

Write ONLY the script content. No JSON. No formatting. Just the script text."""
        
        r = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
            temperature=0.7
        )
        script = r.choices[0].message.content.strip()
        if len(script) > 500:
            log(f"  ✓ Script OK ({len(script)} chars)")
            return script
    except Exception as e:
        log(f"  ✗ Error: {e}")
    
    raise Exception("Script generation failed")

def generate_audio(script, voice):
    log("  Generating audio...")
    try:
        audio_file = str(WORK_DIR / "audio.mp3")
        subprocess.run(
            ["python", "-m", "edge_tts", "--text", script[:3000], "--voice", voice, "--write-media", audio_file],
            timeout=120,
            capture_output=True
        )
        if Path(audio_file).exists() and Path(audio_file).stat().st_size > 50000:
            log(f"  ✓ Audio OK")
            return audio_file
    except Exception as e:
        log(f"  ✗ Error: {e}")
    
    raise Exception("Audio generation failed")

def get_background_video():
    log("  Getting background video...")
    try:
        r = requests.get("https://pixabay.com/api/videos/", 
            params={"key": PIXABAY_KEY, "q": "dark mystery", "per_page": 1}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("hits"):
                url = data["hits"][0]["videos"]["medium"]["url"]
                video_path = str(WORK_DIR / "background.mp4")
                r = requests.get(url, timeout=30, stream=True)
                with open(video_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                log(f"  ✓ Video OK")
                return video_path
    except Exception as e:
        log(f"  ✗ Error: {e}")
    
    log("  ! Continuing without background video")
    return str(WORK_DIR / "background.mp4")

def upload_youtube(video_path, title, description):
    log("  Uploading to YouTube...")
    try:
        r = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": YT_CLIENT_ID,
            "client_secret": YT_CLIENT_SEC,
            "refresh_token": YT_REFRESH,
            "grant_type": "refresh_token"
        })
        token = r.json().get("access_token")
        if not token:
            raise Exception("YouTube auth failed")
        
        init = requests.post(
            "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "snippet": {"title": title, "description": description, "tags": ["investigation"], "categoryId": "22"},
                "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
            }
        )
        
        url = init.headers.get("Location")
        if not url:
            raise Exception("No upload URL")
        
        sz = Path(video_path).stat().st_size
        with open(video_path, "rb") as f:
            up = requests.put(url,
                headers={"Content-Length": str(sz), "Content-Type": "video/mp4"},
                data=f, timeout=3600)
        
        if up.status_code in [200, 201]:
            vid_id = up.json().get("id")
            yt_url = f"https://www.youtube.com/watch?v={vid_id}"
            log(f"  ✓ Uploaded: {yt_url}")
            return yt_url
    except Exception as e:
        log(f"  ✗ Error: {e}")
    
    raise Exception("YouTube upload failed")

def cleanup():
    try:
        for f in glob.glob(str(WORK_DIR / "*")):
            if os.path.isfile(f):
                os.remove(f)
    except:
        pass

def main():
    start = time.time()
    log("\n" + "="*70)
    log("DEEPDIVE EMPIRE v8.0")
    log("="*70)

    state = load_state()
    tg("Pipeline starting...")

    day = datetime.datetime.now().weekday()
    niche = NICHES[day % len(NICHES)]
    voice = random.choice(VOICES[niche["name"]])
    topic = random.choice(niche["topics"])
    episode = state.get("episode_count", 0) + 1

    log(f"\nNiche: {niche['name']}")
    log(f"Episode: {episode}")
    log(f"Voice: {voice}")

    try:
        log("\n[STAGE 1: SCRIPT]")
        script = generate_script(topic, niche["series"])
    except Exception as e:
        log(f"FAILED: {e}")
        tg(f"Script failed: {e}")
        sys.exit(1)

    try:
        log("\n[STAGE 2: AUDIO]")
        audio = generate_audio(script, voice)
    except Exception as e:
        log(f"FAILED: {e}")
        tg(f"Audio failed: {e}")
        sys.exit(1)

    try:
        log("\n[STAGE 3: VIDEO]")
        video = get_background_video()
    except Exception as e:
        log(f"FAILED: {e}")
        tg(f"Video failed: {e}")
        sys.exit(1)

    title = f"Episode {episode}: {niche['series']}"
    desc = f"{niche['series']} - Episode {episode}\n\nSubscribe for daily investigations"

    try:
        log("\n[STAGE 4: UPLOAD]")
        yt_url = upload_youtube(video, title, desc)
    except Exception as e:
        log(f"FAILED: {e}")
        tg(f"Upload failed: {e}")
        sys.exit(1)

    cleanup()

    state["episode_count"] = episode
    state["last_url"] = yt_url
    state.setdefault("weekly", []).append({"date": datetime.datetime.now().isoformat(), "url": yt_url})
    save_state(state)

    elapsed = (time.time() - start) / 60
    tg(f"✅ PUBLISHED!\n{title}\n{yt_url}\nDone in {elapsed:.0f}m")
    log(f"\n✅ COMPLETE: {yt_url}\nTime: {elapsed:.1f}m")

if __name__ == "__main__":
    main()
