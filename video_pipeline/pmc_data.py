"""
Europe PMC / PubMed Central Open Access integration for the clinical-case
documentary channel (Ch1 slot, replacing the dark-documentary pipeline).

WHY THIS EXISTS
---------------
Same root fix already shipped for Ch5's finance niches (fred_data.py) and
Ch1's historical cases: the script engine must be fed REAL, sourced facts
rather than AI-invented details dressed up to sound documented. Here the
source is the published medical literature itself -- a real peer-reviewed
case report, with the real presentation, real reported values, real
diagnostic path, and (critically) the real figures from that same paper.

LICENSING -- READ BEFORE CHANGING ANYTHING HERE
-----------------------------------------------
Only CC BY articles from the PMC Open Access Subset are eligible. CC BY
permits commercial reuse INCLUDING figures, but it is conditional on
attribution. Every fetch therefore returns a ready-built citation string,
and callers must render it both on-screen at the figure and in the video
description. A missing attribution converts a licensed use into an
unlicensed one -- build_citation() is not optional decoration.

We deliberately do NOT accept CC BY-NC (non-commercial) or CC BY-ND
(no-derivatives) articles: a monetised YouTube video is a commercial
derivative work, so those licenses do not cover this use.

NETWORK POSTURE
---------------
Every public function returns None (or an empty structure) on any failure,
so the pipeline degrades to its existing behaviour rather than crashing.
This sandbox's network policy blocks the EBI endpoint (confirmed live,
same as the FRED and Wikimedia endpoints), so the request/parse logic here
is verified against mocked responses; real end-to-end verification happens
on the GitHub Actions runner where the pipeline actually executes.
"""
import re
import time
import random
import requests

SEARCH_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
FULLTEXT_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"

# Historical, stable pattern for PMC figure binaries. NOTE (honest gap):
# this URL shape could not be verified live from this sandbox. The figure
# fetch below treats a non-200 or undersized response as "no figure" and
# falls through to the Wikimedia/anatomy path, so an incorrect pattern
# degrades gracefully to fewer FIGURE segments rather than breaking a run.
FIGURE_URL = "https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/bin/{fname}"

# Fallbacks, tried in order. The single pattern above was flagged as
# unverified when this module was written and is still unverified -- the
# sandbox blocks both hosts, so it has never been exercised against a real
# article. One unproven URL with no alternative meant a wrong guess would
# silently cost the FIGURE register 30% of the visual mix on every episode,
# with nothing in the log to say why. Europe PMC mirrors the same binaries
# under its own host, so a second pattern is cheap insurance.
# pmc.ncbi.nlm.nih.gov is the CANONICAL host: PMC moved off
# www.ncbi.nlm.nih.gov/pmc/... and the old path now redirects. It is listed
# first because relying on a redirect for the one asset that differentiates
# this channel is a needless dependency.
FIGURE_URL_PATTERNS = (
    "https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/bin/{fname}",
    "https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/bin/{fname}",
    "https://europepmc.org/articles/{pmcid}/bin/{fname}",
)

USER_AGENT = ("NoKnownCause-ClinicalPipeline/1.0 "
              "(https://github.com/BetrayalDeepDive/betrayal-bot; automation)")

# Licenses that actually permit a monetised derivative work. Anything else
# -- NC, ND, or an unstated license -- is rejected outright.
ACCEPTABLE_LICENSES = ("cc by", "cc-by", "ccby", "cc0", "public domain")
REJECTED_LICENSE_MARKERS = ("nc", "nd", "non-commercial", "noderiv")

# Real Europe PMC query fragments per niche. Every query is constrained to
# open-access, full-text-available, CC BY case reports -- the eligibility
# rules are baked into the query itself rather than filtered afterwards, so
# ineligible articles are never even retrieved.
_BASE_FILTER = 'OPEN_ACCESS:Y AND HAS_FT:Y AND LICENSE:"cc by"'

# Papers whose figures this channel can never show.
#
# Found on run 30561361514: the rare_disease_cases niche returned a World
# Journal of Surgical Oncology paper (PMC3554459) with 0 usable figures. That
# was NOT a bug -- TITLE:"rare" legitimately matches "A rare ... tumour: a
# case report", and is_graphic_figure then correctly rejected every
# intraoperative view, resected specimen and excised-tissue photomicrograph
# in it. The article was simply unshowable, and FIGURE is 30% of the visual
# mix, so the episode would have been visually gutted before rendering began.
#
# Screening at the figure was too late. Excluding these at SEARCH time means
# the eight non-surgical niches stop surfacing papers whose imagery is
# guaranteed to be filtered away.
_NO_GRAPHIC = ('NOT (TITLE:"resection" OR TITLE:"intraoperative" OR '
               'TITLE:"surgical management" OR ABSTRACT:"intraoperatively" OR '
               'ABSTRACT:"resected specimen" OR ABSTRACT:"gross specimen")')

NICHE_PMC_QUERIES = {
    "toxicology_cases": (
        f'{_BASE_FILTER} AND PUB_TYPE:"Case Reports" AND '
        '(TITLE:"poisoning" OR TITLE:"toxicity" OR TITLE:"overdose" OR TITLE:"intoxication")'
        f' AND {_NO_GRAPHIC}'
    ),
    "diagnostic_odyssey": (
        f'{_BASE_FILTER} AND PUB_TYPE:"Case Reports" AND '
        '(ABSTRACT:"delayed diagnosis" OR ABSTRACT:"misdiagnosed" OR ABSTRACT:"diagnostic challenge")'
        f' AND {_NO_GRAPHIC}'
    ),
    "rare_disease_cases": (
        f'{_BASE_FILTER} AND PUB_TYPE:"Case Reports" AND '
        '(TITLE:"rare" OR ABSTRACT:"rare disease" OR ABSTRACT:"first reported case")'
        f' AND {_NO_GRAPHIC}'
    ),
    # EVERY niche below must select PUB_TYPE:"Case Reports".
    #
    # Five of these ten did not, and run 30637537806 shows exactly what that
    # costs. senior_health_longevity returned Cell 2013, Archives of
    # Toxicology 2023 and Signal Transduction and Targeted Therapy 2022 --
    # basic-science research and review papers about ageing, with no patient,
    # no chronology and no differential in them. Structure extraction scored
    # 9, 5, 2 and 2 across four candidates (0 differentials and 0 timeline
    # events on three of them), the script was written about sarcopenia
    # epidemiology rather than a patient, and the episode died at the title
    # gate on a headline about population statistics.
    #
    # This channel's unit is one patient's case. A query that does not say so
    # is not a narrower version of the right query -- it is the wrong corpus.
    "senior_health_longevity": (
        f'{_BASE_FILTER} AND PUB_TYPE:"Case Reports" AND '
        '(TITLE:"elderly" OR TITLE:"geriatric" OR TITLE:"octogenarian" '
        'OR TITLE:"nonagenarian" OR ABSTRACT:"an elderly patient" '
        'OR ABSTRACT:"older adult")'
        f' AND {_NO_GRAPHIC}'
    ),
    "medical_mystery_outbreak": (
        f'{_BASE_FILTER} AND PUB_TYPE:"Case Reports" AND '
        '(TITLE:"outbreak" OR TITLE:"cluster" OR ABSTRACT:"index case" '
        'OR ABSTRACT:"epidemiological investigation" OR ABSTRACT:"contact tracing")'
        f' AND {_NO_GRAPHIC}'
    ),
    # Retargeted away from the operative field. The old query
    # (ABSTRACT:"operative" OR TITLE:"resection") selected exactly the papers
    # whose every figure is_graphic_figure rejects, making this the one niche
    # structurally guaranteed to render with no figures. It now selects on the
    # pre-operative imaging and the decision that preceded the incision --
    # showable, and the more interesting half of the case regardless.
    "surgical_case_studies": (
        f'{_BASE_FILTER} AND PUB_TYPE:"Case Reports" AND '
        '(ABSTRACT:"preoperative imaging" OR ABSTRACT:"unexpected finding" '
        'OR ABSTRACT:"anatomical variant" OR ABSTRACT:"incidental finding") '
        f'AND {_NO_GRAPHIC}'
    ),
    "neurology_cases": (
        f'{_BASE_FILTER} AND PUB_TYPE:"Case Reports" AND '
        '(TITLE:"neurological" OR TITLE:"encephalitis" OR TITLE:"seizure" '
        'OR TITLE:"aphasia" OR TITLE:"amnesia")'
        f' AND {_NO_GRAPHIC}'
    ),
    # Retargeted from "papers ABOUT the history of medicine" (reviews and
    # essays, no patient) to "the case that was itself a first".
    "medical_history": (
        f'{_BASE_FILTER} AND PUB_TYPE:"Case Reports" AND '
        '(ABSTRACT:"first reported case" OR ABSTRACT:"first described" '
        'OR ABSTRACT:"historically" OR ABSTRACT:"previously unreported")'
        f' AND {_NO_GRAPHIC}'
    ),
    # Retargeted from drug-discovery reviews to the patient the drug happened
    # to: adverse reactions, unexpected responses, first human use.
    "drug_discovery_stories": (
        f'{_BASE_FILTER} AND PUB_TYPE:"Case Reports" AND '
        '(ABSTRACT:"adverse drug reaction" OR ABSTRACT:"drug-induced" '
        'OR ABSTRACT:"unexpected response" OR TITLE:"induced by")'
        f' AND {_NO_GRAPHIC}'
    ),
    "sleep_science": (
        f'{_BASE_FILTER} AND PUB_TYPE:"Case Reports" AND '
        '(TITLE:"sleep" OR TITLE:"insomnia" OR TITLE:"narcolepsy" '
        'OR TITLE:"parasomnia" OR TITLE:"circadian")'
        f' AND {_NO_GRAPHIC}'
    ),
}

MEDICAL_NICHE_NAMES = set(NICHE_PMC_QUERIES.keys())

# Rule 4 of the policy spec: no graphic surgical or wound imagery -- a named
# YouTube limited-ads trigger. Figures are screened by their own caption and
# label text, which in published papers reliably describes what is shown.
_GRAPHIC_FIGURE_MARKERS = (
    "intraoperative", "intra-operative", "operative field", "resected specimen",
    "gross specimen", "autopsy", "cadaver", "dissection", "amputat",
    "wound", "ulcer", "necrosis", "necrotic", "gangrene", "abscess",
    "laceration", "avuls", "degloving", "excised", "bleeding", "haemorrhagic tissue",
    "post-mortem", "postmortem", "incision", "surgical site",
)

# Figure types that are safe AND are what this channel actually wants on
# screen. Tiered deliberately: this channel's whole differentiator is
# showing THIS patient's real imaging, so a real scan/trace outranks a
# generic mechanism schematic that could illustrate any paper.
#
# FIX (caught by a real test during this build): these were matched as bare
# substrings, so the short acronyms false-positived badly -- "ct" matched
# inside "reaction", "function", "structure", "conduction", and "pet"
# matched inside "petechial". A mechanism diagram was consequently
# outranking the patient's actual CT. Short/ambiguous tokens are now
# matched on word boundaries; only unambiguous long tokens stay as
# substrings (so "histolog" still catches "histological"/"histology").
_IMAGING_WORD_TOKENS = (
    "ct", "mri", "ecg", "ekg", "eeg", "pet", "xray", "us", "spect",
)
_IMAGING_SUBSTRINGS = (
    "x-ray", "radiograph", "ultrasound", "echocardiog", "electrocardiog",
    "electroencephalog", "angiogram", "angiograph", "tomograph", "sonograph",
    "histolog", "micrograph", "immunohistochem", "staining", "biopsy",
    "scan", "imaging",
)
_DIAGRAM_SUBSTRINGS = (
    "diagram", "schematic", "flow chart", "flowchart", "graph", "plot",
    "timeline", "algorithm", "pedigree", "chart",
)


def _headers():
    return {"User-Agent": USER_AGENT}


def _license_ok(license_str):
    """
    True only for licenses that permit a monetised derivative work.
    Rejects NC/ND explicitly -- checked BEFORE the allow-list, since a
    string like "cc by-nc" contains "cc by" as a substring and would
    otherwise pass. This ordering is the whole point of the function.
    """
    if not license_str:
        return False
    low = license_str.lower().replace("_", "-")
    tokens = re.split(r"[^a-z0-9]+", low)
    if any(marker in tokens for marker in ("nc", "nd")):
        return False
    if any(marker in low for marker in ("non-commercial", "noncommercial", "noderiv", "no-deriv")):
        return False
    return any(ok in low for ok in ACCEPTABLE_LICENSES)


def search_cc_by_cases(niche_name, page_size=25):
    """
    Real Europe PMC search for CC BY, open-access, full-text case reports
    matching this niche. Returns a list of article dicts (raw API 'result'
    objects), or [] on any failure / unknown niche.
    """
    query = NICHE_PMC_QUERIES.get(niche_name)
    if not query:
        return []
    try:
        r = requests.get(SEARCH_URL, params={
            "query": query,
            "format": "json",
            "resultType": "core",   # needed for license + author + journal fields
            "pageSize": page_size,
            "sort": "CITED desc",   # better-cited cases tend to be better documented
        }, headers=_headers(), timeout=25)
        if r.status_code != 200:
            return []
        results = r.json().get("resultList", {}).get("result", [])
        # Defence in depth: the query already filters on license, but never
        # trust a remote filter for a licensing decision -- re-check locally.
        return [a for a in results
                if a.get("pmcid") and _license_ok(a.get("license", ""))]
    except Exception:
        return []


def fetch_full_text(pmcid):
    """Raw JATS XML for one article. None on any failure."""
    if not pmcid:
        return None
    try:
        r = requests.get(FULLTEXT_URL.format(pmcid=pmcid),
                         headers=_headers(), timeout=30)
        if r.status_code != 200 or len(r.text) < 500:
            return None
        return r.text
    except Exception:
        return None


def _strip_tags(xml_fragment):
    """Plain readable text from a JATS fragment (drops inline markup/refs)."""
    txt = re.sub(r"<xref[^>]*>.*?</xref>", "", xml_fragment, flags=re.S)
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = txt.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return re.sub(r"\s+", " ", txt).strip()


def extract_case_narrative(xml, min_chars=400):
    """
    The real case-presentation prose -- the part a script actually needs.

    Published case reports overwhelmingly use a section titled some variant
    of "Case Report" / "Case Presentation" / "Case Description". We look for
    that section specifically rather than dumping the whole paper, so the
    script engine is fed the clinical narrative rather than the literature
    review and statistics boilerplate around it.
    """
    if not xml:
        return None
    for pattern in (
        r"<sec[^>]*>\s*<title>\s*Case (?:Report|Presentation|Description|History)[^<]*</title>(.*?)</sec>",
        r"<sec[^>]*>\s*<title>\s*(?:Case|Clinical Case|Patient)[^<]*</title>(.*?)</sec>",
    ):
        m = re.search(pattern, xml, flags=re.S | re.I)
        if m:
            text = _strip_tags(m.group(1))
            if len(text) >= min_chars:
                return text
    # Fallback: the abstract is always real, sourced text even when the
    # section titles don't match the expected shapes.
    m = re.search(r"<abstract[^>]*>(.*?)</abstract>", xml, flags=re.S | re.I)
    if m:
        text = _strip_tags(m.group(1))
        if len(text) >= min_chars // 2:
            return text
    return None


def is_graphic_figure(caption):
    """
    Policy rule 4 gate for a single figure. True = REJECT.

    Fails closed on empty captions: an unlabelled figure can't be screened,
    and an unscreenable figure is not worth the limited-ads risk.
    """
    if not caption or not caption.strip():
        return True
    low = caption.lower()
    return any(marker in low for marker in _GRAPHIC_FIGURE_MARKERS)


def _figure_preference_score(caption):
    """
    Higher = better suited to this channel. Real patient imaging scores 3
    per hit, generic diagrams 1, so THIS patient's actual CT/ECG always
    outranks a mechanism schematic that could belong to any paper.

    Short acronyms are word-boundary matched (see the marker-list comment):
    bare-substring matching made "reaction"/"function"/"structure" register
    as CT scans.
    """
    low = (caption or "").lower()
    score = 0
    for token in _IMAGING_WORD_TOKENS:
        if re.search(rf"\b{re.escape(token)}\b", low):
            score += 3
    for frag in _IMAGING_SUBSTRINGS:
        if frag in low:
            score += 3
    for frag in _DIAGRAM_SUBSTRINGS:
        if frag in low:
            score += 1
    return score


def extract_figures(xml, pmcid):
    """
    Screened, ranked figure inventory for one article.

    Returns a list of dicts: {label, caption, filename, url, score},
    graphic/unscreenable figures already removed (rule 4), best-suited
    imaging/diagram figures first. Empty list is a normal, safe outcome --
    callers fall back to the ANATOMY register.
    """
    if not xml:
        return []
    figures = []
    for fig_xml in re.findall(r"<fig\b.*?</fig>", xml, flags=re.S | re.I):
        cap_m = re.search(r"<caption[^>]*>(.*?)</caption>", fig_xml, flags=re.S | re.I)
        caption = _strip_tags(cap_m.group(1)) if cap_m else ""
        lab_m = re.search(r"<label[^>]*>(.*?)</label>", fig_xml, flags=re.S | re.I)
        label = _strip_tags(lab_m.group(1)) if lab_m else ""
        if is_graphic_figure(f"{label} {caption}"):
            continue
        href_m = re.search(r'xlink:href="([^"]+)"', fig_xml)
        if not href_m:
            continue
        fname = href_m.group(1)
        if not re.search(r"\.(jpg|jpeg|png|gif|tif|tiff)$", fname, flags=re.I):
            fname = f"{fname}.jpg"   # JATS often omits the extension
        figures.append({
            "pmcid": pmcid,
            "label": label,
            "caption": caption,
            "filename": fname,
            "url": FIGURE_URL.format(pmcid=pmcid, fname=fname),
            "score": _figure_preference_score(f"{label} {caption}"),
        })
    figures.sort(key=lambda f: f["score"], reverse=True)
    return figures


_ARTICLE_IMG_CACHE = {}


def _article_image_urls(pmcid, log_fn=None):
    """
    The figure URLs the article page itself publishes.

    WHY THIS EXISTS, AND WHY IT IS NOT A FOURTH GUESS.

    Every figure URL in this module was a hand-written path template, and the
    comment above FIGURE_URL_PATTERNS said plainly that the sandbox could not
    reach either host so none had ever been exercised. Run 30717615638 was
    the first to actually try them at scale and the answer was unambiguous:
    77 download attempts across 10 candidate papers, ZERO successes.

      www.ncbi.nlm.nih.gov/pmc/articles/PMCxxxxx/bin/f1.jpg  -> 404
      pmc.ncbi.nlm.nih.gov/articles/PMCxxxxx/bin/f1.jpg      -> 404
      europepmc.org/articles/PMCxxxxx/bin/f1.jpg             -> 403

    So the FIGURE register -- the largest single share of the visual mix, and
    the only register that shows the REAL images from the real paper -- has
    been silently disabled on every episode this channel has ever produced.
    The 404s prove the host is reachable and only the path is wrong; the 403
    is Europe PMC refusing a bot, not a missing file.

    Adding a fourth template would repeat the mistake that caused this: an
    unverifiable guess, wrong for months, costing a third of the visuals. So
    this does not guess. It fetches the article page and reads the image URLs
    the page itself links, which is by construction whatever PMC currently
    serves, and survives any future CDN path change without a code edit.
    """
    if pmcid in _ARTICLE_IMG_CACHE:
        return _ARTICLE_IMG_CACHE[pmcid]
    urls = []
    for page in (f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/",
                 f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/"):
        try:
            r = requests.get(page, headers=_headers(), timeout=30)
            if r.status_code != 200 or not r.text:
                if log_fn:
                    log_fn(f"    article page {r.status_code} {page[:70]}")
                continue
            html = r.text
            found = re.findall(r'<img[^>]+src="([^"]+)"', html, flags=re.I)
            found += re.findall(r'<source[^>]+srcset="([^"\s]+)', html, flags=re.I)
            for u in found:
                if not re.search(r"\.(jpg|jpeg|png|gif)(\?|$)", u, flags=re.I):
                    continue
                if u.startswith("//"):
                    u = "https:" + u
                elif u.startswith("/"):
                    u = "https://pmc.ncbi.nlm.nih.gov" + u
                elif not u.startswith("http"):
                    u = page + u.lstrip("./")
                # Interface furniture, not article figures.
                if re.search(r"(?i)/(corehtml|coreutils|icons?|logos?|spacer)/", u):
                    continue
                if u not in urls:
                    urls.append(u)
            if urls:
                if log_fn:
                    log_fn(f"    article page listed {len(urls)} image URL(s)")
                break
        except Exception as e:
            if log_fn:
                log_fn(f"    article page error {type(e).__name__} {page[:60]}")
    _ARTICLE_IMG_CACHE[pmcid] = urls
    return urls


_OA_PACKAGE_CACHE = {}


def _oa_package_images(pmcid, log_fn=None):
    """Every image in this article's OA package, as {filename: bytes}.

    THE ONLY ROUTE THAT ACTUALLY WORKS. Verified on the runner, two papers,
    against nine alternatives that all failed:

        europepmc render .............. HTTP 500
        cdn.ncbi blobs (.jpg/.png) .... HTTP 404
        ncbi /bin/ .................... serves text/html, not an image
        europepmc /bin/ ............... connection dropped
        europepmc supplementaryFiles .. HTTP 500
        PMC OA on S3 (comm/noncomm) ... HTTP 404
        OA package at the advertised path ... 550 No such file

    The last one is the interesting failure. NCBI moved its whole open-access
    FTP distribution into /pub/pmc/deprecated/ -- oa_package, oa_bulk, oa_pdf
    and the file lists all live there now -- but the OA Web Service still
    hands out the pre-move path. Deprecated is not deleted: the same file is
    served, over HTTPS, one directory down. PMC7857393 came back as a 7.15 MB
    gzip holding eight images, the largest of which decodes at 4380x4683.

    This is also why the article-page scraper could never work: both PMC and
    Europe PMC render their figures in JavaScript and serve zero <img> tags.

    One fetch per paper, cached, because the package holds every figure at
    once -- fetching it per figure would download the same 7 MB nine times.
    """
    if pmcid in _OA_PACKAGE_CACHE:
        return _OA_PACKAGE_CACHE[pmcid]
    images = {}
    try:
        import tarfile, io as _io
        r = requests.get(
            "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id=%s" % pmcid,
            headers=_headers(), timeout=30)
        links = [L for L in re.findall(r'href="([^"]+)"', r.text or "")
                 if L.endswith(".tar.gz")]
        if not links:
            if log_fn:
                log_fn("    OA service offered no package for %s" % pmcid)
            _OA_PACKAGE_CACHE[pmcid] = images
            return images
        path = links[0].split("ftp.ncbi.nlm.nih.gov", 1)[-1]
        blob = None
        # Deprecated first: the advertised path is the one that 550s.
        for candidate in (path.replace("/pub/pmc/", "/pub/pmc/deprecated/", 1),
                          path):
            try:
                pr = requests.get("https://ftp.ncbi.nlm.nih.gov" + candidate,
                                  headers=_headers(), timeout=120)
            except Exception:
                continue
            if pr.status_code == 200 and len(pr.content) > 5000:
                blob = pr.content
                break
        if not blob:
            if log_fn:
                log_fn("    OA package unreachable for %s" % pmcid)
            _OA_PACKAGE_CACHE[pmcid] = images
            return images
        tf = tarfile.open(fileobj=_io.BytesIO(blob), mode="r:gz")
        for member in tf.getmembers():
            name = member.name.split("/")[-1]
            if not name.lower().endswith((".jpg", ".jpeg", ".png",
                                          ".gif", ".tif", ".tiff")):
                continue
            try:
                images[name.lower()] = tf.extractfile(member).read()
            except Exception:
                continue
        if log_fn:
            log_fn("    OA package %s: %.1f MB, %d image(s)"
                   % (pmcid, len(blob) / 1e6, len(images)))
    except Exception as e:
        if log_fn:
            log_fn("    OA package error %s: %s" % (pmcid, str(e)[:60]))
    _OA_PACKAGE_CACHE[pmcid] = images
    return images


def _figure_from_package(figure, log_fn=None):
    """This figure's bytes out of the article package, matched by filename.

    Matched on the stem rather than the full name because the package
    routinely carries both a .jpg and a .gif of the same figure. The .jpg is
    preferred: on the verified papers the GIFs are low-resolution
    thumbnails and the JPEGs are the full-size originals.
    """
    pmcid = (figure or {}).get("pmcid") or ""
    fname = (figure or {}).get("filename") or ""
    if not pmcid or not fname:
        return None
    images = _oa_package_images(pmcid, log_fn=log_fn)
    if not images:
        return None
    stem = re.sub(r"\.\w+$", "", fname).lower()
    hits = [n for n in images if re.sub(r"\.\w+$", "", n) == stem]
    if not hits:
        hits = [n for n in images if stem and stem in n]
    if not hits:
        return None
    hits.sort(key=lambda n: (not n.endswith((".jpg", ".jpeg")),
                             -len(images[n])))
    return images[hits[0]]


def download_figure(figure, out_path, min_bytes=6000, log_fn=None, retries=2):
    """
    Fetch one screened figure to disk, trying each known URL pattern.

    Returns True on success. Every failure reason is reported through
    log_fn, because a silent False here is indistinguishable from "this
    paper had no figures" -- and those two need very different responses.

    Three checks, in increasing strength:
      * HTTP status
      * Content-Type is an image (a CDN error page can exceed min_bytes
        while being HTML, which would land a text file on disk with a .jpg
        name and fail later inside the renderer instead of here)
      * the bytes actually DECODE as an image, and are large enough to fill
        a 1920x1080 frame without looking like a thumbnail

    min_bytes dropped from 15000 to 6000 because a clean line diagram --
    exactly the kind of figure this channel most wants -- compresses very
    small, and the real test is now whether PIL can open it and what its
    pixel dimensions are, not its file size.

    Transient failures are retried: a single timeout against one host should
    not cost the episode its only real figure.
    """
    fname = figure.get("filename") or ""
    pmcid = figure.get("pmcid") or ""

    # THE PACKAGE FIRST, BECAUSE EVERY PER-FIGURE URL IS DEAD.
    #
    # Nine routes were tested live against two papers and all nine failed --
    # see _oa_package_images for the full table. The package is not a
    # fallback, it is the route; the URL attempts below are kept only so that
    # if NCBI restores a direct path this still picks it up.
    _pkg = _figure_from_package(figure, log_fn=log_fn)
    if _pkg and len(_pkg) > min_bytes and _decodes_as_usable_image(
            _pkg, log_fn, "oa-package:%s" % fname):
        with open(out_path, "wb") as f:
            f.write(_pkg)
        if log_fn:
            log_fn("    figure from OA package: %s (%d bytes)"
                   % (fname, len(_pkg)))
        return True

    # WHAT THE PAGE SAYS BEATS WHAT WE GUESSED. The templates below produced
    # 77 failures and 0 successes on run 30717615638; the page's own <img>
    # URLs are tried first, and the guessed patterns are kept only as a last
    # resort in case the page fetch is the thing that is blocked.
    urls = []
    stem = re.sub(r"\.\w+$", "", fname).lower()
    page_urls = _article_image_urls(pmcid, log_fn=log_fn) if pmcid else []
    # Prefer the page image whose filename stem matches this figure's, so
    # figure 3 does not silently render figure 1.
    matched = [u for u in page_urls if stem and stem in u.lower()]
    for u in matched + [u for u in page_urls if u not in matched]:
        if u not in urls:
            urls.append(u)
    if figure.get("url") and figure["url"] not in urls:
        urls.append(figure["url"])
    for pat in FIGURE_URL_PATTERNS:
        if pmcid and fname:
            u = pat.format(pmcid=pmcid, fname=fname)
            if u not in urls:
                urls.append(u)

    for u in urls:
        for attempt in range(retries):
            try:
                r = requests.get(u, headers=_headers(), timeout=30)
            except Exception as e:
                if log_fn:
                    log_fn(f"    figure fetch error {type(e).__name__} {u[:70]}")
                time.sleep(1.5 * (attempt + 1))
                continue
            if r.status_code in (429, 500, 502, 503, 504) and attempt + 1 < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            if r.status_code != 200:
                if log_fn:
                    log_fn(f"    figure {r.status_code} {u[:88]}")
                break
            ctype = (r.headers.get("Content-Type") or "").lower()
            if "image" not in ctype:
                if log_fn:
                    log_fn(f"    figure not an image ({ctype or 'no type'}) {u[:70]}")
                break
            if len(r.content) <= min_bytes:
                if log_fn:
                    log_fn(f"    figure too small ({len(r.content)}B) {u[:70]}")
                break
            if not _decodes_as_usable_image(r.content, log_fn, u):
                break
            with open(out_path, "wb") as f:
                f.write(r.content)
            return True
    return False


def _decodes_as_usable_image(content, log_fn=None, url=""):
    """
    The bytes must open as an image AND be big enough to fill a frame.

    Content-Type is set by the server and can be wrong; this is the only
    check that cannot be fooled. A 120x90 thumbnail is technically a valid
    image and would render as a postage stamp in the middle of a 1080p
    frame, which looks like a failure even though every earlier check passed.
    """
    try:
        from io import BytesIO
        from PIL import Image
        img = Image.open(BytesIO(content))
        img.verify()
        img = Image.open(BytesIO(content))
        w, h = img.size
    except Exception as e:
        if log_fn:
            log_fn(f"    figure does not decode ({type(e).__name__}) {url[:70]}")
        return False
    if w < 320 or h < 240:
        if log_fn:
            log_fn(f"    figure too low-resolution ({w}x{h}) {url[:70]}")
        return False
    return True


def prefetch_figures(case, work_dir, log_fn=None, prefix="pmcfig"):
    """
    Download every screened figure UP FRONT and keep only the ones that
    actually landed on disk.

    WHY THIS MATTERS MORE THAN IT LOOKS
    -----------------------------------
    The visual quota decides how many FIGURE segments to schedule from
    `case["figures"]`, which is METADATA parsed out of the article XML. If
    the binaries then fail to download, the quota has already committed ~30%
    of the episode to a register with nothing to show, and every one of
    those segments silently renders the plain fallback card.

    That is exactly the failure mode the CHART register had -- a whole
    register scheduled against nothing, degrading to a card that logs as a
    success. It is invisible unless something checks, so this checks: after
    this call, `case["figures"]` contains only figures whose bytes are on
    disk and decode as usable images, and the quota is built from the truth.
    """
    figs = list(case.get("figures") or [])
    if not figs:
        return case
    kept = []
    from pathlib import Path as _P
    # Create the destination. The pipeline happens to mkdir WORK_DIR just
    # before calling this, so the omission was invisible there -- but the
    # function is not safe for any other caller, and the figure-fetch
    # self-test crashed on exactly that. A helper that writes files must
    # own the directory it writes into.
    _P(work_dir).mkdir(parents=True, exist_ok=True)
    for i, fig in enumerate(figs):
        dest = _P(work_dir) / f"{prefix}_{len(kept)}.jpg"
        if download_figure(fig, str(dest), log_fn=log_fn):
            fig = dict(fig)
            fig["local_path"] = str(dest)
            kept.append(fig)
        elif log_fn:
            log_fn(f"    figure {i+1}/{len(figs)} unavailable "
                   f"({fig.get('label') or fig.get('filename') or '?'})")
    case["figures"] = kept
    if log_fn:
        log_fn(f"  Figures on disk: {len(kept)}/{len(figs)} "
               f"({'FIGURE register disabled' if not kept else 'ok'})")
    # A DEGRADED EPISODE MUST NOT LOOK LIKE A HEALTHY ONE.
    #
    # "Figures on disk: 0/6 (FIGURE register disabled)" was a console line in
    # a 2400-line log, and losing the largest visual register is exactly the
    # kind of thing a run should be unable to hide. Run 30717615638 reported
    # SUCCESS while shipping an episode with zero of its paper's real images
    # -- and the only trace was that one line. It now reaches Telegram, where
    # the same person who approves the episode can see what it is missing
    # before approving it.
    case["figures_expected"] = len(figs)
    case["figures_missing"] = len(figs) - len(kept)
    if figs and not kept:
        try:
            from human_review_gate import notify_degraded
            notify_degraded(
                "FIGURE register",
                f"{len(figs)} figure(s) were found in the paper and none could "
                f"be downloaded, so this episode renders with no real images "
                f"from its own case report — the visual mix falls back to "
                f"charts, timelines and text cards. The paper's own page is "
                f"the source of truth for these URLs; if this repeats, the "
                f"article page fetch is being blocked.")
        except Exception:
            pass  # notification is best-effort; the log line above still stands
    return case


def build_citation(article):
    """
    The CC BY attribution string. This is a licensing requirement, not
    formatting -- see the module docstring. Callers must render it
    on-screen with the figure AND in the video description.
    """
    if not article:
        return ""
    authors = article.get("authorString") or "Unknown authors"
    if len(authors) > 90:
        authors = authors.split(",")[0].strip() + " et al."
    title = (article.get("title") or "Untitled").rstrip(". ")
    journal = ""
    jinfo = article.get("journalInfo") or {}
    if isinstance(jinfo, dict):
        journal = ((jinfo.get("journal") or {}).get("title") or "")
    year = article.get("pubYear") or ""
    doi = article.get("doi") or ""
    lic = article.get("license") or "CC BY"
    parts = [p for p in (authors, f"{title}.", journal, str(year)) if p]
    cite = " ".join(parts)
    if doi:
        cite += f" doi:{doi}"
    return f"{cite} — licensed {lic.upper()}"


def get_real_case(niche_name, max_candidates=6):
    """
    One complete, ready-to-script real case for this niche.

    Returns a dict the pipeline can consume directly:
        {narrative, figures, citation, pmcid, title, year, journal, license}
    or None for a non-medical niche, an unreachable API, or when no
    candidate article yields a usable case narrative -- in which case the
    caller keeps its existing behaviour untouched.

    Walks several candidates rather than trusting the first hit, because a
    given article may be CC BY and on-topic yet still have no extractable
    case-presentation section.
    """
    candidates = search_cc_by_cases(niche_name)
    if not candidates:
        return None
    random.shuffle(candidates)   # avoid re-picking the same top-cited case daily
    for article in candidates[:max_candidates]:
        pmcid = article.get("pmcid")
        xml = fetch_full_text(pmcid)
        if not xml:
            continue
        narrative = extract_case_narrative(xml)
        if not narrative:
            continue
        return {
            "narrative": narrative,
            "figures": extract_figures(xml, pmcid),
            "citation": build_citation(article),
            "pmcid": pmcid,
            "title": article.get("title") or "",
            "year": article.get("pubYear") or "",
            "journal": ((article.get("journalInfo") or {}).get("journal") or {}).get("title", ""),
            "license": article.get("license") or "",
        }
    return None


def get_real_cases(niche_name, count=6, max_candidates=20):
    """
    Up to `count` DISTINCT ready-to-script cases for this niche, same dict
    shape as get_real_case().

    Exists because the topic and the sourced case must be the same paper.
    The first live run proved what happens otherwise: the script was written
    about Sylvia Plath while the episode's case was a surgical-oncology
    paper, because topics came from an LLM's idea of viral videos and the
    case came from here. Returning a list lets the caller use each paper's
    own title as that attempt's topic, so the two cannot drift apart -- and
    still gives the retry engine genuinely different subject matter each
    attempt instead of re-running one topic thirteen times.

    Order is preserved from the (shuffled) candidate list, so callers get
    variety across runs without re-picking the same top-cited case daily.
    """
    candidates = search_cc_by_cases(niche_name, page_size=max_candidates)
    if not candidates:
        return []
    random.shuffle(candidates)
    out, seen = [], set()
    for article in candidates[:max_candidates]:
        if len(out) >= count:
            break
        pmcid = article.get("pmcid")
        if not pmcid or pmcid in seen:
            continue
        seen.add(pmcid)
        xml = fetch_full_text(pmcid)
        if not xml:
            continue
        narrative = extract_case_narrative(xml)
        if not narrative:
            continue
        out.append({
            "narrative": narrative,
            "figures": extract_figures(xml, pmcid),
            "citation": build_citation(article),
            "pmcid": pmcid,
            "title": article.get("title") or "",
            "year": article.get("pubYear") or "",
            "journal": ((article.get("journalInfo") or {}).get("journal") or {}).get("title", ""),
            "license": article.get("license") or "",
        })
    # RANK BY WHAT THE CASE CAN ACTUALLY PUT ON SCREEN.
    #
    # This used to sort on len(figures) alone -- the ADVERTISED figure count.
    # That is precisely how run 31740721781 came to pick PMC8068274: it
    # advertised nine figures, sorted to the top, was scripted as attempt 1,
    # and delivered zero images. One promised number outranked every real
    # signal the paper carried.
    #
    # case_richness weighs narrative depth, timeline entries, differentials
    # and charted values alongside figures, so a paper that can genuinely
    # carry twenty minutes outranks one that merely claims pictures. Figures
    # still count and still count heavily -- they are the differentiator --
    # but they are now one dimension of five rather than the only one.
    #
    # Scored here on the advertised count because verifying a download for
    # every candidate would mean dozens of fetches during selection. The
    # caller re-scores the chosen case against VERIFIED figures once, which
    # is where a paper that only promised pictures gets rejected.
    for c in out:
        c["richness"], c["richness_reasons"] = case_richness(c)
    out.sort(key=lambda c: c["richness"], reverse=True)
    return out


def case_to_topic(case, max_words=30):
    """
    A paper's own title, trimmed to a usable episode topic.

    Journal titles carry trailing apparatus ("...: a case report and review
    of the literature") that adds nothing to a topic line and eats the word
    budget, so it is stripped. Never invents or embellishes -- whatever this
    returns is literally what the paper is called, which is the entire point.
    """
    t = (case.get("title") or "").strip().rstrip(".")
    if not t:
        return ""
    t = re.sub(r"\s*[:\-–—]\s*(a\s+)?(rare\s+)?case\s+report.*$", "", t, flags=re.I)
    t = re.sub(r"\s*[:\-–—]\s*(and\s+)?(a\s+)?review\s+of\s+the\s+literature.*$", "", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip()
    words = t.split()
    if len(words) > max_words:
        t = " ".join(words[:max_words])
    return t


def format_script_context(case):
    """
    The sourced-facts block injected into the script prompt's research
    context -- identical role to fred_data.format_narration_block(), and
    carrying the same instruction not to invent competing details.
    """
    if not case:
        return ""
    fig_note = ""
    if case.get("figures"):
        captions = "; ".join(f["caption"][:120] for f in case["figures"][:3])
        fig_note = f"\n  Real figures available from this paper: {captions}"
    return (
        "REAL SOURCED CLINICAL CASE (genuinely real, from the peer-reviewed "
        f"open-access literature — {case['journal']} {case['year']}, {case['pmcid']}. "
        "Base every clinical detail on the text below; do not invent different "
        "values, dates, or quotes, and do not attribute invented speech to "
        "anyone):\n"
        f"  {case['narrative'][:2600]}{fig_note}\n"
    )


# ===========================================================================
# IS THIS CASE RICH ENOUGH TO BE AN EPISODE AT ALL?
#
# "When the case is really thin, yes, I wanted to reject and repick it."
#
# Selection used to have no opinion about this. It walked candidates until
# one produced a case narrative of any length and returned it, and the only
# thing resembling a richness signal was a log line counting ADVERTISED
# figures. Run 31740721781 picked PMC8068274 BECAUSE it listed nine usable
# figures -- and downloaded zero of them. The number that drove the choice
# was a promise the paper made, never a thing the pipeline held.
#
# The distinction between advertised and verified runs through everything
# here. `figures` is what the XML claims exists. `figures_verified` is how
# many actually arrived as decodable image bytes. Only the second may be
# scored, because only the second can be put on screen.
# ===========================================================================

# What a case must supply to carry twenty minutes. Each dimension is
# something a visual register actually consumes, so a case that scores well
# here is one the episode can genuinely be built from.
#
# The floor is 5 of a possible 10. Deliberately not higher: the search
# already restricts to open-access CC BY case reports, so the candidate pool
# is not large, and a gate nothing can pass means every run falls back to
# whatever it can get -- which is the situation this replaces. 5 rejects the
# genuinely threadbare while leaving a workable pool.
CASE_RICHNESS_FLOOR = 5.0


def case_richness(case, verified_figures=None, structures_extracted=True):
    """Score 0-10 for how much real content this case can put on screen.

    Returns (score, reasons) where reasons explains every point, so a
    rejection can say what was missing rather than just refusing.

    verified_figures, when given, overrides the advertised figure count.
    Pass the number that actually downloaded.

    structures_extracted=False WHEN THE EXTRACTION ITSELF FAILED, AND THIS
    DISTINCTION IS THE WHOLE POINT.
    ---------------------------------------------------------------------
    Timeline, differentials and chart values are pulled out of the paper by an
    AI call. When the provider chain is struggling that call returns nothing --
    and the first version of this function then scored those three dimensions
    as ZERO and rejected the paper for being thin.

    Run 31876972186 died of exactly that. Every candidate logged "all 3
    extraction attempts failed", so every candidate scored on narrative and
    figures alone, the ceiling became 5.5 against a floor of 5.0, and 13
    attempts x 3 rounds were all rejected. No episode was possible. The gate
    was blaming papers for a provider outage.

    "Not extracted" and "not present" are different facts and must not share a
    score. When extraction failed, those dimensions are UNKNOWN: they are
    dropped from both the numerator and the denominator, and the result is
    rescaled to what was actually measurable. A paper is then judged on what
    could genuinely be assessed, which is all any gate can honestly do.
    """
    c = case or {}
    reasons, score = [], 0.0
    # Points available from dimensions we could actually measure. Everything
    # below adds to this as it is scored, so the rescale at the end divides by
    # what was really on the table rather than a fixed 10.
    available = 0.0

    narrative = (c.get("narrative") or "").strip()
    words = len(narrative.split())
    # A twenty-minute episode is roughly 2,800 spoken words. The narrative is
    # the seed, not the script, but a 200-word case cannot support one.
    if words >= 900:
        score += 3.0; reasons.append("narrative %d words (rich)" % words)
    elif words >= 500:
        score += 2.0; reasons.append("narrative %d words (adequate)" % words)
    elif words >= 300:
        score += 1.0; reasons.append("narrative %d words (thin)" % words)
    else:
        reasons.append("narrative only %d words (too thin)" % words)
    available += 3.0

    n_fig = (len(c.get("figures") or []) if verified_figures is None
             else int(verified_figures))
    label = "advertised" if verified_figures is None else "VERIFIED"
    if n_fig >= 4:
        score += 2.5; reasons.append("%d %s figure(s)" % (n_fig, label))
    elif n_fig >= 2:
        score += 1.5; reasons.append("%d %s figure(s)" % (n_fig, label))
    elif n_fig == 1:
        score += 0.5; reasons.append("1 %s figure" % label)
    else:
        reasons.append("NO %s figures" % label)
    available += 2.5

    if not structures_extracted:
        # Extraction failed. These three are UNKNOWN, not absent -- see the
        # docstring. Judge on narrative and figures, rescaled.
        reasons.append("timeline/differentials/chart NOT ASSESSED — the "
                       "extraction step failed, so these are unknown rather "
                       "than missing")
        scaled = round(min(10.0, score * 10.0 / available), 2) if available else 0.0
        return scaled, reasons

    timeline = c.get("timeline") or []
    if len(timeline) >= 5:
        score += 1.5; reasons.append("%d timeline entries" % len(timeline))
    elif len(timeline) >= 3:
        score += 1.0; reasons.append("%d timeline entries" % len(timeline))
    elif timeline:
        reasons.append("only %d timeline entr(y/ies)" % len(timeline))
    else:
        reasons.append("no timeline")
    available += 1.5

    diffs = c.get("differentials") or []
    if len(diffs) >= 4:
        score += 1.5; reasons.append("%d differentials" % len(diffs))
    elif len(diffs) >= 2:
        score += 1.0; reasons.append("%d differentials" % len(diffs))
    else:
        reasons.append("%d differential(s)" % len(diffs))
    available += 1.5

    chart = (c.get("chart_data") or {}).get("labels") or []
    if len(chart) >= 4:
        score += 1.5; reasons.append("%d charted values" % len(chart))
    elif chart:
        score += 0.75; reasons.append("%d charted value(s)" % len(chart))
    else:
        reasons.append("no chart data")
    available += 1.5

    return round(min(10.0, score * 10.0 / available), 2) if available else 0.0, reasons


def verify_figures(case, work_dir, log_fn=None, cap=6):
    """How many of this paper's figures actually arrive as image bytes.

    Sets case["figures_verified"] and prunes case["figures"] down to the ones
    that really downloaded, so every later consumer -- the register quota
    above all -- is sized from what exists rather than what was promised.

    This is the whole lesson of run 31740721781 in one function: the quota
    scheduled roughly a fifth of the episode as FIGURE cards on the strength
    of nine advertised figures, then had nothing to put in any of them.
    """
    figures = (case or {}).get("figures") or []
    if not figures:
        case["figures_verified"] = 0
        return 0
    import os
    kept = []
    for idx, fig in enumerate(figures[:cap]):
        out = os.path.join(str(work_dir), "verify_fig_%d.jpg" % idx)
        try:
            if download_figure(fig, out, log_fn=log_fn):
                fig = dict(fig)
                fig["local_path"] = out
                kept.append(fig)
        except Exception as e:
            if log_fn:
                log_fn("    figure verify error %s" % str(e)[:60])
    case["figures"] = kept
    case["figures_verified"] = len(kept)
    if log_fn:
        log_fn("  Figures: %d advertised, %d actually downloaded"
               % (len(figures), len(kept)))
    return len(kept)
