"""
Caption grouping, timing and ASS generation.

Extracted from clinical_pipeline.generate_real_synced_ass so the logic that
decides WHEN a caption appears and HOW LONG it stays can be tested directly,
instead of only being observable by watching a finished 250 MB video.

WHAT WAS ACTUALLY WRONG
-----------------------
Direct feedback on the first rendered episode: "the subtitles are moving too
fast, and there are words that are not even syncing in." A previous pass
raised the minimum dwell and added a lead-out, which was necessary and not
sufficient. Reading the logic against real timings shows five separate
defects, four of which survived that pass:

1. THE MINIMUM DWELL WAS NOT ENFORCED. The code extended a short cue to
   MIN_DWELL and then immediately clamped it with
   `end = min(end, next_start)` so cues could not overlap. In continuous
   speech the next cue starts almost immediately, so the clamp won every
   time and the dwell floor did nothing at all -- exactly the cues that
   were too short stayed too short. A dwell floor has to be met by MERGING
   with the following cue, not by extending into space that is not there.

2. NOTHING LIMITED READING SPEED. Time on screen is not readability:
   46 characters held for 1.5 seconds is 30 characters per second. Broadcast
   practice is 17 and Netflix caps at 20. Every cue could satisfy the dwell
   floor and still be unreadable, which is the literal complaint.

3. GROUPING IGNORED LANGUAGE. Words were packed to a character budget with
   no regard for punctuation or pauses, so cues broke mid-clause -- "the
   liver has already" / "processed the pigment and then failed". That reads
   as desync even when the timing is perfect, because the eye expects a
   caption to be a unit of sense.

4. NO ASS ESCAPING. `{` and `}` open and close override blocks in ASS and
   a trailing backslash escapes the following character. An unescaped brace
   from a transcript silently swallows the rest of the line.

5. OUTLINE-ONLY WHITE TEXT. Style used BorderStyle 1 over figures that are
   frequently near-white (a CT window, a pale histology slide). White text
   with a 3px outline on a white background is unreadable. This channel puts
   real medical imaging behind its captions, so the caption needs its own
   background, not just an edge.

Everything here is pure: given word timings in, cues out. No network, no
audio, no ffmpeg -- so it is testable, and tools/local_caption_render.py
burns the result onto real frames to confirm it visually.
"""
import re

# ── readability constants ──────────────────────────────────────────────
# Characters per second. 17 is the long-standing broadcast subtitling
# figure and Netflix's own timed-text style guide caps adult content at 20.
# Clinical narration carries unfamiliar words, so the lower end is right.
MAX_CPS = 17.0

MIN_DWELL = 1.2          # never flash
MAX_DWELL = 7.0          # never leave a stale caption sitting through silence
LEAD_OUT = 0.35          # let the eye finish the line after the voice stops
MIN_GAP = 0.08           # visible separation between consecutive cues

MAX_CHARS_PER_LINE = 42
MAX_LINES = 2
MAX_CHARS = MAX_CHARS_PER_LINE * MAX_LINES

# A pause this long is a natural caption boundary regardless of length.
PAUSE_BREAK = 0.45

_SENTENCE_END = re.compile(r"[.!?…]['\"”’)]?$")
_CLAUSE_END = re.compile(r"[,;:—-]$")


def escape_ass(text):
    """
    Make text safe for an ASS Dialogue field.

    `{` opens an override block and `}` closes it, so an unescaped brace
    makes libass treat everything up to the next `}` as formatting tags and
    render nothing. A trailing backslash escapes the newline handling.
    """
    t = (text or "").replace("\\", "\\\\")
    t = t.replace("{", "\\{").replace("}", "\\}")
    # Real newlines are not valid inside a Dialogue line; \N is the ASS form.
    t = t.replace("\r", " ").replace("\n", "\\N")
    return t.strip()


def wrap_two_lines(text, max_chars=MAX_CHARS_PER_LINE, max_lines=MAX_LINES):
    """
    Balanced wrap into at most max_lines. Balanced, not greedy: a greedy
    wrap produces a full line above a two-word orphan, which draws the eye
    to the wrong place and looks like a mistake.
    """
    words = text.split()
    if not words:
        return ""
    if len(text) <= max_chars:
        return text
    # Try the split point closest to the middle that keeps every line legal.
    best, best_cost = None, None
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        if len(a) > max_chars or len(b) > max_chars * (max_lines - 1):
            continue
        cost = abs(len(a) - len(b))
        if best_cost is None or cost < best_cost:
            best, best_cost = (a, b), cost
    if best is None:
        # Cannot split legally (one enormous word); let it ride on one line
        # rather than dropping content.
        return text
    a, b = best
    if len(b) > max_chars and max_lines > 2:
        return a + "\\N" + wrap_two_lines(b, max_chars, max_lines - 1)
    return a + "\\N" + b


def _tok(w):
    return (w.get("word") or "").strip()


def _normalise(words_data):
    """
    Keep only words that carry usable timing, in order.

    Whisper occasionally returns an entry without `start`/`end`. The old code
    indexed those keys directly inside the function-wide try/except, so ONE
    malformed word discarded the captions for the entire episode.
    """
    out = []
    for w in words_data or []:
        tok = _tok(w)
        if not tok:
            continue
        try:
            s, e = float(w["start"]), float(w["end"])
        except (KeyError, TypeError, ValueError):
            continue
        if e < s:
            s, e = e, s
        if out and s < out[-1]["end"]:
            s = out[-1]["end"]          # transcripts can overlap slightly
        out.append({"word": tok, "start": s, "end": max(e, s)})
    return out


def group_words(words_data):
    """
    Words -> caption groups, broken where language breaks.

    Priority order for a boundary:
      1. sentence end          (always, if the group has content)
      2. a real pause          (>= PAUSE_BREAK)
      3. the character budget  (soft: prefers a preceding clause break)
    """
    words = _normalise(words_data)
    if not words:
        return []

    groups, cur, chars = [], [], 0
    for i, w in enumerate(words):
        tok = w["word"]
        add = len(tok) + (1 if chars else 0)

        if cur and chars + add > MAX_CHARS:
            # Over budget. Prefer to have broken at the last clause boundary
            # inside the current group rather than mid-phrase.
            cut = None
            for j in range(len(cur) - 1, max(0, len(cur) - 5) - 1, -1):
                if _CLAUSE_END.search(cur[j]["word"]):
                    cut = j + 1
                    break
            if cut and cut < len(cur):
                groups.append(cur[:cut])
                cur = cur[cut:]
                chars = sum(len(x["word"]) for x in cur) + max(0, len(cur) - 1)
            else:
                groups.append(cur)
                cur, chars = [], 0
            add = len(tok)

        cur.append(w)
        chars += add

        if _SENTENCE_END.search(tok):
            groups.append(cur)
            cur, chars = [], 0
            continue
        nxt = words[i + 1] if i + 1 < len(words) else None
        if nxt and (nxt["start"] - w["end"]) >= PAUSE_BREAK and cur:
            groups.append(cur)
            cur, chars = [], 0
    if cur:
        groups.append(cur)
    return _absorb_orphans([g for g in groups if g])


# A caption this small is an orphan, not a caption. Measured on the real
# narration: the character-budget split leaves a remainder, and when the very
# next token ends a sentence that remainder flushes as a cue containing one
# word -- "poorly.", "litre.", "after." -- each on screen for under a second.
# Three of them in a twelve-minute episode, and every one reads as a glitch.
ORPHAN_MAX_CHARS = 14
ORPHAN_MAX_WORDS = 2


def _absorb_orphans(groups):
    """
    Fold tiny groups into a neighbour. Backwards first: an orphan is the tail
    of the phrase before it, so that is where it belongs and where it reads
    correctly. Forwards only if joining backwards would blow the budget.
    """
    if len(groups) < 2:
        return groups
    out = []
    for g in groups:
        text = _text_of(g)
        is_orphan = len(text) <= ORPHAN_MAX_CHARS or len(g) <= ORPHAN_MAX_WORDS
        if is_orphan and out and len(_text_of(out[-1])) + 1 + len(text) <= MAX_CHARS:
            out[-1] = out[-1] + g
            continue
        out.append(g)
    # Anything still orphaned could not merge backwards; try forwards.
    merged = []
    i = 0
    while i < len(out):
        g = out[i]
        text = _text_of(g)
        is_orphan = len(text) <= ORPHAN_MAX_CHARS or len(g) <= ORPHAN_MAX_WORDS
        if (is_orphan and i + 1 < len(out)
                and len(text) + 1 + len(_text_of(out[i + 1])) <= MAX_CHARS):
            merged.append(g + out[i + 1])
            i += 2
            continue
        merged.append(g)
        i += 1

    # Anything STILL orphaned could not merge in either direction, because
    # both neighbours are already at the character budget. Rebalance instead:
    # pull words back from the previous cue until the orphan is a real
    # caption and the donor is still legal. This is what a subtitle editor
    # does by hand, and it is the only move that fixes the last case -- a
    # one-word cue ("litre.") wedged between two full ones.
    final = []
    for g in merged:
        if (final and (len(_text_of(g)) <= ORPHAN_MAX_CHARS
                       or len(g) <= ORPHAN_MAX_WORDS)):
            prev = final[-1]
            moved = 0
            while (len(prev) - 1 >= 2 and moved < 4
                   and (len(_text_of(g)) <= ORPHAN_MAX_CHARS
                        or len(g) <= ORPHAN_MAX_WORDS)):
                g = [prev[-1]] + g
                prev = prev[:-1]
                moved += 1
            final[-1] = prev
        final.append(g)
    return [g for g in final if g]


def _text_of(group):
    return " ".join(w["word"] for w in group)


def build_cues(words_data, total_duration=None):
    """
    (cues, stats). Each cue is {'start', 'end', 'text', 'cps'}.

    Dwell and reading speed are satisfied by MERGING groups, never by
    stealing time from the next cue -- which is what made the previous
    dwell floor a no-op.
    """
    groups = group_words(words_data)
    if not groups:
        return [], {"cues": 0}

    # Pass 1: merge any group that physically cannot be read in the time it
    # owns, into the following group. Repeat until stable, because merging
    # can create a new group that is still too fast.
    changed = True
    while changed and len(groups) > 1:
        changed = False
        merged = []
        i = 0
        while i < len(groups):
            g = groups[i]
            if i + 1 < len(groups):
                nxt = groups[i + 1]
                span = nxt[0]["start"] - g[0]["start"]      # time actually owned
                text = _text_of(g)
                needs = max(MIN_DWELL, len(text) / MAX_CPS)
                combined = len(text) + 1 + len(_text_of(nxt))
                if span < needs and combined <= MAX_CHARS:
                    merged.append(g + nxt)
                    i += 2
                    changed = True
                    continue
            merged.append(g)
            i += 1
        groups = merged

    cues = []
    for gi, g in enumerate(groups):
        start = g[0]["start"]
        text = _text_of(g)
        # The cue may run until the next one starts (minus a visible gap),
        # or until the audio ends.
        if gi + 1 < len(groups):
            nxt_start = groups[gi + 1][0]["start"]
            # The visible gap between cues is desirable, but not at the cost
            # of cutting a caption before its own last word has finished --
            # in continuous speech the next cue can start within MIN_GAP of
            # this one's final word, and subtracting the gap unconditionally
            # truncated it. Take the gap when there is room for it, and fall
            # back to ending exactly at the next cue's start when there is
            # not. Never past it: an overlap is worse than a missing gap.
            ceiling = max(nxt_start - MIN_GAP, min(g[-1]["end"], nxt_start))
        elif total_duration:
            ceiling = float(total_duration)
        else:
            ceiling = g[-1]["end"] + LEAD_OUT

        spoken_end = g[-1]["end"]
        want = max(spoken_end + LEAD_OUT,
                   start + max(MIN_DWELL, len(text) / MAX_CPS))
        # MAX_DWELL exists to stop a caption sitting through a long silence.
        # It must never cut a caption short while its own words are still
        # being SPOKEN -- the first draft did exactly that, clipping the
        # opening cue at 7.00s while the sentence ran to 8.6s, so the caption
        # vanished mid-word. The cap therefore applies to the lead-out only,
        # never below the end of speech.
        hard_cap = max(spoken_end + LEAD_OUT, start + MAX_DWELL)
        end = min(want, ceiling, hard_cap)
        if end <= start:
            end = start + max(0.4, min(MIN_DWELL, max(0.0, ceiling - start)))
        cues.append({"start": start, "end": end, "text": text,
                     "cps": len(text) / max(0.01, end - start)})

    over = [c for c in cues if c["cps"] > MAX_CPS + 0.5]
    short = [c for c in cues if (c["end"] - c["start"]) < MIN_DWELL - 0.01]
    stats = {
        "cues": len(cues),
        "over_cps": len(over),
        "under_dwell": len(short),
        "max_cps": round(max((c["cps"] for c in cues), default=0), 1),
        "mean_dwell": round(sum(c["end"] - c["start"] for c in cues)
                            / max(1, len(cues)), 2),
        "overlaps": sum(1 for a, b in zip(cues, cues[1:]) if b["start"] < a["end"]),
    }
    return cues, stats


# ── ASS output ─────────────────────────────────────────────────────────
def _t(s):
    s = max(0.0, float(s))
    h = int(s) // 3600
    m = (int(s) % 3600) // 60
    sec = int(s) % 60
    cs = int(round((s - int(s)) * 100))
    if cs == 100:
        cs, sec = 0, sec + 1
    return f"{h}:{m:02d}:{sec:02d}.{cs:02d}"


# BorderStyle 3 = opaque box behind the text, BackColour is that box.
# &H B0 000000 is black at ~31% transparency (ASS alpha is inverted: 00 is
# opaque, FF is invisible).
#
# This channel puts real diagnostic imaging behind its captions. A CT window
# or a pale histology slide is close to white, and the previous style was
# white text with a 3px outline and no box -- unreadable over exactly the
# frames this channel exists to show. Font is named as an installed family
# rather than Arial, which only rendered because fontconfig silently
# substitutes Liberation Sans.
ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,52,&H00FFFFFF,&H000000FF,&H00101418,&HB0000000,-1,0,0,0,100,100,0,0,3,14,0,2,120,120,68,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def build_ass(cues):
    lines = [ASS_HEADER.rstrip("\n")]
    for c in cues:
        text = wrap_two_lines(escape_ass(c["text"]))
        lines.append(f"Dialogue: 0,{_t(c['start'])},{_t(c['end'])},"
                     f"Default,,0,0,0,,{text}")
    return "\n".join(lines) + "\n"


def ass_from_words(words_data, total_duration=None):
    """(ass_text, stats). The single entry point the pipelines call."""
    cues, stats = build_cues(words_data, total_duration)
    if not cues:
        return None, stats
    return build_ass(cues), stats
