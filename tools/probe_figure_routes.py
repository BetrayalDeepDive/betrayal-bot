#!/usr/bin/env python3
"""
WHICH URL ACTUALLY SERVES A PMC FIGURE? ASK THE RUNNER, NOT THE SANDBOX.

Run 31740721781 lost all nine of its paper's figures. Every candidate URL
failed one of two ways:

    figure not an image (text/html)  ...ncbi.nlm.nih.gov/.../bin/g001.jpg
    figure 403                       ...europepmc.org/articles/.../bin/g001.jpg

pmc_data.FIGURE_URL carries a comment written when the module was built:
"this URL shape could not be verified live from this sandbox". It is still
unverified, and production has now shown it is wrong. The consequence was
not a crash -- it was an episode that shipped with 8-10 visuals repeating
for 22 minutes and reported success.

Guessing a replacement from a sandbox that cannot reach either host would
be the identical mistake. So this asks the machine that CAN reach them.

It is read-only: it downloads a few candidate images for one known
open-access paper, checks whether the bytes decode as a real image of
usable size, and prints a ranked verdict. Nothing is written to the repo
and no episode state is touched.

Usage:  python tools/probe_figure_routes.py [PMCID ...]
Exit 0 if at least one route works, 1 if none do -- so the workflow step
fails loudly rather than reporting a green run that learned nothing.
"""

import io
import re
import sys
import requests

# Two open-access papers with several figures each. Two, not one, so a
# route that happens to work for a single article's storage layout is not
# mistaken for a general answer.
DEFAULT_PMCIDS = ["PMC8068274", "PMC7857393"]

TIMEOUT = 30
UA = {"User-Agent": "Mozilla/5.0 (compatible; NoKnownCause/1.0; +figure-probe)"}

EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"


def _decodes(content):
    """True when these bytes are a real raster image big enough to fill a frame."""
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(content))
        im.load()
        return im.size[0] >= 300 and im.size[1] >= 200, "%dx%d" % im.size
    except Exception as e:
        return False, "undecodable (%s)" % str(e)[:40]


def _try(label, url, results):
    try:
        r = requests.get(url, timeout=TIMEOUT, headers=UA)
    except Exception as e:
        print("  %-34s CONNECT FAIL  %s" % (label, str(e)[:60]))
        results.append((label, False, "connect fail"))
        return None
    ctype = (r.headers.get("Content-Type") or "?").split(";")[0]
    if r.status_code != 200:
        print("  %-34s HTTP %s  %s" % (label, r.status_code, ctype))
        results.append((label, False, "HTTP %s" % r.status_code))
        return None
    ok, detail = _decodes(r.content)
    print("  %-34s %s  %s  %d bytes  %s"
          % (label, "OK   " if ok else "not an image", ctype,
             len(r.content), detail))
    results.append((label, ok, detail))
    return r.content if ok else None


def graphic_hrefs(pmcid):
    """The figure filenames the article's own full text declares."""
    try:
        r = requests.get("%s/%s/fullTextXML" % (EPMC, pmcid),
                         timeout=TIMEOUT, headers=UA)
        if r.status_code != 200:
            print("  fullTextXML: HTTP %s" % r.status_code)
            return []
        hrefs = re.findall(r'xlink:href="([^"]+)"', r.text)
        # Keep the ones that look like figure graphics, in document order.
        figs, seen = [], set()
        for h in hrefs:
            base = h.split("/")[-1]
            if re.search(r"(g\d|fig|f\d)", base, re.I) and base not in seen:
                seen.add(base)
                figs.append(base)
        print("  fullTextXML: %d graphic href(s) -> %s"
              % (len(figs), figs[:4]))
        return figs
    except Exception as e:
        print("  fullTextXML: %s" % str(e)[:70])
        return []


def probe(pmcid):
    print("\n" + "=" * 74)
    print("PMCID %s" % pmcid)
    print("=" * 74)
    figs = graphic_hrefs(pmcid)
    fname = figs[0] if figs else "g001"
    stem = re.sub(r"\.\w+$", "", fname)
    results = []

    print("\n-- routes, using first graphic '%s' --" % fname)
    # Europe PMC's own article-render host. This is the one the browser
    # uses, so if anything is going to serve the bytes it is this.
    _try("europepmc render",
         "https://europepmc.org/api/fulltextRepo?pprId=%s&type=FILE&fileName=%s"
         % (pmcid, fname), results)
    # The modern PMC blob CDN, which is what pmc.ncbi.nlm.nih.gov pages
    # actually reference now that /bin/ returns HTML.
    for ext in ("jpg", "png"):
        _try("cdn blobs .%s" % ext,
             "https://cdn.ncbi.nlm.nih.gov/pmc/blobs/%s/%s.%s"
             % (pmcid, stem, ext), results)
    # The historical patterns, kept so the report says plainly whether the
    # thing currently in pmc_data is dead or merely unlucky.
    _try("ncbi /bin/ (current code)",
         "https://www.ncbi.nlm.nih.gov/pmc/articles/%s/bin/%s" % (pmcid, fname),
         results)
    _try("europepmc /bin/ (current code)",
         "https://europepmc.org/articles/%s/bin/%s" % (pmcid, fname), results)
    # The OA Web Service: the documented, supported way to get an open-access
    # article's files. Returns XML pointing at a package rather than an image,
    # so it is reported separately below.
    try:
        r = requests.get(
            "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id=%s" % pmcid,
            timeout=TIMEOUT, headers=UA)
        links = re.findall(r'href="([^"]+)"', r.text or "")
        print("  %-34s HTTP %s  %d package link(s) %s"
              % ("OA web service", r.status_code, len(links),
                 links[0][:60] if links else ""))
        results.append(("OA web service (package)", bool(links),
                        links[0][:70] if links else "no links"))
        if links:
            results.append(probe_package(links[0]))
    except Exception as e:
        print("  %-34s CONNECT FAIL %s" % ("OA web service", str(e)[:50]))
        results.append(("OA web service (package)", False, "connect fail"))
    return results


def probe_package(ftp_url):
    """Can the runner actually OPEN the package, and are there figures in it?

    The OA service answers with an ftp:// URL. Knowing the URL exists is not
    the same as being able to use it: GitHub runners commonly block outbound
    FTP, and a tarball that turns out to hold only the XML would be no better
    than the dead image routes. NCBI serves the identical tree over HTTPS, so
    this rewrites the scheme and checks the whole path end to end -- fetch,
    untar, find images, decode one.
    """
    import tarfile
    https = ftp_url.replace("ftp://ftp.ncbi.nlm.nih.gov",
                            "https://ftp.ncbi.nlm.nih.gov")
    print("\n-- OA package over HTTPS --")
    try:
        r = requests.get(https, timeout=90, headers=UA)
    except Exception as e:
        print("  %-34s CONNECT FAIL  %s" % ("package download", str(e)[:60]))
        return ("OA package (https, decoded figure)", False, "connect fail")
    if r.status_code != 200:
        print("  %-34s HTTP %s" % ("package download", r.status_code))
        return ("OA package (https, decoded figure)", False,
                "HTTP %s" % r.status_code)
    print("  %-34s HTTP 200  %.1f MB" % ("package download",
                                         len(r.content) / 1e6))
    try:
        tf = tarfile.open(fileobj=io.BytesIO(r.content), mode="r:gz")
        names = tf.getnames()
    except Exception as e:
        print("  %-34s untar failed  %s" % ("package open", str(e)[:50]))
        return ("OA package (https, decoded figure)", False, "untar failed")
    imgs = [n for n in names
            if n.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".tif"))]
    print("  %-34s %d member(s), %d image(s) %s"
          % ("package contents", len(names), len(imgs),
             [n.split("/")[-1] for n in imgs[:4]]))
    if not imgs:
        return ("OA package (https, decoded figure)", False, "no images inside")
    # Decode the largest, which is the one most likely to be a real figure
    # rather than a publisher logo or an equation glyph.
    biggest = max(imgs, key=lambda n: tf.getmember(n).size)
    data = tf.extractfile(biggest).read()
    ok, detail = _decodes(data)
    print("  %-34s %s  %s  %d bytes  %s"
          % ("largest image decodes", "OK   " if ok else "NOT AN IMAGE",
             biggest.split("/")[-1], len(data), detail))
    return ("OA package (https, decoded figure)", ok, detail)


def main():
    pmcids = sys.argv[1:] or DEFAULT_PMCIDS
    all_results = {}
    for p in pmcids:
        for label, ok, detail in probe(p):
            all_results.setdefault(label, []).append(ok)

    print("\n" + "=" * 74)
    print("VERDICT — a route is only usable if it worked for EVERY paper")
    print("=" * 74)
    winners = []
    for label, oks in all_results.items():
        mark = "USABLE  " if all(oks) and oks else "no      "
        if all(oks) and oks:
            winners.append(label)
        print("  %s %-34s %d/%d" % (mark, label, sum(oks), len(oks)))

    if winners:
        print("\nUse: %s" % winners[0])
        print("Wire this into pmc_data.FIGURE_URL_PATTERNS as the first entry.")
        return 0
    print("\nNo route returned a decodable image for every paper.")
    print("Figures cannot be sourced from PMC on this runner; the case gate")
    print("must reject figure-dependent episodes until one is found.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
