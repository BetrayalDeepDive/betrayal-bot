#!/usr/bin/env python3
"""
DeepDive Empire v10.0 - COMPLETE BUILD
=======================================
Includes all v9.0 bug fixes PLUS:
  [1] Psychological 7-stage script framework
  [2] AI-generated SEO description (300 words)
  [3] Thumbnail image generation (Pillow)
  [4] Thumbnail upload to YouTube
  [5] Background ambient music (FFmpeg generated)
  [6] YouTube Short #1 - Teaser (first 55s)
  [7] YouTube Short #2 - Recap (at 67% mark)
  [8] Both Shorts uploaded with proper metadata

Pipeline sequence:
  S1 Script → S2 SEO → S3 Audio → S4 Video → S5 Music
  → S6 Compose Main → S7 Thumbnail → S8 Upload Main
  → S9 Set Thumbnail → S10 Create+Upload Shorts
"""

import os, sys, json, re, time, random, datetime, glob, asyncio
import subprocess, textwrap
from pathlib import Path
import requests

# ─────────────────────────────────────────────────────────
# CREDENTIALS
# ─────────────────────────────────────────────────────────
GROQ_KEY       = os.environ.get("GROQ_API_KEY","")
GEMINI_KEY     = os.environ.get("GEMINI_API_KEY","")
CEREBRAS_KEY   = os.environ.get("CEREBRAS_API_KEY","")
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY","")
PIXABAY_KEY    = os.environ.get("PIXABAY_KEY","")
PEXELS_KEY     = os.environ.get("PEXELS_API_KEY","")
YT_CLIENT_ID   = os.environ.get("YOUTUBE_CLIENT_ID","")
YT_CLIENT_SEC  = os.environ.get("YOUTUBE_CLIENT_SECRET","")
YT_REFRESH     = os.environ.get("YOUTUBE_REFRESH_TOKEN","")
TG_TOKEN       = os.environ.get("TELEGRAM_TOKEN","")
TG_CHAT        = os.environ.get("TELEGRAM_CHAT_ID","")
IS_MAKEUP      = os.environ.get("IS_MAKEUP","false").lower() == "true"

# ─────────────────────────────────────────────────────────
# AI ENDPOINTS
# ─────────────────────────────────────────────────────────
GEMINI_URL     = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
CEREBRAS_URL   = "https://api.cerebras.ai/v1/chat/completions"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
GROQ_URL       = "https://api.groq.com/openai/v1/chat/completions"

# ─────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
WORK_DIR   = Path("/tmp/deepdive")
WORK_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = SCRIPT_DIR / "state.json"

# ─────────────────────────────────────────────────────────
# QUALITY CONFIG
# ─────────────────────────────────────────────────────────
MIN_WORDS  = 2000
MAX_WORDS  = 2600
MIN_GATE   = 7.0
FINAL_GATE = 6.5

# ─────────────────────────────────────────────────────────
# NICHE DEFINITIONS
# ─────────────────────────────────────────────────────────
DAY_NICHE = {0:"dark_horror", 1:"seduction_dark", 2:"psychological_trap",
             3:"supernatural_real", 4:"obsession_dark"}

NICHES = [
    {
        "name":"dark_horror","rpm":13.00,"series":"Dark Hours",
        "topics":[
            "A family discovered something had been living in their walls for three years — and only found out when the child disappeared overnight",
            "A night-shift nurse documented 14 incidents that nobody believed — until the third patient died the same way",
            "A hiker survived something in the mountains that three separate search teams still cannot explain",
            "A woman received a letter from herself — postmarked the day after she went missing",
        ],
        "dread_style":"physical dread — the horror of something real being in your space without you knowing",
        "implication":"the listener has probably been in a space where something wrong was happening and never felt it",
    },
    {
        "name":"seduction_dark","rpm":14.00,"series":"The Dark Seduction Files",
        "topics":[
            "A charismatic figure destroyed 23 lives over 8 years using the exact same method on every single target",
            "A relationship that was later revealed to have been planned in complete detail three years before they ever met",
            "The 14-stage emotional extraction system used to drain targets of their finances, identity, and relationships",
            "How one person convinced seven strangers to cut off their entire families within a single month",
        ],
        "dread_style":"the horror of realising you were chosen, not met — the illusion of a relationship dismantled",
        "implication":"the listener may have been targeted and interpreted the warning signs as love",
    },
    {
        "name":"psychological_trap","rpm":12.00,"series":"The Trap",
        "topics":[
            "A 9-stage system designed specifically to make targets financially, emotionally, and socially dependent",
            "How sustained gaslighting over 18 months made a clinical psychologist unable to trust her own memory",
            "The psychological conditioning trap that has claimed over 4,000 documented victims across 12 countries",
            "The social media manipulation campaign that systematically dismantled a person's entire sense of self",
        ],
        "dread_style":"the horror of a system — the realisation that what felt like chaos was actually a designed process",
        "implication":"the listener may currently be inside a trap and interpreting it as a bad relationship",
    },
    {
        "name":"supernatural_real","rpm":11.50,"series":"Evidence Files",
        "topics":[
            "A 2019 incident with 14 unconnected witnesses — classified by three government agencies within 72 hours",
            "Every single occupant of the building reported the identical auditory experience — later confirmed by independent instruments",
            "A medical case in which the patient accurately described events they could not have witnessed from their location",
            "A location where 11 of 300 tourists reported the exact same vision on the same afternoon — none knew each other",
        ],
        "dread_style":"the horror of evidence that cannot be explained — the collapse of the rational framework",
        "implication":"the listener has probably had an experience they dismissed that deserves to be reconsidered",
    },
    {
        "name":"obsession_dark","rpm":13.00,"series":"Consumed",
        "topics":[
            "4,380 consecutive days of obsessive behaviour — documented in meticulous handwritten detail",
            "A stalker who embedded themselves as a trusted friend for three years before a single person noticed",
            "An obsession that systematically removed every relationship, asset, and ambition the subject had built over seven years",
            "A person who dedicated an entire decade to watching someone they had never spoken a single word to",
        ],
        "dread_style":"the horror of invisible fixation — someone whose entire world revolves around a target who has no idea",
        "implication":"the listener may have someone in their life whose interest is far beyond what it appears",
    },
]

VOICES = {
    "dark_horror":        ["en-US-DavisNeural","en-GB-RyanNeural"],
    "seduction_dark":     ["en-GB-RyanNeural","en-US-AndrewNeural"],
    "psychological_trap": ["en-US-BrianNeural","en-GB-ThomasNeural"],
    "supernatural_real":  ["en-GB-RyanNeural","en-US-DavisNeural"],
    "obsession_dark":     ["en-US-AndrewNeural","en-GB-RyanNeural"],
}

BG_KEYWORDS = {
    "dark_horror":        ["dark shadow night","abandoned house dark","dark forest fog"],
    "seduction_dark":     ["dark silhouette","mystery dark room candle","dark neon city rain"],
    "psychological_trap": ["dark corridor shadow","dark labyrinth","dark spiral staircase"],
    "supernatural_real":  ["dark mysterious fog","abandoned building night","dark forest mist"],
    "obsession_dark":     ["dark window rain","surveillance night","shadow watching"],
}

# Psychological dread triggers mapped to niche
DREAD_TRIGGERS = {
    "dark_horror": [
        "slow realisation that something was wrong long before they understood it",
        "the moment the ordinary became permanently broken",
        "the detail that made everything before it feel like a lie",
        "the specific sound or sight that cannot be explained away",
    ],
    "seduction_dark": [
        "the moment the target realised the relationship had never been real",
        "the discovery of the planning that predated the first meeting",
        "the pattern that only became visible in retrospect",
        "the thing the manipulator said that they repeated to every single target",
    ],
    "psychological_trap": [
        "the stage where the target stops trusting their own memory",
        "the moment the system becomes invisible because the target defends it",
        "the specific technique that makes leaving feel impossible",
        "the realisation that the confusion was deliberately created",
    ],
    "supernatural_real": [
        "the piece of evidence that the rational explanation cannot account for",
        "the moment multiple unconnected witnesses describe the identical detail",
        "the official response that implied more than it denied",
        "the thing that was recorded that should not have been possible",
    ],
    "obsession_dark": [
        "the detail that revealed how long the observation had been happening",
        "the moment the target understood the full scope of what they were inside",
        "the action that proved the obsession had moved beyond passive watching",
        "the evidence that the obsession had shaped the target's life without their knowledge",
    ],
}

# ─────────────────────────────────────────────────────────
# UTILS
# ─────────────────────────────────────────────────────────
def log(m): print(m, flush=True)

def tg(m):
    if not TG_TOKEN or not TG_CHAT: return
    for chunk in [m[i:i+4000] for i in range(0,len(m),4000)]:
        try:
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                json={"chat_id":TG_CHAT,"text":chunk,"parse_mode":"HTML"}, timeout=15)
        except Exception as e: log(f"TG error: {e}")

def load_state():
    try: return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    except: return {}

def save_state(s):
    try: STATE_FILE.write_text(json.dumps(s, indent=2))
    except Exception as e: log(f"State save error: {e}")

def run_ffmpeg(cmd, timeout=1800, label="ffmpeg"):
    """Run an ffmpeg command with visible error output."""
    log(f"  [{label}] running...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        log(f"  [{label}] STDERR:\n{result.stderr[-3000:]}")
        raise RuntimeError(f"{label} failed (code {result.returncode})")
    log(f"  [{label}] OK")
    return result

# ─────────────────────────────────────────────────────────
# AI CALLERS
# ─────────────────────────────────────────────────────────
def call_cerebras(prompt, tokens=8000):
    if not CEREBRAS_KEY: return None
    try:
        r = requests.post(CEREBRAS_URL,
            headers={"Authorization":f"Bearer {CEREBRAS_KEY}","Content-Type":"application/json"},
            json={"model":"llama-3.3-70b","messages":[{"role":"user","content":prompt}],
                  "max_completion_tokens":min(tokens,8000),"temperature":0.88}, timeout=90)
        if r.status_code == 200:
            text = r.json().get("choices",[{}])[0].get("message",{}).get("content","")
            if text and len(text.strip()) > 100: log("✓ Cerebras"); return text
        else: log(f"Cerebras {r.status_code}: {r.text[:150]}")
    except Exception as e: log(f"Cerebras error: {e}")
    return None

def call_groq(prompt, tokens=8000):
    if not GROQ_KEY: return None
    try:
        r = requests.post(GROQ_URL,
            headers={"Authorization":f"Bearer {GROQ_KEY}","Content-Type":"application/json"},
            json={"model":"llama-3.3-70b-versatile","messages":[{"role":"user","content":prompt}],
                  "temperature":0.88,"max_tokens":min(tokens,8000)}, timeout=90)
        if r.status_code == 200:
            text = r.json().get("choices",[{}])[0].get("message",{}).get("content","")
            if text and len(text.strip()) > 100: log("✓ Groq"); return text
        else: log(f"Groq {r.status_code}: {r.text[:150]}")
    except Exception as e: log(f"Groq error: {e}")
    return None

def call_gemini(prompt, tokens=8000):
    if not GEMINI_KEY: return None
    try:
        r = requests.post(f"{GEMINI_URL}?key={GEMINI_KEY}",
            headers={"Content-Type":"application/json"},
            json={"contents":[{"parts":[{"text":prompt}]}],
                  "generationConfig":{"temperature":0.88,"maxOutputTokens":min(tokens,8192)},
                  "safetySettings":[{"category":"HARM_CATEGORY_HARASSMENT","threshold":"BLOCK_NONE"}]},
            timeout=90)
        if r.status_code == 200:
            c = r.json().get("candidates",[])
            if c:
                text = c[0]["content"]["parts"][0]["text"]
                if text and len(text.strip()) > 100: log("✓ Gemini"); return text
        else: log(f"Gemini {r.status_code}: {r.text[:150]}")
    except Exception as e: log(f"Gemini error: {e}")
    return None

def call_openrouter(prompt, tokens=8000):
    if not OPENROUTER_KEY: return None
    try:
        r = requests.post(OPENROUTER_URL,
            headers={"Authorization":f"Bearer {OPENROUTER_KEY}","Content-Type":"application/json"},
            json={"model":"meta-llama/llama-3.3-70b-instruct:free",
                  "messages":[{"role":"user","content":prompt}],
                  "max_tokens":min(tokens,8000),"temperature":0.88}, timeout=90)
        if r.status_code == 200:
            text = r.json()["choices"][0]["message"]["content"]
            if text and len(text.strip()) > 100: log("✓ OpenRouter"); return text
        else: log(f"OpenRouter {r.status_code}: {r.text[:150]}")
    except Exception as e: log(f"OpenRouter error: {e}")
    return None

def ai_generate(prompt, tokens=8000):
    for fn in [call_cerebras, call_groq, call_gemini, call_openrouter]:
        result = fn(prompt, tokens)
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
    if not r: return 0.0, ["no result"]
    s = 5.0
    w = r.get("words", 0)
    if w >= MIN_WORDS: s += 2.8
    elif w >= 1600:    s += 0.8
    else:              s -= 2.0
    v = r.get("violations", 0)
    if v == 0:   s += 2.2
    elif v <= 2: s += 0.8
    else:        s -= 1.5
    return min(round(s,1), 10.0), []

# ─────────────────────────────────────────────────────────
# STAGE 1-A: PSYCHOLOGICAL SCRIPT GENERATION
# ─────────────────────────────────────────────────────────
def build_script_prompt(niche, topic, episode, attempt):
    """
    Build a 7-stage psychological script prompt.
    This is what separates channels that retain viewers from channels that don't.
    """
    triggers = random.sample(DREAD_TRIGGERS.get(niche["name"], []), min(2, len(DREAD_TRIGGERS.get(niche["name"],[]))))
    trigger_text = "\n".join(f"  - {t}" for t in triggers)

    intensity = "dark and gripping"
    if attempt == 2: intensity = "extremely dark, psychologically disturbing"
    if attempt >= 3: intensity = "at maximum psychological intensity — deeply unsettling"

    prompt = f"""You are writing a {intensity} investigative narration script for a dark documentary YouTube channel.

SERIES: {niche["series"]}
TOPIC: {topic}
EPISODE: {episode}
STYLE: {niche["dread_style"]}

PSYCHOLOGICAL FRAMEWORK — follow this 7-stage structure EXACTLY:

STAGE 1 — COLD OPEN (first 100 words):
Begin mid-action. State the most disturbing single fact about this story in the very first sentence.
Do NOT say "today we're looking at" or "welcome back." Start as if we are already inside the story.
Example structure: "On [specific detail], [person] [disturbing action]. Nobody would find out for [time]."

STAGE 2 — THE BEFORE (next 200 words):
Show who the person was before everything changed. Make the listener care.
Specific details. Real-feeling texture. The ordinary life that is about to be permanently broken.

STAGE 3 — FIRST SIGNALS (next 250 words):
The small things that were wrong but explainable. The details that felt like coincidence.
This is where {triggers[0] if triggers else 'the first warning signs'} becomes visible.
The listener starts to feel the dread before the characters do.

STAGE 4 — ESCALATION (next 400 words):
Things accelerate. The signs stop being dismissible.
Use short sentences. One sentence per breath. The pacing must create physical tension.
Include: what they found, what they tried, why it did not work.

STAGE 5 — FALSE RESOLUTION (next 200 words):
A moment where it seems like it might be over. The relief is real — but brief.
This is essential. Without false resolution, the final reveal has no impact.

STAGE 6 — THE REAL REVEAL (next 300 words):
{triggers[1] if len(triggers) > 1 else 'The full scope of what actually happened'} becomes clear.
This is the moment that reframes everything the listener thought they understood.
Short paragraphs. One idea per paragraph. Let each one land.

STAGE 7 — PSYCHOLOGICAL IMPLICATION + CTA (final 150 words):
{niche["implication"]}
Do not state this directly — imply it. Let the listener arrive at the conclusion themselves.
Final sentence must be: "Subscribe and hit the bell. You will not want to miss what we find next."

HARD RULES:
- Total: {MIN_WORDS} to {MAX_WORDS} words. Do NOT go below {MIN_WORDS}.
- Maximum 15 words per sentence — this is narration, not prose
- NO markdown: no asterisks, hashtags, bold, bullets, headers
- Plain narration text ONLY
- No stage labels in the output — write the script straight through

Write the complete script now. Begin with the cold open. Nothing before it."""

    return prompt

def generate_title_candidates(niche, topic):
    """Generate 5 CTR-optimized title options and return the best one."""
    prompt = f"""Generate 5 YouTube video titles for a dark investigative documentary.
Series: {niche["series"]}
Topic: {topic}

Rules:
- Each title 55-70 characters
- Must open a psychological loop — curiosity that cannot be closed without watching
- Use specific numbers, durations, or counts where they fit naturally
- Dark, investigative, documentary tone — not sensational clickbait
- No quotation marks. No colons unless essential.

Return ONLY 5 titles, one per line, no numbering, no other text."""

    result = ai_generate(prompt, tokens=400)
    if not result:
        return f"{niche['series']}: {topic[:55]}"

    hook_words = ["never","nobody","secret","revealed","truth","years","days",
                  "finally","hidden","classified","documented","found","knew","told"]
    lines = [l.strip() for l in result.strip().splitlines() if 40 <= len(l.strip()) <= 75]

    def title_score(t):
        s = 0
        if 55 <= len(t) <= 70: s += 3
        for hw in hook_words:
            if hw.lower() in t.lower(): s += 2
        if any(c.isdigit() for c in t): s += 2
        return s

    if lines:
        lines.sort(key=title_score, reverse=True)
        return lines[0]
    return f"{niche['series']}: {topic[:55]}"

def generate_script_content(niche, topic, episode, attempt):
    """Generate the full script using the psychological framework."""
    prompt = build_script_prompt(niche, topic, episode, attempt)
    result = ai_generate(prompt, tokens=8000)
    if not result: return None

    script = strip_md(strip_md(result))
    wc     = len(script.split())
    violations = len(re.findall(r'[#*_`\[\]{}<>\\]', script))

    log(f"  Script: {wc} words, {violations} violations")

    # Expand if too short
    if wc < MIN_WORDS:
        deficit = MIN_WORDS - wc
        log(f"  Too short by {deficit} words. Expanding...")
        expand = f"""This narration script is {wc} words and needs to reach {MIN_WORDS} words minimum.
Expand it by {deficit} words. Deepen the psychological analysis in stages 3, 4, and 6.
Add specific sensory details, witness reactions, and emotional texture.
Keep ALL existing content. Add only to what is already there.
Return the COMPLETE expanded script with NO markdown formatting.

SCRIPT:
{script}"""
        result2 = ai_generate(expand, tokens=8000)
        if result2:
            clean2 = strip_md(strip_md(result2))
            if len(clean2.split()) > wc:
                script = clean2
                wc = len(script.split())
                violations = len(re.findall(r'[#*_`\[\]{}<>\\]', script))
                log(f"  Expanded to: {wc} words")

    return {"script":script, "words":wc, "violations":violations}

# ─────────────────────────────────────────────────────────
# STAGE 1-B: SEO DESCRIPTION GENERATOR
# ─────────────────────────────────────────────────────────
def generate_seo_description(niche, topic, title, episode, audio_duration_seconds=0):
    """
    Generate a 300-word SEO-rich description.
    YouTube's search algorithm reads the first 200 characters heavily.
    """
    duration_min = int(audio_duration_seconds / 60) if audio_duration_seconds > 0 else 15

    prompt = f"""Write a YouTube video description for a dark investigative documentary.

Title: {title}
Series: {niche["series"]}, Episode {episode}
Topic: {topic}
Duration: approximately {duration_min} minutes

Structure:
1. First 2 sentences (the hook): Restate the core mystery/disturbing fact. Creates urgency to watch.
2. Next 3-4 sentences: What the video investigates. Do NOT spoil the reveal.
3. One line: "Watch until the end — the final revelation changes everything."
4. Timestamps section (approximate, based on {duration_min} min video):
   - 0:00 The opening
   - 2:00 Background
   - 5:00 First warning signs
   - 9:00 Escalation
   - 13:00 The reveal
   - {duration_min-1}:00 What this means
5. Keyword section: 10-15 natural sentences using these themes: dark documentary, true investigation,
   psychological analysis, hidden truth, classified evidence, real story, disturbing facts,
   {niche["name"].replace("_"," ")}, investigative narration, dark nonfiction
6. Final line: "Subscribe for new investigations every week."
7. Hashtag line: 8-10 relevant hashtags

Total: 280-350 words. No markdown. Plain text only. Real paragraphs."""

    result = ai_generate(prompt, tokens=1200)
    if result:
        desc = strip_md(result)
        # Append required AI disclosure
        desc += "\n\n⚠️ This video uses AI-assisted narration and editing."
        return desc

    # Fallback description
    return (
        f"{title}\n\n"
        f"Episode {episode} of {niche['series']}. An investigation into {topic.lower()}.\n\n"
        f"This channel documents real cases of {niche['name'].replace('_',' ')} through "
        f"investigative narration and archival evidence.\n\n"
        f"Subscribe for new investigations every week.\n\n"
        f"#{niche['name'].replace('_','')} #documentary #investigation #darknonfiction\n\n"
        f"⚠️ This video uses AI-assisted narration and editing."
    )

# ─────────────────────────────────────────────────────────
# STAGE 1: FULL SCRIPT STAGE (runs generation + title)
# ─────────────────────────────────────────────────────────
def run_stage1(state):
    log("="*70)
    log("STAGE 1: Script Generation (Psychological Framework)")
    log("="*70)

    name  = DAY_NICHE.get(datetime.datetime.now().weekday(), "dark_horror")
    niche = next(x for x in NICHES if x["name"] == name)

    voice   = random.choice(VOICES.get(niche["name"], ["en-GB-RyanNeural"]))
    topic   = random.choice(niche["topics"])
    episode = state.get("episode_count", 0) + 1

    log(f"Niche:   {niche['name']}")
    log(f"Topic:   {topic}")
    log(f"Voice:   {voice}")
    log(f"Episode: {episode}")

    best_result = None
    best_score  = 0.0

    for attempt in range(1, 4):
        log(f"\nAttempt {attempt}/3...")
        content = generate_script_content(niche, topic, episode, attempt)
        score, _ = score_result(content)
        log(f"Score: {score}/10")
        if score > best_score:
            best_score  = score
            best_result = content
        if score >= MIN_GATE:
            log("✓ Quality gate passed")
            break
        elif attempt == 3 and score >= FINAL_GATE:
            log(f"⚠ Final gate passed at {score}")
            break
        elif attempt < 3:
            log(f"Below gate ({score} < {MIN_GATE}), retrying...")

    if not best_result or best_score < FINAL_GATE:
        log(f"FATAL: Script generation failed. Best: {best_score}/10")
        tg(f"❌ Script generation failed. Best score: {best_score}/10")
        sys.exit(1)

    title    = generate_title_candidates(niche, topic)
    tags     = ["documentary","investigation","true story","dark","mystery",
                "psychological","narration","evidence","real","nonfiction",
                niche["name"].replace("_",""), niche["series"].lower().replace(" ","")]
    thumb_text = " ".join(topic.split()[:3]).upper()  # First 3 words in caps for thumbnail

    result = {
        "script":     best_result["script"],
        "words":      best_result["words"],
        "violations": best_result["violations"],
        "title":      title,
        "thumb_text": thumb_text,
        "tags":       tags,
        "topic":      topic,
    }

    log(f"\n✓ Stage 1 complete")
    log(f"  Title:  {title}")
    log(f"  Words:  {result['words']}")
    log(f"  Score:  {best_score}/10")

    tg(f"🎬 <b>Script Ready</b>\n📺 {title}\n📝 {result['words']} words | ⭐ {best_score}/10\n⏳ Generating audio now...")
    return niche, voice, episode, result, best_score

# ─────────────────────────────────────────────────────────
# STAGE 2: AUDIO GENERATION
# ─────────────────────────────────────────────────────────
async def _tts_generate(text, voice, output_path):
    import edge_tts
    communicate = edge_tts.Communicate(text=text, voice=voice, rate="-8%", volume="+0%")
    await communicate.save(output_path)

def get_media_duration(path):
    try:
        r = subprocess.run(
            ["ffprobe","-v","quiet","-show_entries","format=duration","-of","csv=p=0", str(path)],
            capture_output=True, text=True, timeout=30)
        return float(r.stdout.strip())
    except: return 0.0

def run_stage2_audio(script, voice):
    log("="*70)
    log("STAGE 2: Audio Generation")
    log("="*70)

    audio_file = str(WORK_DIR / "narration.mp3")
    log(f"  Words: {len(script.split())}  |  Voice: {voice}")

    success = False
    voices_to_try = [voice] + [v for v in
        ["en-GB-RyanNeural","en-US-BrianNeural","en-US-DavisNeural","en-US-AndrewNeural"]
        if v != voice]

    for v in voices_to_try:
        try:
            log(f"  Trying voice: {v}")
            asyncio.run(_tts_generate(script, v, audio_file))
            if Path(audio_file).exists() and Path(audio_file).stat().st_size > 50000:
                duration = get_media_duration(audio_file)
                log(f"✓ Audio: {duration:.1f}s ({duration/60:.1f} min) via {v}")
                return audio_file, duration, v
        except Exception as e:
            log(f"  {v} error: {e}")

    log("FATAL: All TTS voices failed")
    tg("❌ Audio generation failed")
    sys.exit(1)

# ─────────────────────────────────────────────────────────
# STAGE 3: VIDEO DOWNLOAD
# ─────────────────────────────────────────────────────────
def download_pixabay_video(keywords):
    if not PIXABAY_KEY: return None
    for kw in keywords:
        try:
            r = requests.get("https://pixabay.com/api/videos/",
                params={"key":PIXABAY_KEY,"q":kw,"per_page":5,"video_type":"film","orientation":"horizontal"},
                timeout=15)
            if r.status_code == 200 and r.json().get("hits"):
                hit = max(r.json()["hits"], key=lambda h: h.get("duration",0))
                url = hit["videos"]["medium"]["url"]
                path = str(WORK_DIR / "background.mp4")
                log(f"  Pixabay: '{kw}' ({hit.get('duration',0)}s)")
                with requests.get(url, timeout=60, stream=True) as dl:
                    dl.raise_for_status()
                    with open(path,'wb') as f:
                        for chunk in dl.iter_content(32768): f.write(chunk)
                if Path(path).stat().st_size > 50000:
                    log(f"✓ Pixabay video ({Path(path).stat().st_size//1024}KB)")
                    return path
        except Exception as e: log(f"  Pixabay '{kw}': {e}")
    return None

def download_pexels_video(keywords):
    if not PEXELS_KEY: return None
    for kw in keywords:
        try:
            r = requests.get("https://api.pexels.com/videos/search",
                headers={"Authorization":PEXELS_KEY},
                params={"query":kw,"per_page":5,"orientation":"landscape"}, timeout=15)
            if r.status_code == 200 and r.json().get("videos"):
                video = r.json()["videos"][0]
                files = sorted(video.get("video_files",[]), key=lambda f: f.get("width",0))
                target = next((f for f in files if f.get("width",0)>=720), files[-1]) if files else None
                if not target: continue
                path = str(WORK_DIR / "background.mp4")
                log(f"  Pexels: '{kw}'")
                with requests.get(target["link"], timeout=60, stream=True) as dl:
                    dl.raise_for_status()
                    with open(path,'wb') as f:
                        for chunk in dl.iter_content(32768): f.write(chunk)
                if Path(path).stat().st_size > 50000:
                    log(f"✓ Pexels video ({Path(path).stat().st_size//1024}KB)")
                    return path
        except Exception as e: log(f"  Pexels '{kw}': {e}")
    return None

def create_black_video_fallback(duration_seconds):
    path = str(WORK_DIR / "background.mp4")
    duration = max(int(duration_seconds) + 10, 60)
    run_ffmpeg([
        "ffmpeg","-y","-f","lavfi",
        "-i",f"color=c=black:size=1280x720:rate=24:duration={duration}",
        "-c:v","libx264","-pix_fmt","yuv420p", path
    ], label="black-video-fallback")
    log(f"✓ Black video fallback ({duration}s)")
    return path

def run_stage3_video(niche, audio_duration):
    log("="*70)
    log("STAGE 3: Background Video")
    log("="*70)
    keywords = BG_KEYWORDS.get(niche["name"], ["dark shadow night"])
    v = download_pixabay_video(keywords)
    if v: return v
    log("  Pixabay failed → Pexels")
    v = download_pexels_video(keywords)
    if v: return v
    log("  Both APIs failed → FFmpeg black fallback")
    return create_black_video_fallback(audio_duration)

# ─────────────────────────────────────────────────────────
# STAGE 4: BACKGROUND MUSIC GENERATION
# ─────────────────────────────────────────────────────────
def generate_ambient_music(duration_seconds):
    """
    Generate dark ambient background music using FFmpeg.
    Two-layer approach: deep bass sine drone + subtle high noise at very low volume.
    Mixed to sit -25dB under normal narration so it's felt, not heard.
    """
    log("="*70)
    log("STAGE 4: Background Music (FFmpeg ambient generator)")
    log("="*70)

    music_path = str(WORK_DIR / "music.mp3")
    # Add 10 seconds buffer so music doesn't cut at end
    duration = int(duration_seconds) + 15

    # Layer 1: 55Hz bass drone (sub-bass felt more than heard)
    # Layer 2: 110Hz secondary drone (adds body)
    # Layer 3: Very low white noise (adds texture/atmosphere)
    # Combined at very low volume, low-pass filtered for warmth
    cmd = [
        "ffmpeg", "-y",
        "-f","lavfi","-i",f"sine=frequency=55:duration={duration}",
        "-f","lavfi","-i",f"sine=frequency=110:duration={duration}",
        "-f","lavfi","-i",f"aevalsrc=random(0)*0.004:duration={duration}",
        "-filter_complex",
        "[0]volume=0.06[a];"
        "[1]volume=0.03[b];"
        "[2]volume=0.5[c];"
        "[a][b][c]amix=inputs=3:duration=first,"
        "lowpass=f=300,"
        "highpass=f=30,"
        "volume=0.12[out]",
        "-map","[out]",
        "-c:a","mp3","-q:a","4",
        music_path
    ]
    run_ffmpeg(cmd, label="music-gen")
    log(f"✓ Ambient music generated ({duration}s)")
    return music_path

# ─────────────────────────────────────────────────────────
# STAGE 5: THUMBNAIL GENERATION
# ─────────────────────────────────────────────────────────
def generate_thumbnail(thumb_text, niche_name, title):
    """
    Create a 1280x720 thumbnail using Pillow.
    Design: Black background, blood-red 3-word hook text (massive),
    white subtitle text below, subtle red corner vignette.
    """
    log("="*70)
    log("STAGE 5: Thumbnail Generation")
    log("="*70)

    thumb_path = str(WORK_DIR / "thumbnail.jpg")

    try:
        from PIL import Image, ImageDraw, ImageFont, ImageFilter

        W, H = 1280, 720
        img  = Image.new("RGB", (W, H), color=(0, 0, 0))
        draw = ImageDraw.Draw(img)

        # ── Red vignette overlay (atmospheric) ──
        vignette = Image.new("RGBA", (W, H), (0,0,0,0))
        vdraw    = ImageDraw.Draw(vignette)
        for i in range(180):
            alpha = int(160 * (1 - i/180))
            vdraw.rectangle([i, i, W-i, H-i], outline=(80,0,0,alpha))
        img.paste(Image.new("RGB",(W,H),(80,0,0)),
                  mask=vignette.split()[3])

        # ── Font paths (Ubuntu has these) ──
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
        ]
        def get_font(size):
            for fp in font_paths:
                if Path(fp).exists():
                    try: return ImageFont.truetype(fp, size)
                    except: pass
            return ImageFont.load_default()

        # ── Main hook text (blood red, huge) ──
        # Split thumb_text into max 2 lines
        words = thumb_text.split()
        if len(words) <= 3:
            lines = [thumb_text]
        else:
            mid   = len(words) // 2
            lines = [" ".join(words[:mid]), " ".join(words[mid:])]

        font_main = get_font(120)
        red_color = (200, 0, 0)
        shadow_c  = (40, 0, 0)

        total_text_h = len(lines) * 130
        start_y = (H - total_text_h) // 2 - 40

        for i, line in enumerate(lines):
            y = start_y + i * 130
            bbox = draw.textbbox((0,0), line, font=font_main)
            tw   = bbox[2] - bbox[0]
            x    = (W - tw) // 2
            # Shadow
            draw.text((x+4, y+4), line, font=font_main, fill=shadow_c)
            # Main text
            draw.text((x, y), line, font=font_main, fill=red_color)

        # ── Sub-title (white, smaller) ──
        sub_text = title[:60] + ("…" if len(title) > 60 else "")
        font_sub = get_font(36)
        bbox_sub = draw.textbbox((0,0), sub_text, font=font_sub)
        sub_x    = (W - (bbox_sub[2]-bbox_sub[0])) // 2
        sub_y    = start_y + len(lines)*130 + 20
        draw.text((sub_x+2, sub_y+2), sub_text, font=font_sub, fill=(30,30,30))
        draw.text((sub_x, sub_y), sub_text, font=font_sub, fill=(220,220,220))

        # ── Series badge (top-left corner) ──
        font_badge = get_font(28)
        badge_text = f"● DARK DOCUMENTARY"
        draw.text((30, 25), badge_text, font=font_badge, fill=(160,0,0))

        img.save(thumb_path, "JPEG", quality=95)
        log(f"✓ Thumbnail created: {Path(thumb_path).stat().st_size//1024}KB")
        return thumb_path

    except ImportError:
        log("  Pillow not available, using ImageMagick fallback")
        return generate_thumbnail_imagemagick(thumb_text, title, thumb_path)
    except Exception as e:
        log(f"  Pillow error: {e}, trying ImageMagick")
        return generate_thumbnail_imagemagick(thumb_text, title, thumb_path)

def generate_thumbnail_imagemagick(thumb_text, title, thumb_path):
    """Fallback thumbnail using ImageMagick convert (pre-installed on Ubuntu)."""
    safe_text  = thumb_text.replace("'","").replace('"','')[:30]
    safe_title = title[:55].replace("'","").replace('"','')
    cmd = [
        "convert",
        "-size","1280x720","xc:black",
        "-fill","#C80000",
        "-pointsize","120",
        "-gravity","Center",
        "-annotate","0", safe_text,
        "-fill","#DCDCDC",
        "-pointsize","36",
        "-gravity","South",
        "-annotate","0+0+60", safe_title,
        "-fill","#A00000",
        "-pointsize","28",
        "-gravity","NorthWest",
        "-annotate","0+30+25","● DARK DOCUMENTARY",
        thumb_path
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=30)
        log(f"✓ Thumbnail via ImageMagick")
        return thumb_path
    except Exception as e:
        log(f"  ImageMagick error: {e} — skipping thumbnail")
        return None

# ─────────────────────────────────────────────────────────
# STAGE 6: COMPOSE MAIN VIDEO
# ─────────────────────────────────────────────────────────
def compose_main_video(narration_path, bg_video_path, music_path, audio_duration):
    """
    Merge: looped background video + narration audio + ambient music → final.mp4
    Music sits at -25dB under narration so it's atmospheric, not distracting.
    """
    log("="*70)
    log("STAGE 6: Compose Main Video (video + narration + music)")
    log("="*70)

    for p in [narration_path, bg_video_path]:
        if not Path(p).exists():
            raise FileNotFoundError(f"Missing: {p}")

    final_path = str(WORK_DIR / "final.mp4")
    bg_duration = get_media_duration(bg_video_path)
    loop_count  = max(int(audio_duration / max(bg_duration, 1)) + 2, 1)

    log(f"  BG video:  {bg_duration:.1f}s → looped {loop_count}x")
    log(f"  Narration: {audio_duration:.1f}s")
    log(f"  Output:    {audio_duration:.1f}s")

    has_music = music_path and Path(music_path).exists()

    if has_music:
        # 3-stream: video + narration + music
        # Mix narration at 1.0 and music at 0.08 (very subtle atmosphere)
        cmd = [
            "ffmpeg","-y",
            "-stream_loop", str(loop_count), "-i", bg_video_path,
            "-i", narration_path,
            "-i", music_path,
            "-filter_complex",
            "[1:a]volume=1.0[narr];"
            "[2:a]volume=0.08[music];"
            "[narr][music]amix=inputs=2:duration=first:dropout_transition=3[aout]",
            "-map","0:v",
            "-map","[aout]",
            "-t", str(audio_duration),
            "-c:v","libx264","-preset","fast","-crf","23",
            "-c:a","aac","-b:a","192k",
            "-pix_fmt","yuv420p",
            "-vf","scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2",
            "-movflags","+faststart",
            final_path
        ]
        log("  Composing with music layer...")
    else:
        # 2-stream: video + narration only
        cmd = [
            "ffmpeg","-y",
            "-stream_loop", str(loop_count), "-i", bg_video_path,
            "-i", narration_path,
            "-map","0:v", "-map","1:a",
            "-t", str(audio_duration),
            "-c:v","libx264","-preset","fast","-crf","23",
            "-c:a","aac","-b:a","192k",
            "-pix_fmt","yuv420p",
            "-vf","scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2",
            "-movflags","+faststart",
            final_path
        ]
        log("  Composing without music (music file unavailable)...")

    run_ffmpeg(cmd, timeout=1800, label="compose-main")

    if not Path(final_path).exists():
        raise FileNotFoundError("Final video not created")

    size_mb = Path(final_path).stat().st_size // (1024*1024)
    log(f"✓ Main video composed: {size_mb}MB, {audio_duration/60:.1f} min")
    return final_path

# ─────────────────────────────────────────────────────────
# STAGE 7: CREATE YOUTUBE SHORTS
# ─────────────────────────────────────────────────────────
def extract_audio_segment(narration_path, start_sec, duration_sec, output_path):
    """Extract a segment from the narration audio."""
    run_ffmpeg([
        "ffmpeg","-y",
        "-i", narration_path,
        "-ss", str(start_sec),
        "-t", str(duration_sec),
        "-c:a","copy",
        output_path
    ], label=f"audio-segment-{int(start_sec)}s")

def compose_short(narration_segment, bg_video_path, music_path,
                  segment_duration, output_path, label="short"):
    """
    Compose a YouTube Short (vertical 1080x1920 or 720x1280).
    Crop the landscape background to vertical using center crop.
    """
    bg_duration = get_media_duration(bg_video_path)
    loop_count  = max(int(segment_duration / max(bg_duration, 1)) + 2, 1)
    has_music   = music_path and Path(music_path).exists()

    # Vertical crop: from 1280x720, crop center to 405x720, scale to 1080x1920
    # OR simpler: crop to 9:16 aspect ratio from center
    vf = ("scale=1280:720:force_original_aspect_ratio=decrease,"
          "pad=1280:720:(ow-iw)/2:(oh-ih)/2,"
          "crop=405:720:(iw-405)/2:0,"
          "scale=1080:1920")

    if has_music:
        cmd = [
            "ffmpeg","-y",
            "-stream_loop", str(loop_count), "-i", bg_video_path,
            "-i", narration_segment,
            "-i", music_path,
            "-filter_complex",
            "[1:a]volume=1.0[narr];"
            "[2:a]volume=0.08[music];"
            "[narr][music]amix=inputs=2:duration=first:dropout_transition=1[aout]",
            "-map","0:v", "-map","[aout]",
            "-t", str(segment_duration),
            "-c:v","libx264","-preset","fast","-crf","23",
            "-c:a","aac","-b:a","128k",
            "-pix_fmt","yuv420p",
            "-vf", vf,
            "-movflags","+faststart",
            output_path
        ]
    else:
        cmd = [
            "ffmpeg","-y",
            "-stream_loop", str(loop_count), "-i", bg_video_path,
            "-i", narration_segment,
            "-map","0:v", "-map","1:a",
            "-t", str(segment_duration),
            "-c:v","libx264","-preset","fast","-crf","23",
            "-c:a","aac","-b:a","128k",
            "-pix_fmt","yuv420p",
            "-vf", vf,
            "-movflags","+faststart",
            output_path
        ]

    run_ffmpeg(cmd, timeout=300, label=label)
    return output_path

def create_shorts(narration_path, bg_video_path, music_path,
                  audio_duration, title, niche):
    """
    Create 2 YouTube Shorts:
      Short 1 (Teaser):  First 55s of narration — the cold open hook
      Short 2 (Recap):   55s starting at 67% through — the reveal moment
    """
    log("="*70)
    log("STAGE 7: Creating YouTube Shorts")
    log("="*70)

    SHORT_DURATION = 55  # Max 55s to stay under 60s Shorts limit
    shorts = []

    # ── Short 1: Teaser (first 55 seconds) ──
    seg1_duration = min(SHORT_DURATION, audio_duration * 0.15)
    seg1_duration = max(seg1_duration, 30)
    seg1_audio    = str(WORK_DIR / "short1_audio.mp3")
    seg1_video    = str(WORK_DIR / "short1.mp4")

    log(f"  Short 1 (Teaser): 0s → {seg1_duration:.0f}s")
    try:
        extract_audio_segment(narration_path, 0, seg1_duration, seg1_audio)
        compose_short(seg1_audio, bg_video_path, music_path,
                      seg1_duration, seg1_video, label="short1")
        shorts.append({
            "path":        seg1_video,
            "title":       f"{title[:60]} #Shorts",
            "description": f"Full investigation: search for '{title}' on this channel.\n\n#Shorts #{niche['name'].replace('_','')} #documentary #dark",
            "type":        "teaser"
        })
        log(f"✓ Short 1 created: {Path(seg1_video).stat().st_size//1024}KB")
    except Exception as e:
        log(f"  Short 1 failed (non-fatal): {e}")

    # ── Short 2: Recap (starting at 67% through narration) ──
    seg2_start    = audio_duration * 0.67
    seg2_duration = min(SHORT_DURATION, audio_duration - seg2_start)
    seg2_duration = max(seg2_duration, 20)
    seg2_audio    = str(WORK_DIR / "short2_audio.mp3")
    seg2_video    = str(WORK_DIR / "short2.mp4")

    log(f"  Short 2 (Recap): {seg2_start:.0f}s → {seg2_start+seg2_duration:.0f}s")
    try:
        extract_audio_segment(narration_path, seg2_start, seg2_duration, seg2_audio)
        compose_short(seg2_audio, bg_video_path, music_path,
                      seg2_duration, seg2_video, label="short2")
        shorts.append({
            "path":        seg2_video,
            "title":       f"The Truth Revealed — {title[:40]} #Shorts",
            "description": f"Watch the full investigation: search '{title}' on this channel.\n\n#Shorts #{niche['name'].replace('_','')} #reveal #dark",
            "type":        "recap"
        })
        log(f"✓ Short 2 created: {Path(seg2_video).stat().st_size//1024}KB")
    except Exception as e:
        log(f"  Short 2 failed (non-fatal): {e}")

    return shorts

# ─────────────────────────────────────────────────────────
# YOUTUBE API
# ─────────────────────────────────────────────────────────
def get_yt_token():
    r = requests.post("https://oauth2.googleapis.com/token",
        data={"client_id":YT_CLIENT_ID,"client_secret":YT_CLIENT_SEC,
              "refresh_token":YT_REFRESH,"grant_type":"refresh_token"}, timeout=30)
    d = r.json()
    if "access_token" not in d:
        raise Exception(f"YouTube token failed: {d.get('error')} — {d.get('error_description')}")
    log("✓ YouTube token obtained")
    return d["access_token"]

def upload_yt(path, title, desc, tags, token=None, privacy="public"):
    """Upload a video to YouTube using chunked resumable upload."""
    log(f"\n  Uploading: {Path(path).name} ({Path(path).stat().st_size//(1024*1024)}MB)")
    log(f"  Title: {title[:80]}")

    if not token:
        token = get_yt_token()

    file_size = Path(path).stat().st_size

    # Initiate session
    init = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Upload-Content-Length": str(file_size),
            "X-Upload-Content-Type": "video/mp4",
        },
        json={
            "snippet": {"title":title[:100],"description":desc,"tags":tags[:15],"categoryId":"22"},
            "status":  {"privacyStatus":privacy,"selfDeclaredMadeForKids":False,"madeForKids":False}
        },
        timeout=30
    )
    upload_url = init.headers.get("Location")
    if not upload_url:
        raise Exception(f"No upload URL. Status: {init.status_code}. Body: {init.text[:400]}")

    # Chunked upload with retry
    CHUNK    = 16 * 1024 * 1024   # 16MB
    uploaded = 0
    retries  = 0

    with open(path, "rb") as f:
        while uploaded < file_size:
            chunk_data = f.read(CHUNK)
            if not chunk_data: break
            chunk_end = uploaded + len(chunk_data) - 1
            try:
                up = requests.put(upload_url,
                    headers={
                        "Authorization":  f"Bearer {token}",
                        "Content-Length": str(len(chunk_data)),
                        "Content-Range":  f"bytes {uploaded}-{chunk_end}/{file_size}",
                        "Content-Type":   "video/mp4",
                    },
                    data=chunk_data, timeout=600)
                if up.status_code in [200, 201]:
                    vid_id = up.json().get("id")
                    yt_url = f"https://www.youtube.com/watch?v={vid_id}"
                    log(f"  ✓ Upload complete: {yt_url}")
                    return yt_url, vid_id
                elif up.status_code == 308:
                    rh = up.headers.get("Range","")
                    uploaded = int(rh.split("-")[1]) + 1 if rh else uploaded + len(chunk_data)
                    log(f"  {int(uploaded*100/file_size)}% uploaded")
                    retries = 0
                elif up.status_code in [500,502,503,504]:
                    retries += 1
                    if retries > 5: raise Exception(f"Upload failed after 5 retries ({up.status_code})")
                    wait = 2 ** retries
                    log(f"  Server error {up.status_code}, retry {retries}/5 in {wait}s")
                    time.sleep(wait)
                else:
                    raise Exception(f"Upload failed HTTP {up.status_code}: {up.text[:300]}")
            except requests.exceptions.Timeout:
                retries += 1
                if retries > 5: raise Exception("Upload timed out repeatedly")
                log(f"  Timeout, retry {retries}/5...")
                time.sleep(5)

    raise Exception("Upload loop ended without completion")

def upload_thumbnail(video_id, thumb_path, token):
    """Upload custom thumbnail to a YouTube video."""
    if not thumb_path or not Path(thumb_path).exists():
        log("  No thumbnail to upload")
        return
    try:
        log(f"  Uploading thumbnail...")
        with open(thumb_path, "rb") as f:
            r = requests.post(
                f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={video_id}&uploadType=media",
                headers={"Authorization":f"Bearer {token}","Content-Type":"image/jpeg"},
                data=f.read(), timeout=60
            )
        if r.status_code in [200,201]:
            log("✓ Thumbnail uploaded")
        else:
            log(f"  Thumbnail upload failed: {r.status_code} — {r.text[:200]}")
    except Exception as e:
        log(f"  Thumbnail upload error (non-fatal): {e}")

# ─────────────────────────────────────────────────────────
# CLEANUP
# ─────────────────────────────────────────────────────────
def cleanup():
    try:
        for f in glob.glob(str(WORK_DIR / "*")):
            if os.path.isfile(f): os.remove(f)
        log("✓ Temp files cleaned")
    except Exception as e:
        log(f"Cleanup error (non-fatal): {e}")

# ─────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────
def main():
    log("="*70)
    log("DEEPDIVE EMPIRE v10.0")
    log("="*70)
    log(f"Time:   {datetime.datetime.now().isoformat()}")
    log(f"Day:    {['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][datetime.datetime.now().weekday()]}")
    log(f"Makeup: {IS_MAKEUP}")
    log("="*70)

    state = load_state()
    log(f"Episodes uploaded so far: {state.get('episode_count', 0)}")

    try:
        # ── Stage 1: Script (psychological framework) ──
        niche, voice, episode, result, score = run_stage1(state)

        # ── Stage 2: Audio ──
        audio_path, audio_duration, voice_used = run_stage2_audio(result["script"], voice)

        # ── Stage 2B: SEO Description (uses actual duration now) ──
        log("  Building SEO description...")
        description = generate_seo_description(
            niche, result["topic"], result["title"], episode, audio_duration)

        # ── Stage 3: Background Video ──
        bg_video_path = run_stage3_video(niche, audio_duration)

        # ── Stage 4: Background Music ──
        music_path = generate_ambient_music(audio_duration)

        # ── Stage 5: Thumbnail ──
        thumb_path = generate_thumbnail(result["thumb_text"], niche["name"], result["title"])

        # ── Stage 6: Compose Main Video ──
        final_video = compose_main_video(audio_path, bg_video_path, music_path, audio_duration)

        # ── Stage 7: Create Shorts ──
        shorts = create_shorts(audio_path, bg_video_path, music_path,
                               audio_duration, result["title"], niche)

        # ── Stage 8: Upload Main Video ──
        log("="*70)
        log("STAGE 8: Upload Main Video")
        log("="*70)
        token = get_yt_token()
        yt_url, video_id = upload_yt(
            final_video, result["title"], description, result["tags"], token=token)

        # ── Stage 9: Upload Thumbnail ──
        log("="*70)
        log("STAGE 9: Set Thumbnail")
        log("="*70)
        upload_thumbnail(video_id, thumb_path, token)

        # ── Stage 10: Upload Shorts ──
        log("="*70)
        log("STAGE 10: Upload Shorts")
        log("="*70)
        short_urls = []
        for i, short in enumerate(shorts, 1):
            log(f"\n  Short {i} ({short['type']}):")
            try:
                s_url, _ = upload_yt(
                    short["path"], short["title"], short["description"],
                    result["tags"][:8], token=token)
                short_urls.append(s_url)
            except Exception as e:
                log(f"  Short {i} upload failed (non-fatal): {e}")

        # ── Update state ──
        state["episode_count"]  = episode
        state["last_upload"]    = datetime.datetime.now().isoformat()
        state["last_title"]     = result["title"]
        state["last_url"]       = yt_url
        state["total_uploads"]  = state.get("total_uploads", 0) + 1
        state["total_shorts"]   = state.get("total_shorts", 0) + len(short_urls)
        save_state(state)

        # ── Cleanup ──
        cleanup()

        # ── Final Telegram notification ──
        shorts_text = "\n".join([f"🩳 {u}" for u in short_urls]) if short_urls else "⚠️ Shorts skipped"
        success_msg = (
            f"✅ <b>DeepDive Empire v10.0 — Published!</b>\n\n"
            f"📺 <b>{result['title']}</b>\n"
            f"🔗 {yt_url}\n\n"
            f"🎯 Niche:    {niche['name']}\n"
            f"🔊 Voice:    {voice_used}\n"
            f"📝 Words:    {result['words']}\n"
            f"⏱ Duration: {audio_duration/60:.1f} min\n"
            f"⭐ Score:    {score}/10\n"
            f"📊 Episode:  {episode} | Total: {state['total_uploads']}\n\n"
            f"<b>Shorts:</b>\n{shorts_text}"
        )
        tg(success_msg)

        log("="*70)
        log(f"✅ SUCCESS: {yt_url}")
        for s_url in short_urls:
            log(f"✅ SHORT:   {s_url}")
        log("="*70)

    except Exception as e:
        import traceback
        log(f"\nPIPELINE FAILED: {e}")
        log(traceback.format_exc())
        tg(f"❌ <b>Pipeline FAILED</b>\n\nError: {str(e)[:500]}")
        sys.exit(1)

if __name__ == "__main__":
    main()
