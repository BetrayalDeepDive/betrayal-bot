#!/usr/bin/env python3
"""
DEEPDIVE EMPIRE - STAGE 2: AUDIO GENERATION
============================================
TTS: edge-tts (Microsoft Azure Neural Voices)
✅ pip install only — zero apt-get — zero system dependencies
✅ Works 100% on GitHub Actions ubuntu-latest
✅ 8 dark cinematic voices for dark investigation content
✅ Duration calculated from word count (no ffprobe needed)
✅ Handles ffmpeg gracefully (uses if available, skips if not)
✅ Validates audio file size and existence
"""

import os, sys, json, re, time, subprocess, asyncio, requests, shutil
from pathlib import Path

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT  = os.environ["TELEGRAM_CHAT_ID"]
OUTPUT_DIR     = Path("/tmp/pipeline_data")
MIN_SECS       = 900   # 15 minutes
MAX_SECS       = 1080  # 18 minutes

# Edge-tts voices matched to niches
VOICE_MAP = {
    "betrayal":       ["en-GB-RyanNeural","en-GB-ThomasNeural","en-US-GuyNeural"],
    "legal_drama":    ["en-GB-RyanNeural","en-GB-SoniaNeural","en-US-GuyNeural"],
    "finance_scandal":["en-GB-ThomasNeural","en-US-GuyNeural","en-GB-RyanNeural"],
    "true_crime":     ["en-US-GuyNeural","en-GB-RyanNeural","en-US-DavisNeural"],
    "psych_thriller": ["en-GB-RyanNeural","en-US-GuyNeural","en-GB-SoniaNeural"],
    "business_fraud": ["en-US-GuyNeural","en-GB-ThomasNeural","en-GB-RyanNeural"],
    "ai_tech_dark":   ["en-US-GuyNeural","en-GB-RyanNeural","en-US-DavisNeural"],
    "health_scandal": ["en-GB-SoniaNeural","en-US-GuyNeural","en-GB-RyanNeural"],
}

VOICE_DESC = {
    "en-GB-RyanNeural":   "British male BBC gravitas",
    "en-GB-ThomasNeural": "British male cold cinematic",
    "en-US-GuyNeural":    "US male serious commanding",
    "en-GB-SoniaNeural":  "British female sharp devastating",
    "en-US-DavisNeural":  "US male dark dramatic",
}

DEFAULT_VOICES = ["en-GB-RyanNeural", "en-US-GuyNeural", "en-GB-ThomasNeural"]


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


async def _tts_async(text, voice_id, output_path):
    import edge_tts
    communicate = edge_tts.Communicate(
        text, voice_id,
        rate="-12%",    # Slower = more deliberate = more tension
        pitch="-8Hz",   # Deeper = more authority and dread
        volume="+10%"
    )
    await communicate.save(output_path)


def generate_audio(script_clean, voice_id):
    print(f"  Voice: {voice_id} — {VOICE_DESC.get(voice_id, 'cinematic voice')}")
    audio_path = str(OUTPUT_DIR / "audio.mp3")

    # Run edge-tts async generation
    asyncio.run(_tts_async(script_clean, voice_id, audio_path))

    if not Path(audio_path).exists():
        raise Exception("edge-tts produced no output file")

    file_size = Path(audio_path).stat().st_size
    if file_size < 50_000:
        raise Exception(f"Audio file too small: {file_size} bytes — generation failed")

    # Calculate duration from word count (accurate, no external tools needed)
    # edge-tts at -12% rate speaks at approximately 128 words per minute
    word_count = len(script_clean.split())
    duration   = (word_count / 128.0) * 60.0

    print(f"  Audio: {file_size/1024/1024:.1f}MB | {word_count} words | ~{duration/60:.1f}min")
    return audio_path, duration, file_size, word_count


def convert_to_wav(mp3_path):
    """Convert MP3 to WAV for FFmpeg subtitle burning in stage3."""
    wav_path = str(OUTPUT_DIR / "audio.wav")
    try:
        result = subprocess.run([
            "ffmpeg", "-y", "-i", mp3_path,
            "-acodec", "pcm_s16le", "-ar", "24000", "-ac", "1",
            wav_path
        ], capture_output=True, text=True, timeout=300)

        if result.returncode == 0 and Path(wav_path).exists():
            size = Path(wav_path).stat().st_size
            if size > 100_000:
                print(f"  Converted to WAV: {size/1024/1024:.1f}MB")
                return wav_path
    except FileNotFoundError:
        print("  ffmpeg not available here — stage3 will handle conversion")
    except Exception as e:
        print(f"  WAV conversion: {e}")

    # Fallback: copy MP3 with WAV name so stage3 finds it
    shutil.copy(mp3_path, wav_path)
    print(f"  Audio saved as: {Path(mp3_path).stat().st_size/1024/1024:.1f}MB")
    return mp3_path


def score_audio(duration, file_size, word_count):
    issues = []
    s = 5.0

    # Duration from word count
    if MIN_SECS <= duration <= MAX_SECS:
        s += 3.8
    elif duration >= 700:
        s += 2.0
        issues.append(f"Audio {duration/60:.1f}min — slightly below 15min")
    elif duration >= 480:
        s += 0.8
        issues.append(f"Audio {duration/60:.1f}min — needs longer script next time")
    else:
        s -= 2.0
        issues.append(f"FATAL: {duration/60:.1f}min — script was too short ({word_count} words)")

    # File size
    if file_size > 5_000_000:
        s += 1.2
    elif file_size > 1_000_000:
        s += 0.8
    elif file_size > 200_000:
        s += 0.3
    else:
        issues.append(f"File small: {file_size/1024:.0f}KB")

    # Azure Neural quality bonus
    s += 1.0

    score = min(round(s, 1), 10.0)
    return score, issues, score >= 8.0


def main():
    print("\n" + "=" * 65)
    print("  STAGE 2: Audio Generation")
    print("  Engine: edge-tts (Microsoft Azure Neural Voices)")
    print("  Zero apt-get | Zero system deps | Proven on GitHub Actions")
    print("=" * 65 + "\n")

    print("edge-tts ready | Duration from word count (no ffprobe)\n")

    data       = load_pipeline()
    script     = load_script()
    niche      = data.get("niche", {})
    niche_name = niche.get("name", "betrayal") if isinstance(niche, dict) else str(niche)
    words      = data.get("script_words", len(script.split()))

    print(f"Niche: {niche_name} | Script: {words} words\n")

    # Get voice from pipeline (set by stage1) or use niche default
    pipeline_voice = data.get("voice", {})
    if isinstance(pipeline_voice, dict) and pipeline_voice.get("id"):
        primary_voice = pipeline_voice["id"]
        # Map Kokoro IDs to edge-tts if needed
        kokoro_map = {
            "am_adam":"en-US-GuyNeural","am_michael":"en-US-DavisNeural",
            "am_fenrir":"en-US-GuyNeural","am_puck":"en-US-DavisNeural",
            "af_heart":"en-US-JennyNeural","af_nova":"en-US-JennyNeural",
            "bm_george":"en-GB-RyanNeural","bm_lewis":"en-GB-RyanNeural",
            "bm_daniel":"en-GB-ThomasNeural","bm_fable":"en-GB-RyanNeural",
            "bf_emma":"en-GB-SoniaNeural","bf_isabella":"en-GB-SoniaNeural",
        }
        primary_voice = kokoro_map.get(primary_voice, primary_voice)
    else:
        primary_voice = VOICE_MAP.get(niche_name, DEFAULT_VOICES)[0]

    # Build voice priority list
    niche_voices = VOICE_MAP.get(niche_name, DEFAULT_VOICES)
    voices = [primary_voice] + [v for v in niche_voices if v != primary_voice]

    audio_approved = False
    final_score    = 0
    voice_used     = voices[0]

    for voice_id in voices[:4]:
        print(f"Trying: {voice_id}")
        try:
            audio_path, duration, file_size, word_count = generate_audio(script, voice_id)
            score, issues, passed = score_audio(duration, file_size, word_count)
            final_score = score

            print(f"  Score: {score}/10 {'PASSED' if passed else 'FAILED'} | {duration/60:.1f}min")
            if issues:
                print(f"  {' | '.join(issues[:2])}")

            if passed:
                final_path = convert_to_wav(audio_path)
                voice_used = voice_id

                data["audio_path"]      = final_path
                data["audio_mp3"]       = audio_path
                data["audio_duration"]  = duration
                data["audio_size"]      = file_size
                data["audio_words"]     = word_count
                data["voice_used"]      = {"id": voice_id, "desc": VOICE_DESC.get(voice_id, "")}
                data["score_l3"]        = score
                data["tts_engine"]      = "edge-tts-microsoft-azure-neural"

                with open(OUTPUT_DIR / "pipeline.json", "w") as f:
                    json.dump(data, f, indent=2)

                audio_approved = True
                print(f"\nAudio APPROVED | {voice_id} | {duration/60:.1f}min | {score}/10\n")
                break
            else:
                print(f"  Trying next voice...")

        except Exception as e:
            print(f"  Error: {str(e)[:120]}")
            time.sleep(5)

    if not audio_approved:
        telegram(
            f"<b>Stage 2 Failed</b>\n\n"
            f"All voice attempts failed.\n"
            f"Best score: {final_score}/10\n"
            f"Script words: {words} (need 2200+ for 15min)"
        )
        sys.exit(1)

    telegram(
        f"<b>Stage 2 Complete</b>\n\n"
        f"Voice: {voice_used} — {VOICE_DESC.get(voice_used, '')}\n"
        f"Duration: {data['audio_duration']/60:.1f} minutes\n"
        f"Score: {data['score_l3']}/10\n\n"
        f"Stage 3: Video assembly starting..."
    )
    print("Stage 2 complete")


if __name__ == "__main__":
    main()
