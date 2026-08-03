"""
The laboratory dashboard register.

WHY
---
CHART already plots one reported value over time. What it cannot show is the
thing a clinician actually looks at: a panel of results at once, each against
its own reference range, with the abnormal ones jumping out. That panel is
how a diagnosis gets made, and it is the most legible way to show a viewer
WHY the doctors reacted.

THE RULE, SAME AS EVERYWHERE ELSE ON THIS CHANNEL
-------------------------------------------------
Only values the paper actually reports are drawn. There is no synthetic
panel, no "typical" result filled in to make the card look complete, and no
inference from one value to another. A dashboard with three real rows is
honest; one with twelve rows where nine were invented is a fabricated
clinical record wearing a citation.

Reference ranges are the standard adult ranges and are labelled as such.
They vary by laboratory, age and sex, so the card says "typical adult range"
rather than implying the source lab's own range.
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
HIGH = (206, 92, 80)
LOW = (86, 140, 214)
OK = (110, 182, 138)

# analyte -> (display, unit, low, high, aliases)
ANALYTES = {
    "sodium":      ("Sodium", "mmol/L", 135, 145, ("na+", "serum sodium")),
    "potassium":   ("Potassium", "mmol/L", 3.5, 5.0, ("k+",)),
    "creatinine":  ("Creatinine", "umol/L", 60, 110, ()),
    "haemoglobin": ("Haemoglobin", "g/L", 130, 170, ("hemoglobin", "hb")),
    "platelets":   ("Platelets", "x10^9/L", 150, 400, ("platelet count",)),
    "crp":         ("CRP", "mg/L", 0, 5, ("c-reactive protein",)),
    "glucose":     ("Glucose", "mmol/L", 3.9, 5.5, ("blood glucose",)),
    "calcium":     ("Calcium", "mmol/L", 2.2, 2.6, ()),
    "bilirubin":   ("Bilirubin", "umol/L", 0, 21, ()),
    "alt":         ("ALT", "U/L", 0, 40, ("alanine aminotransferase",)),
    "lactate":     ("Lactate", "mmol/L", 0.5, 2.2, ()),
    "albumin":     ("Albumin", "g/L", 35, 50, ()),
    "ferritin":    ("Ferritin", "ug/L", 30, 400, ()),
    "tsh":         ("TSH", "mIU/L", 0.4, 4.0, ()),
    "inr":         ("INR", "", 0.8, 1.2, ()),
    "white cell":  ("White cells", "x10^9/L", 4.0, 11.0,
                    ("white blood cell", "wbc", "leucocyte", "leukocyte")),
}

# "sodium of 118", "sodium was 118", "sodium 118 mmol/L", "sodium: 118"
_NUM = r"(\d{1,4}(?:\.\d{1,2})?)"
# An optional measurement noun between the analyte and its value: papers
# write "white cell COUNT of 18.4" and "creatinine LEVEL was 214". Without
# this the analyte name and the number are not adjacent and the whole result
# is missed.
_MID = r"(?:\s+(?:count|counts|level|levels|concentration|value|values|" \
       r"activity|titre|titer))?"
_JOIN = r"(?:\s*(?:of|was|were|at|:|=|rose to|fell to|peaked at)\s*|\s+)"


def extract_labs(text, limit=7):
    """Every analyte the text actually reports, in the order it reports them.

    Deliberately conservative. A number has to appear next to a recognised
    analyte name to be picked up at all, which means some real values are
    missed — the right trade on a channel where a wrong number is worse than
    a missing one.
    """
    low = re.sub(r"\s+", " ", (text or "").lower())
    found, seen = [], set()
    for key, (disp, unit, lo, hi, aliases) in ANALYTES.items():
        for name in (key,) + tuple(aliases):
            m = re.search(rf"\b{re.escape(name)}\b{_MID}{_JOIN}{_NUM}", low)
            if not m:
                continue
            try:
                val = float(m.group(1))
            except ValueError:
                continue
            # Guard against a sentence number swallowed as a result ("day 3"
            # landing next to an analyte name), NOT against abnormality.
            #
            # The first version capped at hi*12, which threw away a CRP of
            # 212 against a 0-5 reference range -- i.e. it discarded exactly
            # the wildly abnormal values that are the reason the case got
            # published. The floor does the real work here, because adjacency
            # to the analyte name is already a strong filter.
            if lo > 0 and val < lo * 0.05:
                continue
            if val > max(hi, 1) * 100:
                continue
            if key in seen:
                continue
            seen.add(key)
            found.append({"name": disp, "unit": unit, "value": val,
                          "low": lo, "high": hi,
                          "flag": "HIGH" if val > hi else "LOW" if val < lo else "NORMAL"})
            break
    # Abnormal first, then by how far outside the range the value sits.
    #
    # The first version sorted abnormals alphabetically, which is a
    # meaningless order for clinical results and had a real consequence: with
    # eight abnormal values and a seven-row cap, a white cell count of 18.4
    # against a 4-11 range was dropped because "White cells" sorts last. The
    # row that survives a cap should be the one a clinician would look at
    # first.
    found.sort(key=lambda r: (r["flag"] == "NORMAL", -_deviation(r)))
    return found[:limit]


def _deviation(row):
    """How far outside its reference range a value sits, as a multiple of
    the range width. Comparable across analytes with different units."""
    lo, hi, val = row["low"], row["high"], row["value"]
    width = max(hi - lo, 1e-6)
    if val > hi:
        return (val - hi) / width
    if val < lo:
        return (lo - val) / width
    return 0.0


def _bar(d, x, y, w, h, row, accent):
    """One result as a range bar with the value marked on it."""
    lo, hi, val = row["low"], row["high"], row["value"]
    span_lo = min(lo, val) - (hi - lo) * 0.35
    span_hi = max(hi, val) + (hi - lo) * 0.35
    if span_hi <= span_lo:
        span_hi = span_lo + 1.0

    def px(v):
        return x + (v - span_lo) / (span_hi - span_lo) * w

    d.rectangle([x, y + h // 2 - 3, x + w, y + h // 2 + 3], fill=(44, 56, 64))
    # The reference band.
    d.rectangle([px(lo), y + 4, px(hi), y + h - 4], fill=(30, 58, 56),
                outline=(52, 92, 88), width=2)
    colour = {"HIGH": HIGH, "LOW": LOW}.get(row["flag"], OK)
    mx = px(val)
    d.polygon([(mx, y + 2), (mx - 13, y - 14), (mx + 13, y - 14)], fill=colour)
    d.rectangle([mx - 3, y + 2, mx + 3, y + h - 2], fill=colour)
    return colour


def render_lab_still(case, text, out_path, niche_label="NO KNOWN CAUSE",
                     accent=None, reveal=1.0, title="LABORATORY PANEL"):
    """Draw the dashboard. Returns False when the paper reports no values.

    False matters: it means the register falls through to another one rather
    than rendering an empty panel, which would be both ugly and a lie about
    what the paper contains.
    """
    accent = tuple(accent) if accent else ACCENT
    rows = extract_labs(text)
    if not rows:
        return False

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    for x in range(0, W, 60):
        d.line([(x, 0), (x, H)], fill=(20, 26, 31), width=1)

    d.rectangle([110, 84, W - 110, 176], fill=PANEL, outline=EDGE, width=2)
    d.rectangle([110, 84, 122, 176], fill=accent)
    d.text((152, 104), title, font=mfr._font(36, True), fill=accent)
    d.text((152, 146), "Values as reported in the source paper",
           font=mfr._font(22, False), fill=DIM)

    shown = max(1, int(round(len(rows) * max(0.05, min(1.0, reveal)))))
    y = 226
    row_h = min(112, int((mfr.CONTENT_BOTTOM - 250) / max(1, len(rows))))
    for row in rows[:shown]:
        d.rectangle([110, y, W - 110, y + row_h - 10], fill=PANEL,
                    outline=EDGE, width=1)
        d.text((140, y + 16), row["name"], font=mfr._font(30, True), fill=TEXT)
        d.text((140, y + 54), f"ref {_fmt(row['low'])}–{_fmt(row['high'])} "
                              f"{row['unit']}".strip(),
               font=mfr._font(20, False), fill=DIM)
        colour = _bar(d, 560, y + 34, 780, row_h - 62, row, accent)
        val_s = f"{_fmt(row['value'])} {row['unit']}".strip()
        d.text((1400, y + 22), val_s, font=mfr._font(34, True), fill=colour)
        if row["flag"] != "NORMAL":
            d.text((1400, y + 62), row["flag"], font=mfr._font(24, True), fill=colour)
        y += row_h

    d.text((140, H - 92), "Reference intervals are typical adult ranges and "
                          "vary by laboratory, age and sex.",
           font=mfr._font(21, False), fill=DIM)
    cit = (case.get("citation") or "")[:150]
    if cit:
        d.text((140, H - 58), cit, font=mfr._font(21, False), fill=DIM)
    img.save(out_path)
    return True


def _fmt(v):
    return f"{v:.0f}" if float(v).is_integer() else f"{v:g}"
