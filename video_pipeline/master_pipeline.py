#!/usr/bin/env python3
"""DeepDive Empire v8.0 - FINAL FIXED"""
import os, sys, json, re, time, random, datetime, glob, subprocess, shutil, requests, smtplib
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from groq import Groq

# Config
GROQ_KEY = os.environ.get("GROQ_API_KEY","")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY","")
CEREBRAS_KEY = os.environ.get("CEREBRAS_API_KEY","")
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY","")
PIXABAY_KEY = os.environ.get("PIXABAY_KEY","")
YT_CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID","")
YT_CLIENT_SEC = os.environ.get("YOUTUBE_CLIENT_SECRET","")
YT_REFRESH = os.environ.get("YOUTUBE_REFRESH_TOKEN","")
TG_TOKEN = os.environ.get("TELEGRAM_TOKEN","")
TG_CHAT = os.environ.get("TELEGRAM_CHAT_ID","")
IS_MAKEUP = os.environ.get("IS_MAKEUP","false").lower() == "true"

groq_client = Groq(api_key=GROQ_KEY)
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

WORK_DIR = Path("/tmp/deepdive")
WORK_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = WORK_DIR / "state.json"

MIN_WORDS = 2000
MAX_WORDS = 2600
MIN_GATE = 7.0
FINAL_GATE = 6.5

DAY_NICHE = {0:"dark_horror",1:"seduction_dark",2:"psychological_trap",3:"supernatural_real",4:"obsession_dark"}

NICHES = [
    {"name":"dark_horror","rpm":13.00,"series":"Dark Hours","topics":["A family discovered something living in their house for years","A nurse documented night shift incidents nobody believed","A hiker survived something in mountains search teams cannot explain"]},
    {"name":"seduction_dark","rpm":14.00,"series":"The Dark Seduction Files","topics":["A person used a 14-step system to destroy someone emotionally","A charismatic figure destroyed 23 people over 8 years","A relationship revealed to have been planned 3 years before meeting"]},
    {"name":"psychological_trap","rpm":12.00,"series":"The Trap","topics":["A 9-stage process to make targets financially dependent","A psychological trap using social media over 18 months","How gaslighting made a psychologist doubt her judgment"]},
    {"name":"supernatural_real","rpm":11.50,"series":"Evidence Files","topics":["A 2019 incident with 14 witnesses classified within 72 hours","Every occupant reported the same auditory experience confirmed by instruments","A medical case describing an event they could not have witnessed"]},
    {"name":"obsession_dark","rpm":13.00,"series":"Consumed","topics":["4380 consecutive days of obsessive behavior documented","An obsession destroying everything the subject built over 7 years","A stalker embedded as trusted friend for 3 years"]},
]

VOICES = {"dark_horror":["en-US-DavisNeural","en-GB-RyanNeural"],"seduction_dark":["en-GB-RyanNeural","en-US-AndrewNeural"],"psychological_trap":["en-US-BrianNeural","en-GB-ThomasNeural"],"supernatural_real":["en-GB-RyanNeural","en-US-DavisNeural"],"obsession_dark":["en-US-AndrewNeural","en-GB-RyanNeural"]}
BG_KEYWORDS = {"dark_horror":"dark horror shadow night","seduction_dark":"dark sensual shadow","psychological_trap":"dark corridor trap","supernatural_real":"dark mysterious fog","obsession_dark":"dark shadow watching"}

def log(m): print(m, flush=True)
def tg(m):
    for chunk in [m[i:i+4000] for i in range(0,len(m),4000)]:
        try:requests.post("https://api.telegram.org/bot"+TG_TOKEN+"/sendMessage", json={"chat_id":TG_CHAT,"text":chunk,"parse_mode":"HTML"},timeout=15)
        except: pass
def load_state():
    try: return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    except: return {}
def save_state(s): STATE_FILE.write_text(json.dumps(s,indent=2))

def call_cerebras(prompt, tokens=8000):
    if not CEREBRAS_KEY: return None
    try:
        r = requests.post(CEREBRAS_URL, headers={"Authorization":"Bearer "+CEREBRAS_KEY,"Content-Type":"application/json"}, json={"model":"llama-3.3-70b","messages":[{"role":"user","content":prompt}],"max_completion_tokens":min(tokens,8000),"temperature":0.88}, timeout=90)
        if r.status_code == 200:
            text = r.json().get("choices",[{}])[0].get("message",{}).get("content","")
            if text and len(text.strip()) > 100: log("OK Cerebras"); return text
    except: pass
    return None

def call_groq(prompt, tokens=8000):
    try:
        r = groq_client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":prompt}], temperature=0.88, max_tokens=min(tokens,8000))
        text = r.choices[0].message.content
        if text and len(text.strip()) > 100: log("OK Groq"); return text
    except: pass
    return None

def call_gemini(prompt, tokens=8000):
    try:
        r = requests.post(GEMINI_URL+"?key="+GEMINI_KEY, headers={"Content-Type":"application/json"}, json={"contents":[{"parts":[{"text":prompt}]}],"generationConfig":{"temperature":0.88,"maxOutputTokens":min(tokens,8192)},"safetySettings":[{"category":"HARM_CATEGORY_HARASSMENT","threshold":"BLOCK_NONE"}]}, timeout=90)
        if r.status_code == 200:
            c = r.json().get("candidates",[])
            if c: text = c[0]["content"]["parts"][0]["text"]; 
            if text and len(text.strip()) > 100: log("OK Gemini"); return text
    except: pass
    return None

def call_openrouter(prompt, tokens=8000):
    if not OPENROUTER_KEY: return None
    try:
        r = requests.post(OPENROUTER_URL, headers={"Authorization":"Bearer "+OPENROUTER_KEY,"Content-Type":"application/json"}, json={"model":"meta-llama/llama-3.3-70b-instruct:free","messages":[{"role":"user","content":prompt}],"max_tokens":min(tokens,8000),"temperature":0.88}, timeout=90)
        if r.status_code == 200: text = r.json()["choices"][0]["message"]["content"]; 
        if text and len(text.strip()) > 100: log("OK OpenRouter"); return text
    except: pass
    return None

def ai_generate(prompt, tokens=8000):
    result = call_cerebras(prompt, tokens); 
    if result: return result
    result = call_groq(prompt, tokens); 
    if result: return result
    result = call_gemini(prompt, tokens); 
    if result: return result
    result = call_openrouter(prompt, tokens); 
    if result: return result
    return None

def strip_md(text):
    for _ in range(2):
        text = re.sub(r'^#{1,6}\s+','',text,flags=re.MULTILINE)
        text = re.sub(r'\*+([^*\n]+)\*+',r'\1',text)
        text = re.sub(r'_+([^_\n]+)_+',r'\1',text)
        text = re.sub(r'`+[^`]*`+','',text)
        text = re.sub(r'[#*_`\[\]{}<>\\]','',text)
    return text.strip()

def score_result(r):
    if not r: return 0.0, ["failed"]
    s = 5.0
    w = r.get("words",0)
    if w >= MIN_WORDS: s += 2.8
    elif w >= 1600: s += 0.8
    else: s -= 2.0
    md = r.get("violations",0)
    if md == 0: s += 2.2
    elif md <= 2: s += 0.8
    else: s -= 1.5
    return min(round(s,1),10.0), []

def generate_everything(niche, topic, episode, attempt):
    darkness = min(40+attempt*8, 96)
    
    prompt = "Write a complete YouTube video script.\n"
    prompt = prompt + "Series: " + niche["series"] + "\n"
    prompt = prompt + "Topic: " + topic + "\n"
    prompt = prompt + "Style: Dark, mysterious, investigative\n"
    prompt = prompt + "Length: " + str(MIN_WORDS) + "-" + str(MAX_WORDS) + " words\n"
    prompt = prompt + "Requirements: Natural narration voice, max 12 words per sentence\n"
    prompt = prompt + "Include psychological hooks in first 100 words\n"
    prompt = prompt + "End with compelling call to action\n"
    
    result = ai_generate(prompt, tokens=8000)
    if not result: return None
    
    script = strip_md(strip_md(result))
    wc = len(script.split())
    violations = len(re.findall(r'[#*_`\[\]{}<>\\]', script))
    
    if wc < MIN_WORDS:
        deficit = MIN_WORDS - wc
        expand_prompt = "Expand this script by " + str(deficit) + " words: " + script[:200] + "..."
        result2 = ai_generate(expand_prompt, tokens=8000)
        if result2:
            clean2 = strip_md(strip_md(result2))
            if len(clean2.split()) > wc: script = clean2; wc = len(script.split())
    
    title = niche["series"] + ": Episode " + str(episode)
    thumbnail = "NOBODY KNEW"
    tags = ["horror","dark","documentary","true","story","psychological","real","mystery"]
    
    return {"script":script,"words":wc,"violations":violations,"title":title,"thumbnail":thumbnail,"tags":tags}

def run_stage1(state):
    log("="*70)
    log("STAGE 1: Script Generation")
    log("="*70)
    
    name = DAY_NICHE.get(datetime.datetime.now().weekday(),"dark_horror")
    niche = next(x for x in NICHES if x["name"]==name)
    
    opts = VOICES.get(niche["name"],["en-GB-RyanNeural"])
    voice = random.choice(opts)
    topic = random.choice(niche["topics"])
    episode = state.get("episode_count",0) + 1
    
    log("Niche: " + niche["name"])
    
    for attempt in range(1, 4):
        log("Attempt " + str(attempt) + "/3...")
        result = generate_everything(niche, topic, episode, attempt)
        score, _ = score_result(result)
        log("Score: " + str(score) + "/10")
        
        if score >= MIN_GATE or (score >= FINAL_GATE and attempt == 3):
            return niche, voice, episode, result, score
    
    sys.exit(1)

def run_stage2_approval(niche, voice, result, score):
    log("="*70)
    log("STAGE 2: Approval")
    log("="*70)
    try: tg("Script ready: " + result["title"])
    except: pass

def run_stage3_audio(script, voice):
    log("="*70)
    log("STAGE 3: Audio")
    log("="*70)
    try:
        subprocess.run(["pip","install","edge-tts","-q"],timeout=30)
        audio_file = str(WORK_DIR / "audio.mp3")
        subprocess.run(["python","-m","edge_tts","--text",script[:5000],"--voice",voice,"--write-media",audio_file],timeout=120,capture_output=True)
        if Path(audio_file).exists(): return audio_file, 60.0, voice
    except: pass
    sys.exit(1)

def run_stage4_video(niche):
    log("="*70)
    log("STAGE 4: Video")
    log("="*70)
    try:
        keyword = BG_KEYWORDS.get(niche["name"], "dark")
        r = requests.get("https://pixabay.com/api/videos/", params={"key":PIXABAY_KEY,"q":keyword,"per_page":1}, timeout=10)
        if r.status_code == 200 and r.json().get("hits"):
            url = r.json()["hits"][0]["videos"]["medium"]["url"]
            video_path = str(WORK_DIR / "background.mp4")
            r = requests.get(url, timeout=30, stream=True)
            with open(video_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
            return video_path
    except: pass
    return str(WORK_DIR / "background.mp4")

def get_yt_token():
    r = requests.post("https://oauth2.googleapis.com/token", data={"client_id":YT_CLIENT_ID,"client_secret":YT_CLIENT_SEC,"refresh_token":YT_REFRESH,"grant_type":"refresh_token"})
    d = r.json()
    if "access_token" not in d: raise Exception("YT token failed")
    return d["access_token"]

def upload_yt(path, title, desc, tags):
    log("Uploading...")
    token = get_yt_token()
    init = requests.post("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status", headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"}, json={"snippet":{"title":title,"description":desc,"tags":tags,"categoryId":"22"},"status":{"privacyStatus":"public"}})
    url = init.headers.get("Location")
    if not url: raise Exception("No upload URL")
    sz = Path(path).stat().st_size
    with open(path,"rb") as f:
        up = requests.put(url, headers={"Content-Length":str(sz),"Content-Type":"video/mp4"}, data=f, timeout=2400)
    if up.status_code in [200,201]:
        vid_id = up.json().get("id")
        yt_url = "https://www.youtube.com/watch?v=" + vid_id
        return yt_url
    raise Exception("Upload failed")

def cleanup():
    try:
        for f in glob.glob(str(WORK_DIR / "*")):
            if os.path.isfile(f): os.remove(f)
    except: pass

def main():
    log("="*70)
    log("DEEPDIVE EMPIRE v8.0")
    log("="*70)
    
    state = load_state()
    
    try:
        niche, voice, episode, result, score = run_stage1(state)
        run_stage2_approval(niche, voice, result, score)
        audio_path, duration, voice_used = run_stage3_audio(result["script"], voice)
        video_path = run_stage4_video(niche)
        
        log("="*70)
        log("STAGE 5: Upload")
        log("="*70)
        
        desc = result["title"] + "\n\nEpisode " + str(episode)
        yt_url = upload_yt(video_path, result["title"], desc, result["tags"])
        
        cleanup()
        
        state["episode_count"] = episode
        save_state(state)
        
        try: tg("Published: " + yt_url)
        except: pass
        
        log("SUCCESS: " + yt_url)
        
    except Exception as e:
        log("FAILED: " + str(e))
        try: tg("Failed: " + str(e))
        except: pass
        sys.exit(1)

if __name__ == "__main__":
    main()
