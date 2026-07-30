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
FIGURE_URL_PATTERNS = (
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
    "senior_health_longevity": (
        f'{_BASE_FILTER} AND '
        '(TITLE:"ageing" OR TITLE:"aging" OR TITLE:"longevity" OR TITLE:"geriatric" '
        'OR TITLE:"sarcopenia" OR TITLE:"frailty")'
        f' AND {_NO_GRAPHIC}'
    ),
    "medical_mystery_outbreak": (
        f'{_BASE_FILTER} AND '
        '(TITLE:"outbreak" OR TITLE:"cluster" OR ABSTRACT:"epidemiological investigation")'
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
    "medical_history": (
        f'{_BASE_FILTER} AND '
        '(TITLE:"history of medicine" OR TITLE:"historical" OR ABSTRACT:"medical history")'
        f' AND {_NO_GRAPHIC}'
    ),
    "drug_discovery_stories": (
        f'{_BASE_FILTER} AND '
        '(TITLE:"discovery of" OR ABSTRACT:"drug discovery" OR ABSTRACT:"was first isolated")'
        f' AND {_NO_GRAPHIC}'
    ),
    "sleep_science": (
        f'{_BASE_FILTER} AND '
        '(TITLE:"sleep" OR TITLE:"insomnia" OR TITLE:"narcolepsy" OR TITLE:"circadian")'
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


def download_figure(figure, out_path, min_bytes=15000, log_fn=None):
    """
    Fetch one screened figure to disk, trying each known URL pattern.

    Returns True on success. Every failure reason is reported through
    log_fn, because a silent False here is indistinguishable from "this
    paper had no figures" -- and those two need very different responses.

    Checks Content-Type as well as size: a CDN error page can exceed
    min_bytes while being HTML, which would land a text file on disk with
    a .jpg name and fail later inside the renderer instead of here.
    """
    fname = figure.get("filename") or ""
    pmcid = figure.get("pmcid") or ""
    urls = [figure["url"]] if figure.get("url") else []
    for pat in FIGURE_URL_PATTERNS:
        if pmcid and fname:
            u = pat.format(pmcid=pmcid, fname=fname)
            if u not in urls:
                urls.append(u)
    for u in urls:
        try:
            r = requests.get(u, headers=_headers(), timeout=30)
            ctype = (r.headers.get("Content-Type") or "").lower()
            if r.status_code != 200:
                if log_fn: log_fn(f"    figure {r.status_code} {u[:88]}")
                continue
            if "image" not in ctype:
                if log_fn: log_fn(f"    figure not an image ({ctype or 'no type'}) {u[:70]}")
                continue
            if len(r.content) <= min_bytes:
                if log_fn: log_fn(f"    figure too small ({len(r.content)}B) {u[:70]}")
                continue
            with open(out_path, "wb") as f:
                f.write(r.content)
            return True
        except Exception as e:
            if log_fn: log_fn(f"    figure fetch error {type(e).__name__} {u[:70]}")
    return False


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
    # Figure-bearing papers first. The caller uses out[attempt-1], so this
    # puts the best-illustrated case on attempt 1 -- the attempt most likely
    # to be the one that publishes. A paper with no usable figures is still
    # kept (it can carry the episode on BOARD/TIMELINE/CHART/ANATOMY), just
    # ranked below one that can actually show the patient's own imaging,
    # which is the channel's entire differentiator.
    out.sort(key=lambda c: len(c.get("figures") or []), reverse=True)
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
