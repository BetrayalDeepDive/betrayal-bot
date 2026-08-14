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


def _try_zip(label, url, results, expect_images=True):
    """Fetch an archive (or a plain file) and report what is actually inside.

    Separate from _try because these routes answer with a container, and
    "HTTP 200" on a container says nothing about whether there is a figure in
    it -- an empty ZIP and a ZIP full of TIFFs look identical from the status
    line.
    """
    import zipfile
    try:
        r = requests.get(url, timeout=90, headers=UA)
    except Exception as e:
        print("  %-34s CONNECT FAIL  %s" % (label, str(e)[:55]))
        results.append((label, False, "connect fail"))
        return
    ctype = (r.headers.get("Content-Type") or "?").split(";")[0]
    if r.status_code != 200:
        print("  %-34s HTTP %s  %s" % (label, r.status_code, ctype))
        results.append((label, False, "HTTP %s" % r.status_code))
        return
    if not expect_images:
        print("  %-34s HTTP 200  %s  %d bytes"
              % (label, ctype, len(r.content)))
        results.append((label, False, "not an image container"))
        return
    try:
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        names = zf.namelist()
    except Exception as e:
        print("  %-34s HTTP 200 but not a zip  %s  %s"
              % (label, ctype, str(e)[:35]))
        results.append((label, False, "not a zip"))
        return
    imgs = [n for n in names
            if n.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".tif"))]
    print("  %-34s HTTP 200  %d member(s), %d image(s) %s"
          % (label, len(names), len(imgs),
             [n.split("/")[-1] for n in imgs[:3]]))
    if not imgs:
        results.append((label, False, "zip has no images"))
        return
    biggest = max(imgs, key=lambda n: zf.getinfo(n).file_size)
    ok, detail = _decodes(zf.read(biggest))
    print("  %-34s %s  %s  %s"
          % ("  -> largest decodes", "OK   " if ok else "NOT AN IMAGE",
             biggest.split("/")[-1], detail))
    results.append((label, ok, detail))


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
    # What the live article page itself references. pmc_data already has an
    # _article_image_urls() that scrapes this and it produced nothing in
    # production, so print the raw <img> srcs: either the page has no usable
    # image URLs at all, or the scraper is looking for the wrong shape, and
    # those need opposite fixes.
    for host in ("https://pmc.ncbi.nlm.nih.gov/articles/%s/" % pmcid,
                 "https://europepmc.org/article/MED/%s" % pmcid.replace("PMC", "")):
        try:
            r = requests.get(host, timeout=TIMEOUT, headers=UA)
            srcs = re.findall(r'<img[^>]+src="([^"]+)"', r.text or "")
            big = [s for s in srcs if re.search(r"\.(jpg|jpeg|png|gif)", s, re.I)]
            print("  %-34s HTTP %s  %d img tag(s), %d image-like"
                  % ("article page " + host.split("/")[2], r.status_code,
                     len(srcs), len(big)))
            for s in big[:5]:
                print("      %s" % s[:110])
        except Exception as e:
            print("  %-34s FAIL %s" % ("article page " + host.split("/")[2],
                                       str(e)[:50]))

    # Europe PMC's supplementary-files endpoint. Documented, returns a ZIP.
    # Nominally "supplementary" rather than "figures", but on many articles
    # the deposited package includes the figure images, and it is one HTTPS
    # call against a host this pipeline already depends on.
    _try_zip("europepmc supplementaryFiles",
             "%s/%s/supplementaryFiles" % (EPMC, pmcid), results)

    # The PMC Open Access subset on AWS Open Data. Public bucket, no
    # credentials, and it is the route NCBI now points bulk users at -- which
    # is consistent with the FTP package path having gone stale.
    for sub in ("oa_comm", "oa_noncomm"):
        _try_zip("s3 %s package" % sub,
                 "https://pmc-oa-opendata.s3.amazonaws.com/%s/xml/all/%s.xml"
                 % (sub, pmcid), results, expect_images=False)

    # The OA Web Service: the documented, supported way to get an open-access
    # article's files. Returns XML pointing at a package rather than an image,
    # so it is reported separately below.
    try:
        r = requests.get(
            "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id=%s" % pmcid,
            timeout=TIMEOUT, headers=UA)
        links = re.findall(r'href="([^"]+)"', r.text or "")
        print("  %-34s HTTP %s  %d package link(s)"
              % ("OA web service", r.status_code, len(links)))
        for L in links:
            print("      %s" % L)
        # NOT scored as usable on its own. The last run marked this route
        # "USABLE 2/2" purely because it returned links -- and both links
        # turned out to be 550 No such file. A route that answers with a
        # dead pointer has not served a figure, and the verdict must not say
        # otherwise. Only probe_package's result counts.
        tgz = [L for L in links if L.endswith(".tar.gz")]
        if tgz:
            results.append(probe_package(tgz[0]))
        else:
            results.append(("OA package (decoded figure)", False,
                            "no tgz link offered"))
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
    path = ftp_url.split("ftp.ncbi.nlm.nih.gov", 1)[-1]
    print("\n-- OA package: getting the bytes --")
    blob = None
    # The HTTPS mirror is the first choice: no extra protocol, no extra
    # library, and it goes through the same proxy as everything else. But
    # "the FTP tree is also on HTTPS" is itself an assumption, so each form
    # is tried and reported rather than assumed.
    for label, url in (("https ftp.ncbi", "https://ftp.ncbi.nlm.nih.gov" + path),
                       ("https www.ncbi", "https://www.ncbi.nlm.nih.gov" + path)):
        try:
            r = requests.get(url, timeout=120, headers=UA)
        except Exception as e:
            print("  %-34s CONNECT FAIL  %s" % (label, str(e)[:50]))
            continue
        print("  %-34s HTTP %s  %.2f MB  %s"
              % (label, r.status_code, len(r.content) / 1e6,
                 (r.headers.get("Content-Type") or "?").split(";")[0]))
        if r.status_code == 200 and len(r.content) > 5000:
            blob = r.content
            break
    if blob is None:
        # Plain FTP, straight from the URL the OA service actually gave us.
        #
        # The previous run proved FTP itself is NOT blocked here: it connected
        # and answered "550 No such file". So the OA service is handing out a
        # path that does not exist -- its response is stale relative to the
        # tree it points at. Which means the useful question is no longer
        # "can we fetch this file" but "what is actually in that directory",
        # so this lists the parent before giving up.
        try:
            import ftplib
            buf = io.BytesIO()
            ftp = ftplib.FTP("ftp.ncbi.nlm.nih.gov", timeout=90)
            ftp.login()
            try:
                ftp.retrbinary("RETR " + path, buf.write)
                blob = buf.getvalue()
                print("  %-34s OK  %.2f MB" % ("plain ftp", len(blob) / 1e6))
            except Exception as e:
                print("  %-34s FAIL  %s" % ("plain ftp", str(e)[:60]))
                parent = path.rsplit("/", 1)[0]
                try:
                    listing = ftp.nlst(parent)
                    print("  %-34s %d entr(y/ies) in %s"
                          % ("ftp listing", len(listing), parent))
                    for n in listing[:10]:
                        print("      %s" % n)
                except Exception as e2:
                    print("  %-34s %s" % ("ftp listing", str(e2)[:60]))
            ftp.quit()
        except Exception as e:
            print("  %-34s CONNECT FAIL  %s" % ("plain ftp", str(e)[:60]))
    if not blob:
        return ("OA package (decoded figure)", False, "could not fetch package")
    try:
        tf = tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz")
        names = tf.getnames()
    except Exception as e:
        print("  %-34s untar failed  %s" % ("package open", str(e)[:50]))
        return ("OA package (decoded figure)", False, "untar failed")
    imgs = [n for n in names
            if n.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".tif"))]
    print("  %-34s %d member(s), %d image(s) %s"
          % ("package contents", len(names), len(imgs),
             [n.split("/")[-1] for n in imgs[:4]]))
    if not imgs:
        return ("OA package (decoded figure)", False, "no images inside")
    # Decode the largest, which is the one most likely to be a real figure
    # rather than a publisher logo or an equation glyph.
    biggest = max(imgs, key=lambda n: tf.getmember(n).size)
    data = tf.extractfile(biggest).read()
    ok, detail = _decodes(data)
    print("  %-34s %s  %s  %d bytes  %s"
          % ("largest image decodes", "OK   " if ok else "NOT AN IMAGE",
             biggest.split("/")[-1], len(data), detail))
    return ("OA package (decoded figure)", ok, detail)


def map_the_ftp_tree():
    """Where do the OA packages actually live now?

    The OA service points at /pub/pmc/oa_package/db/2e/PMCxxxx.tar.gz and the
    server says that directory does not exist -- not the file, the directory.
    So the tree moved and the service's response was never updated. Rather
    than propose a tenth path and test it, ask the server for its own layout
    once and read the answer.
    """
    print("\n" + "=" * 74)
    print("WHERE DID THE PACKAGES GO? (one listing beats another guess)")
    print("=" * 74)
    try:
        import ftplib
        ftp = ftplib.FTP("ftp.ncbi.nlm.nih.gov", timeout=60)
        ftp.login()
        for d in ("/pub/pmc", "/pub/pmc/oa_package", "/pub/pmc/oa_bulk"):
            try:
                entries = ftp.nlst(d)
                print("  %-26s %d entr(y/ies)" % (d, len(entries)))
                for e in entries[:14]:
                    print("      %s" % e)
            except Exception as e:
                print("  %-26s %s" % (d, str(e)[:55]))
        ftp.quit()
    except Exception as e:
        print("  ftp connect failed: %s" % str(e)[:70])


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
    map_the_ftp_tree()
    print("\nNo route returned a decodable image for every paper.")
    print("Figures cannot be sourced from PMC on this runner; the case gate")
    print("must reject figure-dependent episodes until one is found.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
