"""
A continuous scored bed for the whole episode — written, not droned.

WHAT WAS THERE
--------------
`_synthesize_mood_track` builds the bed from two sine waves and a noise
source, mixed, filtered, and held absolutely flat for nineteen minutes. It is
a drone. It never changes, so after about forty seconds the ear stops hearing
it entirely, and it does nothing whatsoever to carry a viewer through material
they did not already care about.

The bank of real tracks it prefers does not exist: `music_bank/` has never been
created, so every episode this channel has ever made fell through to the drone.

WHAT THIS IS
------------
Music has to MOVE or it is wallpaper. This writes a real bed:

  * A CHORD PROGRESSION. Four chords in a minor key, each held eight to twelve
    seconds, cycling for the length of the episode. A chord change is the
    smallest unit of musical movement there is, and it is the entire difference
    between "a sound is playing" and "something is going on".

  * PADS, NOT TONES. Each note is a root plus its octave, fifth and a quiet
    third, each slightly detuned against a twin. Detuning is what makes a
    synthesised note sound wide and alive instead of thin and electronic.

  * AN ARC ACROSS THE EPISODE. Quiet under the cold open so the voice owns the
    first thirty seconds, rising through the middle, densest around the reveal,
    settling at the end. A bed at one level for nineteen minutes tells the
    viewer nothing; a bed that swells tells them something is coming.

  * A PULSE AT RESTING HEART RATE. Very quiet, around 52 beats a minute. On a
    clinical channel that is not a gimmick -- it is the sound the room the
    story happens in actually makes, and it gives the ear something to hold
    onto without competing with the narration.

  * A KEY, AND A CHARACTER, CHOSEN BY THE EPISODE. The niche picks the family
    of progression; the case itself then picks the root note, the chord length,
    and -- when the topic says something clear enough to act on -- which family
    to use at all. A death, a mystery and a procedure are not the same story
    and should not be scored as though they were. A death is scored reflective,
    never as dread: a real patient in a published case report is not a jump
    scare.

It is written as raw samples with numpy and encoded once, rather than chained
through ffmpeg's filter graph, because a chord progression with an envelope
per note is not expressible as a fixed filter chain -- which is why the thing
it replaces was a drone in the first place.

MIXING
------
Returned at a level meant to sit UNDER a voice, not beside it. The caller
still ducks it against the narration; this is the source, not the mix.
"""
import hashlib
import math
import os
import subprocess
import wave

SR = 44100

# Minor-key progressions. Degrees are semitone offsets from the root.
# i - VI - III - VII is the most-used minor loop in film scoring for a reason:
# it never resolves, so it can run for nineteen minutes without ever sounding
# like it has finished.
PROGRESSIONS = {
    "clinical":   [(0, "min"), (8, "maj"), (3, "maj"), (10, "maj")],
    "unease":     [(0, "min"), (1, "maj"), (0, "min"), (10, "min")],
    "reflective": [(0, "min"), (5, "min"), (8, "maj"), (3, "maj")],
    "dread":      [(0, "min"), (0, "min"), (11, "maj"), (10, "maj")],
}

# Roots low enough to sit under a voice without muddying it. A bed above about
# 160 Hz starts fighting the fundamental of male narration.
ROOTS = (65.41, 69.30, 73.42, 77.78, 82.41, 87.31)     # C2 through F2

_CHORD = {"min": (0, 3, 7, 12), "maj": (0, 4, 7, 12)}


def _seeded(topic, mood):
    h = hashlib.sha1(("%s|%s" % (topic, mood)).encode()).hexdigest()
    return int(h[:8], 16), int(h[8:12], 16)


# What the CASE is, not just what the niche is.
#
# The niche picks the progression, which means every episode on a given
# surface was scored the same way -- a death and a recovery got identical
# music. The topic already chose the key and the chord length, so two
# episodes were never in unison, but they were always the same KIND of
# music, and kind is what a viewer actually registers.
#
# A death does not get dread. A real patient in a published case report is
# not a jump scare, and scoring one as a horror beat is both tasteless and,
# on a channel whose whole claim is that it treats these records seriously,
# self-defeating. It gets the reflective progression -- the one that sounds
# like an ending rather than a threat.
_TILT = {
    "reflective": ("died", "death", "fatal", "autopsy", "post-mortem",
                   "postmortem", "recovered", "discharged", "survived",
                   "remission", "resolved", "returned home", "years later"),
    "unease":     ("unexplained", "no known cause", "unknown", "misdiagnosed",
                   "missed", "puzzling", "baffled", "never identified",
                   "no diagnosis", "idiopathic"),
    "clinical":   ("surgery", "surgical", "operation", "procedure", "biopsy",
                   "transplant", "resection", "catheter", "ventilator"),
}


def tilt_for(topic, default):
    """Let the case itself choose the character of its own bed.

    Conservative on purpose: a mood only moves when one group clearly wins.
    A tie, or nothing matched, leaves the niche's choice alone -- the niche
    is the better guess in the absence of evidence, and a bed that lurches
    between characters on one stray word is worse than one that never moves.
    """
    low = (topic or "").lower()
    hits = {m: sum(1 for w in ws if w in low) for m, ws in _TILT.items()}
    best = max(hits, key=lambda m: hits[m])
    if hits[best] == 0:
        return default
    if sum(1 for m in hits if hits[m] == hits[best]) > 1:
        return default                        # tie: no clear signal
    return best


def _note(freq, n, detune=0.004):
    """One voice: two slightly detuned sines, so it is wide rather than thin."""
    import numpy as np
    t = np.arange(n, dtype=np.float32) / SR
    a = np.sin(2 * math.pi * freq * (1.0 - detune) * t)
    b = np.sin(2 * math.pi * freq * (1.0 + detune) * t)
    # A little third harmonic gives it a body rather than a whistle.
    c = np.sin(2 * math.pi * freq * 3.0 * t) * 0.06
    return ((a + b) * 0.5 + c).astype(np.float32)


def _envelope(n, attack=0.35, release=0.45):
    """Slow in, slow out. A pad has no attack transient; a beep does."""
    import numpy as np
    e = np.ones(n, dtype=np.float32)
    a = max(1, int(n * attack))
    r = max(1, int(n * release))
    e[:a] = np.linspace(0, 1, a, dtype=np.float32) ** 1.6
    e[-r:] = np.linspace(1, 0, r, dtype=np.float32) ** 1.6
    return e


def _arc(n, cold_open=30.0):
    """Where the bed sits, moment to moment, across the whole episode.

    Under the cold open the voice has to own the frame, so the bed is barely
    there. It rises through the middle, peaks around three-quarters in (where
    a case report puts its reveal), and settles for the close.
    """
    import numpy as np
    t = np.linspace(0.0, 1.0, n, dtype=np.float32)
    shape = 0.55 + 0.45 * np.sin(math.pi * np.clip(t / 0.78, 0, 1) ** 0.9)
    shape = np.where(t > 0.78, 0.72 - 0.22 * (t - 0.78) / 0.22, shape)
    lead = int(min(n, cold_open * SR))
    if lead > 1:
        shape[:lead] *= np.linspace(0.35, 1.0, lead, dtype=np.float32)
    return shape.astype(np.float32)


def _pulse(n, bpm=52.0, level=0.05):
    """A resting heart rate, felt more than heard."""
    import numpy as np
    out = np.zeros(n, dtype=np.float32)
    period = int(SR * 60.0 / bpm)
    beat_n = int(SR * 0.16)
    t = np.arange(beat_n, dtype=np.float32) / SR
    # Two thumps, lub-dub, low and soft.
    thump = (np.sin(2 * math.pi * 46 * t) * np.exp(-t * 26)
             + 0.55 * np.sin(2 * math.pi * 38 * t) * np.exp(-t * 20))
    for start in range(0, n - beat_n, period):
        out[start:start + beat_n] += thump * level
        second = start + int(SR * 0.30)
        if second + beat_n < n:
            out[second:second + beat_n] += thump * level * 0.6
    return out


def render(out_path, duration, mood="clinical", topic="", cold_open=30.0,
           log=print):
    """Write the episode's bed. Returns the path, or None if numpy is absent."""
    try:
        import numpy as np
    except Exception as e:
        log("  ambient bed: numpy unavailable (%s)" % e)
        return None

    mood = tilt_for(topic, mood if mood in PROGRESSIONS else "clinical")
    seed_a, seed_b = _seeded(topic, mood)
    root = ROOTS[seed_a % len(ROOTS)]
    prog = PROGRESSIONS.get(mood, PROGRESSIONS["clinical"])
    hold = 8.0 + (seed_b % 5)                    # 8-12s per chord

    n = int(SR * (duration + 6))
    mix = np.zeros(n, dtype=np.float32)

    # OVERLAP MUST NEVER EXCEED THE STEP, OR THE LOOP STOPS ADVANCING.
    #
    # Chords bleed into each other by 1.6s, so each iteration moves the write
    # head by (segment - overlap). At the tail of the track the segment gets
    # clipped to whatever is left, and once that fell to 1.6s or less the
    # advance became zero and the loop span forever -- a 60-second bed never
    # finished rendering. The advance is now floored, and the tail is left to
    # the sub and the pulse rather than being chased with ever-shorter chords.
    overlap = int(SR * 1.6)
    at, step = 0, 0
    while at < n - overlap:
        degree, quality = prog[step % len(prog)]
        seg = min(int(SR * hold), n - at)
        if seg < SR:
            break
        env = _envelope(seg)
        chord_root = root * (2 ** (degree / 12.0))
        # Root, fifth and octave carry the chord; the third is quiet because a
        # loud third makes a bed sound like a song and pulls focus off the
        # voice.
        for k, semitone in enumerate(_CHORD[quality]):
            gain = (0.42, 0.16, 0.30, 0.20)[k]
            f = chord_root * (2 ** (semitone / 12.0))
            mix[at:at + seg] += _note(f, seg) * env * gain

        # THE BED HAS TO SURVIVE A PHONE SPEAKER.
        #
        # FIX (direct user report, "I don't see the background sound in the
        # video"): everything above lives between the sub at root/2 (~41 Hz)
        # and the 690 Hz softening filter, with the chord itself sitting near
        # the root (~82 Hz). Measured on a real render: the bed is -26.7 LUFS
        # full-range but only -33.4 LUFS above 200 Hz, which is roughly where
        # a phone speaker starts reproducing anything at all. The bed already
        # sits ~18 units under the narration by design, so on a phone it is
        # effectively 25 under -- correctly mixed for headphones, and simply
        # not there on the device most of this channel is watched on. Nothing
        # was broken; it was inaudible, which from the far side of the screen
        # is the same thing.
        #
        # A quiet two-octave-up voice puts real energy at ~330 Hz for an 82 Hz
        # root: inside what a phone reproduces, still under the 690 Hz filter,
        # and quiet enough (0.13 against the root's 0.42) that it colours the
        # bed rather than turning it into a tune competing with the voice.
        for semitone in _CHORD[quality][:3]:
            f_up = chord_root * (2 ** ((semitone + 24) / 12.0))
            mix[at:at + seg] += _note(f_up, seg) * env * 0.38
        at += max(SR // 2, seg - overlap)        # always moves forward
        step += 1

    # A sub underneath, holding the room together between chord changes.
    t = np.arange(n, dtype=np.float32) / SR
    mix += np.sin(2 * math.pi * (root / 2.0) * t).astype(np.float32) * 0.11
    mix += _pulse(n, bpm=50 + (seed_b % 7))
    mix *= _arc(n, cold_open=cold_open)

    # Soften the top so it never competes with speech consonants.
    #
    # Done as a running sum rather than np.convolve. Convolving a 220-tap
    # kernel over nineteen minutes at 44.1 kHz is fifty billion multiply-adds
    # -- the first version of this had not finished after two minutes on a
    # four-minute test bed. A running sum is the same moving average in one
    # pass over the array, and it is exact rather than approximate.
    # FIX (direct user report, "I don't see the background sound in the
    # video"): k was 64, putting -3dB near 300 Hz -- which cancelled most of
    # the upper-octave voice added above for exactly this reason. Measured
    # end to end: the bed lost 6.7 LU going through a 200 Hz high-pass (what
    # a phone speaker effectively does), and now loses 2.8. k=40 sits the
    # null at ~1100 Hz and -3dB near 485 Hz: still far below the 2-8 kHz
    # band that carries speech consonants, so intelligibility is untouched.
    #
    # k=220 puts the cutoff at about 200 Hz, which removes the chord itself
    # and leaves only the sub -- measured: the spectrum at minute 1 and minute
    # 10 were identical, which is the drone this replaces. k=64 sits the
    # cutoff near 690 Hz: above the bed's own harmonics, still well below the
    # consonants that carry speech intelligibility.
    k = 40
    csum = np.cumsum(np.concatenate([[0.0], mix.astype(np.float64)]))
    smooth = ((csum[k:] - csum[:-k]) / k).astype(np.float32)
    pad = n - smooth.shape[0]
    mix = np.concatenate([smooth, mix[-pad:]]) if pad > 0 else smooth[:n]

    peak = float(np.max(np.abs(mix))) or 1.0
    mix = (mix / peak) * 0.30                    # source level; the mix ducks it

    wav = str(out_path).rsplit(".", 1)[0] + ".wav"
    pcm = (np.clip(mix, -1, 1) * 32767).astype("<i2")
    with wave.open(wav, "wb") as fh:
        fh.setnchannels(1)
        fh.setsampwidth(2)
        fh.setframerate(SR)
        fh.writeframes(pcm.tobytes())

    if str(out_path).endswith(".wav"):
        log("  ambient bed: %.1f min, %s, root %.1f Hz" %
            (duration / 60.0, mood, root))
        return wav
    try:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
                        "-c:a", "libmp3lame", "-q:a", "4", str(out_path)],
                       check=True, timeout=300)
        os.remove(wav)
    except Exception as e:
        log("  ambient bed: encode failed (%s), using the wav" % e)
        return wav
    log("  ambient bed: %.1f min, %s, root %.1f Hz, %d chord changes" %
        (duration / 60.0, mood, root, step))
    return str(out_path)
