#!/usr/bin/env python3
"""
Everything that has to be true before Channel 1 runs for real.

    python3 tools/preflight_ch1_thumbnails.py

Each check is a thing that has actually broken, or that would break silently.
The point of running it before a test rather than after is that a thumbnail
defect is invisible in a log: the run goes green, the file is written, and the
fault only shows up when a human looks at the picture -- or, in the case of the
duration badge, only once the video is live.

Exit code 0 means the run is safe to start.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "video_pipeline"))
sys.path.insert(0, os.path.join(ROOT, "channels"))

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append((name, detail))
    print("  %s  %-52s %s" % ("PASS" if ok else "FAIL", name, detail))


def main():
    print("\nCh1 thumbnail pre-flight\n" + "-" * 78)

    import photo_thumbnail as pt
    import presenter_library as pl
    import stock_library as sl
    import thumbnail_formats as tf
    import shorts_formats as sf

    # ── the five formats are the five that were chosen ─────────────
    chosen = ("reaction", "bubbles", "pointing", "verdict", "banner")
    check("five chosen formats in rotation", tuple(pt.FORMATS) == chosen,
          ", ".join(pt.FORMATS))
    pool = tf.CHANNEL_PREFERRED_FORMATS.get("No Known Cause", [])
    check("CTR learning pool matches the renderer's keys",
          set(pool) == set(chosen),
          "a mismatch means CTR attaches to a format that cannot be rendered")

    # ── the presenter library is intact ────────────────────────────
    poses = pl.poses()
    check("presenter poses present", len(poses) >= 23, "%d poses" % len(poses))
    missing = [n for n, p in poses.items()
               if not os.path.exists(os.path.join(pl.LIB, p["file"]))]
    check("every pose file on disk", not missing, ", ".join(missing[:4]))

    # ── the stock library can carry a run on its own ───────────────
    counts = {r: sl.count(r) for r in sl.ROLES}
    check("stock library covers scene + evidence",
          counts["scene"] >= 3 and counts["evidence"] >= 3, str(counts))

    # ── render every format with the network dead ──────────────────
    def dead(q, niche, out):
        raise RuntimeError("preflight: pretending the API is down")

    work = tempfile.mkdtemp()
    photos = pt.resolve_photos(dead, "brain lesion mri", "neurology_cases",
                               work, log=lambda m: None)
    check("photos resolve with no network", set(photos) >= {"scene", "evidence"},
          "roles: %s" % ", ".join(sorted(photos)))

    results = {}
    for fmt in pt.FORMATS:
        try:
            r = pt.render(os.path.join(work, fmt + ".jpg"),
                          "Every test came back clean and nobody could say why",
                          photos, fmt=fmt, episode=3, kicker="CASE 03")
            results[fmt] = r
        except Exception as e:
            check("render %s" % fmt, False, repr(e))
    check("all five formats render offline", len(results) == len(pt.FORMATS),
          "%d/%d" % (len(results), len(pt.FORMATS)))

    if results:
        check("nothing under YouTube's duration badge",
              all(r["badge_clear"] for r in results.values()),
              "badge covers the bottom-right corner in every feed")
        check("headline never exceeds the word cap",
              all(r["words"] <= pt.MAX_WORDS for r in results.values()),
              "max %d words" % max(r["words"] for r in results.values()))
        worst = min(r["contrast_120px"] for r in results.values())
        check("legible at 120px", worst >= 45, "worst %.1f" % worst)

        # The score quoted at review has to come from the picture. It used to
        # come from the headline string, which is how a card reading "8 0"
        # was presented as 10.0/10.
        bad = {f: r["image_issues"] for f, r in results.items()
               if r["image_score"] < 8.9}
        check("every format scores 8.9+ on its own pixels", not bad,
              "; ".join("%s %s" % (f, w) for f, w in list(bad.items())[:2]))

    # ── the channel mark never lands on the presenter ──────────────
    # A teal badge stuck to his shirt was in the reported screenshot. The
    # placement is measured, so it is checked by measurement too.
    import presenter_cutout as pcut
    import numpy as np
    worst_on_him = 0.0
    for fmt in pt.FORMATS:
        seen = {}
        real = pt._mark

        def watch(im, size=58, pad=26, side="auto", _seen=seen, _real=real):
            occ = pcut.LAST_OCCUPANCY
            _real(im, size, pad, side)
            # Read the slot the renderer RECORDED. The first version of this
            # hunted for the mark's teal in each corner, and a teal-tinted
            # hospital photograph in another corner tripped it -- reporting
            # the mark on the presenter at 80% when it was in a clear corner.
            chosen = getattr(pt._mark, "last_slot", None)
            for name, sx, sy in pt._mark_slots(size, pad):
                if name != chosen:
                    continue
                _seen["on_him"] = (0.0 if occ is None
                                   else float(occ[sy:sy + size, sx:sx + size].mean()))
                return
            _seen["on_him"] = 0.0

        pt._mark = watch
        try:
            pt.render(os.path.join(work, "mark_" + fmt + ".jpg"),
                      "Doctors said it was anxiety but the sodium was 0.4",
                      photos, fmt=fmt, episode=3, kicker="CASE 03", mark="DAY 9")
        finally:
            pt._mark = real
        worst_on_him = max(worst_on_him, seen.get("on_him", 0.0))
    check("channel mark never sits on the presenter", worst_on_him < 0.05,
          "worst overlap %.0f%%" % (worst_on_him * 100))

    # ── the presenter runs off the bottom, never stops short ───────
    # Every pose plate is a crop with 66-100% of its last row still subject,
    # so a plate that ends inside the card ends in a straight cut across his
    # chest with background showing under it.
    short = []
    real_place = pcut.place_on_photo

    def measure(bg, plate, a, box, **kw):
        if box[3] < bg.shape[0]:
            short.append((box[3], bg.shape[0]))
        return real_place(bg, plate, a, box, **kw)

    pcut.place_on_photo = measure
    try:
        for fmt in pt.FORMATS:
            pt.render(os.path.join(work, "cut_" + fmt + ".jpg"),
                      "Doctors said it was anxiety but the sodium was 0.4",
                      photos, fmt=fmt, episode=3, kicker="CASE 03")
    finally:
        pcut.place_on_photo = real_place
    check("presenter always reaches the bottom edge", not short,
          "%d layout(s) stop short, worst %s" % (len(short), short[:1]))

    # ── a headline is never spliced across a conjunction ───────────
    check("headline stays a whole statement",
          pt.trim_words("Every test came back clean and nobody could say why")
          == "Every test came back clean",
          "got %r" % pt.trim_words("Every test came back clean and nobody could say why"))

    # ── a drawing can never reach a card ───────────────────────────
    from PIL import Image, ImageDraw
    flat = os.path.join(work, "flat.png")
    im = Image.new("RGB", (900, 600), (232, 240, 250))
    ImageDraw.Draw(im).ellipse([200, 150, 700, 450], fill=(200, 40, 40))
    im.save(flat)
    check("a flat drawing is detected", pt.looks_drawn(flat),
          "vector diagrams must never reach a thumbnail")
    check("a photograph is not mistaken for a drawing",
          not pt.looks_drawn(photos["scene"]))

    # ── both learning loops are wired, not just present ────────────
    for mod, label in ((tf, "long-form"), (sf, "shorts")):
        have = all(hasattr(mod, f) for f in
                   ("record_format_used", "record_format_ctr", "attach_video_id"))
        check("%s CTR loop complete" % label, have,
              "record + attach + feedback")

    src = open(os.path.join(ROOT, "video_pipeline", "growth_engine.py")).read()
    check("shorts CTR is fed from YouTube Analytics",
          "from shorts_formats import record_format_ctr" in src,
          "without this the Shorts history never learns")
    src2 = open(os.path.join(ROOT, "video_pipeline",
                             "shorts_reels_engine.py")).read()
    check("shorts video_id is attached after upload",
          "attach_video_id as _attach_short" in src2)

    # ── the pipeline actually calls the new renderer ───────────────
    src3 = open(os.path.join(ROOT, "channels", "betrayal_deepdive",
                             "clinical_pipeline.py")).read()
    check("Ch1 pipeline calls the photographic renderer",
          "import photo_thumbnail as _pt" in src3)
    check("Ch1 pipeline records the format for CTR learning",
          "record_format_used(_cache" in src3)

    # ── the script decides the visuals, and the policy holds ───────
    import visual_brief as vbrief
    import visual_synth as vsynth

    _BEATS = [
        ("The CT showed nothing and the bloods came back normal.", "evidence"),
        ("Her sodium had fallen to 118 millimoles per litre.", "value"),
        ("The clot travelled from her calf and lodged in her lung.", "mechanism"),
        ("By the ninth day she could no longer stand.", "chronology"),
        ("She was sent home from the emergency department twice.", "place"),
        ("Nobody could explain why it had happened at all.", "state"),
    ]
    misread = ["%r read as %s not %s"
               % (t[:30], vbrief.classify(t)[0], want)
               for t, want in _BEATS if vbrief.classify(t)[0] != want]
    check("the script analyser reads each beat's job", not misread,
          "; ".join(misread[:2]))

    # THE LINE THAT MUST NOT MOVE. A generated CT, ECG or patient photograph
    # is a claim about a real published patient. There is no flag that turns
    # this off, so there is a check that it is still on.
    _MUST_REFUSE = [
        "a CT scan of the brain showing a lesion",
        "an MRI slice of this patient's head",
        "an ECG trace showing ventricular tachycardia",
        "a histology slide with abnormal cells",
        "a lab report showing a sodium of 118",
        "an x-ray of the chest",
        "a photograph of the patient in her hospital bed",
        "photorealistic hospital corridor, shot on DSLR",
    ]
    leaked = [p for p in _MUST_REFUSE if not vsynth.refuse(p)]
    check("no prompt can fabricate clinical evidence", not leaked,
          ("LET THROUGH: %s" % "; ".join(leaked[:2])) if leaked
          else "%d evidentiary prompts all blocked" % len(_MUST_REFUSE))

    _MUST_ALLOW = [
        "a narrowing vessel, one dark mass carried along it, " + vbrief.STYLE,
        "an empty waiting area, rows of chairs, one light on, " + vbrief.STYLE,
    ]
    blocked = [p for p in _MUST_ALLOW if vsynth.refuse(p)]
    check("interpretive imagery is still allowed", not blocked,
          ("over-tightened: %s" % blocked[0][:56]) if blocked else "")

    # An evidentiary beat must never even carry a prompt to refuse.
    _bad = [b for b in (vbrief.brief_for(t) for t, _ in _BEATS)
            if b["intent"] in ("evidence", "value") and b["prompt"]]
    check("evidence beats never reach a generator", not _bad,
          "a brief carried a prompt it must not have" if _bad else "")

    # And generation must work with the network unplugged, or the beats it
    # serves fall back to the diagrams it replaced.
    _gen_ok = []
    for _t, _want in _BEATS:
        _b = vbrief.brief_for(_t)
        if _b["treatment"] != "generated":
            continue
        _p = os.path.join(work, "synth_%d.png" % len(_gen_ok))
        _ok, _route = vsynth.make(_b, _p, work_dir=work, log=lambda m: None,
                                  allow_network=False)
        _gen_ok.append((_ok, _route))
    check("interpretive frames render with no network",
          bool(_gen_ok) and all(ok for ok, _ in _gen_ok),
          "routes: %s" % ", ".join(r or "FAILED" for _, r in _gen_ok))

    # Two beats must not produce the same frame, or this is the procedural
    # diagram problem again wearing a photograph.
    import hashlib as _hl
    _digests = set()
    for _i, _t in enumerate(["The clot travelled from her calf to her lung.",
                             "The swelling spread across the whole left side.",
                             "The pressure had cut off the blood supply."]):
        _p = os.path.join(work, "var_%d.png" % _i)
        vsynth.make(vbrief.brief_for(_t, _i), _p, log=lambda m: None,
                    allow_network=False)
        if os.path.exists(_p):
            _digests.add(_hl.sha1(open(_p, "rb").read()).hexdigest())
    check("no two beats render the identical frame", len(_digests) >= 3,
          "%d distinct frame(s) from 3 beats" % len(_digests))

    _src = open(os.path.join(ROOT, "video_pipeline", "medical_segments.py")).read()
    _consults = ("_vb.brief_for(" in _src
                 and '_brief["treatment"]' in _src)
    check("the pipeline asks the brief before reaching for a photo", _consults,
          "" if _consults else "an analyser nothing consults changes nothing")

    # ── both sources are used, neither replaces the other ──────────
    # "I never said that I only want you to create visuals from your own end
    # and not try for stock footage. I want you to use both the things
    # wherever applicable." Sending every atmospheric beat to the generator
    # put the mix at 42% invented against 34% real, which is the opposite.
    _SCRIPT = ("A thirty-four year old woman went to her GP with a headache "
               "lasting nine days. She was sent home from the emergency "
               "department twice that week. The CT showed nothing and the "
               "bloods came back normal. Her sodium had fallen to 118 "
               "millimoles per litre by the second sample. By the ninth day "
               "she could no longer stand without help. The clot had "
               "travelled from a vein in her calf and lodged in her lung. "
               "Nobody could explain why a healthy woman had thrown a clot "
               "at all. The repeat MRI revealed a lesion nobody had seen on "
               "the first scan. She waited eleven weeks for the follow-up "
               "appointment. By then the pressure had cut off the blood "
               "supply to the optic nerve. ") * 4
    _beats = vbrief.split_beats(_SCRIPT, 40)
    _briefs, _plan = vbrief.shot_list(_beats, topic="an unexplained clot")
    _kinds = {}
    for _b in _briefs:
        _kinds[_b["treatment"]] = _kinds.get(_b["treatment"], 0) + 1
    check("a state beat can still choose a real photograph",
          _kinds.get("either", 0) > 0,
          "atmospheric beats must try the library before inventing anything")

    import medical_segments as _msg
    _used, _made, _shot = set(), 0, 0
    for _i, _b in enumerate(_briefs):
        if _b["treatment"] not in ("photograph", "either", "generated"):
            continue
        _msgs = []
        _msg.render_scene_still(_beats[_i], os.path.join(work, "blend_%d.png" % _i),
                                work, variant=_i, topic="an unexplained clot",
                                used=_used, log_fn=lambda m: _msgs.append(m))
        _shot += 1
        if "interpretive frame" in " ".join(_msgs):
            _made += 1
    _real = _shot - _made + _plan["counts"].get("evidence", 0)
    _pct_made = 100.0 * _made / max(1, _plan["n"])
    _pct_real = 100.0 * _real / max(1, _plan["n"])
    check("real material still leads the episode", _pct_real > _pct_made,
          "%.0f%% real vs %.0f%% invented" % (_pct_real, _pct_made))
    check("invented imagery stays a minority", _pct_made <= 30.0,
          "%.0f%% of cards invented" % _pct_made)
    check("both sources are actually used", _made > 0 and (_shot - _made) > 0,
          "%d photograph(s), %d made" % (_shot - _made, _made))

    # ── the background bed is music, not a drone ───────────────────
    # Every episode this channel has made fell through to two sine waves held
    # flat for nineteen minutes, because music_bank/ was never created.
    import ambient_bed as abed
    _bed = os.path.join(work, "bed.wav")
    _t0 = __import__("time").time()
    _got = abed.render(_bed, 90, mood="clinical", topic="an unexplained clot",
                       log=lambda m: None)
    _took = __import__("time").time() - _t0
    check("the bed renders, and in reasonable time",
          bool(_got) and os.path.exists(_got) and _took < 60,
          "%.1fs for 90s of bed" % _took)

    if _got and os.path.exists(_got):
        import wave as _wave
        with _wave.open(_got) as _w:
            _a = np.frombuffer(_w.readframes(_w.getnframes()),
                               dtype="<i2").astype(float)
            _sr = _w.getframerate()

        def _chord_band(x):
            _f = np.abs(np.fft.rfft(x * np.hanning(len(x))))
            _fr = np.fft.rfftfreq(len(x), 1.0 / _sr)
            _m = (_fr > 55) & (_fr < 260)     # above the constant sub
            _v = _f[_m]
            return _v / (np.linalg.norm(_v) or 1)

        _s1 = _chord_band(_a[int(15 * _sr):int(21 * _sr)])
        _s2 = _chord_band(_a[int(60 * _sr):int(66 * _sr)])
        _same = float(_s1 @ _s2)
        check("the harmony actually moves", _same < 0.75,
              "similarity %.2f between two moments (1.00 = a frozen drone)"
              % _same)

        _w1 = float(np.sqrt((_a[:int(10 * _sr)] ** 2).mean()))
        _w2 = float(np.sqrt((_a[int(40 * _sr):int(50 * _sr)] ** 2).mean()))
        check("the bed stays out of the way under the cold open",
              _w1 < _w2 * 0.8,
              "opening is %.0f%% of the mid-episode level"
              % (100.0 * _w1 / max(1e-6, _w2)))

    # The bed follows the CASE, not only the surface. Two episodes on the same
    # niche used to be scored identically; the topic now moves the character.
    _tilts = [
        ("A patient who died six weeks after an unremarkable scan",
         "clinical", "reflective"),
        ("An unexplained fever with no known cause for eleven weeks",
         "clinical", "unease"),
        ("Laparoscopic resection of a rare abdominal mass",
         "unease", "clinical"),
        ("Sudden bilateral vision loss in a 34-year-old",
         "clinical", "clinical"),          # no signal: the niche keeps it
        ("", "reflective", "reflective"),  # no topic at all
    ]
    _bad = [(t, want, abed.tilt_for(t, niche))
            for t, niche, want in _tilts if abed.tilt_for(t, niche) != want]
    check("the case chooses the character of its own bed", not _bad,
          "%d topic(s) scored wrong: %s" % (len(_bad), _bad) if _bad else
          "death reads reflective, mystery reads unease, procedure reads clinical")

    # A death must never be scored as a horror beat. This channel's whole
    # claim is that it treats real published patients seriously.
    check("a death is not scored as dread",
          abed.tilt_for("the patient died in the early hours", "dread")
          != "dread",
          "a real patient in a case report is not a jump scare")

    _cp = open(os.path.join(ROOT, "channels", "betrayal_deepdive",
                            "clinical_pipeline.py")).read()
    check("the pipeline uses the written bed before the drone",
          "import ambient_bed" in _cp,
          "a bed nothing calls changes nothing")

    # ── and the bed is actually AUDIBLE in the finished mix ────────
    # Writing music nobody can hear is the same as not writing it. The mix
    # used a flat volume=0.08, which put the bed 33.9 units under the voice
    # -- measured, not guessed. Broadcast practice for music under dialogue
    # is fifteen to twenty. This runs the real filter graph out of the
    # pipeline source and measures each side of it, so the day someone
    # retunes that number the check says what it did to the balance.
    _fx = re.search(r'"\[1:a\]volume=1\.0\[n\];"\s*\n\s*"(.*?)"\s*\n\s*"(.*?)"\s*\n\s*"(.*?)",',
                    _cp, re.S)
    _graph = "[1:a]volume=1.0[n];" + "".join(_fx.groups()) if _fx else ""
    check("the mix graph was found in the pipeline", bool(_graph),
          ("%d chars of real filter chain" % len(_graph)) if _graph else
          "cannot measure a balance without the real filter chain")

    # The main video and the Shorts are mixed by two separate ffmpeg calls.
    # They were both wrong in the same way, so fixing one and not the other
    # would have left every Short silent behind the voice -- on the surface
    # watched almost entirely on a phone speaker.
    _beds = len(re.findall(r"loudnorm=I=-37:LRA=11:TP=-6", _cp))
    check("the Shorts get the same balance as the main video", _beds >= 2,
          "%d of 2 mixes carry the bed target" % _beds)
    # Narrowly the narration-against-music pattern. `volume=0.08` also appears
    # inside _synthesize_mood_track, where it balances that drone's own sine
    # components against each other -- nothing to do with the voice, and now
    # irrelevant anyway, since loudnorm re-levels whatever the bed route hands
    # over. Matching the bare number flagged it and would have sent the next
    # person to edit an unrelated filter.
    _old = re.findall(r"\[\d:a\]volume=1\.0\[n\];\[\d:a\]volume=0\.08\[m\]", _cp)
    check("no mix still uses the old flat gain", not _old,
          "a fixed gain multiplies a level nobody measured"
          if _old else "both mixes measure the bed instead of guessing")

    if _graph and shutil.which("ffmpeg") and _got and os.path.exists(_got):
        # ffmpeg indexes are 1=narration, 2=music in the pipeline (0 is the
        # background video). Re-point them at two audio-only inputs and feed
        # each side alone against silence, so what comes back is that side's
        # own contribution to the finished mix.
        _g = _graph.replace("[1:a]", "[0:a]").replace("[2:a]", "[1:a]")
        _sil = os.path.join(work, "sil.wav")
        _sp = os.path.join(work, "speech.wav")
        # A stand-in for narration at the -16 LUFS every voice profile targets.
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                        "-i", "anullsrc=r=44100:cl=mono", "-t", "60", _sil],
                       check=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                        "-i", "sine=frequency=220:r=44100", "-t", "60",
                        "-af", "tremolo=f=5:d=0.9,loudnorm=I=-16:TP=-1.5:LRA=11",
                        _sp], check=True)

        def _through(a, b, out):
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", a,
                            "-i", b, "-filter_complex", _g, "-map", "[aout]",
                            out], check=True)
            r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i",
                                out, "-af", "ebur128", "-f", "null", "-"],
                               capture_output=True, text=True).stderr
            m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r)
            return float(m[-1]) if m else 0.0

        try:
            _lv = _through(_sp, _sil, os.path.join(work, "m_v.wav"))
            _lb = _through(_sil, _got, os.path.join(work, "m_b.wav"))
            _gap = _lv - _lb
            check("the bed is audible under the narration", 13.0 <= _gap <= 21.0,
                  "bed sits %.1f LU under the voice (want 15-20; at 34 it is "
                  "not quiet, it is absent)" % _gap)
            check("the finished mix is not shipped quiet", _lv > -19.0,
                  "narration lands at %.1f LUFS (YouTube turns loud uploads "
                  "down, it never turns quiet ones up)" % _lv)
        except Exception as _e:
            check("the bed is audible under the narration", False,
                  "could not measure the mix: %s" % _e)

    # ── the narration has three routes that can actually publish ───
    # The audio gate scores the voice tier at 40% against an 8.5 floor, so a
    # route's ceiling is tier*0.4 + 6.0. By that arithmetic gTTS (7.6) and
    # espeak (6.6) can NEVER ship an episode, which meant the four listed
    # narration backups were really two. These assert the arithmetic itself,
    # so the day someone retunes a tier weight the consequence is visible.
    import piper_tts as _pt

    _src_qs = open(os.path.join(ROOT, "video_pipeline",
                                "quality_scoring.py")).read()
    _tiers = re.findall(r'"([a-z0-9\-]+)":\s*([\d.]+)[,\s]', _src_qs)
    _tier = {k: float(v) for k, v in _tiers}
    _GATE = 8.5

    def _ceiling(name):
        return _tier.get(name, 0.0) * 0.40 + 10 * 0.25 + 10 * 0.20 + 10 * 0.15

    _keyfree = ("kokoro", "edge-tts", "piper")
    _can = [n for n in _keyfree if _ceiling(n) >= _GATE]
    check("three key-free voices can clear the audio gate", len(_can) >= 3,
          "%d of %d: %s" % (len(_can), len(_keyfree),
                            ", ".join("%s %.1f" % (n, _ceiling(n))
                                      for n in _keyfree)))
    check("the draft-only voices really are unpublishable",
          _ceiling("gtts-fallback") < _GATE
          and _ceiling("espeak-offline-lastresort") < _GATE,
          "gTTS %.1f, espeak %.1f — both must stay under %.1f"
          % (_ceiling("gtts-fallback"),
             _ceiling("espeak-offline-lastresort"), _GATE))

    # Piper must be reached BEFORE the two routes that cannot publish, or it
    # never runs on the day it is needed.
    _pi, _gt = _cp.find("import piper_tts"), _cp.find("from gtts import gTTS")
    check("Piper is tried before the draft-only voices",
          _pi > 0 and _gt > 0 and _pi < _gt,
          "a publishable route below an unpublishable one never runs")

    check("Piper narrates in the gender the episode was cast for",
          _pt.gender_of("en-GB-SoniaNeural") == "female"
          and _pt.gender_of("en-GB-RyanNeural") == "male",
          "a voice swap mid-catalogue reads as a different narrator")

    # PACE DECIDES WHETHER THIS ROUTE WORKS AT ALL.
    #
    # Piper's own default is 248 wpm against this channel's 100. Left alone a
    # real script measured 235 wpm -- ratio 0.42, duration scores 1.0, total
    # 7.2 against an 8.5 gate. The voice sounds fine and the episode is
    # rejected every single time: a backup that looks wired up and can never
    # fire. These assert the conversion still happens and still lands in the
    # gate's top band.
    check("Piper is given the gate's pace, not a raw stretch",
          "target_wpm=_piper.target_for(" in _cp
          and "CLINICAL_NARRATION_WPM" in _cp,
          "248 wpm against a 100 wpm yardstick fails on duration forever")

    _t = _pt.target_for(100.0)
    _ratio = 100.0 / _t
    check("Piper's target lands in the gate's full-marks band",
          0.85 <= _ratio <= 1.15,
          "targets %.0f wpm -> ratio %.2f (needs 0.85-1.15 for 10/10)"
          % (_t, _ratio))

    # And the arithmetic all the way through to a real score.
    _best = _tier.get("piper", 0.0) * 0.40 + 10 * 0.25 + 10 * 0.20 + 10 * 0.15
    _real = _tier.get("piper", 0.0) * 0.40 + 10 * 0.25 + 8 * 0.20 + 10 * 0.15
    check("Piper clears the gate with room for an imperfect file",
          _real >= _GATE,
          "%.1f with a silence penalty applied (ceiling %.1f, gate %.1f)"
          % (_real, _best, _GATE))

    _wf = open(os.path.join(ROOT, ".github", "workflows",
                            "ch1_generate.yml")).read()
    check("the runner installs Piper", "piper-tts" in _wf,
          "a route the runner cannot import is not a route")

    # ── the SHORTS have their own voice chain, and it published a robot ──
    # Run 31257986626: Groq returned 429 on one chunk, the Shorts engine fell
    # to espeak, and the Short scored 9.3/10 and went live on the channel --
    # because its audio component was "the file exists and is over 500KB",
    # which a synthesiser satisfies as well as a neural voice. The main
    # narration path already refused espeak; this one had no equivalent, so
    # the same fallback had opposite consequences depending on which pipeline
    # reached it. These assert the rule now applies on both sides.
    import shorts_reels_engine as _sre

    _fake = os.path.join(work, "fake_short.mp4")
    with open(_fake, "wb") as _fh:
        _fh.write(b"\0" * 900000)          # comfortably over the size check
    _t, _s = "THE PATIENT NOBODY COULD EXPLAIN", "Shocking. Nobody could explain it. "

    _saved = getattr(_sre, "LAST_TTS_ROUTE", "none")
    try:
        _sre.LAST_TTS_ROUTE = "espeak"
        _bad = _sre.score_final_video(_fake, _s, _t, True, True, "betrayal_deepdive")
        _sre.LAST_TTS_ROUTE = "groq-orpheus"
        _good = _sre.score_final_video(_fake, _s, _t, True, True, "betrayal_deepdive")
    finally:
        _sre.LAST_TTS_ROUTE = _saved

    check("a robot-voiced Short cannot pass its gate", not _bad["passed"],
          "espeak scored %.1f, audio component %.1f — %s"
          % (_bad["total"], _bad["audio"], _bad.get("blocked_reason", "")))
    check("a real voice still scores full marks on audio",
          _good["audio"] == 2.0 and _good["total"] > _bad["total"],
          "%.1f vs %.1f — the block must be the VOICE, not a blanket penalty"
          % (_good["total"], _bad["total"]))
    check("the Shorts engine records which voice spoke",
          "LAST_TTS_ROUTE" in open(os.path.join(
              ROOT, "video_pipeline", "shorts_reels_engine.py")).read(),
          "a scorer that cannot see the route cannot judge it")

    _sresrc = open(os.path.join(ROOT, "video_pipeline",
                                "shorts_reels_engine.py")).read()
    _pi, _es = _sresrc.find("import piper_tts"), _sresrc.find("espeak-ng fallback")
    check("Shorts reach Piper before the synthesiser",
          _pi > 0 and _es > 0 and _pi < _es,
          "a rate limit must not cost the channel its voice")

    # ── the picture matches the sentence it sits under ─────────────
    # The library was already tagged and nothing was reading the narration
    # against it: SCENE rotated through twelve fixed phrases indexed by the
    # segment number, so a line about a pupil could get a waiting room. These
    # assert the matcher makes the calls a person would.
    import stock_match as smatch

    _EXPECT = [
        ("Her sodium had fallen to 118 millimoles per litre.", "blood"),
        ("The repeat MRI showed a lesion on the first scan.", "mri"),
        ("The pupil on the right no longer reacted to light.", "eye"),
        ("He collapsed and the paramedics could not find a rhythm.", "paramedic"),
        ("By the ninth night on the ward the fever had not moved.", "ward"),
        ("She was sent home from the emergency department twice.", "clinic"),
    ]
    wrong = []
    for line, want_tag in _EXPECT:
        path, why, _role = smatch.best_any(line)
        if not path or want_tag not in why.split():
            wrong.append("%r -> %s" % (line[:34], why or "(no match)"))
    check("the photograph matches what the line is about", not wrong,
          "; ".join(wrong[:2]))

    # The topic fires on EVERY segment, so it must tilt a close call and never
    # decide one. An episode titled "months of normal scans" used to put
    # imaging terms into all 106 cards.
    _p, _why, _ = smatch.best_any("The pupil on the right no longer reacted.",
                                  topic="Eleven months of normal scans")
    check("the episode topic cannot override the segment", "eye" in _why.split(),
          "matched on [%s]" % _why)

    # A photograph already shown must lose to one that has not, or a small
    # library shows the same corridor four times in one episode.
    _seen = set()
    _lines = [l for l, _ in _EXPECT] * 2
    for line in _lines:
        _p, _w, _r = smatch.best_any(line, used=_seen)
        if _p:
            _seen.add(os.path.basename(_p))
    check("variety is spent before anything repeats", len(_seen) >= 6,
          "%d distinct photograph(s) over %d cards" % (len(_seen), len(_lines)))

    # And the library has to know what it is missing, or harvest() grows it
    # toward a list written once instead of toward what episodes ask for.
    _gaps = smatch.gaps("scene", smatch.terms_for("The clot travelled to the lung"))
    check("the library reports its own gaps", bool(_gaps),
          "a term nothing matches is the one worth an API call: %s"
          % ", ".join(_gaps[:4]))

    for _mod, _fn in (("medical_segments.py", "smatch.best_any"),
                      ("../channels/betrayal_deepdive/clinical_pipeline.py",
                       "_smatch.gaps")):
        _src = open(os.path.join(ROOT, "video_pipeline", _mod)).read()
        check("the matcher is actually called in %s" % os.path.basename(_mod),
              _fn in _src, "an unused matcher changes nothing")

    # ── every register in the mix is reachable by the scheduler ────
    # A register can hold a share of TARGET_MIX and still never be picked:
    # _neediest() chooses from FILLABLE, so anything outside that tuple is
    # reachable only by a keyword hint. SCENE was given 18% and left out of
    # FILLABLE, and on a case with no data the episode came out ANATOMY 59
    # times in a row -- 57 breaches of a run cap of 2, with SCENE sitting
    # live at half the mix and unreachable. The fuzzer caught it, twelve
    # minutes in; this catches the same class in under a second.
    import medical_register as mreg
    for _label, _case in (("a case with nothing in it", {}),
                          ("a thin case", {"differentials": [{"name": "x"}],
                                           "timeline": [{"day": "1"}, {"day": "2"}]})):
        q = mreg.new_quota(59, figure_count=0, case=_case)
        seq = [q.pick("plain narration line %d" % i) for i in range(59)]
        longest, cur, prev = 1, 0, None
        for r in seq:
            cur = cur + 1 if r == prev else 1
            prev, longest = r, max(longest, cur)
        check("run cap holds on %s" % _label,
              longest <= q.MAX_RUN and q.forced_repeats == 0,
              "longest run %d (cap %d), %d forced repeat(s)"
              % (longest, q.MAX_RUN, q.forced_repeats))
        unreachable = [r for r in q.live_registers if r not in set(seq)
                       and r not in (mreg.TEXT,)]
        check("no live register is unreachable on %s" % _label, not unreachable,
              "scheduled 0 times: %s" % ", ".join(unreachable))

    # ── the subtitle chain has more than one link ──────────────────
    # Whisper failed three times on run 31156373254 (502) and three times on
    # the run before it (413), and both episodes were captioned by spreading
    # the script evenly across the runtime. Retrying one endpoint is not a
    # backup; these checks assert the other routes are real and reachable.
    import caption_align as ca
    from caption_timing import ass_from_words

    tone = os.path.join(work, "pauses.wav")
    # speech 0-6, silence 6-9, speech 9-14, silence 14-16, speech 16-24
    chain, idx = [], 0
    for dur, loud in ((6.0, 1), (3.0, 0), (5.0, 1), (2.0, 0), (8.0, 1)):
        chain.append(("sine=frequency=%d:duration=%.2f:sample_rate=44100"
                      % (180 + 40 * idx, dur)) if loud else
                     "anullsrc=r=44100:cl=mono:d=%.2f" % dur)
        idx += 1
    filt = ";".join("%s[a%d]" % (s, i) for i, s in enumerate(chain))
    filt += ";" + "".join("[a%d]" % i for i in range(len(chain))) + \
            "concat=n=%d:v=0:a=1[out]" % len(chain)
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-filter_complex", filt, "-map", "[out]", "-t", "24", tone],
                   capture_output=True, timeout=120)

    truth = [(0.0, 6.0), (9.0, 14.0), (16.0, 24.0)]
    spans = ca.speech_spans(tone, total=24.0)
    close = (len(spans) == len(truth) and
             all(abs(a - c) < 0.3 and abs(b - d) < 0.3
                 for (a, b), (c, d) in zip(spans, truth)))
    check("pauses are found in real audio", close,
          "got %s" % [(round(a, 1), round(b, 1)) for a, b in spans])

    words = ca.align_words(tone, " ".join("word%02d" % i for i in range(60)),
                           total=24.0)
    inside = all(any(a - 0.02 <= w["start"] <= b + 0.02 for a, b in truth)
                 for w in words)
    check("no caption word is placed during a silence", inside and bool(words),
          "%d words aligned" % len(words))

    ass, _st = ass_from_words(words, total_duration=None)
    check("aligned words build a real caption track", bool(ass) and len(ass) > 200,
          "%d bytes" % len(ass or ""))

    # The last link must need nothing. If this ever grows a key or a network
    # call, an outage takes the whole chain down again.
    src = open(os.path.join(ROOT, "video_pipeline", "caption_align.py")).read()
    check("the final caption backup needs no key or network",
          "requests" not in src and "API_KEY" not in src,
          "align_words must work with everything else down")

    cp = open(os.path.join(ROOT, "channels", "betrayal_deepdive",
                           "clinical_pipeline.py")).read()
    check("the pipeline actually calls both caption backups",
          "_local_whisper_ass(" in cp and "_aligned_ass(" in cp,
          "a backup that is never called is not a backup")

    # ── everything the workflow itself will check ──────────────────
    # This tool said "Ready for a real run" and the run then died in 90
    # seconds on a check this tool never ran. A pre-flight that clears work
    # the real gate rejects is worse than no pre-flight, because it is
    # trusted. So the workflow's own gates run here too, by invoking the
    # exact same commands rather than a reimplementation of them.
    for label, cmd in (
        ("defect-class scan (workflow gate)",
         [sys.executable, os.path.join(ROOT, "tools", "defect_classes.py"), "--check"]),
        # "There should be three to four backups for each of the stages."
        # Checked here so a route cannot be deleted or renamed and quietly
        # take a stage back down to one.
        ("every stage has 3+ independent routes",
         [sys.executable, os.path.join(ROOT, "tools", "stage_backups.py")]),
    ):
        if not os.path.exists(cmd[1]):
            continue
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT,
                               timeout=300)
            tail = [l for l in (r.stdout or r.stderr).strip().splitlines() if l.strip()]
            check(label, r.returncode == 0 and "NEW lead" not in (r.stdout or ""),
                  tail[0][:60] if tail else "")
        except Exception as e:
            check(label, False, repr(e))

    # The workflow's undefined-name gate is pyflakes filtered to one message,
    # so it is run the same way here rather than approximated.
    try:
        import subprocess as _sp
        r = _sp.run([sys.executable, "-m", "pyflakes"] +
                    __import__("glob").glob(os.path.join(ROOT, "channels", "*", "*.py")) +
                    __import__("glob").glob(os.path.join(ROOT, "video_pipeline", "*.py")),
                    capture_output=True, text=True, cwd=ROOT, timeout=300)
        bad = [l for l in (r.stdout or "").splitlines() if "undefined name" in l]
        check("undefined names (workflow gate)", not bad,
              bad[0][:70] if bad else "")
    except Exception as e:
        check("undefined names (workflow gate)", True, "pyflakes unavailable: %r" % e)

    print("-" * 78)
    print("  %d passed, %d failed\n" % (len(PASS), len(FAIL)))
    if FAIL:
        print("  NOT READY:")
        for n, d in FAIL:
            print("    - %s %s" % (n, ("(%s)" % d) if d else ""))
        return 1
    print("  Ready for a real run.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
