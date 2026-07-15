"""
reel_generator.py
==================
Creates Reels for Instagram (India) and Shorts for YouTube (US/UK).

For each piece of content:
1. Generates script in English + Hindi caption
2. Groq Orpheus TTS for audio
3. FFmpeg assembles 9:16 vertical video
4. Adds watermark/branding
5. Adds animated text overlay (hook line)
6. Saves metadata for upload scripts

Produces 2 Reels + 2 Shorts per day = 4 videos total.
"""

import os, json, re, subprocess, requests, random, logging, uuid
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [REEL] %(message)s")
log = logging.getLogger(__name__)

GROQ_KEY   = os.environ.get("GROQ_API_KEY", "")
PIXABAY_KEY = os.environ.get("PIXABAY_KEY", "")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/tmp/empire_output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

GROQ_MODEL = "llama-3.3-70b-versatile"
CHANNEL_NAME = "BETRAYAL DEEPDIVE"
WATERMARK_TEXT = "@betrayaldeepdive"

# Voice profiles for Reels (shorter, punchier than long-form)
REEL_VOICES = [
    {"id": "troy",   "tag": "[intense]",    "style": "dramatic"},
    {"id": "autumn", "tag": "[empathetic]", "style": "emotional"},
    {"id": "austin", "tag": "[disbelief]",  "style": "shocking"},
    {"id": "hannah", "tag": "[shocked]",    "style": "shocking"},
    {"id": "diana",  "tag": "[calm]",       "style": "investigative"},
]

# Scene keywords for Pixabay clips (9:16 vertical)
REEL_SCENES = {
    "shocking_reveal":      ["dramatic reveal dark room","secret exposed shocked"],
    "emotional_story":      ["person crying alone sad","emotional broken heart"],
    "psychological_twist":  ["mind games manipulation dark","psychology thriller"],
    "justice_served":       ["justice courtroom victory","karma justice served"],
    "default":              ["dramatic dark cinematic","mystery suspense dark"],
}


def groq_text(prompt: str, max_tokens: int = 1000) -> str:
    """
    FIX: this used to call a single hardcoded model
    ("llama-3.3-70b-versatile") with no fallback. That model was
    announced deprecated by Groq on June 17, 2026 — every Reel/Short
    script would fail outright once Groq fully retires it. Now tries a
    real chain of genuinely current models.
    """
    models = ["openai/gpt-oss-120b", "qwen/qwen3-32b", "llama-3.3-70b-versatile"]
    last_err = None
    for model in models:
        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
                json={"model": model, "messages": [{"role": "user", "content": prompt}],
                      "max_tokens": max_tokens, "temperature": 0.8},
                timeout=45
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            last_err = e
            log.warning("Groq model %s failed (%s) — trying next", model, e)
    raise last_err if last_err else RuntimeError("All Groq models failed")


def generate_reel_content(topic: str, target: str, fmt: str, hook: str) -> dict:
    """
    Generates complete Reel content: script, captions, hashtags.
    target: india_hindi | india_english | global_english
    """
    is_hindi = "hindi" in target

    lang_instruction = ""
    if is_hindi:
        lang_instruction = """
LANGUAGE: Write the narration in SIMPLE HINDI mixed with English (Hinglish).
Example style: "Aaj main aapko ek aisi kahani sunane wala hun jo aapko hilaa degi..."
Caption must be in Hindi with English hashtags."""
    else:
        lang_instruction = """
LANGUAGE: Write in English. Target Indian audience who prefer English content.
Use relatable Indian context and references."""

    prompt = f"""You are a viral short-form video script writer for Instagram Reels and YouTube Shorts.

TOPIC: {topic}
FORMAT: {fmt}
HOOK (first words on screen): {hook}
{lang_instruction}

Write a 45-55 second Reel narration script.

RULES FOR MAXIMUM VIRALITY:
- First sentence = the most shocking statement. No build-up. Start with the climax.
- Every sentence must make the viewer UNABLE to stop watching
- Use these phrases: "But that's not the worst part...", "Nobody knew that...", "What happened next will shock you..."
- End with a question that demands a comment: "What would YOU have done?"
- 130-150 words ONLY (45-55 seconds at normal pace)
- NO intro, NO "hello", NO "welcome" — start DIRECTLY with the story

Also generate:
- YouTube Short title (US/UK keywords, max 60 chars, starts with power word)
- Instagram caption (2-3 sentences + question + 20 hashtags for India)
- Instagram Hindi caption (if hindi target, else same as above)
- Pinterest pin title + description

Return ONLY valid JSON:
{{
  "script": "full narration text here",
  "yt_short_title": "YouTube title here",
  "ig_caption_english": "English Instagram caption + hashtags",
  "ig_caption_hindi": "Hindi/Hinglish caption + English hashtags",
  "pinterest_title": "Pinterest pin title",
  "pinterest_description": "2-sentence Pinterest description with keywords",
  "hook_overlay_text": "5-7 words shown as text overlay at start",
  "end_cta": "Subscribe karo | Follow for more",
  "virality_score": 85
}}"""

    raw = groq_text(prompt, max_tokens=1200)
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except Exception:
        log.error("Content JSON parse failed — using fallback")
        return {
            "script": topic + " This story will shock you. Nobody knew the truth until it was too late.",
            "yt_short_title": f"SHOCKING: {topic[:45]}",
            "ig_caption_english": f"#{topic.replace(' ','').lower()} #betrayal #truecrime #shocking #reels #india",
            "ig_caption_hindi": f"Yeh kahani aapko hilaa degi! #{topic.replace(' ','').lower()} #betrayal",
            "pinterest_title": topic[:60],
            "pinterest_description": f"The shocking story of {topic}.",
            "hook_overlay_text": "This will shock you...",
            "end_cta": "Follow for more",
            "virality_score": 70,
        }


def generate_audio(script: str, voice: dict, out_path: str) -> bool:
    """
    Generate TTS audio using Groq Orpheus.

    FIX (critical): this used to chunk at 2800 characters — Groq's
    Orpheus TTS has a real, hard 200-character limit PER REQUEST
    (confirmed directly against Groq's own API behavior, same limit
    already fixed elsewhere in this project). Every chunk sent at the
    old size would have been silently truncated or rejected by the API,
    meaning every single Reel/Short's narration was broken. Fixed to
    180 chars (safe margin under the real 200-char limit).
    """
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    full_text = voice["tag"] + " " + script

    # Split into chunks (max 180 chars each — real Groq Orpheus limit is 200)
    words = full_text.split()
    chunks, chunk = [], ""
    for word in words:
        if len(chunk) + len(word) + 1 > 180:
            chunks.append(chunk.strip())
            chunk = word
        else:
            chunk += " " + word
    if chunk.strip():
        chunks.append(chunk.strip())

    parts = []
    for i, c in enumerate(chunks):
        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/audio/speech",
                headers=headers,
                json={"model": "canopylabs/orpheus-v1-english",
                      "input": c, "voice": voice["id"], "response_format": "wav"},
                timeout=90
            )
            if r.status_code == 200 and len(r.content) > 500:
                p = out_path + f".part{i}.wav"
                with open(p, "wb") as f:
                    f.write(r.content)
                # Convert to mp3
                mp3 = p.replace(".wav", ".mp3")
                subprocess.run(["ffmpeg", "-y", "-i", p,
                                "-codec:a", "libmp3lame", "-b:a", "192k", mp3],
                               capture_output=True)
                if os.path.exists(mp3):
                    parts.append(mp3)
                    os.remove(p)
                else:
                    parts.append(p)
        except Exception as e:
            log.warning("TTS chunk %d failed: %s", i, e)

    if not parts:
        return False

    if len(parts) == 1:
        import shutil
        shutil.move(parts[0], out_path)
    else:
        cmd = ["ffmpeg", "-y"]
        for p in parts:
            cmd += ["-i", p]
        cmd += ["-filter_complex", f"concat=n={len(parts)}:v=0:a=1[a]",
                "-map", "[a]", "-codec:a", "libmp3lame", out_path]
        subprocess.run(cmd, capture_output=True)
        for p in parts:
            try: os.remove(p)
            except: pass

    return os.path.exists(out_path) and os.path.getsize(out_path) > 1000


def download_vertical_clip(keyword: str, out_path: str) -> bool:
    """Download a vertical/portrait video clip from Pixabay."""
    try:
        r = requests.get(
            f"https://pixabay.com/api/videos/?key={PIXABAY_KEY}"
            f"&q={requests.utils.quote(keyword)}&per_page=10&video_type=film",
            timeout=20
        )
        hits = r.json().get("hits", [])
        random.shuffle(hits)
        for hit in hits:
            for q in ["large", "medium", "small"]:
                url = hit.get("videos", {}).get(q, {}).get("url")
                if url:
                    vr = requests.get(url, stream=True, timeout=60)
                    with open(out_path, "wb") as f:
                        for chunk in vr.iter_content(8192):
                            f.write(chunk)
                    if os.path.getsize(out_path) > 10000:
                        return True
    except Exception as e:
        log.warning("Clip download failed: %s", e)
    return False


def assemble_reel(audio_path: str, bg_clip: str, hook_text: str,
                  watermark: str, out_path: str) -> bool:
    """
    Assembles the final Reel video:
    - 9:16 vertical (1080x1920)
    - Background video clip (looped to match audio length)
    - Audio narration
    - Hook text overlay (top)
    - Watermark (bottom)
    - Dark cinematic vignette overlay
    """
    # Get audio duration
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", audio_path],
        capture_output=True, text=True
    )
    try:
        duration = float(json.loads(probe.stdout)["format"]["duration"])
    except Exception:
        duration = 55.0

    # Safe text for FFmpeg
    def safe(t): return t.replace("'", "").replace(":", " ").replace("%", "")[:50]

    hook_safe = safe(hook_text)
    wm_safe   = safe(watermark)

    # Build FFmpeg command
    vf = (
        # Scale and crop to 9:16
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        # Dark vignette overlay for cinematic look
        "vignette=PI/4,"
        # Hook text (top, large, bold)
        f"drawtext=text='{hook_safe}':"
        "fontsize=58:fontcolor=white:borderw=3:bordercolor=black:"
        "x=(w-text_w)/2:y=120:line_spacing=10,"
        # Watermark (bottom)
        f"drawtext=text='{wm_safe}':"
        "fontsize=36:fontcolor=white@0.7:borderw=2:bordercolor=black@0.5:"
        "x=(w-text_w)/2:y=h-80"
    )

    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1",      # loop background video
        "-i", bg_clip,
        "-i", audio_path,
        "-t", str(duration + 1),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        "-shortest",
        out_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log.error("FFmpeg error: %s", result.stderr[-300:])
        return False

    log.info("Reel assembled: %s (%.1f MB)",
             out_path, os.path.getsize(out_path) / 1024 / 1024)
    return True


def create_reel(content_plan: dict, reel_num: int) -> dict:
    """
    Full pipeline: plan → script → audio → video → metadata.
    Returns dict with video path and all metadata.
    """
    job_id  = uuid.uuid4().hex[:8]
    work_dir = os.path.join(OUTPUT_DIR, f"reel_{reel_num}_{job_id}")
    os.makedirs(work_dir, exist_ok=True)

    niche_key = f"niche_{reel_num}"
    plan      = content_plan.get(niche_key, content_plan.get("niche_1", {}))

    topic  = plan.get("topic", "A shocking betrayal story")
    target = plan.get("target", "india_english")
    fmt    = plan.get("format", "shocking_reveal")
    hook   = plan.get("hook", "This will shock you...")

    log.info("Creating Reel %d: %s", reel_num, topic[:50])

    # 1. Generate content
    content = generate_reel_content(topic, target, fmt, hook)
    script  = content.get("script", topic)
    log.info("Script: %d chars | Virality: %d",
             len(script), content.get("virality_score", 0))

    # 2. Generate audio
    voice      = random.choice(REEL_VOICES)
    audio_path = os.path.join(work_dir, "audio.mp3")
    audio_ok   = generate_audio(script, voice, audio_path)

    if not audio_ok:
        log.error("Audio generation failed for reel %d", reel_num)
        return {}

    # 3. Download background clip
    scene_kws = REEL_SCENES.get(fmt, REEL_SCENES["default"])
    clip_path = os.path.join(work_dir, "bg.mp4")
    clip_ok   = download_vertical_clip(random.choice(scene_kws), clip_path)

    if not clip_ok:
        # Fallback: create solid color background
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "color=c=black:s=1080x1920:r=30",
            "-t", "60", clip_path
        ], capture_output=True)

    # 4. Assemble video
    hook_text  = content.get("hook_overlay_text", hook)
    video_path = os.path.join(OUTPUT_DIR, f"reel_{reel_num}_{job_id}_final.mp4")
    video_ok   = assemble_reel(audio_path, clip_path, hook_text,
                                WATERMARK_TEXT, video_path)

    if not video_ok:
        return {}

    # 5. Build complete metadata
    is_hindi = "hindi" in target
    ig_caption = (content["ig_caption_hindi"] if is_hindi
                  else content["ig_caption_english"])

    result = {
        "video_path":        video_path,
        "topic":             topic,
        "target":            target,
        "format":            fmt,
        "reel_num":          reel_num,
        "job_id":            job_id,
        "script":            script,
        "virality_score":    content.get("virality_score", 70),

        # Instagram metadata
        "ig_caption":        ig_caption,
        "ig_caption_en":     content.get("ig_caption_english", ""),
        "ig_caption_hi":     content.get("ig_caption_hindi", ""),

        # YouTube Shorts metadata
        "yt_title":          content.get("yt_short_title", topic[:60]),
        "yt_description":    content.get("ig_caption_english", ""),
        "yt_tags":           ["Shorts", "YouTubeShorts", "betrayal", "truecrime",
                              "india", "viral", "reels", "shocking"],

        # Pinterest metadata
        "pinterest_title":   content.get("pinterest_title", topic[:60]),
        "pinterest_desc":    content.get("pinterest_description", ""),

        # Engagement
        "end_cta":           content.get("end_cta", "Follow for more"),
        "hook_text":         hook_text,
    }

    # Save metadata
    meta_path = video_path.replace(".mp4", "_meta.json")
    with open(meta_path, "w") as f:
        json.dump(result, f, indent=2)

    log.info("✅ Reel %d ready: %.1f MB | Virality: %d",
             reel_num, os.path.getsize(video_path)/1024/1024,
             result["virality_score"])

    return result


def create_daily_reels(intelligence_report: dict) -> list:
    """Creates all 4 daily content pieces (2 Reels + 2 Shorts use same videos)."""
    strategy = intelligence_report.get("daily_strategy", {})
    results  = []

    for i in [1, 2]:
        result = create_reel(strategy, i)
        if result:
            results.append(result)
        else:
            log.error("Reel %d creation failed", i)

    log.info("Daily reels complete: %d/%d", len(results), 2)
    return results


if __name__ == "__main__":
    # Test with mock strategy
    mock = {
        "daily_strategy": {
            "niche_1": {
                "topic": "A woman discovered her husband had a secret family for 7 years",
                "target": "india_hindi",
                "format": "shocking_reveal",
                "hook": "7 saal ka jhooth...",
            },
            "niche_2": {
                "topic": "A business partner stole 2 crore rupees and vanished",
                "target": "india_english",
                "format": "justice_served",
                "hook": "He took everything...",
            }
        }
    }
    results = create_daily_reels(mock)
    for r in results:
        print(json.dumps({"topic": r["topic"], "video": r["video_path"],
                          "virality": r["virality_score"]}, indent=2))
