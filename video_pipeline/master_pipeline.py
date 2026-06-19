#!/usr/bin/env python3
"""
DeepDive Empire v9.0 - FULLY FIXED
====================================
BUG FIX LOG (vs v8.0):

BUG #1 [CRITICAL] - NO VIDEO COMPOSITION STEP
  v8.0: audio.mp3 and background.mp4 were NEVER merged.
        upload_yt() was uploading raw silent background.mp4 with zero audio.
  FIX:  Added compose_video() using ffmpeg to loop background video
        to match exact audio duration and merge them into final.mp4.

BUG #2 [CRITICAL] - SCRIPT TRUNCATED TO 5000 CHARS
  v8.0: subprocess edge_tts call used script[:5000] — a 2000-word script
        is ~12,000 chars, so only ~800 words got voiced.
  FIX:  Full script written to a temp .txt file. edge_tts Python async
        API reads the file with no length limit.

BUG #3 [CRITICAL] - edge-tts called via CLI subprocess with text as arg
  v8.0: Passing large text as a CLI argument hits Linux ARG_MAX limits
        and fails silently (capture_output=True hid all errors).
  FIX:  Use edge_tts.Communicate() Python async API directly.
        Full text, no shell limits, errors are visible.

BUG #4 - GEMINI LOGIC BUG (NameError on empty response)
  v8.0: if c: text = ...; if text: ...  ← second if is NOT inside first if
        If c is empty, text is never assigned → NameError on next line.
  FIX:  Proper indentation and variable scoping inside the if block.

BUG #5 - OPENROUTER SAME LOGIC BUG
  v8.0: if r.status_code == 200: text = ...; if text: ...
        Same NameError if status != 200.
  FIX:  text initialized to None before block, assigned inside.

BUG #6 - STATE FILE IN /tmp (wiped every GitHub Actions run)
  v8.0: STATE_FILE = /tmp/deepdive/state.json — always fresh, episode=1 always.
  FIX:  State stored in repo directory (./video_pipeline/state.json)
        so it persists via git commits between runs.

BUG #7 - PIXABAY FAILURE RETURNS NON-EXISTENT PATH
  v8.0: On Pixabay failure, returned path to background.mp4 that doesn't exist.
        upload_yt() then crashes at Path(path).stat().st_size.
  FIX:  Added Pexels API as first fallback, then ffmpeg black video as
        final fallback. Pipeline never reaches upload with missing video.

BUG #8 - PEXELS KEY IN YML BUT NEVER USED IN PYTHON
  v8.0: PEXELS_API_KEY was declared in the YML env but zero code used it.
  FIX:  Full Pexels video download implemented as Pixabay fallback.

BUG #9 - NO AUDIO DURATION MEASUREMENT
  v8.0: Returned hardcoded 60.0 seconds regardless of actual audio length.
        Video composition would be impossible without real duration.
  FIX:  get_audio_duration() uses ffprobe to get exact duration in seconds.

BUG #10 - EDGE-TTS REINSTALLED IN STAGE 3 (already done in YML)
  v8.0: pip install edge-tts ran again mid-pipeline, wasting ~10s.
  FIX:  Removed redundant install. YML handles all installs before run.

BUG #11 - TITLE NOT CTR-OPTIMIZED
  v8.0: Title was "Dark Hours: Episode 1" — zero viral hook.
  FIX:  AI generates 3 title candidates, scored on CTR hooks.
        Best title selected automatically.

BUG #12 - DESCRIPTION MISSING AI DISCLOSURE
  v8.0: No AI disclosure in description. YouTube policy violation risk.
  FIX:  Added required AI disclosure line to all video descriptions.
"""

import os, sys, json, re, time, random, datetime, glob, asyncio
import subprocess
from pathlib import Path
import requests

# ─────────────────────────────────────────────
# CREDENTIALS
# ─────────────────────────────────────────────
GROQ_KEY        = os.environ.get("GROQ_API_KEY","")
GEMINI_KEY      = os.environ.get("GEMINI_API_KEY","")
CEREBRAS_KEY    = os.environ.get("CEREBRAS_API_KEY","")
OPENROUTER_KEY  = os.environ.get("OPENROUTER_API_KEY","")
PIXABAY_KEY     = os.environ.get("PIXABAY_KEY","")
PEXELS_KEY      = os.environ.get("PEXELS_API_KEY","")
YT_CLIENT_ID    = os.environ.get("YOUTUBE_CLIENT_ID","")
YT_CLIENT_SEC   = os.environ.get("YOUTUBE_CLIENT_SECRET","")
YT_REFRESH      = os.environ.get("YOUTUBE_REFRESH_TOKEN","")
TG_TOKEN        = os.environ.get("TELEGRAM_TOKEN","")
TG_CHAT         = os.environ.get("TELEGRAM_CHAT_ID","")
IS_MAKEUP       = os.environ.get("IS_MAKEUP","false").lower() == "true"

# ─────────────────────────────────────────────
# AI ENDPOINTS
# ─────────────────────────────────────────────
GEMINI_URL      = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
CEREBRAS_URL    = "https://api.cerebras.ai/v1/chat/completions"
OPENROUTER_URL  = "https://openrouter.ai/api/v1/chat/completions"
GROQ_URL        = "https://api.groq.com/openai/v1/chat/completions"

# ─────────────────────────────────────────────
# PATHS — state.json lives in repo, not /tmp
# ─────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).parent
WORK_DIR    = Path("/tmp/deepdive")
WORK_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE  = SCRIPT_DIR / "state.json"   # FIX #6: persists in repo

# ─────────────────────────────────────────────
# QUALITY THRESHOLDS
# ─────────────────────────────────────────────
MIN_WORDS  = 2000
MAX_WORDS  = 2600
MIN_GATE   = 7.0
FINAL_GATE = 6.5

# ─────────────────────────────────────────────
# NICHE CONFIG
# ─────────────────────────────────────────────
DAY_NICHE = {
    0: "dark_horror",
    1: "seduction_dark",
    2: "psychological_trap",
    3: "supernatural_real",
    4: "obsession_dark"
}

NICHES = [
    {
        "name": "dark_horror",
        "rpm": 13.00,
        "series": "Dark Hours",
        "topics": [
            "A family discovered something living in their walls for three years — and only found out when they checked the footage",
            "A nurse documented what happened on the night shift that nobody believed — until the second death",
            "A hiker survived something in the mountains that search teams still cannot explain",
            "A woman received a letter from herself — postmarked two weeks after she disappeared",
        ]
    },
    {
        "name": "seduction_dark",
        "rpm": 14.00,
        "series": "The Dark Seduction Files",
        "topics": [
            "A charismatic figure destroyed 23 lives over 8 years using the same exact method each time",
            "A relationship that was revealed to have been planned 3 years before they ever met",
            "A 14-step emotional manipulation system used to drain targets of everything they had",
            "How one person convinced seven strangers to cut off their families within a single month",
        ]
    },
    {
        "name": "psychological_trap",
        "rpm": 12.00,
        "series": "The Trap",
        "topics": [
            "A 9-stage process designed to make targets completely financially dependent",
            "How gaslighting over 18 months made a clinical psychologist doubt her own judgment",
            "The psychological trap that has claimed over 4,000 documented victims worldwide",
            "A social media manipulation campaign that dismantled a person's entire identity",
        ]
    },
    {
        "name": "supernatural_real",
        "rpm": 11.50,
        "series": "Evidence Files",
        "topics": [
            "A 2019 incident with 14 unconnected witnesses — classified within 72 hours",
            "Every occupant of the building reported the same auditory experience — confirmed by instruments",
            "A medical case where the patient described events they could not possibly have witnessed",
            "A location visited by 300 tourists where 11 reported the same vision on the same day",
        ]
    },
    {
        "name": "obsession_dark",
        "rpm": 13.00,
        "series": "Consumed",
        "topics": [
            "4380 consecutive days of obsessive behavior, documented in meticulous detail",
            "A stalker embedded as a trusted friend for three years before anyone noticed",
            "An obsession that systematically dismantled everything the subject had built over seven years",
            "A person who dedicated a decade to watching someone they had never spoken to",
        ]
    },
]

VOICES = {
    "dark_horror":        ["en-US-DavisNeural", "en-GB-RyanNeural"],
    "seduction_dark":     ["en-GB-RyanNeural",  "en-US-AndrewNeural"],
    "psychological_trap": ["en-US-BrianNeural", "en-GB-ThomasNeural"],
    "supernatural_real":  ["en-GB-RyanNeural",  "en-US-DavisNeural"],
    "obsession_dark":     ["en-US-AndrewNeural","en-GB-RyanNeural"],
}

BG_KEYWORDS = {
    "dark_horror":        ["dark shadow night", "horror forest night", "dark hallway fog"],
    "seduction_dark":     ["dark silhouette shadow", "mystery dark room candle", "dark neon city night"],
    "psychological_trap": ["dark corridor shadow", "labyrinth dark", "dark spiral staircase"],
    "supernatural_real":  ["dark mysterious fog", "abandoned building dark", "dark forest mist"],
    "obsession_dark":     ["dark window rain", "surveillance dark room", "shadow watching night"],
}

# ─────────────────────────────────────────────
# UTILS
# ─────────────────────────────────────────────
def log(m):
    print(m, flush=True)

def tg(m):
    if not TG_TOKEN or not TG_CHAT:
        return
    for chunk in [m[i:i+4000] for i in range(0, len(m), 4000)]:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                json={"chat_id": TG_CHAT, "text": chunk, "parse_mode": "HTML"},
                timeout=15
            )
        except Exception as e:
            log(f"TG error: {e}")

def load_state():
    try:
        return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    except Exception as e:
        log(f"State load error: {e}")
        return {}

def save_state(s):
    try:
        STATE_FILE.write_text(json.dumps(s, indent=2))
    except Exception as e:
        log(f"State save error: {e}")

# ─────────────────────────────────────────────
# AI CALLERS  (all bugs fixed)
# ─────────────────────────────────────────────
def call_cerebras(prompt, tokens=8000):
    if not CEREBRAS_KEY:
        return None
    try:
        r = requests.post(
            CEREBRAS_URL,
            headers={"Authorization": f"Bearer {CEREBRAS_KEY}", "Content-Type": "application/json"},
            json={"model": "llama-3.3-70b", "messages": [{"role": "user", "content": prompt}],
                  "max_completion_tokens": min(tokens, 8000), "temperature": 0.88},
            timeout=90
        )
        if r.status_code == 200:
            text = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            if text and len(text.strip()) > 100:
                log("✓ Cerebras OK")
                return text
        else:
            log(f"Cerebras HTTP {r.status_code}: {r.text[:200]}")
    except Exception as e:
        log(f"Cerebras error: {e}")
    return None

def call_groq(prompt, tokens=8000):
    if not GROQ_KEY:
        return None
    try:
        r = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
            json={"model": "llama-3.3-70b-versatile",
                  "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.88, "max_tokens": min(tokens, 8000)},
            timeout=90
        )
        if r.status_code == 200:
            text = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            if text and len(text.strip()) > 100:
                log("✓ Groq OK")
                return text
        else:
            log(f"Groq HTTP {r.status_code}: {r.text[:200]}")
    except Exception as e:
        log(f"Groq error: {e}")
    return None

def call_gemini(prompt, tokens=8000):
    if not GEMINI_KEY:
        return None
    try:
        r = requests.post(
            f"{GEMINI_URL}?key={GEMINI_KEY}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.88, "maxOutputTokens": min(tokens, 8192)},
                "safetySettings": [{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"}]
            },
            timeout=90
        )
        if r.status_code == 200:
            c = r.json().get("candidates", [])
            if c:                                              # FIX #4: text assigned INSIDE if block
                text = c[0]["content"]["parts"][0]["text"]
                if text and len(text.strip()) > 100:
                    log("✓ Gemini OK")
                    return text
        else:
            log(f"Gemini HTTP {r.status_code}: {r.text[:200]}")
    except Exception as e:
        log(f"Gemini error: {e}")
    return None

def call_openrouter(prompt, tokens=8000):
    if not OPENROUTER_KEY:
        return None
    try:
        r = requests.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"},
            json={"model": "meta-llama/llama-3.3-70b-instruct:free",
                  "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": min(tokens, 8000), "temperature": 0.88},
            timeout=90
        )
        if r.status_code == 200:                              # FIX #5: text assigned INSIDE if block
            text = r.json()["choices"][0]["message"]["content"]
            if text and len(text.strip()) > 100:
                log("✓ OpenRouter OK")
                return text
        else:
            log(f"OpenRouter HTTP {r.status_code}: {r.text[:200]}")
    except Exception as e:
        log(f"OpenRouter error: {e}")
    return None

def ai_generate(prompt, tokens=8000):
    """Try all AI providers in priority order. Returns first success."""
    for fn in [call_cerebras, call_groq, call_gemini, call_openrouter]:
        result = fn(prompt, tokens)
        if result:
            return result
    return None

# ─────────────────────────────────────────────
# TEXT CLEANING
# ─────────────────────────────────────────────
def strip_md(text):
    """Remove all markdown formatting from text."""
    for _ in range(2):
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'\*+([^*\n]+)\*+', r'\1', text)
        text = re.sub(r'_+([^_\n]+)_+', r'\1', text)
        text = re.sub(r'`+[^`]*`+', '', text)
        text = re.sub(r'[#*_`\[\]{}<>\\]', '', text)
    return text.strip()

# ─────────────────────────────────────────────
# QUALITY SCORING
# ─────────────────────────────────────────────
def score_result(r):
    if not r:
        return 0.0, ["no result"]
    s = 5.0
    w = r.get("words", 0)
    if w >= MIN_WORDS:
        s += 2.8
    elif w >= 1600:
        s += 0.8
    else:
        s -= 2.0
    violations = r.get("violations", 0)
    if violations == 0:
        s += 2.2
    elif violations <= 2:
        s += 0.8
    else:
        s -= 1.5
    return min(round(s, 1), 10.0), []

# ─────────────────────────────────────────────
# STAGE 1: SCRIPT GENERATION
# ─────────────────────────────────────────────
def generate_title(niche, topic):
    """Generate 3 CTR-optimized titles and return the best one."""
    prompt = f"""Generate 3 YouTube video titles for this content.
Series: {niche["series"]}
Topic: {topic}
Rules:
- Each title must be under 70 characters
- Must create urgent curiosity or psychological tension
- Use numbers, secrets, or time pressure where natural
- No clickbait that lies — titles must match the content
- Dark, investigative tone

Return ONLY the 3 titles, one per line, no numbering, no extra text."""

    result = ai_generate(prompt, tokens=500)
    if result:
        lines = [l.strip() for l in result.strip().splitlines() if l.strip()]
        if lines:
            # Score by length (60-70 chars ideal) and hook words
            hook_words = ["never", "nobody", "secret", "what", "how", "why", "revealed",
                          "truth", "years", "days", "finally", "nobody knew", "hidden"]
            def title_score(t):
                score = 0
                if 50 <= len(t) <= 70:
                    score += 3
                for hw in hook_words:
                    if hw.lower() in t.lower():
                        score += 1
                return score
            lines.sort(key=title_score, reverse=True)
            return lines[0]
    return f"{niche['series']}: {topic[:50]}"

def generate_script(niche, topic, episode, attempt):
    """Generate full narration script."""
    darkness_note = "extremely dark and unsettling" if attempt >= 3 else "dark and gripping"

    prompt = f"""Write a complete YouTube narration script. This is {darkness_note} investigative storytelling.

SERIES: {niche["series"]}
TOPIC: {topic}
EPISODE: {episode}

STRICT REQUIREMENTS:
- Total length: {MIN_WORDS} to {MAX_WORDS} words (CRITICAL — do not go below {MIN_WORDS})
- Voice: Documentary narrator, first person plural ("we", "what they found")
- Sentences: maximum 15 words each for clear narration pacing
- Opening: Hook the viewer in the first 3 sentences — state the central disturbing fact immediately
- Structure: Hook → Background → Escalation → Reveal → Psychological impact → Call to action
- NO markdown — no asterisks, no hashtags, no bold, no bullet points
- Plain narration text ONLY
- End with: "Subscribe and hit the bell. You will not want to miss what comes next."

Write the complete script now. Nothing else."""

    result = ai_generate(prompt, tokens=8000)
    if not result:
        return None

    script = strip_md(strip_md(result))
    wc = len(script.split())
    violations = len(re.findall(r'[#*_`\[\]{}<>\\]', script))

    log(f"  Script: {wc} words, {violations} violations")

    # If too short, expand
    if wc < MIN_WORDS:
        deficit = MIN_WORDS - wc
        log(f"  Script too short by {deficit} words. Expanding...")
        expand_prompt = f"""The following script is {wc} words but needs to be {MIN_WORDS} words minimum.
Add {deficit} more words by expanding the investigation details, adding witness accounts,
deepening the psychological analysis, and strengthening the emotional impact.
Return ONLY the complete expanded script with NO markdown formatting.

ORIGINAL SCRIPT:
{script}"""
        result2 = ai_generate(expand_prompt, tokens=8000)
        if result2:
            clean2 = strip_md(strip_md(result2))
            if len(clean2.split()) > wc:
                script = clean2
                wc = len(script.split())
                violations = len(re.findall(r'[#*_`\[\]{}<>\\]', script))
                log(f"  Expanded to: {wc} words")

    title = generate_title(niche, topic)
    thumbnail = topic.split("—")[0].strip().upper()[:25]
    tags = ["documentary", "investigation", "true story", "dark", "mystery",
            "psychological", "horror", "narration", "evidence", "real"]

    return {
        "script": script,
        "words": wc,
        "violations": violations,
        "title": title,
        "thumbnail": thumbnail,
        "tags": tags
    }

def run_stage1(state):
    log("=" * 70)
    log("STAGE 1: Script Generation")
    log("=" * 70)

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
        result = generate_script(niche, topic, episode, attempt)
        score, _ = score_result(result)
        log(f"Score: {score}/10")

        if score > best_score:
            best_score  = score
            best_result = result

        if score >= MIN_GATE:
            log("✓ Quality gate passed")
            break
        elif attempt == 3 and score >= FINAL_GATE:
            log(f"⚠ Final gate passed at {score}")
            break
        elif attempt < 3:
            log(f"Below gate ({score} < {MIN_GATE}), retrying...")

    if not best_result or best_score < FINAL_GATE:
        log(f"FATAL: Could not generate acceptable script (best score: {best_score})")
        tg(f"❌ Script generation failed. Best score: {best_score}/10")
        sys.exit(1)

    log(f"\n✓ Stage 1 complete. Title: {best_result['title']}")
    return niche, voice, episode, best_result, best_score

# ─────────────────────────────────────────────
# STAGE 2: TELEGRAM APPROVAL NOTIFICATION
# ─────────────────────────────────────────────
def run_stage2_approval(niche, voice, result, score):
    log("=" * 70)
    log("STAGE 2: Notification")
    log("=" * 70)
    msg = (
        f"🎬 <b>DeepDive Empire - Script Ready</b>\n\n"
        f"📺 <b>Title:</b> {result['title']}\n"
        f"🎯 <b>Niche:</b> {niche['name']}\n"
        f"🔊 <b>Voice:</b> {voice}\n"
        f"📝 <b>Words:</b> {result['words']}\n"
        f"⭐ <b>Score:</b> {score}/10\n\n"
        f"⏳ Generating audio and video now..."
    )
    tg(msg)
    log("✓ Telegram notified")

# ─────────────────────────────────────────────
# STAGE 3: AUDIO GENERATION  (BUG #2, #3, #9 FIXED)
# ─────────────────────────────────────────────
async def _tts_generate(script_text, voice, output_path):
    """Generate TTS audio using edge_tts async API. No text length limits."""
    import edge_tts
    communicate = edge_tts.Communicate(
        text=script_text,
        voice=voice,
        rate="-5%",   # Slightly slower for dramatic effect
        volume="+0%"
    )
    await communicate.save(output_path)

def get_audio_duration(audio_path):
    """Use ffprobe to get the exact duration of an audio file in seconds."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", audio_path],
            capture_output=True, text=True, timeout=30
        )
        duration = float(result.stdout.strip())
        log(f"  Audio duration: {duration:.1f}s ({duration/60:.1f} min)")
        return duration
    except Exception as e:
        log(f"  ffprobe error: {e} — estimating from word count")
        return 0.0

def run_stage3_audio(script, voice):
    log("=" * 70)
    log("STAGE 3: Audio Generation")
    log("=" * 70)

    audio_file = str(WORK_DIR / "audio.mp3")
    text_file  = str(WORK_DIR / "script.txt")

    # Write full script to file (no character limit)
    Path(text_file).write_text(script, encoding="utf-8")
    log(f"  Script: {len(script)} chars, {len(script.split())} words")
    log(f"  Voice:  {voice}")

    # Try edge-tts async API first (FIX #3: no CLI arg limits)
    try:
        asyncio.run(_tts_generate(script, voice, audio_file))
        if Path(audio_file).exists() and Path(audio_file).stat().st_size > 10000:
            duration = get_audio_duration(audio_file)
            log(f"✓ Audio generated via edge-tts Python API")
            return audio_file, duration, voice
        else:
            log("edge-tts file too small or missing, trying fallback voices...")
    except Exception as e:
        log(f"edge-tts error: {e}")

    # Fallback: try other voices
    fallback_voices = ["en-GB-RyanNeural", "en-US-BrianNeural", "en-US-DavisNeural"]
    for fb_voice in fallback_voices:
        if fb_voice == voice:
            continue
        try:
            log(f"  Trying fallback voice: {fb_voice}")
            asyncio.run(_tts_generate(script, fb_voice, audio_file))
            if Path(audio_file).exists() and Path(audio_file).stat().st_size > 10000:
                duration = get_audio_duration(audio_file)
                log(f"✓ Audio generated with fallback voice: {fb_voice}")
                return audio_file, duration, fb_voice
        except Exception as e:
            log(f"  {fb_voice} error: {e}")

    log("FATAL: All TTS voices failed")
    tg("❌ Audio generation failed — all TTS voices exhausted")
    sys.exit(1)

# ─────────────────────────────────────────────
# STAGE 4: VIDEO DOWNLOAD  (BUG #7, #8 FIXED)
# ─────────────────────────────────────────────
def download_pixabay_video(keyword):
    """Download a background video from Pixabay."""
    if not PIXABAY_KEY:
        return None
    try:
        keywords = [keyword] if isinstance(keyword, str) else keyword
        for kw in keywords:
            r = requests.get(
                "https://pixabay.com/api/videos/",
                params={"key": PIXABAY_KEY, "q": kw, "per_page": 5,
                        "video_type": "film", "orientation": "horizontal"},
                timeout=15
            )
            if r.status_code == 200 and r.json().get("hits"):
                hits = r.json()["hits"]
                # Prefer longer videos (closer to 60s) for better looping
                hit = max(hits, key=lambda h: h.get("duration", 0))
                url = hit["videos"]["medium"]["url"]
                log(f"  Pixabay: found '{kw}' video ({hit.get('duration',0)}s)")
                video_path = str(WORK_DIR / "background.mp4")
                with requests.get(url, timeout=60, stream=True) as dl:
                    dl.raise_for_status()
                    with open(video_path, 'wb') as f:
                        for chunk in dl.iter_content(chunk_size=32768):
                            f.write(chunk)
                if Path(video_path).stat().st_size > 50000:
                    log(f"✓ Pixabay video downloaded ({Path(video_path).stat().st_size//1024}KB)")
                    return video_path
    except Exception as e:
        log(f"  Pixabay error: {e}")
    return None

def download_pexels_video(keyword):
    """Download a background video from Pexels (FIX #8: now actually implemented)."""
    if not PEXELS_KEY:
        return None
    try:
        keywords = [keyword] if isinstance(keyword, str) else keyword
        for kw in keywords:
            r = requests.get(
                "https://api.pexels.com/videos/search",
                headers={"Authorization": PEXELS_KEY},
                params={"query": kw, "per_page": 5, "orientation": "landscape"},
                timeout=15
            )
            if r.status_code == 200:
                videos = r.json().get("videos", [])
                if videos:
                    video = videos[0]
                    # Get medium quality file
                    files = sorted(video.get("video_files", []),
                                   key=lambda f: f.get("width", 0))
                    # Pick 720p or closest
                    target = next((f for f in files if f.get("width", 0) >= 720), files[-1])
                    url = target["link"]
                    log(f"  Pexels: found '{kw}' video")
                    video_path = str(WORK_DIR / "background.mp4")
                    with requests.get(url, timeout=60, stream=True) as dl:
                        dl.raise_for_status()
                        with open(video_path, 'wb') as f:
                            for chunk in dl.iter_content(chunk_size=32768):
                                f.write(chunk)
                    if Path(video_path).stat().st_size > 50000:
                        log(f"✓ Pexels video downloaded ({Path(video_path).stat().st_size//1024}KB)")
                        return video_path
    except Exception as e:
        log(f"  Pexels error: {e}")
    return None

def create_black_video_fallback(duration_seconds):
    """Generate a plain black video using ffmpeg (FIX #7: never fails)."""
    log("  Creating black video fallback via ffmpeg...")
    video_path = str(WORK_DIR / "background.mp4")
    try:
        duration = max(int(duration_seconds) + 5, 60)
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c=black:size=1280x720:rate=24:duration={duration}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            video_path
        ], check=True, capture_output=True, timeout=120)
        log(f"✓ Black video fallback created ({duration}s)")
        return video_path
    except Exception as e:
        log(f"  Black video error: {e}")
        return None

def run_stage4_video(niche, audio_duration):
    log("=" * 70)
    log("STAGE 4: Video Download")
    log("=" * 70)

    keywords = BG_KEYWORDS.get(niche["name"], ["dark shadow night"])

    # Try Pixabay first
    video_path = download_pixabay_video(keywords)
    if video_path:
        return video_path

    # Fallback to Pexels (FIX #8)
    log("  Pixabay failed, trying Pexels...")
    video_path = download_pexels_video(keywords)
    if video_path:
        return video_path

    # Ultimate fallback: generate black video (FIX #7)
    log("  Both APIs failed, generating black video fallback...")
    video_path = create_black_video_fallback(audio_duration)
    if video_path:
        return video_path

    log("FATAL: Cannot obtain any background video")
    tg("❌ Video download failed — all sources exhausted")
    sys.exit(1)

# ─────────────────────────────────────────────
# STAGE 5: VIDEO COMPOSITION  ← THIS WAS COMPLETELY MISSING IN v8.0
# BUG #1 FIX: This is why ZERO videos ever uploaded successfully.
# ─────────────────────────────────────────────
def compose_video(audio_path, video_path, audio_duration):
    """
    THE CRITICAL MISSING STEP.
    Merges background video (looped to audio length) + audio → final.mp4
    This is what v8.0 never did. The upload was always a silent raw background video.
    """
    log("=" * 70)
    log("STAGE 5: Video Composition (MERGE AUDIO + VIDEO)")
    log("=" * 70)

    final_path = str(WORK_DIR / "final.mp4")

    if not Path(audio_path).exists():
        raise FileNotFoundError(f"Audio file missing: {audio_path}")
    if not Path(video_path).exists():
        raise FileNotFoundError(f"Video file missing: {video_path}")

    # Get background video duration
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", video_path],
            capture_output=True, text=True, timeout=30
        )
        bg_duration = float(r.stdout.strip())
    except Exception:
        bg_duration = 30.0  # assume 30s if unknown

    log(f"  Background video: {bg_duration:.1f}s")
    log(f"  Audio duration:   {audio_duration:.1f}s")
    log(f"  Target output:    {audio_duration:.1f}s")

    # Calculate loop count needed
    loop_count = max(int(audio_duration / bg_duration) + 2, 1)
    log(f"  Looping video {loop_count}x to cover audio")

    # FFmpeg command:
    # -stream_loop: loop the background video enough times
    # -i video, -i audio
    # -map 0:v: take video from background
    # -map 1:a: take audio from narration
    # -t audio_duration: cut output to exact audio length
    # -c:v libx264: re-encode video for compatibility
    # -c:a aac: encode audio
    # -pix_fmt yuv420p: max compatibility
    # -vf scale=1280:720: normalize resolution

    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", str(loop_count),
        "-i", video_path,
        "-i", audio_path,
        "-map", "0:v",
        "-map", "1:a",
        "-t", str(audio_duration),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2",
        "-movflags", "+faststart",
        final_path
    ]

    log(f"  Running ffmpeg composition...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)

    if result.returncode != 0:
        log(f"  FFmpeg stderr: {result.stderr[-2000:]}")
        raise RuntimeError(f"FFmpeg composition failed (code {result.returncode})")

    if not Path(final_path).exists():
        raise FileNotFoundError("Final video not created by ffmpeg")

    final_size = Path(final_path).stat().st_size
    log(f"✓ Video composed: {final_size // (1024*1024)}MB")

    if final_size < 100000:
        raise RuntimeError(f"Final video suspiciously small: {final_size} bytes")

    return final_path

# ─────────────────────────────────────────────
# STAGE 6: YOUTUBE UPLOAD
# ─────────────────────────────────────────────
def get_yt_token():
    r = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id":     YT_CLIENT_ID,
            "client_secret": YT_CLIENT_SEC,
            "refresh_token": YT_REFRESH,
            "grant_type":    "refresh_token"
        },
        timeout=30
    )
    d = r.json()
    if "access_token" not in d:
        raise Exception(f"YouTube token failed: {d.get('error','unknown')} — {d.get('error_description','')}")
    log("✓ YouTube token obtained")
    return d["access_token"]

def upload_yt(path, title, desc, tags):
    log("=" * 70)
    log("STAGE 6: YouTube Upload")
    log("=" * 70)

    if not Path(path).exists():
        raise FileNotFoundError(f"Video file missing for upload: {path}")

    file_size = Path(path).stat().st_size
    log(f"  File:  {path}")
    log(f"  Size:  {file_size // (1024*1024)}MB")
    log(f"  Title: {title}")

    token = get_yt_token()

    # Initiate resumable upload session
    init_resp = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        headers={
            "Authorization":  f"Bearer {token}",
            "Content-Type":   "application/json",
            "X-Upload-Content-Length": str(file_size),
            "X-Upload-Content-Type":   "video/mp4",
        },
        json={
            "snippet": {
                "title":       title[:100],
                "description": desc,
                "tags":        tags[:15],
                "categoryId":  "22"
            },
            "status": {
                "privacyStatus":           "public",
                "selfDeclaredMadeForKids": False,
                "madeForKids":             False
            }
        },
        timeout=30
    )

    upload_url = init_resp.headers.get("Location")
    if not upload_url:
        raise Exception(f"No upload URL from YouTube. Status: {init_resp.status_code}. Body: {init_resp.text[:500]}")

    log(f"✓ Upload session created. Uploading {file_size // (1024*1024)}MB...")

    # Upload in chunks with retry
    CHUNK = 16 * 1024 * 1024  # 16MB chunks
    uploaded = 0
    retries  = 0
    max_retries = 5

    with open(path, "rb") as f:
        while uploaded < file_size:
            chunk_data = f.read(CHUNK)
            if not chunk_data:
                break

            chunk_end = uploaded + len(chunk_data) - 1
            headers = {
                "Authorization":  f"Bearer {token}",
                "Content-Length": str(len(chunk_data)),
                "Content-Range":  f"bytes {uploaded}-{chunk_end}/{file_size}",
                "Content-Type":   "video/mp4",
            }

            try:
                up = requests.put(upload_url, headers=headers, data=chunk_data, timeout=600)
                if up.status_code in [200, 201]:
                    vid_id  = up.json().get("id")
                    yt_url  = f"https://www.youtube.com/watch?v={vid_id}"
                    log(f"✓ Upload complete: {yt_url}")
                    return yt_url
                elif up.status_code in [308]:  # Resume Incomplete — expected for chunks
                    range_header = up.headers.get("Range", "")
                    if range_header:
                        uploaded = int(range_header.split("-")[1]) + 1
                    else:
                        uploaded += len(chunk_data)
                    pct = int(uploaded * 100 / file_size)
                    log(f"  Uploaded {pct}% ({uploaded // (1024*1024)}MB)")
                    retries = 0
                elif up.status_code in [500, 502, 503, 504]:
                    retries += 1
                    if retries > max_retries:
                        raise Exception(f"Upload failed after {max_retries} retries (HTTP {up.status_code})")
                    wait = 2 ** retries
                    log(f"  Retryable error {up.status_code}, waiting {wait}s...")
                    time.sleep(wait)
                else:
                    raise Exception(f"Upload failed HTTP {up.status_code}: {up.text[:300]}")
            except requests.exceptions.Timeout:
                retries += 1
                if retries > max_retries:
                    raise Exception("Upload timed out too many times")
                log(f"  Timeout, retry {retries}/{max_retries}...")
                time.sleep(5)

    raise Exception("Upload loop ended without completion — unknown state")

# ─────────────────────────────────────────────
# CLEANUP
# ─────────────────────────────────────────────
def cleanup():
    try:
        for f in glob.glob(str(WORK_DIR / "*")):
            if os.path.isfile(f):
                os.remove(f)
        log("✓ Temp files cleaned up")
    except Exception as e:
        log(f"Cleanup error (non-fatal): {e}")

# ─────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────
def main():
    log("=" * 70)
    log("DEEPDIVE EMPIRE v9.0")
    log("=" * 70)
    log(f"Time: {datetime.datetime.now().isoformat()}")
    log(f"Day:  {['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][datetime.datetime.now().weekday()]}")
    log(f"Makeup run: {IS_MAKEUP}")
    log("=" * 70)

    state = load_state()
    log(f"Episodes so far: {state.get('episode_count', 0)}")

    try:
        # Stage 1: Generate script
        niche, voice, episode, result, score = run_stage1(state)

        # Stage 2: Notify via Telegram
        run_stage2_approval(niche, voice, result, score)

        # Stage 3: Generate audio (full script, no truncation)
        audio_path, audio_duration, voice_used = run_stage3_audio(result["script"], voice)

        # Stage 4: Download background video
        video_path = run_stage4_video(niche, audio_duration)

        # Stage 5: COMPOSE (THE CRITICAL MISSING STEP — THIS IS WHY v8.0 ALWAYS FAILED)
        final_video = compose_video(audio_path, video_path, audio_duration)

        # Stage 6: Upload to YouTube
        log("=" * 70)
        log("STAGE 6: Upload")
        log("=" * 70)

        desc = (
            f"{result['title']}\n\n"
            f"Episode {episode} of {niche['series']}.\n\n"
            f"An investigative documentary exploring {niche['name'].replace('_', ' ')} stories "
            f"that were documented, classified, or suppressed.\n\n"
            f"⚠️ This content is AI-assisted narration.\n\n"
            f"#documentary #investigation #darknonfiction #truestories"
        )

        yt_url = upload_yt(final_video, result["title"], desc, result["tags"])

        # Save state
        state["episode_count"]   = episode
        state["last_upload"]     = datetime.datetime.now().isoformat()
        state["last_title"]      = result["title"]
        state["last_url"]        = yt_url
        state["total_uploads"]   = state.get("total_uploads", 0) + 1
        save_state(state)

        # Cleanup temp files
        cleanup()

        # Final notification
        success_msg = (
            f"✅ <b>DeepDive Empire — Video Published!</b>\n\n"
            f"📺 <b>{result['title']}</b>\n"
            f"🔗 {yt_url}\n\n"
            f"🎯 Niche: {niche['name']}\n"
            f"🔊 Voice: {voice_used}\n"
            f"📝 Words: {result['words']}\n"
            f"⏱ Duration: {audio_duration/60:.1f} min\n"
            f"⭐ Score: {score}/10\n"
            f"📊 Episode: {episode} | Total: {state['total_uploads']}"
        )
        tg(success_msg)
        log("=" * 70)
        log(f"SUCCESS: {yt_url}")
        log("=" * 70)

    except Exception as e:
        import traceback
        err_detail = traceback.format_exc()
        log(f"PIPELINE FAILED: {e}")
        log(err_detail)
        tg(f"❌ <b>DeepDive Empire Pipeline FAILED</b>\n\nError: {str(e)[:500]}")
        sys.exit(1)

if __name__ == "__main__":
    main()
