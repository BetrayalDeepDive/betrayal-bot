#!/usr/bin/env python3
"""
Render one full episode's VISUAL SEQUENCE locally and look at it.

WHY THIS EXISTS
---------------
Five live runs and roughly ten hours of CI compute went into this channel
without a single frame of real output ever being inspected. That is how an
episode about a newborn's liver failure shipped illustrated with a mountain
and a woman dancing: every fix was reasoned from logs and from renderers
tested in isolation, never from the finished sequence a viewer actually sees.

This harness reproduces the pipeline's per-segment visual loop exactly --
same bucket split, same lowercasing, same RegisterQuota, same
render_medical_segment call with the same progress value -- against a
realistic case, and writes every still plus contact sheets so the whole
episode can be judged as a viewer would judge it.

It deliberately does NOT stub the renderers. The only substitutions are the
two things this sandbox cannot reach:
  * the PMC figure download (network policy blocks ebi.ac.uk / ncbi), so a
    local placeholder image stands in for the downloaded figure -- layout,
    caption and CC BY credit placement are still the real code paths
  * the Wikimedia anatomy lookup, same reason
Both are reported in the run summary so nothing is silently assumed.

Usage:  python3 tools/local_episode_render.py [outdir]
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "video_pipeline"))

from PIL import Image, ImageDraw, ImageFilter  # noqa: E402
import random  # noqa: E402

import medical_figure_render as mfr           # noqa: E402
from medical_register import new_quota        # noqa: E402
import medical_segments as ms                 # noqa: E402


# ── the fixture case ────────────────────────────────────────────────────
# Shaped exactly like what clinical_pipeline builds: pmc_data.get_real_case()
# output plus the five structures the extraction step adds (differentials,
# timeline, chart_data, anatomy, quote). Values are representative of a real
# published CC BY case report; the point of the harness is the RENDERING, so
# what matters is that every field has the shape and the length the real
# pipeline produces.
CASE = {
    "pmcid": "PMC0000000",
    "journal": "Journal of Medical Case Reports",
    "year": "2023",
    "title": "Acute liver failure in a neonate following a rare inherited "
             "disorder of galactose metabolism",
    "citation": ("Okonkwo A, Vasquez M, Lindqvist P. Acute liver failure in a "
                 "neonate following a rare inherited disorder of galactose "
                 "metabolism. J Med Case Rep. 2023;17:214. CC BY 4.0."),
    "narrative": "(fixture)",
    "figures": [
        {"pmcid": "PMC0000000", "filename": "fig1.jpg", "label": "Figure 1",
         "caption": "Abdominal ultrasound on day three showing a diffusely "
                    "echogenic liver with preserved portal flow and no biliary "
                    "dilatation."},
        {"pmcid": "PMC0000000", "filename": "fig2.jpg", "label": "Figure 2",
         "caption": "Peripheral blood film demonstrating marked anisocytosis "
                    "and occasional target cells."},
        {"pmcid": "PMC0000000", "filename": "fig3.jpg", "label": "Figure 3",
         "caption": "Serial serum galactose-1-phosphate concentrations from "
                    "admission to day twenty-one of life."},
    ],
    "differentials": [
        ("Neonatal sepsis", "EXCLUDED",
         "Blood and urine cultures were sterile at forty-eight hours"),
        ("Biliary atresia", "EXCLUDED",
         "Ultrasound showed a normal gallbladder and no biliary dilatation"),
        ("Tyrosinaemia type 1", "PARTIAL",
         "Succinylacetone was requested but returned within normal limits"),
        ("Classic galactosaemia", "CONFIRMED",
         "GALT enzyme activity was undetectable in erythrocytes"),
    ],
    "timeline": [
        ("Day 2", "Poor feeding and jaundice noted on the postnatal ward"),
        ("Day 3", "Conjugated bilirubin rose to one hundred and forty micromoles per litre"),
        ("Day 4", "Coagulopathy developed; INR reached two point eight"),
        ("Day 6", "Galactose-free formula started empirically"),
        ("Day 9", "GALT enzyme assay returned undetectable"),
        ("Day 21", "Liver function normalised; discharged on dietary management"),
    ],
    "chart_data": {
        "chart_type": "line",
        "title": "Serum galactose-1-phosphate",
        "y_label": "micromoles per litre of red cells",
        "labels": ["Day 3", "Day 6", "Day 9", "Day 12", "Day 16", "Day 21"],
        "values": [1240, 980, 610, 340, 180, 95],
    },
    "anatomy": {
        "title": "Galactose-1-phosphate uridylyltransferase",
        "explanation": "Without this enzyme, galactose-1-phosphate accumulates "
                       "inside liver and kidney cells and poisons them from the "
                       "inside. The sugar itself is harmless; the half-finished "
                       "product of breaking it down is not.",
        "search": "galactose metabolism pathway",
        "pathway": ["Lactose in milk", "Galactose", "Galactose-1-phosphate",
                    "Glucose-1-phosphate"],
        "blocked_step": 3,
    },
    "quote": ("The infant's deterioration continued despite antibiotics, and it "
              "was the absence of infection rather than its presence that "
              "redirected the investigation."),
}


# ── the fixture narration ───────────────────────────────────────────────
# ~1,600 words, matching the length and register of what the script gate
# actually passes (run 30578466862 shipped 1,613 words). Segment CONTENT is
# what drives classify_hint(), so this has to be real prose, not lorem.
NARRATION = """
On the second day of her life, a baby girl in a postnatal ward stopped
feeding. Nothing about that is rare. Newborns tire, newborns refuse, and
tired mothers are told, gently and constantly, that this is normal. What was
not normal was what her blood looked like ninety-six hours later, when a
junior doctor held the results up to the light and realised that the child in
front of her was, in the most literal sense, being poisoned by milk.

This is a documented case, published in a peer-reviewed journal under an open
licence, and everything that follows is drawn from that published record.

She was born at term, after an uncomplicated pregnancy, weighing three
kilograms and two hundred grams. Her first day was unremarkable. On day two
the midwives noted that she was jaundiced and that she was feeding poorly.
Jaundice in a newborn is so common that it is almost a rite of passage; in
most infants it reflects an immature liver clearing the pigment left over from
foetal red cells, and it resolves without anyone doing anything at all.

The distinction that mattered here, and the distinction that most people
outside medicine have never had reason to learn, is between two different
kinds of jaundice. Unconjugated jaundice is the ordinary kind. Conjugated
jaundice is not. When the conjugated fraction rises, the liver has already
processed the pigment and then failed to excrete it, which means the problem
is not immaturity. It is obstruction, or it is damage.

On day three her conjugated bilirubin was one hundred and forty micromoles per
litre. That single number moved her from a routine postnatal review to a
paediatric ward with an intravenous line in the back of her hand.

The first working diagnosis was sepsis. It almost always is. A newborn who
feeds poorly, looks jaundiced and feels subtly wrong is treated as infected
until proven otherwise, because the cost of being wrong in that direction is
measured in hours. Broad-spectrum antibiotics were started within forty
minutes of the decision being made. Blood cultures, urine cultures and a
lumbar puncture were sent.

By day four she was worse. Her INR, a measure of how quickly her blood could
form a clot, had climbed to two point eight. The liver manufactures nearly all
the clotting factors in circulation, so a rising INR in an infant who has been
given vitamin K is not a clotting problem. It is a liver that has stopped
building things.

Her transaminases were elevated. Her blood glucose was low, repeatedly, in a
pattern that required a continuous infusion to correct. And the cultures, at
forty-eight hours, were sterile.

It is worth pausing on that, because it is the hinge of the whole case. The
antibiotics were not working, and the reason they were not working was that
there was nothing there for them to work on. The team had been treating an
infection that did not exist.

The investigation reopened. An abdominal ultrasound was performed on day
three and repeated on day five. It showed a diffusely echogenic liver, which
is the sonographer's way of describing tissue that is reflecting sound more
brightly than it should because something has accumulated inside the cells.
The gallbladder was present and normal. There was no dilatation of the bile
ducts.

That finding excluded biliary atresia, which had been high on the list.
Biliary atresia is a progressive obliteration of the bile ducts, and in a
jaundiced infant it is the diagnosis nobody wants to miss, because the surgery
that treats it works far better before sixty days of life than after. Normal
ducts on imaging, with a visible gallbladder, made it very unlikely.

Tyrosinaemia type one was the next candidate. It produces liver failure and
coagulopathy in early infancy, and it is treatable, which is precisely why it
is looked for. A urine sample was sent for succinylacetone. It came back
within normal limits.

Which left the metabolic screen, and one enzyme in particular.

Galactose is one half of lactose, the sugar in every drop of milk the child
had swallowed since birth. To use it, the body converts it through a short
chain of reactions. The second step in that chain is performed by an enzyme
with an unwieldy name: galactose-one-phosphate uridylyltransferase, usually
shortened to GALT. In classic galactosaemia, that enzyme is absent.

The consequence is not that galactose goes unused. The consequence is that the
reaction stops halfway. Galactose-one-phosphate, the intermediate, accumulates
inside liver cells, kidney tubules and the lens of the eye, and at high
concentrations it is directly toxic to them. The sugar itself is harmless. The
half-finished product of breaking it down is not.

This is why the presentation is so consistent, and so cruel in its timing. A
child with classic galactosaemia is entirely well in the womb, because the
mother's circulation handles the clearance. The illness begins with the first
feed, and it worsens with every subsequent one. The treatment the ward was
providing, milk, was the exposure.

Her erythrocyte GALT activity was undetectable.

The team did not wait for that result. On day six, with sepsis excluded and
the metabolic screen still pending, they stopped milk entirely and started a
soya-based, galactose-free formula. This is standard practice in a deteriorating
infant with unexplained liver dysfunction, and it is one of the few
interventions in medicine where the empirical trial is close to risk-free.

Her clinical course turned within seventy-two hours. Her INR fell. Her glucose
stabilised. Her conjugated bilirubin, which had been climbing steadily since
day two, peaked and began to decline. Serial measurements of
galactose-one-phosphate in her red cells traced the same curve in reverse:
twelve hundred and forty micromoles per litre on day three, six hundred and
ten by day nine, ninety-five by day twenty-one.

By day nine, when the enzyme assay returned, the diagnosis was a confirmation
rather than a discovery. She was discharged on day twenty-one with normal liver
function and a lifelong dietary restriction.

The published discussion is careful about what this case does and does not
demonstrate. It is not an argument that sepsis should be treated less
aggressively in newborns; the authors are explicit that empirical antibiotics
were correct at the time they were given. Their argument is narrower and more
useful. It is that a negative result is information, and that forty-eight
sterile hours in an infant who is still deteriorating should trigger a
different question rather than a longer course of the same answer.

Most developed countries now screen newborns for galactosaemia in the first
days of life, before symptoms appear. In the health system where this child was
born, it was not on the panel. Her diagnosis therefore depended on a team
noticing that their own treatment was not working, and asking why, rather than
waiting.

She is one child, in one paper, in one journal. But the reason a case like this
gets published at all is that the sequence is repeatable: the ordinary finding,
the reasonable first diagnosis, the negative result that everyone hoped would
be positive, and the reversal that came from taking that negative seriously.

That is what the record shows.
""".strip()


# ── stand-ins for the two network-dependent assets ──────────────────────
def make_placeholder_figure(path, kind, seed):
    """
    A locally generated stand-in for a downloaded PMC figure.

    NOT an attempt to fake a scan. Its only job is to be a real image file of
    a realistic size and aspect so render_figure_frame() composes the frame
    the way it will in production -- panel sizing, caption wrap, credit line.
    Clearly watermarked so no frame from this harness can be mistaken for
    real output.
    """
    rnd = random.Random(seed)
    if kind == "portrait":
        w, h = 780, 1040
    elif kind == "wide":
        w, h = 1400, 620
    else:
        w, h = 900, 900
    img = Image.new("L", (w, h), 18)
    d = ImageDraw.Draw(img)
    for _ in range(90):
        cx, cy = rnd.randrange(w), rnd.randrange(h)
        r = rnd.randrange(20, 190)
        v = rnd.randrange(40, 210)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=v)
    img = img.filter(ImageFilter.GaussianBlur(9))
    img = img.convert("RGB")
    d = ImageDraw.Draw(img)
    d.text((16, h - 30), "LOCAL PLACEHOLDER - NOT A REAL FIGURE",
           font=mfr._font(20, False), fill=(255, 90, 90))
    img.save(path)
    return path


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1
               else "/tmp/episode_render")
    work = out / "work"
    work.mkdir(parents=True, exist_ok=True)

    notes = []

    # Pre-place the "downloaded" figures where render_medical_segment expects
    # them, so the download is skipped rather than mocked.
    figs = CASE["figures"]
    for i, kind in enumerate(("portrait", "square", "wide")[:len(figs)]):
        make_placeholder_figure(work / f"pmcfig_{i}.jpg", kind, seed=i)
    notes.append(f"{len(figs)} placeholder figure images pre-staged "
                 "(network policy blocks the real PMC download here)")

    # Kill the Wikimedia lookup: unreachable in this sandbox, and letting it
    # fail silently would misrepresent ANATOMY as always-procedural.
    import real_case_images
    real_case_images.search_wikimedia_commons = lambda *a, **k: (False, "")
    notes.append("Wikimedia anatomy lookup disabled (unreachable here) -- "
                 "ANATOMY frames show the procedural diagram")

    # ── reproduce the pipeline's bucket split exactly ───────────────────
    audio_duration = 1613 / 110.0 * 60.0        # WPM 110, run-4 word count
    TARGET_SECONDS_PER_CLIP = 15.0
    n_buckets = int(round(audio_duration / TARGET_SECONDS_PER_CLIP))
    n_buckets = max(55, min(65, n_buckets))
    words = NARRATION.split()
    total = len(words)
    bucket_words = max(1, total // n_buckets)
    segment_dur = audio_duration / n_buckets

    print(f"words={total}  audio={audio_duration:.0f}s  buckets={n_buckets}  "
          f"seg={segment_dur:.1f}s")

    quota = new_quota(n_buckets, figure_count=len(figs), case=CASE)
    print("mix:", {k: round(v, 3) for k, v in quota.mix.items() if v > 0})

    seq = []
    for i in range(n_buckets):
        start = i * bucket_words
        end = min(start + bucket_words, total)
        stage_display = " ".join(words[start:end])
        stage_text = stage_display.lower()      # pipeline lowercases for matching
        register = quota.pick(stage_text)
        occ, exp = quota.reveal(register)
        still = work / f"med_{i}_{register.lower()}.png"

        if register == "TEXT":
            ok = ms.render_text_still(
                CASE.get("quote") or "", str(still),
                attribution=ms.short_credit(CASE.get("citation", "")))
            if not ok:
                ok = ms.render_last_resort_still(stage_display, str(still),
                                                 citation=CASE["citation"])
        else:
            ok = _render_still_only(register, stage_display, i, still,
                                    progress=occ / max(1, exp), variant=occ - 1,
                                    variant_total=exp)
        seq.append((i, register, still if ok else None, stage_display))
        print(f"  {i:02d} {register:8s} {occ}/{exp} {'ok' if ok else 'FAILED'}")

    _contact_sheets(seq, out)
    _report(seq, quota, out, notes)


def _render_still_only(register, stage_text, index, still, progress, variant,
                       variant_total):
    """
    render_medical_segment() minus the ffmpeg clip step, so 60 stills render
    in seconds instead of minutes. Same dispatch, same arguments, same
    fallback behaviour -- the clip step is exercised separately on a sample.
    """
    from unittest import mock
    with mock.patch.object(ms, "still_to_clip", return_value=True):
        return ms.render_medical_segment(
            register, CASE, stage_text, 15.0, index,
            str(still.with_suffix(".mp4")), work_dir=str(still.parent),
            log_fn=lambda m: print("     " + m.strip()),
            progress=progress, variant=variant,
            variant_total=variant_total)


def _contact_sheets(seq, out):
    """Six 10-up sheets: the whole episode, in order, at a glance."""
    cols, rows = 5, 2
    tw, th = 480, 270
    per = cols * rows
    for s in range(0, len(seq), per):
        chunk = seq[s:s + per]
        sheet = Image.new("RGB", (cols * tw, rows * th), (8, 10, 12))
        d = ImageDraw.Draw(sheet)
        for k, (i, reg, path, _txt) in enumerate(chunk):
            x, y = (k % cols) * tw, (k // cols) * th
            if path and Path(path).exists():
                sheet.paste(Image.open(path).resize((tw, th)), (x, y))
            d.rectangle([x, y, x + tw - 1, y + th - 1],
                        outline=(60, 60, 60), width=1)
            d.text((x + 8, y + 6), f"{i:02d} {reg}",
                   font=mfr._font(20), fill=(255, 210, 90))
        p = out / f"sheet_{s // per + 1}.png"
        sheet.save(p)
        print("sheet ->", p)


def _report(seq, quota, out, notes):
    from collections import Counter
    regs = [r for _i, r, _p, _t in seq]
    counts = Counter(regs)
    longest, cur = 1, 1
    for a, b in zip(regs, regs[1:]):
        cur = cur + 1 if a == b else 1
        longest = max(longest, cur)
    failed = [i for i, _r, p, _t in seq if p is None]
    lines = [
        "LOCAL EPISODE RENDER",
        f"segments        : {len(seq)}",
        f"realised mix    : {dict(counts)}",
        f"longest run     : {longest} consecutive identical registers",
        f"failed to render: {failed or 'none'}",
        "",
        "substitutions:",
        *[f"  - {n}" for n in notes],
    ]
    txt = "\n".join(lines)
    (out / "report.txt").write_text(txt)
    print("\n" + txt)


if __name__ == "__main__":
    main()
