"""
A third narration voice that is neural, local, and needs no account.

WHY THIS EXISTS
---------------
The audio gate scores the voice tier at 40% of the total and the gate is 8.5.
Work the arithmetic through with the numbers in quality_scoring.py and the
picture is not what the backup inventory claimed:

    ElevenLabs  10.0 -> ceiling 10.0   can publish   (needs a paid key)
    Kokoro       9.5 -> ceiling  9.8   can publish   (local, no key)
    edge-tts     9.0 -> ceiling  9.6   can publish   (Microsoft endpoint)
    Fish Audio   8.5 -> ceiling  9.4   can publish   (needs a key)
    gTTS         4.0 -> ceiling  7.6   CAN NEVER PASS
    espeak       1.5 -> ceiling  6.6   CAN NEVER PASS

So of the four routes the inventory listed for narration, two of them could
never produce a publishable episode no matter how perfect the file was. With
no API keys set, the real count was TWO: Kokoro and edge-tts. Lose both -- a
Microsoft outage on a day Kokoro's weights fail to fetch -- and there is no
episode at all, because everything left is barred by the gate.

That is the gap this closes. Piper is a real neural TTS that runs entirely on
the runner, needs no key and no account, and sounds like a person rather than
a 1980s speech chip. It makes three key-free publishable routes instead of
two, which is what "three to four backups for each of the stages" actually
requires once you count only the routes that can really ship.

WHAT IT IS NOT
--------------
Not a replacement for Kokoro. Kokoro stays primary -- it was made primary on
purpose because it sounds more human, and nothing here changes that. This is
the backstop that runs when the better tiers are unavailable, and its whole
job is to be clearly better than silence and clearly better than a robot.

ACCENT
------
The channel's voices are British and the best-quality Piper voices are
American. For a tier that only runs when two better ones have already failed,
"sounds like a person" beats "has the right accent" -- an American narrator
for one episode is a far smaller problem than a skipped day or a synthetic
buzz. British voices are listed first where they exist at a usable quality
and are picked when they do.
"""
import os
import subprocess
import tarfile
import urllib.request

# Piper's own release assets. These are plain files on GitHub releases, not an
# API call, so they survive in environments where the GitHub API is scoped.
_BASE = "https://github.com/rhasspy/piper/releases/download/v0.0.2"

# Ordered best-first WITHIN each gender. The suffix is the model's own quality
# tier and it is audible: "high" is worth the extra download and the extra
# synthesis time, "low" is the last thing to reach for.
VOICES = {
    "male":   ("en-us-ryan-high", "en-us-ryan-medium", "en-gb-alan-low"),
    "female": ("en-us-lessac-medium", "en-gb-southern_english_female-low",
               "en-us-amy-low"),
}

# Where the extracted model lives. Deliberately outside the repo: it is ~120MB
# and it is a cache, not source.
CACHE = os.environ.get("PIPER_VOICE_DIR", "/tmp/piper-voices")

# Female markers in the edge-tts voice name, so this tier narrates in the same
# gender the episode was cast for rather than switching mid-catalogue.
_FEMALE = ("aria", "jenny", "michelle", "ana", "sonia", "libby", "maisie",
           "natasha", "freya", "emily", "molly", "clara", "isabella", "amy",
           "lessac", "female")


def gender_of(edge_voice):
    """Which gender the episode was cast for, read off the edge-tts name."""
    low = (edge_voice or "").lower()
    return "female" if any(m in low for m in _FEMALE) else "male"


def ensure_voice(asset, log=print):
    """Download and unpack one voice. Returns (onnx_path, config_path) or None.

    Cached: a second call in the same job costs nothing. The runner is
    ephemeral, so the first call each run pays the download.
    """
    os.makedirs(CACHE, exist_ok=True)
    onnx = os.path.join(CACHE, "%s.onnx" % asset)
    cfg = onnx + ".json"
    if os.path.exists(onnx) and os.path.exists(cfg):
        return onnx, cfg

    tgz = os.path.join(CACHE, "%s.tar.gz" % asset)
    url = "%s/voice-%s.tar.gz" % (_BASE, asset)
    try:
        log("  piper: fetching %s" % asset)
        urllib.request.urlretrieve(url, tgz)
        with tarfile.open(tgz) as tf:
            # Flatten: the archives carry a directory prefix that varies.
            for m in tf.getmembers():
                if m.name.endswith((".onnx", ".onnx.json")):
                    m.name = os.path.basename(m.name)
                    tf.extract(m, CACHE)
        os.remove(tgz)
    except Exception as e:
        log("  piper: could not fetch %s (%s)" % (asset, e))
        return None
    return (onnx, cfg) if os.path.exists(onnx) and os.path.exists(cfg) else None


# PACE IS NOT COSMETIC HERE -- IT DECIDES WHETHER THE ROUTE WORKS AT ALL.
#
# The audio gate scores duration by comparing the file against what this
# channel's word count SHOULD produce at CLINICAL_NARRATION_WPM, which is 100.
# Measured on en-us-ryan-high: Piper's own default runs at 248 wpm. Left
# alone, a 1,600-word script came out at 235 wpm -- a ratio of 0.42 against
# the expected length, which scores 1.0 out of 10 on duration and drags the
# total to 7.2 against an 8.5 gate. The voice would have sounded fine and the
# episode would have been rejected every single time, which is the most
# expensive kind of bug: a backup that looks wired up and cannot ever fire.
#
# The gate's bands are the thing to aim at, not the headline number: a ratio
# of 0.85 or better scores full marks, and 0.70 still scores 7.0 (which with
# Piper's tier clears the gate at 8.7). Full marks means landing at or under
# about 118 wpm.
#
# Getting there by stretching phonemes alone would need a length_scale near
# 2.5, which drawls. Real documentary narration is not slow words, it is
# normal words with room between the sentences. So this stretches moderately
# and buys the rest with pauses -- and it MEASURES what it got rather than
# trusting a constant, because a different voice model has a different
# natural pace and the same constant would be wrong for it.
FULL_MARKS_RATIO = 0.87     # inside the gate's >=0.85 band, with room to spare
TARGET_WPM = 115.0          # only a default; callers should pass the real one
_PAUSE_CAP = 1.8            # beyond this a gap reads as a dropout, not a beat
_STRETCH = (1.5, 1.75, 2.0, 2.25)


def target_for(gate_wpm):
    """The pace to narrate at, given the pace the gate measures against.

    Deliberately NOT the gate's own number. The gate divides the real duration
    by the duration `gate_wpm` implies and wants that ratio near 1.0, but its
    top band opens at 0.85 -- so aiming a little FASTER than the nominal pace
    lands inside the band with margin on both sides, where aiming exactly at it
    leaves a slow render one rounding error from dropping a whole band.
    """
    return float(gate_wpm) / FULL_MARKS_RATIO


def _sentences(script):
    import re
    parts = [s.strip() for s in re.split(r"(?<=[.!?])\s+", script) if s.strip()]
    return parts or [script]


def synthesize(script, out_path, edge_voice="en-GB-RyanNeural",
               target_wpm=TARGET_WPM, log=print, **kw):
    """Narrate `script` to `out_path` at roughly `target_wpm`. Path or None.

    Sentence by sentence, so the gaps between them are real editorial pauses
    rather than a uniform slowdown of everything.
    """
    try:
        import wave
        from piper import PiperVoice, SynthesisConfig
    except Exception as e:
        log("  piper: not installed (%s)" % e)
        return None

    sents = _sentences(script)
    words = len(script.split())
    want = words / max(1.0, target_wpm) * 60.0

    for asset in VOICES[gender_of(edge_voice)]:
        got = ensure_voice(asset, log=log)
        if not got:
            continue
        onnx, cfg = got
        try:
            voice = PiperVoice.load(onnx, config_path=cfg)
        except Exception as e:
            log("  piper: %s would not load (%s)" % (asset, e))
            continue

        work = os.path.join(CACHE, "seg")
        os.makedirs(work, exist_ok=True)
        for stretch in _STRETCH:
            paths, speech = [], 0.0
            try:
                for i, s in enumerate(sents):
                    p = os.path.join(work, "s%04d.wav" % i)
                    with wave.open(p, "wb") as fh:
                        voice.synthesize_wav(
                            s, fh,
                            syn_config=SynthesisConfig(length_scale=stretch))
                    with wave.open(p) as fh:
                        speech += fh.getnframes() / float(fh.getframerate())
                    paths.append(p)
            except Exception as e:
                log("  piper: %s failed mid-script (%s)" % (asset, e))
                break

            gaps = max(1, len(paths) - 1)
            pause = max(0.25, min(_PAUSE_CAP, (want - speech) / gaps))
            got_wpm = words / max(0.1, (speech + pause * gaps)) * 60.0
            log("  piper: %s stretch %.2f -> %.0f wpm with %.2fs pauses"
                % (asset, stretch, got_wpm, pause))
            # Too fast still means the stretch was not enough; try the next
            # one. Too slow cannot be fixed by stretching further, so take it.
            if got_wpm > target_wpm * 1.18 and stretch != _STRETCH[-1]:
                continue

            if _join(paths, pause, out_path, log=log):
                log("  piper: narrated with %s at ~%.0f wpm" % (asset, got_wpm))
                return str(out_path)
            break
    return None


def _join(parts, pause, out_path, log=print):
    """Concatenate the sentences with `pause` seconds of real silence between."""
    if not parts:
        return False
    lst = os.path.join(CACHE, "join.txt")
    sil = os.path.join(CACHE, "gap.wav")
    try:
        # The gap has to match the SPEECH's own sample rate, read off the first
        # segment rather than assumed. The voices are not all the same: ryan
        # and lessac are 22.05 kHz, others in the same release are 16 kHz, and
        # the concat demuxer will not splice streams whose rates disagree. A
        # constant here would have worked for the male voice and broken the
        # female one -- the kind of fault that only shows up on the day the
        # backup is actually needed.
        import wave as _w
        with _w.open(parts[0]) as _fh:
            rate = _fh.getframerate()
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                        "-i", "anullsrc=r=%d:cl=mono" % rate,
                        "-t", "%.3f" % pause, sil], check=True, timeout=120)
        with open(lst, "w") as fh:
            for i, p in enumerate(parts):
                fh.write("file '%s'\n" % p)
                if i != len(parts) - 1:
                    fh.write("file '%s'\n" % sil)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat",
                        "-safe", "0", "-i", lst, "-ar", "44100",
                        "-c:a", "libmp3lame" if not str(out_path).endswith(".wav")
                        else "pcm_s16le", str(out_path)],
                       check=True, timeout=1800)
        return (os.path.exists(out_path)
                and os.path.getsize(out_path) > 50000)
    except Exception as e:
        log("  piper: could not assemble the narration (%s)" % e)
        return False
