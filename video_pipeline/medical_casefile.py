"""
The case-file opening card.

WHY
---
The channel had no signature opening. Segment zero was a title card and then
whatever register the quota scheduled next, so nothing told a returning
viewer they were watching the same series. Every documentary strand that
works has an opening move you recognise before the narration starts.

A published case report opens the same way every time — a patient, an age, a
presentation, a clock starting — so the card writes itself from the paper.

THE RULE THAT SHAPES THIS FILE
------------------------------
Every field is either extracted from the paper's own text or shown as NOT
STATED. Nothing is inferred, averaged, or filled in for looks. On a medical
channel a plausible invented age is worse than a blank: it is a fabricated
clinical detail presented as a fact from a cited source, and the citation
makes it look verified. So the extractors below are deliberately narrow —
they match the phrasings case reports actually use, and return nothing when
they are not sure.
"""
import re

from PIL import Image, ImageDraw

import medical_figure_render as mfr

W, H = 1920, 1080
BG = mfr.BG
PANEL = mfr.PANEL
EDGE = mfr.PANEL_EDGE
ACCENT = mfr.ACCENT
TEXT = mfr.TEXT
DIM = mfr.TEXT_DIM
ALERT = (196, 88, 78)

NOT_STATED = "NOT STATED"

# ── extraction ─────────────────────────────────────────────────────────
# "a 54-year-old man", "a 7-month-old infant", "aged 61 years"
_AGE = [
    re.compile(r"\b(\d{1,3})[-\s]year[-\s]old\b", re.I),
    re.compile(r"\baged?\s+(\d{1,3})\s*years?\b", re.I),
    re.compile(r"\b(\d{1,2})[-\s]month[-\s]old\b", re.I),
]
_AGE_MONTHS = re.compile(r"\b(\d{1,2})[-\s]month[-\s]old\b", re.I)

_SEX = [
    (re.compile(r"\b(?:man|male|gentleman|boy|he|his)\b", re.I), "Male"),
    (re.compile(r"\b(?:woman|female|lady|girl|she|her)\b", re.I), "Female"),
]

# "presented with X", "presenting with X", "was admitted with X"
_PRESENT = re.compile(
    r"\b(?:presented|presenting|admitted|referred)\s+(?:to [^,.;]{0,40}\s+)?with\s+([^.;]{6,120})",
    re.I)

# "a 3-day history of", "for the past two weeks", "over 6 months"
_ONSET = re.compile(
    r"\b(?:(\d{1,3})[-\s](day|week|month|year)s?\s+history|"
    r"for\s+(?:the\s+)?(?:past\s+)?(\d{1,3})\s+(day|week|month|year)s?)\b", re.I)


def _first(patterns, text):
    for p in patterns:
        m = p.search(text or "")
        if m:
            return m.group(1)
    return None


def extract_case_facts(case, narrative=""):
    """Pull the case-file fields out of the paper's own words.

    Returns strings ready to print, using NOT_STATED where the text does not
    say. The narrative is searched before the title because a title is
    written to be catchy and a case description is written to be precise.
    """
    text = " ".join(str(x) for x in (
        narrative or "", case.get("narrative", ""), case.get("title", ""))
        if x)[:6000]

    age = _first(_AGE, text)
    if age and _AGE_MONTHS.search(text) and not re.search(r"year[-\s]old", text, re.I):
        age_s = f"{age} months"
    elif age:
        age_s = f"{age} years"
    else:
        age_s = NOT_STATED

    sex = NOT_STATED
    for pat, label in _SEX:
        if pat.search(text):
            sex = label
            break

    m = _PRESENT.search(text)
    present = _clean(m.group(1)) if m else NOT_STATED

    m = _ONSET.search(text)
    if m:
        n = m.group(1) or m.group(3)
        unit = m.group(2) or m.group(4)
        onset = f"{n} {unit}{'s' if not unit.endswith('s') else ''}"
    else:
        onset = NOT_STATED

    pmcid = str(case.get("pmcid") or "").replace("PMC", "").strip()
    return {
        # The case ID is the real PMC accession, not an invented patient
        # number: it is the one identifier that is both real and already
        # public, and it lets a viewer find the paper.
        "case_id": f"PMC{pmcid}" if pmcid else NOT_STATED,
        "age": age_s,
        "sex": sex,
        "presentation": present,
        "onset": onset,
        "source": " ".join(str(x) for x in
                           (case.get("journal", ""), case.get("year", "")) if x).strip()
                  or NOT_STATED,
    }


def _clean(s):
    """Tidy a presenting complaint down to the complaint itself.

    Case reports run the presentation straight into the history -- "weakness
    of both hands and difficulty speaking, following a 12-day history of
    intermittent confusion". The onset belongs in its own row, so the clause
    that introduces it is cut here rather than printed twice.
    """
    s = re.sub(r"\s+", " ", s or "").strip(" ,;:")
    s = re.sub(r"^(a|an|the)\s+", "", s, flags=re.I)
    s = re.split(r",?\s+(?:following|after|preceded by|on a background of|"
                 r"in the context of)\b", s, maxsplit=1, flags=re.I)[0]
    return s.strip(" ,;:")


def _fit(d, text, box_w, start=40, min_size=22):
    """Largest font at which the value still fits its row.

    The first version printed at a fixed 40px and ran a long presenting
    complaint clean off the right-hand edge of the frame. Shrink first, and
    only truncate once the smallest readable size still will not fit.
    """
    size = start
    while size > min_size:
        f = mfr._font(size, True)
        if d.textbbox((0, 0), text, font=f)[2] <= box_w:
            return f, text
        size -= 2
    f = mfr._font(min_size, True)
    out = text
    while out and d.textbbox((0, 0), out + "…", font=f)[2] > box_w:
        out = out[:-1].rstrip()
    return f, (out + "…") if out != text else text


# ── render ─────────────────────────────────────────────────────────────
def _rows(facts):
    return [
        ("CASE",         facts["case_id"]),
        ("AGE",          facts["age"]),
        ("SEX",          facts["sex"]),
        ("PRESENTED WITH", facts["presentation"]),
        ("SYMPTOM ONSET", facts["onset"]),
        ("SOURCE",       facts["source"]),
    ]


def render_casefile_still(case, out_path, narrative="", niche_label="NO KNOWN CAUSE",
                          accent=None, reveal=1.0, anchor="left"):
    """Draw the case-file card.

    reveal 0..1 fills the rows progressively, so the card can appear more
    than once in an episode without being the same frame twice — the fix
    already applied to every other register here.
    """
    accent = tuple(accent) if accent else ACCENT
    facts = extract_case_facts(case, narrative)
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # Faint grid: says "clinical record" without a word of chrome.
    for x in range(0, W, 60):
        d.line([(x, 0), (x, H)], fill=(20, 26, 31), width=1)
    for y in range(0, H, 60):
        d.line([(0, y), (W, y)], fill=(20, 26, 31), width=1)

    d.rectangle([120, 96, W - 120, 200], fill=PANEL, outline=EDGE, width=2)
    d.rectangle([120, 96, 132, 200], fill=accent)
    d.text((164, 122), niche_label, font=mfr._font(38, True), fill=accent)
    d.text((164, 160), "CASE FILE", font=mfr._font(26, False), fill=DIM)

    rows = _rows(facts)
    shown = max(1, int(round(len(rows) * max(0.0, min(1.0, reveal)))))
    y = 258
    for i, (label, value) in enumerate(rows):
        if i >= shown:
            break
        d.rectangle([120, y, W - 120, y + 104], fill=PANEL, outline=EDGE, width=1)
        d.text((150, y + 16), label, font=mfr._font(24, True), fill=DIM)
        missing = value == NOT_STATED
        _font, _val = _fit(d, value, (W - 120 - 200) - 150,
                           start=40 if not missing else 32)
        d.text((150, y + 52), _val, font=_font,
               fill=(TEXT if not missing else ALERT))
        if not missing:
            d.rectangle([W - 168, y + 40, W - 150, y + 62], fill=accent)
        y += 118

    # An honest footer. If any field is missing the card says so rather than
    # letting a blank read as "no symptoms".
    if any(v == NOT_STATED for _, v in rows):
        d.text((150, H - 96),
               "Fields marked NOT STATED are absent from the source paper.",
               font=mfr._font(24, False), fill=DIM)
    cit = (case.get("citation") or "")[:150]
    if cit:
        d.text((150, H - 60), cit, font=mfr._font(22, False), fill=DIM)

    img.save(out_path)
    return True
