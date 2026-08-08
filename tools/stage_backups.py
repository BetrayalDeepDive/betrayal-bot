#!/usr/bin/env python3
"""
How many real backups each stage of Channel 1 actually has.

    python3 tools/stage_backups.py

"There should be three to four backups for each of the stages."

That is checkable, and it was not being checked. Run 31156373254 shipped an
episode whose subtitles were guessed, because the subtitle stage had exactly
one provider behind three retries of the same endpoint -- and nothing anywhere
would have told you that until the captions were visibly out of sync.

A BACKUP IS A DIFFERENT MECHANISM, NOT A SECOND ATTEMPT. Calling the same URL
three times is one route. Two models on one vendor's API is one and a half:
it survives a model outage, not an account or network one. What counts here is
a route that fails independently of the ones above it, so the entries below are
listed with what each one actually depends on.

Exit code 1 if any stage has fewer than MIN_ROUTES independent routes.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))

MIN_ROUTES = 3

# (stage, [(route, depends on, proof this route exists in the tree)])
# The proof is a (file, substring) pair, so a route that gets deleted or
# renamed stops counting instead of living on in a comment.
STAGES = [
    ("Script / text generation", [
        ("Cloudflare Workers AI", "CLOUDFLARE_API_TOKEN",
         ("channels/betrayal_deepdive/clinical_pipeline.py", "Cloudflare")),
        ("Groq", "GROQ_API_KEY",
         ("channels/betrayal_deepdive/clinical_pipeline.py", "api.groq.com")),
        ("Cerebras", "CEREBRAS_API_KEY",
         ("channels/betrayal_deepdive/clinical_pipeline.py", "Cerebras")),
        ("NVIDIA NIM", "NVIDIA_API_KEY",
         ("channels/betrayal_deepdive/clinical_pipeline.py", "NVIDIA")),
        ("SambaNova", "SAMBANOVA_API_KEY",
         ("channels/betrayal_deepdive/clinical_pipeline.py", "SambaNova")),
        ("Mistral", "MISTRAL_API_KEY",
         ("channels/betrayal_deepdive/clinical_pipeline.py", "Mistral")),
        ("Cohere", "COHERE_API_KEY",
         ("channels/betrayal_deepdive/clinical_pipeline.py", "Cohere")),
        ("OpenRouter", "OPENROUTER_API_KEY",
         ("channels/betrayal_deepdive/clinical_pipeline.py", "OpenRouter")),
    ]),
    ("Narration audio", [
        ("Kokoro (local, on the runner)", "nothing — runs here",
         ("channels/betrayal_deepdive/clinical_pipeline.py", "run_audio_with_kokoro")),
        ("edge-tts SSML", "Microsoft's public endpoint",
         ("channels/betrayal_deepdive/clinical_pipeline.py", "edge-tts")),
        ("gTTS", "Google's public endpoint",
         ("channels/betrayal_deepdive/clinical_pipeline.py", "gTTS")),
        ("espeak-ng (local)", "nothing — runs here",
         ("channels/betrayal_deepdive/clinical_pipeline.py", "espeak")),
    ]),
    ("Subtitles", [
        ("Groq Whisper, retried", "GROQ_API_KEY",
         ("channels/betrayal_deepdive/clinical_pipeline.py", "_whisper_words_chunked")),
        ("faster-whisper (local)", "an optional pip package",
         ("channels/betrayal_deepdive/clinical_pipeline.py", "_local_whisper_ass")),
        ("script-to-audio alignment", "nothing — ffmpeg only",
         ("channels/betrayal_deepdive/clinical_pipeline.py", "_aligned_ass")),
        ("even spreading (last resort)", "nothing",
         ("channels/betrayal_deepdive/clinical_pipeline.py", "generate_fallback_ass")),
    ]),
    ("Thumbnail photographs", [
        ("Pixabay", "PIXABAY_KEY",
         ("channels/betrayal_deepdive/clinical_pipeline.py", "pixabay")),
        ("Pexels", "PEXELS_API_KEY",
         ("channels/betrayal_deepdive/clinical_pipeline.py", "pexels")),
        ("local stock library", "nothing — files in the repo",
         ("video_pipeline/photo_thumbnail.py", "stock_library")),
        ("drawn clinical renderer", "nothing",
         ("channels/betrayal_deepdive/clinical_pipeline.py", "clinical_thumbnail")),
    ]),
    ("Episode visuals", [
        ("FIGURE — the paper's own images", "the PMC hosts",
         ("video_pipeline/medical_segments.py", 'register == "FIGURE"')),
        ("SCENE — real photographs", "stock library, then Pixabay",
         ("video_pipeline/medical_segments.py", "render_scene_still")),
        ("ANATOMY / CHART / BOARD / TIMELINE", "nothing — drawn here",
         ("video_pipeline/medical_segments.py", "render_anatomy_still")),
        ("last-resort card", "nothing",
         ("video_pipeline/medical_segments.py", "render_last_resort_still")),
    ]),
    ("Review decisions", [
        ("Telegram buttons", "TELEGRAM_TOKEN",
         ("video_pipeline/human_review_gate.py", "reply_markup")),
        ("Telegram text reply", "TELEGRAM_TOKEN",
         ("video_pipeline/human_review_gate.py", '"CANCELLED", "CANCELED"')),
        ("email", "GMAIL_APP_PASSWORD",
         ("video_pipeline/human_review_gate.py", "send_email_notification")),
        ("per-gate share, then proceed", "nothing",
         ("video_pipeline/human_review_gate.py", "_gate_share_seconds")),
    ]),
]


def main():
    print("\nChannel 1 — backup routes per stage\n" + "-" * 74)
    failed = []
    for stage, routes in STAGES:
        live = []
        for name, needs, (path, token) in routes:
            full = os.path.join(ROOT, path)
            try:
                present = token in open(full, encoding="utf-8").read()
            except Exception:
                present = False
            live.append((present, name, needs))
        n = sum(1 for ok, _, _ in live if ok)
        flag = "OK  " if n >= MIN_ROUTES else "THIN"
        print("\n  %s  %-28s %d route(s)" % (flag, stage, n))
        for ok, name, needs in live:
            print("        %s %-34s needs: %s"
                  % ("+" if ok else "-", name, needs))
        if n < MIN_ROUTES:
            failed.append((stage, n))

    print("\n" + "-" * 74)
    if failed:
        print("  BELOW THE %d-ROUTE BAR:" % MIN_ROUTES)
        for stage, n in failed:
            print("    - %s (%d)" % (stage, n))
        return 1
    print("  Every stage has at least %d independent routes.\n" % MIN_ROUTES)
    return 0


if __name__ == "__main__":
    sys.exit(main())
