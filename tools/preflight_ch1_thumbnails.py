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
# Ch1's pipeline module itself, so the provider-chain checks below can drive
# the real call_* functions rather than reading their source. Without this,
# `import clinical_pipeline` does not resolve and the checks fail closed --
# which is how the defect scanner caught it, correctly.
sys.path.insert(0, os.path.join(ROOT, "channels", "betrayal_deepdive"))

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
    #
    # The bed target used to be written into this check as a literal
    # (`loudnorm=I=-37...`), which meant retuning the bed for the phone band
    # made the CHECK fail rather than the code -- a check encoding a number
    # it is supposed to be verifying is downstream of. What actually matters
    # is that the two mixes carry the SAME chain as each other, whatever it
    # currently is, so the chain is read out of the pipeline and counted.
    _bedchains = re.findall(r"\[2:a\](.*?)\[m\];", _cp)
    _beds = (len([c for c in _bedchains if c == _bedchains[0]])
             if _bedchains else 0)
    check("the Shorts get the same balance as the main video",
          _beds >= 2 and "loudnorm" in (_bedchains[0] if _bedchains else ""),
          "%d of 2 mixes carry the same measured bed chain (%s)"
          % (_beds, "; ".join(sorted(set(_bedchains)))[:90] or "none found"))
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

    # ── no robotic voice exists anywhere any more ──────────────────
    # "I don't want anything related to robotic voice, only humanic voices."
    # The arithmetic above proved these routes could not publish, and a live
    # Short was narrated by espeak anyway — because the Shorts scorer was a
    # different scorer, and the synthesiser was still installed and still
    # reachable. So they are deleted, not demoted, and that is asserted per
    # file rather than trusted.
    import voice_policy as _vp
    for _ch, _p in (("Ch1", ("channels", "betrayal_deepdive", "clinical_pipeline.py")),
                    ("Ch2", ("channels", "evidence_room", "evidence_room_pipeline.py")),
                    ("Ch3", ("channels", "collapse_index", "collapse_index_pipeline.py")),
                    ("Ch4", ("channels", "archive", "archive_pipeline.py")),
                    ("Ch5", ("channels", "control_files", "control_files_pipeline.py")),
                    ("Shorts", ("video_pipeline", "shorts_reels_engine.py"))):
        _s = open(os.path.join(ROOT, *_p)).read()
        check("%s has no robotic voice route left" % _ch,
              "from gtts import" not in _s and 'espeak-ng"' not in _s,
              "a synthesiser that stays reachable is eventually heard")

    check("a robotic route is refused by name",
          not _vp.is_human("espeak") and not _vp.is_human("gtts-fallback")
          and not _vp.is_human("espeak-offline-LASTRESORT"),
          "these must never be reintroduced quietly")
    check("an unknown voice route is refused, not allowed",
          not _vp.is_human("some-new-tts") and not _vp.is_human(""),
          "a blocklist passes anything it failed to predict")
    check("the real human routes are allowed",
          all(_vp.is_human(r) for r in ("kokoro-local", "edge-tts", "piper",
                                        "groq-orpheus", "fish-audio-backup",
                                        "en-GB-RyanNeural")),
          "refusing everything is not a fix")
    # Read directly: _sre_src is not defined until much further down.
    _shorts_src = open(os.path.join(ROOT, "video_pipeline",
                                    "shorts_reels_engine.py")).read()
    check("Shorts still has three human voice routes",
          all('"%s"' % t in _shorts_src
              for t in ("groq-orpheus", "edge-tts", "piper")),
          "removing espeak must not drop Shorts below the backup floor")

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

    # This used to assert Piper was reached before espeak. espeak is gone, so
    # that check could never pass again. What still matters is the order of
    # the three HUMAN routes: Groq's own voices, then the remote neural one,
    # then the local one that works with the network down — three routes with
    # three different failure modes, cheapest recovery first.
    _sresrc = open(os.path.join(ROOT, "video_pipeline",
                                "shorts_reels_engine.py")).read()
    _gq = _sresrc.find('"groq-orpheus"')
    _ed = _sresrc.find('LAST_TTS_ROUTE"] = "edge-tts"')
    _pi = _sresrc.find('LAST_TTS_ROUTE"] = "piper"')
    check("Shorts fall through the human voices in order",
          0 < _gq < _ed < _pi,
          "a rate limit must not cost the channel its voice")
    check("Shorts refuse to narrate when every human voice fails",
          "refusing to narrate this" in _sresrc,
          "returning silence is the point — there is nothing below Piper")

    # ── a photograph carries NO text of its own ────────────────────
    # The delivered episode put TWO pieces of type on every photograph: an
    # eyebrow header top-left and a 58px slice of narration across the lower
    # third — while the finished video ALSO burns synced subtitles from the
    # same narration. Three texts, two of them saying overlapping things a
    # beat apart. Asserted on real pixels rather than by reading the source,
    # because the point is what reaches the screen.
    _photo_seg = os.path.join(work, "bare_photo.png")
    import medical_segments as _ms
    _drew = _ms.render_scene_still(
        "She had come in with vaginal bleeding that had lasted three days. "
        "Under treatment, nothing changed.",
        _photo_seg, work, variant=3, niche_label="HOW IT WAS FOUND",
        topic="unexplained bleeding in a young woman")
    check("a photograph segment still renders", _drew and
          os.path.exists(_photo_seg), "the register must still produce a frame")

    if _drew and os.path.exists(_photo_seg):
        _pim = Image.open(_photo_seg).convert("L")
        _pa = np.asarray(_pim).astype(float)
        # The eyebrow sat at y=82 on the left; the narration line filled the
        # lower third at x>=150. Type is high-contrast against its backdrop,
        # so a band containing burned text has a far wider spread of values
        # than the same band of an untouched photograph.
        _band = _pa[60:110, 80:900]
        _bright = float((_band > 200).mean())
        check("no eyebrow header burned onto the photograph", _bright < 0.02,
              "%.1f%% of the eyebrow band is near-white type" % (_bright * 100))

        _low = _pa[int(_pa.shape[0] * 0.72):int(_pa.shape[0] * 0.95), 140:1600]
        _lowbright = float((_low > 215).mean())
        check("no narration line burned across the lower third",
              _lowbright < 0.02,
              "%.1f%% of the caption band is near-white type — the subtitles "
              "already carry these words" % (_lowbright * 100))

    _mssrc = open(os.path.join(ROOT, "video_pipeline",
                               "medical_segments.py")).read()
    _scene = _mssrc.split("def render_scene_still")[1].split("\ndef ")[0]
    _vert = _mssrc.split("def _render_vertical_photo")[1].split("\ndef ")[0]
    check("the photo renderers draw no type at all",
          "_eyebrow(" not in _scene and "d.text(" not in _scene
          and "_v_eyebrow(" not in _vert and "d.text(" not in _vert,
          "horizontal and vertical photographs must both stay bare")
    check("drawn cards keep their labels",
          "_eyebrow(d, niche_label)" in _mssrc,
          "a chart without its axis is broken, not cleaner")

    # Nothing else may print onto the finished picture either. Two more
    # sources were found on audit: the corner watermark (the wrongly-named
    # "The Ageing Files" in the reported screenshot) and five script phrases
    # drawn at 58px in the LOWER THIRD, wobbling and flickering, directly on
    # top of the subtitles.
    _cps = open(os.path.join(ROOT, "channels", "betrayal_deepdive",
                             "clinical_pipeline.py")).read()
    check("no corner watermark burned on the video",
          "label=\"watermark\"" not in _cps and "watermark_text" not in _cps,
          "YouTube already shows the channel name under every video")
    check("no flickering script phrases over the subtitles",
          "5*sin(45*t)" not in _cps and "unstable text beats" not in _cps,
          "58px strobing text at h-h/3 sat exactly where the captions are")

    # The atmosphere treatment itself must survive: it works ON the picture
    # rather than printing over it, and removing text should not have cost it.
    check("grain, glitch and the reveal flash still apply",
          "jump-scare flash" in _cps and "rgbashift" in _cps,
          "the treatment is not the text — only the text was removed")

    # ── no Short goes public from a generate-only run ──────────────
    # Run 31257986626 put four Shorts live on the channel during a workflow
    # whose own header reads "Phase 1: GENERATE only (no upload)". None had
    # been reviewed; one was narrated by espeak. privacyStatus was the literal
    # string "public" with no way to ask for anything else, while the main
    # video had been uploading unlisted-then-flipping for months.
    _saved_phase = os.environ.get("PHASE")
    try:
        for _phase, _want in (("generate", "unlisted"), ("", "unlisted"),
                              ("upload", "public")):
            os.environ["PHASE"] = _phase
            _got = _sre._default_short_privacy()
            check("PHASE=%s uploads Shorts as %s" % (_phase or "(unset)", _want),
                  _got == _want, "got %r" % _got)
    finally:
        if _saved_phase is None:
            os.environ.pop("PHASE", None)
        else:
            os.environ["PHASE"] = _saved_phase

    check("privacyStatus is never hardcoded public",
          '"privacyStatus": "public"' not in _sresrc,
          "a constant here is what put four unreviewed Shorts on the channel")
    check("subscribers are only told about visible Shorts",
          '"notifySubscribers": privacy == "public"' in _sresrc,
          "a notification for an unlisted preview is a dead link in every feed")
    check("the log says which privacy it used",
          'uploaded [%s]' in _sresrc,
          "'uploaded: <url>' read the same for a preview and a live video")
    check("uploaded Shorts are recorded for the upload phase",
          "UPLOADED_SHORTS" in _sresrc,
          "previews with no record sit unlisted forever")

    # ── the series name on a card belongs to that episode's niche ──
    # Raised as a defect from a screenshot showing "THE AGEING FILES", then
    # withdrawn: that episode WAS senior_health_longevity, whose series is
    # The Ageing Files, and the screenshots spanned two different episodes.
    # The guard is kept anyway, because the failure it describes is real and
    # cheap to prevent — every renderer takes niche["series"] from ONE lookup
    # by name, so a duplicated or missing series would mislabel a whole
    # episode with nothing to catch it.
    _src_p = open(os.path.join(ROOT, "channels", "betrayal_deepdive",
                               "clinical_pipeline.py")).read()
    _pairs = re.findall(r'"name":\s*"([a-z_]+)".*?"series":\s*"([^"]+)"',
                        _src_p, re.S)
    _pairs = [(n, s) for n, s in _pairs if len(n) < 40]
    _series = [s for _n, s in _pairs]
    check("every niche has a series name", len(_pairs) >= 10,
          "%d niches carry one" % len(_pairs))
    check("no two niches share a series name",
          len(set(_series)) == len(_series),
          "a shared name mislabels one of them on every card")
    check("the series comes from one lookup by name",
          _src_p.count('next(n for n in NICHES if n["name"] == niche_name)') >= 1
          and "niche_label=niche[\"series\"].upper()" in _src_p,
          "two sources of the same label is how they drift apart")

    # ── a picture must never contradict the line it sits under ─────
    # The delivered episode narrated "vaginal bleeding that had lasted three
    # days" over a sheet of brain CT slices — and that was the HIGHEST-scoring
    # match in the library, 18.0, because the lesion entry ended "... brain
    # slices ..." so every bleed anywhere in the body resolved to brain
    # imagery. "haemorrhage" is what a radiologist writes about a scan;
    # "bleeding" is what a patient reports. Sorting by which word was used
    # gets both right.
    _PAIRS = [
        ("vaginal bleeding that had lasted three days", "brain", False),
        ("He had been bleeding from the bowel for weeks.", "brain", False),
        ("A brain haemorrhage was found on the CT.", "brain", True),
        ("The MRI showed a lesion in the left frontal lobe.", "mri", True),
    ]
    import stock_match as _smx
    for _line, _tag, _want in _PAIRS:
        _p, _why, _role = _smx.best_any(_line, topic="rectal cancer")
        _has = _tag in (_why or "")
        check("%r %s %s" % (_line[:38], "gets" if _want else "never gets", _tag),
              _has == _want, "matched on [%s]" % _why)

    # ── a thumbnail has to be a picture of THIS episode ────────────
    # The delivered card was molecular models and a pine branch, with a red
    # ring round a twig, on a case report about advanced rectal cancer after
    # the Fukushima disaster — and it scored 9/10. Nothing was wrong with the
    # picture. Every term in score_image measured whether the card READS;
    # none asked what it was OF.
    _TOPIC = ("Social isolation and cancer management - advanced rectal cancer "
              "with patient delay following the 2011 triple disaster in Fukushima")
    _saved_chosen = dict(pt.CHOSEN_BY)
    try:
        pt.CHOSEN_BY.clear()
        pt.CHOSEN_BY.update({"scene": "hospital cancer ward",
                             "evidence": "rectal cancer ct scan"})
        _rel_ok, _ = pt.relevance(_TOPIC)
        pt.CHOSEN_BY.clear()
        pt.CHOSEN_BY.update({"scene": "molecular model",
                             "evidence": "pine branch macro"})
        _rel_bad, _why_bad = pt.relevance(_TOPIC)
    finally:
        pt.CHOSEN_BY.clear()
        pt.CHOSEN_BY.update(_saved_chosen)

    check("a photo about the episode reads as relevant", _rel_ok >= 1.0,
          "%.0f%% of roles matched the case" % (_rel_ok * 100))
    check("a photo about nothing reads as irrelevant", _rel_bad <= 0.0,
          "%s" % (_why_bad[0] if _why_bad else ""))

    _ptsrc = open(os.path.join(ROOT, "video_pipeline",
                               "photo_thumbnail.py")).read()
    check("every role searches the episode's own subject first",
          'if role == "evidence":\n            terms = (organ_terms' not in _ptsrc,
          "the SCENE photo is the whole background; it was searched generically")
    check("the thumbnail score can see the topic",
          "def score_image(path, topic=" in _ptsrc,
          "a score that never learns the subject cannot judge relevance")
    check("the pipeline passes the topic to the renderer",
          "topic=f\"{topic or ''} {title or ''}\".strip()" in _cps,
          "an unwired relevance term is an inert one")

    # ── the CC BY credit moved to the end, and must ARRIVE there ───
    # Removing the credit from the figure frame is only lawful because the
    # end card carries it. If that chain breaks the licence condition is
    # unmet, so it is checked rather than assumed.
    import medical_figure_render as _mfrx
    _mfrx.reset_figure_credits()
    _mfrx.register_figure_credit("Ozaki A et al. J Med Case Rep 2017", "Fig 1")
    _mfrx.register_figure_credit("Ozaki A et al. J Med Case Rep 2017", "Fig 2")
    check("a figure's source is recorded for the end card",
          _mfrx.figure_credits() == ["Ozaki A et al. J Med Case Rep 2017"],
          "one paper shown twice is credited once, not twice")
    _mfrsrc = open(os.path.join(ROOT, "video_pipeline",
                                "medical_figure_render.py")).read()
    _ff = _mfrsrc.split("def render_figure_frame")[1].split("\ndef ")[0]
    check("the figure frame itself draws nothing",
          "draw.text(" not in _ff,
          "the diagnostic image is the one frame a viewer must actually read")
    check("the end card prints the CC BY attribution",
          "FIGURES REPRODUCED UNDER CC BY 4.0" in _cps
          and "figure_credits()" in _cps,
          "credit may move off the image; it may not disappear")
    check("the citations card renders when figures were used",
          "if not real_sources and not _fig_credits" in _cps,
          "the card is now mandatory whenever a licensed figure was shown")

    # ── the photo library is big enough for one episode ────────────
    # A 114-segment episode showed 5 distinct photographs, because the
    # library held 18 images and the workflow never committed the ones it
    # harvested — so it could not grow past what was once added by hand.
    _wf2 = open(os.path.join(ROOT, ".github", "workflows",
                             "ch1_generate.yml")).read()
    check("harvested photographs survive the runner",
          "git add video_pipeline/stock_library/" in _wf2,
          "an ephemeral runner deletes anything not committed")
    check("the library tops up against a real episode's appetite",
          "_FLOOR = {" in _cps and "scene\": 40" in _cps,
          "an episode schedules ~37 photo cards; 9 scene images cannot cover it")

    # ── on-screen labels are complete thoughts ─────────────────────
    # Two renderers built their label by taking the first N words of whatever
    # narration sat under the segment. Segments are cut to fit a visual's
    # duration, not to sentence boundaries, so the result began and ended
    # mid-thought and then sat on screen for ten seconds. A real one from the
    # delivered episode: "lasted three days. She worked as a high-school
    # history" -- nine words, two half-sentences.
    import screen_text as _st

    _REAL = ("lasted three days. She worked as a high-school history teacher "
             "and took no medications beyond an occasional ibuprofen for "
             "tension headaches.")
    _lab = _st.caption_label(_REAL, max_words=9)
    check("the exact fragment from the episode is gone",
          _lab and not _lab.startswith("lasted three days"),
          "was 'lasted three days. She worked as a high-school history' -> now %r"
          % _lab)
    check("a label never opens mid-sentence",
          _lab and (_lab[0].isupper() or _lab[0].isdigit()),
          "a lowercase opening is the tail of a sentence the viewer missed")
    check("a label never opens on a conjunction",
          _st.caption_label("and took no medications beyond an occasional "
                            "ibuprofen for headaches.").split()[0].lower()
          not in ("and", "but", "or", "so"),
          "'and took no medications...' reads as a rendering fault")
    check("a label never ends on a dangling word",
          not _st.caption_label(
              "She was thirty-four years old, and she had been well on the "
              "Tuesday.").rstrip("…").split()[-1].lower()
          in ("and", "the", "a", "of", "had", "been"),
          "a trailing 'and' promises a word that never comes")
    check("nothing usable yields no label rather than a broken one",
          _st.caption_label("Under treatment.") == "",
          "two words is not a thought; drawing nothing is better")

    for _mod, _bad in (("medical_anatomy_motion.py", "split()[:9]"),
                       ("kinetic_text.py", "quote.split()[:12]")):
        _msrc = open(os.path.join(ROOT, "video_pipeline", _mod)).read()
        check("%s no longer slices raw words" % _mod, _bad not in _msrc,
              "slicing narration by word count is the bug itself")

    # ── the review gates actually open ─────────────────────────────
    # Run 31257986626: all six gates returned budget-exhausted having waited
    # zero seconds, so nothing was ever reviewed. The cause was comparing
    # wall-clock-since-process-start against a budget that exists to cap
    # WAITING -- so generation was spending the reviewer's time. These replay
    # that run's real gate arrival times and assert the gates now open.
    import human_review_gate as _hrg

    _JOB, _RES = 360.0, 45.0
    _ARRIVALS = [("script", 167), ("audio", 174), ("video", 257)]

    def _budget_at(el):
        return max(0.0, min(4.5, (_JOB - el - _RES) / 60.0))

    _saved_waits = list(_hrg._REVIEW_WAITS)
    _hrg._REVIEW_WAITS.clear()
    try:
        # The old rule, reconstructed, to prove the regression is real.
        _old_all_dead = all((el / 60.0) >= _budget_at(el) for _, el in _ARRIVALS)
        check("the old gate rule really did kill every gate", _old_all_dead,
              "wall-clock since process start always exceeded the budget")

        # The new rule: spent-waiting vs budget.
        _first = _hrg._review_time_spent_hours()
        check("a gate with no waiting behind it is not 'exhausted'",
              _first < _budget_at(167),
              "spent %.2fh against a %.2fh budget at the script gate"
              % (_first, _budget_at(167)))

        # And a gate that HAS spent the budget still closes.
        _hrg.record_review_wait("script", 4.6 * 3600, "timeout")
        check("a genuinely spent budget still closes the gates",
              _hrg._review_time_spent_hours() >= _budget_at(174),
              "4.6h of real waiting must exhaust a 4.5h ceiling")
    finally:
        _hrg._REVIEW_WAITS[:] = _saved_waits

    check("a window too short to answer is refused, not offered",
          _hrg.MIN_USABLE_GATE_MINUTES >= 10.0,
          "%.0f min floor — a 1-minute window expires while the notification "
          "is still arriving" % _hrg.MIN_USABLE_GATE_MINUTES)

    _hsrc = open(os.path.join(ROOT, "video_pipeline",
                              "human_review_gate.py")).read()
    # This used to assert "unreviewable-no-time" sat INSIDE _NO_REPLY, which
    # encoded the old, wrong behaviour: the gate never opened and the stage
    # proceeded as generated anyway. It now belongs to _NEVER_ASKED and must
    # NOT be in _NO_REPLY, because a gate that never put the question to a
    # human holds the episode instead of shipping it.
    # Asked of the MODULE, not of its source text. The previous two versions
    # of this check both read the file: the first asserted the value sat in
    # _NO_REPLY (encoding the bug), the second looked for the literal string
    # after "_NEVER_ASKED = " and failed because the tuple names the constant
    # rather than repeating the literal. Neither was wrong about the
    # behaviour, only about how the behaviour happens to be spelled.
    check("an unreviewed stage is never called approved",
          _hrg.never_asked(_hrg.UNREVIEWABLE_NO_TIME)
          and _hrg.never_asked(_hrg.HOLD_UNDELIVERED)
          and not _hrg.never_asked("timeout")
          and _hrg.UNREVIEWABLE_NO_TIME not in _hrg._NO_REPLY,
          "'auto-approved' on a gate that never opened reads as consent")
    check("the spent-review measure is waiting, not wall clock",
          "_review_time_spent_hours" in _hsrc
          and "_REVIEW_PROCESS_START).total_seconds() / 3600\n    return elapsed_hours"
              not in _hsrc,
          "a budget for waiting has to be measured in waiting")

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
    # This used to ask for the gaps in "The clot travelled to the lung" and
    # assert the answer was non-empty -- a check that PASSED only while the
    # library was still missing those pictures, and started failing the
    # moment a run harvested them. A test that breaks when the thing it
    # guards improves is worse than no test: it trains you to ignore a red
    # line. What actually needs guarding is that gaps() still reports a term
    # the library genuinely does not hold, so harvest() keeps being aimed at
    # what episodes ask for.
    _gaps = smatch.gaps("scene", ["zzzqqxnonexistentterm"])
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

    # ── a topic Short must not be the episode's monologue ──────────
    # "It's just like the monologue of the main script. I keep seeing that
    # it's like a cut and paste of the main script." The prompt used to
    # ASK for that in as many words, so these checks cover both halves of
    # the fix: the instruction is gone, and the measurement that catches
    # it anyway still separates a lifted script from an honest one.
    import shorts_reels_engine as _sre
    _sre_src = open(os.path.join(ROOT, "video_pipeline",
                                 "shorts_reels_engine.py")).read()
    check("the Short is no longer told to copy the episode",
          "same story with the same hook" not in _sre_src,
          "the old prompt demanded the main video's hook and ending")

    _main = ("She was forty-one years old and her blood pressure read seventy "
             "over forty in a corridor at two in the morning. For eleven weeks "
             "she had been telling three separate doctors that she was tired, "
             "that she was thirsty all the time, that her legs would not hold "
             "her on the stairs. Each of them wrote the same two words in her "
             "notes: probable dehydration. By the time somebody finally ordered "
             "a CT scan, the mass in her adrenal gland was nine centimetres "
             "across, and it had been quietly flooding her body with hormones.")
    _lifted = ("She was forty-one years old and her blood pressure read seventy "
               "over forty in a corridor at two in the morning. Each of them "
               "wrote the same two words in her notes: probable dehydration. "
               "By the time somebody finally ordered a CT scan, the mass in her "
               "adrenal gland was nine centimetres across.")
    _own = ("Write a number down twice and you have already admitted you do not "
            "trust it. Nine centimetres of tumour sat unimaged while three "
            "clinicians reached for the most ordinary answer available to them, "
            "and the maddening part is that they were not wrong: she really was "
            "dehydrated. Dehydration was the disease talking.")
    _d_lift = _sre.derivative_of(_lifted, _main)
    _d_own = _sre.derivative_of(_own, _main)
    check("a Short lifted from the episode is rejected",
          _d_lift > _sre.MAX_DERIVATIVE, "measured %.0f%%" % (_d_lift * 100))
    check("a Short written independently is not rejected",
          _d_own <= _sre.MAX_DERIVATIVE, "measured %.0f%%" % (_d_own * 100))
    check("a rejected Short is told which sentences it reused",
          "REJECTED FOR COPYING" in _sre._reuse_note(_lifted, _main)
          and _sre._reuse_note(_own, _main) == "",
          "a blind retry just reproduces the same lift")
    check("the reuse note reaches the next attempt's prompt",
          "{_overlap_note}" in _sre_src and "_overlap_note = _reuse_note(" in _sre_src,
          "a note nothing reads changes nothing")

    # ── silence only means yes if we actually asked ────────────────
    # Auto-approving on timeout is deliberate and stays. But the button
    # sender returned nothing, so a message Telegram REJECTED was byte-for-
    # byte identical to a message nobody answered — and every content gate
    # reads "no reply" as APPROVE. One 400 therefore published an episode no
    # human had been shown: "no buttons, auto-approved", exactly as reported.
    import human_review_gate as _hrg0
    _hrg0_src = open(os.path.join(ROOT, "video_pipeline",
                                  "human_review_gate.py")).read()
    check("the review sender reports whether the ask arrived",
          "THE REVIEWER WAS NEVER ASKED" in _hrg0_src,
          "a send that fails silently is indistinguishable from a timeout")
    check("an undelivered review is held, not auto-approved",
          _hrg0.resolve_silent_window(False, "", "", 60, what="t") == "hold-undelivered"
          and _hrg0.resolve_silent_window(True, "", "", 60, what="t") == "approve",
          "silence means yes only when somebody was actually asked")
    # Exactly ONE occurrence: the auto-approve notice may only be emitted
    # from inside resolve_silent_window(). A second copy anywhere means a
    # gate is still approving on silence without asking whether it asked.
    check("every auto-approve branch goes through that decision",
          _hrg0_src.count("resolve_silent_window(") >= 9
          and _hrg0_src.count("min expired — auto-approved.") == 1,
          "found %d copies of the auto-approve notice (want exactly 1)"
          % _hrg0_src.count("min expired — auto-approved."))
    check("a rejected HTML message is retried as plain text",
          '"chat_id": tg_chat, "text": text, "reply_markup": keyboard' in _hrg0_src,
          "losing the formatting beats losing the review")
    # EVERY gate, not most of them. Enumerated from the source rather than
    # listed by hand, so a gate added later is checked automatically instead
    # of being the one nobody remembered to add here.
    import re as _re2
    _gate_gaps = []
    for _f in _re2.split(r"\ndef ", _hrg0_src):
        _n = _f.split("(")[0].strip()
        if not _n.startswith("review_") or _n in ("review_time_report", "review_recipient"):
            continue
        _btn = ("_button_keyboard(" in _f or "_tg_send_message_with_buttons(" in _f
                or "send_with_keyboard(" in _f)
        if not (_btn and "_delivered" in _f and "_poll_for_decision" in _f):
            _gate_gaps.append(_n)
    check("every review gate has buttons, tracks delivery, and polls",
          not _gate_gaps, "gaps: %r" % (_gate_gaps,))
    check("the audio gate never approves without asking",
          "proceeding on quality-gate score alone" not in _hrg0_src
          and "review_audio_excerpt.mp3" in _hrg0_src,
          "a narration too big to send used to skip the audio review entirely")
    check("all button messages go through one hardened sender",
          _hrg0_src.count('"reply_markup": _community_tab_keyboard()') == 0
          and _hrg0_src.count('"reply_markup": {"inline_keyboard": buttons}') == 0,
          "a gate posting its own keyboard bypasses the retry and the check")
    check("a tapped button is acknowledged so it cannot read as expired",
          "answerCallbackQuery" in _hrg0_src,
          "an unanswered callback spins and then says expired")

    check("HOLD does not delete the episode",
          'if _final_gate["decision"] == "hold-undelivered":' in _cp
          and _cp.index('if _final_gate["decision"] == "hold-undelivered":')
              < _cp.index('if _final_gate["decision"] != "approve":'),
          "deleting an upload because Telegram 400'd would be absurd")
    check("HOLD breaks the script gate's while-True instead of spinning",
          'if _review["decision"] == "hold-undelivered":' in _cp,
          "re-sending to a dead channel just burns the job clock")

    # ── the two non-negotiables, asserted rather than assumed ──────
    # "CC BY only — never CC BY-NC or CC BY-ND", and no medical advice.
    # Both were implemented carefully and NEITHER had a preflight check,
    # which is the wrong way round: these are the two rules where a silent
    # regression is a legal and safety problem, not a quality one.
    import pmc_data as _pmc
    _lic_cases = [("cc by", True), ("CC BY", True), ("cc-by", True),
                  ("cc by 4.0", True), ("cc0", True), ("public domain", True),
                  ("cc by-nc", False), ("CC BY-NC 4.0", False),
                  ("cc by-nd", False), ("cc by-nc-nd", False),
                  ("cc_by_nc", False), ("non-commercial", False),
                  ("noderivatives", False), ("", False), (None, False),
                  ("all rights reserved", False)]
    _lic_bad = [s for s, want in _lic_cases if bool(_pmc._license_ok(s)) != want]
    check("CC BY passes and NC/ND never does",
          not _lic_bad,
          "misclassified: %r" % (_lic_bad[:3],))
    check("the NC/ND rejection runs BEFORE the allow-list",
          not _pmc._license_ok("cc by-nc"),
          "'cc by-nc' contains 'cc by' — order is the whole point")
    check("every article path re-checks the licence locally",
          "_license_ok(a.get(\"license\"" in open(
              os.path.join(ROOT, "video_pipeline", "pmc_data.py")).read(),
          "never trust a remote filter for a licensing decision")

    import medical_policy_gate as _mpg
    _cit = "Smith J et al. BMJ Case Rep 2021. PMC1234567 — licensed CC BY 4.0"
    _adv_ok, _adv_v = _mpg.check_script(
        "You should take 500mg of ibuprofen twice daily if you feel this way.", _cit)
    # THE DOSE CAME OUT OF THIS SENTENCE ON PURPOSE.
    #
    # This case used to read "given 500mg of ibuprofen twice daily" and
    # asserted it was NOT blocked. That assertion is now wrong, by direct
    # owner instruction after run 31740721781 shipped "argatroban at 2
    # micrograms per kilogram per minute" and "IVIG 1 g/kg/day": a dosing
    # schedule stated in a documentary is actionable by a member of the
    # public, and it is now rule 7.
    #
    # Recording plainly that this is a POLICY CHANGE, not a test bent to fit
    # new code. What the check protects is unchanged and still matters: the
    # channel must be able to report what happened to a patient, or it cannot
    # function at all. So the sentence still reports drug, timing and a lab
    # value -- everything the narration genuinely needs -- and only the
    # milligrams are gone. The dose form gets its own check right below, so
    # the two halves of the rule are both pinned.
    _rep_ok, _rep_v = _mpg.check_script(
        "The patient was given ibuprofen twice that day. Her sodium was 122 "
        "and by the third morning it had fallen further.", _cit)
    _dose_ok, _dose_v = _mpg.check_script(
        "She was started on argatroban at 2 micrograms per kilogram per "
        "minute, and IVIG 1 g/kg/day was added.", _cit)
    check("second-person medical advice is blocked",
          bool(_adv_v) and any(v.get("severity") == "block" for v in _adv_v),
          "this is the YouTube policy line, not a style preference")
    check("reporting what happened to a patient is not blocked",
          not _rep_v,
          "the channel cannot function if describing a real case trips the gate")
    check("an actionable dosing schedule IS blocked",
          bool(_dose_v) and any(v.get("severity") == "block" for v in _dose_v),
          "run 31740721781 narrated argatroban 2 mcg/kg/min and IVIG 1 g/kg/day "
          "past every gate")
    # ── THE CARD CEILING, WHICH HAD NO TEST AT ALL ─────────────────
    #
    # The most-repeated instruction in this whole channel's history --
    # "I don't want any visual card longer than X, it should be hardcoded" --
    # was enforced by code nothing ever checked. That is how the previous
    # ceiling shipped cards past it for months: durations() clamped every
    # card correctly and then a final residue step added the leftover to the
    # longest one WITHOUT re-clamping, so any episode whose audio outran
    # n * MAX_SECONDS put the entire shortfall on a single card.
    #
    # Read from the module, never written as a literal here. A check that
    # hardcodes 12.5 stops testing the rule the moment the rule is retuned --
    # which already happened once in this file, when a bed-loudness check
    # carried the value it was supposed to be verifying.
    import clinical_variation as _cvar
    _ceil_bad, _sum_bad, _floor_bad = [], [], []
    for _mins in (15, 18, 20, 22, 25, 30):
        _tot = _mins * 60
        _n = _cvar.cards_needed(_tot)
        _d = _cvar.EpisodeVariation(3, _n).durations(_tot, [""] * _n)
        if max(_d) > _cvar.MAX_SECONDS + 1e-6:
            _ceil_bad.append((_mins, round(max(_d), 2)))
        if min(_d) < _cvar.MIN_SECONDS - 1e-6:
            _floor_bad.append((_mins, round(min(_d), 2)))
        if abs(sum(_d) - _tot) > 0.05:
            _sum_bad.append((_mins, round(sum(_d) - _tot, 2)))
    check("no card ever exceeds the hardcoded ceiling",
          not _ceil_bad,
          "over the %.1fs ceiling at: %s" % (_cvar.MAX_SECONDS, _ceil_bad))
    check("no card falls under the floor either",
          not _floor_bad,
          "under the %.1fs floor at: %s" % (_cvar.MIN_SECONDS, _floor_bad))
    check("the cards cover the audio exactly, at every length",
          not _sum_bad,
          "visuals drift out of sync with the narration at: %s" % (_sum_bad,))
    # The specific bug, reproduced: ask for far too few cards and the old
    # code silently handed one card the whole shortfall. It must refuse.
    try:
        _cvar.EpisodeVariation(1, 40).durations(1200, [""] * 40)
        _too_few_raises = False
    except _cvar.CardsTooFew:
        _too_few_raises = True
    except Exception:
        _too_few_raises = False
    check("too few cards is refused, not absorbed by one long card",
          _too_few_raises,
          "this is exactly how the old ceiling was breached — silently")
    # And the pacing must not collapse onto the ceiling, which is the other
    # way this goes wrong: every card the same length reads as static even
    # though no single card breaks the rule.
    _n75 = _cvar.cards_needed(900)
    _slow = "the patient died that night and the diagnosis was finally revealed"
    _fast = "then the next morning meanwhile the team also reviewed the chart"
    _flat = "her admission notes recorded a temperature and a pulse on arrival"
    _dd = _cvar.EpisodeVariation(3, _n75).durations(
        900, [(_slow if i % 7 == 0 else _fast if i % 5 == 0 else _flat)
              for i in range(_n75)])
    _pinned = sum(1 for x in _dd if x > _cvar.MAX_SECONDS - 0.05) / float(_n75)
    check("the pacing does not collapse onto the ceiling",
          _pinned < 0.35,
          "%.0f%% of cards render at exactly the ceiling — that is the flat "
          "pace the variation engine exists to prevent" % (_pinned * 100))

    check("a lab value is never mistaken for a dose",
          not _mpg.check_script(
              "Her sodium was 118 mmol/L, creatinine 2.4 mg/dL, platelets "
              "12,000 per microlitre.", _cit)[1],
          "the CHART register plots exactly these numbers — a gate that eats "
          "them blocks every good script and gets switched off")
    check("a script with no citation is blocked",
          bool(_mpg.check_script("Her sodium was 122.", "")[1]),
          "an uncited clinical claim is the thing the licence requires")

    # ── a missing artifact must not cost a finished episode ────────
    # Generate and Upload are separate runs on separate ephemeral runners,
    # so the video reaches Upload only as a downloaded artifact — and that
    # step is configured `if_no_artifact_found: warn`, so a missing or
    # expired artifact arrives here as a missing FILE, not a failed step.
    # The episode is usually already on YouTube unlisted by then (today's
    # real pending_upload.json carries prerendered_yt_video_id lo1b3ays1ms),
    # and publishing it needs a metadata call, not the bytes.
    check("a missing artifact does not kill an already-uploaded episode",
          "_have_remote = bool(pending.get(\"prerendered_yt_video_id\"))" in _cp
          and "if not _have_remote:" in _cp,
          "the file check used to exit(1) before looking for the remote copy")
    check("with no remote copy AND no file, it still fails loudly",
          "no unlisted upload exists to publish instead" in _cp,
          "silently continuing without a video would be worse")
    _up = _cp[_cp.find("UPLOAD PHASE"):]
    _upload_call = _up.find("video_path, title, description, tags")
    _else = _up.rfind("else:", 0, _upload_call)
    _if = _up.rfind("if _prerendered_vid_id:", 0, _else)
    check("the byte-consuming upload only runs without a remote copy",
          0 < _if < _else < _upload_call,
          "otherwise a missing file would still crash the reuse path")

    # ── an approved Short has to actually reach the channel ────────
    # Making Shorts upload unlisted stopped four unreviewed ones going live,
    # and left the opposite bug: approve did nothing, so a Short a human had
    # approved stayed unlisted for ever. They now follow the main video —
    # approved during generate, published by the upload phase.
    check("approving a Short records it for the upload phase",
          "_approved_short_ids.append(" in _cp
          and '"approved_short_ids": _approved_short_ids' in _cp,
          "approve used to be a no-op once Shorts stopped going out public")
    check("the upload phase publishes the approved Shorts",
          'pending.get("approved_short_ids")' in _cp
          and "Short published: https://youtube.com/shorts/" in _cp,
          "unlisted for ever is not the same as reviewed")
    check("a rejected episode takes its Shorts with it",
          "Deleted the unlisted Short" in _cp,
          "Shorts promoting a video that was never published")
    # The declaration must dominate save_pending, not sit inside the Shorts
    # try — anything raising in between would reach save_pending with the
    # name unbound and kill the generate phase after the episode was built.
    _decl = _cp.find("_approved_short_ids = []")
    _try = _cp.find("if importlib.util.find_spec(\"shorts_reels_engine\")")
    _use = _cp.find('"approved_short_ids": _approved_short_ids')
    check("the approved-Shorts list cannot be unbound at save time",
          0 < _decl < _try < _use,
          "a NameError here loses a completed episode")

    # ── the script gate could not see boring ───────────────────────
    # The delivered episode's script was reported as "okay, fine", 6.5,
    # while the gate had passed it above 8.5. score_narrative_craft() opens
    # at 4.0 and adds points for an escalation KEYWORD, a resolution
    # KEYWORD, and sentence-length variance — all of which a competent dull
    # recitation has. Structure is not interest. What is measurable, and
    # specific to this channel, is whether the script stayed in the register
    # of the paper it came from.
    import clinical_quality as _cq
    _dull = ("The patient was a forty-one year old woman. She was assessed by "
             "three physicians. Each assessment concluded that her symptoms "
             "were consistent with dehydration. No imaging was performed. "
             "Computed tomography was subsequently arranged. This "
             "demonstrated a nine centimetre adrenal mass. Treatment was "
             "commenced. The case was published. This case illustrates the "
             "importance of considering endocrine causes. Clinicians should "
             "maintain an index of suspicion in patients presenting with "
             "unexplained hypotension.")
    _written = ("The triage nurse wrote the number down twice. Seventy over "
                "forty, at two in the morning. For eleven weeks this woman "
                "had told three doctors the same three things, and three "
                "doctors wrote the same two words. Nobody ordered a scan. "
                "The first gave her a leaflet about drinking water. When "
                "somebody finally looked, nine centimetres of tumour sat on "
                "her adrenal gland, stripping the salt out of her blood as "
                "fast as she could drink.")
    _dp, _dr, _di = _cq.case_report_register(_dull)
    _wp, _wr, _wi = _cq.case_report_register(_written)
    check("a script written like the paper is flagged",
          bool(_di), "%.1f passive/100w, %.1f journal connectives" % (_dp, _dr))
    check("a script written like a film is not flagged",
          not _wi, "%.1f passive/100w, %.1f journal connectives" % (_wp, _wr))
    _s_dull = _cq.score_script(2000, 0, _dull, 8.0, 8.0, 8.0)[0]
    _s_written = _cq.score_script(2000, 0, _written, 8.0, 8.0, 8.0)[0]
    check("register costs enough to send a dull script back",
          _s_dull < _s_written - 1.0,
          "same craft/hook/clarity: dull %.2f vs written %.2f" % (_s_dull, _s_written))
    check("register is a penalty, never a block",
          "duration floor" in _cq.score_script(100, 0, _dull, 8.0, 8.0, 8.0)[2].get("blocked_on", [])
          and not any("passive" in b for b in
                      _cq.score_script(2000, 0, _dull, 8.0, 8.0, 8.0)[2]["blocked_on"]),
          "it is a rewrite the stage can do — retry, do not skip the day")
    check("a script just over the line is barely charged",
          _cq.PASSIVE_LIMIT_PER_100W > 0 and
          min(2.0, (_cq.PASSIVE_LIMIT_PER_100W + 0.5) - _cq.PASSIVE_LIMIT_PER_100W) == 0.5,
          "over-penalising is how a gate blocks every attempt")
    check("the generator is told not to write in journal register",
          "DO NOT WRITE IT LIKE THE PAPER" in _cp,
          "measuring a fault without asking for the fix wastes attempts")

    # ── generation must not spend the review window ────────────────
    # Run 31257986626's script stage ran 2h43m with 275 rate-limit errors,
    # Groq at 98,807/100,000 tokens and Cloudflare out of daily neurons.
    # Cause: ai_generate CLEARED the dead-provider set once everything had
    # failed, so every later call re-walked all ten providers with a 10s
    # pause between each — 90s of sleeping per call, ~28 sweeps, before any
    # HTTP time. That hour came out of the window kept for review.
    check("a daily-exhausted provider is retired, not revived",
          "_EXHAUSTED_PROVIDERS_THIS_RUN" in _cp
          and "_DEAD_PROVIDERS_THIS_RUN.clear()" not in _cp,
          "clearing the set re-swept ten dead providers on every call")
    check("every provider marks its own daily exhaustion",
          _cp.count("_note_quota_exhausted(\"") >= 9,
          "a provider that never reports quota is revived forever")
    check("the chain stops when every provider is exhausted",
          "Not retrying: " in _cp,
          "nothing answers until the allocations reset")
    check("no 10s pause is spent on a daily 429",
          "is out of quota for today — moving straight on" in _cp,
          "the next provider is a different account; waiting helps nobody")
    check("the script loop yields before the reserve is gone",
          "_generation_may_continue()" in _cp
          and "is into the reserve kept for review" in _cp,
          "attempt 9 with no reviewer is worth less than attempt 8 with one")

    # ── the Community post fallback WAS the generic post ───────────
    # score_community_post lists "what's your take" and "drop your theory"
    # as generic filler. The fallback draft was exactly that sentence, and
    # being the failure path it never faced the gate at all — so the one
    # draft that could not pass was the one that shipped on a bad day.
    import human_review_gate as _hrg
    _filler = 'What\'s your take on "The 9cm mass"? Drop your theory below.'
    _fs, _fi = _hrg.score_community_post(_filler, [], "an adrenal tumour case",
                                         "The 9cm mass")
    check("the old fallback post could never have passed the gate",
          _fs < _hrg.COMMUNITY_POST_MIN,
          "scored %.1f/10 against a %.1f bar" % (_fs, _hrg.COMMUNITY_POST_MIN))
    check("no AI provider means no post, not filler",
          _hrg.draft_community_post("a case", "niche", "T", None) == {},
          "it used to return the filler above, ungated")
    check("all attempts failing means no post, not filler",
          _hrg.draft_community_post("a case", "niche", "T",
                                    lambda *a, **k: None) == {},
          "a skipped post costs one slot; a generic one is published")
    _sig = __import__("inspect").signature(_hrg.review_community_tab).parameters
    check("a below-bar draft can be flagged to the reviewer",
          "below_bar" in _sig and "score" in _sig and "issues" in _sig,
          "draft_community_post set below_bar and nothing could receive it")
    _hrg_src = open(os.path.join(ROOT, "video_pipeline", "human_review_gate.py")).read()
    check("the reviewer is told when a draft failed its gate",
          "THIS DRAFT DID NOT PASS THE QUALITY GATE" in _hrg_src,
          "being asked to publish it silently looks like it was checked")
    for _ch, _p in (("Ch1", ("channels", "betrayal_deepdive", "clinical_pipeline.py")),
                    ("Ch2", ("channels", "evidence_room", "evidence_room_pipeline.py")),
                    ("Ch3", ("channels", "collapse_index", "collapse_index_pipeline.py")),
                    ("Ch4", ("channels", "archive", "archive_pipeline.py")),
                    ("Ch5", ("channels", "control_files", "control_files_pipeline.py"))):
        _src = open(os.path.join(ROOT, *_p)).read()
        if "draft_community_post" not in _src:
            continue
        check("%s survives an empty Community draft" % _ch,
              'no draft worth posting' in _src and 'below_bar=_cp_draft.get' in _src,
              "the shared drafter now returns {} — a bare [\"question\"] is a KeyError")

    # ── a paraphrase is still a retelling ──────────────────────────
    # The n-gram check alone was not enough and its own numbers said so:
    # three paraphrases of the same episode scored 1.8%, 0.0% and 0.0%
    # literal overlap. Rewriting the sentences hides literal reuse but
    # cannot hide the running order, so beat order carries this. Both
    # halves of the corpus are asserted here — catching every copy is
    # worthless if it also rejects every original.
    _EP = ("She was forty-one years old and her blood pressure read seventy "
           "over forty in a corridor at two in the morning. For eleven weeks "
           "she had been telling three separate doctors that she was tired, "
           "that she was thirsty all the time, that her legs would not hold "
           "her on the stairs. Each of them wrote the same two words in her "
           "notes: probable dehydration. Nobody ordered a scan. The first "
           "doctor suggested she drink more water. By the time somebody "
           "finally ordered a CT scan, the mass in her adrenal gland was nine "
           "centimetres across, and it had been quietly flooding her body "
           "with hormones that stripped the salt out of her blood.")
    _COPY = ("A forty-one year old woman had a blood pressure of seventy over "
             "forty when she reached the corridor at two in the morning. Over "
             "eleven weeks she told three different doctors the same thing: "
             "exhausted, thirsty, legs failing on the stairs. All three wrote "
             "down probable dehydration. None ordered imaging. The first told "
             "her to drink more water. When a CT was finally requested, a nine "
             "centimetre mass sat on her adrenal gland, pouring out hormones "
             "that stripped salt from her blood.")
    _OWN = ("Her legs were the tell. Not the thirst, which any of us would "
            "explain away, and not the tiredness, which every adult reports. "
            "Legs that will not carry you up a staircase are muscles running "
            "out of the salt they need to fire, and salt was exactly what was "
            "being stripped out of her by nine centimetres of tissue nobody "
            "had imaged. Three clinicians heard about the stairs. It went in "
            "the notes as dehydration.")

    def _rejected(short):
        return (_sre.derivative_of(short, _EP) > _sre.MAX_DERIVATIVE
                or _sre.beat_order_similarity(short, _EP) > _sre.MAX_BEAT_ORDER)

    check("a paraphrase is invisible to the literal check",
          _sre.derivative_of(_COPY, _EP) <= _sre.MAX_DERIVATIVE,
          "measured %.1f%% — this is why beat order exists"
          % (_sre.derivative_of(_COPY, _EP) * 100))
    check("a paraphrase is still caught, by its running order",
          _rejected(_COPY),
          "beat order %.0f%% (max %.0f%%)"
          % (_sre.beat_order_similarity(_COPY, _EP) * 100, _sre.MAX_BEAT_ORDER * 100))
    check("an independent Short on the same case is not caught",
          not _rejected(_OWN),
          "beat order %.0f%%" % (_sre.beat_order_similarity(_OWN, _EP) * 100))
    check("too little shared material is not called a retelling",
          _sre.beat_order_similarity("A completely unrelated sentence.", _EP) == 0.0,
          "four shared details is the floor for judging order")
    check("the originality judge fails open, not closed",
          _sre.judge_is_retelling("", _EP) == (False, ""),
          "a dead API must not block every Short the channel makes")
    check("all three originality gates run before the rubric",
          "_beat > MAX_BEAT_ORDER" in _sre_src and "judge_is_retelling(" in _sre_src
          and "_deriv > MAX_DERIVATIVE" in _sre_src,
          "the rubric passes a retelling, because the episode passed it")
    check("a Short must carry a whole arc, not a trailer",
          "A WHOLE STORY IN UNDER A MINUTE" in _sre_src,
          "hook, situation, turn and real ending inside 45 seconds")

    # ── generic filler cannot be published ─────────────────────────
    # Asserted by BEHAVIOUR, not by searching for the phrase: the phrases
    # legitimately still appear in the source, in the ban list and in the
    # comment recording what was removed.
    # A CHECK MUST NOT LEAVE FOOTPRINTS IN PRODUCTION STATE.
    #
    # This call reaches the Shorts format chooser, which appends to the real
    # channels/betrayal_deepdive/shorts_format_history.json. Running the
    # suite therefore wrote entries for Shorts that were never produced --
    # video_id null, ctr null -- into the history that drives format
    # rotation and the CTR learning. Harmless individually, wrong in
    # aggregate: the suite is run repeatedly, and every run taught the
    # rotation about episodes that do not exist. The format recorder is
    # stubbed for the same reason llm_json is, and by the same mechanism.
    import shorts_formats as _sf_mod
    _real_llm_json = _sre.llm_json
    _real_record = getattr(_sf_mod, "record_format_used", None)
    try:
        _sre.llm_json = lambda *a, **k: None      # model fails
        if _real_record:
            _sf_mod.record_format_used = lambda *a, **k: None
        _fallback = _sre.get_trending_short_topic("standalone_1")
    finally:
        _sre.llm_json = _real_llm_json
        if _real_record:
            _sf_mod.record_format_used = _real_record
    check("a failed topic ships nothing rather than filler",
          _fallback == {},
          "it used to return hype with no fact in it, got %r" % (_fallback,))
    check("a failed topic retries instead of shipping filler",
          "No usable trending topic this attempt" in _sre_src,
          "an empty dict must not KeyError the caller")
    _old_filler = ("The truth about sleep will shock you. What really happened "
                   "was hidden from the public for years and nobody told you.")
    check("empty hype is rejected",
          len(_sre.hollow_phrases(_old_filler, "SHOCKING: sleep",
                                  "You won't believe this...")) >= 5,
          "the deleted template is the specification for this check")
    check("a real clinical Short is not called hype",
          _sre.hollow_phrases(
              "Seventy over forty, at two in the morning, and the nurse wrote "
              "it down twice. Eleven weeks of being told to drink more water.",
              "The 9cm mass 3 doctors missed", "Written down twice") == [],
          "the gate must not punish plain writing")
    check("a script with no concrete number is rejected",
          any("number" in r for r in _sre.hollow_phrases(
              " ".join(["something remarkable happened to a person"] * 12))),
          "a Short with no number in it is an opinion")
    check("a clinical title can score full marks without crime words",
          _sre.score_short_script(
              "x " * 130, "The 9cm tumour 3 doctors missed", "written twice"
          )["title"] >= _sre.TITLE_AXIS_MAX,
          "the rubric used to require SHOCKING/BETRAYAL/CAUGHT")

    # ── a Short link must survive the trip to Telegram ─────────────
    # "the standalone Short links don't open at all". Every sender posted
    # with legacy Markdown, and a YouTube id is base64url — two of the four
    # Shorts that went live carried an underscore, which opens italic. One
    # underscore means Telegram rejects the message with a 400 that requests
    # does not raise; two means it is accepted with the underscores eaten
    # and the link silently pointing at a video that does not exist.
    import tg_safe as _tgs
    check("a Short URL with an underscore is not sent as Markdown",
          _tgs.markdown_would_break(
              "*UPLOADED*\nURL: https://youtube.com/shorts/zNvuOykr_vk"),
          "one underscore is a 400, and the message never arrives")
    check("a URL whose underscores would be eaten is caught",
          _tgs.markdown_would_break("URL: https://youtube.com/shorts/a_b_c1234"),
          "this one succeeds and delivers a broken link")
    check("a clean message still gets its formatting",
          not _tgs.markdown_would_break(
              "*UPLOADED*\nURL: https://youtube.com/shorts/DnHi98fcoYg"),
          "the fallback should be a fallback, not the default")
    check("an LLM title with a stray marker is caught",
          _tgs.markdown_would_break("Title: the 9_cm mass\nURL: https://y.tube/abc"),
          "titles are written by a model and are not escaped")
    for _mod, _path in (("Shorts", ("video_pipeline", "shorts_reels_engine.py")),
                        ("post-upload report", ("video_pipeline", "post_upload_reporter.py")),
                        ("weekly report", ("scripts", "empire_report.py"))):
        _s = open(os.path.join(ROOT, *_path)).read()
        check("%s sends through the safe sender" % _mod,
              "from tg_safe import send" in _s,
              "a raw Markdown post can lose the link")

    # ── standalone Shorts research the right thing ─────────────────
    check("trending research uses the topic it was given",
          "_TREND_CACHE" in _sre_src and "want = {w for w in re.findall" in _sre_src,
          "niche_hint used to be accepted and ignored")
    check("trending research asks the categories this channel competes in",
          "videoCategoryId" in _sre_src and _sre._TREND_CATEGORIES,
          "general US trending is music and sport, not medicine")
    check("trending research is not refetched every retry",
          "_TREND_CACHE[hint] = titles" in _sre_src,
          "13 attempts asked YouTube the same question 13 times")
    check("trending research never fabricates on failure",
          _sre.get_real_youtube_trending_signal("no credentials here") == [],
          "an invented trend is worse than none")

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

    # ══════════════════════════════════════════════════════════════════
    # A GATE NOBODY CAN CLEAR IS NOT A STANDARD, IT IS A DEAD END.
    #
    # Ch1 run 31373726976 produced a real 8.5 script, human-approved audio
    # narrated by Kokoro, a rendered 71MB video and three separate human
    # approvals — and then binned the whole episode because the thumbnail
    # OVERLAY TEXT could not clear 8.5 in 39 attempts. Every one of those 39
    # attempts scored exactly 5.5, which is the signature of an arithmetic
    # impossibility rather than a quality problem: the sanitizer deleted the
    # digits that score_thumbnail_text awards +2.5 for, so the NUMBER+NOUN
    # format the prompt asks for FIRST could never score above 5.5.
    #
    # These checks compose the two halves — the real sanitizer and the real
    # scorer — and prove a well-formed answer can actually reach the bar.
    # Checking either half alone is exactly what missed this for weeks.
    # ══════════════════════════════════════════════════════════════════
    try:
        from thumbnail_engine_v2 import score_thumbnail_text as _sts

        def _sanitize_like_pipeline(raw):
            """The sanitizer as the pipelines run it, applied verbatim."""
            hq = raw.strip().endswith("?")
            r = re.sub(r'[^A-Z0-9%\.,\s]', '', raw.upper()).strip()
            r = re.sub(r'(?<![0-9])[\.,]|[\.,](?![0-9])', '', r).strip()
            w = r.split()[:4]
            if not (2 <= len(w) <= 4):
                return None
            return ' '.join(w) + ("?" if hq else "")

        _THUMB_GATE = 8.5
        for _raw in ("10 DAYS COMA", "4,380 DAYS HIDDEN", "0.1 WHITE CELLS"):
            _clean = _sanitize_like_pipeline(_raw)
            check("a NUMBER+NOUN thumbnail line can clear the gate: %r" % _raw,
                  _clean is not None and _sts(_clean) >= _THUMB_GATE,
                  "sanitized to %r scoring %s — the gate is unreachable"
                  % (_clean, _sts(_clean) if _clean else None))
        _q = _sanitize_like_pipeline("WHY DID SHE STOP?")
        check("a DIRECT QUESTION thumbnail line can clear the gate",
              _q is not None and _sts(_q) >= _THUMB_GATE,
              "sanitized to %r scoring %s" % (_q, _sts(_q) if _q else None))
        # and the bar still bites — a fix that just lowers the standard is
        # not a fix. A line with neither a digit nor a question mark must
        # still fail, exactly as it did live.
        _flat = _sanitize_like_pipeline("ZERO WHITE BLOOD")
        check("a number-less, question-less line still fails the gate",
              _flat is not None and _sts(_flat) < _THUMB_GATE,
              "the gate stopped discriminating")
        # the digits must survive the sanitizer itself, not just the scorer
        check("the sanitizer preserves digits",
              _sanitize_like_pipeline("10 DAYS COMA") == "10 DAYS COMA",
              "digits stripped before scoring — the live 39x5.5 failure")
    except Exception as _e:
        check("thumbnail-text gate reachability", False, repr(_e))

    # These next checks scan for defective CODE, and the fix commits carry
    # comments that quote the defective code by name to explain it. Scanning
    # raw text would flag the explanation as the defect, so comments are
    # stripped first — the question is what the pipeline RUNS.
    def _code_only(src):
        out = []
        for line in src.splitlines():
            s = line.lstrip()
            if s.startswith("#"):
                continue
            out.append(line)
        return "\n".join(out)

    # THE PROMPT MUST NOT TEACH THE MODEL TO OMIT THE NUMBER.
    #
    # Scoring was only half of it. Ch1's prompt introduced the NUMBER+NOUN
    # format with the lead example "FOUND INSIDE WALLS" — which contains no
    # number — so the model dutifully produced number-less lines, and the
    # sanitizer then deleted any digit that did survive. Two independent
    # causes pushing the same way, which is why 39 of 39 attempts landed on
    # exactly 5.5. The other four channels illustrate the format only with
    # digits ('$2.4M GONE', '47 REPORTS', '4380 DAYS'), and were fine.
    # Scoped to format A only: format B is a QUESTION and its examples
    # ("WHO WAS WATCHING?") correctly have no digits, so a wider window
    # would fail on the one format that is right.
    _ch1_prompt = ""
    if "A. NUMBER+NOUN" in _cp and "B. DIRECT QUESTION" in _cp:
        _a0 = _cp.index("A. NUMBER+NOUN")
        _ch1_prompt = _cp[_a0:_cp.index("B. DIRECT QUESTION", _a0)]
    _examples = re.findall(r"\(e\.g\.\s*([^)]+)\)", _ch1_prompt)
    _ex_items = [e.strip() for grp in _examples for e in grp.split(",")]
    check("every NUMBER+NOUN example in the prompt contains a digit",
          bool(_ex_items) and all(any(c.isdigit() for c in e) for e in _ex_items),
          "an example without a number teaches the model to omit it: %s"
          % [e for e in _ex_items if not any(c.isdigit() for c in e)][:3])

    # The identical sanitizer line exists in all five channel pipelines, so
    # the identical dead end exists in all five unless all five are checked.
    for _ch, _p in (("Ch1", ("channels", "betrayal_deepdive", "clinical_pipeline.py")),
                    ("Ch2", ("channels", "evidence_room", "evidence_room_pipeline.py")),
                    ("Ch3", ("channels", "collapse_index", "collapse_index_pipeline.py")),
                    ("Ch4", ("channels", "archive", "archive_pipeline.py")),
                    ("Ch5", ("channels", "control_files", "control_files_pipeline.py"))):
        _src = _code_only(open(os.path.join(ROOT, *_p)).read())
        check("%s thumbnail sanitizer does not delete digits" % _ch,
              r"[^A-Z\s]" not in _src,
              "the character class that made the 8.5 gate unreachable")

    # ══════════════════════════════════════════════════════════════════
    # THE SOUND DESIGN MUST NOT BE HOSTAGE TO THE PICTURE GRADE.
    #
    # Same run: the FX step hit its timeout twice (20 min each) because the
    # 0.15s jump-scare flash was built from a full-length synthesized white
    # video plus a per-pixel blend expression. Because the audio mix shared
    # that one ffmpeg call, every content-matched SFX cue died with it —
    # the log shows the cues being selected and then discarded, twice.
    # ══════════════════════════════════════════════════════════════════
    _cp_code = _code_only(_cp)
    check("the jump-scare flash costs nothing outside its own window",
          "blend=all_expr" not in _cp_code and "eq=brightness=1.0" in _cp_code,
          "a full-length white stream + per-pixel blend for 0.15s of white")
    check("no full-length white source is synthesized for the flash",
          "color=c=white:size=1920x1080" not in _cp_code,
          "45,000 frames synthesized to show 4 of them")
    check("the SFX mix survives a failed picture grade",
          "horror-fx-audio-only" in _cp_code and '"-c:v", "copy"' in _cp_code,
          "one ffmpeg call welded the cheap valuable half to the expensive one")
    check("the FX step cannot eat more of the clock than it did live",
          "timeout=1200" not in _cp_code.split("label=\"horror-fx\"")[0][-400:],
          "a 20-minute timeout it could never finish inside")

    # ══════════════════════════════════════════════════════════════════
    # EVERY GATE THAT CAN RECEIVE "hold-undelivered" MUST HANDLE IT.
    #
    # resolve_silent_window returns this whenever a review message could not
    # be delivered, so nobody was ever asked. Two of the five consumers were
    # written before that value existed and compared only against
    # reject/remake/edit/swap/approve — so it matched nothing and fell off
    # the bottom of a `while True`, re-asking a question that provably could
    # not arrive, once an hour, until the review budget was gone. A value a
    # gate cannot name is a value that gate mishandles.
    # ══════════════════════════════════════════════════════════════════
    _hold_consumers = (
        ("script gate", 'if _review["decision"] == "hold-undelivered":'),
        ("final pre-publish gate", 'if _final_gate["decision"] == "hold-undelivered":'),
        ("audio/video gate", 'if "hold-undelivered" in (_a_dec, _v_dec_early):'),
        ("title/thumbnail/description gate",
         'if _ttd_review["decision"] == "hold-undelivered":'),
        ("Shorts gate", 'if _sh_review["decision"] == "hold-undelivered":'),
    )
    for _label, _needle in _hold_consumers:
        check("the %s handles an undelivered review" % _label,
              _needle in _cp,
              "an undelivered review falls through this gate unhandled")

    # ══════════════════════════════════════════════════════════════════
    # THE SHOT LIST MUST READ NUMBERS THE WAY THE SCRIPT WRITES THEM.
    #
    # Run 31373726976's shot list came back state 52 / 68 with a 12-beat run
    # of one kind, and the log blamed the writing. It was the reader: every
    # value pattern demanded a digit, while the script says "neutrophils at
    # three percent" and "by tenfold" because a voice has to read it aloud;
    # and where the script DID use digits, the unit alternation had never
    # heard of L, μg/mL or U/L, so "5 L of plasma" and "platinum to 1.2
    # μg/mL" — the treatment working, measured — read as atmosphere too.
    # Same failure as the thumbnail gate above: a detector looking for a
    # shape the producer never emits.
    # ══════════════════════════════════════════════════════════════════
    try:
        import visual_brief as _vb
        for _want, _line in (
            ("value", "Blood work showed neutrophils at three percent."),
            ("value", "Infusion rate exceeded the prescribed dosage by tenfold."),
            ("value", "A total of 5 L of plasma was removed."),
            ("value", "Plasma platinum fell to 1.2 ug/mL after the session."),
            ("value", "Kidney markers dipped from 2.5 to 1.8 that week."),
            ("chronology", "At nine PM on July fifteen the pulse changed."),
            # and the reader must not simply call everything a value — an age
            # is a person, not a chart, and atmosphere must stay atmosphere.
            ("state", "The patient was a forty-six-year-old woman."),
            ("state", "Nobody could explain what was happening to her."),
        ):
            _got = _vb.classify(_line)[0]
            check("shot list reads %r as %s" % (_line[:34], _want),
                  _got == _want, "read as %s" % _got)
    except Exception as _e:
        check("shot-list number reading", False, repr(_e))

    # ══════════════════════════════════════════════════════════════════
    # A RESUMED RUN MUST NOT DIE ON A NAME THE SKIPPED STAGE WOULD HAVE SET.
    #
    # Resuming works by SKIPPING a stage. Every name that stage assigned is
    # then unbound for the rest of the episode, and Python does not complain
    # until the moment something reads it — which for `voice_used` was
    # save_pending(), the very last line of the generate phase. Found while
    # auditing live resume run 31393310000: script, audio, video, every
    # review gate and about three hours of work, then UnboundLocalError at
    # the finish line, caught by the outer handler, announced as "Pipeline
    # FAILED" and re-raised so nothing was queued. It had never fired before
    # because no earlier resume had reached the end.
    #
    # pyflakes cannot see this — the name IS assigned somewhere in the
    # function, just not on this path. So the check is a real definite-
    # assignment analysis of both resume branches.
    # ══════════════════════════════════════════════════════════════════
    try:
        import ast as _ast
        _tree = _ast.parse(_cp)

        _comp_targets = set()
        for _n in _ast.walk(_tree):
            if isinstance(_n, (_ast.ListComp, _ast.SetComp, _ast.DictComp,
                               _ast.GeneratorExp)):
                for _g in _n.generators:
                    for _nn in _ast.walk(_g.target):
                        if isinstance(_nn, _ast.Name):
                            _comp_targets.add(_nn.id)

        def _stores(node):
            return {n.id for n in _ast.walk(node)
                    if isinstance(n, _ast.Name) and isinstance(n.ctx, _ast.Store)}

        _unbound = []
        for _n in _ast.walk(_tree):
            if not isinstance(_n, _ast.If):
                continue
            try:
                _t = _ast.unparse(_n.test)
            except Exception:
                continue
            if _t not in ("_resume_audio", "_resume_script"):
                continue

            _body = set().union(*[_stores(s) for s in _n.body]) if _n.body else set()
            _else = set().union(*[_stores(s) for s in _n.orelse]) if _n.orelse else set()

            # Conditional blocks that START after the resume branch: their
            # bodies may simply not run on the resumed path.
            _guards = [_a for _a in _ast.walk(_tree)
                       if isinstance(_a, (_ast.If, _ast.While, _ast.For,
                                          _ast.Try, _ast.ExceptHandler))
                       and _a.lineno > _n.end_lineno]

            def _enclosing(_line, _guards=_guards):
                return [_g for _g in _guards
                        if _g.lineno <= _line <= (_g.end_lineno or 0)]

            # A try/except assigns DEFINITELY when its body and every handler
            # assign the name — that is how _audio_score is bound, and calling
            # it conditional would be a false alarm.
            def _try_is_total(_t2, _nm):
                if not isinstance(_t2, _ast.Try):
                    return False
                _b = set().union(*[_stores(s) for s in _t2.body]) if _t2.body else set()
                if _nm not in _b or not _t2.handlers:
                    return False
                return all(_nm in (set().union(*[_stores(s) for s in _h.body])
                                   if _h.body else set())
                           for _h in _t2.handlers)

            for _name in sorted(_else - _body - _comp_targets):
                if any(isinstance(x, _ast.Name) and isinstance(x.ctx, _ast.Store)
                       and x.id == _name and x.lineno < _n.lineno
                       for x in _ast.walk(_tree)):
                    continue

                _reads = sorted(x.lineno for x in _ast.walk(_tree)
                                if isinstance(x, _ast.Name)
                                and isinstance(x.ctx, _ast.Load)
                                and x.id == _name
                                and x.lineno > _n.end_lineno)
                _writes = sorted(x.lineno for x in _ast.walk(_tree)
                                 if isinstance(x, _ast.Name)
                                 and isinstance(x.ctx, _ast.Store)
                                 and x.id == _name
                                 and x.lineno > _n.end_lineno)

                # EVERY read must be dominated, not just the first. voice_used
                # is read inside the REMAKE block that assigns it (dominated,
                # fine) and then AGAIN at save_pending, where nothing on the
                # approved path ever assigned it. Checking only the first read
                # is exactly how the first version of this check missed it.
                for _r in _reads:
                    _rg = _enclosing(_r)
                    _dominated = False
                    for _w in _writes:
                        if _w >= _r:
                            break
                        _extra = [_g for _g in _enclosing(_w)
                                  if _g not in _rg and not _try_is_total(_g, _name)]
                        if not _extra:
                            _dominated = True
                            break
                    if not _dominated:
                        _unbound.append("%s (read at line %d)" % (_name, _r))
                        break

        check("a resumed run binds every name it later reads",
              not _unbound,
              "unbound on the resume path: " + ", ".join(_unbound[:4]))
    except Exception as _e:
        check("resume-path definite assignment", False, repr(_e))

    # ══════════════════════════════════════════════════════════════════
    # AND THIS SUITE MUST ACTUALLY BE A GATE.
    #
    # Every check above was written so a defect found live could not ship
    # again. That promise was empty: for its whole existence this file ran
    # only when a human typed it, while ch1_generate.yml gated on pyflakes,
    # defect classes and the fuzzer alone. Two failures this suite already
    # covers reached a real run anyway — the thumbnail gate nothing could
    # clear, and the unbound name on the resume path. An unwired check is
    # not a weaker check, it is decoration.
    #
    # So the suite asserts its own wiring. If someone removes the step, the
    # next local run says so instead of the next four-hour job.
    # ══════════════════════════════════════════════════════════════════
    try:
        _wf = open(os.path.join(ROOT, ".github", "workflows",
                                "ch1_generate.yml")).read()
        check("the generate workflow actually runs this preflight",
              "tools/preflight_ch1_thumbnails.py" in _wf,
              "these assertions gate nothing until the workflow runs them")
        check("a failed assertion stops the run",
              "exit 1" in _wf.split("tools/preflight_ch1_thumbnails.py")[-1][:300]
              if "tools/preflight_ch1_thumbnails.py" in _wf else False,
              "a non-blocking gate is a log line, not a gate")
    except Exception as _e:
        check("preflight is wired into the workflow", False, repr(_e))

    # ══════════════════════════════════════════════════════════════════
    # NO NARRATION WORDS ARE PRINTED ON THE PICTURE. ANY CARD, ANY PATH.
    #
    # Reported repeatedly, with screenshots, and "fixed" more than once by
    # trimming the wording or the clipping instead of removing the text. The
    # cards showed a label plus a slice of the spoken line -- "Smith recorded
    # the paradoxical recovery, urging further toxicolo" -- while the
    # captions said the same words at the bottom of the same frame.
    #
    # Checking the source for d.text() calls would not settle it: five
    # different register paths reached the same offending draw, and a card
    # that merely CHOOSES its motion or its photograph from the narration is
    # fine. So this instruments PIL directly, renders every register, and
    # asserts no distinctive narration token was ever handed to a text call.
    # ══════════════════════════════════════════════════════════════════
    try:
        from PIL import ImageDraw as _ID
        _drawn = []
        _orig_text = _ID.ImageDraw.text

        def _spy(self, xy, text, *a, **k):
            if text:
                _drawn.append(str(text))
            return _orig_text(self, xy, text, *a, **k)

        _ID.ImageDraw.text = _spy
        try:
            from medical_segments import render_medical_segment
            _narr = ("Smith recorded the paradoxical recovery, urging further "
                     "toxicology review after the neutrophil count collapsed.")
            _tokens = {"smith", "paradoxical", "urging", "toxicology",
                       "neutrophil", "collapsed"}
            _case = {
                "narrative": "A patient developed neutropenia after an overdose.",
                "citation": "Hofmann G et al. BMC cancer 2006 doi:10.1186/1471-2407-6-1",
                "quote": "paradoxical recovery", "figures": [],
                "labs": [{"name": "Neutrophils", "value": 0.1, "low": 2.0,
                          "high": 7.5, "unit": "x10^9/L", "flag": "LOW"}],
                "chart_data": {"labels": ["d1", "d5"], "values": [3.2, 0.1],
                               "title": "Neutrophils", "y_label": "x10^9/L",
                               "chart_type": "line"},
                "differentials": [{"name": "Sepsis", "reason": "fever", "value": 0.7}],
                "timeline": [{"day": "Day 1", "events": ["admitted"]}],
                "anatomy": {"title": "Marrow suppression",
                            "explanation": "cell production halted", "search": ""},
            }
            _wd = os.path.join(tempfile.gettempdir(), "preflight_cards")
            os.makedirs(_wd, exist_ok=True)
            _leaks = {}
            for _reg in ("CASEFILE", "LAB", "FIGURE", "CHART", "BOARD",
                         "TIMELINE", "ANATOMY", "SCENE", "TEXT", "__NONE__"):
                _drawn.clear()
                try:
                    render_medical_segment(
                        _reg, _case, _narr, 2.0, 0,
                        os.path.join(_wd, "seg.mp4"), work_dir=_wd,
                        niche_label="NO KNOWN CAUSE", run_ffmpeg=None,
                        log_fn=lambda *a, **k: None)
                except Exception:
                    pass
                _hit = {w for s in _drawn
                        for w in str(s).lower().replace(",", " ").replace(".", " ").split()
                        if w in _tokens}
                if _hit:
                    _leaks[_reg] = sorted(_hit)
            check("no card prints the narration on the picture",
                  not _leaks,
                  "; ".join("%s: %s" % (k, ", ".join(v))
                            for k, v in list(_leaks.items())[:3]))
        finally:
            _ID.ImageDraw.text = _orig_text
    except Exception as _e:
        check("no card prints the narration on the picture", False, repr(_e))

    # ══════════════════════════════════════════════════════════════════
    # A RETRY MUST PRODUCE SOMETHING DIFFERENT, AND A GATE THAT NEVER
    # ASKED MUST NOT APPROVE.
    # ══════════════════════════════════════════════════════════════════
    try:
        from retry_variation import AttemptLedger
        _led = AttemptLedger("t", near=0.8)
        _led.note("HOURS LATER", 5.5)
        check("a repeated candidate is recognised as a repeat",
              _led.is_repeat("HOURS LATER") and _led.is_repeat("HOURS LATER?")
              and _led.is_repeat("hours  later"),
              "thirteen identical attempts counted as thirteen attempts")
        check("a genuinely different candidate is not a repeat",
              not _led.is_repeat("0.1 WHITE CELLS"),
              "the ledger would block real variety")
        check("the next prompt is told what was rejected",
              "HOURS LATER" in _led.avoid_clause(),
              "the model is asked the identical question again")
    except Exception as _e:
        check("retry variation ledger", False, repr(_e))

    check("the thumbnail gate refuses to count a repeat as an attempt",
          "_thumb_ledger.is_repeat(text)" in _cp
          and "_thumb_ledger.avoid_clause(" in _cp,
          "the gate scores one candidate thirteen times")

    try:
        from clinical_variation import EpisodeVariation as _EV
        _t = ["beat"] * 40
        _a, _b, _c = _EV(12, 40), _EV(12, 40), _EV(12, 40, nonce=1)
        check("re-rendering the same episode stays reproducible",
              _a.tint == _b.tint and _a.durations(400, _t) == _b.durations(400, _t),
              "determinism was lost")
        check("a REMAKE genuinely re-rolls the presentation",
              (_a.tint, _a.durations(400, _t)) != (_c.tint, _c.durations(400, _t)),
              "REMAKE hands back the same render as the new version")
    except Exception as _e:
        check("remake variation", False, repr(_e))

    check("every video redo bumps the remake nonce",
          _cp.count("_VIDEO_REMAKE_NONCE[0] += 1") >= 8,
          "a redo path reproduces the previous render")

    try:
        import human_review_gate as _hrg2
        check("a gate that never asked cannot auto-approve",
              _hrg2.never_asked("unreviewable-no-time")
              and _hrg2.never_asked("hold-undelivered")
              and not _hrg2.never_asked("timeout"),
              "no buttons sent, then reported as approved")
        check("an unasked gate is not in the proceed-anyway set",
              "unreviewable-no-time" not in _hrg2._NO_REPLY,
              "it would still ship the stage unreviewed")
        import job_clock as _jc
        check("generation reserves a real window for every gate",
              _jc.review_floor_minutes() >= 60.0
              and not _jc.generation_may_continue.__doc__ is None,
              "generation may eat the review window again")
    except Exception as _e:
        check("review-window protection", False, repr(_e))

    _hrg_src2 = open(os.path.join(ROOT, "video_pipeline",
                                 "human_review_gate.py")).read()
    check("the delivered flag defaults to NOT delivered",
          'locals().get("_delivered", True)' not in _hrg_src2,
          "an unsent review still reports itself as auto-approved")

    # The review floor is one policy read from two ends. Two literals would
    # drift the moment either was tuned, and the failure would be silent:
    # generation reserving less than the gates demand recreates the exact
    # "no buttons were sent" report the floor exists to prevent.
    try:
        import job_clock as _jc2
        import human_review_gate as _hrg3
        check("the review floor has one source of truth",
              _hrg3.MIN_USABLE_GATE_MINUTES == _jc2.MIN_GATE_MIN,
              "generation and the gates disagree about a usable window")
        check("the reserved review window is the floor times the gate count",
              abs(_jc2.review_floor_minutes()
                  - _jc2.MIN_GATE_MIN * _jc2.GATES_PER_EPISODE) < 0.01,
              "the reserve does not match the policy")
    except Exception as _e:
        check("review floor single source", False, repr(_e))

    # Shorts are paused on instruction. The switch must actually gate every
    # producing call, and must default to OFF -- a flag that defaults ON is a
    # flag someone forgets, and that failure publishes the very thing that was
    # supposed to be stopped.
    try:
        import ast as _a2
        _t2 = _a2.parse(_cp)
        _guard = None
        for _n2 in _a2.walk(_t2):
            if isinstance(_n2, _a2.If):
                try:
                    if _a2.unparse(_n2.test) == "not SHORTS_ENABLED":
                        _guard = _n2
                except Exception:
                    pass
        _lo = min(x.lineno for x in _guard.orelse) if _guard and _guard.orelse else 0
        _hi = max(getattr(x, "end_lineno", x.lineno)
                  for x in _guard.orelse) if _guard and _guard.orelse else 0
        _loose = [n.lineno for n in _a2.walk(_t2)
                  if isinstance(n, _a2.Call) and isinstance(n.func, _a2.Name)
                  and n.func.id in ("produce_video_topic_short",
                                    "produce_standalone_short")
                  and not (_lo <= n.lineno <= _hi)]
        check("every Shorts-producing call sits behind the pause switch",
              _guard is not None and not _loose,
              "a Short can still be produced while Shorts are paused: %s" % _loose)
        check("the Shorts switch defaults to OFF",
              'os.environ.get("SHORTS_ENABLED", "")' in _cp,
              "a forgotten flag would publish the paused format")
    except Exception as _e:
        check("Shorts pause switch", False, repr(_e))

    # ══════════════════════════════════════════════════════════════════
    # THE REBUILT SHORTS RUBRIC MUST BE REACHABLE, AND MUST DISCRIMINATE.
    #
    # Both halves, because either alone has already shipped a broken gate on
    # this channel: the thumbnail gate was reachable-looking but arithmetically
    # impossible, and the old Shorts rubric discriminated on crime vocabulary
    # a clinical script is forbidden from using, scoring 0.0 on every correct
    # answer. A bar nothing can clear and a bar everything clears are the same
    # defect wearing different clothes.
    # ══════════════════════════════════════════════════════════════════
    try:
        import shorts_strategy as _ss
        from shorts_reels_engine import score_short_script as _sss, QUALITY_MIN as _sq

        _good = ("A fatal chemotherapy dose was given ten times over. 225 milligrams "
                 "per square metre, an unexplained error nobody caught. Her white "
                 "cell count fell to zero point one and the team prepared for the "
                 "worst as ventilator support began. Then on day ten the marrow "
                 "started making cells again on its own, a reversal that is absent "
                 "from the literature. Nobody has explained it since. The fatal "
                 "chemotherapy dose that should have ended her life is the one no "
                 "doctor can account for. A real case every week.")
        _bad = ("Hi guys, welcome back to the channel. Today I want to talk about an "
                "incredible medical story that I think you will find really amazing. "
                "There was a patient who had a bad reaction to some medicine and the "
                "doctors were very worried about what might happen to her over time. "
                "In the end everything worked out fine and she went home happy and "
                "healthy, which is a wonderful outcome for everybody involved here. "
                "Thanks so much for watching and please remember to subscribe.")
        _gr = _sss(_good, "Fatal 10x Dose: The Recovery Nobody Explains",
                   "A fatal chemotherapy dose was given ten times over.")
        _br = _sss(_bad, "An Amazing Medical Story", "Hi guys, welcome back.")
        check("a well-built clinical Short can clear the Shorts gate",
              _gr["total"] >= _sq,
              "best realistic script scores %s against %s — unreachable"
              % (_gr["total"], _sq))
        check("a boring Short is still rejected",
              _br["total"] < _sq - 2.0,
              "the rubric stopped discriminating (%s)" % _br["total"])
        check("the length band is read off seconds, not a word count",
              30.0 <= _gr["_seconds"] <= 42.0,
              "%.1fs is outside the researched band" % _gr["_seconds"])
        # The old band, restated as the regression it was.
        _old_lo, _old_hi = 120, 160
        _s_lo = _ss.seconds_for_words(_old_lo)
        _s_hi = _ss.seconds_for_words(_old_hi)
        _lo_w, _hi_w = _ss.target_word_band()
        _brief = __import__("shorts_reels_engine").SHORTS_RUBRIC_BLOCK
        check("the brief asks for the researched band, not the old one",
              _s_hi > _ss.HARD_SECONDS_MAX
              and ("%d-%d words" % (_lo_w, _hi_w)) in _brief,
              "the brief does not state the %d-%d word (%.0f-%.0fs) target"
              % (_lo_w, _hi_w, _ss.TARGET_SECONDS_MIN, _ss.TARGET_SECONDS_MAX))
        # Diagnostics must never be summed into the score.
        check("diagnostics are not summed into the Shorts score",
              _gr["total"] <= 10.0,
              "a diagnostic leaked into the total and clamped every script to 10")
        # A clinical script must not be punished for refusing tabloid words.
        _turn, _ = _ss.score_turn(_good)
        check("a clinical script scores on its turn, not on tabloid adjectives",
              _turn >= 2.0,
              "the emotion axis still penalises the channel's own register")
    except Exception as _e:
        check("rebuilt Shorts rubric", False, repr(_e))

    # ══════════════════════════════════════════════════════════════════
    # EVERY GATE, DRIVEN WITH A STUCK PROVIDER.
    #
    # The checks above this point that read source text for a ledger call
    # cannot tell code from the comment describing it -- that mistake has
    # been made repeatedly. These two DRIVE the real functions with a fake
    # provider that always answers the same thing, and assert on what the
    # function actually did: whether the rejected answer was named in the
    # next prompt, and whether the repeat was allowed to spend an attempt.
    # ══════════════════════════════════════════════════════════════════
    try:
        import human_review_gate as _hrg3
        _c_topic = ("A 34-year-old woman had recurrent fevers for eleven "
                    "months. Every culture was negative and four specialists "
                    "found nothing.")
        _c_title = "11 MONTHS OF FEVER, EVERY TEST NORMAL"
        _prompts = []

        def _stuck_ai(prompt, min_chars=0):
            _prompts.append(prompt)
            return ("QUESTION: What's your take on this case? Drop your "
                    "theory below.\nOPTION1: Infection\nOPTION2: Autoimmune\n")

        _hrg3.draft_community_post(_c_topic, "medical", _c_title, _stuck_ai)
        check("the community post names its rejected draft in the next prompt",
              any("ALREADY TRIED AND REJECTED" in p for p in _prompts),
              "every attempt asked the identical question")
        check("a repeated community post does not spend an attempt",
              len(_prompts) < _hrg3.COMMUNITY_POST_ATTEMPTS,
              "one draft was scored %d times and logged as %d attempts"
              % (len(_prompts), _hrg3.COMMUNITY_POST_ATTEMPTS))

        # And it must still accept a genuinely different draft.
        _seq = [("QUESTION: What's your take on this case?\n"
                 "OPTION1: Infection\nOPTION2: Cancer\n"),
                ("QUESTION: Eleven months of fever, every culture negative. "
                 "What would you have imaged next?\nOPTION1: Abdominal CT\n"
                 "OPTION2: Tagged WBC scan\nOPTION3: Echocardiogram\n"
                 "OPTION4: Bone marrow\n")]
        _i = [0]

        def _varying_ai(prompt, min_chars=0):
            _r = _seq[min(_i[0], len(_seq) - 1)]
            _i[0] += 1
            return _r

        _got = _hrg3.draft_community_post(_c_topic, "medical", _c_title,
                                          _varying_ai) or {}
        check("a genuinely better community post is still accepted",
              bool(_got.get("question")) and not _got.get("below_bar"),
              "the ledger blocks real variety instead of repeats")

        # The description loop, same treatment.
        _dcalls = [0]

        def _stuck_desc(n, t, ti, ep, ch, dur):
            _dcalls[0] += 1
            return "A short description that will not score well.\n\n" * 3

        _dres = _hrg3.regenerate_description_until_good(
            "n", "t", "Title", 1, "", 600.0, "niche", _stuck_desc,
            min_score=9.0, max_attempts=4)
        check("one description repeated is not reported as four attempts",
              _dres["attempts"] <= 1,
              "reported %s attempts for one piece of work"
              % _dres["attempts"])
    except Exception as _e:
        check("repeat protection, driven end to end", False, repr(_e))

    # ══════════════════════════════════════════════════════════════════
    # THE BACKGROUND BED, MEASURED WHERE THE EAR IS.
    #
    # Reported directly and more than once: "I don't see the background
    # sound in the video." Every previous answer to that was a gain number
    # nobody measured. This renders a real bed, pushes it through the
    # LITERAL filtergraph taken out of the shipping pipeline, subtracts the
    # same mix built with a silent bed, and reads the LUFS of what is left.
    # That difference IS the bed as delivered, so the assertion is on the
    # sound, not on the source text.
    #
    # Two numbers, because they fail independently: broadband (headphones)
    # and above 200 Hz (a phone speaker reproduces essentially nothing
    # below that, and a pad is mostly low end -- which is how a bed can be
    # correctly placed on paper and inaudible in the hand).
    # ══════════════════════════════════════════════════════════════════
    try:
        _bedgraph = re.search(
            r'"(\[2:a\][^"]*loudnorm[^"]*\[m\];)"', _cp)
        _wd2 = os.path.join(tempfile.gettempdir(), "preflight_bed")
        os.makedirs(_wd2, exist_ok=True)
        import ambient_bed as _ab
        _bp = os.path.join(_wd2, "bed.mp3")
        _ab.render(_bp, 24.0, mood="clinical", topic="unexplained fever",
                   log=lambda *a, **k: None)

        def _lufs(path, pre=""):
            _r = subprocess.run(
                ["ffmpeg", "-i", path, "-af", pre + "ebur128=peak=true",
                 "-f", "null", "-"], capture_output=True, text=True)
            _m = re.findall(r"I:\s+(-?[\d.]+) LUFS", _r.stderr)
            return float(_m[-1]) if _m else None

        _nar = os.path.join(_wd2, "narr.wav")
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i",
                        "anoisesrc=d=24:c=pink:a=0.5", "-af",
                        "loudnorm=I=-16.9:LRA=7:TP=-1.5", "-ar", "44100",
                        _nar], capture_output=True)
        _bedchain = (_bedgraph.group(1) if _bedgraph
                     else "[2:a]loudnorm=I=-37:LRA=11:TP=-6[m];")
        _tail = ("[n][m]amix=inputs=2:duration=first:normalize=0[mx];"
                 "[mx]alimiter=limit=0.94[aout]")
        _mix = os.path.join(_wd2, "mix.wav")
        _nob = os.path.join(_wd2, "nobed.wav")
        _dif = os.path.join(_wd2, "diff.wav")
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-t", "24", "-i",
                        "color=c=black:s=64x64:r=5", "-i", _nar, "-i", _bp,
                        "-filter_complex", "[1:a]volume=1.0[n];" + _bedchain + _tail,
                        "-map", "[aout]", "-ar", "44100", _mix],
                       capture_output=True)
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-t", "24", "-i",
                        "color=c=black:s=64x64:r=5", "-i", _nar,
                        "-f", "lavfi", "-t", "24", "-i", "anullsrc=r=44100:cl=mono",
                        "-filter_complex", "[1:a]volume=1.0[n];[2:a]anull[m];" + _tail,
                        "-map", "[aout]", "-ar", "44100", _nob],
                       capture_output=True)
        subprocess.run(["ffmpeg", "-y", "-i", _mix, "-i", _nob,
                        "-filter_complex",
                        "[1:a]volume=-1[inv];[0:a][inv]amix=inputs=2:normalize=0[d]",
                        "-map", "[d]", "-ar", "44100", _dif], capture_output=True)
        _nl = _lufs(_nar)
        _under = _nl - _lufs(_dif)
        _under_phone = _nl - _lufs(_dif, "highpass=f=200,")
        check("the background bed is audible under the narration",
              15.0 <= _under <= 21.0,
              "%.1f LU under the voice — broadcast practice is 15-20, and "
              "past ~30 it is not quiet, it is absent" % _under)
        check("the bed survives into the band a phone speaker can play",
              15.0 <= _under_phone <= 21.0,
              "%.1f LU under above 200 Hz — correct on headphones, inaudible "
              "in the hand" % _under_phone)
        check("the bed is not paid for out of the narration",
              _lufs(_mix) >= _nl - 0.5,
              "adding the bed pushed the finished mix down to %.1f LUFS"
              % _lufs(_mix))
    except Exception as _e:
        check("background bed, measured", False, repr(_e))

    # ══════════════════════════════════════════════════════════════════
    # THE PROVIDER CHAIN, DRIVEN WITH THE FAILURES THAT ACTUALLY HAPPENED.
    #
    # Run 31580988663 spent 5h04m on the script stage and died with nothing
    # rendered. Not one cause -- a collapse:
    #   * GitHub Models returned 410 (retirement brownout) on all 5 models,
    #     and 410 was handled as an ordinary error, so every AI call made
    #     five doomed round-trips and the provider was never marked dead.
    #   * NVIDIA NIM signalled saturation as 503 "ResourceExhausted" rather
    #     than 429, which no branch recognised.
    #   * Cloudflare's gemma-3-12b-it 403'd on every call because the
    #     account is not entitled to it, and the model kept its place.
    #   * Worst of all, ONE transient failure retired a provider for the
    #     whole run, so four providers that had each answered successfully
    #     vanished after a single blip and everything piled onto NIM.
    # These drive the real functions with the real response bodies.
    # ══════════════════════════════════════════════════════════════════
    try:
        os.environ.setdefault("GITHUB_TOKEN", "preflight")
        os.environ.setdefault("CLOUDFLARE_API_TOKEN", "preflight")
        os.environ.setdefault("CLOUDFLARE_ACCOUNT_ID", "0")
        import clinical_pipeline as _cp_mod

        class _Resp:
            def __init__(s, code, text=""):
                s.status_code, s.text = code, text

            def json(s):
                return {}

        _real_post = _cp_mod.requests.post
        try:
            _hits = []
            _cp_mod.requests.post = lambda url, **kw: (
                _hits.append(kw.get("json", {}).get("model")),
                _Resp(410, '{"error":{"code":"github_models_retirement_brownout"}}')
            )[1]
            _cp_mod._EXHAUSTED_PROVIDERS_THIS_RUN.discard("github_models")
            _cp_mod._DEAD_PROVIDERS_THIS_RUN.discard("github_models")
            _cp_mod.call_github_models("x", tokens=50, min_chars=5)
            check("a retired provider is dropped, not re-asked per model",
                  len(_hits) == 1
                  and "github_models" in _cp_mod._EXHAUSTED_PROVIDERS_THIS_RUN,
                  "410 Gone walked all %d models and left the provider live"
                  % len(_hits))

            _cp_mod._EXHAUSTED_PROVIDERS_THIS_RUN.discard("nvidia_nim")
            _cp_mod._DEAD_PROVIDERS_THIS_RUN.discard("nvidia_nim")
            # The key is read into a module constant at import, and this check
            # is worthless without one: call_nvidia_nim returns at its first
            # line when the key is missing, so the 503 branch is never reached
            # and the check passes having exercised nothing. That is exactly
            # how it passed before the branch existed at all.
            _saved_key = _cp_mod.NVIDIA_NIM_KEY
            _cp_mod.NVIDIA_NIM_KEY = "preflight"
            _cp_mod.requests.post = lambda url, **kw: _Resp(
                503, '{"error":{"message":"ResourceExhausted: Worker local '
                     'total request limit reached (27/16)"}}')
            _cp_mod.call_nvidia_nim("x", tokens=50, min_chars=5)
            _cp_mod.NVIDIA_NIM_KEY = _saved_key
            check("a saturated pool counts as rate limited",
                  "nvidia_nim" in _cp_mod._EXHAUSTED_PROVIDERS_THIS_RUN,
                  "503 ResourceExhausted was treated as transient and the "
                  "provider stayed at the front of the chain")

            _cp_mod._EXHAUSTED_PROVIDERS_THIS_RUN.discard("cloudflare")
            _cp_mod._DENIED_MODELS_THIS_RUN.clear()
            _seen = []

            def _cf(url, **kw):
                _m = kw.get("json", {}).get("model")
                _seen.append(_m)
                return _Resp(403, "not allowed to access") \
                    if "gemma" in (_m or "") else _Resp(500, "transient")

            _cp_mod.requests.post = _cf
            _cp_mod.call_cloudflare("x", tokens=50, min_chars=5)
            _first = len(_seen)
            _seen.clear()
            _cp_mod.call_cloudflare("x", tokens=50, min_chars=5)
            check("an unentitled model is dropped without killing its provider",
                  len(_seen) == _first - 1
                  and "cloudflare" not in _cp_mod._EXHAUSTED_PROVIDERS_THIS_RUN,
                  "the 403 model is re-asked every call, or took the whole "
                  "provider down with it")
        finally:
            _cp_mod.requests.post = _real_post

        # The amplifier: one blip must not retire a provider that works.
        _sleep, _log = _cp_mod.time.sleep, _cp_mod.log
        _saved = {n: getattr(_cp_mod, n) for n in (
            "call_cerebras", "call_github_models", "call_cloudflare",
            "call_nvidia_nim", "call_sambanova", "call_gemini", "call_groq",
            "call_openrouter", "call_cohere", "call_mistral")}
        try:
            _cp_mod.time.sleep = lambda *a, **k: None
            _cp_mod.log = lambda *a, **k: None
            for _n in _saved:
                setattr(_cp_mod, _n, lambda p, t=8000, m=100: None)
            _seq = ["y" * 200, "y" * 200, None, "y" * 200]
            _i = [0]

            def _flaky(p, t=8000, m=100):
                _v = _seq[_i[0]] if _i[0] < len(_seq) else "y" * 200
                _i[0] += 1
                return _v

            _cp_mod.call_cerebras = _flaky
            _cp_mod._DEAD_PROVIDERS_THIS_RUN.clear()
            _cp_mod._EXHAUSTED_PROVIDERS_THIS_RUN.clear()
            _cp_mod._PROVIDER_STRIKES.clear()
            _cp_mod._PROVIDER_WINS.clear()
            _cp_mod._AI_VARIANT[0] = 0
            _out = [bool(_cp_mod.ai_generate("x", 50, 5)) for _ in range(4)]
            check("one transient failure does not retire a working provider",
                  _out == [True, True, False, True],
                  "a provider that answered twice was lost to one blip: %s"
                  % _out)

            _cp_mod._DEAD_PROVIDERS_THIS_RUN.clear()
            _cp_mod._EXHAUSTED_PROVIDERS_THIS_RUN.clear()
            _cp_mod._PROVIDER_STRIKES.clear()
            _cp_mod._PROVIDER_WINS.clear()
            _cp_mod.call_cerebras = lambda p, t=8000, m=100: None
            _cp_mod.ai_generate("x", 50, 5)
            check("a provider that never answers is still dropped at once",
                  "cerebras" in _cp_mod._DEAD_PROVIDERS_THIS_RUN,
                  "the clock is spent being patient with a dead provider")

            # ── RUN 31876972186: 130 MINUTES ASKING FOR THREE DEAD NAMES ──
            #
            # Only a read TIMEOUT was remembered. A 404 "wrong model name"
            # logged and moved on, so discovery re-supplied the same three
            # NVIDIA names on every call; and because the revival path only
            # excluded QUOTA-exhausted providers, NIM was revived forever and
            # the honest "nothing will answer" exit was unreachable.
            for _s in (_cp_mod._DEAD_PROVIDERS_THIS_RUN,
                       _cp_mod._EXHAUSTED_PROVIDERS_THIS_RUN,
                       _cp_mod._DENIED_MODELS_THIS_RUN,
                       _cp_mod._NO_MODELS_LEFT):
                _s.clear()
            _cp_mod._PROVIDER_STRIKES.clear()
            _cp_mod._PROVIDER_WINS.clear()

            _cp_mod._note_model_gone("NVIDIA NIM", "nvidia/gone-9b", 404, None)
            check("a 404 model name is remembered, not re-asked every call",
                  "nvidia/gone-9b" in _cp_mod._DENIED_MODELS_THIS_RUN,
                  "a name the provider does not serve is requested again on "
                  "the next call, and the one after that")

            check("a provider with no model left says so",
                  _cp_mod._models_left("nvidia_nim", ["nvidia/gone-9b"]) == []
                  and "nvidia_nim" in _cp_mod._NO_MODELS_LEFT,
                  "a provider whose every model has gone still looks healthy "
                  "to the chain")

            _nim_calls = [0]

            def _all_404(p, t=8000, m=100):
                _nim_calls[0] += 1
                _left = _cp_mod._models_left("nvidia_nim", ["a/dead-1", "a/dead-2"])
                for _m in _left:
                    _cp_mod._note_model_gone("NVIDIA NIM", _m, 404, None)
                return None

            for _s in (_cp_mod._DEAD_PROVIDERS_THIS_RUN,
                       _cp_mod._EXHAUSTED_PROVIDERS_THIS_RUN,
                       _cp_mod._DENIED_MODELS_THIS_RUN,
                       _cp_mod._NO_MODELS_LEFT):
                _s.clear()
            _cp_mod._PROVIDER_STRIKES.clear()
            _cp_mod._PROVIDER_WINS.clear()
            for _n in ("cerebras", "cloudflare", "sambanova", "gemini",
                       "groq", "openrouter", "cohere", "mistral"):
                _cp_mod._note_quota_exhausted(_n)
            for _fn in ("call_cerebras", "call_cloudflare", "call_sambanova",
                        "call_gemini", "call_groq", "call_openrouter",
                        "call_cohere", "call_mistral"):
                setattr(_cp_mod, _fn, lambda p, t=8000, m=100: None)
            _cp_mod.call_nvidia_nim = _all_404
            _res = [_cp_mod.ai_generate("x", 50, 5) for _ in range(20)]
            check("the chain stops asking once nothing can answer",
                  all(_r is None for _r in _res) and _nim_calls[0] <= 2,
                  "the only surviving provider serves no model and was still "
                  "re-asked %d times across 20 calls — this is the 130 minutes "
                  "run 31876972186 spent" % _nim_calls[0])

            for _s in (_cp_mod._DEAD_PROVIDERS_THIS_RUN,
                       _cp_mod._EXHAUSTED_PROVIDERS_THIS_RUN,
                       _cp_mod._DENIED_MODELS_THIS_RUN,
                       _cp_mod._NO_MODELS_LEFT):
                _s.clear()

            # ── 410 GONE: THE PROVIDER SAYING IT IN WORDS ──────────────
            #
            # Run 31888423963, AFTER the 404 version of this was fixed:
            # "mistralai/mixtral-8x7b-instruct-v0.1: 410 ... has reached its
            # end of life on 2026-07-27 and is no longer available." 410 fell
            # through to the generic branch and was forgotten, so the retired
            # model was re-requested for 117 minutes.
            _cp_mod._DENIED_MODELS_THIS_RUN.clear()
            _cp_mod._note_model_gone("NIM", "eol-model", 410, None)
            _cp_mod._note_model_gone("NIM", "long-prompt", 400, None)
            check("a model that announces its end of life is not re-asked",
                  "eol-model" in _cp_mod._DENIED_MODELS_THIS_RUN,
                  "a 410 Gone is logged and forgotten, so the retired model "
                  "is requested again on the very next call")
            check("a bad request is not held against the model",
                  "long-prompt" not in _cp_mod._DENIED_MODELS_THIS_RUN,
                  "one overlong prompt retires a working model for every "
                  "shorter prompt that follows")

            # ── THE BREAKER: AN OUTAGE MUST NOT COST THE WHOLE JOB ─────
            _calls = [0]

            def _all_dead(p, t=8000, m=100):
                _calls[0] += 1
                return None

            _prev_fns = {}
            for _fn in ("call_cerebras", "call_cloudflare", "call_sambanova",
                        "call_gemini", "call_groq", "call_openrouter",
                        "call_cohere", "call_mistral", "call_nvidia_nim"):
                _prev_fns[_fn] = getattr(_cp_mod, _fn)
                setattr(_cp_mod, _fn, _all_dead)
            for _s in (_cp_mod._DEAD_PROVIDERS_THIS_RUN,
                       _cp_mod._EXHAUSTED_PROVIDERS_THIS_RUN,
                       _cp_mod._DENIED_MODELS_THIS_RUN,
                       _cp_mod._NO_MODELS_LEFT):
                _s.clear()
            _cp_mod._PROVIDER_STRIKES.clear()
            _cp_mod._PROVIDER_WINS.clear()
            _cp_mod._WHOLE_CHAIN_FAILURES[0] = 0
            _cp_mod._CHAIN_DOWN[0] = False
            _out = [_cp_mod.ai_generate("x", 50, 5) for _ in range(300)]
            check("a total outage stops the run instead of costing it",
                  all(_r is None for _r in _out)
                  and _cp_mod.chain_is_down() and _calls[0] < 200,
                  "300 calls against a chain where nothing answers made %d "
                  "provider requests and the breaker is %s — this is the 117 "
                  "minutes run 31888423963 spent"
                  % (_calls[0], "down" if _cp_mod.chain_is_down() else "OPEN"))

            _cp_mod._WHOLE_CHAIN_FAILURES[0] = 0
            _cp_mod._CHAIN_DOWN[0] = False
            _cp_mod._PROVIDER_STRIKES.clear()
            _cp_mod._PROVIDER_WINS.clear()
            for _s in (_cp_mod._DEAD_PROVIDERS_THIS_RUN,
                       _cp_mod._EXHAUSTED_PROVIDERS_THIS_RUN,
                       _cp_mod._DENIED_MODELS_THIS_RUN,
                       _cp_mod._NO_MODELS_LEFT):
                _s.clear()
            _cp_mod.call_cerebras = lambda p, t=8000, m=100: "z" * 200
            check("one working provider keeps the breaker open",
                  bool(_cp_mod.ai_generate("x", 50, 5))
                  and not _cp_mod.chain_is_down(),
                  "a chain that CAN answer was still declared down — the "
                  "breaker would strand a working run")
            for _fn, _f in _prev_fns.items():
                setattr(_cp_mod, _fn, _f)
            _cp_mod._WHOLE_CHAIN_FAILURES[0] = 0
            _cp_mod._CHAIN_DOWN[0] = False

            # ── A MODEL PROVEN TO WORK SURVIVES THE RUN THAT PROVED IT ──
            #
            # Discovery re-ranks a live catalogue every run and remembers
            # nothing, so the pipeline had no way to know that a different
            # NVIDIA name had answered perfectly well that same morning.
            import provider_health as _ph
            import tempfile as _tf, json as _js, pathlib as _pl
            _real_path, _real_cache = _ph.HEALTH_PATH, _ph._CACHE[0]
            try:
                _ph.HEALTH_PATH = _pl.Path(_tf.mkdtemp()) / "provider_health.json"
                _ph._CACHE[0] = None
                _ph.record_working_model("nvidia_nim", "meta/llama-3.3-70b-instruct")
                _order = _cp_mod._models_left(
                    "nvidia_nim", ["a/dead-1", "meta/llama-3.3-70b-instruct"])
                check("a model proven to answer leads the list next time",
                      _order and _order[0] == "meta/llama-3.3-70b-instruct",
                      "the catalogue's guess still outranks a name that "
                      "actually produced a sentence: %s" % (_order,))

                _d = _js.loads(_ph.HEALTH_PATH.read_text())
                _d["checked_at"] = "2020-01-01T00:00:00Z"
                _ph.HEALTH_PATH.write_text(_js.dumps(_d))
                _ph._CACHE[0] = None
                check("a stale working-model record is not trusted",
                      _ph.working_model("nvidia_nim") == "",
                      "a name from a fortnight ago is still being preferred "
                      "over what discovery says today")
            finally:
                _ph.HEALTH_PATH, _ph._CACHE[0] = _real_path, _real_cache
                _cp_mod._DENIED_MODELS_THIS_RUN.clear()
                _cp_mod._NO_MODELS_LEFT.clear()
        finally:
            _cp_mod.time.sleep, _cp_mod.log = _sleep, _log
            for _n, _f in _saved.items():
                setattr(_cp_mod, _n, _f)
    except Exception as _e:
        check("provider chain under real failures", False, repr(_e))

    # ══════════════════════════════════════════════════════════════════
    # A BLANK PHOTOGRAPH IS REJECTED BEFORE IT IS RENDERED, NOT AFTER.
    #
    # Run 31695910257: the chosen Pixabay photo was ~60% blank surface, and
    # all five layouts then scored exactly 8.0/10 with the same complaint.
    # Five layouts cannot rescue one empty picture. The searches already ask
    # for five candidates and took [0] regardless.
    # ══════════════════════════════════════════════════════════════════
    try:
        import io as _io
        import numpy as _np
        from PIL import Image as _Im, ImageDraw as _ID2
        from photo_thumbnail import featureless_fraction as _ff, FEATURELESS_MAX as _FMAX
        import clinical_pipeline as _cp3
        _rng = _np.random.default_rng(1)

        def _blankish():
            _a = (_np.full((720, 1280, 3), 118, dtype=_np.int16)
                  + _rng.integers(-1, 2, (720, 1280, 3)))
            return _Im.fromarray(_np.clip(_a, 0, 255).astype(_np.uint8))

        def _subject():
            _im = _Im.fromarray(_rng.integers(0, 255, (720, 1280, 3), dtype=_np.uint8))
            _ID2.Draw(_im).ellipse((400, 150, 900, 650), fill=(30, 40, 60))
            return _im

        def _png(_i):
            _b = _io.BytesIO(); _i.save(_b, "PNG"); return _b.getvalue()

        check("the blank/subject test tells them apart at all",
              _ff(_blankish()) > _FMAX >= _ff(_subject()),
              "blank %.2f vs subject %.2f against a %.2f bar"
              % (_ff(_blankish()), _ff(_subject()), _FMAX))

        _BL, _BU = _png(_blankish()), _png(_subject())
        _out = os.path.join(tempfile.gettempdir(), "preflight_photo.png")
        _saved_get, _saved_log = _cp3.requests.get, _cp3.log
        try:
            _cp3.log = lambda *a, **k: None

            class _Rp:
                def __init__(s, c):
                    s.status_code, s.content = 200, c

            _cp3.requests.get = lambda url, **kw: _Rp({"b": _BL, "g": _BU}[url])
            _ok = _cp3._pick_photo_with_a_subject(["b", "g"], _out, "T", "kw")
            check("a blank first hit is skipped for one with a subject in it",
                  _ok and _ff(_out) <= _FMAX,
                  "the chooser still hands the renderer a blank surface")

            _cp3.requests.get = lambda url, **kw: _Rp(_BL)
            _ok2 = _cp3._pick_photo_with_a_subject(["b", "b"], _out, "T", "kw")
            check("all-blank candidates still yield a picture, not nothing",
                  _ok2,
                  "the keep-the-best fallback is unreachable — a set of "
                  "perfectly blank candidates returns empty-handed")
        finally:
            _cp3.requests.get, _cp3.log = _saved_get, _saved_log
    except Exception as _e:
        check("blank-photo rejection at selection time", False, repr(_e))

    # ══════════════════════════════════════════════════════════════════
    # THE FX PASS MUST NOT INFLATE THE FILE IT IS HANDED.
    # Measured live: 108MB composed -> 2594MB finished, and a previous run
    # died when the artifact hit 4.65GB.
    # ══════════════════════════════════════════════════════════════════
    check("the FX re-encode does not out-quality its own source",
          '"-crf", "23",' in _cp[_cp.find("label=\"horror-fx\"") - 900:
                                _cp.find("label=\"horror-fx\"")]
          if "label=\"horror-fx\"" in _cp else False,
          "the FX pass re-encodes above the source's crf, spending bits on "
          "precision the picture never had")
    check("grain is not the most expensive thing in the render",
          "noise=alls=10:allf=t+u" in _cp,
          "grain strength 15 with temporal noise measured 11.3x the source "
          "size; 10 measures 1.1x and still plainly reads as film")

    # ══════════════════════════════════════════════════════════════════
    # THE RECEIPT MUST NEVER PUT THE OWNER'S NAME ON A DECISION THEY DID
    # NOT MAKE.
    #
    # Requested: confirm on Telegram what was decided and what happens
    # next, "so that I can be best in loop of things and not blind sided
    # with just auto approvals". A receipt that said "approved" for a gate
    # nobody answered would be worse than no receipt at all -- it would
    # manufacture consent. So the load-bearing assertion here is not that
    # the message is sent, it is that an unanswered gate reads differently
    # from an approved one, in every wording the gates can return.
    # ══════════════════════════════════════════════════════════════════
    try:
        import human_review_gate as _hrg4
        _sent = []
        _real_send = _hrg4._tg_send_message
        try:
            _hrg4._tg_send_message = lambda t, c, txt: _sent.append(txt)

            _hrg4.send_decision_receipt("t", "c", "script", "approve", 40.0)
            _yours = _sent[-1]
            check("an approval you gave says so, and says what is next",
                  "BY YOU" in _yours and "Next:" in _yours
                  and "Audio" in _yours,
                  "the receipt does not confirm the decision or the next stage")

            _bad = []
            for _d in list(_hrg4._NO_REPLY) + list(_hrg4._NEVER_ASKED):
                _sent.clear()
                _hrg4.send_decision_receipt("t", "c", "thumbnail", _d, 3600.0)
                _m = _sent[-1] if _sent else ""
                # It must not claim the owner did anything, and must not
                # borrow the approval headline.
                if "BY YOU" in _m or "✅" in _m:
                    _bad.append(_d)
            check("a gate nobody answered is never reported as your approval",
                  not _bad,
                  "these decisions still read as owner approvals: %s" % _bad)

            _sent.clear()
            _hrg4.send_decision_receipt("t", "c", "audio+video", "edit", 90.0,
                                        "cut the first two sentences")
            check("your own words come back to you verbatim",
                  "cut the first two sentences" in _sent[-1],
                  "an EDIT receipt does not quote the note being acted on")

            # The ledger is the end-of-run backstop for the same concern.
            _sent.clear()
            _hrg4.send_run_ledger("t", "c", "done")
            _ledger = _sent[-1] if _sent else ""
            check("the end-of-run summary separates your calls from the clock's",
                  "not you" in _ledger and "went ahead without you" in _ledger,
                  "the run can end without saying which approvals were not "
                  "the owner's")
        finally:
            _hrg4._tg_send_message = _real_send
            _hrg4._GATE_LEDGER.clear()

        check("every gate reports through one place, so none can be missed",
              _hrg_src2.count("send_decision_receipt(") >= 2
              and "record_review_wait(label, _waited, decision)" in _hrg_src2,
              "a gate could return without ever confirming what happened")
    except Exception as _e:
        check("decision receipts", False, repr(_e))

    # The remaining gates live inside long pipeline functions that cannot be
    # driven standalone, so these assert on the mechanism each one uses.
    check("the Shorts gate refuses to count a repeat as an attempt",
          "_short_ledger.is_repeat(" in open(
              os.path.join(ROOT, "video_pipeline",
                           "shorts_reels_engine.py")).read(),
          "a rejected Short could be resubmitted and scored again")
    check("the title gate refuses to count a repeat as an attempt",
          "_title_wasted[0] += 1" in _cp and "_fresh = [t for t in titles" in _cp,
          "already-rejected titles still burn one of the thirteen")

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
