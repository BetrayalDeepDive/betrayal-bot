#!/usr/bin/env python3
"""
THE COLLAPSE INDEX — ANIMATED PIPELINE v1.0
Channel 5 of DeepDive Empire

Niches: AI Failures, Surveillance Capitalism, Tech Displacement,
        Algorithmic Society, Collapse Scenarios, Cybersecurity/Hacking Documentaries

Format: Terminal aesthetic — phosphor green, amber, ice blue, red decay color modes
Phase: PIPELINE_PHASE=generate / upload / full
"""
import os, sys, re, json, time, datetime, random, asyncio, subprocess, shutil
from pathlib import Path

# ── PATHS ────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).parent
WORK_DIR     = Path(os.environ.get("WORK_DIR", "/tmp/collapse_index"))
WORK_DIR.mkdir(parents=True, exist_ok=True)

MIN_WORDS = 1900
MAX_WORDS = 2100

# ── NICHES ───────────────────────────────────────────────────
NICHES = [
    {
        "name": "ai_failures", "rpm": 16.00,
        "series": "The Collapse Index: AI Failures",
        "color_mode": "phosphor_green",
        "viral_search": "ai failure artificial intelligence disaster documentary investigation animated",
        "archive_search": "ai failure disaster investigation documentary viral 2022 2023",
        "thumbnail_triggers": ["AI DECIDED","SYSTEM FAILED","147 MILLION","STILL RUNNING"],
        "seed_topics": [
            "The AI hiring tool Amazon quietly shut down after discovering it penalized female applicants systematically",
            "A facial recognition system wrongly identified 28 members of Congress as criminal suspects in 2018",
            "COMPAS: the algorithm that influenced sentencing for 135,000 defendants with documented racial disparity",
            "The AI model deployed in hospital triage that was trained only on historical data from a biased system",
            "An autonomous vehicle decision system that classified darker-skinned pedestrians with lower confidence scores",
            "The healthcare AI that recommended opioids based on insurance billing patterns rather than patient outcomes",
            "A content moderation AI that removed 11 million posts in 48 hours without human review capability",
        ],
    },
    {
        "name": "surveillance_capitalism", "rpm": 15.00,
        "series": "The Collapse Index: Surveillance Capitalism",
        "color_mode": "amber",
        "viral_search": "surveillance capitalism data privacy investigation documentary animated exposed",
        "archive_search": "surveillance capitalism data privacy exposed documentary viral 2022 2023",
        "thumbnail_triggers": ["YOUR DATA","ALWAYS WATCHING","87 MILLION","SOLD TODAY"],
        "seed_topics": [
            "Facebook's internal research confirmed it could alter users' emotional states through feed manipulation",
            "The data broker industry sells 73,000 data points per person to buyers who never identify themselves",
            "Cambridge Analytica processed 87 million profiles to build psychological targeting models for elections",
            "Google's Location History continues recording movement after users explicitly disable the feature",
            "The insurance industry uses social media activity as an undisclosed factor in premium calculations",
            "A mental health app shared user therapy session data with third-party advertisers for 4 years",
            "The smartphone app that granted 50 third-party firms microphone access in the background permissions",
        ],
    },
    {
        "name": "tech_displacement", "rpm": 14.00,
        "series": "The Collapse Index: Tech Displacement",
        "color_mode": "ice_blue",
        "viral_search": "technology displacement automation jobs economy documentary investigation animated",
        "archive_search": "technology automation displacement jobs documentary viral 2022 2023",
        "thumbnail_triggers": ["47 PERCENT","ALREADY GONE","STILL COMING","NO PLAN EXISTS"],
        "seed_topics": [
            "The Oxford study projected 47 percent of US jobs face automation risk within two decades",
            "Amazon warehouse automation reduced per-unit human labor by 70 percent — the worker count increased",
            "The trucking industry automation timeline and the 3.5 million drivers for whom no retraining plan exists",
            "A radiologist AI diagnoses 26 conditions from chest X-rays at higher accuracy than board-certified physicians",
            "The call center automation wave that eliminated 1.2 million jobs between 2015 and 2022",
            "Robotic process automation in legal discovery reduced 500-attorney document review to 3 software licenses",
            "The agricultural automation systems replacing seasonal workers who have no documented pathway to transition",
        ],
    },
    {
        "name": "algorithmic_society", "rpm": 14.50,
        "series": "The Collapse Index: Algorithmic Society",
        "color_mode": "red_decay",
        "viral_search": "algorithm social media control society documented investigation documentary animated",
        "archive_search": "algorithm social media control society documentary viral 2022 2023",
        "thumbnail_triggers": ["THE ALGORITHM","DESIGNED THIS","YOUR FEED CHOSE","THEY KNEW"],
        "seed_topics": [
            "The Facebook internal research memo that stated the platform knowingly amplified divisive content to boost engagement",
            "YouTube's recommendation algorithm directed viewers toward increasingly extreme content over 17 minutes on average",
            "The credit scoring algorithm that used zip code as a proxy for race — documented in regulatory filings",
            "TikTok's For You algorithm reaches full personalization within 40 videos — 23 minutes of viewing",
            "An insurance company algorithm that raised premiums in minority zip codes independent of claim history",
            "The child protective services algorithm that flagged families in poverty at a documented higher rate",
            "A predictive policing system that directed patrol resources based on historical arrest data — not crime data",
        ],
    },
    {
        "name": "collapse_scenarios", "rpm": 11.00,
        "series": "The Collapse Index: Collapse Scenarios",
        "color_mode": "phosphor_green",
        "viral_search": "collapse scenario infrastructure society documented investigation documentary animated",
        "archive_search": "collapse scenario infrastructure society documented documentary viral 2022 2023",
        "thumbnail_triggers": ["72 HOURS LEFT","SINGLE POINT","STILL POSSIBLE","NO BACKUP"],
        "seed_topics": [
            "The US power grid has a documented single point of failure that FERC has known about since 2013",
            "A solar storm equivalent to 1859 Carrington Event would disable GPS, power grids, and internet for 12 months",
            "The global fertilizer supply chain concentrates 78 percent of production in 3 countries — all hostile to each other",
            "Antibiotic resistance: the WHO projects 10 million annual deaths by 2050 from currently treatable infections",
            "The internet's routing infrastructure depends on 13 root server clusters — 7 are in the United States",
            "A Mississippi River flood at 1993 levels would interrupt 60 percent of US grain exports for 90 days",
            "The documented fragility of the global chip supply chain: 90 percent of advanced semiconductors from one island",
        ],
    },
    {
        "name": "cybersecurity_hacking", "rpm": 11.50,
        "series": "The Collapse Index: Breach Files",
        "color_mode": "phosphor_green",
        "viral_search": "cybersecurity hacking breach investigation documentary animated terminal",
        "archive_search": "cybersecurity hacking breach investigation documentary viral 2022 2023",
        "thumbnail_triggers": ["147 MILLION","14 DAYS","STILL BEING USED","PATCH EXISTED"],
        "seed_topics": [
            "The Equifax breach exposed 147 million Social Security numbers. A patch for the vulnerability had existed for months.",
            "Colonial Pipeline paid $4.4M ransom to a group of 18-year-olds. Operations were down for 6 days.",
            "SolarWinds: a single trojanized software update granted access to 18,000 government and corporate networks for 9 months",
            "NSA hacking tools stolen in 2017 were deployed in ransomware attacks still active against hospitals in 2023",
            "A hospital network encryption attack in 2020 kept systems offline for 14 days. Three patients died during the outage.",
            "The Marriott breach gave attackers access to 500 million guest records — for four years before detection",
            "A water treatment plant in Florida had its chemical levels remotely altered in 2021 by an unknown actor",
        ],
    },
]

# ── COLOR MODES (terminal aesthetic) ─────────────────────────
COLOR_MODES = {
    "phosphor_green": {"bg":(2,8,2),  "primary":(0,255,0),   "accent":(0,200,0),   "secondary":(0,120,0)},
    "amber":          {"bg":(8,5,0),  "primary":(255,180,0),  "accent":(255,140,0),  "secondary":(180,100,0)},
    "ice_blue":       {"bg":(0,5,12), "primary":(100,200,255),"accent":(0,180,255),  "secondary":(0,100,180)},
    "red_decay":      {"bg":(8,0,0),  "primary":(255,50,50),  "accent":(200,0,0),   "secondary":(120,0,0)},
}

NICHE_VOICES = {
    "ai_failures":            ["en-GB-ThomasNeural","en-US-ChristopherNeural","en-US-BrianNeural","en-GB-RyanNeural"],
    "surveillance_capitalism":["en-US-BrianNeural","en-GB-ThomasNeural","en-US-ChristopherNeural","en-GB-RyanNeural"],
    "tech_displacement":      ["en-GB-RyanNeural","en-US-BrianNeural","en-GB-ThomasNeural","en-US-ChristopherNeural"],
    "algorithmic_society":    ["en-US-ChristopherNeural","en-GB-ThomasNeural","en-US-BrianNeural","en-GB-RyanNeural"],
    "collapse_scenarios":     ["en-GB-ThomasNeural","en-US-BrianNeural","en-GB-RyanNeural","en-US-ChristopherNeural"],
    "cybersecurity_hacking":  ["en-US-BrianNeural","en-GB-ThomasNeural","en-US-ChristopherNeural","en-GB-RyanNeural"],
}

GUARANTEED_VOICES = [
    "en-GB-ThomasNeural","en-GB-RyanNeural","en-US-BrianNeural",
    "en-US-ChristopherNeural","en-US-AndrewNeural","en-US-EricNeural","en-US-GuyNeural",
]

DREAD_TRIGGERS = {
    "infrastructure": "The system everyone depends on — and the single documented failure point.",
    "scale":          "Exact numbers. Then make each number a specific person or consequence.",
    "institutional":  "The company, platform, or government knew. The record proves it.",
    "duration":       "Not years — exact months, exact days. 9 months. 14 days. 4 years undetected.",
    "reversal":       "The public version was the cover story. The internal document is different.",
    "proximity":      "This is not historical. It is running right now. You are inside it.",
    "invisibility":   "It was hidden because it looked exactly like normal operation.",
    "competence":     "The patience. The architecture. The cold deliberateness of it.",
}

STAGE_TARGETS = {1:120, 2:200, 3:280, 4:480, 5:150, 6:520, 7:150}
MAX_CHUNK = 500

# ── PROVIDERS (same 7-provider chain) ────────────────────────
CEREBRAS_KEY   = os.environ.get("CEREBRAS_API_KEY","")
SAMBANOVA_KEY  = os.environ.get("SAMBANOVA_API_KEY","")
GEMINI_KEY     = os.environ.get("GEMINI_API_KEY","")
GEMINI_KEY_2   = os.environ.get("GEMINI_API_KEY_2","")
GROQ_KEY       = os.environ.get("GROQ_API_KEY","")
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY","")
COHERE_KEY     = os.environ.get("COHERE_API_KEY","")
MISTRAL_KEY    = os.environ.get("MISTRAL_API_KEY","")

YT_CLIENT_ID     = os.environ.get("COLLAPSE_YT_CLIENT_ID","")
YT_CLIENT_SECRET = os.environ.get("COLLAPSE_YT_CLIENT_SECRET","")
YT_REFRESH_TOKEN = os.environ.get("COLLAPSE_YT_REFRESH_TOKEN","")

TG_TOKEN   = os.environ.get("TELEGRAM_TOKEN","")
TG_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID","")

import requests

def log(msg): print(msg, flush=True)

def tg(msg):
    if not TG_TOKEN or not TG_CHAT_ID: return
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id":TG_CHAT_ID,"text":msg,"parse_mode":"HTML"}, timeout=15)
    except Exception as e: log(f"  TG: {e}")

def strip_md(text):
    if not text: return ""
    text = re.sub(r"[#*_`\[\]{}|<>]","",text)
    text = re.sub(r"\n{3,}","\n\n",text)
    return text.strip()

def get_media_duration(path):
    try:
        r = subprocess.run(["ffprobe","-v","quiet","-show_entries","format=duration",
            "-of","csv=p=0",str(path)], capture_output=True, text=True, timeout=30)
        if r.returncode==0 and r.stdout.strip(): return float(r.stdout.strip())
    except Exception: pass
    return 0.0

def run_ffmpeg(cmd, label="ffmpeg", timeout=300):
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout)
        if r.returncode != 0:
            log(f"  {label}: exit {r.returncode} — {r.stderr.decode('utf-8','ignore')[-150:]}")
            return False
        return True
    except subprocess.TimeoutExpired: log(f"  {label}: timeout"); return False
    except Exception as e: log(f"  {label}: {e}"); return False

def _call_cerebras(p,t=2000,temp=0.85):
    if not CEREBRAS_KEY: return None
    for m in ["llama-3.3-70b","llama3.3-70b","llama-3.1-70b","llama3.1-70b"]:
        try:
            r = requests.post("https://api.cerebras.ai/v1/chat/completions",
                headers={"Authorization":f"Bearer {CEREBRAS_KEY}","Content-Type":"application/json"},
                json={"model":m,"messages":[{"role":"user","content":p}],"max_tokens":min(t,9000),"temperature":temp},timeout=60)
            if r.status_code==200:
                txt=r.json()["choices"][0]["message"]["content"].strip()
                if txt: log(f"  OK Cerebras"); return txt
        except Exception as e: log(f"  Cerebras {m}: {e}")
    return None

def _call_sambanova(p,t=2000,temp=0.85):
    if not SAMBANOVA_KEY: return None
    try:
        r = requests.post("https://api.sambanova.ai/v1/chat/completions",
            headers={"Authorization":f"Bearer {SAMBANOVA_KEY}","Content-Type":"application/json"},
            json={"model":"Meta-Llama-3.3-70B-Instruct","messages":[{"role":"user","content":p}],"max_tokens":t,"temperature":temp},timeout=60)
        if r.status_code==200:
            txt=r.json()["choices"][0]["message"]["content"].strip()
            if txt: log(f"  OK SambaNova"); return txt
    except Exception as e: log(f"  SambaNova: {e}")
    return None

def _call_gemini(p,t=2000,temp=0.85):
    for kn,key in [("primary",GEMINI_KEY),("backup",GEMINI_KEY_2)]:
        if not key: continue
        try:
            r=requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}",
                json={"contents":[{"parts":[{"text":p}]}],"generationConfig":{"maxOutputTokens":t,"temperature":temp},
                      "safetySettings":[{"category":c,"threshold":"BLOCK_NONE"} for c in ["HARM_CATEGORY_HARASSMENT","HARM_CATEGORY_HATE_SPEECH","HARM_CATEGORY_SEXUALLY_EXPLICIT","HARM_CATEGORY_DANGEROUS_CONTENT"]]},timeout=90)
            if r.status_code==200:
                txt=r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                if txt: log(f"  OK Gemini ({kn})"); return txt
            elif r.status_code==429: log(f"  Gemini ({kn}) quota exhausted")
        except Exception as e: log(f"  Gemini: {e}")
    return None

def _call_groq(p,t=2000,temp=0.85):
    if not GROQ_KEY: return None
    try:
        r=requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization":f"Bearer {GROQ_KEY}","Content-Type":"application/json"},
            json={"model":"llama-3.3-70b-versatile","messages":[{"role":"user","content":p}],"max_tokens":min(t,4800),"temperature":temp},timeout=60)
        if r.status_code==200:
            txt=r.json()["choices"][0]["message"]["content"].strip()
            if txt: log(f"  OK Groq"); return txt
    except Exception as e: log(f"  Groq: {e}")
    return None

def _call_openrouter(p,t=2000,temp=0.85):
    if not OPENROUTER_KEY: return None
    for m in ["meta-llama/llama-3.3-70b-instruct:free","mistralai/mistral-7b-instruct:free",
               "google/gemma-2-9b-it:free","microsoft/phi-3-mini-128k-instruct:free"]:
        try:
            r=requests.post("https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization":f"Bearer {OPENROUTER_KEY}","Content-Type":"application/json"},
                json={"model":m,"messages":[{"role":"user","content":p}],"max_tokens":t,"temperature":temp},timeout=60)
            if r.status_code==200:
                txt=r.json()["choices"][0]["message"]["content"].strip()
                if txt: log(f"  OK OpenRouter"); return txt
        except Exception as e: log(f"  OpenRouter {m}: {e}")
    return None

def _call_cohere(p,t=2000,temp=0.85):
    if not COHERE_KEY: return None
    try:
        r=requests.post("https://api.cohere.ai/v1/generate",
            headers={"Authorization":f"Bearer {COHERE_KEY}","Content-Type":"application/json"},
            json={"model":"command-r-08-2024","prompt":p,"max_tokens":t,"temperature":temp},timeout=60)
        if r.status_code==200:
            txt=r.json().get("generations",[{}])[0].get("text","").strip()
            if txt: log(f"  OK Cohere"); return txt
    except Exception as e: log(f"  Cohere: {e}")
    return None

def _call_mistral(p,t=2000,temp=0.85):
    if not MISTRAL_KEY: return None
    try:
        r=requests.post("https://api.mistral.ai/v1/chat/completions",
            headers={"Authorization":f"Bearer {MISTRAL_KEY}","Content-Type":"application/json"},
            json={"model":"mistral-small-latest","messages":[{"role":"user","content":p}],"max_tokens":t,"temperature":temp},timeout=60)
        if r.status_code==200:
            txt=r.json()["choices"][0]["message"]["content"].strip()
            if txt: log(f"  OK Mistral"); return txt
    except Exception as e: log(f"  Mistral: {e}")
    return None

def ai(prompt, tokens=2000, temp=0.85, prefer=None):
    providers = [
        ("cerebras",_call_cerebras),("sambanova",_call_sambanova),("gemini",_call_gemini),
        ("groq",_call_groq),("openrouter",_call_openrouter),("cohere",_call_cohere),("mistral",_call_mistral),
    ]
    if prefer:
        providers = sorted(providers, key=lambda x: 0 if x[0]==prefer else 1)
    for name, fn in providers:
        result = fn(prompt, tokens, temp)
        if result and len(result.split()) > 20: return result
        log(f"  Waiting 10s before next provider..."); time.sleep(10)
    return None

STATE_FILE = WORK_DIR / "collapse_state.json"
def load_state():
    try:
        if STATE_FILE.exists(): return json.loads(STATE_FILE.read_text())
    except Exception: pass
    return {"niche_idx":0,"episode":0}

def save_state(s): STATE_FILE.write_text(json.dumps(s,indent=2))

def get_niche(state):
    idx = state.get("niche_idx",0) % len(NICHES)
    n   = NICHES[idx]
    state["niche_idx"] = (idx+1) % len(NICHES)
    return n

def get_topic(niche):
    seed = random.choice(niche["seed_topics"])
    prompt = (f"Research topic for a dark tech/AI/collapse documentary channel.\n"
              f"Niche: {niche['name']} | Seed: {seed}\n"
              f"Generate ONE specific documentary topic — documented, not speculative.\n"
              f"Must have a specific current implication. 1-2 sentences. Return ONLY the topic.")
    r = ai(prompt, tokens=200, temp=0.9)
    return r.strip() if r else seed

def generate_script(niche, topic, episode):
    st   = STAGE_TARGETS
    mode = niche.get("color_mode","phosphor_green")
    prompt = f"""You are writing a 15-minute dark tech documentary script for The Collapse Index.

CHANNEL: The Collapse Index | NICHE: {niche["series"]} | VISUAL: {mode} terminal aesthetic
TOPIC: {topic} | EPISODE: {episode}

TONE: DARK DOCUMENTARY. Terminal aesthetic — every sentence reads like a system alert.
Every fact is documented. Every claim is verifiable. The horror is in the evidence, not the speculation.
Dark humor permitted: the kind where viewers laugh because the alternative is despair.

CRAVEABILITY TRIGGERS (3+ minimum):
1. The documented statistic that sounds fabricated but is real.
2. The internal document, memo, or research that contradicts the public statement.
3. The system still running right now — not past tense, not historical.
4. The implication that is worse than the event itself.
5. The specific detail (exact figure, exact date, exact person) that proves everything.
6. The uncomfortable question left open.
7. The gap between what was announced and what the documents show.

TITLE: No generic titles. "[Documented Number] [System/Event] [Dark Implication]"
FORBIDDEN WORDS: Shocking, Incredible, Amazing, Unbelievable, Mind-Blowing

SEVEN STAGES (write continuously, no labels):
STAGE 1 ({st[1]}w): Specific documented fact opens a loop. Scale. Proximity. Unresolved.
STAGE 2 ({st[2]}w): What existed before. What was normal. The last moment before the evidence begins.
STAGE 3 ({st[3]}w): First documented signals. Each individually explainable. Accumulation.
STAGE 4 ({st[4]}w): The full documented record. Specific sources, dates, figures. Architecture.
STAGE 5 ({st[5]}w): The official version. Then one sentence showing the gap.
STAGE 6 ({st[6]}w): The complete picture. One finding per paragraph. Ordered by severity.
STAGE 7 ({st[7]}w): Current implications. What is still running. Subscribe CTA at peak.

RULES: Max 13 words/sentence. Zero markdown. No labels. {MIN_WORDS}-{MAX_WORDS} words total.

After script write:
---METADATA---
TITLE: [dark documentary title]
THUMBNAIL: [3 words ALL CAPS]
TAGS: [10 tags comma separated]
"""
    return ai(prompt, tokens=8000, temp=0.85)

def parse_script(raw, niche):
    if not raw: return None,None,None,[]
    parts  = raw.split("---METADATA---")
    script = strip_md(parts[0].strip())
    meta   = parts[1].strip() if len(parts)>1 else ""
    title,thumb,tags = None,None,[]
    for line in meta.split("\n"):
        line=line.strip()
        if line.startswith("TITLE:"): title=line[6:].strip()
        elif line.startswith("THUMBNAIL:"): thumb=line[10:].strip()
        elif line.startswith("TAGS:"): tags=[t.strip() for t in line[5:].split(",") if t.strip()]
    if not title: title=f"{niche['series']} — Investigation"
    if not thumb: thumb=random.choice(niche["thumbnail_triggers"])
    return script,title,thumb,tags

def score_script(script,wc,violations):
    if not script: return 0.0,["Empty"]
    score=5.0; issues=[]
    if wc>=MIN_WORDS: score+=2.8
    elif wc>=int(MIN_WORDS*0.8): score+=0.8
    else: score-=2.0; issues.append(f"Under target: {wc}w")
    if violations==0: score+=2.2
    elif violations<=2: score+=0.8
    else: score-=1.5; issues.append(f"{violations} MD violations")
    words=script.split(); total=len(words)
    if total>=400:
        hooks=["subscribe","documented","still running","the evidence","classified","internal","breach","still active"]
        s60=" ".join(words[int(total*0.55):int(total*0.65)]).lower()
        if sum(1 for h in hooks if h in s60)<2: score-=0.8; issues.append("Weak 60% hook")
        if "subscribe" not in " ".join(words[-60:]).lower(): score-=0.3; issues.append("No final CTA")
    return min(round(score,1),10.0),issues

def inject_ctas(script,niche_name):
    cta_map={
        "ai_failures":["Subscribe to The Collapse Index for more documented AI failure investigations.","Follow The Collapse Index — new tech investigation every week.","Subscribe for more documented AI system failures at The Collapse Index."],
        "surveillance_capitalism":["Subscribe to The Collapse Index for more documented surveillance investigations.","Follow The Collapse Index — new surveillance capitalism case every week.","Subscribe for more verified surveillance capitalism files at The Collapse Index."],
        "tech_displacement":["Subscribe to The Collapse Index for more documented automation investigations.","Follow The Collapse Index — new tech displacement case every week.","Subscribe for more documented tech displacement analysis at The Collapse Index."],
        "algorithmic_society":["Subscribe to The Collapse Index for more documented algorithm investigations.","Follow The Collapse Index — new algorithmic society case every week.","Subscribe for more verified algorithmic control investigations at The Collapse Index."],
        "collapse_scenarios":["Subscribe to The Collapse Index for more documented collapse scenario analysis.","Follow The Collapse Index — new collapse investigation every week.","Subscribe for more documented infrastructure vulnerability analysis at The Collapse Index."],
        "cybersecurity_hacking":["Subscribe to The Collapse Index for more documented breach investigations.","Follow The Collapse Index — new cybersecurity investigation every week.","Subscribe for more verified breach files at The Collapse Index."],
    }
    ctas=cta_map.get(niche_name,["Subscribe to The Collapse Index for more documented tech investigations."])
    words=script.split(); total=len(words)
    if total<400: return script
    result=script; inserted=0
    for i,mark in enumerate([int(total*0.30),int(total*0.60),int(total*0.80)]):
        cta=ctas[i%len(ctas)]
        target=mark+inserted; aw=result.split()
        if target>=len(aw): continue
        char_pos=len(" ".join(aw[:target]))
        period=result.find(". ",char_pos)
        if period==-1: continue
        result=result[:period+2]+cta+" "+result[period+2:]
        inserted+=len(cta.split())+1
    if "subscribe" not in " ".join(result.split()[-60:]).lower():
        result=result.rstrip()+" Subscribe to The Collapse Index for more documented tech investigations."
    return result

def check_audio_quality(mp3,dur_expected):
    try:
        sz=Path(mp3).stat().st_size
        if sz<200000: return False
        r=subprocess.run(["ffprobe","-v","quiet","-show_entries","format=duration","-of","csv=p=0",str(mp3)],
            capture_output=True,text=True,timeout=30)
        if r.returncode==0 and r.stdout.strip():
            actual=float(r.stdout.strip())
            if actual<dur_expected*0.20: return False
            log(f"  Quality OK: {actual:.0f}s"); return True
    except Exception: pass
    return False

async def _tts(text,voice,path):
    import edge_tts
    chunks=[]; current=""
    for sent in re.split(r"(?<=[.!?])\s+",text):
        if len(current)+len(sent)>MAX_CHUNK and current:
            chunks.append(current.strip()); current=sent
        else: current+=" "+sent
    if current.strip(): chunks.append(current.strip())
    parts=[]
    for i,chunk in enumerate(chunks):
        if not chunk.strip(): continue
        part=str(WORK_DIR/f"chunk_{i:03d}.mp3")
        c=edge_tts.Communicate(chunk,voice,rate="-8%")
        await asyncio.wait_for(c.save(part),timeout=90)
        if Path(part).exists() and Path(part).stat().st_size>1000: parts.append(part)
    if not parts: raise RuntimeError("All chunks failed")
    if len(parts)==1: shutil.copy(parts[0],path); return
    cf=str(WORK_DIR/"concat.txt")
    with open(cf,"w") as f:
        for p in parts: f.write(f"file '{p}'\n")
    run_ffmpeg(["ffmpeg","-y","-f","concat","-safe","0","-i",cf,"-c:a","libmp3lame","-q:a","2",path],"concat",120)

def run_stage3_audio(script_clean,voice_id,niche_name):
    _w=script_clean.split()
    if len(_w)>MAX_WORDS: script_clean=" ".join(_w[:MAX_WORDS]); log(f"  Script truncated to {MAX_WORDS}w")
    wc=len(script_clean.split())
    dur_expected=min((wc/125.0)*60.0,900.0)
    preferred=NICHE_VOICES.get(niche_name,GUARANTEED_VOICES[:4])
    vq=preferred+[v for v in GUARANTEED_VOICES if v not in preferred]
    audio=str(WORK_DIR/"audio.mp3")
    for _vi,v in enumerate(vq[:12]):
        if _vi > 0: time.sleep(3)  # avoid edge-tts rate limit
        log(f"  Trying: {v}")
        try:
            asyncio.run(asyncio.wait_for(_tts(script_clean,v,audio),timeout=180))
            if not Path(audio).exists(): continue
            if not check_audio_quality(audio,dur_expected): continue
            log(f"  ACCEPTED: {v}")
            eq=str(WORK_DIR/"audio_eq.mp3")
            af=('"equalizer=f=60:width_type=o:width=2:g=4,"'
                '"equalizer=f=250:width_type=o:width=2:g=2,"'
                '"equalizer=f=3000:width_type=o:width=2:g=-1,"'
                '"equalizer=f=8000:width_type=o:width=2:g=-2,"'
                '"aecho=0.85:0.88:60:0.3,"'
                '"acompressor=threshold=-20dB:ratio=3:attack=3:release=100:makeup=3dB,"'
                '"loudnorm=I=-16:LRA=11:TP=-1.5"')
            if run_ffmpeg(["ffmpeg","-y","-i",audio,"-af",af,"-c:a","libmp3lame","-q:a","2",eq],"eq",180):
                shutil.copy(eq,audio)
            return audio,get_media_duration(audio),None,v
        except Exception as e: log(f"  {v} err: {e}")
    raise RuntimeError("All voices failed")

def assemble_video(niche,audio_path,duration,topic):
    mode=niche.get("color_mode","phosphor_green")
    pal=COLOR_MODES[mode]; W,H=1920,1080
    try: from PIL import Image,ImageDraw
    except ImportError:
        out=str(WORK_DIR/"final.mp4")
        run_ffmpeg(["ffmpeg","-y","-i",audio_path,"-vf",f"color=c=black:size={W}x{H}:rate=24",
            "-shortest","-c:v","libx264","-c:a","aac",out],"video",600)
        return out
    frames=WORK_DIR/"frames"; frames.mkdir(exist_ok=True)
    n=max(1,int(duration*24))
    bg=tuple(pal["bg"]); acc=tuple(pal["accent"]); pri=tuple(pal["primary"])
    for i in range(min(n,72000)):
        t=i/max(n,1)
        img=Image.new("RGB",(W,H),bg)
        draw=ImageDraw.Draw(img)
        # Terminal scanline effect
        for sy in range(0,H,4):
            alpha_line=int(5+3*abs((t*2%1.0)-0.5))
            draw.line([(0,sy),(W,sy)],fill=bg,width=1)
        # Cursor blink
        if int(t*2)%2==0:
            draw.rectangle([W-60,H-40,W-20,H-10],fill=pri)
        img.save(str(frames/f"frame_{i:06d}.jpg"),quality=85)
    temp=str(WORK_DIR/"tv.mp4")
    run_ffmpeg(["ffmpeg","-y","-r","24","-i",str(frames/"frame_%06d.jpg"),
        "-c:v","libx264","-preset","ultrafast","-pix_fmt","yuv420p",temp],"frames",600)
    final=str(WORK_DIR/"final.mp4")
    run_ffmpeg(["ffmpeg","-y","-i",temp,"-i",audio_path,"-c:v","copy","-c:a","aac","-shortest",final],"mux",120)
    shutil.rmtree(str(frames),ignore_errors=True)
    return final

def generate_thumbnail(niche,topic,title,thumb_text):
    try: from PIL import Image,ImageDraw,ImageFont
    except ImportError: return None
    W,H=1280,720; mode=niche.get("color_mode","phosphor_green"); pal=COLOR_MODES[mode]
    img=Image.new("RGB",(W,H),tuple(pal["bg"])); draw=ImageDraw.Draw(img)
    draw.rectangle([0,H-8,W,H],fill=(200,0,0))
    words=" ".join(thumb_text.strip().upper().split()[:3])
    try: font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",120)
    except Exception: font=ImageFont.load_default()
    bbox=draw.textbbox((0,0),words,font=font)
    x=(W-(bbox[2]-bbox[0]))//2; y=(H-(bbox[3]-bbox[1]))//2-40
    draw.text((x+3,y+3),words,font=font,fill=(0,0,0))
    draw.text((x,y),words,font=font,fill=(255,255,255))
    path=str(WORK_DIR/"thumbnail.jpg"); img.save(path,quality=95); return path

def get_yt_token():
    import urllib.request,urllib.parse
    if not YT_CLIENT_ID: raise RuntimeError("Missing COLLAPSE_YT_CLIENT_ID")
    data=urllib.parse.urlencode({"client_id":YT_CLIENT_ID,"client_secret":YT_CLIENT_SECRET,
        "refresh_token":YT_REFRESH_TOKEN,"grant_type":"refresh_token"}).encode()
    req=urllib.request.Request("https://oauth2.googleapis.com/token",data=data,
        headers={"Content-Type":"application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req,timeout=30) as resp: return json.loads(resp.read())["access_token"]

def upload_yt(video_path,title,description,tags,thumb_path=None):
    import urllib.request
    token=get_yt_token()
    meta=json.dumps({"snippet":{"title":title[:100],"description":description,
        "tags":tags[:30],"categoryId":"28","defaultLanguage":"en"},
        "status":{"privacyStatus":"public","selfDeclaredMadeForKids":False}}).encode()
    boundary="boundary_collapse_upload"
    body=(f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n".encode()
          +meta+f"\r\n--{boundary}\r\nContent-Type: video/mp4\r\n\r\n".encode()
          +open(video_path,"rb").read()+f"\r\n--{boundary}--".encode())
    req=urllib.request.Request(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=multipart&part=snippet,status",
        data=body,headers={"Authorization":f"Bearer {token}","Content-Type":f"multipart/related; boundary={boundary}","Content-Length":str(len(body))})
    with urllib.request.urlopen(req,timeout=300) as resp:
        r=json.loads(resp.read()); vid_id=r.get("id","")
        if thumb_path and vid_id:
            try:
                td=open(thumb_path,"rb").read()
                tr=urllib.request.Request(f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={vid_id}",
                    data=td,headers={"Authorization":f"Bearer {token}","Content-Type":"image/jpeg"})
                urllib.request.urlopen(tr,timeout=60)
            except Exception as e: log(f"  Thumb: {e}")
        return vid_id

PENDING_FILE=WORK_DIR/"pending_upload.json"
def save_pending(d): PENDING_FILE.write_text(json.dumps(d,indent=2))
def load_pending():
    if PENDING_FILE.exists(): return json.loads(PENDING_FILE.read_text())
    return None
def clear_pending():
    if PENDING_FILE.exists(): PENDING_FILE.unlink()

def main():
    log("="*65)
    log(f"THE COLLAPSE INDEX v1.0 — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    log("="*65)
    phase=os.environ.get("PIPELINE_PHASE","generate").lower()
    log(f"Phase: {phase.upper()}")

    if phase=="upload":
        pending=load_pending()
        if not pending: tg("⚠️ Collapse Index: no pending video."); return
        try:
            vid_id=upload_yt(pending["video_path"],pending["title"],pending["description"],pending["tags"],pending.get("thumb_path"))
            clear_pending()
            tg(f"✅ Collapse Index LIVE\n\n<b>{pending['title']}</b>\nhttps://youtube.com/watch?v={vid_id}")
        except Exception as e: tg(f"❌ Collapse Upload FAILED: {e}"); raise
        return

    state=load_state(); niche=get_niche(state)
    episode=state.get("episode",0)+1; state["episode"]=episode; save_state(state)
    log(f"\nNiche: {niche['name']} | Color: {niche['color_mode']} | Episode: {episode}")

    log("\nSTAGE 1: Topic")
    topic=get_topic(niche); log(f"  Topic: {topic}")

    log("\nSTAGE 2: Script")
    raw=generate_script(niche,topic,episode)
    if not raw: tg("❌ Collapse Index: Script failed"); sys.exit(1)
    script,title,thumb_text,tags=parse_script(raw,niche)
    if not script: tg("❌ Collapse Index: Parse failed"); sys.exit(1)

    wc=len(script.split())
    exp_round=0
    while wc < MIN_WORDS and wc <= MAX_WORDS and exp_round < 3:
        if wc>MAX_WORDS: break
        exp_round+=1; deficit=MIN_WORDS-wc
        log(f"  {wc}w short — expanding round {exp_round}...")
        ep=(f"Script is {wc}w. Needs {MIN_WORDS}. Expand evidence sections only.\n"
            f"Zero markdown. Max 13 words/sentence. Return COMPLETE script:\n\n"+script[:3000])
        r2=ai(ep,tokens=7000,prefer="gemini")
        if r2:
            s2=strip_md(r2); s2wc=len(s2.split())
            if s2wc>wc:
                if s2wc>MAX_WORDS: s2=" ".join(s2.split()[:MAX_WORDS]); s2wc=MAX_WORDS
                script=s2; wc=s2wc; log(f"  Expanded to {wc}w")
        else: break
    if wc>MAX_WORDS:
        script=" ".join(script.split()[:MAX_WORDS]); wc=MAX_WORDS; log(f"  Truncated to {wc}w")

    violations=len(re.findall(r"[#*_`\[\]{}|<>\\]",script))
    score,issues=score_script(script,wc,violations)
    log(f"  Score: {score}/10 | {wc}w | {violations} MD")
    if score<6.9: tg(f"⚠️ Collapse Index: Score {score}/10 below gate — skipping"); sys.exit(0)

    script=inject_ctas(script,niche["name"])
    preview=" ".join(script.split()[:80])
    tg(f"📖 Collapse Index Script: {score}/10\n\n<b>{title}</b>\n{preview}...")

    log("\nSTAGE 3: Audio")
    try: audio_path,duration,_,voice=run_stage3_audio(script,None,niche["name"])
    except Exception as e: tg(f"❌ Collapse Audio FAILED: {e}"); sys.exit(1)
    log(f"  Audio: {duration:.0f}s | Voice: {voice}")

    log("\nSTAGE 4: Video")
    try: video_path=assemble_video(niche,audio_path,duration,topic)
    except Exception as e: tg(f"❌ Collapse Video FAILED: {e}"); sys.exit(1)

    log("\nSTAGE 5: Thumbnail")
    thumb_path=generate_thumbnail(niche,topic,title,thumb_text)

    description=(f"{title}\n\nThe Collapse Index documents the systems, decisions, and "
                 f"failures that are shaping collapse scenarios in real time.\n\n"
                 f"Episode: {niche['series']} | {niche['color_mode'].replace('_',' ').title()} Mode\n\n"
                 f"#CollapseIndex #AI #Technology #Cybersecurity #Documentary")

    save_pending({"video_path":video_path,"audio_path":audio_path,"thumb_path":thumb_path,
        "title":title,"description":description,"tags":tags+["collapse","technology","AI","cybersecurity","documentary"],
        "niche":niche["name"],"score":score,"wc":wc,"episode":episode})

    tg(f"✅ Collapse Index Generated\n\n<b>{title}</b>\nNiche: {niche['name']} | {score}/10 | {wc}w | {duration/60:.1f}min")
    log("\nGenerate complete.")

if __name__=="__main__": main()
