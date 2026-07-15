"""
PRODUCT MANUSCRIPT SYSTEM — builds the 3 real digital products from the
Media Empire operating model, by harvesting genuine insights from real
produced episodes (per the document's own instruction: "Build the Atlas
and Handbook by harvesting the best episodes rather than writing from
scratch in isolation").

Each product is a genuine growing Markdown manuscript, organized into
the specific chapters the source document defined, stored at repo root
in products/ (NOT in docs/ — these are working drafts that get exported
and sold, not free public pages; keeping them separate avoids
undermining the thing you're trying to sell).

HONEST NOTE, stated plainly: the Empire Collapse Atlas has no working
feeder channel yet. It's fed only by The Archive and The Collapse Index
(Ch4/Ch5), neither of which is built. Its structure exists below so it's
ready the moment those channels come online, but it will genuinely stay
empty until then — this module doesn't pretend otherwise or fill it with
placeholder content.

Free-tier: plain Markdown files, no database, committed to the repo like
everything else in this project.
"""

import json
import re
import difflib
import datetime
from pathlib import Path

PRODUCTS = {
    "dark-manipulation-tactics-handbook": {
        "title": "Dark Manipulation Tactics Handbook",
        "feeder_channels": ["betrayal_deepdive", "control_files"],
        "chapters": [
            "Love Bombing, Mirroring, and Soft Entry Points of Control",
            "Trauma Bonding, Shame, and the Dependency Loop",
            "False Apologies, Smear Campaigns, and Post-Exit Punishment",
            "Cult Loyalty Traps and Propaganda Crossover Mechanics",
            "Betrayal as a Control System: How Coercive Loyalty Is Engineered",
        ],
    },
    "empire-collapse-atlas": {
        "title": "Empire Collapse Atlas",
        "feeder_channels": ["archive", "collapse_index"],  # NEITHER built yet — stays empty honestly
        "chapters": [
            "Collapse Signals and the Early-Warning Scoreboard",
            "Overstretch, Logistics, and the Empire-Killing Math Nobody Sees",
            "Elite Infighting, Betrayal, and Internal Fracture",
            "Propaganda in Decline: The Stories Dying States Tell Themselves",
            "Modern Parallels: AI, Institutions, and Corporate Brittleness",
        ],
    },
    "faceless-documentary-creator-toolkit": {
        "title": "Faceless Documentary Creator Toolkit",
        "feeder_channels": ["evidence_room"],  # also fed by operating-system knowledge, see below
        "chapters": [
            "Topic Scoring and Ruthless Backlog Building",
            "Title Systems and Thumbnail Tension Frameworks",
            "Companion Pages, Product Bridges, and Owned-Asset Monetization",
            "Channel Voice Design and Script Prompt Systems",
            "The Weekly Operator Loop for a Five-Channel Media Machine",
        ],
    },
}

CHANNEL_TO_PRODUCT = {
    "betrayal_deepdive": "dark-manipulation-tactics-handbook",
    "control_files":     "dark-manipulation-tactics-handbook",
    "evidence_room":      "faceless-documentary-creator-toolkit",
    "archive":            "empire-collapse-atlas",
    "collapse_index":     "empire-collapse-atlas",
}

SIMILARITY_THRESHOLD = 0.72  # above this, a new note is considered too similar to an existing one


def _manuscript_path(products_root, product_id):
    return Path(products_root) / f"{product_id}.md"


def _load_manuscript_notes(products_root, product_id):
    """
    Returns {chapter_name: [note_text, ...]} parsed from the existing
    manuscript file, or an empty skeleton (every defined chapter present,
    no notes yet) if the file doesn't exist. Never raises.
    """
    product = PRODUCTS.get(product_id)
    if not product:
        return {}
    skeleton = {ch: [] for ch in product["chapters"]}

    path = _manuscript_path(products_root, product_id)
    if not path.exists():
        return skeleton

    try:
        text = path.read_text(encoding="utf-8")
        current_chapter = None
        for line in text.splitlines():
            chapter_match = re.match(r'^## (.+)$', line)
            if chapter_match:
                current_chapter = chapter_match.group(1).strip()
                if current_chapter not in skeleton:
                    skeleton[current_chapter] = []
                continue
            note_match = re.match(r'^- (.+)$', line)
            if note_match and current_chapter:
                skeleton[current_chapter].append(note_match.group(1).strip())
        return skeleton
    except Exception:
        return skeleton


def _write_manuscript(products_root, product_id, notes_by_chapter):
    product = PRODUCTS[product_id]
    lines = [f"# {product['title']}", ""]
    lines.append(f"_Last updated: {datetime.date.today().isoformat()}_")
    lines.append("")
    for chapter in product["chapters"]:
        lines.append(f"## {chapter}")
        lines.append("")
        for note in notes_by_chapter.get(chapter, []):
            lines.append(f"- {note}")
        lines.append("")
    try:
        Path(products_root).mkdir(parents=True, exist_ok=True)
        _manuscript_path(products_root, product_id).write_text("\n".join(lines), encoding="utf-8")
        return True
    except Exception:
        return False


def extract_product_note(episode_title, script_excerpt, channel_id, ai_fn):
    """
    Generates ONE genuine, reusable insight from a real episode — not a
    restatement of the episode, an actual extractable framework/pattern/
    warning-sign a reader could apply elsewhere. Also picks which of the
    product's defined chapters it belongs to. Returns
    {chapter, note_text} or None if the channel has no product route yet
    or extraction fails.
    """
    product_id = CHANNEL_TO_PRODUCT.get(channel_id)
    if not product_id:
        return None
    product = PRODUCTS[product_id]
    chapters_list = "\n".join(f"- {c}" for c in product["chapters"])

    prompt = f"""Extract ONE genuinely reusable insight from this real episode, for a
reference handbook chapter. This must be a real, applicable pattern or
framework — NOT a summary of what happened in the episode.

EPISODE: {episode_title}
CONTENT: {script_excerpt[:800]}

Which chapter does this belong to (pick the single best match)?
{chapters_list}

Return ONLY valid JSON:
{{"chapter": "exact chapter name from the list above",
  "note_text": "one genuinely reusable insight, framework, or warning sign, "
               "specific enough to be useful, phrased so it applies beyond just this one case"}}"""
    try:
        raw = ai_fn(prompt, tokens=300)
        if raw:
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                data = json.loads(match.group())
                if data.get("chapter") in product["chapters"] and data.get("note_text"):
                    return {"chapter": data["chapter"], "note_text": data["note_text"]}
    except Exception:
        pass
    return None


def add_product_note(products_root, episode_title, script_excerpt, channel_id, ai_fn):
    """
    The real pipeline entry point: extracts a note from this episode and
    appends it to the right product's manuscript, in the right chapter —
    unless a near-duplicate insight already exists in that chapter (so
    the manuscript grows into a genuine reference, not repetitive filler).
    Returns the note added, or None if skipped (no route / duplicate / failure).
    """
    product_id = CHANNEL_TO_PRODUCT.get(channel_id)
    if not product_id:
        return None

    extracted = extract_product_note(episode_title, script_excerpt, channel_id, ai_fn)
    if not extracted:
        return None

    notes_by_chapter = _load_manuscript_notes(products_root, product_id)
    existing_in_chapter = notes_by_chapter.get(extracted["chapter"], [])

    for existing_note in existing_in_chapter:
        similarity = difflib.SequenceMatcher(None, existing_note.lower(),
                                              extracted["note_text"].lower()).ratio()
        if similarity > SIMILARITY_THRESHOLD:
            return None  # too similar to something already captured — skip, don't pad the manuscript

    notes_by_chapter.setdefault(extracted["chapter"], []).append(extracted["note_text"])
    success = _write_manuscript(products_root, product_id, notes_by_chapter)
    return extracted if success else None


def get_manuscript_stats(products_root):
    """Quick per-product note counts, for reporting/dashboard use."""
    stats = {}
    for product_id, product in PRODUCTS.items():
        notes = _load_manuscript_notes(products_root, product_id)
        total = sum(len(v) for v in notes.values())
        stats[product_id] = {
            "title": product["title"],
            "total_notes": total,
            "chapters_with_content": sum(1 for v in notes.values() if v),
            "chapters_total": len(product["chapters"]),
        }
    return stats
