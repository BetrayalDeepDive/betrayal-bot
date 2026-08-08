"""
Word timings when transcription is unavailable — the last two links in the
subtitle chain.

WHY THIS EXISTS
---------------
Subtitles on this channel come from Groq's Whisper, run on the final narration
audio. That is one provider and one model, and when it is down there is no
second opinion:

    run 31156373254:  Whisper request failed (502) x3  ->  no captions
    run before that:  Whisper request failed (413) x3  ->  no captions

Both times the pipeline fell back to generate_fallback_ass(), which spreads the
script evenly across the runtime by word count. Even spreading is the worst
possible model of speech: it assumes no pauses, no breath, no SSML rate change
and no sentence-final lengthening. The error accumulates in one direction, so
the captions drift further out of sync the longer the episode runs -- reported,
accurately, as "the subtitles are not even syncing, they are moving too fast
or too slow".

WHAT THIS DOES INSTEAD
----------------------
It does not need to recognise the speech. The exact script is already known --
it is what was sent to the voice. The only unknown is WHEN each word was said,
and the audio answers that directly: speech is loud, pauses are quiet, and
ffmpeg's silencedetect reports every pause with real timestamps.

So the words are laid onto the segments of the audio that actually contain
speech, in proportion to how long each of those segments lasts, and no word is
ever placed inside a pause. That single correction removes the dominant source
of drift, because pauses are exactly what even spreading cannot see.

It needs no API key, no model download and no network, so unlike every other
link in the chain it cannot be unavailable.

align_words() returns the same shape Groq returns -- [{"word", "start",
"end"}] -- so it feeds caption_timing.ass_from_words() unchanged.
"""
import json
import re
import subprocess


# Below this, a gap is a natural word boundary rather than a pause worth
# modelling. Measured against real narration: inter-word gaps in continuous
# speech sit under 0.20s, sentence breaks land at 0.35-0.9s, and the pause
# before a reveal runs past a second.
MIN_PAUSE_SEC = 0.28

# Silence threshold. Narration is mastered near -16 LUFS, room tone and the
# music bed sit far below; -34 dBFS separates them without treating a quiet
# consonant as a pause.
SILENCE_DB = -34


def _run(cmd, timeout=300):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def audio_duration(path):
    """Seconds, or None if the file cannot be probed."""
    r = _run(["ffprobe", "-v", "quiet", "-print_format", "json",
              "-show_format", str(path)])
    try:
        return float(json.loads(r.stdout)["format"]["duration"])
    except Exception:
        return None


def speech_spans(path, total=None, min_pause=MIN_PAUSE_SEC, db=SILENCE_DB):
    """The stretches of the audio that actually contain speech.

    Returns [(start, end), ...] covering the file minus its pauses. If the
    probe fails or finds nothing, returns one span covering everything, which
    degrades this to plain even spreading -- no worse than what it replaces.
    """
    total = total or audio_duration(path)
    if not total:
        return []
    r = _run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
              "-af", "silencedetect=noise=%ddB:d=%.2f" % (db, min_pause),
              "-f", "null", "-"])
    text = (r.stderr or "") + (r.stdout or "")

    pauses = []
    start = None
    for m in re.finditer(r"silence_(start|end):\s*(-?[\d.]+)", text):
        kind, value = m.group(1), float(m.group(2))
        if kind == "start":
            start = value
        elif start is not None:
            pauses.append((max(0.0, start), min(total, value)))
            start = None
    if start is not None:                      # trailing silence to EOF
        pauses.append((max(0.0, start), total))

    spans, cursor = [], 0.0
    for p0, p1 in sorted(pauses):
        if p0 - cursor > 0.05:
            spans.append((cursor, p0))
        cursor = max(cursor, p1)
    if total - cursor > 0.05:
        spans.append((cursor, total))
    return spans or [(0.0, total)]


def _weight(word):
    """Roughly how long a word takes to say.

    Length in characters is a decent proxy and needs no dictionary; the floor
    stops "a" and "I" collapsing to nothing, and the vowel-group count keeps a
    long word with few syllables ("through") from being over-weighted.
    """
    letters = re.sub(r"[^A-Za-z']", "", word) or word
    syllables = max(1, len(re.findall(r"[aeiouyAEIOUY]+", letters)))
    return max(1.6, 0.55 * len(letters) + 1.1 * syllables)


def align_words(audio_path, script_text, total=None):
    """Place the KNOWN script onto the audio's real speech, word by word.

    Returns [{"word", "start", "end"}, ...] in Groq's shape, or [] if there is
    nothing to align.
    """
    words = [w for w in (script_text or "").split() if w.strip()]
    if not words:
        return []
    total = total or audio_duration(audio_path)
    if not total:
        return []

    spans = speech_spans(audio_path, total=total)
    speech = sum(b - a for a, b in spans) or total

    # Each word's share of the SPEAKING time, not of the wall clock. This is
    # the whole correction: the pauses are removed from the denominator, so a
    # long silence no longer pushes every later word off its mark.
    weights = [_weight(w) for w in words]
    per_unit = speech / (sum(weights) or 1.0)

    out = []
    span_i = 0
    cursor = spans[0][0]
    for word, weight in zip(words, weights):
        need = weight * per_unit
        # Walk to a span with room left, skipping over pauses entirely.
        while span_i < len(spans) - 1 and cursor >= spans[span_i][1] - 1e-6:
            span_i += 1
            cursor = spans[span_i][0]
        start = cursor
        end = start + need
        room = spans[span_i][1]
        if end > room:
            # The word straddles a pause. It keeps the time available in this
            # span and resumes on the far side, so it is never shown DURING
            # the silence -- which is precisely the artefact that made the
            # old captions look like they were running ahead of the voice.
            left = need - (room - start)
            end = room
            if span_i < len(spans) - 1:
                span_i += 1
                cursor = spans[span_i][0] + left
            else:
                cursor = room
        else:
            cursor = end
        out.append({"word": word, "start": round(start, 3),
                    "end": round(max(end, start + 0.06), 3)})
    return out


def local_whisper_words(audio_path, model="tiny.en"):
    """Transcribe on this machine, with no API and no key.

    faster-whisper is CPU-only and pip-installable, so it is a genuine backup
    for an outage at the hosted provider rather than another call to the same
    place. It is optional: when the package is not installed this returns None
    and the chain moves on to align_words(), which needs nothing at all.
    """
    try:
        from faster_whisper import WhisperModel
    except Exception:
        return None
    try:
        m = WhisperModel(model, device="cpu", compute_type="int8")
        segments, _ = m.transcribe(str(audio_path), word_timestamps=True,
                                   language="en")
        out = []
        for seg in segments:
            for w in (seg.words or []):
                out.append({"word": w.word.strip(),
                            "start": round(float(w.start), 3),
                            "end": round(float(w.end), 3)})
        return out or None
    except Exception:
        return None
