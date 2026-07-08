"""
MONETIZATION MODULE — Layer 2 of the monetization stack (digital
products). Exports the growing product manuscripts into properly
formatted, sellable PDFs, and manages the config connecting each product
to its real Gumroad listing.

HONEST DESIGN NOTE: creating the actual Gumroad account and the first
listing for each product is a genuine one-time manual step — no API
lets you sign up for a payment processor on someone's behalf, the same
category of thing as enabling GitHub Pages. This module automates
everything AFTER that: keeping the sellable PDF fresh as the manuscript
grows, and once you've created the real Gumroad listings, plugging their
URLs into GUMROAD_CONFIG below makes every "Buy" button across the whole
site point to the real thing instead of a placeholder.

GitHub Pages / commercial-use note: this module deliberately never
processes a sale itself. The exported PDF and the "Buy" button live on
GitHub Pages as free, informational content; the actual transaction
happens entirely on Gumroad. This keeps the commercial activity off of
GitHub Pages itself, not just the language around it.
"""

import json
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

# ══════════════════════════════════════════════════════════════════
# GUMROAD CONFIG — fill in the real product URLs here once you've
# created the actual listings (gumroad.com, free to sign up and list,
# they take a per-sale fee instead of a monthly cost). Everything below
# a placeholder URL will show a "coming soon" state instead of a broken
# link, so nothing looks broken while you're still setting this up.
# ══════════════════════════════════════════════════════════════════
GUMROAD_CONFIG = {
    "dark-manipulation-tactics-handbook": {
        "gumroad_url": None,     # e.g. "https://gumroad.com/l/dmth"
        "price_usd": 19,
        "status": "not_yet_listed",
    },
    "empire-collapse-atlas": {
        "gumroad_url": None,
        "price_usd": 19,
        "status": "not_yet_listed",
    },
    "faceless-documentary-creator-toolkit": {
        "gumroad_url": None,
        "price_usd": 29,
        "status": "not_yet_listed",
    },
}


def get_product_cta_url(product_id):
    """
    Returns the real Gumroad URL if configured, otherwise a safe fallback
    to the product's own info page (never a broken link, never a fake
    checkout).
    """
    cfg = GUMROAD_CONFIG.get(product_id, {})
    if cfg.get("gumroad_url"):
        return cfg["gumroad_url"]
    return f"../products/{product_id}.html"  # falls back to the info page itself


def export_manuscript_to_pdf(product_title, chapters_with_notes, output_path):
    """
    Converts a product's current manuscript content into a properly
    formatted, sellable PDF. chapters_with_notes: {chapter_name: [notes]}
    same shape as product_manuscript.py's internal format.

    Returns True on success, False on failure (non-fatal by design — a
    PDF export failure should never break the weekly report run).
    """
    try:
        doc = SimpleDocTemplate(str(output_path), pagesize=letter,
                                 topMargin=0.9*inch, bottomMargin=0.9*inch,
                                 leftMargin=0.9*inch, rightMargin=0.9*inch)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="ProductTitle", fontSize=24, leading=30,
                                   spaceAfter=20, fontName="Helvetica-Bold",
                                   textColor=colors.HexColor("#14161a")))
        styles.add(ParagraphStyle(name="ChapterHead", fontSize=15, leading=19,
                                   spaceBefore=24, spaceAfter=10, fontName="Helvetica-Bold",
                                   textColor=colors.HexColor("#7d6b45")))
        styles.add(ParagraphStyle(name="NoteText", fontSize=10.5, leading=15,
                                   spaceAfter=8, bulletIndent=0, leftIndent=14))
        styles.add(ParagraphStyle(name="EmptyChapter", fontSize=10, leading=14,
                                   textColor=colors.grey, leftIndent=14))

        story = [Paragraph(product_title, styles["ProductTitle"]),
                 Spacer(1, 6),
                 Paragraph("A living reference, built from real documented cases. "
                           "This edition reflects the current state of the research — "
                           "new editions are issued as new cases are added.",
                           styles["NoteText"]),
                 Spacer(1, 12)]

        for chapter, notes in chapters_with_notes.items():
            story.append(Paragraph(chapter, styles["ChapterHead"]))
            if notes:
                for note in notes:
                    story.append(Paragraph(f"• {note}", styles["NoteText"]))
            else:
                story.append(Paragraph("(This chapter is still being built out as new "
                                        "cases are documented.)", styles["EmptyChapter"]))
            story.append(Spacer(1, 8))

        doc.build(story)
        return True
    except Exception:
        return False


def export_all_products(products_root, pdf_output_root):
    """
    Weekly-cadence entry point: exports every product with at least one
    note into a fresh sellable PDF. Products with zero notes (like the
    Atlas, until Ch4/5 exist) are skipped rather than exporting an
    empty, unsellable file.
    """
    from product_manuscript import PRODUCTS, _load_manuscript_notes

    Path(pdf_output_root).mkdir(parents=True, exist_ok=True)
    results = []
    for product_id, product in PRODUCTS.items():
        notes = _load_manuscript_notes(products_root, product_id)
        total_notes = sum(len(v) for v in notes.values())
        if total_notes == 0:
            results.append({"product_id": product_id, "exported": False,
                             "reason": "no content yet"})
            continue
        out_path = Path(pdf_output_root) / f"{product_id}.pdf"
        success = export_manuscript_to_pdf(product["title"], notes, out_path)
        results.append({"product_id": product_id, "exported": success,
                         "note_count": total_notes, "path": str(out_path) if success else None})
    return results
