#!/usr/bin/env python3
"""
DEEPDIVE EMPIRE — STAGE 2: KOKORO TTS AUDIO GENERATION
12 voices (6 US + 6 British) | Zero robotic output tolerance
Target: 15-18 minutes | Validates every chunk for silence
Auto-switches voice if primary fails | Max 4 voice attempts
"""

import os, sys, json, re, time, subprocess, requests
from pathlib import Path

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT  = os.environ["TELEGRAM_CHAT_ID"]
OUTPUT_DIR     = Path("/tmp/pipeline_data")
QUALITY_MIN    = 8.5
MIN_SECS       = 900   # 15 min
MAX_SECS       = 1080  # 18 min

ALL_VOICES = [
    {"id": "am_adam",     "lang": "a", "gender": "M", "tone": "commanding_deep",
     "desc": "Deep commanding US male — maximum authority"},
    {"id": "am_michael",  "lang": "a", "gender": "M", "tone": "intense_investigative",
     "desc": "Intense investigative US male — psychological depth"},
    {"id": "am_fenrir",   "lang": "a", "gender": "M", "tone": "darkest_dramatic",
     "desc": "Darkest US male voice — sends genuine chills"},
    {"id": "am_puck",     "lang": "a", "gender": "M", "tone": "urgent_conversational",
     "desc": "Urgent conversational US male — builds relentless tension"},
    {"id": "af_heart",    "lang": "a", "gender": "F", "tone": "emotionally_devastating",
     "desc": "Emotionally devastating US female"},
    {"id": "af_nova",     "lang": "a", "gender": "F", "tone": "dark_journalistic",
     "desc": "Dark journalistic US female — investigative documentary"},
    {"id": "bm_george",   "lang": "b", "gender": "M", "tone": "bbc_gravitas",
     "desc": "BBC documentary gravitas — most trusted voice"},
    {"id": "bm_lewis",    "lang": "b", "gender": "M", "tone": "cinematic_deep",
     "desc": "Deepest British cinematic male — maximum atmosphere"},
    {"id": "bm_daniel",   "lang": "b", "gender": "M", "tone": "cold_measured",
     "desc": "Cold measured British male — financial crime authority"},
    {"id": "bm_fable",    "lang": "b", "gender": "M", "tone": "dark_storytelling",
     "desc": "Master dark storyteller — grips and never lets go"},
    {"id": "bf_emma",     "lang": "b", "gender": "F", "tone": "sharp_authoritative",
     "desc": "Sharp authoritative British female — cuts through deception"},
    {"id": "bf_isabella", "lang": "b", "gender": "F", "tone": "haunting_intense",
     "desc": "Haunting intense British female — unforgettable narration"},
]


def telegram(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT, "text": msg, "parse_mode": "HTML"},
            timeout=15
        )
    except:
        pass


def load_pipeline():
    with open(OUTPUT_DIR / "pipeline.json") as f:
        return json.load(f)


def load_script():
    with open(OUTPUT_DIR / "script.txt", encoding="utf-8") as f:
        return f.read()


def generate_audio(script_clean, voice):
    """Generate audio with Kokoro TTS. Validates every chunk for silence."""
    print(f"Voice: {voice['id']} — {voice['desc']}")

    sentences = re.split(r'(?<=[.!?])\s+', script_clean)
    chunks, cur = [], ""
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        if len(cur) + len(sent) + 1 <= 400:
            cur += (" " if cur else "") + sent
        else:
            if cur:
                chunks.append(cur)
            cur = sent
    if cur:
        chunks.append(cur)

    total = len(chunks)
    print(f"Processing {total} audio chunks...")

    kokoro_code = f"""
import sys, soundfile as sf, numpy as np, os
from kokoro import KPipeline

try:
    pl = KPipeline(lang_code='{voice["lang"]}')
    print("Pipeline ready", flush=True)
except Exception as e:
    print(f"INIT_FAIL:{{e}}", file=sys.stderr)
    sys.exit(1)

chunks = {json.dumps(chunks)}
audio_parts, ok, total = [], 0, len(chunks)

for i, chunk in enumerate(chunks):
    if not chunk.strip():
        continue
    try:
        parts = []
        for _, _, audio in pl(chunk, voice='{voice["id"]}', speed=0.87, split_pattern=None):
            parts.append(audio)
        if parts:
            combined = np.concatenate(parts)
            peak = np.max(np.abs(combined))
            if peak > 0.0005:
                audio_parts.append(combined)
                ok += 1
            else:
                print(f"SILENT:{{i}}", file=sys.stderr)
        if (i+1) % 10 == 0 or i == total - 1:
            print(f"PROGRESS:{{i+1}}/{{total}}", flush=True)
    except Exception as e:
        print(f"CHUNK_FAIL:{{i}}:{{str(e)[:60]}}", file=sys.stderr)

rate = ok / total if total > 0 else 0
print(f"RATE:{{ok}}/{{total}}:{{rate:.2f}}", flush=True)

if not audio_parts or rate < 0.80:
    print(f"FATAL: Only {{ok}}/{{total}} chunks OK", file=sys.stderr)
    sys.exit(1)

final = np.concatenate(audio_parts)
peak = np.max(np.abs(final))
if peak > 0:
    final = final / peak * 0.93

os.makedirs('/tmp/pipeline_data', exist_ok=True)
sf.write('/tmp/pipeline_data/audio.wav', final, 24000, subtype='PCM_16')
dur = len(final) / 24000
sz = os.path.getsize('/tmp/pipeline_data/audio.wav')
print(f"DONE:{{dur:.1f}}:{{ok}}:{{total}}:{{sz}}", flush=True)
"""

    with open("/tmp/tts_run.py", "w") as f:
        f.write(kokoro_code)

    result = subprocess.run(
        [sys.executable, "/tmp/tts_run.py"],
        capture_output=True, text=True, timeout=2400
    )

    if result.returncode != 0:
        raise Exception(f"Kokoro failed: {result.stderr[-400:]}")

    chunks_ok = total
    duration = file_size = 0
    for line in result.stdout.split('\n'):
        if line.startswith("DONE:"):
            parts = line.replace("DONE:", "").split(":")
            if len(parts) >= 4:
                try:
                    duration  = float(parts[0])
                    chunks_ok = int(parts[1])
                    file_size = int(parts[3])
                except:
                    pass
        if line.startswith("PROGRESS:"):
            print(f"  {line}")

    audio_path = OUTPUT_DIR / "audio.wav"
    if not audio_path.exists() or audio_path.stat().st_size < 200_000:
        raise Exception(f"Audio missing or too small")

    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(audio_path)],
        capture_output=True, text=True
    )
    duration = float(json.loads(probe.stdout)["format"]["duration"])
    file_size = audio_path.stat().st_size

    print(f"Audio: {duration/60:.1f}min | {file_size/1024/1024:.1f}MB | {chunks_ok}/{total} chunks")
    return str(audio_path), duration, chunks_ok, total


def score_audio(duration, file_size, chunks_ok, chunks_total):
    issues = []
    s = 5.0
    rate = chunks_ok / max(chunks_total, 1)

    if MIN_SECS <= duration <= MAX_SECS:
        s += 3.8
    elif duration >= 780:
        s += 1.8
        issues.append(f"Audio {duration/60:.1f}min — below 15min")
    elif duration >= 480:
        s += 0.3
        issues.append(f"CRITICAL: {duration/60:.1f}min — too short")
    else:
        s -= 2.0
        issues.append(f"FATAL: {duration/60:.1f}min — TTS failed")

    if file_size > 25_000_000:
        s += 1.2
    elif file_size > 8_000_000:
        s += 0.6
    elif file_size > 2_000_000:
        s += 0.1
        issues.append(f"Audio {file_size/1024/1024:.1f}MB small")
    else:
        issues.append(f"FATAL: {file_size/1024:.0f}KB — TTS critically failed")

    if rate >= 0.97:
        s += 1.0
    elif rate >= 0.90:
        s += 0.5
        issues.append(f"TTS {rate*100:.0f}% chunk success")
    else:
        s -= 0.8
        issues.append(f"CRITICAL: Only {rate*100:.0f}% chunks succeeded")

    score = min(round(s, 1), 10.0)
    return score, issues, score >= QUALITY_MIN


def main():
    print("\n" + "=" * 65)
    print("  STAGE 2: Kokoro TTS Audio Generation")
    print("  12 voices | 6 US + 6 British | Zero robotic output")
    print("  Target: 15-18 minutes | Validates every chunk")
    print("=" * 65 + "\n")

    print("Installing Kokoro TTS...")
    subprocess.run(
        ["pip", "install", "kokoro>=0.9.4", "soundfile", "scipy", "numpy", "--break-system-packages", "-q"],
        capture_output=True
    )
    subprocess.run(["apt-get", "install", "-y", "-q", "espeak-ng", "ffmpeg"], capture_output=True)
    print("Kokoro TTS ready\n")

    data   = load_pipeline()
    script = load_script()
    primary_voice = data["voice"]
    niche  = data["niche"]

    print(f"Niche: {niche['name']} | Script: {data['script_words']} words")
    print(f"Primary voice: {primary_voice['id']}\n")

    # Try primary voice first, then backups in niche-order
    backup_voices = [v for v in ALL_VOICES if v["id"] != primary_voice["id"]][:3]
    voices_to_try = [primary_voice] + backup_voices

    audio_approved = False
    final_score    = 0
    voice_used     = primary_voice

    for voice in voices_to_try:
        print(f"Trying: {voice['id']} — {voice['desc']}")
        try:
            audio_path, duration, chunks_ok, chunks_total = generate_audio(script, voice)
            score, issues, passed = score_audio(duration, Path(audio_path).stat().st_size, chunks_ok, chunks_total)
            final_score = score

            print(f"  L3 Audio: {score}/10 {'PASSED' if passed else 'FAILED'} | {duration/60:.1f}min")
            if issues:
                print(f"  Issues: {' | '.join(issues[:2])}")

            if passed:
                voice_used = voice
                data["audio_duration"]   = duration
                data["audio_size"]       = Path(audio_path).stat().st_size
                data["audio_chunks_ok"]  = chunks_ok
                data["audio_chunks_total"] = chunks_total
                data["voice_used"]       = voice
                data["score_l3"]         = score
                with open(OUTPUT_DIR / "pipeline.json", "w") as f:
                    json.dump(data, f, indent=2)
                audio_approved = True
                print(f"\nAudio APPROVED — Voice: {voice['id']} | Score: {score}/10\n")
                break
            else:
                print(f"  Voice {voice['id']} failed — trying next...")

        except Exception as e:
            print(f"  Voice {voice['id']} error: {str(e)[:100]}")
            time.sleep(10)

    if not audio_approved:
        telegram(
            f"<b>Stage 2 Failed — Audio</b>\n"
            f"All voice attempts failed.\n"
            f"Best L3 score: {final_score}/10\n"
            f"Required: {QUALITY_MIN}"
        )
        sys.exit(1)

    telegram(
        f"<b>Stage 2 Complete — Audio</b>\n\n"
        f"Voice: {voice_used['id']} — {voice_used['desc']}\n"
        f"Duration: {data['audio_duration']/60:.1f} minutes\n"
        f"Chunks: {data['audio_chunks_ok']}/{data['audio_chunks_total']} OK\n"
        f"L3 Score: {data['score_l3']}/10\n\n"
        f"Stage 3: Video assembly starting..."
    )
    print("Stage 2 complete")


if __name__ == "__main__":
    main()
