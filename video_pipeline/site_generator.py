"""
SITE GENERATOR — the "owned-site layer" from the Media Empire operating
model. Generates companion pages and resource pages as static HTML,
committed to the /docs folder for GitHub Pages to serve for free.

IMPORTANT DESIGN DECISION (stated explicitly, not silently): the demo
document this was built from had every companion page using the exact
same template SENTENCES with only the topic name swapped in ("This
episode goes past the surface version of the story..." verbatim across
all 30 examples, regardless of channel). That is precisely the templated,
low-variation pattern the whole rest of this project's authenticity work
exists to avoid. This module treats the document's structure (which
SECTIONS a page needs) as the blueprint, but generates the actual PROSE
content fresh, per episode, via the same AI provider chain the scripts
already use — with the same specificity discipline (real details, not
generic filler) already proven out in the script-scoring system.

Free-tier only: pure Python + Jinja2 (a lightweight, standard templating
library), static HTML output, no server, no database, no paid hosting —
served by GitHub Pages directly from the repo.
"""

import json
import re
import datetime
from pathlib import Path

try:
    from jinja2 import Environment, FileSystemLoader
except ImportError:
    Environment = None  # caller should treat missing jinja2 as non-fatal

CHANNEL_SITE_CONFIG = {
    "betrayal_deepdive": {
        "slug": "bdd",
        "display_name": "BetrayalDeepDive",
        "dir_name": "betrayaldeepdive",
        "series_default": "Confessions of Betrayal",
    },
    "evidence_room": {
        "slug": "ter",
        "display_name": "The Evidence Room",
        "dir_name": "evidenceroom",
        "series_default": "The Evidence Room: Cold Cases",
    },
    # FIX: control_files was never onboarded here — render_companion_page
    # silently returns None for any channel_id not in this dict, so every
    # Ch3 companion page call was a guaranteed silent no-op.
    "control_files": {
        "slug": "cf",
        "display_name": "The Control Files",
        "dir_name": "controlfiles",
        "series_default": "The Control Files: Case Files",
    },
}

PRODUCT_ROUTES = {
    "betrayal_deepdive": {
        "product_id": "dark-manipulation-tactics-handbook",
        "headline": "Want the full pattern library behind this?",
        "cta_button": "Get the Dark Manipulation Tactics Handbook",
    },
    "evidence_room": {
        "product_id": "faceless-documentary-creator-toolkit",
        "headline": "Want the investigative framework behind this case?",
        "cta_button": "Get the Faceless Documentary Creator Toolkit",
    },
    "control_files": {
        "product_id": "dark-manipulation-tactics-handbook",
        "headline": "Want the full control-systems pattern library?",
        "cta_button": "Get the Dark Manipulation Tactics Handbook",
    },
}

# ══════════════════════════════════════════════════════════════════
# EMAIL CAPTURE CONFIG — FIX: previously every form on every page pointed
# at a literal unconfigured placeholder that would fail if anyone actually
# tried to sign up. This is a genuine one-time manual step, same category
# as GitHub Pages and Gumroad: sign up free at formspree.io (50
# submissions/month, no credit card), create one form, and paste its real
# ID below. Until you do, forms show a clear "not yet active" state
# instead of silently failing.
# ══════════════════════════════════════════════════════════════════
FORMSPREE_FORM_ID = None  # e.g. "abcdwxyz" — set this once you've created a real form

def get_optin_form_action():
    if FORMSPREE_FORM_ID:
        return f"https://formspree.io/f/{FORMSPREE_FORM_ID}"
    return None  # templates check for this and show a real "coming soon" state


def _get_real_product_url(product_id):
    """
    Uses monetization.py's real Gumroad-aware URL resolution when
    available, falling back to the plain local info-page path if that
    module has any issue — companion/resource page generation should
    never break just because the monetization layer had a hiccup.
    """
    try:
        from monetization import get_product_cta_url
        return get_product_cta_url(product_id)
    except Exception:
        return f"../products/{product_id}.html"


def _get_jinja_env(templates_dir=None):
    if Environment is None:
        return None
    if templates_dir is None:
        templates_dir = Path(__file__).parent / "site_templates"
    # FIX (critical, found via direct testing): autoescape was never enabled.
    # Every page here inserts AI-generated prose directly into HTML — without
    # this, a stray '<' or '&' in any AI response passes through completely
    # raw, which can break page rendering or, in a worse case, create a real
    # content-injection risk on the actual public site. Verified the fix
    # with the same test that found the bug: a string containing
    # '<script>...' now renders as literal, escaped text, not executable markup.
    return Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=True)


def generate_companion_page_content(episode_title, episode_summary_source, niche_name,
                                     channel_id, ai_fn):
    """
    Generates the actual prose for a companion page — genuinely written
    per episode, not filled into a fixed sentence. Returns a dict with
    why_it_matters, episode_summary, framework_name, framework_description,
    and takeaways (list of 5). Fails safe with honest, still-real fallback
    content (not a copy of the demo document's generic sentences) if the
    AI call fails.
    """
    prompt = f"""You are writing the companion web page for a documentary episode.

EPISODE TITLE: {episode_title}
EPISODE CONTENT (for reference, do not just repeat this): {episode_summary_source[:600]}
CHANNEL NICHE: {niche_name}

Write 4 things, each genuinely specific to THIS episode's actual content —
not a generic template that could apply to any episode. Reference real
details from the episode content above.

Return ONLY valid JSON with these exact keys:
{{
  "why_it_matters": "2-3 sentences on why THIS specific case/story is worth studying, referencing a real detail from it",
  "episode_summary": "3-4 sentences summarizing what actually happens in THIS episode, with specific details",
  "framework_name": "A short, specific name for the pattern/framework this episode reveals (not generic - e.g. 'The Isolation-Then-Dependency Loop' not 'A Framework')",
  "framework_description": "2-3 sentences explaining this specific framework and how it applied in this exact case",
  "takeaways": ["5 short, specific takeaway strings, each referencing a real element of this episode, not generic advice"]
}}"""
    try:
        raw = ai_fn(prompt, tokens=500)
        if raw:
            json_match = re.search(r'\{.*\}', raw, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                if all(k in data for k in ("why_it_matters", "episode_summary",
                                             "framework_name", "framework_description", "takeaways")):
                    return data
    except Exception:
        pass
    # Honest fallback — still references the real title, not a generic
    # sentence that could apply to any episode
    return {
        "why_it_matters": f"\"{episode_title}\" is covered in full in the linked video, with sourcing "
                           f"and additional context available there.",
        "episode_summary": f"See the full episode for the complete breakdown of \"{episode_title}.\"",
        "framework_name": "Full Analysis in Video",
        "framework_description": "The complete pattern breakdown for this case is covered in the video itself.",
        "takeaways": [
            "Watch the full episode for the complete breakdown.",
            "Sourcing and context are covered in the video.",
            "See related cases below for similar patterns.",
        ],
    }


def render_companion_page(episode_data, output_root, ai_fn, templates_dir=None):
    """
    episode_data must contain: episode_number, episode_title, video_url,
    channel_id, niche_name, publish_date, script_excerpt (for content
    generation), related_links (list of {title, url}, optional).

    templates_dir defaults to this module's own bundled site_templates/
    folder — pass an explicit path only if testing against a different
    template set.

    Writes the rendered HTML file to output_root/<channel_dir>/ep<N>.html
    and returns the relative path written, or None on failure (non-fatal
    by design — a page-generation failure should never break a video
    publish).
    """
    env = _get_jinja_env(templates_dir)
    if env is None:
        return None

    channel_cfg = CHANNEL_SITE_CONFIG.get(episode_data["channel_id"])
    if not channel_cfg:
        return None  # channel not yet onboarded to the site layer

    content = generate_companion_page_content(
        episode_data["episode_title"],
        episode_data.get("script_excerpt", ""),
        episode_data.get("niche_name", ""),
        episode_data["channel_id"],
        ai_fn,
    )

    product_route = PRODUCT_ROUTES.get(episode_data["channel_id"], {})

    try:
        template = env.get_template("companion_page.html")
        html = template.render(
            page_title=episode_data["episode_title"],
            meta_description=content["why_it_matters"][:160],
            channel_slug=channel_cfg["slug"],
            channel_display_name=channel_cfg["display_name"],
            root_path="../",
            episode_number=episode_data["episode_number"],
            episode_title=episode_data["episode_title"],
            publish_date=episode_data.get("publish_date", datetime.date.today().isoformat()),
            series_name=episode_data.get("series_name", channel_cfg["series_default"]),
            why_it_matters=content["why_it_matters"],
            episode_summary=content["episode_summary"],
            framework_name=content["framework_name"],
            framework_description=content["framework_description"],
            takeaways=content["takeaways"],
            video_url=episode_data["video_url"],
            product_cta_headline=product_route.get("headline", "Go deeper"),
            product_cta_body="Every case that fits this pattern feeds one growing reference — "
                              "get the full breakdown, not just this one case.",
            product_url=_get_real_product_url(product_route.get('product_id', '')),
            product_cta_button_text=product_route.get("cta_button", "Learn more"),
            optin_headline="Get new case breakdowns before they're public",
            optin_body="One email when a new companion page goes live. No spam, unsubscribe anytime.",
            optin_form_action=get_optin_form_action(),
            related_links=episode_data.get("related_links", []),
        )
    except Exception:
        return None

    out_dir = Path(output_root) / channel_cfg["dir_name"]
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"ep{episode_data['episode_number']}.html"
    try:
        out_path.write_text(html, encoding="utf-8")
        return str(out_path)
    except Exception:
        return None


def generate_resource_page_content(niche_name, channel_id, episode_titles, ai_fn):
    """
    Generates the actual prose for a resource page covering a genuine
    theme/pattern across multiple real episodes — not a generic keyword-
    stuffing page. Returns dict with resource_title, resource_intro,
    framework_section_title, framework_content (HTML-safe string).
    """
    titles_list = "\n".join(f"- {t}" for t in episode_titles[:15])
    prompt = f"""You are writing an evergreen reference page for a documentary
channel, covering a real recurring theme across these actual published episodes:

NICHE: {niche_name}
EPISODES COVERING THIS THEME:
{titles_list}

Write a genuine field-guide page about this real pattern — not a generic
"top 10 tips" listicle. Reference that this is built from real documented
cases, not abstract theory.

Return ONLY valid JSON:
{{"resource_title": "specific, real title for this theme (not generic)",
  "resource_intro": "2-3 sentences framing why this pattern matters, referencing that it's drawn from real documented cases",
  "framework_section_title": "a specific section header for the core framework",
  "framework_content": "3-5 sentences or a short HTML list (use <ul><li> tags) laying out the actual real pattern/framework, specific enough to be genuinely useful, not generic advice"}}"""
    try:
        raw = ai_fn(prompt, tokens=500)
        if raw:
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                data = json.loads(match.group())
                if all(k in data for k in ("resource_title", "resource_intro",
                                             "framework_section_title", "framework_content")):
                    return data
    except Exception:
        pass
    return {
        "resource_title": f"{niche_name.replace('_', ' ').title()} — Case Index",
        "resource_intro": "This page indexes real documented cases covering this theme.",
        "framework_section_title": "Covered Cases",
        "framework_content": "See the case list below for the full breakdown of each.",
    }


def render_resource_page(niche_name, channel_id, episodes, output_root, ai_fn, templates_dir=None):
    """
    episodes: list of Publishing Archive entries for this niche cluster
    (each with title, companion_page_url). Generates/overwrites the
    resource page for this niche — safe to call repeatedly as the
    cluster grows, since it always reflects the CURRENT full episode list.
    """
    env = _get_jinja_env(templates_dir)
    if env is None:
        return None

    channel_cfg = CHANNEL_SITE_CONFIG.get(channel_id)
    if not channel_cfg:
        return None

    episode_titles = [e["title"] for e in episodes]
    content = generate_resource_page_content(niche_name, channel_id, episode_titles, ai_fn)
    product_route = PRODUCT_ROUTES.get(channel_id, {})

    related_episodes = [
        {"title": e["title"], "url": f"../{channel_cfg['dir_name']}/{e['companion_page_url'].split('/')[-1]}"}
        for e in sorted(episodes, key=lambda e: e.get("published_at", ""), reverse=True)
    ]

    try:
        template = env.get_template("resource_page.html")
        html = template.render(
            page_title=content["resource_title"],
            meta_description=content["resource_intro"][:160],
            channel_slug=channel_cfg["slug"],
            channel_display_name=channel_cfg["display_name"],
            root_path="../",
            resource_title=content["resource_title"],
            resource_intro=content["resource_intro"],
            framework_section_title=content["framework_section_title"],
            framework_content=content["framework_content"],
            related_episodes=related_episodes,
            product_cta_headline=product_route.get("headline", "Go deeper"),
            product_cta_body="This whole pattern, and every other one like it, is collected "
                              "in one growing reference.",
            product_url=_get_real_product_url(product_route.get('product_id', '')),
            product_cta_button_text=product_route.get("cta_button", "Learn more"),
            optin_headline="Get new field guides before they're public",
            optin_body="One email when a new resource page goes live. No spam, unsubscribe anytime.",
            optin_form_action=get_optin_form_action(),
        )
    except Exception:
        return None

    out_dir = Path(output_root) / "resources"
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_niche = re.sub(r'[^a-z0-9]+', '-', niche_name.lower())
    out_path = out_dir / f"{channel_cfg['dir_name']}-{safe_niche}.html"
    try:
        out_path.write_text(html, encoding="utf-8")
        return str(out_path)
    except Exception:
        return None


def generate_legal_pages(docs_root, templates_dir=None):
    """
    Generates privacy policy and terms of service pages with the current
    date. HONEST NOTE: the content is a real, plain-language starting
    point, not a substitute for actual legal review — especially once
    real product sales and email collection are genuinely active.
    """
    import datetime as _dt
    env = _get_jinja_env(templates_dir)
    if env is None:
        return []
    written = []
    today = _dt.date.today().isoformat()
    for template_name, out_name in [("privacy_policy.html", "privacy.html"),
                                      ("terms_of_service.html", "terms.html")]:
        try:
            template = env.get_template(template_name)
            html = template.render(today=today)
            out_path = Path(docs_root) / out_name
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(html, encoding="utf-8")
            written.append(str(out_path))
        except Exception:
            pass
    return written


def generate_seo_files(docs_root, site_base_url):
    """
    Generates sitemap.xml and robots.txt — previously entirely missing.
    Without these, search engines have no reliable way to discover every
    page on the site or know it's safe to crawl. Scans the actual docs/
    folder for real HTML files rather than guessing what exists.
    site_base_url should be the real published URL, e.g.
    'https://<username>.github.io/<repo>/' or a real custom domain.
    """
    docs_root = Path(docs_root)
    base = site_base_url.rstrip("/") + "/"

    urls = []
    for html_file in docs_root.rglob("*.html"):
        rel_path = html_file.relative_to(docs_root).as_posix()
        urls.append(base + rel_path)

    sitemap_lines = ['<?xml version="1.0" encoding="UTF-8"?>',
                      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url in sorted(urls):
        sitemap_lines.append(f"  <url><loc>{url}</loc></url>")
    sitemap_lines.append("</urlset>")

    try:
        (docs_root / "sitemap.xml").write_text("\n".join(sitemap_lines), encoding="utf-8")
        (docs_root / "robots.txt").write_text(
            f"User-agent: *\nAllow: /\nSitemap: {base}sitemap.xml\n", encoding="utf-8"
        )
        return {"sitemap_urls": len(urls), "written": True}
    except Exception as e:
        return {"written": False, "reason": str(e)}


def generate_all_resource_pages(channel_id, channel_dir, output_root, ai_fn, templates_dir=None):
    """
    The weekly-cadence entry point: checks every niche cluster in the
    Publishing Archive and regenerates the resource page for each one
    that has enough episodes (min_cluster_size, see publishing_archive.py).
    Safe to run repeatedly — always reflects the current full cluster.
    """
    from publishing_archive import get_niche_clusters
    clusters = get_niche_clusters(channel_dir)
    results = []
    for niche_name, episodes in clusters.items():
        path = render_resource_page(niche_name, channel_id, episodes, output_root, ai_fn, templates_dir)
        results.append({"niche": niche_name, "episode_count": len(episodes), "path": path})
    return results


def generate_site_navigation(channel_dirs: dict, output_root, templates_dir=None):
    """
    Regenerates the site's navigation pages: root index (lists both
    channels), each channel's home page (lists its recent episodes +
    field guides), and the resources index (lists every field guide
    across the whole site). Reads directly from each channel's own
    Publishing Archive — call this after resource-page generation in
    the weekly cadence, so it reflects the current real state.

    channel_dirs: {"betrayal_deepdive": "<path to that channel's SCRIPT_DIR>",
                   "evidence_room": "<path to that channel's SCRIPT_DIR>"}
    """
    from publishing_archive import load_archive

    env = _get_jinja_env(templates_dir)
    if env is None:
        return []

    written = []
    all_channel_summaries = []
    all_resource_links = []

    for channel_id, channel_dir in channel_dirs.items():
        cfg = CHANNEL_SITE_CONFIG.get(channel_id)
        if not cfg:
            continue

        archive = load_archive(channel_dir)
        archive_sorted = sorted(archive, key=lambda e: e.get("published_at", ""), reverse=True)
        recent_episodes = [
            {"title": e["title"], "url": e["companion_page_url"].split("/")[-1]}
            for e in archive_sorted[:15]
        ]

        # Real resource-page links for this channel — check which niche
        # clusters actually have a rendered file, not just guessed names.
        resources_dir = Path(output_root) / "resources"
        channel_resource_links = []
        if resources_dir.exists():
            for f in resources_dir.glob(f"{cfg['dir_name']}-*.html"):
                niche_guess = f.stem.replace(f"{cfg['dir_name']}-", "").replace("-", " ").title()
                link = {"title": f"{niche_guess} — Field Guide", "url": f"../resources/{f.name}"}
                channel_resource_links.append(link)
                all_resource_links.append({"title": f"{cfg['display_name']}: {niche_guess}",
                                            "url": f"resources/{f.name}"})

        try:
            template = env.get_template("channel_index.html")
            html = template.render(
                page_title=cfg["display_name"],
                meta_description=f"Case breakdowns and field guides from {cfg['display_name']}.",
                channel_slug=cfg["slug"],
                channel_display_name=cfg["display_name"],
                root_path="../",
                channel_description=f"Investigative case breakdowns from {cfg['display_name']}.",
                episodes=recent_episodes,
                resource_links=channel_resource_links,
            )
            out_path = Path(output_root) / cfg["dir_name"] / "index.html"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(html, encoding="utf-8")
            written.append(str(out_path))
        except Exception:
            pass

        all_channel_summaries.append({
            "dir_name": cfg["dir_name"],
            "display_name": cfg["display_name"],
            "description": f"{len(archive)} documented cases and counting.",
        })

    # Site root index
    try:
        template = env.get_template("site_index.html")
        html = template.render(channels=all_channel_summaries)
        out_path = Path(output_root) / "index.html"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")
        written.append(str(out_path))
    except Exception:
        pass

    # Resources index (across all channels)
    try:
        template = env.get_template("resources_index.html")
        html = template.render(resources=all_resource_links)
        out_path = Path(output_root) / "resources" / "index.html"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")
        written.append(str(out_path))
    except Exception:
        pass

    return written


def render_all_product_pages(products_root, output_root, templates_dir=None):
    """
    Generates the real product landing pages — one per product — pulling
    genuine chapter/note-count data from the manuscript and the real (or
    not-yet-configured) Gumroad URL. Safe to run repeatedly; always
    reflects current state, including products with zero content yet.
    """
    from product_manuscript import PRODUCTS, _load_manuscript_notes
    from monetization import GUMROAD_CONFIG, get_product_cta_url
    import datetime as _dt

    env = _get_jinja_env(templates_dir)
    if env is None:
        return []

    written = []
    for product_id, product in PRODUCTS.items():
        notes = _load_manuscript_notes(products_root, product_id)
        total_notes = sum(len(v) for v in notes.values())
        gumroad_cfg = GUMROAD_CONFIG.get(product_id, {})

        try:
            template = env.get_template("product_page.html")
            html = template.render(
                product_title=product["title"],
                product_description=f"A growing reference built from real documented cases "
                                     f"across our channels — {product['title']}.",
                chapters=product["chapters"],
                note_count=total_notes,
                last_updated=_dt.date.today().isoformat(),
                is_listed=bool(gumroad_cfg.get("gumroad_url")),
                price_usd=gumroad_cfg.get("price_usd", "—"),
                optin_form_action=get_optin_form_action(),
                gumroad_url=get_product_cta_url(product_id),
            )
            out_path = Path(output_root) / "products" / f"{product_id}.html"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(html, encoding="utf-8")
            written.append(str(out_path))
        except Exception:
            pass

    return written
