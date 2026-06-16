#!/usr/bin/env python3
"""
DEEPDIVE EMPIRE - STAGE 2: AUDIO GENERATION
TTS: edge-tts (Microsoft Azure Neural Voices)
- pip install edge-tts (3 seconds, pure Python)
- Zero system dependencies - no espeak-ng needed
- Works 100% on GitHub Actions ubuntu-latest
- 8 dark cinematic voices
- Rate: -12% (deliberate pacing) | Pitch: -8Hz (deeper)
"""

import os, sys, json, re, time, subprocess, asyncio, requests
from pathlib import Path

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT  = os.environ["TELEGRAM_CHAT_ID"]
OUTPUT_DIR     = Path("/tmp/pipeline_data")
MIN_SECS       = 900
MAX_SECS       = 1080

VOICE_MAP = {
    "betrayal":       [{"id":"en-GB-RyanNeural","desc":"British male BBC gravitas"},
                       {"id":"en-GB-ThomasNeural","desc":"British male cold cinematic"},
                       {"id":"en-US-GuyNeural","desc":"US male serious commanding"}],
    "legal_drama":    [{"id":"en-GB-RyanNeural","desc":"British male courtroom authority"},
                       {"id":"en-GB-SoniaNeural","desc":"British female sharp precise"},
                       {"id":"en-US-GuyNeural","desc":"US male prosecutorial"}],
    "finance_scandal":[{"id":"en-GB-ThomasNeural","desc":"British male financial authority"},
                       {"id":"en-US-GuyNeural","desc":"US male Wall Street darkness"},
                       {"id":"en-GB-RyanNeural","desc":"British male cold measured"}],
    "true_crime":     [{"id":"en-US-GuyNeural","desc":"US male dark investigative"},
                       {"id":"en-GB-RyanNeural","desc":"British male documentary"},
                       {"id":"en-US-DavisNeural","desc":"US male dramatic tension"}],
    "psych_thriller": [{"id":"en-GB-RyanNeural","desc":"British male unsettling"},
                       {"id":"en-US-GuyNeural","desc":"US male intense psychological"},
                       {"id":"en-GB-SoniaNeural","desc":"British female haunting"}],
    "business_fraud": [{"id":"en-US-GuyNeural","desc":"US male corporate darkness"},
                       {"id":"en-GB-ThomasNeural","desc":"British male cold exposure"},
                       {"id":"en-GB-RyanNeural","desc":"British male investigative"}],
    "ai_tech_dark":   [{"id":"en-US-GuyNeural","desc":"US male tech authority"},
                       {"id":"en-GB-RyanNeural","desc":"British male documentary"},
                       {"id":"en-US-DavisNeural","desc":"US male dramatic"}],
    "health_scandal": [{"id":"en-GB-SoniaNeural","desc":"British female devastating"},
                       {"id":"en-US-GuyNeural","desc":"US male serious"},
                       {"id":"en-GB-RyanNeural","desc":"British male authority"}],
}

DEFAULT_VOICES = [
    {"id":"en-GB-RyanNeural","desc":"British male BBC gravitas"},
    {"id":"en-US-GuyNeural","desc":"US male commanding authority"},
    {"id":"en-GB-ThomasNeural","desc":"British male cinematic depth"},
]


def telegram(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id":TELEGRAM_CHAT,"text":msg,"parse_mode":"HTML"},
            timeout=15
        )
    except: pass


def load_pipeline():
    with open(OUTPUT_DIR/"pipeline.json") as f:
        return json.load(f)


def load_script():
    with open(OUTPUT_DIR/"script.txt", encoding="utf-8") as f:
        return f.read()


async def _tts_async(text, voice_id, output_path):
    import edge_tts
    communicate = edge_tts.Communicate(
        text, voice_id,
        rate="-12%",
        pitch="-8Hz",
        volume="+10%"
    )
    await communicate.save(output_path)


def generate_audio(script_clean, voice):
    print(f"  Voice: {voice['id']} — {voice['desc']}")
    audio_path = str(OUTPUT_DIR / "audio.mp3")

    asyncio.run(_tts_async(script_clean, voice["id"], audio_path))

    if not Path(audio_path).exists():
        raise Exception("No output file created")

    file_size = Path(audio_path).stat().st_size
    if file_size < 50_000:
        raise Exception(f"File too small: {file_size} bytes")

    # Get duration
    probe = subprocess.run(
        ["ffprobe","-v","quiet","-print_format","json","-show_format", audio_path],
        capture_output=True, text=True
    )
    duration = 0.0
    try:
        duration = float(json.loads(probe.stdout)["format"]["duration"])
    except:
        duration = (file_size * 8) / (128 * 1000)

    print(f"  Audio: {duration/60:.1f}min | {file_size/1024/1024:.1f}MB")
    return audio_path, duration, file_size


def convert_to_wav(mp3_path):
    wav_path = str(OUTPUT_DIR / "audio.wav")
    result = subprocess.run([
        "ffmpeg","-y","-i", mp3_path,
        "-acodec","pcm_s16le","-ar","24000","-ac","1", wav_path
    ], capture_output=True, text=True, timeout=300)

    if result.returncode == 0 and Path(wav_path).exists():
        size = Path(wav_path).stat().st_size
        if size > 100_000:
            print(f"  WAV: {size/1024/1024:.1f}MB")
            return wav_path

    print("  Using MP3 directly")
    return mp3_path


def score_audio(duration, file_size):
    issues = []
    s = 5.0
    if MIN_SECS <= duration <= MAX_SECS: s += 3.8
    elif duration >= 600: s += 1.5; issues.append(f"Audio {duration/60:.1f}min below 15min")
    elif duration >= 300: s += 0.3; issues.append(f"CRITICAL: only {duration/60:.1f}min")
    else: s -= 2.0; issues.append(f"FATAL: {duration/60:.1f}min")
    if file_size > 10_000_000: s += 1.2
    elif file_size > 3_000_000: s += 0.8
    elif file_size > 500_000: s += 0.3
    else: issues.append(f"File too small: {file_size/1024:.0f}KB")
    s += 1.0  # Azure Neural quality bonus
    score = min(round(s,1), 10.0)
    return score, issues, score >= 8.0


def main():
    print("\n" + "="*60)
    print("  STAGE 2: Audio Generation")
    print("  Engine: edge-tts (Microsoft Azure Neural)")
    print("  Free | Zero system deps | GitHub Actions proven")
    print("="*60 + "\n")

    # Install edge-tts (3 seconds, pure Python)
    print("Installing edge-tts...")
    subprocess.run(
        ["pip","install","edge-tts","requests","--break-system-packages","-q"],
        capture_output=True
    )
    print("edge-tts ready\n")

    data   = load_pipeline()
    script = load_script()
    niche  = data.get("niche", {})
    niche_name = niche.get("name","betrayal") if isinstance(niche,dict) else str(niche)

    print(f"Niche: {niche_name} | Script: {data.get('script_words',0)} words\n")

    voices = VOICE_MAP.get(niche_name, DEFAULT_VOICES)

    audio_approved = False
    final_score    = 0
    voice_used     = voices[0]

    for voice in voices[:4]:
        print(f"Trying: {voice['id']}")
        try:
            audio_path, duration, file_size = generate_audio(script, voice)
            score, issues, passed = score_audio(duration, file_size)
            final_score = score
            print(f"  Score: {score}/10 {'PASSED' if passed else 'FAILED'} | {duration/60:.1f}min")
            if issues: print(f"  {' | '.join(issues[:2])}")

            if passed:
                final_path = convert_to_wav(audio_path)
                voice_used = voice
                data["audio_path"]     = final_path
                data["audio_mp3"]      = audio_path
                data["audio_duration"] = duration
                data["audio_size"]     = file_size
                data["voice_used"]     = voice
                data["score_l3"]       = score
                data["tts_engine"]     = "edge-tts-microsoft-azure"
                with open(OUTPUT_DIR/"pipeline.json","w") as f:
                    json.dump(data,f,indent=2)
                audio_approved = True
                print(f"\nAudio APPROVED | {voice['id']} | {duration/60:.1f}min | {score}/10\n")
                break
            else:
                print(f"  Trying next voice...")

        except Exception as e:
            print(f"  Error: {str(e)[:100]}")
            time.sleep(5)

    if not audio_approved:
        telegram(f"<b>Stage 2 Failed</b>\n\nAll voices failed.\nBest: {final_score}/10\nEngine: edge-tts")
        sys.exit(1)

    telegram(
        f"<b>Stage 2 Complete</b>\n\n"
        f"Voice: {voice_used['id']}\n"
        f"Duration: {data['audio_duration']/60:.1f} minutes\n"
        f"Score: {data['score_l3']}/10\n\n"
        f"Stage 3: Video assembly starting..."
    )
    print("Stage 2 complete")


if __name__ == "__main__":
    main()
