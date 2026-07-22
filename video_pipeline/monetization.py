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
import requests
from pathlib import Path
# FIX (found on live Ch1 test run — real bug, not a design choice): reportlab
# was imported at module level, so importing THIS WHOLE MODULE failed with
# "No module named 'reportlab'" on every single generate run across all 5
# channels whenever reportlab wasn't installed (it wasn't — only the upload/
# weekly-report workflows install it, generate workflows never do, and never
# needed to). That broke get_product_cta_url() too, even though it doesn't
# use reportlab at all — only export_manuscript_to_pdf() below does. Moved
# the import into that one function so the common, lightweight path
# (get_product_cta_url, used in every video description) never depends on a
# PDF-export-only dependency the generate workflows don't install.

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
        "gumroad_product_url_id": None,  # the real Gumroad product ID, from your dashboard, needed for Update/Enable API calls
        "price_usd": 19,
        "status": "not_yet_listed",
    },
    "empire-collapse-atlas": {
        "gumroad_url": None,
        "gumroad_product_url_id": None,
        "price_usd": 19,
        "status": "not_yet_listed",
    },
    "faceless-documentary-creator-toolkit": {
        "gumroad_url": None,
        "gumroad_product_url_id": None,
        "price_usd": 29,
        "status": "not_yet_listed",
    },
    # v1 addition — a genuine, purpose-built product for The Collapse
    # Index, bridging both of its real content pillars (documented
    # business/tech collapses + personal finance) rather than reusing
    # an unrelated existing product from a different channel.
    "financial-red-flags-field-guide": {
        "gumroad_url": None,
        "gumroad_product_url_id": None,
        "price_usd": 19,
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
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors

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


def update_gumroad_listing(product_id, gumroad_product_url_id, access_token,
                            description=None, price_cents=None):
    """
    Real Gumroad API call — confirmed via research that Update works even
    though product Creation does not (Gumroad's own current docs
    explicitly say creation isn't supported via API). Requires the
    product to already exist (created once, manually, in the Gumroad
    dashboard) and its real Gumroad product ID.
    """
    if not access_token or not gumroad_product_url_id:
        return {"updated": False, "reason": "missing access_token or gumroad_product_url_id"}
    payload = {"access_token": access_token}
    if description:
        payload["description"] = description
    if price_cents:
        payload["price"] = price_cents
    try:
        r = requests.put(f"https://api.gumroad.com/v2/products/{gumroad_product_url_id}",
                         data=payload, timeout=20)
        if r.status_code == 200:
            return {"updated": True}
        return {"updated": False, "reason": f"API returned {r.status_code}"}
    except Exception as e:
        return {"updated": False, "reason": str(e)}


def set_gumroad_listing_enabled(gumroad_product_url_id, access_token, enabled=True):
    """
    Real Gumroad enable/disable — genuinely useful for the Empire
    Collapse Atlas specifically: it can stay disabled (not visible for
    purchase) while it's honestly empty (no Ch4/Ch5 yet), and this
    function is what would flip it live automatically once it actually
    has real content, rather than needing a manual dashboard visit.
    """
    if not access_token or not gumroad_product_url_id:
        return {"updated": False, "reason": "missing access_token or gumroad_product_url_id"}
    action = "enable" if enabled else "disable"
    try:
        r = requests.put(f"https://api.gumroad.com/v2/products/{gumroad_product_url_id}/{action}",
                         data={"access_token": access_token}, timeout=20)
        if r.status_code == 200:
            return {"updated": True, "enabled": enabled}
        return {"updated": False, "reason": f"API returned {r.status_code}"}
    except Exception as e:
        return {"updated": False, "reason": str(e)}


def sync_all_gumroad_listings(products_root, access_token):
    """
    Real weekly-cadence entry point: for every product with a configured
    Gumroad ID, updates its live description to reflect the real current
    manuscript (chapter count, insight count), and auto-enables it the
    moment it has genuine content for the first time — never disables
    a product that's already live, only ever enables.
    """
    from product_manuscript import PRODUCTS, _load_manuscript_notes
    if not access_token:
        return [{"product_id": p, "updated": False, "reason": "no GUMROAD_ACCESS_TOKEN configured"}
                for p in PRODUCTS]

    results = []
    for product_id, product in PRODUCTS.items():
        cfg = GUMROAD_CONFIG.get(product_id, {})
        gumroad_url_id = cfg.get("gumroad_product_url_id")
        if not gumroad_url_id:
            results.append({"product_id": product_id, "updated": False,
                            "reason": "no real Gumroad listing configured yet"})
            continue

        notes = _load_manuscript_notes(products_root, product_id)
        total_notes = sum(len(v) for v in notes.values())
        chapters_with_content = sum(1 for v in notes.values() if v)

        if total_notes == 0:
            results.append({"product_id": product_id, "updated": False,
                            "reason": "genuinely no content yet — not touching the live listing"})
            continue

        new_description = (f"{product['title']} — a living reference built from real "
                           f"documented cases. Currently {total_notes} real insights across "
                           f"{chapters_with_content}/{len(product['chapters'])} chapters, "
                           f"growing with every new episode.")
        update_result = update_gumroad_listing(product_id, gumroad_url_id, access_token,
                                                description=new_description)
        enable_result = set_gumroad_listing_enabled(gumroad_url_id, access_token, enabled=True)
        results.append({"product_id": product_id, "updated": update_result.get("updated", False),
                        "enabled": enable_result.get("updated", False)})
    return results


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
